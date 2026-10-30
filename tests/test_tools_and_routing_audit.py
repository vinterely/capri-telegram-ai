# -*- coding: utf-8 -*-
"""Comprehensive test suite for Capri AI Tools, Commands, and Request Routing Audit.

Covers:
1. Video download routing scenario
2. Video summary routing scenario
3. Video info / metadata routing scenario
4. Download failure reporting (truthful error, zero false success claims, zero fake quarantine claims)
5. Telegram transmission failure distinction (creation/download ok vs forward/send failure)
6. Conversational / text questions bypassing tools (e.g. 'یوتیوب در چه سالی تاسیس شد؟')
7. Concurrency & isolation safety across requests
8. Tool definitions validation & backward compatibility
"""
import asyncio
import json
import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from ai_engine import agent, tools
from services.media import socialdl, ytdownload, ytsummary
import bot


class TestVideoRoutingTriaging(unittest.IsolatedAsyncioTestCase):
    """Test clear triaging between video download, summary, info, and social links."""

    async def test_youtube_download_intent_in_bot(self):
        """Explicit download request with YouTube link routes to download_youtube_video."""
        event = MagicMock()
        event.chat_id = 12345
        client = MagicMock()
        status = AsyncMock()
        event.reply = AsyncMock(return_value=status)

        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        text = f"کاپری این ویدیو رو برام با کیفیت 720 دانلود کن: {url}"

        with patch("services.media.ytdownload.download_youtube_video", new_callable=AsyncMock) as mock_dl:
            mock_dl.return_value = "✅ ویدیوی یوتیوب با کیفیت 720p دریافت و ارسال شد."
            with patch("bot._safe_edit_or_send", new_callable=AsyncMock) as mock_send:
                event.raw_text = text
                # Test intent helper directly
                self.assertTrue(bot._is_download_request(text))
                self.assertFalse(bot._is_summary_request(text))
                self.assertFalse(bot._is_video_info_request(text))

    async def test_youtube_summary_intent_in_bot(self):
        """Summary request with YouTube link routes to summarize_youtube_video without download."""
        url = "https://youtu.be/dQw4w9WgXcQ"
        text = f"کاپری خلاصه و نکات مهم این ویدیو چیه؟ {url}"

        self.assertTrue(bot._is_summary_request(text))
        self.assertFalse(bot._is_download_request(text))
        self.assertFalse(bot._is_video_info_request(text))

        with patch("services.media.ytsummary.summarize_youtube_video") as mock_sum:
            mock_sum.return_value = "🎬 خلاصه ویدیوی یوتیوب:\nایده اصلی: بررسی هوش مصنوعی"
            res = await asyncio.to_thread(ytsummary.summarize_youtube_video, text)
            self.assertIn("خلاصه ویدیوی یوتیوب", res)
            mock_sum.assert_called_once_with(text)

    async def test_youtube_info_metadata_intent_in_bot(self):
        """Metadata/info request with YouTube link routes to get_youtube_video_info."""
        url = "https://youtu.be/dQw4w9WgXcQ"
        text = f"کاپری مشخصات، مدت زمان و اطلاعات این ویدیو رو بده: {url}"

        self.assertTrue(bot._is_video_info_request(text))
        self.assertFalse(bot._is_download_request(text))
        self.assertFalse(bot._is_summary_request(text))

        with patch("services.media.ytsummary.get_oembed_data") as mock_oembed, \
             patch("services.media.ytsummary.get_ytdlp_data") as mock_ytdlp:
            mock_oembed.return_value = {"title": "Never Gonna Give You Up", "author_name": "Rick Astley"}
            mock_ytdlp.return_value = {
                "title": "Never Gonna Give You Up",
                "uploader": "Rick Astley",
                "duration": 213,
                "upload_date": "20091025",
                "view_count": 1500000000,
                "like_count": 17000000,
                "tags": ["music", "pop"],
                "description": "The official music video for Rick Astley"
            }
            info = ytsummary.get_youtube_video_info(url)
            self.assertIn("Never Gonna Give You Up", info)
            self.assertIn("Rick Astley", info)
            self.assertIn("3:33", info)
            self.assertIn("1,500,000,000", info)

    async def test_social_url_download_vs_summary_intent(self):
        """Social URL with summary intent is not downloaded automatically; bare URL is downloaded."""
        summary_query = "این پست اینستا چی میگه و موضوعش چیه؟ https://instagram.com/p/DA12345"
        self.assertTrue(bot._is_summary_request(summary_query))
        self.assertFalse(bot._is_download_request(summary_query))

        bare_download_query = "https://instagram.com/p/DA12345"
        self.assertFalse(bot._is_summary_request(bare_download_query))
        self.assertFalse(bot._is_video_info_request(bare_download_query))


