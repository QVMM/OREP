import os
import threading
import time
from unittest.mock import patch

import pytest

from app.services.asr_service import (
    LongAudioTranscriptionError,
    _parse_asr_result,
    transcribe_long_audio,
)


class FakeAudio:
    def __init__(self, duration_ms):
        self.duration_ms = duration_ms

    def __len__(self):
        return self.duration_ms

    def __getitem__(self, key):
        start = key.start or 0
        stop = min(key.stop or self.duration_ms, self.duration_ms)
        return FakeChunk(stop - start)


class FakeChunk(FakeAudio):
    def export(self, path, format):
        assert format == "wav"
        return path


class FakeRecognitionResult:
    def __init__(self, sentences):
        self.sentences = sentences

    def get_sentence(self):
        return self.sentences

    def get(self, key, default=None):
        return {"request_id": "request-1"}.get(key, default)


def test_file_asr_does_not_invent_speaker_zero_when_provider_returns_none():
    result = _parse_asr_result(FakeRecognitionResult([
        {"text": "真实转写", "begin_time": 0, "end_time": 1000, "speaker_id": None}
    ]))

    assert "speaker" not in result["segments"][0]
    assert "confidence" not in result["segments"][0]
    assert result["speakers"] == []


def test_long_audio_chunks_overlap_but_merge_in_timeline_order(tmp_path):
    active = 0
    max_active = 0
    lock = threading.Lock()
    calls = []

    def fake_transcribe(path):
        nonlocal active, max_active
        index = int(os.path.basename(path).split("_")[1].split(".")[0])
        with lock:
            active += 1
            max_active = max(max_active, active)
            calls.append(index)
        time.sleep(0.05)
        with lock:
            active -= 1
        return {
            "segments": [{"text": f"chunk-{index}", "start": 0.0, "end": 1.0, "speaker": "SPEAKER_0"}],
        }

    audio_path = tmp_path / "long.wav"
    audio_path.touch()
    with patch("pydub.AudioSegment.from_wav", return_value=FakeAudio(900_000)), \
         patch("app.services.asr_service.transcribe_audio", side_effect=fake_transcribe):
        result = transcribe_long_audio(str(audio_path), chunk_duration=300, max_workers=3)

    assert max_active >= 2
    assert sorted(calls) == [0, 1, 2]
    assert [item["text"] for item in result["segments"]] == ["chunk-0", "chunk-1", "chunk-2"]
    assert [item["start"] for item in result["segments"]] == [0.0, 300.0, 600.0]
    assert not (tmp_path / "_chunks").exists()


def test_long_audio_chunk_failure_is_not_silently_published_as_complete(tmp_path):
    def fake_transcribe(path):
        index = int(os.path.basename(path).split("_")[1].split(".")[0])
        if index == 1:
            raise RuntimeError("provider_timeout")
        return {"segments": [{"text": f"chunk-{index}", "start": 0.0, "end": 1.0}]}

    audio_path = tmp_path / "long.wav"
    audio_path.touch()
    with patch("pydub.AudioSegment.from_wav", return_value=FakeAudio(900_000)), \
         patch("app.services.asr_service.transcribe_audio", side_effect=fake_transcribe):
        with pytest.raises(
            LongAudioTranscriptionError,
            match="long_audio_chunk_failed:2:provider_timeout",
        ):
            transcribe_long_audio(str(audio_path), chunk_duration=300, max_workers=3)

    assert not (tmp_path / "_chunks").exists()
