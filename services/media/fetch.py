import asyncio
import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple, Union

from telethon import functions, types
from telethon.tl.functions.channels import JoinChannelRequest, LeaveChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest

from core import config

log = logging.getLogger("fetch")

# لینک ربات با deep-link: t.me/SomeBot?start=TOKEN
BOT_START_RE = re.compile(r"t\.me/([A-Za-z0-9_]+)\?start=([A-Za-z0-9_\-]+)")

SPONSOR_HINTS = ("عضو", "عضویت", "کانال", "جوین", "سبسکرایب", "subscribe", "join")
CONFIRM_HINTS = ("تایید", "تأیید", "بررسی", "عضویت", "عضو شدم", "چک", "check", "confirm", "✅", "شدم", "دریافت")
DOWNLOAD_HINTS = ("دانلود", "دریافت", "download", "لینک")
SUBSCRIPTION_HINTS = (
    "اشتراک", "تهیه اشتراک", "خرید اشتراک", "تمدید اشتراک", "نیاز به تهیه اشتراک",
    "پرداخت", "تومان", "قیمت", "پولی", "پریمیوم", "premium", "کارت به کارت",
    "مبلغ", "سکه", "خرید پنل", "vip", "وی آی پی", "ویژه", "خرید پلن"
)

# «اشتراک‌گذاری» (دکمه‌ی share) نباید با «اشتراک» (پولی) اشتباه بشه
_SHARE_RE = re.compile(r"اشتراک[\u200c\s]*گذاری")

PAID_BOTS_FILE = os.path.join(config.BASE_DIR, "paid_bots.json")


