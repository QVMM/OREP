# 选题专家团接力链路 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把准备页“选题策划”从一次性 AI 输出升级为可追踪、可持久化、可重试的 OREP 选题专家团接力链路。

**Architecture:** 采用方案 B：一次 Mimo 联网模型调用返回完整结构化 JSON，同时包含 `agentSteps`、`directionScores`、`directions`、`questions`、`sources`。Java 后端负责异步运行、并发保护、持久化专家步骤、方向和运行状态；前端负责展示专家接力过程、方向评分矩阵、失败重试和下一步闭环。

**Tech Stack:** Vue 3 `<script setup>`、Element Plus、Java Spring Boot、JdbcTemplate、MySQL/H2、FastAPI、OpenAI Python SDK、Mimo 联网模型、pytest、JUnit、Maven、Vite。

---

## 文件结构

- Modify: `backend/src/main/resources/sql/create_project_preparation_tables.sql`
  - 新增 `project_prep_agent_step`，保存每轮 AI 的专家接力步骤。
  - 扩展 `project_prep_direction`，保存方向评分、推荐等级、专家引用摘要。
- Modify: `backend/src/main/java/com/orep/backend/dto/ProjectPreparationAiResponse.java`
  - 增加 `AgentStep`、`DirectionScore` DTO。
  - 给 `Direction` 增加 `scores`、`recommendationLevel`、`expertRationale`。
- Modify: `backend/src/main/java/com/orep/backend/service/ProjectPreparationService.java`
  - schema 自动升级。
  - AI 请求上下文增加专家团版本字段。
  - AI 成功后保存 `agentSteps`。
  - session payload 返回 `agentSteps`、方向评分、最新 run 状态。
  - 并发逻辑保留“一会话一运行”，补充已运行中的用户提示和 stale run 保护。
- Modify: `backend/src/main/java/com/orep/backend/service/ProjectPreparationAiClient.java`
  - 保持现有超时配置，增强空响应和协议异常错误信息。
- Modify: `ai-scoring/app/services/prep_topic_planning_service.py`
  - Prompt 升级为“选题专家团接力”。
  - 输出合同增加 `agentSteps` 和方向评分。
  - normalize 层补齐默认值，保证后端永远拿到可渲染结构。
- Modify: `ai-scoring/tests/test_prep_topic_planning_service.py`
  - 覆盖 `agentSteps`、评分矩阵、缺失字段兜底。
- Modify: `backend/src/test/java/com/orep/backend/service/ProjectPreparationServiceTest.java`
  - 覆盖专家步骤持久化、session 返回、方向评分保存、运行中并发保护。
- Modify: `backend/src/test/java/com/orep/backend/service/ProjectPreparationAiClientTest.java`
  - 覆盖新 JSON 合同解析。
- Modify: `frontend/user/src/views/ScriptList.vue`
  - 展示专家接力卡片。
  - 方向池展示评分矩阵、推荐等级、专家理由。
  - 右侧栏增加“本轮决策看板”。

## 数据合同

AI 服务返回 JSON 必须兼容现有字段，并新增以下结构：

```json
{
  "accepted": true,
  "message": "已完成选题专家团接力分析",
  "assistantMessage": "专家团已完成本轮选题判断。",
  "agentSteps": [
    {
      "agentKey": "topic_planner",
      "agentName": "赵选题",
      "agentRole": "选题总策划",
      "status": "COMPLETED",
      "inputSummary": "用户希望围绕温室场景和大模型能力选题。",
      "outputSummary": "建议收窄为温室环境诊断与调控建议。",
      "findings": ["题目需要回到真实应用场景，避免泛泛写大模型能力。"],
      "questions": ["是否有温室传感器数据或设备清单？"],
      "sources": []
    }
  ],
  "questions": ["是否有温室传感器数据或设备清单？"],
  "researchSummary": "公开资料显示智慧农业和设施农业节能是热点；团队事实仅限已上传材料。",
  "directions": [
    {
      "title": "面向温室场景的环境诊断与调控建议系统",
      "summary": "基于团队已有传感器材料，形成可演示的温室环境诊断闭环。",
      "tags": ["智慧农业", "节能", "传感器"],
      "equipmentMatch": "HIGH",
      "competitionMatch": "MEDIUM",
      "recommendationLevel": "RECOMMENDED",
      "expertRationale": "赵选题认为边界清晰，周可行认为可演示闭环较强。",
      "scores": {
        "competitionFit": 8,
        "resourceFit": 8,
        "innovation": 7,
        "demoReadiness": 7,
        "riskControl": 6
      },
      "evidenceGaps": ["补充传感器字段和样例数据"],
      "risks": ["真实数据周期不足会影响可信度"],
      "nextTasks": [
        {"title": "整理传感器字段", "description": "列出字段、采样频率和样例数据。", "priority": "HIGH", "stageKey": "TOPIC"}
      ],
      "researchRefs": [
        {"title": "智慧农业公开趋势", "url": "https://example.com", "sourceType": "PUBLIC_WEB"}
      ]
    }
  ],
  "sources": [],
  "nextActions": ["采纳推荐方向", "补充传感器数据", "生成策划书草稿"],
  "model": "mimo-v2.5-pro"
}
```

## 任务

### Task 1: AI 服务合同和归一化

