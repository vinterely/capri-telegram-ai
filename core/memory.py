import json
import logging
import os
import re
import threading
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from core import config

log = logging.getLogger("memory")

MEMORY_FILE = os.path.join(config.BASE_DIR, "memory.json")
BACKUP_FILE = os.path.join(config.BASE_DIR, "private_backups", "memory_backup.json")

MAX_FACTS = 500
MAX_HISTORY = 100
MAX_SHORT_TERM_TOKENS = 1200  # سقف بودجه توکن برای پنجره مکالمه کوتاه‌مدت

# قفل همزمانی برای تضمین اتمیک بودن و پیشگیری ۱۰۰٪ از Race Condition در درخواست‌های همزمان
_MEMORY_LOCK = threading.RLock()
_CURRENT_OWNER_ID: Optional[int] = None


# =====================================================================
# 1. ساختار داده‌ای حافظه بلندمدت (Structured Long-Term Memory)
# =====================================================================

@dataclass
class MemoryRecord:
    id: str
    content: str
    category: str = "fact"  # fact, preference, decision, project, instruction, interaction
    importance: int = 3  # 1 (کم) تا 5 (بسیار مهم و حیاتی)
    confidence: float = 1.0  # 0.0 تا 1.0
    created_at: int = field(default_factory=lambda: int(time.time()))
    updated_at: int = field(default_factory=lambda: int(time.time()))
    source: str = "user"  # user, bot, reflection, tool, system, social_engine
    chat_id: Optional[str] = None
    status: str = "active"  # active, superseded, archived, repaired
    scope_id: Optional[str] = None  # شناسه قطعی و مستقل فضای حافظه (Scoped Namespace)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Any) -> "MemoryRecord":
        if isinstance(data, str):
            # تبدیل سازگار با رکوردهای متنی قدیمی (Legacy Plain String)
            rec_id = f"mem_{int(time.time())}_{abs(hash(data)) % 100000}"
            cat = cls._infer_category(data)
            return cls(
                id=rec_id,
                content=data.strip(),
                category=cat,
                importance=3,
                confidence=1.0,
                created_at=int(time.time()),
                updated_at=int(time.time()),
                source="legacy",
                status="active",
                scope_id=None
            )
        if isinstance(data, dict):
            raw_chat_id = str(data.get("chat_id")) if data.get("chat_id") is not None else None
            raw_scope_id = str(data.get("scope_id")) if data.get("scope_id") is not None else None
            # اگر scope_id ثبت نشده ولی chat_id دارد، مهاجرت خودکار انجام شود
            if not raw_scope_id and raw_chat_id:
                raw_scope_id = normalize_scope_id(raw_chat_id)
            return cls(
                id=str(data.get("id") or f"mem_{int(time.time())}_{int(time.time()*1000)%100000}"),
                content=str(data.get("content") or "").strip(),
                category=str(data.get("category") or "fact"),
                importance=int(data.get("importance") or 3),
                confidence=float(data.get("confidence") or 1.0),
                created_at=int(data.get("created_at") or int(time.time())),
                updated_at=int(data.get("updated_at") or int(time.time())),
                source=str(data.get("source") or "user"),
                chat_id=raw_chat_id,
                status=str(data.get("status") or "active"),
                scope_id=raw_scope_id
            )
        return cls(id=f"mem_{int(time.time())}", content=str(data))

    @staticmethod
    def _infer_category(text: str) -> str:
        t = text.lower()
        if any(w in t for w in ("علاقه‌مند", "دوست دارد", "ترجیح", "سلیقه", "خوشش می‌آید", "متنفر")):
            return "preference"
        if any(w in t for w in ("تصمیم", "مقرر شد", "از این به بعد", "قانون", "همیشه باید", "نباید")):
            return "decision"
        if any(w in t for w in ("پروژه", "برنامه", "مخزن", "کد", "ریپازیتوری", "بات", "سرور", "توسعه")):
            return "project"
        if any(w in t for w in ("دستور", "فرمان", "تنظیم کن", "اعمال کن")):
            return "instruction"
        if any(w in t for w in ("توهین", "بی‌ادبی", "عذرخواهی", "تعامل", "احترام", "پرخاش")):
            return "interaction"
        return "fact"


# =====================================================================
# 2. مدیریت و تفکیک فضاهای حافظه (Memory Scopes & Namespaces)
# =====================================================================

def set_owner_id(owner_id: Any) -> None:
    """تنظیم شناسه کاربری صاحب اکانت برای تشخیص معتبر و قطعی Saved Messages."""
    global _CURRENT_OWNER_ID
    try:
        if owner_id is not None:
            _CURRENT_OWNER_ID = int(owner_id)
    except Exception:
        pass


