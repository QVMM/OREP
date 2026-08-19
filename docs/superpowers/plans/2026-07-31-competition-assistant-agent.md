# 竞赛助手（Competition Assistant）可落地开发方案

> **For agentic workers:** 实施时按文末「分阶段任务」顺序推进；每阶段可独立验收。  
> **角色视角：** Grok 产品经理（交互与边界）+ Grok 项目工程师（库表/接口/权限/事件/落地路径）。  
> **日期：** 2026-07-31  
> **状态：** 已确认产品规则，待立项开发

---

## 0. 一句话目标

在竞赛大脑用户端增加 **Grok 网页式个人智能对话工作台**：多轮对话、思考过程与工具步骤、文件区、个人记忆、按需评分、资源中心 RAG、生成文件回写；**不执行代码、无沙箱**；权限与 UI 完全融入现有平台。

---

## 1. 已确认产品规则（冻结）

| ID | 规则 | 工程含义 |
|----|------|----------|
| P1 | 长期记忆仅个人 | `ai_assistant_memory.user_id` 强制隔离；队友不可见 |
| P2 | 成果可进团队 | 用户主动「保存到资源中心」才创建团队资源并可选索引 |
| P3 | 聊天可分享到团队 | 导出为团队文件（纪要/快照），**不是**共享 memory 表 |
| P4 | 评分仅提到才拉 | 意图门闩后调用 `get_scores`；默认上下文无评分块 |
| P5 | 不执行代码/无沙箱 | 代码仅 Markdown 展示 + 复制 + 可选保存文件 |
| P6 | 浏览器不直连引擎 | 只访问竞赛大脑 API；AnythingLLM/MiMo Key 仅服务端 |
| P7 | 复用现有体系 | Vue3 用户端 + Spring Boot + 现有 AI 服务 + 资源中心；AnythingLLM 无 UI 引擎 |

**文案约定（防误解）：**

- 「记忆」= 提炼后的个人要点，不是完整聊天记录  
- 「分享对话」= 生成团队文件/快照  
- 「保存到资源中心」= 把产物变成团队资料  

---

## 2. 现状复用清单（禁止推倒重来）

| 能力 | 现状 | 本方案用法 |
|------|------|------------|
| 设计规范 | `frontend/user/DESIGN.md` + `workspace-tokens.css` | 对话页全部走 `--ds-*`，橙色行动色 |
| 工作台壳 | `WorkspaceShell.vue` | 新路由挂在壳内；`meta.flushMain=true` 类沉浸三栏 |
| 资源中心 | `/api/resource-center` + `ResourceCenterService` | 团队文件真源；索引同步目标 |
| 评分 | `/api/ai-score` + 报告/会话 | 按需 Tool 数据源 |
| 路演复盘聊天 | `RoadshowChat.vue` + `AiChatController` + `chat_service.py` | **保留**会议复盘场景；通用助手独立新模块，不污染 meeting 绑定 |
| 流式 | `AiScoreAssistant.vue` fetch stream | 通用助手统一 SSE 事件协议（升级版） |
| 权限上下文 | request attribute `tenantId/userId/role` | 所有新接口同款 |
| Agent 步骤先例 | `project_prep_agent_step` | 通用 `ai_assistant_run_step` 对齐字段思想 |

**不复用 / 不替换：**

- 不把 `ai_chat_session.meeting_id` 硬改成通用会话（新表更干净）  
- 不 iframe AnythingLLM  
- 不引入 Dify 多租户  

---

## 3. 总体架构

```text
┌─────────────────────────────────────────────────────────────────┐
│  frontend/user · /assistant                                     │
│  Grok 式三栏：会话列表 | 对话主区 | 文件/记忆右侧栏               │
│  Design Tokens: --ds-* · WorkspaceShell                         │
└────────────────────────────┬────────────────────────────────────┘
                             │ JWT · REST + SSE
┌────────────────────────────▼────────────────────────────────────┐
│  Spring Boot · /api/assistant/*                                 │
│  会话/消息/记忆/附件/分享/权限 · 主数据 MySQL                     │
│  编排代理 → AI 服务；资源中心保存；评分摘要查询                   │
└──────────────┬─────────────────────────────┬────────────────────┘
               │                             │
               ▼                             ▼
┌──────────────────────────┐   ┌──────────────────────────────────┐
│ ai-scoring FastAPI       │   │ ResourceCenter / MinIO           │
│ AssistantOrchestrator    │   │ 团队文件 + knowledge 任务               │
│ · 意图门闩 get_scores    │   └──────────────────────────────────┘
│ · 记忆注入               │
│ · RAG / Agent (ALL)      │──► AnythingLLM (headless API)
│ · MiMo stream+thinking   │──► MiMo OpenAI-Compatible
│ · 文档生成               │
└──────────────────────────┘
```

**原则：**

1. **主数据在 OREP**（会话、消息、记忆、附件元数据、运行轨迹）  
2. **AnythingLLM 无状态引擎**（workspace 文档、检索、Document Generation）  
3. **一个团队 = 一个 ALL Workspace**（仅团队已发布资料）；个人临时附件不进团队库  
4. **一次用户发送 = 一次 `run`**，可中止、可重试  

---

## 4. 信息架构与路由

### 4.1 路由

| path | name | meta | 说明 |
|------|------|------|------|
| `/assistant` | `AssistantHome` | `requiresAuth`, `moduleGroup: 'assistant'`, `flushMain: true` | 默认进入最近会话或欢迎态 |
| `/assistant/c/:sessionId` | `AssistantChat` | 同上 | 指定会话 |
| 可选 deep-link | query | `?teamId=&projectId=` | 绑定上下文团队（用于资源中心选材/保存） |

侧栏入口：`WorkspaceSidebar` / `WorkspaceModuleNav` 增加 **竞赛助手**，图标色建议 `--ds-icon-review` 或新 token `--ds-icon-assistant`。

### 4.2 与现有页面关系

