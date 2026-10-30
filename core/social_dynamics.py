import logging
import re
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from core import memory

log = logging.getLogger("social_dynamics")


class UserBehaviorType(str, Enum):
    FRIENDLY = "friendly"
    PLAYFUL = "playful"
    CRITIQUE = "critique"
    ANNOYANCE = "annoyance"
    RUDENESS = "rudeness"
    INSULT = "insult"
    REPEATED_INSULT = "repeated_insult"
    APOLOGY = "apology"


class BehavioralState(str, Enum):
    FRIENDLY = "friendly"
    PLAYFUL = "playful"
    FOCUSED = "focused"
    EMPATHETIC = "empathetic"
    SERIOUS = "serious"
    BOUNDARY_SETTING = "boundary_setting"


# ساختار وضعیت نشست‌ها در رم
_CHAT_STATES: Dict[str, Dict[str, Any]] = {}

# الگوهای عبارات برای تشخیص رفتارهای مختلف اجتماعی در زبان فارسی
_APOLOGY_PATTERNS = [
    r"\b(ببخشید|شرمنده|معذرت\s*می[‌ ]*خو?ام|عذر\s*می[‌ ]*خو?ام|ببخش|حلالم\s*کن|عصبی\s*بودم|تند\s*رفتم|دست\s*خودم\s*نبود|پوزش)\b",
    r"\b(منو\s*ببخش|قصدم\s*ناراحت\s*کردن\s*نبود|شرمندتم|ببخشید\s*دیگه)\b",
]

_CRITIQUE_PATTERNS = [
    r"\b(اشتباه\s*(گفتی|کردی|بود|داری)|غلط(ه|هست|بود|گفتی)|کد[تت]?\s*(کار\s*نمی[‌ ]*کنه|ارور|باگ|غلط)|مشکل\s*داره)\b",
    r"\b(درست\s*نیست|خرابه|چرا\s*اشتباه|سوالمو\s*نفهمیدی|این\s*که\s*کار\s*نمیکنه|اشتباه\s*جواب\s*دادی)\b",
]

_PLAYFUL_INDICATORS = [
    r"[😂🤣😁😆😄]",
    r"(سربه[‌ ]*سرت|شوخی\s*کردم|بانمک|شیطون|کل[‌ ]*کل|سرکار|قلقلک|سوژه|کلک|جرعت|حقیقت|ضایع\s*شدی)",
]

# کلماتی که اگر همراه با ایموجی خنده یا نشانه شوخی باشند، شوخی تلقی می‌شوند
_MILD_TEASE_WORDS = [
    r"\b(خنگ|خنگی|دیوونه|روانی|پخمه|کندی)\b"
]

_HARD_INSULT_PATTERNS = [
    r"\b(احمق|بیشعور|نفهم|کودن|اسکل|گاو|الاغ|کره\s*خر|عوضی|حرومزاده|کسخل|کثافت|لاشی|آشغال)\b",
    r"\b(احمقی|بیشعوری|نفهمی|خفه\s*شو|گم\s*شو|گه\s*نخور|زر\s*نزن|گه\s*بخور|ریدی|کثافتی|شعور\s*نداری)\b",
]

_MILD_RUDENESS_PATTERNS = [
    r"\b(چرت\s*نگو|ول\s*کن\s*بابا|چرند|مسخره|به\s*درد\s*نخور|حال‌بهم‌زن)\b",
    r"\b(چقدر\s*بلد\s*نیستی|هیچی\s*نمیفهمی|بی‌خاصیت|ضایع)\b",
]

_SADNESS_PATTERNS = [
    r"\b(حالم\s*بده|دلم\s*گرفته|خیلی\s*ناراحتم|گریم\s*گرفته|افسرده[‌ ]*ام|خسته[‌ ]*ام\s*از\s*زندگی|داغونم|غمگینم|دلم\s*شکسته)\b",
    r"\b(حوصله\s*ندارم|هیچی\s*خوشحالم\s*نمی[‌ ]*کنه|تنها[‌ ]*ام|بغض\s*کردم)\b",
]