def get_owner_id() -> Optional[int]:
    """دریافت شناسه معتبر صاحب اکانت."""
    global _CURRENT_OWNER_ID
    if _CURRENT_OWNER_ID is not None:
        return _CURRENT_OWNER_ID
    try:
        from core import reactions
        if getattr(reactions, "_owner_id", None):
            return int(reactions._owner_id)
    except Exception:
        pass
    return None


def normalize_scope_id(
    chat_id: Any,
    chat_type: Optional[str] = None,
    is_saved_messages: bool = False,
    owner_id: Optional[Any] = None,
    account_id: Optional[Any] = None
) -> str:
    """
    نرمال‌سازی و ایجاد شناسه یکتا، قطعی و پایدار برای فضای حافظه:
    - گروه تلگرام: memory:group:<id>
    - کانال تلگرام: memory:channel:<id>
    - گفتگوی خصوصی (PV): memory:dm:<id>
    - پیام‌های ذخیره‌شده (Saved Messages): memory:saved:<owner_id>
    """
    if chat_id is None or chat_id == "":
        return ""

    raw = str(chat_id).strip()
    eff_owner = owner_id or get_owner_id()

    # اگر از قبل پیشوند استاندارد memory دارد
    if raw.startswith("memory:"):
        return raw

    # اگر پیشوند کوتاه دارد
    if raw.startswith("group:"):
        return f"memory:{raw}"
    if raw.startswith("dm:") or raw.startswith("private:"):
        clean = raw.split(":", 1)[1]
        return f"memory:dm:{clean}"
    if raw.startswith("saved:"):
        clean = raw.split(":", 1)[1]
        return f"memory:saved:{clean}"
    if raw.startswith("channel:"):
        return f"memory:{raw}"

    # تشخیص Saved Messages با اعتبارسنجی قطعی سیستمی
    if is_saved_messages or raw.lower() in ("saved", "me", "saved_messages", "self"):
        target_id = str(eff_owner) if eff_owner else (raw if raw not in ("saved", "me", "saved_messages", "self") else "self")
        return f"memory:saved:{target_id}"

    if eff_owner is not None and raw == str(eff_owner):
        return f"memory:saved:{eff_owner}"

    # تشخیص بر اساس نوع چت ارائه‌شده
    c_type = (chat_type or "").lower().strip()
    if c_type in ("group", "supergroup"):
        clean = raw.replace("group:", "").strip()
        return f"memory:group:{clean}"
    if c_type == "channel":
        clean = raw.replace("channel:", "").strip()
        return f"memory:channel:{clean}"
    if c_type in ("private", "dm", "user"):
        clean = raw.replace("dm:", "").replace("private:", "").strip()
        return f"memory:dm:{clean}"

    # تشخیص هوشمند بر اساس ویژگی‌های شناسه تلگرام
    if raw.startswith("-"):
        return f"memory:group:{raw}"
    if "group" in raw.lower():
        return f"memory:group:{raw}"
    if "user" in raw.lower() or "dm" in raw.lower() or "pv" in raw.lower():
        return f"memory:dm:{raw}"
    if raw.isdigit():
        # شناسه عددی مثبت در تلگرام کاربر/پیوی است
        return f"memory:dm:{raw}"

    # شناسه متنی سفارشی (برای تست‌ها یا شناسه‌های خاص)
    return f"memory:chat:{raw}"


def get_event_memory_scope(event: Any, owner_id: Optional[Any] = None) -> str:
    """
    استخراج قطعی و غیرقابل جعل شناسه فضای حافظه از یک پیام/رویداد تلگرام.
    این تابع به متن پیام یا نام نمایشی اعتماد نمی‌کند و منحصراً ساختار سیستمی تلگرام را بررسی می‌کند.
    """
    if event is None:
        return ""

    eff_owner = owner_id or get_owner_id()

    # اگر ورودی یک رشته یا عدد است و نه Event تلگرام
    if isinstance(event, (str, int)):
        return normalize_scope_id(event, owner_id=eff_owner)

    chat_id = getattr(event, "chat_id", None)
    if chat_id is None:
        chat_id = getattr(event, "peer_id", None)
    if chat_id is None:
        return ""

    is_priv = getattr(event, "is_private", False)
    is_grp = getattr(event, "is_group", False)
    is_chan = getattr(event, "is_channel", False)
    sender_id = getattr(event, "sender_id", None)

    # بررسی Saved Messages: چت خصوصی صاحب اکانت با خودش
    if is_priv and eff_owner is not None and int(chat_id) == int(eff_owner):
        return f"memory:saved:{eff_owner}"

    if is_priv and sender_id is not None and int(chat_id) == int(sender_id) and getattr(event, "out", False):
        return f"memory:saved:{chat_id}"

    if is_grp:
        return f"memory:group:{chat_id}"

    if is_chan and not is_grp:
        return f"memory:channel:{chat_id}"

    if is_priv:
        return f"memory:dm:{chat_id}"

    return normalize_scope_id(chat_id, owner_id=eff_owner)


