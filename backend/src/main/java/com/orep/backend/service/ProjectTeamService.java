package com.orep.backend.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.annotation.PostConstruct;
import org.springframework.core.io.ClassPathResource;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.server.ResponseStatusException;

import java.io.InputStream;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.sql.PreparedStatement;
import java.sql.Statement;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.*;
import java.util.stream.Collectors;

@Service
public class ProjectTeamService {
    private final JdbcTemplate jdbc;
    private final RoadshowMemoryAnalyzer roadshowMemoryAnalyzer;
    private final AiResultEvidenceAnchorExtractor evidenceAnchorExtractor;
    private final RecordingEvidenceAnchorBuilder recordingEvidenceAnchorBuilder;
    private final ScoreEvidenceAnchorStore scoreEvidenceAnchorStore;
    private final CompetitionReadinessService competitionReadinessService;
    private final TrainingDayAvailabilityService trainingDayAvailabilityService;
    private final ObjectMapper objectMapper = new ObjectMapper();
    private final Path uploadRoot;
    private static final long MAX_TEAM_MATERIAL_BYTES = 200L * 1024 * 1024;
    private static final Set<String> TEAM_MATERIAL_EXTENSIONS = Set.of(
            "pdf", "doc", "docx", "ppt", "pptx", "xls", "xlsx", "csv", "txt", "md",
            "png", "jpg", "jpeg", "gif", "webp",
            "mp4", "webm", "mov", "mp3", "wav", "m4a",
            "zip", "rar", "7z"
    );
    private static final List<String> CAPTAIN_PERMISSION_KEYS = List.of(
            "ASSIGN_TASK",
            "REVIEW_SUBMISSION",
            "REVIEW_MATERIAL",
            "BIND_ROADSHOW"
    );

    private static final List<String> ABILITY_DIMENSIONS = List.of(
            "problemSolving", "coding", "communication", "teamwork", "presentation", "creativity"
    );

    /** 课程/测评为建议准备项，不计入主链路门禁与整体进度 */
    private static final Set<String> OPTIONAL_STAGE_KEYS = Set.of("COURSE", "EXAM");

    public ProjectTeamService(
            JdbcTemplate jdbc,
            RoadshowMemoryAnalyzer roadshowMemoryAnalyzer,
            AiResultEvidenceAnchorExtractor evidenceAnchorExtractor,
            RecordingEvidenceAnchorBuilder recordingEvidenceAnchorBuilder,
            ScoreEvidenceAnchorStore scoreEvidenceAnchorStore,
            CompetitionReadinessService competitionReadinessService,
            TrainingDayAvailabilityService trainingDayAvailabilityService,
            @Value("${file.upload-dir:./uploads}") String uploadDir
    ) {
        this.jdbc = jdbc;
        this.roadshowMemoryAnalyzer = roadshowMemoryAnalyzer;
        this.evidenceAnchorExtractor = evidenceAnchorExtractor;
        this.recordingEvidenceAnchorBuilder = recordingEvidenceAnchorBuilder;
        this.scoreEvidenceAnchorStore = scoreEvidenceAnchorStore;
        this.competitionReadinessService = competitionReadinessService;
        this.trainingDayAvailabilityService = trainingDayAvailabilityService;
        this.uploadRoot = Paths.get(uploadDir).toAbsolutePath().normalize();
    }

    @PostConstruct
    public void ensureSchema() {
        try (InputStream in = new ClassPathResource("sql/create_project_team_tables.sql").getInputStream()) {
            String sql = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            for (String statement : sql.split(";")) {
                String trimmed = statement.trim();
                if (!trimmed.isBlank()) jdbc.execute(trimmed);
            }
            ensureAiScoreSchema();
            ensureAiScoringSessionSchema();
            ensureRoadshowMemorySchema();
            ensureSchemaUpgrades();
            seedDefaultPositionRoles();
            seedRoleAliases();
            importLegacyAiScoreReports();
        } catch (Exception e) {
            throw new IllegalStateException("项目团队表初始化失败", e);
        }
    }

    private void ensureAiScoreSchema() {
        try (InputStream in = new ClassPathResource("sql/create_ai_score_report_table.sql").getInputStream()) {
            String sql = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            for (String statement : sql.split(";")) {
                String trimmed = statement.trim();
                if (!trimmed.isBlank()) jdbc.execute(trimmed);
            }
        } catch (Exception e) {
            throw new IllegalStateException("AI评分报告表初始化失败", e);
        }
    }

    private void ensureAiScoringSessionSchema() {
        try (InputStream in = new ClassPathResource("sql/create_ai_scoring_session_tables.sql").getInputStream()) {
            String sql = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            for (String statement : sql.split(";")) {
                String trimmed = statement.trim();
                if (!trimmed.isBlank()) jdbc.execute(trimmed);
            }
        } catch (Exception e) {
            throw new IllegalStateException("AI评分会话表初始化失败", e);
        }
    }

    private void ensureRoadshowMemorySchema() {
        try (InputStream in = new ClassPathResource("sql/create_roadshow_memory_tables.sql").getInputStream()) {
            String sql = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            for (String statement : sql.split(";")) {
                String trimmed = statement.trim();
                if (!trimmed.isBlank()) jdbc.execute(trimmed);
            }
        } catch (Exception e) {
            throw new IllegalStateException("路演评分记忆表初始化失败", e);
        }
    }

    private void ensureSchemaUpgrades() {
        try {
            jdbc.execute("ALTER TABLE project_team ADD COLUMN track_id VARCHAR(128) DEFAULT NULL COMMENT '赛道ID，对应评分规则' AFTER description");
        } catch (Exception ignored) {
        }
        try {
            jdbc.execute("ALTER TABLE project_team ADD COLUMN track_name VARCHAR(255) DEFAULT NULL COMMENT '赛道完整名称' AFTER track_id");
        } catch (Exception ignored) {
        }
        try {
            jdbc.execute("ALTER TABLE project_team ADD INDEX idx_project_team_track (track_id)");
        } catch (Exception ignored) {
        }
        try {
            jdbc.execute("ALTER TABLE ai_score_report ADD COLUMN score_calibration_json TEXT COMMENT '技术与现场演示校准 JSON' AFTER speech_quality_json");
        } catch (Exception ignored) {
        }
        try {
            jdbc.execute("ALTER TABLE project_team_member ADD COLUMN captain_permissions VARCHAR(500) DEFAULT NULL COMMENT '队长权限JSON'");
        } catch (Exception ignored) {
        }
        try {
            jdbc.execute("ALTER TABLE project_task_submission ADD COLUMN attachment_name VARCHAR(255) DEFAULT NULL COMMENT '附件原始文件名'");
        } catch (Exception ignored) {
        }
        try {
            jdbc.execute("ALTER TABLE project_task_submission ADD COLUMN attachment_size BIGINT DEFAULT NULL COMMENT '附件大小'");
        } catch (Exception ignored) {
        }
        try {
            jdbc.execute("ALTER TABLE project_task_submission ADD COLUMN attachment_type VARCHAR(120) DEFAULT NULL COMMENT '附件MIME类型'");
        } catch (Exception ignored) {
        }
        try {
            jdbc.execute("ALTER TABLE project_task_submission ADD COLUMN submission_type VARCHAR(60) NOT NULL DEFAULT 'OTHER' COMMENT '成果类型'");
        } catch (Exception ignored) {
        }
        try {
            jdbc.execute("ALTER TABLE project_task_submission ADD COLUMN sync_to_material TINYINT NOT NULL DEFAULT 1 COMMENT '是否同步到项目材料'");
        } catch (Exception ignored) {
        }
        try {
            jdbc.execute("""
                CREATE TABLE IF NOT EXISTS project_submission_asset (
                  id BIGINT PRIMARY KEY AUTO_INCREMENT,
                  submission_id BIGINT NOT NULL COMMENT '提交ID',
                  task_id BIGINT NOT NULL COMMENT '任务ID',
                  team_id BIGINT NOT NULL COMMENT '团队ID',
                  asset_kind VARCHAR(40) NOT NULL DEFAULT 'MAIN' COMMENT '资产用途',
                  file_url VARCHAR(500) NOT NULL COMMENT '文件地址',
                  file_name VARCHAR(255) DEFAULT NULL COMMENT '文件名',
                  file_size BIGINT DEFAULT NULL COMMENT '文件大小',
                  file_type VARCHAR(120) DEFAULT NULL COMMENT '文件MIME类型',
                  sort_order INT NOT NULL DEFAULT 0 COMMENT '排序',
                  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                  KEY idx_submission_asset_submission (submission_id),
                  KEY idx_submission_asset_task (task_id),
                  KEY idx_submission_asset_team (team_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='任务提交文件资产'
                """);
        } catch (Exception ignored) {
        }
        try {
            jdbc.execute("""
                CREATE TABLE IF NOT EXISTS project_submission_link (
                  id BIGINT PRIMARY KEY AUTO_INCREMENT,
                  submission_id BIGINT NOT NULL COMMENT '提交ID',
                  task_id BIGINT NOT NULL COMMENT '任务ID',
                  team_id BIGINT NOT NULL COMMENT '团队ID',
                  link_type VARCHAR(40) NOT NULL DEFAULT 'OTHER' COMMENT '链接类型',
                  title VARCHAR(160) DEFAULT NULL COMMENT '链接标题',
                  url VARCHAR(800) NOT NULL COMMENT '链接地址',
                  sort_order INT NOT NULL DEFAULT 0 COMMENT '排序',
                  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                  KEY idx_submission_link_submission (submission_id),
                  KEY idx_submission_link_task (task_id),
                  KEY idx_submission_link_team (team_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='任务提交外部链接'
                """);
        } catch (Exception ignored) {
        }
        try {
            jdbc.execute("ALTER TABLE project_task ADD COLUMN task_type VARCHAR(60) DEFAULT 'OTHER_BUSINESS' COMMENT '任务类型'");
        } catch (Exception ignored) {
        }
        try {
            jdbc.execute("ALTER TABLE project_task ADD COLUMN task_type_label VARCHAR(80) DEFAULT NULL COMMENT '任务类型名称'");
        } catch (Exception ignored) {
        }
        try {
            jdbc.execute("ALTER TABLE project_task ADD COLUMN time_slot VARCHAR(30) DEFAULT NULL COMMENT '计划时间段：MORNING/AFTERNOON/EVENING'");
        } catch (Exception ignored) {
        }
        try {
            jdbc.execute("ALTER TABLE project_task ADD COLUMN source_type VARCHAR(40) NOT NULL DEFAULT 'OTHER' COMMENT '任务来源类型'");
        } catch (Exception ignored) {
        }
        try {
            jdbc.execute("ALTER TABLE project_task ADD COLUMN reviewer_user_id BIGINT DEFAULT NULL COMMENT '指定成果审核人'");
        } catch (Exception ignored) {
        }
        try {
            jdbc.execute("ALTER TABLE project_material ADD COLUMN source_submission_id BIGINT DEFAULT NULL COMMENT '来源提交ID'");
        } catch (Exception ignored) {
        }
        try {
            jdbc.execute("ALTER TABLE project_material ADD COLUMN source_item_key VARCHAR(190) DEFAULT NULL COMMENT '来源成果稳定键'");
        } catch (Exception ignored) {
        }
        try {
            jdbc.execute("ALTER TABLE users ADD COLUMN school_name VARCHAR(120) DEFAULT NULL COMMENT '学校'");
        } catch (Exception ignored) {
        }
        try {
            jdbc.execute("ALTER TABLE users ADD COLUMN college_name VARCHAR(120) DEFAULT NULL COMMENT '学院'");
        } catch (Exception ignored) {
        }
        try {
            jdbc.execute("ALTER TABLE users ADD COLUMN class_name VARCHAR(120) DEFAULT NULL COMMENT '班级'");
        } catch (Exception ignored) {
        }
        try {
            jdbc.execute("ALTER TABLE users ADD COLUMN user_group VARCHAR(120) DEFAULT NULL COMMENT '用户组'");
        } catch (Exception ignored) {
        }
        try {
            jdbc.execute("ALTER TABLE project_stage ADD COLUMN is_optional TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否可选阶段'");
        } catch (Exception ignored) {
        }
        try {
            jdbc.execute("ALTER TABLE project_stage ADD COLUMN suggestion_text VARCHAR(500) DEFAULT NULL COMMENT '阶段说明提示'");
        } catch (Exception ignored) {
        }
        try {
            jdbc.update("UPDATE project_stage SET is_optional = 1 WHERE stage_key IN ('COURSE', 'EXAM')");
        } catch (Exception ignored) {
        }
        try {
            jdbc.execute("ALTER TABLE project_team ADD COLUMN ability_synced_at DATETIME DEFAULT NULL COMMENT '能力画像最近重算时间，NULL 表示待重算（事件触发后置脏）'");
        } catch (Exception ignored) {
        }
        try {
            jdbc.execute("""
                CREATE TABLE IF NOT EXISTS roadshow_speaker_score (
                  id BIGINT PRIMARY KEY AUTO_INCREMENT,
                  meeting_id BIGINT NOT NULL COMMENT '路演会议ID',
                  team_id BIGINT NOT NULL COMMENT '所属团队ID',
                  speaker_label VARCHAR(64) NOT NULL COMMENT 'AI 说话人标签，如 S1/发言人A',
                  claimed_role VARCHAR(255) DEFAULT NULL COMMENT '发言人自报岗位原文',
                  normalized_role VARCHAR(120) DEFAULT NULL COMMENT '归一后的岗位名（对齐花名册）',
                  matched_name VARCHAR(120) DEFAULT NULL COMMENT 'AI 识别到的自报姓名',
                  matched_user_id BIGINT DEFAULT NULL COMMENT '对齐到的成员用户ID',
                  matched_role_name VARCHAR(120) DEFAULT NULL COMMENT '对齐到的成员岗位名',
                  match_method VARCHAR(24) NOT NULL DEFAULT 'NONE' COMMENT 'NAME/ROLE_ALIGN/ATTENDANCE/TEACHER/NONE',
                  match_confidence DECIMAL(5,2) DEFAULT NULL COMMENT '对齐置信度0-1',
                  duration_sec INT DEFAULT 0 COMMENT '该发言人发言总时长（秒）',
                  dimensions_json LONGTEXT COMMENT '分维度评分JSON',
                  evidence_quotes_json LONGTEXT COMMENT '证据原话引用JSON',
                  segments_json LONGTEXT COMMENT '发言时间区间JSON',
                  status VARCHAR(16) NOT NULL DEFAULT 'AUTO' COMMENT 'AUTO/CONFIRMED/REJECTED',
                  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                  UNIQUE KEY uk_meeting_team_speaker (meeting_id, team_id, speaker_label),
                  KEY idx_meeting (meeting_id),
                  KEY idx_team_user (team_id, matched_user_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='路演分发言人/分岗位 AI 评分对齐表'
                """);
        } catch (Exception ignored) {
        }
        try {
            jdbc.execute("""
                CREATE TABLE IF NOT EXISTS project_role_alias (
                  id BIGINT PRIMARY KEY AUTO_INCREMENT,
                  tenant_id BIGINT NOT NULL,
                  alias VARCHAR(120) NOT NULL COMMENT '别名/同义词（自报岗位口语）',
                  canonical_role VARCHAR(120) NOT NULL COMMENT '归一后的标准岗位名',
                  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                  UNIQUE KEY uk_tenant_alias (tenant_id, alias),
                  KEY idx_tenant (tenant_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='岗位别名归一表，用于把发言人自报岗位对齐到成员分工'
                """);
        } catch (Exception ignored) {
        }
        jdbc.update("""
            UPDATE project_team_member
            SET captain_permissions = ?
            WHERE role_in_team = 'CAPTAIN'
              AND (captain_permissions IS NULL OR captain_permissions = '')
            """, permissionsJson(CAPTAIN_PERMISSION_KEYS));
    }

    private void seedDefaultPositionRoles() {
        List<Map<String, Object>> tenants = jdbc.queryForList("SELECT DISTINCT tenant_id tenantId FROM users WHERE tenant_id IS NOT NULL");
        if (tenants.isEmpty()) tenants = List.of(Map.of("tenantId", 1L));
        for (Map<String, Object> tenant : tenants) {
            Long tenantId = longValue(tenant.get("tenantId"));
            if (tenantId == null) continue;
            seedPositionRole(tenantId, "项目经理", "统筹项目计划、进度、风险和团队协作", 10);
            seedPositionRole(tenantId, "产品经理", "梳理需求、用户价值、产品方案和演示逻辑", 20);
            seedPositionRole(tenantId, "前端开发工程师", "负责前端页面、交互体验和演示界面实现", 30);
            seedPositionRole(tenantId, "后端开发工程师", "负责接口、数据库、服务稳定性和数据闭环", 40);
            seedPositionRole(tenantId, "算法工程师", "负责AI能力、模型调用、数据分析和效果验证", 50);
            seedPositionRole(tenantId, "测试工程师", "负责测试用例、缺陷跟踪、验收和质量保障", 60);
            seedPositionRole(tenantId, "UI/UX设计师", "负责视觉规范、交互流程和路演展示体验", 70);
            seedPositionRole(tenantId, "路演主讲", "负责路演表达、答辩组织和现场节奏控制", 80);
            seedPositionRole(tenantId, "资料负责人", "负责周报、PPT、逐字稿和佐证材料归档", 90);
            seedPositionRole(tenantId, "运维部署工程师", "负责部署环境、演示设备和运行保障", 100);
        }
    }

    private void seedRoleAliases() {
        List<Map<String, Object>> tenants = jdbc.queryForList("SELECT DISTINCT tenant_id tenantId FROM users WHERE tenant_id IS NOT NULL");
        if (tenants.isEmpty()) tenants = List.of(Map.of("tenantId", 1L));
        for (Map<String, Object> tenant : tenants) {
            Long tenantId = longValue(tenant.get("tenantId"));
            if (tenantId == null) continue;
            seedAlias(tenantId, "项目经理", "项目经理");
            seedAlias(tenantId, "队长", "项目经理");
            seedAlias(tenantId, "组长", "项目经理");
            seedAlias(tenantId, "负责人", "项目经理");
            seedAlias(tenantId, "leader", "项目经理");
            seedAlias(tenantId, "PM", "项目经理");
            seedAlias(tenantId, "产品经理", "产品经理");
            seedAlias(tenantId, "产品", "产品经理");
            seedAlias(tenantId, "产品负责人", "产品经理");
            seedAlias(tenantId, "前端开发工程师", "前端开发工程师");
            seedAlias(tenantId, "前端", "前端开发工程师");
            seedAlias(tenantId, "前端开发", "前端开发工程师");
            seedAlias(tenantId, "前端工程师", "前端开发工程师");
            seedAlias(tenantId, "FE", "前端开发工程师");
            seedAlias(tenantId, "后端开发工程师", "后端开发工程师");
            seedAlias(tenantId, "后端", "后端开发工程师");
            seedAlias(tenantId, "后端开发", "后端开发工程师");
            seedAlias(tenantId, "服务端", "后端开发工程师");
            seedAlias(tenantId, "后端工程师", "后端开发工程师");
            seedAlias(tenantId, "BE", "后端开发工程师");
            seedAlias(tenantId, "算法工程师", "算法工程师");
            seedAlias(tenantId, "算法", "算法工程师");
            seedAlias(tenantId, "模型", "算法工程师");
            seedAlias(tenantId, "测试工程师", "测试工程师");
            seedAlias(tenantId, "测试", "测试工程师");
            seedAlias(tenantId, "QA", "测试工程师");
            seedAlias(tenantId, "质量", "测试工程师");
            seedAlias(tenantId, "UI/UX设计师", "UI/UX设计师");
            seedAlias(tenantId, "UI", "UI/UX设计师");
            seedAlias(tenantId, "UX", "UI/UX设计师");
            seedAlias(tenantId, "设计", "UI/UX设计师");
            seedAlias(tenantId, "设计师", "UI/UX设计师");
            seedAlias(tenantId, "视觉", "UI/UX设计师");
            seedAlias(tenantId, "路演主讲", "路演主讲");
            seedAlias(tenantId, "主讲", "路演主讲");
            seedAlias(tenantId, "演讲", "路演主讲");
            seedAlias(tenantId, "讲解", "路演主讲");
            seedAlias(tenantId, "资料负责人", "资料负责人");
            seedAlias(tenantId, "资料", "资料负责人");
            seedAlias(tenantId, "文档", "资料负责人");
            seedAlias(tenantId, "文案", "资料负责人");
            seedAlias(tenantId, "运维部署工程师", "运维部署工程师");
            seedAlias(tenantId, "运维", "运维部署工程师");
            seedAlias(tenantId, "部署", "运维部署工程师");
            seedAlias(tenantId, "devops", "运维部署工程师");
        }
    }

    private void seedAlias(Long tenantId, String alias, String canonical) {
        jdbc.update("INSERT IGNORE INTO project_role_alias (tenant_id, alias, canonical_role) VALUES (?, ?, ?)",
                tenantId, alias, canonical);
    }

    private void seedPositionRole(Long tenantId, String name, String description, int sortOrder) {
        jdbc.update("""
            INSERT IGNORE INTO project_position_role
            (tenant_id, name, description, sort_order, status)
            VALUES (?, ?, ?, ?, 'ACTIVE')
            """, tenantId, name, description, sortOrder);
    }

    private void importLegacyAiScoreReports() {
        Path resultDir = legacyAiResultDir();
        if (!Files.isDirectory(resultDir)) return;
        try (var files = Files.list(resultDir)) {
            files
                    .filter(path -> path.getFileName().toString().startsWith("result_"))
                    .filter(path -> path.getFileName().toString().endsWith(".json"))
                    .forEach(this::importLegacyAiScoreReport);
        } catch (Exception ignored) {
        }
    }

    private Path legacyAiResultDir() {
        Path runtimeDir = Paths.get(System.getProperty("user.dir")).toAbsolutePath().normalize();
        Path projectRoot = "backend".equals(runtimeDir.getFileName().toString()) ? runtimeDir.getParent() : runtimeDir;
        Path projectRelative = projectRoot.resolve("ai-scoring").resolve("uploads").resolve("results");
        if (Files.isDirectory(projectRelative)) return projectRelative;
        return Paths.get(System.getProperty("user.home"), "项目", "OREP", "ai-scoring", "uploads", "results");
    }

    private void importLegacyAiScoreReport(Path path) {
        try {
            Map<String, Object> result = objectMapper.readValue(Files.readString(path), new TypeReference<Map<String, Object>>() {});
            Long meetingId = longValue(result.get("meeting_id"));
            if (meetingId == null) meetingId = longValue(result.get("meetingId"));
            if (meetingId == null || !meetingExists(meetingId) || aiReportExists(meetingId)) return;

            Map<String, Object> aiScore = parseNestedMap(result.get("ai_score"));
            Map<String, Object> asr = parseNestedMap(result.get("asr"));
            String status = text(result.get("status"), "completed");
            Object overallScore = aiScore.getOrDefault("overall_score", aiScore.get("overallScore"));
            jdbc.update("""
                INSERT INTO ai_score_report
                (meeting_id, overall_score, dimensions_json, highlights_json, critical_issues_json,
                 improvement_priorities_json, transcript, speech_quality_json, model, result_path,
                 status, error_message, started_at, completed_at, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NOW(), NOW())
                """,
                    meetingId,
                    decimalValue(overallScore),
                    jsonString(aiScore.get("dimensions")),
                    jsonString(aiScore.get("highlights")),
                    jsonString(aiScore.get("critical_issues")),
                    jsonString(aiScore.get("improvement_priorities")),
                    text(asr.get("transcript"), null),
                    jsonString(result.get("speech_quality")),
                    text(aiScore.get("model"), "legacy-import"),
                    relativizeAiResultPath(path),
                    status,
                    text(result.get("error"), null),
                    dateTimeValue(result.get("started_at")),
                    dateTimeValue(result.get("completed_at"))
            );
        } catch (Exception ignored) {
        }
    }

    public List<Map<String, Object>> myTeams(Long tenantId, Long userId, String role) {
        // 列表字段需覆盖教师端「项目管理」：指导老师、成员数等
        final String teamSelect = """
                SELECT t.id,
                       t.name,
                       t.name projectName,
                       t.description,
                       t.track_id trackId,
                       t.track_name trackName,
                       t.start_date startDate,
                       t.end_date endDate,
                       t.current_stage currentStage,
                       t.status,
                       t.mentor_id mentorId,
                       (
                         SELECT GROUP_CONCAT(DISTINCT names.username ORDER BY names.username SEPARATOR '、')
                         FROM (
                           SELECT u.username AS username
                           FROM users u
                           WHERE u.id = t.mentor_id
                             AND u.username IS NOT NULL
                             AND u.username <> ''
                           UNION
                           SELECT u.username AS username
                           FROM project_team_member mm
                           JOIN users u ON u.id = mm.user_id
                           WHERE mm.team_id = t.id
                             AND mm.role_in_team = 'MENTOR'
                             AND u.username IS NOT NULL
                             AND u.username <> ''
                         ) names
                       ) mentorNames,
                       (
                         SELECT GROUP_CONCAT(DISTINCT names.username ORDER BY names.username SEPARATOR '、')
                         FROM (
                           SELECT u.username AS username
                           FROM users u
                           WHERE u.id = t.mentor_id
                             AND u.username IS NOT NULL
                             AND u.username <> ''
                           UNION
                           SELECT u.username AS username
                           FROM project_team_member mm
                           JOIN users u ON u.id = mm.user_id
                           WHERE mm.team_id = t.id
                             AND mm.role_in_team = 'MENTOR'
                             AND u.username IS NOT NULL
                             AND u.username <> ''
                         ) names
                       ) mentorName,
                       (
                         SELECT u.username
                         FROM project_team_member cap
                         JOIN users u ON u.id = cap.user_id
                         WHERE cap.team_id = t.id AND cap.role_in_team = 'CAPTAIN'
                         ORDER BY cap.id ASC
                         LIMIT 1
                       ) captainName,
                       (
                         SELECT COUNT(*)
                         FROM project_team_member mc
                         WHERE mc.team_id = t.id
                           AND mc.role_in_team IN ('CAPTAIN', 'MEMBER')
                       ) memberCount,
                       (
                         SELECT COUNT(*)
                         FROM project_team_member mc
                         WHERE mc.team_id = t.id
                       ) totalMemberCount
                """;

        if (isAdministrator(role)) {
            return jdbc.queryForList(teamSelect + """
                ,
                       COALESCE(m.role_in_team, 'TEACHER') myRoleInTeam
                FROM project_team t
                LEFT JOIN project_team_member m ON m.team_id = t.id AND m.user_id = ?
                WHERE t.tenant_id = ?
                ORDER BY t.updated_at DESC
                """, userId, tenantId);
        }
        if (isTeacher(role)) {
            return jdbc.queryForList(teamSelect + """
                ,
                       COALESCE(m.role_in_team, 'MENTOR') myRoleInTeam
                FROM project_team t
                LEFT JOIN project_team_member m ON m.team_id = t.id AND m.user_id = ?
                WHERE t.tenant_id = ?
                  AND (t.mentor_id = ? OR EXISTS (
                    SELECT 1 FROM project_team_member mentor
                    WHERE mentor.team_id = t.id
                      AND mentor.user_id = ?
                      AND mentor.role_in_team = 'MENTOR'
                  ))
                ORDER BY t.updated_at DESC
                """, userId, tenantId, userId, userId);
        }
        return jdbc.queryForList(teamSelect + """
            ,
                   m.role_in_team myRoleInTeam
            FROM project_team t
            JOIN project_team_member m ON m.team_id = t.id
            WHERE t.tenant_id = ? AND m.user_id = ?
            ORDER BY t.updated_at DESC
            """, tenantId, userId);
    }