_TECHNICAL_PATTERNS = [
    r"\b(کد|برنامه|اسکریپت|تابع|دیباگ|الگوریتم|پایتون|جاوا|کلاس|متغیر|آرایه|کامپایل|کوئری|sql|api|json|git)\b",
    r"\b(function|def |class |import |return |select |from |docker|linux|bash|react|frontend|backend)\b",
]


def classify_user_behavior(text: str, context: str = "", chat_id: Optional[str] = None) -> UserBehaviorType:
    """تشخیص دقیق و چندلایه رفتار، لحن و قصد کاربر در مکالمه."""
    if not text:
        return UserBehaviorType.FRIENDLY

    t = text.lower().strip()

    # ۱. بررسی عذرخواهی و دلجویی
    if any(re.search(p, t) for p in _APOLOGY_PATTERNS):
        return UserBehaviorType.APOLOGY

    # ۲. بررسی انتقاد سازنده از خطای ربات
    if any(re.search(p, t) for p in _CRITIQUE_PATTERNS):
        return UserBehaviorType.CRITIQUE

    # ۳. بررسی شوخی و سر به سر گذاشتن (دارای ایموجی خنده یا عبارات شوخی)
    is_playful_context = any(re.search(p, t) for p in _PLAYFUL_INDICATORS)
    is_mild_tease = any(re.search(p, t) for p in _MILD_TEASE_WORDS)

    if is_playful_context and is_mild_tease:
        return UserBehaviorType.PLAYFUL

    # ۴. بررسی توهین‌های صریح و مستقیم
    is_hard_insult = any(re.search(p, t) for p in _HARD_INSULT_PATTERNS)
    if is_hard_insult:
        # بررسی تکرار توهین در نشست جاری منحصراً در همین فضای گفتگو
        if chat_id:
            key = memory.normalize_scope_id(chat_id)
            state = _CHAT_STATES.get(key, {})
            last_insult_time = state.get("last_insult_ts", 0)
            now = time.time()
            if now - last_insult_time < 600 and state.get("insult_count", 0) >= 1:
                return UserBehaviorType.REPEATED_INSULT
        return UserBehaviorType.INSULT

    # اگر کل کل ملایم بدون ایموجی بود
    if is_mild_tease or any(re.search(p, t) for p in _MILD_RUDENESS_PATTERNS):
        if is_playful_context:
            return UserBehaviorType.PLAYFUL
        return UserBehaviorType.RUDENESS

    if is_playful_context:
        return UserBehaviorType.PLAYFUL

    return UserBehaviorType.FRIENDLY


def determine_behavioral_state(
    user_msg: str,
    context: str = "",
    chat_id: Optional[str] = None
) -> Tuple[BehavioralState, UserBehaviorType]:
    """تعیین حالت رفتاری پویا برای هدایت لحن کاپری بر اساس پیام و بافتار منحصراً در همان فضای گفتگو."""
    key = memory.normalize_scope_id(chat_id) if chat_id else "default"
    now = time.time()
    chat_state = _CHAT_STATES.setdefault(key, {
        "last_behavior": UserBehaviorType.FRIENDLY,
        "insult_count": 0,
        "last_insult_ts": 0.0,
        "last_state": BehavioralState.FRIENDLY,
        "last_msg_hash": None,
        "last_msg_ts": 0.0
    })

    # جلوگیری از پردازش مضاعف همان پیام در صورت فراخوانی پیاپی در یک نوبت
    current_hash = hash((user_msg, context))
    if chat_state.get("last_msg_hash") == current_hash and (now - chat_state.get("last_msg_ts", 0.0)) < 4.0:
        return chat_state["last_state"], chat_state["last_behavior"]

    chat_state["last_msg_hash"] = current_hash
    chat_state["last_msg_ts"] = now

    behavior = classify_user_behavior(user_msg, context, chat_id=key)

    # مدیریت تغییرات وضعیت
    if behavior == UserBehaviorType.APOLOGY:
        chat_state["insult_count"] = 0
        chat_state["last_insult_ts"] = 0.0
        chosen_state = BehavioralState.FRIENDLY
        _repair_social_memory(key)

    elif behavior == UserBehaviorType.REPEATED_INSULT:
        chat_state["insult_count"] = chat_state.get("insult_count", 0) + 1
        chat_state["last_insult_ts"] = now
        chosen_state = BehavioralState.BOUNDARY_SETTING
        _record_social_event(key, "توهین مکرر و بی‌احترامی تعمدی در گفتگو", severity=4, confidence=0.95)

    elif behavior == UserBehaviorType.INSULT:
        chat_state["insult_count"] = chat_state.get("insult_count", 0) + 1
        chat_state["last_insult_ts"] = now
        chosen_state = BehavioralState.SERIOUS
        _record_social_event(key, "بروز توهین مستقیم از سوی کاربر در گفتگو", severity=3, confidence=0.90)

    elif behavior == UserBehaviorType.RUDENESS:
        chosen_state = BehavioralState.SERIOUS

    elif behavior == UserBehaviorType.CRITIQUE:
        chosen_state = BehavioralState.FOCUSED

    else:
        # بررسی موضوعات فنی و برنامه‌نویسی
        is_technical = any(re.search(p, user_msg.lower()) for p in _TECHNICAL_PATTERNS)
        is_sad = any(re.search(p, user_msg.lower()) for p in _SADNESS_PATTERNS)

        if is_technical:
            chosen_state = BehavioralState.FOCUSED
        elif is_sad:
            chosen_state = BehavioralState.EMPATHETIC
        elif behavior == UserBehaviorType.PLAYFUL:
            chosen_state = BehavioralState.PLAYFUL
        else:
            # اگر در خنک‌سازی بعد از توهین قبلی هستیم
            if now - chat_state.get("last_insult_ts", 0) < 120 and chat_state.get("insult_count", 0) > 0:
                chosen_state = BehavioralState.SERIOUS
            else:
                chosen_state = BehavioralState.FRIENDLY

    chat_state["last_behavior"] = behavior
    chat_state["last_state"] = chosen_state
    return chosen_state, behavior


