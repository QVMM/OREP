package com.orep.backend.service.roadshow;

import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class EvidenceTokenizerTest {

    @Test
    void extractsPercentAndCountFromScript() {
        List<Map<String, Object>> tokens = EvidenceTokenizer.extract(List.of(
                Map.of("id", "s4", "content", "三个试点大棚，从采到入库平均损耗 23%，钱主要耗在这一段。")
        ));
        assertTrue(tokens.stream().anyMatch(t -> "23%".equals(t.get("surface")) && "metric".equals(t.get("kind"))));
        assertTrue(tokens.stream().anyMatch(t -> String.valueOf(t.get("surface")).contains("3") && "s4".equals(t.get("stepId"))));
    }

    @Test
    void doesNotMintMoneyWithoutSource() {
        List<Map<String, Object>> tokens = EvidenceTokenizer.extract(List.of(
                Map.of("id", "s9", "content", "本项目可为农户节约 12 万，回本周期短。")
        ));
        assertFalse(tokens.stream().anyMatch(t -> String.valueOf(t.get("surface")).contains("12")));
        assertFalse(tokens.stream().anyMatch(t -> String.valueOf(t.get("surface")).contains("万")));
    }

    @Test
    void extractsContrastPair() {
        List<Map<String, Object>> tokens = EvidenceTokenizer.extract(List.of(
                Map.of("id", "s11", "content", "入库损耗从 23% 降到 9%，同一套秤。")
        ));
        assertTrue(tokens.stream().anyMatch(t -> "contrast".equals(t.get("kind"))
                && String.valueOf(t.get("surface")).contains("23%")
                && String.valueOf(t.get("surface")).contains("9%")));
    }
}
