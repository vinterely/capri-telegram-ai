import asyncio

from telethon import functions, types

GLOBAL_LIMIT = 20


def _norm(s: str) -> str:
    for ch in ".:_-/":
        s = s.replace(ch, " ")
    return " ".join(s.lower().split())


def _score(text: str, query: str) -> int:
    t = _norm(text)
    q = _norm(query)
    if not q:
        return 0
    if q in t:
        return 100
    words = [w for w in q.split() if len(w) >= 4]
    return sum(15 for w in words if w in t)


def _filename(m) -> str:
    if not m or not m.media:
        return ""
    if hasattr(m.media, "document"):
        for a in m.media.document.attributes:
            if hasattr(a, "file_name"):
                return a.file_name
    return ""


def _audio_title(m) -> str:
    if not m or not m.media:
        return ""
    if hasattr(m.media, "document"):
        for a in m.media.document.attributes:
            if hasattr(a, "title"):
                parts = [a.title, getattr(a, "performer", "")]
                return " - ".join(p for p in parts if p)
    return ""


async def _global(client, query: str, filt):
    res = await client(functions.messages.SearchGlobalRequest(
        q=query,
        filter=filt if filt is not None else types.InputMessagesFilterEmpty(),
        min_date=None,
        max_date=None,
        offset_rate=0,
        offset_peer=types.InputPeerEmpty(),
        offset_id=0,
        limit=GLOBAL_LIMIT,
    ))
    return res.messages


def _rank(msgs, query: str):
    """پیام‌های جستجو شده رو امتیازبندی و مرتب می‌کنه."""
    results = []
    seen = set()
    seen_files = set()
    for m in msgs:
        if not m or m.out:
            continue
        pid = getattr(m.peer_id, "channel_id", None) or getattr(m.peer_id, "user_id", None)
        key = (pid, m.id)
        if key in seen:
            continue
        seen.add(key)

        fname = _filename(m)
        atitle = _audio_title(m)
        text = m.message or ""
        score = max(_score(fname, query), _score(atitle, query), _score(text, query))
        if score <= 0:
            continue
        if fname or atitle:
            fkey = _norm(fname or atitle)
            if fkey in seen_files:
                continue
            seen_files.add(fkey)
            kind = "file"
        elif m.photo:
            kind = "photo"
        else:
            # متن خالی‌فقط اگه لینک دانلود (t.me) داشته باشه مفیده
            if "t.me/" not in text:
                continue
            kind = "text"

        results.append({
            "score": score,
            "kind": kind,
            "name": fname or atitle or text[:60],
            "text": text,
            "msg": m,
        })

    results.sort(key=lambda r: -r["score"])
    return results


async def find_files(client, query: str, limit: int = 3, kind: str = ""):
    if not query.strip():
        return []

    k = (kind or "").strip().lower()
    if k == "music":
        return _rank(await _global(client, query, types.InputMessagesFilterMusic()), query)[:limit]
    if k == "video":
        return _rank(await _global(client, query, types.InputMessagesFilterVideo()), query)[:limit]
    if k == "document":
        return _rank(await _global(client, query, types.InputMessagesFilterDocument()), query)[:limit]

    # جستجوی سراسری توی همه‌ی کانال‌ها: کپشن + سند + ویدیو + موزیک
    msgs = await _global(client, query, None)
    try:
        msgs += await _global(client, query, types.InputMessagesFilterDocument())
        msgs += await _global(client, query, types.InputMessagesFilterVideo())
        msgs += await _global(client, query, types.InputMessagesFilterMusic())
    except Exception:
        pass

    return _rank(msgs, query)[:limit]


MEDIA_FILTERS = {
    "video": types.InputMessagesFilterVideo(),
    "document": types.InputMessagesFilterDocument(),
    "music": types.InputMessagesFilterMusic(),
    "photo": types.InputMessagesFilterPhotos(),
}


def media_filter(kind: str):
    for k, f in MEDIA_FILTERS.items():
        if k in (kind or "").lower():
            return f
    return None


async def find_in_channel(client, entity, query: str, limit: int = 5, kind: str = ""):
    """جستجوی پیشرفته: توی یه کانال خاص (با فیلتر نوع رسانه)."""
    if not query.strip():
        return []
    msgs = []
    try:
        msgs = await client.get_messages(entity, search=query, filter=media_filter(kind), limit=limit * 2)
    except Exception:
        try:
            msgs = await client.get_messages(entity, search=query, limit=limit * 2)
        except Exception:
            return []
    return _rank(msgs, query)[:limit]
