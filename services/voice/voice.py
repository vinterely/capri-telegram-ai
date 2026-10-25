import asyncio
import os
import re

import httpx

from core import config

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


GEMINI_TTS_MODEL = "gemini-3.8-flash-tts"

GEMINI_VOICES = {
    "Puck": {"fa": "پاک (Puck)", "desc": "پرانرژی، پویا و صمیمی", "type": "جوان"},
    "Charon": {"fa": "شارون (Charon)", "desc": "بم، عمیق، رسمی و جدی", "type": "مردانه/بم"},
    "Kore": {"fa": "کوره (Kore)", "desc": "آرامش‌بخش، گرم و باوقار", "type": "زنانه/گرم"},
    "Fenrir": {"fa": "فنریر (Fenrir)", "desc": "رسا، باصلابت و قدرتمند", "type": "مردانه/حماسی"},
    "Aoede": {"fa": "آئوده (Aoede)", "desc": "ملایم، لطیف و متفکر", "type": "زنانه/آرام"},
}


async def speak_gemini(clean_text: str, out_path: str, voice_name: str = None) -> bool:
    """متن → فایل صوتی با Gemini TTS با امکان انتخاب گوینده از بین ۵ صدای رسمی جمینای."""
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
        client = ai._get_client()
        cfg = types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=selected_voice)
                )
            )
        )
        resp = client.models.generate_content(model=GEMINI_TTS_MODEL, contents=clean_text, config=cfg)
        for cand in resp.candidates or []:
            for part in cand.content.parts or []:
                data = getattr(part, "inline_data", None)
                if data and data.data:
                    return bytes(data.data)
        return b""

    try:
        audio = await asyncio.to_thread(_gen)
        if audio:
            with open(out_path, "wb") as f:
                f.write(audio)
            if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
                return True
    except Exception as e:
        logger.warning(f"Gemini TTS generation failed ({e}), falling back to Edge-TTS...")

    # فال‌بک خودکار به Microsoft Edge-TTS در صورت محدودیت سهمیه (429) یا خطای شبکه
    try:
        import edge_tts
        edge_voice = settings.get_tts_voice() or "fa-IR-FaridNeural"
        c = edge_tts.Communicate(clean_text, edge_voice, rate="+5%")
        await c.save(out_path)
        return os.path.exists(out_path) and os.path.getsize(out_path) > 0
    except Exception as fb_err:
        logger.error(f"Fallback Edge-TTS also failed: {fb_err}")
        return False


async def speak(text: str, out_path: str, voice: str = None) -> bool:
    """متن → فایل صوتی با موتور انتخابی (Microsoft Edge-TTS یا Gemini TTS)."""
    clean_text = prepare_for_tts(text)
    if not clean_text:
        return False

    from core import settings
    if settings.get_tts_engine() == "gemini":
        return await speak_gemini(clean_text, out_path)

    selected_voice = voice or settings.get_tts_voice() or TTS_VOICE
    try:
        import edge_tts
        c = edge_tts.Communicate(clean_text, selected_voice, rate="+5%")
        await c.save(out_path)
        return os.path.exists(out_path) and os.path.getsize(out_path) > 0
    except Exception:
        return False


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
