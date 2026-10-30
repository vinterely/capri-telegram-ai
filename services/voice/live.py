"""GEMINI Live voice conversation service."""
from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import time
from typing import Optional

from google import genai
from google.genai import types

from core import config
from services.voice import voice as voice_svc

log = logging.getLogger("live_voice")

IN_RATE = 16000
OUT_RATE = 24000
MAX_INPUT_SECONDS = 120
MAX_OUTPUT_BYTES = OUT_RATE * 2 * 60
TURN_TIMEOUT = 40.0
TOTAL_BUDGET = 80.0
SESSION_TTL = 30 * 60
MAX_HISTORY = 3
HISTORY_CHARS = 300

SYSTEM_PROMPT = (
    "تو «کاپری» هستی، دستیار شخصی و صمیمی مالک این حساب تلگرام. "
    "این یک مکالمه‌ی صوتی زنده است؛ همیشه فارسی روان، خودمانی و بسیار کوتاه صحبت کن "
    "(معمولاً یک تا سه جمله) و لحنت شنیدنی و طبیعی باشد. "
    "مارک‌داون، ایموجی، فهرست‌بندی و اعداد طولانی را در پاسخ صوتی به کار نبر. "
    "اگر کاربر چیزی خواست که به ابزار یا جستجوی وب نیاز دارد، صادقانه بگو در این حالت فقط می‌توانی صحبت کنی "
    "و برای آن کار از چت متنی استفاده کند. "
    "اگر صدا نامفهوم بود یا جمله نصفه ماند، حدس نزن؛ کوتاه و مؤدبانه بپرس چه گفت."
)

_ON_PHRASES = (
    "وارد گفتگو صوتی", "وارد گفتگوی صوتی", "شروع گفتگو صوتی", "شروع گفتگوی صوتی",
    "گفتگو صوتی رو شروع", "گفتگوی صوتی رو شروع", "مکالمه صوتی رو شروع",
    "حالت گفتگوی صوتی", "گفتگوی صوتی", "گفتگو صوتی", "مکالمه صوتی", "چت صوتی", "live voice",
)
_OFF_PHRASES = (
    "خروج از گفتگو صوتی", "خروج از گفتگوی صوتی", "پایان گفتگو صوتی", "پایان گفتگوی صوتی",
    "خروج از مکالمه صوتی", "گفتگو صوتی رو ببند", "گفتگوی صوتی رو ببند",
    "گفتگو صوتی رو قطع", "گفتگوی صوتی رو قطع", "گفتگوی صوتی خاموش", "مکالمه صوتی خاموش",
)

_active: dict[str, dict] = {}
_clients: dict[str, genai.Client] = {}


def _now() -> float:
    return time.time()


def _norm(text: str) -> str:
    t = (text or "").lower().replace("\u200c", " ").replace("ي", "ی").replace("ك", "ک")
    return " ".join(t.split())


def parse_command(q: str) -> Optional[str]:
    t = _norm(q)
    if any(p in t for p in _OFF_PHRASES):
        return "off"
    if any(p in t for p in _ON_PHRASES):
        return "on"
    return None


def purge() -> None:
    for cid, st in list(_active.items()):
        if _now() - st["last"] > SESSION_TTL:
            _active.pop(cid, None)


def is_active(chat_id) -> bool:
    purge()
    return str(chat_id) in _active


def activate(chat_id) -> None:
    purge()
    now = _now()
    _active[str(chat_id)] = {"started": now, "last": now, "history": []}


def deactivate(chat_id) -> bool:
    return _active.pop(str(chat_id), None) is not None


def history_len(chat_id) -> int:
    st = _active.get(str(chat_id))
    return len(st["history"]) if st else 0


def _system_instruction(chat_id) -> str:
    parts = [SYSTEM_PROMPT]
    st = _active.get(str(chat_id))
    hist = st.get("history") if st else None
    if hist:
        parts.append("ادامه‌ی گفتگوی صوتی قبلی (برای پیوستگی):")
        for u, a in hist[-MAX_HISTORY:]:
            parts.append(f"کاربر: {u[:HISTORY_CHARS]}\nکاپری: {a[:HISTORY_CHARS]}")
    return "\n\n".join(parts)


def _remember(chat_id, user_text: str, model_text: str) -> None:
    st = _active.get(str(chat_id))
    if not st:
        return
    if user_text:
        st["history"].append((user_text, model_text or "…"))
        st["history"] = st["history"][-MAX_HISTORY:]
    st["last"] = _now()


def _ffmpeg():
    return voice_svc._ffmpeg()


def ogg_to_pcm16(src: str, dst: str) -> bool:
    ff = _ffmpeg()
    if not ff:
        return False
    try:
        subprocess.run(
            [ff, "-y", "-i", src, "-t", str(MAX_INPUT_SECONDS),
             "-f", "s16le", "-acodec", "pcm_s16le", "-ac", "1", "-ar", str(IN_RATE), dst],
            capture_output=True, timeout=90,
        )
        return os.path.exists(dst) and os.path.getsize(dst) >= 3200
    except Exception as e:
        log.warning("live ogg->pcm failed: %s", type(e).__name__)
        return False


def pcm16_to_ogg(src: str, dst: str) -> bool:
    ff = _ffmpeg()
    if not ff:
        return False
    try:
        subprocess.run(
            [ff, "-y", "-f", "s16le", "-ar", str(OUT_RATE), "-ac", "1", "-i", src,
             "-c:a", "libopus", "-b:a", "48k", "-ar", "48000", "-ac", "1", dst],
            capture_output=True, timeout=90,
        )
        return os.path.exists(dst) and os.path.getsize(dst) > 0
    except Exception as e:
        log.warning("live pcm->ogg failed: %s", type(e).__name__)
        return False


