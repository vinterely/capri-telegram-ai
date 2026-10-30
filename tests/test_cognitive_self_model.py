import json
import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core import cognitive_memory
from core import memory as core_memory
import bot


def _base_data():
    return {
        "user_profile": {"name": "Owner", "interests": [], "tone_preference": "صمیمی", "habits": []},
        "key_facts": [],
        "self_model": [],
        "social_context": {"important_topics": []},
        "reflection_history": [],
    }


class TestCognitiveSelfModel(unittest.IsolatedAsyncioTestCase):
    async def test_01_reflect_extracts_and_saves_self_notes(self):
        saved = {}
        payload = {
            "new_facts": ["کاربر برنامه‌نویس پایتون است"],
            "new_interests": [],
            "new_habits": [],
            "self_notes": ["مالک می‌خواهد کاپری شوخ‌تر باشد"],
        }
        with patch.object(cognitive_memory, "_load", return_value=_base_data()), \
             patch.object(cognitive_memory, "_save", side_effect=lambda d: saved.update(d)), \
             patch.object(cognitive_memory.ai, "ask", return_value=json.dumps(payload, ensure_ascii=False)), \
             patch.object(core_memory, "add_memory") as mock_add:
            await cognitive_memory.reflect_interaction(
                "من برنامه‌نویس پایتونم و دوست دارم کاپری شوخ‌تر باشه", "باشه!",
                scope_id="memory:dm:111",
            )
        self.assertIn("شوخ‌تر", saved["self_model"][0])
        self.assertIn("برنامه‌نویس پایتون", saved["key_facts"][0])
        mock_add.assert_called_once()
        self.assertEqual(mock_add.call_args.kwargs.get("scope_id"), "memory:dm:111")

    async def test_02_reflect_stores_distilled_not_verbatim(self):
        raw_msg = "من واقعا عاشق پیتزا پپرونی هستم و هر جمعه شب حتما میخورمش با نوشابه"
        distilled = "علاقهٔ کاربر به پیتزا پپرونی در شب‌های جمعه"
        saved = {}
        payload = {"new_facts": [distilled], "new_interests": [], "new_habits": [], "self_notes": []}
        with patch.object(cognitive_memory, "_load", return_value=_base_data()), \
             patch.object(cognitive_memory, "_save", side_effect=lambda d: saved.update(d)), \
             patch.object(cognitive_memory.ai, "ask", return_value=json.dumps(payload, ensure_ascii=False)), \
             patch.object(core_memory, "add_memory"):
            await cognitive_memory.reflect_interaction(raw_msg, "نوش جان!")
        self.assertEqual(saved["key_facts"], [distilled])
        self.assertNotIn("هر جمعه", " ".join(saved["key_facts"]))
        self.assertNotIn(raw_msg, " ".join(saved["key_facts"]))

    async def test_03_trivial_message_writes_nothing(self):
        saved = {}
        payload = {"new_facts": [], "new_interests": [], "new_habits": [], "self_notes": []}
        with patch.object(cognitive_memory, "_load", return_value=_base_data()), \
             patch.object(cognitive_memory, "_save", side_effect=lambda d: saved.update(d)) as mock_save, \
             patch.object(cognitive_memory.ai, "ask", return_value=json.dumps(payload, ensure_ascii=False)):
            await cognitive_memory.reflect_interaction("فقط یه سلام ساده", "سلام!")
        mock_save.assert_not_called()

    def test_04_context_summary_includes_self_model(self):
        data = _base_data()
        data["self_model"] = ["کاپری باید پاسخ‌هایش را کوتاه کند"]
        with patch.object(cognitive_memory, "_load", return_value=data):
            summary = cognitive_memory.get_context_summary()
        self.assertIn("کاپری باید پاسخ‌هایش را کوتاه کند", summary)
        self.assertIn("شناخت کاپری از خودش", summary)

    async def test_05_trigger_learn_runs_without_keyword_marker(self):
        with patch.object(bot, "_learn") as mock_learn, \
             patch.object(bot.cognitive_memory, "reflect_interaction", new=AsyncMock()) as mock_reflect, \
             patch.object(bot, "_last_learn_time", 0.0):
            await bot._trigger_learn(
                "امروز هوا خیلی خوبه و رفتم پارک قدم زدم", "خوش گذشت!", scope_id="memory:dm:222",
            )
        mock_learn.assert_called_once()
        mock_reflect.assert_awaited_once()

    async def test_06_trigger_learn_skips_tiny_messages(self):
        with patch.object(bot, "_learn") as mock_learn, \
             patch.object(bot.cognitive_memory, "reflect_interaction", new=AsyncMock()) as mock_reflect, \
             patch.object(bot, "_last_learn_time", 0.0):
            await bot._trigger_learn("hi", "سلام", scope_id="memory:dm:333")
        mock_learn.assert_not_called()
        mock_reflect.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
