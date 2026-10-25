"""ماژول ناوبری و کنترل خودمختار ۰ تا ۱۰۰ ربات‌های مدیا و دانلود با هوش مصنوعی.

این ماژول کنترل کامل جریان تعامل با ربات‌های دانلود تلگرام را به عهده می‌گیرد:
- ناوبری هوشمند دکمه‌های شیشه‌ای (Inline Buttons) بدون گیر افتادن در لوپ
- فیلتر اکید دکمه‌های بازگشت و منوی اصلی (جلوگیری کامل از عقبگرد)
- تشخیص دستورات متنی، اسلش‌کامندها (/dl_... یا /start ...) و کدهای داخل پیام
- تشخیص و استخراج لینک‌های مستقیم (t.me/... یا هایپرلینک‌های متنی)
- تطابق دقیق کیفیت (480p، 720p، 1080p)، صوت (دوبله فارسی در برابر زیرنویس چسبیده)، فصل و قسمت
- مکانیسم ضددور و جلوگیری قطعی از چرخه‌های تکراری (Anti-Loop Circuit Breaker)
"""

import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from ai_engine import ai

log = logging.getLogger("ai_nav")

_PERSIAN_DIGITS = {
    '۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4',
    '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9'
}

BACK_BUTTON_HINTS = (
    "برگشت", "بازگشت", "منوی قبل", "صفحه قبل", "منوی اصلی",
    "back", "return", "main menu", "🔙", "⬅️", "◀️", "↩️"
)


def is_back_button(text: str) -> bool:
    """تشخیص آیا دکمه از نوع بازگشت/منوی اصلی/عقبگرد است یا خیر."""
    t = (text or "").strip().lower()
    if not t:
        return False
    if any(icon in t for icon in ("🔙", "⬅️", "◀️", "↩️")):
        return True
    exact_hints = ("برگشت", "بازگشت", "منوی قبل", "صفحه قبل", "منوی اصلی", "back", "return", "main menu")
    if t in exact_hints or any(t == f"[{h}]" for h in exact_hints):
        return True
    if any(h in t for h in ("منوی قبل", "صفحه قبل", "منوی اصلی", "بازگشت به منو", "برگشت به منو", "بازگشت به منوی قبل")):
        return True
    if any(h in t for h in ("برگشت", "بازگشت", "back")) and len(t) <= 15:
        if not any(k in t for k in ("فیلم", "قسمت", "فصل", "دانلود", "کیفیت", "1080", "720", "480", "series", "movie")):
            return True
    return False


def extract_message_elements(msg: Any) -> Dict[str, Any]:
    """استخراج تمام گزینه‌ها، دستورات، لینک‌ها و دکمه‌ها از یک پیام تلگرام."""
    text = getattr(msg, "message", "") or ""

    # ۱. استخراج دکمه‌ها
    buttons = []
    if getattr(msg, "buttons", None):
        for row_idx, row in enumerate(msg.buttons):
            for col_idx, b in enumerate(row):
                b_text = (getattr(b, "text", "") or "").strip()
                buttons.append({
                    "raw": b,
                    "text": b_text,
                    "data": getattr(b, "data", None),
                    "url": getattr(b, "url", None),
                    "is_back": is_back_button(b_text),
                    "row": row_idx,
                    "col": col_idx
                })

    # ۲. استخراج دستورات اسلش (/dl_... /start ... /get_...)
    commands = list(dict.fromkeys(re.findall(r"(/(?:dl|start|get|download|part|file|watch)_[a-zA-Z0-9_\-]+|/[a-zA-Z0-9_]{3,30})", text, re.IGNORECASE)))

    # ۳. استخراج کدهای عددی یا الفبایی که ربات دستور داده ارسال شوند
    codes = []
    for m in re.finditer(r"(?:کد|code|ارسال|send|شماره)\s*[:=\-]?\s*([a-zA-Z0-9_\-]{4,20})", text, re.IGNORECASE):
        c = m.group(1).strip()
        if c and not c.isdigit() or len(c) >= 3:
            codes.append(c)

    # ۴. استخراج لینک‌های اینترنتی و تلگرامی
    links = []
    # از متن خام
    for m in re.finditer(r"(https?://t\.me/[a-zA-Z0-9_\-\?=&]+|tg://resolve\?[a-zA-Z0-9_\-=&]+)", text):
        links.append({"url": m.group(1), "label": ""})

    # از هایپرلینک‌های entities
    for e in (getattr(msg, "entities", None) or []):
        url = getattr(e, "url", None)
        if url:
            offset = getattr(e, "offset", 0)
            length = getattr(e, "length", 0)
            lbl = text[offset:offset + length].strip() if 0 <= offset < len(text) else ""
            links.append({"url": url, "label": lbl})

    # ۵. بررسی اشتراک پولی
    is_sub = any(h in text.lower() for h in (
        "خرید اشتراک", "vip", "اشتراک ویژه", "ارتقا به vip", "حساب ویژه",
        "پلن نقره‌ای", "پلن طلایی", "پرداخت", "درگاه پرداخت", "سکه شما کافی نیست"
    ))

    # ۶. تفکیک دکمه‌های پیشروی از دکمه‌های بازگشت
    forward_btns = [b for b in buttons if not b["is_back"]]
    display_buttons = forward_btns if forward_btns else buttons

    return {
        "text": text.strip(),
        "buttons": buttons,
        "display_buttons": display_buttons,
        "commands": commands,
        "codes": codes,
        "links": links,
        "is_subscription": is_sub,
    }


