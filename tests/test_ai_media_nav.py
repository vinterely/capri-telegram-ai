"""تست‌های جامع ناوبری و کنترل خودمختار ۰ تا ۱۰۰ ربات‌های مدیا و دانلود با هوش مصنوعی."""

import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from telethon import types

from services.media import ai_nav, media_flow, fetch


class TestAIMediaNav(unittest.TestCase):
    def test_extract_message_elements_buttons_and_commands(self):
        """تست استخراج کامل دکمه‌ها، دستورات اسلش، لینک‌ها و فیلتر دکمه‌های برگشت."""
        fake_b1 = MagicMock(text="کیفیت 480p", data=b"q_480", url=None)
        fake_b2 = MagicMock(text="کیفیت 720p", data=b"q_720", url=None)
        fake_b_back = MagicMock(text="🔙 بازگشت به منو", data=b"back", url=None)

        fake_msg = MagicMock()
        fake_msg.message = (
            "برای دانلود فیلم یکی از گزینه‌های زیر را انتخاب کنید:\n"
            "کیفیت 480p زیرنویس: /dl_480_sub\n"
            "کیفیت 720p دوبله: /dl_720_dub\n"
            "لینک مستقیم: https://t.me/dl_robot?start=token123"
        )
        fake_msg.buttons = [[fake_b1, fake_b2], [fake_b_back]]
        fake_msg.entities = []

        elements = ai_nav.extract_message_elements(fake_msg)

        self.assertEqual(len(elements["buttons"]), 3)
        # دکمه بازگشت باید به درستی شناسایی و علامت‌گذاری شده باشد
        self.assertTrue(elements["buttons"][2]["is_back"])
        # فهرست display_buttons نباید شامل دکمه بازگشت باشد
        self.assertEqual(len(elements["display_buttons"]), 2)
        self.assertEqual(elements["display_buttons"][0]["text"], "کیفیت 480p")
        self.assertEqual(elements["display_buttons"][1]["text"], "کیفیت 720p")

        # بررسی استخراج دستورات اسلش
        self.assertIn("/dl_480_sub", elements["commands"])
        self.assertIn("/dl_720_dub", elements["commands"])

        # بررسی استخراج لینک‌ها
        self.assertTrue(any("https://t.me/dl_robot?start=token123" in l["url"] for l in elements["links"]))
        self.assertFalse(elements["is_subscription"])

    def test_match_best_command_with_quality_and_audio(self):
        """تست تطابق دقیق دستور اسلش بر اساس کیفیت و صوت درخواستی کاربر."""
        text = (
            "1. Oppenheimer 480p SoftSub: /dl_912\n"
            "2. Oppenheimer 720p SoftSub: /dl_913\n"
            "3. Oppenheimer 1080p Dubbed: /dl_914\n"
        )
        commands = ["/dl_912", "/dl_913", "/dl_914"]

        # درخواست ۱: کیفیت 480 با زیرنویس
        req1 = {"quality": 480, "audio": "subtitled"}
        cmd1 = ai_nav.match_best_command(text, commands, req1)
        self.assertEqual(cmd1, "/dl_912")

        # درخواست ۲: کیفیت 720 با زیرنویس
        req2 = {"quality": 720, "audio": "subtitled"}
        cmd2 = ai_nav.match_best_command(text, commands, req2)
        self.assertEqual(cmd2, "/dl_913")

        # درخواست ۳: کیفیت 1080 با دوبله
        req3 = {"quality": 1080, "audio": "dubbed"}
        cmd3 = ai_nav.match_best_command(text, commands, req3)
        self.assertEqual(cmd3, "/dl_914")

    def test_parse_ai_decision_send_text_and_click_button(self):
        """تست پارس خروجی ساختاریافته مدل به اقدامات عملیاتی."""
        elements = {
            "buttons": [
                {"text": "زیرنویس 480p", "data": b"sub480", "is_back": False},
                {"text": "دوبله 720p", "data": b"dub720", "is_back": False}
            ],
            "display_buttons": [
                {"text": "زیرنویس 480p", "data": b"sub480", "is_back": False},
                {"text": "دوبله 720p", "data": b"dub720", "is_back": False}
            ],
            "commands": ["/dl_480", "/dl_720"],
            "links": [{"url": "https://t.me/dlbot?start=tok"}],
            "text": "منوی دانلود فیلم"
        }

        # حالت ۱: دستور متنی send_text
        ai_raw_send = '{"action": "send_text", "text": "/dl_480", "reason": "کیفیت ۴۸۰ درخواستی"}'
        dec1 = ai_nav.parse_ai_decision(ai_raw_send, elements)
        self.assertEqual(dec1["action"], "send_text")
        self.assertEqual(dec1["text"], "/dl_480")

        # حالت ۲: کلیک دکمه click_button
        ai_raw_btn = '{"action": "click_button", "button_index": 1, "reason": "انتخاب زیرنویس ۴۸۰"}'
        dec2 = ai_nav.parse_ai_decision(ai_raw_btn, elements)
        self.assertEqual(dec2["action"], "click_button")
        self.assertEqual(dec2["button"]["text"], "زیرنویس 480p")

        # حالت ۳: پایان فرایند done
        ai_raw_done = '{"action": "done", "reason": "فایل دریافت شد"}'
        dec3 = ai_nav.parse_ai_decision(ai_raw_done, elements)
        self.assertEqual(dec3["action"], "done")

    def test_analyze_menu_buttons_none_safe(self):
        """تست عدم کرش تحلیل‌گر دکمه‌ها در صورت ارسال پیام‌های بدون دکمه (متن خالی یا صرفاً متن)."""
        res = media_flow.analyze_menu_buttons(None)
        self.assertEqual(res["seasons"], {})
        self.assertEqual(res["qualities"], {})
        self.assertEqual(res["audio"], {})
        self.assertEqual(res["all_valid"], [])


