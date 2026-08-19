# 准备页选题策划成熟化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把用户端“准备”页从静态样式页升级成成熟的项目准备工作台：左侧导航在本页内切换中间内容，选题策划使用真实团队/材料/讲稿数据，并通过 ai-scoring 内已有 Mimo 联网模型生成、追问、沉淀真实选题方向。

**Architecture:** 前端保留 `/script-editor` 路由作为准备工作台入口，不再让左侧准备导航跳走；改为 `activeWorkspaceKey` 控制中间内容区域。Java 后端新增 `project_preparation_*` 数据表和 `/api/project-prep/**` 用户接口，负责权限、持久化、团队数据聚合和调用 Python AI 服务。Python `ai-scoring` 新增 `/api/prep/topic-planning/**`，复用 `settings.MIMO_WEB_*` 与 OpenAI-compatible client，对 Mimo 联网模型做结构化选题策划、联网研究摘要和方向池生成。

**Tech Stack:** Vue 3 `<script setup>`、Element Plus、Vite、Java Spring Boot、MyBatis Plus/JdbcTemplate、MySQL、FastAPI、OpenAI Python SDK、Mimo `mimo-v2.5-pro` 联网模型配置、Playwright/Vite build/Maven tests。

---

## 已确认现状

- 用户端真实入口：`frontend/user/src/views/ScriptList.vue`，路由是 `/script-editor`。
- 当前页面存在静态团队、静态方向池、静态文件列表，需要删除。
- 真实团队数据已有：`GET /api/project-teams/my` 与 `GET /api/project-teams/{teamId}/dashboard`。
- 真实材料数据已在团队 dashboard 返回：`materials`、`tasks`、`submissions`、`members`、`stages`。
- 真实讲稿数据已有：`GET /api/script/my`、`GET /api/script-template`。
- 真实资源数据已有：`GET /api/ppt-template`。
- ai-scoring 已有 Mimo 配置：
  - `MIMO_WEB_API_KEY`
  - `MIMO_WEB_BASE_URL`
  - `MIMO_WEB_MODEL`
  - `MIMO_API_KEY`
  - `MIMO_BASE_URL`
  - `MIMO_MODEL`
- `ai-scoring/app/services/chat_service.py` 已经有 `_mimo_client()` 和 `_normalize_openai_base_url()`，可以抽出通用 Mimo client，避免重复写一套。

## 产品目标

1. **准备页成为一个完整工作台**
   - 左侧导航固定在准备页内部。
   - 点击“选题策划、材料库、PPT生成、讲稿制作、路演联调、版本记录”时，中间主区域切换内容。
   - 不再默认跳转到其它路由；跳转只作为具体行动按钮，例如“进入 PPT 编辑器”“打开讲稿详情”。

2. **选题策划成为可用 AI 功能**
   - 用户可以选择真实项目团队。
   - 系统读取真实团队成员、任务、材料、讲稿、赛道、已有路演记忆。
   - 用户输入想法或补充信息后，Mimo 联网模型生成：
     - 追问清单
     - 联网研究摘要
     - 方向池
     - 每个方向的设备匹配、赛项匹配、材料缺口、风险、下一步任务
   - 生成结果写入数据库，刷新页面后仍然存在。

3. **去假数据**
   - 页面不再写死“智慧农业温室项目”“王老师”“赵选题”等作为真实数据。
   - 没有真实数据时显示空状态和下一步操作，不伪装成已有文件或已有团队。
   - 允许保留“AI 角色名称”作为功能角色，但必须来自配置常量，不作为真实团队成员。

4. **成熟产品体验**
   - AI 过程有状态：未开始、收集中、联网研究中、生成方向中、已完成、失败可重试。
   - 每个方向都能“采纳为主方向”“生成任务”“生成策划书草稿”“同步到项目团队”。
   - 用户能查看历史对话和历史方向池。
   - 所有 AI 产物标注来源类型：用户输入、团队材料、联网研究、模型推理。

## 信息架构

### 左侧准备导航

左侧只是本页内导航，不再直接 `router.push()`：

- 选题策划：中间显示 AI 选题策划工作台。
- 材料库：中间显示当前团队材料、资源文件、待补材料。
- PPT生成：中间显示 PPT 生成任务入口、历史任务、最近 PPT。
- 讲稿制作：中间显示真实讲稿列表、模板、从方向生成讲稿入口。
- 路演联调：中间显示团队绑定会议、联调清单、最近路演。
- 版本记录：中间显示方向池、策划书、PPT、讲稿版本。

