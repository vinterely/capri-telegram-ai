"""کاتالوگ مدل‌ها + تشخیص دستور طبیعی انتخاب مدل با پشتیبانی از UID و ارائه‌دهندگان جدید."""

import re
from ai_engine import provider_xkiro
from ai_engine import provider_bai
from ai_engine import provider_anyapi
from ai_engine import provider_openrouter

GROQ = [
    {"uid": "g1", "id": "qwen/qwen3.8-27b", "name": "Qwen 3.8 27B",
     "desc": "متعادل و بسیار سریع؛ پاسخ‌گویی عمومی و استدلال عالی", "cat": "speed", "ctx": "128K"},
    {"uid": "g2", "id": "openai/gpt-oss-120b", "name": "GPT-OSS 120B",
     "desc": "پرچمدار Groq؛ استدلال عمیق و کارهای پیچیده و برنامه‌نویسی", "cat": "reasoning", "ctx": "128K"},
    {"uid": "g3", "id": "openai/gpt-oss-20b", "name": "GPT-OSS 20B",
     "desc": "سبک‌تر و فوق‌سریع برای کارهای روزمره", "cat": "speed", "ctx": "128K"},
]

HOOSHIA = [
    {"uid": "h1", "id": "GLM-4.5-Flash", "name": "GLM 4.5 Flash",
     "desc": "مدل سریع و سبک هوشیا؛ پاسخ‌گویی پرسرعت و درک روان فارسی", "cat": "speed", "ctx": "128K"},
    {"uid": "h2", "id": "GLM-4.6V-Flash", "name": "GLM 4.6V Flash (Vision)",
     "desc": "مدل چندوجهی هوشیا با قابلیت تحلیل تصاویر، عکس و اسناد", "cat": "vision", "ctx": "128K"},
    {"uid": "h3", "id": "GLM-4.7-Flash", "name": "GLM 4.7 Flash",
     "desc": "نسخه پیشرفته هوشیا با قدرت استدلال عمیق‌تر و دقت بالا در فارسی", "cat": "reasoning", "ctx": "128K"},
]

INCEPTION = [
    {"uid": "i1", "id": "mercury-3", "name": "Mercury 3",
     "desc": "فوق‌سریع (Diffusion LLM) با پشتیبانی کامل ابزارها؛ پاسخ سریع برای ایجنت", "cat": "speed", "ctx": "128K"},
]

OPENROUTER = provider_openrouter.MODELS
XKIRO = provider_xkiro.MODELS
BAI = provider_bai.MODELS
ANYAPI = provider_anyapi.MODELS

ALL_SERVICES = {
    "xkiro": XKIRO,
    "bai": BAI,
    "anyapi": ANYAPI,
    "openrouter": OPENROUTER,
    "groq": GROQ,
    "hooshia": HOOSHIA,
    "inception": INCEPTION,
}

# نقشه‌ی سراسری UID به مدل
UID_MAP = {}
for srv, lst in ALL_SERVICES.items():
    for item in lst:
        uid = item.get("uid", "").lower()
        if uid:
            UID_MAP[uid] = (srv, item["id"], item)

CATEGORIES = {
    "reasoning": "🧠 استدلال و مسائل پیچیده",
    "code": "💻 برنامه‌نویسی",
    "speed": "⚡ سرعت و استفاده عمومی",
    "vision": "🖼 چندوجهی (تصویر)",
    "general": "💬 عمومی",
}

SMART_PICKS = {
    "reasoning": ("xkiro", "openai/gpt-6.1-sol"),
    "code": ("xkiro", "mistralai/codestral-2508"),
    "speed": ("anyapi", "google/gemini-3.6-flash"),
    "vision": ("openrouter", "nvidia/nemotron-3.5-super-vl:free"),
    "general": ("xkiro", "openai/gpt-5.6-sol"),
}

CAT_REASON = {
    "reasoning": "چون قدرتمندترین مدل استدلال پرچمدار در کاتالوگ است",
    "code": "چون برای برنامه‌نویسی و حل پیشرفته کدهای ایجنت بهینه‌سازی شده",
    "speed": "چون گزینه فوق‌سریع و پایدار با کانتکست عظیم است",
    "vision": "چون چندوجهی تخصصی تحلیل تصویر و اسناد است",
    "general": "چون متوازن‌ترین پرچمدار عمومی برای انواع مکالمات است",
}


