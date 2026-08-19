# AI Score Minutes Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task with review checkpoints.

**Goal:** 将评分“依据”页升级为真实视频、事件时间轴、评分事件、按角色转写和路演章节联动的纪要式复盘工作台，并保证桌面端左侧一屏完整可见、右侧独立滚动。

**Architecture:** Java 报告 API 暴露受访问控制保护的媒体播放元数据，并提供支持 HTTP Range 的视频流；Vue 将现有真实报告、ASR、结构化扣分和证据锚点归一化为单一复盘展示模型，由播放器当前时间驱动左右两侧联动。原始识别值与展示角色映射分离，缺数据时使用诚实空态。

**Tech Stack:** Java 17, Spring Boot MVC, MyBatis-Plus, JUnit 5, MockMvc, Vue 3 Composition API, Element Plus, Vite, Node test runner.

---

## Checkpoint 1: 媒体契约与 Range 流

**Files:**

- Modify: `backend/src/main/java/com/orep/backend/dto/AiScoreReportUserResponse.java`
- Modify: `backend/src/main/java/com/orep/backend/service/AiScoringSessionService.java`
- Modify: `backend/src/main/java/com/orep/backend/service/AiScoreMediaAssetService.java`
- Modify: `backend/src/main/java/com/orep/backend/controller/AiScoreController.java`
- Test: `backend/src/test/java/com/orep/backend/service/AiScoringSessionReportDetailTest.java`
- Test: `backend/src/test/java/com/orep/backend/controller/AiScoreSessionControllerTest.java`

### Step 1: 先写失败测试

- 报告响应应包含真实媒体 ID、MIME、大小、时长和会话级流地址。
- Range 请求应返回 206、准确区间和准确字节。
- 越界 Range 应返回 416。
- 视频接口必须先执行会话访问控制。

### Step 2: 运行定向测试并确认红灯

Run: `./mvnw -q -Dtest=AiScoringSessionReportDetailTest,AiScoreSessionControllerTest test`

### Step 3: 最小实现

- 为报告 DTO 增加 `mediaPlayback`。
- 服务层只选择当前会话真实视频资产，并安全解析文件路径。
- 控制器实现 HEAD/GET/Range 响应，使用区间流式写出。

### Step 4: 重跑测试并检查契约

Run: `./mvnw -q -Dtest=AiScoringSessionReportDetailTest,AiScoreSessionControllerTest test`

通过后记录检查点，不进入前端前隐藏失败。

## Checkpoint 2: 复盘展示模型

**Files:**

- Create: `frontend/user/src/utils/aiScoreMinutesPresentation.js`
- Create: `frontend/user/src/utils/aiScoreMinutesPresentation.test.js`
- Modify: `frontend/user/src/composables/useAiScoreReport.js`

### Step 1: 先写失败测试

覆盖以下事实：

- ASR 只有 `SPEAKER_0` 时不得生成额外人物。
- 正式扣分和证据锚点按 ID 关联；无时间锚点不得伪造时间。
- 当前时间可以解析当前转写、章节和事件。
- 诊断项没有正式规则关联时不返回扣分值。

### Step 2: 运行定向测试并确认红灯

Run: `node --test src/utils/aiScoreMinutesPresentation.test.js`

### Step 3: 最小实现并接入 composable

- 归一化媒体、转写、章节和评分事件。
- 为页面暴露真实媒体播放元数据与复盘展示模型输入。
- 保留现有报告字段兼容路径，不编造缺失字段。

### Step 4: 重跑全部 AI 评分工具测试

Run: `node --test src/utils/aiScore*.test.js`

## Checkpoint 3: 依据页生产实现

**Files:**

- Replace: `frontend/user/src/views/ai-score-report/AiScoreReportWhy.vue`

### Step 1: 编写页面行为断言

在展示模型测试中补充事件点击目标时间和空态断言；已有红灯后再写组件。

### Step 2: 实现固定左栏与独立右栏

- 报告顶部导航保持不变。
- 主工作区使用 `min-height: 0` 的双栏 Grid。
- 左栏使用 `grid-template-rows: minmax(0, 1fr) auto` 和 `overflow: hidden`。
- 视频区域 `object-fit: contain`；时间轴固定占据第二行。
- 右栏头部固定，内容区独立 `overflow-y: auto`。
- 桌面高度不足时通过 `clamp()` 压缩间距和时间轴高度。
- 窄屏切换为文档流，避免强行压缩到不可用。

### Step 3: 实现真实时间联动

- `loadedmetadata/timeupdate/seeking/error` 更新页面状态。
- 点击事件、转写、章节统一 seek。
- 当前时间高亮真实条目；没有时间戳的条目只在列表展示。

### Step 4: 构建验证

Run: `npm run build`

## Checkpoint 4: 会话 26 真实验收

**Files:**

- Real media: `backend/uploads/ai-score/26/4cbd1dd1-7754-46bc-8cfc-b95d0b8c40a0-e9df998256bca0a6cbba604c1390330e.mp4`
- Real result: `ai-scoring/uploads/results/result_26.json`

### Step 1: 数据真实性核对

- 报告最终分以 Java API 为准。
- 视频时长约 3270.592 秒。
- 当前 ASR 246 段且原始 speaker 均为 `SPEAKER_0`；页面不得显示虚构多人。

### Step 2: HTTP 播放核对

- 请求首段、尾段和越界 Range。
- 核对 Content-Range、Content-Length、MIME 与返回字节。

### Step 3: 浏览器桌面验收

- 常用桌面分辨率下左栏全部可见且不滚动。
- 右侧独立滚动。
- 点击一个真实后半段事件/转写可跳播。
- 视频可播放、暂停、拖动、倍速和全屏。

### Step 4: 最终回归

Run:

- `./mvnw -q -Dtest=AiScoringSessionReportDetailTest,AiScoreSessionControllerTest test`
- `node --test src/utils/aiScore*.test.js`
- `npm run build`

本工作区不是 Git 仓库，因此以四个可复现测试检查点替代提交检查点；不执行伪造的 commit 步骤。

## 实施结果（2026-07-13）

- Checkpoint 1 完成：报告 API 已增加 `mediaPlayback`，会话视频接口支持受权限保护的 GET/HEAD/单段 Range、206 和 416。
- Checkpoint 2 完成：新增纪要展示模型，合并完整失分账本与结构化扣分，并用结构化记录补全失分账目的真实数据库证据锚点。
- Checkpoint 3 完成：依据页已替换为左侧一屏完整复盘台、右侧独立滚动纪要；视频、章节、转写和评分事件共享播放时间。
- Checkpoint 4 完成：会话 26 的 49.5 分、19 项/50.5 分失分账本、246 段真实转写、7 个真实章节、1 个可信时间锚点评分事件均通过端到端验证。
- 数据诚实限制：会话 26 原始 ASR 全部为 `SPEAKER_0`，因此当前只显示一个“发言人待确认”，未把 Python 推断的 S1-S4 冒充为真实分离说话人。人工角色校正需在上游产出可持久化 diarization speaker ID 后启用。
- 最终验证：Java 45 个测试套件共 225 项通过；前端 AI 评分工具测试 62 项通过；生产构建通过；真实会话端到端 3 项通过。
