import json
from pathlib import Path

import app.services.evidence_extraction_service as evidence_extraction_service
import app.services.pipeline_service as pipeline_service
from app.services.evidence_extraction_service import (
    _rule_file_index,
    extract_evidence,
    extract_evidence_from_llm_payload,
    load_pilot_track_rule,
    rubrics_dir,
)


def test_loads_pilot_rules_for_first_two_tracks():
    ai_rule = load_pilot_track_rule("人工智能赛道")
    it_rule = load_pilot_track_rule("新一代信息技术赛道")

    assert ai_rule["trackName"] == "人工智能赛道"
    assert it_rule["trackName"] == "新一代信息技术赛道"
    assert len(ai_rule["observations"]) == 15
    assert len(it_rule["observations"]) == 15


def test_rule_index_covers_all_42_tracks_by_id_alias_and_name():
    plan = json.loads((rubrics_dir() / "track_expansion_plan_v1.json").read_text(encoding="utf-8"))
    tracks = [
        track
        for batch in plan.get("batches") or []
        for track in batch.get("tracks") or []
        if track.get("status") in {"pilot_completed", "pilot_generated"}
    ]
    index = _rule_file_index()

    assert len(tracks) == 42
    assert all(str(track["trackId"]) in index for track in tracks)
    assert all(f"track_{track['trackId']}" in index for track in tracks)
    assert all(track["trackName"] in index for track in tracks)
    assert all((Path(index[str(track["trackId"])]).suffix == ".json") for track in tracks)


def test_loads_pilot_generated_rule_for_expanded_commerce_track():
    commerce_rule = load_pilot_track_rule("商贸赛道")

    assert commerce_rule["trackId"] == "33"
    assert commerce_rule["trackName"] == "商贸赛道"
    assert commerce_rule["status"] == "pilot"
    assert commerce_rule["pilotPromotion"]["activeAllowed"] is False
    assert len(commerce_rule["observations"]) == 15


def test_parser_ignores_llm_score_and_fills_all_observations_with_e0():
    rule = load_pilot_track_rule("人工智能赛道")
    payload = json.dumps(
        {
            "overall_score": 99,
            "dimension_scores": {"skill_level": 60},
            "claims": [{"claimId": "c1", "text": "我们使用了AI模型"}],
            "evidenceItems": [],
            "observationEvidence": [
                {
                    "observationCode": "O01",
                    "claimIds": ["c1"],
                    "evidenceIds": [],
                    "evidenceLevel": "E5",
                    "confidence": 0.95,
                    "supportSummary": "模型声称很强，但没有证据锚点",
                }
            ],
            "deductionCandidates": [],
            "recoveryCandidates": [],
            "riskFlags": [],
            "extractionQuality": {"jsonParseable": True},
        },
        ensure_ascii=False,
    )

    extraction = extract_evidence_from_llm_payload(payload, rule)

    assert "overall_score" not in extraction
    assert "dimension_scores" not in extraction
    assert extraction["status"] == "review_required"
    assert extraction["extractionQuality"]["modelObservationCount"] == 1
    assert extraction["extractionQuality"]["matchedObservationCount"] == 1
    assert extraction["extractionQuality"]["publicationEligible"] is False
    assert len(extraction["observationEvidence"]) == 15
    by_code = {item["observationCode"]: item for item in extraction["observationEvidence"]}
    assert by_code["O01"]["evidenceLevel"] == "E0"
    assert by_code["O01"]["validityStatus"] == "missing_evidence"
    assert by_code["O01"]["evidenceIds"] == []
    assert all(item["evidenceLevel"] == "E0" for code, item in by_code.items() if code != "O01")


