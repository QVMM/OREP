"""Fuse local LR-ASD active faces with acoustic diarization turns."""

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy


def _visual_key(interval: dict) -> tuple[str, str]:
    visual_id = str(interval.get("visualIdentityId") or "").strip()
    if visual_id:
        return "VISUAL", visual_id
    return "FACE", str(interval["faceTrackId"])


def _overlap_ms(left: dict, right: dict) -> int:
    return max(
        0,
        min(int(left.get("endMs") or 0), int(right.get("endMs") or 0))
        - max(int(left.get("startMs") or 0), int(right.get("startMs") or 0)),
    )


def fuse_active_speaker_evidence(
    diarization_result: dict,
    active_speaker_result: dict | None,
    *,
    minimum_active_probability: float = 0.65,
    minimum_visible_probability: float = 0.60,
    minimum_temporal_coverage: float = 0.35,
    minimum_winner_dominance: float = 0.70,
    minimum_identity_confidence: float = 0.0,
    minimum_cluster_vote_dominance: float = 0.70,
    minimum_cluster_supporting_turns: int = 1,
    minimum_cluster_support_ms: int = 0,
) -> dict:
    """Return acoustic turns refined only by sufficiently strong AV evidence."""

    base = deepcopy(diarization_result or {})
    av = active_speaker_result if isinstance(active_speaker_result, dict) else {}
    av_status = str(av.get("status") or "unavailable")
    if av_status not in {"completed", "partial"}:
        base["audioVisualStatus"] = av_status if av_status in {"failed", "unavailable"} else "unavailable"
        base["activeSpeakerSource"] = av.get("source", "local_lr_asd")
        return base

    intervals = [
        item
        for item in (av.get("activeIntervals") or [])
        if isinstance(item, dict)
        and float(item.get("activeProbability") or 0) >= minimum_active_probability
        and float(item.get("visibleProbability") or 0) >= minimum_visible_probability
        and int(item.get("endMs") or 0) > int(item.get("startMs") or 0)
        and str(item.get("faceTrackId") or "").strip()
    ]
    turns = [deepcopy(item) for item in (base.get("turns") or []) if isinstance(item, dict)]
    direct_matches: list[dict | None] = []
    cluster_votes: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    cluster_support_ms: dict[str, dict[str, int]] = defaultdict(
        lambda: defaultdict(int)
    )
    cluster_supporting_turns: dict[str, dict[str, int]] = defaultdict(
        lambda: defaultdict(int)
    )
    cluster_supported_turn_duration_ms: dict[str, dict[str, int]] = defaultdict(
        lambda: defaultdict(int)
    )

    for turn in turns:
        duration_ms = max(1, int(turn.get("endMs") or 0) - int(turn.get("startMs") or 0))
        overlap_by_identity: dict[tuple[str, str], int] = defaultdict(int)
        weight_by_identity: dict[tuple[str, str], float] = defaultdict(float)
        face_weight_by_identity: dict[tuple[str, str], dict[str, float]] = defaultdict(
            lambda: defaultdict(float)
        )
        for interval in intervals:
            overlap = _overlap_ms(turn, interval)
            if not overlap:
                continue
            identity_key = _visual_key(interval)
            face_id = str(interval["faceTrackId"])
            weight = overlap * float(interval["activeProbability"]) * float(
                interval["visibleProbability"]
            )
            overlap_by_identity[identity_key] += overlap
            weight_by_identity[identity_key] += weight
            face_weight_by_identity[identity_key][face_id] += weight
        ranked = sorted(
            weight_by_identity.items(), key=lambda item: (-item[1], item[0])
        )
        match = None
        if ranked:
            winner_identity, winner_weight = ranked[0]
            total_weight = sum(weight_by_identity.values())
            coverage = overlap_by_identity[winner_identity] / duration_ms
            dominance = winner_weight / max(1.0, total_weight)
            confidence = winner_weight / duration_ms
            if (
                coverage >= minimum_temporal_coverage
                and dominance >= minimum_winner_dominance
                and confidence >= minimum_identity_confidence
            ):
                representative_face = sorted(
                    face_weight_by_identity[winner_identity].items(),
                    key=lambda item: (-item[1], item[0]),
                )[0][0]
                match = {
                    "identityKey": winner_identity,
                    "faceTrackId": representative_face,
                    "visualIdentityId": (
                        winner_identity[1]
                        if winner_identity[0] == "VISUAL"
                        else None
                    ),
                    "confidence": round(max(0.0, min(1.0, confidence)), 6),
                    "coverage": round(max(0.0, min(1.0, coverage)), 6),
                    "dominance": round(max(0.0, min(1.0, dominance)), 6),
                    "support": winner_weight,
                }
                cluster_id = str(turn.get("rawSpeakerId") or "").strip()
                if cluster_id:
                    cluster_votes[cluster_id][winner_identity] += winner_weight
                    cluster_support_ms[cluster_id][winner_identity] += overlap_by_identity[
                        winner_identity
                    ]
                    cluster_supporting_turns[cluster_id][winner_identity] += 1
                    cluster_supported_turn_duration_ms[cluster_id][
                        winner_identity
                    ] += duration_ms
        direct_matches.append(match)

    cluster_to_identity: dict[str, tuple[str, str]] = {}
    cluster_confidence: dict[str, float] = {}
    for cluster_id, votes in cluster_votes.items():
        ranked = sorted(votes.items(), key=lambda item: (-item[1], item[0]))
        winner_identity, winner_weight = ranked[0]
        dominance = winner_weight / max(1.0, sum(votes.values()))
        support_turn_count = cluster_supporting_turns[cluster_id][winner_identity]
        support_ms = cluster_support_ms[cluster_id][winner_identity]
        if (
            dominance >= minimum_cluster_vote_dominance
            and support_turn_count >= max(1, int(minimum_cluster_supporting_turns))
            and support_ms >= max(0, int(minimum_cluster_support_ms))
        ):
            cluster_to_identity[cluster_id] = winner_identity
            absolute_evidence_quality = winner_weight / max(
                1,
                cluster_supported_turn_duration_ms[cluster_id][winner_identity],
            )
            cluster_confidence[cluster_id] = round(
                max(0.0, min(1.0, dominance * absolute_evidence_quality)), 6
            )

    identity_first_seen: dict[str, int] = {}
    identity_keys = []
    for turn in turns:
        acoustic_id = str(turn.get("rawSpeakerId") or "UNKNOWN")
        visual_identity = cluster_to_identity.get(acoustic_id)
        identity_key = (
            f"{visual_identity[0]}:{visual_identity[1]}"
            if visual_identity
            else f"AUDIO:{acoustic_id}"
        )
        if identity_key not in identity_first_seen:
            identity_first_seen[identity_key] = int(turn.get("startMs") or 0)
            identity_keys.append(identity_key)
    identity_keys.sort(key=lambda key: (identity_first_seen[key], key))
    identity_to_speaker = {
        identity_key: f"SPEAKER_{index}" for index, identity_key in enumerate(identity_keys)
    }

    direct_candidate_count = sum(match is not None for match in direct_matches)
    direct_verified_count = 0
    inherited_verified_count = 0
    rejected_candidate_count = 0
    for turn, direct in zip(turns, direct_matches):
        acoustic_id = str(turn.get("rawSpeakerId") or "UNKNOWN")
        visual_identity = cluster_to_identity.get(acoustic_id)
        identity_key = (
            f"{visual_identity[0]}:{visual_identity[1]}"
            if visual_identity
            else f"AUDIO:{acoustic_id}"
        )
        turn["rawSpeakerId"] = identity_to_speaker[identity_key]
        if visual_identity:
            turn["activeSpeakerSource"] = av.get("source", "local_lr_asd")
            if visual_identity[0] == "VISUAL":
                turn["visualIdentityId"] = visual_identity[1]
            if direct and direct["identityKey"] == visual_identity:
                direct_verified_count += 1
                turn["faceTrackId"] = direct["faceTrackId"]
                turn["speakerVerification"] = "AUDIO_VISUAL"
                turn["identityConfidence"] = direct["confidence"]
                turn["activeSpeakerCoverage"] = direct["coverage"]
                turn["activeSpeakerDominance"] = direct["dominance"]
            else:
                inherited_verified_count += 1
                if visual_identity[0] == "FACE":
                    turn["faceTrackId"] = visual_identity[1]
                turn["speakerVerification"] = "AUDIO_INHERITED"
                turn["identityConfidence"] = cluster_confidence[acoustic_id]
        else:
            turn["speakerVerification"] = "AUDIO_ONLY"
        if direct and direct["identityKey"] != visual_identity:
            rejected_candidate_count += 1

    original_clusters = {
        str(item.get("rawSpeakerId") or "")
        for item in (diarization_result or {}).get("turns") or []
        if isinstance(item, dict) and item.get("rawSpeakerId") is not None
    }
    speakers = [identity_to_speaker[key] for key in identity_keys]
    base["turns"] = turns
    base["speakers"] = speakers
    base["detectedSpeakerCount"] = len(speakers)
    verified_count = direct_verified_count + inherited_verified_count
    base["audioVisualVerifiedTurnCount"] = verified_count
    base["audioVisualDirectCandidateTurnCount"] = direct_candidate_count
    base["audioVisualDirectTurnCount"] = direct_verified_count
    base["audioVisualInheritedTurnCount"] = inherited_verified_count
    base["audioVisualRejectedCandidateTurnCount"] = rejected_candidate_count
    base["audioVisualStatus"] = (
        "completed" if turns and verified_count == len(turns) else "partial"
    )
    base["activeSpeakerSource"] = av.get("source", "local_lr_asd")
    base["source"] = f"{base.get('source', 'local_diarization')}+local_lr_asd"
    base["mergedAcousticClusterCount"] = max(0, len(original_clusters) - len(speakers))
    base["faceIdentityCount"] = len(set(cluster_to_identity.values()))
    return base