**Files:**
- Modify: `ai-scoring/app/services/prep_topic_planning_service.py`
- Modify: `ai-scoring/tests/test_prep_topic_planning_service.py`

- [ ] **Step 1: 写失败测试，验证 agentSteps 和 scores 被归一化**

在 `ai-scoring/tests/test_prep_topic_planning_service.py` 增加测试：

```python
def test_analyze_normalizes_agent_steps_and_direction_scores():
    class _MessageWithAgents:
        content = """
        {
          "accepted": true,
          "message": "ok",
          "assistantMessage": "专家团已完成本轮判断。",
          "agentSteps": [
            {
              "agentKey": "topic_planner",
              "agentName": "赵选题",
              "agentRole": "选题总策划",
              "status": "COMPLETED",
              "inputSummary": "用户希望做温室选题。",
              "outputSummary": "建议收窄到温室诊断。",
              "findings": ["边界清晰"],
              "questions": ["是否有传感器数据？"],
              "sources": [{"title": "用户补充", "sourceType": "USER_INPUT"}]
            }
          ],
          "directions": [
            {
              "title": "温室诊断",
              "summary": "基于真实材料做温室环境诊断。",
              "scores": {"competitionFit": 8, "resourceFit": 7, "innovation": 6, "demoReadiness": 8, "riskControl": 6},
              "recommendationLevel": "RECOMMENDED",
              "expertRationale": "赵选题和周可行均建议优先推进。"
            }
          ]
        }
        """

    class _ChoiceWithAgents:
        message = _MessageWithAgents()

    class _ResponseWithAgents:
        choices = [_ChoiceWithAgents()]

    class _CompletionsWithAgents:
        def create(self, **kwargs):
            return _ResponseWithAgents()

    class _ChatWithAgents:
        completions = _CompletionsWithAgents()

    class _ClientWithAgents:
        chat = _ChatWithAgents()

    service = PrepTopicPlanningService(client=_ClientWithAgents())
    result = service.analyze({"context": {"team": {"name": "真实团队"}}, "latestUserMessage": "做温室"})

    assert result["agentSteps"][0]["agentKey"] == "topic_planner"
    assert result["agentSteps"][0]["agentName"] == "赵选题"
    assert result["agentSteps"][0]["status"] == "COMPLETED"
    assert result["directions"][0]["scores"]["competitionFit"] == 8
    assert result["directions"][0]["recommendationLevel"] == "RECOMMENDED"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest ai-scoring/tests/test_prep_topic_planning_service.py -q`

Expected: FAIL，原因是 `agentSteps` 或 `scores` 不存在。

- [ ] **Step 3: 升级 Python normalize 逻辑**

在 `prep_topic_planning_service.py` 中做最小修改：

```python
AGENT_ORDER = [
    ("topic_planner", "赵选题", "选题总策划"),
    ("policy_researcher", "李政策", "赛项与政策研究员"),
    ("industry_researcher", "张调研", "行业与用户调研员"),
    ("feasibility_analyst", "周可行", "落地可行性评估师"),
    ("chief_editor", "刘主编", "策划书主编"),
]

def _normalize(self, data: dict[str, Any]) -> dict[str, Any]:
    directions = data.get("directions")
    if not isinstance(directions, list):
        directions = []
    normalized_directions = [self._normalize_direction(item) for item in directions if isinstance(item, dict)]
    if not normalized_directions:
        normalized_directions = [self._fallback_direction()]
    return {
        "accepted": bool(data.get("accepted", True)),
        "message": str(data.get("message") or "已生成选题策划建议"),
        "assistantMessage": str(data.get("assistantMessage") or data.get("assistant_message") or "已基于真实团队资料生成方向池。"),
        "agentSteps": self._normalize_agent_steps(data.get("agentSteps") or data.get("agent_steps")),
        "questions": self._string_list(data.get("questions")),
        "researchSummary": str(data.get("researchSummary") or data.get("research_summary") or "暂无可确认的联网摘要。"),
        "directions": normalized_directions,
        "sources": self._dict_list(data.get("sources")),
        "nextActions": self._string_list(data.get("nextActions") or data.get("next_actions")),
    }
```

新增辅助函数：

```python
def _normalize_agent_steps(self, value: Any) -> list[dict[str, Any]]:
    items = self._dict_list(value)
    if not items:
        return [
            {
                "agentKey": key,
                "agentName": name,
                "agentRole": role,
                "status": "PENDING",
                "inputSummary": "等待本轮选题输入。",
                "outputSummary": "尚未形成专家判断。",
                "findings": [],
                "questions": [],
                "sources": [],
            }
            for key, name, role in AGENT_ORDER
        ]
    normalized = []
    for index, item in enumerate(items):
        default_key, default_name, default_role = AGENT_ORDER[min(index, len(AGENT_ORDER) - 1)]
        normalized.append(
            {
                "agentKey": str(item.get("agentKey") or item.get("agent_key") or default_key),
                "agentName": str(item.get("agentName") or item.get("agent_name") or default_name),
                "agentRole": str(item.get("agentRole") or item.get("agent_role") or default_role),
                "status": self._agent_status(item.get("status")),
                "inputSummary": str(item.get("inputSummary") or item.get("input_summary") or "接收上一位专家结论。"),
                "outputSummary": str(item.get("outputSummary") or item.get("output_summary") or "已完成本角色判断。"),
                "findings": self._string_list(item.get("findings")),
                "questions": self._string_list(item.get("questions")),
                "sources": self._normalize_refs(item.get("sources")),
            }
        )
    return normalized

def _agent_status(self, value: Any) -> str:
    normalized = str(value or "COMPLETED").upper()
    return normalized if normalized in {"PENDING", "RUNNING", "COMPLETED", "FAILED"} else "COMPLETED"

def _score_value(self, value: Any) -> int:
    try:
        score = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, min(10, score))

def _normalize_scores(self, value: Any) -> dict[str, int]:
    if not isinstance(value, dict):
        value = {}
    return {
        "competitionFit": self._score_value(value.get("competitionFit") or value.get("competition_fit")),
        "resourceFit": self._score_value(value.get("resourceFit") or value.get("resource_fit")),
        "innovation": self._score_value(value.get("innovation")),
        "demoReadiness": self._score_value(value.get("demoReadiness") or value.get("demo_readiness")),
        "riskControl": self._score_value(value.get("riskControl") or value.get("risk_control")),
    }
```

