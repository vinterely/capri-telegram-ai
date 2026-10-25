import asyncio
import logging
import re
from typing import Optional, Tuple

from ai_engine import ai

log = logging.getLogger("roast")

ROAST_KEYWORDS = (
    "جوابش رو بده", "جوابشو بده", "ضایعش کن", "ضایع کن", "روستش کن", "روست کن",
    "برین بهش", "بشورش", "تیکه بنداز", "تیکه سنگین", "دندون شکن", "دندون‌شکن",
    "ترولش کن", "ترول کن", "حالشو بگیر", "حالش رو بگیر", "با خاک یکسانش کن",
    "قهوه‌ایش کن", "قهوه ایش کن", "بمالش", "لالش کن", "خفه‌ش کن", "خفش کن"
)


def is_roast_request(text: str) -> bool:
    t = (text or "").lower()
    return any(k in t for k in ROAST_KEYWORDS)


async def generate_roast(target_name: str, target_text: str, user_prompt: str = "") -> str:
    """تولید حاضر‌جوابی یا روست فوق‌العاده تیز، بی‌رحمانه و مدرن فارسی خطاب به طرف مقابل."""
    target_clean = target_name or "طرف مقابل"
    prompt = (
        "تو بی رحم ترین شخصیت داری باید طرف نابود کنی ببین چی میگه بعد بکشش با کلمات\n"
        f"در چت تلگرام، شخصی به نام «{target_clean}» این پیام را داده است:\n"
        f"پیام {target_clean}: «{target_text}»\n\n"
        f"دستور و خواسته: {user_prompt or 'یه تیکه بی رحمانه بنداز که طرف دیگه جرعت نکنه حتی ریپلای کنه مثلا برو درتو بزار  یا سیک کن بسته به جملش واکنش متفاوت بده'}\n\n"
        "قوانین حیاتی و بدون مصالحه:\n"
        f"۱. مخاطب و هدف شلیک مستقیم تو دقیقاً همان شخص ({target_clean}) است؛ به هیچ عنوان به کاربری که بهت دستور داده تیکه نینداز!\n"
        "۲. طرف نابود کن اگه فحش داده بود خشاب بکش روش فحش بده تو ازادی.\n"
        "۳.  روست کن تخریب شخصیتی و بولی. برگ برنده تو بولی کردنه\n"
        "۴. جواب باید ۱ الی ۲ جمله کوتاه، تند، مدرن، فوق‌العاده بُرنده و کوبنده باشد (Punchline ناب تلگرامی/توییتری).\n"
        "۵. از کلمات رکیک استفاده میتونی کنی خیلی بی ملاحضه بزن خاکشیر کن طرفو فقط فحش خانوادگی نده.\n"
        "۶. فقط و فقط متن پاسخ نهایی را بنویس بدون هیچ مقدمه، نقل‌قول، پرانتز یا علامت گیومه."
    )
    try:
        res = await asyncio.to_thread(ai.ask_direct, prompt)
        clean = (res or "").strip().strip("«»\"'")
        if clean:
            return clean
    except Exception as e:
        log.warning(f"AI roast generation error: {e}. Using savage fallback punchline.")

    import random
    _FALLBACK_ROASTS = [
        "سطح حرفات جوری پایینه که حتی اینترنت منم قطع شد که نبینمش! 🤡",
        "کاش یکم از اون تایمی که برای فکر کردن نذاشتی، برای سکوت کردن استفاده می‌کردی! 🤡",
        "اعتماد به نفست رو کاش پراید داشت، الان پرواز می‌کرد! 🤡",
        "من رباتم ولی از حرفت ارور مغزی ۴۰۴ گرفتم، برو یه دور سیستم‌عامل مغزتو ریست کن! 🤡",
        "دلقک‌بازی هم یه هنره ولی تو حتی استعداد اونو هم نداری! 🤡",
        "حرف زدن بلد نیستی حداقل سکوت کردن رو تمرین کن رفیق! 🤡",
    ]
    return random.choice(_FALLBACK_ROASTS)


async def handle_roast(client, event, question: str, status=None) -> bool:
    """
    بررسی و اجرای روست:
    پیام طرف مقابل را پیدا می‌کند، روست هوشمندانه می‌سازد و دقیقاً روی پیام طرف مقابل ریپلای می‌زند.
    """
    reply_id = getattr(event, "reply_to_msg_id", None)
    if not reply_id:
        if status:
            await status.edit("❌ برای روست کردن یا جواب دندون‌شکن، باید روی پیام اون شخص ریپلای بزنی!")
        return False

    try:
        target_msg = await client.get_messages(event.chat_id, ids=reply_id)
        if not target_msg:
            if status:
                await status.edit("❌ نتونستم پیام طرف رو پیدا کنم.")
            return False

        target_name = "رفیق"
        if target_msg.sender:
            target_name = getattr(target_msg.sender, "first_name", "") or getattr(target_msg.sender, "title", "رفیق")

        target_text = target_msg.message or ""
        if not target_text and target_msg.media:
            target_text = "[یک مدیا یا استیکر فرستاده]"

        if status:
            try:
                await status.edit(f"🔥 در حال پر کردن خشاب برای «{target_name}»...")
            except Exception:
                pass

        roast_text = await generate_roast(target_name, target_text, question)

        # ارسال پاسخ مستقیماً به صورت ریپلای روی پیام خودِ طرف مقابل
        await client.send_message(event.chat_id, roast_text, reply_to=target_msg.id)

        # حذف پیام وضعیت (status) تا چت خلوت بماند و فقط روست روی پیام طرف دیده شود
        if status:
            try:
                await status.delete()
            except Exception:
                pass

        return True
    except Exception as e:
        log.error(f"Error handling roast: {e}")
        if status:
            try:
                await status.edit(f"❌ خطا در روست: {e}")
            except Exception:
                pass
        return False
