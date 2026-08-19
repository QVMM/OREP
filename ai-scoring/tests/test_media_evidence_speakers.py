from app.services.media_evidence.speaker_reconciliation import normalize_asr_segments


def test_missing_speaker_id_remains_unknown_instead_of_speaker_zero():
    result = normalize_asr_segments(
        [{"start": 1.0, "end": 2.0, "text": "你好", "speaker_id": None}],
        source="legacy_realtime",
    )

    assert result["segments"][0]["rawSpeakerId"] is None
    assert result["segments"][0]["displaySpeaker"] == "发言人待确认"
    assert result["diarizationStatus"] == "unavailable"
    assert result["detectedSpeakerCount"] == 0


def test_legacy_fabricated_speaker_string_is_not_treated_as_audio_fact():
    result = normalize_asr_segments(
        [
            {
                "start": 1.0,
                "end": 2.0,
                "text": "旧结果",
                "speaker": "SPEAKER_0",
                "speaker_id": None,
            }
        ],
        source="legacy_realtime",
    )

    assert result["segments"][0]["rawSpeakerId"] is None
    assert result["diarizationStatus"] == "unavailable"


def test_provider_speaker_id_is_preserved_as_raw_fact():
    result = normalize_asr_segments(
        [
            {
                "begin_time": 1000,
                "end_time": 2500,
                "text": "技术介绍",
                "speaker_id": 2,
            }
        ],
        source="dashscope_fun_asr",
        time_unit="ms",
    )

    segment = result["segments"][0]
    assert segment["rawSpeakerId"] == "SPEAKER_2"
    assert segment["displaySpeaker"] == "3号发言人"
    assert segment["startMs"] == 1000
    assert segment["endMs"] == 2500
    assert result["detectedSpeakerCount"] == 1
    assert result["diarizationStatus"] == "completed"


def test_overlap_is_not_forced_to_one_identity():
    result = normalize_asr_segments(
        [
            {
                "start": 3.0,
                "end": 4.0,
                "text": "同时发言",
                "speaker_id": [1, 2],
            }
        ],
        source="local_diarization",
    )

    segment = result["segments"][0]
    assert segment["speakerState"] == "OVERLAP"
    assert segment["rawSpeakerId"] is None
    assert segment["speakerCandidates"] == ["SPEAKER_1", "SPEAKER_2"]
    assert result["overlapSegmentCount"] == 1


def test_short_segment_is_marked_insufficient_without_losing_raw_label():
    result = normalize_asr_segments(
        [{"start": 2.0, "end": 2.1, "text": "嗯", "speaker_id": 1}],
        source="dashscope_fun_asr",
    )

    segment = result["segments"][0]
    assert segment["speakerState"] == "INSUFFICIENT_AUDIO"
    assert segment["rawSpeakerId"] == "SPEAKER_1"


def test_segments_are_sorted_and_numbered_by_time():
    result = normalize_asr_segments(
        [
            {"start": 5.0, "end": 6.0, "text": "第二段", "speaker_id": 1},
            {"start": 1.0, "end": 2.0, "text": "第一段", "speaker_id": 0},
        ],
        source="dashscope_fun_asr",
    )

    assert [item["text"] for item in result["segments"]] == ["第一段", "第二段"]
    assert [item["segmentNo"] for item in result["segments"]] == [1, 2]
    assert result["speakers"] == ["SPEAKER_0", "SPEAKER_1"]


def test_mixed_known_and_unknown_segments_report_partial_diarization():
    result = normalize_asr_segments(
        [
            {"start": 1.0, "end": 2.0, "text": "已识别", "speaker_id": 0},
            {"start": 2.0, "end": 3.0, "text": "未知", "speaker_id": None},
        ],
        source="dashscope_fun_asr",
    )

    assert result["diarizationStatus"] == "partial"
    assert result["unresolvedSegmentCount"] == 1
