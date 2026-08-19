# OREP AI HTML 生成功能 UX 代码级任务清单

> 版本：v1.0
> 日期：2026-04-23
> 对应上位文档：`/Users/liuyixing/项目/OREP/docs/OREP_AI_HTML_UX_EXECUTION_PLAN.md`
> 目标：把 UX 执行计划进一步拆成可直接开发的代码级任务清单

---

## 一、适用范围

本清单只聚焦 AI 生成 PPT 式 HTML 相关主路径，覆盖：

- 主用户前端
- `ai-scoring` 后端
- 交付门禁、评分覆盖、补图、预览、修复、等待进度

不包含：

- Java 主业务后端的非 PPT 功能
- 会议、录制、脚本等其他模块

---

## 二、核心文件地图

### 前端主文件

| 文件 | 作用 | 当前问题 |
|---|---|---|
| `/Users/liuyixing/项目/OREP/frontend/user/src/views/PptEditor.vue` | 生成主流程（问卷/大纲/生成/预览/导出） | 体积过大、状态复杂、等待体验不够真实 |
| `/Users/liuyixing/项目/OREP/frontend/user/src/views/PptHistoryDetail.vue` | 历史详情、质检、预览、修复、下载条件 | 已承担大量工作台逻辑，需继续任务化 |
| `/Users/liuyixing/项目/OREP/frontend/user/src/stores/ppt.js` | PPT 相关状态与 API 调用 | 接口聚合多、状态刷新口径需统一 |
| `/Users/liuyixing/项目/OREP/frontend/user/src/utils/request.js` | 全局请求封装 | 超时/错误提示已部分优化，仍需支持更细粒度错误语义 |
| `/Users/liuyixing/项目/OREP/frontend/user/src/router/index.js` | 路由入口 | 后续需要更明确区分正式入口与调试入口 |

### 后端主文件

| 文件 | 作用 | 当前问题 |
|---|---|---|
| `/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/ppt_service.py` | 核心业务服务：任务、质检、评分、交付、素材、修复 | 逻辑集中、职责重，但也是当前最关键改造点 |
| `/Users/liuyixing/项目/OREP/ai-scoring/app/routers/ppt_router.py` | PPT 相关 API 路由 | 接口持续扩张，需要清晰区分主路径与高级接口 |
| `/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/scoring_checker.py` | 评分覆盖与评分点检测 | 需继续补规则与 HTML 优先逻辑 |
| `/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/html_generator.py` | HTML 模板与降级页生成 | 需统一视口和字体规范 |
| `/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/html_renderer.py` | HTML 渲染/截图 | 与导出、预览一致性相关 |
| `/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/pptx_renderer_html.py` | HTML 转 PPTX | 后续 PDF/ZIP 扩展会涉及 |
| `/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/vision_judge_service.py` | 视觉检查 | 后续等待与页级修复闭环会继续依赖 |
| `/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/adapter_code/pipeline_coordinator.py` | Round 1-4 生成链路协调 | 等待进度真实化、阶段状态拆分会涉及 |

---

## 三、P0 代码级任务清单

## P0.1 统一交付门禁口径

### 前端要改什么

#### 1. `/frontend/user/src/views/PptHistoryDetail.vue`

要做：

- 所有“下载条件卡”“终稿总审”“交付状态卡”统一只读 `deliverability`。
- `warning` 与 `blocked` 的 UI 语义明确区分：
  - `blocked`：禁止下载
  - `warning`：允许下载但提示补强
- 下载弹窗、下载按钮、总审摘要使用同一套 `downloadChecklist` 数据。

验收：

- 页面内不再出现“卡片显示通过，但按钮仍然不可下载”。

#### 2. `/frontend/user/src/stores/ppt.js`

要做：

- 增加统一方法：
  - `fetchTaskDetail(taskId)`
  - `refreshDeliverability(taskId)`
- 确保预览页、历史详情页、轮询状态页都通过同一 store 方法拿 `deliverability`。

