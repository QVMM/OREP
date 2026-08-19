import unittest
import json
from unittest.mock import patch

from app.services.session_pipeline_service import _build_authoritative_jury_result, _build_final_result


class SessionAuthoritativeCallbackTest(unittest.TestCase):
    def test_final_callback_carries_score_free_speaker_evidence(self):
        speaker_evidence = [{
            "rawSpeakerId": "SPEAKER_0",
            "displayName": "1号发言人",
            "roleName": None,
            "matchedName": None,
            "status": "AUTO",
            "source": "final_asr",
            "confidence": 0.91,
            "durationSec": 18.2,
            "evidenceQuotes": ["我们展示核心算法"],
            "segments": [{"startMs": 1000, "endMs": 5000}],
        }]

        speaker_attribution = {
            "contractVersion": "speaker-attribution-v1",
            "revision": 1,
            "status": "FINAL",
            "clock": {"clockId": "clock-26", "masterSource": "MEDIA_PTS"},
            "people": [],
            "turns": [],
            "segments": [],
        }
        final_result = _build_final_result({
            "ai_score": {"overall_score": 49.5},
            "asr": {
                "transcript": "test",
                "segments": [],
                "speakerAttribution": speaker_attribution,
            },
            "speaker_evidence": speaker_evidence,
        })

        self.assertEqual(final_result["speakerEvidence"], speaker_evidence)
        self.assertEqual(final_result["speakerAttribution"], speaker_attribution)
        self.assertNotIn("speakerScores", final_result)

    @patch("app.services.session_pipeline_service.build_rule_engine_shadow_payload")
    def test_v3_callback_contains_reconciled_ledger_tasks_and_coverage(self, build_payload):
        build_payload.return_value = {
            "scoreAuthority": "structured_rule_engine",
            "finalScore": 50.0,
            "ruleEngineScore": 50.0,
            "scoringFingerprint": "fingerprint-v3",
            "observations": [{
                "observationCode": "O1",
                "observationName": "现场演示",
                "dimensionCode": "skill",
                "maxScore": 100.0,
                "baseScore": 50.0,
                "scoreCap": 100.0,
                "finalScore": 50.0,
                "trackDefinition": "稳定完成演示并解释关键技术选择",
                "requiredInfo": ["完整演示过程"],
                "acceptableEvidence": ["完整录像"],
                "trainingTaskTemplate": "完成稳定性修复并复演",
            }],
            "deductions": [],
            "lossLedger": [{
                "causeCode": "O1:performance_gap",
                "observationCode": "O1",
                "lossType": "performance_gap",
                "points": 50.0,
                "reason": "现场演示只达到一半要求",
                "evidenceAnchorIds": [],
                "consumedBy": "performance_score",
            }],
            "evidenceAnchors": [],
            "dimensionScores": {"skill": 50.0},
            "dimensionMaxScores": {"skill": 100.0},
            "reconciliation": {"finalScore": 50.0, "totalLoss": 50.0},
        }
        pipeline_result = {
            "ai_score": {
                "overall_score": 68.0,
                "dimensions": {},
                "action_plan": [{
                    "id": "plan-1",
                    "priority": "P0",
                    "title": "修复并复演",
                    "problem": "现场演示不稳定",
                    "method": "完成稳定性修复并复演",
                    "observationCode": "O1",
                    "expectedRecoverPoints": 50,
                }],
            },
            "evidence_extraction": {
                "status": "completed",
                "ruleHash": "rule-v3",
                "extractionQuality": {"publicationEligible": True},
            },
            "asr": {"transcript": "test", "segments": []},
        }

        final_result = _build_final_result(pipeline_result)
        ledger = json.loads(final_result["lossLedgerJson"])
        tasks = json.loads(final_result["actionPlanJson"])
        coverage = json.loads(final_result["coverageSummaryJson"])
        projection = json.loads(final_result["scoreProjectionJson"])

        self.assertEqual(final_result["contractVersion"], "ai-score-report-v3")
        self.assertEqual(final_result["todoPortfolioStatus"], "complete")
        self.assertTrue(final_result["publishCompleteTodoPortfolio"])
        self.assertEqual(sum(item["points"] for item in ledger), 50.0)
        self.assertEqual(coverage["fullGap"], 50.0)
        self.assertEqual(coverage["coverageRate"], 1.0)
        self.assertEqual(coverage["remediationTaskCount"], len(tasks))
        self.assertEqual(tasks[0]["coveredLossIds"], [ledger[0]["lossId"]])
        self.assertNotIn("expectedRecoverPoints", tasks[0])
        self.assertEqual(tasks[0]["coveredGapPoints"], 50.0)
        self.assertEqual(projection["scenarioScope"], "all_known_tasks_minimum_acceptance")
        self.assertEqual(projection["coveredGapPoints"], 50.0)

    @patch("app.services.session_pipeline_service.build_rule_engine_shadow_payload")
    def test_serializes_all_action_plan_items_and_aligns_matching_observation(self, build_payload):
        build_payload.return_value = {
            "scoreAuthority": "structured_rule_engine",
            "finalScore": 49.5,
            "ruleEngineScore": 49.5,
            "ruleHash": "rule-26",
            "scoringFingerprint": "fingerprint-26",
            "observations": [{
                "observationCode": "O02",
                "dimensionCode": "skill_level",
                "maxScore": 60.0,
                "baseScore": 33.0,
                "scoreCap": 60.0,
                "finalScore": 31.0,
            }],
            "deductions": [{
                "deductionId": "O02-D01",
                "observationCode": "O02",
                "penaltyRuleCode": "SKILL_DEMO_FAILURE",
                "deductedPoints": 2.0,
                "maxRecoverablePoints": 2.0,
                "scoreEffect": "subtractive",
                "status": "new",
            }],
            "evidenceAnchors": [],
        }
        action_plan = [
            {
                "priority": "P0",
                "title": "AI问答模块稳定性加固与备用方案",
                "problem": "AI模块演示严重故障，导致93.96秒中断，严重削弱技术可信度。",
                "method": "增加离线知识库和备用视频。",
                "acceptance": "连续5次演示零故障。",
                "expectedRecoverPoints": 99,
            },
            {"priority": "P0", "title": "精简代码讲解", "problem": "代码讲解过长"},
            {"priority": "P1", "title": "补充数据来源", "problem": "数据缺乏来源"},
            {"priority": "P1", "title": "完善商业模式", "problem": "商业路线不完整"},
            {"priority": "P2", "title": "补安全测试", "problem": "安全证据缺失"},
            {"priority": "P2", "title": "优化语速", "problem": "语速过快"},
        ]
        pipeline_result = {
            "ai_score": {"overall_score": 68.5, "dimensions": {}, "action_plan": action_plan},
            "evidence_extraction": {
                "status": "completed",
                "extractionQuality": {"publicationEligible": True},
                "deductionCandidates": [{
                    "observationCode": "O02",
                    "penaltyRuleCode": "SKILL_DEMO_FAILURE",
                    "triggerFact": "AI问答模块演示出现严重故障，需要现场修改代码，导致演示中断约93.96秒",
                }],
            },
            "asr": {"transcript": "test", "segments": []},
        }

        final_result = _build_final_result(pipeline_result)
        serialized = json.loads(final_result["actionPlanJson"])

        self.assertEqual(len(serialized), 6)
        self.assertEqual([item["title"] for item in serialized], [item["title"] for item in action_plan])
        self.assertEqual(serialized[0]["observationCode"], "O02")
        self.assertEqual(serialized[0]["sourceIssueKey"], "SKILL_DEMO_FAILURE")
        self.assertTrue(serialized[0]["id"].startswith("action-"))
        self.assertNotIn("expectedRecoverPoints", serialized[0])
        self.assertEqual(serialized[0]["scoreImpact"]["impactType"], "deduction_recovery")
        self.assertEqual(serialized[0]["scoreImpact"]["upper"], 2.0)
        projection = json.loads(final_result["scoreProjectionJson"])
        self.assertEqual(projection["goalScore"], 100.0)
        self.assertEqual(projection["currentScore"], 31.0)
        self.assertEqual(projection["predictedScoreUpper"], 33.0)
        self.assertEqual(projection["scoredTodoCount"], 1)
        self.assertEqual(projection["unlinkedAdviceCount"], 5)

    def test_serializes_empty_action_plan_as_empty_array(self):
        final_result = _build_final_result({
            "ai_score": {"overall_score": 68.0, "dimensions": {}},
            "asr": {"transcript": "legacy", "segments": []},
        })

        self.assertEqual(json.loads(final_result["actionPlanJson"]), [])
        projection = json.loads(final_result["scoreProjectionJson"])
        self.assertEqual(projection["goalScore"], 100.0)
        self.assertIsNone(projection["predictedScoreUpper"])

    @patch("app.services.session_pipeline_service.build_rule_engine_shadow_payload")
    def test_uses_structured_rule_score_as_overall_score(self, build_payload):
        build_payload.return_value = {
            "scoreAuthority": "structured_rule_engine",
            "scorePolicyVersion": "score-policy-v2-single-attribution",
            "finalScore": 73.5,
            "ruleEngineScore": 73.5,
            "llmRawScore": 86.0,
            "scoreDiff": -12.5,
            "diffReasons": ["score_diff_exceeds_10"],
            "ruleEngineVersion": "v1-authoritative",
            "scoringFingerprint": "rule-hash",
            "observations": [{"observationCode": "O1", "finalScore": 73.5}],
            "deductions": [{"deductionId": "O1:missing-proof"}],
            "diagnosticDeductions": [{"deductionId": "O1:evidence-gap"}],
            "lossLedger": [{"causeCode": "O1:performance_gap", "points": 26.5}],
            "evidenceAnchors": [{"id": 1}],
            "reconciliation": {"finalScore": 73.5, "dimensionScoreTotal": 73.5},
            "dimensionScores": {"market": 73.5},
            "dimensionMaxScores": {"market": 100.0},
        }
        pipeline_result = {
            "ai_score": {
                "overall_score": 86.0,
                "raw_overall_score": 88.0,
                "dimensions": {"market": {"score": 86.0}},
                "model": "test-model",
            },
            "evidence_extraction": {"ruleHash": "rule-hash"},
            "asr": {"transcript": "test", "segments": []},
        }

        final_result = _build_final_result(pipeline_result)

        self.assertEqual(final_result["overallScore"], 73.5)
        self.assertEqual(final_result["scoreAuthority"], "structured_rule_engine")
        self.assertEqual(final_result["llmRawScore"], 86.0)
        self.assertEqual(final_result["reconciliation"]["finalScore"], 73.5)
        self.assertEqual(final_result["scorePolicyVersion"], "score-policy-v2-single-attribution")
        self.assertEqual(final_result["lossLedger"][0]["points"], 26.5)
        self.assertEqual(final_result["diagnosticDeductions"][0]["deductionId"], "O1:evidence-gap")
        self.assertTrue(final_result["publishOfficialScore"])
        self.assertEqual(json.loads(final_result["dimensionsJson"]), {
            "market": {"score": 73.5, "max_score": 100.0, "source": "structured_rule_engine"}
        })

    @patch("app.services.session_pipeline_service.build_rule_engine_shadow_payload")
    def test_normalizes_structured_required_fix_to_java_string_contract(self, build_payload):
        build_payload.return_value = {
            "scoreAuthority": "structured_rule_engine",
            "finalScore": 49.5,
            "ruleEngineScore": 49.5,
            "observations": [{"observationCode": "O02", "finalScore": 7.5}],
            "deductions": [{
                "deductionId": "O02-D01",
                "requiredFix": {
                    "title": "补齐技能熟练度证据链",
                    "action": "补充现场操作脚本和异常处理预案",
                    "acceptanceCriteria": ["形成证据对应表", "下一轮主动说明补证内容"],
                },
                "acceptanceCriteria": ["证据可定位", "能支撑观测点"],
            }],
            "evidenceAnchors": [],
        }
        pipeline_result = {
            "ai_score": {"overall_score": 68.5, "dimensions": {}},
            "evidence_extraction": {"status": "completed", "extractionQuality": {"publicationEligible": True}},
            "asr": {"transcript": "test", "segments": []},
        }

        final_result = _build_final_result(pipeline_result)

        deduction = final_result["deductions"][0]
        self.assertIsInstance(deduction["requiredFix"], str)
        self.assertIn("补齐技能熟练度证据链", deduction["requiredFix"])
        self.assertIn("补充现场操作脚本和异常处理预案", deduction["requiredFix"])
        self.assertIn("形成证据对应表", deduction["requiredFix"])
        self.assertIsInstance(deduction["acceptanceCriteria"], str)
        self.assertIn("证据可定位", deduction["acceptanceCriteria"])

    def test_marks_legacy_llm_fallback_explicitly(self):
        pipeline_result = {
            "ai_score": {
                "overall_score": 68.0,
                "raw_overall_score": 70.0,
                "dimensions": {},
                "model": "test-model",
            },
            "asr": {"transcript": "legacy", "segments": []},
        }

        final_result = _build_final_result(pipeline_result)

        self.assertEqual(final_result["overallScore"], 68.0)
        self.assertEqual(final_result["scoreAuthority"], "legacy_llm")
        self.assertEqual(final_result["llmRawScore"], 70.0)
        self.assertEqual(final_result["observations"], [])
        self.assertEqual(final_result["deductions"], [])

    def test_does_not_publish_llm_score_when_extraction_exists_without_rule_score(self):
        pipeline_result = {
            "ai_score": {
                "overall_score": 88.0,
                "raw_overall_score": 90.0,
                "dimensions": {"market": {"score": 88.0}},
                "model": "test-model",
            },
            "evidence_extraction": {
                "status": "completed",
                "trackName": "未知赛道",
                "extractionQuality": {"publicationEligible": True},
            },
            "asr": {"transcript": "test", "segments": []},
        }

        with patch(
            "app.services.session_pipeline_service.build_rule_engine_shadow_payload",
            return_value={"scoreAuthority": "none", "llmRawScore": 88.0},
        ):
            final_result = _build_final_result(pipeline_result)

        self.assertIsNone(final_result["overallScore"])
        self.assertEqual(final_result["scoreAuthority"], "review_required")
        self.assertEqual(final_result["reviewReason"], "rule_engine_score_unavailable")
        self.assertEqual(final_result["llmRawScore"], 88.0)
        self.assertEqual(final_result["rawOverallScore"], 90.0)

    def test_review_required_extraction_keeps_llm_out_of_official_score(self):
        pipeline_result = {
            "ai_score": {"overall_score": 77.0, "raw_overall_score": 80.0, "dimensions": {}},
            "evidence_extraction": {
                "status": "review_required",
                "extractionQuality": {"publicationEligible": False},
            },
            "asr": {"transcript": "test", "segments": []},
        }

        final_result = _build_final_result(pipeline_result)

        self.assertIsNone(final_result["overallScore"])
        self.assertEqual(final_result["scoreAuthority"], "review_required")
        self.assertEqual(final_result["reviewReason"], "evidence_extraction_not_publishable")
        self.assertEqual(final_result["llmRawScore"], 80.0)

    def test_jury_receives_the_same_authoritative_score_as_the_user(self):
        pipeline_result = {
            "ai_score": {
                "overall_score": 63.75,
                "dimensions": {"skill_level": {"score": 37.5, "max_score": 60}},
            },
            "video_analysis": {"frame_count": 79},
            "has_video": True,
        }
        final_result = {
            "overallScore": 39.1,
            "scoreAuthority": "structured_rule_engine",
            "dimensionsJson": json.dumps({
                "skill_level": {"score": 28.0, "max_score": 60.0, "source": "structured_rule_engine"}
            }),
        }

        jury_result = _build_authoritative_jury_result(pipeline_result, final_result)

        self.assertEqual(jury_result["ai_score"]["overall_score"], 39.1)
        self.assertEqual(jury_result["ai_score"]["raw_overall_score"], 63.75)
        self.assertEqual(jury_result["ai_score"]["dimensions"]["skill_level"]["score"], 28.0)
        self.assertEqual(jury_result["score_authority"], "structured_rule_engine")
        self.assertEqual(pipeline_result["ai_score"]["overall_score"], 63.75)

    @patch("app.services.session_pipeline_service.build_rule_engine_shadow_payload")
    def test_diagnostic_run_cannot_claim_official_score_authority(self, build_payload):
        build_payload.return_value = {
            "scoreAuthority": "structured_rule_engine",
            "scorePolicyVersion": "score-policy-v2-single-attribution",
            "finalScore": 55.0,
            "ruleEngineScore": 55.0,
            "observations": [],
            "deductions": [],
            "diagnosticDeductions": [],
            "lossLedger": [],
            "reconciliation": {"finalScore": 55.0, "ruleMaxScore": 100.0, "totalLoss": 45.0},
        }
        binding = {
            "trackName": "商贸赛道",
            "selectionSource": "diagnostic_override",
            "bindingStatus": "diagnostic_assumption",
            "publicationMode": "diagnostic",
        }
        pipeline_result = {
            "ai_score": {"overall_score": 70.0, "dimensions": {}},
            "evidence_extraction": {"ruleHash": "rule-hash"},
            "competition_binding": binding,
            "publish_official_score": False,
            "asr": {"transcript": "test", "segments": []},
        }

        final_result = _build_final_result(pipeline_result)

        self.assertEqual(final_result["scoreAuthority"], "diagnostic_rule_engine")
        self.assertFalse(final_result["publishOfficialScore"])
        self.assertEqual(final_result["competitionBinding"], binding)
        self.assertEqual(final_result["overallScore"], 55.0)

    @patch("app.services.session_pipeline_service.build_rule_engine_shadow_payload")
    def test_unpublishable_extraction_never_falls_back_to_llm_score(self, build_payload):
        pipeline_result = {
            "ai_score": {"overall_score": 69.5, "dimensions": {}},
            "evidence_extraction": {
                "status": "review_required",
                "extractionQuality": {
                    "publicationEligible": False,
                    "matchedObservationCount": 0,
                },
            },
            "asr": {"transcript": "test", "segments": []},
        }

        final_result = _build_final_result(pipeline_result)

        build_payload.assert_not_called()
        self.assertEqual(final_result["scoreAuthority"], "review_required")
        self.assertIsNone(final_result["overallScore"])
        self.assertEqual(final_result["reviewReason"], "evidence_extraction_not_publishable")


if __name__ == "__main__":
    unittest.main()
