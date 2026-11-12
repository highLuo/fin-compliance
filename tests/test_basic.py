#!/usr/bin/env python3
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fin_compliance as fc


class TestBasic(unittest.TestCase):

    def setUp(self):
        self.rules = fc.load_rules(None)

    def test_clean_sample_no_findings(self):
        p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "samples", "clean", "compliant-ad.md")
        found = fc._scan_file(p, self.rules, os.path.dirname(p))
        # 合规示例只应触发 low 级 "AI标识已标识" 之外的 0 命中（已含标识，故 0）
        self.assertEqual(len(found), 0, "合规示例不应有任何命中: %s" % found)

    def test_violation_sample_finds_categories(self):
        p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "samples", "violation.md")
        found = fc._scan_file(p, self.rules, os.path.dirname(p))
        cats = {x["category"] for x in found}
        for must in ("收益承诺", "荐股", "引流"):
            self.assertIn(must, cats, "应检出 %s，实际: %s" % (must, cats))
        # violation.md 无 AI 标识，应触发 missing_marker
        self.assertIn("AI标识", cats)

    def test_self_test_passes(self):
        self.assertTrue(fc.run_self_test())


if __name__ == "__main__":
    unittest.main()
