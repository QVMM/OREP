# 职业院校技能大赛 PPT Agent 前半段改造设计方案

> 目标：参考 paper-ppt-agent 的「先理解资料、再组织叙事、再生成逐页稿件」逻辑，将当前面向科研论文的 PPT 生成前半段，改造成面向职业院校技能大赛作品汇报的前半段。后半段继续复用 Strategist、SVG Executor、Critic、Preview、Export 和逐页生成机制。

---

## 1. 设计结论

当前 paper-ppt-agent 的高质量来源不是模板，而是一条稳定的中间产物链：

```text
PDF/TeX 解析
  -> ParsedPaper
  -> Deep Analysis
  -> Narrative Arc
  -> Slide Manuscript
  -> Self Review
  -> Design Spec
  -> Page-by-page SVG
  -> Critic Repair
  -> PPTX Export
```

职业院校技能大赛 PPT 不能直接套用论文逻辑，因为比赛汇报的核心不是「科研贡献」，而是「作品是否真实、完整、可落地、可验证、符合赛制表达」。因此前半段需要改造成：

```text
资料接收
  -> 资料分析 Agent
  -> 缺资料诊断 Agent
  -> 比赛大纲 Agent
  -> 证据链 Agent
  -> 职业赛制 Manuscript Agent
  -> 比赛版 Review Agent
  -> Design Spec
  -> Page-by-page SVG
  -> Critic Repair
  -> PPTX Export
```

后半段可以保留，重点改造前半段 6 个 agent。

---

## 2. 反向推理：高质量比赛 PPT 到底需要什么资料

不是用户给什么就直接生成什么，而是系统要从「最终 PPT 必须看起来可信、完整、可答辩」反推出必需资料。

### 2.0 评分标准硬约束

依据用户提供的《世界职业院校技能大赛总决赛评分要素.pdf》，比赛总分 100 分，评分原则是「突出能力导向、解决实际问题、体现创新因素、确保公平可比」。评委依据参赛团队的技能操作和现场讲解情况评分，避免主观印象影响。

因此 PPT 生成不是普通项目介绍，而是要服务于五类评分指标：

| 评分指标 | 权重 | 观测点 | 对 PPT 生成的直接要求 |
|---|---:|---|---|
| 技能水平 | 60 分 | 操作规范性 10、技能熟练度 15、任务难易度 15、技术先进性 15、现场讲解效果 5 | 必须突出实操过程、操作规范、关键技术难点、前沿技术应用和讲解逻辑 |
| 职业素养 | 10 分 | 职业道德与行为规范 4、工匠精神 3、安全意识 3 | 必须体现诚信合规、知识产权、质量意识、细节控制、安全与风险防范 |
| 应用价值 | 10 分 | 实用性 4、经济性 3、可持续性 3 | 必须说明实际问题、落地价值、资源利用、绿色低碳和未来方向 |
| 团队合作 | 10 分 | 团队精神 5、沟通协作 5 | 必须体现匿名化角色分工、协作机制、突发情况应对，不展示个人姓名 |
| 创新创意 | 10 分 | 创新意识 4、创新成效 6 | 必须区分创意来源、技术/流程/服务优化、数字化改良和实际成效 |

这意味着刚才的方案需要补强：

1. **技能水平权重最大**：原方案强调证据和成果，但对「操作规范性、技能熟练度、任务难易度」的证据要求不够强。
2. **现场讲解效果是评分项**：需要让 Manuscript Agent 同时生成讲解逻辑、重点提示和时间控制建议。
3. **职业素养不是泛泛合规**：需要显式覆盖知识产权、职业伦理、工匠精神、质量意识、安全规范和劳动保护。
4. **应用价值不只讲价值**：需要覆盖实用性、经济性、可持续性，并能对接产业升级、区域发展、乡村振兴、高质量就业等战略需求。
5. **团队合作是独立 10 分**：方案必须支持匿名化团队角色、协作流程、沟通机制、突发情况补台，而不是完全隐藏团队维度。
6. **创新创意要看成效**：不能只写创新点，要写创新带来的具体改良、优化或可验证效果。

### 2.0.1 现场执行约束：按 55 分钟设计

比赛官方规定 60 分钟，但系统应按约 55 分钟进行 PPT 和实操设计，预留约 5 分钟作为设备切换、异常处理、评委追问缓冲。比赛形式是选手携带 PPT 和自有设备到现场进行讲解与实操演示，因此 PPT 的职责不只是展示结论，还要成为现场执行脚本。

建议默认时间结构：

| 环节 | 建议时长 | 主要内容 | PPT 作用 |
|---|---:|---|---|
| 开场与项目定位 | 3-5 分钟 | 作品主题、场景、问题、目标 | 快速建立评委理解 |
| 背景需求与任务难点 | 6-8 分钟 | 真实问题、任务挑战、评分点对齐 | 解释为什么值得做、难在哪里 |
| 方案与技术架构 | 8-10 分钟 | 架构、模块、数据流、关键技术 | 证明方案完整、技术选择恰当 |
| 现场实操演示 | 18-22 分钟 | 设备接入、关键操作、异常处理、结果输出 | 展示技能水平、操作规范、熟练度 |
| 数据证据与成果验证 | 7-9 分钟 | 指标、样本、验证方法、结果对比 | 证明成果可信 |
| 职业素养、团队协作、创新价值 | 5-7 分钟 | 安全质量、角色分工、应用价值、创新成效 | 覆盖非技能水平的 40 分 |
| 总结与缓冲 | 2-4 分钟 | 价值收束、改进方向、应对追问 | 控制节奏，避免超时 |

因此，Competition Agent 必须额外生成：

1. `run_of_show`：55 分钟讲解和实操编排。
2. `demo_script`：现场实操步骤、设备状态、操作者、讲解者、预期输出。
3. `equipment_checklist`：自带设备、软件环境、网络/离线方案、备用材料。
4. `team_roles`：匿名团队角色和交接关系。
5. `contingency_plan`：设备异常、网络异常、数据异常、时间超限时的备选讲法。

### 2.1 高质量比赛 PPT 的最终判断标准

一套职业院校技能大赛 PPT 至少要让评委相信：

