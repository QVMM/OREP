# 决策记录

> 项目代号：PitchForge
> 维护者：Orchestrator

---

## 决策日志

### 2026-04-15

**决策 #001**: Sprint 0 启动顺序

**背景**: 项目刚启动，需要确定 Sprint 0 的调度顺序

**决策**:
1. 先启动 Standards（无依赖，最先需要规范）
2. 同时启动 Tech Lead（负责全局规划和任务分配）
3. 其他角色在 Standards 和 Tech Lead 产出后依次启动

**依据**: AGENTS.md 中的调度规则

**执行人**: Orchestrator

---

### 2026-04-15

**决策 #002**: 启动 Tech Lead 进行新 Pipeline 集成方案设计

**背景**:
- Sprint 1 的 S1-001/S1-002/S1-003 任务创建了新的 Round 1/2/3/4 Pipeline 代码
- 但 `app/routers/ppt_router.py` 仍在调用旧的 `ppt_service.create_task_v2()` 方案
- 用户发现生成的 HTML 使用的是旧的本地的 html 框架方案，而非新的 AI 流程

**问题**:
1. 新的 `pipeline_coordinator.py` 和 `config_switch.py` 已创建但未被集成
2. `app/routers/ppt_router.py` 的 `POST /api/ppt/v2/task/create` 仍在调用旧流程
3. 需要决定是替换旧方案，还是用 ConfigSwitch 做渐进式切换

**决策**:
1. 启动 Tech Lead 进行技术修复方案设计
2. 需要分析 `pipeline_coordinator.py` 的实现和 `config_switch.py` 的机制
3. 需要决定集成策略：直接替换 vs 渐进式切换

**执行人**: Tech Lead

**Tech Lead 分析结果**:
- 推荐方案：ConfigSwitch 渐进切换（old/new/shadow 三模式）
- 核心修改：提取 `_run_old_pipeline()`，修改 `_generate_v2_async()` 使用 `ConfigSwitch.execute_with_switch()`
- 需要修改的文件：`app/services/ppt/ppt_service.py`
- 新增配置：`PPT_PIPELINE_MODE=shadow`
- 切换策略：Week 1-2 Shadow模式 → Week 3-4 灰度放量 → Week 5-6 全面切换

---

**决策 #003**: 批准 Tech Lead 方案，启动 Backend Engineer 执行

**日期**: 2026-04-15

**决策**:
1. ~~批准 ConfigSwitch 渐进切换方案~~
2. ~~启动 Backend Engineer 执行代码修改~~
3. ~~实施步骤：阶段1-4~~

**人类用户调整决策**: 直接切换到新 Pipeline（不用渐进式）

**最终决策**:
1. 直接切换模式：`PPT_PIPELINE_MODE=new`
2. 替换旧模板方案为新 Pipeline
3. 不保留旧方案作为 fallback

**执行人**: Backend Engineer

---

## 决策模板

```
**决策 #N**: 决策标题

**背景**: 决策的背景

**决策**: 具体决策内容

**依据**: 依据的规范或原则

**执行人**: 执行此决策的人
```
