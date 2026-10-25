"""ماژول ناوبری هوشمند دکمه‌های شیشه‌ای ربات‌های دانلود با هوش مصنوعی.

این ماژول گزینه‌ها و دکمه‌های شیشه‌ای ربات‌های تلگرام (دانلود فیلم، سریال و مدیا)
را به هوش مصنوعی می‌دهد تا بر اساس درخواست کاربر (عنوان، فصل، قسمت، کیفیت، دوبله/زیرنویس)
بهترین دکمه را برای کلیک کردن انتخاب کند یا وضعیت اتمام/ادامه را هدایت نماید.
"""

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional

from ai_engine import ai

log = logging.getLogger("ai_nav")

_PERSIAN_DIGITS = {
    '۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4',
    '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9'
}
 
BACK_BUTTON_HINTS = (
    "برگشت", "بازگشت", "منوی قبل", "صفحه قبل", "منوی اصلی",
    "back", "return", "main menu", "🔙", "⬅️", "◀️", "↩️"
)


def is_back_button(text: str) -> bool:
    """تشخیص آیا دکمه از نوع بازگشت/منوی اصلی/عقبگرد است یا خیر."""
    t = (text or "").strip().lower()
    if not t:
        return False
    # اگر آیکون‌های بازگشت وجود دارد
    if any(icon in t for icon in ("🔙", "⬅️", "◀️", "↩️")):
        return True
    exact_hints = ("برگشت", "بازگشت", "منوی قبل", "صفحه قبل", "منوی اصلی", "back", "return", "main menu")
    if t in exact_hints or any(t == f"[{h}]" for h in exact_hints):
        return True
    if any(h in t for h in ("منوی قبل", "صفحه قبل", "منوی اصلی", "بازگشت به منو", "برگشت به منو", "بازگشت به منوی قبل")):
        return True
    if any(h in t for h in ("برگشت", "بازگشت", "back")) and len(t) <= 15:
        if not any(k in t for k in ("فیلم", "قسمت", "فصل", "دانلود", "کیفیت", "1080", "720", "480", "series", "movie")):
            return True
    return False


NAV_SYSTEM_PROMPT = (
    "تو یک موتور فوق‌هوشمند ناوبری دکمه‌های شیشه‌ای (Inline Buttons) در ربات‌های تلگرام برای دانلود فیلم و سریال هستی.\n"
    "وظیفه تو این است که با بررسی متن پیام ربات، درخواست کاربر، وضعیت فایل‌های دریافت شده و فهرست دکمه‌های موجود، "
    "دقیقاً مشخص کنی کدام دکمه باید کلیک شود تا فایل به دست کاربر برسد.\n\n"
    "قوانین اکید تصمیم‌گیری:\n"
    "۱. ممنوعیت دکمه برگشت: هرگز دکمه‌های «برگشت»، «بازگشت»، «منوی قبل»، «منوی اصلی»، «Back» یا آیکون‌های 🔙 و ⬅️ را انتخاب نکن! هدف تو پیشروی به سمت دانلود است نه عقبگرد.\n"
    "۲. انتخاب نسخه صوت/زیرنویس: اگر کاربر زیرنویس خواسته است (subtitled)، دکمه زیرنویس (زیرنویس چسبیده / SoftSub / HardSub / زیرنویس) را انتخاب کن و هرگز دوبله را انتخاب نکن. اگر کاربر دوبله خواسته، دکمه دوبله را انتخاب کن.\n"
    "۳. انتخاب کیفیت: اگر منو شامل کیفیت‌ها است، دکمه دقیقاً مطابق با کیفیت درخواستی کاربر (مثلاً 480p یا 720p یا 1080p) را انتخاب کن. هرگز روی منوی کیفیت دکمه برگشت نزن!\n"
    "۴. انتخاب فصل و قسمت: اگر منوی انتخاب فصل است، فصل خواسته شده را انتخاب کن. اگر منوی قسمت‌ها است، قسمت مورد نظر کاربر را انتخاب کن.\n"
    "۵. دریافت فایل: اگر دکمه «دریافت فایل»، «دانلود»، «Download» یا لینک دانلود مستقیم وجود دارد، آن را انتخاب کن.\n"
    "۶. اگر کل فصل خواسته شده و قسمت فعلی دریافت شده، دکمه «بعدی» یا «Next» را بزن.\n"
    "۷. اتمام: فقط زمانی عدد 0 را بفرست که تمام فایل‌های درخواستی دریافت شده باشند یا واقعاً هیچ گزینه‌ای برای دانلود باقی نمانده باشد.\n\n"
    "خروجی: فقط و فقط یک عدد (شماره گزینه مثلاً 1 یا 2 یا 0 برای اتمام) بدون هیچ متن، توضیح یا کلمه اضافه."
)


