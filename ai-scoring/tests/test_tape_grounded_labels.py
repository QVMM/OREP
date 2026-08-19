import json
import unittest
from pathlib import Path

from app.services.scoring.tape_grounded_labels import (
    apply_tape_grounded_labels,
    tokens_for_observation,
    transcript_sha256,
)
from app.services.scoring.rule_executor import execute_rule_score
from app.services.pipeline_payloads import _build_shadow_observations


def _rule():
    return {
        "observations": [
            {
                "observationCode": "O01",
                "observationName": "操作规范性",
                "dimensionCode": "skill_level",
                "maxScore": 10.0,
                "claimTypes": ["系统自研", "流程规范"],
                "requiredInfo": ["核心代码、接口、测试记录、部署方式"],
                "acceptableEvidence": ["架构图", "测试报告", "现场系统运行画面"],
                "evidenceCaps": {"E0": 2.0, "E1": 3.0, "E2": 5.0, "E3": 7.0},
            },
            {
                "observationCode": "O08",
                "observationName": "安全意识",
                "dimensionCode": "professionalism",
                "maxScore": 4.0,
                "requiredInfo": ["权限、日志、脱敏"],
                "acceptableEvidence": ["权限矩阵"],
                "evidenceCaps": {"E0": 0.8, "E1": 1.2, "E2": 2.0, "E3": 2.8},
            },
        ]
    }


def _asr():
    return {
        "transcript": "下面演示核心代码和架构图，接口联调通过，测试报告显示正常，已经部署上线。",
        "segments": [
            {"start": 10, "end": 20, "text": "下面演示核心代码和架构图"},
            {"start": 21, "end": 35, "text": "接口联调通过，测试报告显示正常，已经部署上线"},
        ],
        "duration": 40,
    }


class TapeGroundedLabelsTest(unittest.TestCase):
    def test_same_transcript_same_labels_and_score(self):
        extraction = {
            "observationEvidence": [
                {"observationCode": "O01", "evidenceLevel": "E3", "performanceLevel": "complete"},
                {"observationCode": "O08", "evidenceLevel": "E2", "performanceLevel": "partial"},
            ]
        }
        a = apply_tape_grounded_labels(extraction, _asr(), _rule())
        b = apply_tape_grounded_labels(extraction, _asr(), _rule())
        self.assertEqual(
            [(i["evidenceLevel"], i["performanceLevel"], i["suggestedBaseScore"]) for i in a["observationEvidence"]],
            [(i["evidenceLevel"], i["performanceLevel"], i["suggestedBaseScore"]) for i in b["observationEvidence"]],
        )
        self.assertEqual(transcript_sha256(_asr()), transcript_sha256(_asr()))
        o01 = a["observationEvidence"][0]
        self.assertEqual(o01["llmEvidenceLevel"], "E3")
        self.assertIn(o01["evidenceLevel"], {"E2", "E3"})
        self.assertGreater(o01["suggestedBaseScore"], 0)

    def test_missing_topic_stays_e0(self):
        extraction = {
            "observationEvidence": [
                {"observationCode": "O08", "evidenceLevel": "E3", "performanceLevel": "complete"},
            ]
        }
        stamped = apply_tape_grounded_labels(extraction, _asr(), _rule())
        o08 = stamped["observationEvidence"][0]
        self.assertEqual(o08["evidenceLevel"], "E0")
        self.assertEqual(o08["llmEvidenceLevel"], "E3")

    def test_real_cached_transcript_is_stable_across_copies(self):
        result_path = Path("/Users/liuyixing/项目/OREP/ai-scoring/uploads/results/result_42.json")
        if not result_path.is_file():
            self.skipTest("no live result_42")
        result = json.loads(result_path.read_text(encoding="utf-8"))
        asr = result.get("asr") or {}
        extraction = result.get("evidence_extraction") or {}
        from app.services.pipeline_payloads import _load_shadow_track_rule

        rule = _load_shadow_track_rule(extraction)
        if not rule:
            self.skipTest("no track rule")
        first = apply_tape_grounded_labels(extraction, asr, rule)
        second = apply_tape_grounded_labels(extraction, asr, rule)
        keys = ("observationCode", "evidenceLevel", "performanceLevel", "suggestedBaseScore", "suggestedScoreCap")
        self.assertEqual(
            [{k: row.get(k) for k in keys} for row in first["observationEvidence"]],
            [{k: row.get(k) for k in keys} for row in second["observationEvidence"]],
        )
        rules = {item.get("observationCode"): item for item in rule.get("observations") or []}
        obs = _build_shadow_observations(first["observationEvidence"], rules, {})
        score_a = execute_rule_score(obs, []).get("finalScore")
        obs_b = _build_shadow_observations(second["observationEvidence"], rules, {})
        score_b = execute_rule_score(obs_b, []).get("finalScore")
        self.assertEqual(score_a, score_b)

    def test_tokens_split_required_info(self):
        tokens = tokens_for_observation({
            "observationName": "操作规范性",
            "requiredInfo": ["核心代码、接口、测试记录"],
            "acceptableEvidence": ["架构图"],
        })
        self.assertIn("核心代码", tokens)
        self.assertIn("架构图", tokens)


if __name__ == "__main__":
    unittest.main()
