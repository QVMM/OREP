package com.orep.backend.service;

import com.orep.backend.entity.AiScoreMediaAsset;
import com.orep.backend.entity.MeetingRecording;
import com.orep.backend.mapper.AiScoreMediaAssetMapper;
import com.orep.backend.mapper.MeetingRecordingMapper;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.web.multipart.MultipartFile;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;

class AiScoreMediaAssetServiceTest {

    @TempDir
    Path tempDir;

    @Test
    void storesAllowedVideoAndComputesStableHash() throws Exception {
        AiScoreMediaAssetMapper mapper = mock(AiScoreMediaAssetMapper.class);
        doAnswer(invocation -> {
            AiScoreMediaAsset asset = invocation.getArgument(0);
            asset.setId(77L);
            return 1;
        }).when(mapper).insert(any(AiScoreMediaAsset.class));
        AiScoreMediaAssetService service = new AiScoreMediaAssetService(mapper, tempDir.toString());
        MockMultipartFile video = new MockMultipartFile(
                "video", "roadshow.mp4", "video/mp4", "video-content".getBytes());

        AiScoreMediaAsset first = service.storeVideo(101L, video, 7L);
        AiScoreMediaAsset second = service.storeVideo(101L, video, 7L);

        assertEquals("video", first.getAssetType());
        assertEquals("uploaded_video", first.getSourceType());
        assertEquals("uploaded", first.getStatus());
        assertTrue(first.getHasVideo());
        assertTrue(first.getHasAudio());
        assertEquals(first.getFileHash(), second.getFileHash());
        assertTrue(Files.exists(tempDir.resolve("ai-score/101").resolve(Path.of(first.getFilePath()).getFileName())));
        verify(mapper, times(2)).insert(any(AiScoreMediaAsset.class));
    }

    @Test
    void rejectsEmptyVideo() {
        AiScoreMediaAssetService service = new AiScoreMediaAssetService(mock(AiScoreMediaAssetMapper.class), tempDir.toString());
        MockMultipartFile video = new MockMultipartFile("video", "empty.mp4", "video/mp4", new byte[0]);

        IllegalArgumentException error = assertThrows(IllegalArgumentException.class,
                () -> service.storeVideo(101L, video, 7L));

        assertTrue(error.getMessage().contains("文件为空"));
    }

    @Test
    void rejectsUnsupportedVideoExtension() {
        AiScoreMediaAssetService service = new AiScoreMediaAssetService(mock(AiScoreMediaAssetMapper.class), tempDir.toString());
        MockMultipartFile video = new MockMultipartFile("video", "bad.exe", "application/octet-stream", "x".getBytes());

        IllegalArgumentException error = assertThrows(IllegalArgumentException.class,
                () -> service.storeVideo(101L, video, 7L));

        assertTrue(error.getMessage().contains("视频格式不支持"));
    }

    @Test
    void storesAllowedMaterial() throws Exception {
        AiScoreMediaAssetMapper mapper = mock(AiScoreMediaAssetMapper.class);
        AiScoreMediaAssetService service = new AiScoreMediaAssetService(mapper, tempDir.toString());
        MockMultipartFile material = new MockMultipartFile("materials", "bp.pdf", "application/pdf", "pdf".getBytes());

        AiScoreMediaAsset asset = service.storeMaterial(101L, material, 7L);

        assertEquals("material", asset.getAssetType());
        assertEquals("uploaded_video", asset.getSourceType());
        assertFalse(asset.getHasVideo());
        assertFalse(asset.getHasAudio());
        verify(mapper).insert(any(AiScoreMediaAsset.class));
    }

