from app.services.scoring.score_impact_service import build_score_impact_projection


def _observation(
    code,
    dimension,
    *,
    max_score,
    base_score,
    score_cap,
    performance_reason="",
    evidence_reason="",
):
    return {
        "observationCode": code,
        "observationName": code,
        "dimensionCode": dimension,
        "maxScore": max_score,
        "baseScore": base_score,
        "scoreCap": score_cap,
        "performanceReason": performance_reason,
        "evidenceReason": evidence_reason,
    }


def test_builds_deduction_evidence_performance_and_unlinked_impacts():
    observations = [
        _observation(
            "O1",
            "skill",
            max_score=10,
            base_score=5,
            score_cap=10,
            performance_reason="讲解节奏拖沓，演示稳定性不足",
        ),
        _observation(
            "O2",
            "value",
            max_score=10,
            base_score=8,
            score_cap=5,
            evidence_reason="关键业务数据缺少来源和第三方验证",
        ),
    ]
    deductions = [{
        "deductionId": "D1",
        "causeCode": "DEMO_FAILURE",
        "observationCode": "O1",
        "deductedPoints": 2,
        "maxRecoverablePoints": 2,
        "scoreEffect": "subtractive",
        "status": "new",
    }]
    tasks = [
        {
            "id": "t1",
            "title": "修复演示故障",
            "observationCode": "O1",
            "sourceIssueKey": "DEMO_FAILURE",
        },
        {
            "id": "t2",
            "title": "优化讲解节奏",
            "observationCode": "O1",
            "impactType": "performance_improvement",
        },
        {
            "id": "t3",
            "title": "补充数据来源",
            "observationCode": "O2",
            "impactType": "evidence_unlock",
        },
        {"id": "t4", "title": "更换队服"},
    ]

    scored_tasks, projection = build_score_impact_projection(
        tasks,
        observations,
        deductions,
        rule_hash="rule-1",
        scoring_fingerprint="fp-1",
    )

    assert scored_tasks[0]["scoreImpact"]["impactType"] == "deduction_recovery"
    assert scored_tasks[0]["scoreImpact"]["lower"] == 2.0
    assert scored_tasks[0]["scoreImpact"]["upper"] == 2.0
    assert scored_tasks[1]["scoreImpact"]["impactType"] == "performance_improvement"
    assert 0 < scored_tasks[1]["scoreImpact"]["lower"] <= scored_tasks[1]["scoreImpact"]["upper"]
    assert scored_tasks[2]["scoreImpact"]["impactType"] == "evidence_unlock"
    assert scored_tasks[2]["scoreImpact"]["upper"] == 3.0
    assert scored_tasks[3]["scoreImpact"] == {
        "scoreLinkStatus": "unlinked",
        "lower": None,
        "upper": None,
        "reason": "no_scoring_rule_link",
    }
    assert projection["goalScore"] == 100.0
    assert projection["currentScore"] == 8.0
    assert projection["fullGap"] == 92.0
    assert projection["predictedScoreLower"] <= projection["predictedScoreUpper"] <= 100.0
    assert projection["scoredTodoCount"] == 3
    assert projection["unlinkedAdviceCount"] == 1
    assert projection["calculationVersion"] == "score-impact-v1"
    assert projection["ruleHash"] == "rule-1"
    assert projection["scoringFingerprint"] == "fp-1"


def test_portfolio_replays_shared_observation_once_instead_of_summing_task_ranges():
    observations = [
        _observation(
            "O1",
            "skill",
            max_score=10,
            base_score=5,
            score_cap=10,
            performance_reason="讲解节奏和结构不足",
        )
    ]
    tasks = [
        {
            "id": "a",
            "title": "精简讲解",
            "observationCode": "O1",
            "impactType": "performance_improvement",
        },
        {
            "id": "b",
            "title": "降低语速",
            "observationCode": "O1",
            "impactType": "performance_improvement",
        },
    ]

    scored, projection = build_score_impact_projection(
        tasks,
        observations,
        [],
        rule_hash="rule-2",
        scoring_fingerprint="fp-2",
    )

    summed_upper = sum(item["scoreImpact"]["upper"] for item in scored)
    assert projection["predictedGainUpper"] < summed_upper
    assert projection["predictedGainUpper"] == max(item["scoreImpact"]["upper"] for item in scored)


def test_model_expected_gain_never_creates_a_score_without_a_rule_link():
    scored, projection = build_score_impact_projection(
        [{"id": "a", "title": "泛化建议", "expected_gain": 20}],
        [_observation("O1", "skill", max_score=10, base_score=5, score_cap=10)],
        [],
        rule_hash="rule-3",
        scoring_fingerprint="fp-3",
    )

    assert scored[0]["scoreImpact"]["scoreLinkStatus"] == "unlinked"
    assert scored[0]["scoreImpact"]["upper"] is None
    assert projection["predictedGainUpper"] == 0.0


