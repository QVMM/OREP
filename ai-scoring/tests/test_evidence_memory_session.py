import json
import unittest

from unittest.mock import patch

from app.services.scoring.evidence_memory_session import (
    build_report_memory_pack,
    extract_with_memory_session,
    is_extraction_incomplete,
    is_scan_incomplete,
    should_use_memory_session,
    _build_time_windows,
    _json_call_with_retry,
    _merge_scan_into_memory,
    _new_memory,
    _observation_catalog,
    _should_retry_scan,
    _synthesize_prompt,
)


class EvidenceMemorySessionTest(unittest.TestCase):
    def test_long_roadshow_triggers_memory_session(self):
        asr = {
            "duration": 3270,
            "segments": [{"start": i * 10, "end": i * 10 + 8, "text": f"内容{i}"} for i in range(120)],
        }
        self.assertTrue(should_use_memory_session(asr))
        self.assertFalse(should_use_memory_session({"duration": 120, "segments": [{"text": "短"}]}))

    def test_windows_cover_start_and_end_without_full_dump(self):
        asr = {
            "duration": 3270,
            "segments": [
                {"start": i * 30, "end": i * 30 + 20, "text": ("开场" if i == 0 else "结尾" if i > 100 else "中段") + f"-{i}-" + ("详" * 20)}
                for i in range(110)
            ],
        }
        windows = _build_time_windows(asr, {"timeline": []})
        self.assertGreaterEqual(len(windows), 3)
        self.assertLessEqual(len(windows), 8)
        joined = "\n".join(w["transcript"] for w in windows)
        self.assertIn("开场", joined)
        self.assertIn("结尾", joined)
        # Each window is capped; total raw window text stays far below full dump.
        self.assertLess(sum(len(w["transcript"]) for w in windows), 3500 * 8)

    def test_merge_scan_updates_running_summary_and_notes(self):
        track_rule = {
            "observations": [
                {"observationCode": "O01", "observationName": "操作规范性"},
                {"observationCode": "O02", "observationName": "技能熟练度"},
            ]
        }
        windows = [{"windowId": "W1", "timeRange": "00:00-10:00", "startSec": 0, "endSec": 600}]
        memory = _new_memory(track_rule, windows)
        _merge_scan_into_memory(
            memory,
            {
                "windowSummary": "团队完成环境监测演示",
                "claims": [{"text": "我们完成了现场演示"}],
                "evidenceItems": [{
                    "sourceRef": "transcript@05:00",
                    "text": "现在开始演示智能排风",
                    "sourceType": "transcript",
                }],
                "observationSignals": [{
                    "observationCode": "O02",
                    "signal": "现场操作流畅",
                    "suggestedEvidenceLevel": "E3",
                    "suggestedPerformanceLevel": "substantial",
                    "quote": "智能排风已启动",
                }],
            },
            windows[0],
        )
        self.assertIn("环境监测演示", memory["runningSummary"])
        self.assertEqual(len(memory["evidenceItems"]), 1)
        self.assertEqual(memory["observationNotes"]["O02"]["bestEvidenceLevel"], "E3")
        self.assertEqual(memory["observationNotes"]["O02"]["bestPerformanceLevel"], "substantial")

    def test_report_memory_pack_is_compact(self):
        pack = build_report_memory_pack(
            rule_payload={
                "finalScore": 62,
                "performanceGap": 30,
                "evidenceLimitedGap": 8,
                "effectiveHardPenalty": 0,
                "dimensionScores": {"skill": 40},
                "observations": [{"observationCode": "O01", "finalScore": 6, "maxScore": 10}],
                "lossLedger": [{"observationCode": "O01", "points": 4, "lossType": "performance_gap", "reason": "演示不完整"}],
            },
            evidence_extraction={
                "sessionMemory": {"runningSummary": "开场清楚，中段演示，结尾致谢"},
                "evidenceItems": [{"evidenceId": "E1", "sourceRef": "transcript@01:00", "text": "大家好"}],
            },
            asr_result={"segments": [{"text": "x"}]},
        )
        encoded = json.dumps(pack, ensure_ascii=False)
        self.assertIn("开场清楚", encoded)
        self.assertLess(len(encoded), 5000)

    def test_two_failed_windows_mark_extraction_incomplete(self):
        self.assertTrue(is_scan_incomplete(6, 2))
        self.assertFalse(is_scan_incomplete(6, 1))
        self.assertTrue(is_scan_incomplete(1, 1))
        self.assertTrue(is_extraction_incomplete({
            "extractionQuality": {"incomplete": True, "scanFailureCount": 2, "windowCount": 6}
        }))

    def test_truncation_retries_once_with_higher_tokens(self):
        calls = []

        def fake_json_call(**kwargs):
            calls.append(kwargs["max_tokens"])
            if len(calls) == 1:
                return None, {"stage": kwargs["stage"], "error": "Unterminated string", "finish_reason": "length", "truncated": True, "attempt": 1}
            return {"windowSummary": "ok"}, {"stage": kwargs["stage"], "attempt": 2, "error": None}

        with patch(
            "app.services.scoring.evidence_memory_session._json_call",
            side_effect=lambda **kwargs: fake_json_call(**kwargs),
        ):
            payload, metas = _json_call_with_retry(
                client=None,
                model_name="x",
                system="s",
                user="u",
                max_tokens=2500,
                retry_tokens=4000,
                timeout=10,
                stage="memory_scan_1",
            )
        self.assertEqual(payload["windowSummary"], "ok")
        self.assertEqual(calls, [2500, 4000])
        self.assertEqual(len(metas), 2)
        self.assertTrue(_should_retry_scan({"finish_reason": "length"}))

    def test_synth_prompt_forbids_neighbor_window_invention(self):
        prompt = _synthesize_prompt(
            [{"observationCode": "O01", "observationName": "操作规范性"}],
            {"runningSummary": "中段演示", "evidenceItems": [], "observationNotes": {}},
            failed_windows=[{"windowId": "W1", "timeRange": "00:00-09:05"}],
        )
        self.assertIn("失败窗", prompt)
        self.assertIn("00:00-09:05", prompt)
        self.assertIn("禁止用邻窗推断", prompt)

    def test_extract_marks_incomplete_when_scans_fail(self):
        asr = {
            "duration": 3270,
            "segments": [{"start": i * 30, "end": i * 30 + 20, "text": f"内容{i}" * 8} for i in range(110)],
        }
        track_rule = {
            "trackId": "it",
            "trackName": "新一代信息技术赛道",
            "ruleVersion": "v1.2",
            "ruleHash": "sha256:x",
            "observations": [
                {"observationCode": "O01", "observationName": "操作规范性", "dimensionCode": "skill_level"},
            ],
        }

        def always_fail(**kwargs):
            return None, {
                "stage": kwargs["stage"],
                "attempt": 1,
                "error": "Expecting ',' delimiter",
                "finish_reason": "length",
                "truncated": True,
            }

        with patch(
            "app.services.scoring.evidence_memory_session._json_call",
            side_effect=lambda **kwargs: always_fail(**kwargs),
        ):
            extraction = extract_with_memory_session(
                client=None,
                model_name="deepseek-v4-pro",
                track_rule=track_rule,
                asr_result=asr,
            )
        quality = extraction["extractionQuality"]
        self.assertGreaterEqual(quality["scanFailureCount"], 2)
        self.assertTrue(quality["incomplete"])
        self.assertFalse(quality["publicationEligible"])
        self.assertTrue(is_extraction_incomplete(extraction))


if __name__ == "__main__":
    unittest.main()
