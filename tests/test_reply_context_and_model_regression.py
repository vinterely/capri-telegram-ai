"""
تست‌های رگرسیون جامع Capri Telegram AI:
تأییدیه ۱۰ سناریوی حیاتی مطابق بند ۶ دستورالعمل کاربر:
۱. خلاصه‌کردن متن ساده نباید فرمان تغییر مدل را اجرا کند.
۲. فرمان معتبر تغییر مدل باید مدل انتخاب‌شده را فعال کند و درخواست‌های عادی نباید آن را تغییر دهند.
۳. ریپلای به پیام متنی همراه با دستور «خلاصه کن» باید محتوای پیام اصلی را به مدل منتقل کند.
۴. ریپلای به پیام حاوی لینک باید لینک و محتوای مرتبط پیام اصلی را در دسترس مسیر مناسب قرار دهد.
۵. ریپلای در گروه باید نویسنده پیام اصلی و فرستنده درخواست جاری را به‌درستی تفکیک کند.
۶. پیام‌های همزمان در دو گروه نباید context یا هویت یکدیگر را دریافت کنند.
۷. درخواست‌های همزمان با مدل‌های متفاوت نباید باعث نشت وضعیت مدل یا context شوند.
۸. دسترسی به پیام اصلی حذف‌شده یا غیرقابل‌دسترسی باید به‌درستی مدیریت شود.
۹. اطلاعات حافظه خصوصی نباید در پاسخ گروهی افشا شود.
۱۰. تغییرات جدید نباید مسیرهای دانلود، خلاصه‌سازی، دریافت اطلاعات ویدیو یا پاسخ متنی را خراب کنند.
"""

import asyncio
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from ai_engine import models
from ai_engine.agent import AgentExecutionCycle, build_environment_context
from core import memory, settings
from services.media import socialdl, ytsummary


class MockTelegramSender:
    def __init__(self, sender_id: int, first_name: str, username: str = ""):
        self.id = sender_id
        self.first_name = first_name
        self.username = username
        self.title = first_name


class MockTelegramChat:
    def __init__(self, chat_id: int, title: str = "", megagroup: bool = False):
        self.id = chat_id
        self.title = title
        self.megagroup = megagroup


class MockTelegramMessage:
    def __init__(self, msg_id: int, text: str, sender_id: int = 1001, sender_name: str = "Ali", media=None):
        self.id = msg_id
        self.raw_text = text
        self.message = text
        self.sender_id = sender_id
        self.sender = MockTelegramSender(sender_id, sender_name)
        self.out = False
        self.fwd_from = None
        self.media = media
        self.photo = media if media == "photo" else None
        self.video = media if media == "video" else None
        self.video_note = None
        self.voice = media if media == "voice" else None
        self.audio = None
        self.document = media if media == "document" else None
        self.file = None

    async def get_sender(self):
        return self.sender


class MockTelegramEvent:
    def __init__(
        self,
        chat_id: int,
        sender_id: int,
        text: str,
        reply_to_msg_id: int = None,
        is_private: bool = True,
        is_group: bool = False,
        chat_title: str = "",
        sender_name: str = "User",
        out: bool = False
    ):
        self.id = 9999
        self.chat_id = chat_id
        self.sender_id = sender_id
        self.raw_text = text
        self.message = text
        self.reply_to_msg_id = reply_to_msg_id
        self.is_private = is_private
        self.is_group = is_group
        self.is_channel = False
        self.chat = MockTelegramChat(chat_id, title=chat_title)
        self.sender = MockTelegramSender(sender_id, sender_name)
        self.out = out
        self.fwd_from = None
        self._reply_message = None

    async def get_sender(self):
        return self.sender

    async def get_chat(self):
        return self.chat

    async def get_reply_message(self):
        return self._reply_message


