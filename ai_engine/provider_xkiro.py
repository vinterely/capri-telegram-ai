"""سرویس و فراخوانی مدل‌های ارائه‌دهنده XKIRO.

شامل ۹۷ مدل از سرور رسمی XKIRO با پیشوند شناسه یکتای k1 تا k97.
"""

from core import config
from core import logger

log = logger.get_logger(__name__)

BASE_URL = "https://api.xkiro.com/v1"
CHAT_ENDPOINT = f"{BASE_URL}/chat/completions"
DEFAULT_MODEL = "mistralai/ministral-14b"

MODELS = [
    {
        "uid": "k1",
        "id": "mistralai/ministral-14b",
        "name": "Ministral 3 14B",
        "desc": "مدل Ministral 3 14B (🆓 رایگان) از XKIRO",
        "cat": "speed",
        "tier": "free",
        "ctx": "128K+"
    },
    {
        "uid": "k2",
        "id": "google/gemini-3.6-flash",
        "name": "Gemini 3.6 Flash",
        "desc": "مدل Gemini 3.6 Flash (💳 پلن پولی) از XKIRO",
        "cat": "speed",
        "tier": "paid",
        "ctx": "128K+"
    },
    {
        "uid": "k3",
        "id": "openai/gpt-6.1-sol",
        "name": "GPT-6.1 Sol",
        "desc": "مدل GPT-6.1 Sol (💳 پلن پولی) از XKIRO",
        "cat": "reasoning",
        "tier": "paid",
        "ctx": "128K+"
    },
    {
        "uid": "k4",
        "id": "anthropic/claude-sonnet-4.6",
        "name": "Sonnet 4.6",
        "desc": "مدل Sonnet 4.6 (💳 پلن پولی) از XKIRO",
        "cat": "general",
        "tier": "paid",
        "ctx": "128K+"
    },
    {
        "uid": "k5",
        "id": "anthropic/claude-fable-5",
        "name": "Fable 5",
        "desc": "مدل Fable 5 (💳 پلن پولی) از XKIRO",
        "cat": "reasoning",
        "tier": "paid",
        "ctx": "128K+"
    },
    {
        "uid": "k6",
        "id": "x-ai/grok-4.5",
        "name": "Grok 4.5",
        "desc": "مدل Grok 4.5 (💳 پلن پولی) از XKIRO",
        "cat": "general",
        "tier": "premium",
        "ctx": "128K+"
    },
    {
        "uid": "k7",
        "id": "anthropic/claude-opus-4.8",
        "name": "Opus 4.8",
        "desc": "مدل Opus 4.8 (💳 پلن پولی) از XKIRO",
        "cat": "reasoning",
        "tier": "paid",
        "ctx": "128K+"
    },
    {
        "uid": "k8",
        "id": "anthropic/claude-fable-5-1",
        "name": "Fable 5.1",
        "desc": "مدل Fable 5.1 (💳 پلن پولی) از XKIRO",
        "cat": "reasoning",
        "tier": "paid",
        "ctx": "128K+"
    },
    {
        "uid": "k9",
        "id": "x-ai/grok-4.7",
        "name": "Grok 4.7",
        "desc": "مدل Grok 4.7 (💳 پلن پولی) از XKIRO",
        "cat": "general",
        "tier": "paid",
        "ctx": "128K+"
    },
    {
        "uid": "k10",
        "id": "anthropic/claude-haiku-5.5",
        "name": "Haiku 5.5",
        "desc": "مدل Haiku 5.5 (💳 پلن پولی) از XKIRO",
        "cat": "speed",
        "tier": "paid",
        "ctx": "128K+"
    },
    {
        "uid": "k11",
        "id": "anthropic/claude-sonnet-5.5",
        "name": "Sonnet 5.5",
        "desc": "مدل Sonnet 5.5 (💳 پلن پولی) از XKIRO",
        "cat": "general",
        "tier": "paid",
        "ctx": "128K+"
    },
    {
        "uid": "k12",
        "id": "anthropic/claude-opus-5",
        "name": "Opus 5",
        "desc": "مدل Opus 5 (💳 پلن پولی) از XKIRO",
        "cat": "reasoning",
        "tier": "paid",
        "ctx": "128K+"
    },
    {
        "uid": "k13",
        "id": "anthropic/claude-haiku-4.5",
        "name": "Haiku 4.5",
        "desc": "مدل Haiku 4.5 (💳 پلن پولی) از XKIRO",
        "cat": "speed",
        "tier": "paid",
        "ctx": "128K+"
    },
    {
        "uid": "k14",
        "id": "anthropic/claude-opus-4.5",
        "name": "Opus 4.5",
        "desc": "مدل Opus 4.5 (💳 پلن پولی) از XKIRO",
        "cat": "reasoning",
        "tier": "paid",
        "ctx": "128K+"
    },
    {
        "uid": "k15",
        "id": "minimax/minimax-m3",
        "name": "MiniMax M3",
        "desc": "مدل MiniMax M3 (💳 پلن پولی) از XKIRO",
        "cat": "speed",
        "tier": "paid",
        "ctx": "128K+"
    },
    {
        "uid": "k16",
        "id": "minimax/minimax-m2.7",
        "name": "MiniMax M2.7",
        "desc": "مدل MiniMax M2.7 (💳 پلن پولی) از XKIRO",
        "cat": "speed",
        "tier": "paid",
        "ctx": "128K+"
    },
    {
        "uid": "k17",
        "id": "minimax/minimax-m2.7-highspeed",
        "name": "MiniMax M2.7 Highspeed",
        "desc": "مدل MiniMax M2.7 Highspeed (💳 پلن پولی) از XKIRO",
        "cat": "speed",
        "tier": "paid",
        "ctx": "128K+"
    },
    {
        "uid": "k18",
        "id": "openai/gpt-6-astra",
        "name": "GPT-6 Astra",
        "desc": "مدل GPT-6 Astra (💳 پلن پولی) از XKIRO",
        "cat": "reasoning",
        "tier": "paid",
        "ctx": "128K+"
    },
    {
        "uid": "k19",
        "id": "openai/gpt-6-sol",
        "name": "GPT-6 Sol",
        "desc": "مدل GPT-6 Sol (💳 پلن پولی) از XKIRO",
        "cat": "reasoning",
        "tier": "paid",
        "ctx": "128K+"
    },
    {
        "uid": "k20",
        "id": "google/gemini-3.8-flash",
        "name": "Gemini 3.8 Flash",
        "desc": "مدل Gemini 3.8 Flash (💳 پلن پولی) از XKIRO",
        "cat": "speed",
        "tier": "premium",
        "ctx": "128K+"
    },
    {
        "uid": "k21",
        "id": "moonshotai/kimi-k2.8-preview-agent",
        "name": "Kimi K2.8 Preview Agent",
        "desc": "مدل Kimi K2.8 Preview Agent (💳 پلن پولی) از XKIRO",
        "cat": "general",
        "tier": "premium",
        "ctx": "128K+"
    },
    {
        "uid": "k22",
        "id": "qwen/qwen3-vl-plus:free",
        "name": "Qwen3 VL Plus (Free)",
        "desc": "مدل Qwen3 VL Plus (Free) (🆓 رایگان) از XKIRO",
        "cat": "vision",
        "tier": "free",
        "ctx": "128K+"
    },
    {
        "uid": "k23",
        "id": "google/gemini-3.7-flash",
        "name": "Gemini 3.7 Flash",
        "desc": "مدل Gemini 3.7 Flash (💳 پلن پولی) از XKIRO",
        "cat": "speed",
        "tier": "paid",
        "ctx": "128K+"
    },
    {
        "uid": "k24",
        "id": "x-ai/grok-4.6",
        "name": "Grok 4.6",
        "desc": "مدل Grok 4.6 (💳 پلن پولی) از XKIRO",
        "cat": "general",
        "tier": "premium",
        "ctx": "128K+"
    },
    {
        "uid": "k25",
        "id": "cohere/north-mini-code",
        "name": "North Mini Code",
        "desc": "مدل North Mini Code (🆓 رایگان) از XKIRO",
        "cat": "code",
        "tier": "free",
        "ctx": "128K+"
    },
    {
        "uid": "k26",
        "id": "cohere/command-r-08-2024",
        "name": "Command R (08-2024)",
        "desc": "مدل Command R (08-2024) (🆓 رایگان) از XKIRO",
        "cat": "general",
        "tier": "free",
        "ctx": "128K+"
    },
    {
        "uid": "k27",
        "id": "qwen/qwen-plus-2025-07-28:free",
        "name": "Qwen Plus 0728 (Free)",
        "desc": "مدل Qwen Plus 0728 (Free) (🆓 رایگان) از XKIRO",
        "cat": "general",
        "tier": "free",
        "ctx": "128K+"
    },
    {
        "uid": "k28",
        "id": "sensenova/sensenova-6.8-flash-lite",
        "name": "SenseNova 6.8 Flash-Lite",
        "desc": "مدل SenseNova 6.8 Flash-Lite (🆓 رایگان) از XKIRO",
        "cat": "speed",
        "tier": "free",
        "ctx": "128K+"
    },
    {
        "uid": "k29",
        "id": "cohere/command-a",
        "name": "Command A",
        "desc": "مدل Command A (🆓 رایگان) از XKIRO",
        "cat": "general",
        "tier": "free",
        "ctx": "128K+"
    },
    {
        "uid": "k30",
        "id": "cohere/aya-vision-32b",
        "name": "Aya Vision 32B",
        "desc": "مدل Aya Vision 32B (🆓 رایگان) از XKIRO",
        "cat": "vision",
        "tier": "free",
        "ctx": "128K+"
    },
    {
        "uid": "k31",
        "id": "mistralai/ministral-3b",
        "name": "Ministral 3 3B",
        "desc": "مدل Ministral 3 3B (🆓 رایگان) از XKIRO",
        "cat": "speed",
        "tier": "free",
        "ctx": "128K+"
    },
    {
        "uid": "k32",
        "id": "anthropic/claude-sonnet-4",
        "name": "Sonnet 4",
        "desc": "مدل Sonnet 4 (💳 پلن پولی) از XKIRO",
        "cat": "general",
        "tier": "paid",
        "ctx": "128K+"
    },
    {
        "uid": "k33",
        "id": "cohere/tiny-aya-earth",
        "name": "Tiny Aya Earth",
        "desc": "مدل Tiny Aya Earth (🆓 رایگان) از XKIRO",
        "cat": "speed",
        "tier": "free",
        "ctx": "128K+"
    },
    {
        "uid": "k34",
        "id": "cohere/tiny-aya-global",
        "name": "Tiny Aya Global",
        "desc": "مدل Tiny Aya Global (🆓 رایگان) از XKIRO",
        "cat": "speed",
        "tier": "free",
        "ctx": "128K+"
    },
    {
        "uid": "k35",
        "id": "cohere/command-r-plus-08-2024",
        "name": "Command R+ (08-2024)",
        "desc": "مدل Command R+ (08-2024) (🆓 رایگان) از XKIRO",
        "cat": "reasoning",
        "tier": "free",
        "ctx": "128K+"
    },
    {
        "uid": "k36",
        "id": "cohere/aya-expanse-32b",
        "name": "Aya Expanse 32B",
        "desc": "مدل Aya Expanse 32B (🆓 رایگان) از XKIRO",
        "cat": "general",
        "tier": "free",
        "ctx": "128K+"
    },
    {
        "uid": "k37",
        "id": "openai/gpt-5.6-terra",
        "name": "GPT-5.6 Terra",
        "desc": "مدل GPT-5.6 Terra (💳 پلن پولی) از XKIRO",
        "cat": "speed",
        "tier": "paid",
        "ctx": "128K+"
    },
    {
        "uid": "k38",
        "id": "cohere/tiny-aya-fire",
        "name": "Tiny Aya Fire",
        "desc": "مدل Tiny Aya Fire (🆓 رایگان) از XKIRO",
        "cat": "speed",
        "tier": "free",
        "ctx": "128K+"
    },
    {
        "uid": "k39",
        "id": "minimax/minimax-m3.1-flash",
        "name": "MiniMax M3.1 Flash",
        "desc": "مدل MiniMax M3.1 Flash (💳 پلن پولی) از XKIRO",
        "cat": "speed",
        "tier": "paid",
        "ctx": "128K+"
    },
    {
        "uid": "k40",
        "id": "cohere/command-a-plus",
        "name": "Command A+",
        "desc": "مدل Command A+ (🆓 رایگان) از XKIRO",
        "cat": "general",
        "tier": "free",
        "ctx": "128K+"
    },
    {
        "uid": "k41",
        "id": "anthropic/claude-opus-4.6",
        "name": "Opus 4.6",
        "desc": "مدل Opus 4.6 (💳 پلن پولی) از XKIRO",
        "cat": "reasoning",
        "tier": "paid",
        "ctx": "128K+"
    },
    {
        "uid": "k42",
        "id": "openai/gpt-6-luna",
        "name": "GPT-6 Luna",
        "desc": "مدل GPT-6 Luna (💳 پلن پولی) از XKIRO",
        "cat": "reasoning",
        "tier": "paid",
        "ctx": "128K+"
    },
    {
        "uid": "k43",
        "id": "google/gemini-3.5-flash",
        "name": "Gemini 3.5 Flash",
        "desc": "مدل Gemini 3.5 Flash (💳 پلن پولی) از XKIRO",
        "cat": "speed",
        "tier": "paid",
        "ctx": "128K+"
    },
    {
        "uid": "k44",
        "id": "anthropic/claude-sonnet-4.5",
        "name": "Sonnet 4.5",
        "desc": "مدل Sonnet 4.5 (💳 پلن پولی) از XKIRO",
        "cat": "general",
        "tier": "paid",
        "ctx": "128K+"
    },
    {
        "uid": "k45",
        "id": "google/gemini-3.1-pro",
        "name": "Gemini 3.1 Pro",
        "desc": "مدل Gemini 3.1 Pro (💳 پلن پولی) از XKIRO",
        "cat": "reasoning",
        "tier": "paid",
        "ctx": "128K+"
    },
    {
        "uid": "k46",
        "id": "openai/gpt-5.6-luna",
        "name": "GPT-5.6 Luna",
        "desc": "مدل GPT-5.6 Luna (💳 پلن پولی) از XKIRO",
        "cat": "speed",
        "tier": "paid",
        "ctx": "128K+"
    },
    {
        "uid": "k47",
        "id": "anthropic/claude-sonnet-5",
        "name": "Sonnet 5",
        "desc": "مدل Sonnet 5 (💳 پلن پولی) از XKIRO",
        "cat": "general",
        "tier": "paid",
        "ctx": "128K+"
    },
    {
        "uid": "k48",
        "id": "google/gemini-2.5-flash",
        "name": "Gemini 2.5 Flash",
        "desc": "مدل Gemini 2.5 Flash (💳 پلن پولی) از XKIRO",
        "cat": "speed",
        "tier": "paid",
        "ctx": "128K+"
    },
    {
        "uid": "k49",
        "id": "mistralai/mistral-large-4-0",
        "name": "Mistral Large 4",
        "desc": "مدل Mistral Large 4 (💳 پلن پولی) از XKIRO",
        "cat": "general",
        "tier": "paid",
        "ctx": "128K+"
    },
    {
        "uid": "k50",
        "id": "moonshotai/kimi-k3-agent",
        "name": "Kimi K3 Agent",
        "desc": "مدل Kimi K3 Agent (💳 پلن پولی) از XKIRO",
        "cat": "general",
        "tier": "premium",
        "ctx": "128K+"
    },
    {
        "uid": "k51",
        "id": "mistralai/mistral-large-2512",
        "name": "Mistral Large 3",
        "desc": "مدل Mistral Large 3 (🆓 رایگان) از XKIRO",
        "cat": "general",
        "tier": "free",
        "ctx": "128K+"
    },
    {
        "uid": "k52",
        "id": "mistralai/mistral-medium-3.5",
        "name": "Mistral Medium 3.5",
        "desc": "مدل Mistral Medium 3.5 (🆓 رایگان) از XKIRO",
        "cat": "general",
        "tier": "free",
        "ctx": "128K+"
    },
    {
        "uid": "k53",
        "id": "mistralai/mistral-small-2603",
        "name": "Mistral Small 4",
        "desc": "مدل Mistral Small 4 (🆓 رایگان) از XKIRO",
        "cat": "speed",
        "tier": "free",
        "ctx": "128K+"
    },
    {
        "uid": "k54",
        "id": "mistralai/devstral-medium",
        "name": "Devstral 2",
        "desc": "مدل Devstral 2 (🆓 رایگان) از XKIRO",
        "cat": "code",
        "tier": "free",
        "ctx": "128K+"
    },
    {
        "uid": "k55",
        "id": "anthropic/claude-opus-5.5",
        "name": "Opus 5.5",
        "desc": "مدل Opus 5.5 (💳 پلن پولی) از XKIRO",
        "cat": "reasoning",
        "tier": "paid",
        "ctx": "128K+"
    },
    {
        "uid": "k56",
        "id": "mistralai/codestral-2508",
        "name": "Codestral",
        "desc": "مدل Codestral (🆓 رایگان) از XKIRO",
        "cat": "code",
        "tier": "free",
        "ctx": "128K+"
    },
    {
        "uid": "k57",
        "id": "cohere/command-a-translate",
        "name": "Command A Translate",
        "desc": "مدل Command A Translate (🆓 رایگان) از XKIRO",
        "cat": "general",
        "tier": "free",
        "ctx": "128K+"
    },
    {
        "uid": "k58",
        "id": "google/gemini-3-flash",
        "name": "Gemini 3 Flash",
        "desc": "مدل Gemini 3 Flash (💳 پلن پولی) از XKIRO",
        "cat": "speed",
        "tier": "paid",
        "ctx": "128K+"
    },
    {
        "uid": "k59",
        "id": "minimax/minimax-m2.5",
        "name": "MiniMax M2.5",
        "desc": "مدل MiniMax M2.5 (💳 پلن پولی) از XKIRO",
        "cat": "speed",
        "tier": "paid",
        "ctx": "128K+"
    },
    {
        "uid": "k60",
        "id": "minimax/minimax-m2.1",
        "name": "MiniMax M2.1",
        "desc": "مدل MiniMax M2.1 (💳 پلن پولی) از XKIRO",
        "cat": "speed",
        "tier": "paid",
        "ctx": "128K+"
    },
    {
        "uid": "k61",
        "id": "qwen/qwen3-omni-flash:free",
        "name": "Qwen3 Omni Flash (Free)",
        "desc": "مدل Qwen3 Omni Flash (Free) (🆓 رایگان) از XKIRO",
        "cat": "speed",
        "tier": "free",
        "ctx": "128K+"
    },
    {
        "uid": "k62",
        "id": "mistralai/ministral-8b",
        "name": "Ministral 3 8B",
        "desc": "مدل Ministral 3 8B (🆓 رایگان) از XKIRO",
        "cat": "speed",
        "tier": "free",
        "ctx": "128K+"
    },
    {
        "uid": "k63",
        "id": "xiaomi/mimo-v2.6-pro",
        "name": "MiMo v2.6 Pro",
        "desc": "مدل MiMo v2.6 Pro (💳 پلن پولی) از XKIRO",
        "cat": "reasoning",
        "tier": "paid",
        "ctx": "128K+"
    },
    {
        "uid": "k64",
        "id": "google/gemini-2.5-pro",
        "name": "Gemini 2.5 Pro",
        "desc": "مدل Gemini 2.5 Pro (💳 پلن پولی) از XKIRO",
        "cat": "reasoning",
        "tier": "paid",
        "ctx": "128K+"
    },
    {
        "uid": "k65",
        "id": "xiaomi/mimo-v2.6-flash",
        "name": "MiMo v2.6 Flash",
        "desc": "مدل MiMo v2.6 Flash (💳 پلن پولی) از XKIRO",
        "cat": "speed",
        "tier": "paid",
        "ctx": "128K+"
    },
    {
        "uid": "k66",
        "id": "anthropic/claude-opus-4.7",
        "name": "Opus 4.7",
        "desc": "مدل Opus 4.7 (💳 پلن پولی) از XKIRO",
        "cat": "reasoning",
        "tier": "paid",
        "ctx": "128K+"
    },
    {
        "uid": "k67",
        "id": "minimax/minimax-m2.5-highspeed",
        "name": "MiniMax M2.5 Highspeed",
        "desc": "مدل MiniMax M2.5 Highspeed (💳 پلن پولی) از XKIRO",
        "cat": "speed",
        "tier": "paid",
        "ctx": "128K+"
    },
    {
        "uid": "k68",
        "id": "minimax/minimax-m2.1-highspeed",
        "name": "MiniMax M2.1 Highspeed",
        "desc": "مدل MiniMax M2.1 Highspeed (💳 پلن پولی) از XKIRO",
        "cat": "speed",
        "tier": "paid",
        "ctx": "128K+"
    },
    {
        "uid": "k69",
        "id": "minimax/minimax-m2",
        "name": "MiniMax M2",
        "desc": "مدل MiniMax M2 (💳 پلن پولی) از XKIRO",
        "cat": "speed",
        "tier": "paid",
        "ctx": "128K+"
    },
    {
        "uid": "k70",
        "id": "xiaomi/mimo-v2.5",
        "name": "MiMo v2.5",
        "desc": "مدل MiMo v2.5 (💳 پلن پولی) از XKIRO",
        "cat": "general",
        "tier": "paid",
        "ctx": "128K+"
    },
    {
        "uid": "k71",
        "id": "qwen/qwen3.6-plus:free",
        "name": "Qwen3.6 Plus (Free)",
        "desc": "مدل Qwen3.6 Plus (Free) (🆓 رایگان) از XKIRO",
        "cat": "general",
        "tier": "free",
        "ctx": "128K+"
    },
    {
        "uid": "k72",
        "id": "qwen/qwen3.7-max:free",
        "name": "Qwen3.7 Max (Free)",
        "desc": "مدل Qwen3.7 Max (Free) (🆓 رایگان) از XKIRO",
        "cat": "general",
        "tier": "free",
        "ctx": "128K+"
    },
    {
        "uid": "k73",
        "id": "meituan/longcat-2.0",
        "name": "LongCat 2.0",
        "desc": "مدل LongCat 2.0 (🆓 رایگان) از XKIRO",
        "cat": "general",
        "tier": "free",
        "ctx": "128K+"
    },
    {
        "uid": "k74",
        "id": "meituan/longcat-2.5-preview:free",
        "name": "LongCat 2.5 Preview (Free)",
        "desc": "مدل LongCat 2.5 Preview (Free) (🆓 رایگان) از XKIRO",
        "cat": "general",
        "tier": "free",
        "ctx": "128K+"
    },
    {
        "uid": "k75",
        "id": "openai/gpt-5.6-sol",
        "name": "GPT-5.6 Sol",
        "desc": "مدل GPT-5.6 Sol (💳 پلن پولی) از XKIRO",
        "cat": "general",
        "tier": "paid",
        "ctx": "128K+"
    },
    {
        "uid": "k76",
        "id": "qwen/qwen3.7-plus:free",
        "name": "Qwen3.7 Plus (Free)",
        "desc": "مدل Qwen3.7 Plus (Free) (🆓 رایگان) از XKIRO",
        "cat": "general",
        "tier": "free",
        "ctx": "128K+"
    },
    {
        "uid": "k77",
        "id": "nvidia/nemotron-3-ultra",
        "name": "Nemotron 3 Ultra",
        "desc": "مدل Nemotron 3 Ultra (💳 پلن پولی) از XKIRO",
        "cat": "general",
        "tier": "paid",
        "ctx": "128K+"
    },
    {
        "uid": "k78",
        "id": "stealth/big-pickle",
        "name": "Big Pickle (Free)",
        "desc": "مدل Big Pickle (Free) (🆓 رایگان) از XKIRO",
        "cat": "general",
        "tier": "free",
        "ctx": "128K+"
    },
    {
        "uid": "k79",
        "id": "qwen/qwen3.5-omni-flash:free",
        "name": "Qwen3.5 Omni Flash (Free)",
        "desc": "مدل Qwen3.5 Omni Flash (Free) (🆓 رایگان) از XKIRO",
        "cat": "speed",
        "tier": "free",
        "ctx": "128K+"
    },
    {
        "uid": "k80",
        "id": "cohere/command-r7b-12-2024",
        "name": "Command R7B (12-2024)",
        "desc": "مدل Command R7B (12-2024) (🆓 رایگان) از XKIRO",
        "cat": "general",
        "tier": "free",
        "ctx": "128K+"
    },
    {
        "uid": "k81",
        "id": "nvidia/nemotron-3-nano-omni",
        "name": "Nemotron 3 Nano Omni",
        "desc": "مدل Nemotron 3 Nano Omni (💳 پلن پولی) از XKIRO",
        "cat": "general",
        "tier": "paid",
        "ctx": "128K+"
    },
    {
        "uid": "k82",
        "id": "qwen/qwen3.8-max:free",
        "name": "Qwen3.8 Max (Free)",
        "desc": "مدل Qwen3.8 Max (Free) (🆓 رایگان) از XKIRO",
        "cat": "general",
        "tier": "free",
        "ctx": "128K+"
    },
    {
        "uid": "k83",
        "id": "qwen/qwen3.8-omni-flash:free",
        "name": "Qwen3.8 Omni Flash (Free)",
        "desc": "مدل Qwen3.8 Omni Flash (Free) (🆓 رایگان) از XKIRO",
        "cat": "speed",
        "tier": "free",
        "ctx": "128K+"
    },
    {
        "uid": "k84",
        "id": "qwen/qwen3.7-flash:free",
        "name": "Qwen3.7 Flash (Free)",
        "desc": "مدل Qwen3.7 Flash (Free) (🆓 رایگان) از XKIRO",
        "cat": "speed",
        "tier": "free",
        "ctx": "128K+"
    },
    {
        "uid": "k85",
        "id": "qwen/qwen3.6-max-preview:free",
        "name": "Qwen3.6 Max Preview (Free)",
        "desc": "مدل Qwen3.6 Max Preview (Free) (🆓 رایگان) از XKIRO",
        "cat": "general",
        "tier": "free",
        "ctx": "128K+"
    },
    {
        "uid": "k86",
        "id": "qwen/qwen3-coder-plus:free",
        "name": "Qwen3 Coder Plus (Free)",
        "desc": "مدل Qwen3 Coder Plus (Free) (🆓 رایگان) از XKIRO",
        "cat": "reasoning",
        "tier": "free",
        "ctx": "128K+"
    },
    {
        "uid": "k87",
        "id": "cohere/north-small-translate",
        "name": "North Small Translate",
        "desc": "مدل North Small Translate (🆓 رایگان) از XKIRO",
        "cat": "speed",
        "tier": "free",
        "ctx": "128K+"
    },
    {
        "uid": "k88",
        "id": "qwen/qwen3.6-27b:free",
        "name": "Qwen3.6 27B (Free)",
        "desc": "مدل Qwen3.6 27B (Free) (🆓 رایگان) از XKIRO",
        "cat": "general",
        "tier": "free",
        "ctx": "128K+"
    },
    {
        "uid": "k89",
        "id": "qwen/qwen3.5-plus:free",
        "name": "Qwen3.5 Plus (Free)",
        "desc": "مدل Qwen3.5 Plus (Free) (🆓 رایگان) از XKIRO",
        "cat": "general",
        "tier": "free",
        "ctx": "128K+"
    },
    {
        "uid": "k90",
        "id": "cohere/command-a-vision",
        "name": "Command A Vision",
        "desc": "مدل Command A Vision (🆓 رایگان) از XKIRO",
        "cat": "vision",
        "tier": "free",
        "ctx": "128K+"
    },
    {
        "uid": "k91",
        "id": "cohere/command-a-reasoning",
        "name": "Command A Reasoning",
        "desc": "مدل Command A Reasoning (🆓 رایگان) از XKIRO",
        "cat": "reasoning",
        "tier": "free",
        "ctx": "128K+"
    },
    {
        "uid": "k92",
        "id": "qwen/qwen3.5-omni-plus:free",
        "name": "Qwen3.5 Omni Plus (Free)",
        "desc": "مدل Qwen3.5 Omni Plus (Free) (🆓 رایگان) از XKIRO",
        "cat": "general",
        "tier": "free",
        "ctx": "128K+"
    },
    {
        "uid": "k93",
        "id": "qwen/qwen3.6-35b-a3b:free",
        "name": "Qwen3.6 35B A3B (Free)",
        "desc": "مدل Qwen3.6 35B A3B (Free) (🆓 رایگان) از XKIRO",
        "cat": "general",
        "tier": "free",
        "ctx": "128K+"
    },
    {
        "uid": "k94",
        "id": "qwen/qwen3.5-flash:free",
        "name": "Qwen3.5 Flash (Free)",
        "desc": "مدل Qwen3.5 Flash (Free) (🆓 رایگان) از XKIRO",
        "cat": "speed",
        "tier": "free",
        "ctx": "128K+"
    },
    {
        "uid": "k95",
        "id": "cohere/tiny-aya-water",
        "name": "Tiny Aya Water",
        "desc": "مدل Tiny Aya Water (🆓 رایگان) از XKIRO",
        "cat": "speed",
        "tier": "free",
        "ctx": "128K+"
    },
    {
        "uid": "k96",
        "id": "qwen/qwen3.5-397b-a17b:free",
        "name": "Qwen3.5 397B A17B (Free)",
        "desc": "مدل Qwen3.5 397B A17B (Free) (🆓 رایگان) از XKIRO",
        "cat": "general",
        "tier": "free",
        "ctx": "128K+"
    },
    {
        "uid": "k97",
        "id": "qwen/qwen3-max:free",
        "name": "Qwen3 Max (Free)",
        "desc": "مدل Qwen3 Max (Free) (🆓 رایگان) از XKIRO",
        "cat": "general",
        "tier": "free",
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
    if not config.XKIRO_KEY:
        log.warning("XKIRO_KEY is not configured")
        return ""
    headers = {"Authorization": f"Bearer {config.XKIRO_KEY}"}
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
        log.warning("Xkiro chat error on %s: %s", model, type(e).__name__)
        return ""


def call_tools(messages: list, model: str = DEFAULT_MODEL, tools_def=None, temperature: float = 0.7, max_tokens: int = 2048, timeout: int = 35) -> dict:
    from ai_engine import providers, tools
    if not config.XKIRO_KEY:
        raise ValueError("XKIRO_KEY is not configured")
    headers = {"Authorization": f"Bearer {config.XKIRO_KEY}"}
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
