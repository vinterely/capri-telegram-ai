import os
import sys
import tempfile
import time
import unittest
from unittest.mock import MagicMock, patch

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from ai_engine import agent
import bot
from core import config
from core import fsutil
from ai_engine import providers


class TestHalfOpenCircuitBreaker(unittest.TestCase):
    """مدار شکن باید پس از cooldown فقط یک تلاش نیمه‌باز بدهد و در صورت شکست فوراً دوباره باز شود."""

    def test_half_open_reopens_immediately_on_trial_failure(self):
        cb = agent.CircuitBreaker(failure_threshold=2, window_seconds=5, cooldown_seconds=10)
        key = "srv:mod"
        cb.record_failure(key)
        cb.record_failure(key)
        self.assertFalse(cb.is_available(key))  # مدار باز شد

        with patch("ai_engine.agent.time.time", return_value=time.time() + 11):
            self.assertTrue(cb.is_available(key))  # تلاش آزمایشی نیمه‌باز مجاز است
            cb.record_failure(key)  # شکست در حالت نیمه‌باز

        self.assertFalse(cb.is_available(key))  # بلافاصله دوباره باز شد

    def test_half_open_recovers_on_success(self):
        cb = agent.CircuitBreaker(failure_threshold=2, window_seconds=5, cooldown_seconds=10)
        key = "srv:mod"
        cb.record_failure(key)
        cb.record_failure(key)
        self.assertFalse(cb.is_available(key))

        with patch("ai_engine.agent.time.time", return_value=time.time() + 11):
            self.assertTrue(cb.is_available(key))
            cb.record_success(key)

        self.assertTrue(cb.is_available(key))  # موفقیت مدار را بست


class TestTriggerMatching(unittest.TestCase):
    """تطبیق نام دستیار باید با مرز توکن، غیرحساس به بزرگی/کوچکی و نرمال‌سازی ی/ک باشد."""

    def test_token_boundary(self):
        p = bot._name_pattern("capri")
        self.assertTrue(p.search("capri سلام"))
        self.assertTrue(p.search("سلام CAPRI"))
        self.assertIsNone(p.search("capricious"))
        self.assertIsNone(p.search("xcapriy"))

    def test_persian_arabic_variants(self):
        p = bot._name_pattern("کاپری")
        self.assertTrue(p.search("کاپری"))
        self.assertTrue(p.search("کاپري"))  # ي عربی → ی
        self.assertTrue(p.search("كاپری"))  # ك عربی → ک

    def test_has_trigger_and_strip(self):
        name = config.ASSISTANT_NAMES[0]
        self.assertTrue(bot.has_trigger(f"{name} سلام"))
        stripped = bot.strip_trigger(f"{name} سلام چطوری")
        self.assertNotIn(name, stripped)
        self.assertIn("سلام", stripped)


class TestAtomicWriteJson(unittest.TestCase):
    """نوشتن اتمیک JSON باید فایل معتبر بنویسد و روی مقدار قبلی جایگزین کند."""

    def test_write_and_overwrite(self):
        import json
        d = tempfile.mkdtemp()
        p = os.path.join(d, "state.json")
        fsutil.atomic_write_json(p, {"a": 1})
        with open(p, encoding="utf-8") as f:
            self.assertEqual(json.load(f), {"a": 1})
        fsutil.atomic_write_json(p, {"b": 2})
        with open(p, encoding="utf-8") as f:
            self.assertEqual(json.load(f), {"b": 2})


class TestProviderRetryPolicy(unittest.TestCase):
    """_post فقط باید روی 429/5xx و خطاهای شبکه retry کند، نه 400/401/403."""

    def _resp(self, status):
        r = MagicMock()
        r.status_code = status
        r.headers = {}
        return r

    def test_retries_on_429_then_succeeds(self):
        resp429 = self._resp(429)
        resp200 = self._resp(200)
        resp200.json.return_value = {"choices": []}

        session = MagicMock()
        session.post.side_effect = [resp429, resp200]
        with patch.object(providers, "_session", return_value=session), \
             patch("ai_engine.providers.time.sleep", return_value=None):
            result = providers._post("https://api.groq.com/openai/v1/chat/completions", {}, {})
        self.assertEqual(result, {"choices": []})
        self.assertEqual(session.post.call_count, 2)

    def test_does_not_retry_400(self):
        import requests
        session = MagicMock()
        session.post.return_value = self._resp(400)
        with patch.object(providers, "_session", return_value=session), \
             patch("ai_engine.providers.time.sleep", return_value=None):
            with self.assertRaises(requests.exceptions.HTTPError):
                providers._post("https://api.groq.com/openai/v1/chat/completions", {}, {})
        self.assertEqual(session.post.call_count, 1)


if __name__ == "__main__":
    unittest.main()
