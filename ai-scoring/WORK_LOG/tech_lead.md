# Tech Lead Work Log

## 当前状态
**角色**: Tech Lead（技术负责人）
**Sprint**: Sprint 0 - 项目初始化
**状态**: T000 任务已完成
**新任务**: 新 Pipeline 集成方案设计

---

## 进展记录

### 2026-04-15

#### T000 任务完成
- [x] 项目启动，等待 Orchestrator 分配 Sprint 0 任务
- [x] 发布项目 README.md
- [x] 创建目录结构并添加 .gitkeep 文件
- [x] 创建 docs/SPRINT_PLAN.md
- [x] 创建 docs/ARCHITECTURE_DECISIONS.md

#### 新 Pipeline 集成方案分析

**分析文件**：
- `/Users/liuyixing/项目/OREP/ai-scoring/app/routers/ppt_router.py`
- `/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/ppt_service.py`
- `/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/adapter_code/pipeline_coordinator.py`
- `/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/adapter_code/config_switch.py`
- `/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/adapter_code/input_adapter.py`
- `/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/adapter_code/output_adapter.py`

**分析结果**：详见下方「Pipeline 集成方案」章节

---

## Pipeline 集成方案

### 1. 问题概述

**现状**：
- `POST /api/ppt/v2/task/create` 调用 `ppt_service.create_task_v2()` (第328-341行)
- `create_task_v2()` 内部调用 `_generate_v2_async()`，使用旧模板方案
- 新 Pipeline (`pipeline_coordinator.execute()`) 已实现但未被调用

**目标**：将新 Pipeline 集成到 API 路由中，支持渐进切换

### 2. 当前系统 vs 新 Pipeline 对比

#### 2.1 当前系统 (`_generate_v2_async`)

```
问卷数据
    ↓
rule_engine.evaluate()    [规则引擎增强]
    ↓
outline_generator.generate()  [1次AI调用 - 生成大纲]
    ↓
LayoutRuleEngine.process()    [0次AI调用 - 布局处理]
    ↓
BackgroundGenerator.generate_batch()  [AI调用 - 生成背景图]
    ↓
AssemblyEngine.assemble_page()  [模板装配 - 生成HTML]
    ↓
PPTXRendererHTML.render()  [渲染PPTX]
```

**AI调用次数**：~1-2次（大纲 + 背景图）
**输出**：outline_json + HTML pages + PPTX

#### 2.2 新 Pipeline (`pipeline_coordinator.execute()`)

```
问卷数据
    ↓
Round 1: Structurize     [AI调用 - 结构化JSON]
    ↓
Round 2: Narrative        [AI调用 - 叙事框架]
    ↓
Round 3: Enrich           [AI调用 - 丰富内容]
    ↓
Round 4: HTML Generation  [AI调用 - AI生成HTML页面]  ← 核心创新
    ↓
Self-Check               [AI调用 - 质量审计]
```

**AI调用次数**：4-5次（Round 1-4 + Self-Check）
**输出**：`enriched_pages` + `html_pages` + `check_report`

#### 2.3 关键差异

| 特性 | 当前系统 | 新 Pipeline |
|------|---------|-------------|
| AI生成HTML | 否（模板装配） | 是（Round 4） |
| 内容质量控制 | 无 | Self-Check审计 |
| 叙事连贯性 | 无 | Round 2叙事框架 |
| 执行时间 | 较短 | 较长 |
| 输出格式 | outline_json | enriched_pages + html_pages |

### 3. 现有适配器分析

#### 3.1 已实现的适配器

| 适配器 | 路径 | 功能 |
|--------|------|------|
| `InputAdapter` | `adapter_code/input_adapter.py` | 问卷格式 → Pipeline格式 |
| `OutputAdapter` | `adapter_code/output_adapter.py` | Pipeline输出 → 现有系统格式 |
| `ConfigSwitch` | `adapter_code/config_switch.py` | 三模式切换控制器 |

#### 3.2 ConfigSwitch 模式

```python
class PipelineMode(Enum):
    OLD = "old"      # 仅使用旧模板系统
    NEW = "new"      # 仅使用新Pipeline
    SHADOW = "shadow"  # 两者都跑，返回旧结果（用于对比验证）
```

#### 3.3 适配器接口

**InputAdapter** (`convert_questionnaire_to_pipeline_format`):
- 输入：问卷 responses dict
- 输出：Round 1 格式的 structured_data

**OutputAdapter** (`convert_pipeline_output_to_existing_format`):
- 输入：`enriched_pages` list
- 输出：兼容现有系统的 `outline_json`

