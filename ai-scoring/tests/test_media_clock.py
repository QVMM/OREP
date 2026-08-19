import pytest

from app.services.media_evidence.media_clock import (
    MediaClock,
    MediaClockError,
    ProvisionalSegmentLedger,
)


def test_live_audio_sample_clock_is_authoritative_for_chunk_timestamps():
    clock = MediaClock(
        clock_id="clock-live-1",
        master_source="AUDIO_SAMPLE_CLOCK",
        sample_rate=16_000,
    )

    mapped = clock.record_audio_chunk(
        sequence=0,
        start_sample=0,
        sample_count=16_000,
        declared_start_ms=17,
        declared_end_ms=1_019,
    )

    assert mapped == {
        "clockId": "clock-live-1",
        "sequence": 0,
        "startSample": 0,
        "endSample": 16_000,
        "sampleCount": 16_000,
        "startMs": 0,
        "endMs": 1_000,
        "declaredStartMs": 17,
        "declaredEndMs": 1_019,
        "declaredDriftMs": 19,
        "syncStatus": "SYNCED",
    }


def test_live_video_pts_keeps_raw_value_and_maps_to_audio_master_clock():
    clock = MediaClock(
        clock_id="clock-live-1",
        master_source="AUDIO_SAMPLE_CLOCK",
        sample_rate=16_000,
        severe_drift_ms=500,
    )

    mapped = clock.map_video_pts(
        raw_pts=90_000,
        timebase_num=1,
        timebase_den=90_000,
        observed_audio_sample=16_000,
    )

    assert mapped == {
        "clockId": "clock-live-1",
        "rawPts": 90_000,
        "ptsTimebaseNum": 1,
        "ptsTimebaseDen": 90_000,
        "rawPtsMs": 1_000,
        "mappedMs": 1_000,
        "driftMs": 0,
        "syncStatus": "SYNCED",
    }


def test_severe_video_drift_is_explicitly_degraded_without_rewriting_raw_pts():
    clock = MediaClock(
        clock_id="clock-live-1",
        master_source="AUDIO_SAMPLE_CLOCK",
        sample_rate=16_000,
        severe_drift_ms=500,
    )

    mapped = clock.map_video_pts(
        raw_pts=135_000,
        timebase_num=1,
        timebase_den=90_000,
        observed_audio_sample=16_000,
    )

    assert mapped["rawPts"] == 135_000
    assert mapped["rawPtsMs"] == 1_500
    assert mapped["mappedMs"] == 1_000
    assert mapped["driftMs"] == 500
    assert mapped["syncStatus"] == "DEGRADED"


def test_upload_media_pts_is_the_master_clock():
    clock = MediaClock(
        clock_id="clock-upload-1",
        master_source="MEDIA_PTS",
    )

    mapped = clock.map_video_pts(
        raw_pts=225_000,
        timebase_num=1,
        timebase_den=90_000,
    )

    assert mapped["rawPtsMs"] == 2_500
    assert mapped["mappedMs"] == 2_500
    assert mapped["driftMs"] == 0
    assert mapped["syncStatus"] == "SYNCED"


def test_clock_snapshot_preserves_identity_and_sample_cursor_across_reconnect():
    first = MediaClock(
        clock_id="clock-live-1",
        master_source="AUDIO_SAMPLE_CLOCK",
        sample_rate=16_000,
    )
    first.record_audio_chunk(sequence=0, start_sample=0, sample_count=8_000)

    recovered = MediaClock.from_snapshot(first.snapshot())

    assert recovered.clock_id == "clock-live-1"
    assert recovered.next_sample == 8_000
    assert recovered.record_audio_chunk(
        sequence=1,
        start_sample=8_000,
        sample_count=8_000,
    )["endMs"] == 1_000


def test_clock_rejects_overlapping_sample_ranges_and_invalid_timebase():
    clock = MediaClock(
        clock_id="clock-live-1",
        master_source="AUDIO_SAMPLE_CLOCK",
        sample_rate=16_000,
    )
    clock.record_audio_chunk(sequence=0, start_sample=0, sample_count=16_000)

    with pytest.raises(MediaClockError, match="AUDIO_SAMPLE_OVERLAP"):
        clock.record_audio_chunk(sequence=1, start_sample=8_000, sample_count=16_000)

    with pytest.raises(MediaClockError, match="INVALID_PTS_TIMEBASE"):
        clock.map_video_pts(raw_pts=1, timebase_num=1, timebase_den=0)


def test_provisional_segment_allows_only_increasing_revisions_within_ten_seconds():
    ledger = ProvisionalSegmentLedger(correction_horizon_ms=10_000)

    assert ledger.accept(
        {"segmentId": "seg-1", "revision": 1, "state": "PROVISIONAL"},
        observed_at_ms=1_000,
    )
    assert ledger.accept(
        {"segmentId": "seg-1", "revision": 2, "state": "PROVISIONAL"},
        observed_at_ms=10_999,
    )
    assert not ledger.accept(
        {"segmentId": "seg-1", "revision": 2, "state": "PROVISIONAL"},
        observed_at_ms=11_000,
    )
    assert not ledger.accept(
        {"segmentId": "seg-1", "revision": 3, "state": "PROVISIONAL"},
        observed_at_ms=11_001,
    )


def test_final_segment_is_terminal_and_cannot_be_overwritten_by_provisional_data():
    ledger = ProvisionalSegmentLedger(correction_horizon_ms=10_000)
    ledger.accept(
        {"segmentId": "seg-1", "revision": 1, "state": "PROVISIONAL"},
        observed_at_ms=1_000,
    )

    assert ledger.accept(
        {"segmentId": "seg-1", "revision": 2, "state": "FINAL"},
        observed_at_ms=20_000,
    )
    assert not ledger.accept(
        {"segmentId": "seg-1", "revision": 3, "state": "PROVISIONAL"},
        observed_at_ms=20_001,
    )
    assert ledger.current("seg-1")["state"] == "FINAL"
