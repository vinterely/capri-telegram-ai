# 🌟 Capri — Autonomous Telegram AI Userbot (v1.6.0)

[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![Telethon](https://img.shields.io/badge/telethon-1.36+-0088cc.svg)](https://docs.telethon.dev/)
[![Architecture](https://img.shields.io/badge/architecture-Autonomous%20ReAct%20Agent-orange.svg)]()
[![Tests](https://img.shields.io/badge/unit%20tests-137%20passed%20(100%25)-brightgreen.svg)]()
[![Release](https://img.shields.io/badge/release-v1.6.0-blueviolet.svg)](https://github.com/vinterely/capri-telegram-ai/releases/tag/v1.6.0)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

🌐 **Language / زبان:** **English** | [فارسی (Persian)](README_FA.md)

**Capri** is an ultra-advanced, autonomous personal assistant userbot running directly on your personal Telegram account via Telethon MTProto.

Unlike traditional rule-based chatbots or brittle regex routers, Capri is an **Autonomous ReAct Agent**, **Smart Saved Messages Forum Vault**, **Invisible Smart Reactions Assistant**, **Intelligent DND & Schedule Manager**, **Study Partner & Document Analyst (PDF OCR / Code)**, **Digital Twin (Ghost Mode Persona Emulation)**, **Chat & Relationship Behavioral Profiler (Vibe Check)**, **Real-Time Deep Research Engine**, and a **48kHz Opus Studio Voice Synthesizer**.

Capri requires no third-party cloud servers. It runs entirely on your local machine, VPS, or cloud homelab, turning your Telegram account into an intelligent, autonomous command center.

---

> 📖 **New to Capri?** Follow the step-by-step setup guide in [TUTORIAL.md](TUTORIAL.md) to get running in under 5 minutes.

---

## 📋 Table of Contents
- [What's New in v1.6.0](#-whats-new-in-v160)
- [Key Features & Architecture](#-key-features--architecture)
  - [1. Autonomous ReAct Agent & Multi-Provider Failover](#1-autonomous-react-agent--multi-provider-failover)
  - [2. Capri Vault: Smart Saved Messages Organizer](#2-capri-vault-smart-saved-messages-organizer)
  - [3. Invisible Smart Reactions Assistant](#3-invisible-smart-reactions-assistant)
  - [4. Intelligent DND & Scheduled Reminders](#4-intelligent-dnd--scheduled-reminders)
  - [5. Channel & Folder Management](#5-channel--folder-management)
  - [6. Study Partner, PDF OCR & Code Analysis](#6-study-partner-pdf-ocr--code-analysis)
  - [7. Digital Twin (Ghost Mode)](#7-digital-twin-ghost-mode)
  - [8. Real-Time Web Research & Image Search](#8-real-time-web-research--image-search)
  - [9. 48kHz Opus Voice Synthesizer](#9-48khz-opus-voice-synthesizer)
  - [10. Media Flow & YouTube Bridge](#10-media-flow--youtube-bridge)
- [Quick Start](#-quick-start)
- [Multi-Layer Security Architecture](#-multi-layer-security-architecture)
- [Supported Providers & Models](#-supported-providers--models)
- [Verification & Test Suite](#-verification--test-suite)
- [License](#-license)

---

## 🚀 What's New in v1.6.0

- ⚡ **Zero-Retry Fast Failover:** Eliminates lagging network loops; instantly fails over on broken SSL/HTTP connections.
- 🎬 **Smart Media & AI Button Navigation:** Intelligent multi-level inline button navigation with subtitle vs dubbed matching, quality selection (480p, 720p, 1080p), cycle breakers, and strict back-button filtering.
- 🛡️ **Fail-Closed Access Whitelist:** Thread-safe, atomic 0600 `access.json` control with silent stranger rejection and owner commands (`کاپری مجوز بده` / `کاپری مجوز بگیر` / `کاپری لیست مجوزها`).
- ⏰ **Natural Language Reminder Engine:** Fully stem-aware Persian/English reminder parser with single-item deletion (`یادآور ۱ رو پاک کن`) and bulk wipe (`پاک کردن یادآورها`).
- 📢 **Stem-Aware Channel Scanner:** Deep dialog scanner (500+ chats) with root-stem matching (e.g., `کنکور` / `کنکوری`) and numbered confirmation.
- 🎙️ **Multi-Voice Studio Audio:** Microsoft Edge-TTS support with instant voice switching (`دلارا` / `فرید`).
- 🛡️ **Anti-Prompt Injection & Taint Quarantine:** Protects against untrusted external chat messages while guaranteeing zero-denial of owner capabilities.
- 🧪 **137 Unit Tests (100% Pass Rate):** Full automated test coverage across all routing, security, media navigation, parsing, reaction, and vault subsystems.

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

### 2. Capri Vault: Smart Saved Messages Organizer
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

### 3. Invisible Smart Reactions Assistant
Triggers actions simply by reacting with emojis:
- 🤡 **Clown:** Generates a savage, contextual AI roast directly replying to the target.
- 🎙️ **Microphone:** Transcribes voice notes with Whisper STT and sends deep takeaways to Saved Messages.
- 👍 / ❤️ **Like / Heart:** Automatically archives the message into its Capri Vault topic.
- 👀 **Eyes:** Creates a 1-hour reminder in Saved Messages for later follow-up.

### 4. Intelligent DND & Scheduled Reminders
- **Smart DND:** Auto-replies politely to direct messages and mentions during sleep, study, work, or meetings, with real-time Saved Messages logging and emergency escalation.
- **Natural Language Reminders:** Add, list, or clear reminders naturally (`کاپری ۲ ساعت دیگه یادم بنداز...`, `کاپری یادآور رو پاک کن`).

### 5. Channel & Folder Management
- Lists and organizes Telegram folders.
- Deep scans up to 500 dialogs to find matching channels and safely leaves unwanted channels in batches with numbered confirmation.

### 6. Study Partner, PDF OCR & Code Analysis
Directly upload textbook PDFs, scanned documents, Word files, or source code. Capri reads, extracts formulas, summarizes key points, and solves coding bugs.

### 7. Digital Twin (Ghost Mode)
Learns your chatting style, emojis, sentence length, and vocabulary from recent chats to generate natural replies in private messages when you're away.

### 8. Real-Time Web Research & Image Search
Searches Google and crawls web pages for live prices, sports results, news, and gaming guides, returning clean Markdown tables.

### 9. 48kHz Opus Voice Synthesizer
Generates studio-grade voice notes using Edge-TTS with natural Persian speakers (`دلارا` / `فرید`), converted to Opus voice messages playable directly in Telegram.

### 10. Media Flow & YouTube Bridge
Downloads YouTube videos in 720p/1080p via Telegram bot bridges and extracts English/Persian video summaries directly from transcripts.

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

Capri includes an exhaustive 137-unit test suite verifying all logic:
```bash
python -m unittest discover -s tests
```
```text
Ran 137 tests in 3.4s
OK (All passed)
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
