@echo off
chcp 65001 >nul
title Capri Telegram AI Userbot v1.5.0

:MENU
cls
echo ==============================================================================
echo           🌟 CAPRI TELEGRAM AI USERBOT [v1.5.0] - ONE-CLICK LAUNCHER
echo ==============================================================================
echo.

:: 1. Verify Python installation
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not found in system PATH!
    echo Please install Python 3.10, 3.11, or 3.12 from:
    echo https://www.python.org/downloads/
    echo (Make sure to check "Add python.exe to PATH" during installation)
    echo.
    pause
    exit /b 1
)

:: 2. Auto-provision Virtual Environment (venv)
if not exist "venv\Scripts\python.exe" (
    echo [*] Creating virtual environment (venv)...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment!
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created successfully.
)

:: 3. Auto-install Dependencies
if not exist "venv\Lib\site-packages\telethon" (
    echo [*] Installing required packages from requirements.txt...
    echo [*] This happens only once on initial setup. Please wait...
    .\venv\Scripts\python.exe -m pip install --upgrade pip --quiet
    .\venv\Scripts\python.exe -m pip install -r requirements.txt --quiet
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install dependencies!
        pause
        exit /b 1
    )
    echo [OK] Dependencies installed successfully.
)

echo Available Options:
echo   [1] 🚀 Start Capri Userbot (Normal Mode)
echo   [2] 🧙 Interactive Setup Wizard (start.py)
echo   [3] 📱 Authenticate Telegram Session (login.py)
echo   [4] 🧪 Run Automated Test Suite (93 unit tests)
echo   [5] 📝 Edit Environment Configuration (.env)
echo   [0] ❌ Exit
echo.
set /p CHOICE="Enter your choice [1-5, or 0 to exit] (Default: 1): "

if "%CHOICE%"=="" set CHOICE=1
if "%CHOICE%"=="0" goto EXIT
if "%CHOICE%"=="2" goto WIZARD
if "%CHOICE%"=="3" goto LOGIN
if "%CHOICE%"=="4" goto TESTS
if "%CHOICE%"=="5" goto EDIT_ENV
if "%CHOICE%"=="1" goto START_BOT

echo Invalid choice. Please try again.
timeout /t 2 >nul
goto MENU

:EDIT_ENV
if not exist ".env" (
    copy .env.example .env >nul
)
notepad .env
goto MENU

:WIZARD
cls
.\venv\Scripts\python.exe start.py
goto MENU

:LOGIN
cls
echo ==============================================================================
echo [*] Launching Telegram Authentication (login.py)...
echo Enter your phone number with country code (e.g., +989123456789).
echo ==============================================================================
echo.
.\venv\Scripts\python.exe login.py
echo.
echo Press any key to return to menu...
pause >nul
goto MENU

:TESTS
cls
echo ==============================================================================
echo [*] Running Capri Test Suite (test_logic.py)...
echo ==============================================================================
echo.
.\venv\Scripts\python.exe -m unittest discover tests
echo.
echo Press any key to return to menu...
pause >nul
goto MENU

:START_BOT
:: Verify .env existence
if not exist ".env" (
    echo.
    echo [!] No .env file found. Creating from .env.example...
    copy .env.example .env >nul
    echo.
    echo ==============================================================================
    echo [ACTION REQUIRED] Please configure your Telegram API credentials!
    echo Opening .env in Notepad...
    echo Fill in your API_ID, API_HASH, and GEMINI_API_KEY.
    echo Save the file (Ctrl+S), and close Notepad.
    echo ==============================================================================
    notepad .env
    echo Once you have saved and closed Notepad, press any key to continue...
    pause >nul
)

:: Verify Telegram session existence
if not exist "session.session" (
    if not exist "session" (
        echo.
        echo ==============================================================================
        echo [*] First-time authentication required.
        echo Launching login.py...
        echo Enter your phone number, verification code, and 2FA password (if set).
        echo ==============================================================================
        echo.
        .\venv\Scripts\python.exe login.py
        if not exist "session.session" (
            if not exist "session" (
                echo.
                echo [WARNING] Login did not generate a session file.
                echo Please verify your credentials and try again.
                pause
                goto MENU
            )
        )
        echo [OK] Telegram session authenticated successfully!
    )
)

cls
echo ==============================================================================
echo [*] Starting Capri Telegram AI Userbot [v1.5.0]...
echo [*] Press Ctrl+C at any time in this window to stop the bot.
echo ==============================================================================
echo.

.\venv\Scripts\python.exe bot.py

echo.
echo [*] Capri Userbot has stopped.
echo Press any key to return to menu...
pause >nul
goto MENU

:EXIT
echo.
echo 👋 Goodbye!
timeout /t 1 >nul
exit /b 0
