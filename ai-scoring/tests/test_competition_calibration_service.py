from app.services.official_rubric_service import normalize_official_rubric
from app.services.demo_evidence_service import analyze_demo_evidence
from app.services.competition_calibration_service import apply_calibration_to_result, calibrate_ai_score
from app.services.pipeline_payloads import build_backend_callback_payload


def test_normalize_official_rubric_preserves_skill_level_60_points():
    ai_score = {
        "overall_score": 88,
        "dimensions": {
            "skill_level": {
                "name": "技能水平",
                "max_score": 60,
                "score": 50,
                "items": [
                    {"name": "操作规范性", "max_score": 10, "score": 8},
                    {"name": "技能熟练度", "max_score": 15, "score": 12},
                    {"name": "任务难易度", "max_score": 15, "score": 13},
                    {"name": "技术先进性", "max_score": 15, "score": 12},
                    {"name": "现场讲解效果", "max_score": 5, "score": 5},
                ],
            }
        },
    }

    rubric = normalize_official_rubric(ai_score)

    assert rubric["total_score"] == 50.0
    assert rubric["dimensions"]["skill_level"]["score"] == 50.0
    assert rubric["dimensions"]["skill_level"]["max_score"] == 60.0
    assert rubric["dimensions"]["skill_level"]["items"][1]["key"] == "skill_fluency"


def test_demo_evidence_detects_demo_with_runtime_and_test_data():
    result = {
        "asr": {"transcript": "下面进入现场演示，系统成功运行，响应时间降低40%。"},
        "video_analysis": {
            "per_frame": [
                {"screen_content": {"screen_type": "系统界面", "text": "运行成功 响应时间 200ms"}},
                {"screen_content": {"screen_type": "测试报告", "text": "benchmark 准确率 92%"}},
            ]
        },
        "fusion": {"screen_content_summary": {"screen_type_distribution": {"系统界面": 1, "测试报告": 1}}},
    }

    evidence = analyze_demo_evidence(result)

    assert evidence["has_demo"] is True
    assert evidence["has_runtime_result"] is True
    assert evidence["has_test_data"] is True
    assert evidence["level"] == "full_channel"


def test_calibration_caps_score_when_demo_evidence_is_missing():
    result = {
        "ai_score": {
            "overall_score": 96,
            "dimensions": {
                "skill_level": {"name": "技能水平", "max_score": 60, "score": 56, "items": []},
                "professionalism": {"name": "职业素养", "max_score": 10, "score": 10, "items": []},
                "application_value": {"name": "应用价值", "max_score": 10, "score": 10, "items": []},
                "teamwork": {"name": "团队合作", "max_score": 10, "score": 10, "items": []},
                "innovation": {"name": "创新创意", "max_score": 10, "score": 10, "items": []},
            },
        },
        "asr": {"transcript": "我们介绍了技术方案和PPT。"},
        "video_analysis": {"per_frame": [{"screen_content": {"screen_type": "PPT幻灯片", "text": "技术方案"}}]},
    }

    calibrated = calibrate_ai_score(result)

    assert calibrated["final_score"] == 85.0
    assert calibrated["technical_ceiling_score"] == 85.0
    assert "缺少现场演示证据" in calibrated["ceiling_reasons"][0]


def test_apply_calibration_updates_ai_score_and_keeps_original_score():
    result = {
        "ai_score": {
            "overall_score": 96,
            "dimensions": {
                "skill_level": {"name": "技能水平", "max_score": 60, "score": 56, "items": []},
                "professionalism": {"name": "职业素养", "max_score": 10, "score": 10, "items": []},
                "application_value": {"name": "应用价值", "max_score": 10, "score": 10, "items": []},
                "teamwork": {"name": "团队合作", "max_score": 10, "score": 10, "items": []},
                "innovation": {"name": "创新创意", "max_score": 10, "score": 10, "items": []},
            },
        },
        "asr": {"transcript": "PPT介绍技术方案。"},
        "video_analysis": {"per_frame": []},
    }

    updated = apply_calibration_to_result(result)

    assert updated["ai_score"]["overall_score"] == 85.0
    assert updated["ai_score"]["raw_overall_score"] == 96.0
    assert updated["score_calibration"]["ceiling_applied"] is True


