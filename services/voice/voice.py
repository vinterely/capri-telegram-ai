import asyncio
import logging
import os
import re
import time

import httpx

from core import config

log = logging.getLogger("voice")

GROQ_STT_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
TTS_VOICE = os.getenv("TTS_VOICE", "fa-IR-FaridNeural").strip()

_MIME = {
    ".ogg": "audio/ogg", ".opus": "audio/ogg", ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4", ".mp4": "audio/mp4", ".wav": "audio/wav",
    ".flac": "audio/flac", ".webm": "audio/webm", ".oga": "audio/ogg",
}


def _ensure_proxy_env():
    """edge-tts (aiohttp) فقط پروکسی HTTP رو می‌فهمه؛ پورت مختلط v2rayN قبول می‌کنه."""
    if not config.PROXY_HOST or not config.PROXY_PORT:
        return
    creds = f"{config.PROXY_USER}:{config.PROXY_PASS}@" if config.PROXY_USER else ""
    url = f"http://{creds}{config.PROXY_HOST}:{config.PROXY_PORT}"
    if not os.environ.get("HTTPS_PROXY"):
        os.environ["HTTPS_PROXY"] = url
    if not os.environ.get("HTTP_PROXY"):
        os.environ["HTTP_PROXY"] = url


_ensure_proxy_env()


def transcribe(path: str) -> str:
    """ویس → متن با Groq Whisper. خالی یعنی خطا."""
    if not config.GROQ_API_KEY:
        return ""
    try:
        ext = os.path.splitext(path)[1].lower()
        mime = _MIME.get(ext, "audio/ogg")
        with open(path, "rb") as f:
            files = {"file": (os.path.basename(path), f, mime)}
            data = {"model": "whisper-large-v3-turbo"}
            headers = {"Authorization": f"Bearer {config.GROQ_API_KEY}"}
            with httpx.Client(proxy=config.get_http_proxy_url(), timeout=120) as c:
                r = c.post(GROQ_STT_URL, files=files, data=data, headers=headers)
        if r.status_code != 200:
            return ""
        return (r.json().get("text") or "").strip()
    except Exception:
        return ""


def prepare_for_tts(text: str) -> str:
    """آماده‌سازی متن برای خوانش طبیعی، بااحساس و خوش‌ریتم در موتور صوتی."""
    if not text:
        return ""
    # حذف علائم مارک‌داون
    s = re.sub(r"[*_#`~>|]", " ", text)
    # استخراج عنوان لینک‌ها [متن](آدرس) -> متن
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)
    # حذف اموجی‌ها و کاراکترهای تصویری جهت جلوگیری از گیج شدن موتور صوتی
    s = re.sub(r"[\U00010000-\U0010ffff]", "", s)
    # استانداردسازی علائم نگارشی فارسی
    s = s.replace(",", "،").replace("?", "؟")
    # تنظیم فاصله بعد از علائم نگارشی
    s = re.sub(r"\s*([،؛!?.])\s*", r"\1 ", s)
    s = re.sub(r"\s+", " ", s).strip()
    if s and s[-1] not in (".", "!", "؟", "…"):
        s += "."
    return s


GEMINI_VOICES = {
    "Puck": {"fa": "پاک (Puck)", "desc": "پرانرژی، پویا و صمیمی", "type": "جوان"},
    "Charon": {"fa": "شارون (Charon)", "desc": "بم، عمیق، رسمی و جدی", "type": "مردانه/بم"},
    "Kore": {"fa": "کوره (Kore)", "desc": "آرامش‌بخش، گرم و باوقار", "type": "زنانه/گرم"},
    "Fenrir": {"fa": "فنریر (Fenrir)", "desc": "رسا، باصلابت و قدرتمند", "type": "مردانه/حماسی"},
    "Aoede": {"fa": "آئوده (Aoede)", "desc": "ملایم، لطیف و متفکر", "type": "زنانه/آرام"},
}

# اولویت مدل‌های رسمی صوتی جمینای با پشتیبانی از خروجی صوت (AUDIO)
GEMINI_TTS_MODELS = [
    os.getenv("GEMINI_TTS_MODEL", "").strip() or "gemini-3.8-flash-tts",
    "gemini-3.8-flash-lite-tts",
    "gemini-2.5-flash-preview-tts",
]
GEMINI_TTS_MODELS = [m for m in dict.fromkeys(GEMINI_TTS_MODELS) if m]

# ردگیری کول‌داون کلیدها و مدل‌ها در صورت محدودیت سهمیه (429 RESOURCE_EXHAUSTED)
_tts_cooldowns: dict[tuple[str, str], float] = {}