验收：

- 前端所有交付相关状态来自同一个 store 数据源。

### 后端要改什么

#### 1. `/ai-scoring/app/services/ppt/ppt_service.py`

要做：

- 将 `assess_task_deliverability()` 定义为唯一交付判断入口。
- 将：
  - `blocked`
  - `warning`
  - `ready`
  语义彻底固化。
- 统一 `p0_count` 只统计“硬阻塞任务”。
- 将软建议类 blocker 降级为 `warning`。

验收：

- 同一任务在服务端所有接口里交付状态一致。

#### 2. `/ai-scoring/app/routers/ppt_router.py`

要做：

- 所有涉及任务详情、历史详情、下载的接口统一返回最新 `deliverability`。
- 下载接口只拦 `blocked`。

验收：

- 前后端下载判断一致。

### 需要补充/统一的数据结构

#### `deliverability`

建议固定结构：

```json
{
  "status": "blocked | warning | ready",
  "label": "不可直接交付 | 可预览但需补强 | 可交付",
  "summary": "面向用户的中文总结",
  "short_hint": "短提示",
  "blockers": ["字符串摘要"],
  "blocker_details": [
    {
      "type": "placeholder | evidence | scoring | p0 | health | page_polish",
      "priority": "P0 | P1 | P2",
      "tab": "quality | preview | materials | scoring | roadshow",
      "page_index": 26,
      "page_title": "规范操作：开发与部署流程",
      "related_points": ["市场规模"],
      "target_pages": [26, 28]
    }
  ]
}
```

---

## P0.2 清理内部修复痕迹污染正式页

### 前端要改什么

#### `/frontend/user/src/views/PptHistoryDetail.vue`

要做：

- 当前页预览、修复预览、正式页预览三区分：
  - 正式内容层
  - 辅助面板层
  - 调试信息层
- 不再把修复辅助块写进正式 HTML 预览字符串。

### 后端要改什么

#### `/ai-scoring/app/services/ppt/ppt_service.py`

要做：

- 统一在以下流程前剥离内部修复痕迹：
  - 质量检查
  - 评分覆盖
  - 导出
  - 交付门禁
- 新增或继续强化：
  - `_strip_existing_repair_artifacts()`
  - `_sanitize_html_for_delivery()`
  - `_analyze_html_page_quality()`

#### `/ai-scoring/app/services/ppt/html_generator.py`

要做：

- 明确正式页与调试页输出契约，避免模板降级页继续引入调试层。

### 需要补充的数据结构

建议在页级快照里补一个字段：

```json
{
  "page_debug_flags": {
    "has_internal_repair_panel": false,
    "has_debug_overlay": false,
    "has_scoring_annotation": false
  }
}
```

---

## P0.3 评分覆盖按当前 HTML 重算

### 前端要改什么

#### `/frontend/user/src/views/PptHistoryDetail.vue`

要做：

- “一键补评分点”执行后，统一刷新：
  - `scoring_coverage`
  - `scoring_dashboard`
  - `quality_report`
  - `deliverability`
- 在卡片中展示：
  - 当前缺失评分点
  - 当前优先补评分点
  - 已关联页面

#### `/frontend/user/src/stores/ppt.js`

要做：

- 补一个评分覆盖强制刷新方法，例如：
  - `refreshScoringCoverage(taskId)`

### 后端要改什么

#### `/ai-scoring/app/services/ppt/ppt_service.py`

要做：

- `get_task_scoring_coverage(task_id)` 统一优先从当前 HTML 重算。
- 保留 outline-only 作为兜底，不再作为主路径。
- “一键补评分点”相关修复逻辑必须把 `target_points` 写入修复上下文。

#### `/ai-scoring/app/services/ppt/scoring_checker.py`

要做：

- 细化必备评分点识别规则。
- 为当前缺失评分点提供更稳定的关键词/语义规则。

### 需要补充的数据结构

#### `scoring_coverage`

建议结构统一为：