| 页面 | 关系 |
|------|------|
| `/roadshow-chat/:meetingId` | 保留「本场复盘」；可链到助手并带 `source=roadshow&meetingId=` 预填，**不自动拉评分** 除非用户话里提到 |
| 评分报告 | 入口「用助手改进」→ 打开助手，**不预注入评分**，欢迎区 chip：「根据最近评分完善讲稿」由用户点选后才算「提到评分」 |
| 资源中心 | 助手内选材 / 保存产物复用 API |

---

## 5. 前端方案（Grok 网页布局 × 竞赛大脑规范）

### 5.1 布局结构（桌面 ≥1280）

参考 Grok 网页：**左会话 · 中对话 · 右上下文**，但视觉 **禁止** 搬 Grok 黑底/赛博风；严格执行 `DESIGN.md`：

- 背景：`--ds-canvas-background`  
- 表面：`--ds-surface` / `--ds-surface-solid`  
- 主按钮：`--ds-orange-action` + 暖白字  
- 字号：消息正文 `--ds-text-body` 15px；侧栏标题 `--ds-text-h3` 16px  
- 间距：4px 阶梯；主按钮 40px；图标按钮 36×36  

```text
┌──────── WorkspaceShell ──────────────────────────────────────┐
│ Sidebar │ Topbar                                             │
│         ├────────── flush main (assistant-layout) ───────────┤
│         │ ┌──────┬────────────────────────┬───────────────┐  │
│         │ │ 280  │        flex 1          │ 320 (可折叠)  │  │
│         │ │ 会话 │  顶栏 + 消息 + 输入    │ 文件 / 记忆   │  │
│         │ │ 列表 │                        │               │  │
│         │ └──────┴────────────────────────┴───────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

**响应式：**

| 宽度 | 行为 |
|------|------|
| ≥1280 | 三栏 |
| 960–1279 | 隐藏右侧，顶栏按钮抽屉打开文件/记忆 |
| <960 | 会话列表抽屉；主区全宽；右侧抽屉 |

### 5.2 组件目录（新建）

```text
frontend/user/src/
  views/assistant/
    AssistantWorkspace.vue          # 页面壳 + 三栏
  components/assistant/
    SessionList.vue                 # 左栏会话
    ChatHeader.vue                  # 会话标题、停止、更多菜单
    MessageList.vue
    MessageItem.vue                 # user / assistant 气泡
    ThinkingBlock.vue               # 可折叠思考
    StepTimeline.vue                # 工具步骤
    CitationChips.vue               # 知识库引用
    CodeBlock.vue                   # 高亮 + 复制 + 保存为文件
    FileCard.vue                    # 产物/附件卡片
    Composer.vue                    # 输入框 + 附件 + 发送/停止
    AttachmentStrip.vue             # 待发送附件
    RightPanel.vue                  # Tabs: 文件 | 记忆
    FilesPanel.vue
    MemoryPanel.vue
    ShareDialog.vue                 # 分享对话到团队
    SaveToResourceDialog.vue        # 保存产物到资源中心
    ResourcePickerDialog.vue        # 从资源中心选材
    WelcomeHero.vue                 # 空会话引导 + 建议 chip
  composables/
    useAssistantSessions.js
    useAssistantChat.js             # SSE 消费
    useAssistantFiles.js
    useAssistantMemory.js
  services/
    assistantClient.js              # REST 封装
  styles/
    assistant.css                   # 仅本模块；token 引用 --ds-*
