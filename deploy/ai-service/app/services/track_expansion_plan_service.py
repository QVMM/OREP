"""Stage-8 helpers for expanding pilot track rules to all 42 tracks."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


REQUIRED_EVIDENCE_LEVELS = {"E0", "E1", "E2", "E3", "E4", "E5"}
TRACK_SOURCE_TYPES = {"official", "track_inference", "orep_training"}


def load_track_expansion_plan(path: str | Path | None = None) -> dict[str, Any]:
    """Load the stage-8 expansion plan asset."""
    plan_path = Path(path) if path else Path(__file__).resolve().parents[1] / "rubrics" / "track_expansion_plan_v1.json"
    with plan_path.open(encoding="utf-8") as f:
        return json.load(f)


def validate_track_expansion_plan(plan: dict[str, Any] | None, markdown_dir: str | Path) -> dict[str, Any]:
    """Validate that stage-8 has a complete, non-duplicated 42-track expansion plan."""
    source = plan or {}
    batches = _as_list(source.get("batches"))
    gate = source.get("globalAdmissionGate") if isinstance(source.get("globalAdmissionGate"), dict) else {}
    markdown_root = Path(markdown_dir)
    markdown_track_names = {
        path.stem
        for path in markdown_root.glob("*.md")
        if path.name not in {"README.md", "42赛道梯度评分规则v1.2定义总纲.md"}
    }

    blocking_reasons: list[str] = []
    tracks: list[dict[str, Any]] = []
    for batch in batches:
        if not isinstance(batch, dict):
            blocking_reasons.append("each batch must be an object")
            continue
        if not batch.get("batchId") or not batch.get("batchName"):
            blocking_reasons.append("each batch must have batchId and batchName")
        if not _as_list(batch.get("tracks")):
            blocking_reasons.append(f"{batch.get('batchId') or 'batch'} must include tracks")
        tracks.extend(track for track in _as_list(batch.get("tracks")) if isinstance(track, dict))

    track_names = [str(track.get("trackName") or "") for track in tracks]
    track_ids = [str(track.get("trackId") or "") for track in tracks]
    duplicated_names = sorted(name for name, count in Counter(track_names).items() if name and count > 1)
    duplicated_ids = sorted(track_id for track_id, count in Counter(track_ids).items() if track_id and count > 1)
    missing_markdown = sorted(markdown_track_names - set(track_names))
    unknown_tracks = sorted(set(track_names) - markdown_track_names)

    if len(batches) != 5:
        blocking_reasons.append("stage8 expansion plan must contain 5 batches")
    if len(tracks) != 42:
        blocking_reasons.append("stage8 expansion plan must contain 42 tracks")
    if duplicated_names:
        blocking_reasons.append(f"duplicated track names: {', '.join(duplicated_names)}")
    if duplicated_ids:
        blocking_reasons.append(f"duplicated track ids: {', '.join(duplicated_ids)}")
    if missing_markdown:
        blocking_reasons.append(f"markdown tracks missing from plan: {', '.join(missing_markdown)}")
    if unknown_tracks:
        blocking_reasons.append(f"plan tracks missing markdown source: {', '.join(unknown_tracks)}")

    blocking_reasons.extend(_validate_global_gate(gate))
    for track in tracks:
        blocking_reasons.extend(_validate_planned_track(track, gate, markdown_root))

    return {
        "status": "ready" if not blocking_reasons else "not_ready",
        "trackCount": len(tracks),
        "batchCount": len(batches),
        "trackStatusCounts": dict(Counter(str(track.get("status") or "unknown") for track in tracks)),
        "blockingReasons": blocking_reasons,
    }


def validate_track_expansion_candidate(
    track_rule: dict[str, Any] | None,
    samples: list[dict[str, Any]] | None,
    audit_record: dict[str, Any] | None,
    quality_report: dict[str, Any] | None,
    global_gate: dict[str, Any] | None,
) -> dict[str, Any]:
    """Validate a single new track before it can move from planned to pilot/active."""
    rule = track_rule or {}
    gate = global_gate or {}
    sample_list = [sample for sample in _as_list(samples) if isinstance(sample, dict)]
    audit = audit_record or {}
    report = quality_report or {}
    blocking_reasons: list[str] = []

    if len(_as_list(rule.get("observations"))) != 15:
        blocking_reasons.append("rule must contain 15 observations")
    if set(rule.get("evidenceCaps") or {}) != REQUIRED_EVIDENCE_LEVELS:
        blocking_reasons.append("rule must define E0-E5 evidence caps")
    if rule.get("sourceType") not in TRACK_SOURCE_TYPES:
        blocking_reasons.append("rule sourceType must identify official, track_inference, or orep_training")
    if not _has_track_specific_evidence(rule):
        blocking_reasons.append("track-specific acceptable evidence is required")
    if not _rules_have_deduction_and_recovery(rule):
        blocking_reasons.append("deduction and recovery rules are required")

    minimum_samples = int(gate.get("minimumAdmissionSamplesPerTrack") or 10)
    if len(sample_list) < minimum_samples:
        blocking_reasons.append("at least 10 admission samples are required")
    sample_type_counts = Counter(str(sample.get("sampleType") or "") for sample in sample_list)
    if sample_type_counts["low_evidence"] < int(gate.get("minimumLowEvidenceSamples") or 2):
        blocking_reasons.append("at least 2 low-evidence samples are required")
    if sample_type_counts["middle_score"] < int(gate.get("minimumMiddleSamples") or 2):
        blocking_reasons.append("at least 2 middle-score samples are required")
    if sample_type_counts["high_score"] < int(gate.get("minimumHighEvidenceSamples") or 2):
        blocking_reasons.append("at least 2 high-evidence samples are required")
    if sample_type_counts["demo_failure"] + sample_type_counts["material_missing"] < int(
        gate.get("minimumDemoFailureOrMissingMaterialSamples") or 1
    ):
        blocking_reasons.append("at least 1 demo-failure or missing-material sample is required")

    if gate.get("requiresRuleAdmissionAudit") is True and audit.get("status") != "approved":
        blocking_reasons.append("rule admission audit is required")
    if gate.get("requiresQualityReport") is True and report.get("status") != "ready":
        blocking_reasons.append("ready quality report is required")

    return {
        "status": "ready" if not blocking_reasons else "not_ready",
        "blockingReasons": blocking_reasons,
        "sampleTypeCounts": dict(sample_type_counts),
    }


def summarize_stage8_final_readiness(
    plan: dict[str, Any] | None,
    rubric_dir: str | Path,
    admission_dir: str | Path,
    markdown_dir: str | Path,
) -> dict[str, Any]:
    """Summarize final stage-8 asset coverage without promoting generated tracks to active."""
    source = plan or {}
    tracks = [
        track
        for batch in _as_list(source.get("batches"))
        if isinstance(batch, dict)
        for track in _as_list(batch.get("tracks"))
        if isinstance(track, dict)
    ]
    rubric_root = Path(rubric_dir)
    admission_root = Path(admission_dir)
    markdown_root = Path(markdown_dir)

    missing_structured_rules: list[dict[str, str]] = []
    missing_admission_assets: list[dict[str, str]] = []
    tracks_allowed_active: list[dict[str, str]] = []
    structured_rule_count = 0
    active_ready_count = 0
    active_blocked_count = 0

    for track in tracks:
        status = str(track.get("status") or "")
        track_id = str(track.get("trackId") or "")
        track_name = str(track.get("trackName") or "")

        structured_rule_path = _structured_rule_path_for_track(track, rubric_root)
        if structured_rule_path and structured_rule_path.exists():
            structured_rule_count += 1
        else:
            missing_structured_rules.append(
                {
                    "trackId": track_id,
                    "trackName": track_name,
                    "path": str(track.get("structuredRuleFile") or f"track_{track_id}_*_engine_pilot.json"),
                }
            )

        if status == "pilot_generated":
            promotion = track.get("pilotPromotion") if isinstance(track.get("pilotPromotion"), dict) else {}
            if promotion.get("activeAllowed") is True:
                active_ready_count += 1
                tracks_allowed_active.append({"trackId": track_id, "trackName": track_name})
            else:
                active_blocked_count += 1

            for asset_type in ("admissionManifest", "ruleAdmissionAudit", "qualityReport"):
                asset_value = str(track.get(asset_type) or "")
                asset_path = _resolve_asset_path(asset_value, admission_root)
                if not asset_value or not asset_path.exists():
                    missing_admission_assets.append(
                        {
                            "trackId": track_id,
                            "trackName": track_name,
                            "assetType": asset_type,
                            "path": asset_value,
                        }
                    )

    markdown_files = [
        path
        for path in markdown_root.glob("*.md")
        if path.name not in {"README.md", "42赛道梯度评分规则v1.2定义总纲.md"}
    ]
    real_sample_blockers = [
        "pilot_generated tracks use generated admission assets and require real raw samples before active",
        "stage8 active promotion must rerun candidate gate with real original competition samples",
    ]
    blocking_reasons = []
    if len(tracks) != 42:
        blocking_reasons.append("stage8 final summary must cover 42 tracks")
    if len(markdown_files) != 42:
        blocking_reasons.append("stage8 final summary must cover 42 markdown sources")
    if missing_structured_rules:
        blocking_reasons.append("structured rule files are missing")
    if missing_admission_assets:
        blocking_reasons.append("generated admission assets are missing")
    if tracks_allowed_active:
        blocking_reasons.append("pilot_generated tracks must not allow active")

    return {
        "status": "not_ready" if blocking_reasons else "pilot_ready_not_active",
        "trackCount": len(tracks),
        "markdownSourceCount": len(markdown_files),
        "structuredRuleCount": structured_rule_count,
        "pilotCompletedCount": sum(1 for track in tracks if track.get("status") == "pilot_completed"),
        "pilotGeneratedCount": sum(1 for track in tracks if track.get("status") == "pilot_generated"),
        "activeReadyCount": active_ready_count,
        "activeBlockedCount": active_blocked_count,
        "missingStructuredRuleFiles": missing_structured_rules,
        "missingAdmissionAssets": missing_admission_assets,
        "tracksAllowedActive": tracks_allowed_active,
        "realSampleRevalidationRequired": True,
        "realSampleRevalidationBlockers": real_sample_blockers,
        "blockingReasons": blocking_reasons,
    }


def _validate_global_gate(gate: dict[str, Any]) -> list[str]:
    reasons = []
    if int(gate.get("minimumAdmissionSamplesPerTrack") or 0) < 10:
        reasons.append("global gate must require at least 10 admission samples per track")
    if int(gate.get("recommendedSamplesBeforeActive") or 0) < 30:
        reasons.append("global gate must recommend at least 30 samples before active")
    for field in ("requiresRuleAdmissionAudit", "requiresHumanSpotCheck", "requiresQualityReport"):
        if gate.get(field) is not True:
            reasons.append(f"global gate must set {field}=true")
    return reasons


def _validate_planned_track(track: dict[str, Any], gate: dict[str, Any], markdown_root: Path) -> list[str]:
    reasons = []
    track_name = str(track.get("trackName") or "")
    source_markdown = str(track.get("sourceMarkdown") or "")
    if not track.get("trackId"):
        reasons.append(f"{track_name or 'track'} missing trackId")
    if not track_name.endswith("赛道"):
        reasons.append(f"{track_name or 'track'} must use the赛道 name")
    if track.get("status") not in {"pilot_completed", "pilot_generated", "planned"}:
        reasons.append(f"{track_name or 'track'} has invalid stage8 status")
    if not _as_list(track.get("evidenceFocus")):
        reasons.append(f"{track_name or 'track'} missing evidenceFocus")
    if track.get("admissionGate") != gate:
        reasons.append(f"{track_name or 'track'} admission gate must match global gate")
    if source_markdown and not (markdown_root / Path(source_markdown).name).exists():
        reasons.append(f"{track_name or 'track'} source markdown not found")
    if source_markdown and track_name and not source_markdown.endswith(f"{track_name}.md"):
        reasons.append(f"{track_name} source markdown must match track name")
    return reasons


def _has_track_specific_evidence(rule: dict[str, Any]) -> bool:
    observations = _as_list(rule.get("observations"))
    if not observations:
        return False
    for observation in observations:
        if not isinstance(observation, dict):
            continue
        acceptable_evidence = [str(item) for item in _as_list(observation.get("acceptableEvidence")) if str(item).strip()]
        track_definition = str(observation.get("trackDefinition") or "").strip()
        if track_definition and len(acceptable_evidence) >= 3:
            return True
    return False


def _rules_have_deduction_and_recovery(rule: dict[str, Any]) -> bool:
    observations = _as_list(rule.get("observations"))
    if not observations:
        return False
    return all(
        isinstance(observation, dict)
        and _as_list(observation.get("deductionRules"))
        and _as_list(observation.get("recoveryRules"))
        for observation in observations
    )


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _structured_rule_path_for_track(track: dict[str, Any], rubric_root: Path) -> Path | None:
    explicit_rule = str(track.get("structuredRuleFile") or "")
    if explicit_rule:
        return _resolve_asset_path(explicit_rule, rubric_root)
    track_id = str(track.get("trackId") or "")
    matches = sorted(rubric_root.glob(f"track_{track_id}_*_engine_pilot.json"))
    return matches[0] if matches else None


def _resolve_asset_path(asset_path: str, base_dir: Path) -> Path:
    path = Path(asset_path)
    if path.is_absolute():
        return path
    cwd_path = Path.cwd() / path
    if cwd_path.exists():
        return cwd_path
    return base_dir / path.name
