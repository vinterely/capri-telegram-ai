"""Capri Emotional Sticker Library: sends contextual stickers from designated pack (Vinterely)."""
import json
import logging
import os
import random
import time

from core import config

log = logging.getLogger("stickers")

STICKER_PACK_SHORTNAME = getattr(config, "STICKER_PACK_SHORTNAME", None) or "Vinterely"
LIBRARY_FILE = os.path.join(config.BASE_DIR, "sticker_library.json")

# Mapping Persian emotion -> sticker emojis (each sticker is identified by its emoji attribute)
EMOTION_EMOJIS = {
    "خنده": ("😂", "🤣", "😆", "😹", "😄"),
    "شادی": ("🎉", "🥳", "✨", "😁", "🎊"),
    "غم": ("😢", "😭", "😔", "🥺", "💔"),
    "عشق": ("❤️", "😍", "🥰", "💕", "😘"),
    "تعجب": ("😮", "😱", "🤯", "😲"),
    "خشم": ("😠", "😡", "🤬", "💢"),
    "خستگی": ("😴", "🥱", "😪"),
    "چشمک": ("😉", "😏"),
    "تشویق": ("👏", "👍", "🙌", "💪"),
}

_CACHE = {"ts": 0.0, "library": None}
_SENT_AT: dict = {}  # chat_id -> timestamp of last sent sticker (for cooldown enforcement)
_LAST_ERROR: str = ""


def _load_library() -> dict:
    try:
        with open(LIBRARY_FILE, encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {}


def _save_library(data: dict) -> None:
    try:
        from core import fsutil
        fsutil.atomic_write_json(LIBRARY_FILE, data)
    except Exception as e:
        log.warning("Failed to save sticker library: %s", e)


def _sticker_emoji(doc) -> str:
    from telethon.tl.types import DocumentAttributeSticker
    for attr in (getattr(doc, "attributes", None) or []):
        if isinstance(attr, DocumentAttributeSticker):
            return (getattr(attr, "alt", "") or "").strip()
    return ""


async def refresh_library(client) -> dict:
    """Fetch sticker set from Telegram and build emotion -> list of file_ids mapping."""
    global _LAST_ERROR
    from telethon.tl.functions.messages import GetStickerSetRequest
    from telethon.tl.types import InputStickerSetShortName
    from telethon import utils

    try:
        result = await client(GetStickerSetRequest(
            stickerset=InputStickerSetShortName(STICKER_PACK_SHORTNAME),
            hash=0
        ))
    except Exception as e:
        _LAST_ERROR = str(e)
        log.warning("Failed to fetch sticker pack %s: %s", STICKER_PACK_SHORTNAME, e)
        return _load_library()
    _LAST_ERROR = ""

    emoji_to_ids: dict = {}
    for doc in (result.documents or []):
        emoji = _sticker_emoji(doc)
        if not emoji:
            continue
        try:
            fid = utils.pack_bot_file_id(doc)
        except Exception:
            continue
        if fid:
            emoji_to_ids.setdefault(emoji, [])
            if fid not in emoji_to_ids[emoji]:
                emoji_to_ids[emoji].append(fid)

    library: dict = {}
    for emotion, emojis in EMOTION_EMOJIS.items():
        ids = []
        for em in emojis:
            ids.extend(emoji_to_ids.get(em, []))
        if ids:
            library[emotion] = ids

    if library:
        _save_library(library)
        _CACHE["library"] = library
        _CACHE["ts"] = time.time()
        log.info("Sticker library built from pack %s: %d emotions, %d stickers",
                 STICKER_PACK_SHORTNAME, len(library), sum(len(v) for v in library.values()))
    else:
        log.warning("Sticker pack %s fetched (%d docs) but no stickers matched emotion emojis",
                    STICKER_PACK_SHORTNAME, len(result.documents or []))
    return library or _load_library()


def last_error() -> str:
    """Get the last error from fetching the sticker pack for diagnostics."""
    return _LAST_ERROR or ""


def get_library() -> dict:
    """Read sticker library from cache or disk without network roundtrips."""
    if _CACHE["library"] is not None:
        return _CACHE["library"]
    _CACHE["library"] = _load_library()
    _CACHE["ts"] = time.time()
    return _CACHE["library"]


async def ensure_library(client) -> dict:
    """Return sticker library; fetches from Telegram network only if unpopulated."""
    lib = get_library()
    if lib:
        return lib
    return await refresh_library(client)


def pick_sticker(emotion: str) -> str:
    """Pick a random sticker file_id for the given emotion."""
    emotion = (emotion or "").strip()
    lib = get_library()
    ids = lib.get(emotion)
    if not ids:
        for e, eids in lib.items():
            if emotion and (emotion in e or e in emotion):
                ids = eids
                break
    if not ids:
        return ""
    return random.choice(ids)


def _cooldown_ok(chat_id, cooldown: int) -> bool:
    if cooldown <= 0:
        return True
    now = time.time()
    last = _SENT_AT.get(chat_id, 0.0)
    if now - last < cooldown:
        return False
    _SENT_AT[chat_id] = now
    return True


async def send_sticker(client, chat_id, emotion: str, cooldown: int = 0) -> bool:
    """Send an emotional sticker with per-chat anti-spam cooldown protection."""
    if not _cooldown_ok(chat_id, cooldown):
        return False
    fid = pick_sticker(emotion)
    if not fid:
        return False
    try:
        await client.send_file(chat_id, fid)
        return True
    except Exception as e:
        log.warning("Failed to send sticker (%s): %s", emotion, e)
        return False