在 `_normalize_direction` 返回值中增加：

```python
"recommendationLevel": self._recommendation_level(item.get("recommendationLevel") or item.get("recommendation_level")),
"expertRationale": str(item.get("expertRationale") or item.get("expert_rationale") or "专家团建议结合真实材料继续核验。"),
"scores": self._normalize_scores(item.get("scores")),
```

新增：

```python
def _recommendation_level(self, value: Any) -> str:
    normalized = str(value or "CANDIDATE").upper()
    return normalized if normalized in {"RECOMMENDED", "CANDIDATE", "BACKUP", "NOT_RECOMMENDED"} else "CANDIDATE"
```

- [ ] **Step 4: 升级 SYSTEM_PROMPT**

把 `SYSTEM_PROMPT` 中角色描述改为明确专家团接力：

```text
你不是一个单一助手，而是 OREP 选题专家团。必须按以下顺序输出 agentSteps：
1. 赵选题：判断选题边界、赛道方向、团队事实边界。
2. 李政策：基于公开资料和赛项要求补充政策/赛项依据。
3. 张调研：补充行业案例、用户痛点、同类项目差异。
4. 周可行：评估设备、数据、周期、团队能力和展示风险。
5. 刘主编：整合为方向池、追问清单、任务清单和策划书框架。

后一个专家必须承接前一个专家的关键结论。每个专家只能做自己职责内的判断。
```

同时在 JSON 结构示例中加入 `agentSteps`、`scores`、`recommendationLevel`、`expertRationale`。

- [ ] **Step 5: 运行 AI 服务测试**

Run: `pytest ai-scoring/tests/test_prep_topic_planning_service.py -q`

Expected: PASS。

### Task 2: Java DTO 支持专家步骤和评分矩阵

**Files:**
- Modify: `backend/src/main/java/com/orep/backend/dto/ProjectPreparationAiResponse.java`
- Modify: `backend/src/test/java/com/orep/backend/service/ProjectPreparationAiClientTest.java`

- [ ] **Step 1: 写失败测试，验证客户端能解析 agentSteps 和 scores**

修改 `ProjectPreparationAiClientTest.analyzeCallsPrepTopicPlanningEndpointAndParsesDirections` 的 JSON，加入：

```json
"agentSteps": [
  {
    "agentKey": "topic_planner",
    "agentName": "赵选题",
    "agentRole": "选题总策划",
    "status": "COMPLETED",
    "inputSummary": "用户补充温室场景。",
    "outputSummary": "建议收窄到温室诊断。",
    "findings": ["边界清晰"],
    "questions": ["是否有数据？"],
    "sources": [{"title": "用户补充", "sourceType": "USER_INPUT"}]
  }
]
```

在 direction 中加入：

```json
"recommendationLevel": "RECOMMENDED",
"expertRationale": "专家团建议优先推进。",
"scores": {"competitionFit": 8, "resourceFit": 7, "innovation": 6, "demoReadiness": 8, "riskControl": 6}
```

新增断言：

```java
assertThat(response.getAgentSteps()).hasSize(1);
assertThat(response.getAgentSteps().get(0).getAgentName()).isEqualTo("赵选题");
assertThat(response.getDirections().get(0).getRecommendationLevel()).isEqualTo("RECOMMENDED");
assertThat(response.getDirections().get(0).getScores().getCompetitionFit()).isEqualTo(8);
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && mvn -Dtest=ProjectPreparationAiClientTest test`

Expected: FAIL，原因是 DTO 缺字段或 getter 不存在。

- [ ] **Step 3: 扩展 DTO**

在 `ProjectPreparationAiResponse.java` 中增加：

```java
private List<AgentStep> agentSteps = new ArrayList<>();

@Data
public static class AgentStep {
    private String agentKey;
    private String agentName;
    private String agentRole;
    private String status;
    private String inputSummary;
    private String outputSummary;
    private List<String> findings = new ArrayList<>();
    private List<String> questions = new ArrayList<>();
    private List<Map<String, Object>> sources = new ArrayList<>();
}

@Data
public static class DirectionScore {
    private Integer competitionFit;
    private Integer resourceFit;
    private Integer innovation;
    private Integer demoReadiness;
    private Integer riskControl;
}
```

