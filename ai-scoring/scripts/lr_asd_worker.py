#!/usr/bin/env python3
"""Local LR-ASD worker.

Heavy dependencies are imported only inside runtime functions so the scoring
service can unit-test the JSON boundary without installing PyTorch itself.
"""

from __future__ import annotations

import argparse
import heapq
import json
import math
import os
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.media_evidence.global_person_registrar import (
    register_global_visual_identities,
)


CONTRACT_VERSION = "lr-asd-evidence-v1"
TARGET_FPS = 25


def select_device(torch_module: Any) -> str:
    if bool(torch_module.cuda.is_available()):
        return "cuda"
    mps = getattr(getattr(torch_module, "backends", None), "mps", None)
    if mps is not None and bool(mps.is_available()):
        return "mps"
    return "cpu"


def split_checkpoint_state(checkpoint: dict) -> tuple[dict, dict]:
    model_state = {}
    classifier_state = {}
    for original_key, value in (checkpoint or {}).items():
        key = str(original_key)
        if key.startswith("module."):
            key = key[len("module.") :]
        if key.startswith("model."):
            model_state[key[len("model.") :]] = value
        elif key.startswith("lossAV.FC."):
            classifier_state[key[len("lossAV.FC.") :]] = value
    return model_state, classifier_state


def coalesce_active_frames(
    frames: list[tuple[str, int, int, float, float]],
    *,
    maximum_gap_ms: int = 80,
) -> list[dict]:
    by_face: dict[str, list] = defaultdict(list)
    for item in frames:
        by_face[str(item[0])].append(item)
    grouped: list[dict] = []
    for face_id, face_frames in by_face.items():
        for _, start_ms, end_ms, active, visible in sorted(
            face_frames, key=lambda item: (item[1], item[2])
        ):
            if (
                grouped
                and grouped[-1]["faceTrackId"] == face_id
                and int(start_ms) - grouped[-1]["endMs"] <= maximum_gap_ms
            ):
                current = grouped[-1]
                current["endMs"] = max(current["endMs"], int(end_ms))
                current["_active"].append(float(active))
                current["_visible"].append(float(visible))
            else:
                grouped.append(
                    {
                        "faceTrackId": face_id,
                        "startMs": int(start_ms),
                        "endMs": int(end_ms),
                        "_active": [float(active)],
                        "_visible": [float(visible)],
                    }
                )
    result = []
    for item in grouped:
        active_values = item.pop("_active")
        visible_values = item.pop("_visible")
        item["activeProbability"] = round(sum(active_values) / len(active_values), 6)
        item["visibleProbability"] = round(
            sum(visible_values) / len(visible_values), 6
        )
        result.append(item)
    result.sort(key=lambda item: (item["startMs"], item["endMs"], item["faceTrackId"]))
    return result


def build_error_result(reason: str, *, status: str = "failed") -> dict:
    return {
        "contractVersion": CONTRACT_VERSION,
        "status": status,
        "reason": str(reason),
        "faceTracks": [],
        "activeIntervals": [],
        "processing": {},
    }


def emit_json(value: dict) -> None:
    sys.stdout.write(json.dumps(value, ensure_ascii=False, separators=(",", ":")))
    sys.stdout.write("\n")
    sys.stdout.flush()


def _diagnostic(message: str) -> None:
    sys.stderr.write(f"[lr-asd] {message}\n")
    sys.stderr.flush()


def _load_model(repository: Path, weight: Path, device: str):
    import torch

    repository_text = str(repository.resolve())
    if repository_text not in sys.path:
        sys.path.insert(0, repository_text)
    from loss import lossAV
    from model.Model import ASD_Model

    checkpoint = torch.load(str(weight), map_location="cpu", weights_only=False)
    model_state, classifier_state = split_checkpoint_state(checkpoint)
    if not model_state or not classifier_state:
        raise RuntimeError("checkpoint_keys_missing")
    model = ASD_Model()
    classifier = lossAV().FC
    model.load_state_dict(model_state, strict=True)
    classifier.load_state_dict(classifier_state, strict=True)
    model.to(device).eval()
    classifier.to(device).eval()
    return model, classifier


