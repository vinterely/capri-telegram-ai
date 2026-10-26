# Capri — Advanced Autonomous Telegram AI Userbot (v2.7.0)

<p align="center">
  <img src="https://raw.githubusercontent.com/vinterely/capri-telegram-ai/main/assets/banner.png" alt="Capri Telegram AI Banner" width="700" onerror="this.style.display='none'"/>
</p>

<p align="center">
  <a href="https://github.com/vinterely/capri-telegram-ai/releases"><img src="https://img.shields.io/badge/version-2.7.0-blue.svg" alt="Version 2.7.0"/></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue" alt="Python Version"/></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License"/></a>
  <a href="MODELS.md"><img src="https://img.shields.io/badge/models-253%20AI%20Models-orange" alt="Supported Models"/></a>
  <a href="tests/"><img src="https://img.shields.io/badge/tests-225%20passing-brightgreen.svg" alt="Test Suite"/></a>
</p>

---

> 📖 **Persian Documentation:** For the full Persian manual and guide, see [README_FA.md](README_FA.md).  
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

### 2. 🤖 Universal Model Selector (253 Models across 7 Providers)
Switch between 253 state-of-the-art AI models instantly via short Unique Identifiers (UIDs) or natural language:
- **XKIRO (`k1`..`k97`):** 97 flagship, coding, and open-source models.
- **B.AI (`b1`..`b62`):** 62 enterprise and conversational models (MiniMax, Claude, GPT-4o).
- **AnyAPI (`a1`..`a7`):** Fast Google Gemini and Nemotron models.
- **OpenRouter (`o1`..`o15`):** 15 free open-source LLMs.
- **Groq (`g1`..`g3`):** Ultra-low latency inference (`Qwen-3.8-27b`, `GPT-OSS`).
- **Hooshia (`h1`..`h3`):** Native colloquial Persian models (`GLM-4.5-Flash`, `GLM-4.7-Flash`).
- **Inception Labs (`i1`):** Mercury 3 Diffusion-LLM with native tool-calling.
- **Interactive Inline Pagination:** Send `Capri models` or `/models` to open an interactive Telegram pagination menu to browse, inspect, and activate models with single taps.
- **Intent-Guarded Matching:** Discrete word-boundary matching prevents accidental model switching when words like "must" (*باید*), language levels (*B2*), or vitamins (*B1*) appear in regular text.

### 3. 💬 Deep Reply Context & Situational Environment Grounding
- **Structured Reply Context (`get_reply_info`):** When replying to any Telegram message, Capri extracts the original message text, media type, links, message ID, and the original author's numeric Telegram ID and display name.
- **Direct Summarization on Reply:** Replying to any long article or message with *"Summarize this"* (*خلاصه کن*) automatically injects the original text into the summarization pipeline.
- **Automatic Link Forwarding:** Replying with *"Download this"* or *"Summarize video"* to a message containing a YouTube, Instagram, or TikTok link automatically routes the link to the appropriate handler.
- **Group Identity Separation:** Accurately distinguishes between the current sender and the author of the replied-to message in group chats, eliminating identity confusion.
- **Honest Handling of Deleted Messages:** If a replied-to message was deleted or inaccessible, Capri transparently informs the user rather than hallucinating or pretending to read it.

### 4. 🛡️ Scoped Memory Architecture & Privacy Isolation
- **Namespace Partitioning:** Memory records are strictly partitioned into isolated namespaces:
  - `memory:group:<chat_id>`: Shared group chat memory.
  - `memory:dm:<user_id>`: Individual private direct message memory.
  - `memory:saved:<owner_id>`: Personal Saved Messages memory space.
- **Zero Privacy Leakage:** Replying to a user in a group chat never exposes or queries private facts from private direct messages.
- **Short-Term Context vs. Long-Term Memory:** Separates immediate conversational reply context from persistent biographical memory.

### 5. 🎯 Zero-Hallucination & Intent-Driven Request Routing
A strict 6-layer separation of concerns eliminates accidental tool execution and false claims:
1. **Intent Detection:** Definitively classifies requests into explicit download, content summary, metadata lookup, or general conversational QA.
2. **Tool Authorization:** Enforces role-based permissions (owner vs. guest) and quarantine state (Taint tracking).
3. **Execution & Feedback:** Handles tool timeouts, retries, and error feedback.
4. **Result Validation:** Separates media download failure from Telegram transmission issues.
5. **Telegram Transmission:** Securely forwards media files with platform error handling.
6. **Persona Synthesis:** Generates faithful responses without distorting technical outputs.
- **Anti-Visual-Hallucination Guard in Video Summaries:** When summarizing YouTube videos via metadata and web snippets, Capri strictly enforces negative constraints preventing fabricated visual descriptions of camera work, lighting, acting, or directing.
- **Truthfulness Guard (`_finalize`):** If an operational tool fails, the agent is strictly prohibited from claiming success or stating that the file was sent.