class TestAsyncMediaFlowExecution(unittest.IsolatedAsyncioTestCase):
    async def test_execute_bot_navigation_text_command_flow(self):
        """تست ناوبری موفق رباتی که دکمه شیشه‌ای ندارد و با اسلش‌کامند کار می‌کند."""
        mock_client = AsyncMock()
        mock_bot = MagicMock()
        mock_client.get_entity.return_value = mock_bot

        start_msg = MagicMock()
        start_msg.id = 100
        start_msg.out = False
        start_msg.buttons = None
        start_msg.message = "فیلم مورد نظر پیدا شد:\nبرای دانلود کیفیت 480: /dl_part_480"
        start_msg.media = None

        doc_msg = MagicMock()
        doc_msg.id = 105
        doc_msg.out = False
        doc_msg.media = types.MessageMediaDocument(document=MagicMock())
        doc_msg.buttons = None
        doc_msg.message = "فایل فیلم خدمت شما"

        mock_client.get_messages.return_value = [start_msg]

        req = {"title": "Inception", "quality": 480, "audio": "subtitled"}
        event = MagicMock(chat_id=123456)
        status = AsyncMock()

        # collect_documents در دور اول خالی و بعد از اجرای دستور فایل را برمی‌گرداند
        with patch("services.media.media_flow.collect_documents", side_effect=[[], [], [doc_msg], [doc_msg]]):
            with patch("services.media.ai_nav.decide_action_sync", return_value={"action": "send_text", "text": "/dl_part_480", "reason": "دستور دانلود ۴۸۰"}):
                files, err = await media_flow.execute_bot_navigation(
                    mock_client, "dl_movie_bot", start_msg, req, event=event, status=status
                )

                mock_client.send_message.assert_called_with(mock_bot, "/dl_part_480")
                mock_client.forward_messages.assert_called_with(123456, doc_msg)
                self.assertEqual(len(files), 1)
                self.assertIsNone(err)

    async def test_execute_bot_navigation_strictly_avoids_opposite_audio(self):
        """تست اینکه در صورت درخواست زیرنویس، سیستم به درستی دکمه زیرنویس را کلیک می‌کند."""
        mock_client = AsyncMock()
        mock_bot = MagicMock()
        mock_client.get_entity.return_value = mock_bot

        b_dub = MagicMock(text="دوبله فارسی", data=b"dub")
        b_sub = MagicMock(text="زیرنویس چسبیده", data=b"sub")

        menu_msg = MagicMock()
        menu_msg.id = 200
        menu_msg.out = False
        menu_msg.buttons = [[b_dub, b_sub]]
        menu_msg.message = "انتخاب صوت"
        menu_msg.media = None
        menu_msg.click = AsyncMock()

        doc_msg = MagicMock()
        doc_msg.id = 205
        doc_msg.out = False
        doc_msg.media = types.MessageMediaDocument(document=MagicMock())

        mock_client.get_messages.return_value = [menu_msg]

        req = {"title": "Inception", "quality": 480, "audio": "subtitled"}
        event = MagicMock(chat_id=123456)
        status = AsyncMock()

        with patch("services.media.media_flow.collect_documents", side_effect=[[], [], [doc_msg], [doc_msg]]):
            with patch("services.media.ai_nav.decide_action_sync", return_value={"action": "click_button", "button": {"text": "زیرنویس چسبیده", "data": b"sub"}, "button_index": 2, "reason": "انتخاب زیرنویس"}):
                files, err = await media_flow.execute_bot_navigation(
                    mock_client, "dl_movie_bot", menu_msg, req, event=event, status=status
                )
                menu_msg.click.assert_called_with(data=b"sub")
                self.assertEqual(len(files), 1)


if __name__ == "__main__":
    unittest.main()
