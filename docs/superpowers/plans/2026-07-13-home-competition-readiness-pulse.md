# 首页备赛脉搏与动态缺项 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将首页不可用的总体进度条替换为基于真实项目、材料、任务、路演评分与赛道证据结构动态计算的“备赛脉搏”和“上场前还缺什么”。

**Architecture:** `CompetitionReadinessAnalyzer` 负责纯业务判定，输入为数据库事实快照，输出最多三个按风险排序的缺项；`CompetitionReadinessService` 只负责读取项目团队相关表、最新评分会话绑定的赛道证据结构并组装 7 天活动数据。现有 `ProjectTeamService.dashboard` 聚合返回 `competitionReadiness`，Vue 首页仅消费该字段并保留无数据降级态。

**Tech Stack:** Java 21、Spring Boot 3.2、JdbcTemplate、JUnit 5、Vue 3、Vite、原生 SVG/CSS。

---

### Task 1: 动态缺项分析器

**Files:**
- Create: `backend/src/main/java/com/orep/backend/service/CompetitionReadinessAnalyzer.java`
- Test: `backend/src/test/java/com/orep/backend/service/CompetitionReadinessAnalyzerTest.java`

- [ ] **Step 1: 写失败测试**：覆盖赛道材料缺失、未完成路演、未闭环高风险问题、证据齐备时不虚构缺项。
- [ ] **Step 2: 运行测试确认 RED**：`cd backend && ./mvnw -Dtest=CompetitionReadinessAnalyzerTest test`，预期因类不存在失败。
- [ ] **Step 3: 最小实现**：把事实快照转换为带 `key/title/description/severity/actionPath/source` 的前三项建议。
- [ ] **Step 4: 运行测试确认 GREEN**：同一命令预期全部通过。

### Task 2: 数据库事实聚合与现有接口接入

**Files:**
- Create: `backend/src/main/java/com/orep/backend/service/CompetitionReadinessService.java`
- Modify: `backend/src/main/java/com/orep/backend/service/ProjectTeamService.java`
- Modify: `backend/src/test/java/com/orep/backend/controller/ProjectTeamControllerTest.java`

- [ ] **Step 1: 写接口契约失败测试**：团队 dashboard 返回 `competitionReadiness`。
- [ ] **Step 2: 聚合真实数据**：查询近 7 天任务、提交、材料、路演绑定和复盘更新；读取最新评分会话的 `track_evidence_schema.material_types_json`；计算倒计时、活动曲线和近期动态。
- [ ] **Step 3: 接入聚合接口**：`ProjectTeamService.dashboard` 增加 `competitionReadiness`，访问控制沿用团队 dashboard。
- [ ] **Step 4: 验证后端测试**：运行分析器和控制器测试。

### Task 3: 首页第四方案 UI

**Files:**
- Modify: `frontend/user/src/views/Dashboard.vue`

- [ ] **Step 1: 替换模板**：移除总体百分比，新增 7 日折线、近期动态、缺项列表、比赛倒计时与动态操作入口。
- [ ] **Step 2: 增加降级逻辑**：接口暂不可用时从现有 dashboard 数据推导安全空态，不展示虚构数值。
- [ ] **Step 3: 样式与响应式**：复刻第四张方案的双栏脉搏卡，移动端改为单栏，保留焦点态与减少动画设置。
- [ ] **Step 4: 构建验证**：`npm --prefix frontend/user run build`，预期 exit 0。

### Task 4: 完整验证

**Files:**
- Modify: `docs/superpowers/plans/2026-07-13-home-competition-readiness-pulse.md`

- [ ] **Step 1: 后端定向测试**：分析器与 ProjectTeam 控制器测试通过。
- [ ] **Step 2: 后端编译**：`cd backend && ./mvnw -DskipTests package` 通过。
- [ ] **Step 3: 前端生产构建**：用户端 Vite 构建通过。
- [ ] **Step 4: 复核要求**：确认无总体进度、无硬编码项目数据、缺项来源可追溯且不暴露内部评分规则。
