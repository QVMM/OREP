# AI Score Upload Task Queue Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将“上传评分”重构为符合平台设计规范的紧凑上传区与全宽持久任务队列，并让当前用户的分析任务在刷新或重新登录后仍能恢复展示。

**Architecture:** 后端从现有 `ai_scoring_session` 与 `ai_score_media_asset` 持久数据中查询当前用户的上传视频评分任务，返回全部进行中任务与最近 10 条终态任务；前端通过独立组合式函数获取、轮询和刷新队列。页面只保留浏览器本地上传进度，服务器分析进度统一进入任务队列，避免重复状态卡片，并由全局 `.workspace-main` 独占页面外边距。

**Tech Stack:** Java 21、Spring Boot 3.2.5、JdbcTemplate、JUnit 5、Vue 3、Vite 8、Axios、Playwright、现有 `--ds-*` 设计令牌与 `BaseButton`

---

## 0. 文件职责与实施边界

### 新增文件

- `backend/src/main/java/com/orep/backend/dto/AiScoreUploadTaskResponse.java`：面向当前用户的安全任务队列响应。
- `backend/src/main/java/com/orep/backend/service/AiScoreUploadTaskService.java`：查询当前用户全部非终态任务和最近终态任务。
- `backend/src/test/java/com/orep/backend/service/AiScoreUploadTaskServiceTest.java`：验证用户隔离、来源隔离、排序和终态数量上限。
- `backend/src/test/java/com/orep/backend/controller/AiScoreUploadTaskControllerTest.java`：验证接口只使用认证用户身份并限制 `completedLimit`。
- `frontend/user/src/composables/useAiScoreUploadQueue.js`：任务加载、3 秒轮询、页面可见性与窗口聚焦刷新。
- `frontend/user/src/components/ai-score/AiScoreUploadTaskQueue.vue`：全宽任务队列及完成、失败、空状态动作。
- `frontend/user/tests/ai-score-upload-task-queue.spec.js`：刷新恢复、状态更新、布局、进度条和窄屏验收。

### 修改文件

- `backend/src/main/java/com/orep/backend/controller/AiScoreUploadController.java`：增加认证用户任务队列接口。
- `backend/src/test/java/com/orep/backend/controller/AiScoreUploadControllerWebMvcTest.java`：补充新服务依赖，保持 Spring MVC 装配测试通过。
- `frontend/user/src/utils/aiScoreUpload.js`：增加任务队列请求。
- `frontend/user/src/components/ai-score/VideoScoreUploadForm.vue`：压缩信息密度，折叠评分偏好，支持失败任务上下文回填。
- `frontend/user/src/views/VideoScoreUpload.vue`：移除重复状态区，组合紧凑上传卡和全宽任务队列。
- `frontend/user/tests/review-pages-design.spec.js`：更新旧的主辅栏断言为 B+ 单列布局断言。

### 明确不做

- 不实现分片上传、断点续传或浏览器刷新后的原始文件继续传输。
- 不创建独立“任务中心”页面。
- 不新增页面级外边距、私有配色或另一套组件视觉语言。
- 不返回文件存储路径、评分规则路径、rubric hash 或其他内部字段。

工作区当前没有 Git 元数据，因此每个任务末尾使用“验证检查点”记录可回退文件与测试结果，不执行会失败的提交命令。

---

### Task 1: 持久任务查询服务

**Files:**

- Create: `backend/src/main/java/com/orep/backend/dto/AiScoreUploadTaskResponse.java`
- Create: `backend/src/main/java/com/orep/backend/service/AiScoreUploadTaskService.java`
- Test: `backend/src/test/java/com/orep/backend/service/AiScoreUploadTaskServiceTest.java`

- [ ] **Step 1: 写入服务层失败测试**

创建 `AiScoreUploadTaskServiceTest.java`，用独立 H2 数据库建立最小表结构，插入：

- 当前用户 2 条非终态上传任务；
- 当前用户 12 条终态上传任务；
- 其他用户 1 条上传任务；
- 当前用户 1 条 `meeting_recording` 任务；
- 视频资产与团队名称。

测试核心内容如下：

