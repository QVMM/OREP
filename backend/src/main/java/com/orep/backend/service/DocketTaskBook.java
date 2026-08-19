package com.orep.backend.service;

/**
 * Published task book belongs to the docket, not a single rerun session.
 * Report snapshot wins when that run itself was published; otherwise the docket snapshot.
 */
public final class DocketTaskBook {
    private DocketTaskBook() {
    }

    public record Snapshot(boolean published, String json, Long publishedSessionId) {
        public Snapshot(boolean published, String json) {
            this(published, json, null);
        }

        public static Snapshot unpublished() {
            return new Snapshot(false, null, null);
        }
    }

    public static boolean flag(Object reportPublished, Object docketPublished) {
        return isTrue(reportPublished) || isTrue(docketPublished);
    }

    public static Snapshot resolve(
            Boolean reportPublished,
            String reportJson,
            Boolean docketPublished,
            String docketJson
    ) {
        if (isTrue(reportPublished) && hasText(reportJson)) {
            return new Snapshot(true, reportJson);
        }
        if (isTrue(docketPublished) && hasText(docketJson)) {
            return new Snapshot(true, docketJson);
        }
        return Snapshot.unpublished();
    }

    /**
     * Prior-round book only. A snapshot published by the current session is this round, not last round.
     */
    public static Snapshot prior(
            Boolean previousReportPublished,
            String previousReportJson,
            Boolean docketPublished,
            String docketJson,
            Long docketPublishedSessionId,
            Long currentSessionId
    ) {
        if (isTrue(previousReportPublished) && hasText(previousReportJson)) {
            return new Snapshot(true, previousReportJson, docketPublishedSessionId);
        }
        if (isTrue(docketPublished)
                && hasText(docketJson)
                && publishedBefore(docketPublishedSessionId, currentSessionId)) {
            return new Snapshot(true, docketJson, docketPublishedSessionId);
        }
        return Snapshot.unpublished();
    }

    /**
     * New tape = new docket. Fall back to the team's last published book on the same track.
     * A book published by the current docket this round must not fall back to an older docket.
     */
    public static Snapshot priorAcross(
            Snapshot sameDocketPrior,
            boolean sameDocketHasThisRoundBook,
            Snapshot teamTrackPrior,
            Long currentSessionId
    ) {
        if (sameDocketPrior != null && sameDocketPrior.published() && hasText(sameDocketPrior.json())) {
            return sameDocketPrior;
        }
        if (sameDocketHasThisRoundBook) {
            return Snapshot.unpublished();
        }
        if (teamTrackPrior != null
                && teamTrackPrior.published()
                && hasText(teamTrackPrior.json())
                && publishedBefore(teamTrackPrior.publishedSessionId(), currentSessionId)) {
            return teamTrackPrior;
        }
        return Snapshot.unpublished();
    }

    private static boolean publishedBefore(Long publishedSessionId, Long currentSessionId) {
        if (publishedSessionId == null || currentSessionId == null) {
            return false;
        }
        return publishedSessionId < currentSessionId;
    }

    private static boolean isTrue(Object value) {
        if (value instanceof Boolean bool) {
            return bool;
        }
        if (value instanceof Number number) {
            return number.intValue() != 0;
        }
        if (value == null) {
            return false;
        }
        String text = String.valueOf(value).trim();
        return "1".equals(text) || "true".equalsIgnoreCase(text);
    }

    private static boolean hasText(String value) {
        return value != null && !value.isBlank();
    }
}
