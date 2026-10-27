"""
Smart Do Not Disturb (DND) & Reminders System
Features:
1. Intelligent DND modes: Sleep, Class, Meeting, Work, Workout.
2. Contextual AI-generated away replies in DMs and group mentions (one per sender ID per DND session).
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

# Maximum timeout for generating AI away replies; falls back to static template on timeout
_AI_REPLY_TIMEOUT = 25
# Cap on stored replied sender IDs per DND session to bound state growth
_MAX_REPLIED_IDS = 500
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
        "replies_count": 0,
        "replied_ids": [],
        "missed": [],
        "missed_since": time.time(),
    }
    save_dnd(info)
    return info


def _already_replied(dnd_data: dict, sender_id) -> bool:
    try:
        sid = int(sender_id)
    except (TypeError, ValueError):
        return False
    return sid in {int(x) for x in (dnd_data.get("replied_ids") or []) if str(x).lstrip("-").isdigit()}


def _mark_replied(sender_id) -> None:
    """Mark sender ID as replied to avoid duplicate replies during current DND session."""
    try:
        sid = int(sender_id)
    except (TypeError, ValueError):
        return
    d = load_dnd()
    ids = [int(x) for x in (d.get("replied_ids") or []) if str(x).lstrip("-").isdigit()]
    if sid in ids:
        return
    ids.append(sid)
    if len(ids) > _MAX_REPLIED_IDS:
        ids = ids[-_MAX_REPLIED_IDS:]
    d["replied_ids"] = ids
    d["replies_count"] = int(d.get("replies_count", 0)) + 1
    save_dnd(d)


_MISSED_MAX = 50


def record_missed(sender_name: str, source: str, text: str) -> None:
    """Record missed messages during owner absence (bounded queue) for return briefing."""
    d = load_dnd()
    missed = d.get("missed") or []
    snippet = (text or "").strip()
    if len(snippet) > 300:
        snippet = snippet[:300] + "..."
    missed.append({
        "name": (sender_name or "مخاطب").strip(),
        "source": (source or "پیوی").strip(),
        "text": snippet,
        "ts": time.time(),
    })
    if len(missed) > _MISSED_MAX:
        missed = missed[-_MISSED_MAX:]
    d["missed"] = missed
    save_dnd(d)


def get_missed_summary() -> str:
    """Format a summary briefing of missed messages for the returning owner."""
    d = load_dnd()
    missed = d.get("missed") or []
    since = d.get("missed_since")
    if not missed:
        return "📭 در دورهٔ غیبت اخیر پیام جدیدی ثبت نشده (یا خلاصه پاک شده)."
    lines = [f"📥 **پیام‌های رسیده در نبود تو** ({len(missed)} مورد):\n"]
    for i, m in enumerate(missed[-20:], 1):
        name = m.get("name", "مخاطب")
        source = m.get("source", "")
        text = m.get("text", "") or "[پیام بدون متن]"
        lines.append(f"{i}. 👤 {name} — {source}\n   «{text}»")
    if len(missed) > 20:
        lines.append(f"\n_... و {len(missed) - 20} پیام دیگر_")
    return "\n".join(lines)


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
    if any(w in t for w in ("خواب", "بدرگیرم", "می‌درگیرم", "میدرگیرم", "استراحت")):
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

    # پایان روز/شب برای اعلام غیبت‌های مبهم مثل «امشب نیستم» یا «امروز در دسترس نیستم»
    if "امشب" in t or "تا شب" in t:
        target = now.replace(hour=23, minute=59, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        return target, "امشب"
    if "امروز" in t and any(w in t for w in ("نیستم", "در دسترس", "درگیر", "مشغول", "نمیتونم", "نمی")):
        target = now.replace(hour=23, minute=59, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        return target, "امروز"

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
    status = f"{owner} تا {until_str} درگیر {reason} هست" if until_str else f"{owner} الان درگیر {reason} هست"

    if is_urgent:
        return (
            f"سلام! {status} و فعلاً دسترسی به گوشی نداره. "
            f"پیامت رو دیدم و چون فوری به نظر می‌رسه، جزو پیام‌های مهم علامت زدم که اول از همه سراغش بره. 🙏"
        )

    return (
        f"سلام! {status} و فعلاً نمی‌تونه جواب بده. "
        f"پیامت رسید؛ به‌محض آزاد شدن حتماً جوابت رو می‌ده 🙏"
    )


def generate_group_reply(owner_name: str, reason: str, until_str: str) -> str:
    owner = owner_name or "من"
    status = f"{owner} تا {until_str} درگیر {reason} هست" if until_str else f"{owner} الان درگیر {reason} هست"
    return f"{status} و فعلاً دسترسی نداره؛ پیامت رو دیده و به‌محض برگشتن جواب می‌ده 🙏"


async def generate_ai_reply(
    kind: str,
    owner_name: str,
    reason: str,
    until_str: str,
    sender_name: str,
    incoming: str,
    is_urgent: bool = False,
) -> str:
    """پاسخ غیبت را با هوش مصنوعی و متناسب با پیام طرف می‌سازد؛ در خطا رشتهٔ خالی برمی‌گردد."""
    from ai_engine import ai

    owner = owner_name or "من"
    place = "گروه" if kind == "group" else "چت خصوصی"
    until_line = f"تا {until_str}" if until_str else "تا اطلاع بعدی"
    text = (incoming or "").strip()
    if len(text) > 600:
        text = text[:600] + "…"

    urgent_line = (
        "پیام او فوری/اضطراری به نظر می‌رسد؛ در پاسخ اشاره کن که در اولویت قرار گرفت.\n"
        if is_urgent else ""
    )
    prompt = (
        f"تو دستیار شخصی «{owner}» هستی و از طرف او به پیام {sender_name} در {place} جواب می‌دهی.\n"
        f"وضعیت: {owner} {until_line} درگیر «{reason}» است و الان نمی‌تواند پاسخ بدهد.\n"
        f"متن پیام او: «{text or '[بدون متن / رسانه]'}»\n"
        f"{urgent_line}\n"
        "یک پاسخ کوتاه (حداکثر دو جمله)، محترمانه، صمیمی و طبیعی به فارسی بنویس که:\n"
        "- روشن بگوید الان نیست و دلیلش همین است، و کی برمی‌گردد.\n"
        "- اگر پیامش کار مهمی دارد، بگوید دیده شد و به‌محض برگشتن بررسی می‌شود.\n"
        "- از عبارت‌های کلیشه‌ای مثل «مشغولم» یا «سرش شلوغه» استفاده نکن.\n"
        "- هیچ قول، زمان یا جزئیاتی که در این متن نیست از خودت نساز.\n"
        "- فقط متن نهایی پیام را بده؛ بدون مقدمه و بدون گیومه."
    )
    try:
        reply = await asyncio.wait_for(asyncio.to_thread(ai.ask_direct, prompt), timeout=_AI_REPLY_TIMEOUT)
    except Exception as e:
        log.warning(f"AI DND reply generation failed: {type(e).__name__}")
        return ""
    reply = (reply or "").strip().strip('"“”«»').strip()
    if len(reply) > 400:
        reply = reply[:400].rsplit(" ", 1)[0] + "…"
    return reply


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

async def _sender_info(event) -> Optional[Tuple[str, str]]:
    """نام و یوزرنیم فرستنده؛ برای بات‌ها None برمی‌گرداند."""
    try:
        sender = await event.get_sender()
    except Exception:
        sender = None
    if sender is not None and getattr(sender, "bot", False):
        return None
    name = (getattr(sender, "first_name", "") or "مخاطب").strip()
    username = getattr(sender, "username", "") or ""
    return name, username


async def handle_incoming_pv(event, client) -> bool:
    """پاسخ خودکار هوشمند در چت خصوصی هنگام فعال بودن DND (یک‌بار به هر شناسه در هر دوره)."""
    if not is_dnd_active():
        return False

    sender_id = event.sender_id
    if not sender_id:
        return False

    my_id = await _get_my_id(client)
    if my_id and sender_id == my_id:
        return False

    info = await _sender_info(event)
    if info is None:
        return False
    s_name, s_username = info
    incoming = (event.raw_text or "").strip()

    dnd_data = get_dnd_info()
    reason = dnd_data.get("reason", "مشغله")
    until_str = dnd_data.get("until_str", "")

    # پیام‌ها حتی از فرستنده‌هایی که قبلاً پاسخ گرفته‌اند در خلاصهٔ غیبت ثبت می‌شوند
    record_missed(s_name, "چت خصوصی (PV)", incoming)
    if _already_replied(dnd_data, sender_id):
        return True

    urgent = is_urgent_message(incoming)
    reply_text = await generate_ai_reply(
        "pv", config.OWNER_NAME, reason, until_str, s_name, incoming, is_urgent=urgent
    )
    if not reply_text:
        reply_text = generate_pv_reply(config.OWNER_NAME, reason, until_str, is_urgent=urgent)

    try:
        await event.reply(reply_text)
        _mark_replied(sender_id)

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
    """پاسخ خودکار هوشمند در گروه هنگام تگ شدن مالک (یک‌بار به هر شناسه در هر دوره)."""
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

    info = await _sender_info(event)
    if info is None:
        return False
    s_name, s_username = info
    incoming = (event.raw_text or "").strip()

    try:
        chat = await event.get_chat()
        group_title = getattr(chat, "title", "گروه") or "گروه"
    except Exception:
        group_title = "گروه"

    dnd_data = get_dnd_info()
    reason = dnd_data.get("reason", "مشغله")
    until_str = dnd_data.get("until_str", "")

    # پیام‌ها حتی از فرستنده‌هایی که قبلاً پاسخ گرفته‌اند در خلاصهٔ غیبت ثبت می‌شوند
    record_missed(s_name, f"گروه «{group_title}»", incoming)
    if _already_replied(dnd_data, sender_id):
        return True

    urgent = is_urgent_message(incoming)
    reply_text = await generate_ai_reply(
        "group", config.OWNER_NAME, reason, until_str, s_name, incoming, is_urgent=urgent
    )
    if not reply_text:
        reply_text = generate_group_reply(config.OWNER_NAME, reason, until_str)

    try:
        await event.reply(reply_text)
        _mark_replied(sender_id)

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
        "dnd رو خاموش", "dnd رو ببند", "خاموش کردن dnd", "سرشلوغی رو بردار", "پایان dnd",
        "برگشتم", "برگشتیم", "اومدم", "آمدم", "رسیدم", "حالم بهتره", "خوابم تموم شد"
    ))


_ABSENCE_STRONG = (
    "برمیگردم", "بر میگردم", "برمیگردیم", "در دسترس نیستم", "در دسترس نباشم", "دسترس نیستم",
    "فعلا نیستم", "فعلاً نیستم", "غایبم", "غیبم", "غیبتم", "میرم بیرون",
    "نمیتونم پیام", "نمی تونم پیام", "نمی‌تونم پیام",
)
_ABSENCE_WEAK = ("نیستم", "نیستیم", "نمیتونم", "نمی تونم", "نمی‌تونم")
_ABSENCE_CONTEXT = (
    "ساعت", "امشب", "امروز", "چند ساعت", "دقیقه", "الان", "الآن", "فعلا", "فعلاً",
    "مدیریت", "جواب", "پیام", "در دسترس", "نیم ساعت", "یک ربع", "برگرد",
)
# رد قطعی (سوال یا زمان گذشته): صرف‌نظر از جای آن در جمله، اعلام غیبت شمرده نمی‌شود.
_ABSENCE_HARD_NEGATE = (
    "؟", "?", "چرا", "چطور", "چطوری", "چگونه", "آیا",
    "دیروز", "پارسال", "دیشب", "نبودم", "نبودند",
)
# رد شرطی/نقل‌قول: فقط وقتی قبل از خودِ اعلام غیبت بیاید.
# مثال: «اگه امروز نیستم» رد می‌شود ولی «فعلاً نیستم؛ اگه کسی پیام داد مدیریت کن» فعال می‌شود.
_ABSENCE_SOFT_NEGATE = (
    "اگه", "اگر", "فرض کن", "مثلا", "مثلاً", "شاید",
    "میگه", "میگفت", "بگه", "نقل قول", "چی میگه",
)


def _first_absence_marker_pos(t: str) -> Optional[int]:
    """موقعیت نخستین نشانهٔ غیبت (قوی یا ضعیف) در متن؛ اگر نبود None."""
    positions = [t.find(w) for w in _ABSENCE_STRONG + _ABSENCE_WEAK if w in t]
    return min(positions) if positions else None


def is_absence_activation(text: str) -> bool:
    """تشخیص اعلام غیبت مالک به زبان طبیعی (من نیستم/برمیگردم/امشب نمیتونم...) بدون مثبت کاذب.

    عبارت‌های قطعیِ اول‌شخص بلافاصله فعال می‌شوند؛ نشانه‌های ضعیف («نیستم»/«نمیتونم»)
    فقط همراه با بافت زمان یا مدیریت پیام فعال می‌شوند تا جمله‌هایی مثل
    «من طرفدار این نیستم» وضعیت را تغییر ندهند. سوال و زمان گذشته همیشه رد می‌شوند؛
    فرض و نقل‌قول فقط وقتی رد می‌شوند که قبل از خود اعلام غیبت بیایند.
    """
    t = (text or "").strip().lower()
    if not t or len(t) > 80:
        return False

    # سوال یا زمان گذشته: همیشه رد
    if any(w in t for w in _ABSENCE_HARD_NEGATE):
        return False

    marker_pos = _first_absence_marker_pos(t)
    if marker_pos is None:
        return False

    # «گفت» سوم‌شخص (نه «گفتم» اول‌شخص) پیش از اعلام غیبت → صحبت دربارهٔ دیگری است
    m_quote = re.search(r"گفت(?!م)", t)
    if m_quote and m_quote.start() < marker_pos:
        return False

    # فرض/شرط/نقل‌قول قبل از اعلام غیبت → اعلام واقعی نیست
    for w in _ABSENCE_SOFT_NEGATE:
        idx = t.find(w)
        if idx != -1 and idx < marker_pos:
            return False

    if any(w in t for w in _ABSENCE_STRONG):
        return True
    has_weak = any(w in t for w in _ABSENCE_WEAK)
    if not has_weak:
        return False
    return any(w in t for w in _ABSENCE_CONTEXT)


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
        "درگیرم", "بدرگیرم", "می‌درگیرم", "میدرگیرم", "استراحتم", "کلاسم", "سر کلاسم", "کلاس دارم",
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

    # خلاصهٔ پیام‌های رسیده هنگام غیبت (برای بازبینی مالک)
    if any(w in q_low for w in ("در نبودم", "وقتی نبودم", "خلاصه غیبت", "خلاصه غیبتم", "پیامای نبودم", "پیامهای نبودم", "نبودم چی شد", "چی شد وقتی")):
        msg = get_missed_summary()
        if status:
            await status.edit(msg)
        else:
            await event.reply(msg)
        return True

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

    # ۳. فعال‌سازی DND (اعلام غیبت یا مشغله به زبان طبیعی)
    if is_dnd_command(q) or is_absence_activation(q):
        target_dt, until_str = parse_time_expression(q)
        reason = extract_dnd_reason(q)
        until_ts = target_dt.timestamp() if target_dt else None

        activate_dnd(reason, until_ts=until_ts, until_str=until_str)
        resp = (
            f"🔕 **حالت سرشلوغ (DND) فعال شد.**\n\n"
            f"📌 **علت:** {reason}\n"
            f"⏳ **مدت اعتبار:** {until_str or 'تا اعلام پایان توسط شما'}\n"
            f"💬 در این مدت پیام‌های پیوی و تگ‌های گروه با یک پاسخ محترمانه و طبیعی (یک‌بار به هر نفر) جواب داده می‌شوند و گزارش لحظه‌ای آن‌ها به همین صفحه (Saved Messages) ارسال خواهد شد."
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
