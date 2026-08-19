import json
from collections import Counter
from pathlib import Path

from app.services.scoring.rule_executor import execute_rule_score
from app.services.scoring.loss_ledger_service import normalize_loss_ledger


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "session_26_scoring_snapshot.json"


def load_session_26_fixture():
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_session_26_fixture_reconciles_to_full_gap():
    fixture = load_session_26_fixture()
    expected = fixture["expected"]

    result = execute_rule_score(fixture["observations"], fixture["deductions"])

    assert result["finalScore"] == expected["currentScore"]
    assert result["reconciliation"]["totalLoss"] == expected["fullGap"]
    assert len(result["observations"]) == expected["observationCount"]
    assert len(result["lossLedger"]) == expected["lossItemCount"]
    assert Counter(item["lossType"] for item in result["lossLedger"]) == expected["lossTypeCounts"]


def test_normalized_loss_items_have_stable_identity_and_budget():
    fixture = load_session_26_fixture()
    rule_result = execute_rule_score(fixture["observations"], fixture["deductions"])

    ledger = normalize_loss_ledger(
        rule_result=rule_result,
        rule_hash=fixture["ruleHash"],
        scoring_fingerprint=fixture["scoringFingerprint"],
    )

    performance = next(item for item in ledger if item["causeCode"] == "O02:performance_gap")
    assert performance["lossId"].startswith("loss-")
    assert performance["lossKey"] == f'{fixture["ruleHash"]}:O02:performance_gap'
    assert performance["scoreBudgetKey"] == "O02:performance_score"
    assert performance["observationName"] == "技能熟练度"
    assert performance["dimensionCode"] == "skill_level"
    assert performance["ruleHash"] == fixture["ruleHash"]
    assert performance["scoringFingerprint"] == fixture["scoringFingerprint"]

    violation = next(item for item in ledger if item["lossType"] == "hard_violation")
    assert violation["scoreBudgetKey"] == "O02:hard_violation:SKILL_DEMO_FAILURE"
    assert violation["deductionId"] == "27-O02-D01"
    assert violation["maxRecoverablePoints"] == 2.0


def test_loss_key_is_stable_but_loss_id_is_report_specific():
    fixture = load_session_26_fixture()
    rule_result = execute_rule_score(fixture["observations"], fixture["deductions"])
    first = normalize_loss_ledger(
        rule_result=rule_result,
        rule_hash=fixture["ruleHash"],
        scoring_fingerprint="report-fingerprint-a",
    )
    second = normalize_loss_ledger(
        rule_result=rule_result,
        rule_hash=fixture["ruleHash"],
        scoring_fingerprint="report-fingerprint-b",
    )

    assert {item["lossKey"] for item in first} == {item["lossKey"] for item in second}
    assert {item["lossId"] for item in first}.isdisjoint({item["lossId"] for item in second})


def test_normalized_loss_carries_rule_acceptance_facts():
    result = execute_rule_score(
        [{
            "observationCode": "O1",
            "observationName": "客户验证",
            "dimensionCode": "market",
            "maxScore": 10,
            "baseScore": 6,
            "scoreCap": 5,
            "trackDefinition": "完整验证客户需求并形成证据闭环",
            "requiredInfo": ["客户对象", "验证结果"],
            "acceptableEvidence": ["访谈原始记录"],
            "trainingTaskTemplate": "补齐客户访谈过程与结果材料",
        }],
        [],
    )

    ledger = normalize_loss_ledger(
        rule_result=result,
        rule_hash="rule",
        scoring_fingerprint="fingerprint",
    )

    assert ledger[0]["trackDefinition"] == "完整验证客户需求并形成证据闭环"
    assert ledger[0]["requiredInfo"] == ["客户对象", "验证结果"]
    assert ledger[0]["acceptableEvidence"] == ["访谈原始记录"]
    assert ledger[0]["trainingTaskTemplate"] == "补齐客户访谈过程与结果材料"