```java
package com.orep.backend.service;

import com.orep.backend.dto.AiScoreUploadTaskResponse;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;

import java.util.List;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class AiScoreUploadTaskServiceTest {
    private JdbcTemplate jdbc;
    private AiScoreUploadTaskService service;

    @BeforeEach
    void setUp() {
        String database = "ai-upload-queue-" + UUID.randomUUID();
        jdbc = new JdbcTemplate(new DriverManagerDataSource(
                "jdbc:h2:mem:" + database + ";MODE=MySQL;DATABASE_TO_LOWER=TRUE;DB_CLOSE_DELAY=-1",
                "sa",
                ""
        ));
        jdbc.execute("""
                CREATE TABLE project_team (
                    id BIGINT PRIMARY KEY,
                    name VARCHAR(120)
                )
                """);
        jdbc.execute("""
                CREATE TABLE ai_scoring_session (
                    id BIGINT PRIMARY KEY,
                    session_no VARCHAR(80),
                    source_type VARCHAR(40),
                    project_id BIGINT,
                    team_id BIGINT,
                    track_name VARCHAR(120),
                    status VARCHAR(40),
                    current_stage VARCHAR(80),
                    progress_percent INT,
                    use_history_memory BOOLEAN,
                    jury_enabled BOOLEAN,
                    report_id BIGINT,
                    error_message VARCHAR(500),
                    created_by BIGINT,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP
                )
                """);
        jdbc.execute("""
                CREATE TABLE ai_score_media_asset (
                    id BIGINT PRIMARY KEY,
                    session_id BIGINT,
                    asset_type VARCHAR(40),
                    original_name VARCHAR(255),
                    size_bytes BIGINT
                )
                """);
        jdbc.update("INSERT INTO project_team(id, name) VALUES (9, '应用攻坚队')");

        insertSession(101, 7, "uploaded_video", "scoring", "model_scoring", 46, null, 0);
        insertSession(102, 7, "uploaded_video", "created", "queued", 5, null, 1);
        jdbc.update("""
                INSERT INTO ai_score_media_asset(id, session_id, asset_type, original_name, size_bytes)
                VALUES (1, 101, 'video', '决赛路演.mp4', 52428800)
                """);

        for (int index = 0; index < 12; index++) {
            long id = 200 + index;
            String status = index == 0 ? "failed" : "completed";
            Long reportId = "completed".equals(status) ? 900L + index : null;
            insertSession(id, 7, "uploaded_video", status, status, 100, reportId, index + 2);
        }
        insertSession(301, 8, "uploaded_video", "scoring", "model_scoring", 50, null, 30);
        insertSession(302, 7, "meeting_recording", "scoring", "model_scoring", 50, null, 31);
        service = new AiScoreUploadTaskService(jdbc);
    }

    @Test
    void returnsAllActiveAndLatestTenTerminalTasksForCurrentUser() {
        List<AiScoreUploadTaskResponse> tasks = service.listForUser(7L, 10);

        assertEquals(12, tasks.size());
        assertEquals(List.of(101L, 102L), tasks.subList(0, 2).stream()
                .map(AiScoreUploadTaskResponse::sessionId)
                .toList());
        assertTrue(tasks.stream().anyMatch(task ->
                task.sessionId().equals(101L)
                        && task.fileName().equals("决赛路演.mp4")
                        && task.fileSize().equals(52428800L)
                        && task.teamName().equals("应用攻坚队")));
        assertFalse(tasks.stream().anyMatch(task -> task.sessionId().equals(301L)));
        assertFalse(tasks.stream().anyMatch(task -> task.sessionId().equals(302L)));
        assertFalse(tasks.stream().anyMatch(task -> task.sessionId().equals(211L)));
        assertEquals(10, tasks.stream().filter(task ->
                List.of("completed", "failed", "cancelled").contains(task.status())
        ).count());
    }

    @Test
    void clampsTerminalLimitAndTruncatesPublicErrorMessage() {
        jdbc.update("""
                UPDATE ai_scoring_session
                SET error_message = ?
                WHERE id = 200
                """, "分析服务暂时不可用".repeat(30));

        List<AiScoreUploadTaskResponse> tasks = service.listForUser(7L, 99);
        AiScoreUploadTaskResponse failed = tasks.stream()
                .filter(task -> task.sessionId().equals(200L))
                .findFirst()
                .orElseThrow();

        assertEquals(10, tasks.stream().filter(task ->
                List.of("completed", "failed", "cancelled").contains(task.status())
        ).count());
        assertEquals(160, failed.errorMessage().length());
    }

    private void insertSession(long id, long userId, String sourceType, String status,
                               String stage, int progress, Long reportId, int minutesAgo) {
        jdbc.update("""
                INSERT INTO ai_scoring_session(
                    id, session_no, source_type, project_id, team_id, track_name,
                    status, current_stage, progress_percent, use_history_memory,
                    jury_enabled, report_id, error_message, created_by, created_at, updated_at
                ) VALUES (?, ?, ?, 3, 9, '新一代信息技术赛道', ?, ?, ?, TRUE,
                    FALSE, ?, ?, ?, DATEADD('MINUTE', ?, CURRENT_TIMESTAMP), CURRENT_TIMESTAMP)
                """,
                id, "SC-" + id, sourceType, status, stage, progress, reportId,
                "failed".equals(status) ? "分析服务暂时不可用" : null,
                userId, -minutesAgo);
    }
}
```

- [ ] **Step 2: 运行测试并确认 RED**

Run:

```bash
cd backend
mvn -Dtest=AiScoreUploadTaskServiceTest test
```

Expected: 编译失败，提示 `AiScoreUploadTaskService` 和 `AiScoreUploadTaskResponse` 不存在。

- [ ] **Step 3: 创建安全响应 DTO**

创建 `AiScoreUploadTaskResponse.java`：

```java
package com.orep.backend.dto;

import java.time.LocalDateTime;

public record AiScoreUploadTaskResponse(
        Long sessionId,
        String sessionNo,
        String fileName,
        Long fileSize,
        Long projectId,
        Long teamId,
        String teamName,
        String trackName,
        String status,
        String currentStage,
        Integer progressPercent,
        Boolean useHistoryMemory,
        Boolean juryEnabled,
        Long reportId,
        String errorMessage,
        LocalDateTime createdAt,
        LocalDateTime updatedAt
) {
}
```

- [ ] **Step 4: 实现当前用户队列查询**

创建 `AiScoreUploadTaskService.java`：

```java
package com.orep.backend.service;

import com.orep.backend.dto.AiScoreUploadTaskResponse;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.List;

@Service
public class AiScoreUploadTaskService {
    private static final int DEFAULT_TERMINAL_LIMIT = 10;
    private static final int MAX_TERMINAL_LIMIT = 10;
    private static final int MAX_PUBLIC_ERROR_LENGTH = 160;
    private static final String SELECT = """
            SELECT s.id AS session_id,
                   s.session_no,
                   COALESCE(a.original_name, s.session_no) AS file_name,
                   COALESCE(a.size_bytes, 0) AS file_size,
                   s.project_id,
                   s.team_id,
                   COALESCE(t.name, '未命名团队') AS team_name,
                   s.track_name,
                   s.status,
                   s.current_stage,
                   COALESCE(s.progress_percent, 0) AS progress_percent,
                   s.use_history_memory,
                   s.jury_enabled,
                   s.report_id,
                   s.error_message,
                   s.created_at,
                   s.updated_at
            FROM ai_scoring_session s
            LEFT JOIN ai_score_media_asset a ON a.id = (
                SELECT MIN(a2.id)
                FROM ai_score_media_asset a2
                WHERE a2.session_id = s.id AND a2.asset_type = 'video'
            )
            LEFT JOIN project_team t ON t.id = s.team_id
            WHERE s.created_by = ?
              AND s.source_type = 'uploaded_video'
            """;

    private final JdbcTemplate jdbc;

    public AiScoreUploadTaskService(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public List<AiScoreUploadTaskResponse> listForUser(Long userId, Integer completedLimit) {
        if (userId == null) {
            throw new IllegalArgumentException("用户身份不能为空");
        }
        int limit = completedLimit == null
                ? DEFAULT_TERMINAL_LIMIT
                : Math.max(0, Math.min(MAX_TERMINAL_LIMIT, completedLimit));
        List<AiScoreUploadTaskResponse> result = new ArrayList<>(jdbc.query(
                SELECT + """
                          AND COALESCE(s.status, 'created') NOT IN ('completed', 'failed', 'cancelled')
                        ORDER BY s.created_at DESC, s.id DESC
                        """,
                this::mapTask,
                userId
        ));
        if (limit > 0) {
            result.addAll(jdbc.query(
                    SELECT + """
                              AND s.status IN ('completed', 'failed', 'cancelled')
                            ORDER BY s.created_at DESC, s.id DESC
                            LIMIT ?
                            """,
                    this::mapTask,
                    userId,
                    limit
            ));
        }
        return result;
    }

    private AiScoreUploadTaskResponse mapTask(ResultSet rs, int rowNum) throws SQLException {
        return new AiScoreUploadTaskResponse(
                rs.getLong("session_id"),
                rs.getString("session_no"),
                rs.getString("file_name"),
                rs.getLong("file_size"),
                nullableLong(rs, "project_id"),
                nullableLong(rs, "team_id"),
                rs.getString("team_name"),
                rs.getString("track_name"),
                rs.getString("status"),
                rs.getString("current_stage"),
                Math.max(0, Math.min(100, rs.getInt("progress_percent"))),
                rs.getBoolean("use_history_memory"),
                rs.getBoolean("jury_enabled"),
                nullableLong(rs, "report_id"),
                truncate(rs.getString("error_message")),
                rs.getTimestamp("created_at") == null
                        ? null : rs.getTimestamp("created_at").toLocalDateTime(),
                rs.getTimestamp("updated_at") == null
                        ? null : rs.getTimestamp("updated_at").toLocalDateTime()
        );
    }

    private Long nullableLong(ResultSet rs, String column) throws SQLException {
        long value = rs.getLong(column);
        return rs.wasNull() ? null : value;
    }

    private String truncate(String value) {
        if (value == null || value.length() <= MAX_PUBLIC_ERROR_LENGTH) {
            return value;
        }
        return value.substring(0, MAX_PUBLIC_ERROR_LENGTH);
    }
}
```