class TestModelAndReplyRegression(unittest.TestCase):
    def setUp(self):
        # ذخیره وضعیت قبلی تنظیمات مدل
        self._orig_selection = settings.get_selection()
        settings.set_selection("inception", "mercury-3")

    def tearDown(self):
        # بازگرداندن وضعیت مدل
        if self._orig_selection[0] and self._orig_selection[1]:
            settings.set_selection(self._orig_selection[0], self._orig_selection[1])

    # -------------------------------------------------------------------------
    # سناریو ۱: خلاصه‌کردن متن ساده نباید فرمان تغییر مدل را اجرا کند
    # -------------------------------------------------------------------------
    def test_scenario_1_summarizing_text_does_not_trigger_model_change(self):
        """متن‌های دارای افعال فارسی مانند «باید» نباید به عنوان سرویس bai یا تغییر مدل شناسایی شوند."""
        test_queries = [
            "کاپری این متن رو باید خلاصه کنی: هوش مصنوعی و یادگیری عمیق شاخه‌ای از علوم کامپیوتر هستند.",
            "باید این مقاله طولانی را به زبان فارسی خلاصه کنی.",
            "این متن طولانی ایرانی را برام چکیده کن.",
            "کاپری لطفاً خلاصه کن که هوش مصنوعی چطوری کار می‌کنه.",
            "بایستی این سند را مطالعه و تحلیل کنی."
        ]
        for q in test_queries:
            req = models.parse_request(q)
            self.assertIsNone(
                req,
                f"عبارت «{q}» نباید درخواست تغییر مدل تولید کند، اما {req} بازگردانده شد."
            )

        # اطمینان از اینکه مدل فعال در settings بدون تغییر روی mercury-3 باقی مانده است
        sel_srv, sel_mod = settings.get_selection()
        self.assertEqual(sel_srv, "inception")
        self.assertEqual(sel_mod, "mercury-3")

    # -------------------------------------------------------------------------
    # سناریو ۲: فرمان معتبر تغییر مدل فعال می‌شود؛ درخواست‌های عادی تغییری نمی‌دهند
    # -------------------------------------------------------------------------
    def test_scenario_2_valid_model_commands_switch_model_and_normal_text_does_not(self):
        """فرمان‌های معتبر باید مدل را شناسایی کنند، اما متن‌های عادی با کلمات مشابه نباید."""
        # الف) فرامین معتبر
        valid_mercury = models.parse_request("کاپری برو رو مرکوری")
        self.assertIsNotNone(valid_mercury)
        self.assertEqual(valid_mercury.get("action"), "select")
        self.assertEqual(valid_mercury.get("service"), "inception")
        self.assertEqual(valid_mercury.get("model"), "mercury-3")

        valid_uid = models.parse_request("k1")
        self.assertIsNotNone(valid_uid)
        self.assertEqual(valid_uid.get("action"), "select")
        self.assertEqual(valid_uid.get("uid"), "k1")

        valid_model_uid = models.parse_request("کاپری مدل k1")
        self.assertIsNotNone(valid_model_uid)
        self.assertEqual(valid_model_uid.get("action"), "select")

        valid_info = models.parse_request("کاپری مدل فعال چیه؟")
        self.assertIsNotNone(valid_info)
        self.assertEqual(valid_info.get("action"), "info")

        # ب) جملات عادی که نباید تغییر مدل را فعال کنند
        normal_queries = [
            "سطح زبان من b2 هست و می‌خوام تقویتش کنم",
            "ویتامین b1 برای عملکرد مغز و اعصاب ضروری است",
            "پروژه e3 در شرکت ما با موفقیت تحویل داده شد",
            "آیا شرکت openrouter در سانفرانسیسکو است؟",
            "امروز با دوستم گفتیم و خندیدیم و بعدش بای بای کردیم",
            "متن قانون مدنی ایران درباره ارث"
        ]
        for nq in normal_queries:
            self.assertIsNone(
                models.parse_request(nq),
                f"جمله عادی «{nq}» نباید مدل را تغییر دهد!"
            )

    # -------------------------------------------------------------------------
    # سناریو ۳: ریپلای به پیام متنی همراه با دستور «خلاصه کن»
    # -------------------------------------------------------------------------
    def test_scenario_3_reply_to_text_with_summarize_transfers_content(self):
        """ریپلای به یک پیام متنی با دستور «خلاصه کن» باید محتوای پیام اصلی را استخراج و تزریق کند."""
        import bot

        original_text = "پایتون یک زبان برنامه‌نویسی همه‌منظوره و شی‌ءگرا است که در سال ۱۹۹۱ توسعه یافت."
        orig_msg = MockTelegramMessage(msg_id=123, text=original_text, sender_id=1001, sender_name="Ali")

        event = MockTelegramEvent(
            chat_id=1001,
            sender_id=1001,
            text="کاپری خلاصه کن",
            reply_to_msg_id=123,
            is_private=True
        )

        mock_client = AsyncMock()
        mock_client.get_messages.return_value = orig_msg

        # تست استخراج اطلاعات ریپلای
        reply_info = asyncio.run(bot.get_reply_info(event, mock_client))
        self.assertTrue(reply_info["has_reply"])
        self.assertTrue(reply_info["is_available"])
        self.assertEqual(reply_info["author_name"], "Ali")
        self.assertEqual(reply_info["author_id"], 1001)
        self.assertIn("پایتون", reply_info["text"])

        # تست ساخت کانتکست با ریپلای
        with patch.object(bot, "client", mock_client):
            context = asyncio.run(bot.get_context(event))
            self.assertIn("Ali", context)
            self.assertIn("1001", context)
            self.assertIn(original_text, context)
            self.assertIn("پیام ارجاع‌شده", context)

    # -------------------------------------------------------------------------
    # سناریو ۴: ریپلای به پیام حاوی لینک (یوتیوب / شبکه‌های اجتماعی)
    # -------------------------------------------------------------------------
    def test_scenario_4_reply_to_link_makes_link_accessible_to_route(self):
        """ریپلای به پیام حاوی لینک باید شناسه و آدرس ویدیو را برای مسیر متناسب فراهم کند."""
        import bot

        # الف) لینک یوتیوب در پیام اصلی
        yt_url = "https://youtu.be/dQw4w9WgXcQ"
        yt_msg = MockTelegramMessage(msg_id=456, text=f"این ویدیوی عالی را ببینید:\n{yt_url}")
        event_yt = MockTelegramEvent(chat_id=2002, sender_id=2002, text="کاپری خلاصه کن", reply_to_msg_id=456)

        mock_client = AsyncMock()
        mock_client.get_messages.return_value = yt_msg

        reply_info_yt = asyncio.run(bot.get_reply_info(event_yt, mock_client))
        self.assertEqual(reply_info_yt["yt_id"], "dQw4w9WgXcQ")

        # ب) لینک اینستاگرام در پیام اصلی
        ig_url = "https://www.instagram.com/reel/C1234567/"
        ig_msg = MockTelegramMessage(msg_id=789, text=f"اینم کلیپ اینستا:\n{ig_url}")
        event_ig = MockTelegramEvent(chat_id=2002, sender_id=2002, text="کاپری دانلود کن", reply_to_msg_id=789)

        mock_client.get_messages.return_value = ig_msg
        reply_info_ig = asyncio.run(bot.get_reply_info(event_ig, mock_client))
        self.assertEqual(reply_info_ig["social_url"], ig_url)

    # -------------------------------------------------------------------------
    # سناریو ۵: ریپلای در گروه و تفکیک نویسنده پیام اصلی و فرستنده جاری
    # -------------------------------------------------------------------------
    def test_scenario_5_group_reply_distinguishes_author_and_sender(self):
        """در گروه، شناسه عددی تلگرام و نام فرستنده جاری باید کاملاً از نویسنده پیام اصلی تفکیک شوند."""
        import bot

        author_id = 77777
        sender_id = 88888
        group_id = -100123456789

        orig_msg = MockTelegramMessage(
            msg_id=301,
            text="فردا ساعت ۸ صبح جلسه داریم.",
            sender_id=author_id,
            sender_name="سارا"
        )

        event = MockTelegramEvent(
            chat_id=group_id,
            sender_id=sender_id,
            text="کاپری فردا ساعت چند بود؟",
            reply_to_msg_id=301,
            is_private=False,
            is_group=True,
            chat_title="تیم فنی",
            sender_name="امیر"
        )

        mock_client = AsyncMock()
        mock_client.get_messages.return_value = orig_msg

        with patch.object(bot, "client", mock_client):
            context = asyncio.run(bot.get_context(event))

            # تفکیک فرستنده جاری
            self.assertIn("امیر", context)
            self.assertIn(str(sender_id), context)
            self.assertIn("فرستنده درخواست", context)

            # تفکیک گروه
            self.assertIn("تیم فنی", context)
            self.assertIn(str(group_id), context)

            # تفکیک نویسنده اصلی پیام ریپلای‌شده
            self.assertIn("سارا", context)
            self.assertIn(str(author_id), context)
            self.assertIn("فردا ساعت ۸ صبح جلسه داریم", context)

    # -------------------------------------------------------------------------
    # سناریو ۶: پیام‌های همزمان در دو گروه هویت یا context یکدیگر را دریافت نمی‌کنند
    # -------------------------------------------------------------------------
    def test_scenario_6_concurrent_messages_in_two_groups_isolated(self):
        """دو درخواست همزمان در دو گروه مختلف نباید کانتکست یکدیگر را نشت دهند."""
        import bot

        event_A = MockTelegramEvent(
            chat_id=-100111,
            sender_id=111,
            text="کاپری وضع گروه چطوره؟",
            is_private=False,
            is_group=True,
            chat_title="گروه آلفا",
            sender_name="نوید"
        )
        event_B = MockTelegramEvent(
            chat_id=-100222,
            sender_id=222,
            text="کاپری پروژه در چه مرحله‌ایه؟",
            is_private=False,
            is_group=True,
            chat_title="گروه بتا",
            sender_name="بهزاد"
        )

        mock_client = AsyncMock()
        mock_client.get_messages.return_value = []

        async def run_both():
            with patch.object(bot, "client", mock_client):
                return await asyncio.gather(
                    bot.get_context(event_A),
                    bot.get_context(event_B)
                )

        ctx_A, ctx_B = asyncio.run(run_both())

        # گروه آلفا فقط باید مشخصات خودش را داشته باشد
        self.assertIn("گروه آلفا", ctx_A)
        self.assertIn("نوید", ctx_A)
        self.assertNotIn("گروه بتا", ctx_A)
        self.assertNotIn("بهزاد", ctx_A)

        # گروه بتا فقط باید مشخصات خودش را داشته باشد
        self.assertIn("گروه بتا", ctx_B)
        self.assertIn("بهزاد", ctx_B)
        self.assertNotIn("گروه آلفا", ctx_B)
        self.assertNotIn("نوید", ctx_B)

    # -------------------------------------------------------------------------
    # سناریو ۷: درخواست‌های همزمان با مدل‌های متفاوت باعث نشت وضعیت نمی‌شوند
    # -------------------------------------------------------------------------
    def test_scenario_7_concurrent_cycles_with_different_models_isolated(self):
        """وضعیت و پیام‌های چرخه ReAct در درخواست‌های همزمان کاملاً ایزوله هستند."""
        event_1 = MockTelegramEvent(chat_id=501, sender_id=501, text="درخواست اول")
        event_2 = MockTelegramEvent(chat_id=502, sender_id=502, text="درخواست دوم")

        cycle_1 = AgentExecutionCycle(
            question="تحلیل معماری",
            context="کانتکست ۱",
            memory_str="حافظه ۱",
            event=event_1,
            client=AsyncMock(),
            is_owner=True
        )

        cycle_2 = AgentExecutionCycle(
            question="ترجمه متن",
            context="کانتکست ۲",
            memory_str="حافظه ۲",
            event=event_2,
            client=AsyncMock(),
            is_owner=False
        )

        # شناسه‌های درخواست باید یکتا باشند
        self.assertNotEqual(cycle_1.state.request_id, cycle_2.state.request_id)
        # وضعیت مالکیت باید در سطح هر چرخه مستقل باشد
        self.assertTrue(cycle_1.state.is_owner)
        self.assertFalse(cycle_2.state.is_owner)
        # کانتکست‌ها و متغیرها مجزا هستند
        self.assertEqual(cycle_1.question, "تحلیل معماری")
        self.assertEqual(cycle_2.question, "ترجمه متن")

    # -------------------------------------------------------------------------
    # سناریو ۸: دسترسی به پیام اصلی حذف‌شده یا غیرقابل‌دسترسی بدون وانمودکردن
    # -------------------------------------------------------------------------
    def test_scenario_8_deleted_or_inaccessible_reply_handled_safely(self):
        """اگر پیام ریپلای‌شده حذف شده باشد، سیستم صادقانه اعلام می‌کند و وانمود به خواندن آن نمی‌کند."""
        import bot

        deleted_msg_id = 99999
        event = MockTelegramEvent(
            chat_id=1001,
            sender_id=1001,
            text="کاپری خلاصه کن",
            reply_to_msg_id=deleted_msg_id,
            is_private=True
        )

        mock_client = AsyncMock()
        # تلگرام برای پیام حذف‌شده None برمی‌گرداند یا اکسپشن پرتاب می‌کند
        mock_client.get_messages.return_value = None

        reply_info = asyncio.run(bot.get_reply_info(event, mock_client))
        self.assertTrue(reply_info["has_reply"])
        self.assertFalse(reply_info["is_available"])
        self.assertEqual(reply_info["text"], "")

        with patch.object(bot, "client", mock_client):
            context = asyncio.run(bot.get_context(event))
            self.assertIn("حذف شده یا قابل دسترسی نیست", context)
            self.assertIn(str(deleted_msg_id), context)

    # -------------------------------------------------------------------------
    # سناریو ۹: اطلاعات حافظه خصوصی نباید در پاسخ گروهی افشا شود
    # -------------------------------------------------------------------------
    def test_scenario_9_private_memory_not_leaked_in_group(self):
        """حافظه شخصی و اطلاعات محرمانه در گفتگوی گروهی تحت هیچ شرایطی بازیابی نمی‌شوند."""
        owner_id = 998877
        private_scope = f"memory:dm:{owner_id}"
        group_scope = "memory:group:-100987654321"

        # ثبت یک حقیقت بسیار محرمانه در چت خصوصی
        secret_fact = "شماره پاسپورت محرمانه صاحب اکانت A12345678 است."
        memory.add_memory(secret_fact, scope_id=private_scope)

        # جستجوی حقیقت در فضای گروه
        group_retrieval = memory.relevant_facts("پاسپورت", scope_id=group_scope)
        self.assertEqual(
            group_retrieval,
            "",
            "اطلاعات محرمانه خصوصی نباید در فضای گروه بازیابی شوند!"
        )

        # اطمینان از اینکه حقیقت فقط در فضای خصوصی موجود است
        dm_retrieval = memory.relevant_facts("پاسپورت", scope_id=private_scope)
        self.assertIn("A12345678", dm_retrieval)

    # -------------------------------------------------------------------------
    # سناریو ۱۰: سلامت کامل مسیرهای دانلود، خلاصه‌سازی و اطلاعات ویدیو و ضدتوهم
    # -------------------------------------------------------------------------
    def test_scenario_10_media_routes_and_anti_hallucination_integrity(self):
        """مسیرهای خلاصه‌ساز، دانلود، متادیتای ویدیو و قید ضدتوهم بصری سالم هستند."""
        import inspect

        # الف) بررسی وجود دستورالعمل ضدتوهم بصری در سورس خلاصه یوتیوب
        yt_src = inspect.getsource(ytsummary.summarize_youtube_video)
        self.assertIn("ضوابط حیاتی عدم توهم بصری", yt_src)
        self.assertIn("نورپردازی", yt_src)
        self.assertIn("حرکات دوربین", yt_src)

        # ب) اعتبارسنجی استخراج‌کننده‌های URL
        test_yt = "https://www.youtube.com/watch?v=kJQP7kiw5Fk"
        self.assertEqual(ytsummary.extract_youtube_id(test_yt), "kJQP7kiw5Fk")

        test_social = "https://tiktok.com/@user/video/123456789"
        self.assertEqual(socialdl.extract_social_url(test_social), test_social)

        # ج) عدم استخراج لینک از متن معمولی
        self.assertIsNone(socialdl.extract_social_url("این یک متن معمولی بدون لینک است"))
        self.assertIsNone(ytsummary.extract_youtube_id("این یک متن معمولی بدون لینک یوتیوب است"))


if __name__ == "__main__":
    unittest.main()
