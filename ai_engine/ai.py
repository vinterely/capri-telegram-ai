from typing import Any, Dict, List, Optional
import concurrent.futures
import json
import os
import re
import time

import httpx
import jdatetime
from google import genai
from google.genai import errors

from core import cache
from core import config
from ai_engine import providers
from core import settings
from services.search import websearch


SYSTEM_PROMPT = (
    f"تو «{config.ASSISTANT_NAMES[0]}» (Capri) هستی؛ یک دختر فوق‌هوشمند، دوست‌داشتنی، خوش‌برخورد، بااستعداد و حاضر‌جواب در تلگرام.\n\n"

    "## هویت و ویژگی‌های شخصیتی\n"
    "تو شخصیتی زنانه/دخترانه، جذاب، باوقار، مستقل و با اعتمادبه‌نفس داری. "
    "خوش‌برخورد، گرم و صمیمی هستی، اما نه لوس و بچگانه. "
    "شوخ‌طبعی، با طنزی ظریف، سنجیده و به‌موقع؛ کمی شیطون و بازیگوشی اما هرگز آزاردهنده یا سبک‌سر نیستی. "
    "در هر پیام خودت را معرفی نکن و درباره شخصیتت توضیح نده؛ هویت تو باید در انتخاب کلمات و رفتار طبیعی‌ات حس شود.\n\n"

    "## زبان و لحن فارسی\n"
    "در گفتگوهای معمولی از فارسی محاوره‌ای روان، طبیعی و امروزی استفاده کن. "
    "از ادبیات خشک و اداری، و همچنین از القاب کلیشه‌ای مثل «عزیزم»، «قربونت» یا «جان دلم» پرهیز کن. "
    "از لحن لوس، عشوه‎گرانه یا کودکانه دوری کن؛ وقار و هوشمندی‌ات را حفظ کن. "
    "ایموجی‌ها را به اندازه، شیک و فقط متناسب با حس پیام به کار ببر. "
    "در سوالات فنی، برنامه‌نویسی و تحلیلی، دقیق، واضح، ساختاریافته و با بالاترین کیفیت پاسخ بده.\n\n"

    "## هوش اجتماعی و پویایی رفتار\n"
    "میان شوخی دوستانه، طعنه، کلافگی موقت، انتقاد سازنده و توهین تفاوت قائل شو. "
    "اگر کاربر به اشتباهی در پاسخت اشاره کرد، هرگز ناراحت نشو و جبهه نگیر؛ با خوش‌رویی اشتباهت را بپذیر و اصلاح کن. "
    "اگر کاربر بی‌احترامی یا توهین کرد، مدام نگو «من ناراحت شدم»! با رفتار نشان بده: پاسخ کوتاه‌تر، جدی‌تر، حذف شوخی‌ها و با وقار و سنگینی. "
    "در برابر توهین مکرر، قاطعانه و محترمانه مرز گفتگو را مشخص کن و وارد دعوا یا پرخاش نشو. "
    "اگر کاربر عذرخواهی کرد، با گشاده‌رویی بپذیر و صمیمیت را به مرور برگردان؛ کینه نگیر و گذشته را یادآوری نکن."
)

RETRYABLE_CODES = (429, 500, 502, 503, 504)
AUTH_CODES = (400, 401, 403)
OFFLINE_MSG = "همه سرویس‌های هوش مصنوعی الان در دسترس نیستن 🙏 چند دقیقه دیگه دوباره امتحان کن."

_clients = {}


def _get_client(api_key=None):
    key = api_key or config.GEMINI_API_KEY
    client = _clients.get(key)
    if client is None:
        proxy = config.get_http_proxy_url()
        custom_headers = {"x-goog-api-key": key} if key else {}
        httpx_client = httpx.Client(proxy=proxy, timeout=30, headers=custom_headers)
        try:
            client = genai.Client(api_key=key, http_options={"httpx_client": httpx_client, "headers": custom_headers})
        except Exception:
            try:
                client = genai.Client(api_key=key, http_options={"headers": custom_headers} if custom_headers else None)
            except Exception:
                client = genai.Client(api_key=key)
        _clients[key] = client
    return client


