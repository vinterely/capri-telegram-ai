# 🌟 Capri — Autonomous Telegram AI Userbot (v2.0.0)

[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![Telethon](https://img.shields.io/badge/telethon-1.36+-0088cc.svg)](https://docs.telethon.dev/)
[![Architecture](https://img.shields.io/badge/architecture-Autonomous%20ReAct%20Agent-orange.svg)]()
[![Tests](https://img.shields.io/badge/unit%20tests-156%20passed%20(100%25)-brightgreen.svg)]()
[![Release](https://img.shields.io/badge/release-v2.0.0-blueviolet.svg)](https://github.com/vinterely/capri-telegram-ai/releases/tag/v2.0.0)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

🌐 **Language / زبان:** **English** | [فارسی (Persian)](README_FA.md)

**Capri** is an ultra-advanced, autonomous personal assistant userbot running directly on your personal Telegram account via Telethon MTProto.

Unlike traditional rule-based chatbots or brittle regex routers, Capri is an **Autonomous ReAct Agent**, **Interactive Roleplay & Game Master**, **Smart Saved Messages Forum Vault**, **Invisible Smart Reactions Assistant**, **Intelligent DND & Schedule Manager**, **Study Partner & Document Analyst (PDF OCR / Code)**, **Digital Twin (Ghost Mode Persona Emulation)**, **Chat & Relationship Behavioral Profiler (Vibe Check)**, **Real-Time Deep Research Engine**, and a **Triple-Engine Opus Studio Voice Synthesizer**.

Capri requires no third-party cloud servers. It runs entirely on your local machine, VPS, or cloud homelab, turning your Telegram account into an intelligent, autonomous command center.

---

> 📖 **New to Capri?** Follow the step-by-step setup guide in [TUTORIAL.md](TUTORIAL.md) to get running in under 5 minutes.

---

## 📋 Table of Contents
- [What's New in v2.0.0](#-whats-new-in-v200)
- [Key Features & Architecture](#-key-features--architecture)
  - [1. Autonomous ReAct Agent & Multi-Provider Failover](#1-autonomous-react-agent--multi-provider-failover)
  - [2. Interactive Roleplay & Game Master Engine](#2-interactive-roleplay--game-master-engine)
  - [3. Capri Vault: Smart Saved Messages Organizer](#3-capri-vault-smart-saved-messages-organizer)
  - [4. Invisible Smart Reactions Assistant](#4-invisible-smart-reactions-assistant)
  - [5. Intelligent DND & Scheduled Reminders](#5-intelligent-dnd--scheduled-reminders)
  - [6. Channel & Folder Management](#6-channel--folder-management)
  - [7. Study Partner, PDF OCR & Code Analysis](#7-study-partner-pdf-ocr--code-analysis)
  - [8. Digital Twin (Ghost Mode)](#8-digital-twin-ghost-mode)
  - [9. Real-Time Web Research & Image Search](#9-real-time-web-research--image-search)
  - [10. Triple-Engine Voice Synthesizer & Jarvoice Bot](#10-triple-engine-voice-synthesizer--jarvoice-bot)
  - [11. Autonomous Media Flow & YouTube Bridge](#11-autonomous-media-flow--youtube-bridge)
- [Quick Start](#-quick-start)
- [Multi-Layer Security Architecture](#-multi-layer-security-architecture)
- [Supported Providers & Models](#-supported-providers--models)
- [Verification & Test Suite](#-verification--test-suite)
- [License](#-license)

---

## 🚀 What's New in v2.0.0

- 🎭 **Interactive Roleplay & Game Master Engine (`roleplay.py`):**
  Full interactive world-building, multi-character generation (2–4 controllable characters with attributes, backstory, and inventory), turn-by-turn dynamic narration with consequence tracking, state persistence in `roleplay.json`, and pause/resume lifecycle commands (`کاپری رول پلی شروع کن`, `کاپری رول پلی نگه دار`, `کاپری رول پلی ادامه`).
- 🎙️ **Jarvoice Studio TTS Engine (`@jarvis_roobot`):**
  Ultra-realistic Persian voice synthesis with 7 distinct speakers (Baran, Sara, Arash, Keyvan, Bahram, Negin, Omid) and 6 mood tones (Natural, Friendly, Formal, Energetic, Calm, Epic).
- 🔄 **Multi-Key Gemini Voice Failover & Emergency Edge-TTS:**
  Multi-key round-robin quota rotation for Google Gemini TTS (`GEMINI_API_KEY`, `GEMINI_API_KEY_2`) with automatic 429 backoff and instant Microsoft Edge-TTS fallback.
- 🎬 **Autonomous 0-to-100 Media Navigation (`ai_nav.py`):**
  Full support for both inline keyboard buttons and text slash commands (`/dl_...`), direct channel file streaming, anti-loop circuit breaker, and strict prompt compliance (`زیرنویس 480`).
- ✍️ **Persian Grammar & Text Normalization Engine (`persian_writing.py`):**
  Automated text revision, zero-width non-joiner (ZWNJ / نیم‌فاصله) correction, and character cleanup.
- 🛡️ **Fail-Closed Access Whitelist (`access.json`):**
  Atomic 0600 file write, 30-second rate-limiting, and owner-only management (`کاپری لیست مجوزها`, `کاپری مجوز بده`, `کاپری مجوز بگیر`).
- 🧪 **156 Automated Unit Tests (100% Pass Rate):**
  Exhaustive test suite covering all routing, security, media navigation, roleplay, voice multikey, reactions, and vault subsystems.

---

## 🧠 Key Features & Architecture

```
                  ┌─────────────────────────────────────────┐
                  │         Incoming Telegram Event         │
                  └────────────────────┬────────────────────┘
                                       │
                    ┌──────────────────┴──────────────────┐
                    ▼                                     ▼
        ┌───────────────────────┐             ┌───────────────────────┐
        │ Direct Fast Handlers  │             │   ReAct AI Agent      │
        │ • Image Search        │             │ • Google Gemini       │
        │ • DND & Reminders     │             │ • Inception Mercury-3 │
        │ • Channel Leave       │             │ • Groq Llama / Qwen   │
        │ • Smart Reactions     │             │ • Multi-Step Tools    │
        └───────────┬───────────┘             └───────────┬───────────┘
                    │                                     │
                    └──────────────────┬──────────────────┘
                                       ▼
                  ┌─────────────────────────────────────────┐
                  │    Autonomous Execution & Feedback      │
                  │  (Saved Messages / Chat Reply / Vault)  │
                  └─────────────────────────────────────────┘
```

### 1. Autonomous ReAct Agent & Multi-Provider Failover
Capri plans, reasons, and executes multi-step actions autonomously using function calling. It orchestrates tools for file search, calculations, reminders, channel administration, and web intelligence, backed by automatic circuit-breaker failover.

### 2. Interactive Roleplay & Game Master Engine
Turns Capri into an interactive storyteller, world-builder, and dungeon/game master (`roleplay.py`):
- Dynamic setting and world generation across any genre (Medieval Fantasy, Cyberpunk, Survival, Modern Life, Sci-Fi).
- Automated character sheet design (2–4 controllable characters with attributes, health, inventory, and secrets).
- Interactive turn-by-turn narrative with meaningful choice consequences.
- Full game lifecycle management: start (`کاپری رول پلی شروع کن`), pause/save (`کاپری رول پلی نگه دار`), resume (`کاپری رول پلی ادامه`), and climactic wrap-up (`کاپری رول پلی تموم کن`).
- Complete context isolation: roleplay runs in its own state file (`roleplay.json`) without polluting long-term memory.

### 3. Capri Vault: Smart Saved Messages Organizer
Transforms your chaotic Telegram "Saved Messages" into a structured, searchable private supergroup forum with 9 topic channels:
- 🎵 Audio & Music
- 🎬 Movies & Series
- 📚 Books, PDFs & Education
- 💻 Code, Tech & Programming
- 🎮 Gaming & Entertainment
- 💡 Ideas, Notes & Articles
- 💳 Financial & Receipts
- 🛠 Tools & Utilities
- 🗂 General Archives

### 4. Invisible Smart Reactions Assistant
Triggers actions simply by reacting with emojis:
- 🤡 **Clown:** Generates a savage, contextual AI roast directly replying to the target.
- 🎙️ **Microphone:** Transcribes voice notes with Whisper STT and sends deep takeaways to Saved Messages.
- 👍 / ❤️ **Like / Heart:** Automatically archives the message into its Capri Vault topic.
- 👀 **Eyes:** Creates a 1-hour reminder in Saved Messages for later follow-up.

### 5. Intelligent DND & Scheduled Reminders
- **Smart DND:** Auto-replies politely to direct messages and mentions during sleep, study, work, or meetings, with real-time Saved Messages logging and emergency escalation.
- **Natural Language Reminders:** Add, list, or clear reminders naturally (`کاپری ۲ ساعت دیگه یادم بنداز...`, `کاپری یادآور رو پاک کن`).

### 6. Channel & Folder Management
- Lists and organizes Telegram folders.
- Deep scans up to 500 dialogs to find matching channels and safely leaves unwanted channels in batches with numbered confirmation.

### 7. Study Partner, PDF OCR & Code Analysis
Directly upload textbook PDFs, scanned documents, Word files, or source code. Capri reads, extracts formulas, summarizes key points, and solves coding bugs.

### 8. Digital Twin (Ghost Mode)
Learns your chatting style, emojis, sentence length, and vocabulary from recent chats to generate natural replies in private messages when you're away.

### 9. Real-Time Web Research & Image Search
Searches Google and crawls web pages for live prices, sports results, news, and gaming guides, returning clean Markdown tables.

### 10. Triple-Engine Voice Synthesizer & Jarvoice Bot
- **Jarvoice Telegram Engine (`@jarvis_roobot`):** 7 distinct speakers (Baran, Sara, Arash, Keyvan, Bahram, Negin, Omid) and 6 mood tones (Natural, Friendly, Formal, Energetic, Calm, Epic) for lifelike Persian voice output.
- **Google Gemini TTS (`gemini-3.8-flash-tts`):** 5 AI voices with multi-key round-robin rotation and automatic 429 quota backoff.
- **Microsoft Edge-TTS:** Instant, unlimited fallback with natural voices (`دلارا` / `فرید`).

### 11. Autonomous Media Flow & YouTube Bridge
- Autonomous 0-to-100 bot navigation supporting both inline buttons and plaintext slash commands (`/dl_...`), direct channel file streaming, anti-loop circuit breaker, and strict quality/audio matching.
- Downloads YouTube videos in 720p/1080p via Telegram bot bridges and extracts English/Persian video summaries directly from transcripts.

---

## ⚡ Quick Start

```bash
# 1. Clone repository
git clone https://github.com/vinterely/capri-telegram-ai.git
cd capri-telegram-ai

# 2. Run Interactive Launcher
# On Windows:
run.bat
# On Linux / macOS:
chmod +x run.sh && ./run.sh
```

Follow the on-screen wizard to:
1. Generate your `.env` configuration.
2. Authenticate your Telegram session (`login.py`).
3. Run the automated test suite.
4. Start Capri!

For detailed instructions, see the complete [TUTORIAL.md](TUTORIAL.md).

---

## 🛡️ Multi-Layer Security Architecture

- **Local Session Storage:** Session files are stored exclusively on your machine and never transmitted to external servers.
- **Strict Anti-Prompt Injection:** Messages from external users, channels, or web scrapers are treated as untrusted data and strictly prevented from hijacking agent tools.
- **Circuit Breaker Protection:** Isolates failing API providers, preventing cascading timeouts.
- **Owner-Exclusive Authorization:** System commands, channel operations, DND, and reminders can only be triggered by the authenticated account owner.

---

## 🧪 Verification & Test Suite

Capri includes an exhaustive 156-unit test suite verifying all logic:
```bash
python -m unittest discover -s tests
```
```text
Ran 156 tests in 14.3s
OK (All passed)
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
