package com.orep.backend.service.roadshow.projection;

import java.util.List;
import java.util.Map;

public record ProjectionPageResult(
        int pageIndex,
        String intentId,
        String role,
        List<String> selectedStableIds,
        String slideText,
        String speaking,
        String taskFocus,
        boolean hardSuccessPass,
        String softSuccessStatus,
        String pageStatus,
        String blockReason,
        Map<String, Object> decision
) {
    public boolean blocked() {
        return "blocked".equals(pageStatus);
    }
}