    @Test
    void rejectsMaterialBatchAboveOneGigabyte() {
        AiScoreMediaAssetService service = new AiScoreMediaAssetService(
                mock(AiScoreMediaAssetMapper.class),
                tempDir.toString()
        );
        MultipartFile video = sizedFile("roadshow.mp4", 100L * 1024 * 1024);
        MultipartFile first = sizedFile("first.pdf", 180L * 1024 * 1024);
        MultipartFile second = sizedFile("second.pdf", 180L * 1024 * 1024);
        MultipartFile third = sizedFile("third.pdf", 180L * 1024 * 1024);
        MultipartFile fourth = sizedFile("fourth.pdf", 180L * 1024 * 1024);
        MultipartFile fifth = sizedFile("fifth.pdf", 180L * 1024 * 1024);
        MultipartFile sixth = sizedFile("sixth.pdf", 180L * 1024 * 1024);

        IllegalArgumentException error = assertThrows(
                IllegalArgumentException.class,
                () -> service.validateUploadBatch(video, List.of(first, second, third, fourth, fifth, sixth))
        );

        assertEquals("佐证材料合计最大1GB，请减少文件后重试", error.getMessage());
    }

    @Test
    void storeVideoBindsDocketWhenHashPresent() throws Exception {
        AiScoreMediaAssetMapper mapper = mock(AiScoreMediaAssetMapper.class);
        AiScoreDocketService docketService = mock(AiScoreDocketService.class);
        AiScoreMediaAssetService service = new AiScoreMediaAssetService(mapper, tempDir.toString(), docketService);
        MockMultipartFile video = new MockMultipartFile(
                "video", "roadshow.mp4", "video/mp4", "video-content".getBytes());

        AiScoreMediaAsset asset = service.storeVideo(101L, video, 7L);

        assertEquals("video", asset.getAssetType());
        assertNotNull(asset.getFileHash());
        assertFalse(asset.getFileHash().isBlank());
        verify(docketService).bindAfterVideoHash(eq(101L), eq(asset.getFileHash()));
    }

    @Test
    void storeMaterialDoesNotBindDocket() throws Exception {
        AiScoreMediaAssetMapper mapper = mock(AiScoreMediaAssetMapper.class);
        AiScoreDocketService docketService = mock(AiScoreDocketService.class);
        AiScoreMediaAssetService service = new AiScoreMediaAssetService(mapper, tempDir.toString(), docketService);
        MockMultipartFile material = new MockMultipartFile("materials", "bp.pdf", "application/pdf", "pdf".getBytes());

        service.storeMaterial(101L, material, 7L);

        verify(docketService, never()).bindAfterVideoHash(any(), any());
    }

    @Test
    void registerMeetingRecordingAssetHashesLocalFileAndBinds() throws Exception {
        AiScoreMediaAssetMapper mapper = mock(AiScoreMediaAssetMapper.class);
        AiScoreDocketService docketService = mock(AiScoreDocketService.class);
        Path recording = tempDir.resolve("recordings/meeting-7.webm");
        Files.createDirectories(recording.getParent());
        Files.write(recording, "meeting-bytes".getBytes());
        AiScoreMediaAssetService service = new AiScoreMediaAssetService(mapper, tempDir.toString(), docketService);

        AiScoreMediaAsset asset = service.registerMeetingRecordingAsset(
                101L, "recordings/meeting-7.webm", "meeting-7.webm", "video/webm", null, 7L);

        assertEquals("meeting_recording", asset.getAssetType());
        assertNotNull(asset.getFileHash());
        assertEquals(64, asset.getFileHash().length());
        assertEquals(13L, asset.getSizeBytes());
        verify(docketService).bindAfterVideoHash(101L, asset.getFileHash());
    }

    @Test
    void registerMeetingRecordingAssetSkipsMissingOrEscapedPaths() {
        AiScoreMediaAssetMapper mapper = mock(AiScoreMediaAssetMapper.class);
        AiScoreDocketService docketService = mock(AiScoreDocketService.class);
        AiScoreMediaAssetService service = new AiScoreMediaAssetService(mapper, tempDir.toString(), docketService);

        AiScoreMediaAsset missing = service.registerMeetingRecordingAsset(
                101L, "recordings/gone.webm", "gone.webm", "video/webm", 9L, 7L);
        assertNull(missing.getFileHash());
        assertEquals("hash_missing", missing.getStatus());
        assertEquals(9L, missing.getSizeBytes());

        AiScoreMediaAsset escaped = service.registerMeetingRecordingAsset(
                101L, "/etc/hosts", "hosts", "video/webm", 1L, 7L);
        assertNull(escaped.getFileHash());
        verify(docketService, never()).bindAfterVideoHash(any(), any());
    }

