"""سرویس و فراخوانی مدل‌های ارائه‌دهنده ANYAPI.

شامل ۷۰ مدل با پیشوند شناسه یکتای a1 تا a70.
"""

from core import config
from core import logger

log = logger.get_logger(__name__)

BASE_URL = "https://api.anyapi.ai/v1"
CHAT_ENDPOINT = f"{BASE_URL}/chat/completions"
DEFAULT_MODEL = "google/gemini-3.6-flash"

MODELS = [
    {
        "uid": "a1",
        "id": "google/gemini-2.5-flash-lite",
        "name": "Gemini 2.5 Flash Lite",
        "desc": "مدل Gemini 2.5 Flash Lite از AnyAPI (کانتکست 1,048,576)",
        "cat": "speed",
        "ctx": "1,048,576"
    },
    {
        "uid": "a2",
        "id": "google/gemini-3.6-flash",
        "name": "Gemini 3.6 Flash",
        "desc": "مدل Gemini 3.6 Flash از AnyAPI (کانتکست 1,048,576)",
        "cat": "speed",
        "ctx": "1,048,576"
    },
    {
        "uid": "a3",
        "id": "google/gemma-4-26b-a4b-it:free",
        "name": "Gemma 4 26B A4B It Free",
        "desc": "مدل Gemma 4 26B A4B It Free از AnyAPI (کانتکست 262,144)",
        "cat": "general",
        "ctx": "262,144"
    },
    {
        "uid": "a4",
        "id": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
        "name": "Nemotron 3 Nano Omni 30B A3B Reasoning Free",
        "desc": "مدل Nemotron 3 Nano Omni 30B A3B Reasoning Free از AnyAPI",
        "cat": "reasoning",
        "ctx": ""
    },
    {
        "uid": "a5",
        "id": "nvidia/nemotron-3-ultra-550b-a55b:free",
        "name": "Nemotron 3 Ultra 550B A55B Free",
        "desc": "مدل Nemotron 3 Ultra 550B A55B Free از AnyAPI",
        "cat": "general",
        "ctx": ""
    },
    {
        "uid": "a6",
        "id": "dots-studio/dots-3-note-preview:free",
        "name": "Dots 3 Note Preview Free",
        "desc": "مدل Dots 3 Note Preview Free از AnyAPI",
        "cat": "general",
        "ctx": ""
    },
    {
        "uid": "a7",
        "id": "nvidia/nemotron-3.5-lightning:free",
        "name": "Nemotron 3.5 Lightning Free",
        "desc": "مدل Nemotron 3.5 Lightning Free از AnyAPI (کانتکست 1,000,000)",
        "cat": "general",
        "ctx": "1,000,000"
    },
    {
        "uid": "a8",
        "id": "anthropic/claude-sonnet-4",
        "name": "Claude Sonnet 4",
        "desc": "مدل Claude Sonnet 4 از AnyAPI (کانتکست 200,000)",
        "cat": "general",
        "ctx": "200,000"
    },
    {
        "uid": "a9",
        "id": "amazon/nova-lite-v1",
        "name": "Nova Lite V1",
        "desc": "مدل Nova Lite V1 از AnyAPI (کانتکست 300,000)",
        "cat": "speed",
        "ctx": "300,000"
    },
    {
        "uid": "a10",
        "id": "openai/gpt-oss-120b",
        "name": "Gpt Oss 120B",
        "desc": "مدل Gpt Oss 120B از AnyAPI (کانتکست 131,072)",
        "cat": "general",
        "ctx": "131,072"
    },
    {
        "uid": "a11",
        "id": "openai/gpt-oss-20b",
        "name": "Gpt Oss 20B",
        "desc": "مدل Gpt Oss 20B از AnyAPI (کانتکست 131,072)",
        "cat": "general",
        "ctx": "131,072"
    },
    {
        "uid": "a12",
        "id": "amazon/nova-2-lite-v1",
        "name": "Nova 2 Lite V1",
        "desc": "مدل Nova 2 Lite V1 از AnyAPI (کانتکست 1,000,000)",
        "cat": "speed",
        "ctx": "1,000,000"
    },
    {
        "uid": "a13",
        "id": "anthropic/claude-haiku-4.5",
        "name": "Claude Haiku 4.5",
        "desc": "مدل Claude Haiku 4.5 از AnyAPI (کانتکست 200,000)",
        "cat": "speed",
        "ctx": "200,000"
    },
    {
        "uid": "a14",
        "id": "qwen/qwen3-coder-30b-a3b-instruct",
        "name": "Qwen3 Coder 30B A3B Instruct",
        "desc": "مدل Qwen3 Coder 30B A3B Instruct از AnyAPI (کانتکست 160,000)",
        "cat": "code",
        "ctx": "160,000"
    },
    {
        "uid": "a15",
        "id": "qwen/qwen3-32b",
        "name": "Qwen3 32B",
        "desc": "مدل Qwen3 32B از AnyAPI (کانتکست 40,960)",
        "cat": "general",
        "ctx": "40,960"
    },
    {
        "uid": "a16",
        "id": "moonshotai/kimi-k2.5",
        "name": "Kimi K2.5",
        "desc": "مدل Kimi K2.5 از AnyAPI (کانتکست 262,144)",
        "cat": "general",
        "ctx": "262,144"
    },
    {
        "uid": "a17",
        "id": "google/gemini-2.5-flash",
        "name": "Gemini 2.5 Flash",
        "desc": "مدل Gemini 2.5 Flash از AnyAPI (کانتکست 1,048,576)",
        "cat": "speed",
        "ctx": "1,048,576"
    },
    {
        "uid": "a18",
        "id": "google/gemini-2.5-pro",
        "name": "Gemini 2.5 Pro",
        "desc": "مدل Gemini 2.5 Pro از AnyAPI (کانتکست 1,048,576)",
        "cat": "reasoning",
        "ctx": "1,048,576"
    },
    {
        "uid": "a19",
        "id": "google/gemini-2.0-flash-001",
        "name": "Gemini 2.0 Flash 001",
        "desc": "مدل Gemini 2.0 Flash 001 از AnyAPI (کانتکست 1,000,000)",
        "cat": "speed",
        "ctx": "1,000,000"
    },
    {
        "uid": "a20",
        "id": "anthropic/claude-sonnet-4.6",
        "name": "Claude Sonnet 4.6",
        "desc": "مدل Claude Sonnet 4.6 از AnyAPI (کانتکست 1,000,000)",
        "cat": "general",
        "ctx": "1,000,000"
    },
    {
        "uid": "a21",
        "id": "anthropic/claude-opus-4.6",
        "name": "Claude Opus 4.6",
        "desc": "مدل Claude Opus 4.6 از AnyAPI (کانتکست 1,000,000)",
        "cat": "reasoning",
        "ctx": "1,000,000"
    },
    {
        "uid": "a22",
        "id": "moonshotai/kimi-k2-thinking",
        "name": "Kimi K2 Thinking",
        "desc": "مدل Kimi K2 Thinking از AnyAPI (کانتکست 262,144)",
        "cat": "reasoning",
        "ctx": "262,144"
    },
    {
        "uid": "a23",
        "id": "openai/gpt-4.1",
        "name": "Gpt 4.1",
        "desc": "مدل Gpt 4.1 از AnyAPI (کانتکست 1,047,576)",
        "cat": "general",
        "ctx": "1,047,576"
    },
    {
        "uid": "a24",
        "id": "openai/gpt-4.1-mini",
        "name": "Gpt 4.1 Mini",
        "desc": "مدل Gpt 4.1 Mini از AnyAPI (کانتکست 1,047,576)",
        "cat": "speed",
        "ctx": "1,047,576"
    },
    {
        "uid": "a25",
        "id": "openai/gpt-4.1-nano",
        "name": "Gpt 4.1 Nano",
        "desc": "مدل Gpt 4.1 Nano از AnyAPI (کانتکست 1,047,576)",
        "cat": "speed",
        "ctx": "1,047,576"
    },
    {
        "uid": "a26",
        "id": "openai/o1-pro",
        "name": "O1 Pro",
        "desc": "مدل O1 Pro از AnyAPI (کانتکست 200,000)",
        "cat": "reasoning",
        "ctx": "200,000"
    },
    {
        "uid": "a27",
        "id": "openai/o1",
        "name": "O1",
        "desc": "مدل O1 از AnyAPI (کانتکست 200,000)",
        "cat": "reasoning",
        "ctx": "200,000"
    },
    {
        "uid": "a28",
        "id": "openai/gpt-4o-2024-11-20",
        "name": "Gpt 4O 2024 11 20",
        "desc": "مدل Gpt 4O 2024 11 20 از AnyAPI (کانتکست 128,000)",
        "cat": "general",
        "ctx": "128,000"
    },
    {
        "uid": "a29",
        "id": "openai/gpt-4o-2024-08-06",
        "name": "Gpt 4O 2024 08 06",
        "desc": "مدل Gpt 4O 2024 08 06 از AnyAPI (کانتکست 128,000)",
        "cat": "general",
        "ctx": "128,000"
    },
    {
        "uid": "a30",
        "id": "openai/gpt-4o-mini",
        "name": "Gpt 4O Mini",
        "desc": "مدل Gpt 4O Mini از AnyAPI (کانتکست 128,000)",
        "cat": "speed",
        "ctx": "128,000"
    },
    {
        "uid": "a31",
        "id": "openai/gpt-4o-mini-2024-07-18",
        "name": "Gpt 4O Mini 2024 07 18",
        "desc": "مدل Gpt 4O Mini 2024 07 18 از AnyAPI (کانتکست 128,000)",
        "cat": "speed",
        "ctx": "128,000"
    },
    {
        "uid": "a32",
        "id": "openai/gpt-4o",
        "name": "Gpt 4O",
        "desc": "مدل Gpt 4O از AnyAPI (کانتکست 128,000)",
        "cat": "general",
        "ctx": "128,000"
    },
    {
        "uid": "a33",
        "id": "openai/gpt-4-turbo",
        "name": "Gpt 4 Turbo",
        "desc": "مدل Gpt 4 Turbo از AnyAPI (کانتکست 128,000)",
        "cat": "speed",
        "ctx": "128,000"
    },
    {
        "uid": "a34",
        "id": "openai/gpt-3.5-turbo-0613",
        "name": "Gpt 3.5 Turbo 0613",
        "desc": "مدل Gpt 3.5 Turbo 0613 از AnyAPI (کانتکست 4,095)",
        "cat": "speed",
        "ctx": "4,095"
    },
    {
        "uid": "a35",
        "id": "openai/gpt-3.5-turbo-instruct",
        "name": "Gpt 3.5 Turbo Instruct",
        "desc": "مدل Gpt 3.5 Turbo Instruct از AnyAPI (کانتکست 4,095)",
        "cat": "speed",
        "ctx": "4,095"
    },
    {
        "uid": "a36",
        "id": "openai/gpt-3.5-turbo-16k",
        "name": "Gpt 3.5 Turbo 16K",
        "desc": "مدل Gpt 3.5 Turbo 16K از AnyAPI (کانتکست 16,385)",
        "cat": "speed",
        "ctx": "16,385"
    },
    {
        "uid": "a37",
        "id": "openai/gpt-3.5-turbo",
        "name": "Gpt 3.5 Turbo",
        "desc": "مدل Gpt 3.5 Turbo از AnyAPI (کانتکست 16,385)",
        "cat": "speed",
        "ctx": "16,385"
    },
    {
        "uid": "a38",
        "id": "openai/gpt-4",
        "name": "Gpt 4",
        "desc": "مدل Gpt 4 از AnyAPI (کانتکست 8,191)",
        "cat": "general",
        "ctx": "8,191"
    },
    {
        "uid": "a39",
        "id": "cohere/command-r7b-12-2024",
        "name": "Command R7B 12 2024",
        "desc": "مدل Command R7B 12 2024 از AnyAPI (کانتکست 128,000)",
        "cat": "general",
        "ctx": "128,000"
    },
    {
        "uid": "a40",
        "id": "cohere/command-r-plus-08-2024",
        "name": "Command R Plus 08 2024",
        "desc": "مدل Command R Plus 08 2024 از AnyAPI (کانتکست 128,000)",
        "cat": "general",
        "ctx": "128,000"
    },
    {
        "uid": "a41",
        "id": "cohere/command-r-08-2024",
        "name": "Command R 08 2024",
        "desc": "مدل Command R 08 2024 از AnyAPI (کانتکست 128,000)",
        "cat": "general",
        "ctx": "128,000"
    },
    {
        "uid": "a42",
        "id": "qwen/qwen-2.5-coder-32b-instruct",
        "name": "Qwen 2.5 Coder 32B Instruct",
        "desc": "مدل Qwen 2.5 Coder 32B Instruct از AnyAPI (کانتکست 32,768)",
        "cat": "code",
        "ctx": "32,768"
    },
    {
        "uid": "a43",
        "id": "deepseek/deepseek-r1-0528",
        "name": "Deepseek R1 0528",
        "desc": "مدل Deepseek R1 0528 از AnyAPI (کانتکست 163,840)",
        "cat": "reasoning",
        "ctx": "163,840"
    },
    {
        "uid": "a44",
        "id": "deepseek/deepseek-chat",
        "name": "Deepseek Chat",
        "desc": "مدل Deepseek Chat از AnyAPI (کانتکست 163,840)",
        "cat": "general",
        "ctx": "163,840"
    },
    {
        "uid": "a45",
        "id": "mancer/weaver",
        "name": "Weaver",
        "desc": "مدل Weaver از AnyAPI (کانتکست 8,000)",
        "cat": "general",
        "ctx": "8,000"
    },
    {
        "uid": "a46",
        "id": "undi95/remm-slerp-l2-13b",
        "name": "Remm Slerp L2 13B",
        "desc": "مدل Remm Slerp L2 13B از AnyAPI (کانتکست 6,144)",
        "cat": "general",
        "ctx": "6,144"
    },
    {
        "uid": "a47",
        "id": "gryphe/mythomax-l2-13b",
        "name": "Mythomax L2 13B",
        "desc": "مدل Mythomax L2 13B از AnyAPI (کانتکست 4,096)",
        "cat": "general",
        "ctx": "4,096"
    },
    {
        "uid": "a48",
        "id": "mistralai/mistral-small-3.2-24b-instruct",
        "name": "Mistral Small 3.2 24B Instruct",
        "desc": "مدل Mistral Small 3.2 24B Instruct از AnyAPI (کانتکست 128,000)",
        "cat": "speed",
        "ctx": "128,000"
    },
    {
        "uid": "a49",
        "id": "mistralai/mistral-small-3.1-24b-instruct",
        "name": "Mistral Small 3.1 24B Instruct",
        "desc": "مدل Mistral Small 3.1 24B Instruct از AnyAPI (کانتکست 128,000)",
        "cat": "speed",
        "ctx": "128,000"
    },
    {
        "uid": "a50",
        "id": "mistralai/mistral-large-2407",
        "name": "Mistral Large 2407",
        "desc": "مدل Mistral Large 2407 از AnyAPI (کانتکست 131,072)",
        "cat": "general",
        "ctx": "131,072"
    },
    {
        "uid": "a51",
        "id": "mistralai/mixtral-8x22b-instruct",
        "name": "Mixtral 8X22B Instruct",
        "desc": "مدل Mixtral 8X22B Instruct از AnyAPI (کانتکست 65,536)",
        "cat": "speed",
        "ctx": "65,536"
    },
    {
        "uid": "a52",
        "id": "microsoft/wizardlm-2-8x22b",
        "name": "Wizardlm 2 8X22B",
        "desc": "مدل Wizardlm 2 8X22B از AnyAPI (کانتکست 65,535)",
        "cat": "general",
        "ctx": "65,535"
    },
    {
        "uid": "a53",
        "id": "mistralai/mistral-large",
        "name": "Mistral Large",
        "desc": "مدل Mistral Large از AnyAPI (کانتکست 128,000)",
        "cat": "general",
        "ctx": "128,000"
    },
    {
        "uid": "a54",
        "id": "anthropic/claude-3-haiku",
        "name": "Claude 3 Haiku",
        "desc": "مدل Claude 3 Haiku از AnyAPI (کانتکست 200,000)",
        "cat": "speed",
        "ctx": "200,000"
    },
    {
        "uid": "a55",
        "id": "perplexity/sonar-reasoning-pro",
        "name": "Sonar Reasoning Pro",
        "desc": "مدل Sonar Reasoning Pro از AnyAPI (کانتکست 128,000)",
        "cat": "reasoning",
        "ctx": "128,000"
    },
    {
        "uid": "a56",
        "id": "perplexity/sonar-pro",
        "name": "Sonar Pro",
        "desc": "مدل Sonar Pro از AnyAPI (کانتکست 200,000)",
        "cat": "reasoning",
        "ctx": "200,000"
    },
    {
        "uid": "a57",
        "id": "perplexity/sonar-deep-research",
        "name": "Sonar Deep Research",
        "desc": "مدل Sonar Deep Research از AnyAPI (کانتکست 128,000)",
        "cat": "general",
        "ctx": "128,000"
    },
    {
        "uid": "a58",
        "id": "openai/o3-mini-high",
        "name": "O3 Mini High",
        "desc": "مدل O3 Mini High از AnyAPI (کانتکست 200,000)",
        "cat": "reasoning",
        "ctx": "200,000"
    },
    {
        "uid": "a59",
        "id": "openai/o3-mini",
        "name": "O3 Mini",
        "desc": "مدل O3 Mini از AnyAPI (کانتکست 200,000)",
        "cat": "reasoning",
        "ctx": "200,000"
    },
    {
        "uid": "a60",
        "id": "perplexity/sonar",
        "name": "Sonar",
        "desc": "مدل Sonar از AnyAPI (کانتکست 127,072)",
        "cat": "general",
        "ctx": "127,072"
    },
    {
        "uid": "a61",
        "id": "meta-llama/llama-3.3-70b-instruct",
        "name": "Llama 3.3 70B Instruct",
        "desc": "مدل Llama 3.3 70B Instruct از AnyAPI (کانتکست 131,072)",
        "cat": "speed",
        "ctx": "131,072"
    },
    {
        "uid": "a62",
        "id": "qwen/qwen3-coder",
        "name": "Qwen3 Coder",
        "desc": "مدل Qwen3 Coder از AnyAPI (کانتکست 262,144)",
        "cat": "code",
        "ctx": "262,144"
    },
    {
        "uid": "a63",
        "id": "bytedance/ui-tars-1.5-7b",
        "name": "Ui Tars 1.5 7B",
        "desc": "مدل Ui Tars 1.5 7B از AnyAPI (کانتکست 128,000)",
        "cat": "vision",
        "ctx": "128,000"
    },
    {
        "uid": "a64",
        "id": "deepseek/deepseek-chat-v3.1",
        "name": "Deepseek Chat V3.1",
        "desc": "مدل Deepseek Chat V3.1 از AnyAPI (کانتکست 32,768)",
        "cat": "general",
        "ctx": "32,768"
    },
    {
        "uid": "a65",
        "id": "openai/gpt-5-mini",
        "name": "Gpt 5 Mini",
        "desc": "مدل Gpt 5 Mini از AnyAPI (کانتکست 400,000)",
        "cat": "speed",
        "ctx": "400,000"
    },
    {
        "uid": "a66",
        "id": "openai/gpt-5-nano",
        "name": "Gpt 5 Nano",
        "desc": "مدل Gpt 5 Nano از AnyAPI (کانتکست 400,000)",
        "cat": "speed",
        "ctx": "400,000"
    },
    {
        "uid": "a67",
        "id": "anthropic/claude-opus-4.1",
        "name": "Claude Opus 4.1",
        "desc": "مدل Claude Opus 4.1 از AnyAPI (کانتکست 200,000)",
        "cat": "reasoning",
        "ctx": "200,000"
    },
    {
        "uid": "a68",
        "id": "anthropic/claude-sonnet-4.5",
        "name": "Claude Sonnet 4.5",
        "desc": "مدل Claude Sonnet 4.5 از AnyAPI (کانتکست 1,000,000)",
        "cat": "general",
        "ctx": "1,000,000"
    },
    {
        "uid": "a69",
        "id": "anthropic/claude-opus-4.5",
        "name": "Claude Opus 4.5",
        "desc": "مدل Claude Opus 4.5 از AnyAPI (کانتکست 200,000)",
        "cat": "reasoning",
        "ctx": "200,000"
    },
    {
        "uid": "a70",
        "id": "openai/gpt-5.1-codex-max",
        "name": "Gpt 5.1 Codex Max",
        "desc": "مدل Gpt 5.1 Codex Max از AnyAPI",
        "cat": "code",
        "ctx": ""
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