在 `Direction` 中增加：

```java
private String recommendationLevel;
private String expertRationale;
private DirectionScore scores;
```

- [ ] **Step 4: 运行 DTO/client 测试**

Run: `cd backend && mvn -Dtest=ProjectPreparationAiClientTest test`

Expected: PASS。

### Task 3: 数据库表和 schema 自动升级

**Files:**
- Modify: `backend/src/main/resources/sql/create_project_preparation_tables.sql`
- Modify: `backend/src/main/java/com/orep/backend/service/ProjectPreparationService.java`
- Modify: `backend/src/test/java/com/orep/backend/service/ProjectPreparationServiceTest.java`

- [ ] **Step 1: 写失败测试，验证 schema 创建 agent step 表和方向评分列**

在 `ProjectPreparationServiceTest` 增加：

```java
@Test
void ensureSchemaCreatesAgentStepTableAndDirectionScoreColumns() {
    TestHarness harness = harness("project_prep_agent_schema");
    JdbcTemplate jdbc = harness.jdbc;

    Integer stepTableCount = jdbc.queryForObject("""
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME = 'project_prep_agent_step'
            """, Integer.class);
    Integer scoreColumnCount = jdbc.queryForObject("""
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'project_prep_direction'
            AND COLUMN_NAME IN ('scores_json', 'recommendation_level', 'expert_rationale')
            """, Integer.class);

    assertThat(stepTableCount).isEqualTo(1);
    assertThat(scoreColumnCount).isEqualTo(3);
}
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && mvn -Dtest=ProjectPreparationServiceTest#ensureSchemaCreatesAgentStepTableAndDirectionScoreColumns test`

Expected: FAIL，缺表或缺列。

- [ ] **Step 3: 修改 SQL 建表文件**

在 `create_project_preparation_tables.sql` 的 `project_prep_direction` 中加入：

```sql
  scores_json TEXT COMMENT '专家评分JSON',
  recommendation_level VARCHAR(40) DEFAULT NULL COMMENT '推荐等级',
  expert_rationale TEXT COMMENT '专家团推荐理由',
```

在文件末尾新增：

```sql
CREATE TABLE IF NOT EXISTS project_prep_agent_step (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  session_id BIGINT NOT NULL COMMENT '选题会话ID',
  ai_run_id BIGINT NOT NULL COMMENT 'AI运行ID',
  step_no INT NOT NULL COMMENT '步骤序号',
  agent_key VARCHAR(80) NOT NULL COMMENT '专家标识',
  agent_name VARCHAR(80) NOT NULL COMMENT '专家名称',
  agent_role VARCHAR(120) NOT NULL COMMENT '专家角色',
  status VARCHAR(32) NOT NULL DEFAULT 'COMPLETED' COMMENT '步骤状态',
  input_summary TEXT COMMENT '输入摘要',
  output_summary TEXT COMMENT '输出摘要',
  findings_json TEXT COMMENT '发现JSON',
  questions_json TEXT COMMENT '追问JSON',
  sources_json TEXT COMMENT '来源JSON',
  started_at DATETIME DEFAULT NULL COMMENT '开始时间',
  completed_at DATETIME DEFAULT NULL COMMENT '完成时间',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_project_prep_agent_step (session_id, ai_run_id, step_no),
  KEY idx_project_prep_agent_step_run (session_id, ai_run_id),
  KEY idx_project_prep_agent_step_agent (session_id, agent_key)
) COMMENT='项目准备专家团接力步骤';
```

- [ ] **Step 4: 增加 schema upgrade**

在 `ProjectPreparationService.ensureSchemaUpgrades()` 增加容错升级：

```java
try {
    jdbc.execute("ALTER TABLE project_prep_direction ADD COLUMN scores_json TEXT");
} catch (Exception ignored) {
}
try {
    jdbc.execute("ALTER TABLE project_prep_direction ADD COLUMN recommendation_level VARCHAR(40) DEFAULT NULL");
} catch (Exception ignored) {
}
try {
    jdbc.execute("ALTER TABLE project_prep_direction ADD COLUMN expert_rationale TEXT");
} catch (Exception ignored) {
}
try {
    jdbc.execute("""
            CREATE TABLE IF NOT EXISTS project_prep_agent_step (
              id BIGINT NOT NULL AUTO_INCREMENT,
              session_id BIGINT NOT NULL,
              ai_run_id BIGINT NOT NULL,
              step_no INT NOT NULL,
              agent_key VARCHAR(80) NOT NULL,
              agent_name VARCHAR(80) NOT NULL,
              agent_role VARCHAR(120) NOT NULL,
              status VARCHAR(32) NOT NULL DEFAULT 'COMPLETED',
              input_summary TEXT,
              output_summary TEXT,
              findings_json TEXT,
              questions_json TEXT,
              sources_json TEXT,
              started_at DATETIME DEFAULT NULL,
              completed_at DATETIME DEFAULT NULL,
              created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              PRIMARY KEY (id),
              UNIQUE KEY uk_project_prep_agent_step (session_id, ai_run_id, step_no),
              KEY idx_project_prep_agent_step_run (session_id, ai_run_id),
              KEY idx_project_prep_agent_step_agent (session_id, agent_key)
            )
            """);
} catch (Exception ignored) {
}
```

- [ ] **Step 5: 运行 schema 测试**

