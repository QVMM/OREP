package com.orep.backend.service;

import com.orep.backend.entity.AiScoreMediaPreprocessJob;
import com.orep.backend.mapper.AiScoreMediaPreprocessJobMapper;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.web.multipart.MultipartFile;

import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class AiScoreMediaPreprocessServiceTest {

    @TempDir
    Path tempDir;

    @Test
    void rejectsSourceVideoAboveFiveGigabytes() {
        AiScoreMediaPreprocessService service = new AiScoreMediaPreprocessService(
                mock(AiScoreMediaPreprocessJobMapper.class),
                mock(AiScoringSessionService.class),
                mock(AiScoreMediaAssetService.class),
                tempDir.toString(),
                "ffmpeg"
        );
        MultipartFile video = mock(MultipartFile.class);
        when(video.isEmpty()).thenReturn(false);
        when(video.getSize()).thenReturn(5L * 1024 * 1024 * 1024 + 1);

        try {
            IllegalArgumentException error = assertThrows(
                    IllegalArgumentException.class,
                    () -> service.createJob(video, 1L, 1L, null, "新一代信息技术赛道", true, false, 1L)
            );
            assertEquals("源视频超过 5GB，请压缩后上传", error.getMessage());
        } finally {
            service.destroy();
        }
    }

    @Test
    void statusHidesJobsOwnedBySomeoneElse() {
        AiScoreMediaPreprocessJobMapper mapper = mock(AiScoreMediaPreprocessJobMapper.class);
        AiScoreMediaPreprocessJob job = new AiScoreMediaPreprocessJob();
        job.setId(9L);
        job.setCreatedBy(7L);
        job.setStatus("queued");
        when(mapper.selectById(9L)).thenReturn(job);
        AiScoreMediaPreprocessService service = new AiScoreMediaPreprocessService(
                mapper,
                mock(AiScoringSessionService.class),
                mock(AiScoreMediaAssetService.class),
                tempDir.toString(),
                "ffmpeg"
        );
        try {
            IllegalStateException error = assertThrows(
                    IllegalStateException.class,
                    () -> service.status(9L, 10L)
            );
            assertEquals("预处理任务不存在", error.getMessage());
        } finally {
            service.destroy();
        }
    }
}
