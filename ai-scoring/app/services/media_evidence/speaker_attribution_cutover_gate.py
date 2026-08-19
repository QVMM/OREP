"""Machine-readable rollout gate for public speaker attribution.

Model confidence is deliberately not treated as accuracy. Accuracy inputs must
come from independently labeled time spans; missing truth always produces a
NO_GO decision.
"""

from __future__ import annotations

from typing import Iterable, Mapping


HIGH_CONFIDENCE_THRESHOLD = 0.85
MAX_EXTERNAL_TO_CONTESTANT_FALSE_RATE = 0.01
MIN_HIGH_CONFIDENCE_ACCURACY = 0.95
MIN_HIGH_CONFIDENCE_COVERAGE = 0.50
MIN_LABELED_DURATION_MS = 600_000
MAX_LIVE_P95_MS = 3_000
MAX_UPLOAD_BRANCH_MS = 720_000


def evaluate_labeled_accuracy(samples: Iterable[Mapping]) -> dict:
    """Calculate duration-weighted metrics from independent ground truth."""

    annotated_ms = 0
    rejected_ms = 0
    high_confidence_ms = 0
    high_confidence_correct_ms = 0
    external_truth_ms = 0
    external_to_contestant_false_ms = 0

    for sample in samples:
        duration_ms = max(0, int(sample.get("durationMs") or 0))
        if not duration_ms:
            continue
        truth_type = str(sample.get("truthPersonType") or "").upper()
        truth_id = _text_or_none(sample.get("truthPersonId"))
        predicted_type = str(sample.get("predictedPersonType") or "").upper()
        predicted_id = _text_or_none(sample.get("predictedPersonId"))
        speaker_state = str(sample.get("speakerState") or "").upper()
        confidence = _bounded_float(sample.get("confidence"))

        annotated_ms += duration_ms
        rejected = speaker_state in {"UNKNOWN", "OVERLAP"} or not predicted_type
        if rejected:
            rejected_ms += duration_ms

        if truth_type in {"VISITOR", "OFFSCREEN", "EXTERNAL"}:
            external_truth_ms += duration_ms
            if predicted_type == "CONTESTANT":
                external_to_contestant_false_ms += duration_ms

        is_high_confidence = not rejected and confidence >= HIGH_CONFIDENCE_THRESHOLD
        if is_high_confidence:
            high_confidence_ms += duration_ms
            if truth_type == predicted_type and truth_id == predicted_id:
                high_confidence_correct_ms += duration_ms

    return {
        "source": "INDEPENDENT_LABELED_TIMELINE",
        "annotatedDurationMs": annotated_ms,
        "rejectedDurationMs": rejected_ms,
        "rejectionCoverage": _ratio(rejected_ms, annotated_ms),
        "highConfidenceDurationMs": high_confidence_ms,
        "highConfidenceCoverage": _ratio(high_confidence_ms, annotated_ms),
        "highConfidenceCorrectDurationMs": high_confidence_correct_ms,
        "highConfidenceAccuracy": _ratio(
            high_confidence_correct_ms, high_confidence_ms
        ),
        "externalTruthDurationMs": external_truth_ms,
        "externalToContestantFalseDurationMs": external_to_contestant_false_ms,
        "externalToContestantFalseAttributionRate": _ratio(
            external_to_contestant_false_ms, external_truth_ms
        ),
    }


