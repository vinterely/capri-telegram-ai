import asyncio
import os
import shutil
import sys
import tempfile
import time
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure root directory is on sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from ai_engine import agent
import bot
from core import memory
from ai_engine import tools
from services.search import webreader


class TestWebReaderSecurity(unittest.TestCase):
    def test_safe_urls(self):
        self.assertTrue(webreader._is_safe_url("https://example.com/test"))
        self.assertTrue(webreader._is_safe_url("http://google.com"))

    def test_blocked_urls(self):
        self.assertFalse(webreader._is_safe_url("file:///etc/passwd"))
        self.assertFalse(webreader._is_safe_url("ftp://example.com"))
        self.assertFalse(webreader._is_safe_url("http://localhost:8080"))
        self.assertFalse(webreader._is_safe_url("http://127.0.0.1:8000"))
        self.assertFalse(webreader._is_safe_url("http://10.0.0.1/admin"))
        self.assertFalse(webreader._is_safe_url("http://192.168.1.1/secret"))
        self.assertFalse(webreader._is_safe_url("http://169.254.169.254/latest/meta-data/"))

    def test_blocked_ipv6(self):
        self.assertFalse(webreader._is_safe_url("http://[::1]/x"))
        self.assertFalse(webreader._is_safe_url("http://[fe80::1]/x"))
        self.assertFalse(webreader._is_safe_url("http://[::ffff:127.0.0.1]/x"))


class TestSkillSecurity(unittest.TestCase):
    def test_validate_rejects_dangerous_code(self):
        from ai_engine import skills_manager
        bad_samples = [
            "import os\nasync def execute(a,c,e):\n    os.system('id')",
            "import subprocess\nasync def execute(a,c,e):\n    return 'x'",
            "import socket\nasync def execute(a,c,e):\n    return 'x'",
            "import pathlib\nasync def execute(a,c,e):\n    return 'x'",
            "async def execute(a,c,e):\n    return eval('1')",
            "async def execute(a,c,e):\n    return exec('1')",
            "async def execute(a,c,e):\n    return open('/x').read()",
            "async def execute(a,c,e):\n    return __import__('os')",
            "async def execute(a,c,e):\n    x = ().__class__\n    return 'x'",
        ]
        for code in bad_samples:
            self.assertTrue(skills_manager._validate_skill_code(code), code)

    def test_validate_allows_simple_code(self):
        from ai_engine import skills_manager
        good = "import requests\n\nasync def execute(args, client, event):\n    return 'ok'"
        self.assertEqual(skills_manager._validate_skill_code(good), "")


class TestStrangerSecurity(unittest.IsolatedAsyncioTestCase):
    def test_stranger_rate_limit(self):
        uid = 999999
        bot._stranger_hits.pop(uid, None)
        for _ in range(6):
            self.assertTrue(bot._stranger_rate_ok(uid, limit=6, window=60))
        self.assertFalse(bot._stranger_rate_ok(uid, limit=6, window=60))

    async def test_stranger_tool_gate(self):
        event = MagicMock()
        event.out = False
        client = MagicMock()
        # "create_or_update_skill" is not in STRANGER_ALLOWED_TOOLS
        res = await tools.execute_tool("create_or_update_skill", {"name": "test"}, event, client)
        self.assertIn("فقط برای صاحب اکانت فعال است", res)


class TestStrangerCaps(unittest.TestCase):
    def test_daily_cap(self):
        uid = 111111
        bot._stranger_hits.pop(uid, None)
        bot._stranger_daily.pop(uid, None)
        bot._global_daily[:] = []
        old = bot.STRANGER_DAILY_LIMIT
        bot.STRANGER_DAILY_LIMIT = 3
        try:
            for _ in range(3):
                self.assertTrue(bot._stranger_rate_ok(uid, limit=1000, window=60))
            self.assertFalse(bot._stranger_rate_ok(uid, limit=1000, window=60))
        finally:
            bot.STRANGER_DAILY_LIMIT = old

    def test_global_daily_cap(self):
        bot._stranger_hits.clear()
        bot._stranger_daily.clear()
        bot._global_daily[:] = []
        old = bot.STRANGER_GLOBAL_DAILY_LIMIT
        bot.STRANGER_GLOBAL_DAILY_LIMIT = 2
        try:
            self.assertTrue(bot._stranger_rate_ok(1, limit=1000, window=60))
            self.assertTrue(bot._stranger_rate_ok(2, limit=1000, window=60))
            self.assertFalse(bot._stranger_rate_ok(3, limit=1000, window=60))
        finally:
            bot.STRANGER_GLOBAL_DAILY_LIMIT = old


class TestPendingTTL(unittest.TestCase):
    def test_take_pending_expires(self):
        bot.pending.clear()
        bot.pending["123"] = {"kind": "confirm_clear_memory"}
        bot.pending["123"]["ts"] = time.time() - 200  # Simulate expiration
        self.assertIsNone(bot._take_pending("123"))
        self.assertNotIn("123", bot.pending)

    def test_take_pending_fresh(self):
        bot.pending.clear()
        bot.pending["456"] = {"kind": "confirm_clear_memory"}
        p = bot._take_pending("456")
        self.assertIsNotNone(p)
        self.assertEqual(p["kind"], "confirm_clear_memory")
        self.assertNotIn("456", bot.pending)


class TestConfirmMatching(unittest.TestCase):
    def test_whole_token_no_substring_false_positive(self):
        self.assertFalse(bot._answer_yes("پاره"))  # Contains substring but not standalone token
        self.assertFalse(bot._answer_yes("آب نبات"))

    def test_negation_first(self):
        self.assertFalse(bot._answer_yes("نه"))
        self.assertFalse(bot._answer_yes("آره نه"))
        self.assertFalse(bot._answer_yes("تایید نمیکنم"))

    def test_positive(self):
        self.assertTrue(bot._answer_yes("آره"))
        self.assertTrue(bot._answer_yes("بله حتما"))

    def test_normalize_persian_variants(self):
        self.assertEqual(bot._normalize_fa("ت\u0627\u064a\u064a\u062f"), "تایید")  # ي عربی → ی
        self.assertEqual(bot._normalize_fa("پ\u0643"), "پک")  # ك عربی → ک
        self.assertEqual(bot._normalize_fa("بی\u200cخیال"), "بی خیال")  # نیم‌فاصله → فاصله
        self.assertTrue(bot._answer_yes("ت\u0627\u064a\u064a\u062f"))


class TestCircuitBreaker(unittest.TestCase):
    def test_circuit_breaker(self):
        cb = agent.CircuitBreaker(failure_threshold=2, window_seconds=5, cooldown_seconds=10)
        key = "test_srv:test_mod"
        self.assertTrue(cb.is_available(key))
        cb.record_failure(key)
        self.assertTrue(cb.is_available(key))
        cb.record_failure(key)
        self.assertFalse(cb.is_available(key))
        cb.record_success(key)
        self.assertTrue(cb.is_available(key))


class TestMemoryDeduplication(unittest.TestCase):
    def test_jaccard_dedup(self):
        toks1 = {"کاربر", "علاقه‌مند", "پایتون", "هوشمند"}
        toks2 = {"کاربر", "علاقه‌مند", "پایتون", "هوشمند"}
        self.assertAlmostEqual(memory._jaccard(toks1, toks2), 1.0)
        toks3 = {"کاملاً", "موضوع", "متفاوت"}
        self.assertEqual(memory._jaccard(toks1, toks3), 0.0)


