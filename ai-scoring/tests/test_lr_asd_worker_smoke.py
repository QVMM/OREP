import json
from io import StringIO
from types import SimpleNamespace

import numpy as np

from scripts.lr_asd_worker import (
    _IdentityStore,
    build_global_visual_registration,
    build_error_result,
    coalesce_active_frames,
    emit_json,
    is_face_box_usable,
    build_parser,
    select_device,
    serve_requests,
    split_checkpoint_state,
)


class _Availability:
    def __init__(self, available):
        self._available = available

    def is_available(self):
        return self._available


class _Torch:
    def __init__(self, *, cuda=False, mps=False):
        self.cuda = _Availability(cuda)
        self.backends = type("Backends", (), {"mps": _Availability(mps)})()


def test_device_selection_prefers_cuda_then_mps_then_cpu():
    assert select_device(_Torch(cuda=True, mps=True)) == "cuda"
    assert select_device(_Torch(cuda=False, mps=True)) == "mps"
    assert select_device(_Torch(cuda=False, mps=False)) == "cpu"


def test_checkpoint_state_is_split_without_cuda_training_wrapper():
    model_state, classifier_state = split_checkpoint_state(
        {
            "model.visualEncoder.layer": "visual",
            "model.audioEncoder.layer": "audio",
            "lossAV.FC.weight": "weight",
            "lossAV.FC.bias": "bias",
            "lossV.FC.weight": "ignored",
        }
    )

    assert model_state == {
        "visualEncoder.layer": "visual",
        "audioEncoder.layer": "audio",
    }
    assert classifier_state == {"weight": "weight", "bias": "bias"}


def test_active_frames_coalesce_by_face_and_gap_then_sort():
    intervals = coalesce_active_frames(
        [
            ("FACE_1", 1000, 1040, 0.8, 0.9),
            ("FACE_0", 0, 40, 0.9, 0.8),
            ("FACE_0", 40, 80, 0.7, 1.0),
            ("FACE_0", 200, 240, 0.95, 0.95),
        ],
        maximum_gap_ms=80,
    )

    assert [(item["faceTrackId"], item["startMs"], item["endMs"]) for item in intervals] == [
        ("FACE_0", 0, 80),
        ("FACE_0", 200, 240),
        ("FACE_1", 1000, 1040),
    ]
    assert intervals[0]["activeProbability"] == 0.8
    assert intervals[0]["visibleProbability"] == 0.9


def test_interleaved_faces_do_not_prevent_each_track_from_coalescing():
    intervals = coalesce_active_frames(
        [
            ("FACE_0", 0, 40, 0.9, 0.9),
            ("FACE_1", 0, 40, 0.1, 0.9),
            ("FACE_0", 40, 80, 0.8, 0.9),
            ("FACE_1", 40, 80, 0.2, 0.9),
        ]
    )

    assert [(item["faceTrackId"], item["startMs"], item["endMs"]) for item in intervals] == [
        ("FACE_0", 0, 80),
        ("FACE_1", 0, 80),
    ]


def test_real_roadshow_small_face_is_accepted_but_tiny_noise_is_rejected():
    assert is_face_box_usable([0, 0, 14, 18], minimum_size=12) is True
    assert is_face_box_usable([0, 0, 10, 20], minimum_size=12) is False


def test_recent_high_iou_track_survives_noisy_small_face_embedding():
    store = _IdentityStore(embedding_threshold=0.42)
    first = store.assign(
        np.asarray([1.0, 0.0], dtype=np.float32),
        [100, 100, 14, 18],
        0,
        set(),
    )
    second = store.assign(
        np.asarray([0.0, 1.0], dtype=np.float32),
        [101, 100, 14, 18],
        5,
        set(),
    )

    assert second == first


def test_distant_same_embedding_starts_a_new_tracklet_for_global_registration():
    store = _IdentityStore(embedding_threshold=0.42)
    first = store.assign(
        np.asarray([1.0, 0.0], dtype=np.float32),
        [10, 10, 20, 20],
        0,
        set(),
    )
    second = store.assign(
        np.asarray([1.0, 0.0], dtype=np.float32),
        [300, 200, 20, 20],
        5,
        set(),
    )

    assert second != first


