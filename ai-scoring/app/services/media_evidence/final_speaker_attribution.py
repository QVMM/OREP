"""Build the final, score-free speaker attribution from local 3D-Speaker evidence.

P0 policy (zero enrollment / zero manual correction):
1. Prefer explicit "我是 X 号选手" introductions when unambiguous.
2. Fill remaining contestant slots with top speaking-time clusters
   (plus light contestant-language boost), not default VISITOR.
3. Only mark VISITOR when residual clusters look external (short + external
   language / negligible airtime). Never dump every unanchored cluster as 外部人员.

P1 accuracy upgrades (still zero enrollment):
4. Multi-intro in one ASR line: split by character-time so 1–4 号 don't collapse.
5. Collapsed diarization (one SPEAKER_* for whole show): use intro/handoff timeline
   to separate contestants instead of one person owning all transcript.
6. Handoff phrases ("下面请二号选手") as soft slot anchors.
7. Soft segment dominance (high share / coverage) to cut UNKNOWN false negatives.
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
# FunASR: 一号 → 医药
_ASR_ONE_CORRECTION = re.compile(r"我是\s*医药选手")
# 交接话术（不要求本人自称）
_HANDOFF = re.compile(
    r"(?:下面|接下来|稍后|现在|有请|请)\s*(?:请|有请|由)?\s*(?:第)?\s*"
    r"([1234一二两三四])\s*(?:号)?\s*(?:选手|队员|成员)?"
)
# 报号后的岗位短描述
_ROLE_AFTER_INTRO = re.compile(
    r"(?:是|担任|在本项目中担任|主要担任)\s*([^，。,.；;\n]{2,20}?)(?:，|。|,|；|;|负责|主要|$)"
)

# 队员语义（不要求报号）
_CONTESTANT_LANG = re.compile(
    r"我们团队|我们项目|参赛作品|参赛|我是本项目|我是本次|工程师|负责人|演示|"
    r"系统架构|请看|大屏|路演|接下来由我|下面由我|各位评委老师好|尊敬的各位|"
    r"视觉营销|内容营销|直播运营|数据分析|物联网|项目经理|测试工程师"
)
# 外部/评委语义
_EXTERNAL_LANG = re.compile(
    r"请问|有个问题|评委想|老师想问|请先停|停一下|补充一下提问|谢谢回答|我插一句|"
    r"功耗怎么|怎么测|我问一下"
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


def _soft_dominant_cluster(
    start_ms: int,
    end_ms: int,
    turns: list[dict],
) -> tuple[str | None, float, list[str]]:
    """P1: accept high-share winners even when absolute coverage is imperfect."""
    strict = _dominant_cluster(
        start_ms,
        end_ms,
        turns,
        minimum_coverage=0.55,
        minimum_share=0.55,
        minimum_margin=0.15,
    )
    if strict[0] is not None:
        return strict
    ranked = _rank_clusters(start_ms, end_ms, turns)
    if not ranked:
        return None, 0.0, []
    duration = max(1, end_ms - start_ms)
    total = sum(item[0] for item in ranked) or 1
    best_overlap, best_cluster = ranked[0]
    second_overlap = ranked[1][0] if len(ranked) > 1 else 0
    coverage = best_overlap / duration
    share = best_overlap / max(1, total)
    margin = (best_overlap - second_overlap) / max(1, total)
    candidates = [item[1] for item in ranked]
    # High share with modest coverage still usable for transcript labeling.
    if share >= 0.72 and margin >= 0.2 and coverage >= 0.35:
        return best_cluster, round(coverage, 6), candidates
    if share >= 0.85 and coverage >= 0.25:
        return best_cluster, round(coverage, 6), candidates
    return None, round(coverage, 6), candidates


def _slot_from_token(token: str) -> int | None:
    if token.isdigit():
        value = int(token)
        return value if 1 <= value <= 4 else None
    return _CHINESE_SLOTS.get(token)


def _introduction_slot(text: str, *, start_ms: int) -> tuple[int | None, bool]:
    """Back-compat single match (first intro only)."""
    events = _intro_events_in_text(str(text or ""), start_ms=start_ms, end_ms=start_ms)
    if not events:
        return None, False
    return events[0]["slot"], bool(events[0].get("corrected"))


def _intro_events_in_text(
    text: str,
    *,
    start_ms: int,
    end_ms: int,
) -> list[dict]:
    """Find all intro / handoff slot anchors with char-proportional timestamps."""
    raw = str(text or "")
    if not raw.strip():
        return []
    length = max(1, len(raw))
    duration = max(1, int(end_ms) - int(start_ms))
    events: list[dict] = []

    def _push(slot: int, char_start: int, *, corrected: bool, kind: str, role: str | None) -> None:
        t = int(start_ms) + int(duration * max(0, min(char_start, length - 1)) / length)
        events.append(
            {
                "slot": int(slot),
                "startMs": t,
                "charStart": int(char_start),
                "corrected": bool(corrected),
                "kind": kind,
                "roleName": role,
            }
        )

    for match in _INTRODUCTION.finditer(raw):
        slot = _slot_from_token(match.group(1))
        if slot is None:
            continue
        role = None
        tail = raw[match.end() : match.end() + 40]
        role_match = _ROLE_AFTER_INTRO.search(tail)
        if role_match:
            role = role_match.group(1).strip()
        _push(slot, match.start(), corrected=False, kind="intro", role=role)

    if int(start_ms) <= 300_000:
        for match in _ASR_ONE_CORRECTION.finditer(raw):
            role = None
            tail = raw[match.end() : match.end() + 40]
            role_match = _ROLE_AFTER_INTRO.search(tail)
            if role_match:
                role = role_match.group(1).strip()
            _push(1, match.start(), corrected=True, kind="intro_asr_fix", role=role)

    for match in _HANDOFF.finditer(raw):
        slot = _slot_from_token(match.group(1))
        if slot is None:
            continue
        # Avoid double-counting pure "我是X号" which already matches intro.
        window = raw[max(0, match.start() - 4) : match.end()]
        if _INTRODUCTION.search(window):
            continue
        _push(slot, match.start(), corrected=False, kind="handoff", role=None)

    events.sort(key=lambda item: (item["charStart"], item["slot"], item["kind"]))
    # De-dupe same slot at nearly same char (intro + handoff)
    deduped: list[dict] = []
    for event in events:
        if (
            deduped
            and deduped[-1]["slot"] == event["slot"]
            and abs(deduped[-1]["charStart"] - event["charStart"]) <= 4
        ):
            if event["kind"] == "intro" and deduped[-1]["kind"] != "intro":
                deduped[-1] = event
            continue
        deduped.append(event)
    return deduped


def _expand_segments_for_multi_intro(asr_result: dict) -> tuple[list[dict], int]:
    """Split ASR segments that contain multiple slot intros into time-proportional pieces."""
    original = (asr_result or {}).get("segments") or []
    expanded: list[dict] = []
    split_count = 0
    for segment in original:
        if not isinstance(segment, dict):
            continue
        text = str(segment.get("text") or "").strip()
        if not text:
            continue
        start_ms, end_ms = _segment_range(segment)
        events = _intro_events_in_text(text, start_ms=start_ms, end_ms=end_ms)
        intro_like = [e for e in events if e["kind"] in {"intro", "intro_asr_fix"}]
        if len(intro_like) <= 1:
            row = dict(segment)
            row["text"] = text
            row["startMs"] = start_ms
            row["endMs"] = end_ms
            if intro_like:
                row["forcedSlot"] = intro_like[0]["slot"]
                if intro_like[0].get("roleName"):
                    row["forcedRoleName"] = intro_like[0]["roleName"]
            expanded.append(row)
            continue

        split_count += 1
        length = max(1, len(text))
        duration = max(1, end_ms - start_ms)
        # Prefix before first intro → attach to first intro piece
        anchors = intro_like
        for index, event in enumerate(anchors):
            char_start = 0 if index == 0 else int(event["charStart"])
            char_end = (
                int(anchors[index + 1]["charStart"])
                if index + 1 < len(anchors)
                else length
            )
            piece = text[char_start:char_end].strip()
            if not piece:
                continue
            piece_start = start_ms + int(duration * char_start / length)
            piece_end = start_ms + int(duration * char_end / length)
            if piece_end <= piece_start:
                piece_end = piece_start + 1
            row = dict(segment)
            row["text"] = piece
            row["start"] = piece_start / 1000.0
            row["end"] = piece_end / 1000.0
            row["startMs"] = piece_start
            row["endMs"] = piece_end
            row["forcedSlot"] = event["slot"]
            if event.get("roleName"):
                row["forcedRoleName"] = event["roleName"]
            expanded.append(row)
    return expanded, split_count


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
    """Return (cluster→slot, duration_promoted clusters, residual personType by cluster)."""
    slot_count = max(0, min(4, int(contestant_slots)))
    assigned: dict[str, int] = dict(intro_slots)
    used_slots = set(assigned.values())
    promoted: set[str] = set()

    media = max(1, int(duration_ms))
    ranked: list[tuple[float, int, str]] = []
    for cluster in clusters:
        if cluster in assigned:
            continue
        air = int(airtime_ms.get(cluster) or 0)
        c_lang = float(contestant_lang.get(cluster) or 0.0)
        e_lang = float(external_lang.get(cluster) or 0.0)
        air_score = min(1.0, air / max(1.0, media * 0.15))
        score = air_score + 0.35 * min(c_lang, 3.0) / 3.0 - 0.45 * min(e_lang, 3.0) / 3.0
        if e_lang >= 0.8 and air < max(4000, int(media * 0.03)):
            score -= 0.5
        ranked.append((score, air, cluster))
    ranked.sort(key=lambda item: (-item[0], -item[1], item[2]))

    min_air_ms = max(600, int(media * 0.008))
    for score, air, cluster in ranked:
        if len(used_slots) >= slot_count:
            break
        e_lang = float(external_lang.get(cluster) or 0.0)
        c_lang = float(contestant_lang.get(cluster) or 0.0)
        if e_lang > c_lang + 0.3 and air < max(8000, int(media * 0.05)):
            continue
        if air < min_air_ms and c_lang < 0.5:
            continue
        if score < 0.08 and c_lang < 0.5:
            continue
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
        if e_lang >= 0.6 and e_lang >= c_lang:
            residual_type[cluster] = "VISITOR"
        elif air < max(800, int(media * 0.006)):
            residual_type[cluster] = "VISITOR"
        else:
            residual_type[cluster] = "OFFSCREEN"

    return assigned, promoted, residual_type


def _collect_global_intro_events(segments: list[dict], contestant_slots: int) -> list[dict]:
    events: list[dict] = []
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        start_ms, end_ms = _segment_range(segment)
        text = str(segment.get("text") or "")
        for event in _intro_events_in_text(text, start_ms=start_ms, end_ms=end_ms):
            if 1 <= int(event["slot"]) <= int(contestant_slots):
                events.append(event)
    events.sort(key=lambda item: (item["startMs"], item["slot"]))
    return events


def _timeline_slot_for_time(mid_ms: int, intro_events: list[dict]) -> int | None:
    if not intro_events:
        return None
    chosen = None
    for event in intro_events:
        if int(event["startMs"]) <= int(mid_ms) + 250:
            chosen = int(event["slot"])
        else:
            break
    return chosen


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
            cluster_first_last[cluster][0] = min(
                cluster_first_last[cluster][0], int(turn["startMs"])
            )
            cluster_first_last[cluster][1] = max(
                cluster_first_last[cluster][1], int(turn["endMs"])
            )
    clusters = sorted(cluster_first_last, key=lambda key: (cluster_first_last[key][0], key))

    # Expand multi-intro ASR lines before identity work.
    working_asr = dict(asr_result or {})
    expanded_segments, multi_intro_split_count = _expand_segments_for_multi_intro(working_asr)
    working_asr["segments"] = expanded_segments

    # --- Stage 1: explicit introduction anchors (when unambiguous) ---
    claims_by_cluster: dict[str, set[int]] = defaultdict(set)
    clusters_by_slot: dict[int, set[str]] = defaultdict(set)
    correction_count = 0
    role_by_slot: dict[int, str] = {}
    for segment in expanded_segments:
        if not isinstance(segment, dict):
            continue
        start_ms, end_ms = _segment_range(segment)
        text = str(segment.get("text") or "")
        events = _intro_events_in_text(text, start_ms=start_ms, end_ms=end_ms)
        intro_events = [e for e in events if e["kind"] in {"intro", "intro_asr_fix"}]
        # Prefer forcedSlot after multi-intro split (one event per piece).
        if segment.get("forcedSlot") is not None and not intro_events:
            intro_events = [
                {
                    "slot": int(segment["forcedSlot"]),
                    "startMs": start_ms,
                    "charStart": 0,
                    "corrected": False,
                    "kind": "intro",
                    "roleName": segment.get("forcedRoleName"),
                }
            ]
        for event in intro_events:
            slot = int(event["slot"])
            if slot > int(contestant_slots):
                continue
            if event.get("roleName") and slot not in role_by_slot:
                role_by_slot[slot] = str(event["roleName"])
            if event.get("corrected"):
                correction_count += 1
            cluster, _, _ = _dominant_cluster(
                start_ms,
                end_ms,
                turns,
                minimum_coverage=0.45,
                minimum_share=0.55,
                minimum_margin=0.15,
            )
            if cluster is None:
                cluster, _, _ = _soft_dominant_cluster(start_ms, end_ms, turns)
            if cluster is None:
                continue
            claims_by_cluster[cluster].add(slot)
            clusters_by_slot[slot].add(cluster)

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

    # --- Stage 2: fill slots by airtime + language ---
    airtime_ms = _cluster_airtime_ms(turns)
    contestant_lang, external_lang = _cluster_language_scores(working_asr, turns)
    assigned_slots, duration_promoted, residual_type = _auto_contestant_slots(
        clusters=clusters,
        airtime_ms=airtime_ms,
        contestant_lang=contestant_lang,
        external_lang=external_lang,
        intro_slots=intro_slots,
        contestant_slots=int(contestant_slots),
        duration_ms=int(duration_ms),
    )

    global_intro_events = _collect_global_intro_events(
        expanded_segments, int(contestant_slots)
    )
    intro_slot_set = {
        int(e["slot"])
        for e in global_intro_events
        if e["kind"] in {"intro", "intro_asr_fix", "handoff"}
    }
    # Collapsed diarization: few acoustic clusters but many self-intros in text.
    use_intro_timeline = (
        len(intro_slot_set) >= 2
        and (
            len(clusters) <= 1
            or len({slot for slot in assigned_slots.values()}) < len(intro_slot_set)
        )
    )

    cluster_to_person: dict[str, str] = {}
    people: list[dict] = []
    timeline_mode = False
    slot_to_person: dict[int, str] = {}

    if use_intro_timeline:
        timeline_mode = True
        # One stable contestant per introduced slot, ordered by first appearance.
        ordered_slots = sorted(intro_slot_set)
        # Prefer real cluster binding when unique; else virtual INTRO cluster.
        slot_to_cluster: dict[int, str] = {}
        for cluster, slot in assigned_slots.items():
            if slot in ordered_slots and slot not in slot_to_cluster:
                slot_to_cluster[slot] = cluster
        for slot in ordered_slots:
            if slot not in slot_to_cluster:
                slot_to_cluster[slot] = f"INTRO_{slot}"

        for index, slot in enumerate(ordered_slots, start=1):
            person_id = f"PERSON_{index}"
            cluster = slot_to_cluster[slot]
            cluster_to_person[cluster] = person_id
            slot_to_person[slot] = person_id
            # first/last seen from intro events
            slot_times = [int(e["startMs"]) for e in global_intro_events if int(e["slot"]) == slot]
            first_seen = min(slot_times) if slot_times else 0
            last_seen = max(slot_times) if slot_times else first_seen
            if cluster in cluster_first_last:
                first_seen = min(first_seen, cluster_first_last[cluster][0])
                last_seen = max(last_seen, cluster_first_last[cluster][1])
            display = f"{slot}号选手"
            role = role_by_slot.get(slot)
            people.append(
                {
                    "personId": person_id,
                    "personType": "CONTESTANT",
                    "contestantSlot": slot,
                    "displayName": display,
                    "roleName": role,
                    "state": "STABLE",
                    "confidence": 0.88 if role else 0.84,
                    "firstSeenMs": first_seen,
                    "lastSeenMs": last_seen,
                    "faceTrackIds": [],
                    "bodyTrackIds": [],
                    "voiceClusterIds": [cluster],
                    "modelRevision": int(revision),
                }
            )

        # Residual acoustic clusters not used as primary contestant still published.
        used_real = {c for c in slot_to_cluster.values() if not str(c).startswith("INTRO_")}
        residual_index = len(people)
        for cluster in clusters:
            if cluster in used_real or cluster in cluster_to_person:
                # Map real cluster to its contestant person if assigned
                if cluster in assigned_slots and assigned_slots[cluster] in slot_to_person:
                    cluster_to_person[cluster] = slot_to_person[assigned_slots[cluster]]
                continue
            residual_index += 1
            person_id = f"PERSON_{residual_index}"
            cluster_to_person[cluster] = person_id
            person_type = residual_type.get(cluster, "OFFSCREEN")
            people.append(
                {
                    "personId": person_id,
                    "personType": person_type,
                    "contestantSlot": None,
                    "displayName": None,
                    "state": "STABLE",
                    "confidence": 0.55 if person_type == "VISITOR" else 0.6,
                    "firstSeenMs": cluster_first_last[cluster][0],
                    "lastSeenMs": cluster_first_last[cluster][1],
                    "faceTrackIds": [],
                    "bodyTrackIds": [],
                    "voiceClusterIds": [cluster],
                    "modelRevision": int(revision),
                }
            )
        duration_promoted = set(slot_to_cluster.values())
        intro_slots = {slot_to_cluster[s]: s for s in ordered_slots}
        contestant_clusters = set(slot_to_cluster.values())
    else:
        for index, cluster in enumerate(clusters, start=1):
            person_id = f"PERSON_{index}"
            cluster_to_person[cluster] = person_id
            slot = assigned_slots.get(cluster)
            if slot is not None:
                person_type = "CONTESTANT"
                display_name = f"{slot}号选手"
                confidence = 0.9 if cluster in intro_slots else 0.78
                role = role_by_slot.get(slot)
            else:
                person_type = residual_type.get(cluster, "OFFSCREEN")
                display_name = None
                confidence = 0.55 if person_type == "VISITOR" else 0.6
                role = None
            people.append(
                {
                    "personId": person_id,
                    "personType": person_type,
                    "contestantSlot": slot,
                    "displayName": display_name,
                    "roleName": role,
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

    # --- Turns ---
    output_turns: list[dict] = []
    for index, turn in enumerate(turns, start=1):
        cluster = str(turn["sourceClusterId"])
        person_id = cluster_to_person.get(cluster)
        if person_id is None and timeline_mode:
            # Map turn time to intro timeline contestant
            mid = (int(turn["startMs"]) + int(turn["endMs"])) // 2
            slot = _timeline_slot_for_time(mid, global_intro_events)
            person_id = slot_to_person.get(slot) if slot is not None else None
        if person_id is None:
            # Skip orphan turns only if completely unmappable; keep as OFFSCREEN person if exists
            continue
        confirmed = cluster in intro_slots or cluster in contestant_clusters
        output_turns.append(
            {
                "turnId": f"TURN_{index}",
                "startMs": int(turn["startMs"]),
                "endMs": int(turn["endMs"]),
                "personId": person_id,
                "speakerState": "CONFIRMED"
                if cluster in intro_slots or cluster in duration_promoted
                else ("PROVISIONAL" if confirmed else "PROVISIONAL"),
                "confidence": 0.9
                if cluster in intro_slots
                else (0.78 if cluster in duration_promoted else 0.65),
                "candidatePersonIds": [person_id],
                "sourceClusterId": cluster,
            }
        )

    # --- Segments ---
    output_segments: list[dict] = []
    attributed_count = 0
    unknown_count = 0
    timeline_attributed = 0
    for index, segment in enumerate(expanded_segments, start=1):
        if not isinstance(segment, dict):
            continue
        text = str(segment.get("text") or "").strip()
        if not text:
            continue
        start_ms, end_ms = _segment_range(segment)
        mid_ms = (start_ms + end_ms) // 2
        cluster, coverage, candidate_clusters = _soft_dominant_cluster(
            start_ms, end_ms, turns
        )
        candidate_people = [
            cluster_to_person[item]
            for item in candidate_clusters
            if item in cluster_to_person
        ]

        person_id = None
        state = "UNKNOWN"
        confidence = 0.0
        forced_slot = segment.get("forcedSlot")
        if forced_slot is not None and timeline_mode and int(forced_slot) in slot_to_person:
            person_id = slot_to_person[int(forced_slot)]
            state = "CONFIRMED"
            confidence = 0.9
            timeline_attributed += 1
            attributed_count += 1
        elif timeline_mode:
            slot = _timeline_slot_for_time(mid_ms, global_intro_events)
            if forced_slot is not None:
                slot = int(forced_slot)
            if slot is not None and slot in slot_to_person:
                person_id = slot_to_person[slot]
                state = "CONFIRMED"
                confidence = 0.86
                timeline_attributed += 1
                attributed_count += 1
            elif cluster is not None and cluster in cluster_to_person:
                person_id = cluster_to_person[cluster]
                state = "PROVISIONAL"
                confidence = coverage or 0.55
                attributed_count += 1
            else:
                unknown_count += 1
        elif cluster is None:
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

        # External language short segment without contestant language → VISITOR person if any
        if person_id is None and _EXTERNAL_LANG.search(text) and not _CONTESTANT_LANG.search(text):
            visitor = next(
                (p for p in people if p["personType"] == "VISITOR"),
                None,
            )
            if visitor is not None:
                person_id = visitor["personId"]
                state = "PROVISIONAL"
                confidence = 0.5
                attributed_count += 1
                unknown_count = max(0, unknown_count - 1)

        item = {
            "segmentId": f"SEG_{index}",
            "revision": int(revision),
            "startMs": start_ms,
            "endMs": end_ms,
            "text": text,
            "personId": person_id,
            "speakerState": state,
            "speakerConfidence": confidence,
            "candidatePersonIds": candidate_people
            or ([person_id] if person_id else []),
            "isFinal": True,
            "source": str(
                segment.get("source") or (asr_result or {}).get("source") or "asr"
            ),
        }
        if cluster is not None:
            item["rawSpeakerId"] = cluster
            item["sourceClusterId"] = cluster
        elif person_id and timeline_mode:
            # Synthetic raw label for timeline contestants
            person = next((p for p in people if p["personId"] == person_id), None)
            if person and person.get("voiceClusterIds"):
                item["rawSpeakerId"] = person["voiceClusterIds"][0]
                item["sourceClusterId"] = person["voiceClusterIds"][0]
        if segment.get("confidence") is not None:
            item["asrConfidence"] = segment["confidence"]
        output_segments.append(item)

    segment_count = len(output_segments)
    contestant_count = sum(1 for p in people if p["personType"] == "CONTESTANT")
    visitor_count = sum(1 for p in people if p["personType"] == "VISITOR")
    unattributed_count = sum(1 for p in people if p["personType"] == "OFFSCREEN")
    policy = (
        "intro_timeline_collapsed_diarization"
        if timeline_mode
        else "intro_then_top_airtime_language_no_enrollment"
    )
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
            "introductionAnchoredCount": len(
                {int(e["slot"]) for e in global_intro_events if e["kind"].startswith("intro")}
            ),
            "durationPromotedCount": len(duration_promoted),
            "anonymousPersonCount": visitor_count + unattributed_count,
            "visitorPersonCount": visitor_count,
            "unattributedPersonCount": unattributed_count,
            "introductionConflictCount": len(conflicting_clusters),
            "introductionCorrectionCount": correction_count,
            "attributedSegmentCount": attributed_count,
            "unknownSegmentCount": unknown_count,
            "transcriptCoverageRatio": round(attributed_count / segment_count, 6)
            if segment_count
            else 0.0,
            "confidenceSemantics": "derived_temporal_alignment_not_model_score",
            "assignmentPolicy": policy,
            "multiIntroSegmentSplitCount": multi_intro_split_count,
            "introTimelineMode": timeline_mode,
            "introTimelineAttributedSegments": timeline_attributed,
            "introEventCount": len(global_intro_events),
        },
    }
    return normalize_speaker_attribution(result)
