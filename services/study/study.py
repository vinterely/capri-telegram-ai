"""همیار درسی و تحلیلگر کد: کالبدشکافی اسناد آموزشی و فایل‌های کد.

فرمت‌های سند: PDF, DOCX, PPTX, TXT, MD + فایل‌های کد (py, js, cpp, ...).

دو حالت دارد:
  ۱) بررسی کلی فایل (بدون سوال مشخص) → گزارش ساخت‌یافته (نقشه راه، مفاهیم کلیدی،
     پیش‌بینی سوالات امتحانی، دام‌های امتحانی / برای کد: نمای کلی، تحلیل، باگ، بهبود).
  ۲) سوال مشخص روی فایل → پاسخ ساخت‌یافته ۳ بخشی با ارجاع.

PDF با Gemini File API مستقیماً خوانده می‌شود (حتی اسکن‌شده/کم‌اسکنر که لایه‌ی
متن ندارد و pypdf نمی‌تواند بخواند). DOCX/PPTX با کتابخانه استاندارد zipfile/xml
و کد/TXT/MD به‌صورت متن خام استخراج می‌شوند.
"""
import logging
import os
import re
import zipfile
import xml.etree.ElementTree as ET

from telethon import types

from ai_engine import ai

log = logging.getLogger("study")

DOC_EXTS = {".pdf", ".docx", ".pptx", ".txt", ".md", ".markdown"}

CODE_EXTS = {
    ".py", ".pyw", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".vue", ".svelte",
    ".cpp", ".cc", ".cxx", ".c", ".h", ".hpp", ".hh", ".cs", ".java", ".go", ".rs",
    ".rb", ".php", ".swift", ".kt", ".kts", ".dart", ".lua", ".r", ".m", ".pl",
    ".ex", ".exs", ".fs", ".fsx", ".scala", ".clj", ".groovy", ".gradle",
    ".sh", ".bash", ".zsh", ".ps1", ".bat", ".cmd",
    ".sql", ".html", ".htm", ".css", ".scss", ".sass", ".less",
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf", ".xml", ".ipynb",
}

SUPPORTED_EXTS = DOC_EXTS | CODE_EXTS

MAX_CHARS = 120000

_DOCX_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_PPTX_NS = "{http://schemas.openxmlformats.org/drawingml/2006/main}"

_REVIEW_PHRASES = (
    "این فایل رو بررسی کن", "این فایل را بررسی کن", "این فایلو بررسی کن",
    "این فایل رو بررسی", "این فایل را بررسی", "فایل رو بررسی کن", "فایل را بررسی کن",
    "این جزوه رو بررسی کن", "این جزوه را بررسی کن", "این جزوه رو بررسی", "این جزوه را بررسی",
    "جزوه رو بررسی کن", "جزوه را بررسی کن", "جزوه رو بررسی", "جزوه را بررسی",
    "این کد رو بررسی کن", "این کد را بررسی کن", "کد رو بررسی کن", "کد را بررسی کن",
    "اسلایدها رو بررسی کن", "اسلایدها را بررسی کن", "این اسلایدها رو بررسی", "این اسلایدها را بررسی",
    "بررسی کن", "بررسیش کن", "بررسی کنید", "بررسی", "کالبدشکافی کن", "کالبدشکافی",
    "تحلیل کن این فایل", "تحلیل کن این جزوه", "تحلیلش کن", "تحلیل کن", "تحلیل بده",
    "خلاصه ش کن", "خلاصه‌ش کن", "خلاصه‌اش کن", "خلاصه کن", "خلاصه اش کن",
    "جمع بندی کن", "جمع‌بندی کن", "جمع بندی", "جمع‌بندی", "چکیده کن", "چکیده",
)

_DOC_PREFIX_RE = re.compile(
    r"^\s*(?:(?:طبق|بر\s*اساس|براساس|بر\s*طبق|برطبق|با\s*توجه\s*به|باتوجه\s*به)\s+)?"
    r"(?:این|همین)?\s*(?:جزوه|فایل|سند|کد|اسلاید|اسلایدها|متن|مطالب)\s*(?:رو|را)?\s*",
    re.IGNORECASE,
)


