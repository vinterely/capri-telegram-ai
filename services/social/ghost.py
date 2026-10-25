"""حالت همزاد (Ghost Mode): کاپری به‌جای مالک در پیوی جواب می‌دهد.

فقط مالک با «کاپری مثل من شو» فعالش می‌کند و با «کاپری برگرد به حالت عادی»
غیرفعال. وقتی فعال است، پیام‌های خصوصی ورودی کاربرانِ مجاز (allow-list) را
به‌جای خودِ مالک، با سبک و امضای کلامی او پاسخ می‌دهد.
"""
import asyncio
import json
import os
import re
import time

from ai_engine import ai
from core import config
from core import fsutil

FILE = os.path.join(config.BASE_DIR, "ghost.json")

# کول‌داون هر چت برای جلوگیری از اسپم/بن (ثانیه)
COOLDOWN_SEC = 15
_cooldown = {}

REDLINE_KEYWORDS = (
    "کارت به کارت", "کارت‌به‌کارت", "شماره کارت", "شماره شبا", "شبا", "رمز",
    "پسورد", "رمز عبور", "رمز ورود", "پول", "قرض", "وام", "حساب بانکی",
    "حسابم", "پرداخت", "واریز", "انتقال پول", "بیعانه", "پیش‌پرداخت",
    "قرارداد", "امضا", "سند", "تعهد", "شکایت", "شاکی", "دادگاه", "پلیس",
    "تهدید", "دعوا", "بدهی", "طلبکار", "سفته", "چک",
)

# عبارت انحرافی که به‌جای پاسخ حساس داده می‌شود
DEFLECT_REPLY = "الان دستم بنده، سر فرصت بهت زنگ می‌زنم 🙂"


