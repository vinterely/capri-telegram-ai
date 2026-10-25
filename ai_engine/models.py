"""کاتالوگ مدل‌ها + تشخیص دستور طبیعی انتخاب مدل."""

import re

GROQ = [
    {"id": "qwen/qwen3.8-27b", "name": "Qwen 3.8 27B",
     "desc": "متعادل و بسیار سریع؛ پاسخ‌گویی عمومی و استدلال عالی", "cat": "general"},
    {"id": "openai/gpt-oss-120b", "name": "GPT-OSS 120B",
     "desc": "پرچمدار Groq؛ استدلال عمیق و کارهای پیچیده و برنامه‌نویسی", "cat": "reasoning"},
    {"id": "openai/gpt-oss-20b", "name": "GPT-OSS 20B",
     "desc": "سبک‌تر و فوق‌سریع برای کارهای روزمره", "cat": "speed"},
]

OPENROUTER = [
    {"id": "nvidia/nemotron-3-ultra-550b-a55b:free", "name": "Nemotron 3 Ultra 550B",
     "desc": "غول استدلال؛ مناسب مسائل بسیار سنگین و محاسباتی", "cat": "reasoning"},
    {"id": "nvidia/nemotron-3-super-120b-a12b:free", "name": "Nemotron 3 Super 120B",
     "desc": "مدل قدرتمند متوازن برای گفتگو و استدلال", "cat": "general"},
    {"id": "nvidia/nemotron-3.5-lightning:free", "name": "Nemotron 3.5 Lightning",
     "desc": "فوق‌سریع و باکیفیت برای استفاده عمومی", "cat": "speed"},
    {"id": "nvidia/nemotron-3.5-super-vl:free", "name": "Nemotron 3.5 Super VL",
     "desc": "چندوجهی رایگان: تحلیل عکس، اسکرین‌شات و اسناد", "cat": "vision"},
    {"id": "google/gemma-4-31b-it:free", "name": "Gemma 4 31B",
     "desc": "مدل پیشرفته گوگل برای مکالمه، کد و حل مسئله", "cat": "general"},
    {"id": "google/gemma-4-26b-a4b-it:free", "name": "Gemma 4 26B",
     "desc": "نسخه سبک‌تر گما گوگل برای سرعت بالاتر", "cat": "speed"},
    {"id": "poolside/laguna-s-2.1:free", "name": "Laguna S 2.1",
     "desc": "تخصصی برنامه‌نویسی و ایجنت‌های کدنویسی", "cat": "code"},
    {"id": "poolside/laguna-xs-2.1:free", "name": "Laguna XS 2.1",
     "desc": "کدنویسی سبک و سریع", "cat": "code"},
    {"id": "cohere/north-mini-code:free", "name": "North Mini Code",
     "desc": "کدنویسی و حل باگ کوهیر", "cat": "code"},
    {"id": "recursive/flint-v1.0:free", "name": "Flint v1.0",
     "desc": "مدل عمومی دقیق و روان", "cat": "general"},
    {"id": "liquid/lfm-2.5-2.6b:free", "name": "LFM 2.5",
     "desc": "فوق‌العاده سریع با معماری غیرترانسفورمری", "cat": "speed"},
    {"id": "xingchen-agi/xing4.0-29b-a4b:free", "name": "Xing 4.0 29B",
     "desc": "گزینه عمومی و خلاقانه", "cat": "general"},
    {"id": "dots-studio/dots-3-note-preview:free", "name": "Dots 3 Note",
     "desc": "تخصصی نگارش و پردازش یادداشت‌ها", "cat": "general"},
    {"id": "thinkingmachines/inkling:free", "name": "Inkling",
     "desc": "استدلال منطقی و حل مسائل", "cat": "reasoning"},
    {"id": "thinkingmachines/inkling-small:free", "name": "Inkling Small",
     "desc": "استدلال سبک و سریع", "cat": "speed"},
]

HOOSHIA = [
    {"id": "GLM-4.5-Flash", "name": "GLM 4.5 Flash",
     "desc": "مدل سریع و سبک هوشیا؛ پاسخ‌گویی پرسرعت و درک روان فارسی", "cat": "speed"},
    {"id": "GLM-4.6V-Flash", "name": "GLM 4.6V Flash (Vision)",
     "desc": "مدل چندوجهی هوشیا با قابلیت تحلیل تصاویر، عکس و اسناد", "cat": "vision"},
    {"id": "GLM-4.7-Flash", "name": "GLM 4.7 Flash",
     "desc": "نسخه پیشرفته هوشیا با قدرت استدلال عمیق‌تر و دقت بالا در فارسی", "cat": "reasoning"},
]

