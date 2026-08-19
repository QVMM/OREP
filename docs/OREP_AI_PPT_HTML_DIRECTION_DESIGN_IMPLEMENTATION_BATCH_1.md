# OREP AI 生成 PPT 式 HTML

## 编导与页面设计第一批落地实施清单

> 目标：把下面 4 份设计规则文档，翻译成第一批真正可以开工的系统改造任务。

> 依赖文档：
>
> 1. [页面契约表 V1](/Users/liuyixing/项目/OREP/docs/OREP_AI_PPT_HTML_PAGE_CONTRACT_TABLE_V1.md)
> 2. [页系样张方案 V1](/Users/liuyixing/项目/OREP/docs/OREP_AI_PPT_HTML_PAGE_SERIES_STYLE_SYSTEM_V1.md)
> 3. [章节编导模板 V1](/Users/liuyixing/项目/OREP/docs/OREP_AI_PPT_HTML_STORY_DIRECTING_TEMPLATE_V1.md)
> 4. [单页重设计协议 V1](/Users/liuyixing/项目/OREP/docs/OREP_AI_PPT_HTML_SINGLE_PAGE_REDESIGN_PROTOCOL_V1.md)

> 这份清单只做第一批最值的落地，不追求一次覆盖全部页面类型。

---

## 1. 第一批总目标

第一批改造不求“一次把所有页面都变成终极形态”，而是先做到 4 件事：

1. **让大纲层具备幕次和页面角色意识**
2. **让生成层具备页面契约意识**
3. **让视觉审查具备导演式约束输出**
4. **让 repair 流程真正分流到单页重设计**

换句话说，第一批先把：

- 编导规则
- 页面契约
- 页系样张
- 单页重设计协议

真正接进系统，不再只是文档存在。

---

## 2. 第一批范围

为了控制风险，第一批只覆盖最关键的 6 类页面：

1. 目录 / 赛程页
2. 政策 / 背景证据页
3. 方案总览 / 价值闭环页
4. 技术架构 / 核心技术页
5. 实操步骤 / 结果证据页
6. 总结收束页

原因：

- 这 6 类页面最能决定“像不像比赛级 PPT”
- 也是当前最容易出：
  - HTML 味
  - 模板化
  - 焦点弱
  - 缺证据
  - 章节顺序不稳

---

## 3. 后端数据结构第一批改造

## 3.1 Round 2 输出字段扩充

### 目标

让大纲不再只是一串页标题，而是带“编导信息”的页面计划。

### 需要新增的字段

建议在 Round 2 输出的每一页中增加：

```json
{
  "page_type": "policy_context_evidence",
  "act_phase": "act_1",
  "story_goal": "证明项目与政策/行业背景高度相关",
  "transition_role": "从背景引入项目定义",
  "served_scoring_dimensions": ["应用价值", "讲解效果"],
  "contract_id": "policy_context_evidence_v1",
  "page_series_type": "report_light",
  "page_visual_role": "evidence_anchor"
}
```

### 涉及文件

- [round2_narrative.md](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/prompts/round2_narrative.md)
- [pipeline_coordinator.py](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/adapter_code/pipeline_coordinator.py)
- [ppt_service.py](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/ppt_service.py)

### 验收标准

- `outline_json` 中每页都带上述元数据
- 前端可读到 `page_type / act_phase / contract_id`

---

## 3.2 新增页面契约注册表

### 目标

让页面契约不只存在 md 里，而变成系统可读配置。

### 建议形式

新增配置文件，例如：

- `/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/page_contracts.py`

或：

- `/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/contracts/page_contracts_v1.json`

### 第一批写入的契约

- `agenda_timeline_v1`
- `policy_context_evidence_v1`
- `solution_overview_value_loop_v1`
- `tech_architecture_core_v1`
- `practice_step_ioe_v1`
- `team_summary_closing_v1`

### 每份契约必须包含的字段

- `contract_id`
- `page_type`
- `act_phase`
- `page_goal`
- `required_blocks`
- `forbidden_blocks`
- `primary_visual_type`
- `required_evidence_types`
- `common_failure_modes`
- `repair_strategy_hint`

### 涉及文件

- 新增配置文件
- [ppt_service.py](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/ppt_service.py)

### 验收标准

- 后端能按 `contract_id` 取出页面契约
- 历史详情接口中能把契约摘要返回给前端

---

## 4. Round 3 第一批改造

## 4.1 Round 3 从“内容充实”升级成“页面设计元数据生成”

