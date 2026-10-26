import asyncio
import logging
import os
import re
import time
import unicodedata
from typing import Any, Dict, List, Optional, Tuple, Union

from telethon import functions, types
from telethon.tl.functions.channels import JoinChannelRequest, LeaveChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest

from core import cognitive_memory
from core import config
from services.media import ai_nav
from services.media import fetch

log = logging.getLogger("media_flow")

PERSIAN_NUMS = {'۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4', '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9'}
ORDINALS = {
    'اول': 1, 'یکم': 1, 'دوم': 2, 'سوم': 3, 'چهارم': 4, 'پنجم': 5,
    'ششم': 6, 'هفتم': 7, 'هشتم': 8, 'نهم': 9, 'دهم': 10,
    'یازدهم': 11, 'دوازدهم': 12, 'سیزدهم': 13, 'چهاردهم': 14, 'پانزدهم': 15
}

CONFIRM_HINTS = ("تایید", "تأیید", "بررسی", "عضویت", "عضو شدم", "چک", "check", "confirm", "✅", "شدم", "دریافت")
SPONSOR_HINTS = ("عضو", "عضویت", "کانال", "جوین", "سبسکرایب", "subscribe", "join")
BATCH_HINTS = ("دانلود یکجا", "تمام قسمت", "پک کامل", "فایل زیپ", "همه‌ی قسمت", "دانلود کل", "zip")
DUBBED_HINTS = ("دوبله", "دوبله فارسی", "صوت دوبله", "دوبلاژ", "dubbed", "fa dub", "fa_dub")
SUB_HINTS = ("زیرنویس", "زیرنویس چسبیده", "softsub", "hardsub", "sub", "subbed", "farsisub")


def normalize_digits(s: str) -> str:
    if not s:
        return ""
    for p, a in PERSIAN_NUMS.items():
        s = s.replace(p, a)
    return s


def extract_season(text: str) -> Optional[int]:
    """استخراج شماره فصل از متن یا دکمه."""
    t = normalize_digits((text or "").lower())
    m = re.search(r"(?:فصل|season|s)\s*0?(\d{1,2})", t)
    if m:
        return int(m.group(1))
    m = re.search(r"\b(?:ف)\s*0?(\d{1,2})\b", t)
    if m:
        return int(m.group(1))
    for word, num in ORDINALS.items():
        if f"فصل {word}" in t or f"فصل{word}" in t:
            return num
    return None


def extract_episode(text: str) -> Union[int, str, None]:
    """استخراج شماره قسمت یا عبارت «کل فصل/همه»."""
    t = normalize_digits((text or "").lower())
    if any(k in t for k in ["کل فصل", "همه قسمتا", "همه قسمت‌ها", "تمام قسمت‌ها", "همش", "همه رو", "دانلود یکجا", "all"]):
        return "all"
    m = re.search(r"(?:قسمت|episode|ep|e)\s*(\d{1,3})", t)
    if m:
        return int(m.group(1))
    for word, num in ORDINALS.items():
        if f"قسمت {word}" in t or f"قسمت{word}" in t:
            return num
    return None


def extract_quality(text: str) -> Optional[int]:
    """استخراج کیفیت ویدیو (1080, 720, 480, ...)"""
    t = normalize_digits((text or "").lower())
    m = re.search(r"(?:کیفیت|با کیفیت|در کیفیت)?\s*(1080|720|480|360|2160|4k)", t)
    if m:
        val = m.group(1)
        if val == "4k":
            return 2160
        return int(val)
    m2 = re.search(r"\b(1080|720|480|360|2160)\b", t)
    if m2:
        return int(m2.group(1))
    return None


def extract_audio(text: str, preferred: Optional[str] = None) -> Optional[str]:
    """تشخیص نسخه دوبله یا زیرنویس با اولویت ترجیح کاربر."""
    t = (text or "").lower()
    has_dub = any(k in t for k in DUBBED_HINTS)
    has_sub = any(k in t for k in SUB_HINTS)
    if has_dub and has_sub:
        return preferred or "subtitled"
    if has_dub:
        return "dubbed"
    if has_sub:
        return "subtitled"
    return None


def parse_media_request(text: str) -> Dict[str, Any]:
    """آنالیز جامع متن ورودی کاربر برای استخراج فیلم، فصل، قسمت، کیفیت و صوت."""
    q_quality = extract_quality(text)
    q_season = extract_season(text)
    q_episode = extract_episode(text)
    q_audio = extract_audio(text)

    # پاکسازی عنوان
    cleaned = normalize_digits(text)
    # ۱. اول عبارت‌های ترکیبی فصل، قسمت و کیفیت
    cleaned = re.sub(r"(?:فصل|season|s)\s*\d{1,2}", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(?:ف)\s*\d{1,2}\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"(?:قسمت|episode|ep|e)\s*\d{1,3}", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"(?:کیفیت|با کیفیت|در کیفیت)?\s*(?:1080|720|480|360|2160|4k)p?", " ", cleaned, flags=re.IGNORECASE)
    for ord_w in ORDINALS:
        cleaned = cleaned.replace(f"فصل {ord_w}", " ").replace(f"قسمت {ord_w}", " ")

    # ۲. عبارات رایج دانلود و اصطلاحات
    for w in ("کاپری", "فیلم", "سریال", "انیمیشن", "انیمه", "دانلود کن", "دانلود", "رو بیار", "بگیر", "بیار", "بفرست", "بده", "پیدا کن", "برو", "کل فصل", "همه قسمتا", "همه قسمت‌ها", "تمام قسمت‌ها", "همش", "همه رو", "دوبله فارسی", "دوبله", "زیرنویس چسبیده", "زیرنویس"):
        cleaned = re.sub(rf"(?:^|\s){re.escape(w)}(?:$|\s)", " ", cleaned, flags=re.IGNORECASE)

    # ۳. حذف حروف اضافه و حرف تک 'ف'
    cleaned = re.sub(r"\b(?:رو|را|به|با|کل|ف)\b", " ", cleaned)

    title = " ".join(cleaned.split()).strip("،,:.؟? ")

    # اگر فصل پیدا نشده، بررسی حافظه شناختی برای سریال‌های پیگیری‌شده
    if q_season is None and title:
        try:
            prefs = cognitive_memory.get_media_preferences()
            prog = prefs.get("series_progress", {})
            for s_k, s_v in prog.items():
                if s_k.lower() in title.lower():
                    if s_v.get("last_season"):
                        q_season = s_v.get("last_season")
        except Exception:
            pass

    return {
        "title": title,
        "season": q_season,
        "episode": q_episode,
        "quality": q_quality,
        "audio": q_audio
    }


