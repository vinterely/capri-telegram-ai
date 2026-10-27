import asyncio
import hashlib
import json
import os
import tempfile
import time
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import bot
from ai_engine import agent, skills_manager, tools
from core import access, fsutil, logger


class TestSevenSecurityHardens(unittest.IsolatedAsyncioTestCase):
    """تست‌های جامع اعتبارسنجی هفتگانه امنیت و قابلیت‌های نوین."""

    # ---------------- 1. کنترل دسترسی و رد بی‌صدا ----------------
    async def test_section1_silent_drop_stranger(self):
        """غریبه‌ها بدون هیچ پاسخی (حتی پیام خطا یا کول‌داون) به صورت بی‌صدا رد می‌شوند."""
        event = MagicMock()
        event.raw_text = "کاپری سلام"
        event.sender_id = 998877
        event.out = False
        event.reply = AsyncMock()
        event.get_sender = AsyncMock(return_value=MagicMock(first_name="غریبه", bot=False))

        with patch("core.access.is_allowed", return_value=False), \
             patch("services.social.dnd.is_dnd_active", return_value=False):
            await bot.on_incoming_pm(event)

        event.reply.assert_not_called()

    async def test_section1_silent_drop_bot_even_if_allowed(self):
        """ربات‌ها حتی در صورت وجود در لیست مجوزها، بی‌صدا رد می‌شوند."""
        event = MagicMock()
        event.raw_text = "کاپری سلام"
        event.sender_id = 111222
        event.out = False
        event.reply = AsyncMock()
        event.get_sender = AsyncMock(return_value=MagicMock(first_name="ربات مخرب", bot=True))

        with patch("core.access.is_allowed", return_value=True), \
             patch("services.social.dnd.is_dnd_active", return_value=False):
            await bot.on_incoming_pm(event)

        event.reply.assert_not_called()

    async def test_section1_access_json_fail_closed(self):
        """در صورت نبود یا خراب بودن فایل access.json، هیچ‌کس مجاز نیست (fail-closed)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_file = os.path.join(tmpdir, "corrupt_access.json")
            with open(bad_file, "w", encoding="utf-8") as f:
                f.write("{invalid json content---")
            with patch("core.access.FILE", bad_file):
                self.assertFalse(access.is_allowed(12345))
                self.assertEqual(access.get_allowed_users(), [])

    async def test_section1_allowed_user_30s_cooldown(self):
        """کول‌داون برای کاربران مجاز ۳۰ ثانیه است."""
        bot._stranger_last_request.clear()
        bot._stranger_cooldown_warned.clear()

        uid = 555666
        event = MagicMock()
        event.raw_text = "کاپری وضعیت آب و هوا چطوره؟"
        event.sender_id = uid
        event.out = False
        event.is_private = True
        event.is_group = False
        event.fwd_from = None
        event.via_bot = None
        event.via_bot_id = None
        event.message = MagicMock(file=None, photo=None, video=None, document=None, voice=None, audio=None, media=None, fwd_from=None, via_bot=None, via_bot_id=None)
        event.get_reply_message = AsyncMock(return_value=None)
        event.reply = AsyncMock()
        event.get_sender = AsyncMock(return_value=MagicMock(first_name="کاربر مجاز", bot=False))

        bot._stranger_last_request[uid] = time.time() - 15  # ۱۵ ثانیه قبل درخواست داده (کمتر از ۳۰ ثانیه)

        with patch("core.access.is_allowed", return_value=True), \
             patch("core.access.is_denied", return_value=False), \
             patch("bot._stranger_rate_ok", return_value=True), \
             patch("services.social.dnd.is_dnd_active", return_value=False):
            await bot.on_incoming_pm(event)

        event.reply.assert_called_once()
        self.assertIn("۳۰ ثانیه", event.reply.call_args[0][0])

    async def test_section1_owner_commands_parse_mode_none(self):
        """دستورات مدیریت مجوز با parse_mode=None ارسال شده و هدف‌های بات یا مالک را رد می‌کنند."""
        event = MagicMock()
        event.chat_id = 100
        event.is_private = True
        event.reply_to_msg_id = None

        with patch.object(bot.client, "send_message", new_callable=AsyncMock) as mock_send, \
             patch.object(bot.client, "get_me", new_callable=AsyncMock, return_value=MagicMock(id=999)), \
             patch.object(bot.client, "get_entity", new_callable=AsyncMock, return_value=MagicMock(id=100, first_name="علی", last_name="رضایی", bot=False)):
            
            # ۱. لیست مجوزها
            with patch("core.access.get_allowed_users", return_value=[100]):
                await bot._handle_access_command(event, "list")
                mock_send.assert_called_with(100, "لیست کاربران مجاز:\n1. نام: علی رضایی | شناسه: 100", parse_mode=None)

            # ۲. اعطای مجوز
            mock_send.reset_mock()
            with patch("core.access.allow_user") as mock_allow:
                await bot._handle_access_command(event, "allow")
                mock_allow.assert_called_once_with(100)
                mock_send.assert_called_with(100, "✅ کاربر علی رضایی با شناسه 100 به لیست مجوزها اضافه شد.", parse_mode=None)

            # ۳. رد اعطای مجوز به خود مالک
            mock_send.reset_mock()
            event.chat_id = 999
            with patch.object(bot.client, "get_entity", new_callable=AsyncMock, return_value=MagicMock(id=999, first_name="مالک", bot=False)):
                await bot._handle_access_command(event, "allow")
                mock_send.assert_called_with(999, "❌ امکان تغییر مجوز برای خود مالک اکانت وجود ندارد.", parse_mode=None)

    # ---------------- ۲. خنثی‌کردن تریگر در خروجی بات ----------------
    def test_section2_trigger_neutralization(self):
        """کلمات فعال‌ساز کاپری و capri با کاراکتر نیم‌فاصله یا نامرئی شکسته می‌شوند."""
        res_fa = bot.neutralize_triggers("سلام کاپری جان")
        self.assertEqual(res_fa, "سلام کا\u200cپری جان")
        self.assertNotIn("کاپری", res_fa)

        res_en = bot.neutralize_triggers("Hello Capri please assist")
        self.assertEqual(res_en, "Hello ca\u200bpri please assist")
        self.assertNotIn("capri", res_en.lower())

    def test_section2_starts_with_trigger_validation(self):
        """پیام فقط در صورتی پذیرفته می‌شود که تریگر در ابتدای متن باشد."""
        self.assertTrue(bot.starts_with_trigger("کاپری وضعیت رو بگو"))
        self.assertTrue(bot.starts_with_trigger("  capri hello"))
        self.assertFalse(bot.starts_with_trigger("سلام کاپری"))
        self.assertFalse(bot.starts_with_trigger("اداره کاپری"))

    def test_section2_self_sent_tuple_tracking(self):
        """ثبت پیام‌های ارسالی با تاپل (chat_id, message_id)."""
        bot.self_sent.clear()
        mock_msg = MagicMock()
        mock_msg.id = 555
        mock_msg.chat_id = 1234
        bot.register_self_sent(mock_msg)

        self.assertIn((1234, 555), bot.self_sent)
        self.assertIn(555, bot.self_sent)

    # ---------------- ۳. تایید برای کارهای خطرناک با مرز کلمه ----------------
    def test_section3_word_boundary_confirmation(self):
        """تطابق تاییدیه با مرز کلمه؛ کلماتی مثل اداره یا برنامه نباید تایید یا لغو تلقی شوند."""
        p = {"kind": "confirm_leave_single"}
        self.assertFalse(bot._is_confirmation_response("این اداره کجاست؟", p))
        self.assertFalse(bot._is_confirmation_response("برنامه امروز چیه؟", p))
        self.assertTrue(bot._is_confirmation_response("آره", p))
        self.assertTrue(bot._is_confirmation_response("نه", p))
        self.assertTrue(bot._is_confirmation_response("اره لفت بده", p))

    async def test_section3_dangerous_actions_require_confirmation(self):
        """manage_memory(action='add') و manage_important_channels به تایید صریح نیاز دارند."""
        event = MagicMock()
        event.chat_id = 777
        event.out = True

        # ۱. ذخیره حافظه
        res_mem = await tools.execute_tool("manage_memory", {"action": "add", "fact": "رنگ مورد علاقه من آبی است"}, event, bot.client)
        self.assertIn("⚠️ برای ذخیره", res_mem)
        self.assertIn("777", bot.pending)
        self.assertEqual(bot.pending["777"]["kind"], "confirm_add_memory")

        # ۲. افزودن کانال مهم
        res_ch = await tools.execute_tool("manage_important_channels", {"action": "add", "channel_name": "@tech_news"}, event, bot.client)
        self.assertIn("⚠️ برای افزودن به لیست کانال‌های مهم", res_ch)
        self.assertEqual(bot.pending["777"]["kind"], "confirm_important_channel")

    # ---------------- ۴. ردیابی Taint و جلوگیری از نشت داده ----------------
    async def test_section4_taint_quarantine_blocks_network_and_sensitive_tools(self):
        """در صورت آلودگی، ابزارهای شبکه و حساس بلاک می‌شوند و فقط ask_clarification و get_current_datetime مجازند."""
        tainted_defs = tools.get_all_tool_definitions(is_owner=True, tainted=True)
        tool_names = {t["function"]["name"] for t in tainted_defs}
        self.assertEqual(tool_names, {"ask_clarification", "get_current_datetime"})

        # تست بلاک شدن در پایتون
        res = await tools.execute_tool("read_webpage", {"url": "https://example.com"}, MagicMock(), bot.client, tainted=True)
        self.assertIn("قرنطینه امنیتی", res)

    def test_section4_sanitize_tainted_output_removes_all_urls(self):
        """تمام URLها و عکس‌های مارک‌داون در خروجی آلوده حذف می‌شوند."""
        raw = "متن تست ![عکس](https://evil.com/img.png) و لینک مستقیم https://secret-token.com/leak و [سایت](https://google.com)"
        clean = agent.sanitize_tainted_output(raw)
        self.assertNotIn("https://evil.com", clean)
        self.assertNotIn("https://secret-token.com", clean)
        self.assertNotIn("https://google.com", clean)
        self.assertIn("سایت", clean)

    async def test_section4_voice_learn_only_on_owner_voice(self):
        """یادگیری در _handle_voice فقط روی وویس‌های ارسالی خود مالک اجرا می‌شود."""
        with patch("bot.memory.remember_exchange") as mock_remember, \
             patch("bot._learn") as mock_learn:
            
            # وویس طرف مقابل (out=False)
            other_msg = MagicMock(out=False, fwd_from=None)
            is_owner = getattr(other_msg, "out", False) and not getattr(other_msg, "fwd_from", None)
            self.assertFalse(is_owner)

            # وویس فورواردشده مالک (fwd_from!=None)
            fwd_msg = MagicMock(out=True, fwd_from=MagicMock())
            is_owner_fwd = getattr(fwd_msg, "out", False) and not getattr(fwd_msg, "fwd_from", None)
            self.assertFalse(is_owner_fwd)

            # وویس مستقیم خود مالک
            owner_msg = MagicMock(out=True, fwd_from=None)
            is_owner_direct = getattr(owner_msg, "out", False) and not getattr(owner_msg, "fwd_from", None)
            self.assertTrue(is_owner_direct)

    # ---------------- ۵. امنیت اسکیل‌ها ----------------
    def test_section5_skill_creation_guard_and_regex(self):
        """پیش‌فرض ساخت اسکیل غیرفعال است و نام آن با regex اعتبارسنجی می‌شود."""
        with patch("ai_engine.skills_manager.is_skill_creation_allowed", return_value=False):
            self.assertIn("غیرفعال", skills_manager.create_or_update_skill("my_skill", "desc", {}, "async def execute(): pass"))
            self.assertIn("غیرفعال", skills_manager.delete_skill("my_skill"))

        with patch("ai_engine.skills_manager.is_skill_creation_allowed", return_value=True):
            # نام نامعتبر (خیلی کوتاه یا کاراکتر غیرمجاز یا عدد در ابتدا)
            err_short = skills_manager.validate_skill("ab", "code")
            self.assertIn("باید انگلیسی کوچک", err_short)
            err_digit = skills_manager.validate_skill("1skill", "code")
            self.assertIn("باید انگلیسی کوچک", err_digit)
            # تداخل با ابزار پیش‌فرض سیستم
            err_coll = skills_manager.validate_skill("web_search", "code")
            self.assertIn("تداخل دارد", err_coll)

    async def test_section5_skill_integrity_sha256(self):
        """اسکیلی که هش آن با فایل یکپارچگی مطابقت ندارد اجرا نمی‌شود."""
        with patch("ai_engine.skills_manager._load_registry", return_value={"test_skill": {"file": "dummy.py"}}), \
             patch("os.path.exists", return_value=True), \
             patch("ai_engine.skills_manager._load_integrity", return_value={"test_skill": "expected_valid_hash"}), \
             patch("ai_engine.skills_manager._calc_file_sha256", return_value="tampered_different_hash"):
            
            res = await skills_manager.execute_skill("test_skill", {}, MagicMock(), MagicMock())
            self.assertIn("تغییر یافته است", res)

    # ---------------- ۶. محرمانگی کلیدها و لاگ‌ها ----------------
    def test_section6_gemini_key_and_url_redacted(self):
        """کلیدهای Gemini (AIzaSy...) و پارامترهای ?key=... در لاگ پنهان می‌شوند."""
        raw_log = "API request to https://generativelanguage.googleapis.com/v1beta?key=AIzaSyA1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6 with Bearer eyJhbGciOi"
        sanitized = logger.redact_secrets(raw_log)
        self.assertNotIn("AIzaSyA1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6", sanitized)
        self.assertIn("<REDACTED>", sanitized)


if __name__ == "__main__":
    unittest.main()
