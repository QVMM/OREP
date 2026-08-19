"""Bounded camera-only evidence subscriber for live scoring sessions.

The core class deliberately has no LiveKit dependency.  It owns the stable
transport contract (track selection, sampling, PTS preservation, reconnect
identity and overload behaviour), while the optional SDK adapter below only
translates LiveKit events into that contract.
"""

from __future__ import annotations

import asyncio
import io
import threading
from collections import deque
from copy import deepcopy
from typing import Any, Awaitable, Callable


class LiveCameraSubscriberError(ValueError):
    """Stable live-camera protocol failure."""


class LiveCameraSubscriber:
    """Thread-safe, camera-only frame sampler with a bounded processing queue."""

    def __init__(
        self,
        *,
        clock_id: str,
        target_fps: int = 6,
        max_backlog_ms: int = 3000,
        max_queue_frames: int | None = None,
    ):
        clock_id = str(clock_id or "").strip()
        if not clock_id:
            raise LiveCameraSubscriberError("CLOCK_ID_REQUIRED")
        self.clock_id = clock_id
        self.target_fps = max(5, min(8, int(target_fps)))
        self.max_backlog_ms = max(250, int(max_backlog_ms))
        self.max_queue_frames = max(
            1,
            int(max_queue_frames or (self.target_fps * 4)),
        )
        self._sample_interval_ms = 1000.0 / self.target_fps
        self._next_sample_at_ms: float | None = None
        self._frames: deque[dict[str, Any]] = deque()
        self._lock = threading.RLock()
        self._state = "WAITING_CAMERA"
        self._connection_id: str | None = None
        self._reconnect_count = 0
        self._dropped_frame_count = 0
        self._drop_ranges: list[dict[str, Any]] = []
        self._integrity_status = "OK"
        self._degradation_reason: str | None = None
        self._final_summary: dict[str, Any] | None = None

    @staticmethod
    def should_subscribe(*, kind: str, source: str) -> bool:
        """Only camera video is evidence; screen share and audio are separate flows."""

        normalized_kind = str(kind or "").strip().lower()
        normalized_source = str(source or "").strip().lower().replace("-", "_")
        return normalized_kind == "video" and normalized_source in {
            "camera",
            "source_camera",
        }

    def mark_connected(self, connection_id: str, *, clock_id: str | None = None) -> dict:
        with self._lock:
            self._ensure_active()
            if clock_id is not None and str(clock_id) != self.clock_id:
                raise LiveCameraSubscriberError("CLOCK_ID_CONFLICT")
            self._connection_id = str(connection_id or "").strip() or None
            self._state = "CONNECTED"
            return self.status()

    def mark_reconnecting(self) -> dict:
        with self._lock:
            self._ensure_active()
            self._reconnect_count += 1
            self._state = "RECONNECTING"
            return self.status()

    def ingest_frame(
        self,
        *,
        track_id: str,
        source: str,
        raw_pts: int,
        pts_timebase_num: int,
        pts_timebase_den: int,
        received_at_ms: int | float,
        payload: bytes,
        is_key_frame: bool = False,
    ) -> bool:
        """Accept one sampled frame and retain its original media timestamp."""

        with self._lock:
            self._ensure_active()
            if not self.should_subscribe(kind="video", source=source):
                return False
            if isinstance(raw_pts, bool) or not isinstance(raw_pts, int):
                raise LiveCameraSubscriberError("INVALID_RAW_PTS")
            if pts_timebase_den <= 0 or pts_timebase_num <= 0:
                raise LiveCameraSubscriberError("INVALID_PTS_TIMEBASE")
            if not isinstance(payload, (bytes, bytearray, memoryview)) or not payload:
                raise LiveCameraSubscriberError("INVALID_FRAME_PAYLOAD")

            received_at_ms = float(received_at_ms)
            if (
                self._next_sample_at_ms is not None
                and received_at_ms < self._next_sample_at_ms - 1e-6
            ):
                return False

            mapped_pts_ms = round(raw_pts * pts_timebase_num * 1000 / pts_timebase_den)
            frame = {
                "clockId": self.clock_id,
                "trackId": str(track_id or ""),
                "source": "CAMERA",
                "rawPts": raw_pts,
                "ptsTimebaseNum": int(pts_timebase_num),
                "ptsTimebaseDen": int(pts_timebase_den),
                "mappedPtsMs": mapped_pts_ms,
                "receivedAtMs": received_at_ms,
                "payload": bytes(payload),
                "isKeyFrame": bool(is_key_frame),
            }
            self._frames.append(frame)
            if self._next_sample_at_ms is None:
                self._next_sample_at_ms = received_at_ms + self._sample_interval_ms
            else:
                while self._next_sample_at_ms <= received_at_ms + 1e-6:
                    self._next_sample_at_ms += self._sample_interval_ms
            self._state = "CONNECTED"
            self._shed_backlog()
            return True

    def _shed_backlog(self) -> None:
        while self._non_key_span_ms() > self.max_backlog_ms:
            if not self._drop_oldest_non_key("BACKLOG_TIME_LIMIT"):
                break
        while len(self._frames) > self.max_queue_frames:
            if not self._drop_oldest_non_key("QUEUE_CAPACITY"):
                # A queue made only of key evidence is pathological, but memory
                # remains bounded.  Record this stronger integrity degradation.
                dropped = self._frames.popleft()
                self._record_drop(dropped, "KEY_FRAME_CAPACITY")

    def _non_key_span_ms(self) -> int:
        timestamps = [
            int(frame["mappedPtsMs"])
            for frame in self._frames
            if not frame["isKeyFrame"]
        ]
        return timestamps[-1] - timestamps[0] if len(timestamps) > 1 else 0

    def _drop_oldest_non_key(self, reason: str) -> bool:
        for index, frame in enumerate(self._frames):
            if frame["isKeyFrame"]:
                continue
            del self._frames[index]
            self._record_drop(frame, reason)
            return True
        return False

    def _record_drop(self, frame: dict[str, Any], reason: str) -> None:
        timestamp = int(frame["mappedPtsMs"])
        self._dropped_frame_count += 1
        self._integrity_status = "DEGRADED"
        if self._drop_ranges and self._drop_ranges[-1]["reason"] == reason:
            current = self._drop_ranges[-1]
            current["endMs"] = timestamp
            current["count"] += 1
        else:
            self._drop_ranges.append(
                {"startMs": timestamp, "endMs": timestamp, "count": 1, "reason": reason}
            )

    def drain(self) -> list[dict[str, Any]]:
        with self._lock:
            frames = list(self._frames)
            self._frames.clear()
            return frames

    def mark_camera_unavailable(self, reason: str) -> dict:
        with self._lock:
            self._ensure_active()
            self._state = "AUDIO_ONLY"
            self._integrity_status = "DEGRADED"
            self._degradation_reason = str(reason or "CAMERA_UNAVAILABLE")
            return self.status()

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "state": self._state,
                "clockId": self.clock_id,
                "connectionId": self._connection_id,
                "targetFps": self.target_fps,
                "queuedFrameCount": len(self._frames),
                "droppedFrameCount": self._dropped_frame_count,
                "dropRanges": deepcopy(self._drop_ranges),
                "reconnectCount": self._reconnect_count,
                "integrityStatus": self._integrity_status,
                "degradationReason": self._degradation_reason,
                "audioMayContinue": True,
            }

    def stop(self) -> dict[str, Any]:
        with self._lock:
            if self._final_summary is not None:
                return deepcopy(self._final_summary)
            self._state = "FINAL"
            self._final_summary = self.status()
            return deepcopy(self._final_summary)

    def _ensure_active(self) -> None:
        if self._final_summary is not None:
            raise LiveCameraSubscriberError("SUBSCRIBER_FINALIZED")


