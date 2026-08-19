package com.orep.backend.service.roadshow;

import org.junit.jupiter.api.Test;

import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.assertTrue;

class SlidePreviewRendererTest {

    @Test
    void rendersTomatoCoverAsPng() throws Exception {
        Path pptx = Path.of(
                "/Users/liuyixing/项目/OREP/backend/uploads/roadshow/legacy/2026/08/18/66770919e8cc1b5490bbd253adc64322183643f818a4cd74080c27f77ca95cd0-original.pptx"
        );
        if (!Files.isRegularFile(pptx)) return;
        byte[] png = SlidePreviewRenderer.png(pptx, 1);
        assertTrue(png.length > 8000);
        assertTrue(png[0] == (byte) 0x89 && png[1] == 0x50 && png[2] == 0x4E && png[3] == 0x47);
    }
}