def _matches_scope(rec: MemoryRecord, target_scope: Optional[str]) -> bool:
    """
    بررسی تعلق یک رکورد حافظه به فضای موردنظر.
    اگر فضای هدف مشخص باشد، رکوردهای بدون مالک یا رکوردهای فضاهای دیگر هرگز تطابق داده نمی‌شوند.
    """
    if not target_scope:
        return False
    norm_target = normalize_scope_id(target_scope)
    if not norm_target:
        return False
    rec_scope = normalize_scope_id(rec.scope_id or rec.chat_id) if (rec.scope_id or rec.chat_id) else None
    if not rec_scope:
        return False
    return rec_scope == norm_target


def _is_same_scope(rec: MemoryRecord, target_scope: Optional[str]) -> bool:
    """بررسی تطابق دقیق محدوده در عملیات رفع تناقض و پیشگیری از تکرار."""
    if target_scope:
        return _matches_scope(rec, target_scope)
    return rec.scope_id is None and rec.chat_id is None


# =====================================================================
# 3. نرمال‌سازی فارسی و توکنایزر اختصاصی
# =====================================================================

_PERSIAN_STOPWORDS = {
    "از", "به", "با", "برای", "در", "تا", "که", "این", "آن", "ها", "های", "را",
    "رو", "شد", "شده", "است", "بود", "باشد", "می", "نمی", "یک", "یکی", "هم",
    "اما", "اگر", "ولی", "یا", "همان", "همین", "چون", "چه", "چرا", "چطور"
}

_PERSIAN_SUFFIXES = ("‌هایی", "‌های", "‌ها", "هایی", "های", "ها", "ترین", "تر", "مند", "سازی", "شده", "ان", "ات", "ی")
_PERSIAN_PREFIXES = ("می‌", "نمی‌", "بی‌")


def _norm_persian(text: str) -> str:
    """نرمال‌سازی حروف عربی/فارسی، حذف اعراب و یکپارچه‌سازی نیم‌فاصله‌ها."""
    if not text:
        return ""
    t = str(text)
    t = t.replace("ي", "ی").replace("ك", "ک").replace("ة", "ه").replace("ۀ", "ه")
    t = t.replace("\u200c", " ")  # تبدیل ZWNJ به فاصله برای تفکیک واژه‌ها
    t = re.sub(r"[\u064B-\u065F\u0670]", "", t)  # حذف تنوین و اعراب
    t = re.sub(r"[«»\"'،,.:؟?()\[\]\-_/\\|;!#*]", " ", t)
    return " ".join(t.split())


def _stem_persian(word: str) -> str:
    """ریشه‌یابی و حذف پیشوندها و پسوندهای رایج صرفی فارسی."""
    w = word.strip()
    if len(w) <= 3:
        return w
    for pfx in _PERSIAN_PREFIXES:
        if w.startswith(pfx):
            w = w[len(pfx):]
            break
    for sfx in _PERSIAN_SUFFIXES:
        if w.endswith(sfx) and len(w) - len(sfx) >= 3:
            w = w[:-len(sfx)]
            break
    return w


def _tokens(s: str) -> List[str]:
    """توکنایزر بهینه‌شده برای جستجو و همپوشانی کلمات."""
    norm = _norm_persian(s)
    toks = []
    for w in norm.split():
        w_low = w.lower()
        if len(w_low) >= 3 and w_low not in _PERSIAN_STOPWORDS:
            toks.append(_stem_persian(w_low))
    return toks


def _norm_fact(s: str) -> str:
    return _norm_persian(s)


def _jaccard(toks1: Set[str], toks2: Set[str]) -> float:
    """محاسبه ضریب شباهت ژاکارد میان دو مجموعه توکن."""
    if not toks1 or not toks2:
        return 0.0
    inter = len(toks1 & toks2)
    union = len(toks1 | toks2)
    return inter / union if union > 0 else 0.0


