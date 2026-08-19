package com.orep.backend.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.orep.backend.entity.AiScoreRemediationTask;
import com.orep.backend.entity.AiScoreTaskLossLink;
import com.orep.backend.entity.AiScoreTaskVerification;
import com.orep.backend.mapper.AiScoreRemediationTaskMapper;
import com.orep.backend.mapper.AiScoreTaskLossLinkMapper;
import com.orep.backend.mapper.AiScoreTaskVerificationMapper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

@Service
public class AiScoreRemediationService {
    private static final Map<String, Set<String>> USER_TRANSITIONS = Map.of(
            "not_started", Set.of("in_progress"),
            "in_progress", Set.of("not_started", "submitted"),
            "submitted", Set.of("awaiting_rerun"),
            "awaiting_rerun", Set.of("in_progress")
    );
    private final AiScoreRemediationTaskMapper taskMapper;
    private final AiScoreTaskLossLinkMapper linkMapper;
    private final AiScoreTaskVerificationMapper verificationMapper;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public AiScoreRemediationService(
            AiScoreRemediationTaskMapper taskMapper,
            AiScoreTaskLossLinkMapper linkMapper,
            AiScoreTaskVerificationMapper verificationMapper
    ) {
        this.taskMapper = taskMapper;
        this.linkMapper = linkMapper;
        this.verificationMapper = verificationMapper;
    }

    @Transactional
    public void persistSnapshot(
            String projectScopeKey,
            Long reportId,
            String actionPlanJson,
            String lossLedgerJson
    ) {
        persistSnapshot(projectScopeKey, reportId, null, actionPlanJson, lossLedgerJson, null);
    }

    @Transactional
    public void persistSnapshot(
            String projectScopeKey,
            Long reportId,
            Long currentSessionId,
            String actionPlanJson,
            String lossLedgerJson,
            String coverageSummaryJson
    ) {
        List<Map<String, Object>> tasks = readArray(actionPlanJson, "actionPlanJson");
        List<Map<String, Object>> losses = readArray(lossLedgerJson, "lossLedgerJson");
        List<PreviousTaskState> awaitingTasks = awaitingTaskStates(projectScopeKey);
        Map<String, Map<String, Object>> lossById = new LinkedHashMap<>();
        for (Map<String, Object> loss : losses) {
            String lossId = text(loss.get("lossId"));
            if (!lossId.isBlank()) {
                lossById.put(lossId, loss);
            }
        }
        for (Map<String, Object> taskSnapshot : tasks) {
            AiScoreRemediationTask task = upsertTask(projectScopeKey, reportId, taskSnapshot);
            replaceLossLinks(reportId, task, taskSnapshot, lossById);
        }
        if (currentSessionId != null) {
            verifyAwaitingTasks(reportId, currentSessionId, coverageSummaryJson, losses, awaitingTasks);
        }
    }

    String verificationStatus(BigDecimal previousPoints, BigDecimal currentPoints) {
        BigDecimal before = previousPoints == null ? BigDecimal.ZERO : previousPoints;
        BigDecimal after = currentPoints == null ? BigDecimal.ZERO : currentPoints;
        if (before.signum() == 0 && after.signum() > 0) {
            return "regressed";
        }
        if (before.signum() > 0 && after.signum() == 0) {
            return "verified";
        }
        if (before.signum() > 0 && after.compareTo(before) < 0) {
            return "partial";
        }
        return "failed";
    }

    public List<Map<String, Object>> liveTasksForReport(Long reportId, String actionPlanJson) {
        List<Map<String, Object>> snapshots = readArray(actionPlanJson, "actionPlanJson");
        List<AiScoreRemediationTask> liveRows = taskMapper.selectList(
                new LambdaQueryWrapper<AiScoreRemediationTask>()
                        .and(wrapper -> wrapper
                                .eq(AiScoreRemediationTask::getSourceReportId, reportId)
                                .or()
                                .eq(AiScoreRemediationTask::getLatestReportId, reportId))
                        .orderByAsc(AiScoreRemediationTask::getId)
        );
        Map<String, AiScoreRemediationTask> liveByKey = new LinkedHashMap<>();
        for (AiScoreRemediationTask row : liveRows == null ? List.<AiScoreRemediationTask>of() : liveRows) {
            liveByKey.put(row.getTaskKey(), row);
        }
        return snapshots.stream().map(snapshot -> {
            Map<String, Object> result = new LinkedHashMap<>(snapshot);
            AiScoreRemediationTask live = liveByKey.get(text(snapshot.get("taskId")));
            if (live != null) {
                result.put("taskRecordId", live.getId());
                result.put("status", live.getStatus());
            }
            return result;
        }).toList();
    }