def service_name(code: str) -> str:
    return {
        "xkiro": "XKIRO (۹۹ مدل)",
        "bai": "B.AI (۶۲ مدل)",
        "anyapi": "AnyAPI (۷۰ مدل)",
        "openrouter": "OpenRouter (رایگان)",
        "groq": "Groq (فوق‌سریع)",
        "hooshia": "هوشیا (بومی فارسی)",
        "inception": "Inception (Mercury 3)",
        "freemodel": "FreeModel",
        "github": "GitHub Models",
        "hf": "HuggingFace"
    }.get(code, code)


def find(service: str, model_id_or_uid: str):
    q = (model_id_or_uid or "").strip()
    if q.lower() in UID_MAP:
        srv, mid, item = UID_MAP[q.lower()]
        if not service or service == srv:
            return item

    srv = (service or "").lower()
    lst = ALL_SERVICES.get(srv)
    if lst is None:
        lst = XKIRO + BAI + ANYAPI + OPENROUTER + GROQ + HOOSHIA + INCEPTION

    for e in lst:
        if e.get("id") == q or e.get("id", "").lower() == q.lower() or e.get("uid") == q.lower():
            return e
    return None


def smart_pick(cat: str):
    pair = SMART_PICKS.get(cat)
    if not pair:
        return None
    service, mid = pair
    e = find(service, mid)
    if not e:
        return None
    return {"service": service, "id": mid, "name": e["name"],
            "desc": e.get("desc", ""), "reason": CAT_REASON.get(cat, "")}


def _norm(s: str) -> str:
    s = (s or "").replace("_", " ").replace("-", " ").replace("/", " ").replace(":", " ")
    return " ".join(s.lower().split())


def _detect_service(t: str):
    if any(s in t for s in ("xkiro", "کیرو", "خیرو")):
        return "xkiro"
    if any(s in t for s in ("bai", "بای", "بی ای", "بی‌ای")):
        return "bai"
    if any(s in t for s in ("anyapi", "انی", "انی ای پی آی", "انی‌پی‌آی", "انی پی آی")):
        return "anyapi"
    if any(s in t for s in ("openrouter", "اوپن روتر", "اوپنروتر", "اوپن راتر", "اوپنراتر")):
        return "openrouter"
    if any(s in t for s in ("groq", "گروک", "گروق")):
        return "groq"
    if any(s in t for s in ("hooshia", "هوشیا")):
        return "hooshia"
    if any(s in t for s in ("inception", "اینسپشن", "اینسبشن", "مرکوری", "mercury", "عطارد")):
        return "inception"
    return None


def _list_intent(t: str) -> bool:
    return any(w in t for w in ("نشون", "نمایش", "بیار", "لیست", "چی داری", "چی دارید", "نشان", "بده", "کاتالوگ", "فهرست"))


def _match_model_in_service(srv: str, subtext: str):
    """جستجوی منعطف یک مدل درون یک سرویس خاص."""
    lst = ALL_SERVICES.get(srv, [])
    st = subtext.strip().lower()
    if not st:
        return None
    # ۱. جستجو بر اساس UID
    if st in UID_MAP and UID_MAP[st][0] == srv:
        return UID_MAP[st][1]
    # ۲. جستجو بر اساس شناسه یا نام
    for item in lst:
        if item["id"].lower() == st or item.get("uid", "").lower() == st:
            return item["id"]
        if st in item["name"].lower() or st in item["id"].lower():
            return item["id"]
    return None


def _find_model(text: str):
    clean_text = re.sub(r"https?://\S+", "", text).strip()
    if not clean_text:
        return None

    lt = clean_text.lower()

    # بررسی مستقیم UID مانند k5, b12, a2, o1, g1, h2, i1
    m_uid = re.search(r"\b([kbaoghie][0-9]{1,3})\b", lt)
    if m_uid:
        uid_cand = m_uid.group(1)
        if uid_cand in UID_MAP:
            srv, mid, _ = UID_MAP[uid_cand]
            return srv, mid

    # جستجوی فرمت vendor/model
    m_id = re.search(r"\b([a-zA-Z0-9_\-]+/[a-zA-Z0-9_\-\.:]+)\b", clean_text)
    if m_id:
        cand_id = m_id.group(1).lower()
        for srv, lst in ALL_SERVICES.items():
            for e in lst:
                if e["id"].lower() == cand_id:
                    return srv, e["id"]

    # کلمات کلیدی هوشیا
    if any(k in lt for k in ("hooshia", "هوشیا", "glm")):
        if "4.7" in lt:
            return "hooshia", "GLM-4.7-Flash"
        if "4.6" in lt:
            return "hooshia", "GLM-4.6V-Flash"
        return "hooshia", "GLM-4.5-Flash"

    # تطبیق نام مدل در کل سرویس‌ها
    nt = _norm(clean_text)
    SHORTCUTS = [
        ("qwen", "groq", "qwen/qwen3.8-27b"),
        ("120b", "groq", "openai/gpt-oss-120b"),
        ("20b", "groq", "openai/gpt-oss-20b"),
        ("nemotron", "openrouter", "nvidia/nemotron-3.5-lightning:free"),
        ("gemma", "openrouter", "google/gemma-4-31b-it:free"),
        ("mercury", "inception", "mercury-3"),
        ("مرکوری", "inception", "mercury-3"),
    ]
    for kw, serv, m_id in SHORTCUTS:
        if kw in nt:
            return serv, m_id

    return None


