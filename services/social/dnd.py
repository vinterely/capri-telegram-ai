"""
Smart Do Not Disturb (DND) & Reminders System
Features:
1. Intelligent DND modes: Sleep, Class, Meeting, Work, Workout.
2. Contextual auto-replies in DMs and group mentions.
3. Real-time logging of auto-replies to Saved Messages.
4. Urgency detection for emergency escalation.
5. Scheduled reminders and notifications in Saved Messages.
6. Auto-deactivation when scheduled time elapses.
7. System status and uptime dashboard.
"""

import asyncio
from datetime import datetime, timedelta
import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from core import config
from core import fsutil

log = logging.getLogger("dnd")

DND_FILE = os.path.join(config.BASE_DIR, "dnd.json")
REMINDERS_FILE = os.path.join(config.BASE_DIR, "reminders.json")

# Auto-reply cooldown (15 mins per user/chat) to prevent spam
COOLDOWN_SEC = 900
_pv_cooldown: Dict[int, float] = {}
_group_cooldown: Dict[Tuple[int, int], float] = {}
_my_id: Optional[int] = None

_PERSIAN_DIGITS = {
    '۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4',
    '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9'
}

URGENT_KEYWORDS = (
    "فوری", "خیلی واجبه", "خیلی واجب", "کار واجب", "اورژانس", "اورژانسی",
    "بیمارستان", "تصادف", "اضطراری", "سریع جواب بده", "سریع زنگ بزن",
    "کار مهم", "مهم و فوری", "زود باش", "کجایی توروخدا", "تو رو خدا جواب بده",
    "خیلی ضروری", "ضروری", "کار حیاتی", "حیاتی"
)


def normalize_digits(s: str) -> str:
    if not s:
        return ""
    for p, a in _PERSIAN_DIGITS.items():
        s = s.replace(p, a)
    return s


def _prune_cooldowns() -> None:
    """Prune expired cooldown timestamps to prevent memory growth."""
    now = time.time()
    stale_pv = [k for k, ts in _pv_cooldown.items() if now - ts > 3600]
    for k in stale_pv:
        _pv_cooldown.pop(k, None)
    stale_grp = [k for k, ts in _group_cooldown.items() if now - ts > 3600]
    for k in stale_grp:
        _group_cooldown.pop(k, None)


async def _get_my_id(client) -> Optional[int]:
    """Fetch and cache owner user ID."""
    global _my_id
    if _my_id is None:
        try:
            me = await client.get_me()
            if me:
                _my_id = me.id
        except Exception:
            pass
    return _my_id


# -----------------------------------------------------------------------------
# DND & Reminders Persistence
# -----------------------------------------------------------------------------

