import sys
if __name__ == "__main__":
    sys.modules["bot"] = sys.modules["__main__"]

import asyncio
import os
import re
import time
from collections import deque
from typing import Any, Optional

from telethon import Button, TelegramClient, events, types

from core import access
from ai_engine import agent
from ai_engine import ai
from services.social import briefing
from services.social import chatanalysis
from services.telegram import channels
from core import config
from services.media import fetch
from services.telegram import folders
from services.telegram import vault
from services.telegram import reactions
from services.social import ghost
from services.social import dnd
from services.search import gsearch
from core import memory
from ai_engine import models
from ai_engine import providers
from services.search import search
from core import settings
from services.study import study
from ai_engine import tools
from services.voice import voice
from services.media import ytsummary
from core import cognitive_memory
from services.social import drafter
from core import logger
from services.social import memegen
from services.social import roast
from services.social import roleplay
from services.social import vibecheck

log = logger.get_logger(__name__)

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

client = TelegramClient(config.SESSION_FILE, config.API_ID, config.API_HASH, proxy=config.get_proxy(), flood_sleep_threshold=120)

START_TIME = time.time()

def _get_uptime_str() -> str:
    uptime_sec = int(time.time() - START_TIME)
    h = uptime_sec // 3600
    m = (uptime_sec % 3600) // 60
    s = uptime_sec % 60
    if h > 0:
        return f"{h} ساعت و {m} دقیقه"
    if m > 0:
        return f"{m} دقیقه و {s} ثانیه"
    return f"{s} ثانیه"

class _BoundedIdSet:
    """مجموعه‌ی با سقف ثابت از شناسه‌های پیام ارسال‌شده (جلوگیری از رشد نامحدود حافظه)."""
    def __init__(self, max_size: int = 2000):
        self.max_size = max_size
        self._set = set()
        self._order = deque()

    def add(self, x) -> None:
        if x in self._set:
            return
        self._set.add(x)
        self._order.append(x)
        while len(self._order) > self.max_size:
            self._set.discard(self._order.popleft())

    def clear(self) -> None:
        self._set.clear()
        self._order.clear()

    def __contains__(self, x) -> bool:
        return x in self._set


self_sent = _BoundedIdSet()


def neutralize_triggers(text: str) -> str:
    """خنثی‌کردن تریگر در خروجی بات با کاراکتر نیم‌فاصله یا نامرئی تا کلمه فعال‌ساز در متن خام وجود نداشته باشد."""
    if not text or not isinstance(text, str):
        return text
    # شکستن کاپری با نیم‌فاصله (\u200c)
    t = re.sub(r"[کك]\s*[اآ]\s*پ\s*ر\s*[یي]", "کا\u200cپری", text, flags=re.IGNORECASE)
    # شکستن capri با zero-width space (\u200b)
    t = re.sub(r"c\s*a\s*p\s*r\s*i", "ca\u200bpri", t, flags=re.IGNORECASE)
    return t


def register_self_sent(item, default_chat_id=None) -> None:
    """ثبت مطمئن پیام‌های ارسالی یا فورواردشده به صورت تاپل (chat_id, message_id) جهت جلوگیری از تداخل چت‌ها."""
    if item is None:
        return
    if isinstance(item, tuple) and len(item) == 2:
        try:
            self_sent.add((int(item[0]), int(item[1])))
            self_sent.add(int(item[1]))
        except (ValueError, TypeError):
            pass
        return
    if isinstance(item, (list, tuple, set)):
        for x in item:
            register_self_sent(x, default_chat_id)
        return
    if hasattr(item, "id"):
        try:
            mid = int(item.id)
            cid = getattr(item, "chat_id", None)
            if cid is None and hasattr(item, "peer_id"):
                peer = item.peer_id
                cid = getattr(peer, "user_id", None) or getattr(peer, "chat_id", None) or getattr(peer, "channel_id", None)
            if cid is None and default_chat_id is not None:
                cid = default_chat_id
            if cid is not None:
                self_sent.add((int(cid), mid))
            self_sent.add(mid)
        except (ValueError, TypeError):
            pass
    elif isinstance(item, (int, str)):
        try:
            mid = int(item)
            self_sent.add(mid)
            if default_chat_id is not None:
                self_sent.add((int(default_chat_id), mid))
        except (ValueError, TypeError):
            pass


def _wrap_client_message_senders(cl):
    """
    رپ کردن تمامی متدهای ارسال و فوروارد پیام کلاینت جهت خنثی‌سازی تریگر و ثبت خودکار در self_sent.
    هر خروجی بات قبل از ارسال تریگرهایش شکسته می‌شود و آیدی تک‌تک پیام‌ها در تاپل (chat_id, message_id) ثبت می‌گردد.
    """
    orig_send_message = cl.send_message
    orig_send_file = cl.send_file
    orig_forward_messages = cl.forward_messages

    async def wrapped_send_message(entity, *args, **kwargs):
        if args:
            new_args = list(args)
            if isinstance(new_args[0], str):
                new_args[0] = neutralize_triggers(new_args[0])
            args = tuple(new_args)
        if "message" in kwargs and isinstance(kwargs["message"], str):
            kwargs["message"] = neutralize_triggers(kwargs["message"])

        res = await orig_send_message(entity, *args, **kwargs)
        cid = getattr(entity, "id", None) or (int(entity) if isinstance(entity, int) else None)
        register_self_sent(res, default_chat_id=cid)
        return res

    async def wrapped_send_file(entity, file, *args, **kwargs):
        if "caption" in kwargs:
            cap = kwargs["caption"]
            if isinstance(cap, str):
                kwargs["caption"] = neutralize_triggers(cap)
            elif isinstance(cap, (list, tuple)):
                kwargs["caption"] = [neutralize_triggers(c) if isinstance(c, str) else c for c in cap]
        elif len(args) >= 1 and isinstance(args[0], str):
            new_args = list(args)
            new_args[0] = neutralize_triggers(new_args[0])
            args = tuple(new_args)

        res = await orig_send_file(entity, file, *args, **kwargs)
        cid = getattr(entity, "id", None) or (int(entity) if isinstance(entity, int) else None)
        register_self_sent(res, default_chat_id=cid)
        return res

    async def wrapped_forward_messages(entity, *args, **kwargs):
        res = await orig_forward_messages(entity, *args, **kwargs)
        cid = getattr(entity, "id", None) or (int(entity) if isinstance(entity, int) else None)
        register_self_sent(res, default_chat_id=cid)
        return res

    cl.send_message = wrapped_send_message
    cl.send_file = wrapped_send_file
    cl.forward_messages = wrapped_forward_messages


_wrap_client_message_senders(client)

# سوال‌های معلق (پاسخ بعدی کاربر بدون اسم دستیار هم پردازش می‌شه)
PENDING_TTL = 60  # ثانیه؛ پس از آن تاییدیه‌ها خودکار منقضی می‌شوند


class _PendingDict(dict):
    """دیکشنری تاییدیه‌ها که به هر آیتم زمان ثبت (ts) اضافه می‌کند تا TTL یکنواخت اعمال شود."""
    def __setitem__(self, key, value):
        if isinstance(value, dict):
            value = dict(value)
            value.setdefault("ts", time.time())
        super().__setitem__(key, value)


pending = _PendingDict()


def _take_pending(key: str):
    """برداشتن تاییدیه‌ی معتبر؛ در صورت انقضا، پاک و None برمی‌گرداند."""
    p = pending.get(key)
    if p is None:
        return None
    if time.time() - p.get("ts", 0) > PENDING_TTL:
        pending.pop(key, None)
        return None
    return pending.pop(key)


_FA_VARIANTS = (("ي", "ی"), ("ك", "ک"), ("\u200c", ""), ("\u200f", ""), ("\u200e", ""))


def _norm_trigger_name(name: str) -> str:
    s = (name or "").lower()
    for a, b in _FA_VARIANTS:
        s = s.replace(a, b)
    return s


def _name_pattern(name: str) -> "re.Pattern":
    """الگوی تطبیق نام دستیار با مرز توکن (جلوگیری از تطبیق داخل کلمات دیگر) و نرمال‌سازی ی/ک."""
    n = _norm_trigger_name(name)
    n = n.replace("ی", "[یي]").replace("ک", "[کك]")
    return re.compile(r"(?<![آ-یa-zA-Z0-9])" + n + r"(?![آ-یa-zA-Z0-9])", re.IGNORECASE)


_NAME_PATTERNS = [_name_pattern(n) for n in config.ASSISTANT_NAMES]


def has_trigger(text: str) -> bool:
    return any(p.search(text or "") for p in _NAME_PATTERNS)


def starts_with_trigger(text: str) -> bool:
    """بررسی اینکه پیام ورودی دقیقاً با کلمه تریگر (کاپری یا capri) در ابتدای متن آغاز شده باشد."""
    if not text:
        return False
    t = text.strip()
    return bool(re.match(r"^(?:[کك][اآ]\s*پ\s*ر\s*[یي]|capri)(?![آ-یa-zA-Z0-9])", t, re.IGNORECASE))


def strip_trigger(text: str) -> str:
    t = text or ""
    for p in _NAME_PATTERNS:
        t = p.sub(" ", t, count=1)
    return t.strip().strip("،,:.؟? ")


async def get_reply_info(event, client=None) -> Optional[dict]:
    """Extract structured context from replied-to Telegram messages, resolving author identity, text, and media."""
    reply_id = getattr(event, "reply_to_msg_id", None)
    if not reply_id:
        return None

    cli = client or globals().get("client")
    reply_msg = None
    try:
        if cli and getattr(event, "chat_id", None):
            reply_msg = await cli.get_messages(event.chat_id, ids=reply_id)
        elif hasattr(event, "get_reply_message"):
            reply_msg = await event.get_reply_message()
    except Exception:
        reply_msg = None

    if reply_msg is None or not getattr(reply_msg, "id", None):
        return {
            "has_reply": True,
            "is_available": False,
            "reply_id": reply_id,
            "author_id": None,
            "author_name": None,
            "text": "",
            "media_type": None,
            "yt_id": None,
            "social_url": None,
            "msg": None
        }

    author_id = getattr(reply_msg, "sender_id", None)
    author_name = "کاربر"
    try:
        sender = await reply_msg.get_sender()
        if sender:
            author_name = getattr(sender, "first_name", "") or getattr(sender, "title", "") or "کاربر"
    except Exception:
        pass

    text = getattr(reply_msg, "raw_text", None) or getattr(reply_msg, "message", None) or ""
    media_type = None
    if getattr(reply_msg, "photo", None):
        media_type = "photo"
    elif getattr(reply_msg, "video", None) and not getattr(reply_msg, "video_note", None):
        media_type = "video"
    elif getattr(reply_msg, "voice", None) or getattr(reply_msg, "audio", None) or getattr(reply_msg, "video_note", None):
        media_type = "voice"
    elif getattr(reply_msg, "document", None):
        media_type = "document"

    try:
        from services.media import ytsummary, socialdl
        yt_id = ytsummary.extract_youtube_id(text)
        social_url = socialdl.extract_social_url(text)
    except Exception:
        yt_id = None
        social_url = None

    return {
        "has_reply": True,
        "is_available": True,
        "reply_id": reply_id,
        "author_id": author_id,
        "author_name": author_name,
        "text": text,
        "media_type": media_type,
        "yt_id": yt_id,
        "social_url": social_url,
        "msg": reply_msg
    }


async def get_context(event) -> str:
    """Build situational context for the request, including chat environment, sender identity, and reply context."""
    cli = globals().get("client")
    owner_id = globals().get("_owner_id")
    if owner_id is None:
        try:
            from core import memory as _m
            owner_id = _m.get_owner_id()
        except Exception:
            owner_id = None

    chat_id = getattr(event, "chat_id", None)
    is_priv = getattr(event, "is_private", False)
    is_grp = getattr(event, "is_group", False)
    is_chan = getattr(event, "is_channel", False)

    env_lines = []

    # ۱. شناسایی محیط چت (محیط گفتگو، Saved Messages، گروه یا PV)
    if is_priv and owner_id and int(chat_id or 0) == int(owner_id):
        env_lines.append("[محیط مکالمه: پیام‌های ذخیره‌شده (Saved Messages / فضای شخصی مالک)]")
    elif is_grp:
        chat_title = ""
        try:
            chat = getattr(event, "chat", None)
            chat_title = getattr(chat, "title", "")
        except Exception:
            pass
        group_type = "سوپرگروه" if getattr(getattr(event, "chat", None), "megagroup", False) else "گروه"
        env_lines.append(f"[محیط مکالمه: {group_type} «{chat_title or 'گروه'}» (شناسه: {chat_id})]")
    elif is_priv:
        sender_name = ""
        try:
            sender = getattr(event, "sender", None)
            if sender:
                sender_name = getattr(sender, "first_name", "") or getattr(sender, "title", "")
        except Exception:
            pass
        env_lines.append(f"[محیط مکالمه: گفتگوی خصوصی (PV) با کاربر {sender_name or 'مخاطب'} (شناسه: {chat_id})]")
    elif is_chan:
        env_lines.append(f"[محیط مکالمه: کانال تلگرام (شناسه: {chat_id})]")

    # ۲. هویت فرستنده فعلی با تفکیک قطعی شناسه یکتا از نام نمایشی
    cur_sender_id = getattr(event, "sender_id", None)
    cur_sender_name = ""
    try:
        s = getattr(event, "sender", None)
        if s:
            cur_sender_name = getattr(s, "first_name", "")
    except Exception:
        pass
    is_cur_owner = (owner_id and int(cur_sender_id or 0) == int(owner_id)) or (getattr(event, "out", False) and not getattr(event, "fwd_from", None))
    owner_label = "صاحب اکانت" if is_cur_owner else "کاربر عادی"
    if cur_sender_id is not None:
        env_lines.append(f"[فرستنده درخواست: {cur_sender_name or 'کاربر'} (شناسه عددی تلگرام: {cur_sender_id}, نقش: {owner_label})]")

    # ۳. استخراج پیام ارجاع‌شده در صورت ریپلای
    reply_id = getattr(event, "reply_to_msg_id", None)
    if reply_id:
        r_info = await get_reply_info(event, cli)
        if r_info:
            if not r_info.get("is_available"):
                env_lines.append(f"[پیام ارجاع‌شده (Reply): پیام اصلی با شناسه {reply_id} حذف شده یا قابل دسترسی نیست]")
            else:
                r_author = r_info.get("author_name") or "کاربر"
                r_author_id = r_info.get("author_id")
                r_text = (r_info.get("text") or "").strip().replace("\n", " ")[:600]
                media_note = f" (نوع رسانه: {r_info['media_type']})" if r_info.get("media_type") else ""
                id_info = f" با شناسه {r_author_id}" if r_author_id is not None else ""
                env_lines.append(f"[پیام ارجاع‌شده (Reply) از {r_author}{id_info} - شناسه پیام {reply_id}{media_note}]: «{r_text}»")

    # ۴. پیام‌های اخیر گفتگو
    history_lines = []
    seen = set()
    try:
        if cli and getattr(event, "chat_id", None):
            msgs = await cli.get_messages(event.chat_id, limit=8)
            for m in reversed(list(msgs)):
                if getattr(m, "id", None) == getattr(event, "id", None) or getattr(m, "id", None) in self_sent:
                    continue
                if not getattr(m, "message", None):
                    continue
                clean_text = m.message.strip().replace("\n", " ")[:200]
                if clean_text in seen:
                    continue
                seen.add(clean_text)
                if is_grp:
                    s_name = "کاربر"
                    try:
                        s_obj = getattr(m, "sender", None)
                        if s_obj:
                            s_name = getattr(s_obj, "first_name", "") or "کاربر"
                    except Exception:
                        pass
                    m_sid = getattr(m, "sender_id", "نامشخص")
                    history_lines.append(f"{s_name} (ID: {m_sid}): {clean_text}")
                else:
                    who = "کاربر" if getattr(m, "out", False) else "دیگران"
                    history_lines.append(f"{who}: {clean_text}")
    except Exception:
        pass

    res = []
    if env_lines:
        res.extend(env_lines)
    if history_lines:
        res.append("--- پیام‌های اخیر چت ---")
        res.extend(history_lines)

    return "\n".join(res)


