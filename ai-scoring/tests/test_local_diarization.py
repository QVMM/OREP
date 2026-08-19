from types import SimpleNamespace

import numpy as np
import pytest

from app.services.media_evidence.local_diarization import (
    LocalDiarizationError,
    LocalSpeakerDiarizer,
)


def _model_files(tmp_path):
    segmentation = tmp_path / "segmentation.onnx"
    embedding = tmp_path / "embedding.onnx"
    segmentation.write_bytes(b"onnx-segmentation")
    embedding.write_bytes(b"onnx-embedding")
    return segmentation, embedding


def test_requires_preinstalled_local_models_and_never_downloads(tmp_path):
    diarizer = LocalSpeakerDiarizer(
        segmentation_model=tmp_path / "missing-segmentation.onnx",
        embedding_model=tmp_path / "missing-embedding.onnx",
        engine_factory=lambda **kwargs: pytest.fail("engine must not start"),
    )

    with pytest.raises(LocalDiarizationError, match="local_diarization_model_missing"):
        diarizer.diarize(tmp_path / "meeting.wav")


def test_uses_unknown_speaker_count_and_returns_sorted_global_turns(tmp_path):
    segmentation, embedding = _model_files(tmp_path)
    wav = tmp_path / "meeting.wav"
    wav.write_bytes(b"RIFF-local-test")
    captured = {}

    class FakeEngine:
        sample_rate = 16000

        def process(self, samples):
            assert samples.dtype == np.float32
            return [
                SimpleNamespace(start=2.0, end=3.25, speaker=1),
                SimpleNamespace(start=0.1, end=1.5, speaker=0),
            ]

    def factory(**kwargs):
        captured.update(kwargs)
        return FakeEngine()

    diarizer = LocalSpeakerDiarizer(
        segmentation_model=segmentation,
        embedding_model=embedding,
        cluster_threshold=0.5,
        minimum_cluster_duration_seconds=0,
        engine_factory=factory,
        audio_loader=lambda path: (np.zeros(32000, dtype=np.float32), 16000),
    )

    result = diarizer.diarize(wav)

    assert captured["num_clusters"] == -1
    assert captured["cluster_threshold"] == 0.5
    assert result["turns"] == [
        {
            "startMs": 100,
            "endMs": 1500,
            "rawSpeakerId": "SPEAKER_0",
            "sourceClusterId": "SPEAKER_0",
        },
        {
            "startMs": 2000,
            "endMs": 3250,
            "rawSpeakerId": "SPEAKER_1",
            "sourceClusterId": "SPEAKER_1",
        },
    ]
    assert result["speakers"] == ["SPEAKER_0", "SPEAKER_1"]
    assert result["diarizationStatus"] == "completed"
    assert result["source"] == "local_sherpa_onnx"


def test_rejects_non_16khz_audio_instead_of_silently_rescaling_timeline(tmp_path):
    segmentation, embedding = _model_files(tmp_path)
    wav = tmp_path / "meeting.wav"
    wav.write_bytes(b"RIFF-local-test")
    diarizer = LocalSpeakerDiarizer(
        segmentation_model=segmentation,
        embedding_model=embedding,
        engine_factory=lambda **kwargs: SimpleNamespace(sample_rate=16000),
        audio_loader=lambda path: (np.zeros(48000, dtype=np.float32), 48000),
    )

    with pytest.raises(LocalDiarizationError, match="local_diarization_audio_invalid:sample_rate"):
        diarizer.diarize(wav)


def test_empty_turns_are_explicitly_incomplete_without_fake_speaker(tmp_path):
    segmentation, embedding = _model_files(tmp_path)
    wav = tmp_path / "meeting.wav"
    wav.write_bytes(b"RIFF-local-test")
    engine = SimpleNamespace(sample_rate=16000, process=lambda samples: [])
    diarizer = LocalSpeakerDiarizer(
        segmentation_model=segmentation,
        embedding_model=embedding,
        engine_factory=lambda **kwargs: engine,
        audio_loader=lambda path: (np.zeros(16000, dtype=np.float32), 16000),
    )

    result = diarizer.diarize(wav)

    assert result["turns"] == []
    assert result["speakers"] == []
    assert result["diarizationStatus"] == "evidence_incomplete"


def test_implausible_auto_cluster_count_is_rejected_instead_of_published(tmp_path):
    segmentation, embedding = _model_files(tmp_path)
    wav = tmp_path / "meeting.wav"
    wav.write_bytes(b"RIFF-local-test")
    turns = [
        SimpleNamespace(start=float(index), end=float(index) + 0.5, speaker=index)
        for index in range(17)
    ]
    engine = SimpleNamespace(sample_rate=16000, process=lambda samples: turns)
    diarizer = LocalSpeakerDiarizer(
        segmentation_model=segmentation,
        embedding_model=embedding,
        engine_factory=lambda **kwargs: engine,
        audio_loader=lambda path: (np.zeros(16000, dtype=np.float32), 16000),
        max_detected_speakers=16,
        minimum_cluster_duration_seconds=0,
    )

    with pytest.raises(
        LocalDiarizationError,
        match="local_diarization_cluster_count_implausible:17",
    ):
        diarizer.diarize(wav)