def load() -> dict:
    try:
        with open(FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save(data: dict) -> None:
    fsutil.atomic_write_json(FILE, data)


def is_active() -> bool:
    return bool(load().get("active"))


def get_persona() -> str:
    return load().get("persona", "")


def activate(persona: str) -> None:
    save({"active": True, "persona": persona, "updated": time.time()})


def deactivate() -> None:
    d = load()
    d["active"] = False
    save(d)


_PERSONA_PROMPT = (
    "تو یک موتور فوق‌تخصصی روان‌شناسی زبان و کالبدشکافی سبک نوشتار هستی. "
    "وظیفه تو این است که پیام‌های ارسالی صاحب اکانت را در چت‌های اخیرش تحلیل کنی و "
    "«امضای رفتاری و کلامی» او را دقیقاً در این ۶ فاکتور استخراج کنی:\n"
    "۱. تکیه‌کلام‌ها و اصطلاحات رایج (مثلاً: چاکرم، داداش، فدات، حاجی، دمت گرم، اوکیه، مخلص) — با ذکر مثال واقعی از خود پیام‌ها.\n"
    "۲. ساختار جملات (کوتاه و تلگرامی می‌نویسد یا بلند؟ جملات تک‌کلمه‌ای می‌فرستد؟ چند پیام کوتاه پشت سر هم؟).\n"
    "۳. نحوه سلام و احوال‌پرسی (خشک و رسمی یا صمیمی و خودمانی؟ چه عبارت‌هایی برای سلام/خداحافظی دارد؟).\n"
    "۴. نحوه استفاده از علائم نگارشی و اموجی‌ها (چقدر اموجی؟ اموجی‌های پرتکرارش کدامند؟ نقطه و علامت سوال می‌گذارد یا نه؟).\n"
    "۵. غلط‌های املایی عمدی یا فرم محاوره‌ای (مثلاً «میرم» یا «می‌رم»؟ «باشه» یا «باش»؟ «خوبی» یا «خبی»؟) — دقیق مشخص کن کدام فرم را به کار می‌برد.\n"
    "۶. حس و انرژی کلی (خونسرد، شوخ‌طبع، پرانرژی، یا سریع و گزیده‌گو؟).\n\n"
    "خروجی باید یک پروفایل سبکِ فشرده، شفاف و قابل‌استفاده در پرامپت بعدی باشد؛ "
    "برای هر فاکتور یک یا دو خط مشخص بنویس و حتماً مثال واقعی از پیام‌ها بیاور. "
    "فقط خود پروفایل را بنویس؛ بدون مقدمه، توضیح اضافه یا عنوان کلی."
)


def _is_command_to_bot(text: str) -> bool:
    t = (text or "").strip()
    for name in config.ASSISTANT_NAMES:
        if name and name in t:
            return True
    return False


async def collect_samples(client, limit: int = 60) -> list:
    """نمونه‌ی پیام‌های ارسالی اخیر مالک از دیالوگ‌های اخیر (بدون دستور به خود بات)."""
    samples = []
    seen = set()
    async for d in client.iter_dialogs(limit=60):
        try:
            async for m in client.iter_messages(d.id, limit=15):
                text = (m.text or "").strip()
                if not m.out or not text:
                    continue
                # پیام‌های ویرایش‌شده خوانده نشوند (چون توسط بات ویرایش شده‌اند)
                if getattr(m, "edit_date", None) is not None:
                    continue
                if _is_command_to_bot(text):
                    continue
                if len(text) < 2 or len(text) > 400:
                    continue
                if text in seen:
                    continue
                seen.add(text)
                samples.append(text)
                if len(samples) >= limit:
                    return samples
        except Exception:
            continue
    return samples


async def extract_persona(client) -> str:
    """جمع‌آوری نمونه‌ها و استخراج پروفایل ۶ فاکتوری با جمینای."""
    samples = await collect_samples(client)
    if len(samples) < 5:
        return ""
    corpus = "\n".join(f"- {s}" for s in samples)
    prompt = _PERSONA_PROMPT + "\n\nپیام‌های نمونه (به ترتیب زمانی):\n" + corpus
    raw = await asyncio.to_thread(ai._gemini, prompt)
    if raw:
        return raw.strip()
    return ""


def _norm(s: str) -> str:
    return re.sub(r"[\u200c\u200f\u200e]", "", (s or "").replace("ي", "ی").replace("ك", "ک"))


def is_redline(text: str) -> bool:
    t = _norm(text)
    return any(k in t for k in REDLINE_KEYWORDS)


_GHOST_SYSTEM = (
    "# ماموریت حیاتی: تو خودِ {owner} هستی!\n"
    "از این لحظه، تو یک دستیار هوش مصنوعی نیستی؛ تو دقیقاً خودِ {owner} هستی که داری "
    "با گوشی شخصی‌ات در تلگرام به مخاطبت پیام می‌دهی.\n\n"
    "### 🎭 پروفایل و امضای لحن تو:\n{persona}\n"
    "(دقیقاً طبق الگوها، تکیه‌کلام‌ها و عادات نگارشی بالا پاسخ بده).\n\n"
    "### ⛔ قوانین بقا و مخفی‌کاری:\n"
    "۱. هرگز و تحت هیچ شرایطی نگو «من هوش مصنوعی هستم»، «من کاپری هستم»، «من دستیار هستم» "
    "یا «چطور می‌توانم کمکتان کنم؟». حتی اگر طرف شک کرد و پرسید «رباتی؟»، با خنده و به زبان "
    "خودمانی بگو «دیوونه شدی؟ خواب دیدی خیر باشه» یا «چی زدی داداش؟!».\n"
    "۲. طول پیام‌ها: آدم‌ها در چت تلگرام پاراگراف دانشگاهی نمی‌نویسند! پاسخ‌های تو باید "
    "۱ الی ۲ خط، بسیار طبیعی، سریع و تلگرامی باشند.\n"
    "۳. تطبیق صمیمیت: لحنت با دوستان صمیمی باید گرم، خودمانی و پر از اصطلاحات تلگرامی باشد؛ "
    "با افراد غریبه یا کاری، محترمانه ولی همچنان انسانی و طبیعی.\n"
    "۴. تکنیک جاخالی دادن طبیعی: اگر طرف سوالی پرسید که تو اطلاعاتش را نداری (مثلاً «فلان فایل "
    "رو به کی دادی؟» یا «فردا ساعت چند بریم؟»)، هرگز نگو «من نمی‌دانم»؛ خیلی طبیعی مثل یک آدم "
    "سرشلوغ بگو «الان بیرون درگیرم، رسیدم خونه چکش می‌کنم بهت میگم» یا «الان یادم نیست دقیق، "
    "شب پیام بده هماهنگ کنیم».\n\n"
    "### 🚨 خطوط قرمز امنیتی (سوپاپ اطمینان):\n"
    "اگر پیام طرف مربوط به هر یک از موارد زیر بود: مسائل مالی (کارت به کارت، رمز، حساب بانکی، "
    "پول قرض)، تعهدات کاری یا حقوقی سنگین، دعوا و تنش شدید احساسی، یا اعترافات شخصی حساس — "
    "هیچ پاسخ واقعی نده و فقط و فقط بنویس: REDLINE\n\n"
    "### 📝 خروجی:\n"
    "فقط و فقط متن خود پیام نهایی (۱ تا ۲ خط) را بنویس؛ بدون مقدمه، توضیح، نقل‌قول، ایموجی اضافه یا عنوان."
)


async def reply_as_owner(event, client) -> bool:
    """پاسخ به‌جای مالک به یک پیام خصوصی ورودی. True یعنی پیام مدیریت شد."""
    chat_id = event.chat_id
    now = time.time()
    if now - _cooldown.get(chat_id, 0) < COOLDOWN_SEC:
        return True

    try:
        sender = await event.get_sender()
    except Exception:
        sender = None
    if sender is not None and getattr(sender, "bot", False):
        return False

    name = (getattr(sender, "first_name", "") or "مخاطب").strip()
    username = getattr(sender, "username", "") or ""
    incoming = (event.raw_text or "").strip()

    history = ""
    try:
        hist_msgs = []
        async for m in client.iter_messages(chat_id, limit=6):
            if m.id == event.id or not m.text:
                continue
            who = "تو" if m.out else name
            hist_msgs.append(f"{who}: {m.text.strip()}")
        history = "\n".join(reversed(hist_msgs))
    except Exception:
        history = ""

    # ۱) تشخیص قطعی با کلیدواژه (سریع و بدون خطا)
    if is_redline(incoming):
        await _report_redline(client, name, username, incoming, "کلیدواژه")
        await _safe_send(client, chat_id, DEFLECT_REPLY)
        _cooldown[chat_id] = now
        return True

    # ۲) تشخیص ترکیبی با مدل (نشانه‌ی REDLINE در پاسخ)
    system = _GHOST_SYSTEM.replace("{owner}", config.OWNER_NAME).replace("{persona}", get_persona())
    prompt = (
        f"{system}\n\n"
        f"[اطلاعات وضعیت چت]\n- طرف مقابل: {name}" + (f" (@{username})" if username else "") + "\n"
        f"- پیام‌های اخیر گفتگو:\n{history or '—'}\n\n"
        f'پیام جدید او: "{incoming}"\n\n'
        f"دستور: به عنوان خودِ {config.OWNER_NAME}، پاسخ بعدی را دقیقاً در ۱ تا ۲ خط بنویس."
    )
    raw = await asyncio.to_thread(ai._gemini, prompt)
    if not raw:
        return False
    raw = raw.strip().strip("«»\"'")

    if raw.upper().startswith("REDLINE"):
        await _report_redline(client, name, username, incoming, "مدل")
        await _safe_send(client, chat_id, DEFLECT_REPLY)
        _cooldown[chat_id] = now
        return True

    await _safe_send(client, chat_id, raw)
    _cooldown[chat_id] = now
    if len(_cooldown) > 500:
        _prune_cooldown()
    return True


async def _safe_send(client, chat_id, text: str) -> None:
    try:
        await client.send_message(chat_id, text)
    except Exception:
        pass


async def _report_redline(client, name, username, incoming, source) -> None:
    line = f"🚨 هشدار همزاد ({source}) — پیام حساس از {name}"
    if username:
        line += f" (@{username})"
    line += f":\n\n{incoming}"
    try:
        await client.send_message("me", line)
    except Exception:
        pass


def _prune_cooldown() -> None:
    now = time.time()
    stale = [k for k, ts in _cooldown.items() if now - ts > 3600]
    for k in stale:
        _cooldown.pop(k, None)