Run: `cd backend && mvn -Dtest=ProjectPreparationServiceTest#ensureSchemaCreatesAgentStepTableAndDirectionScoreColumns test`

Expected: PASS。

### Task 4: 后端持久化专家步骤和方向评分

**Files:**
- Modify: `backend/src/main/java/com/orep/backend/service/ProjectPreparationService.java`
- Modify: `backend/src/test/java/com/orep/backend/service/ProjectPreparationServiceTest.java`

- [ ] **Step 1: 写失败测试，验证 AI 成功后保存并返回 agentSteps**

在 `sendMessagePersistsGenerationAndSourceDisclosureWhenAiSucceeds` 中给 `accepted` 增加：

```java
ProjectPreparationAiResponse.AgentStep step = new ProjectPreparationAiResponse.AgentStep();
step.setAgentKey("topic_planner");
step.setAgentName("赵选题");
step.setAgentRole("选题总策划");
step.setStatus("COMPLETED");
step.setInputSummary("用户补充传感器基础。");
step.setOutputSummary("建议收窄到温室诊断。");
step.setFindings(List.of("边界清晰"));
step.setQuestions(List.of("是否有数据？"));
step.setSources(List.of(Map.of("title", "用户补充", "sourceType", "USER_INPUT")));
accepted.setAgentSteps(List.of(step));

ProjectPreparationAiResponse.DirectionScore scores = new ProjectPreparationAiResponse.DirectionScore();
scores.setCompetitionFit(8);
scores.setResourceFit(7);
scores.setInnovation(6);
scores.setDemoReadiness(8);
scores.setRiskControl(6);
direction.setScores(scores);
direction.setRecommendationLevel("RECOMMENDED");
direction.setExpertRationale("专家团建议优先推进。");
```

新增断言：

```java
List<Map<String, Object>> agentSteps = (List<Map<String, Object>>) latestRun.get("agentSteps");
assertThat(agentSteps).hasSize(1);
assertThat(agentSteps.get(0)).containsEntry("agentName", "赵选题");
assertThat(jdbc.queryForObject("SELECT COUNT(*) FROM project_prep_agent_step WHERE session_id = 88", Integer.class)).isEqualTo(1);
assertThat(directions.get(0)).containsEntry("recommendationLevel", "RECOMMENDED");
assertThat((Map<String, Object>) directions.get(0).get("scores")).containsEntry("competitionFit", 8);
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && mvn -Dtest=ProjectPreparationServiceTest#sendMessagePersistsGenerationAndSourceDisclosureWhenAiSucceeds test`

Expected: FAIL，后端未保存或未返回 `agentSteps`、`scores`。

- [ ] **Step 3: 实现 saveAgentSteps**

在 `ProjectPreparationService` 中新增：

```java
private void saveAgentSteps(Long sessionId, Long runId, List<ProjectPreparationAiResponse.AgentStep> steps) {
    if (steps == null || steps.isEmpty()) return;
    int stepNo = 1;
    for (ProjectPreparationAiResponse.AgentStep step : steps) {
        jdbc.update("""
                INSERT INTO project_prep_agent_step
                (session_id, ai_run_id, step_no, agent_key, agent_name, agent_role, status,
                 input_summary, output_summary, findings_json, questions_json, sources_json, started_at, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                sessionId,
                runId,
                stepNo++,
                firstNonBlank(step.getAgentKey(), "agent"),
                firstNonBlank(step.getAgentName(), "选题专家"),
                firstNonBlank(step.getAgentRole(), "选题专家"),
                firstNonBlank(step.getStatus(), "COMPLETED"),
                firstNonBlank(step.getInputSummary(), "接收本轮上下文"),
                firstNonBlank(step.getOutputSummary(), "已完成专家判断"),
                json(step.getFindings()),
                json(step.getQuestions()),
                json(step.getSources()),
                LocalDateTime.now(),
                LocalDateTime.now()
        );
    }
}
```

在 `completeAiRun` 中保存方向前调用：

```java
saveAgentSteps(sessionId, runId, response.getAgentSteps());
```

- [ ] **Step 4: 扩展 saveDirection**

把 `saveDirection` 的 SQL 扩展为保存新字段：

```java
INSERT INTO project_prep_direction
(session_id, ai_run_id, generation_no, title, summary, tags_json, equipment_match, competition_match,
 evidence_gaps_json, risks_json, next_tasks_json, research_refs_json, scores_json, recommendation_level, expert_rationale)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
```

新增参数：

```java
json(direction.getScores()),
direction.getRecommendationLevel(),
direction.getExpertRationale()
```

- [ ] **Step 5: 扩展 view 方法**

在 `directionView` 增加：

```java
result.put("scores", parseMap(row.get("scores_json")));
result.put("recommendationLevel", text(row.get("recommendation_level")));
result.put("expertRationale", text(row.get("expert_rationale")));
```

如果没有 `parseMap`，新增：

```java
private Map<String, Object> parseMap(Object value) {
    String raw = text(value);
    if (raw.isBlank()) return Map.of();
    try {
        return objectMapper.readValue(raw, new TypeReference<Map<String, Object>>() {});
    } catch (Exception e) {
        return Map.of();
    }
}
```

- [ ] **Step 6: latestRun 返回 agentSteps**

在 `latestRun` view 方法中增加：

