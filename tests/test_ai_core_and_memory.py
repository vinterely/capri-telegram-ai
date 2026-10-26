import asyncio
import json
import os
import time
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from ai_engine import agent
from ai_engine.agent import AgentExecutionCycle, CircuitBreaker
from core import memory
from core.memory import ConversationBuffer, MemoryRecord


class TestMemoryUpgrade(unittest.TestCase):
    def setUp(self):
        # ایزوله‌سازی حافظه برای هر تست با فایل موقت یا پاکسازی حافظه
        memory.clear_memory()
        memory.clear_history()

    def tearDown(self):
        memory.clear_memory()
        memory.clear_history()

    def test_memory_record_creation_and_inference(self):
        # تست تبدیل خودکار و تشخیص دسته‌بندی
        rec = MemoryRecord.from_dict("کاربر به یادگیری پایتون علاقه‌مند است")
        self.assertEqual(rec.category, "preference")
        self.assertEqual(rec.status, "active")
        self.assertTrue(rec.id.startswith("mem_"))

        rec2 = MemoryRecord.from_dict("مقرر شد از این به بعد خروجی به فرمت JSON باشد")
        self.assertEqual(rec2.category, "decision")

        rec3 = MemoryRecord.from_dict("پروژه کاپری ریپازیتوری بات شخصی است")
        self.assertEqual(rec3.category, "project")

    def test_persian_normalization_and_stemming(self):
        # نرمال‌سازی ی/ک و اعراب
        norm = memory._norm_persian("كتاب‌هاي آموزشيِ پايتون")
        self.assertNotIn("ك", norm)
        self.assertNotIn("ي", norm)
        self.assertNotIn("ِ", norm)

        # استمینگ پسوندهای صرفی فارسی
        toks = memory._tokens("کتاب‌های آموزشی برنامه‌نویسی پایتون")
        self.assertTrue(any("کتاب" in t for t in toks))

    def test_deduplication(self):
        # تست پیشگیری از ثبت تکراری دقیق و با شباهت ژاکارد بالا
        id1 = memory.add_memory("کاربر به زبان پایتون ۳.۱۲ علاقه دارد", importance=3)
        self.assertTrue(id1)
        self.assertEqual(len(memory.list_facts()), 1)

        # تلاش برای ثبت مجدد همان مفهوم
        id2 = memory.add_memory("کاربر به زبان پایتون ۳.۱۲ علاقه دارد", importance=5)
        self.assertEqual(id1, id2)
        self.assertEqual(len(memory.list_facts()), 1)

        # بررسی به‌روزرسانی اهمیت
        records = memory._get_records()
        self.assertEqual(records[0].importance, 5)

    def test_conflict_resolution(self):
        # تست رفع تناقض: ثبت تصمیم جدید باید تصمیم متناقض قبلی را supersede کند
        id_old = memory.add_memory("تصمیم بر این شد که مدل پیش‌فرض gpt-4 باشد", category="decision")
        records = memory._get_records()
        self.assertEqual(records[0].status, "active")

        # تغییر تصمیم توسط کاربر
        id_new = memory.add_memory("تصمیم جدید: مدل پیش‌فرض باید gemini-2.5-flash باشد", category="decision")
        self.assertNotEqual(id_old, id_new)

        records_after = memory._get_records()
        # رکورد قدیمی باید به supersede تغییر وضعیت داده باشد
        old_rec = next(r for r in records_after if r.id == id_old)
        new_rec = next(r for r in records_after if r.id == id_new)
        self.assertEqual(old_rec.status, "superseded")
        self.assertEqual(new_rec.status, "active")

        # در لیست فکت‌های فعال فقط رکورد جدید باید ظاهر شود
        active_facts = memory.list_facts()
        self.assertEqual(len(active_facts), 1)
        self.assertIn("gemini-2.5-flash", active_facts[0])

    def test_smart_retrieval_and_scoring(self):
        # ثبت چند حافظه در دسته‌بندی‌های گوناگون
        memory.add_memory("کاربر پروژه توسعه تلگرام بات کاپری را مدیریت می‌کند", category="project", importance=4)
        memory.add_memory("رنگ مورد علاقه کاربر آبی کاربنی است", category="preference", importance=2)
        memory.add_memory("سرور اصلی روی سیستم لینوکس اوبونتو ۲۴ مستقر است", category="fact", importance=3)

        # جستجو بر اساس کلمات کلیدی پروژه
        results = memory.retrieve_relevant_memories("پروژه تلگرام کاپری چیه؟", limit=2)
        self.assertGreaterEqual(len(results), 1)
        self.assertIn("کاپری", results[0]["content"])

        # جستجو با ارجاع به گذشته (همون پروژه قبلی)
        results_past = memory.retrieve_relevant_memories("همون کار قبلی درباره سرور", limit=2)
        self.assertGreaterEqual(len(results_past), 1)
        self.assertTrue(any("سرور" in r["content"] for r in results_past))

    def test_short_term_sliding_window_and_summarization(self):
        chat_id = "test_chat_99"
        # ثبت بیش از ۲۰ نوبت مکالمه برای تحریک فشرده‌سازی خودکار پنجره
        for i in range(25):
            memory.remember_exchange(chat_id, f"پیام کاربر درباره موضوع {i}", f"پاسخ ربات کاپری شماره {i}")

        context = memory.load_history(chat_id)
        # باید حاوی خلاصه گفتگوهای پیشین و آخرین پیام‌ها باشد
        self.assertIn("خلاصه گفتگوهای پیشین", context)
        self.assertIn("پیام کاربر درباره موضوع 24", context)