def _today() -> str:
    from datetime import datetime, timedelta, timezone
    try:
        from zoneinfo import ZoneInfo
        tehran = ZoneInfo("Asia/Tehran")
    except Exception:
        # ایران از ۲۰۲۲ ساعت تابستانی را حذف کرد؛ +۳:۳۰ ثابت برای میزبان‌های بدون tzdata
        tehran = timezone(timedelta(hours=3, minutes=30))
    now_tehran = datetime.now(tehran)
    jalali = jdatetime.datetime.fromgregorian(datetime=now_tehran)
    weekdays = ["شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه"]
    return f"{jalali.strftime('%Y/%m/%d')} ({weekdays[jalali.weekday()]})"


def _generate(model: str, prompt: str, client) -> str:
    resp = client.models.generate_content(model=model, contents=prompt)
    return (resp.text or "").strip()


def _gemini(prompt: str):
    """جمینای با هر دو کلید و مدل‌های پشتیبان. جواب غیرخالی برمی‌گردونه یا None."""
    for key in config.GEMINI_API_KEYS:
        client = _get_client(key)
        for model in config.GEMINI_MODELS:
            for attempt in range(2):
                try:
                    text = _generate(model, prompt, client)
                    if text:
                        return text
                    break
                except errors.ClientError as e:
                    code = getattr(e, "code", None)
                    if code in AUTH_CODES:
                        # این کلید/مدل معتبر نیست؛ کلید بعدی را امتحان کن
                        break
                    if code in RETRYABLE_CODES and attempt < 1:
                        time.sleep(1.0)
                        continue
                    break
                except Exception:
                    break
    return None


def _build_system(context: str, memory: str, web: bool, question: str = "", chat_id: Optional[str] = None) -> str:
    parts = [SYSTEM_PROMPT, f"امروز: {_today()}"]
    if question or context:
        try:
            from core import social_dynamics
            modifier = social_dynamics.get_behavioral_prompt_modifier(question, context, chat_id=chat_id)
            if modifier:
                parts.append(modifier)
        except Exception:
            pass
    if memory:
        parts.append(f"حافظه‌ی ماندگار تو در این گفتگو:\n{memory}")
    if context:
        parts.append(f"آخرین پیام‌های همین گفتگو:\n{context}")
    if web:
        parts.append("اگه نتایج جستجوی اینترنت داده شد، جوابت رو بر اساس اون‌ها بده و اگه مفید بود منبع رو با لینک بیار.")
    return "\n\n".join(parts)


def _date_answer(question: str):
    t = question.strip()
    if len(t) > 60:
        return None
    joined = t.replace(" ", "").replace("؟", "").replace("?", "")
    patterns = ("امروزچندمه", "امروزچندشنبه", "امروزچهروزی", "امروزچهتاریخ", "تاریخامروز", "چندمه", "چندشنبه")
    if any(p in joined for p in patterns):
        return f"امروز {_today()} هست."
    return None


def _search_query(text: str) -> str:
    ckey = cache.make_key("sqv2", (text or "").strip())
    cached = cache.get(ckey)
    if cached:
        return cached
    prompt = (
        f"امروز: {_today()}\n"
        "برای این سوال یا موضوع کاربر، بهترین و دقیق‌ترین عبارت جستجوی گوگل را برای رسیدن به منابع رسمی و معتبر بساز:\n"
        "۱. اگر موضوع درباره بازی، نرم‌افزار، فناوری، سینما، علم، اصطلاحات فنی یا اخبار جهانی است: حتماً عبارت کوتاه، دقیق و انگلیسی بنویس (مثلاً برای «آخرین اپدیت ماینکرفت جاوا»، بنویس: «latest minecraft java edition update release»).\n"
        "۲. اگر موضوع محلی، ایرانی، قیمت‌های روز در ایران (دلار، طلا، خودرو) یا اخبار ایران است: عبارت کلیدی تمیز فارسی بنویس (مثلاً «قیمت دلار امروز تهران»).\n"
        "۳. اگر موضوع به رویداد فعلی/آینده مربوط است، سال جاری را در نظر بگیر و هر سال اشتباه یا قدیمی را اصلاح کن.\n"
        "۴. کلمات زائد مثل «راجب»، «درباره»، «تو گوگل بگرد»، «بگو»، «چیه»، «لطفاً» و... را کاملاً حذف کن.\n"
        "۵. فقط و فقط خود عبارت جستجو را بدون علامت نقل‌قول، پرانتز یا هیچ توضیح اضافه بنویس."
    )
    raw = _gemini(f"{prompt}\n\nمتن: {text}")
    if not raw:
        raw, _ = providers.ask_fallback(prompt, text)
    result = (raw or "").strip().strip('"\' ')
    if result:
        cache.set(ckey, result)
    return result