```java
result.put("agentSteps", agentSteps(sessionId, longValue(row.get("id"))));
```

新增查询方法：

```java
private List<Map<String, Object>> agentSteps(Long sessionId, Long runId) {
    if (runId == null) return List.of();
    return jdbc.queryForList("""
            SELECT id, session_id sessionId, ai_run_id aiRunId, step_no stepNo,
                   agent_key agentKey, agent_name agentName, agent_role agentRole, status,
                   input_summary inputSummary, output_summary outputSummary,
                   findings_json findingsJson, questions_json questionsJson, sources_json sourcesJson,
                   started_at startedAt, completed_at completedAt, created_at createdAt
            FROM project_prep_agent_step
            WHERE session_id = ? AND ai_run_id = ?
            ORDER BY step_no ASC
            """, sessionId, runId).stream().map(row -> {
        Map<String, Object> result = new LinkedHashMap<>(row);
        result.put("findings", parseList(row.get("findingsJson")));
        result.put("questions", parseList(row.get("questionsJson")));
        result.put("sources", parseListMap(row.get("sourcesJson")));
        return result;
    }).toList();
}
```

- [ ] **Step 7: 运行后端服务测试**

Run: `cd backend && mvn -Dtest=ProjectPreparationServiceTest test`

Expected: PASS。

### Task 5: 并发、超时和稳定性加固

**Files:**
- Modify: `backend/src/main/java/com/orep/backend/service/ProjectPreparationService.java`
- Modify: `backend/src/test/java/com/orep/backend/service/ProjectPreparationServiceTest.java`
- Modify: `backend/src/main/java/com/orep/backend/service/ProjectPreparationAiClient.java`

- [ ] **Step 1: 写测试，验证运行中不再创建第二个 run**

在 `ProjectPreparationServiceTest` 增加：

```java
@Test
void sendMessageDoesNotCreateSecondRunWhenSessionAlreadyRunning() {
    TestHarness harness = harness("project_prep_running_guard");
    JdbcTemplate jdbc = harness.jdbc;
    ProjectPreparationService service = harness.service;
    jdbc.update("""
            INSERT INTO project_prep_session (id, tenant_id, team_id, created_by, title, status)
            VALUES (88, 3, 9, 12, '真实团队 选题策划', 'AI_RUNNING')
            """);
    jdbc.update("""
            INSERT INTO project_prep_ai_run (id, session_id, run_type, status, started_at)
            VALUES (99, 88, 'TOPIC_PLANNING', 'RUNNING', CURRENT_TIMESTAMP)
            """);
    when(harness.projectTeamService.dashboard(eq(9L), eq(3L), eq(12L), eq("STUDENT")))
            .thenReturn(Map.of("team", Map.of("id", 9L, "name", "真实团队")));

    Map<String, Object> result = service.sendMessage(88L, Map.of("content", "继续生成"), 3L, 12L, "STUDENT");

    assertThat(result.get("message")).isEqualTo("上一轮选题策划仍在生成中");
    assertThat(jdbc.queryForObject("SELECT COUNT(*) FROM project_prep_ai_run WHERE session_id = 88", Integer.class))
            .isEqualTo(1);
}
```

- [ ] **Step 2: 运行测试确认当前保护是否通过**

Run: `cd backend && mvn -Dtest=ProjectPreparationServiceTest#sendMessageDoesNotCreateSecondRunWhenSessionAlreadyRunning test`

Expected: PASS。如果失败，修复 `activeRunningRun(sessionId)` 的查询只认 `status='RUNNING'`。

- [ ] **Step 3: 增加 stale run 自动失败保护**

业务规则：超过 10 分钟仍处于 `RUNNING` 的 run 视为陈旧任务，允许新一轮继续提交，同时把旧 run 标记失败。

新增测试：

```java
@Test
void sendMessageExpiresStaleRunningRunBeforeCreatingNewRun() {
    TestHarness harness = harness("project_prep_stale_run");
    JdbcTemplate jdbc = harness.jdbc;
    ProjectPreparationService service = harness.service;
    jdbc.update("""
            INSERT INTO project_prep_session (id, tenant_id, team_id, created_by, title, status)
            VALUES (88, 3, 9, 12, '真实团队 选题策划', 'AI_RUNNING')
            """);
    jdbc.update("""
            INSERT INTO project_prep_ai_run (id, session_id, run_type, status, started_at)
            VALUES (99, 88, 'TOPIC_PLANNING', 'RUNNING', DATEADD('MINUTE', -20, CURRENT_TIMESTAMP))
            """);
    when(harness.projectTeamService.dashboard(eq(9L), eq(3L), eq(12L), eq("STUDENT")))
            .thenReturn(Map.of("team", Map.of("id", 9L, "name", "真实团队"), "members", List.of(), "tasks", List.of(), "materials", List.of()));
    when(harness.scriptService.listByUserId(12L)).thenReturn(List.of());
    ProjectPreparationAiResponse accepted = new ProjectPreparationAiResponse();
    accepted.setAccepted(true);
    accepted.setAssistantMessage("已完成。");
    when(harness.aiClient.analyze(any())).thenReturn(accepted);

    service.sendMessage(88L, Map.of("content", "重新生成"), 3L, 12L, "STUDENT");

    assertThat(jdbc.queryForObject("SELECT status FROM project_prep_ai_run WHERE id = 99", String.class))
            .isEqualTo("FAILED");
    assertThat(jdbc.queryForObject("SELECT COUNT(*) FROM project_prep_ai_run WHERE session_id = 88", Integer.class))
            .isEqualTo(2);
}
```

