# -*- coding: utf-8 -*-
"""دانلود ویدیو/پست/آهنگ از شبکه‌های اجتماعی (تیک‌تاک، اینستاگرام، پینترست، توییتر/ایکس، ساوندکلاد)
از طریق ربات دانلود تلگرام و فوروارد مستقیم فایل به چت کاربر."""
import asyncio
import logging
import re

from telethon import types

from core import config
from services.media import fetch

log = logging.getLogger("socialdl")

MAX_STEPS = 20
POLL_SECONDS = 2.0

CONFIRM_HINTS = ("تایید", "تأیید", "بررسی", "عضویت", "عضو شدم", "چک", "check", "confirm", "✅", "شدم", "دریافت")

PLATFORM_RE = re.compile(
    r"(?:tiktok\.com|vm\.tiktok\.com|instagram\.com|instagr\.am|pin\.it|pinterest\.com|"
    r"x\.com|twitter\.com|soundcloud\.com)",
    re.IGNORECASE,
)

URL_RE = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)


def extract_social_url(text: str):
    """اولین لینک مربوط به پلتفرم‌های پشتیبانی‌شده را از متن برمی‌گرداند (یا None)."""
    if not text:
        return None
    for m in URL_RE.finditer(text):
        u = m.group(0).rstrip(".,;!?()[]{}\u200c")
        if PLATFORM_RE.search(u):
            return u
    return None


def is_social_link(text: str) -> bool:
    return extract_social_url(text) is not None


async def download_social(client, url: str, event=None, status=None) -> str:
    """لینک را به ربات دانلود می‌فرستد، فایل رسیده را در چت فوروارد می‌کند و نتیجه را برمی‌گرداند."""
    clean = (url or "").strip()
    if not clean:
        return "❌ لینکی برای دانلود ارسال نشده است."
    if not PLATFORM_RE.search(clean):
        return "❌ این لینک مربوط به تیک‌تاک/اینستاگرام/پینترست/توییتر/ساوندکلاد نیست."

    bot_name = config.SOCIAL_DL_BOT or "@MooNDLBoT"
    try:
        bot = await client.get_entity(bot_name)
    except Exception as e:
        log.warning("Could not resolve downloader bot %s: %s", bot_name, e)
        return f"❌ ربات دانلود «{bot_name}» در دسترس نیست."

    try:
        sent = await client.send_message(bot, clean)
    except Exception as e:
        log.warning("Could not send link to %s: %s", bot_name, e)
        return f"❌ خطا در ارسال لینک به ربات دانلود: {e}"

    base = sent.id
    joined = []

    if status:
        try:
            await status.edit(f"⬇️ لینک به {bot_name} ارسال شد؛ در حال دریافت فایل...")
        except Exception:
            pass

    for _ in range(MAX_STEPS):
        await asyncio.sleep(POLL_SECONDS)
        try:
            msgs = await client.get_messages(bot, limit=15)
        except Exception:
            continue

        for m in msgs:
            if m.out or m.id <= base:
                continue

            # قفل اسپانسر / عضویت اجباری
            if m.buttons and fetch._is_sponsor(m):
                flat = [b for row in m.buttons for b in row]
                for b in flat:
                    if b.url and fetch._is_invite_url(b.url):
                        ch = await fetch._join(client, b.url)
                        if ch is not None and not any(getattr(c, "id", None) == ch.id for c in joined):
                            joined.append(ch)
                        await asyncio.sleep(1.0)
                confirm = next((b for b in flat if b.data and any(h in (b.text or "").lower() for h in CONFIRM_HINTS)), None)
                if confirm:
                    try:
                        await m.click(data=confirm.data)
                    except Exception:
                        pass
                    await asyncio.sleep(2.0)
                continue

            if isinstance(m.media, (types.MessageMediaDocument, types.MessageMediaPhoto)):
                if status:
                    try:
                        await status.edit("📥 فایل دریافت شد؛ در حال ارسال به شما...")
                    except Exception:
                        pass
                try:
                    await client.forward_messages(event.chat_id, m)
                except Exception as e:
                    for ch in joined:
                        await fetch._leave(client, ch)
                    return f"❌ خطا در ارسال تلگرام: فایل با موفقیت دریافت شد اما فوروارد آن به چت با خطا مواجه شد ({e})."
                for ch in joined:
                    await fetch._leave(client, ch)
                return "✅ دانلود شد و فایل در چت ارسال شد. 👆"

    for ch in joined:
        await fetch._leave(client, ch)
    return "❌ خطا در دانلود: ربات دانلود در زمان مقرر پاسخی نداد. دوباره تلاش کن یا لینک را مستقیم در همان ربات امتحان کن."