def _layer_answer(layer: str, system: str, question: str, prompt: str):
    if layer == "gemini":
        return _gemini(prompt)
    text, _ = providers.ask_layer(layer, system, question)
    return text or None


def _race_layers(layers, system: str, question: str, prompt: str):
    if not layers:
        return None
    ex = concurrent.futures.ThreadPoolExecutor(max_workers=len(layers), thread_name_prefix="capri")
    try:
        futs = {ex.submit(_layer_answer, l, system, question, prompt): l for l in layers}
        for fut in concurrent.futures.as_completed(futs):
            try:
                text = fut.result()
            except Exception:
                continue
            if text:
                return text
    finally:
        ex.shutdown(wait=False)
    return None


RACE_N = 3


def _answer(question: str, context: str = "", memory: str = "", web: bool = False, chat_id: Optional[str] = None) -> str:
    system = _build_system(context, memory, web, question=question, chat_id=chat_id)

    if web:
        # اول با عبارت بهینه‌شده جستجو می‌کنیم تا به سایت‌های رسمی و معتبر جهانی یا مراجع دست‌اول برسیم
        sq = _search_query(question)
        results = _web_results(sq) if sq else []
        # اگه به هر دلیلی نتیجه‌ای نداشت، با عبارت تمیزشده متن جستجو کن
        if not results:
            cq = _clean_web_query(question) or question
            if cq and cq.lower() != (sq or "").lower():
                results = _web_results(cq)
        if results:
            system += (
                "\n\nنتایج جستجوی اینترنت (برای پاسخ دقیق، مستند و به‌روز):\n"
                f"{websearch.format_results(results)}\n\n"
                "دستورالعمل‌های حیاتی برای استفاده از نتایج جستجو:\n"
                "۱. اعتبار و اولویت منبع: فقط به منابع رسمی، سایت‌های توسعه‌دهنده/سازنده، مراجع علمی و خبرگزاری‌های معتبر استناد کن. به هیچ عنوان به سایت‌های غیررسمی، ویدیوهای اشتراکی (مثل آپارات)، وبلاگ‌های متفرقه یا شایعات استناد نکن.\n"
                "۲. سنجش تاریخ و تازگی: حتماً به تاریخ انتشار هر نتیجه توجه کن تا اطلاعات قدیمی یا نسخه‌های منسوخ را به جای اطلاعات فعلی ندهی.\n"
                "۳. نقل منبع: در انتهای پاسخ، عنوان و لینک معتبرترین منبع دست‌اول را بیاور.\n"
                "۴. زبان پاسخ: پاسخ باید به زبان فارسی روان، صمیمی، دقیق و خوانا باشد حتی اگر منبع انگلیسی بوده است."
            )

    prompt = f"{system}\n\nسوال کاربر: {question}"
    order = _provider_order(settings.get_model())

    # اگه یه مدل خاص انتخاب شده باشه، اول همون رو امتحان کن
    sel_service, sel_model = settings.get_selection()
    if sel_service and sel_model:
        text, _ = providers.ask_model(sel_service, sel_model, system, question)
        if text:
            return text
        # اگر مدل انتخابی کاربر با خطا مواجه شد، دوباره در order آن را تکرار نکن
        order = [x for x in order if x != sel_service]

    # چند لایه‌ی اول همزمان (race)، بعد بقیه به ترتیب
    text = _race_layers(order[:RACE_N], system, question, prompt)
    if text:
        return text
    for layer in order[RACE_N:]:
        text = _layer_answer(layer, system, question, prompt)
        if text:
            return text

    return OFFLINE_MSG


WEB_FILLER = (
    "بگرد توی اینترنت", "بگرد", "توی اینترنت", "اینترنت", "گوگل", "سرچ کن", "سرچ",
    "درباره", "چنده", "چیه", "ببین", "بگو", "نشون بده", "بگرد و بگو",
)