### 6. 🌸 Personality & Social Dynamics
- **Charming & Witty Persona:** Independent, dignified, playful, and charming female assistant persona with high self-esteem.
- **Colloquial Persian Fluency:** Natural, living colloquial Persian conversations combined with rigorous technical problem-solving for coding and engineering queries.
- **Social Dynamic States:** Smoothly adapts behavioral tone across `friendly`, `playful`, `focused`, `serious`, and `empathetic` states based on conversation cues.
- **Behavioral Hurt & Relationship Repair:** Expresses hurt through subtle behavioral changes (shorter, serious replies without emojis) rather than repetitive complaints, and graciously accepts apologies without holding grudges.

### 7. 🌐 Trilingual Deep Research (`gsearch.py`)
- **Parallel Multi-Regional Search:** Translates queries into English (global sources, GitHub, Reddit), Chinese (NGA gaming forums, deep guides), and Persian simultaneously.
- **Pre-Agent YouTube Discovery:** Retrieves validated video links, view counts, and metadata before agent execution.
- **Automatic Markdown Export:** Long responses (>4000 chars) or large code snippets are automatically packaged and delivered as clean `.md` files.

### 8. 🎙️ High-Fidelity Voice Synthesis (TTS) & Whisper Transcription
- **48kHz Opus Voice Notes:** Sends studio-grade audio bubbles directly in Telegram's native voice note format.
- **Multiple TTS Engines:**
  - Telegram Voice Bot integration with 7 distinct voices and 6 expressive tones.
  - Microsoft Edge-TTS with natural neural voices (`fa-IR-DilaraNeural` & `fa-IR-FaridNeural`).
  - Google Gemini TTS fallback.
- **Whisper Voice-to-Text:** Transcribes voice notes and voice messages with fast summaries delivered to Saved Messages.

### 9. 📁 Capri Vault — Automated Telegram Forum Supergroup
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
├── start.py                    # Dependency wizard and setup manager
├── run.bat / run.sh            # One-click launchers for Windows and Linux/macOS
├── Dockerfile                  # Production container definition
├── docker-compose.yml          # Container orchestration template
├── MODELS.md                   # Reference catalog of 253 AI models and UIDs
├── TUTORIAL.md                 # Complete step-by-step setup tutorial
├── README.md                   # English documentation (this file)
├── README_FA.md                # Comprehensive Persian documentation
├── requirements.txt            # Production dependencies
├── requirements-dev.txt        # Development and testing dependencies
│
├── core/                       # Core system modules
│   ├── config.py               # Environment validation and credentials
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
│   ├── media/                  # Video, audio, social downloads & YouTube summaries
│   │   ├── ytsummary.py        # YouTube metadata summarizer with anti-hallucination guard
│   │   ├── ytdownload.py       # Autonomous video downloader
│   │   └── socialdl.py         # Instagram, TikTok, X, Pinterest & SoundCloud downloader
│   ├── search/                 # Trilingual Google Serper web search
│   ├── voice/                  # Edge-TTS, Gemini TTS & Jarvis voice synthesis
│   ├── telegram/               # Smart reactions and Vault forum supergroup
│   └── social/                 # Ghostwriter, roleplay & chat analysis
│
└── tests/                      # Comprehensive test suite (225 passing tests)
    ├── test_reply_context_and_model_regression.py  # 10 mandatory regression scenarios
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

#### Method B: Manual Setup
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

#### Method C: Docker Deployment
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

# Assistant Configuration
ASSISTANT_NAME=Capri,کاپری
OWNER_NAME=YourName
```

---

## 🧪 Testing & Verification

Capri includes an extensive automated test suite covering all ReAct workflows, memory isolation namespaces, tool routings, social dynamics, and regression scenarios:

```bash
# Run all 225 unit and regression tests
python -m unittest discover -s tests

# Run dedicated reply context & model switching regression tests
python -m unittest tests/test_reply_context_and_model_regression.py
```

All 225 tests pass out of the box with zero failures.

---

## 📄 License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for complete details.

---

<p align="center">
  Crafted with ❤️ for intelligent, transparent, and respectful human-AI coexistence.
</p>