FrameSink = Callable[[dict[str, Any]], Awaitable[None] | None]


def build_livekit_subscriber_token(
    *,
    api_key: str,
    api_secret: str,
    room_name: str,
    session_id: str,
) -> str:
    """Mint a hidden, subscribe-only token scoped to exactly one local room."""

    from livekit import api

    if not all(str(item or "").strip() for item in (api_key, api_secret, room_name, session_id)):
        raise LiveCameraSubscriberError("LIVEKIT_SUBSCRIBER_CONFIG_MISSING")
    identity = f"orep-speaker-shadow-{session_id}"[:128]
    return (
        api.AccessToken(api_key, api_secret)
        .with_identity(identity)
        .with_grants(
            api.VideoGrants(
                room_join=True,
                room=str(room_name),
                can_publish=False,
                can_subscribe=True,
                can_publish_data=False,
                hidden=True,
            )
        )
        .to_jwt()
    )


class LiveKitCameraAdapter:
    """Thin optional adapter for the official LiveKit Python RTC SDK.

    The adapter never publishes media and never writes OSS.  Frames are JPEG
    encoded locally, placed in the bounded core queue, then forwarded to the
    supplied local sink by a single consumer task.
    """

    def __init__(
        self,
        *,
        subscriber: LiveCameraSubscriber,
        url: str,
        token: str,
        frame_sink: FrameSink | None = None,
        jpeg_max_width: int = 960,
        jpeg_quality: int = 70,
    ):
        self.subscriber = subscriber
        self.url = url
        self.token = token
        self.frame_sink = frame_sink
        self.jpeg_max_width = max(320, int(jpeg_max_width))
        self.jpeg_quality = max(40, min(90, int(jpeg_quality)))
        self.room = None
        self._track_tasks: set[asyncio.Task] = set()
        self._sink_task: asyncio.Task | None = None
        self._stopping = False

    async def start(self) -> None:
        from livekit import rtc

        self.room = rtc.Room()

        @self.room.on("reconnecting")
        def _on_reconnecting() -> None:
            self.subscriber.mark_reconnecting()

        @self.room.on("reconnected")
        def _on_reconnected() -> None:
            asyncio.create_task(self._mark_room_connected("reconnected"))

        @self.room.on("track_published")
        def _on_track_published(publication, _participant) -> None:
            if self._is_camera_publication(publication):
                publication.set_subscribed(True)

        @self.room.on("track_subscribed")
        def _on_track_subscribed(track, publication, _participant) -> None:
            if not self._is_camera_publication(publication):
                return
            task = asyncio.create_task(self._receive_track(track, publication.sid))
            self._track_tasks.add(task)
            task.add_done_callback(self._track_tasks.discard)

        options = rtc.RoomOptions(auto_subscribe=False, dynacast=True)
        await self.room.connect(self.url, self.token, options=options)
        await self._mark_room_connected("connected")
        for participant in self.room.remote_participants.values():
            for publication in participant.track_publications.values():
                if self._is_camera_publication(publication):
                    publication.set_subscribed(True)
        if self.frame_sink is not None:
            self._sink_task = asyncio.create_task(self._consume_queue())

    async def _mark_room_connected(self, fallback: str) -> None:
        connection_id = fallback
        if self.room is not None:
            try:
                connection_id = await self.room.sid
            except Exception:
                pass
        self.subscriber.mark_connected(connection_id or fallback)

    @staticmethod
    def _is_camera_publication(publication: Any) -> bool:
        from livekit import rtc

        return (
            publication.kind == rtc.TrackKind.KIND_VIDEO
            and publication.source == rtc.TrackSource.SOURCE_CAMERA
        )

    async def _receive_track(self, track: Any, track_id: str) -> None:
        from livekit import rtc

        stream = rtc.VideoStream(track, capacity=1)
        last_key_pts_ms: int | None = None
        try:
            async for event in stream:
                if self._stopping:
                    break
                payload = await asyncio.to_thread(self._encode_jpeg, event.frame)
                pts_ms = int(event.timestamp_us // 1000)
                is_key = last_key_pts_ms is None or pts_ms - last_key_pts_ms >= 2000
                if is_key:
                    last_key_pts_ms = pts_ms
                self.subscriber.ingest_frame(
                    track_id=track_id,
                    source="camera",
                    raw_pts=int(event.timestamp_us),
                    pts_timebase_num=1,
                    pts_timebase_den=1_000_000,
                    received_at_ms=asyncio.get_running_loop().time() * 1000,
                    payload=payload,
                    is_key_frame=is_key,
                )
        finally:
            await stream.aclose()

    def _encode_jpeg(self, frame: Any) -> bytes:
        from livekit import rtc
        from PIL import Image

        converted = frame.convert(rtc.VideoBufferType.RGBA)
        image = Image.frombytes(
            "RGBA",
            (converted.width, converted.height),
            bytes(converted.data),
        )
        if image.width > self.jpeg_max_width:
            scale = self.jpeg_max_width / image.width
            image = image.resize(
                (self.jpeg_max_width, max(1, round(image.height * scale))),
                Image.Resampling.LANCZOS,
            )
        output = io.BytesIO()
        image.convert("RGB").save(
            output,
            format="JPEG",
            quality=self.jpeg_quality,
            optimize=False,
        )
        return output.getvalue()

    async def _consume_queue(self) -> None:
        while not self._stopping:
            await asyncio.sleep(0.05)
            frames = self.subscriber.drain()
            try:
                await self._deliver_frames(frames)
            except Exception as error:
                self.subscriber.mark_camera_unavailable(
                    f"VISUAL_SINK_FAILED:{type(error).__name__}"
                )
                return

    async def _deliver_frames(self, frames: list[dict[str, Any]]) -> None:
        if self.frame_sink is None:
            return
        for frame in frames:
            result = self.frame_sink(frame)
            if asyncio.iscoroutine(result):
                await result

    async def stop(self) -> dict[str, Any]:
        if self._stopping:
            return self.subscriber.stop()
        self._stopping = True
        for task in tuple(self._track_tasks):
            task.cancel()
        if self._track_tasks:
            await asyncio.gather(*self._track_tasks, return_exceptions=True)
        if self._sink_task is not None:
            self._sink_task.cancel()
            await asyncio.gather(self._sink_task, return_exceptions=True)
        remaining_frames = self.subscriber.drain()
        if remaining_frames and self.frame_sink is not None:
            try:
                await self._deliver_frames(remaining_frames)
            except Exception as error:
                self.subscriber.mark_camera_unavailable(
                    f"VISUAL_SINK_FLUSH_FAILED:{type(error).__name__}"
                )
        if self.room is not None:
            await self.room.disconnect()
        return self.subscriber.stop()


class LiveCameraRuntimeRegistry:
    """Own optional per-session LiveKit subscribers inside one FastAPI process."""

    def __init__(self, *, adapter_factory=LiveKitCameraAdapter):
        self._adapter_factory = adapter_factory
        self._runtimes: dict[str, dict[str, Any]] = {}

    async def start(
        self,
        *,
        session_id: str,
        room_name: str,
        clock_id: str,
        url: str,
        token: str,
        target_fps: int = 6,
        max_backlog_ms: int = 3000,
        max_queue_frames: int | None = None,
        frame_sink: FrameSink | None = None,
        jpeg_max_width: int = 960,
        jpeg_quality: int = 70,
    ) -> dict[str, Any]:
        session_id = str(session_id)
        existing = self._runtimes.get(session_id)
        if existing is not None:
            return existing["subscriber"].status()

        subscriber = LiveCameraSubscriber(
            clock_id=clock_id,
            target_fps=target_fps,
            max_backlog_ms=max_backlog_ms,
            max_queue_frames=max_queue_frames,
        )
        adapter = self._adapter_factory(
            subscriber=subscriber,
            url=url,
            token=token,
            frame_sink=frame_sink,
            jpeg_max_width=jpeg_max_width,
            jpeg_quality=jpeg_quality,
        )
        runtime: dict[str, Any] = {
            "roomName": str(room_name),
            "subscriber": subscriber,
            "adapter": adapter,
            "bootstrapTask": None,
        }
        self._runtimes[session_id] = runtime

        async def bootstrap() -> None:
            try:
                await adapter.start()
            except asyncio.CancelledError:
                raise
            except Exception as error:
                if subscriber.status()["state"] != "FINAL":
                    subscriber.mark_camera_unavailable(
                        f"LIVEKIT_CAMERA_SUBSCRIBE_FAILED:{type(error).__name__}"
                    )

        runtime["bootstrapTask"] = asyncio.create_task(bootstrap())
        return subscriber.status()

    def status(self, session_id: str) -> dict[str, Any] | None:
        runtime = self._runtimes.get(str(session_id))
        return runtime["subscriber"].status() if runtime is not None else None

    def drain(self, session_id: str) -> list[dict[str, Any]]:
        runtime = self._runtimes.get(str(session_id))
        return runtime["subscriber"].drain() if runtime is not None else []

    async def stop(self, session_id: str) -> dict[str, Any] | None:
        runtime = self._runtimes.pop(str(session_id), None)
        if runtime is None:
            return None
        bootstrap_task = runtime.get("bootstrapTask")
        if bootstrap_task is not None and not bootstrap_task.done():
            bootstrap_task.cancel()
            await asyncio.gather(bootstrap_task, return_exceptions=True)
        try:
            return await runtime["adapter"].stop()
        except Exception as error:
            subscriber = runtime["subscriber"]
            if subscriber.status()["state"] != "FINAL":
                subscriber.mark_camera_unavailable(
                    f"LIVEKIT_CAMERA_STOP_FAILED:{type(error).__name__}"
                )
            return subscriber.stop()


live_camera_runtime_registry = LiveCameraRuntimeRegistry()
