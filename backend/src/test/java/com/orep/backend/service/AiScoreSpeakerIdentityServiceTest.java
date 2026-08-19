package com.orep.backend.service;

import com.orep.backend.dto.PipelineCallbackRequest;
import com.orep.backend.entity.AiScoreSpeakerIdentity;
import com.orep.backend.entity.AiScoreTranscriptSegment;
import com.orep.backend.mapper.AiScoreSpeakerIdentityMapper;
import com.orep.backend.mapper.AiScoreTranscriptSegmentMapper;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class AiScoreSpeakerIdentityServiceTest {

    @Test
    void unresolvedBucketWithoutRawClusterIsNotPersistedAsANinthPerson() {
        AiScoreSpeakerIdentityMapper identityMapper = mock(AiScoreSpeakerIdentityMapper.class);
        AiScoreSpeakerIdentityService service = new AiScoreSpeakerIdentityService(
                identityMapper, mock(AiScoreTranscriptSegmentMapper.class)
        );
        PipelineCallbackRequest.SpeakerEvidenceInput unresolved =
                new PipelineCallbackRequest.SpeakerEvidenceInput();
        unresolved.setRawSpeakerId(null);
        unresolved.setDisplayName("发言人待确认");
        unresolved.setStatus("UNRESOLVED");

        List<AiScoreSpeakerIdentity> result = service.upsertAutoEvidence(
                26L, List.of(unresolved)
        );

        assertThat(result).isEmpty();
        verify(identityMapper, never()).selectOne(any());
        verify(identityMapper, never()).insert(any());
        verify(identityMapper, never()).updateById(any());
    }

    @Test
    void insertsModelSpeakerEvidenceAsAutoIdentityWithoutAnyScore() {
        AiScoreSpeakerIdentityMapper identityMapper = mock(AiScoreSpeakerIdentityMapper.class);
        AiScoreTranscriptSegmentMapper segmentMapper = mock(AiScoreTranscriptSegmentMapper.class);
        when(identityMapper.selectOne(any())).thenReturn(null);
        when(identityMapper.insert(any())).thenAnswer(invocation -> {
            AiScoreSpeakerIdentity value = invocation.getArgument(0);
            value.setId(18L);
            return 1;
        });
        AiScoreSpeakerIdentityService service = new AiScoreSpeakerIdentityService(identityMapper, segmentMapper);
        PipelineCallbackRequest.SpeakerEvidenceInput evidence = speakerEvidence(
                "SPEAKER_0", "1号发言人", null, "0.9132"
        );

        List<AiScoreSpeakerIdentity> result = service.upsertAutoEvidence(26L, List.of(evidence));

        assertThat(result).hasSize(1);
        AiScoreSpeakerIdentity identity = result.get(0);
        assertThat(identity.getSessionId()).isEqualTo(26L);
        assertThat(identity.getRawSpeakerLabel()).isEqualTo("SPEAKER_0");
        assertThat(identity.getDisplayName()).isEqualTo("1号发言人");
        assertThat(identity.getStatus()).isEqualTo("AUTO");
        assertThat(identity.getSource()).isEqualTo("MODEL");
        assertThat(identity.getConfidence()).isEqualByComparingTo("0.9132");
        assertThat(identity.getRevision()).isEqualTo(1);
        verify(identityMapper).insert(identity);
    }

    @Test
    void completedCallbackReplayUpdatesAutoIdentityInsteadOfDuplicatingIt() {
        AiScoreSpeakerIdentityMapper identityMapper = mock(AiScoreSpeakerIdentityMapper.class);
        AiScoreSpeakerIdentity existing = new AiScoreSpeakerIdentity();
        existing.setId(18L);
        existing.setSessionId(26L);
        existing.setRawSpeakerLabel("SPEAKER_0");
        existing.setDisplayName("旧名称");
        existing.setStatus("AUTO");
        existing.setSource("MODEL");
        existing.setRevision(1);
        when(identityMapper.selectOne(any())).thenReturn(existing);
        AiScoreSpeakerIdentityService service = new AiScoreSpeakerIdentityService(
                identityMapper, mock(AiScoreTranscriptSegmentMapper.class)
        );

        service.upsertAutoEvidence(26L, List.of(
                speakerEvidence("SPEAKER_0", "1号发言人", null, "0.8800")
        ));

        verify(identityMapper, never()).insert(any());
        verify(identityMapper).updateById(existing);
        assertThat(existing.getDisplayName()).isEqualTo("1号发言人");
        assertThat(existing.getRevision()).isEqualTo(1);
    }

    @Test
    void modelReplayNeverOverwritesHumanConfirmedOrRejectedIdentity() {
        for (String protectedStatus : List.of("CONFIRMED", "REJECTED")) {
            AiScoreSpeakerIdentityMapper identityMapper = mock(AiScoreSpeakerIdentityMapper.class);
            AiScoreSpeakerIdentity existing = new AiScoreSpeakerIdentity();
            existing.setId(19L);
            existing.setSessionId(26L);
            existing.setRawSpeakerLabel("SPEAKER_1");
            existing.setDisplayName("已人工确认");
            existing.setStatus(protectedStatus);
            existing.setSource("USER");
            existing.setRevision(3);
            when(identityMapper.selectOne(any())).thenReturn(existing);
            AiScoreSpeakerIdentityService service = new AiScoreSpeakerIdentityService(
                    identityMapper, mock(AiScoreTranscriptSegmentMapper.class)
            );

            service.upsertAutoEvidence(26L, List.of(
                    speakerEvidence("SPEAKER_1", "模型新名称", null, "0.9900")
            ));

            verify(identityMapper, never()).insert(any());
            verify(identityMapper, never()).updateById(any());
            assertThat(existing.getDisplayName()).isEqualTo("已人工确认");
            assertThat(existing.getStatus()).isEqualTo(protectedStatus);
            assertThat(existing.getRevision()).isEqualTo(3);
        }
    }

    private PipelineCallbackRequest.SpeakerEvidenceInput speakerEvidence(
            String rawSpeakerId,
            String displayName,
            String roleName,
            String confidence
    ) {
        PipelineCallbackRequest.SpeakerEvidenceInput input = new PipelineCallbackRequest.SpeakerEvidenceInput();
        input.setRawSpeakerId(rawSpeakerId);
        input.setDisplayName(displayName);
        input.setRoleName(roleName);
        input.setStatus("AUTO");
        input.setSource("final_asr");
        input.setConfidence(new java.math.BigDecimal(confidence));
        return input;
    }

    @Test
    void confirmsDisplayIdentityWithoutChangingRawSpeakerLabel() {
        AiScoreSpeakerIdentityMapper identityMapper = mock(AiScoreSpeakerIdentityMapper.class);
        AiScoreTranscriptSegmentMapper segmentMapper = mock(AiScoreTranscriptSegmentMapper.class);
        AiScoreTranscriptSegment segment = new AiScoreTranscriptSegment();
        segment.setSpeakerLabel("SPEAKER_2");
        when(segmentMapper.selectList(any())).thenReturn(List.of(segment));
        when(identityMapper.selectOne(any())).thenReturn(null);
        when(identityMapper.insert(any())).thenAnswer(invocation -> {
            AiScoreSpeakerIdentity value = invocation.getArgument(0);
            value.setId(8L);
            return 1;
        });
        AiScoreSpeakerIdentityService service = new AiScoreSpeakerIdentityService(identityMapper, segmentMapper);

        AiScoreSpeakerIdentity result = service.confirm(
                26L, "SPEAKER_2", "3号选手", "AI算法工程师", 7L
        );

        assertThat(result.getId()).isEqualTo(8L);
        assertThat(result.getSessionId()).isEqualTo(26L);
        assertThat(result.getRawSpeakerLabel()).isEqualTo("SPEAKER_2");
        assertThat(result.getDisplayName()).isEqualTo("3号选手");
        assertThat(result.getRoleName()).isEqualTo("AI算法工程师");
        assertThat(result.getStatus()).isEqualTo("CONFIRMED");
        assertThat(result.getSource()).isEqualTo("USER");
        assertThat(result.getConfidence()).isEqualByComparingTo("1.0000");
        assertThat(result.getRevision()).isEqualTo(1);
        assertThat(result.getUpdatedBy()).isEqualTo(7L);
    }

    @Test
    void correctionIncrementsRevisionButPreservesStoredRawLabel() {
        AiScoreSpeakerIdentityMapper identityMapper = mock(AiScoreSpeakerIdentityMapper.class);
        AiScoreTranscriptSegmentMapper segmentMapper = mock(AiScoreTranscriptSegmentMapper.class);
        AiScoreTranscriptSegment segment = new AiScoreTranscriptSegment();
        segment.setSpeakerLabel("SPEAKER_1");
        when(segmentMapper.selectList(any())).thenReturn(List.of(segment));
        AiScoreSpeakerIdentity existing = new AiScoreSpeakerIdentity();
        existing.setId(9L);
        existing.setSessionId(26L);
        existing.setRawSpeakerLabel("SPEAKER_1");
        existing.setRevision(2);
        when(identityMapper.selectOne(any())).thenReturn(existing);
        AiScoreSpeakerIdentityService service = new AiScoreSpeakerIdentityService(identityMapper, segmentMapper);

        service.confirm(26L, "SPEAKER_1", "2号选手", "前端工程师", 7L);

        ArgumentCaptor<AiScoreSpeakerIdentity> captor = ArgumentCaptor.forClass(AiScoreSpeakerIdentity.class);
        verify(identityMapper).updateById(captor.capture());
        assertThat(captor.getValue().getRawSpeakerLabel()).isEqualTo("SPEAKER_1");
        assertThat(captor.getValue().getRevision()).isEqualTo(3);
    }

    @Test
    void refusesToCreateIdentityForSpeakerNotPresentInTranscript() {
        AiScoreSpeakerIdentityMapper identityMapper = mock(AiScoreSpeakerIdentityMapper.class);
        AiScoreTranscriptSegmentMapper segmentMapper = mock(AiScoreTranscriptSegmentMapper.class);
        when(segmentMapper.selectList(any())).thenReturn(List.of());
        AiScoreSpeakerIdentityService service = new AiScoreSpeakerIdentityService(identityMapper, segmentMapper);

        assertThatThrownBy(() -> service.confirm(26L, "SPEAKER_9", "未知", "", 7L))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("不存在");
        verify(identityMapper, never()).insert(any());
    }

    @Test
    void blankDisplayNameAndRoleAreRejected() {
        AiScoreSpeakerIdentityService service = new AiScoreSpeakerIdentityService(
                mock(AiScoreSpeakerIdentityMapper.class), mock(AiScoreTranscriptSegmentMapper.class)
        );

        assertThatThrownBy(() -> service.confirm(26L, "SPEAKER_1", "", "", 7L))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("姓名或角色");
    }
}
