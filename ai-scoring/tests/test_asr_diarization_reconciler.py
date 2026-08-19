from app.services.media_evidence.asr_diarization_reconciler import reconcile_asr_with_diarization


def _forbidden_keys(value):
    found = []
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = "".join(ch for ch in key.lower() if ch.isalnum())
            if normalized in {"score", "overallscore", "dimensionscore", "speakerscores"}:
                found.append(key)
            found.extend(_forbidden_keys(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(_forbidden_keys(child))
    return found


def test_assigns_majority_overlap_without_changing_asr_text_or_timestamps():
    asr = {
        "transcript": "第一段 第二段",
        "segments": [
            {"start": 0.0, "end": 2.0, "text": "第一段", "confidence": 0.9},
            {"startMs": 2000, "endMs": 4000, "start": 2.0, "end": 4.0, "text": "第二段"},
        ],
        "duration": 4.0,
        "source": "cloud_streaming_asr",
    }
    diarization = {
        "turns": [
            {"startMs": 0, "endMs": 1800, "rawSpeakerId": "SPEAKER_0"},
            {"startMs": 1800, "endMs": 4200, "rawSpeakerId": "SPEAKER_1"},
        ],
        "source": "local_sherpa_onnx",
    }

    result = reconcile_asr_with_diarization(asr, diarization)

    assert result["transcript"] == "第一段 第二段"
    assert result["segments"][0]["text"] == "第一段"
    assert result["segments"][0]["start"] == 0.0
    assert result["segments"][0]["end"] == 2.0
    assert result["segments"][0]["startMs"] == 0
    assert result["segments"][0]["endMs"] == 2000
    assert result["segments"][0]["rawSpeakerId"] == "SPEAKER_0"
    assert result["segments"][1]["rawSpeakerId"] == "SPEAKER_1"
    assert result["speakers"] == ["SPEAKER_0", "SPEAKER_1"]
    assert result["diarizationStatus"] == "completed"
    assert _forbidden_keys(result) == []


def test_ambiguous_overlap_remains_overlap_instead_of_forcing_a_person():
    result = reconcile_asr_with_diarization(
        {"segments": [{"start": 0, "end": 2, "text": "两人交接"}]},
        {"turns": [
            {"startMs": 0, "endMs": 1000, "rawSpeakerId": "SPEAKER_0"},
            {"startMs": 1000, "endMs": 2000, "rawSpeakerId": "SPEAKER_1"},
        ]},
    )

    segment = result["segments"][0]
    assert segment["rawSpeakerId"] is None
    assert segment["speakerState"] == "OVERLAP"
    assert segment["speakerCandidates"] == ["SPEAKER_0", "SPEAKER_1"]
    assert result["diarizationStatus"] == "partial"


def test_insufficient_overlap_stays_unknown_and_does_not_reuse_old_asr_speaker():
    result = reconcile_asr_with_diarization(
        {"segments": [{
            "start": 0,
            "end": 10,
            "text": "长句",
            "speaker": "SPEAKER_9",
            "rawSpeakerId": "SPEAKER_9",
        }]},
        {"turns": [{"startMs": 0, "endMs": 1000, "rawSpeakerId": "SPEAKER_0"}]},
    )

    segment = result["segments"][0]
    assert segment["rawSpeakerId"] is None
    assert segment["speaker"] is None
    assert segment["speakerState"] == "UNKNOWN"
    assert result["diarizationStatus"] == "evidence_incomplete"


def test_propagates_audio_visual_acceptance_and_rejection_counters():
    result = reconcile_asr_with_diarization(
        {"segments": [{"start": 0, "end": 1, "text": "验证"}]},
        {
            "turns": [
                {
                    "startMs": 0,
                    "endMs": 1000,
                    "rawSpeakerId": "SPEAKER_0",
                    "speakerVerification": "AUDIO_VISUAL",
                }
            ],
            "audioVisualDirectCandidateTurnCount": 5,
            "audioVisualDirectTurnCount": 2,
            "audioVisualInheritedTurnCount": 3,
            "audioVisualRejectedCandidateTurnCount": 3,
        },
    )

    assert result["audioVisualDirectCandidateTurnCount"] == 5
    assert result["audioVisualDirectTurnCount"] == 2
    assert result["audioVisualInheritedTurnCount"] == 3
    assert result["audioVisualRejectedCandidateTurnCount"] == 3
