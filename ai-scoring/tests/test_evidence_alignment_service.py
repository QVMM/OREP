"""音画证据对齐：facts 构建与 IDE 绝对否定句消歧。"""

from __future__ import annotations

import unittest

from app.services.evidence_alignment_service import (
    apply_skill_visual_rescore,
    build_visual_dev_tool_facts,
    sanitize_ai_score_payload,
    sanitize_result_for_report,
    sanitize_scoring_text,
    format_visual_constraints_for_prompt,
    build_prompt_visual_block,
)


class EvidenceAlignmentTests(unittest.TestCase):
    def test_facts_from_screen_type_distribution(self):
        facts = build_visual_dev_tool_facts(
            fusion_context={
                "screen_content_summary": {
                    "screen_type_distribution": {"代码编辑器": 21, "PPT幻灯片": 58, "终端命令行": 4},
                    "content_type_counts": {"代码展示": 25},
                    "code_detections": [{"timestamp_min": 12.5, "desc": "源码"}],
                }
            }
        )
        self.assertTrue(facts["has_code_editor_ui"])
        self.assertTrue(facts["has_terminal_ui"])
        self.assertTrue(facts["has_dev_tool_ui"])
        self.assertGreaterEqual(facts["editor_count"], 21)

    def test_sanitize_absolute_ide_claim(self):
        facts = {"has_dev_tool_ui": True, "has_code_editor_ui": True}
        text = "技能展示无深度：全程未展示IDE、调试工具、配置文件、命令行等任何开发者工具，技能熟练度被严重扣分。"
        out = sanitize_scoring_text(text, facts)
        self.assertNotIn("全程未展示IDE", out)
        self.assertNotIn("全程未展示任何", out)
        self.assertTrue("代码" in out or "工程" in out or "界面" in out)

    def test_no_rewrite_without_visual(self):
        facts = {"has_dev_tool_ui": False}
        text = "全程未展示IDE界面，无法评估技能。"
        out = sanitize_scoring_text(text, facts)
        self.assertIn("全程未展示IDE", out)

    def test_strip_leak_phrases(self):
        facts = {"has_dev_tool_ui": True}
        text = "问题。【画面识别提示】本场抽帧已识别到代码编辑器约 21 帧。"
        out = sanitize_scoring_text(text, facts)
        self.assertNotIn("抽帧", out)
        self.assertNotIn("画面识别", out)

    def test_sanitize_ai_score_recursive(self):
        facts = build_visual_dev_tool_facts(
            fusion_context={
                "screen_content_summary": {
                    "screen_type_distribution": {"代码编辑器": 10},
                    "code_detections": [{"timestamp_min": 1}],
                }
            }
        )
        ai = {
            "critical_issues": ["全程未展示任何IDE界面，导致技能扣分。"],
            "final_verdict": {
                "critical_deductions": [
                    "技能展示无深度（-15分）：全程未展示IDE、调试工具、配置文件、命令行等任何开发者工具，技能水平和任务难易度被严重扣分。"
                ],
                "summary": "整体未展示IDE。",
            },
            "score_overview": {"diagnosis": "全程未展示IDE。", "key_issues": ["未展示任何IDE界面"]},
        }
        out = sanitize_ai_score_payload(ai, facts)
        blob = str(out)
        self.assertNotIn("全程未展示IDE", blob)
        self.assertNotIn("未展示任何IDE界面", blob)

    def test_sanitize_result_for_report(self):
        result = {
            "fusion": {
                "screen_content_summary": {
                    "screen_type_distribution": {"代码编辑器": 5},
                    "code_detections": [{"timestamp_min": 3.0, "desc": "code"}],
                }
            },
            "ai_score": {
                "critical_issues": ["全程未展示IDE、调试工具。"],
                "overall_score": 36.8,
            },
        }
        out = sanitize_result_for_report(result)
        self.assertEqual(out["ai_score"]["overall_score"], 36.8)
        self.assertNotIn("全程未展示IDE", str(out["ai_score"]["critical_issues"]))
        # 原 result 不被污染
        self.assertIn("全程未展示IDE", result["ai_score"]["critical_issues"][0])

    def test_prompt_block_has_constraints(self):
        block = build_prompt_visual_block(
            {
                "screen_content_summary": {
                    "screen_type_distribution": {"代码编辑器": 21},
                    "code_detections": [{"timestamp_min": 10, "desc": "VSCode"}],
                    "content_type_counts": {"代码展示": 3},
                }
            }
        )
        self.assertIn("硬约束", block)
        self.assertIn("禁止", block)
        self.assertIn("代码编辑", block)

    def test_constraints_empty_without_dev_ui(self):
        facts = build_visual_dev_tool_facts(
            fusion_context={"screen_content_summary": {"screen_type_distribution": {"PPT幻灯片": 10}}}
        )
        self.assertFalse(facts["has_dev_tool_ui"])
        self.assertEqual(format_visual_constraints_for_prompt(facts), "")

    def test_skill_rescore_session40_style_no_items(self):
        """画面有代码编辑器 + skill 过低 + 文案按无工具扣 → 抬 skill 与总分。"""
        facts = {
            "has_dev_tool_ui": True,
            "has_code_editor_ui": True,
            "has_terminal_ui": True,
            "has_code_content": True,
        }
        ai = {
            "overall_score": 36.8,
            "critical_issues": [
                "技能展示无深度（-15分）：全程未展示IDE、调试工具、配置文件、命令行等任何开发者工具。"
            ],
            "final_verdict": {
                "summary": "最终得分36.8，处于较低水平。",
                "critical_deductions": [
                    "技能展示无深度（-15分）：全程未展示IDE、调试工具。"
                ],
            },
            "score_overview": {
                "total_score": 36.8,
                "diagnosis": "权威总分36.8，核心原因是技能熟练度（skill_level）仅得27/60分。",
            },
            "dimensions": {
                "skill_level": {"score": 27.0, "max_score": 60.0, "items": []},
                "professionalism": {"score": 3.0, "max_score": 10.0},
                "application_value": {"score": 2.5, "max_score": 10.0},
                "teamwork": {"score": 2.5, "max_score": 10.0},
                "innovation": {"score": 1.8, "max_score": 10.0},
            },
        }
        out = sanitize_ai_score_payload(ai, facts)
        skill = out["dimensions"]["skill_level"]["score"]
        self.assertGreater(skill, 27.0)
        self.assertLessEqual(skill, 34.8)  # 58% cap of 60
        self.assertAlmostEqual(skill, 34.0, places=1)  # 27+7
        self.assertAlmostEqual(out["overall_score"], 43.8, places=1)  # 36.8+7
        meta = out.get("_skill_visual_rescore") or {}
        self.assertEqual(meta.get("before"), 27.0)
        self.assertEqual(meta.get("credit_rule"), "code_editor")
        # 文案已消歧
        blob = str(out)
        self.assertNotIn("全程未展示IDE", blob)
        self.assertNotIn("抽帧", blob)
        # 分值括号弱化
        self.assertNotIn("（-15分）", blob)
        # 叙述分数字面量同步
        self.assertEqual(out["score_overview"]["total_score"], 43.8)
        self.assertIn("43.8", out["score_overview"]["diagnosis"])
        self.assertIn("34/60", out["score_overview"]["diagnosis"])
        self.assertNotIn("36.8", out["score_overview"]["diagnosis"])
        self.assertNotIn("仅得27", out["score_overview"]["diagnosis"])
        self.assertIn("43.8", out["final_verdict"]["summary"])

    def test_skill_rescore_no_boost_without_visual(self):
        facts = {"has_dev_tool_ui": False}
        ai = {
            "overall_score": 36.8,
            "critical_issues": ["全程未展示IDE。"],
            "dimensions": {"skill_level": {"score": 27.0, "max_score": 60.0}},
        }
        out = apply_skill_visual_rescore(ai, facts)
        self.assertEqual(out["dimensions"]["skill_level"]["score"], 27.0)
        self.assertEqual(out["overall_score"], 36.8)

    def test_skill_rescore_idempotent(self):
        facts = {"has_dev_tool_ui": True, "has_code_editor_ui": True}
        ai = {
            "overall_score": 28.7,
            "critical_issues": ["技能展示无深度：全程未展示IDE。"],
            "dimensions": {"skill_level": {"score": 24.0, "max_score": 60.0, "items": []}},
        }
        once = sanitize_ai_score_payload(ai, facts)
        twice = sanitize_ai_score_payload(once, facts)
        self.assertAlmostEqual(
            once["dimensions"]["skill_level"]["score"],
            twice["dimensions"]["skill_level"]["score"],
            places=2,
        )
        self.assertAlmostEqual(once["overall_score"], twice["overall_score"], places=2)
        self.assertEqual(twice["_skill_visual_rescore"]["before"], 24.0)

    def test_skill_rescore_cap_and_high_score_skip(self):
        facts = {"has_dev_tool_ui": True, "has_code_editor_ui": True}
        # 已高且无「无工具」叙事 → 不抬
        ai_hi = {
            "overall_score": 70.0,
            "critical_issues": ["工程操作深度可再加强。"],
            "dimensions": {"skill_level": {"score": 40.0, "max_score": 60.0}},
        }
        out_hi = apply_skill_visual_rescore(ai_hi, facts)
        self.assertEqual(out_hi["dimensions"]["skill_level"]["score"], 40.0)

        # 已达可见性上限 → 不抬
        ai_cap = {
            "overall_score": 50.0,
            "critical_issues": ["技能展示无深度：全程未展示IDE。"],
            "dimensions": {"skill_level": {"score": 34.8, "max_score": 60.0}},
        }
        out_cap = apply_skill_visual_rescore(ai_cap, facts)
        self.assertEqual(out_cap["dimensions"]["skill_level"]["score"], 34.8)

    def test_skill_rescore_with_items(self):
        facts = {"has_dev_tool_ui": True, "has_code_editor_ui": True}
        ai = {
            "overall_score": 30.0,
            "critical_issues": ["技能展示无深度：全程未展示IDE。"],
            "dimensions": {
                "skill_level": {
                    "score": 20.0,
                    "max_score": 60.0,
                    "items": [
                        {"name": "操作规范性", "score": 3.0, "max_score": 10.0, "reason": "未展示工具"},
                        {"name": "技能熟练度", "score": 5.0, "max_score": 15.0, "reason": "深度不足"},
                        {"name": "任务难易度", "score": 12.0, "max_score": 15.0, "reason": "任务完整"},
                        {"name": "现场讲解效果", "score": 0.0, "max_score": 20.0, "reason": "一般"},
                    ],
                }
            },
        }
        out = apply_skill_visual_rescore(ai, facts)
        skill = out["dimensions"]["skill_level"]
        self.assertGreater(skill["score"], 20.0)
        self.assertLessEqual(skill["score"], 34.8)
        # items 分数之和 = skill.score
        item_sum = sum(float(it["score"]) for it in skill["items"])
        self.assertAlmostEqual(item_sum, skill["score"], places=1)
        # 熟练度应被抬高
        fluency = next(it for it in skill["items"] if "熟练" in it["name"])
        self.assertGreater(fluency["score"], 5.0)


if __name__ == "__main__":
    unittest.main()