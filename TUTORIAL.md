# 📘 Capri AI Userbot [v1.5.0] - Comprehensive Setup Tutorial

Welcome to the definitive setup tutorial for **Capri**, an autonomous Telegram AI userbot powered by Telethon and multi-provider ReAct agent intelligence.

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
8. [Step 4: Testing Key Commands & Features (v1.5.0)](#8-step-4-testing-key-commands--features-v150)
9. [Step 5: Production 24/7 Daemon Execution](#9-step-5-production-247-daemon-execution)
10. [Troubleshooting & FAQ](#10-troubleshooting--faq)

---

## 1. Prerequisites

Before installing Capri, verify that your machine meets the following requirements:

- **Operating System:** Windows 10/11, Ubuntu 20.04+, Debian, macOS, or any Linux server.
- **Python:** Python **3.10**, **3.11**, or **3.12** ([Download Python](https://www.python.org/downloads/)).
  - *Note for Windows users:* Check the box **"Add python.exe to PATH"** during installation.
- **Git:** Installed on your system ([Download Git](https://git-scm.com/)).
- **FFmpeg (Crucial for Voice Notes):**
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

Capri supports multiple AI providers with automatic fallback and circuit-breaker resilience. You need **at least one** LLM provider (Google Gemini is free and recommended for start):

### 1. Google Gemini (Primary / Vision / Fallback) — **Recommended & Free**
- Go to [Google AI Studio](https://aistudio.google.com/apikey).
- Create a free project and generate your API key (`GEMINI_API_KEY`).

### 2. Inception Labs / Mercury 3 (Ultra-Fast ReAct Agent Engine) — **Recommended**
- Register at [Inception Labs](https://api.inceptionlabs.ai).
- Get your `INCEPTION_API_KEY` for instant Diffusion-LLM reasoning and function calling.

### 3. Groq (Ultra-Fast Inference & Whisper Audio Transcription) — **Recommended**
- Register at [Groq Console](https://console.groq.com/keys).
- Create your `GROQ_API_KEY` (used for `whisper-large-v3-turbo` voice-to-text and `qwen-3.8-27b`).

### 4. Hooshia (Native Persian & Regional LLM) — **Optional**
- Register at [Hooshia.com](https://hooshia.com).
- Obtain `HOOSHIA_API_KEY` for high-fidelity colloquial Persian comprehension without VPN.

### 5. Google Serper (Real-Time Web & YouTube Search) — **Recommended**
- Register at [Serper.dev](https://serper.dev).
- Get your free `SERPER_API_KEY` (provides 2,500 free Google searches for real-time web retrieval).

---

## 4. 🚀 Method 1: The One-Click Launcher (run.bat / run.sh)

Capri provides an updated interactive launcher that handles virtual environment creation, dependency installation, configuration checking, testing, and execution automatically.

### On Windows:
1. Clone the repository:
   ```bash
   git clone https://github.com/vinterely/capri-telegram-ai.git
   cd capri-telegram-ai
   ```
2. **Double-click on `run.bat`** (or execute `.\run.bat` in Command Prompt / PowerShell).
3. The interactive menu presents:
   - `[1] Start Capri Userbot (Normal Mode)`
   - `[2] Interactive Setup Wizard (start.py)`
   - `[3] Authenticate Telegram Session (login.py)`
   - `[4] Run Automated Test Suite (93 unit tests)`
   - `[5] Edit Environment Configuration (.env)`
4. Select `[1]` to start. If it's your first run, it will automatically guide you through `.env` setup and `login.py` authentication.

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

For a menu-driven terminal experience that works identically across Windows, macOS, and Linux:

```bash
python start.py
```

`start.py` is a self-contained CLI wizard built using only Python's standard library. It provides:
- **System Health Check:** Instantly scans for `.env`, `session.session`, `ffmpeg`, and virtual environment.
- **Interactive .env Configuration:** Prompts for your Telegram and Gemini keys step-by-step and writes `.env` automatically.
- **Telegram Authentication:** Launches `login.py` directly from the menu.
- **One-Key Bot Launch:** Starts Capri with graceful stop handling (`Ctrl+C`).
- **Test Suite Verification:** Runs the 93-test unit test suite with a single keypress.

---

## 6. 🐳 Method 3: Docker Deployment (Recommended for Servers/VPS)

For 24/7 server deployments without polluting your host environment:

1. Clone and enter the directory:
   ```bash
   git clone https://github.com/vinterely/capri-telegram-ai.git
   cd capri-telegram-ai
   ```

2. Perform the initial one-time interactive login to generate `session.session`:
   ```bash
   python3 -m venv venv && source venv/bin/activate
   pip install telethon python-dotenv
   python login.py
   ```

3. Configure your `.env` file from the template:
   ```bash
   cp .env.example .env
   nano .env
   ```

4. Launch Capri in background via Docker Compose:
   ```bash
   docker compose up -d --build
   ```

5. Monitor logs anytime:
   ```bash
   docker compose logs -f
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

## 8. Step 4: Testing Key Commands & Features (v1.5.0)

Open Telegram on your phone or desktop and test Capri in **Saved Messages** or any chat:

### 1. 📁 Smart Saved Messages Organizer (Capri Vault)
- `کاپری مرتب کن سیو مسیج ۱۰ پیام` *(Provisions private Forum supergroup and classifies last 10 messages into 8 topics)*
- `کاپری ۵۰۰ پیام سیومسیج رو مرتب کن` *(Batch-sorts 500 messages with live progress bar and flood control)*
- `کاپری وضعیت صندوق` *(Displays current vault group status, total sorted count, and invite link)*
- `کاپری صندوق پاکسازی کن` *(Purges all content messages from vault and resets processing cache)*
- `کاپری 50 پیام اخیر صندوق پاکسازی کن` *(Deletes the last 50 content messages from vault supergroup)*
- `کاپری دوباره مرتب کن صندوقو` *(Re-evaluates and re-sorts Saved Messages ignoring previous cache)*
- `کاپری ۱۰۰ پیام اخیر اینجا رو مرتب کن` *(In Saved Messages chat: spatial grounding detects "here" as Saved Messages)*

### 2. ⚡ Invisible Smart Reactions Assistant
- **On Channel Posts:** React with **❤️** or **👍** on any post $\rightarrow$ Capri analyzes topic and forwards to designated topic in Capri Vault + sends receipt to Saved Messages.
- **On Voice Notes:** React with **✍️**, **🎙️**, or **📝** on any voice message $\rightarrow$ Whisper transcribes audio + AI produces structured tone & intent analysis in Saved Messages.
- **In DMs & Groups:** React with **🕊️** or **🤖** on any message $\rightarrow$ AI analyzes topic and forwards to Capri Vault.
- **Direct Roast:** React with **🤡** on any message from another user $\rightarrow$ Capri generates a witty, sharp roast and replies directly to their message in the chat.
- **Smart Reminders:** React with **👀** or **👨‍💻** on any message $\rightarrow$ Schedules a 1-hour task reminder in DND with notification in Saved Messages.

### 3. 🔕 Smart DND, Sleep Mode & Reminders
- `کاپری تا ساعت ۲ خوابم` / `تا ساعت ۱۴ سر کلاسم` *(Activates DND with empathetic auto-replies in DMs and group mentions)*
- `کاپری بیدار شدم` / `کاپری آزاد شدم` *(Deactivates DND and returns to normal operation with activity report)*
- `کاپری ساعت ۱۰ یادم بنداز جزوه رو بفرستم` *(Schedules a timed reminder in Saved Messages)*
- `کاپری لیست یادآورها` / `کاپری پاک کردن یادآورها` *(View or clear scheduled reminders)*

### 4. 🎓 Study Partner & Code Review
- Send a document (PDF, Word, PPTX) + `کاپری این فایل رو بررسی کن` *(Generates 4-part exam roadmap & predictions)*
- Send a source code file + `کاپری این کد رو بررسی کن` *(Full code review: architecture, security risks, optimization)*

### 5. 🎭 Digital Twin (Ghost Mode)
- `کاپری مثل من شو` *(Learns your writing style from unedited messages and answers whitelisted DMs as you)*
- `کاپری برگرد به حالت عادی` *(Deactivates Ghost Mode)*

### 6. 🧠 Relationship & Chat Analytics
- `کاپری تحلیل کن این چت` *(6-dimensional behavioral audit of up to 500 unedited chat messages with health score)*

### 7. 🎙️ Voice Synthesizer (48kHz Studio TTS)
- `کاپری صدا دلارا` *(Switches voice to warm female Dilara)*
- `کاپری صدا فرید` *(Switches voice to professional male Farid)*
- `کاپری صدا جمینای` *(Switches voice to Google Gemini TTS)*
- `کاپری چه صدایی` *(Shows active TTS engine and voice)*

### 8. 🎵 Direct Music Search & Deezer Pilot
- `کاپری آهنگ [نام آهنگ یا خواننده] بفرست` *(Queries Deezer Music Bot, clicks matching option, re-uploads cleanly)*

### 9. 🌐 Multi-Lingual Deep Research (gsearch)
- `کاپری مقایسه عملکرد Go و Rust در وب‌سرورها چیه` *(Simultaneous search across English, Chinese NGA forums, and Persian)*

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

### Q3: `ValueError: Your API ID or Hash cannot be empty or None`
- **Cause:** You ran `bot.py` before filling in your `.env` file.
- **Solution:** Verify that `.env` is present in the project root and `API_ID` / `API_HASH` are set.

### Q4: Connection timeouts or SOCKS proxy errors
- **Cause:** Telegram is filtered in your region and proxy details are not set.
- **Solution:** Verify your VPN / V2Ray is running and set `PROXY_TYPE=socks5`, `PROXY_HOST=127.0.0.1`, and `PROXY_PORT=10808` in `.env`.

### Q5: Is running a userbot safe?
- **Guidelines:** Capri is designed with safety gates (deny-by-default for strangers, taint quarantine against prompt injection, destructive action confirmations). Always respect Telegram's Terms of Service and do not use userbots for unsolicited broadcasting or spam.

---

🎉 **Congratulations!** Your Capri Telegram AI Userbot is now up, verified, and running smoothly.
