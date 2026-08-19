from app.services.video_analysis_service import VideoAnalysisService, sample_evenly
from app.services.visual_frame_selector import select_visual_frame_events, visual_frame_selection_summary
import threading
import time


def test_sample_evenly_preserves_whole_timeline():
    items = [{"timestamp_min": index * 0.5, "text": f"frame-{index}"} for index in range(100)]

    sampled = sample_evenly(items, 20, key=lambda item: item["timestamp_min"])

    assert len(sampled) == 20
    assert sampled[0]["timestamp_min"] == 0
    assert sampled[-1]["timestamp_min"] == 49.5
    assert any(20 <= item["timestamp_min"] <= 30 for item in sampled)


def test_sample_evenly_keeps_short_lists_unchanged():
    items = [{"timestamp_min": index} for index in range(4)]

    assert sample_evenly(items, 20, key=lambda item: item["timestamp_min"]) == items


def test_batch_failure_falls_back_to_single_frame_analysis():
    class FakeVideoAnalysisService(VideoAnalysisService):
        def __init__(self):
            self._client_lock = threading.Lock()
            self._timeout_streak = 0

        def _analyze_batch(self, frame_paths, start_index, timestamps_sec=None):
            if len(frame_paths) > 1:
                raise RuntimeError("batch rejected")
            return ([{"frame": start_index + 1, "ok": True}], {"prompt_tokens": 1, "completion_tokens": 2})

    service = FakeVideoAnalysisService()

    results, tokens = service._analyze_batch_with_recovery(["a.jpg", "b.jpg"], 0, [1.0, 2.0])

    assert results == [{"frame": 1, "ok": True}, {"frame": 2, "ok": True}]
    assert tokens == {"prompt_tokens": 2, "completion_tokens": 4}


def test_timeout_batch_splits_in_half_before_singles():
    class FakeVideoAnalysisService(VideoAnalysisService):
        def __init__(self):
            self._client_lock = threading.Lock()
            self._timeout_streak = 0
            self.sizes = []

        def _analyze_batch(self, frame_paths, start_index, timestamps_sec=None):
            self.sizes.append(len(frame_paths))
            if len(frame_paths) > 2:
                raise TimeoutError("Request timed out.")
            return (
                [{"frame": start_index + offset + 1, "ok": True} for offset in range(len(frame_paths))],
                {"prompt_tokens": len(frame_paths), "completion_tokens": 1},
            )

    service = FakeVideoAnalysisService()
    results, _ = service._analyze_batch_with_recovery(
        ["a.jpg", "b.jpg", "c.jpg", "d.jpg"], 0, [1.0, 2.0, 3.0, 4.0]
    )
    assert [item["frame"] for item in results] == [1, 2, 3, 4]
    assert 4 in service.sizes
    assert 2 in service.sizes
    assert all("error" not in item for item in results)


def test_timeout_streak_stops_further_calls():
    class FakeVideoAnalysisService(VideoAnalysisService):
        def __init__(self):
            self._client_lock = threading.Lock()
            self._timeout_streak = 0
            self.calls = 0

        def _analyze_batch(self, frame_paths, start_index, timestamps_sec=None):
            self.calls += 1
            raise TimeoutError("Request timed out.")

    service = FakeVideoAnalysisService()
    service._timeout_streak = 5
    results, _ = service._analyze_batch_with_recovery(["a.jpg", "b.jpg"], 0, [1.0, 2.0])
    assert service.calls == 1
    assert all("vision_timeout_circuit" in item.get("error", "") for item in results)


def test_visual_batches_overlap_and_merge_in_frame_order():
    class ConcurrentFakeVideoAnalysisService(VideoAnalysisService):
        def __init__(self):
            self.batch_size = 2
            self.active = 0
            self.max_active = 0
            self.lock = threading.Lock()
            self._client_lock = threading.Lock()
            self._timeout_streak = 0

        def _analyze_batch_with_recovery(self, batch, start_index, timestamps_sec=None):
            with self.lock:
                self.active += 1
                self.max_active = max(self.max_active, self.active)
            time.sleep(0.05)
            with self.lock:
                self.active -= 1
            return (
                [{"frame": start_index + offset + 1} for offset in range(len(batch))],
                {"prompt_tokens": len(batch), "completion_tokens": len(batch) * 2},
            )

    service = ConcurrentFakeVideoAnalysisService()
    progress = []

    results, tokens = service.analyze_frames(
        [f"frame-{index}.jpg" for index in range(6)],
        timestamps_sec=[float(index * 30) for index in range(6)],
        progress_callback=lambda completed, total: progress.append((completed, total)),
        max_workers=3,
    )

    assert service.max_active >= 2
    assert [item["frame"] for item in results] == [1, 2, 3, 4, 5, 6]
    assert tokens == {"prompt": 6, "completion": 12}
    assert progress[-1] == (6, 6)


def test_visual_frame_selection_adds_scene_change_frames_after_time_baseline():
    frames = [
        {"frame_id": f"f{i}", "timestamp": i * 10, "frame_type": "interval", "diff_score": 0, "image_path": f"{i}.jpg"}
        for i in range(12)
    ]
    frames.append({"frame_id": "scene-a", "timestamp": 25, "frame_type": "scene_change", "diff_score": 0.45, "image_path": "scene-a.jpg"})
    frames.append({"frame_id": "scene-b", "timestamp": 75, "frame_type": "interval", "diff_score": 0.2, "image_path": "scene-b.jpg"})

    selected = select_visual_frame_events(frames, target_interval=30, max_frames=8, scene_diff_threshold=0.12)
    selected_ids = {item["frame_id"] for item in selected}

    assert "scene-a" in selected_ids
    assert "scene-b" in selected_ids
    assert len(selected) == 6
    assert [item["timestamp"] for item in selected] == sorted(item["timestamp"] for item in selected)


def test_visual_frame_selection_summary_reports_strategy_and_type_counts():
    selected = [
        {"frame_type": "start"},
        {"frame_type": "interval"},
        {"frame_type": "scene_change"},
    ]

    summary = visual_frame_selection_summary(10, selected, 30, 180, 0.12)

    assert summary["strategy"] == "time_interval_plus_scene_change"
    assert summary["captured_frame_count"] == 10
    assert summary["selected_frame_count"] == 3
    assert summary["selected_type_counts"]["scene_change"] == 1