def _is_on_cooldown(key: str, model: str) -> bool:
    expire_at = _tts_cooldowns.get((key, model), 0)
    return time.time() < expire_at


def _set_cooldown(key: str, model: str, duration_sec: float = 3600):
    _tts_cooldowns[(key, model)] = time.time() + duration_sec


def _parse_retry_delay(err_msg: str, default: float = 3600) -> float:
    match = re.search(r"retryDelay['\":\s]+(\d+(?:\.\d+)?)s?", str(err_msg))
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            pass
    return default


DIACRITICS = set("\u064B\u064C\u064D\u064E\u064F\u0650\u0651\u0652\u0670")


def has_sufficient_diacritics(text: str) -> bool:
    """بررسی اینکه آیا متن در حال حاضر دارای حرکات اعرابی کافی است یا خیر."""
    if not text:
        return False
    vowels = sum(1 for c in text if c in DIACRITICS)
    words = len(text.split())
    return vowels >= max(2, words // 3)


async def ensure_persian_vowels(text: str) -> str:
    """اعراب‌گذاری دقیق متن فارسی فقط برای خوانش در موتور صوتی (در صورت عدم وجود اعراب)."""
    if not text or has_sufficient_diacritics(text):
        return text

    def _vocalize() -> str:
        from ai_engine import ai
        for key in config.GEMINI_API_KEYS:
            try:
                client = ai._get_client(key)
                prompt = (
                    "متن فارسی محاوره‌ای زیر را فقط اعراب‌گذاری کامل کن (با حرکات فتحه َ، کسره ِ، ضمه ُ، تشدید ّ) "
                    "جهت خوانش دقیق در موتور صوتی. "
                    "فقط و فقط متن اعراب‌گذاری‌شده را بدون هیچ توضیح اضافه، مقدمه، موخره یا علامت دیگری بنویس:\n\n"
                    + text
                )
                mod = config.GEMINI_MODELS[0] if config.GEMINI_MODELS else "gemini-2.5-flash"
                resp = client.models.generate_content(model=mod, contents=prompt)
                res = (resp.text or "").strip()
                if res and has_sufficient_diacritics(res):
                    return res
            except Exception:
                continue
        return text

    try:
        # مهلت زمانی حداکثر ۳.۵ ثانیه برای پیشگیری از تاخیر در پاسخ
        vocalized = await asyncio.wait_for(asyncio.to_thread(_vocalize), timeout=3.5)
        return vocalized or text
    except Exception:
        return text


def _ffmpeg():
    env_path = os.getenv("FFMPEG_PATH", "").strip()
    if env_path and os.path.exists(env_path):
        return env_path
    import shutil
    candidates = [
        os.path.join("F:", os.sep, "MediaTools", "bin", "ffmpeg.exe"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    which_ff = shutil.which("ffmpeg")
    if which_ff:
        return which_ff
    return None


def is_valid_audio(path: str) -> bool:
    """بررسی قطعی سالم بودن، داشتن دیتای واقعی صوت و قابل‌پخش بودن فایل صوتی."""
    if not path or not os.path.exists(path):
        return False
    size = os.path.getsize(path)
    if size < 1000:  # فایل‌های زیر ۱ کیلوبایت معمولاً فقط هدر خالی یا خطای سرور هستند
        return False
    ff = _ffmpeg()
    if not ff:
        return size >= 1000
    try:
        import subprocess
        # اعتبارسنجی سریع سلامت استریم صوتی بدون خطای EOF
        res = subprocess.run(
            [ff, "-v", "error", "-i", path, "-f", "null", "-"],
            capture_output=True, timeout=8
        )
        return res.returncode == 0
    except Exception:
        return size >= 1000


async def speak_gemini(clean_text: str, out_path: str, voice_name: str = None) -> bool:
    """متن → فایل صوتی با Gemini TTS با استفاده از هر دو کلید جمینای، چرخش هوشمند مدل‌ها و فال‌بک خودکار."""
    from core import settings
    selected_voice = voice_name or settings.get_gemini_voice() or "Puck"
    if selected_voice not in GEMINI_VOICES:
        for k in GEMINI_VOICES:
            if k.lower() == selected_voice.lower():
                selected_voice = k
                break
        else:
            selected_voice = "Puck"

    def _gen() -> bytes:
        from ai_engine import ai
        from google.genai import types

        keys = config.GEMINI_API_KEYS
        if not keys:
            return b""

        for key_idx, key in enumerate(keys, 1):
            for model in GEMINI_TTS_MODELS:
                if _is_on_cooldown(key, model):
                    continue
                try:
                    client = ai._get_client(key)
                    cfg = types.GenerateContentConfig(
                        response_modalities=["AUDIO"],
                        speech_config=types.SpeechConfig(
                            voice_config=types.VoiceConfig(
                                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=selected_voice)
                            )
                        )
                    )
                    resp = client.models.generate_content(model=model, contents=clean_text, config=cfg)
                    for cand in resp.candidates or []:
                        for part in cand.content.parts or []:
                            data = getattr(part, "inline_data", None)
                            if data and data.data:
                                return bytes(data.data)
                except Exception as e:
                    err_str = str(e)
                    if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower():
                        delay = _parse_retry_delay(err_str, default=3600)
                        _set_cooldown(key, model, delay)
                        log.warning(
                            "Gemini TTS quota exceeded for key #%d on model '%s' (cooldown %.0fs). Trying next key/model...",
                            key_idx, model, delay
                        )
                    else:
                        log.debug("Gemini TTS key #%d model '%s' error: %s", key_idx, model, err_str[:120])
                    continue
        return b""

    try:
        audio = await asyncio.to_thread(_gen)
        if audio:
            with open(out_path, "wb") as f:
                f.write(audio)
            if is_valid_audio(out_path):
                return True
    except Exception as e:
        log.warning(f"Gemini TTS generation error ({e}), falling back to Edge-TTS...")

    # فال‌بک خودکار به Microsoft Edge-TTS در صورت محدودیت سهمیه (429) یا خطای شبکه
    log.info("Gemini TTS currently unavailable or in cooldown across keys/models. Falling back to Microsoft Edge-TTS...")
    try:
        import edge_tts
        edge_voice = settings.get_tts_voice() or "fa-IR-FaridNeural"
        c = edge_tts.Communicate(clean_text, edge_voice, rate="+5%")
        await c.save(out_path)
        return is_valid_audio(out_path)
    except Exception as fb_err:
        log.error(f"Fallback Edge-TTS also failed: {fb_err}")
        return False


async def speak(text: str, out_path: str, voice: str = None, client = None) -> bool:
    """متن → فایل صوتی با موتور انتخابی (Jarvis Bot، Gemini TTS یا فال‌بک تضمینی به Edge-TTS)."""
    from core import settings
    engine = settings.get_tts_engine()

    # اعراب‌گذاری فقط برای Edge-TTS مفید است؛ گوینده‌های بومی فارسی (جمینای/جارویس) متن ساده را طبیعی‌تر می‌خوانند.
    if engine == "microsoft":
        text = await ensure_persian_vowels(text)
    clean_text = prepare_for_tts(text)
    if not clean_text:
        return False

    # ۱. اگر موتور فعال ربات تلگرام (@jarvis_roobot) باشد
    if engine == "jarvis" and client:
        try:
            from services.voice import jarvis_bot
            ok = await jarvis_bot.speak_jarvis(client, clean_text, out_path)
            if ok and is_valid_audio(out_path):
                return True
            log.warning("Jarvis bot voice generation failed or produced invalid audio. Falling back to Gemini TTS / Edge-TTS...")
        except Exception as e:
            log.warning("Jarvis bot voice exception (%s), falling back to Gemini...", e)

    # ۲. موتور Gemini TTS
    if engine in ("gemini", "jarvis"):
        ok = await speak_gemini(clean_text, out_path)
        if ok:
            return True

    # ۳. فال‌بک نهایی و تضمینی: Microsoft Edge-TTS
    selected_voice = voice or settings.get_tts_voice() or TTS_VOICE
    try:
        import edge_tts
        out_dir = os.path.dirname(os.path.abspath(out_path))
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        c = edge_tts.Communicate(clean_text, selected_voice, rate="+5%")
        await c.save(out_path)
        return is_valid_audio(out_path)
    except Exception as fb_err:
        log.error("Final Edge-TTS fallback failed: %s", fb_err)
        return False


def to_ogg(src: str, dst: str) -> bool:
    """mp3 → ogg/opus برای ویسنوت با کیفیت استودیویی 48kHz. False اگه ffmpeg نبود یا خطا داد."""
    ff = _ffmpeg()
    if not ff:
        return False
    try:
        import subprocess
        subprocess.run(
            [ff, "-y", "-i", src, "-c:a", "libopus", "-b:a", "64k", "-ar", "48000", "-ac", "1", dst],
            capture_output=True, timeout=90,
        )
        return os.path.exists(dst) and os.path.getsize(dst) > 0
    except Exception:
        return False