def match_best_command(text: str, commands: List[str], req: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """تطابق هوشمند بهترین دستور اسلش بر اساس کیفیت، صوت، فصل و قسمت."""
    if not commands:
        return None
    if not req:
        return commands[0]

    target_q = req.get("quality")
    target_audio = req.get("audio")
    target_ep = req.get("episode")
    target_s = req.get("season")

    best_cmd = None
    best_score = -999

    lines = (text or "").splitlines()
    for cmd in commands:
        cmd_line = next((l for l in lines if cmd in l), "")
        score = 0
        l_low = cmd_line.lower()

        # تطابق کیفیت
        if target_q:
            if str(target_q) in l_low:
                score += 40
            else:
                for other_q in (1080, 720, 480, 360):
                    if other_q != target_q and str(other_q) in l_low:
                        score -= 25

        # تطابق صوت / زیرنویس
        if target_audio == "subtitled":
            if any(k in l_low for k in ("زیرنویس", "sub", "softsub", "hardsub")):
                score += 35
            if any(k in l_low for k in ("دوبله", "dub", "farsi")):
                score -= 50
        elif target_audio == "dubbed":
            if any(k in l_low for k in ("دوبله", "dub", "farsi")):
                score += 35
            if any(k in l_low for k in ("زیرنویس", "sub")):
                score -= 50

        # تطابق فصل
        if target_s is not None:
            if f"s{target_s:02d}" in l_low or f"s{target_s}" in l_low or f"فصل {target_s}" in l_low:
                score += 30

        # تطابق قسمت
        if isinstance(target_ep, int):
            if f"e{target_ep:02d}" in l_low or f"ep{target_ep}" in l_low or f"قسمت {target_ep}" in l_low:
                score += 30

        if score > best_score:
            best_score = score
            best_cmd = cmd

    if best_score > 0:
        return best_cmd
    return commands[0]


NAV_SYSTEM_PROMPT = (
    "تو ناخدای خودمختار هوشمند (Autonomous AI Navigator) برای دانلود دقیق فیلم و سریال از ربات‌های تلگرام هستی.\n"
    "وظیفه تو این است که تمام اجزای پیام ربات (متن، دستورات، لینک‌ها و دکمه‌های شیشه‌ای) را ارزیابی کنی "
    "و در هر مرحله دقیق‌ترین اقدام را برای پیشروی و دریافت فایل به سمت کیفیت و صوت درخواستی کاربر انتخاب کنی.\n\n"
    "قوانین اکید تصمیم‌گیری:\n"
    "۱. جلوگیری کامل از لوپ و درجا زدن: به بخش تاریخچه اقدامات قبلی نگاه کن. هرگز دکمه یا دستوری که قبلاً زدی و مجدداً به همین منو برگشته را دوباره تکرار نکن!\n"
    "۲. عدم کلیک روی دکمه‌های برگشت: هرگز دکمه‌های «بازگشت»، «برگشت»، «منوی قبل» یا 🔙 را کلیک نکن.\n"
    "۳. اگر دکمه شیشه‌ای وجود ندارد یا لینک‌ها در متن هستند:\n"
    "   - اگر دستوراتی مثل /dl_... یا کدی برای کیفیت/صوت درخواستی در متن آمده، اقدام send_text با آن دستور را بده.\n"
    "   - اگر لینکی در متن یا دکمه متنی برای دانلود آمده، اقدام follow_link با آن آدرس را بده.\n"
    "   - اگر ربات فهرستی از فیلم‌ها فرستاده و شماره خواسته (مثلاً: برای دانلود ۱ را بفرستید)، اقدام send_text با شماره را بده.\n"
    "۴. تطابق کیفیت: کیفیت درخواستی کاربر (480p یا 720p یا 1080p) را بر کیفیت‌های دیگر ترجیح بده.\n"
    "۵. تطابق صوت و زیرنویس: اگر کاربر زیرنویس خواسته (subtitled)، دکمه یا دستور زیرنویس را انتخاب کن و به هیچ وجه دوبله را نزن. اگر دوبله خواسته (dubbed)، دوبله را انتخاب کن.\n"
    "۶. اگر فایل به دست کاربر رسیده و قسمت بعدی وجود ندارد، اقدام done را اعلام کن.\n\n"
    "خروجی الزاماً باید فقط و فقط یک شیء JSON با ساختار زیر باشد بدون هیچ متن یا کلمه اضافی:\n"
    "{\n"
    '  "action": "click_button" | "send_text" | "follow_link" | "done" | "give_up",\n'
    '  "button_index": <شماره دکمه از 1 تا N در صورت click_button>,\n'
    '  "text": "<دستور یا متنی که باید به ربات ارسال شود در صورت send_text>",\n'
    '  "url": "<لینک مورد نظر در صورت follow_link>",\n'
    '  "reason": "<دلیل خلاصه در یک جمله>"\n'
    "}"
)


def format_nav_prompt(
    bot_messages: List[Any],
    req: Dict[str, Any],
    state: Dict[str, Any]
) -> Tuple[str, Dict[str, Any]]:
    """ساخت پرامپت ساختاریافته برای تصمیم‌گیری خودمختار هوش مصنوعی."""
    title = req.get("title") or "فیلم / سریال"
    quality = req.get("quality") or 720
    audio_req = req.get("audio")
    season = req.get("season")
    episode = req.get("episode")

    if audio_req == "subtitled":
        audio_str = "زیرنویس (فقط نسخه زیرنویس فارسی / SoftSub / HardSub)"
    elif audio_req == "dubbed":
        audio_str = "دوبله (فقط نسخه دوبله فارسی اختصاصی)"
    else:
        audio_str = audio_req or "دوبله یا زیرنویس (هرکدام موجود است)"

    s_str = f"فصل {season}" if season is not None else "نامشخص (اولین یا جدیدترین)"
    ep_str = "کل قسمت‌های فصل" if str(episode) == "all" else (f"قسمت {episode}" if episode is not None else "تک‌قسمتی / تمام قسمت‌ها")

    # بررسی پیام اخیر
    last_msg = bot_messages[-1] if bot_messages else None
    elements = extract_message_elements(last_msg) if last_msg else {
        "text": "", "buttons": [], "display_buttons": [], "commands": [], "codes": [], "links": [], "is_subscription": False
    }

    # دکمه‌های شیشه‌ای فعال (فیلتر اکید دکمه‌های بازگشت طبق استاندارد سیستم)
    display_btns = elements.get("display_buttons", [])
    buttons_text = []
    for idx, b in enumerate(display_btns, start=1):
        buttons_text.append(f"{idx}. [{b['text']}]")
    buttons_str = "\n".join(buttons_text) if buttons_text else "هیچ دکمه شیشه‌ای وجود ندارد."

    # دستورات متنی
    cmds_text = []
    for idx, cmd in enumerate(elements["commands"], start=1):
        cmds_text.append(f"- {cmd}")
    cmds_str = "\n".join(cmds_text) if cmds_text else "دستور اسلشی در متن یافت نشد."

    # لینک‌های داخل متن
    links_text = []
    for idx, l in enumerate(elements["links"], start=1):
        lbl = f" (برچسب: {l['label']})" if l['label'] else ""
        links_text.append(f"- {l['url']}{lbl}")
    links_str = "\n".join(links_text) if links_text else "لینکی در متن یافت نشد."

    history = state.get("history") or []
    history_str = "\n".join(f"گام {i+1}: {h}" for i, h in enumerate(history[-5:])) if history else "شروع ناوبری (گام اول)"

    files_count = state.get("files_count", 0)

    prompt = (
        f"🎯 **هدف و درخواست کاربر:**\n"
        f"- عنوان اثر: {title}\n"
        f"- کیفیت مورد نیاز: {quality}p\n"
        f"- نسخه صوتی/متنی: {audio_str}\n"
        f"- فصل: {s_str}\n"
        f"- قسمت: {ep_str}\n\n"
        f"📩 **متن آخرین پیام دریافت شده از ربات دانلود:**\n"
        f"«{elements['text'][:600]}»\n\n"
        f"🔘 **۱. دکمه‌های شیشه‌ای موجود:**\n{buttons_str}\n\n"
        f"⌨️ **۲. دستورات اسلش / کدهای داخل متن:**\n{cmds_str}\n\n"
        f"🔗 **۳. لینک‌های شناسایی‌شده:**\n{links_str}\n\n"
        f"📜 **تاریخچه اقدامات اخیر (برای پیشگیری از تکرار و لوپ):**\n{history_str}\n\n"
        f"📊 **وضعیت کنونی:** {files_count} فایل تا این لحظه دریافت شده است.\n\n"
        f"❓ **دستور:** دقیقاً اقدام بعدی چیست؟ فقط و فقط شیء JSON معتبر خروجی بده:"
    )

    return prompt, elements


def parse_ai_decision(raw_output: str, elements: Dict[str, Any], req: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """پارس امن پاسخ مدل و تبدیل به شیء تصمیم‌گیری استاندارد."""
    raw = (raw_output or "").strip()
    decision = {"action": "done", "reason": "پاسخ نامشخص"}
    pool = elements.get("display_buttons") or elements.get("buttons") or []

    # استخراج بلاک JSON
    json_match = re.search(r"\{[\s\S]*\}", raw)
    if json_match:
        try:
            data = json.loads(json_match.group(0))
            action = str(data.get("action", "")).strip().lower()
            reason = str(data.get("reason", "")).strip()

            if any(k in action for k in ("click", "button", "select")):
                b_idx = data.get("button_index")
                if b_idx is not None:
                    try:
                        b_int = int(b_idx)
                        if 1 <= b_int <= len(pool):
                            return {
                                "action": "click_button",
                                "button_index": b_int,
                                "button": pool[b_int - 1],
                                "reason": reason or f"انتخاب دکمه شماره {b_int}"
                            }
                    except (ValueError, TypeError):
                        pass

            elif any(k in action for k in ("send", "text", "command")):
                txt = str(data.get("text", "")).strip()
                if txt:
                    return {
                        "action": "send_text",
                        "text": txt,
                        "reason": reason or f"ارسال متن/دستور {txt}"
                    }

            elif any(k in action for k in ("follow", "link", "url")):
                url = str(data.get("url", "")).strip()
                if url:
                    return {
                        "action": "follow_link",
                        "url": url,
                        "reason": reason or f"دنبال کردن لینک {url}"
                    }

            elif any(k in action for k in ("done", "finish", "complete")):
                return {"action": "done", "reason": reason or "اتمام دانلود"}

            elif any(k in action for k in ("give_up", "fail", "not_found", "pay")):
                return {"action": "give_up", "reason": reason or "عدم دسترسی به فایل رایگان"}

        except Exception as e:
            log.debug("JSON parse error in parse_ai_decision: %s", e)

    # فال‌بک: اگر استخراج عدد ساده انجام شود (با تبدیل ارقام فارسی)
    raw_normalized = raw
    for p, a in _PERSIAN_DIGITS.items():
        raw_normalized = raw_normalized.replace(p, a)

    m_num = re.search(r"\b\d+\b", raw_normalized)
    if m_num and pool:
        val = int(m_num.group(0))
        if 1 <= val <= len(pool):
            return {
                "action": "click_button",
                "button_index": val,
                "button": pool[val - 1],
                "reason": f"فال‌بک عددی به دکمه {val}"
            }

    # فال‌بک دستور اسلش هوشمند
    if elements.get("commands"):
        chosen_cmd = match_best_command(elements.get("text", ""), elements["commands"], req)
        if chosen_cmd:
            return {
                "action": "send_text",
                "text": chosen_cmd,
                "reason": f"ارسال دستور اسلش {chosen_cmd}"
            }

    # فال‌بک تطابق دکمه با ترجیحات کاربر (کیفیت، صوت)
    if pool and req:
        target_q = req.get("quality")
        target_audio = req.get("audio")
        for idx, b in enumerate(pool, start=1):
            bt = (b.get("text") or "").lower()
            if target_q and str(target_q) in bt:
                return {
                    "action": "click_button",
                    "button_index": idx,
                    "button": b,
                    "reason": f"فال‌بک تطابق کیفیت {target_q}"
                }
            if target_audio == "subtitled" and any(k in bt for k in ("زیرنویس", "sub")):
                return {
                    "action": "click_button",
                    "button_index": idx,
                    "button": b,
                    "reason": "فال‌بک تطابق زیرنویس"
                }

    # فال‌بک به اولین دکمه پیشروی
    if pool:
        return {
            "action": "click_button",
            "button_index": 1,
            "button": pool[0],
            "reason": "فال‌بک به اولین گزینه پیشروی"
        }

    return decision


def decide_action_sync(
    bot_messages: List[Any],
    req: Dict[str, Any],
    state: Dict[str, Any]
) -> Dict[str, Any]:
    """تصمیم‌گیری همگام با هوش مصنوعی برای گام بعدی ناوبری ربات."""
    prompt, elements = format_nav_prompt(bot_messages, req, state)

    # اگر پیام اشتراک پولی است، بی‌درنگ توقف
    if elements.get("is_subscription"):
        return {"action": "give_up", "reason": "ربات نیاز به اشتراک پولی/VIP دارد."}

    try:
        raw_output = ai.ask_direct(prompt, system=NAV_SYSTEM_PROMPT)
    except Exception as e:
        log.warning("ai_nav ask_direct failed: %s", e)
        raw_output = ""

    decision = parse_ai_decision(raw_output, elements, req)
    log.info("[ai_nav] AI Decision: %s (Reason: %s)", decision.get("action"), decision.get("reason"))
    return decision


async def ai_decide_action(
    bot_messages: List[Any],
    req: Dict[str, Any],
    state: Dict[str, Any]
) -> Dict[str, Any]:
    """تصمیم‌گیری ناهمگام با هوش مصنوعی برای گام بعدی ناوبری ربات."""
    return await asyncio.to_thread(decide_action_sync, bot_messages, req, state)


# ==============================================================================
# سازگاری با توابع قبلی (Backward Compatibility)
# ==============================================================================

def format_buttons_list(buttons: List[Any]) -> str:
    lines = []
    for idx, b in enumerate(buttons, start=1):
        txt = (getattr(b, "text", "") or "").strip()
        lines.append(f"{idx}. [{txt}]")
    return "\n".join(lines)


def parse_choice(raw: str, buttons: List[Any]) -> Optional[int]:
    if not raw:
        return None
    s = raw.strip()
    for p, a in _PERSIAN_DIGITS.items():
        s = s.replace(p, a)
    count = len(buttons)
    m = re.search(r'\b\d+\b', s) or re.search(r'\d+', s)
    if m:
        val = int(m.group(0))
        if 1 <= val <= count:
            return val - 1
        if val == 0:
            return None
    low = s.lower()
    for i, b in enumerate(buttons):
        t = (getattr(b, "text", "") or "").strip().lower()
        if len(t) >= 3 and t in low:
            return i
    return None


def pick_button_sync(
    buttons: List[Any],
    bot_message: str,
    req: Dict[str, Any],
    state: Dict[str, Any]
) -> Optional[int]:
    if not buttons:
        return None
    if len(buttons) == 1:
        return 0

    # فیلتر اکید دکمه‌های بازگشت طبق نیازمندی سیستم
    forward_buttons = [b for b in buttons if not is_back_button(getattr(b, "text", "") or "")]
    active_buttons = forward_buttons if forward_buttons else buttons

    fake_msg = type("FakeMsg", (), {"message": bot_message, "buttons": [active_buttons], "entities": []})()
    decision = decide_action_sync([fake_msg], req, state)
    if decision.get("action") == "click_button":
        chosen_b_dict = decision.get("button")
        if chosen_b_dict and "raw" in chosen_b_dict:
            chosen_raw = chosen_b_dict["raw"]
            if chosen_raw in buttons:
                return buttons.index(chosen_raw)
        b_idx = decision.get("button_index", 1) - 1
        if 0 <= b_idx < len(active_buttons):
            chosen_raw = active_buttons[b_idx]
            if chosen_raw in buttons:
                return buttons.index(chosen_raw)
            return b_idx

    if active_buttons:
        return buttons.index(active_buttons[0])
    return 0


async def ai_pick_button(
    buttons: List[Any],
    bot_message: str,
    req: Dict[str, Any],
    state: Dict[str, Any]
) -> Optional[int]:
    return await asyncio.to_thread(pick_button_sync, buttons, bot_message, req, state)
