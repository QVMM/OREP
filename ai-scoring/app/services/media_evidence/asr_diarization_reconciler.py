"""Merge cloud ASR text with local speaker turns using time overlap only."""

from __future__ import annotations

from collections import defaultdict


def _time_ms(segment: dict, key: str) -> int:
    ms_key = f"{key}Ms"
    if segment.get(ms_key) is not None:
        return int(round(float(segment[ms_key])))
    return int(round(float(segment.get(key) or 0) * 1000))


def _overlap_ms(start_ms: int, end_ms: int, turn: dict) -> int:
    return max(0, min(end_ms, int(turn.get("endMs") or 0)) - max(start_ms, int(turn.get("startMs") or 0)))


def _display_name(raw_speaker_id: str | None) -> str:
    if raw_speaker_id is None:
        return "发言人待确认"
    try:
        return f"{int(raw_speaker_id.rsplit('_', 1)[1]) + 1}号发言人"
    except (IndexError, ValueError):
        return raw_speaker_id


def reconcile_asr_with_diarization(
    asr_result: dict,
    diarization_result: dict,
    *,
    minimum_coverage: float = 0.35,
    minimum_dominance: float = 0.60,
) -> dict:
    turns = [turn for turn in (diarization_result or {}).get("turns") or [] if isinstance(turn, dict)]
    output_segments = []
    resolved_speakers = set()
    unresolved_count = 0
    overlap_count = 0

    for index, original in enumerate((asr_result or {}).get("segments") or [], start=1):
        segment = dict(original)
        start_ms = _time_ms(segment, "start")
        end_ms = max(start_ms, _time_ms(segment, "end"))
        duration_ms = max(1, end_ms - start_ms)
        overlap_by_speaker = defaultdict(int)
        for turn in turns:
            raw_speaker = str(turn.get("rawSpeakerId") or "").strip()
            if raw_speaker:
                overlap_by_speaker[raw_speaker] += _overlap_ms(start_ms, end_ms, turn)
        ranked = sorted(overlap_by_speaker.items(), key=lambda item: (-item[1], item[0]))
        winner = None
        speaker_state = "UNKNOWN"
        candidates = [item[0] for item in ranked if item[1] > 0]
        winner_overlap = ranked[0][1] if ranked else 0
        coverage = winner_overlap / duration_ms
        if ranked and coverage >= minimum_coverage:
            second_overlap = ranked[1][1] if len(ranked) > 1 else 0
            dominance = winner_overlap / max(1, winner_overlap + second_overlap)
            if second_overlap and dominance < minimum_dominance:
                speaker_state = "OVERLAP"
                overlap_count += 1
            else:
                winner = ranked[0][0]
                speaker_state = "IDENTIFIED_CLUSTER"
                resolved_speakers.add(winner)
        else:
            unresolved_count += 1

        segment["segmentNo"] = int(segment.get("segmentNo") or index)
        segment["startMs"] = start_ms
        segment["endMs"] = end_ms
        segment["speaker"] = winner
        segment["rawSpeakerId"] = winner
        segment["displaySpeaker"] = _display_name(winner)
        segment["speakerState"] = speaker_state
        segment["speakerCandidates"] = candidates if speaker_state == "OVERLAP" else []
        segment["diarizationOverlapMs"] = winner_overlap
        segment["diarizationCoverage"] = round(coverage, 4)
        segment["diarizationSource"] = (diarization_result or {}).get("source", "local_diarization")
        if winner:
            winner_turns = [
                turn
                for turn in turns
                if str(turn.get("rawSpeakerId") or "") == winner
                and _overlap_ms(start_ms, end_ms, turn) > 0
            ]
            if winner_turns:
                winner_turn = max(
                    winner_turns,
                    key=lambda turn: (
                        _overlap_ms(start_ms, end_ms, turn),
                        -int(turn.get("startMs") or 0),
                    ),
                )
                for key in (
                    "sourceClusterId",
                    "faceTrackId",
                    "speakerVerification",
                    "identityConfidence",
                    "activeSpeakerCoverage",
                    "activeSpeakerDominance",
                    "activeSpeakerSource",
                ):
                    if winner_turn.get(key) is not None:
                        segment[key] = winner_turn[key]
        output_segments.append(segment)

    if output_segments and len(resolved_speakers) and not unresolved_count and not overlap_count:
        status = "completed"
    elif resolved_speakers or overlap_count:
        status = "partial"
    else:
        status = "evidence_incomplete"

    result = dict(asr_result or {})
    result["segments"] = output_segments
    result["speakers"] = sorted(resolved_speakers)
    result["detectedSpeakerCount"] = len(resolved_speakers)
    result["unresolvedSegmentCount"] = unresolved_count
    result["overlapSegmentCount"] = overlap_count
    result["diarizationStatus"] = status
    result["diarizationSource"] = (diarization_result or {}).get("source", "local_diarization")
    result["diarizationTurns"] = turns
    for key in (
        "audioVisualStatus",
        "activeSpeakerSource",
        "activeSpeakerFailureCode",
        "audioVisualVerifiedTurnCount",
        "audioVisualDirectCandidateTurnCount",
        "audioVisualDirectTurnCount",
        "audioVisualInheritedTurnCount",
        "audioVisualRejectedCandidateTurnCount",
        "mergedAcousticClusterCount",
        "faceIdentityCount",
    ):
        if (diarization_result or {}).get(key) is not None:
            result[key] = diarization_result[key]
    return result
