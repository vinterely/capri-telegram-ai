"""تست‌های رگرسیون: تزریق تاریخ/زمان پویا، لغو واقعی عملیات، و تشخیص هوشمند غیبت مالک."""
import asyncio
import os
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import bot
from ai_engine import ai
from core import ops
from services.social import dnd


# -----------------------------------------------------------------------------
# ۱. تزریق تاریخ/زمان پویا + تازگی دانش
# -----------------------------------------------------------------------------

class TestDateInjection(unittest.TestCase):
    """تاریخ و زمان فعلی باید از ساعت واقعی سیستم + تایم‌زون پیکربندی‌شده محاسبه شود."""

    def test_today_is_jalali_format(self):
        today = ai._today()
        self.assertRegex(today, r"\d{4}/\d{2}/\d{2}")
        self.assertIn("(", today)  # روز هفته داخل پرانتز

    def test_now_context_has_time_and_timezone(self):
        ctx = ai._now_context()
        self.assertIn("ساعت", ctx)
        self.assertIn("منطقه زمانی", ctx)
        self.assertRegex(ctx, r"\d{2}:\d{2}:\d{2}")

    def test_local_tz_is_tz_aware(self):
        tz = ai._local_tz()
        now = datetime.now(tz)
        self.assertIsNotNone(now.tzinfo)
        self.assertIsNotNone(now.utcoffset())

    def test_build_system_injects_now_context(self):
        sys_prompt = ai._build_system("", "", web=False)
        self.assertIn("تاریخ و زمان فعلی", sys_prompt)
        self.assertIn("تازگی دانش", sys_prompt)


# -----------------------------------------------------------------------------
# ۲. تشخیص دقیق دستور لغو (بدون مثبت کاذب)
# -----------------------------------------------------------------------------

class TestCancelCommand(unittest.TestCase):
    """دستور لغو باید فرم‌های دستوری کوتاه را بگیرد و متن عادی را رد کند."""

    POSITIVE = (
        "لغو کن", "کنسل", "بی‌خیال", "متوقفش کن", "لغو عملیات",
        "دانلود رو لغو کن", "این کار رو کنسل کن", "ولش کن",
        "لغو", "متوقف", "استپ", "توقف", "انصراف", "لغو دانلود",
    )

    NEGATIVE = (
        "", "یه چیز معمولی", "درباره لغو توضیح بده", "لغو اشتراک یعنی چی؟",
        "سلام چطوری", "امروز هوا خوبه",
        # جملهٔ طولانی غیردستوری (بیش از ۴۰ کاراکتر یا چند کلمه)
        "لغو جلسه فردا ساعت ده صبح لطفا اطلاع رسانی کن",
    )

    def test_positive(self):
        for t in self.POSITIVE:
            self.assertTrue(bot.is_cancel_command(t), f"should be cancel: {t!r}")

    def test_negative(self):
        for t in self.NEGATIVE:
            self.assertFalse(bot.is_cancel_command(t), f"should NOT be cancel: {t!r}")


# -----------------------------------------------------------------------------
# ۳. رجیستری عملیات و لغو واقعی (ایزوله بر اساس گفتگو)
# -----------------------------------------------------------------------------