    @Test
    void registerMeetingRecordingAssetHashesObjectStoreKeyAndBinds() throws Exception {
        AiScoreMediaAssetMapper mapper = mock(AiScoreMediaAssetMapper.class);
        AiScoreDocketService docketService = mock(AiScoreDocketService.class);
        MinioService minioService = mock(MinioService.class);
        when(minioService.exists("recordings/meeting-9.webm")).thenReturn(true);
        when(minioService.download("recordings/meeting-9.webm"))
                .thenReturn(new java.io.ByteArrayInputStream("object-bytes".getBytes()));
        AiScoreMediaAssetService service = new AiScoreMediaAssetService(
                mapper, tempDir.toString(), docketService, minioService);

        AiScoreMediaAsset asset = service.registerMeetingRecordingAsset(
                101L, "recordings/meeting-9.webm", "meeting-9.webm", "video/webm", null, 7L);

        assertNotNull(asset.getFileHash());
        assertEquals(64, asset.getFileHash().length());
        assertEquals(12L, asset.getSizeBytes());
        verify(docketService).bindAfterVideoHash(101L, asset.getFileHash());
    }

    @Test
    void registerMeetingRecordingAssetDoesNotAskObjectStoreForEscapedPaths() throws Exception {
        AiScoreMediaAssetMapper mapper = mock(AiScoreMediaAssetMapper.class);
        MinioService minioService = mock(MinioService.class);
        AiScoreMediaAssetService service = new AiScoreMediaAssetService(
                mapper, tempDir.toString(), mock(AiScoreDocketService.class), minioService);

        AiScoreMediaAsset escaped = service.registerMeetingRecordingAsset(
                101L, "/etc/hosts", "hosts", "video/webm", 1L, 7L);
        assertNull(escaped.getFileHash());
        verify(minioService, never()).exists(any());
        verify(minioService, never()).download(any());
    }

    @Test
    void registerMeetingRecordingForSessionUsesReadyObjectKeyAndBinds() throws Exception {
        AiScoreMediaAssetMapper mapper = mock(AiScoreMediaAssetMapper.class);
        AiScoreDocketService docketService = mock(AiScoreDocketService.class);
        MeetingRecordingMapper recordingMapper = mock(MeetingRecordingMapper.class);
        MinioService minioService = mock(MinioService.class);
        when(minioService.exists("recordings/meeting-11.webm")).thenReturn(true);
        when(minioService.download("recordings/meeting-11.webm"))
                .thenReturn(new java.io.ByteArrayInputStream("ready-bytes".getBytes()));
        MeetingRecording recording = new MeetingRecording();
        recording.setId(11L);
        recording.setMeetingId(12L);
        recording.setStatus("READY");
        recording.setFilePath("recordings/meeting-11.webm");
        recording.setMimeType("video/webm");
        recording.setSizeBytes(11L);
        when(recordingMapper.selectById(11L)).thenReturn(recording);
        AiScoreMediaAssetService service = new AiScoreMediaAssetService(
                mapper, tempDir.toString(), docketService, minioService);
        service.setMeetingRecordingMapper(recordingMapper);

        AiScoreMediaAsset asset = service.registerMeetingRecordingForSession(101L, 11L, 12L, 7L);

        assertEquals("uploaded", asset.getStatus());
        assertEquals(64, asset.getFileHash().length());
        verify(docketService).bindAfterVideoHash(eq(101L), eq(asset.getFileHash()));
    }