实现：在 `sendMessage` 检查 active run 前调用：

```java
expireStaleRuns(sessionId);
```

新增：

```java
private void expireStaleRuns(Long sessionId) {
    jdbc.update("""
            UPDATE project_prep_ai_run
            SET status = 'FAILED', error_message = 'AI 运行超时，已允许重新提交', completed_at = ?
            WHERE session_id = ? AND status = 'RUNNING' AND started_at < ?
            """, LocalDateTime.now(), sessionId, LocalDateTime.now().minus(Duration.ofMinutes(10)));
}
```

- [ ] **Step 4: 增强 AI client 错误信息**

在 `ProjectPreparationAiClient.analyze` 中保持现有 `RestClientException` 兜底，新增 catch `Exception`：

```java
} catch (Exception e) {
    log.error("Unexpected prep AI client failure at {}: {}", baseUrl, e.getMessage(), e);
    ProjectPreparationAiResponse error = new ProjectPreparationAiResponse();
    error.setAccepted(false);
    error.setMessage("AI 服务响应解析失败: " + e.getMessage());
    return error;
}
```

- [ ] **Step 5: 运行后端测试**

Run: `cd backend && mvn -Dtest=ProjectPreparationServiceTest,ProjectPreparationAiClientTest test`

Expected: PASS。

### Task 6: 前端专家团接力展示

**Files:**
- Modify: `frontend/user/src/views/ScriptList.vue`

- [ ] **Step 1: 增加前端数据 helper**

在 `TopicWorkspace.setup` 内增加：

```js
const defaultAgentSteps = () => props.advisors.map((advisor, index) => ({
  id: `default-${index}`,
  agentKey: advisor.name,
  agentName: advisor.name,
  agentRole: advisor.role,
  status: aiRunning() && index === 0 ? 'RUNNING' : 'PENDING',
  inputSummary: advisor.focus,
  outputSummary: '等待专家判断',
  findings: [],
  questions: [],
  sources: []
}))

const visibleAgentSteps = () => {
  const steps = props.latestRun?.agentSteps || []
  return steps.length ? steps : defaultAgentSteps()
}

const agentStepClass = status => String(status || 'PENDING').toLowerCase()

const scoreLabel = key => ({
  competitionFit: '赛项匹配',
  resourceFit: '资源匹配',
  innovation: '创新表达',
  demoReadiness: '展示闭环',
  riskControl: '风险可控'
}[key] || key)

const scoreEntries = scores => Object.entries(scores || {}).filter(([, value]) => Number(value) > 0)

const recommendationText = level => ({
  RECOMMENDED: '优先推荐',
  CANDIDATE: '可选方向',
  BACKUP: '备用方向',
  NOT_RECOMMENDED: '暂不推荐'
}[String(level || 'CANDIDATE').toUpperCase()] || '可选方向')
```

- [ ] **Step 2: 在聊天流前展示专家步骤**

在 `topic-main-scroll` 内、`chat-stream` 前增加：

```js
h('section', { class: 'agent-chain-panel' }, [
  h('div', { class: 'section-heading' }, [
    h('div', [h('strong', '选题专家团接力'), h('span', '每位专家只负责一个判断维度')])
  ]),
  h('div', { class: 'agent-chain-list' }, visibleAgentSteps().map((step, index) => h('article', { class: ['agent-step-card', agentStepClass(step.status)] }, [
    h('span', { class: 'agent-step-index' }, String(index + 1)),
    h('div', { class: 'agent-step-body' }, [
      h('div', { class: 'agent-step-head' }, [
        h('strong', step.agentName || '选题专家'),
        h('span', step.agentRole || '专家'),
        h('em', step.status === 'COMPLETED' ? '完成' : step.status === 'RUNNING' ? '进行中' : step.status === 'FAILED' ? '失败' : '等待')
      ]),
      h('p', step.outputSummary || step.inputSummary || '等待专家判断'),
      step.findings?.length ? h('ul', step.findings.slice(0, 2).map(item => h('li', item))) : null,
      step.questions?.length ? h('div', { class: 'agent-question-row' }, step.questions.slice(0, 2).map(item => h('span', item))) : null
    ])
  ])))
])
```

- [ ] **Step 3: 方向卡增加评分矩阵**

在 direction card 中 `expertRationale` 和 `scores` 位置加入：

```js
direction.recommendationLevel ? h('span', { class: ['recommendation-pill', String(direction.recommendationLevel).toLowerCase()] }, recommendationText(direction.recommendationLevel)) : null,
direction.expertRationale ? h('p', { class: 'expert-rationale' }, direction.expertRationale) : null,
scoreEntries(direction.scores).length ? h('div', { class: 'score-matrix' }, scoreEntries(direction.scores).map(([key, value]) => h('div', { class: 'score-cell' }, [
  h('span', scoreLabel(key)),
  h('strong', `${value}/10`)
]))) : null,
```

- [ ] **Step 4: 增加 CSS**

在 `<style>` 中增加：

