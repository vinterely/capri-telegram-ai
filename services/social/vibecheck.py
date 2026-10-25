import asyncio
import logging
from typing import Optional

from ai_engine import ai

log = logging.getLogger("vibecheck")

VIBE_KEYWORDS = (
    "تحلیل کن", "تحلیل چت", "وایب چت", "وایبش چیه", "وایب این", "نیتش چیه",
    "روانشناسی", "روان‌شناسی", "داره دروغ میگه", "راست میگه", "چت رو بررسی کن",
    "فازش چیه", "حسش چیه", "تحلیل پیام", "زیرمتن", "کالبدشکافی کن",
    "کالبد شکافی", "پشت پرده پیام", "داره بازیم میده", "تله روانی", "تستش کن"
)


def is_vibe_request(text: str) -> bool:
    t = (text or "").lower()
    return any(k in t for k in VIBE_KEYWORDS)


async def analyze_chat_vibe(client, event, question: str) -> str:
    """تحلیل روان‌شناختی پیشرفته پیام‌ها، زیرمتن پنهان، زبان بدن دیجیتال و ارائه سناریوهای حرکت برنده."""
    reply_id = getattr(event, "reply_to_msg_id", None)
    chat_id = event.chat_id

    messages_flow = []
    target_name = "مخاطب"

    if reply_id:
        try:
            target_msg = await client.get_messages(chat_id, ids=reply_id)
            if target_msg and target_msg.sender:
                target_name = getattr(target_msg.sender, "first_name", "") or getattr(target_msg.sender, "title", "مخاطب")
        except Exception:
            pass

    # خواندن ۲۰ پیام اخیر برای درک دقیق دینامیک و ریتم مکالمه
    try:
        async for m in client.iter_messages(chat_id, limit=25):
            if not m:
                continue
            sender_name = "مخاطب"
            if m.out:
                sender_name = "من (کاربر)"
            elif m.sender:
                sender_name = getattr(m.sender, "first_name", "مخاطب")
            txt = m.message or ("[یک عکس، وویس یا مدیا]" if m.media else "")
            if txt:
                messages_flow.append(f"{sender_name}: {txt}")
    except Exception as e:
        log.warning(f"Error reading chat flow for vibecheck: {e}")

    messages_flow.reverse()
    context_text = "\n".join(messages_flow[-20:])

    prompt = (
        "تو یک روان‌شناس تاریک، تحلیلگر ارشد زبان بدن دیجیتال و متخصص رفتارشناسی روابط انسانی و مذاکره هستی.\n"
        f"گفتگوی زیر در تلگرام با شخصی به نام «{target_name}» رخ داده است:\n\n"
        f"گزیده مکالمه اخیر:\n{context_text}\n\n"
        f"دستور و سوال کاربر: «{question}»\n\n"
        "وظیفه تو: کالبدشکافی فوق‌العاده تیزبینانه، بدون تعارف، روان‌شناختی، عمیق و کاربردی به زبان فارسی با ساختار دقیق زیر:\n\n"
        f"🧠 **کالبدشکافی پیشرفته و پروفایلینگ روان‌شناختی («{target_name}»):**\n\n"
        "🎭 **۱. پوزیشن روانی و استراتژی ناخودآگاه (Psychological Posture):**\n"
        "- طرف در چه موضعی قرار دارد؟ (مثلاً موضع برتری فیک، حالت دفاعی منفعل، قربانی‌نمایی/مظلوم‌نمایی، یا ایگنور کنترل‌شده برای تست کردن کاربر)\n\n"
        "🔍 **۲. رمزگشایی زیرمتن عریان (Unfiltered Subtext):**\n"
        "- ظاهر کلمات طرف: ...\n"
        "- ترجمه حقیقت پشت پرده (چیزی که واقعاً در مغزش می‌گذرد ولی به زبان نمی‌آورد): ...\n\n"
        "⚠️ **۳. رادار دستکاری روانی و پرچم‌های خطر (Manipulation Radar):**\n"
        "- بررسی وجود گس‌لایتینگ (Gaslighting)، القای حس گناه (Guilt-tripping)، شیت‌تست (Shit Test برای سنجش ضعف‌های کاربر)، یا فرافکنی.\n\n"
        "📊 **۴. دماسنج تعادل قدرت و سرمایه‌گذاری (Power Balance):**\n"
        "- بررسی اینکه دست بالا با چه کسی است، چه کسی انرژی بیشتری خرج می‌کند و تعادل روانی مکالمه کجاست.\n\n"
        "♟️ **۵. سناریوهای حرکت برنده و شطرنجی (Grandmaster Power Moves):**\n"
        "• **تاکتیک اول (بی‌تفاوتی شیک و خلع سلاح روانی):**\n"
        "  پاسخ آماده: `«متن دقیق برای کپی»`\n"
        "• **تاکتیک دوم (پاسخ معکوس و انداختن توپ به زمین حریف):**\n"
        "  پاسخ آماده: `«متن دقیق برای کپی»`\n\n"
        "نکته: لحن باید صریح، به شدت باهوش، کاریزماتیک، واقع‌بین و عاری از تعارفات کلیشه‌ای باشد."
    )

    try:
        res = await asyncio.to_thread(ai.ask_direct, prompt)
        return res
    except Exception as e:
        return f"❌ خطا در تحلیل روان‌شناختی چت: {e}"
