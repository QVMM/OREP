from app.services.scoring.coverage_validator import validate_remediation_coverage


def ledger_item(loss_id, points, budget_key):
    return {
        "lossId": loss_id,
        "points": points,
        "scoreBudgetKey": budget_key,
    }


def task(task_id, *loss_ids):
    return {"taskId": task_id, "coveredLossIds": list(loss_ids)}


def test_complete_coverage_reconciles_unique_loss_points():
    summary = validate_remediation_coverage(
        current_score=49.5,
        loss_ledger=[
            ledger_item("l1", 20.0, "O1:performance"),
            ledger_item("l2", 30.5, "O2:evidence"),
        ],
        tasks=[task("t1", "l1"), task("t2", "l2")],
        rule_hash="rule-hash",
        scoring_fingerprint="fingerprint",
    )

    assert summary["fullGap"] == 50.5
    assert summary["ledgerPoints"] == 50.5
    assert summary["coveredGapPoints"] == 50.5
    assert summary["coverageRate"] == 1.0
    assert summary["uncoveredLossIds"] == []
    assert summary["unresolvedDuplicateBudgetKeys"] == []
    assert summary["status"] == "complete"


def test_missing_loss_keeps_portfolio_incomplete():
    summary = validate_remediation_coverage(
        current_score=90,
        loss_ledger=[ledger_item("l1", 4, "b1"), ledger_item("l2", 6, "b2")],
        tasks=[task("t1", "l1")],
    )

    assert summary["coveredLossItemCount"] == 1
    assert summary["coveredGapPoints"] == 4.0
    assert summary["coverageRate"] == 0.5
    assert summary["uncoveredLossIds"] == ["l2"]
    assert summary["status"] == "incomplete"


def test_reconciliation_error_or_duplicate_budget_keeps_portfolio_incomplete():
    summary = validate_remediation_coverage(
        current_score=89,
        loss_ledger=[
            ledger_item("l1", 5, "shared-budget"),
            ledger_item("l2", 5, "shared-budget"),
        ],
        tasks=[task("t1", "l1", "l2")],
    )

    assert summary["reconciliationError"] == -1.0
    assert summary["unresolvedDuplicateBudgetKeys"] == ["shared-budget"]
    assert summary["status"] == "incomplete"