INCEPTION = [
    {"id": "mercury-3", "name": "Mercury 3",
     "desc": "فوق‌سریع (Diffusion LLM) با پشتیبانی کامل ابزارها؛ پاسخ سریع برای ایجنت", "cat": "speed"},
]

CATEGORIES = {
    "reasoning": "🧠 استدلال و مسائل پیچیده",
    "code": "💻 برنامه‌نویسی",
    "speed": "⚡ سرعت و استفاده عمومی",
    "vision": "🖼 چندوجهی (تصویر)",
    "general": "💬 عمومی",
}

SMART_PICKS = {
    "reasoning": ("openrouter", "nvidia/nemotron-3-ultra-550b-a55b:free"),
    "code": ("openrouter", "poolside/laguna-s-2.1:free"),
    "speed": ("openrouter", "nvidia/nemotron-3.5-lightning:free"),
    "vision": ("openrouter", "nvidia/nemotron-3.5-super-vl:free"),
    "general": ("openrouter", "recursive/flint-v1.0:free"),
}

CAT_REASON = {
    "reasoning": "چون توی کاتالوگ به‌عنوان «استدلال قوی» ثبت شده",
    "code": "چون برای «برنامه‌نویسی و ایجنت کدنویسی» معرفی شده",
    "speed": "چون «گزینه سریع برای استفاده عمومی» معرفی شده",
    "vision": "چون «چندوجهی (تصویر/سند)» معرفی شده",
    "general": "چون «مدل عمومی برای استدلال و پاسخ‌گویی» معرفی شده",
}


def service_name(code: str) -> str:
    return {
        "groq": "Groq (فوق‌سریع)",
        "openrouter": "OpenRouter (رایگان)",
        "hooshia": "هوشیا (بومی فارسی)",
        "inception": "Inception (Mercury 3)",
        "freemodel": "FreeModel",
        "github": "GitHub Models",
        "hf": "HuggingFace"
    }.get(code, code)


def find(service: str, model_id: str):
    if service == "groq":
        lst = GROQ
    elif service == "openrouter":
        lst = OPENROUTER
    elif service == "hooshia":
        lst = HOOSHIA
    elif service == "inception":
        lst = INCEPTION
    else:
        lst = GROQ + OPENROUTER + HOOSHIA + INCEPTION
    for e in lst:
        if e["id"] == model_id:
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
            "desc": e["desc"], "reason": CAT_REASON.get(cat, "")}


def _norm(s: str) -> str:
    s = (s or "").replace("_", " ").replace("-", " ").replace("/", " ").replace(":", " ")
    return " ".join(s.lower().split())


def _detect_service(t: str):
    if any(s in t for s in ("groq", "گروک", "گروق")):
        return "groq"
    if any(s in t for s in ("openrouter", "اوپن روتر", "اوپنروتر", "اوپن راتر", "اوپنراتر")):
        return "openrouter"
    if any(s in t for s in ("hooshia", "هوشیا")):
        return "hooshia"
    if any(s in t for s in ("inception", "اینسپشن", "اینسبشن", "مرکوری", "mercury", "عطارد")):
        return "inception"
    return None


def _list_intent(t: str) -> bool:
    return any(w in t for w in ("نشون", "نمایش", "بیار", "لیست", "چی داری", "چی دارید", "نشان", "بده"))