def is_media_request(text: str) -> bool:
    """تشخیص دقیق اینکه آیا پیام کاربر درخواست دانلود یا دریافت فیلم/سریال/فایل است یا خیر."""
    t = (text or "").lower().strip()
    if not t:
        return False

    # اگر پیام فرستادن به شخص دیگری باشد (Ghostwriter)، مدیا نیست
    if re.search(r"^(?:به\s+(@?[\w\.\-]+|\S+)|(بهش))\s+(?:پیام\s*)?بگو", t):
        return False

    # ۲. استثنای قطعی یوتیوب: ویدیوهای یوتیوب باید در گوگل/وب جستجو شوند، نه در ربات‌های فیلم تلگرام!
    if "یوتیوب" in t or "youtube" in t:
        return False

    # ۱. استثنائات قطعی: اگر سوال اطلاعاتی، تحلیلی، بازی، راهنمایی، گیمینگ یا گفتگوی عمومی باشد، مدیا نیست!
    INFO_INDICATORS = (
        "چطوری", "چگونه", "چیه", "چیست", "چرا", "کجا", "بهترین روش", "روش", "راهنمایی", "راهکار",
        "چیکار کنم", "توضیح بده", "توضیح", "آموزش", "نظرت", "تحلیل", "مقایسه",
        "فاصله بده", "متن رو", "خلاصه کن", "ترجمه",
        "برنامه‌نویسی", "پایتون", "کد", "چت", "حالت چطوره", "سلام", "بازی", "گیم"
    )
    has_explicit_media_noun = any(n in t for n in ("فیلم", "سریال", "انیمه", "انیمیشن", "سینمایی"))
    if any(info in t for info in INFO_INDICATORS) and not has_explicit_media_noun:
        return False

    # دیپ‌لینک‌های صریح ربات‌های تلگرام
    if "t.me/" in t and "?start=" in t:
        return True

    # اگر کلمات فصل یا قسمت همراه با کلمات مربوط به مدیا باشد
    if any(k in t for k in ("فصل", "قسمت", "season", "episode", "s0", "e0")):
        # اگر در سیاق سوال عمومی نیست
        if has_explicit_media_noun or any(w in t for w in ("بفرست", "دانلود", "بگیر", "کیفیت", "قسمت", "فصل", "زیرنویس", "دوبله")):
            return True

    if re.search(r"\b(?:ف|s|e)\s*\d{1,2}\b", t) and (has_explicit_media_noun or any(w in t for w in ("دانلود", "بفرست", "بگیر"))):
        return True

    # اگر کاراکتر ف در انتهای عبارت انگلیسی یا نام سریال باشد (تایپ ناقص مثل slow horse ف)
    if re.search(r"\s+ف$", t) and any(c.isascii() and c.isalpha() for c in t) and len(t.split()) <= 4:
        return True

    if has_explicit_media_noun:
        return True

    if any(v in t for v in ("دانلود کن", "دانلودش کن", "دانلود")):
        return True

    if any(v in t for v in ("بگیر", "بیار", "بفرست")) and any(k in t for k in ("کیفیت", "دوبله", "زیرنویس", "1080", "720", "480", "4k")):
        return True

    # اگر درخواست کوتاه است و صراحتاً دانلود/فرستادن فایل است (حداکثر ۵ کلمه، نه یک سوال طولانی)
    words = t.split()
    if len(words) <= 5 and any(v in t for v in ("دانلود", "فایلش رو بفرست", "فیلمش رو بیار")):
        return True

    # بررسی آیا با عناوین ذخیره‌شده در حافظه تطابق دارد
    try:
        prefs = cognitive_memory.get_media_preferences()
        prog = prefs.get("series_progress", {})
        for s_title in prog:
            if s_title.lower() in t and any(w in t for w in ("بفرست", "قسمت", "فصل", "دانلود")):
                return True
    except Exception:
        pass

    return False


