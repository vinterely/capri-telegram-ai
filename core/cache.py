import hashlib
import json
import os
import threading
import time

from core import config

FILE = os.path.join(config.BASE_DIR, "cache.json")
DEFAULT_TTL = 6 * 3600
MAX_ENTRIES = 2000

_lock = threading.Lock()
_data = None


def _load() -> dict:
    global _data
    if _data is None:
        try:
            with open(FILE, encoding="utf-8") as f:
                raw = json.load(f)
            _data = raw if isinstance(raw, dict) else {}
        except Exception:
            _data = {}
    return _data


def _save() -> None:
    try:
        from core import fsutil
        fsutil.atomic_write_json(FILE, _data)
    except Exception:
        pass


def make_key(*parts) -> str:
    blob = "\x1f".join(str(p) for p in parts)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:24]


def get(key: str):
    with _lock:
        d = _load()
        e = d.get(key)
        if not e:
            return None
        if time.time() - e.get("t", 0) > e.get("ttl", DEFAULT_TTL):
            d.pop(key, None)
            return None
        return e.get("v")


def set(key: str, value, ttl: int = DEFAULT_TTL) -> None:
    with _lock:
        d = _load()
        d[key] = {"v": value, "t": time.time(), "ttl": ttl}
        if len(d) > MAX_ENTRIES:
            items = sorted(d.items(), key=lambda kv: kv[1].get("t", 0))
            for k, _ in items[:len(d) - MAX_ENTRIES]:
                d.pop(k, None)
        _save()