### 目标

Round 3 不再只是吐很多文案，而是先定这页怎么设计。

### 需要新增的输出字段

```json
{
  "page_goal": "让评委理解端边云架构为什么合理",
  "must_answer": [
    "系统分层是什么",
    "为什么这样设计",
    "关键技术难点是什么"
  ],
  "required_blocks": [
    "主架构图",
    "关键技术点",
    "可信性说明"
  ],
  "primary_visual_type": "architecture_diagram",
  "layout_intent": "central_diagram_with_side_explanations",
  "required_evidence_types": ["code_screenshot", "metric_chart"],
  "max_key_messages": 1,
  "max_support_points": 3
}
```

### 涉及文件

- [round3_enrich.md](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/prompts/round3_enrich.md)
- [pipeline_coordinator.py](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/adapter_code/pipeline_coordinator.py)

### 验收标准

- `enriched_pages` 中新增这些设计元数据
- 后续 Round 4 和 repair 都能读取

---

## 4.2 第一批页系样张基线接入

### 目标

让 Round 3 / Round 4 不只是知道风格名，而是知道对应的页系样张方向。

### 第一批基线

- `tech_dark`
- `report_light`
- `practice_demo`

### 样张层信息需要进入元数据

- `style_family`
- `page_series_type`
- `visual_mood`
- `contrast_level`
- `frame_density`

### 涉及文件

- [ppt_service.py](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/ppt_service.py)
- 风格样张生成相关逻辑
- [PptStylePreviewSection.vue](/Users/liuyixing/项目/OREP/frontend/user/src/components/ppt/PptStylePreviewSection.vue)

### 验收标准

- 风格选择后，Round 3 能拿到对应页系类型
- style preview 不再只输出封面样张

---

## 5. Round 4 第一批改造

## 5.1 Round 4 接入页面契约与页系样张

### 目标

让 Round 4 不再自由生成，而是按契约和页系方向落地 HTML。

### 实施原则

Round 4 输入不再只依赖：

- 标题
- 文案
- section

而是同时依赖：

- `contract_id`
- `page_type`
- `page_goal`
- `required_blocks`
- `primary_visual_type`
- `required_evidence_types`
- `page_series_type`

### 涉及文件

- [round4_html_generation_optimized.md](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/prompts/round4_html_generation_optimized.md)
- [html_generator.py](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/html_generator.py)
- [pipeline_coordinator.py](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/adapter_code/pipeline_coordinator.py)

### 第一批硬规则

- 目录页必须有时间结构
- 政策页必须有证据位主区
- 技术页必须有主结构图
- 实操页必须有 IOE 闭环
- 总结页必须有收束结论主卡

### 验收标准

- 同一 `page_type` 的页面结构明显更稳定
- 页面更少出现“网页卡片拼装感”

---

## 5.2 正文禁用词与草稿态内容彻底隔离

### 目标

禁止这些内容进入终稿正文：

- `[待补充]`
- `[待核实]`
- `建议上传`
- `证据位`
- `占位图`

### 涉及文件

- [round4_html_generation_optimized.md](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/prompts/round4_html_generation_optimized.md)
- [ppt_service.py](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/ppt_service.py)

### 验收标准

- 草稿态内容只能留在元数据，不进入正式 HTML 正文

---

## 6. 视觉审查第一批改造

## 6.1 视觉检察官增加“导演式约束输出”

### 目标

视觉审查结果不再只是问题列表，还要能指导重设计。

### 新增输出字段

```json
{
  "focus_constraints": {
    "expected_primary_focus": "architecture_diagram",
    "max_primary_visuals": 1,
    "focus_conflict": true
  },
  "layout_constraints": {
    "avoid_regions": ["bottom_right"],
    "suggested_layout_type": "central_diagram_with_caption"
  },
  "evidence_constraints": {
    "needs_evidence_anchor": true,
    "min_evidence_slots": 1
  },
  "directing_notes": [
    "当前页像说明书，不像上台镜头",
    "主信息重心不够集中"
  ]
}
```

### 涉及文件

- [vision_judge_service.py](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/vision_judge_service.py)
- [ppt_service.py](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/ppt_service.py)

### 验收标准

- 视觉审查结果能直接被单页重设计消费

---

## 7. Repair / 单页重设计第一批改造

## 7.1 在 repair 前先做根因分类

### 目标

把页面分成：

- `html_polish`
- `structure_rebuild`
- `evidence_attach_or_wait`

