import unittest
from unittest.mock import patch

from app.services.scoring import ledger_report_service as service


class LedgerReportServiceTest(unittest.TestCase):
    def test_validate_locks_official_score_and_cleans_action_plan(self):
        rule_payload = {
            "finalScore": 49.5,
            "scoreAuthority": "structured_rule_engine",
            "dimensionScores": {"skill": 30},
            "dimensionMaxScores": {"skill": 60},
        }
        fact_pack = {"allowedObservationCodes": ["O02", "O03"]}
        payload = {
            "score_overview": {
                "diagnosis": "现场演示中断与证据不足共同压低了综合表现，需优先修复演示链路。",
                "highlights": ["开场较清晰"],
                "key_issues": ["演示中断"],
            },
            "highlights": ["开场价值交代清楚"],
            "critical_issues": ["AI模块演示中断约90秒"],
            "action_plan": [
                {
                    "priority": "P0",
                    "title": "演示容灾",
                    "problem": "演示中断",
                    "method": "准备离线兜底页并排练切换。",
                    "owner": "技术讲解",
                    "timebox": "3天",
                    "acceptance": "连续5次演示无中断",
                    "observation_codes": ["O03", "FAKE"],
                    "expected_gain": 20,
                }
            ],
            "final_verdict": {"summary": "有基础但关键演示不稳"},
            "improvement_priorities": [
                {"priority": 1, "dimension": "skill", "issue": "演示不稳", "suggestion": "补容灾"}
            ],
            "overall_score": 99,
        }

        validated = service._validate_and_lock_report(payload, rule_payload, fact_pack)
        self.assertEqual(validated["overall_score"], 49.5)
        self.assertEqual(validated["action_plan"][0]["observation_codes"], ["O03"])
        self.assertNotIn("expected_gain", validated["action_plan"][0])

    def test_merge_freezes_dimensions_and_clamps_jury_scores(self):
        base = {
            "overall_score": 49.5,
            "dimensions": {"skill": {"score": 31, "source": "structured_rule_engine"}},
            "generation_meta": {},
        }
        payload = {
            "score_overview": {"diagnosis": "综合分受证据与演示稳定性拖累。"},
            "highlights": ["亮点A"],
            "critical_issues": ["问题A"],
            "jury_review": [
                {"judge_code": "ISTJ", "judge_type": "规范", "score": 90, "comment": "需证据"},
            ],
            "action_plan": [{"title": "x", "method": "y", "problem": "z"}],
            "final_verdict": {"summary": "总结"},
            "improvement_priorities": [{"priority": 1, "issue": "a", "suggestion": "b"}],
        }
        rule_payload = {
            "finalScore": 49.5,
            "dimensionScores": {"skill": 31.0, "value": 18.5},
            "dimensionMaxScores": {"skill": 60.0, "value": 40.0},
            "llmRawScore": 80,
        }
        merged = service._merge_locked_report(base, payload, rule_payload)
        self.assertEqual(merged["overall_score"], 49.5)
        self.assertEqual(merged["dimensions"]["value"]["score"], 18.5)
        self.assertEqual(merged["jury_review"][0]["score_authority"], "diagnostic_only")
        # 90 is clamped near official 49.5 within +/-8 => 57.5
        self.assertEqual(merged["jury_review"][0]["score"], 57.5)
        self.assertIn("49.5", merged["score_overview"]["diagnosis"])

    def test_enrich_returns_base_when_rule_not_ready(self):
        base = {"overall_score": 70, "score_authority": "legacy_llm"}
        out = service.enrich_with_ledger_grounded_report(
            ai_score=base,
            rule_payload={"scoreAuthority": "none"},
            evidence_extraction={},
            asr_result={},
            speech_quality={},
            project_info={},
        )
        self.assertEqual(out["overall_score"], 70)

    def test_rejects_shallow_diagnosis(self):
        rule_payload = {"finalScore": 50, "scoreAuthority": "structured_rule_engine"}
        fact_pack = {"allowedObservationCodes": ["O01"]}
        with self.assertRaisesRegex(ValueError, "stage_a_diagnosis_incomplete"):
            service._validate_and_lock_report(
                {
                    "score_overview": {"diagnosis": "还需优化"},
                    "highlights": ["a"],
                    "critical_issues": ["b"],
                    "action_plan": [{"title": "t", "method": "m", "problem": "p"}],
                    "final_verdict": {"summary": "s"},
                    "improvement_priorities": [{"priority": 1, "issue": "i", "suggestion": "s"}],
                },
                rule_payload,
                fact_pack,
            )

    def test_stage_packs_stay_lean(self):
        fact_pack = {
            "project": {"projectName": "demo"},
            "speechQuality": {"speechRate": 160},
            "authoritativeScore": {"overallScore": 40.3},
            "runningSummary": "summary",
            "topLosses": [{"observationCode": f"O{i}", "points": i} for i in range(20)],
            "observations": [{"observationCode": f"O{i}", "finalScore": 1} for i in range(20)],
            "evidenceItems": [{"text": "x" * 200} for _ in range(20)],
            "seedHighlights": ["h"] * 10,
            "seedCriticalIssues": ["c"] * 10,
            "seedActionPlan": [{"title": "a"} for _ in range(10)],
            "allowedObservationCodes": ["O1", "O2"],
        }
        pack_a = service._stage_pack_a(fact_pack)
        pack_b = service._stage_pack_b(fact_pack, {"diagnosis": "d"})
        self.assertLessEqual(len(pack_a["topLosses"]), 10)
        self.assertLessEqual(len(pack_a["evidenceItems"]), 8)
        self.assertLessEqual(len(pack_b["topLosses"]), 8)
        self.assertIn("stageA", pack_b)
        prompt_a = service._build_stage_a_prompt(fact_pack)
        prompt_b = service._build_stage_b_prompt(fact_pack, {"diagnosis": "d"})
        self.assertIn("阶段A", prompt_a)
        self.assertIn("jury_review", prompt_b)
        self.assertLess(len(prompt_a), 12000)
        self.assertLess(len(prompt_b), 10000)

    def test_stage_b_requires_nine_jury(self):
        with self.assertRaisesRegex(ValueError, "stage_b_jury"):
            service._validate_stage_b(
                {"jury_review": [{"judge_code": "A"}], "final_verdict": {"summary": "足够长的总结文本"}},
                {"finalScore": 40},
            )
        ok = service._validate_stage_b(
            {
                "jury_review": [
                    {"judge_code": f"J{i}", "judge_type": f"type{i}", "score": 40, "comment": "c"}
                    for i in range(9)
                ],
                "final_verdict": {"summary": "本场有基础但仍需补证据链。"},
            },
            {"finalScore": 40},
        )
        self.assertEqual(len(ok["jury_review"]), 9)

    def test_stage_b1_locks_assigned_persona_roster(self):
        assigned = [
            {"code": "ISFJ", "name": "落地关怀型评委", "short_label": "用户、服务", "seat_no": 1},
            {"code": "ENTJ", "name": "价值决策型评委", "short_label": "价值、竞争", "seat_no": 2},
            {"code": "INTP", "name": "逻辑推理型评委", "short_label": "逻辑、算法", "seat_no": 3},
            {"code": "ESFP", "name": "表达感染型评委", "short_label": "表达", "seat_no": 4},
            {"code": "ESTP", "name": "现场表现型评委", "short_label": "冲击力", "seat_no": 5},
            {"code": "INFJ", "name": "愿景洞察型评委", "short_label": "愿景", "seat_no": 6},
            {"code": "ESTJ", "name": "交付管理型评委", "short_label": "交付", "seat_no": 7},
            {"code": "ENFJ", "name": "领导说服型评委", "short_label": "领导力", "seat_no": 8},
            {"code": "ISTP", "name": "实操验证型评委", "short_label": "演示", "seat_no": 9},
        ]
        # Missing one assigned persona must fail.
        with self.assertRaisesRegex(ValueError, "stage_b_jury_missing_assigned"):
            service._validate_stage_b1(
                {
                    "jury_review": [
                        {"judge_code": row["code"], "score": 40, "comment": "c"}
                        for row in assigned[:-1]
                    ]
                },
                {"finalScore": 40},
                assigned_personas=assigned,
            )
        payload = service._validate_stage_b1(
            {
                "jury_review": [
                    {
                        "judge_code": row["code"],
                        "judge_type": "wrong-type",
                        "score": 41,
                        "comment": "独立点评",
                        "recognition": "亮点",
                        "concern": "缺口",
                        "challenge_question": "追问",
                    }
                    for row in assigned
                ]
            },
            {"finalScore": 40},
            assigned_personas=assigned,
        )
        codes = [row["judge_code"] for row in payload["jury_review"]]
        self.assertEqual(codes, [row["code"] for row in assigned])
        self.assertEqual(payload["jury_review"][0]["judge_type"], "落地关怀型评委")
        self.assertEqual(payload["jury_review"][1]["judge_type"], "价值决策型评委")

    def test_select_report_jury_uses_pool_sample_not_fixed_set(self):
        a, meta_a = service._select_report_jury_personas(
            meeting_id="meeting-alpha",
            rule_payload={"scoreInstanceId": "s1"},
            project_info={},
            ai_score={},
        )
        b, meta_b = service._select_report_jury_personas(
            meeting_id="meeting-beta",
            rule_payload={"scoreInstanceId": "s2"},
            project_info={},
            ai_score={},
        )
        self.assertEqual(len(a), 9)
        self.assertEqual(len(b), 9)
        self.assertEqual(meta_a["seed"], "meeting-alpha:ai_jury_v1")
        self.assertEqual(meta_b["seed"], "meeting-beta:ai_jury_v1")
        # Same seed is stable; different meetings should usually differ.
        a2, _ = service._select_report_jury_personas(
            meeting_id="meeting-alpha",
            rule_payload={},
            project_info={},
            ai_score={},
        )
        self.assertEqual([p["code"] for p in a], [p["code"] for p in a2])
        self.assertNotEqual([p["code"] for p in a], [p["code"] for p in b])

    def test_fallback_jury_follows_assigned_personas(self):
        assigned = [
            {"code": "ISFJ", "name": "落地关怀型评委", "short_label": "用户", "seat_no": 1},
            {"code": "ENTJ", "name": "价值决策型评委", "short_label": "价值", "seat_no": 2},
            {"code": "INTP", "name": "逻辑推理型评委", "short_label": "逻辑", "seat_no": 3},
            {"code": "ESFP", "name": "表达感染型评委", "short_label": "表达", "seat_no": 4},
            {"code": "ESTP", "name": "现场表现型评委", "short_label": "冲击力", "seat_no": 5},
            {"code": "INFJ", "name": "愿景洞察型评委", "short_label": "愿景", "seat_no": 6},
            {"code": "ESTJ", "name": "交付管理型评委", "short_label": "交付", "seat_no": 7},
            {"code": "ENFJ", "name": "领导说服型评委", "short_label": "领导力", "seat_no": 8},
            {"code": "ISTP", "name": "实操验证型评委", "short_label": "演示", "seat_no": 9},
        ]
        rows = service._fallback_jury_review(
            {"highlights": ["开场清晰"], "critical_issues": ["演示中断"]},
            {"finalScore": 40.3},
            assigned_personas=assigned,
        )
        self.assertEqual(len(rows), 9)
        self.assertEqual([r["judge_code"] for r in rows], [p["code"] for p in assigned])
        self.assertEqual(rows[0]["judge_type"], "落地关怀型评委")
        self.assertEqual(rows[0]["score_authority"], "diagnostic_only")

    def test_b1_prompt_lists_assigned_not_fixed_nine(self):
        assigned = [
            {"code": "ISFJ", "name": "落地关怀型评委", "short_label": "用户"},
            {"code": "ENTJ", "name": "价值决策型评委", "short_label": "价值"},
        ]
        prompt = service._build_stage_b1_prompt(
            {"authoritativeScore": {"overallScore": 40}},
            {"diagnosis": "d"},
            assigned_personas=assigned,
        )
        self.assertIn("ISFJ", prompt)
        self.assertIn("ENTJ", prompt)
        self.assertIn("人格库抽样", prompt)
        self.assertNotIn("必须且只能按 assignedJury 名单输出，judge_code 顺序与集合必须完全一致：ENFJ,ENTP", prompt)


if __name__ == "__main__":
    unittest.main()
