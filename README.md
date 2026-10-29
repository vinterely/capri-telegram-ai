# Capri — Advanced Autonomous Telegram AI Userbot (v3.1.0)

<p align="center">
  <img src="https://raw.githubusercontent.com/vinterely/capri-telegram-ai/main/assets/banner.png" alt="Capri Telegram AI Banner" width="700" onerror="this.style.display='none'"/>
</p>

<p align="center">
  <a href="https://github.com/vinterely/capri-telegram-ai/releases"><img src="https://img.shields.io/badge/version-3.1.0-blue.svg" alt="Version 3.1.0"/></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue" alt="Python Version"/></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License"/></a>
  <a href="MODELS.md"><img src="https://img.shields.io/badge/models-253%20AI%20Models-orange" alt="Supported Models"/></a>
  <a href="tests/"><img src="https://img.shields.io/badge/tests-284%20passing-brightgreen.svg" alt="Test Suite"/></a>
</p>

---

> 📖 **Persian Documentation:** For the complete Persian manual and guide, see [README_FA.md](README_FA.md).  
> 📘 **Step-by-Step Installation Guide:** See [TUTORIAL.md](TUTORIAL.md).  
> 📄 **Complete 253 Model Catalog & UIDs:** See [MODELS.md](MODELS.md).

---

## 🌟 Overview