- [ ] **Step 5: 运行服务测试并确认 GREEN**

Run:

```bash
cd backend
mvn -Dtest=AiScoreUploadTaskServiceTest test
```

Expected: `Tests run: 2, Failures: 0, Errors: 0`。

- [ ] **Step 6: 验证检查点**

确认本任务只新增 DTO、查询服务和服务测试；运行 `rg -n "filePath|rubric|hash" backend/src/main/java/com/orep/backend/dto/AiScoreUploadTaskResponse.java`，Expected: 无匹配。

---

### Task 2: 认证用户任务队列接口

**Files:**

- Modify: `backend/src/main/java/com/orep/backend/controller/AiScoreUploadController.java`
- Modify: `backend/src/test/java/com/orep/backend/controller/AiScoreUploadControllerWebMvcTest.java`
- Test: `backend/src/test/java/com/orep/backend/controller/AiScoreUploadTaskControllerTest.java`

- [ ] **Step 1: 写入控制器失败测试**

创建 `AiScoreUploadTaskControllerTest.java`：

```java
package com.orep.backend.controller;

import com.orep.backend.dto.AiScoreUploadTaskResponse;
import com.orep.backend.service.AiScoreAccessControlService;
import com.orep.backend.service.AiScoreMediaAssetService;
import com.orep.backend.service.AiScoreUploadTaskService;
import com.orep.backend.service.AiScoringPipelineClient;
import com.orep.backend.service.AiScoringSessionService;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;

import java.time.LocalDateTime;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class AiScoreUploadTaskControllerTest {
    @Test
    void listsTasksForAuthenticatedUserAndClampsTerminalLimitInService() {
        AiScoreUploadTaskService taskService = mock(AiScoreUploadTaskService.class);
        AiScoreUploadTaskResponse task = new AiScoreUploadTaskResponse(
                101L, "SC-101", "路演.mp4", 1000L, 3L, 9L, "应用攻坚队",
                "新一代信息技术赛道", "scoring", "model_scoring", 46,
                true, false, null, null, LocalDateTime.now(), LocalDateTime.now()
        );
        when(taskService.listForUser(7L, 10)).thenReturn(List.of(task));
        AiScoreUploadController controller = new AiScoreUploadController(
                mock(AiScoringSessionService.class),
                mock(AiScoreMediaAssetService.class),
                mock(AiScoreAccessControlService.class),
                mock(AiScoringPipelineClient.class),
                "./uploads",
                taskService
        );
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.setAttribute("userId", 7L);

        var result = controller.listUploadTasks(10, request);

        assertEquals(200, result.getCode());
        assertEquals(101L, result.getData().getFirst().sessionId());
        verify(taskService).listForUser(7L, 10);
    }
}
```

- [ ] **Step 2: 运行测试并确认 RED**

Run:

```bash
cd backend
mvn -Dtest=AiScoreUploadTaskControllerTest test
```

Expected: 编译失败，提示六参数测试构造器和 `listUploadTasks` 不存在。

- [ ] **Step 3: 注入服务并增加接口**

在 `AiScoreUploadController` 中：

```java
import com.orep.backend.dto.AiScoreUploadTaskResponse;
import com.orep.backend.service.AiScoreUploadTaskService;
```

增加字段：

```java
private final AiScoreUploadTaskService uploadTaskService;
```

保留现有五参数测试构造器，并让它委托给新增六参数测试构造器：

```java
public AiScoreUploadController(AiScoringSessionService scoringSessionService,
                               AiScoreMediaAssetService mediaAssetService,
                               AiScoreAccessControlService accessControlService,
                               AiScoringPipelineClient pipelineClient,
                               String uploadDir) {
    this(scoringSessionService, mediaAssetService, accessControlService, pipelineClient,
            uploadDir, null);
}

public AiScoreUploadController(AiScoringSessionService scoringSessionService,
                               AiScoreMediaAssetService mediaAssetService,
                               AiScoreAccessControlService accessControlService,
                               AiScoringPipelineClient pipelineClient,
                               String uploadDir,
                               AiScoreUploadTaskService uploadTaskService) {
    this(scoringSessionService, mediaAssetService, accessControlService, pipelineClient,
            uploadTaskService, uploadDir, "http://127.0.0.1:8080", "");
}
```

将生产构造器签名和赋值改为：

```java
@Autowired
public AiScoreUploadController(AiScoringSessionService scoringSessionService,
                               AiScoreMediaAssetService mediaAssetService,
                               AiScoreAccessControlService accessControlService,
                               AiScoringPipelineClient pipelineClient,
                               AiScoreUploadTaskService uploadTaskService,
                               @Value("${file.upload-dir:./uploads}") String uploadDir,
                               @Value("${recording.callback.base-url:http://127.0.0.1:8080}") String callbackBaseUrl,
                               @Value("${ai-scoring.file-root:}") String aiScoringFileRoot) {
    this.scoringSessionService = scoringSessionService;
    this.mediaAssetService = mediaAssetService;
    this.accessControlService = accessControlService;
    this.pipelineClient = pipelineClient;
    this.uploadTaskService = uploadTaskService;
    this.uploadDir = Path.of(uploadDir).toAbsolutePath().normalize().toString();
    this.callbackBaseUrl = callbackBaseUrl == null || callbackBaseUrl.isBlank()
            ? "http://127.0.0.1:8080"
            : callbackBaseUrl.trim().replaceAll("/+$", "");
    this.aiScoringFileRoot = aiScoringFileRoot == null ? "" : aiScoringFileRoot.trim();
}
```

