import asyncio
import re

from telethon.tl.functions.channels import JoinChannelRequest, LeaveChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest

INVITE_RE = re.compile(r"t\.me/(?:joinchat/|\+|)([A-Za-z0-9_\-]+)")

STOP_WORDS = {"کانال", "کانالهای", "کانال های", "چنل", "گروه", "های", "رو", "توی", "داخل",
              "به", "از", "که", "همه", "همشون"}


def _norm(s: str) -> str:
    s = (s or "").replace("\u200c", " ")
    for a, b in (("ي", "ی"), ("ك", "ک"), ("\u200f", " "), ("\u200e", " ")):
        s = s.replace(a, b)
    for ch in ".:_-/":
        s = s.replace(ch, " ")
    return " ".join(s.lower().split())


def match_name(name: str, pattern: str) -> bool:
    toks = [t for t in _norm(pattern).split() if t not in STOP_WORDS]
    if not toks:
        return False
    n = _norm(name)
    for t in toks:
        if t in n:
            continue
        # پشتیبانی از پسوندهای فارسی (مثلاً کنکوری -> کنکور، کتاب‌ها -> کتاب)
        matched_stem = False
        for suffix in ("ها", "های", "ی", "ان", "ات"):
            if t.endswith(suffix) and len(t) - len(suffix) >= 3:
                stem = t[:-len(suffix)]
                if stem in n:
                    matched_stem = True
                    break
        if matched_stem:
            continue
        return False
    return True


async def find_channels(client, pattern: str, limit: int = 50, max_scan: int = 500):
    """کانال/گروه‌هایی که اسمشون شامل pattern هست رو برمی‌گردونه (لیست دیالوگ)."""
    out = []
    clean_p = pattern.lstrip("@").lower().strip()
    async for d in client.iter_dialogs(limit=max_scan):
        if not (d.is_channel or d.is_group):
            continue
        uname = (getattr(d.entity, "username", None) or "").lower()
        if (clean_p and uname == clean_p) or match_name(d.name, pattern):
            out.append(d)
            if len(out) >= limit:
                break
    return out


async def leave_dialogs(client, dialogs, delay: float = 0.8):
    """لیست دیالوگ‌ها رو لفت می‌ده. لیست اسم‌های لفت‌شده رو برمی‌گردونه."""
    left = []
    for d in dialogs:
        try:
            inp = await client.get_input_entity(d.entity)
            await client(LeaveChannelRequest(inp))
            left.append(d.name)
        except Exception:
            pass
        await asyncio.sleep(delay)
    return left


async def join_channel(client, target: str):
    """با یوزرنیم/لینک عضو می‌شه. (ok: bool, err: str|None) رو برمی‌گردونه."""
    target = (target or "").strip().strip("@،,:.؟? ")
    if not target:
        return False, "لینک یا اسم کانال رو بده."
    m = INVITE_RE.search(target)
    slug = m.group(1) if m else target
    is_invite = "joinchat/" in target or "+" in target
    try:
        if is_invite:
            res = await client(ImportChatInviteRequest(slug))
            return bool(getattr(res, "chats", None)), None
        await client(JoinChannelRequest(slug))
        return True, None
    except Exception as e:
        return False, str(e)