```

### 5.3 中栏交互（Grok 感 × OREP 克制）

**顶栏 `ChatHeader`：**

- 可编辑会话标题（blur 保存）  
- 绑定团队名称（只读 chip，来自 `teamId`）  
- 按钮：停止生成 | 重新生成 | 分享对话 | 更多（重命名/删除/清空）  

**消息区：**

- 用户：右对齐浅表面气泡，附件缩略图在文案上  
- 助手：左对齐开放排版（少卡片边框），顺序固定：  
  1. `ThinkingBlock`（默认折叠，生成中展开）  
  2. `StepTimeline`（进行中高亮）  
  3. 正文 Markdown（表格/列表/代码）  
  4. `CitationChips`  
  5. `FileCard[]`  
- 生成中：停止按钮在 Composer 变为「停止」  
- 触底自动滚；用户上滚则暂停 stick  

**Composer（底部）：**

- 多行输入，Enter 发送，Shift+Enter 换行  
- 左：`+` 菜单 → 上传文件 | 上传图片 | 从资源中心选择  
- 占位符示例：「问讲稿、训练计划、申报书… 提到评分时会读取你的评分结果」  
- 发送禁用条件：空内容且无附件，或 `run.status=running`  

**建议 Chip（欢迎态 / 消息后）：**

- 「根据最近评分，完善我的讲稿」→ 用户点击即写入输入框发送，**算提到评分**  
- 「把资源中心里的路演讲稿总结成提纲」  
- 「生成一份本周训练计划 Excel」  
- 「把上面代码保存为 .java 文件」（仅当上条有代码块时出现）  

### 5.4 右栏

**Tab A · 本会话文件**

分组：

1. 临时附件（未进团队库）  
2. 引用的资源中心资料  
3. AI 生成产物  

每项操作：预览 | 下载 | 保存到资源中心 | 从会话移除（临时）  

**Tab B · 我的记忆**

- 列表：内容、类型、更新时间  
- 添加 / 编辑 / 删除  
- 说明文案：「仅你可见。不会自动分享给队友。」  
- **不展示精确分数类记忆**（产品禁止写入，见 §8）  

### 5.5 Markdown / 代码

- 推荐 `markdown-it` + `highlight.js`（或现有项目若已有则复用）  
- 代码块工具条：复制 | 保存为文件（弹出文件名，扩展名按语言）  
- 公式：若一期不做 KaTeX，可纯文本；二期再加  
- **禁止** 自动执行任何代码  

### 5.6 状态与空态

| 状态 | UI |
|------|----|
| 无会话 | WelcomeHero + 新建按钮 |
| 会话无消息 | 居中欢迎 + chips |
| 流式中 | thinking 展开、step 滚动、停止可用 |
| 失败 | 气泡内错误条 + 「重试本条」 |
| 索引中 | 文件 chip 显示「解析中」 |

### 5.7 无障碍与焦点

- 主按钮/发送 40px；图标 36px  
- 焦点：2px 橙色 outline + 2px offset（`DESIGN.md`）  
- `aria-live="polite"` 挂在步骤完成与错误提示  

---

## 6. 数据库设计

> 新模块前缀 `ai_assistant_*`，与会议绑定的 `ai_chat_*` 并存。

### 6.1 `ai_assistant_session` — 会话

```sql
CREATE TABLE IF NOT EXISTS ai_assistant_session (
  id              BIGINT PRIMARY KEY AUTO_INCREMENT,
  tenant_id       BIGINT NOT NULL,
  user_id         BIGINT NOT NULL COMMENT '会话所有者，个人空间',
  team_id         BIGINT DEFAULT NULL COMMENT '上下文团队：资源选材/保存目标',
  project_id      BIGINT DEFAULT NULL COMMENT '可选项目上下文',
  title           VARCHAR(200) NOT NULL DEFAULT '新对话',
  title_source    VARCHAR(20) NOT NULL DEFAULT 'default' COMMENT 'default|user|auto',
  status          VARCHAR(20) NOT NULL DEFAULT 'active' COMMENT 'active|archived|deleted',
  model           VARCHAR(80) DEFAULT NULL,
  last_message_at DATETIME DEFAULT NULL,
  message_count   INT NOT NULL DEFAULT 0,
  pin             TINYINT NOT NULL DEFAULT 0,
  all_thread_id   VARCHAR(100) DEFAULT NULL COMMENT 'AnythingLLM thread 映射，可空',
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_owner_updated (tenant_id, user_id, status, updated_at),
  KEY idx_team (tenant_id, team_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='竞赛助手会话（个人）';
```

### 6.2 `ai_assistant_message` — 消息

```sql
CREATE TABLE IF NOT EXISTS ai_assistant_message (
  id              BIGINT PRIMARY KEY AUTO_INCREMENT,
  session_id      BIGINT NOT NULL,
  tenant_id       BIGINT NOT NULL,
  user_id         BIGINT NOT NULL COMMENT '会话所有者冗余，便于鉴权',
  role            VARCHAR(20) NOT NULL COMMENT 'user|assistant|system',
  content_text    LONGTEXT COMMENT '纯文本/Markdown 正文，便于检索与兼容',
  content_json    JSON DEFAULT NULL COMMENT '结构化块：text/code/citation/file/image',
  thinking_text   LONGTEXT COMMENT '模型思考，仅展示，默认不回灌全量',
  status          VARCHAR(20) NOT NULL DEFAULT 'completed'
                  COMMENT 'pending|streaming|completed|failed|cancelled',
  model           VARCHAR(80) DEFAULT NULL,
  run_id          BIGINT DEFAULT NULL COMMENT '关联一次生成 run',
  parent_message_id BIGINT DEFAULT NULL COMMENT '重新生成时指向被替换消息',
  token_prompt    INT DEFAULT NULL,
  token_completion INT DEFAULT NULL,
  error_code      VARCHAR(40) DEFAULT NULL,
  error_message   VARCHAR(500) DEFAULT NULL,
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_session_time (session_id, id),
  KEY idx_run (run_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='竞赛助手消息';
```

**`content_json` 块约定：**

```json
{
  "blocks": [
    { "type": "text", "text": "..." },
    { "type": "code", "language": "java", "code": "..." },
    { "type": "citation", "resourceId": 12, "title": "讲稿v3", "snippet": "...", "page": 3 },
    { "type": "file", "fileId": 88, "name": "讲稿完善.docx", "mime": "...", "size": 12345 },
    { "type": "image", "fileId": 89, "url": "/api/assistant/files/89/preview" }
  ]
}
```

### 6.3 `ai_assistant_run` — 一次生成

```sql
CREATE TABLE IF NOT EXISTS ai_assistant_run (
  id              BIGINT PRIMARY KEY AUTO_INCREMENT,
  session_id      BIGINT NOT NULL,
  tenant_id       BIGINT NOT NULL,
  user_id         BIGINT NOT NULL,
  user_message_id BIGINT NOT NULL,
  assistant_message_id BIGINT DEFAULT NULL,
  status          VARCHAR(20) NOT NULL DEFAULT 'queued'
                  COMMENT 'queued|running|completed|failed|cancelled',
  intent_json     JSON DEFAULT NULL COMMENT '门闩结果：need_scores, need_rag, need_docgen...',
  request_json    JSON DEFAULT NULL,
  trace_id        VARCHAR(64) NOT NULL,
  started_at      DATETIME DEFAULT NULL,
  finished_at     DATETIME DEFAULT NULL,
  error_code      VARCHAR(40) DEFAULT NULL,
  error_message   VARCHAR(500) DEFAULT NULL,
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_session_run (session_id, id),
  KEY idx_trace (trace_id),
  KEY idx_status (status, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='竞赛助手单次生成运行';
```

### 6.4 `ai_assistant_run_step` — 工具/步骤轨迹

```sql
CREATE TABLE IF NOT EXISTS ai_assistant_run_step (
  id              BIGINT PRIMARY KEY AUTO_INCREMENT,
  run_id          BIGINT NOT NULL,
  session_id      BIGINT NOT NULL,
  step_no         INT NOT NULL,
  step_key        VARCHAR(64) NOT NULL COMMENT 'intent|get_scores|rag_search|llm|doc_gen|memory_write',
  title           VARCHAR(120) NOT NULL COMMENT '展示文案：正在检索讲稿…',
  status          VARCHAR(20) NOT NULL DEFAULT 'running' COMMENT 'running|completed|failed|skipped',
  input_summary   VARCHAR(500) DEFAULT NULL,
  output_summary  VARCHAR(1000) DEFAULT NULL,
  detail_json     JSON DEFAULT NULL,
  started_at      DATETIME DEFAULT NULL,
  finished_at     DATETIME DEFAULT NULL,
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_run_step (run_id, step_no),
  KEY idx_session_steps (session_id, run_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='竞赛助手运行步骤（前端时间线）';
```

### 6.5 `ai_assistant_file` — 会话文件

```sql
CREATE TABLE IF NOT EXISTS ai_assistant_file (
  id              BIGINT PRIMARY KEY AUTO_INCREMENT,
  tenant_id       BIGINT NOT NULL,
  user_id         BIGINT NOT NULL,
  session_id      BIGINT NOT NULL,
  message_id      BIGINT DEFAULT NULL,
  source          VARCHAR(20) NOT NULL
                  COMMENT 'upload|generated|resource_ref|export',
  visibility      VARCHAR(20) NOT NULL DEFAULT 'private'
                  COMMENT 'private|team_resource',
  name            VARCHAR(255) NOT NULL,
  mime_type       VARCHAR(120) DEFAULT NULL,
  size_bytes      BIGINT DEFAULT NULL,
  storage_key     VARCHAR(500) DEFAULT NULL COMMENT 'MinIO/本地 key；resource_ref 可空',
  resource_id     INT DEFAULT NULL COMMENT '关联资源中心 ID',
  sha256          VARCHAR(64) DEFAULT NULL,
  index_status    VARCHAR(20) NOT NULL DEFAULT 'none'
                  COMMENT 'none|pending|indexing|ready|failed|skipped',
  index_error     VARCHAR(500) DEFAULT NULL,
  all_document_id VARCHAR(100) DEFAULT NULL,
  meta_json       JSON DEFAULT NULL,
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_session_files (session_id, source),
  KEY idx_user_files (tenant_id, user_id, created_at),
  KEY idx_resource (resource_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='竞赛助手会话文件元数据';
```

**索引策略：**

| source | 默认 index_status |
|--------|-------------------|
| upload 临时 | `skipped`（仅本会话 attach，不入团队向量库） |
| resource_ref | 依赖资源中心 `knowledge_status` |
| generated | `none`；保存到团队后才 `pending` |
| export 分享 | 保存到团队时可 `pending` |

### 6.6 `ai_assistant_memory` — 个人长期记忆

```sql
CREATE TABLE IF NOT EXISTS ai_assistant_memory (
  id              BIGINT PRIMARY KEY AUTO_INCREMENT,
  tenant_id       BIGINT NOT NULL,
  user_id         BIGINT NOT NULL,
  team_id         BIGINT DEFAULT NULL COMMENT '可选：记忆关联的团队上下文，仍仅本人可见',
  memory_type     VARCHAR(32) NOT NULL
                  COMMENT 'preference|goal|style|project_focus|manual|auto_summary',
  content         VARCHAR(500) NOT NULL COMMENT '单条短事实，禁止精确分数',
  importance      TINYINT NOT NULL DEFAULT 3 COMMENT '1-5',
  source          VARCHAR(20) NOT NULL DEFAULT 'manual' COMMENT 'manual|auto|system',
  source_session_id BIGINT DEFAULT NULL,
  status          VARCHAR(20) NOT NULL DEFAULT 'active' COMMENT 'active|archived|deleted',
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_user_active (tenant_id, user_id, status, importance),
  KEY idx_user_type (tenant_id, user_id, memory_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='竞赛助手个人记忆';
```

**硬约束：**

- 单用户 active 上限 **50**（超出按 importance 升序 + 最旧淘汰或拒绝新增并提示）  
- 注入模型时 TopK=**8**（相关度：关键词 + 近会话 team/project）  
- **禁止** `memory_type` 存 `score_number`；禁止 content 匹配 `\d+(\.\d+)?\s*分` 的自动写入  

### 6.7 `ai_assistant_share` — 分享到团队审计

```sql
CREATE TABLE IF NOT EXISTS ai_assistant_share (
  id              BIGINT PRIMARY KEY AUTO_INCREMENT,
  tenant_id       BIGINT NOT NULL,
  user_id         BIGINT NOT NULL,
  session_id      BIGINT NOT NULL,
  team_id         BIGINT NOT NULL,
  share_mode      VARCHAR(20) NOT NULL COMMENT 'summary|full_text|artifacts_only',
  include_thinking TINYINT NOT NULL DEFAULT 0,
  resource_id     INT DEFAULT NULL COMMENT '生成的资源中心文件',
  file_id         BIGINT DEFAULT NULL COMMENT '助手文件表',
  status          VARCHAR(20) NOT NULL DEFAULT 'completed',
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_session_share (session_id),
  KEY idx_team_share (team_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='对话分享到团队的审计记录';
```

### 6.8 资源中心扩展字段（ALTER）

在资源表（以实际表名为准，如 `team_resource` / 现网实体）增加：

```sql
ALTER TABLE /* resource table */ 
  ADD COLUMN knowledge_status VARCHAR(20) NOT NULL DEFAULT 'none'
    COMMENT 'none|pending|indexing|ready|failed|skipped',
  ADD COLUMN knowledge_document_id VARCHAR(100) DEFAULT NULL,
  ADD COLUMN content_hash VARCHAR(64) DEFAULT NULL,
  ADD COLUMN indexed_at DATETIME DEFAULT NULL,
  ADD COLUMN index_error VARCHAR(500) DEFAULT NULL,
  ADD COLUMN index_version INT NOT NULL DEFAULT 0;
```

同步任务表（可选独立表）：

```sql
CREATE TABLE IF NOT EXISTS ai_knowledge_index_job (
  id              BIGINT PRIMARY KEY AUTO_INCREMENT,
  tenant_id       BIGINT NOT NULL,
  team_id         BIGINT NOT NULL,
  resource_id     INT NOT NULL,
  action          VARCHAR(20) NOT NULL COMMENT 'upsert|delete',
  status          VARCHAR(20) NOT NULL DEFAULT 'pending',
  attempts        INT NOT NULL DEFAULT 0,
  last_error      VARCHAR(500) DEFAULT NULL,
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_pending (status, id),
  KEY idx_resource (resource_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### 6.9 团队 → AnythingLLM 映射

```sql
CREATE TABLE IF NOT EXISTS ai_team_workspace_map (
  id              BIGINT PRIMARY KEY AUTO_INCREMENT,
  tenant_id       BIGINT NOT NULL,
  team_id         BIGINT NOT NULL,
  all_workspace_slug VARCHAR(120) NOT NULL,
  all_workspace_id   VARCHAR(80) DEFAULT NULL,
  status          VARCHAR(20) NOT NULL DEFAULT 'active',
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_team (tenant_id, team_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

---

## 7. 接口设计

统一响应：`Result<T>`（现有）。  
鉴权：JWT → `tenantId, userId, role`。  
前缀：`/api/assistant`。

### 7.1 会话

| Method | Path | 说明 |
|--------|------|------|
| GET | `/api/assistant/sessions?page&size&keyword` | 当前用户会话列表 |
| POST | `/api/assistant/sessions` | 创建：`{ teamId?, projectId?, title? }` |
| GET | `/api/assistant/sessions/{id}` | 详情 |
| PATCH | `/api/assistant/sessions/{id}` | `{ title?, status?, pin? }` |
| DELETE | `/api/assistant/sessions/{id}` | 软删 `status=deleted` |

### 7.2 消息

| Method | Path | 说明 |
|--------|------|------|
| GET | `/api/assistant/sessions/{id}/messages?beforeId&limit=50` | 历史，游标分页 |
| POST | `/api/assistant/sessions/{id}/messages` | **非流式**完整回合（测试用） |
| POST | `/api/assistant/sessions/{id}/messages:stream` | **SSE 主路径** |
| POST | `/api/assistant/runs/{runId}/cancel` | 停止生成 |
| POST | `/api/assistant/messages/{id}/regenerate:stream` | 对助手消息重新生成 |

**`messages:stream` 请求体：**

```json
{
  "content": "根据我最近的评分结果，结合知识库讲稿，完善我的讲稿",
  "clientMessageId": "uuid",
  "attachmentFileIds": [1, 2],
  "resourceIds": [101],
  "options": {
    "enableDocGen": true,
    "forceScores": false
  }
}
```

- `forceScores` 仅内部/调试；**用户产品路径不暴露**  
- 用户点 chip「根据最近评分…」时，content 自带评分关键词，走意图检测即可  

### 7.3 文件

| Method | Path | 说明 |
|--------|------|------|
| POST | `/api/assistant/sessions/{id}/files` | multipart 上传临时附件 |
| GET | `/api/assistant/sessions/{id}/files` | 本会话文件列表 |
| GET | `/api/assistant/files/{fileId}/preview` | 预览 |
| GET | `/api/assistant/files/{fileId}/download` | 下载 |
| DELETE | `/api/assistant/files/{fileId}` | 删除临时附件 |
| POST | `/api/assistant/files/{fileId}/save-to-resource` | `{ teamId, folderKey? }` → 资源中心 |
| POST | `/api/assistant/code/save-as-file` | `{ sessionId, language, code, fileName }` |

### 7.4 记忆

| Method | Path | 说明 |
|--------|------|------|
| GET | `/api/assistant/memories` | 当前用户 |
| POST | `/api/assistant/memories` | `{ content, memoryType, teamId? }` |
| PATCH | `/api/assistant/memories/{id}` | |
| DELETE | `/api/assistant/memories/{id}` | 软删 |

### 7.5 分享

| Method | Path | 说明 |
|--------|------|------|
| POST | `/api/assistant/sessions/{id}/share` | 见下 |
| GET | `/api/assistant/sessions/{id}/shares` | 历史分享记录 |

**share body：**

```json
{
  "teamId": 1,
  "folderKey": "exports",
  "shareMode": "summary",
  "includeThinking": false,
  "makeSearchable": false
}
```

- `summary`：模型或模板生成 Markdown 纪要 → 上传资源中心  
- `full_text`：拼接对话导出（无 system，thinking 默认否）  
- `artifacts_only`：仅打包生成物说明 + 链接  
- `makeSearchable=true` 才创建索引任务  

### 7.6 资源选材（只读代理）

| Method | Path | 说明 |
|--------|------|------|
| GET | `/api/assistant/resource-picker?teamId=` | 包装 resource-center workspace，过滤可引用类型 |

### 7.7 内部/引擎（不对浏览器）

| Method | Path | 说明 |
|--------|------|------|
| POST | `/api/assistant/internal/index-callback` | ALL/索引 worker 回调（服务间密钥） |
| AI 服务 | `POST /assistant/v1/runs` | Spring 调 FastAPI 编排 |

### 7.8 Spring 调 AI 服务契约

```json
// POST {AI_BASE}/assistant/v1/runs  (stream SSE)
{
  "traceId": "...",
  "tenantId": 1,
  "userId": 9,
  "teamId": 3,
  "sessionId": 100,
  "runId": 200,
  "messages": [
    { "role": "user", "content": "..." },
    { "role": "assistant", "content": "..." }
  ],
  "memories": ["用户偏好口语化讲稿", "本周重点改问题定义"],
  "attachments": [
    { "fileId": 1, "name": "a.png", "mime": "image/png", "url": "signed-or-internal" }
  ],
  "resourceIds": [101],
  "workspaceSlug": "tenant1-team3",
  "options": { "enableDocGen": true }
}
```

AI 服务 **自己** 做意图检测、按需拉评分（通过回调 Spring 或直连只读 API + 服务密钥）。

**评分只读内部接口（新建）：**

```http
GET /api/assistant/internal/score-summary?userId=&teamId=&limit=3
Header: X-Internal-Token: ...
```

返回：

```json
{
  "items": [
    {
      "sessionId": 55,
      "meetingId": 12,
      "scoredAt": "2026-07-20T10:00:00",
      "overallScore": 78,
      "track": "新一代信息技术",
      "topDeductions": [
        { "title": "问题定义不清", "points": 4, "hint": "..." }
      ],
      "topSuggestions": ["..."]
    }
  ]
}
```

**注意：** 仅当意图 `need_scores=true` 时 AI 服务才调用。

---

## 8. 编排逻辑（AI 服务 · 核心状态机）

### 8.1 单次 Run 流程

```text
receive run
  → create steps
  → intent_detect(user_text, attachments)
       need_scores | need_rag | need_docgen | need_memory_write | image_only
  → if need_scores:
       step get_scores → internal API
       if empty: step 标记 completed + summary「未找到评分」
  → inject memories (TopK, no scores)
  → if need_rag or resourceIds or team workspace:
       step rag_search → AnythingLLM
  → step llm_stream (MiMo)
       emit thinking / content
       tool calls only if agent path (doc gen)
  → if need_docgen or model requests file:
       step doc_gen → ALL Document Agent or 本地模板
       upload bytes → Spring save generated file
  → finalize message + run
  → optional: schedule memory extract (no scores)
```

### 8.2 意图门闩（评分）— 可落地规则

**规则优先（一期），模型兜底（二期）：**

```text
SCORE_PATTERNS = [
  r"评分", r"打分", r"得分", r"扣分", r"分数",
  r"AI\s*分", r"最近.*分", r"上[次轮场].*分",
  r"复盘分", r"评分结果", r"根据评分", r"按评分"
]
```

- 命中任一 → `need_scores=true`  
- 用户点击官方 chip 文案「根据最近评分…」→ 必中  
- **未命中 → 绝不调用评分 API，且 system 追加：**  
  `当前未提供评分数据。禁止编造具体分数、扣分项或声称已读取评分。`  

### 8.3 记忆注入规则

System 附加块：

```text
## 关于该用户的个人记忆（仅本人，可能过时）
- ...
请参考偏好与目标；涉及分数必须以工具结果为准。
```

自动抽取（异步，会话结束后或每 N 轮）：

- 只抽 preference / goal / style / project_focus  
- 过滤含分数模式的候选  
- 默认 `source=auto`，用户可在右栏删除  

### 8.4 RAG 范围

| 数据 | 是否进入团队 Workspace |
|------|------------------------|
| 资源中心已保存且用户有权限的团队文件 | 是（索引后） |
| 本会话临时 upload | 否；本 turn 以 attach/上下文传入 |
| 个人记忆 | 否；走 system 注入 |
| 评分 | 否；走 tool |

### 8.5 文档生成

- 优先 AnythingLLM Document Generation Agent（DOCX/PDF/PPTX/XLSX）  
- 失败降级：Markdown 文件或纯文本  
- 成功：字节流回 Spring → `ai_assistant_file(source=generated)` → SSE `file` 事件  

### 8.6 代码回复

- 模型输出 fenced code  
- 解析进 `content_json.blocks`  
- 前端 CodeBlock；可选 `save-as-file` 写成 `ai_assistant_file`  

---

## 9. SSE 事件协议（特殊事件处理核心）

`Content-Type: text/event-stream; charset=utf-8`  
每条：`event: <name>\ndata: <json>\n\n`

| event | data 关键字段 | 前端处理 |
|-------|----------------|----------|
| `run_started` | `runId, sessionId, traceId, userMessageId, assistantMessageId` | 建助手气泡，status=streaming |
| `intent` | `needScores, needRag, needDocGen, labels[]` | 可选 debug；产品可忽略 |
| `step_start` | `stepNo, stepKey, title` | StepTimeline 追加 running |
| `step_end` | `stepNo, status, outputSummary` | 更新步骤 |
| `thinking_delta` | `text` | ThinkingBlock 追加；生成中默认展开 |
| `thinking_done` | `{}` | 可自动折叠（配置项） |
| `content_delta` | `text` | 正文追加 |
| `citation` | `resourceId, title, snippet, page?` | CitationChips |
| `file` | `fileId, name, mime, size, source` | FileCard + 右栏刷新 |
| `memory_proposed` | `content, memoryType`（二期） | 可选「记住」确认条 |
| `message_completed` | `messageId, contentText` | status=completed；落盘确认 |
| `error` | `code, message, retryable` | 错误条 |
| `run_completed` | `runId, status` | 解锁输入 |
| `heartbeat` | `ts` | 防代理超时（每 15s） |

### 9.1 断线与重连

1. 客户端 AbortError / network error  
2. `GET /messages?afterId=` 或拉 run 状态  
3. 若 run 仍 `running`：可轮询 `GET /api/assistant/runs/{id}` 直到完成再拉消息  
4. 一期可不做 SSE resume；保证 **服务端落库优先**，刷新页面可见完整结果  

### 9.2 停止生成

1. 前端 `POST /runs/{id}/cancel`  
2. 编排层设 cancel flag，停止读 MiMo stream  
3. 已生成 content 保留，status=`cancelled`  
4. SSE `run_completed` status=cancelled  

### 9.3 重新生成

1. 原 assistant 消息 `parent` 链保留或标记 superseded  
2. 新 run 基于 **同一 user message**  
3. 列表默认只展示最新 assistant；「查看历史版本」二期  

### 9.4 幂等

- `clientMessageId` 唯一索引（可选表字段）防止双击双发  
- 同一 clientMessageId 10 分钟内返回同一 run  

### 9.5 超时

| 环节 | 超时 | 行为 |
|------|------|------|
| 整 run | 180s | fail + 提示 |
| 评分 API | 5s | step failed，继续无评分生成并声明 |
| RAG | 20s | 降级无检索 |
| 文档生成 | 120s | 失败则仅 Markdown |
| SSE 空闲 | 45s 无事件 | 发 heartbeat；客户端 90s 无数据提示 |

### 9.6 限流

- 用户：10 rpm 新建 run；3 并发 run  
- 租户：可配置  
- 超限：`429` + `error.code=RATE_LIMIT`  

---

## 10. 权限模型

### 10.1 主体

| 资源 | 可见 | 写 |
|------|------|-----|
| session / message / memory / private file | 仅 owner `user_id` | owner |
| team resource | 团队成员（现有 ResourceCenter 规则） | 现有规则 |
| share 导出的资源 | 团队成员 | 创建者按资源中心权限 |
| score-summary internal | 服务账号 + 目标 user 属于 team | 只读 |

### 10.2 校验清单（每个接口）

1. JWT 有效  
2. `session.tenant_id == tenantId && session.user_id == userId`  
3. 涉及 `teamId`：用户是团队成员（复用 `ProjectTeamService`）  
4. `resourceIds`：逐个 `ResourceCenterService.resolve` 权限  
5. 保存到资源中心：上传权限  
6. 分享：目标 team 成员身份  
7. 内部接口：`X-Internal-Token` 常量时间比较  

### 10.3 角色

| role | 助手 |
|------|------|
| student/user | 完整个人助手 |
| teacher | 可用；记忆仍个人；不可看学生 memory |
| admin | 运维接口另议；**不**默认可读学生对话全文 |

### 10.4 越权测试用例（必做）

1. A 的 sessionId 被 B 拉 messages → 404  
2. A 临时附件 URL 被 B 预览 → 404  
3. A memory 被 B list → 空/403  
4. 非队员 save-to-resource → 403  
5. 未提评分时响应不含具体分（抽检）  
6. 分享 summary 不含其他用户数据  

---

## 11. AnythingLLM 集成规格

### 11.1 部署

- Docker 固定版本（验证通过后写死 tag，如 `1.x.y`）  
- 仅内网；不暴露公网端口  
- 环境变量：MiMo 作为 Generic OpenAI provider  

### 11.2 映射

- `ai_team_workspace_map`：首次团队使用助手时懒创建 workspace  
- slug：`t{tenantId}-team{teamId}`  

### 11.3 同步

上传/删除资源中心文件 → `ai_knowledge_index_job` → worker：

1. 下载文件  
2. ALL upsert/delete document  
3. 回写 `knowledge_status`  

### 11.4 对话

- 优先 **OREP 编排 + ALL 仅检索/文档生成 API**  
- 若 ALL chat API 更稳，可 thread 映射 `all_thread_id`，但 **消息仍双写 OREP**  

### 11.5 降级

ALL 不可用：

- 对话仍可用（无 RAG）  
- 文件生成降级 Markdown  
- 前端 toast：知识库暂时不可用  

---

## 12. 后端模块划分（Java）

```text
com.orep.backend
  controller.assistant.AssistantController
  controller.assistant.AssistantInternalController
  service.assistant.AssistantSessionService
  service.assistant.AssistantMessageService
  service.assistant.AssistantRunService
  service.assistant.AssistantFileService
  service.assistant.AssistantMemoryService
  service.assistant.AssistantShareService
  service.assistant.AssistantScoreSummaryService
  service.assistant.AssistantAccessService
  service.assistant.KnowledgeIndexService
  client.AssistantAiClient          # WebClient SSE 转发
  entity.assistant.*
  mapper.assistant.*
```

**SSE 转发：** Spring 使用 `WebClient` 读 AI 服务流，边收边写 `SseEmitter`；同时解析关键事件落库（step/file/message）。

---

## 13. AI 服务模块划分（Python）

```text
ai-scoring/app/
  api/assistant_routes.py
  services/assistant/
    orchestrator.py
    intent.py
    score_client.py
    rag_client.py          # AnythingLLM
    docgen_client.py
    mimo_stream.py
    memory_policy.py
    prompts.py
```

配置：

```env
ASSISTANT_ENABLED=true
ANYTHINGLLM_BASE_URL=
ANYTHINGLLM_API_KEY=
ASSISTANT_INTERNAL_TOKEN=
SCORE_SUMMARY_URL=http://backend:8080/api/assistant/internal/score-summary
```

---

## 14. 提示词骨架（落地用）

```text
你是「竞赛大脑 · 竞赛助手」，帮助学生备赛：讲稿、训练计划、申报材料、代码讲解等。
语气：专业、克制、可执行，不鸡汤。
规则：
1. 未提供评分工具结果时，禁止编造分数与扣分项。
2. 引用知识库时说明资料名称；不确定则明说。
3. 代码用 Markdown 代码块，不假设可执行环境。
4. 需要生成正式文件时说明将生成的格式。
5. 尊重用户个人偏好记忆，但不泄露「记忆系统」内部实现细节。
```

---

## 15. 前端 SSE 消费伪代码（实现标准）

```javascript
// composables/useAssistantChat.js 核心行为
async function send(content, { attachmentFileIds, resourceIds }) {
  const run = { steps: [], thinking: '', content: '' }
  const res = await fetch(`/api/assistant/sessions/${sessionId}/messages:stream`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ content, attachmentFileIds, resourceIds, clientMessageId: crypto.randomUUID() }),
    signal: abortController.signal
  })
  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buf = ''
  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buf += decoder.decode(value, { stream: true })
    // parse SSE frames → switch(event) update pinia/refs
  }
}
```

**必须处理：** `heartbeat` 忽略；`error` 可重试；组件卸载 abort。

---

## 16. 配置与安全

| 项 | 要求 |
|----|------|
| 密钥 | ALL / MiMo / Internal Token 仅环境变量 |
| 上传 | 类型白名单：pdf/docx/pptx/xlsx/txt/md/png/jpg/webp；单文件 20MB；会话合计 100MB |
| 预览 URL | 鉴权下载，禁止长期裸链；可用短时签名 |
| 审计 | share / save-to-resource 写日志表或现有 audit |
| 隐私 | export 默认去 thinking；不包含其他用户 |

---

## 17. 观测与日志

每次 run 结构化日志：

```json
{
  "traceId": "...",
  "tenantId": 1,
  "userId": 9,
  "sessionId": 1,
  "runId": 2,
  "intent": { "needScores": true },
  "stepsMs": { "get_scores": 120, "rag": 800, "llm": 5000 },
  "tokens": { "prompt": 1, "completion": 2 },
  "status": "completed"
}
```

指标：run 成功率、P95 时延、评分调用率、RAG 命中率、取消率。

---

## 18. 测试计划

### 18.1 后端单测

- 意图：命中/不命中评分  
- 记忆：禁止分数写入  
- Access：跨用户 404  
- share 模式生成文件名与内容边界  

### 18.2 接口/契约

- SSE 事件顺序：`run_started → … → run_completed`  
- cancel 半截 content 保留  

### 18.3 前端

- 三栏响应式  
- 思考折叠  
- 停止按钮  
- 文件区刷新  

### 18.4 安全手工

见 §10.4  

### 18.5 评测集（上线前）

| 用例 | 期望 |
|------|------|
| 「帮我润色这段话」 | 无评分 API |
| 「根据最近评分完善讲稿」 | 有 get_scores step + 引用讲稿 |
| 上传 PNG 问图 | 多模态，不进团队库 |
| 生成 DOCX 并保存团队 | 资源中心可见 |
| 分享 summary | 队员在资源中心可见文件，不可见 A 的 memory |
| 队友问 A 的私聊内容 | 无法访问 |

---

## 19. 分阶段交付（可排期）

### 阶段 0 · 技术验证（3–5 天）

- [ ] 部署固定版 AnythingLLM + MiMo  
- [ ] 两团队 Workspace 隔离验证  
- [ ] PDF/DOCX/PPTX 中文检索  
- [ ] Document Generation 拉通  
- [ ] 输出验证报告（go/no-go）  

### 阶段 1 · 数据与 API 骨架（1 周）

- [ ] SQL 迁移全部 `ai_assistant_*` 表  
- [ ] Session/Message/Memory CRUD  
- [ ] 文件上传 MinIO + 预览下载  
- [ ] Access 单测  

### 阶段 2 · 编排 MVP + SSE（1–1.5 周）

- [ ] FastAPI orchestrator + 意图门闩  
- [ ] MiMo stream + thinking_delta  
- [ ] Spring SseEmitter 转发与落库  
- [ ] cancel / regenerate  

### 阶段 3 · 前端工作台（1.5 周）

- [ ] AssistantWorkspace 三栏  
- [ ] Message/Thinking/Step/Composer  
- [ ] 右栏文件与记忆  
- [ ] 路由与侧栏入口  
- [ ] 遵循 DESIGN.md token  

### 阶段 4 · 资源中心闭环 + 分享（1 周）

- [ ] 索引 job  
- [ ] resource picker  
- [ ] save-to-resource  
- [ ] share 三种 mode  

### 阶段 5 · 硬化上线（3–5 天）

- [ ] 限流、超时、降级  
- [ ] 安全用例全过  
- [ ] 中文样例回归  
- [ ] 文档与运维手册  

**人力粗估：** 2 后端 + 1 前端 ≈ **4–5 周** 可上线 MVP（含阶段 0）。

---

## 20. 文件级改造清单（实施索引）

| 动作 | 路径 |
|------|------|
| Create | `deploy/sql/backend-resources/create_ai_assistant_tables.sql` |
| Create | `backend/.../controller/assistant/*` |
| Create | `backend/.../service/assistant/*` |
| Create | `backend/.../entity/assistant/*` |
| Create | `ai-scoring/app/api/assistant_routes.py` |
| Create | `ai-scoring/app/services/assistant/*` |
| Create | `frontend/user/src/views/assistant/AssistantWorkspace.vue` |
| Create | `frontend/user/src/components/assistant/*` |
| Create | `frontend/user/src/services/assistantClient.js` |
| Create | `frontend/user/src/styles/assistant.css` |
| Modify | `frontend/user/src/router/index.js` |
| Modify | `frontend/user/src/components/workspace/WorkspaceSidebar.vue`（入口） |
| Modify | `frontend/user/src/components/workspace/WorkspaceShell.vue`（flush 规则若需） |
| Modify | 资源实体 + `ResourceCenterService` 索引字段 |
| Keep | `AiChatController` / `RoadshowChat.vue`（会议复盘） |

---

## 21. 产品文案（可直接用）

| 位置 | 文案 |
|------|------|
| 侧栏 | 竞赛助手 |
| 空态标题 | 今天想推进哪一步备赛？ |
| 记忆说明 | 记忆只对你可见，换对话仍可参考。完整聊天不会自动带入新会话。 |
| 分享对话框 | 将把选定内容保存为团队文件，不会共享你的个人记忆条目。 |
| 未找到评分 | 没有找到可用的评分记录。你可以先完成一次 AI 评分，或换个问法。 |
| 知识库降级 | 知识库暂不可用，我先根据对话内容回答。 |

---

## 22. 明确不做（防范围膨胀）

- 代码执行 / 沙箱 / 终端  
- 教师查看学生全部私聊（需另立项）  
- 自动把个人记忆同步给团队  
- 每轮自动注入评分  
- 替换 Coze Studio 全站  
- 复用 Dify 多租户  

---

## 23. 验收标准（MVP Definition of Done）

1. 用户可新建会话、多轮 SSE 对话、停止、刷新后历史仍在  
2. 思考过程可折叠；工具步骤可见  
3. 上传图片/文件仅本人会话可用；保存后进资源中心  
4. 提到评分才出现「获取评分」步骤；未提及时无具体分  
5. 个人记忆跨会话生效；队友不可见  
6. 分享 summary 在资源中心可下载  
7. 生成 DOCX/MD 可下载并可保存团队  
8. 越权用例全部通过  
9. UI 符合 `DESIGN.md` 色板与字号，非深色 Grok 皮肤  

---

## 24. 决策日志

| 决策 | 选择 | 原因 |
|------|------|------|
| 引擎 | AnythingLLM headless | MIT、RAG+文档生成、OpenAI 兼容 |
| 记忆真源 | OREP 表 | 条数/类型/禁分数可控 |
| 评分 | 意图门闩 | 用户明确要求 |
| 分享 | 文件导出 | 避免共享 memory |
| UI | 自研 Grok 式三栏 | 品牌与权限一致 |
| 旧 ai_chat | 保留 | 会议复盘场景独立 |

---

**文档结束。** 实施时建议从阶段 0 验证报告签字后再建表，避免引擎能力假设落空。