在上传接口前增加：

```java
@GetMapping("/upload-tasks")
public Result<List<AiScoreUploadTaskResponse>> listUploadTasks(
        @RequestParam(value = "completedLimit", defaultValue = "10") Integer completedLimit,
        HttpServletRequest request) {
    Long userId = attrLong(request, "userId");
    if (userId == null) {
        return Result.error(401, "用户未登录");
    }
    return Result.success(uploadTaskService.listForUser(userId, completedLimit));
}
```

- [ ] **Step 4: 补齐 Spring MVC 测试依赖**

在 `AiScoreUploadControllerWebMvcTest.java` 中增加：

```java
import com.orep.backend.service.AiScoreUploadTaskService;
```

以及：

```java
@MockBean
private AiScoreUploadTaskService uploadTaskService;
```

- [ ] **Step 5: 运行控制器与既有上传测试并确认 GREEN**

Run:

```bash
cd backend
mvn -Dtest=AiScoreUploadTaskControllerTest,AiScoreUploadControllerWebMvcTest,AiScoreUploadControllerTest,AiScoreResponseRedactionTest test
```

Expected: 所列测试全部通过，且既有五参数测试构造器仍可编译。

- [ ] **Step 6: 运行后端完整测试检查接口装配**

Run:

```bash
cd backend
mvn test
```

Expected: `BUILD SUCCESS`，无 Spring Bean 缺失错误。

- [ ] **Step 7: 验证检查点**

确认接口路径只有 `GET /api/ai-score/upload-tasks`，身份只来自 `request.getAttribute("userId")`，请求参数中没有 `userId`、`createdBy` 或文件路径。

---

### Task 3: 前端任务获取与生命周期轮询

**Files:**

- Modify: `frontend/user/src/utils/aiScoreUpload.js`
- Create: `frontend/user/src/composables/useAiScoreUploadQueue.js`
- Test: `frontend/user/tests/ai-score-upload-task-queue.spec.js`

- [ ] **Step 1: 写入队列刷新恢复失败测试**

先创建 `ai-score-upload-task-queue.spec.js` 的基础路由与刷新用例：

```javascript
import { expect, test } from '@playwright/test'

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('orep_user_token', 'upload-queue-token')
    localStorage.setItem('orep_user', JSON.stringify({ username: '张申', role: 'STUDENT' }))
  })
  await page.route('**/api/project-teams/my', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      code: 200,
      data: [{ id: 9, name: '应用攻坚队', myRoleInTeam: 'CAPTAIN' }]
    })
  }))
})

test('刷新后从服务端恢复进行中和最近完成任务', async ({ page }) => {
  let queueRequests = 0
  await page.route('**/api/ai-score/upload-tasks?completedLimit=10', route => {
    queueRequests += 1
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        code: 200,
        data: [
          {
            sessionId: 101,
            sessionNo: 'SC-101',
            fileName: '决赛路演.mp4',
            fileSize: 52428800,
            projectId: 3,
            teamId: 9,
            teamName: '应用攻坚队',
            trackName: '新一代信息技术赛道',
            status: 'scoring',
            currentStage: 'model_scoring',
            progressPercent: 46,
            useHistoryMemory: true,
            juryEnabled: false,
            reportId: null,
            errorMessage: null,
            createdAt: '2026-07-30T09:00:00',
            updatedAt: '2026-07-30T09:03:00'
          },
          {
            sessionId: 100,
            sessionNo: 'SC-100',
            fileName: '初赛路演.mp4',
            fileSize: 10485760,
            projectId: 3,
            teamId: 9,
            teamName: '应用攻坚队',
            trackName: '新一代信息技术赛道',
            status: 'completed',
            currentStage: 'completed',
            progressPercent: 100,
            useHistoryMemory: true,
            juryEnabled: false,
            reportId: 901,
            errorMessage: null,
            createdAt: '2026-07-29T09:00:00',
            updatedAt: '2026-07-29T09:15:00'
          }
        ]
      })
    })
  })

  await page.goto('/ai-score-upload')
  await expect(page.getByRole('heading', { name: '评分任务', level: 2 })).toBeVisible()
  await expect(page.getByText('决赛路演.mp4', { exact: true })).toBeVisible()
  await expect(page.getByText('46%', { exact: true })).toBeVisible()
  await expect(page.getByRole('link', { name: '查看报告' })).toHaveAttribute(
    'href',
    '/ai-score/report/100'
  )

  await page.reload()
  await expect(page.getByText('决赛路演.mp4', { exact: true })).toBeVisible()
  expect(queueRequests).toBeGreaterThanOrEqual(2)
})
```

- [ ] **Step 2: 运行用例并确认 RED**

Run:

```bash
cd frontend/user
npx playwright test tests/ai-score-upload-task-queue.spec.js --project=chromium
```

Expected: 失败，页面不存在“评分任务”标题，也没有请求 `/api/ai-score/upload-tasks`。

- [ ] **Step 3: 增加前端请求函数**

在 `aiScoreUpload.js` 末尾增加：

```javascript
export async function getAiScoreUploadTasks(completedLimit = 10) {
  return unwrap(await request.get(uploadUrl('/api/ai-score/upload-tasks'), {
    params: { completedLimit }
  }))
}
```

- [ ] **Step 4: 实现队列组合式函数**

创建 `useAiScoreUploadQueue.js`：

