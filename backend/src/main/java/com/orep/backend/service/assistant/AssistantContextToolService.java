package com.orep.backend.service.assistant;

import com.orep.backend.security.AdminAccess;
import com.orep.backend.service.CollaborationWorkItemService;
import com.orep.backend.service.ProjectTeamService;
import com.orep.backend.service.StudentTrainingService;
import com.orep.backend.service.TeacherPortalService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/**
 * 小启 AI 只读上下文工具：学习 / 任务 / 协同 / 教师门户。
 * 一律复用现有 Service 鉴权；输出裁剪后的摘要，禁止写操作。
 * 教师工具仅 TEACHER/ADMIN/SCHOOL_ADMIN 可调用；学生角色调用返回明确拒绝。
 */
@Service
public class AssistantContextToolService {
    private static final Logger log = LoggerFactory.getLogger(AssistantContextToolService.class);
    private static final int MAX_TASKS = 12;
    private static final int MAX_COLLAB_ITEMS = 12;
    private static final int MAX_WEEKS = 6;
    private static final int MAX_DAYS_PER_WEEK = 8;
    private static final int MAX_TEXT = 240;
    private static final int MAX_REVIEW = 12;
    private static final int MAX_PROGRESS_MEMBERS = 16;

    private final JdbcTemplate jdbc;
    private final StudentTrainingService studentTrainingService;
    private final ProjectTeamService projectTeamService;
    private final CollaborationWorkItemService collaborationWorkItemService;
    private final TeacherPortalService teacherPortalService;
    private final String internalToken;

    public AssistantContextToolService(
            JdbcTemplate jdbc,
            StudentTrainingService studentTrainingService,
            ProjectTeamService projectTeamService,
            CollaborationWorkItemService collaborationWorkItemService,
            TeacherPortalService teacherPortalService,
            @org.springframework.beans.factory.annotation.Value("${orep.assistant.internal-token:OREP_ASSISTANT_INTERNAL_DEV_TOKEN}") String internalToken
    ) {
        this.jdbc = jdbc;
        this.studentTrainingService = studentTrainingService;
        this.projectTeamService = projectTeamService;
        this.collaborationWorkItemService = collaborationWorkItemService;
        this.teacherPortalService = teacherPortalService;
        this.internalToken = internalToken;
    }

    /** 教师工作台摘要（待批、未交、今日任务等） */
    public Map<String, Object> teacherWorkbench(Long tenantId, Long userId, String role, String token) {
        assertInternal(token);
        requireIds(tenantId, userId);
        String resolved = requireTeacherRole(userId, role);
        if (resolved == null) {
            return emptyTool("get_teacher_workbench", "当前账号不是教师或管理员，无法读取教师工作台数据。请使用学生端小启。");
        }
        try {
            Map<String, Object> raw = teacherPortalService.workbench(tenantId, userId, resolved);
            Map<String, Object> data = trimTeacherWorkbench(raw);
            return Map.of(
                    "tool", "get_teacher_workbench",
                    "data", data,
                    "markdown", formatTeacherWorkbenchMd(data)
            );
        } catch (Exception e) {
            log.warn("teacherWorkbench failed: {}", e.getMessage());
            return emptyTool("get_teacher_workbench", "读取教师工作台失败：" + e.getMessage());
        }
    }

    /** 教师批改队列摘要 */
    public Map<String, Object> teacherReviewQueue(Long tenantId, Long userId, String role, String token) {
        assertInternal(token);
        requireIds(tenantId, userId);
        String resolved = requireTeacherRole(userId, role);
        if (resolved == null) {
            return emptyTool("get_teacher_review_queue", "当前账号不是教师或管理员，无法读取批改队列。");
        }
        try {
            // review queue lives under TeacherReviewService via controller - use portal analytics + camp overview
            Map<String, Object> camp = teacherPortalService.campOverview(tenantId, userId, resolved, null);
            Map<String, Object> data = trimTeacherReviewContext(camp);
            return Map.of(
                    "tool", "get_teacher_review_queue",
                    "data", data,
                    "markdown", formatTeacherReviewMd(data)
            );
        } catch (Exception e) {
            log.warn("teacherReviewQueue failed: {}", e.getMessage());
            return emptyTool("get_teacher_review_queue", "读取批改/训练进度失败：" + e.getMessage());
        }
    }

    /** 教师训练营进度摘要（成员提交） */
    public Map<String, Object> teacherCampProgress(Long tenantId, Long userId, String role, Long campId, String token) {
        assertInternal(token);
        requireIds(tenantId, userId);
        String resolved = requireTeacherRole(userId, role);
        if (resolved == null) {
            return emptyTool("get_teacher_camp_progress", "当前账号不是教师或管理员，无法读取训练进度。");
        }
        try {
            Map<String, Object> raw = teacherPortalService.campOverview(tenantId, userId, resolved, campId);
            Map<String, Object> data = trimTeacherProgress(raw);
            return Map.of(
                    "tool", "get_teacher_camp_progress",
                    "data", data,
                    "markdown", formatTeacherProgressMd(data)
            );
        } catch (Exception e) {
            log.warn("teacherCampProgress failed: {}", e.getMessage());
            return emptyTool("get_teacher_camp_progress", "读取训练进度失败：" + e.getMessage());
        }
    }