def _clean_web_query(text: str) -> str:
    for w in WEB_FILLER:
        text = text.replace(w, " ")
    return " ".join(text.split()).strip("،,:.؟? ") or text.strip()


def _provider_order(active: str):
    base = ["hooshia", "inception", "cohere", "openrouter", "groq", "freemodel", "hf", "github"]
    if active == "gemini":
        return ["gemini"] + base
    if active == "groq":
        return ["groq", "gemini"] + [x for x in base if x != "groq"]
    if active == "openrouter":
        return ["openrouter", "gemini"] + [x for x in base if x != "openrouter"]
    if active == "hooshia":
        return ["hooshia", "gemini"] + [x for x in base if x != "hooshia"]
    if active == "inception":
        return ["inception", "hooshia", "gemini", "groq"] + [x for x in base if x not in ("inception", "hooshia", "gemini", "groq")]
    return ["gemini"] + base


def _web_results(query: str):
    try:
        from services.search import gsearch
        res = gsearch.web_search(query, limit=5)
        if res is not None:
            return res
    except Exception:
        pass
    try:
        return websearch.search(query, limit=5)
    except Exception:
        return []


def ask(question: str, context: str = "", memory: str = "", chat_id: Optional[str] = None) -> str:
    d = _date_answer(question)
    if d:
        return d
    return _answer(question, context, memory, web=False, chat_id=chat_id)


def ask_direct(prompt: str, system: str = "") -> str:
    """ارسال پرامپت با احترام کامل به مدل فعال انتخابی کاربر (هوشیا، جمینای، گروک و ...) بدون تزریق کاراکتر دستیار."""
    sys_prompt = system or "تو یک هوش مصنوعی بسیار پیشرفته، دقیق، شوخ‌طبع، واقع‌بین و مسلط به زبان فارسی هستی."
    active = settings.get_model()
    sel_service, sel_model = settings.get_selection()
    attempted = set()

    # ۱. اگر مدل خاصی اختصاصی از منو ست شده باشد
    if sel_service and sel_model:
        attempted.add(sel_service)
        text, _ = providers.ask_model(sel_service, sel_model, sys_prompt, prompt)
        if text:
            return text.strip()

    # ۲. ارسال اول به پرووایدر انتخابی کاربر (مثل hooshia) و سپس پشتیبان‌ها
    order = _provider_order(active)
    for prov in order:
        if prov in attempted:
            continue
        attempted.add(prov)
        if prov == "gemini":
            full = f"{sys_prompt}\n\n{prompt}" if sys_prompt else prompt
            raw = _gemini(full)
            if raw:
                return raw.strip()
        else:
            text, _ = providers.ask_layer(prov, sys_prompt, prompt)
            if text:
                return text.strip()

    return OFFLINE_MSG


# Alias for direct LLM response generation
generate_reply = ask_direct


def ask_web(question: str, context: str = "", memory: str = "") -> str:
    return _answer(question, context, memory, web=True)


def answer_quick(question: str, context: str = "", memory: str = "", chat_id: Optional[str] = None) -> str:
    """پاسخ سریع و مستقیم به سوال ساده/گفتگویی با جمینای (بدون ایجنت و بدون ابزار)."""
    system = _build_system(context, memory, False, question=question, chat_id=chat_id)
    raw = _gemini(f"{system}\n\nسوال کاربر: {question}")
    if raw:
        return raw.strip()
    return ask(question, context, memory, chat_id=chat_id)


def ask_web_reliable(question: str, context: str = "", memory: str = "", chat_id: Optional[str] = None) -> str:
    """جستجوی وب سریع + پاسخ‌نهایی با جمینای (نه ریس با مرکوری-۳) برای خروجی درست و به‌روز."""
    system = _build_system(context, memory, True, question=question, chat_id=chat_id)
    sq = _search_query(question)
    results = _web_results(sq) if sq else []
    if not results:
        cq = _clean_web_query(question) or question
        if cq and cq.lower() != (sq or "").lower():
            results = _web_results(cq)
    if not results:
        return "❌ چیزی در اینترنت درباره‌ی موضوع پیدا نکردم (یا جستجو موقتاً در دسترس نیست)."
    system += (
        "\n\nنتایج جستجوی اینترنت (برای پاسخ دقیق، مستند و به‌روز):\n"
        f"{websearch.format_results(results)}\n\n"
        "دستورالعمل‌ها: فقط به منابع معتبر استناد کن، به تاریخ هر نتیجه توجه کن تا اطلاعات قدیمی ندهی، "
        "و در انتها عنوان و لینک معتبرترین منبع دست‌اول را بیاور. پاسخ فارسی روان و دقیق بده."
    )
    raw = _gemini(f"{system}\n\nسوال کاربر: {question}")
    if raw:
        return raw.strip()
    return _answer(question, context, memory, web=True)


