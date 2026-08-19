"""Select captured visual frames for model analysis."""

from app.config import settings


def select_visual_frame_events(
    frames: list[dict],
    target_interval: int = 30,
    max_frames: int | None = None,
    scene_diff_threshold: float | None = None
) -> list[dict]:
    """Pick a time baseline, then add high-change frames up to the configured cap."""
    if not frames:
        return []

    max_frames = max_frames or settings.VIDEO_ANALYSIS_MAX_FRAMES
    scene_diff_threshold = (
        settings.VIDEO_SCENE_DIFF_THRESHOLD
        if scene_diff_threshold is None
        else scene_diff_threshold
    )
    selected = []
    selected_keys = set()
    last_interval_ts = -target_interval

    def frame_key(item: dict) -> str:
        return str(item.get("frame_id") or item.get("image_path") or item.get("timestamp") or id(item))

    def add_frame(item: dict) -> bool:
        key = frame_key(item)
        if key in selected_keys:
            return False
        selected.append(item)
        selected_keys.add(key)
        return True

    for item in frames:
        ts = float(item.get("timestamp") or 0)
        frame_type = item.get("frame_type", "")
        if frame_type in {"start", "stop"}:
            add_frame(item)
        elif ts - last_interval_ts >= target_interval:
            if add_frame(item):
                last_interval_ts = ts

    if len(selected) <= max_frames:
        remaining = max_frames - len(selected)
        scene_candidates = [
            item for item in frames
            if frame_key(item) not in selected_keys
            and (
                item.get("frame_type") == "scene_change"
                or float(item.get("diff_score") or 0) >= scene_diff_threshold
            )
        ]
        scene_candidates.sort(
            key=lambda item: (
                float(item.get("diff_score") or 0),
                float(item.get("timestamp") or 0)
            ),
            reverse=True
        )
        for item in scene_candidates[:remaining]:
            add_frame(item)
        selected.sort(key=lambda item: float(item.get("timestamp") or 0))
        return selected

    special = [item for item in selected if item.get("frame_type") in {"start", "stop"}]
    regular = [item for item in selected if item.get("frame_type") not in {"start", "stop", "scene_change"}]
    remaining = max(0, max_frames - len(special))
    if remaining <= 0:
        sampled = special[:max_frames]
    else:
        if len(regular) <= remaining:
            sampled_regular = regular
        else:
            step = max(1, len(regular) / remaining)
            sampled_regular = [regular[int(i * step)] for i in range(remaining)]
        sampled = special + sampled_regular

    sampled.sort(key=lambda item: float(item.get("timestamp") or 0))
    return sampled


def visual_frame_selection_summary(
    captured_count: int,
    selected_frames: list[dict],
    target_interval: int,
    max_frames: int,
    scene_diff_threshold: float,
) -> dict:
    type_counts: dict[str, int] = {}
    for item in selected_frames:
        frame_type = item.get("frame_type") or "interval"
        type_counts[frame_type] = type_counts.get(frame_type, 0) + 1
    return {
        "strategy": "time_interval_plus_scene_change",
        "target_interval_sec": target_interval,
        "max_frames": max_frames,
        "scene_diff_threshold": scene_diff_threshold,
        "captured_frame_count": captured_count,
        "selected_frame_count": len(selected_frames),
        "selected_type_counts": type_counts,
    }
