"""سرویس و فراخوانی مدل‌های ارائه‌دهنده B.AI.

شامل ۶۲ مدل رسمی B.AI با شناسه‌های دقیق سرور و پیشوند شناسه یکتای b1 تا b62.
"""

from core import config
from core import logger

log = logger.get_logger(__name__)

BASE_URL = "https://api.b.ai/v1"
CHAT_ENDPOINT = f"{BASE_URL}/chat/completions"
DEFAULT_MODEL = "minimax-m3.1-flash"

MODELS = [
    {
        "uid": "b1",
        "id": "minimax-m3.1-flash",
        "name": "Minimax M3.1 Flash",
        "desc": "مدل Minimax M3.1 Flash از B.AI",
        "cat": "reasoning",
        "ctx": "128K+"
    },
    {
        "uid": "b2",
        "id": "minimax-m3",
        "name": "Minimax M3",
        "desc": "مدل Minimax M3 از B.AI",
        "cat": "reasoning",
        "ctx": "128K+"
    },
    {
        "uid": "b3",
        "id": "minimax-m2.7",
        "name": "Minimax M2.7",
        "desc": "مدل Minimax M2.7 از B.AI",
        "cat": "reasoning",
        "ctx": "128K+"
    },
    {
        "uid": "b4",
        "id": "glm-5.1",
        "name": "Glm 5.1",
        "desc": "مدل Glm 5.1 از B.AI",
        "cat": "general",
        "ctx": "128K+"
    },
    {
        "uid": "b5",
        "id": "glm-5.2",
        "name": "Glm 5.2",
        "desc": "مدل Glm 5.2 از B.AI",
        "cat": "general",
        "ctx": "128K+"
    },
    {
        "uid": "b6",
        "id": "gpt-6.1-sol",
        "name": "Gpt 6.1 Sol",
        "desc": "مدل Gpt 6.1 Sol از B.AI",
        "cat": "reasoning",
        "ctx": "128K+"
    },
    {
        "uid": "b7",
        "id": "gpt-6-astra",
        "name": "Gpt 6 Astra",
        "desc": "مدل Gpt 6 Astra از B.AI",
        "cat": "reasoning",
        "ctx": "128K+"
    },
    {
        "uid": "b8",
        "id": "gpt-6-sol",
        "name": "Gpt 6 Sol",
        "desc": "مدل Gpt 6 Sol از B.AI",
        "cat": "reasoning",
        "ctx": "128K+"
    },
    {
        "uid": "b9",
        "id": "gpt-6-luna",
        "name": "Gpt 6 Luna",
        "desc": "مدل Gpt 6 Luna از B.AI",
        "cat": "reasoning",
        "ctx": "128K+"
    },
    {
        "uid": "b10",
        "id": "gpt-5.6-sol",
        "name": "Gpt 5.6 Sol",
        "desc": "مدل Gpt 5.6 Sol از B.AI",
        "cat": "general",
        "ctx": "128K+"
    },
    {
        "uid": "b11",
        "id": "gpt-5.6-terra",
        "name": "Gpt 5.6 Terra",
        "desc": "مدل Gpt 5.6 Terra از B.AI",
        "cat": "general",
        "ctx": "128K+"
    },
    {
        "uid": "b12",
        "id": "gpt-5.6-luna",
        "name": "Gpt 5.6 Luna",
        "desc": "مدل Gpt 5.6 Luna از B.AI",
        "cat": "speed",
        "ctx": "128K+"
    },
    {
        "uid": "b13",
        "id": "gpt-5.5",
        "name": "Gpt 5.5",
        "desc": "مدل Gpt 5.5 از B.AI",
        "cat": "general",
        "ctx": "128K+"
    },
    {
        "uid": "b14",
        "id": "gpt-5.5-instant",
        "name": "Gpt 5.5 Instant",
        "desc": "مدل Gpt 5.5 Instant از B.AI",
        "cat": "speed",
        "ctx": "128K+"
    },
    {
        "uid": "b15",
        "id": "gpt-5.4",
        "name": "Gpt 5.4",
        "desc": "مدل Gpt 5.4 از B.AI",
        "cat": "general",
        "ctx": "128K+"
    },
    {
        "uid": "b16",
        "id": "gpt-5.2",
        "name": "Gpt 5.2",
        "desc": "مدل Gpt 5.2 از B.AI",
        "cat": "general",
        "ctx": "128K+"
    },
    {
        "uid": "b17",
        "id": "gpt-5.4-pro",
        "name": "Gpt 5.4 Pro",
        "desc": "مدل Gpt 5.4 Pro از B.AI",
        "cat": "reasoning",
        "ctx": "128K+"
    },
    {
        "uid": "b18",
        "id": "gpt-5.4-mini",
        "name": "Gpt 5.4 Mini",
        "desc": "مدل Gpt 5.4 Mini از B.AI",
        "cat": "speed",
        "ctx": "128K+"
    },
    {
        "uid": "b19",
        "id": "gpt-5-mini",
        "name": "Gpt 5 Mini",
        "desc": "مدل Gpt 5 Mini از B.AI",
        "cat": "speed",
        "ctx": "128K+"
    },
    {
        "uid": "b20",
        "id": "gpt-5.4-nano",
        "name": "Gpt 5.4 Nano",
        "desc": "مدل Gpt 5.4 Nano از B.AI",
        "cat": "speed",
        "ctx": "128K+"
    },
    {
        "uid": "b21",
        "id": "gpt-5-nano",
        "name": "Gpt 5 Nano",
        "desc": "مدل Gpt 5 Nano از B.AI",
        "cat": "speed",
        "ctx": "128K+"
    },
    {
        "uid": "b22",
        "id": "gpt-image-2",
        "name": "Gpt Image 2",
        "desc": "مدل Gpt Image 2 از B.AI",
        "cat": "vision",
        "ctx": "128K+"
    },
    {
        "uid": "b23",
        "id": "claude-opus-5.5",
        "name": "Claude Opus 5.5",
        "desc": "مدل Claude Opus 5.5 از B.AI",
        "cat": "reasoning",
        "ctx": "128K+"
    },
    {
        "uid": "b24",
        "id": "claude-sonnet-5.5",
        "name": "Claude Sonnet 5.5",
        "desc": "مدل Claude Sonnet 5.5 از B.AI",
        "cat": "general",
        "ctx": "128K+"
    },
    {
        "uid": "b25",
        "id": "claude-haiku-5.5",
        "name": "Claude Haiku 5.5",
        "desc": "مدل Claude Haiku 5.5 از B.AI",
        "cat": "speed",
        "ctx": "128K+"
    },
    {
        "uid": "b26",
        "id": "claude-fable-5.1",
        "name": "Claude Fable 5.1",
        "desc": "مدل Claude Fable 5.1 از B.AI",
        "cat": "reasoning",
        "ctx": "128K+"
    },
    {
        "uid": "b27",
        "id": "claude-fable-5",
        "name": "Claude Fable 5",
        "desc": "مدل Claude Fable 5 از B.AI",
        "cat": "reasoning",
        "ctx": "128K+"
    },
    {
        "uid": "b28",
        "id": "claude-opus-5",
        "name": "Claude Opus 5",
        "desc": "مدل Claude Opus 5 از B.AI",
        "cat": "reasoning",
        "ctx": "128K+"
    },
    {
        "uid": "b29",
        "id": "claude-opus-4.8",
        "name": "Claude Opus 4.8",
        "desc": "مدل Claude Opus 4.8 از B.AI",
        "cat": "reasoning",
        "ctx": "128K+"
    },
    {
        "uid": "b30",
        "id": "claude-opus-4.7",
        "name": "Claude Opus 4.7",
        "desc": "مدل Claude Opus 4.7 از B.AI",
        "cat": "reasoning",
        "ctx": "128K+"
    },
    {
        "uid": "b31",
        "id": "claude-opus-4.6",
        "name": "Claude Opus 4.6",
        "desc": "مدل Claude Opus 4.6 از B.AI",
        "cat": "reasoning",
        "ctx": "128K+"
    },
    {
        "uid": "b32",
        "id": "claude-opus-4.5",
        "name": "Claude Opus 4.5",
        "desc": "مدل Claude Opus 4.5 از B.AI",
        "cat": "reasoning",
        "ctx": "128K+"
    },
    {
        "uid": "b33",
        "id": "claude-sonnet-5",
        "name": "Claude Sonnet 5",
        "desc": "مدل Claude Sonnet 5 از B.AI",
        "cat": "general",
        "ctx": "128K+"
    },
    {
        "uid": "b34",
        "id": "claude-sonnet-4.6",
        "name": "Claude Sonnet 4.6",
        "desc": "مدل Claude Sonnet 4.6 از B.AI",
        "cat": "general",
        "ctx": "128K+"
    },
    {
        "uid": "b35",
        "id": "claude-sonnet-4.5",
        "name": "Claude Sonnet 4.5",
        "desc": "مدل Claude Sonnet 4.5 از B.AI",
        "cat": "general",
        "ctx": "128K+"
    },
    {
        "uid": "b36",
        "id": "claude-haiku-4.5",
        "name": "Claude Haiku 4.5",
        "desc": "مدل Claude Haiku 4.5 از B.AI",
        "cat": "speed",
        "ctx": "128K+"
    },
    {
        "uid": "b37",
        "id": "gemini-4-argon",
        "name": "Gemini 4 Argon",
        "desc": "مدل Gemini 4 Argon از B.AI",
        "cat": "speed",
        "ctx": "128K+"
    },
    {
        "uid": "b38",
        "id": "gemini-3.8-flash",
        "name": "Gemini 3.8 Flash",
        "desc": "مدل Gemini 3.8 Flash از B.AI",
        "cat": "speed",
        "ctx": "128K+"
    },
    {
        "uid": "b39",
        "id": "gemini-3.6-flash",
        "name": "Gemini 3.6 Flash",
        "desc": "مدل Gemini 3.6 Flash از B.AI",
        "cat": "speed",
        "ctx": "128K+"
    },
    {
        "uid": "b40",
        "id": "gemini-3.5-flash-lite",
        "name": "Gemini 3.5 Flash Lite",
        "desc": "مدل Gemini 3.5 Flash Lite از B.AI",
        "cat": "speed",
        "ctx": "128K+"
    },
    {
        "uid": "b41",
        "id": "gemini-3.5-flash",
        "name": "Gemini 3.5 Flash",
        "desc": "مدل Gemini 3.5 Flash از B.AI",
        "cat": "speed",
        "ctx": "128K+"
    },
    {
        "uid": "b42",
        "id": "gemini-3.1-pro",
        "name": "Gemini 3.1 Pro",
        "desc": "مدل Gemini 3.1 Pro از B.AI",
        "cat": "reasoning",
        "ctx": "128K+"
    },
    {
        "uid": "b43",
        "id": "gemini-3-flash",
        "name": "Gemini 3 Flash",
        "desc": "مدل Gemini 3 Flash از B.AI",
        "cat": "speed",
        "ctx": "128K+"
    },
    {
        "uid": "b44",
        "id": "hy4-preview",
        "name": "Hy4 Preview",
        "desc": "مدل Hy4 Preview از B.AI",
        "cat": "general",
        "ctx": "128K+"
    },
    {
        "uid": "b45",
        "id": "mimo-v2.6-pro",
        "name": "Mimo V2.6 Pro",
        "desc": "مدل Mimo V2.6 Pro از B.AI",
        "cat": "reasoning",
        "ctx": "128K+"
    },
    {
        "uid": "b46",
        "id": "glm-5.3-flash",
        "name": "Glm 5.3 Flash",
        "desc": "مدل Glm 5.3 Flash از B.AI",
        "cat": "speed",
        "ctx": "128K+"
    },
    {
        "uid": "b47",
        "id": "glm-5.3-flashx",
        "name": "Glm 5.3 Flashx",
        "desc": "مدل Glm 5.3 Flashx از B.AI",
        "cat": "speed",
        "ctx": "128K+"
    },
    {
        "uid": "b48",
        "id": "kimi-k3.1-pro",
        "name": "Kimi K3.1 Pro",
        "desc": "مدل Kimi K3.1 Pro از B.AI",
        "cat": "reasoning",
        "ctx": "128K+"
    },
    {
        "uid": "b49",
        "id": "kimi-k3.1-pro-highspeed",
        "name": "Kimi K3.1 Pro Highspeed",
        "desc": "مدل Kimi K3.1 Pro Highspeed از B.AI",
        "cat": "reasoning",
        "ctx": "128K+"
    },
    {
        "uid": "b50",
        "id": "kimi-k3",
        "name": "Kimi K3",
        "desc": "مدل Kimi K3 از B.AI",
        "cat": "general",
        "ctx": "128K+"
    },
    {
        "uid": "b51",
        "id": "glm-5.3",
        "name": "Glm 5.3",
        "desc": "مدل Glm 5.3 از B.AI",
        "cat": "general",
        "ctx": "128K+"
    },
    {
        "uid": "b52",
        "id": "mimo-v2.6-flash",
        "name": "Mimo V2.6 Flash",
        "desc": "مدل Mimo V2.6 Flash از B.AI",
        "cat": "speed",
        "ctx": "128K+"
    },
    {
        "uid": "b53",
        "id": "kimi-k2.8-preview",
        "name": "Kimi K2.8 Preview",
        "desc": "مدل Kimi K2.8 Preview از B.AI",
        "cat": "general",
        "ctx": "128K+"
    },
    {
        "uid": "b54",
        "id": "kimi-k2.6",
        "name": "Kimi K2.6",
        "desc": "مدل Kimi K2.6 از B.AI",
        "cat": "general",
        "ctx": "128K+"
    },
    {
        "uid": "b55",
        "id": "hy3",
        "name": "Hy3",
        "desc": "مدل Hy3 از B.AI",
        "cat": "general",
        "ctx": "128K+"
    },
    {
        "uid": "b56",
        "id": "qwen3.8-flash",
        "name": "Qwen3.8 Flash",
        "desc": "مدل Qwen3.8 Flash از B.AI",
        "cat": "speed",
        "ctx": "128K+"
    },
    {
        "uid": "b57",
        "id": "qwen3.8-max",
        "name": "Qwen3.8 Max",
        "desc": "مدل Qwen3.8 Max از B.AI",
        "cat": "reasoning",
        "ctx": "128K+"
    },
    {
        "uid": "b58",
        "id": "qwen3.8-27b",
        "name": "Qwen3.8 27B",
        "desc": "مدل Qwen3.8 27B از B.AI",
        "cat": "general",
        "ctx": "128K+"
    },
    {
        "uid": "b59",
        "id": "jev-1.13.0",
        "name": "Jev 1.13.0",
        "desc": "مدل Jev 1.13.0 از B.AI",
        "cat": "general",
        "ctx": "128K+"
    },
    {
        "uid": "b60",
        "id": "deepseek-v4.1-flash",
        "name": "Deepseek V4.1 Flash",
        "desc": "مدل Deepseek V4.1 Flash از B.AI",
        "cat": "speed",
        "ctx": "128K+"
    },
    {
        "uid": "b61",
        "id": "deepseek-v4-pro",
        "name": "Deepseek V4 Pro",
        "desc": "مدل Deepseek V4 Pro از B.AI",
        "cat": "reasoning",
        "ctx": "128K+"
    },
    {
        "uid": "b62",
        "id": "jev-latest",
        "name": "Jev Latest",
        "desc": "مدل Jev Latest از B.AI",
        "cat": "general",
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