    public List<Map<String, Object>> verificationsForReport(Long reportId) {
        List<AiScoreTaskVerification> rows = verificationMapper.selectList(
                new LambdaQueryWrapper<AiScoreTaskVerification>()
                        .eq(AiScoreTaskVerification::getReportId, reportId)
                        .orderByAsc(AiScoreTaskVerification::getId)
        );
        return (rows == null ? List.<AiScoreTaskVerification>of() : rows).stream().map(row -> {
            Map<String, Object> value = new LinkedHashMap<>();
            value.put("taskRecordId", row.getTaskId());
            value.put("sourceSessionId", row.getSourceSessionId());
            value.put("verificationSessionId", row.getVerificationSessionId());
            value.put("status", row.getStatus());
            value.put("minimumAcceptancePassed", row.getMinimumPassed());
            value.put("fullScoreCriteriaPassed", row.getFullScorePassed());
            value.put("reason", row.getReason());
            value.put("ruleComparable", row.getRuleComparable());
            value.put("verifiedAt", row.getVerifiedAt());
            return value;
        }).toList();
    }

    @Transactional
    public Map<String, Object> updateUserTaskStatus(Long reportId, Long taskId, String requestedStatus) {
        AiScoreRemediationTask task = taskMapper.selectById(taskId);
        if (task == null || (!reportId.equals(task.getSourceReportId()) && !reportId.equals(task.getLatestReportId()))) {
            throw new IllegalArgumentException("remediation task does not belong to report");
        }
        String current = defaulted(task.getStatus(), "not_started");
        String requested = text(requestedStatus);
        if (!USER_TRANSITIONS.getOrDefault(current, Set.of()).contains(requested)) {
            throw new IllegalArgumentException("task status transition " + current + " -> " + requested + " is not allowed");
        }
        task.setStatus(requested);
        task.setUpdatedAt(LocalDateTime.now());
        taskMapper.updateById(task);
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("taskRecordId", task.getId());
        result.put("taskId", task.getTaskKey());
        result.put("status", task.getStatus());
        return result;
    }

    private List<PreviousTaskState> awaitingTaskStates(String projectScopeKey) {
        List<AiScoreRemediationTask> rows = taskMapper.selectList(
                new LambdaQueryWrapper<AiScoreRemediationTask>()
                        .eq(AiScoreRemediationTask::getProjectScopeKey, projectScopeKey)
                        .eq(AiScoreRemediationTask::getStatus, "awaiting_rerun")
        );
        if (rows == null) {
            return List.of();
        }
        return rows.stream().map(row -> new PreviousTaskState(
                row.getId(),
                row.getLatestReportId(),
                row.getTaskJson(),
                row
        )).toList();
    }