async def search_smart_media_links(client, title: str, req: Dict[str, Any]) -> Dict[str, Any]:
    """
    جستجوی ساختاریافته در کانال‌ها:
    تفکیک دقیق لینک‌های دیپ‌لینک بر اساس فصل‌ها و قسمت‌ها از متن و ساختار پست‌ها.
    """
    res = await client(functions.messages.SearchGlobalRequest(
        q=title, filter=types.InputMessagesFilterEmpty(),
        min_date=None, max_date=None, offset_rate=0,
        offset_peer=types.InputPeerEmpty(), offset_id=0, limit=40
    ))

    target_season = req.get("season")
    target_ep = req.get("episode")
    parsed_posts = []

    # بررسی فایل‌های مستقیم سندی و ویدیویی در کانال‌ها
    direct_channel_files = []
    for m in res.messages:
        if m.out:
            continue
        if isinstance(getattr(m, "media", None), types.MessageMediaDocument):
            doc = getattr(m.media, "document", None)
            mime = getattr(doc, "mime_type", "") or ""
            c_text = unicodedata.normalize('NFKD', m.message or "")
            if "video" in mime or any(ext in c_text.lower() for ext in (".mkv", ".mp4", ".avi", "1080p", "720p", "480p")):
                direct_channel_files.append(m)

    if direct_channel_files:
        matched_channel_files = []
        for df in direct_channel_files:
            c_txt = unicodedata.normalize('NFKD', df.message or "")
            f_s = extract_season(c_txt)
            f_ep = extract_episode(c_txt)
            if target_season is not None and f_s is not None and f_s != target_season:
                continue
            if isinstance(target_ep, int) and isinstance(f_ep, int) and f_ep != target_ep:
                continue
            matched_channel_files.append(df)

        if matched_channel_files:
            return {"kind": "direct_channel_files", "files": matched_channel_files}

    for m in res.messages:
        if m.out or not m.message:
            continue
        raw_text = unicodedata.normalize('NFKD', m.message)
        lines = raw_text.splitlines()

        cur_season = None
        post_links = []

        for line in lines:
            sm = re.search(r'(?:Season|فصل)\s*0?(\d+)', line, re.IGNORECASE)
            if sm:
                cur_season = int(sm.group(1))

            for mm in fetch.BOT_START_RE.finditer(line):
                bot, tok = mm.group(1), mm.group(2)
                if fetch.is_paid_bot(bot):
                    continue
                post_links.append({"bot": bot, "token": tok, "season": cur_season, "label": ""})

        # استخراج از entities با متن برچسب
        for e in (m.entities or []):
            url = getattr(e, "url", None)
            if not url:
                continue
            mm = fetch.BOT_START_RE.search(url)
            if mm:
                bot, tok = mm.group(1), mm.group(2)
                if fetch.is_paid_bot(bot):
                    continue
                lbl = fetch._entity_text(m.message, getattr(e, "offset", 0), getattr(e, "length", 0))
                ep_val = extract_episode(lbl) if lbl else None
                q_val = extract_quality(lbl) if lbl else None

                # فصل مرتبط بر اساس موقعیت قبل از لینک
                s_val = None
                before_text = unicodedata.normalize('NFKD', m.message[:getattr(e, "offset", 0)])
                s_matches = list(re.finditer(r'(?:Season|فصل)\s*0?(\d+)', before_text, re.IGNORECASE))
                if s_matches:
                    s_val = int(s_matches[-1].group(1))

                post_links.append({
                    "bot": bot,
                    "token": tok,
                    "label": lbl,
                    "season": s_val,
                    "episode": ep_val if isinstance(ep_val, int) else None,
                    "quality": q_val
                })

        # استخراج از دکمه‌ها
        if m.buttons:
            for row in m.buttons:
                for b in row:
                    if b.url:
                        mm = fetch.BOT_START_RE.search(b.url)
                        if mm:
                            bot = mm.group(1)
                            if fetch.is_paid_bot(bot):
                                continue
                            b_text = b.text or ""
                            post_links.append({
                                "bot": bot,
                                "token": mm.group(2),
                                "label": b_text,
                                "season": extract_season(b_text),
                                "episode": extract_episode(b_text) if isinstance(extract_episode(b_text), int) else None,
                                "quality": extract_quality(b_text)
                            })

        if post_links:
            parsed_posts.append({"msg": m, "links": post_links})

    # تطابق فصلی مستقیم
    if target_season is not None:
        matched_season_links = []
        for p in parsed_posts:
            s_links = [l for l in p["links"] if l.get("season") == target_season]
            if s_links:
                matched_season_links.extend(s_links)

        if matched_season_links:
            if isinstance(target_ep, int):
                ep_match = [l for l in matched_season_links if l.get("episode") == target_ep]
                if ep_match:
                    return {"kind": "direct_tokens", "tokens": ep_match}
            unique = {}
            for l in matched_season_links:
                k = (l["bot"].lower(), l["token"])
                if k not in unique:
                    unique[k] = l
            sorted_tokens = sorted(unique.values(), key=lambda x: x.get("episode") or 0)
            return {"kind": "direct_tokens", "tokens": sorted_tokens}

    generic_tokens = []
    seen = set()
    for p in parsed_posts:
        for l in p["links"]:
            k = (l["bot"].lower(), l["token"])
            if k not in seen:
                seen.add(k)
                generic_tokens.append(l)

    return {"kind": "bot_menu", "tokens": generic_tokens}


def analyze_menu_buttons(buttons_2d: Optional[List[List[Any]]]) -> Dict[str, Any]:
    """دسته‌بندی هوشمند دکمه‌های پیام ربات تلگرام به فصل‌ها، کیفیت‌ها، صوت و قسمت‌ها."""
    res: Dict[str, Any] = {
        "seasons": {},       # season_num -> button
        "episodes": {},      # ep_num -> button
        "qualities": {},     # quality_num -> button
        "audio": {},         # "dubbed" / "subtitled" -> button
        "batch": None,       # button
        "confirm": None,     # button
        "sponsors": [],      # buttons with invite urls
        "all_valid": []
    }
    if not buttons_2d:
        return res

    all_buttons = [b for row in buttons_2d for b in row]

    for b in all_buttons:
        txt = (b.text or "").strip()
        if not txt:
            continue
        res["all_valid"].append(b)

        # اسپانسر / عضویت
        if b.url and fetch._is_invite_url(b.url):
            res["sponsors"].append(b)
            continue

        # تایید عضویت
        if any(h in txt.lower() for h in CONFIRM_HINTS):
            res["confirm"] = b
            continue

        # دانلود یکجا / بچ
        if any(h in txt.lower() for h in BATCH_HINTS):
            res["batch"] = b

        # فصل‌ها
        s_num = extract_season(txt)
        if s_num is not None:
            res["seasons"][s_num] = b

        # قسمت‌ها
        ep_num = extract_episode(txt)
        if isinstance(ep_num, int):
            res["episodes"][ep_num] = b

        # کیفیت‌ها
        q_num = extract_quality(txt)
        if q_num is not None and q_num in fetch.QUALITY_SET:
            res["qualities"][q_num] = b

        # صوت
        a_type = extract_audio(txt)
        if a_type is not None:
            res["audio"][a_type] = b

    return res


