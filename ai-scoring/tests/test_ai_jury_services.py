from app.services.jury.aggregate_service import aggregate_judge_reports
from app.services.jury.scoring_service import jury_member_total_timeout_seconds


def test_jury_member_total_timeout_covers_all_stages_and_retries():
    assert jury_member_total_timeout_seconds(180, 1) == 1090
from app.services.jury.personas import select_personas
import json

from app.services.jury import persona_repository
from app.services.jury.persona_repository import default_personas, update_persona
from app.services.jury.scoring_service import provider_for_member, public_jury_result, resolve_jury_provider_channels, resolve_provider_channels
from app.services.jury import scoring_service
from app.services.jury.scoring_service import is_failed_llm_report, validate_jury_evidence_quality
from app.services.jury.snapshot_service import build_jury_evidence_snapshot
from app.services.jury.evidence_service import build_system_evidence_summary
from app.services.jury.report_service import build_jury_report_payload, jury_report_judges_for_item


def test_select_personas_is_stable_and_unique():
    selected_a = select_personas("meeting-42")
    selected_b = select_personas("meeting-42")

    assert [persona["code"] for persona in selected_a] == [persona["code"] for persona in selected_b]
    assert len(selected_a) == 9
    assert len({persona["code"] for persona in selected_a}) == 9


def test_trimmed_average_removes_highest_and_lowest():
    reports = [
        {"id": 1, "member_id": 1, "persona_code": "ISTJ", "overall_score": 70},
        {"id": 2, "member_id": 2, "persona_code": "ENTP", "overall_score": 80},
        {"id": 3, "member_id": 3, "persona_code": "ENTJ", "overall_score": 90},
        {"id": 4, "member_id": 4, "persona_code": "ISFJ", "overall_score": 60},
    ]

    aggregate = aggregate_judge_reports(reports, official_score=78.25)

    assert aggregate["raw_average_score"] == 75.00
    assert aggregate["trimmed_average_score"] == 75.00
    assert aggregate["trimmed_total_score"] == 150.00
    assert aggregate["trimmed_count"] == 2
    assert aggregate["removed_low"]["id"] == 4
    assert aggregate["removed_high"]["id"] == 3
    assert aggregate["score_diff_from_official"] == -3.25


def test_nine_judge_competition_score_sums_remaining_seven():
    reports = [
        {"id": index, "member_id": index, "persona_code": f"J{index}", "overall_score": score}
        for index, score in enumerate([50, 60, 61, 62, 63, 64, 65, 66, 90], start=1)
    ]

    aggregate = aggregate_judge_reports(reports, official_score=64.5)

    assert aggregate["judge_count"] == 9
    assert aggregate["trimmed_count"] == 7
    assert aggregate["removed_low"]["overall_score"] == 50.00
    assert aggregate["removed_high"]["overall_score"] == 90.00
    assert aggregate["trimmed_total_score"] == 441.00
    assert aggregate["trimmed_average_score"] == 63.00
    assert aggregate["score_diff_from_official"] == -1.50


def test_dimension_disagreement_uses_range_between_judges():
    reports = [
        {
            "id": 1,
            "overall_score": 70,
            "dimensions": {
                "skill_level": {"name": "技能水平", "score": 40, "max_score": 60},
                "innovation": {"name": "创新创意", "score": 7, "max_score": 10},
            },
        },
        {
            "id": 2,
            "overall_score": 80,
            "dimensions": {
                "skill_level": {"name": "技能水平", "score": 50, "max_score": 60},
                "innovation": {"name": "创新创意", "score": 6, "max_score": 10},
            },
        },
    ]

    aggregate = aggregate_judge_reports(reports, official_score=76)

    skill = aggregate["dimension_stats"][0]
    assert skill["key"] == "skill_level"
    assert skill["range"] == 10.00
    assert skill["average_score"] == 45.00