```css
.agent-chain-panel {
  border: 1px solid var(--orep-border-soft);
  border-radius: 18px;
  background: oklch(0.995 0.004 55);
  padding: 16px;
  margin-bottom: 16px;
}

.agent-chain-list {
  display: grid;
  gap: 10px;
}

.agent-step-card {
  display: grid;
  grid-template-columns: 28px minmax(0, 1fr);
  gap: 10px;
  padding: 12px;
  border: 1px solid var(--orep-border-soft);
  border-radius: 14px;
  background: #fff;
}

.agent-step-card.running {
  border-color: oklch(0.72 0.18 55);
  background: oklch(0.98 0.025 65);
}

.agent-step-card.completed {
  border-color: oklch(0.76 0.12 145);
}

.agent-step-card.failed {
  border-color: oklch(0.66 0.2 28);
}

.agent-step-index {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: oklch(0.95 0.02 55);
  font-weight: 700;
}

.agent-step-head {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.agent-step-head span,
.agent-step-head em {
  font-size: 12px;
  color: var(--orep-text-muted);
  font-style: normal;
}

.agent-question-row,
.score-matrix {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 8px;
}

.agent-question-row span,
.score-cell,
.recommendation-pill {
  border: 1px solid var(--orep-border-soft);
  border-radius: 999px;
  padding: 4px 9px;
  font-size: 12px;
  background: oklch(0.985 0.008 55);
}

.score-cell strong {
  margin-left: 6px;
}

.expert-rationale {
  color: var(--orep-text-muted);
  margin: 8px 0 0;
}
```

- [ ] **Step 5: 构建前端**

Run: `cd frontend/user && npm run build`

Expected: PASS。

### Task 7: 右侧决策看板和失败体验

**Files:**
- Modify: `frontend/user/src/views/ScriptList.vue`

- [ ] **Step 1: 右侧栏增加本轮专家进度**

在 artifact panel 顶部加入一个 `ArtifactGroup`：

```vue
<ArtifactGroup title="专家团进度" :count="latestRun?.agentSteps?.length || 0">
  <ArtifactItem
    v-for="step in (latestRun?.agentSteps || []).slice(0, 5)"
    :key="step.id || step.agentKey"
    :name="step.agentName || '选题专家'"
    :meta="step.status === 'COMPLETED' ? '已完成' : step.status === 'RUNNING' ? '进行中' : step.status === 'FAILED' ? '失败' : '等待'"
    type="doc"
  />
  <EmptyBlock v-if="!latestRun?.agentSteps?.length" title="等待专家团" desc="提交选题信息后显示接力过程。" compact />
</ArtifactGroup>
```

- [ ] **Step 2: 失败卡片说明可重试原因**

保留现有失败卡片，文案改为：

```js
h('strong', '选题专家团生成失败')
h('span', props.latestRun.errorMessage || 'AI 服务暂时不可用，已保留你的输入，可以直接重试。')
```

- [ ] **Step 3: 运行前端构建**

Run: `cd frontend/user && npm run build`

Expected: PASS。

### Task 8: 全链路验证

**Files:**
- No source changes unless verification fails.

- [ ] **Step 1: Python 单测**

Run: `pytest ai-scoring/tests/test_prep_topic_planning_service.py -q`

Expected: PASS。

- [ ] **Step 2: 后端相关单测**

Run: `cd backend && mvn -Dtest=ProjectPreparationServiceTest,ProjectPreparationAiClientTest test`

Expected: PASS。

- [ ] **Step 3: 后端编译**

Run: `cd backend && mvn -DskipTests compile`

Expected: PASS。

- [ ] **Step 4: 前端构建**

Run: `cd frontend/user && npm run build`

Expected: PASS。

- [ ] **Step 5: 手工验收本地页面**

启动现有本地服务后打开：`https://localhost:5174/script-editor`

验收项：

- 提交一句选题补充后，页面显示“选题专家团接力”。
- AI 完成后，至少展示赵选题、李政策、张调研、周可行、刘主编的步骤卡片。
- 方向池展示推荐等级和 5 项评分。
- 右侧栏显示专家团进度。
- 失败时显示可重试提示，不丢失历史消息。
- 同一 session 运行中再次提交，不会创建第二个 run。

## 上线和稳定性要求

- 一次 session 同时只允许一个 `RUNNING` run，避免模型并发重复扣费和方向池污染。
- 超过 10 分钟的 `RUNNING` run 自动标记失败，允许老师重新提交。
- AI 服务失败只影响当前 run，不删除用户消息、历史方向和已生成文档。
- 所有公开资料必须标注 `PUBLIC_WEB`，不能写成团队事实。
- 专家步骤是 AI 产物，不等同真实教师意见，前端文案避免“官方结论”。
- 方向评分是辅助判断，最终仍需要老师结合真实材料确认。

## Self Review

- Spec coverage: 数据库、后端 DTO、后端持久化、并发稳定性、AI 服务合同、前端展示、测试和验收均有对应任务。
- Placeholder scan: 本计划不使用 TBD/TODO；每个任务都有明确文件、代码片段、命令和预期结果。
- Type consistency: `agentSteps`、`agentKey`、`agentName`、`agentRole`、`recommendationLevel`、`expertRationale`、`scores.competitionFit/resourceFit/innovation/demoReadiness/riskControl` 在 Python、Java、前端保持一致。
