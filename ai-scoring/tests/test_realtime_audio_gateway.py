import hashlib
import json
import os

import pytest

from app.services.media_evidence.realtime_gateway import (
    AudioChunkJournal,
    AudioChunkRejected,
)


def _payload(text: str) -> bytes:
    return text.encode("utf-8")


def test_contiguous_chunks_are_accepted_and_advance_next_sequence(tmp_path):
    journal = AudioChunkJournal(str(tmp_path), "session-1")

    first = journal.append(0, 0, 1000, _payload("first"))
    second = journal.append(1, 1000, 2000, _payload("second"))

    assert first["status"] == "accepted"
    assert first["nextSequence"] == 1
    assert second["status"] == "accepted"
    assert second["nextSequence"] == 2
    assert second["missingSequences"] == []


def test_same_sequence_and_hash_is_idempotent(tmp_path):
    journal = AudioChunkJournal(str(tmp_path), "session-1")
    payload = _payload("same")
    journal.append(0, 0, 1000, payload)
    size_before = os.path.getsize(journal.data_path)

    duplicate = journal.append(0, 0, 1000, payload)

    assert duplicate["status"] == "duplicate"
    assert os.path.getsize(journal.data_path) == size_before


def test_same_sequence_with_different_payload_is_rejected(tmp_path):
    journal = AudioChunkJournal(str(tmp_path), "session-1")
    journal.append(0, 0, 1000, _payload("first"))

    with pytest.raises(AudioChunkRejected) as raised:
        journal.append(0, 0, 1000, _payload("changed"))

    assert raised.value.code == "SEQUENCE_HASH_CONFLICT"


def test_out_of_order_chunks_are_persisted_but_gap_remains_visible(tmp_path):
    journal = AudioChunkJournal(str(tmp_path), "session-1")

    receipt = journal.append(2, 2000, 3000, _payload("third"))

    assert receipt["status"] == "accepted"
    assert receipt["nextSequence"] == 0
    assert receipt["missingSequences"] == [0, 1]

    summary = journal.finalize()
    assert summary["integrityStatus"] == "incomplete"
    assert summary["missingSequences"] == [0, 1]


def test_declared_payload_hash_must_match_bytes(tmp_path):
    journal = AudioChunkJournal(str(tmp_path), "session-1")

    with pytest.raises(AudioChunkRejected) as raised:
        journal.append(
            0,
            0,
            1000,
            _payload("actual"),
            declared_hash="sha256:" + hashlib.sha256(b"other").hexdigest(),
        )

    assert raised.value.code == "PAYLOAD_HASH_MISMATCH"


@pytest.mark.parametrize(
    ("sequence", "start_ms", "end_ms", "payload", "code"),
    [
        (-1, 0, 1000, b"data", "INVALID_SEQUENCE"),
        (0, 1000, 999, b"data", "INVALID_TIME_RANGE"),
        (0, 0, 1000, b"", "EMPTY_AUDIO_CHUNK"),
        (0, 0, 1000, b"012345", "AUDIO_CHUNK_TOO_LARGE"),
    ],
)
def test_invalid_chunks_are_rejected(
    tmp_path, sequence, start_ms, end_ms, payload, code
):
    journal = AudioChunkJournal(str(tmp_path), "session-1", max_chunk_bytes=5)

    with pytest.raises(AudioChunkRejected) as raised:
        journal.append(sequence, start_ms, end_ms, payload)

    assert raised.value.code == code


def test_journal_recovers_deduplication_state_after_restart(tmp_path):
    first = AudioChunkJournal(str(tmp_path), "session-1")
    first.append(0, 0, 1000, _payload("first"))
    first.close()

    recovered = AudioChunkJournal(str(tmp_path), "session-1")
    receipt = recovered.append(0, 0, 1000, _payload("first"))

    assert receipt["status"] == "duplicate"
    assert recovered.next_sequence == 1


def test_finalize_is_atomic_idempotent_and_auditable(tmp_path):
    journal = AudioChunkJournal(str(tmp_path), "session-1")
    journal.append(0, 0, 1000, _payload("first"))
    journal.append(1, 1000, 2000, _payload("second"))

    first = journal.finalize()
    second = journal.finalize()

    assert first == second
    assert first["status"] == "FINAL"
    assert first["integrityStatus"] == "complete"
    assert first["acceptedChunkCount"] == 2
    assert first["totalBytes"] == len(_payload("firstsecond"))
    assert first["firstSequence"] == 0
    assert first["lastSequence"] == 1
    assert first["nextSequence"] == 2
    assert first["missingSequences"] == []
    assert first["timelineCoverage"] == 1.0
    assert first["dataHash"].startswith("sha256:")
    assert json.loads(open(journal.summary_path, encoding="utf-8").read()) == first
    assert list(tmp_path.glob("*.tmp")) == []


def test_append_after_finalize_is_rejected(tmp_path):
    journal = AudioChunkJournal(str(tmp_path), "session-1")
    journal.append(0, 0, 1000, _payload("first"))
    journal.finalize()

    with pytest.raises(AudioChunkRejected) as raised:
        journal.append(1, 1000, 2000, _payload("late"))

    assert raised.value.code == "JOURNAL_FINALIZED"
