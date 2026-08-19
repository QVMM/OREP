from app.services.speech_analysis_service import _analyze_speech_rate


def test_unknown_speaker_segments_remain_unknown_and_do_not_break_sorting():
    result = _analyze_speech_rate(
        [
            {"speaker": "SPEAKER_0", "text": "已识别发言", "start": 0, "end": 2},
            {"speaker": None, "text": "无法可靠归属", "start": 2, "end": 4},
            {"text": "尚未识别", "start": 4, "end": 6},
        ],
        total_duration=6,
    )

    speakers = [item["speaker"] for item in result["per_speaker"]]
    assert speakers == ["SPEAKER_0", "UNKNOWN"]
    assert "SPEAKER_1" not in speakers
    unknown = next(item for item in result["per_speaker"] if item["speaker"] == "UNKNOWN")
    assert unknown["speaking_seconds"] == 4.0
    assert unknown["total_chars"] == len("无法可靠归属尚未识别")