```javascript
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { getAiScoreUploadTasks } from '../utils/aiScoreUpload'

const POLL_INTERVAL_MS = 3000
const MAX_CONSECUTIVE_FAILURES = 2
const TERMINAL_STATUSES = new Set(['completed', 'failed', 'cancelled'])

export function useAiScoreUploadQueue() {
  const tasks = ref([])
  const loading = ref(true)
  const syncing = ref(false)
  const error = ref('')
  let timer = 0
  let requestInFlight = false
  let consecutiveFailures = 0

  const hasActiveTasks = computed(() => tasks.value.some(task =>
    !TERMINAL_STATUSES.has(String(task.status || '').toLowerCase())
  ))

  async function refresh({ silent = false } = {}) {
    if (requestInFlight) return
    requestInFlight = true
    if (silent) syncing.value = true
    else loading.value = true
    try {
      const data = await getAiScoreUploadTasks(10)
      tasks.value = Array.isArray(data) ? data : []
      error.value = ''
      consecutiveFailures = 0
    } catch (requestError) {
      if (!tasks.value.length) {
        error.value = requestError?.message || '评分任务加载失败，请稍后重试'
      }
      consecutiveFailures += 1
    } finally {
      requestInFlight = false
      loading.value = false
      syncing.value = false
      schedule()
    }
  }

  function schedule() {
    window.clearTimeout(timer)
    if (
      !document.hidden
      && hasActiveTasks.value
      && consecutiveFailures < MAX_CONSECUTIVE_FAILURES
    ) {
      timer = window.setTimeout(() => refresh({ silent: true }), POLL_INTERVAL_MS)
    }
  }

  function mergeUploadedSession(session) {
    if (!session?.sessionId) return
    const optimisticTask = {
      sessionId: session.sessionId,
      sessionNo: session.sessionNo,
      fileName: session.fileName || session.sessionNo || '新上传的路演视频',
      fileSize: Number(session.fileSize) || 0,
      projectId: session.projectId,
      teamId: session.teamId,
      teamName: session.teamName || '正在同步团队',
      trackName: session.trackName,
      status: session.status || 'scoring',
      currentStage: session.currentStage || 'queued',
      progressPercent: Number(session.progressPercent) || 0,
      useHistoryMemory: session.useHistoryMemory !== false,
      juryEnabled: session.juryEnabled === true,
      reportId: session.reportId,
      errorMessage: session.errorMessage || null,
      createdAt: session.createdAt || new Date().toISOString(),
      updatedAt: session.updatedAt || new Date().toISOString()
    }
    tasks.value = [
      optimisticTask,
      ...tasks.value.filter(task => task.sessionId !== session.sessionId)
    ]
    schedule()
  }

  function handleVisibilityChange() {
    if (document.hidden) {
      window.clearTimeout(timer)
      return
    }
    refresh({ silent: true })
  }

  function handleFocus() {
    if (!document.hidden) refresh({ silent: true })
  }

  onMounted(() => {
    document.addEventListener('visibilitychange', handleVisibilityChange)
    window.addEventListener('focus', handleFocus)
    refresh()
  })

  onUnmounted(() => {
    window.clearTimeout(timer)
    document.removeEventListener('visibilitychange', handleVisibilityChange)
    window.removeEventListener('focus', handleFocus)
  })

  return {
    tasks,
    loading,
    syncing,
    error,
    hasActiveTasks,
    refresh,
    mergeUploadedSession
  }
}
```

- [ ] **Step 5: 暂时在页面挂载组合式函数以驱动测试请求**

在 `VideoScoreUpload.vue` 的脚本中导入并调用：

```javascript
import { useAiScoreUploadQueue } from '../composables/useAiScoreUploadQueue'

const {
  tasks,
  loading: queueLoading,
  syncing: queueSyncing,
  error: queueError,
  refresh: refreshQueue,
  mergeUploadedSession
} = useAiScoreUploadQueue()
```

本步骤只负责建立数据生命周期；模板在 Task 4 一次性替换，当前 Playwright 用例仍应因缺少队列组件而失败，但网络面板应已能观察到队列请求。

- [ ] **Step 6: 验证轮询边界**

在 Playwright 用例末尾临时增加并运行：

```javascript
await page.waitForTimeout(3200)
expect(queueRequests).toBeGreaterThanOrEqual(3)
```

Expected: 活跃任务存在时发生下一次请求。然后将模拟数据改为空数组再次运行 3.2 秒，Expected: 请求总数保持 1。再让路由连续返回两次 500，Expected: 第二次失败后不再高频请求。确认后保留“活跃任务轮询”和“连续失败停止高频重试”断言，删除空数组临时改动。

- [ ] **Step 7: 验证检查点**

确认组合式函数在 `document.hidden` 时清除定时器，在重新可见和窗口聚焦时立即刷新，并用 `requestInFlight` 阻止并发重复请求。

---

### Task 4: B+ 页面、紧凑上传区与全宽任务队列

**Files:**

- Create: `frontend/user/src/components/ai-score/AiScoreUploadTaskQueue.vue`
- Modify: `frontend/user/src/components/ai-score/VideoScoreUploadForm.vue`
- Modify: `frontend/user/src/views/VideoScoreUpload.vue`
- Modify: `frontend/user/tests/ai-score-upload-task-queue.spec.js`
- Modify: `frontend/user/tests/review-pages-design.spec.js`

- [ ] **Step 1: 扩充失败测试，锁定视觉与交互契约**

在 `ai-score-upload-task-queue.spec.js` 增加以下用例：

```javascript
test('页面采用紧凑上传区和全宽队列，不再出现重复状态卡', async ({ page }) => {
  await page.route('**/api/ai-score/upload-tasks?completedLimit=10', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ code: 200, data: [] })
  }))
  await page.setViewportSize({ width: 1288, height: 892 })
  await page.goto('/ai-score-upload')

  await expect(page.getByRole('heading', { name: '上传评分', level: 1 })).toBeVisible()
  await expect(page.getByRole('heading', { name: '评分任务', level: 2 })).toBeVisible()
  await expect(page.getByText('处理流程', { exact: true })).toHaveCount(0)
  await expect(page.getByText('当前状态', { exact: true })).toHaveCount(0)
  await expect(page.locator('.session-strip, .analysis-panel, .upload-side')).toHaveCount(0)
  await expect(page.getByRole('button', { name: '评分偏好' })).toHaveAttribute('aria-expanded', 'false')

  const metrics = await page.locator('.video-score-page').evaluate(root => {
    const rootStyle = getComputedStyle(root)
    const transferTrack = root.querySelector('.upload-transfer__track')
    const queue = root.querySelector('.score-task-queue')
    const form = root.querySelector('.upload-main-card')
    return {
      padding: rootStyle.padding,
      backgroundColor: rootStyle.backgroundColor,
      queueWidth: queue.getBoundingClientRect().width,
      formWidth: form.getBoundingClientRect().width,
      transferHeight: transferTrack ? getComputedStyle(transferTrack).height : null,
      noOverflow: document.documentElement.scrollWidth <= window.innerWidth
    }
  })
  expect(metrics.padding).toBe('0px')
  expect(metrics.backgroundColor).toBe('rgba(0, 0, 0, 0)')
  expect(Math.abs(metrics.queueWidth - metrics.formWidth)).toBeLessThanOrEqual(1)
  expect(metrics.noOverflow).toBe(true)
})

test('失败任务可回填团队赛道但要求重新选择本地视频', async ({ page }) => {
  await page.route('**/api/ai-score/upload-tasks?completedLimit=10', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      code: 200,
      data: [{
        sessionId: 201,
        sessionNo: 'SC-201',
        fileName: '失败路演.mp4',
        fileSize: 1000,
        projectId: 3,
        teamId: 9,
        teamName: '应用攻坚队',
        trackName: '新一代信息技术赛道',
        status: 'failed',
        currentStage: 'failed',
        progressPercent: 67,
        useHistoryMemory: false,
        juryEnabled: true,
        reportId: null,
        errorMessage: '视频中未检测到可用音轨',
        createdAt: '2026-07-30T09:00:00',
        updatedAt: '2026-07-30T09:03:00'
      }]
    })
  }))
  await page.goto('/ai-score-upload')

  await expect(page.getByText('视频中未检测到可用音轨')).toBeVisible()
  await page.getByRole('button', { name: '重新上传' }).click()
  await expect(page.getByRole('combobox', { name: '项目团队' })).toHaveValue('9')
  await expect(page.getByRole('button', { name: '评分偏好' })).toHaveAttribute('aria-expanded', 'true')
  await expect(page.getByText('请重新选择本地视频文件')).toBeVisible()
})

test('窄屏任务行纵向排布且没有横向溢出', async ({ page }) => {
  await page.route('**/api/ai-score/upload-tasks?completedLimit=10', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ code: 200, data: [] })
  }))
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/ai-score-upload')
  await expect(page.getByRole('heading', { name: '评分任务', level: 2 })).toBeVisible()
  expect(await page.evaluate(() =>
    document.documentElement.scrollWidth <= window.innerWidth
  )).toBe(true)
})
```

