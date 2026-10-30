import contextlib
import os
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import bot
from services.voice import live

CHAT_ID = -100777


class TestLiveCommands(unittest.TestCase):
    def test_start_and_exit_commands(self):
        self.assertEqual(live.parse_command("کاپری وارد گفتگو صوتی شو"), "on")
        self.assertEqual(live.parse_command("شروع مکالمه صوتی"), "on")
        self.assertEqual(live.parse_command("گفتگوی صوتی"), "on")
        self.assertEqual(live.parse_command("خروج از گفتگو صوتی"), "off")
        self.assertEqual(live.parse_command("گفتگوی صوتی رو ببند"), "off")

    def test_does_not_collide_with_voice_mode(self):
        self.assertIsNone(live.parse_command("حالت صوتی روشن"))
        self.assertIsNone(live.parse_command("حالت ویس خاموش"))
        self.assertIsNone(live.parse_command("سلام"))

    def test_exit_wins_over_start_word(self):
        self.assertEqual(live.parse_command("خروج از گفتگو صوتی"), "off")


class TestLiveSessions(unittest.TestCase):
    def tearDown(self):
        live.deactivate(CHAT_ID)

    def test_activate_and_deactivate(self):
        live.activate(CHAT_ID)
        self.assertTrue(live.is_active(CHAT_ID))
        self.assertTrue(live.deactivate(CHAT_ID))
        self.assertFalse(live.is_active(CHAT_ID))
        self.assertFalse(live.deactivate(CHAT_ID))

    def test_ttl_expiry(self):
        with patch.object(live, "_now", return_value=1000.0):
            live.activate(CHAT_ID)
        with patch.object(live, "_now", return_value=1000.0 + live.SESSION_TTL + 1):
            self.assertFalse(live.is_active(CHAT_ID))

    def test_history_is_capped(self):
        live.activate(CHAT_ID)
        for i in range(6):
            live._remember(CHAT_ID, f"u{i}", f"a{i}")
        self.assertEqual(live.history_len(CHAT_ID), live.MAX_HISTORY)

    def test_system_instruction_contains_history(self):
        live.activate(CHAT_ID)
        live._remember(CHAT_ID, "سلام", "سلام! خوبی؟")
        text = live._system_instruction(CHAT_ID)
        self.assertIn("سلام", text)
        self.assertIn("خوبی", text)

    def test_history_not_stored_without_input(self):
        live.activate(CHAT_ID)
        live._remember(CHAT_ID, "", "فقط پاسخ")
        self.assertEqual(live.history_len(CHAT_ID), 0)