    public Map<String, Object> learningToday(Long tenantId, Long userId, String token) {
        assertInternal(token);
        requireIds(tenantId, userId);
        // 教师角色不应读「我作为学生的今日训练」冒充学生视角
        String role = resolveRole(userId, null);
        if (AdminAccess.canAccessTeacherPortal(role)) {
            return emptyTool(
                    "get_learning_today",
                    "当前为教师账号。请改用教师工作台/训练进度工具，不要按学生视角查询「我的今日训练」。"
            );
        }
        try {
            Map<String, Object> raw = studentTrainingService.todayOverview(tenantId, userId);
            return Map.of(
                    "tool", "get_learning_today",
                    "data", trimLearningToday(raw),
                    "markdown", formatLearningTodayMd(trimLearningToday(raw))
            );
        } catch (ResponseStatusException e) {
            throw e;
        } catch (Exception e) {
            log.warn("learningToday failed: {}", e.getMessage());
            return emptyTool("get_learning_today", "读取训练营今日数据失败：" + e.getMessage());
        }
    }

    public Map<String, Object> learningPlan(Long tenantId, Long userId, String token) {
        assertInternal(token);
        requireIds(tenantId, userId);
        try {
            Map<String, Object> raw = studentTrainingService.plan(tenantId, userId);
            Map<String, Object> trimmed = trimLearningPlan(raw);
            return Map.of(
                    "tool", "get_learning_plan",
                    "data", trimmed,
                    "markdown", formatLearningPlanMd(trimmed)
            );
        } catch (Exception e) {
            log.warn("learningPlan failed: {}", e.getMessage());
            return emptyTool("get_learning_plan", "读取训练营计划失败：" + e.getMessage());
        }
    }

    public Map<String, Object> myTasks(Long tenantId, Long userId, Long teamId, String role, String token) {
        assertInternal(token);
        requireIds(tenantId, userId);
        String resolvedRole = resolveRole(userId, role);
        try {
            List<Map<String, Object>> tasks = new ArrayList<>();
            List<Map<String, Object>> teams = projectTeamService.myTeams(tenantId, userId, resolvedRole);
            List<Long> teamIds = new ArrayList<>();
            if (teamId != null) {
                teamIds.add(teamId);
            } else {
                for (Map<String, Object> t : teams) {
                    Long id = longVal(t.get("id"));
                    if (id == null) id = longVal(t.get("teamId"));
                    if (id != null) teamIds.add(id);
                    if (teamIds.size() >= 5) break;
                }
            }
            for (Long tid : teamIds) {
                try {
                    Map<String, Object> dash = projectTeamService.dashboard(tid, tenantId, userId, resolvedRole);
                    Object teamObj = dash.get("team");
                    String teamName = teamObj instanceof Map<?, ?> m
                            ? str(m.get("name"))
                            : null;
                    @SuppressWarnings("unchecked")
                    List<Map<String, Object>> list = (List<Map<String, Object>>) dash.getOrDefault("tasks", List.of());
                    for (Map<String, Object> task : list) {
                        Map<String, Object> row = trimTask(task, tid, teamName);
                        if (row != null) tasks.add(row);
                        if (tasks.size() >= MAX_TASKS) break;
                    }
                } catch (ResponseStatusException ex) {
                    // 无权限团队跳过
                    log.debug("skip team {} for tasks: {}", tid, ex.getReason());
                }
                if (tasks.size() >= MAX_TASKS) break;
            }
            Map<String, Object> data = new LinkedHashMap<>();
            data.put("tasks", tasks);
            data.put("count", tasks.size());
            data.put("teamIdFilter", teamId);
            return Map.of(
                    "tool", "get_my_tasks",
                    "data", data,
                    "markdown", formatTasksMd(tasks)
            );
        } catch (Exception e) {
            log.warn("myTasks failed: {}", e.getMessage());
            return emptyTool("get_my_tasks", "读取任务列表失败：" + e.getMessage());
        }
    }

    public Map<String, Object> taskDetail(Long tenantId, Long userId, Long teamId, Long taskId, String role, String token) {
        assertInternal(token);
        requireIds(tenantId, userId);
        if (teamId == null || taskId == null) {
            return emptyTool("get_task_detail", "缺少 teamId 或 taskId");
        }
        String resolvedRole = resolveRole(userId, role);
        try {
            Map<String, Object> raw = projectTeamService.taskDetail(teamId, taskId, tenantId, userId, resolvedRole);
            Map<String, Object> trimmed = trimTaskDetail(raw, teamId);
            return Map.of(
                    "tool", "get_task_detail",
                    "data", trimmed,
                    "markdown", formatTaskDetailMd(trimmed)
            );
        } catch (ResponseStatusException e) {
            return emptyTool("get_task_detail", e.getReason() != null ? e.getReason() : "无权查看该任务");
        } catch (Exception e) {
            log.warn("taskDetail failed: {}", e.getMessage());
            return emptyTool("get_task_detail", "读取任务详情失败：" + e.getMessage());
        }
    }

    public Map<String, Object> collabSummary(Long tenantId, Long userId, String role, String token) {
        assertInternal(token);
        requireIds(tenantId, userId);
        // 始终以 users.role 为准，避免 JWT/默认 STUDENT 导致教师可见范围错误
        String resolvedRole = resolveRole(userId, null);
        try {
            Map<String, Object> raw = collaborationWorkItemService.summary(tenantId, userId, resolvedRole);
            // 附带分栏样本，避免「待处理=0」时模型/用户误以为整个协作里什么都没有
            Map<String, Object> action = fetchCollabView(tenantId, userId, resolvedRole, "ACTION_REQUIRED", null, 8);
            Map<String, Object> mine = fetchCollabView(tenantId, userId, resolvedRole, "CREATED_BY_ME", null, 8);
            Map<String, Object> progress = fetchCollabView(tenantId, userId, resolvedRole, "IN_PROGRESS", null, 8);
            Map<String, Object> data = new LinkedHashMap<>(raw);
            data.put("resolvedRole", resolvedRole);
            data.put("actionRequiredItems", action.get("items"));
            data.put("createdByMeItems", mine.get("items"));
            data.put("inProgressItems", progress.get("items"));
            return Map.of(
                    "tool", "get_collab_summary",
                    "data", data,
                    "markdown", formatCollabOverviewMd(data)
            );
        } catch (ResponseStatusException e) {
            return emptyTool("get_collab_summary", e.getReason() != null ? e.getReason() : "协同功能不可用");
        } catch (Exception e) {
            log.warn("collabSummary failed: {}", e.getMessage());
            return emptyTool("get_collab_summary", "读取协同摘要失败：" + e.getMessage());
        }
    }