def match_preferred_button(buttons_2d_or_1d: Any, req: Dict[str, Any]) -> Optional[Any]:
    """تطابق قطعی و هوشمند دکمه‌ها با اولویت‌های کاربر (فصل، صوت، کیفیت، دانلود)."""
    if not buttons_2d_or_1d:
        return None
    if isinstance(buttons_2d_or_1d, list) and buttons_2d_or_1d and isinstance(buttons_2d_or_1d[0], list):
        flat_buttons = [b for row in buttons_2d_or_1d for b in row]
    else:
        flat_buttons = list(buttons_2d_or_1d)

    target_audio = req.get("audio")
    target_q = req.get("quality")
    target_s = req.get("season")
    target_ep = req.get("episode")

    candidates = [
        b for b in flat_buttons
        if getattr(b, "data", None) and not ai_nav.is_back_button(getattr(b, "text", "") or "")
    ]
    if not candidates:
        return None

    best_btn = None
    best_score = -999

    for b in candidates:
        txt = (b.text or "").strip()
        score = 0

        # ۱. صوت / زیرنویس
        b_audio = extract_audio(txt, preferred=target_audio)
        if target_audio:
            if b_audio == target_audio:
                score += 35
            elif b_audio is not None and b_audio != target_audio:
                score -= 60

        # ۲. کیفیت
        b_q = extract_quality(txt)
        if target_q and b_q is not None and b_q in fetch.QUALITY_SET:
            if b_q == target_q:
                score += 45
            else:
                diff = abs(b_q - target_q)
                score += max(0, 20 - (diff // 50))

        # ۳. فصل
        b_s = extract_season(txt)
        if target_s is not None and b_s is not None:
            if b_s == target_s:
                score += 30
            else:
                score -= 40

        # ۴. قسمت
        b_ep = extract_episode(txt)
        if isinstance(target_ep, int) and isinstance(b_ep, int):
            if b_ep == target_ep:
                score += 40
            else:
                score -= 30

        # ۵. دکمه مستقیم دانلود
        if any(h in txt.lower() for h in fetch.DOWNLOAD_HINTS):
            score += 15

        if score > best_score:
            best_score = score
            best_btn = b

    if best_score >= 30:
        return best_btn
    return None


async def _handle_sponsors(client, bot_entity, current_msg, joined_list) -> Tuple[Any, str]:
    """بررسی خودکار و عضویت در کانال‌های اسپانسر تا رفع قفل ربات."""
    for _ in range(5):
        if not current_msg or not current_msg.buttons:
            break
        analysis = analyze_menu_buttons(current_msg.buttons)
        if analysis["sponsors"]:
            for sb in analysis["sponsors"]:
                ch = await fetch._join(client, sb.url)
                if ch is not None and not any(getattr(c, "id", None) == ch.id for c in joined_list):
                    joined_list.append(ch)
                await asyncio.sleep(1.0)
            if analysis["confirm"]:
                await current_msg.click(data=analysis["confirm"].data)
                await asyncio.sleep(2.5)
                msgs = await client.get_messages(bot_entity, limit=5)
                current_msg = next((m for m in msgs if not m.out and m.buttons), current_msg)
                continue
        break
    return current_msg, None


async def start_and_inspect_bot(client, bot_name: str, token: str, joined_list) -> Tuple[Any, Optional[str]]:
    """شروع تعامل با ربات و رسیدن به منوی اصلی بدون قفل اسپانسر."""
    if fetch.is_paid_bot(bot_name):
        return None, "subscription"
    try:
        bot = await client.get_entity(bot_name)
    except Exception as e:
        return None, f"ربات @{bot_name} پیدا نشد: {e}"

    sent = await client.send_message(bot, f"/start {token}" if token else "/start")
    await asyncio.sleep(2.5)

    msgs = await client.get_messages(bot, limit=8)

    # بررسی سریع آیا پیام اشتراک پولی است
    for m in msgs:
        if m.out or m.id <= sent.id:
            continue
        m_txt = m.message or ""
        if m.buttons:
            m_txt += " " + " ".join(b.text or "" for row in m.buttons for b in row)
        if fetch._is_subscription(m_txt):
            fetch.mark_paid_bot(bot_name)
            return None, "subscription"

    candidates = [m for m in msgs if not m.out and m.id > sent.id]
    if not candidates:
        candidates = [m for m in msgs if not m.out]

    # ۱. بررسی آیا فایلی مستقیماً بدون دکمه فرستاده شده؟
    file_msg = next((m for m in candidates if isinstance(m.media, types.MessageMediaDocument)), None)
    if file_msg:
        return file_msg, None

    # ۲. پیام دارای دکمه‌های شیشه‌ای
    menu_msg = next((m for m in candidates if m.buttons), None)

    # ۳. پیام متنی بدون دکمه (دستورات اسلش، لینک‌های دانلود یا کدهای متنی)
    if not menu_msg:
        menu_msg = next((m for m in candidates if (m.message and len(m.message.strip()) > 1)), None)

    if not menu_msg:
        return None, "ربات پاسخی ارسال نکرد."

    if menu_msg.buttons:
        menu_msg, _ = await _handle_sponsors(client, bot, menu_msg, joined_list)
    return menu_msg, None


async def collect_documents(client, bot_entity, base_id: int, timeout: float = 12.0) -> List[Any]:
    """جمع‌آوری تمام فایل‌های سندی جدید ارسال شده توسط ربات."""
    start_time = time.time()
    files = {}
    last_file_time = 0.0

    while time.time() - start_time < timeout:
        msgs = await client.get_messages(bot_entity, limit=20)
        new_found = False
        for m in msgs:
            if m.out or m.id <= base_id:
                continue
            if isinstance(m.media, types.MessageMediaDocument):
                if m.id not in files:
                    files[m.id] = m
                    last_file_time = time.time()
                    new_found = True

        # اگر فایلی رسیده و ۲.۵ ثانیه فایل جدید نیامده، یعنی سری تمام شده
        if files and (time.time() - last_file_time > 2.5):
            break
        await asyncio.sleep(1.0)

    return sorted(files.values(), key=lambda x: x.id)


async def execute_bot_navigation(client, bot_name: str, start_msg, req: Dict[str, Any], event=None, status=None) -> Tuple[List[Any], Optional[str]]:
    """
    ناوبری هوشمند ۰ تا ۱۰۰ ربات‌های تلگرام با کنترل خودمختار هوش مصنوعی:
    - ناوبری هوشمند دکمه‌های شیشه‌ای بدون لوپ و عقبگرد
    - ارسال فرامین متنی (/dl_...) یا کدهای دانلود در صورت عدم وجود دکمه شیشه‌ای
    - دنبال کردن لینک‌ها و توکن‌های دانلود متنی
    - فیلتر اکید دکمه‌های بازگشت و چرخه‌های تکرار (Anti-Loop Circuit Breaker)
    - فوروارد درجا به محض رسیدن هر قسمت به چت کاربر
    """
    try:
        bot = await client.get_entity(bot_name)
    except Exception as e:
        return [], f"خطا در دسترسی به ربات @{bot_name}: {e}"

    cur_msg = start_msg
    base_id = start_msg.id if start_msg else 0
    all_collected = []
    seen_doc_ids = set()
    clicked_actions = set()
    action_history = []
    recent_actions = []

    target_ep = req.get("episode")
    target_audio = req.get("audio")
    target_q = req.get("quality")

    async def forward_now(doc_msg):
        if event and getattr(event, "chat_id", None) and doc_msg.id not in seen_doc_ids:
            seen_doc_ids.add(doc_msg.id)
            all_collected.append(doc_msg)
            try:
                await client.forward_messages(event.chat_id, doc_msg)
                return True
            except Exception as e:
                log.warning(f"Error forwarding file: {e}")
        return False

    # بررسی اولیه آیا فایلی مستقیم ارسال شده است
    direct_docs = await collect_documents(client, bot, base_id, timeout=3.0)
    if direct_docs:
        for d in direct_docs:
            await forward_now(d)
        if isinstance(target_ep, int) or (req.get("season") is None and target_ep is None):
            return all_collected, None

    for step in range(15):
        # بررسی و فوروارد هر فایلی که در میان‌مرحله رسیده است
        interim_docs = await collect_documents(client, bot, base_id, timeout=1.5)
        for d in interim_docs:
            await forward_now(d)

        # اگر کاربر یک قسمت مشخص خواسته بود یا فیلم تک‌قسمتی بود و فایل رسید، اتمام
        if (isinstance(target_ep, int) or (req.get("season") is None and target_ep is None)) and len(all_collected) >= 1:
            return all_collected, None

        # به‌روزرسانی پیام اخیر ربات (پشتیبانی از هر دو نوع پیام: دکمه‌دار یا متن ساده)
        msgs = await client.get_messages(bot, limit=8)
        non_out = [m for m in msgs if not m.out]
        candidates = [m for m in non_out if m.id > base_id] if any(m.id > base_id for m in non_out) else non_out

        file_msg = next((m for m in candidates if isinstance(m.media, types.MessageMediaDocument)), None)
        if file_msg:
            await forward_now(file_msg)
            if (isinstance(target_ep, int) or (req.get("season") is None and target_ep is None)):
                return all_collected, None

        new_cur = next((m for m in candidates if m.buttons or (m.message and len(m.message.strip()) > 1)), None)
        if new_cur:
            cur_msg = new_cur

        if not cur_msg:
            await asyncio.sleep(2.0)
            msgs = await client.get_messages(bot, limit=5)
            cur_msg = next((m for m in msgs if not m.out and (m.buttons or m.message)), None)
            if not cur_msg:
                break

        # رسیدگی خودکار به اسپانسرها و قفل‌های عضویت
        if cur_msg.buttons:
            analysis = analyze_menu_buttons(cur_msg.buttons)
            if analysis["sponsors"]:
                for sb in analysis["sponsors"]:
                    await fetch._join(client, sb.url)
                    await asyncio.sleep(1.0)
                if analysis["confirm"]:
                    await cur_msg.click(data=analysis["confirm"].data)
                    action_history.append("تایید عضویت در کانال‌های اسپانسر")
                    await asyncio.sleep(2.5)
                    continue

        # بررسی ربات‌های ورق‌زن استاندارد (آیتم X/Y و دکمه دریافت و بعدی)
        cur_text = normalize_digits(cur_msg.message or '')
        m_item = re.search(r'(?:آیتم|item)\s*(\d+)\s*/\s*(\d+)', cur_text, re.IGNORECASE)
        all_btns = [b for row in (cur_msg.buttons or []) for b in row]
        dl_btn = next((b for b in all_btns if any(h in (b.text or "") for h in ("دریافت فایل", "دریافت", "دانلود"))), None)
        next_btn = next((b for b in all_btns if any(h in (b.text or "") for h in ("بعدی", "next", "⏭"))), None)

        if m_item and dl_btn:
            cur_item = int(m_item.group(1))
            total_items = int(m_item.group(2))
            if isinstance(target_ep, int):
                while cur_item < target_ep and next_btn:
                    if status:
                        await status.edit(f"🎬 در حال ورق زدن به قسمت {target_ep} (آیتم {cur_item}/{total_items})...")
                    await cur_msg.click(data=next_btn.data)
                    await asyncio.sleep(1.2)
                    msgs = await client.get_messages(bot, limit=5)
                    cur_msg = next((m for m in msgs if not m.out and m.buttons), cur_msg)
                    cur_text = normalize_digits(cur_msg.message or '')
                    m_item = re.search(r'(?:آیتم|item)\s*(\d+)\s*/\s*(\d+)', cur_text, re.IGNORECASE)
                    cur_item = int(m_item.group(1)) if m_item else cur_item + 1
                    all_btns = [b for row in (cur_msg.buttons or []) for b in row]
                    dl_btn = next((b for b in all_btns if any(h in (b.text or "") for h in ("دریافت فایل", "دریافت", "دانلود"))), dl_btn)
                    next_btn = next((b for b in all_btns if any(h in (b.text or "") for h in ("بعدی", "next", "⏭"))), None)

                if status:
                    await status.edit(f"🎬 در حال دریافت قسمت {target_ep}...")
                if dl_btn:
                    await cur_msg.click(data=dl_btn.data)
                docs = await collect_documents(client, bot, cur_msg.id, timeout=6.0)
                for d in docs:
                    await forward_now(d)
                return all_collected, None

            # کاربر کل فصل را خواسته است (دریافت و فوروارد درجا)
            if status:
                await status.edit(f"🎬 شناسایی {total_items} قسمت! در حال دریافت و فوروارد درجا...")

            for item_idx in range(cur_item, total_items + 1):
                if status:
                    try:
                        await status.edit(f"🎬 در حال دریافت قسمت {item_idx} از {total_items}...")
                    except Exception:
                        pass
                if dl_btn:
                    await cur_msg.click(data=dl_btn.data)
                docs = await collect_documents(client, bot, cur_msg.id, timeout=5.0)
                for d in docs:
                    await forward_now(d)
                if status:
                    try:
                        await status.edit(f"📤 قسمت {item_idx} از {total_items} فوروارد شد 👆")
                    except Exception:
                        pass
                if item_idx < total_items:
                    all_btns = [b for row in (cur_msg.buttons or []) for b in row]
                    next_btn = next((b for b in all_btns if any(h in (b.text or "") for h in ("بعدی", "next", "⏭"))), None)
                    if next_btn:
                        await cur_msg.click(data=next_btn.data)
                        await asyncio.sleep(1.2)
                        msgs = await client.get_messages(bot, limit=5)
                        cur_msg = next((m for m in msgs if not m.out and m.buttons), cur_msg)
                        all_btns = [b for row in (cur_msg.buttons or []) for b in row]
                        dl_btn = next((b for b in all_btns if any(h in (b.text or "") for h in ("دریافت فایل", "دریافت", "دانلود"))), dl_btn)
                    else:
                        break
            return all_collected, None

        # Media download flow handler
        nav_state = {
            "files_count": len(all_collected),
            "history": action_history,
            "step": step + 1
        }
        decision = await ai_nav.ai_decide_action([cur_msg], req, nav_state)
        action_type = decision.get("action")
        reason = decision.get("reason", "")

        if action_type == "done":
            docs_last = await collect_documents(client, bot, base_id, timeout=3.0)
            for d in docs_last:
                await forward_now(d)
            return all_collected, None

        elif action_type == "give_up":
            return all_collected, reason or "عدم دسترسی به فایل"

        elif action_type == "send_text":
            cmd = (decision.get("text") or "").strip()
            act_sig = ("send_text", cmd)
            if act_sig in clicked_actions:
                log.warning("Loop prevention: text command %s already sent. Skipping repeat.", cmd)
            else:
                if status:
                    try:
                        await status.edit(f"🤖 [هوش مصنوعی] ارسال دستور به ربات: {cmd}...")
                    except Exception:
                        pass
                await client.send_message(bot, cmd)
                clicked_actions.add(act_sig)
                action_history.append(f"ارسال دستور «{cmd}» ({reason})")
                recent_actions.append(act_sig)
                await asyncio.sleep(2.5)

                docs_after = await collect_documents(client, bot, cur_msg.id, timeout=5.0)
                for d in docs_after:
                    await forward_now(d)

                if (isinstance(target_ep, int) or (req.get("season") is None and target_ep is None)) and len(all_collected) >= 1:
                    return all_collected, None
                continue

        elif action_type == "follow_link":
            url = (decision.get("url") or "").strip()
            act_sig = ("follow_link", url)
            if act_sig not in clicked_actions:
                clicked_actions.add(act_sig)
                action_history.append(f"دنبال کردن لینک «{url}» ({reason})")
                recent_actions.append(act_sig)
                m_start = fetch.BOT_START_RE.search(url)
                if m_start:
                    sub_bot, sub_tok = m_start.group(1), m_start.group(2)
                    sub_files, _ = await fetch.follow_bot(
                        client, sub_bot, sub_tok, [],
                        quality=target_q, audio=target_audio,
                        season=req.get("season"), episode=target_ep,
                        event=event, status=status
                    )
                    if sub_files:
                        for sf in sub_files:
                            await forward_now(sf)
                        return all_collected, None
            continue

        elif action_type == "click_button" and decision.get("button"):
            btn_dict = decision["button"]
            b_data = btn_dict.get("data")
            b_text = btn_dict.get("text", "")
            act_sig = ("click_button", b_text, b_data)

            if act_sig in clicked_actions:
                log.warning("Loop prevention: button %s already clicked in this flow.", b_text)
            else:
                if status:
                    try:
                        await status.edit(f"🎬 [هوش مصنوعی] انتخاب «{b_text}»...")
                    except Exception:
                        pass
                await cur_msg.click(data=b_data)
                clicked_actions.add(act_sig)
                action_history.append(f"انتخاب دکمه «{b_text}» ({reason})")
                recent_actions.append(act_sig)
                await asyncio.sleep(2.5)

                docs_after = await collect_documents(client, bot, cur_msg.id, timeout=4.0)
                for d in docs_after:
                    await forward_now(d)

                if (isinstance(target_ep, int) or (req.get("season") is None and target_ep is None)) and len(all_collected) >= 1:
                    return all_collected, None
                continue

        # Button matching fallback handler
        if cur_msg.buttons:
            best_b = match_preferred_button(cur_msg.buttons, req)
            if best_b and getattr(best_b, "data", None):
                b_text = (best_b.text or "").strip()
                act_sig = ("click_button", b_text, best_b.data)
                if act_sig not in clicked_actions:
                    if status:
                        try:
                            await status.edit(f"🎬 انتخاب «{b_text}»...")
                        except Exception:
                            pass
                    await cur_msg.click(data=best_b.data)
                    clicked_actions.add(act_sig)
                    action_history.append(f"انتخاب «{b_text}»")
                    recent_actions.append(act_sig)
                    await asyncio.sleep(2.5)

                    docs_after = await collect_documents(client, bot, cur_msg.id, timeout=4.0)
                    for d in docs_after:
                        await forward_now(d)
                    if (isinstance(target_ep, int) or (req.get("season") is None and target_ep is None)) and len(all_collected) >= 1:
                        return all_collected, None
                    continue

        # فال‌بک ساختاری امن: انتخاب فصل، کیفیت و صوت با احترام قطعی به اولویت کاربر (بدون انتخاب صوت متضاد)
        if cur_msg.buttons:
            analysis = analyze_menu_buttons(cur_msg.buttons)

            # ۱. انتخاب فصل
            if analysis["seasons"]:
                raw_s = req.get("season")
                target_season = int(raw_s) if raw_s is not None else None
                s_btn = analysis["seasons"].get(target_season) if target_season else analysis["seasons"][sorted(analysis["seasons"].keys())[0]]
                if s_btn and s_btn.data and ("click_button", s_btn.text, s_btn.data) not in clicked_actions and not ai_nav.is_back_button(s_btn.text or ""):
                    await cur_msg.click(data=s_btn.data)
                    clicked_actions.add(("click_button", s_btn.text, s_btn.data))
                    await asyncio.sleep(2.2)
                    continue

            # ۲. انتخاب صوت (اکیداً بدون انتخاب صوت مخالف)
            if analysis["audio"]:
                chosen_a_btn = None
                if target_audio:
                    chosen_a_btn = analysis["audio"].get(target_audio)
                else:
                    chosen_a_btn = analysis["audio"].get("subtitled") or next(iter(analysis["audio"].values()), None)

                if chosen_a_btn and chosen_a_btn.data and ("click_button", chosen_a_btn.text, chosen_a_btn.data) not in clicked_actions and not ai_nav.is_back_button(chosen_a_btn.text or ""):
                    await cur_msg.click(data=chosen_a_btn.data)
                    clicked_actions.add(("click_button", chosen_a_btn.text, chosen_a_btn.data))
                    await asyncio.sleep(2.2)
                    continue

            # ۳. انتخاب کیفیت
            if analysis["qualities"]:
                target_q_val = target_q or 480
                q_btn = analysis["qualities"].get(target_q_val)
                if not q_btn:
                    avail_qs = sorted(analysis["qualities"].keys())
                    q_btn = analysis["qualities"][min(avail_qs, key=lambda x: abs(x - target_q_val))]
                if q_btn and q_btn.data and ("click_button", q_btn.text, q_btn.data) not in clicked_actions and not ai_nav.is_back_button(q_btn.text or ""):
                    await cur_msg.click(data=q_btn.data)
                    clicked_actions.add(("click_button", q_btn.text, q_btn.data))
                    await asyncio.sleep(2.2)
                    continue

            # ۴. دکمه مستقیم دانلود
            dl_b = next((b for b in analysis["all_valid"] if b.data and ("click_button", b.text, b.data) not in clicked_actions and not ai_nav.is_back_button(b.text or "") and any(h in (b.text or "").lower() for h in fetch.DOWNLOAD_HINTS)), None)
            if dl_b:
                await cur_msg.click(data=dl_b.data)
                clicked_actions.add(("click_button", dl_b.text, dl_b.data))
                docs = await collect_documents(client, bot, cur_msg.id, timeout=8.0)
                for d in docs:
                    await forward_now(d)
                if all_collected:
                    return all_collected, None

        # ۵. فال‌بک دستورات اسلش یا متنی در پیام جاری
        if cur_msg.message:
            m_elems = ai_nav.extract_message_elements(cur_msg)
            if m_elems.get("commands"):
                best_cmd = ai_nav.match_best_command(cur_msg.message, m_elems["commands"], req)
                if best_cmd and ("send_text", best_cmd) not in clicked_actions:
                    if status:
                        try:
                            await status.edit(f"🤖 ارسال دستور دانلود: {best_cmd}...")
                        except Exception:
                            pass
                    await client.send_message(bot, best_cmd)
                    clicked_actions.add(("send_text", best_cmd))
                    recent_actions.append(("send_text", best_cmd))
                    await asyncio.sleep(2.5)
                    docs = await collect_documents(client, bot, cur_msg.id, timeout=6.0)
                    for d in docs:
                        await forward_now(d)
                    if (isinstance(target_ep, int) or (req.get("season") is None and target_ep is None)) and len(all_collected) >= 1:
                        return all_collected, None
                    continue

        # تشخیص حلقه تکراری
        if len(recent_actions) >= 4 and recent_actions[-1] == recent_actions[-3] and recent_actions[-2] == recent_actions[-4]:
            log.warning("Loop cycle detected in bot navigation; breaking circuit.")
            break

        await asyncio.sleep(1.5)

    # بررسی نهایی برای فایل‌های تاخیری
    final_docs = await collect_documents(client, bot, base_id, timeout=3.5)
    for d in final_docs:
        await forward_now(d)

    if all_collected:
        return all_collected, None

    return [], "فایلی از سمت ربات دریافت نشد."


async def smart_fetch_media(
    client, event, status, question: str, pending: dict, req_override: Optional[Dict[str, Any]] = None
) -> Tuple[bool, str]:
    """
    جریان هوشمند جستجو، تشخیص سریال/فیلم، پرسش از کاربر در صورت چند فصلی بودن،
    ناوبری دقیق و ارسال تمام فایل‌ها.
    """
    req = parse_media_request(question)
    if req_override:
        for k, v in req_override.items():
            if v is not None:
                req[k] = v
    title = req.get("title") or question

    # ترجمه عنوان فیلم در صورت نیاز
    if "t.me/" not in title and not any(ch.isascii() and ch.isalpha() for ch in title):
        try:
            from ai_engine import ai
            en_title = await asyncio.to_thread(ai._english_query, title)
            if en_title:
                title = en_title
        except Exception:
            pass

    if status:
        await status.edit(f"🔍 در حال جستجوی منابع و ربات‌های دانلود برای «{title}»...")

    # ۱. جستجوی ساختاریافته در کانال‌ها
    structured = await search_smart_media_links(client, title, req)

    # حالت صفر: فایل‌های ویدیویی مستقیم در کانال‌ها پیدا شده‌اند (فوروارد فوری بدون نیاز به ربات واسط)
    if structured.get("kind") == "direct_channel_files" and structured.get("files"):
        c_files = structured["files"]
        if status:
            await status.edit(f"🎬 تعداد {len(c_files)} فایل ویدیویی مستقیم در کانال‌ها پیدا شد! در حال فوروارد...")
        fwded = []
        for cf in c_files:
            try:
                await client.forward_messages(event.chat_id, cf)
                fwded.append(cf)
            except Exception as e:
                log.warning(f"Error forwarding direct channel file: {e}")
        if fwded:
            if status:
                await status.edit(f"✅ تمام {len(fwded)} فایل با موفقیت فوروارد شد 👆")
            return True, "ارسال شد."

    # حالت الف: لینک‌های مستقیم قسمت‌های فصل در کانال پیدا شده‌اند (حل مشکل اسلو هورس و امثال آن)
    if structured.get("kind") == "direct_tokens" and structured.get("tokens"):
        tokens = structured["tokens"]
        s_num = req.get("season") or "مورد نظر"
        if status:
            await status.edit(f"🎬 تعداد {len(tokens)} قسمت از فصل {s_num} پیدا شد! در حال دریافت فایل‌ها...")

        joined_list = []
        all_files = []
        seen_msg_ids = set()
        try:
            for i, t_info in enumerate(tokens):
                b_name = t_info["bot"]
                tok = t_info["token"]
                lbl = t_info.get("label") or f"قسمت {i+1}"
                if status:
                    try:
                        await status.edit(f"🎬 در حال دریافت {lbl} ({i+1} از {len(tokens)})...")
                    except Exception:
                        pass
                f_list, err = await fetch.follow_bot(
                    client,
                    b_name,
                    tok,
                    joined_list,
                    quality=req.get("quality"),
                    audio=req.get("audio"),
                    season=req.get("season"),
                    episode=t_info.get("episode") or req.get("episode"),
                    event=event,
                    status=status,
                )
                if err == "subscription":
                    fetch.mark_paid_bot(b_name)
                    if status:
                        try:
                            await status.edit(f"⚠️ ربات @{b_name} اشتراکی/پولی است؛ در حال سوییچ به منابع رایگان...")
                        except Exception:
                            pass
                    break
                if f_list:
                    for f in f_list:
                        if f.id not in seen_msg_ids:
                            seen_msg_ids.add(f.id)
                            all_files.append(f)
                            if event and getattr(event, "chat_id", None):
                                try:
                                    await client.forward_messages(event.chat_id, f)
                                except Exception:
                                    pass
                await asyncio.sleep(1.0)
        finally:
            for ch in joined_list:
                try:
                    await fetch._leave(client, ch)
                except Exception:
                    pass

        if all_files:
            cognitive_memory.update_media_preferences(
                quality=req.get("quality") or 720,
                audio=req.get("audio") or "dubbed",
                series_title=title,
                season=req.get("season")
            )
            if status:
                await status.edit(f"✅ تمام {len(all_files)} قسمت فصل {s_num} سریال «{title}» با موفقیت فوروارد شد 👆")
            return True, "ارسال شد."

    # حالت ب: بات‌های منودار عمومی (مثل AloFilmBot)
    cand_tokens = [t for t in (structured.get("tokens") or []) if not fetch.is_paid_bot(t.get("bot", ""))]
    raw_links = await fetch._search_links(client, title, quality=req.get("quality"))
    if not raw_links:
        raw_links = await fetch._search_channels(client, title, quality=req.get("quality"))

    candidates = []
    seen_cand = set()
    for t in cand_tokens:
        k = (t["bot"].lower(), t["token"])
        if k not in seen_cand and not fetch.is_paid_bot(t["bot"]):
            seen_cand.add(k)
            candidates.append((t["bot"], t["token"]))
    for b_n, tok in raw_links:
        k = (b_n.lower(), tok)
        if k not in seen_cand and not fetch.is_paid_bot(b_n):
            seen_cand.add(k)
            candidates.append((b_n, tok))

    if not candidates:
        if status:
            await status.edit(f"❌ منبع رایگانی برای «{title}» پیدا نشد (ربات‌های یافت‌شده اشتراکی بودند).")
        return False, "منبع رایگان پیدا نشد."

    menu_msg = None
    bot_name = None
    token = None
    joined_list = []

    for c_bot, c_tok in candidates:
        if fetch.is_paid_bot(c_bot):
            continue
        if status:
            await status.edit(f"🤖 در حال بررسی محتوای ربات @{c_bot}...")
        c_menu, err = await start_and_inspect_bot(client, c_bot, c_tok, joined_list)
        if err == "subscription":
            fetch.mark_paid_bot(c_bot)
            if status:
                try:
                    await status.edit(f"⚠️ ربات @{c_bot} اشتراکی است؛ در حال بررسی منبع رایگان بعدی...")
                except Exception:
                    pass
            continue
        if c_menu:
            menu_msg = c_menu
            bot_name = c_bot
            token = c_tok
            break

    if not menu_msg:
        if status:
            await status.edit(f"❌ هیچ ربات رایگانی برای دریافت «{title}» پاسخ نداد.")
        return False, "هیچ ربات رایگانی پاسخ نداد."

    # اگر مستقیماً یک فایل فرستاده شده بود (فیلم تک‌قسمتی)
    if isinstance(menu_msg.media, types.MessageMediaDocument):
        fwd = await client.forward_messages(event.chat_id, menu_msg)
        if status:
            await status.edit("✅ فایل با موفقیت فوروارد شد 👆")
        return True, "فایل فوروارد شد."

    analysis = analyze_menu_buttons(menu_msg.buttons)

    # بررسی آیا سریال چندفصلی است و کاربر هنوز فصل را نگفته؟
    if len(analysis["seasons"]) > 1 and req.get("season") is None:
        avail_seasons = sorted(analysis["seasons"].keys())
        seasons_text = "، ".join(f"فصل {s}" for s in avail_seasons)

        avail_q = sorted(analysis["qualities"].keys()) if analysis["qualities"] else [480, 720, 1080]
        q_text = " | ".join(f"{q}p" for q in avail_q)

        # ثبت وضعیت در pending برای تعامل چند مرحله‌ای
        pending[str(event.chat_id)] = {
            "kind": "media_select",
            "bot_name": bot_name,
            "token": token,
            "title": title,
            "msg_id": menu_msg.id,
            "joined": [c.id for c in joined_list if hasattr(c, "id")],
            "req": req,
            "available_seasons": avail_seasons,
            "available_qualities": avail_q
        }

        question_prompt = (
            f"🎬 **گزینه‌های پیدا شده برای «{title}»:**\n\n"
            f"📌 **فصل‌های موجود:** {seasons_text}\n"
            f"🎥 **کیفیت‌ها:** {q_text}\n"
            f"🎙 **نسخه‌ها:** دوبله فارسی | زیرنویس چسبیده\n\n"
            "❓ **کدوم فصل و چه کیفیتی رو برات بفرستم؟**\n"
            "*(مثلاً بنویس: «فصل ۱ کیفیت ۷۲۰» یا «کل فصل ۲» یا «فصل ۳ قسمت ۴»)*"
        )
        if status:
            await status.edit(question_prompt)
        return True, "__WAITING_USER_SELECTION__"

    # اگر فصل مشخص است یا فیلم تک قسمتی است، مستقیماً دریافت کن
    if status:
        await status.edit(f"🎬 در حال دریافت محتوای «{title}»...")

    files, err = await execute_bot_navigation(client, bot_name, menu_msg, req, event=event, status=status)

    # پاکسازی کانال‌های اسپانسری که عضو شده بود
    for ch in joined_list:
        try:
            await fetch._leave(client, ch)
        except Exception:
            pass

    if err or not files:
        if status:
            await status.edit(f"❌ {err or 'فایلی دریافت نشد.'}")
        return False, err or "فایل دریافت نشد."

    # یادگیری و ثبت در حافظه شناختی
    cognitive_memory.update_media_preferences(
        quality=req.get("quality") or 720,
        audio=req.get("audio") or "dubbed",
        series_title=title,
        season=req.get("season")
    )

    if status:
        await status.edit(f"✅ تمام {len(files)} قسمت «{title}» با موفقیت فوروارد شد 👆")

    return True, "انجام شد."


async def resume_media_fetch(client, event, pending_data: Dict[str, Any], user_reply: str) -> None:
    """ادامه فرایند دریافت فایل پس از پاسخ کاربر به سوال فصل/کیفیت."""
    bot_name = pending_data.get("bot_name")
    title = pending_data.get("title") or "فیلم"
    orig_req = pending_data.get("req") or {}
    msg_id = pending_data.get("msg_id")

    reply_req = parse_media_request(user_reply)

    # ادغام اطلاعات جدید با درخواست قبلی
    season = reply_req.get("season") or orig_req.get("season") or 1
    episode = reply_req.get("episode") or orig_req.get("episode")
    quality = reply_req.get("quality") or orig_req.get("quality") or 720
    audio = reply_req.get("audio") or orig_req.get("audio") or "dubbed"

    final_req = {
        "title": title,
        "season": season,
        "episode": episode,
        "quality": quality,
        "audio": audio
    }

    status = await event.reply(f"🎬 دریافت شد! در حال آماده‌سازی فصل {season} با کیفیت {quality}p...")

    try:
        bot = await client.get_entity(bot_name)
        start_msg = await client.get_messages(bot, ids=msg_id) if msg_id else None
        if not start_msg or not start_msg.buttons:
            # شروع مجدد در صورت منقضی شدن پیام
            sent = await client.send_message(bot, f"/start {pending_data.get('token', '')}")
            await asyncio.sleep(2.5)
            msgs = await client.get_messages(bot, limit=5)
            start_msg = next((m for m in msgs if not m.out and m.buttons), None)

        files, err = await execute_bot_navigation(client, bot_name, start_msg, final_req, event=event, status=status)

        if err or not files:
            await status.edit(f"❌ {err or 'فایلی پیدا نشد.'}")
            return

        # ثبت یادگیری در حافظه شناختی
        cognitive_memory.update_media_preferences(
            quality=quality,
            audio=audio,
            series_title=title,
            season=season,
            episode=episode
        )

        await status.edit(f"✅ تمام {len(files)} قسمت فصل {season} با کیفیت {quality}p فوروارد شد 👆")
    except Exception as e:
        log.error(f"Error resuming media fetch: {e}")
        await status.edit(f"❌ خطا در پردازش دریافت فایل: {e}")
