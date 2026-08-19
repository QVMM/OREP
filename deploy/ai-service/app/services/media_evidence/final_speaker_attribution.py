"""Build the final, score-free speaker attribution from local 3D-Speaker evidence.

P0 policy (zero enrollment / zero manual correction):
1. Prefer explicit "我是 X 号选手" introductions when unambiguous.
2. Fill remaining contestant slots with top speaking-time clusters
   (plus light contestant-language boost), not default VISITOR.
3. Only mark VISITOR when residual clusters look external (short + external
   language / negligible airtime). Never dump every unanchored cluster as 外部人员.
"""

from __future__ import annotations

from collections import defaultdict
import re

from .speaker_attribution_contract import normalize_speaker_attribution
from .three_d_speaker_contract import normalize_three_d_speaker_result


_CHINESE_SLOTS = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4}
_INTRODUCTION = re.compile(
    r"(?:我是|我叫|本人是|这里是)\s*(?:第)?\s*([1234一二两三四])\s*(?:号)?\s*(?:选手|队员|成员|负责人)?"
)
_ASR_ONE_CORRECTION = re.compile(r"我是\s*医药选手")

# 队员语义（不要求报号）
_CONTESTANT_LANG = re.compile(
    r"我们团队|我们项目|参赛作品|参赛|我是本项目|我是本次|工程师|负责人|演示|"
    r"系统架构|请看|大屏|路演|接下来由我|下面由我|各位评委老师好|尊敬的各位"
)
# 外部/评委语义
_EXTERNAL_LANG = re.compile(
    r"请问|有个问题|评委想|老师想问|请先停|停一下|补充一下提问|谢谢回答|我插一句"
)


def _time_ms(value: dict, key: str) -> int:
    explicit = value.get(f"{key}Ms")
    if explicit is not None:
        return max(0, int(round(float(explicit))))
    return max(0, int(round(float(value.get(key) or 0) * 1000)))


def _segment_range(segment: dict) -> tuple[int, int]:
    start_ms = _time_ms(segment, "start")
    return start_ms, max(start_ms, _time_ms(segment, "end"))


def _overlap(start_ms: int, end_ms: int, turn: dict) -> int:
    return max(
        0,
        min(end_ms, int(turn["endMs"])) - max(start_ms, int(turn["startMs"])),
    )


def _rank_clusters(start_ms: int, end_ms: int, turns: list[dict]) -> list[tuple[int, str]]:
    totals: dict[str, int] = defaultdict(int)
    for turn in turns:
        overlap = _overlap(start_ms, end_ms, turn)
        if overlap:
            totals[str(turn["sourceClusterId"])] += overlap
    return sorted(((value, key) for key, value in totals.items()), key=lambda item: (-item[0], item[1]))


def _dominant_cluster(
    start_ms: int,
    end_ms: int,
    turns: list[dict],
    *,
    minimum_coverage: float,
    minimum_share: float,
    minimum_margin: float,
) -> tuple[str | None, float, list[str]]:
    ranked = _rank_clusters(start_ms, end_ms, turns)
    if not ranked:
        return None, 0.0, []
    duration = max(1, end_ms - start_ms)
    total = sum(item[0] for item in ranked)
    best_overlap, best_cluster = ranked[0]
    second_overlap = ranked[1][0] if len(ranked) > 1 else 0
    coverage = best_overlap / duration
    share = best_overlap / max(1, total)
    margin = (best_overlap - second_overlap) / max(1, total)
    candidates = [item[1] for item in ranked]
    if coverage < minimum_coverage or share < minimum_share or margin < minimum_margin:
        return None, round(coverage, 6), candidates
    return best_cluster, round(coverage, 6), candidates


def _introduction_slot(text: str, *, start_ms: int) -> tuple[int | None, bool]:
    match = _INTRODUCTION.search(str(text or ""))
    if match:
        token = match.group(1)
        return int(token) if token.isdigit() else _CHINESE_SLOTS[token], False
    # FunASR occasionally renders "一号选手" as "医药选手".
    if start_ms <= 300_000 and _ASR_ONE_CORRECTION.search(str(text or "")):
        return 1, True
    return None, False


def _clock(duration_ms: int, media_clock: dict | None) -> dict:
    if media_clock:
        return dict(media_clock)
    return {
        "clockId": "MEDIA_CLOCK",
        "timebase": "MILLISECONDS",
        "masterSource": "MEDIA_PTS",
        "durationMs": int(duration_ms),
        "syncStatus": "SYNCED",
        "maxObservedDriftMs": 0,
    }


