"""تحلیل چت: گزارش داده‌محور و ۶ مرحله‌ای از تاریخچه‌ی چت فعلی.

پیام‌های خام (تا ۵۰۰ پیام، بدون پیام‌های ویرایش‌شده) را می‌خواند و گزارشی عریان و
واقع‌بینانه در ۶ محور (انرژی، ریتم پاسخ‌دهی، اتمسفر احساسی، تعادل قدرت،
پرچم‌های قرمز/سبز و نمره‌ی سلامت) تولید می‌کند.
"""
import asyncio
import logging

from ai_engine import ai
from core import config

log = logging.getLogger("chatanalysis")

MAX_MSGS = 500

CHAT_ANALYSIS_TRIGGERS = (
    "تحلیل کن این چت", "تحلیل کن چت", "این چت رو تحلیل", "این چتو تحلیل", "این چت را تحلیل",
    "تحلیل این چت", "چت رو تحلیل", "چتو تحلیل", "تحلیل چت",
    "آنالیز کن این چت", "آنالیز این چت", "چت رو آنالیز", "آنالیز چت",
)


def is_chat_analysis_request(text: str) -> bool:
    t = (text or "").lower()
    return any(k in t for k in CHAT_ANALYSIS_TRIGGERS)


_REPORT_SYSTEM = (
    "# نقش: تو یک روان‌شناس ارشد رفتاری و پروفایلر دیجیتال روابط انسانی هستی.\n"
    "وظیفه تو این است که تاریخچه تبادل پیام‌های بین «صاحب اکانت ({OWNER_NAME})» و «مخاطب ({TARGET_NAME})» را "
    "کالبدشکافی کنی و گزارشی عریان، واقعی و بدون تعارف از وضعیت این چت ارائه دهی.\n\n"
    "### ⛔ قانون طلایی فیلترینگ داده‌ها:\n"
    "تمامی پیام‌های ویرایش‌شده قبلاً از داده حذف شده‌اند؛ تحلیل تو باید ۱۰۰٪ مبتنی بر پیام‌های خام، دست‌نخورده و اولیه باشد "
    "تا افکار ناخودآگاه و ارگانیک افراد سنجیده شود.\n"
    "---\n"
    "### 📊 ساختار گزارش و محورهای ۶ گانه تحلیل:\n"
    "#### ۱. 🌡️ دماسنج انرژی و توازن سرمایه‌گذاری (Energy & Investment Balance)\n"
    "- نسبت شروع گفتگوها: چند درصد مکالمات توسط {OWNER_NAME} آغاز شده و چند درصد توسط {TARGET_NAME}؟ (چه کسی اشتیاق بیشتری خرج می‌کند؟)\n"
    "- طول و حجم کلامی: چه کسی پیام‌های بلند و کامل می‌نویسد و چه کسی به پیام‌های کوتاه، تک‌کلمه‌ای بسنده می‌کند؟\n"
    "- تعادل اشتیاق: آیا تلاش دوطرفه است یا یک نفر مکالمه را به تنهایی حمل می‌کند؟\n\n"
    "#### ۲. ⏱️ رادار زمان پاسخ‌دهی و تغییرات ریتم (Response Latency & Trendline)\n"
    "- میانگین سرعت پاسخ طرفین: هر طرف به طور میانگین بعد از چه مدت پاسخ می‌دهد؟\n"
    "- سیر تحول در طول زمان: مقایسه سرعت پاسخ در اوایل بازه نسبت به اواخر بازه؛ آیا «سردی تدریجی»، «تاخیر تاکتیکی» یا «نادیده گرفتن (Ghosting/Drifting)» دیده می‌شود؟\n\n"
    "#### ۳. 🎭 نقشه اتمسفر احساسی و زیرمتن غالب (Emotional Climate)\n"
    "- لحن مسلط: صمیمانه و پرمحبت، اداری و خشک، طلبکارانه، سرزنش‌گر، شوخ‌طبع و رفاقتی، یا منفعل-تهاجمی؟\n"
    "- کلیدواژه‌ها و تکیه‌کلام‌های پرتکرار و موضوعات محوری.\n"
    "- تغییر شیفت عاطفی: آیا نوسانات روحی شدید در رفتار {TARGET_NAME} نسبت به {OWNER_NAME} دیده می‌شود؟\n\n"
    "#### ۴. ⚖️ دماسنج تعادل قدرت (Power Dynamics & Leverage)\n"
    "- دست بالا با کیست؟ چه کسی «تعیین‌کننده مسیر» است و چه کسی بیشتر در موضع «تاییدخواهی، توضیح دادن یا جلب رضایت» قرار دارد؟\n"
    "- سنجش آزمون‌های روانی: آیا نشانه‌ای از گس‌لایتینگ، ایجاد عذاب وجدان یا سرد و گرم کردن عامدانه در پیام‌های مخاطب دیده می‌شود؟\n\n"
    "#### ۵. 🚩 پرچم‌های قرمز و 🟢 پرچم‌های سبز (Red & Green Flags)\n"
    "- نقاط قوت: حمایتگری، احترام به حریم، خوش‌قولی و همدلی.\n"
    "- نقاط مسموم یا هشداردهنده: پاسخ ندادن‌های عامدانه، صحبت فقط هنگام نیاز به کمک، بی‌میلی به باز کردن صحبت‌های عمیق.\n\n"
    "#### ۶. ♟️ نمره سلامت چت و توصیه استراتژیک به {OWNER_NAME}\n"
    "- نمره نهایی سلامت این چت از ۱۰۰.\n"
    "- توصیه رفتاری مستقیم: آیا باید انرژی‌اش را با این فرد کم کند، مرزهایش را سفت‌تر ببندد، یا فضا برای اعتماد و صمیمیت بیشتر مهیاست؟\n\n"
    "خروجی را فارسی، روان، ساختاریافته (با تیتر و بولت) و بی‌رودربایستی بنویس."
)