def parse_request(text: str):
    """دستور طبیعی انتخاب/نمایش مدل را تشخیص می‌دهد."""
    no_urls = re.sub(r"https?://\S+", "", text).strip()
    if not no_urls:
        return None

    t = no_urls.lower()

    if ("برگردون" in t or "برگردان" in t or "قبلی" in t) and ("مدل" in t or "model" in t):
        return {"action": "restore"}

    if "مدل فعلی" in t or "چه مدلی" in t or "کدوم مدل" in t or "مدل فعال" in t or ("مدل" in t and "چیه" in t):
        return {"action": "info"}

    service = _detect_service(t)
    MODEL_TRIGGERS = (
        "مدل", "model", "سوییچ", "سوئیچ", "برو رو", "برو روی",
        "بذار رو", "بزار رو", "بذار روی", "بزار روی", "فعال کن", "عوض کن", "تغییر بده"
    )
    model_intent = any(w in t for w in MODEL_TRIGGERS) or service is not None

    # بررسی مستقیم UID (مثال: k1, a5, کاپری مدل b12, برو رو o3)
    m_uid = re.search(r"\b([kbaoghie][0-9]{1,3})\b", t)
    if m_uid:
        uid_cand = m_uid.group(1)
        if uid_cand in UID_MAP:
            srv, mid, _ = UID_MAP[uid_cand]
            return {"action": "select", "service": srv, "model": mid, "uid": uid_cand}

    # اگر کاربر نام سرویس را گفته باشد (مثلا: کاپری مدل کیرو / کاپری مدل بای / کاپری مدل انی / کاپری مدل اوپن روتر)
    if service:
        # استخراج متن باقی‌مانده پس از نام سرویس
        sub = re.sub(r".*?\b(کیرو|خیرو|xkiro|بای|بی ای|بی‌ای|bai|انی|anyapi|اوپن روتر|اوپنروتر|openrouter|گروک|groq|هوشیا|hooshia|اینسپشن|inception)\b", "", t).strip()
        # اگر کاربر فقط گفته «کاپری مدل کیرو» یا شبیه آن (بدون درخواست لیست)
        if not _list_intent(t):
            if sub:
                matched_mid = _match_model_in_service(service, sub)
                if matched_mid:
                    return {"action": "select", "service": service, "model": matched_mid}
            # انتخاب مدل پرچمدار پیش‌فرض سرویس
            defaults = {
                "xkiro": provider_xkiro.DEFAULT_MODEL,
                "bai": provider_bai.DEFAULT_MODEL,
                "anyapi": provider_anyapi.DEFAULT_MODEL,
                "openrouter": provider_openrouter.DEFAULT_MODEL,
                "groq": "qwen/qwen3.8-27b",
                "hooshia": "GLM-4.5-Flash",
                "inception": "mercury-3",
            }
            if service in defaults:
                return {"action": "select", "service": service, "model": defaults[service]}

    if model_intent:
        if "کدنویسی" in t or "برنامه نویسی" in t or "کد " in t or "coding" in t:
            return {"action": "smart", "cat": "code"}
        if "سریع" in t or "سبک" in t or "سرعت" in t:
            return {"action": "smart", "cat": "speed"}
        if "تصویر" in t or "چندوجهی" in t or "multimodal" in t or "اسکرین" in t or "عکس" in t or "بینایی" in t:
            return {"action": "smart", "cat": "vision"}
        if "قوی" in t or "بهترین" in t or "قدرتمند" in t or "استدلال" in t:
            return {"action": "smart", "cat": "reasoning"}

    hit = _find_model(no_urls)
    if hit:
        words_count = len(no_urls.split())
        if model_intent or words_count <= 4:
            return {"action": "select", "service": hit[0], "model": hit[1]}

    if service and _list_intent(t):
        return {"action": "list", "service": service}
    if _list_intent(t) and ("مدل" in t or "model" in t):
        return {"action": "list", "service": None}

    return None