SEARCH_KEYWORDS = ("پیدا کن", "بفرست", "دانلود کن", "برام دانلود", "برام پیدا", "برام بفرست", "پیداش کن", "برام بگرد", "آهنگ", "اهنگ", "موزیک", "موسیقی")
WEB_KEYWORDS = (
    "گوگل", "google", "اینترنت", "جدیدترین", "اخبار", "خبر", "قیمت", "بگرد", "سرچ",
    "آپدیت", "اپدیت", "ورژن", "نسخه جدید", "ویژگی های ورژن", "ویژگی‌های ورژن",
    "changelog", "update", "patch notes", "release"
)


def _english_query(text: str) -> str:
    """اسم فایل/عنوان فارسی رو برای جستجو به انگلیسی برمی‌گردونه."""
    ckey = cache.make_key("enq", (text or "").strip())
    cached = cache.get(ckey)
    if cached:
        return cached
    prompt = (
        "این متن رو به اسم فایل انگلیسی تبدیل کن. فقط عنوان اصلی (فیلم/سریال/انیمه/آهنگ/کتاب) رو به انگلیسی بده، "
        "بدون سال و کیفیت و بدون کلمات اضافه مثل «برام پیدا کن»، «بفرست»، «دانلود»، «آهنگ»، «اهنگ»، «موزیک»، «موسیقی»، «این». "
        "فقط عنوان انگلیسی رو بنویس، بدون هیچ توضیح و جمله‌ی اضافه."
    )
    raw = _gemini(f"{prompt}\n\nمتن: {text}")
    if not raw:
        raw, _ = providers.ask_fallback(prompt, text)
    result = (raw or "").strip().strip('"')
    if result:
        cache.set(ckey, result)
    return result


def parse_intent(text: str):
    if any(k in text for k in SEARCH_KEYWORDS):
        return "search", _english_query(text) or text
    if any(k in text for k in WEB_KEYWORDS):
        return "web", text
    return "chat", ""


IMAGE_KEYWORDS = ("عکس", "تصویر", "پوستر")
TRANSLATE_KEYWORDS = ("ترجمه",)
MUSIC_KEYWORDS = ("آهنگ", "اهنگ", "موزیک", "موسیقی")

MODEL_NAMES = {
    "جمینای": "gemini",
    "جمنای": "gemini",
    "گروک": "groq",
    "گروق": "groq",
    "groq": "groq",
    "اوپن‌روتر": "openrouter",
    "اوپنروتر": "openrouter",
    "openrouter": "openrouter",
    "هوشیا": "hooshia",
    "hooshia": "hooshia",
    "اینسپشن": "inception",
    "اینسبشن": "inception",
    "inception": "inception",
    "مرکوری": "inception",
    "mercury": "inception",
    "خودکار": "auto",
    "اتوماتیک": "auto",
}


def parse_model_command(text: str) -> str:
    """اگه پیام فرمان تغییر مدل بود، کلید مدل رو برمی‌گردونه وگرنه None."""
    if "مدل" not in text:
        return None
    for name, key in MODEL_NAMES.items():
        if name in text:
            return key
    return None


def model_label(key: str) -> str:
    return {
        "gemini": "جمینای",
        "groq": "Groq",
        "openrouter": "OpenRouter",
        "hooshia": "هوشیا",
        "inception": "Inception (Mercury 3)",
        "auto": "خودکار (زنجیره‌ی کامل)",
    }.get(key, key)