### 涉及文件

- [ppt_service.py](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/ppt_service.py)

### 验收标准

- 不再所有问题都直接进入普通 repair

---

## 7.2 新增 `design_context`

### 目标

给单页重设计传完整上下文，而不只传当前 HTML。

### 建议字段

- `page_type`
- `act_phase`
- `transition_role`
- `contract_id`
- `page_goal`
- `served_scoring_dimensions`
- `primary_visual_type`
- `required_evidence_types`
- `confirmed_materials`
- `visual_review_constraints`
- `repair_history_summary`

### 涉及文件

- [ppt_service.py](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/ppt_service.py)
- [usePptRepairWorkspace.js](/Users/liuyixing/项目/OREP/frontend/user/src/composables/usePptRepairWorkspace.js)

### 验收标准

- repair preview 请求体中包含 `design_context`

---

## 7.3 重设计输出先产“结构方案”，再产 HTML

### 目标

让单页重设计从“修 HTML”升级成“先重做页面设计”。

### 第一批输出结构

```json
{
  "redesign_summary": "...",
  "new_layout_type": "central_diagram_with_side_explanations",
  "primary_visual_plan": "...",
  "content_block_plan": ["..."],
  "evidence_plan": "...",
  "removal_plan": ["..."],
  "html": "<html>...</html>"
}
```

### 涉及文件

- repair prompt
- [ppt_service.py](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/ppt_service.py)

### 验收标准

- repair history 中能看到本次重设计摘要
- 后端可以基于 `new_layout_type` 和 `evidence_plan` 做二次检查

---

## 8. 前端第一批接入

## 8.1 大纲页显示页面类型与幕次

### 目标

让用户在 Step 1 就知道：

- 这页属于哪一幕
- 这页是什么页面类型

### 涉及文件

- [PptOutlineEditor.vue](/Users/liuyixing/项目/OREP/frontend/user/src/components/ppt/PptOutlineEditor.vue)
- [PptEditor.vue](/Users/liuyixing/项目/OREP/frontend/user/src/views/PptEditor.vue)

### 验收标准

- 每个大纲页卡片显示：
  - `第一幕/第二幕/...`
  - `技术架构页 / 实操证据页 / 总结页`

---

## 8.2 预览页显示页面契约摘要

### 目标

让当前页工作台不只显示“这页有问题”，还显示：

- 这页本来应该承担什么职责

### 涉及文件

- [PptHtmlWorkbench.vue](/Users/liuyixing/项目/OREP/frontend/user/src/components/ppt/PptHtmlWorkbench.vue)
- [usePptCurrentPageWorkspace.js](/Users/liuyixing/项目/OREP/frontend/user/src/composables/usePptCurrentPageWorkspace.js)

### 验收标准

- 当前页右侧能看到：
  - 页面类型
  - 幕次
  - 当前页目标
  - 应服务的评分点

---

## 8.3 修复预览弹窗显示“单页重设计摘要”

### 目标

让用户知道这次不是小修，而是重做这页。

### 涉及文件

- 修复预览相关前端组件/逻辑

### 验收标准

- 结构型页修复时，预览弹窗显示：
  - 本次重设计目标
  - 新版式类型
  - 为什么这样改

---

## 9. 第一批落地顺序

建议严格按下面顺序：

### 第一步

新增页面契约注册表 + Round 2 输出字段

### 第二步

改 Round 3，让它生成页面设计元数据

### 第三步

改 Round 4，让 HTML 生成按契约与页系样张落地

### 第四步

改视觉审查，新增导演式约束

### 第五步

改 repair，接入 `design_context` 和重设计输出

### 第六步

改前端大纲页与预览页，把新字段展示出来

---

## 10. 第一批验收方式

建议选 1 套真实任务 + 1 套标准测试任务来对比：

### 对比前后看 6 个指标

1. 技术页是否更像技术架构页
2. 实操页是否更像证据主导页
3. 总结页是否更像收束页
4. 模板页风险页数是否下降
5. 视觉焦点失败页数是否下降
6. 单页重设计后的通过率是否高于普通 repair

---

## 11. 最终原则

这份第一批落地实施清单的核心原则只有一句：

> 先把“编导规则、页面契约、页系样张、重设计协议”接进生成主链，再去继续修 bug，收益才会最大。

否则就会持续出现：

- 系统越来越稳
- 但最终页面仍然只是“更稳定的普通 HTML”

这正是当前最应该避免的方向。