def test_parser_preserves_non_e0_when_evidence_is_bound():
    rule = load_pilot_track_rule("新一代信息技术赛道")
    payload = json.dumps(
        {
            "claims": [{"claimId": "c1", "text": "系统已完成部署和测试"}],
            "evidenceItems": [
                {
                    "evidenceId": "e1",
                    "sourceType": "material",
                    "sourceRef": "测试报告.pdf#page=2",
                    "text": "测试报告包含接口、性能和部署记录",
                    "confidence": 0.88,
                }
            ],
            "observationEvidence": [
                {
                    "observationCode": "O01",
                    "claimIds": ["c1"],
                    "evidenceIds": ["e1"],
                    "evidenceLevel": "E3",
                    "confidence": 0.88,
                    "supportSummary": "测试报告可支撑工程流程闭环的一部分",
                }
            ],
            "deductionCandidates": [{"observationCode": "O02", "reason": "缺少现场操作"}],
            "recoveryCandidates": [],
            "riskFlags": [],
            "extractionQuality": {},
        },
        ensure_ascii=False,
    )

    extraction = extract_evidence_from_llm_payload(payload, rule)
    by_code = {item["observationCode"]: item for item in extraction["observationEvidence"]}

    assert extraction["status"] == "review_required"
    assert extraction["extractionQuality"]["modelObservationCount"] == 1
    assert extraction["extractionQuality"]["matchedObservationCount"] == 1
    assert extraction["extractionQuality"]["publicationEligible"] is False
    assert by_code["O01"]["evidenceLevel"] == "E3"
    assert by_code["O01"]["evidenceIds"] == ["e1"]
    assert by_code["O01"]["suggestedScoreCap"] == 7.0
    assert extraction["deductionCandidates"][0]["sourceType"] == "llm_extraction"


def test_parser_blocks_publication_when_e0_observations_bind_evidence():
    rule = load_pilot_track_rule("新一代信息技术赛道")
    payload = json.dumps(
        {
            "claims": [{"claimId": "c1", "text": "团队完成了现场演示"}],
            "evidenceItems": [{
                "evidenceId": "e1",
                "sourceType": "timeline",
                "sourceRef": "timeline@12:30",
                "text": "现场展示系统运行界面和传感器数据",
                "confidence": 0.9,
            }],
            "observationEvidence": [
                {
                    "observationCode": observation["observationCode"],
                    "evidenceIds": ["e1"],
                    "evidenceLevel": "E0",
                    "performanceLevel": "not_demonstrated",
                }
                for observation in rule["observations"]
            ],
            "deductionCandidates": [],
            "recoveryCandidates": [],
            "riskFlags": [],
            "extractionQuality": {},
        },
        ensure_ascii=False,
    )

    extraction = extract_evidence_from_llm_payload(payload, rule)

    assert extraction["status"] == "review_required"
    assert extraction["extractionQuality"]["publicationEligible"] is False
    assert "O01:E0_with_bound_evidence" in extraction["extractionQuality"]["warnings"]


def test_parser_blocks_publication_when_evidence_inventory_is_never_bound():
    rule = load_pilot_track_rule("新一代信息技术赛道")
    payload = json.dumps(
        {
            "claims": [{"claimId": "c1", "text": "团队完成了现场演示"}],
            "evidenceItems": [{
                "evidenceId": "e1",
                "sourceType": "timeline",
                "sourceRef": "timeline@12:30",
                "text": "现场展示系统运行界面和传感器数据",
            }],
            "observationEvidence": [
                {
                    "observationCode": observation["observationCode"],
                    "claimIds": [],
                    "evidenceIds": [],
                    "evidenceLevel": "E0",
                    "performanceLevel": "not_demonstrated",
                }
                for observation in rule["observations"]
            ],
            "deductionCandidates": [],
            "recoveryCandidates": [],
            "riskFlags": [],
            "extractionQuality": {},
        },
        ensure_ascii=False,
    )

    extraction = extract_evidence_from_llm_payload(payload, rule)

    assert extraction["status"] == "review_required"
    assert extraction["extractionQuality"]["publicationEligible"] is False
    assert "evidence_inventory_unbound" in extraction["extractionQuality"]["warnings"]


