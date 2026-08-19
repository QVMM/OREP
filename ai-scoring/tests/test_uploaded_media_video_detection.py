from app.routers.scoring_router import _uploaded_media_has_video


def test_browser_webm_is_video_when_recorder_declares_video_track():
    assert _uploaded_media_has_video(".webm", declared_has_video=True) is True


def test_audio_only_webm_stays_audio_only():
    assert _uploaded_media_has_video(".webm", declared_has_video=False) is False


def test_known_video_container_is_detected_without_hint():
    assert _uploaded_media_has_video(".mp4", declared_has_video=None) is True