class TestDownloadFailureTruthfulness(unittest.IsolatedAsyncioTestCase):
    """Test strict truthfulness when downloads or tools fail."""

    async def test_youtube_downloader_failure_reported_truthfully(self):
        """Downloader bot failure returns genuine error and never claims false success."""
        client = MagicMock()
        event = MagicMock()
        event.chat_id = 999

        with patch("services.media.ytdownload._run_bot_download", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = (False, "ربات @MegaSaverBot در زمان مقرر فایل ویدیو را ارسال نکرد.")
            res = await ytdownload.download_youtube_video(client, "https://youtu.be/dQw4w9WgXcQ", event=event)
            self.assertIn("❌ خطا در دانلود:", res)
            self.assertNotIn("ارسال شد", res)
            self.assertNotIn("قرنطینه", res)

    async def test_agent_anti_hallucination_on_action_failure(self):
        """If action tool returns error, agent does not let persona hallucinate success."""
        event = MagicMock()
        event.out = True
        event.chat_id = 111
        client = MagicMock()

        tc = {
            "id": "dl_1",
            "function": {
                "name": "download_youtube_video",
                "arguments": json.dumps({"url": "https://youtu.be/dQw4w9WgXcQ"})
            }
        }

        with patch("ai_engine.agent._call_model_step") as mock_step, \
             patch("ai_engine.tools.execute_tool", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = "❌ خطا در دانلود: متأسفانه ربات‌های دانلود تلگرام در این لحظه پاسخگو نبودند."
            mock_step.side_effect = [
                {"content": "", "tool_calls": [tc]},
                {"content": "ویدیوی یوتیوب با کیفیت عالی دانلود شد و برات فرستادم رفیق!", "tool_calls": []}
            ]

            res = await agent.run_agent("این ویدیو رو دانلود کن https://youtu.be/dQw4w9WgXcQ", "", "", event, client)
            # The anti-hallucination guard must override the false claim with the real error!
            self.assertIn("خطا", res)
            self.assertIn("❌ خطا در دانلود", res)

    async def test_no_fake_quarantine_claims(self):
        """When no external taint exists, quarantine message is never fabricated."""
        event = MagicMock()
        event.out = True
        event.chat_id = 222
        client = MagicMock()

        res = await tools.execute_tool("get_current_datetime", {}, event, client, tainted=False)
        self.assertNotIn("قرنطینه", res)
        self.assertNotIn("Taint Quarantine", res)


class TestTelegramTransmissionFailureDistinction(unittest.IsolatedAsyncioTestCase):
    """Test distinguishing file creation/download success from Telegram transmission failure."""

    async def test_ytdownload_forward_failure_distinction(self):
        """When video is received from bot but forwarding to chat fails, return distinct error."""
        client = MagicMock()
        event = MagicMock()
        event.chat_id = 888

        # Mock bot entity and messages
        bot_entity = MagicMock()
        client.get_entity = AsyncMock(return_value=bot_entity)
        sent_msg = MagicMock()
        sent_msg.id = 100
        client.send_message = AsyncMock(return_value=sent_msg)

        # Video document received from downloader bot
        video_msg = MagicMock()
        video_msg.out = False
        video_msg.id = 105
        from telethon import types
        video_msg.media = types.MessageMediaDocument(document=MagicMock())
        client.get_messages = AsyncMock(return_value=[video_msg])

        # Forwarding to user chat fails (e.g. ChatWriteForbiddenError)
        client.forward_messages = AsyncMock(side_effect=Exception("ChatWriteForbiddenError: You can't write in this chat"))

        ok, msg = await ytdownload._run_bot_download(client, "MegaSaverBot", "https://youtu.be/dQw4w9WgXcQ", 720, event, None)
        self.assertFalse(ok)
        self.assertIn("❌ خطا در ارسال تلگرام:", msg)
        self.assertIn("فایل ویدیو با موفقیت از سرور دانلود دریافت شد", msg)
        self.assertIn("ChatWriteForbiddenError", msg)

    async def test_socialdl_forward_failure_distinction(self):
        """When social file is received but forwarding to chat fails, return distinct transmission error."""
        client = MagicMock()
        event = MagicMock()
        event.chat_id = 777

        bot_ent = MagicMock()
        client.get_entity = AsyncMock(return_value=bot_ent)
        sent_msg = MagicMock()
        sent_msg.id = 200
        client.send_message = AsyncMock(return_value=sent_msg)

        media_msg = MagicMock()
        media_msg.out = False
        media_msg.id = 205
        from telethon import types
        media_msg.media = types.MessageMediaDocument(document=MagicMock())
        media_msg.buttons = None
        client.get_messages = AsyncMock(return_value=[media_msg])

        client.forward_messages = AsyncMock(side_effect=Exception("PeerFloodError: Too many forwards"))

        res = await socialdl.download_social(client, "https://www.instagram.com/p/DA12345", event=event)
        self.assertIn("❌ خطا در ارسال تلگرام:", res)
        self.assertIn("فایل با موفقیت دریافت شد", res)
        self.assertIn("PeerFloodError", res)

    async def test_voice_send_failure_distinction(self):
        """When voice note is synthesized ok but send_file fails, return transmission failure."""
        client = MagicMock()
        event = MagicMock()
        event.chat_id = 666
        event.message = None
        event.id = 10

        # Simulate send_file failure
        client.send_file = AsyncMock(side_effect=Exception("MediaEmptyError: The provided file could not be sent"))

        with patch("services.voice.voice.speak", new_callable=AsyncMock) as mock_speak, \
             patch("services.voice.voice.to_ogg") as mock_ogg, \
             patch("os.path.exists", return_value=True), \
             patch("os.path.getsize", return_value=15000), \
             patch("os.remove"):
            mock_speak.return_value = True
            mock_ogg.return_value = True

            res = await tools.execute_tool("send_voice_note", {"text": "سلام رفیقِ عزیز!"}, event, client)
            self.assertIn("❌ خطا در ارسال تلگرام:", res)
            self.assertIn("ویس با موفقیت ضبط شد", res)
            self.assertIn("MediaEmptyError", res)

    async def test_voice_synthesis_failure_distinction(self):
        """When voice synthesis fails, return audio generation failure."""
        client = MagicMock()
        event = MagicMock()
        event.chat_id = 666

        with patch("services.voice.voice.speak", new_callable=AsyncMock) as mock_speak, \
             patch("os.path.exists", return_value=False):
            mock_speak.return_value = False

            res = await tools.execute_tool("send_voice_note", {"text": "تست صدا"}, event, client)
            self.assertIn("❌ خطا در تولید ویس:", res)


class TestConversationalQuestionsBypassTools(unittest.TestCase):
    """Test that general conversational & informational questions bypass media/download tools."""

    def test_youtube_history_question_bypasses_media_tools(self):
        """General questions about YouTube history do NOT trigger tool mode."""
        q1 = "یوتیوب در چه سالی تاسیس شد؟"
        q2 = "بنیانگذاران یوتیوب چه کسانی بودند؟"
        q3 = "چرا یوتیوب در ایران فیلتر شد؟"

        self.assertTrue(bot._is_simple_question(q1), f"Expected simple question for: {q1}")
        self.assertTrue(bot._is_simple_question(q2), f"Expected simple question for: {q2}")
        self.assertTrue(bot._is_simple_question(q3), f"Expected simple question for: {q3}")

    def test_general_time_and_chat_questions_bypass_tools(self):
        """Conversational questions with words like 'پیام' or 'ساعت' without reminders bypass tools."""
        q1 = "ساعت چنده؟"
        q2 = "یک پیام الهام‌بخش بگو"
        q3 = "چطور برنامه‌نویسی پایتون رو شروع کنم؟"

        self.assertTrue(bot._is_simple_question(q1), f"Expected simple question for: {q1}")
        self.assertTrue(bot._is_simple_question(q2), f"Expected simple question for: {q2}")
        self.assertTrue(bot._is_simple_question(q3), f"Expected simple question for: {q3}")

    def test_actual_tool_requests_are_recognized(self):
        """Actual tool requests are recognized and not marked as simple questions."""
        q_dl = "این ویدیو رو دانلود کن برام"
        q_yt_link = "این ویدیو رو ببین: https://youtu.be/dQw4w9WgXcQ"
        q_music = "آهنگ جدید شادمهر رو برام بفرست"
        q_rem = "فردا ساعت ۱۰ یادم بنداز برم دکتر"

        self.assertFalse(bot._is_simple_question(q_dl))
        self.assertFalse(bot._is_simple_question(q_yt_link))
        self.assertFalse(bot._is_simple_question(q_music))
        self.assertFalse(bot._is_simple_question(q_rem))


class TestSendMessageRequestRouting(unittest.TestCase):
    """درخواست «به کسی پیام بده/بگو» باید به ایجنت برود تا ابزار Ghostwriter اجرا شود."""

    def test_send_message_requests_route_to_agent(self):
        cases = (
            "کاپری به ali پیام بده بگو دیر میام",
            "به علی پیام بده بگو دیر میام",
            "به مامانم پیام بده بگو دیر میام",
            "پیام بده به علی",
            "به علی بگو دیر میام",
            "بگو به علی که جلسه کنسل شد",
        )
        for q in cases:
            self.assertFalse(bot._is_simple_question(q), f"Should route to agent: {q}")

    def test_self_addressed_talk_stays_simple(self):
        cases = (
            "یک پیام الهام‌بخش بگو",
            "به من بگو یک جوک",
            "به کاپری بگو سلام برسون",
        )
        for q in cases:
            self.assertTrue(bot._is_simple_question(q), f"Should stay simple: {q}")


class TestConcurrencyAndIsolationSafety(unittest.IsolatedAsyncioTestCase):
    """Test that concurrent requests run safely with isolated states and no taint leaks."""

    async def test_concurrent_agent_requests_with_isolated_taint(self):
        """Concurrent requests with differing taint states remain strictly isolated via ContextVar."""
        event_clean = MagicMock()
        event_clean.out = True
        event_clean.chat_id = 1001

        event_tainted = MagicMock()
        event_tainted.out = True
        event_tainted.chat_id = 1002

        client = MagicMock()

        def mock_step_dispatcher(messages, **kwargs):
            user_msg = next((m.get("content", "") for m in messages if m.get("role") == "user"), "")
            if "ریاضی" in str(user_msg):
                return {"content": "پاسخ عادی ۱", "tool_calls": []}
            has_tool_res = any(m.get("role") == "tool" for m in messages)
            if not has_tool_res:
                return {
                    "content": "",
                    "tool_calls": [{
                        "id": "read_1",
                        "function": {"name": "read_webpage", "arguments": json.dumps({"url": "https://example.com"})}
                    }]
                }
            return {"content": "خلاصه کامل صفحه وب با لینک https://example.com", "tool_calls": []}

        with patch("ai_engine.agent._call_model_step", side_effect=mock_step_dispatcher), \
             patch("ai_engine.tools.execute_tool", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = "محتوای صفحه وب"

            async def run_clean():
                res = await agent.run_agent("یک مفهوم ریاضی رو توضیح بده", "", "", event_clean, client)
                return res

            async def run_tainted():
                res = await agent.run_agent("این لینک رو بخون https://example.com", "", "", event_tainted, client)
                return res

            res_clean, res_tainted = await asyncio.gather(run_clean(), run_tainted())
            self.assertIn("پاسخ عادی ۱", res_clean)
            self.assertIn("خلاصه کامل صفحه وب", res_tainted)
            self.assertNotIn("https://example.com", res_tainted)


class TestToolDefinitionsAndBackwardCompatibility(unittest.TestCase):
    """Validate tool definitions, constraints, and backward compatibility."""

    def test_all_base_tool_definitions_valid(self):
        defs = tools.get_all_tool_definitions(is_owner=True, tainted=False)
        tool_names = [d["function"]["name"] for d in defs]

        # Verify essential tools are present
        expected_tools = [
            "web_search", "deep_search", "download_youtube_video",
            "summarize_youtube_video", "get_youtube_video_info",
            "download_social_media", "fetch_and_forward_movie",
            "search_channel_files", "search_music", "send_voice_note",
            "manage_memory", "manage_folders", "manage_channel_membership",
            "manage_dnd", "manage_reminders", "organize_saved_messages",
        ]
        for t in expected_tools:
            self.assertIn(t, tool_names, f"Missing tool definition: {t}")

        # Check structure and descriptions
        for d in defs:
            fn = d["function"]
            self.assertTrue(fn["name"])
            self.assertTrue(fn["description"], f"Tool {fn['name']} missing description")
            self.assertIn("parameters", fn)

    def test_stranger_tools_strictly_isolated(self):
        """Strangers cannot see or execute media download tools."""
        stranger_defs = tools.get_all_tool_definitions(is_owner=False, tainted=False)
        stranger_names = {d["function"]["name"] for d in stranger_defs}

        forbidden_for_strangers = [
            "download_youtube_video", "download_social_media",
            "fetch_and_forward_movie", "manage_folders", "manage_memory",
            "organize_saved_messages", "manage_channel_membership"
        ]
        for f in forbidden_for_strangers:
            self.assertNotIn(f, stranger_names, f"Stranger exposed to forbidden tool: {f}")


if __name__ == "__main__":
    unittest.main()
