import unittest

from app.services.scoring.rule_executor import execute_rule_score


def observation(code, dimension, *, max_score, base_score, score_cap):
    return {
        "observationCode": code,
        "dimensionCode": dimension,
        "maxScore": max_score,
        "baseScore": base_score,
        "scoreCap": score_cap,
    }


def deduction(
    code,
    observation_code,
    points,
    *,
    status="new",
    max_recoverable=None,
    score_effect="subtractive",
    cause_code=None,
):
    item = {
        "deductionId": code,
        "observationCode": observation_code,
        "deductedPoints": points,
        "maxRecoverablePoints": points if max_recoverable is None else max_recoverable,
        "status": status,
        "scoreEffect": score_effect,
    }
    if cause_code is not None:
        item["causeCode"] = cause_code
    return item


class AuthoritativeRuleExecutorTest(unittest.TestCase):
    def test_calculates_from_pre_deduction_base_score(self):
        result = execute_rule_score(
            [observation("O1", "D1", max_score=20, base_score=16, score_cap=18)],
            [deduction("D-1", "O1", 3)],
        )

        self.assertEqual(result["finalScore"], 13.0)
        self.assertEqual(result["deductedScore"], 3.0)
        self.assertEqual(result["observations"][0]["baseScore"], 16.0)


    def test_applies_evidence_cap_after_recovery(self):
        result = execute_rule_score(
            [observation("O1", "D1", max_score=20, base_score=19, score_cap=14)],
            [deduction("D-1", "O1", 4, max_recoverable=3)],
            [{"sourceDeductionId": "D-1", "recoveryStatus": "verified", "requestedRecoverPoints": 3}],
        )

        self.assertEqual(result["recoveredScore"], 3.0)
        self.assertEqual(result["finalScore"], 13.0)
        self.assertEqual(result["observations"][0]["effectiveHardPenalty"], 1.0)


    def test_excludes_invalid_and_recovered_current_deductions(self):
        result = execute_rule_score(
            [observation("O1", "D1", max_score=20, base_score=18, score_cap=20)],
            [
                deduction("D-1", "O1", 4, status="invalid"),
                deduction("D-2", "O1", 5, status="recovered"),
            ],
        )

        self.assertEqual(result["deductedScore"], 0.0)
        self.assertEqual(result["finalScore"], 18.0)


    def test_clamps_deductions_to_the_available_base_score(self):
        result = execute_rule_score(
            [observation("O1", "D1", max_score=10, base_score=6, score_cap=10)],
            [deduction("D-1", "O1", 9)],
        )

        self.assertEqual(result["deductedScore"], 6.0)
        self.assertEqual(result["finalScore"], 0.0)


    def test_hard_penalty_order_is_stable_when_input_shuffled(self):
        obs = observation("O1", "D1", max_score=20, base_score=12, score_cap=12)
        left = [
            deduction("D-small", "O1", 3, cause_code="O1:small"),
            deduction("D-large", "O1", 10, cause_code="O1:large"),
        ]
        right = list(reversed(left))

        first = execute_rule_score([obs], left)
        second = execute_rule_score([obs], right)

        self.assertEqual(first["finalScore"], second["finalScore"])
        self.assertEqual(first["deductedScore"], second["deductedScore"])
        self.assertEqual(first["effectiveHardPenalty"], second["effectiveHardPenalty"])
        self.assertEqual(
            [row["causeCode"] for row in first["lossLedger"] if row["lossType"] == "hard_violation"],
            [row["causeCode"] for row in second["lossLedger"] if row["lossType"] == "hard_violation"],
        )
        # Larger penalty is applied first, so it consumes the available score.
        self.assertEqual(
            [row["causeCode"] for row in first["lossLedger"] if row["lossType"] == "hard_violation"],
            ["O1:large", "O1:small"],
        )


    def test_returns_dimension_totals_and_reconciliation_totals(self):
        result = execute_rule_score(
            [
                observation("O1", "D1", max_score=20, base_score=16, score_cap=18),
                observation("O2", "D1", max_score=10, base_score=8, score_cap=8),
                observation("O3", "D2", max_score=15, base_score=12, score_cap=10),
            ],
            [deduction("D-1", "O1", 2)],
        )

        self.assertEqual(result["dimensionScores"], {"D1": 22.0, "D2": 10.0})
        self.assertEqual(result["dimensionMaxScores"], {"D1": 30.0, "D2": 15.0})
        self.assertEqual(result["finalScore"], 32.0)
        self.assertEqual(result["reconciliation"], {
            "ruleMaxScore": 45.0,
            "baseScore": 36.0,
            "performanceGap": 9.0,
            "evidenceLimitedGap": 2.0,
            "deductedScore": 2.0,
            "recoveredScore": 0.0,
            "effectiveHardPenalty": 2.0,
            "currentScoreCap": 36.0,
            "totalLoss": 13.0,
            "finalScore": 32.0,
            "dimensionScoreTotal": 32.0,
        })


    def test_rejects_duplicate_observation_codes(self):
        with self.assertRaisesRegex(ValueError, "duplicate observationCode O1"):
            execute_rule_score(
                [
                    observation("O1", "D1", max_score=10, base_score=8, score_cap=10),
                    observation("O1", "D2", max_score=10, base_score=7, score_cap=10),
                ],
                [],
            )

    def test_evidence_gap_diagnostic_does_not_subtract_twice(self):
        source_observation = observation("O1", "D1", max_score=20, base_score=16, score_cap=14)
        source_observation["observationName"] = "客户验证"
        result = execute_rule_score(
            [source_observation],
            [deduction(
                "D-1-evidence-gap",
                "O1",
                3,
                score_effect="diagnostic_only",
            )],
        )

        scored = result["observations"][0]
        self.assertEqual(result["scorePolicyVersion"], "score-policy-v2-single-attribution")
        self.assertEqual(result["finalScore"], 14.0)
        self.assertEqual(result["deductedScore"], 0.0)
        self.assertEqual(scored["performanceGap"], 4.0)
        self.assertEqual(scored["evidenceLimitedGap"], 2.0)
        self.assertEqual(scored["effectiveHardPenalty"], 0.0)
        self.assertEqual(sum(row["points"] for row in result["lossLedger"]), 6.0)
        self.assertEqual(result["lossLedger"][0]["observationName"], "客户验证")
        self.assertEqual(result["lossLedger"][0]["dimensionCode"], "D1")
        self.assertEqual(result["reconciliation"]["ruleMaxScore"], 20.0)
        self.assertEqual(result["reconciliation"]["totalLoss"], 6.0)

    def test_explicit_hard_violation_subtracts_once_and_reconciles(self):
        result = execute_rule_score(
            [observation("O1", "D1", max_score=20, base_score=16, score_cap=14)],
            [deduction(
                "D-1-timeout",
                "O1",
                3,
                score_effect="subtractive",
                cause_code="EVENT:TIMEOUT:O1",
            )],
        )

        scored = result["observations"][0]
        self.assertEqual(result["finalScore"], 11.0)
        self.assertEqual(scored["effectiveHardPenalty"], 3.0)
        self.assertEqual(result["reconciliation"]["totalLoss"], 9.0)
        self.assertEqual(
            {row["lossType"] for row in result["lossLedger"]},
            {"performance_gap", "evidence_limited", "hard_violation"},
        )

    def test_rejects_duplicate_hard_violation_cause_codes(self):
        with self.assertRaisesRegex(ValueError, "duplicate causeCode EVENT:TIMEOUT"):
            execute_rule_score(
                [observation("O1", "D1", max_score=20, base_score=16, score_cap=20)],
                [
                    deduction("D-1", "O1", 2, cause_code="EVENT:TIMEOUT"),
                    deduction("D-2", "O1", 1, cause_code="EVENT:TIMEOUT"),
                ],
            )

    def test_rejects_performance_score_above_observation_maximum(self):
        with self.assertRaisesRegex(ValueError, "baseScore must be between 0 and maxScore"):
            execute_rule_score(
                [observation("O1", "D1", max_score=10, base_score=11, score_cap=10)],
                [],
            )


if __name__ == "__main__":
    unittest.main()
