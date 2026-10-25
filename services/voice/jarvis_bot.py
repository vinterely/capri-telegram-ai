import asyncio
import logging
import os
import re
from typing import Optional, Tuple

from telethon import types

log = logging.getLogger("jarvis_bot")

JARVIS_BOT = "jarvis_roobot"

VOICES = {
    "1": {"id": 1, "name": "باران", "gender": "زنانه", "desc": "لطیف، دلنشین و زنده (پیش‌فرض)"},
    "2": {"id": 2, "name": "سارا", "gender": "زنانه", "desc": "بسیار گرم، آرام و صمیمی"},
    "3": {"id": 3, "name": "آرش", "gender": "مردانه", "desc": "عمیق، متین و فصیح"},
    "4": {"id": 4, "name": "کیوان", "gender": "مردانه", "desc": "صمیمی، گفتاری و دلنشین"},
    "5": {"id": 5, "name": "بهرام", "gender": "مردانه", "desc": "پرانرژی، حماسی و رسا"},
    "6": {"id": 6, "name": "نگین", "gender": "زنانه", "desc": "محکم، رسا و شفاف"},
    "7": {"id": 7, "name": "امید", "gender": "مردانه", "desc": "جوان، سرزنده و پرنشاط"},
}

TONES = {
    "1": {"id": 1, "name": "طبیعی", "desc": "استاندارد، متعادل و زنده (پیش‌فرض)"},
    "2": {"id": 2, "name": "صمیمی", "desc": "گرم، دوستانه و خودمانی"},
    "3": {"id": 3, "name": "رسمی", "desc": "باوقار، جدی، فصیح و خبری"},
    "4": {"id": 4, "name": "باانرژی", "desc": "شاداب، پرانرژی و هیجان‌انگیز"},
    "5": {"id": 5, "name": "آرام", "desc": "لطیف، ملایم، آرام‌بخش و قصه‌گو"},
    "6": {"id": 6, "name": "حماسی", "desc": "باصلابت، پرقدرت و دراماتیک"},
}


def parse_voice_and_tone(text: str) -> Tuple[Optional[dict], Optional[dict]]:
    """استخراج گوینده و لحن از متن دستوری کاربر (مانند 'سارا 6' یا 'باران حماسی')."""
    t = text.lower().strip()
    t = re.sub(r"^(?:کاپری|capri)\s*", "", t)
    t = re.sub(r"^(?:تنظیم|صدای|ویس|صدا)?\s*(?:ربات|جارویس)?\s*", "", t).strip()

    found_voice = None
    found_tone = None

    tokens = t.split()

    # ۱. جستجوی اسامی خاص گویندگان
    for vid, vinfo in VOICES.items():
        if vinfo["name"] in t:
            found_voice = vinfo
            break

    # ۲. جستجوی اسامی خاص لحن‌ها
    for tid, tinfo in TONES.items():
        if tinfo["name"] in t:
            found_tone = tinfo
            break

    # ۳. بررسی شناسه‌های عددی (مثلاً 'سارا 6' یا '2 6')
    for tok in tokens:
        if tok.isdigit():
            val = tok
            if not found_voice and val in VOICES:
                found_voice = VOICES[val]
            elif not found_tone and val in TONES:
                found_tone = TONES[val]

    return found_voice, found_tone