def _synthetic_forward(model, classifier, device: str) -> None:
    import torch

    with torch.inference_mode():
        audio = torch.zeros((1, 100, 13), dtype=torch.float32, device=device)
        visual = torch.zeros((1, 25, 112, 112), dtype=torch.float32, device=device)
        audio_embedding = model.forward_audio_frontend(audio)
        visual_embedding = model.forward_visual_frontend(visual)
        output = model.forward_audio_visual_backend(audio_embedding, visual_embedding)
        probability = torch.softmax(classifier(output), dim=-1)[:, 1]
        if probability.numel() != 25:
            raise RuntimeError("synthetic_output_length_invalid")


def _load_model_with_fallback(repository: Path, weight: Path):
    import torch

    requested = select_device(torch)
    candidates = [requested]
    if requested != "cpu":
        candidates.append("cpu")
    last_error = None
    for device in candidates:
        try:
            model, classifier = _load_model(repository, weight, device)
            _synthetic_forward(model, classifier, device)
            return model, classifier, device
        except RuntimeError as exc:
            last_error = exc
            _diagnostic(f"device {device} rejected: {type(exc).__name__}")
            if device == "cuda":
                try:
                    torch.cuda.empty_cache()
                except Exception:
                    pass
    raise RuntimeError("model_device_unavailable") from last_error


def _normalized_feature(value):
    import numpy as np

    vector = np.asarray(value, dtype=np.float32).reshape(-1)
    norm = float(np.linalg.norm(vector))
    return vector / norm if norm > 1e-8 else vector


def _cosine(left, right) -> float:
    import numpy as np

    return float(np.dot(_normalized_feature(left), _normalized_feature(right)))


def _box_iou(left, right) -> float:
    lx, ly, lw, lh = [float(value) for value in left]
    rx, ry, rw, rh = [float(value) for value in right]
    x1, y1 = max(lx, rx), max(ly, ry)
    x2, y2 = min(lx + lw, rx + rw), min(ly + lh, ry + rh)
    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    union = max(1.0, lw * lh + rw * rh - intersection)
    return intersection / union


def _expanded_face_crop(frame, box):
    import cv2

    x, y, width, height = [float(value) for value in box]
    size = max(width, height) * 1.8
    center_x = x + width / 2
    center_y = y + height / 2
    left = max(0, int(round(center_x - size / 2)))
    top = max(0, int(round(center_y - size / 2)))
    right = min(frame.shape[1], int(round(center_x + size / 2)))
    bottom = min(frame.shape[0], int(round(center_y + size / 2)))
    if right - left < 12 or bottom - top < 12:
        return None
    crop = cv2.resize(frame[top:bottom, left:right], (224, 224))
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    return gray[56:168, 56:168]


def is_face_box_usable(box, *, minimum_size: float = 12.0) -> bool:
    if not isinstance(box, (list, tuple)) or len(box) < 4:
        return False
    width, height = float(box[2]), float(box[3])
    return min(width, height) >= float(minimum_size)


class _IdentityStore:
    def __init__(self, *, embedding_threshold: float = 0.42) -> None:
        self.embedding_threshold = embedding_threshold
        self.items: dict[str, dict] = {}
        self._next_id = 0

    def assign(
        self,
        feature,
        box,
        frame_index: int,
        excluded: set[str],
        *,
        frame_width: int | None = None,
    ) -> str:
        spatial_candidates = []
        for face_id, item in self.items.items():
            if face_id in excluded:
                continue
            recent = frame_index - item["lastFrame"] <= TARGET_FPS
            spatial = _box_iou(box, item["lastBox"])
            if recent and spatial >= 0.15:
                spatial_candidates.append((spatial, face_id))
        if spatial_candidates:
            best_id = max(spatial_candidates, key=lambda item: (item[0], item[1]))[1]
            best_value = 1.0
        else:
            best_id = None
            best_value = -1.0
        if best_id is None or best_value < self.embedding_threshold:
            best_id = f"FACE_{self._next_id}"
            self._next_id += 1
            self.items[best_id] = {
                "feature": _normalized_feature(feature),
                "firstFrame": frame_index,
                "lastFrame": frame_index,
                "lastBox": list(box),
                "meanCenterX": 0.0,
                "visibleSum": 0.0,
                "detectionCount": 0,
            }
        item = self.items[best_id]
        count = int(item["detectionCount"])
        item["feature"] = _normalized_feature(
            (item["feature"] * min(count, 20) + _normalized_feature(feature))
            / (min(count, 20) + 1)
        )
        item["lastFrame"] = frame_index
        item["lastBox"] = list(box)
        if frame_width and frame_width > 0:
            center_x = max(
                0.0,
                min(1.0, (float(box[0]) + float(box[2]) / 2.0) / frame_width),
            )
            item["meanCenterX"] = (
                float(item.get("meanCenterX") or 0.0) * count + center_x
            ) / (count + 1)
        item["detectionCount"] = count + 1
        return best_id


