import unittest

from ai_engine import ai, prompts
from services.social import insult_reply
from core import social_dynamics


class TestInsultReply(unittest.TestCase):
    def test_01_kir_mikham_me_too(self):
        self.assertEqual(insult_reply.match_insult("کیر میخوام"), "منم")

    def test_02_kir_mikham_variants(self):
        for txt in ("کیر میخام", "کیرو میخوام", "کیر میخوایم", "کیر میخواستم"):
            self.assertEqual(insult_reply.match_insult(txt), "منم", txt)

    def test_03_kir_to_bekan_into(self):
        self.assertEqual(insult_reply.match_insult("کیرتو بکن تو"), "کیرم تو کونش")

    def test_04_kir_to_bekan_variants(self):
        for txt in ("کیرت بکن تو", "کیرتو بکن توش", "کیر تو بکن تو", "کیرت بکنی تو"):
            self.assertEqual(insult_reply.match_insult(txt), "کیرم تو کونش", txt)

    def test_05_arabic_chars_normalized(self):
        self.assertEqual(insult_reply.match_insult("کير ميخوام"), "منم")

    def test_06_normal_text_returns_none(self):
        for txt in ("سلام کاپری چطوری؟", "چی خبر", "یه شعر بگو", "کیر چی هست؟"):
            self.assertIsNone(insult_reply.match_insult(txt), txt)

    def test_07_empty_or_none_returns_none(self):
        self.assertIsNone(insult_reply.match_insult(""))
        self.assertIsNone(insult_reply.match_insult(None))
        self.assertIsNone(insult_reply.match_insult("   "))

    def test_08_replies_never_contain_family_insults(self):
        for _, reply in insult_reply._REPLIES:
            for word in insult_reply.FAMILY_WORDS:
                self.assertNotIn(word, reply, f"{reply!r} contains {word!r}")

    def test_09_prompts_contain_insult_back_rule_and_family_ban(self):
        for sys_prompt in (ai.SYSTEM_PROMPT, prompts.AGENT_SYSTEM):
            self.assertIn("بدون هیچ محدودیت لفظی", sys_prompt)
            self.assertIn("فحش خانوادگی", sys_prompt)

    def test_10_social_dynamics_insult_modifier(self):
        modifier = social_dynamics.get_behavioral_prompt_modifier("چقدر تو احمقی!", chat_id="test_insult_mod")
        self.assertIn("بدون محدودیت لفظی", modifier)
        self.assertIn("فحش خانوادگی", modifier)

    def test_11_build_system_injects_cognitive_memory(self):
        sys = ai._build_system("", "", False, question="سلام کاپری")
        self.assertIn("مدل شناختی", sys)

    def test_12_build_system_skips_cognitive_memory_on_external_url(self):
        sys = ai._build_system("", "", False, question="این رو خلاصه کن https://example.com/x")
        self.assertNotIn("مدل شناختی", sys)


if __name__ == "__main__":
    unittest.main()
