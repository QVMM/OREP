package com.orep.backend.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.annotation.PostConstruct;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;
import org.springframework.util.LinkedCaseInsensitiveMap;
import org.springframework.web.server.ResponseStatusException;

import java.sql.PreparedStatement;
import java.sql.Statement;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.Collection;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

@Service
public class TeacherPortalService {
    private final JdbcTemplate jdbc;
    private final ObjectMapper objectMapper;
    private final TrainingDayContentService contentService;
    private final NotificationService notificationService;
    private final TrainingDayAvailabilityService trainingDayAvailabilityService;
    private final PlaybackLibraryService playbackLibraryService;
    private final StudentLearningAnalyticsService learningAnalytics;

    public TeacherPortalService(
            JdbcTemplate jdbc,
            ObjectMapper objectMapper,
            TrainingDayContentService contentService,
            NotificationService notificationService,
            TrainingDayAvailabilityService trainingDayAvailabilityService,
            PlaybackLibraryService playbackLibraryService,
            StudentLearningAnalyticsService learningAnalytics
    ) {
        this.jdbc = jdbc;
        this.objectMapper = objectMapper;
        this.contentService = contentService;
        this.notificationService = notificationService;
        this.playbackLibraryService = playbackLibraryService;
        this.trainingDayAvailabilityService = trainingDayAvailabilityService;
        this.learningAnalytics = learningAnalytics;
    }

    @PostConstruct
    void ensureTables() {
        jdbc.execute("""
            CREATE TABLE IF NOT EXISTS teacher_portal_event (
              id BIGINT PRIMARY KEY AUTO_INCREMENT,
              tenant_id BIGINT NOT NULL,
              actor_user_id BIGINT NOT NULL,
              event_type VARCHAR(60) NOT NULL,
              target_type VARCHAR(60) DEFAULT NULL,
              target_id BIGINT DEFAULT NULL,
              payload_json TEXT DEFAULT NULL,
              read_at DATETIME DEFAULT NULL,
              created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              KEY idx_teacher_event_tenant (tenant_id, created_at),
              KEY idx_teacher_event_target (target_type, target_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='教师端操作与提醒事件'
            """);
        try {
            jdbc.execute("ALTER TABLE teacher_portal_event ADD COLUMN read_at DATETIME NULL AFTER payload_json");
        } catch (Exception ignored) { }
        try {
            jdbc.execute("ALTER TABLE training_day ADD COLUMN requirements_json TEXT NULL COMMENT '教师编辑中的交付要求 JSON' AFTER summary");
        } catch (Exception ignored) { }
        try {
            jdbc.execute("ALTER TABLE training_day ADD COLUMN content_html LONGTEXT NULL COMMENT '经过服务端清洗的日任务富文本说明' AFTER summary");
        } catch (Exception ignored) { }
    }

    public Map<String, Object> workbench(Long tenantId, Long userId, String role) {
        List<Long> teamIds = accessibleTeamIds(tenantId, userId, role);
        if (teamIds.isEmpty()) return emptyWorkbench();
        String teamScope = idCsv(teamIds);
        Map<String, Object> camp = activeCamp(tenantId, teamIds);
        Long teamId = longValue(camp.get("teamId"));
        Long campId = longValue(camp.get("campId"));
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("camp", camp);
        result.put("teacherName", teacherDisplayName(userId));
        result.put("pendingReviews", scalar(("""
            SELECT COUNT(*) FROM project_task_submission s
            JOIN project_team t ON t.id=s.team_id
            WHERE t.tenant_id=? AND t.id IN (%s) AND s.status IN ('PENDING_REVIEW','REVIEWING')
              AND s.id=(SELECT x.id FROM project_task_submission x WHERE x.task_id=s.task_id
                        AND x.submitter_id=s.submitter_id
                        ORDER BY x.version_no DESC,x.id DESC LIMIT 1)
            """).formatted(teamScope), tenantId));
        result.put("runningMeetings", scalar(("""
            SELECT COUNT(DISTINCT m.id) FROM meeting m
            JOIN project_roadshow_binding b ON b.meeting_id=m.id AND b.team_id IN (%s)
            WHERE m.tenant_id=? AND m.status IN ('CREATED','RUNNING')
              AND DATE(COALESCE(m.start_time,m.created_at))=CURRENT_DATE
            """).formatted(teamScope), tenantId));
        result.put("aiTodos", scalar(("""
            SELECT COUNT(DISTINCT art.id)
            FROM ai_score_remediation_task art
            LEFT JOIN ai_score_report r ON r.id=art.latest_report_id
            LEFT JOIN ai_scoring_session s ON s.id=r.session_id
            LEFT JOIN project_roadshow_binding b ON b.meeting_id=r.meeting_id
            WHERE COALESCE(s.team_id,b.team_id) IN (%s)
              AND art.status IN ('not_started','draft','teacher_edited')
            """).formatted(teamScope)));
        result.put("missingToday", teamId == null || campId == null ? 0 : scalar("""
            SELECT COUNT(*) FROM project_team_member tm
            JOIN users u ON u.id=tm.user_id AND u.role='STUDENT'
            WHERE tm.team_id=? AND NOT EXISTS (
              SELECT 1 FROM training_day d
              JOIN training_day_task dt ON dt.training_day_id=d.id
              JOIN project_task_submission s ON s.task_id=dt.task_id AND s.submitter_id=tm.user_id
              WHERE d.camp_id=? AND d.training_date=CURRENT_DATE
            )
            """, teamId, campId));

        int onlineToday = scalar(("""
            SELECT COUNT(DISTINCT tm.user_id)
            FROM project_team_member tm
            JOIN project_team pt ON pt.id=tm.team_id AND pt.tenant_id=? AND pt.id IN (%s)
            JOIN users u ON u.id=tm.user_id AND u.role='STUDENT'
            LEFT JOIN user_online_status o ON o.user_id=tm.user_id
            WHERE (
              (o.last_seen_at IS NOT NULL AND o.last_seen_at >= CURDATE())
              OR EXISTS (
                SELECT 1 FROM student_learning_session s
                WHERE s.user_id=tm.user_id AND s.started_at >= CURDATE()
              )
              OR EXISTS (
                SELECT 1 FROM project_task_submission sub
                WHERE sub.submitter_id=tm.user_id AND sub.created_at >= CURDATE()
                  AND sub.team_id IN (%s)
              )
            )
            """).formatted(teamScope, teamScope), tenantId);
        result.put("onlineToday", onlineToday);

        int candidateCount = 0;
        try {
            candidateCount = projectTeamCandidateCount(tenantId, userId, role);
        } catch (Exception ignored) {
            candidateCount = 0;
        }
        result.put("candidateCount", candidateCount);

        int newReportCount = scalar(("""
            SELECT COUNT(DISTINCT %s) FROM ai_score_report r
            LEFT JOIN ai_scoring_session s ON s.id=r.session_id
            LEFT JOIN project_roadshow_binding b ON b.meeting_id=r.meeting_id
            WHERE r.status='completed'
              AND COALESCE(s.team_id,b.team_id) IN (%s)
              AND COALESCE(r.completed_at,r.created_at) >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
              AND %s
            """).formatted(DocketScoreStats.identitySql("s"), teamScope, DurationSkipReport.sqlNotSkipped("r")));
        result.put("newReportCount", newReportCount);

        int studentCount = scalar(("""
            SELECT COUNT(DISTINCT tm.user_id)
            FROM project_team_member tm
            JOIN project_team pt ON pt.id=tm.team_id AND pt.tenant_id=? AND pt.id IN (%s)
            JOIN users u ON u.id=tm.user_id AND u.role='STUDENT'
            """).formatted(teamScope), tenantId);
        result.put("studentCount", studentCount);

        // 状态副文案只陈述可核对指标，避免「宣传口吻」被当成假数据
        int missing = intValue(result.get("missingToday"));
        int pending = intValue(result.get("pendingReviews"));
        String statusTone = missing >= 3 || pending >= 8 ? "risk" : (missing > 0 || pending >= 3 ? "watch" : "good");
        String statusHeadline = statusTone.equals("risk")
                ? "今天有待跟进事项"
                : statusTone.equals("watch") ? "队伍运行平稳，仍有跟进项" : "队伍状态正常";
        List<String> detailBits = new ArrayList<>();
        detailBits.add("今日在线 " + onlineToday + " 人");
        if (pending > 0) detailBits.add("待批改 " + pending + " 份");
        if (missing > 0) detailBits.add("今日未交 " + missing + " 人");
        if (newReportCount > 0) detailBits.add("近7日评分 " + newReportCount + " 份");
        String statusDetail = String.join(" · ", detailBits);
        result.put("statusTone", statusTone);
        result.put("statusHeadline", statusHeadline);
        result.put("statusDetail", statusDetail);

        result.put("weeklyLearning", workbenchWeeklyLearning(tenantId, teamScope));
        result.put("progressStars", workbenchProgressStars(tenantId, teamScope));
        result.put("attention", workbenchAttention(teamId, campId, teamScope, tenantId));
        result.put("trainingLog", workbenchTrainingLog(tenantId, teamScope));
        result.put("latestScores", workbenchLatestScores(tenantId, teamScope));

        // 兼容旧字段
        result.put("timeline", timeline(tenantId, camp, teamIds));
        result.put("interventions", interventions(teamId));
        return result;
    }

    public List<Map<String, Object>> camps(Long tenantId, Long userId, String role) {
        List<Long> teamIds = accessibleTeamIds(tenantId, userId, role);
        if (teamIds.isEmpty()) return List.of();
        return jdbc.queryForList(("""
            SELECT c.id campId,c.name campName,c.subtitle,c.start_date startDate,c.end_date endDate,
                   c.total_days totalDays,c.status,pt.id teamId,pt.name teamName,
                   pt.start_date teamStartDate,pt.end_date teamEndDate
            FROM training_camp c
            JOIN training_camp_team ct ON ct.camp_id=c.id AND ct.status='ACTIVE'
            JOIN project_team pt ON pt.id=ct.team_id AND pt.tenant_id=c.tenant_id
            WHERE c.tenant_id=? AND pt.id IN (%s) AND c.status<>'ARCHIVED'
            ORDER BY CASE WHEN ? BETWEEN c.start_date AND c.end_date THEN 0 ELSE 1 END,
                     c.start_date DESC,c.id DESC,pt.id
            """).formatted(idCsv(teamIds)), tenantId, trainingDayAvailabilityService.today());
    }

    @Transactional
    public Map<String, Object> createCamp(Long tenantId, Long userId, String role, Map<String, Object> body) {
        List<Long> accessible = accessibleTeamIds(tenantId, userId, role);
        if (accessible.isEmpty()) throw new ResponseStatusException(HttpStatus.FORBIDDEN, "请先创建并关联备赛团队");
        List<Long> teamIds = longValues(body.get("teamIds"));
        if (teamIds.isEmpty()) {
            Long teamId = longValue(body.get("teamId"));
            if (teamId != null) teamIds = List.of(teamId);
        }
        if (teamIds.isEmpty()) throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "请选择参加集训的团队");
        for (Long teamId : teamIds) assertTeamAccess(tenantId, userId, role, teamId);

