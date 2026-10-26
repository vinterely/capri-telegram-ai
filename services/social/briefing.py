import asyncio
import json
import os

from ai_engine import ai
from core import config

FILE = os.path.join(config.BASE_DIR, "important.json")

BRIEFING_KEYWORDS = ("امروز چیا داریم", "چیا داریم", "خلاصه امروز", "امروز چی داریم", "امروز چه خبر", "چی شده امروز")

IMPORTANT_ADD = ("مهم کن", "مهم بکن", "مهمش کن", "مهمش بکن")
IMPORTANT_LIST = ("کانال‌های مهم", "کانال های مهم", "مهم‌های من", "لیست مهم")
IMPORTANT_REMOVE = ("از مهم‌ها بردار", "از مهم ها بردار", "از مهم‌ها", "از مهم ها")


def load_important():
    try:
        with open(FILE, encoding="utf-8") as f:
            return json.load(f).get("channels", [])
    except Exception:
        return []


def _save(names):
    from core import fsutil
    fsutil.atomic_write_json(FILE, {"channels": names})


def add_important(name: str):
    names = load_important()
    if name and name not in names:
        names.append(name)
        _save(names)
    return names


def remove_important(name: str):
    names = [n for n in load_important() if n != name]
    _save(names)
    return names


async def _recent_texts(client, entity, limit):
    try:
        msgs = await client.get_messages(entity, limit=limit)
    except Exception:
        return []
    out = []
    for m in msgs:
        if not m or m.out or not m.message:
            continue
        first = ""
        if m.sender:
            first = getattr(m.sender, "first_name", "") or ""
        prefix = f"{first}: " if first else ""
        out.append(prefix + m.message[:120])
    return out


async def collect_private(client, top=3):
    """چت‌های خصوصی که پیام نخوانده دارن + چند پیام آخرشون."""
    rows = []
    async for d in client.iter_dialogs():
        if not d.is_user or getattr(d.entity, "bot", False):
            continue
        if d.unread_count > 0:
            rows.append(d)
    rows.sort(key=lambda d: -d.unread_count)
    out = []
    for d in rows[:top]:
        out.append({"name": d.name, "unread": d.unread_count,
                    "lines": await _recent_texts(client, d.entity, 4)})
    return out


async def collect_channels(client, top=3):
    """کانال‌های مهم (لیست) + کانال‌های پرپیام نخوانده، با آخرین پست‌هاشون."""
    important = load_important()
    rows = []
    async for d in client.iter_dialogs():
        if d.is_channel:
            rows.append(d)
    picked = [d for d in rows if d.name in important]
    for d in rows:
        if d not in picked and d.unread_count > 0 and len(picked) < top:
            picked.append(d)
    out = []
    for d in picked[:top]:
        lines = await _recent_texts(client, d.entity, 5)
        if lines:
            out.append({"name": d.name, "unread": d.unread_count, "lines": lines})
    return out


async def build_briefing(client):
    pv = await collect_private(client)
    ch = await collect_channels(client)

    context_lines = []
    if pv:
        context_lines.append("چت‌های خصوصی:")
        for p in pv:
            context_lines.append(f"- {p['name']} ({p['unread']} نخوانده):")
            for l in p["lines"]:
                context_lines.append("    " + l)
    if ch:
        context_lines.append("کانال‌ها:")
        for c in ch:
            context_lines.append(f"- {c['name']}:")
            for l in c["lines"]:
                context_lines.append("    " + l)

    context = "\n".join(context_lines)
    header = f"☀️ امروز {ai._today()}"
    if not context:
        return header + "\nپیام نخوانده‌ی مهمی نداری 😊 همه‌چیز مرتبه."

    summary = await asyncio.to_thread(ai.summarize_daily, context)
    if summary:
        return header + "\n\n" + summary

    # Heuristic fallback
    lines = [header]
    for p in pv:
        lines.append(f"💬 {p['name']}: {p['unread']} پیام نخوانده")
    for c in ch:
        lines.append(f"📣 {c['name']}: {len(c['lines'])} پست جدید")
    return "\n".join(lines)