    public Map<String, Object> collabItems(
            Long tenantId, Long userId, Long teamId, String role, String view, String token
    ) {
        assertInternal(token);
        requireIds(tenantId, userId);
        String resolvedRole = resolveRole(userId, null);
        String v = (view == null || view.isBlank()) ? "ACTION_REQUIRED" : view;
        // 小启问「我的协作」时默认不按会话 team 过滤，与协同工作台默认一致（看全部可见团队）
        try {
            Map<String, Object> raw = collaborationWorkItemService.items(
                    tenantId, userId, resolvedRole, v, null, null, MAX_COLLAB_ITEMS);
            @SuppressWarnings("unchecked")
            List<Map<String, Object>> items = (List<Map<String, Object>>) raw.getOrDefault("items", List.of());
            List<Map<String, Object>> trimmed = new ArrayList<>();
            for (Map<String, Object> item : items) {
                trimmed.add(trimCollabItem(item));
                if (trimmed.size() >= MAX_COLLAB_ITEMS) break;
            }
            Map<String, Object> data = new LinkedHashMap<>();
            data.put("view", raw.get("view"));
            data.put("items", trimmed);
            data.put("count", trimmed.size());
            data.put("hasMore", raw.get("hasMore"));
            data.put("resolvedRole", resolvedRole);
            data.put("teamIdFilterIgnored", teamId); // 仅记录，不用于过滤
            return Map.of(
                    "tool", "get_collab_items",
                    "data", data,
                    "markdown", formatCollabItemsMd(trimmed, v)
            );
        } catch (ResponseStatusException e) {
            return emptyTool("get_collab_items", e.getReason() != null ? e.getReason() : "协同功能不可用");
        } catch (Exception e) {
            log.warn("collabItems failed: {}", e.getMessage());
            return emptyTool("get_collab_items", "读取协同事项失败：" + e.getMessage());
        }
    }

