package com.orep.backend.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Max |score_n - score_1| / dimMax across shared dimensions.
 * Missing max or missing first-run dim is skipped, not treated as 100% drift.
 */
public final class DimensionScoreDelta {
    private static final ObjectMapper MAPPER = new ObjectMapper();

    private DimensionScoreDelta() {
    }

    public static BigDecimal maxRatio(String firstJson, String currentJson) {
        Map<String, Dim> first = parse(firstJson);
        Map<String, Dim> current = parse(currentJson);
        if (first.isEmpty() || current.isEmpty()) {
            return null;
        }
        BigDecimal max = null;
        for (Map.Entry<String, Dim> entry : current.entrySet()) {
            Dim prior = first.get(entry.getKey());
            Dim now = entry.getValue();
            if (prior == null || now == null || now.max == null || now.max.compareTo(BigDecimal.ZERO) <= 0) {
                continue;
            }
            if (prior.score == null || now.score == null) {
                continue;
            }
            BigDecimal ratio = now.score.subtract(prior.score).abs()
                    .divide(now.max, 4, RoundingMode.HALF_UP);
            if (max == null || ratio.compareTo(max) > 0) {
                max = ratio;
            }
        }
        return max;
    }

    static Map<String, Dim> parse(String json) {
        Map<String, Dim> out = new LinkedHashMap<>();
        if (json == null || json.isBlank()) {
            return out;
        }
        try {
            JsonNode root = MAPPER.readTree(json);
            if (root == null || !root.isObject()) {
                return out;
            }
            Iterator<String> names = root.fieldNames();
            while (names.hasNext()) {
                String name = names.next();
                JsonNode node = root.get(name);
                Dim dim = readDim(node);
                if (dim != null) {
                    out.put(name, dim);
                }
            }
        } catch (Exception ignored) {
            return out;
        }
        return out;
    }

    private static Dim readDim(JsonNode node) {
        if (node == null || node.isNull()) {
            return null;
        }
        if (node.isNumber()) {
            return new Dim(decimal(node), null);
        }
        if (!node.isObject()) {
            return null;
        }
        JsonNode score = first(node, "score", "officialScore", "value");
        JsonNode max = first(node, "max_score", "maxScore", "scoreCap");
        if (score == null || !score.isNumber()) {
            return null;
        }
        return new Dim(decimal(score), max != null && max.isNumber() ? decimal(max) : null);
    }

    private static JsonNode first(JsonNode node, String... keys) {
        for (String key : keys) {
            if (node.has(key) && !node.get(key).isNull()) {
                return node.get(key);
            }
        }
        return null;
    }

    private static BigDecimal decimal(JsonNode node) {
        return node.decimalValue().setScale(4, RoundingMode.HALF_UP);
    }

    static final class Dim {
        final BigDecimal score;
        final BigDecimal max;

        Dim(BigDecimal score, BigDecimal max) {
            this.score = score;
            this.max = max;
        }
    }
}