def test_legacy_plan_titles_only_link_when_one_observation_is_a_clear_semantic_winner():
    observations = [
        {
            **_observation(
                "O5",
                "skill",
                max_score=5,
                base_score=2.5,
                score_cap=2.5,
                performance_reason="讲解结构完整，但语速过快、停顿多、填充词多，影响流畅度。",
            ),
            "observationName": "现场讲解效果",
        },
        {
            **_observation(
                "O8",
                "professionalism",
                max_score=3,
                base_score=1.5,
                score_cap=1.5,
                performance_reason="口头说明安全措施，但未展示安全测试结果或应急预案。",
            ),
            "observationName": "安全意识",
        },
        {
            **_observation(
                "O11",
                "value",
                max_score=3,
                base_score=0,
                score_cap=2.7,
                performance_reason="口头提及未来规划，但缺乏具体路线图或商业化规划。",
            ),
            "observationName": "可持续性",
        },
        {
            **_observation(
                "O15",
                "innovation",
                max_score=6,
                base_score=3,
                score_cap=3,
                performance_reason="提供量化数据，但数据来源未说明。",
            ),
            "observationName": "创新成效",
        },
    ]
    tasks = [
        {"title": "优化语速与表达流畅度"},
        {"title": "展示安全测试与知识产权证明"},
        {"title": "完善商业模式与未来规划"},
        {"title": "补充数据来源与第三方验证"},
        {"title": "精简代码讲解，聚焦核心逻辑"},
    ]

    scored, projection = build_score_impact_projection(tasks, observations, [])

    assert [item.get("observationCode") for item in scored[:4]] == ["O5", "O8", "O11", "O15"]
    assert all(item["scoreImpact"]["scoreLinkStatus"] == "linked" for item in scored[:4])
    assert scored[4]["scoreImpact"]["scoreLinkStatus"] == "unlinked"
    assert projection["scoredTodoCount"] == 4
    assert projection["unlinkedAdviceCount"] == 1


def test_no_authoritative_observations_returns_full_score_reference_without_prediction():
    scored, projection = build_score_impact_projection(
        [{"id": "a", "title": "训练建议"}],
        [],
        [],
        rule_hash=None,
        scoring_fingerprint=None,
    )

    assert scored[0]["scoreImpact"]["scoreLinkStatus"] == "unlinked"
    assert projection == {
        "goalScore": 100.0,
        "currentScore": None,
        "fullGap": None,
        "predictedScoreLower": None,
        "predictedScoreUpper": None,
        "predictedGainLower": None,
        "predictedGainUpper": None,
        "scoredTodoCount": 0,
        "unlinkedAdviceCount": 1,
        "calculationVersion": "score-impact-v1",
        "ruleHash": None,
        "scoringFingerprint": None,
    }


def test_v3_uses_covered_losses_and_keeps_gap_distinct_from_conservative_gain():
    observations = [
        _observation(
            "O1",
            "skill",
            max_score=10,
            base_score=0,
            score_cap=10,
            performance_reason="现场演示未达到要求",
        )
    ]
    ledger = [{
        "lossId": "loss-o1-performance",
        "lossKey": "rule:O1:performance_gap",
        "observationCode": "O1",
        "dimensionCode": "skill",
        "lossType": "performance_gap",
        "points": 10.0,
        "scoreBudgetKey": "O1:performance_score",
    }]
    tasks = [{
        "taskId": "task-o1",
        "title": "提升现场演示",
        "coveredLossIds": ["loss-o1-performance"],
        "minimumAcceptance": {"summary": "完成一次稳定演示", "requiredEvidence": ["录像"]},
        "fullScoreCriteria": {"summary": "完整满足观测点要求", "ruleReference": "O1"},
    }]

    scored, projection = build_score_impact_projection(
        tasks,
        observations,
        [],
        loss_ledger=ledger,
        rule_hash="rule",
        scoring_fingerprint="fp",
    )

    assert scored[0]["coveredGapPoints"] == 10.0
    assert scored[0]["scoreImpact"]["scoreLinkStatus"] == "linked"
    assert scored[0]["scoreImpact"]["upper"] < scored[0]["coveredGapPoints"]
    assert scored[0]["scoreImpact"]["scoreBudgetKeys"] == ["O1:performance_score"]
    assert projection["scenarioScope"] == "all_known_tasks_minimum_acceptance"
    assert projection["coveredGapPoints"] == 10.0
    assert projection["coverageRate"] == 1.0
    assert projection["calculationVersion"] == "score-impact-v2"


def test_v3_portfolio_consumes_shared_loss_budget_once():
    observations = [
        _observation("O1", "skill", max_score=10, base_score=5, score_cap=10)
    ]
    ledger = [{
        "lossId": "loss-o1",
        "observationCode": "O1",
        "dimensionCode": "skill",
        "lossType": "performance_gap",
        "points": 5.0,
        "scoreBudgetKey": "O1:performance_score",
    }]
    tasks = [
        {"taskId": "a", "title": "精简讲解", "coveredLossIds": ["loss-o1"]},
        {"taskId": "b", "title": "降低语速", "coveredLossIds": ["loss-o1"]},
    ]

    scored, projection = build_score_impact_projection(
        tasks,
        observations,
        [],
        loss_ledger=ledger,
    )

    assert projection["predictedGainUpper"] < sum(item["scoreImpact"]["upper"] for item in scored)
    assert projection["coveredGapPoints"] == 5.0
