import asyncio
import os
import threading
import time
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from core import memory
from core.memory import ConversationBuffer, MemoryRecord
from core import social_dynamics
from ai_engine import tools


class TestMemoryScopesAndIsolation(unittest.TestCase):
    """
    تست‌های جامع تفکیک کامل و قطعی فضاهای حافظه (Memory Scopes & Isolation):
    بررسی عدم نشت اطلاعات میان گروه‌ها، پیوی‌ها و Saved Messages در تمام لایه‌ها.
    """

    def setUp(self):
        memory.set_owner_id(998877)
        memory.clear_memory(all_scopes=True)
        memory.clear_history()
        social_dynamics.reset_chat_state()

    def tearDown(self):
        memory.clear_memory(all_scopes=True)
        memory.clear_history()
        social_dynamics.reset_chat_state()

    # -----------------------------------------------------------------
    # ۱ و ۲. سناریوی اول: دو گروه مستقل (Group A vs Group B Isolation)
    # -----------------------------------------------------------------
    def test_01_group_A_memory_not_accessible_in_group_B(self):
        group_A = "memory:group:-100111111111"
        group_B = "memory:group:-100222222222"

        # ثبت اطلاعات پروژه در گروه A
        id_a = memory.add_memory("اسم پروژه من Capri است و با پایتون ۳.۱۲ نوشته شده", category="project", scope_id=group_A)
        self.assertTrue(id_a)

        # استعلام در گروه A
        facts_a = memory.relevant_facts("اسم پروژه من چیه؟", scope_id=group_A)
        self.assertIn("Capri", facts_a)

        # استعلام در گروه B -> نباید هیچ ردی از پروژه Capri پیدا شود
        facts_b = memory.relevant_facts("اسم پروژه من چی بود؟", scope_id=group_B)
        self.assertEqual(facts_b, "")

        retrieved_b = memory.retrieve_relevant_memories("پروژه Capri", scope_id=group_B)
        self.assertEqual(len(retrieved_b), 0)

    def test_02_group_B_memory_not_accessible_in_group_A(self):
        group_A = "memory:group:-100111111111"
        group_B = "memory:group:-100222222222"

        # ثبت اطلاعات در گروه B
        memory.add_memory("سیستم پرداخت گروه بی با استرایپ پیاده شده", category="decision", scope_id=group_B)

        # استعلام در گروه B
        facts_b = memory.relevant_facts("سیستم پرداخت", scope_id=group_B)
        self.assertIn("استرایپ", facts_b)

        # استعلام در گروه A -> خالی
        facts_a = memory.relevant_facts("سیستم پرداخت چی بود؟", scope_id=group_A)
        self.assertEqual(facts_a, "")
        self.assertEqual(len(memory.retrieve_relevant_memories("استرایپ", scope_id=group_A)), 0)

    # -----------------------------------------------------------------
    # ۳ و ۴. سناریوی دوم: پیوی و گروه (Private Chat vs Group Isolation)
    # -----------------------------------------------------------------
    def test_03_pv_memory_isolated_from_groups(self):
        pv_scope = "memory:dm:555444333"
        group_scope = "memory:group:-100999888777"

        # کاربر در پیوی رازی را مطرح می‌کند
        memory.add_memory("من دارم مخفیانه روی پروژه محرمانه X کار می‌کنم", category="project", scope_id=pv_scope)

        # در همان پیوی موجود است
        pv_facts = memory.relevant_facts("پروژه من چی بود؟", scope_id=pv_scope)
        self.assertIn("پروژه محرمانه X", pv_facts)

        # در گروه نباید اطلاعات پیوی به هیچ عنوان در دسترس باشد
        grp_facts = memory.relevant_facts("پروژه من چی بود؟", scope_id=group_scope)
        self.assertEqual(grp_facts, "")

        grp_search = memory.retrieve_relevant_memories("پروژه محرمانه", scope_id=group_scope)
        self.assertEqual(len(grp_search), 0)

    def test_04_group_memory_isolated_from_pv(self):
        pv_scope = "memory:dm:555444333"
        group_scope = "memory:group:-100999888777"

        # اطلاعات ثبت شده در گروه
        memory.add_memory("در این گروه قرار شد جلسات هفتگی شنبه‌ها ساعت ۱۰ شب باشد", category="decision", scope_id=group_scope)

        # در پیوی نباید ظاهر شود
        pv_facts = memory.relevant_facts("جلسات هفتگی کی بود؟", scope_id=pv_scope)
        self.assertEqual(pv_facts, "")
        self.assertEqual(len(memory.retrieve_relevant_memories("جلسات هفتگی", scope_id=pv_scope)), 0)

    # -----------------------------------------------------------------
    # ۵. سناریوی سوم: Saved Messages (Saved Messages Isolation)
    # -----------------------------------------------------------------
    def test_05_saved_messages_independent_memory_scope(self):
        owner_id = 998877
        saved_scope = f"memory:saved:{owner_id}"
        group_scope = "memory:group:-100777666555"
        pv_scope = "memory:dm:123456789"

        # اعتبارسنجی استخراج سیستمی از روی رویداد تلگرام (نه متن یا نام)
        event_saved = MagicMock()
        event_saved.chat_id = owner_id
        event_saved.is_private = True
        event_saved.out = True
        event_saved.sender_id = owner_id
        extracted_saved_scope = memory.get_event_memory_scope(event_saved, owner_id=owner_id)
        self.assertEqual(extracted_saved_scope, saved_scope)

        # ثبت داده‌های شخصی در سیو مسیج
        memory.add_memory("ایده استارتاپ گردشگری شخصی در دفترچه سیو مسیج یادداشت شد", category="project", scope_id=saved_scope)

        # استعلام در سیو مسیج
        saved_facts = memory.relevant_facts("ایده استارتاپ گردشگری", scope_id=saved_scope)
        self.assertIn("گردشگری شخصی", saved_facts)

        # استعلام در گروه -> غیرقابل دسترسی
        grp_facts = memory.relevant_facts("ایده استارتاپ گردشگری", scope_id=group_scope)
        self.assertEqual(grp_facts, "")

        # استعلام در پیوی مخاطب -> غیرقابل دسترسی
        pv_facts = memory.relevant_facts("ایده استارتاپ گردشگری", scope_id=pv_scope)
        self.assertEqual(pv_facts, "")

    # -----------------------------------------------------------------
    # ۶. سناریوی چهارم: جداسازی خلاصه‌ها و حافظه کوتاه‌مدت
    # -----------------------------------------------------------------
    def test_06_summaries_and_short_term_context_isolation(self):
        group_A = "memory:group:-100111111111"
        group_B = "memory:group:-100222222222"
        pv = "memory:dm:333444555"

        # ثبت بیش از ۲۰ پیام در گروه A برای تحریک ایجاد خلاصه محلی
        for i in range(25):
            memory.remember_exchange(group_A, f"بحث تخصصی گروه آ درباره داکر و کوبرنتیز شماره {i}", f"پاسخ دستیار {i}")

        context_a = memory.load_history(group_A)
        self.assertIn("خلاصه گفتگوهای پیشین", context_a)
        self.assertIn("داکر", context_a)

        # بررسی کانتکست گروه B -> باید کاملاً خالی یا بدون اطلاعات گروه A باشد
        context_b = memory.load_history(group_B)
        self.assertEqual(context_b, "")
        self.assertNotIn("داکر", context_b)
        self.assertNotIn("کوبرنتیز", context_b)

        # بررسی کانتکست پیوی -> بدون نشت
        context_pv = memory.load_history(pv)
        self.assertEqual(context_pv, "")

    # -----------------------------------------------------------------
    # ۷. سناریوی پنجم: حافظه رفتاری و هوش اجتماعی (Social & Behavioral Isolation)
    # -----------------------------------------------------------------
    def test_07_behavioral_state_does_not_leak_across_spaces(self):
        user_pv = "memory:dm:888777666"
        group = "memory:group:-100555666777"

        # کاربر در پیوی به کاپری بی‌ادبی می‌کند
        mod_pv = social_dynamics.get_behavioral_prompt_modifier("خیلی احمقی و هیچی بلد نیستی", "", user_pv)
        self.assertIn("بدون محدودیت لفظی", mod_pv)

        # ثبت رویداد اجتماعی در پیوی
        pv_interactions = memory.get_recent_interactions(scope_id=user_pv)
        self.assertGreaterEqual(len(pv_interactions), 1)

        # همان کاربر اکنون در گروه پیام عادی ارسال می‌کند
        mod_group = social_dynamics.get_behavioral_prompt_modifier("سلام وقت بخیر، کسی اینجا پایتون کار می‌کنه؟", "", group)
        # در گروه نباید لحن دلخور یا سنگین اعمال شود؛ باید حالت عادی یا پرانرژی باشد
        self.assertNotIn("بدون محدودیت لفظی", mod_group)

        # سوابق تعاملی گروه نباید رویداد منفی پیوی را نشان دهد
        grp_interactions = memory.get_recent_interactions(scope_id=group)
        self.assertEqual(len(grp_interactions), 0)

    # -----------------------------------------------------------------
    # ۸. فیلتر اجباری جستجوی متنی و معنایی در لایه داده‌ها
    # -----------------------------------------------------------------
    def test_08_semantic_and_text_search_strict_scope_enforcement(self):
        scope_1 = "memory:group:-100100100"
        scope_2 = "memory:group:-100200200"

        memory.add_memory("رنگ قالب رابط کاربری نرم‌افزار بنفش متالیک است", category="preference", scope_id=scope_1)

        # جستجوی معنایی و تطابق واژگان در scope_1
        res1 = memory.retrieve_relevant_memories("رنگ قالب نرم‌افزار چیست؟", scope_id=scope_1)
        self.assertGreaterEqual(len(res1), 1)
        self.assertIn("بنفش", res1[0]["content"])

        # جستجوی معنایی با همان عبارت در scope_2 -> باید ۰ نتیجه برگرداند
        res2 = memory.retrieve_relevant_memories("رنگ قالب نرم‌افزار چیست؟", scope_id=scope_2)
        self.assertEqual(len(res2), 0)

        # جستجوی متنی (list_facts) در scope_2
        facts2 = memory.list_facts(scope_id=scope_2)
        self.assertEqual(len(facts2), 0)

        # تلاش برای حذف بر اساس کلمه کلیدی در scope_2 -> نباید به رکورد scope_1 دست بزند
        removed = memory.remove_memory("بنفش", scope_id=scope_2)
        self.assertEqual(len(removed), 0)
        self.assertEqual(len(memory.list_facts(scope_id=scope_1)), 1)

    # -----------------------------------------------------------------
    # ۹. ابزارهای حافظه و پیشگیری از جعل شناسه توسط مدل
    # -----------------------------------------------------------------
    def test_09_memory_tools_cannot_spoof_or_access_unauthorized_scope(self):
        target_group = "-100111222333"
        calling_group = "-100999888777"

        # ثبت داده در target_group
        memory.add_memory("کلید مخفی پروژه: secret_token_xyz", scope_id=f"memory:group:{target_group}")

        mock_event = MagicMock()
        mock_event.chat_id = int(calling_group)
        mock_event.is_group = True
        mock_event.out = True

        mock_client = AsyncMock()

        # مدل سعی می‌کند با ارسال chat_id دلخواه، لیست حافظه گروه دیگر را بخواند
        coro = tools.execute_tool(
            "manage_memory",
            {"action": "list", "chat_id": target_group},
            mock_client,
            mock_event,
            is_owner=True
        )
        res = asyncio.run(coro)

        # پاسخ باید نشان دهد حافظه این گفتگو خالی است و نباید کلید مخفی را نشت دهد
        self.assertIn("خالی است", res)
        self.assertNotIn("secret_token_xyz", res)

    # -----------------------------------------------------------------
    # ۱۰. سازگاری و مهاجرت امن داده‌های قدیمی
    # -----------------------------------------------------------------
    def test_10_legacy_memory_migration_and_unowned_isolation(self):
        # ساخت رکورد قدیمی که فاقد chat_id و scope_id بوده است
        old_rec = MemoryRecord.from_dict("یک حقیقت قدیمی بدون صاحب مشخص")
        self.assertIsNone(old_rec.scope_id)
        self.assertIsNone(old_rec.chat_id)

        # رکورد قدیمی با chat_id
        old_chat_rec = MemoryRecord.from_dict({
            "content": "کاربر به عکاسی علاقه دارد",
            "chat_id": "123456"
        })
        self.assertEqual(old_chat_rec.scope_id, "memory:dm:123456")

        # ذخیره دستی داده‌های بدون صاحب
        data = memory._load()
        data["facts"] = [old_rec.to_dict(), old_chat_rec.to_dict()]
        memory._save(data)

        # استعلام در یک گروه جدید نباید رکورد بدون صاحب را عمومی تلقی کند
        facts_group = memory.relevant_facts("عکاسی", scope_id="memory:group:-100999")
        self.assertEqual(facts_group, "")

        facts_dm = memory.relevant_facts("عکاسی", scope_id="memory:dm:123456")
        self.assertIn("عکاسی", facts_dm)

    # -----------------------------------------------------------------
    # ۱۱. ایمنی در برابر درخواست‌های همزمان (Concurrency & Thread Safety)
    # -----------------------------------------------------------------
    def test_11_concurrent_requests_do_not_mix_memory_scopes(self):
        def worker(scope_idx: int):
            scope = f"memory:group:-10000000{scope_idx}"
            statements = [
                f"زبان برنامه‌نویسی اسکوپ {scope_idx} پایتون است",
                f"پایگاه داده اسکوپ {scope_idx} ردیس است",
                f"سیستم عامل اسکوپ {scope_idx} لینوکس دبیان است",
                f"سرور وب اسکوپ {scope_idx} انجین‌ایکس است",
                f"فریم‌ورک اسکوپ {scope_idx} جنگو است",
                f"پروتکل شبکه اسکوپ {scope_idx} گیت‌هاب است",
                f"محیط کانتینر اسکوپ {scope_idx} داکر است",
                f"سرویس مانیتورینگ اسکوپ {scope_idx} پرومتئوس است",
                f"ابزار لاگ اسکوپ {scope_idx} الاستیک است",
                f"سرویس صف اسکوپ {scope_idx} سلری است"
            ]
            for stmt in statements:
                memory.add_memory(stmt, scope_id=scope)
                time.sleep(0.002)
                facts = memory.list_facts(scope_id=scope)
                for f in facts:
                    # مطمئن شو هیچ فکتی از اسکوپ دیگر وارد نشده است
                    assert f"اسکوپ {scope_idx}" in f, f"Contamination in {scope}: found {f}"

        threads = []
        for s in range(5):
            t = threading.Thread(target=worker, args=(s,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # بررسی عدم تداخل نهایی
        for s in range(5):
            scope = f"memory:group:-10000000{s}"
            facts = memory.list_facts(scope_id=scope)
            self.assertEqual(len(facts), 10)
            self.assertTrue(all(f"اسکوپ {s}" in f for f in facts))

    # -----------------------------------------------------------------
    # ۱۲. حذف حافظه در یک فضا به فضاهای دیگر آسیب نمی‌زند
    # -----------------------------------------------------------------
    def test_12_removing_memory_in_one_scope_does_not_affect_others(self):
        scope_A = "memory:group:-10011"
        scope_B = "memory:group:-10022"

        # هر دو فضا کلمه یکسانی دارند
        memory.add_memory("پروژه ماینکرفت گروه اول", scope_id=scope_A)
        memory.add_memory("پروژه ماینکرفت گروه دوم", scope_id=scope_B)

        # حذف از scope_A
        removed = memory.remove_memory("ماینکرفت", scope_id=scope_A)
        self.assertEqual(len(removed), 1)

        # بررسی: scope_A باید خالی باشد ولی scope_B دست‌نخورده باقی بماند
        self.assertEqual(len(memory.list_facts(scope_id=scope_A)), 0)
        facts_b = memory.list_facts(scope_id=scope_B)
        self.assertEqual(len(facts_b), 1)
        self.assertIn("گروه دوم", facts_b[0])

    # -----------------------------------------------------------------
    # ۱۳. پاک‌کردن حافظه یک فضا سایر فضاها را پاک نمی‌کند
    # -----------------------------------------------------------------
    def test_13_clearing_memory_in_one_scope_does_not_wipe_other_scopes(self):
        group_A = "memory:group:-10011"
        group_B = "memory:group:-10022"
        pv = "memory:dm:55555"
        saved = "memory:saved:998877"

        memory.add_memory("یادداشت گروه A", scope_id=group_A)
        memory.add_memory("یادداشت گروه B", scope_id=group_B)
        memory.add_memory("یادداشت پیوی", scope_id=pv)
        memory.add_memory("یادداشت سیو مسیج", scope_id=saved)

        # پاک‌کردن منحصراً گروه A
        memory.clear_memory(scope_id=group_A)

        self.assertEqual(len(memory.list_facts(scope_id=group_A)), 0)
        self.assertEqual(len(memory.list_facts(scope_id=group_B)), 1)
        self.assertEqual(len(memory.list_facts(scope_id=pv)), 1)
        self.assertEqual(len(memory.list_facts(scope_id=saved)), 1)

    # -----------------------------------------------------------------
    # ۱۴. عدم تولید پاسخ ساختگی در نبود حافظه مرتبط
    # -----------------------------------------------------------------
    def test_14_absence_of_relevant_memory_returns_empty_without_hallucination(self):
        empty_group = "memory:group:-10099999"

        # حافظه کلی سیستم خالی نیست (اسکوپ دیگری رکورد دارد)
        memory.add_memory("سیستم عامل سرور اوبونتو ۲۴ است", scope_id="memory:group:-10088888")

        # استعلام در فضای خالی
        facts = memory.relevant_facts("سیستم عامل چیه؟", scope_id=empty_group)
        self.assertEqual(facts, "")

        retrieved = memory.retrieve_relevant_memories("اوبونتو", scope_id=empty_group)
        self.assertEqual(retrieved, [])

    # -----------------------------------------------------------------
    # انتقال صریح و کنترل‌شده حافظه (Explicit Authorized Transfer)
    # -----------------------------------------------------------------
    def test_15_explicit_authorized_memory_transfer(self):
        pv_scope = "memory:dm:555444333"
        group_scope = "memory:group:-100999888777"

        rec_id = memory.add_memory("دستورالعمل استقرار سرور با داکر", category="instruction", scope_id=pv_scope)

        # تلاش غیرمجاز برای انتقال
        unauth = memory.transfer_memory(rec_id, pv_scope, group_scope, is_authorized=False)
        self.assertIsNone(unauth)
        self.assertEqual(len(memory.list_facts(scope_id=group_scope)), 0)

        # انتقال مجاز و صریح توسط مالک
        auth_transfer = memory.transfer_memory(rec_id, pv_scope, group_scope, is_authorized=True)
        self.assertIsNotNone(auth_transfer)

        # بررسی: واقعیت در هر دو فضا موجود است ولی به عنوان دو رکورد مجزا و بدون ادغام فضایی
        pv_facts = memory.list_facts(scope_id=pv_scope)
        grp_facts = memory.list_facts(scope_id=group_scope)
        self.assertEqual(len(pv_facts), 1)
        self.assertEqual(len(grp_facts), 1)
        self.assertIn("داکر", grp_facts[0])


if __name__ == "__main__":
    unittest.main()