async def configure_jarvis(client, voice_info: Optional[dict] = None, tone_info: Optional[dict] = None) -> Tuple[bool, str]:
    """ارسال تنظیمات گوینده و لحن به ربات تلگرام @jarvis_roobot و ذخیره در تنظیمات."""
    from core import settings

    bot_username = JARVIS_BOT
    try:
        bot = await client.get_entity(bot_username)
    except Exception as e:
        log.warning("Could not resolve @%s: %s", bot_username, e)
        bot = bot_username

    v_id = voice_info["id"] if voice_info else int(settings.get_jarvis_voice() or 1)
    t_id = tone_info["id"] if tone_info else int(settings.get_jarvis_tone() or 1)

    # ارسال دستور انتخاب صدا به ربات در تلگرام
    if voice_info:
        try:
            await client.send_message(bot, f"/voice{v_id}")
            await asyncio.sleep(0.5)
        except Exception as e:
            log.warning("Failed to send /voice to @%s: %s", bot_username, e)

    # ارسال دستور انتخاب لحن به ربات در تلگرام
    if tone_info:
        try:
            await client.send_message(bot, f"/tone{t_id}")
            await asyncio.sleep(0.5)
        except Exception as e:
            log.warning("Failed to send /tone to @%s: %s", bot_username, e)

    settings.set_tts_engine("jarvis")
    if voice_info:
        settings.set_jarvis_voice(str(v_id))
    if tone_info:
        settings.set_jarvis_tone(str(t_id))

    cur_v = VOICES.get(str(v_id), VOICES["1"])
    cur_t = TONES.get(str(t_id), TONES["1"])

    msg = (
        f"✅ **تنظیمات موتور صوتی ربات تلگرام (@{bot_username}) اعمال شد:**\n\n"
        f"👤 **گوینده:** {cur_v['name']} ({cur_v['gender']}) — `/voice{v_id}`\n"
        f"🎭 **لحن خوانش:** {cur_t['name']} ({cur_t['desc']}) — `/tone{t_id}`\n"
        f"⚙️ **موتور فعال صوتی:** ربات تلگرام (Jarvoice)\n\n"
        f"💡 از این پس تمامی ویس‌ها با این مشخصات مستقیماً از طریق @{bot_username} تولید و به صورت ریپلای ارسال خواهند شد."
    )
    return True, msg


async def speak_jarvis(client, text: str, out_path: str) -> bool:
    """ارسال متن به ربات @jarvis_roobot و دریافت و ذخیره فایل صوتی در out_path."""
    if not client or not text:
        return False

    bot_username = JARVIS_BOT
    try:
        bot = await client.get_entity(bot_username)
    except Exception as e:
        log.warning("Cannot resolve bot @%s: %s", bot_username, e)
        return False

    try:
        sent = await client.send_message(bot, text)
        base_id = sent.id
    except Exception as e:
        log.warning("Failed to send text to @%s: %s", bot_username, e)
        return False

    # حلقه بررسی پاسخ ربات (حداکثر ۲۵ گام ~ ۳۵ ثانیه)
    for _ in range(25):
        await asyncio.sleep(1.5)
        try:
            msgs = await client.get_messages(bot, limit=5)
        except Exception as e:
            log.debug("Error fetching messages from @%s: %s", bot_username, e)
            continue

        for m in msgs:
            if m.out or m.id <= base_id:
                continue

            # بررسی اینکه آیا پیام دارای فایل صوتی، ویس یا مدیا است
            has_audio = bool(
                m.voice or m.audio or (m.media and isinstance(m.media, types.MessageMediaDocument))
            )
            if has_audio:
                try:
                    if os.path.exists(out_path):
                        try:
                            os.remove(out_path)
                        except Exception:
                            pass
                    dl = await client.download_media(m.media, file=out_path)
                    from services.voice import voice
                    if dl and voice.is_valid_audio(out_path):
                        log.info("Audio received from @%s and validated (%d bytes)", bot_username, os.path.getsize(out_path))
                        return True
                    else:
                        bad_sz = os.path.getsize(out_path) if os.path.exists(out_path) else 0
                        log.warning("Audio from @%s was empty or corrupted (%d bytes). Falling back.", bot_username, bad_sz)
                        if os.path.exists(out_path):
                            try:
                                os.remove(out_path)
                            except Exception:
                                pass
                        return False
                except Exception as dl_err:
                    log.error("Failed to download audio from @%s: %s", bot_username, dl_err)
                    return False

            # اگر ربات به جای ویس، پیام متنی (مانند اعلام خطا یا سهمیه) فرستاده باشد
            if m.message and len(m.message.strip()) > 0:
                log.warning("Bot @%s replied with text instead of audio: '%s'. Falling back.", bot_username, m.message[:100])
                return False

    log.warning("Timed out waiting for voice response from @%s", bot_username)
    return False
