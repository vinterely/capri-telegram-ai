"""
🌟 Capri Userbot - Interactive Cross-Platform CLI Wizard & Launcher
Runs on Windows, macOS, and Linux using Python standard library.
"""
import os
import sys
import subprocess
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(BASE_DIR, ".env")
ENV_EXAMPLE = os.path.join(BASE_DIR, ".env.example")
SESSION_FILE = os.path.join(BASE_DIR, "session.session")


def get_python_exe() -> str:
    """Find the best Python executable, prioritizing the project's virtual environment."""
    # 1. Windows venv
    win_venv = os.path.join(BASE_DIR, "venv", "Scripts", "python.exe")
    if os.path.exists(win_venv):
        return win_venv
    # 2. Linux / macOS venv
    posix_venv = os.path.join(BASE_DIR, "venv", "bin", "python")
    if os.path.exists(posix_venv):
        return posix_venv
    # 3. Fallback to current interpreter
    return sys.executable


def ensure_dependencies() -> bool:
    """Ensure venv exists and required packages (telethon, etc.) are installed."""
    py_exe = get_python_exe()

    # Check if telethon can be imported cleanly
    res = subprocess.run([py_exe, "-c", "import telethon"], capture_output=True, cwd=BASE_DIR)
    if res.returncode == 0:
        return True

    print("\n📦 Required packages not found in active environment. Setting up...")

    # Create venv if not present
    if py_exe == sys.executable:
        venv_dir = os.path.join(BASE_DIR, "venv")
        if not os.path.exists(venv_dir):
            print("[*] Creating virtual environment (venv)...")
            subprocess.run([sys.executable, "-m", "venv", "venv"], cwd=BASE_DIR)
            py_exe = get_python_exe()

    req_file = os.path.join(BASE_DIR, "requirements.txt")
    if os.path.exists(req_file):
        print("[*] Installing requirements from requirements.txt...")
        subprocess.run([py_exe, "-m", "pip", "install", "--upgrade", "pip"], cwd=BASE_DIR)
        install_res = subprocess.run([py_exe, "-m", "pip", "install", "-r", "requirements.txt"], cwd=BASE_DIR)
        return install_res.returncode == 0
    return False


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def print_banner():
    print("""
======================================================================
  🌟 CAPRI TELEGRAM AI USERBOT [v2.0.0] - LAUNCHER & WIZARD
======================================================================
""")


def check_status():
    has_env = os.path.exists(ENV_FILE)
    has_session = os.path.exists(SESSION_FILE) or os.path.exists(os.path.join(BASE_DIR, "session"))
    has_ffmpeg = shutil.which("ffmpeg") is not None
    py_exe = get_python_exe()
    in_venv = py_exe != sys.executable or "venv" in py_exe.lower()

    print("📋 Current System Status:")
    print(f"  • Python Environment:               {'✅ venv (' + py_exe + ')' if in_venv else '⚠️ System Python'}")
    print(f"  • Environment Configuration (.env): {'✅ Ready' if has_env else '⚠️ Missing (.env)'}")
    print(f"  • Telegram Authentication:          {'✅ Authenticated' if has_session else '⚠️ Not logged in (session.session)'}")
    print(f"  • FFmpeg Audio Processor:           {'✅ Installed' if has_ffmpeg else '⚠️ Not found in PATH (Voice notes may fail)'}")
    print("----------------------------------------------------------------------")


def setup_env_wizard():
    print("\n🔑 --- .env Configuration Wizard ---")
    if not os.path.exists(ENV_EXAMPLE):
        print("❌ .env.example not found.")
        input("\nPress Enter to return...")
        return

    with open(ENV_EXAMPLE, "r", encoding="utf-8") as f:
        template = f.read()

    print("\nPlease enter your Telegram credentials (from https://my.telegram.org):")
    api_id = input("1. API_ID (numeric, e.g. 12345678): ").strip()
    api_hash = input("2. API_HASH (hexadecimal): ").strip()
    gemini_key = input("3. GEMINI_API_KEY (from https://aistudio.google.com/apikey): ").strip()
    assistant_name = input("4. Assistant Name [default: Capri,capri,کاپری]: ").strip() or "Capri,capri,کاپری"
    owner_name = input("5. Your Name/Username: ").strip() or "Owner"

    proxy_choice = input("6. Do you need a proxy? (y/n) [default: n]: ").strip().lower()
    proxy_host = ""
    proxy_port = ""
    if proxy_choice == "y":
        proxy_host = input("   Proxy Host [default: 127.0.0.1]: ").strip() or "127.0.0.1"
        proxy_port = input("   Proxy Port (SOCKS5) [default: 10808]: ").strip() or "10808"

    # Replace values
    if api_id:
        template = template.replace("API_ID=1234567", f"API_ID={api_id}")
    if api_hash:
        template = template.replace("API_HASH=your_api_hash_here", f"API_HASH={api_hash}")
    if gemini_key:
        template = template.replace("GEMINI_API_KEY=your_gemini_api_key_here", f"GEMINI_API_KEY={gemini_key}")
    if assistant_name:
        template = template.replace("ASSISTANT_NAME=Capri,capri,کاپری", f"ASSISTANT_NAME={assistant_name}")
    if owner_name:
        template = template.replace("OWNER_NAME=YourName", f"OWNER_NAME={owner_name}")
    if proxy_host and proxy_port:
        template = template.replace("# PROXY_TYPE=socks5", "PROXY_TYPE=socks5")
        template = template.replace("# PROXY_HOST=127.0.0.1", f"PROXY_HOST={proxy_host}")
        template = template.replace("# PROXY_PORT=10808", f"PROXY_PORT={proxy_port}")

    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.write(template)

    print("\n✅ .env file configured and saved successfully!")
    input("Press Enter to return to main menu...")