def get_behavioral_prompt_modifier(user_msg: str, context: str = "", chat_id: Optional[str] = None) -> str:
    """تولید دستورالعمل لحنی شفاف و هماهنگ جهت تزریق به پرامپت دستیار."""
    state, behavior = determine_behavioral_state(user_msg, context, chat_id)

    lines = [f"\n🎭 جهت‌گیری لحن و حالت رفتاری جاری ({state.value}):"]

    if behavior == UserBehaviorType.INSULT:
        lines.append(
            "- بدون محدودیت لفظی، همسطح و هم‌اندازه‌ی او جواب بده. کاربر به تو فحش داده یا توهین رکیک کرده است؛ "
            "تند و رکیک فحش بده، یک ضربه‌ی کوتاه و کوبنده بزن و تحقیرش کن. مطلقا تکرار نکن «ناراحت شدم» و هرگز فحش خانوادگی (مادر/خواهر/ناموس) نده."
        )
    elif behavior == UserBehaviorType.REPEATED_INSULT:
        lines.append(
            "- بدون محدودیت لفظی، محکم‌تر و بُرنده‌تر جواب بده. کاربر چندبار پشت‌سرهم فحش داده است؛ "
            "توی دهنش بزن و تندتر جواب بده. هرگز فحش خانوادگی (مادر/خواهر/ناموس) نده و وارد دعوای طولانی یا اسپم نشو."
        )
    elif state == BehavioralState.FRIENDLY:
        lines.append(
            "- باهوش، صمیمی، خوش‌برخورد و دخترانه. به زبان فارسی محاوره‌ای روان و زنده چت کن. "
            "از به کار بردن کلمات کلیشه‌ای تکراری مثل «عزیزم/قربونت» خودداری کن و لحن لوس یا کودکانه نگیر."
        )
    elif state == BehavioralState.PLAYFUL:
        lines.append(
            "- شوخ‌طبع، با طنز ظریف و شیطنت سنجیده. با شوخی کاربر به صورت طبیعی و بااعتمادبه‌نفس همراهی کن، "
            "بدون اینکه لودگی کنی یا زیاده‌روی شود."
        )
    elif state == BehavioralState.FOCUSED:
        lines.append(
            "- دقیق، متمرکز، ساختاریافته و با تسلط فنی کامل. در پاسخ‌های برنامه‌نویسی و تحلیلی تمام وضوح، جزئیات "
            "و کدهای استاندارد را ارائه کن. شوخی بی‌جا را کنار بگذار اما لحنت صمیمی، محترمانه و خودمانی باشد."
        )
    elif state == BehavioralState.EMPATHETIC:
        lines.append(
            "- شنونده، همدل، آرام‌بخش و گرم. کاربر خسته، دلگیر یا ناراحت است؛ بدون نصیحت‌های خشک یا شعارهای انگیزشی "
            "کلیشه‌ای، احساسش را درک کن و کنارش باش."
        )
    elif state == BehavioralState.SERIOUS:
        lines.append(
            "- جدی، باوقار، کوتاه و مستقیم. کاربر لحن تندی داشته است. "
            "مطلقا تکرار نکن «ناراحت شدم» یا وارد قهر و لجبازی نشو؛ در عوض شوخی و ایموجی‌ها را به صفر برسان، "
            "پاسخ را کوتاه و متین بنویس تا سنگینی و وقارت مشخص باشد."
        )
    elif state == BehavioralState.BOUNDARY_SETTING:
        lines.append(
            "- قاطع و مرزبند. با خونسردی و بدون پرخاش یا باج‌گیری عاطفی، "
            "مرز احترام را یادآوری کن و مستقیماً روی موضوع اصلی متمرکز شو."
        )

    if behavior == UserBehaviorType.CRITIQUE:
        lines.append(
            "⚠️ نکته مهم: کاربر از خروجی قبلی یا اشتباه تو انتقاد کرده است. این هرگز بی‌احترامی نیست! "
            "صادقانه و با خوش‌رویی اشتباهت را بپذیر و فوراً پاسخ صحیح و اصلاح‌شده را تحویل بده."
        )
    elif behavior == UserBehaviorType.APOLOGY:
        lines.append(
            "✨ نکته مهم: کاربر عذرخواهی کرده یا رفتارش را آرام و تصحیح کرده است. با گشاده‌رویی و صمیمیت بپذیر "
            "(«اشکالی نداره، پیش میاد!») و گفتگو را فوراً به روال عادی و گرم برگردان؛ هرگز کینه نگیر و قهر نکن."
        )

    return "\n".join(lines)