1. 项目背景真实，问题有来源，不是空泛命题。
2. 需求和痛点明确，能说明为什么要做这个作品。
3. 技术方案完整，有系统结构、模块分工、数据流或业务流。
4. 实操过程可复现，有操作规范、输入、操作、输出、证据。
5. 技能熟练度能被看见，例如流程流畅度、时间控制、关键操作精准度。
6. 任务难度和复杂问题解决能力能被说明。
7. 技术先进性有依据，能说明新标准、新技术、新场景或数字化技术的恰当应用。
8. 现场实操环节可执行，有设备、操作者、步骤、预期输出和异常预案。
9. 数据和成果可验证，有指标、样本、来源、测试方法。
10. 职业素养清楚，包括职业伦理、知识产权、质量意识、安全规范和风险防范。
11. 应用价值明确，包括实用性、经济性、可持续性。
12. 团队协作可信，有匿名角色分工、现场配合和补台机制，但不暴露姓名、学校、电话、邮箱等个人或单位敏感信息。
13. 创新点可信，并能说明创新成效，不能只是口号。
14. 不编造数据，不把猜测写成事实。
15. 正式版导出时，关键结论必须有证据或来源。

### 2.2 必需资料分层

| 资料层级 | 资料类型 | 对 PPT 质量的影响 | 缺失后果 |
|---|---|---|---|
| A 级必需 | 赛项/任务方向、作品主题、应用场景、用户对象、核心问题 | 决定整套 PPT 的方向 | 容易生成空泛汇报 |
| A 级必需 | 系统/作品功能清单、技术路线、模块划分 | 决定架构页和方案页是否成立 | 页面只能写概念，无法像作品 |
| A 级必需 | 实操流程、操作规范、关键步骤、输入输出、时间控制 | 决定技能水平 60 分是否能被支撑 | 比赛感很弱，技能熟练度无法体现 |
| A 级必需 | 现场实操脚本、设备清单、演示环境、备用方案 | 决定现场演示是否可执行 | PPT 只能讲，不能支撑现场实操 |
| A 级必需 | 成果数据、测试结果、样本说明、验证方法 | 决定正式版是否可信 | 不能正式导出 |
| A 级必需 | 证据材料：截图、日志、报告、代码片段、设备照片、表格 | 支撑结论和成果页 | 无证据时只能草稿 |
| A 级必需 | 任务难点、复杂问题、关键技术挑战 | 支撑任务难易度和技能水平 | 看起来像普通展示，缺少比赛竞争力 |
| B 级重要 | 背景政策、行业数据、标准规范、同类方案 | 增强项目必要性 | 需要联网补充 |
| B 级重要 | 职业素养材料：安全规范、风险点、异常情况、质量控制、知识产权说明 | 支撑职业素养 10 分 | 评委追问时薄弱 |
| B 级重要 | 团队匿名角色、分工、协作流程、突发情况应对 | 支撑团队合作 10 分 | 团队合作页空泛或违规展示个人信息 |
| B 级重要 | 应用价值材料：成本、效率、资源利用、绿色低碳、推广场景 | 支撑应用价值 10 分 | 价值页只剩口号 |
| B 级重要 | 创新点、推广价值、改进方向 | 增强总结页质量 | 结尾变空 |
| B 级重要 | 现场讲解重点、演示顺序、时间分配 | 支撑现场讲解效果 | PPT 能看但不好讲 |
| C 级辅助 | Logo、配色偏好、素材图片 | 影响视觉风格 | 可由模型生成替代 |

### 2.3 用户资料的三种情况

#### 情况一：资料完整

用户提供 PDF、Word、图片、表格、日志、截图、说明文档等。

系统策略：

- 尽量从用户资料中抽取内容。
- 建立证据 token，例如 `[[EVID:log_001]]`、`[[SCREEN:alarm_panel_01]]`、`[[DATA:test_accuracy_table]]`。
- 所有关键结论绑定证据或来源。
- 可以直接进入完整生成。

输出等级：

- 可以生成正式版。
- 如果无敏感信息、关键结论有证据，可开放正式导出。

#### 情况二：有资料但不完整

用户提供部分说明或少量截图，但缺数据、缺流程、缺测试方法。

系统策略：

- 已有资料进入证据池。
- 缺失资料进入「补充清单」。
- 可联网补充背景、行业数据、标准规范，但不能联网编造用户项目结果。
- 允许生成 B 级草稿，可预览。
- 缺关键证据时禁止正式版导出。

输出等级：

- 草稿可预览。
- 正式版需要用户补填 A 级缺口。

#### 情况三：几乎没有资料，只有文字描述

用户只输入一句或一段项目描述。

系统策略：

- 先做意图拆解和资料需求反推。
- 联网只补公共背景，不生成虚假项目成果。
- 系统生成「资料采集问卷」让用户补填。
- 可先生成低置信度草稿，但成果数据、实操证据、测试结论必须标记为待补充。

输出等级：

- 只能生成 C 级草稿。
- 不允许正式导出。

---

## 3. 6 个前半段 Agent 总体结构

### 3.1 对应 paper-ppt-agent 的逻辑映射

| paper-ppt-agent 阶段 | 作用 | 比赛版对应 |
|---|---|---|
| ParsedPaper | 将论文解析成结构化对象 | CompetitionMaterialBundle |
| Pass 1 Deep Reading | 深读论文，找问题、方法、证据、贡献 | 资料分析 Agent |
| Pass 2 Narrative Arc | 设计论文演讲叙事 | 比赛大纲 Agent |
| Pass 3 Manuscript | 生成逐页演示稿 | 职业赛制 Manuscript Agent |
| Pass 4 Review | 三视角评审并修订 | 比赛版 Review Agent |
| Figure Token Contract | 论文图 token，防止乱用图片 | 证据链 Agent |
| Structure Validation | 检查页数和 page_type | 缺资料诊断 + 比赛结构校验 |

### 3.2 新的中间产物

建议引入 6 个核心中间文件：

```text
material_bundle.json
missing_requirements.json
competition_outline.md
evidence_chain.json
competition_manuscript.md
competition_review.md
```

后续 `design_spec.md` 和 SVG 生成继续沿用现有链路。