def test_track_keeps_a_normalized_horizontal_position_anchor():
    store = _IdentityStore(embedding_threshold=0.42)
    face_id = store.assign(
        np.asarray([1.0, 0.0], dtype=np.float32),
        [100, 20, 20, 20],
        0,
        set(),
        frame_width=400,
    )
    store.assign(
        np.asarray([1.0, 0.0], dtype=np.float32),
        [110, 20, 20, 20],
        5,
        set(),
        frame_width=400,
    )

    assert store.items[face_id]["meanCenterX"] == 0.2875


def test_real_video_defaults_allow_sface_links_to_become_stable_with_covisiibility_veto():
    args = build_parser().parse_args([
        "--model-repository", "/tmp/model",
        "--model-weight", "/tmp/weight",
        "--yunet-model", "/tmp/yunet",
        "--sface-model", "/tmp/sface",
        "--health-check",
    ])

    assert args.global_identity_threshold == 0.30
    assert args.global_identity_stable_threshold == 0.45


def test_worker_global_registration_merges_prototypes_without_exporting_vectors():
    store = _IdentityStore(embedding_threshold=0.42)
    store.items = {
        "FACE_0": {"feature": np.asarray([1.0, 0.0], dtype=np.float32)},
        "FACE_1": {"feature": np.asarray([0.99, 0.01], dtype=np.float32)},
    }
    tracks = [
        {"faceTrackId": "FACE_0", "startMs": 0, "endMs": 1000,
         "detectionCount": 10, "visibleProbability": 0.9},
        {"faceTrackId": "FACE_1", "startMs": 3000, "endMs": 4000,
         "detectionCount": 10, "visibleProbability": 0.9},
    ]

    result = build_global_visual_registration(
        store,
        tracks,
        co_visible_pairs=set(),
        minimum_similarity=0.8,
    )

    assert result["identities"][0]["faceTrackIds"] == ["FACE_0", "FACE_1"]
    assert "feature" not in json.dumps(result)


def test_worker_global_registration_preserves_co_visible_people():
    store = _IdentityStore(embedding_threshold=0.42)
    store.items = {
        "FACE_0": {"feature": np.asarray([1.0, 0.0], dtype=np.float32)},
        "FACE_1": {"feature": np.asarray([1.0, 0.0], dtype=np.float32)},
    }
    tracks = [
        {"faceTrackId": "FACE_0", "startMs": 0, "endMs": 1000,
         "detectionCount": 10, "visibleProbability": 0.9},
        {"faceTrackId": "FACE_1", "startMs": 0, "endMs": 1000,
         "detectionCount": 10, "visibleProbability": 0.9},
    ]

    result = build_global_visual_registration(
        store,
        tracks,
        co_visible_pairs={("FACE_0", "FACE_1")},
        minimum_similarity=0.8,
    )

    assert len(result["identities"]) == 2
    assert result["diagnostics"]["rejectedCoVisibleLinkCount"] == 1


def test_error_result_and_stdout_are_machine_readable(capsys):
    result = build_error_result("no_visible_face", status="unavailable")

    emit_json(result)

    captured = capsys.readouterr()
    assert captured.err == ""
    assert json.loads(captured.out) == result
    assert result["contractVersion"] == "lr-asd-evidence-v1"
    assert result["faceTracks"] == []
    assert result["activeIntervals"] == []


def test_serve_protocol_correlates_request_without_reloading_model(tmp_path):
    video = tmp_path / "video.mp4"
    audio = tmp_path / "audio.wav"
    video.write_bytes(b"video")
    audio.write_bytes(b"audio")
    request_stream = StringIO(
        json.dumps(
            {
                "requestId": "req-1",
                "payload": {"video": str(video), "audio": str(audio)},
            }
        )
        + "\n"
    )
    output_stream = StringIO()
    calls = []

    serve_requests(
        SimpleNamespace(video=None, audio=None),
        model=object(),
        classifier=object(),
        device="cpu",
        input_stream=request_stream,
        output_stream=output_stream,
        analyzer=lambda args, model, classifier, device: (
            calls.append((args.video, args.audio, device))
            or build_error_result("none", status="unavailable")
        ),
    )

    response = json.loads(output_stream.getvalue())
    assert response["requestId"] == "req-1"
    assert response["ok"] is True
    assert response["result"]["contractVersion"] == "lr-asd-evidence-v1"
    assert calls == [(str(video), str(audio), "cpu")]
