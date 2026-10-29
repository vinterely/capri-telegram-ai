import asyncio
import json
import logging
import re
import time

log = logging.getLogger("tools")

from ai_engine import ai
from services.social import briefing
from core import cache
from services.telegram import channels
from core import config
from services.media import fetch
from services.telegram import folders
from services.search import gsearch
from core import memory
from services.search import search
from services.search import websearch

# Tools permissible for non-owner whitelisted users
# Tools permissible for non-owner whitelisted users (strictly excludes any link/file/destructive tools)
STRANGER_ALLOWED_TOOLS = {
    "web_search", "get_current_datetime", "send_voice_note",
    "search_google_images",
    "roast_target", "vibe_check", "generate_meme", "ask_clarification",
}

# ابزارهای مجاز پس از مصرف محتوای خارجی غیرقابل‌اعتماد (Taint Quarantine):
# فقط ابزارهای کاملاً امن و ایزوله که هیچ تماسی با شبکه، اینترنت، فایل، کانال، حافظه یا تنظیمات ندارند!
POST_TAINT_ALLOWED_TOOLS = {
    "ask_clarification", "get_current_datetime",
}
READ_ONLY_TOOLS = POST_TAINT_ALLOWED_TOOLS  # جهت سازگاری کامل

UNTRUSTED_SOURCE_TOOLS = {
    "web_search", "deep_search", "read_webpage", "summarize_youtube_video", "get_youtube_video_info", "search_channel_files",
    "search_in_channel", "get_daily_briefing", "vibe_check", "read_channel_posts",
    "search_music", "fetch_and_forward_movie", "download_social_media",
}
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "جستجو در وب برای اخبار روز، قیمت‌ها، وقایع، مشخصات فنی یا اطلاعاتی که از صحت آن مطمئن نیستی. هرگز برای دانلود فایل، دانلود ویدیو یا باز کردن مستقیم لینک‌های مشخص وب فراخوانی نشود.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "عبارت جستجو."}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "deep_search",
            "description": "جستجوی عمیق و چندزبانه (انگلیسی، چینی، فارسی) در وب برای موضوعات تخصصی، ترفندها و مستندات دقیق. وقتی جستجوی معمولی کافی نبود یا موضوع فنی/پیچیده است.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "موضوع یا سوال تخصصی برای جستجوی عمیق."}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_channel_files",
            "description": "جستجوی فایل، آهنگ یا ویدیو در تمام کانال‌ها و گروه‌های تلگرام کاربر و فوروارد آن.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "نام فایل یا کلمه کلیدی."},
                    "kind": {"type": "string", "enum": ["video", "music", "document"], "description": "نوع رسانه."}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_music",
            "description": "گرفتن آهنگ یا موزیک از @DeezerMusicBot (و در صورت خطا، جستجو در کانال‌ها و گروه‌های تلگرام) و ارسال فایل صوتی بدون کپشن. برای درخواست‌هایی مثل «آهنگ ... بفرست»، «موزیک ... بده»، «اهنگ ... بذار».",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "نام آهنگ یا نام خواننده."}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_in_channel",
            "description": "جستجوی فایل یا پیام در یک کانال تلگرامی مشخص با نام channel_name و ارسال آن.",
            "parameters": {
                "type": "object",
                "properties": {
                    "channel_name": {"type": "string", "description": "نام یا شناسه کانال."},
                    "query": {"type": "string", "description": "نام فایل یا موضوع."},
                    "kind": {"type": "string", "enum": ["video", "music", "document"], "description": "نوع رسانه."}
                },
                "required": ["channel_name", "query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_and_forward_movie",
            "description": "جستجو و ارسال مستقیم فایل فیلم یا سریال از بات‌های تلگرام. فقط و فقط وقتی کاربر صریحاً دستور دانلود/ارسال فایل فیلم یا سریال می‌دهد. هرگز برای نقد، تحلیل، سوالات عمومی، خلاصه‌سازی و یا لینک‌های یوتیوب و شبکه‌های اجتماعی فراخوانی نشود.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "نام فیلم/سریال یا لینک دانلود."},
                    "quality": {"type": "integer", "description": "کیفیت عددی مانند 1080، 720، 480."},
                    "audio": {"type": "string", "enum": ["subtitled", "dubbed"], "description": "نوع صوت یا زیرنویس: subtitled برای زیرنویس چسبیده یا زیرنویس، dubbed برای دوبله فارسی."},
                    "season": {"type": "integer", "description": "شماره فصل سریال در صورت درخواست کاربر."},
                    "episode": {"type": "string", "description": "شماره قسمت سریال (عددی) یا all برای کل فصل."}
                },
                "required": ["target"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_google_images",
            "description": "جستجو و ارسال تصاویر گوگل در چت تلگرام. فقط وقتی کاربر عکس موضوعی را می‌خواهد.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "موضوع یا نام شخص برای تصویر."},
                    "count": {"type": "integer", "description": "تعداد عکس‌ها (پیش‌فرض ۳)."}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "manage_memory",
            "description": "مدیریت حافظه ماندگار این گفتگو (افزودن، حذف، لیست یا پاکسازی علایق و مشخصات کاربر منحصراً در فضای همین چت).",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["add", "remove", "list", "clear", "transfer"], "description": "عملیات حافظه."},
                    "fact": {"type": "string", "description": "متن واقعیت برای add یا remove یا transfer."},
                    "target_chat": {"type": "string", "description": "شناسه یا عنوان گفتگوی مقصد برای انتقال صریح (منحصراً در action='transfer')."}
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "manage_channel_membership",
            "description": "مدیریت عضویت یا خروج از کانال‌های تلگرام (join یا leave). خروج (لفت دادن) نیازمند تأیید کاربر است.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["join", "leave"], "description": "leave برای لفت دادن یا خروج از کانال؛ join برای عضویت یا پیوستن."},
                    "target": {"type": "string", "description": "نام یا لینک کانال مورد نظر."}
                },
                "required": ["action", "target"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "manage_folders",
            "description": "مدیریت پوشه‌های چت تلگرام: مشاهده لیست پوشه‌ها (action='list')، ساخت پوشه (action='create')، حذف (action='delete')، افزودن کانال به پوشه (action='assign')، یا مرتب‌سازی خودکار همه کانال‌ها و گروه‌ها (action='auto_sort'). وقتی کاربر گفت «پوشه‌هامو مرتب کن» یا «پوشه‌ها رو دسته‌بندی کن» حتماً auto_sort را صدا بزن.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["list", "create", "delete", "assign", "auto_sort"], "description": "عملیات پوشه."},
                    "folder_name": {"type": "string", "description": "نام پوشه."},
                    "channel_name": {"type": "string", "description": "نام کانال."}
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "manage_important_channels",
            "description": "مدیریت کانال‌های مهم تلگرام برای گزارش و خلاصه روزانه (add، remove، list).",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["add", "remove", "list"], "description": "عملیات."},
                    "channel_name": {"type": "string", "description": "نام کانال."}
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_daily_briefing",
            "description": "دریافت گزارش و خلاصه پیام‌های جدید کانال‌های مهم تلگرام کاربر.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_datetime",
            "description": "دریافت تاریخ شمسی و میلادی و ساعت فعلی به وقت ایران.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_webpage",
            "description": "مطالعه و استخراج متن کامل یک صفحه وب از طریق لینک URL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "آدرس اینترنتی کامل صفحه وب."}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "summarize_youtube_video",
            "description": "خلاصه‌سازی هوشمند و متنی محتوای ویدیوی یوتیوب بدون مصرف حجم و بدون دانلود فایل ویدیو. فقط وقتی کاربر خلاصه، نکات مهم، چکیده یا بررسی محتوای ویدیوی یوتیوب را خواسته است. هرگز برای دانلود ویدیو یا سوالات عمومی تاریخی بدون لینک یوتیوب فراخوانی نشود.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "لینک کامل یا شناسه ویدیو در یوتیوب."}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_youtube_video_info",
            "description": "دریافت اطلاعات، مشخصات و متادیتای ویدیوی یوتیوب (عنوان، نام کانال، مدت زمان، تاریخ انتشار، تعداد بازدید و لایک) بدون دانلود ویدیو و بدون خلاصه‌سازی کامل متن. فقط وقتی کاربر مشخصات، مدت زمان یا اطلاعات یک لینک یوتیوب را می‌خواهد.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "لینک کامل یا شناسه ویدیو در یوتیوب."}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "download_youtube_video",
            "description": "دانلود و ارسال فایل ویدیوی یوتیوب در چت با کیفیت دلخواه (پیش‌فرض 720p). فقط و فقط وقتی کاربر صریحاً دستور دانلود یا دریافت فایل ویدیو را داده است (مانند «دانلود کن»، «فایل ویدیو رو بفرست»). هرگز برای خلاصه‌سازی، دریافت مشخصات یا سوالات تئوری فراخوانی نشود.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "لینک ویدیوی یوتیوب."},
                    "quality": {"type": "integer", "description": "کیفیت عددی مانند 1080، 720، 480."}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "download_social_media",
            "description": "دانلود ویدیو/پست/آهنگ از شبکه‌های اجتماعی (اینستاگرام، تیک‌تاک، پینترست، توییتر/ایکس یا ساوندکلاد) و فوروارد مستقیم فایل به چت. فقط وقتی کاربر صریحاً دستور دانلود فایل از این شبکه‌ها را دارد یا لینک مستقیم بدون پرسش فرستاده است (نه برای یوتیوب و نه برای سوالات متنی یا خلاصه‌سازی).",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "لینک کامل پست/ویدیو از تیک‌تاک، اینستاگرام، پینترست، توییتر/ایکس یا ساوندکلاد."}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_voice_note",
            "description": "تبدیل پاسخ به پیام صوتی (ویس) تلگرام با صدای طبیعی. وقتی کاربر ویس یا پیام صوتی خواسته است.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "متن صمیمی و محاوره‌ای برای ویس که باید همراه با حرکات کامل اعرابی (فتحه َ، کسره ِ، ضمه ُ، تشدید ّ) نوشته شود تا تلفظ دقیق باشد."
                    }
                },
                "required": ["text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ask_clarification",
            "description": "پرسیدن یک سوال کوتاه و صمیمی برای رفع ابهام در صورتی که درخواست کاربر ناقص یا دوپهلو باشد.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "سوال شفاف‌سازی."}
                },
                "required": ["question"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "draft_and_send_message",
            "description": "تنظیم پیش‌نویس پیام و ارسال به مخاطب در تلگرام پس از تأیید (Ghostwriter).",
            "parameters": {
                "type": "object",
                "properties": {
                    "target_contact": {"type": "string", "description": "نام مخاطب، آیدی یا 'reply'."},
                    "message_intent": {"type": "string", "description": "متن یا منظور پیام."},
                    "tone": {"type": "string", "description": "لحن پیام."}
                },
                "required": ["target_contact", "message_intent"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "roast_target",
            "description": "روست کردن، حاضرجوابی و شوخی سنگین با شخص مقابل در چت با ریپلای روی پیام او.",
            "parameters": {
                "type": "object",
                "properties": {
                    "style": {"type": "string", "description": "سبک روست (سنگین، طعنه‌دار، کنایه‌آمیز)."}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "vibe_check",
            "description": "تحلیل روان‌شناختی جو چت و لحن پیام‌های اخیر.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "تمرکز تحلیلی کاربر."}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_meme",
            "description": "ساخت تصویر میم طنز از روی عکس یا پیام ریپلای شده طرف مقابل.",
            "parameters": {
                "type": "object",
                "properties": {
                    "caption": {"type": "string", "description": "ایده یا متن طنز میم."}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_or_update_skill",
            "description": "ساخت و ثبت مهارت پایتونی جدید برای کاپری.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "نام اسکیل."},
                    "description": {"type": "string", "description": "توضیح اسکیل."},
                    "parameters": {"type": "object", "description": "اسکیمای JSON."},
                    "python_code": {"type": "string", "description": "کد پایتون execute(args, client, event)."}
                },
                "required": ["name", "description", "python_code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_skills",
            "description": "مشاهده لیست تمام اسکیل‌های فعال.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_skill",
            "description": "حذف یک اسکیل داینامیک.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "نام اسکیل."}
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "manage_dnd",
            "description": "مدیریت حالت سرشلوغ، خواب و مزاحم نشوید (DND). هر زمان کاربر گفت درگیرم، کلاسم، جلسه دارم، کار دارم، سرم شلوغه، مزاحمم نشید (action='enable')، یا گفت بیدار شدم، آزاد شدم، تموم شد، لغو کن (action='disable')، یا وضعیت خواست (action='status'). پارامتر reason علت مشغله است و duration_or_time زمان پایان (مثلاً: «تا ساعت ۱۴»، «۲ ساعت»، «تا فردا صبح»).",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["enable", "disable", "status"], "description": "عملیات: enable برای فعال‌سازی، disable برای خاموش کردن، status برای وضعیت."},
                    "reason": {"type": "string", "description": "علت سرشلوغی مانند خواب، کلاس دانشگاه، جلسه کاری، درس و امتحان."},
                    "duration_or_time": {"type": "string", "description": "مدت زمان یا ساعت پایان، مثلاً: «ساعت ۱۴»، «۲ ساعت»، «تا فردا صبح»."}
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "manage_reminders",
            "description": "مدیریت یادآورها و تسک‌های زمان‌دار در Saved Messages. هر زمان کاربر گفت فلان ساعت یادم بنداز، نیم ساعت دیگه بگو، یادم نره (action='add')، یا یادآورها رو نشون بده (action='list')، یا پاک/حذف کن (action='clear' یا action='delete'). پارامتر text متن یادآوری، time_expression زمان سررسید آن، و index شماره یادآور برای حذف تکی است.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["add", "list", "clear", "delete", "remove"], "description": "عملیات: add برای ثبت یادآور، list برای نمایش، clear یا delete برای پاک کردن یادآورها."},
                    "text": {"type": "string", "description": "متن موضوع یادآوری (مثلاً: «ارسال جزوه به استاد»)."},
                    "time_expression": {"type": "string", "description": "زمان سررسید یادآوری، مثلاً: «ساعت ۱۰»، «نیم ساعت دیگه»، «فردا ساعت ۹ صبح»."},
                    "index": {"type": "integer", "description": "شماره یا اندیس یادآور (مثلاً ۱ یا ۲) در صورت درخواست حذف یک مورد خاص."}
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "organize_saved_messages",
            "description": "دسته‌بندی، تفکیک و انتقال پیام‌های ذخیره شده (Saved Messages) به سوپرگروه اختصاصی صندوق هوشمند (Capri Vault) با تاپیک‌های تفکیک‌شده. هر زمان کاربر گفت پیام‌های سیو مسیج را مرتب کن، یا اگر در چت Saved Messages بود و با عباراتی عامیانه مانند «اینجا را مرتب کن»، «پیام‌های اینجا رو بچین»، «بریز تو تاپیک‌ها»، «صندوقو مرتب کن» درخواست تفکیک داد، از این ابزار استفاده کن. پارامتر limit تعداد پیام‌ها است (مثلاً ۱۰، ۵۰، ۱۰۰، ۵۰۰؛ برای همه عدد 1- ارسال شود).",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "تعداد پیام‌های اخیر برای سازمان‌دهی (مثلاً ۱۰، ۵۰، ۵۰۰، ۱۰۰۰). برای تمام پیام‌ها عدد 1- ارسال شود."}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_vault_info",
            "description": "دریافت وضعیت و آمار سوپرگروه صندوق هوشمند سیو مسیج، لینک دسترسی و تعداد پیام‌های بایگانی‌شده در هر تاپیک.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "purge_vault",
            "description": "پاک‌سازی و حذف پیام‌های داخل سوپرگروه صندوق هوشمند (Capri Vault). هر زمان کاربر گفت صندوق را پاک کن، خالی کن، پیام‌های صندوق رو پاکسازی کن، یا N پیام اخیر صندوق را پاک کن، از این ابزار استفاده کن. پارامتر limit تعداد پیام‌های حذفی است (برای پاک‌سازی کامل عدد 1-).",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "تعداد پیام‌های اخیر برای حذف (مثلاً ۵۰). برای پاک‌سازی کامل صندوق عدد 1- ارسال شود."}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_sticker",
            "description": "ارسال یک استیکر احساسی متناسب با حال‌وهوای گفتگو. فقط در لحظه‌های احساسی قوی (شوخی و خنده، همدردی، جشن و تبریک، تعجب) و حداکثر یک استیکر در هر پاسخ استفاده شود؛ هرگز پشت‌سرهم یا برای پیام‌های عادی/فنی/اطلاعاتی استیکر نفرست. پارامتر emotion یکی از: خنده، شادی، غم، عشق، تعجب، خشم، خستگی، چشمک، تشویق.",
            "parameters": {
                "type": "object",
                "properties": {
                    "emotion": {"type": "string", "description": "احساس استیکر: خنده/شادی/غم/عشق/تعجب/خشم/خستگی/چشمک/تشویق."}
                },
                "required": ["emotion"]
            }
        }
    }
]


def get_all_tool_definitions(is_owner: bool = True, tainted: bool = False) -> list:
    """
    تولید لیست ابزارهای فعال بر اساس نقش کاربر و وضعیت آلودگی داده (Taint).
    در وضعیت Taint، مدل بلافاصله خلع سلاح می‌شود و هیچ ابزار شبکه‌ای یا فایلی دریافت نمی‌کند.
    """
    if tainted:
        return [t for t in TOOL_DEFINITIONS if t["function"]["name"] in POST_TAINT_ALLOWED_TOOLS]

    from ai_engine import skills_manager
    from core import config
    allow_skills = getattr(config, "ALLOW_SKILL_CREATION", False) or getattr(skills_manager, "ALLOW_SKILL_CREATION", False)

    base_tools = TOOL_DEFINITIONS
    if not allow_skills:
        base_tools = [t for t in base_tools if t["function"]["name"] not in ("create_or_update_skill", "delete_skill")]

    if not is_owner:
        return [t for t in base_tools if t["function"]["name"] in STRANGER_ALLOWED_TOOLS]

    dynamic = skills_manager.get_skill_tool_definitions() if allow_skills else []
    return base_tools + dynamic


async def execute_tool(name: str, args: dict, event, client, status=None, is_owner: bool = True, tainted: bool = False) -> str:
    """Execute dispatched tool and return stringified result to the ReAct agent."""
    from core import config
    try:
        # ۱. قرنطینه امنیتی Taint: در صورتی که داده خارجی مصرف شده باشد، هیچ ابزار شبکه‌ای یا فایلی حق اجرا ندارد
        if tainted and name not in POST_TAINT_ALLOWED_TOOLS:
            return (
                f"⛔ قرنطینه امنیتی داده‌های خارجی (Taint Quarantine): "
                f"ابزار '{name}' پس از دریافت داده از وب/رسانه مسدود است. "
                f"جهت پیشگیری ۱۰۰٪ از تزریق پرامپت و نشت اطلاعات، این درخواست فقط باید به شکل پاسخ متنی تکمیل شود."
            )

        # ۲. گارد تفکیک مالک/غریبه
        is_really_owner = is_owner and getattr(event, "out", False)
        if not is_really_owner and name not in STRANGER_ALLOWED_TOOLS:
            return "⛔ این قابلیت فقط برای صاحب اکانت فعال است."

        # ۳. گارد اسکیل‌ها
        if name in ("create_or_update_skill", "delete_skill"):
            from core import config
            from ai_engine import skills_manager
            allow_skills = getattr(config, "ALLOW_SKILL_CREATION", False) or getattr(skills_manager, "ALLOW_SKILL_CREATION", False)
            if not allow_skills:
                return "⛔ ساخت، ویرایش یا حذف اسکیل‌ها در تنظیمات سیستم غیرفعال است (ALLOW_SKILL_CREATION=0)."
            if tainted:
                return "⛔ خطای امنیتی: ایجاد یا ذخیره اسکیل پس از مصرف داده‌های خارجی مسدود است."
        if name == "web_search":
            query = args.get("query", "").strip()
            if not query:
                return "خطا: عبارت جستجو خالی است."
            # Query normalization and single fast search pass
            fixed = (await asyncio.to_thread(ai._search_query, query) or query).strip()
            if status:
                await status.edit(f"🔍 در حال جستجوی سریع برای: «{fixed}»...")
            results = await asyncio.to_thread(gsearch.web_search, fixed, 5)
            if not results:
                results = await asyncio.to_thread(gsearch.web_search, query, 5)
            if not results:
                return "هیچ نتیجه‌ای در جستجوی اینترنت یافت نشد."
            return gsearch.format_search_results(results)

        elif name == "deep_search":
            query = args.get("query", "").strip()
            if not query:
                return "خطا: عبارت جستجو خالی است."
            if status:
                try:
                    await status.edit(f"🔎 در حال جستجوی عمیق چندزبانه برای: «{query}»...")
                except Exception:
                    pass
            return await asyncio.to_thread(gsearch.multilingual_deep_search, query)

        elif name == "search_channel_files":
            query = args.get("query", "").strip()
            kind = (args.get("kind", "") or "").strip().lower()
            if not query:
                return "خطا: عبارت جستجو مشخص نشده."
            if status:
                await status.edit(f"🔍 در حال جستجوی «{query}» در کانال‌ها...")
            results = await search.find_files(client, query, limit=3, kind=kind)
            if not results:
                return f"هیچ فایلی با نام یا موضوع «{query}» در کانال‌ها پیدا نشد."
            for r in results:
                if r["kind"] == "text":
                    await client.send_message(event.chat_id, r["text"])
                elif kind == "music" and getattr(r["msg"], "media", None):
                    # Re-upload audio track cleanly to strip forwarded origin channel metadata
                    await client.send_file(event.chat_id, r["msg"].media, caption=r.get("name") or None)
                else:
                    await client.forward_messages(event.chat_id, r["msg"])
                await asyncio.sleep(0.4)
            if kind == "music":
                return f"تعداد {len(results)} آهنگ یافت شد و ارسال شد (بدون نمایش منبع)."
            return f"تعداد {len(results)} مورد یافت شد و مستقیماً از تلگرام فوروارد شد (بدون مصرف حجم)."

        elif name == "search_music":
            query = args.get("query", "").strip()
            if not query:
                return "خطا: نام آهنگ مشخص نشده است."

            # Query Deezer Music Bot first; fallback to user channels if unavailable
            if status:
                await status.edit(f"🎵 در حال گرفتن آهنگ «{query}» از @DeezerMusicBot...")
            try:
                from services.media import deezer
                dsent, derr = await deezer.fetch_music(client, query, event=event, status=status)
            except Exception as e:
                dsent, derr = 0, str(e)
            if dsent:
                return f"آهنگ «{query}» از @DeezerMusicBot گرفته شد و بدون کپشن/منبع ارسال شد."

            if status:
                await status.edit(f"🎵 Deezer جواب نداد ({derr})؛ دارم توی کانال‌ها می‌گردم: «{query}»...")
            results = await search.find_files(client, query, limit=3, kind="music")
            if not results:
                return f"❌ خطا در یافتن آهنگ: هیچ آهنگی با نام یا خواننده «{query}» پیدا نشد (نه در Deezer نه در کانال‌ها)."
            sent = 0
            send_errors = []
            for r in results:
                m = r.get("msg")
                if getattr(m, "media", None):
                    try:
                        await client.send_file(event.chat_id, m.media, caption=r.get("name") or None)
                        sent += 1
                        await asyncio.sleep(0.6)
                    except Exception as err:
                        send_errors.append(str(err))
                        continue
            if not sent:
                err_detail = f" ({send_errors[0]})" if send_errors else ""
                return f"❌ خطا در ارسال تلگرام: آهنگ «{query}» پیدا شد اما ارسال آن به چت با خطا مواجه شد{err_detail}."
            return f"تعداد {sent} آهنگ برای «{query}» پیدا و ارسال شد (بدون نمایش منبع)."

        elif name == "search_in_channel":
            chan = args.get("channel_name", "").strip()
            query = args.get("query", "").strip()
            kind = (args.get("kind", "") or "").strip().lower()
            if not chan or not query:
                return "خطا: نام کانال و عبارت جستجو الزامی است."
            if status:
                await status.edit(f"🔍 در حال جستجو در کانال «{chan}» برای «{query}»...")
            dialogs = await channels.find_channels(client, chan)
            if not dialogs:
                return f"کانالی با نام «{chan}» در اکانت پیدا نشد."
            target = dialogs[0]
            results = await search.find_in_channel(client, target.entity, query, limit=5, kind=kind)
            if not results:
                return f"در کانال «{target.name}» موردی برای «{query}» پیدا نشد."
            for r in results:
                if r["kind"] == "text":
                    await client.send_message(event.chat_id, r["text"])
                elif kind == "music" and getattr(r["msg"], "media", None):
                    await client.send_file(event.chat_id, r["msg"].media, caption=r.get("name") or None)
                else:
                    await client.forward_messages(event.chat_id, r["msg"])
                await asyncio.sleep(0.4)
            return f"تعداد {len(results)} مورد در کانال «{target.name}» پیدا شد و مستقیماً فوروارد شد."

        elif name in ("fetch_and_forward_movie", "download_movie_or_file"):
            target = args.get("target", "").strip()
            quality = args.get("quality")
            audio = args.get("audio")
            season = args.get("season")
            episode = args.get("episode")
            if not target:
                return "خطا: عنوان یا لینک مشخص نشده."
            from services.media import ytsummary
            if ytsummary.extract_youtube_id(target):
                from services.media import ytdownload
                try:
                    q_val = int(quality) if quality else 720
                except Exception:
                    q_val = 720
                return await ytdownload.download_youtube_video(client, target, quality=q_val, event=event, status=status)
            if status:
                try:
                    await status.edit(f"🎬 در حال بررسی و دریافت «{target}»...")
                except Exception:
                    pass

            from services.media import media_flow
            raw_text = getattr(event, "raw_text", "") or getattr(event, "message", "") or ""
            if not audio and raw_text:
                detected_a = media_flow.extract_audio(raw_text)
                if detected_a:
                    audio = detected_a
            if not quality and raw_text:
                detected_q = media_flow.extract_quality(raw_text)
                if detected_q:
                    quality = detected_q
            if season is None and raw_text:
                detected_s = media_flow.extract_season(raw_text)
                if detected_s is not None:
                    season = detected_s
            if episode is None and raw_text:
                detected_e = media_flow.extract_episode(raw_text)
                if detected_e is not None:
                    episode = detected_e

            query_parts = [target]
            if season is not None:
                query_parts.append(f"فصل {season}")
            if episode is not None:
                query_parts.append(f"قسمت {episode}" if str(episode) != "all" else "کل فصل")
            if quality:
                query_parts.append(f"کیفیت {quality}")
            if audio:
                query_parts.append("زیرنویس" if audio == "subtitled" else "دوبله")
            query_str = " ".join(query_parts)

            req_override = {
                "title": target,
                "quality": int(quality) if quality and str(quality).isdigit() else (quality if quality else None),
                "audio": audio,
                "season": int(season) if season and str(season).isdigit() else (season if season else None),
                "episode": episode
            }

            import bot
            ok, res_msg = await media_flow.smart_fetch_media(
                client, event, status, query_str, bot.pending, req_override=req_override
            )
            return res_msg

        elif name == "search_google_images":
            query = args.get("query", "").strip()
            count = int(args.get("count", 3) or 3)
            count = max(1, min(count, 5))
            if not query:
                return "خطا: موضوع عکس مشخص نشده."
            if status:
                await status.edit(f"🖼 در حال جستجوی تصاویر «{query}»...")
            import bot
            msg_res = await bot.send_images(event, query, limit=count)
            return f"نتیجه ارسال تصاویر: {msg_res}"

        elif name == "manage_memory":
            if not getattr(event, "out", False):
                owner_str = f" ({config.OWNER_NAME})" if config.OWNER_NAME else ""
                return f"خطای دسترسی: حافظه و قوانین دستیار فقط توسط صاحب اکانت{owner_str} قابل تغییر است و اشخاص دیگر اجازه تعیین قانون یا ذخیره حافظه را ندارند."
            
            # استخراج قطعی و امن فضای حافظه از کانتکست معتبر رویداد تلگرام (پیشگیری از نشت و جعل شناسه توسط مدل)
            scope_id = memory.get_event_memory_scope(event)
            act = args.get("action", "")
            fact = args.get("fact", "").strip()
            
            if act == "add":
                if not fact:
                    return "خطا: متنی برای ذخیره داده نشد."
                import bot
                chat_key = str(event.chat_id)
                bot.pending[chat_key] = {
                    "kind": "confirm_add_memory",
                    "fact": fact,
                    "scope_id": scope_id,
                    "chat_id": event.chat_id,
                    "ts": time.time()
                }
                return f"⚠️ برای ذخیره «{fact}» در حافظه این گفتگو، تایید شما لازم است. لطفاً برای تایید بگویید «آره» یا برای لغو «نه»."
            elif act == "remove":
                if not fact:
                    return "خطا: موضوع برای حذف مشخص نشده."
                removed = memory.remove_memory(fact, scope_id=scope_id)
                if removed:
                    return f"از حافظه این گفتگو پاک شد: {', '.join(removed)}"
                return "موردی شبیه این در حافظه این گفتگو نبود."
            elif act == "list":
                facts = memory.list_facts(scope_id=scope_id)
                if not facts:
                    return "حافظه این گفتگو در حال حاضر خالی است."
                return "چیزهایی که در حافظه این گفتگو ثبت شده است:\n" + "\n".join(f"- {f}" for f in facts)
            elif act == "clear":
                import bot
                chat_key = str(event.chat_id)
                bot.pending[chat_key] = {
                    "kind": "confirm_clear_memory",
                    "scope_id": scope_id,
                    "chat_id": event.chat_id,
                    "ts": time.time()
                }
                return "⚠️ آیا مطمئنید می‌خواهید کل حافظه ماندگار را پاک کنید؟ (بگویید «آره» یا «نه»)"
            elif act == "transfer":
                target_chat = args.get("target_chat", "").strip()
                if not target_chat:
                    return "خطا: گفتگوی مقصد برای انتقال مشخص نشده است."
                target_scope = memory.normalize_scope_id(target_chat)
                transferred = memory.transfer_memory(fact, source_scope_id=scope_id, target_scope_id=target_scope, is_authorized=True)
                if transferred:
                    return f"✅ واقعیت «{transferred.content}» با موفقیت از این گفتگو به گفتگوی مقصد منتقل شد."
                return "خطا: انتقال حافظه ناموفق بود (یا واقعیت در حافظه این گفتگو یافت نشد یا دسترسی نامعتبر است)."
            return "عملیات حافظه نامعتبر است."

        elif name == "manage_channel_membership":
            act = args.get("action", "")
            target = args.get("target", "").strip()
            if not target:
                return "خطا: کانال هدف مشخص نشده است."
            if act == "join":
                if status:
                    await status.edit(f"🔗 در حال عضویت در «{target}»...")
                ok, err = await channels.join_channel(client, target)
                return f"با موفقیت عضو شد به «{target}»." if ok else f"خطا در عضویت: {err}"
            elif act == "leave":
                if status:
                    try:
                        await status.edit(f"🚪 در حال بررسی کانال‌های «{target}»...")
                    except Exception:
                        pass
                dialogs = await channels.find_channels(client, target)
                if not dialogs:
                    return f"کانالی با نام «{target}» پیدا نشد."
                import bot
                chat_key = str(event.chat_id)
                if len(dialogs) == 1:
                    bot.pending[chat_key] = {"kind": "confirm_leave_single", "dialog": dialogs[0], "name": dialogs[0].name}
                    return f"⚠️ برای خروج از کانال «{dialogs[0].name}»، لطفاً تایید کنید. (بگویید «آره» یا «نه»)"
                else:
                    names = "\n".join(f"{i + 1}. {d.name}" for i, d in enumerate(dialogs))
                    bot.pending[chat_key] = {"kind": "leave", "dialogs": dialogs}
                    return f"این کانال‌ها را پیدا کردم:\n{names}\n\nکدام را لفت بزنم؟ بگویید «همه» یا شماره‌ها (مثلاً 1، 3)."
            return "عملیات عضویت نامعتبر است."

        elif name == "manage_folders":
            act = args.get("action", "")
            fname = args.get("folder_name", "").strip()
            cname = args.get("channel_name", "").strip()
            folds = await folders.list_folders(client)
            if act == "list":
                if not folds:
                    return "هنوز هیچ پوشه‌ای در اکانت تلگرام ساخته نشده است."
                return "پوشه‌های موجود در اکانت:\n" + "\n".join(f"- {f['title']}" for f in folds)
            elif act == "delete":
                f = folders.find_folder(folds, fname)
                if not f:
                    return f"پوشه‌ای با نام «{fname}» پیدا نشد."
                import bot
                bot.pending[str(event.chat_id)] = {"kind": "confirm_delete_folder", "folder_id": f, "name": f['title']}
                return f"⚠️ برای حذف پوشه «{f['title']}»، لطفاً تایید کنید. (بگویید «آره» یا «نه»)"
            elif act == "create" or act == "assign":
                if not fname:
                    return "خطا: نام پوشه مشخص نشده."
                dialogs = await channels.find_channels(client, cname) if cname else []
                if not dialogs:
                    return f"کانالی به نام «{cname}» برای قراردادن در پوشه پیدا نشد (تلگرام پوشه خالی قبول نمی‌کند)."
                f = folders.find_folder(folds, fname)
                if f is None:
                    f, err = await folders.create_folder(client, fname, [d.entity for d in dialogs])
                    if err:
                        return f"خطا در ساخت پوشه: {err}"
                    return f"پوشه «{f['title']}» ساخته شد و {len(dialogs)} کانال درون آن قرار گرفت."
                n = await folders.assign_to_folder(client, f, [d.entity for d in dialogs])
                return f"{n} کانال با موفقیت به پوشه «{f['title']}» اضافه شد."
            elif act == "auto_sort":
                import bot
                await bot._do_sort(event, status)
                return "__PENDING_SORT__"
            return "عملیات پوشه نامعتبر است."

        elif name == "manage_important_channels":
            act = args.get("action", "")
            cname = args.get("channel_name", "").strip()
            if act == "list":
                names = briefing.load_important()
                if not names:
                    return "هنوز کانال مهمی ثبت نشده است."
                return "کانال‌های مهم ثبت‌شده برای خلاصه روزانه:\n" + "\n".join(f"- {n}" for n in names)
            elif act in ("add", "remove"):
                if not cname:
                    return "خطا: نام کانال مشخص نشده است."
                import bot
                chat_key = str(event.chat_id)
                action_fa = "افزودن به" if act == "add" else "حذف از"
                bot.pending[chat_key] = {
                    "kind": "confirm_important_channel",
                    "action": act,
                    "channel_name": cname,
                    "ts": time.time(),
                }
                return f"⚠️ برای {action_fa} لیست کانال‌های مهم («{cname}»)، تایید شما لازم است. لطفاً برای تایید بگویید «آره» یا برای لغو «نه»."
            return "عملیات نامعتبر است."

        elif name == "ask_clarification":
            q_text = args.get("question", "").strip()
            if not q_text:
                q_text = "می‌شه دقیق‌تر بگی منظورت چیه تا بتونم کمکت کنم؟"
            return f"__ASK_USER__:{q_text}"

        elif name == "get_daily_briefing":
            if status:
                await status.edit("☀️ در حال گردآوری و تحلیل خلاصه روزانه...")
            report = await briefing.build_briefing(client)
            return report

        elif name == "get_current_datetime":
            return f"امروز {ai._today()} است."

        elif name == "read_webpage":
            url = args.get("url", "").strip()
            if not url:
                return "خطا: آدرس لینک مشخص نشده است."
            if status:
                await status.edit("🌐 در حال باز کردن و مطالعه لینک صفحه وب...")
            from services.search import webreader
            data = await asyncio.to_thread(webreader.fetch_url, url)
            if data.get("error"):
                return f"خطا در باز کردن صفحه وب ({url}): {data['error']}"
            title = data.get("title", "")
            content = data.get("content", "")
            if not content:
                return f"صفحه باز شد اما متن قابل استخراجی نداشت: {title}"
            return f"عنوان صفحه: {title}\nآدرس: {url}\n\nمتن محتوای صفحه:\n{content}"

        elif name == "summarize_youtube_video":
            url = args.get("url", "").strip()
            if not url:
                return "خطا: آدرس یا لینک یوتیوب مشخص نشده است."
            if status:
                try:
                    await status.edit("🎬 در حال دریافت اطلاعات و خلاصه‌سازی ویدیو یوتیوب بدون مصرف حجم...")
                except Exception:
                    pass
            from services.media import ytsummary
            summary = await asyncio.to_thread(ytsummary.summarize_youtube_video, url)
            return summary

        elif name == "get_youtube_video_info":
            url = args.get("url", "").strip()
            if not url:
                return "خطا: آدرس یا لینک یوتیوب مشخص نشده است."
            if status:
                try:
                    await status.edit("🎬 در حال دریافت متادیتا و اطلاعات ویدیوی یوتیوب...")
                except Exception:
                    pass
            from services.media import ytsummary
            return await asyncio.to_thread(ytsummary.get_youtube_video_info, url)

        elif name == "download_youtube_video":
            url = args.get("url", "").strip()
            quality = args.get("quality")
            if not url:
                return "خطا: آدرس یا لینک ویدیوی یوتیوب مشخص نشده است."
            try:
                m_q = re.search(r"\d+", str(quality)) if quality else None
                q_val = int(m_q.group(0)) if m_q else 720
            except Exception:
                q_val = 720
            from services.media import ytdownload
            return await ytdownload.download_youtube_video(client, url, quality=q_val, event=event, status=status)

        elif name == "download_social_media":
            url = args.get("url", "").strip()
            if not url:
                return "خطا: لینک دانلود مشخص نشده است."
            from services.media import socialdl
            return await socialdl.download_social(client, url, event=event, status=status)

        elif name == "send_voice_note":
            text = args.get("text", "").strip()
            if not text:
                return "خطا: متن ویس مشخص نشده است."
            if status:
                try:
                    await status.edit("🎙 در حال ضبط ویس...")
                except Exception:
                    pass
            import os
            from services.voice import voice
            os.makedirs(config.DOWNLOAD_DIR, exist_ok=True)
            ts = int(time.time() * 1000)
            mp3 = os.path.join(config.DOWNLOAD_DIR, f"tts_{ts}.mp3")
            ogg = os.path.join(config.DOWNLOAD_DIR, f"tts_{ts}.ogg")
            ok = await voice.speak(text, mp3, client=client)
            converted = await asyncio.to_thread(voice.to_ogg, mp3, ogg) if ok else False

            # اگر تولید ویس یا تبدیل به ogg ناموفق بود، فال‌بک اضطراری مستقیم با Edge-TTS انجام می‌شود
            if not ok or not converted or not os.path.exists(ogg) or os.path.getsize(ogg) < 1000:
                log.warning("Primary voice synthesis failed or produced invalid ogg. Executing direct Edge-TTS emergency fallback...")
                try:
                    import edge_tts
                    clean_fallback = voice.prepare_for_tts(text)
                    c = edge_tts.Communicate(clean_fallback, "fa-IR-FaridNeural", rate="+5%")
                    await c.save(mp3)
                    converted = await asyncio.to_thread(voice.to_ogg, mp3, ogg)
                    ok = converted and os.path.exists(ogg) and os.path.getsize(ogg) >= 1000
                except Exception as fb_err:
                    log.error("Emergency Edge-TTS fallback failed: %s", fb_err)
                    ok = False

            if ok and os.path.exists(ogg) and os.path.getsize(ogg) >= 1000:
                reply_to_id = getattr(event, "message", None)
                reply_id = reply_to_id.id if reply_to_id else getattr(event, "id", None)
                try:
                    vmsg = await client.send_file(event.chat_id, ogg, voice_note=True, reply_to=reply_id)
                    import bot
                    bot.self_sent.add(vmsg.id)
                except Exception as send_err:
                    try:
                        os.remove(mp3)
                        os.remove(ogg)
                    except Exception:
                        pass
                    return f"❌ خطا در ارسال تلگرام: ویس با موفقیت ضبط شد اما ارسال آن به چت با خطا مواجه شد ({send_err})."
                try:
                    os.remove(mp3)
                    os.remove(ogg)
                except Exception:
                    pass
                if status:
                    try:
                        await status.delete()
                    except Exception:
                        pass
                return f"__VOICE_SENT__:{text}"
            return "❌ خطا در تولید ویس: فایل صوتی تولید نشد یا فرآیند تبدیل به فرمت صدا ناموفق بود."

        elif name == "create_or_update_skill":
            if not getattr(event, "out", False):
                owner_str = f" ({config.OWNER_NAME})" if config.OWNER_NAME else ""
                return f"خطای دسترسی: ساخت و تغییر اسکیل‌ها فقط مختص صاحب اکانت{owner_str} است."
            from ai_engine import skills_manager
            s_name = args.get("name", "")
            desc = args.get("description", "")
            params = args.get("parameters") or {"type": "object", "properties": {}}
            code = args.get("python_code", "")

            err = skills_manager.validate_skill(s_name, code)
            if err:
                return f"❌ {err}"

            import bot
            preview_code = code if len(code) <= 3500 else code[:3500] + "\n\n... (کد طولانی‌تر است؛ نسخه کامل پس از تایید ذخیره می‌شود)"
            preview = (
                f"🛠 **اسکیل پیشنهادی «{s_name}»**\n"
                f"▫️ توضیح: {desc or '—'}\n\n"
                f"```python\n{preview_code}\n```\n\n"
                f"ساخته و ثبت بشه؟ بگو «آره» یا «نه»."
            )
            sent_m = await client.send_message(event.chat_id, preview)
            bot.self_sent.add(sent_m.id)

            bot.pending[str(event.chat_id)] = {
                "kind": "confirm_skill",
                "name": s_name,
                "description": desc,
                "parameters": params,
                "python_code": code,
            }
            return "__PENDING_SKILL__"

        elif name == "list_skills":
            from ai_engine import skills_manager
            all_s = skills_manager.get_all_skills()
            if not all_s:
                return "هنوز هیچ اسکیل داینامیکی در سیستم ثبت نشده است."
            lines = ["🛠 **اسکیل‌ها و مهارت‌های داینامیک ثبت‌شده کاپری:**"]
            for k, v in all_s.items():
                lines.append(f"• **{k}**: {v.get('description', '')}")
            return "\n".join(lines)

        elif name == "delete_skill":
            from ai_engine import skills_manager
            s_name = args.get("name", "")
            return skills_manager.delete_skill(s_name)

        elif name == "draft_and_send_message":
            from services.social import drafter
            target_str = args.get("target_contact", "").strip()
            intent = args.get("message_intent", "").strip()
            tone = args.get("tone", "صمیمی و محترمانه").strip()

            if status:
                try:
                    await status.edit("✍️ در حال جستجوی مخاطب و تنظیم پیش‌نویس پیام...")
                except Exception:
                    pass

            target_entity, target_name = await drafter.resolve_target(client, event, target_str)
            if not target_entity:
                return f"❌ مخاطبی با نام یا مشخصات «{target_str}» در چت‌ها و مخاطبین تلگرام یافت نشد."

            draft_text = await drafter.craft_message(target_name, intent, tone)
            msg_preview = (
                f"✍️ **پیش‌نویس پیام برای «{target_name}»:**\n"
                f"━━━━━━━━━━━━━━━\n"
                f"«{draft_text}»\n"
                f"━━━━━━━━━━━━━━━\n"
                f"اگر تایید می‌کنی، روی این پیام ریپلای بزن و بگو «بفرست» (برای لغو بگو «لغو»)."
            )
            preview_id = None
            if status:
                try:
                    await status.edit(msg_preview)
                    preview_id = status.id
                except Exception:
                    pass
            if not preview_id:
                sent_m = await client.send_message(event.chat_id, msg_preview)
                preview_id = sent_m.id

            drafter.set_pending_draft(event.chat_id, preview_id, target_entity, target_name, draft_text)
            return f"__DRAFT_SENT__:{target_name}"

        elif name == "roast_target":
            from services.social import roast
            style = args.get("style", "سنگین و دندان‌شکن")
            ok = await roast.handle_roast(client, event, style, status)
            if ok:
                return "__ROAST_SENT__"
            return "روست ارسال نشد؛ مطمئن شو روی پیام طرف ریپلای زدی."

        elif name == "vibe_check":
            from services.social import vibecheck
            q = args.get("question", "تحلیل وایب چت و نیت طرف")
            report = await vibecheck.analyze_chat_vibe(client, event, q)
            return report

        elif name == "generate_meme":
            from services.social import memegen
            cap = args.get("caption", "")
            ok = await memegen.handle_meme(client, event, cap, status)
            if ok:
                return "__MEME_SENT__"
            return "تولید میم انجام نشد؛ مطمئن شو روی پیام یا عکس طرف ریپلای زدی."

        elif name == "manage_dnd":
            if not getattr(event, "out", False):
                return "خطای دسترسی: تغییر حالت سرشلوغ (DND) فقط توسط صاحب اکانت مجاز است."
            from services.social import dnd
            act = args.get("action", "status")
            if act == "disable":
                dnd.deactivate_dnd()
                return "حالت سرشلوغ (DND) خاموش شد و کاپری به حالت عادی بازگشت."
            elif act == "status":
                info = dnd.get_dnd_info()
                if dnd.is_dnd_active():
                    return f"حالت DND فعال است. علت: {info.get('reason')}، تا: {info.get('until_str')}، پاسخ‌های خودکار: {info.get('replies_count')}"
                return "حالت DND غیرفعال است."
            elif act == "enable":
                reason = args.get("reason", "مشغله شخصی")
                time_expr = args.get("duration_or_time", "")
                target_dt, until_str = dnd.parse_time_expression(time_expr) if time_expr else (None, "")
                until_ts = target_dt.timestamp() if target_dt else None
                dnd.activate_dnd(reason, until_ts=until_ts, until_str=until_str)
                return f"حالت سرشلوغ (DND) با موفقیت فعال شد. علت: {reason}، مدت اعتبار: {until_str or 'تا اعلام لغو توسط شما'}."

        elif name == "manage_reminders":
            if not getattr(event, "out", False):
                return "خطای دسترسی: مدیریت یادآورها فقط توسط صاحب اکانت مجاز است."
            from services.social import dnd
            act = str(args.get("action", "list")).strip().lower()
            if act in ("clear", "delete", "remove", "cancel"):
                rems = dnd.load_reminders()
                if not rems:
                    return "هیچ یادآور فعالی در صف وجود ندارد."
                idx = args.get("index")
                if idx is not None:
                    try:
                        idx_num = int(idx)
                        if 1 <= idx_num <= len(rems):
                            target = rems[idx_num - 1]
                            dnd.remove_reminder(target.get("id"))
                            return f"یادآور شماره {idx_num} با موفقیت پاک شد: {target.get('text')}"
                    except Exception:
                        pass
                cnt = dnd.clear_all_reminders()
                return f"تمام یادآورهای فعال ({cnt} مورد) با موفقیت پاک شدند."
            elif act == "list":
                rems = dnd.load_reminders()
                if not rems:
                    return "هیچ یادآور فعالی در صف وجود ندارد."
                return "یادآورهای فعال:\n" + "\n".join(f"{idx}. {r['text']} (زمان: {r['due_str']})" for idx, r in enumerate(rems, start=1))
            elif act == "add":
                rem_text = args.get("text", "").strip()
                time_expr = args.get("time_expression", "").strip()
                if not rem_text or not time_expr:
                    return "خطا: موضوع و زمان یادآوری باید مشخص باشد."
                target_dt, due_str = dnd.parse_time_expression(time_expr)
                if not target_dt:
                    return "خطا: فرمت زمان یادآوری نامفهوم بود."
                dnd.add_reminder(rem_text, target_dt.timestamp(), due_str)
                return f"یادآور با موفقیت ثبت شد: «{rem_text}» برای {due_str}."

        elif name == "organize_saved_messages":
            if not getattr(event, "out", False):
                return "⛔ عدم دسترسی: سازمان‌دهی صندوق سیو مسیج فقط توسط مالک ربات مجاز است."
            from services.telegram import vault
            raw_limit = args.get("limit", 20)
            try:
                limit = int(raw_limit)
            except (ValueError, TypeError):
                limit = 20

            async def _cb(t):
                if status:
                    try:
                        await status.edit(t)
                    except Exception:
                        pass

            rep = await vault.organize_saved_messages(client, limit=limit, status_callback=_cb)
            total = rep.get("total", 0)
            if total == 0:
                return rep.get("message", "هیچ پیامی برای سازمان‌دهی در سیو مسیج یافت نشد.")
            topics_summary = "\n".join(f"- {t}: {c} پیام" for t, c in rep.get("by_topic", {}).items())
            link = rep.get("vault_link", "")
            link_txt = f"\nلینک گروه: {link}" if link else ""
            return f"سازمان‌دهی با موفقیت انجام شد. مجموع {total} پیام در تاپیک‌های زیر دسته‌بندی شدند:\n{topics_summary}{link_txt}"

        elif name == "get_vault_info":
            if not getattr(event, "out", False):
                return "⛔ عدم دسترسی: مشاهده اطلاعات صندوق فقط توسط مالک ربات مجاز است."
            from services.telegram import vault
            info = vault.get_vault_info()
            gid = info.get("group_id")
            if not gid:
                return "هنوز صندوق هوشمند ایجاد نشده است."
            total = info.get("total_organized_count", 0)
            topics = info.get("topics", {})
            link = info.get("group_invite_link", "")
            topics_str = ", ".join(t.get("title", k) for k, t in topics.items()) if topics else "بدون تاپیک"
            return f"صندوق هوشمند فعال است. شناسه گروه: {gid} | کل پیام‌های سازمان‌دهی شده: {total} | تاپیک‌ها: {topics_str} | لینک: {link or 'نامشخص'}"

        elif name == "purge_vault":
            if not getattr(event, "out", False):
                return "⛔ این قابلیت فقط برای صاحب اکانت فعال است."
            from services.telegram import vault
            raw_limit = args.get("limit", -1)
            try:
                limit = int(raw_limit)
            except (ValueError, TypeError):
                limit = -1

            async def _cb(t):
                if status:
                    try:
                        await status.edit(t)
                    except Exception:
                        pass

            res = await vault.purge_vault_messages(client, limit=limit, status_callback=_cb)
            return f"پاک‌سازی صندوق انجام شد: {res.get('message', '')}"

        elif name == "send_sticker":
            emotion = (args.get("emotion", "") or "").strip()
            if not emotion:
                return "خطا: احساس استیکر مشخص نشده است."
            from services.social import stickers
            lib = await stickers.ensure_library(client)
            if not lib:
                err = stickers.last_error()
                if err:
                    return f"کتابخانه استیکر خالی است؛ پک در دسترس نبود. خطا: {err}"
                return "کتابخانه استیکر خالی است؛ پک استیکر در دسترس نبود."
            if await stickers.send_sticker(client, event.chat_id, emotion):
                return f"استیکر «{emotion}» ارسال شد."
            return f"استیکر مناسبی برای احساس «{emotion}» در پک یافت نشد."

        # Execute runtime dynamic Hermes skill
        from ai_engine import skills_manager
        if name in skills_manager.get_all_skills():
            from core import config
            allow_skills = getattr(config, "ALLOW_SKILL_CREATION", False) or getattr(skills_manager, "ALLOW_SKILL_CREATION", False)
            if not allow_skills:
                return "⛔ اجرای اسکیل‌های متفرقه در تنظیمات سیستم غیرفعال است (ALLOW_SKILL_CREATION=0)."
            if tainted:
                return "⛔ خطای امنیتی: اجرای اسکیل‌های پویا در وضعیت Taint مسدود است."
            if status:
                try:
                    await status.edit(f"⚙️ در حال اجرای اسکیل «{name}»...")
                except Exception:
                    pass
            return await skills_manager.execute_skill(name, args, client, event)

        return f"ابزار ناشناخته: {name}"
    except Exception as e:
        return f"خطا در اجرای ابزار {name}: {e}"