- [ ] **Step 2: 运行页面用例并确认 RED**

Run:

```bash
cd frontend/user
npx playwright test tests/ai-score-upload-task-queue.spec.js --project=chromium
```

Expected: “评分任务”、折叠偏好、全宽队列和移除旧状态区相关断言失败。

- [ ] **Step 3: 创建任务队列组件**

创建 `AiScoreUploadTaskQueue.vue`，模板必须包含以下完整状态分支：

```vue
<template>
  <section class="score-task-queue" aria-labelledby="score-task-title">
    <header class="score-task-queue__head">
      <div>
        <h2 id="score-task-title">评分任务</h2>
        <p>分析任务会持续保留，刷新或重新登录后仍可查看。</p>
      </div>
      <button
        class="score-task-queue__refresh"
        type="button"
        :disabled="syncing"
        @click="$emit('reload')"
      >
        {{ syncing ? '同步中' : '刷新' }}
      </button>
    </header>

    <div v-if="loading" class="score-task-queue__state" aria-live="polite">正在加载评分任务…</div>
    <div v-else-if="error" class="score-task-queue__state is-error">
      <p>{{ error }}</p>
      <BaseButton type="secondary" @click="$emit('reload')">重新加载</BaseButton>
    </div>
    <div v-else-if="!tasks.length" class="score-task-queue__state">
      <strong>还没有评分任务</strong>
      <p>选择路演视频并开始上传后，分析进度会显示在这里。</p>
    </div>
    <ul v-else class="score-task-list">
      <li v-for="task in tasks" :key="task.sessionId" class="score-task">
        <div class="score-task__identity">
          <strong :title="task.fileName">{{ task.fileName || task.sessionNo }}</strong>
          <span>{{ task.teamName }} · {{ task.trackName || '未选择赛道' }}</span>
          <time :datetime="task.createdAt">{{ formatTime(task.createdAt) }}</time>
        </div>
        <div class="score-task__progress">
          <div class="score-task__status">
            <span :class="`is-${statusModel(task).tone}`">{{ statusModel(task).label }}</span>
            <b>{{ progress(task) }}%</b>
          </div>
          <div
            class="score-task__track"
            role="progressbar"
            aria-valuemin="0"
            aria-valuemax="100"
            :aria-valuenow="progress(task)"
            :aria-label="`${task.fileName || task.sessionNo}分析进度`"
          >
            <i :style="{ width: `${progress(task)}%` }"></i>
          </div>
          <p v-if="task.errorMessage" class="score-task__error">{{ task.errorMessage }}</p>
        </div>
        <div class="score-task__action">
          <BaseButton
            v-if="task.status === 'completed' && task.reportId"
            type="secondary"
            :to="`/ai-score/report/${task.sessionId}`"
          >
            查看报告
          </BaseButton>
          <BaseButton
            v-else-if="task.status === 'failed'"
            type="secondary"
            @click="$emit('retry', task)"
          >
            重新上传
          </BaseButton>
          <span v-else class="score-task__passive">系统处理中</span>
        </div>
      </li>
    </ul>
  </section>
</template>

<script setup>
import BaseButton from '../base/BaseButton.vue'

defineProps({
  tasks: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  syncing: { type: Boolean, default: false },
  error: { type: String, default: '' }
})

defineEmits(['reload', 'retry'])

const STAGES = {
  created: '等待上传',
  uploaded: '等待分析',
  queued: '排队中',
  audio_extracting: '提取音频',
  asr_processing: '识别讲解内容',
  frame_extracting: '提取画面',
  ocr_processing: '识别展示内容',
  evidence_building: '整理评分证据',
  model_scoring: 'AI 评分中',
  rule_calibrating: '校准评分',
  report_generating: '生成报告',
  completed: '已完成',
  failed: '处理失败',
  cancelled: '已取消'
}

function progress(task) {
  return Math.max(0, Math.min(100, Number(task.progressPercent) || 0))
}

function statusModel(task) {
  if (task.status === 'completed') return { label: '已完成', tone: 'success' }
  if (task.status === 'failed') return { label: '处理失败', tone: 'danger' }
  if (task.status === 'cancelled') return { label: '已取消', tone: 'muted' }
  return {
    label: STAGES[task.currentStage] || STAGES[task.status] || '处理中',
    tone: 'active'
  }
}

function formatTime(value) {
  if (!value) return '时间待同步'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '时间待同步'
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  }).format(date)
}
</script>
```

样式只使用 `--ds-*` 令牌，关键尺寸固定为：

```css
.score-task-queue {
  width: 100%;
  border: 1px solid var(--ds-card-border);
  border-radius: var(--ds-radius-lg);
  background: var(--ds-card-bg);
  box-shadow: var(--ds-card-shadow);
  overflow: hidden;
}

.score-task-queue__head,
.score-task {
  padding: var(--ds-space-5) var(--ds-space-6);
}

.score-task {
  display: grid;
  grid-template-columns: minmax(220px, 1.4fr) minmax(260px, 1fr) auto;
  gap: var(--ds-space-6);
  align-items: center;
  border-top: 1px solid var(--ds-line);
}

.score-task__track {
  height: 4px;
  overflow: hidden;
  border-radius: 999px;
  background: var(--ds-line);
}

.score-task__track i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--ds-orange-action);
  transition: width 240ms ease;
}

@media (max-width: 720px) {
  .score-task-queue__head,
  .score-task {
    padding: var(--ds-space-4);
  }

  .score-task {
    grid-template-columns: 1fr;
    gap: var(--ds-space-4);
  }

  .score-task__action .base-button {
    width: 100%;
  }
}
```

