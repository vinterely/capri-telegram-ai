"""سرویس و فراخوانی مدل‌های ارائه‌دهنده B.AI.

شامل ۶۲ مدل با پیشوند شناسه یکتای b1 تا b62.
"""

from core import config
from core import logger

log = logger.get_logger(__name__)

BASE_URL = "https://api.b.ai/v1"
CHAT_ENDPOINT = f"{BASE_URL}/chat/completions"
DEFAULT_MODEL = "GPT-6.1 Sol"

MODELS = [
    {
        "uid": "b1",
        "id": "MiniMax-M3.1-Flash",
        "name": "MiniMax-M3.1-Flash",
        "desc": "مدل MiniMax-M3.1-Flash از B.AI (رسمی)",
        "cat": "reasoning",
        "ctx": "128K+"
    },
    {
        "uid": "b2",
        "id": "MiniMax-M3",
        "name": "MiniMax-M3",
        "desc": "مدل MiniMax-M3 از B.AI (رسمی)",
        "cat": "reasoning",
        "ctx": "128K+"
    },
    {
        "uid": "b3",
        "id": "MiniMax-M2.7",
        "name": "MiniMax-M2.7",
        "desc": "مدل MiniMax-M2.7 از B.AI (رسمی)",
        "cat": "reasoning",
        "ctx": "128K+"
    },
    {
        "uid": "b4",
        "id": "jev-1.13.0",
        "name": "Jev 1.13.0",
        "desc": "مدل Jev 1.13.0 از B.AI (رسمی)",
        "cat": "general",
        "ctx": "128K+"
    },
    {
        "uid": "b5",
        "id": "jev-latest",
        "name": "Jev-Latest",
        "desc": "مدل Jev-Latest از B.AI (رسمی)",
        "cat": "general",
        "ctx": "128K+"
    },
    {
        "uid": "b6",
        "id": "DeepSeek-V4.1-Flash",
        "name": "DeepSeek-V4.1-Flash",
        "desc": "مدل DeepSeek-V4.1-Flash از B.AI (رسمی)",
        "cat": "speed",
        "ctx": "128K+"
    },
    {
        "uid": "b7",
        "id": "DeepSeek-V4-Pro",
        "name": "DeepSeek-V4-Pro",
        "desc": "مدل DeepSeek-V4-Pro از B.AI (رسمی)",
        "cat": "reasoning",
        "ctx": "128K+"
    },
    {
        "uid": "b8",
        "id": "Hy4-preview",
        "name": "Hy4-preview",
        "desc": "مدل Hy4-preview از B.AI (رسمی)",
        "cat": "general",
        "ctx": "128K+"
    },
    {
        "uid": "b9",
        "id": "Hy3",
        "name": "Hy3",
        "desc": "مدل Hy3 از B.AI (رسمی)",
        "cat": "general",
        "ctx": "128K+"
    },
    {
        "uid": "b10",
        "id": "MiMo-V2.6-Pro",
        "name": "MiMo-V2.6-Pro",
        "desc": "مدل MiMo-V2.6-Pro از B.AI (رسمی)",
        "cat": "reasoning",
        "ctx": "128K+"
    },
    {
        "uid": "b11",
        "id": "MiMo-V2.6-Flash",
        "name": "MiMo-V2.6-Flash",
        "desc": "مدل MiMo-V2.6-Flash از B.AI (رسمی)",
        "cat": "speed",
        "ctx": "128K+"
    },
    {
        "uid": "b12",
        "id": "Z.ai",
        "name": "GLM-5.3-Flash",
        "desc": "مدل GLM-5.3-Flash از B.AI (رسمی)",
        "cat": "general",
        "ctx": "128K+"
    },
    {
        "uid": "b13",
        "id": "GLM-5.3-FlashX",
        "name": "GLM-5.3-FlashX",
        "desc": "مدل GLM-5.3-FlashX از B.AI (رسمی)",
        "cat": "speed",
        "ctx": "128K+"
    },
    {
        "uid": "b14",
        "id": "GLM-5.3",
        "name": "GLM-5.3",
        "desc": "مدل GLM-5.3 از B.AI (رسمی)",
        "cat": "general",
        "ctx": "128K+"
    },
    {
        "uid": "b15",
        "id": "GLM-5.2",
        "name": "GLM-5.2",
        "desc": "مدل GLM-5.2 از B.AI (رسمی)",
        "cat": "general",
        "ctx": "128K+"
    },
    {
        "uid": "b16",
        "id": "GLM-5.1",
        "name": "GLM-5.1",
        "desc": "مدل GLM-5.1 از B.AI (رسمی)",
        "cat": "general",
        "ctx": "128K+"
    },
    {
        "uid": "b17",
        "id": "Qwen3.8-Flash",
        "name": "Qwen3.8-Flash",
        "desc": "مدل Qwen3.8-Flash از B.AI (رسمی)",
        "cat": "speed",
        "ctx": "128K+"
    },
    {
        "uid": "b18",
        "id": "Qwen3.8-Max",
        "name": "Qwen3.8-Max",
        "desc": "مدل Qwen3.8-Max از B.AI (رسمی)",
        "cat": "reasoning",
        "ctx": "128K+"
    },
    {
        "uid": "b19",
        "id": "Qwen3.8-27B",
        "name": "Qwen3.8-27B",
        "desc": "مدل Qwen3.8-27B از B.AI (رسمی)",
        "cat": "general",
        "ctx": "128K+"
    },
    {
        "uid": "b20",
        "id": "Kimi K3.1 Pro",
        "name": "Kimi K3.1 Pro",
        "desc": "مدل Kimi K3.1 Pro از B.AI (رسمی)",
        "cat": "reasoning",
        "ctx": "128K+"
    },
    {
        "uid": "b21",
        "id": "Kimi K3.1 Pro Highspeed",
        "name": "Kimi K3.1 Pro Highspeed",
        "desc": "مدل Kimi K3.1 Pro Highspeed از B.AI (رسمی)",
        "cat": "reasoning",
        "ctx": "128K+"
    },
    {
        "uid": "b22",
        "id": "Kimi K3",
        "name": "Kimi K3",
        "desc": "مدل Kimi K3 از B.AI (رسمی)",
        "cat": "general",
        "ctx": "128K+"
    },
    {
        "uid": "b23",
        "id": "Kimi K2.8 Preview",
        "name": "Kimi K2.8 Preview",
        "desc": "مدل Kimi K2.8 Preview از B.AI (رسمی)",
        "cat": "general",
        "ctx": "128K+"
    },
    {
        "uid": "b24",
        "id": "Kimi-K2.6",
        "name": "Kimi-K2.6",
        "desc": "مدل Kimi-K2.6 از B.AI (رسمی)",
        "cat": "general",
        "ctx": "128K+"
    },
    {
        "uid": "b25",
        "id": "Claude Opus 5.5",
        "name": "Claude Opus 5.5",
        "desc": "مدل Claude Opus 5.5 از B.AI (رسمی)",
        "cat": "reasoning",
        "ctx": "128K+"
    },
    {
        "uid": "b26",
        "id": "Claude Sonnet 5.5",
        "name": "Claude Sonnet 5.5",
        "desc": "مدل Claude Sonnet 5.5 از B.AI (رسمی)",
        "cat": "general",
        "ctx": "128K+"
    },
    {
        "uid": "b27",
        "id": "Claude Haiku 5.5",
        "name": "Claude Haiku 5.5",
        "desc": "مدل Claude Haiku 5.5 از B.AI (رسمی)",
        "cat": "speed",
        "ctx": "128K+"
    },
    {
        "uid": "b28",
        "id": "Claude Fable 5.1",
        "name": "Claude Fable 5.1",
        "desc": "مدل Claude Fable 5.1 از B.AI (رسمی)",
        "cat": "reasoning",
        "ctx": "128K+"
    },
    {
        "uid": "b29",
        "id": "Claude Fable 5",
        "name": "Claude Fable 5",
        "desc": "مدل Claude Fable 5 از B.AI (رسمی)",
        "cat": "reasoning",
        "ctx": "128K+"
    },
    {
        "uid": "b30",
        "id": "Claude Opus 5",
        "name": "Claude Opus 5",
        "desc": "مدل Claude Opus 5 از B.AI (رسمی)",
        "cat": "reasoning",
        "ctx": "128K+"
    },
    {
        "uid": "b31",
        "id": "Claude Opus 4.8",
        "name": "Claude Opus 4.8",
        "desc": "مدل Claude Opus 4.8 از B.AI (رسمی)",
        "cat": "reasoning",
        "ctx": "128K+"
    },
    {
        "uid": "b32",
        "id": "Claude Opus 4.7",
        "name": "Claude Opus 4.7",
        "desc": "مدل Claude Opus 4.7 از B.AI (رسمی)",
        "cat": "reasoning",
        "ctx": "128K+"
    },
    {
        "uid": "b33",
        "id": "Claude Opus 4.6",
        "name": "Claude Opus 4.6",
        "desc": "مدل Claude Opus 4.6 از B.AI (رسمی)",
        "cat": "reasoning",
        "ctx": "128K+"
    },
    {
        "uid": "b34",
        "id": "Claude Opus 4.5",
        "name": "Claude Opus 4.5",
        "desc": "مدل Claude Opus 4.5 از B.AI (رسمی)",
        "cat": "reasoning",
        "ctx": "128K+"
    },
    {
        "uid": "b35",
        "id": "Claude Sonnet 5",
        "name": "Claude Sonnet 5",
        "desc": "مدل Claude Sonnet 5 از B.AI (رسمی)",
        "cat": "general",
        "ctx": "128K+"
    },
    {
        "uid": "b36",
        "id": "Claude Sonnet 4.6",
        "name": "Claude Sonnet 4.6",
        "desc": "مدل Claude Sonnet 4.6 از B.AI (رسمی)",
        "cat": "general",
        "ctx": "128K+"
    },
    {
        "uid": "b37",
        "id": "Claude Sonnet 4.5",
        "name": "Claude Sonnet 4.5",
        "desc": "مدل Claude Sonnet 4.5 از B.AI (رسمی)",
        "cat": "general",
        "ctx": "128K+"
    },
    {
        "uid": "b38",
        "id": "Claude Haiku 4.5",
        "name": "Claude Haiku 4.5",
        "desc": "مدل Claude Haiku 4.5 از B.AI (رسمی)",
        "cat": "speed",
        "ctx": "128K+"
    },
    {
        "uid": "b39",
        "id": "GPT-6.1 Sol",
        "name": "GPT-6.1 Sol",
        "desc": "مدل GPT-6.1 Sol از B.AI (رسمی)",
        "cat": "reasoning",
        "ctx": "128K+"
    },
    {
        "uid": "b40",
        "id": "GPT-6 Astra",
        "name": "GPT-6 Astra",
        "desc": "مدل GPT-6 Astra از B.AI (رسمی)",
        "cat": "reasoning",
        "ctx": "128K+"
    },
    {
        "uid": "b41",
        "id": "GPT-6 Sol",
        "name": "GPT-6 Sol",
        "desc": "مدل GPT-6 Sol از B.AI (رسمی)",
        "cat": "reasoning",
        "ctx": "128K+"
    },
    {
        "uid": "b42",
        "id": "GPT-6 Luna",
        "name": "GPT-6 Luna",
        "desc": "مدل GPT-6 Luna از B.AI (رسمی)",
        "cat": "reasoning",
        "ctx": "128K+"
    },
    {
        "uid": "b43",
        "id": "GPT-5.6 Sol",
        "name": "GPT-5.6 Sol",
        "desc": "مدل GPT-5.6 Sol از B.AI (رسمی)",
        "cat": "general",
        "ctx": "128K+"
    },
    {
        "uid": "b44",
        "id": "GPT-5.6 Terra",
        "name": "GPT-5.6 Terra",
        "desc": "مدل GPT-5.6 Terra از B.AI (رسمی)",
        "cat": "general",
        "ctx": "128K+"
    },
    {
        "uid": "b45",
        "id": "GPT-5.6 Luna",
        "name": "GPT-5.6 Luna",
        "desc": "مدل GPT-5.6 Luna از B.AI (رسمی)",
        "cat": "speed",
        "ctx": "128K+"
    },
    {
        "uid": "b46",
        "id": "GPT-5.5",
        "name": "GPT-5.5",
        "desc": "مدل GPT-5.5 از B.AI (رسمی)",
        "cat": "general",
        "ctx": "128K+"
    },
    {
        "uid": "b47",
        "id": "GPT-5.5-Instant",
        "name": "GPT-5.5-Instant",
        "desc": "مدل GPT-5.5-Instant از B.AI (رسمی)",
        "cat": "speed",
        "ctx": "128K+"
    },
    {
        "uid": "b48",
        "id": "GPT-5.4",
        "name": "GPT-5.4",
        "desc": "مدل GPT-5.4 از B.AI (رسمی)",
        "cat": "general",
        "ctx": "128K+"
    },
    {
        "uid": "b49",
        "id": "GPT-5.2",
        "name": "GPT-5.2",
        "desc": "مدل GPT-5.2 از B.AI (رسمی)",
        "cat": "general",
        "ctx": "128K+"
    },
    {
        "uid": "b50",
        "id": "GPT-5.4 Pro",
        "name": "GPT-5.4 Pro",
        "desc": "مدل GPT-5.4 Pro از B.AI (رسمی)",
        "cat": "reasoning",
        "ctx": "128K+"
    },
    {
        "uid": "b51",
        "id": "GPT-5.4 mini",
        "name": "GPT-5.4 mini",
        "desc": "مدل GPT-5.4 mini از B.AI (رسمی)",
        "cat": "speed",
        "ctx": "128K+"
    },
    {
        "uid": "b52",
        "id": "GPT-5 mini",
        "name": "GPT-5 mini",
        "desc": "مدل GPT-5 mini از B.AI (رسمی)",
        "cat": "speed",
        "ctx": "128K+"
    },
    {
        "uid": "b53",
        "id": "GPT-5.4 nano",
        "name": "GPT-5.4 nano",
        "desc": "مدل GPT-5.4 nano از B.AI (رسمی)",
        "cat": "speed",
        "ctx": "128K+"
    },
    {
        "uid": "b54",
        "id": "GPT-5 nano",
        "name": "GPT-5 nano",
        "desc": "مدل GPT-5 nano از B.AI (رسمی)",
        "cat": "speed",
        "ctx": "128K+"
    },
    {
        "uid": "b55",
        "id": "GPT Image 2",
        "name": "GPT Image 2",
        "desc": "مدل GPT Image 2 از B.AI (رسمی)",
        "cat": "vision",
        "ctx": "128K+"
    },
    {
        "uid": "b56",
        "id": "Gemini 4 Argon",
        "name": "Gemini 4 Argon",
        "desc": "مدل Gemini 4 Argon از B.AI (رسمی)",
        "cat": "speed",
        "ctx": "128K+"
    },
    {
        "uid": "b57",
        "id": "Gemini 3.8 flash",
        "name": "Gemini 3.8 flash",
        "desc": "مدل Gemini 3.8 flash از B.AI (رسمی)",
        "cat": "speed",
        "ctx": "128K+"
    },
    {
        "uid": "b58",
        "id": "Gemini 3.6 flash",
        "name": "Gemini 3.6 flash",
        "desc": "مدل Gemini 3.6 flash از B.AI (رسمی)",
        "cat": "speed",
        "ctx": "128K+"
    },
    {
        "uid": "b59",
        "id": "Gemini 3.5 flash-lite",
        "name": "Gemini 3.5 flash-lite",
        "desc": "مدل Gemini 3.5 flash-lite از B.AI (رسمی)",
        "cat": "speed",
        "ctx": "128K+"
    },
    {
        "uid": "b60",
        "id": "Gemini 3.5 flash",
        "name": "Gemini 3.5 flash",
        "desc": "مدل Gemini 3.5 flash از B.AI (رسمی)",
        "cat": "speed",
        "ctx": "128K+"
    },
    {
        "uid": "b61",
        "id": "Gemini 3.1 Pro",
        "name": "Gemini 3.1 Pro",
        "desc": "مدل Gemini 3.1 Pro از B.AI (رسمی)",
        "cat": "reasoning",
        "ctx": "128K+"
    },
    {
        "uid": "b62",
        "id": "Gemini 3 Flash",
        "name": "Gemini 3 Flash",
        "desc": "مدل Gemini 3 Flash از B.AI (رسمی)",
        "cat": "speed",
        "ctx": "128K+"
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
    if not config.BAI_KEY:
        log.warning("BAI_KEY is not configured")
        return ""
    headers = {"Authorization": f"Bearer {config.BAI_KEY}"}
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
        log.warning("B.AI chat error on %s: %s", model, type(e).__name__)
        return ""


def call_tools(messages: list, model: str = DEFAULT_MODEL, tools_def=None, temperature: float = 0.7, max_tokens: int = 2048, timeout: int = 35) -> dict:
    from ai_engine import providers, tools
    if not config.BAI_KEY:
        raise ValueError("BAI_KEY is not configured")
    headers = {"Authorization": f"Bearer {config.BAI_KEY}"}
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
