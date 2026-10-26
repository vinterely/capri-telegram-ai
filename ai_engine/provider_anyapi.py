"""سرویس و فراخوانی مدل‌های ارائه‌دهنده ANYAPI.

شامل مدل‌های فعال سرور با پیشوند شناسه یکتای a1 تا a7.
"""

from core import config
from core import logger

log = logger.get_logger(__name__)

BASE_URL = "https://api.anyapi.ai/v1"
CHAT_ENDPOINT = f"{BASE_URL}/chat/completions"
DEFAULT_MODEL = "google/gemini-2.5-flash-lite"

MODELS = [
    {
        "uid": "a1",
        "id": "google/gemini-2.5-flash-lite",
        "name": "Gemini 2.5 Flash Lite",
        "desc": "مدل Gemini 2.5 Flash Lite از AnyAPI",
        "cat": "speed",
        "ctx": "1048576"
    },
    {
        "uid": "a2",
        "id": "google/gemma-4-26b-a4b-it:free",
        "name": "Gemma 4 26B A4B It Free",
        "desc": "مدل Gemma 4 26B A4B It Free از AnyAPI",
        "cat": "general",
        "ctx": "262144"
    },
    {
        "uid": "a3",
        "id": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
        "name": "Nemotron 3 Nano Omni 30B A3B Reasoning Free",
        "desc": "مدل Nemotron 3 Nano Omni 30B A3B Reasoning Free از AnyAPI",
        "cat": "reasoning",
        "ctx": "128K"
    },
    {
        "uid": "a4",
        "id": "nvidia/nemotron-3-ultra-550b-a55b:free",
        "name": "Nemotron 3 Ultra 550B A55B Free",
        "desc": "مدل Nemotron 3 Ultra 550B A55B Free از AnyAPI",
        "cat": "reasoning",
        "ctx": "128K"
    },
    {
        "uid": "a5",
        "id": "dots-studio/dots-3-note-preview:free",
        "name": "Dots 3 Note Preview Free",
        "desc": "مدل Dots 3 Note Preview Free از AnyAPI",
        "cat": "general",
        "ctx": "128K"
    },
    {
        "uid": "a6",
        "id": "nvidia/nemotron-3.5-lightning:free",
        "name": "Nemotron 3.5 Lightning Free",
        "desc": "مدل Nemotron 3.5 Lightning Free از AnyAPI",
        "cat": "speed",
        "ctx": "1000000"
    },
    {
        "uid": "a7",
        "id": "google/gemini-3.6-flash",
        "name": "Gemini 3.6 Flash",
        "desc": "مدل Gemini 3.6 Flash از AnyAPI",
        "cat": "speed",
        "ctx": "1048576"
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


def call_chat(model: str, messages: list, temperature: float = 0.7, max_tokens: int = 2048, timeout: int = 35) -> str:
    from ai_engine import providers
    if not config.ANYAPI_KEY:
        log.warning("ANYAPI_KEY is not configured")
        return ""
    headers = {"Authorization": f"Bearer {config.ANYAPI_KEY}"}
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
        log.warning("AnyAPI chat error on %s: %s", model, type(e).__name__)
        return ""


def call_tools(messages: list, model: str = DEFAULT_MODEL, tools_def=None, temperature: float = 0.7, max_tokens: int = 2048, timeout: int = 35) -> dict:
    from ai_engine import providers, tools
    if not config.ANYAPI_KEY:
        raise ValueError("ANYAPI_KEY is not configured")
    headers = {"Authorization": f"Bearer {config.ANYAPI_KEY}"}
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
