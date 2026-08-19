"""Build and atomically persist safe speaker-attribution shadow snapshots."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
from uuid import uuid4

from .session_identity_graph import SessionIdentityGraph
from .session_identity_graph import ObservationRef
from .speaker_attribution_contract import normalize_speaker_attribution
from .transcript_attributor import attribute_transcript


def _cluster_ids(diarization_result: dict) -> list[str]:
    return sorted(
        {
            str(item.get("sourceClusterId") or item.get("rawSpeakerId") or "").strip()
            for item in (diarization_result or {}).get("turns") or []
            if isinstance(item, dict)
            and str(item.get("rawSpeakerId") or item.get("sourceClusterId") or "").strip()
        }
    )


def build_shadow_attribution(
    *,
    session_id: str,
    duration_ms: int,
    contestant_slots: int,
    asr_result: dict,
    diarization_result: dict,
    active_speaker_result: dict | None,
    media_clock: dict | None = None,
    revision: int = 1,
) -> dict:
    """Create a conservative snapshot from stable audio-visual identities.

    Acoustic clusters are never people.  A contestant is materialized only
    after the visual registrar marks an identity stable; several acoustic
    clusters may then become voice aliases of that one person.
    """

    slot_count = max(0, min(4, int(contestant_slots)))
    graph = SessionIdentityGraph(session_id=str(session_id), contestant_slots=0)
    av = active_speaker_result if isinstance(active_speaker_result, dict) else {}
    tracks = [
        item for item in (av.get("faceTracks") or []) if isinstance(item, dict)
    ]
    tracks_by_visual: dict[str, list[dict]] = {}
    for track in tracks:
        visual_id = str(track.get("visualIdentityId") or "").strip()
        if visual_id:
            tracks_by_visual.setdefault(visual_id, []).append(track)

    stable_visuals = [
        item
        for item in (av.get("visualIdentities") or [])
        if isinstance(item, dict)
        and str(item.get("registrationState") or "").upper() == "STABLE"
        and str(item.get("visualIdentityId") or "").strip()
    ]

    def horizontal_anchor(identity: dict) -> float:
        identity_tracks = tracks_by_visual.get(
            str(identity.get("visualIdentityId") or ""), []
        )
        weighted = [
            (
                float(track.get("meanCenterX")),
                max(1, int(track.get("detectionCount") or 1)),
            )
            for track in identity_tracks
            if track.get("meanCenterX") is not None
        ]
        if not weighted:
            return 2.0
        return sum(value * weight for value, weight in weighted) / sum(
            weight for _, weight in weighted
        )

    stable_visuals.sort(
        key=lambda item: (
            horizontal_anchor(item),
            int(item.get("firstSeenMs") or 0),
            str(item.get("visualIdentityId") or ""),
        )
    )
    # Four expected contestants is a validation target, never a clustering
    # instruction.  If the registrar still has more or fewer stable identities,
    # keep every segment unknown instead of publishing the first four by chance.
    contestant_visuals = (
        stable_visuals if len(stable_visuals) == slot_count else []
    )
    person_by_visual: dict[str, str] = {}
    confidence_by_visual: dict[str, float] = {}
    for slot, identity in enumerate(contestant_visuals, start=1):
        visual_id = str(identity["visualIdentityId"])
        person = graph.create_person(
            "CONTESTANT",
            contestant_slot=slot,
            first_seen_ms=max(0, int(identity.get("firstSeenMs") or 0)),
        )
        confidence = max(
            0.0,
            min(1.0, float(identity.get("confidence") or 0.0)),
        )
        person.state = "STABLE"
        person.confidence = confidence
        person.last_seen_ms = max(
            person.first_seen_ms,
            int(identity.get("lastSeenMs") or person.first_seen_ms),
        )
        for track in tracks_by_visual.get(visual_id, []):
            face_id = str(track.get("faceTrackId") or "").strip()
            if not face_id:
                continue
            track_start = max(0, int(track.get("startMs") or 0))
            track_end = max(track_start, int(track.get("endMs") or track_start))
            graph.attach_observation(
                person.person_id,
                ObservationRef(
                    "FACE",
                    face_id,
                    track_start,
                    track_end,
                    max(
                        0.0,
                        min(
                            1.0,
                            float(track.get("visibleProbability") or confidence),
                        ),
                    ),
                ),
            )
        person_by_visual[visual_id] = person.person_id
        confidence_by_visual[visual_id] = confidence

    turns = []
    for index, raw in enumerate((diarization_result or {}).get("turns") or [], start=1):
        if not isinstance(raw, dict):
            continue
        start_ms = max(0, int(raw.get("startMs") or 0))
        end_ms = max(start_ms, int(raw.get("endMs") or start_ms))
        visual_id = str(raw.get("visualIdentityId") or "").strip()
        person_id = person_by_visual.get(visual_id)
        verification = str(raw.get("speakerVerification") or "AUDIO_ONLY").upper()
        raw_confidence = raw.get("identityConfidence")
        confidence = max(
            0.0,
            min(
                1.0,
                float(raw_confidence)
                if raw_confidence is not None
                else confidence_by_visual.get(visual_id, 0.0),
            ),
        )
        if person_id and (
            (verification == "AUDIO_VISUAL" and confidence >= 0.60)
            or (verification == "AUDIO_INHERITED" and confidence >= 0.70)
        ):
            speaker_state = "CONFIRMED" if confidence >= 0.85 else "PROVISIONAL"
            candidate_ids = [person_id]
            cluster_id = str(
                raw.get("sourceClusterId") or raw.get("rawSpeakerId") or ""
            ).strip()
            if cluster_id:
                graph.attach_observation(
                    person_id,
                    ObservationRef(
                        "VOICE", cluster_id, start_ms, end_ms, confidence
                    ),
                )
        else:
            person_id = None
            speaker_state = "UNKNOWN"
            candidate_ids = (
                [person_by_visual[visual_id]]
                if visual_id in person_by_visual
                else []
            )
            confidence = 0.0
        turns.append(
            {
                "turnId": f"TURN_{index}",
                "startMs": start_ms,
                "endMs": end_ms,
                "personId": person_id,
                "speakerState": speaker_state,
                "confidence": confidence,
                "candidatePersonIds": candidate_ids,
                "sourceClusterId": str(
                    raw.get("sourceClusterId") or raw.get("rawSpeakerId") or ""
                ),
                "sourceVisualIdentityId": str(
                    raw.get("visualIdentityId") or ""
                )
                or None,
                "speakerVerification": verification,
            }
        )
    normalized_revision = max(1, int(revision))
    segments = attribute_transcript(
        asr_result or {}, turns, revision=normalized_revision, is_final=True
    )
    requested_clock = media_clock if isinstance(media_clock, dict) else {}
    clock = {
        "clockId": str(requested_clock.get("clockId") or f"session-{session_id}"),
        "timebase": "MILLISECONDS",
        "masterSource": str(
            requested_clock.get("masterSource") or "MEDIA_PTS"
        ).upper(),
        "durationMs": max(0, int(duration_ms)),
        "syncStatus": str(
            requested_clock.get("syncStatus") or "UNAVAILABLE"
        ).upper(),
        "maxObservedDriftMs": max(
            0, int(requested_clock.get("maxObservedDriftMs") or 0)
        ),
    }
    base = graph.snapshot(
        revision=normalized_revision,
        status="FINAL",
        clock=clock,
    )
    base["turns"] = turns
    base["segments"] = segments
    base["diagnostics"] = {
        "mode": "EVIDENCE_GATED_GLOBAL_PEOPLE",
        "acousticClusterCount": len(_cluster_ids(diarization_result or {})),
        "faceTrackCount": len(
            [item for item in (av.get("faceTracks") or []) if isinstance(item, dict)]
        ),
        "activeIntervalCount": len(
            [item for item in (av.get("activeIntervals") or []) if isinstance(item, dict)]
        ),
        "visualIdentityCount": len(
            [item for item in (av.get("visualIdentities") or []) if isinstance(item, dict)]
        ),
        "stableVisualIdentityCount": len(stable_visuals),
        "publishedPersonCount": len(contestant_visuals),
        "audioVisualVerifiedTurnCount": int(
            (diarization_result or {}).get("audioVisualVerifiedTurnCount") or 0
        ),
        "promotionBlockedReason": (
            None if person_by_visual else "NO_STABLE_VISUAL_IDENTITY"
        ),
    }
    return normalize_speaker_attribution(base)


def save_shadow_attribution(upload_dir: str, session_id: str, snapshot: dict) -> dict:
    """Persist one deterministic revision under a private local result directory."""

    normalized = normalize_speaker_attribution(snapshot)
    canonical = json.dumps(
        normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    snapshot_hash = "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    safe_id = re.sub(r"[^A-Za-z0-9_.-]", "_", str(session_id))[:160]
    result_dir = Path(upload_dir) / "results" / "speaker-attribution" / safe_id
    result_dir.mkdir(parents=True, exist_ok=True)
    final_path = result_dir / f"revision-{normalized['revision']}.json"
    temporary_path = result_dir / f".{final_path.name}.{uuid4().hex}.tmp"
    try:
        with temporary_path.open("w", encoding="utf-8") as handle:
            handle.write(canonical)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, final_path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise
    return {
        "path": str(final_path),
        "snapshotHash": snapshot_hash,
        "revision": normalized["revision"],
        "status": normalized["status"],
    }