def build_global_visual_registration(
    identity_store: _IdentityStore,
    tracks: list[dict],
    *,
    co_visible_pairs: set[tuple[str, str]],
    minimum_similarity: float,
    stable_similarity: float = 0.80,
    minimum_detection_count: int = 3,
    minimum_visible_probability: float = 0.60,
) -> dict:
    """Build score-free global IDs and keep biometric vectors process-local."""

    eligible_ids = {
        str(track.get("faceTrackId") or "")
        for track in tracks
        if int(track.get("detectionCount") or 0) >= minimum_detection_count
        and float(track.get("visibleProbability") or 0)
        >= minimum_visible_probability
    }
    face_ids = sorted(face_id for face_id in identity_store.items if face_id in eligible_ids)
    links = []
    top_links: list[tuple[float, str, str]] = []
    for left_index, left in enumerate(face_ids):
        for right in face_ids[left_index + 1 :]:
            similarity = _cosine(
                identity_store.items[left]["feature"],
                identity_store.items[right]["feature"],
            )
            candidate = (float(similarity), left, right)
            if len(top_links) < 12:
                heapq.heappush(top_links, candidate)
            elif candidate > top_links[0]:
                heapq.heapreplace(top_links, candidate)
            if similarity >= minimum_similarity:
                links.append(
                    {
                        "leftFaceTrackId": left,
                        "rightFaceTrackId": right,
                        "similarity": similarity,
                    }
                )
    result = register_global_visual_identities(
        tracks,
        links,
        co_visible_pairs=co_visible_pairs,
        minimum_similarity=minimum_similarity,
        stable_similarity=stable_similarity,
        minimum_detection_count=minimum_detection_count,
        minimum_visible_probability=minimum_visible_probability,
    )
    conflict_set = {
        tuple(sorted((str(left), str(right))))
        for left, right in co_visible_pairs
    }
    result["diagnostics"]["topPrototypeSimilarities"] = [
        {
            "leftFaceTrackId": left,
            "rightFaceTrackId": right,
            "similarity": round(similarity, 6),
            "coVisibleConflict": tuple(sorted((left, right))) in conflict_set,
        }
        for similarity, left, right in sorted(
            top_links, key=lambda item: (-item[0], item[1], item[2])
        )
    ]
    return result


def _detect_faces(
    frame,
    detector,
    recognizer,
    identity_store,
    frame_index: int,
    *,
    minimum_face_size: float,
):
    import numpy as np

    detector.setInputSize((int(frame.shape[1]), int(frame.shape[0])))
    _, faces = detector.detect(frame)
    if faces is None:
        return []
    ordered = sorted(faces, key=lambda row: float(row[-1]), reverse=True)
    excluded: set[str] = set()
    result = []
    for raw in ordered:
        row = np.asarray(raw, dtype=np.float32)
        box = row[:4].tolist()
        if not is_face_box_usable(box, minimum_size=minimum_face_size):
            continue
        try:
            aligned = recognizer.alignCrop(frame, row)
            feature = recognizer.feature(aligned)
        except Exception:
            continue
        face_id = identity_store.assign(
            feature,
            box,
            frame_index,
            excluded,
            frame_width=int(frame.shape[1]),
        )
        excluded.add(face_id)
        confidence = max(0.0, min(1.0, float(row[-1])))
        item = identity_store.items[face_id]
        item["visibleSum"] += confidence
        result.append(
            {
                "faceTrackId": face_id,
                "box": box,
                "visibleProbability": confidence,
            }
        )
    return result


def _load_audio(path: Path):
    import numpy as np
    import soundfile as sf

    samples, sample_rate = sf.read(str(path), dtype="float32", always_2d=True)
    if samples.shape[1] != 1 or int(sample_rate) != 16000:
        raise RuntimeError("audio_must_be_mono_16khz")
    return np.ascontiguousarray(samples[:, 0], dtype=np.float32), int(sample_rate)