class _Base(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._stack = contextlib.ExitStack()
        self._stack.enter_context(patch.object(bot, "self_sent", bot._BoundedIdSet()))
        self._stack.enter_context(patch.object(bot.drafter, "get_pending_draft", return_value=None))
        self._stack.enter_context(patch.object(bot, "get_reply_info", AsyncMock(return_value={})))
        self._stack.enter_context(patch.object(bot.home, "is_home_backup_message", return_value=False))
        self._stack.enter_context(patch.object(bot.home, "is_home_chat", return_value=False))
        self._stack.enter_context(patch.object(bot.roleplay, "handle", AsyncMock(return_value=False)))
        self._stack.enter_context(patch.object(bot, "_media_target", AsyncMock(return_value=None)))
        self._stack.enter_context(patch.object(bot.settings, "get_voice_mode", return_value=False))
        live.deactivate(CHAT_ID)
        bot.pending.pop(str(CHAT_ID), None)

    def tearDown(self):
        bot.pending.pop(str(CHAT_ID), None)
        live.deactivate(CHAT_ID)
        self._stack.close()

    def _event(self, text="", voice=False):
        status = MagicMock(name="status")
        status.id = 999
        status.edit = AsyncMock()
        status.delete = AsyncMock()

        event = MagicMock()
        event.chat_id = CHAT_ID
        event.id = 101
        event.raw_text = text
        event.reply_to_msg_id = None
        event.out = True
        event.fwd_from = None
        event.via_bot_id = None
        event.via_bot = None

        message = MagicMock()
        message.fwd_from = None
        message.via_bot_id = None
        message.via_bot = None
        message.voice = MagicMock() if voice else None
        message.video_note = None
        message.media = None
        event.message = message
        event.reply = AsyncMock(return_value=status)
        return event, status

    def _client_patches(self, respond_mock):
        fake_client = MagicMock()
        fake_client.download_media = AsyncMock()
        fake_client.send_file = AsyncMock()
        self.fake_client = fake_client
        return [
            patch.object(bot, "client", fake_client),
            patch.object(bot.ops, "register", MagicMock()),
            patch.object(bot, "_safe_unlink", MagicMock()),
            patch.object(live, "respond", respond_mock),
        ]


class TestHandleLiveVoice(_Base):
    async def test_voice_sends_native_reply(self):
        event, status = self._event(voice=True)
        respond = AsyncMock(return_value=("reply.ogg", "سلام! خوبم، تو چطوری؟", None))
        tr = MagicMock()
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self._client_patches(respond) + [patch.object(bot.config, "DOWNLOAD_DIR", tmp)]
            with ctx[0], ctx[1], ctx[2], ctx[3], ctx[4], patch.object(bot.voice, "transcribe", tr):
                await bot._handle_live_voice(event)
        respond.assert_awaited_once()
        self.fake_client.send_file.assert_awaited_once()
        self.assertTrue(self.fake_client.send_file.await_args.kwargs.get("voice_note"))
        status.delete.assert_awaited_once()
        self.assertFalse(tr.called)

    async def test_text_fallback_when_no_audio(self):
        event, status = self._event(voice=True)
        respond = AsyncMock(return_value=(None, "متن پاسخ", None))
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self._client_patches(respond) + [patch.object(bot.config, "DOWNLOAD_DIR", tmp)]
            with ctx[0], ctx[1], ctx[2], ctx[3], ctx[4]:
                await bot._handle_live_voice(event)
        self.fake_client.send_file.assert_not_awaited()
        self.assertTrue(any("متن پاسخ" in str(c.args[0]) for c in status.edit.await_args_list if c.args))

    async def test_error_is_reported(self):
        event, status = self._event(voice=True)
        respond = AsyncMock(return_value=(None, None, "سهمیه پر شده"))
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self._client_patches(respond) + [patch.object(bot.config, "DOWNLOAD_DIR", tmp)]
            with ctx[0], ctx[1], ctx[2], ctx[3], ctx[4]:
                await bot._handle_live_voice(event)
        self.fake_client.send_file.assert_not_awaited()
        self.assertTrue(any("سهمیه پر شده" in str(c.args[0]) for c in status.edit.await_args_list if c.args))


class TestRouting(_Base):
    async def test_start_command_activates_and_skips_ai(self):
        event, status = self._event(text="کاپری وارد گفتگو صوتی شو")
        with patch.object(bot.ai, "answer_quick", MagicMock()) as aq:
            await bot.on_outgoing(event)
        self.assertTrue(live.is_active(CHAT_ID))
        aq.assert_not_called()
        self.assertTrue(any("فعال" in str(c.args[0]) for c in status.edit.await_args_list if c.args))

    async def test_exit_command_deactivates(self):
        live.activate(CHAT_ID)
        event, status = self._event(text="کاپری خروج از گفتگو صوتی")
        await bot.on_outgoing(event)
        self.assertFalse(live.is_active(CHAT_ID))

    async def test_active_live_intercepts_voice_before_stt(self):
        live.activate(CHAT_ID)
        event, status = self._event(voice=True)
        handle = AsyncMock()
        with patch.object(bot, "_handle_live_voice", handle), \
                patch.object(bot, "_transcribe_voice_mode", AsyncMock()) as tr:
            await bot.on_outgoing(event)
        handle.assert_awaited_once()
        tr.assert_not_awaited()

    async def test_voice_ignored_when_live_inactive(self):
        event, status = self._event(voice=True)
        handle = AsyncMock()
        with patch.object(bot, "_handle_live_voice", handle):
            await bot.on_outgoing(event)
        handle.assert_not_awaited()
        event.reply.assert_not_called()


class TestRespondGuards(unittest.IsolatedAsyncioTestCase):
    async def test_missing_models(self):
        with patch.object(live.config, "GEMINI_LIVE_MODELS", []):
            ogg, text, err = await live.respond("c", "x.ogg")
        self.assertIsNone(ogg)
        self.assertIn("تنظیم", err)

    async def test_conversion_failure(self):
        with patch.object(live.config, "GEMINI_LIVE_MODELS", ["m"]), \
                patch.object(live.config, "GEMINI_API_KEYS", ["k"]), \
                patch.object(live, "ogg_to_pcm16", return_value=False):
            ogg, text, err = await live.respond("c", "x.ogg")
        self.assertIsNone(ogg)
        self.assertIn("ffmpeg", err)


if __name__ == "__main__":
    unittest.main()