def _find_dialog(name_to_dialog: dict, label: str):
    l = (label or "").strip().lower()
    if not l:
        return None
    for n, d in name_to_dialog.items():
        if n.strip().lower() == l:
            return d
    for n, d in name_to_dialog.items():
        nl = n.strip().lower()
        if nl and (nl in l or l in nl):
            return d
    return None


async def _execute_sort(event, mapping: dict) -> None:
    folds = await folders.list_folders(client)
    lines = []
    total = 0
    for fname, dialogs in mapping.items():
        f = folders.find_folder(folds, fname)
        if f is None:
            f, err = await folders.create_folder(client, fname, [d.entity for d in dialogs])
            if err:
                lines.append(f"⚠️ پوشه «{fname}» ساخته نشد: {err}")
                continue
            lines.append(f"📁 {fname}: {len(dialogs)} کانال")
            total += len(dialogs)
            continue
        n = await folders.assign_to_folder(client, f, [d.entity for d in dialogs])
        total += n
        lines.append(f"📁 {fname}: {n} کانال")
        await asyncio.sleep(0.5)
    if lines:
        await event.reply("✅ مرتب کردم:\n" + "\n".join(lines))
    else:
        await event.reply("❌ چیزی مرتب نشد.")


_NEG_WORDS = {
    "نه", "نخیر", "خیر", "لغو", "کنسل", "انصراف", "بیخیال", "منصرف",
    "ولش", "نکن", "نفرست", "no", "cancel", "nope", "not", "حذفش نکن",
}
_POS_WORDS = {
    "آره", "اره", "بله", "آری", "تایید", "موافقم", "موافق", "بفرست",
    "ارسال", "بساز", "برو", "انجام", "yes", "ok", "okay", "yep", "send",
}


def _normalize_fa(text: str) -> str:
    """نرمال‌سازی متن فارسی: یکسان‌سازی ي/ی و ك/ک و تبدیل نیم‌فاصله به فاصله."""
    if not text:
        return ""
    t = text
    for a, b in (("ي", "ی"), ("ك", "ک"), ("\u200c", " "), ("\u200f", " "), ("\u200e", " "), ("‌", " ")):
        t = t.replace(a, b)
    return t.strip().lower()


def _answer_yes(text: str, extra_pos: tuple = ()) -> bool:
    """تایید یا لغو کاربر با تطبیق کل-توکن و اولویت نفی (نفی برنده است)."""
    t = _normalize_fa(text)
    tokens = re.findall(r"[a-z0-9آ-ی]+", t)
    for tok in tokens:
        if tok in _NEG_WORDS or tok.startswith(("نمی", "نخوا", "نکن")):
            return False
    pos = _POS_WORDS | set(extra_pos)
    for tok in tokens:
        if tok in pos:
            return True
    for phrase in extra_pos:
        if " " in phrase and phrase in t:
            return True
    return False


def _is_confirmation_response(text: str, p: dict) -> bool:
    """بررسی تطابق دقیق با مرز کلمه (word boundary) برای تاییدیه تا عباراتی مانند 'اداره' تایید شمرده نشوند."""
    if not text or not isinstance(text, str):
        return False
    t = _normalize_fa(text)
    tokens = set(re.findall(r"[a-z0-9آ-ی]+", t))
    if tokens & _POS_WORDS or tokens & _NEG_WORDS:
        return True
    kind = p.get("kind")
    if kind in ("leave", "media_select"):
        if any(tok.isdigit() for tok in tokens) or "همه" in tokens or "all" in tokens:
            return True
    return False


async def _answer_pending(event, p: dict, text: str) -> None:
    kind = p.get("kind")
    if kind == "confirm_add_memory":
        fact = p.get("fact", "")
        scope_id = p.get("scope_id") or memory.get_event_memory_scope(event, owner_id=_owner_id)
        if _answer_yes(text, ("ذخیره کن", "ثبت کن", "یادت باشه")):
            if fact:
                memory.add_memory(fact, scope_id=scope_id, chat_id=event.chat_id)
                await event.reply(f"✅ واقعیت با موفقیت در حافظه ماندگار این گفتگو ذخیره شد:\n«{fact}»")
            else:
                await event.reply("❌ متنی برای ذخیره داده نشد.")
        else:
            await event.reply("باشه، ذخیره در حافظه لغو شد.")
        return
    if kind == "confirm_important_channel":
        action = p.get("action", "")
        cname = p.get("channel_name", "")
        if _answer_yes(text, ("اضافه کن", "حذف کن", "انجام بده")):
            if action == "add":
                ent_name = None
                if cname.startswith("@") or "t.me/" in cname:
                    try:
                        ent = await client.get_entity(cname)
                        ent_name = getattr(ent, "title", None) or getattr(ent, "username", None) or cname
                    except Exception:
                        pass
                if not ent_name:
                    dialogs = await channels.find_channels(client, cname, limit=50)
                    if dialogs:
                        ent_name = dialogs[0].name
                if not ent_name:
                    ent_name = cname
                briefing.add_important(ent_name)
                await event.reply(f"⭐ کانال «{ent_name}» به لیست کانال‌های مهم اضافه شد و در خلاصه روزانه می‌آید.")
            elif action == "remove":
                names = briefing.load_important()
                pn = channels._norm(cname)
                matches = [n for n in names if pn in channels._norm(n) or channels._norm(n) in pn]
                if matches:
                    briefing.remove_important(matches[0])
                    await event.reply(f"🗑 «{matches[0]}» از لیست کانال‌های مهم برداشته شد.")
                else:
                    await event.reply(f"«{cname}» در لیست کانال‌های مهم نبود.")
        else:
            await event.reply("باشه، عملیات کانال‌های مهم لغو شد.")
        return
    if kind == "confirm_leave_single":
        dialog = p.get("dialog")
        ch_name = p.get("name", "کانال")
        if _answer_yes(text, ("لفت بده", "خارج شو")):
            if dialog:
                left = await channels.leave_dialogs(client, [dialog])
                if left:
                    await event.reply(f"✅ از «{ch_name}» لفت دادم.")
                else:
                    await event.reply(f"❌ نتونستم از «{ch_name}» لفت بدم.")
        else:
            await event.reply("باشه، لفت دادن لغو شد.")
        return
    if kind == "confirm_delete_folder":
        folder_id = p.get("folder_id")
        fname = p.get("name", "پوشه")
        if _answer_yes(text, ("پاک کن", "حذف کن")):
            if folder_id is not None:
                ok = await folders.delete_folder(client, folder_id)
                if ok:
                    await event.reply(f"✅ پوشه «{fname}» حذف شد.")
                else:
                    await event.reply(f"❌ نتونستم پوشه «{fname}» رو حذف کنم.")
        else:
            await event.reply("باشه، حذف پوشه لغو شد.")
        return
    if kind == "confirm_clear_memory":
        scope_id = p.get("scope_id") or memory.get_event_memory_scope(event, owner_id=_owner_id)
        if _answer_yes(text, ("پاک کن", "خالی کن")):
            memory.clear_memory(scope_id=scope_id)
            await event.reply("🗑 تمام حافظه ماندگار کاپری پاک شد.")
        else:
            await event.reply("باشه، پاک‌کردن حافظه لغو شد.")
        return
    if kind == "leave":
        dialogs = p.get("dialogs", [])
        t = _normalize_fa(text)
        if "همه" in t or "all" in t:
            picked = dialogs
        else:
            nums = [int(x) for x in re.findall(r"\d+", text)]
            picked = [dialogs[i - 1] for i in nums if 1 <= i <= len(dialogs)]
            if not picked:
                picked = [d for d in dialogs if channels.match_name(d.name, text)]
        if not picked:
            pending[str(event.chat_id)] = p
            await event.reply("نفهمیدم. بگو «همه» یا شماره‌هاشون (مثلاً 1، 3).")
            return
        left = await channels.leave_dialogs(client, picked)
        if left:
            await event.reply("✅ لفت زدم: " + "، ".join(left))
        else:
            await event.reply("❌ نتونستم لفت بزنم.")
        return
    if kind == "sort":
        if _answer_yes(text, ("انجام بده", "بزن")):
            await _execute_sort(event, p.get("mapping", {}))
        else:
            await event.reply("باشه، لغو کردم.")
        return
    if kind == "draft":
        draft_id = p.get("draft_id")
        target = p.get("target")
        draft_text = p.get("text")
        target_name = p.get("target_name")
        if _answer_yes(text, ("بفرست", "ارسال")):
            from services.social import drafter
            drafter.remove_draft(draft_id)
            ok, res_msg = await drafter.send_draft_message(client, target, draft_text)
            if ok:
                await event.reply(f"✅ پیام با موفقیت به «{target_name}» ارسال شد:\n\n«{draft_text}»")
            else:
                await event.reply(res_msg)
        else:
            from services.social import drafter
            drafter.remove_draft(draft_id)
            await event.reply(f"✖️ ارسال پیام به «{target_name}» لغو شد.")
        return
    if kind == "media_select":
        from services.media import media_flow
        await media_flow.resume_media_fetch(client, event, p, text)
        return
    if kind == "confirm_skill":
        if _answer_yes(text, ("بساز", "ثبت کن")):
            from ai_engine import skills_manager
            res = skills_manager.create_or_update_skill(
                p.get("name", ""), p.get("description", ""),
                p.get("parameters") or {}, p.get("python_code", ""))
            await event.reply(res)
        else:
            await event.reply("باشه، ساخت اسکیل لغو شد.")
        return
    await event.reply("این سوال رو دیگه متوجه نشدم؛ از اول بپرس.")


async def _do_sort(event, status) -> None:
    dialogs = []
    async for d in client.iter_dialogs():
        if d.is_channel or d.is_group:
            dialogs.append(d)
    if len(dialogs) < 2:
        await status.edit("کانال/گروهی برای مرتب کردن پیدا نکردم.")
        return
    name_to_dialog = {d.name: d for d in dialogs}
    await status.edit(f"🧠 دارم {len(dialogs)} کانال رو با هوش مصنوعی دسته‌بندی می‌کنم...")
    cats = await asyncio.to_thread(ai.categorize_channels, list(name_to_dialog.keys()))
    if not cats:
        await status.edit("❌ نتونستم دسته‌بندی کنم (هوش مصنوعی جواب نداد).")
        return
    mapping = {}
    for c in cats:
        d = _find_dialog(name_to_dialog, c.get("channel", ""))
        if d is not None:
            mapping.setdefault(c.get("folder") or "متفرقه", []).append(d)
    if not mapping:
        await status.edit("❌ نتونستم کانال‌ها رو به دسته‌ها وصل کنم.")
        return
    plan = "\n".join(f"📁 {f}: {len(ds)} کانال" for f, ds in mapping.items())
    pending[str(event.chat_id)] = {"kind": "sort", "mapping": mapping}
    await status.edit("این‌طوری دسته‌بندی کردم:\n" + plan + "\n\nانجامش بدم؟ بگو «آره» یا «نه».")


async def send_images(event, query: str, limit: int = 3):
    if not config.SERPER_API_KEY:
        return "جستجوی عکس هنوز تنظیم نشده. اول کلید Serper رو بذار."
    eq = await asyncio.to_thread(ai._search_query, query) or query
    items = await asyncio.to_thread(gsearch.image_search, eq, limit)
    if items is None:
        return f"🖼 نتونستم دنبال «{eq}» بگردم (خطای API)."
    if not items:
        return f"🖼 عکسی برای «{eq}» پیدا نکردم."
    os.makedirs(config.DOWNLOAD_DIR, exist_ok=True)
    sent = 0
    for i, it in enumerate(items[:limit]):
        path = os.path.join(config.DOWNLOAD_DIR, f"img_{int(time.time())}_{i}.jpg")
        ok = await asyncio.to_thread(gsearch.download, it["url"], path)
        if not ok and it.get("thumb"):
            ok = await asyncio.to_thread(gsearch.download, it["thumb"], path)
        if not ok:
            continue
        try:
            cap = f"🖼 {it['title']}" if it.get("title") else None
            m = await client.send_file(event.chat_id, path, caption=cap)
            self_sent.add(m.id)
            sent += 1
            await asyncio.sleep(0.8)
        except Exception:
            pass
        finally:
            _safe_unlink(path)
    if sent:
        return f"✅ {sent} عکس فرستادم 👆"
    return "🖼 نتونستم عکس رو دانلود کنم."


def _learn(question: str, answer: str, scope_id: Optional[str] = None, chat_id: Optional[Any] = None) -> None:
    try:
        fact = ai.extract_fact(question, answer)
        if fact:
            memory.add_memory(fact, scope_id=scope_id, chat_id=chat_id)
    except Exception:
        pass


_last_learn_time = 0.0
_learn_lock = asyncio.Lock()
_PERSONAL_MARKERS = ("من ", " من", "دوست دارم", "علاقه", "ترجیح", "کارم", "شغلم", "اسمم", "سنم", "یادم", "همیشه", "بلدم", "بدم میاد", "عاشق")


