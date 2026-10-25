import asyncio
import sys

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

from core import config

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

client = TelegramClient(config.SESSION_FILE, config.API_ID, config.API_HASH, proxy=config.get_proxy())


async def main():
    await client.connect()

    if await client.is_user_authorized():
        me = await client.get_me()
        print("ALREADY_LOGGED_IN", me.first_name or "", me.username or "")
        await client.disconnect()
        return

    args = sys.argv[1:]
    if not args:
        print("USAGE: login.py <phone>            -> send code")
        print("       login.py <phone> <code> <hash> [password]  -> finish login")
        await client.disconnect()
        return

    phone = args[0]

    if len(args) == 1:
        sent = await client.send_code_request(phone)
        print("CODE_SENT", sent.phone_code_hash)
    else:
        code = args[1]
        phone_code_hash = args[2]
        try:
            await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
        except SessionPasswordNeededError:
            if len(args) > 3:
                await client.sign_in(password=args[3])
            else:
                print("NEED_PASSWORD")
                await client.disconnect()
                return
        me = await client.get_me()
        print("LOGGED_IN", me.first_name or "", me.username or "")

    await client.disconnect()


asyncio.run(main())
