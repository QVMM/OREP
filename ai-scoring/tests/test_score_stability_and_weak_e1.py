"""弱信号升 E1 + 跨场次稳定钳制。"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from app.services.evidence_extraction_service import (
    extract_evidence_from_llm_payload,
    load_pilot_track_rule,
)
from app.services.scoring.score_stability_service import (
    apply_cross_session_stability,
    build_media_fingerprint,
    fingerprints_match,
    resolve_prior_dimension_scores,
)
from app.services.scoring.rule_executor import execute_rule_score


class WeakSignalE1Tests(unittest.TestCase):
    def test_weak_signal_creates_synthetic_evidence_and_upgrades_to_e1(self):
        rule = load_pilot_track_rule("新一代信息技术赛道")
        payload = json.dumps(
            {
                "claims": [],
                "evidenceItems": [],
                "observationEvidence": [
                    {
                        "observationCode": "O12",
                        "evidenceIds": [],
                        "evidenceLevel": "E0",
                        "performanceLevel": "not_demonstrated",
                        "performanceReason": "团队口头介绍了模块分工和各自负责部分。",
                        "evidenceReason": "未展示看板，但提到了分工。",
                    }
                ],
                "deductionCandidates": [],
                "recoveryCandidates": [],
                "riskFlags": [],
                "extractionQuality": {},
            },
            ensure_ascii=False,
        )
        extraction = extract_evidence_from_llm_payload(payload, rule)
        row = next(i for i in extraction["observationEvidence"] if i["observationCode"] == "O12")
        self.assertEqual(row["evidenceLevel"], "E1")
        self.assertTrue(row["evidenceIds"])
        self.assertTrue(any(str(e).startswith("sys-weak-") for e in row["evidenceIds"]))
        # E1 绝对帽 1.5；partial 表现 2.5 → final 受帽 1.5
        self.assertEqual(row["suggestedScoreCap"], 1.5)
        self.assertGreaterEqual(row["suggestedBaseScore"], 1.5)
        self.assertIn("weak_signal", row.get("performanceAssessmentStatus") or "")
        # 合成证据进入库存
        self.assertTrue(
            any(e.get("synthetic") for e in extraction["evidenceItems"] if isinstance(e, dict))
        )

    def test_weak_signal_prefers_inventory_match(self):
        rule = load_pilot_track_rule("新一代信息技术赛道")
        payload = json.dumps(
            {
                "claims": [],
                "evidenceItems": [
                    {
                        "evidenceId": "team-board-1",
                        "sourceType": "transcript",
                        "sourceRef": "transcript@03:00",
                        "text": "我们展示了任务看板和成员分工表。",
                        "confidence": 0.7,
                    }
                ],
                "observationEvidence": [
                    {
                        "observationCode": "O12",
                        "evidenceIds": [],
                        "evidenceLevel": "E0",
                        "performanceReason": "提到了分工协作。",
                    }
                ],
                "deductionCandidates": [],
                "recoveryCandidates": [],
                "riskFlags": [],
                "extractionQuality": {},
            },
            ensure_ascii=False,
        )
        extraction = extract_evidence_from_llm_payload(payload, rule)
        row = next(i for i in extraction["observationEvidence"] if i["observationCode"] == "O12")
        self.assertEqual(row["evidenceLevel"], "E1")
        self.assertIn("team-board-1", row["evidenceIds"])
        self.assertFalse(any(str(e).startswith("sys-weak-") for e in row["evidenceIds"]))


class StabilityClampTests(unittest.TestCase):
    def test_fingerprint_match(self):
        a = {"asr_duration": 3270.6, "frame_count": 110, "track": "新一代信息技术赛道", "team_size": 4}
        b = {"asr_duration": 3270.5, "frame_count": 110, "track": "新一代信息技术赛道", "team_size": 4}
        self.assertTrue(fingerprints_match(a, b))
        c = {**b, "frame_count": 99}
        self.assertFalse(fingerprints_match(a, c))

    def test_clamp_dimension_within_delta(self):
        auth = {
            "scoreAuthority": "structured_rule_engine",
            "finalScore": 20.0,
            "baseScore": 20.0,
            "performanceGap": 0,
            "evidenceLimitedGap": 0,
            "deductedScore": 0,
            "recoveredScore": 0,
            "effectiveHardPenalty": 0,
            "currentScoreCap": 20,
            "dimensionScores": {
                "skill_level": 10.0,
                "professionalism": 0.0,
                "teamwork": 0.0,
            },
            "dimensionMaxScores": {
                "skill_level": 60.0,
                "professionalism": 10.0,
                "teamwork": 10.0,
            },
            "reconciliation": {"finalScore": 20.0},
            "observations": [
                {
                    "observationCode": "O06",
                    "dimensionCode": "professionalism",
                    "maxScore": 4.0,
                    "baseScore": 0.0,
                    "scoreCap": 0.8,
                    "finalScore": 0.0,
                },
                {
                    "observationCode": "O12",
                    "dimensionCode": "teamwork",
                    "maxScore": 5.0,
                    "baseScore": 0.0,
                    "scoreCap": 1.0,
                    "finalScore": 0.0,
                },
                {
                    "observationCode": "O01",
                    "dimensionCode": "skill_level",
                    "maxScore": 10.0,
                    "baseScore": 10.0,
                    "scoreCap": 10.0,
                    "finalScore": 10.0,
                },
            ],
            "lossLedger": [],
        }
        result = {
            "meeting_id": "41",
            "prior_scoring_snapshot": {
                "dimensions": {
                    "skill_level": 24.0,
                    "professionalism": 1.8,
                    "teamwork": 1.5,
                },
                "overall": 36.8,
            },
        }
        out = apply_cross_session_stability(auth, result, dim_max_delta=1.5, overall_max_delta=5.0)
        # skill 10 相对 prior 24 → 抬到 24-1.5=22.5
        self.assertAlmostEqual(out["dimensionScores"]["skill_level"], 22.5, places=1)
        # profession 0 相对 1.8 → 抬到 0.3
        self.assertAlmostEqual(out["dimensionScores"]["professionalism"], 0.3, places=1)
        # team 0 相对 1.5 → 0.0  (1.5-1.5=0)
        self.assertAlmostEqual(out["dimensionScores"]["teamwork"], 0.0, places=1)
        self.assertIn("_stability_clamp", out)

    def test_resolve_prior_from_disk(self):
        # 用本地 fixtures 目录模拟：写入两个临时 result
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as td:
            results = Path(td) / "results"
            results.mkdir()
            prior = {
                "meeting_id": "40",
                "asr": {"duration": 1000.0},
                "video_analysis": {"frame_count": 50},
                "project_info": {"track": "IT", "team_size": 3},
                "ai_score": {
                    "overall_score": 40.0,
                    "dimensions": {
                        "skill_level": {"score": 30.0},
                        "professionalism": {"score": 2.0},
                    },
                },
            }
            current = {
                "meeting_id": "41",
                "asr": {"duration": 1000.0},
                "video_analysis": {"frame_count": 50},
                "project_info": {"track": "IT", "team_size": 3},
                "ai_score": {"overall_score": 10.0, "dimensions": {}},
            }
            (results / "result_40.json").write_text(json.dumps(prior), encoding="utf-8")
            snap = resolve_prior_dimension_scores(current, upload_dir=td)
            self.assertIsNotNone(snap)
            self.assertEqual(snap["dimensions"]["skill_level"], 30.0)
            self.assertEqual(str(snap["meeting_id"]), "40")


if __name__ == "__main__":
    unittest.main()