class TestRouterRegex(unittest.TestCase):
    def test_leave_command_vs_question(self):
        cmd = "از کانال‌های خبری لفت بزن"
        info = "چطوری از گیجی لفت بدم؟"
        
        IS_INFO_QUESTION_cmd = any(q in cmd for q in ("چطور", "چطوری", "چگونه", "چرا"))
        IS_INFO_QUESTION_info = any(q in info for q in ("چطور", "چطوری", "چگونه", "چرا"))
        
        self.assertFalse(IS_INFO_QUESTION_cmd)
        self.assertTrue(IS_INFO_QUESTION_info)

    def test_sort_command_vs_question(self):
        import re
        cmd = "کانال‌ها رو مرتب کن"
        info = "چطوری مرتب کنم؟"
        
        pat = r"^(?:کانال(?:‌ها|ها)?\s*(?:رو\s*)?)?(?:مرتب|دسته‌بندی|دسته\s*بندی)\s*(?:کن|شون\s*کن)$"
        self.assertIsNotNone(re.search(pat, cmd.strip()))
        self.assertIsNone(re.search(pat, info.strip()))


class TestAgentExecution(unittest.IsolatedAsyncioTestCase):
    async def test_agent_final_step_forces_no_tools(self):
        event = MagicMock()
        event.out = True
        client = MagicMock()
        
        with patch("ai_engine.agent._call_model_step") as mock_step:
            # Step 0: returns empty tool_calls with content
            mock_step.return_value = {"content": "پاسخ نهایی تستی", "tool_calls": []}
            res = await agent.run_agent("تست سوال", "", "", event, client, max_steps=2)
            self.assertEqual(res, "پاسخ نهایی تستی")

    async def test_tool_duplicate_memoization(self):
        # Verify executed_calls cache logic within agent
        event = MagicMock()
        event.out = True
        client = MagicMock()

        tc1 = {
            "id": "c1",
            "function": {"name": "calculate", "arguments": '{"expr": "2+2"}'}
        }
        tc2 = {
            "id": "c2",
            "function": {"name": "calculate", "arguments": '{"expr": "2+2"}'}
        }
        with patch("ai_engine.agent._call_model_step") as mock_step, \
             patch("ai_engine.tools.execute_tool", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = "4"
            # Return tool calls on step 0, then final answer on step 1
            mock_step.side_effect = [
                {"content": "", "tool_calls": [tc1, tc2]},
                {"content": "جواب ۴ است", "tool_calls": []}
            ]
            res = await agent.run_agent("حساب کن", "", "", event, client, max_steps=3)
            # execute_tool should only be called once because the second call has identical arguments!
            self.assertEqual(mock_exec.call_count, 1)


class TestPendingConfirmations(unittest.IsolatedAsyncioTestCase):
    async def test_confirm_clear_memory_yes(self):
        event = AsyncMock()
        event.reply = AsyncMock()
        with patch("core.memory.clear_memory") as mock_clear:
            await bot._answer_pending(event, {"kind": "confirm_clear_memory"}, "آره پاک کن")
            mock_clear.assert_called_once()
            event.reply.assert_called_with("🗑 تمام حافظه ماندگار کاپری پاک شد.")

    async def test_confirm_clear_memory_no(self):
        event = AsyncMock()
        event.reply = AsyncMock()
        with patch("core.memory.clear_memory") as mock_clear:
            await bot._answer_pending(event, {"kind": "confirm_clear_memory"}, "نه بیخیال")
            mock_clear.assert_not_called()
            event.reply.assert_called_with("باشه، پاک‌کردن حافظه لغو شد.")

    async def test_confirm_leave_single_yes(self):
        event = AsyncMock()
        event.reply = AsyncMock()
        mock_dialog = MagicMock()
        with patch("services.telegram.channels.leave_dialogs", new_callable=AsyncMock) as mock_leave:
            mock_leave.return_value = ["بروز نیوز"]
            await bot._answer_pending(event, {"kind": "confirm_leave_single", "dialog": mock_dialog, "name": "بروز نیوز"}, "اره")
            mock_leave.assert_called_once()
            event.reply.assert_called_with("✅ از «بروز نیوز» لفت دادم.")

    async def test_confirm_leave_single_no(self):
        event = AsyncMock()
        event.reply = AsyncMock()
        with patch("services.telegram.channels.leave_dialogs", new_callable=AsyncMock) as mock_leave:
            await bot._answer_pending(event, {"kind": "confirm_leave_single", "dialog": MagicMock(), "name": "بروز نیوز"}, "نه")
            mock_leave.assert_not_called()
            event.reply.assert_called_with("باشه، لفت دادن لغو شد.")


class TestToolCallTextExtraction(unittest.TestCase):
    def test_extract_json_tool_call(self):
        sample = '{"tool": "download_youtube_video", "arguments": {"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "quality": "720p"}}'
        tc = agent._extract_tool_calls_from_text(sample)
        self.assertEqual(len(tc), 1)
        self.assertEqual(tc[0]["function"]["name"], "download_youtube_video")
        args = agent.json.loads(tc[0]["function"]["arguments"])
        self.assertEqual(args["quality"], "720p")
        self.assertEqual(args["url"], "https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    def test_extract_invalid_tool_skipped(self):
        sample = '{"tool": "non_existent_tool_xyz", "arguments": {}}'
        tc = agent._extract_tool_calls_from_text(sample)
        self.assertEqual(len(tc), 0)

    def test_extract_rejects_natural_language_with_json(self):
        # Prose mixed with JSON should not trigger tool extraction (closing prompt injection vectors)
        sample = 'رفیق برات شروع می‌کنم 🎬\n\n{"tool": "download_youtube_video", "arguments": {"url": "https://x.com/1"}}'
        self.assertEqual(agent._extract_tool_calls_from_text(sample), [])

    def test_extract_rejects_non_json_text(self):
        self.assertEqual(agent._extract_tool_calls_from_text("فقط یک متن ساده"), [])


class TestGhostCollectSamples(unittest.IsolatedAsyncioTestCase):
    async def test_collect_samples_skips_edited_messages(self):
        from datetime import datetime, timezone
        from services.social import ghost

        mock_dialog = MagicMock()
        mock_dialog.id = 12345

        msg_normal = MagicMock()
        msg_normal.out = True
        msg_normal.text = "سلام داداش کجایی؟"
        msg_normal.edit_date = None

        msg_edited = MagicMock()
        msg_edited.out = True
        msg_edited.text = "پاسخ هوش مصنوعی به کاربر"
        msg_edited.edit_date = datetime.now(timezone.utc)

        msg_in = MagicMock()
        msg_in.out = False
        msg_in.text = "سلام"
        msg_in.edit_date = None

        client = MagicMock()

        async def mock_iter_dialogs(limit=60):
            yield mock_dialog

        async def mock_iter_messages(chat_id, limit=15):
            for m in [msg_normal, msg_edited, msg_in]:
                yield m

        client.iter_dialogs = mock_iter_dialogs
        client.iter_messages = mock_iter_messages

        samples = await ghost.collect_samples(client, limit=10)
        self.assertIn("سلام داداش کجایی؟", samples)
        self.assertNotIn("پاسخ هوش مصنوعی به کاربر", samples)
        self.assertEqual(len(samples), 1)


class TestAINavigation(unittest.IsolatedAsyncioTestCase):
    def test_parse_choice_numbers_and_persian(self):
        from services.media import ai_nav

        b1 = MagicMock(text="فصل اول")
        b2 = MagicMock(text="فصل دوم")
        b3 = MagicMock(text="فصل سوم")
        buttons = [b1, b2, b3]

        self.assertEqual(ai_nav.parse_choice("2", buttons), 1)
        self.assertEqual(ai_nav.parse_choice("گزینه ۲", buttons), 1)
        self.assertEqual(ai_nav.parse_choice("دکمه 3 رو بزن", buttons), 2)
        self.assertIsNone(ai_nav.parse_choice("0", buttons))
        self.assertIsNone(ai_nav.parse_choice("اتمام", buttons))
        self.assertIsNone(ai_nav.parse_choice("9", buttons))  # out of bounds

    def test_parse_choice_text_fallback(self):
        from services.media import ai_nav

        b1 = MagicMock(text="دانلود مستقیم")
        b2 = MagicMock(text="فصل ششم")
        buttons = [b1, b2]

        self.assertEqual(ai_nav.parse_choice("فصل ششم رو بزن", buttons), 1)
        self.assertEqual(ai_nav.parse_choice("روی دانلود مستقیم کلیک کن", buttons), 0)

    async def test_ai_pick_button_async(self):
        from services.media import ai_nav

        b1 = MagicMock(text="فصل اول")
        b2 = MagicMock(text="فصل دوم")
        buttons = [b1, b2]
        req = {"title": "زخم کاری", "season": 2, "episode": "all", "quality": 720}
        state = {"files_count": 0, "last_action": "شروع"}

        with patch("ai_engine.ai.ask_direct", return_value="2") as mock_ask:
            choice = await ai_nav.ai_pick_button(buttons, "منوی فصل‌ها", req, state)
            self.assertEqual(choice, 1)
            mock_ask.assert_called_once()
            prompt_arg = mock_ask.call_args[0][0]
            self.assertIn("زخم کاری", prompt_arg)
            self.assertIn("فصل 2", prompt_arg)
            self.assertIn("1. [فصل اول]", prompt_arg)
            self.assertIn("2. [فصل دوم]", prompt_arg)


class TestDNDAndReminders(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        from services.social import dnd
        self.dnd = dnd
        self.orig_dnd_file = dnd.DND_FILE
        self.orig_rem_file = dnd.REMINDERS_FILE
        dnd.DND_FILE = dnd.DND_FILE + ".test"
        dnd.REMINDERS_FILE = dnd.REMINDERS_FILE + ".test"
        dnd._pv_cooldown.clear()
        dnd._group_cooldown.clear()
        if os.path.exists(dnd.DND_FILE):
            os.remove(dnd.DND_FILE)
        if os.path.exists(dnd.REMINDERS_FILE):
            os.remove(dnd.REMINDERS_FILE)

    def tearDown(self):
        if os.path.exists(self.dnd.DND_FILE):
            os.remove(self.dnd.DND_FILE)
        if os.path.exists(self.dnd.REMINDERS_FILE):
            os.remove(self.dnd.REMINDERS_FILE)
        self.dnd.DND_FILE = self.orig_dnd_file
        self.dnd.REMINDERS_FILE = self.orig_rem_file

    def test_parse_time_and_reason(self):
        from datetime import datetime
        now = datetime(2026, 10, 25, 4, 0)
        dt, s = self.dnd.parse_time_expression("تا ساعت ۱۴ سر کلاسم", now)
        self.assertIsNotNone(dt)
        self.assertEqual(dt.hour, 14)
        self.assertEqual(s, "ساعت 14:00")

        reason = self.dnd.extract_dnd_reason("تا ساعت ۱۴ سر کلاسم")
        self.assertEqual(reason, "کلاس و دانشگاه")

    def test_urgent_detection(self):
        self.assertTrue(self.dnd.is_urgent_message("سلام توروخدا خیلی واجبه جواب بده"))
        self.assertTrue(self.dnd.is_urgent_message("کار اورژانسی پیش اومده"))
        self.assertFalse(self.dnd.is_urgent_message("سلام خوبی کجایی؟"))

    def test_dnd_activation_lifecycle(self):
        self.assertFalse(self.dnd.is_dnd_active())
        self.dnd.activate_dnd("خواب", time.time() + 3600, "ساعت بعد")
        self.assertTrue(self.dnd.is_dnd_active())
        info = self.dnd.get_dnd_info()
        self.assertEqual(info["reason"], "خواب")
        self.dnd.deactivate_dnd()
        self.assertFalse(self.dnd.is_dnd_active())

    def test_reminders_crud(self):
        self.assertEqual(len(self.dnd.load_reminders()), 0)
        self.dnd.add_reminder("خرید نان", time.time() + 1000, "ساعت ۱۰")
        rems = self.dnd.load_reminders()
        self.assertEqual(len(rems), 1)
        self.assertEqual(rems[0]["text"], "خرید نان")
        self.dnd.clear_all_reminders()
        self.assertEqual(len(self.dnd.load_reminders()), 0)

    async def test_pv_auto_reply_and_report(self):
        self.dnd.activate_dnd("کلاس دانشگاه", time.time() + 3600, "ساعت ۱۴")
        event = AsyncMock()
        event.sender_id = 999
        event.raw_text = "سلام کجایی کار دارم"
        sender = MagicMock()
        sender.first_name = "علی"
        sender.username = "ali99"
        sender.bot = False
        event.get_sender = AsyncMock(return_value=sender)
        event.reply = AsyncMock()

        client = AsyncMock()
        handled = await self.dnd.handle_incoming_pv(event, client)
        self.assertTrue(handled)
        event.reply.assert_called_once()
        reply_arg = event.reply.call_args[0][0]
        self.assertIn("کلاس دانشگاه", reply_arg)
        client.send_message.assert_called_once()
        me_arg = client.send_message.call_args[0][0]
        report_text = client.send_message.call_args[0][1]
        self.assertEqual(me_arg, "me")
        self.assertIn("علی", report_text)
        self.assertIn("چت خصوصی", report_text)

    async def test_group_auto_reply_and_report(self):
        self.dnd.activate_dnd("امتحان مدار", time.time() + 3600, "ساعت ۱۶")
        event = AsyncMock()
        event.chat_id = -100123456
        event.sender_id = 888
        event.mentioned = True
        event.reply_to_msg_id = None
        event.raw_text = "کجایی بیا پروژه رو بفرست"

        sender = MagicMock()
        sender.first_name = "سارا"
        sender.username = "sara_dev"
        sender.bot = False
        event.get_sender = AsyncMock(return_value=sender)
        event.reply = AsyncMock()

        chat = MagicMock()
        chat.title = "گروه برنامه‌نویسی"
        event.get_chat = AsyncMock(return_value=chat)

        client = AsyncMock()
        client.get_me = AsyncMock(return_value=MagicMock(id=111))

        handled = await self.dnd.handle_incoming_group_mention(event, client)
        self.assertTrue(handled)
        event.reply.assert_called_once()
        group_reply_text = event.reply.call_args[0][0]
        self.assertIn("امتحان مدار", group_reply_text)
        client.send_message.assert_called_once()
        report = client.send_message.call_args[0][1]
        self.assertIn("گروه «گروه برنامه‌نویسی»", report)
        self.assertIn("سارا", report)

    def test_clean_reminder_text_preserves_prepositions(self):
        res = self.dnd.clean_reminder_text("کاپری ساعت ۱۰ یادم بنداز که به علی زنگ بزنم")
        self.assertEqual(res, "به علی زنگ بزنم")

    def test_dashboard_status(self):
        dash = self.dnd.get_dashboard_status("۲ ساعت", "Mercury-3", "دلارا")
        self.assertIn("داشبورد وضعیت", dash)
        self.assertIn("Mercury-3", dash)
        self.assertIn("دلارا", dash)

    def test_reminder_clear_and_list_recognition(self):
        # تست تشخیص دقیق دستورات حذف یادآور
        clear_phrases = [
            "پاک کردن یادآورها",
            "یادآور رو پاک کن",
            "یادآورا رو پاک کن",
            "یادآورها رو پاک کن",
            "حذف یادآورها",
            "یادآورها رو حذف کن",
            "ریمایندرها رو پاک کن",
            "آلارم رو پاک کن",
            "یادآور اول رو پاک کن",
        ]
        for phrase in clear_phrases:
            self.assertTrue(self.dnd.is_reminder_clear_command(phrase), f"Failed for: {phrase}")
            # نباید اشتباهاً به عنوان لیست شناخته شود
            self.assertFalse(self.dnd.is_reminder_list_command(phrase), f"Wrongly recognized as list: {phrase}")

        # تست دستورات مشاهده لیست
        list_phrases = [
            "لیست یادآورها",
            "یادآورام چیه",
            "یادآورهای فعال",
            "یادآورها",
        ]
        for phrase in list_phrases:
            self.assertTrue(self.dnd.is_reminder_list_command(phrase), f"Failed list for: {phrase}")

        # تست استخراج اندیس
        self.assertEqual(self.dnd.extract_reminder_target_index("یادآور ۱ رو پاک کن"), 1)
        self.assertEqual(self.dnd.extract_reminder_target_index("یادآور اول رو پاک کن"), 1)
        self.assertEqual(self.dnd.extract_reminder_target_index("یادآور دوم رو حذف کن"), 2)
        self.assertIsNone(self.dnd.extract_reminder_target_index("پاک کردن یادآورها"))

    async def test_handle_owner_command_reminder_clear_flow(self):
        # ثبت دو یادآور آزمایشی
        self.dnd.add_reminder("یادآور شماره یک", time.time() + 1000, "۱ ساعت دیگر")
        self.dnd.add_reminder("یادآور شماره دو", time.time() + 2000, "۲ ساعت دیگر")
        self.assertEqual(len(self.dnd.load_reminders()), 2)

        event = AsyncMock()
        status = AsyncMock()

        # تست ۱: دستور «پاک کردن یادآورها» باید مستقیماً پاک کند و وارد لیست نشود
        handled = await self.dnd.handle_owner_command(event, status, "کاپری پاک کردن یادآورها")
        self.assertTrue(handled)
        status.edit.assert_called()
        self.assertIn("پاک شدند", status.edit.call_args[0][0])
        self.assertEqual(len(self.dnd.load_reminders()), 0)

        # تست ۲: حال که خالی است، مشاهده لیست باید صف خالی اعلام کند
        status.reset_mock()
        handled = await self.dnd.handle_owner_command(event, status, "کاپری لیست یادآورها")
        self.assertTrue(handled)
        self.assertIn("هیچ یادآور فعالی", status.edit.call_args[0][0])

        # تست ۳: ثبت یک یادآور و سپس حذف با «یادآور رو پاک کن»
        self.dnd.add_reminder("تست سینگل", time.time() + 1000, "۱ ساعت دیگر")
        self.assertEqual(len(self.dnd.load_reminders()), 1)
        status.reset_mock()
        handled = await self.dnd.handle_owner_command(event, status, "کاپری یادآور رو پاک کن")
        self.assertTrue(handled)
        self.assertEqual(len(self.dnd.load_reminders()), 0)


class TestVaultOrganizer(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        from services.telegram import vault
        self.vault = vault
        self.test_dir = tempfile.mkdtemp()
        self.orig_vault_file = vault.VAULT_FILE
        vault.VAULT_FILE = os.path.join(self.test_dir, "test_vault.json")

    def tearDown(self):
        self.vault.VAULT_FILE = self.orig_vault_file
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_vault_command_detection_and_parsing(self):
        self.assertTrue(self.vault.is_vault_command("کاپری مرتب کن سیو مسیج"))
        self.assertTrue(self.vault.is_vault_command("کاپری سیو مسیج مرتب کن ۱۰ پیام"))
        self.assertTrue(self.vault.is_vault_command("کاپری وضعیت صندوق"))
        self.assertTrue(self.vault.is_vault_command("کاپری ۵۰۰ پیام سیومسیج رو دسته‌بندی کن"))
        self.assertFalse(self.vault.is_vault_command("کاپری وضعیت"))
        self.assertFalse(self.vault.is_vault_command("سلام چطوری"))

        self.assertEqual(self.vault.parse_vault_command_limit("کاپری مرتب کن سیو مسیج ۱۰ تا"), 10)
        self.assertEqual(self.vault.parse_vault_command_limit("کاپری مرتب کن سیو مسیج ۵۰۰ پیام"), 500)
        self.assertEqual(self.vault.parse_vault_command_limit("کاپری ۱۰۰۰ پیام سیو مسیج تفکیک کن"), 1000)
        self.assertEqual(self.vault.parse_vault_command_limit("کاپری همه سیو مسیج رو مرتب کن"), -1)
        self.assertEqual(self.vault.parse_vault_command_limit("کاپری مرتب کن سیو مسیج"), 20)

    def test_classify_message_heuristic(self):
        # 1. Code
        code_msg = MagicMock()
        code_msg.raw_text = "```python\ndef hello():\n    return 'world'\n```"
        code_msg.file = None
        code_msg.voice = None
        code_msg.video = None
        code_msg.entities = []
        cat, conf = self.vault.classify_message_heuristic(code_msg)
        self.assertEqual(cat, "code")

        # 2. Media
        media_msg = MagicMock()
        media_msg.raw_text = "دانلود فیلم سینمایی Inception 1080p با زیرنویس چسبیده"
        media_msg.file = None
        media_msg.voice = None
        media_msg.video = None
        media_msg.entities = []
        cat, conf = self.vault.classify_message_heuristic(media_msg)
        self.assertEqual(cat, "media")

        # 3. Music
        music_msg = MagicMock()
        music_msg.raw_text = "آهنگ جدید شادمهر عقیلی موزیک ویدیو"
        music_msg.file = None
        music_msg.voice = None
        music_msg.video = None
        music_msg.entities = []
        cat, conf = self.vault.classify_message_heuristic(music_msg)
        self.assertEqual(cat, "music")

        # 4. Files
        doc_msg = MagicMock()
        doc_msg.raw_text = "جزوه مدار منطقی دکتر حسینی"
        doc_file = MagicMock()
        doc_file.name = "modar.pdf"
        doc_file.mime_type = "application/pdf"
        doc_msg.file = doc_file
        doc_msg.voice = None
        doc_msg.video = None
        doc_msg.entities = []
        cat, conf = self.vault.classify_message_heuristic(doc_msg)
        self.assertEqual(cat, "files")

        # 5. Personal
        personal_msg = MagicMock()
        personal_msg.raw_text = "شماره شبا من: IR120560000000000000000000"
        personal_msg.file = None
        personal_msg.voice = None
        personal_msg.video = None
        personal_msg.entities = []
        cat, conf = self.vault.classify_message_heuristic(personal_msg)
        self.assertEqual(cat, "personal")

        # 6. Gaming keywords
        game_msg = MagicMock()
        game_msg.raw_text = "دانلود بازی خدای جنگ God of War برای کامپیوتر نسخه کرک شده با لینک مستقیم"
        game_msg.file = None
        game_msg.voice = None
        game_msg.video = None
        game_msg.entities = []
        cat, conf = self.vault.classify_message_heuristic(game_msg)
        self.assertEqual(cat, "gaming")

        # 7. Gaming extensions (.xapk)
        xapk_msg = MagicMock()
        xapk_msg.raw_text = "فایل نصبی"
        xapk_file = MagicMock()
        xapk_file.name = "gta_san_andreas.xapk"
        xapk_file.mime_type = "application/octet-stream"
        xapk_msg.file = xapk_file
        xapk_msg.voice = None
        xapk_msg.video = None
        xapk_msg.entities = []
        cat, conf = self.vault.classify_message_heuristic(xapk_msg)
        self.assertEqual(cat, "gaming")

        # 8. Gaming channel title context
        appduny_msg = MagicMock()
        appduny_msg.raw_text = "نسخه ۱.۵ بدون مشکل اجرا شد"
        appduny_msg.file = None
        appduny_msg.voice = None
        appduny_msg.video = None
        appduny_msg.entities = []
        cat, conf = self.vault.classify_message_heuristic(appduny_msg, chat_title="دانلود بازی - اپدونی | AppDuny")
        self.assertEqual(cat, "gaming")

    async def test_album_sibling_resolution_and_forwarding(self):
        client = AsyncMock()

        # Mock album messages sharing the same grouped_id
        target_msg = MagicMock()
        target_msg.id = 8191
        target_msg.grouped_id = 123456789
        target_msg.raw_text = ""
        target_msg.peer_id = 999

        sib1 = MagicMock(id=8190, grouped_id=123456789, raw_text="دانلود بازی Resident Evil 4 Remake")
        sib2 = target_msg
        sib3 = MagicMock(id=8192, grouped_id=123456789, raw_text="")
        other = MagicMock(id=8189, grouped_id=987654321, raw_text="دیگری")

        client.get_messages = AsyncMock(return_value=[other, sib1, sib2, sib3])

        album = await self.vault.get_album_messages(client, target_msg)
        self.assertEqual(len(album), 3)
        self.assertEqual([m.id for m in album], [8190, 8191, 8192])

        # Test forwarding entire album via forward_to_topic
        vault_entity = MagicMock()
        ok = await self.vault.forward_to_topic(client, vault_entity, target_msg, topic_id=5, album_ids=[8190, 8191, 8192])
        self.assertTrue(ok)

    async def test_ensure_vault_group_reuse_and_create(self):
        client = AsyncMock()

        # Case A: First run provisioning (no existing group)
        created_chat = MagicMock()
        created_chat.id = -100999888
        res = MagicMock()
        res.chats = [created_chat]
        client.return_value = res  # for CreateChannelRequest call

        inv_res = MagicMock()
        inv_res.link = "https://t.me/+AbCdEf"
        client.side_effect = lambda req: (
            res if hasattr(req, "title") and "Capri Vault" in getattr(req, "title", "")
            else (inv_res if "ExportChatInviteRequest" in type(req).__name__ else MagicMock())
        )

        group_id, link = await self.vault.ensure_vault_group(client)
        self.assertEqual(group_id, -100999888)

        # Case B: Subsequent run reusing existing group
        client.get_entity = AsyncMock(return_value=created_chat)
        group_id_2, _ = await self.vault.ensure_vault_group(client)
        self.assertEqual(group_id_2, -100999888)

    async def test_organize_saved_messages_flow(self):
        client = AsyncMock()
        client.get_input_entity = AsyncMock(return_value=MagicMock())

        # Mock test vault group in database
        data = self.vault.load_vault_data()
        data["group_id"] = -100555444
        data["group_invite_link"] = "https://t.me/+test"
        data["topics"] = {
            "code": {"id": 10, "title": "💻 کد و برنامه‌نویسی"},
            "media": {"id": 20, "title": "🎬 فیلم و سریال"},
            "misc": {"id": 1, "title": "📦 متفرقه و سایر"},
        }
        self.vault.save_vault_data(data)

        client.get_entity = AsyncMock(return_value=MagicMock(id=-100555444))

        # Mock two sample messages in Saved Messages
        msg1 = MagicMock()
        msg1.id = 101
        msg1.raw_text = "def calculate_sum(a, b):\n    return a + b"
        msg1.file = None
        msg1.voice = None
        msg1.video = None
        msg1.entities = []

        msg2 = MagicMock()
        msg2.id = 102
        msg2.raw_text = "فیلم سینمایی بتمن کیفیت 1080p"
        msg2.file = None
        msg2.voice = None
        msg2.video = None
        msg2.entities = []

        async def fake_iter(*args, **kwargs):
            for m in [msg1, msg2]:
                yield m

        client.iter_messages = fake_iter

        client.side_effect = None
        client.return_value = MagicMock()

        rep = await self.vault.organize_saved_messages(client, limit=10)
        self.assertEqual(rep["total"], 2)
        self.assertIn("💻 کد و برنامه‌نویسی", rep["by_topic"])
        self.assertIn("🎬 فیلم و سریال", rep["by_topic"])

        # Verify processed message IDs are stored in local registry
        saved_data = self.vault.load_vault_data()
        self.assertIn(101, saved_data["processed_msg_ids"])
        self.assertIn(102, saved_data["processed_msg_ids"])
        self.assertEqual(saved_data["total_organized_count"], 2)

    async def test_vault_tools_execution(self):
        event = MagicMock()
        event.out = True
        client = AsyncMock()

        # Check status query when vault is uninitialized
        res1 = await tools.execute_tool("get_vault_info", {}, event, client)
        self.assertIn("هنوز صندوق هوشمند ایجاد نشده است", res1)

        # Deny non-owner access
        stranger_event = MagicMock()
        stranger_event.out = False
        res_denied = await tools.execute_tool("organize_saved_messages", {}, stranger_event, client)
        self.assertIn("صاحب اکانت", res_denied)

    async def test_purge_vault_messages(self):
        client = AsyncMock()
        client.get_input_entity = AsyncMock(return_value=MagicMock())

        # Prepare local database
        data = self.vault.load_vault_data()
        data["group_id"] = -100777888
        data["processed_msg_ids"] = [10, 11, 12]
        data["total_organized_count"] = 3
        self.vault.save_vault_data(data)

        # Mock messages: topic creation action (preserve), msg 1 (preserve), 2 content messages
        topic_create_msg = MagicMock()
        topic_create_msg.id = 2
        topic_create_msg.action = MagicMock()  # action message!

        root_msg = MagicMock()
        root_msg.id = 1
        root_msg.action = None

        content_msg1 = MagicMock()
        content_msg1.id = 50
        content_msg1.action = None

        content_msg2 = MagicMock()
        content_msg2.id = 51
        content_msg2.action = None

        async def fake_vault_iter(*args, **kwargs):
            for m in [topic_create_msg, content_msg2, content_msg1, root_msg]:
                yield m

        client.iter_messages = fake_vault_iter
        client.delete_messages = AsyncMock()

        # Case A: Full purge
        res = await self.vault.purge_vault_messages(client, limit=-1)
        self.assertEqual(res["deleted"], 2)  # Only content_msg1 and content_msg2 are deleted
        client.delete_messages.assert_called_once()
        deleted_ids = client.delete_messages.call_args[0][1]
        self.assertEqual(set(deleted_ids), {50, 51})

        # Verify cache reset
        updated_data = self.vault.load_vault_data()
        self.assertEqual(updated_data["processed_msg_ids"], [])
        self.assertEqual(updated_data["total_organized_count"], 0)

    async def test_purge_and_reorganize_command_handling(self):
        self.assertTrue(self.vault.is_vault_command("کاپری صندوق پاکسازی کن"))
        self.assertTrue(self.vault.is_vault_command("کاپری 50 پیام اخیر صندوق پاکسازی کن"))
        self.assertTrue(self.vault.is_vault_command("کاپری دوباره مرتب کن صندوقو"))

        event = AsyncMock()
        event.client = AsyncMock()
        status = AsyncMock()

        # Purge via handle_vault_command dispatch
        data = self.vault.load_vault_data()
        data["group_id"] = -100777888
        self.vault.save_vault_data(data)

        with patch.object(self.vault, "purge_vault_messages", new_callable=AsyncMock) as mock_purge:
            mock_purge.return_value = {"deleted": 50, "is_full_reset": False}
            handled = await self.vault.handle_vault_command(event, status, "کاپری 50 پیام اخیر صندوق پاکسازی کن")
            self.assertTrue(handled)
            mock_purge.assert_called_once_with(event.client, limit=50, status_callback=unittest.mock.ANY)

        with patch.object(self.vault, "organize_saved_messages", new_callable=AsyncMock) as mock_org:
            mock_org.return_value = {"total": 50, "by_topic": {"کد": 20}, "vault_link": ""}
            handled = await self.vault.handle_vault_command(event, status, "کاپری دوباره مرتب کن صندوقو")
            self.assertTrue(handled)
            mock_org.assert_called_once()
            self.assertTrue(mock_org.call_args[1].get("force_all"))


class TestAgentContextGrounding(unittest.IsolatedAsyncioTestCase):
    async def test_build_environment_context_saved_messages(self):
        from ai_engine import agent
        client = AsyncMock()
        client.get_me = AsyncMock(return_value=MagicMock(id=123456))
        event = MagicMock()
        event.chat_id = 123456
        event.is_private = True
        event.reply_to_msg_id = None

        ctx = await agent.build_environment_context(event, client)
        self.assertIn("Saved Messages", ctx)
        self.assertIn("پیام‌های ذخیره‌شده", ctx)

    async def test_build_environment_context_group_and_reply(self):
        from ai_engine import agent
        client = AsyncMock()
        client.get_me = AsyncMock(return_value=MagicMock(id=123456))
        event = AsyncMock()
        event.chat_id = -100987654
        event.is_private = False
        event.is_group = True
        event.is_channel = False
        event.reply_to_msg_id = 42

        group_chat = MagicMock()
        group_chat.title = "پروژه هوش مصنوعی"
        event.get_chat = AsyncMock(return_value=group_chat)

        replied_msg = MagicMock()
        replied_msg.raw_text = "لطفاً این بخش کد رو چک کن"
        replied_msg.file = None
        replied_msg.photo = None
        replied_msg.video = None
        replied_msg.voice = None
        replied_msg.audio = None
        replied_msg.sender = MagicMock(first_name="علی")
        event.get_reply_message = AsyncMock(return_value=replied_msg)

        ctx = await agent.build_environment_context(event, client)
        self.assertIn("پروژه هوش مصنوعی", ctx)
        self.assertIn("علی", ctx)
        self.assertIn("لطفاً این بخش کد رو چک کن", ctx)

    def test_build_agent_messages_includes_env_context(self):
        from ai_engine import agent
        msgs = agent._build_agent_messages(
            question="کاپری ۱۰۰ پیام اخیر اینجا رو مرتب کن",
            context="",
            memory_str="",
            is_owner=True,
            sender_name="مالک",
            env_context="موقعیت فعلی: پیام‌های ذخیره‌شده (Saved Messages)"
        )
        sys_content = msgs[0]["content"]
        self.assertIn("Saved Messages", sys_content)
        self.assertIn("راهنمای درک ضمایر و موقعیت", sys_content)
        self.assertIn("organize_saved_messages", sys_content)


class TestSmartReactions(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        from services.telegram import reactions
        self.reactions = reactions
        self.reactions._handled_reactions.clear()

    def test_extract_owner_reactions(self):
        from telethon.tl import types

        # 1. Other user reaction (my=False)
        up_other = types.UpdateMessageReactions(
            peer=types.PeerUser(user_id=123),
            msg_id=1,
            reactions=types.MessageReactions(
                results=[types.ReactionCount(reaction=types.ReactionEmoji(emoticon="❤️"), count=1)],
                recent_reactions=[
                    types.MessagePeerReaction(
                        peer_id=types.PeerUser(user_id=123),
                        date=None,
                        reaction=types.ReactionEmoji(emoticon="❤️"),
                        my=False
                    )
                ]
            )
        )
        self.assertEqual(self.reactions.extract_owner_reactions(up_other), [])

        # 2. Owner reaction in DM or group (my=True)
        up_my_pv = types.UpdateMessageReactions(
            peer=types.PeerUser(user_id=123),
            msg_id=2,
            reactions=types.MessageReactions(
                results=[],
                recent_reactions=[
                    types.MessagePeerReaction(
                        peer_id=types.PeerUser(user_id=999),
                        date=None,
                        reaction=types.ReactionEmoji(emoticon="❤️"),
                        my=True
                    )
                ]
            )
        )
        self.assertEqual(self.reactions.extract_owner_reactions(up_my_pv), ["❤️"])

        # 3. Owner reaction in broadcast channel (chosen_order is not None)
        up_channel = types.UpdateMessageReactions(
            peer=types.PeerChannel(channel_id=555),
            msg_id=3,
            reactions=types.MessageReactions(
                results=[
                    types.ReactionCount(
                        reaction=types.ReactionEmoji(emoticon="👍"),
                        count=10,
                        chosen_order=0
                    )
                ],
                recent_reactions=None
            )
        )
        self.assertEqual(self.reactions.extract_owner_reactions(up_channel), ["👍"])

    def test_deduplication_cache(self):
        self.assertFalse(self.reactions.is_already_handled(100, 1, "❤️"))
        self.assertTrue(self.reactions.is_already_handled(100, 1, "❤️"))
        self.assertFalse(self.reactions.is_already_handled(100, 2, "❤️"))

    async def test_voice_reaction_flow(self):
        client = AsyncMock()
        msg = MagicMock()
        msg.id = 500
        msg.voice = MagicMock()
        msg.file = None
        msg.raw_text = ""

        chat = MagicMock()
        chat.title = "گروه تست"
        msg.get_chat = AsyncMock(return_value=chat)
        msg.get_sender = AsyncMock(return_value=MagicMock(first_name="سارا"))

        client.download_media = AsyncMock(return_value="/tmp/fake_voice.ogg")

        with patch("os.path.exists", return_value=True), patch("os.remove"), \
             patch("services.voice.voice.transcribe", return_value="سلام پروژه آماده شد"), \
             patch("ai_engine.ai.ask_direct", return_value="تحلیل: درخواست ارسال پروژه"):
            handled = await self.reactions._handle_voice_reaction(client, msg, "🎙️", "سارا", "گروه تست")
            self.assertTrue(handled)
            client.send_message.assert_called_once()
            report_text = client.send_message.call_args[0][1]
            self.assertIn("پیاده‌سازی و تحلیل هوشمند ویس", report_text)
            self.assertIn("سلام پروژه آماده شد", report_text)
            self.assertIn("سارا", report_text)
            self.assertIn("تحلیل: درخواست ارسال پروژه", report_text)

    async def test_vault_reaction_flow(self):
        client = AsyncMock()
        client.get_input_entity = AsyncMock(return_value=MagicMock())

        msg = MagicMock()
        msg.id = 600
        msg.voice = None
        msg.file = None
        msg.raw_text = "دانلود فیلم سینمایی Inception 1080p"

        with patch("services.telegram.vault.ensure_vault_group", return_value=(-100123, "https://t.me/+fake")), \
             patch("services.telegram.vault.ensure_vault_topics", return_value={"media": 5}), \
             patch("services.telegram.vault.forward_to_topic", return_value=True) as mock_fwd:
            handled = await self.reactions._handle_vault_reaction(client, msg, "❤️", "کانال فیلم")
            self.assertTrue(handled)
            mock_fwd.assert_called_once()
            client.send_message.assert_called_once()
            report_text = client.send_message.call_args[0][1]
            self.assertIn("بایگانی خودکار در صندوق هوشمند", report_text)
            self.assertIn("فیلم و سریال", report_text)

    async def test_vault_reaction_with_album_flow(self):
        client = AsyncMock()
        client.get_input_entity = AsyncMock(return_value=MagicMock())

        # Target message is photo 2 of an album, has empty raw_text
        target_msg = MagicMock()
        target_msg.id = 8191
        target_msg.grouped_id = 998877
        target_msg.voice = None
        target_msg.file = None
        target_msg.raw_text = ""

        # Sibling 1 has the actual gaming caption
        sib1 = MagicMock(id=8190, grouped_id=998877, raw_text="دانلود بازی Resident Evil 4 Remake کامپیوتر")
        sib2 = target_msg
        sib3 = MagicMock(id=8192, grouped_id=998877, raw_text="")

        with patch("services.telegram.vault.get_album_messages", return_value=[sib1, sib2, sib3]), \
             patch("services.telegram.vault.ensure_vault_group", return_value=(-100123, "https://t.me/+fake")), \
             patch("services.telegram.vault.ensure_vault_topics", return_value={"gaming": 15}), \
             patch("services.telegram.vault.forward_to_topic", return_value=True) as mock_fwd:
            handled = await self.reactions._handle_vault_reaction(client, target_msg, "👍", "دانلود بازی - اپدونی | AppDuny", source_label="کانال")
            self.assertTrue(handled)
            mock_fwd.assert_called_once()
            # Verify album_ids passed to forward_to_topic
            self.assertEqual(mock_fwd.call_args[1]["album_ids"], [8190, 8191, 8192])
            client.send_message.assert_called_once()
            report_text = client.send_message.call_args[0][1]
            self.assertIn("بازی و گیمینگ", report_text)
            self.assertIn("3 تصویر/رسانه به صورت یکجا", report_text)

    async def test_roast_reaction_flow(self):
        client = AsyncMock()
        msg = MagicMock()
        msg.id = 700
        msg.raw_text = "ادعا داری بیا بازی"
        peer = MagicMock()

        with patch("services.social.roast.generate_roast", return_value="فعلا برو مشقاتو بنویس"):
            handled = await self.reactions._handle_roast_reaction(client, msg, "🤡", "سامان", "گروه گیم", peer)
            self.assertTrue(handled)
            # Verify direct reply in chat
            client.send_message.assert_any_call(peer, "فعلا برو مشقاتو بنویس", reply_to=700)
            # Verify report delivery in Saved Messages
            client.send_message.assert_any_call("me", unittest.mock.ANY)

    async def test_reminder_reaction_flow(self):
        client = AsyncMock()
        msg = MagicMock()
        msg.id = 800
        msg.file = None
        msg.raw_text = "ساعت پنج جلسه کاری داریم"

        with patch("services.social.dnd.add_reminder") as mock_add_rem:
            handled = await self.reactions._handle_reminder_reaction(client, msg, "👀", "مدیر", "پیوی کاری")
            self.assertTrue(handled)
            mock_add_rem.assert_called_once()
            client.send_message.assert_called_once()
            report = client.send_message.call_args[0][1]
            self.assertIn("ثبت خودکار یادآور", report)
            self.assertIn("ساعت پنج جلسه کاری داریم", report)

    async def test_reaction_update_dispatcher_routing(self):
        from telethon.tl import types
        client = AsyncMock()

        # Mock clown reaction event in group chat
        up_roast = types.UpdateMessageReactions(
            peer=types.PeerChat(chat_id=1234),
            msg_id=777,
            reactions=types.MessageReactions(
                results=[],
                recent_reactions=[
                    types.MessagePeerReaction(
                        peer_id=types.PeerUser(user_id=999),
                        date=None,
                        reaction=types.ReactionEmoji(emoticon="🤡"),
                        my=True
                    )
                ]
            )
        )

        mock_msg = MagicMock()
        mock_msg.id = 777
        mock_msg.raw_text = "من از همه بهترم"
        mock_msg.voice = None
        mock_msg.audio = None
        mock_msg.file = None
        mock_msg.is_channel = False
        mock_msg.is_group = True
        mock_msg.is_private = False

        chat = MagicMock()
        chat.title = "گروه کل کل"
        chat.broadcast = False
        chat.megagroup = True
        mock_msg.get_chat = AsyncMock(return_value=chat)
        mock_msg.get_sender = AsyncMock(return_value=MagicMock(first_name="رامین"))

        client.get_messages = AsyncMock(return_value=mock_msg)
        client.get_peer_id = AsyncMock(return_value=1234)

        with patch("services.social.roast.generate_roast", return_value="تو حتی از خودت هم بهتری!"):
            handled = await self.reactions.handle_reaction_update(client, up_roast)
            self.assertTrue(handled)
            client.send_message.assert_any_call(up_roast.peer, "تو حتی از خودت هم بهتری!", reply_to=777)

    async def test_update_edit_message_reaction_pv(self):
        """تست دریافت رویداد UpdateEditMessage در چت خصوصی (PV) که تلگرام به جای UpdateMessageReactions می‌فرستد."""
        from telethon.tl import types
        client = AsyncMock()

        # UpdateEditMessage حاوی Message با reactions
        msg_obj = MagicMock()
        msg_obj.id = 12345
        msg_obj.peer_id = types.PeerUser(user_id=778899)
        msg_obj.reactions = types.MessageReactions(
            results=[],
            recent_reactions=[
                types.MessagePeerReaction(
                    peer_id=types.PeerUser(user_id=999),
                    date=None,
                    reaction=types.ReactionEmoji(emoticon="🤡"),
                    my=True
                )
            ]
        )
        up_edit = types.UpdateEditMessage(message=msg_obj, pts=1, pts_count=1)

        fetched_msg = MagicMock()
        fetched_msg.id = 12345
        fetched_msg.raw_text = "چرا جواب نمیدی؟"
        fetched_msg.voice = None
        fetched_msg.audio = None
        fetched_msg.file = None
        fetched_msg.post = False
        fetched_msg.is_channel = False
        fetched_msg.is_group = False
        fetched_msg.is_private = True
        fetched_msg.get_chat = AsyncMock(return_value=MagicMock(title="کاربر شاکی", broadcast=False, megagroup=False))
        fetched_msg.get_sender = AsyncMock(return_value=MagicMock(first_name="علیرضا"))

        client.get_messages = AsyncMock(return_value=fetched_msg)
        client.get_peer_id = AsyncMock(return_value=778899)

        with patch("services.social.roast.generate_roast", return_value="برو مشقاتو بنویس!"):
            handled = await self.reactions.handle_reaction_update(client, up_edit)
            self.assertTrue(handled)
            client.send_message.assert_any_call(msg_obj.peer_id, "برو مشقاتو بنویس!", reply_to=12345)

    async def test_roast_pv_fallback_to_msg_reply(self):
        """تست خطای عدم یافتن Input Entity در پیوی و فال‌بک موفق به msg.reply."""
        client = AsyncMock()
        peer = MagicMock()
        # شبیه‌سازی خطای تل‌تون هنگامی که access_hash مخاطب در دیتابیس لوکال نیست
        client.send_message = AsyncMock(side_effect=[ValueError("Could not find the input entity for PeerUser"), MagicMock()])

        msg = MagicMock()
        msg.id = 999
        msg.raw_text = "خیلی ادعات میشه"
        msg.reply = AsyncMock()

        with patch("services.social.roast.generate_roast", return_value="فعلا که زیرمایی!"):
            handled = await self.reactions._handle_roast_reaction(client, msg, "🤡", "حامد", "پیوی حامد", peer)
            self.assertTrue(handled)
            msg.reply.assert_called_once_with("فعلا که زیرمایی!")

    async def test_roast_fallback_on_ai_failure(self):
        """تست اینکه در صورت خطای هوش مصنوعی، روست همچنان با پانچ‌لاین‌های فال‌بک پاسخ می‌دهد."""
        from services.social import roast
        with patch("ai_engine.ai.ask_direct", side_effect=Exception("Connection reset by peer / SSL")):
            punchline = await roast.generate_roast("حریف", "پیام بیخود")
            self.assertTrue(len(punchline) > 5)
            self.assertIn("🤡", punchline)

    async def test_custom_emoji_reaction_resolution(self):
        """تست ریزالو واکنش‌های کاستوم / متحرک تلگرام به یونیکد اصلی."""
        from telethon.tl import types
        client = AsyncMock()
        doc_mock = MagicMock()
        doc_mock.id = 88776655
        attr_mock = MagicMock()
        attr_mock.alt = "❤️"
        doc_mock.attributes = [attr_mock]
        client.side_effect = None
        client.return_value = [doc_mock]

        reactions_obj = types.MessageReactions(
            results=[
                types.ReactionCount(
                    reaction=types.ReactionCustomEmoji(document_id=88776655),
                    count=5,
                    chosen_order=0
                )
            ]
        )
        resolved = await self.reactions.extract_owner_reactions_async(client, reactions_obj)
        self.assertIn("❤️", resolved)

    async def test_channel_reaction_with_update_edit_channel(self):
        """تست دریافت رویداد UpdateEditChannelMessage با لایک در کانال و ارسال به صندوق."""
        from telethon.tl import types
        client = AsyncMock()

        msg_obj = MagicMock()
        msg_obj.id = 554433
        msg_obj.peer_id = types.PeerChannel(channel_id=889900)
        msg_obj.reactions = types.MessageReactions(
            results=[
                types.ReactionCount(
                    reaction=types.ReactionEmoji(emoticon="👍"),
                    count=30,
                    chosen_order=0
                )
            ]
        )
        up_channel_edit = types.UpdateEditChannelMessage(message=msg_obj, pts=1, pts_count=1)

        fetched_msg = MagicMock()
        fetched_msg.id = 554433
        fetched_msg.raw_text = "آهنگ جدید و زیبای شادمهر عقیلی با کیفیت ۳۲۰"
        fetched_msg.voice = None
        fetched_msg.audio = MagicMock()
        fetched_msg.file = MagicMock()
        fetched_msg.file.mime_type = "audio/mp3"
        fetched_msg.post = True
        fetched_msg.is_channel = True
        fetched_msg.is_group = False
        fetched_msg.is_private = False
        fetched_msg.grouped_id = None
        fetched_msg.get_chat = AsyncMock(return_value=MagicMock(title="کانال موزیک", broadcast=True, megagroup=False))
        fetched_msg.get_sender = AsyncMock(return_value=None)

        client.get_messages = AsyncMock(return_value=fetched_msg)
        client.get_peer_id = AsyncMock(return_value=889900)
        client.get_input_entity = AsyncMock(return_value=MagicMock())

        with patch("services.telegram.vault.ensure_vault_group", return_value=(-100123, "https://t.me/+fake")), \
             patch("services.telegram.vault.ensure_vault_topics", return_value={"music": 12}), \
             patch("services.telegram.vault.forward_to_topic", return_value=True) as mock_fwd:
            handled = await self.reactions.handle_reaction_update(client, up_channel_edit)
            self.assertTrue(handled)
            mock_fwd.assert_called_once()
            client.send_message.assert_called_once()
            self.assertIn("موزیک و صوت", client.send_message.call_args[0][1])

    def test_get_voice_speaker_setting(self):
        """تست واکشی صحیح نام گوینده صوتی فعال برای داشبورد."""
        from core import settings
        with patch.object(settings, "get_tts_engine", return_value="microsoft"), \
             patch.object(settings, "get_tts_voice", return_value="fa-IR-DilaraNeural"):
            self.assertEqual(settings.get_voice_speaker(), "دلارا")

        with patch.object(settings, "get_tts_engine", return_value="microsoft"), \
             patch.object(settings, "get_tts_voice", return_value="fa-IR-FaridNeural"):
            self.assertEqual(settings.get_voice_speaker(), "فرید")

        with patch.object(settings, "get_tts_engine", return_value="gemini"):
            self.assertIn("جمینای", settings.get_voice_speaker())

    def test_channel_leave_keyword_and_stem_matching(self):
        """تست استخراج دقیق موضوع کانال جهت لفت دادن و تطبیق پسوندهای زبان فارسی."""
        import bot
        from services.telegram import channels

        # 1. تست تشخیص و استخراج کلمه کلیدی
        q = "کاپری از کانال های کنکور لفت بده"
        self.assertTrue(bot._is_channel_leave_request(q))
        self.assertEqual(bot._extract_channel_leave_keyword(q), "کنکور")

        q2 = "از کانال‌های اخبار فوری لفت بزن"
        self.assertTrue(bot._is_channel_leave_request(q2))
        self.assertEqual(bot._extract_channel_leave_keyword(q2), "اخبار فوری")

        # 2. تست تطبیق نام و پسوندها
        self.assertTrue(channels.match_name("زیست کنکور آسان است", "کنکور"))
        self.assertTrue(channels.match_name("کانال آزمون کنکور", "کانالهای کنکور"))
        self.assertTrue(channels.match_name("مرکز مشاوره کنکور ۱۴۰۴", "کانالهای کنکوری"))
        self.assertFalse(channels.match_name("کانال دانلود فیلم", "کنکور"))







if __name__ == "__main__":
    unittest.main()
