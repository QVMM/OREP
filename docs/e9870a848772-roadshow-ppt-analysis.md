# e9870a848772 路演 PPT 生成质量分析

分析对象：`e9870a848772`

产物目录：`ai-scoring/uploads/ppt_agent/workspaces/roadshow_ppt_ppt169_20260515_231320`

分析时间：2026-05-16

## 一、结论

这份 17 页路演 PPT 的问题，主要不是 SVG 执行器完全不会画，而是上游提示词给出的页面策划过于“内容容器化”：大量页面被定义成三列、四卡片、2x2 网格、信息卡片、表格。执行器收到的任务天然就是“把文字放进卡片”，而不是“把业务逻辑转化为可理解的系统图、操作图、证据图”。

所以它目前的状态是：

- 页面能生成，风格基本统一。
- 架构、流程、目标页有一定可读性。
- 但重点页缺少“评委一眼看懂”的主视觉。
- 实操页还像功能说明卡，不像现场操作导览页。
- 成果页仍有大量 `[待补充]`，正式导出被门禁拦截是合理的。
- 封面、目录的 `双击编辑文字/空表格` 是前端编辑器写入污染，不属于原始模型生成质量问题。

## 二、原始页面整体观感

总览图：

`ai-scoring/uploads/ppt_agent/workspaces/roadshow_ppt_ppt169_20260515_231320/analysis_render_output/contact_sheet.jpg`

按原始 `svg_output` 看，页面大致分为三类：

1. **可接受页**
   - 第 6 页：解决方案概述，有“痛点 -> 方案”的转换关系。
   - 第 8 页：五层架构页，结构清楚，视觉比一般卡片页好。
   - 第 9 页：技术选型与数据流，虽然密，但具备流程理解力。
   - 第 11 页：目标页，有指标条和时长信息。

2. **一般页**
   - 第 4 页：项目定位，三栏卡片过于普通，缺少“项目一句话价值”。
   - 第 5 页：痛点页，内容是对的，但视觉还是列表，冲击力不足。
   - 第 10 页：关键技术页，仍是四卡片，技术亮点没有机制图。
   - 第 13-16 页：实操模块页，像说明书，不像比赛现场实操指挥页。

3. **明显不合格页**
   - 第 17 页：主要成果页仍保留 `[待补充]`，不能正式使用。
   - 第 13-16 页：缺少真实截图、日志、接口返回、设备状态等证据资产。
   - 封面与目录若看 `svg_final`，有编辑器残留元素，需要另行清理。

## 三、逐页问题

| 页码 | 页面 | 主要问题 | 根因判断 |
|---|---|---|---|
| 01 | 封面 | 原始封面尚可，但缺少主题插画或真实系统感；`svg_final` 有编辑器残留 | 封面提示词只说“抽象剪影”，没有要求设备/仓储/数据流复合插画 |
| 02 | 目录 | 原始目录可用，但信息密度偏低；`svg_final` 有空表格和双击文字污染 | 编辑器保存污染；目录设计缺少“55分钟现场流程”强约束 |
| 03 | 章节页 | 简洁但意义弱 | 章节页可以保留，但 35-45 页时要减少纯过渡页 |
| 04 | 项目定位 | 三张卡片，重点不突出 | `visual_strategy` 明确要求“三个卡片并列” |
| 05 | 行业痛点 | 仍是左右列表，缺少痛点链路或现场问题照片 | 没有真实素材，提示词也未强制“痛点-后果-评委关注点”图解 |
| 06 | 解决方案概述 | 相对较好，有端边智用审流程 | 这是因为提示词明确要求五阶段流程图 |
| 07 | 章节页 | 可用但信息价值低 | 结构页，不是质量问题 |
| 08 | 系统总体架构 | 本套里较好，但仍偏静态堆叠 | 提示词指定了五层架构，因此执行器能画出来 |
| 09 | 技术选型与数据流 | 信息完整，但技术栈和数据流分裂，缺少“技术如何支撑流程”的映射 | 提示词只要求左技术栈、右数据流，没有要求连线说明 |
| 10 | 关键技术点 | 四卡片，技术深度没有被画出来 | `visual_strategy` 明确要求 2x2 卡片，导致必然卡片化 |
| 11 | 项目目标 | 指标条可读，但目标缺少“验收方式” | 成果/目标提示没有要求“指标-验证动作-证据文件”三联 |
| 12 | 章节页 | 可用 | 结构页 |
| 13 | 设备接入 | 纵向四卡片，不像实操页 | 提示词要求“四行卡片式布局”，没有要求操作屏幕/输入输出/验收信号 |
| 14 | 数据采集 | 有 98.6%，但它是示例补位，存在造数风险 | manuscript 中保留“如 98.6%”，没有证据时不应生成具体数字 |
| 15 | 智能识别 | 流程有了，但准确率 91.7% 是示例补位 | 同上，示例数字被执行器当作真实指标 |
| 16 | 告警工单 | 有闭环图，但主图太小，四周卡片仍多 | 提示词要求“中心图+四周卡片”，但没有要求状态机占主导 |
| 17 | 主要成果 | `[待补充]` 多，正式不可用 | 证据诊断未前置到生成前；门禁只在导出阶段拦截 |

