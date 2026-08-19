from app.services.scoring.remediation_planner import build_complete_remediation_map


def loss(
    loss_id,
    observation_code,
    loss_type,
    points,
    *,
    cause_code=None,
    budget_key=None,
    observation_name=None,
):
    return {
        "lossId": loss_id,
        "lossKey": f"rule:{cause_code or f'{observation_code}:{loss_type}'}",
        "causeCode": cause_code or f"{observation_code}:{loss_type}",
        "observationCode": observation_code,
        "observationName": observation_name or observation_code,
        "dimensionCode": "skill_level",
        "lossType": loss_type,
        "points": points,
        "reason": f"{observation_name or observation_code}尚未达到规则要求",
        "evidenceAnchorIds": [1],
        "scoreBudgetKey": budget_key or f"{observation_code}:{loss_type}",
        "actionability": "actionable",
        "requiredInfo": ["对象与场景", "过程与结果"],
        "acceptableEvidence": ["过程记录", "验收材料"],
        "trackDefinition": f"完整满足{observation_name or observation_code}要求并形成证据闭环",
    }


def test_uncovered_losses_receive_deterministic_fallback_tasks():
    losses = [
        loss(f"loss-{index}", f"O{index:02d}", "performance_gap", 2.0)
        for index in range(1, 8)
    ]
    model_tasks = [
        {
            "id": f"model-{index}",
            "title": f"模型任务{index}",
            "method": f"执行整改动作{index}",
            "observationCode": "O01" if index == 1 else None,
        }
        for index in range(1, 7)
    ]

    first = build_complete_remediation_map(action_plan=model_tasks, loss_ledger=losses)
    second = build_complete_remediation_map(action_plan=model_tasks, loss_ledger=losses)

    covered = {loss_id for task in first for loss_id in task["coveredLossIds"]}
    assert covered == {item["lossId"] for item in losses}
    assert len(first) >= 6
    assert [item["taskId"] for item in first] == [item["taskId"] for item in second]
    assert any(item["taskId"].startswith("task-fallback-") for item in first)


def test_tasks_merge_only_when_root_cause_and_action_match():
    losses = [
        loss("l1", "O01", "performance_gap", 2.0),
        loss("l2", "O02", "performance_gap", 3.0),
        loss("l3", "O03", "performance_gap", 4.0),
    ]
    plans = [
        {
            "id": "p1",
            "rootCauseKey": "DEMO_STABILITY",
            "title": "演示稳定性",
            "method": "修复主路径并增加离线备用方案",
            "observationCode": "O02",
        },
        {
            "id": "p2",
            "rootCauseKey": "DEMO_STABILITY",
            "title": "演示稳定性复演",
            "method": "修复主路径并增加离线备用方案",
            "observationCode": "O03",
        },
        {
            "id": "p3",
            "rootCauseKey": "EVIDENCE_CHAIN",
            "title": "演示稳定性",
            "method": "补齐过程记录",
            "observationCode": "O01",
        },
    ]

    tasks = build_complete_remediation_map(action_plan=plans, loss_ledger=losses)

    merged = next(item for item in tasks if item["rootCauseKey"] == "DEMO_STABILITY")
    separate = next(item for item in tasks if item["rootCauseKey"] == "EVIDENCE_CHAIN")
    assert set(merged["coveredLossIds"]) == {"l2", "l3"}
    assert separate["coveredLossIds"] == ["l1"]
    assert merged["taskId"] != separate["taskId"]
    assert len(tasks) == 2


def test_fallback_task_uses_rule_facts_for_both_acceptance_levels():
    tasks = build_complete_remediation_map(
        action_plan=[],
        loss_ledger=[loss("l1", "O01", "evidence_limited", 4.0, observation_name="操作规范性")],
    )

    task = tasks[0]
    assert task["coveredGapPoints"] == 4.0
    assert task["minimumAcceptance"]["summary"] == "对象与场景；过程与结果"
    assert task["minimumAcceptance"]["requiredEvidence"] == ["过程记录", "验收材料"]
    assert task["fullScoreCriteria"]["summary"] == "完整满足操作规范性要求并形成证据闭环"
    assert task["observationCodes"] == ["O01"]