### 右侧产出栏

右侧始终显示当前团队的真实产出摘要：

- 赛项文件：来自团队材料或资源文件。
- 调研资料：来自团队材料，`materialType` 映射为政策、调研、案例、数据等。
- 方向草案：来自新增 `project_prep_direction_pool`。
- 策划书版本：来自新增 `project_prep_document` 或现有 `script` 的策划书类型扩展。
- 操作按钮：生成策划书、同步到项目团队。

## 数据模型

### SQL

Create: `backend/src/main/resources/sql/create_project_preparation_tables.sql`

```sql
CREATE TABLE IF NOT EXISTS project_prep_session (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  tenant_id BIGINT NOT NULL,
  team_id BIGINT NOT NULL,
  created_by BIGINT NOT NULL,
  title VARCHAR(120) NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'DRAFT',
  active_direction_id BIGINT DEFAULT NULL,
  context_snapshot_json JSON DEFAULT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_prep_session_team (tenant_id, team_id, updated_at)
);

CREATE TABLE IF NOT EXISTS project_prep_message (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  session_id BIGINT NOT NULL,
  role VARCHAR(32) NOT NULL,
  content TEXT NOT NULL,
  source_type VARCHAR(32) DEFAULT NULL,
  model VARCHAR(80) DEFAULT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_prep_message_session (session_id, created_at)
);

CREATE TABLE IF NOT EXISTS project_prep_direction (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  session_id BIGINT NOT NULL,
  title VARCHAR(160) NOT NULL,
  summary TEXT NOT NULL,
  tags_json JSON DEFAULT NULL,
  equipment_match VARCHAR(32) DEFAULT NULL,
  competition_match VARCHAR(32) DEFAULT NULL,
  evidence_gaps_json JSON DEFAULT NULL,
  risks_json JSON DEFAULT NULL,
  next_tasks_json JSON DEFAULT NULL,
  research_refs_json JSON DEFAULT NULL,
  selected TINYINT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_prep_direction_session (session_id, selected, updated_at)
);

CREATE TABLE IF NOT EXISTS project_prep_ai_run (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  session_id BIGINT NOT NULL,
  run_type VARCHAR(32) NOT NULL,
  status VARCHAR(32) NOT NULL,
  request_json JSON DEFAULT NULL,
  response_json JSON DEFAULT NULL,
  error_message TEXT DEFAULT NULL,
  model VARCHAR(80) DEFAULT NULL,
  started_at DATETIME DEFAULT NULL,
  completed_at DATETIME DEFAULT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_prep_ai_run_session (session_id, created_at)
);
```

## 后端接口

Create: `backend/src/main/java/com/orep/backend/controller/ProjectPreparationController.java`

Endpoints:

- `GET /api/project-prep/bootstrap`
  - 返回当前用户可访问团队、默认团队、团队 dashboard、讲稿、模板、资源、最近 prep session。
- `GET /api/project-prep/teams/{teamId}`
  - 切换团队时刷新准备工作台所需真实数据。
- `POST /api/project-prep/teams/{teamId}/sessions`
  - 创建或恢复选题策划 session。
- `GET /api/project-prep/sessions/{sessionId}`
  - 返回消息、方向池、AI run 状态。
- `POST /api/project-prep/sessions/{sessionId}/messages`
  - 用户发送补充信息，后端保存消息并调用 AI 服务。
- `POST /api/project-prep/sessions/{sessionId}/directions/{directionId}/select`
  - 采纳方向。
- `POST /api/project-prep/sessions/{sessionId}/directions/{directionId}/tasks`
  - 把方向缺口转成项目团队任务。
- `POST /api/project-prep/sessions/{sessionId}/document`
  - 基于当前方向生成策划书草稿。

Create: `backend/src/main/java/com/orep/backend/service/ProjectPreparationService.java`

Responsibilities:

- 做 tenant/team/user 权限校验，可复用 `ProjectTeamService.dashboard()` 的访问口径。
- 聚合真实数据，不向前端返回假数据。
- 保存 session/message/direction/run。
- 调用 Python AI 服务。
- 把方向任务写入 `project_task`，把材料缺口写入 `project_material` 或返回待创建建议。

Create: `backend/src/main/java/com/orep/backend/service/ProjectPreparationAiClient.java`

Responsibilities:

- 使用 `RestTemplate` 调用 `ai-scoring.base-url`。
- 调用 `POST /api/prep/topic-planning/analyze`。
- 超时要比评分长，建议 read timeout 180 秒。
- AI 服务失败时返回 `accepted=false` 和用户可读错误，不吞掉。

