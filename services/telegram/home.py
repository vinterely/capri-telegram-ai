"""Capri Home Management Supergroup, Dialog Folder, and Forum Topics.

Bootstraps and manages Capri's private Telegram administration structure:
- A private forum supergroup (default title: '🏠 Capri Home | مدیریت کاپری').
- A Telegram dialog folder named 'capri' containing Home and Vault supergroups.
- Dedicated forum topics for 'backup' and 'summary' inside the Home supergroup.
All IDs are persisted in home.json to avoid recreating structures across restarts.
"""
import json
import logging
import os
import random
from typing import Dict, Optional, Tuple

from telethon import functions, types, utils as tl_utils

from core import config, fsutil

logger = logging.getLogger("home")

HOME_FILE = os.path.join(config.BASE_DIR, "home.json")

# Default forum topics for Capri Home group
HOME_TOPICS = [
    {
        "key": "backup",
        "title": "🗂 بکاپ",
        "color": 0x8EEE98,
        "description": "بکاپ پیام‌های مالک پیش از حذف",
    },
    {
        "key": "summary",
        "title": "📰 خلاصه کانال‌ها",
        "color": 0x6FB9F0,
        "description": "خلاصه دوره‌ای کانال‌های منتخب مالک",
    },
]

HOME_TOPIC_TITLE_MAP = {t["key"]: t["title"] for t in HOME_TOPICS}


