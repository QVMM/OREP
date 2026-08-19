import hashlib

import pytest

from app.services.media_evidence.realtime_gateway import (
    AudioChunkJournal,
    AudioChunkRejected,
    RealtimeAudioProtocol,
    get_audio_chunk_journal,
    select_transport_mode,
)


def _hash(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _metadata(sequence=0, start_ms=0, end_ms=1000, payload=b"pcm"):
    return {
        "type": "audio_chunk",
        "sequence": sequence,
        "startMs": start_ms,
        "endMs": end_ms,
        "payloadHash": _hash(payload),
    }


def test_v2_requires_hello_then_pairs_metadata_with_binary(tmp_path):
    forwarded = []
    protocol = RealtimeAudioProtocol(
        AudioChunkJournal(str(tmp_path), "session-1"), forwarded.append
    )

    ready = protocol.handle_control(
        {
            "type": "hello",
            "protocol": "media-evidence-v2",
            "sampleRate": 16000,
            "channels": 1,
        }
    )
    pending = protocol.handle_control(_metadata())
    ack = protocol.handle_binary(b"pcm")

    assert ready == {
        "type": "ready",
        "protocol": "media-evidence-v2",
        "sampleRate": 16000,
        "channels": 1,
        "nextSequence": 0,
    }
    assert pending == {"type": "chunk_metadata_accepted", "sequence": 0}
    assert ack["type"] == "ack"
    assert ack["status"] == "accepted"
    assert ack["providerForwarded"] is True
    assert ack["nextSequence"] == 1
    assert forwarded == [b"pcm"]


def test_protocol_rejects_binary_without_metadata(tmp_path):
    protocol = RealtimeAudioProtocol(AudioChunkJournal(str(tmp_path), "s"), lambda _: None)
    protocol.handle_control(
        {"type": "hello", "protocol": "media-evidence-v2", "sampleRate": 16000, "channels": 1}
    )

    with pytest.raises(AudioChunkRejected) as raised:
        protocol.handle_binary(b"pcm")

    assert raised.value.code == "BINARY_WITHOUT_METADATA"


def test_protocol_rejects_chunk_before_hello_and_double_metadata(tmp_path):
    protocol = RealtimeAudioProtocol(AudioChunkJournal(str(tmp_path), "s"), lambda _: None)

    with pytest.raises(AudioChunkRejected) as before_hello:
        protocol.handle_control(_metadata())
    assert before_hello.value.code == "HELLO_REQUIRED"

    protocol.handle_control(
        {"type": "hello", "protocol": "media-evidence-v2", "sampleRate": 16000, "channels": 1}
    )
    protocol.handle_control(_metadata())
    with pytest.raises(AudioChunkRejected) as double:
        protocol.handle_control(_metadata(sequence=1, start_ms=1000, end_ms=2000))
    assert double.value.code == "PENDING_BINARY_REQUIRED"


def test_wrong_protocol_and_audio_format_are_rejected(tmp_path):
    protocol = RealtimeAudioProtocol(AudioChunkJournal(str(tmp_path), "s"), lambda _: None)

    with pytest.raises(AudioChunkRejected) as wrong_protocol:
        protocol.handle_control(
            {"type": "hello", "protocol": "v1", "sampleRate": 16000, "channels": 1}
        )
    assert wrong_protocol.value.code == "UNSUPPORTED_PROTOCOL"

    with pytest.raises(AudioChunkRejected) as wrong_format:
        protocol.handle_control(
            {
                "type": "hello",
                "protocol": "media-evidence-v2",
                "sampleRate": 48000,
                "channels": 2,
            }
        )
    assert wrong_format.value.code == "UNSUPPORTED_AUDIO_FORMAT"


def test_provider_failure_keeps_durable_chunk_and_reports_degraded(tmp_path):
    def fail(_payload):
        raise RuntimeError("provider disconnected")

    journal = AudioChunkJournal(str(tmp_path), "s")
    protocol = RealtimeAudioProtocol(journal, fail)
    protocol.handle_control(
        {"type": "hello", "protocol": "media-evidence-v2", "sampleRate": 16000, "channels": 1}
    )
    protocol.handle_control(_metadata())

    ack = protocol.handle_binary(b"pcm")

    assert ack["status"] == "accepted"
    assert ack["providerForwarded"] is False
    assert ack["providerStatus"] == "degraded"
    assert ack["providerError"] == "provider disconnected"
    assert journal.next_sequence == 1


def test_duplicate_chunk_is_not_forwarded_twice(tmp_path):
    forwarded = []
    protocol = RealtimeAudioProtocol(
        AudioChunkJournal(str(tmp_path), "s"), forwarded.append
    )
    hello = {"type": "hello", "protocol": "media-evidence-v2", "sampleRate": 16000, "channels": 1}
    protocol.handle_control(hello)
    protocol.handle_control(_metadata())
    protocol.handle_binary(b"pcm")
    protocol.handle_control(_metadata())
    duplicate = protocol.handle_binary(b"pcm")

    assert duplicate["status"] == "duplicate"
    assert duplicate["providerForwarded"] is False
    assert forwarded == [b"pcm"]


def test_transport_disconnect_does_not_finalize_journal(tmp_path):
    journal = AudioChunkJournal(str(tmp_path), "s")
    protocol = RealtimeAudioProtocol(journal, lambda _: None)
    protocol.handle_control(
        {"type": "hello", "protocol": "media-evidence-v2", "sampleRate": 16000, "channels": 1}
    )
    protocol.handle_control(_metadata())
    protocol.handle_binary(b"pcm")

    protocol.close_transport()

    recovered = AudioChunkJournal(str(tmp_path), "s")
    assert recovered.next_sequence == 1
    assert not recovered.is_finalized


def test_stop_finalizes_idempotently_and_rejects_unpaired_metadata(tmp_path):
    protocol = RealtimeAudioProtocol(
        AudioChunkJournal(str(tmp_path), "s"), lambda _: None
    )
    protocol.handle_control(
        {"type": "hello", "protocol": "media-evidence-v2", "sampleRate": 16000, "channels": 1}
    )
    protocol.handle_control(_metadata())
    with pytest.raises(AudioChunkRejected) as pending:
        protocol.handle_control({"type": "stop"})
    assert pending.value.code == "PENDING_BINARY_REQUIRED"

    protocol.handle_binary(b"pcm")
    first = protocol.handle_control({"type": "stop"})
    second = protocol.handle_control({"type": "stop"})

    assert first == second
    assert first["type"] == "finalized"
    assert first["summary"]["status"] == "FINAL"


def test_transport_mode_preserves_legacy_until_both_ends_enable_v2():
    assert select_transport_mode(False, None) == "legacy_raw"
    assert select_transport_mode(True, None) == "legacy_raw"
    assert select_transport_mode(True, "media-evidence-v2") == "media-evidence-v2"

    with pytest.raises(AudioChunkRejected) as disabled:
        select_transport_mode(False, "media-evidence-v2")
    assert disabled.value.code == "LIVE_GATEWAY_DISABLED"


def test_registry_reuses_one_journal_for_reconnects(tmp_path):
    first = get_audio_chunk_journal(str(tmp_path), "same-session")
    second = get_audio_chunk_journal(str(tmp_path), "same-session")

    assert first is second


def test_clocked_v2_uses_audio_samples_instead_of_declared_milliseconds(tmp_path):
    protocol = RealtimeAudioProtocol(
        AudioChunkJournal(str(tmp_path), "clocked"), lambda _: None
    )
    ready = protocol.handle_control(
        {
            "type": "hello",
            "protocol": "media-evidence-v2",
            "sampleRate": 16000,
            "channels": 1,
            "clockId": "clock-live-1",
            "masterSource": "AUDIO_SAMPLE_CLOCK",
        }
    )
    payload = bytes(32_000)
    protocol.handle_control(
        {
            **_metadata(start_ms=37, end_ms=1_041, payload=payload),
            "startSample": 0,
            "sampleCount": 16_000,
        }
    )

    ack = protocol.handle_binary(payload)
    summary = protocol.handle_control({"type": "stop"})["summary"]

    assert ready["clockId"] == "clock-live-1"
    assert ready["nextSample"] == 0
    assert ack["startMs"] == 0
    assert ack["endMs"] == 1000
    assert ack["declaredDriftMs"] == 41
    assert ack["nextSample"] == 16_000
    assert summary["mediaClock"]["clockId"] == "clock-live-1"
    assert summary["mediaClock"]["nextSample"] == 16_000


def test_reconnect_preserves_clock_and_rejects_a_different_clock_id(tmp_path):
    journal = AudioChunkJournal(str(tmp_path), "clocked")
    first = RealtimeAudioProtocol(journal, lambda _: None)
    hello = {
        "type": "hello",
        "protocol": "media-evidence-v2",
        "sampleRate": 16000,
        "channels": 1,
        "clockId": "clock-live-1",
        "masterSource": "AUDIO_SAMPLE_CLOCK",
    }
    first.handle_control(hello)
    payload = bytes(16_000)
    first.handle_control(
        {
            **_metadata(start_ms=0, end_ms=500, payload=payload),
            "startSample": 0,
            "sampleCount": 8_000,
        }
    )
    first.handle_binary(payload)
    first.close_transport()

    recovered = AudioChunkJournal(str(tmp_path), "clocked")
    second = RealtimeAudioProtocol(recovered, lambda _: None)
    ready = second.handle_control(hello)
    assert ready["clockId"] == "clock-live-1"
    assert ready["nextSequence"] == 1
    assert ready["nextSample"] == 8_000

    conflicting = RealtimeAudioProtocol(recovered, lambda _: None)
    with pytest.raises(AudioChunkRejected) as raised:
        conflicting.handle_control({**hello, "clockId": "clock-live-2"})
    assert raised.value.code == "CLOCK_ID_CONFLICT"


def test_clocked_chunk_requires_sample_range_and_matching_pcm_length(tmp_path):
    protocol = RealtimeAudioProtocol(
        AudioChunkJournal(str(tmp_path), "clocked"), lambda _: None
    )
    protocol.handle_control(
        {
            "type": "hello",
            "protocol": "media-evidence-v2",
            "sampleRate": 16000,
            "channels": 1,
            "clockId": "clock-live-1",
            "masterSource": "AUDIO_SAMPLE_CLOCK",
        }
    )

    with pytest.raises(AudioChunkRejected) as missing:
        protocol.handle_control(_metadata())
    assert missing.value.code == "INVALID_CHUNK_METADATA"

    protocol.handle_control(
        {
            **_metadata(payload=b"pcm"),
            "startSample": 0,
            "sampleCount": 16_000,
        }
    )
    with pytest.raises(AudioChunkRejected) as mismatch:
        protocol.handle_binary(b"pcm")
    assert mismatch.value.code == "AUDIO_SAMPLE_COUNT_MISMATCH"