    private void verifyAwaitingTasks(
            Long currentReportId,
            Long currentSessionId,
            String coverageSummaryJson,
            List<Map<String, Object>> currentLosses,
            List<PreviousTaskState> awaitingTasks
    ) {
        if (awaitingTasks.isEmpty()) {
            return;
        }
        Map<String, BigDecimal> currentPointsByLossKey = new LinkedHashMap<>();
        Map<String, Map<String, Object>> currentLossByKey = new LinkedHashMap<>();
        for (Map<String, Object> loss : currentLosses) {
            String lossKey = text(loss.get("lossKey"));
            if (lossKey.isBlank()) {
                continue;
            }
            currentPointsByLossKey.merge(lossKey, decimal(loss.get("points")), BigDecimal::add);
            currentLossByKey.put(lossKey, loss);
        }
        String currentRuleHash = text(readObject(coverageSummaryJson).get("ruleHash"));
        if (currentRuleHash.isBlank() && !currentLosses.isEmpty()) {
            currentRuleHash = text(currentLosses.getFirst().get("ruleHash"));
        }

        for (PreviousTaskState previous : awaitingTasks) {
            if (previous.latestReportId() == null || previous.latestReportId().equals(currentReportId)) {
                continue;
            }
            List<AiScoreTaskLossLink> previousLinks = linkMapper.selectList(
                    new LambdaQueryWrapper<AiScoreTaskLossLink>()
                            .eq(AiScoreTaskLossLink::getReportId, previous.latestReportId())
                            .eq(AiScoreTaskLossLink::getTaskId, previous.taskId())
            );
            previousLinks = previousLinks == null ? List.of() : previousLinks;
            String previousRuleHash = taskRuleHash(previous.taskJson());
            boolean comparable = !currentRuleHash.isBlank() && currentRuleHash.equals(previousRuleHash) && !previousLinks.isEmpty();
            BigDecimal before = previousLinks.stream()
                    .map(AiScoreTaskLossLink::getGapPoints)
                    .filter(value -> value != null)
                    .reduce(BigDecimal.ZERO, BigDecimal::add);
            BigDecimal after = previousLinks.stream()
                    .map(AiScoreTaskLossLink::getLossKey)
                    .map(key -> currentPointsByLossKey.getOrDefault(key, BigDecimal.ZERO))
                    .reduce(BigDecimal.ZERO, BigDecimal::add);
            String status = comparable ? verificationStatus(before, after) : "not_observable";
            AiScoreTaskVerification verification = new AiScoreTaskVerification();
            verification.setTaskId(previous.taskId());
            verification.setSourceSessionId(null);
            verification.setVerificationSessionId(currentSessionId);
            verification.setReportId(currentReportId);
            verification.setStatus(status);
            verification.setMinimumPassed("verified".equals(status) || "partial".equals(status));
            verification.setFullScorePassed("verified".equals(status));
            verification.setEvidenceAnchorIdsJson(writeJson(currentEvidenceAnchorIds(previousLinks, currentLossByKey)));
            verification.setPreviousStateJson(writeJson(pointsState(previousLinks, null)));
            verification.setCurrentStateJson(writeJson(pointsState(previousLinks, currentPointsByLossKey)));
            verification.setReason(verificationReason(status, before, after));
            verification.setRuleComparable(comparable);
            verification.setVerifiedAt(LocalDateTime.now());
            verification.setCreatedAt(LocalDateTime.now());
            AiScoreTaskVerification existing = verificationMapper.selectOne(
                    new LambdaQueryWrapper<AiScoreTaskVerification>()
                            .eq(AiScoreTaskVerification::getTaskId, previous.taskId())
                            .eq(AiScoreTaskVerification::getVerificationSessionId, currentSessionId)
                            .last("LIMIT 1")
            );
            if (existing == null) {
                verificationMapper.insert(verification);
            } else {
                verification.setId(existing.getId());
                verificationMapper.updateById(verification);
            }
            AiScoreRemediationTask task = previous.task();
            task.setStatus(status);
            task.setLatestReportId(currentReportId);
            task.setUpdatedAt(LocalDateTime.now());
            taskMapper.updateById(task);
        }
    }

    private Map<String, Object> pointsState(
            List<AiScoreTaskLossLink> links,
            Map<String, BigDecimal> currentPoints
    ) {
        Map<String, Object> state = new LinkedHashMap<>();
        for (AiScoreTaskLossLink link : links) {
            state.put(
                    link.getLossKey(),
                    currentPoints == null
                            ? (link.getGapPoints() == null ? BigDecimal.ZERO : link.getGapPoints())
                            : currentPoints.getOrDefault(link.getLossKey(), BigDecimal.ZERO)
            );
        }
        return state;
    }

    private List<Object> currentEvidenceAnchorIds(
            List<AiScoreTaskLossLink> links,
            Map<String, Map<String, Object>> currentLossByKey
    ) {
        List<Object> anchors = new ArrayList<>();
        for (AiScoreTaskLossLink link : links) {
            Map<String, Object> loss = currentLossByKey.get(link.getLossKey());
            if (loss != null && loss.get("evidenceAnchorIds") instanceof List<?> ids) {
                anchors.addAll(ids);
            }
        }
        return anchors.stream().distinct().toList();
    }

    private String taskRuleHash(String taskJson) {
        Map<String, Object> task = readObject(taskJson);
        Object scoreImpact = task.get("scoreImpact");
        if (scoreImpact instanceof Map<?, ?> values) {
            return text(values.get("ruleHash"));
        }
        return text(task.get("ruleHash"));
    }

    private String verificationReason(String status, BigDecimal before, BigDecimal after) {
        return switch (status) {
            case "verified" -> "同一评分规则下，关联失分已从 " + before + " 降为 0";
            case "partial" -> "同一评分规则下，关联失分由 " + before + " 降至 " + after;
            case "regressed" -> "此前已归零的关联失分在本轮再次出现";
            case "failed" -> "同一评分规则下，关联失分未下降";
            default -> "评分规则已变化或缺少可比账目，本轮不做同口径验证";
        };
    }