```json
{
  "coverage_rate": "89%",
  "required_coverage_rate": "89%",
  "required_points_total": 13,
  "required_points_covered": 12,
  "missing_required_points": ["市场规模"],
  "priority_missing_points": ["市场规模", "竞争优势", "融资需求"],
  "point_to_pages": {
    "市场规模": [3, 5, 8],
    "竞争优势": [8, 9, 10]
  },
  "stage": "computed_html"
}
```

---

## P0.4 补图绑定与缺图提示一致性修复

### 前端要改什么

#### `/frontend/user/src/views/PptHistoryDetail.vue`

要做：

- 当前页右侧工作台的“缺图提示”只读最新 `failed_checks`。
- 如果：
  - `material_evidence = pass`
  - `policy_evidence = pass`
  就不再提示“先补证据”。
- 上传完成后自动静默触发当前页质检刷新。

#### `/frontend/user/src/stores/ppt.js`

要做：

- 新增“上传素材后重跑当前页质检”封装。

### 后端要改什么

#### `/ai-scoring/app/services/ppt/ppt_service.py`

要做：

- 强化显式页码绑定：
  - 文件名含 `page26`
  - 描述含 `第26页`
  - 页面标题显式命中
- 上传成功后支持按页重跑质检。

#### `/ai-scoring/app/routers/ppt_router.py`

要做：

- 补充一个按页重质检的轻量接口，或在上传接口里增加可选触发参数。

### 需要补充的数据结构

#### `page_material_binding`

建议至少有：

```json
{
  "page_index": 26,
  "page_title": "规范操作：开发与部署流程",
  "material_id": 15,
  "binding_source": "explicit_page_hint | recommendation | manual",
  "binding_confidence": 0.98,
  "material_types": ["screenshot", "chart"],
  "status": "active"
}
```

---

## 四、P1 代码级任务清单

## P1.1 下载条件卡工作台化

### 前端要改什么

#### `/frontend/user/src/views/PptHistoryDetail.vue`

要做：

- 每张卡都支持当前页直接处理：
  - 占位词
  - 模板化
  - 评分覆盖
  - P0 阻塞
- 每张卡增加：
  - `actionText`
  - `actionHint`
  - `targetPages`
  - `relatedPoints`
  - `lastActionResult`
- 动作完成后卡内直接回显：
  - 本次处理页
  - 本次已满足的规则
  - 当前剩余差距

### 后端要改什么

#### `/ai-scoring/app/services/ppt/ppt_service.py`

要做：

- 对外统一输出“下载条件卡所需数据”。
- 支持批量当前页动作：
  - 清占位词
  - 模板页重做
  - 评分点补强
  - P0 批量处理

### 需要补充的数据结构

#### `download_checklist_item`

```json
{
  "key": "scoring-coverage",
  "status": "pass | fail",
  "title": "必备评分点覆盖建议达到 85% 以上",
  "current_value": 67,
  "target_value": 85,
  "unit": "%",
  "related_points": ["市场规模", "竞争优势"],
  "target_pages": [3, 5, 8],
  "action_text": "一键补评分点",
  "action_hint": "共缺 3 个必备评分点"
}
```

---

## P1.2 将补图并入 HTML 预览页

### 前端要改什么

#### `/frontend/user/src/views/PptHistoryDetail.vue`

要做：

- 在 `HTML 预览` 右侧工作台固定显示：
  - 当前页缺图任务
  - 已关联素材
  - 本页直接上传
  - 本页补图结果提示
- “素材证据”页只保留：
  - 高级管理
  - 全局素材总览
  - 高级绑定

### 后端要改什么

#### `/ai-scoring/app/services/ppt/ppt_service.py`

要做：

- 返回当前页缺图任务摘要：
  - 缺什么
  - 推荐上传什么
  - 已绑定了什么
  - 哪条缺图规则已满足

### 需要补充的数据结构

#### `page_material_task`

