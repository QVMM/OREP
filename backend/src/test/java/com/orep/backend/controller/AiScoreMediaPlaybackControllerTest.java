package com.orep.backend.controller;

import com.orep.backend.entity.AiScoreMediaAsset;
import com.orep.backend.entity.AiScoringSession;
import com.orep.backend.service.AiScoreAccessControlService;
import com.orep.backend.service.AiScoreMediaAssetService;
import com.orep.backend.service.AiScoringPipelineClient;
import com.orep.backend.service.AiScoringSessionService;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.test.web.servlet.MockMvc;

import java.nio.file.Files;
import java.nio.file.Path;

import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;
import static org.springframework.test.web.servlet.setup.MockMvcBuilders.standaloneSetup;

class AiScoreMediaPlaybackControllerTest {

    @TempDir
    Path tempDir;

    @Test
    void streamsRequestedVideoRangeAfterSessionAccessCheck() throws Exception {
        byte[] bytes = "0123456789abcdef".getBytes();
        Path file = tempDir.resolve("demo.mp4");
        Files.write(file, bytes);
        AiScoreMediaAsset asset = new AiScoreMediaAsset();
        asset.setId(77L);
        asset.setSessionId(101L);
        asset.setMimeType("video/mp4");
        AiScoreMediaAssetService.PlayableMedia playable =
                new AiScoreMediaAssetService.PlayableMedia(asset, file, bytes.length);

        AiScoringSessionService sessionService = mock(AiScoringSessionService.class);
        AiScoreMediaAssetService mediaService = mock(AiScoreMediaAssetService.class);
        AiScoreAccessControlService access = mock(AiScoreAccessControlService.class);
        AiScoringSession session = new AiScoringSession();
        session.setId(101L);
        when(sessionService.requireSessionForAccess(101L)).thenReturn(session);
        when(mediaService.requirePlayableVideo(101L)).thenReturn(playable);

        MockMvc mvc = standaloneSetup(new AiScoreUploadController(
                sessionService,
                mediaService,
                access,
                mock(AiScoringPipelineClient.class),
                tempDir.toString()
        )).build();

        mvc.perform(get("/api/ai-score/sessions/101/media/video")
                        .header("Range", "bytes=4-9")
                        .requestAttr("tenantId", 3L)
                        .requestAttr("userId", 7L)
                        .requestAttr("role", "STUDENT"))
                .andExpect(status().isPartialContent())
                .andExpect(header().string("Accept-Ranges", "bytes"))
                .andExpect(header().string("Content-Range", "bytes 4-9/16"))
                .andExpect(header().longValue("Content-Length", 6))
                .andExpect(content().bytes("456789".getBytes()));

        verify(access).assertSessionAccess(eq(session), eq(3L), eq(7L), eq("STUDENT"));
    }

    @Test
    void returnsRangeNotSatisfiableForOutOfBoundsRequest() throws Exception {
        byte[] bytes = "0123456789abcdef".getBytes();
        Path file = tempDir.resolve("demo.mp4");
        Files.write(file, bytes);
        AiScoreMediaAsset asset = new AiScoreMediaAsset();
        asset.setId(77L);
        asset.setSessionId(101L);
        asset.setMimeType("video/mp4");

        AiScoringSessionService sessionService = mock(AiScoringSessionService.class);
        AiScoreMediaAssetService mediaService = mock(AiScoreMediaAssetService.class);
        when(sessionService.requireSessionForAccess(101L)).thenReturn(new AiScoringSession());
        when(mediaService.requirePlayableVideo(101L)).thenReturn(
                new AiScoreMediaAssetService.PlayableMedia(asset, file, bytes.length));

        MockMvc mvc = standaloneSetup(new AiScoreUploadController(
                sessionService,
                mediaService,
                mock(AiScoreAccessControlService.class),
                mock(AiScoringPipelineClient.class),
                tempDir.toString()
        )).build();

        mvc.perform(get("/api/ai-score/sessions/101/media/video")
                        .header("Range", "bytes=99-120"))
                .andExpect(status().isRequestedRangeNotSatisfiable())
                .andExpect(header().string("Content-Range", "bytes */16"));
    }
}