def test_jury_snapshot_excludes_official_ai_score():
    pipeline_result = {
        "meeting_id": "42",
        "status": "completed",
        "ai_score": {
            "overall_score": 99,
            "critical_issues": ["this would anchor the jury"],
        },
        "asr": {
            "transcript": "项目完成了现场演示。",
            "segments": [{"text": "项目完成了现场演示。", "start": 0, "end": 3}],
        },
        "speech_quality": {"speech_rate": {"global_chars_per_minute": 180}},
        "video_analysis": {"frame_count": 3},
        "fusion": {"summary": {"fusion_avg": 80}},
    }

    snapshot = build_jury_evidence_snapshot(pipeline_result, {"project_name": "Demo"})

    assert "ai_score" not in snapshot
    assert "official_score" not in snapshot
    assert "official_ai_score" not in snapshot
    assert snapshot["asr"]["transcript"] == "项目完成了现场演示。"
    assert snapshot["project_info"]["project_name"] == "Demo"


def test_jury_snapshot_keeps_memory_without_score_anchors():
    pipeline_result = {
        "meeting_id": "42",
        "asr": {"transcript": "本轮补充了演示和测试数据。"},
        "roadshow_memory": {
            "priorIssueReview": [
                {
                    "title": "关键功能演示不完整",
                    "status": "resolved",
                    "conclusion": "本轮已经现场跑通核心链路",
                    "recoveredScore": 3,
                    "evidenceAnchors": [
                        {
                            "type": "transcript",
                            "summary": "现场演示跑通了核心链路",
                            "sourceRef": "00:03:10-00:03:50",
                            "score": 100,
                        }
                    ],
                }
            ],
            "newIssues": [
                {
                    "title": "性能测试数据不足",
                    "severity": "HIGH",
                    "score": 88,
                }
            ],
            "trainingPlan": [
                {
                    "title": "补齐压力测试证据",
                    "acceptance": "提交可复现实测数据",
                }
            ],
            "fullScoreGap": {
                "rawScore": 96,
                "ceilingScore": 88,
                "reasons": ["技术证据不足以进入95+"],
            },
            "timeline": [
                {"roundNo": 1, "score": 80, "issueCount": 2},
                {"roundNo": 2, "score": 88, "issueCount": 1},
            ],
        },
    }

    snapshot = build_jury_evidence_snapshot(pipeline_result, {"project_name": "Demo"})
    memory = snapshot["roadshow_memory"]

    assert memory["prior_issue_review"][0]["title"] == "关键功能演示不完整"
    assert memory["prior_issue_review"][0]["status"] == "resolved"
    assert memory["prior_issue_review"][0]["evidence_anchors"][0]["type"] == "transcript"
    assert "score" not in memory["prior_issue_review"][0]["evidence_anchors"][0]
    assert memory["full_score_gap_reasons"] == ["技术证据不足以进入95+"]
    assert "recoveredScore" not in memory["prior_issue_review"][0]
    assert "score" not in memory["new_issues"][0]
    assert "score" not in memory["timeline"][0]
    assert "ceilingScore" not in str(memory)
    assert "rawScore" not in str(memory)


def test_jury_session_accepts_manual_memory_summary_without_scores(tmp_path, monkeypatch):
    monkeypatch.setattr(scoring_service.settings, "UPLOAD_DIR", str(tmp_path))
    official_result = {
        "meeting_id": "42",
        "has_video": False,
        "ai_score": {"overall_score": 91},
        "asr": {"transcript": "本轮补齐了演示。"},
        "speech_quality": {},
    }
    memory_summary = {
        "priorIssueReview": [
            {
                "title": "关键功能演示不完整",
                "status": "resolved",
                "recoveredScore": 3,
            }
        ],
        "timeline": [{"roundNo": 1, "score": 80}],
    }

    session = scoring_service._build_session(
        "42",
        official_result,
        {"project_name": "Demo"},
        "deepseek",
        False,
        memory_summary=memory_summary,
    )

    memory = session["roadshow_memory_summary"]
    assert memory["prior_issue_review"][0]["title"] == "关键功能演示不完整"
    assert memory["prior_issue_review"][0]["status"] == "resolved"
    assert "recoveredScore" not in str(memory)
    assert "score" not in str(memory)


