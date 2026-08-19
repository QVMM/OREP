import asyncio

from app.config import settings
from app.routers.scoring_router import (
    ScoringSessionFinishRequest,
    ScoringSessionStartRequest,
    finish_scoring_session,
    live_camera_runtime_registry,
    _append_live_camera_frame_event,
    _read_live_camera_frame_events,
    start_scoring_session,
)


def test_session_start_returns_and_persists_one_server_media_clock(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))

    session = asyncio.run(
        start_scoring_session(
            ScoringSessionStartRequest(
                meeting_id="room-101",
                has_audio=True,
                has_video=True,
            )
        )
    )

    assert session["media_clock_id"].startswith(f"session-{session['session_id']}-")
    assert session["media_clock_master"] == "AUDIO_SAMPLE_CLOCK"


def test_enabled_live_camera_runtime_uses_session_clock_and_stops_at_terminal(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "LIVE_CAMERA_SUBSCRIBER_ENABLED", True)
    monkeypatch.setattr(settings, "LIVEKIT_API_KEY", "test-key")
    monkeypatch.setattr(settings, "LIVEKIT_API_SECRET", "test-secret-32-characters-minimum")
    observed = {}

    async def fake_start(**kwargs):
        observed.update(kwargs)
        return {
            "state": "CONNECTED",
            "clockId": kwargs["clock_id"],
            "audioMayContinue": True,
        }

    async def fake_stop(session_id):
        observed["stopped_session_id"] = session_id
        return {
            "state": "FINAL",
            "clockId": observed["clock_id"],
            "audioMayContinue": True,
        }

    monkeypatch.setattr(live_camera_runtime_registry, "start", fake_start)
    monkeypatch.setattr(live_camera_runtime_registry, "stop", fake_stop)

    session = asyncio.run(
        start_scoring_session(
            ScoringSessionStartRequest(
                meeting_id="room-live",
                has_audio=True,
                has_video=True,
            )
        )
    )
    final = asyncio.run(
        finish_scoring_session(
            session["session_id"], ScoringSessionFinishRequest(status="finished")
        )
    )

    assert observed["room_name"] == "room-live"
    assert observed["clock_id"] == session["media_clock_id"]
    assert observed["stopped_session_id"] == session["session_id"]
    assert final["live_camera_subscriber"]["state"] == "FINAL"


def test_live_camera_metadata_samples_authoritative_audio_cursor(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))

    class Journal:
        media_clock_snapshot = {
            "clockId": "clock-audio",
            "sampleRate": 16_000,
            "nextSample": 32_000,
        }

    monkeypatch.setattr(
        "app.routers.scoring_router.get_audio_chunk_journal",
        lambda *_args, **_kwargs: Journal(),
    )
    _append_live_camera_frame_event(
        "session-audio-clock",
        {
            "clockId": "clock-audio",
            "trackId": "camera-1",
            "rawPts": 900_000,
            "ptsTimebaseNum": 1,
            "ptsTimebaseDen": 90_000,
            "mappedPtsMs": 10_000,
            "isKeyFrame": False,
        },
    )

    event = _read_live_camera_frame_events("session-audio-clock")[0]
    assert event["observed_audio_sample"] == 32_000
    assert event["timestamp"] == 2.0
    assert "payload" not in event
