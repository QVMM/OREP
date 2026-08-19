package com.orep.backend.service;

import com.orep.backend.dto.AiScoreEvidenceBundleResponse;
import com.orep.backend.entity.AiScoreEvidenceAnchor;
import com.orep.backend.entity.AiScoreEvidenceSnapshot;
import com.orep.backend.entity.AiScoreFrame;
import com.orep.backend.entity.AiScoreMediaAsset;
import com.orep.backend.entity.AiScoreTranscriptSegment;
import com.orep.backend.mapper.AiScoreEvidenceAnchorMapper;
import com.orep.backend.mapper.AiScoreEvidenceSnapshotMapper;
import com.orep.backend.mapper.AiScoreFrameMapper;
import com.orep.backend.mapper.AiScoreMediaAssetMapper;
import com.orep.backend.mapper.AiScoreTranscriptSegmentMapper;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.atLeast;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class AiScoreEvidenceBundleServiceTest {

    @Test
    void prepareEvidenceFreezesOnlyRealMediaAndDoesNotInventTranscriptOrFrames() {
        AiScoreMediaAssetMapper mediaMapper = mock(AiScoreMediaAssetMapper.class);
        AiScoreTranscriptSegmentMapper segmentMapper = mock(AiScoreTranscriptSegmentMapper.class);
        AiScoreFrameMapper frameMapper = mock(AiScoreFrameMapper.class);
        AiScoreEvidenceAnchorMapper anchorMapper = mock(AiScoreEvidenceAnchorMapper.class);
        AiScoreEvidenceSnapshotMapper snapshotMapper = mock(AiScoreEvidenceSnapshotMapper.class);

        AiScoreMediaAsset video = uploadedVideo();
        when(mediaMapper.selectList(any())).thenReturn(List.of(video));
        when(segmentMapper.insert(any())).thenAnswer(invocation -> {
            AiScoreTranscriptSegment value = invocation.getArgument(0);
            value.setId((long) value.getSegmentNo());
            return 1;
        });
        when(frameMapper.insert(any())).thenAnswer(invocation -> {
            AiScoreFrame value = invocation.getArgument(0);
            value.setId((long) value.getFrameNo());
            return 1;
        });
        when(anchorMapper.insert(any())).thenReturn(1);
        when(snapshotMapper.insert(any())).thenAnswer(invocation -> {
            AiScoreEvidenceSnapshot value = invocation.getArgument(0);
            value.setId(901L);
            return 1;
        });

        AiScoreEvidenceBundleService service = new AiScoreEvidenceBundleService(
                mediaMapper, segmentMapper, frameMapper, anchorMapper, snapshotMapper
        );

        AiScoreEvidenceBundleResponse response = service.prepareEvidence(101L);

        assertEquals(101L, response.getSessionId());
        assertEquals(901L, response.getSnapshotId());
        assertEquals("ready", response.getSnapshotStatus());
        assertEquals(1, response.getMediaAssetCount());
        assertEquals(0, response.getTranscriptSegmentCount());
        assertEquals(0, response.getFrameCount());
        assertEquals(0, response.getEvidenceAnchorCount());
        assertNotNull(response.getAsrSnapshotHash());
        assertNotNull(response.getFrameSnapshotHash());
        assertNotNull(response.getOcrSnapshotHash());
        assertNotNull(response.getMediaAssetHash());
        assertNotNull(response.getMaterialSnapshotHash());

        verify(segmentMapper, never()).insert(any());
        verify(frameMapper, never()).insert(any());
        verify(anchorMapper, never()).insert(any());

        ArgumentCaptor<AiScoreEvidenceSnapshot> snapshotCaptor = ArgumentCaptor.forClass(AiScoreEvidenceSnapshot.class);
        verify(snapshotMapper).insert(snapshotCaptor.capture());
        assertEquals("ready", snapshotCaptor.getValue().getSnapshotStatus());
        assertEquals(response.getAsrSnapshotHash(), snapshotCaptor.getValue().getAsrSnapshotHash());
        assertEquals(response.getFrameSnapshotHash(), snapshotCaptor.getValue().getFrameSnapshotHash());
    }

    @Test
    void prepareEvidenceRejectsSessionWithoutUploadedMediaAssets() {
        AiScoreMediaAssetMapper mediaMapper = mock(AiScoreMediaAssetMapper.class);
        when(mediaMapper.selectList(any())).thenReturn(List.of());

        AiScoreEvidenceBundleService service = new AiScoreEvidenceBundleService(
                mediaMapper,
                mock(AiScoreTranscriptSegmentMapper.class),
                mock(AiScoreFrameMapper.class),
                mock(AiScoreEvidenceAnchorMapper.class),
                mock(AiScoreEvidenceSnapshotMapper.class)
        );

        IllegalStateException error = assertThrows(IllegalStateException.class, () -> service.prepareEvidence(101L));
        assertTrue(error.getMessage().contains("未找到可用媒体资产"));
    }

    @Test
    void prepareEvidenceCanRegenerateSameSessionWithStableHashes() {
        AiScoreMediaAssetMapper mediaMapper = mock(AiScoreMediaAssetMapper.class);
        AiScoreTranscriptSegmentMapper segmentMapper = mock(AiScoreTranscriptSegmentMapper.class);
        AiScoreFrameMapper frameMapper = mock(AiScoreFrameMapper.class);
        AiScoreEvidenceAnchorMapper anchorMapper = mock(AiScoreEvidenceAnchorMapper.class);
        AiScoreEvidenceSnapshotMapper snapshotMapper = mock(AiScoreEvidenceSnapshotMapper.class);

        when(mediaMapper.selectList(any())).thenReturn(List.of(uploadedVideo()));
        when(segmentMapper.insert(any())).thenAnswer(invocation -> {
            AiScoreTranscriptSegment value = invocation.getArgument(0);
            value.setId((long) value.getSegmentNo());
            return 1;
        });
        when(frameMapper.insert(any())).thenAnswer(invocation -> {
            AiScoreFrame value = invocation.getArgument(0);
            value.setId((long) value.getFrameNo());
            return 1;
        });
        when(anchorMapper.insert(any())).thenReturn(1);
        when(snapshotMapper.insert(any())).thenAnswer(invocation -> {
            AiScoreEvidenceSnapshot value = invocation.getArgument(0);
            value.setId(900L + value.getSessionId());
            return 1;
        });
        AiScoreEvidenceBundleService service = new AiScoreEvidenceBundleService(
                mediaMapper, segmentMapper, frameMapper, anchorMapper, snapshotMapper
        );

        AiScoreEvidenceBundleResponse first = service.prepareEvidence(101L);
        AiScoreEvidenceBundleResponse second = service.prepareEvidence(101L);

        assertEquals(first.getMediaAssetHash(), second.getMediaAssetHash());
        assertEquals(first.getAsrSnapshotHash(), second.getAsrSnapshotHash());
        assertEquals(first.getFrameSnapshotHash(), second.getFrameSnapshotHash());
        assertEquals(first.getOcrSnapshotHash(), second.getOcrSnapshotHash());
        assertEquals(first.getMaterialSnapshotHash(), second.getMaterialSnapshotHash());
        verify(anchorMapper, times(2)).delete(any());
        verify(segmentMapper, times(2)).delete(any());
        verify(frameMapper, times(2)).delete(any());
        verify(snapshotMapper, times(2)).delete(any());
    }

    @Test
    void latestBundleReturnsMissingWhenNoSnapshotExists() {
        AiScoreEvidenceSnapshotMapper snapshotMapper = mock(AiScoreEvidenceSnapshotMapper.class);
        when(snapshotMapper.selectOne(any())).thenReturn(null);
        AiScoreEvidenceBundleService service = new AiScoreEvidenceBundleService(
                mock(AiScoreMediaAssetMapper.class),
                mock(AiScoreTranscriptSegmentMapper.class),
                mock(AiScoreFrameMapper.class),
                mock(AiScoreEvidenceAnchorMapper.class),
                snapshotMapper
        );

        AiScoreEvidenceBundleResponse response = service.latestBundle(101L);

        assertEquals(101L, response.getSessionId());
        assertEquals("missing", response.getSnapshotStatus());
        assertEquals(0, response.getMediaAssetCount());
        assertEquals(0, response.getTranscriptSegmentCount());
        assertEquals(0, response.getFrameCount());
        assertEquals(0, response.getEvidenceAnchorCount());
    }

    @Test
    void latestBundleReturnsLatestSnapshotHashesAndCounts() {
        AiScoreMediaAssetMapper mediaMapper = mock(AiScoreMediaAssetMapper.class);
        AiScoreTranscriptSegmentMapper segmentMapper = mock(AiScoreTranscriptSegmentMapper.class);
        AiScoreFrameMapper frameMapper = mock(AiScoreFrameMapper.class);
        AiScoreEvidenceAnchorMapper anchorMapper = mock(AiScoreEvidenceAnchorMapper.class);
        AiScoreEvidenceSnapshotMapper snapshotMapper = mock(AiScoreEvidenceSnapshotMapper.class);
        AiScoreEvidenceSnapshot snapshot = new AiScoreEvidenceSnapshot();
        snapshot.setId(902L);
        snapshot.setSessionId(101L);
        snapshot.setSnapshotStatus("ready");
        snapshot.setMediaAssetHash("media-hash");
        snapshot.setAsrSnapshotHash("asr-hash");
        snapshot.setFrameSnapshotHash("frame-hash");
        snapshot.setOcrSnapshotHash("ocr-hash");
        snapshot.setMaterialSnapshotHash("material-hash");
        when(snapshotMapper.selectOne(any())).thenReturn(snapshot);
        when(mediaMapper.selectCount(any())).thenReturn(2L);
        when(segmentMapper.selectCount(any())).thenReturn(3L);
        when(frameMapper.selectCount(any())).thenReturn(3L);
        when(anchorMapper.selectCount(any())).thenReturn(6L);
        AiScoreEvidenceBundleService service = new AiScoreEvidenceBundleService(
                mediaMapper, segmentMapper, frameMapper, anchorMapper, snapshotMapper
        );

        AiScoreEvidenceBundleResponse response = service.latestBundle(101L);

        assertEquals(902L, response.getSnapshotId());
        assertEquals("ready", response.getSnapshotStatus());
        assertEquals(2, response.getMediaAssetCount());
        assertEquals(3, response.getTranscriptSegmentCount());
        assertEquals(3, response.getFrameCount());
        assertEquals(6, response.getEvidenceAnchorCount());
        assertEquals("media-hash", response.getMediaAssetHash());
        assertEquals("asr-hash", response.getAsrSnapshotHash());
        assertEquals("frame-hash", response.getFrameSnapshotHash());
        assertEquals("ocr-hash", response.getOcrSnapshotHash());
        assertEquals("material-hash", response.getMaterialSnapshotHash());
    }

    private AiScoreMediaAsset uploadedVideo() {
        AiScoreMediaAsset video = new AiScoreMediaAsset();
        video.setId(11L);
        video.setSessionId(101L);
        video.setAssetType("video");
        video.setSourceType("uploaded_video");
        video.setOriginalName("roadshow.mp4");
        video.setFilePath("uploads/ai-score/101/roadshow.mp4");
        video.setFileHash("hash-video");
        video.setHasAudio(true);
        video.setHasVideo(true);
        video.setStatus("uploaded");
        return video;
    }
}
