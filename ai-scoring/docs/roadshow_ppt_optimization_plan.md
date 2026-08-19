# 路演 PPT 生成优化方案与开发步骤

依据：`roadshow_task_c9229dd1b0b4_analysis.md`

## 1. 优化目标

把当前“能生成路演形态”的版本，推进到“可稳定生成职业院校技能大赛作品汇报草稿，并能拦截不合格正式导出”的版本。

这次不优先追求更多模板，而优先补三道闸门：

1. 事实闸门：项目名、指标、设备、实操步骤、团队匿名角色不得被后续 agent 改写或编造。
2. 素材闸门：PDF 表格裁图、时间安排表、团队分工表不能被误当作架构图/数据流图/系统截图。
3. 导出闸门：草稿可以预览，但正式 PPTX 导出前必须检查占位符、证据缺失、无来源数据和素材错配。

## 2. 问题到修法映射

| 报告问题 | 根因 | 本轮修法 |
| --- | --- | --- |
| 项目名称漂移 | strategist 重新抽象标题 | 新增 `locked_project_title`，写入 manuscript 隐藏元数据，并传入 strategist |
| 指标被模型补造 | KPI 没有结构化来源约束 | 抽取 `verified_metrics`，提示词只允许使用已验证指标 |
| 联网搜索无效结果污染 | 模型自述被当成 web finding | 过滤“没有联网工具/很抱歉/无 URL”等无效结果 |
| 图乱截 | 表格区域裁图被当成设计素材 | 对 figure inventory 增加 roadshow 语义分类和 `allowed_for_roadshow` 门禁 |
| 正式版仍可导出 | 无合规门禁 | export/re-export 前执行 `roadshow_export_gate_report.json` 检查 |

## 3. 新增模块

新增：

`ai-scoring/app/services/ppt/agent/backend/orchestrator/roadshow_quality.py`

职责：

- `extract_locked_facts`：从资料分析和 manuscript 中抽取锁定事实。
- `roadshow_figure_token_inventory_block`：只向 manuscript agent 暴露安全素材 token。
- `filter_roadshow_figure_inventory`：只向 strategist/executor 暴露可用图片。
- `valid_external_findings`：过滤无效联网搜索结果。
- `evaluate_roadshow_export_gate`：正式导出前检查并写入门禁报告。

## 4. 开发步骤

### 阶段一：事实锁定

- 在资料分析完成后抽取 `locked_project_title`。
- 抽取材料中可确认的指标，形成 `verified_metrics`。
- 把锁定事实注入 Pass 2、Pass 3、视觉策划和 review prompt。
- 在最终 manuscript 第一页加入隐藏注释：`locked_project_title`。
- strategist 生成后强制修正 Project Name。

验收：

- 生成稿不应把“智能仓储设备健康监测与安全作业辅助系统”改写成另一个项目名。
- KPI 页面不能把无来源目标写成已达成结果。

### 阶段二：素材门禁

- 对所有 PDF 抽图增加 roadshow 语义判断。
- `table_region` 默认禁止作为路演正式图片使用。
- 没有安全图时，manuscript 必须写 `待补充`，而不是乱用 `[[FIG:...]]`。
- strategist 和 executor 只接收过滤后的图片库存。

验收：

- 表格裁图不能再被当成架构图、技术选型图、数据流图。
- 架构/流程/证据页应优先用原生 SVG 结构表达。

### 阶段三：正式版导出门禁

- pipeline 正常生成 SVG 供预览。
- export 阶段执行门禁。
- re-export 接口也执行同一门禁。
- 门禁失败时写入 `roadshow_export_gate_report.json`，并返回阻断原因。

拦截项：

- 团队/学校/电话/邮箱等占位符。
- 疑似自动编造的报告编号或精确时间戳。
- 实操/数据/证据页仍存在 `待补充` 证据。
- SVG 使用了被判定为不安全的 PDF 表格/页面裁图。

### 阶段四：页面质量继续提升

本轮先不重做全部视觉模板。下一轮再做：

- 确定性生成五层架构页。
- 确定性生成输入/操作/输出/证据实操页。
- 确定性生成证据链页。
- 引入真实系统截图补充流程。
- 增加 partial resume，从失败页继续生成。

## 5. 当前实现状态

已完成本轮第一批代码：

- 新增 roadshow quality 模块。
- roadshow_agent 接入锁定事实与安全素材 token。
- strategist 接收 roadshow guardrails 与过滤后的 figure inventory。
- pipeline 在 roadshow export 前执行正式版门禁。
- re-export 接口执行同一门禁。
- research enrichment 过滤无效 web finding，并避免用单字标题构造 web query。

后续建议以一个 8-15 页验证任务先测：

1. 上传同一份比赛说明书。
2. 开启路演 PPT。
3. 观察 manuscript 是否保留正确项目名。
4. 检查第 9-11 页是否不再乱用 PDF 表格裁图。
5. 如果证据缺失，确认 PPT 可预览但正式导出被阻止并给出门禁报告。