def evaluate_speaker_attribution_cutover(
    *,
    labeled_accuracy: Mapping | None,
    performance: Mapping | None,
    reliability: Mapping | None,
    contestant_duplicate_count: int,
) -> dict:
    """Return an auditable GO/NO_GO decision without changing feature flags."""

    failures: list[str] = []
    accuracy = dict(labeled_accuracy or {})
    performance_value = dict(performance or {})
    reliability_value = dict(reliability or {})

    if not labeled_accuracy:
        failures.append("LABELED_ACCURACY_UNAVAILABLE")
    else:
        if int(accuracy.get("annotatedDurationMs") or 0) < MIN_LABELED_DURATION_MS:
            failures.append("LABELED_DURATION_BELOW_600000_MS")
        if (
            float(accuracy.get("externalToContestantFalseAttributionRate") or 0.0)
            >= MAX_EXTERNAL_TO_CONTESTANT_FALSE_RATE
        ):
            failures.append(
                "EXTERNAL_TO_CONTESTANT_FALSE_ATTRIBUTION_AT_OR_ABOVE_1_PERCENT"
            )
        if (
            float(accuracy.get("highConfidenceAccuracy") or 0.0)
            < MIN_HIGH_CONFIDENCE_ACCURACY
        ):
            failures.append("HIGH_CONFIDENCE_ACCURACY_BELOW_95_PERCENT")
        if (
            float(accuracy.get("highConfidenceCoverage") or 0.0)
            < MIN_HIGH_CONFIDENCE_COVERAGE
        ):
            failures.append("HIGH_CONFIDENCE_COVERAGE_BELOW_50_PERCENT")

    live_p95_ms = _non_negative_int(performance_value.get("liveP95Ms"))
    upload_branch_ms = _non_negative_int(performance_value.get("uploadBranchMs"))
    if live_p95_ms is None:
        failures.append("LIVE_P95_UNAVAILABLE")
    elif live_p95_ms > MAX_LIVE_P95_MS:
        failures.append("LIVE_P95_EXCEEDS_3000_MS")
    if upload_branch_ms is None:
        failures.append("UPLOAD_BRANCH_RUNTIME_UNAVAILABLE")
    elif upload_branch_ms > MAX_UPLOAD_BRANCH_MS:
        failures.append("UPLOAD_BRANCH_EXCEEDS_720000_MS")

    for field, failure in (
        ("terminalProtectionPassed", "TERMINAL_PROTECTION_FAILED"),
        ("callbackReplayPassed", "CALLBACK_REPLAY_FAILED"),
        ("workerRecoveryPassed", "WORKER_RECOVERY_FAILED"),
    ):
        if reliability_value.get(field) is not True:
            failures.append(failure)

    if max(0, int(contestant_duplicate_count or 0)) > 0:
        failures.append("DUPLICATE_CONTESTANT_IDENTITIES")

    failures = list(dict.fromkeys(failures))
    allowed = not failures
    return {
        "contractVersion": "speaker-attribution-cutover-gate-v1",
        "decision": "GO" if allowed else "NO_GO",
        "publicCutoverAllowed": allowed,
        "failureReasons": failures,
        "thresholds": {
            "highConfidence": HIGH_CONFIDENCE_THRESHOLD,
            "maximumExternalToContestantFalseAttributionRate": MAX_EXTERNAL_TO_CONTESTANT_FALSE_RATE,
            "minimumHighConfidenceAccuracy": MIN_HIGH_CONFIDENCE_ACCURACY,
            "minimumHighConfidenceCoverage": MIN_HIGH_CONFIDENCE_COVERAGE,
            "minimumLabeledDurationMs": MIN_LABELED_DURATION_MS,
            "maximumLiveP95Ms": MAX_LIVE_P95_MS,
            "maximumUploadBranchMs": MAX_UPLOAD_BRANCH_MS,
        },
        "accuracy": accuracy or None,
        "performance": {
            **performance_value,
            "liveP95Ms": live_p95_ms,
            "uploadBranchMs": upload_branch_ms,
        },
        "reliability": reliability_value,
        "contestantDuplicateCount": max(0, int(contestant_duplicate_count or 0)),
        "switchMutationPerformed": False,
    }


def simulate_one_hour_live_transport(
    *,
    input_fps: int = 25,
    target_fps: int = 6,
    drain_every_ms: int = 1_000,
    interrupt_at_ms: int | None = None,
) -> dict:
    """Exercise a one-hour media clock without claiming model-level latency.

    This intentionally measures only the bounded camera transport that exists
    today. The returned model latency is ``None`` until a real incremental
    attribution consumer is connected and measured.
    """

    from .live_camera_subscriber import LiveCameraSubscriber

    duration_ms = 3_600_000
    input_fps = max(1, int(input_fps))
    frame_interval_ms = 1_000 / input_fps
    drain_every_ms = max(1, int(drain_every_ms))
    subscriber = LiveCameraSubscriber(
        clock_id="cutover-gate-one-hour",
        target_fps=target_fps,
        max_backlog_ms=3_000,
        max_queue_frames=max(8, target_fps * 4),
    )
    subscriber.mark_connected("connection-1")
    input_frames = 0
    accepted_frames = 0
    maximum_queue = 0
    next_drain_ms = drain_every_ms
    interrupted = False

    timestamp_ms = 0.0
    while timestamp_ms < duration_ms:
        rounded_ms = round(timestamp_ms)
        if (
            interrupt_at_ms is not None
            and not interrupted
            and rounded_ms >= int(interrupt_at_ms)
        ):
            subscriber.mark_reconnecting()
            subscriber.mark_connected(
                "connection-2", clock_id="cutover-gate-one-hour"
            )
            interrupted = True
        accepted = subscriber.ingest_frame(
            track_id="camera-1",
            source="camera",
            raw_pts=rounded_ms * 90,
            pts_timebase_num=1,
            pts_timebase_den=90_000,
            received_at_ms=timestamp_ms,
            payload=b"frame",
            is_key_frame=rounded_ms % 10_000 == 0,
        )
        input_frames += 1
        accepted_frames += int(accepted)
        maximum_queue = max(
            maximum_queue, subscriber.status()["queuedFrameCount"]
        )
        if timestamp_ms >= next_drain_ms:
            subscriber.drain()
            next_drain_ms += drain_every_ms
        timestamp_ms += frame_interval_ms

    subscriber.drain()
    final = subscriber.stop()
    return {
        "contractVersion": "speaker-attribution-live-transport-gate-v1",
        "mediaDurationMs": duration_ms,
        "inputFrameCount": input_frames,
        "acceptedFrameCount": accepted_frames,
        "targetFps": subscriber.target_fps,
        "maximumQueuedFrameCount": maximum_queue,
        "droppedFrameCount": final["droppedFrameCount"],
        "reconnectCount": final["reconnectCount"],
        "audioMayContinue": final["audioMayContinue"],
        "integrityStatus": final["integrityStatus"],
        "endToEndAttributionP95Ms": None,
        "attributionLatencyStatus": "NOT_MEASURABLE_PATH_NOT_CONNECTED",
    }


def _text_or_none(value) -> str | None:
    text = str(value or "").strip()
    return text or None


def _bounded_float(value) -> float:
    try:
        return min(1.0, max(0.0, float(value or 0.0)))
    except (TypeError, ValueError):
        return 0.0


def _non_negative_int(value) -> int | None:
    if value is None or value == "":
        return None
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return None


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 6)