- [ ] **Step 4: 压缩上传表单并支持失败任务回填**

在 `VideoScoreUploadForm.vue` 增加 prop：

```javascript
const props = defineProps({
  retryContext: {
    type: Object,
    default: null
  }
})
```

将 Vue 导入补充 `watch`，增加偏好状态：

```javascript
const preferencesExpanded = ref(false)
const retryHint = ref('')

watch(() => props.retryContext, context => {
  if (!context) return
  if (context.teamId) form.teamId = String(context.teamId)
  if (context.trackName) form.trackName = context.trackName
  form.useHistoryMemory = context.useHistoryMemory !== false
  form.juryEnabled = context.juryEnabled === true
  preferencesExpanded.value = true
  retryHint.value = '已恢复上次的团队、赛道和评分偏好，请重新选择本地视频文件。'
  videoFile.value = null
}, { deep: true })
```

将两个平铺复选框替换为可访问折叠区：

```vue
<div class="score-preferences">
  <button
    type="button"
    class="score-preferences__toggle"
    :aria-expanded="String(preferencesExpanded)"
    aria-controls="score-preferences-panel"
    @click="preferencesExpanded = !preferencesExpanded"
  >
    <span>评分偏好</span>
    <small>历史评分记忆、AI 评审团</small>
  </button>
  <div v-if="preferencesExpanded" id="score-preferences-panel" class="score-preferences__panel">
    <label>
      <input v-model="form.useHistoryMemory" type="checkbox">
      引用历史评分记忆
    </label>
    <label>
      <input v-model="form.juryEnabled" type="checkbox">
      启用 AI 评审团复核
    </label>
  </div>
</div>
<p v-if="retryHint" class="retry-hint" role="status">{{ retryHint }}</p>
```

上传控件调整为紧凑文件行，保留：

- 路演视频格式与 5GB 上限；
- 佐证材料可选、单个 200MB、合计 1GB；
- 已选文件名与移除动作；
- 原有上传校验、预处理、真实速度和剩余时间计算。

删除“处理流程”的重复说明，把提交按钮文案改为：

```vue
<BaseButton type="primary" native-type="submit" :disabled="submitting">
  {{ submitting ? '正在上传' : '开始上传评分' }}
</BaseButton>
```

在现有 `pickVideo` 开头清空 `retryHint`，并保留原有大小校验与状态上报：

```javascript
function pickVideo(event) {
  retryHint.value = ''
  error.value = ''
  const selected = event.target.files?.[0] || null
  if (selected && selected.size > MAX_VIDEO_BYTES) {
    videoFile.value = null
    event.target.value = ''
    error.value = '路演视频最大5GB，请压缩后上传'
    emit('status-change', { status: 'failed', progress: 0 })
    return
  }
  videoFile.value = selected
  if (videoFile.value) {
    resetUploadTelemetry()
    emit('status-change', {
      status: 'selected',
      progress: 10,
      stage: '文件已选择',
      totalBytes: videoFile.value.size,
      loadedBytes: 0
    })
  }
}
```

- [ ] **Step 5: 用 B+ 页面结构替换旧模板和状态逻辑**

将 `VideoScoreUpload.vue` 的页面模板收敛为：

```vue
<template>
  <div class="video-score-page">
    <header class="upload-page-head">
      <div>
        <h1>上传评分</h1>
        <p>上传路演视频，系统会持续分析并生成评分报告。</p>
      </div>
      <BaseButton type="secondary" to="/online-meeting?tab=reports">返回评分报告</BaseButton>
    </header>

    <section ref="uploadCard" class="upload-main-card">
      <div class="section-title">
        <h2>上传材料</h2>
        <p>确认团队与赛道后选择路演视频；佐证材料可选。</p>
      </div>
      <VideoScoreUploadForm
        :retry-context="retryContext"
        @status-change="handleStatusChange"
        @uploaded="handleUploaded"
      />
      <div v-if="hasUploadBytes" class="upload-transfer" aria-live="polite">
        <div class="upload-transfer__head">
          <span>{{ uploadMeta.stage || '正在上传' }}</span>
          <b>{{ uploadProgress }}%</b>
        </div>
        <div
          class="upload-transfer__track"
          role="progressbar"
          aria-label="本地文件上传进度"
          aria-valuemin="0"
          aria-valuemax="100"
          :aria-valuenow="uploadProgress"
        >
          <i :style="{ width: `${uploadProgress}%` }"></i>
        </div>
        <p>{{ uploadedBytesText }} / {{ totalBytesText }} · {{ uploadSpeedText }} · 预计剩余 {{ remainingText }}</p>
      </div>
    </section>

    <AiScoreUploadTaskQueue
      :tasks="tasks"
      :loading="queueLoading"
      :syncing="queueSyncing"
      :error="queueError"
      @reload="refreshQueue"
      @retry="retryTask"
    />
  </div>
</template>
```

脚本保留本地上传格式化函数，删除：

- `getAiScoreSessionStatus` 导入；
- `createdSession`、`pipelineStatus`、`pipelineStage`、`pipelineProgress`；
- `pipelinePollingTimer` 及全部单会话轮询函数；
- `progressTitle`、`progressText`、`analysisTitle`、`analysisText`；
- `openReport` 和旧路由跳转。

增加：

```javascript
import { nextTick, ref } from 'vue'
import AiScoreUploadTaskQueue from '../components/ai-score/AiScoreUploadTaskQueue.vue'

const uploadCard = ref(null)
const retryContext = ref(null)

async function handleUploaded(session) {
  uploadStatus.value = 'completed'
  uploadProgress.value = 100
  mergeUploadedSession(session)
  await refreshQueue()
}

async function retryTask(task) {
  retryContext.value = {
    ...task,
    retryKey: `${task.sessionId}-${Date.now()}`
  }
  await nextTick()
  uploadCard.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}
```

页面样式遵循：

```css
.video-score-page {
  width: 100%;
  padding: 0;
  margin: 0;
  background: transparent;
}

.upload-page-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--ds-space-6);
  margin-bottom: var(--ds-space-5);
}

.upload-main-card {
  width: 100%;
  padding: var(--ds-space-6);
  border: 1px solid var(--ds-card-border);
  border-radius: var(--ds-radius-lg);
  background: var(--ds-card-bg);
  box-shadow: var(--ds-card-shadow);
}

.score-task-queue {
  margin-top: var(--ds-space-5);
}

.upload-transfer__track {
  height: 4px;
  overflow: hidden;
  border-radius: 999px;
  background: var(--ds-line);
}

@media (max-width: 720px) {
  .upload-page-head {
    flex-direction: column;
  }

  .upload-main-card {
    padding: var(--ds-space-4);
  }
}
```

