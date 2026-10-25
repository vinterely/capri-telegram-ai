import asyncio
import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core import settings
from services.voice import jarvis_bot, voice


class TestVoiceMultiKeyAndDiacritics(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        voice._tts_cooldowns.clear()

    def test_has_sufficient_diacritics(self):
        plain = "سلام رفیق حالت چطوره من اینجام تا کمکت کنم"
        self.assertFalse(voice.has_sufficient_diacritics(plain))

        vocalized = "سَلام رَفیق! حالِت چِطورِه؟ مَن اینجام تا کُمَکِت کُنَم."
        self.assertTrue(voice.has_sufficient_diacritics(vocalized))

    async def test_ensure_persian_vowels_already_vocalized(self):
        vocalized = "سَلام رَفیق! حالِت چِطورِه؟"
        result = await voice.ensure_persian_vowels(vocalized)
        self.assertEqual(result, vocalized)

    async def test_ensure_persian_vowels_calls_ai_when_plain(self):
        plain = "سلام رفیق"
        mock_resp = MagicMock()
        mock_resp.text = "سَلام رَفیق"

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_resp

        with patch("core.config.GEMINI_API_KEYS", ["MOCK_KEY"]), patch("ai_engine.ai._get_client", return_value=mock_client):
            result = await voice.ensure_persian_vowels(plain)
            self.assertEqual(result, "سَلام رَفیق")

    async def test_speak_gemini_rotates_on_429_quota(self):
        out_file = "/tmp/test_voice_out.mp3"

        key1_mock_client = MagicMock()
        key1_mock_client.models.generate_content.side_effect = Exception("429 RESOURCE_EXHAUSTED. Quota exceeded. retryDelay: '3600s'")

        key2_mock_client = MagicMock()
        mock_cand = MagicMock()
        mock_part = MagicMock()
        mock_part.inline_data = MagicMock(data=b"dummy_audio_bytes")
        mock_cand.content.parts = [mock_part]
        mock_resp = MagicMock(candidates=[mock_cand])
        key2_mock_client.models.generate_content.return_value = mock_resp

        def fake_get_client(key=None):
            if key == "KEY1":
                return key1_mock_client
            return key2_mock_client

        with patch("core.config.GEMINI_API_KEYS", ["KEY1", "KEY2"]), \
             patch("ai_engine.ai._get_client", side_effect=fake_get_client), \
             patch("builtins.open", unittest.mock.mock_open()), \
             patch("services.voice.voice.is_valid_audio", return_value=True):

            ok = await voice.speak_gemini("سَلام رَفیق!", out_file)
            self.assertTrue(ok)
            # Verify cooldown was recorded for KEY1
            self.assertTrue(voice._is_on_cooldown("KEY1", voice.GEMINI_TTS_MODELS[0]))

    async def test_speak_gemini_fallback_to_edge_tts(self):
        out_file = "/tmp/test_voice_out.mp3"

        # Both keys fail with 429
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception("429 RESOURCE_EXHAUSTED")

        mock_edge_comm = AsyncMock()
        mock_edge_comm.save = AsyncMock()

        with patch("core.config.GEMINI_API_KEYS", ["KEY1", "KEY2"]), \
             patch("ai_engine.ai._get_client", return_value=mock_client), \
             patch("edge_tts.Communicate", return_value=mock_edge_comm), \
             patch("services.voice.voice.is_valid_audio", return_value=True):

            ok = await voice.speak_gemini("سَلام رَفیق!", out_file)
            self.assertTrue(ok)
            mock_edge_comm.save.assert_awaited_once_with(out_file)

    def test_jarvis_parse_voice_and_tone(self):
        # 1. سارا 6 -> گوینده سارا، لحن حماسی (6)
        v, t = jarvis_bot.parse_voice_and_tone("سارا 6")
        self.assertIsNotNone(v)
        self.assertEqual(v["name"], "سارا")
        self.assertIsNotNone(t)
        self.assertEqual(t["name"], "حماسی")
        self.assertEqual(t["id"], 6)

        # 2. باران 2 -> گوینده باران، لحن صمیمی (2)
        v, t = jarvis_bot.parse_voice_and_tone("باران 2")
        self.assertEqual(v["name"], "باران")
        self.assertEqual(t["name"], "صمیمی")

        # 3. فقط نام گوینده
        v, t = jarvis_bot.parse_voice_and_tone("کیوان")
        self.assertEqual(v["name"], "کیوان")
        self.assertIsNone(t)

        # 4. فقط نام لحن
        v, t = jarvis_bot.parse_voice_and_tone("حماسی")
        self.assertIsNone(v)
        self.assertEqual(t["name"], "حماسی")

    def test_bot_parse_voice_command_jarvis(self):
        import bot
        # کاپری صدای ربات
        cmd = bot.parse_voice_command("کاپری صدای ربات")
        self.assertIsNotNone(cmd)
        self.assertEqual(cmd.get("action"), "set_engine")
        self.assertEqual(cmd.get("engine"), "jarvis")

        # کاپری ربات سارا 6
        cmd = bot.parse_voice_command("کاپری ربات سارا 6")
        self.assertIsNotNone(cmd)
        self.assertEqual(cmd.get("action"), "set_jarvis")
        self.assertEqual(cmd["voice"]["name"], "سارا")
        self.assertEqual(cmd["tone"]["id"], 6)

    async def test_configure_jarvis(self):
        mock_client = AsyncMock()
        mock_client.get_entity = AsyncMock(return_value="fake_bot_entity")
        mock_client.send_message = AsyncMock()

        v_info = {"id": 2, "name": "سارا", "gender": "زنانه", "desc": ""}
        t_info = {"id": 6, "name": "حماسی", "desc": ""}

        with patch("core.settings.set_tts_engine") as mock_set_engine, \
             patch("core.settings.set_jarvis_voice") as mock_set_voice, \
             patch("core.settings.set_jarvis_tone") as mock_set_tone:

            ok, msg = await jarvis_bot.configure_jarvis(mock_client, v_info, t_info)
            self.assertTrue(ok)
            self.assertIn("سارا", msg)
            self.assertIn("حماسی", msg)
            mock_client.send_message.assert_any_await("fake_bot_entity", "/voice2")
            mock_client.send_message.assert_any_await("fake_bot_entity", "/tone6")
            mock_set_engine.assert_called_with("jarvis")
            mock_set_voice.assert_called_with("2")
            mock_set_tone.assert_called_with("6")

    async def test_speak_jarvis_success(self):
        mock_client = AsyncMock()
        mock_client.get_entity = AsyncMock(return_value="bot_entity")
        sent_mock = MagicMock(id=100)
        mock_client.send_message = AsyncMock(return_value=sent_mock)

        # Incoming voice message from bot
        reply_mock = MagicMock()
        reply_mock.out = False
        reply_mock.id = 105
        reply_mock.voice = MagicMock()
        reply_mock.media = MagicMock()

        mock_client.get_messages = AsyncMock(return_value=[reply_mock])
        mock_client.download_media = AsyncMock(return_value="/tmp/test_jarvis.ogg")

        with patch("os.path.exists", return_value=True), \
             patch("os.path.getsize", return_value=1234), \
             patch("services.voice.voice.is_valid_audio", return_value=True):

            ok = await jarvis_bot.speak_jarvis(mock_client, "متن تستی", "/tmp/test_jarvis.ogg")
            self.assertTrue(ok)
            mock_client.send_message.assert_awaited_once_with("bot_entity", "متن تستی")
            mock_client.download_media.assert_awaited_once_with(reply_mock.media, file="/tmp/test_jarvis.ogg")

    async def test_speak_fallback_when_jarvis_fails(self):
        mock_client = AsyncMock()
        # Jarvis bot times out
        with patch("services.voice.jarvis_bot.speak_jarvis", return_value=False), \
             patch.object(settings, "get_tts_engine", return_value="jarvis"), \
             patch("services.voice.voice.speak_gemini", return_value=True) as mock_gemini:

            ok = await voice.speak("سَلام رَفیق!", "/tmp/out.mp3", client=mock_client)
            self.assertTrue(ok)
            mock_gemini.assert_awaited_once()

    def test_is_valid_audio(self):
        # 1. فایل وجود ندارد
        self.assertFalse(voice.is_valid_audio("/non_existent_file.mp3"))

        # 2. فایل کمتر از ۱۰۰۰ بایت (مانند هدر خالی ۱۳۷ بایتی)
        with patch("os.path.exists", return_value=True), \
             patch("os.path.getsize", return_value=137):
            self.assertFalse(voice.is_valid_audio("/tmp/corrupt.mp3"))

        # 3. فایل سالم بالای ۱۰۰۰ بایت
        with patch("os.path.exists", return_value=True), \
             patch("os.path.getsize", return_value=25000), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            self.assertTrue(voice.is_valid_audio("/tmp/valid.mp3"))

    async def test_jarvis_rejects_empty_audio_and_deletes_corrupt(self):
        mock_client = AsyncMock()
        mock_client.get_entity = AsyncMock(return_value="bot_entity")
        sent_mock = MagicMock(id=100)
        mock_client.send_message = AsyncMock(return_value=sent_mock)

        reply_mock = MagicMock()
        reply_mock.out = False
        reply_mock.id = 105
        reply_mock.voice = MagicMock()
        reply_mock.media = MagicMock()

        mock_client.get_messages = AsyncMock(return_value=[reply_mock])
        mock_client.download_media = AsyncMock(return_value="/tmp/test_corrupt.ogg")

        # فایل دانلود شده ۱۳۷ بایت است (هدر خالی)
        with patch("os.path.exists", return_value=True), \
             patch("os.path.getsize", return_value=137), \
             patch("os.remove") as mock_remove:

            ok = await jarvis_bot.speak_jarvis(mock_client, "متن تستی", "/tmp/test_corrupt.ogg")
            # باید رد شود و فایل معیوب پاک گردد
            self.assertFalse(ok)
            mock_remove.assert_called()

    async def test_tools_send_voice_note_emergency_fallback(self):
        from ai_engine import tools
        mock_client = AsyncMock()
        mock_event = MagicMock(chat_id=123456)
        mock_status = AsyncMock()

        vmsg = MagicMock(id=999)
        mock_client.send_file = AsyncMock(return_value=vmsg)

        # فرض کنیم speak اولیه یا to_ogg ناموفق بوده است
        with patch("services.voice.voice.speak", return_value=False), \
             patch("edge_tts.Communicate") as mock_edge, \
             patch("services.voice.voice.to_ogg", return_value=True), \
             patch("os.path.exists", return_value=True), \
             patch("os.path.getsize", return_value=15000):

            edge_instance = AsyncMock()
            edge_instance.save = AsyncMock()
            mock_edge.return_value = edge_instance

            res = await tools.execute_tool(
                "send_voice_note",
                {"text": "متن تستی انگیزشی"},
                event=mock_event,
                client=mock_client,
                status=mock_status
            )

            self.assertTrue(res.startswith("__VOICE_SENT__:"))
            mock_client.send_file.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