def _similarity(qtoks, ftoks) -> int:
    """محاسبه امتیاز همپوشانی کلمات با وزن پیشوند/ریشه."""
    s = 0
    for q in qtoks:
        for w in ftoks:
            if q == w:
                s += 2
            elif (len(q) >= 4 and w.startswith(q)) or (len(w) >= 4 and q.startswith(w)):
                s += 1
    return s


def _estimate_tokens(text: str) -> int:
    """تخمین تعداد توکن‌های یک متن."""
    if not text:
        return 0
    return max(1, len(text) // 4)


# =====================================================================
# 4. بارگذاری و ذخیره‌سازی داده‌ها (Data Persistence & Atomicity)
# =====================================================================

def _load() -> dict:
    with _MEMORY_LOCK:
        try:
            with open(MEMORY_FILE, encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    return {"facts": [], "history": {}, "summaries": {}}
                data.setdefault("facts", [])
                data.setdefault("history", {})
                data.setdefault("summaries", {})
                return data
        except Exception:
            return {"facts": [], "history": {}, "summaries": {}}


def _save(data: dict) -> None:
    with _MEMORY_LOCK:
        from core import fsutil
        fsutil.atomic_write_json(MEMORY_FILE, data)


def _get_records() -> List[MemoryRecord]:
    """خواندن تمام رکوردهای حافظه و ارتقای داده‌های قدیمی به MemoryRecord."""
    raw_facts = _load().get("facts", [])
    records = []
    for item in raw_facts:
        rec = MemoryRecord.from_dict(item)
        records.append(rec)
    return records


# =====================================================================
# 5. حافظه بلندمدت با تفکیک قطعی فضا (Scoped Long-Term Engine)
# =====================================================================

def add_memory(
    fact: str,
    category: Optional[str] = None,
    importance: int = 3,
    confidence: float = 1.0,
    source: str = "user",
    chat_id: Optional[Any] = None,
    scope_id: Optional[Any] = None
) -> str:
    """
    ثبت رکورد در حافظه بلندمدت با تفکیک ۱۰۰٪ مستقل بر مبنای فضای حافظه (Scope).
    پیشگیری از تکرار و رفع تناقض فقط در محدوده همان گفتگو اعمال می‌شود.
    """
    clean_fact = _sanitize_fact(fact)
    if not clean_fact:
        return ""

    resolved_scope = normalize_scope_id(scope_id or chat_id) if (scope_id or chat_id) else None

    with _MEMORY_LOCK:
        data = _load()
        raw_facts = data.setdefault("facts", [])
        records = [MemoryRecord.from_dict(item) for item in raw_facts]

        new_toks = set(_tokens(clean_fact))
        cat = category or MemoryRecord._infer_category(clean_fact)
        now = int(time.time())

        # ۱. بررسی تکرار دقیق یا شباهت بسیار بالا (Deduplication) - منحصراً در همان فضای حافظه
        for rec in records:
            if rec.status != "active":
                continue
            if not _is_same_scope(rec, resolved_scope):
                continue

            if _norm_fact(rec.content) == _norm_fact(clean_fact):
                rec.updated_at = now
                rec.importance = max(rec.importance, importance)
                rec.confidence = max(rec.confidence, confidence)
                _persist_records(data, records)
                return rec.id
            if new_toks and _jaccard(new_toks, set(_tokens(rec.content))) >= 0.8:
                rec.updated_at = now
                rec.importance = max(rec.importance, importance)
                _persist_records(data, records)
                return rec.id

        # ۲. تشخیص و رفع تناقض (Conflict Resolution) - منحصراً در همان فضای حافظه
        for rec in records:
            if rec.status != "active":
                continue
            if not _is_same_scope(rec, resolved_scope):
                continue

            rec_toks = set(_tokens(rec.content))
            if not new_toks or not rec_toks:
                continue
            sim = _jaccard(new_toks, rec_toks)
            overlap_ratio = len(new_toks & rec_toks) / min(len(new_toks), len(rec_toks))
            is_same_subject = (sim >= 0.35 or overlap_ratio >= 0.5)
            is_dynamic_cat = (rec.category in ("decision", "preference", "project") or cat in ("decision", "preference", "project"))
            if is_same_subject and is_dynamic_cat:
                log.info("Memory conflict resolved in scope %s: Superseding %s with newer record (cat: %s)", resolved_scope, rec.id, cat)
                rec.status = "superseded"
                rec.updated_at = now

        # ۳. ثبت رکورد جدید با الصاق دقیق شناسه فضا
        rec_id = f"mem_{now}_{abs(hash(clean_fact)) % 100000}"
        new_record = MemoryRecord(
            id=rec_id,
            content=clean_fact,
            category=cat,
            importance=max(1, min(5, importance)),
            confidence=max(0.1, min(1.0, confidence)),
            created_at=now,
            updated_at=now,
            source=source,
            chat_id=str(chat_id) if chat_id else None,
            status="active",
            scope_id=resolved_scope
        )
        records.append(new_record)
        _persist_records(data, records)
        return rec_id


def _persist_records(data: dict, records: List[MemoryRecord]) -> None:
    """ذخیره رکوردها در فایل با حفظ حداکثر تعداد رکوردهای فعال."""
    active = [r for r in records if r.status == "active"]
    inactive = [r for r in records if r.status != "active"]

    if len(active) > MAX_FACTS:
        active.sort(key=lambda r: (r.importance, r.updated_at), reverse=True)
        active = active[:MAX_FACTS]

    final_records = active + inactive[-50:]
    data["facts"] = [r.to_dict() for r in final_records]
    _save(data)


def _sanitize_fact(text: str) -> str:
    """پالایش واقعیت و رد عبارات بی‌ارزش یا خیلی کوتاه."""
    if not text:
        return ""
    t = str(text).strip()
    t = "".join(ch for ch in t if ch in ("\n", " ") or (ord(ch) >= 32 and ord(ch) != 0x7F))
    t = " ".join(t.split())
    if len(t) < 4:
        return ""
    trivial = {"سلام", "خوبی", "چطوری", "مرسی", "ممنون", "ok", "باشه"}
    if t.lower() in trivial:
        return ""
    return t


def remove_memory(keyword: str, scope_id: Optional[Any] = None, chat_id: Optional[Any] = None) -> List[str]:
    """حذف/آرشیو واقعیت‌های مرتبط با کلمه کلیدی، منحصراً در فضای حافظه مشخص‌شده."""
    target_scope = normalize_scope_id(scope_id or chat_id) if (scope_id or chat_id) else None
    with _MEMORY_LOCK:
        data = _load()
        records = [MemoryRecord.from_dict(item) for item in data.get("facts", [])]
        qtoks = _tokens(keyword)
        if not qtoks:
            return []

        removed, keep = [], []
        for r in records:
            if r.status != "active":
                keep.append(r)
                continue

            # فیلتر اجباری محدوده دسترسی
            if target_scope:
                if not _matches_scope(r, target_scope):
                    keep.append(r)
                    continue
            else:
                # اگر فضایی مشخص نشده باشد، فقط رکوردهای قدیمی بدون مالک مشمول می‌شوند
                if r.scope_id is not None or r.chat_id is not None:
                    keep.append(r)
                    continue

            ftoks = _tokens(r.content)
            hit = any(q == w or (len(q) >= 4 and w.startswith(q)) or (len(w) >= 4 and q.startswith(w))
                      for q in qtoks for w in ftoks)
            if hit:
                r.status = "archived"
                r.updated_at = int(time.time())
                removed.append(r.content)
                keep.append(r)
            else:
                keep.append(r)

        if removed:
            _persist_records(data, keep)
        return removed


def clear_memory(scope_id: Optional[Any] = None, chat_id: Optional[Any] = None, all_scopes: bool = False) -> None:
    """
    پاکسازی حافظه ماندگار:
    - اگر scope_id یا chat_id مشخص شود، فقط حافظه همان گفتگو پاک می‌شود و گفتگوهای دیگر مصون می‌مانند.
    - اگر all_scopes=True باشد یا هیچ شناسه‌ای داده نشود، کل حافظه پاکسازی می‌شود (مخصوص Fixtureهای تست).
    """
    target_scope = normalize_scope_id(scope_id or chat_id) if (scope_id or chat_id) else None
    with _MEMORY_LOCK:
        data = _load()
        if all_scopes or (target_scope is None and scope_id is None and chat_id is None):
            data["facts"] = []
            _save(data)
            return

        records = [MemoryRecord.from_dict(item) for item in data.get("facts", [])]
        kept = [r for r in records if not _matches_scope(r, target_scope)]
        data["facts"] = [r.to_dict() for r in kept]
        _save(data)


def list_facts(scope_id: Optional[Any] = None, chat_id: Optional[Any] = None) -> List[str]:
    """برگرداندن لیست حقایق و تصمیمات فعال متعلق به فضای مشخص‌شده."""
    target_scope = normalize_scope_id(scope_id or chat_id) if (scope_id or chat_id) else None
    records = _get_records()
    matched = []
    for r in records:
        if r.status == "active" and r.category != "interaction":
            if target_scope:
                if _matches_scope(r, target_scope):
                    matched.append(r.content)
            else:
                if r.scope_id is None and r.chat_id is None:
                    matched.append(r.content)
    return matched


def load_memory(scope_id: Optional[Any] = None, chat_id: Optional[Any] = None) -> str:
    """نمایش تمامی حقایق فعال متعلق به فضای مشخص‌شده جهت تزریق به پرامپت یا گزارش."""
    facts = list_facts(scope_id=scope_id, chat_id=chat_id)
    return "\n".join(f"- {f}" for f in facts)


def get_recent_interactions(
    chat_id: Optional[Any] = None,
    limit: int = 3,
    scope_id: Optional[Any] = None
) -> List[Dict[str, Any]]:
    """دریافت سوابق تعاملی فعال یا ترمیم‌شده منحصراً برای فضای گفتگو مشخص‌شده."""
    target_scope = normalize_scope_id(scope_id or chat_id) if (scope_id or chat_id) else None
    records = _get_records()
    items = []
    for r in records:
        if r.category == "interaction" and r.status in ("active", "repaired"):
            if target_scope is not None:
                if _matches_scope(r, target_scope):
                    items.append(r)
            else:
                if r.scope_id is None and r.chat_id is None:
                    items.append(r)
    items.sort(key=lambda r: r.created_at, reverse=True)
    return [r.to_dict() for r in items[:limit]]


# =====================================================================
# 6. بازیابی هوشمند حافظه با فیلتر لایه دسترسی (Scoped Retrieval)
# =====================================================================

def retrieve_relevant_memories(
    query: str,
    chat_id: Optional[Any] = None,
    limit: int = 6,
    min_score: float = 0.1,
    include_interactions: bool = False,
    scope_id: Optional[Any] = None
) -> List[Dict[str, Any]]:
    """
    بازیابی هوشمند و رتبه‌بندی حافظه با اعمال فیلتر قطعی فضا در لایه دسترسی داده‌ها.
    رکوردهای فضاهای دیگر پیش از هرگونه تحلیل متنی یا معنایی حذف می‌شوند.
    """
    records = _get_records()
    target_scope = normalize_scope_id(scope_id or chat_id) if (scope_id or chat_id) else None

    # فیلتر اجباری فضا در لایه داده‌ها
    active_records = []
    for r in records:
        if r.status != "active":
            continue
        if not include_interactions and r.category == "interaction":
            continue

        if target_scope:
            if _matches_scope(r, target_scope):
                active_records.append(r)
        else:
            # جستجو بدون فضا فقط رکوردهای بدون مالک را برمی‌گرداند
            if r.scope_id is None and r.chat_id is None:
                active_records.append(r)

    if not active_records:
        return []

    qtoks = set(_tokens(query or ""))
    query_norm = _norm_persian(query or "").lower()
    now = int(time.time())

    is_referring_past = any(w in query_norm for w in ("همون", "دفعه قبل", "کار قبلی", "دیروز", "تصمیم", "پروژه", "قبلاً"))

    scored: List[Tuple[MemoryRecord, float]] = []

    for r in active_records:
        rtoks = set(_tokens(r.content))
        sim_score = _similarity(qtoks, rtoks) if qtoks else 0
        jacc = _jaccard(qtoks, rtoks) if qtoks else 0.0

        importance_multiplier = 1.0 + (r.importance - 1) * 0.25
        days_ago = max(0.0, (now - r.updated_at) / 86400.0)
        recency_factor = 1.0 / (1.0 + (days_ago * 0.05))

        cat_boost = 1.0
        if is_referring_past and r.category in ("decision", "project", "preference"):
            cat_boost = 1.5

        base_score = (sim_score * 1.5) + (jacc * 3.0)
        if not qtoks:
            total_score = r.importance * recency_factor
        else:
            total_score = (base_score * importance_multiplier * recency_factor * cat_boost)

        if total_score >= min_score or not qtoks:
            scored.append((r, total_score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return [rec.to_dict() for rec, score in scored[:limit] if score > 0]


def relevant_facts(
    question: str,
    chat_id: Optional[Any] = None,
    limit: int = 8,
    scope_id: Optional[Any] = None
) -> str:
    """
    برگرداندن حقایق مرتبط با سوال، منحصراً از همان فضای گفتگو.
    در صورت نبود حافظه مرتبط در این فضا، هیچ‌گونه اطلاعات ساختگی یا متعلق به فضاهای دیگر تولید نمی‌شود.
    """
    target_scope = normalize_scope_id(scope_id or chat_id) if (scope_id or chat_id) else None
    matched = retrieve_relevant_memories(question, scope_id=target_scope, limit=limit, min_score=0.1)
    if not matched:
        records = _get_records()
        same_scope_active = []
        for r in records:
            if r.status == "active" and r.category != "interaction":
                if target_scope:
                    if _matches_scope(r, target_scope):
                        same_scope_active.append(r)
                else:
                    if r.scope_id is None and r.chat_id is None:
                        same_scope_active.append(r)
        if not same_scope_active:
            return ""
        same_scope_active.sort(key=lambda r: (r.importance, r.updated_at), reverse=True)
        return "\n".join(f"- {r.content}" for r in same_scope_active[:limit])

    return "\n".join(f"- {item['content']}" for item in matched)


# =====================================================================
# 7. انتقال صریح و کنترل‌شده حافظه میان فضاها (Explicit Transfer)
# =====================================================================

def transfer_memory(
    fact_id_or_keyword: str,
    source_scope_id: str,
    target_scope_id: str,
    is_authorized: bool = False
) -> Optional[MemoryRecord]:
    """
    انتقال صریح و گزینشی یک واقعیت از یک فضا به فضای دیگر:
    - فقط با درخواست صریح و احراز مجوز معتبر انجام می‌شود.
    - فقط داده انتخاب‌شده کپی می‌شود و دو فضا هرگز ادغام دائمی نمی‌شوند.
    """
    if not is_authorized:
        log.warning("Unauthorized memory transfer attempt from %s to %s", source_scope_id, target_scope_id)
        return None

    src = normalize_scope_id(source_scope_id)
    dst = normalize_scope_id(target_scope_id)
    if not src or not dst or src == dst:
        return None

    records = _get_records()
    target_rec: Optional[MemoryRecord] = None

    for r in records:
        if r.status == "active" and _matches_scope(r, src):
            if r.id == fact_id_or_keyword or fact_id_or_keyword in r.content:
                target_rec = r
                break

    if not target_rec:
        return None

    # ثبت به عنوان رکورد جدید در فضای مقصد با حفظ محتوا
    new_id = add_memory(
        fact=target_rec.content,
        category=target_rec.category,
        importance=target_rec.importance,
        confidence=target_rec.confidence,
        source=f"transferred_from_{src}",
        scope_id=dst
    )
    if new_id:
        log.info("Explicit memory transfer: Fact %s transferred from %s to %s", target_rec.id, src, dst)
        return MemoryRecord(
            id=new_id,
            content=target_rec.content,
            category=target_rec.category,
            importance=target_rec.importance,
            confidence=target_rec.confidence,
            scope_id=dst
        )
    return None


# =====================================================================
# 8. حافظه کوتاه‌مدت با تفکیک قطعی فضا (Scoped ConversationBuffer)
# =====================================================================

class ConversationBuffer:
    """
    مدیریت پنجره کانتکست و خلاصه گفتگوها با تفکیک ۱۰۰٪ مستقل بر مبنای فضای حافظه (Scope):
    - خلاصه گروه A هرگز وارد پنجره گروه B یا پیوی نمی‌شود.
    - بودجه توکن برای هر گفتگو مستقل است.
    """

    @classmethod
    def get_context(cls, scope_or_chat_id: Any, max_tokens: int = MAX_SHORT_TERM_TOKENS) -> str:
        key = normalize_scope_id(scope_or_chat_id)
        if not key:
            return ""

        with _MEMORY_LOCK:
            data = _load()
            hist = data.get("history", {}).get(key, [])
            summary = data.get("summaries", {}).get(key, "")

            if not hist and not summary:
                return ""

            lines = []
            if summary:
                lines.append(f"📌 [خلاصه گفتگوهای پیشین این گفتگو]:\n{summary}\n")

            recent_lines = []
            token_count = _estimate_tokens(summary)

            for entry in reversed(hist):
                u_text = entry.get("user", "")
                b_text = entry.get("bot", "")
                bot_name = config.ASSISTANT_NAMES[0] if getattr(config, "ASSISTANT_NAMES", None) else "کاپری"
                turn_str = f"کاربر: {u_text}\n{bot_name}: {b_text}"
                turn_tokens = _estimate_tokens(turn_str)
                if token_count + turn_tokens > max_tokens and recent_lines:
                    break
                recent_lines.append(turn_str)
                token_count += turn_tokens

            recent_lines.reverse()
            lines.extend(recent_lines)
            return "\n".join(lines).strip()

    @classmethod
    def add_exchange(cls, scope_or_chat_id: Any, user_msg: str, bot_reply: str) -> None:
        if not user_msg and not bot_reply:
            return
        key = normalize_scope_id(scope_or_chat_id)
        if not key:
            return

        with _MEMORY_LOCK:
            data = _load()
            hist = data.setdefault("history", {}).setdefault(key, [])
            summaries = data.setdefault("summaries", {})

            hist.append({
                "user": user_msg[:600].strip(),
                "bot": bot_reply[:600].strip(),
                "ts": int(time.time())
            })

            if len(hist) > 20:
                to_summarize = hist[:-10]
                kept = hist[-10:]
                old_summary = summaries.get(key, "")
                new_digest = cls._create_local_digest(to_summarize, old_summary)
                summaries[key] = new_digest
                data["history"][key] = kept
            else:
                data["history"][key] = hist[-MAX_HISTORY:]

            _save(data)

    @classmethod
    def _create_local_digest(cls, exchanges: List[Dict[str, Any]], existing_summary: str) -> str:
        """خلاصه‌سازی فشرده محلی بدون ایجاد وابستگی خارجی مسدودکننده."""
        topics = []
        for e in exchanges:
            u = e.get("user", "")
            if len(u) > 10:
                first_part = u.split("،")[0].split(".")[0][:60]
                topics.append(first_part)
        digest = "؛ ".join(topics[-4:])
        if existing_summary:
            return f"{existing_summary} | بحث‌های بعد: {digest}"[:400]
        return f"موضوعات مطرح‌شده: {digest}"[:300]


def remember_exchange(chat_id: Any, user_msg: str, bot_reply: str, scope_id: Optional[Any] = None) -> None:
    """ثبت تبادل گفتگو در حافظه کوتاه‌مدت با تفکیک فضای گفتگو."""
    target = scope_id or chat_id
    ConversationBuffer.add_exchange(target, user_msg, bot_reply)


def load_history(chat_id: Any, scope_id: Optional[Any] = None) -> str:
    """خواندن تاریخچه مکالمات و خلاصه مختص فضای گفتگو."""
    target = scope_id or chat_id
    return ConversationBuffer.get_context(target, max_tokens=MAX_SHORT_TERM_TOKENS)


def clear_history(chat_id: Optional[Any] = None, scope_id: Optional[Any] = None) -> None:
    """پاکسازی تاریخچه گفتگوها برای فضای مشخص یا تمام فضاها."""
    target = scope_id or chat_id
    with _MEMORY_LOCK:
        data = _load()
        if target is not None:
            key = normalize_scope_id(target)
            data.get("history", {}).pop(key, None)
            data.get("summaries", {}).pop(key, None)
        else:
            data["history"] = {}
            data["summaries"] = {}
        _save(data)


# =====================================================================
# 9. سازگاری و مهاجرت داده‌های قدیمی (Backward Compatibility & Safe Migration)
# =====================================================================

def migrate_legacy_memory() -> Dict[str, int]:
    """
    مهاجرت امن و برگشت‌پذیر رکوردهای قدیمی به ساختار جدید بر اساس scope_id:
    - ایجاد نسخه پشتیبان پیش از اعمال تغییرات.
    - اگر chat_id وجود داشته باشد، به scope_id متناظر نرمال‌سازی می‌شود.
    - رکوردهای قدیمی بدون مالکیت مشخص هرگز به حافظه عمومی تبدیل نمی‌شوند.
    """
    with _MEMORY_LOCK:
        data = _load()
        os.makedirs(os.path.dirname(BACKUP_FILE), exist_ok=True)
        try:
            with open(BACKUP_FILE, "w", encoding="utf-8") as bf:
                json.dump(data, bf, ensure_ascii=False, indent=2)
        except Exception as e:
            log.warning("Memory backup creation warning: %s", e)

        raw_facts = data.get("facts", [])
        migrated_facts = 0
        unscoped_facts = 0

        updated_facts = []
        for item in raw_facts:
            rec = MemoryRecord.from_dict(item)
            if rec.scope_id:
                migrated_facts += 1
            else:
                unscoped_facts += 1
            updated_facts.append(rec.to_dict())

        # مهاجرت کلیدهای تاریخچه
        history = data.get("history", {})
        new_history = {}
        for k, v in history.items():
            norm_k = normalize_scope_id(k)
            new_history[norm_k] = v

        summaries = data.get("summaries", {})
        new_summaries = {}
        for k, v in summaries.items():
            norm_k = normalize_scope_id(k)
            new_summaries[norm_k] = v

        data["facts"] = updated_facts
        data["history"] = new_history
        data["summaries"] = new_summaries
        _save(data)

        return {
            "total_facts": len(updated_facts),
            "migrated_facts": migrated_facts,
            "unscoped_facts": unscoped_facts,
            "history_scopes": len(new_history)
        }