    public List<Map<String, Object>> teacherReviewQueue(Long tenantId, Long userId, String role) {
        assertTeacherReviewRole(role);
        boolean teacher = "TEACHER".equalsIgnoreCase(String.valueOf(role));
        List<Map<String, Object>> rows = teacher
                ? jdbc.queryForList(teacherSubmissionSql("""
                    WHERE pt.tenant_id = ?
                      AND (pt.mentor_id = ? OR EXISTS (
                        SELECT 1
                        FROM project_team_member mentor
                        WHERE mentor.team_id = pt.id
                          AND mentor.user_id = ?
                          AND mentor.role_in_team = 'MENTOR'
                      ))
                      AND s.id = (
                        SELECT latest.id
                        FROM project_task_submission latest
                        WHERE latest.task_id = s.task_id
                          AND latest.submitter_id = s.submitter_id
                        ORDER BY latest.version_no DESC, latest.id DESC LIMIT 1
                      )
                      AND s.status IN ('PENDING_REVIEW', 'REVIEWING')
                    ORDER BY s.created_at ASC, s.id ASC
                    """), tenantId, userId, userId)
                : jdbc.queryForList(teacherSubmissionSql("""
                    WHERE pt.tenant_id = ?
                      AND s.id = (
                        SELECT latest.id
                        FROM project_task_submission latest
                        WHERE latest.task_id = s.task_id
                          AND latest.submitter_id = s.submitter_id
                        ORDER BY latest.version_no DESC, latest.id DESC LIMIT 1
                      )
                      AND s.status IN ('PENDING_REVIEW', 'REVIEWING')
                    ORDER BY s.created_at ASC, s.id ASC
                    """), tenantId);
        attachSubmissionPayloads(rows);
        return rows;
    }

    public Map<String, Object> teacherSubmissionDetail(
            Long submissionId, Long tenantId, Long userId, String role
    ) {
        assertTeacherReviewRole(role);
        boolean teacher = "TEACHER".equalsIgnoreCase(String.valueOf(role));
        List<Map<String, Object>> rows = teacher
                ? jdbc.queryForList(teacherSubmissionSql("""
                    WHERE s.id = ? AND pt.tenant_id = ?
                      AND (pt.mentor_id = ? OR EXISTS (
                        SELECT 1
                        FROM project_team_member mentor
                        WHERE mentor.team_id = pt.id
                          AND mentor.user_id = ?
                          AND mentor.role_in_team = 'MENTOR'
                      ))
                    """), submissionId, tenantId, userId, userId)
                : jdbc.queryForList(teacherSubmissionSql("WHERE s.id = ? AND pt.tenant_id = ?"), submissionId, tenantId);
        if (rows.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "提交记录不存在");
        }