## 四、为什么它会大量卡片化

### 1. Manuscript 本身在强推卡片

典型字段：

- 第 4 页：`中60%三列卡片`
- 第 10 页：`2x2网格布局，四张等大卡片`
- 第 13 页：`垂直排列四张信息卡片`
- 第 16 页：`中心闭环流程图，四周环绕四个环节的卡片说明`
- 第 17 页：`数据集说明卡片 + 指标表格 + 素养要点`

这些不是执行器自由发挥，而是上游页面策划明确给出的布局。下游再强，也只能在这个框里做。

### 2. 设计规格把“卡片”当成默认组织方式

`design_spec.md` 的通用布局包含：

- three/four column cards
- matrix grid
- card gap
- card padding
- card border radius

但缺少面向职业赛 PPT 的专用图解类型，例如：

- 现场实操板
- 评委视角证据链
- 操作输入输出闭环
- 故障恢复流程
- 双屏/设备/人员协同图
- 代码还原讲解图
- 测试验收仪表盘

于是模型会走最稳的低风险路径：卡片、表格、流程箭头。

### 3. “视觉策划字段”还不够可执行

当前每页有：

- `page_role`
- `judge_focus`
- `visual_strategy`
- `layout_hint`
- `evidence_assets`
- `speaker_goal`

这些字段方向是对的，但它们没有约束到“每页必须有一个主视觉对象”。例如第 10 页说“关键技术点以卡片并列”，没有要求画出边缘补传队列、组合判断规则树、证据绑定关系图。

### 4. 证据缺失被留到最后才拦截

第 17 页仍有 `[待补充]`。第 14 页和第 15 页出现 98.6%、91.7% 这类示例数字。说明当前逻辑里：

- 资料诊断发现证据不足；
- 但 manuscript 仍允许把“待补充/如 xx%”写进去；
- SVG 执行器把它当成可画内容；
- 最后导出门禁再拦。

这会导致用户看到“页面生成了，但不能用”，体验上很挫败。

### 5. 实操页没有真正变成比赛现场页面

真实比赛中的实操讲解不是“功能价值、关键技术、产品效果、模块小结”四卡片，而是：

- 当前谁讲；
- 谁操作；
- 操作对象是什么；
- 屏幕应该出现什么；
- 评委应该看哪个结果；
- 失败时怎么切换备用方案；
- 这个操作证明了哪个评分点。

当前第 13-16 页虽然有 `operator_action`、`expected_screen_state`，但这些内容没有成为视觉主体，而是被隐藏在 manuscript 字段里。最终页面仍像普通功能说明页。

## 五、提示词层面的核心偏差

### 偏差 A：页面策划先选布局，再装内容

现在的流程是：

内容点 -> layout_hint -> 执行器按布局画

但比赛 PPT 更应该是：

评委要理解什么 -> 需要看到什么证据/操作 -> 选择最能解释它的图 -> 再安排文字

也就是说，应该先定“理解模型”，不是先定“三列/四卡片”。

### 偏差 B：没有强制“每页一个主信息图”

目前不是每页都有主图。有些页只有卡片、条目、表格。应该要求每个内容页必须有一个 `primary_visual`：

- architecture_map
- pain_to_solution_map
- live_demo_board
- input_operation_output_evidence_flow
- evidence_chain
- rule_tree
- test_dashboard
- team_handoff_lane

如果没有 `primary_visual`，该页不允许进入 SVG 生成。

### 偏差 C：示例数字没有和真实证据隔离

`[待补充：如 98.6%]` 这种写法非常危险。模型会把 “98.6%” 画得很漂亮，但它不是证据。提示词必须改成：

- 没证据时只显示“待测/待验证”，不能显示示例数。
- 示例数字只能存在于 internal planning，不得进入 manuscript visible content。
- 成果页必须引用 evidence_id，否则进入草稿态。

### 偏差 D：现场实操字段没有进入画面

`stage_mode / operator_action / expected_screen_state / fallback_plan / acceptance_signal` 是好字段，但现在没有强制执行器把它们转成画面元素。应该要求现场页必须包含：

- 操作角色
- 操作步骤
- 输入数据
- 预期画面
- 成功信号
- 证据留存
- 失败切换

这类页不应该用普通卡片页模板。

## 六、应改的提示词方向

### 1. 新增页面类型，而不是继续靠 content/chapter

建议将 roadshow manuscript 的页面类型扩展为：