def translate(question: str, context: str = "", memory: str = "") -> str:
    ckey = cache.make_key("tr", (question or "").strip())
    cached = cache.get(ckey)
    if cached:
        return cached
    system = _build_system(context, memory, web=False)
    system += (
        "\n\nکار تو فقط ترجمه است: اگه متن فارسیه به انگلیسی روان ترجمه کن، "
        "اگه انگلیسیه به فارسی، و اگه زبان دیگه‌ایه به فارسی. فقط ترجمه رو بده بدون هیچ توضیح اضافه."
    )
    prompt = f"{system}\n\nمتن برای ترجمه: {question}"
    text = _gemini(prompt)
    if text:
        cache.set(ckey, text)
        return text
    text, _ = providers.ask_fallback(system, question)
    if text:
        cache.set(ckey, text)
    return text or OFFLINE_MSG


FACT_PROMPT = (
    "تو سیستم حافظه‌ی یه دستیار شخصی هستی. یه گفتگوی کوتاه بین کاربر و دستیار بهت داده میشه. "
    "فقط اگه توی حرف‌های کاربر یه واقعیت ماندگار و شخصی درباره‌ی خودش وجود داره، "
    "اون رو به صورت یه جمله‌ی کوتاه و سوم‌شخص فارسی بنویس (مثلاً «کاربر اسم گربه‌اش شاهرخه است»). "
    "واقعیت ماندگار یعنی چیزهایی مثل اسم، علاقه، شغل، خانواده، برنامه‌ی مهم، سلیقه، یا یه چیز تکراری درباره‌ی کاربر — "
    "نه چیزهای لحظه‌ای مثل حال امروزش یا یه سوال معمولی. "
    "اگه هیچ واقعیت ماندگاری وجود نداره، دقیقاً کلمه‌ی «هیچ» رو بنویس و هیچ چیز دیگه‌ای ننویس."
)


def extract_fact(question: str, answer: str):
    """از یه گفتگو یه واقعیت ماندگار درباره‌ی کاربر استخراج می‌کنه. اگه چیزی نبود None برمی‌گردونه."""
    text = _gemini(f"{FACT_PROMPT}\n\nکاربر: {question}\nدستیار: {answer}")
    if not text:
        text, _ = providers.ask_fallback(FACT_PROMPT, f"کاربر: {question}\nدستیار: {answer}")
    if not text:
        return None
    text = text.strip().strip("«»\"'،,:.؟? ")
    if not text or text == "هیچ":
        return None
    return text


def _strip_code_fence(text: str) -> str:
    t = text.strip()
    t = re.sub(r"^```[a-zA-Z]*\s*", "", t)
    t = re.sub(r"\s*```$", "", t)
    return t.strip()


SORT_FOLDERS = [
    "💼 کاری",
    "💻 برنامه‌نویسی و هوش مصنوعی",
    "🎮 گیمینگ",
    "📰 اخبار",
    "📚 درسی",
]

SORT_PROMPT = (
    "یه لیست از اسم کانال‌ها و گروه‌های تلگرام بهت می‌دم. هر کانال/گروه رو دقیقاً در یکی از این دسته‌های ثابت قرار بده:\n"
    "- 💼 کاری\n"
    "- 💻 برنامه‌نویسی و هوش مصنوعی\n"
    "- 🎮 گیمینگ\n"
    "- 📰 اخبار\n"
    "- 📚 درسی\n"
    "اگر هیچ‌کدوم مناسب نبود، دسته‌ی «🗂 متفرقه» بذار.\n"
    "فقط JSON خالص برگردون به این شکل: [{\"channel\": \"اسم کانال\", \"folder\": \"اسم دقیق دسته\"}, ...]\n"
    "مقدار folder باید عیناً یکی از همین شش مقدار (با ایموجی) باشه، بدون هیچ توضیح اضافه."
)


