"""Periodic Summarization of Selected Channels (Channel Summary).

Allows the owner to subscribe to Telegram channels; Capri polls new posts every 30 minutes
(tracking message IDs to avoid duplicates) and delivers high-fidelity digests to the
'summary' forum topic in Capri Home.

- Channel list and message cursors are persisted in channel_summary.json.
- Strictly avoids duplicate processing and sends nothing if no new posts arrived.
"""
import asyncio
import json
import logging
import os
import time
from typing import Dict, List, Optional

from telethon import types as tl_types

from core import config, fsutil
from services.telegram import home

logger = logging.getLogger("channel_summary")

SUMMARY_FILE = os.path.join(config.BASE_DIR, "channel_summary.json")

INTERVAL_SEC = 30 * 60  # Every 30 minutes
TICK_SEC = 60
MAX_NEW_PER_CHANNEL = 30
MAX_CHUNK = 3800  # Max chunk length for Telegram message delivery


def load_data() -> dict:
    data = {}
    if os.path.exists(SUMMARY_FILE):
        try:
            with open(SUMMARY_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    data = loaded
        except Exception:
            data = {}
    data.setdefault("channels", [])
    data.setdefault("last_msg_id", {})
    data.setdefault("last_run_ts", 0)
    return data


def save_data(data: dict) -> None:
    fsutil.atomic_write_json(SUMMARY_FILE, data)


def get_channels() -> List[dict]:
    return list(load_data().get("channels", []))


def _find_index(data: dict, identifier) -> int:
    """Find channel index by name or ID; returns -1 if absent."""
    ident = str(identifier).strip().lower()
    for i, ch in enumerate(data.get("channels", [])):
        if str(ch.get("id", "")).lower() == ident:
            return i
        if (ch.get("name") or "").strip().lower() == ident:
            return i
        if ident in (ch.get("name") or "").strip().lower():
            return i
    return -1


def add_channel(name: str, cid, username: str = "", seed_msg_id: Optional[int] = None,
                access_hash: Optional[int] = None) -> List[dict]:
    """Add channel to summary list (idempotently) and initialize cursor."""
    data = load_data()
    if _find_index(data, cid) == -1:
        data["channels"].append({
            "name": (name or "").strip(),
            "id": int(cid),
            "username": (username or "").strip(),
            "access_hash": int(access_hash) if access_hash is not None else None,
        })
        if seed_msg_id is not None:
            data["last_msg_id"][str(cid)] = int(seed_msg_id)
    save_data(data)
    return data["channels"]


def remove_channel(identifier) -> List[dict]:
    data = load_data()
    idx = _find_index(data, identifier)
    if idx != -1:
        removed = data["channels"].pop(idx)
        data["last_msg_id"].pop(str(removed.get("id")), None)
        save_data(data)
    return data["channels"]


def get_cursor(cid) -> int:
    return int(load_data().get("last_msg_id", {}).get(str(cid), 0))


def set_cursor(cid, msg_id: int) -> None:
    data = load_data()
    data.setdefault("last_msg_id", {})[str(cid)] = int(msg_id)
    save_data(data)


def _bare_channel_id(cid) -> Optional[int]:
    try:
        cid = int(cid)
    except (TypeError, ValueError):
        return None
    if cid < 0:
        a = abs(cid)
        if a > 1_000_000_000_000:
            return a - 1_000_000_000_000
        return a
    return cid


def _message_link(ch, msg_id) -> str:
    uname = (ch.get("username") or "").strip()
    if uname:
        return f"https://t.me/{uname}/{msg_id}"
    bare = _bare_channel_id(ch.get("id"))
    if bare:
        return f"https://t.me/c/{bare}/{msg_id}"
    return ""


def _message_line(ch, m) -> str:
    from ai_engine import ai
    try:
        tz = ai._local_tz()
        when = m.date.astimezone(tz).strftime("%Y-%m-%d %H:%M")
    except Exception:
        when = str(getattr(m, "date", ""))
    text = (getattr(m, "raw_text", None) or getattr(m, "message", None) or "").strip()
    text = " ".join(text.split())[:300]
    link = _message_link(ch, m.id)
    line = f"- [{ch.get('name') or 'کانال'} | {when}]"
    if link:
        line += f" (لینک: {link})"
    line += f": {text or '[پیام رسانه‌ای بدون متن]'}"
    return line


async def _resolve_entity(client, ch):
    """Resolve Telegram channel entity via username, access_hash, or ID cache."""
    uname = (ch.get("username") or "").strip()
    if uname:
        try:
            return await client.get_input_entity(uname)
        except Exception:
            pass
    bare = _bare_channel_id(ch.get("id"))
    ah = ch.get("access_hash")
    if bare and ah is not None:
        try:
            return tl_types.InputPeerChannel(channel_id=bare, access_hash=int(ah))
        except Exception:
            pass
    try:
        return await client.get_input_entity(ch["id"])
    except Exception:
        try:
            return await client.get_entity(ch["id"])
        except Exception:
            return None


async def summarize_once(client, status_callback=None) -> Optional[str]:
    """Execute one pass over subscribed channels; returns generated summary text or None."""
    from ai_engine import ai

    channels = get_channels()
    if not channels:
        return None

    group_id, _ = await home.ensure_home_group(client)
    topics = await home.ensure_home_topics(client, group_id)
    summary_topic = topics.get("summary") or 1
    home_entity = await client.get_input_entity(group_id)

    collected = []  # (ch, new_messages)
    for ch in channels:
        ent = await _resolve_entity(client, ch)
        if ent is None:
            logger.warning("Cannot resolve channel %s (%s)", ch.get("name"), ch.get("id"))
            continue
        try:
            msgs = await client.get_messages(ent, limit=MAX_NEW_PER_CHANNEL)
        except Exception as e:
            logger.warning("Failed to fetch messages for channel %s: %s", ch.get("name"), e)
            continue
        cursor = get_cursor(ch["id"])
        new_msgs = [m for m in (msgs or []) if m and getattr(m, "id", 0) > cursor]
        if not new_msgs:
            continue
        new_msgs.sort(key=lambda m: m.id)
        collected.append((ch, new_msgs))

    if not collected:
        return None

    # Construct input context strictly grounded on channel posts
    feed_lines = []
    for ch, new_msgs in collected:
        for m in new_msgs:
            feed_lines.append(_message_line(ch, m))

    prompt = (
        "تو دستیار شخصی هستی که خلاصه اخبار و مطالب جدید کانال‌های تلگرام را می‌سازد.\n"
        "مطالب زیر جدیدترین پست‌های کانال‌های منتخب کاربر هستند:\n\n"
        + "\n".join(feed_lines)
        + "\n\nلطفاً یک خلاصه فارسی دقیق و وفادار بنویس:\n"
        "- برای هر مطلب: نام کانال، زمان انتشار و (در صورت وجود) لینک پیام را نگه دار.\n"
        "- هیچ خبر، تاریخ، نام یا جزئیات ساختگی اضافه نکن؛ فقط بر اساس همین متن‌ها.\n"
        "- اگر مطالب زیاد است، آن‌ها را با تیتر کوتاه دسته‌بندی کن.\n"
        "- لحن صمیمی و روان باشد. خروجی فقط خود خلاصه باشد بدون مقدمه اضافی."
    )

    try:
        summary = await asyncio.to_thread(ai.ask_direct, prompt)
        summary = (summary or "").strip()
    except Exception as e:
        logger.error("Summary generation failed: %s", e)
        summary = ""

    if not summary:
        summary = "\n".join(feed_lines[:20])

    # Send summary to Capri Home summary topic (chunked if long)
    header = f"📰 **خلاصه کانال‌های منتخب** — {ai._today()}\n\n"
    body = header + summary
    for i in range(0, len(body), MAX_CHUNK):
        try:
            await client.send_message(home_entity, body[i:i + MAX_CHUNK], reply_to=summary_topic, link_preview=False)
        except Exception as e:
            logger.warning("Failed to send summary chunk: %s", e)
        await asyncio.sleep(0.5)

    # Advance cursors for processed channels
    for ch, new_msgs in collected:
        set_cursor(ch["id"], max(m.id for m in new_msgs))

    data = load_data()
    data["last_run_ts"] = time.time()
    save_data(data)
    return body


async def start_summary_loop(client) -> None:
    """Background scheduler loop; checks for new channel posts every 30 minutes."""
    logger.info("Starting channel summary scheduler loop...")
    while True:
        try:
            await asyncio.sleep(TICK_SEC)
            data = load_data()
            if time.time() - data.get("last_run_ts", 0) < INTERVAL_SEC:
                continue
            await summarize_once(client)
        except Exception as e:
            logger.error("Error in channel summary loop: %s", e, exc_info=True)
            await asyncio.sleep(TICK_SEC)
