# V5 Creative Director Upgrade Development Plan

## 目标

当前 V5 已经能稳定生成 PPTX，并且图示错位、溢出、repair 卡死的问题已经明显下降。下一阶段不再优先追求“页面不坏”，而是补上“页面凭什么好看”的产品能力：每页在 MiMo 写 HTML 前先确定创意概念、第一眼焦点、主视觉占比、构图打法、卡片限制和失败重生条件。

## 当前问题判断

这几轮生成的共同问题是：

- 页面偏淡、偏轻，像系统 UI，而不是参赛级 PPT。
- 卡片、表格、浅色描边模块出现频率过高。
- 封面和目录没有形成强记忆点。
- 很多页有内容，但第一眼不知道重点。
- 图示更规范了，但图示没有自动变成页面视觉焦点。
- repair 主要修几何问题，不能把平庸页修成高级页。

所以后续开发重点是新增“创意总监层”和“设计质量门禁”，而不是继续堆长提示词。

## 七步开发路径

### 1. Creative Director Plan

新增 `app/services/ppt/v5/creative_director.py`。

每页输出：

- `creative_mode`：本页创意模式。
- `first_glance_focus`：1-3 秒内必须读到的重点。
- `visual_anchor`：主视觉类型、占比、位置、字号/图形强度。
- `composition_contract`：硬构图合同。
- `card_policy`：卡片数量、是否允许等权卡片阵列。
- `density_contract`：信息密度和可见文字目标。
- `style_energy`：页面视觉能量，不再只用“高级、好看”形容词。
- `forbidden_layouts`：本页禁用版式。
- `regeneration_triggers`：生成后需要重生的条件。

### 2. Playbook 从建议升级为构图合同

保留现有 `v5_slide_playbook_library.json`，但新增合同字段：

- `composition_contracts`
- `primary_visual_min_ratio`
- `card_limit`
- `allowed_visual_motifs`
- `must_not_repeat_with_previous`

第一阶段先由 `creative_director.py` 根据现有 playbook 派生合同，避免一次性大改 JSON。

### 3. MiMo Prompt 接入创意计划

在 `_body_user_prompt` 中注入：

- `creative_director_plan`
- `creative_execution_contract`
- 更明确的设计方向：先执行创意计划，再执行 visual contract/playbook/diagram。

MiMo 必须在 `.mimo-body-root` 写入：

- `data-creative-mode`
- `data-dominant-visual`
- `data-focus-text`

### 4. 反卡片机制

将卡片从默认方案降级为辅助元素：

- 普通内容页最多 3-4 个卡片。
- 重点图示页主视觉必须超过主体区 45%-60%。
- 禁止 4 个以上同尺寸卡片作为主体。
- 如果连续页面都是卡片结构，下一页强制换成图解、路径、证据墙、强数字或场景化构图。

### 5. Design Quality Audit

新增 `app/services/ppt/v5/design_quality_auditor.py`。

第一版从 HTML 结构和已有 render audit 指标判断：

- 是否缺少 `.mimo-body-root` 追踪属性。
- 是否卡片数量过多。
- 是否主视觉占比不足。
- 是否大面积空白。
- 是否缺少焦点文字。
- 是否像网页后台或上传控件。

低分页面不进入普通 repair，而是回到创意计划层重生。

### 6. 首页和目录特殊流程

封面、目录不按普通内容页处理：

- 封面先确定行业主视觉素材策略，再写 HTML。
- 目录必须是章节地图、景观目录页或路线图，不允许普通列表/时间线。
- 如果没有素材，调用图片生成模型生成行业通用主视觉。

### 7. 验证策略

先不直接跑完整 38 页。每次改动先跑目标页：

- 1：首页
- 2：目录
- 8：方案/架构
- 12：数据/流程
- 24：证据链
- 30：价值页
- 35：团队/执行

通过后再跑完整智慧农业 JSON。

## 本轮开发范围

本轮先完成：

- 新增 Creative Director Plan 模块。
- 接入 clean pipeline。
- 接入 page contract。
- 注入 MiMo prompt。
- 补充单测。

暂不做：

- 不立即接图片生成模型。
- 不重写全部 playbook JSON。
- 不替换现有 render audit。
- 不直接改 PPTX 导出逻辑。

## 验收标准

- `build_clean_pipeline` 输出 `v5_creative_director_plans`。
- 每个 `v5_page_contract` 都带 `creative_director_plan`。
- `_body_user_prompt` JSON 中包含 `creative_director_plan` 和 `creative_execution_contract`。
- 首页/目录/架构/证据链/价值页的 creative mode 不同。
- 单测通过。

