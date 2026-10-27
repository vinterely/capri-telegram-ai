import asyncio
import contextlib
import datetime
import os
import sys
import tempfile
import types as pytypes
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from telethon import functions, types as tl_types

import bot
from services.telegram import channel_summary, cleaner, home
from services.voice import voice

CHAT_ID = -1001234567890


def _msg(mid, out=True, text="متن"):
    m = MagicMock()
    m.id = mid
    m.out = out
    m.raw_text = text
    m.message = text
    m.action = None
    m.media = None
    m.date = datetime.datetime(2026, 10, 27, 12, 0, tzinfo=datetime.timezone.utc)
    return m


def _forum_topic(tid, title):
    return tl_types.ForumTopic(
        id=tid,
        date=None,
        peer=tl_types.PeerChannel(channel_id=1),
        title=title,
        icon_color=0,
        top_message=1,
        read_inbox_max_id=0,
        read_outbox_max_id=0,
        unread_count=0,
        unread_mentions_count=0,
        unread_reactions_count=0,
        unread_poll_votes_count=0,
        from_id=None,
        notify_settings=tl_types.PeerNotifySettings(show_previews=None, silent=None, mute_until=None),
    )


class _Base(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._stack = contextlib.ExitStack()
        self._stack.enter_context(patch.object(bot, "self_sent", bot._BoundedIdSet()))
        self._stack.enter_context(patch.object(bot.drafter, "get_pending_draft", return_value=None))
        self._stack.enter_context(patch.object(bot, "get_reply_info", AsyncMock(return_value={})))
        self._stack.enter_context(patch.object(bot.home, "is_home_backup_message", return_value=False))
        self._stack.enter_context(patch.object(bot.roleplay, "handle", AsyncMock(return_value=False)))
        self._stack.enter_context(patch.object(bot, "_media_target", AsyncMock(return_value=None)))
        self._stack.enter_context(patch.object(bot.settings, "get_voice_mode", return_value=False))
        self._stack.enter_context(patch.object(bot, "_transcribe_voice_mode", AsyncMock(return_value=None)))
        bot.pending.pop(str(CHAT_ID), None)

    def tearDown(self):
        bot.pending.pop(str(CHAT_ID), None)
        self._stack.close()

    def _event(self, text="", chat_id=CHAT_ID, msg_id=101, voice=False):
        status = MagicMock(name="status")
        status.id = 999
        status.edit = AsyncMock()
        status.delete = AsyncMock()

        event = MagicMock()
        event.chat_id = chat_id
        event.id = msg_id
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


class TestVoiceModeSettings(unittest.IsolatedAsyncioTestCase):
    async def test_voice_mode_persisted_in_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "settings.json")
            with patch.object(bot.settings, "FILE", path):
                bot.settings.set_voice_mode(True)
                self.assertTrue(bot.settings.get_voice_mode())
                bot.settings.set_voice_mode(False)
                self.assertFalse(bot.settings.get_voice_mode())


class TestVoiceModeTranscribe(unittest.IsolatedAsyncioTestCase):
    async def test_transcribe_downloads_and_cleans_file(self):
        fake_client = MagicMock()
        fake_client.download_media = AsyncMock()
        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(bot.config, "DOWNLOAD_DIR", tmp), \
                patch.object(bot, "client", fake_client), \
                patch.object(bot.voice, "transcribe", MagicMock(return_value="سلام")) as tr:
            text = await bot._transcribe_voice_mode(MagicMock())
            tr.assert_called_once()
            self.assertEqual(os.listdir(tmp), [])
        self.assertEqual(text, "سلام")

    async def test_transcribe_empty_returns_none(self):
        fake_client = MagicMock()
        fake_client.download_media = AsyncMock()
        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(bot.config, "DOWNLOAD_DIR", tmp), \
                patch.object(bot, "client", fake_client), \
                patch.object(bot.voice, "transcribe", MagicMock(return_value="   ")):
            self.assertIsNone(await bot._transcribe_voice_mode(MagicMock()))


