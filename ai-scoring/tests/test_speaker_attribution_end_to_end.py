from app.services.media_evidence.speaker_attribution_cutover_gate import (
    evaluate_labeled_accuracy,
    evaluate_speaker_attribution_cutover,
    simulate_one_hour_live_transport,
)


def _sample(
    *,
    duration_ms=10_000,
    truth_type="CONTESTANT",
    truth_id="PERSON_1",
    predicted_type="CONTESTANT",
    predicted_id="PERSON_1",
    confidence=0.96,
    state="CONFIRMED",
):
    return {
        "durationMs": duration_ms,
        "truthPersonType": truth_type,
        "truthPersonId": truth_id,
        "predictedPersonType": predicted_type,
        "predictedPersonId": predicted_id,
        "confidence": confidence,
        "speakerState": state,
    }


def test_cutover_passes_only_when_accuracy_performance_and_reliability_all_pass():
    samples = [
        _sample(duration_ms=400_000),
        _sample(
            duration_ms=200_000,
            truth_type="VISITOR",
            truth_id="VISITOR_1",
            predicted_type="VISITOR",
            predicted_id="VISITOR_1",
        ),
        _sample(
            duration_ms=100_000,
            truth_type="OFFSCREEN",
            truth_id="OFFSCREEN_1",
            predicted_type="OFFSCREEN",
            predicted_id="OFFSCREEN_1",
            confidence=0.91,
        ),
        _sample(
            duration_ms=300_000,
            truth_type="CONTESTANT",
            truth_id="PERSON_2",
            predicted_type=None,
            predicted_id=None,
            confidence=0.2,
            state="UNKNOWN",
        ),
    ]
    result = evaluate_speaker_attribution_cutover(
        labeled_accuracy=evaluate_labeled_accuracy(samples),
        performance={"liveP95Ms": 2_400, "uploadBranchMs": 690_000},
        reliability={
            "terminalProtectionPassed": True,
            "callbackReplayPassed": True,
            "workerRecoveryPassed": True,
        },
        contestant_duplicate_count=0,
    )

    assert result["decision"] == "GO"
    assert result["publicCutoverAllowed"] is True
    assert result["failureReasons"] == []
    assert result["accuracy"]["rejectionCoverage"] == 0.3


def test_cutover_blocks_when_labeled_truth_is_missing_even_if_model_is_confident():
    result = evaluate_speaker_attribution_cutover(
        labeled_accuracy=None,
        performance={"liveP95Ms": 1_000, "uploadBranchMs": 60_000},
        reliability={
            "terminalProtectionPassed": True,
            "callbackReplayPassed": True,
            "workerRecoveryPassed": True,
        },
        contestant_duplicate_count=0,
    )

    assert result["decision"] == "NO_GO"
    assert result["publicCutoverAllowed"] is False
    assert "LABELED_ACCURACY_UNAVAILABLE" in result["failureReasons"]


def test_cutover_cannot_hide_bad_coverage_behind_perfect_accuracy():
    samples = [
        _sample(duration_ms=10_000),
        _sample(
            duration_ms=990_000,
            predicted_type=None,
            predicted_id=None,
            confidence=0.1,
            state="UNKNOWN",
        ),
    ]
    accuracy = evaluate_labeled_accuracy(samples)
    result = evaluate_speaker_attribution_cutover(
        labeled_accuracy=accuracy,
        performance={"liveP95Ms": 2_500, "uploadBranchMs": 700_000},
        reliability={
            "terminalProtectionPassed": True,
            "callbackReplayPassed": True,
            "workerRecoveryPassed": True,
        },
        contestant_duplicate_count=0,
    )

    assert accuracy["highConfidenceAccuracy"] == 1.0
    assert accuracy["highConfidenceCoverage"] == 0.01
    assert "HIGH_CONFIDENCE_COVERAGE_BELOW_50_PERCENT" in result["failureReasons"]


def test_cutover_blocks_external_people_misattributed_to_contestants_and_slow_paths():
    samples = [
        _sample(duration_ms=500_000),
        _sample(
            duration_ms=100_000,
            truth_type="VISITOR",
            truth_id="VISITOR_1",
            predicted_type="CONTESTANT",
            predicted_id="PERSON_1",
        ),
    ]
    result = evaluate_speaker_attribution_cutover(
        labeled_accuracy=evaluate_labeled_accuracy(samples),
        performance={"liveP95Ms": 3_001, "uploadBranchMs": 720_001},
        reliability={
            "terminalProtectionPassed": False,
            "callbackReplayPassed": True,
            "workerRecoveryPassed": True,
        },
        contestant_duplicate_count=1,
    )

    assert result["decision"] == "NO_GO"
    assert set(result["failureReasons"]) >= {
        "EXTERNAL_TO_CONTESTANT_FALSE_ATTRIBUTION_AT_OR_ABOVE_1_PERCENT",
        "HIGH_CONFIDENCE_ACCURACY_BELOW_95_PERCENT",
        "LIVE_P95_EXCEEDS_3000_MS",
        "UPLOAD_BRANCH_EXCEEDS_720000_MS",
        "TERMINAL_PROTECTION_FAILED",
        "DUPLICATE_CONTESTANT_IDENTITIES",
    }


def test_one_hour_live_transport_stays_bounded_but_does_not_invent_model_latency():
    result = simulate_one_hour_live_transport(
        input_fps=25,
        target_fps=6,
        drain_every_ms=1_000,
        interrupt_at_ms=1_800_000,
    )

    assert result["mediaDurationMs"] == 3_600_000
    assert 21_000 <= result["acceptedFrameCount"] <= 22_000
    assert result["maximumQueuedFrameCount"] <= 8
    assert result["reconnectCount"] == 1
    assert result["audioMayContinue"] is True
    assert result["endToEndAttributionP95Ms"] is None
    assert result["attributionLatencyStatus"] == "NOT_MEASURABLE_PATH_NOT_CONNECTED"