    @Test
    void registerMeetingRecordingForSessionReturnsNullWhenNoRecording() {
        AiScoreMediaAssetMapper mapper = mock(AiScoreMediaAssetMapper.class);
        MeetingRecordingMapper recordingMapper = mock(MeetingRecordingMapper.class);
        when(recordingMapper.selectByMeetingId(12L)).thenReturn(List.of());
        AiScoreMediaAssetService service = new AiScoreMediaAssetService(mapper, tempDir.toString());
        service.setMeetingRecordingMapper(recordingMapper);

        assertNull(service.registerMeetingRecordingForSession(101L, null, 12L, 7L));
        verify(mapper, never()).insert(any());
    }

    @Test
    void registerMeetingRecordingAssetLeavesHashNullWhenObjectMissing() throws Exception {
        AiScoreMediaAssetMapper mapper = mock(AiScoreMediaAssetMapper.class);
        AiScoreDocketService docketService = mock(AiScoreDocketService.class);
        MinioService minioService = mock(MinioService.class);
        when(minioService.exists("recordings/gone.webm")).thenReturn(false);
        AiScoreMediaAssetService service = new AiScoreMediaAssetService(
                mapper, tempDir.toString(), docketService, minioService);

        AiScoreMediaAsset missing = service.registerMeetingRecordingAsset(
                101L, "recordings/gone.webm", "gone.webm", "video/webm", 9L, 7L);
        assertNull(missing.getFileHash());
        assertEquals("hash_missing", missing.getStatus());
        assertEquals(9L, missing.getSizeBytes());
        verify(minioService, never()).download(any());
        verify(docketService, never()).bindAfterVideoHash(any(), any());
    }

    @Test
    void opensOnlyTheRequestedPlayableVideoRange() throws Exception {
        AiScoreMediaAssetMapper mapper = mock(AiScoreMediaAssetMapper.class);
        byte[] bytes = "0123456789abcdef".getBytes();
        Path media = tempDir.resolve("ai-score/101/demo.mp4");
        Files.createDirectories(media.getParent());
        Files.write(media, bytes);
        AiScoreMediaAsset asset = new AiScoreMediaAsset();
        asset.setId(77L);
        asset.setSessionId(101L);
        asset.setAssetType("video");
        asset.setFilePath("ai-score/101/demo.mp4");
        asset.setMimeType("video/mp4");
        asset.setSizeBytes((long) bytes.length);
        when(mapper.selectOne(any())).thenReturn(asset);

        AiScoreMediaAssetService service = new AiScoreMediaAssetService(mapper, tempDir.toString());
        AiScoreMediaAssetService.PlayableMedia playable = service.requirePlayableVideo(101L);

        assertEquals(77L, playable.asset().getId());
        assertEquals(bytes.length, playable.sizeBytes());
        try (var input = playable.openRange(4, 6)) {
            assertArrayEquals(Arrays.copyOfRange(bytes, 4, 10), input.readAllBytes());
        }
    }

    @Test
    void rejectsPlayableAssetThatEscapesUploadRoot() {
        AiScoreMediaAssetMapper mapper = mock(AiScoreMediaAssetMapper.class);
        AiScoreMediaAsset asset = new AiScoreMediaAsset();
        asset.setId(77L);
        asset.setSessionId(101L);
        asset.setAssetType("video");
        asset.setFilePath("../../private.mp4");
        when(mapper.selectOne(any())).thenReturn(asset);

        AiScoreMediaAssetService service = new AiScoreMediaAssetService(mapper, tempDir.toString());

        assertThrows(IllegalArgumentException.class, () -> service.requirePlayableVideo(101L));
    }

    private MultipartFile sizedFile(String name, long size) {
        MultipartFile file = mock(MultipartFile.class);
        when(file.isEmpty()).thenReturn(false);
        when(file.getOriginalFilename()).thenReturn(name);
        when(file.getSize()).thenReturn(size);
        return file;
    }
}