---

## 4. Agent 1：资料分析 Agent

### 4.1 目标

把用户上传的资料和文字描述转成结构化的比赛资料包 `material_bundle.json`。

它对应 paper-ppt-agent 的 `ParsedPaper + Pass 1 Deep Reading`，但分析对象从「论文」变成「参赛作品资料」。

### 4.2 输入

- 用户文字描述
- 上传文件：PDF、Word、PPT、Excel、图片、日志、代码片段、压缩包
- 用户选择或系统识别的赛项方向
- 联网补充资料结果，若启用

### 4.3 输出：material_bundle.json

建议结构：

```json
{
  "project": {
    "title": "",
    "subtitle": "",
    "competition_type": "",
    "scenario": "",
    "target_users": [],
    "problem_statement": "",
    "value_proposition": ""
  },
  "solution": {
    "functions": [],
    "technical_route": [],
    "modules": [],
    "architecture_layers": [],
    "data_flow": [],
    "operation_flow": []
  },
  "implementation": {
    "tools_or_platforms": [],
    "hardware_or_devices": [],
    "software_stack": [],
    "deployment_environment": "",
    "key_steps": [],
    "operation_standards": [],
    "skill_difficulty_points": [],
    "time_control_notes": [],
    "demo_script": [],
    "equipment_checklist": [],
    "environment_requirements": [],
    "contingency_plan": []
  },
  "presentation_plan": {
    "target_duration_minutes": 55,
    "run_of_show": [],
    "speaker_flow": [],
    "demo_segments": [],
    "transition_cues": [],
    "buffer_minutes": 5
  },
  "results": {
    "metrics": [],
    "test_cases": [],
    "sample_description": "",
    "validation_methods": []
  },
  "score_alignment": {
    "skill_level": {
      "operation_norms": [],
      "skill_proficiency": [],
      "task_difficulty": [],
      "technical_advancement": [],
      "presentation_logic": []
    },
    "professionalism": {
      "ethics_and_ip": [],
      "craftsmanship_and_quality": [],
      "safety_awareness": []
    },
    "application_value": {
      "practicality": [],
      "economy": [],
      "sustainability": []
    },
    "teamwork": {
      "anonymous_roles": [],
      "collaboration_process": [],
      "demo_role_handoffs": [],
      "emergency_response": []
    },
    "innovation": {
      "innovation_awareness": [],
      "innovation_effectiveness": []
    }
  },
  "evidence_assets": [],
  "external_sources": [],
  "risks": [],
  "innovation_points": [],
  "improvement_plan": [],
  "privacy_findings": []
}
```

### 4.4 分析规则

1. 不得把用户没有提供的项目结果写成事实。
2. 识别并屏蔽姓名、学校、电话、邮箱等个人或单位信息。
3. 将事实、推断、待确认内容分开。
4. 将公共背景资料和用户项目资料分开。
5. 能绑定来源的内容必须记录来源。
6. 对图片、日志、截图、表格生成稳定证据 token。
7. 按官方 5 项评分指标建立 `score_alignment`，避免后续大纲遗漏高权重评分点。

### 4.5 需要用户提供什么

最少需要：

- 作品主题
- 应用场景
- 解决的问题
- 已完成的功能
- 有无实操或测试结果
- 是否有操作规范、时间控制、关键难点
- 是否有现场实操脚本、设备清单、演示环境和备用方案
- 是否有安全、质量、知识产权或团队协作说明

最好提供：

- 作品说明书
- 系统截图
- 操作流程截图
- 现场实操脚本和设备清单
- 演示环境、账号、网络/离线数据要求
- 测试数据表
- 日志或报告
- 实物照片或部署环境照片
- 代码/接口/配置片段

---

## 5. Agent 2：缺资料诊断 Agent

### 5.1 目标

判断当前资料是否足以生成比赛 PPT，并输出缺口清单、追问问题、生成等级和导出门禁。

这是 paper-ppt-agent 没有的能力，因为论文通常自带完整内容；比赛项目资料经常不完整。

### 5.2 输入

- `material_bundle.json`
- 赛制要求
- 目标页数范围：35-45 页
- 证据资产列表

### 5.3 输出：missing_requirements.json

```json
{
  "readiness_level": "A|B|C",
  "can_generate_preview": true,
  "can_export_official": false,
  "blocking_gaps": [],
  "recommended_questions": [],
  "optional_questions": [],
  "evidence_gaps": [],
  "risk_flags": [],
  "draft_policy": {
    "allowed_claim_types": [],
    "forbidden_claim_types": []
  }
}
```

### 5.4 评分维度

| 维度 | 权重 | 判断内容 |
|---|---:|---|
| 技能水平资料完备度 | 60 | 是否能支撑操作规范性、技能熟练度、任务难易度、技术先进性、现场讲解效果 |
| 职业素养资料完备度 | 10 | 是否能支撑职业道德、知识产权、工匠精神、质量意识、安全意识 |
| 应用价值资料完备度 | 10 | 是否能支撑实用性、经济性、可持续性 |
| 团队合作资料完备度 | 10 | 是否能支撑匿名角色分工、团队精神、沟通协作、突发情况应对 |
| 创新创意资料完备度 | 10 | 是否能支撑创新意识和创新成效 |

内部可再细分为：

| 子维度 | 阻断规则 |
|---|---|
| 主题与场景 | 缺失时不能生成完整 PPT |
| 技术方案 | 缺失时架构页、模块页降级为草稿 |
| 操作规范与熟练度 | 缺失时技能水平相关页面不能正式导出 |
| 任务难度 | 缺失时无法突出比赛竞争力 |
| 技术先进性 | 缺失时不能声称应用新技术或前沿技术 |
| 数据成果 | 缺来源、样本、验证方法时正式导出阻断 |
| 职业素养 | 缺安全/质量/伦理材料时需要生成追问 |
| 团队合作 | 缺角色和协作说明时团队合作页只能草稿 |
| 创新成效 | 只有创新口号、无成效证据时正式导出阻断 |

建议等级：

- A：≥ 80，可生成正式版。
- B：60-79，可生成草稿预览，正式导出受限。
- C：< 60，仅生成资料补全建议或低置信度草稿。