        attachSubmissionPayloads(rows);
        Map<String, Object> result = rows.get(0);
        Long taskId = longValue(result.get("taskId"));
        Long submitterId = longValue(result.get("submitterId"));
        result.put("requirements", jdbc.queryForList("""
            SELECT requirement.id, requirement.title, requirement.description, requirement.required,
                   requirement.asset_type assetType, requirement.sort_order sortOrder
            FROM project_task_requirement requirement
            JOIN project_task t ON t.id = requirement.task_id
            JOIN project_team pt ON pt.id = t.team_id
            WHERE requirement.task_id = ? AND pt.tenant_id = ?
            ORDER BY requirement.sort_order ASC, requirement.id ASC
            """, taskId, tenantId));
        List<Map<String, Object>> history = jdbc.queryForList("""
            SELECT history.id, history.id submissionId, history.version_no versionNo, history.status,
                   history.submitter_id submitterId, submitter.username submitterName,
                   history.submission_type submissionType, history.content,
                   history.attachment_url attachmentUrl, history.attachment_name attachmentName,
                   history.attachment_size attachmentSize, history.attachment_type attachmentType,
                   history.review_comment reviewComment,
                   history.reviewer_id reviewerId, reviewer.username reviewerName,
                   history.reviewed_at reviewedAt, history.created_at createdAt,
                   history.created_at submittedAt, history.task_id taskId, history.team_id teamId
            FROM project_task_submission history
            JOIN project_task t ON t.id = history.task_id
            JOIN project_team pt ON pt.id = t.team_id
            JOIN users submitter ON submitter.id = history.submitter_id
            LEFT JOIN users reviewer ON reviewer.id = history.reviewer_id
            WHERE history.task_id = ? AND history.submitter_id = ? AND pt.tenant_id = ?
            ORDER BY history.version_no DESC, history.id DESC
            """, taskId, submitterId, tenantId).stream()
                .map(row -> {
                    Map<String, Object> copy = new org.springframework.util.LinkedCaseInsensitiveMap<>();
                    copy.putAll(row);
                    return copy;
                })
                .collect(Collectors.toCollection(ArrayList::new));
        attachSubmissionPayloads(history);
        result.put("history", history);
        Long latestSubmissionId = longValue(result.get("latestSubmissionId"));
        String status = text(result.get("status"), "").toUpperCase(Locale.ROOT);
        result.put("canReview", Objects.equals(submissionId, latestSubmissionId)
                && Set.of("PENDING_REVIEW", "REVIEWING").contains(status));
        return result;
    }

    private void assertTeacherReviewRole(String role) {
        if (!canUseTeacherScope(role)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "仅管理员或教师可审核任务提交");
        }
    }

    private String teacherSubmissionSql(String where) {
        return """
            SELECT s.id, s.id submissionId, s.task_id taskId, s.team_id teamId,
                   s.submitter_id submitterId, submitter.username submitterName,
                   s.submission_type submissionType, s.content,
                   s.attachment_url attachmentUrl, s.attachment_name attachmentName,
                   s.attachment_size attachmentSize, s.attachment_type attachmentType,
                   s.sync_to_material syncToMaterial, s.version_no versionNo, s.status,
                   s.reviewer_id reviewerId, reviewer.username reviewerName,
                   s.review_comment reviewComment, s.reviewed_at reviewedAt,
                   s.created_at createdAt, s.created_at submittedAt,
                   t.title taskTitle, t.description taskDescription,
                   t.task_type taskType, t.task_type_label taskTypeLabel,
                   t.priority, t.due_at dueAt, pt.name teamName,
                   (SELECT latest_id.id
                    FROM project_task_submission latest_id
                    WHERE latest_id.task_id = s.task_id
                      AND latest_id.submitter_id = s.submitter_id
                    ORDER BY latest_id.version_no DESC, latest_id.id DESC LIMIT 1) latestSubmissionId,
                   (SELECT c.id
                    FROM training_camp_team ct
                    JOIN training_camp c ON c.id = ct.camp_id AND c.tenant_id = pt.tenant_id
                    WHERE ct.team_id = pt.id AND ct.status = 'ACTIVE'
                    ORDER BY ct.joined_at DESC, c.id DESC LIMIT 1) campId,
                   (SELECT c.name
                    FROM training_camp_team ct
                    JOIN training_camp c ON c.id = ct.camp_id AND c.tenant_id = pt.tenant_id
                    WHERE ct.team_id = pt.id AND ct.status = 'ACTIVE'
                    ORDER BY ct.joined_at DESC, c.id DESC LIMIT 1) campName,
                   (SELECT d.id
                    FROM training_day_task dt
                    JOIN training_day d ON d.id = dt.training_day_id
                    JOIN training_camp c ON c.id = d.camp_id AND c.tenant_id = pt.tenant_id
                    JOIN training_camp_team ct ON ct.camp_id = c.id
                      AND ct.team_id = pt.id AND ct.status = 'ACTIVE'
                    WHERE dt.task_id = t.id
                    ORDER BY ct.joined_at DESC, c.id DESC,
                             d.training_date DESC, d.day_no DESC, d.id DESC LIMIT 1) dayId,
                   (SELECT d.day_no
                    FROM training_day_task dt
                    JOIN training_day d ON d.id = dt.training_day_id
                    JOIN training_camp c ON c.id = d.camp_id AND c.tenant_id = pt.tenant_id
                    JOIN training_camp_team ct ON ct.camp_id = c.id
                      AND ct.team_id = pt.id AND ct.status = 'ACTIVE'
                    WHERE dt.task_id = t.id
                    ORDER BY ct.joined_at DESC, c.id DESC,
                             d.training_date DESC, d.day_no DESC, d.id DESC LIMIT 1) dayNo,
                   (SELECT d.title
                    FROM training_day_task dt
                    JOIN training_day d ON d.id = dt.training_day_id
                    JOIN training_camp c ON c.id = d.camp_id AND c.tenant_id = pt.tenant_id
                    JOIN training_camp_team ct ON ct.camp_id = c.id
                      AND ct.team_id = pt.id AND ct.status = 'ACTIVE'
                    WHERE dt.task_id = t.id
                    ORDER BY ct.joined_at DESC, c.id DESC,
                             d.training_date DESC, d.day_no DESC, d.id DESC LIMIT 1) dayTitle
            FROM project_task_submission s
            JOIN project_task t ON t.id = s.task_id
            JOIN project_team pt ON pt.id = s.team_id AND pt.id = t.team_id
            JOIN users submitter ON submitter.id = s.submitter_id
            LEFT JOIN users reviewer ON reviewer.id = s.reviewer_id
            """ + where;
    }

    public Map<String, Object> dashboard(Long teamId, Long tenantId, Long userId, String role) {
        String roleInTeam = roleInTeam(teamId, userId);
        boolean teacherScope = hasTeacherTeamScope(teamId, userId, role);
        if (!teacherScope && roleInTeam == null) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "无权访问该项目团队");
        }

        boolean canManage = teacherScope || "CAPTAIN".equals(roleInTeam);
        Map<String, Boolean> managementPermissions = managementPermissions(teamId, userId, role);
        syncAiReviewIssues(teamId);
        if (abilityNeedsRefresh(teamId)) {
            refreshAbilitySnapshots(teamId);
        }
        syncProjectStages(teamId);
        Map<String, Object> team = team(teamId, tenantId);

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("team", team);
        result.put("currentUserId", userId);
        result.put("myRoleInTeam", roleInTeam != null ? roleInTeam : "TEACHER");
        result.put("canManage", canManage);
        result.put("canTeachObserve", teacherScope);
        result.put("canEditStageSchedule", canEditStageSchedule(teamId, userId, role, roleInTeam));
        result.put("managementPermissions", managementPermissions);
        result.put("members", members(teamId));
        result.put("positionRoles", positionRoles(tenantId));
        result.put("stages", decorateStages(teamId, userId, roleInTeam, stages(teamId)));
        result.put("metrics", metrics(teamId));
        result.put("tasks", tasks(teamId, canManage ? null : userId, userId, role, tenantId));
        result.put("trainingSchedule", trainingSchedule(teamId, tenantId));
        result.put("submissions", submissions(teamId, canManage ? null : userId));
        result.put("materials", materials(teamId));
        result.put("roadshow", roadshow(teamId));
        // Team review list is strictly team-scoped. Personal history is only for binding.
        result.put("roadshowMeetings", roadshowMeetings(teamId));
        result.put("bindableRoadshowMeetings", bindableRoadshowMeetings(teamId, tenantId, userId, role));
        result.put("reviewIssues", reviewIssues(teamId, teacherScope || canManage ? null : userId));
        result.put("competitionReadiness", competitionReadinessService.build(teamId));
        result.put("abilities", abilities(teamId));
        if (teacherScope) {
            result.put("teacherObservation", teacherObservation(teamId));
        }
        return result;
    }

    public Map<String, Object> taskDetail(
            Long teamId, Long taskId, Long tenantId, Long userId, String role
    ) {
        assertTeamAccess(teamId, tenantId, userId, role);
        assertTrainingTaskAvailableForStudent(teamId, taskId, tenantId, role);
        List<Map<String, Object>> taskRows = jdbc.queryForList(
                taskSql("WHERE t.id = ? AND t.team_id = ?"), taskId, teamId);
        if (taskRows.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "任务不存在");
        }

        Map<String, Object> task = new LinkedHashMap<>(taskRows.get(0));
        attachTaskAssignees(task);
        decorateTaskAccess(task, userId, role);

        List<Map<String, Object>> requirements = jdbc.queryForList("""
            SELECT requirement.id, requirement.title, requirement.description, requirement.required,
                   requirement.asset_type assetType, requirement.sort_order sortOrder
            FROM project_task_requirement requirement
            WHERE requirement.task_id = ?
            ORDER BY requirement.sort_order ASC, requirement.id ASC
            """, taskId);

        List<Map<String, Object>> trainingRows = jdbc.queryForList("""
            SELECT d.id dayId, d.day_no dayNo, d.title dayTitle, d.summary,
                   d.content_html contentHtml, d.training_date trainingDate, d.due_at trainingDueAt,
                   d.status, d.early_unlocked_at earlyUnlockedAt,
                   dt.is_primary isPrimary, dt.sort_order taskSortOrder,
                   c.id campId, c.name campName
            FROM training_day_task dt
            JOIN training_day d ON d.id = dt.training_day_id
            JOIN training_camp c ON c.id = d.camp_id AND c.tenant_id = ?
            JOIN training_camp_team ct ON ct.camp_id = c.id AND ct.team_id = ?
            WHERE dt.task_id = ?
            ORDER BY CASE WHEN ct.status = 'ACTIVE' THEN 0 ELSE 1 END,
                     d.training_date DESC, d.day_no DESC, d.id DESC
            """, tenantId, teamId, taskId);

        Map<String, Object> trainingDay = trainingRows.stream()
                .map(LinkedHashMap::new)
                .peek(row -> row.putAll(trainingDayAvailabilityService.availability(row)))
                .filter(row -> canUseTeacherScope(role) || !Boolean.TRUE.equals(row.get("locked")))
                .findFirst()
                .map(row -> (Map<String, Object>) row)
                .orElse(Map.of());
        if (!trainingDay.isEmpty()) {
            trainingDay.putAll(trainingDayAvailabilityService.availability(trainingDay));
        }
        Long dayId = longValue(trainingDay.get("dayId"));
        boolean primaryTrainingTask = intValue(trainingDay.get("isPrimary"), 0) == 1;
        List<Map<String, Object>> attachments = dayId == null
                ? List.of()
                : jdbc.queryForList("""
                    SELECT id, file_name fileName, file_url fileUrl, file_size fileSize,
                           mime_type mimeType, sort_order sortOrder, status, created_at createdAt
                    FROM training_day_attachment
                    WHERE training_day_id = ? AND status = 'ACTIVE'
                    ORDER BY sort_order ASC, id ASC
                    """, dayId);

        Map<String, Object> taskBook = new LinkedHashMap<>();
        taskBook.put("sourceType", dayId == null ? "PROJECT_TASK" : "TRAINING_DAY");
        taskBook.put("title", task.get("title"));
        taskBook.put("summary", text(trainingDay.get("summary"), text(task.get("description"), "")));
        taskBook.put("contentHtml", primaryTrainingTask ? text(trainingDay.get("contentHtml"), "") : "");
        taskBook.put("requirements", requirements);
        taskBook.put("attachments", attachments);
        taskBook.put("dayId", dayId);
        taskBook.put("dayNo", trainingDay.get("dayNo"));
        taskBook.put("dayTitle", trainingDay.get("dayTitle"));
        taskBook.put("trainingDate", trainingDay.get("trainingDate"));
        taskBook.put("campId", trainingDay.get("campId"));
        taskBook.put("campName", trainingDay.get("campName"));
        taskBook.put("isPrimary", primaryTrainingTask);
        taskBook.putAll(trainingDay.isEmpty()
                ? Map.of()
                : trainingDayAvailabilityService.availability(trainingDay));

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("task", task);
        result.put("taskBook", taskBook);
        return result;
    }

    public Map<String, Object> roadshowMemory(Long teamId, Long tenantId, Long userId, String role) {
        assertTeamAccess(teamId, tenantId, userId, role);
        syncAiReviewIssues(teamId);
        List<Map<String, Object>> rows = jdbc.queryForList("""
            SELECT b.id bindingId, b.team_id teamId, b.meeting_id meetingId, b.roadshow_type roadshowType,
                   m.title meetingTitle, m.status meetingStatus, m.start_time startTime, m.end_time endTime,
                   b.created_at boundAt,
                   ai.id aiReportId, ai.status aiStatus, ai.overall_score aiScore, ai.dimensions_json dimensionsJson,
                   ai.highlights_json highlightsJson, ai.critical_issues_json criticalIssuesJson,
                   ai.improvement_priorities_json improvementPrioritiesJson, ai.speech_quality_json speechQualityJson,
                   ai.score_calibration_json scoreCalibrationJson, ai.transcript transcript, ai.result_path resultPath
            FROM project_roadshow_binding b
            JOIN meeting m ON m.id = b.meeting_id
            JOIN ai_score_report ai ON ai.meeting_id = b.meeting_id
            WHERE b.team_id = ? AND ai.status = 'completed'
            ORDER BY COALESCE(ai.completed_at, b.created_at) ASC, ai.id ASC
            """, teamId);
        List<Map<String, Object>> rounds = rows.stream().map(this::decorateRoadshow).toList();
        Map<String, Object> memory = roadshowMemoryAnalyzer.buildSummary(rounds);
        memory.put("teamId", teamId);
        memory.put("generatedAt", LocalDateTime.now());
        return memory;
    }

    public Map<String, Object> evidenceExcerpt(
            Long teamId,
            Long aiReportId,
            String sourceRef,
            Long tenantId,
            Long userId,
            String role
    ) {
        assertTeamAccess(teamId, tenantId, userId, role);
        String cleanSourceRef = shortText(sourceRef, 240);
        List<Map<String, Object>> rows = jdbc.queryForList("""
            SELECT ai.id aiReportId, ai.meeting_id meetingId, ai.result_path resultPath
            FROM ai_score_report ai
            JOIN project_roadshow_binding b ON b.meeting_id = ai.meeting_id
            WHERE b.team_id = ? AND ai.id = ?
            LIMIT 1
            """, teamId, aiReportId);
        if (rows.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "证据来源不存在或不属于该团队");
        }

        Map<String, Object> row = rows.get(0);
        Path resultPath = resolveAiResultPath(row.get("resultPath"));
        Map<String, Object> excerpt = evidenceAnchorExtractor.extractExcerpt(resultPath, cleanSourceRef);

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("teamId", teamId);
        result.put("aiReportId", longValue(row.get("aiReportId")));
        result.put("meetingId", longValue(row.get("meetingId")));
        result.put("sourceRef", cleanSourceRef);
        if (excerpt.isEmpty()) {
            result.put("type", "unknown");
            result.put("summary", "未找到对应 AI 原始片段，可能是旧报告或该证据来自汇总字段。");
            result.put("raw", Map.of());
            return result;
        }
        result.putAll(excerpt);
        return result;
    }

    public List<Map<String, Object>> positionRoles(Long tenantId) {
        seedDefaultPositionRoles();
        return jdbc.queryForList("""
            SELECT id, name, description, sort_order sortOrder, status
            FROM project_position_role
            WHERE tenant_id = ? AND status = 'ACTIVE'
            ORDER BY sort_order, id
            """, tenantId);
    }

    public List<Map<String, Object>> availableTracks(String role) {
        if (!canUseTeacherScope(role)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "只有教师或管理员可以查看赛道");
        }
        return jdbc.queryForList("""
            SELECT track_id trackId, track_name trackName
            FROM track_rubric_config
            WHERE status = 'active' AND active_slot = 'ACTIVE'
            GROUP BY track_id, track_name
            ORDER BY CONVERT(track_name USING gbk), track_name
            """);
    }

    public Map<String, Object> createPositionRole(Long tenantId, Long userId, String role, Map<String, Object> body) {
        if (!canManagePositionRoles(tenantId, userId, role)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "只有管理员、教师或队长可以新增岗位角色");
        }
        String name = sanitizePositionName(firstText(body, "name", "positionName"), "");
        if (name.isBlank()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "岗位名称不能为空");
        }
        String description = sanitizePositionDescription(firstText(body, "description"), defaultResponsibility(name));
        Integer maxSort = jdbc.queryForObject(
                "SELECT COALESCE(MAX(sort_order), 0) FROM project_position_role WHERE tenant_id = ?",
                Integer.class, tenantId);
        int sortOrder = (maxSort == null ? 0 : maxSort) + 10;
        jdbc.update("""
            INSERT INTO project_position_role (tenant_id, name, description, sort_order, status)
            VALUES (?, ?, ?, ?, 'ACTIVE')
            ON DUPLICATE KEY UPDATE
              description = VALUES(description),
              status = 'ACTIVE'
            """, tenantId, name, description, sortOrder);
        return jdbc.queryForList("""
            SELECT id, name, description, sort_order sortOrder, status
            FROM project_position_role
            WHERE tenant_id = ? AND name = ?
            """, tenantId, name).stream().findFirst()
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "岗位角色保存失败"));
    }

    private boolean canManagePositionRoles(Long tenantId, Long userId, String role) {
        if (canUseTeacherScope(role)) return true;
        Integer captainTeams = jdbc.queryForObject("""
            SELECT COUNT(*) FROM project_team_member m
            JOIN project_team t ON t.id = m.team_id
            WHERE t.tenant_id = ? AND m.user_id = ? AND m.role_in_team = 'CAPTAIN'
            """, Integer.class, tenantId, userId);
        return captainTeams != null && captainTeams > 0;
    }

    private String sanitizePositionDescription(String value, String fallback) {
        String text = nullableText(value);
        if (text == null) text = fallback;
        text = text.replaceAll("[\\r\\n\\t]+", " ").trim();
        return shortText(text, 300);
    }

    public List<Map<String, Object>> candidateMembers(Long tenantId, Long userId, String role) {
        if (!canUseTeacherScope(role)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "只有教师或管理员可以选择项目成员");
        }
        String organizationScope = isAdministrator(role) ? "" : """
            AND (
              (operator.school_id IS NULL AND u.id = operator.id)
              OR (u.school_id = operator.school_id AND (operator.college_id IS NULL OR u.college_id = operator.college_id))
            )
            """;
        return jdbc.queryForList("""
            SELECT u.id, u.username, u.email, u.role,
                   u.school_id schoolId, u.college_id collegeId, u.class_id classId,
                   COALESCE(NULLIF(u.school_name, ''), '未设置学校') schoolName,
                   COALESCE(NULLIF(u.college_name, ''), '未设置学院') collegeName,
                   COALESCE(NULLIF(u.class_name, ''), '未设置班级') className,
                   COALESCE(ug.groupNames, NULLIF(u.user_group, ''), u.role) userGroup
            FROM users u
            JOIN users operator ON operator.id = ? AND operator.tenant_id = u.tenant_id
            LEFT JOIN (
                SELECT gm.tenant_id, gm.user_id,
                       GROUP_CONCAT(g.name ORDER BY g.name SEPARATOR '、') groupNames
                FROM user_group_member gm
                JOIN user_group g ON g.id = gm.group_id AND g.tenant_id = gm.tenant_id AND g.status = 'ACTIVE'
                GROUP BY gm.tenant_id, gm.user_id
            ) ug ON ug.user_id = u.id AND ug.tenant_id = u.tenant_id
            WHERE u.tenant_id = ? AND u.role NOT IN ('ADMIN', 'SCHOOL_ADMIN')
            """ + organizationScope + """
            ORDER BY CASE
                       WHEN u.role = 'STUDENT' THEN 0
                       WHEN u.role = 'TEACHER' THEN 1
                       ELSE 2
                     END, u.username, u.id
            """, userId, tenantId);
    }

    public Map<String, Object> createTeam(Long tenantId, Long userId, String role, Map<String, Object> body) {
        if (!canUseTeacherScope(role)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "只有教师或管理员可以创建项目");
        }
        Long captainId = longValue(body.get("captainUserId"));
        if (captainId == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "请选择项目队长");
        }
        assertTenantProjectParticipant(tenantId, captainId, userId, role);
        Set<Long> memberIds = new LinkedHashSet<>(longList(body.get("memberUserIds")));
        Map<Long, Map<String, Object>> assignments = memberAssignments(body.get("memberAssignments"));
        memberIds.addAll(assignments.keySet());
        memberIds.add(captainId);
        for (Long memberId : memberIds) assertTenantProjectParticipant(tenantId, memberId, userId, role);
        List<String> permissions = sanitizeCaptainPermissions(body.get("captainPermissions"));
        if (permissions.isEmpty()) permissions = CAPTAIN_PERMISSION_KEYS;

        Map<String, Object> track = requireActiveTrack(body.get("trackId"));
        LocalDate startDate = localDateValue(body.get("startDate"));
        LocalDate endDate = localDateValue(body.get("endDate"));
        if (startDate == null || endDate == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "请设置完整的备赛开始日期和结束日期");
        }
        if (endDate.isBefore(startDate)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "备赛结束日期不能早于开始日期");
        }

        Long teamId = insert("""
            INSERT INTO project_team
            (tenant_id, name, description, track_id, track_name, current_stage, status, mentor_id, start_date, end_date, created_by)
            VALUES (?, ?, ?, ?, ?, 'COURSE', 'ACTIVE', ?, ?, ?, ?)
            """,
                tenantId,
                requiredText(body.get("name"), "项目名称不能为空"),
                text(body.get("description"), "围绕课程、测评、材料、路演和复盘推进的项目团队。"),
                track.get("trackId"),
                track.get("trackName"),
                userId,
                startDate,
                endDate,
                userId
        );

        String captainPermissions = permissionsJson(permissions);
        String captainPosition = sanitizePositionName(firstText(body, "captainPositionName", "captainPosition"), "项目经理");
        String captainResponsibility = sanitizeResponsibility(firstText(body, "captainResponsibility", "responsibility"), defaultResponsibility(captainPosition));
        jdbc.update("""
            INSERT INTO project_team_member
            (team_id, user_id, role_in_team, position_name, responsibility, captain_permissions)
            VALUES (?, ?, 'CAPTAIN', ?, ?, ?)
            """, teamId, captainId, captainPosition, captainResponsibility, captainPermissions);
        for (Long memberId : memberIds) {
            if (Objects.equals(memberId, captainId)) continue;
            Map<String, Object> assignment = assignments.getOrDefault(memberId, Map.of());
            String position = sanitizePositionName(firstText(assignment, "positionName", "position"), "项目成员");
            String responsibility = sanitizeResponsibility(firstText(assignment, "responsibility"), defaultResponsibility(position));
            jdbc.update("""
                INSERT INTO project_team_member
                (team_id, user_id, role_in_team, position_name, responsibility)
                VALUES (?, ?, 'MEMBER', ?, ?)
                """, teamId, memberId, position, responsibility);
        }
        if (!memberIds.contains(userId)) {
            jdbc.update("""
                INSERT IGNORE INTO project_team_member
                (team_id, user_id, role_in_team, position_name, responsibility)
                VALUES (?, ?, 'MENTOR', '指导教师', ?)
                """, teamId, userId, defaultResponsibility("指导教师"));
        }
        seedStages(teamId, captainId);
        return team(teamId, tenantId);
    }

    @Transactional
    public Map<String, Object> updateMemberPosition(
            Long teamId,
            Long memberUserId,
            Long tenantId,
            Long userId,
            String role,
            Map<String, Object> body
    ) {
        assertCanManage(teamId, tenantId, userId, role, "ASSIGN_TASK");
        assertTeamMember(teamId, memberUserId);
        String roleInTeam = roleInTeam(teamId, memberUserId);
        String targetSystemRole = null;
        String targetTeamRole = roleInTeam;
        if (body.containsKey("systemRole")) {
            assertTenantProjectParticipant(tenantId, memberUserId, userId, role);
            targetSystemRole = requestedSystemRole(tenantId, memberUserId, role, body.get("systemRole"));
            targetTeamRole = teamRoleForSystemRole(targetSystemRole, roleInTeam);
            preparePrimaryMentorChange(teamId, memberUserId, roleInTeam, targetTeamRole);
        }
        String fallback = "CAPTAIN".equals(targetTeamRole)
                ? "项目经理"
                : "MENTOR".equals(targetTeamRole) ? "指导教师" : "项目成员";
        String position = sanitizePositionName(firstText(body, "positionName", "position"), fallback);
        String responsibility = sanitizeResponsibility(firstText(body, "responsibility"), defaultResponsibility(position));
        if (targetSystemRole == null) {
            jdbc.update("""
                UPDATE project_team_member
                SET position_name = ?, responsibility = ?
                WHERE team_id = ? AND user_id = ?
                """, position, responsibility, teamId, memberUserId);
        } else {
            String currentSystemRole = userSystemRole(tenantId, memberUserId);
            if (!Objects.equals(currentSystemRole, targetSystemRole)) {
                jdbc.update(
                        "UPDATE users SET role = ? WHERE tenant_id = ? AND id = ?",
                        targetSystemRole, tenantId, memberUserId
                );
            }
            jdbc.update("""
                UPDATE project_team_member
                SET role_in_team = ?, position_name = ?, responsibility = ?
                WHERE team_id = ? AND user_id = ?
                """, targetTeamRole, position, responsibility, teamId, memberUserId);
            if ("MENTOR".equals(targetTeamRole)) {
                assignPrimaryMentorIfMissing(teamId, memberUserId);
            }
        }
        realignTeamRoadshows(teamId);
        markAbilityDirty(teamId);
        return members(teamId).stream()
                .filter(member -> Objects.equals(longValue(member.get("userId")), memberUserId))
                .findFirst()
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "团队成员不存在"));
    }

    @Transactional
    public Map<String, Object> addMember(Long teamId,Long tenantId,Long userId,String role,Map<String,Object> body) {
        assertCanManage(teamId,tenantId,userId,role,"ASSIGN_TASK");
        Long memberUserId = longValue(body.get("userId"));
        if (memberUserId == null) throw new ResponseStatusException(HttpStatus.BAD_REQUEST,"请选择成员");
        assertTenantProjectParticipant(tenantId,memberUserId,userId,role);
        String systemRole = requestedSystemRole(tenantId, memberUserId, role, body.get("systemRole"));
        String existingTeamRole = roleInTeam(teamId, memberUserId);
        String teamRole = teamRoleForSystemRole(systemRole, existingTeamRole);
        String fallbackPosition = "MENTOR".equals(teamRole) ? "指导教师" : "项目成员";
        String position = sanitizePositionName(firstText(body,"positionName","position"),fallbackPosition);
        String responsibility = sanitizeResponsibility(firstText(body,"responsibility"),defaultResponsibility(position));
        String currentSystemRole = userSystemRole(tenantId, memberUserId);
        if (!Objects.equals(currentSystemRole, systemRole)) {
            jdbc.update(
                    "UPDATE users SET role = ? WHERE tenant_id = ? AND id = ?",
                    systemRole, tenantId, memberUserId
            );
        }
        if ("CAPTAIN".equals(teamRole)) {
            jdbc.update("""
                UPDATE project_team_member
                SET position_name = ?, responsibility = ?
                WHERE team_id = ? AND user_id = ?
                """, position, responsibility, teamId, memberUserId);
        } else if ("MENTOR".equals(teamRole)) {
            jdbc.update("""
                INSERT INTO project_team_member(team_id, user_id, role_in_team, position_name, responsibility)
                VALUES (?, ?, 'MENTOR', ?, ?)
                ON DUPLICATE KEY UPDATE role_in_team = 'MENTOR',
                  position_name = VALUES(position_name), responsibility = VALUES(responsibility)
                """, teamId, memberUserId, position, responsibility);
            assignPrimaryMentorIfMissing(teamId, memberUserId);
        } else {
            jdbc.update("""
                INSERT INTO project_team_member(team_id, user_id, role_in_team, position_name, responsibility)
                VALUES (?, ?, 'MEMBER', ?, ?)
                ON DUPLICATE KEY UPDATE role_in_team = 'MEMBER',
                  position_name = VALUES(position_name), responsibility = VALUES(responsibility)
                """, teamId, memberUserId, position, responsibility);
        }
        // 学生晚加入时，补齐已发布训练日任务的指派人，避免无法提交前几天任务
        if ("MEMBER".equals(teamRole) || "CAPTAIN".equals(teamRole) || "STUDENT".equalsIgnoreCase(systemRole)) {
            ensureStudentOnPublishedTrainingDayTasks(teamId, memberUserId);
        }
        markAbilityDirty(teamId);
        return members(teamId).stream().filter(m -> Objects.equals(longValue(m.get("userId")),memberUserId)).findFirst()
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND,"团队成员不存在"));
    }

    /**
     * 将学生补录到团队全部「已发布训练日」关联任务的 assignee 中。
     * 解决：训练日发布时快照成员，之后邀请的学生无法提交历史训练日任务。
     */
    public void ensureStudentOnPublishedTrainingDayTasks(Long teamId, Long studentUserId) {
        if (teamId == null || studentUserId == null) return;
        jdbc.update("""
            INSERT IGNORE INTO project_task_assignee (task_id, team_id, user_id, sort_order)
            SELECT t.id, t.team_id, ?, COALESCE((
                SELECT MAX(a.sort_order) + 1 FROM project_task_assignee a WHERE a.task_id = t.id
            ), 0)
            FROM project_task t
            JOIN training_day_task dt ON dt.task_id = t.id
            JOIN training_day d ON d.id = dt.training_day_id
            WHERE t.team_id = ?
              AND d.status = 'PUBLISHED'
              AND (t.task_type = 'TRAINING_DAY' OR t.stage_key = 'TRAINING' OR dt.task_id IS NOT NULL)
            """, studentUserId, teamId);
    }

    /**
     * 全量：团队当前所有学生成员 → 同步到已发布训练日任务指派人。
     * 用于访问训练计划时的懒修复，以及历史数据自愈。
     */
    public int syncAllStudentsToPublishedTrainingDayTasks(Long teamId) {
        if (teamId == null) return 0;
        return jdbc.update("""
            INSERT IGNORE INTO project_task_assignee (task_id, team_id, user_id, sort_order)
            SELECT t.id, t.team_id, tm.user_id, 0
            FROM project_task t
            JOIN training_day_task dt ON dt.task_id = t.id
            JOIN training_day d ON d.id = dt.training_day_id AND d.status = 'PUBLISHED'
            JOIN project_team_member tm ON tm.team_id = t.team_id
              AND tm.role_in_team IN ('CAPTAIN', 'MEMBER')
            JOIN users u ON u.id = tm.user_id AND u.role = 'STUDENT'
            WHERE t.team_id = ?
            """, teamId);
    }

    @Transactional
    public Map<String, Object> removeMember(Long teamId,Long memberUserId,Long tenantId,Long userId,String role) {
        assertCanManage(teamId,tenantId,userId,role,"ASSIGN_TASK");
        String teamRole = roleInTeam(teamId,memberUserId);
        if (Set.of("CAPTAIN","MENTOR").contains(teamRole)) throw new ResponseStatusException(HttpStatus.BAD_REQUEST,"队长或指导教师不能直接移出");
        jdbc.update("DELETE a FROM project_task_assignee a JOIN project_task t ON t.id=a.task_id WHERE t.team_id=? AND a.user_id=?",teamId,memberUserId);
        int affected = jdbc.update("DELETE FROM project_team_member WHERE team_id=? AND user_id=?",teamId,memberUserId);
        if (affected == 0) throw new ResponseStatusException(HttpStatus.NOT_FOUND,"团队成员不存在");
        markAbilityDirty(teamId);
        return Map.of("removed",true,"userId",memberUserId);
    }

    public Map<String, Object> createTask(Long teamId, Long tenantId, Long userId, String role, Map<String, Object> body) {
        assertCanManage(teamId, tenantId, userId, role, "ASSIGN_TASK");
        Long ownerId = longValue(body.get("ownerUserId"));
        if (ownerId != null) assertTeamMember(teamId, ownerId);
        List<Long> assigneeIds = taskAssigneeIds(body, ownerId);
        for (Long assigneeId : assigneeIds) assertTeamMember(teamId, assigneeId);
        String requestedSourceType = text(body.get("sourceType"), "OTHER").toUpperCase(Locale.ROOT);
        String sourceType = "TEACHER_ASSIGNMENT".equals(requestedSourceType) && canUseTeacherScope(role)
                ? "TEACHER_ASSIGNMENT"
                : "OTHER";
        Long reviewerUserId = "TEACHER_ASSIGNMENT".equals(sourceType) ? userId : null;
        Long taskId = insert("""
            INSERT INTO project_task
            (team_id, stage_key, title, description, task_type, task_type_label, time_slot,
             owner_user_id, created_by, source_type, reviewer_user_id,
             priority, status, start_at, due_at, review_required)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            teamId,
            text(body.get("stageKey"), "MATERIAL"),
            requiredText(body.get("title"), "任务标题不能为空"),
            text(body.get("description"), ""),
            text(firstValue(body, "taskType", "businessType"), "OTHER_BUSINESS"),
            nullableText(firstValue(body, "taskTypeLabel", "businessTypeLabel", "customTaskType")),
            nullableText(firstValue(body, "timeSlot", "timePeriod")),
            ownerId,
            userId,
            sourceType,
            reviewerUserId,
            text(body.get("priority"), "MEDIUM"),
            text(body.get("status"), "TODO"),
            text(body.get("startAt"), null),
            text(body.get("dueAt"), null),
            bool(body.get("reviewRequired"), true) ? 1 : 0
        );
        saveTaskAssignees(taskId, teamId, assigneeIds);
        markAbilityDirty(teamId);
        return oneTask(taskId);
    }

    /**
     * 仅由协调请求接受事务调用，不能作为学生任意创建任务的公开接口。
     */
    public Map<String, Object> createAcceptedCollaborationTask(
            Long teamId,
            Long requesterId,
            Long recipientId,
            String title,
            String description,
            String priority,
            Object dueAt
    ) {
        assertTeamMember(teamId, requesterId);
        assertTeamMember(teamId, recipientId);
        Long taskId = insert("""
            INSERT INTO project_task(
              team_id,stage_key,title,description,task_type,task_type_label,
              owner_user_id,created_by,source_type,reviewer_user_id,
              priority,status,due_at,review_required
            ) VALUES (?,'COLLABORATION',?,?, 'COORDINATION','同学协作',
                      ?,?,'PEER_COLLABORATION',?,?,'TODO',?,1)
            """,
                teamId,
                requiredText(title, "任务标题不能为空"),
                text(description, ""),
                recipientId,
                requesterId,
                requesterId,
                text(priority, "MEDIUM"),
                dueAt
        );
        saveTaskAssignees(taskId, teamId, List.of(recipientId));
        markAbilityDirty(teamId);
        return oneTask(taskId);
    }

    public Map<String, Object> updateTask(Long taskId, Long tenantId, Long userId, String role, Map<String, Object> body) {
        Long teamId = taskTeamId(taskId);
        assertCanManage(teamId, tenantId, userId, role, "ASSIGN_TASK");
        Long ownerId = longValue(body.get("ownerUserId"));
        if (ownerId != null) assertTeamMember(teamId, ownerId);
        List<Long> assigneeIds = taskAssigneeIds(body, ownerId);
        for (Long assigneeId : assigneeIds) assertTeamMember(teamId, assigneeId);
        jdbc.update("""
            UPDATE project_task
            SET stage_key = COALESCE(?, stage_key),
                title = COALESCE(?, title),
                description = COALESCE(?, description),
                task_type = COALESCE(?, task_type),
                task_type_label = COALESCE(?, task_type_label),
                time_slot = COALESCE(?, time_slot),
                owner_user_id = COALESCE(?, owner_user_id),
                priority = COALESCE(?, priority),
                status = COALESCE(?, status),
                start_at = COALESCE(?, start_at),
                due_at = COALESCE(?, due_at)
            WHERE id = ?
            """,
            nullableText(body.get("stageKey")),
            nullableText(body.get("title")),
            nullableText(body.get("description")),
            nullableText(firstValue(body, "taskType", "businessType")),
            nullableText(firstValue(body, "taskTypeLabel", "businessTypeLabel", "customTaskType")),
            nullableText(firstValue(body, "timeSlot", "timePeriod")),
            ownerId,
            nullableText(body.get("priority")),
            nullableText(body.get("status")),
            nullableText(body.get("startAt")),
            nullableText(body.get("dueAt")),
            taskId
        );
        if (body.containsKey("assigneeUserIds") || body.containsKey("ownerUserIds") || body.containsKey("ownerUserId")) {
            saveTaskAssignees(taskId, teamId, assigneeIds);
        }
        markAbilityDirty(teamId);
        return oneTask(taskId);
    }

    @Transactional
    public Map<String, Object> submitTask(Long taskId, Long tenantId, Long userId, String role, Map<String, Object> body) {
        Long teamId = taskTeamId(taskId);
        assertTeamAccess(teamId, tenantId, userId, role);
        assertTrainingTaskAvailableForStudent(teamId, taskId, tenantId, role);
        // 训练日任务：当前团队学生应可提交；晚加入成员在提交前补齐 assignee
        if (isPublishedTrainingDayTask(taskId) && isStudentTeamParticipant(teamId, userId)) {
            ensureStudentOnPublishedTrainingDayTasks(teamId, userId);
        }
        Map<String, Object> task = oneTask(taskId);
        Long ownerId = longValue(task.get("ownerUserId"));
        Integer assignmentCount = jdbc.queryForObject("""
            SELECT COUNT(*)
            FROM project_task_assignee
            WHERE task_id = ? AND user_id = ?
            """, Integer.class, taskId, userId);
        boolean canSubmit = Objects.equals(ownerId, userId) || (assignmentCount != null && assignmentCount > 0);
        // 训练日任务兜底：已是团队学生成员即可提交（即使历史 assignee 未同步）
        if (!canSubmit && isPublishedTrainingDayTask(taskId) && isStudentTeamParticipant(teamId, userId)) {
            jdbc.update("""
                INSERT IGNORE INTO project_task_assignee (task_id, team_id, user_id, sort_order)
                VALUES (?, ?, ?, 0)
                """, taskId, teamId, userId);
            canSubmit = true;
        }
        if (!canSubmit) throw new ResponseStatusException(HttpStatus.FORBIDDEN, "只能提交自己负责的任务");
        assertRequiredLearningCompleted(taskId, userId);
        String content = text(body.get("content"), "").trim();
        String submissionType = normalizeSubmissionType(body.get("submissionType"));
        List<Map<String, Object>> assets = normalizeSubmissionAssets(body, taskId, teamId);
        List<Map<String, Object>> links = normalizeSubmissionLinks(body, taskId, teamId);
        boolean syncToMaterial = bool(body.get("syncToMaterial"), true);
        if (content.isBlank() && assets.isEmpty() && links.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "请填写提交说明、成果链接或上传成果文件");
        }
        Map<String, Object> recent = findRecentDuplicateSubmission(taskId, userId, content, assets, links);
        if (recent != null) {
            recent.put("idempotentReuse", true);
            org.slf4j.LoggerFactory.getLogger(ProjectTeamService.class).info(
                    "training-task submit reused taskId={} userId={} submissionId={}",
                    taskId, userId, recent.get("id")
            );
            return recent;
        }
        Map<String, Object> firstAsset = assets.isEmpty() ? Map.of() : assets.get(0);
        Integer version = jdbc.queryForObject("SELECT COALESCE(MAX(version_no), 0) + 1 FROM project_task_submission WHERE task_id = ?", Integer.class, taskId);
        Long submissionId = insert("""
            INSERT INTO project_task_submission
            (task_id, team_id, submitter_id, submission_type, content, attachment_url, attachment_name, attachment_size, attachment_type, sync_to_material, version_no, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING_REVIEW')
            """,
            taskId,
            teamId,
            userId,
            submissionType,
            content,
            nullableText(firstAsset.get("fileUrl")),
            nullableText(firstAsset.get("fileName")),
            longValue(firstAsset.get("fileSize")),
            nullableText(firstAsset.get("fileType")),
            syncToMaterial ? 1 : 0,
            version
        );
        saveSubmissionAssets(submissionId, taskId, teamId, assets);
        saveSubmissionLinks(submissionId, taskId, teamId, links);
        String sourceType = text(task.get("sourceType"), "OTHER").toUpperCase(Locale.ROOT);
        boolean delayedMaterialSync = Set.of("PEER_COLLABORATION", "TEACHER_ASSIGNMENT").contains(sourceType);
        boolean materialSyncFailed = false;
        if (syncToMaterial && !delayedMaterialSync) {
            try {
                syncSubmissionToMaterials(
                        task,
                        submissionId,
                        teamId,
                        userId,
                        null,
                        submissionType,
                        content,
                        assets,
                        links,
                        "PENDING_REVIEW"
                );
            } catch (Exception syncError) {
                materialSyncFailed = true;
                org.slf4j.LoggerFactory.getLogger(ProjectTeamService.class).warn(
                        "training-task material sync failed taskId={} submissionId={}: {}",
                        taskId, submissionId, syncError.getMessage()
                );
            }
        }
        jdbc.update("UPDATE project_task SET status = 'REVIEWING' WHERE id = ?", taskId);
        markAbilityDirty(teamId);
        Map<String, Object> saved = oneSubmission(submissionId);
        saved.put("materialSyncFailed", materialSyncFailed);
        org.slf4j.LoggerFactory.getLogger(ProjectTeamService.class).info(
                "training-task submitted taskId={} teamId={} userId={} submissionId={} version={} assets={} links={} materialSyncFailed={}",
                taskId, teamId, userId, submissionId, version, assets.size(), links.size(), materialSyncFailed
        );
        return saved;
    }

    static final int SUBMIT_IDEMPOTENT_WINDOW_SECONDS = 5;

    private Map<String, Object> findRecentDuplicateSubmission(
            Long taskId,
            Long userId,
            String content,
            List<Map<String, Object>> assets,
            List<Map<String, Object>> links
    ) {
        try {
            List<Map<String, Object>> rows = jdbc.queryForList("""
                SELECT id
                FROM project_task_submission
                WHERE task_id = ? AND submitter_id = ?
                  AND created_at >= DATE_SUB(NOW(), INTERVAL ? SECOND)
                ORDER BY id DESC
                LIMIT 1
                """, taskId, userId, SUBMIT_IDEMPOTENT_WINDOW_SECONDS);
            if (rows.isEmpty()) return null;
            Long existingId = longValue(rows.get(0).get("id"));
            if (existingId == null) return null;
            Map<String, Object> existing = oneSubmission(existingId);
            String existingContent = text(existing.get("content"), "").trim();
            if (!existingContent.equals(content == null ? "" : content.trim())) {
                return null;
            }
            String newUrl = firstAssetUrl(assets);
            String oldUrl = firstAssetUrl(mapList(existing.get("assets")));
            if (newUrl != null && oldUrl != null && !newUrl.equals(oldUrl)) {
                return null;
            }
            String newLink = firstLinkUrl(links);
            String oldLink = firstLinkUrl(mapList(existing.get("links")));
            if (newLink != null && oldLink != null && !newLink.equals(oldLink)) {
                return null;
            }
            return existing;
        } catch (Exception ignored) {
            return null;
        }
    }

    private String firstAssetUrl(List<Map<String, Object>> assets) {
        if (assets == null || assets.isEmpty()) return null;
        return nullableText(firstNonBlank(assets.get(0).get("fileUrl"), assets.get(0).get("url")));
    }

    private String firstLinkUrl(List<Map<String, Object>> links) {
        if (links == null || links.isEmpty()) return null;
        return nullableText(firstNonBlank(links.get(0).get("url"), links.get(0).get("href")));
    }

    private void assertRequiredLearningCompleted(Long taskId, Long userId) {
        Integer incomplete = jdbc.queryForObject("""
            SELECT COUNT(*)
            FROM training_day_task dt
            JOIN training_day_learning_resource r
              ON r.training_day_id = dt.training_day_id
             AND r.status = 'ACTIVE'
             AND r.is_required = 1
            LEFT JOIN training_learning_progress p
              ON p.learning_resource_id = r.id AND p.user_id = ?
            WHERE dt.task_id = ?
              AND COALESCE(p.status, 'NOT_STARTED') <> 'COMPLETED'
              AND COALESCE(p.progress_percent, 0) < 100
            """, Integer.class, userId, taskId);
        if (incomplete != null && incomplete > 0) {
            throw new ResponseStatusException(
                    HttpStatus.CONFLICT,
                    "还有 " + incomplete + " 项必学内容未完成，请先完成学习再提交"
            );
        }
    }

    private String normalizeSubmissionType(Object value) {
        String type = text(value, "OTHER").trim().toUpperCase(Locale.ROOT);
        Set<String> allowed = Set.of("DOCUMENT", "PPT", "SCRIPT", "CODE", "VIDEO", "DATA", "DESIGN", "IMAGE", "PACKAGE", "LINK", "OTHER");
        return allowed.contains(type) ? type : "OTHER";
    }

    private List<Map<String, Object>> normalizeSubmissionAssets(Map<String, Object> body, Long taskId, Long teamId) {
        List<Map<String, Object>> assets = new ArrayList<>();
        for (Map<String, Object> item : mapList(body.get("assets"))) {
            String fileUrl = nullableText(firstNonBlank(item.get("fileUrl"), item.get("url"), item.get("attachmentUrl")));
            if (fileUrl == null) continue;
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("taskId", taskId);
            row.put("teamId", teamId);
            row.put("assetKind", text(firstNonBlank(item.get("assetKind"), item.get("kind")), "MAIN").toUpperCase(Locale.ROOT));
            row.put("fileUrl", fileUrl);
            row.put("fileName", nullableText(firstNonBlank(item.get("fileName"), item.get("name"), item.get("attachmentName"))));
            row.put("fileSize", longValue(firstNonBlank(item.get("fileSize"), item.get("size"), item.get("attachmentSize"))));
            row.put("fileType", nullableText(firstNonBlank(item.get("fileType"), item.get("type"), item.get("attachmentType"))));
            row.put("sortOrder", assets.size());
            assets.add(row);
        }
        String legacyUrl = nullableText(body.get("attachmentUrl"));
        if (legacyUrl != null && assets.stream().noneMatch(item -> legacyUrl.equals(item.get("fileUrl")))) {
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("taskId", taskId);
            row.put("teamId", teamId);
            row.put("assetKind", "MAIN");
            row.put("fileUrl", legacyUrl);
            row.put("fileName", nullableText(body.get("attachmentName")));
            row.put("fileSize", longValue(body.get("attachmentSize")));
            row.put("fileType", nullableText(body.get("attachmentType")));
            row.put("sortOrder", assets.size());
            assets.add(row);
        }
        return assets;
    }

    private List<Map<String, Object>> normalizeSubmissionLinks(Map<String, Object> body, Long taskId, Long teamId) {
        List<Map<String, Object>> links = new ArrayList<>();
        for (Map<String, Object> item : mapList(body.get("links"))) {
            String url = nullableText(firstNonBlank(item.get("url"), item.get("href"), item.get("link")));
            if (url == null) continue;
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("taskId", taskId);
            row.put("teamId", teamId);
            row.put("linkType", text(firstNonBlank(item.get("linkType"), item.get("type")), "OTHER").toUpperCase(Locale.ROOT));
            row.put("title", nullableText(firstNonBlank(item.get("title"), item.get("name"))));
            row.put("url", url);
            row.put("sortOrder", links.size());
            links.add(row);
        }
        String legacyLink = nullableText(body.get("linkUrl"));
        if (legacyLink == null) legacyLink = nullableText(body.get("submissionLink"));
        final String finalLegacyLink = legacyLink;
        if (finalLegacyLink != null && links.stream().noneMatch(item -> finalLegacyLink.equals(item.get("url")))) {
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("taskId", taskId);
            row.put("teamId", teamId);
            row.put("linkType", "OTHER");
            row.put("title", nullableText(body.get("linkTitle")));
            row.put("url", finalLegacyLink);
            row.put("sortOrder", links.size());
            links.add(row);
        }
        return links;
    }

    private void saveSubmissionAssets(Long submissionId, Long taskId, Long teamId, List<Map<String, Object>> assets) {
        int order = 0;
        for (Map<String, Object> asset : assets) {
            jdbc.update("""
                INSERT INTO project_submission_asset
                (submission_id, task_id, team_id, asset_kind, file_url, file_name, file_size, file_type, sort_order)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                submissionId,
                taskId,
                teamId,
                text(asset.get("assetKind"), "MAIN"),
                nullableText(asset.get("fileUrl")),
                nullableText(asset.get("fileName")),
                longValue(asset.get("fileSize")),
                nullableText(asset.get("fileType")),
                order++
            );
        }
    }

    private void saveSubmissionLinks(Long submissionId, Long taskId, Long teamId, List<Map<String, Object>> links) {
        int order = 0;
        for (Map<String, Object> link : links) {
            jdbc.update("""
                INSERT INTO project_submission_link
                (submission_id, task_id, team_id, link_type, title, url, sort_order)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                submissionId,
                taskId,
                teamId,
                text(link.get("linkType"), "OTHER"),
                nullableText(link.get("title")),
                nullableText(link.get("url")),
                order++
            );
        }
    }

    private void syncSubmissionToMaterials(
            Map<String, Object> task,
            Long submissionId,
            Long teamId,
            Long ownerUserId,
            Long reviewerUserId,
            String submissionType,
            String content,
            List<Map<String, Object>> assets,
            List<Map<String, Object>> links,
            String reviewStatus
    ) {
        Long taskId = longValue(task.get("id"));
        String taskTitle = text(task.get("title"), "任务成果");
        String materialType = materialTypeForSubmission(submissionType);
        String description = content.isBlank() ? text(task.get("description"), "任务提交成果") : shortText(content, 500);
        int index = 1;
        for (Map<String, Object> asset : assets) {
            String name = nullableText(asset.get("fileName"));
            if (name == null) name = taskTitle + " 成果 " + index;
            String sourceItemKey = "submission:" + submissionId + ":asset:" + index;
            jdbc.update("""
                INSERT INTO project_material
                (team_id, material_type, name, description, owner_user_id, source_type, file_url,
                 linked_task_id, review_status, reviewer_id, source_submission_id, source_item_key)
                VALUES (?, ?, ?, ?, ?, 'TASK_SUBMISSION', ?, ?, ?, ?, ?, ?)
                ON DUPLICATE KEY UPDATE
                  review_status=VALUES(review_status),
                  reviewer_id=COALESCE(VALUES(reviewer_id),reviewer_id)
                """,
                teamId,
                materialType,
                shortText(name, 160),
                description,
                ownerUserId,
                nullableText(asset.get("fileUrl")),
                taskId,
                reviewStatus,
                reviewerUserId,
                submissionId,
                sourceItemKey
            );
            index++;
        }
        for (Map<String, Object> link : links) {
            String title = nullableText(link.get("title"));
            if (title == null) title = taskTitle + " 链接 " + index;
            String sourceItemKey = "submission:" + submissionId + ":link:" + index;
            jdbc.update("""
                INSERT INTO project_material
                (team_id, material_type, name, description, owner_user_id, source_type, file_url,
                 linked_task_id, review_status, reviewer_id, source_submission_id, source_item_key)
                VALUES (?, ?, ?, ?, ?, 'TASK_LINK', ?, ?, ?, ?, ?, ?)
                ON DUPLICATE KEY UPDATE
                  review_status=VALUES(review_status),
                  reviewer_id=COALESCE(VALUES(reviewer_id),reviewer_id)
                """,
                teamId,
                "LINK",
                shortText(title, 160),
                description,
                ownerUserId,
                nullableText(link.get("url")),
                taskId,
                reviewStatus,
                reviewerUserId,
                submissionId,
                sourceItemKey
            );
            index++;
        }
    }

    private String materialTypeForSubmission(String submissionType) {
        return switch (submissionType) {
            case "PPT" -> "PPT";
            case "SCRIPT", "DOCUMENT" -> "DOC";
            case "VIDEO" -> "VIDEO";
            case "DATA" -> "DATA";
            case "DESIGN", "IMAGE" -> "IMAGE";
            case "CODE", "PACKAGE" -> "OTHER";
            case "LINK" -> "LINK";
            default -> "OTHER";
        };
    }

    @Transactional
    public Map<String, Object> reviewSubmission(Long submissionId, Long tenantId, Long userId, String role, Map<String, Object> body) {
        Map<String, Object> submission = oneSubmission(submissionId);
        Long teamId = longValue(submission.get("teamId"));
        team(teamId, tenantId);
        Long taskId = longValue(submission.get("taskId"));
        assertCanReviewSubmission(teamId, taskId, userId, role);
        String status = text(body.get("status"), "CHANGES_REQUESTED").toUpperCase(Locale.ROOT);
        if (!Set.of("APPROVED", "REJECTED", "CHANGES_REQUESTED").contains(status)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "不支持的审核状态");
        }

        Long submitterId = longValue(submission.get("submitterId"));
        Long latestSubmissionId = jdbc.queryForObject("""
            SELECT latest.id
            FROM project_task_submission latest
            WHERE latest.task_id = ? AND latest.submitter_id = ?
            ORDER BY latest.version_no DESC, latest.id DESC
            LIMIT 1
            """, Long.class, taskId, submitterId);
        if (!Objects.equals(submissionId, latestSubmissionId)) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "只能审核任务的最新提交版本");
        }
        String currentStatus = text(submission.get("status"), "").toUpperCase(Locale.ROOT);
        if (!Set.of("PENDING_REVIEW", "REVIEWING").contains(currentStatus)) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "该提交已完成审核，不能重复操作");
        }

        int affected = jdbc.update("""
            UPDATE project_task_submission current
            SET status = ?, reviewer_id = ?, review_comment = ?, reviewed_at = NOW()
            WHERE current.id = (
              SELECT eligible.id
              FROM (
                SELECT candidate.id
                FROM project_task_submission candidate
                WHERE candidate.id = ?
                  AND candidate.status IN ('PENDING_REVIEW', 'REVIEWING')
                  AND NOT EXISTS (
                    SELECT 1
                    FROM project_task_submission newer
                    WHERE newer.task_id = candidate.task_id
                      AND newer.submitter_id = candidate.submitter_id
                      AND (newer.version_no > candidate.version_no
                        OR (newer.version_no = candidate.version_no AND newer.id > candidate.id))
                  )
              ) eligible
              )
            """, status, userId, text(body.get("reviewComment"), ""), submissionId);
        if (affected != 1) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "提交状态已变化，请刷新后重试");
        }
        int unresolvedAssignees = jdbc.queryForObject("""
            SELECT COUNT(*) FROM project_task_assignee a
            WHERE a.task_id=? AND NOT EXISTS (
              SELECT 1 FROM project_task_submission latest
              WHERE latest.task_id=a.task_id AND latest.submitter_id=a.user_id
                AND latest.id=(SELECT x.id FROM project_task_submission x
                  WHERE x.task_id=latest.task_id AND x.submitter_id=latest.submitter_id
                  ORDER BY x.version_no DESC,x.id DESC LIMIT 1)
                AND latest.status='APPROVED'
            )
            """, Integer.class, taskId);
        jdbc.update("UPDATE project_task SET status = ? WHERE id = ?",
                unresolvedAssignees == 0 ? "DONE" : "IN_PROGRESS", taskId);
        if ("APPROVED".equals(status) && bool(submission.get("syncToMaterial"), true)) {
            Map<String, Object> task = oneTask(taskId);
            String sourceType = text(task.get("sourceType"), "OTHER").toUpperCase(Locale.ROOT);
            if (Set.of("PEER_COLLABORATION", "TEACHER_ASSIGNMENT").contains(sourceType)) {
                syncSubmissionToMaterials(
                        task,
                        submissionId,
                        teamId,
                        submitterId,
                        userId,
                        text(submission.get("submissionType"), "OTHER"),
                        text(submission.get("content"), ""),
                        mapList(submission.get("assets")),
                        mapList(submission.get("links")),
                        "APPROVED"
                );
            }
        }
        markAbilityDirty(teamId);
        syncProjectStages(teamId);
        return oneSubmission(submissionId);
    }

    public Map<String, Object> createMaterial(Long teamId, Long tenantId, Long userId, String role, Map<String, Object> body) {
        assertTeamAccess(teamId, tenantId, userId, role);
        Long ownerId = longValue(body.get("ownerUserId"));
        if (ownerId != null) assertTeamMember(teamId, ownerId);
        String reviewStatus = isPrivilegedUploader(role) ? "APPROVED" : "PENDING_REVIEW";
        Long materialId = insert("""
            INSERT INTO project_material
            (team_id, material_type, name, description, owner_user_id, source_type, file_url, linked_task_id, review_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            teamId,
            text(body.get("materialType"), "DOCS"),
            requiredText(body.get("name"), "材料名称不能为空"),
            text(body.get("description"), ""),
            ownerId != null ? ownerId : userId,
            text(body.get("sourceType"), "MANUAL"),
            nullableText(body.get("fileUrl")),
            longValue(body.get("linkedTaskId")),
            reviewStatus
        );
        markAbilityDirty(teamId);
        return oneMaterial(materialId);
    }

    /**
     * 团队共享资源：实际上传文件到 uploads/project-teams/{teamId}/，并写入 project_material。
     */
    @Transactional
    public Map<String, Object> uploadMaterial(
            Long teamId,
            Long tenantId,
            Long userId,
            String role,
            MultipartFile file,
            String name,
            String materialType,
            String description
    ) {
        assertTeamAccess(teamId, tenantId, userId, role);
        if (file == null || file.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "请选择要上传的文件");
        }
        if (file.getSize() > MAX_TEAM_MATERIAL_BYTES) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "单个文件不能超过 200MB");
        }
        String original = safeMaterialFileName(file.getOriginalFilename());
        String extension = materialExtension(original);
        if (!TEAM_MATERIAL_EXTENSIONS.contains(extension)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST,
                    "不支持的文件类型，请上传文档、图片、音视频或常见压缩包");
        }
        String storedName = UUID.randomUUID().toString().replace("-", "") + "." + extension;
        Path relative = Paths.get("project-teams", String.valueOf(teamId), storedName);
        try {
            Path target = uploadRoot.resolve(relative).normalize();
            if (!target.startsWith(uploadRoot)) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "文件路径不合法");
            }
            Files.createDirectories(target.getParent());
            Files.copy(file.getInputStream(), target, StandardCopyOption.REPLACE_EXISTING);
        } catch (ResponseStatusException ex) {
            throw ex;
        } catch (Exception ex) {
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "文件保存失败");
        }
        String url = "/uploads/" + relative.toString().replace('\\', '/');
        String displayName = (name == null || name.isBlank()) ? stripExtension(original) : name.trim();
        if (displayName.isBlank()) displayName = "未命名文件";
        String type = (materialType == null || materialType.isBlank())
                ? guessMaterialType(extension)
                : materialType.trim().toUpperCase(Locale.ROOT);
        String reviewStatus = isPrivilegedUploader(role) ? "APPROVED" : "PENDING_REVIEW";
        Long materialId = insert("""
            INSERT INTO project_material
            (team_id, material_type, name, description, owner_user_id, source_type, file_url, linked_task_id, review_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                teamId,
                type,
                displayName,
                description == null ? "" : description.trim(),
                userId,
                "UPLOAD",
                url,
                null,
                reviewStatus
        );
        markAbilityDirty(teamId);
        return oneMaterial(materialId);
    }

    private boolean isPrivilegedUploader(String role) {
        String r = role == null ? "" : role.trim().toUpperCase(Locale.ROOT);
        return Set.of("TEACHER", "ADMIN", "SCHOOL_ADMIN", "MENTOR").contains(r);
    }

    private String safeMaterialFileName(String raw) {
        if (raw == null || raw.isBlank()) return "file.bin";
        String name = Paths.get(raw).getFileName().toString().replaceAll("[\\\\/\\0]", "_").trim();
        return name.isBlank() ? "file.bin" : name;
    }

    private String materialExtension(String fileName) {
        int i = fileName.lastIndexOf('.');
        if (i < 0 || i == fileName.length() - 1) return "";
        return fileName.substring(i + 1).toLowerCase(Locale.ROOT);
    }

    private String stripExtension(String fileName) {
        int i = fileName.lastIndexOf('.');
        return i > 0 ? fileName.substring(0, i) : fileName;
    }

    private String guessMaterialType(String extension) {
        return switch (extension) {
            case "ppt", "pptx" -> "PPT";
            case "pdf", "doc", "docx", "txt", "md", "xls", "xlsx", "csv" -> "DOCS";
            case "mp4", "webm", "mov" -> "VIDEO";
            case "png", "jpg", "jpeg", "gif", "webp" -> "DOCS";
            default -> "DOCS";
        };
    }

    public Map<String, Object> reviewMaterial(Long materialId, Long tenantId, Long userId, String role, Map<String, Object> body) {
        Map<String, Object> material = oneMaterial(materialId);
        Long teamId = longValue(material.get("teamId"));
        assertCanManage(teamId, tenantId, userId, role, "REVIEW_MATERIAL");
        String status = text(body.get("reviewStatus"), "CHANGES_REQUESTED").toUpperCase(Locale.ROOT);
        if (!Set.of("APPROVED", "REJECTED", "CHANGES_REQUESTED", "PENDING_REVIEW").contains(status)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "不支持的材料审核状态");
        }
        jdbc.update("""
            UPDATE project_material
            SET review_status = ?, reviewer_id = ?, review_comment = ?
            WHERE id = ?
            """, status, userId, text(body.get("reviewComment"), ""), materialId);
        markAbilityDirty(teamId);
        syncProjectStages(teamId);
        return oneMaterial(materialId);
    }

    public Map<String, Object> bindRoadshow(Long teamId, Long tenantId, Long userId, String role, Map<String, Object> body) {
        assertCanManage(teamId, tenantId, userId, role, "BIND_ROADSHOW");
        Long meetingId = longValue(body.get("meetingId"));
        if (meetingId == null) throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "meetingId 不能为空");
        Integer count = jdbc.queryForObject("SELECT COUNT(*) FROM meeting WHERE tenant_id = ? AND id = ?", Integer.class, tenantId, meetingId);
        if (count == null || count == 0) throw new ResponseStatusException(HttpStatus.NOT_FOUND, "会议不存在");
        jdbc.update("""
            INSERT IGNORE INTO project_roadshow_binding (team_id, meeting_id, roadshow_type, created_by)
            VALUES (?, ?, ?, ?)
            """, teamId, meetingId, text(body.get("roadshowType"), "REHEARSAL"), userId);
        markAbilityDirty(teamId);
        syncProjectStages(teamId);
        return roadshow(teamId);
    }

    /**
     * 管理员/指导教师调整阶段配置（排期、必做/可选、说明文案）。
     */
    public Map<String, Object> updateStageSchedule(
            Long teamId,
            String stageKey,
            Long tenantId,
            Long userId,
            String role,
            Map<String, Object> body
    ) {
        assertCanEditStageSchedule(teamId, tenantId, userId, role);
        String key = text(stageKey, "").trim().toUpperCase(Locale.ROOT);
        if (key.isBlank()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "阶段编码不能为空");
        }
        Integer exists = jdbc.queryForObject(
                "SELECT COUNT(*) FROM project_stage WHERE team_id = ? AND stage_key = ?",
                Integer.class, teamId, key);
        if (exists == null || exists == 0) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "阶段不存在");
        }

        String title = body.containsKey("title") ? text(body.get("title"), "").trim() : null;
        LocalDate startDate = body.containsKey("startDate") ? localDateValue(body.get("startDate")) : null;
        LocalDate dueDate = body.containsKey("dueDate") ? localDateValue(body.get("dueDate")) : null;
        Boolean optional = body.containsKey("optional") ? booleanValue(body.get("optional")) : null;
        String suggestionText = body.containsKey("suggestion") ? nullableText(body.get("suggestion")) : null;

        if (title == null && startDate == null && dueDate == null && optional == null && !body.containsKey("suggestion")) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "请提供需要更新的阶段配置");
        }
        if (title != null && title.isBlank()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "阶段名称不能为空");
        }
        if (startDate != null && dueDate != null && startDate.isAfter(dueDate)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "开始日期不能晚于截止日期");
        }

        Map<String, Object> current = oneStage(teamId, key);
        String nextTitle = title != null ? title : text(current.get("title"), "");
        LocalDate nextStart = startDate != null ? startDate : localDateValue(current.get("startDate"));
        LocalDate nextDue = dueDate != null ? dueDate : localDateValue(current.get("dueDate"));
        int nextOptional = optional != null ? (optional ? 1 : 0) : stageIsOptional(current) ? 1 : 0;
        String nextSuggestion = body.containsKey("suggestion") ? suggestionText : nullableText(current.get("suggestionText"));

        if (nextStart != null && nextDue != null && nextStart.isAfter(nextDue)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "开始日期不能晚于截止日期");
        }

        jdbc.update("""
            UPDATE project_stage
            SET title = ?, start_date = ?, due_date = ?, is_optional = ?, suggestion_text = ?
            WHERE team_id = ? AND stage_key = ?
            """, nextTitle, nextStart, nextDue, nextOptional, nextSuggestion, teamId, key);

        Map<String, Object> row = oneStage(teamId, key);
        String roleInTeam = roleInTeam(teamId, userId);
        return decorateStages(teamId, userId, roleInTeam, List.of(row)).get(0);
    }

    private Map<String, Object> oneStage(Long teamId, String stageKey) {
        List<Map<String, Object>> rows = jdbc.queryForList("""
            SELECT s.id, s.stage_key stageKey, s.title, s.status, s.progress,
                   s.owner_user_id ownerUserId, u.username ownerName,
                   s.start_date startDate, s.due_date dueDate,
                   s.is_optional isOptional, s.suggestion_text suggestionText
            FROM project_stage s
            LEFT JOIN users u ON u.id = s.owner_user_id
            WHERE s.team_id = ? AND s.stage_key = ?
            """, teamId, stageKey);
        if (rows.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "阶段不存在");
        }
        return rows.get(0);
    }

    private void seedStages(Long teamId, Long captainId) {
        Object[][] stages = {
                {"COURSE", "课程学习", "PENDING", 0, 1},
                {"EXAM", "能力测评", "PENDING", 0, 2},
                {"MATERIAL", "材料准备", "PENDING", 0, 3},
                {"ROADSHOW", "路演展示", "PENDING", 0, 4},
                {"REVIEW", "复盘提升", "PENDING", 0, 5}
        };
        for (Object[] stage : stages) {
            String stageKey = String.valueOf(stage[0]);
            int isOptional = OPTIONAL_STAGE_KEYS.contains(stageKey) ? 1 : 0;
            jdbc.update("""
                INSERT IGNORE INTO project_stage
                (team_id, stage_key, title, status, progress, owner_user_id, start_date, due_date, sort_order, is_optional)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, teamId, stage[0], stage[1], stage[2], stage[3], captainId,
                    LocalDate.now().minusDays(7), LocalDate.now().plusDays((Integer) stage[4] * 3L), stage[4], isOptional);
        }
        syncProjectStages(teamId);
    }

    /**
     * Intentionally removed auto-bind of "latest tenant meeting".
     * That logic attached unrelated meetings to brand-new teams.
     * Teams now start with zero bindings; managers bind explicitly.
     */

    private Map<String, Object> team(Long teamId, Long tenantId) {
        List<Map<String, Object>> rows = jdbc.queryForList("""
            SELECT id, tenant_id tenantId, name, description, track_id trackId, track_name trackName,
                   current_stage currentStage, status,
                   mentor_id mentorId, start_date startDate, end_date endDate
            FROM project_team WHERE id = ? AND tenant_id = ?
            """, teamId, tenantId);
        if (rows.isEmpty()) throw new ResponseStatusException(HttpStatus.NOT_FOUND, "项目团队不存在");
        return rows.get(0);
    }

    private List<Map<String, Object>> members(Long teamId) {
        return jdbc.queryForList("""
            SELECT m.id, m.team_id teamId, m.user_id userId, u.username, u.role systemRole,
                   m.role_in_team roleInTeam, m.position_name positionName, m.responsibility,
                   m.captain_permissions captainPermissions
            FROM project_team_member m
            JOIN users u ON u.id = m.user_id
            WHERE m.team_id = ?
            ORDER BY FIELD(m.role_in_team, 'CAPTAIN', 'MEMBER', 'MENTOR', 'OBSERVER'), m.id
            """, teamId);
    }

    private List<Map<String, Object>> stages(Long teamId) {
        return jdbc.queryForList("""
            SELECT s.id, s.stage_key stageKey, s.title, s.status, s.progress,
                   s.owner_user_id ownerUserId, u.username ownerName,
                   s.start_date startDate, s.due_date dueDate,
                   s.is_optional isOptional, s.suggestion_text suggestionText
            FROM project_stage s
            LEFT JOIN users u ON u.id = s.owner_user_id
            WHERE s.team_id = ?
            ORDER BY s.sort_order
            """, teamId);
    }

    /**
     * 按真实业务数据回写团队阶段进度。课程/测评为建议项；主链路为材料→路演→复盘。
     * 不设置任何操作门禁，仅更新展示用 progress/status。
     */
    private void syncProjectStages(Long teamId) {
        List<Long> studentUserIds = studentMemberUserIds(teamId);
        int courseProgress = teamCourseProgress(studentUserIds);
        int examProgress = teamExamProgress(studentUserIds);
        int materialProgress = teamMaterialProgress(teamId);
        int roadshowProgress = teamRoadshowProgress(teamId);
        int reviewProgress = teamReviewProgress(teamId);

        updateStageRow(teamId, "COURSE", courseProgress);
        updateStageRow(teamId, "EXAM", examProgress);
        updateStageRow(teamId, "MATERIAL", materialProgress);
        updateStageRow(teamId, "ROADSHOW", roadshowProgress);
        updateStageRow(teamId, "REVIEW", reviewProgress);
        syncCurrentStage(teamId);
    }

    private List<Long> studentMemberUserIds(Long teamId) {
        return jdbc.queryForList("""
            SELECT user_id FROM project_team_member
            WHERE team_id = ? AND role_in_team IN ('CAPTAIN', 'MEMBER')
            ORDER BY user_id
            """, Long.class, teamId);
    }

    private void updateStageRow(Long teamId, String stageKey, int progress) {
        Map<String, Object> row = queryOne("""
            SELECT start_date startDate, due_date dueDate
            FROM project_stage WHERE team_id = ? AND stage_key = ?
            """, teamId, stageKey);
        LocalDate startDate = localDateValue(row.get("startDate"));
        LocalDate dueDate = localDateValue(row.get("dueDate"));
        int safe = Math.max(0, Math.min(100, progress));
        jdbc.update("""
            UPDATE project_stage SET progress = ?, status = ?
            WHERE team_id = ? AND stage_key = ?
            """, safe, resolveStageStatus(safe, startDate, dueDate), teamId, stageKey);
    }

    /**
     * 阶段可并行：排期窗口内即视为进行中，不再要求「全局只能一个节点亮」。
     */
    private String resolveStageStatus(int progress, LocalDate startDate, LocalDate dueDate) {
        if (progress >= 100) return "DONE";
        if (progress > 0) return "IN_PROGRESS";
        LocalDate today = LocalDate.now();
        if (startDate != null && today.isBefore(startDate)) return "PENDING";
        if (startDate != null || dueDate != null) return "IN_PROGRESS";
        return "PENDING";
    }

    private int teamCourseProgress(List<Long> userIds) {
        if (userIds.isEmpty()) return 0;
        int sum = 0;
        for (Long userId : userIds) {
            sum += queryInt("SELECT COALESCE(MAX(progress_percent), 0) FROM course_learning_progress WHERE user_id = ?", userId);
        }
        return sum / userIds.size();
    }

    private int teamExamProgress(List<Long> userIds) {
        if (userIds.isEmpty()) return 0;
        int sum = 0;
        for (Long userId : userIds) {
            Integer rate = jdbc.queryForObject("""
                SELECT COALESCE(ROUND(AVG(score / NULLIF(total_score, 0) * 100)), 0)
                FROM exam_attempt WHERE user_id = ? AND status = 'SUBMITTED'
                """, Integer.class, userId);
            sum += rate != null ? rate : 0;
        }
        return sum / userIds.size();
    }

    private int teamMaterialProgress(Long teamId) {
        Map<String, Object> mat = queryOne("""
            SELECT COUNT(*) total,
                   SUM(CASE WHEN review_status = 'APPROVED' THEN 1 ELSE 0 END) approved
            FROM project_material WHERE team_id = ?
            """, teamId);
        int matTotal = intValue(mat.get("total"), 0);
        int matApproved = intValue(mat.get("approved"), 0);
        int matPct = matTotal == 0 ? 0 : (int) Math.round(matApproved * 100.0 / matTotal);

        Map<String, Object> tasks = queryOne("""
            SELECT COUNT(*) total, SUM(CASE WHEN status = 'DONE' THEN 1 ELSE 0 END) done
            FROM project_task WHERE team_id = ? AND stage_key = 'MATERIAL'
            """, teamId);
        int taskTotal = intValue(tasks.get("total"), 0);
        int taskDone = intValue(tasks.get("done"), 0);
        int taskPct = taskTotal == 0 ? 0 : (int) Math.round(taskDone * 100.0 / taskTotal);

        if (matTotal == 0 && taskTotal == 0) return 0;
        if (matTotal == 0) return taskPct;
        if (taskTotal == 0) return matPct;
        return (matPct + taskPct) / 2;
    }

    private int teamRoadshowProgress(Long teamId) {
        Integer bound = jdbc.queryForObject(
                "SELECT COUNT(*) FROM project_roadshow_binding WHERE team_id = ?", Integer.class, teamId);
        if (bound == null || bound == 0) return 0;
        Map<String, Object> rs = roadshow(teamId);
        if ("AI_COMPLETED".equalsIgnoreCase(String.valueOf(rs.get("status")))) {
            return Math.min(100, intValue(rs.get("score"), 0));
        }
        return 30;
    }

    private int teamReviewProgress(Long teamId) {
        Map<String, Object> issues = queryOne("""
            SELECT COUNT(*) total, SUM(CASE WHEN status = 'DONE' THEN 1 ELSE 0 END) closed
            FROM project_review_issue WHERE team_id = ?
            """, teamId);
        int total = intValue(issues.get("total"), 0);
        if (total == 0) return 0;
        return (int) Math.round(intValue(issues.get("closed"), 0) * 100.0 / total);
    }

    /** 团队「当前节点」仅用于 KPI 展示，不限制其它阶段并行进行。 */
    private void syncCurrentStage(Long teamId) {
        List<Map<String, Object>> rows = stages(teamId);
        String fallback = "MATERIAL";
        String latestActiveMain = null;
        for (Map<String, Object> row : rows) {
            if (stageIsOptional(row)) continue;
            String status = String.valueOf(row.get("status")).toUpperCase(Locale.ROOT);
            if ("IN_PROGRESS".equals(status) || "DONE".equals(status)) {
                latestActiveMain = text(row.get("stageKey"), fallback);
            }
        }
        if (latestActiveMain == null) {
            boolean hasBinding = intValue(jdbc.queryForObject(
                    "SELECT COUNT(*) FROM project_roadshow_binding WHERE team_id = ?", Integer.class, teamId), 0) > 0;
            latestActiveMain = hasBinding ? "ROADSHOW" : fallback;
        }
        jdbc.update("UPDATE project_team SET current_stage = ? WHERE id = ?", latestActiveMain, teamId);
    }

    private List<Map<String, Object>> decorateStages(Long teamId, Long userId, String roleInTeam, List<Map<String, Object>> rows) {
        boolean isStudentMember = roleInTeam != null && Set.of("CAPTAIN", "MEMBER").contains(roleInTeam);
        int personalCourse = isStudentMember ? personalCourseProgress(userId) : -1;
        int personalExam = isStudentMember ? personalExamProgress(userId) : -1;
        List<Map<String, Object>> decorated = new ArrayList<>();
        for (Map<String, Object> row : rows) {
            Map<String, Object> copy = new LinkedHashMap<>(row);
            String key = text(row.get("stageKey"), "");
            int teamProgress = intValue(row.get("progress"), 0);
            boolean optional = stageIsOptional(row);
            copy.put("optional", optional);
            String customSuggestion = nullableText(row.get("suggestionText"));
            copy.put("suggestion", customSuggestion != null && !customSuggestion.isBlank()
                    ? customSuggestion
                    : stageSuggestion(key, teamProgress));
            if ("COURSE".equals(key) && personalCourse >= 0) copy.put("personalProgress", personalCourse);
            if ("EXAM".equals(key) && personalExam >= 0) copy.put("personalProgress", personalExam);
            decorated.add(copy);
        }
        return decorated;
    }

    private int personalCourseProgress(Long userId) {
        if (userId == null) return 0;
        return queryInt("SELECT COALESCE(MAX(progress_percent), 0) FROM course_learning_progress WHERE user_id = ?", userId);
    }

    private int personalExamProgress(Long userId) {
        if (userId == null) return 0;
        return queryInt("""
            SELECT COALESCE(ROUND(AVG(score / NULLIF(total_score, 0) * 100)), 0)
            FROM exam_attempt WHERE user_id = ? AND status = 'SUBMITTED'
            """, userId);
    }

    private String stageSuggestion(String stageKey, int teamProgress) {
        return switch (stageKey) {
            case "COURSE" -> teamProgress < 60
                    ? "建议完成推荐课程（可选，不阻断后续节点）"
                    : null;
            case "EXAM" -> teamProgress < 60
                    ? "建议完成能力测评，便于能力画像采样（可选）"
                    : null;
            case "MATERIAL" -> teamProgress < 50
                    ? "主链路：优先补齐并通过审核的项目材料"
                    : null;
            case "ROADSHOW" -> teamProgress == 0
                    ? "主链路：绑定彩排会议并完成 AI 路演评分"
                    : (teamProgress < 100 ? "主链路：可继续彩排提升路演得分" : null);
            case "REVIEW" -> teamProgress > 0 && teamProgress < 100
                    ? "主链路：推进复盘问题闭环"
                    : null;
            default -> null;
        };
    }

    private List<Map<String, Object>> tasks(
            Long teamId,
            Long onlyUserId,
            Long currentUserId,
            String role,
            Long tenantId
    ) {
        List<Map<String, Object>> rows;
        if (onlyUserId == null) {
            rows = jdbc.queryForList(taskSql("WHERE t.team_id = ?"), teamId);
        } else {
            rows = jdbc.queryForList(taskSql("WHERE t.team_id = ? AND (t.owner_user_id = ? OR EXISTS (SELECT 1 FROM project_task_assignee a WHERE a.task_id = t.id AND a.user_id = ?))"), teamId, onlyUserId, onlyUserId);
        }
        for (Map<String, Object> row : rows) {
            attachTaskAssignees(row);
            decorateTaskAccess(row, currentUserId, role);
        }
        return canUseTeacherScope(role)
                ? rows
                : accessibleTasksForStudent(rows, teamId, tenantId);
    }

    private List<Map<String, Object>> accessibleTasksForStudent(
            List<Map<String, Object>> tasks,
            Long teamId,
            Long tenantId
    ) {
        List<Long> taskIds = tasks.stream()
                .map(task -> longValue(task.get("id")))
                .filter(Objects::nonNull)
                .toList();
        if (taskIds.isEmpty()) return tasks;

        String placeholders = String.join(",", taskIds.stream().map(ignored -> "?").toList());
        List<Object> args = new ArrayList<>();
        args.add(tenantId);
        args.add(teamId);
        args.addAll(taskIds);
        List<Map<String, Object>> links = jdbc.queryForList(("""
            SELECT dt.task_id taskId, d.training_date trainingDate, d.status,
                   d.early_unlocked_at earlyUnlockedAt
            FROM training_day_task dt
            JOIN training_day d ON d.id = dt.training_day_id
            JOIN training_camp c ON c.id = d.camp_id AND c.tenant_id = ?
            JOIN training_camp_team ct ON ct.camp_id = c.id
              AND ct.team_id = ? AND ct.status = 'ACTIVE'
            WHERE dt.task_id IN (%s)
            """).formatted(placeholders), args.toArray());

        Set<Long> linkedTaskIds = new HashSet<>();
        Set<Long> accessibleTaskIds = new HashSet<>();
        for (Map<String, Object> link : links) {
            Long taskId = longValue(link.get("taskId"));
            if (taskId == null) continue;
            linkedTaskIds.add(taskId);
            if (!Boolean.TRUE.equals(trainingDayAvailabilityService.availability(link).get("locked"))) {
                accessibleTaskIds.add(taskId);
            }
        }
        return tasks.stream()
                .filter(task -> {
                    Long taskId = longValue(task.get("id"));
                    return !linkedTaskIds.contains(taskId) || accessibleTaskIds.contains(taskId);
                })
                .toList();
    }

    private List<Map<String, Object>> trainingSchedule(Long teamId, Long tenantId) {
        List<Map<String, Object>> camps = jdbc.queryForList("""
            SELECT c.id campId, c.name campName
            FROM training_camp c
            JOIN training_camp_team ct ON ct.camp_id = c.id AND ct.status = 'ACTIVE'
            WHERE ct.team_id = ? AND c.tenant_id = ? AND c.status IN ('PLANNED', 'ACTIVE')
            ORDER BY CASE WHEN ? BETWEEN c.start_date AND c.end_date THEN 0 ELSE 1 END,
                     c.start_date DESC, c.id DESC
            LIMIT 1
            """, teamId, tenantId, trainingDayAvailabilityService.today());
        if (camps.isEmpty()) return List.of();

        Long campId = longValue(camps.get(0).get("campId"));
        List<Map<String, Object>> days = jdbc.queryForList("""
            SELECT d.id dayId, d.day_no dayNo, d.training_date trainingDate,
                   d.title, d.summary, d.due_at dueAt, d.status,
                   d.early_unlocked_at earlyUnlockedAt
            FROM training_day d
            WHERE d.camp_id = ?
            ORDER BY d.sort_order ASC, d.day_no ASC, d.id ASC
            """, campId);
        List<Map<String, Object>> links = jdbc.queryForList("""
            SELECT dt.training_day_id dayId, dt.task_id taskId
            FROM training_day_task dt
            JOIN project_task t ON t.id = dt.task_id
            WHERE training_day_id IN (SELECT id FROM training_day WHERE camp_id = ?)
              AND t.team_id = ?
            ORDER BY dt.training_day_id, dt.is_primary DESC, dt.sort_order, dt.id
            """, campId, teamId);

        Map<Long, List<Long>> taskIdsByDay = new LinkedHashMap<>();
        for (Map<String, Object> link : links) {
            Long dayId = longValue(link.get("dayId"));
            Long taskId = longValue(link.get("taskId"));
            if (dayId != null && taskId != null) {
                taskIdsByDay.computeIfAbsent(dayId, ignored -> new ArrayList<>()).add(taskId);
            }
        }
        for (Map<String, Object> day : days) {
            day.put("taskIds", taskIdsByDay.getOrDefault(longValue(day.get("dayId")), List.of()));
            day.putAll(trainingDayAvailabilityService.availability(day));
            trainingDayAvailabilityService.redactDraftPlaceholder(day);
        }
        return days;
    }

    private List<Long> taskAssigneeIds(Map<String, Object> body, Long ownerId) {
        LinkedHashSet<Long> ids = new LinkedHashSet<>();
        Object raw = body.containsKey("assigneeUserIds") ? body.get("assigneeUserIds") : body.get("ownerUserIds");
        if (raw instanceof Collection<?> collection) {
            for (Object value : collection) {
                Long id = longValue(value);
                if (id != null) ids.add(id);
            }
        } else if (raw instanceof String text) {
            for (String part : text.split(",")) {
                Long id = longValue(part.trim());
                if (id != null) ids.add(id);
            }
        }
        if (ids.isEmpty() && ownerId != null) ids.add(ownerId);
        return new ArrayList<>(ids);
    }

    private void saveTaskAssignees(Long taskId, Long teamId, List<Long> assigneeIds) {
        jdbc.update("DELETE FROM project_task_assignee WHERE task_id = ?", taskId);
        for (int i = 0; i < assigneeIds.size(); i++) {
            jdbc.update("""
                INSERT INTO project_task_assignee (task_id, team_id, user_id, sort_order)
                VALUES (?, ?, ?, ?)
                """, taskId, teamId, assigneeIds.get(i), i);
        }
    }

    private void attachTaskAssignees(Map<String, Object> task) {
        Long taskId = longValue(task.get("id"));
        if (taskId == null) return;
        List<Map<String, Object>> assignees = jdbc.queryForList("""
            SELECT a.user_id userId, u.username, m.position_name positionName, m.role_in_team roleInTeam
            FROM project_task_assignee a
            JOIN users u ON u.id = a.user_id
            LEFT JOIN project_team_member m ON m.team_id = a.team_id AND m.user_id = a.user_id
            WHERE a.task_id = ?
            ORDER BY a.sort_order, a.id
            """, taskId);
        if (assignees.isEmpty() && task.get("ownerUserId") != null) {
            assignees = List.of(Map.of(
                    "userId", task.get("ownerUserId"),
                    "username", String.valueOf(task.getOrDefault("ownerName", ""))
            ));
        }
        task.put("assignees", assignees);
    }

    private void decorateTaskAccess(Map<String, Object> task, Long currentUserId, String role) {
        Long ownerId = longValue(task.get("ownerUserId"));
        boolean owner = ownerId != null && Objects.equals(ownerId, currentUserId);
        Object assignees = task.get("assignees");
        if (!owner && assignees instanceof Collection<?> collection) {
            owner = collection.stream().anyMatch(item -> item instanceof Map<?, ?> map && Objects.equals(longValue(map.get("userId")), currentUserId));
        }
        Long taskId = longValue(task.get("id"));
        Long teamId = longValue(task.get("teamId"));
        // 训练日任务：团队学生均视为可提交（与指派人同步策略一致）
        if (!owner && taskId != null && teamId != null
                && isPublishedTrainingDayTask(taskId)
                && isStudentTeamParticipant(teamId, currentUserId)) {
            owner = true;
        }
        boolean canSubmit = owner;
        String reason = "";
        if (!owner) {
            reason = ownerId == null ? "任务尚未指定负责人" : "只有任务负责人可以提交成果";
        }
        task.put("currentUserIsOwner", owner);
        task.put("currentUserCanSubmit", canSubmit);
        task.put("submitLockedReason", reason);
    }

    private boolean isPublishedTrainingDayTask(Long taskId) {
        if (taskId == null) return false;
        Integer n = jdbc.queryForObject("""
            SELECT COUNT(*)
            FROM training_day_task dt
            JOIN training_day d ON d.id = dt.training_day_id
            WHERE dt.task_id = ? AND d.status = 'PUBLISHED'
            """, Integer.class, taskId);
        return n != null && n > 0;
    }

    private boolean isStudentTeamParticipant(Long teamId, Long userId) {
        if (teamId == null || userId == null) return false;
        Integer n = jdbc.queryForObject("""
            SELECT COUNT(*)
            FROM project_team_member tm
            JOIN users u ON u.id = tm.user_id
            WHERE tm.team_id = ?
              AND tm.user_id = ?
              AND tm.role_in_team IN ('CAPTAIN', 'MEMBER')
              AND u.role = 'STUDENT'
            """, Integer.class, teamId, userId);
        return n != null && n > 0;
    }

    private String taskSql(String where) {
        return """
            SELECT t.id, t.team_id teamId, t.stage_key stageKey, t.title, t.description,
                   t.task_type taskType, t.task_type_label taskTypeLabel, t.time_slot timeSlot,
                   t.owner_user_id ownerUserId, owner.username ownerName, t.created_by createdBy,
                   t.source_type sourceType,t.reviewer_user_id reviewerUserId,
                   creator.username creatorName, t.priority, t.status, t.start_at startAt, t.due_at dueAt,
                   t.review_required reviewRequired,
                   (SELECT COUNT(*) FROM project_task_submission s WHERE s.task_id = t.id) submissionCount,
                   (SELECT id FROM project_task_submission s WHERE s.task_id = t.id ORDER BY s.id DESC LIMIT 1) latestSubmissionId,
                   (SELECT status FROM project_task_submission s WHERE s.task_id = t.id ORDER BY s.id DESC LIMIT 1) latestSubmissionStatus,
                   (SELECT submitter.username FROM project_task_submission s JOIN users submitter ON submitter.id = s.submitter_id WHERE s.task_id = t.id ORDER BY s.id DESC LIMIT 1) latestSubmitterName,
                   (SELECT attachment_url FROM project_task_submission s WHERE s.task_id = t.id ORDER BY s.id DESC LIMIT 1) latestAttachmentUrl,
                   (SELECT attachment_name FROM project_task_submission s WHERE s.task_id = t.id ORDER BY s.id DESC LIMIT 1) latestAttachmentName,
                   (SELECT attachment_size FROM project_task_submission s WHERE s.task_id = t.id ORDER BY s.id DESC LIMIT 1) latestAttachmentSize,
                   (SELECT attachment_type FROM project_task_submission s WHERE s.task_id = t.id ORDER BY s.id DESC LIMIT 1) latestAttachmentType,
                   (SELECT created_at FROM project_task_submission s WHERE s.task_id = t.id ORDER BY s.id DESC LIMIT 1) latestSubmittedAt
            FROM project_task t
            LEFT JOIN users owner ON owner.id = t.owner_user_id
            LEFT JOIN users creator ON creator.id = t.created_by
            """ + where + " ORDER BY FIELD(t.status, 'REVIEWING', 'CHANGES_REQUESTED', 'IN_PROGRESS', 'TODO', 'DONE'), t.due_at, t.id";
    }

    private Map<String, Object> oneTask(Long taskId) {
        Map<String, Object> task = jdbc.queryForList(taskSql("WHERE t.id = ?"), taskId).stream().findFirst()
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "任务不存在"));
        attachTaskAssignees(task);
        return task;
    }

    private List<Map<String, Object>> submissions(Long teamId, Long onlyUserId) {
        List<Map<String, Object>> rows;
        if (onlyUserId == null) {
            rows = jdbc.queryForList(submissionSql("WHERE s.team_id = ?"), teamId);
        } else {
            rows = jdbc.queryForList(submissionSql("WHERE s.team_id = ? AND s.submitter_id = ?"), teamId, onlyUserId);
        }
        attachSubmissionPayloads(rows);
        return rows;
    }

    private String submissionSql(String where) {
        return """
            SELECT s.id, s.task_id taskId, s.team_id teamId, s.submitter_id submitterId,
                   submitter.username submitterName, s.submission_type submissionType, s.content, s.attachment_url attachmentUrl,
                   s.attachment_name attachmentName, s.attachment_size attachmentSize, s.attachment_type attachmentType,
                   s.sync_to_material syncToMaterial, s.version_no versionNo, s.status, s.reviewer_id reviewerId,
                   reviewer.username reviewerName, s.review_comment reviewComment,
                   s.reviewed_at reviewedAt, s.created_at createdAt, t.title taskTitle
            FROM project_task_submission s
            JOIN project_task t ON t.id = s.task_id
            JOIN users submitter ON submitter.id = s.submitter_id
            LEFT JOIN users reviewer ON reviewer.id = s.reviewer_id
            """ + where + " ORDER BY s.created_at DESC";
    }

    private Map<String, Object> oneSubmission(Long submissionId) {
        List<Map<String, Object>> rows = jdbc.queryForList(submissionSql("WHERE s.id = ?"), submissionId);
        attachSubmissionPayloads(rows);
        return rows.stream().findFirst()
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "提交记录不存在"));
    }

    private void attachSubmissionPayloads(List<Map<String, Object>> rows) {
        if (rows.isEmpty()) return;
        List<Long> ids = rows.stream()
                .map(row -> longValue(row.get("id")))
                .filter(Objects::nonNull)
                .toList();
        if (ids.isEmpty()) return;
        Map<Long, List<Map<String, Object>>> assets = new LinkedHashMap<>();
        Map<Long, List<Map<String, Object>>> links = new LinkedHashMap<>();
        String placeholders = ids.stream().map(id -> "?").collect(Collectors.joining(","));
        try {
            List<Map<String, Object>> assetRows = jdbc.queryForList("""
                SELECT id, submission_id submissionId, task_id taskId, team_id teamId,
                       asset_kind assetKind, file_url fileUrl, file_name fileName,
                       file_size fileSize, file_type fileType, sort_order sortOrder, created_at createdAt
                FROM project_submission_asset
                WHERE submission_id IN (""" + placeholders + ") ORDER BY submission_id, sort_order, id", ids.toArray());
            for (Map<String, Object> asset : assetRows) {
                Long submissionId = longValue(asset.get("submissionId"));
                if (submissionId != null) assets.computeIfAbsent(submissionId, key -> new ArrayList<>()).add(asset);
            }
        } catch (Exception ignored) {
        }
        try {
            List<Map<String, Object>> linkRows = jdbc.queryForList("""
                SELECT id, submission_id submissionId, task_id taskId, team_id teamId,
                       link_type linkType, title, url, sort_order sortOrder, created_at createdAt
                FROM project_submission_link
                WHERE submission_id IN (""" + placeholders + ") ORDER BY submission_id, sort_order, id", ids.toArray());
            for (Map<String, Object> link : linkRows) {
                Long submissionId = longValue(link.get("submissionId"));
                if (submissionId != null) links.computeIfAbsent(submissionId, key -> new ArrayList<>()).add(link);
            }
        } catch (Exception ignored) {
        }
        for (Map<String, Object> row : rows) {
            Long id = longValue(row.get("id"));
            List<Map<String, Object>> rowAssets = new ArrayList<>(assets.getOrDefault(id, List.of()));
            String legacyUrl = nullableText(row.get("attachmentUrl"));
            if (legacyUrl != null && rowAssets.stream().noneMatch(asset -> legacyUrl.equals(asset.get("fileUrl")))) {
                Map<String, Object> legacy = new LinkedHashMap<>();
                legacy.put("submissionId", id);
                legacy.put("taskId", row.get("taskId"));
                legacy.put("teamId", row.get("teamId"));
                legacy.put("assetKind", "MAIN");
                legacy.put("fileUrl", legacyUrl);
                legacy.put("fileName", row.get("attachmentName"));
                legacy.put("fileSize", row.get("attachmentSize"));
                legacy.put("fileType", row.get("attachmentType"));
                legacy.put("sortOrder", 0);
                rowAssets.add(0, legacy);
            }
            row.put("assets", rowAssets);
            row.put("links", links.getOrDefault(id, List.of()));
            row.put("assetCount", rowAssets.size());
            row.put("linkCount", links.getOrDefault(id, List.of()).size());
        }
    }

    private List<Map<String, Object>> materials(Long teamId) {
        return jdbc.queryForList("""
            SELECT m.id, m.team_id teamId, m.material_type materialType, m.name, m.description,
                   m.owner_user_id ownerUserId, owner.username ownerName, m.source_type sourceType,
                   m.file_url fileUrl, m.linked_task_id linkedTaskId, m.review_status reviewStatus,
                   m.reviewer_id reviewerId, reviewer.username reviewerName, m.review_comment reviewComment,
                   m.updated_at updatedAt
            FROM project_material m
            LEFT JOIN users owner ON owner.id = m.owner_user_id
            LEFT JOIN users reviewer ON reviewer.id = m.reviewer_id
            WHERE m.team_id = ?
            ORDER BY FIELD(m.material_type, 'PROGRESS', 'DOCS', 'PPT', 'SCRIPT', 'VIDEO', 'CODE'), m.id
            """, teamId);
    }

    private Map<String, Object> oneMaterial(Long materialId) {
        return jdbc.queryForList("""
            SELECT id, team_id teamId, material_type materialType, name, description,
                   owner_user_id ownerUserId, source_type sourceType, file_url fileUrl,
                   linked_task_id linkedTaskId, review_status reviewStatus, review_comment reviewComment
            FROM project_material WHERE id = ?
            """, materialId).stream().findFirst()
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "材料不存在"));
    }

    private Map<String, Object> roadshow(Long teamId) {
        List<Map<String, Object>> bindings = jdbc.queryForList("""
            SELECT b.id, b.meeting_id meetingId, b.roadshow_type roadshowType,
                   m.title meetingTitle, m.status meetingStatus, m.start_time startTime, m.end_time endTime,
                   b.created_at boundAt,
                   ai.id aiReportId, ai.status aiStatus, ai.overall_score aiScore, ai.dimensions_json dimensionsJson,
                   ai.highlights_json highlightsJson, ai.critical_issues_json criticalIssuesJson,
                   ai.improvement_priorities_json improvementPrioritiesJson, ai.speech_quality_json speechQualityJson,
                   ai.transcript transcript, ai.result_path resultPath,
                   (SELECT COALESCE(ROUND(AVG(sr.total_score)), 0) FROM score_record sr WHERE sr.meeting_id = m.id) manualScore
            FROM project_roadshow_binding b
            JOIN meeting m ON m.id = b.meeting_id
            LEFT JOIN ai_score_report ai ON ai.meeting_id = m.id
            WHERE b.team_id = ?
            ORDER BY b.created_at DESC
            LIMIT 1
            """, teamId);
        if (bindings.isEmpty()) {
            return Map.of("score", 0, "status", "NOT_BOUND", "dimensions", List.of(), "summary", "尚未绑定路演会议");
        }
        return decorateRoadshow(bindings.get(0));
    }

    /**
     * Meetings already bound to this team only.
     * Never mix in personal history or tenant-wide admin visibility — that leaked
     * other teams' meetings into a brand-new team's review picker.
     */
    private List<Map<String, Object>> roadshowMeetings(Long teamId) {
        List<Map<String, Object>> rows = jdbc.queryForList("""
            SELECT m.id meetingId, m.title meetingTitle, m.status meetingStatus,
                   m.creator_id creatorId, creator.username creatorName,
                   m.start_time startTime, m.end_time endTime, m.created_at createdAt,
                   b.id bindingId, b.roadshow_type roadshowType, b.created_at boundAt,
                   1 boundToTeam,
                   ai.id aiReportId, ai.status aiStatus, ai.overall_score aiScore, ai.dimensions_json dimensionsJson,
                   ai.highlights_json highlightsJson, ai.critical_issues_json criticalIssuesJson,
                   ai.improvement_priorities_json improvementPrioritiesJson, ai.speech_quality_json speechQualityJson,
                   ai.transcript transcript, ai.result_path resultPath,
                   (SELECT COALESCE(ROUND(AVG(sr.total_score)), 0) FROM score_record sr WHERE sr.meeting_id = m.id) manualScore
            FROM project_roadshow_binding b
            JOIN meeting m ON m.id = b.meeting_id
            LEFT JOIN users creator ON creator.id = m.creator_id
            LEFT JOIN ai_score_report ai ON ai.meeting_id = m.id
            WHERE b.team_id = ?
            ORDER BY COALESCE(b.created_at, m.end_time, m.start_time, m.created_at) DESC
            LIMIT 50
            """, teamId);
        return rows.stream().map(this::decorateRoadshow).toList();
    }

    /**
     * Personal / accessible meetings that can be bound to this team, excluding
     * meetings already bound here. Used only by the bind UI, never as the team
     * review history list.
     */
    private List<Map<String, Object>> bindableRoadshowMeetings(
            Long teamId, Long tenantId, Long userId, String role
    ) {
        boolean adminScope = isAdministrator(role);
        List<Map<String, Object>> rows = jdbc.queryForList("""
            SELECT DISTINCT m.id meetingId, m.title meetingTitle, m.status meetingStatus,
                   m.creator_id creatorId, creator.username creatorName,
                   m.start_time startTime, m.end_time endTime, m.created_at createdAt,
                   CASE WHEN m.creator_id = ? THEN 1 ELSE 0 END createdByMe,
                   CASE WHEN mp.user_id IS NOT NULL THEN 1 ELSE 0 END participated,
                   ai.id aiReportId, ai.status aiStatus, ai.overall_score aiScore,
                   (SELECT COALESCE(ROUND(AVG(sr.total_score)), 0) FROM score_record sr WHERE sr.meeting_id = m.id) manualScore
            FROM meeting m
            LEFT JOIN users creator ON creator.id = m.creator_id
            LEFT JOIN meeting_participant mp ON mp.meeting_id = m.id AND mp.user_id = ?
            LEFT JOIN ai_score_report ai ON ai.meeting_id = m.id
            WHERE m.tenant_id = ?
              AND NOT EXISTS (
                    SELECT 1 FROM project_roadshow_binding b
                    WHERE b.team_id = ? AND b.meeting_id = m.id
              )
              AND (
                    m.creator_id = ?
                    OR mp.user_id IS NOT NULL
                    OR ? = 1
              )
            ORDER BY COALESCE(m.end_time, m.start_time, m.created_at) DESC
            LIMIT 50
            """, userId, userId, tenantId, teamId, userId, adminScope ? 1 : 0);
        return rows.stream().map(row -> {
            Map<String, Object> item = new LinkedHashMap<>(row);
            item.put("boundToTeam", 0);
            item.put("status", "BINDABLE");
            item.put("summary", "可绑定到本团队的会议，绑定后才会出现在团队复盘列表");
            return item;
        }).toList();
    }

    private Map<String, Object> decorateRoadshow(Map<String, Object> source) {
        Map<String, Object> row = new LinkedHashMap<>(source);
        Long meetingId = longValue(row.get("meetingId"));
        boolean aiCompleted = "completed".equalsIgnoreCase(String.valueOf(row.get("aiStatus")));
        if (aiCompleted) {
            List<Map<String, Object>> highlights = insightCards(row.get("highlightsJson"), "亮点", "LOW");
            List<Map<String, Object>> criticalIssues = insightCards(row.get("criticalIssuesJson"), "关键问题", "HIGH");
            List<Map<String, Object>> improvementPriorities = insightCards(row.get("improvementPrioritiesJson"), "提升建议", "MEDIUM");
            Map<String, Object> speechQuality = parseJsonMap(row.get("speechQualityJson"));
            row.put("score", intValue(row.get("aiScore"), 0));
            row.put("status", "AI_COMPLETED");
            row.put("scoreSource", "AI");
            row.put("dimensions", aiDimensions(row.get("dimensionsJson")));
            row.put("highlights", highlights);
            row.put("criticalIssues", criticalIssues);
            row.put("improvementPriorities", improvementPriorities);
            row.put("speechQuality", speechQuality);
            row.put("scoreCalibration", parseJsonMap(row.get("scoreCalibrationJson")));
            row.put("evidenceAnchors", roadshowEvidenceAnchors(row, highlights, criticalIssues, speechQuality));
            row.put("summary", "已同步会议室 AI 评分，可用于复盘和能力画像");
            return row;
        }
        int manualScore = intValue(row.get("manualScore"), 0);
        row.put("score", manualScore);
        row.put("status", manualScore > 0 ? "MANUAL_SCORE" : "WAITING_SCORE");
        row.put("scoreSource", manualScore > 0 ? "评委" : "等待评分");
        row.put("dimensions", manualScore > 0 && meetingId != null ? scoreDimensionsFromManual(meetingId) : List.of());
        row.put("highlights", List.of());
        row.put("criticalIssues", List.of());
        row.put("improvementPriorities", manualScore > 0 ? manualImprovementPriorities(meetingId) : List.of());
        row.put("speechQuality", Map.of());
        row.put("scoreCalibration", Map.of());
        row.put("evidenceAnchors", List.of());
        row.put("summary", manualScore > 0 ? "已同步评委评分，建议结合评语继续复盘" : "该会议暂未生成 AI 或评委评分");
        return row;
    }

    private List<Map<String, Object>> roadshowEvidenceAnchors(
            Map<String, Object> row,
            List<Map<String, Object>> highlights,
            List<Map<String, Object>> criticalIssues,
            Map<String, Object> speechQuality
    ) {
        Path resolvedResultPath = resolveAiResultPath(row.get("resultPath"));
        Long meetingId = longValue(row.get("meetingId"));
        Long aiReportId = longValue(row.get("aiReportId"));
        List<Map<String, Object>> recordingAnchors = recordingEvidenceAnchors(meetingId);
        List<Map<String, Object>> precise = new ArrayList<>(evidenceAnchorExtractor.extract(resolvedResultPath, meetingId, aiReportId));
        precise.addAll(recordingAnchors);
        Long teamId = longValue(row.get("teamId"));
        if (!precise.isEmpty()) {
            return scoreEvidenceAnchorStore.syncRoundAnchors(teamId, row, precise.stream().limit(24).toList());
        }

        List<Map<String, Object>> anchors = new ArrayList<>();
        int index = 1;
        for (Map<String, Object> issue : criticalIssues) {
            anchors.add(evidenceAnchor(
                    "ai_issue",
                    text(issue.get("title"), "关键问题") + "：" + text(issue.get("description"), text(issue.get("evidence"), "")),
                    "ai_report:" + aiReportId + ":critical_issue:" + index++,
                    meetingId,
                    aiReportId
            ));
        }
        index = 1;
        for (Map<String, Object> highlight : highlights) {
            anchors.add(evidenceAnchor(
                    "ai_highlight",
                    text(highlight.get("title"), "亮点") + "：" + text(highlight.get("description"), text(highlight.get("evidence"), "")),
                    "ai_report:" + aiReportId + ":highlight:" + index++,
                    meetingId,
                    aiReportId
            ));
        }
        String transcript = nullableText(row.get("transcript"));
        if (transcript != null) {
            anchors.add(evidenceAnchor(
                    "transcript",
                    shortText(transcript, 180),
                    "meeting:" + meetingId + ":transcript",
                    meetingId,
                    aiReportId
            ));
        }
        if (!speechQuality.isEmpty()) {
            anchors.add(evidenceAnchor(
                    "speech_quality",
                    "语音质量分析已生成，可用于核查语速、停顿、表达稳定性等表现。",
                    "ai_report:" + aiReportId + ":speech_quality",
                    meetingId,
                    aiReportId
            ));
        }
        String resultPath = nullableText(row.get("resultPath"));
        if (resultPath != null) {
            anchors.add(evidenceAnchor(
                    "ai_result_file",
                    "AI 原始评分结果文件已归档，可追溯视频分析、融合分析和评分输入。",
                    resultPath,
                    meetingId,
                aiReportId
            ));
        }
        anchors.addAll(recordingAnchors);
        return scoreEvidenceAnchorStore.syncRoundAnchors(teamId, row, anchors.stream().limit(12).toList());
    }

    private List<Map<String, Object>> recordingEvidenceAnchors(Long meetingId) {
        if (meetingId == null) return List.of();
        try {
            List<Map<String, Object>> recordings = jdbc.queryForList("""
                SELECT id, meeting_id meetingId, status, file_path filePath, camera_file cameraFile,
                       screen_file screenFile, audio_file audioFile, duration_seconds durationSeconds
                FROM meeting_recording
                WHERE meeting_id = ? AND status = 'READY'
                ORDER BY COALESCE(recorded_at, ended_at, started_at) DESC, id DESC
                LIMIT 3
                """, meetingId);
            return recordingEvidenceAnchorBuilder.build(recordings);
        } catch (Exception ignored) {
            return List.of();
        }
    }

    private Path resolveAiResultPath(Object value) {
        String text = nullableText(value);
        if (text == null) return null;
        try {
            Path direct = Paths.get(text);
            if (direct.isAbsolute() && Files.isRegularFile(direct)) return direct;
            Path uploadsRoot = legacyAiResultDir().getParent();
            Path uploadRelative = uploadsRoot.resolve(text).normalize();
            if (Files.isRegularFile(uploadRelative)) return uploadRelative;
            Path resultRelative = legacyAiResultDir().resolve(text).normalize();
            if (Files.isRegularFile(resultRelative)) return resultRelative;
        } catch (Exception ignored) {
        }
        return null;
    }

    private Map<String, Object> evidenceAnchor(String type, String summary, String sourceRef, Long meetingId, Long aiReportId) {
        Map<String, Object> anchor = new LinkedHashMap<>();
        anchor.put("type", type);
        anchor.put("summary", summary == null || summary.isBlank() ? "可回看该轮会议证据复核。" : summary);
        anchor.put("sourceRef", sourceRef == null ? "" : sourceRef);
        anchor.put("meetingId", meetingId == null ? "" : meetingId);
        anchor.put("aiReportId", aiReportId == null ? "" : aiReportId);
        return anchor;
    }

    private List<Map<String, Object>> manualImprovementPriorities(Long meetingId) {
        if (meetingId == null) return List.of();
        return jdbc.queryForList("""
            SELECT si.category category, si.name title, sd.comment description,
                   CASE WHEN sd.score / NULLIF(si.max_score, 0) < 0.6 THEN 'HIGH' ELSE 'MEDIUM' END severity
            FROM score_record sr
            JOIN score_detail sd ON sd.record_id = sr.id
            JOIN score_item si ON si.id = sd.item_id
            WHERE sr.meeting_id = ? AND sd.comment IS NOT NULL AND sd.comment <> ''
            ORDER BY sd.score / NULLIF(si.max_score, 0), sd.id
            LIMIT 6
            """, meetingId);
    }

    private List<Map<String, Object>> scoreDimensionsFromManual(Long meetingId) {
        return jdbc.queryForList("""
            SELECT si.category name, ROUND(SUM(sd.score)) score, ROUND(SUM(si.max_score)) maxScore,
                   ROUND(SUM(sd.score) / NULLIF(SUM(si.max_score), 0) * 100) percent
            FROM score_record sr
            JOIN score_detail sd ON sd.record_id = sr.id
            JOIN score_item si ON si.id = sd.item_id
            WHERE sr.meeting_id = ?
            GROUP BY si.category
            """, meetingId);
    }

    private void syncAiReviewIssues(Long teamId) {
        List<Map<String, Object>> reports = jdbc.queryForList("""
            SELECT ai.id reportId, ai.meeting_id meetingId, m.title meetingTitle,
                   ai.critical_issues_json criticalIssuesJson,
                   ai.improvement_priorities_json improvementPrioritiesJson
            FROM project_roadshow_binding b
            JOIN meeting m ON m.id = b.meeting_id
            JOIN ai_score_report ai ON ai.meeting_id = b.meeting_id
            WHERE b.team_id = ? AND ai.status = 'completed'
            ORDER BY ai.completed_at DESC, ai.id DESC
            """, teamId);
        for (Map<String, Object> report : reports) {
            Long reportId = longValue(report.get("reportId"));
            syncAiIssueList(teamId, reportId, report.get("criticalIssuesJson"), "AI 关键问题", "HIGH", "OPEN");
            syncAiIssueList(teamId, reportId, report.get("improvementPrioritiesJson"), "AI 提升建议", "MEDIUM", "IN_PROGRESS");
        }
    }

    private void syncAiIssueList(Long teamId, Long reportId, Object json, String category, String severity, String status) {
        for (Map<String, Object> item : insightCards(json, category, severity)) {
            String title = text(item.get("title"), category);
            String description = text(item.get("description"), "");
            Integer exists = jdbc.queryForObject("""
                SELECT COUNT(*) FROM project_review_issue
                WHERE team_id = ? AND source_type = 'AI_SCORE' AND source_id = ? AND title = ?
                """, Integer.class, teamId, reportId, title);
            if (exists != null && exists > 0) continue;
            jdbc.update("""
                INSERT INTO project_review_issue
                (team_id, source_type, source_id, category, title, description, severity, status, evidence)
                VALUES (?, 'AI_SCORE', ?, ?, ?, ?, ?, ?, ?)
                """, teamId, reportId, text(item.get("category"), category), title, description,
                    text(item.get("severity"), severity), status, text(item.get("evidence"), "来自会议室 AI 评分报告"));
        }
    }

    private List<Map<String, Object>> insightCards(Object json, String fallbackCategory, String fallbackSeverity) {
        List<Object> raw = normalizeJsonList(json);
        List<Map<String, Object>> cards = new ArrayList<>();
        for (Object object : raw) {
            Map<String, Object> map = object instanceof Map<?, ?> rawMap
                    ? rawMap.entrySet().stream().collect(Collectors.toMap(e -> String.valueOf(e.getKey()), Map.Entry::getValue))
                    : Map.of("title", shortText(String.valueOf(object), 36), "description", String.valueOf(object));
            String title = firstText(map, "title", "issue", "problem", "name", "dimension", "category");
            String description = firstText(map, "description", "detail", "summary", "suggestion", "action", "reason", "content");
            if (title == null || title.isBlank()) title = shortText(description, 36);
            if (description == null || description.isBlank()) description = String.valueOf(object);
            Map<String, Object> card = new LinkedHashMap<>();
            card.put("category", text(map.get("category"), fallbackCategory));
            card.put("title", title);
            card.put("description", description);
            card.put("severity", text(map.get("severity"), fallbackSeverity).toUpperCase(Locale.ROOT));
            card.put("evidence", text(map.get("evidence"), "来自会议室 AI 评分报告"));
            cards.add(card);
        }
        return cards;
    }

    private String firstText(Map<String, Object> map, String... keys) {
        for (String key : keys) {
            String value = nullableText(map.get(key));
            if (value != null) return value;
        }
        return null;
    }

    private Object firstValue(Map<String, Object> map, String... keys) {
        for (String key : keys) {
            if (map.containsKey(key) && nullableText(map.get(key)) != null) return map.get(key);
        }
        return null;
    }

    private String shortText(String value, int maxLength) {
        String text = value == null ? "" : value.trim();
        if (text.length() <= maxLength) return text;
        return text.substring(0, maxLength) + "...";
    }

    private List<Map<String, Object>> reviewIssues(Long teamId, Long onlyUserId) {
        if (onlyUserId == null) {
            return jdbc.queryForList(reviewSql("WHERE i.team_id = ?"), teamId);
        }
        return jdbc.queryForList(reviewSql("WHERE i.team_id = ? AND (i.owner_user_id = ? OR i.owner_user_id IS NULL)"), teamId, onlyUserId);
    }

    private String reviewSql(String where) {
        return """
            SELECT i.id, i.team_id teamId, i.source_type sourceType, i.category, i.title, i.description,
                   i.severity, i.owner_user_id ownerUserId, u.username ownerName, i.due_at dueAt,
                   i.status, i.evidence, i.updated_at updatedAt
            FROM project_review_issue i
            LEFT JOIN users u ON u.id = i.owner_user_id
            """ + where + " ORDER BY FIELD(i.status, 'OPEN', 'IN_PROGRESS', 'DONE'), FIELD(i.severity, 'HIGH', 'MEDIUM', 'LOW'), i.id DESC";
    }

    private List<Map<String, Object>> abilities(Long teamId) {
        List<Map<String, Object>> rows = jdbc.queryForList("""
            SELECT s.team_id teamId, s.user_id userId, u.username, m.role_in_team roleInTeam,
                   s.problem_solving problemSolving, s.coding, s.communication, s.teamwork,
                   s.presentation, s.creativity, s.confidence, s.calculated_at calculatedAt
            FROM member_ability_snapshot s
            JOIN users u ON u.id = s.user_id
            LEFT JOIN project_team_member m ON m.team_id = s.team_id AND m.user_id = s.user_id
            WHERE s.team_id = ?
            ORDER BY FIELD(m.role_in_team, 'CAPTAIN', 'MEMBER', 'MENTOR'), u.id
            """, teamId);
        for (Map<String, Object> row : rows) {
            Long userId = longValue(row.get("userId"));
            List<Map<String, Object>> evidence = jdbc.queryForList("""
                SELECT dimension_key dimensionKey, source_type sourceType, source_id sourceId,
                       score, weight, summary, created_at createdAt
                FROM member_ability_evidence
                WHERE team_id = ? AND user_id = ?
                ORDER BY dimension_key, created_at DESC
                """, teamId, userId);
            row.put("evidence", evidence);

            // 标记每个维度是否有“真实证据”（非基础占位分且计入权重）——前端据此区分真实分 vs 待采样占位分
            Map<String, Boolean> dimensionSampled = new LinkedHashMap<>();
            for (String key : ABILITY_DIMENSIONS) {
                dimensionSampled.put(key, false);
            }
            for (Map<String, Object> item : evidence) {
                String dim = text(item.get("dimensionKey"), "");
                String sourceType = text(item.get("sourceType"), "");
                int weight = intValue(item.get("weight"), 0);
                if (!"BASELINE".equals(sourceType) && weight > 0 && dimensionSampled.containsKey(dim)) {
                    dimensionSampled.put(dim, true);
                }
            }
            row.put("dimensionSampled", dimensionSampled);
            row.put("sampledDimensionCount", dimensionSampled.values().stream().filter(Boolean::booleanValue).count());
        }
        return rows;
    }

    private Map<String, Object> metrics(Long teamId) {
        List<Map<String, Object>> stageRows = stages(teamId);
        int progress = stageRows.isEmpty() ? 0 : (int) Math.round(stageRows.stream()
                .filter(s -> !stageIsOptional(s))
                .mapToInt(s -> intValue(s.get("progress"), 0))
                .average()
                .orElse(0));
        Integer taskCount = jdbc.queryForObject("SELECT COUNT(*) FROM project_task WHERE team_id = ?", Integer.class, teamId);
        Integer pendingReviews = jdbc.queryForObject("SELECT COUNT(*) FROM project_task_submission WHERE team_id = ? AND status = 'PENDING_REVIEW'", Integer.class, teamId);
        Integer openIssues = jdbc.queryForObject("SELECT COUNT(*) FROM project_review_issue WHERE team_id = ? AND status <> 'DONE'", Integer.class, teamId);
        Map<String, Object> roadshow = roadshow(teamId);
        return Map.of(
                "overallProgress", progress,
                "taskCount", taskCount != null ? taskCount : 0,
                "pendingReviews", pendingReviews != null ? pendingReviews : 0,
                "openIssues", openIssues != null ? openIssues : 0,
                "roadshowScore", roadshow.getOrDefault("score", 0)
        );
    }

    private Map<String, Object> teacherObservation(Long teamId) {
        Map<String, Object> metrics = metrics(teamId);
        Map<String, Object> roadshow = roadshow(teamId);
        int progress = intValue(metrics.get("overallProgress"), 0);
        int pendingReviews = intValue(metrics.get("pendingReviews"), 0);
        int openIssues = intValue(metrics.get("openIssues"), 0);
        int roadshowScore = intValue(roadshow.get("score"), 0);
        int issuePenalty = Math.min(25, openIssues * 5);
        int reviewPenalty = Math.min(18, pendingReviews * 4);
        int readiness = Math.max(0, Math.min(100, Math.round(progress * 0.45f + roadshowScore * 0.35f + 20) - issuePenalty - reviewPenalty));
        String level = readiness >= 82 && openIssues == 0 ? "READY" : readiness >= 62 ? "WATCH" : "RISK";
        List<Map<String, Object>> highRisks = jdbc.queryForList("""
            SELECT id, title, severity, status FROM project_review_issue
            WHERE team_id = ? AND status <> 'DONE'
            ORDER BY FIELD(severity, 'HIGH', 'MEDIUM', 'LOW'), id DESC
            LIMIT 5
            """, teamId);
        List<String> focusAreas = new ArrayList<>();
        if (roadshowScore == 0) focusAreas.add("尚未形成有效路演评分证据，建议先绑定一次彩排会议。");
        if (pendingReviews > 0) focusAreas.add("存在待审核交付，教师可优先检查材料是否支撑路演表达。");
        if (openIssues > 0) focusAreas.add("复盘问题尚未闭环，需要队长提交修改证明或安排专项训练。");
        if (focusAreas.isEmpty()) focusAreas.add("主要风险已收敛，可把指导重点放到表达节奏和答辩预案。");
        List<String> actions = new ArrayList<>();
        if (roadshowScore == 0) actions.add("要求队长绑定彩排会议并生成 AI 评分。");
        if (pendingReviews > 0) actions.add("集中审核待提交材料，退回时写明可验证的修改标准。");
        if (openIssues > 0) actions.add("挑选高风险问题开一次 10 分钟复盘会。");
        if (actions.isEmpty()) actions.add("安排正式路演前的最终演练和问答抽查。");
        Map<String, Object> observation = new LinkedHashMap<>();
        observation.put("visibility", "TEACHER_ONLY");
        observation.put("summary", "判断团队是否具备进入正式路演的教学观察面板。");
        observation.put("readinessScore", readiness);
        observation.put("readinessLevel", level);
        observation.put("overallProgress", progress);
        observation.put("pendingReviews", pendingReviews);
        observation.put("openIssues", openIssues);
        observation.put("roadshowScore", roadshowScore);
        observation.put("highRisks", highRisks);
        observation.put("roadshowSpeakers", roadshowSpeakerAlignment(teamId));
        observation.put("focusAreas", focusAreas);
        observation.put("actions", actions);
        observation.put("intervention", switch (level) {
            case "READY" -> "具备进入正式路演的基础条件，建议做最终答辩压力测试。";
            case "WATCH" -> "准备度中等，需要盯住材料审核、复盘闭环和表达证据。";
            default -> "存在明显准备风险，建议先完成彩排评分和高风险问题闭环。";
        });
        return observation;
    }

    /** 能力画像最长容忍的“读时陈旧”窗口（分钟）。事件触发会即时置脏，此 TTL 仅作为课程/测评等外部数据的兜底刷新。 */
    private static final int ABILITY_REFRESH_TTL_MINUTES = 30;

    /**
     * 判断是否需要重算能力快照：脏标记（synced_at 为 NULL）、新成员尚无快照、或超过 TTL 兜底窗口。
     * 用于把“每次读都全员重算”改为“事件触发 + 兜底”，降低读路径上的写压力。
     */
    private boolean abilityNeedsRefresh(Long teamId) {
        Integer needs = jdbc.queryForObject("""
            SELECT CASE
                WHEN t.ability_synced_at IS NULL THEN 1
                WHEN t.ability_synced_at < (NOW() - INTERVAL ? MINUTE) THEN 1
                WHEN (SELECT COUNT(*) FROM project_team_member m WHERE m.team_id = t.id)
                     > (SELECT COUNT(*) FROM member_ability_snapshot s WHERE s.team_id = t.id) THEN 1
                ELSE 0 END
            FROM project_team t WHERE t.id = ?
            """, Integer.class, ABILITY_REFRESH_TTL_MINUTES, teamId);
        return needs == null || needs == 1;
    }

    /** 将团队能力画像置脏，下一次读取时会触发重算（事件触发入口）。 */
    private void markAbilityDirty(Long teamId) {
        if (teamId == null) return;
        jdbc.update("UPDATE project_team SET ability_synced_at = NULL WHERE id = ?", teamId);
    }

    /** AI 评分回调等以会议为入口的事件：把绑定该会议的团队能力画像置脏。 */
    public void markAbilityDirtyByMeeting(Long meetingId) {
        if (meetingId == null) return;
        jdbc.update("""
            UPDATE project_team SET ability_synced_at = NULL
            WHERE id IN (SELECT team_id FROM project_roadshow_binding WHERE meeting_id = ?)
            """, meetingId);
    }

    /**
     * 内部评分服务拉花名册。调用方必须先校验内部 token，不能对浏览器开放。
     */
    public List<Map<String, Object>> roadshowTeamRoster(Long meetingId) {
        return loadRoadshowTeamRoster(meetingId);
    }

    /**
     * 登录用户拉花名册：会议创建人/参会人，或绑定队成员/本租户教师。
     * 无权限时返回空列表，不泄露他队花名册。
     */
    public List<Map<String, Object>> roadshowTeamRoster(Long meetingId, Long tenantId, Long userId, String role) {
        if (userId == null) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "请先登录");
        }
        List<Long> teamIds = boundRoadshowTeamIds(meetingId);
        if (teamIds.isEmpty()) {
            return List.of();
        }
        Long teamId = teamIds.get(0);
        if (!canViewRoadshowRoster(meetingId, teamId, tenantId, userId, role)) {
            return List.of();
        }
        return loadRoadshowTeamRoster(meetingId);
    }

    private List<Long> boundRoadshowTeamIds(Long meetingId) {
        if (meetingId == null) {
            return List.of();
        }
        return jdbc.queryForList(
                "SELECT team_id FROM project_roadshow_binding WHERE meeting_id = ?", Long.class, meetingId);
    }

    private boolean canViewRoadshowRoster(Long meetingId, Long teamId, Long tenantId, Long userId, String role) {
        Integer participant = jdbc.queryForObject("""
                SELECT COUNT(1)
                FROM meeting m
                LEFT JOIN meeting_participant mp
                    ON mp.meeting_id = m.id AND mp.user_id = ?
                WHERE m.id = ? AND (m.creator_id = ? OR mp.user_id = ?)
                """, Integer.class, userId, meetingId, userId, userId);
        if (participant != null && participant > 0) {
            return true;
        }
        try {
            assertTeamAccess(teamId, tenantId, userId, role);
            return true;
        } catch (ResponseStatusException ignored) {
            return false;
        }
    }

    private List<Map<String, Object>> loadRoadshowTeamRoster(Long meetingId) {
        List<Long> teamIds = boundRoadshowTeamIds(meetingId);
        if (teamIds.isEmpty()) return List.of();
        Long teamId = teamIds.get(0);
        List<Map<String, Object>> roster = new ArrayList<>();
        for (Map<String, Object> member : members(teamId)) {
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("userId", member.get("userId"));
            row.put("username", member.get("username"));
            row.put("positionName", member.get("positionName"));
            row.put("responsibility", member.get("responsibility"));
            row.put("roleInTeam", member.get("roleInTeam"));
            roster.add(row);
        }
        return roster;
    }

    /**
     * 写入旧回调通道的发言人证据。此处只保存身份、时长、原话与时间段，
     * 不接收第二套发言人分数；人工（教师）确认结果继续受到保护。
     */
    public void ingestRoadshowSpeakers(Long meetingId, List<Map<String, Object>> speakers) {
        if (meetingId == null || speakers == null || speakers.isEmpty()) return;
        List<Long> teamIds = jdbc.queryForList(
                "SELECT team_id FROM project_roadshow_binding WHERE meeting_id = ?", Long.class, meetingId);
        if (teamIds.isEmpty()) return;
        for (Long teamId : teamIds) {
            int index = 0;
            for (Map<String, Object> speaker : speakers) {
                if (speaker == null) continue;
                index++;
                String label = text(firstNonBlank(speaker.get("speakerLabel"), speaker.get("speaker"), speaker.get("label")),
                        "S" + index);
                jdbc.update("""
                    INSERT INTO roadshow_speaker_score
                    (meeting_id, team_id, speaker_label, claimed_role, normalized_role, matched_name,
                     match_confidence, duration_sec, evidence_quotes_json, segments_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON DUPLICATE KEY UPDATE
                      claimed_role = VALUES(claimed_role),
                      normalized_role = VALUES(normalized_role),
                      matched_name = VALUES(matched_name),
                      match_confidence = VALUES(match_confidence),
                      duration_sec = VALUES(duration_sec),
                      evidence_quotes_json = VALUES(evidence_quotes_json),
                      segments_json = VALUES(segments_json),
                      updated_at = NOW()
                    """,
                        meetingId,
                        teamId,
                        label,
                        nullableText(firstNonBlank(speaker.get("claimedRole"), speaker.get("role"))),
                        nullableText(speaker.get("normalizedRole")),
                        nullableText(firstNonBlank(speaker.get("matchedName"), speaker.get("name"))),
                        decimalValue(speaker.get("confidence")),
                        intValue(firstNonBlank(speaker.get("durationSec"), speaker.get("duration")), 0),
                        jsonString(firstNonBlank(speaker.get("evidenceQuotes"), speaker.get("quotes"))),
                        jsonString(speaker.get("segments"))
                );
            }
            alignTeamMeetingSpeakers(teamId, meetingId);
        }
    }

    private Long teamTenantId(Long teamId) {
        try {
            return jdbc.queryForObject("SELECT tenant_id FROM project_team WHERE id = ?", Long.class, teamId);
        } catch (Exception e) {
            return null;
        }
    }

    private Map<String, String> roleAliasMap(Long tenantId) {
        Map<String, String> map = new LinkedHashMap<>();
        if (tenantId == null) return map;
        for (Map<String, Object> a : jdbc.queryForList(
                "SELECT alias, canonical_role canonical FROM project_role_alias WHERE tenant_id = ?", tenantId)) {
            String alias = text(a.get("alias"), "");
            String canonical = text(a.get("canonical"), "");
            if (!alias.isBlank() && !canonical.isBlank()) map.put(alias, canonical);
        }
        return map;
    }

    /** 把一段自报岗位/职位文本归一到标准岗位名：先精确别名，再最长子串别名，最后返回清洗后的原文。 */
    private String normalizeRole(Map<String, String> aliasMap, String raw) {
        if (raw == null) return null;
        String clean = raw.trim().replaceAll("^(我是|我叫|我负责|我担任|担任|负责|本人|我)", "").trim();
        if (clean.isEmpty()) return null;
        for (Map.Entry<String, String> entry : aliasMap.entrySet()) {
            if (entry.getKey().equalsIgnoreCase(clean)) return entry.getValue();
        }
        String best = null;
        int bestLen = 0;
        for (Map.Entry<String, String> entry : aliasMap.entrySet()) {
            String alias = entry.getKey();
            if (alias.length() > bestLen && clean.toLowerCase(Locale.ROOT).contains(alias.toLowerCase(Locale.ROOT))) {
                best = entry.getValue();
                bestLen = alias.length();
            }
        }
        return best != null ? best : clean;
    }

    /** 对齐一个会议下绑定团队的发言人；仅处理 status='AUTO' 行，保留教师确认(CONFIRMED)/否决(REJECTED)。 */
    private void alignTeamMeetingSpeakers(Long teamId, Long meetingId) {
        if (teamId == null || meetingId == null) return;
        Long tenantId = teamTenantId(teamId);
        Map<String, String> aliasMap = roleAliasMap(tenantId);
        List<Map<String, Object>> members = members(teamId);
        List<Map<String, Object>> speakers = jdbc.queryForList("""
            SELECT id, claimed_role claimedRole, normalized_role normalizedRole, matched_name matchedName,
                   match_confidence matchConfidence
            FROM roadshow_speaker_score
            WHERE meeting_id = ? AND team_id = ? AND status = 'AUTO'
            """, meetingId, teamId);
        for (Map<String, Object> sp : speakers) {
            Long rowId = longValue(sp.get("id"));
            Long matchedUserId = null;
            String method = "NONE";
            String roleName = null;
            BigDecimal confidence = null;

            // 1) 自报姓名唯一命中（最高可信）
            final String name = text(sp.get("matchedName"), "").trim();
            if (!name.isEmpty()) {
                List<Map<String, Object>> byName = members.stream()
                        .filter(m -> name.equalsIgnoreCase(text(m.get("username"), "")))
                        .toList();
                if (byName.size() == 1) {
                    matchedUserId = longValue(byName.get(0).get("userId"));
                    roleName = text(byName.get(0).get("positionName"), null);
                    method = "NAME";
                    confidence = new BigDecimal("0.95");
                }
            }

            // 2) 岗位归一后唯一命中；同岗多人或无命中 → 留待确认（matched_user_id 置空）
            if (matchedUserId == null) {
                final String canonical = normalizeRole(aliasMap,
                        text(firstNonBlank(sp.get("normalizedRole"), sp.get("claimedRole")), null));
                if (canonical != null) {
                    List<Map<String, Object>> byRole = members.stream()
                            .filter(m -> {
                                String pos = normalizeRole(aliasMap, text(m.get("positionName"), ""));
                                return pos != null && pos.equalsIgnoreCase(canonical);
                            })
                            .toList();
                    if (byRole.size() == 1) {
                        matchedUserId = longValue(byRole.get(0).get("userId"));
                        roleName = text(byRole.get(0).get("positionName"), null);
                        method = "ROLE_ALIGN";
                        BigDecimal spConf = sp.get("matchConfidence") != null ? decimalValue(sp.get("matchConfidence")) : null;
                        confidence = spConf != null ? spConf : new BigDecimal("0.80");
                    }
                }
            }

            jdbc.update("""
                UPDATE roadshow_speaker_score
                SET matched_user_id = ?, matched_role_name = ?, match_method = ?,
                    match_confidence = COALESCE(?, match_confidence)
                WHERE id = ? AND status = 'AUTO'
                """, matchedUserId, roleName, method, confidence, rowId);
        }
    }

    /** 团队成员/岗位变更后，重新对齐该团队所有路演会议的自动发言人匹配。 */
    private void realignTeamRoadshows(Long teamId) {
        for (Long meetingId : jdbc.queryForList(
                "SELECT meeting_id FROM project_roadshow_binding WHERE team_id = ?", Long.class, teamId)) {
            alignTeamMeetingSpeakers(teamId, meetingId);
        }
    }

    /** 教师观察面板用：列出团队主路演会议下每个发言人的对齐情况、置信度、原话片段。 */
    private List<Map<String, Object>> roadshowSpeakerAlignment(Long teamId) {
        Map<String, Object> roadshow = roadshow(teamId);
        Long meetingId = longValue(roadshow.get("meetingId"));
        if (meetingId == null) return List.of();
        List<Map<String, Object>> rows = jdbc.queryForList("""
            SELECT s.id, s.speaker_label speakerLabel, s.claimed_role claimedRole, s.normalized_role normalizedRole,
                   s.matched_name matchedName, s.matched_user_id matchedUserId, u.username matchedUsername,
                   s.matched_role_name matchedRoleName, s.match_method matchMethod, s.match_confidence matchConfidence,
                   s.duration_sec durationSec, s.dimensions_json dimensionsJson, s.evidence_quotes_json evidenceQuotesJson,
                   s.status
            FROM roadshow_speaker_score s
            LEFT JOIN users u ON u.id = s.matched_user_id
            WHERE s.team_id = ? AND s.meeting_id = ?
            ORDER BY s.speaker_label
            """, teamId, meetingId);
        for (Map<String, Object> row : rows) {
            row.put("dimensions", readJsonMap(row.get("dimensionsJson")));
            row.put("quote", firstQuote(row.get("evidenceQuotesJson")));
            row.remove("dimensionsJson");
            row.remove("evidenceQuotesJson");
        }
        return rows;
    }

    private String memberPosition(Long teamId, Long userId) {
        try {
            return jdbc.queryForObject(
                    "SELECT position_name FROM project_team_member WHERE team_id = ? AND user_id = ?",
                    String.class, teamId, userId);
        } catch (Exception e) {
            return null;
        }
    }

    /**
     * 教师对发言人对齐结果做人工裁定：
     * CONFIRM/ASSIGN → 确认或改派到指定成员（status=CONFIRMED, method=TEACHER, conf=1）；
     * REJECT → 否决（不计入任何成员）；RESET → 退回自动并重新对齐。完成后置脏能力画像。
     */
    public Map<String, Object> resolveRoadshowSpeaker(Long speakerId, Long tenantId, Long userId, String role, Map<String, Object> body) {
        Map<String, Object> row = queryOne(
                "SELECT id, team_id teamId, meeting_id meetingId, matched_user_id matchedUserId FROM roadshow_speaker_score WHERE id = ?",
                speakerId);
        if (row == null || row.get("id") == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "发言人记录不存在");
        }
        Long teamId = longValue(row.get("teamId"));
        Long meetingId = longValue(row.get("meetingId"));
        assertCanManage(teamId, tenantId, userId, role, "BIND_ROADSHOW");
        String action = text(body.get("action"), "").toUpperCase(Locale.ROOT);
        switch (action) {
            case "CONFIRM", "ASSIGN" -> {
                Long matchedUserId = longValue(body.get("matchedUserId"));
                if (matchedUserId == null) matchedUserId = longValue(row.get("matchedUserId"));
                if (matchedUserId == null) {
                    throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "请选择要确认对齐的成员");
                }
                assertTeamMember(teamId, matchedUserId);
                String position = memberPosition(teamId, matchedUserId);
                jdbc.update("""
                    UPDATE roadshow_speaker_score
                    SET matched_user_id = ?, matched_role_name = ?, match_method = 'TEACHER',
                        match_confidence = 1.00, status = 'CONFIRMED'
                    WHERE id = ?
                    """, matchedUserId, position, speakerId);
            }
            case "REJECT" -> jdbc.update(
                    "UPDATE roadshow_speaker_score SET status = 'REJECTED', matched_user_id = NULL WHERE id = ?", speakerId);
            case "RESET" -> {
                jdbc.update("""
                    UPDATE roadshow_speaker_score
                    SET status = 'AUTO', match_method = 'NONE', matched_user_id = NULL, matched_role_name = NULL
                    WHERE id = ?
                    """, speakerId);
                alignTeamMeetingSpeakers(teamId, meetingId);
            }
            default -> throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "不支持的操作类型");
        }
        markAbilityDirty(teamId);
        return Map.of("ok", true, "teamId", teamId, "speakerId", speakerId, "status",
                action.equals("REJECT") ? "REJECTED" : action.equals("RESET") ? "AUTO" : "CONFIRMED");
    }

    private Object firstNonBlank(Object... values) {
        if (values == null) return null;
        for (Object value : values) {
            if (value == null) continue;
            if (value instanceof String s && s.isBlank()) continue;
            return value;
        }
        return null;
    }

    private void refreshAbilitySnapshots(Long teamId) {
        List<Map<String, Object>> memberRows = members(teamId);
        for (Map<String, Object> member : memberRows) {
            Long userId = longValue(member.get("userId"));
            List<Evidence> evidence = buildEvidence(teamId, userId);
            jdbc.update("DELETE FROM member_ability_evidence WHERE team_id = ? AND user_id = ?", teamId, userId);
            for (Evidence item : evidence) {
                jdbc.update("""
                    INSERT INTO member_ability_evidence
                    (team_id, user_id, dimension_key, source_type, source_id, score, weight, summary)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, teamId, userId, item.dimensionKey, item.sourceType, item.sourceId, item.score, item.weight, item.summary);
            }
            Map<String, Integer> scores = new LinkedHashMap<>();
            for (String key : ABILITY_DIMENSIONS) {
                List<Evidence> byDimension = evidence.stream().filter(e -> e.dimensionKey.equals(key)).toList();
                int weighted = weightedScore(byDimension);
                scores.put(key, weighted);
            }
            long scoredEvidenceCount = evidence.stream().filter(e -> e.weight > 0).count();
            int confidence = Math.min(100, (int) Math.round(scoredEvidenceCount / 12.0 * 100));
            jdbc.update("""
                INSERT INTO member_ability_snapshot
                (team_id, user_id, problem_solving, coding, communication, teamwork, presentation, creativity, confidence, calculated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NOW())
                ON DUPLICATE KEY UPDATE
                  problem_solving = VALUES(problem_solving),
                  coding = VALUES(coding),
                  communication = VALUES(communication),
                  teamwork = VALUES(teamwork),
                  presentation = VALUES(presentation),
                  creativity = VALUES(creativity),
                  confidence = VALUES(confidence),
                  calculated_at = NOW()
                """,
                teamId, userId,
                scores.get("problemSolving"),
                scores.get("coding"),
                scores.get("communication"),
                scores.get("teamwork"),
                scores.get("presentation"),
                scores.get("creativity"),
                confidence
            );
        }
        jdbc.update("UPDATE project_team SET ability_synced_at = NOW() WHERE id = ?", teamId);
    }

    private List<Evidence> buildEvidence(Long teamId, Long userId) {
        List<Evidence> evidence = new ArrayList<>();
        int courseProgress = queryInt("SELECT COALESCE(ROUND(AVG(progress_percent)), 0) FROM course_learning_progress WHERE user_id = ?", userId);
        if (courseProgress > 0) {
            evidence.add(new Evidence("coding", "COURSE", null, courseProgress, 2, "课程学习平均进度 " + courseProgress + "%，权重2，反映技术知识准备度"));
            evidence.add(new Evidence("problemSolving", "COURSE", null, Math.min(96, courseProgress + 4), 1, "课程完成度折算问题理解基础，权重1"));
        }
        Map<String, Object> exam = queryOne("""
            SELECT COALESCE(ROUND(AVG(score / NULLIF(total_score, 0) * 100)), 0) avgScore,
                   COALESCE(SUM(correct_count), 0) correctCount,
                   COALESCE(SUM(question_count), 0) questionCount
            FROM exam_attempt
            WHERE user_id = ? AND status = 'SUBMITTED'
            """, userId);
        int examScore = intValue(exam.get("avgScore"), 0);
        if (examScore > 0) {
            evidence.add(new Evidence("problemSolving", "EXAM", null, examScore, 2, "考试平均得分率 " + examScore + "%，权重2，反映知识迁移和解题准确性"));
            evidence.add(new Evidence("coding", "EXAM", null, Math.min(96, examScore + 3), 1, "测评中的技术题表现折算代码能力，权重1"));
        }
        Map<String, Object> taskStats = queryOne("""
            SELECT COUNT(*) totalTasks,
                   SUM(CASE WHEN status = 'DONE' THEN 1 ELSE 0 END) doneTasks,
                   SUM(CASE WHEN status = 'CHANGES_REQUESTED' THEN 1 ELSE 0 END) returnedTasks
            FROM project_task
            WHERE team_id = ? AND owner_user_id = ?
            """, teamId, userId);
        int taskTotal = intValue(taskStats.get("totalTasks"), 0);
        if (taskTotal > 0) {
            int doneRate = Math.round(intValue(taskStats.get("doneTasks"), 0) * 100f / taskTotal);
            int quality = Math.max(45, doneRate - intValue(taskStats.get("returnedTasks"), 0) * 8);
            evidence.add(new Evidence("teamwork", "TASK", null, doneRate, 2, "个人负责任务完成率 " + doneRate + "%，权重2，反映协作履约"));
            evidence.add(new Evidence("problemSolving", "TASK", null, quality, 1, "任务返修次数会扣分，当前问题闭环质量 " + quality + "，权重1"));
        }
        int approvedMaterials = queryInt("""
            SELECT COUNT(*) FROM project_material
            WHERE team_id = ? AND owner_user_id = ? AND review_status = 'APPROVED'
            """, teamId, userId);
        if (approvedMaterials > 0) {
            int score = Math.min(94, 68 + approvedMaterials * 8);
            evidence.add(new Evidence("communication", "MATERIAL", null, score, 1, "已通过审核材料 " + approvedMaterials + " 份，权重1，反映表达完整性"));
            evidence.add(new Evidence("creativity", "MATERIAL", null, Math.min(96, score + 4), 1, "材料通过审核支撑方案表达和创意呈现，权重1"));
        }
        Map<String, Object> roadshow = roadshow(teamId);
        int roadshowScore = intValue(roadshow.get("score"), 0);
        if (roadshowScore > 0) {
            Long meetingId = longValue(roadshow.get("meetingId"));
            String source = "AI".equals(roadshow.get("scoreSource")) ? "AI 评分" : "评委评分";
            String meetingTitle = text(roadshow.get("meetingTitle"), "绑定路演会议");
            Map<String, Object> speaker = meetingId != null ? findSpeakerScoreForUser(teamId, meetingId, userId) : null;
            if (speaker != null) {
                // 声纹簇只证明本人确实发言；所有数值均来自公开的团队正式评分，
                // 不再读取历史 hidden speaker dimensions。
                int present = roadshowScore;
                int comm = communicationFromRoadshow(roadshow);
                int crea = creativityFromRoadshow(roadshow);
                int teamScore = teamworkFromRoadshow(roadshow);
                boolean high = "CONFIRMED".equals(text(speaker.get("status"), "AUTO"))
                        || "NAME".equals(text(speaker.get("matchMethod"), "NONE"));
                String roleName = text(speaker.get("matchedRoleName"), "");
                String tag = high
                        ? "（个人发言，已确认对齐）"
                        : "（AI 按岗位「" + roleName + "」自动对齐，教师可在观察面板确认）";
                String quote = firstQuote(speaker.get("evidenceQuotesJson"));
                String quoteText = quote.isBlank() ? "" : "；原话引用：" + quote;
                evidence.add(new Evidence("presentation", "ROADSHOW", meetingId, present, high ? 3 : 2,
                        "路演会议「" + meetingTitle + "」个人发言" + tag + "，声纹仅证明发言归属；采用团队" + source + "公开分 " + present + quoteText));
                evidence.add(new Evidence("communication", "ROADSHOW", meetingId, comm, 2,
                        "路演会议「" + meetingTitle + "」个人答辩/表达" + tag + "，采用团队正式沟通维度 " + comm));
                evidence.add(new Evidence("creativity", "ROADSHOW", meetingId, crea, high ? 2 : 1,
                        "路演会议「" + meetingTitle + "」个人创新表达" + tag + "，采用团队正式创新维度 " + crea));
                evidence.add(new Evidence("teamwork", "ROADSHOW", meetingId, teamScore, high ? 2 : 1,
                        "路演会议「" + meetingTitle + "」个人协作证据" + tag + "，采用团队正式协作维度 " + teamScore));
            } else if (meetingId != null && participatedInMeeting(meetingId, userId)) {
                // 兜底：登录过会议室但暂无分发言人分析 → 套用团队级综合分
                evidence.add(new Evidence("presentation", "ROADSHOW", meetingId, roadshowScore, 3, "本人参与路演会议「" + meetingTitle + "」，" + source + "综合分 " + roadshowScore + "，权重3，计入个人演讲能力"));
                evidence.add(new Evidence("communication", "ROADSHOW", meetingId, communicationFromRoadshow(roadshow), 2, "本人参与路演会议「" + meetingTitle + "」，" + source + "表达清晰度/答辩反馈折算沟通能力，权重2"));
                evidence.add(new Evidence("creativity", "ROADSHOW", meetingId, creativityFromRoadshow(roadshow), 2, "本人参与路演会议「" + meetingTitle + "」，" + source + "创新创意维度折算，权重2"));
                evidence.add(new Evidence("teamwork", "ROADSHOW", meetingId, teamworkFromRoadshow(roadshow), 2, "本人参与路演会议「" + meetingTitle + "」，" + source + "团队协作维度折算，权重2"));
            } else {
                evidence.add(new Evidence("presentation", "ROADSHOW_CONTEXT", meetingId, 50, 0, "团队已绑定路演会议「" + meetingTitle + "」并获得 " + roadshowScore + " 分，但暂未对齐到该成员（未登录会议室、且未匹配到发言岗位/姓名）；仅作团队复盘，不计入个人能力画像"));
            }
        }
        int openOwnedIssues = queryInt("""
            SELECT COUNT(*) FROM project_review_issue
            WHERE team_id = ? AND status <> 'DONE' AND (owner_user_id = ? OR owner_user_id IS NULL)
            """, teamId, userId);
        if (openOwnedIssues > 0) {
            int problemScore = Math.max(35, 82 - openOwnedIssues * 7);
            evidence.add(new Evidence("problemSolving", "REVIEW", null, problemScore, 1, "未闭环复盘问题 " + openOwnedIssues + " 个，按问题闭环风险折算，权重1"));
        }
        if (evidence.isEmpty()) {
            evidence.add(new Evidence("problemSolving", "BASELINE", null, 50, 1, "暂无足够证据，使用基础分等待采样"));
            evidence.add(new Evidence("coding", "BASELINE", null, 50, 1, "暂无足够证据，使用基础分等待采样"));
            evidence.add(new Evidence("communication", "BASELINE", null, 50, 1, "暂无足够证据，使用基础分等待采样"));
            evidence.add(new Evidence("teamwork", "BASELINE", null, 50, 1, "暂无足够证据，使用基础分等待采样"));
            evidence.add(new Evidence("presentation", "BASELINE", null, 50, 1, "暂无足够证据，使用基础分等待采样"));
            evidence.add(new Evidence("creativity", "BASELINE", null, 50, 1, "暂无足够证据，使用基础分等待采样"));
        }
        return evidence;
    }

    /** 取本人在该路演会议下、已对齐且未被否决的分发言人评分（优先教师确认，其次置信度高）。 */
    private Map<String, Object> findSpeakerScoreForUser(Long teamId, Long meetingId, Long userId) {
        if (teamId == null || meetingId == null || userId == null) return null;
        List<Map<String, Object>> rows = jdbc.queryForList("""
            SELECT status, match_method matchMethod, matched_role_name matchedRoleName, match_confidence matchConfidence,
                   dimensions_json dimensionsJson, evidence_quotes_json evidenceQuotesJson
            FROM roadshow_speaker_score
            WHERE team_id = ? AND meeting_id = ? AND matched_user_id = ? AND status <> 'REJECTED'
            ORDER BY FIELD(status, 'CONFIRMED', 'AUTO'), match_confidence DESC, id DESC
            LIMIT 1
            """, teamId, meetingId, userId);
        return rows.isEmpty() ? null : rows.get(0);
    }

    @SuppressWarnings("unchecked")
    private String firstQuote(Object quotesJson) {
        for (Object item : readJsonList(quotesJson)) {
            if (item == null) continue;
            String text;
            if (item instanceof Map<?, ?> map) {
                text = text(((Map<String, Object>) map).get("quote"), text(((Map<String, Object>) map).get("text"), ""));
            } else {
                text = item.toString();
            }
            if (text != null && !text.isBlank()) {
                String trimmed = text.trim();
                return trimmed.length() > 60 ? trimmed.substring(0, 60) + "…" : trimmed;
            }
        }
        return "";
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> readJsonMap(Object value) {
        if (value == null) return Map.of();
        if (value instanceof Map<?, ?> map) return (Map<String, Object>) map;
        String text = value.toString();
        if (text.isBlank()) return Map.of();
        try {
            return objectMapper.readValue(text, new TypeReference<Map<String, Object>>() {});
        } catch (Exception e) {
            return Map.of();
        }
    }

    @SuppressWarnings("unchecked")
    private List<Object> readJsonList(Object value) {
        if (value == null) return List.of();
        if (value instanceof List<?> list) return (List<Object>) list;
        String text = value.toString();
        if (text.isBlank()) return List.of();
        try {
            return objectMapper.readValue(text, new TypeReference<List<Object>>() {});
        } catch (Exception e) {
            return List.of();
        }
    }

    private int creativityFromRoadshow(Map<String, Object> roadshow) {
        return dimensionPercent(roadshow, List.of("创新创意", "创新意识", "创新成效", "创新"), intValue(roadshow.get("score"), 0));
    }

    private int teamworkFromRoadshow(Map<String, Object> roadshow) {
        return dimensionPercent(roadshow, List.of("团队合作", "团队精神", "沟通协作", "团队"), intValue(roadshow.get("score"), 0));
    }

    private int communicationFromRoadshow(Map<String, Object> roadshow) {
        int score = intValue(roadshow.get("score"), 0);
        int expression = dimensionPercent(roadshow, List.of("现场讲解效果", "沟通协作", "表达", "答辩"), -1);
        if (expression >= 0) return expression;
        int speechScore = speechQualityScore(roadshow.get("speechQuality"));
        if (speechScore >= 0) return speechScore;
        return score;
    }

    @SuppressWarnings("unchecked")
    private int dimensionPercent(Map<String, Object> roadshow, List<String> keywords, int fallback) {
        Object dimensionsObj = roadshow.get("dimensions");
        if (!(dimensionsObj instanceof List<?> dimensions)) return fallback;
        return dimensions.stream()
                .filter(Map.class::isInstance)
                .map(item -> (Map<String, Object>) item)
                .filter(item -> keywords.stream().anyMatch(keyword -> String.valueOf(item.get("name")).contains(keyword)))
                .map(this::dimensionRowPercent)
                .findFirst()
                .orElse(fallback);
    }

    private int dimensionRowPercent(Map<String, Object> row) {
        int percent = intValue(row.get("percent"), -1);
        if (percent >= 0) return percent;
        float score = floatValue(row.get("score"), -1);
        float maxScore = floatValue(row.get("maxScore"), floatValue(row.get("max_score"), -1));
        if (score >= 0 && maxScore > 0) return Math.round(score / maxScore * 100f);
        return intValue(row.get("score"), 0);
    }

    private List<Map<String, Object>> aiDimensions(Object json) {
        Map<String, Object> parsed = parseJsonMap(json);
        if (parsed.isEmpty()) return List.of();
        return parsed.entrySet().stream().map(entry -> {
            Map<String, Object> dimension = parseJsonMap(entry.getValue());
            String name = text(dimension.get("name"), readableDimensionName(entry.getKey()));
            float score = floatValue(dimension.get("score"), floatValue(entry.getValue(), 0));
            float maxScore = floatValue(dimension.get("max_score"), floatValue(dimension.get("maxScore"), 100));
            int percent = maxScore > 0 ? Math.round(score / maxScore * 100f) : Math.round(score);
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("key", entry.getKey());
            row.put("name", name);
            row.put("score", score);
            row.put("maxScore", maxScore);
            row.put("percent", Math.max(0, Math.min(100, percent)));
            row.put("items", dimension.getOrDefault("items", List.of()));
            return row;
        }).toList();
    }

    private String readableDimensionName(String key) {
        return switch (key) {
            case "skill_level" -> "技能水平";
            case "professionalism" -> "职业素养";
            case "application_value" -> "应用价值";
            case "teamwork" -> "团队合作";
            case "innovation" -> "创新创意";
            default -> key;
        };
    }

    @SuppressWarnings("unchecked")
    private int speechQualityScore(Object value) {
        Map<String, Object> speech = parseJsonMap(value);
        if (speech.isEmpty()) return -1;
        Object rating = speech.get("overall_rating");
        if (rating instanceof Map<?, ?> map) {
            int score = intValue(((Map<String, Object>) map).get("total_score"), -1);
            if (score >= 0) return score;
        }
        int rateScore = nestedScore(speech.get("speech_rate"), "rating_score");
        int fillerScore = nestedScore(speech.get("fillers"), "filler_rate_percent");
        List<Integer> scores = new ArrayList<>();
        if (rateScore >= 0) scores.add(rateScore);
        if (fillerScore >= 0) scores.add(Math.max(0, Math.min(100, 100 - fillerScore * 8)));
        if (scores.isEmpty()) return -1;
        return Math.round(scores.stream().mapToInt(Integer::intValue).sum() * 1f / scores.size());
    }

    private int nestedScore(Object value, String key) {
        Map<String, Object> map = parseJsonMap(value);
        return intValue(map.get(key), -1);
    }

    private List<Object> normalizeJsonList(Object json) {
        if (json == null) return List.of();
        try {
            if (json instanceof String text && !text.isBlank()) {
                return objectMapper.readValue(text, new TypeReference<List<Object>>() {});
            }
            if (json instanceof List<?> list) return List.copyOf(list);
        } catch (Exception ignored) {
        }
        return List.of();
    }

    private Map<String, Object> parseJsonMap(Object json) {
        if (json == null) return Map.of();
        try {
            if (json instanceof String text && !text.isBlank()) {
                return objectMapper.readValue(text, new TypeReference<Map<String, Object>>() {});
            }
            if (json instanceof Map<?, ?> map) {
                return map.entrySet().stream().collect(Collectors.toMap(e -> String.valueOf(e.getKey()), Map.Entry::getValue));
            }
        } catch (Exception ignored) {
        }
        return Map.of();
    }

    private int weightedScore(List<Evidence> evidence) {
        List<Evidence> scored = evidence.stream().filter(e -> e.weight > 0).toList();
        if (scored.isEmpty()) return 50;
        int weight = scored.stream().mapToInt(e -> e.weight).sum();
        int total = scored.stream().mapToInt(e -> e.score * e.weight).sum();
        return Math.max(0, Math.min(100, Math.round(total * 1f / Math.max(1, weight))));
    }

    private boolean participatedInMeeting(Long meetingId, Long userId) {
        Integer count = jdbc.queryForObject("""
            SELECT COUNT(*)
            FROM meeting_participant
            WHERE meeting_id = ? AND user_id = ?
            """, Integer.class, meetingId, userId);
        return count != null && count > 0;
    }

    private void assertCanManage(Long teamId, Long tenantId, Long userId, String role, String requiredPermission) {
        team(teamId, tenantId);
        if (hasTeacherTeamScope(teamId, userId, role) || hasCaptainPermission(teamId, userId, requiredPermission)) return;
        throw new ResponseStatusException(HttpStatus.FORBIDDEN, "无权执行该团队管理操作");
    }

    private void assertCanReviewSubmission(Long teamId, Long taskId, Long userId, String role) {
        String normalizedRole = String.valueOf(role).toUpperCase(Locale.ROOT);
        if (Set.of("ADMIN", "SCHOOL_ADMIN").contains(normalizedRole)) return;
        if ("TEACHER".equals(normalizedRole) && isTeamMentor(teamId, userId)) return;
        if (hasCaptainPermission(teamId, userId, "REVIEW_SUBMISSION")) return;
        Integer designatedPeerReviewer = jdbc.queryForObject("""
            SELECT COUNT(*)
            FROM project_task task
            JOIN project_team_member member
              ON member.team_id=task.team_id AND member.user_id=?
            WHERE task.id=? AND task.team_id=?
              AND task.source_type='PEER_COLLABORATION'
              AND task.reviewer_user_id=?
            """, Integer.class, userId, taskId, teamId, userId);
        if (designatedPeerReviewer != null && designatedPeerReviewer > 0) return;
        throw new ResponseStatusException(HttpStatus.FORBIDDEN, "无权审核该团队任务提交");
    }

    private boolean isTeamMentor(Long teamId, Long userId) {
        Integer count = jdbc.queryForObject("""
            SELECT COUNT(*)
            FROM project_team t
            WHERE t.id = ?
              AND (t.mentor_id = ? OR EXISTS (
                SELECT 1
                FROM project_team_member mentor
                WHERE mentor.team_id = t.id
                  AND mentor.user_id = ?
                  AND mentor.role_in_team = 'MENTOR'
              ))
            """, Integer.class, teamId, userId, userId);
        return count != null && count > 0;
    }

    /** 仅管理员或指导教师可调整阶段配置。 */
    private void assertCanEditStageSchedule(Long teamId, Long tenantId, Long userId, String role) {
        team(teamId, tenantId);
        if (!canEditStageSchedule(teamId, userId, role, roleInTeam(teamId, userId))) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "仅管理员或指导教师可修改阶段配置");
        }
    }

    private boolean canEditStageSchedule(Long teamId, Long userId, String role, String roleInTeam) {
        return hasTeacherTeamScope(teamId, userId, role);
    }

    private boolean stageIsOptional(Map<String, Object> row) {
        if (row == null) return false;
        Object value = row.get("isOptional");
        if (value instanceof Boolean bool) return bool;
        if (value instanceof Number number) return number.intValue() != 0;
        if (value != null) {
            String text = String.valueOf(value).trim();
            if ("true".equalsIgnoreCase(text) || "1".equals(text)) return true;
            if ("false".equalsIgnoreCase(text) || "0".equals(text)) return false;
        }
        return OPTIONAL_STAGE_KEYS.contains(text(row.get("stageKey"), ""));
    }

    private void assertTeamAccess(Long teamId, Long tenantId, Long userId, String role) {
        team(teamId, tenantId);
        if (hasTeacherTeamScope(teamId, userId, role) || roleInTeam(teamId, userId) != null) return;
        throw new ResponseStatusException(HttpStatus.FORBIDDEN, "无权访问该团队");
    }

    private void assertTrainingTaskAvailableForStudent(
            Long teamId,
            Long taskId,
            Long tenantId,
            String role
    ) {
        if (canUseTeacherScope(role)) return;
        List<Map<String, Object>> rows = jdbc.queryForList("""
            SELECT d.id dayId, d.training_date trainingDate, d.status,
                   d.early_unlocked_at earlyUnlockedAt
            FROM training_day_task dt
            JOIN training_day d ON d.id = dt.training_day_id
            JOIN training_camp c ON c.id = d.camp_id AND c.tenant_id = ?
            JOIN training_camp_team ct ON ct.camp_id = c.id
              AND ct.team_id = ? AND ct.status = 'ACTIVE'
            WHERE dt.task_id = ?
            ORDER BY CASE WHEN c.status IN ('PLANNED', 'ACTIVE') THEN 0 ELSE 1 END,
                     d.training_date DESC, d.id DESC
            """, tenantId, teamId, taskId);
        if (rows.isEmpty()) return;
        List<Map<String, Object>> availability = rows.stream()
                .map(trainingDayAvailabilityService::availability)
                .toList();
        if (availability.stream().anyMatch(item -> !Boolean.TRUE.equals(item.get("locked")))) return;
        String reason = availability.stream()
                .anyMatch(item -> "NOT_PUBLISHED".equals(item.get("lockReason")))
                ? "训练日尚未发布"
                : "训练日尚未开放";
        throw new ResponseStatusException(HttpStatus.LOCKED, reason);
    }

    private void assertTeamMember(Long teamId, Long userId) {
        Integer count = jdbc.queryForObject("SELECT COUNT(*) FROM project_team_member WHERE team_id = ? AND user_id = ?", Integer.class, teamId, userId);
        if (count == null || count == 0) throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "负责人不是该团队成员");
    }

    private void assertTenantUser(Long tenantId, Long userId) {
        Integer count = jdbc.queryForObject("SELECT COUNT(*) FROM users WHERE tenant_id = ? AND id = ?", Integer.class, tenantId, userId);
        if (count == null || count == 0) throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "用户不属于当前租户");
    }

    private void assertTenantProjectParticipant(Long tenantId, Long userId, Long operatorUserId, String operatorRole) {
        Integer count = jdbc.queryForObject("""
            SELECT COUNT(*) FROM users target
            JOIN users operator ON operator.id=? AND operator.tenant_id=target.tenant_id
            WHERE target.tenant_id=? AND target.id=? AND target.role NOT IN ('ADMIN', 'SCHOOL_ADMIN')
              AND (?=1 OR (
                (operator.school_id IS NULL AND target.id=operator.id)
                OR (target.school_id=operator.school_id AND (operator.college_id IS NULL OR target.college_id=operator.college_id))
              ))
            """, Integer.class, operatorUserId, tenantId, userId, isAdministrator(operatorRole) ? 1 : 0);
        if (count == null || count == 0) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "项目成员必须属于当前教师所在学院，且不能是系统管理员账号");
        }
    }

    private String userSystemRole(Long tenantId, Long userId) {
        String role = jdbc.queryForObject(
                "SELECT role FROM users WHERE tenant_id = ? AND id = ?",
                String.class,
                tenantId,
                userId
        );
        String normalized = String.valueOf(role).toUpperCase(Locale.ROOT);
        if (!Set.of("STUDENT", "TEACHER").contains(normalized)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "团队成员只能设置为学生或教师");
        }
        return normalized;
    }

    private String requestedSystemRole(
            Long tenantId,
            Long memberUserId,
            String operatorRole,
            Object requestedValue
    ) {
        String currentRole = userSystemRole(tenantId, memberUserId);
        if (requestedValue == null || String.valueOf(requestedValue).isBlank()) {
            return currentRole;
        }
        String requestedRole = String.valueOf(requestedValue).trim().toUpperCase(Locale.ROOT);
        if (!Set.of("STUDENT", "TEACHER").contains(requestedRole)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "成员身份只能设置为学生或教师");
        }
        if (!Objects.equals(currentRole, requestedRole) && !canUseTeacherScope(operatorRole)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "只有教师或管理员可以修改成员全局身份");
        }
        return requestedRole;
    }

    private String teamRoleForSystemRole(String systemRole, String currentTeamRole) {
        if ("CAPTAIN".equals(currentTeamRole)) {
            if ("TEACHER".equals(systemRole)) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "队长必须保持学生身份，请先更换队长");
            }
            return "CAPTAIN";
        }
        return "TEACHER".equals(systemRole) ? "MENTOR" : "MEMBER";
    }

    private void assignPrimaryMentorIfMissing(Long teamId, Long memberUserId) {
        jdbc.update("""
            UPDATE project_team
            SET mentor_id = COALESCE(mentor_id, ?)
            WHERE id = ?
            """, memberUserId, teamId);
    }

    private void preparePrimaryMentorChange(
            Long teamId,
            Long memberUserId,
            String currentTeamRole,
            String targetTeamRole
    ) {
        if (!"MENTOR".equals(currentTeamRole) || "MENTOR".equals(targetTeamRole)) return;
        Long primaryMentorId = jdbc.queryForObject(
                "SELECT mentor_id FROM project_team WHERE id = ?",
                Long.class,
                teamId
        );
        if (!Objects.equals(primaryMentorId, memberUserId)) return;
        List<Long> replacements = jdbc.queryForList("""
            SELECT user_id FROM project_team_member
            WHERE team_id = ? AND user_id <> ? AND role_in_team = 'MENTOR'
            ORDER BY id
            LIMIT 1
            """, Long.class, teamId, memberUserId);
        if (replacements.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "请先为团队指定其他指导教师");
        }
        jdbc.update("UPDATE project_team SET mentor_id = ? WHERE id = ?", replacements.get(0), teamId);
    }

    private String roleInTeam(Long teamId, Long userId) {
        List<Map<String, Object>> rows = jdbc.queryForList("SELECT role_in_team FROM project_team_member WHERE team_id = ? AND user_id = ?", teamId, userId);
        return rows.isEmpty() ? null : String.valueOf(rows.get(0).get("role_in_team"));
    }

    private Long taskTeamId(Long taskId) {
        List<Map<String, Object>> rows = jdbc.queryForList("SELECT team_id FROM project_task WHERE id = ?", taskId);
        if (rows.isEmpty()) throw new ResponseStatusException(HttpStatus.NOT_FOUND, "任务不存在");
        return longValue(rows.get(0).get("team_id"));
    }

    private boolean canUseTeacherScope(String role) {
        return Set.of("ADMIN", "SCHOOL_ADMIN", "TEACHER").contains(String.valueOf(role).toUpperCase(Locale.ROOT));
    }

    private boolean isAdministrator(String role) {
        return Set.of("ADMIN", "SCHOOL_ADMIN").contains(String.valueOf(role).toUpperCase(Locale.ROOT));
    }

    private boolean isTeacher(String role) {
        return "TEACHER".equals(String.valueOf(role).toUpperCase(Locale.ROOT));
    }

    private boolean hasTeacherTeamScope(Long teamId, Long userId, String role) {
        return isAdministrator(role) || (isTeacher(role) && isTeamMentor(teamId, userId));
    }

    private Map<String, Boolean> managementPermissions(Long teamId, Long userId, String role) {
        Map<String, Boolean> permissions = new LinkedHashMap<>();
        boolean teacherScope = hasTeacherTeamScope(teamId, userId, role);
        for (String key : CAPTAIN_PERMISSION_KEYS) {
            permissions.put(key, teacherScope || hasCaptainPermission(teamId, userId, key));
        }
        return permissions;
    }

    private boolean hasCaptainPermission(Long teamId, Long userId, String requiredPermission) {
        List<Map<String, Object>> rows = jdbc.queryForList("""
            SELECT role_in_team, captain_permissions
            FROM project_team_member
            WHERE team_id = ? AND user_id = ?
            """, teamId, userId);
        if (rows.isEmpty() || !"CAPTAIN".equals(String.valueOf(rows.get(0).get("role_in_team")))) return false;
        List<String> permissions = sanitizeCaptainPermissions(rows.get(0).get("captain_permissions"));
        if (permissions.isEmpty()) permissions = CAPTAIN_PERMISSION_KEYS;
        return permissions.contains(requiredPermission);
    }

    private List<String> sanitizeCaptainPermissions(Object value) {
        List<String> raw = stringList(value);
        return raw.stream()
                .map(item -> item.toUpperCase(Locale.ROOT))
                .filter(CAPTAIN_PERMISSION_KEYS::contains)
                .distinct()
                .toList();
    }

    private String permissionsJson(List<String> permissions) {
        try {
            return objectMapper.writeValueAsString(permissions);
        } catch (Exception e) {
            return "[\"ASSIGN_TASK\",\"REVIEW_SUBMISSION\",\"REVIEW_MATERIAL\",\"BIND_ROADSHOW\"]";
        }
    }

    private String defaultResponsibility(String position) {
        return switch (position) {
            case "项目统筹" -> "拆解项目任务、分配负责人、审核材料并推动复盘闭环";
            case "指导教师" -> "观察团队进展、识别风险并给出教学干预建议";
            default -> "按任务节点提交材料，完成测评训练和路演复盘";
        };
    }

    private Long insert(String sql, Object... args) {
        KeyHolder keyHolder = new GeneratedKeyHolder();
        jdbc.update(connection -> {
            PreparedStatement ps = connection.prepareStatement(sql, Statement.RETURN_GENERATED_KEYS);
            for (int i = 0; i < args.length; i++) ps.setObject(i + 1, args[i]);
            return ps;
        }, keyHolder);
        Number key = keyHolder.getKey();
        if (key == null) throw new IllegalStateException("插入数据失败，未返回主键");
        return key.longValue();
    }

    private boolean meetingExists(Long meetingId) {
        Integer count = jdbc.queryForObject("SELECT COUNT(*) FROM meeting WHERE id = ?", Integer.class, meetingId);
        return count != null && count > 0;
    }

    private boolean aiReportExists(Long meetingId) {
        Integer count = jdbc.queryForObject("SELECT COUNT(*) FROM ai_score_report WHERE meeting_id = ?", Integer.class, meetingId);
        return count != null && count > 0;
    }

    private Map<String, Object> parseNestedMap(Object value) {
        if (value instanceof Map<?, ?> map) {
            return map.entrySet().stream().collect(Collectors.toMap(entry -> String.valueOf(entry.getKey()), Map.Entry::getValue));
        }
        if (value instanceof String text && !text.isBlank()) {
            try {
                return objectMapper.readValue(text, new TypeReference<Map<String, Object>>() {});
            } catch (Exception ignored) {
            }
        }
        return Map.of();
    }

    private String jsonString(Object value) {
        if (value == null) return null;
        if (value instanceof String text) return text.isBlank() ? null : text;
        try {
            return objectMapper.writeValueAsString(value);
        } catch (Exception ignored) {
            return String.valueOf(value);
        }
    }

    private String relativizeAiResultPath(Path path) {
        try {
            Path root = Paths.get(System.getProperty("user.home"), "项目", "OREP", "ai-scoring", "uploads");
            return root.relativize(path).toString();
        } catch (Exception ignored) {
            return path.toString();
        }
    }

    private LocalDateTime dateTimeValue(Object value) {
        String text = nullableText(value);
        if (text == null) return null;
        try {
            return LocalDateTime.parse(text);
        } catch (Exception ignored) {
            return null;
        }
    }

    private LocalDate localDateValue(Object value) {
        String text = nullableText(value);
        if (text == null) return null;
        try {
            if (text.length() >= 10) {
                return LocalDate.parse(text.substring(0, 10));
            }
            return LocalDate.parse(text);
        } catch (Exception ignored) {
            return null;
        }
    }

    private Map<String, Object> requireActiveTrack(Object trackIdValue) {
        String trackId = trackIdValue == null ? "" : String.valueOf(trackIdValue).trim();
        if (trackId.isBlank()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "请从 42 个正式赛道中选择一个赛道");
        }
        List<Map<String, Object>> rows = jdbc.queryForList("""
            SELECT track_id trackId, track_name trackName
            FROM track_rubric_config
            WHERE track_id = ? AND status = 'active' AND active_slot = 'ACTIVE'
            LIMIT 1
            """, trackId);
        if (rows.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "所选赛道不存在或已停用，请重新选择");
        }
        return rows.get(0);
    }

    private boolean booleanValue(Object value) {
        if (value == null) return false;
        if (value instanceof Boolean bool) return bool;
        String text = String.valueOf(value).trim();
        return "true".equalsIgnoreCase(text) || "1".equals(text);
    }

    private BigDecimal decimalValue(Object value) {
        if (value == null) return null;
        try {
            return new BigDecimal(String.valueOf(value));
        } catch (Exception ignored) {
            return null;
        }
    }

    private Map<String, Object> queryOne(String sql, Object... args) {
        List<Map<String, Object>> rows = jdbc.queryForList(sql, args);
        return rows.isEmpty() ? Map.of() : rows.get(0);
    }

    private int queryInt(String sql, Object... args) {
        Integer value = jdbc.queryForObject(sql, Integer.class, args);
        return value != null ? value : 0;
    }

    private Long longValue(Object value) {
        if (value == null) return null;
        if (value instanceof Number number) return number.longValue();
        String text = String.valueOf(value);
        if (text.isBlank()) return null;
        try {
            return Long.parseLong(text);
        } catch (NumberFormatException ignored) {
            return null;
        }
    }

    private Map<Long, Map<String, Object>> memberAssignments(Object value) {
        if (value == null) return Map.of();
        Collection<?> items;
        if (value instanceof Collection<?> collection) {
            items = collection;
        } else if (value instanceof String text && text.trim().startsWith("[")) {
            try {
                items = objectMapper.readValue(text, new TypeReference<List<Map<String, Object>>>() {});
            } catch (Exception ignored) {
                return Map.of();
            }
        } else {
            return Map.of();
        }
        Map<Long, Map<String, Object>> assignments = new LinkedHashMap<>();
        for (Object item : items) {
            if (!(item instanceof Map<?, ?> raw)) continue;
            Map<String, Object> map = raw.entrySet().stream()
                    .collect(Collectors.toMap(entry -> String.valueOf(entry.getKey()), Map.Entry::getValue));
            Long userId = longValue(map.get("userId"));
            if (userId != null) assignments.put(userId, map);
        }
        return assignments;
    }

    private List<Long> longList(Object value) {
        if (value == null) return List.of();
        if (value instanceof Collection<?> collection) {
            return collection.stream()
                    .map(this::longValue)
                    .filter(Objects::nonNull)
                    .distinct()
                    .toList();
        }
        String text = String.valueOf(value);
        if (text.isBlank()) return List.of();
        return Arrays.stream(text.split(","))
                .map(String::trim)
                .filter(item -> !item.isBlank())
                .map(Long::parseLong)
                .distinct()
                .toList();
    }

    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> mapList(Object value) {
        if (value == null) return List.of();
        Collection<?> items;
        if (value instanceof Collection<?> collection) {
            items = collection;
        } else if (value instanceof String text && text.trim().startsWith("[")) {
            try {
                items = objectMapper.readValue(text, new TypeReference<List<Map<String, Object>>>() {});
            } catch (Exception ignored) {
                return List.of();
            }
        } else {
            return List.of();
        }
        List<Map<String, Object>> result = new ArrayList<>();
        for (Object item : items) {
            if (item instanceof Map<?, ?> map) {
                result.add(map.entrySet().stream()
                        .collect(Collectors.toMap(entry -> String.valueOf(entry.getKey()), Map.Entry::getValue)));
            }
        }
        return result;
    }

    @SuppressWarnings("unchecked")
    private List<String> stringList(Object value) {
        if (value == null) return List.of();
        if (value instanceof Collection<?> collection) {
            return collection.stream()
                    .map(String::valueOf)
                    .map(String::trim)
                    .filter(item -> !item.isBlank())
                    .toList();
        }
        try {
            if (value instanceof String text && text.trim().startsWith("[")) {
                return objectMapper.readValue(text, new TypeReference<List<String>>() {});
            }
        } catch (Exception ignored) {
        }
        String text = String.valueOf(value);
        if (text.isBlank()) return List.of();
        return Arrays.stream(text.split(","))
                .map(String::trim)
                .filter(item -> !item.isBlank())
                .toList();
    }

    private int intValue(Object value, int fallback) {
        if (value == null) return fallback;
        if (value instanceof Number number) return number.intValue();
        if (value instanceof BigDecimal decimal) return decimal.intValue();
        String text = String.valueOf(value);
        if (text.isBlank()) return fallback;
        try {
            return Math.round(Float.parseFloat(text));
        } catch (Exception ignored) {
            return fallback;
        }
    }

    private float floatValue(Object value, float fallback) {
        if (value == null) return fallback;
        if (value instanceof Number number) return number.floatValue();
        String text = String.valueOf(value);
        if (text.isBlank()) return fallback;
        try {
            return Float.parseFloat(text);
        } catch (Exception ignored) {
            return fallback;
        }
    }

    private String requiredText(Object value, String error) {
        String text = nullableText(value);
        if (text == null) throw new ResponseStatusException(HttpStatus.BAD_REQUEST, error);
        return text;
    }

    private String text(Object value, String fallback) {
        String text = nullableText(value);
        return text != null ? text : fallback;
    }

    private String sanitizePositionName(String value, String fallback) {
        String text = nullableText(value);
        if (text == null) text = fallback;
        text = text.replaceAll("[\\r\\n\\t]+", " ").trim();
        return shortText(text, 80);
    }

    private String sanitizeResponsibility(String value, String fallback) {
        String text = nullableText(value);
        if (text == null) text = fallback;
        text = text.replaceAll("[\\r\\n\\t]+", " ").trim();
        return shortText(text, 500);
    }

    private String nullableText(Object value) {
        if (value == null) return null;
        String text = String.valueOf(value).trim();
        return text.isBlank() ? null : text;
    }

    private boolean bool(Object value, boolean fallback) {
        if (value == null) return fallback;
        if (value instanceof Boolean b) return b;
        return Boolean.parseBoolean(String.valueOf(value));
    }

    private record Evidence(String dimensionKey, String sourceType, Long sourceId, int score, int weight, String summary) {}
}