def _find_model(text: str):
    # حذف کامل لینک‌ها تا با مسیر مدل اشتباه نشوند
    clean_text = re.sub(r"https?://\S+", "", text).strip()
    if not clean_text:
        return None

    lt = clean_text.lower()

    # ۰) اگر کاربر مستقیم فرمت vendor/model نوشته
    m_id = re.search(r"\b([a-zA-Z0-9_\-]+/[a-zA-Z0-9_\-\.:]+)\b", clean_text)
    if m_id:
        cand_id = m_id.group(1).lower()
        for e in GROQ:
            if e["id"].lower() == cand_id:
                return "groq", e["id"]
        for e in OPENROUTER:
            if e["id"].lower() == cand_id:
                return "openrouter", e["id"]
        if cand_id.endswith(":free"):
            return "openrouter", m_id.group(1)
        if any(cand_id.startswith(p) for p in ("openai/", "qwen/", "allam")):
            return "groq", m_id.group(1)

    # ۱) کلمات کلیدی هوشیا
    if any(k in lt for k in ("hooshia", "هوشیا", "glm")):
        if "4.7" in lt:
            return "hooshia", "GLM-4.7-Flash"
        return "hooshia", "GLM-4.5-Flash"

    # ۲) آیدی دقیق مدل (خام) در لیست‌ها
    for service, lst in (("groq", GROQ), ("openrouter", OPENROUTER)):
        for e in lst:
            if e["id"].lower() in lt:
                return service, e["id"]

    nt = _norm(clean_text)
    # ۳) آیدی دقیق مدل (نرمال‌شده، با و بدون :free)
    for service, lst in (("groq", GROQ), ("openrouter", OPENROUTER)):
        for e in lst:
            variants = [e["id"]]
            if e["id"].endswith(":free"):
                variants.append(e["id"][:-5])
            for v in variants:
                if _norm(v) in nt:
                    return service, e["id"]

    # ۴) کلمات کلیدی پرکاربرد مدل‌های معروف
    SHORTCUTS = [
        ("qwen", "groq", "qwen/qwen3.8-27b"),
        ("کوئن", "groq", "qwen/qwen3.8-27b"),
        ("کون", "groq", "qwen/qwen3.8-27b"),
        ("120b", "groq", "openai/gpt-oss-120b"),
        ("20b", "groq", "openai/gpt-oss-20b"),
        ("gpt oss", "groq", "openai/gpt-oss-120b"),
        ("nemotron", "openrouter", "nvidia/nemotron-3.5-lightning:free"),
        ("نموترون", "openrouter", "nvidia/nemotron-3.5-lightning:free"),
        ("gemma", "openrouter", "google/gemma-4-31b-it:free"),
        ("گما", "openrouter", "google/gemma-4-31b-it:free"),
        ("flint", "openrouter", "recursive/flint-v1.0:free"),
        ("فلینت", "openrouter", "recursive/flint-v1.0:free"),
        ("laguna", "openrouter", "poolside/laguna-s-2.1:free"),
        ("north", "openrouter", "cohere/north-mini-code:free"),
        ("lfm", "openrouter", "liquid/lfm-2.5-2.6b:free"),
        ("inkling", "openrouter", "thinkingmachines/inkling:free"),
        ("dots", "openrouter", "dots-studio/dots-3-note-preview:free"),
        ("xing", "openrouter", "xingchen-agi/xing4.0-29b-a4b:free"),
        ("mercury", "inception", "mercury-3"),
        ("مرکوری", "inception", "mercury-3"),
        ("مرکیوری", "inception", "mercury-3"),
    ]
    for kw, serv, m_id in SHORTCUTS:
        if kw in nt:
            return serv, m_id

    # ۵) تطبیق اسم/اسلاگ
    best = None
    for service, lst in (("groq", GROQ), ("openrouter", OPENROUTER)):
        for e in lst:
            cands = [e["name"]] + [p for p in e["id"].split(":")[0].split("/") if p]
            for c in cands:
                nc = _norm(c)
                score = len(nc.replace(" ", ""))
                if score < 4:
                    continue
                if nc in nt:
                    if best is None or score > best[0]:
                        best = (score, service, e["id"])
    if best:
        return best[1], best[2]
    return None


def parse_request(text: str):
    """دستور طبیعی انتخاب/نمایش مدل رو تشخیص می‌ده. None = ربطی به مدل نداره."""
    # حذف کامل لینک‌ها تا با مدل اشتباه گرفته نشوند
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
        # فقط در صورتی که کاربر نیت تغییر مدل داشته باشد یا پیام بسیار کوتاه (تنها نام مدل) باشد
        if model_intent or words_count <= 4:
            return {"action": "select", "service": hit[0], "model": hit[1]}

    if service and _list_intent(t):
        return {"action": "list", "service": service}
    if service and ("مدل" in t or "model" in t) and "بذار" not in t and "بزار" not in t:
        return {"action": "list", "service": service}
    if _list_intent(t) and ("مدل" in t or "model" in t):
        return {"action": "list", "service": None}

    return None