async def _trigger_learn(question: str, answer: str, scope_id: Optional[str] = None, chat_id: Optional[Any] = None) -> None:
    global _last_learn_time
    q = (question or "").strip()
    if len(q) < 15:
        return
    if not any(m in q for m in _PERSONAL_MARKERS):
        return
    now = time.time()
    if now - _last_learn_time < 30.0:
        return
    if _learn_lock.locked():
        return
    async with _learn_lock:
        _last_learn_time = time.time()
        try:
            await asyncio.to_thread(_learn, question, answer, scope_id, chat_id)
        except Exception as e:
            log.debug("Fact learning exception: %s", e)
        try:
            # تأمل شناختی خودکار منحصراً در گفتگوهای خصوصی یا سیو مسیج
            if not scope_id or ":group:" not in str(scope_id):
                await cognitive_memory.reflect_interaction(question, answer)
        except Exception as e:
            log.debug("Cognitive reflection exception: %s", e)


# کلمات کلیدی سطح ماژول برای تشخیص ویس/عمل/پژوهش (جلوگیری از تکرار و misfire)
VOICE_WORDS = ("ویس", "وویس", "صوتی", "حرف بزن")
ACTION_WORDS = ("بگیر", "بده", "بفرست", "بگو", "کن", "بساز", "ارسال", "بخون")
RESEARCH_WORDS = ("چطوری", "چگونه", "چیه", "چیست", "چرا", "بهترین", "روش", "راهنمایی",
                  "آموزش", "بررسی", "مقایسه", "تحلیل", "تفاوت", "راه حل", "توضیح")


def _chunk_text(text: str, max_size: int = 4000) -> list:
    if len(text) <= max_size:
        return [text]
    chunks = []
    lines = text.splitlines(keepends=True)
    current = ""
    for line in lines:
        if len(current) + len(line) <= max_size:
            current += line
        else:
            if current:
                chunks.append(current)
            if len(line) > max_size:
                for i in range(0, len(line), max_size):
                    chunks.append(line[i:i + max_size])
                current = ""
            else:
                current = line
    if current:
        chunks.append(current)
    return chunks


async def _safe_edit_or_send(event, status, text: str, link_preview: bool = True) -> None:
    """ارسال ایمن متن با پشتیبانی از چندبخشی خودکار جهت جلوگیری از خطای ۴۰۹۶ کاراکتر تلگرام و کنترل پیش‌نمایش لینک."""
    chunks = _chunk_text(text, 4000)
    if not chunks:
        return
    if status is not None:
        try:
            await status.edit(chunks[0], link_preview=link_preview)
            register_self_sent(status.id, default_chat_id=event.chat_id)
        except Exception:
            try:
                m = await event.reply(chunks[0], link_preview=link_preview)
                register_self_sent(m, default_chat_id=event.chat_id)
            except Exception:
                pass
    else:
        m = await event.reply(chunks[0], link_preview=link_preview)
        register_self_sent(m, default_chat_id=event.chat_id)
    for chunk in chunks[1:]:
        m = await client.send_message(event.chat_id, chunk, link_preview=link_preview)
        register_self_sent(m, default_chat_id=event.chat_id)
        await asyncio.sleep(0.3)


MD_DIR = os.path.join(config.DOWNLOAD_DIR, "md")


def _is_long_or_code(text: str) -> bool:
    """تشخیص پاسخ‌هایی که بهتر است به‌صورت فایل Markdown ارسال شوند (طولانی/کد/جدول)."""
    if not text:
        return False
    if len(text) > 4000:
        return True
    if "```" in text:
        return True
    lines = text.splitlines()
    # جدول Markdown: سطر جداکننده‌ی ستون‌ها (--- بین |) یا دو سطر پیاپی حاوی |
    if any("---" in ln and "|" in ln for ln in lines):
        return True
    for i in range(len(lines) - 1):
        if "|" in lines[i] and "|" in lines[i + 1]:
            return True
    return False