def _cluster_airtime_ms(turns: list[dict]) -> dict[str, int]:
    totals: dict[str, int] = defaultdict(int)
    for turn in turns:
        cluster = str(turn["sourceClusterId"])
        totals[cluster] += max(0, int(turn["endMs"]) - int(turn["startMs"]))
    return dict(totals)


def _cluster_language_scores(
    asr_result: dict,
    turns: list[dict],
) -> tuple[dict[str, float], dict[str, float]]:
    """Accumulate contestant/external language scores per cluster via ASR×turn overlap."""
    contestant: dict[str, float] = defaultdict(float)
    external: dict[str, float] = defaultdict(float)
    for segment in (asr_result or {}).get("segments") or []:
        if not isinstance(segment, dict):
            continue
        text = str(segment.get("text") or "")
        if not text.strip():
            continue
        start_ms, end_ms = _segment_range(segment)
        c_hit = 1.0 if _CONTESTANT_LANG.search(text) else 0.0
        e_hit = 1.0 if _EXTERNAL_LANG.search(text) else 0.0
        if not c_hit and not e_hit:
            continue
        ranked = _rank_clusters(start_ms, end_ms, turns)
        if not ranked:
            continue
        # soft-assign language score to overlapping clusters by overlap weight
        total = sum(item[0] for item in ranked) or 1
        for overlap, cluster in ranked:
            weight = overlap / total
            if c_hit:
                contestant[cluster] += c_hit * weight
            if e_hit:
                external[cluster] += e_hit * weight
    return dict(contestant), dict(external)


def _auto_contestant_slots(
    *,
    clusters: list[str],
    airtime_ms: dict[str, int],
    contestant_lang: dict[str, float],
    external_lang: dict[str, float],
    intro_slots: dict[str, int],
    contestant_slots: int,
    duration_ms: int,
) -> tuple[dict[str, int], set[str], dict[str, str]]:
    """Return (cluster→slot, duration_promoted clusters, residual personType by cluster).

    residual types: VISITOR only when evidence looks external; else UNATTRIBUTED
    (encoded as personType OFFSCREEN for contract, frontend shows 未识别说话人).
    """
    slot_count = max(0, min(4, int(contestant_slots)))
    assigned: dict[str, int] = dict(intro_slots)
    used_slots = set(assigned.values())
    promoted: set[str] = set()

    # Ranking score: airtime + language boost − external penalty
    media = max(1, int(duration_ms))
    ranked: list[tuple[float, int, str]] = []
    for cluster in clusters:
        if cluster in assigned:
            continue
        air = int(airtime_ms.get(cluster) or 0)
        c_lang = float(contestant_lang.get(cluster) or 0.0)
        e_lang = float(external_lang.get(cluster) or 0.0)
        # Normalize airtime to 0–1 against media duration (cap 1)
        air_score = min(1.0, air / max(1.0, media * 0.15))  # 15% of video ≈ full air score
        score = air_score + 0.35 * min(c_lang, 3.0) / 3.0 - 0.45 * min(e_lang, 3.0) / 3.0
        # Strong external + short airtime: demote hard
        if e_lang >= 0.8 and air < max(4000, int(media * 0.03)):
            score -= 0.5
        ranked.append((score, air, cluster))
    ranked.sort(key=lambda item: (-item[0], -item[1], item[2]))

    # 短视频用更低绝对门槛；长视频用时长比例
    min_air_ms = max(600, int(media * 0.008))
    for score, air, cluster in ranked:
        if len(used_slots) >= slot_count:
            break
        e_lang = float(external_lang.get(cluster) or 0.0)
        c_lang = float(contestant_lang.get(cluster) or 0.0)
        # Skip obvious externals unless they dominate airtime
        if e_lang > c_lang + 0.3 and air < max(8000, int(media * 0.05)):
            continue
        if air < min_air_ms and c_lang < 0.5:
            continue
        if score < 0.08 and c_lang < 0.5:
            continue
        # assign smallest free slot 1..N
        for slot in range(1, slot_count + 1):
            if slot not in used_slots:
                assigned[cluster] = slot
                used_slots.add(slot)
                promoted.add(cluster)
                break

    residual_type: dict[str, str] = {}
    for cluster in clusters:
        if cluster in assigned:
            continue
        air = int(airtime_ms.get(cluster) or 0)
        e_lang = float(external_lang.get(cluster) or 0.0)
        c_lang = float(contestant_lang.get(cluster) or 0.0)
        # Strong external / negligible airtime → VISITOR; else OFFSCREEN (未识别，非外部)
        if e_lang >= 0.6 and e_lang >= c_lang:
            residual_type[cluster] = "VISITOR"
        elif air < max(800, int(media * 0.006)):
            residual_type[cluster] = "VISITOR"
        else:
            residual_type[cluster] = "OFFSCREEN"

    return assigned, promoted, residual_type