```json
{
  "page_index": 26,
  "page_title": "规范操作：开发与部署流程",
  "status": "missing | partial | ready",
  "required_materials": ["系统操作截图", "验收记录截图", "指标对比图"],
  "missing_reasons": ["评分观测点证明不足"],
  "linked_materials": [
    {"id": 15, "filename": "page26_ops_flow.png"}
  ]
}
```

---

## P1.3 素材证据页改为逐页缺图清单

### 前端要改什么

#### `/frontend/user/src/views/PptHistoryDetail.vue`

要做：

- 素材页顶部改成“逐页待上传清单”。
- 逐页卡片支持：
  - 页码
  - 标题
  - 缺图建议
  - 一键进入该页上传
- 证据包视图默认收起，只保留高级入口。

### 后端要改什么

#### `/ai-scoring/app/services/ppt/ppt_service.py`

要做：

- 输出“逐页待上传清单”数据，而不是只输出证据包。
- 同时保留证据包，用于内部复用和高级视图。

### 需要补充的数据结构

#### `page_upload_task`

```json
{
  "page_index": 17,
  "page_title": "安全与质量保障",
  "priority": "P1",
  "required_images": ["系统截图", "设备运行照片", "结果数据图"],
  "why_missing": "缺少能支撑工程流程与结果验证的真实证据"
}
```

---

## P1.4 预览区交互优化

### 前端要改什么

#### `/frontend/user/src/views/PptHistoryDetail.vue`

要做：

- 在预览区增加：
  - 适应窗口
  - 100%
  - 整页
- 增加快捷键：
  - 左右翻页
  - Home/End
- 页列表、主舞台、右侧工作台形成稳定三栏。

#### `/frontend/user/src/views/PptEditor.vue`

要做：

- 将 Step 3 预览调整页面继续向“以当前页为中心”收敛。

### 后端要改什么

- 本项后端改动较少，主要依赖前端交互与现有预览数据。

---

## 五、P1.5 代码级任务清单

## P1.5.1 生成过程真实进度

### 前端要改什么

#### `/frontend/user/src/views/PptEditor.vue`

要做：

- 将当前静态阶段提示替换为真实子状态展示。
- 展示：
  - 当前阶段
  - 当前处理页/总页数
  - 当前批次
  - 最近输出时间
  - 是否处于恢复流程

#### `/frontend/user/src/stores/ppt.js`

要做：

- 轮询接口结果标准化。
- 将 `progress / stage / page_progress / recovery_state` 统一收口。

### 后端要改什么

#### `/ai-scoring/app/services/ppt/adapter_code/pipeline_coordinator.py`

要做：

- 各 Round 输出更细的进度状态：
  - Round 1：解析问卷 / 结构化完成
  - Round 2：大纲生成中 / 章节生成中
  - Round 3：内容富化中 / 第 X 批处理中
  - Round 4：HTML 生成中 / 第 X 页处理中

#### `/ai-scoring/app/routers/ppt_router.py`

要做：

- 任务状态接口返回更细字段：
  - `stage_label`
  - `page_progress`
  - `batch_progress`
  - `last_output_at`
  - `recovery_state`

### 需要补充的数据结构

```json
{
  "stage": "round4_html",
  "stage_label": "正在生成 HTML",
  "page_progress": {"current": 12, "total": 38},
  "batch_progress": {"current": 3, "total": 8},
  "last_output_at": "2026-04-23T16:20:15+08:00",
  "recovery_state": "normal | recovering | resumed"
}
```

---

## 六、P2 代码级任务清单

## P2.1 拆分 `PptEditor.vue`

### 前端要改什么

#### `/frontend/user/src/views/PptEditor.vue`

要做：

- 拆分为：
  - `components/ppt/StepQuestionnaire.vue`
  - `components/ppt/StepOutline.vue`
  - `components/ppt/StepGeneration.vue`
  - `components/ppt/StepPreview.vue`
  - `components/ppt/StepExport.vue`