def _infer_face_segment(
    *,
    frames: list,
    start_frame: int,
    face_id: str,
    visible_probability: float,
    audio_samples,
    sample_rate: int,
    model,
    classifier,
    device: str,
    minimum_audio_rms: float,
    active_threshold: float,
) -> list[tuple[str, int, int, float, float]]:
    import numpy as np
    import python_speech_features
    import torch

    if len(frames) < 10:
        return []
    start_second = start_frame / TARGET_FPS
    end_second = (start_frame + len(frames)) / TARGET_FPS
    audio_start = max(0, int(round(start_second * sample_rate)))
    audio_end = min(len(audio_samples), int(round(end_second * sample_rate)))
    audio = audio_samples[audio_start:audio_end]
    if audio.size < int(sample_rate * 0.35):
        return []
    rms = float(np.sqrt(np.mean(np.square(audio), dtype=np.float64)))
    if not math.isfinite(rms) or rms < minimum_audio_rms:
        return []
    audio_feature = python_speech_features.mfcc(
        audio,
        sample_rate,
        numcep=13,
        winlen=0.025,
        winstep=0.010,
    )
    visual_feature = np.asarray(frames, dtype=np.float32)
    aligned_frames = min(len(visual_feature), len(audio_feature) // 4)
    if aligned_frames < 10:
        return []
    visual_feature = visual_feature[:aligned_frames]
    audio_feature = audio_feature[: aligned_frames * 4]
    with torch.inference_mode():
        audio_tensor = torch.as_tensor(
            audio_feature, dtype=torch.float32, device=device
        ).unsqueeze(0)
        visual_tensor = torch.as_tensor(
            visual_feature, dtype=torch.float32, device=device
        ).unsqueeze(0)
        audio_embedding = model.forward_audio_frontend(audio_tensor)
        visual_embedding = model.forward_visual_frontend(visual_tensor)
        output = model.forward_audio_visual_backend(audio_embedding, visual_embedding)
        probabilities = (
            torch.softmax(classifier(output), dim=-1)[:, 1].detach().cpu().numpy()
        )
    active_frames = []
    for offset, probability in enumerate(probabilities[:aligned_frames]):
        value = float(probability)
        if value < active_threshold:
            continue
        frame_number = start_frame + offset
        start_ms = int(round(frame_number * 1000 / TARGET_FPS))
        active_frames.append(
            (
                face_id,
                start_ms,
                start_ms + int(round(1000 / TARGET_FPS)),
                value,
                visible_probability,
            )
        )
    return active_frames


def analyze_video(args, model, classifier, device: str) -> dict:
    import cv2
    import numpy as np

    started = time.monotonic()
    video_path = Path(args.video)
    audio_path = Path(args.audio)
    probe = cv2.VideoCapture(str(video_path))
    width = int(probe.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(probe.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration_frames = int(probe.get(cv2.CAP_PROP_FRAME_COUNT))
    source_fps = float(probe.get(cv2.CAP_PROP_FPS) or 0)
    probe.release()
    if width <= 0 or height <= 0:
        raise RuntimeError("video_metadata_invalid")

    detector = cv2.FaceDetectorYN.create(
        str(args.yunet_model), "", (width, height), args.face_detection_threshold, 0.3, 5000
    )
    recognizer = cv2.FaceRecognizerSF.create(str(args.sface_model), "")
    audio_samples, sample_rate = _load_audio(audio_path)
    identity_store = _IdentityStore(embedding_threshold=args.face_identity_threshold)
    command = [
        "ffmpeg",
        "-v",
        "error",
        "-i",
        str(video_path),
        "-vf",
        f"fps={TARGET_FPS}",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "bgr24",
        "pipe:1",
    ]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if process.stdout is None:
        raise RuntimeError("ffmpeg_stdout_unavailable")

    frame_size = width * height * 3
    detection_stride = max(1, int(args.detection_stride))
    maximum_segment_frames = max(25, int(round(args.maximum_segment_seconds * TARGET_FPS)))
    current_faces = []
    buffers: dict[str, dict] = {}
    active_frames = []
    co_visible_pairs: set[tuple[str, str]] = set()
    frame_index = 0

    def flush(face_id: str) -> None:
        buffer = buffers.pop(face_id, None)
        if not buffer:
            return
        active_frames.extend(
            _infer_face_segment(
                frames=buffer["frames"],
                start_frame=buffer["startFrame"],
                face_id=face_id,
                visible_probability=buffer["visibleSum"] / max(1, buffer["visibleCount"]),
                audio_samples=audio_samples,
                sample_rate=sample_rate,
                model=model,
                classifier=classifier,
                device=device,
                minimum_audio_rms=args.minimum_audio_rms,
                active_threshold=args.active_threshold,
            )
        )

    try:
        while True:
            raw = process.stdout.read(frame_size)
            if len(raw) != frame_size:
                break
            frame = np.frombuffer(raw, dtype=np.uint8).reshape((height, width, 3))
            if frame_index % detection_stride == 0:
                current_faces = _detect_faces(
                    frame,
                    detector,
                    recognizer,
                    identity_store,
                    frame_index,
                    minimum_face_size=args.minimum_face_size,
                )
                visible_ids = {item["faceTrackId"] for item in current_faces}
                ordered_visible_ids = sorted(visible_ids)
                for left_index, left in enumerate(ordered_visible_ids):
                    for right in ordered_visible_ids[left_index + 1 :]:
                        co_visible_pairs.add((left, right))
                for missing_id in list(buffers):
                    if missing_id not in visible_ids:
                        flush(missing_id)
            for face in current_faces:
                face_id = face["faceTrackId"]
                crop = _expanded_face_crop(frame, face["box"])
                if crop is None:
                    continue
                if face_id not in buffers:
                    buffers[face_id] = {
                        "startFrame": frame_index,
                        "frames": [],
                        "visibleSum": 0.0,
                        "visibleCount": 0,
                    }
                buffer = buffers[face_id]
                buffer["frames"].append(crop)
                buffer["visibleSum"] += face["visibleProbability"]
                buffer["visibleCount"] += 1
                if len(buffer["frames"]) >= maximum_segment_frames:
                    flush(face_id)
            frame_index += 1
    finally:
        processing_exception_active = sys.exc_info()[0] is not None
        for face_id in list(buffers):
            flush(face_id)
        try:
            process.stdout.close()
        except Exception:
            pass
        stderr = process.stderr.read().decode("utf-8", errors="replace") if process.stderr else ""
        return_code = process.wait(timeout=10)
        if return_code != 0 and not processing_exception_active:
            _diagnostic(stderr[-500:])
            raise RuntimeError(f"ffmpeg_failed:{return_code}")

    tracks = []
    for face_id, item in identity_store.items.items():
        count = max(1, int(item["detectionCount"]))
        tracks.append(
            {
                "faceTrackId": face_id,
                "startMs": int(round(item["firstFrame"] * 1000 / TARGET_FPS)),
                "endMs": int(round((item["lastFrame"] + detection_stride) * 1000 / TARGET_FPS)),
                "visibleProbability": round(item["visibleSum"] / count, 6),
                "detectionCount": count,
                "meanCenterX": round(float(item.get("meanCenterX") or 0.0), 6),
            }
        )
    tracks.sort(key=lambda item: (item["startMs"], item["faceTrackId"]))
    intervals = coalesce_active_frames(active_frames)
    registration = build_global_visual_registration(
        identity_store,
        tracks,
        co_visible_pairs=co_visible_pairs,
        minimum_similarity=args.global_identity_threshold,
        stable_similarity=args.global_identity_stable_threshold,
        minimum_detection_count=args.global_identity_minimum_detections,
        minimum_visible_probability=args.global_identity_minimum_visibility,
    )
    assignment_by_track = {
        item["faceTrackId"]: item
        for item in registration["trackAssignments"]
    }
    for track in tracks:
        assignment = assignment_by_track.get(track["faceTrackId"])
        if assignment:
            track["visualIdentityId"] = assignment["visualIdentityId"]
            track["registrationState"] = assignment["registrationState"]
    for interval in intervals:
        assignment = assignment_by_track.get(interval["faceTrackId"])
        if assignment:
            interval["visualIdentityId"] = assignment["visualIdentityId"]
    if not tracks:
        status, reason = "unavailable", "no_visible_face"
    elif not intervals:
        status, reason = "partial", "no_confident_active_speaker"
    else:
        status, reason = "completed", None
    expected_target_frames = int(
        round((duration_frames / source_fps) * TARGET_FPS)
    ) if duration_frames > 0 and source_fps > 0 else frame_index
    return {
        "contractVersion": CONTRACT_VERSION,
        "status": status,
        "reason": reason,
        "faceTracks": tracks,
        "activeIntervals": intervals,
        "visualIdentities": registration["identities"],
        "registrationDiagnostics": registration["diagnostics"],
        "processing": {
            "model": "LR-ASD",
            "device": device,
            "durationMs": int(round((time.monotonic() - started) * 1000)),
            "decodedFrameCount": frame_index,
            "expectedTargetFrameCount": expected_target_frames,
            "sourceFps": round(source_fps, 6),
            "targetFps": TARGET_FPS,
            "detectionStride": detection_stride,
        },
    }


def serve_requests(
    args,
    model,
    classifier,
    device: str,
    *,
    input_stream=None,
    output_stream=None,
    analyzer=analyze_video,
) -> None:
    """Serve correlated local-path requests after loading the model once."""

    input_stream = input_stream or sys.stdin
    output_stream = output_stream or sys.stdout
    for line in input_stream:
        request_id = None
        try:
            envelope = json.loads(line)
            request_id = str(envelope.get("requestId") or "").strip()
            payload = envelope.get("payload")
            if not request_id or not isinstance(payload, dict):
                raise ValueError("request_invalid")
            video = Path(str(payload.get("video") or ""))
            audio = Path(str(payload.get("audio") or ""))
            if not video.is_file() or not audio.is_file():
                raise FileNotFoundError("media_missing")
            request_args = argparse.Namespace(**vars(args))
            request_args.video = str(video)
            request_args.audio = str(audio)
            response = {
                "requestId": request_id,
                "ok": True,
                "result": analyzer(
                    request_args, model, classifier, device
                ),
            }
        except Exception as error:
            response = {
                "requestId": request_id,
                "ok": False,
                "error": f"worker_request_failed:{type(error).__name__}",
            }
        output_stream.write(
            json.dumps(response, ensure_ascii=False, separators=(",", ":")) + "\n"
        )
        output_stream.flush()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local LR-ASD active-speaker worker")
    parser.add_argument("--model-repository", required=True)
    parser.add_argument("--model-weight", required=True)
    parser.add_argument("--yunet-model", required=True)
    parser.add_argument("--sface-model", required=True)
    parser.add_argument("--video")
    parser.add_argument("--audio")
    parser.add_argument("--health-check", action="store_true")
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--detection-stride", type=int, default=5)
    parser.add_argument("--maximum-segment-seconds", type=float, default=6.0)
    parser.add_argument("--minimum-audio-rms", type=float, default=0.0025)
    parser.add_argument("--active-threshold", type=float, default=0.5)
    parser.add_argument("--face-detection-threshold", type=float, default=0.65)
    parser.add_argument("--face-identity-threshold", type=float, default=0.42)
    # The fixed-camera roadshow keeps all contestants visible together.  That
    # co-visibility veto is an absolute cannot-link, so the SFace threshold can
    # stay near its published operating point without merging distinct people.
    parser.add_argument("--global-identity-threshold", type=float, default=0.30)
    parser.add_argument("--global-identity-stable-threshold", type=float, default=0.45)
    parser.add_argument("--global-identity-minimum-detections", type=int, default=3)
    parser.add_argument("--global-identity-minimum-visibility", type=float, default=0.60)
    parser.add_argument("--minimum-face-size", type=float, default=12.0)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        repository = Path(args.model_repository)
        weight = Path(args.model_weight)
        if not repository.is_dir() or not weight.is_file():
            raise RuntimeError("model_assets_missing")
        model, classifier, device = _load_model_with_fallback(repository, weight)
        if args.health_check:
            emit_json(
                {
                    "status": "ready",
                    "model": "LR-ASD",
                    "device": device,
                    "repositoryCommit": "1b6dcd2d8fc2895683de6508ec6294ec47d388ca",
                }
            )
            return 0
        if args.serve:
            required_models = [args.yunet_model, args.sface_model]
            if not all(required_models) or not all(
                Path(value).is_file() for value in required_models
            ):
                raise RuntimeError("face_model_missing")
            serve_requests(args, model, classifier, device)
            return 0
        required = [args.video, args.audio, args.yunet_model, args.sface_model]
        if not all(required) or not all(Path(value).is_file() for value in required):
            raise RuntimeError("media_or_face_model_missing")
        emit_json(analyze_video(args, model, classifier, device))
        return 0
    except Exception as exc:
        _diagnostic(f"{type(exc).__name__}:{exc}")
        emit_json(build_error_result(f"worker_exception:{type(exc).__name__}"))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