### 5.5 反向追问策略

追问不应该问泛泛的“请补充更多资料”，而应问能直接提升 PPT 质量的问题。

必问问题示例：

1. 作品主要解决哪个真实场景中的问题？
2. 系统包含哪些核心功能？请按 3-6 个模块列出。
3. 一次完整实操从输入到输出经历哪些步骤？
4. 有哪些可验证成果？例如准确率、耗时、完成率、故障率、节省成本等。
5. 每个成果数据来自哪里？样本量是多少？如何测试？
6. 有没有截图、日志、表格、报告能证明这些结果？
7. 哪些操作有行业标准、岗位规范或安全规范要求？
8. 哪些步骤最能体现技能熟练度？是否有时间控制或操作流畅度证据？
9. 任务难点在哪里？解决了哪些复杂问题？
10. 用到了哪些新标准、新技术、新场景或数字化技术？为什么选择它们？
11. 现场实操要带哪些设备？需要什么软件、账号、网络或离线数据环境？
12. 现场实操由哪些匿名角色完成？谁讲解、谁操作、谁记录、谁处理异常？
13. 如果设备、网络、数据或演示环境出问题，有什么备用方案？
14. 项目有哪些风险控制、劳动保护或异常处理机制？
15. 团队可以匿名描述为哪些角色？角色之间如何协作？遇到突发情况如何补台？
16. 项目如何体现实用性、经济性、可持续性？
17. 创新点带来了什么成效？有无数据、截图或对比证明？
18. 哪些内容不能公开展示？

---

## 6. Agent 3：比赛大纲 Agent

### 6.1 目标

生成符合职业院校技能大赛表达习惯的 35-45 页大纲，而不是论文式 hook-method-result。

它对应 paper-ppt-agent 的 Pass 2 Narrative Arc，但叙事目标从「讲清论文贡献」变成「证明作品可信、完整、可落地」。

### 6.2 输入

- `material_bundle.json`
- `missing_requirements.json`
- 赛项方向
- 页数范围：35-45 页
- 用户生成要求

### 6.3 输出：competition_outline.md

大纲需要包含：

- 章节结构
- 每页标题
- 页面类型
- 页面目的
- 所需证据
- 是否允许草稿
- 视觉建议

### 6.4 推荐结构

默认 38 页左右：

| 模块 | 页数 | 内容 |
|---|---:|---|
| 封面 | 1 | 标题、副标题、团队名称或匿名团队称呼、主题视觉 |
| 目录 | 1 | 章节导览 |
| 项目背景与真实问题 | 4-5 | 场景、痛点、需求、目标，对接实际问题 |
| 任务与技能挑战 | 3-4 | 任务难度、复杂问题、关键技能点、操作规范 |
| 方案总体设计 | 5-7 | 总体架构、模块分工、数据流、关键技术 |
| 现场实操准备 | 2-3 | 自带设备、软件环境、操作角色、演示输入、备用方案 |
| 实操流程与技能展示 | 8-10 | 输入、操作、输出、证据、时间控制、关键界面 |
| 数据证据与成果 | 5-7 | 指标、样本、测试方法、结果、来源 |
| 职业素养与风险控制 | 3-4 | 职业伦理、知识产权、工匠精神、质量意识、安全与风险防范 |
| 应用价值 | 2-3 | 实用性、经济性、可持续性、推广场景 |
| 团队合作 | 2-3 | 匿名角色分工、协作流程、突发情况应对 |
| 创新创意 | 3-4 | 创新意识、技术/流程/服务优化、创新成效 |
| 总结与改进 | 1-2 | 价值收束、后续优化 |
| 结尾 | 1 | 简洁收束 |

### 6.5 页面类型建议

```text
cover
agenda
section_overview
problem_context
requirement_analysis
skill_challenge
operation_standard
demo_setup
architecture
module_design
data_flow
practice_process
operation_step
demo_runbook
evidence_result
kpi_dashboard
professionalism
safety_quality
application_value
teamwork
risk_control
innovation
improvement
ending
```

这里不建议使用 paper-ppt-agent 的 `chapter` 思路作为显性章节过渡页，因为用户已明确不喜欢章节过渡页。可以保留章节分组，但页面本身要有信息价值。

### 6.6 大纲校验规则

1. 总页数必须 35-45。
2. 不能出现个人信息。
3. 数据成果页必须绑定证据或标记待补充。
4. 架构、流程、成果三类页面必须存在。
5. 技能水平相关页面必须占最大比重，体现 60 分权重。
6. 职业素养、应用价值、团队合作、创新创意必须各有明确页面承接。
7. 必须包含 55 分钟现场执行节奏和实操环节安排。
8. 必须包含设备/环境准备、角色分工、备用方案，不得只写“现场演示”四个字。
9. 不允许大量空泛介绍页。
10. 每页只能承担一个核心任务。

---

## 7. Agent 4：证据链 Agent

### 7.1 目标

建立比赛 PPT 的证据 token 体系，防止模型编造数据、乱用截图、乱写来源。

它对应 paper-ppt-agent 的 `[[FIG:id]]` 合同，但比赛版要比论文图更复杂。

### 7.2 证据类型

| Token 类型 | 示例 | 用途 |
|---|---|---|
| `[[EVID:...]]` | `[[EVID:test_report_001]]` | 测试报告、验收记录 |
| `[[SCREEN:...]]` | `[[SCREEN:dashboard_alarm]]` | 系统截图、操作界面 |
| `[[LOG:...]]` | `[[LOG:device_upload_202605]]` | 日志、接口调用记录 |
| `[[DATA:...]]` | `[[DATA:accuracy_table]]` | 数据表、统计结果 |
| `[[CODE:...]]` | `[[CODE:risk_rule_engine]]` | 代码或配置片段 |
| `[[DEMO:...]]` | `[[DEMO:live_device_connect]]` | 现场实操步骤、设备演示、操作记录 |
| `[[ROLE:...]]` | `[[ROLE:operator_a]]` | 匿名团队角色和现场分工 |
| `[[PLAN:...]]` | `[[PLAN:network_fallback]]` | 设备/网络/数据异常备用方案 |
| `[[SRC:...]]` | `[[SRC:policy_standard_001]]` | 联网资料、标准、政策、行业报告 |
| `[[TODO:...]]` | `[[TODO:sample_size]]` | 缺失但必要的信息 |

