"""کنترل دسترسی کاربران به کاپری (allow/deny).

صاحب اکانت با «کاپری جوابشو بده» یا «کاپری جوابشو نده» تعیین می‌کند کدام کاربران
(به‌جز خودش) حق صدا زدن کاپری را دارند. به‌طور پیش‌فرض غریبه‌ها جواب نمی‌گیرند.
"""
import json
import os

from core import config

FILE = os.path.join(config.BASE_DIR, "access.json")

DEFAULTS = {"allow": [], "deny": []}


def load() -> dict:
    try:
        with open(FILE, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}
    d = dict(DEFAULTS)
    for k in DEFAULTS:
        v = data.get(k)
        if isinstance(v, list):
            d[k] = [int(x) for x in v if str(x).lstrip("-").isdigit()]
    return d


def _save(data: dict) -> None:
    from core import fsutil
    fsutil.atomic_write_json(FILE, data)


def get_allowed_users() -> list:
    """دریافت لیست شناسه عددی تمام کاربران مجاز."""
    return list(load().get("allow", []))


def is_denied(uid) -> bool:
    if uid is None:
        return True
    try:
        return int(uid) in load()["deny"]
    except (ValueError, TypeError):
        return True


def is_allowed(uid) -> bool:
    if uid is None:
        return False
    try:
        return int(uid) in load()["allow"]
    except (ValueError, TypeError):
        return False


def allow_user(uid: int) -> None:
    d = load()
    uid = int(uid)
    if uid in d["deny"]:
        d["deny"].remove(uid)
    if uid not in d["allow"]:
        d["allow"].append(uid)
    _save(d)


def deny_user(uid: int) -> None:
    d = load()
    uid = int(uid)
    if uid in d["allow"]:
        d["allow"].remove(uid)
    if uid not in d["deny"]:
        d["deny"].append(uid)
    _save(d)