class TestVoiceMode(_Base):
    async def test_toggle_parsing(self):
        self.assertTrue(bot._parse_voice_mode_command("کاپری حالت ویس روشن"))
        self.assertTrue(bot._parse_voice_mode_command("ویس مود رو فعال کن"))
        self.assertFalse(bot._parse_voice_mode_command("کاپری حالت ویس رو خاموش کن"))
        self.assertFalse(bot._parse_voice_mode_command("ویس مود غیرفعال"))
        self.assertIsNone(bot._parse_voice_mode_command("ویس مود"))
        self.assertIsNone(bot._parse_voice_mode_command("سلام"))

    async def test_voice_mode_on_runs_transcribed_command(self):
        event, status = self._event(text="", voice=True)
        with patch.object(bot.settings, "get_voice_mode", return_value=True), \
                patch.object(bot.home, "is_home_chat", return_value=False), \
                patch.object(bot, "_transcribe_voice_mode",
                             AsyncMock(return_value="۵ پیام پاک کن")) as tr, \
                patch.object(bot.cleaner, "run_delete",
                             AsyncMock(return_value={"message": "انجام شد"})) as rd:
            await bot.on_outgoing(event)
        tr.assert_awaited_once()
        rd.assert_awaited_once()
        self.assertEqual(rd.await_args.args[1], CHAT_ID)
        self.assertEqual(rd.await_args.args[3], 5)
        self.assertIn(999, rd.await_args.kwargs["skip_ids"])

    async def test_voice_mode_off_ignores_voice_without_trigger(self):
        event, status = self._event(text="", voice=True)
        with patch.object(bot.settings, "get_voice_mode", return_value=False), \
                patch.object(bot.home, "is_home_chat", return_value=False), \
                patch.object(bot, "_transcribe_voice_mode", AsyncMock()) as tr:
            await bot.on_outgoing(event)
        tr.assert_not_awaited()
        event.reply.assert_not_called()

    async def _run_simple(self, event):
        with patch.object(bot.home, "is_home_chat", return_value=False), \
                patch.object(bot, "_is_web_question", return_value=False), \
                patch.object(bot, "_is_simple_question", return_value=True), \
                patch.object(bot.ai, "answer_quick", MagicMock(return_value="خوبم، مرسی")), \
                patch.object(bot, "get_context", AsyncMock(return_value="ctx")), \
                patch.object(bot.memory, "get_event_memory_scope", return_value="scope"), \
                patch.object(bot.memory, "load_history", return_value=[]), \
                patch.object(bot.memory, "relevant_facts", return_value=""), \
                patch.object(bot.memory, "remember_exchange", MagicMock()), \
                patch.object(bot, "_trigger_learn", AsyncMock()):
            await bot.on_outgoing(event)
            await asyncio.sleep(0)

    async def test_plain_question_replies_text_only(self):
        event, status = self._event(text="کاپری خوبی؟")
        with patch.object(bot.voice, "speak", AsyncMock()) as spk:
            await self._run_simple(event)
        spk.assert_not_awaited()
        texts = [str(c.args[0]) for c in status.edit.await_args_list if c.args]
        self.assertTrue(any("خوبم، مرسی" in t for t in texts), texts)

    async def test_explicit_voice_request_uses_voice_reply(self):
        event, status = self._event(text="کاپری خوبی؟ اینو با ویس جواب بده")
        with patch.object(bot, "_send_voice_answer", AsyncMock(return_value=True)) as va:
            await self._run_simple(event)
        va.assert_awaited_once()
        self.assertEqual(va.await_args.kwargs.get("scope_id"), "scope")

    async def test_unclear_voice_asks_instead_of_guessing(self):
        event, status = self._event(text="", voice=True)
        with patch.object(bot.settings, "get_voice_mode", return_value=True), \
                patch.object(bot.home, "is_home_chat", return_value=False), \
                patch.object(bot, "_transcribe_voice_mode", AsyncMock(return_value=None)), \
                patch.object(bot.cleaner, "run_delete", AsyncMock()) as rd:
            await bot.on_outgoing(event)
        rd.assert_not_awaited()
        event.reply.assert_awaited_once()
        self.assertIn("متوجه", event.reply.await_args.args[0])