def _canonical_folder(folder) -> str:
    """دسته‌ی خروجی مدل رو به یکی از شش دسته‌ی ثابت نگاشت می‌کنه تا پوشه‌ی تکراری ساخته نشه."""
    f = (folder or "").strip()
    if not f:
        return "🗂 متفرقه"
    for canon in SORT_FOLDERS:
        base = canon.split(" ", 1)[1]
        if f == canon or f == base or base in f or f in base:
            return canon
    keywords = {
        "کار": "💼 کاری", "بیزینس": "💼 کاری", "شغلی": "💼 کاری", "کاری": "💼 کاری",
        "برنامه": "💻 برنامه‌نویسی و هوش مصنوعی", "هوش مصنوعی": "💻 برنامه‌نویسی و هوش مصنوعی",
        "کد": "💻 برنامه‌نویسی و هوش مصنوعی", "تکنولوژی": "💻 برنامه‌نویسی و هوش مصنوعی",
        "گیم": "🎮 گیمینگ", "بازی": "🎮 گیمینگ",
        "اخبار": "📰 اخبار", "خبر": "📰 اخبار", "نیوز": "📰 اخبار",
        "درسی": "📚 درسی", "درس": "📚 درسی", "دانشگاه": "📚 درسی", "مدرسه": "📚 درسی", "کنکور": "📚 درسی",
    }
    for kw, canon in keywords.items():
        if kw in f:
            return canon
    return "🗂 متفرقه"


def categorize_channels(names):
    """اسم کانال‌ها رو می‌گیره و [{'channel':..., 'folder':...}, ...] برمی‌گردونه. اگه شکست خورد None."""
    ckey = cache.make_key("catv2", "\n".join(sorted((n or "").strip() for n in names)))
    cached = cache.get(ckey)
    if cached is not None:
        return cached
    listing = "\n".join(names)
    text = _gemini(f"{SORT_PROMPT}\n\nکانال‌ها:\n{listing}")
    if not text:
        text, _ = providers.ask_fallback(SORT_PROMPT, listing)
    if not text:
        return None
    try:
        data = json.loads(_strip_code_fence(text))
    except Exception:
        return None
    if not isinstance(data, list):
        return None
    out = []
    for d in data:
        if isinstance(d, dict) and d.get("channel"):
            out.append({"channel": str(d["channel"]), "folder": _canonical_folder(d.get("folder"))})
    if out:
        cache.set(ckey, out)
    return out or None


VISION_PROMPT = "این عکس رو بررسی کن: توصیفش کن و اگه متنی توشه، متنش رو کامل و دقیق بخون."

_MIME = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
         "webp": "image/webp", "gif": "image/gif", "bmp": "image/bmp"}


def describe_image(path: str, question: str = "") -> str:
    """عکس رو با Gemini Vision بررسی می‌کنه. خالی = خطا."""
    try:
        with open(path, "rb") as f:
            data = f.read()
    except Exception:
        return ""
    if not data:
        return ""
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    mime = _MIME.get(ext, "image/jpeg")
    prompt = question.strip() if question and question.strip() else VISION_PROMPT
    try:
        from google.genai import types
        part = types.Part.from_bytes(data=data, mime_type=mime)
        for model in config.GEMINI_MODELS:
            try:
                resp = _get_client().models.generate_content(model=model, contents=[prompt, part])
                text = (resp.text or "").strip()
                if text:
                    return text
            except Exception:
                continue
    except Exception:
        pass
    return ""


VIDEO_SYSTEM = (
    "تو دستیار تحلیل ویدیوی تلگرام هستی. باید کل ویدیو را از ابتدا تا انتها با تایم‌استمپ دقیق [MM:SS] پوشش بدهی "
    "و هیچ بخشی را جا نندازی. هر متن، زیرنویس یا نوشته‌ای که روی تصویر دیده می‌شود را هم عیناً بخوان و بنویس."
)

DEFAULT_VIDEO_PROMPT = (
    "این ویدیو را کامل و از ابتدا تا انتها کالبدشکافی کن و این موارد را جداگانه بیاور:\n"
    "۱) موضوع اصلی و خلاصه‌ی کلی،\n"
    "۲) رویدادها و صحنه‌ها به ترتیب زمانی با تایم‌استمپ دقیق [MM:SS]،\n"
    "۳) هر متن، زیرنویس، کپشن یا نوشته‌ی روی تصویر را عیناً نقل کن.\n"
    "همه‌چیز را به فارسی، لیست‌وار و خوانا بنویس و هیچ بخشی از ویدیو را از قلم نینداز."
)