    private Map<String, Object> fetchCollabView(
            Long tenantId, Long userId, String role, String view, Long teamId, int limit
    ) {
        Map<String, Object> raw = collaborationWorkItemService.items(
                tenantId, userId, role, view, teamId, null, limit);
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> items = (List<Map<String, Object>>) raw.getOrDefault("items", List.of());
        List<Map<String, Object>> trimmed = new ArrayList<>();
        for (Map<String, Object> item : items) {
            trimmed.add(trimCollabItem(item));
            if (trimmed.size() >= limit) break;
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("items", trimmed);
        out.put("count", trimmed.size());
        return out;
    }

    // ── trim / format ─────────────────────────────────────────

    @SuppressWarnings("unchecked")
    private Map<String, Object> trimLearningToday(Map<String, Object> raw) {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("hasCamp", raw.get("hasCamp"));
        out.put("hasTrainingDay", raw.get("hasTrainingDay"));
        out.put("message", raw.get("message"));
        if (raw.get("camp") instanceof Map<?, ?> camp) {
            out.put("camp", pick(camp, "campId", "name", "teamId", "teamName", "status"));
        } else {
            // current() 风格扁平
            out.put("campId", raw.get("campId"));
            out.put("campName", first(raw.get("name"), raw.get("campName")));
        }
        out.put("dayId", raw.get("dayId"));
        out.put("dayNo", raw.get("dayNo"));
        out.put("title", raw.get("title"));
        out.put("summary", clip(raw.get("summary"), MAX_TEXT));
        out.put("trainingDate", raw.get("trainingDate"));
        out.put("dueAt", raw.get("dueAt"));
        out.put("status", raw.get("status"));
        out.put("locked", raw.get("locked"));
        out.put("available", raw.get("available"));
        out.put("learningResourceCount", raw.get("learningResourceCount"));
        out.put("requiredLearningCount", raw.get("requiredLearningCount"));
        out.put("completedLearningCount", raw.get("completedLearningCount"));
        out.put("estimatedLearningMinutes", raw.get("estimatedLearningMinutes"));
        out.put("learningPreview", raw.get("learningPreview"));
        if (raw.get("primaryTask") instanceof Map<?, ?> pt) {
            out.put("primaryTask", pick(pt, "taskId", "id", "title", "status", "dueAt", "priority",
                    "latestSubmissionStatus", "latestSubmissionId"));
        }
        if (raw.get("tasks") instanceof List<?> list) {
            List<Map<String, Object>> tasks = new ArrayList<>();
            for (Object o : list) {
                if (o instanceof Map<?, ?> m) {
                    tasks.add(pick(m, "taskId", "id", "title", "status", "dueAt", "priority", "isPrimary"));
                }
                if (tasks.size() >= 8) break;
            }
            out.put("tasks", tasks);
        }
        if (raw.get("nextDay") instanceof Map<?, ?> nd) {
            out.put("nextDay", pick(nd, "dayId", "dayNo", "title", "trainingDate"));
        }
        // 不注入 contentHtml / 大段正文
        return out;
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> trimLearningPlan(Map<String, Object> raw) {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("hasCamp", raw.get("hasCamp"));
        out.put("message", raw.get("message"));
        out.put("camp", raw.get("camp") instanceof Map<?, ?> c
                ? pick(c, "campId", "name", "teamId", "teamName", "status")
                : null);
        List<Map<String, Object>> weeksOut = new ArrayList<>();
        if (raw.get("weeks") instanceof List<?> weeks) {
            int wi = 0;
            for (Object w : weeks) {
                if (!(w instanceof Map<?, ?> week) || wi >= MAX_WEEKS) continue;
                Map<String, Object> wo = pick(week, "weekId", "weekNo", "title", "startDate", "endDate");
                List<Map<String, Object>> daysOut = new ArrayList<>();
                if (week.get("days") instanceof List<?> days) {
                    int di = 0;
                    for (Object d : days) {
                        if (!(d instanceof Map<?, ?> day) || di >= MAX_DAYS_PER_WEEK) continue;
                        Map<String, Object> dd = pick(day,
                                "dayId", "dayNo", "title", "trainingDate", "dueAt", "status",
                                "progressStatus", "taskCount", "learningResourceCount",
                                "completedLearningCount", "requiredLearningCount", "locked");
                        dd.put("summary", clip(day.get("summary"), 120));
                        daysOut.add(dd);
                        di++;
                    }
                }
                wo.put("days", daysOut);
                weeksOut.add(wo);
                wi++;
            }
        }
        out.put("weeks", weeksOut);
        return out;
    }

    private Map<String, Object> trimTask(Map<String, Object> task, Long teamId, String teamName) {
        if (task == null) return null;
        Map<String, Object> row = pick(task,
                "id", "title", "status", "priority", "dueAt", "ownerUserId", "ownerName",
                "sourceType", "createdAt", "updatedAt");
        row.put("teamId", teamId);
        if (teamName != null) row.put("teamName", teamName);
        row.put("description", clip(task.get("description"), MAX_TEXT));
        return row;
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> trimTaskDetail(Map<String, Object> raw, Long teamId) {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("teamId", teamId);
        // taskDetail 可能把任务字段摊平或包在 task 里
        Map<String, Object> task = raw.get("task") instanceof Map<?, ?> t
                ? castMap(t)
                : raw;
        out.put("task", pick(task,
                "id", "title", "status", "priority", "dueAt", "ownerUserId", "ownerName",
                "sourceType", "createdAt", "updatedAt", "canSubmit", "canEdit"));
        out.put("description", clip(task.get("description"), 600));
        if (raw.get("requirements") instanceof List<?> reqs) {
            List<Map<String, Object>> list = new ArrayList<>();
            for (Object r : reqs) {
                if (r instanceof Map<?, ?> m) {
                    list.add(pick(m, "id", "title", "required", "assetType", "description"));
                }
                if (list.size() >= 10) break;
            }
            out.put("requirements", list);
        }
        if (raw.get("training") instanceof Map<?, ?> tr) {
            out.put("training", pick(tr, "dayId", "dayNo", "dayTitle", "campName", "trainingDate"));
        } else if (raw.get("trainingDays") instanceof List<?> tds && !tds.isEmpty() && tds.get(0) instanceof Map<?, ?> tr) {
            out.put("training", pick(tr, "dayId", "dayNo", "dayTitle", "campName", "trainingDate"));
        }
        return out;
    }

    private Map<String, Object> trimCollabItem(Map<String, Object> item) {
        Map<String, Object> row = pick(item,
                "id", "key", "entityType", "type", "kind", "title", "status", "statusLabel",
                "priority", "sourceType", "sourceLabel", "primaryAction",
                "teamId", "teamName", "actionRequired", "createdByCurrentUser",
                "dueAt", "updatedAt", "createdAt", "ownerName", "requesterName",
                "recipientName", "canAccept", "canDecline", "canWithdraw", "targetPath");
        row.put("description", clip(first(item.get("description"), item.get("summary"), item.get("content")), MAX_TEXT));
        return row;
    }

    private String formatLearningTodayMd(Map<String, Object> d) {
        StringBuilder md = new StringBuilder();
        md.append("## 训练营 · 今日学习\n\n");
        if (!Boolean.TRUE.equals(d.get("hasCamp"))) {
            md.append(str(d.get("message")) != null ? d.get("message") : "当前没有集训营").append("\n");
            return md.toString();
        }
        if (!Boolean.TRUE.equals(d.get("hasTrainingDay"))) {
            md.append(str(d.get("message")) != null ? d.get("message") : "今天暂未安排集训").append("\n");
            if (d.get("nextDay") instanceof Map<?, ?> n) {
                Object nt = n.get("title");
                Object nd = n.get("trainingDate");
                if (nt != null || nd != null) {
                    md.append("- 下一次：").append(nullTo(nt, "待定"));
                    if (nd != null) md.append("（").append(nd).append("）");
                    md.append("\n");
                }
            }
            return md.toString();
        }
        md.append("**").append(nullTo(d.get("title"), "今日训练")).append("**\n\n");
        if (d.get("trainingDate") != null) md.append("- 日期：").append(d.get("trainingDate")).append("\n");
        if (d.get("summary") != null) md.append("- 摘要：").append(d.get("summary")).append("\n");
        md.append("- 学习资源：完成 ").append(d.getOrDefault("completedLearningCount", 0))
                .append("/").append(d.getOrDefault("requiredLearningCount", d.getOrDefault("learningResourceCount", 0)))
                .append("，预计 ").append(d.getOrDefault("estimatedLearningMinutes", 0)).append(" 分钟\n");
        if (d.get("primaryTask") instanceof Map<?, ?> pt) {
            md.append("- 主任务：").append(pt.get("title"))
                    .append("（状态 ").append(pt.get("status")).append("）\n");
        }
        if (d.get("tasks") instanceof List<?> tasks && !tasks.isEmpty()) {
            md.append("\n### 今日任务\n");
            int i = 0;
            for (Object t : tasks) {
                if (!(t instanceof Map<?, ?> m)) continue;
                i++;
                md.append(i).append(". ").append(m.get("title"))
                        .append(" · ").append(m.get("status"));
                if (m.get("dueAt") != null) md.append(" · 截止 ").append(m.get("dueAt"));
                md.append("\n");
            }
        }
        md.append("\n*可跳转：/training/today*\n");
        return md.toString();
    }

    @SuppressWarnings("unchecked")
    private String formatLearningPlanMd(Map<String, Object> d) {
        StringBuilder md = new StringBuilder("## 训练营 · 计划摘要\n\n");
        if (!Boolean.TRUE.equals(d.get("hasCamp"))) {
            md.append(nullTo(d.get("message"), "暂无集训营计划")).append("\n");
            return md.toString();
        }
        if (d.get("weeks") instanceof List<?> weeks) {
            for (Object w : weeks) {
                if (!(w instanceof Map<?, ?> week)) continue;
                md.append("### 第").append(week.get("weekNo")).append("周 ")
                        .append(nullTo(week.get("title"), "")).append("\n");
                if (week.get("days") instanceof List<?> days) {
                    for (Object dayObj : days) {
                        if (!(dayObj instanceof Map<?, ?> dayRaw)) continue;
                        Map<String, Object> day = castMap(dayRaw);
                        md.append("- D").append(day.get("dayNo")).append(" ")
                                .append(day.get("title"))
                                .append(" · ").append(day.getOrDefault("progressStatus", day.get("status")))
                                .append(" · 任务").append(day.getOrDefault("taskCount", 0))
                                .append(" · 学习").append(day.getOrDefault("completedLearningCount", 0))
                                .append("/").append(day.getOrDefault("learningResourceCount", 0));
                        if (Boolean.TRUE.equals(day.get("locked"))) md.append(" · 🔒");
                        md.append("\n");
                    }
                }
                md.append("\n");
            }
        }
        md.append("*可跳转：/training/plan*\n");
        return md.toString();
    }

    private String formatTasksMd(List<Map<String, Object>> tasks) {
        StringBuilder md = new StringBuilder("## 我的任务\n\n");
        if (tasks == null || tasks.isEmpty()) {
            md.append("当前没有可见的待办任务。\n");
            return md.toString();
        }
        int i = 0;
        for (Map<String, Object> t : tasks) {
            i++;
            md.append(i).append(". **").append(nullTo(t.get("title"), "未命名任务")).append("**");
            md.append(" · ").append(nullTo(t.get("status"), "-"));
            if (t.get("priority") != null) md.append(" · 优先级 ").append(t.get("priority"));
            if (t.get("dueAt") != null) md.append(" · 截止 ").append(t.get("dueAt"));
            if (t.get("teamName") != null) md.append(" · 团队 ").append(t.get("teamName"));
            md.append("\n");
            md.append("   - taskId=").append(t.get("id")).append(" teamId=").append(t.get("teamId")).append("\n");
            if (t.get("description") != null) {
                md.append("   - ").append(t.get("description")).append("\n");
            }
        }
        md.append("\n*可跳转：/project-team*\n");
        return md.toString();
    }

    @SuppressWarnings("unchecked")
    private String formatTaskDetailMd(Map<String, Object> d) {
        StringBuilder md = new StringBuilder("## 任务详情\n\n");
        Map<String, Object> task = d.get("task") instanceof Map<?, ?> t ? castMap(t) : Map.of();
        md.append("**").append(nullTo(task.get("title"), "任务")).append("**\n\n");
        md.append("- 状态：").append(task.get("status")).append("\n");
        if (task.get("priority") != null) md.append("- 优先级：").append(task.get("priority")).append("\n");
        if (task.get("dueAt") != null) md.append("- 截止：").append(task.get("dueAt")).append("\n");
        if (task.get("ownerName") != null) md.append("- 负责人：").append(task.get("ownerName")).append("\n");
        if (d.get("description") != null) md.append("\n").append(d.get("description")).append("\n");
        if (d.get("requirements") instanceof List<?> reqs && !reqs.isEmpty()) {
            md.append("\n### 交付要求\n");
            int i = 0;
            for (Object r : reqs) {
                if (!(r instanceof Map<?, ?> m)) continue;
                i++;
                md.append(i).append(". ").append(m.get("title"));
                if (Boolean.TRUE.equals(m.get("required"))) md.append("（必填）");
                md.append("\n");
            }
        }
        md.append("\n*taskId=").append(task.get("id")).append(" teamId=").append(d.get("teamId")).append("*\n");
        return md.toString();
    }

    @SuppressWarnings("unchecked")
    private String formatCollabOverviewMd(Map<String, Object> d) {
        StringBuilder md = new StringBuilder("## 协同工作台（竞赛大脑站内）\n\n");
        md.append("说明：这里的「待我处理」= 需要你现在行动的事项（接受协作 / 提交任务 / 审核）。\n");
        md.append("「我发起的」= 你创建/发起的事项，**不一定**等于待你处理。\n\n");
        md.append("| 分类 | 数量 | 含义 |\n| --- | ---: | --- |\n");
        md.append("| **待我处理** | **").append(d.getOrDefault("actionRequired", 0))
                .append("** | 需要你现在操作 |\n");
        md.append("| 进行中 | ").append(d.getOrDefault("inProgress", 0)).append(" | 推进中 |\n");
        md.append("| 我发起的 | ").append(d.getOrDefault("createdByMe", 0)).append(" | 你创建/发起 |\n");
        md.append("| 已完成 | ").append(d.getOrDefault("completed", 0)).append(" | 已结束 |\n");
        md.append("| 合计可见 | ").append(d.getOrDefault("total", 0)).append(" | 你有权限看到的 |\n\n");

        appendCollabSection(md, "待我处理（需要你行动）",
                (List<Map<String, Object>>) d.get("actionRequiredItems"), true);
        appendCollabSection(md, "我发起的（不等于待处理）",
                (List<Map<String, Object>>) d.get("createdByMeItems"), false);
        appendCollabSection(md, "进行中",
                (List<Map<String, Object>>) d.get("inProgressItems"), false);

        int ar = 0;
        try {
            ar = Integer.parseInt(String.valueOf(d.getOrDefault("actionRequired", 0)));
        } catch (Exception ignored) {
        }
        if (ar == 0) {
            md.append("**结论：当前没有「待你处理」的协作/任务。**");
            Object cbm = d.get("createdByMe");
            if (cbm != null && !"0".equals(String.valueOf(cbm))) {
                md.append(" 你有 ").append(cbm).append(" 条「我发起的」事项，可在协同工作台「我发起的」里查看。");
            }
            md.append("\n");
        }
        md.append("\n*可打开侧栏「待办中心」对照；此为站内数据，不是飞书/钉钉。*\n");
        return md.toString();
    }

    private void appendCollabSection(StringBuilder md, String title, List<Map<String, Object>> items, boolean actionView) {
        md.append("### ").append(title).append("\n\n");
        if (items == null || items.isEmpty()) {
            md.append(actionView ? "（空）\n\n" : "（无）\n\n");
            return;
        }
        int i = 0;
        for (Map<String, Object> it : items) {
            i++;
            md.append(i).append(". **").append(nullTo(it.get("title"), "未命名")).append("**");
            Object label = first(it.get("statusLabel"), it.get("status"));
            if (label != null) md.append(" · ").append(label);
            if (it.get("sourceLabel") != null) md.append(" · ").append(it.get("sourceLabel"));
            if (it.get("teamName") != null) md.append(" · ").append(it.get("teamName"));
            if (it.get("entityType") != null) md.append(" · ").append(it.get("entityType"));
            if (it.get("id") != null) md.append(" · id=").append(it.get("id"));
            md.append("\n");
            if (it.get("description") != null) {
                md.append("   - ").append(it.get("description")).append("\n");
            }
            if (Boolean.TRUE.equals(it.get("canAccept"))) {
                md.append("   - 可操作：接受（需确认卡，requestId=").append(it.get("id")).append("）\n");
            }
        }
        md.append("\n");
    }

    private String formatCollabItemsMd(List<Map<String, Object>> items, String view) {
        String viewLabel = switch (view == null ? "" : view.toUpperCase()) {
            case "ACTION_REQUIRED" -> "待我处理";
            case "CREATED_BY_ME" -> "我发起的";
            case "IN_PROGRESS" -> "进行中";
            case "ALL" -> "全部";
            default -> view;
        };
        StringBuilder md = new StringBuilder("## 协同事项 · ").append(viewLabel).append("\n\n");
        if ("ACTION_REQUIRED".equalsIgnoreCase(view)) {
            md.append("（仅含需要你现在行动的事项）\n\n");
        }
        if (items == null || items.isEmpty()) {
            md.append("当前「").append(viewLabel).append("」为空。\n");
            return md.toString();
        }
        int i = 0;
        for (Map<String, Object> it : items) {
            i++;
            md.append(i).append(". **").append(nullTo(it.get("title"), "未命名")).append("**");
            Object label = first(it.get("statusLabel"), it.get("status"));
            if (label != null) md.append(" · ").append(label);
            if (it.get("sourceLabel") != null) md.append(" · ").append(it.get("sourceLabel"));
            if (Boolean.TRUE.equals(it.get("actionRequired"))) md.append(" · ⚠ 待你处理");
            if (it.get("teamName") != null) md.append(" · ").append(it.get("teamName"));
            if (it.get("id") != null) md.append(" · id=").append(it.get("id"));
            md.append("\n");
            if (it.get("description") != null) {
                md.append("   - ").append(it.get("description")).append("\n");
            }
        }
        return md.toString();
    }

    // ── helpers ───────────────────────────────────────────────

    /** @return 规范化教师角色，非教师返回 null */
    private String requireTeacherRole(Long userId, String role) {
        String resolved = resolveRole(userId, role);
        if (!AdminAccess.canAccessTeacherPortal(resolved)) {
            return null;
        }
        return resolved;
    }

    private Map<String, Object> trimTeacherWorkbench(Map<String, Object> raw) {
        Map<String, Object> out = new LinkedHashMap<>();
        if (raw == null) return out;
        out.put("pendingReviews", raw.get("pendingReviews"));
        out.put("runningMeetings", raw.get("runningMeetings"));
        out.put("aiTodos", raw.get("aiTodos"));
        out.put("missingToday", raw.get("missingToday"));
        if (raw.get("camp") instanceof Map<?, ?> camp) {
            out.put("camp", pick(camp, "campId", "campName", "name", "teamId", "teamName",
                    "status", "currentDay", "totalDays", "startDate", "endDate", "remainingDays"));
        }
        if (raw.get("timeline") instanceof List<?> list) {
            List<Map<String, Object>> tl = new ArrayList<>();
            for (Object o : list) {
                if (o instanceof Map<?, ?> m) {
                    tl.add(pick(m, "date", "type", "title", "time", "status"));
                }
                if (tl.size() >= 8) break;
            }
            out.put("timeline", tl);
        }
        if (raw.get("interventions") instanceof List<?> list) {
            List<Map<String, Object>> iv = new ArrayList<>();
            for (Object o : list) {
                if (o instanceof Map<?, ?> m) {
                    iv.add(pick(m, "userId", "username", "reason", "missingDays"));
                }
                if (iv.size() >= 8) break;
            }
            out.put("interventions", iv);
        }
        return out;
    }

    private String formatTeacherWorkbenchMd(Map<String, Object> d) {
        StringBuilder md = new StringBuilder("## 教师工作台（竞赛大脑教师端）\n\n");
        md.append("说明：以下为当前教师有权限管理的项目/训练营真实数据，不是学生个人视角。\n\n");
        if (d.get("camp") instanceof Map<?, ?> camp && !camp.isEmpty()) {
            md.append("**当前训练营**：").append(nullTo(first(camp.get("campName"), camp.get("name")), "未命名"))
                    .append(" · 项目 ").append(nullTo(camp.get("teamName"), "—"))
                    .append(" · 进度第 ").append(nullTo(camp.get("currentDay"), "—"))
                    .append("/").append(nullTo(camp.get("totalDays"), "—")).append(" 天\n\n");
        } else {
            md.append("**当前训练营**：未关联或暂无进行中的训练营\n\n");
        }
        md.append("| 指标 | 数值 |\n| --- | ---: |\n");
        md.append("| 待批改 | ").append(d.getOrDefault("pendingReviews", 0)).append(" |\n");
        md.append("| 今日未交 | ").append(d.getOrDefault("missingToday", 0)).append(" |\n");
        md.append("| 进行中路演 | ").append(d.getOrDefault("runningMeetings", 0)).append(" |\n");
        md.append("| AI 待办 | ").append(d.getOrDefault("aiTodos", 0)).append(" |\n\n");
        if (d.get("interventions") instanceof List<?> list && !list.isEmpty()) {
            md.append("### 需关注学生\n\n");
            int i = 0;
            for (Object o : list) {
                if (!(o instanceof Map<?, ?> m)) continue;
                i++;
                md.append(i).append(". ").append(nullTo(m.get("username"), "学生"))
                        .append(" · ").append(nullTo(m.get("reason"), "提交异常"));
                if (m.get("missingDays") != null) md.append(" · 缺交 ").append(m.get("missingDays")).append(" 天");
                md.append("\n");
            }
            md.append("\n");
        }
        if (d.get("timeline") instanceof List<?> list && !list.isEmpty()) {
            md.append("### 近几日日程\n\n");
            for (Object o : list) {
                if (!(o instanceof Map<?, ?> m)) continue;
                md.append("- ").append(nullTo(m.get("date"), ""))
                        .append(" · ").append(nullTo(first(m.get("title"), m.get("type")), "日程"))
                        .append(m.get("time") != null ? " · " + m.get("time") : "")
                        .append("\n");
            }
        }
        return md.toString();
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> trimTeacherReviewContext(Map<String, Object> camp) {
        Map<String, Object> out = new LinkedHashMap<>();
        if (camp == null) return out;
        out.put("hasCamp", camp.get("hasCamp"));
        out.put("pendingReviews", camp.get("pendingReviews"));
        out.put("memberCount", camp.get("memberCount"));
        Integer currentDay = null;
        if (camp.get("camp") instanceof Map<?, ?> c) {
            out.put("camp", pick(c, "campId", "campName", "name", "teamName", "currentDay", "totalDays", "status"));
            Object cd = c.get("currentDay");
            if (cd instanceof Number n) currentDay = n.intValue();
        }
        // campOverview 无独立 today 字段，从 days 里取当前天
        if (camp.get("days") instanceof List<?> days) {
            Map<?, ?> best = null;
            for (Object o : days) {
                if (!(o instanceof Map<?, ?> d)) continue;
                if (currentDay != null && currentDay.equals(intish(d.get("dayNo")))) {
                    best = d;
                    break;
                }
                if (best == null) best = d;
            }
            if (best != null) {
                out.put("today", pick(best, "dayNo", "title", "submittedCount", "pendingCount", "status"));
            }
        }
        return out;
    }

    private static Integer intish(Object v) {
        if (v instanceof Number n) return n.intValue();
        try {
            return v == null ? null : Integer.parseInt(String.valueOf(v));
        } catch (Exception e) {
            return null;
        }
    }

    private String formatTeacherReviewMd(Map<String, Object> d) {
        StringBuilder md = new StringBuilder("## 教师 · 提交与批改概况\n\n");
        if (Boolean.FALSE.equals(d.get("hasCamp"))) {
            md.append("当前没有可管理的训练营数据。\n");
            return md.toString();
        }
        md.append("待批改约 **").append(d.getOrDefault("pendingReviews", 0)).append("** 份");
        md.append(" · 参训成员 **").append(d.getOrDefault("memberCount", 0)).append("** 人\n\n");
        if (d.get("today") instanceof Map<?, ?> t) {
            md.append("**今日训练**：第 ").append(nullTo(t.get("dayNo"), "—")).append(" 天 · ")
                    .append(nullTo(t.get("title"), "主题待填"))
                    .append(" · 已提交 ").append(nullTo(t.get("submittedCount"), "0"))
                    .append(" · 待批 ").append(nullTo(t.get("pendingCount"), "0")).append("\n");
        }
        md.append("\n*可引导教师打开「提交与批改」页处理队列。*\n");
        return md.toString();
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> trimTeacherProgress(Map<String, Object> raw) {
        Map<String, Object> out = new LinkedHashMap<>();
        if (raw == null) return out;
        out.put("hasCamp", raw.get("hasCamp"));
        out.put("memberCount", raw.get("memberCount"));
        out.put("pendingReviews", raw.get("pendingReviews"));
        if (raw.get("camp") instanceof Map<?, ?> c) {
            out.put("camp", pick(c, "campId", "campName", "name", "teamName", "currentDay", "totalDays", "status"));
        }
        if (raw.get("progress") instanceof List<?> list) {
            List<Map<String, Object>> members = new ArrayList<>();
            for (Object o : list) {
                if (!(o instanceof Map<?, ?> m)) continue;
                Map<String, Object> row = pick(m, "userId", "username", "positionName", "submittedDays");
                // 统计缺交天数（已开放日内）
                int missing = 0;
                if (m.get("days") instanceof List<?> days) {
                    for (Object d : days) {
                        if (d instanceof Map<?, ?> day) {
                            String st = String.valueOf(day.get("status") == null ? "" : day.get("status")).toUpperCase(Locale.ROOT);
                            if ("NOT_SUBMITTED".equals(st) || "EXPIRED".equals(st)) missing++;
                        }
                    }
                }
                row.put("missingDays", missing);
                members.add(row);
                if (members.size() >= MAX_PROGRESS_MEMBERS) break;
            }
            out.put("members", members);
        }
        return out;
    }

    private String formatTeacherProgressMd(Map<String, Object> d) {
        StringBuilder md = new StringBuilder("## 教师 · 训练进度摘要\n\n");
        if (Boolean.FALSE.equals(d.get("hasCamp"))) {
            md.append("暂无训练营进度。\n");
            return md.toString();
        }
        if (d.get("camp") instanceof Map<?, ?> c) {
            md.append("**训练营** ").append(nullTo(first(c.get("campName"), c.get("name")), "—"))
                    .append(" · 第 ").append(nullTo(c.get("currentDay"), "—"))
                    .append("/").append(nullTo(c.get("totalDays"), "—")).append(" 天\n\n");
        }
        md.append("参训 **").append(d.getOrDefault("memberCount", 0)).append("** 人 · 待批改 **")
                .append(d.getOrDefault("pendingReviews", 0)).append("**\n\n");
        if (d.get("members") instanceof List<?> list && !list.isEmpty()) {
            md.append("### 成员提交概况（节选）\n\n");
            md.append("| 学生 | 岗位 | 已提交天数 | 缺交天数 |\n| --- | --- | ---: | ---: |\n");
            for (Object o : list) {
                if (!(o instanceof Map<?, ?> m)) continue;
                md.append("| ").append(nullTo(m.get("username"), "—"))
                        .append(" | ").append(nullTo(m.get("positionName"), "—"))
                        .append(" | ").append(nullTo(m.get("submittedDays"), "0"))
                        .append(" | ").append(nullTo(m.get("missingDays"), "0"))
                        .append(" |\n");
            }
        }
        return md.toString();
    }

    private Map<String, Object> emptyTool(String tool, String message) {
        return Map.of(
                "tool", tool,
                "data", Map.of("empty", true, "message", message),
                "markdown", "（" + message + "）"
        );
    }

    private void assertInternal(String token) {
        if (token == null || !internalToken.equals(token)) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "invalid internal token");
        }
    }

    private void requireIds(Long tenantId, Long userId) {
        if (tenantId == null || userId == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "tenantId/userId required");
        }
    }

    /** 优先用库内真实角色，避免工具可见范围与协同工作台不一致 */
    private String resolveRole(Long userId, String role) {
        try {
            String r = jdbc.queryForObject("SELECT role FROM users WHERE id = ? LIMIT 1", String.class, userId);
            if (r != null && !r.isBlank()) return r.trim();
        } catch (Exception ignored) {
        }
        if (role != null && !role.isBlank() && !"null".equalsIgnoreCase(role)) {
            return role.trim();
        }
        return "STUDENT";
    }

    private static Map<String, Object> pick(Map<?, ?> src, String... keys) {
        Map<String, Object> out = new LinkedHashMap<>();
        if (src == null) return out;
        for (String k : keys) {
            if (src.containsKey(k) && src.get(k) != null) {
                out.put(k, src.get(k));
            }
        }
        return out;
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> castMap(Map<?, ?> m) {
        Map<String, Object> out = new LinkedHashMap<>();
        for (Map.Entry<?, ?> e : m.entrySet()) {
            out.put(String.valueOf(e.getKey()), e.getValue());
        }
        return out;
    }

    private static Object first(Object... vals) {
        for (Object v : vals) {
            if (v != null && !(v instanceof String s && s.isBlank())) return v;
        }
        return null;
    }

    private static String clip(Object v, int max) {
        if (v == null) return null;
        String s = String.valueOf(v).replaceAll("\\s+", " ").trim();
        if (s.isEmpty()) return null;
        return s.length() <= max ? s : s.substring(0, max) + "…";
    }

    private static String str(Object v) {
        return v == null ? null : String.valueOf(v);
    }

    private static String nullTo(Object v, String dft) {
        String s = str(v);
        return s == null || s.isBlank() ? dft : s;
    }

    private static Long longVal(Object v) {
        if (v == null) return null;
        if (v instanceof Number n) return n.longValue();
        try {
            return Long.parseLong(String.valueOf(v));
        } catch (Exception e) {
            return null;
        }
    }
}