def _decode_bytes(data: bytes) -> str:
    for enc in ("utf-8", "utf-16", "windows-1256", "cp1252"):
        try:
            return data.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return data.decode("utf-8", errors="replace")


def _extract_pdf(path: str) -> str:
    from pypdf import PdfReader
    reader = PdfReader(path)
    parts = []
    for i, page in enumerate(reader.pages, 1):
        try:
            txt = page.extract_text() or ""
        except Exception as e:
            log.warning("pdf page %d extract error: %s", i, e)
            txt = ""
        if txt.strip():
            parts.append(f"[صفحه {i}]\n{txt.strip()}")
    return "\n\n".join(parts)


def _extract_docx(path: str) -> str:
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml")
    root = ET.fromstring(xml)
    paras = []
    for p in root.iter(f"{_DOCX_NS}p"):
        runs = [t.text or "" for t in p.iter(f"{_DOCX_NS}t")]
        line = "".join(runs).strip()
        if line:
            paras.append(line)
    return "\n".join(paras)


def _extract_pptx(path: str) -> str:
    with zipfile.ZipFile(path) as z:
        names = [n for n in z.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)]
        names.sort(key=lambda n: int(re.search(r"(\d+)", n).group(1)))
        parts = []
        for name in names:
            num = int(re.search(r"(\d+)", name).group(1))
            xml = z.read(name)
            root = ET.fromstring(xml)
            texts = [t.text or "" for t in root.iter(f"{_PPTX_NS}t")]
            line = "\n".join(x.strip() for x in texts if x.strip())
            if line:
                parts.append(f"[اسلاید {num}]\n{line}")
    return "\n\n".join(parts)


def _extract_plain(path: str) -> str:
    with open(path, "rb") as f:
        return _decode_bytes(f.read())


def extract_text(path: str, ext: str) -> str:
    ext = (ext or "").lower()
    if ext == ".pdf":
        text = _extract_pdf(path)
    elif ext == ".docx":
        text = _extract_docx(path)
    elif ext == ".pptx":
        text = _extract_pptx(path)
    else:
        text = _extract_plain(path)
    text = (text or "").strip()
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS] + "\n... [ادامه متن به دلیل حجم حذف شد]"
    return text


_FORMAT_RULES = (
    "### قالب‌بندی (تو یک ویرایشگر متن حرفه‌ای هستی):\n"
    "- تیترها را با ## و ### بنویس و کلمات/تعریف‌های کلیدی را **بولد** کن.\n"
    "- پاسخ مستقیم، تعریف‌ها و قضیه‌ها را داخل کادر نقل‌قول (>) بگذار تا قابل کپی باشد.\n"
    "- هر فرمول یا کد را داخل بلاک کد (```) بگذار تا دقیق و قابل کپی باشد.\n"
    "- هر جا مقایسه یا فهرست نظام‌مند لازم بود، از جدول Markdown استفاده کن.\n"
    "- فارسی، روان و منظم بنویس.\n"
)

_STUDY_SYSTEM = (
    "# نقش: تو «کاپری»، همیار فوق‌هوشمند تحصیلی و استادیار (TA) شخصی دانشجو هستی.\n"
    "تو اسناد آموزشی (جزوه، اسلایدهای درسی، مقاله و یادداشت) را با دقت آکادمیک بسیار بالا "
    "کالبدشکافی می‌کنی تا کاربر در امتحان موفق شود.\n\n"
    "### اصول طلایی کار تو:\n"
    "۱. **پایه‌گذاری (Grounding):** پاسخ‌هایت را فقط بر اساس متن همین سند بده؛ هر ادعا را با شماره "
    "صفحه/اسلاید ارجاع بده (مثلاً «صفحه ۳»). اگر مطلبی در سند نبود، صادقانه بگو در سند نیست.\n"
    "۲. **ساده‌سازی:** مفاهیم پیچیده را با زبان ساده، مثال و تشبیه توضیح بده.\n"
    "۳. **رادار امتحان:** همیشه پیش‌بینی کن سوال امتحانی احتمالی چیست و نکته‌ی تستی بده.\n\n"
) + _FORMAT_RULES

