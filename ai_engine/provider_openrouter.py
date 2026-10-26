"""سرویس و فراخوانی مدل‌های ارائه‌دهنده OpenRouter.

شامل ۱۵ مدل رایگان با پیشوند شناسه یکتای o1 تا o15.
"""

from core import config
from core import logger

log = logger.get_logger(__name__)

BASE_URL = "https://openrouter.ai/api/v1"
CHAT_ENDPOINT = f"{BASE_URL}/chat/completions"
DEFAULT_MODEL = "nvidia/nemotron-3.5-lightning:free"

MODELS = [
    {
        "id": "nvidia/nemotron-3-ultra-550b-a55b:free",
        "name": "Nemotron 3 Ultra 550B",
        "desc": "غول استدلال؛ مناسب مسائل بسیار سنگین و محاسباتی",
        "cat": "reasoning",
        "ctx": "128K",
        "uid": "o1"
    },
    {
        "id": "nvidia/nemotron-3-super-120b-a12b:free",
        "name": "Nemotron 3 Super 120B",
        "desc": "مدل قدرتمند متوازن برای گفتگو و استدلال",
        "cat": "general",
        "ctx": "128K",
        "uid": "o2"
    },
    {
        "id": "nvidia/nemotron-3.5-lightning:free",
        "name": "Nemotron 3.5 Lightning",
        "desc": "فوق‌سریع و باکیفیت برای استفاده عمومی",
        "cat": "speed",
        "ctx": "128K",
        "uid": "o3"
    },
    {
        "id": "nvidia/nemotron-3.5-super-vl:free",
        "name": "Nemotron 3.5 Super VL",
        "desc": "چندوجهی رایگان: تحلیل عکس، اسکرین‌شات و اسناد",
        "cat": "vision",
        "ctx": "128K",
        "uid": "o4"
    },
    {
        "id": "google/gemma-4-31b-it:free",
        "name": "Gemma 4 31B",
        "desc": "مدل پیشرفته گوگل برای مکالمه، کد و حل مسئله",
        "cat": "general",
        "ctx": "262K",
        "uid": "o5"
    },
    {
        "id": "google/gemma-4-26b-a4b-it:free",
        "name": "Gemma 4 26B",
        "desc": "نسخه سبک‌تر گما گوگل برای سرعت بالاتر",
        "cat": "speed",
        "ctx": "262K",
        "uid": "o6"
    },
    {
        "id": "poolside/laguna-s-2.1:free",
        "name": "Laguna S 2.1",
        "desc": "تخصصی برنامه‌نویسی و ایجنت‌های کدنویسی",
        "cat": "code",
        "ctx": "128K",
        "uid": "o7"
    },
    {
        "id": "poolside/laguna-xs-2.1:free",
        "name": "Laguna XS 2.1",
        "desc": "کدنویسی سبک و سریع",
        "cat": "code",
        "ctx": "128K",
        "uid": "o8"
    },
    {
        "id": "cohere/north-mini-code:free",
        "name": "North Mini Code",
        "desc": "کدنویسی و حل باگ کوهیر",
        "cat": "code",
        "ctx": "128K",
        "uid": "o9"
    },
    {
        "id": "recursive/flint-v1.0:free",
        "name": "Flint v1.0",
        "desc": "مدل عمومی دقیق و روان",
        "cat": "general",
        "ctx": "128K",
        "uid": "o10"
    },
    {
        "id": "liquid/lfm-2.5-2.6b:free",
        "name": "LFM 2.5",
        "desc": "فوق‌العاده سریع با معماری غیرترانسفورمری",
        "cat": "speed",
        "ctx": "128K",
        "uid": "o11"
    },
    {
        "id": "xingchen-agi/xing4.0-29b-a4b:free",
        "name": "Xing 4.0 29B",
        "desc": "گزینه عمومی و خلاقانه",
        "cat": "general",
        "ctx": "128K",
        "uid": "o12"
    },
    {
        "id": "dots-studio/dots-3-note-preview:free",
        "name": "Dots 3 Note",
        "desc": "تخصصی نگارش و پردازش یادداشت‌ها",
        "cat": "general",
        "ctx": "128K",
        "uid": "o13"
    },
    {
        "id": "thinkingmachines/inkling:free",
        "name": "Inkling",
        "desc": "استدلال منطقی و حل مسائل",
        "cat": "reasoning",
        "ctx": "128K",
        "uid": "o14"
    },
    {
        "id": "thinkingmachines/inkling-small:free",
        "name": "Inkling Small",
        "desc": "استدلال سبک و سریع",
        "cat": "speed",
        "ctx": "128K",
        "uid": "o15"
    }
]

UID_MAP = {m["uid"]: m for m in MODELS}
ID_MAP = {m["id"]: m for m in MODELS}


def get_models() -> list:
    return list(MODELS)


def find_by_uid(uid: str):
    return UID_MAP.get((uid or "").strip().lower())


def find_by_id(model_id: str):
    m_clean = (model_id or "").strip()
    return ID_MAP.get(m_clean) or ID_MAP.get(m_clean.lower())


def call_chat(model: str, messages: list, temperature: float = 0.7, max_tokens: int = 1500, timeout: int = 35) -> str:
    from ai_engine import providers
    if not config.OPENROUTER_API_KEY:
        log.warning("OPENROUTER_API_KEY is not configured")
        return ""
    headers = {
        "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://github.com",
        "X-Title": "Capri"
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    try:
        data = providers._post(CHAT_ENDPOINT, payload, headers, timeout=timeout)
        return (data["choices"][0]["message"]["content"] or "").strip()
    except Exception as e:
        log.warning("OpenRouter chat error on %s: %s", model, type(e).__name__)
        return ""


def call_tools(messages: list, model: str = DEFAULT_MODEL, tools_def=None, temperature: float = 0.7, max_tokens: int = 1500, timeout: int = 35) -> dict:
    from ai_engine import providers, tools
    if not config.OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY is not configured")
    headers = {
        "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://github.com",
        "X-Title": "Capri"
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if tools_def is None:
        payload["tools"] = tools.get_all_tool_definitions()
        payload["tool_choice"] = "auto"
    elif tools_def:
        payload["tools"] = tools_def
        payload["tool_choice"] = "auto"
    return providers._post(CHAT_ENDPOINT, payload, headers, timeout=timeout)
