import json

import pytest

from app.services.media_evidence.legacy_adapter import build_legacy_evidence_package
from app.services.media_evidence.shadow_store import save_shadow_package


def sample_inputs():
    asr_result = {
        "source": "file",
        "duration": 10,
        "segments": [
            {
                "start": 0.0,
                "end": 4.0,
                "text": "我们展示核心算法",
                "speaker": "SPEAKER_0",
            },
            {
                "start": 5.0,
                "end": 9.0,
                "text": "系统准确率达到百分之九十二",
                "speaker": "SPEAKER_0",
            },
        ],
    }
    speech_quality = {
        "speech_rate": {"value": 220, "score": 8, "rating": "偏快"},
        "pauses": {"count": 3, "average_duration": 0.8},
        "fillers": {"count": 2, "words": ["嗯", "然后"]},
        "prosody": {"enabled": True, "variation": 0.4},
    }
    video_analysis = {
        "frame_count": 2,
        "source": "video_file",
        "per_frame": [
            {
                "frame": 2,
                "timestamp_min": 1.0,
                "gesture": {"desc": "手势清楚", "score": 7},
                "screen_content": {
                    "screen_type": "PPT幻灯片",
                    "key_text": "准确率92%",
                },
            },
            {
                "frame": 1,
                "timestamp_min": 0.5,
                "posture": {"desc": "站姿稳定", "score": 8},
                "screen_content": {"screen_type": "代码演示"},
            },
        ],
        "aggregates": {"avg_visual_composite": 7.5},
    }
    fusion = {
        "contradictions": [
            {
                "time_min": 1.0,
                "description": "口头称有测试，但画面未展示测试来源",
                "audio_score": 8,
                "visual_score": 3,
            }
        ]
    }
    return asr_result, speech_quality, video_analysis, fusion


def test_legacy_adapter_builds_score_free_deterministic_package():
    asr_result, speech_quality, video_analysis, fusion = sample_inputs()

    package = build_legacy_evidence_package(
        session_id="26",
        source_type="UPLOAD_VIDEO",
        asr_result=asr_result,
        speech_quality=speech_quality,
        video_analysis=video_analysis,
        fusion=fusion,
        processing_metrics={"durationMs": 100},
        ai_score={"overall_score": 99},
    )

    assert package["contractVersion"] == "media-evidence-v1"
    assert package["sourceType"] == "UPLOAD_VIDEO"
    assert package["status"] == "FINAL"
    assert package["integrity"]["audioCoverage"] == 0.8
    assert package["integrity"]["diarizationStatus"] == "unavailable"
    assert all(item["rawSpeakerId"] is None for item in package["transcriptSegments"])
    assert [item["startMs"] for item in package["visualEvidence"]] == [30000, 60000]

    serialized = json.dumps(package, ensure_ascii=False)
    assert '"overall_score"' not in serialized
    assert '"audio_score"' not in serialized
    assert '"visual_score"' not in serialized
    assert '"score"' not in serialized


def test_video_scores_are_renamed_to_signal_values():
    asr_result, speech_quality, video_analysis, fusion = sample_inputs()

    package = build_legacy_evidence_package(
        session_id="26",
        source_type="UPLOAD_VIDEO",
        asr_result=asr_result,
        speech_quality=speech_quality,
        video_analysis=video_analysis,
        fusion=fusion,
    )

    gesture = next(item for item in package["deliverySignals"] if item["signal"] == "gesture")
    posture = next(item for item in package["deliverySignals"] if item["signal"] == "posture")
    assert gesture["signalValue"] == 7
    assert posture["signalValue"] == 8
    assert all("score" not in item for item in package["deliverySignals"])


def test_shadow_store_replaces_snapshot_atomically(tmp_path):
    first = {"snapshotHash": "sha256:first", "text": "旧证据"}
    second = {"snapshotHash": "sha256:second", "text": "新证据"}

    path = save_shadow_package(str(tmp_path), "26", first)
    save_shadow_package(str(tmp_path), "26", second)

    assert path.endswith("results/evidence_shadow_26.json")
    assert json.loads((tmp_path / "results" / "evidence_shadow_26.json").read_text()) == second
    assert list((tmp_path / "results").glob("*.tmp")) == []


def test_shadow_store_serialization_failure_keeps_prior_snapshot(tmp_path):
    prior = {"snapshotHash": "sha256:prior"}
    save_shadow_package(str(tmp_path), "26", prior)

    with pytest.raises(TypeError):
        save_shadow_package(str(tmp_path), "26", {"notSerializable": object()})

    persisted = json.loads((tmp_path / "results" / "evidence_shadow_26.json").read_text())
    assert persisted == prior
    assert list((tmp_path / "results").glob("*.tmp")) == []