- `cover`
- `agenda`
- `context_problem`
- `solution_map`
- `architecture`
- `data_flow`
- `technical_mechanism`
- `live_demo_board`
- `code_explain_board`
- `test_evidence`
- `result_dashboard`
- `risk_fallback`
- `team_handoff`
- `conclusion`

每种类型绑定默认主视觉，不允许都走 `content`。

### 2. 新增 `primary_visual` 合同

每页必须输出：

```yaml
primary_visual:
  type: architecture_map | evidence_chain | live_demo_board | rule_tree | test_dashboard
  purpose: 这一页让评委一眼理解什么
  required_elements:
    - 必须出现的节点/流程/数据
  forbidden_layouts:
    - 纯四卡片
    - 纯列表
    - 只有表格
  visual_weight: 60%-75%
```

执行器如果看到 `primary_visual`，就以它为主体布局，文字退为辅助说明。

### 3. 对卡片页加硬限制

建议写入策略提示：

- 全套 PPT 中，纯卡片页不得超过 20%。
- 单页卡片数量超过 4 时必须改为流程图、泳道图、矩阵图或证据链。
- 技术页不得使用“标题+四卡片”作为最终布局，除非每张卡片内部有机制小图。
- 实操页禁止使用“功能价值/关键技术/产品效果/模块小结”四卡片作为主结构。

### 4. 把实操页改成现场导览板

实操页应该固定输出：

```yaml
live_demo_board:
  demo_goal: 本次操作证明什么
  operator: 操作角色
  input: 输入/设备/数据包
  action_steps:
    - step 1
    - step 2
  expected_screen: 预期系统画面
  success_signal: 评委能看到的成功信号
  evidence_capture: 截图/日志/API/报告
  fallback: 失败时备用展示
```

页面视觉应是“左侧操作步骤 + 中间系统画面占位 + 右侧证据/成功信号”，不是四条说明。

### 5. 成果页必须证据化

成果页不要直接写 KPI 表。应该先要求 evidence table：

```yaml
evidence_metrics:
  - metric: 平均采集延迟
    value: null
    status: missing | verified
    source: null
    verification_method: 对比设备上报与系统接收时间戳
    evidence_id: null
```

无 `value/source/evidence_id` 时，页面只能显示“验证方法与待采集项”，不能画成正式成果。

## 七、代码层面建议

### 1. 在 roadshow_agent 的视觉策划阶段加入结构化校验

当前只校验字段是否存在，不校验字段质量。应增加：

- `primary_visual.type` 必填。
- `layout_hint` 中出现 “卡片/网格/三列/四列” 过多时降级重写。
- `evidence_assets` 为待补充时，不允许 `visual_strategy` 使用成果展示语气。
- 实操页必须包含现场执行七要素。

### 2. 在 strategist_agent 中限制通用卡片模板

现有 roadshow guardrails 已经说“prefer live-operation layouts”，但力度不够。需要改成强约束：

- live demo 页面 MUST use live-operation board。
- technical mechanism 页面 MUST use mechanism diagram。
- evidence/result 页面 MUST use evidence dashboard。
- 如果 manuscript 没有 primary_visual，strategist 必须补齐，不得直接生成 design_spec。

### 3. 在 SVG executor 前加入 page plan lint

在进入单页 SVG 生成前，对 page section 做 lint：

- 没有主视觉：退回 strategist/visual_plan。
- 纯卡片页过多：退回重写。
- 有 `[待补充：如 xx%]`：删除示例数，只保留待验证。
- 实操页没有 expected_screen/success_signal：退回补齐。

### 4. 清理编辑器污染

当前 `svg_final` 的 01、02 页有 `data-paper-editor` 残留。需要在保存逻辑中区分：

- 原始 SVG 内容；
- 用户新增编辑层；
- 预览渲染临时 SVG；

避免把“新建文本/新建表格”的默认内容写入最终页。

## 八、下一步推荐

优先不要继续调样式，而是改提示词合同：

1. 修改 roadshow manuscript 生成，让每页输出 `page_type + primary_visual + evidence_contract + live_demo_contract`。
2. 修改 visual plan review，发现纯卡片页立即重写。
3. 修改 strategist，按页面类型生成专用 Section IX，不再把所有页都归到 content/card/layout。
4. 修改 executor prompt，要求每页先声明“主视觉占比”和“评委理解目标”，再生成 SVG。
5. 用 `e9870a848772` 同一份材料重新跑 17 页对比，重点看第 10、13、14、15、16、17 页。

一句话：这版失败不是因为“不够漂亮”，而是页面策划没有把比赛现场的“讲解、操作、证据、验收”变成画面主体。只要上游提示词继续输出“三列卡片/四张信息卡片”，下游 SVG 再怎么优化，也很难生成真正有理解力的比赛 PPT。