### 7.3 输入

- 上传文件解析结果
- OCR 结果
- 图片/日志/表格元数据
- 联网资料结果
- `material_bundle.json`

### 7.4 输出：evidence_chain.json

```json
{
  "assets": [
    {
      "token": "[[SCREEN:dashboard_alarm]]",
      "type": "screen",
      "title": "告警看板截图",
      "source": "uploaded_file",
      "path": "sources/images/dashboard_alarm.png",
      "supports_claims": ["异常告警可视化", "处理状态可追踪"],
      "privacy_status": "clean",
      "confidence": 0.91
    }
  ],
  "claims": [
    {
      "claim": "系统可完成设备异常识别与告警闭环",
      "support_tokens": ["[[SCREEN:dashboard_alarm]]", "[[LOG:alarm_log_001]]"],
      "status": "supported"
    }
  ],
  "unsupported_claims": [],
  "privacy_findings": []
}
```

### 7.5 证据链规则

1. 成果数据必须绑定 `DATA` 或 `EVID`。
2. 操作流程必须至少绑定 `SCREEN`、`LOG`、`EVID` 中的一类。
3. 现场实操环节必须绑定 `DEMO`，并尽量关联 `SCREEN`、`LOG`、`DATA` 或 `EVID`。
4. 团队合作页面必须使用 `ROLE`，只能描述匿名角色和协作流程。
5. 备用方案必须使用 `PLAN`，覆盖设备、网络、数据、时间超限等风险。
6. 背景和行业判断可以绑定 `SRC`。
7. 用户项目成果不能只靠 `SRC`，必须有用户证据。
8. 没证据的强结论要降级为草稿表达。
9. 出现个人信息时，证据资产必须标记 `privacy_status: blocked|needs_redaction`。

---

## 8. Agent 5：职业赛制 Manuscript Agent

### 8.1 目标

生成逐页 `competition_manuscript.md`，作为后续 Strategist 和 SVG Executor 的输入。

它对应 paper-ppt-agent 的 Pass 3 Slide Manuscript，但写作规则要改成比赛汇报。

### 8.2 输入

- `material_bundle.json`
- `missing_requirements.json`
- `competition_outline.md`
- `evidence_chain.json`
- 用户要求

### 8.3 输出格式

沿用 paper-ppt-agent 的页分隔机制，便于后半段复用：

```markdown
<!-- page_type: architecture -->
## 系统总体架构

**核心结论**：系统采用采集层、处理层、识别层、应用层、审计层形成端到端闭环。

- 采集层负责设备状态、运行参数和现场数据接入
- 处理层完成清洗、缓存、阈值判断和离线补传
- 识别层输出异常分类和风险等级
- 应用层形成告警、工单和报告

[[SCREEN:architecture_sketch]]
[[LOG:data_upload_log]]

[DIAGRAM: 五层架构流程，突出数据从采集到审计的闭环]
```

现场实操页示例：

```markdown
<!-- page_type: demo_runbook -->
## 现场实操：设备接入到告警闭环

**核心结论**：本环节用真实设备数据完成“接入、识别、告警、处置、留痕”的完整闭环。

- 演示输入：设备状态数据、异常阈值配置、离线补传数据包
- 操作角色：`[[ROLE:operator_a]]` 完成设备接入，`[[ROLE:speaker_b]]` 同步讲解关键判断
- 预期输出：告警记录、处置结果、审计日志
- 异常预案：网络异常时切换到 `[[PLAN:offline_demo_dataset]]`

[[DEMO:live_device_connect]]
[[SCREEN:alarm_dashboard]]
[[LOG:audit_trace_log]]

[PROCESS: 现场实操流程，按 01 接入 -> 02 识别 -> 03 告警 -> 04 处置 -> 05 留痕 展示]
```

### 8.4 写作规则

1. 每页一个核心结论。
2. 先讲结论，再给证据。
3. 所有成果、数据、闭环、风险控制必须尽量绑定证据 token。
4. 禁止出现姓名、学校、电话、邮箱。
5. 不得把 `TODO` 写成已完成事实。
6. 没证据时使用草稿表达，例如「可在正式版中补充测试报告」。
7. 页面内容要适合 16:9 PPT，不写长段落。
8. 35-45 页内保持章节节奏，不为了凑页写空话。
9. 生成 `speaker_notes` 或页面讲解提示时，必须按 55 分钟总时长进行节奏控制。
10. 实操相关页面必须明确演示输入、操作者、讲解者、操作步骤、预期输出、证据和异常预案。
11. 团队分工页面必须使用匿名角色，例如“方案设计角色”“实操执行角色”“测试记录角色”“应急保障角色”。

### 8.5 页面角色约束

| 页面角色 | 必须包含 | 不应包含 |
|---|---|---|
| 封面 | 大标题、副标题、团队名称或匿名团队称呼、主题视觉提示 | 数据表、长说明、个人信息 |
| 目录 | 章节名称、每章一句说明 | 太多标签和细节 |
| 背景页 | 场景、痛点、需求来源 | 无来源的宏大判断 |
| 架构页 | 层级、模块、数据流、闭环 | 大段文字 |
| 实操页 | 输入、操作、输出、证据 | 抽象口号 |
| 现场执行页 | 55 分钟时间编排、设备清单、角色交接、备用方案 | 只写“现场演示”但无步骤 |
| 成果页 | KPI、样本、来源、验证方法 | 无来源数字 |
| 风险页 | 风险、控制措施、证据 | 空泛安全声明 |
| 总结页 | 价值、推广、改进 | 重复前文 |

---

## 9. Agent 6：比赛版 Review Agent

### 9.1 目标

在进入设计生成前，对 `competition_manuscript.md` 做比赛视角的质量审查和修订。

它对应 paper-ppt-agent 的 Pass 4 Self-Evaluation，但评审视角要换。

### 9.2 三类评审视角