def load_dnd() -> dict:
    try:
        if os.path.exists(DND_FILE):
            with open(DND_FILE, encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        log.warning(f"Error loading dnd.json: {e}")
    return {}


def save_dnd(data: dict) -> None:
    fsutil.atomic_write_json(DND_FILE, data)


def is_dnd_active() -> bool:
    d = load_dnd()
    if not d.get("active"):
        return False
    until_ts = d.get("until_ts")
    if until_ts and time.time() >= until_ts:
        deactivate_dnd()
        return False
    return True


def get_dnd_info() -> dict:
    return load_dnd()


def activate_dnd(reason: str, until_ts: Optional[float] = None, until_str: str = "") -> dict:
    info = {
        "active": True,
        "reason": reason or "مشغله شخصی",
        "until_ts": until_ts,
        "until_str": until_str or ("تا اطلاع بعدی" if not until_ts else ""),
        "started_at": time.time(),
        "replies_count": 0
    }
    save_dnd(info)
    return info


def deactivate_dnd() -> None:
    d = load_dnd()
    d["active"] = False
    save_dnd(d)


def load_reminders() -> List[dict]:
    try:
        if os.path.exists(REMINDERS_FILE):
            with open(REMINDERS_FILE, encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        log.warning(f"Error loading reminders.json: {e}")
    return []


def save_reminders(items: List[dict]) -> None:
    fsutil.atomic_write_json(REMINDERS_FILE, items)


def add_reminder(text: str, due_ts: float, due_str: str) -> dict:
    items = load_reminders()
    rem = {
        "id": f"rem_{int(time.time() * 1000)}",
        "text": text,
        "due_ts": due_ts,
        "due_str": due_str,
        "created_at": time.time()
    }
    items.append(rem)
    items.sort(key=lambda x: x["due_ts"])
    save_reminders(items)
    return rem


def remove_reminder(rem_id: str) -> bool:
    items = load_reminders()
    new_items = [r for r in items if r.get("id") != rem_id]
    if len(new_items) != len(items):
        save_reminders(new_items)
        return True
    return False


def clear_all_reminders() -> int:
    items = load_reminders()
    cnt = len(items)
    save_reminders([])
    return cnt


# -----------------------------------------------------------------------------
# Natural Time and Reason Parser
# -----------------------------------------------------------------------------

def extract_dnd_reason(text: str) -> str:
    t = text.lower()
    if any(w in t for w in ("خواب", "بخوابم", "می‌خوابم", "میخوابم", "استراحت")):
        return "خواب و استراحت"
    if any(w in t for w in ("کلاس", "دانشگاه", "مدرسه")):
        return "کلاس و دانشگاه"
    if any(w in t for w in ("درس", "مطالعه", "امتحان", "پروژه")):
        return "درس و امتحان"
    if any(w in t for w in ("جلسه", "میتینگ", "meeting")):
        return "جلسه کاری"
    if any(w in t for w in ("کار دارم", "سر کارم", "مشغولم", "درگیرم", "کارم")):
        return "مشغله کاری"
    if any(w in t for w in ("باشگاه", "ورزش", "تمرین")):
        return "باشگاه و ورزش"
    if any(w in t for w in ("رانندگی", "بیرون", "بیرونم")):
        return "بیرون بودن"
    return "مشغله و کارهای شخصی"


def parse_time_expression(text: str, now: Optional[datetime] = None) -> Tuple[Optional[datetime], str]:
    """Extract future target datetime from natural text."""
    if now is None:
        now = datetime.now()
    t = normalize_digits(text.lower())

    # Simple relative time expressions
    if "نیم ساعت" in t:
        return now + timedelta(minutes=30), "۳۰ دقیقه دیگر"
    if "یک ربع" in t:
        return now + timedelta(minutes=15), "۱۵ دقیقه دیگر"

    # Offset hours / minutes
    m_h = re.search(r'(\d+)\s*(?:ساعت|ساعته|h)\b', t)
    m_m = re.search(r'(\d+)\s*(?:دقیقه|مین|min)\b', t)

    if m_h or m_m:
        delta = timedelta()
        parts = []
        if m_h:
            h = int(m_h.group(1))
            delta += timedelta(hours=h)
            parts.append(f"{h} ساعت")
        if m_m:
            m = int(m_m.group(1))
            delta += timedelta(minutes=m)
            parts.append(f"{m} دقیقه")
        target = now + delta
        desc = " و ".join(parts) + " دیگر"
        return target, desc

    # Exact clock time expressions
    m_clock = re.search(r'(?:ساعت|تا\s+ساعت|تا)\s*(\d{1,2})(?::(\d{2}))?', t)
    if not m_clock:
        m_clock = re.search(r'\b(\d{1,2}):(\d{2})\b', t)

    if m_clock:
        hour = int(m_clock.group(1))
        minute = int(m_clock.group(2)) if m_clock.group(2) else 0

        is_tomorrow = "فردا" in t
        is_evening = any(w in t for w in ("عصر", "بعد از ظهر", "بعدازظهر", "غروب", "شب"))
        is_morning = any(w in t for w in ("صبح", "صبح زود"))

        if is_evening and hour < 12:
            hour += 12
        elif is_morning and hour == 12:
            hour = 0

        try:
            target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        except ValueError:
            return None, ""

        if is_tomorrow:
            target += timedelta(days=1)
        elif target <= now:
            if hour <= 12 and not is_morning:
                alt = target.replace(hour=hour + 12)
                if alt > now:
                    target = alt
                else:
                    target += timedelta(days=1)
            else:
                target += timedelta(days=1)

        time_str = f"ساعت {target.strftime('%H:%M')}"
        if is_tomorrow or target.date() > now.date():
            time_str = f"فردا {time_str}"
        return target, time_str

    return None, ""


def clean_reminder_text(text: str) -> str:
    """استخراج هسته پیام یادآوری بدون کلمات دستوری و زمان."""
    cleaned = text
    for prefix in ("کاپری", "لطفا", "لطفاً"):
        cleaned = re.sub(rf"^\s*{prefix}\s*", "", cleaned)

    # پاکسازی افعال دستوری یادآوری
    for w in (
        "یادم بنداز که", "یادم بنداز", "یادم بیار که", "یادم بیار",
        "یادآوری کن که", "یادآوری کن", "بهم بگو که", "بهم بگو",
        "خبر بده که", "خبر بده", "آلارم بذار برای", "الارم بزار برای", "آلارم بذار", "الارم بزار"
    ):
        cleaned = cleaned.replace(w, " ")

    # پاکسازی مشخصات زمانی
    for w in ("فردا", "صبح", "عصر", "شب", "امشب", "نیم ساعت دیگه", "یک ربع دیگه"):
        cleaned = cleaned.replace(w, " ")
    cleaned = re.sub(r'(?:تا\s+)?ساعت\s*\d{1,2}(?::\d{2})?', ' ', cleaned)
    cleaned = re.sub(r'\d+\s*(?:ساعت|ساعته|دقیقه|مین)\s*(?:دیگه|بعد)?', ' ', cleaned)

    res = " ".join(cleaned.split()).strip("،,:.؟! ")
    return res or "پیگیری تسک شخصی"


# -----------------------------------------------------------------------------
# تولید پیام‌های پاسخ با لحن طبیعی تلگرامی
# -----------------------------------------------------------------------------

def is_urgent_message(text: str) -> bool:
    t = (text or "").lower()
    return any(k in t for k in URGENT_KEYWORDS)


def generate_pv_reply(owner_name: str, reason: str, until_str: str, is_urgent: bool = False) -> str:
    owner = owner_name or "من"
    until_part = f" و تا {until_str}" if until_str else ""

    if is_urgent:
        return (
            f"سلام! {owner} الان درگیر {reason} هست{until_part} و دستش بنده. "
            f"پیام شما چون به نظر فوری و مهم می‌آید، در صفحه پیام‌های ذخیره‌شده‌اش نشانه‌گذاری شد تا به محض اینکه فرصت کرد سریعاً ببیند. 🙏"
        )

    return (
        f"سلام! {owner} الان درگیر {reason} هست{until_part} و سرش شلوغه. "
        f"پیامتون رو دیدم، به محض اینکه آزاد بشه حتماً جوابتون رو میده 🙂"
    )


def generate_group_reply(owner_name: str, reason: str, until_str: str) -> str:
    owner = owner_name or "من"
    until_part = f" تا {until_str}" if until_str else ""
    return f"{owner} الان{until_part} درگیر {reason} هست، آزاد بشه پیامت رو چک می‌کنه ✌️"


# -----------------------------------------------------------------------------
# گزارش به Saved Messages
# -----------------------------------------------------------------------------

async def report_dnd_action(
    client,
    sender_name: str,
    sender_username: str,
    source_type: str,
    incoming_text: str,
    reply_text: str,
    is_urgent: bool = False
) -> None:
    username_str = f" (@{sender_username})" if sender_username else ""
    urgent_banner = "🚨 **[هشدار فوری / پیام اضطراری!]**\n" if is_urgent else ""
    
    # سقف طول پیام ورودی جهت جلوگیری از خطای سقف طول تلگرام (4096)
    snippet = (incoming_text or "").strip()
    if len(snippet) > 500:
        snippet = snippet[:500] + "..."
    if not snippet:
        snippet = "[پیام تصویری، صوتی یا بدون متن]"

    report = (
        f"{urgent_banner}"
        f"🔕 **پاسخ خودکار در حالت سرشلوغ (DND)**\n\n"
        f"👤 **فرستنده:** {sender_name}{username_str}\n"
        f"📍 **محل پیام:** {source_type}\n"
        f"📩 **متن پیام او:**\n«{snippet}»\n\n"
        f"🤖 **پاسخی که داده شد:**\n«{reply_text}»"
    )
    try:
        await client.send_message("me", report)
    except Exception as e:
        log.warning(f"Error reporting DND reply to Saved Messages: {e}")


# -----------------------------------------------------------------------------
# هندلرهای ورودی (پیوی و گروه)
# -----------------------------------------------------------------------------

async def handle_incoming_pv(event, client) -> bool:
    """پاسخ خودکار در چت خصوصی هنگام فعال بودن DND."""
    if not is_dnd_active():
        return False

    sender_id = event.sender_id
    if not sender_id:
        return False

    my_id = await _get_my_id(client)
    if my_id and sender_id == my_id:
        return False

    now = time.time()
    if now - _pv_cooldown.get(sender_id, 0) < COOLDOWN_SEC:
        return True  # کول‌داون فعال است

    try:
        sender = await event.get_sender()
    except Exception:
        sender = None

    if sender is not None and getattr(sender, "bot", False):
        return False

    s_name = (getattr(sender, "first_name", "") or "مخاطب").strip()
    s_username = getattr(sender, "username", "") or ""
    incoming = (event.raw_text or "").strip()

    dnd_data = get_dnd_info()
    reason = dnd_data.get("reason", "مشغله")
    until_str = dnd_data.get("until_str", "")
    urgent = is_urgent_message(incoming)

    reply_text = generate_pv_reply(config.OWNER_NAME, reason, until_str, is_urgent=urgent)

    try:
        await event.reply(reply_text)
        _pv_cooldown[sender_id] = now
        if len(_pv_cooldown) > 200:
            _prune_cooldowns()

        dnd_data["replies_count"] = dnd_data.get("replies_count", 0) + 1
        save_dnd(dnd_data)

        # ارسال گزارش به سیود مسیجز
        await report_dnd_action(
            client=client,
            sender_name=s_name,
            sender_username=s_username,
            source_type="چت خصوصی (PV)",
            incoming_text=incoming,
            reply_text=reply_text,
            is_urgent=urgent
        )
        return True
    except Exception as e:
        log.warning(f"Error sending DND reply in PV: {e}")
        return False


async def handle_incoming_group_mention(event, client) -> bool:
    """پاسخ خودکار در گروه هنگام تگ شدن مالک در زمان فعال بودن DND."""
    if not is_dnd_active():
        return False

    sender_id = event.sender_id
    my_id = await _get_my_id(client)
    if not sender_id or (my_id and sender_id == my_id):
        return False

    # بررسی آیا پیام تگ مالک است یا ریپلای روی پیام مالک
    is_tag = getattr(event, "mentioned", False)
    if not is_tag and event.reply_to_msg_id:
        try:
            replied = await event.get_reply_message()
            if replied and (getattr(replied, "out", False) or (my_id and replied.sender_id == my_id)):
                is_tag = True
        except Exception:
            pass

    if not is_tag:
        return False

    chat_id = event.chat_id
    if not chat_id:
        return False

    now = time.time()
    key = (chat_id, sender_id)
    if now - _group_cooldown.get(key, 0) < COOLDOWN_SEC:
        return True

    try:
        sender = await event.get_sender()
    except Exception:
        sender = None

    if sender is not None and getattr(sender, "bot", False):
        return False

    s_name = (getattr(sender, "first_name", "") or "مخاطب").strip()
    s_username = getattr(sender, "username", "") or ""
    incoming = (event.raw_text or "").strip()

    try:
        chat = await event.get_chat()
        group_title = getattr(chat, "title", "گروه") or "گروه"
    except Exception:
        group_title = "گروه"

    dnd_data = get_dnd_info()
    reason = dnd_data.get("reason", "مشغله")
    until_str = dnd_data.get("until_str", "")
    urgent = is_urgent_message(incoming)

    reply_text = generate_group_reply(config.OWNER_NAME, reason, until_str)

    try:
        await event.reply(reply_text)
        _group_cooldown[key] = now
        if len(_group_cooldown) > 200:
            _prune_cooldowns()

        dnd_data["replies_count"] = dnd_data.get("replies_count", 0) + 1
        save_dnd(dnd_data)

        # ارسال گزارش به سیود مسیجز
        await report_dnd_action(
            client=client,
            sender_name=s_name,
            sender_username=s_username,
            source_type=f"گروه «{group_title}»",
            incoming_text=incoming,
            reply_text=reply_text,
            is_urgent=urgent
        )
        return True
    except Exception as e:
        log.warning(f"Error sending DND reply in group: {e}")
        return False


# -----------------------------------------------------------------------------
# مدیریت فرامین صادر شده توسط مالک (DND و Reminders)
# -----------------------------------------------------------------------------

def is_status_command(text: str) -> bool:
    t = (text or "").strip().lower()
    return any(w in t for w in ("وضعیت سرشلوغ", "وضعیت dnd", "حالت dnd فعال هست", "سرشلوغ فعاله", "وضعیت ربات", "وضعیت سیستم", "وضعیت کاپری", "آمار کاپری", "استاتوس"))


def is_dnd_deactivate_command(text: str) -> bool:
    t = (text or "").strip().lower()
    return any(w in t for w in (
        "بیدار شدم", "آزاد شدم", "سرشلوغ رو خاموش", "سرشلوغ رو ببند",
        "dnd رو خاموش", "dnd رو ببند", "خاموش کردن dnd", "سرشلوغی رو بردار", "پایان dnd"
    ))


def is_dnd_command(text: str) -> bool:
    t = (text or "").strip().lower()
    if not t:
        return False
    if is_dnd_deactivate_command(t) or is_status_command(t):
        return True

    # سوالات اطلاعاتی نباید اشتباهاً DND را فعال کنند
    if any(q in t for q in ("چرا", "چطور", "چطوری", "چگونه", "آیا", "چیه")):
        return False

    has_activity = any(w in t for w in (
        "خوابم", "بخوابم", "می‌خوابم", "میخوابم", "استراحتم", "کلاسم", "سر کلاسم", "کلاس دارم",
        "دانشگاهم", "سر کارم", "کار دارم", "جلسه‌ام", "جلسه دارم", "درس دارم", "درس می‌خونم",
        "درس میخونم", "امتحان دارم", "باشگاهم", "بیرونم", "رانندگی‌ام", "مزاحم نشید", "مزاحمم نشید",
        "سرم شلوغه", "سرشلوغ", "dnd"
    ))
    has_time = any(w in t for w in ("تا ساعت", "ساعت", "دقیقه", "مین", "نیم ساعت", "یک ربع", "فعال کن", "بذار رو", "برو رو"))

    return has_activity and (has_time or "مزاحم" in t or "سرشلوغ" in t or "dnd" in t)


def is_reminder_clear_command(text: str) -> bool:
    """تشخیص دستور پاک کردن یا حذف یادآورها."""
    t = (text or "").strip().lower()
    if not t:
        return False
    has_rem = any(w in t for w in ("یادآور", "یاداور", "ریمایندر", "آلارم", "الارم"))
    has_clear = any(w in t for w in (
        "پاک", "حذف", "لغو", "کنسل", "بردار", "خالی کن", "دیلیت", "پاکش", "حذفش", "بردارش"
    ))
    return has_rem and has_clear


def is_reminder_list_command(text: str) -> bool:
    """تشخیص درخواست مشاهده لیست یادآورها."""
    t = (text or "").strip().lower()
    if not t or is_reminder_clear_command(t):
        return False
    has_rem = any(w in t for w in ("یادآور", "یاداور", "ریمایندر", "آلارم", "الارم"))
    if not has_rem:
        return False
    # افعال ثبت یادآور جدید نباید با لیست اشتباه شوند
    if any(w in t for w in ("بنداز", "بیار", "بذار", "بزار", "بگو", "ثبت", "تنظیم")):
        return False
    has_list = any(w in t for w in (
        "لیست", "چیه", "نشون بده", "چی دارم", "چی گذاشتی", "چند تا", "کدوما", "وضعیت", "ببینم", "نمایش"
    ))
    is_exact = any(w in t for w in ("یادآورام", "یادآورها", "یادآورهام", "ریمایندرهام", "یادآورهای فعال"))
    return has_list or is_exact


def extract_reminder_target_index(text: str) -> Optional[int]:
    """استخراج شماره یادآور برای حذف تکی (مثال: «یادآور ۱ رو پاک کن» یا «یادآور اول»)."""
    t = normalize_digits((text or "").lower())
    m = re.search(r'(?:شماره|یادآور|مورد)\s*(\d+)', t)
    if m:
        try:
            return int(m.group(1))
        except Exception:
            pass
    word_map = {"اول": 1, "دوم": 2, "سوم": 3, "چهارم": 4, "پنجم": 5}
    for w, idx in word_map.items():
        if w in t:
            return idx
    m_alone = re.search(r'(\d+)', t)
    if m_alone:
        try:
            return int(m_alone.group(1))
        except Exception:
            pass
    return None


def is_reminder_command(text: str) -> bool:
    t = (text or "").strip().lower()
    if not t:
        return False
    if is_reminder_clear_command(t) or is_reminder_list_command(t):
        return True

    has_trigger_verb = any(w in t for w in ("یادم بنداز", "یادم بیار", "یادآوری کن", "یاداوری کن", "بهم بگو", "آلارم بذار", "الارم بزار", "ریمایندر", "یادآور بذار", "یاداور بزار"))
    has_time = any(w in t for w in ("ساعت", "دقیقه", "فردا", "دیگه", "نیم ساعت", "یک ربع"))

    return has_trigger_verb and has_time


def get_dashboard_status(uptime_str: str, active_model: str, voice_str: str) -> str:
    """ساخت داشبورد جامع وضعیت و آمار کاپری."""
    dnd_info = get_dnd_info()
    rems = load_reminders()

    if is_dnd_active():
        dnd_status = f"🔴 **فعال** (علت: {dnd_info.get('reason', 'مشغله')} | تا: {dnd_info.get('until_str', 'اعلام لغو')})"
    else:
        dnd_status = "🟢 **عادی (پاسخ‌گو)**"

    rem_status = f"{len(rems)} مورد فعال" if rems else "صف خالی"

    try:
        from services.telegram import vault
        v_data = vault.load_vault_data()
        if v_data.get("group_id"):
            vault_status = f"فعال ({v_data.get('total_organized_count', 0)} پیام بایگانی)"
        else:
            vault_status = "راه‌اندازی نشده"
    except Exception:
        vault_status = "نامشخص"

    return (
        "📊 **داشبورد وضعیت و آمار کاپری**\n\n"
        f"⏱ **مدت زمان فعالیت (Uptime):** {uptime_str}\n"
        f"🤖 **مدل فعال هوش مصنوعی:** {active_model}\n"
        f"🎙 **گوینده و موتور صوتی:** {voice_str}\n"
        f"🔕 **حالت سرشلوغ (DND):** {dnd_status}\n"
        f"⏰ **یادآورهای در صف:** {rem_status}\n"
        f"📁 **صندوق هوشمند (Vault):** {vault_status}\n"
        f"💬 **پاسخ‌های خودکار داده‌شده:** {dnd_info.get('replies_count', 0)} پیام"
    )


async def handle_owner_command(event, status, question: str) -> bool:
    """بررسی و اجرای فرامین DND و یادآور صادر شده توسط مالک."""
    q = (question or "").strip()
    q_low = q.lower()

    # ۱. خاموش کردن DND
    if is_dnd_deactivate_command(q_low):
        dnd_info = get_dnd_info()
        rep_cnt = dnd_info.get("replies_count", 0)
        deactivate_dnd()
        msg = f"✅ حالت سرشلوغ (DND) خاموش شد و کاپری به حالت عادی بازگشت.\n📊 تعداد پاسخ‌های خودکار داده‌شده در این دوره: {rep_cnt} مورد"
        if status:
            await status.edit(msg)
        else:
            await event.reply(msg)
        return True

    # ۲. استعلام وضعیت DND یا داشبورد
    if is_status_command(q_low):
        dnd_info = get_dnd_info()
        if is_dnd_active():
            res_str = (
                f"🔕 **حالت سرشلوغ (DND) فعال است.**\n\n"
                f"📌 **علت ثبت‌شده:** {dnd_info.get('reason', 'مشغله')}\n"
                f"⏳ **زمان پایان:** {dnd_info.get('until_str', 'نامشخص')}\n"
                f"📊 **تعداد پاسخ‌های خودکار:** {dnd_info.get('replies_count', 0)} پیام"
            )
        else:
            res_str = "✅ حالت سرشلوغ (DND) هم‌اکنون غیرفعال است و ربات در وضعیت عادی قرار دارد."
        if status:
            await status.edit(res_str)
        else:
            await event.reply(res_str)
        return True

    # ۳. فعال‌سازی DND
    if is_dnd_command(q):
        target_dt, until_str = parse_time_expression(q)
        reason = extract_dnd_reason(q)
        until_ts = target_dt.timestamp() if target_dt else None

        activate_dnd(reason, until_ts=until_ts, until_str=until_str)
        resp = (
            f"🔕 **حالت سرشلوغ (DND) فعال شد.**\n\n"
            f"📌 **علت:** {reason}\n"
            f"⏳ **مدت اعتبار:** {until_str or 'تا اعلام پایان توسط شما'}\n"
            f"💬 در این مدت پیام‌های پیوی و تگ‌های گروه به‌صورت محترمانه پاسخ داده می‌شوند و گزارش لحظه‌ای آن‌ها به همین صفحه (Saved Messages) ارسال خواهد شد."
        )
        if status:
            await status.edit(resp)
        else:
            await event.reply(resp)
        return True

    # ۴. پاک کردن یادآورها (اولویت بالاتر نسبت به لیست تا فرامینی مثل «پاک کردن یادآورها» اشتباهاً لیست نشوند)
    if is_reminder_clear_command(q_low):
        idx = extract_reminder_target_index(q_low)
        rems = load_reminders()
        if not rems:
            msg = "📋 هیچ یادآور فعالی در صف وجود ندارد."
        elif idx is not None and 1 <= idx <= len(rems):
            target = rems[idx - 1]
            remove_reminder(target.get("id"))
            msg = f"🗑️ یادآور شماره {idx} با موفقیت پاک شد:\n📌 **{target.get('text')}**"
        else:
            cnt = clear_all_reminders()
            msg = f"🗑️ تمام یادآورهای فعال شما ({cnt} مورد) با موفقیت پاک شدند." if cnt > 0 else "📋 هیچ یادآور فعالی در صف وجود نداشت."
        if status:
            await status.edit(msg)
        else:
            await event.reply(msg)
        return True

    # ۵. لیست یادآورها
    if is_reminder_list_command(q_low):
        rems = load_reminders()
        if not rems:
            msg = "📋 هیچ یادآور فعالی در صف وجود ندارد."
        else:
            lines = ["📋 **لیست یادآورهای فعال شما:**\n"]
            for idx, r in enumerate(rems, start=1):
                lines.append(f"{idx}. 📌 **{r.get('text')}** — ⏰ {r.get('due_str')}")
            msg = "\n".join(lines)
        if status:
            await status.edit(msg)
        else:
            await event.reply(msg)
        return True

    # ۶. افزودن یادآور جدید
    if is_reminder_command(q):
        target_dt, due_str = parse_time_expression(q)
        if not target_dt:
            msg = "⚠️ نتونستم زمان دقیق یادآوری رو متوجه بشم. لطفاً مثلاً بگو: «ساعت ۱۰ یادم بنداز جزوه رو بفرستم» یا «۲ ساعت دیگه یادم بنداز»."
            if status:
                await status.edit(msg)
            else:
                await event.reply(msg)
            return True

        rem_text = clean_reminder_text(q)
        add_reminder(rem_text, target_dt.timestamp(), due_str)
        msg = f"⏰ **یادآور با موفقیت ثبت شد!**\n\n📌 **موضوع:** {rem_text}\n⏳ **زمان هشدار:** {due_str}"
        if status:
            await status.edit(msg)
        else:
            await event.reply(msg)
        return True

    return False


# -----------------------------------------------------------------------------
# حلقه پس‌زمینه زمان‌بندی (Scheduler Loop)
# -----------------------------------------------------------------------------

async def start_scheduler_loop(client) -> None:
    """حلقه پس‌زمینه سبک برای بررسی انقضای DND و سررسید یادآورها."""
    log.info("Starting DND & Reminders scheduler loop...")
    while True:
        try:
            await asyncio.sleep(10)
            now = time.time()

            # ۱. بررسی انقضای خودکار DND
            dnd_data = load_dnd()
            if dnd_data.get("active"):
                until_ts = dnd_data.get("until_ts")
                if until_ts and now >= until_ts:
                    deactivate_dnd()
                    until_str = dnd_data.get("until_str", "مقرر")
                    rep_cnt = dnd_data.get("replies_count", 0)
                    notice = (
                        f"🔔 **پایان حالت سرشلوغ (DND):**\n\n"
                        f"ساعت {until_str} سپری شد و کاپری به حالت عادی بازگشت.\n"
                        f"📊 در این مدت {rep_cnt} پیام به‌صورت خودکار مدیریت شدند."
                    )
                    try:
                        await client.send_message("me", notice)
                    except Exception as e:
                        log.warning(f"Error sending DND expiration notice: {e}")

            # ۲. بررسی سررسید یادآورها
            reminders = load_reminders()
            if reminders:
                due_reminders = [r for r in reminders if now >= r.get("due_ts", 0)]
                remaining_reminders = [r for r in reminders if now < r.get("due_ts", 0)]

                if due_reminders:
                    save_reminders(remaining_reminders)
                    for r in due_reminders:
                        alarm_msg = (
                            f"⏰ **یادآور کاپری!**\n\n"
                            f"📌 **موضوع:** {r.get('text')}\n"
                            f"⏳ **زمان تعیین‌شده:** {r.get('due_str')}"
                        )
                        try:
                            await client.send_message("me", alarm_msg)
                        except Exception as e:
                            log.warning(f"Error delivering reminder: {e}")

        except Exception as e:
            log.error(f"Error in DND scheduler loop: {e}", exc_info=True)
            await asyncio.sleep(10)
