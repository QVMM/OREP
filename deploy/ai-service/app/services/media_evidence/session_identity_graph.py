"""Pure in-memory identity graph for one roadshow session."""

from __future__ import annotations

from dataclasses import dataclass, field
from .speaker_attribution_contract import normalize_speaker_attribution


PERSON_TYPES = {"CONTESTANT", "VISITOR", "OFFSCREEN"}
OBSERVATION_KINDS = {"FACE", "BODY", "VOICE", "ACTIVE_SPEAKER", "SEMANTIC"}


class IdentityGraphConflict(ValueError):
    """Raised when an identity mutation contradicts existing evidence."""


@dataclass(frozen=True)
class ObservationRef:
    kind: str
    observation_id: str
    start_ms: int
    end_ms: int
    confidence: float

    def __post_init__(self) -> None:
        kind = str(self.kind).upper()
        if kind not in OBSERVATION_KINDS:
            raise ValueError(f"INVALID_OBSERVATION_KIND:{kind}")
        if not str(self.observation_id).strip():
            raise ValueError("EMPTY_OBSERVATION_ID")
        if self.start_ms < 0 or self.end_ms < self.start_ms:
            raise ValueError("INVALID_OBSERVATION_TIME")
        if not 0 <= float(self.confidence) <= 1:
            raise ValueError("INVALID_OBSERVATION_CONFIDENCE")
        object.__setattr__(self, "kind", kind)


@dataclass(frozen=True)
class MergeEvidence:
    modalities: set[str]
    confidence: float
    reason: str

    def __post_init__(self) -> None:
        normalized = {str(value).upper() for value in self.modalities}
        if not normalized.issubset(OBSERVATION_KINDS):
            raise ValueError("INVALID_MERGE_MODALITY")
        if not 0 <= float(self.confidence) <= 1:
            raise ValueError("INVALID_MERGE_CONFIDENCE")
        if not str(self.reason).strip():
            raise ValueError("EMPTY_MERGE_REASON")
        object.__setattr__(self, "modalities", normalized)


@dataclass
class PersonNode:
    person_id: str
    person_type: str
    contestant_slot: int | None
    first_seen_ms: int
    last_seen_ms: int
    state: str = "CANDIDATE"
    confidence: float = 0.0
    face_track_ids: set[str] = field(default_factory=set)
    body_track_ids: set[str] = field(default_factory=set)
    voice_cluster_ids: set[str] = field(default_factory=set)
    observations: list[ObservationRef] = field(default_factory=list)
    merged_into: str | None = None