1. **赛项评委视角**
   - 是否符合比赛作品汇报逻辑？
   - 是否看得出真实完成了作品？
   - 是否有技术含量、任务难度、实操闭环和现场讲解重点？

2. **技术实现视角**
   - 架构是否自洽？
   - 模块和流程是否能跑起来？
   - 数据、接口、日志、截图是否支持结论？
   - 是否体现技能熟练度、操作规范和技术先进性？

3. **合规与证据视角**
   - 是否出现个人信息？
   - 是否有无来源数据？
   - 是否把猜测写成事实？
   - 是否覆盖职业道德、知识产权、质量意识、安全意识？
   - 是否满足正式导出门禁？

### 9.3 输出：competition_review.md

```markdown
# Competition Manuscript Review

## Scores
- 技能水平支撑：42/60
- 职业素养支撑：8/10
- 应用价值支撑：7/10
- 团队合作支撑：6/10
- 创新创意支撑：7/10
- 证据可信度：2/5
- 视觉可执行性：4/5

## Blocking Issues
- Slide 22 的准确率缺少样本数量和测试方法，正式版导出前必须补充。
- Slide 12-15 的实操流程缺少操作规范和时间控制证据，技能熟练度支撑不足。

## Revisions Applied
- 将无证据的“准确率达到 95%”改为“当前草稿待补充准确率测试结果”。

## Export Gate
- Preview: allowed
- Official Export: blocked
```

### 9.4 门禁规则

| 问题 | 预览 | 正式导出 |
|---|---|---|
| 缺少部分背景来源 | 允许 | 可提示但不阻断 |
| 缺少关键成果证据 | 允许 | 阻断 |
| 出现个人信息 | 阻断或自动脱敏后允许 | 阻断 |
| 数据来源不明 | 允许草稿 | 阻断 |
| 实操流程缺证据 | 允许草稿 | 阻断 |
| 缺少现场实操脚本或设备准备说明 | 允许草稿 | 阻断 |
| 缺少设备/网络/数据异常备用方案 | 允许草稿 | 阻断 |
| 技能水平 60 分核心观测点缺失 | 允许草稿 | 阻断 |
| 职业素养完全未覆盖 | 允许草稿 | 阻断 |
| 团队合作出现真实姓名/学校 | 阻断或脱敏后允许 | 阻断 |
| 页数不在 35-45 | 阻断 | 阻断 |

---

## 10. 用户需要提供的资料清单

### 10.1 最小可生成

用户至少需要填写：

```json
{
  "project_title": "作品名称",
  "scenario": "应用场景",
  "problem": "解决的问题",
  "target_users": "使用对象",
  "core_functions": ["功能1", "功能2", "功能3"],
  "technical_route": "技术路线简述",
  "operation_flow": ["步骤1", "步骤2", "步骤3"],
  "operation_standards": "操作规范、行业标准或岗位要求",
  "skill_difficulty": "最能体现技能水平的难点",
  "team_roles": "匿名角色分工，例如方案设计、实操执行、测试记录",
  "demo_plan": "55分钟现场讲解和实操安排，包括设备、环境、角色、备用方案",
  "known_results": "已有成果或待测试说明"
}
```

这个级别只能生成 C/B 级草稿。

### 10.2 推荐高质量资料

建议用户上传：

- 作品说明书
- 需求分析文档
- 系统架构图或草图
- 功能截图
- 实操流程截图
- 现场实操脚本、设备清单、演示环境说明
- 离线数据包、备用账号、网络异常预案
- 操作规范、行业标准、岗位要求说明
- 关键技能操作视频截图或步骤记录
- 任务进度和时间利用记录
- 日志文件
- 测试数据表
- 测试报告
- 代码片段或接口文档
- 设备/现场/部署图片
- 风险控制说明
- 安全规范、劳动保护、异常处理说明
- 知识产权、开源组件或引用资料说明
- 匿名团队角色分工和协作过程说明
- 成本、资源利用、绿色低碳或可持续性说明
- 改进计划

### 10.3 正式版必要资料

正式导出至少需要：

1. 作品主题和场景明确。
2. 核心功能和技术路线明确。
3. 至少一条完整实操闭环。
4. 有 55 分钟现场执行计划，包含讲解、实操、设备切换和缓冲时间。
5. 有设备清单、演示环境、匿名角色分工和异常备用方案。
6. 技能水平核心观测点有支撑：操作规范、技能熟练度、任务难度、技术先进性、讲解逻辑。
7. 至少一组可追溯成果数据。
8. 成果数据有来源、样本或验证方法。
9. 职业素养至少覆盖安全、质量、职业伦理或知识产权中的关键项。
10. 应用价值至少覆盖实用性，并尽量覆盖经济性和可持续性。
11. 团队合作用匿名角色表达，不出现真实姓名、学校、电话、邮箱。
12. 创新创意有成效说明，不能只有口号。
13. 关键页面无个人信息。
14. 风险或限制没有被隐藏。

---

## 11. 与现有代码的改造关系

### 11.1 保留

保留现有：

- `strategist_agent.py`
- `svg_executor.py`
- `svg_critic.py`
- `visual_critic.py`
- `pipeline.py` 后半段机制
- preview / websocket / export
- 一页一页生成机制
- template 可选机制，但默认不用模板

### 11.2 替换或新增

建议新增：

```text
backend/orchestrator/competition/
  material_agent.py
  missing_agent.py
  outline_agent.py
  evidence_agent.py
  manuscript_agent.py
  review_agent.py
  models.py
  prompts/
    material_analysis.md
    missing_diagnosis.md
    competition_outline.md
    evidence_chain.md
    competition_manuscript.md
    competition_review.md
```

建议不要直接删除 `research_agent.py`，而是增加 `mode = paper | competition`。这样后续如果还要支持论文 PPT，不会互相污染。

### 11.3 Pipeline 建议

```text
if mode == "paper":
    paper-ppt-agent 原流程

if mode == "competition":
    parse materials
    material_agent.run()
    missing_agent.run()
    if readiness_level == C and user wants official:
        stop and ask for materials
    outline_agent.run()
    evidence_agent.run()
    manuscript_agent.run()
    review_agent.run()
    if preview allowed:
        strategist_agent.create_design_spec()
        svg_executor.generate_svg_pages()
        export draft
    if official export requested:
        check export gate
```