## Python AI 服务

Create: `ai-scoring/app/routers/prep_router.py`

Endpoints:

- `POST /api/prep/topic-planning/analyze`
  - 输入团队上下文、历史消息、用户最新补充。
  - 输出结构化 JSON：`assistant_message`、`questions`、`research_summary`、`directions`、`sources`、`next_actions`。
- `GET /api/prep/health`
  - 返回 Mimo 配置是否齐全，隐藏 key。

Create: `ai-scoring/app/services/prep_topic_planning_service.py`

Responsibilities:

- 复用 Mimo OpenAI-compatible client。
- System prompt 明确约束：
  - 不能编造学校、获奖、企业合作、真实数据。
  - 没有材料就写“待补证据”。
  - 联网研究摘要必须区分“公开资料趋势”和“项目已具备事实”。
  - 输出必须是 JSON。
- 对模型输出做 JSON schema 校验。
- 模型失败时返回结构化错误。

Modify: `ai-scoring/main.py`

- 注册 `prep_router`。
- root endpoint 增加 `prep_topic_planning` 描述。

## 前端设计

Modify: `frontend/user/src/views/ScriptList.vue`

Target structure:

- `activeWorkspaceKey` 控制主区域：
  - `topic`
  - `materials`
  - `ppt`
  - `script`
  - `roadshow`
  - `versions`
- 删除静态 `teamMembers`、`directions`、`competitionFiles`、`researchFiles`。
- 新增 `bootstrapState`：

```js
const bootstrap = ref({
  teams: [],
  activeTeam: null,
  dashboard: null,
  scripts: [],
  templates: [],
  resources: [],
  prepSession: null
})
```

- 新增真实加载流程：

```js
async function loadPrepBootstrap() {
  loading.value = true
  try {
    const res = await request.get('/api/project-prep/bootstrap')
    if (res.code === 200) bootstrap.value = res.data
  } finally {
    loading.value = false
  }
}
```

Create: `frontend/user/src/components/prep/PrepSideNav.vue`

- 只 emit `change`，不做路由跳转。

Create: `frontend/user/src/components/prep/TopicPlanningWorkspace.vue`

- 显示真实团队、AI 角色、消息流、问题补充、AI run 状态、方向池。
- 不自己造数据，全部通过 props/API。

Create: `frontend/user/src/components/prep/PrepArtifactPanel.vue`

- 统一展示真实材料、方向、策划书、讲稿。

Create: `frontend/user/src/components/prep/PrepMaterialsWorkspace.vue`

- 展示 `dashboard.materials`、资源库文件、待补材料。

Create: `frontend/user/src/components/prep/PrepScriptWorkspace.vue`

- 展示 `scripts` 和 `templates`，保留打开讲稿和从模板新建。

Create: `frontend/user/src/api/projectPrepApi.js`

- 封装 `/api/project-prep/**`。

## 实施任务

### Task 1: 建立准备页真实 bootstrap 后端

**Files:**
- Create: `backend/src/main/resources/sql/create_project_preparation_tables.sql`
- Create: `backend/src/main/java/com/orep/backend/controller/ProjectPreparationController.java`
- Create: `backend/src/main/java/com/orep/backend/service/ProjectPreparationService.java`
- Create: `backend/src/test/java/com/orep/backend/controller/ProjectPreparationControllerTest.java`

- [ ] 写 controller test：未登录/无 team 权限不能拿数据。
- [ ] 写 service test：`bootstrap` 返回 teams、activeTeam、dashboard、scripts、templates、resources、prepSession。
- [ ] 实现 SQL 初始化。
- [ ] 实现 controller/service。
- [ ] Run: `cd backend && JAVA_HOME=/Library/Java/JavaVirtualMachines/jdk-21.jdk/Contents/Home mvn -Dtest=ProjectPreparationControllerTest test`
- [ ] Expected: tests pass。

### Task 2: 接入 Mimo 联网选题 AI 服务

**Files:**
- Create: `ai-scoring/app/routers/prep_router.py`
- Create: `ai-scoring/app/services/prep_topic_planning_service.py`
- Modify: `ai-scoring/main.py`
- Create: `ai-scoring/tests/test_prep_topic_planning_service.py`

- [ ] 写测试：Mimo client mock 返回合法 JSON，service 能解析为 directions。
- [ ] 写测试：模型返回非 JSON 时返回结构化错误。
- [ ] 实现 Mimo client 复用逻辑。
- [ ] 实现 prompt 和 schema 校验。
- [ ] 注册 router。
- [ ] Run: `cd ai-scoring && python3 -m pytest tests/test_prep_topic_planning_service.py`
- [ ] Expected: tests pass。

