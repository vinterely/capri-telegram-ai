# -*- coding: utf-8 -*-
"""راه‌انداز یک‌جا و پیشرفتهٔ کاپری:
فیکس خودکار پروکسی (SOCKS5 روی 127.0.0.1:10808) + ورود تعاملی تلگرام + اجرای ربات."""

import asyncio
import os
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(BASE_DIR, ".env")
ENV_EXAMPLE = os.path.join(BASE_DIR, ".env.example")

PROXY_HOST = "127.0.0.1"
PROXY_PORT = "10808"


def ensure_proxy_env() -> None:
    """مطمئن می‌شود پروکسی در .env فعال و روی 127.0.0.1:10808 است (بقیهٔ خطوط دست نمی‌خورد)."""
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, encoding="utf-8") as f:
            lines = f.read().splitlines()
    elif os.path.exists(ENV_EXAMPLE):
        with open(ENV_EXAMPLE, encoding="utf-8") as f:
            lines = f.read().splitlines()
    else:
        lines = []

    out = []
    have_type = have_host = have_port = False
    for line in lines:
        if "=" not in line:
            out.append(line)
            continue
        key = line.split("=", 1)[0].strip().lstrip("#").strip().upper()
        if key == "PROXY_TYPE":
            out.append("PROXY_TYPE=socks5")
            have_type = True
        elif key == "PROXY_HOST":
            out.append(f"PROXY_HOST={PROXY_HOST}")
            have_host = True
        elif key == "PROXY_PORT":
            out.append(f"PROXY_PORT={PROXY_PORT}")
            have_port = True
        else:
            out.append(line)

    if not have_type:
        out.append("PROXY_TYPE=socks5")
    if not have_host:
        out.append(f"PROXY_HOST={PROXY_HOST}")
    if not have_port:
        out.append(f"PROXY_PORT={PROXY_PORT}")

    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(out).rstrip("\n") + "\n")
    print(f"[OK] پروکسی روی SOCKS5 {PROXY_HOST}:{PROXY_PORT} تنظیم شد.")


def get_python_exe() -> str:
    win_venv = os.path.join(BASE_DIR, "venv", "Scripts", "python.exe")
    if os.path.exists(win_venv):
        return win_venv
    posix_venv = os.path.join(BASE_DIR, "venv", "bin", "python")
    if os.path.exists(posix_venv):
        return posix_venv
    return sys.executable


def login_interactive() -> bool:
    from core import config
    from telethon import TelegramClient
    from telethon.errors import SessionPasswordNeededError

    if not config.API_ID or config.API_ID == 123456:
        print("[!] API_ID در .env تنظیم نشده. از https://my.telegram.org بگیر و در .env بگذار.")
        return False
    if not config.API_HASH or config.API_HASH.startswith("00000000"):
        print("[!] API_HASH در .env تنظیم نشده. از https://my.telegram.org بگیر و در .env بگذار.")
        return False

    async def run() -> bool:
        client = TelegramClient(
            config.SESSION_FILE, config.API_ID, config.API_HASH, proxy=config.get_proxy()
        )
        print("[*] در حال اتصال به تلگرام از طریق پروکسی...")
        try:
            await client.connect()
        except Exception as e:
            print(f"[X] اتصال ناموفق: {e}")
            print(f"[*] یعنی پروکسی کار نمی‌کند. مطمئن شو v2rayN وصل است و پورت SOCKS5 آن {PROXY_PORT} است.")
            return False

        if await client.is_user_authorized():
            me = await client.get_me()
            print(f"[OK] قبلاً وارد شده‌ای: {me.first_name or ''} (@{me.username or ''})")
            await client.disconnect()
            return True

        phone = input("شماره تلفن با کد کشور (مثلاً +989123456789): ").strip()
        try:
            sent = await client.send_code_request(phone)
        except Exception as e:
            print(f"[X] ارسال کد ناموفق: {e}")
            await client.disconnect()
            return False

        code = input("کدی که تلگرام برایت فرستاد: ").strip()
        try:
            await client.sign_in(phone, code, phone_code_hash=sent.phone_code_hash)
        except SessionPasswordNeededError:
            password = input("رمز دومرحله‌ای (2FA): ")
            await client.sign_in(password=password)

        me = await client.get_me()
        print(f"[OK] ورود موفق: {me.first_name or ''} (@{me.username or ''})")
        await client.disconnect()
        return True

    try:
        return asyncio.run(run())
    except Exception as e:
        print(f"[X] خطا: {e}")
        return False


def run_bot() -> None:
    print("[*] در حال اجرای ربات... (برای توقف Ctrl+C بزن)")
    subprocess.run([get_python_exe(), os.path.join(BASE_DIR, "bot.py")], cwd=BASE_DIR)


def main() -> None:
    print("=" * 62)
    print("  CAPRI QUICKSTART — فیکس پروکسی + ورود + اجرا")
    print("=" * 62)
    ensure_proxy_env()
    if not login_interactive():
        print("\n[!] ورود کامل نشد. اول v2rayN و .env را درست کن، بعد دوباره اجرا کن.")
        return
    run_bot()


if __name__ == "__main__":
    main()