- 对话框拆分为：
  - `ReadinessDialog.vue`
  - `DeliverabilityGuide.vue`
  - `ProgressPanel.vue`

#### `/frontend/user/src/stores/ppt.js`

要做：

- 明确把所有 API 与跨步骤状态保留在 store。

### 后端要改什么

- 本项以后端接口稳定为前提，无需新增复杂逻辑，但需要保证接口职责清晰。

---

## P2.2 明确双前端定位

### 前端要改什么

#### `/frontend/user/src/router/index.js`

要做：

- 确保主用户流程只走正式入口。

#### AI Scoring 前端（如仍保留）

要做：

- 明确加 `DEV ONLY`
- 或调整部署策略，不对普通用户暴露

### 后端要改什么

- 无强依赖，但需要和部署策略一起确认。

---

## P2.3 统一视口与字体规范

### 后端要改什么

#### `/ai-scoring/app/services/ppt/html_generator.py`

要做：

- 所有生成路径统一输出 `1920x1080`。
- 模板降级页同步统一。
- 统一字体栈，移除 Google Fonts 依赖。

#### `/ai-scoring/app/services/ppt/html_renderer.py`

要做：

- 确保截图/渲染也按统一视口工作。

#### `/ai-scoring/app/services/ppt/pptx_renderer_html.py`

要做：

- 与 HTML 统一尺寸输出，避免转换偏差。

### 前端要改什么

#### `/frontend/user/src/views/PptHistoryDetail.vue`

要做：

- 默认预览舞台与 1920x1080 契约一致。

---

## 七、P3 代码级任务清单

## P3.1 导出增强

### 前端要改什么

#### `/frontend/user/src/views/PptHistoryDetail.vue`

要做：

- 下载区支持：
  - PPTX
  - PDF
  - HTML ZIP

### 后端要改什么

#### `/ai-scoring/app/services/ppt/html_renderer.py`

要做：

- 增加 PDF 渲染封装。

#### `/ai-scoring/app/routers/ppt_router.py`

要做：

- 增加：
  - `GET /api/ppt/task/{task_id}/download/pdf`
  - `GET /api/ppt/task/{task_id}/download/html-zip`

#### `/ai-scoring/app/services/ppt/pptx_renderer_html.py`

要做：

- 继续保留现有 PPTX 输出。

---

## 八、推荐开发顺序（代码层）

### 第一批：必须优先动

1. `ppt_service.py`
   - 门禁统一
   - 评分覆盖按 HTML 重算
   - 内部修复痕迹剥离
   - 补图绑定一致性

2. `ppt_router.py`
   - 统一任务详情/下载/状态接口字段

3. `PptHistoryDetail.vue`
   - 下载条件卡工作台化
   - 当前页补图
   - 当前页一键修复

4. `ppt.js`
   - 统一任务详情/交付状态/评分覆盖刷新入口

### 第二批：主流程优化

1. `PptEditor.vue`
   - 真实进度与等待体验
2. `pipeline_coordinator.py`
   - 细粒度进度
3. `html_generator.py`
   - 视口/字体统一

### 第三批：结构治理

1. 拆 `PptEditor.vue`
2. 清理双前端定位
3. 导出增强

---

## 九、验收方式建议

每个批次都建议按下面方式验收：

### 接口层

- 用真实任务 ID 测：
  - 任务详情
  - 评分覆盖
  - 下载判断
  - 补图刷新

### 页面层

- 测 3 条主路径：
  - 预览页补图
  - 下载条件卡一键处理
  - 一键补评分点

### 回归层

- 确认不会再次出现：
  - 明明补图了还一直提示缺图
  - 明明补评分点了但分数不变
  - 页面通过了但仍不可下载

---

## 十、建议下一步

如果继续往下执行，最推荐的顺序是：

1. 先按本清单把 `P0` 彻底补齐
2. 再整理一份“接口字段标准文档”
3. 最后再进组件拆分和导出增强

这样可以避免边拆组件边修逻辑，导致回归成本过高。