---

## 12. 改造难度评估

| 模块 | 难度 | 原因 |
|---|---|---|
| 资料分析 Agent | 中 | 需要支持多种资料来源和结构化提取 |
| 缺资料诊断 Agent | 中 | 规则清晰，但要设计好评分和追问 |
| 比赛大纲 Agent | 中 | 需要稳定控制 35-45 页和比赛结构 |
| 证据链 Agent | 中高 | 需要 token、证据绑定、隐私检查、导出门禁 |
| Manuscript Agent | 中 | 可参考 paper-ppt-agent Pass 3，但提示词要重写 |
| Review Agent | 中 | 可参考 Pass 4，但评分维度要换 |
| 后半段接入 | 低中 | 已有机制可复用，主要是 page_type 和证据 token 适配 |

整体难度：中等偏大，但不是重做系统。

最大风险不是技术，而是领域规则不够明确导致模型继续写成科研或政企汇报。

---

## 13. 开发顺序建议

### Phase 1：先打通比赛稿件链路

目标：不追求视觉，先让前半段生成比赛风格 `competition_manuscript.md`。

任务：

1. 新增 `CompetitionMaterialBundle` 数据结构。
2. 新增资料分析 Agent。
3. 新增缺资料诊断 Agent。
4. 新增比赛大纲 Agent。
5. 新增 manuscript Agent。
6. 用固定模拟数据跑出 38 页 manuscript。

验收：

- 页数 35-45。
- 不像论文 PPT。
- 架构、实操、证据、成果页齐全。
- 缺资料时有 TODO 和导出门禁。

### Phase 2：证据链和门禁

目标：让系统知道哪些结论能正式导出。

任务：

1. 新增证据 token。
2. 图片/日志/表格生成证据资产。
3. unsupported claim 检查。
4. 正式版导出 gate。

验收：

- 无证据成果页只能草稿。
- 有证据成果页能绑定来源。
- 个人信息能被识别并阻断。

### Phase 3：接入现有后半段

目标：让比赛版 manuscript 进入 Strategist 和 SVG Executor。

任务：

1. 扩展 page_type。
2. 修改 strategist 提示词，让它理解比赛页面角色。
3. 修改 executor 证据 token 展示规则。
4. 保持默认自由设计，不强制模板。

验收：

- 38 页可完整生成。
- 首页、目录、架构、实操、成果页符合比赛表达。

### Phase 4：质量优化

目标：让生成结果真正接近可用比赛 PPT。

任务：

1. 增加比赛版 Review Agent。
2. 增加比赛版视觉规则。
3. 增加页面类型模板或参考规则，但不变成套壳。
4. 增加用户补资料交互。

---

## 14. 最重要的设计原则

1. 不要把比赛 PPT 改成论文 PPT。
2. 不要把职业赛制要求变成政企模板风格。
3. 不要让模型编造项目数据。
4. 证据链比视觉更优先。
5. 草稿和正式版必须分级。
6. 用户资料不足时，系统要反推缺口，而不是硬生成。
7. 后半段逐页生成机制值得保留。
8. 默认自由设计，模板只作为可选能力。

---

## 15. 6 个 Agent 的 Prompt 骨架

这一节用于后续开发。每个 agent 都应该有独立 prompt，不建议把所有要求塞进一个超长 prompt。

### 15.1 资料分析 Agent Prompt 骨架

System：

```text
你是职业院校技能大赛作品资料分析专家。你的任务不是写 PPT，而是把用户提供的文字、文件、截图、表格、日志和联网资料整理成结构化资料包。

你必须区分：
1. 用户资料中的事实
2. 联网资料中的公共背景
3. 合理推断
4. 待用户确认的信息

禁止编造项目数据、比赛结果、测试指标、学校名称、团队成员、联系方式。
发现姓名、学校、电话、邮箱等信息时，必须标记 privacy_findings。
必须按官方评分指标建立 score_alignment：技能水平 60、职业素养 10、应用价值 10、团队合作 10、创新创意 10。
```

User：

```text
## 用户文字描述
{user_instruction}

## 上传资料解析结果
{parsed_materials}

## 联网资料
{web_research_results}

## 输出要求
输出 material_bundle.json。
只输出 JSON，不要输出解释。
```

关键要求：

- 输出 JSON 必须可解析。
- 任何没有证据的数据写入 `assumptions` 或 `unknowns`，不能写入 `results.metrics`。
- 上传文件、截图、日志、表格要生成候选 evidence asset。
- 必须抽取能支撑技能水平的资料：操作规范、技能熟练度、任务难度、技术先进性、讲解逻辑。
- 必须抽取现场执行资料：55 分钟 run_of_show、demo_script、equipment_checklist、team_roles、contingency_plan。

### 15.2 缺资料诊断 Agent Prompt 骨架

System：

```text
你是职业院校技能大赛 PPT 生成前的资料门诊专家。
你的任务是判断当前资料是否足以生成高质量比赛 PPT，并反推出最应该向用户追问什么。

你不能要求用户泛泛补充资料。
每个问题都必须说明：为什么重要、影响哪些页面、是否阻断正式导出。
诊断评分必须以官方五类评分指标为主轴，尤其优先检查技能水平 60 分是否有足够资料支撑。
```

User：

```text
## 结构化资料包
{material_bundle_json}

## 证据资产列表
{evidence_assets}

## 目标
生成 35-45 页职业院校技能大赛作品汇报 PPT。

## 输出要求
输出 missing_requirements.json。
```

关键要求：

- 给出 `readiness_level: A|B|C`。
- 给出 `can_generate_preview` 和 `can_export_official`。
- 把问题分成 `blocking_gaps`、`recommended_questions`、`optional_questions`。
- 正式导出门禁必须保守。
- 缺少技能水平核心观测点时，正式导出必须阻断或降级。

### 15.3 比赛大纲 Agent Prompt 骨架

System：

