package com.orep.backend.service.roadshow.projection;

import java.util.List;

public record PageIntentSpec(
        String id,
        int pageIndex,
        String role,
        int requiredImpactMin,
        int requiredOstensibleMin,
        boolean requireBridge,
        boolean forbidTech,
        List<String> relatedRubrics
) {
    public static PageIntentSpec urgency() {
        return new PageIntentSpec(
                "intent_urgency", 4, "urgency",
                4, 4, false, true, List.of("实用性"));
    }

    public static PageIntentSpec bridge() {
        return new PageIntentSpec(
                "intent_bridge", 5, "bridge",
                0, 0, true, true, List.of("实用性"));
    }
}
