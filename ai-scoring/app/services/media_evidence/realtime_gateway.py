"""Durable, idempotent PCM chunk journal for live evidence transport."""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
from pathlib import Path
from typing import Any

from .media_clock import MediaClock, MediaClockError


_JOURNAL_REGISTRY: dict[tuple[str, str], "AudioChunkJournal"] = {}
_JOURNAL_REGISTRY_LOCK = threading.Lock()


class AudioChunkRejected(ValueError):
    """Stable protocol failure raised before a chunk can be acknowledged."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _safe_session_id(session_id: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_.-]", "_", str(session_id or ""))
    if not value:
        raise AudioChunkRejected("INVALID_SESSION_ID", "session id is empty")
    return value[:160]


def _sha256(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


class AudioChunkJournal:
    """Append-only audio payload log with a recoverable sequence/hash index."""

    def __init__(
        self,
        root_dir: str,
        session_id: str,
        *,
        max_chunk_bytes: int = 128 * 1024,
    ):
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.session_id = _safe_session_id(session_id)
        self.max_chunk_bytes = max(1, int(max_chunk_bytes))
        prefix = f"audio_gateway_{self.session_id}"
        self.data_path = str(self.root_dir / f"{prefix}.pcmjournal")
        self.index_path = str(self.root_dir / f"{prefix}.jsonl")
        self.clock_path = str(self.root_dir / f"{prefix}.clock.json")
        self.summary_path = str(self.root_dir / f"{prefix}.summary.json")
        self._lock = threading.RLock()
        self._entries: dict[int, dict] = {}
        self._clock: MediaClock | None = None
        self._final_summary: dict | None = None
        self._data_handle = None
        self._index_handle = None
        self._load_state()

    @property
    def next_sequence(self) -> int:
        sequence = 0
        while sequence in self._entries:
            sequence += 1
        return sequence

    @property
    def is_finalized(self) -> bool:
        return self._final_summary is not None

    @property
    def media_clock_snapshot(self) -> dict | None:
        return self._clock.snapshot() if self._clock is not None else None

    def _load_state(self) -> None:
        if os.path.exists(self.index_path):
            with open(self.index_path, "r", encoding="utf-8") as handle:
                for line_no, line in enumerate(handle, start=1):
                    if not line.strip():
                        continue
                    try:
                        item = json.loads(line)
                        sequence = int(item["sequence"])
                        if sequence in self._entries:
                            if self._entries[sequence].get("payloadHash") != item.get("payloadHash"):
                                raise ValueError("conflicting duplicate sequence")
                            continue
                        self._entries[sequence] = item
                    except Exception as error:
                        raise AudioChunkRejected(
                            "JOURNAL_INDEX_CORRUPT",
                            f"invalid journal index line {line_no}: {error}",
                        ) from error
        if os.path.exists(self.summary_path):
            with open(self.summary_path, "r", encoding="utf-8") as handle:
                self._final_summary = json.load(handle)
        if os.path.exists(self.clock_path):
            try:
                with open(self.clock_path, "r", encoding="utf-8") as handle:
                    snapshot = json.load(handle)
                self._clock = MediaClock.from_snapshot(snapshot)
                # The JSONL entry is committed before the sidecar snapshot. If a
                # process died between those fsyncs, replay the missing mappings.
                for sequence in sorted(self._entries):
                    item = self._entries[sequence]
                    if "startSample" not in item:
                        continue
                    self._clock.record_audio_chunk(
                        sequence=int(item["sequence"]),
                        start_sample=int(item["startSample"]),
                        sample_count=int(item["sampleCount"]),
                        declared_start_ms=item.get("declaredStartMs"),
                        declared_end_ms=item.get("declaredEndMs"),
                    )
            except (OSError, ValueError, TypeError, MediaClockError) as error:
                raise AudioChunkRejected(
                    "CLOCK_STATE_CORRUPT", f"invalid media clock state: {error}"
                ) from error

    @staticmethod
    def _write_json_atomic(path: str, value: dict) -> None:
        temporary_path = path + ".tmp"
        try:
            with open(temporary_path, "w", encoding="utf-8") as handle:
                json.dump(value, handle, ensure_ascii=False, sort_keys=True)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, path)
        except Exception:
            try:
                os.unlink(temporary_path)
            except FileNotFoundError:
                pass
            raise

    def bind_clock(
        self,
        clock_id: str,
        *,
        master_source: str = "AUDIO_SAMPLE_CLOCK",
        sample_rate: int = 16_000,
    ) -> dict:
        """Bind one durable clock identity to all reconnects of this session."""

        with self._lock:
            try:
                candidate = MediaClock(
                    clock_id=clock_id,
                    master_source=master_source,
                    sample_rate=sample_rate,
                )
            except MediaClockError as error:
                raise AudioChunkRejected(str(error), str(error)) from error
            if self._clock is not None:
                if self._clock.clock_id != candidate.clock_id:
                    raise AudioChunkRejected(
                        "CLOCK_ID_CONFLICT", "session is already bound to another clock"
                    )
                if (
                    self._clock.master_source != candidate.master_source
                    or self._clock.sample_rate != candidate.sample_rate
                ):
                    raise AudioChunkRejected(
                        "CLOCK_FORMAT_CONFLICT",
                        "clock master source or sample rate changed",
                    )
                return self._clock.snapshot()
            self._clock = candidate
            self._write_json_atomic(self.clock_path, self._clock.snapshot())
            return self._clock.snapshot()

    def _ensure_open(self) -> None:
        if self._data_handle is None:
            self._data_handle = open(self.data_path, "ab")
        if self._index_handle is None:
            self._index_handle = open(self.index_path, "a", encoding="utf-8")

    @staticmethod
    def _validate_integer(value: Any, code: str) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise AudioChunkRejected(code, f"expected integer, got {type(value).__name__}")
        return value

    def _validate(
        self,
        sequence: Any,
        start_ms: Any,
        end_ms: Any,
        payload: Any,
    ) -> tuple[int, int, int, bytes]:
        sequence = self._validate_integer(sequence, "INVALID_SEQUENCE")
        start_ms = self._validate_integer(start_ms, "INVALID_TIME_RANGE")
        end_ms = self._validate_integer(end_ms, "INVALID_TIME_RANGE")
        if sequence < 0 or sequence > 1_000_000:
            raise AudioChunkRejected("INVALID_SEQUENCE", "sequence outside allowed range")
        if start_ms < 0 or end_ms < start_ms:
            raise AudioChunkRejected("INVALID_TIME_RANGE", "invalid audio time range")
        if not isinstance(payload, (bytes, bytearray, memoryview)):
            raise AudioChunkRejected("INVALID_AUDIO_CHUNK", "payload must be bytes")
        payload = bytes(payload)
        if not payload:
            raise AudioChunkRejected("EMPTY_AUDIO_CHUNK", "audio chunk is empty")
        if len(payload) > self.max_chunk_bytes:
            raise AudioChunkRejected(
                "AUDIO_CHUNK_TOO_LARGE",
                f"audio chunk exceeds {self.max_chunk_bytes} bytes",
            )
        return sequence, start_ms, end_ms, payload

    def _missing_sequences(self) -> list[int]:
        if not self._entries:
            return []
        return [
            sequence
            for sequence in range(max(self._entries) + 1)
            if sequence not in self._entries
        ]

    def _receipt(self, status: str, sequence: int, payload_hash: str) -> dict:
        receipt = {
            "status": status,
            "sequence": sequence,
            "payloadHash": payload_hash,
            "nextSequence": self.next_sequence,
            "missingSequences": self._missing_sequences(),
        }
        entry = self._entries.get(sequence)
        if entry is not None and "startSample" in entry:
            receipt.update(
                {
                    "clockId": entry.get("clockId"),
                    "startSample": entry.get("startSample"),
                    "endSample": entry.get("endSample"),
                    "sampleCount": entry.get("sampleCount"),
                    "startMs": entry.get("startMs"),
                    "endMs": entry.get("endMs"),
                    "declaredDriftMs": entry.get("declaredDriftMs"),
                    "syncStatus": entry.get("syncStatus"),
                    "nextSample": self._clock.next_sample if self._clock else None,
                }
            )
        return receipt

    def append(
        self,
        sequence: int,
        start_ms: int,
        end_ms: int,
        payload: bytes,
        *,
        declared_hash: str | None = None,
        clock_id: str | None = None,
        start_sample: int | None = None,
        sample_count: int | None = None,
    ) -> dict:
        """Durably append a chunk before returning an acknowledgement receipt."""

        with self._lock:
            if self._final_summary is not None:
                raise AudioChunkRejected("JOURNAL_FINALIZED", "journal is already final")
            sequence, start_ms, end_ms, payload = self._validate(
                sequence, start_ms, end_ms, payload
            )
            clock_mapping = None
            candidate_clock = None
            if clock_id is not None:
                if self._clock is None or self._clock.clock_id != str(clock_id):
                    raise AudioChunkRejected(
                        "CLOCK_ID_CONFLICT", "audio chunk clock does not match journal"
                    )
                if (
                    isinstance(sample_count, bool)
                    or not isinstance(sample_count, int)
                    or sample_count <= 0
                    or len(payload) != sample_count * 2
                ):
                    raise AudioChunkRejected(
                        "AUDIO_SAMPLE_COUNT_MISMATCH",
                        "16-bit mono PCM bytes must equal sampleCount * 2",
                    )
                try:
                    candidate_clock = MediaClock.from_snapshot(self._clock.snapshot())
                    clock_mapping = candidate_clock.record_audio_chunk(
                        sequence=sequence,
                        start_sample=start_sample,
                        sample_count=sample_count,
                        declared_start_ms=start_ms,
                        declared_end_ms=end_ms,
                    )
                except MediaClockError as error:
                    raise AudioChunkRejected(str(error), str(error)) from error
                start_ms = clock_mapping["startMs"]
                end_ms = clock_mapping["endMs"]
            elif self._clock is not None:
                raise AudioChunkRejected(
                    "CLOCK_METADATA_REQUIRED",
                    "clocked journal requires startSample and sampleCount",
                )
            payload_hash = _sha256(payload)
            if declared_hash and str(declared_hash).lower() != payload_hash:
                raise AudioChunkRejected(
                    "PAYLOAD_HASH_MISMATCH", "declared hash does not match audio bytes"
                )

            existing = self._entries.get(sequence)
            if existing is not None:
                if existing.get("payloadHash") != payload_hash:
                    raise AudioChunkRejected(
                        "SEQUENCE_HASH_CONFLICT",
                        "sequence was previously stored with a different payload",
                    )
                return self._receipt("duplicate", sequence, payload_hash)

            self._ensure_open()
            offset = self._data_handle.tell()
            self._data_handle.write(payload)
            self._data_handle.flush()
            os.fsync(self._data_handle.fileno())

            entry = {
                "sequence": sequence,
                "startMs": start_ms,
                "endMs": end_ms,
                "offset": offset,
                "length": len(payload),
                "payloadHash": payload_hash,
            }
            if clock_mapping is not None:
                entry.update(clock_mapping)
            self._index_handle.write(
                json.dumps(entry, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                + "\n"
            )
            self._index_handle.flush()
            os.fsync(self._index_handle.fileno())
            self._entries[sequence] = entry
            if candidate_clock is not None:
                self._clock = candidate_clock
                self._write_json_atomic(self.clock_path, self._clock.snapshot())
            return self._receipt("accepted", sequence, payload_hash)

    @staticmethod
    def _timeline_coverage(entries: list[dict]) -> float:
        intervals = sorted(
            (int(item["startMs"]), int(item["endMs"]))
            for item in entries
            if int(item["endMs"]) > int(item["startMs"])
        )
        if not intervals:
            return 0.0
        span = intervals[-1][1] - intervals[0][0]
        if span <= 0:
            return 0.0
        covered = 0
        current_start, current_end = intervals[0]
        for start_ms, end_ms in intervals[1:]:
            if start_ms <= current_end:
                current_end = max(current_end, end_ms)
            else:
                covered += current_end - current_start
                current_start, current_end = start_ms, end_ms
        covered += current_end - current_start
        return round(min(1.0, covered / span), 6)

    def finalize(self) -> dict:
        """Freeze one auditable summary; repeated calls return the same object value."""

        with self._lock:
            if self._final_summary is not None:
                return dict(self._final_summary)
            self.close()

            entries = [self._entries[key] for key in sorted(self._entries)]
            missing = self._missing_sequences()
            hash_view = [
                {
                    key: item.get(key)
                    for key in (
                        "sequence",
                        "clockId",
                        "startSample",
                        "endSample",
                        "sampleCount",
                        "startMs",
                        "endMs",
                        "declaredStartMs",
                        "declaredEndMs",
                        "declaredDriftMs",
                        "syncStatus",
                        "length",
                        "payloadHash",
                    )
                    if key in item
                }
                for item in entries
            ]
            digest_input = json.dumps(
                hash_view, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
            summary = {
                "status": "FINAL",
                "sessionId": self.session_id,
                "integrityStatus": "complete" if entries and not missing else "incomplete",
                "acceptedChunkCount": len(entries),
                "totalBytes": sum(int(item["length"]) for item in entries),
                "firstSequence": entries[0]["sequence"] if entries else None,
                "lastSequence": entries[-1]["sequence"] if entries else None,
                "nextSequence": self.next_sequence,
                "missingSequences": missing,
                "timelineCoverage": self._timeline_coverage(entries),
                "dataHash": _sha256(digest_input),
            }
            if self._clock is not None:
                summary["mediaClock"] = self._clock.snapshot()
            temporary_path = self.summary_path + ".tmp"
            try:
                with open(temporary_path, "w", encoding="utf-8") as handle:
                    json.dump(summary, handle, ensure_ascii=False, sort_keys=True)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary_path, self.summary_path)
            except Exception:
                try:
                    os.unlink(temporary_path)
                except FileNotFoundError:
                    pass
                raise
            self._final_summary = summary
            return dict(summary)

    def close(self) -> None:
        with self._lock:
            for attribute in ("_data_handle", "_index_handle"):
                handle = getattr(self, attribute)
                if handle is not None:
                    handle.flush()
                    os.fsync(handle.fileno())
                    handle.close()
                    setattr(self, attribute, None)

    def __enter__(self) -> "AudioChunkJournal":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


class RealtimeAudioProtocol:
    """State machine for the v2 JSON-metadata + binary-payload WebSocket protocol."""

    PROTOCOL = "media-evidence-v2"
    SAMPLE_RATE = 16_000
    CHANNELS = 1

    def __init__(self, journal: AudioChunkJournal, provider_audio_sink):
        self.journal = journal
        self.provider_audio_sink = provider_audio_sink
        self._hello_received = False
        self._pending_metadata: dict | None = None
        self._stopped_response: dict | None = None
        self._clock_id: str | None = None

    def _require_hello(self) -> None:
        if not self._hello_received:
            raise AudioChunkRejected("HELLO_REQUIRED", "v2 hello must be sent first")

    def handle_control(self, message: dict) -> dict:
        if not isinstance(message, dict):
            raise AudioChunkRejected("INVALID_CONTROL_MESSAGE", "control message must be an object")
        message_type = str(message.get("type") or "")

        if message_type == "hello":
            if message.get("protocol") != self.PROTOCOL:
                raise AudioChunkRejected("UNSUPPORTED_PROTOCOL", "unsupported media protocol")
            if (
                message.get("sampleRate") != self.SAMPLE_RATE
                or message.get("channels") != self.CHANNELS
            ):
                raise AudioChunkRejected(
                    "UNSUPPORTED_AUDIO_FORMAT", "only 16 kHz mono PCM is accepted"
                )
            if self._stopped_response is not None:
                raise AudioChunkRejected("JOURNAL_FINALIZED", "audio stream is already final")
            clock_id = str(message.get("clockId") or "").strip() or None
            existing_clock = self.journal.media_clock_snapshot
            if clock_id is not None:
                clock = self.journal.bind_clock(
                    clock_id,
                    master_source=message.get("masterSource")
                    or "AUDIO_SAMPLE_CLOCK",
                    sample_rate=self.SAMPLE_RATE,
                )
                self._clock_id = clock["clockId"]
            elif existing_clock is not None:
                raise AudioChunkRejected(
                    "CLOCK_METADATA_REQUIRED",
                    "reconnect must provide the journal clock id",
                )
            self._hello_received = True
            response = {
                "type": "ready",
                "protocol": self.PROTOCOL,
                "sampleRate": self.SAMPLE_RATE,
                "channels": self.CHANNELS,
                "nextSequence": self.journal.next_sequence,
            }
            if self._clock_id is not None:
                response.update(
                    {
                        "clockId": self._clock_id,
                        "masterSource": "AUDIO_SAMPLE_CLOCK",
                        "nextSample": self.journal.media_clock_snapshot["nextSample"],
                    }
                )
            return response

        self._require_hello()
        if message_type == "audio_chunk":
            if self._stopped_response is not None:
                raise AudioChunkRejected("JOURNAL_FINALIZED", "audio stream is already final")
            if self._pending_metadata is not None:
                raise AudioChunkRejected(
                    "PENDING_BINARY_REQUIRED", "previous metadata has no binary payload"
                )
            required = (
                ("sequence", "startMs", "endMs", "startSample", "sampleCount")
                if self._clock_id is not None
                else ("sequence", "startMs", "endMs")
            )
            if any(key not in message for key in required):
                raise AudioChunkRejected(
                    "INVALID_CHUNK_METADATA", "chunk metadata is incomplete"
                )
            self._pending_metadata = {
                "sequence": message.get("sequence"),
                "startMs": message.get("startMs"),
                "endMs": message.get("endMs"),
                "payloadHash": message.get("payloadHash"),
                "clockId": self._clock_id,
                "startSample": message.get("startSample"),
                "sampleCount": message.get("sampleCount"),
            }
            return {
                "type": "chunk_metadata_accepted",
                "sequence": message.get("sequence"),
            }

        if message_type == "stop":
            if self._pending_metadata is not None:
                raise AudioChunkRejected(
                    "PENDING_BINARY_REQUIRED", "cannot stop before pending binary arrives"
                )
            if self._stopped_response is None:
                self._stopped_response = {
                    "type": "finalized",
                    "summary": self.journal.finalize(),
                }
            return dict(self._stopped_response)

        raise AudioChunkRejected(
            "UNSUPPORTED_CONTROL_MESSAGE", f"unsupported message type: {message_type}"
        )

    def handle_binary(self, payload: bytes) -> dict:
        self._require_hello()
        if self._stopped_response is not None:
            raise AudioChunkRejected("JOURNAL_FINALIZED", "audio stream is already final")
        if self._pending_metadata is None:
            raise AudioChunkRejected(
                "BINARY_WITHOUT_METADATA", "binary payload has no chunk metadata"
            )

        metadata = self._pending_metadata
        self._pending_metadata = None
        receipt = self.journal.append(
            metadata["sequence"],
            metadata["startMs"],
            metadata["endMs"],
            payload,
            declared_hash=metadata.get("payloadHash"),
            clock_id=metadata.get("clockId"),
            start_sample=metadata.get("startSample"),
            sample_count=metadata.get("sampleCount"),
        )

        provider_forwarded = False
        provider_status = "skipped" if receipt["status"] == "duplicate" else "available"
        provider_error = None
        if receipt["status"] == "accepted":
            try:
                self.provider_audio_sink(bytes(payload))
                provider_forwarded = True
            except Exception as error:
                provider_status = "degraded"
                provider_error = str(error)

        return {
            "type": "ack",
            **receipt,
            "providerForwarded": provider_forwarded,
            "providerStatus": provider_status,
            "providerError": provider_error,
        }

    def close_transport(self) -> None:
        """Close one socket transport without declaring the meeting stream final."""

        self._pending_metadata = None
        self.journal.close()


def select_transport_mode(gateway_enabled: bool, requested_protocol: str | None) -> str:
    """Keep legacy raw PCM unless the client explicitly requests an enabled v2."""

    if requested_protocol in (None, "", "legacy_raw"):
        return "legacy_raw"
    if requested_protocol != RealtimeAudioProtocol.PROTOCOL:
        raise AudioChunkRejected("UNSUPPORTED_PROTOCOL", "unsupported media protocol")
    if not gateway_enabled:
        raise AudioChunkRejected(
            "LIVE_GATEWAY_DISABLED", "live media gateway is not enabled"
        )
    return RealtimeAudioProtocol.PROTOCOL


def get_audio_chunk_journal(
    root_dir: str,
    session_id: str,
    *,
    max_chunk_bytes: int = 128 * 1024,
) -> AudioChunkJournal:
    """Return the single in-process journal instance used across reconnects."""

    safe_session = _safe_session_id(session_id)
    key = (os.path.abspath(root_dir), safe_session)
    with _JOURNAL_REGISTRY_LOCK:
        journal = _JOURNAL_REGISTRY.get(key)
        if journal is None:
            journal = AudioChunkJournal(
                key[0], safe_session, max_chunk_bytes=max_chunk_bytes
            )
            _JOURNAL_REGISTRY[key] = journal
        return journal