```text
你是职业院校技能大赛作品汇报大纲策划专家。
你的任务是设计 35-45 页 PPT 的内容结构，让评委能看懂项目背景、方案、实操闭环、数据证据、职业素养、应用价值、团队合作、创新创意。
技能水平权重 60 分，因此大纲必须把最大篇幅给操作规范、技能熟练度、任务难度、技术先进性和现场讲解逻辑。
比赛官方时长 60 分钟，但大纲必须按约 55 分钟设计，预留 5 分钟给设备切换、异常处理和评委追问缓冲。

你要参考 paper-ppt-agent 的叙事设计逻辑：每页有明确角色，每页推进理解。
但不要写科研论文式大纲，不要围绕论文 contribution/method/result 展开。
```

User：

```text
## 结构化资料包
{material_bundle_json}

## 缺资料诊断
{missing_requirements_json}

## 目标页数
35-45 页，默认 38 页。

## 输出要求
输出 competition_outline.md。
每页必须包含：页码、页面类型、标题、页面目的、核心信息、所需证据、视觉建议、草稿/正式状态。
```

关键要求：

- 必须包含封面、目录、架构、技能挑战、实操流程、数据证据/成果、职业素养、应用价值、团队合作、创新创意、改进总结。
- 必须包含现场实操准备和现场实操流程页面，并按 55 分钟总时长安排讲解与演示节奏。
- 不使用空白章节过渡页。
- 缺证据页面要标记为草稿。

### 15.4 证据链 Agent Prompt 骨架

System：

```text
你是比赛 PPT 的证据链审计专家。
你的任务是把截图、日志、表格、报告、代码、联网来源和 PPT 中的关键结论建立可追溯关系。

你不能替用户证明不存在的成果。
如果结论缺少证据，必须标记 unsupported。
```

User：

```text
## 结构化资料包
{material_bundle_json}

## 大纲
{competition_outline_md}

## 文件资产清单
{asset_inventory}

## 联网来源
{external_sources}

## 输出要求
输出 evidence_chain.json。
```

关键要求：

- 为证据生成 token：`EVID`、`SCREEN`、`LOG`、`DATA`、`CODE`、`DEMO`、`ROLE`、`PLAN`、`SRC`、`TODO`。
- 为每条关键 claim 绑定 support_tokens。
- 区分用户项目证据和公共背景来源。
- 检查隐私风险。
- 现场实操步骤、团队角色、备用方案必须分别使用 `DEMO`、`ROLE`、`PLAN`。

### 15.5 职业赛制 Manuscript Agent Prompt 骨架

System：

```text
你是职业院校技能大赛作品汇报 PPT 的逐页稿件作者。
你要根据大纲和证据链生成可直接交给设计 agent 的 slide manuscript。

规则：
1. 每页一个核心结论。
2. 先结论，后证据。
3. 不编造数据。
4. 不出现个人信息。
5. 使用证据 token 支撑关键结论。
6. 缺证据内容只能写成待补充或草稿表达。
7. 输出必须使用 standalone --- 分隔每一页。
8. 按官方评分指标组织内容，尤其要让技能水平 60 分的观测点在页面中可见。
9. 团队合作只能使用匿名角色，不得出现真实姓名、学校、电话、邮箱。
10. 必须按约 55 分钟生成讲解节奏，实操页必须说明设备、操作者、讲解者、预期输出和异常预案。
```

User：

```text
## 结构化资料包
{material_bundle_json}

## 大纲
{competition_outline_md}

## 证据链
{evidence_chain_json}

## 缺资料诊断
{missing_requirements_json}

## 输出要求
输出 competition_manuscript.md。
每页开头使用 <!-- page_type: xxx -->。
```

关键要求：

- 页面数量必须 35-45。
- page_type 必须是比赛版页面类型。
- 证据 token 必须原样引用，不能发明 token。
- `TODO` 不能写成事实。
- 必须生成适合现场讲解的核心结论和演示顺序提示。
- 现场实操相关页面必须引用 `DEMO`、`ROLE`、`PLAN` token。

### 15.6 比赛版 Review Agent Prompt 骨架

System：

```text
你是职业院校技能大赛 PPT 赛前审查组，由三个视角组成：
1. 赛项评委
2. 技术实现专家
3. 合规与证据审计员

你要审查 manuscript 是否能进入设计生成，是否允许正式导出。
如果发现问题，应修订 manuscript，但不能编造证据。
评分必须使用官方五类指标：技能水平 60、职业素养 10、应用价值 10、团队合作 10、创新创意 10。
必须额外检查：是否按 55 分钟准备，是否包含现场实操环节、设备清单、匿名角色分工、角色交接和异常备用方案。
```

User：

```text
## Manuscript
{competition_manuscript_md}

## 证据链
{evidence_chain_json}

## 缺资料诊断
{missing_requirements_json}

## 输出要求
输出 competition_review.md。
如果需要修订，同时输出 revised_competition_manuscript.md。
```

关键要求：

- 给出官方五类评分：技能水平 60、职业素养 10、应用价值 10、团队合作 10、创新创意 10。
- 额外给出证据可信度和视觉可执行性，但它们不替代官方评分。
- 明确 `Preview: allowed|blocked`。
- 明确 `Official Export: allowed|blocked`。
- 如果阻断，必须说明阻断页面和原因。
- 缺少现场实操脚本、设备准备或备用方案时，正式导出必须阻断。

---

## 16. 开发时最容易踩的坑

1. **把大纲写成论文结构**
   - 错误：背景、相关工作、方法、实验、结论。
   - 正确：场景问题、需求目标、系统设计、实操闭环、数据证据、风险控制、改进推广。

2. **联网资料污染用户项目事实**
   - 联网只能补公共背景、行业趋势、标准规范。
   - 不能用联网资料替代用户作品的测试结果。

3. **缺资料时仍然生成正式口吻**
   - 缺证据的成果必须写成草稿或待补充。
   - 正式导出必须受门禁控制。

4. **证据 token 只做展示，不做约束**
   - token 必须参与 claim 校验、manuscript 校验、导出门禁。

5. **过早优化视觉**
   - 先让前半段生成正确的比赛 manuscript。
   - 再进入 Strategist/SVG 视觉优化。

6. **让模板决定内容**
   - 比赛 PPT 的结构由赛制逻辑决定。
   - 模板只能辅助视觉，不应该反向决定页面内容。
