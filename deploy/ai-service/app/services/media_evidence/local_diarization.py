"""Local complete-recording speaker diarization without object storage.

Long recordings are processed in fixed windows with global speaker-embedding
re-clustering so speaker IDs stay consistent across the full timeline. Short
recordings keep the single full-file sherpa Offline path.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

import numpy as np


class LocalDiarizationError(RuntimeError):
    """Named failure at the local speaker-evidence boundary."""


def _load_mono_float32(path: Path) -> tuple[np.ndarray, int]:
    try:
        import soundfile as sf

        audio, sample_rate = sf.read(str(path), dtype="float32", always_2d=True)
    except Exception as exc:
        raise LocalDiarizationError(
            f"local_diarization_audio_invalid:{type(exc).__name__}"
        ) from exc
    if audio.ndim != 2 or audio.shape[1] != 1:
        raise LocalDiarizationError("local_diarization_audio_invalid:channels")
    return np.ascontiguousarray(audio[:, 0], dtype=np.float32), int(sample_rate)


def _build_sherpa_engine(
    *,
    segmentation_model: str,
    embedding_model: str,
    cluster_threshold: float,
    num_clusters: int,
) -> Any:
    try:
        import sherpa_onnx
    except Exception as exc:
        raise LocalDiarizationError("local_diarization_engine_unavailable") from exc

    config = sherpa_onnx.OfflineSpeakerDiarizationConfig(
        segmentation=sherpa_onnx.OfflineSpeakerSegmentationModelConfig(
            pyannote=sherpa_onnx.OfflineSpeakerSegmentationPyannoteModelConfig(
                model=segmentation_model,
            )
        ),
        embedding=sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=embedding_model),
        clustering=sherpa_onnx.FastClusteringConfig(
            num_clusters=num_clusters,
            threshold=cluster_threshold,
        ),
        min_duration_on=0.3,
        min_duration_off=0.5,
    )
    if not config.validate():
        raise LocalDiarizationError("local_diarization_model_invalid")
    try:
        return sherpa_onnx.OfflineSpeakerDiarization(config)
    except Exception as exc:
        raise LocalDiarizationError("local_diarization_engine_unavailable") from exc


def _build_embedding_extractor(embedding_model: str) -> Any:
    try:
        import sherpa_onnx
    except Exception as exc:
        raise LocalDiarizationError("local_diarization_engine_unavailable") from exc
    config = sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=embedding_model)
    if not config.validate():
        raise LocalDiarizationError("local_diarization_model_invalid")
    try:
        return sherpa_onnx.SpeakerEmbeddingExtractor(config)
    except Exception as exc:
        raise LocalDiarizationError("local_diarization_engine_unavailable") from exc


def _cluster_embeddings(
    embeddings: np.ndarray,
    *,
    cluster_threshold: float,
    num_clusters: int,
) -> list[int]:
    try:
        import sherpa_onnx
    except Exception as exc:
        raise LocalDiarizationError("local_diarization_engine_unavailable") from exc
    if embeddings.ndim != 2 or embeddings.shape[0] == 0:
        return []
    if embeddings.shape[0] == 1:
        return [0]
    config = sherpa_onnx.FastClusteringConfig(
        num_clusters=num_clusters,
        threshold=cluster_threshold,
    )
    clustering = sherpa_onnx.FastClustering(config)
    try:
        labels = clustering(embeddings)
    except Exception as exc:
        raise LocalDiarizationError(
            f"local_diarization_clustering_failed:{type(exc).__name__}"
        ) from exc
    return [int(label) for label in labels]


def _embed_segment(
    extractor: Any,
    samples: np.ndarray,
    sample_rate: int,
    start_sample: int,
    end_sample: int,
    *,
    min_samples: int,
) -> np.ndarray | None:
    start = max(0, int(start_sample))
    end = min(int(samples.size), int(end_sample))
    if end - start < min_samples:
        return None
    segment = np.ascontiguousarray(samples[start:end], dtype=np.float32)
    try:
        stream = extractor.create_stream()
        stream.accept_waveform(sample_rate, segment)
        stream.input_finished()
        if hasattr(extractor, "is_ready") and not extractor.is_ready(stream):
            return None
        embedding = np.asarray(extractor.compute(stream), dtype=np.float32).reshape(-1)
    except Exception as exc:
        raise LocalDiarizationError(
            f"local_diarization_embedding_failed:{type(exc).__name__}"
        ) from exc
    if embedding.size == 0 or not np.isfinite(embedding).all():
        return None
    return embedding


def _merge_adjacent_turns(
    turns: list[dict],
    *,
    max_gap_ms: int = 400,
) -> list[dict]:
    if not turns:
        return []
    ordered = sorted(
        turns,
        key=lambda item: (
            item["startMs"],
            item["endMs"],
            item.get("rawSpeakerId", ""),
        ),
    )
    merged: list[dict] = [dict(ordered[0])]
    for turn in ordered[1:]:
        prev = merged[-1]
        same_speaker = prev.get("rawSpeakerId") == turn.get("rawSpeakerId")
        gap = int(turn["startMs"]) - int(prev["endMs"])
        if same_speaker and gap <= max_gap_ms:
            prev["endMs"] = max(int(prev["endMs"]), int(turn["endMs"]))
            continue
        merged.append(dict(turn))
    return merged


class LocalSpeakerDiarizer:
    def __init__(
        self,
        *,
        segmentation_model: str | Path,
        embedding_model: str | Path,
        cluster_threshold: float = 1.0,
        max_detected_speakers: int = 16,
        minimum_cluster_duration_seconds: float = 5.0,
        chunk_seconds: float = 600.0,
        chunk_overlap_seconds: float = 15.0,
        full_pass_max_seconds: float = 720.0,
        engine_factory: Callable[..., Any] | None = None,
        embedding_extractor_factory: Callable[..., Any] | None = None,
        audio_loader: Callable[[Path], tuple[np.ndarray, int]] | None = None,
        progress_callback: Callable[[str, int, int], None] | None = None,
    ) -> None:
        self._segmentation_model = Path(segmentation_model)
        self._embedding_model = Path(embedding_model)
        self._cluster_threshold = float(cluster_threshold)
        self._max_detected_speakers = max(2, int(max_detected_speakers))
        self._minimum_cluster_duration_ms = max(
            0, int(round(float(minimum_cluster_duration_seconds) * 1000))
        )
        self._chunk_seconds = max(60.0, float(chunk_seconds))
        self._chunk_overlap_seconds = max(0.0, float(chunk_overlap_seconds))
        self._full_pass_max_seconds = max(
            self._chunk_seconds, float(full_pass_max_seconds)
        )
        self._engine_factory = engine_factory or _build_sherpa_engine
        self._embedding_extractor_factory = (
            embedding_extractor_factory or _build_embedding_extractor
        )
        self._audio_loader = audio_loader or _load_mono_float32
        self._progress_callback = progress_callback

    def _validate_models(self) -> None:
        for path in (self._segmentation_model, self._embedding_model):
            if not path.is_file():
                raise LocalDiarizationError("local_diarization_model_missing")
            if path.suffix.lower() != ".onnx" or path.stat().st_size <= 0:
                raise LocalDiarizationError("local_diarization_model_invalid")

    def _emit_progress(self, stage: str, current: int, total: int) -> None:
        if self._progress_callback is None:
            return
        try:
            self._progress_callback(stage, current, total)
        except Exception:
            # Progress is best-effort and must never abort diarization.
            return

    def _process_window(
        self,
        samples: np.ndarray,
        sample_rate: int,
        *,
        speaker_count_hint: int | None,
    ) -> list[Any]:
        num_clusters = -1 if speaker_count_hint is None else max(1, int(speaker_count_hint))
        engine = self._engine_factory(
            segmentation_model=str(self._segmentation_model),
            embedding_model=str(self._embedding_model),
            cluster_threshold=self._cluster_threshold,
            num_clusters=num_clusters,
        )
        if int(getattr(engine, "sample_rate", sample_rate)) != sample_rate:
            raise LocalDiarizationError(
                "local_diarization_audio_invalid:engine_sample_rate"
            )
        try:
            processed = engine.process(samples)
            if hasattr(processed, "sort_by_start_time"):
                processed = processed.sort_by_start_time()
            return list(processed)
        except LocalDiarizationError:
            raise
        except Exception as exc:
            raise LocalDiarizationError(
                f"local_diarization_processing_failed:{type(exc).__name__}"
            ) from exc

    def _finalize_turns(
        self,
        source_turns: list[dict],
        *,
        speaker_count_hint: int | None,
        source: str,
        chunk_count: int | None = None,
    ) -> dict:
        duration_by_cluster: dict[str, int] = defaultdict(int)
        for turn in source_turns:
            duration_by_cluster[turn["sourceClusterId"]] += (
                int(turn["endMs"]) - int(turn["startMs"])
            )
        original_cluster_count = len(duration_by_cluster)
        stable_clusters = {
            cluster_id
            for cluster_id, duration_ms in duration_by_cluster.items()
            if duration_ms >= self._minimum_cluster_duration_ms
        }
        stable_order: list[str] = []
        for turn in sorted(
            source_turns,
            key=lambda item: (item["startMs"], item["endMs"], item["sourceClusterId"]),
        ):
            cluster_id = turn["sourceClusterId"]
            if cluster_id in stable_clusters and cluster_id not in stable_order:
                stable_order.append(cluster_id)
        cluster_mapping = {
            cluster_id: f"SPEAKER_{index}"
            for index, cluster_id in enumerate(stable_order)
        }
        turns = [
            {
                "startMs": int(turn["startMs"]),
                "endMs": int(turn["endMs"]),
                "rawSpeakerId": cluster_mapping[turn["sourceClusterId"]],
                "sourceClusterId": turn["sourceClusterId"],
            }
            for turn in sorted(
                source_turns,
                key=lambda item: (
                    item["startMs"],
                    item["endMs"],
                    item["sourceClusterId"],
                ),
            )
            if turn["sourceClusterId"] in cluster_mapping
        ]
        turns = _merge_adjacent_turns(turns)
        discarded_turn_count = len(source_turns) - len(
            [
                turn
                for turn in source_turns
                if turn["sourceClusterId"] in cluster_mapping
            ]
        )
        speakers = [cluster_mapping[cluster_id] for cluster_id in stable_order]
        if speaker_count_hint is None and len(speakers) > self._max_detected_speakers:
            raise LocalDiarizationError(
                f"local_diarization_cluster_count_implausible:{len(speakers)}"
            )
        if not speakers:
            status = "evidence_incomplete"
        elif discarded_turn_count:
            status = "partial"
        else:
            status = "completed"
        payload = {
            "turns": turns,
            "speakers": speakers,
            "detectedSpeakerCount": len(speakers),
            "originalDetectedSpeakerCount": original_cluster_count,
            "discardedClusterCount": original_cluster_count - len(speakers),
            "discardedTurnCount": discarded_turn_count,
            "minimumClusterDurationMs": self._minimum_cluster_duration_ms,
            "diarizationStatus": status,
            "source": source,
        }
        if chunk_count is not None:
            payload["chunkCount"] = int(chunk_count)
        return payload

    def _diarize_full(
        self,
        samples: np.ndarray,
        sample_rate: int,
        *,
        speaker_count_hint: int | None,
    ) -> dict:
        self._emit_progress("full", 0, 1)
        raw_turns = self._process_window(
            samples, sample_rate, speaker_count_hint=speaker_count_hint
        )
        source_turns = []
        for raw in raw_turns:
            start_ms = max(0, int(round(float(raw.start) * 1000)))
            end_ms = max(start_ms, int(round(float(raw.end) * 1000)))
            speaker = int(raw.speaker)
            source_cluster_id = f"SPEAKER_{speaker}"
            source_turns.append(
                {
                    "startMs": start_ms,
                    "endMs": end_ms,
                    "sourceClusterId": source_cluster_id,
                }
            )
        self._emit_progress("full", 1, 1)
        return self._finalize_turns(
            source_turns,
            speaker_count_hint=speaker_count_hint,
            source="local_sherpa_onnx",
            chunk_count=1,
        )

    def _window_ranges(
        self, sample_count: int, sample_rate: int
    ) -> list[tuple[int, int, int, int]]:
        """Return (start, end, own_start, own_end) sample ranges for each chunk."""
        chunk_samples = int(round(self._chunk_seconds * sample_rate))
        overlap_samples = int(round(self._chunk_overlap_seconds * sample_rate))
        hop = max(1, chunk_samples - overlap_samples)
        ranges: list[tuple[int, int, int, int]] = []
        start = 0
        while start < sample_count:
            end = min(sample_count, start + chunk_samples)
            if start == 0:
                own_start = 0
            else:
                own_start = start + overlap_samples // 2
            if end >= sample_count:
                own_end = sample_count
            else:
                own_end = end - overlap_samples // 2
            own_start = max(start, min(own_start, end))
            own_end = max(own_start, min(own_end, end))
            ranges.append((start, end, own_start, own_end))
            if end >= sample_count:
                break
            start += hop
        return ranges

    def _diarize_chunked(
        self,
        samples: np.ndarray,
        sample_rate: int,
        *,
        speaker_count_hint: int | None,
    ) -> dict:
        ranges = self._window_ranges(samples.size, sample_rate)
        if not ranges:
            return self._finalize_turns(
                [],
                speaker_count_hint=speaker_count_hint,
                source="local_sherpa_onnx_chunked",
                chunk_count=0,
            )

        provisional: list[dict] = []
        embeddings: list[np.ndarray] = []
        min_embed_samples = max(1, int(round(0.25 * sample_rate)))
        extractor = self._embedding_extractor_factory(str(self._embedding_model))

        for index, (start, end, own_start, own_end) in enumerate(ranges):
            self._emit_progress("chunk", index, len(ranges))
            window = np.ascontiguousarray(samples[start:end], dtype=np.float32)
            # Per-chunk clustering is local only; global identity comes from embeddings.
            raw_turns = self._process_window(
                window, sample_rate, speaker_count_hint=None
            )
            for raw in raw_turns:
                local_start = max(0, int(round(float(raw.start) * sample_rate)))
                local_end = max(
                    local_start, int(round(float(raw.end) * sample_rate))
                )
                abs_start = start + local_start
                abs_end = start + local_end
                midpoint = (abs_start + abs_end) // 2
                if midpoint < own_start or midpoint >= own_end:
                    continue
                if abs_end <= abs_start:
                    continue
                embedding = _embed_segment(
                    extractor,
                    samples,
                    sample_rate,
                    abs_start,
                    abs_end,
                    min_samples=min_embed_samples,
                )
                if embedding is None:
                    continue
                provisional.append(
                    {
                        "startMs": int(round(abs_start * 1000 / sample_rate)),
                        "endMs": int(round(abs_end * 1000 / sample_rate)),
                        "chunkIndex": index,
                        "localSpeaker": int(raw.speaker),
                    }
                )
                embeddings.append(embedding)
            self._emit_progress("chunk", index + 1, len(ranges))

        if not provisional:
            return self._finalize_turns(
                [],
                speaker_count_hint=speaker_count_hint,
                source="local_sherpa_onnx_chunked",
                chunk_count=len(ranges),
            )

        matrix = np.stack(embeddings, axis=0)
        num_clusters = (
            -1 if speaker_count_hint is None else max(1, int(speaker_count_hint))
        )
        labels = _cluster_embeddings(
            matrix,
            cluster_threshold=self._cluster_threshold,
            num_clusters=num_clusters,
        )
        if len(labels) != len(provisional):
            raise LocalDiarizationError(
                "local_diarization_clustering_size_mismatch"
            )

        source_turns = [
            {
                "startMs": item["startMs"],
                "endMs": item["endMs"],
                "sourceClusterId": f"SPEAKER_{label}",
            }
            for item, label in zip(provisional, labels)
        ]
        return self._finalize_turns(
            source_turns,
            speaker_count_hint=speaker_count_hint,
            source="local_sherpa_onnx_chunked",
            chunk_count=len(ranges),
        )

    def diarize(
        self,
        wav_path: str | Path,
        *,
        speaker_count_hint: int | None = None,
    ) -> dict:
        self._validate_models()
        path = Path(wav_path)
        if not path.is_file():
            raise LocalDiarizationError("local_diarization_audio_missing")
        samples, sample_rate = self._audio_loader(path)
        if sample_rate != 16000:
            raise LocalDiarizationError("local_diarization_audio_invalid:sample_rate")
        samples = np.ascontiguousarray(samples, dtype=np.float32).reshape(-1)
        if samples.size == 0:
            raise LocalDiarizationError("local_diarization_audio_invalid:empty")

        duration_seconds = float(samples.size) / float(sample_rate)
        if duration_seconds <= self._full_pass_max_seconds:
            return self._diarize_full(
                samples, sample_rate, speaker_count_hint=speaker_count_hint
            )
        return self._diarize_chunked(
            samples, sample_rate, speaker_count_hint=speaker_count_hint
        )