class SessionIdentityGraph:
    """Maintain stable session people without treating raw clusters as people."""

    def __init__(self, *, session_id: str, contestant_slots: int = 4):
        if not str(session_id).strip():
            raise ValueError("EMPTY_SESSION_ID")
        if isinstance(contestant_slots, bool) or not 0 <= int(contestant_slots) <= 4:
            raise ValueError("INVALID_CONTESTANT_SLOT_COUNT")
        self.session_id = str(session_id)
        self._people: dict[str, PersonNode] = {}
        self._next_person_number = 1
        for slot in range(1, int(contestant_slots) + 1):
            self.create_person("CONTESTANT", first_seen_ms=0, contestant_slot=slot)

    def _new_id(self) -> str:
        person_id = f"PERSON_{self._next_person_number}"
        self._next_person_number += 1
        return person_id

    def create_person(
        self,
        person_type: str,
        *,
        first_seen_ms: int,
        contestant_slot: int | None = None,
    ) -> PersonNode:
        normalized_type = str(person_type).upper()
        if normalized_type not in PERSON_TYPES:
            raise ValueError(f"INVALID_PERSON_TYPE:{normalized_type}")
        if first_seen_ms < 0:
            raise ValueError("INVALID_FIRST_SEEN_MS")
        if normalized_type == "CONTESTANT":
            if contestant_slot not in {1, 2, 3, 4}:
                raise ValueError("INVALID_CONTESTANT_SLOT")
            if any(
                person.person_type == "CONTESTANT"
                and person.contestant_slot == contestant_slot
                for person in self._people.values()
            ):
                raise ValueError("DUPLICATE_CONTESTANT_SLOT")
        elif contestant_slot is not None:
            raise ValueError("NON_CONTESTANT_HAS_SLOT")
        node = PersonNode(
            person_id=self._new_id(),
            person_type=normalized_type,
            contestant_slot=contestant_slot,
            first_seen_ms=int(first_seen_ms),
            last_seen_ms=int(first_seen_ms),
        )
        self._people[node.person_id] = node
        return node

    def person(self, person_id: str) -> PersonNode:
        try:
            return self._people[str(person_id)]
        except KeyError as error:
            raise KeyError(f"UNKNOWN_PERSON:{person_id}") from error

    def people(self) -> list[PersonNode]:
        return sorted(
            self._people.values(),
            key=lambda item: (item.first_seen_ms, item.person_id),
        )

    def contestant_slots(self) -> list[PersonNode]:
        return sorted(
            (item for item in self._people.values() if item.person_type == "CONTESTANT"),
            key=lambda item: int(item.contestant_slot or 0),
        )

    def attach_observation(self, person_id: str, observation: ObservationRef) -> PersonNode:
        person = self.person(person_id)
        if person.state == "MERGED":
            raise IdentityGraphConflict("CANNOT_ATTACH_TO_MERGED_PERSON")
        if observation not in person.observations:
            person.observations.append(observation)
        person.first_seen_ms = min(person.first_seen_ms, observation.start_ms)
        person.last_seen_ms = max(person.last_seen_ms, observation.end_ms)
        person.confidence = max(person.confidence, round(float(observation.confidence), 6))
        alias_sets = {
            "FACE": person.face_track_ids,
            "BODY": person.body_track_ids,
            "VOICE": person.voice_cluster_ids,
        }
        if observation.kind in alias_sets:
            alias_sets[observation.kind].add(observation.observation_id)
        return person

    @staticmethod
    def _overlap(left: ObservationRef, right: ObservationRef) -> bool:
        return min(left.end_ms, right.end_ms) > max(left.start_ms, right.start_ms)

    def _has_co_visible_conflict(self, target: PersonNode, source: PersonNode) -> bool:
        target_faces = [item for item in target.observations if item.kind == "FACE"]
        source_faces = [item for item in source.observations if item.kind == "FACE"]
        return any(self._overlap(left, right) for left in target_faces for right in source_faces)

    def merge_people(
        self,
        target_person_id: str,
        source_person_id: str,
        evidence: MergeEvidence,
    ) -> PersonNode:
        if target_person_id == source_person_id:
            return self.person(target_person_id)
        target = self.person(target_person_id)
        source = self.person(source_person_id)
        if target.state == "MERGED" or source.state == "MERGED":
            raise IdentityGraphConflict("PERSON_ALREADY_MERGED")
        strong_single_face = evidence.modalities == {"FACE"} and evidence.confidence >= 0.95
        if len(evidence.modalities) < 2 and not strong_single_face:
            raise IdentityGraphConflict("INSUFFICIENT_MERGE_EVIDENCE")
        if self._has_co_visible_conflict(target, source):
            raise IdentityGraphConflict("CO_VISIBLE_CONFLICT")
        for observation in list(source.observations):
            self.attach_observation(target.person_id, observation)
        target.confidence = max(target.confidence, round(float(evidence.confidence), 6))
        source.state = "MERGED"
        source.merged_into = target.person_id
        return target

    def upgrade_person_type(self, person_id: str, person_type: str) -> PersonNode:
        person = self.person(person_id)
        normalized_type = str(person_type).upper()
        if normalized_type not in {"VISITOR", "OFFSCREEN"}:
            raise ValueError("INVALID_PERSON_TYPE_UPGRADE")
        if person.person_type == "CONTESTANT":
            raise IdentityGraphConflict("CANNOT_CHANGE_CONTESTANT_ROLE")
        person.person_type = normalized_type
        return person

    def split_alias(
        self,
        person_id: str,
        *,
        alias_kind: str,
        alias_id: str,
        reason: str,
    ) -> PersonNode:
        person = self.person(person_id)
        kind = str(alias_kind).upper()
        alias_sets = {
            "FACE": person.face_track_ids,
            "BODY": person.body_track_ids,
            "VOICE": person.voice_cluster_ids,
        }
        if kind not in alias_sets or alias_id not in alias_sets[kind]:
            raise IdentityGraphConflict("UNKNOWN_ALIAS")
        if not str(reason).strip():
            raise ValueError("EMPTY_SPLIT_REASON")
        detached = self.create_person(person.person_type, first_seen_ms=person.first_seen_ms)
        moved = [
            item
            for item in person.observations
            if item.kind == kind and item.observation_id == alias_id
        ]
        person.observations = [item for item in person.observations if item not in moved]
        alias_sets[kind].discard(alias_id)
        for observation in moved:
            self.attach_observation(detached.person_id, observation)
        return detached

    def snapshot(self, *, revision: int, status: str, clock: dict) -> dict:
        people = []
        for person in self.people():
            people.append(
                {
                    "personId": person.person_id,
                    "personType": person.person_type,
                    "contestantSlot": person.contestant_slot,
                    "displayName": (
                        f"{person.contestant_slot}号选手"
                        if person.person_type == "CONTESTANT"
                        else None
                    ),
                    "state": person.state,
                    "confidence": person.confidence,
                    "firstSeenMs": person.first_seen_ms,
                    "lastSeenMs": person.last_seen_ms,
                    "faceTrackIds": sorted(person.face_track_ids),
                    "bodyTrackIds": sorted(person.body_track_ids),
                    "voiceClusterIds": sorted(person.voice_cluster_ids),
                    "modelRevision": int(revision),
                }
            )
        return normalize_speaker_attribution(
            {
                "contractVersion": "speaker-attribution-v1",
                "revision": int(revision),
                "status": str(status).upper(),
                "clock": dict(clock),
                "people": people,
                "turns": [],
                "segments": [],
            }
        )