_CODE_SYSTEM = (
    "# نقش: تو «کاپری»، مهندس ارشد نرم‌افزار و تحلیلگر کد هستی.\n"
    "کد کاربر را دقیق، فنی و کاربردی تحلیل می‌کنی تا آن را بفهمد، باگ‌هایش را پیدا کند و بهترش کند.\n\n"
    "### قواعد:\n"
    "۱. **پایه‌گذاری (Grounding):** فقط بر اساس خود کد؛ هر ادعا را با نام تابع/کلاس/خط ارجاع بده.\n"
    "۲. **ساده‌سازی:** منطق پیچیده را با زبان ساده توضیح بده.\n"
    "۳. **دقت فنی:** ورودی/خروجی، وابستگی‌ها و رفتارهای edge-case را ببین.\n\n"
) + _FORMAT_RULES


def _report_prompt(is_code: bool, filename: str) -> str:
    if is_code:
        return (
            f"### ماموریت:\n"
            f"کاربر فایل کد «{filename}» را فرستاده و از تو خواسته آن را بررسی کنی. "
            f"یک گزارش کامل و حرفه‌ای در ۴ بخش زیر تولید کن:\n\n"
            f"#### 🗺️ ۱. نمای کلی و معماری:\n"
            f"- این کد چه کاری انجام می‌دهد؟ (در یک پاراگراف ساده)\n"
            f"- ساختار و بخش‌های اصلی (توابع/کلاس‌ها/ماژول‌ها) را فهرست کن.\n\n"
            f"#### 🔑 ۲. تحلیل دقیق بخش‌های کلیدی:\n"
            f"- مهم‌ترین توابع/کلاس‌ها را یکی‌یکی توضیح بده و به نام آن‌ها ارجاع بده.\n"
            f"- منطق، ورودی/خروجی و نکات ظریف هر بخش را بگو.\n\n"
            f"#### 🐞 ۳. باگ‌ها، مشکلات و ریسک‌ها:\n"
            f"- خطاهای احتمالی، نشت منابع، مشکلات امنیتی یا کارایی را شناسایی کن.\n\n"
            f"#### ✨ ۴. پیشنهادهای بهبود:\n"
            f"- پیشنهادهای مشخص برای تمیزتر/سریع‌تر/امن‌تر شدن کد بده.\n"
        )
    return (
        f"### ماموریت:\n"
        f"کاربر فایل «{filename}» را فرستاده و از تو خواسته این سند را بررسی کنی. "
        f"یک گزارش جامع مطالعه در ۴ بخش زیر تولید کن:\n\n"
        f"#### 🗺️ ۱. نقشه راه (Roadmap):\n"
        f"- منطق کلی و ساختار سند را بگو؛ این سند به چه ترتیبی چه مباحثی را پوشش می‌دهد؟\n"
        f"- بهترین ترتیب مطالعه برای امتحان را پیشنهاد بده.\n\n"
        f"#### 🔑 ۲. مفاهیم کلیدی و فرمول‌ها:\n"
        f"- مهم‌ترین مفاهیم، تعریف‌ها، فرمول‌ها و قضایا را با ذکر شماره صفحه/اسلاید فهرست کن.\n"
        f"- برای هر مفهوم یک توضیح کوتاه و ساده بنویس.\n\n"
        f"#### 🎯 ۳. پیش‌بینی سوالات امتحانی (Exam Radar):\n"
        f"- ۳ تا ۵ سوال محتمل امتحانی را همراه با پاسخ خلاصه بنویس.\n\n"
        f"#### ⚠️ ۴. دام‌های امتحانی (Traps):\n"
        f"- رایج‌ترین اشتباهات مفهومی، نکات گمراه‌کننده و مواردی که دانشجوها جا می‌اندازند را هشدار بده.\n"
    )