def format_buttons_list(buttons: List[Any]) -> str:
    """فرمت‌بندی دکمه‌ها به صورت یک لیست شماره‌دار برای هوش مصنوعی."""
    lines = []
    for idx, b in enumerate(buttons, start=1):
        txt = (getattr(b, "text", "") or "").strip()
        lines.append(f"{idx}. [{txt}]")
    return "\n".join(lines)


def parse_choice(raw: str, buttons: List[Any]) -> Optional[int]:
    """تبدیل پاسخ مدل به ایندکس 0-based دکمه. 0 یا خروجی نامعتبر -> None."""
    if not raw:
        return None
    s = raw.strip()
    for p, a in _PERSIAN_DIGITS.items():
        s = s.replace(p, a)

    count = len(buttons)

    # ۱. استخراج عدد مستقیم
    m = re.search(r'\b\d+\b', s) or re.search(r'\d+', s)
    if m:
        val = int(m.group(0))
        if 1 <= val <= count:
            return val - 1
        if val == 0:
            return None

    # ۲. تطبیق متن دکمه در صورت بازگرداندن متن به جای عدد
    low = s.lower()
    for i, b in enumerate(buttons):
        t = (getattr(b, "text", "") or "").strip().lower()
        if len(t) >= 3 and t in low:
            return i

    return None


def pick_button_sync(
    buttons: List[Any],
    bot_message: str,
    req: Dict[str, Any],
    state: Dict[str, Any]
) -> Optional[int]:
    """انتخاب همگام دکمه مناسب از میان دکمه‌های موجود با هوش مصنوعی."""
    if not buttons:
        return None
    if len(buttons) == 1:
        return 0

    # تفکیک دکمه‌های رو به جلو از دکمه‌های بازگشت/منوی قبل
    forward_candidates = [
        (orig_idx, b) for orig_idx, b in enumerate(buttons)
        if not is_back_button(getattr(b, "text", ""))
    ]
    if forward_candidates:
        active_candidates = forward_candidates
    else:
        active_candidates = list(enumerate(buttons))

    cand_buttons = [b for _, b in active_candidates]
    numbered_buttons = format_buttons_list(cand_buttons)

    title = req.get("title") or "فیلم / سریال"
    season = req.get("season")
    episode = req.get("episode")
    quality = req.get("quality") or 720
    audio_req = req.get("audio")

    if audio_req == "subtitled":
        audio_str = "زیرنویس (فقط زیرنویس فارسی / Subtitled انتخاب شود)"
    elif audio_req == "dubbed":
        audio_str = "دوبله (فقط نسخه دوبله فارسی / Dubbed انتخاب شود)"
    else:
        audio_str = audio_req or "دوبله یا زیرنویس"

    s_str = f"فصل {season}" if season else "مشخص نشده (اولین یا جدیدترین)"
    ep_str = "تمام قسمت‌ها (کل فصل)" if episode == "all" else (f"قسمت {episode}" if episode else "تمام قسمت‌ها / نامشخص")
    files_count = state.get("files_count", 0)
    last_action = state.get("last_action", "شروع تعامل")

    prompt = (
        f"پیام دریافتی از ربات دانلود:\n"
        f"«{(bot_message or '').strip()[:400]}»\n\n"
        f"درخواست کاربر:\n"
        f"- عنوان اثر: {title}\n"
        f"- فصل: {s_str}\n"
        f"- قسمت: {ep_str}\n"
        f"- کیفیت: {quality}p\n"
        f"- نسخه: {audio_str}\n\n"
        f"وضعیت فعلی:\n"
        f"- تعداد فایل‌های دریافت شده تا اکنون: {files_count}\n"
        f"- آخرین اقدام: {last_action}\n\n"
        f"دکمه‌های موجود:\n"
        f"{numbered_buttons}\n\n"
        f"دستور: کدام دکمه را باید بزنم؟ فقط یک عدد بنویس (یا 0 اگر کار تمام است):"
    )

    try:
        raw = ai.ask_direct(prompt, system=NAV_SYSTEM_PROMPT)
    except Exception as e:
        log.warning(f"Error in ai_nav ask_direct: {e}")
        raw = ""

    sub_choice = parse_choice(raw, cand_buttons)
    if sub_choice is not None and 0 <= sub_choice < len(active_candidates):
        orig_choice = active_candidates[sub_choice][0]
    else:
        orig_choice = None

    log.info(f"[ai_nav] Model response: {raw!r} -> Choice index: {orig_choice}")
    return orig_choice


async def ai_pick_button(
    buttons: List[Any],
    bot_message: str,
    req: Dict[str, Any],
    state: Dict[str, Any]
) -> Optional[int]:
    """انتخاب ناهمگام دکمه با ارسال به ترد جداگانه جهت جلوگیری از بلاک شدن event loop."""
    return await asyncio.to_thread(pick_button_sync, buttons, bot_message, req, state)
