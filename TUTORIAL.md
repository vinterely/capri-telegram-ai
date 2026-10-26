# 📘 Capri AI Userbot [v2.7.0] - Comprehensive Setup Tutorial

Welcome to the definitive setup tutorial for **Capri (v2.7.0)**, an autonomous Telegram AI userbot powered by Telethon and multi-provider ReAct agent intelligence.

This tutorial guides you from a blank machine to a fully running, production-ready Capri userbot in under 5 minutes.

---

## 📑 Table of Contents
1. [Prerequisites](#1-prerequisites)
2. [Step 1: Obtain Telegram API Credentials](#2-step-1-obtain-telegram-api-credentials)
3. [Step 2: Obtain AI & Search API Keys](#3-step-2-obtain-ai--search-api-keys)
4. [🚀 Method 1: The One-Click Launcher (run.bat / run.sh)](#4--method-1-the-one-click-launcher-runbat--runsh)
5. [🧙 Method 2: The Interactive Python Wizard (start.py)](#5--method-2-the-interactive-python-wizard-startpy)
6. [🐳 Method 3: Docker Deployment (Recommended for Servers/VPS)](#6--method-3-docker-deployment-recommended-for-serversvps)
7. [🛠️ Method 4: Manual Terminal Setup](#7-️-method-4-manual-terminal-setup)
8. [Step 4: Testing Key Commands & Features (v2.7.0)](#8-step-4-testing-key-commands--features-v270)
9. [Step 5: Production 24/7 Daemon Execution](#9-step-5-production-247-daemon-execution)
10. [Troubleshooting & FAQ](#10-troubleshooting--faq)

---

## 1. Prerequisites

Before installing Capri, verify that your machine meets the following requirements:

- **Operating System:** Windows 10/11, Ubuntu 20.04+, Debian, macOS, or any Linux server.
- **Python:** Python **3.10**, **3.11**, or **3.12** ([Download Python](https://www.python.org/downloads/)).
  - *Note for Windows users:* Check the box **"Add python.exe to PATH"** during installation.
- **Git:** Installed on your system ([Download Git](https://git-scm.com/)).
- **FFmpeg (Crucial for Voice Notes & Audio):**
  - **Linux (Debian/Ubuntu):**
    ```bash
    sudo apt update && sudo apt install -y ffmpeg
    ```
  - **macOS:**
    ```bash
    brew install ffmpeg
    ```
  - **Windows:** Download FFmpeg from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) or install via winget:
    ```powershell
    winget install Gyan.FFmpeg
    ```
    Verify in terminal with `ffmpeg -version`.

---

## 2. Step 1: Obtain Telegram API Credentials

Capri connects directly to the Telegram MTProto network as a user client via Telethon.

1. Navigate to **[https://my.telegram.org](https://my.telegram.org)** in your web browser.
2. Log in using your Telegram phone number (in international format, e.g., `+1...` or `+98...`) and enter the verification code sent to your Telegram app.
3. Once logged in, click on **API development tools**.
4. Fill in the form:
   - **App title:** `Capri Assistant` (or any custom name)
   - **Short name:** `capri`
   - **Platform:** Desktop or Other
5. Click **Create application**.
6. You will see two essential fields:
   - **`api_id`**: A numeric ID (e.g., `12345678`).
   - **`api_hash`**: A 32-character hexadecimal string (e.g., `abcdef0123456789abcdef0123456789`).
7. Save these securely; you will paste them into `.env`.

---

## 3. Step 2: Obtain AI & Search API Keys

Capri supports multiple AI providers with automatic circuit-breaker failover. You need **at least one** LLM provider (Google Gemini is free and recommended to start):

### 1. Google Gemini (Primary / Vision / Fallback) — **Recommended & Free**
- Go to [Google AI Studio](https://aistudio.google.com/apikey).
- Create a free project and generate your API key (`GEMINI_API_KEY`).
- *(Optional)* Add a second key (`GEMINI_API_KEY_2`) to double your rate limits.

### 2. Inception Labs / Mercury 3 (Diffusion-LLM with Native Tool-Calling) — **Recommended**
- Register at [Inception Labs](https://api.inceptionlabs.ai).
- Get your `INCEPTION_API_KEY` for ultra-fast ReAct reasoning (`mercury-3`, UID: `i1`).

### 3. Groq (Ultra-Fast Inference & Whisper Transcription) — **Recommended**
- Register at [Groq Console](https://console.groq.com/keys).
- Create your `GROQ_API_KEY` (used for `whisper-large-v3-turbo` audio transcription and `qwen/qwen3.8-27b`).

### 4. XKIRO, B.AI & AnyAPI (200+ Flagship & Specialized Models) — **Optional**
- **XKIRO:** [xkiro.com](https://xkiro.com) ➔ `XKIRO_KEY` (97 models, UIDs `k1`..`k97`).
- **B.AI:** [b.ai](https://b.ai) ➔ `BAI_KEY` (62 models, UIDs `b1`..`b62`).
- **AnyAPI:** [anyapi.ai](https://anyapi.ai) ➔ `ANYAPI_KEY` (7 models, UIDs `a1`..`a7`).
- **OpenRouter:** [openrouter.ai](https://openrouter.ai) ➔ `OPENROUTER_API_KEY` (15 models, UIDs `o1`..`o15`).

### 5. Hooshia (Persian-Native Models) — **Optional**
- Register at [Hooshia.com](https://hooshia.com).
- Obtain `HOOSHIA_API_KEY` for high-fidelity colloquial Persian GLM models without VPN (`h1`..`h3`).

### 6. Google Serper (Real-Time Web & YouTube Search) — **Recommended**
- Register at [Serper.dev](https://serper.dev).
- Get your free `SERPER_API_KEY` (provides 2,500 free Google searches for real-time web retrieval).

---

## 4. 🚀 Method 1: The One-Click Launcher (run.bat / run.sh)

Capri provides an automated launcher that handles virtual environment creation, dependency installation, configuration checking, testing, and execution automatically.

### On Windows:
1. Clone the repository:
   ```bash
   git clone https://github.com/vinterely/capri-telegram-ai.git
   cd capri-telegram-ai
   ```
2. Double-click `run.bat` (or run `run.bat` in Command Prompt / PowerShell).
3. The wizard will create `.env` if missing, guide you through interactive setup, and launch the bot.

### On Linux / macOS:
1. Clone the repository:
   ```bash
   git clone https://github.com/vinterely/capri-telegram-ai.git
   cd capri-telegram-ai
   ```
2. Make `run.sh` executable and run it:
   ```bash
   chmod +x run.sh
   ./run.sh
   ```

---

## 5. 🧙 Method 2: The Interactive Python Wizard (start.py)

If you prefer an interactive console setup:
```bash
python start.py
```
`start.py` performs environment checks, prompts for missing keys, runs connection diagnostics, and boots Capri.

---

## 6. 🐳 Method 3: Docker Deployment (Recommended for Servers/VPS)

1. Clone the repository and configure `.env`:
   ```bash
   git clone https://github.com/vinterely/capri-telegram-ai.git
   cd capri-telegram-ai
   cp .env.example .env
   # Edit .env with your credentials
   ```

2. Perform one-time Telegram authentication on your host machine to generate `session.session`:
   ```bash
   python login.py
   ```

3. Launch via Docker Compose:
   ```bash
   docker-compose up -d --build
   ```

4. View logs:
   ```bash
   docker-compose logs -f
   ```

---

## 7. 🛠️ Method 4: Manual Terminal Setup

For developers configuring their environment step-by-step:

### 1. Clone & Set Up Virtual Environment
```bash
git clone https://github.com/vinterely/capri-telegram-ai.git
cd capri-telegram-ai

# Create virtual environment
python -m venv venv

# Activate venv:
# Linux/macOS:
source venv/bin/activate
# Windows PowerShell:
.\venv\Scripts\Activate.ps1

# Install requirements
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Configure `.env`
```bash
cp .env.example .env
```
Edit `.env` and populate your credentials:
```ini
API_ID=12345678
API_HASH=abcdef0123456789abcdef0123456789
GEMINI_API_KEY=your_gemini_api_key_here
ASSISTANT_NAME=Capri,capri,کاپری
OWNER_NAME=YourName
```

### 3. Authenticate Telegram Session
```bash
python login.py
```
Enter your phone number and verification code to create `session.session`.

### 4. Run Capri
```bash
python bot.py
```

---

## 8. Step 4: Testing Key Commands & Features (v2.7.0)

Open Telegram and test Capri in **Saved Messages** or any chat:

### 1. 🤖 Model Switching & Catalog Navigation (v2.7.0)
- `کاپری مدلها` / `/models` *(Opens interactive Telegram inline pagination menu to browse 253 AI models)*
- `کاپری برو رو مرکوری` *(Switches to Inception Labs Mercury 3 fast diffusion agent)*
- `k1` or `کاپری مدل k1` *(Instantly switches to flagship model from XKIRO)*
- `b1` or `کاپری مدل b1` *(Switches to MiniMax M3.1 Flash from B.AI)*
- `a1` or `کاپری مدل a1` *(Switches to Gemini 2.5 Flash Lite from AnyAPI)*
- `o3` or `کاپری مدل o3` *(Switches to Nemotron 3.5 Lightning from OpenRouter)*
- `کاپری مدل فعلی چیه؟` *(Displays active model, service provider, and UID)*

### 2. 💬 Deep Reply Context & Smart Summarization (v2.7.0)
- **Summarize Replied Message:** Reply to any long message or article and say `کاپری خلاصه کن` *(Capri directly summarizes the original message text with author attribution)*
- **Reply to Media Links:** Reply to a message with a YouTube or Instagram link and say `کاپری خلاصه کن` or `کاپری دانلود کن` *(Seamlessly pulls the link from the replied message)*
- **Group Identity Separation:** In groups, Capri accurately differentiates between the current sender's Telegram ID/name and the replied message author's Telegram ID/name.
- **Honest Deleted Handling:** If you reply to a deleted message, Capri informs you that the message is inaccessible rather than hallucinating content.

### 3. 🎬 Anti-Visual-Hallucination Video Summaries (v2.7.0)
- `کاپری این ویدیو درباره چیه: [لینک یوتیوب]` *(Summarizes YouTube video content, chapters, and takeaways without downloading or fabricating visual descriptions)*
- `کاپری مشخصات این ویدیو چیه: [لینک یوتیوب]` *(Fetches video duration, channel author, and view counts without full summary)*
- `کاپری دانلود کن این ویدیو رو با کیفیت 720: [لینک یوتیوب]` *(Downloads and forwards original video file)*

### 4. 📁 Smart Saved Messages Organizer (Capri Vault)
- `کاپری مرتب کن سیو مسیج ۱۰ پیام` *(Provisions private Forum supergroup and classifies messages into 7 topics)*
- `کاپری ۵۰۰ پیام سیومسیج رو مرتب کن` *(Batch-sorts 500 messages with live progress and flood control)*
- `کاپری وضعیت صندوق` *(Displays current vault group status, total sorted count, and invite link)*

### 5. ⚡ Invisible Smart Reactions Assistant
- **On Channel Posts:** React with **❤️** or **👍** $\rightarrow$ Archives post directly into the appropriate topic in Capri Vault.
- **On Voice Notes:** React with **✍️** or **🎙️** $\rightarrow$ Transcribes audio with Whisper and sends analysis to Saved Messages.
- **Direct Roast:** React with **🤡** on any message from another user $\rightarrow$ Generates a witty roast reply directed at the sender.
- **Smart Reminders:** React with **👀** on any message $\rightarrow$ Schedules a 1-hour task reminder in Saved Messages.

### 6. 🎙️ Voice Synthesizer (48kHz Studio TTS)
- `کاپری صدا دلارا` *(Switches voice to warm female Dilara)*
- `کاپری صدا فرید` *(Switches voice to professional male Farid)*
- `کاپری صدا جمینای` *(Switches voice to Google Gemini TTS)*
- `کاپری چه صدایی` *(Shows active TTS engine and speaker)*

### 7. 🔕 Smart DND, Sleep Mode & Reminders
- `کاپری تا ساعت ۲ خوابم` / `تا ساعت ۱۴ سر کلاسم` *(Activates DND with empathetic auto-replies in DMs and group mentions)*
- `کاپری بیدار شدم` / `کاپری آزاد شدم` *(Deactivates DND and returns to normal operation with activity report)*
- `کاپری ساعت ۱۰ یادم بنداز جزوه رو بفرستم` *(Schedules a timed reminder in Saved Messages)*

---

## 9. Step 5: Production 24/7 Daemon Execution

To keep Capri running 24/7 on a remote server or desktop:

### Option A: Using `systemd` (Linux Server / VPS)
Create a service file:
```bash
sudo nano /etc/systemd/system/capri.service
```

Paste the following template (adjust paths and user):
```ini
[Unit]
Description=Capri Telegram AI Userbot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/capri-telegram-ai
ExecStart=/home/ubuntu/capri-telegram-ai/venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable capri
sudo systemctl start capri
sudo systemctl status capri
```

### Option B: Using `tmux` or `screen` (Quick Linux Solution)
```bash
tmux new -s capri
source venv/bin/activate
python bot.py
# Press Ctrl+B then D to detach
```

### Option C: Running as a Windows Background Task
In PowerShell:
```powershell
Start-Process -NoNewWindow -FilePath ".\venv\Scripts\python.exe" -ArgumentList "bot.py"
```

---

## 10. Troubleshooting & FAQ

### Q1: `telethon.errors.rpcerrorlist.FloodWaitError`
- **Cause:** Telegram rate-limited your account because of rapid calls.
- **Solution:** Capri has an automatic `flood_sleep_threshold=120` setting. It will gracefully pause and resume. Avoid spamming groups with hundreds of automated requests in short periods.

### Q2: Voice messages fail or don't play as native voice bubbles
- **Cause:** `ffmpeg` is missing or not located in system `PATH`.
- **Solution:** Install FFmpeg and verify with `ffmpeg -version`. If installed in a custom directory, set `FFMPEG_PATH=C:\path\to\ffmpeg.exe` in your `.env`.

### Q3: Why did saying "باید خلاصه کنی" switch the model in older versions?
- **Resolved in v2.7.0:** Earlier versions used substring matching on "بای" (which matched inside Persian words like "باید"). In v2.7.0, discrete Unicode word-boundary matching and explicit `model_intent` requirements ensure natural words never trigger accidental model switching.

### Q4: Connection timeouts or SOCKS proxy errors
- **Cause:** Telegram is filtered in your region and proxy details are not set.
- **Solution:** Verify your VPN / proxy client is running and set `PROXY_TYPE=socks5`, `PROXY_HOST=127.0.0.1`, and `PROXY_PORT=10808` in `.env`.

### Q5: Is running a userbot safe?
- **Guidelines:** Capri is designed with comprehensive safety gates (deny-by-default for strangers, taint quarantine against prompt injection, destructive action confirmations, and isolated memory namespaces). Always respect Telegram's Terms of Service and do not use userbots for unsolicited broadcasting or spam.
