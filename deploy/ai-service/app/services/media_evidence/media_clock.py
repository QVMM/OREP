"""Shared, score-free media clock primitives for upload and live evidence."""

from __future__ import annotations

import copy
import math
from typing import Any


class MediaClockError(ValueError):
    """Raised when raw media timing cannot be mapped without ambiguity."""


def _integer(value: Any, code: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise MediaClockError(code)
    return value


class MediaClock:
    """Map audio samples and media PTS onto one auditable millisecond timeline.

    Live roadshows use the received 16 kHz PCM sample count as master. Uploaded
    recordings use container media PTS as master. Raw PTS is always retained;
    mapping creates additional fields and never mutates the source timestamp.
    """

    SUPPORTED_MASTERS = frozenset({"AUDIO_SAMPLE_CLOCK", "MEDIA_PTS"})

    def __init__(
        self,
        *,
        clock_id: str,
        master_source: str,
        sample_rate: int = 16_000,
        severe_drift_ms: int = 500,
    ):
        self.clock_id = str(clock_id or "").strip()
        if not self.clock_id:
            raise MediaClockError("INVALID_CLOCK_ID")
        self.master_source = str(master_source or "").strip().upper()
        if self.master_source not in self.SUPPORTED_MASTERS:
            raise MediaClockError("INVALID_MASTER_SOURCE")
        self.sample_rate = _integer(sample_rate, "INVALID_SAMPLE_RATE", minimum=1)
        self.severe_drift_ms = _integer(
            severe_drift_ms, "INVALID_DRIFT_THRESHOLD", minimum=1
        )
        self._audio_chunks: dict[int, dict] = {}

    @property
    def next_sample(self) -> int:
        sequence = 0
        cursor = 0
        while sequence in self._audio_chunks:
            chunk = self._audio_chunks[sequence]
            if chunk["startSample"] != cursor:
                break
            cursor = chunk["endSample"]
            sequence += 1
        return cursor

    def _sample_ms(self, sample: int) -> int:
        return int(round((sample / self.sample_rate) * 1000))

    def record_audio_chunk(
        self,
        *,
        sequence: int,
        start_sample: int,
        sample_count: int,
        declared_start_ms: int | None = None,
        declared_end_ms: int | None = None,
    ) -> dict:
        sequence = _integer(sequence, "INVALID_SEQUENCE")
        start_sample = _integer(start_sample, "INVALID_START_SAMPLE")
        sample_count = _integer(sample_count, "INVALID_SAMPLE_COUNT", minimum=1)
        end_sample = start_sample + sample_count

        existing = self._audio_chunks.get(sequence)
        if existing is not None:
            if (
                existing["startSample"] != start_sample
                or existing["sampleCount"] != sample_count
            ):
                raise MediaClockError("AUDIO_SEQUENCE_CONFLICT")
            return copy.deepcopy(existing)

        for chunk in self._audio_chunks.values():
            if start_sample < chunk["endSample"] and end_sample > chunk["startSample"]:
                raise MediaClockError("AUDIO_SAMPLE_OVERLAP")

        start_ms = self._sample_ms(start_sample)
        end_ms = self._sample_ms(end_sample)
        declared_values: list[int] = []
        if declared_start_ms is not None:
            declared_start_ms = _integer(
                declared_start_ms, "INVALID_DECLARED_TIME"
            )
            declared_values.append(abs(declared_start_ms - start_ms))
        if declared_end_ms is not None:
            declared_end_ms = _integer(declared_end_ms, "INVALID_DECLARED_TIME")
            declared_values.append(abs(declared_end_ms - end_ms))
        declared_drift_ms = max(declared_values, default=0)

        item = {
            "clockId": self.clock_id,
            "sequence": sequence,
            "startSample": start_sample,
            "endSample": end_sample,
            "sampleCount": sample_count,
            "startMs": start_ms,
            "endMs": end_ms,
            "declaredStartMs": declared_start_ms,
            "declaredEndMs": declared_end_ms,
            "declaredDriftMs": declared_drift_ms,
            "syncStatus": (
                "DEGRADED"
                if declared_drift_ms >= self.severe_drift_ms
                else "SYNCED"
            ),
        }
        self._audio_chunks[sequence] = item
        return copy.deepcopy(item)

    def map_video_pts(
        self,
        *,
        raw_pts: int | float,
        timebase_num: int,
        timebase_den: int,
        observed_audio_sample: int | None = None,
    ) -> dict:
        if (
            isinstance(raw_pts, bool)
            or not isinstance(raw_pts, (int, float))
            or not math.isfinite(float(raw_pts))
            or raw_pts < 0
        ):
            raise MediaClockError("INVALID_RAW_PTS")
        timebase_num = _integer(timebase_num, "INVALID_PTS_TIMEBASE", minimum=1)
        timebase_den = _integer(timebase_den, "INVALID_PTS_TIMEBASE", minimum=1)
        raw_pts_ms = int(round(float(raw_pts) * timebase_num / timebase_den * 1000))

        if self.master_source == "MEDIA_PTS":
            mapped_ms = raw_pts_ms
            drift_ms = 0
            sync_status = "SYNCED"
        elif observed_audio_sample is None:
            mapped_ms = raw_pts_ms
            drift_ms = None
            sync_status = "UNAVAILABLE"
        else:
            observed_audio_sample = _integer(
                observed_audio_sample, "INVALID_AUDIO_SAMPLE"
            )
            mapped_ms = self._sample_ms(observed_audio_sample)
            drift_ms = raw_pts_ms - mapped_ms
            sync_status = (
                "DEGRADED"
                if abs(drift_ms) >= self.severe_drift_ms
                else "SYNCED"
            )

        return {
            "clockId": self.clock_id,
            "rawPts": raw_pts,
            "ptsTimebaseNum": timebase_num,
            "ptsTimebaseDen": timebase_den,
            "rawPtsMs": raw_pts_ms,
            "mappedMs": mapped_ms,
            "driftMs": drift_ms,
            "syncStatus": sync_status,
        }

    def snapshot(self) -> dict:
        return {
            "clockId": self.clock_id,
            "masterSource": self.master_source,
            "sampleRate": self.sample_rate,
            "severeDriftMs": self.severe_drift_ms,
            "audioChunks": [
                copy.deepcopy(self._audio_chunks[key])
                for key in sorted(self._audio_chunks)
            ],
            "nextSample": self.next_sample,
        }

    @classmethod
    def from_snapshot(cls, value: dict) -> "MediaClock":
        if not isinstance(value, dict):
            raise MediaClockError("INVALID_CLOCK_SNAPSHOT")
        clock = cls(
            clock_id=value.get("clockId"),
            master_source=value.get("masterSource"),
            sample_rate=value.get("sampleRate", 16_000),
            severe_drift_ms=value.get("severeDriftMs", 500),
        )
        for item in value.get("audioChunks") or []:
            if not isinstance(item, dict):
                raise MediaClockError("INVALID_CLOCK_SNAPSHOT")
            clock.record_audio_chunk(
                sequence=item.get("sequence"),
                start_sample=item.get("startSample"),
                sample_count=item.get("sampleCount"),
                declared_start_ms=item.get("declaredStartMs"),
                declared_end_ms=item.get("declaredEndMs"),
            )
        return clock


class ProvisionalSegmentLedger:
    """Enforce monotonic revisions and a terminal FINAL state per segment."""

    def __init__(self, *, correction_horizon_ms: int = 10_000):
        self.correction_horizon_ms = _integer(
            correction_horizon_ms, "INVALID_CORRECTION_HORIZON", minimum=1
        )
        self._entries: dict[str, dict] = {}

    def accept(self, segment: dict, *, observed_at_ms: int) -> bool:
        if not isinstance(segment, dict):
            raise MediaClockError("INVALID_SEGMENT")
        segment_id = str(segment.get("segmentId") or "").strip()
        if not segment_id:
            raise MediaClockError("INVALID_SEGMENT_ID")
        revision = _integer(segment.get("revision"), "INVALID_SEGMENT_REVISION")
        observed_at_ms = _integer(observed_at_ms, "INVALID_OBSERVED_TIME")
        state = str(segment.get("state") or "PROVISIONAL").strip().upper()
        if state not in {"PROVISIONAL", "FINAL"}:
            raise MediaClockError("INVALID_SEGMENT_STATE")

        existing = self._entries.get(segment_id)
        if existing is not None:
            if existing["segment"]["state"] == "FINAL":
                return False
            if revision <= existing["segment"]["revision"]:
                return False
            if (
                state == "PROVISIONAL"
                and observed_at_ms - existing["firstObservedAtMs"]
                > self.correction_horizon_ms
            ):
                return False
            first_observed_at_ms = existing["firstObservedAtMs"]
        else:
            first_observed_at_ms = observed_at_ms

        stored = copy.deepcopy(segment)
        stored["segmentId"] = segment_id
        stored["revision"] = revision
        stored["state"] = state
        self._entries[segment_id] = {
            "segment": stored,
            "firstObservedAtMs": first_observed_at_ms,
            "lastObservedAtMs": observed_at_ms,
        }
        return True

    def current(self, segment_id: str) -> dict | None:
        entry = self._entries.get(str(segment_id))
        return copy.deepcopy(entry["segment"]) if entry else None

    def values(self) -> list[dict]:
        return [
            copy.deepcopy(item["segment"])
            for _, item in sorted(self._entries.items())
        ]
