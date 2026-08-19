package com.orep.backend.service.roadshow;

import org.junit.jupiter.api.Test;

import java.io.ByteArrayInputStream;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

import static org.junit.jupiter.api.Assertions.assertTrue;

class RoadshowPptxWriterTest {

    @Test
    void writesEditableTextNotImageSlide() throws Exception {
        byte[] bytes = RoadshowPptxWriter.write(List.of(
                Map.of("kicker", "问题", "title", "损耗发生在入库前", "number", "23%", "line", "三个试点")
        ));
        String slide = readEntry(bytes, "ppt/slides/slide1.xml");
        assertTrue(slide.contains("<a:t>损耗发生在入库前</a:t>"));
        assertTrue(slide.contains("<a:t>23%</a:t>"));
        assertTrue(!slide.contains("a:blip"));
        assertTrue(readEntry(bytes, "ppt/slides/slide1.xml").contains("<a:t>损耗发生在入库前</a:t>"));
        assertTrue(readEntry(bytes, "[Content_Types].xml").contains("presentationml.presentation"));
    }

    private static String readEntry(byte[] zip, String name) throws Exception {
        try (ZipInputStream in = new ZipInputStream(new ByteArrayInputStream(zip))) {
            ZipEntry e;
            while ((e = in.getNextEntry()) != null) {
                if (name.equals(e.getName())) {
                    return new String(in.readAllBytes(), StandardCharsets.UTF_8);
                }
            }
        }
        return "";
    }
}