class TestCapriHomeRouting(_Base):
    async def test_owner_message_in_home_without_trigger_is_answered(self):
        event, status = self._event(text="سلام")
        with patch.object(bot.home, "is_home_chat", return_value=True), \
                patch.object(bot, "_is_web_question", return_value=False), \
                patch.object(bot, "_is_simple_question", return_value=True), \
                patch.object(bot.ai, "answer_quick", MagicMock(return_value="سلام! خوبی؟")), \
                patch.object(bot, "get_context", AsyncMock(return_value="ctx")), \
                patch.object(bot.memory, "get_event_memory_scope", return_value="scope"), \
                patch.object(bot.memory, "load_history", return_value=[]), \
                patch.object(bot.memory, "relevant_facts", return_value=""), \
                patch.object(bot.memory, "remember_exchange", MagicMock()), \
                patch.object(bot, "_trigger_learn", AsyncMock()):
            await bot.on_outgoing(event)
            await asyncio.sleep(0)
        texts = [str(c.args[0]) for c in status.edit.await_args_list if c.args]
        self.assertTrue(any("سلام! خوبی؟" in t for t in texts), texts)

    async def test_home_message_from_non_owner_is_rejected(self):
        event = MagicMock()
        event.chat_id = CHAT_ID
        event.raw_text = "کاپری ۵ پیام پاک کن"
        event.out = False
        event.sender_id = 424242
        event.fwd_from = None
        event.via_bot_id = None
        event.via_bot = None
        message = MagicMock()
        message.fwd_from = None
        message.via_bot_id = None
        message.via_bot = None
        event.message = message
        event.get_sender = AsyncMock(return_value=MagicMock(bot=False, first_name="کاربر"))
        event.reply = AsyncMock()

        with patch.object(bot.home, "is_home_chat", return_value=True), \
                patch.object(bot.access, "is_allowed", return_value=True), \
                patch.object(bot.access, "is_denied", return_value=False), \
                patch.object(bot.cleaner, "run_delete", AsyncMock()) as rd:
            await bot.on_incoming_pm(event)
        rd.assert_not_awaited()
        event.reply.assert_not_called()

    async def test_home_backup_topic_messages_are_ignored(self):
        event, status = self._event(text="کاپری سلام")
        with patch.object(bot.home, "is_home_chat", return_value=True), \
                patch.object(bot.home, "is_home_backup_message", return_value=True):
            await bot.on_outgoing(event)
        event.reply.assert_not_called()


class TestCleanerBackup(unittest.IsolatedAsyncioTestCase):
    class _Client:
        def __init__(self, msgs):
            self.messages = msgs
            self.deleted = []
            self.sent = []

        async def get_input_entity(self, x):
            return "home-ent"

        async def get_entity(self, x):
            return MagicMock(title="چت تست")

        async def send_message(self, *a, **k):
            self.sent.append((a, k))
            return MagicMock(id=1)

        async def iter_messages(self, chat_id, limit=2000):
            for m in self.messages:
                yield m

        async def delete_messages(self, chat_id, ids, revoke=True):
            self.deleted.append(ids)
            return None

    def _patches(self):
        return [
            patch.object(home, "ensure_home_group", AsyncMock(return_value=(5, ""))),
            patch.object(home, "ensure_home_topics", AsyncMock(return_value={"backup": 7, "summary": 8})),
        ]

    async def test_backup_failure_prevents_any_delete(self):
        client = self._Client([_msg(11), _msg(12)])
        with self._patches()[0], self._patches()[1], \
                patch.object(cleaner.vault, "forward_to_topic", AsyncMock(return_value=False)):
            report = await cleaner.run_delete(client, CHAT_ID, 100, 2)
        self.assertEqual(report["backup_failed"], [11, 12])
        self.assertEqual(report["deleted"], [])
        self.assertEqual(client.deleted, [])
        self.assertIn("بکاپ ناموفق", report["message"])

    async def test_only_backed_up_messages_are_deleted(self):
        client = self._Client([_msg(11), _msg(12)])
        with self._patches()[0], self._patches()[1], \
                patch.object(cleaner.vault, "forward_to_topic",
                             AsyncMock(side_effect=[True, False])):
            report = await cleaner.run_delete(client, CHAT_ID, 100, 2)
        self.assertEqual(report["deleted"], [11])
        self.assertEqual(report["backup_failed"], [12])
        self.assertEqual(client.deleted, [11])

    async def test_collect_ignores_others_ai_and_skipped_messages(self):
        client = self._Client([
            _msg(21, out=True),
            _msg(22, out=False),
            _msg(23, out=True),
            _msg(24, out=True),
            _msg(25, out=True),
        ])
        got = await cleaner.collect_owner_messages(client, CHAT_ID, 21, 5, skip_ids={25})
        self.assertEqual([m.id for m in got], [23, 24])

    async def test_delete_count_respects_max(self):
        client = self._Client([_msg(i) for i in range(30, 35)])
        got = await cleaner.collect_owner_messages(client, CHAT_ID, 999, 2)
        self.assertEqual([m.id for m in got], [30, 31])


