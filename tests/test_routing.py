import asyncio
import json
import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure project root is on sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from ai_engine import agent
import bot
from ai_engine import tools


class TestEvalPromptsDataset(unittest.TestCase):
    """Verify that eval_prompts.json contains expected structure and diverse scenarios."""

    def test_eval_prompts_file_validity(self):
        prompts_path = os.path.join(BASE_DIR, "tests", "eval_prompts.json")
        self.assertTrue(os.path.exists(prompts_path), "eval_prompts.json must exist")
        with open(prompts_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertGreaterEqual(len(data), 30, "Must have at least 30 eval prompts")
        for item in data:
            self.assertIn("id", item)
            self.assertIn("prompt", item)
            self.assertIn("category", item)
            self.assertIn("expected_tool", item)

    def test_eval_prompts_scenarios_coverage(self):
        prompts_path = os.path.join(BASE_DIR, "tests", "eval_prompts.json")
        with open(prompts_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        categories = {item["category"] for item in data}
        self.assertIn("advice_or_review", categories)
        self.assertIn("media_download", categories)
        self.assertIn("destructive_action", categories)
        self.assertIn("instruction_question", categories)
        self.assertIn("ambiguous_prompt", categories)
        self.assertIn("social_tool", categories)

        # Check advice/question prompts do NOT allow destructive/media tools
        for item in data:
            if item.get("forbidden_tool"):
                self.assertNotEqual(item["expected_tool"], item["forbidden_tool"])


class TestBatchTaintSecurity(unittest.IsolatedAsyncioTestCase):
    """Test that tainted state updates immediately inside batch execution,

    preventing subsequent sensitive tools in the SAME turn.
    """

    async def test_taint_blocks_subsequent_sensitive_tool_in_same_batch(self):
        event = MagicMock()
        event.out = True
        event.chat_id = 12345
        client = MagicMock()

        tc1 = {
            "id": "call_1",
            "function": {
                "name": "read_webpage",
                "arguments": json.dumps({"url": "https://example.com/test"})
            }
        }
        tc2 = {
            "id": "call_2",
            "function": {
                "name": "manage_memory",
                "arguments": json.dumps({"action": "add", "fact": "نکته محرمانه"})
            }
        }

        with patch("ai_engine.agent._call_model_step") as mock_step, \
             patch("ai_engine.tools.execute_tool", new_callable=AsyncMock) as mock_exec:

            mock_exec.return_value = "محتوای صفحه وب"

            mock_step.side_effect = [
                {"content": "", "tool_calls": [tc1, tc2]},
                {"content": "عملیات انجام شد", "tool_calls": []}
            ]

            res = await agent.run_agent("تست تزریق نفوذ", "", "", event, client, max_steps=2)

            # read_webpage was executed
            mock_exec.assert_called_once_with("read_webpage", {"url": "https://example.com/test"}, event, client, None)
            # manage_memory was blocked before execute_tool because tainted became True!
            self.assertEqual(res, "عملیات انجام شد")

    async def test_taint_blocks_side_effect_tools_deny_by_default(self):
        # بعد از خواندن محتوای غیرقابل‌اعتماد، ابزارهای دارای اثر جانبی (نه فقط SENSITIVE قبلی)
        # هم مسدود می‌شوند (مدل deny-by-default با لیست READ_ONLY_TOOLS).
        event = MagicMock()
        event.out = True
        event.chat_id = 12345
        client = MagicMock()

        tc1 = {
            "id": "call_1",
            "function": {"name": "read_webpage", "arguments": json.dumps({"url": "https://example.com"})}
        }
        tc2 = {
            "id": "call_2",
            "function": {"name": "download_youtube_video", "arguments": json.dumps({"url": "https://youtu.be/x"})}
        }

        with patch("ai_engine.agent._call_model_step") as mock_step, \
             patch("ai_engine.tools.execute_tool", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = "محتوای وب"
            mock_step.side_effect = [
                {"content": "", "tool_calls": [tc1, tc2]},
                {"content": "دانلود مسدود شد", "tool_calls": []}
            ]
            await agent.run_agent("بخوان و دانلود کن", "", "", event, client, max_steps=2)
            # فقط read_webpage اجرا شد؛ download_youtube_video بعد از taint مسدود شد
            mock_exec.assert_called_once_with("read_webpage", {"url": "https://example.com"}, event, client, None)

    async def test_clean_batch_executes_both_tools(self):
        event = MagicMock()
        event.out = True
        event.chat_id = 12345
        client = MagicMock()

        tc1 = {
            "id": "call_1",
            "function": {
                "name": "web_search",
                "arguments": json.dumps({"query": "اخبار هوش مصنوعی"})
            }
        }
        tc2 = {
            "id": "call_2",
            "function": {
                "name": "get_current_datetime",
                "arguments": "{}"
            }
        }

        with patch("ai_engine.agent._call_model_step") as mock_step, \
             patch("ai_engine.tools.execute_tool", new_callable=AsyncMock) as mock_exec:

            mock_exec.side_effect = ["نتایج اخبار", "امروز شنبه است"]

            mock_step.side_effect = [
                {"content": "", "tool_calls": [tc1, tc2]},
                {"content": "جواب نهایی با اخبار و تاریخ", "tool_calls": []}
            ]

            res = await agent.run_agent("اخبار و تاریخ بگو", "", "", event, client, max_steps=2)
            self.assertEqual(mock_exec.call_count, 2)
            self.assertEqual(res, "جواب نهایی با اخبار و تاریخ")


class TestDestructiveConfirmationGates(unittest.IsolatedAsyncioTestCase):
    """Test that destructive operations (leave, delete folder, clear memory, auto_sort)

    are intercepted and registered in bot.pending instead of executing directly.
    """

    async def test_leave_single_channel_registers_pending(self):
        event = MagicMock()
        event.out = True
        event.chat_id = 999
        client = MagicMock()
        bot.pending.clear()

        fake_channel = MagicMock()
        fake_channel.name = "کانال بد"

        with patch("services.telegram.channels.find_channels", new_callable=AsyncMock, return_value=[fake_channel]):
            res = await tools.execute_tool(
                "manage_channel_membership",
                {"action": "leave", "target": "@badchannel"},
                event,
                client
            )
            self.assertIn("برای خروج از کانال «کانال بد»، لطفاً تایید کنید", res)
            self.assertIn("999", bot.pending)
            self.assertEqual(bot.pending["999"]["kind"], "confirm_leave_single")
            self.assertEqual(bot.pending["999"]["name"], "کانال بد")

    async def test_leave_multiple_channels_registers_pending(self):
        event = MagicMock()
        event.out = True
        event.chat_id = 999
        client = MagicMock()
        bot.pending.clear()

        ch1 = MagicMock()
        ch1.name = "کانال یک"
        ch2 = MagicMock()
        ch2.name = "کانال دو"

        with patch("services.telegram.channels.find_channels", new_callable=AsyncMock, return_value=[ch1, ch2]):
            res = await tools.execute_tool(
                "manage_channel_membership",
                {"action": "leave", "target": "کانال"},
                event,
                client
            )
            self.assertIn("کدام را لفت بزنم؟", res)
            self.assertIn("999", bot.pending)
            self.assertEqual(bot.pending["999"]["kind"], "leave")

    async def test_delete_folder_registers_pending(self):
        event = MagicMock()
        event.out = True
        event.chat_id = 888
        client = MagicMock()
        bot.pending.clear()

        folder_item = {"id": 12, "title": "سرگرمی"}
        with patch("services.telegram.folders.list_folders", new_callable=AsyncMock, return_value=[folder_item]), \
             patch("services.telegram.folders.find_folder", return_value=folder_item):
            res = await tools.execute_tool(
                "manage_folders",
                {"action": "delete", "folder_name": "سرگرمی"},
                event,
                client
            )
            self.assertIn("برای حذف پوشه «سرگرمی»، لطفاً تایید کنید", res)
            self.assertIn("888", bot.pending)
            self.assertEqual(bot.pending["888"]["kind"], "confirm_delete_folder")
            self.assertEqual(bot.pending["888"]["name"], "سرگرمی")

    async def test_clear_memory_registers_pending(self):
        event = MagicMock()
        event.out = True
        event.chat_id = 777
        client = MagicMock()
        bot.pending.clear()

        res = await tools.execute_tool(
            "manage_memory",
            {"action": "clear"},
            event,
            client
        )
        self.assertIn("آیا مطمئنید می‌خواهید کل حافظه ماندگار را پاک کنید؟", res)
        self.assertIn("777", bot.pending)
        self.assertEqual(bot.pending["777"]["kind"], "confirm_clear_memory")

    async def test_auto_sort_folders_triggers_sort_and_pending(self):
        event = MagicMock()
        event.out = True
        event.chat_id = 666
        client = MagicMock()
        bot.pending.clear()

        with patch("services.telegram.folders.list_folders", new_callable=AsyncMock, return_value=[]), \
             patch("bot._do_sort", new_callable=AsyncMock) as mock_sort:
            res = await tools.execute_tool(
                "manage_folders",
                {"action": "auto_sort"},
                event,
                client
            )
            self.assertEqual(res, "__PENDING_SORT__")
            mock_sort.assert_called_once()


class TestStrangerToolGate(unittest.IsolatedAsyncioTestCase):
    """Ensure strangers (event.out = False) are blocked from sensitive and admin tools."""

    async def test_stranger_cannot_access_sensitive_tools(self):
        event = MagicMock()
        event.out = False
        event.chat_id = 111
        client = MagicMock()

        sensitive_calls = [
            ("manage_channel_membership", {"action": "leave", "target": "@test"}),
            ("manage_folders", {"action": "auto_sort"}),
            ("manage_memory", {"action": "add", "fact": "f"}),
            ("manage_important_channels", {"action": "add", "channel_name": "@ch"}),
            ("create_or_update_skill", {"name": "test_skill"}),
            ("delete_skill", {"name": "test_skill"}),
            ("fetch_and_forward_movie", {"target": "movie"}),
            ("draft_and_send_message", {"target_contact": "user", "message_intent": "msg"}),
        ]

        for tool_name, args in sensitive_calls:
            res = await tools.execute_tool(tool_name, args, event, client)
            self.assertIn("فقط برای صاحب اکانت فعال است", res, f"Tool {tool_name} should be blocked for stranger")

    async def test_stranger_can_access_allowed_tools(self):
        event = MagicMock()
        event.out = False
        event.chat_id = 111
        client = MagicMock()

        res1 = await tools.execute_tool("get_current_datetime", {}, event, client)
        self.assertIn("امروز", res1)

        res2 = await tools.execute_tool("ask_clarification", {"question": "توضیح بیشتر بده"}, event, client)
        self.assertEqual(res2, "__ASK_USER__:توضیح بیشتر بده")


class TestAskClarificationTool(unittest.IsolatedAsyncioTestCase):
    """Test that calling ask_clarification terminates agent turn immediately and returns prompt."""

    async def test_ask_clarification_stops_agent_turn(self):
        event = MagicMock()
        event.out = True
        event.chat_id = 123
        client = MagicMock()

        tc = {
            "id": "clarify_1",
            "function": {
                "name": "ask_clarification",
                "arguments": json.dumps({"question": "منظورت کدوم فیلمه؟ لطفاً سال یا اسم کاملش رو بگو."})
            }
        }

        with patch("ai_engine.agent._call_model_step") as mock_step:
            mock_step.return_value = {"content": "", "tool_calls": [tc]}
            res = await agent.run_agent("فیلم رو دانلود کن", "", "", event, client, max_steps=3)
            self.assertEqual(res, "منظورت کدوم فیلمه؟ لطفاً سال یا اسم کاملش رو بگو.")
            self.assertEqual(mock_step.call_count, 1)


class TestProviderFallback(unittest.IsolatedAsyncioTestCase):
    """Test circuit breaker and fallback mechanisms."""

    def setUp(self):
        agent.breaker.reset()

    async def test_gemini_failure_falls_back_to_next_provider(self):
        with patch.object(agent.config, "GEMINI_API_KEY", "dummy_key"), \
             patch.object(agent.config, "GEMINI_MODELS", ["gemini-2.5-flash"]), \
             patch("ai_engine.agent._call_gemini_tools", side_effect=Exception("Gemini quota exceeded")), \
             patch("core.settings.get_selection", return_value=("hooshia", "GLM-4.5-Flash")), \
             patch.object(agent.config, "HOOSHIA_API_KEY", "hooshia_key"), \
             patch("ai_engine.agent._call_hooshia_tools", return_value={"choices": [{"message": {"content": "پاسخ از ارائه‌دهنده پشتیبان", "tool_calls": []}}]}) as mock_hooshia:

            res = await asyncio.to_thread(agent._call_model_step, [{"role": "user", "content": "سلام"}], tools.TOOL_DEFINITIONS)
            self.assertIn("content", res)
            self.assertEqual(res["content"], "پاسخ از ارائه‌دهنده پشتیبان")
            mock_hooshia.assert_called_once()


class TestMockPromptRouting(unittest.IsolatedAsyncioTestCase):
    """Verify mock agent routing behavior across prompt types."""

    async def test_media_review_does_not_download(self):
        event = MagicMock()
        event.out = True
        event.chat_id = 555
        client = MagicMock()

        with patch("ai_engine.agent._call_model_step") as mock_step:
            mock_step.return_value = {
                "content": "فیلم اوپنهایمر نقدهای بسیار مثبتی دریافت کرد و در سایت راتن تومیتوز امتیاز ۹۳٪ را کسب کرده است.",
                "tool_calls": []
            }
            res = await agent.run_agent("فیلم Oppenheimer چطور بود و نمراتش چی شد؟", "", "", event, client)
            self.assertIn("اوپنهایمر", res)
            # Ensure no fetch_and_forward_movie was called
            self.assertEqual(mock_step.call_count, 1)

    async def test_media_download_invokes_fetch_tool(self):
        event = MagicMock()
        event.out = True
        event.chat_id = 555
        client = MagicMock()

        tc = {
            "id": "fetch_1",
            "function": {
                "name": "fetch_and_forward_movie",
                "arguments": json.dumps({"target": "Inception 2010"})
            }
        }

        with patch("ai_engine.agent._call_model_step") as mock_step, \
             patch("ai_engine.tools.execute_tool", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = "درخواست فیلم ثبت شد"
            mock_step.side_effect = [
                {"content": "", "tool_calls": [tc]},
                {"content": "فیلم پیدا شد و فرستادم برات.", "tool_calls": []}
            ]
            res = await agent.run_agent("کاپری فیلم Inception 2010 رو دانلود کن برام", "", "", event, client)
            self.assertEqual(res, "فیلم پیدا شد و فرستادم برات.")
            mock_exec.assert_called_once_with("fetch_and_forward_movie", {"target": "Inception 2010"}, event, client, None)

    async def test_youtube_download_invokes_ytdownload(self):
        event = MagicMock()
        event.out = True
        event.chat_id = 555
        client = MagicMock()

        with patch("services.media.ytdownload.download_youtube_video", new_callable=AsyncMock) as mock_yt:
            mock_yt.return_value = "✅ ویدیوی یوتیوب با کیفیت 720p دریافت و ارسال شد."
            res = await tools.execute_tool(
                "download_youtube_video",
                {"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "quality": 720},
                event,
                client
            )
            self.assertIn("با کیفیت 720p", res)
            mock_yt.assert_called_once_with(client, "https://www.youtube.com/watch?v=dQw4w9WgXcQ", quality=720, event=event, status=None)


if __name__ == "__main__":
    unittest.main()
