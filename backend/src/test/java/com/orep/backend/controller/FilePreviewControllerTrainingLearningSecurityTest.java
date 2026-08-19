package com.orep.backend.controller;

import com.orep.backend.common.Result;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.test.util.ReflectionTestUtils;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class FilePreviewControllerTrainingLearningSecurityTest {
    @TempDir
    Path uploadRoot;

    @Test
    void genericPreviewCannotBypassControlledTrainingLearningDownload() throws Exception {
        Path file = uploadRoot.resolve("training/learning/51/document/demo.pdf");
        Files.createDirectories(file.getParent());
        Files.writeString(file, "%PDF-private");
        FilePreviewController controller = new FilePreviewController();
        ReflectionTestUtils.setField(controller, "uploadDir", uploadRoot.toString());

        Result<Map<String, Object>> result = controller.preview(
                "/uploads/training/learning/51/document/demo.pdf"
        );

        assertEquals(400, result.getCode());
        assertTrue(result.getMessage().contains("受控"));
    }
}