    private AiScoreRemediationTask upsertTask(
            String projectScopeKey,
            Long reportId,
            Map<String, Object> snapshot
    ) {
        String taskKey = text(snapshot.get("taskId"));
        if (taskKey.isBlank()) {
            throw new IllegalArgumentException("remediation task requires taskId");
        }
        AiScoreRemediationTask task = taskMapper.selectOne(
                new LambdaQueryWrapper<AiScoreRemediationTask>()
                        .eq(AiScoreRemediationTask::getProjectScopeKey, projectScopeKey)
                        .eq(AiScoreRemediationTask::getTaskKey, taskKey)
                        .last("LIMIT 1")
        );
        LocalDateTime now = LocalDateTime.now();
        if (task == null) {
            task = new AiScoreRemediationTask();
            task.setProjectScopeKey(projectScopeKey);
            task.setTaskKey(taskKey);
            task.setStatus(defaulted(text(snapshot.get("status")), "not_started"));
            task.setSourceReportId(reportId);
            task.setCreatedAt(now);
        }
        task.setRootCauseKey(defaulted(text(snapshot.get("rootCauseKey")), taskKey));
        task.setTitle(defaulted(text(snapshot.get("title")), taskKey));
        task.setTaskJson(writeJson(snapshot));
        task.setLatestReportId(reportId);
        task.setUpdatedAt(now);
        if (task.getId() == null) {
            taskMapper.insert(task);
        } else {
            taskMapper.updateById(task);
        }
        return task;
    }

    private void replaceLossLinks(
            Long reportId,
            AiScoreRemediationTask task,
            Map<String, Object> snapshot,
            Map<String, Map<String, Object>> lossById
    ) {
        linkMapper.delete(new LambdaQueryWrapper<AiScoreTaskLossLink>()
                .eq(AiScoreTaskLossLink::getReportId, reportId)
                .eq(AiScoreTaskLossLink::getTaskId, task.getId()));
        for (String lossId : strings(snapshot.get("coveredLossIds"))) {
            Map<String, Object> loss = lossById.get(lossId);
            if (loss == null) {
                throw new IllegalArgumentException("remediation task references unknown lossId " + lossId);
            }
            AiScoreTaskLossLink link = new AiScoreTaskLossLink();
            link.setReportId(reportId);
            link.setTaskId(task.getId());
            link.setLossId(lossId);
            link.setLossKey(text(loss.get("lossKey")));
            link.setObservationCode(text(loss.get("observationCode")));
            link.setScoreBudgetKey(text(loss.get("scoreBudgetKey")));
            link.setGapPoints(decimal(loss.get("points")));
            link.setCreatedAt(LocalDateTime.now());
            linkMapper.insert(link);
        }
    }

    private List<Map<String, Object>> readArray(String json, String field) {
        try {
            return objectMapper.readValue(
                    json == null ? "[]" : json,
                    new TypeReference<List<Map<String, Object>>>() { }
            );
        } catch (Exception exception) {
            throw new IllegalArgumentException(field + " is not valid JSON array", exception);
        }
    }

    private String writeJson(Map<String, Object> value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (Exception exception) {
            throw new IllegalArgumentException("remediation task cannot be serialized", exception);
        }
    }

    private String writeJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (Exception exception) {
            throw new IllegalArgumentException("verification state cannot be serialized", exception);
        }
    }

    private Map<String, Object> readObject(String json) {
        if (json == null || json.isBlank()) {
            return Map.of();
        }
        try {
            return objectMapper.readValue(json, new TypeReference<Map<String, Object>>() { });
        } catch (Exception exception) {
            return Map.of();
        }
    }

    private List<String> strings(Object value) {
        if (!(value instanceof List<?> values)) {
            return List.of();
        }
        return values.stream().map(this::text).filter(item -> !item.isBlank()).toList();
    }

    private BigDecimal decimal(Object value) {
        return new BigDecimal(String.valueOf(value == null ? "0" : value));
    }

    private String text(Object value) {
        return value == null ? "" : String.valueOf(value).trim();
    }

    private String defaulted(String value, String fallback) {
        return value == null || value.isBlank() ? fallback : value;
    }

    private record PreviousTaskState(
            Long taskId,
            Long latestReportId,
            String taskJson,
            AiScoreRemediationTask task
    ) { }
}
