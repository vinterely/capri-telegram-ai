@echo off
title Capri Telegram AI Userbot v2.2.0

REM Change to directory of this script
cd /d "%~dp0"

:CHECK_PYTHON
where python >nul 2>nul
if %ERRORLEVEL% equ 0 goto CHECK_VENV
where py >nul 2>nul
if %ERRORLEVEL% equ 0 goto CHECK_VENV

echo ==============================================================================
echo [ERROR] Python is not installed or not found in system PATH!
echo Please install Python 3.10, 3.11, or 3.12 from:
echo https://www.python.org/downloads/
echo Make sure to check "Add python.exe to PATH" during installation.
echo ==============================================================================
echo.
pause
exit /b 1

:CHECK_VENV
if exist "venv\Scripts\python.exe" goto CHECK_DEPS
echo [*] Creating virtual environment [venv]...
python -m venv venv 2>nul || py -3 -m venv venv
if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Failed to create virtual environment!
    pause
    exit /b 1
)
echo [OK] Virtual environment created successfully.

:CHECK_DEPS
if exist "venv\Lib\site-packages\telethon" goto MENU
echo [*] Installing required packages from requirements.txt...
echo [*] This happens only once on initial setup. Please wait...
.\venv\Scripts\python.exe -m pip install --upgrade pip --quiet
.\venv\Scripts\python.exe -m pip install -r requirements.txt --quiet
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to install dependencies!
    pause
    exit /b 1
)
echo [OK] Dependencies installed successfully.

:MENU
cls
echo ==============================================================================
echo             CAPRI TELEGRAM AI USERBOT [v2.2.0] - LAUNCHER
echo ==============================================================================
echo.
echo Available Options:
echo   [1] Start Capri Userbot (Normal Mode)
echo   [2] Interactive Setup Wizard (start.py)
echo   [3] Authenticate Telegram Session (login.py)
echo   [4] Run Automated Test Suite (156 tests)
echo   [5] Edit Environment Configuration (.env)
echo   [0] Exit
echo.
set "CHOICE=1"
set /p CHOICE="Enter your choice [1-5, or 0 to exit] (Default: 1): "

if "%CHOICE%"=="0" goto EXIT
if "%CHOICE%"=="1" goto START_BOT
if "%CHOICE%"=="2" goto WIZARD
if "%CHOICE%"=="3" goto LOGIN
if "%CHOICE%"=="4" goto TESTS
if "%CHOICE%"=="5" goto EDIT_ENV

echo Invalid choice. Please try again.
ping 127.0.0.1 -n 2 >nul
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
echo Enter your phone number with country code (e.g. +989123456789).
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
echo [*] Running Capri Test Suite (156 tests)...
echo ==============================================================================
echo.
.\venv\Scripts\python.exe -m unittest discover -s tests
echo.
echo Press any key to return to menu...
pause >nul
goto MENU

:START_BOT
if exist ".env" goto CHECK_SESSION
echo.
echo [!] No .env file found. Creating from .env.example...
copy .env.example .env >nul
echo.
echo ==============================================================================
echo [ACTION REQUIRED] Please configure your Telegram API credentials!
echo Opening .env in Notepad...
echo Fill in your API_ID, API_HASH, and API keys.
echo Save the file (Ctrl+S), and close Notepad.
echo ==============================================================================
notepad .env
echo Once you have saved and closed Notepad, press any key to continue...
pause >nul

:CHECK_SESSION
if exist "session.session" goto RUN_BOT
if exist "session" goto RUN_BOT

echo.
echo ==============================================================================
echo [*] First-time authentication required.
echo Launching login.py...
echo Enter your phone number, verification code, and 2FA password if set.
echo ==============================================================================
echo.
.\venv\Scripts\python.exe login.py
if exist "session.session" goto RUN_BOT
if exist "session" goto RUN_BOT

echo.
echo [WARNING] Login did not generate a session file.
echo Please verify your credentials and try again.
pause
goto MENU

:RUN_BOT
cls
echo ==============================================================================
echo [*] Starting Capri Telegram AI Userbot [v2.2.0]...
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
echo [*] Goodbye!
ping 127.0.0.1 -n 2 >nul
exit /b 0