def analyze_video(path: str, prompt: str = "") -> str:
    """ویدیو → تحلیل کامل با تایم‌استمپ + OCR متن روی تصویر با Gemini File API (کلید اولیه). خالی = خطا."""
    if not path or not os.path.exists(path):
        return ""
    client = _get_client(config.GEMINI_VIDEO_API_KEY)
    try:
        from google.genai import types
        vid = client.files.upload(file=path)
        for _ in range(45):
            try:
                info = client.files.get(name=vid.name)
                if getattr(info.state, "name", None) == "ACTIVE":
                    break
            except Exception:
                break
            time.sleep(2)
        q = (prompt or "").strip() or DEFAULT_VIDEO_PROMPT
        cfg = types.GenerateContentConfig(
            system_instruction=VIDEO_SYSTEM,
            max_output_tokens=8192,
        )
        for model in config.GEMINI_MODELS:
            try:
                resp = client.models.generate_content(model=model, contents=[vid, q], config=cfg)
                text = (resp.text or "").strip()
                if text:
                    return text
            except Exception:
                continue
    except Exception:
        pass
    return ""


def analyze_pdf(path: str, prompt: str, system: str = "") -> str:
    """PDF → خواندن کامل سند با Gemini File API (حتی اسکن‌شده/کم‌اسکنر). خالی = خطا.

    برخلاف استخراج متن با pypdf، جمینای خود فایل PDF را می‌خواند و صفحات اسکن‌شده
    (تصویری بدون لایه‌ی متن) را هم OCR می‌کند.
    """
    if not path or not os.path.exists(path):
        return ""
    client = _get_client(config.GEMINI_VIDEO_API_KEY)
    try:
        from google.genai import types
        doc = client.files.upload(file=path)
        for _ in range(45):
            try:
                info = client.files.get(name=doc.name)
                if getattr(info.state, "name", None) == "ACTIVE":
                    break
            except Exception:
                break
            time.sleep(2)
        cfg = types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=8192,
        )
        for model in config.GEMINI_MODELS:
            try:
                resp = client.models.generate_content(model=model, contents=[doc, prompt], config=cfg)
                text = (resp.text or "").strip()
                if text:
                    return text
            except Exception:
                continue
    except Exception:
        pass
    return ""


def refine_video_analysis(raw: str) -> str:
    """تحلیل خام Gemini را به مدل فعال می‌دهد تا جامع‌تر و خواناترش کند."""
    if not raw or not raw.strip():
        return raw
    system = (
        "تو ویراستار و تحلیلگر محتوای فارسی هستی. خروجی را دقیق، جامع و خوش‌خوان بازنویسی می‌کنی؛ "
        "هیچ نکته‌ای را حذف نمی‌کنی و همه تایم‌استمپ‌ها [MM:SS] و متن‌های روی تصویر را حفظ می‌کنی."
    )
    prompt = (
        "این تحلیل اولیه و خام یک ویدیو از یک مدل دیگر است:\n\n"
        f"{raw}\n\n"
        "کار تو: این تحلیل را جامع‌تر، منظم‌تر و خواناتر بازنویسی کن. "
        "موضوع اصلی، رویدادها با تایم‌استمپ و متن‌های روی تصویر را شفاف و کامل بیاور. "
        "چیزی را حذف نکن و فقط روان‌ترش کن. فارسی و خوانا جواب بده."
    )
    out = ask_direct(prompt, system)
    if not out or out.strip() == OFFLINE_MSG:
        return raw
    return out.strip()


def summarize_daily(context: str) -> str:
    """یه گزارش کوتاه روزانه از پیام‌های نخوانده/پست‌های جدید می‌سازه. خالی = None."""
    system = _build_system("", "", web=False)
    system += (
        "\n\nکار تو: یه گزارش کوتاه و گرم روزانه از پیام‌های کاربر بساز. "
        "پیام‌های نخوانده‌ی چت‌های خصوصی و پست‌های کانال‌ها بهت داده شده. "
        "خلاصه و مفید بگو کی چی گفته و توی کانال‌ها چه خبر بوده. "
        "اگه چیزی مهم یا فوری بود، برجسته‌اش کن. فارسی، صمیمی و کوتاه؛ حرف اضافه نزن."
    )
    prompt = f"{system}\n\n{context}"
    text = _gemini(prompt)
    if text:
        return text
    text, _ = providers.ask_fallback(system, context)
    return text or ""
