import json
import os

from core import config

FILE = os.path.join(config.BASE_DIR, "settings.json")

DEFAULTS = {"model": "auto"}

GEMINI_VOICES = {
    "Puck": {"fa": "پاک (Puck)", "desc": "پرانرژی، پویا و صمیمی", "type": "جوان"},
    "Charon": {"fa": "شارون (Charon)", "desc": "بم، عمیق، رسمی و جدی", "type": "مردانه/بم"},
    "Kore": {"fa": "کوره (Kore)", "desc": "آرامش‌بخش، گرم و باوقار", "type": "زنانه/گرم"},
    "Fenrir": {"fa": "فنریر (Fenrir)", "desc": "رسا، باصلابت و قدرتمند", "type": "مردانه/حماسی"},
    "Aoede": {"fa": "آئوده (Aoede)", "desc": "ملایم، لطیف و متفکر", "type": "زنانه/آرام"},
}


def load() -> dict:
    try:
        with open(FILE, encoding="utf-8") as f:
            data = json.load(f)
        return {**DEFAULTS, **data}
    except Exception:
        return dict(DEFAULTS)


def save(**kw) -> None:
    data = load()
    data.update(kw)
    from core import fsutil
    fsutil.atomic_write_json(FILE, data)


def get_model() -> str:
    return load().get("model", "auto")


def set_model(name: str) -> None:
    save(model=name, service="", model_id="")


def get_selection():
    """(service, model_id) انتخاب‌شده یا (None, None)."""
    d = load()
    s = d.get("service", "")
    m = d.get("model_id", "")
    return (s, m) if s and m else (None, None)


def set_selection(service: str, model_id: str) -> None:
    d = load()
    prev = {"service": d.get("service", ""), "model": d.get("model_id", "")}
    save(service=service, model_id=model_id, model=service, previous=prev)


def get_previous():
    d = load()
    p = d.get("previous", {})
    s, m = p.get("service", ""), p.get("model", "")
    return (s, m) if s and m else (None, None)


def get_tts_engine() -> str:
    return load().get("tts_engine", "microsoft")


def set_tts_engine(engine: str) -> None:
    save(tts_engine=engine)


def get_tts_voice() -> str:
    return load().get("tts_voice", "fa-IR-FaridNeural")


def set_tts_voice(voice: str) -> None:
    save(tts_voice=voice)


def get_gemini_voice() -> str:
    """دریافت نام گوینده فعال جمینای (Puck, Charon, Kore, Fenrir, Aoede)."""
    return load().get("gemini_voice", "Puck")


def set_gemini_voice(voice: str) -> None:
    """تنظیم گوینده جمینای."""
    save(gemini_voice=voice)


def get_voice_speaker() -> str:
    """دریافت نام فارسی گوینده فعال برای داشبورد و آمار سیستم."""
    engine = get_tts_engine()
    if engine == "gemini":
        gv = get_gemini_voice()
        info = GEMINI_VOICES.get(gv, {})
        fa_name = info.get("fa", gv)
        return f"جمینای ({fa_name})"
    v = get_tts_voice()
    if "Dilara" in v:
        return "دلارا"
    if "Farid" in v:
        return "فرید"
    return v or "دلارا"
