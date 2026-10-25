import json
import os
import re

from core import config

MEMORY_FILE = os.path.join(config.BASE_DIR, "memory.json")

MAX_FACTS = 500
MAX_HISTORY = 100


def _load() -> dict:
    try:
        with open(MEMORY_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"facts": [], "history": {}}


def _save(data: dict) -> None:
    from core import fsutil
    fsutil.atomic_write_json(MEMORY_FILE, data)


def load_memory() -> str:
    facts = _load().get("facts", [])
    return "\n".join(f"- {x}" for x in facts)


def _similarity(qtoks, ftoks) -> int:
    s = 0
    for q in qtoks:
        for w in ftoks:
            if q == w:
                s += 2
            elif w.startswith(q) or q.startswith(w):
                s += 1
    return s


def relevant_facts(question: str, limit: int = 8) -> str:
    """حقایق مرتبط با سوال رو (بر اساس همپوشانی کلمه‌ها) برمی‌گردونه تا پرامپت کوچیک بمونه."""
    facts = _load().get("facts", [])
    if not facts:
        return ""
    qtoks = set(_tokens(question or ""))
    if not qtoks:
        return "\n".join(f"- {x}" for x in facts[:limit])
    scored = [(f, _similarity(qtoks, set(_tokens(f)))) for f in facts]
    scored.sort(key=lambda x: x[1], reverse=True)
    return "\n".join(f"- {f}" for f, s in scored[:limit] if s > 0)


def _norm_fact(s: str) -> str:
    return " ".join(re.sub(r"[«»\"'،,.:؟?()\-_/]", " ", s).split())


def _jaccard(toks1: set, toks2: set) -> float:
    if not toks1 or not toks2:
        return 0.0
    inter = len(toks1 & toks2)
    union = len(toks1 | toks2)
    return inter / union if union > 0 else 0.0


def add_memory(fact: str) -> None:
    data = _load()
    facts = data.setdefault("facts", [])
    norm = _norm_fact(fact)
    if not norm:
        return
    toks = set(_tokens(fact))
    for f in facts:
        if _norm_fact(f) == norm:
            return
        if toks and _jaccard(toks, set(_tokens(f))) >= 0.8:
            return
    facts.append(fact)
    data["facts"] = facts[-MAX_FACTS:]
    _save(data)


def _tokens(s: str):
    s = re.sub(r"[«»\"'،,.:؟?()\-_/]", " ", s)
    return [w for w in s.split() if len(w) >= 4]


def remove_memory(keyword: str):
    """حذف واقعیت‌هایی که با کلمه‌ی کلیدی مرتبط‌ان. لیست حذف‌شده‌ها رو برمی‌گردونه."""
    data = _load()
    facts = data.get("facts", [])
    qtoks = _tokens(keyword)
    if not qtoks:
        return []
    removed, keep = [], []
    for f in facts:
        ftoks = _tokens(f)
        hit = any(q == w or w.startswith(q) or q.startswith(w) for q in qtoks for w in ftoks)
        if hit:
            removed.append(f)
        else:
            keep.append(f)
    if removed:
        data["facts"] = keep
        _save(data)
    return removed


def list_facts():
    return list(_load().get("facts", []))


def clear_memory() -> None:
    data = _load()
    data["facts"] = []
    _save(data)


def remember_exchange(chat_id, user_msg: str, bot_reply: str) -> None:
    data = _load()
    hist = data.setdefault("history", {})
    key = str(chat_id)
    entries = hist.setdefault(key, [])
    entries.append({"user": user_msg[:500], "bot": bot_reply[:500]})
    hist[key] = entries[-MAX_HISTORY:]
    _save(data)


def load_history(chat_id) -> str:
    entries = _load().get("history", {}).get(str(chat_id), [])
    if not entries:
        return ""
    lines = []
    for e in entries:
        lines.append(f"کاربر: {e['user']}")
        lines.append(f"{config.ASSISTANT_NAMES[0]}: {e['bot']}")
    return "\n".join(lines)
