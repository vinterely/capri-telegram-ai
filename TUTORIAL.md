# 📘 Capri AI Userbot [v3.1.0] - Comprehensive Setup Tutorial

Welcome to the definitive setup tutorial for **Capri (v3.1.0)**, an autonomous Telegram AI userbot powered by Telethon and multi-provider ReAct agent intelligence.

This tutorial guides you from a blank machine to a fully running, production-ready Capri userbot in under 5 minutes.

---

## 📑 Table of Contents
1. [Prerequisites](#1-prerequisites)
2. [Step 1: Obtain Telegram API Credentials](#2-step-1-obtain-telegram-api-credentials)
3. [Step 2: Obtain AI & Search API Keys](#3-step-2-obtain-ai--search-api-keys)
4. [🚀 Method 1: The One-Click Launcher (run.bat / run.sh)](#4--method-1-the-one-click-launcher-runbat--runsh)
5. [⚡ Method 2: All-in-One Quickstart (quickstart.py)](#5--method-2-all-in-one-quickstart-quickstartpy)
6. [🧙 Method 3: The Interactive Python Wizard (start.py)](#6--method-3-the-interactive-python-wizard-startpy)
7. [🐳 Method 4: Docker Deployment (Recommended for Servers/VPS)](#7--method-4-docker-deployment-recommended-for-serversvps)
8. [🛠️ Method 5: Manual Terminal Setup](#8-️-method-5-manual-terminal-setup)
9. [Step 4: Testing Key Commands & Features (v3.1.0)](#9-step-4-testing-key-commands--features-v310)
10. [Step 5: Production 24/7 Daemon Execution](#10-step-5-production-247-daemon-execution)
11. [Troubleshooting & FAQ](#11-troubleshooting--faq)

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

- **On Windows:** Double-click `run.bat` or run:
  ```cmd
  run.bat
  ```
- **On Linux / macOS:** Run:
  ```bash
  chmod +x run.sh
  ./run.sh
  ```

---

## 5. ⚡ Method 2: All-in-One Quickstart (quickstart.py)

If you are using a proxy client (such as v2rayN on port 10808) and want a single script to verify proxy settings, log in to Telegram interactively, and launch Capri:

```bash
python quickstart.py
```

---

## 6. 🧙 Method 3: The Interactive Python Wizard (start.py)

Run the built-in setup wizard:
```bash
python start.py
```
The wizard guides you through dependency validation, API key input, and initial login.

---

## 7. 🐳 Method 4: Docker Deployment (Recommended for Servers/VPS)

Capri includes production-ready `Dockerfile` and `docker-compose.yml` configurations:

```bash
# 1. Create .env with your credentials
cp .env.example .env

# 2. Build and start container in detached daemon mode
docker-compose up -d --build

# 3. View live runtime logs
docker-compose logs -f
```

---

## 8. 🛠️ Method 5: Manual Terminal Setup

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
TIMEZONE=Asia/Tehran
STICKER_PACK_SHORTNAME=Vinterely
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

## 9. Step 4: Testing Key Commands & Features (v3.1.0)

Open Telegram and test Capri in **Saved Messages**, in **Capri Home**, or in any chat:

### 1. 💡 Structured Ideation & Brainstorming (v3.1.0)
- `کاپری یه ایده بده برای ساخت یک محصول جدید` / `کاپری طوفان فکری کن روی [موضوع]`
- Capri runs a fast-path structured brainstorming workflow:
  - Validates core assumptions and target goals.
  - Proposes unconventional, creative out-of-the-box concepts.
  - Delivers low-friction quick wins and bold high-risk/high-reward paths.
  - Asks 1–2 sharpening questions to refine the project.

### 2. 🎀 Emotional Stickers from Vinterely Pack (v3.1.0)
- During conversations with high emotional resonance (jokes, celebration, empathy, surprise), Capri contextually responds with matching stickers from the `Vinterely` pack.
- Enforces an automatic 15-minute per-chat cooldown to ensure stickers remain delightful rather than spammy.
- The ReAct agent can also invoke the `send_sticker(emotion)` tool autonomously.

### 3. 🗓️ Synchronized Solar Hijri & Gregorian Date Awareness (v3.1.0)
- `امروز چه روزیه؟` / `تاریخ امروز چیه؟`
- Returns accurate, synchronized date context:
  - Solar Hijri (Jalali) date + Persian weekday.
  - Gregorian date (YYYY/MM/DD) and exact local time (`Asia/Tehran`).
  - Web searches for recent news, prices, and software releases automatically inject the current Gregorian year to eliminate stale results.

### 4. 🏠 Capri Home & Direct Management
- Capri automatically sets up a private forum supergroup titled **`🏠 Capri Home | مدیریت کاپری`** and groups it into a Telegram dialog folder named **`capri`**.
- Inside Capri Home, talk directly to Capri without trigger keywords.
- Inspect the dedicated topics:
  - `🗂 بکاپ`: Confirmed pre-deletion backups of deleted messages.
  - `📰 خلاصه کانال‌ها`: Periodic digests of monitored channels.

### 5. 🛑 True Operation Cancellation
- Send `کنسل`, `لغو کن`, `متوقفش کن`, or `بیخیال` during any long-running operation (search, download, multi-step ReAct).
- The active asynchronous task is cancelled immediately for that specific chat with zero side effects on concurrent tasks.

### 6. 🗑️ Message Cleaner with Verified Backup
- `کاپری ۱۰ پاک کن` / `کاپری ۵ پیام پاک کن`:
  - Scans recent outgoing messages from the owner in that chat.
  - Forwards content and metadata to the Home `🗂 بکاپ` topic.
  - Confirms backup success for each message before deleting.
  - Revokes only backed-up messages and returns an honest report.
- Operations exceeding 20 messages prompt for interactive confirmation.

### 7. 📰 Periodic Channel Summarizer
- `این کانال رو به خلاصه اضافه کن` / `به خلاصه اضافه کن @channel`: Adds a channel to the monitoring list.
- `کانال‌های خلاصه`: Lists all currently subscribed channels.
- `از خلاصه حذف کن @channel`: Removes a channel from monitoring.
- Capri polls posts every 30 minutes and sends clean, link-attributed summaries to Capri Home.

### 8. 🎧 Voice Mode — Hands-Free Voice Interaction
- `حالت ویس روشن`: Activates Voice Mode (persisted in `settings.json`).
- `حالت ویس خاموش`: Deactivates Voice Mode.
- When Voice Mode is on, any voice or video note sent by the owner is automatically transcribed via Whisper and replied to with voice notes without trigger words.

### 9. 🔕 Smart Absence, DND & Missed Inbox
- `من تا ساعت ۸ نیستم` / `تا ساعت ۱۴ سر جلسه‌ام`: Activates DND with intelligent absence tracking.
- Contextual away auto-replies are sent to private chats and mentions with a single-response-per-sender guard.
- Missed inquiries are recorded into a bounded inbox.
- Upon return, ask `چی شد وقتی نبودم` to receive a briefing of all missed messages.

### 10. 🤖 Model Switching & Catalog Navigation
- `کاپری مدلها` / `/models`: Opens interactive Telegram inline pagination menu to browse 253 AI models.
- `کاپری برو رو مرکوری`: Switches to Inception Labs Mercury 3 fast diffusion agent (`i1`).
- `k1`, `b1`, `a1`, `o1`: Switches instantly to specific provider models.
- `کاپری مدل فعلی چیه؟`: Displays active model and provider status.

---

## 10. Step 5: Production 24/7 Daemon Execution

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

## 11. Troubleshooting & FAQ

### Q1: `telethon.errors.rpcerrorlist.FloodWaitError`
- **Cause:** Telegram rate-limited your account because of rapid calls.
- **Solution:** Capri has an automatic `flood_sleep_threshold=120` setting. It will gracefully pause and resume.

### Q2: Voice messages fail or don't play as native voice bubbles
- **Cause:** `ffmpeg` is missing or not located in system `PATH`.
- **Solution:** Install FFmpeg and verify with `ffmpeg -version`. If installed in a custom directory, set `FFMPEG_PATH=C:\path\to\ffmpeg.exe` in your `.env`.

### Q3: SOCKS proxy errors or connection drops
- **Solution:** Verify your VPN / proxy client is running and ensure `PROXY_TYPE=socks5`, `PROXY_HOST=127.0.0.1`, and `PROXY_PORT=10808` are configured in `.env`.

### Q4: Are messages safely backed up before deletion?
- **Guarantee:** Capri's cleaner enforces an uncompromising safety rule: zero messages are deleted without confirmed pre-deletion forwarding to the Capri Home `🗂 بکاپ` topic. If forwarding fails for any reason, the original message remains intact.

### Q5: How do I change the default sticker pack?
- **Solution:** In `.env`, set `STICKER_PACK_SHORTNAME=YourPackName`. Capri will fetch the new pack and cache the emotion mappings upon the next startup.