不得给 `.video-score-page`、`.upload-shell` 或其替代根容器添加 padding、渐变背景或 max-width；外部上下左右间距由 `.workspace-main` 统一提供。

- [ ] **Step 6: 更新旧设计测试**

将 `review-pages-design.spec.js` 中“上传评分页采用与训练营一致的主辅栏并移除重复空闲进度”改为：

```javascript
test('上传评分页采用全宽任务队列并由工作区统一提供外边距', async ({ page }) => {
  await page.route('**/api/ai-score/upload-tasks?completedLimit=10', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ code: 200, data: [] })
  }))
  await page.setViewportSize({ width: 1288, height: 892 })
  await page.goto('/ai-score-upload')

  await expect(page.getByRole('heading', { name: '上传评分', level: 1 })).toBeVisible()
  await expect(page.getByRole('heading', { name: '评分任务', level: 2 })).toBeVisible()
  await expect(page.getByRole('link', { name: '返回评分报告' })).toHaveAttribute(
    'href',
    '/online-meeting?tab=reports'
  )
  const metrics = await page.locator('.video-score-page').evaluate(root => {
    const main = document.querySelector('.workspace-main')
    const rootRect = root.getBoundingClientRect()
    const mainStyle = getComputedStyle(main)
    const expectedLeft = main.getBoundingClientRect().left + parseFloat(mainStyle.paddingLeft)
    return {
      rootPadding: getComputedStyle(root).padding,
      leftDelta: Math.abs(rootRect.left - expectedLeft),
      noOverflow: document.documentElement.scrollWidth <= window.innerWidth
    }
  })
  expect(metrics.rootPadding).toBe('0px')
  expect(metrics.leftDelta).toBeLessThanOrEqual(1)
  expect(metrics.noOverflow).toBe(true)
})
```

在 `beforeEach` 中统一添加空队列 mock，避免每个旧用例意外访问真实后端：

```javascript
await page.route('**/api/ai-score/upload-tasks?completedLimit=10', route => route.fulfill({
  status: 200,
  contentType: 'application/json',
  body: JSON.stringify({ code: 200, data: [] })
}))
```

窄屏旧用例删除 `.upload-side` 位置断言，改为队列可见与无溢出断言。

- [ ] **Step 7: 运行页面测试并确认 GREEN**

Run:

```bash
cd frontend/user
npx playwright test tests/ai-score-upload-task-queue.spec.js tests/review-pages-design.spec.js --project=chromium
```

Expected: 所有用例通过；队列从 API 恢复，完成任务可进入报告，失败任务可回填上下文，390px 和 1288px 均无横向溢出。

- [ ] **Step 8: 验证设计令牌与冗余节点**

Run:

```bash
rg -n "#[0-9a-fA-F]{3,8}|linear-gradient|radial-gradient" \
  frontend/user/src/views/VideoScoreUpload.vue \
  frontend/user/src/components/ai-score/AiScoreUploadTaskQueue.vue \
  frontend/user/src/components/ai-score/VideoScoreUploadForm.vue

rg -n "upload-side|analysis-panel|session-strip|处理流程|当前状态" \
  frontend/user/src/views/VideoScoreUpload.vue
```

Expected: 第一条不出现新增私有颜色或渐变；第二条无匹配。

---

### Task 5: 完整回归与真实浏览器验收

**Files:**

- Verify: `backend/src/main/java/com/orep/backend/**`
- Verify: `frontend/user/src/**`
- Verify: `frontend/user/tests/**`

- [ ] **Step 1: 运行后端任务队列专项测试**

Run:

```bash
cd backend
mvn -Dtest=AiScoreUploadTaskServiceTest,AiScoreUploadTaskControllerTest,AiScoreUploadControllerWebMvcTest,AiScoreUploadControllerTest,AiScoreResponseRedactionTest test
```

Expected: 全部通过，无响应泄露与构造器装配回归。

- [ ] **Step 2: 运行后端完整测试**

Run:

```bash
cd backend
mvn test
```

Expected: `BUILD SUCCESS`。

- [ ] **Step 3: 运行前端专项与既有评分页面测试**

Run:

```bash
cd frontend/user
npx playwright test \
  tests/ai-score-upload-task-queue.spec.js \
  tests/review-pages-design.spec.js \
  tests/ai-score-hardening.spec.js \
  --project=chromium
```

Expected: 所有用例通过。

- [ ] **Step 4: 构建前端**

Run:

```bash
cd frontend/user
npm run build
```

Expected: Vite 构建成功，无 Vue 模板、未使用变量或 CSS 解析错误。

- [ ] **Step 5: 真实浏览器桌面验收**

在本地服务已启动的情况下打开 `http://localhost:5174/ai-score-upload`，按顺序确认：

1. 页面标题、上传卡、任务队列左边缘一致；
2. 页面外边距与 `/online-meeting?tab=reports` 的工作区内容一致；
3. 上传区没有右侧说明栏、重复状态卡或“处理流程”；
4. 偏好默认折叠；
5. 选择视频后只出现一条 4px 本地上传进度；
6. 服务端接受上传后任务立即进入下方队列；
7. 刷新页面后任务仍存在并恢复分析进度；
8. 完成任务显示“查看报告”，失败任务显示原因和“重新上传”；
9. “返回评分报告”直达 `/online-meeting?tab=reports`。

- [ ] **Step 6: 真实浏览器窄屏验收**

将视口设为 390 × 844，确认：

1. 顶部动作换行但仍可点击；
2. 团队、赛道、文件选择和主按钮均不超出容器；
3. 任务行改为纵向结构；
4. 操作按钮占可用宽度；
5. 页面无横向滚动。

- [ ] **Step 7: 刷新与登录恢复验收**

使用一个实际分析中的 `uploaded_video` 会话：

1. 记录文件名与当前百分比；
2. 刷新页面，确认同一 `sessionId` 重新出现；
3. 退出并重新登录同一账号，确认任务仍出现；
4. 登录另一账号，确认看不到前一账号的任务；
5. 等待进度更新，确认队列按约 3 秒刷新；
6. 切到后台标签页，确认不持续轮询；返回后立即同步一次。

- [ ] **Step 8: 最终验收记录**

最终说明必须明确区分：

- 已实现：服务端接受上传后的分析任务持久恢复；
- 未包含：浏览器仍在传输原始文件时刷新后的断点续传；
- 队列范围：全部进行中任务 + 最近 10 条完成、失败或取消任务；
- 视觉结果：全局外边距统一，上传与队列全宽对齐，进度条为 4px。
