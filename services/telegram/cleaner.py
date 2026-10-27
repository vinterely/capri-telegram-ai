"""Owner Message Cleaner with Guaranteed Pre-Deletion Backup.

Trigger: "کاپری ۱۰ پاک کن" / "کاپری ۵ پیام پاک کن" / "کاپری ۲۰ تا از پیام‌هام رو پاک کن".

Safety Rule: Zero messages are deleted without confirmed pre-deletion backup.
Pipeline:
1) Verify owner authorization.
2) Parse count and verify confirmation threshold.
3) Collect outgoing owner message targets (excluding bot replies and commands).
4) Backup message metadata and forward content to the 'backup' forum topic in Capri Home.
5) Confirm backup success for each individual message.
6) Revoke/delete ONLY confirmed backed-up messages.
7) Return truthful, transparent execution report.
"""
import asyncio
import logging
import re
import time
from typing import Dict, List, Optional

from services.telegram import home, vault

logger = logging.getLogger("cleaner")

DELETE_VERBS = ("پاک کن", "پاکش کن", "پاک کردن", "حذف کن", "حذف کردن", "پاک بکن", "حذف بکن")
# Guard against collisions with Vault purge operations
_VAULT_CONTEXT = ("صندوق", "سیو", "سیومسیج", "مرتب", "دسته", "سازمان", "saved")

# Deletions above this threshold require interactive owner confirmation
CONFIRM_THRESHOLD = 20

_PERSIAN_DIGITS = {
    '۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4',
    '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9',
}


def _norm_digits(s: str) -> str:
    for p, a in _PERSIAN_DIGITS.items():
        s = s.replace(p, a)
    return s


def parse_delete_count(question: str) -> Optional[int]:
    """Extract message count from query; returns None if invalid or absent."""
    t = _norm_digits((question or "").lower())
    m = re.search(r"\b(\d+)\b", t)
    if not m:
        return None
    try:
        n = int(m.group(1))
    except ValueError:
        return None
    return n if n > 0 else None


def is_delete_command(question: str) -> bool:
    """Detect owner message deletion intent (number + delete verb, outside vault context)."""
    t = (question or "").strip().lower()
    if not t:
        return False
    if any(w in t for w in _VAULT_CONTEXT):
        return False
    if not any(w in t for w in DELETE_VERBS):
        return False
    return parse_delete_count(t) is not None


def needs_confirmation(n: int) -> bool:
    return n > CONFIRM_THRESHOLD


async def _chat_title(client, chat_id) -> str:
    try:
        ent = await client.get_entity(chat_id)
        return getattr(ent, "title", None) or getattr(ent, "first_name", "") or str(chat_id)
    except Exception:
        return str(chat_id)


def _message_snippet(m, limit: int = 80) -> str:
    text = (getattr(m, "raw_text", None) or getattr(m, "message", None) or "").strip()
    if text:
        text = " ".join(text.split())
        if len(text) > limit:
            text = text[:limit] + "..."
        return text
    if getattr(m, "media", None) and not getattr(m, "action", None):
        return "[پیام دارای رسانه/فایل]"
    return "[پیام بدون متن]"


def _format_ts(ts) -> str:
    try:
        return time.strftime("%Y-%m-%d %H:%M", time.localtime(ts))
    except Exception:
        return str(ts)


async def collect_owner_messages(client, chat_id, command_msg_id, n: int, skip_ids=None) -> List:
    """Collect up to n outgoing owner messages (out=True) in reverse chronological order.

    Excludes bot responses, status messages, and command messages.
    """
    skip = {int(x) for x in (skip_ids or set())}
    targets: List = []
    async for m in client.iter_messages(chat_id, limit=2000):
        if getattr(m, "action", None) is not None:
            continue
        if not getattr(m, "out", False):
            continue
        if getattr(m, "id", None) == command_msg_id or getattr(m, "id", None) in skip:
            continue
        targets.append(m)
        if len(targets) >= n:
            break
    return targets