class TestOpsRegistry(unittest.IsolatedAsyncioTestCase):
    """لغو باید فقط تسکِ همان گفتگو را باطل کند و تسک خودِ دستور لغو را لغو نکند."""

    async def asyncSetUp(self):
        ops._active.clear()

    async def _spawn(self):
        async def work():
            try:
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                raise

        return asyncio.create_task(work())

    async def test_register_get_unregister(self):
        t = await self._spawn()
        ops.register("123", t)
        self.assertIsNotNone(ops.get("123"))
        self.assertIs(ops.get("123").task, t)
        ops.unregister("123", t)
        self.assertIsNone(ops.get("123"))
        t.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await t

    async def test_cancel_stops_only_matching_chat(self):
        t1 = await self._spawn()
        t2 = await self._spawn()
        ops.register("111", t1)
        ops.register("222", t2)
        self.assertTrue(ops.cancel("111"))
        await asyncio.sleep(0)
        self.assertTrue(t1.cancelled())
        self.assertFalse(t2.cancelled())
        ops.cancel("222")
        await asyncio.sleep(0)
        self.assertTrue(t2.cancelled())

    async def test_cancel_nothing_returns_false(self):
        self.assertFalse(ops.cancel("999"))

    async def test_cancel_does_not_cancel_self(self):
        ops.register("me", asyncio.current_task())
        self.assertFalse(ops.cancel("me"))
        self.assertIsNotNone(ops.get("me"))
        ops.unregister("me")

    async def test_unregister_ignores_stale_task(self):
        t1 = await self._spawn()
        t2 = await self._spawn()
        ops.register("x", t1)
        ops.unregister("x", t2)  # تسک متفاوت؛ نباید عملیات را حذف کند
        self.assertIsNotNone(ops.get("x"))
        ops.unregister("x", t1)
        self.assertIsNone(ops.get("x"))
        t1.cancel()
        t2.cancel()

    async def test_cancel_all(self):
        t1 = await self._spawn()
        t2 = await self._spawn()
        ops.register("1", t1)
        ops.register("2", t2)
        self.assertEqual(ops.cancel_all(), 2)
        await asyncio.sleep(0)
        self.assertTrue(t1.cancelled())
        self.assertTrue(t2.cancelled())


# -----------------------------------------------------------------------------
# ۴. تشخیص هوشمند غیبت مالک (بدون مثبت کاذب)
# -----------------------------------------------------------------------------

class TestAbsenceDetection(unittest.TestCase):
    """اعلام غیبت اول‌شخص باید فعال شود؛ سوال، نقل‌قول، فرض و زمان گذشته رد شود."""

    POSITIVE = (
        "من تا ساعت ۸ نیستم",
        "تا دو ساعت دیگه برمیگردم",
        "امشب نمیتونم پیامها رو ببینم",
        "فعلا نیستم، اگه کسی پیام داد مدیریت کن",
        "میرم بیرون تا نیم ساعت دیگه برمیگردم",
        "امروز در دسترس نیستم",
    )

    NEGATIVE = (
        "من طرفدار این نیستم",
        "چرا نیستم؟",
        "اون گفت که نیستم",
        "من دیروز نبودم",
        "پارسال نبودم خونه",
        "فرض کن نیستم",
        "اگه نباشم چی میشه؟",
        "تو نبودم چی کار می‌کنی؟",
        "علی گفت امروز نیستم",
    )

    def test_positive(self):
        for t in self.POSITIVE:
            self.assertTrue(dnd.is_absence_activation(t), f"should be absence: {t!r}")

    def test_negative(self):
        for t in self.NEGATIVE:
            self.assertFalse(dnd.is_absence_activation(t), f"should NOT be absence: {t!r}")

    def test_deactivate_return_words(self):
        for t in ("برگشتم", "برگشتیم", "اومدم", "آمدم", "رسیدم", "آزاد شدم", "بیدار شدم"):
            self.assertTrue(dnd.is_dnd_deactivate_command(t), f"should deactivate: {t!r}")

    def test_deactivate_not_triggered_by_normal_text(self):
        self.assertFalse(dnd.is_dnd_deactivate_command("حالم خوبه"))
        self.assertFalse(dnd.is_dnd_deactivate_command("برگشتن به خونه چقدر طول کشید؟"))


# -----------------------------------------------------------------------------
# ۵. تجزیهٔ زمان (نسبی/مطلق) برای غیبت و یادآور
# -----------------------------------------------------------------------------