class TestDeleteConfirmation(_Base):
    async def test_wide_delete_waits_for_confirmation(self):
        event, status = self._event(text="کاپری ۲۵ تا از پیامهام رو پاک کن")
        with patch.object(bot.home, "is_home_chat", return_value=False), \
                patch.object(bot.cleaner, "run_delete", AsyncMock()) as rd:
            await bot.on_outgoing(event)
        rd.assert_not_awaited()
        p = bot.pending.get(str(CHAT_ID))
        self.assertIsNotNone(p)
        self.assertEqual(p.get("kind"), "confirm_delete_messages")
        self.assertEqual(p.get("n"), 25)
        self.assertEqual(p.get("command_msg_id"), 101)

    async def test_small_delete_requires_confirmation_threshold(self):
        self.assertFalse(cleaner.needs_confirmation(20))
        self.assertTrue(cleaner.needs_confirmation(21))


class TestChannelSummary(unittest.IsolatedAsyncioTestCase):
    class _Client:
        def __init__(self, msgs, fail=False):
            self.msgs = msgs
            self.fail = fail
            self.sent = []

        async def get_input_entity(self, x):
            return "home-ent"

        async def get_messages(self, ent, limit=30):
            if self.fail:
                raise Exception("FloodWaitError: 42 seconds")
            return list(self.msgs)

        async def send_message(self, *a, **k):
            self.sent.append((a, k))
            return MagicMock(id=1)

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._stack = contextlib.ExitStack()
        self._stack.enter_context(patch.object(channel_summary, "SUMMARY_FILE",
                                               os.path.join(self._tmp.name, "summary.json")))
        self._stack.enter_context(patch.object(home, "HOME_FILE",
                                               os.path.join(self._tmp.name, "home.json")))
        self._stack.enter_context(patch.object(home, "ensure_home_group",
                                               AsyncMock(return_value=(5, ""))))
        self._stack.enter_context(patch.object(home, "ensure_home_topics",
                                               AsyncMock(return_value={"backup": 7, "summary": 8})))
        self._stack.enter_context(patch("ai_engine.ai.ask_direct", return_value="خلاصهٔ تست"))

    def tearDown(self):
        self._stack.close()
        self._tmp.cleanup()

    async def test_only_new_messages_are_summarized_once(self):
        channel_summary.add_channel("کانال تست", -1001234567890, "testch", seed_msg_id=100)
        self.assertEqual(channel_summary.get_cursor(-1001234567890), 100)

        client = self._Client([_msg(100), _msg(101), _msg(102)])
        body = await channel_summary.summarize_once(client)
        self.assertIsNotNone(body)
        self.assertIn("خلاصهٔ تست", body)
        self.assertEqual(len(client.sent), 1)
        self.assertEqual(channel_summary.get_cursor(-1001234567890), 102)

        # نقطهٔ پردازش باید پس از ری‌استارت هم از روی فایل خوانده شود
        self.assertEqual(channel_summary.load_data()["last_msg_id"]["-1001234567890"], 102)

        again = await channel_summary.summarize_once(client)
        self.assertIsNone(again)
        self.assertEqual(len(client.sent), 1)

    async def test_no_new_content_sends_nothing(self):
        channel_summary.add_channel("کانال تست", -1001234567890, "testch", seed_msg_id=200)
        client = self._Client([_msg(198), _msg(200)])
        self.assertIsNone(await channel_summary.summarize_once(client))
        self.assertEqual(client.sent, [])

    async def test_fetch_error_is_survived(self):
        channel_summary.add_channel("کانال تست", -1001234567890, "testch", seed_msg_id=0)
        client = self._Client([], fail=True)
        self.assertIsNone(await channel_summary.summarize_once(client))
        self.assertEqual(client.sent, [])