def test_jury_session_carries_rule_engine_dispute_context(tmp_path, monkeypatch):
    monkeypatch.setattr(scoring_service.settings, "UPLOAD_DIR", str(tmp_path))
    official_result = {
        "meeting_id": "43",
        "has_video": False,
        "ai_score": {"overall_score": 72},
        "asr": {"transcript": "商业验证证据不足。"},
        "speech_quality": {},
    }
    dispute_context = {
        "mode": "dispute_review",
        "ruleEngineScore": 72,
        "llmRawScore": 89,
        "scoreDiff": -17,
        "reviewTriggers": ["规则引擎分与旧 LLM 分差异超过10分", "E4/E5 高证据等级存在锚点不足风险"],
        "disputedObservations": [{"dimensionName": "商业验证", "evidenceLevel": "E5", "anchorCount": 1}],
        "deductionReviewItems": [{"reason": "客户访谈证据不足", "deductedPoints": 4}],
        "humanReviewSuggested": True,
    }

    session = scoring_service._build_session(
        "43",
        official_result,
        {"project_name": "Demo"},
        "deepseek",
        False,
        dispute_review_context=dispute_context,
    )
    snapshot = scoring_service._read_json(session["evidence_snapshot_path"])
    public_result = public_jury_result(session)

    assert session["review_mode"] == "dispute_review"
    assert session["dispute_review_context"]["ruleEngineScore"] == 72
    assert snapshot["dispute_review_context"]["reviewTriggers"][0] == "规则引擎分与旧 LLM 分差异超过10分"
    assert public_result["review_mode"] == "dispute_review"
    assert public_result["dispute_review_context"]["disputedObservations"][0]["dimensionName"] == "商业验证"


def test_provider_channels_round_robin_by_seat():
    channels = resolve_provider_channels("deepseek,minimax,unknown,,deepseek")

    assert channels == ["deepseek", "deepseek"]
    assert provider_for_member({"seat_no": 1}, channels) == "deepseek"
    assert provider_for_member({"seat_no": 2}, channels) == "deepseek"
    assert provider_for_member({"seat_no": 3}, channels) == "deepseek"
    assert provider_for_member({"seat_no": 4}, channels) == "deepseek"


def test_request_provider_channels_are_not_shadowed_by_default_settings(monkeypatch):
    monkeypatch.setattr("app.services.jury.scoring_service.settings.AI_JURY_PROVIDERS", "")

    channels = resolve_jury_provider_channels("deepseek,minimax")

    assert channels == ["deepseek"]


def test_default_personas_have_detailed_profiles():
    personas = default_personas()

    assert len(personas) == 16
    for persona in personas:
        profile = persona["judge_profile"]
        rubric = persona["rubric_focus"]
        assert profile["core_traits"]
        assert profile["scoring_style"]
        assert profile["evidence_preference"]
        assert profile["sensitive_risks"]
        assert profile["likely_high_score_reason"]
        assert profile["likely_low_score_reason"]
        assert profile["feedback_style"]
        assert rubric["primary_dimensions"]
        assert rubric["primary_items"]


def test_update_persona_preserves_code_and_merges_profile():
    personas = default_personas()
    updated = update_persona(
        personas,
        "ISTJ",
        {
            "name": "规范证据审查官",
            "judge_profile": {
                "scoring_style": "极度重视证据闭环。",
                "core_traits": ["严谨", "保守", "证据导向"],
            },
        },
    )

    istj = next(item for item in updated if item["code"] == "ISTJ")
    assert istj["name"] == "规范证据审查官"
    assert istj["code"] == "ISTJ"
    assert istj["judge_profile"]["scoring_style"] == "极度重视证据闭环。"
    assert istj["judge_profile"]["evidence_preference"]