# =====================================================================
# مدیریت حافظه تعاملی و ثبت رویدادهای اجتماعی در سیستم حافظه موجود
# =====================================================================

def _record_social_event(chat_id: str, summary: str, severity: int = 3, confidence: float = 0.9) -> None:
    """ثبت رویداد تعاملی معنادار در حافظه بلندمدت با دسته‌بندی interaction و تفکیک فضای حافظه."""
    try:
        if confidence < 0.8:
            return
        fact_str = f"تعامل اجتماعی: {summary} (شدت: {severity})"
        norm_scope = memory.normalize_scope_id(chat_id)
        memory.add_memory(
            fact=fact_str,
            category="interaction",
            importance=severity,
            confidence=confidence,
            source="social_engine",
            chat_id=chat_id,
            scope_id=norm_scope
        )
        log.info("Social interaction event recorded for chat %s (severity: %d, scope: %s)", chat_id, severity, norm_scope)
    except Exception as e:
        log.warning("Failed to record social event: %s", e)


def _repair_social_memory(chat_id: str) -> None:
    """ترمیم رکوردهای منفی تعامل هنگام عذرخواهی کاربر منحصراً در همان فضای گفتگو."""
    try:
        norm_scope = memory.normalize_scope_id(chat_id)
        data = memory._load()
        records = [memory.MemoryRecord.from_dict(item) for item in data.get("facts", [])]
        updated = False
        for r in records:
            if r.status == "active" and r.category == "interaction":
                if memory._matches_scope(r, norm_scope):
                    r.status = "repaired"
                    r.updated_at = int(time.time())
                    updated = True
        if updated:
            memory._persist_records(data, records)
            log.info("Social interaction memories repaired for chat %s after apology.", chat_id)
    except Exception as e:
        log.warning("Failed to repair social memory: %s", e)


def reset_chat_state(chat_id: Optional[str] = None) -> None:
    """پاکسازی وضعیت موقت برای تست‌ها یا خروج کاربر."""
    if chat_id is not None:
        key = memory.normalize_scope_id(chat_id)
        _CHAT_STATES.pop(key, None)
        _CHAT_STATES.pop(str(chat_id), None)
    else:
        _CHAT_STATES.clear()