def test_parser_downgrades_e3_when_internal_quantitative_condition_is_missing():
    rule = load_pilot_track_rule("商贸赛道")
    observation_code = rule["observations"][0]["observationCode"]
    payload = json.dumps(
        {
            "claims": [{"claimId": "c1", "text": "我们说明了运营流程"}],
            "evidenceItems": [
                {
                    "evidenceId": "e1",
                    "sourceType": "transcript",
                    "sourceRef": "timeline@05:00",
                    "text": "团队说明了选品、内容制作和渠道运营流程，但没有展示数据、指标或测算。",
                    "confidence": 0.82,
                }
            ],
            "observationEvidence": [
                {
                    "observationCode": observation_code,
                    "claimIds": ["c1"],
                    "evidenceIds": ["e1"],
                    "evidenceLevel": "E3",
                    "confidence": 0.82,
                    "supportSummary": "有流程解释，但缺少内部量化证据。",
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
    by_code = {item["observationCode"]: item for item in extraction["observationEvidence"]}

    assert by_code[observation_code]["evidenceLevel"] == "E2"
    # 比例帽解析为绝对分：E2=0.5 * maxScore
    max_score = float(by_code[observation_code]["maxScore"] or 0)
    assert by_code[observation_code]["suggestedScoreCap"] == round(0.5 * max_score, 2)
    assert by_code[observation_code]["scoreCapUnit"] == "points"
    assert f"{observation_code}:E3_downgraded_missing_internal_quantitative_evidence" in extraction["extractionQuality"]["warnings"]


def test_parser_rechecks_e3_condition_after_e4_downgrade():
    rule = load_pilot_track_rule("商贸赛道")
    observation_code = rule["observations"][0]["observationCode"]
    payload = json.dumps(
        {
            "claims": [{"claimId": "c1", "text": "我们说明了渠道运营流程"}],
            "evidenceItems": [
                {
                    "evidenceId": "e1",
                    "sourceType": "transcript",
                    "sourceRef": "timeline@06:00",
                    "text": "团队说明了渠道运营流程和内容规划。",
                }
            ],
            "observationEvidence": [
                {
                    "observationCode": observation_code,
                    "claimIds": ["c1"],
                    "evidenceIds": ["e1"],
                    "evidenceLevel": "E4",
                    "supportSummary": "有流程说明，但没有场景验证或量化数据。",
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
    by_code = {item["observationCode"]: item for item in extraction["observationEvidence"]}

    assert by_code[observation_code]["evidenceLevel"] == "E2"
    assert f"{observation_code}:E4_downgraded_missing_scene_validation" in extraction["extractionQuality"]["warnings"]
    assert f"{observation_code}:E3_downgraded_missing_internal_quantitative_evidence" in extraction["extractionQuality"]["warnings"]


def test_parser_downgrades_fake_e5_without_independent_verification():
    rule = load_pilot_track_rule("商贸赛道")
    observation_code = rule["observations"][0]["observationCode"]
    payload = json.dumps(
        {
            "claims": [{"claimId": "c1", "text": "我们很领先"}],
            "evidenceItems": [
                {
                    "evidenceId": "e1",
                    "sourceType": "transcript",
                    "sourceRef": "transcript@01:00",
                    "text": "团队口头表示方案先进、规范、已经落地。",
                }
            ],
            "observationEvidence": [
                {
                    "observationCode": observation_code,
                    "claimIds": ["c1"],
                    "evidenceIds": ["e1"],
                    "evidenceLevel": "E5",
                    "supportSummary": "模型自称达到独立可核验水平。",
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
    by_code = {item["observationCode"]: item for item in extraction["observationEvidence"]}
    warnings = extraction["extractionQuality"]["warnings"]

    assert by_code[observation_code]["evidenceLevel"] == "E2"
    assert f"{observation_code}:E5_downgraded_missing_independent_verification" in warnings
    assert f"{observation_code}:E4_downgraded_missing_scene_validation" in warnings
    assert f"{observation_code}:E3_downgraded_missing_internal_quantitative_evidence" in warnings


def test_parser_rejects_empty_evidence_item_for_non_e0_observation():
    rule = load_pilot_track_rule("商贸赛道")
    observation_code = rule["observations"][0]["observationCode"]
    payload = json.dumps(
        {
            "claims": [],
            "evidenceItems": [{"evidenceId": "empty-evidence", "text": "", "sourceRef": ""}],
            "observationEvidence": [
                {
                    "observationCode": observation_code,
                    "evidenceIds": ["empty-evidence"],
                    "evidenceLevel": "E3",
                    "confidence": 0.8,
                    "supportSummary": "只有空证据ID，不能支撑非E0",
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
    by_code = {item["observationCode"]: item for item in extraction["observationEvidence"]}

    assert by_code[observation_code]["evidenceLevel"] == "E0"
    assert by_code[observation_code]["evidenceIds"] == []
    assert by_code[observation_code]["validityStatus"] == "missing_evidence"
    assert f"{observation_code}:non_e0_without_evidence" in extraction["extractionQuality"]["warnings"]


def test_e0_missing_evidence_applies_floor_not_zero_for_professionalism_and_teamwork():
    """缺证非红线：职业/团队观测点应按 E0 帽给地板分，而不是 0。"""
    rule = load_pilot_track_rule("新一代信息技术赛道")
    payload = json.dumps(
        {
            "claims": [],
            "evidenceItems": [],
            "observationEvidence": [
                {
                    "observationCode": code,
                    "evidenceIds": [],
                    "evidenceLevel": "E0",
                    "performanceLevel": "not_demonstrated",
                    "confidence": 0.9,
                    "performanceReason": "会话中未展示相关材料。",
                    "evidenceReason": "当前无可核验证据",
                }
                for code in ("O06", "O07", "O08", "O12", "O13")
            ],
            "deductionCandidates": [],
            "recoveryCandidates": [],
            "riskFlags": [],
            "extractionQuality": {},
        },
        ensure_ascii=False,
    )

    extraction = extract_evidence_from_llm_payload(payload, rule)
    by_code = {item["observationCode"]: item for item in extraction["observationEvidence"]}

    # absolute E0 caps on IT pilot
    expected = {"O06": 0.8, "O07": 0.6, "O08": 0.6, "O12": 1.0, "O13": 1.0}
    for code, floor in expected.items():
        row = by_code[code]
        assert row["evidenceLevel"] == "E0"
        assert row["scoreCapUnit"] == "points"
        assert row["suggestedScoreCap"] == floor
        assert row["suggestedBaseScore"] == floor
        assert row["performanceAssessmentStatus"] == "e0_missing_evidence_floor"
        assert f"{code}:e0_missing_evidence_floor" in extraction["extractionQuality"]["warnings"]

    # 经 rule shadow 后维度分应约为 2.0 + 2.0，而非 0
    from app.services.pipeline_payloads import build_rule_engine_shadow_payload

    shadow = build_rule_engine_shadow_payload(
        {
            "ai_score": {"overall_score": 0},
            "evidence_extraction": extraction,
        }
    )
    dims = shadow["dimensionScores"]
    assert abs(dims.get("professionalism", 0) - 2.0) < 1e-6
    assert abs(dims.get("teamwork", 0) - 2.0) < 1e-6


def test_hard_redline_still_allows_zero_on_e0():
    rule = load_pilot_track_rule("新一代信息技术赛道")
    payload = json.dumps(
        {
            "claims": [],
            "evidenceItems": [],
            "observationEvidence": [
                {
                    "observationCode": "O06",
                    "evidenceIds": [],
                    "evidenceLevel": "E0",
                    "performanceLevel": "not_demonstrated",
                    "confidence": 0.95,
                    "performanceReason": "出现明确侵权与伪造成果，触及诚信红线。",
                    "evidenceReason": "红线行为",
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
    row = next(i for i in extraction["observationEvidence"] if i["observationCode"] == "O06")
    assert row["suggestedBaseScore"] == 0.0
    assert row["performanceAssessmentStatus"] == "hard_redline_zero"


def test_weak_system_memory_reason_is_rewritten():
    rule = load_pilot_track_rule("新一代信息技术赛道")
    payload = json.dumps(
        {
            "claims": [],
            "evidenceItems": [],
            "observationEvidence": [
                {
                    "observationCode": "O07",
                    "evidenceIds": [],
                    "evidenceLevel": "E0",
                    "performanceLevel": "not_demonstrated",
                    "evidenceReason": "本轮记忆中证据有限",
                    "performanceReason": "本轮记忆中证据有限",
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
    row = next(i for i in extraction["observationEvidence"] if i["observationCode"] == "O07")
    assert "记忆中证据有限" not in (row.get("evidenceReason") or "")
    assert row["suggestedBaseScore"] == 0.6


def test_prompt_includes_compact_fusion_timeline_for_source_refs():
    rule = load_pilot_track_rule("商贸赛道")
    prompt = evidence_extraction_service.build_extraction_prompt(
        rule,
        {"transcript": "团队展示了化妆刷产品。"},
        {
            "timeline": [
                {
                    "time_min": 0.5,
                    "visual_impression": "团队通过实物演示与肢体语言增强说服力",
                    "text_preview": "我们展示文港化妆刷的用户价值",
                    "scene_type": "演示",
                }
            ],
            "screen_content_summary": {"visible_texts": ["文港化妆刷"]},
        },
    )

    assert "timeline@00:30" in prompt
    assert "团队通过实物演示" in prompt
    assert "evidenceItems 必须填写 sourceRef 和 text" in prompt
    assert "E0不得绑定evidenceIds" in prompt


def test_transcript_coverage_keeps_opening_and_closing_for_long_roadshow():
    segments = []
    for minute in range(0, 60):
        marker = "开场重点" if minute == 0 else "结尾总结" if minute == 59 else "中段讲解"
        segments.append({
            "start": minute * 60,
            "end": minute * 60 + 50,
            "text": f"第{minute}分钟内容-{marker}-" + ("详" * 400),
        })
    asr = {"segments": segments, "transcript": "ignored-when-segments-present"}

    coverage = evidence_extraction_service.build_transcript_coverage(
        asr,
        max_total_chars=8000,
        max_part_chars=2500,
        max_parts=4,
    )
    # Force the prompt path to use the same tight budget by temporarily packing
    # a pre-built long transcript that already exceeds the default part threshold.
    packed_asr = {
        "transcript": coverage["text"],
        "segments": segments,
    }
    # Direct unit check on coverage packing.
    assert coverage["coverageMode"] == "time_bucket_parts"
    assert len(coverage["parts"]) >= 2
    assert "开场重点" in coverage["text"]
    assert "结尾总结" in coverage["text"]
    assert "转写分段" in coverage["text"]

    # Prompt uses live coverage builder; with default large budget a 60-min dense
    # transcript still becomes multi-part under the default part size.
    default_coverage = evidence_extraction_service.build_transcript_coverage(asr)
    prompt = evidence_extraction_service.build_extraction_prompt(
        load_pilot_track_rule("人工智能赛道"),
        asr,
    )
    assert "开场重点" in prompt
    assert "结尾总结" in prompt
    if default_coverage["coverageMode"] == "time_bucket_parts":
        assert "禁止只依据第一段判断" in prompt
    # packed multi-part text itself is what production injects when over budget
    assert "开场重点" in packed_asr["transcript"]
    assert "结尾总结" in packed_asr["transcript"]


def test_short_transcript_stays_single_full_block():
    asr = {
        "segments": [
            {"start": 0, "end": 3, "text": "大家好，我是一号选手。"},
            {"start": 4, "end": 8, "text": "下面介绍项目方案。"},
        ]
    }
    coverage = evidence_extraction_service.build_transcript_coverage(asr)
    assert coverage["coverageMode"] == "full_timestamped"
    assert coverage["parts"][0]["timeRange"] == "full"
    assert "大家好，我是一号选手" in coverage["text"]
    assert "下面介绍项目方案" in coverage["text"]


def test_prompt_uses_core_reasons_only_as_evidence_location_hints():
    rule = load_pilot_track_rule("新一代信息技术赛道")
    prompt = evidence_extraction_service.build_extraction_prompt(
        rule,
        {"transcript": "团队展示了系统运行。"},
        scoring_context={
            "dimensions": {
                "skill_level": {
                    "items": [{
                        "name": "操作规范性",
                        "score": 8.5,
                        "reason": "12:30画面展示测试报告",
                        "improvement": "补充附件",
                    }]
                }
            }
        },
    )

    assert "候选证据定位线索" in prompt
    assert "12:30画面展示测试报告" in prompt
    assert '"score": 8.5' not in prompt
    assert "必须回到转写或timeline核验" in prompt


def test_invalid_json_returns_failed_extraction_without_fake_report_quality():
    rule = load_pilot_track_rule("人工智能赛道")

    extraction = extract_evidence_from_llm_payload("不是JSON", rule)

    assert extraction["status"] == "failed"
    assert extraction["observationEvidence"] == []
    assert extraction["extractionQuality"]["jsonParseable"] is False


def test_pipeline_retries_once_when_observation_contract_is_not_publishable(monkeypatch):
    responses = iter([
        {
            "status": "review_required",
            "extractionQuality": {"publicationEligible": False, "matchedObservationCount": 0},
        },
        {
            "status": "completed",
            "extractionQuality": {"publicationEligible": True, "matchedObservationCount": 15},
        },
    ])
    calls = []

    def fake_extract(**kwargs):
        calls.append(kwargs)
        return next(responses)

    monkeypatch.setattr(evidence_extraction_service, "extract_evidence", fake_extract)
    result = {"meeting_id": "test"}

    pipeline_service._attach_evidence_extraction(
        result,
        {"transcript": "test"},
        {"track": "商贸赛道"},
        {"timeline": []},
        "deepseek",
    )

    assert len(calls) == 2
    assert result["evidence_extraction"]["status"] == "completed"
    assert result["evidence_extraction"]["extractionQuality"]["retryCount"] == 1


def test_pipeline_retries_once_when_extraction_json_parse_fails(monkeypatch):
    responses = iter([
        {
            "status": "failed",
            "observationEvidence": [],
            "extractionQuality": {
                "jsonParseable": False,
                "error": "Expecting ',' delimiter: line 159 column 6 (char 4710)",
            },
            "riskFlags": [{"code": "json_parse_failed", "message": "truncated", "sourceType": "system"}],
        },
        {
            "status": "completed",
            "extractionQuality": {
                "jsonParseable": True,
                "publicationEligible": True,
                "matchedObservationCount": 15,
            },
        },
    ])
    calls = []

    def fake_extract(**kwargs):
        calls.append(kwargs)
        return next(responses)

    monkeypatch.setattr(evidence_extraction_service, "extract_evidence", fake_extract)
    result = {"meeting_id": "session-34"}

    pipeline_service._attach_evidence_extraction(
        result,
        {"transcript": "test"},
        {"track": "新一代信息技术赛道"},
        {"timeline": []},
        "deepseek",
    )

    assert len(calls) == 2
    assert result["evidence_extraction"]["status"] == "completed"
    assert result["evidence_extraction"]["extractionQuality"]["retryCount"] == 1


def test_extract_evidence_falls_back_to_observation_batches_when_single_shot_truncates(monkeypatch):
    rule = load_pilot_track_rule("新一代信息技术赛道")
    observation_codes = [item["observationCode"] for item in rule["observations"]]
    assert len(observation_codes) == 15
    calls = []

    def batch_payload(codes):
        return json.dumps(
            {
                "claims": [],
                "evidenceItems": [
                    {
                        "evidenceId": f"E-{code}",
                        "sourceRef": "transcript@01:00",
                        "text": f"{code} 相关证据",
                        "sourceType": "transcript",
                        "confidence": 0.8,
                    }
                    for code in codes
                ],
                "observationEvidence": [
                    {
                        "observationCode": code,
                        "evidenceLevel": "E2",
                        "evidenceIds": [f"E-{code}"],
                        "performanceLevel": "partial",
                        "performanceReason": "有部分可观察证据",
                        "confidence": 0.7,
                    }
                    for code in codes
                ],
                "deductionCandidates": [],
                "recoveryCandidates": [],
                "riskFlags": [],
                "extractionQuality": {"jsonParseable": True},
            },
            ensure_ascii=False,
        )

    class FakeMessage:
        def __init__(self, content):
            self.content = content

    class FakeChoice:
        def __init__(self, content, finish_reason):
            self.message = FakeMessage(content)
            self.finish_reason = finish_reason

    class FakeUsage:
        def __init__(self, completion_tokens):
            self.prompt_tokens = 36000
            self.completion_tokens = completion_tokens
            self.total_tokens = 36000 + completion_tokens

    class FakeCompletions:
        @staticmethod
        def create(**kwargs):
            calls.append(kwargs)
            user_content = kwargs["messages"][-1]["content"]
            # First call is the full single-shot request and gets truncated.
            if "分批范围" not in user_content:
                return type(
                    "FakeResponse",
                    (),
                    {
                        "choices": [FakeChoice('{"claims":[{"id":1}', "length")],
                        "usage": FakeUsage(12000),
                    },
                )()
            # Later calls are observation batches.
            batch_codes = [code for code in observation_codes if code in user_content]
            # Keep only codes explicitly listed in the batch instruction section.
            marker = "分批观测点："
            listed = []
            if marker in user_content:
                listed_part = user_content.split(marker, 1)[1].split("\n", 1)[0]
                listed = [part.strip() for part in listed_part.split(",") if part.strip()]
            codes = listed or batch_codes[:5]
            return type(
                "FakeResponse",
                (),
                {
                    "choices": [FakeChoice(batch_payload(codes), "stop")],
                    "usage": FakeUsage(900),
                },
            )()

    class FakeChat:
        completions = FakeCompletions()

    class FakeClient:
        chat = FakeChat()

    monkeypatch.setattr(evidence_extraction_service, "load_pilot_track_rule", lambda track: rule)
    monkeypatch.setattr("app.services.llm_scoring_service.get_client", lambda provider: FakeClient())

    extraction = extract_evidence(
        {"transcript": "测试转写"},
        {"track": "新一代信息技术赛道"},
        provider="deepseek",
    )

    # 1 truncated single-shot + 3 batches of 5 observations
    assert len(calls) == 4
    assert all("分批范围" in call["messages"][-1]["content"] or idx == 0 for idx, call in enumerate(calls))
    assert extraction["extractionQuality"]["strategy"] == "observation_batches"
    assert extraction["extractionQuality"]["jsonParseable"] is True
    assert extraction["extractionQuality"].get("retryCount", 0) >= 1
    matched_codes = {
        item.get("observationCode")
        for item in extraction["observationEvidence"]
        if item.get("evidenceLevel") != "E0" or item.get("evidenceIds")
    }
    # All 15 observations should be covered after batch merge.
    assert {item.get("observationCode") for item in extraction["observationEvidence"]} == set(observation_codes)
    assert len(matched_codes) == 15


def test_extract_evidence_falls_back_to_batches_when_model_rejects_single_shot_budget(monkeypatch):
    rule = load_pilot_track_rule("新一代信息技术赛道")
    observation_codes = [item["observationCode"] for item in rule["observations"]]
    calls = []

    class FakeMessage:
        def __init__(self, content):
            self.content = content

    class FakeChoice:
        def __init__(self, content):
            self.message = FakeMessage(content)
            self.finish_reason = "stop"

    class FakeUsage:
        prompt_tokens = 2000
        completion_tokens = 500
        total_tokens = 2500

    class FakeCompletions:
        @staticmethod
        def create(**kwargs):
            calls.append(kwargs)
            user_content = kwargs["messages"][-1]["content"]
            if "分批范围" not in user_content:
                raise ValueError("max_tokens must be less than or equal to 8192")
            listed = user_content.split("分批观测点：", 1)[1].split("\n", 1)[0].split(",")
            payload = json.dumps({
                "claims": [],
                "evidenceItems": [],
                "observationEvidence": [
                    {
                        "observationCode": code,
                        "evidenceLevel": "E0",
                        "evidenceIds": [],
                        "performanceLevel": "not_demonstrated",
                        "performanceReason": "本批未定位到直接证据",
                        "confidence": 0.2,
                    }
                    for code in listed
                ],
                "deductionCandidates": [],
                "recoveryCandidates": [],
                "riskFlags": [],
                "extractionQuality": {"jsonParseable": True},
            }, ensure_ascii=False)
            return type(
                "FakeResponse",
                (),
                {"choices": [FakeChoice(payload)], "usage": FakeUsage()},
            )()

    class FakeChat:
        completions = FakeCompletions()

    class FakeClient:
        chat = FakeChat()

    monkeypatch.setattr(evidence_extraction_service, "load_pilot_track_rule", lambda track: rule)
    monkeypatch.setattr("app.services.llm_scoring_service.get_client", lambda provider: FakeClient())

    extraction = extract_evidence(
        {"transcript": "测试转写"},
        {"track": "新一代信息技术赛道"},
        provider="deepseek",
    )

    assert len(calls) == 4
    assert calls[0]["max_tokens"] == 12000
    assert all(call["max_tokens"] == 6000 for call in calls[1:])
    assert extraction["extractionQuality"]["strategy"] == "observation_batches"
    assert extraction["extractionQuality"]["fallbackReason"].startswith("single_shot_request_failed:")
    assert {item["observationCode"] for item in extraction["observationEvidence"]} == set(observation_codes)


def test_parse_json_object_repairs_trailing_commas_and_code_fences():
    payload = """```json
{
  "claims": [],
  "evidenceItems": [],
  "observationEvidence": [],
  "deductionCandidates": [],
  "recoveryCandidates": [],
  "riskFlags": [],
  "extractionQuality": {"jsonParseable": true,},
}
```"""

    parsed = evidence_extraction_service._parse_json_object(payload)

    assert parsed["extractionQuality"]["jsonParseable"] is True
    assert parsed["claims"] == []


def test_extract_evidence_requests_json_object_response(monkeypatch):
    captured = {}
    rule = load_pilot_track_rule("商贸赛道")
    payload = json.dumps(
        {
            "claims": [],
            "evidenceItems": [],
            "observationEvidence": [],
            "deductionCandidates": [],
            "recoveryCandidates": [],
            "riskFlags": [],
            "extractionQuality": {"jsonParseable": True},
        },
        ensure_ascii=False,
    )

    class FakeMessage:
        content = payload

    class FakeChoice:
        message = FakeMessage()
        finish_reason = "stop"

    class FakeUsage:
        prompt_tokens = 1
        completion_tokens = 1
        total_tokens = 2

    class FakeCompletions:
        @staticmethod
        def create(**kwargs):
            captured.update(kwargs)
            return type("FakeResponse", (), {"choices": [FakeChoice()], "usage": FakeUsage()})()

    class FakeChat:
        completions = FakeCompletions()

    class FakeClient:
        chat = FakeChat()

    monkeypatch.setattr(evidence_extraction_service, "load_pilot_track_rule", lambda track: rule)
    monkeypatch.setattr("app.services.llm_scoring_service.get_client", lambda provider: FakeClient())

    extraction = extract_evidence({"transcript": "测试"}, {"track": "商贸赛道"}, provider="deepseek")

    assert captured["response_format"] == {"type": "json_object"}
    assert len(extraction["observationEvidence"]) == 15