class TestHomeIdempotency(unittest.IsolatedAsyncioTestCase):
    async def test_existing_group_is_reused(self):
        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(home, "HOME_FILE", os.path.join(tmp, "home.json")):
            home.save_home_data({"group_id": 123, "peer_id": -1000000000123})
            client = MagicMock()
            client.get_entity = AsyncMock(return_value=MagicMock(title="Capri Home"))
            gid, _ = await home.ensure_home_group(client)
            self.assertEqual(gid, 123)
            client.assert_not_called()

    async def test_existing_topics_are_not_recreated(self):
        class _ForumClient:
            def __init__(self):
                self.calls = []

            async def get_input_entity(self, gid):
                return "ent"

            async def __call__(self, req):
                self.calls.append(req)
                return MagicMock(topics=[
                    _forum_topic(11, "🗂 بکاپ"),
                    _forum_topic(12, "📰 خلاصه کانال‌ها"),
                ])

        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(home, "HOME_FILE", os.path.join(tmp, "home.json")):
            client = _ForumClient()
            topics = await home.ensure_home_topics(client, 5)
        self.assertEqual(topics, {"backup": 11, "summary": 12})
        self.assertEqual(len(client.calls), 1)
        self.assertIsInstance(client.calls[0], functions.messages.GetForumTopicsRequest)


class TestVoiceAnswerHelper(unittest.IsolatedAsyncioTestCase):
    async def test_explicit_voice_request_is_detected(self):
        self.assertTrue(bot._wants_voice_reply("اینو با ویس جواب بده"))
        self.assertTrue(bot._wants_voice_reply("جوابم رو صوتی بگو"))
        self.assertFalse(bot._wants_voice_reply("سلام خوبی؟"))

    async def test_voice_answer_sent_when_tts_works(self):
        def fake_to_ogg(src, dst):
            with open(dst, "wb") as fh:
                fh.write(b"\0" * 2000)
            return True

        async def fake_speak(text, path, client=None):
            with open(path, "wb") as fh:
                fh.write(b"mp3")
            return True

        client = MagicMock()
        client.send_file = AsyncMock(return_value=MagicMock(id=777))
        status = MagicMock()
        status.delete = AsyncMock()

        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(bot.config, "DOWNLOAD_DIR", tmp), \
                patch.object(bot, "client", client), \
                patch.object(bot.voice, "speak", fake_speak), \
                patch.object(bot.voice, "to_ogg", fake_to_ogg), \
                patch.object(bot, "register_self_sent", MagicMock()):
            ok = await bot._send_voice_answer(MagicMock(chat_id=CHAT_ID), status, "سلام، این یک پاسخ صوتی است.")
            self.assertTrue(ok)
            self.assertEqual(os.listdir(tmp), [])

        client.send_file.assert_awaited_once()
        self.assertTrue(client.send_file.await_args.kwargs.get("voice_note"))
        status.delete.assert_awaited_once()

    async def test_voice_answer_falls_back_to_text_when_tts_fails(self):
        fake_mod = pytypes.ModuleType("edge_tts")

        def _boom(*a, **k):
            raise RuntimeError("no network")

        fake_mod.Communicate = _boom
        client = MagicMock()
        client.send_file = AsyncMock()

        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(bot.config, "DOWNLOAD_DIR", tmp), \
                patch.object(bot, "client", client), \
                patch.object(bot.voice, "speak", AsyncMock(return_value=False)), \
                patch.dict(sys.modules, {"edge_tts": fake_mod}):
            ok = await bot._send_voice_answer(MagicMock(chat_id=CHAT_ID), None, "متن پاسخ")
        self.assertFalse(ok)
        client.send_file.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
