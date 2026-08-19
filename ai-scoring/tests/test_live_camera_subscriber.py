import pytest
import asyncio
import jwt

from app.services.media_evidence.live_camera_subscriber import (
    LiveCameraSubscriber,
    LiveCameraSubscriberError,
    LiveKitCameraAdapter,
    LiveCameraRuntimeRegistry,
    build_livekit_subscriber_token,
)


def test_selects_camera_video_and_rejects_screen_share_or_audio_tracks():
    subscriber = LiveCameraSubscriber(clock_id="clock-live-1")

    assert subscriber.should_subscribe(kind="video", source="camera") is True
    assert subscriber.should_subscribe(kind="video", source="screen_share") is False
    assert subscriber.should_subscribe(kind="audio", source="camera") is False


def test_samples_camera_between_five_and_eight_frames_per_second_and_keeps_pts():
    subscriber = LiveCameraSubscriber(clock_id="clock-live-1", target_fps=6)

    for timestamp_ms in range(0, 1000, 25):
        subscriber.ingest_frame(
            track_id="camera-1",
            source="camera",
            raw_pts=timestamp_ms * 90,
            pts_timebase_num=1,
            pts_timebase_den=90_000,
            received_at_ms=timestamp_ms,
            payload=b"frame",
        )

    frames = subscriber.drain()
    assert 5 <= len(frames) <= 8
    assert frames[0]["rawPts"] == 0
    assert frames[-1]["rawPts"] > 0
    assert all(item["clockId"] == "clock-live-1" for item in frames)


def test_reconnect_preserves_clock_and_rejects_a_different_clock():
    subscriber = LiveCameraSubscriber(clock_id="clock-live-1")
    subscriber.mark_connected("connection-1")
    subscriber.mark_reconnecting()
    subscriber.mark_connected("connection-2", clock_id="clock-live-1")

    assert subscriber.status()["connectionId"] == "connection-2"
    assert subscriber.status()["clockId"] == "clock-live-1"
    assert subscriber.status()["reconnectCount"] == 1

    with pytest.raises(LiveCameraSubscriberError, match="CLOCK_ID_CONFLICT"):
        subscriber.mark_connected("connection-3", clock_id="clock-live-2")


def test_backlog_discards_oldest_non_key_frames_but_retains_key_timestamps():
    subscriber = LiveCameraSubscriber(
        clock_id="clock-live-1",
        target_fps=8,
        max_backlog_ms=3000,
        max_queue_frames=32,
    )
    for timestamp_ms in range(0, 6001, 125):
        subscriber.ingest_frame(
            track_id="camera-1",
            source="camera",
            raw_pts=timestamp_ms,
            pts_timebase_num=1,
            pts_timebase_den=1000,
            received_at_ms=timestamp_ms,
            payload=b"key" if timestamp_ms in {0, 3000, 6000} else b"frame",
            is_key_frame=timestamp_ms in {0, 3000, 6000},
        )

    frames = subscriber.drain()
    status = subscriber.status()
    assert {item["rawPts"] for item in frames if item["isKeyFrame"]} == {0, 3000, 6000}
    non_keys = [item for item in frames if not item["isKeyFrame"]]
    assert non_keys[-1]["mappedPtsMs"] - non_keys[0]["mappedPtsMs"] <= 3000
    assert status["droppedFrameCount"] > 0
    assert status["integrityStatus"] == "DEGRADED"
    assert status["dropRanges"]


def test_camera_failure_degrades_visual_evidence_without_stopping_audio():
    subscriber = LiveCameraSubscriber(clock_id="clock-live-1")

    subscriber.mark_camera_unavailable("NO_CAMERA_TRACK")

    assert subscriber.status()["state"] == "AUDIO_ONLY"
    assert subscriber.status()["audioMayContinue"] is True
    assert subscriber.status()["integrityStatus"] == "DEGRADED"


def test_terminal_stop_rejects_late_frames_and_is_idempotent():
    subscriber = LiveCameraSubscriber(clock_id="clock-live-1")
    first = subscriber.stop()
    second = subscriber.stop()

    assert first == second
    with pytest.raises(LiveCameraSubscriberError, match="SUBSCRIBER_FINALIZED"):
        subscriber.ingest_frame(
            track_id="camera-1",
            source="camera",
            raw_pts=0,
            pts_timebase_num=1,
            pts_timebase_den=1000,
            received_at_ms=0,
            payload=b"late",
        )


def test_livekit_token_is_hidden_subscribe_only_and_bound_to_one_room():
    token = build_livekit_subscriber_token(
        api_key="local-key",
        api_secret="local-secret-at-least-32-characters",
        room_name="meeting-26",
        session_id="session-26",
    )

    claims = jwt.decode(token, options={"verify_signature": False})
    assert claims["sub"] == "orep-speaker-shadow-session-26"
    assert claims["video"]["room"] == "meeting-26"
    assert claims["video"]["roomJoin"] is True
    assert claims["video"]["canSubscribe"] is True
    assert claims["video"]["canPublish"] is False
    assert claims["video"]["hidden"] is True


def test_registry_starts_and_stops_one_runtime_without_blocking_audio():
    adapters = []

    class FakeAdapter:
        def __init__(self, **kwargs):
            self.subscriber = kwargs["subscriber"]
            self.started = False
            self.stopped = False
            adapters.append(self)

        async def start(self):
            self.started = True
            self.subscriber.mark_connected("fake-room")

        async def stop(self):
            self.stopped = True
            return self.subscriber.stop()

    async def scenario():
        registry = LiveCameraRuntimeRegistry(adapter_factory=FakeAdapter)
        initial = await registry.start(
            session_id="session-26",
            room_name="meeting-26",
            clock_id="clock-26",
            url="ws://livekit:7880",
            token="token",
        )
        await asyncio.sleep(0)
        running = registry.status("session-26")
        final = await registry.stop("session-26")
        return initial, running, final

    initial, running, final = asyncio.run(scenario())
    assert initial["state"] in {"WAITING_CAMERA", "CONNECTED"}
    assert running["state"] == "CONNECTED"
    assert running["audioMayContinue"] is True
    assert final["state"] == "FINAL"
    assert adapters[0].started is True
    assert adapters[0].stopped is True


def test_adapter_stop_flushes_remaining_sample_metadata_to_local_sink():
    received = []

    async def sink(frame):
        received.append(frame)

    async def scenario():
        subscriber = LiveCameraSubscriber(clock_id="clock-flush")
        subscriber.ingest_frame(
            track_id="camera-1",
            source="camera",
            raw_pts=90_000,
            pts_timebase_num=1,
            pts_timebase_den=90_000,
            received_at_ms=1000,
            payload=b"jpeg",
        )
        adapter = LiveKitCameraAdapter(
            subscriber=subscriber,
            url="ws://local",
            token="token",
            frame_sink=sink,
        )
        final = await adapter.stop()
        return final

    final = asyncio.run(scenario())
    assert len(received) == 1
    assert received[0]["rawPts"] == 90_000
    assert final["state"] == "FINAL"
