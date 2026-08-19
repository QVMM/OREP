"""跨场次评分稳定钳制。

同一音画指纹（时长 + 帧数 + 赛道 + 团队规模）的历史结果，
维度分相对上次变动超过阈值时钳制，降低抽取噪声导致的「武断跳变」。
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# 单维允许相对上次的最大跳动（分）
DEFAULT_DIM_MAX_DELTA = 1.5
# 总分允许相对上次的最大跳动（分）
DEFAULT_OVERALL_MAX_DELTA = 5.0


def apply_cross_session_stability(
    authoritative: dict[str, Any],
    result: dict | None,
    *,
    dim_max_delta: float = DEFAULT_DIM_MAX_DELTA,
    overall_max_delta: float = DEFAULT_OVERALL_MAX_DELTA,
    upload_dir: str | None = None,
) -> dict[str, Any]:
    """对 rule executor 输出做跨场次钳制；无先验则原样返回。"""
    if not isinstance(authoritative, dict):
        return authoritative
    prior = resolve_prior_dimension_scores(result, upload_dir=upload_dir)
    if not prior:
        return authoritative
    prior_dims = prior.get("dimensions") or {}
    if not prior_dims:
        return authoritative

    out = dict(authoritative)
    cur_dims = dict(out.get("dimensionScores") or {})
    max_dims = dict(out.get("dimensionMaxScores") or {})
    clamped_dims: dict[str, float] = {}
    clamp_log: list[dict[str, Any]] = []

    for dim, score in cur_dims.items():
        try:
            cur = float(score)
        except Exception:
            clamped_dims[dim] = score
            continue
        if dim not in prior_dims:
            clamped_dims[dim] = round(cur, 2)
            continue
        try:
            prev = float(prior_dims[dim])
        except Exception:
            clamped_dims[dim] = round(cur, 2)
            continue
        lo = prev - dim_max_delta
        hi = prev + dim_max_delta
        # 不超过维度满分
        try:
            dmax = float(max_dims.get(dim) or 100)
            hi = min(hi, dmax)
            lo = max(0.0, lo)
        except Exception:
            lo = max(0.0, lo)
        new_score = min(hi, max(lo, cur))
        new_score = round(new_score, 2)
        clamped_dims[dim] = new_score
        if abs(new_score - cur) > 1e-9:
            clamp_log.append(
                {
                    "dimension": dim,
                    "before": round(cur, 2),
                    "after": new_score,
                    "prior": round(prev, 2),
                    "maxDelta": dim_max_delta,
                }
            )

    if not clamp_log and not prior.get("overall"):
        # 即使维内未触发，仍可能对总分钳制
        pass

    # 按比例缩放该维观测点 finalScore / baseScore，尽量保持内部一致
    observations = list(out.get("observations") or [])
    if clamp_log:
        observations = _scale_observations_to_dimension_targets(observations, cur_dims, clamped_dims)

    new_final = round(sum(float(v) for v in clamped_dims.values()), 2)
    # 总分钳制：仅当已做维内钳制后仍越界时，做一次等比例收缩（不抬高单维超过维内上限）
    prior_overall = prior.get("overall")
    if prior_overall is not None and clamp_log:
        try:
            po = float(prior_overall)
            lo = po - overall_max_delta
            hi = po + overall_max_delta
            if new_final > hi + 1e-9 and new_final > 1e-9:
                target_final = round(hi, 2)
                factor = target_final / new_final
                scaled_dims = {k: round(float(v) * factor, 2) for k, v in clamped_dims.items()}
                drift = round(target_final - sum(scaled_dims.values()), 2)
                if abs(drift) > 1e-9 and scaled_dims:
                    first = next(iter(scaled_dims))
                    scaled_dims[first] = round(scaled_dims[first] + drift, 2)
                observations = _scale_observations_to_dimension_targets(
                    observations, clamped_dims, scaled_dims
                )
                clamped_dims = scaled_dims
                new_final = target_final
                clamp_log.append(
                    {
                        "dimension": "_overall",
                        "before": round(sum(float(v) for v in cur_dims.values()), 2),
                        "after": new_final,
                        "prior": round(po, 2),
                        "maxDelta": overall_max_delta,
                    }
                )
        except Exception:
            pass

    out["dimensionScores"] = clamped_dims
    out["finalScore"] = new_final
    out["observations"] = observations
    # 刷新 reconciliation 中的关键合计（宽松；loss ledger 保持原样作诊断）
    recon = dict(out.get("reconciliation") or {})
    recon["finalScore"] = new_final
    recon["dimensionScoreTotal"] = new_final
    out["reconciliation"] = recon
    if clamp_log:
        out["_stability_clamp"] = {
            "priorMeetingId": prior.get("meeting_id"),
            "priorOverall": prior.get("overall"),
            "fingerprint": prior.get("fingerprint"),
            "changes": clamp_log,
        }
        logger.info(
            "cross-session stability clamp applied: prior=%s changes=%s",
            prior.get("meeting_id"),
            clamp_log,
        )
    return out


def resolve_prior_dimension_scores(
    result: dict | None,
    *,
    upload_dir: str | None = None,
) -> dict[str, Any] | None:
    """解析先验维度分：显式快照 > 磁盘同指纹最近场次。"""
    if not isinstance(result, dict):
        return None

    explicit = (
        result.get("prior_scoring_snapshot")
        or result.get("stability_prior")
        or result.get("priorScoringSnapshot")
    )
    if isinstance(explicit, dict) and (explicit.get("dimensions") or explicit.get("dimensionScores")):
        dims = explicit.get("dimensions") or explicit.get("dimensionScores") or {}
        flat = _flatten_dim_scores(dims)
        if flat:
            return {
                "dimensions": flat,
                "overall": _safe_float(
                    explicit.get("overall")
                    or explicit.get("overall_score")
                    or explicit.get("finalScore")
                ),
                "meeting_id": explicit.get("meeting_id") or explicit.get("meetingId"),
                "fingerprint": explicit.get("fingerprint"),
                "source": "explicit",
            }

    # 显式 related session
    related = (
        result.get("related_session_id")
        or result.get("rescore_of_session_id")
        or result.get("relatedSessionId")
    )
    if related is not None:
        loaded = _load_result_file(str(related), upload_dir=upload_dir)
        if loaded:
            snap = _snapshot_from_result(loaded)
            if snap:
                snap["source"] = f"related_session:{related}"
                return snap

    fp = build_media_fingerprint(result)
    if not fp or not fp.get("asr_duration"):
        return None

    prior_path = _find_latest_matching_result(
        fp,
        exclude_meeting_id=str(result.get("meeting_id") or ""),
        upload_dir=upload_dir,
    )
    if not prior_path:
        return None
    try:
        loaded = json.loads(prior_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    snap = _snapshot_from_result(loaded)
    if not snap:
        return None
    snap["source"] = f"fingerprint:{prior_path.name}"
    snap["fingerprint"] = fp
    return snap


def build_media_fingerprint(result: dict | None) -> dict[str, Any]:
    if not isinstance(result, dict):
        return {}
    asr = result.get("asr") if isinstance(result.get("asr"), dict) else {}
    va = result.get("video_analysis") if isinstance(result.get("video_analysis"), dict) else {}
    pi = result.get("project_info") if isinstance(result.get("project_info"), dict) else {}
    duration = _safe_float(asr.get("duration"))
    try:
        frames = int(va.get("frame_count") or 0)
    except Exception:
        frames = 0
    try:
        team_size = int(pi.get("team_size") or 0)
    except Exception:
        team_size = 0
    track = str(pi.get("track") or result.get("track") or "").strip()
    return {
        "asr_duration": round(duration, 1) if duration else 0.0,
        "frame_count": frames,
        "track": track,
        "team_size": team_size,
    }


def fingerprints_match(a: dict[str, Any], b: dict[str, Any]) -> bool:
    if not a or not b:
        return False
    if not a.get("asr_duration") or not b.get("asr_duration"):
        return False
    if abs(float(a["asr_duration"]) - float(b["asr_duration"])) > 0.15:
        return False
    if int(a.get("frame_count") or 0) != int(b.get("frame_count") or 0):
        return False
    # 帧数都为 0 时不可靠，要求赛道一致且时长命中仍不够 → 拒绝
    if int(a.get("frame_count") or 0) <= 0:
        return False
    ta, tb = str(a.get("track") or ""), str(b.get("track") or "")
    if ta and tb and ta != tb:
        return False
    sa, sb = int(a.get("team_size") or 0), int(b.get("team_size") or 0)
    if sa and sb and sa != sb:
        return False
    return True


def _snapshot_from_result(result: dict) -> dict[str, Any] | None:
    ai = result.get("ai_score") if isinstance(result.get("ai_score"), dict) else {}
    shadow = result.get("rule_engine_shadow") if isinstance(result.get("rule_engine_shadow"), dict) else {}
    dims = {}
    if isinstance(ai.get("dimensions"), dict) and ai["dimensions"]:
        dims = _flatten_dim_scores(ai["dimensions"])
    elif isinstance(shadow.get("dimensionScores"), dict) and shadow["dimensionScores"]:
        dims = _flatten_dim_scores(shadow["dimensionScores"])
    if not dims:
        return None
    overall = _safe_float(
        ai.get("overall_score"),
        _safe_float(shadow.get("finalScore"), sum(dims.values())),
    )
    return {
        "dimensions": dims,
        "overall": overall,
        "meeting_id": result.get("meeting_id"),
        "fingerprint": build_media_fingerprint(result),
    }


def _flatten_dim_scores(dims: dict) -> dict[str, float]:
    out: dict[str, float] = {}
    for k, v in (dims or {}).items():
        if isinstance(v, dict):
            try:
                out[str(k)] = float(v.get("score"))
            except Exception:
                continue
        else:
            try:
                out[str(k)] = float(v)
            except Exception:
                continue
    return out


def _scale_observations_to_dimension_targets(
    observations: list,
    old_dims: dict[str, Any],
    new_dims: dict[str, float],
) -> list:
    by_dim: dict[str, list[dict]] = {}
    passthrough: list = []
    for obs in observations:
        if not isinstance(obs, dict):
            passthrough.append(obs)
            continue
        dim = str(obs.get("dimensionCode") or "unassigned")
        by_dim.setdefault(dim, []).append(dict(obs))

    scaled: list = list(passthrough)
    for dim, rows in by_dim.items():
        old_total = float(
            old_dims.get(dim)
            if dim in old_dims
            else sum(float(r.get("finalScore") or 0) for r in rows)
        )
        new_total = float(new_dims.get(dim) if dim in new_dims else old_total)
        if abs(old_total - new_total) < 1e-9:
            scaled.extend(rows)
            continue
        if old_total <= 1e-9:
            if rows and new_total > 0:
                each = round(new_total / len(rows), 2)
                rem = new_total
                for i, row in enumerate(rows):
                    val = each if i < len(rows) - 1 else round(rem, 2)
                    rem = round(rem - val, 2)
                    cap = float(row.get("scoreCap") or row.get("maxScore") or val)
                    val = min(max(0.0, val), cap)
                    row["finalScore"] = val
                    row["baseScore"] = max(float(row.get("baseScore") or 0), val)
                    row["performanceScore"] = row["baseScore"]
                    scaled.append(row)
            else:
                scaled.extend(rows)
            continue
        factor = new_total / old_total
        rem = new_total
        for i, row in enumerate(rows):
            old_f = float(row.get("finalScore") or row.get("baseScore") or 0)
            if i < len(rows) - 1:
                val = round(old_f * factor, 2)
                rem = round(rem - val, 2)
            else:
                val = round(rem, 2)
            cap = float(row.get("scoreCap") or row.get("maxScore") or val)
            val = min(max(0.0, val), cap)
            row["finalScore"] = val
            row["baseScore"] = max(float(row.get("baseScore") or 0), val)
            row["performanceScore"] = row["baseScore"]
            scaled.append(row)
    return scaled


def _find_latest_matching_result(
    fingerprint: dict[str, Any],
    *,
    exclude_meeting_id: str,
    upload_dir: str | None,
) -> Path | None:
    root = Path(upload_dir or os.getenv("UPLOAD_DIR") or "/app/uploads")
    results_dir = root / "results"
    if not results_dir.is_dir():
        # local dev fallback
        local = Path(__file__).resolve().parents[2] / "uploads" / "results"
        results_dir = local if local.is_dir() else results_dir
    if not results_dir.is_dir():
        return None

    candidates: list[tuple[float, Path]] = []
    for path in results_dir.glob("result_*.json"):
        if path.name.endswith(".bak") or ".bak_" in path.name:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        mid = str(data.get("meeting_id") or path.stem.replace("result_", ""))
        if exclude_meeting_id and mid == str(exclude_meeting_id):
            continue
        other_fp = build_media_fingerprint(data)
        if not fingerprints_match(fingerprint, other_fp):
            continue
        # 必须有维度分
        if not _snapshot_from_result(data):
            continue
        try:
            mtime = path.stat().st_mtime
        except Exception:
            mtime = 0
        candidates.append((mtime, path))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def _load_result_file(session_id: str, *, upload_dir: str | None) -> dict | None:
    root = Path(upload_dir or os.getenv("UPLOAD_DIR") or "/app/uploads")
    path = root / "results" / f"result_{session_id}.json"
    if not path.is_file():
        local = Path(__file__).resolve().parents[2] / "uploads" / "results" / f"result_{session_id}.json"
        path = local if local.is_file() else path
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default
