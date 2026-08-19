from app.services.pipeline_payloads import (
    persistable_fusion,
    persistable_video_analysis,
    validate_fusion_for_scoring,
    validate_video_analysis_for_scoring,
)


def test_video_result_payload_preserves_per_frame_analysis():
    payload = persistable_video_analysis({
        "frame_count": 1,
        "interval_sec": 30,
        "per_frame": [{"timestamp_min": 1.5, "screen_content": {"screen_type": "PPT幻灯片"}}],
        "aggregates": {"avg_visual_composite": 7.5},
        "tokens_used": {"total": 123},
        "source": "session_capture",
        "selection_strategy": {"strategy": "time_interval_plus_scene_change"},
    })

    assert payload["per_frame"][0]["screen_content"]["screen_type"] == "PPT幻灯片"
    assert payload["aggregates"]["avg_visual_composite"] == 7.5
    assert payload["source"] == "session_capture"
    assert payload["selection_strategy"]["strategy"] == "time_interval_plus_scene_change"


def test_fusion_result_payload_preserves_timeline_and_screen_summary():
    payload = persistable_fusion({
        "summary": {"fusion_avg": 8.1},
        "audio_windows": [{"time_min": 1.0, "speech_rate_score": 7}],
        "timeline": [{"time_min": 1.0, "fusion_score": 8.1}],
        "trends": {"fusion": {"values": [8.1]}},
        "contradictions": [],
        "screen_content_summary": {"screen_type_distribution": {"PPT幻灯片": 3}},
    })

    assert payload["timeline"][0]["fusion_score"] == 8.1
    assert payload["audio_windows"][0]["speech_rate_score"] == 7
    assert payload["screen_content_summary"]["screen_type_distribution"]["PPT幻灯片"] == 3


def test_video_validation_rejects_all_failed_frame_analysis():
    try:
        validate_video_analysis_for_scoring({
            "aggregates": {"error": "无有效数据"},
            "per_frame": [{"frame": 1, "error": "api failed"}],
        })
    except RuntimeError as exc:
        assert "视频帧分析没有有效结果" in str(exc)
    else:
        raise AssertionError("expected invalid video analysis to fail")


def test_video_validation_rejects_low_valid_frame_ratio():
    try:
        validate_video_analysis_for_scoring({
            "aggregates": {"avg_visual_composite": 7.2},
            "per_frame": [
                {"frame": 1, "screen_content": {"screen_type": "PPT幻灯片"}},
                {"frame": 2, "error": "timeout"},
                {"frame": 3, "error": "timeout"},
            ],
        })
    except RuntimeError as exc:
        assert "视频帧分析有效率过低" in str(exc)
        assert "有效 1/3 帧" in str(exc)
    else:
        raise AssertionError("expected low valid frame ratio to fail")


def test_fusion_validation_rejects_empty_timeline():
    try:
        validate_fusion_for_scoring({"summary": {"total_windows": 0}, "timeline": []})
    except RuntimeError as exc:
        assert "音视频融合没有生成有效时间线" in str(exc)
    else:
        raise AssertionError("expected empty fusion timeline to fail")