### Task 3: Java 后端调用 ai-scoring 并持久化 AI 结果

**Files:**
- Create: `backend/src/main/java/com/orep/backend/service/ProjectPreparationAiClient.java`
- Modify: `backend/src/main/java/com/orep/backend/service/ProjectPreparationService.java`
- Modify: `backend/src/main/java/com/orep/backend/controller/ProjectPreparationController.java`
- Create: `backend/src/test/java/com/orep/backend/service/ProjectPreparationAiClientTest.java`
- Create: `backend/src/test/java/com/orep/backend/service/ProjectPreparationServiceTest.java`

- [ ] 写 client test：请求路径是 `/api/prep/topic-planning/analyze`。
- [ ] 写 service test：保存用户 message 后创建 `RUNNING` run。
- [ ] 写 service test：AI 返回 directions 后写入 `project_prep_direction`。
- [ ] 实现 client。
- [ ] 实现 message/analyze/select/tasks/document 业务。
- [ ] Run: `cd backend && JAVA_HOME=/Library/Java/JavaVirtualMachines/jdk-21.jdk/Contents/Home mvn -Dtest=ProjectPreparationAiClientTest,ProjectPreparationServiceTest test`
- [ ] Expected: tests pass。

### Task 4: 重构准备页为本页内导航

**Files:**
- Modify: `frontend/user/src/views/ScriptList.vue`
- Create: `frontend/user/src/api/projectPrepApi.js`
- Create: `frontend/user/src/components/prep/PrepSideNav.vue`
- Create: `frontend/user/src/components/prep/PrepArtifactPanel.vue`
- Create: `frontend/user/src/components/prep/TopicPlanningWorkspace.vue`
- Create: `frontend/user/src/components/prep/PrepMaterialsWorkspace.vue`
- Create: `frontend/user/src/components/prep/PrepScriptWorkspace.vue`

- [ ] 删除 `ScriptList.vue` 内静态团队、方向、文件数组。
- [ ] 增加 `loadPrepBootstrap()`。
- [ ] 左侧导航点击只改 `activeWorkspaceKey`。
- [ ] 每个工作区都接真实 props。
- [ ] 空状态显示“暂无真实数据”，不显示假文件。
- [ ] Run: `cd frontend/user && npm run build`
- [ ] Expected: build succeeds。

### Task 5: 选题策划完整交互

**Files:**
- Modify: `frontend/user/src/components/prep/TopicPlanningWorkspace.vue`
- Modify: `frontend/user/src/api/projectPrepApi.js`

- [ ] 用户输入补充信息后调用 `POST /api/project-prep/sessions/{sessionId}/messages`。
- [ ] 显示 AI run 状态。
- [ ] 方向池按真实返回渲染。
- [ ] “采纳方向”调用 select API。
- [ ] “生成团队任务”调用 tasks API，并刷新 dashboard。
- [ ] “生成策划书草稿”调用 document API。
- [ ] 失败时显示可重试错误。

### Task 6: 页面验收与回归

**Commands:**

```bash
cd backend
JAVA_HOME=/Library/Java/JavaVirtualMachines/jdk-21.jdk/Contents/Home mvn test
```

```bash
cd ai-scoring
python3 -m pytest tests/test_prep_topic_planning_service.py
```

```bash
cd frontend/user
npm run build
```

Manual checks:

- Open `http://localhost:5175/script-editor`。
- 点击左侧“选题策划、材料库、PPT生成、讲稿制作、路演联调、版本记录”。
- URL 保持 `/script-editor`，中间内容切换。
- 无团队时不出现假团队。
- 有团队时显示真实团队成员、任务、材料。
- 发送选题补充后，能看到 AI 状态和 Mimo 生成方向。
- 刷新页面后，消息和方向池仍然存在。
- 采纳方向后，右侧“方向草案”更新。
- 生成团队任务后，团队 dashboard 中出现真实任务。

## 验收目标

- 准备页所有左侧导航点击不跳路由。
- 页面无硬编码业务假数据。
- 选题策划至少能完成一条真实链路：选择团队 → 输入信息 → Mimo 生成方向 → 保存方向 → 采纳方向 → 生成团队任务。
- AI 输出有持久化、有错误状态、有重试入口。
- 构建和测试通过。
- 首屏视觉继续贴合当前截图风格，但功能不再是样板。