def load_paid_bots() -> set:
    """لیست ربات‌های اشتراکی و پولی تلگرام که نباید به سمتشون رفت."""
    if os.path.exists(PAID_BOTS_FILE):
        try:
            with open(PAID_BOTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return set(b.lower().strip("@") for b in data)
        except Exception:
            pass
    return {"m00n_movie_bot", "moon_movie_bot"}


def mark_paid_bot(bot_name: str) -> None:
    """ثبت فوری یک ربات به عنوان ربات پولی در حافظه پایدار."""
    if not bot_name:
        return
    b = bot_name.lower().strip("@")
    bots = load_paid_bots()
    if b not in bots:
        bots.add(b)
        try:
            from core import fsutil
            fsutil.atomic_write_json(PAID_BOTS_FILE, sorted(list(bots)))
        except Exception:
            pass


def is_paid_bot(bot_name: str) -> bool:
    """بررسی اینکه آیا ربات مورد نظر اشتراکی/پولی است یا خیر."""
    if not bot_name:
        return False
    b = bot_name.lower().strip("@")
    return b in load_paid_bots()


def _is_subscription(text: str) -> bool:
    if not text:
        return False
    t = _SHARE_RE.sub("", text).lower()
    return any(h in t for h in SUBSCRIPTION_HINTS)

MOVIE_CHANNEL_HINTS = ("فیلم", "مووی", "movie", "film", "سریال", "سینما", "انیمه", "انیمیشن", "مانگا", "manga")

MAX_STEPS = 14
FILE_IDLE_SECONDS = 8

QUALITY_SET = {360, 480, 720, 1080, 1440, 2160, 4320}
QUALITY_RE = re.compile(r"(?:با|به|در)?\s*کیفیت\s*[:\s،]*(\d{3,4})")
STANDALONE_P_RE = re.compile(r"\b(\d{3,4})p\b")


def extract_quality(text: str):
    """کیفیت درخواستی (مثل 1080) رو از متن بیرون می‌کشه و متن رو تمیز می‌کنه."""
    m = QUALITY_RE.search(text)
    if not m:
        m = STANDALONE_P_RE.search(text)
    q = None
    cleaned = text
    if m:
        n = int(m.group(1))
        if n in QUALITY_SET:
            q = n
            cleaned = text[:m.start()] + " " + text[m.end():]
    cleaned = " ".join(cleaned.split()).strip("،,:.؟? ")
    return q, cleaned


def _label_quality(label: str):
    """کیفیت یه لیبل/دکمه مثل «1080p x265» یا «480» رو برمی‌گردونه."""
    if not label:
        return None
    mm = re.search(r"(\d{3,4})", label)
    if not mm:
        return None
    n = int(mm.group(1))
    return n if n in QUALITY_SET else None


def _extract_audio_type(text: str) -> Optional[str]:
    """تشخیص نوع صوت یا زیرنویس از روی متن دکمه."""
    t = (text or "").lower()
    if any(k in t for k in ("دوبله", "دوبله فارسی", "صوت دوبله", "دوبلاژ", "dubbed", "fa dub", "fa_dub")):
        return "dubbed"
    if any(k in t for k in ("زیرنویس", "زیرنویس چسبیده", "softsub", "hardsub", "sub", "subbed", "farsisub")):
        return "subtitled"
    return None


def _norm(s: str) -> str:
    for ch in ".:_-/":
        s = s.replace(ch, " ")
    return " ".join(s.lower().split())


def _entity_text(text: str, offset: int, length: int) -> str:
    """متنِ یک entity؛ آفست تلگرام بر حسب UTF-16 هست نه کاراکتر پایتون."""
    try:
        return text.encode("utf-16-le")[offset * 2:(offset + length) * 2].decode("utf-16-le")
    except Exception:
        return ""


def _bot_links(m):
    """لینک‌های ربات (bot, token, label) توی پیام؛ از لینک‌های‌پرمتن، متن خام و دکمه‌ها."""
    text = m.message or ""
    out = []
    for e in (m.entities or []):
        url = getattr(e, "url", None)
        if not url:
            continue
        mm = BOT_START_RE.search(url)
        if mm:
            bot = mm.group(1)
            if not is_paid_bot(bot):
                label = _entity_text(text, getattr(e, "offset", 0), getattr(e, "length", 0))
                out.append((bot, mm.group(2), label))
    for mm in BOT_START_RE.finditer(text):
        bot = mm.group(1)
        if not is_paid_bot(bot):
            out.append((bot, mm.group(2), ""))
    if m.buttons:
        for row in m.buttons:
            for b in row:
                if b.url:
                    mm = BOT_START_RE.search(b.url)
                    if mm:
                        bot = mm.group(1)
                        if not is_paid_bot(bot):
                            out.append((bot, mm.group(2), b.text or ""))
    return out


async def _search_links(client, query: str, limit: int = 50, quality=None):
    """جستجوی سراسری برای پست‌هایی که لینک ربات دانلود دارن."""
    res = await client(functions.messages.SearchGlobalRequest(
        q=query, filter=types.InputMessagesFilterEmpty(),
        min_date=None, max_date=None, offset_rate=0,
        offset_peer=types.InputPeerEmpty(), offset_id=0, limit=limit))
    qn = _norm(query)
    links = []
    seen = set()
    for m in res.messages:
        if m.out or not getattr(m.peer_id, "channel_id", None):
            continue
        mtext_norm = _norm(m.message or "")
        for bot, token, label in _bot_links(m):
            key = (bot.lower(), token)
            if key in seen:
                continue
            seen.add(key)
            ln = _norm(label)
            score = 0
            if quality and _label_quality(label) == quality:
                score = 1100
            if qn and ln and qn in ln:
                score = max(score, 200)
            elif qn and mtext_norm and qn in mtext_norm:
                score = max(score, 100)
            elif qn and mtext_norm and any(w in mtext_norm for w in qn.split() if len(w) >= 4):
                score = max(score, 40)
            if score:
                links.append((score, bot, token))
    links.sort(key=lambda x: -x[0])
    return [(b, t) for _, b, t in links]


async def _search_channels(client, query: str, limit: int = 4, quality=None):
    """پشتیبان: جستجو توی کانال‌هایی که اسمشون شبیه فیلم/سریاله."""
    qn = _norm(query)
    links = []
    seen = set()
    async for d in client.iter_dialogs():
        if not d.is_channel:
            continue
        if not any(h in (d.name or "").lower() for h in MOVIE_CHANNEL_HINTS):
            continue
        try:
            posts = await client.get_messages(d.entity, search=query, limit=limit)
        except Exception:
            continue
        for m in posts:
            if m.out:
                continue
            mtext_norm = _norm(m.message or "")
            for bot, token, label in _bot_links(m):
                key = (bot.lower(), token)
                if key in seen:
                    continue
                seen.add(key)
                ln = _norm(label)
                score = 200 if (qn and ln and qn in ln) else (100 if (qn and qn in mtext_norm) else 40)
                if quality and _label_quality(label) == quality:
                    score = max(score, 1100)
                if score:
                    links.append((score, bot, token))
        await asyncio.sleep(0.3)
    links.sort(key=lambda x: -x[0])
    return [(b, t) for _, b, t in links]


def _is_invite_url(url: str) -> bool:
    if not url or "t.me/" not in url:
        return False
    if BOT_START_RE.search(url):
        return False
    return True


def _is_sponsor(m) -> bool:
    text = (m.message or "").lower()
    if not any(h in text for h in SPONSOR_HINTS):
        return False
    return any(_is_invite_url(b.url) for row in (m.buttons or []) for b in row)


def _pick_quality(buttons, requested=None):
    def num(b):
        return _label_quality(b.text or "") or 0
    if requested:
        for b in buttons:
            if _label_quality(b.text or "") == requested:
                return b
    return max(buttons, key=num)


async def _join(client, url: str):
    """عضو شدن توی کانال دعوت. موجودیت کانال رو برمی‌گردونه (برای لفت بعدی) یا None."""
    if not url:
        return None
    m = re.search(r"t\.me/(?:joinchat/|\+|)([A-Za-z0-9_\-]+)", url)
    if not m:
        return None
    slug = m.group(1)
    is_invite = "joinchat/" in url or ("+" + slug) in url
    try:
        if is_invite:
            res = await client(ImportChatInviteRequest(slug))
            if hasattr(res, "chats") and res.chats:
                return res.chats[0]
        else:
            await client(JoinChannelRequest(slug))
            return await client.get_entity(slug)
    except Exception:
        return None


async def _leave(client, channel) -> None:
    try:
        await client(LeaveChannelRequest(channel))
    except Exception:
        pass


PERSIAN_NUMS = {'۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4', '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9'}
ORDINALS = {
    'اول': 1, 'یکم': 1, 'دوم': 2, 'سوم': 3, 'چهارم': 4, 'پنجم': 5,
    'ششم': 6, 'هفتم': 7, 'هشتم': 8, 'نهم': 9, 'دهم': 10,
    'یازدهم': 11, 'دوازدهم': 12, 'سیزدهم': 13, 'چهاردهم': 14, 'پانزدهم': 15
}


def _extract_season_num(text: str):
    if not text:
        return None
    t = text
    for p, a in PERSIAN_NUMS.items():
        t = t.replace(p, a)
    t = t.lower()
    m = re.search(r"(?:فصل|season|s)\s*0?(\d{1,2})", t)
    if m:
        return int(m.group(1))
    for word, num in ORDINALS.items():
        if f"فصل {word}" in t or f"فصل{word}" in t:
            return num
    return None


def _extract_episode_num(text: str):
    if not text:
        return None
    t = text
    for p, a in PERSIAN_NUMS.items():
        t = t.replace(p, a)
    t = t.lower()
    m = re.search(r"(?:قسمت|episode|ep|e)\s*0?(\d{1,3})", t)
    if m:
        return int(m.group(1))
    return None


async def follow_bot(
    client,
    bot_name: str,
    token: str,
    joined: list,
    depth: int = 0,
    quality=None,
    audio=None,
    season=None,
    episode=None,
    event=None,
    status=None,
):
    """دنبال کردن یه ربات دانلود تا رسیدن همه‌ی فایل‌ها، همراه با انتخاب فصل، کیفیت،
    پیمایش ربات‌های ورق‌زن (آیتم 1/X) و فوروارد درجا به محض رسیدن هر فایل.

    برمی‌گردونه (files, status):
      - status=None یعنی موفق (files ممکنه خالی باشه)
      - status="subscription" یعنی ربات اشتراک پولی می‌خواد
      - status=<پیام خطا>
    """
    if depth > 3:
        return [], "زنجیره‌ی ربات‌ها خیلی طولانی شد."
    if is_paid_bot(bot_name):
        return [], "subscription"
    try:
        bot = await client.get_entity(bot_name)
    except Exception as e:
        return [], f"ربات @{bot_name} پیدا نشد: {e}"

    sent = await client.send_message(bot, f"/start {token}" if token else "/start")
    base = sent.id
    await asyncio.sleep(2.5)

    clicked = set()
    files = {}
    forwarded_ids = set()

    async def forward_stream(doc):
        if event and getattr(event, "chat_id", None) and doc.id not in forwarded_ids:
            forwarded_ids.add(doc.id)
            try:
                await client.forward_messages(event.chat_id, doc)
            except Exception:
                pass

    for _ in range(MAX_STEPS):
        msgs = await client.get_messages(bot, limit=20)

        # ۲. بررسی تمام پیام‌های جدید از نظر اشتراک پولی (چه متنی، چه با دکمه)
        for m in msgs:
            if m.out or m.id <= base:
                continue
            m_full_text = m.message or ""
            if m.buttons:
                m_full_text += " " + " ".join(b.text or "" for row in m.buttons for b in row)
            if _is_subscription(m_full_text):
                mark_paid_bot(bot_name)
                return sorted(files.values(), key=lambda x: x.id), "subscription"

        # جمع‌آوری همه‌ی فایل‌های جدید و فوروارد فوری
        for m in msgs:
            if m.out or m.id <= base or not isinstance(m.media, types.MessageMediaDocument):
                continue
            if m.id not in files:
                files[m.id] = m
                await forward_stream(m)

        act = next((m for m in msgs if not m.out and m.buttons), None)
        if act is None:
            if files:
                # اگر فایلی دریافت شده و دکمه‌ای نیست، کمی صبر کن تا آخرین فایل‌ها هم برسند
                await asyncio.sleep(2.0)
                latest_msgs = await client.get_messages(bot, limit=10)
                for lm in latest_msgs:
                    if not lm.out and lm.id > base and isinstance(lm.media, types.MessageMediaDocument):
                        if lm.id not in files:
                            files[lm.id] = lm
                            await forward_stream(lm)
                return sorted(files.values(), key=lambda x: x.id), None
            await asyncio.sleep(2)
            continue

        buttons = [b for row in act.buttons for b in row]

        # 1) اسپانسر: عضو شدن توی کانال + تایید
        if _is_sponsor(act):
            for b in buttons:
                if _is_invite_url(b.url):
                    ch = await _join(client, b.url)
                    if ch is not None and not any(getattr(c, "id", None) == ch.id for c in joined):
                        joined.append(ch)
                    await asyncio.sleep(1.0)
            confirm = next((b for b in buttons
                            if b.data and b.data not in clicked
                            and any(h in (b.text or "").lower() for h in CONFIRM_HINTS)), None)
            if confirm:
                await act.click(data=confirm.data)
                clicked.add(confirm.data)
                await asyncio.sleep(2.5)
                continue

        # 2) اشتراک پولی؟ بیخیال شو
        all_text = ((act.message or "") + " " + " ".join(b.text or "" for b in buttons)).lower()
        if _is_subscription(all_text):
            return sorted(files.values(), key=lambda x: x.id), "subscription"

        # 3) لینک کیفیت / ربات بعدی
        url_links = [b for b in buttons if b.url and BOT_START_RE.search(b.url)]
        if url_links:
            best = _pick_quality(url_links, quality)
            mm = BOT_START_RE.search(best.url)
            return await follow_bot(
                client, mm.group(1), mm.group(2), joined, depth + 1,
                quality=quality, audio=audio, season=season, episode=episode,
                event=event, status=status
            )

        # 4) ربات‌های ورق‌زن / آیتم‌دار (مثل AloFilmBot با آیتم 1/6 و دکمه‌های بعدی و دریافت فایل)
        act_text = act.message or ""
        for p, a in PERSIAN_NUMS.items():
            act_text = act_text.replace(p, a)
        m_item = re.search(r'(?:آیتم|item)\s*(\d+)\s*/\s*(\d+)', act_text, re.IGNORECASE)
        dl_btn = next((b for b in buttons if b.data and any(h in (b.text or "").lower() for h in ("دریافت فایل", "دریافت", "دانلود", "download"))), None)
        next_btn = next((b for b in buttons if b.data and any(h in (b.text or "").lower() for h in ("بعدی", "next", "⏭"))), None)

        if m_item and dl_btn:
            cur_item = int(m_item.group(1))
            total_items = int(m_item.group(2))

            target_ep = int(episode) if isinstance(episode, (int, str)) and str(episode).isdigit() else None

            # اگر کاربر فقط یک قسمت خاص را خواسته
            if target_ep is not None:
                while cur_item < target_ep and next_btn:
                    if status:
                        try:
                            await status.edit(f"🎬 در حال رفتن به قسمت {target_ep} (آیتم {cur_item}/{total_items})...")
                        except Exception:
                            pass
                    await act.click(data=next_btn.data)
                    await asyncio.sleep(1.4)
                    upd_msgs = await client.get_messages(bot, limit=5)
                    act = next((m for m in upd_msgs if not m.out and m.buttons), act)
                    buttons = [b for row in act.buttons for b in row]
                    act_text = act.message or ""
                    for p, a in PERSIAN_NUMS.items():
                        act_text = act_text.replace(p, a)
                    m_item = re.search(r'(?:آیتم|item)\s*(\d+)\s*/\s*(\d+)', act_text, re.IGNORECASE)
                    cur_item = int(m_item.group(1)) if m_item else cur_item + 1
                    dl_btn = next((b for b in buttons if b.data and any(h in (b.text or "").lower() for h in ("دریافت فایل", "دریافت", "دانلود", "download"))), dl_btn)
                    next_btn = next((b for b in buttons if b.data and any(h in (b.text or "").lower() for h in ("بعدی", "next", "⏭"))), None)

                if status:
                    try:
                        await status.edit(f"🎬 در حال دریافت قسمت {target_ep}...")
                    except Exception:
                        pass
                if dl_btn:
                    await act.click(data=dl_btn.data)
                    for _ in range(6):
                        await asyncio.sleep(1.0)
                        latest = await client.get_messages(bot, limit=10)
                        for lm in latest:
                            if not lm.out and lm.id > base and isinstance(lm.media, types.MessageMediaDocument):
                                if lm.id not in files:
                                    files[lm.id] = lm
                                    await forward_stream(lm)
                        if files:
                            break
                return sorted(files.values(), key=lambda x: x.id), None

            # کاربر کل فصل یا همه قسمت‌ها را خواسته است (دریافت و فوروارد درجا)
            for item_num in range(cur_item, total_items + 1):
                if status:
                    try:
                        await status.edit(f"🎬 در حال دریافت و ارسال قسمت {item_num} از {total_items}...")
                    except Exception:
                        pass

                # کلیک دریافت فایل
                if dl_btn:
                    await act.click(data=dl_btn.data)

                # انتظار برای رسیدن فایل و فوروارد درجا
                got_new = False
                for _ in range(7):
                    await asyncio.sleep(1.0)
                    latest = await client.get_messages(bot, limit=10)
                    for lm in latest:
                        if not lm.out and lm.id > base and isinstance(lm.media, types.MessageMediaDocument):
                            if lm.id not in files:
                                files[lm.id] = lm
                                await forward_stream(lm)
                                got_new = True
                    if got_new:
                        break

                if status:
                    try:
                        await status.edit(f"📤 قسمت {item_num} از {total_items} فوروارد شد 👆")
                    except Exception:
                        pass

                # ورق زدن به قسمت بعدی
                if item_num < total_items:
                    upd_msgs = await client.get_messages(bot, limit=5)
                    act = next((m for m in upd_msgs if not m.out and m.buttons), act)
                    buttons = [b for row in act.buttons for b in row]
                    next_btn = next((b for b in buttons if b.data and any(h in (b.text or "").lower() for h in ("بعدی", "next", "⏭"))), None)
                    if next_btn:
                        await act.click(data=next_btn.data)
                        await asyncio.sleep(1.3)
                        upd_msgs = await client.get_messages(bot, limit=5)
                        act = next((m for m in upd_msgs if not m.out and m.buttons), act)
                        buttons = [b for row in act.buttons for b in row]
                        dl_btn = next((b for b in buttons if b.data and any(h in (b.text or "").lower() for h in ("دریافت فایل", "دریافت", "دانلود", "download"))), dl_btn)
                    else:
                        break

            return sorted(files.values(), key=lambda x: x.id), None

        # 5) انتخاب فصل در صورت وجود منوی فصل‌ها
        season_buttons = {}
        for b in buttons:
            if b.data and b.data not in clicked:
                s_n = _extract_season_num(b.text or "")
                if s_n is not None:
                    season_buttons[s_n] = b

        if season_buttons:
            target_s = int(season) if isinstance(season, (int, str)) and str(season).isdigit() else None
            chosen_s_btn = None
            if target_s is not None and target_s in season_buttons:
                chosen_s_btn = season_buttons[target_s]
            elif season_buttons:
                chosen_s_btn = season_buttons[sorted(season_buttons.keys())[0]]

            if chosen_s_btn:
                if status:
                    try:
                        await status.edit(f"🎬 در حال انتخاب فصل {target_s or 'مورد نظر'}...")
                    except Exception:
                        pass
                await act.click(data=chosen_s_btn.data)
                clicked.add(chosen_s_btn.data)
                await asyncio.sleep(2.5)
                continue

        # 5.5) انتخاب صوت / زیرنویس (دوبله یا زیرنویس)
        audio_buttons = {}
        for b in buttons:
            if b.data and b.data not in clicked:
                a_type = _extract_audio_type(b.text or "")
                if a_type:
                    audio_buttons[a_type] = b

        if audio_buttons:
            target_audio = audio or "subtitled"
            chosen_a_btn = audio_buttons.get(target_audio)
            if not chosen_a_btn and audio_buttons:
                chosen_a_btn = next(iter(audio_buttons.values()))

            if chosen_a_btn:
                if status:
                    try:
                        lbl = "زیرنویس" if target_audio == "subtitled" else "دوبله"
                        await status.edit(f"🎙 در حال انتخاب نسخه {lbl}...")
                    except Exception:
                        pass
                await act.click(data=chosen_a_btn.data)
                clicked.add(chosen_a_btn.data)
                await asyncio.sleep(2.5)
                continue

        # 6) انتخاب کیفیت (1080، 720، 480 و ...)
        qual_buttons = {}
        for b in buttons:
            if b.data and b.data not in clicked:
                q_n = _label_quality(b.text or "")
                if q_n:
                    qual_buttons[q_n] = b

        if qual_buttons:
            target_q = int(quality) if isinstance(quality, (int, str)) and str(quality).isdigit() else 720
            chosen_q_btn = qual_buttons.get(target_q)
            if not chosen_q_btn:
                avail_qs = sorted(qual_buttons.keys())
                chosen_q_btn = qual_buttons[min(avail_qs, key=lambda x: abs(x - target_q))]

            if chosen_q_btn:
                if status:
                    try:
                        await status.edit(f"🎥 در حال انتخاب کیفیت {target_q}p...")
                    except Exception:
                        pass
                await act.click(data=chosen_q_btn.data)
                clicked.add(chosen_q_btn.data)
                await asyncio.sleep(2.2)
                continue

        # 7) دکمه دانلود یکجا / پک کامل
        batch_btn = next((b for b in buttons if b.data and b.data not in clicked and any(h in (b.text or "").lower() for h in ("یکجا", "پک کامل", "زیپ", "zip"))), None)
        if batch_btn and (episode is None or episode == "all"):
            if status:
                try:
                    await status.edit("🎬 در حال دریافت یکجای تمام قسمت‌ها...")
                except Exception:
                    pass
            await act.click(data=batch_btn.data)
            clicked.add(batch_btn.data)
            await asyncio.sleep(4.0)
            continue

        # 8) دکمه‌های فهرست قسمت‌ها (قسمت 1، 2 و ...)
        ep_buttons = {}
        for b in buttons:
            if b.data and b.data not in clicked:
                ep_n = _extract_episode_num(b.text or "")
                if ep_n is not None:
                    ep_buttons[ep_n] = b

        if ep_buttons:
            target_ep = int(episode) if isinstance(episode, (int, str)) and str(episode).isdigit() else None
            if target_ep is not None and target_ep in ep_buttons:
                ep_b = ep_buttons[target_ep]
                if status:
                    try:
                        await status.edit(f"🎬 در حال دریافت قسمت {target_ep}...")
                    except Exception:
                        pass
                await act.click(data=ep_b.data)
                clicked.add(ep_b.data)
                await asyncio.sleep(3.0)
                continue
            elif episode is None or episode == "all":
                for ep_n in sorted(ep_buttons.keys()):
                    ep_b = ep_buttons[ep_n]
                    if status:
                        try:
                            await status.edit(f"🎬 در حال دریافت قسمت {ep_n}...")
                        except Exception:
                            pass
                    await act.click(data=ep_b.data)
                    clicked.add(ep_b.data)
                    for _ in range(5):
                        await asyncio.sleep(1.0)
                        latest = await client.get_messages(bot, limit=10)
                        for lm in latest:
                            if not lm.out and lm.id > base and isinstance(lm.media, types.MessageMediaDocument):
                                if lm.id not in files:
                                    files[lm.id] = lm
                                    await forward_stream(lm)
                return sorted(files.values(), key=lambda x: x.id), None

        # 9) دکمه‌ی دانلود مستقیم
        dl = next((b for b in buttons
                   if b.data and b.data.startswith(b"download_") and b.data not in clicked), None)
        if dl:
            await act.click(data=dl.data)
            clicked.add(dl.data)
            await asyncio.sleep(2.5)
            continue

        dl2 = next((b for b in buttons
                    if b.data and b.data not in clicked
                    and any(h in (b.text or "").lower() for h in DOWNLOAD_HINTS)), None)
        if dl2:
            await act.click(data=dl2.data)
            clicked.add(dl2.data)
            await asyncio.sleep(2.5)
            continue

        # 10) ناوبری با هوش مصنوعی برای دکمه‌های خارج از الگو (بدون دکمه‌های بازگشت)
        from services.media import ai_nav
        flat_valid = [b for b in buttons if b.data and b.data not in clicked and not ai_nav.is_back_button(b.text or "")]
        if flat_valid:
            try:
                state = {"files_count": len(files), "last_action": "ناوبری", "step": _}
                req_info = {
                    "title": getattr(event, "message", "") or "دانلود",
                    "season": season,
                    "episode": episode,
                    "quality": quality,
                    "audio": audio
                }
                ai_idx = await ai_nav.ai_pick_button(flat_valid, act.message or "", req_info, state)
                if ai_idx is not None and 0 <= ai_idx < len(flat_valid):
                    chosen_b = flat_valid[ai_idx]
                    if status:
                        try:
                            await status.edit(f"🎬 [هوش مصنوعی] در حال انتخاب «{chosen_b.text or ''}»...")
                        except Exception:
                            pass
                    await act.click(data=chosen_b.data)
                    clicked.add(chosen_b.data)
                    await asyncio.sleep(2.5)
                    continue
                elif ai_idx is None and files:
                    return sorted(files.values(), key=lambda x: x.id), None
            except Exception as e:
                log.warning("ai_nav in follow_bot error: %s", e)

        # 11) هر دکمه‌ی callback دیگه (آخرین راه - به استثنای دکمه‌های بازگشت)
        other = next((b for b in buttons if b.data and b.data not in clicked and not ai_nav.is_back_button(b.text or "")), None)
        if other:
            await act.click(data=other.data)
            clicked.add(other.data)
            await asyncio.sleep(2.5)
            continue

        return sorted(files.values(), key=lambda x: x.id), "نتونستم ادامه‌ی جریان رو تشخیص بدم."

    return sorted(files.values(), key=lambda x: x.id), None


def _status_msg(status: str, query: str) -> str:
    if status == "subscription":
        return "این ربات اشتراک پولی می‌خواد؛ بیخیالش شدم."
    return status or f"نتونستم «{query}» رو بگیرم."


async def fetch_movie(client, query: str, quality=None, audio=None, season=None, episode=None, event=None, status=None):
    """می‌گرده، تشخیص می‌ده و همه‌ی فایل‌ها رو می‌گیره.

    برمی‌گردونه (files: list, err: str|None). کانال‌های اسپانسری که عضو شده رو آخرش لفت می‌ده.
    """
    joined = []
    try:
        mm = BOT_START_RE.search(query)
        if mm:
            files, err_status = await follow_bot(
                client, mm.group(1), mm.group(2), joined,
                quality=quality, audio=audio, season=season, episode=episode,
                event=event, status=status
            )
            if files:
                return files, None
            return [], _status_msg(err_status, query)

        links = await _search_links(client, query, quality=quality)
        if not links:
            links = await _search_channels(client, query, quality=quality)
        if not links:
            return [], f"چیزی به اسم «{query}» توی کانال‌هات پیدا نکردم."

        last_err = None
        skipped_sub = 0
        for bot, token in links[:3]:
            files, err_status = await follow_bot(
                client, bot, token, joined,
                quality=quality, audio=audio, season=season, episode=episode,
                event=event, status=status
            )
            if files:
                return files, None
            if err_status == "subscription":
                skipped_sub += 1
                continue
            last_err = err_status or "فایل نیومد."

        if skipped_sub and skipped_sub == min(3, len(links)):
            return [], "همه‌ی لینک‌ها اشتراک پولی می‌خواستن؛ نتونستم رایگان بگیرم."
        return [], last_err or "نتونستم فایل رو بگیرم."
    finally:
        for ch in joined:
            await _leave(client, ch)
            await asyncio.sleep(0.5)
