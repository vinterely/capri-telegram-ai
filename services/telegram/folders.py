import random

from telethon import types
from telethon.tl.functions.messages import GetDialogFiltersRequest, UpdateDialogFilterRequest


def _title_text(title) -> str:
    if isinstance(title, str):
        return title
    if hasattr(title, "text"):
        return title.text
    return ""


def _norm(s: str) -> str:
    for ch in ".:_-/":
        s = s.replace(ch, " ")
    return " ".join((s or "").lower().split())


async def list_folders(client):
    """پوشه‌های فعلی رو برمی‌گردونه: [{id, title, obj}]"""
    res = await client(GetDialogFiltersRequest())
    out = []
    for f in (res.filters or []):
        if isinstance(f, types.DialogFilterDefault):
            continue
        title = _title_text(getattr(f, "title", ""))
        if not title and isinstance(f, types.DialogFilterChatlist):
            title = getattr(f, "emoticon", "") or ""
        out.append({"id": getattr(f, "id", 0), "title": title, "obj": f})
    return out


def find_folder(folders, title: str):
    """پوشه‌ای که اسمش شامل title باشه رو برمی‌گردونه یا None."""
    t = _norm(title)
    for f in folders:
        if t and (t in _norm(f["title"]) or _norm(f["title"]) in t):
            return f
    return None


async def _to_input_peers(client, entities):
    peers = []
    for e in entities:
        try:
            peers.append(await client.get_input_entity(e))
        except Exception:
            pass
    return peers


async def create_folder(client, title: str, peers=None):
    """پوشه‌ی جدید می‌سازه (با حداقل یه کانال؛ تلگرام پوشه‌ی خالی نمی‌ده).

    برمی‌گردونه (folder_dict, err). folder_dict مثل list_folders هست.
    """
    title = (title or "").strip()
    if not title:
        return None, "اسم پوشه رو بگو."
    include = await _to_input_peers(client, peers or [])
    if not include:
        return None, "تلگرام اجازه‌ی پوشه‌ی خالی نمی‌ده؛ حداقل یه کانال توش بذار."
    existing = await list_folders(client)
    fid = max([f["id"] for f in existing] + [1]) + 1
    if fid < 2:
        fid = random.randint(100, 10_000_000)
    filt = types.DialogFilter(
        id=fid,
        title=types.TextWithEntities(text=title, entities=[]),
        pinned_peers=[],
        include_peers=include,
        exclude_peers=[],
    )
    try:
        await client(UpdateDialogFilterRequest(id=fid, filter=filt))
        return {"id": fid, "title": title, "obj": filt}, None
    except Exception as e:
        return None, str(e)


async def delete_folder(client, folder) -> bool:
    try:
        await client(UpdateDialogFilterRequest(id=folder["id"], filter=None))
        return True
    except Exception:
        return False


async def _update_folder(client, folder, include_peers):
    f = folder["obj"]
    return await client(UpdateDialogFilterRequest(
        id=f.id,
        filter=types.DialogFilter(
            id=f.id,
            title=getattr(f, "title", ""),
            pinned_peers=getattr(f, "pinned_peers", None) or [],
            include_peers=include_peers,
            exclude_peers=getattr(f, "exclude_peers", None) or [],
            contacts=getattr(f, "contacts", None),
            non_contacts=getattr(f, "non_contacts", None),
            groups=getattr(f, "groups", None),
            broadcasts=getattr(f, "broadcasts", None),
            bots=getattr(f, "bots", None),
            exclude_muted=getattr(f, "exclude_muted", None),
            exclude_read=getattr(f, "exclude_read", None),
            exclude_archived=getattr(f, "exclude_archived", None),
            emoticon=getattr(f, "emoticon", None),
        ),
    ))


async def assign_to_folder(client, folder, entities) -> int:
    """کانال‌ها رو به پوشه اضافه می‌کنه. تعداد اضافه‌شده رو برمی‌گردونه."""
    f = folder["obj"]
    existing = list(getattr(f, "include_peers", None) or [])
    seen = set()
    for p in existing:
        seen.add((type(p).__name__, getattr(p, "channel_id", None) or getattr(p, "chat_id", None)))
    new = await _to_input_peers(client, entities)
    added = 0
    for p in new:
        key = (type(p).__name__, getattr(p, "channel_id", None) or getattr(p, "chat_id", None))
        if key not in seen:
            existing.append(p)
            seen.add(key)
            added += 1
    if added:
        await _update_folder(client, folder, existing)
    return added
