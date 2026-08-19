package com.orep.backend.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.orep.backend.dto.PipelineCallbackRequest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.stereotype.Service;
import org.springframework.transaction.support.TransactionTemplate;

import javax.sql.DataSource;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

@Service
public class AiScoreSpeakerAttributionPersistenceService {
    public enum PersistenceOutcome {
        APPLIED,
        IDEMPOTENT,
        STALE_IGNORED,
        FINAL_PROTECTED
    }

    private record CurrentSnapshot(Integer revision, String status, String snapshotHash) {}

    private static final Set<String> PERSON_TYPES = Set.of("CONTESTANT", "VISITOR", "OFFSCREEN");
    private static final Set<String> SPEAKER_STATES = Set.of(
            "CONFIRMED", "PROVISIONAL", "OFFSCREEN_CONFIRMED", "UNKNOWN", "OVERLAP"
    );

    private final JdbcTemplate jdbc;
    private final TransactionTemplate transactions;
    private final ObjectMapper objectMapper = new ObjectMapper()
            .configure(SerializationFeature.ORDER_MAP_ENTRIES_BY_KEYS, true);

    public AiScoreSpeakerAttributionPersistenceService(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
        DataSource dataSource = jdbc.getDataSource();
        if (dataSource == null) {
            throw new IllegalArgumentException("speaker attribution requires a JDBC data source");
        }
        this.transactions = new TransactionTemplate(new DataSourceTransactionManager(dataSource));
    }

    public PersistenceOutcome persist(
            Long sessionId,
            PipelineCallbackRequest.SpeakerAttributionInput snapshot
    ) {
        ValidatedSnapshot valid = validate(sessionId, snapshot);
        PersistenceOutcome result = transactions.execute(status -> apply(valid));
        if (result == null) throw new IllegalStateException("speaker attribution transaction returned null");
        return result;
    }

