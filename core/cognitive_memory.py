import asyncio
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

from ai_engine import ai
from core import config
from ai_engine import providers
from core import settings

log = logging.getLogger("cognitive_memory")

COGNITIVE_FILE = os.path.join(config.BASE_DIR, "cognitive_memory.json")

DEFAULT_MODEL = {
    "user_profile": {
        "name": getattr(config, "OWNER_NAME", "") or "Owner",
        "interests": [],
        "tone_preference": "صمیمی، محاوره‌ای، کوتاه، بدون پرحرفی",
        "habits": []
    },
    "key_facts": [
        "کاربر ترجیح می‌دهد کاپری به عنوان دستیار هوشمند تلگرام پاسخ‌های دقیق، خودمانی و بدون مقدمه‌چینی بدهد",
    ],
    "self_model": [
        "مالک ترجیح می‌دهد کاپری دستیار دقیق، خودمانی و بدون مقدمه‌چینی باشد",
    ],
    "social_context": {
        "important_topics": []
    },
    "reflection_history": []
}


def _load() -> Dict[str, Any]:
    if not os.path.exists(COGNITIVE_FILE):
        _save(DEFAULT_MODEL)
        return DEFAULT_MODEL
    try:
        with open(COGNITIVE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # اطمینان از وجود کلیدهای اصلی
            for k, v in DEFAULT_MODEL.items():
                if k not in data:
                    data[k] = v
            return data
    except Exception as e:
        log.warning(f"Error reading cognitive memory: {e}")
        return DEFAULT_MODEL


def _save(data: Dict[str, Any]) -> None:
    try:
        from core import fsutil
        fsutil.atomic_write_json(COGNITIVE_FILE, data)
    except Exception as e:
        log.error(f"Error saving cognitive memory: {e}")


def get_context_summary() -> str:
    """خلاصه‌ای عمیق و شناختی از هویت، علایق، عادات و دانسته‌های کاپری درباره کاربر جهت تزریق به پرامپت دستیار."""
    data = _load()
    prof = data.get("user_profile", {})
    facts = data.get("key_facts", [])
    self_notes = data.get("self_model", [])

    lines = []
    lines.append(f"نام کاربر: {prof.get('name', 'کاربر')}")
    if prof.get("interests"):
        lines.append(f"علایق و تخصص‌ها: {', '.join(prof['interests'])}")
    if prof.get("tone_preference"):
        lines.append(f"سلیقه لحن و ارتباط: {prof['tone_preference']}")
    if prof.get("habits"):
        lines.append(f"عادات و ترجیحات رفتاری: {', '.join(prof['habits'])}")
    if facts:
        lines.append("نکات و حقایق کلیدی تثبیت‌شده:")
        for f in facts[-8:]:
            lines.append(f"  • {f}")
    if self_notes:
        lines.append("شناخت کاپری از خودش (درخواست‌ها و ترجیحات رفتاری مالک دربارهٔ تو — حتماً رعایت کن):")
        for s in self_notes[-10:]:
            lines.append(f"  • {s}")

    return "\n".join(lines)


def _clean_json_str(s: str) -> str:
    s = s.strip()
    if s.startswith("```json"):
        s = s[7:]
    elif s.startswith("```"):
        s = s[3:]
    if s.endswith("```"):
        s = s[:-3]
    return s.strip()


async def reflect_interaction(user_msg: str, bot_response: str, scope_id: Optional[Any] = None) -> None:
    """
    حلقه تأمل شناختی در پس‌زمینه (Autonomous Reflection):
    پیام اخیر کاربر و پاسخ دستیار را بررسی می‌کند و بدون ایجاد وقفه در عملکرد ربات،
    حقایق جدید، علایق، ترجیحات و عادات جدید را کشف و در فایل حافظه شناختی تثبیت می‌کند.
    """
    if not user_msg or len(user_msg.strip()) < 4:
        return

    # پیام‌های کوتاه دستوری مثل «سلام» یا «بله» نیاز به تأمل عمیق ندارند
    SKIP_WORDS = {"سلام", "خوبی", "چطوری", "مرسی", "ممنون", "ok", "اوکی", "اره", "آره", "نه", "باشه"}
    if user_msg.strip().lower() in SKIP_WORDS:
        return

    data = _load()
    current_prof = data.get("user_profile", {})
    current_facts = data.get("key_facts", [])

    prompt = (
        "تو ناظر شناختی هوش مصنوعی کاپری (Capri Cognitive Engine) هستی.\n"
        "تعامل اخیر بین کاربر تلگرام و کاپری را بررسی کن و به‌جای ذخیرهٔ متن خام، الگوهای ماندگار را کشف و تقطیر کن:\n\n"
        f"پیام کاربر: «{user_msg}»\n"
        f"پاسخ دستیار: «{bot_response[:300]}»\n\n"
        f"شناخت فعلی:\n"
        f"- علایق: {current_prof.get('interests', [])}\n"
        f"- عادات: {current_prof.get('habits', [])}\n"
        f"- حقایق کلیدی: {current_facts[-5:]}\n\n"
        "وظیفهٔ تو تأمل (Reflection) است. اگر نکتهٔ ماندگار و جدیدی کشف شد که ارزش ثبت دارد، فقط یک آبجکت JSON معتبر به این فرمت برگردان:\n"
        "{\n"
        '  "new_facts": ["واقعیت جدید دربارهٔ کاربر یا خالی"],\n'
        '  "new_interests": ["علاقهٔ جدید یا خالی"],\n'
        '  "new_habits": ["عادت یا ترجیح جدید یا خالی"],\n'
        '  "self_notes": ["درخواست یا ترجیح رفتاری که کاربر دربارهٔ خودِ کاپری گفته (مثلاً شوخ‌تر باش، کوتاه جواب بده، با فلانی این‌جور رفتار کن) یا خالی"]\n'
        "}\n"
        "قوانین:\n"
        "- هر آیتم باید یک جملهٔ کوتاهِ تقطیرشده باشد، نه کپی متن خام کاربر.\n"
        "- اگر پیام احوالپرسی یا سؤال عمومی بود و نکتهٔ ماندگاری نداشت، همهٔ آرایه‌ها را خالی بگذار.\n"
        "- فقط و فقط کد JSON برگردان بدون هیچ توضیح اضافه."
    )

    try:
        raw_res = await asyncio.to_thread(ai.ask, prompt)
        clean = _clean_json_str(raw_res)
        m = re.search(r"\{.*\}", clean, re.DOTALL)
        if not m:
            return
        parsed = json.loads(m.group(0))

        updated = False
        new_facts = parsed.get("new_facts") or []
        for nf in new_facts:
            nf = str(nf).strip()
            if nf and nf not in current_facts and len(nf) > 4:
                current_facts.append(nf)
                updated = True
                try:
                    from core import memory
                    memory.add_memory(nf, scope_id=scope_id)
                except Exception:
                    pass

        new_interests = parsed.get("new_interests") or []
        interests = current_prof.setdefault("interests", [])
        for ni in new_interests:
            ni = str(ni).strip()
            if ni and ni not in interests:
                interests.append(ni)
                updated = True

        new_habits = parsed.get("new_habits") or []
        habits = current_prof.setdefault("habits", [])
        for nh in new_habits:
            nh = str(nh).strip()
            if nh and nh not in habits:
                habits.append(nh)
                updated = True

        new_self = parsed.get("self_notes") or []
        self_notes = data.setdefault("self_model", [])
        for sn in new_self:
            sn = str(sn).strip()
            if sn and sn not in self_notes and len(sn) > 4:
                self_notes.append(sn)
                updated = True

        if updated:
            data["key_facts"] = current_facts[-100:]  # نگهداری ۱۰۰ حقیقت مهم
            data["user_profile"] = current_prof
            data["self_model"] = self_notes[-30:]  # نگهداری ۳۰ یادداشت خودشناسی
            # ثبت در تاریخچه تاملات
            history = data.setdefault("reflection_history", [])
            history.append({
                "trigger": user_msg[:100],
                "added_facts": new_facts,
                "added_interests": new_interests,
                "added_self_notes": new_self
            })
            data["reflection_history"] = history[-50:]
            _save(data)
            log.info(f"Cognitive memory updated autonomously from message: {user_msg[:50]}")
    except Exception as e:
        log.debug(f"Reflection cycle error: {e}")


def get_media_preferences() -> Dict[str, Any]:
    """دریافت تنظیمات و ذائقه یادگرفته‌شده کاربر برای دانلود فیلم و سریال."""
    data = _load()
    return data.get("media_preferences", {
        "default_quality": 720,
        "default_audio": "dubbed",
        "series_progress": {}
    })


def update_media_preferences(quality: Optional[int] = None, audio: Optional[str] = None,
                            series_title: Optional[str] = None, season: Optional[int] = None,
                            episode: Optional[Any] = None) -> None:
    """ذخیره و یادگیری ترجیحات کاربر (کیفیت محبوب، دوبله/زیرنویس، آخرین فصل/قسمت دیده شده)."""
    data = _load()
    prefs = data.setdefault("media_preferences", {
        "default_quality": 720,
        "default_audio": "dubbed",
        "series_progress": {}
    })
    if quality:
        prefs["default_quality"] = quality
    if audio:
        prefs["default_audio"] = audio
    if series_title:
        st = series_title.lower().strip()
        prog = prefs.setdefault("series_progress", {})
        s_data = prog.setdefault(st, {})
        if season is not None:
            s_data["last_season"] = season
        if episode is not None:
            s_data["last_episode"] = episode
    _save(data)
    log.info(f"Media preferences updated: quality={quality}, audio={audio}, series={series_title}")
