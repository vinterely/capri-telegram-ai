# Capri — Advanced Autonomous Telegram AI Userbot (v2.2.0)

<p align="center">
  <img src="https://raw.githubusercontent.com/vinterely/capri-telegram-ai/main/assets/banner.png" alt="Capri Telegram AI Banner" width="700" onerror="this.style.display='none'"/>
</p>

<p align="center">
  <a href="https://github.com/vinterely/capri-telegram-ai/releases"><img src="https://img.shields.io/badge/version-2.2.0-blue.svg" alt="Version 2.2.0"/></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue" alt="Python Version"/></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License"/></a>
  <a href="MODELS.md"><img src="https://img.shields.io/badge/models-253%20AI%20Models-orange" alt="Supported Models"/></a>
</p>

---

## 🌟 Overview

**Capri** is an advanced, production-grade Telegram Userbot driven by an **Autonomous ReAct Agent architecture** and native **Function Calling**. Built on top of [Telethon](https://github.com/LonamiWebs/Telethon) (Telegram MTProto client library), Capri turns any personal Telegram account into a proactive, intelligent personal assistant.

Unlike simple rule-based bots, Capri understands user intent, autonomously decides whether to leverage tools or answer directly, manages media downloads, organizes Telegram chats into forum topics, transcribes voice notes, drafts responses, and maintains long-term cognitive memory.

---

## 🚀 Key Features

### 1. 🧠 Autonomous ReAct Agent & Multi-Provider Architecture
- **Self-Governing Tool Execution:** Capri dynamically queries tools or answers using internal knowledge based on semantic intent.
- **Over 20 Specialized Tools:** Trilingual web search, deep page reading, YouTube summarization, audio/music search, channel file lookup, media navigation, and automated memo drafting.
- **Context Grounding:** Seamlessly understands contextual references (e.g., *"Sort the last 100 messages here"* in Saved Messages, or *"Archive this"* when replying to a message in a group).
- **Multi-Provider Failover & Circuit Breaker:**
  - **XKIRO:** 97 flagship and free models (prefix `k`)
  - **B.AI:** 62 official models (prefix `b`)
  - **AnyAPI:** Fast Gemini and Nemotron models (prefix `a`)
  - **OpenRouter:** 15 free open-source models (prefix `o`)
  - **Groq:** Ultra-low latency tool-calling inference (`g1`..`g3`)
  - **Hooshia:** Persian-native GLM models (`h1`..`h3`)
  - **Inception Labs:** Mercury 3 Diffusion LLM (`i1`)

### 2. 🤖 Interactive Model Selector & Universal UID System
Switch between 253 AI models instantly using short Unique Identifiers (UIDs) or natural language commands:
- `k1` / `Capri model k1` ➔ Flagship fast model from XKIRO
- `a1` / `Capri model a1` ➔ Gemini 2.5 Flash Lite from AnyAPI
- `o3` / `Capri model o3` ➔ Nemotron 3.5 Lightning from OpenRouter
- `b1` / `Capri model b1` ➔ MiniMax M3.1 Flash from B.AI
- **Interactive Inline Menu:** Saying `Capri models` or `Capri list models` brings up an interactive Telegram pagination menu to browse and switch models with a single tap.
- **Full Catalog:** View the complete list of 253 models with specifications in [`MODELS.md`](MODELS.md).

### 3. 📁 Capri Vault — Automated Telegram Forum Supergroup
- **Intelligent Organization:** Automatically creates and pins a private Telegram supergroup (`Capri Vault`) with dedicated forum topics.
- **Topic Classification:** Automatically routes messages into dedicated topics:
  - 📝 Personal & Notes
  - 🎬 Movies & Series
  - 💻 Code & Development
  - 📁 Documents & Archives
  - 🎵 Music & Audio
  - 🌐 Links & Web Content
  - 🎮 Gaming & Emulation
- **Zero Token Heuristics & Fallback:** Fast classification layer for instant routing without token consumption, with semantic fallback for complex messages.

### 4. ⚡ Smart Reaction Shortcuts
Perform background actions with single-click emoji reactions:
- **❤️ / 👍 (Heart / Like on Channels):** Analyzes post contents and archives directly into the appropriate topic in Capri Vault.
- **🎙️ / ✍️ (Microphone / Write on Voices):** Transcribes voice notes with Whisper and delivers an actionable summary to Saved Messages.
- **🤡 (Clown):** Generates a sharp, witty roast reply directed at the message sender.
- **👀 (Eyes / Laptop):** Automatically schedules an hourly reminder in Saved Messages.

### 5. 🎙️ High-Fidelity Voice Synthesis (TTS) & Whisper Transcription
- **48kHz Opus Telegram Voice Messages:** Transmits studio-grade voice notes directly in Telegram voice message bubble format.
- **Multiple TTS Engines:**
  - Telegram Voice Bot integration with 7 distinct speakers and 6 expressive tones.
  - Microsoft Edge-TTS with natural bilingual neural voices (`fa-IR-DilaraNeural` & `fa-IR-FaridNeural`).
  - Google Gemini TTS fallback.

### 6. 🎬 Smart Media & Social Downloader Navigation
- **Social Media Downloader:** Automatically detects Instagram, TikTok, Pinterest, X/Twitter, and SoundCloud links and fetches original media via automated userbot conduits.
- **Autonomous Download Navigation:** Navigates inline button interfaces on download bots, resolving multi-step selections, quality options, and multi-season TV show episodes autonomously.
- **Deezer Music Integration:** Searches Deezer and retrieves 320kbps MP3 tracks with complete album metadata and lyrics.

### 7. 🎲 Roleplay & Ghostwriter Engines
- **Stateful Roleplay:** Dungeon-master / game-narrator mode with isolated character state, inventory, and episodic memory maintained in a dedicated session state.
- **Ghostwriter & Chat Profiling:** Analyzes user speech patterns and drafts natural replies matching personal writing tone while respecting privacy constraints.

---

## 🛠️ Directory Structure

```text
capri-telegram-ai/
│
├── bot.py                      # Telegram dispatcher, event handlers, and UI routers
├── login.py                    # Initial MTProto login and session generator
├── start.py                    # Interactive setup and dependency manager
├── run.bat / run.sh            # One-click launchers for Windows and Linux/macOS
├── MODELS.md                   # Complete reference catalog of 253 AI models
├── LICENSE                     # MIT License
│
├── core/                       # Core system infrastructure
│   ├── config.py               # Environment configuration and validation
│   ├── logger.py               # Sanitized logging system with secret redaction
│   ├── fsutil.py               # Atomic filesystem utility (temp + os.replace)
│   ├── access.py               # Access control policy manager
│   ├── cache.py                # In-memory TTL cache for searches
│   ├── settings.py             # Active model and voice settings state
│   ├── memory.py               # Fact-based episodic memory store
│   └── cognitive_memory.py     # Cognitive user modeling and background reflection loop
│
├── ai_engine/                  # Decision-making and AI integration
│   ├── agent.py                # Autonomous ReAct agent loop and circuit breaker
│   ├── prompts.py              # System identity prompts and personality directives
│   ├── tools.py                # Schema definitions and dispatcher for 20+ tools
│   ├── ai.py                   # High-level LLM interface
│   ├── providers.py            # Resilient HTTP transport with connection pooling
│   ├── models.py               # Model catalog registry, natural parser & UID routing
│   ├── provider_xkiro.py       # XKIRO provider module (97 models, UID: k)
│   ├── provider_bai.py         # B.AI provider module (62 models, UID: b)
│   ├── provider_anyapi.py      # AnyAPI provider module (7 models, UID: a)
│   ├── provider_openrouter.py  # OpenRouter provider module (15 models, UID: o)
│   └── skills_manager.py       # Dynamic skill registry and runtime compiler
│
├── services/                   # Modular service packages
│   ├── media/                  # Media navigation, YouTube, Deezer, and Social DL
│   ├── social/                 # DND reminders, Vault supergroup, Ghostwriter, Roleplay
│   ├── voice/                  # TTS voice synthesis and Whisper transcription
│   ├── search/                 # Google Serper, web reader, and channel search
│   └── telegram/               # Channel management, folder sorting, and reactions
│
└── tests/                      # Automated test suite (156 comprehensive unit tests)
```

---

## ⚙️ Installation & Quick Start

### Prerequisites
- **Python 3.10+** (Python 3.11 or 3.12 recommended)
- **Telegram API Credentials** (`api_id` and `api_hash` from [my.telegram.org](https://my.telegram.org))
- **FFmpeg** (Recommended for audio encoding; automatically detected in system PATH)

### 1. Clone the Repository
```bash
git clone https://github.com/vinterely/capri-telegram-ai.git
cd capri-telegram-ai
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Edit `.env` and fill in your credentials:
```ini
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=your_api_hash_here

# Provider API Keys (Fill in at least one)
OPENROUTER_API_KEY=your_openrouter_key
GROQ_API_KEY=your_groq_key
XKIRO_KEY=your_xkiro_key
ANYAPI_KEY=your_anyapi_key
BAI_KEY=your_bai_key
```

### 3. Launch with One Click
- **Windows:** Double-click `run.bat`
- **Linux / macOS:** Run `chmod +x run.sh && ./run.sh`

The launcher will automatically configure a virtual environment (`venv`), install dependencies, guide you through Telegram authentication, and start the userbot.

### 4. Running via Docker
```bash
docker compose up -d
```

---

## 🧪 Testing

Capri features a comprehensive automated test suite covering routing, tool validation, circuit breakers, and state persistence:

```bash
python -m unittest discover -s tests
```
*Current test suite: **156 tests passing** with 100% success rate.*

---

## 🔒 Security & Privacy

- **On-Device Execution:** All operations run locally on your system or personal VPS. No third-party proxy servers intermediate your Telegram MTProto connection.
- **Secret Redaction:** Logs automatically scrub API keys, phone numbers, and session hashes.
- **Isolated State:** Sensitive credentials are kept strictly in `.env` and excluded via `.gitignore`.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