def build_final_speaker_attribution(
    *,
    session_id: str,
    duration_ms: int,
    revision: int,
    asr_result: dict,
    three_d_speaker_result: dict,
    contestant_slots: int,
    media_clock: dict | None = None,
) -> dict:
    """Map final joint A/V clusters to stable people without user enrollment."""

    if not str(session_id).strip():
        raise ValueError("EMPTY_SESSION_ID")
    if isinstance(revision, bool) or int(revision) < 1:
        raise ValueError("INVALID_ATTRIBUTION_REVISION")
    if isinstance(contestant_slots, bool) or not 0 <= int(contestant_slots) <= 4:
        raise ValueError("INVALID_CONTESTANT_SLOT_COUNT")

    provider = normalize_three_d_speaker_result(
        three_d_speaker_result or {}, duration_ms=int(duration_ms)
    )
    turns = provider["turns"]
    cluster_first_last: dict[str, list[int]] = {}
    for turn in turns:
        cluster = str(turn["sourceClusterId"])
        if cluster not in cluster_first_last:
            cluster_first_last[cluster] = [int(turn["startMs"]), int(turn["endMs"])]
        else:
            cluster_first_last[cluster][0] = min(cluster_first_last[cluster][0], int(turn["startMs"]))
            cluster_first_last[cluster][1] = max(cluster_first_last[cluster][1], int(turn["endMs"]))
    clusters = sorted(cluster_first_last, key=lambda key: (cluster_first_last[key][0], key))

    # --- Stage 1: explicit introduction anchors (when unambiguous) ---
    claims_by_cluster: dict[str, set[int]] = defaultdict(set)
    clusters_by_slot: dict[int, set[str]] = defaultdict(set)
    correction_count = 0
    for segment in (asr_result or {}).get("segments") or []:
        if not isinstance(segment, dict):
            continue
        start_ms, end_ms = _segment_range(segment)
        slot, corrected = _introduction_slot(str(segment.get("text") or ""), start_ms=start_ms)
        if slot is None or slot > int(contestant_slots):
            continue
        cluster, _, _ = _dominant_cluster(
            start_ms,
            end_ms,
            turns,
            minimum_coverage=0.5,
            minimum_share=0.6,
            minimum_margin=0.2,
        )
        if cluster is None:
            continue
        claims_by_cluster[cluster].add(slot)
        clusters_by_slot[slot].add(cluster)
        correction_count += int(corrected)

    intro_slots: dict[str, int] = {}
    conflicting_clusters: set[str] = set()
    for cluster, claimed_slots in claims_by_cluster.items():
        if len(claimed_slots) != 1:
            conflicting_clusters.add(cluster)
            continue
        slot = next(iter(claimed_slots))
        if len(clusters_by_slot[slot]) != 1:
            conflicting_clusters.update(clusters_by_slot[slot])
            continue
        intro_slots[cluster] = slot

    # --- Stage 2: fill slots by airtime + language (no enrollment) ---
    airtime_ms = _cluster_airtime_ms(turns)
    contestant_lang, external_lang = _cluster_language_scores(asr_result or {}, turns)
    assigned_slots, duration_promoted, residual_type = _auto_contestant_slots(
        clusters=clusters,
        airtime_ms=airtime_ms,
        contestant_lang=contestant_lang,
        external_lang=external_lang,
        intro_slots=intro_slots,
        contestant_slots=int(contestant_slots),
        duration_ms=int(duration_ms),
    )

    cluster_to_person: dict[str, str] = {}
    people: list[dict] = []
    for index, cluster in enumerate(clusters, start=1):
        person_id = f"PERSON_{index}"
        cluster_to_person[cluster] = person_id
        slot = assigned_slots.get(cluster)
        if slot is not None:
            person_type = "CONTESTANT"
            display_name = f"{slot}号选手"
            confidence = 0.9 if cluster in intro_slots else 0.78
        else:
            person_type = residual_type.get(cluster, "OFFSCREEN")
            # VISITOR only for residual external-like; OFFSCREEN = 未识别（前端不显示「外部人员」）
            display_name = None
            confidence = 0.55 if person_type == "VISITOR" else 0.6
        people.append(
            {
                "personId": person_id,
                "personType": person_type,
                "contestantSlot": slot,
                "displayName": display_name,
                "state": "STABLE",
                "confidence": confidence,
                "firstSeenMs": cluster_first_last[cluster][0],
                "lastSeenMs": cluster_first_last[cluster][1],
                "faceTrackIds": [],
                "bodyTrackIds": [],
                "voiceClusterIds": [cluster],
                "modelRevision": int(revision),
            }
        )

    contestant_clusters = {c for c, s in assigned_slots.items()}

    output_turns: list[dict] = []
    for index, turn in enumerate(turns, start=1):
        cluster = str(turn["sourceClusterId"])
        person_id = cluster_to_person[cluster]
        confirmed = cluster in intro_slots or cluster in contestant_clusters
        output_turns.append(
            {
                "turnId": f"TURN_{index}",
                "startMs": int(turn["startMs"]),
                "endMs": int(turn["endMs"]),
                "personId": person_id,
                "speakerState": "CONFIRMED" if cluster in intro_slots else (
                    "CONFIRMED" if cluster in duration_promoted else (
                        "PROVISIONAL" if confirmed else "PROVISIONAL"
                    )
                ),
                "confidence": 0.9 if cluster in intro_slots else (
                    0.78 if cluster in duration_promoted else 0.65
                ),
                "candidatePersonIds": [person_id],
                "sourceClusterId": cluster,
            }
        )

    output_segments: list[dict] = []
    attributed_count = 0
    unknown_count = 0
    for index, segment in enumerate((asr_result or {}).get("segments") or [], start=1):
        if not isinstance(segment, dict):
            continue
        text = str(segment.get("text") or "").strip()
        if not text:
            continue
        start_ms, end_ms = _segment_range(segment)
        cluster, coverage, candidate_clusters = _dominant_cluster(
            start_ms,
            end_ms,
            turns,
            minimum_coverage=0.6,
            minimum_share=0.6,
            minimum_margin=0.2,
        )
        candidate_people = [
            cluster_to_person[item]
            for item in candidate_clusters
            if item in cluster_to_person
        ]
        if cluster is None:
            person_id = None
            state = "UNKNOWN"
            confidence = 0.0
            unknown_count += 1
        else:
            person_id = cluster_to_person[cluster]
            if cluster in intro_slots:
                state = "CONFIRMED"
            elif cluster in duration_promoted or cluster in contestant_clusters:
                state = "CONFIRMED" if cluster in duration_promoted else "PROVISIONAL"
            else:
                state = "PROVISIONAL"
            confidence = coverage
            attributed_count += 1
        item = {
            "segmentId": f"SEG_{index}",
            "revision": int(revision),
            "startMs": start_ms,
            "endMs": end_ms,
            "text": text,
            "personId": person_id,
            "speakerState": state,
            "speakerConfidence": confidence,
            "candidatePersonIds": candidate_people,
            "isFinal": True,
            "source": str(segment.get("source") or (asr_result or {}).get("source") or "asr"),
        }
        # Persist acoustic cluster for DB speaker_label / later recompute.
        if cluster is not None:
            item["rawSpeakerId"] = cluster
            item["sourceClusterId"] = cluster
        if segment.get("confidence") is not None:
            item["asrConfidence"] = segment["confidence"]
        output_segments.append(item)

    segment_count = len(output_segments)
    contestant_count = sum(1 for p in people if p["personType"] == "CONTESTANT")
    visitor_count = sum(1 for p in people if p["personType"] == "VISITOR")
    unattributed_count = sum(1 for p in people if p["personType"] == "OFFSCREEN")
    result = {
        "contractVersion": "speaker-attribution-v1",
        "revision": int(revision),
        "status": "FINAL",
        "clock": _clock(int(duration_ms), media_clock),
        "people": people,
        "turns": output_turns,
        "segments": output_segments,
        "diagnostics": {
            "provider": provider["provider"],
            "providerStatus": provider["status"],
            "speakerClusterCount": len(clusters),
            "publishedPersonCount": len(people),
            "anchoredContestantCount": contestant_count,
            "introductionAnchoredCount": len(intro_slots),
            "durationPromotedCount": len(duration_promoted),
            "anonymousPersonCount": visitor_count + unattributed_count,
            "visitorPersonCount": visitor_count,
            "unattributedPersonCount": unattributed_count,
            "introductionConflictCount": len(conflicting_clusters),
            "introductionCorrectionCount": correction_count,
            "attributedSegmentCount": attributed_count,
            "unknownSegmentCount": unknown_count,
            "transcriptCoverageRatio": round(attributed_count / segment_count, 6) if segment_count else 0.0,
            "confidenceSemantics": "derived_temporal_alignment_not_model_score",
            "assignmentPolicy": "intro_then_top_airtime_language_no_enrollment",
        },
    }
    return normalize_speaker_attribution(result)