async def analyze_chat(client, event) -> str:
    chat_id = event.chat_id

    target_name = "این چت"
    if event.is_private:
        try:
            ent = await client.get_entity(chat_id)
            if ent is not None:
                target_name = getattr(ent, "first_name", "") or getattr(ent, "title", "") or "مخاطب"
        except Exception:
            pass

    rows = []
    first_ts = last_ts = None
    try:
        async for msg in client.iter_messages(chat_id, limit=MAX_MSGS):
            # قانون طلایی: پیام‌های ویرایش‌شده حذف می‌شوند
            if msg.edit_date is not None:
                continue
            text = msg.text or ""
            if not text:
                continue
            sender = "OWNER" if msg.out else "TARGET"
            date_str = msg.date.strftime("%Y-%m-%d %H:%M")
            rows.append(f"[{date_str}] {sender}: {text}")
            if first_ts is None or msg.date < first_ts:
                first_ts = msg.date
            if last_ts is None or msg.date > last_ts:
                last_ts = msg.date
    except Exception as e:
        log.warning(f"Error reading chat for analysis: {e}")
        return f"❌ خطا در خواندن تاریخچه چت: {e}"

    rows.reverse()
    total = len(rows)
    if total < 3:
        return f"❌ پیام کافی برای تحلیل پیدا نکردم (فقط {total} پیام خامِ غیرویرایش‌شده موجوده)."

    history = "\n".join(rows)
    if len(history) > 60000:
        history = history[:60000] + "\n... [ادامهٔ تاریخچه به دلیل حجم حذف شد]"

    start_date = first_ts.strftime("%Y-%m-%d") if first_ts else "—"
    end_date = last_ts.strftime("%Y-%m-%d") if last_ts else "—"

    system = _REPORT_SYSTEM.replace("{OWNER_NAME}", config.OWNER_NAME).replace("{TARGET_NAME}", target_name)
    prompt = (
        f"{system}\n\n"
        f"[اطلاعات مکالمه]\n"
        f"- صاحب اکانت: {config.OWNER_NAME} (OWNER)\n"
        f"- مخاطب/چت: {target_name} (TARGET)\n"
        f"- بازه زمانی: {start_date} تا {end_date}\n"
        f"- تعداد پیام‌های دست‌نخورده بررسی‌شده: {total}\n\n"
        f"[تاریخچه چت‌های خام بدون پیام‌های ادیت‌شده]:\n{history}\n\n"
        "دستور: طبق پرامپت تحلیلی سیستم، یک گزارش جامع ۶ مرحله‌ای، واقع‌بینانه و بدون رودربایستی تولید کن."
    )

    try:
        raw = await asyncio.to_thread(ai._gemini, prompt)
    except Exception as e:
        return f"❌ خطا در تولید گزارش: {e}"

    if raw:
        return raw.strip()
    return "❌ الان نتونستم گزارش رو بسازم؛ چند دقیقه دیگه دوباره امتحان کن."