def load_home_data() -> dict:
    """Load Home registry from local JSON file."""
    data = {}
    if os.path.exists(HOME_FILE):
        try:
            with open(HOME_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    data = loaded
        except Exception:
            data = {}
    data.setdefault("group_id", None)
    data.setdefault("peer_id", None)
    data.setdefault("group_title", config.HOME_GROUP_TITLE)
    data.setdefault("group_invite_link", "")
    data.setdefault("folder_id", None)
    data.setdefault("topics", {})
    return data


def save_home_data(data: dict) -> None:
    fsutil.atomic_write_json(HOME_FILE, data)


def get_home_group_id() -> Optional[int]:
    """Return Capri Home group ID if provisioned, else None."""
    gid = load_home_data().get("group_id")
    return int(gid) if gid is not None else None


def get_home_peer_id() -> Optional[int]:
    """Return normalized peer ID for Capri Home group."""
    pid = load_home_data().get("peer_id")
    return int(pid) if pid is not None else None


def _norm_peer(pid) -> Optional[int]:
    try:
        return int(pid)
    except (TypeError, ValueError):
        return None


def is_home_chat(chat_id) -> bool:
    """Check if the given chat_id corresponds to Capri Home group."""
    if chat_id is None:
        return False
    cid = _norm_peer(chat_id)
    if cid is None:
        return False
    gid = get_home_group_id()
    pid = get_home_peer_id()
    for stored in (pid, gid):
        s = _norm_peer(stored)
        if s is None:
            continue
        if cid == s:
            return True
        # مگاگروپ: id پایه (مثبت) در برابر id کامل (منفی با پیشوند -100)
        if s > 0 and cid < 0:
            if abs(cid) == 1000000000000 + s or abs(cid) == s:
                return True
        if s < 0 and cid > 0:
            if abs(s) == 1000000000000 + cid or abs(s) == cid:
                return True
    return False


def is_home_backup_message(event) -> bool:
    """Check if event is inside the 'backup' topic of Home group (never process AI replies here)."""
    try:
        data = load_home_data()
        entry = (data.get("topics") or {}).get("backup") or {}
        tid = entry.get("id") if isinstance(entry, dict) else None
        if not tid:
            return False
        msg = getattr(event, "message", None)
        reply = getattr(msg, "reply_to", None)
        if reply is None:
            reply = getattr(event, "reply_to", None)
        top = (
            getattr(reply, "reply_to_top_id", None)
            or getattr(reply, "reply_to_msg_id", None)
            or getattr(event, "reply_to_msg_id", None)
        )
        return int(top or 0) == int(tid)
    except Exception:
        return False


async def ensure_home_group(client, status_callback=None) -> Tuple[Optional[int], str]:
    """Ensure Capri Home supergroup exists; creates one if missing or inaccessible."""
    data = load_home_data()
    group_id = data.get("group_id")
    invite_link = data.get("group_invite_link", "")

    if group_id:
        try:
            entity = await client.get_entity(group_id)
            if entity:
                logger.info("Existing Capri Home group found: ID=%s", group_id)
                return group_id, invite_link
        except Exception as e:
            logger.warning("Previous Capri Home group inaccessible (%s); creating a new one...", e)

    if status_callback:
        await status_callback("🔨 در حال ساخت گروه مدیریتی خصوصی «Capri Home»...")

    title = config.HOME_GROUP_TITLE
    about = "فضای مدیریتی خصوصی کاپری — ارتباط مستقیم، بکاپ پیام‌ها و خلاصه کانال‌های منتخب."

    try:
        created = await client(functions.channels.CreateChannelRequest(
            title=title,
            about=about,
            megagroup=True,
            forum=True,
        ))
        chat = created.chats[0]
        group_id = chat.id
    except Exception as e:
        logger.error("Failed to create Capri Home supergroup: %s", e)
        raise RuntimeError(f"Telegram supergroup creation failed: {e}")

    # Enable forum topics
    try:
        await client(functions.channels.ToggleForumRequest(channel=chat, enabled=True, tabs=False))
    except Exception as e:
        logger.debug("ToggleForumRequest info/skipped: %s", e)

    try:
        invite = await client(functions.messages.ExportChatInviteRequest(peer=chat))
        invite_link = getattr(invite, "link", "")
    except Exception as e:
        logger.warning("Failed to export Capri Home invite link: %s", e)
        invite_link = ""

    try:
        await client(functions.messages.ToggleDialogPinRequest(peer=chat, pinned=True))
    except Exception as e:
        logger.debug("Failed to pin Capri Home dialog: %s", e)

    try:
        welcome = (
            "🏠 **به Capri Home خوش آمدید!**\n\n"
            "این فضای مدیریتی خصوصی کاپری است. اینجا می‌توانید بدون نوشتن نام «کاپری» مستقیم گفتگو کنید، "
            "بکاپ پیام‌های حذف‌شده را ببینید و خلاصه کانال‌های منتخب‌تان را دنبال کنید.\n\n"
            "🗂 تاپیک «بکاپ»: بکاپ پیام‌ها پیش از حذف\n"
            "📰 تاپیک «خلاصه کانال‌ها»: خلاصه دوره‌ای کانال‌های منتخب"
        )
        wmsg = await client.send_message(chat, welcome)
        await client.pin_message(chat, wmsg.id)
    except Exception as e:
        logger.debug("Failed to send/pin Capri Home welcome: %s", e)

    data["group_id"] = group_id
    try:
        data["peer_id"] = tl_utils.get_peer_id(chat)
    except Exception:
        data["peer_id"] = group_id
    data["group_title"] = title
    data["group_invite_link"] = invite_link
    save_home_data(data)
    logger.info("Capri Home supergroup created: ID=%s", group_id)
    return group_id, invite_link


async def ensure_home_topics(client, group_id: int, status_callback=None) -> Dict[str, int]:
    """Ensure backup and summary forum topics exist; returns {key: topic_id}."""
    data = load_home_data()
    cached_topics = data.get("topics", {})
    entity = await client.get_input_entity(group_id)

    existing_by_title: Dict[str, int] = {}
    try:
        res = await client(functions.messages.GetForumTopicsRequest(
            peer=entity,
            offset_date=None,
            offset_id=0,
            offset_topic=0,
            limit=100,
        ))
        for t in getattr(res, "topics", []):
            if isinstance(t, types.ForumTopic):
                existing_by_title[t.title.strip().lower()] = t.id
    except Exception as e:
        logger.warning("Failed to fetch Capri Home topics: %s", e)

    topic_map: Dict[str, int] = {}

    for t_def in HOME_TOPICS:
        key = t_def["key"]
        title = t_def["title"]
        clean_title = title.strip().lower()

        if clean_title in existing_by_title:
            topic_map[key] = existing_by_title[clean_title]
            cached_topics[key] = {"id": existing_by_title[clean_title], "title": title}
            continue

        if key in cached_topics and cached_topics[key].get("id") in existing_by_title.values():
            topic_map[key] = cached_topics[key]["id"]
            continue

        try:
            created_res = await client(functions.messages.CreateForumTopicRequest(
                peer=entity,
                title=title,
                icon_color=t_def["color"],
                random_id=random.randint(1, 2**63 - 1),
            ))
            topic_id = None
            for u in getattr(created_res, "updates", []):
                m = getattr(u, "message", None)
                if m and getattr(m, "id", None):
                    topic_id = m.id
                    break
            if not topic_id:
                res_check = await client(functions.messages.GetForumTopicsRequest(
                    peer=entity, offset_date=None, offset_id=0, offset_topic=0, limit=20,
                ))
                for t in getattr(res_check, "topics", []):
                    if isinstance(t, types.ForumTopic) and t.title.strip().lower() == clean_title:
                        topic_id = t.id
                        break
            if topic_id:
                topic_map[key] = topic_id
                cached_topics[key] = {"id": topic_id, "title": title}
                logger.info("Capri Home topic created: %s -> %s", title, topic_id)
            else:
                topic_map[key] = 1
        except Exception as e:
            logger.error("Failed to create Capri Home topic %s: %s", title, e)
            topic_map[key] = 1

    data["topics"] = cached_topics
    save_home_data(data)
    return topic_map


async def ensure_capri_folder(client, status_callback=None) -> Optional[int]:
    """Ensure 'capri' dialog folder exists (containing Home and Vault supergroups)."""
    from services.telegram import folders, vault

    peers = []
    for pid in (get_home_group_id(), vault.load_vault_data().get("group_id")):
        if not pid:
            continue
        try:
            peers.append(await client.get_input_entity(pid))
        except Exception:
            continue

    existing = await folders.list_folders(client)
    found = folders.find_folder(existing, config.CAPRI_FOLDER_TITLE)

    if found:
        if peers:
            try:
                await folders.assign_to_folder(client, found, [p for p in peers])
            except Exception as e:
                logger.debug("Failed to assign peers to capri folder: %s", e)
        data = load_home_data()
        data["folder_id"] = found.get("id")
        save_home_data(data)
        return found.get("id")

    if not peers:
        logger.warning("Cannot create capri folder: no peers available yet.")
        return None

    if status_callback:
        await status_callback("🗂 در حال ساخت پوشه‌ی «capri»...")
    try:
        folder, err = await folders.create_folder(client, config.CAPRI_FOLDER_TITLE, peers)
    except Exception as e:
        err = str(e)
        folder = None
    if folder is None:
        logger.warning("Failed to create capri folder: %s", err)
        return None

    data = load_home_data()
    data["folder_id"] = folder.get("id")
    save_home_data(data)
    return folder.get("id")


async def setup_home(client, status_callback=None) -> Dict[str, any]:
    """Idempotently bootstrap entire Capri Home structure: group, topics, and folder."""
    result = {"group_id": None, "topics": {}, "folder_id": None, "invite_link": ""}
    group_id, invite = await ensure_home_group(client, status_callback)
    result["group_id"] = group_id
    result["invite_link"] = invite
    if group_id:
        result["topics"] = await ensure_home_topics(client, group_id, status_callback)
        result["folder_id"] = await ensure_capri_folder(client, status_callback)
    return result
