# PPT Editor 历史记录、单页重生成与前端编辑规划

## 目标

当前 `/ppt-editor` 已经能生成论文 PPT 和路演 PPT，但生成后缺少持续编辑能力。下一步要把它从“一次性生成页”升级为“可恢复、可修改、可迭代的 PPT 工作台”。

## 功能边界

第一阶段做工程闭环，不追求一次性复刻完整 PowerPoint：

- 历史记录：保存并展示历史 PPT 任务，包括源文件、任务状态、页数、导出文件、日志和项目目录。
- 历史打开：用户点击历史任务后，恢复预览、日志、视觉审查、版本记录，可继续下载或编辑。
- 单页保存：用户在前端修改当前页文本或备注后，保存回后端 SVG 工作区。
- 单页重生成：用户选择页码、输入反馈，调用现有 refine 管线，仅重生成指定页面。
- 版本记录：展示 refine 归档版本，方便回看每轮优化。

第二阶段再做更强的可视化编辑：

- 拖拽移动文本/图形。
- 图片替换和裁切。
- 形状、颜色、字体、层级编辑。
- 更完整的 PPTX 反向解析与页面对象模型。

## 数据设计

优先复用 `session_state.json`，不新增复杂数据库表：

- `Session` 保存上传素材：文件名、大小、类型、路径。
- `Job` 保存任务：状态、进度、模型、语言、风格、项目目录、导出路径、日志事件。
- 项目目录保存生成资产：`manuscript.md`、`design_spec.md`、`svg_output/`、`svg_final/`、`exports/`、`critic_history.json`、`svg_archive/`、`notes/`。

如果后续要多用户隔离，再迁移到 MySQL 表：

- `ppt_sessions`
- `ppt_jobs`
- `ppt_job_events`
- `ppt_slide_versions`
- `ppt_assets`

## 后端接口

新增：

- `GET /api/ppt/history`：返回历史任务列表。
- `GET /api/ppt/history/{job_id}`：返回单个任务详情、日志和上传素材信息。

复用：

- `GET /api/ppt/preview/{job_id}`：加载可编辑页面。
- `PUT /api/ppt/preview/{job_id}/slides/{slide_index}`：保存当前页 SVG、备注和页面文档。
- `POST /api/ppt/preview/{job_id}/slides`：新增空白页。
- `DELETE /api/ppt/preview/{job_id}/slides/{slide_index}`：删除页。
- `POST /api/ppt/refine`：传 `target_pages` 实现单页或多页重生成。
- `GET /api/ppt/versions/{job_id}`：版本列表。
- `GET /api/ppt/download/{job_id}`：下载 PPTX。

## 前端步骤

1. 左侧增加“最近记录”入口，打开历史抽屉。
2. 选中历史任务后加载预览、日志、审查记录和版本记录。
3. 中间预览区升级为编辑工作台：缩略图、工具栏、画布、备注。
4. 工具栏先提供可用动作：新增页、编辑文字、保存、删除页、下载。
5. 右侧增加“反馈优化”：选择当前页或全部页，输入反馈，调用 refine。
6. 右侧增加“版本记录”：显示历史 refine 归档。
7. 修改后刷新预览，保证前端看到的是保存后的真实 SVG。

## 风险与约束

- 现阶段 SVG 是主要编辑对象，不是完整 PPTX 对象模型。
- 文本编辑优先支持 `<text>` 节点，复杂 `<tspan>` 会尽量保留但不保证复杂排版完全无损。
- 单页重生成依赖原项目目录中的 `manuscript.md` 和 `design_spec.md`，历史任务如果缺这两个文件，只能预览和下载，不能重生成。
- 路演 PPT 的正式导出门禁仍保留，避免缺证据的版本被当作正式成品导出。
