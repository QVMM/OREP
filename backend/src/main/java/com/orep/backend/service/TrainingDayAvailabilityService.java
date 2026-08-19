package com.orep.backend.service;

import org.springframework.stereotype.Service;

import java.sql.Date;
import java.sql.Timestamp;
import java.time.Clock;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.util.List;
import java.util.LinkedHashMap;
import java.util.Map;

@Service
public class TrainingDayAvailabilityService {
    private static final ZoneId SHANGHAI_ZONE = ZoneId.of("Asia/Shanghai");

    private final Clock clock;

    public TrainingDayAvailabilityService() {
        this(Clock.system(SHANGHAI_ZONE));
    }

    TrainingDayAvailabilityService(Clock clock) {
        this.clock = clock.withZone(SHANGHAI_ZONE);
    }

    public Map<String, Object> availability(String status, Object trainingDate, Object earlyUnlockedAt) {
        LocalDate date = localDate(trainingDate);
        LocalDateTime earlyUnlock = localDateTime(earlyUnlockedAt);
        LocalDateTime scheduledUnlock = date == null ? null : date.atStartOfDay();
        LocalDateTime effectiveUnlock = earlyUnlock == null ? scheduledUnlock : earlyUnlock;
        String normalizedStatus = String.valueOf(status).toUpperCase();
        boolean published = "PUBLISHED".equals(normalizedStatus) || "CLOSED".equals(normalizedStatus);
        boolean locked = !published
                || (earlyUnlock == null
                && (scheduledUnlock == null || LocalDateTime.now(clock).isBefore(scheduledUnlock)));

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("published", published);
        result.put("locked", locked);
        result.put("lockReason", !published ? "NOT_PUBLISHED" : locked ? "SCHEDULED" : null);
        result.put("scheduledUnlockAt", scheduledUnlock);
        result.put("earlyUnlockedAt", earlyUnlock);
        result.put("effectiveUnlockAt", effectiveUnlock);
        return result;
    }

    public void redactDraftPlaceholder(Map<String, Object> trainingDay) {
        if (!"DRAFT".equalsIgnoreCase(String.valueOf(trainingDay.get("status")))) {
            return;
        }
        for (String key : List.of(
                "title", "summary", "dueAt", "contentHtml",
                "tasks", "taskCount", "taskIds",
                "learningResources", "learningResourceCount", "requiredLearningCount",
                "estimatedLearningMinutes", "completedLearningCount",
                "attachments", "primaryTask"
        )) {
            trainingDay.remove(key);
        }
    }

    public Map<String, Object> availability(Map<String, Object> trainingDay) {
        return availability(
                String.valueOf(trainingDay.get("status")),
                trainingDay.get("trainingDate"),
                trainingDay.get("earlyUnlockedAt")
        );
    }

    public LocalDate today() {
        return LocalDate.now(clock);
    }

    public LocalDateTime now() {
        return LocalDateTime.now(clock);
    }

    private LocalDate localDate(Object value) {
        if (value instanceof LocalDate date) return date;
        if (value instanceof Date date) return date.toLocalDate();
        if (value instanceof LocalDateTime dateTime) return dateTime.toLocalDate();
        if (value instanceof Timestamp timestamp) return timestamp.toLocalDateTime().toLocalDate();
        if (value == null) return null;
        try {
            return LocalDate.parse(String.valueOf(value));
        } catch (RuntimeException ignored) {
            return null;
        }
    }

    private LocalDateTime localDateTime(Object value) {
        if (value instanceof LocalDateTime dateTime) return dateTime;
        if (value instanceof Timestamp timestamp) return timestamp.toLocalDateTime();
        if (value instanceof LocalDate date) return date.atStartOfDay();
        if (value instanceof Date date) return date.toLocalDate().atStartOfDay();
        if (value == null) return null;
        try {
            return LocalDateTime.parse(String.valueOf(value).replace(' ', 'T'));
        } catch (RuntimeException ignored) {
            return null;
        }
    }
}
