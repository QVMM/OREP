package com.orep.backend.service.roadshow;

import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertTrue;

class SlideTextPatcherTest {

    @Test
    void replacesVisibleText() {
        String xml = "<p:sld><a:t>损耗发生在入库前</a:t><a:t>23%</a:t></p:sld>";
        String next = SlideTextPatcher.patch(xml, List.of("损耗发生在入库前", "23%"), List.of("损耗发生在入库前", "9%"));
        assertTrue(next.contains("<a:t>9%</a:t>"));
        assertTrue(next.contains("损耗发生在入库前"));
        assertTrue(!next.contains("<a:t>23%</a:t>"));
    }
}