    private PersistenceOutcome apply(ValidatedSnapshot snapshot) {
        CurrentSnapshot current = jdbc.query(
                """
                        SELECT speaker_attribution_revision, speaker_attribution_status,
                               speaker_attribution_snapshot_hash
                        FROM ai_scoring_session WHERE id=? FOR UPDATE
                        """,
                rs -> rs.next()
                        ? new CurrentSnapshot(
                                (Integer) rs.getObject(1),
                                rs.getString(2),
                                rs.getString(3)
                        )
                        : null,
                snapshot.sessionId()
        );
        if (current == null) throw new IllegalArgumentException("评分会话不存在");

        if ("FINAL".equals(current.status()) && "PROVISIONAL".equals(snapshot.status())) {
            return PersistenceOutcome.FINAL_PROTECTED;
        }
        if (current.revision() != null && snapshot.revision() < current.revision()) {
            return PersistenceOutcome.STALE_IGNORED;
        }
        if (current.revision() != null && snapshot.revision() == current.revision()) {
            if (snapshot.snapshotHash().equals(current.snapshotHash())) {
                return PersistenceOutcome.IDEMPOTENT;
            }
            throw new IllegalArgumentException("speaker attribution revision conflict");
        }

        jdbc.update(
                "DELETE FROM ai_score_speaker_identity WHERE session_id=? AND source<>'USER'",
                snapshot.sessionId()
        );
        jdbc.update("DELETE FROM ai_score_speaker_turn WHERE session_id=?", snapshot.sessionId());
        jdbc.update("DELETE FROM ai_score_transcript_segment WHERE session_id=?", snapshot.sessionId());

        Map<String, Long> humanIdentityByRawSpeaker = new HashMap<>();
        for (Map<String, Object> row : jdbc.queryForList(
                """
                        SELECT id, raw_speaker_label
                        FROM ai_score_speaker_identity
                        WHERE session_id=? AND source='USER' AND raw_speaker_label IS NOT NULL
                        """,
                snapshot.sessionId()
        )) {
            Object id = row.get("id");
            Object rawSpeaker = row.get("raw_speaker_label");
            if (id instanceof Number number && rawSpeaker != null) {
                humanIdentityByRawSpeaker.put(String.valueOf(rawSpeaker), number.longValue());
            }
        }

        for (PipelineCallbackRequest.AttributionPersonInput person : snapshot.people()) {
            String primaryVoiceCluster = first(person.getVoiceClusterIds());
            Long humanIdentityId = primaryVoiceCluster == null
                    ? null : humanIdentityByRawSpeaker.get(primaryVoiceCluster);
            if (humanIdentityId != null) {
                // The human decision is the display name/role attached to an
                // immutable acoustic cluster. Refresh only machine-owned graph
                // fields so a new terminal snapshot cannot collide with or
                // erase that correction.
                jdbc.update(
                        """
                                UPDATE ai_score_speaker_identity
                                SET person_id=?, person_type=?, contestant_slot=?,
                                    revision=GREATEST(revision, ?), person_state=?,
                                    first_seen_ms=?, last_seen_ms=?, voice_cluster_ids_json=?,
                                    updated_at=CURRENT_TIMESTAMP
                                WHERE id=? AND session_id=? AND source='USER'
                                """,
                        person.getPersonId(), upper(person.getPersonType()),
                        person.getContestantSlot(),
                        person.getModelRevision() == null
                                ? snapshot.revision() : person.getModelRevision(),
                        upper(person.getState()), person.getFirstSeenMs(),
                        person.getLastSeenMs(), json(person.getVoiceClusterIds()),
                        humanIdentityId, snapshot.sessionId()
                );
                continue;
            }
            jdbc.update(
                    """
                            INSERT INTO ai_score_speaker_identity(
                              session_id, raw_speaker_label, person_id, person_type,
                              contestant_slot, display_name, role_name, status, source,
                              confidence, revision, person_state, first_seen_ms, last_seen_ms,
                              voice_cluster_ids_json, created_at, updated_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'AUTO', 'MODEL', ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                            """,
                    snapshot.sessionId(),
                    primaryVoiceCluster,
                    person.getPersonId(),
                    upper(person.getPersonType()),
                    person.getContestantSlot(),
                    blankToNull(person.getDisplayName()),
                    blankToNull(person.getRoleName()),
                    person.getConfidence(),
                    person.getModelRevision() == null ? snapshot.revision() : person.getModelRevision(),
                    upper(person.getState()),
                    person.getFirstSeenMs(),
                    person.getLastSeenMs(),
                    json(person.getVoiceClusterIds())
            );
        }

        for (PipelineCallbackRequest.AttributionTurnInput turn : snapshot.turns()) {
            jdbc.update(
                    """
                            INSERT INTO ai_score_speaker_turn(
                              session_id, turn_uid, attribution_revision, start_ms, end_ms,
                              person_id, speaker_state, confidence, candidate_person_ids_json,
                              source_cluster_id, source_visual_identity_id, speaker_verification
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                    snapshot.sessionId(), turn.getTurnId(), snapshot.revision(),
                    turn.getStartMs(), turn.getEndMs(), blankToNull(turn.getPersonId()),
                    upper(turn.getSpeakerState()), turn.getConfidence(),
                    json(turn.getCandidatePersonIds()), blankToNull(turn.getSourceClusterId()),
                    blankToNull(turn.getSourceVisualIdentityId()),
                    blankToNull(turn.getSpeakerVerification())
            );
        }

        int segmentNo = 0;
        for (PipelineCallbackRequest.AttributionSegmentInput segment : snapshot.segments()) {
            segmentNo++;
            String rawSpeaker = blankToNull(segment.getRawSpeakerId());
            String segmentHash = sha256(
                    snapshot.sessionId() + "|" + segment.getSegmentId() + "|"
                            + segment.getRevision() + "|" + segment.getStartMs() + "|"
                            + segment.getEndMs() + "|" + segment.getText()
            );
            jdbc.update(
                    """
                            INSERT INTO ai_score_transcript_segment(
                              session_id, segment_no, segment_uid, attribution_revision,
                              speaker_label, person_id, speaker_state, speaker_confidence,
                              is_final, start_ms, end_ms, text, source_type, confidence, segment_hash
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'speaker_attribution', ?, ?)
                            """,
                    snapshot.sessionId(), segmentNo, segment.getSegmentId(), segment.getRevision(),
                    rawSpeaker, blankToNull(segment.getPersonId()), upper(segment.getSpeakerState()),
                    segment.getSpeakerConfidence(), Boolean.TRUE.equals(segment.getFinal()),
                    segment.getStartMs(), segment.getEndMs(), segment.getText(),
                    segment.getSpeakerConfidence(), segmentHash
            );
        }

        jdbc.update(
                """
                        UPDATE ai_scoring_session
                        SET speaker_attribution_revision=?, speaker_attribution_status=?,
                            speaker_attribution_contract_version=?, speaker_attribution_clock_id=?,
                            speaker_attribution_snapshot_hash=?
                        WHERE id=?
                        """,
                snapshot.revision(), snapshot.status(), snapshot.contractVersion(),
                snapshot.clockId(), snapshot.snapshotHash(), snapshot.sessionId()
        );
        return PersistenceOutcome.APPLIED;
    }

    private ValidatedSnapshot validate(
            Long sessionId,
            PipelineCallbackRequest.SpeakerAttributionInput snapshot
    ) {
        if (sessionId == null || sessionId <= 0) throw new IllegalArgumentException("评分会话无效");
        if (snapshot == null) throw new IllegalArgumentException("speaker attribution is required");
        if (!"speaker-attribution-v1".equals(snapshot.getContractVersion())) {
            throw new IllegalArgumentException("unsupported speaker attribution contract");
        }
        if (snapshot.getRevision() == null || snapshot.getRevision() < 1) {
            throw new IllegalArgumentException("invalid speaker attribution revision");
        }
        String status = upper(snapshot.getStatus());
        if (!Set.of("PROVISIONAL", "FINAL").contains(status)) {
            throw new IllegalArgumentException("invalid speaker attribution status");
        }
        Map<String, Object> clock = snapshot.getClock();
        String clockId = clock == null ? "" : text(clock.get("clockId"));
        if (clockId.isBlank()) throw new IllegalArgumentException("speaker attribution clock is required");

        List<PipelineCallbackRequest.AttributionPersonInput> people = copy(snapshot.getPeople());
        List<PipelineCallbackRequest.AttributionTurnInput> turns = copy(snapshot.getTurns());
        List<PipelineCallbackRequest.AttributionSegmentInput> segments = copy(snapshot.getSegments());
        Set<String> personIds = new HashSet<>();
        Set<Integer> contestantSlots = new HashSet<>();
        for (PipelineCallbackRequest.AttributionPersonInput person : people) {
            if (person == null || text(person.getPersonId()).isBlank()
                    || !personIds.add(person.getPersonId())) {
                throw new IllegalArgumentException("duplicate or empty person id");
            }
            String personType = upper(person.getPersonType());
            if (!PERSON_TYPES.contains(personType)) throw new IllegalArgumentException("invalid person type");
            if ("CONTESTANT".equals(personType)) {
                Integer slot = person.getContestantSlot();
                if (slot == null || slot < 1 || slot > 4 || !contestantSlots.add(slot)) {
                    throw new IllegalArgumentException("invalid contestant slot");
                }
            } else if (person.getContestantSlot() != null) {
                throw new IllegalArgumentException("non-contestant cannot have a slot");
            }
            range(person.getFirstSeenMs(), person.getLastSeenMs(), "person");
            confidence(person.getConfidence());
        }

        Set<String> turnIds = new HashSet<>();
        for (PipelineCallbackRequest.AttributionTurnInput turn : turns) {
            if (turn == null || text(turn.getTurnId()).isBlank() || !turnIds.add(turn.getTurnId())) {
                throw new IllegalArgumentException("duplicate or empty turn id");
            }
            range(turn.getStartMs(), turn.getEndMs(), "turn");
            validateReference(turn.getPersonId(), personIds);
            for (String candidate : turn.getCandidatePersonIds() == null
                    ? List.<String>of() : turn.getCandidatePersonIds()) {
                validateReference(candidate, personIds);
            }
            String speakerState = upper(turn.getSpeakerState());
            if (!SPEAKER_STATES.contains(speakerState)) throw new IllegalArgumentException("invalid speaker state");
            if (Set.of("UNKNOWN", "OVERLAP").contains(speakerState) && turn.getPersonId() != null) {
                throw new IllegalArgumentException("unknown or overlap turn cannot bind a person");
            }
            confidence(turn.getConfidence());
        }

        Set<String> segmentIds = new HashSet<>();
        for (PipelineCallbackRequest.AttributionSegmentInput segment : segments) {
            if (segment == null || text(segment.getSegmentId()).isBlank()
                    || !segmentIds.add(segment.getSegmentId())) {
                throw new IllegalArgumentException("duplicate or empty segment id");
            }
            if (segment.getRevision() == null || segment.getRevision() < 1
                    || segment.getRevision() > snapshot.getRevision()) {
                throw new IllegalArgumentException("invalid segment revision");
            }
            range(segment.getStartMs(), segment.getEndMs(), "segment");
            if (text(segment.getText()).isBlank()) throw new IllegalArgumentException("empty transcript text");
            validateReference(segment.getPersonId(), personIds);
            String speakerState = upper(segment.getSpeakerState());
            if (!SPEAKER_STATES.contains(speakerState)) throw new IllegalArgumentException("invalid speaker state");
            if (Set.of("UNKNOWN", "OVERLAP").contains(speakerState) && segment.getPersonId() != null) {
                throw new IllegalArgumentException("unknown segment cannot bind a person");
            }
            if ("FINAL".equals(status) && !Boolean.TRUE.equals(segment.getFinal())) {
                throw new IllegalArgumentException("final snapshot contains provisional segment");
            }
            confidence(segment.getSpeakerConfidence());
        }

        String snapshotHash = sha256(json(snapshot));
        return new ValidatedSnapshot(
                sessionId, snapshot.getContractVersion(), snapshot.getRevision(), status,
                clockId, snapshotHash, people, turns, segments
        );
    }

    private void validateReference(String personId, Set<String> known) {
        if (personId != null && !personId.isBlank() && !known.contains(personId)) {
            throw new IllegalArgumentException("unknown person reference: " + personId);
        }
    }

    private void range(Long start, Long end, String type) {
        if (start == null || end == null || start < 0 || end < start) {
            throw new IllegalArgumentException("invalid " + type + " time range");
        }
    }

    private void confidence(BigDecimal value) {
        if (value != null && (value.compareTo(BigDecimal.ZERO) < 0
                || value.compareTo(BigDecimal.ONE) > 0)) {
            throw new IllegalArgumentException("invalid confidence");
        }
    }

    private <T> List<T> copy(List<T> value) {
        return value == null ? List.of() : new ArrayList<>(value);
    }

    private String json(Object value) {
        try {
            return objectMapper.writeValueAsString(value == null ? List.of() : value);
        } catch (Exception error) {
            throw new IllegalArgumentException("speaker attribution JSON serialization failed", error);
        }
    }

    private String sha256(String value) {
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256")
                    .digest(value.getBytes(StandardCharsets.UTF_8));
            StringBuilder result = new StringBuilder("sha256:");
            for (byte item : digest) result.append(String.format("%02x", item));
            return result.toString();
        } catch (Exception error) {
            throw new IllegalStateException("speaker attribution hash failed", error);
        }
    }

    private String first(List<String> values) {
        if (values == null) return null;
        return values.stream().map(this::blankToNull).filter(value -> value != null).findFirst().orElse(null);
    }

    private String blankToNull(String value) {
        String result = text(value);
        return result.isBlank() ? null : result;
    }

    private String upper(String value) {
        return text(value).toUpperCase();
    }

    private String text(Object value) {
        return value == null ? "" : String.valueOf(value).trim();
    }

    private record ValidatedSnapshot(
            Long sessionId,
            String contractVersion,
            int revision,
            String status,
            String clockId,
            String snapshotHash,
            List<PipelineCallbackRequest.AttributionPersonInput> people,
            List<PipelineCallbackRequest.AttributionTurnInput> turns,
            List<PipelineCallbackRequest.AttributionSegmentInput> segments
    ) {}
}
