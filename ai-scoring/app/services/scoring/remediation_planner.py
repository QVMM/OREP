"""Build a complete, deterministic remediation map from scoring losses."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import re


_PRIORITY_RANK = {"P0": 0, "P1": 1, "P2": 2}


def build_complete_remediation_map(*, action_plan, loss_ledger):
    """Preserve model advice, link explicit facts, and add one fallback for every gap."""

    losses = [deepcopy(row) for row in list(loss_ledger or []) if _valid_loss(row)]
    loss_by_id = {row["lossId"]: row for row in losses}
    tasks = [
        _normalize_model_task(row, index, losses)
        for index, row in enumerate(list(action_plan or []))
        if isinstance(row, dict)
    ]
    covered = {
        loss_id
        for task in tasks
        for loss_id in task.get("coveredLossIds", [])
        if loss_id in loss_by_id
    }
    for loss in losses:
        if loss["lossId"] not in covered:
            tasks.append(_fallback_task(loss))
    return _merge_compatible_tasks(tasks, loss_by_id)


def _normalize_model_task(raw, index, losses):
    task = deepcopy(raw)
    explicit_id = str(task.get("taskId") or task.get("id") or f"model-{index + 1}").strip()
    method = _first_text(task, "method", "action", "suggestion", "trainingAction")
    title = _first_text(task, "title", "name") or f"整改任务 {index + 1}"
    root = str(
        task.get("rootCauseKey")
        or task.get("sourceIssueKey")
        or f"model:{explicit_id}"
    ).strip()
    covered = _resolve_covered_losses(task, losses)
    acceptance = _acceptance_from_task_or_losses(task, covered)
    full_score = _full_score_from_task_or_losses(task, covered)
    task_id = _task_id("model", root, method or title)
    priority = _priority(task.get("priority"), covered)
    return {
        **task,
        "taskId": task_id,
        "rootCauseKey": root,
        "priority": priority,
        "executionGroup": task.get("executionGroup") or ("current" if priority == "P0" else "queue"),
        "title": title,
        "problem": _first_text(task, "problem", "issue", "reason"),
        "method": method,
        "coveredLossIds": [row["lossId"] for row in covered],
        "observationCodes": _unique(row.get("observationCode") for row in covered),
        "coveredGapPoints": _round1(sum(float(row.get("points") or 0) for row in covered)),
        "minimumAcceptance": acceptance,
        "fullScoreCriteria": full_score,
        "dependencies": list(task.get("dependencies") or []),
        "status": str(task.get("status") or "not_started"),
    }


def _resolve_covered_losses(task, losses):
    explicit_ids = set(_as_strings(task.get("coveredLossIds") or task.get("covered_loss_ids")))
    if explicit_ids:
        return [row for row in losses if row["lossId"] in explicit_ids]

    observation_codes = set(_as_strings(
        task.get("observationCodes")
        or task.get("observation_codes")
        or task.get("observationCode")
        or task.get("observation_code")
    ))
    requested_types = set(_as_strings(task.get("lossTypes") or task.get("loss_types")))
    if observation_codes:
        return [
            row for row in losses
            if row.get("observationCode") in observation_codes
            and (not requested_types or row.get("lossType") in requested_types)
        ]

    source_key = str(task.get("sourceIssueKey") or task.get("source_issue_key") or "").strip()
    if not source_key:
        return []
    return [
        row for row in losses
        if source_key in {
            str(row.get("lossKey") or ""),
            str(row.get("causeCode") or ""),
            str(row.get("penaltyRuleCode") or ""),
            str(row.get("deductionId") or ""),
        }
    ]


def _fallback_task(loss):
    name = str(loss.get("observationName") or loss.get("observationCode") or "评分观测点")
    loss_type = str(loss.get("lossType") or "unresolved_gap")
    if loss_type == "evidence_limited":
        title = f"补齐{name}的可核验证据"
    elif loss_type == "hard_violation":
        title = f"消除{name}的规则违规风险"
    else:
        title = f"提升{name}的现场达成度"
    method = str(loss.get("trainingTaskTemplate") or "").strip() or f"围绕{name}按赛道规则补齐过程、结果与复核材料。"
    root = str(loss.get("causeCode") or loss["lossId"])
    return {
        "taskId": _task_id("fallback", root, method),
        "rootCauseKey": root,
        "priority": _priority(None, [loss]),
        "executionGroup": "current" if float(loss.get("points") or 0) >= 5 else "queue",
        "title": title,
        "problem": str(loss.get("reason") or f"{name}尚未达到规则要求"),
        "method": method,
        "coveredLossIds": [loss["lossId"]],
        "observationCodes": [str(loss.get("observationCode") or "unassigned")],
        "coveredGapPoints": _round1(loss.get("points")),
        "minimumAcceptance": _acceptance_from_losses([loss]),
        "fullScoreCriteria": _full_score_from_losses([loss]),
        "evidenceAnchorIds": list(loss.get("evidenceAnchorIds") or []),
        "dependencies": [],
        "status": "not_started",
        "sourceKind": "loss-ledger-fallback",
    }


def _merge_compatible_tasks(tasks, loss_by_id):
    merged = []
    positions = {}
    for task in tasks:
        key = (task["rootCauseKey"], _normalized_action(task.get("method")))
        if not key[1] or str(task["rootCauseKey"]).startswith("model:"):
            merged.append(task)
            continue
        if key not in positions:
            positions[key] = len(merged)
            merged.append(task)
            continue
        target = merged[positions[key]]
        target["coveredLossIds"] = _unique(target["coveredLossIds"] + task["coveredLossIds"])
        target["observationCodes"] = _unique(target["observationCodes"] + task["observationCodes"])
        target["priority"] = min(
            (target["priority"], task["priority"]),
            key=lambda value: _PRIORITY_RANK.get(value, 9),
        )
        target["evidenceAnchorIds"] = _unique(
            list(target.get("evidenceAnchorIds") or []) + list(task.get("evidenceAnchorIds") or [])
        )
    for task in merged:
        unique_losses = [loss_by_id[loss_id] for loss_id in task["coveredLossIds"] if loss_id in loss_by_id]
        task["coveredGapPoints"] = _round1(sum(float(row.get("points") or 0) for row in unique_losses))
        if unique_losses:
            task["minimumAcceptance"] = _merge_acceptance(task.get("minimumAcceptance"), unique_losses)
            task["fullScoreCriteria"] = _merge_full_score(task.get("fullScoreCriteria"), unique_losses)
    return merged


def _acceptance_from_task_or_losses(task, losses):
    value = task.get("minimumAcceptance")
    if isinstance(value, dict) and str(value.get("summary") or "").strip():
        return {
            "summary": str(value["summary"]).strip(),
            "requiredEvidence": _as_strings(value.get("requiredEvidence")),
        }
    explicit = _first_text(task, "acceptance", "acceptanceCriteria")
    if explicit:
        return {"summary": explicit, "requiredEvidence": _evidence_from_losses(losses)}
    return _acceptance_from_losses(losses)


def _acceptance_from_losses(losses):
    required = _unique(
        info
        for loss in losses
        for info in _as_strings(loss.get("requiredInfo"))
    )
    summary = "；".join(required) if required else "整改结果可定位、可复核，并能支撑对应观测点"
    return {"summary": summary, "requiredEvidence": _evidence_from_losses(losses)}


def _merge_acceptance(current, losses):
    current = current if isinstance(current, dict) else {}
    generated = _acceptance_from_losses(losses)
    return {
        "summary": str(current.get("summary") or generated["summary"]),
        "requiredEvidence": _unique(
            _as_strings(current.get("requiredEvidence")) + generated["requiredEvidence"]
        ),
    }


def _full_score_from_task_or_losses(task, losses):
    value = task.get("fullScoreCriteria")
    if isinstance(value, dict) and str(value.get("summary") or "").strip():
        return {
            "summary": str(value["summary"]).strip(),
            "ruleReference": value.get("ruleReference"),
        }
    return _full_score_from_losses(losses)


def _full_score_from_losses(losses):
    definitions = _unique(
        str(loss.get("trackDefinition") or "").strip()
        for loss in losses
        if str(loss.get("trackDefinition") or "").strip()
    )
    codes = _unique(loss.get("observationCode") for loss in losses)
    if definitions:
        summary = "；".join(definitions)
    elif losses:
        names = _unique(loss.get("observationName") or loss.get("observationCode") for loss in losses)
        summary = f"完整满足{'、'.join(names)}的赛道评分要求并形成证据闭环"
    else:
        summary = "达到对应赛道评分规则的满分要求"
    return {"summary": summary, "ruleReference": ",".join(codes) or None}


def _merge_full_score(current, losses):
    current = current if isinstance(current, dict) else {}
    generated = _full_score_from_losses(losses)
    return {
        "summary": str(current.get("summary") or generated["summary"]),
        "ruleReference": current.get("ruleReference") or generated["ruleReference"],
    }


def _evidence_from_losses(losses):
    return _unique(
        evidence
        for loss in losses
        for evidence in _as_strings(loss.get("acceptableEvidence"))
    )


def _priority(value, losses):
    normalized = str(value or "").upper()
    aliases = {"HIGH": "P0", "MEDIUM": "P1", "LOW": "P2"}
    if normalized in aliases:
        return aliases[normalized]
    if normalized in _PRIORITY_RANK:
        return normalized
    points = sum(float(row.get("points") or 0) for row in losses)
    return "P0" if points >= 5 else "P1" if points >= 2 else "P2"


def _task_id(prefix, root, action):
    seed = f"{root}|{_normalized_action(action)}".encode("utf-8")
    return f"task-{prefix}-{hashlib.sha256(seed).hexdigest()[:16]}"


def _normalized_action(value):
    return re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]+", "", str(value or "").lower())


def _first_text(source, *keys):
    for key in keys:
        value = source.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _as_strings(value):
    if value is None or value == "":
        return []
    values = value if isinstance(value, (list, tuple, set)) else [value]
    return [str(item).strip() for item in values if str(item).strip()]


def _unique(values):
    result = []
    seen = set()
    for value in values:
        if value is None or value == "" or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _valid_loss(row):
    return (
        isinstance(row, dict)
        and str(row.get("lossId") or "").strip()
        and float(row.get("points") or 0) > 0
    )


def _round1(value):
    return round(float(value or 0) + 1e-12, 1)