**Capri** is an advanced, production-ready Telegram Userbot driven by an **Autonomous ReAct Agent Architecture** and native **Function Calling**. Built on top of [Telethon](https://github.com/LonamiWebs/Telethon) (Telegram MTProto client library), Capri transforms your personal Telegram account into a proactive, intelligent personal assistant.

Unlike ordinary command-based bots, Capri operates as a true cognitive agent: it autonomously reasons, selects and sequences tools, navigates interactive Telegram interfaces, extracts situational context from replies and groups, protects private memories across isolated namespaces, and synthesizes responses with social intelligence and zero hallucinations.

---

## 🚀 Key Architectural Highlights & Features

### 1. 🧠 Centralized Autonomous ReAct Agent Cycle
Capri features a dedicated **ReAct Agent Loop** (Reasoning + Acting + Observing) engineered for production resilience:
- **Multi-Step Tool Orchestration:** Executes sequential tool calls dynamically (e.g., searching web documentation, retrieving channel archives, and synthesizing code) while observing intermediate outcomes.
- **Strict Step Limiting:** Enforces strict execution bounds (default: 6 steps) to prevent infinite loops, with automatic fallback to direct response synthesis on the final step.
- **JSON Error Feedback Loop:** Catches invalid tool arguments or schema errors and feeds structured correction prompts back to the LLM for self-correction.
- **Per-Request State Isolation (`AgentState`):** Every Telegram request possesses an isolated execution state with unique request IDs, independent error logs, and dedicated taint scopes.
- **Circuit Breaker & Multi-Provider Failover:** Automatically detects HTTP 429 rate limits, quota exhaustions, and provider timeouts, suspending faulty endpoints with proportional cooldowns and seamlessly failing over to healthy providers.
- **Synchronized Solar Hijri & Gregorian Date Awareness:** Today's Solar Hijri (Jalali) date, Gregorian date, Persian weekday, exact time, and validated timezone (default: `Asia/Tehran`, configurable via `TIMEZONE` in `.env`) are calculated from system clock and injected dynamically on every request and into web search query optimization.
- **True Operation Cancellation (`core/ops.py`):** Active asynchronous tasks (ReAct loops, downloads, long searches) are registered in a per-chat operation registry. Commands such as *"Cancel"*, *"Stop"*, or *"Nevermind"* (*«کنسل»*, *«لغو کن»*, *«متوقفش کن»*) immediately cancel the running task for that specific chat without affecting other concurrent tasks.

### 2. 🎀 Emotional Stickers Engine (`services/social/stickers.py` & `sticker_library.json`)
- **Emotion-Mapped Sticker Pack:** Automatically compiles a categorized sticker catalog from the configured Telegram sticker pack (`Vinterely`, customizable via `STICKER_PACK_SHORTNAME`).
- **9 Core Affective Dimensions:** Maps sticker emojis to distinct emotional categories: *Laughter* (خنده), *Joy* (شادی), *Sadness* (غم), *Love* (عشق), *Surprise* (تعجب), *Anger* (خشم), *Fatigue* (خستگی), *Wink* (چشمک), and *Praise* (تشویق).
- **Fast-Path & Autonomous Tool Calling:** Sends contextual stickers during high-emotion conversational moments (jokes, empathy, celebration) with strict 15-minute per-chat cooldowns to prevent spam, while exposing the `send_sticker` tool to the ReAct agent.
- **Zero-Hallucination Fallback:** If the pack is inaccessible or unpopulated, no stickers are sent—avoiding broken links or empty messages.

### 3. 💡 Structured Ideation & Brainstorming (`custom_skills/ideation.py`)
- **Multi-Perspective Strategy:** Initiates an accelerated, structured brainstorming pipeline upon natural ideation prompts (*«یه ایده بده»*, *«ایده‌پردازی کن»*, *«طوفان فکری»*, *«خلاق باش»*).
- **Comprehensive Innovation Framework:** Produces target assumptions, unconventional out-of-the-box concepts, low-friction quick wins, bold high-risk/high-reward ideas, feasibility breakdowns, and sharpening refinement questions.
- **Cognitive Profile Alignment:** Smoothly tailors idea domains to user interests recorded in cognitive memory without hallucinating fake statistics or fictitious sources.

### 4. 🏠 Capri Home — Private Management Supergroup & Dialog Folder (`services/telegram/home.py`)
Bootstraps and maintains an automated administrative hub on Telegram:
- **Forum Supergroup (`🏠 Capri Home | مدیریت کاپری`):** A private forum supergroup where the owner can chat with Capri directly without trigger keywords or prefixes.
- **Telegram Dialog Folder (`capri`):** Automatically creates a clean dialog folder grouping the Capri Home supergroup and the Capri Vault supergroup together.
- **Dedicated Forum Topics:**
  - `🗂 بکاپ` (Backup): Receives verified pre-deletion message backups before message removal.
  - `📰 خلاصه کانال‌ها` (Channel Summaries): Receives periodic digests of subscribed Telegram channels.

### 5. 🗑️ Owner Message Cleaner with Verified Backup (`services/telegram/cleaner.py`)
Enables clean and safe message deletion for the account owner (*«کاپری ۱۰ پاک کن»* / *«کاپری ۵ پیام پاک کن»*):
- **Guaranteed Pre-Deletion Backup:** Zero messages are deleted without confirmed backup. Target messages and metadata are first forwarded to the Home `🗂 بکاپ` topic.
- **Selective Deletion:** Only messages whose backup succeeded are revoked and deleted from the target chat; failed backups remain completely untouched.
- **Confirmation Threshold:** Deleting more than 20 messages requires explicit interactive confirmation to prevent accidental bulk loss.

### 6. 📰 Periodic Channel Summarizer (`services/telegram/channel_summary.py`)
- **Automated Channel Ingestion:** Monitor important channels with natural commands (*«این کانال رو به خلاصه اضافه کن»* or *«کانال‌های خلاصه»*).
- **Scheduled Background Polling:** Polls new posts every 30 minutes, tracking message cursors in `channel_summary.json` to prevent duplicates.
- **High-Fidelity AI Digests:** Synthesizes structured, link-attributed Persian digests delivered directly to the Home `📰 خلاصه کانال‌ها` topic.

### 7. 🎧 Voice Mode — Continuous Hands-Free Voice Interaction
- **Voice Mode Toggle:** Enable or disable hands-free conversation with *«حالت ویس روشن»* / *«حالت ویس خاموش»* (persisted in `settings.json`).
- **Triggerless Voice Interaction:** When Voice Mode is active, any incoming voice note or video note from the owner is automatically transcribed via Whisper and answered with a synthesized voice note—no trigger words needed.

### 8. 🔕 Smart Absence, Do Not Disturb & Missed Inbox (`services/social/dnd.py`)
- **Natural Absence Understanding:** Recognizes absence duration expressions (*«من تا ساعت ۸ نیستم»*, *«تا فردا صبح جلسه دارم»*).
- **AI-Powered Away Auto-Replies:** Generates contextual, polite away responses for private chats and group mentions with a single-reply-per-sender guard to prevent notification spam.
- **Missed Messages Inbox:** Logs incoming inquiries during owner absence into a bounded inbox. Upon return, asking *«چی شد وقتی نبودم»* yields a concise summary of missed messages and senders.

### 9. 🤖 Universal Model Selector (253 Models across 7 Providers)
Switch between 253 state-of-the-art AI models instantly via short Unique Identifiers (UIDs) or natural language:
- **XKIRO (`k1`..`k97`):** 97 flagship, coding, and open-source models.
- **B.AI (`b1`..`b62`):** 62 enterprise and conversational models (MiniMax, Claude, GPT-4o).
- **AnyAPI (`a1`..`a7`):** Fast Google Gemini and Nemotron models.
- **OpenRouter (`o1`..`o15`):** 15 free open-source LLMs.
- **Groq (`g1`..`g3`):** Ultra-low latency inference (`Qwen-3.8-27b`, `GPT-OSS`).
- **Hooshia (`h1`..`h3`):** Native colloquial Persian models (`GLM-4.5-Flash`, `GLM-4.7-Flash`).
- **Inception Labs (`i1`):** Mercury 3 Diffusion-LLM with native tool-calling.
- **Interactive Inline Pagination:** Send `Capri models` or `/models` to open an interactive Telegram pagination menu to browse, inspect, and activate models with single taps.

### 10. 💬 Deep Reply Context & Situational Environment Grounding
- **Structured Reply Context (`get_reply_info`):** When replying to any Telegram message, Capri extracts the original message text, media type, links, message ID, and author identity.
- **Direct Summarization on Reply:** Replying to any long article or message with *"Summarize this"* (*خلاصه کن*) automatically injects the original text into the summarization pipeline.
- **Automatic Link Forwarding:** Replying with *"Download this"* or *"Summarize video"* to a message containing a YouTube, Instagram, or TikTok link automatically routes the link to the appropriate handler.
- **Group Identity Separation:** Accurately distinguishes between the current sender and the author of the replied-to message in group chats, eliminating identity confusion.

### 11. 🛡️ Scoped Memory Architecture & Privacy Isolation
- **Namespace Partitioning:** Memory records are strictly partitioned into isolated namespaces:
  - `memory:group:<chat_id>`: Shared group chat memory.
  - `memory:dm:<user_id>`: Individual private direct message memory.
  - `memory:saved:<owner_id>`: Personal Saved Messages memory space.
- **Zero Privacy Leakage:** Replying to a user in a group chat never exposes or queries private facts from private direct messages.
- **Cognitive Reflection:** Automatically extracts user preferences, communication styles, and interaction insights in private conversations.

### 12. 🎙️ High-Fidelity Voice Synthesis (TTS) & Whisper Transcription
- **48kHz Opus Voice Notes:** Sends studio-grade audio bubbles directly in Telegram's native voice note format.
- **Multiple TTS Engines:**
  - Telegram Voice Bot integration with 7 distinct voices and 6 expressive tones.
  - Microsoft Edge-TTS with natural neural voices (`fa-IR-DilaraNeural` & `fa-IR-FaridNeural`).
  - Google Gemini TTS fallback.
- **Whisper Voice-to-Text:** Transcribes voice notes and voice messages with fast summaries delivered to Saved Messages.

### 13. 📁 Capri Vault — Automated Telegram Forum Supergroup
- **Forum Organization:** Automatically sets up and manages a private forum supergroup (`Capri Vault`) with 7 categorized topics:
  - 📝 Personal & Notes
  - 🎬 Movies & Series
  - 💻 Code & Development
  - 📁 Documents & Archives
  - 🎵 Music & Audio
  - 🌐 Links & Web Content
  - 🎮 Gaming & Emulation
- **Smart Reaction Shortcuts:** React with `❤️` or `👍` on channels to archive posts directly into Capri Vault; react with `🎙️` on voices to transcribe with Whisper; react with `🤡` to deliver a witty roast; or react with `👀` to set an hourly reminder.

---

## 🛠️ Project Structure

```text
capri-telegram-ai/
│
├── bot.py                      # Telegram event handlers, context builders & routing
├── login.py                    # Interactive MTProto login and session generator
├── quickstart.py               # All-in-one setup & proxy wizard
├── start.py                    # Dependency wizard and setup manager
├── run.bat / run.sh            # One-click launchers for Windows and Linux/macOS
├── Dockerfile                  # Production container definition
├── docker-compose.yml          # Container orchestration template
├── MODELS.md                   # Reference catalog of 253 AI models and UIDs
├── TUTORIAL.md                 # Complete step-by-step setup tutorial
├── README.md                   # English documentation (this file)
├── README_FA.md                # Comprehensive Persian documentation
├── sticker_library.json        # Pre-compiled emotional sticker cache
├── requirements.txt            # Production dependencies
├── requirements-dev.txt        # Development and testing dependencies
│
├── core/                       # Core system modules
│   ├── config.py               # Environment validation and credentials
│   ├── ops.py                  # Active operations registry & per-chat task cancellation
│   ├── logger.py               # Secret-redacting logging framework
│   ├── fsutil.py               # Atomic filesystem transactions
│   ├── access.py               # Role-based access control (RBAC)
│   ├── settings.py             # Active model and voice state management
│   ├── memory.py               # Scoped episodic and long-term memory store
│   ├── cognitive_memory.py     # Cognitive user modeling and reflection loop
│   └── social_dynamics.py      # Behavioral state machine and relationship repair
│
├── ai_engine/                  # Intelligence & inference layers
│   ├── agent.py                # Autonomous ReAct agent loop and circuit breaker
│   ├── prompts.py              # System identity prompts, personality & tool inventory
│   ├── tools.py                # Schema definitions and dispatcher for 20+ tools
│   ├── ai.py                   # High-level LLM interface & synchronized date/time injection
│   ├── providers.py            # Resilient HTTP transport with connection pooling
│   ├── models.py               # Model catalog registry, natural parser & UID routing
│   ├── provider_xkiro.py       # XKIRO provider module (97 models, UID: k)
│   ├── provider_bai.py         # B.AI provider module (62 models, UID: b)
│   ├── provider_anyapi.py      # AnyAPI provider module (7 models, UID: a)
│   ├── provider_openrouter.py  # OpenRouter provider module (15 models, UID: o)
│   └── skills_manager.py       # Dynamic skill registry and runtime compiler
│
├── services/                   # Modular service packages
│   ├── telegram/               # Telegram infrastructure
│   │   ├── home.py             # Capri Home supergroup, topics & folder management
│   │   ├── cleaner.py          # Owner message deletion with verified backup
│   │   ├── channel_summary.py  # Periodic channel digestion scheduler
│   │   ├── vault.py            # Forum supergroup & topic organization
│   │   ├── folders.py          # Telegram dialog folder management
│   │   └── reactions.py        # Smart invisible reaction handlers
│   ├── media/                  # Video, audio, social downloads & YouTube summaries
│   │   ├── ytsummary.py        # YouTube metadata summarizer with anti-hallucination guard
│   │   ├── ytdownload.py       # Autonomous video downloader
│   │   ├── ai_nav.py           # Interactive inline-keyboard automation
│   │   └── socialdl.py         # Instagram, TikTok, X, Pinterest & SoundCloud downloader
│   ├── search/                 # Trilingual Google Serper web search with current year injection
│   ├── voice/                  # Edge-TTS, Gemini TTS & Jarvis voice synthesis
│   └── social/                 # Stickers, ideation, DND, ghostwriter, meme generator & roast
│
└── tests/                      # Comprehensive test suite (284 passing tests)
    ├── test_date_cancel_absence.py          # Dynamic date, cancellation & absence tests
    ├── test_home_voice_cleaner_summary.py   # Home, Voice Mode, Cleaner & Channel Summary tests
    ├── test_reply_context_and_model_regression.py  # Regression scenarios
    ├── test_tools_and_routing_audit.py             # Tool audit & intent separation
    ├── test_memory_scopes_and_isolation.py         # Scoped namespace memory isolation
    ├── test_capri_persona_and_social.py            # Personality & social dynamics
    └── test_ai_core_and_memory.py                  # Core agent & memory tests
```

---

## ⚡ Quick Start

### 1. Prerequisites
- **Python 3.10, 3.11, or 3.12** installed ([python.org](https://www.python.org/downloads/)).
- **FFmpeg** installed and accessible in your system `PATH` (required for voice note encoding).
- Telegram `API_ID` and `API_HASH` from [my.telegram.org](https://my.telegram.org).

### 2. Installation & Setup

#### Method A: The One-Click Launcher (Recommended)

- **On Windows:** Double-click `run.bat` or run:
  ```cmd
  run.bat
  ```
- **On Linux / macOS:** Run:
  ```bash
  chmod +x run.sh
  ./run.sh
  ```
The launcher will automatically create a Python virtual environment, install all dependencies, verify FFmpeg, prompt for configuration if missing, and launch Capri.

#### Method B: Quickstart Script
```bash
python quickstart.py
```
Automatically configures proxy settings, logs into Telegram interactively, and starts the bot.

#### Method C: Manual Setup
```bash
# 1. Clone the repository
git clone https://github.com/vinterely/capri-telegram-ai.git
cd capri-telegram-ai

# 2. Create and activate a virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Open .env and add your Telegram API credentials and AI keys

# 5. Authorize Telegram session (one-time interactive login)
python login.py

# 6. Start Capri
python bot.py
```

#### Method D: Docker Deployment
```bash
docker-compose up -d --build
```

---

## ⚙️ Configuration (`.env`)

Copy `.env.example` to `.env` and configure your credentials:

```ini
# Telegram MTProto Credentials (from https://my.telegram.org)
API_ID=12345678
API_HASH=your_api_hash_here

# Assistant Configuration
ASSISTANT_NAME=Capri,کاپری
OWNER_NAME=YourName
TIMEZONE=Asia/Tehran
HOME_GROUP_TITLE=🏠 Capri Home | مدیریت کاپری
CAPRI_FOLDER_TITLE=capri
STICKER_PACK_SHORTNAME=Vinterely

# Primary AI Provider Keys
GEMINI_API_KEY=your_gemini_api_key_here
INCEPTION_API_KEY=your_inception_key_here    # Mercury 3 fast diffusion agent
GROQ_API_KEY=your_groq_api_key_here          # Ultra-fast inference & Whisper
HOOSHIA_API_KEY=your_hooshia_api_key_here    # Native Persian models
XKIRO_KEY=your_xkiro_key_here                # 97 models (k1..k97)
BAI_KEY=your_bai_key_here                    # 62 models (b1..b62)
ANYAPI_KEY=your_anyapi_key_here              # Fast Gemini & Nemotron (a1..a7)
OPENROUTER_API_KEY=your_openrouter_key_here  # Free open-source models (o1..o15)

# Web & YouTube Search
SERPER_API_KEY=your_serper_api_key_here
```

---

## 🧪 Testing & Verification

Capri includes an extensive automated test suite covering all ReAct workflows, memory isolation namespaces, tool routings, social dynamics, date awareness, cancellation, and regression scenarios:

```bash
# Run all 284 unit and regression tests
python -m unittest discover -s tests

# Run dedicated date, cancellation & absence tests
python -m unittest tests/test_date_cancel_absence.py tests/test_home_voice_cleaner_summary.py
```

All 284 tests pass out of the box with zero failures.

---

## 📄 License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for complete details.

---

<p align="center">
  Crafted with ❤️ for intelligent, transparent, and respectful human-AI coexistence.
</p>