def test_backend_callback_payload_includes_score_calibration():
    result = {
        "status": "completed",
        "ai_score": {"overall_score": 85, "model": "deepseek-chat"},
        "asr": {"transcript": "完成现场演示。", "duration": 3600},
        "score_calibration": {
            "original_score": 96,
            "final_score": 85,
            "technical_ceiling_score": 85,
            "ceiling_reasons": ["缺少现场演示证据，技能水平不能支撑95+或满分。"],
        },
    }

    payload = build_backend_callback_payload("42", result)

    assert payload["scoreCalibration"]["original_score"] == 96
    assert payload["scoreCalibration"]["final_score"] == 85
    assert payload["overallScore"] == 85


def test_backend_callback_payload_carries_evidence_extraction_without_scores():
    result = {
        "status": "completed",
        "ai_score": {"overall_score": 85, "model": "deepseek-chat"},
        "asr": {"transcript": "完成现场演示。"},
        "evidence_extraction": {
            "status": "completed_with_warnings",
            "trackName": "人工智能赛道",
            "observationEvidence": [{"observationCode": "O01", "evidenceLevel": "E0"}],
            "claims": [],
            "evidenceItems": [],
        },
    }

    payload = build_backend_callback_payload("42", result)

    assert payload["evidenceExtraction"]["status"] == "completed_with_warnings"
    assert payload["evidenceExtraction"]["trackName"] == "人工智能赛道"
    assert "overall_score" not in payload["evidenceExtraction"]
    assert "dimension_scores" not in payload["evidenceExtraction"]


def test_backend_callback_payload_includes_rule_engine_shadow_score_without_replacing_official_score():
    observation_evidence = []
    for index in range(15):
        observation_evidence.append({
            "observationCode": f"O{index + 1:02d}",
            "observationName": f"观测点{index + 1}",
            "dimensionCode": "skill_level" if index < 5 else "professionalism",
            "dimensionName": "技能水平" if index < 5 else "职业素养",
            "evidenceLevel": "E2",
            "confidence": 0.8,
            "suggestedScoreCap": 2,
            "validityStatus": "valid",
            "supportSummary": "有解释性证据",
            "evidenceIds": ["e1"],
        })
    result = {
        "status": "completed",
        "ai_score": {
            "overall_score": 85,
            "raw_overall_score": 90,
            "model": "deepseek-chat",
        },
        "asr": {"transcript": "完成现场演示。"},
        "evidence_extraction": {
            "status": "completed_with_warnings",
            "trackName": "商贸赛道",
            "ruleVersion": "v1.2-engine-pilot",
            "ruleHash": "sha256:test",
            "observationEvidence": observation_evidence,
            "deductionCandidates": [
                {
                    "deductionId": "D-O01-1",
                    "observationCode": "O01",
                    "dimensionCode": "skill_level",
                    "deductedPoints": 1,
                    "maxRecoverablePoints": 1,
                    "reason": "缺少现场验证",
                    "requiredFix": "补充演示证据",
                    "acceptanceCriteria": "证据可定位",
                    "evidenceLevel": "E2",
                    "confidence": 0.8,
                    "status": "new",
                }
            ],
        },
    }

    payload = build_backend_callback_payload("42", result)

    assert payload["overallScore"] == 85
    assert payload["llmRawScore"] == 90
    assert payload["ruleEngineScore"] == 30
    assert payload["scoreDiff"] == -55
    assert payload["diffReasons"] == ["score_diff_exceeds_10"]
    assert payload["ruleEngineVersion"] == "score-policy-v2-single-attribution"
    assert len(payload["observations"]) == 15
    assert payload["deductions"] == []
    assert payload["diagnosticDeductions"][0]["deductionId"] == "D-O01-1"
