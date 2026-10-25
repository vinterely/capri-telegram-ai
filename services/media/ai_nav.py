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

NAV_SYSTEM_PROMPT = (
    "تو یک موتور فوق‌هوشمند ناوبری دکمه‌های شیشه‌ای (Inline Buttons) در ربات‌های تلگرام برای دانلود فیلم و سریال هستی.\n"
    "وظیفه تو این است که با بررسی متن پیام ربات، درخواست کاربر، وضعیت فایل‌های دریافت شده و فهرست دکمه‌های موجود، "
    "دقیقاً مشخص کنی کدام دکمه باید کلیک شود.\n\n"
    "قوانین تصمیم‌گیری:\n"
    "۱. اگر دکمه‌های ورود به دانلود، منوی اصلی یا تایید وجود دارد، دکمه مرتبط با شروع/دانلود را انتخاب کن.\n"
    "۲. اگر منوی انتخاب فصل است، دکمه فصل درخواستی کاربر را انتخاب کن (اگر کاربر فصل نگفته، فصل اول یا جدیدترین فصل بسته به متن).\n"
    "۳. اگر منوی انتخاب کیفیت است، نزدیک‌ترین کیفیت به کیفیت درخواستی (مثلاً 720p یا 1080p) را انتخاب کن.\n"
    "۴. اگر منوی انتخاب نسخه دوبله یا زیرنویس است، طبق درخواست کاربر انتخاب کن.\n"
    "۵. اگر دکمه «دریافت فایل» یا دکمه شماره قسمت موردنظر کاربر وجود دارد و فایل آن هنوز دریافت نشده، آن را انتخاب کن.\n"
    "۶. اگر کاربر کل فصل یا همه قسمت‌ها را خواسته و فایل قسمت جاری دریافت شده، دکمه «بعدی» یا «Next» یا قسمت بعدی را انتخاب کن.\n"
    "۷. اگر تمام قسمت‌های درخواستی دریافت شده‌اند یا هیچ دکمه مرتبطی وجود ندارد، عدد 0 بنویس.\n\n"
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

    numbered_buttons = format_buttons_list(buttons)
    title = req.get("title") or "فیلم / سریال"
    season = req.get("season")
    episode = req.get("episode")
    quality = req.get("quality") or 720
    audio = req.get("audio") or "دوبله یا زیرنویس"

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
        f"- نسخه: {audio}\n\n"
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

    choice = parse_choice(raw, buttons)
    log.info(f"[ai_nav] Model response: {raw!r} -> Choice index: {choice}")
    return choice


async def ai_pick_button(
    buttons: List[Any],
    bot_message: str,
    req: Dict[str, Any],
    state: Dict[str, Any]
) -> Optional[int]:
    """انتخاب ناهمگام دکمه با ارسال به ترد جداگانه جهت جلوگیری از بلاک شدن event loop."""
    return await asyncio.to_thread(pick_button_sync, buttons, bot_message, req, state)