async def run_delete(client, chat_id, command_msg_id, n: int, status_callback=None, skip_ids=None) -> Dict:
    """Execute message deletion with verified backup. Always returns a factual report."""
    report: Dict = {
        "target_count": 0,
        "backed_up": [],
        "backup_failed": [],
        "deleted": [],
        "delete_failed": [],
        "message": "",
    }

    # 1. Ensure Capri Home group and backup topic exist
    group_id, _ = await home.ensure_home_group(client, status_callback)
    topics = await home.ensure_home_topics(client, group_id, status_callback)
    backup_topic = topics.get("backup") or 1
    home_entity = await client.get_input_entity(group_id)

    # 2. Collect target owner messages
    if status_callback:
        await status_callback(f"🔍 در حال پیدا کردن {n} پیام متعلق به شما...")
    targets = await collect_owner_messages(client, chat_id, command_msg_id, n, skip_ids=skip_ids)
    report["target_count"] = len(targets)

    if not targets:
        report["message"] = "هیچ پیام متعلق به شما در این چت پیدا نشد که بشه حذف کرد."
        return report

    # 3. Send backup header manifest to Home backup topic
    from ai_engine import ai
    chat_title = await _chat_title(client, chat_id)
    lines = [
        "🗂 **بکاپ پیش از حذف**",
        f"• چت مبدأ: {chat_title} (شناسه `{chat_id}`)",
        f"• تاریخ عملیات: {ai._today()} — {_format_ts(time.time())}",
        f"• تعداد پیام‌های هدف: {len(targets)}",
        "",
        "لیست پیام‌ها:",
    ]
    for i, m in enumerate(targets, 1):
        lines.append(f"{i}. ID `{m.id}` | {_format_ts(getattr(m, 'date', None).timestamp() if getattr(m, 'date', None) else 0)} | «{_message_snippet(m)}»")
    header = "\n".join(lines)
    try:
        await client.send_message(home_entity, header, reply_to=backup_topic, link_preview=False)
    except Exception as e:
        logger.warning("Failed to send backup header: %s", e)

    # 4. Forward each target and track verification
    for m in targets:
        ok = False
        try:
            ok = await vault.forward_to_topic(client, home_entity, m, backup_topic, from_peer=chat_id, album_ids=[m.id])
        except Exception as e:
            logger.warning("Backup forward failed for msg %s: %s", m.id, e)
            ok = False
        if ok:
            report["backed_up"].append(m.id)
        else:
            report["backup_failed"].append(m.id)
        await asyncio.sleep(0.3)

    # 5. Revoke/delete ONLY verified backed-up messages
    for mid in report["backed_up"]:
        try:
            await client.delete_messages(chat_id, mid, revoke=True)
            report["deleted"].append(mid)
        except Exception as e:
            logger.warning("Delete failed for msg %s: %s", mid, e)
            report["delete_failed"].append(mid)
        await asyncio.sleep(0.3)

    # 6. Truthful final report
    b_ok = len(report["backed_up"])
    b_fail = len(report["backup_failed"])
    d_ok = len(report["deleted"])
    d_fail = len(report["delete_failed"])

    parts = [
        f"🗑 **عملیات حذف پیام‌های شما انجام شد**",
        f"• پیام‌های هدف: **{report['target_count']}**",
        f"• بکاپ موفق: **{b_ok}**",
        f"• حذف‌شده: **{d_ok}**",
    ]
    if b_fail:
        parts.append(f"• ⚠️ بکاپ ناموفق (حذف نشدند): **{b_fail}**")
    if d_fail:
        parts.append(f"• ⚠️ حذف ناموفق (بکاپ حفظ شد): **{d_fail}**")
    if b_fail or d_fail:
        parts.append("\n❌ فقط پیام‌هایی حذف شدند که بکاپ‌شان تأیید شده بود. موارد ناموفق دست‌نخورده باقی ماندند.")
    report["message"] = "\n".join(parts)
    return report