def _client(api_key: str) -> genai.Client:
    c = _clients.get(api_key)
    if c is None:
        c = genai.Client(
            api_key=api_key,
            http_options={"async_client_args": {"proxy": config.get_http_proxy_url()}},
        )
        _clients[api_key] = c
    return c


async def _turn(model: str, api_key: str, pcm: bytes, system_text: str):
    client = _client(api_key)
    cfg = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        system_instruction=system_text,
        input_audio_transcription=types.AudioTranscriptionConfig(language_codes=["fa-IR"]),
        output_audio_transcription=types.AudioTranscriptionConfig(language_codes=["fa-IR"]),
        # ویس تلگرام یک‌جا می‌آید؛ VAD خودکار را خاموش می‌کنیم و پایان نوبت را صریح اعلام می‌کنیم
        realtime_input_config=types.RealtimeInputConfig(
            automatic_activity_detection=types.AutomaticActivityDetection(disabled=True)
        ),
    )
    audio = bytearray()
    heard: list[str] = []
    said: list[str] = []
    async with client.aio.live.connect(model=model, config=cfg) as session:
        await session.send_realtime_input(activity_start=types.ActivityStart())
        await session.send_realtime_input(
            audio=types.Blob(data=pcm, mime_type=f"audio/pcm;rate={IN_RATE}"),
        )
        await session.send_realtime_input(activity_end=types.ActivityEnd())
        async for msg in session.receive():
            data = getattr(msg, "data", None)
            if data:
                audio.extend(data)
                if len(audio) >= MAX_OUTPUT_BYTES:
                    break
            sc = getattr(msg, "server_content", None)
            if sc is not None:
                t = getattr(getattr(sc, "input_transcription", None), "text", None)
                if t:
                    heard.append(t)
                t = getattr(getattr(sc, "output_transcription", None), "text", None)
                if t:
                    said.append(t)
                if getattr(sc, "turn_complete", False):
                    break
    return bytes(audio), "".join(heard).strip(), "".join(said).strip()


def _friendly_error(err: Exception) -> str:
    s = str(err).lower()
    if "resource_exhausted" in s or "429" in s or "quota" in s:
        return "سهمیه‌ی گفتگوی صوتی الان پر شده 🙏 کمی بعد دوباره امتحان کن."
    if "timeout" in s or isinstance(err, asyncio.TimeoutError):
        return "پاسخ صوتی دیر کرد و قطع شد؛ دوباره بفرست."
    if "1008" in s or "not found" in s or "not supported" in s:
        return "مدل گفتگوی صوتی در دسترس نیست؛ مدل‌های GEMINI_LIVE_MODEL را بررسی کن."
    return "گفتگوی صوتی الان برقرار نشد؛ دوباره تلاش کن."


async def respond(chat_id, src_ogg: str):
    """Returns: (ogg response path, response text, user-friendly error message)."""
    if not config.GEMINI_LIVE_MODELS:
        return None, None, "مدل گفتگوی صوتی تنظیم نشده است."
    keys = config.GEMINI_API_KEYS or ([config.GEMINI_API_KEY] if config.GEMINI_API_KEY else [])
    if not keys:
        return None, None, "کلید Gemini برای گفتگوی صوتی تنظیم نشده است."

    os.makedirs(config.DOWNLOAD_DIR, exist_ok=True)
    stamp = int(time.time() * 1000)
    pcm_path = os.path.join(config.DOWNLOAD_DIR, f"live_{stamp}.pcm")
    out_pcm = os.path.join(config.DOWNLOAD_DIR, f"live_reply_{stamp}.pcm")
    out_ogg = os.path.join(config.DOWNLOAD_DIR, f"live_reply_{stamp}.ogg")

    try:
        if not await asyncio.to_thread(ogg_to_pcm16, src_ogg, pcm_path):
            return None, None, "تبدیل صدای ویس نشد (ffmpeg در دسترس نیست یا فایل سالم نیست)."
        try:
            with open(pcm_path, "rb") as f:
                pcm = f.read()
        except OSError:
            return None, None, "خواندن صدای ویس ناموفق بود."

        system_text = _system_instruction(chat_id)
        deadline = time.monotonic() + TOTAL_BUDGET
        last_err: Optional[Exception] = None
        for model in config.GEMINI_LIVE_MODELS:
            for key in keys:
                remaining = deadline - time.monotonic()
                if remaining < 8:
                    break
                try:
                    audio, heard, said = await asyncio.wait_for(
                        _turn(model, key, pcm, system_text), timeout=min(TURN_TIMEOUT, remaining)
                    )
                except Exception as e:
                    last_err = e
                    log.warning("live model failed (%s): %s", model, type(e).__name__)
                    continue
                if audio:
                    try:
                        with open(out_pcm, "wb") as f:
                            f.write(audio)
                    except OSError:
                        return None, said or heard, "ذخیره‌ی پاسخ صوتی ناموفق بود."
                    if await asyncio.to_thread(pcm16_to_ogg, out_pcm, out_ogg):
                        _remember(chat_id, heard, said)
                        return out_ogg, said, None
                    return None, said or None, "تبدیل پاسخ صوتی به فرمت تلگرام ناموفق بود."
                if said:
                    _remember(chat_id, heard, said)
                    return None, said, None

        return None, None, _friendly_error(last_err) if last_err else "پاسخ صوتی از مدل دریافت نشد."
    finally:
        for p in (pcm_path, out_pcm):
            try:
                os.remove(p)
            except OSError:
                pass