def test_short_lived_clusters_are_withheld_and_stable_clusters_are_reindexed(tmp_path):
    segmentation, embedding = _model_files(tmp_path)
    wav = tmp_path / "meeting.wav"
    wav.write_bytes(b"RIFF-local-test")
    turns = [
        SimpleNamespace(start=0.0, end=3.0, speaker=8),
        SimpleNamespace(start=3.0, end=3.4, speaker=2),
        SimpleNamespace(start=4.0, end=7.0, speaker=8),
        SimpleNamespace(start=8.0, end=14.0, speaker=4),
    ]
    engine = SimpleNamespace(sample_rate=16000, process=lambda samples: turns)
    diarizer = LocalSpeakerDiarizer(
        segmentation_model=segmentation,
        embedding_model=embedding,
        engine_factory=lambda **kwargs: engine,
        audio_loader=lambda path: (np.zeros(16000, dtype=np.float32), 16000),
        minimum_cluster_duration_seconds=5,
    )

    result = diarizer.diarize(wav)

    assert result["originalDetectedSpeakerCount"] == 3
    assert result["detectedSpeakerCount"] == 2
    assert result["discardedClusterCount"] == 1
    assert result["discardedTurnCount"] == 1
    assert result["speakers"] == ["SPEAKER_0", "SPEAKER_1"]
    assert result["turns"] == [
        {
            "startMs": 0,
            "endMs": 3000,
            "rawSpeakerId": "SPEAKER_0",
            "sourceClusterId": "SPEAKER_8",
        },
        {
            "startMs": 4000,
            "endMs": 7000,
            "rawSpeakerId": "SPEAKER_0",
            "sourceClusterId": "SPEAKER_8",
        },
        {
            "startMs": 8000,
            "endMs": 14000,
            "rawSpeakerId": "SPEAKER_1",
            "sourceClusterId": "SPEAKER_4",
        },
    ]
    assert result["diarizationStatus"] == "partial"


def test_long_audio_uses_chunked_path_with_global_speaker_ids(tmp_path, monkeypatch):
    segmentation, embedding = _model_files(tmp_path)
    wav = tmp_path / "long.wav"
    wav.write_bytes(b"RIFF-local-test")
    # 20 minutes @ 16kHz forces chunked path when full_pass_max is 60s.
    sample_rate = 16000
    samples = np.zeros(sample_rate * 1200, dtype=np.float32)
    process_calls = []

    class FakeEngine:
        sample_rate = 16000

        def process(self, window):
            process_calls.append(len(window))
            # Local speaker id flips each call so global recluster must unify them.
            speaker = len(process_calls) % 2
            duration = len(window) / sample_rate
            return [
                SimpleNamespace(start=0.5, end=min(2.5, duration - 0.1), speaker=speaker),
            ]

    class FakeStream:
        def accept_waveform(self, sample_rate, waveform):
            self.sample_rate = sample_rate
            self.waveform = waveform

        def input_finished(self):
            return None

    class FakeExtractor:
        def create_stream(self):
            return FakeStream()

        def is_ready(self, stream):
            return True

        def compute(self, stream):
            # Stable embedding so global clustering yields one speaker.
            return np.ones(4, dtype=np.float32)

    monkeypatch.setattr(
        "app.services.media_evidence.local_diarization._cluster_embeddings",
        lambda embeddings, cluster_threshold, num_clusters: [0] * len(embeddings),
    )

    diarizer = LocalSpeakerDiarizer(
        segmentation_model=segmentation,
        embedding_model=embedding,
        engine_factory=lambda **kwargs: FakeEngine(),
        embedding_extractor_factory=lambda model: FakeExtractor(),
        audio_loader=lambda path: (samples, sample_rate),
        minimum_cluster_duration_seconds=0,
        chunk_seconds=60,
        chunk_overlap_seconds=5,
        full_pass_max_seconds=60,
    )

    result = diarizer.diarize(wav)

    assert len(process_calls) >= 2
    assert result["source"] == "local_sherpa_onnx_chunked"
    assert result["chunkCount"] >= 2
    assert result["speakers"] == ["SPEAKER_0"]
    assert result["detectedSpeakerCount"] == 1
    assert all(turn["rawSpeakerId"] == "SPEAKER_0" for turn in result["turns"])
    assert result["diarizationStatus"] == "completed"