class TestAgentExecutionCycle(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        agent.breaker.reset()
        self.event = MagicMock()
        self.event.chat_id = 123456
        self.event.out = True
        self.client = MagicMock()

    async def test_agent_direct_response_without_tools(self):
        # تست پاسخ مستقیم بدون ابزار
        with patch("ai_engine.agent._call_model_step") as mock_step:
            mock_step.return_value = {
                "role": "assistant",
                "content": "سلام رفیق! چطور می‌تونم کمکت کنم؟",
                "tool_calls": []
            }
            res = await agent.run_agent("سلام کاپری", "", "", self.event, self.client)
            self.assertEqual(res, "سلام رفیق! چطور می‌تونم کمکت کنم؟")
            mock_step.assert_called_once()

    async def test_agent_multistep_tool_execution(self):
        # تست چرخه چندمرحله‌ای: ابتدا ابزار صدا زده می‌شود و سپس پاسخ نهایی بر اساس نتیجه تولید می‌شود
        with patch("ai_engine.agent._call_model_step") as mock_step, \
             patch("ai_engine.tools.execute_tool", new_callable=AsyncMock) as mock_exec:

            mock_exec.return_value = "ساعت ۱۰:۳۰ است"

            # مرحله اول: فراخوانی ابزار get_current_time
            # مرحله دوم: تولید پاسخ نهایی
            mock_step.side_effect = [
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "get_current_time",
                            "arguments": "{}"
                        }
                    }]
                },
                {
                    "role": "assistant",
                    "content": "الان ساعت دقیقا ۱۰:۳۰ است.",
                    "tool_calls": []
                }
            ]

            res = await agent.run_agent("ساعت چنده؟", "", "", self.event, self.client)
            self.assertEqual(res, "الان ساعت دقیقا ۱۰:۳۰ است.")
            self.assertEqual(mock_step.call_count, 2)
            mock_exec.assert_called_once()

    async def test_agent_tool_schema_error_feedback(self):
        # تست ارسال بازخورد خطا به مدل در صورت نامعتبر بودن JSON ورودی
        with patch("ai_engine.agent._call_model_step") as mock_step, \
             patch("ai_engine.tools.execute_tool", new_callable=AsyncMock) as mock_exec:

            mock_exec.return_value = "نتیجه ابزار پس از اصلاح"

            # مدل در گام اول JSON خراب می‌دهد، در گام دوم اصلاح می‌کند
            mock_step.side_effect = [
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": "call_bad",
                        "type": "function",
                        "function": {
                            "name": "search_messages",
                            "arguments": "{bad_json: missing_quotes"
                        }
                    }]
                },
                {
                    "role": "assistant",
                    "content": "پاسخ اصلاح‌شده بعد از بازخورد خطا",
                    "tool_calls": []
                }
            ]

            res = await agent.run_agent("پیام‌ها رو سرچ کن", "", "", self.event, self.client)
            self.assertEqual(res, "پاسخ اصلاح‌شده بعد از بازخورد خطا")
            self.assertEqual(mock_step.call_count, 2)

    async def test_agent_max_steps_limit(self):
        # تست سقف گام‌ها جهت جلوگیری از لوپ نامتناهی
        with patch("ai_engine.agent._call_model_step") as mock_step, \
             patch("ai_engine.agent._final_answer_without_tools", return_value="پاسخ اجباری نهایی در سقف گام‌ها"):

            # مدل در هر گام یک ابزار تکراری صدا می‌زند
            mock_step.return_value = {
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": "call_loop",
                    "type": "function",
                    "function": {"name": "get_current_time", "arguments": "{}"}
                }]
            }

            res = await agent.run_agent("تست لوپ", "", "", self.event, self.client, max_steps=3)
            self.assertEqual(res, "پاسخ اجباری نهایی در سقف گام‌ها")

    async def test_circuit_breaker_custom_cooldown(self):
        cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=30)
        # ثبت خطای 429 با کول‌داون سفارشی
        cb.record_failure("test:model", cooldown=50)
        # فوراً باید به وضعیت بسته (ناموجود) برود بدون نیاز به ۳ خطا
        self.assertFalse(cb.is_available("test:model"))

    async def test_graceful_recovery_when_all_fail(self):
        # اگر همه ارائه‌دهنده‌ها شکست بخورند، به جای کرش یا ارور خام پیام هوشمند فارسی بدهد
        with patch("ai_engine.agent._call_model_step", return_value=None), \
             patch("ai_engine.agent._final_answer_without_tools", return_value=""), \
             patch("ai_engine.ai.ask", return_value=getattr(agent.ai, "OFFLINE_MSG", "")):

            res = await agent.run_agent("سوال مهم", "", "", self.event, self.client)
            self.assertIn("ترافیک بالای سرورها", res)
