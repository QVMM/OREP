package com.orep.backend.service.roadshow.projection;

public record AssessmentRecord(
        String claimStableId,
        String rubricId,
        int strength,
        int verifiability,
        int chi,
        long createdByRunId,
        String createdByPageIntentId,
        String createdForRubricId
) {
}