### 4. 集成方案设计

#### 4.1 推荐方案：ConfigSwitch 渐进切换

**核心思路**：
1. 修改 `_generate_v2_async()` 使用 `ConfigSwitch.execute_with_switch()`
2. 旧Pipeline函数 = 现有 `_generate_v2_async()` 逻辑（提取为独立函数）
3. 新Pipeline函数 = `PipelineCoordinator.execute()`

**优点**：
- 无需修改 API 路由
- 支持三种运行模式
- 可在生产环境渐进验证

#### 4.2 集成点分析

**当前代码** (`ppt_service.py` 第160-207行)：
```python
async def create_task_v2(
    self,
    questionnaire_id: int,
    user_id: int,
    tenant_id: int,
    industry: str = "tech"
) -> Dict:
    # 1. 获取问卷数据
    questionnaire = await self._get_questionnaire(questionnaire_id)
    responses = questionnaire['responses']

    # 2. 创建任务记录
    task_id = await self._create_task_record(...)

    # 3. 异步生成（新系统流程）
    asyncio.create_task(self._generate_v2_async(task_id, responses, industry, project_name, team_name))

    return {"task_id": task_id, "status": "generating", ...}
```

**需要修改**：
- 将 `_generate_v2_async` 的核心逻辑封装为可调用函数
- 在 `ConfigSwitch` 中注册为 `old_pipeline_func`
- `PipelineCoordinator.execute()` 作为 `new_pipeline_func`

#### 4.3 参数映射

**旧Pipeline函数签名**：
```python
async def _run_old_pipeline(task_id: int, questionnaire_data: Dict) -> Dict:
    # 1. rule_engine.evaluate()
    # 2. outline_generator.generate()
    # 3. LayoutRuleEngine.process()
    # 4. AssemblyEngine.assemble_page()
    # 5. PPTXRendererHTML.render()
    # 6. 更新任务状态和pptx_path
```

**新Pipeline函数签名**：
```python
async def PipelineCoordinator.execute(
    task_id: int,
    questionnaire_data: Dict[str, Any],
    progress_callback: Optional[Callable[[int, int, str], None]] = None
) -> Dict[str, Any]:
```

**适配**：
- `questionnaire_data` 格式一致（都是问卷responses）
- 输出格式由 `OutputAdapter` 统一转换

### 5. 实施步骤

#### 阶段 1：环境与配置（1小时）
1. 确保 `PPT_PIPELINE_MODE` 环境变量可用
2. 验证 `ConfigSwitch` 单例正常工作
3. 确认 `PipelineCoordinator` 可独立运行

#### 阶段 2：代码修改（3-4小时）

**文件**: `app/services/ppt/ppt_service.py`

修改内容：
1. 在 `_generate_v2_async` 之前添加 `_run_old_pipeline()` 函数
2. 修改 `_generate_v2_async` 使用 `ConfigSwitch.execute_with_switch()`

伪代码：
```python
async def _run_old_pipeline(
    task_id: int,
    questionnaire_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    旧模板方案Pipeline（被ConfigSwitch调用）
    提取自 _generate_v2_async 的核心逻辑
    """
    # 1. rule_engine.evaluate()
    # 2. outline_generator.generate()
    # 3. LayoutRuleEngine.process()
    # 4. AssemblyEngine.assemble_page()
    # 5. PPTXRendererHTML.render()
    # 6. 更新任务状态和pptx_path

async def _generate_v2_async(self, ...):
    switch = ConfigSwitch()
    questionnaire_data = responses  # 问卷数据

    result = await switch.execute_with_switch(
        task_id=task_id,
        questionnaire_data=questionnaire_data,
        old_pipeline_func=self._run_old_pipeline,
        progress_callback=None
    )
```

#### 阶段 3：输出格式统一（1-2小时）

确保 `PipelineCoordinator.execute()` 的输出通过 `OutputAdapter` 转换为：
```python
{
    "outline_json": {...},      # 兼容现有outline_json格式
    "enriched_pages": [...],    # Pipeline原始输出（可选）
    "html_pages": [...],        # AI生成的HTML页面
    "check_report": {...},       # 质量审计报告
    "meta": {...}
}
```

#### 阶段 4：测试验证（2-3小时）

1. **Shadow模式测试**（`PPT_PIPELINE_MODE=shadow`）：
   - 两套Pipeline并行执行
   - 对比输出差异
   - 验证降级逻辑

2. **New模式测试**（`PPT_PIPELINE_MODE=new`）：
   - 验证完整Pipeline执行
   - 测量性能指标