def _question_prompt(is_code: bool, filename: str, question: str) -> str:
    if is_code:
        return (
            f"### ماموریت:\n"
            f"کاربر فایل کد «{filename}» را فرستاده و این سوال را پرسیده است: «{question}»\n"
            f"پاسخ را فقط بر اساس همین کد و با ساختار ۳ بخشی زیر بده:\n\n"
            f"#### ۱. پاسخ مستقیم و کوتاه:\n"
            f"- در ۱ تا ۳ جمله، پاسخ اصلی سوال را بگو و داخل کادر نقل‌قول بگذار.\n\n"
            f"#### ۲. توضیح فنی با ارجاع به کد:\n"
            f"- با ارجاع به نام تابع/کلاس/خط توضیح بده؛ در صورت نیاز کد مربوطه را در بلاک کد بیاور.\n\n"
            f"#### ۳. نکته یا هشدار:\n"
            f"- باگ احتمالی، بهبود، یا کاربرد مهم این بخش را بگو.\n"
        )
    return (
        f"### ماموریت:\n"
        f"کاربر فایل «{filename}» را فرستاده و این سوال را پرسیده است: «{question}»\n"
        f"پاسخ را فقط بر اساس همین سند و با ساختار ۳ بخشی زیر بده:\n\n"
        f"#### ۱. پاسخ مستقیم و کوتاه:\n"
        f"- در ۱ تا ۳ جمله، پاسخ اصلی سوال را بگو و داخل کادر نقل‌قول بگذار.\n\n"
        f"#### ۲. توضیح مفهومی با ارجاع:\n"
        f"- مفهوم را ساده و دقیق توضیح بده و با شماره صفحه/اسلاید ارجاع بده.\n"
        f"- اگر در سند تعریف/فرمول/شکل مرتبطی هست، همان را بیاور.\n\n"
        f"#### ۳. نکته امتحانی (Exam Tip):\n"
        f"- این مفهوم چطور در سوال امتحانی می‌آید و چه چیزی را باید دقیق حفظ کرد؟\n"
    )


def analyze(path: str, ext: str, filename: str, question: str, is_code: bool = False) -> str:
    """تحلیل فایل (بلاکینگ؛ توسط caller در asyncio.to_thread اجرا شود). خالی = خطا."""
    system = _CODE_SYSTEM if is_code else _STUDY_SYSTEM
    user = _question_prompt(is_code, filename, question) if question else _report_prompt(is_code, filename)
    ext = (ext or "").lower()

    if ext == ".pdf":
        # جمینای خود فایل PDF را می‌خواند (حتی اسکن‌شده). این بهترین مسیر است.
        raw = ai.analyze_pdf(path, user, system)
        if raw and raw.strip():
            return raw.strip()
        # فال‌بک: استخراج متن با pypdf (برای PDF متنی وقتی File API در دسترس نیست)
        text = extract_text(path, ext)
        if text:
            raw = ai._gemini(f"{system}\n\n{user}\n\n### متن سند:\n{text}")
            return (raw or "").strip() or None
        return None

    text = extract_text(path, ext)
    if not text:
        return None
    raw = ai._gemini(f"{system}\n\n{user}\n\n### محتوای سند:\n{text}")
    return (raw or "").strip() or None


def clean_question(q: str) -> str:
    """عبارات «بررسی کن» و ارجاع به سند/کد را حذف می‌کند؛ خروجی خالی یعنی کاربر فقط بررسی کلی می‌خواهد."""
    q = (q or "").strip()
    if not q:
        return ""
    for w in _REVIEW_PHRASES:
        q = q.replace(w, " ")
    for _ in range(3):
        new_q = _DOC_PREFIX_RE.sub("", q, count=1)
        if new_q == q:
            break
        q = new_q
    q = re.sub(r"\s+", " ", q).strip(" ،,:.؟?!")
    return q


def is_study_document(msg) -> str:
    """اگر پیام یک سند آموزشی یا فایل کد با پسوند پشتیبانی‌شده باشد، پسوند (با نقطه) را برمی‌گرداند، وگرنه خالی."""
    doc = getattr(msg, "document", None) or getattr(msg, "file", None)
    if doc is None:
        return ""
    if getattr(msg, "sticker", None) or getattr(msg, "photo", None):
        return ""
    if getattr(msg, "video", None) or getattr(msg, "audio", None) or getattr(msg, "voice", None) or getattr(msg, "video_note", None):
        return ""
    name = ""
    for a in getattr(doc, "attributes", None) or []:
        if isinstance(a, types.DocumentAttributeFilename) and a.file_name:
            name = a.file_name
            break
    if not name:
        return ""
    ext = os.path.splitext(name)[1].lower()
    return ext if ext in SUPPORTED_EXTS else ""
