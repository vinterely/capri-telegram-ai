import asyncio
import json
import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from ai_engine import agent
import bot
from ai_engine import tools


class TestAllCapriFeatures(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        agent.breaker.reset()
        self.event = MagicMock()
        self.event.out = True
        self.event.chat_id = 999
        self.client = MagicMock()

    async def test_01_folders_list(self):
        fake_folders = [{"id": 1, "title": "کاری"}, {"id": 2, "title": "سرگرمی"}]
        tc = {
            "id": "c1",
            "function": {"name": "manage_folders", "arguments": json.dumps({"action": "list"})}
        }
        with patch("ai_engine.agent._call_model_step") as mock_step, \
             patch("services.telegram.folders.list_folders", new_callable=AsyncMock, return_value=fake_folders):
            mock_step.side_effect = [
                {"content": "", "tool_calls": [tc]},
                {"content": "📁 پوشه‌های شما:\n- کاری\n- سرگرمی", "tool_calls": []}
            ]
            res = await agent.run_agent("کاپری لیست پوشه هام بده", "", "", self.event, self.client)
            self.assertTrue("کاری" in res and "سرگرمی" in res, f"Expected folder names, got: {res}")

    async def test_02_channel_leave_confirmation(self):
        bot.pending.clear()
        fake_ch = MagicMock()
        fake_ch.name = "بروز نیوز"
        tc = {
            "id": "c2",
            "function": {"name": "manage_channel_membership", "arguments": json.dumps({"action": "leave", "target": "بروز نیوز"})}
        }
        with patch("ai_engine.agent._call_model_step") as mock_step, \
             patch("services.telegram.channels.find_channels", new_callable=AsyncMock, return_value=[fake_ch]):
            mock_step.side_effect = [
                {"content": "", "tool_calls": [tc]},
                {"content": "برای لفت دادن از بروز نیوز مطمئنی؟", "tool_calls": []}
            ]
            res = await agent.run_agent("کاپری از کانال بروز نیوز لفت بده", "", "", self.event, self.client)
            self.assertTrue(any(k in res for k in ("تایید", "مطمئن", "خروج", "آره", "بروز نیوز")), f"Expected confirmation request, got: {res}")
            self.assertIn("999", bot.pending)

    async def test_03_youtube_download(self):
        tc = {
            "id": "c3",
            "function": {"name": "download_youtube_video", "arguments": json.dumps({"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "quality": 720})}
        }
        with patch("ai_engine.agent._call_model_step") as mock_step, \
             patch("services.media.ytdownload.download_youtube_video", new_callable=AsyncMock, return_value="✅ ویدیوی یوتیوب با کیفیت 720p فوروارد شد."):
            mock_step.side_effect = [
                {"content": "", "tool_calls": [tc]},
                {"content": "✅ ویدیوی یوتیوب با کیفیت 720p دانلود شد.", "tool_calls": []}
            ]
            res = await agent.run_agent("کاپری این ویدیو یوتیوب رو دانلود کن: https://www.youtube.com/watch?v=dQw4w9WgXcQ", "", "", self.event, self.client)
            self.assertTrue("720" in res or "۷۲۰" in res, f"Expected 720 in response, got: {res}")

    async def test_04_youtube_download_quality(self):
        tc = {
            "id": "c4",
            "function": {"name": "download_youtube_video", "arguments": json.dumps({"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "quality": 1080})}
        }
        with patch("ai_engine.agent._call_model_step") as mock_step, \
             patch("services.media.ytdownload.download_youtube_video", new_callable=AsyncMock, return_value="✅ ویدیوی یوتیوب با کیفیت 1080p فوروارد شد."):
            mock_step.side_effect = [
                {"content": "", "tool_calls": [tc]},
                {"content": "✅ ویدیو با کیفیت 1080p فوروارد شد.", "tool_calls": []}
            ]
            res = await agent.run_agent("کاپری این ویدیو یوتیوب رو با کیفیت 1080 برام بفرست: https://www.youtube.com/watch?v=dQw4w9WgXcQ", "", "", self.event, self.client)
            self.assertTrue("1080" in res or "۱۰۸۰" in res, f"Expected 1080 in response, got: {res}")

    async def test_05_youtube_summarize(self):
        tc = {
            "id": "c5",
            "function": {"name": "summarize_youtube_video", "arguments": json.dumps({"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"})}
        }
        with patch("ai_engine.agent._call_model_step") as mock_step, \
             patch("services.media.ytsummary.summarize_youtube_video", return_value="📌 خلاصه ویدیوی یوتیوب: آموزش هوش مصنوعی"):
            mock_step.side_effect = [
                {"content": "", "tool_calls": [tc]},
                {"content": "این خلاصه ویدیوی یوتیوب است: نکات کلیدی ایجنت‌ها", "tool_calls": []}
            ]
            res = await agent.run_agent("کاپری این ویدیو رو خلاصه کن: https://www.youtube.com/watch?v=dQw4w9WgXcQ", "", "", self.event, self.client)
            self.assertIn("خلاصه", res)

    async def test_06_roast_target(self):
        self.event.is_reply = True
        self.event.reply_to_msg_id = 456
        tc = {
            "id": "c6",
            "function": {"name": "roast_target", "arguments": json.dumps({"style": "سنگین"})}
        }
        with patch("ai_engine.agent._call_model_step") as mock_step, \
             patch("services.social.roast.handle_roast", new_callable=AsyncMock, return_value=True):
            mock_step.side_effect = [
                {"content": "", "tool_calls": [tc]}
            ]
            res = await agent.run_agent("کاپری این پیام رو روست کن", "", "", self.event, self.client)
            self.assertEqual(res, "__ROAST_SENT__")

    async def test_07_webpage_reader(self):
        fake_page = {"title": "مقاله تست", "content": "محتوای مقاله درباره ایجنت‌های هوش مصنوعی."}
        tc = {
            "id": "c7",
            "function": {"name": "read_webpage", "arguments": json.dumps({"url": "https://example.com/test"})}
        }
        with patch("ai_engine.agent._call_model_step") as mock_step, \
             patch("services.search.webreader.fetch_url", return_value=fake_page):
            mock_step.side_effect = [
                {"content": "", "tool_calls": [tc]},
                {"content": "خلاصه مقاله درباره ایجنت‌های هوش مصنوعی است.", "tool_calls": []}
            ]
            res = await agent.run_agent("کاپری این مقاله رو بخون و خلاصه کن: https://example.com/test", "", "", self.event, self.client)
            self.assertIn("مقاله", res)

    async def test_08_memory_save(self):
        tc = {
            "id": "c8",
            "function": {"name": "manage_memory", "arguments": json.dumps({"action": "add", "fact": "کاربر عاشق پایتون است"})}
        }
        with patch("ai_engine.agent._call_model_step") as mock_step, \
             patch("core.memory.add_memory") as mock_add:
            mock_step.side_effect = [
                {"content": "", "tool_calls": [tc]},
                {"content": "حله! در حافظه ذخیره کردم که عاشق برنامه‌نویسی پایتونی.", "tool_calls": []}
            ]
            res = await agent.run_agent("کاپری یادت باشه من عاشق برنامه‌نویسی پایتونم", "", "", self.event, self.client)
            self.assertTrue(any(k in res for k in ("حافظه", "ثبت", "یادم", "ذخیره")), f"Expected memory confirmation, got: {res}")

    async def test_09_ambiguous_clarification(self):
        tc = {
            "id": "c9",
            "function": {"name": "ask_clarification", "arguments": json.dumps({"question": "دقیقاً چه چیزی را پاک کنم؟ پیام، حافظه یا کش؟"})}
        }
        with patch("ai_engine.agent._call_model_step") as mock_step:
            mock_step.side_effect = [
                {"content": "", "tool_calls": [tc]}
            ]
            res = await agent.run_agent("کاپری پاکش کن", "", "", self.event, self.client)
            self.assertTrue(len(res) > 5)
            self.assertIn("پاک کنم", res)

    async def test_10_stranger_cannot_access_sensitive(self):
        stranger_event = MagicMock()
        stranger_event.out = False
        res = await tools.execute_tool("manage_folders", {"action": "list"}, stranger_event, self.client)
        self.assertIn("فقط برای صاحب اکانت فعال است", res)


if __name__ == "__main__":
    unittest.main()