3. **Old模式测试**（`PPT_PIPELINE_MODE=old`）：
   - 确保现有逻辑不受影响

### 6. 修改文件清单

| 文件 | 修改类型 | 修改内容 |
|------|---------|---------|
| `app/services/ppt/ppt_service.py` | 重构 | 提取 `_run_old_pipeline()`，集成 `ConfigSwitch` |
| `.env` 或 `config.yaml` | 新增配置 | `PPT_PIPELINE_MODE=shadow` |

### 7. 风险与注意事项

#### 7.1 潜在风险

| 风险 | 缓解措施 |
|------|---------|
| Pipeline执行超时 | ConfigSwitch有timeout和重试机制 |
| 输出格式不兼容 | 使用OutputAdapter严格转换 |
| AI调用成本增加 | Shadow模式对比，New模式稳定后切换 |

#### 7.2 监控指标

建议添加：
- `pipeline_old_calls_total`
- `pipeline_new_calls_total`
- `pipeline_shadow_diff_count`
- `pipeline_execution_duration_seconds`

### 8. 建议的切换策略

```
Week 1-2: Shadow模式
  → 观察日志，对比新旧输出
  → 调整Prompt模板

Week 3-4: 5% New模式 + 95% Shadow
  → 灰度放量，监控错误率

Week 5: 50% New + 50% Shadow
  → 全面监控性能指标

Week 6: 100% New模式
  → 可选：保留Old作为Fallback
```

### 9. 结论

**推荐方案**：使用 `ConfigSwitch` 实现渐进式集成

**理由**：
1. 最小化代码入侵（无需修改API路由）
2. 支持生产环境并行验证
3. 提供完善的降级机制
4. 已有的适配器代码可复用

**下一步行动**：
1. 实现 `_run_old_pipeline()` 函数
2. 修改 `_generate_v2_async()` 使用 `ConfigSwitch`
3. 在Shadow模式下进行端到端测试

---

## 产出物清单

### Sprint 0 产出

- [x] /Users/liuyixing/项目/OREP/ai-scoring/README.md
  - 项目概述（OREP AI PPT 智能生成系统）
  - 快速开始指南
  - 架构说明（Pipeline 5 阶段设计）
  - 目录结构
  - 联系方式

- [x] /Users/liuyixing/项目/OREP/ai-scoring/docs/SPRINT_PLAN.md
  - Sprint 1-3 的粗略计划
  - 各阶段目标
  - 质量指标
  - 测试计划
  - 风险登记

- [x] /Users/liuyixing/项目/OREP/ai-scoring/docs/ARCHITECTURE_DECISIONS.md
  - 技术选型决策（FastAPI、多阶段 Pipeline、SVG 渲染）
  - 架构原则（单一职责、依赖方向、接口抽象）
  - 已知问题与应对（循环依赖、data 字段丢失、空壳页）
  - 扩展性设计
  - 性能考虑
  - 安全考虑

- [x] 目录结构
  - docs/ - 已存在，添加 .gitkeep
  - standards/ - 已存在，添加 .gitkeep
  - prompts/ - 已存在，添加 .gitkeep
  - backend/ - 新建，添加 .gitkeep
  - frontend/ - 新建，添加 .gitkeep
  - qa/ - 新建，添加 .gitkeep
  - tests/ - 已存在（保留）
  - tools/ - 已存在（保留）

### 待完成产出

- [ ] docs/SPRINT_REVIEW.md - Sprint 结束后编写
- [ ] docs/RISK_REGISTER.md - 风险登记册

---

## 决策记录

### 决策 #001：Sprint 0 启动顺序

**日期**: 2026-04-15

**决策**:
1. 先启动 Standards（无依赖，最先需要规范）
2. 同时启动 Tech Lead（负责全局规划和任务分配）
3. 其他角色在 Standards 和 Tech Lead 产出后依次启动

**依据**: AGENTS.md 中的调度规则

**执行人**: Orchestrator

### 决策 #002：新 Pipeline 集成方案

**日期**: 2026-04-15

**决策**: 使用 ConfigSwitch 实现渐进式集成

**依据**:
1. 新 Pipeline 代码已完成但未被调用
2. ConfigSwitch 已实现 old/new/shadow 三模式
3. InputAdapter 和 OutputAdapter 已实现格式转换

**执行人**: Backend Engineer

---

## 备注

Sprint 0 T000 任务已全部完成。目录结构已规范化，所有文档已创建。

Pipeline 集成方案分析已完成，推荐使用 ConfigSwitch 渐进切换方案。
