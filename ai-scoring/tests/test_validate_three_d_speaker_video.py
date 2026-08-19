from scripts.validate_3d_speaker_video import build_parser, evaluate_publication_gate


def _provider(turns, *, rss=1_500_000_000, processing_ms=1000):
    return {
        "status": "completed",
        "turns": turns,
        "diagnostics": {"peakRssBytes": rss, "processingDurationMs": processing_ms},
    }


def _snapshot(*, anchored=4, coverage=0.9, conflicts=0, anonymous=0):
    people = [
        {"personType": "CONTESTANT", "contestantSlot": index}
        for index in range(1, anchored + 1)
    ] + [{"personType": "VISITOR", "contestantSlot": None} for _ in range(anonymous)]
    return {
        "people": people,
        "diagnostics": {
            "anchoredContestantCount": anchored,
            "transcriptCoverageRatio": coverage,
            "introductionConflictCount": conflicts,
            "anonymousPersonCount": anonymous,
        },
    }


def test_gate_passes_four_anchored_contestants_and_named_outsider_state():
    report = evaluate_publication_gate(
        provider_result=_provider([
            {"startMs": 0, "endMs": 1000},
            {"startMs": 1000, "endMs": 2000},
        ]),
        snapshot=_snapshot(anonymous=1),
        duration_ms=2000,
        expected_visible_contestants=4,
        minimum_transcript_coverage=0.85,
        maximum_peak_rss_bytes=4_000_000_000,
        maximum_processing_ms=2_400_000,
    )

    assert report["passed"] is True
    assert report["checks"]["contestantAnchors"]["passed"] is True
    assert report["checks"]["anonymousPeopleAreExplicit"] == {"passed": True, "count": 1}


def test_gate_fails_invented_or_incomplete_identity_timeline_and_resource_overrun():
    report = evaluate_publication_gate(
        provider_result=_provider([
            {"startMs": 500, "endMs": 2500},
            {"startMs": 100, "endMs": 200},
        ], rss=5_000_000_000),
        snapshot=_snapshot(anchored=3, coverage=0.7, conflicts=1),
        duration_ms=2000,
        expected_visible_contestants=4,
        minimum_transcript_coverage=0.85,
        maximum_peak_rss_bytes=4_000_000_000,
    )

    assert report["passed"] is False
    assert report["checks"]["contestantAnchors"]["passed"] is False
    assert report["checks"]["timelineBounds"]["passed"] is False
    assert report["checks"]["monotonicTimeline"]["passed"] is False
    assert report["checks"]["resourceCeiling"]["passed"] is False
    assert report["checks"]["introductionConflicts"]["passed"] is False


def test_provider_failure_fails_without_using_processing_time_as_a_gate():
    provider = _provider(
        [{"startMs": 0, "endMs": 2000}],
        processing_ms=989_695,
    )
    provider["status"] = "failed"
    report = evaluate_publication_gate(
        provider_result=provider,
        snapshot=_snapshot(),
        duration_ms=3_270_792,
        expected_visible_contestants=4,
        minimum_transcript_coverage=0.85,
        maximum_peak_rss_bytes=4_000_000_000,
    )

    assert report["passed"] is False
    assert report["checks"]["providerCompleted"]["status"] == "failed"
    assert "processingLatency" not in report["checks"]


def test_forty_minutes_is_only_the_worker_watchdog_not_a_publication_gate():
    args = build_parser().parse_args([
        "--video", "video.mp4",
        "--session-result", "result.json",
        "--output", "validation.json",
    ])

    assert args.maximum_processing_minutes == 40.0

    report = evaluate_publication_gate(
        provider_result=_provider(
            [{"startMs": 0, "endMs": 2000}],
            processing_ms=989_695,
        ),
        snapshot=_snapshot(),
        duration_ms=3_270_792,
        expected_visible_contestants=4,
        minimum_transcript_coverage=0.85,
        maximum_peak_rss_bytes=4_000_000_000,
        maximum_processing_ms=2_400_000,
    )

    assert report["passed"] is True
    assert "processingLatency" not in report["checks"]