def _save_md(text: str) -> str:
    """ذخیره‌ی پاسخ در پوشه‌ی جداگانه‌ی Markdown داخل دانلودها (نگهداری دائمی؛ از purge معاف است)."""
    os.makedirs(MD_DIR, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    path = os.path.join(MD_DIR, f"capri_{ts}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


async def _send_as_md(event, status, text: str) -> None:
    """ارسال پاسخ به‌صورت فایل Markdown و نگهداری آن در پوشه‌ی اختصاصی."""
    try:
        path = _save_md(text)
        msg = await client.send_file(event.chat_id, path, caption="📄 پاسخ کامل در قالب Markdown")
        self_sent.add(msg.id)
        if status is not None:
            try:
                await status.delete()
            except Exception:
                pass
    except Exception as e:
        log.warning("Markdown file send failed: %s", type(e).__name__)
        await _safe_edit_or_send(event, status, text)


def _safe_unlink(path: str) -> None:
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


def _purge_downloads(max_age: int = 24 * 3600, max_bytes: int = 500 * 1024 * 1024) -> None:
    """حذف فایل‌های موقت قدیمی در پوشه دانلود و اعمال سقف حجم."""
    d = config.DOWNLOAD_DIR
    try:
        files = [os.path.join(d, f) for f in os.listdir(d)]
    except Exception:
        return
    now = time.time()
    total = 0
    for path in files:
        try:
            st = os.stat(path)
            total += st.st_size
            if now - st.st_mtime > max_age:
                _safe_unlink(path)
        except Exception:
            continue
    if total > max_bytes:
        with_age = []
        for path in files:
            try:
                with_age.append((os.path.getmtime(path), path))
            except Exception:
                continue
        with_age.sort()
        for _, path in with_age:
            if total <= max_bytes:
                break
            try:
                sz = os.path.getsize(path)
                _safe_unlink(path)
                total -= sz
            except Exception:
                continue


async def _purge_downloads_loop(interval: int = 6 * 3600) -> None:
    while True:
        try:
            await asyncio.to_thread(_purge_downloads)
        except Exception as e:
            log.debug("Downloads purge error: %s", e)
        await asyncio.sleep(interval)


def _clean_voice_text(text: str) -> str:
    """حذف جملات امتناع ناخواسته مدل (مانند 'من متنی‌ام' یا 'قابلیت ویس ندارم')."""
    lines = text.splitlines()
    clean_lines = []
    refusal_patterns = (
        "قابلیت ویس", "ویس فرستادن", "دستیار متنی", "متنی‌ام", "صدا باهات حرف",
        "نمی‌تونم ویس", "نمی‌توانم ویس", "اگه می‌تونستم ویس", "اگر می‌تونستم ویس",
        "ویس بفرستم", "با صدا حرف بزنم", "صدا ندارم"
    )
    for line in lines:
        if any(rp in line for rp in refusal_patterns):
            continue
        clean_lines.append(line)
    res = "\n".join(clean_lines).strip()
    return res or text.strip()


async def _stage(status, text: str) -> None:
    if status is None:
        return
    try:
        await status.edit(text)
    except Exception:
        pass


def _is_group_summary_request(q: str) -> bool:
    """تشخیص درخواست صورتجلسه/خلاصه پیام‌های گروه یا چت (نه ویدیو/مقاله/ویس)."""
    q = q or ""
    if "خلاصه" not in q and "صورتجلسه" not in q and "صورت جلسه" not in q:
        return False
    if any(x in q for x in ("ویدیو", "ویدئو", "فیلم", "مقاله", "لینک", "ویس", "یوتیوب", "آهنگ", "اهنگ", "موزیک", "موسیقی")):
        return False
    return any(x in q for x in ("پیام", "پیاما", "گروه", "چت", "حرفا", "حرفای", "بحث", "صورتجلسه", "صورت جلسه"))


def _is_folder_sort_request(q: str) -> bool:
    """تشخیص درخواست مرتب‌سازی/دسته‌بندی خودکار پوشه‌ها."""
    q = q or ""
    if "پوشه" not in q:
        return False
    return any(x in q for x in ("مرتب", "دسته‌بندی", "دسته بندی", "ساماندهی", "منظم", "چیدمان"))


def _is_channel_leave_request(q: str) -> bool:
    """تشخیص درخواست خروج یا لفت دادن از کانال‌ها یا گروه‌ها."""
    q = q or ""
    has_leave = any(x in q for x in ("لفت بده", "لفت بزن", "لفت بدم", "لفت کن", "خارج شو", "بیا بیرون", "ترک کن", "لفت"))
    has_channel = any(x in q for x in ("کانال", "کانالها", "کانال های", "کانال‌های", "چنل", "چنل ها", "چنل‌های", "گروه", "گروه ها", "گروه‌های"))
    return has_leave and has_channel


def _extract_channel_leave_keyword(q: str) -> str:
    """استخراج کلمه کلیدی موضوع یا نام کانال از درخواست لفت دادن."""
    q = _normalize_fa(q)
    strip_words = (
        "کاپری", "لطفا", "لطفاً", "بی زحمت", "بی‌زحمت", "برو",
        "از", "توی", "داخل", "کانال های", "کانال‌های", "کانالهای", "کانال",
        "چنل های", "چنل‌های", "چنل", "گروه های", "گروه‌های", "گروه",
        "لفت بده", "لفت بزن", "لفت بدم", "لفت کن", "لفت",
        "خارج شو", "بیا بیرون", "ترک کن", "همشون", "همه رو", "همه", "رو"
    )
    for w in strip_words:
        q = re.sub(r"(?i)\b" + re.escape(w) + r"\b", " ", q)
    return " ".join(q.split()).strip("،,:.؟?! ")


_PERSIAN_REWRITE_PHRASES = (
    "بازنویسی", "باز نویسی", "ویرایش", "ویراست", "اصلاح", "غلط گیر", "غلط‌گیری",
    "درستش کن", "تمیزش کن", "تمیز کن", "پاکیزه کن", "ادیتش کن", "ریرایت", "rewrite",
)


def _is_persian_rewrite_request(q: str) -> bool:
    """تشخیص درخواست بازنویسی/ویراستاری تمیز فارسی (اسکیل نگارش فارسی)."""
    q = q or ""
    return any(w in q for w in _PERSIAN_REWRITE_PHRASES)


def _extract_rewrite_text(q: str) -> str:
    """استخراج متن هدف از درخواست بازنویسی (اگر متن نیامد، اسکیل از ریپلای می‌خواند)."""
    for w in _PERSIAN_REWRITE_PHRASES:
        if w in q:
            q = q.replace(w, " ", 1)
            break
    q = re.sub(r"^(کن|بده|بزن|لطفا|لطفاً|رو|این متن|متن|این)\s+", " ", q)
    return " ".join(q.split()).strip("،,:.؟?! «»\"' ")


_IMAGE_QUERY_WORDS = ("سعکس", "تصویر", "پوستر")
_IMAGE_ACTION_WORDS = (
    "نشونم بده", "نشون بده", "نشان بده", "پیداش کن", "پیدا کن", "بفرستش",
    "بفرست", "بده", "بذار", "بزار", "بگرد", "میخوام", "میخام", "لطفا", "لطفاً",
)


def _is_image_request(q: str) -> bool:
    """تشخیص درخواست مستقیم عکس (نه تحلیل عکسِ موجود/ریپلای‌شده)."""
    q = q or ""
    if "این عکس" in q or "این تصویر" in q or "بررسی کن" in q:
        return False
    if not any(w in q for w in _IMAGE_QUERY_WORDS):
        return False
    return any(w in q for w in _IMAGE_ACTION_WORDS)


def _extract_image_query(q: str) -> str:
    for w in _IMAGE_QUERY_WORDS + _IMAGE_ACTION_WORDS:
        q = q.replace(w, " ")
    return " ".join(q.split()).strip("،,:.؟?! ")


_WEB_FRESH_WORDS = (
    "تازه ترین", "تازه‌ترین", "آخرین", "جدیدترین", "امروز", "فردا", "امشب", "الان",
    "قیمت", "اخبار", "خبر", "آپدیت", "اپدیت", "پیش‌بینی", "پیش بینی",
    "نرخ", "وضعیت", "آب و هوا", "هواشناسی", "جدول",
)
_WEB_LOCAL_GUARD = (
    "یادت باشه", "یادآوری", "فراموش کن", "قانون", "روست", "میم", "وایب", "دانلود",
    "بفرست", "پیدا کن", "خلاصه", "عکس", "تصویر", "پوشه", "مرتب", "ترجمه", "بنویس",
    "کد", "اسکریپت", "برنامه", "یادم باشه", "یادم بنداز", "بهم یادآوری",
    "پیام", "پیش‌نویس", "پیش نویس",
)


def _is_web_question(q: str) -> bool:
    """سوالی که به اطلاعات روز/به‌روز نیاز داره (برای جستجوی مستقیم و سریع، نه ایجنت کند)."""
    q = q or ""
    if any(w in q for w in _WEB_LOCAL_GUARD):
        return False
    return any(w in q for w in _WEB_FRESH_WORDS)


# کلمه‌هایی که نشان می‌دهند پیام یک «دستور ابزار» است (نه سوال ساده) و باید به ایجنت برود
_TOOL_TRIGGER_WORDS = (
    "لفت", "عضو شو", "عضو شدم", "جوین", "پوشه",
    "آهنگ", "اهنگ", "موزیک", "موسیقی", "بگیر بیار", "دانلود",
    "تصویر", "پوستر", "صوتی",
    "یادت باشه", "فراموش کن", "قانون", "حافظه",
    "روست", "تیکه", "ضایع", "میم", "وایب", "نیت", "جوابشو بده", "جوابشو نده",
    "قیمت", "اخبار", "آپدیت", "اپدیت", "نرخ", "وضعیت",
    "بفرست", "پیدا کن", "بگرد", "سرچ", "جستجو", "برام بگرد", "برام پیدا",
    "ترجمه", "بریفینگ", "صورتجلسه", "مرتب",
    "کد بزن", "برنامه بنویس", "اسکریپت", "دیتابیس", "بشین کد بزن",
    "اسکیل", "بهش بگو", "براش بگو", "بهش پیام", "پیش‌نویس", "پیش نویس",
    "یادآور", "یادآوری", "ریمایندر", "آلارم", "یادم بنداز", "پاک کن", "حذف کن", "لغو کن", "یادآورهام", "یادآورام",
)

# کلمات کلیدی تک‌سیلابی که برای جلوگیری از همپوشانی زیررشته‌ای (مثل برنامه‌نویسی یا برعکس)، باید به عنوان کلمه مستقل تطبیق داده شوند
_DISCRETE_TRIGGER_WORDS = ("ویس", "عکس", "فایل", "سند", "خبر")


def _is_summary_request(text: str) -> bool:
    """تشخیص قصد خلاصه‌سازی، چکیده یا توضیح موضوع ویدیو/محتوا."""
    t = (text or "").lower()
    return any(w in t for w in (
        "خلاصه", "خلاصش", "چکیده", "چی میگه", "چی میگن", "موضوعش چیه",
        "توضیح بده", "درباره چیه", "نکات مهم", "خلاصه کن", "summarize", "summary"
    ))


def _is_video_info_request(text: str) -> bool:
    """تشخیص قصد دریافت متادیتا، مدت زمان، نام کانال یا مشخصات ویدیو بدون دانلود."""
    t = (text or "").lower()
    return any(w in t for w in (
        "مشخصات", "اطلاعات", "مدت زمان", "چند دقیقه", "کی منتشر", "کی ساخته",
        "کانالش چیه", "سازندش کیه", "تعداد بازدید", "چند تا بازدید", "چند بازدید",
        "آمار ویدیو", "metadata", "info", "details"
    ))


def _is_download_request(text: str) -> bool:
    """تشخیص قصد صریح دانلود فایل مدیا."""
    t = (text or "").lower()
    return any(w in t for w in (
        "دانلود", "دان کن", "بگیر بیار", "بفرستش", "فایلشو بده", "فایلشو بفرست",
        "فایل ویدیو", "کیفیت", "download", "ذخیره کن", "سیو کن"
    ))


def _is_simple_question(q: str) -> bool:
    """سوال ساده/گفتگویی (بدون ابزار) که می‌شود مستقیم و سریع جواب داد."""
    q = q or ""
    # وجود هرگونه لینک رسانه‌ای نیاز به هدایت به ابزار مربوطه دارد
    if re.search(r"(?:youtube\.com|youtu\.be|instagram\.com|tiktok\.com|twitter\.com|x\.com|pin\.it|pinterest\.com|soundcloud\.com)", q, re.I):
        return False
    if any(w in q for w in _TOOL_TRIGGER_WORDS):
        return False
    for dw in _DISCRETE_TRIGGER_WORDS:
        if re.search(r"(?:^|[^\w\u0600-\u06FF])" + re.escape(dw) + r"(?:[^\w\u0600-\u06FF]|$)", q):
            return False
    return True


def _is_ghost_deactivate(q: str) -> bool:
    q = q or ""
    return any(w in q for w in (
        "برگرد به حالت عادی", "برگرد حالت عادی", "حالت عادی", "حالت طبیعی",
        "همزاد رو خاموش", "همزاد رو ببند", "همزادو خاموش", "مثل من شو رو خاموش",
    ))


def _is_ghost_activate(q: str) -> bool:
    q = q or ""
    if any(w in q for w in ("خاموش", "برگرد", "ببند", "قطع", "غیرفعال")):
        return False
    return any(w in q for w in (
        "مثل من شو", "مثل من باش", "مثل خودم شو", "مثل خودم باش", "شبیه من شو", "همزاد شو",
    ))


async def _media_target(event):
    """پیام مدیا (خود پیام یا ریپلای‌شده) رو برمی‌گردونه؛ None اگه مدیا نبود."""
    if getattr(event, "media", None):
        return event
    if getattr(event, "reply_to_msg_id", None):
        try:
            return await client.get_messages(event.chat_id, ids=event.reply_to_msg_id)
        except Exception:
            return None
    return None


async def _handle_voice(event, status, msg, question) -> None:
    path = os.path.join(config.DOWNLOAD_DIR, f"voice_{int(time.time() * 1000)}.ogg")
    try:
        os.makedirs(config.DOWNLOAD_DIR, exist_ok=True)
        await _stage(status, "🎧 دارم ویس رو با دقت گوش می‌دم...")
        await client.download_media(msg, file=path)
        text = await asyncio.to_thread(voice.transcribe, path)
        if not text or not text.strip():
            await _stage(status, "❌ نتونستم صدای ویس رو واضح متوجه بشم (شاید خیلی کوتاه یا نامفهوم بود) 🙈")
            return

        q_clean = (question or "").strip()
        is_reply_to_other = bool(getattr(event, "reply_to_msg_id", None) and not getattr(msg, "out", False))

        SUMMARY_WORDS = ("خلاصه", "خلاصش", "خلاصه‌ش", "چکیده", "نکات", "موضوع", "چی میگه", "چی گفت", "چی گفته", "چی بود")
        TRANSCRIPT_WORDS = ("فقط متن", "متن کامل", "پیاده کن", "تایپ کن", "تبدیل به متن")

        wants_transcript_only = any(w in q_clean for w in TRANSCRIPT_WORDS) or (("متن" in q_clean or "بنویس" in q_clean) and not any(w in q_clean for w in SUMMARY_WORDS))
        wants_summary = any(w in q_clean for w in SUMMARY_WORDS) or (is_reply_to_other and not q_clean)

        context = await get_context(event)
        # حافظه‌ی صاحب اکانت هرگز بر اساس متن ویسِ دیگران بازیابی نمی‌شود (جلوگیری از استخراج حقایق خصوصی)
        mem = ""

        # ۱. فقط استخراج و نمایش متن دقیق ویس
        if wants_transcript_only:
            out_msg = f"🎙 **متن پیاده‌شده از پیام صوتی:**\n\n«{text.strip()}»"
            await status.edit(out_msg)
            return

        # ۲. خلاصه‌سازی ساختاریافته ویس (Option 2: Voice-to-Summary)
        if wants_summary or is_reply_to_other:
            await _stage(status, "📝 دارم نکات کلیدی ویس رو خلاصه می‌کنم...")
            summary_prompt = (
                f"متن زیر پیاده‌شده از یک پیام صوتی (Voice Message) در تلگرام است:\n"
                f"«{text.strip()}»\n\n"
                "لطفاً یک خلاصه‌ی تمیز، خوانا، شیک و ساختاریافته به زبان فارسی ارائه بده.\n"
                "قالب خروجی دقیقاً این باشد:\n"
                "📌 **موضوع اصلی:** (یک یا دو جمله خلاصه و شفاف)\n"
                "🔍 **نکات کلیدی و مباحث مطرح‌شده:**\n"
                "- (نکته ۱)\n"
                "- (نکته ۲)\n"
                "- ...\n"
                "💡 **نتیجه یا اقدام لازم:** (در صورت وجود، وگرنه ننویس)\n\n"
                "لحنت صمیمی، روان و خودمونی باشد. در انتها متن پیاده‌شده را تکرار نکن (سیستم جداگانه آن را نمایش می‌دهد)."
            )
            summary = await asyncio.to_thread(ai.ask, summary_prompt, context, mem)
            final_reply = (
                f"🎙 **خلاصه پیام صوتی:**\n\n"
                f"{summary.strip()}\n\n"
                f"━━━━━━━━━━━━━━━\n"
                f"📝 **متن کامل پیاده‌شده:**\n"
                f"«{text.strip()}»"
            )
            await status.edit(final_reply)
            return

        # ۳. سوال خاص درباره ویس (مثلاً: کی میاد؟ ساعت چنده؟ آدرس چی بود؟)
        if q_clean and not getattr(msg, "out", False):
            await _stage(status, "🤔 دارم به سوالت درباره ویس جواب می‌دم...")
            qa_prompt = (
                f"متن پیاده‌شده از ویس:\n«{text.strip()}»\n\n"
                f"سوال کاربر درباره این ویس: {q_clean}\n\n"
                "لطفاً با توجه به متن ویس، پاسخ کوتاه، دقیق و صمیمی به زبان فارسی بده."
            )
            answer = await asyncio.to_thread(ai.ask, qa_prompt, context, mem)
            await status.edit(answer)
            return

        # ۴. کاربر خودش ویس فرستاده و به عنوان پرامپت با کاپری صحبت کرده است (مکالمه صوتی دوطرفه)
        if any(w in question.lower() for w in RESEARCH_WORDS):
            await _stage(status, "🔍 در حال کاوش سه‌زبانه (انگلیسی، چینی، فارسی) و تحلیل تخصصی...")
        else:
            await _stage(status, "🤔 دارم فکر می‌کنم...")
        scope_id = memory.get_event_memory_scope(event, owner_id=_owner_id)
        mem = memory.relevant_facts(text, scope_id=scope_id)
        answer = await asyncio.to_thread(ai.ask, text, context, mem, chat_id=scope_id)
        await _stage(status, "🔊 دارم جواب رو صوتی می‌کنم...")
        mp3 = os.path.join(config.DOWNLOAD_DIR, f"reply_{int(time.time() * 1000)}.mp3")
        ok = await voice.speak(answer, mp3, client=client)
        sent = False
        if ok:
            ogg = mp3 + ".ogg"
            if await asyncio.to_thread(voice.to_ogg, mp3, ogg):
                try:
                    await client.send_file(event.chat_id, ogg, voice_note=True)
                    sent = True
                except Exception:
                    sent = False
                _safe_unlink(ogg)
            if not sent:
                try:
                    await client.send_file(event.chat_id, mp3)
                    sent = True
                except Exception:
                    sent = False
        if not sent:
            await status.edit(answer)
        else:
            try:
                await status.delete()
            except Exception:
                pass
        is_owner_voice = getattr(msg, "out", False) and not getattr(msg, "fwd_from", None)
        if is_owner_voice and not agent.get_last_run_tainted():
            memory.remember_exchange(scope_id, text, answer)
            asyncio.get_running_loop().create_task(asyncio.to_thread(_learn, text, answer, scope_id, event.chat_id))
        _safe_unlink(mp3)
    except Exception as e:
        log.error("Error in _handle_voice: %s", type(e).__name__, exc_info=True)
        await _stage(status, "❌ خطایی در پردازش ویس رخ داد؛ لطفاً مجدداً تلاش کنید.")
    finally:
        _safe_unlink(path)


async def _handle_vision(event, status, msg, question) -> None:
    path = os.path.join(config.DOWNLOAD_DIR, f"img_{int(time.time())}.jpg")
    try:
        os.makedirs(config.DOWNLOAD_DIR, exist_ok=True)
        await _stage(status, "👁 دارم عکس رو می‌بینم...")
        await client.download_media(msg, file=path)
        q = question
        for w in ("این عکس", "این تصویر", "عکس", "تصویر", "بررسی کن", "ببین", "چیه", "چی هست", "چیست"):
            q = q.replace(w, " ")
        q = " ".join(q.split()).strip("،,:.؟? ")
        if any(w in question.lower() for w in RESEARCH_WORDS):
            await _stage(status, "🔍 در حال کاوش سه‌زبانه (انگلیسی، چینی، فارسی) و تحلیل تخصصی...")
        else:
            await _stage(status, "🤔 دارم فکر می‌کنم...")
        desc = await asyncio.to_thread(ai.describe_image, path, q)
        if not desc:
            await _stage(status, "❌ نتونستم عکس رو تحلیل کنم.")
            return
        await _stage(status, "📝 دارم جواب می‌دم...")
        await status.edit(desc)
    except Exception as e:
        log.error("Error in _handle_vision: %s", logger.redact_secrets(str(e)))
        await _stage(status, "❌ خطایی در پردازش تصویر رخ داد؛ لطفاً مجدداً تلاش کنید.")
    finally:
        _safe_unlink(path)


def _video_ext(msg) -> str:
    doc = msg.video or msg.document
    if doc:
        for a in doc.attributes:
            if isinstance(a, types.DocumentAttributeFilename) and a.file_name:
                ext = os.path.splitext(a.file_name)[1].lower()
                if ext:
                    return ext
    return ".mp4"


async def _handle_video(event, status, msg, question) -> None:
    path = os.path.join(config.DOWNLOAD_DIR, f"vid_{int(time.time() * 1000)}{_video_ext(msg)}")
    try:
        os.makedirs(config.DOWNLOAD_DIR, exist_ok=True)
        await _stage(status, "📥 دارم ویدیو رو دانلود می‌کنم...")
        await client.download_media(msg, file=path)
        q = (question or "").strip()
        for w in ("این ویدیو", "این ویدئو", "ویدیو", "ویدئو", "فیلم", "تحلیل کن", "کالبدشکافی", "بررسی کن", "ببین", "چیه", "چی میگه"):
            q = q.replace(w, " ")
        q = " ".join(q.split()).strip("،,:.؟? ")
        await _stage(status, "🎬 تحلیل کامل با Gemini (تایم‌استمپ + متن روی تصویر)...")
        raw = await asyncio.to_thread(ai.analyze_video, path, q)
        if not raw:
            await _stage(status, "❌ نتونستم ویدیو رو تحلیل کنم (شاید مدل/سهمیه/فرمت).")
            return
        await _stage(status, "✍️ دارم تحلیل رو به مدل فعال می‌سپرم تا جامع‌ترش کنه...")
        final = await asyncio.to_thread(ai.refine_video_analysis, raw)
        await status.edit(final or raw)
    except Exception as e:
        log.error("Error in _handle_video: %s", logger.redact_secrets(str(e)))
        await _stage(status, "❌ خطایی در پردازش ویدیو رخ داد؛ لطفاً مجدداً تلاش کنید.")
    finally:
        _safe_unlink(path)


async def _handle_document(event, status, msg, question) -> None:
    ext = study.is_study_document(msg)
    if not ext:
        return
    is_code = ext in study.CODE_EXTS
    name = "فایل"
    doc = msg.document
    for a in (getattr(doc, "attributes", None) or []):
        if isinstance(a, types.DocumentAttributeFilename) and a.file_name:
            name = a.file_name
            break
    path = os.path.join(config.DOWNLOAD_DIR, f"doc_{int(time.time() * 1000)}{ext}")
    try:
        os.makedirs(config.DOWNLOAD_DIR, exist_ok=True)
        await _stage(status, "📥 دارم فایل رو دانلود می‌کنم...")
        await client.download_media(msg, file=path)
        q = study.clean_question(question)
        if ext == ".pdf":
            await _stage(status, "📖 دارم سند رو می‌خونم (حتی اگه اسکن‌شده باشه)...")
        elif is_code:
            await _stage(status, "👨‍💻 دارم کد رو تحلیل می‌کنم...")
        else:
            await _stage(status, "🔎 دارم متن سند رو استخراج می‌کنم...")
        ans = await asyncio.to_thread(study.analyze, path, ext, name, q, is_code)
        if not ans:
            await _stage(status, "❌ نتونستم فایل رو تحلیل کنم؛ چند دقیقه دیگه دوباره امتحان کن.")
            return
        if len(ans) <= 3800:
            await _safe_edit_or_send(event, status, ans)
        else:
            await _send_as_md(event, status, ans)
    except Exception as e:
        log.error("Error in _handle_document: %s", logger.redact_secrets(str(e)))
        await _stage(status, "❌ خطایی در پردازش فایل رخ داد؛ لطفاً مجدداً تلاش کنید.")
    finally:
        _safe_unlink(path)


async def _handle_media(event, msg, question) -> bool:
    media = getattr(msg, "media", None)
    if media is None or isinstance(media, types.MessageMediaWebPage):
        return False
    is_voice = bool(msg.voice or msg.audio or msg.video_note)
    is_photo = bool(msg.photo)
    is_video = bool(msg.video) and not msg.video_note
    is_doc = bool(study.is_study_document(msg))
    if not (is_voice or is_photo or is_video or is_doc):
        return False
    status = None
    try:
        status = await event.reply("🧠 در حال جمع‌آوری اطلاعات...")
        self_sent.add(status.id)
    except Exception:
        pass
    if is_video:
        await _handle_video(event, status, msg, question)
    elif is_voice:
        await _handle_voice(event, status, msg, question)
    elif is_doc:
        await _handle_document(event, status, msg, question)
    else:
        await _handle_vision(event, status, msg, question)
    return True


MODEL_PAGE_SIZE = 6


def _model_code(service: str) -> str:
    return {
        "xkiro": "k",
        "bai": "b",
        "anyapi": "a",
        "openrouter": "o",
        "groq": "g",
        "hooshia": "h",
        "inception": "i",
    }.get(service, "o")


def _code_service(code: str) -> str:
    return {
        "k": "xkiro",
        "b": "bai",
        "a": "anyapi",
        "o": "openrouter",
        "g": "groq",
        "h": "hooshia",
        "i": "inception",
    }.get(code, "openrouter")


def _service_models(service: str):
    return {
        "xkiro": models.XKIRO,
        "bai": models.BAI,
        "anyapi": models.ANYAPI,
        "openrouter": models.OPENROUTER,
        "groq": models.GROQ,
        "hooshia": models.HOOSHIA,
        "inception": models.INCEPTION,
    }.get(service, models.OPENROUTER)


def _render_provider_menu():
    text = (
        "🤖 **کاتالوگ جامع مدل‌های هوش مصنوعی کاپری**\n\n"
        "برای مشاهده و انتخاب مدل‌ها، ارائه‌دهنده مورد نظر خود را انتخاب کنید:\n"
        "• **⚡ XKIRO (k):** ۹۷ مدل جهانی (پرچمداران و مدل‌های رایگان)\n"
        "• **🤖 B.AI (b):** ۶۲ مدل رسمی قدرتمند\n"
        "• **🌐 AnyAPI (a):** مدل‌های پرسرعت جمینای و نموترون\n"
        "• **🆓 OpenRouter (o):** ۱۵ مدل متن‌باز کاملاً رایگان\n"
        "• **⚡ Groq (g):** ۳ مدل فوق‌سریع پردازش ابزار و استدلال\n"
        "• **🇮🇷 هوشیا (h):** ۳ مدل بومی فارسی GLM بدون فیلتر\n"
        "• **🚀 Inception (i):** مدل پرسرعت Mercury 3\n\n"
        "💡 **سوییچ فوری با شناسه یکتا:** کافیست UID مدل را بفرستید (مثلاً `k1`، `a1`، `o3`، `b1` یا `h1`).\n"
        "برای دریافت فایل کامل کاتالوگ، روی دکمه فایل متنی بزنید."
    )
    buttons = [
        [Button.inline("⚡ XKIRO (k)", b"ls:k"), Button.inline("🤖 B.AI (b)", b"ls:b")],
        [Button.inline("🌐 AnyAPI (a)", b"ls:a"), Button.inline("🆓 OpenRouter (o)", b"ls:o")],
        [Button.inline("⚡ Groq (g)", b"ls:g"), Button.inline("🇮🇷 هوشیا (h)", b"ls:h"), Button.inline("🚀 Inception (i)", b"ls:i")],
        [Button.inline("📄 دانلود فایل کامل MODELS.md", b"ls:doc")],
        [Button.inline("✖️ بستن منو", b"x")],
    ]
    return text, buttons


def _render_model_list(service: str, page: int):
    lst = _service_models(service)
    total = max(1, (len(lst) + MODEL_PAGE_SIZE - 1) // MODEL_PAGE_SIZE)
    page = min(max(1, page), total)
    start = (page - 1) * MODEL_PAGE_SIZE
    chunk = lst[start:start + MODEL_PAGE_SIZE]
    code = _model_code(service)
    lines = [f"📦 **مدل‌های {models.service_name(service)}** (صفحه {page} از {total})\n"]
    for i, e in enumerate(chunk):
        uid_tag = f"[`{e['uid']}`] " if e.get("uid") else ""
        lines.append(f"{start + i + 1}. {uid_tag}**{e['name']}** — {models.CATEGORIES.get(e.get('cat', ''), 'عمومی')}")
        lines.append(f"   شناسه: `{e['id']}`")
        if e.get("desc"):
            lines.append(f"   _{e['desc']}_")
        lines.append("")
    lines.append("👇 برای فعال‌سازی فوری، روی دکمه مدل بزنید یا شناسه‌اش را بنویسید:")
    buttons = []
    for i, e in enumerate(chunk):
        uid_str = f"[{e['uid']}] " if e.get("uid") else ""
        display_btn = f"{uid_str}{e['name']}"[:30]
        buttons.append([Button.inline(display_btn, f"pk:{code}:{start + i}".encode())])
    nav = []
    if page > 1:
        nav.append(Button.inline("⬅️ قبلی", f"pg:{code}:{page - 1}".encode()))
    nav.append(Button.inline("🔙 منوی ارائه‌دهندگان", b"ls:menu"))
    if page < total:
        nav.append(Button.inline("بعدی ➡️", f"pg:{code}:{page + 1}".encode()))
    if nav:
        buttons.append(nav)
    buttons.append([Button.inline("✖️ بستن", b"x")])
    return "\n".join(lines), buttons


def parse_voice_command(text: str) -> Optional[dict]:
    t = text.lower().strip()

    # ۱. دستورات اختصاصی موتور ربات تلگرام (@jarvis_roobot)
    if any(k in t for k in ("ربات", "جارویس", "jarvis", "jarvoice")):
        from services.voice import jarvis_bot
        v_info, t_info = jarvis_bot.parse_voice_and_tone(t)
        if v_info or t_info:
            return {"action": "set_jarvis", "voice": v_info, "tone": t_info}
        if any(w in t for w in ("صدا", "ویس", "موتور", "فعال", "روشن")):
            return {"action": "set_engine", "engine": "jarvis"}

    # اگر دستور مربوط به ویس دادن عادی یا سوال دیگری است، دستور سوئیچ نیست
    voice_keywords = (
        "گوینده", "صدا", "فرید", "دلارا", "جمینای", "جمنای", "gemini",
        "شارون", "پاک", "پک", "کوره", "فنریر", "آئوده", "ائوده",
        "charon", "puck", "kore", "fenrir", "aoede", "ربات", "جارویس"
    )
    if any(w in t for w in ("بده", "بگیر", "بفرست", "بگو")) and not any(k in t for k in voice_keywords):
        return None
    if not any(w in t for w in ("صدا", "گوینده", "ویس", "شارون", "پاک", "کوره", "فنریر", "آئوده", "charon", "puck", "kore", "fenrir", "aoede", "ربات", "جارویس")):
        return None

    # ۲. استعلام لیست یا وضعیت صداها
    if any(k in t for k in ("چه صدایی", "صدای فعال", "کدوم صدا", "لیست صدا", "صداها چیه", "گوینده‌ها", "لیست گوینده", "چه گوینده")) or ("صدا" in t and ("چیه" in t or "چیست" in t or "کدوم" in t)):
        return {"action": "info"}

    # ۳. گوینده‌های اختصاصی Gemini TTS
    if "شارون" in t or "charon" in t or ("بم" in t and "جمینای" in t):
        return {"action": "set_gemini", "voice": "Charon"}
    if "کوره" in t or "kore" in t or ("زن" in t and "جمینای" in t):
        return {"action": "set_gemini", "voice": "Kore"}
    if "فنریر" in t or "fenrir" in t or ("حماسی" in t and "جمینای" in t):
        return {"action": "set_gemini", "voice": "Fenrir"}
    if "آئوده" in t or "ائوده" in t or "aoede" in t:
        return {"action": "set_gemini", "voice": "Aoede"}
    if "پاک" in t or "پک" in t or "puck" in t:
        return {"action": "set_gemini", "voice": "Puck"}

    # ۴. موتور کلی جمینای (بدون گوینده خاص)
    if any(k in t for k in ("جمینای", "جمنای", "gemini")):
        return {"action": "set_engine", "engine": "gemini"}

    # ۵. موتور مایکروسافت
    if any(k in t for k in ("مایکروسافت", "ماکروسافت", "microsoft", "edge")):
        return {"action": "set_engine", "engine": "microsoft"}

    # ۶. گوینده‌های مایکروسافت
    if "دلارا" in t or "زن" in t:
        return {"action": "set_edge", "voice": "fa-IR-DilaraNeural"}
    if "فرید" in t or "مرد" in t:
        return {"action": "set_edge", "voice": "fa-IR-FaridNeural"}

    return None


async def handle_voice_command(event, status, cmd: dict):
    act = cmd.get("action")
    if act == "info":
        eng = settings.get_tts_engine()
        speaker = settings.get_voice_speaker()
        if eng == "jarvis":
            eng_name = "ربات تلگرام (@jarvis_roobot)"
        elif eng == "gemini":
            eng_name = "Google Gemini TTS"
        else:
            eng_name = "Microsoft Edge-TTS"

        from services.voice import jarvis_bot
        vid = settings.get_jarvis_voice()
        tid = settings.get_jarvis_tone()
        cur_jv = jarvis_bot.VOICES.get(str(vid), jarvis_bot.VOICES["1"])
        cur_jt = jarvis_bot.TONES.get(str(tid), jarvis_bot.TONES["1"])

        msg = (
            f"🎙 **داشبورد وضعیت صدای کاپری:**\n\n"
            f"🔊 **گوینده فعال کنونی:** {speaker}\n"
            f"⚙️ **موتور صوتی:** {eng_name}\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🤖 **موتور ربات تلگرام (@jarvis_roobot):**\n"
            f"• گوینده انتخابی: {cur_jv['name']} | لحن: {cur_jt['name']}\n"
            f"• دستور انتخاب سریع: `کاپری ربات سارا 6` یا `کاپری صدای ربات`\n\n"
            f"💎 **گوینده‌های هوشمند Google Gemini:**\n"
            f"• `کاپری صدا شارون` — بم، عمیق، رسمی و جدی (مردانه)\n"
            f"• `کاپری صدا کوره` — آرامش‌بخش، گرم و باوقار (زنانه)\n"
            f"• `کاپری صدا پاک` — پرانرژی، پویا و صمیمی (جوان)\n"
            f"• `کاپری صدا فنریر` — رسا، باصلابت و قدرتمند (حماسی)\n"
            f"• `کاپری صدا آئوده` — ملایم، لطیف و متفکر (آرام)\n\n"
            f"⚡ **گوینده‌های نامحدود Microsoft Edge-TTS:**\n"
            f"• `کاپری صدا دلارا` — زنانه، طبیعی و شفاف\n"
            f"• `کاپری صدا فرید` — مردانه، واضح و رسا"
        )
        await status.edit(msg)
        return

    if act == "set_jarvis":
        v_info = cmd.get("voice")
        t_info = cmd.get("tone")
        from services.voice import jarvis_bot
        ok, msg = await jarvis_bot.configure_jarvis(client, v_info, t_info)
        await status.edit(msg)
        return

    if act == "set_gemini":
        v = cmd.get("voice", "Puck")
        settings.set_tts_engine("gemini")
        settings.set_gemini_voice(v)
        info = voice.GEMINI_VOICES.get(v, {})
        fa_name = info.get("fa", v)
        desc = info.get("desc", "")
        await status.edit(
            f"✅ صدای کاپری به **Google Gemini ({fa_name})** تغییر یافت! 🎙️\n\n"
            f"🎭 **استایل و لحن:** {desc}\n"
            f"💡 در صورت اتمام سهمیه روزانه جمینای، صدا به صورت خودکار به مایکروسافت فال‌بک می‌شود."
        )
        return

    if act == "set_engine":
        engine = cmd.get("engine", "microsoft")
        settings.set_tts_engine(engine)
        if engine == "jarvis":
            from services.voice import jarvis_bot
            vid = settings.get_jarvis_voice()
            tid = settings.get_jarvis_tone()
            cur_v = jarvis_bot.VOICES.get(str(vid), jarvis_bot.VOICES["1"])
            cur_t = jarvis_bot.TONES.get(str(tid), jarvis_bot.TONES["1"])
            await status.edit(
                f"✅ موتور صدا: **ربات تلگرام (@{jarvis_bot.JARVIS_BOT})**\n\n"
                f"👤 **گوینده فعال:** {cur_v['name']} ({cur_v['gender']}) — `/voice{vid}`\n"
                f"🎭 **لحن فعال:** {cur_t['name']} ({cur_t['desc']}) — `/tone{tid}`\n\n"
                f"💡 برای تغییر گوینده و لحن کافی است بگویید:\n"
                f"• `کاپری ربات سارا 6` (گوینده سارا با لحن حماسی)\n"
                f"• `کاپری ربات باران 2` (گوینده باران با لحن صمیمی)\n"
                f"• `کاپری ربات کیوان 4` (گوینده کیوان با لحن باانرژی)"
            )
        elif engine == "gemini":
            v = settings.get_gemini_voice()
            info = voice.GEMINI_VOICES.get(v, {})
            fa_name = info.get("fa", v)
            await status.edit(
                f"✅ موتور صدا: **Google Gemini TTS ({fa_name})**\n"
                f"🎙 صدای هوش مصنوعی با ۵ گوینده مجزا.\n"
                f"برای تغییر گوینده بگو: `کاپری صدا شارون`، `کاپری صدا کوره` یا `کاپری لیست صداها`."
            )
        else:
            await status.edit(
                "✅ موتور صدا: **Microsoft Edge-TTS** (۱۰۰٪ رایگان و نامحدود).\n"
                "برای تغییر گوینده بگو: `کاپری صدا دلارا` یا `کاپری صدا فرید`."
            )
        return

    if act in ("set", "set_edge"):
        settings.set_tts_engine("microsoft")
        v = cmd.get("voice", "fa-IR-FaridNeural")
        settings.set_tts_voice(v)
        lbl = "دلارا (زن - طبیعی و شفاف)" if "Dilara" in v else "فرید (مرد - رسا)"
        await status.edit(f"✅ صدای کاپری به **Microsoft Edge-TTS ({lbl})** تغییر یافت (۱۰۰٪ رایگان و بدون محدودیت).")
        return


async def _confirm_model(event, status, service, model_id, note: str = ""):
    await _stage(status, f"🔍 دارم مدل {model_id} رو بررسی می‌کنم...")
    text, _ = await asyncio.to_thread(
        providers.ask_model, service, model_id, "سلام", "فقط کلمه‌ی OK رو بنویس.")
    if not text:
        text, _ = await asyncio.to_thread(
            providers.ask_model, service, model_id, "You are a test assistant.", "Say OK")
    if not text:
        e = models.find(service, model_id)
        if e:
            settings.set_selection(service, model_id)
            uid_str = f" (شناسه: `{e['uid']}`)" if e.get("uid") else ""
            msg = (f"✅ مدل فعال شد: **{e['name']}**{uid_str}\n"
                   f"سرویس: {models.service_name(service)}\n`{model_id}`\n\n"
                   f"{e['desc']}")
            await status.edit(msg)
            return
        await status.edit(
            f"❌ مدل `{model_id}` الان در دسترس نیست (نامعتبر/سهمیه/شبکه). انتخاب قبلی تغییری نکرد.")
        return
    settings.set_selection(service, model_id)
    e = models.find(service, model_id)
    uid_str = f" (شناسه: `{e['uid']}`)" if e and e.get("uid") else ""
    msg = (f"✅ مدل فعال شد: **{e['name'] if e else model_id}**{uid_str}\n"
           f"سرویس: {models.service_name(service)}\n`{model_id}`\n\n"
           f"{e['desc'] if e else ''}")
    if note:
        msg += f"\n\n💡 {note}"
    await status.edit(msg)


async def _handle_model_request(event, status, req):
    action = req.get("action")
    if action == "info":
        sel = settings.get_selection()
        if sel[0] and sel[1]:
            e = models.find(sel[0], sel[1])
            await status.edit(
                f"ℹ️ مدل فعال: **{e['name'] if e else sel[1]}** ({models.service_name(sel[0])})\n`{sel[1]}`")
        else:
            await status.edit(f"ℹ️ الان مدل فعال: {ai.model_label(settings.get_model())}")
        return
    if action == "restore":
        prev = settings.get_previous()
        if prev[0] and prev[1]:
            settings.set_selection(prev[0], prev[1])
            e = models.find(prev[0], prev[1])
            await status.edit(
                f"↩️ برگشتم به: **{e['name'] if e else prev[1]}** ({models.service_name(prev[0])})")
        else:
            await status.edit("مدل قبلی ثبت نشده که برگردم بهش.")
        return
    if action == "doc":
        import os
        if os.path.exists("MODELS.md"):
            await client.send_file(event.chat_id, "MODELS.md", caption="📄 **کاتالوگ جامع ۲۵۳ مدل هوش مصنوعی کاپری** به همراه شناسه‌های یکتا (UID) و دستورات سوییچ فوری.")
            await status.delete()
        else:
            await status.edit("❌ فایل کاتالوگ MODELS.md یافت نشد.")
        return
    if action == "list":
        service = req.get("service")
        if service:
            text, buttons = _render_model_list(service, 1)
            await status.edit(text, buttons=buttons)
        else:
            text, buttons = _render_provider_menu()
            await status.edit(text, buttons=buttons)
        return
    if action == "smart":
        entry = models.smart_pick(req.get("cat", "general"))
        if not entry:
            await status.edit("مدلی برای این کاربرد پیدا نکردم.")
            return
        note = f"{entry['reason']} — رایگان (رتبه‌بندی واقعی رو تضمین نمی‌کنم)."
        await _confirm_model(event, status, entry["service"], entry["id"], note=note)
        return
    if action == "select":
        await _confirm_model(event, status, req["service"], req["model"])
        return


_owner_id = None


async def _is_owner_callback(event) -> bool:
    """بررسی اینکه دکمه‌ی اینلاین را فقط صاحب اکانت فشرده باشد (نه غریبه در گروه/چت مشترک)."""
    global _owner_id
    try:
        if _owner_id is None:
            me = await client.get_me()
            _owner_id = me.id
        return int(getattr(event, "sender_id", 0) or 0) == _owner_id
    except Exception:
        return False


@client.on(events.CallbackQuery())
async def on_model_callback(event):
    if not await _is_owner_callback(event):
        try:
            await event.answer("🔒 فقط صاحب اکانت می‌تواند از این دکمه استفاده کند.")
        except Exception:
            pass
        return
    try:
        s = event.data.decode("utf-8", "replace")
    except Exception:
        s = ""
    try:
        if s.startswith("sd:"):
            await event.answer()
            draft_id = s.split(":", 1)[1]
            from services.social import drafter
            draft = drafter.remove_draft(draft_id)
            if not draft:
                await event.edit("این پیش‌نویس منقضی یا قبلاً ارسال شده است.")
                return
            ok, res_msg = await drafter.send_draft_message(client, draft["target"], draft["text"])
            if ok:
                await event.edit(f"✅ پیام با موفقیت به «{draft['name']}» ارسال شد:\n\n«{draft['text']}»")
            else:
                await event.edit(res_msg)
            pending.pop(str(event.chat_id), None)
            return
        if s.startswith("cd:"):
            await event.answer("پیش‌نویس لغو شد.")
            draft_id = s.split(":", 1)[1]
            from services.social import drafter
            drafter.remove_draft(draft_id)
            pending.pop(str(event.chat_id), None)
            await event.edit("✖️ پیش‌نویس پیام لغو شد.")
            return
        if s == "x":
            await event.answer()
            await event.delete()
            return
        if s == "ls:menu":
            await event.answer()
            text, buttons = _render_provider_menu()
            await event.edit(text, buttons=buttons)
            return
        if s == "ls:doc":
            await event.answer("در حال ارسال فایل...")
            import os
            if os.path.exists("MODELS.md"):
                await client.send_file(event.chat_id, "MODELS.md", caption="📄 **کاتالوگ جامع ۲۵۳ مدل هوش مصنوعی کاپری** به همراه شناسه‌های یکتا (UID) و دستورات سوییچ فوری.")
            return
        if s.startswith("ls:"):
            await event.answer()
            service = _code_service(s.split(":")[1])
            text, buttons = _render_model_list(service, 1)
            await event.edit(text, buttons=buttons)
            return
        if s.startswith("pg:"):
            await event.answer()
            _, code, page = s.split(":")
            text, buttons = _render_model_list(_code_service(code), int(page))
            await event.edit(text, buttons=buttons)
            return
        if s.startswith("pk:"):
            _, code, idx = s.split(":")
            service = _code_service(code)
            lst = _service_models(service)
            i = int(idx)
            if 0 <= i < len(lst):
                e = lst[i]
                await event.answer("در حال بررسی...")
                text, _ = await asyncio.to_thread(
                    providers.ask_model, service, e["id"], "سلام", "فقط کلمه‌ی OK رو بنویس.")
                if not text:
                    await event.edit(
                        f"❌ مدل `{e['id']}` الان در دسترس نیست (نامعتبر/سهمیه/شبکه). انتخاب قبلی تغییری نکرد.")
                    return
                settings.set_selection(service, e["id"])
                await event.edit(
                    f"✅ مدل فعال شد: **{e['name']}**\n"
                    f"سرویس: {models.service_name(service)}\n`{e['id']}`\n\n{e['desc']}")
            else:
                await event.answer("خطا")
            return
    except Exception:
        pass
    try:
        await event.answer()
    except Exception:
        pass


ACCESS_ALLOW_WORDS = ("مجوز بده", "اجازه بده", "جوابشو بده", "جوابش بده", "بذار جواب بده", "بزار جواب بده")
ACCESS_DENY_WORDS = ("مجوز بگیر", "اجازه نده", "جوابشو نده", "جوابش نده", "نذار جواب بده", "نزار جواب بده")
ACCESS_LIST_WORDS = ("لیست مجوزها", "لیست مجوز", "مجوزها", "کاربران مجاز")


def _parse_access_command(question: str):
    """تشخیص فرمان مستقیم مدیریت مجوزها: list / allow / deny یا None."""
    q = _normalize_fa(question)
    for w in ACCESS_LIST_WORDS:
        if w in q:
            return "list"
    for w in ACCESS_DENY_WORDS:
        if w in q:
            return "deny"
    for w in ACCESS_ALLOW_WORDS:
        if w in q:
            return "allow"
    return None


async def _access_target(event):
    """کاربر هدف فرمان کنترل دسترسی: شخصِ ریپلای‌شده در گروه یا طرف چت خصوصی."""
    reply_id = getattr(event, "reply_to_msg_id", None)
    if reply_id:
        try:
            rep = await client.get_messages(event.chat_id, ids=reply_id)
            if rep and rep.sender_id:
                try:
                    ent = await client.get_entity(rep.sender_id)
                    first = (getattr(ent, "first_name", "") or "").strip()
                    last = (getattr(ent, "last_name", "") or "").strip()
                    name = f"{first} {last}".strip() or str(rep.sender_id)
                except Exception:
                    ent = None
                    name = str(rep.sender_id)
                return rep.sender_id, name, ent
        except Exception:
            pass
    if event.is_private:
        uid = event.chat_id
        try:
            ent = await client.get_entity(uid)
            first = (getattr(ent, "first_name", "") or "").strip()
            last = (getattr(ent, "last_name", "") or "").strip()
            name = f"{first} {last}".strip() or str(uid)
        except Exception:
            ent = None
            name = str(uid)
        return uid, name, ent
    return None, None, None


async def _handle_access_command(event, action: str) -> None:
    if action == "list":
        allowed = access.get_allowed_users()
        if not allowed:
            await client.send_message(event.chat_id, "هیچ کاربری در لیست مجوزها وجود ندارد.", parse_mode=None)
            return
        lines = ["لیست کاربران مجاز:"]
        for idx, uid in enumerate(allowed, 1):
            try:
                ent = await client.get_entity(uid)
                first = (getattr(ent, "first_name", "") or "").strip()
                last = (getattr(ent, "last_name", "") or "").strip()
                name = f"{first} {last}".strip() or str(uid)
            except Exception:
                name = "ناشناس"
            lines.append(f"{idx}. نام: {name} | شناسه: {uid}")
        await client.send_message(event.chat_id, "\n".join(lines), parse_mode=None)
        return

    uid, name, ent = await _access_target(event)
    if uid is None:
        await client.send_message(
            event.chat_id,
            "❌ کاربر هدف مشخص نیست. در گروه روی پیام شخص ریپلای کنید، یا در پیوی او این دستور را بفرستید.",
            parse_mode=None
        )
        return

    me = await client.get_me()
    if uid == me.id:
        await client.send_message(event.chat_id, "❌ امکان تغییر مجوز برای خود مالک اکانت وجود ندارد.", parse_mode=None)
        return

    if ent and getattr(ent, "bot", False):
        await client.send_message(event.chat_id, "❌ ربات‌ها هرگز مجاز نیستند و امکان اعطای مجوز به آن‌ها وجود ندارد.", parse_mode=None)
        return

    if action == "allow":
        access.allow_user(uid)
        await client.send_message(event.chat_id, f"✅ کاربر {name} با شناسه {uid} به لیست مجوزها اضافه شد.", parse_mode=None)
    else:
        access.deny_user(uid)
        await client.send_message(event.chat_id, f"🚫 مجوز کاربر {name} با شناسه {uid} لغو شد و از لیست مجاز حذف گردید.", parse_mode=None)


@client.on(events.NewMessage(outgoing=True))
async def on_outgoing(event):
    if (event.chat_id, event.id) in self_sent or event.id in self_sent:
        return

    # ۱. گارد قطعی پیام‌های فورواردشده و ربات‌ها:
    if getattr(event, "fwd_from", None) or getattr(event.message, "fwd_from", None):
        return
    if getattr(event, "via_bot_id", None) or getattr(event.message, "via_bot_id", None) or getattr(event, "via_bot", None) or getattr(event.message, "via_bot", None):
        return

    text = event.raw_text or ""
    key = str(event.chat_id)

    # بررسی تایید یا لغو پیش‌نویس پیام (Ghostwriter confirmation) با تطبیق مرز کلمه
    reply_id = getattr(event, "reply_to_msg_id", None)
    draft = drafter.get_pending_draft(event.chat_id, reply_id)
    if draft:
        tokens = set(re.findall(r"[a-z0-9آ-ی]+", _normalize_fa(text)))
        if tokens & _POS_WORDS:
            drafter.pop_pending_draft(event.chat_id, reply_id)
            ok, res_msg = await drafter.send_draft_message(client, draft["target"], draft["text"])
            if ok:
                await event.reply(f"✅ پیام با موفقیت برای «{draft['name']}» ارسال شد:\n\n«{draft['text']}»")
            else:
                await event.reply(res_msg)
            return
        elif tokens & _NEG_WORDS:
            drafter.pop_pending_draft(event.chat_id, reply_id)
            await event.reply(f"✖️ ارسال پیام به «{draft['name']}» لغو شد.")
            return

    # جواب به سوال معلق یا تاییدیه کارهای حساس با تطابق کلمه مستقل و TTL مشخص
    if key in pending:
        p = pending.get(key)
        if p and _is_confirmation_response(text, p):
            p = _take_pending(key)
            if p is not None:
                try:
                    await _answer_pending(event, p, text)
                except Exception as e:
                    log.error("Error answering pending action: %s", type(e).__name__, exc_info=True)
                    await event.reply("❌ خطایی در انجام عملیات رخ داد؛ لطفاً دوباره تلاش کنید.")
                return

    # طبق ضوابط امنیتی، در on_outgoing فقط پیام‌هایی پردازش می‌شوند که تریگر در ابتدای متن باشد
    if not starts_with_trigger(text):
        return

    pending.pop(key, None)  # فرمان جدید → سوال معلق قبلی لغو می‌شه

    question = strip_trigger(text)

    # فرمان کنترل دسترسی: «جوابشو بده» / «جوابشو نده» (فقط مالک، چون پیام خروجی است)
    acc = _parse_access_command(question)
    if acc:
        await _handle_access_command(event, acc)
        return

    # گوش/چشم: ویس یا عکس (خود پیام یا ریپلای) — فقط با اسم دستیار
    media_msg = await _media_target(event)
    if media_msg is not None and getattr(media_msg, "media", None):
        if await _handle_media(event, media_msg, question):
            return

    if not question:
        return

    status = None
    try:
        status = await event.reply("🧠 در حال جمع‌آوری اطلاعات...")
        self_sent.add(status.id)

        # استخراج داده‌های پیام ریپلای‌شده در صورت وجود
        reply_info = await get_reply_info(event, client)

        # اگر کاربر روی پیامی ریپلای کرده و پرسیده «این عکس چیه؟» اما عکسی وجود ندارد یا پیام حذف شده
        if getattr(event, "reply_to_msg_id", None) and any(w in question for w in ("این عکس چیه", "این تصویر چیه", "عکس چیه", "تصویر چیه", "عکس رو ببین", "عکس چیست")):
            if reply_info and not reply_info.get("is_available"):
                await _safe_edit_or_send(event, status, "❌ پیامی که به آن ریپلای زدید در دسترس نیست یا احتمالاً حذف شده است.")
                return
            if not reply_info or reply_info.get("media_type") != "photo":
                await _safe_edit_or_send(event, status, "ℹ️ پیامی که به آن ریپلای زدید فاقد تصویر است یا فایل تصویر آن در دسترس نیست.")
                return

        # اگر کاربر روی پیامی ریپلای کرده که حذف شده و خواسته خلاصه‌اش کند یا درباره‌اش سوال کرده
        if getattr(event, "reply_to_msg_id", None) and reply_info and not reply_info.get("is_available"):
            if _is_summary_request(question) or any(w in question for w in ("این چیه", "نظرت چیه", "بررسی کن", "توضیح بده")):
                await _safe_edit_or_send(event, status, "❌ پیامی که به آن ریپلای زدید در دسترس نیست یا احتمالاً حذف شده است.")
                return

        # ۱. مسیریابی هوشمند لینک‌های شبکه‌های اجتماعی (اینستاگرام، تیک‌تاک، پینترست، X، ساوندکلاد)
        from services.media import socialdl
        social_url = socialdl.extract_social_url(question)
        if not social_url and reply_info and reply_info.get("social_url"):
            social_url = reply_info["social_url"]

        if social_url:
            # اگر کاربر سوال محتوایی یا درخواست خلاصه‌سازی دارد، دانلود خودکار نکن تا ایجنت متن را بررسی کند
            if not _is_summary_request(question) and not _is_video_info_request(question):
                await _stage(status, "⬇️ لینک رسانه‌ای تشخیص داده شد؛ در حال دریافت فایل...")
                try:
                    result = await socialdl.download_social(client, social_url, event=event, status=status)
                except Exception as e:
                    result = f"❌ خطا در دانلود: {logger.redact_secrets(str(e))}"
                await _safe_edit_or_send(event, status, result)
                return

        # ۲. مسیریابی دقیق و تفکیک‌شده لینک‌های یوتیوب بر اساس نیت کاربر:
        from services.media import ytsummary
        yt_id = ytsummary.extract_youtube_id(question)
        target_yt = question
        if not yt_id and reply_info and reply_info.get("yt_id"):
            yt_id = reply_info["yt_id"]
            target_yt = reply_info["yt_id"]

        if yt_id:
            # سناریوی B: خلاصه‌سازی محتوایی و متنی ویدیو
            if _is_summary_request(question):
                await _stage(status, "🎬 در حال مطالعه و خلاصه‌سازی هوشمند ویدیوی یوتیوب...")
                try:
                    result = await asyncio.to_thread(ytsummary.summarize_youtube_video, target_yt)
                except Exception as e:
                    result = f"❌ خطا در خلاصه‌سازی یوتیوب: {logger.redact_secrets(str(e))}"
                await _safe_edit_or_send(event, status, result)
                return

            # سناریوی C: اطلاعات و متادیتای ویدیو (بدون دانلود و بدون خلاصه)
            if _is_video_info_request(question):
                await _stage(status, "🎬 در حال دریافت مشخصات و متادیتای ویدیو...")
                try:
                    result = await asyncio.to_thread(ytsummary.get_youtube_video_info, target_yt)
                except Exception as e:
                    result = f"❌ خطا در استخراج اطلاعات یوتیوب: {logger.redact_secrets(str(e))}"
                await _safe_edit_or_send(event, status, result)
                return

            # سناریوی A: دانلود صریح فایل ویدیو
            clean_q = re.sub(r"https?://\S+", "", question).strip()
            if _is_download_request(question) or len(clean_q) <= 15 or (reply_info and reply_info.get("yt_id")):
                from services.media import ytdownload
                await _stage(status, "🎬 در حال آماده‌سازی و دانلود ویدیوی یوتیوب...")
                try:
                    q_m = re.search(r"\b(1080|720|480|360)\b", question)
                    target_q = int(q_m.group(1)) if q_m else 720
                    result = await ytdownload.download_youtube_video(client, target_yt, quality=target_q, event=event, status=status)
                except Exception as e:
                    result = f"❌ خطا در دانلود یوتیوب: {logger.redact_secrets(str(e))}"
                await _safe_edit_or_send(event, status, result)
                return

        # ۳. خلاصه‌سازی مستقیم پیام متنی در صورت ریپلای با دستور «خلاصه کن»
        if _is_summary_request(question) and reply_info and reply_info.get("has_reply") and reply_info.get("text"):
            r_author = reply_info.get("author_name") or "کاربر"
            r_id = reply_info.get("author_id")
            r_text = reply_info.get("text", "").strip()
            id_str = f" با شناسه {r_id}" if r_id is not None else ""
            question = f"لطفاً متن پیام زیر از {r_author}{id_str} را با دقت، ساختاریافته و شیوایی به زبان فارسی خلاصه کن:\n\n«{r_text}»"

        # حالت رول‌پلی (راوی تعاملی): شروع/پایان/نگه‌داشتن/ادامه + تمام پیام‌های حین بازی
        if await roleplay.handle(event, status, question, client):
            return

        # ۱. فرامین قطعی تنظیمات و پیکربندی:
        # تغییر موتور و گوینده ویس (Microsoft)
        v_cmd = parse_voice_command(question)
        if v_cmd:
            await handle_voice_command(event, status, v_cmd)
            return

        # تغییر مدل (منوی Groq / OpenRouter / Hooshia)
        req = models.parse_request(question)
        if req:
            await _handle_model_request(event, status, req)
            return

        # تغییر مدل (سوئیچ سادهٔ پرووایدر: جمینای/گروک/اوپن‌روتر/هوشیا/خودکار)
        mkey = ai.parse_model_command(question)
        if mkey:
            settings.set_model(mkey)
            await status.edit(f"✅ از این به بعد مدل: {ai.model_label(mkey)}")
            return
        if "چه مدلی" in question or "کدوم مدل" in question or "مدل فعال" in question:
            await status.edit(f"الان مدل فعال: {ai.model_label(settings.get_model())}")
            return

        # داشبورد وضعیت و آمار کاپری
        if question in ("وضعیت", "آمار", "استاتوس", "وضعیت ربات", "وضعیت سیستم", "وضعیت کاپری"):
            dash = dnd.get_dashboard_status(
                uptime_str=_get_uptime_str(),
                active_model=ai.model_label(settings.get_model()),
                voice_str=getattr(settings, "get_voice_speaker", lambda: "دلارا")() or "دلارا"
            )
            await _safe_edit_or_send(event, status, dash + f"\n\n🆔 شناسه یکتای نمونه: `{config.INSTANCE_ID}`")
            return

        # خلاصه‌ساز صورتجلسه گروه/چت (مسیر مستقیم و مطمئن، مستقل از ایجنت)
        if _is_group_summary_request(question):
            from ai_engine import skills_manager
            await _stage(status, "📊 دارم پیام‌های اخیر رو می‌خونم و صورتجلسه می‌سازم...")
            try:
                result = await skills_manager.execute_skill("summarize_chat_history", {"limit": 200}, client, event)
            except Exception as e:
                result = f"❌ خطا در ساخت صورتجلسه: {logger.redact_secrets(str(e))}"
            await _safe_edit_or_send(event, status, result)
            return

        # بازنویسی/ویراستاری تمیز فارسی (اسکیل نگارش فارسی — مسیر مستقیم و مطمئن)
        if _is_persian_rewrite_request(question):
            from ai_engine import skills_manager
            await _stage(status, "✍️ دارم متن رو ویرایش و بازنویسی می‌کنم...")
            try:
                result = await skills_manager.execute_skill("persian_writing", {"text": _extract_rewrite_text(question)}, client, event)
            except Exception as e:
                result = f"❌ خطا در بازنویسی متن: {logger.redact_secrets(str(e))}"
            await _safe_edit_or_send(event, status, result)
            return

        # مرتب‌سازی خودکار پوشه‌ها (مسیر مستقیم و مطمئن، مستقل از ایجنت)
        if _is_folder_sort_request(question):
            await _stage(status, "🗂 دارم کانال‌ها و گروه‌ها رو بررسی و دسته‌بندی می‌کنم...")
            await _do_sort(event, status)
            return

        # خروج از کانال‌ها یا گروه‌ها بر اساس موضوع یا نام (مسیر مستقیم و سریع)
        if _is_channel_leave_request(question):
            keyword = _extract_channel_leave_keyword(question)
            if not keyword:
                await status.edit("❓ از چه کانال‌هایی می‌خوای لفت بدم؟ مثلاً بگو: «کاپری از کانال‌های کنکور لفت بده»")
                return
            await _stage(status, f"🔍 دارم کانال‌های مرتبط با «{keyword}» رو بررسی می‌کنم...")
            dialogs = await channels.find_channels(client, keyword, max_scan=500)
            if not dialogs:
                await _safe_edit_or_send(event, status, f"❌ هیچ کانال یا گروهی مرتبط با «{keyword}» در اکانت شما پیدا نشد.")
                return
            chat_key = str(event.chat_id)
            if len(dialogs) == 1:
                pending[chat_key] = {"kind": "confirm_leave_single", "dialog": dialogs[0], "name": dialogs[0].name}
                await _safe_edit_or_send(event, status, f"⚠️ برای خروج از کانال «{dialogs[0].name}»، لطفاً تایید کنید. (بگویید «آره» یا «نه»)")
            else:
                names = "\n".join(f"{i + 1}. {d.name}" for i, d in enumerate(dialogs))
                pending[chat_key] = {"kind": "leave", "dialogs": dialogs}
                await _safe_edit_or_send(event, status, f"📋 این کانال‌ها رو پیدا کردم:\n{names}\n\nکدام را لفت بزنم؟ بگویید «همه» یا شماره‌ها (مثلاً 1، 3).")
            return

        # جستجوی عکس (مسیر مستقیم و سریع، مستقل از ایجنت)
        if _is_image_request(question):
            query = _extract_image_query(question)
            await _stage(status, "🖼 دارم دنبال عکس می‌گردم...")
            result = await send_images(event, query)
            await _safe_edit_or_send(event, status, result)
            memory.remember_exchange(event.chat_id, question, result)
            return

        # حالت سرشلوغ (DND) و یادآورها (فقط مالک)
        if await dnd.handle_owner_command(event, status, question):
            return

        # سازمان‌دهی و مدیریت صندوق هوشمند سیو مسیج (فقط مالک)
        if await vault.handle_vault_command(event, status, question):
            return

        # حالت همزاد: فعال/غیرفعال (فقط مالک)
        if _is_ghost_deactivate(question):
            ghost.deactivate()
            dnd.deactivate_dnd()
            await status.edit("✅ کاپری برگشت به حالت عادی.")
            return

        if _is_ghost_activate(question):
            await _stage(status, "🕵️ دارم سبک چت کردنت رو آنالیز می‌کنم...")
            persona = await ghost.extract_persona(client)
            if not persona:
                await status.edit("❌ نتونستم سبک چت کردنت رو استخراج کنم (نمونه‌ی کافی از پیام‌هات پیدا نشد).")
                return
            ghost.activate(persona)
            summary = (
                "✅ حالت همزاد فعال شد! کاپری از این به بعد توی پیوی، به‌جای تو به کاربران مجازت جواب می‌ده.\n\n"
                "📋 پروفایل سبک تو:\n" + persona
            )
            if _is_long_or_code(summary):
                await _send_as_md(event, status, summary)
            else:
                await _safe_edit_or_send(event, status, summary)
            return

        # تحلیل چت: گزارش داده‌محور از تاریخچه چت فعلی (مستقل از ایجنت)
        if chatanalysis.is_chat_analysis_request(question):
            await _stage(status, "🕵️ دارم تاریخچه این چت رو کالبدشکافی می‌کنم...")
            report = await chatanalysis.analyze_chat(client, event)
            await _stage(status, "📝 دارم گزارش رو می‌نویسم...")
            await _send_as_md(event, status, report)
            return

        # ۲. کلیه پیام‌ها مستقیماً وارد ایجنت هوشمند می‌شوند و مدل خودش ابزار را تشخیص می‌دهد
        scope_id = memory.get_event_memory_scope(event, owner_id=_owner_id)
        context = await get_context(event)
        hist = memory.load_history(scope_id)
        if hist:
            context = (hist + "\n\n" + context).strip()
        mem = memory.relevant_facts(question, scope_id=scope_id)

        # جستجوی وب (مسیر مستقیم، سریع و با خروجی جمینای — مستقل از ایجنت کند)
        if _is_web_question(question):
            await _stage(status, "🔍 دارم سریع جستجو می‌کنم...")
            raw_answer = await asyncio.to_thread(ai.ask_web_reliable, question, context, mem, chat_id=scope_id)
            answer = agent.sanitize_tainted_output(raw_answer)
            await _stage(status, "📝 دارم جواب می‌دم...")
            if _is_long_or_code(answer):
                await _send_as_md(event, status, answer)
            else:
                await _safe_edit_or_send(event, status, answer, link_preview=False)
            return

        # سوال ساده/گفتگویی (بدون ابزار) → پاسخ مستقیم و سریع با جمینای، بدون حلقه‌ی کند ایجنت
        if _is_simple_question(question):
            await _stage(status, "💭 دارم جواب می‌دم...")
            answer = await asyncio.to_thread(ai.answer_quick, question, context, mem, chat_id=scope_id)
            await _stage(status, "📝 دارم جواب می‌دم...")
            if _is_long_or_code(answer):
                await _send_as_md(event, status, answer)
            else:
                await _safe_edit_or_send(event, status, answer)
            memory.remember_exchange(scope_id, question, answer)
            asyncio.create_task(_trigger_learn(question, answer, scope_id, event.chat_id))
            return

        await _stage(status, "🤔 دارم فکر می‌کنم...")
        answer = await agent.run_agent(question, context, mem, event, client, status, is_owner=True, sender_name=config.OWNER_NAME or "مالک")

        is_tainted = agent.get_last_run_tainted()

        if answer.startswith("__VOICE_SENT__:"):
            real_text = answer.replace("__VOICE_SENT__:", "").strip()
            if not is_tainted:
                memory.remember_exchange(scope_id, question, real_text)
                asyncio.create_task(_trigger_learn(question, real_text, scope_id, event.chat_id))
            return

        if answer.startswith("__DRAFT_SENT__:") or answer in ("__ROAST_SENT__", "__MEME_SENT__"):
            return

        wants_voice = any(w in question for w in VOICE_WORDS) and any(w in question for w in ACTION_WORDS)
        if wants_voice and answer:
            voice_text = _clean_voice_text(answer)
            ts = int(time.time() * 1000)
            mp3 = os.path.join(config.DOWNLOAD_DIR, f"tts_{ts}.mp3")
            ogg = os.path.join(config.DOWNLOAD_DIR, f"tts_{ts}.ogg")
            ok = await voice.speak(voice_text, mp3, client=client)
            converted = await asyncio.to_thread(voice.to_ogg, mp3, ogg) if ok else False
            if not ok or not converted or not os.path.exists(ogg) or os.path.getsize(ogg) < 1000:
                try:
                    import edge_tts
                    clean_fb = voice.prepare_for_tts(voice_text)
                    c = edge_tts.Communicate(clean_fb, "fa-IR-FaridNeural", rate="+5%")
                    await c.save(mp3)
                    converted = await asyncio.to_thread(voice.to_ogg, mp3, ogg)
                    ok = converted and os.path.exists(ogg) and os.path.getsize(ogg) >= 1000
                except Exception:
                    ok = False

            if ok and os.path.exists(ogg) and os.path.getsize(ogg) >= 1000:
                reply_to_id = getattr(event, "message", None)
                reply_id = reply_to_id.id if reply_to_id else getattr(event, "id", None)
                vmsg = await client.send_file(event.chat_id, ogg, voice_note=True, reply_to=reply_id)
                register_self_sent(vmsg, default_chat_id=event.chat_id)
                _safe_unlink(mp3)
                _safe_unlink(ogg)
                if status:
                    try:
                        await status.delete()
                    except Exception:
                        pass
                if not is_tainted:
                    memory.remember_exchange(scope_id, question, voice_text)
                    asyncio.create_task(_trigger_learn(question, voice_text, scope_id, event.chat_id))
                return

        await _stage(status, "📝 دارم جواب می‌دم...")
        lp = not is_tainted
        if _is_long_or_code(answer):
            await _send_as_md(event, status, answer)
        else:
            await _safe_edit_or_send(event, status, answer, link_preview=lp)
        if not is_tainted:
            memory.remember_exchange(scope_id, question, answer)
            asyncio.create_task(_trigger_learn(question, answer, scope_id, event.chat_id))
    except Exception as e:
        log.error("Error in on_outgoing: %s", type(e).__name__, exc_info=True)
        try:
            msg = "❌ خطایی در پردازش رخ داد؛ لطفاً مجدداً تلاش کنید."
            if status is not None:
                await status.edit(msg)
            else:
                await event.reply(msg)
        except Exception:
            pass


_stranger_hits = {}
_stranger_daily = {}
_global_daily = []

STRANGER_DAILY_LIMIT = 50        # سقف روزانه‌ی درخواست هر غریبه
STRANGER_GLOBAL_DAILY_LIMIT = 300  # سقف روزانه‌ی مجموع درخواست‌های همه غریبه‌ها

# نگه‌داری زمان آخرین درخواست هر غریبه جهت اعمال کول‌داون قطعی ۱ دقیقه‌ای
_stranger_last_request = {}
_stranger_cooldown_warned = {}
NON_OWNER_COOLDOWN_SECONDS = 60  # فاصله الزامی ۱ دقیقه (۶۰ ثانیه) بین هر درخواست برای سایر کاربران

_URL_REGEX = re.compile(
    r"(https?://\S+|www\.\S+|t\.me/\S+|telegram\.me/\S+|[a-zA-Z0-9-]+\.(com|org|net|ir|io|me|info|co|xyz|dev|app|ai|ru|cn|gg)/?\S*)",
    re.IGNORECASE
)


def _message_has_file_or_media(msg) -> bool:
    """تشخیص وجود هرگونه فایل، داکیومنت، مدیا، عکس، ویدیو، صدا یا ویس در پیام."""
    if not msg:
        return False
    if getattr(msg, "file", None) or getattr(msg, "photo", None) or getattr(msg, "video", None):
        return True
    if getattr(msg, "document", None) or getattr(msg, "voice", None) or getattr(msg, "audio", None):
        return True
    m = getattr(msg, "media", None)
    if m:
        cname = type(m).__name__
        if any(k in cname for k in ("Photo", "Document", "Audio", "Video", "Voice")):
            return True
    return False


def _prune_stranger_state() -> None:
    """حذف کلیدهای غریبه‌هایی که بیش از ۲۴ ساعت بی‌فعالیت بوده‌اند (جلوگیری از رشد نامحدود دیکشنری‌ها)."""
    if len(_stranger_daily) <= 500:
        return
    now = time.time()
    stale = [u for u, ts in _stranger_daily.items() if not ts or now - ts[-1] > 86400]
    for u in stale:
        _stranger_daily.pop(u, None)
        _stranger_hits.pop(u, None)
        _stranger_last_request.pop(u, None)
        _stranger_cooldown_warned.pop(u, None)


def _stranger_rate_ok(uid, limit: int = 6, window: int = 60) -> bool:
    """محدودیت نرخ برای غریبه‌ها: سقف دقیقه‌ای + سقف روزانه‌ی هر نفر + سقف سراسری روزانه."""
    global _global_daily
    now = time.time()

    hits = [t for t in _stranger_hits.get(uid, []) if now - t < window]
    if len(hits) >= limit:
        _stranger_hits[uid] = hits
        return False

    daily = [t for t in _stranger_daily.get(uid, []) if now - t < 86400]
    if len(daily) >= STRANGER_DAILY_LIMIT:
        _stranger_daily[uid] = daily
        return False

    global_daily = [t for t in _global_daily if now - t < 86400]
    if len(global_daily) >= STRANGER_GLOBAL_DAILY_LIMIT:
        _global_daily = global_daily
        return False

    hits.append(now)
    daily.append(now)
    global_daily.append(now)
    _stranger_hits[uid] = hits
    _stranger_daily[uid] = daily
    _global_daily = global_daily
    _prune_stranger_state()
    return True

@client.on(events.NewMessage(incoming=True))
async def on_incoming_pm(event):
    # ۱. گارد بات‌ها: بات‌ها (sender.bot) هرگز مجاز نیستند حتی اگر در لیست باشند
    sender = await event.get_sender()
    if sender is None or getattr(sender, "bot", False):
        return

    # بلاک فورواردها و پیام‌های ارسال‌شده از طریق ربات‌ها (جلوگیری از اجرای متن غریبه با دسترسی کاربر مجاز)
    if getattr(event, "fwd_from", None) or getattr(event.message, "fwd_from", None):
        return
    if getattr(event, "via_bot_id", None) or getattr(event.message, "via_bot_id", None) or getattr(event, "via_bot", None) or getattr(event.message, "via_bot", None):
        return

    # ۲. اولین چک: هر فرستنده غیر از مالک که در لیست مجوز نباشد، هیچ پاسخی نگیرد (return ساده و بی‌صدا)
    uid = event.sender_id
    if not access.is_allowed(uid) or access.is_denied(uid):
        return

    text = event.raw_text or ""

    # حالت سرشلوغ (DND): برای مخاطبان مجاز در پیوی و تگ‌های گروه
    if dnd.is_dnd_active() and not getattr(event, "out", False):
        if event.is_private:
            if await dnd.handle_incoming_pv(event, client):
                return
        elif event.is_group:
            if await dnd.handle_incoming_group_mention(event, client):
                return

    # حالت همزاد: برای مخاطبان مجاز در پیوی
    if ghost.is_active() and event.is_private and not has_trigger(text):
        if await ghost.reply_as_owner(event, client):
            return

    if not has_trigger(text):
        return

    # بررسی سقف کلی و روزانه کاربران مجاز
    if not _stranger_rate_ok(uid):
        return

    # اعمال کول‌داون ۳۰ ثانیه‌ای بین هر درخواست برای کاربران مجاز
    ALLOWED_USER_COOLDOWN_SECONDS = 30
    now = time.time()
    last_req = _stranger_last_request.get(uid, 0)
    elapsed = now - last_req
    if elapsed < ALLOWED_USER_COOLDOWN_SECONDS:
        rem = int(ALLOWED_USER_COOLDOWN_SECONDS - elapsed) + 1
        warns = _stranger_cooldown_warned.get(uid, 0)
        if warns == 0:
            _stranger_cooldown_warned[uid] = 1
            s_name = (getattr(sender, "first_name", "") or "مخاطب").strip()
            await event.reply(
                f"⏳ {s_name} عزیز، جهت جلوگیری از اسپم، بین هر درخواست باید حداقل ۳۰ ثانیه فاصله باشد.\n"
                f"لطفاً {rem} ثانیه دیگر صبور باشید. 😉"
            )
        return

    question = strip_trigger(text)
    if not question:
        await event.reply("سلام! بهم بگو چه کاری برات انجام بدم.")
        return

    s_name = (getattr(sender, "first_name", "") or "مخاطب").strip()

    # مسدودسازی دستورات ادمینی و بن/کیک اعضای گروه
    if any(w in question for w in ("بن کن", "بلاک کن", "بنداز بیرون", "حذف کن از گروه", "کیک کن", "از گروه حذف", "اخراج کن")):
        await event.reply(
            f"🚫 {s_name} عزیز، کاپری دستیار شخصی (یوزربات) است و دسترسی مدیریت اعضای گروه یا بن/اخراج افراد را ندارد. این امور مربوط به مدیران خودِ گروه است. 😉"
        )
        return

    # افراد متفرقه حق تغییر مدل، تنظیمات یا دستکاری حافظه/قوانین، یادآورها، یا کانال‌ها را ندارند
    SENSITIVE_NON_OWNER_WORDS = (
        "یادت باشه", "فراموش کن", "قانون ذخیره کن", "قانون جدید", "قانون رو ذخیره",
        "یادآور", "یادآوری", "ریمایندر", "آلارم", "لفت بده", "لفت بزن", "کانال",
        "پوشه", "مرتب کن", "خلاصه امروز", "بریفینگ", "پاسپورت", "passport"
    )
    if any(w in question for w in SENSITIVE_NON_OWNER_WORDS) or models.parse_request(question) or parse_voice_command(question):
        await event.reply(f"🔒 {s_name} عزیز، تنظیمات، یادآورها، مدیریت کانال‌ها و قابلیت‌های محرمانه فقط توسط صاحب اکانت قابل استفاده است. 😉")
        return

    # ثبت تایم‌استمپ این درخواست موفق و ریست اخطار کول‌داون
    _stranger_last_request[uid] = time.time()
    _stranger_cooldown_warned[uid] = 0

    status = None
    try:
        status = await event.reply("🧠 در حال جمع‌آوری اطلاعات...")
        register_self_sent(status, default_chat_id=event.chat_id)

        context = await get_context(event)
        mem = ""  # حافظه‌ی صاحب اکانت به دیگران نشان داده نمی‌شود

        # استخراج و غنی‌سازی متن ریپلای برای کاربران مجاز در صورت درخواست خلاصه‌سازی
        reply_info = await get_reply_info(event, client)
        if _is_summary_request(question) and reply_info and reply_info.get("has_reply") and reply_info.get("text"):
            r_author = reply_info.get("author_name") or "کاربر"
            question = f"لطفاً متن پیام زیر از {r_author} را با دقت و شیوایی به زبان فارسی خلاصه کن:\n\n«{reply_info['text']}»"

        await _stage(status, "🤔 دارم فکر می‌کنم...")
        answer = await agent.run_agent(question, context, mem, event, client, status, is_owner=False, sender_name=s_name)

        if answer.startswith("__VOICE_SENT__:") or answer.startswith("__DRAFT_SENT__:") or answer in ("__ROAST_SENT__", "__MEME_SENT__"):
            return

        wants_voice = any(w in question for w in VOICE_WORDS) and any(w in question for w in ACTION_WORDS)
        if wants_voice and answer:
            voice_text = _clean_voice_text(answer)
            ts = int(time.time() * 1000)
            mp3 = os.path.join(config.DOWNLOAD_DIR, f"tts_{ts}.mp3")
            ogg = os.path.join(config.DOWNLOAD_DIR, f"tts_{ts}.ogg")
            ok = await voice.speak(voice_text, mp3, client=client)
            converted = await asyncio.to_thread(voice.to_ogg, mp3, ogg) if ok else False
            if not ok or not converted or not os.path.exists(ogg) or os.path.getsize(ogg) < 1000:
                try:
                    import edge_tts
                    clean_fb = voice.prepare_for_tts(voice_text)
                    c = edge_tts.Communicate(clean_fb, "fa-IR-FaridNeural", rate="+5%")
                    await c.save(mp3)
                    converted = await asyncio.to_thread(voice.to_ogg, mp3, ogg)
                    ok = converted and os.path.exists(ogg) and os.path.getsize(ogg) >= 1000
                except Exception:
                    ok = False

            if ok and os.path.exists(ogg) and os.path.getsize(ogg) >= 1000:
                reply_to_id = getattr(event, "message", None)
                reply_id = reply_to_id.id if reply_to_id else getattr(event, "id", None)
                vmsg = await client.send_file(event.chat_id, ogg, voice_note=True, reply_to=reply_id)
                register_self_sent(vmsg, default_chat_id=event.chat_id)
                _safe_unlink(mp3)
                _safe_unlink(ogg)
                if status:
                    try:
                        await status.delete()
                    except Exception:
                        pass
                return

        await _stage(status, "📝 دارم جواب می‌دم...")
        is_tainted = agent.get_last_run_tainted()
        lp = not is_tainted
        if _is_long_or_code(answer):
            await _send_as_md(event, status, answer)
        else:
            await _safe_edit_or_send(event, status, answer, link_preview=lp)
    except Exception as e:
        log.error("Error in on_incoming_pm: %s", type(e).__name__, exc_info=True)
        try:
            msg = "❌ خطایی در پردازش رخ داد؛ لطفاً مجدداً تلاش کنید."
            if status is not None:
                await status.edit(msg)
            else:
                await event.reply(msg)
        except Exception:
            pass


@client.on(events.Raw((types.UpdateMessageReactions, types.UpdateEditMessage, types.UpdateEditChannelMessage)))
async def on_raw_reaction(update):
    try:
        await reactions.handle_reaction_update(client, update)
    except Exception as e:
        log.error("Error in on_raw_reaction: %s", type(e).__name__, exc_info=True)


async def main():
    config.validate()
    await client.start()
    asyncio.create_task(_purge_downloads_loop())
    asyncio.create_task(dnd.start_scheduler_loop(client))
    await asyncio.to_thread(_purge_downloads)
    me = await client.get_me()
    reactions.set_owner_id(me.id)
    memory.set_owner_id(me.id)
    global _owner_id
    _owner_id = me.id
    print(f"[+] Capri v{config.VERSION} - Successfully logged in as: {me.first_name} (@{me.username})", flush=True)
    print(f"[*] Assistant name: '{config.ASSISTANT_NAME}'", flush=True)
    print(f"[*] Capri is listening. Trigger keyword: '{config.ASSISTANT_NAMES[0]}'", flush=True)
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
