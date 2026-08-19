"""Evidence-gated registration of fragmented face tracks across one session.

This module only creates session-global *visual identities*. A visual identity is
still evidence, not a contestant/person assignment. Raw biometric vectors must
remain inside the isolated model worker and are never returned by this module.
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Iterable


def _probability(value, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(number):
        return default
    return max(0.0, min(1.0, number))


def _canonical_pair(left: str, right: str) -> tuple[str, str]:
    return (left, right) if left < right else (right, left)


def register_global_visual_identities(
    face_tracks: list[dict],
    similarity_links: list[dict],
    *,
    co_visible_pairs: Iterable[tuple[str, str]],
    minimum_similarity: float = 0.80,
    stable_similarity: float = 0.80,
    minimum_detection_count: int = 3,
    minimum_visible_probability: float = 0.60,
    anchor_track_ids: list[str] | None = None,
) -> dict:
    """Merge strong non-conflicting track fragments into visual identities.

    Links are consumed from strongest to weakest. Before every union, all pairs
    across the two candidate components are checked against the co-visibility
    veto set. This makes the veto transitive and prevents one bridging fragment
    from collapsing two people who were visibly present at the same time.
    """

    tracks: dict[str, dict] = {}
    for raw in face_tracks or []:
        if not isinstance(raw, dict):
            continue
        face_id = str(raw.get("faceTrackId") or "").strip()
        if not face_id or face_id in tracks:
            continue
        start_ms = max(0, int(raw.get("startMs") or 0))
        end_ms = max(start_ms, int(raw.get("endMs") or start_ms))
        tracks[face_id] = {
            "faceTrackId": face_id,
            "startMs": start_ms,
            "endMs": end_ms,
            "detectionCount": max(0, int(raw.get("detectionCount") or 0)),
            "visibleProbability": _probability(raw.get("visibleProbability")),
        }

    minimum_similarity = _probability(minimum_similarity, 0.80)
    stable_similarity = max(
        minimum_similarity, _probability(stable_similarity, 0.80)
    )
    minimum_detection_count = max(1, int(minimum_detection_count))
    minimum_visible_probability = _probability(
        minimum_visible_probability, 0.60
    )
    eligible = {
        face_id
        for face_id, track in tracks.items()
        if track["detectionCount"] >= minimum_detection_count
        and track["visibleProbability"] >= minimum_visible_probability
    }
    conflicts = {
        _canonical_pair(str(left), str(right))
        for left, right in co_visible_pairs
        if str(left) in tracks and str(right) in tracks and str(left) != str(right)
    }

    parent = {face_id: face_id for face_id in eligible}
    members = {face_id: {face_id} for face_id in eligible}
    accepted_edges: list[tuple[str, str, float]] = []

    def find(face_id: str) -> str:
        root = face_id
        while parent[root] != root:
            root = parent[root]
        while parent[face_id] != face_id:
            next_id = parent[face_id]
            parent[face_id] = root
            face_id = next_id
        return root

    links = []
    for raw in similarity_links or []:
        if not isinstance(raw, dict):
            continue
        left = str(raw.get("leftFaceTrackId") or "").strip()
        right = str(raw.get("rightFaceTrackId") or "").strip()
        similarity = _probability(raw.get("similarity"), -1.0)
        if (
            left in eligible
            and right in eligible
            and left != right
            and similarity >= minimum_similarity
        ):
            pair = _canonical_pair(left, right)
            links.append((pair[0], pair[1], similarity))
    links.sort(key=lambda item: (-item[2], item[0], item[1]))

    anchor_ids = list(dict.fromkeys(str(item) for item in (anchor_track_ids or [])))
    anchors_are_valid = bool(anchor_ids) and all(item in eligible for item in anchor_ids)
    anchors_are_mutually_visible = anchors_are_valid and all(
        _canonical_pair(left, right) in conflicts
        for index, left in enumerate(anchor_ids)
        for right in anchor_ids[index + 1 :]
    )
    if anchors_are_mutually_visible:
        similarities = {
            _canonical_pair(left, right): similarity
            for left, right, similarity in links
        }
        groups = {anchor: {anchor} for anchor in anchor_ids}
        accepted_by_anchor: dict[str, list[float]] = {
            anchor: [] for anchor in anchor_ids
        }
        remaining = set(eligible) - set(anchor_ids)

        def compatible(candidate: str, anchor: str) -> bool:
            return not any(
                _canonical_pair(candidate, member) in conflicts
                for member in groups[anchor]
            )

        while remaining:
            proposals = []
            for candidate in sorted(remaining):
                scored = []
                for anchor in anchor_ids:
                    if not compatible(candidate, anchor):
                        continue
                    score = max(
                        (
                            similarities.get(_canonical_pair(candidate, member), -1.0)
                            for member in groups[anchor]
                        ),
                        default=-1.0,
                    )
                    if score >= minimum_similarity:
                        scored.append((score, anchor))
                scored.sort(key=lambda item: (-item[0], item[1]))
                if not scored:
                    continue
                best_score, best_anchor = scored[0]
                margin = (
                    best_score - scored[1][0]
                    if len(scored) > 1
                    else 1.0
                )
                proposals.append((margin, best_score, candidate, best_anchor))
            if not proposals:
                break
            # Resolve the least ambiguous fragment first. Its co-visible peers
            # then become incompatible with that identity before they are read.
            _, score, candidate, anchor = max(
                proposals, key=lambda item: (item[0], item[1], item[2], item[3])
            )
            groups[anchor].add(candidate)
            accepted_by_anchor[anchor].append(score)
            remaining.remove(candidate)

        identities = []
        assignments = []
        for index, anchor in enumerate(anchor_ids, start=1):
            group = groups[anchor]
            face_ids = sorted(group)
            confidence = (
                min(accepted_by_anchor[anchor])
                if accepted_by_anchor[anchor]
                else tracks[anchor]["visibleProbability"]
            )
            visual_id = f"VISUAL_{index}"
            identities.append(
                {
                    "visualIdentityId": visual_id,
                    "faceTrackIds": face_ids,
                    "firstSeenMs": min(tracks[item]["startMs"] for item in group),
                    "lastSeenMs": max(tracks[item]["endMs"] for item in group),
                    "registrationState": "STABLE",
                    "confidence": round(_probability(confidence), 6),
                }
            )
            assignments.extend(
                {
                    "faceTrackId": face_id,
                    "visualIdentityId": visual_id,
                    "registrationState": "STABLE",
                }
                for face_id in face_ids
            )
        assignments.extend(
            {
                "faceTrackId": face_id,
                "visualIdentityId": None,
                "registrationState": "UNRESOLVED",
                "reason": (
                    "OPEN_SET_NO_IDENTITY_MATCH"
                    if face_id in eligible
                    else "INSUFFICIENT_TRACK_QUALITY"
                ),
            }
            for face_id in tracks
            if face_id not in eligible or face_id in remaining
        )
        assignments.sort(key=lambda item: item["faceTrackId"])
        return {
            "identities": identities,
            "trackAssignments": assignments,
            "diagnostics": {
                "mode": "CO_VISIBLE_ANCHORED_OPEN_SET",
                "sourceTrackCount": len(tracks),
                "eligibleTrackCount": len(eligible),
                "globalVisualIdentityCount": len(identities),
                "acceptedLinkCount": sum(len(items) for items in accepted_by_anchor.values()),
                "rejectedCoVisibleLinkCount": 0,
                "unresolvedTrackCount": len(tracks) - sum(len(group) for group in groups.values()),
                "anchorTrackIds": anchor_ids,
                "openSetUnmatchedTrackCount": len(remaining),
            },
        }

    rejected_co_visible = 0
    for left, right, similarity in links:
        left_root, right_root = find(left), find(right)
        if left_root == right_root:
            continue
        left_members, right_members = members[left_root], members[right_root]
        if any(
            _canonical_pair(left_id, right_id) in conflicts
            for left_id in left_members
            for right_id in right_members
        ):
            rejected_co_visible += 1
            continue
        # The lexicographically smaller root keeps deterministic parentage.
        target, source = sorted((left_root, right_root))
        parent[source] = target
        members[target] = members[target] | members[source]
        del members[source]
        accepted_edges.append((left, right, similarity))

    components: dict[str, set[str]] = defaultdict(set)
    for face_id in sorted(eligible):
        components[find(face_id)].add(face_id)
    ordered_components = sorted(
        components.values(),
        key=lambda group: (
            min(tracks[face_id]["startMs"] for face_id in group),
            sorted(group),
        ),
    )

    identities = []
    assignment_by_track: dict[str, dict] = {}
    for index, group in enumerate(ordered_components, start=1):
        face_ids = sorted(group)
        visual_id = f"VISUAL_{index}"
        group_edges = [
            similarity
            for left, right, similarity in accepted_edges
            if left in group and right in group
        ]
        confidence = min(group_edges) if group_edges else 0.0
        state = (
            "STABLE"
            if len(group) > 1 and confidence >= stable_similarity
            else "CANDIDATE"
        )
        identities.append(
            {
                "visualIdentityId": visual_id,
                "faceTrackIds": face_ids,
                "firstSeenMs": min(tracks[item]["startMs"] for item in group),
                "lastSeenMs": max(tracks[item]["endMs"] for item in group),
                "registrationState": state,
                "confidence": round(confidence, 6),
            }
        )
        for face_id in face_ids:
            assignment_by_track[face_id] = {
                "faceTrackId": face_id,
                "visualIdentityId": visual_id,
                "registrationState": state,
            }

    for face_id in tracks:
        if face_id not in eligible:
            assignment_by_track[face_id] = {
                "faceTrackId": face_id,
                "visualIdentityId": None,
                "registrationState": "UNRESOLVED",
                "reason": "INSUFFICIENT_TRACK_QUALITY",
            }

    assignments = sorted(
        assignment_by_track.values(), key=lambda item: item["faceTrackId"]
    )
    return {
        "identities": identities,
        "trackAssignments": assignments,
        "diagnostics": {
            "sourceTrackCount": len(tracks),
            "eligibleTrackCount": len(eligible),
            "globalVisualIdentityCount": len(identities),
            "acceptedLinkCount": len(accepted_edges),
            "rejectedCoVisibleLinkCount": rejected_co_visible,
            "unresolvedTrackCount": len(tracks) - len(eligible),
        },
    }