class TestParseTimeExpression(unittest.TestCase):
    def test_relative_hours(self):
        now = datetime(2026, 10, 27, 12, 0, 0)
        target, desc = dnd.parse_time_expression("۲ ساعت دیگه", now=now)
        self.assertEqual(target, now + timedelta(hours=2))

    def test_half_hour(self):
        now = datetime(2026, 10, 27, 12, 0, 0)
        target, desc = dnd.parse_time_expression("نیم ساعت دیگه", now=now)
        self.assertEqual(target, now + timedelta(minutes=30))

    def test_tonight_means_end_of_day(self):
        now = datetime(2026, 10, 27, 12, 0, 0)
        target, desc = dnd.parse_time_expression("امشب نیستم", now=now)
        self.assertEqual(target, now.replace(hour=23, minute=59, second=0, microsecond=0))

    def test_clock_evening_shift(self):
        now = datetime(2026, 10, 27, 12, 0, 0)
        target, desc = dnd.parse_time_expression("تا ساعت ۸ نیستم", now=now)
        self.assertEqual((target.hour, target.minute), (20, 0))

    def test_no_time_returns_none(self):
        target, desc = dnd.parse_time_expression("سلام خوبی؟", now=datetime(2026, 10, 27, 12, 0, 0))
        self.assertIsNone(target)


# -----------------------------------------------------------------------------
# ۶. ماندگاری DND و پیام‌های از دست‌رفته (بدون دستکاری فایل‌های واقعی)
# -----------------------------------------------------------------------------

class TestDndPersistenceAndMissed(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._orig_dnd = dnd.DND_FILE
        self._orig_rem = dnd.REMINDERS_FILE
        dnd.DND_FILE = os.path.join(self.tmp.name, "dnd.json")
        dnd.REMINDERS_FILE = os.path.join(self.tmp.name, "reminders.json")

    def tearDown(self):
        dnd.DND_FILE = self._orig_dnd
        dnd.REMINDERS_FILE = self._orig_rem
        self.tmp.cleanup()

    def test_activate_resets_missed(self):
        dnd.activate_dnd("مشغله")
        info = dnd.get_dnd_info()
        self.assertTrue(info.get("active"))
        self.assertEqual(info.get("missed"), [])
        self.assertIsNotNone(info.get("missed_since"))

    def test_record_missed_and_summary(self):
        dnd.activate_dnd("مشغله")
        dnd.record_missed("علی", "چت خصوصی (PV)", "سلام کجایی؟")
        dnd.record_missed("مریم", "گروه «دوستان»", "کار مهمی داشتم")
        summary = dnd.get_missed_summary()
        self.assertIn("علی", summary)
        self.assertIn("مریم", summary)
        self.assertIn("سلام کجایی؟", summary)

    def test_record_missed_caps_at_50(self):
        dnd.activate_dnd("مشغله")
        for i in range(60):
            dnd.record_missed("کاربر", "چت خصوصی (PV)", f"پیام {i}")
        info = dnd.get_dnd_info()
        self.assertEqual(len(info.get("missed")), 50)
        self.assertEqual(info["missed"][-1]["text"], "پیام 59")

    def test_summary_empty_when_no_missed(self):
        dnd.activate_dnd("مشغله")
        self.assertIn("پیام جدیدی ثبت نشده", dnd.get_missed_summary())

    def test_is_dnd_active_auto_expire(self):
        dnd.activate_dnd("مشغله", until_ts=time.time() - 10, until_str="گذشته")
        self.assertFalse(dnd.is_dnd_active())

    def test_deactivate_turns_off(self):
        dnd.activate_dnd("مشغله")
        self.assertTrue(dnd.is_dnd_active())
        dnd.deactivate_dnd()
        self.assertFalse(dnd.is_dnd_active())

    def test_reminders_add_list_clear(self):
        dnd.add_reminder("جزوه بفرستم", time.time() + 3600, "۱ ساعت دیگر")
        dnd.add_reminder("زنگ بزنم", time.time() + 7200, "۲ ساعت دیگر")
        self.assertEqual(len(dnd.load_reminders()), 2)
        self.assertEqual(dnd.clear_all_reminders(), 2)
        self.assertEqual(dnd.load_reminders(), [])


if __name__ == "__main__":
    unittest.main()
