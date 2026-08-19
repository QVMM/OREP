import json

from app.services.media_evidence.live_finalizer import finalize_live_evidence


def gateway_summary(missing=None):
    missing = list(missing or [])
    return {
        "status": "FINAL",
        "integrityStatus": "incomplete" if missing else "complete",
        "acceptedChunkCount": 10,
        "totalBytes": 320000,
        "missingSequences": missing,
        "timelineCoverage": 0.9 if missing else 1.0,
        "dataHash": "sha256:audio",
    }


def realtime_events():
    return [
        {
            "type": "transcript",
            "text": "临时内容",
            "is_final": False,
            "start": 0,
            "end": 1,
            "source": "realtime",
        },
        {
            "type": "transcript",
            "text": "我们展示核心算法",
            "is_final": True,
            "start": 1,
            "end": 3,
            "source": "realtime",
            "request_id": "r1",
            "overall_score": 99,
        },
    ]


def test_realtime_finalizer_keeps_only_final_score_free_facts():
    package = finalize_live_evidence(
        session_id="live-1",
        transcript_events=realtime_events(),
        visual_frames=[
            {
                "frame_id": "frame-1",
                "timestamp": 2.5,
                "frame_type": "scene_change",
                "diff_score": 0.8,
                "image_path": "/private/path.jpg",
            }
        ],
        gateway_summary=gateway_summary(),
    )

    assert package["sourceType"] == "LIVE_ROADSHOW"
    assert package["status"] == "FINAL"
    assert [item["text"] for item in package["transcriptSegments"]] == [
        "我们展示核心算法"
    ]
    assert package["transcriptSegments"][0]["rawSpeakerId"] is None
    assert package["visualEvidence"][0]["startMs"] == 2500
    assert package["visualEvidence"][0]["sourceRef"] == "visual-frame:frame-1"
    serialized = json.dumps(package, ensure_ascii=False)
    assert "overall_score" not in serialized
    assert "/private/path.jpg" not in serialized
    assert '"score"' not in serialized


def test_offline_final_segments_replace_realtime_provisional_source():
    package = finalize_live_evidence(
        session_id="live-1",
        transcript_events=realtime_events(),
        offline_segments=[
            {
                "start": 1,
                "end": 4,
                "text": "离线终版转写",
                "speaker_id": 2,
            }
        ],
        visual_frames=[],
        gateway_summary=gateway_summary(),
    )

    assert [item["text"] for item in package["transcriptSegments"]] == ["离线终版转写"]
    assert package["transcriptSegments"][0]["rawSpeakerId"] == "SPEAKER_2"
    assert package["integrity"]["transcriptSource"] == "offline_final"


def test_duplicate_realtime_final_events_are_deduplicated_stably():
    events = realtime_events()
    events.append(dict(events[-1]))

    package = finalize_live_evidence(
        session_id="live-1",
        transcript_events=events,
        visual_frames=[],
        gateway_summary=gateway_summary(),
    )

    assert len(package["transcriptSegments"]) == 1


def test_gateway_gap_marks_evidence_incomplete_without_creating_a_score():
    package = finalize_live_evidence(
        session_id="live-1",
        transcript_events=realtime_events(),
        visual_frames=[],
        gateway_summary=gateway_summary([3, 4]),
    )

    assert package["integrity"]["evidenceStatus"] == "evidence_incomplete"
    assert package["integrity"]["missingAudioSequences"] == [3, 4]
    assert package["integrity"]["audioCoverage"] == 0.9


def test_processing_metrics_do_not_change_snapshot_hash():
    first = finalize_live_evidence(
        session_id="live-1",
        transcript_events=realtime_events(),
        visual_frames=[],
        gateway_summary=gateway_summary(),
        processing_metrics={"durationMs": 100, "requestId": "one"},
    )
    second = finalize_live_evidence(
        session_id="live-1",
        transcript_events=realtime_events(),
        visual_frames=[],
        gateway_summary=gateway_summary(),
        processing_metrics={"durationMs": 900, "requestId": "two"},
    )

    assert first["snapshotHash"] == second["snapshotHash"]


def test_visual_pts_is_mapped_to_audio_clock_and_raw_pts_remains_auditable():
    summary = gateway_summary()
    summary["mediaClock"] = {
        "clockId": "clock-live-1",
        "masterSource": "AUDIO_SAMPLE_CLOCK",
        "sampleRate": 16000,
        "severeDriftMs": 500,
        "audioChunks": [],
        "nextSample": 16000,
    }

    package = finalize_live_evidence(
        session_id="live-1",
        transcript_events=realtime_events(),
        visual_frames=[
            {
                "frame_id": "frame-clocked",
                "timestamp": 1.5,
                "raw_pts": 135000,
                "pts_timebase_num": 1,
                "pts_timebase_den": 90000,
                "observed_audio_sample": 16000,
            }
        ],
        gateway_summary=summary,
    )

    frame = package["visualEvidence"][0]
    assert frame["rawPts"] == 135000
    assert frame["rawPtsMs"] == 1500
    assert frame["startMs"] == 1000
    assert frame["mappedMs"] == 1000
    assert frame["driftMs"] == 500
    assert frame["syncStatus"] == "DEGRADED"
    assert package["integrity"]["mediaSyncStatus"] == "DEGRADED"
    assert package["integrity"]["maxObservedDriftMs"] == 500
    assert package["integrity"]["evidenceStatus"] == "evidence_incomplete"


def test_realtime_segment_revisions_are_monotonic_and_final_is_terminal():
    events = [
        {
            "type": "transcript",
            "segmentId": "seg-1",
            "revision": 1,
            "text": "暂定第一版",
            "is_final": False,
            "start": 0,
            "end": 1,
            "observedAtMs": 1000,
        },
        {
            "type": "transcript",
            "segmentId": "seg-1",
            "revision": 2,
            "text": "可信终版",
            "is_final": True,
            "start": 0,
            "end": 1.2,
            "observedAtMs": 2000,
        },
        {
            "type": "transcript",
            "segmentId": "seg-1",
            "revision": 3,
            "text": "迟到的暂定覆盖",
            "is_final": False,
            "start": 0,
            "end": 1.3,
            "observedAtMs": 3000,
        },
        {
            "type": "transcript",
            "segmentId": "seg-2",
            "revision": 1,
            "text": "从未终结的暂定内容",
            "is_final": False,
            "start": 2,
            "end": 3,
            "observedAtMs": 4000,
        },
    ]

    package = finalize_live_evidence(
        session_id="live-1",
        transcript_events=events,
        visual_frames=[],
        gateway_summary=gateway_summary(),
    )

    assert [item["text"] for item in package["transcriptSegments"]] == ["可信终版"]