        LocalDate start = localDate(body.get("startDate"));
        LocalDate end = localDate(body.get("endDate"));
        if (start == null || end == null) throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "请设置集训开始日期和结束日期");
        if (end.isBefore(start)) throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "集训结束日期不能早于开始日期");
        long totalDays = ChronoUnit.DAYS.between(start, end) + 1;
        if (totalDays > 365) throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "单次集训周期不能超过 365 天");
        String name = text(body.get("name"));
        if (name == null) throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "集训营名称不能为空");

        for (Long teamId : teamIds) {
            int overlaps = scalar("""
                SELECT COUNT(*) FROM training_camp c
                JOIN training_camp_team ct ON ct.camp_id=c.id AND ct.status='ACTIVE'
                WHERE c.tenant_id=? AND ct.team_id=? AND c.status IN ('PLANNED','ACTIVE')
                  AND c.start_date<=? AND c.end_date>=?
                """, tenantId, teamId, end, start);
            if (overlaps > 0) throw new ResponseStatusException(HttpStatus.CONFLICT, "所选团队在该时间段已有集训营");
        }

        Long campId = insert("""
            INSERT INTO training_camp
            (tenant_id,name,subtitle,start_date,end_date,total_days,status,created_by)
            VALUES (?,?,?,?,?,?,'PLANNED',?)
            """, tenantId, name, text(body.get("subtitle")), start, end, totalDays, userId);
        for (Long teamId : teamIds) {
            jdbc.update("INSERT INTO training_camp_team(camp_id,team_id,status) VALUES (?,?,'ACTIVE')", campId, teamId);
        }

        int weekCount = (int) Math.ceil(totalDays / 7.0);
        List<Long> weekIds = new ArrayList<>();
        for (int weekNo = 1; weekNo <= weekCount; weekNo++) {
            LocalDate weekStart = start.plusDays((long) (weekNo - 1) * 7);
            LocalDate weekEnd = weekStart.plusDays(6).isAfter(end) ? end : weekStart.plusDays(6);
            weekIds.add(insert("""
                INSERT INTO training_camp_week(camp_id,week_no,title,start_date,end_date,sort_order)
                VALUES (?,?,?,?,?,?)
                """, campId, weekNo, "第 " + weekNo + " 周", weekStart, weekEnd, weekNo));
        }
        for (int dayNo = 1; dayNo <= totalDays; dayNo++) {
            LocalDate trainingDate = start.plusDays(dayNo - 1L);
            Long weekId = weekIds.get((dayNo - 1) / 7);
            jdbc.update("""
                INSERT INTO training_day
                (camp_id,week_id,day_no,training_date,title,summary,requirements_json,due_at,status,sort_order)
                VALUES (?,?,?,?,?,?,?,?,'DRAFT',?)
                """, campId, weekId, dayNo, trainingDate, "第 " + dayNo + " 天训练任务", "", "[]", trainingDate.atTime(22, 0), dayNo);
        }
        recordEvent(tenantId, userId, "CAMP_CREATED", "TRAINING_CAMP", campId, body);
        return campOverview(tenantId, userId, role, campId);
    }

    @Transactional
    public Map<String, Object> rescheduleCamp(
            Long tenantId,
            Long userId,
            String role,
            Long campId,
            Map<String, Object> body
    ) {
        Map<String, Object> camp = scopedCamp(tenantId, userId, role, campId);
        LocalDate oldStart = localDate(camp.get("startDate"));
        LocalDate newStart = localDate(body.get("startDate"));
        if (newStart == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "请选择新的集训开始日期");
        }
        if (oldStart == null) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "当前集训缺少原开始日期，无法改期");
        }
        int totalDays = Math.max(1, intValue(camp.get("totalDays")));
        LocalDate newEnd = newStart.plusDays(totalDays - 1L);
        if (newStart.equals(oldStart)) return campLifecycleSummary(campId, "RESCHEDULED");

        int submissions = scalar("""
            SELECT COUNT(*) FROM project_task_submission s
            JOIN training_day_task dt ON dt.task_id=s.task_id
            JOIN training_day d ON d.id=dt.training_day_id
            WHERE d.camp_id=?
            """, campId);
        if (submissions > 0) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "该集训已有学生提交，不能直接改期");
        }

        List<Long> teamIds = activeCampTeamIds(campId);
        for (Long teamId : teamIds) {
            int overlaps = scalar("""
                SELECT COUNT(*) FROM training_camp c
                JOIN training_camp_team ct ON ct.camp_id=c.id AND ct.status='ACTIVE'
                WHERE c.tenant_id=? AND c.id<>? AND ct.team_id=?
                  AND c.status IN ('PLANNED','ACTIVE')
                  AND c.start_date<=? AND c.end_date>=?
                """, tenantId, campId, teamId, newEnd, newStart);
            if (overlaps > 0) {
                throw new ResponseStatusException(HttpStatus.CONFLICT, "所选团队在新的时间段已有集训营");
            }
        }

        long offsetDays = ChronoUnit.DAYS.between(oldStart, newStart);
        LocalDate today = trainingDayAvailabilityService.today();
        String status = newStart.isAfter(today)
                ? "PLANNED"
                : newEnd.isBefore(today) ? "COMPLETED" : "ACTIVE";

        List<Map<String, Object>> weeks = jdbc.queryForList("""
            SELECT id,start_date startDate,end_date endDate
            FROM training_camp_week WHERE camp_id=? ORDER BY week_no,id
            """, campId);
        for (Map<String, Object> week : weeks) {
            LocalDate start = localDate(week.get("startDate"));
            LocalDate end = localDate(week.get("endDate"));
            jdbc.update("""
                UPDATE training_camp_week SET start_date=?,end_date=? WHERE id=?
                """,
                    start == null ? null : start.plusDays(offsetDays),
                    end == null ? null : end.plusDays(offsetDays),
                    week.get("id"));
        }

        String dayOrder = offsetDays > 0 ? "DESC" : "ASC";
        List<Map<String, Object>> days = jdbc.queryForList("""
            SELECT id,training_date trainingDate,due_at dueAt
            FROM training_day
            WHERE camp_id=?
            ORDER BY training_date %s,id %s
            """.formatted(dayOrder, dayOrder), campId);
        for (Map<String, Object> day : days) {
            Long dayId = longValue(day.get("id"));
            LocalDate trainingDate = localDate(day.get("trainingDate"));
            LocalDateTime dueAt = dateTime(day.get("dueAt"));
            jdbc.update("""
                UPDATE training_day
                SET training_date=?,due_at=?,early_unlocked_at=NULL
                WHERE id=?
                """,
                    trainingDate == null ? null : trainingDate.plusDays(offsetDays),
                    dueAt == null ? null : dueAt.plusDays(offsetDays),
                    dayId);
        }

        List<Map<String, Object>> tasks = jdbc.queryForList("""
            SELECT DISTINCT t.id,t.start_at startAt,t.due_at dueAt
            FROM project_task t
            JOIN training_day_task dt ON dt.task_id=t.id
            JOIN training_day d ON d.id=dt.training_day_id
            WHERE d.camp_id=?
            ORDER BY t.id
            """, campId);
        for (Map<String, Object> task : tasks) {
            LocalDateTime startAt = dateTime(task.get("startAt"));
            LocalDateTime dueAt = dateTime(task.get("dueAt"));
            jdbc.update("""
                UPDATE project_task SET start_at=?,due_at=?,updated_at=NOW() WHERE id=?
                """,
                    startAt == null ? null : startAt.plusDays(offsetDays),
                    dueAt == null ? null : dueAt.plusDays(offsetDays),
                    task.get("id"));
        }

        jdbc.update("""
            UPDATE training_camp
            SET start_date=?,end_date=?,status=?
            WHERE id=? AND tenant_id=?
            """, newStart, newEnd, status, campId, tenantId);
        recordEvent(tenantId, userId, "CAMP_RESCHEDULED", "TRAINING_CAMP", campId,
                Map.of("oldStartDate", oldStart, "startDate", newStart, "endDate", newEnd));
        return campLifecycleSummary(campId, "RESCHEDULED");
    }

    @Transactional
    public Map<String, Object> extendCamp(
            Long tenantId,
            Long userId,
            String role,
            Long campId,
            Map<String, Object> body
    ) {
        Map<String, Object> camp = scopedCamp(tenantId, userId, role, campId);
        LocalDate start = localDate(camp.get("startDate"));
        if (start == null) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "当前集训缺少开始日期，无法延长");
        }

        int currentTotal = Math.max(1, intValue(camp.get("totalDays")));
        int existingDayCount = scalar("SELECT COUNT(*) FROM training_day WHERE camp_id=?", campId);
        int existingMaxDayNo = scalar("SELECT COALESCE(MAX(day_no),0) FROM training_day WHERE camp_id=?", campId);
        int baseline = Math.max(currentTotal, Math.max(existingDayCount, existingMaxDayNo));
        int newTotal = resolveExtendedTotalDays(body, baseline);
        if (newTotal <= baseline) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "训练天数只能增加，不能减少或保持不变");
        }
        if (newTotal > 365) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "单次集训周期不能超过 365 天");
        }

        LocalDate newEnd = start.plusDays(newTotal - 1L);
        List<Long> teamIds = activeCampTeamIds(campId);
        for (Long teamId : teamIds) {
            int overlaps = scalar("""
                SELECT COUNT(*) FROM training_camp c
                JOIN training_camp_team ct ON ct.camp_id=c.id AND ct.status='ACTIVE'
                WHERE c.tenant_id=? AND c.id<>? AND ct.team_id=?
                  AND c.status IN ('PLANNED','ACTIVE')
                  AND c.start_date<=? AND c.end_date>=?
                """, tenantId, campId, teamId, newEnd, start);
            if (overlaps > 0) {
                throw new ResponseStatusException(HttpStatus.CONFLICT, "所选团队在延长后的时间段已有集训营");
            }
        }

        int weekCount = (int) Math.ceil(newTotal / 7.0);
        Map<Integer, Long> weekIds = new LinkedHashMap<>();
        List<Map<String, Object>> weeks = jdbc.queryForList("""
            SELECT id,week_no weekNo FROM training_camp_week WHERE camp_id=? ORDER BY week_no,id
            """, campId);
        for (Map<String, Object> week : weeks) {
            weekIds.put(intValue(week.get("weekNo")), longValue(week.get("id")));
        }
        for (int weekNo = 1; weekNo <= weekCount; weekNo++) {
            LocalDate weekStart = start.plusDays((long) (weekNo - 1) * 7);
            LocalDate weekEnd = weekStart.plusDays(6).isAfter(newEnd) ? newEnd : weekStart.plusDays(6);
            Long weekId = weekIds.get(weekNo);
            if (weekId == null) {
                weekId = insert("""
                    INSERT INTO training_camp_week(camp_id,week_no,title,start_date,end_date,sort_order)
                    VALUES (?,?,?,?,?,?)
                    """, campId, weekNo, "第 " + weekNo + " 周", weekStart, weekEnd, weekNo);
                weekIds.put(weekNo, weekId);
            } else {
                jdbc.update(
                        "UPDATE training_camp_week SET start_date=?,end_date=?,title=? WHERE id=?",
                        weekStart, weekEnd, "第 " + weekNo + " 周", weekId);
            }
        }

        int nextDayNo = existingMaxDayNo + 1;
        for (int dayNo = nextDayNo; dayNo <= newTotal; dayNo++) {
            LocalDate trainingDate = start.plusDays(dayNo - 1L);
            Long weekId = weekIds.get(((dayNo - 1) / 7) + 1);
            jdbc.update("""
                INSERT INTO training_day
                (camp_id,week_id,day_no,training_date,title,summary,requirements_json,due_at,status,sort_order)
                VALUES (?,?,?,?,?,?,?,?,'DRAFT',?)
                """, campId, weekId, dayNo, trainingDate, "第 " + dayNo + " 天训练任务", "", "[]",
                    trainingDate.atTime(22, 0), dayNo);
        }

        LocalDate today = trainingDayAvailabilityService.today();
        String status = start.isAfter(today)
                ? "PLANNED"
                : newEnd.isBefore(today) ? "COMPLETED" : "ACTIVE";
        jdbc.update("""
            UPDATE training_camp
            SET end_date=?,total_days=?,status=?
            WHERE id=? AND tenant_id=?
            """, newEnd, newTotal, status, campId, tenantId);
        recordEvent(tenantId, userId, "CAMP_EXTENDED", "TRAINING_CAMP", campId,
                Map.of("oldTotalDays", currentTotal, "totalDays", newTotal, "endDate", newEnd));
        return campLifecycleSummary(campId, "EXTENDED");
    }

    private int resolveExtendedTotalDays(Map<String, Object> body, int currentTotal) {
        if (body != null && body.get("addedDays") != null && !String.valueOf(body.get("addedDays")).isBlank()) {
            int added = intValue(body.get("addedDays"));
            if (added < 1) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "请输入要增加的训练天数");
            }
            return currentTotal + added;
        }
        if (body != null && body.get("totalDays") != null && !String.valueOf(body.get("totalDays")).isBlank()) {
            return intValue(body.get("totalDays"));
        }
        throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "请设置新的训练天数");
    }

    @Transactional
    public Map<String, Object> deleteCamp(
            Long tenantId,
            Long userId,
            String role,
            Long campId,
            Map<String, Object> body
    ) {
        Map<String, Object> camp = scopedCamp(tenantId, userId, role, campId);
        String mode = text(body.get("mode"));
        mode = mode == null ? "ARCHIVE" : mode.toUpperCase(Locale.ROOT);
        if (!Set.of("ARCHIVE", "PURGE").contains(mode)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "不支持的集训删除方式");
        }

        if ("ARCHIVE".equals(mode)) {
            jdbc.update("UPDATE training_camp SET status='ARCHIVED' WHERE id=? AND tenant_id=?", campId, tenantId);
            recordEvent(tenantId, userId, "CAMP_ARCHIVED", "TRAINING_CAMP", campId, body);
            return Map.of("campId", campId, "mode", "ARCHIVE", "status", "ARCHIVED");
        }

        String confirmationName = text(body.get("confirmationName"));
        String campName = text(camp.get("campName"));
        if (campName == null || !campName.equals(confirmationName)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "输入的集训名称不一致，无法彻底删除");
        }

        List<Long> dayIds = jdbc.queryForList(
                "SELECT id FROM training_day WHERE camp_id=? ORDER BY id",
                Long.class,
                campId);
        List<Long> taskIds = jdbc.queryForList("""
            SELECT DISTINCT dt.task_id
            FROM training_day_task dt
            JOIN training_day d ON d.id=dt.training_day_id
            WHERE d.camp_id=?
            ORDER BY dt.task_id
            """, Long.class, campId);
        List<String> storedUrls = new ArrayList<>();
        collectUrls(storedUrls, "training_day_attachment", "file_url", "training_day_id", dayIds);
        collectUrls(storedUrls, "training_day_learning_resource", "resource_url", "training_day_id", dayIds);
        collectUrls(storedUrls, "project_task_submission", "attachment_url", "task_id", taskIds);
        collectUrls(storedUrls, "project_submission_asset", "file_url", "task_id", taskIds);
        collectUrls(storedUrls, "project_material", "file_url", "linked_task_id", taskIds);

        List<Long> learningResourceIds = queryIds(
                "training_day_learning_resource",
                "SELECT id FROM training_day_learning_resource WHERE training_day_id IN (%s)",
                dayIds);
        deleteByIds("training_learning_progress", "learning_resource_id", learningResourceIds);
        deleteByIds("training_day_learning_resource", "training_day_id", dayIds);
        deleteByIds("training_day_attachment", "training_day_id", dayIds);

        deleteByIds("project_submission_asset", "task_id", taskIds);
        deleteByIds("project_submission_link", "task_id", taskIds);
        deleteByIds("project_material", "linked_task_id", taskIds);
        deleteByIds("project_task_assignee", "task_id", taskIds);
        deleteByIds("project_task_requirement", "task_id", taskIds);
        deleteByIds("project_task_submission", "task_id", taskIds);
        deleteByIds("training_day_task", "training_day_id", dayIds);
        deleteByIds("project_task", "id", taskIds);

        if (tableExists("teacher_portal_event")) {
            jdbc.update("""
                DELETE FROM teacher_portal_event
                WHERE tenant_id=? AND target_type='TRAINING_CAMP' AND target_id=?
                """, tenantId, campId);
        }
        jdbc.update("DELETE FROM training_day WHERE camp_id=?", campId);
        jdbc.update("DELETE FROM training_camp_week WHERE camp_id=?", campId);
        jdbc.update("DELETE FROM training_camp_team WHERE camp_id=?", campId);
        jdbc.update("DELETE FROM training_camp WHERE id=? AND tenant_id=?", campId, tenantId);
        deleteCampFilesAfterCommit(dayIds, storedUrls);
        return Map.of("campId", campId, "mode", "PURGE", "status", "DELETED");
    }

    public Map<String, Object> campOverview(Long tenantId, Long userId, String role) {
        return campOverview(tenantId, userId, role, null);
    }

    public Map<String, Object> campOverview(Long tenantId, Long userId, String role, Long requestedCampId) {
        List<Long> teamIds = accessibleTeamIds(tenantId, userId, role);
        Map<String, Object> camp = requestedCampId == null
                ? activeCamp(tenantId, teamIds)
                : campById(tenantId, teamIds, requestedCampId);
        if (camp.isEmpty()) return Map.of("hasCamp", false, "days", List.of(), "progress", List.of());
        Long campId = longValue(camp.get("campId"));
        Long teamId = longValue(camp.get("teamId"));
        List<Map<String, Object>> days = jdbc.queryForList("""
            SELECT d.id dayId,d.day_no dayNo,d.training_date trainingDate,d.title,d.summary,d.content_html contentHtml,
                   d.requirements_json requirementsJson,d.due_at dueAt,d.status,
                   d.early_unlocked_at earlyUnlockedAt,
                   COUNT(DISTINCT CASE WHEN s.status IN ('PENDING_REVIEW','REVIEWING','APPROVED','CHANGES_REQUESTED') THEN s.submitter_id END) submittedCount,
                   COUNT(DISTINCT CASE WHEN s.status IN ('PENDING_REVIEW','REVIEWING') THEN s.id END) pendingCount
            FROM training_day d
            LEFT JOIN training_day_task dt ON dt.training_day_id=d.id
            LEFT JOIN project_task_submission s ON s.task_id=dt.task_id
            WHERE d.camp_id=?
            GROUP BY d.id,d.day_no,d.training_date,d.title,d.summary,d.content_html,d.requirements_json,
                     d.due_at,d.status,d.early_unlocked_at
            ORDER BY d.day_no
            """, campId);
        for (Map<String, Object> day : days) {
            day.putAll(trainingDayAvailabilityService.availability(day));
            day.put("requirements", parseList(day.remove("requirementsJson")));
            day.put("attachments", contentService.teacherAttachments(tenantId, userId, role, longValue(day.get("dayId"))));
        }
        int memberCount = scalar("""
            SELECT COUNT(*) FROM project_team_member tm JOIN users u ON u.id=tm.user_id
            WHERE tm.team_id=? AND u.role='STUDENT'
            """, teamId);
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("hasCamp", true);
        result.put("camp", camp);
        result.put("memberCount", memberCount);
        result.put("days", days);
        result.put("progress", progressRows(campId, teamId));
        result.put("submissionCount", scalar("""
            SELECT COUNT(*) FROM project_task_submission s
            JOIN training_day_task dt ON dt.task_id=s.task_id
            JOIN training_day d ON d.id=dt.training_day_id
            WHERE d.camp_id=?
            """, campId));
        result.put("pendingReviews", scalar("""
            SELECT COUNT(*) FROM project_task_submission s
            JOIN training_day_task dt ON dt.task_id=s.task_id
            JOIN training_day d ON d.id=dt.training_day_id
            WHERE d.camp_id=? AND s.status IN ('PENDING_REVIEW','REVIEWING')
            """, campId));
        return result;
    }

    @Transactional
    public Map<String, Object> updateTrainingDay(Long tenantId, Long userId, String role, Long dayId, Map<String, Object> body) {
        scopedTrainingDay(tenantId, userId, role, dayId);
        Map<String, Object> row = one("""
            SELECT d.id,d.camp_id campId,d.training_date trainingDate,d.status dayStatus,
                   d.title,d.summary,d.content_html contentHtml,
                   d.requirements_json requirementsJson,d.due_at dueAt
            FROM training_day d
            JOIN training_camp c ON c.id=d.camp_id AND c.tenant_id=?
            WHERE d.id=?
            """, tenantId, dayId);
        if (row.isEmpty()) throw new ResponseStatusException(HttpStatus.NOT_FOUND, "训练日不存在");
        String title = text(body.get("title"));
        String summary = text(body.get("summary"));
        Object currentContent = row.get("contentHtml");
        String contentHtml = body.containsKey("contentHtml")
                ? contentService.sanitizeHtml(body.get("contentHtml"))
                : currentContent == null ? "" : String.valueOf(currentContent);
        LocalDateTime dueAt = dateTime(body.get("dueAt"));
        String status = text(body.get("status"));
        if (status != null) status = status.toUpperCase(Locale.ROOT);
        if (status != null && !Set.of("DRAFT", "PUBLISHED", "CLOSED").contains(status)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "不支持的训练日状态");
        }
        String currentStatus = text(row.get("dayStatus"));
        if ("DRAFT".equals(currentStatus) && "CLOSED".equals(status)) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "草稿训练日不能直接关闭");
        }
        if ("PUBLISHED".equals(currentStatus) && "DRAFT".equals(status)) status = "PUBLISHED";
        List<Map<String, Object>> requirements = body.containsKey("requirements")
                ? normalizeRequirements(body.get("requirements"))
                : parseList(row.get("requirementsJson"));
        String requirementsJson = json(requirements);
        jdbc.update("""
            UPDATE training_day SET title=COALESCE(?,title),summary=COALESCE(?,summary),content_html=?,
              requirements_json=?,due_at=COALESCE(?,due_at),status=COALESCE(?,status) WHERE id=?
            """, title, summary, contentHtml, requirementsJson, dueAt, status, dayId);
        String effectiveStatus = status == null ? currentStatus : status;
        String effectiveTitle = title == null ? text(row.get("title")) : title;
        String effectiveSummary = summary == null ? text(row.get("summary")) : summary;
        LocalDateTime effectiveDueAt = dueAt == null ? dateTime(row.get("dueAt")) : dueAt;
        if ("PUBLISHED".equals(effectiveStatus) && effectiveTitle == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "发布前请填写任务标题");
        }

        List<Map<String, Object>> linkedTasks = new ArrayList<>(jdbc.queryForList("""
            SELECT t.id taskId,t.team_id teamId
            FROM training_day_task dt
            JOIN project_task t ON t.id=dt.task_id
            WHERE dt.training_day_id=?
            ORDER BY t.team_id,t.id
            """, dayId));
        if ("PUBLISHED".equals(effectiveStatus)) {
            Set<Long> linkedTeamIds = linkedTasks.stream()
                    .map(task -> longValue(task.get("teamId")))
                    .filter(java.util.Objects::nonNull)
                    .collect(java.util.stream.Collectors.toSet());
            LocalDate trainingDate = localDate(row.get("trainingDate"));
            for (Long teamId : activeCampTeamIds(longValue(row.get("campId")))) {
                if (linkedTeamIds.contains(teamId)) continue;
                Long taskId = insert("""
                    INSERT INTO project_task
                    (team_id,stage_key,title,description,task_type,task_type_label,created_by,priority,status,start_at,due_at,review_required)
                    VALUES (?,'TRAINING',?,?,'TRAINING_DAY','集训任务',?,'MEDIUM','TODO',?,?,1)
                    """, teamId, effectiveTitle, effectiveSummary == null ? "" : effectiveSummary, userId,
                        trainingDate == null ? null : trainingDate.atStartOfDay(), effectiveDueAt);
                jdbc.update("""
                    INSERT INTO training_day_task(training_day_id,task_id,is_primary,sort_order)
                    VALUES (?,?,1,1)
                    """, dayId, taskId);
                linkedTasks.add(new LinkedHashMap<>(Map.of("taskId", taskId, "teamId", teamId)));
            }
        }

        for (Map<String, Object> linkedTask : linkedTasks) {
            Long taskId = longValue(linkedTask.get("taskId"));
            Long taskTeamId = longValue(linkedTask.get("teamId"));
            jdbc.update("""
                UPDATE project_task SET title=COALESCE(?,title),description=COALESCE(?,description),
                  due_at=COALESCE(?,due_at),status=CASE WHEN ?='CLOSED' THEN 'DONE' ELSE status END,
                  updated_at=NOW() WHERE id=?
                """, title, summary, dueAt, effectiveStatus, taskId);
            if ("PUBLISHED".equals(effectiveStatus)) {
                jdbc.update("DELETE FROM project_task_requirement WHERE task_id=?", taskId);
                int sort = 0;
                for (Map<String, Object> requirement : requirements) {
                    jdbc.update("""
                        INSERT INTO project_task_requirement(task_id,title,description,required,asset_type,sort_order)
                        VALUES (?,?,?,?,?,?)
                        """, taskId, requirement.get("title"), requirement.get("description"),
                            Boolean.TRUE.equals(requirement.get("required")) ? 1 : 0,
                            requirement.get("assetType"), sort++);
                }
                jdbc.update("DELETE FROM project_task_assignee WHERE task_id=?", taskId);
                jdbc.update("""
                    INSERT INTO project_task_assignee(task_id,team_id,user_id)
                    SELECT ?,tm.team_id,tm.user_id FROM project_team_member tm
                    JOIN users u ON u.id=tm.user_id AND u.role='STUDENT'
                    WHERE tm.team_id=?
                    """, taskId, taskTeamId);
            }
        }
        if ("PUBLISHED".equals(effectiveStatus)) {
            jdbc.update("UPDATE training_camp SET status='ACTIVE' WHERE id=? AND status='PLANNED'", row.get("campId"));
            contentService.activateAttachments(dayId);
            recordEvent(tenantId, userId, "TRAINING_DAY_PUBLISHED", "TRAINING_DAY", dayId, body);
        }
        Map<String, Object> updated = one("""
            SELECT id dayId,day_no dayNo,training_date trainingDate,title,summary,
                   content_html contentHtml,due_at dueAt,status,
                   early_unlocked_at earlyUnlockedAt
            FROM training_day WHERE id=?
            """, dayId);
        updated.putAll(trainingDayAvailabilityService.availability(updated));
        updated.put("requirements", requirements);
        updated.put("attachments", contentService.teacherAttachments(tenantId, userId, role, dayId));
        List<Long> taskIds = linkedTasks.stream()
                .map(task -> longValue(task.get("taskId")))
                .filter(java.util.Objects::nonNull)
                .toList();
        updated.put("taskIds", taskIds);
        updated.put("taskId", taskIds.isEmpty() ? null : taskIds.get(0));
        return updated;
    }

    @Transactional
    public Map<String, Object> earlyUnlockTrainingDay(
            Long tenantId,
            Long userId,
            String role,
            Long dayId
    ) {
        Map<String, Object> day = scopedTrainingDay(tenantId, userId, role, dayId);
        if (!"PUBLISHED".equals(String.valueOf(day.get("status")))) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "仅已发布训练日可提前开放");
        }
        LocalDateTime unlockedAt = trainingDayAvailabilityService.now();
        jdbc.update("UPDATE training_day SET early_unlocked_at = ? WHERE id = ?", unlockedAt, dayId);
        day.put("earlyUnlockedAt", unlockedAt);
        day.putAll(trainingDayAvailabilityService.availability(day));
        return day;
    }

    @Transactional
    public Map<String, Object> restoreAutomaticUnlock(
            Long tenantId,
            Long userId,
            String role,
            Long dayId
    ) {
        Map<String, Object> day = scopedTrainingDay(tenantId, userId, role, dayId);
        if (!"PUBLISHED".equals(String.valueOf(day.get("status")))) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "仅已发布训练日可恢复自动开放");
        }
        jdbc.update("UPDATE training_day SET early_unlocked_at = NULL WHERE id = ?", dayId);
        day.put("earlyUnlockedAt", null);
        day.putAll(trainingDayAvailabilityService.availability(day));
        return day;
    }

    public List<Map<String, Object>> recordings(Long tenantId, Long userId, String role) {
        List<Long> teamIds = accessibleTeamIds(tenantId, userId, role);
        return playbackLibraryService.listForTeacher(tenantId, userId, teamIds);
    }

    public List<Map<String, Object>> resources(Long tenantId, Long userId, String role) {
        List<Long> teamIds = accessibleTeamIds(tenantId, userId, role);
        if (teamIds.isEmpty()) return List.of();
        return jdbc.queryForList(("""
            SELECT pm.id,pm.team_id teamId,pt.name teamName,pm.material_type materialType,
                   pm.name,pm.description,pm.file_url fileUrl,pm.review_status reviewStatus,
                   pm.review_comment reviewComment,pm.created_at createdAt,pm.updated_at updatedAt,
                   owner.username ownerName
            FROM project_material pm JOIN project_team pt ON pt.id=pm.team_id AND pt.tenant_id=? AND pt.id IN (%s)
            LEFT JOIN users owner ON owner.id=pm.owner_user_id
            ORDER BY pm.updated_at DESC,pm.id DESC
            """).formatted(idCsv(teamIds)), tenantId);
    }

    /**
     * 学生 AI 生成的 PPT 任务（ppt_task），按教师可访问团队成员过滤。
     */
    public List<Map<String, Object>> aiPptWorks(Long tenantId, Long userId, String role) {
        List<Long> teamIds = accessibleTeamIds(tenantId, userId, role);
        if (teamIds.isEmpty()) return List.of();
        String teamScope = idCsv(teamIds);
        try {
            List<Map<String, Object>> rows = jdbc.queryForList(("""
                SELECT t.id taskId, t.user_id studentUserId, u.username studentName,
                       t.project_name projectName, t.team_name teamNameHint,
                       t.domain, t.theme, t.status, t.progress, t.current_step currentStep,
                       t.pptx_path pptxPath, t.error_msg errorMsg,
                       t.created_at createdAt, t.updated_at updatedAt,
                       (SELECT MIN(pt.name) FROM project_team_member tm
                          JOIN project_team pt ON pt.id = tm.team_id AND pt.tenant_id = ?
                          WHERE tm.user_id = t.user_id AND pt.id IN (%s)
                       ) teamName,
                       (SELECT COUNT(*) FROM ppt_html_page hp WHERE hp.task_id = t.id) pageCount
                FROM ppt_task t
                JOIN users u ON u.id = t.user_id
                WHERE u.role = 'STUDENT'
                  AND EXISTS (
                    SELECT 1 FROM project_team_member tm
                    JOIN project_team pt ON pt.id = tm.team_id AND pt.tenant_id = ?
                    WHERE tm.user_id = t.user_id AND pt.id IN (%s)
                  )
                ORDER BY t.updated_at DESC, t.id DESC
                LIMIT 200
                """).formatted(teamScope, teamScope), tenantId, tenantId);
            for (Map<String, Object> row : rows) {
                String status = String.valueOf(row.getOrDefault("status", ""));
                boolean completed = "completed".equalsIgnoreCase(status);
                Object path = row.get("pptxPath");
                row.put("downloadUrl", completed ? "/api/ppt/task/" + row.get("taskId") + "/download" : null);
                row.put("historyPath", "/ppt-history/" + row.get("taskId"));
                row.put("hasFile", completed && path != null && !String.valueOf(path).isBlank());
                row.put("statusLabel", pptStatusLabel(status));
            }
            return rows;
        } catch (Exception e) {
            return List.of();
        }
    }

    /**
     * 学生 AI/编辑器讲稿（script 表），按教师可访问团队成员过滤。
     */
    public List<Map<String, Object>> aiScripts(Long tenantId, Long userId, String role) {
        List<Long> teamIds = accessibleTeamIds(tenantId, userId, role);
        if (teamIds.isEmpty()) return List.of();
        String teamScope = idCsv(teamIds);
        try {
            List<Map<String, Object>> rows = jdbc.queryForList(("""
                SELECT s.id scriptId, s.title, s.source_type sourceType, s.ppt_job_id pptJobId,
                       s.sync_status syncStatus, s.content_version contentVersion,
                       s.created_by studentUserId, u.username studentName,
                       s.created_at createdAt, s.updated_at updatedAt,
                       CHAR_LENGTH(COALESCE(s.content, '')) contentLength,
                       (SELECT MIN(pt.name) FROM project_team_member tm
                          JOIN project_team pt ON pt.id = tm.team_id AND pt.tenant_id = ?
                          WHERE tm.user_id = s.created_by AND pt.id IN (%s)
                       ) teamName
                FROM script s
                JOIN users u ON u.id = s.created_by
                WHERE u.role = 'STUDENT'
                  AND EXISTS (
                    SELECT 1 FROM project_team_member tm
                    JOIN project_team pt ON pt.id = tm.team_id AND pt.tenant_id = ?
                    WHERE tm.user_id = s.created_by AND pt.id IN (%s)
                  )
                ORDER BY s.updated_at DESC, s.id DESC
                LIMIT 200
                """).formatted(teamScope, teamScope), tenantId, tenantId);
            for (Map<String, Object> row : rows) {
                String source = String.valueOf(row.getOrDefault("sourceType", "manual"));
                row.put("sourceLabel", "ppt".equalsIgnoreCase(source) ? "来自 PPT" : "独立讲稿");
                row.put("editorPath", "/script-editor/" + row.get("scriptId"));
                row.put("pdfUrl", "/api/script/" + row.get("scriptId") + "/pdf");
                Object pptJob = row.get("pptJobId");
                if (pptJob != null && !String.valueOf(pptJob).isBlank() && !"null".equalsIgnoreCase(String.valueOf(pptJob))) {
                    // ppt_job_id 可能是字符串 job id；若可解析为 task 数字 id 则给历史链接
                    try {
                        long taskId = Long.parseLong(String.valueOf(pptJob));
                        row.put("pptHistoryPath", "/ppt-history/" + taskId);
                        row.put("pptTaskId", taskId);
                    } catch (NumberFormatException ignored) {
                        row.put("pptJobId", pptJob);
                    }
                }
            }
            return rows;
        } catch (Exception e) {
            return List.of();
        }
    }

    private static String pptStatusLabel(String status) {
        if (status == null) return "未知";
        return switch (status.toLowerCase(Locale.ROOT)) {
            case "pending" -> "排队中";
            case "generating", "rendering" -> "生成中";
            case "outline_ready" -> "大纲就绪";
            case "confirmed" -> "已确认";
            case "completed" -> "已完成";
            case "failed" -> "失败";
            case "cancelled" -> "已取消";
            default -> status;
        };
    }

    public Map<String, Object> exams(Long tenantId) {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("questionCount", scalar("SELECT COUNT(*) FROM exam_question WHERE status='enabled'"));
        result.put("papers", jdbc.queryForList("""
            SELECT p.id,p.title,p.description,p.duration_minutes durationMinutes,p.pass_score passScore,p.status,p.updated_at updatedAt,
                   COUNT(DISTINCT ppq.question_id) questionCount,COUNT(DISTINCT a.id) attemptCount,
                   ROUND(AVG(CASE WHEN a.status='submitted' THEN a.score END),1) averageScore
            FROM exam_paper p LEFT JOIN exam_paper_question ppq ON ppq.paper_id=p.id
            LEFT JOIN exam_attempt a ON a.paper_id=p.id
            GROUP BY p.id,p.title,p.description,p.duration_minutes,p.pass_score,p.status,p.updated_at
            ORDER BY p.updated_at DESC,p.id DESC
            """));
        return result;
    }

    public List<Map<String, Object>> aiTodos(Long tenantId, Long userId, String role) {
        List<Long> teamIds = accessibleTeamIds(tenantId, userId, role);
        if (teamIds.isEmpty()) return List.of();
        List<Map<String, Object>> rows = jdbc.queryForList(("""
            SELECT t.id,t.source_report_id sourceReportId,t.latest_report_id latestReportId,
                   t.title,t.task_json taskJson,t.status,t.updated_at updatedAt,
                   COALESCE(s.team_id,b.team_id) teamId,pt.name teamName
            FROM ai_score_remediation_task t
            LEFT JOIN ai_score_report r ON r.id=t.latest_report_id
            LEFT JOIN ai_scoring_session s ON s.id=r.session_id
            LEFT JOIN project_roadshow_binding b ON b.meeting_id=r.meeting_id
            LEFT JOIN project_team pt ON pt.id=COALESCE(s.team_id,b.team_id) AND pt.tenant_id=?
            WHERE pt.id IN (%s)
            ORDER BY CASE WHEN t.status IN ('not_started','draft','teacher_edited') THEN 0 ELSE 1 END,t.updated_at DESC,t.id DESC
            LIMIT 100
            """).formatted(idCsv(teamIds)), tenantId);
        for (Map<String, Object> row : rows) {
            Map<String, Object> json = parseMap(row.remove("taskJson"));
            row.put("origin", json.getOrDefault("problem", row.get("title")));
            row.put("draft", json.getOrDefault("title", row.get("title")));
            row.put("priority", json.getOrDefault("priority", "P2"));
            row.put("task", json);
        }
        return rows;
    }

    @Transactional
    public Map<String, Object> publishAiTodo(Long tenantId, Long userId, String role, Long todoId, Map<String, Object> body) {
        Map<String, Object> todo = one("""
            SELECT art.id,art.title,art.task_json taskJson,art.status,
                   COALESCE(s.team_id,b.team_id) sourceTeamId
            FROM ai_score_remediation_task art
            LEFT JOIN ai_score_report r ON r.id=art.latest_report_id
            LEFT JOIN ai_scoring_session s ON s.id=r.session_id
            LEFT JOIN project_roadshow_binding b ON b.meeting_id=r.meeting_id
            WHERE art.id=? LIMIT 1
            """, todoId);
        if (todo.isEmpty()) throw new ResponseStatusException(HttpStatus.NOT_FOUND, "AI 待办不存在");
        assertTeamAccess(tenantId, userId, role, longValue(todo.get("sourceTeamId")));
        Long teamId = longValue(body.get("teamId"));
        if (teamId == null || scalar("SELECT COUNT(*) FROM project_team WHERE id=? AND tenant_id=?", teamId, tenantId) == 0) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "请选择有效团队");
        }
        assertTeamAccess(tenantId, userId, role, teamId);
        Long ownerUserId = longValue(body.get("ownerUserId"));
        String title = text(body.get("title"));
        if (title == null) title = String.valueOf(todo.get("title"));
        String description = text(body.get("description"));
        LocalDateTime dueAt = dateTime(body.get("dueAt"));
        jdbc.update("""
            INSERT INTO project_task(team_id,stage_key,title,description,owner_user_id,created_by,priority,status,due_at,review_required,task_type,task_type_label)
            VALUES (?, 'REVIEW', ?, ?, ?, ?, 'HIGH', 'TODO', ?, 1, 'AI_REMEDIATION', 'AI 评分整改')
            """, teamId, title, description, ownerUserId, userId, dueAt);
        Long taskId = jdbc.queryForObject("SELECT LAST_INSERT_ID()", Long.class);
        if (ownerUserId != null) jdbc.update("INSERT IGNORE INTO project_task_assignee(task_id,user_id) VALUES (?,?)", taskId, ownerUserId);
        jdbc.update("UPDATE ai_score_remediation_task SET status='published',updated_at=NOW() WHERE id=?", todoId);
        recordEvent(tenantId, userId, "AI_TODO_PUBLISHED", "PROJECT_TASK", taskId, body);
        return Map.of("todoId", todoId, "taskId", taskId, "status", "published");
    }

    public Map<String, Object> analytics(Long tenantId, Long userId, String role) {
        List<Long> teamIds = accessibleTeamIds(tenantId, userId, role);
        if (teamIds.isEmpty()) return emptyAnalytics();
        String teamScope = idCsv(teamIds);
        Map<String, Object> camp = activeCamp(tenantId, teamIds);
        Long teamId = longValue(camp.get("teamId"));
        Long campId = longValue(camp.get("campId"));

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("teamCount", teamIds.size());
        result.put("studentCount", scalar(("SELECT COUNT(DISTINCT tm.user_id) FROM project_team_member tm JOIN project_team pt ON pt.id=tm.team_id JOIN users u ON u.id=tm.user_id AND u.role='STUDENT' WHERE pt.tenant_id=? AND pt.id IN (%s)").formatted(teamScope), tenantId));

        // 当前训练营上下文（老师最关心的范围）
        Map<String, Object> campView = new LinkedHashMap<>();
        if (!camp.isEmpty()) {
            campView.put("campId", campId);
            campView.put("campName", camp.get("campName"));
            campView.put("teamId", teamId);
            campView.put("teamName", camp.get("teamName"));
            campView.put("status", camp.get("status"));
            campView.put("startDate", camp.get("startDate"));
            campView.put("endDate", camp.get("endDate"));
            campView.put("totalDays", camp.get("totalDays"));
            campView.put("currentDay", camp.get("currentDay"));
            campView.put("remainingDays", camp.get("remainingDays"));
            campView.put("publishedPastDays", campId == null ? 0 : scalar(
                    "SELECT COUNT(*) FROM training_day WHERE camp_id=? AND training_date<=CURRENT_DATE AND status IN ('PUBLISHED','CLOSED')",
                    campId));
            campView.put("draftPastDays", campId == null ? 0 : scalar(
                    "SELECT COUNT(*) FROM training_day WHERE camp_id=? AND training_date<=CURRENT_DATE AND status='DRAFT'",
                    campId));
        }
        result.put("camp", campView);
        result.put("campName", campView.getOrDefault("campName", null));
        result.put("campId", campId);

        // 提交率：只统计已发布/已关闭且已到日期的训练日，避免草稿日把分母撑大
        Map<String, Object> submission = submissionStats(campId, teamId);
        result.putAll(submission);

        result.put("averageScore", decimalScalar(("""
            SELECT ROUND(AVG(ranked.score),1) FROM (
              SELECT r.overall_score score,
                     ROW_NUMBER() OVER (
                       PARTITION BY %s
                       ORDER BY COALESCE(r.completed_at, r.created_at) DESC, r.id DESC
                     ) rn
              FROM ai_score_report r
              LEFT JOIN ai_scoring_session s ON s.id=r.session_id
              LEFT JOIN project_roadshow_binding b ON b.meeting_id=r.meeting_id
              JOIN project_team pt ON pt.id=COALESCE(s.team_id,b.team_id) AND pt.tenant_id=? AND pt.id IN (%s)
              WHERE r.status='completed' AND r.overall_score IS NOT NULL
                AND %s
            ) ranked WHERE ranked.rn = 1
            """).formatted(DocketScoreStats.identitySql("s"), teamScope, DurationSkipReport.sqlNotSkipped("r")), tenantId));
        result.put("roadshowReportCount", scalar(("""
            SELECT COUNT(DISTINCT %s) FROM ai_score_report r
            LEFT JOIN ai_scoring_session s ON s.id=r.session_id
            LEFT JOIN project_roadshow_binding b ON b.meeting_id=r.meeting_id
            JOIN project_team pt ON pt.id=COALESCE(s.team_id,b.team_id) AND pt.tenant_id=? AND pt.id IN (%s)
            WHERE r.status='completed'
              AND %s
            """).formatted(DocketScoreStats.identitySql("s"), teamScope, DurationSkipReport.sqlNotSkipped("r")), tenantId));
        result.put("roadshowMeetingCount", teamIds.isEmpty() ? 0 : scalar(("""
            SELECT COUNT(DISTINCT m.id) FROM meeting m
            JOIN project_roadshow_binding b ON b.meeting_id=m.id AND b.team_id IN (%s)
            WHERE m.tenant_id=?
            """).formatted(teamScope), tenantId));
        result.put("pendingReviews", scalar(("SELECT COUNT(*) FROM project_task_submission s JOIN project_team t ON t.id=s.team_id WHERE t.tenant_id=? AND t.id IN (%s) AND s.status IN ('PENDING_REVIEW','REVIEWING')").formatted(teamScope), tenantId));
        result.put("dimensionStats", jdbc.queryForList(("""
            SELECT d.dimension_code dimensionCode,
                   ROUND(SUM(d.deducted_points),1) deductedPoints,
                   ROUND(SUM(d.max_recoverable_points),1) recoverablePoints,
                   COUNT(DISTINCT %s) sampleCount
            FROM ai_score_deduction d JOIN ai_score_report r ON r.id=d.report_id
            LEFT JOIN ai_scoring_session s ON s.id=r.session_id
            LEFT JOIN project_roadshow_binding b ON b.meeting_id=r.meeting_id
            JOIN project_team pt ON pt.id=COALESCE(s.team_id,b.team_id) AND pt.tenant_id=? AND pt.id IN (%s)
            WHERE %s
            GROUP BY d.dimension_code ORDER BY deductedPoints DESC
            """).formatted(DocketScoreStats.identitySql("s"), teamScope, DocketScoreStats.latestReportOnlySql("r", "s")), tenantId));
        result.put("dailySubmissions", jdbc.queryForList(("""
            SELECT DATE(s.created_at) date,COUNT(*) count FROM project_task_submission s
            JOIN project_team pt ON pt.id=s.team_id AND pt.tenant_id=? AND pt.id IN (%s)
            WHERE s.created_at>=DATE_SUB(CURRENT_DATE,INTERVAL 13 DAY)
            GROUP BY DATE(s.created_at) ORDER BY date
            """).formatted(teamScope), tenantId));

        // 缺交 / 风险学生：帮助老师定位问题
        result.put("missingStudents", missingStudents(campId, teamId));
        result.put("atRiskStudents", teamId == null ? List.of() : interventions(teamId));

        // 路演最近得分，便于看进步趋势
        List<Map<String, Object>> recentScoreRows = jdbc.queryForList(("""
            SELECT r.id reportId, r.overall_score score,
                   COALESCE(r.completed_at, r.created_at) scoredAt,
                   COALESCE(s.team_id, b.team_id) teamId, pt.name teamName,
                   COALESCE(s.session_no, CONCAT('报告 #', r.id)) title,
                   s.id sessionId, s.docket_id docketId,
                   r.critical_issues_json criticalIssuesJson
            FROM ai_score_report r
            LEFT JOIN ai_scoring_session s ON s.id=r.session_id
            LEFT JOIN project_roadshow_binding b ON b.meeting_id=r.meeting_id
            JOIN project_team pt ON pt.id=COALESCE(s.team_id,b.team_id) AND pt.tenant_id=? AND pt.id IN (%s)
            WHERE r.status='completed' AND r.overall_score IS NOT NULL
            ORDER BY COALESCE(r.completed_at, r.created_at) DESC
            LIMIT 40
            """).formatted(teamScope), tenantId);
        result.put("recentScores", ReportSummaryCollapser.collapse(recentScoreRows).stream().limit(8).toList());

        // 学生排行榜：时长 / 提交活跃 / 资源完成（与缺交名单、均分 KPI 互补，不重复）
        result.put("leaderboards", buildLeaderboards(tenantId, teamScope));

        return result;
    }

    /**
     * 学生档案列表：全员 + 训练/学习/路演摘要与风险标签。
     */
    public Map<String, Object> studentRoster(Long tenantId, Long userId, String role) {
        List<Long> teamIds = accessibleTeamIds(tenantId, userId, role);
        Map<String, Object> result = new LinkedHashMap<>();
        if (teamIds.isEmpty()) {
            result.put("camp", Map.of());
            result.put("students", List.of());
            return result;
        }
        String teamScope = idCsv(teamIds);
        Map<String, Object> camp = activeCamp(tenantId, teamIds);
        Long campId = longValue(camp.get("campId"));
        result.put("camp", camp.isEmpty() ? Map.of() : camp);

        List<Map<String, Object>> students = jdbc.queryForList(("""
            SELECT u.id userId, u.username studentName,
                   MAX(tm.position_name) positionName,
                   MIN(pt.id) teamId, MIN(pt.name) teamName
            FROM project_team_member tm
            JOIN project_team pt ON pt.id = tm.team_id AND pt.tenant_id = ? AND pt.id IN (%s)
            JOIN users u ON u.id = tm.user_id AND u.role = 'STUDENT'
            GROUP BY u.id, u.username
            ORDER BY u.id
            """).formatted(teamScope), tenantId);

        Map<Long, long[]> studyMap = studySecondsByUser(teamIds, tenantId);
        Map<Long, Map<String, Object>> preciseMap = preciseSecondsByUser(teamIds, tenantId);
        Map<Long, Map<String, Object>> trainMap = trainingStatsByUser(campId, teamIds);
        Map<Long, Map<String, Object>> scoreMap = scoreStatsByUser(tenantId, teamIds);
        Map<Long, Integer> remMap = openRemediationByUser(tenantId, teamIds);

        List<Map<String, Object>> rows = new ArrayList<>();
        for (Map<String, Object> s : students) {
            Long sid = longValue(s.get("userId"));
            Map<String, Object> row = new LinkedHashMap<>(s);
            long[] study = studyMap.getOrDefault(sid, new long[]{0L, 0L});
            Map<String, Object> precise = preciseMap.getOrDefault(sid, Map.of(
                    "platformVideoSeconds", 0L,
                    "embedVideoSeconds", 0L,
                    "taskBookDwellSeconds", 0L,
                    "typingSeconds", 0L,
                    "inspireOfficeSeconds", 0L,
                    "inspireOfficeEditSeconds", 0L,
                    "totalPreciseSeconds", 0L
            ));
            long preciseTotal = longValue(precise.get("totalPreciseSeconds")) == null
                    ? 0L : longValue(precise.get("totalPreciseSeconds"));
            // 列表「学习时长」优先展示专项合计（含启发 Office），避免老师看不到投入
            row.put("studySeconds", Math.max(study[0], preciseTotal));
            row.put("weekStudySeconds", study[1]);
            row.put("platformVideoSeconds", precise.get("platformVideoSeconds"));
            row.put("embedVideoSeconds", precise.get("embedVideoSeconds"));
            row.put("taskBookDwellSeconds", precise.get("taskBookDwellSeconds"));
            row.put("typingSeconds", precise.get("typingSeconds"));
            row.put("inspireOfficeSeconds", precise.get("inspireOfficeSeconds"));
            row.put("inspireOfficeEditSeconds", precise.get("inspireOfficeEditSeconds"));
            row.put("precise", precise);

            Map<String, Object> train = trainMap.getOrDefault(sid, Map.of());
            int submitted = intValue(train.get("submittedDays"));
            int due = intValue(train.get("dueDays"));
            int missing = intValue(train.get("missingDays"));
            int pending = intValue(train.get("pendingReviews"));
            row.put("submittedDays", submitted);
            row.put("dueDays", due);
            row.put("missingDays", missing);
            row.put("pendingReviews", pending);
            row.put("submissionRate", due <= 0 ? null : Math.min(100, Math.round(submitted * 100f / due)));

            Map<String, Object> score = scoreMap.getOrDefault(sid, Map.of());
            row.put("latestScore", score.get("latestScore"));
            row.put("averageScore", score.get("averageScore"));
            row.put("scoreCount", intValue(score.get("scoreCount")));
            row.put("openRemediations", remMap.getOrDefault(sid, 0));

            List<String> tags = new ArrayList<>();
            if (missing >= 2) tags.add("连续缺交");
            else if (missing == 1) tags.add("有缺交");
            if (study[0] == 0 && due > 0) tags.add("学习时长偏低");
            if (pending > 0) tags.add("待批改");
            if (remMap.getOrDefault(sid, 0) > 0) tags.add("整改中");
            if (intValue(score.get("scoreCount")) == 0 && !teamIds.isEmpty()) tags.add("未路演评分");
            row.put("riskTags", tags);
            rows.add(row);
        }
        // 缺交多的优先
        rows.sort((a, b) -> {
            int cmp = Integer.compare(intValue(b.get("missingDays")), intValue(a.get("missingDays")));
            if (cmp != 0) return cmp;
            return Long.compare(longValue(a.get("userId")), longValue(b.get("userId")));
        });
        result.put("students", rows);
        return result;
    }

    /**
     * 单个学生详细档案：训练 + 学习投入 + 路演 + 能力快照 + 整改。
     */
    public Map<String, Object> studentProfile(Long tenantId, Long teacherId, String role, Long studentUserId) {
        if (studentUserId == null) throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "学生 ID 不能为空");
        List<Long> teamIds = accessibleTeamIds(tenantId, teacherId, role);
        if (teamIds.isEmpty()) throw new ResponseStatusException(HttpStatus.FORBIDDEN, "无权查看学生档案");
        String teamScope = idCsv(teamIds);

        Map<String, Object> student = one(("""
            SELECT u.id userId, u.username studentName,
                   MAX(tm.position_name) positionName,
                   MIN(pt.id) teamId, MIN(pt.name) teamName
            FROM project_team_member tm
            JOIN project_team pt ON pt.id = tm.team_id AND pt.tenant_id = ? AND pt.id IN (%s)
            JOIN users u ON u.id = tm.user_id AND u.role = 'STUDENT'
            WHERE u.id = ?
            GROUP BY u.id, u.username
            LIMIT 1
            """).formatted(teamScope), tenantId, studentUserId);
        if (student.isEmpty()) throw new ResponseStatusException(HttpStatus.FORBIDDEN, "当前教师未覆盖该学生");

        Map<String, Object> camp = activeCamp(tenantId, teamIds);
        Long campId = longValue(camp.get("campId"));
        Long teamId = longValue(student.get("teamId"));
        if (teamId == null) teamId = longValue(camp.get("teamId"));

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("student", student);
        result.put("camp", camp.isEmpty() ? Map.of() : camp);

        // 训练日进度
        List<Map<String, Object>> dayRows = List.of();
        if (campId != null && teamId != null) {
            dayRows = progressRows(campId, teamId).stream()
                    .filter(m -> studentUserId.equals(longValue(m.get("userId"))))
                    .findFirst()
                    .map(m -> {
                        @SuppressWarnings("unchecked")
                        List<Map<String, Object>> days = (List<Map<String, Object>>) m.getOrDefault("days", List.of());
                        return days;
                    })
                    .orElse(List.of());
            // 仅展示已发布/已关闭日，避免草稿噪音
            if (campId != null) {
                Set<Long> publishedDayIds = new LinkedHashSet<>(jdbc.queryForList(
                        "SELECT id FROM training_day WHERE camp_id=? AND status IN ('PUBLISHED','CLOSED')",
                        Long.class, campId));
                dayRows = dayRows.stream()
                        .filter(d -> publishedDayIds.contains(longValue(d.get("dayId"))))
                        .toList();
            }
        }
        int submittedDays = (int) dayRows.stream().filter(d -> d.get("submissionId") != null).count();
        int missingDays = (int) dayRows.stream().filter(d -> {
            Object status = d.get("status");
            String st = status == null ? "" : String.valueOf(status).toUpperCase(Locale.ROOT);
            return "EXPIRED".equals(st) || "NOT_SUBMITTED".equals(st);
        }).count();
        int pendingReviews = (int) dayRows.stream().filter(d -> {
            Object status = d.get("status");
            String st = status == null ? "" : String.valueOf(status).toUpperCase(Locale.ROOT);
            return "PENDING_REVIEW".equals(st) || "REVIEWING".equals(st);
        }).count();
        int dueDays = dayRows.size();

        Map<String, Object> training = new LinkedHashMap<>();
        training.put("days", dayRows);
        training.put("submittedDays", submittedDays);
        training.put("dueDays", dueDays);
        training.put("missingDays", missingDays);
        training.put("pendingReviews", pendingReviews);
        training.put("submissionRate", dueDays <= 0 ? null : Math.min(100, Math.round(submittedDays * 100f / dueDays)));
        result.put("training", training);

        // 学习投入（复用学生端分析口径）
        List<Map<String, Object>> sessions = learningAnalytics.learningSessions(studentUserId);
        Map<String, Object> learningSummary = learningAnalytics.summary(sessions);
        Map<String, Object> learning = new LinkedHashMap<>(learningSummary);
        learning.put("distribution", learningAnalytics.distribution(sessions));
        // 精准时长：平台内视频 / 站外视频 / 任务书驻留 / 打字 / 启发 Office
        Map<String, Object> precise = learningAnalytics.preciseDurations(tenantId, studentUserId);
        learning.put("precise", precise);
        learning.put("platformVideoSeconds", precise.get("platformVideoSeconds"));
        learning.put("embedVideoSeconds", precise.get("embedVideoSeconds"));
        learning.put("taskBookDwellSeconds", precise.get("taskBookDwellSeconds"));
        learning.put("typingSeconds", precise.get("typingSeconds"));
        learning.put("inspireOfficeSeconds", precise.get("inspireOfficeSeconds"));
        learning.put("inspireOfficeEditSeconds", precise.get("inspireOfficeEditSeconds"));
        // 近 14 日热力（从 heatmap 截取）
        List<Map<String, Object>> heat = learningAnalytics.heatmap(sessions);
        LocalDate from = LocalDate.now(ZoneId.of("Asia/Shanghai")).minusDays(13);
        learning.put("recentDaily", heat.stream()
                .filter(h -> {
                    LocalDate d = localDate(h.get("date"));
                    return d != null && !d.isBefore(from);
                })
                .toList());
        result.put("learning", learning);

        // 路演评分
        List<Map<String, Object>> scores = jdbc.queryForList(("""
            SELECT r.id reportId, r.overall_score score,
                   COALESCE(r.completed_at, r.created_at) scoredAt,
                   s.session_no sessionNo, s.id sessionId, r.meeting_id meetingId,
                   s.docket_id docketId,
                   r.critical_issues_json criticalIssuesJson
            FROM ai_score_report r
            LEFT JOIN ai_scoring_session s ON s.id = r.session_id
            WHERE r.status = 'completed' AND r.overall_score IS NOT NULL
              AND (
                s.created_by = ?
                OR EXISTS (
                  SELECT 1 FROM roadshow_speaker_score rss
                  WHERE rss.matched_user_id = ? AND rss.meeting_id = r.meeting_id
                )
                OR EXISTS (
                  SELECT 1 FROM project_team_member tm
                  WHERE tm.user_id = ? AND tm.team_id = s.team_id
                )
                OR EXISTS (
                  SELECT 1 FROM project_roadshow_binding b
                  JOIN project_team_member tm ON tm.team_id = b.team_id
                  WHERE b.meeting_id = r.meeting_id AND tm.user_id = ?
                )
              )
              AND (
                s.team_id IN (%s)
                OR EXISTS (
                  SELECT 1 FROM project_roadshow_binding b
                  WHERE b.meeting_id = r.meeting_id AND b.team_id IN (%s)
                )
              )
            ORDER BY COALESCE(r.completed_at, r.created_at) DESC
            LIMIT 40
            """).formatted(teamScope, teamScope), studentUserId, studentUserId, studentUserId, studentUserId);
        scores = ReportSummaryCollapser.collapse(scores).stream().limit(12).toList();

        List<Map<String, Object>> dims = jdbc.queryForList(("""
            SELECT d.dimension_code dimensionCode,
                   ROUND(SUM(d.deducted_points),1) deductedPoints,
                   ROUND(SUM(d.max_recoverable_points),1) recoverablePoints,
                   COUNT(DISTINCT %s) sampleCount
            FROM ai_score_deduction d
            JOIN ai_score_report r ON r.id = d.report_id
            LEFT JOIN ai_scoring_session s ON s.id = r.session_id
            WHERE r.status = 'completed'
              AND %s
              AND (
                s.created_by = ?
                OR EXISTS (
                  SELECT 1 FROM roadshow_speaker_score rss
                  WHERE rss.matched_user_id = ? AND rss.meeting_id = r.meeting_id
                )
                OR EXISTS (
                  SELECT 1 FROM project_team_member tm
                  WHERE tm.user_id = ? AND tm.team_id = s.team_id
                )
                OR EXISTS (
                  SELECT 1 FROM project_roadshow_binding b
                  JOIN project_team_member tm ON tm.team_id = b.team_id
                  WHERE b.meeting_id = r.meeting_id AND tm.user_id = ?
                )
              )
              AND (
                s.team_id IN (%s)
                OR EXISTS (
                  SELECT 1 FROM project_roadshow_binding b
                  WHERE b.meeting_id = r.meeting_id AND b.team_id IN (%s)
                )
              )
            GROUP BY d.dimension_code
            ORDER BY deductedPoints DESC
            LIMIT 8
            """).formatted(
                    DocketScoreStats.identitySql("s"),
                    DocketScoreStats.latestReportOnlySql("r", "s"),
                    teamScope,
                    teamScope
            ), studentUserId, studentUserId, studentUserId, studentUserId);

        Object avgScore = null;
        if (!scores.isEmpty()) {
            double sum = 0;
            int n = 0;
            for (Map<String, Object> row : scores) {
                Object sc = row.get("score");
                if (sc instanceof Number num) {
                    sum += num.doubleValue();
                    n++;
                }
            }
            if (n > 0) avgScore = Math.round(sum / n * 10.0) / 10.0;
        }

        Map<String, Object> roadshow = new LinkedHashMap<>();
        roadshow.put("scores", scores);
        roadshow.put("dimensionStats", dims);
        roadshow.put("scoreCount", scores.size());
        roadshow.put("latestScore", scores.isEmpty() ? null : scores.get(0).get("score"));
        roadshow.put("averageScore", avgScore);
        result.put("roadshow", roadshow);

        // 能力画像：只用非 BASELINE 证据按维度加权；无真实证据则返回空（不展示占位 50 分）
        Map<String, Object> ability = buildRealAbility(teamId, studentUserId);
        result.put("ability", ability);

        List<Map<String, Object>> remediations = jdbc.queryForList(("""
            SELECT art.id todoId, art.title, art.status, art.updated_at updatedAt,
                   r.overall_score relatedScore
            FROM ai_score_remediation_task art
            LEFT JOIN ai_score_report r ON r.id = art.latest_report_id
            LEFT JOIN ai_scoring_session s ON s.id = r.session_id
            LEFT JOIN project_roadshow_binding b ON b.meeting_id = r.meeting_id
            WHERE COALESCE(s.team_id, b.team_id) IN (%s)
              AND s.created_by = ?
            ORDER BY art.updated_at DESC
            LIMIT 10
            """).formatted(teamScope), studentUserId);
        result.put("remediations", remediations);

        // 诊断摘要
        List<String> tags = new ArrayList<>();
        if (missingDays >= 2) tags.add("连续缺交");
        else if (missingDays == 1) tags.add("有缺交");
        long totalSec = longValue(learningSummary.get("totalSeconds")) == null ? 0L : longValue(learningSummary.get("totalSeconds"));
        long preciseTotal = longValue(precise.get("totalPreciseSeconds")) == null ? 0L : longValue(precise.get("totalPreciseSeconds"));
        long displayStudySec = Math.max(totalSec, preciseTotal);
        if (displayStudySec == 0 && dueDays > 0) tags.add("学习时长偏低");
        if (pendingReviews > 0) tags.add("待批改");
        if (scores.isEmpty()) tags.add("未路演评分");
        if (!remediations.isEmpty()) tags.add("有整改项");

        String oneLiner;
        if (missingDays >= 2) {
            oneLiner = "训练提交缺口较大，建议优先催交并核对是否卡在资源学习。";
        } else if (scores.isEmpty() && displayStudySec > 0) {
            oneLiner = "学习有投入，但尚未完成路演评分，可安排模拟或上传评分。";
        } else if (!scores.isEmpty() && missingDays == 0) {
            oneLiner = "训练提交较稳，可结合路演薄弱维度做针对性提升。";
        } else if (displayStudySec == 0 && missingDays > 0) {
            oneLiner = "学习与提交均偏弱，需要老师主动介入跟进。";
        } else {
            oneLiner = "整体平稳，可持续关注提交节奏与路演进步。";
        }

        Map<String, Object> summary = new LinkedHashMap<>();
        summary.put("oneLiner", oneLiner);
        summary.put("riskTags", tags);
        summary.put("submittedDays", submittedDays);
        summary.put("dueDays", dueDays);
        summary.put("missingDays", missingDays);
        summary.put("studySeconds", displayStudySec);
        summary.put("platformVideoSeconds", precise.get("platformVideoSeconds"));
        summary.put("embedVideoSeconds", precise.get("embedVideoSeconds"));
        summary.put("taskBookDwellSeconds", precise.get("taskBookDwellSeconds"));
        summary.put("typingSeconds", precise.get("typingSeconds"));
        summary.put("inspireOfficeSeconds", precise.get("inspireOfficeSeconds"));
        summary.put("inspireOfficeEditSeconds", precise.get("inspireOfficeEditSeconds"));
        summary.put("latestScore", roadshow.get("latestScore"));
        summary.put("pendingReviews", pendingReviews);
        result.put("summary", summary);
        return result;
    }

    /** 批量精准时长（列表页用，避免 N+1 明细查询） */
    private Map<Long, Map<String, Object>> preciseSecondsByUser(List<Long> teamIds, Long tenantId) {
        Map<Long, Map<String, Object>> map = new LinkedHashMap<>();
        if (teamIds == null || teamIds.isEmpty()) return map;
        String teamScope = idCsv(teamIds);
        try {
            List<Map<String, Object>> rows = jdbc.queryForList(("""
                SELECT u.id userId,
                       COALESCE(pv.sec, 0) platformVideoSeconds,
                       COALESCE(ev.sec, 0) embedVideoSeconds,
                       COALESCE(tb.sec, 0) taskBookDwellSeconds,
                       COALESCE(ty.sec, 0) typingSeconds,
                       COALESCE(io.sec, 0) inspireOfficeSeconds
                FROM (
                  SELECT DISTINCT tm.user_id id
                  FROM project_team_member tm
                  JOIN project_team pt ON pt.id = tm.team_id AND pt.tenant_id = ? AND pt.id IN (%s)
                  JOIN users u2 ON u2.id = tm.user_id AND u2.role = 'STUDENT'
                ) u
                LEFT JOIN (
                  SELECT p.user_id,
                         SUM(GREATEST(COALESCE(p.actual_learning_seconds,0), COALESCE(p.learned_seconds,0))) sec
                  FROM training_learning_progress p
                  JOIN training_day_learning_resource r ON r.id = p.learning_resource_id
                  WHERE UPPER(r.resource_type) = 'VIDEO'
                  GROUP BY p.user_id
                ) pv ON pv.user_id = u.id
                LEFT JOIN (
                  SELECT p.user_id,
                         SUM(GREATEST(COALESCE(p.actual_learning_seconds,0), COALESCE(p.learned_seconds,0))) sec
                  FROM training_learning_progress p
                  JOIN training_day_learning_resource r ON r.id = p.learning_resource_id
                  WHERE UPPER(r.resource_type) = 'EMBED_VIDEO'
                  GROUP BY p.user_id
                ) ev ON ev.user_id = u.id
                LEFT JOIN (
                  SELECT user_id, SUM(GREATEST(COALESCE(duration_seconds,0),0)) sec
                  FROM student_learning_session
                  WHERE UPPER(activity_type) = 'TASK_BOOK'
                  GROUP BY user_id
                ) tb ON tb.user_id = u.id
                LEFT JOIN (
                  SELECT user_id,
                         SUM(GREATEST(FLOOR(COALESCE(elapsed_ms,0)/1000), 0)) sec
                  FROM typing_session
                  WHERE tenant_id = ?
                    AND COALESCE(elapsed_ms, 0) > 0
                  GROUP BY user_id
                ) ty ON ty.user_id = u.id
                LEFT JOIN (
                  SELECT user_id, SUM(GREATEST(COALESCE(duration_seconds,0),0)) sec
                  FROM student_learning_session
                  WHERE UPPER(activity_type) = 'INSPIRE_OFFICE'
                  GROUP BY user_id
                ) io ON io.user_id = u.id
                """).formatted(teamScope), tenantId, tenantId);
            for (Map<String, Object> r : rows) {
                Long uid = longValue(r.get("userId"));
                if (uid == null) continue;
                long platform = longValue(r.get("platformVideoSeconds")) == null ? 0L : longValue(r.get("platformVideoSeconds"));
                long embed = longValue(r.get("embedVideoSeconds")) == null ? 0L : longValue(r.get("embedVideoSeconds"));
                long dwell = longValue(r.get("taskBookDwellSeconds")) == null ? 0L : longValue(r.get("taskBookDwellSeconds"));
                long typing = longValue(r.get("typingSeconds")) == null ? 0L : longValue(r.get("typingSeconds"));
                long inspire = longValue(r.get("inspireOfficeSeconds")) == null ? 0L : longValue(r.get("inspireOfficeSeconds"));
                Map<String, Object> precise = new LinkedHashMap<>();
                precise.put("platformVideoSeconds", platform);
                precise.put("embedVideoSeconds", embed);
                precise.put("taskBookDwellSeconds", dwell);
                precise.put("typingSeconds", typing);
                precise.put("inspireOfficeSeconds", inspire);
                precise.put("inspireOfficeEditSeconds", 0L);
                precise.put("totalPreciseSeconds", platform + embed + dwell + typing + inspire);
                map.put(uid, precise);
            }
        } catch (Exception ignored) {
            // typing_session / JSON_EXTRACT 等不可用时不影响档案列表
        }
        return map;
    }

    private Map<Long, long[]> studySecondsByUser(List<Long> teamIds, Long tenantId) {
        if (teamIds.isEmpty()) return Map.of();
        String teamScope = idCsv(teamIds);
        List<Map<String, Object>> rows = jdbc.queryForList(("""
            SELECT u.id userId,
                   COALESCE(SUM(act.durationSeconds), 0) totalSeconds,
                   COALESCE(SUM(CASE
                     WHEN act.startedAt >= DATE_SUB(CURRENT_DATE, INTERVAL WEEKDAY(CURRENT_DATE) DAY)
                     THEN act.durationSeconds ELSE 0 END), 0) weekSeconds
            FROM (
              SELECT DISTINCT tm.user_id
              FROM project_team_member tm
              JOIN project_team pt ON pt.id = tm.team_id AND pt.tenant_id = ? AND pt.id IN (%s)
              JOIN users u2 ON u2.id = tm.user_id AND u2.role = 'STUDENT'
            ) scope
            JOIN users u ON u.id = scope.user_id
            LEFT JOIN (
              SELECT user_id,
                     GREATEST(COALESCE(actual_learning_seconds,0), COALESCE(learned_seconds,0), 0) durationSeconds,
                     COALESCE(last_learned_at, updated_at, created_at) startedAt
              FROM training_learning_progress
              UNION ALL
              SELECT user_id, GREATEST(COALESCE(learned_seconds,0),0), COALESCE(last_learned_at, updated_at, created_at)
              FROM course_learning_progress
              UNION ALL
              SELECT user_id, GREATEST(TIMESTAMPDIFF(SECOND, started_at, submitted_at),0), started_at
              FROM exam_attempt WHERE started_at IS NOT NULL AND submitted_at IS NOT NULL
              UNION ALL
              SELECT user_id,
                     GREATEST(COALESCE(duration_seconds, TIMESTAMPDIFF(SECOND, joined_at, left_at), 0), 0),
                     joined_at
              FROM meeting_participant WHERE joined_at IS NOT NULL
              UNION ALL
              SELECT user_id, GREATEST(COALESCE(duration_seconds,0),0), started_at
              FROM student_learning_session
            ) act ON act.user_id = u.id AND GREATEST(COALESCE(act.durationSeconds,0),0) > 0
            GROUP BY u.id
            """).formatted(teamScope), tenantId);
        Map<Long, long[]> map = new LinkedHashMap<>();
        for (Map<String, Object> r : rows) {
            map.put(longValue(r.get("userId")), new long[]{
                    longValue(r.get("totalSeconds")) == null ? 0L : longValue(r.get("totalSeconds")),
                    longValue(r.get("weekSeconds")) == null ? 0L : longValue(r.get("weekSeconds"))
            });
        }
        return map;
    }

    private Map<Long, Map<String, Object>> trainingStatsByUser(Long campId, List<Long> teamIds) {
        Map<Long, Map<String, Object>> map = new LinkedHashMap<>();
        if (campId == null || teamIds.isEmpty()) return map;
        // 每个学生：应训日（已发布过去日）、已交、缺交、待批改
        List<Map<String, Object>> rows = jdbc.queryForList(("""
            SELECT u.id userId,
                   COUNT(DISTINCT d.id) dueDays,
                   COUNT(DISTINCT CASE WHEN hit.submissionId IS NOT NULL THEN d.id END) submittedDays,
                   COUNT(DISTINCT CASE WHEN hit.submissionId IS NULL THEN d.id END) missingDays,
                   COUNT(DISTINCT CASE WHEN hit.status IN ('PENDING_REVIEW','REVIEWING') THEN d.id END) pendingReviews
            FROM project_team_member tm
            JOIN users u ON u.id = tm.user_id AND u.role = 'STUDENT'
            JOIN training_day d ON d.camp_id = ?
              AND d.training_date <= CURRENT_DATE
              AND d.status IN ('PUBLISHED','CLOSED')
            LEFT JOIN (
              SELECT dt.training_day_id dayId, s.submitter_id submitterId,
                     MAX(s.id) submissionId,
                     SUBSTRING_INDEX(GROUP_CONCAT(s.status ORDER BY s.version_no DESC, s.id DESC), ',', 1) status
              FROM training_day_task dt
              JOIN project_task_submission s ON s.task_id = dt.task_id
              GROUP BY dt.training_day_id, s.submitter_id
            ) hit ON hit.dayId = d.id AND hit.submitterId = u.id
            WHERE tm.team_id IN (%s)
            GROUP BY u.id
            """).formatted(idCsv(teamIds)), campId);
        for (Map<String, Object> r : rows) {
            map.put(longValue(r.get("userId")), r);
        }
        return map;
    }

    private Map<Long, Map<String, Object>> scoreStatsByUser(Long tenantId, List<Long> teamIds) {
        Map<Long, Map<String, Object>> map = new LinkedHashMap<>();
        if (teamIds.isEmpty()) return map;
        String teamScope = idCsv(teamIds);
        List<Map<String, Object>> rows = jdbc.queryForList(("""
            SELECT ranked.userId userId,
                   COUNT(*) scoreCount,
                   ROUND(AVG(ranked.score),1) averageScore,
                   SUBSTRING_INDEX(GROUP_CONCAT(ranked.score ORDER BY ranked.scoredAt DESC), ',', 1) latestScore
            FROM (
              SELECT tm.user_id userId,
                     r.overall_score score,
                     COALESCE(r.completed_at, r.created_at) scoredAt,
                     ROW_NUMBER() OVER (
                       PARTITION BY tm.user_id, %s
                       ORDER BY COALESCE(r.completed_at, r.created_at) DESC, r.id DESC
                     ) rn
              FROM ai_score_report r
              JOIN ai_scoring_session s ON s.id = r.session_id
              JOIN project_team_member tm ON (
                tm.team_id = s.team_id
                OR EXISTS (
                  SELECT 1 FROM project_roadshow_binding b
                  WHERE b.meeting_id = r.meeting_id AND b.team_id = tm.team_id
                )
              )
              JOIN users u ON u.id = tm.user_id AND u.role = 'STUDENT'
              WHERE r.status = 'completed' AND r.overall_score IS NOT NULL
                AND %s
                AND (
                  s.team_id IN (%s)
                  OR EXISTS (
                    SELECT 1 FROM project_roadshow_binding b
                    WHERE b.meeting_id = r.meeting_id AND b.team_id IN (%s)
                  )
                )
            ) ranked
            WHERE ranked.rn = 1
            GROUP BY ranked.userId
            """).formatted(
                    DocketScoreStats.identitySql("s"),
                    DurationSkipReport.sqlNotSkipped("r"),
                    teamScope,
                    teamScope
            ));
        for (Map<String, Object> r : rows) {
            Long uid = longValue(r.get("userId"));
            if (uid == null) continue;
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("scoreCount", r.get("scoreCount"));
            m.put("averageScore", r.get("averageScore"));
            try {
                m.put("latestScore", r.get("latestScore") == null ? null : Double.valueOf(String.valueOf(r.get("latestScore"))));
            } catch (Exception e) {
                m.put("latestScore", r.get("latestScore"));
            }
            map.put(uid, m);
        }
        return map;
    }

    private static String normalizeAbilityKey(String raw) {
        if (raw == null || raw.isBlank()) return null;
        return switch (raw) {
            case "problemSolving", "problem_solving" -> "problemSolving";
            case "coding" -> "coding";
            case "communication" -> "communication";
            case "teamwork" -> "teamwork";
            case "presentation" -> "presentation";
            case "creativity" -> "creativity";
            default -> null;
        };
    }

    /**
     * 从 member_ability_evidence 仅汇总真实证据（排除 BASELINE）。
     * 没有真实证据时返回空 Map，前端不展示能力条。
     */
    private Map<String, Object> buildRealAbility(Long teamId, Long studentUserId) {
        if (teamId == null || studentUserId == null) return Map.of();
        List<Map<String, Object>> evidence = jdbc.queryForList("""
            SELECT dimension_key dimensionKey, source_type sourceType, score, weight, summary
            FROM member_ability_evidence
            WHERE user_id = ? AND team_id = ?
              AND source_type IS NOT NULL AND UPPER(source_type) <> 'BASELINE'
              AND weight > 0
            ORDER BY weight DESC, id DESC
            """, studentUserId, teamId);
        if (evidence.isEmpty()) return Map.of();

        Map<String, Integer> weightedSum = new LinkedHashMap<>();
        Map<String, Integer> weightSum = new LinkedHashMap<>();
        for (Map<String, Object> e : evidence) {
            String dim = String.valueOf(e.get("dimensionKey") == null ? "" : e.get("dimensionKey"));
            if (dim.isBlank()) continue;
            int score = intValue(e.get("score"));
            int weight = Math.max(1, intValue(e.get("weight")));
            weightedSum.merge(dim, score * weight, Integer::sum);
            weightSum.merge(dim, weight, Integer::sum);
        }
        if (weightedSum.isEmpty()) return Map.of();

        Map<String, Object> ability = new LinkedHashMap<>();
        for (Map.Entry<String, Integer> entry : weightedSum.entrySet()) {
            String out = normalizeAbilityKey(entry.getKey());
            if (out == null) continue;
            int w = weightSum.getOrDefault(entry.getKey(), 1);
            int val = Math.min(100, Math.max(0, Math.round(entry.getValue() * 1f / w)));
            ability.put(out, val);
        }
        if (ability.isEmpty()) return Map.of();
        ability.put("hasRealEvidence", true);
        ability.put("evidenceCount", evidence.size());
        ability.put("evidence", evidence.size() > 12 ? evidence.subList(0, 12) : evidence);
        ability.put("calculatedAt", jdbc.query("""
            SELECT MAX(created_at) FROM member_ability_evidence
            WHERE user_id = ? AND team_id = ? AND UPPER(COALESCE(source_type,'')) <> 'BASELINE'
            """, rs -> rs.next() ? rs.getTimestamp(1) : null, studentUserId, teamId));
        return ability;
    }

    private Map<Long, Integer> openRemediationByUser(Long tenantId, List<Long> teamIds) {
        Map<Long, Integer> map = new LinkedHashMap<>();
        if (teamIds.isEmpty()) return map;
        String teamScope = idCsv(teamIds);
        List<Map<String, Object>> rows = jdbc.queryForList(("""
            SELECT s.created_by userId, COUNT(*) cnt
            FROM ai_score_remediation_task art
            LEFT JOIN ai_score_report r ON r.id = art.latest_report_id
            LEFT JOIN ai_scoring_session s ON s.id = r.session_id
            LEFT JOIN project_roadshow_binding b ON b.meeting_id = r.meeting_id
            WHERE s.created_by IS NOT NULL
              AND COALESCE(s.team_id, b.team_id) IN (%s)
              AND LOWER(COALESCE(art.status,'')) NOT IN ('done','completed','closed','rejected')
            GROUP BY s.created_by
            """).formatted(teamScope));
        for (Map<String, Object> r : rows) {
            Long uid = longValue(r.get("userId"));
            if (uid != null) map.put(uid, intValue(r.get("cnt")));
        }
        return map;
    }

    public Map<String, Object> remind(Long tenantId, Long userId, String role, Map<String, Object> body) {
        Long targetId = longValue(body.get("targetId"));
        if (targetId == null) throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "提醒对象不能为空");
        String targetType = text(body.get("targetType"));
        List<Long> recipients;
        if ("TRAINING_CAMP".equals(targetType)) {
            List<Long> teamIds = accessibleTeamIds(tenantId, userId, role);
            if (teamIds.isEmpty() || scalar(("""
                SELECT COUNT(*) FROM training_camp c
                JOIN training_camp_team ct ON ct.camp_id=c.id AND ct.status='ACTIVE'
                WHERE c.id=? AND c.tenant_id=? AND ct.team_id IN (%s)
                """).formatted(idCsv(teamIds)), targetId, tenantId) == 0) {
                throw new ResponseStatusException(HttpStatus.FORBIDDEN, "当前教师未关联该集训营");
            }
            recipients = jdbc.queryForList(("""
                SELECT DISTINCT tm.user_id FROM training_camp c
                JOIN training_camp_team ct ON ct.camp_id=c.id AND ct.status='ACTIVE'
                JOIN project_team_member tm ON tm.team_id=ct.team_id
                JOIN users u ON u.id=tm.user_id AND u.role='STUDENT'
                WHERE c.id=? AND c.tenant_id=? AND ct.team_id IN (%s) AND EXISTS (
                  SELECT 1 FROM training_day d
                  WHERE d.camp_id=c.id AND d.training_date<=CURRENT_DATE
                    AND NOT EXISTS (
                      SELECT 1 FROM training_day_task dt
                      JOIN project_task_submission s ON s.task_id=dt.task_id AND s.submitter_id=tm.user_id
                      WHERE dt.training_day_id=d.id
                    )
                )
                """).formatted(idCsv(teamIds)), Long.class, targetId, tenantId);
        } else {
            if (!isAdministrator(role)) {
                List<Long> teamIds = accessibleTeamIds(tenantId, userId, role);
                if (teamIds.isEmpty() || scalar(("""
                    SELECT COUNT(*) FROM project_team_member tm
                    WHERE tm.user_id=? AND tm.team_id IN (%s)
                    """).formatted(idCsv(teamIds)), targetId) == 0) {
                    throw new ResponseStatusException(HttpStatus.FORBIDDEN, "无权提醒未关联团队的成员");
                }
            }
            recipients = List.of(targetId);
        }
        for (Long recipientId : recipients) {
            Map<String, Object> payload = new LinkedHashMap<>(body);
            payload.put("sourceTargetId", targetId);
            payload.put("recipientUserId", recipientId);
            notificationService.createReminder(tenantId, userId, recipientId, targetType, payload);
        }
        return Map.of("sent", !recipients.isEmpty(), "recipientCount", recipients.size(), "recipientIds", recipients, "sentAt", LocalDateTime.now());
    }

    private List<Map<String, Object>> progressRows(Long campId, Long teamId) {
        List<Map<String, Object>> members = jdbc.queryForList("""
            SELECT u.id userId,u.username,tm.position_name positionName FROM project_team_member tm
            JOIN users u ON u.id=tm.user_id AND u.role='STUDENT' WHERE tm.team_id=? ORDER BY u.id
            """, teamId);
        List<Map<String, Object>> days = jdbc.queryForList("SELECT id dayId,day_no dayNo,training_date trainingDate FROM training_day WHERE camp_id=? ORDER BY day_no", campId);
        for (Map<String, Object> member : members) {
            List<Map<String, Object>> statuses = new ArrayList<>();
            for (Map<String, Object> day : days) {
                List<Map<String, Object>> values = jdbc.queryForList("""
                    SELECT s.id submissionId,s.status,s.created_at submittedAt FROM training_day_task dt
                    JOIN project_task_submission s ON s.task_id=dt.task_id AND s.submitter_id=?
                    WHERE dt.training_day_id=? ORDER BY s.version_no DESC,s.id DESC LIMIT 1
                    """, member.get("userId"), day.get("dayId"));
                Map<String, Object> state = new LinkedHashMap<>(day);
                if (values.isEmpty()) {
                    LocalDate trainingDate = localDate(day.get("trainingDate"));
                    state.put("status", trainingDate != null && trainingDate.isBefore(LocalDate.now()) ? "EXPIRED" : "NOT_SUBMITTED");
                } else state.putAll(values.get(0));
                statuses.add(state);
            }
            member.put("days", statuses);
            member.put("submittedDays", statuses.stream().filter(v -> v.get("submissionId") != null).count());
        }
        return members;
    }

    private List<Map<String, Object>> timeline(Long tenantId, Map<String, Object> camp, List<Long> teamIds) {
        List<Map<String, Object>> rows = new ArrayList<>();
        // 注意：无 String.formatted 的 SQL 直接用 %H:%i；
        // 有 .formatted(...) 的 SQL 必须写 %%H:%%i，否则会被当成 Java 格式符。
        if (!camp.isEmpty()) rows.addAll(jdbc.queryForList("""
            SELECT d.training_date date, CONCAT('集训第 ', d.day_no, ' 天') type, d.title,
                   DATE_FORMAT(d.due_at, '%H:%i') time
            FROM training_day d
            WHERE d.camp_id = ?
              AND d.training_date BETWEEN CURRENT_DATE AND DATE_ADD(CURRENT_DATE, INTERVAL 7 DAY)
            ORDER BY d.training_date
            LIMIT 8
            """, camp.get("campId")));
        if (!teamIds.isEmpty()) rows.addAll(jdbc.queryForList(("""
            SELECT DISTINCT DATE(COALESCE(m.start_time, m.created_at)) date, '路演' type, m.title,
                   DATE_FORMAT(COALESCE(m.start_time, m.created_at), '%%H:%%i') time
            FROM meeting m
            JOIN project_roadshow_binding b ON b.meeting_id = m.id AND b.team_id IN (%s)
            WHERE m.tenant_id = ?
              AND DATE(COALESCE(m.start_time, m.created_at)) BETWEEN CURRENT_DATE AND DATE_ADD(CURRENT_DATE, INTERVAL 7 DAY)
            ORDER BY date
            LIMIT 8
            """).formatted(idCsv(teamIds)), tenantId));
        rows.sort((a, b) -> String.valueOf(a.get("date")).compareTo(String.valueOf(b.get("date"))));
        return rows;
    }

    private List<Map<String, Object>> interventions(Long teamId) {
        if (teamId == null) return List.of();
        return jdbc.queryForList("""
            SELECT u.id userId,u.username,
                   SUM(CASE WHEN day_hit.submissionId IS NULL THEN 1 ELSE 0 END) missingDays,
                   '已发布训练日缺交，需关注' reason
            FROM project_team_member tm
            JOIN users u ON u.id=tm.user_id AND u.role='STUDENT'
            JOIN training_camp_team ct ON ct.team_id=tm.team_id AND ct.status='ACTIVE'
            JOIN training_day d ON d.camp_id=ct.camp_id
              AND d.training_date<=CURRENT_DATE
              AND d.status IN ('PUBLISHED','CLOSED')
            LEFT JOIN (
              SELECT dt.training_day_id dayId, s.submitter_id submitterId, MAX(s.id) submissionId
              FROM training_day_task dt
              JOIN project_task_submission s ON s.task_id=dt.task_id
              GROUP BY dt.training_day_id, s.submitter_id
            ) day_hit ON day_hit.dayId=d.id AND day_hit.submitterId=u.id
            WHERE tm.team_id=?
            GROUP BY u.id,u.username
            HAVING missingDays>0
            ORDER BY missingDays DESC
            """, teamId);
    }

    private Map<String, Object> activeCamp(Long tenantId, List<Long> teamIds) {
        if (teamIds == null || teamIds.isEmpty()) return new LinkedHashMap<>();
        Map<String, Object> camp = one(("""
            SELECT c.id campId,c.name campName,c.subtitle,c.start_date startDate,c.end_date endDate,c.total_days totalDays,c.status,
                   pt.id teamId,pt.name teamName
            FROM training_camp c JOIN training_camp_team ct ON ct.camp_id=c.id AND ct.status='ACTIVE'
            JOIN project_team pt ON pt.id=ct.team_id AND pt.tenant_id=c.tenant_id
            WHERE c.tenant_id=? AND pt.id IN (%s) AND c.status IN ('ACTIVE','PLANNED')
            ORDER BY CASE WHEN ? BETWEEN c.start_date AND c.end_date THEN 0 ELSE 1 END,c.id DESC LIMIT 1
            """).formatted(idCsv(teamIds)), tenantId, trainingDayAvailabilityService.today());
        if (!camp.isEmpty()) {
            LocalDate start = localDate(camp.get("startDate"));
            LocalDate end = localDate(camp.get("endDate"));
            LocalDate today = trainingDayAvailabilityService.today();
            camp.put("currentDay", start == null ? 0 : Math.max(0, Math.min(intValue(camp.get("totalDays")), (int) (today.toEpochDay()-start.toEpochDay()+1))));
            camp.put("remainingDays", end == null ? 0 : Math.max(0, end.toEpochDay()-today.toEpochDay()));
        }
        return camp;
    }

    private Map<String, Object> campById(Long tenantId, List<Long> teamIds, Long campId) {
        if (campId == null || teamIds == null || teamIds.isEmpty()) return new LinkedHashMap<>();
        Map<String, Object> camp = one(("""
            SELECT c.id campId,c.name campName,c.subtitle,c.start_date startDate,c.end_date endDate,c.total_days totalDays,c.status,
                   pt.id teamId,pt.name teamName
            FROM training_camp c JOIN training_camp_team ct ON ct.camp_id=c.id AND ct.status='ACTIVE'
            JOIN project_team pt ON pt.id=ct.team_id AND pt.tenant_id=c.tenant_id
            WHERE c.tenant_id=? AND c.id=? AND pt.id IN (%s) LIMIT 1
            """).formatted(idCsv(teamIds)), tenantId, campId);
        decorateCampDates(camp);
        return camp;
    }

    private void decorateCampDates(Map<String, Object> camp) {
        if (camp == null || camp.isEmpty()) return;
        LocalDate start = localDate(camp.get("startDate"));
        LocalDate end = localDate(camp.get("endDate"));
        LocalDate today = trainingDayAvailabilityService.today();
        camp.put("currentDay", start == null ? 0 : Math.max(0, Math.min(intValue(camp.get("totalDays")), (int) (today.toEpochDay()-start.toEpochDay()+1))));
        camp.put("remainingDays", end == null ? 0 : Math.max(0, end.toEpochDay()-today.toEpochDay()));
    }

    private List<Long> accessibleTeamIds(Long tenantId, Long userId, String role) {
        if (tenantId == null || userId == null) return List.of();
        if (isAdministrator(role)) {
            return jdbc.queryForList("SELECT id FROM project_team WHERE tenant_id=? AND status='ACTIVE' ORDER BY id", Long.class, tenantId);
        }
        if (!"TEACHER".equals(String.valueOf(role).toUpperCase(Locale.ROOT))) return List.of();
        return jdbc.queryForList("""
            SELECT DISTINCT t.id FROM project_team t
            LEFT JOIN project_team_member mentor ON mentor.team_id=t.id
              AND mentor.user_id=? AND mentor.role_in_team='MENTOR'
            WHERE t.tenant_id=? AND t.status='ACTIVE'
              AND (t.mentor_id=? OR mentor.user_id IS NOT NULL)
            ORDER BY t.id
            """, Long.class, userId, tenantId, userId);
    }

    private void assertTeamAccess(Long tenantId, Long userId, String role, Long teamId) {
        if (teamId == null || !accessibleTeamIds(tenantId, userId, role).contains(teamId)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "当前教师未关联该团队");
        }
    }

    private Map<String, Object> scopedCamp(Long tenantId, Long userId, String role, Long campId) {
        Map<String, Object> camp = one("""
            SELECT id campId,name campName,start_date startDate,end_date endDate,total_days totalDays,status
            FROM training_camp
            WHERE id=? AND tenant_id=?
            LIMIT 1
            """, campId, tenantId);
        if (camp.isEmpty()) throw new ResponseStatusException(HttpStatus.NOT_FOUND, "集训营不存在");
        if (isAdministrator(role)) return camp;
        List<Long> campTeamIds = activeCampTeamIds(campId);
        List<Long> accessible = accessibleTeamIds(tenantId, userId, role);
        if (campTeamIds.isEmpty() || !accessible.containsAll(campTeamIds)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "当前教师未覆盖该营期全部团队");
        }
        return camp;
    }

    private Map<String, Object> campLifecycleSummary(Long campId, String operation) {
        Map<String, Object> result = one("""
            SELECT id campId,name campName,start_date startDate,end_date endDate,total_days totalDays,status
            FROM training_camp WHERE id=? LIMIT 1
            """, campId);
        result.put("operation", operation);
        return result;
    }

    private void collectUrls(
            List<String> target,
            String table,
            String urlColumn,
            String idColumn,
            List<Long> ids
    ) {
        if (ids.isEmpty() || !tableExists(table)) return;
        List<String> urls = jdbc.queryForList(
                ("SELECT %s FROM %s WHERE %s IN (%s) AND %s IS NOT NULL")
                        .formatted(urlColumn, table, idColumn, idCsv(ids), urlColumn),
                String.class);
        for (String url : urls) if (url != null && !url.isBlank()) target.add(url);
    }

    private List<Long> queryIds(String table, String sqlTemplate, List<Long> ids) {
        if (ids.isEmpty() || !tableExists(table)) return List.of();
        return jdbc.queryForList(sqlTemplate.formatted(idCsv(ids)), Long.class);
    }

    private void deleteByIds(String table, String idColumn, List<Long> ids) {
        if (ids.isEmpty() || !tableExists(table)) return;
        jdbc.update(("DELETE FROM %s WHERE %s IN (%s)").formatted(table, idColumn, idCsv(ids)));
    }

    private void deleteCampFilesAfterCommit(List<Long> dayIds, List<String> storedUrls) {
        if (!TransactionSynchronizationManager.isSynchronizationActive()) {
            contentService.deleteCampFiles(dayIds, storedUrls);
            return;
        }
        TransactionSynchronizationManager.registerSynchronization(new TransactionSynchronization() {
            @Override
            public void afterCommit() {
                contentService.deleteCampFiles(dayIds, storedUrls);
            }
        });
    }

    private boolean tableExists(String tableName) {
        Boolean exists = jdbc.execute((org.springframework.jdbc.core.ConnectionCallback<Boolean>) connection -> {
            try (java.sql.ResultSet tables = connection.getMetaData().getTables(
                    connection.getCatalog(), null, "%", new String[]{"TABLE"})) {
                while (tables.next()) {
                    if (tableName.equalsIgnoreCase(tables.getString("TABLE_NAME"))) return true;
                }
                return false;
            }
        });
        return Boolean.TRUE.equals(exists);
    }

    private Map<String, Object> scopedTrainingDay(
            Long tenantId,
            Long userId,
            String role,
            Long dayId
    ) {
        Map<String, Object> day = one("""
            SELECT d.id dayId, d.day_no dayNo, d.training_date trainingDate,
                   d.title, d.status, d.early_unlocked_at earlyUnlockedAt,
                   c.id campId
            FROM training_day d
            JOIN training_camp c ON c.id = d.camp_id AND c.tenant_id = ?
            WHERE d.id = ?
            LIMIT 1
            """, tenantId, dayId);
        if (day.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "训练日不存在");
        }
        if (isAdministrator(role)) return day;

        List<Long> accessibleTeamIds = accessibleTeamIds(tenantId, userId, role);
        List<Long> activeCampTeamIds = activeCampTeamIds(longValue(day.get("campId")));
        if (activeCampTeamIds.isEmpty() || !accessibleTeamIds.containsAll(activeCampTeamIds)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "当前教师未覆盖该营期全部团队");
        }
        return day;
    }

    private List<Long> activeCampTeamIds(Long campId) {
        return jdbc.queryForList("""
            SELECT team_id
            FROM training_camp_team
            WHERE camp_id = ? AND status = 'ACTIVE'
            ORDER BY team_id
            """, Long.class, campId);
    }

    private boolean isAdministrator(String role) {
        return Set.of("ADMIN", "SCHOOL_ADMIN").contains(String.valueOf(role).toUpperCase(Locale.ROOT));
    }

    private String idCsv(List<Long> ids) {
        if (ids == null || ids.isEmpty()) throw new IllegalArgumentException("团队范围不能为空");
        return ids.stream().map(String::valueOf).reduce((left, right) -> left + "," + right).orElseThrow();
    }

    private Map<String, Object> emptyWorkbench() {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("camp", Map.of());
        result.put("teacherName", "");
        result.put("pendingReviews", 0);
        result.put("runningMeetings", 0);
        result.put("aiTodos", 0);
        result.put("missingToday", 0);
        result.put("onlineToday", 0);
        result.put("candidateCount", 0);
        result.put("newReportCount", 0);
        result.put("studentCount", 0);
        result.put("statusTone", "good");
        result.put("statusHeadline", "欢迎使用教师工作台");
        result.put("statusDetail", "先创建或关联备赛项目，即可看到队伍动态。");
        result.put("weeklyLearning", List.of());
        result.put("progressStars", List.of());
        result.put("attention", List.of());
        result.put("trainingLog", List.of());
        result.put("latestScores", List.of());
        result.put("timeline", List.of());
        result.put("interventions", List.of());
        return result;
    }

    private String teacherDisplayName(Long userId) {
        if (userId == null) return "老师";
        try {
            String name = jdbc.queryForObject(
                    "SELECT username FROM users WHERE id=? LIMIT 1",
                    String.class,
                    userId
            );
            return name == null || name.isBlank() ? "老师" : name.trim();
        } catch (Exception ignored) {
            return "老师";
        }
    }

    private int projectTeamCandidateCount(Long tenantId, Long userId, String role) {
        // 与 ProjectTeamService.candidateMembers 口径一致：本租户未入队的学生
        return scalar("""
            SELECT COUNT(*) FROM users u
            WHERE u.tenant_id=? AND u.role='STUDENT'
              AND NOT EXISTS (
                SELECT 1 FROM project_team_member tm
                JOIN project_team pt ON pt.id=tm.team_id AND pt.tenant_id=u.tenant_id AND pt.status='ACTIVE'
                WHERE tm.user_id=u.id
              )
            """, tenantId);
    }

    /**
     * 近 7 天全队学习时长（小时）：滚动窗口 today-6…today，不是自然周。
     * 前端文案仍为「近 7 天」；X 轴仍用周几标签，对应实际日期。
     */
    private List<Map<String, Object>> workbenchWeeklyLearning(Long tenantId, String teamScope) {
        LocalDate today = trainingDayAvailabilityService.today();
        LocalDate weekStart = today.minusDays(6);
        Map<LocalDate, Long> secondsByDay = new LinkedHashMap<>();
        for (int i = 0; i < 7; i++) secondsByDay.put(weekStart.plusDays(i), 0L);

        List<Map<String, Object>> rows = jdbc.queryForList(("""
            SELECT DATE(act.started_at) dayDate, SUM(act.durationSeconds) totalSeconds
            FROM (
              SELECT s.user_id, s.started_at,
                     GREATEST(COALESCE(s.duration_seconds,0),0) durationSeconds
              FROM student_learning_session s
              WHERE s.tenant_id=? AND s.started_at >= ? AND s.started_at < ?
                AND s.user_id IN (
                  SELECT DISTINCT tm.user_id FROM project_team_member tm
                  JOIN project_team pt ON pt.id=tm.team_id AND pt.tenant_id=? AND pt.id IN (%s)
                  JOIN users u ON u.id=tm.user_id AND u.role='STUDENT'
                )
              UNION ALL
              SELECT p.user_id, COALESCE(p.last_learned_at, p.updated_at) started_at,
                     GREATEST(COALESCE(p.actual_learning_seconds,0), COALESCE(p.learned_seconds,0), 0) durationSeconds
              FROM training_learning_progress p
              WHERE COALESCE(p.last_learned_at, p.updated_at) >= ? AND COALESCE(p.last_learned_at, p.updated_at) < ?
                AND GREATEST(COALESCE(p.actual_learning_seconds,0), COALESCE(p.learned_seconds,0), 0) > 0
                AND p.user_id IN (
                  SELECT DISTINCT tm.user_id FROM project_team_member tm
                  JOIN project_team pt ON pt.id=tm.team_id AND pt.tenant_id=? AND pt.id IN (%s)
                  JOIN users u ON u.id=tm.user_id AND u.role='STUDENT'
                )
            ) act
            GROUP BY DATE(act.started_at)
            """).formatted(teamScope, teamScope),
                tenantId, weekStart.atStartOfDay(), today.plusDays(1).atStartOfDay(), tenantId,
                weekStart.atStartOfDay(), today.plusDays(1).atStartOfDay(), tenantId);

        for (Map<String, Object> row : rows) {
            LocalDate d = localDate(row.get("dayDate"));
            if (d != null && secondsByDay.containsKey(d)) {
                secondsByDay.put(d, Math.max(0L, longValue(row.get("totalSeconds")) == null ? 0L : longValue(row.get("totalSeconds"))));
            }
        }

        List<Map<String, Object>> points = new ArrayList<>();
        long maxSeconds = secondsByDay.values().stream().mapToLong(Long::longValue).max().orElse(0L);
        if (maxSeconds <= 0) maxSeconds = 1L;
        for (Map.Entry<LocalDate, Long> e : secondsByDay.entrySet()) {
            Map<String, Object> p = new LinkedHashMap<>();
            p.put("date", e.getKey().toString());
            p.put("label", weekdayLabelZh(e.getKey()));
            p.put("seconds", e.getValue());
            p.put("hours", Math.round(e.getValue() / 3600.0 * 10.0) / 10.0);
            p.put("minutes", Math.round(e.getValue() / 60.0));
            p.put("ratio", e.getValue() * 1.0 / maxSeconds);
            p.put("isToday", e.getKey().equals(today));
            p.put("isFuture", e.getKey().isAfter(today));
            points.add(p);
        }
        return points;
    }

    private static String weekdayLabelZh(LocalDate date) {
        return switch (date.getDayOfWeek()) {
            case MONDAY -> "周一";
            case TUESDAY -> "周二";
            case WEDNESDAY -> "周三";
            case THURSDAY -> "周四";
            case FRIDAY -> "周五";
            case SATURDAY -> "周六";
            case SUNDAY -> "周日";
        };
    }

    /** 进步之星：本周学习时长相对上周的提升（分钟）。 */
    private List<Map<String, Object>> workbenchProgressStars(Long tenantId, String teamScope) {
        LocalDate today = trainingDayAvailabilityService.today();
        LocalDate thisWeekStart = today.minusDays(today.getDayOfWeek().getValue() - 1L);
        LocalDate lastWeekStart = thisWeekStart.minusDays(7);
        List<Map<String, Object>> rows = jdbc.queryForList(("""
            SELECT u.id userId, u.username studentName,
                   COALESCE(SUM(CASE WHEN act.started_at >= ? AND act.started_at < ? THEN act.sec ELSE 0 END),0) thisWeekSeconds,
                   COALESCE(SUM(CASE WHEN act.started_at >= ? AND act.started_at < ? THEN act.sec ELSE 0 END),0) lastWeekSeconds
            FROM (
              SELECT DISTINCT tm.user_id
              FROM project_team_member tm
              JOIN project_team pt ON pt.id=tm.team_id AND pt.tenant_id=? AND pt.id IN (%s)
              JOIN users u2 ON u2.id=tm.user_id AND u2.role='STUDENT'
            ) scope
            JOIN users u ON u.id=scope.user_id
            LEFT JOIN (
              SELECT user_id, started_at, GREATEST(COALESCE(duration_seconds,0),0) sec
              FROM student_learning_session
              WHERE tenant_id=? AND started_at >= ? AND started_at < ?
              UNION ALL
              SELECT user_id, COALESCE(last_learned_at, updated_at) started_at,
                     GREATEST(COALESCE(actual_learning_seconds,0), COALESCE(learned_seconds,0), 0) sec
              FROM training_learning_progress
              WHERE COALESCE(last_learned_at, updated_at) >= ? AND COALESCE(last_learned_at, updated_at) < ?
            ) act ON act.user_id=u.id
            GROUP BY u.id, u.username
            ORDER BY (thisWeekSeconds - lastWeekSeconds) DESC, thisWeekSeconds DESC, u.id ASC
            LIMIT 5
            """).formatted(teamScope),
                thisWeekStart.atStartOfDay(), thisWeekStart.plusDays(7).atStartOfDay(),
                lastWeekStart.atStartOfDay(), thisWeekStart.atStartOfDay(),
                tenantId,
                tenantId, lastWeekStart.atStartOfDay(), thisWeekStart.plusDays(7).atStartOfDay(),
                lastWeekStart.atStartOfDay(), thisWeekStart.plusDays(7).atStartOfDay());

        List<Map<String, Object>> stars = new ArrayList<>();
        int rank = 1;
        for (Map<String, Object> row : rows) {
            long thisW = longValue(row.get("thisWeekSeconds")) == null ? 0L : longValue(row.get("thisWeekSeconds"));
            long lastW = longValue(row.get("lastWeekSeconds")) == null ? 0L : longValue(row.get("lastWeekSeconds"));
            long deltaMin = Math.round((thisW - lastW) / 60.0);
            if (thisW <= 0 && lastW <= 0) continue;
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("userId", row.get("userId"));
            item.put("studentName", row.get("studentName"));
            item.put("rank", rank++);
            item.put("thisWeekMinutes", Math.round(thisW / 60.0));
            item.put("deltaMinutes", deltaMin);
            item.put("label", rank == 2 ? "进步幅度最大" : ("第" + (rank - 1) + "名"));
            // fix label after rank++
            stars.add(item);
        }
        // 修正 label
        for (int i = 0; i < stars.size(); i++) {
            Map<String, Object> item = stars.get(i);
            int r = i + 1;
            item.put("rank", r);
            item.put("label", r == 1 ? "进步幅度最大" : ("第" + r + "名"));
        }
        return stars.stream().limit(3).toList();
    }

    /**
     * 需要关注：不使用「打卡」口径；避开首页已展示的「今日未交 / 学习排行 / 按日提交人数」。
     * 优先：待批改堆积 → 本周学习为 0 → 近 7 日无训练提交。
     */
    private List<Map<String, Object>> workbenchAttention(Long teamId, Long campId, String teamScope, Long tenantId) {
        List<Map<String, Object>> items = new ArrayList<>();
        Set<Object> seen = new LinkedHashSet<>();

        // 1) 有待批改提交的学生（教师可行动）
        try {
            List<Map<String, Object>> pending = jdbc.queryForList(("""
                SELECT u.id userId, u.username studentName, COUNT(*) pendingCount
                FROM project_task_submission s
                JOIN project_team pt ON pt.id=s.team_id AND pt.tenant_id=? AND pt.id IN (%s)
                JOIN users u ON u.id=s.submitter_id AND u.role='STUDENT'
                WHERE s.status IN ('PENDING_REVIEW','REVIEWING')
                  AND s.id=(
                    SELECT x.id FROM project_task_submission x
                    WHERE x.task_id=s.task_id AND x.submitter_id=s.submitter_id
                    ORDER BY x.version_no DESC, x.id DESC LIMIT 1
                  )
                GROUP BY u.id, u.username
                ORDER BY pendingCount DESC, u.id ASC
                LIMIT 5
                """).formatted(teamScope), tenantId);
            for (Map<String, Object> row : pending) {
                int count = intValue(row.get("pendingCount"));
                Map<String, Object> item = new LinkedHashMap<>();
                item.put("userId", row.get("userId"));
                item.put("studentName", row.get("studentName"));
                item.put("reason", count + " 份提交待批改");
                item.put("level", count >= 3 ? "critical" : "watch");
                item.put("tag", count >= 3 ? "待批改堆积" : "待批改");
                items.add(item);
                seen.add(row.get("userId"));
            }
        } catch (Exception ignored) {
            // optional
        }

        // 2) 本周学习时长为 0（与进步之星互补：那边是学得多的）
        try {
            LocalDate today = trainingDayAvailabilityService.today();
            LocalDate weekStart = today.minusDays(today.getDayOfWeek().getValue() - 1L);
            List<Map<String, Object>> idle = jdbc.queryForList(("""
                SELECT u.id userId, u.username studentName
                FROM (
                  SELECT DISTINCT tm.user_id
                  FROM project_team_member tm
                  JOIN project_team pt ON pt.id=tm.team_id AND pt.tenant_id=? AND pt.id IN (%s)
                  JOIN users u2 ON u2.id=tm.user_id AND u2.role='STUDENT'
                ) scope
                JOIN users u ON u.id=scope.user_id
                LEFT JOIN (
                  SELECT user_id, SUM(sec) totalSec FROM (
                    SELECT user_id, GREATEST(COALESCE(duration_seconds,0),0) sec
                    FROM student_learning_session
                    WHERE tenant_id=? AND started_at >= ? AND started_at < ?
                    UNION ALL
                    SELECT user_id, GREATEST(COALESCE(actual_learning_seconds,0), COALESCE(learned_seconds,0), 0) sec
                    FROM training_learning_progress
                    WHERE COALESCE(last_learned_at, updated_at) >= ? AND COALESCE(last_learned_at, updated_at) < ?
                  ) raw GROUP BY user_id
                ) act ON act.user_id=u.id
                WHERE COALESCE(act.totalSec, 0) <= 0
                ORDER BY u.id ASC
                LIMIT 5
                """).formatted(teamScope),
                    tenantId, tenantId,
                    weekStart.atStartOfDay(), weekStart.plusDays(7).atStartOfDay(),
                    weekStart.atStartOfDay(), weekStart.plusDays(7).atStartOfDay());
            for (Map<String, Object> row : idle) {
                if (seen.contains(row.get("userId"))) continue;
                Map<String, Object> item = new LinkedHashMap<>();
                item.put("userId", row.get("userId"));
                item.put("studentName", row.get("studentName"));
                item.put("reason", "本周学习时长为 0");
                item.put("level", "watch");
                item.put("tag", "学习停滞");
                items.add(item);
                seen.add(row.get("userId"));
                if (items.size() >= 5) break;
            }
        } catch (Exception ignored) {
            // optional
        }

        // 3) 近 7 日无训练提交（不同于「今日未交」汇总）
        if (items.size() < 5) {
            try {
                List<Map<String, Object>> silent = jdbc.queryForList(("""
                    SELECT u.id userId, u.username studentName
                    FROM (
                      SELECT DISTINCT tm.user_id
                      FROM project_team_member tm
                      JOIN project_team pt ON pt.id=tm.team_id AND pt.tenant_id=? AND pt.id IN (%s)
                      JOIN users u2 ON u2.id=tm.user_id AND u2.role='STUDENT'
                    ) scope
                    JOIN users u ON u.id=scope.user_id
                    WHERE NOT EXISTS (
                      SELECT 1 FROM project_task_submission s
                      JOIN project_team pt ON pt.id=s.team_id AND pt.id IN (%s)
                      WHERE s.submitter_id=u.id
                        AND s.created_at >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
                    )
                    ORDER BY u.id ASC
                    LIMIT 5
                    """).formatted(teamScope, teamScope), tenantId);
                for (Map<String, Object> row : silent) {
                    if (seen.contains(row.get("userId"))) continue;
                    Map<String, Object> item = new LinkedHashMap<>();
                    item.put("userId", row.get("userId"));
                    item.put("studentName", row.get("studentName"));
                    item.put("reason", "近 7 日无训练提交");
                    item.put("level", "watch");
                    item.put("tag", "提交沉默");
                    items.add(item);
                    seen.add(row.get("userId"));
                    if (items.size() >= 5) break;
                }
            } catch (Exception ignored) {
                // optional
            }
        }

        return items.stream().limit(5).toList();
    }

    private List<Map<String, Object>> workbenchTrainingLog(Long tenantId, String teamScope) {
        List<Map<String, Object>> log = new ArrayList<>();
        LocalDate today = trainingDayAvailabilityService.today();
        String[] labels = {"今天", "昨天", "前天", "3天前", "4天前"};
        for (int i = 0; i < 5; i++) {
            LocalDate d = today.minusDays(i);
            int count = scalar(("""
                SELECT COUNT(DISTINCT s.submitter_id)
                FROM project_task_submission s
                JOIN project_team pt ON pt.id=s.team_id AND pt.tenant_id=? AND pt.id IN (%s)
                WHERE DATE(s.created_at)=?
                """).formatted(teamScope), tenantId, d);
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("date", d.toString());
            row.put("label", labels[i]);
            row.put("submitterCount", count);
            log.add(row);
        }
        return log;
    }

    private List<Map<String, Object>> workbenchLatestScores(Long tenantId, String teamScope) {
        List<Map<String, Object>> rows = jdbc.queryForList(("""
            SELECT r.id reportId, r.overall_score score,
                   COALESCE(r.completed_at, r.created_at) scoredAt,
                   COALESCE(s.team_id, b.team_id) teamId, pt.name teamName,
                   COALESCE(s.session_no, CONCAT('报告 #', r.id)) title,
                   m.title meetingTitle,
                   s.id sessionId,
                   s.docket_id docketId,
                   r.critical_issues_json criticalIssuesJson,
                   r.task_book_published taskBookPublished,
                   r.task_book_json taskBookJson,
                   d.task_book_published docketTaskBookPublished,
                   d.task_book_json docketTaskBookJson
            FROM ai_score_report r
            LEFT JOIN ai_scoring_session s ON s.id=r.session_id
            LEFT JOIN project_roadshow_binding b ON b.meeting_id=r.meeting_id
            LEFT JOIN meeting m ON m.id=r.meeting_id
            LEFT JOIN ai_score_docket d ON d.docket_id=s.docket_id
            JOIN project_team pt ON pt.id=COALESCE(s.team_id,b.team_id) AND pt.tenant_id=? AND pt.id IN (%s)
            WHERE r.status='completed' AND r.overall_score IS NOT NULL
            ORDER BY COALESCE(r.completed_at, r.created_at) DESC
            LIMIT 40
            """).formatted(teamScope), tenantId);
        for (Map<String, Object> row : rows) {
            attachHungProgress(row);
        }
        List<Map<String, Object>> out = WorkbenchLatestScores.assemble(rows, 5);
        for (Map<String, Object> item : out) {
            double score = item.get("score") == null ? 0 : Double.parseDouble(String.valueOf(item.get("score")));
            item.put("grade", scoreGrade(score));
            item.put("relativeTime", relativeDaysLabel(item.get("scoredAt")));
        }
        return out;
    }

    private void attachHungProgress(Map<String, Object> row) {
        if (!DocketTaskBook.flag(row.get("taskBookPublished"), row.get("docketTaskBookPublished"))) {
            return;
        }
        DocketTaskBook.Snapshot snapshot = DocketTaskBook.resolve(
                publishedFlag(row.get("taskBookPublished")),
                text(row.get("taskBookJson")),
                publishedFlag(row.get("docketTaskBookPublished")),
                text(row.get("docketTaskBookJson"))
        );
        if (!snapshot.published() || snapshot.json() == null || snapshot.json().isBlank()) {
            return;
        }
        try {
            com.orep.backend.dto.TaskBook book = objectMapper.readValue(snapshot.json(), com.orep.backend.dto.TaskBook.class);
            TaskBookHang.Progress progress = TaskBookHang.progress(book);
            if (progress.hung() > 0) {
                row.put("hungDisplay", progress.display());
            }
        } catch (Exception ignored) {
            // latest-score cards stay usable without hang counts
        }
    }

    private String scoreGrade(double score) {
        if (score >= 95) return "A+";
        if (score >= 90) return "A-";
        if (score >= 85) return "B+";
        if (score >= 80) return "B";
        if (score >= 75) return "B-";
        if (score >= 70) return "C+";
        if (score >= 60) return "C";
        return "D";
    }

    private String relativeDaysLabel(Object scoredAt) {
        if (scoredAt == null) return "";
        try {
            LocalDateTime dt;
            if (scoredAt instanceof LocalDateTime ldt) dt = ldt;
            else if (scoredAt instanceof java.sql.Timestamp ts) dt = ts.toLocalDateTime();
            else if (scoredAt instanceof LocalDate ld) dt = ld.atStartOfDay();
            else {
                String raw = String.valueOf(scoredAt).replace('T', ' ');
                if (raw.length() >= 19) dt = LocalDateTime.parse(raw.substring(0, 19).replace(' ', 'T'));
                else if (raw.length() >= 10) dt = LocalDate.parse(raw.substring(0, 10)).atStartOfDay();
                else return "";
            }
            long days = ChronoUnit.DAYS.between(dt.toLocalDate(), trainingDayAvailabilityService.today());
            if (days <= 0) return "今天";
            if (days == 1) return "1天前";
            return days + "天前";
        } catch (Exception ignored) {
            return "";
        }
    }

    private Map<String, Object> emptyAnalytics() {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("teamCount", 0);
        result.put("studentCount", 0);
        result.put("camp", Map.of());
        result.put("campName", null);
        result.put("campId", null);
        result.put("submissionRate", 0);
        result.put("expectedSubmissions", 0);
        result.put("submittedSubmissions", 0);
        result.put("missingSubmissions", 0);
        result.put("missingStudentCount", 0);
        result.put("campStudentCount", 0);
        result.put("publishedPastDays", 0);
        result.put("averageScore", 0);
        result.put("roadshowReportCount", 0);
        result.put("roadshowMeetingCount", 0);
        result.put("pendingReviews", 0);
        result.put("dimensionStats", List.of());
        result.put("dailySubmissions", List.of());
        result.put("missingStudents", List.of());
        result.put("atRiskStudents", List.of());
        result.put("recentScores", List.of());
        result.put("leaderboards", Map.of(
                "studyTime", List.of(),
                "submissions", List.of(),
                "resources", List.of()
        ));
        return result;
    }

    /**
     * 三类排行：范围内全部学生均上榜（无数据记 0，排在后面）。
     * - studyTime：累计学习秒数
     * - submissions：提交次数
     * - resources：完成的学习资源数
     */
    private Map<String, Object> buildLeaderboards(Long tenantId, String teamScope) {
        Map<String, Object> boards = new LinkedHashMap<>();
        // 学生去重：同一人挂多个团队时只计一次
        String scopedStudents = """
            SELECT DISTINCT tm.user_id
            FROM project_team_member tm
            JOIN project_team pt ON pt.id = tm.team_id AND pt.tenant_id = ? AND pt.id IN (%s)
            JOIN users u ON u.id = tm.user_id AND u.role = 'STUDENT'
            """.formatted(teamScope);

        boards.put("studyTime", jdbc.queryForList(("""
            SELECT u.id userId, u.username studentName,
                   COALESCE(SUM(act.durationSeconds), 0) totalSeconds,
                   COUNT(DISTINCT CASE WHEN act.durationSeconds > 0 THEN act.sourceKey END) activitySources
            FROM (%s) scope
            JOIN users u ON u.id = scope.user_id
            LEFT JOIN (
              SELECT user_id,
                     GREATEST(COALESCE(actual_learning_seconds, 0), COALESCE(learned_seconds, 0), 0) durationSeconds,
                     CONCAT('tr:', id) sourceKey
              FROM training_learning_progress
              WHERE GREATEST(COALESCE(actual_learning_seconds, 0), COALESCE(learned_seconds, 0), 0) > 0
              UNION ALL
              SELECT user_id, GREATEST(COALESCE(learned_seconds, 0), 0), CONCAT('co:', id)
              FROM course_learning_progress
              WHERE COALESCE(learned_seconds, 0) > 0
              UNION ALL
              SELECT user_id,
                     GREATEST(TIMESTAMPDIFF(SECOND, started_at, submitted_at), 0),
                     CONCAT('ex:', id)
              FROM exam_attempt
              WHERE started_at IS NOT NULL AND submitted_at IS NOT NULL
              UNION ALL
              SELECT user_id,
                     GREATEST(COALESCE(duration_seconds, TIMESTAMPDIFF(SECOND, joined_at, left_at), 0), 0),
                     CONCAT('mt:', id)
              FROM meeting_participant
              WHERE joined_at IS NOT NULL
                AND GREATEST(COALESCE(duration_seconds, TIMESTAMPDIFF(SECOND, joined_at, left_at), 0), 0) > 0
              UNION ALL
              SELECT user_id, GREATEST(COALESCE(duration_seconds, 0), 0), CONCAT('ss:', id)
              FROM student_learning_session
              WHERE COALESCE(duration_seconds, 0) > 0
            ) act ON act.user_id = u.id
            GROUP BY u.id, u.username
            ORDER BY totalSeconds DESC, u.id
            """).formatted(scopedStudents), tenantId));

        boards.put("submissions", jdbc.queryForList(("""
            SELECT u.id userId, u.username studentName,
                   COUNT(s.id) submissionCount,
                   COUNT(DISTINCT DATE(s.created_at)) activeDays,
                   MAX(s.created_at) lastSubmittedAt
            FROM (%s) scope
            JOIN users u ON u.id = scope.user_id
            LEFT JOIN project_task_submission s
              ON s.submitter_id = u.id AND s.team_id IN (%s)
            GROUP BY u.id, u.username
            ORDER BY submissionCount DESC, lastSubmittedAt DESC, u.id
            """).formatted(scopedStudents, teamScope), tenantId));

        boards.put("resources", jdbc.queryForList(("""
            SELECT u.id userId, u.username studentName,
                   COALESCE(SUM(done.cnt), 0) completedCount
            FROM (%s) scope
            JOIN users u ON u.id = scope.user_id
            LEFT JOIN (
              SELECT user_id, COUNT(*) cnt
              FROM training_learning_progress
              WHERE progress_percent >= 100 OR UPPER(status) IN ('COMPLETED', 'DONE')
              GROUP BY user_id
              UNION ALL
              SELECT user_id, COUNT(*) cnt
              FROM course_learning_progress
              WHERE progress_percent >= 100 OR LOWER(status) IN ('completed', 'done')
              GROUP BY user_id
            ) done ON done.user_id = u.id
            GROUP BY u.id, u.username
            ORDER BY completedCount DESC, u.id
            """).formatted(scopedStudents), tenantId));
        return boards;
    }

    /**
     * 提交率口径（0–100 整数，不是 0–1 小数）：
     * 分母 = 营内学生数 × 已发布/已关闭且训练日 ≤ 今天 的天数
     * 分子 = 学生-天 维度上至少有 1 次提交 的对数
     * 草稿日不计入，避免未发布计划把提交率压成假象或前端把 1 误当成 100%。
     */
    private Map<String, Object> submissionStats(Long campId, Long teamId) {
        Map<String, Object> stats = new LinkedHashMap<>();
        if (campId == null || teamId == null) {
            stats.put("submissionRate", 0);
            stats.put("expectedSubmissions", 0);
            stats.put("submittedSubmissions", 0);
            stats.put("missingSubmissions", 0);
            stats.put("missingStudentCount", 0);
            stats.put("campStudentCount", 0);
            stats.put("publishedPastDays", 0);
            return stats;
        }
        int members = scalar(
                "SELECT COUNT(*) FROM project_team_member tm JOIN users u ON u.id=tm.user_id AND u.role='STUDENT' WHERE tm.team_id=?",
                teamId);
        int days = scalar(
                "SELECT COUNT(*) FROM training_day WHERE camp_id=? AND training_date<=CURRENT_DATE AND status IN ('PUBLISHED','CLOSED')",
                campId);
        int expected = members * days;
        int submitted = days == 0 || members == 0 ? 0 : scalar("""
            SELECT COUNT(DISTINCT CONCAT(s.submitter_id,'-',dt.training_day_id))
            FROM project_task_submission s
            JOIN training_day_task dt ON dt.task_id=s.task_id
            JOIN training_day d ON d.id=dt.training_day_id
            WHERE d.camp_id=? AND d.training_date<=CURRENT_DATE AND d.status IN ('PUBLISHED','CLOSED')
            """, campId);
        int missing = Math.max(0, expected - submitted);
        int missingStudents = days == 0 || members == 0 ? 0 : scalar("""
            SELECT COUNT(*) FROM (
              SELECT u.id
              FROM project_team_member tm
              JOIN users u ON u.id=tm.user_id AND u.role='STUDENT'
              JOIN training_day d ON d.camp_id=? AND d.training_date<=CURRENT_DATE AND d.status IN ('PUBLISHED','CLOSED')
              LEFT JOIN training_day_task dt ON dt.training_day_id=d.id
              LEFT JOIN project_task_submission s ON s.task_id=dt.task_id AND s.submitter_id=u.id
              WHERE tm.team_id=?
              GROUP BY u.id
              HAVING SUM(CASE WHEN s.id IS NULL THEN 1 ELSE 0 END) > 0
            ) t
            """, campId, teamId);
        int rate = expected == 0 ? 0 : Math.min(100, Math.round(submitted * 100f / expected));
        stats.put("submissionRate", rate);
        stats.put("expectedSubmissions", expected);
        stats.put("submittedSubmissions", submitted);
        stats.put("missingSubmissions", missing);
        stats.put("missingStudentCount", missingStudents);
        stats.put("campStudentCount", members);
        stats.put("publishedPastDays", days);
        return stats;
    }

    private List<Map<String, Object>> missingStudents(Long campId, Long teamId) {
        if (campId == null || teamId == null) return List.of();
        return jdbc.queryForList("""
            SELECT u.id userId, u.username studentName,
                   SUM(CASE WHEN s.id IS NULL THEN 1 ELSE 0 END) missingDays,
                   SUM(CASE WHEN s.id IS NOT NULL THEN 1 ELSE 0 END) submittedDays,
                   COUNT(DISTINCT d.id) dueDays
            FROM project_team_member tm
            JOIN users u ON u.id=tm.user_id AND u.role='STUDENT'
            JOIN training_day d ON d.camp_id=? AND d.training_date<=CURRENT_DATE AND d.status IN ('PUBLISHED','CLOSED')
            LEFT JOIN training_day_task dt ON dt.training_day_id=d.id
            LEFT JOIN project_task_submission s ON s.task_id=dt.task_id AND s.submitter_id=u.id
            WHERE tm.team_id=?
            GROUP BY u.id, u.username
            HAVING missingDays > 0
            ORDER BY missingDays DESC, u.id
            LIMIT 30
            """, campId, teamId);
    }

    private void recordEvent(Long tenantId, Long userId, String eventType, String targetType, Long targetId, Object payload) {
        try {
            jdbc.update("INSERT INTO teacher_portal_event(tenant_id,actor_user_id,event_type,target_type,target_id,payload_json) VALUES (?,?,?,?,?,?)",
                    tenantId,userId,eventType,targetType,targetId,objectMapper.writeValueAsString(payload));
        } catch (Exception ignored) { }
    }

    private Map<String, Object> one(String sql, Object... args) {
        List<Map<String, Object>> rows = jdbc.queryForList(sql,args);
        if (rows.isEmpty()) return new LinkedHashMap<>();
        Map<String, Object> result = new LinkedCaseInsensitiveMap<>();
        result.putAll(rows.get(0));
        return result;
    }

    private int scalar(String sql, Object... args) {
        Integer value = jdbc.queryForObject(sql,Integer.class,args);
        return value == null ? 0 : value;
    }

    private Object decimalScalar(String sql, Object... args) {
        return jdbc.queryForObject(sql,Object.class,args);
    }

    private Map<String, Object> parseMap(Object value) {
        if (value == null) return Map.of();
        try { return objectMapper.readValue(String.valueOf(value),new TypeReference<>(){}); }
        catch (Exception ignored) { return Map.of(); }
    }

    private List<Map<String, Object>> parseList(Object value) {
        if (value == null || String.valueOf(value).isBlank()) return List.of();
        if (value instanceof Collection<?> collection) {
            List<Map<String, Object>> rows = new ArrayList<>();
            for (Object item : collection) {
                if (item instanceof Map<?, ?> map) {
                    Map<String, Object> row = new LinkedHashMap<>();
                    map.forEach((key, field) -> row.put(String.valueOf(key), field));
                    rows.add(row);
                }
            }
            return rows;
        }
        try { return objectMapper.readValue(String.valueOf(value),new TypeReference<>(){}); }
        catch (Exception ignored) { return List.of(); }
    }

    private List<Map<String, Object>> normalizeRequirements(Object value) {
        List<Map<String, Object>> normalized = new ArrayList<>();
        for (Map<String, Object> item : parseList(value)) {
            String title = text(item.get("title"));
            if (title == null) continue;
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("title", title);
            row.put("description", text(item.get("description")));
            Object required = item.get("required");
            row.put("required", required instanceof Boolean bool ? bool : !"false".equalsIgnoreCase(String.valueOf(required)));
            String assetType = text(item.get("assetType"));
            row.put("assetType", assetType == null ? "FILE" : assetType.toUpperCase(Locale.ROOT));
            normalized.add(row);
        }
        return normalized;
    }

    private List<Long> longValues(Object value) {
        LinkedHashSet<Long> ids = new LinkedHashSet<>();
        if (value instanceof Collection<?> collection) {
            for (Object item : collection) {
                Long id = longValue(item);
                if (id != null) ids.add(id);
            }
        } else if (value != null) {
            for (String item : String.valueOf(value).split(",")) {
                Long id = longValue(item.trim());
                if (id != null) ids.add(id);
            }
        }
        return new ArrayList<>(ids);
    }

    private String json(Object value) {
        try { return objectMapper.writeValueAsString(value); }
        catch (Exception e) { throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "交付要求格式不正确"); }
    }

    private Long insert(String sql, Object... args) {
        KeyHolder keyHolder = new GeneratedKeyHolder();
        jdbc.update(connection -> {
            PreparedStatement statement = connection.prepareStatement(sql, Statement.RETURN_GENERATED_KEYS);
            for (int index = 0; index < args.length; index++) statement.setObject(index + 1, args[index]);
            return statement;
        }, keyHolder);
        Number key = keyHolder.getKey();
        if (key == null) throw new IllegalStateException("插入数据失败，未返回主键");
        return key.longValue();
    }

    private Long longValue(Object value) {
        if (value instanceof Number n) return n.longValue();
        try { return value == null ? null : Long.valueOf(String.valueOf(value)); }
        catch (Exception ignored) { return null; }
    }

    private int intValue(Object value) {
        if (value instanceof Number n) return n.intValue();
        try { return value == null ? 0 : Integer.parseInt(String.valueOf(value)); }
        catch (Exception ignored) { return 0; }
    }

    private String text(Object value) {
        if (value == null) return null;
        String text = String.valueOf(value).trim();
        return text.isEmpty() ? null : text;
    }

    private static Boolean publishedFlag(Object value) {
        if (value instanceof Boolean flag) {
            return flag;
        }
        if (value instanceof Number number) {
            return number.intValue() != 0;
        }
        if (value == null) {
            return false;
        }
        return "1".equals(String.valueOf(value)) || "true".equalsIgnoreCase(String.valueOf(value));
    }

    private LocalDate localDate(Object value) {
        if (value instanceof java.sql.Date date) return date.toLocalDate();
        if (value instanceof LocalDate date) return date;
        try { return value == null ? null : LocalDate.parse(String.valueOf(value)); }
        catch (Exception ignored) { return null; }
    }

    private LocalDateTime dateTime(Object value) {
        if (value instanceof LocalDateTime date) return date;
        if (value == null || String.valueOf(value).isBlank()) return null;
        String text = String.valueOf(value).trim().replace('T',' ');
        try { return LocalDateTime.parse(text.replace(' ','T')); }
        catch (Exception ignored) { return null; }
    }
}