def test_load_backend_personas_accepts_java_result_wrapper(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps({"data": {"personas": default_personas()[:1]}}, ensure_ascii=False).encode("utf-8")

    monkeypatch.setattr(persona_repository.settings, "AI_JURY_PERSONA_API_URL", "http://backend/api/ai-jury/personas")
    monkeypatch.setattr(persona_repository.urllib.request, "urlopen", lambda url, timeout: FakeResponse())

    personas = persona_repository.load_personas()

    assert len(personas) == 1
    assert personas[0]["code"] == "ISTJ"
    assert personas[0]["judge_profile"]["core_traits"]


def test_failed_llm_report_is_not_treated_as_completed_score():
    report = {
        "overall_score": 0,
        "dimensions": {},
        "critical_issues": ["评分失败 [MiniMax M2.5]: Error code: 429"],
    }

    assert is_failed_llm_report(report)


def test_jury_rejects_video_meeting_without_valid_visual_analysis():
    result = {
        "has_video": True,
        "video_analysis": {"frame_count": 104, "aggregates": {"error": "无有效数据"}},
        "fusion": {"timeline": []},
    }

    try:
        validate_jury_evidence_quality(result)
    except ValueError as exc:
        assert "视频帧分析没有有效结果" in str(exc)
    else:
        raise AssertionError("expected invalid visual evidence to be rejected")


def test_public_jury_result_exposes_member_detail_report_fields():
    session = {
        "meeting_id": "unit-no-file",
        "status": "completed",
        "members": [{"seat_no": 1, "code": "INTP", "role_label": "逻辑推理型评委", "short_label": "逻辑、算法、论证"}],
        "judge_reports": [{
            "seat_no": 1,
            "persona_code": "INTP",
            "status": "completed",
            "overall_score": 62.25,
            "dimensions": {"skill_level": {"name": "技能水平", "score": 39.25, "items": []}},
            "highlights": ["技术路线较完整"],
            "critical_issues": ["论证证据不足"],
            "improvement_priorities": [{"priority": 1, "issue": "补强算法证据", "suggestion": "增加对比实验"}],
            "evidence_summary": {"verbal_evidence_count": 8, "visual_evidence_count": 4},
            "persona_view": {"top_concerns": ["技术逻辑的严密性"]},
        }],
        "aggregate": {},
    }

    result = public_jury_result(session)
    member = result["members"][0]

    assert member["dimensions"]["skill_level"]["score"] == 39.25
    assert member["highlights"] == ["技术路线较完整"]
    assert member["improvement_priorities"][0]["suggestion"] == "增加对比实验"
    assert member["evidence_summary"]["visual_evidence_count"] == 4


def test_public_jury_result_splits_string_top_concerns_for_ui():
    session = {
        "meeting_id": "15",
        "status": "completed",
        "members": [{"seat_no": 1, "code": "ISFP", "role_label": "体验感知型评委"}],
        "judge_reports": [{
            "seat_no": 1,
            "persona_code": "ISFP",
            "status": "completed",
            "overall_score": 59.5,
            "persona_view": {"top_concerns": "用户体验、场景真实感、表达温度"},
        }],
        "aggregate": {},
    }

    result = public_jury_result(session)
    member = result["members"][0]

    assert member["summary"] == "用户体验"
    assert member["persona_view"]["top_concerns"] == ["用户体验", "场景真实感", "表达温度"]


def test_system_evidence_summary_counts_visual_and_cross_validated_evidence():
    official_result = {
        "asr": {
            "segments": [
                {"start": 10, "end": 14, "text": "这里展示代码模块和数据图表。"},
                {"start": 45, "end": 50, "text": "我们展示成本对比和用户反馈。"},
            ]
        },
        "video_analysis": {
            "per_frame": [
                {
                    "timestamp_min": 0.2,
                    "screen_content": {
                        "screen_type": "代码展示",
                        "visible_text": "核心代码模块",
                    },
                },
                {
                    "timestamp_min": 0.8,
                    "screen_content": {
                        "screen_type": "数据图表",
                        "visible_text": "成本对比 用户反馈",
                    },
                },
            ]
        },
        "fusion": {
            "timeline": [{"time_min": 0.2}, {"time_min": 0.8}],
            "screen_content_summary": {
                "visible_texts": [
                    {"timestamp_min": 0.2, "text": "核心代码模块"},
                    {"timestamp_min": 0.8, "text": "成本对比 用户反馈"},
                ]
            },
        },
    }

    summary = build_system_evidence_summary(official_result)

    assert summary["verbal_evidence_count"] == 2
    assert summary["visual_evidence_count"] == 2
    assert summary["cross_validated_count"] == 2
    assert summary["source"] == "system_computed"


def test_public_jury_result_overrides_model_evidence_with_system_counts():
    session = {
        "meeting_id": "16",
        "status": "completed",
        "official_evidence_summary": {
            "verbal_evidence_count": 2,
            "visual_evidence_count": 2,
            "cross_validated_count": 1,
            "source": "system_computed",
        },
        "members": [{"seat_no": 1, "code": "ENFJ", "role_label": "领导说服型评委"}],
        "judge_reports": [{
            "seat_no": 1,
            "persona_code": "ENFJ",
            "status": "completed",
            "overall_score": 63,
            "evidence_summary": {"verbal_evidence_count": 15, "visual_evidence_count": 0, "cross_validated_count": 0},
            "persona_view": {"top_concerns": ["团队愿景"]},
        }],
        "aggregate": {},
    }

    result = public_jury_result(session)
    member = result["members"][0]

    assert member["evidence_summary"]["verbal_evidence_count"] == 2
    assert member["evidence_summary"]["visual_evidence_count"] == 2
    assert member["evidence_summary"]["cross_validated_count"] == 1
    assert member["evidence_summary"]["source"] == "system_computed"


def test_jury_report_payload_has_coaching_tone_and_deduction_map():
    session = {
        "meeting_id": "16",
        "official_score": 64.75,
        "jury_trimmed_avg": 61.58,
        "score_diff_from_official": -3.17,
        "official_evidence_summary": {"verbal_evidence_count": 2, "visual_evidence_count": 2, "cross_validated_count": 1},
        "members": [{"seat_no": 1, "code": "ENFJ", "role_label": "领导说服型评委"}],
        "judge_reports": [{
            "seat_no": 1,
            "persona_code": "ENFJ",
            "role_label": "领导说服型评委",
            "overall_score": 63,
            "dimensions": {
                "skill_level": {
                    "name": "技能水平",
                    "max_score": 60,
                    "score": 35,
                    "items": [{"name": "技能熟练度", "max_score": 15, "score": 8.5, "reason": "演示故障造成冷场。"}],
                }
            },
            "critical_issues": ["演示故障造成冷场"],
            "improvement_priorities": [{"priority": 1, "dimension": "技能水平", "issue": "演示稳定性", "suggestion": "准备应急话术。"}],
        }],
        "aggregate": {"dimension_stats": [{"key": "skill_level", "name": "技能水平", "range": 8.75}]},
    }

    payload = build_jury_report_payload(session)

    assert "不是为了再给一次分" in payload["coach_note"]
    assert "低于本场得分64.75共3.17分" in payload["reading_summary"][0]
    assert payload["score_cards"][0]["persona_code"] == "ENFJ"
    assert payload["deduction_map"][0]["dimension"] == "技能水平"
    assert payload["deduction_map"][0]["item"] == "技能熟练度"
    assert payload["deduction_map"][0]["deducted"] == 6.5


def test_jury_report_payload_merges_repeated_deductions_and_balances_dimensions():
    session = {
        "meeting_id": "16",
        "official_score": 64.75,
        "judge_reports": [
            {
                "persona_code": "A",
                "overall_score": 60,
                "dimensions": {
                    "skill_level": {
                        "name": "技能水平",
                        "items": [
                            {"name": "技能熟练度", "max_score": 15, "score": 8.5, "reason": "AI演示故障造成冷场。"},
                            {"name": "技术先进性", "max_score": 15, "score": 8.0, "reason": "缺少技术对比。"},
                        ],
                    },
                    "innovation": {
                        "name": "创新创意",
                        "items": [{"name": "创新成效", "max_score": 6, "score": 3.5, "reason": "数据来源不清。"}],
                    },
                },
                "improvement_priorities": [
                    {"priority": 1, "dimension": "技能水平", "issue": "AI演示故障", "suggestion": "准备备用演示。"},
                    {"priority": 2, "dimension": "创新创意", "issue": "数据来源不清", "suggestion": "补充A/B测试来源。"},
                ],
            },
            {
                "persona_code": "B",
                "overall_score": 61,
                "dimensions": {
                    "skill_level": {
                        "name": "技能水平",
                        "items": [
                            {"name": "技能熟练度", "max_score": 15, "score": 8.0, "reason": "AI问答模块演示失败。"},
                            {"name": "技术先进性", "max_score": 15, "score": 8.0, "reason": "缺少benchmark。"},
                        ],
                    },
                    "application_value": {
                        "name": "应用价值",
                        "items": [{"name": "经济性", "max_score": 3, "score": 2.0, "reason": "缺少投入产出表。"}],
                    },
                },
                "improvement_priorities": [
                    {"priority": 1, "dimension": "技能水平", "issue": "现场演示稳定性不足", "suggestion": "全流程彩排并准备离线方案。"},
                    {"priority": 2, "dimension": "应用价值", "issue": "成本证据不足", "suggestion": "补成本对比表。"},
                ],
            },
        ],
        "aggregate": {},
    }

    payload = build_jury_report_payload(session)
    skill_fluency = next(item for item in payload["deduction_map"] if item["item"] == "技能熟练度")

    assert skill_fluency["judge_count"] == 2
    assert skill_fluency["dimension"] == "技能水平"
    assert skill_fluency["average_deducted"] == 6.75
    assert len([item for item in payload["deduction_map"] if item["dimension"] == "创新创意"]) == 1
    assert payload["action_routes"][0]["theme"] == "演示稳定性"
    assert payload["action_routes"][0]["mention_count"] == 2


def test_jury_report_counts_unique_judges_and_builds_action_playbook():
    session = {
        "meeting_id": "16",
        "official_score": 64.75,
        "judge_reports": [
            {
                "persona_code": "ISTP",
                "role_label": "实操验证型评委",
                "overall_score": 60,
                "dimensions": {
                    "skill_level": {
                        "name": "技能水平",
                        "items": [
                            {
                                "name": "技能熟练度",
                                "max_score": 15,
                                "score": 8.5,
                                "reason": "AI问答模块现场演示故障，导致冷场。",
                                "improvement": "准备备用演示和异常过渡话术。",
                            },
                            {
                                "name": "现场讲解效果",
                                "max_score": 5,
                                "score": 3.5,
                                "reason": "代码讲解冗长，重点不突出。",
                                "improvement": "压缩代码讲解，只讲业务逻辑、关键算法和结果。",
                            },
                        ],
                    },
                },
                "improvement_priorities": [
                    {"priority": 1, "dimension": "技能水平", "issue": "AI问答模块现场演示故障，导致冷场", "suggestion": "准备备用演示和异常过渡话术。"},
                    {"priority": 2, "dimension": "技能水平", "issue": "代码讲解冗长", "suggestion": "压缩代码讲解，只讲业务逻辑、关键算法和结果。"},
                ],
            },
            {
                "persona_code": "ENTJ",
                "role_label": "价值决策型评委",
                "overall_score": 65,
                "dimensions": {
                    "skill_level": {
                        "name": "技能水平",
                        "items": [
                            {
                                "name": "技能熟练度",
                                "max_score": 15,
                                "score": 9,
                                "reason": "AI问答演示失败，影响现场可信度。",
                                "improvement": "增加全流程彩排和录屏兜底。",
                            },
                        ],
                    },
                    "innovation": {
                        "name": "创新创意",
                        "items": [
                            {
                                "name": "创新成效",
                                "max_score": 6,
                                "score": 3,
                                "reason": "开发效率提升数据缺少来源。",
                                "improvement": "补充A/B测试、性能benchmark和数据来源页。",
                            }
                        ],
                    },
                },
                "improvement_priorities": [
                    {"priority": 1, "dimension": "技能水平", "issue": "AI问答模块现场演示故障", "suggestion": "增加全流程彩排和录屏兜底。"},
                    {"priority": 2, "dimension": "创新创意", "issue": "创新成效数据缺少来源", "suggestion": "补充A/B测试、性能benchmark和数据来源页。"},
                ],
            },
        ],
        "aggregate": {},
    }

    payload = build_jury_report_payload(session)
    stability = next(route for route in payload["action_routes"] if route["theme"] == "演示稳定性")
    skill_fluency = next(item for item in payload["deduction_details"] if item["item"] == "技能熟练度")

    assert stability["judge_count"] == 2
    assert stability["mention_count"] == 2
    assert "2位评委" not in stability["action"]
    assert len(stability["tasks"]) >= 4
    assert any(task["label"] == "演示兜底" for task in stability["tasks"])
    assert skill_fluency["judge_count"] == 2
    assert skill_fluency["average_score"] == 8.75
    assert skill_fluency["average_deducted"] == 6.25
    assert len(skill_fluency["judge_breakdown"]) == 2


def test_jury_report_pdf_uses_all_judges_for_deduction_item():
    item = {
        "judge_breakdown": [
            {"persona_code": f"J{i}", "role_label": "评委", "deducted": i, "reason": "原因"}
            for i in range(1, 10)
        ]
    }

    judges = jury_report_judges_for_item(item)

    assert len(judges) == 9
    assert judges[0]["persona_code"] == "J1"
    assert judges[-1]["persona_code"] == "J9"