def run_login():
    print("\n📱 --- Telegram Authentication ---")
    login_script = os.path.join(BASE_DIR, "login.py")
    if not os.path.exists(login_script):
        print("❌ login.py not found.")
        input("\nPress Enter to return...")
        return
    py_exe = get_python_exe()
    ensure_dependencies()
    subprocess.run([py_exe, login_script], cwd=BASE_DIR)
    input("\nPress Enter to return to main menu...")


def bot_running() -> bool:
    """Check whether an instance of the bot is currently running via bot.lock."""
    lock_path = os.path.join(BASE_DIR, "bot.lock")
    if not os.path.exists(lock_path):
        return False
    try:
        with open(lock_path, "r", encoding="utf-8") as f:
            pid = int(f.read().strip() or "0")
    except Exception:
        return False
    if not pid:
        return False
    try:
        if os.name == "nt":
            res = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                capture_output=True, text=True, timeout=10,
            )
            return str(pid) in res.stdout
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def run_bot():
    print("\n🚀 Starting Capri Telegram AI Userbot...")
    py_exe = get_python_exe()
    bot_script = os.path.join(BASE_DIR, "bot.py")
    ensure_dependencies()

    if bot_running():
        print("\n⚠️ ربات از قبل در حال اجراست! نیازی به اجرای مجدد نیست.")
        print("   برای اجرای مجدد، اول ربات فعلی رو با Ctrl+C ببند و بعد دوباره گزینه ۱ رو بزن.")
        input("\nPress Enter to return to main menu...")
        return

    try:
        res = subprocess.run([py_exe, bot_script], cwd=BASE_DIR)
        if res.returncode != 0:
            print(f"\n❌ Bot stopped with exit code {res.returncode}.")
            print("💡 Tip: Check bot.log for detailed error logs.")
    except KeyboardInterrupt:
        print("\n\n🛑 Bot stopped by user.")
    input("\nPress Enter to return to main menu...")


def run_tests():
    print("\n🧪 Running Capri Unit Test Suite...")
    py_exe = get_python_exe()
    subprocess.run([py_exe, "-m", "unittest", "discover", "tests"], cwd=BASE_DIR)
    input("\nPress Enter to return to main menu...")


def main():
    while True:
        clear_screen()
        print_banner()
        check_status()
        print("""
Options:
  [1] 🚀 Start Capri Userbot
  [2] 🔑 Run .env Configuration Wizard
  [3] 📱 Authenticate Telegram Session (login.py)
  [4] 🧪 Run Test Suite (Verification)
  [5] 📝 Open .env in Editor
  [0] ❌ Exit
""")
        choice = input("Enter option [0-5]: ").strip()
        if choice == "1":
            if not os.path.exists(ENV_FILE):
                print("\n⚠️ Please configure .env first (Option 2).")
                input("Press Enter...")
                continue
            has_session = os.path.exists(SESSION_FILE) or os.path.exists(os.path.join(BASE_DIR, "session"))
            if not has_session:
                print("\n⚠️ Please authenticate your Telegram session first (Option 3).")
                input("Press Enter...")
                continue
            run_bot()
        elif choice == "2":
            setup_env_wizard()
        elif choice == "3":
            run_login()
        elif choice == "4":
            run_tests()
        elif choice == "5":
            if os.path.exists(ENV_FILE):
                if os.name == "nt":
                    os.system(f"notepad {ENV_FILE}")
                else:
                    os.system(f"nano {ENV_FILE}")
            else:
                print("\n⚠️ .env file does not exist yet. Please choose Option 2 first.")
                input("Press Enter...")
        elif choice == "0":
            print("\n👋 Goodbye!")
            break


if __name__ == "__main__":
    main()
