# 职业院校技能大赛现场视频分析与 PPT Agent 偏差报告

> 视频来源：`/Users/liuyixing/Movies/Videos/Media.localized/Home Videos/e9df998256bca0a6cbba604c1390330e.mp4`
>
> 目的：通过完整现场录制视频反向理解比赛过程，对照当前 `roadshow` PPT 生成逻辑和提示词，找出偏离真实比赛表达的地方，并提出下一轮改造方向。

## 1. 分析范围与方法

### 1.1 视频基础信息

| 项目 | 结果 |
| --- | --- |
| 时长 | 00:54:30.792 |
| 画面 | 720 x 406，约 24 fps |
| 音频 | AAC，48 kHz，单声道 |
| 抽帧方式 | 每 30 秒抽取 1 帧，共 109 帧 |
| 联系表 | `docs/video_analysis_assets/e9df998256bca0a6cbba604c1390330e/contact_sheets/` |
| 音频分析 | 提取 16 kHz mono wav，并做静音/活跃音频粗分析 |

### 1.2 重要限制与转译文本补充

本机可用 `whisper` / `faster_whisper`，但模型下载过程出现校验失败和 HuggingFace 下载卡住，因此自动转写没有形成可靠逐字稿。第一版报告只基于画面与音频结构做分析。

用户随后提供了人工/外部转译文本，本版报告已把转译内容纳入分析。由于转译文本仍可能存在识别误差，例如“游离菌/智能大棚”“AI 问答/AI 文档”“打包/打分”等词可能混淆，本报告不把个别词当作最终事实，而是提取稳定的比赛流程、角色协作、实操结构、成果口径和提示词改造需求。

### 1.3 可复查材料

- 抽帧目录：`ai-scoring/docs/video_analysis_assets/e9df998256bca0a6cbba604c1390330e/frames/`
- 联系表目录：`ai-scoring/docs/video_analysis_assets/e9df998256bca0a6cbba604c1390330e/contact_sheets/`
- 音频目录：`ai-scoring/docs/video_analysis_assets/e9df998256bca0a6cbba604c1390330e/audio/`
- 静音分析：`ai-scoring/docs/video_analysis_assets/e9df998256bca0a6cbba604c1390330e/audio/silence_summary.json`

## 2. 从视频看到的真实比赛现场

### 2.1 这不是普通 PPT 路演，而是“PPT + 多屏 + 设备 + 队员协同”的现场演示

画面中反复出现四类载体：

| 载体 | 现场作用 | 对 PPT 生成的启示 |
| --- | --- | --- |
| 中央大屏 | 展示 PPT、系统页面、数据看板、流程页 | PPT 需要成为现场主线，不只是漂亮页面 |
| 左侧移动显示屏 | 多次展示代码、后台页面、桌面或移动端竖屏界面 | 需要支持“副屏/代码屏/移动端镜像”脚本 |
| 右侧队员工位 | 多名队员坐在桌前操作电脑，配合前方讲解 | 每个实操页要知道谁讲、谁操作、谁记录 |
| 左侧项目展板/设备区 | 显示主题背景或实物/场景载体 | 需要把设备和场景作为演示证据，而不是只写文字 |

当前系统虽然在提示词里写了“选手自带 PPT 和设备到现场讲解并实操”，但还没有把这种现场形态建模成结构化数据。它更像在生成一份“比赛主题的 PPT”，而不是生成一份“现场比赛执行脚本 + PPT”。

### 2.2 队员不是轮流念稿，而是分段交接

视频开头有团队整体亮相，随后不同队员轮流站到前方讲解。其他队员坐在右侧电脑前，持续操作或准备。中间能看到多次站位变化、人员交接、前方讲解者与坐席操作者配合。

这说明团队合作不是单独做 2 页“角色分工”就够了。真实比赛里的团队合作体现在：

- 讲解角色与操作角色的时间段切换。
- 前方讲解和后方操作同步。
- 一名队员讲系统逻辑，另一名队员准备或执行操作。
- 设备/软件切换时有自然停顿。
- 结束前回到总结和成果页面。

当前 `roadshow_agent.py` 已要求“匿名角色分工、讲解与操作交接、异常协作”，这是正确方向，但还停留在文案要求。它没有要求每页或每个演示段输出 `handoff_cue`、`operator_action`、`display_target`、`expected_screen_state` 这类现场控制字段。

### 2.3 PPT 页面承担“导航牌”和“证据目录”的作用

视频中的中央大屏页面多为深色科技风，常见形式包括：

- 顶部标题 + 左侧导航栏 + 中央内容区。
- 多模块卡片或仪表盘。
- 系统功能分区。
- 流程/步骤/1-2-3 式展示。
- 软件系统界面或后台管理页面。
- 移动端竖屏界面。
- 代码或控制台展示。

这些页面不像传统演讲 PPT 那样一页讲一个观点，也不像论文 PPT 那样“问题、方法、实验、结果”。它更像“演示控制台”：评委看中央大屏知道当前讲到哪一步，坐席队员按页面提示切系统或操作设备。

当前 `strategist.md` 和 `executor.md` 仍默认把页面分成 Header / Content / Footer 三段，并追求普通演示页的规范性。这对论文 PPT 很稳定，但对比赛现场会显得“像报告”，缺少现场操作界面感。

### 2.4 现场节奏接近 55 分钟，且包含大量操作停顿

视频总时长 54 分 30 秒，和我们之前设定的 55 分钟高度一致。音频粗分析显示，在 -25 dB 阈值下，活跃音频约 2514 秒，占 76.9%；静音/低声/环境段约 756 秒，占 23.1%。这类停顿并不一定是空白，而可能是：

- 切屏。
- 点击系统。
- 等待页面加载。
- 队员交接。
- 评委观察实操。
- 操作者完成某一步输入。

所以 PPT 生成不能把 55 分钟平均分给 38 页讲稿。很多页应该是“讲 20 秒，操作 60 秒”；也有些页只是演示段的入口页。当前提示词虽然要求“55分钟 run-of-show”，但没有要求每页给出时间预算，也没有区分“讲解页”和“操作承载页”。

### 2.5 视觉上不是“极简高级”，而是“高密度、可读、系统感强”

从抽帧看，现场 PPT 大多是深色背景、绿色/青色科技风、面板化模块、系统 UI 截图、流程卡片、导航菜单。它的重点不是留白和文艺感，而是：

- 后排可读。
- 评委能快速定位当前模块。
- 和真实系统界面风格统一。
- 页面能承接现场操作。
- 数据、代码、后台、移动端有可见证据。

这解释了为什么我们之前只做“好看的页面模板”会走偏：比赛 PPT 的美观不是网页式视觉，而是“现场工程展示的清晰度、可信度和可控感”。

### 2.6 转译文本揭示的更关键现场规律

转译文本补充了画面无法完全确认的内容：这场比赛不是简单按 PPT 顺序讲，而是有非常明确的“主持/指令/执行/汇报”机制。

#### 2.6.1 开场先做安全与环境检查

开场不是直接进入项目介绍，而是先由项目经理发出口令，要求队员进行软硬件、安全、应急、环境测试。队员分别汇报：

- 用户端运行正常。
- 系统后台运行正常。
- 设备端通信交互正常或稳定。
- 安全无误后就位。

这说明比赛 PPT 需要在开场附近体现“现场准备与安全确认”，而不是只放封面、目录和项目背景。这个环节本质上支撑评分里的职业素养、安全意识、操作规范性和团队协作。

#### 2.6.2 正式讲解采用“五大板块”而不是普通商业路演结构

转译文本中的主线是：

1. 项目介绍。
2. 总体思路。
3. 技能要点或核心要点。
4. 主要成果。
5. 项目创新。

这比我们当前设计中的“背景、方案、实操、证据、团队、创新、总结”更贴近真实赛场。我们的结构并非错误，但需要让“五大板块”成为默认一级叙事骨架，再在其中嵌入实操、证据、团队和安全。

#### 2.6.3 每个核心功能都按“讲解 -> 代码还原 -> 产品测试”展开

文本中三个核心功能模块都呈现出相似模式：

| 模块 | 技术讲解 | 代码/实现还原 | 产品效果测试 |
| --- | --- | --- | --- |
| 环境监测与预警 | 传感器、蓝牙解析、阈值预警 | 解析函数、标识符、阈值字段、日志输出 | 蓝牙连接、环境监测、阈值设置、自动/手动预警 |
| 智能排风 | 天气 API、作物需求、排风计划 | 低代码表、字段配置、计划生成 | 选择大棚、生成计划、历史记录、手动排风 |
| AI 智能问答 | 本地大模型、SSE、消息保存 | 发送消息函数、POST 保存、SSE 接收 | 输入农业问题、AI 回复、农业科普入口 |

这条规律非常重要。当前 roadshow prompt 只要求“实操页必须包含输入、操作、输出、证据、异常预案”，但没有强制每个核心模块都覆盖：

- 需求价值。
- 技术实现。
- 代码解释。
- 现场操作。
- 测试结果。
- 模块小结。

如果缺这条结构，生成的 PPT 容易变成“系统功能介绍”，而不是“技能大赛作品展示”。

#### 2.6.4 现场故障不是失败，而是评分机会

AI 问答环节出现了现场问题：参数混合、AI 应答未达到预期。团队没有跳过，而是现场说明问题、检查并修改代码，然后再次演示，最终得到有效回答。

这说明我们的 PPT 生成逻辑必须支持“故障恢复脚本”。它不应该只追求完美流程，还应准备：

- 关键功能的常见故障。
- 现场排查口径。
- 快速修复动作。
- 修复后复测路径。
- 如果无法修复，如何切换到预置证据。

这类内容直接体现技能熟练度、问题处理能力、职业素养和团队协作。当前 `fallback_plan` 只被建议为备用方案，还没有成为实操段的强制合同。

#### 2.6.5 成果页存在大量数据，但必须做来源门禁

文本中出现多项成果数据和价值口径，例如：

- 病害发生率下降约 30%。
- 人力成本节约约 30%。
- 硬件或方案成本节约约 40%。
- 精准控制可节约水、肥、电等成本 15%-30%。
- 开发周期缩短 60%。
- 开发效率提升 50%。
- 需求响应提速 70%。
- 后期迭代成本降低 40%。
- 与企业合作、调研活动、推广基地等成果。

这些数据非常像真实比赛汇报会用的“成果弹药”，但对 AI 生成系统来说也是高风险区域。只要资料里没有来源，模型就容易顺着这个风格编造百分比。导出门禁必须区分：

- 用户资料明确提供的数据。
- 联网资料可验证的数据。
- 现场口播但未给证明的数据。
- AI 推断或模板化生成的数据。

正式版只能使用前两类，后两类必须标注待补充或阻断导出。

#### 2.6.6 队员身份是岗位身份，不是个人身份

开场中队员介绍使用的是岗位角色：物联网应用开发工程师、AI 算法工程师、项目经理、测试工程师等。虽然口播中出现“几号选手”，但真正被强调的是岗位职责。

这对我们很关键：比赛要求不能出现姓名、学校、电话、邮箱等个人信息，但并不等于不能展示团队。正确做法是展示“匿名岗位角色 + 职责 + 交接关系”，而不是完全隐藏团队。

## 3. 真实比赛流程推断

基于 109 帧抽样和用户提供的转译文本，可将现场过程抽象为以下 run-of-show：

| 阶段 | 大致时间 | 画面特征 | 真实目的 |
| --- | --- | --- | --- |
| 团队亮相与安全确认 | 0-3 min | 全队站立，中央屏封面，左屏显示代码/后台 | 建立项目识别；完成软硬件、安全、应急、环境测试汇报 |
| 项目介绍与政策/行业背景 | 3-10 min | 深色系统风 PPT，多模块说明 | 说明农业/智慧农业背景、调研发现、行业痛点 |
| 总体思路与三端架构 | 10-16 min | 架构页、技术选型、岗位分工 | 解释用户端、设备端、后台端和数据交互路径 |
| 核心功能 1：环境监测 | 16-27 min | 代码屏、传感器说明、APP 实操 | 讲解蓝牙解析、阈值预警、设备连接和用户端测试 |
| 核心功能 2：智能排风 | 27-36 min | 代码/低代码配置、APP 实操 | 讲解天气 API、排风计划、历史记录和手动排风 |
| 核心功能 3：AI 问答 | 36-45 min | 代码、AI 聊天界面、故障修复 | 讲解 SSE/本地模型/消息保存，并现场处理异常后复测 |
| 后台管理端展示 | 45-49 min | 后台管理列表、增删改查、日志 | 证明系统管理能力、前后端同步和调试能力 |
| 职业素养、成果与价值 | 49-53 min | 规范、安全、成果数据、应用价值 | 说明代码规范、安全协议、团队协作、推广成效和经济价值 |
| 创新与总结 | 53-54.5 min | 创新页、未来规划、结束语 | 收束 AI 赋能、数字乡村、产教融合和可持续发展 |

这个流程对我们的核心启示是：比赛 PPT 应该先有现场流程，再有页面。也就是说，页面不是先按章节生成，而是先生成“现场执行分镜”，再把分镜映射成 PPT 页。

## 4. 当前 roadshow PPT 逻辑中已经做对的部分

当前 `ai-scoring/app/services/ppt/agent/backend/orchestrator/roadshow_agent.py` 已经具备以下正确方向：

1. 明确不是论文汇报，而是职业院校技能大赛作品汇报。
2. 已引入官方评分要素：技能水平 60、职业素养 10、应用价值 10、团队合作 10、创新创意 10。
3. 已要求按约 55 分钟准备，预留 5 分钟。
4. 已要求识别演示环境、设备清单、操作脚本、证据材料、团队分工、备用方案。
5. 已新增页面视觉策划字段：`page_role`、`judge_focus`、`visual_strategy`、`layout_hint`、`evidence_assets`、`speaker_goal`。
6. 已要求实操页包含输入、操作者匿名角色、讲解者匿名角色、操作步骤、输出、证据、异常预案。
7. 已在 `strategist_agent.py` 中加入 roadshow guardrails，避免把比赛 PPT 做成论文答辩或文献综述。
8. 已加了导出门禁，避免缺证据时正式导出。
9. 已经要求团队分工使用匿名角色，这与转译文本中的岗位化表达方向一致。

这些不是错的，问题在于粒度还不够现场化。

## 5. 当前逻辑与真实现场的偏离

### 5.1 缺少“现场执行模型”

当前链路是：

```text
资料分析 -> 大纲 -> manuscript -> visual plan -> review -> design_spec -> 单页 SVG
```

真实现场更像：

```text
资料分析 -> 现场执行分镜 -> 设备/屏幕/角色脚本 -> 页面稿件 -> 视觉系统 -> 单页 SVG
```

当前 prompt 有“实操”“设备”“团队”，但没有一个正式的数据结构回答：

- 此页显示在中央大屏还是左侧副屏？
- 此页是 PPT 讲解页、系统界面页、代码展示页、移动端镜像页，还是设备操作页？
- 讲解者是谁？
- 操作者是谁？
- 操作者此刻应该点击什么？
- 评委此刻应该看什么结果？
- 如果系统打不开，如何回退到 PPT 截图或预录证据？
- 本页是否处于“安全确认、功能讲解、代码还原、产品测试、故障恢复、成果汇报”中的哪一种现场环节？

### 5.2 page_type 太粗，无法表达比赛现场页

当前 manuscript 只允许：

```text
cover | chapter | content | ending
```

这对 paper-ppt-agent 很稳定，但比赛路演需要更细的内部角色。即使对外仍保留这四类 page_type，内部也应该有 `stage_mode` 或 `scene_type`：

| 建议字段 | 示例 |
| --- | --- |
| `stage_mode` | `ppt_explain`、`live_system`、`code_walkthrough`、`mobile_mirror`、`device_demo`、`evidence_review`、`handoff` |
| `display_target` | `main_screen`、`side_screen`、`both_screens`、`physical_device` |
| `demo_phase` | `设备接入`、`数据采集`、`异常识别`、`告警处置`、`记录留痕` |

没有这些字段，后续 strategist 只能把所有页都当普通 PPT 内容页设计。

### 5.3 55 分钟只是被写进 prompt，没有成为可校验合同

当前大纲 prompt 要求 55 分钟 run-of-show，但 manuscript 没有硬性字段：

- `time_budget_sec`
- `speech_time_sec`
- `operation_time_sec`
- `handoff_time_sec`
- `buffer_sec`

所以模型容易生成“看起来覆盖了 55 分钟”的内容，却无法判断现场是否可执行。视频说明真实比赛存在大量 3-10 秒的操作停顿和切换停顿，这些必须进入页面脚本。

转译文本进一步说明，55 分钟不是均匀讲稿，而是多个模块的现场任务链：

```text
安全确认 -> 背景介绍 -> 总体思路 -> 模块1讲解/代码/测试 -> 模块2讲解/代码/测试
-> 模块3讲解/代码/测试/故障修复 -> 后台管理 -> 规范安全 -> 成果价值 -> 创新总结
```

因此每个模块都应该有单独的时间预算和通过条件，而不是只给整套 PPT 一个总时长。

### 5.4 证据链仍偏“图片 token”，没有覆盖现场证据类型

当前 `roadshow_quality.py` 和图像过滤主要解决 `[[FIG:...]]` 乱用问题，这是必要的。但真实比赛中的证据不只有 PDF 图：

- 现场系统界面。
- 代码编辑器/核心代码片段。
- 后台管理页面。
- 移动端界面。
- 操作日志。
- 设备状态。
- 表格记录。
- 现场输出结果。

建议新增证据 token 类型：

```text
[[SCREEN:backend_dashboard]]
[[CODE:core_algorithm]]
[[MOBILE:app_operation]]
[[DEVICE:edge_gateway]]
[[LOG:alarm_trace]]
[[DATA:test_result_table]]
[[ACTION:connect_device]]
[[ROLE:operator_a]]
```

这些 token 不一定都对应图片文件，有些对应现场脚本和可验证事实。

转译文本还证明应该增加两类证据：

```text
[[FIX:ai_qa_parameter_repair]]  # 现场故障排查与修复过程
[[STANDARD:code_quality_security]]  # 开发规约、安全协议、质量检查、项目管理规范
```

前者用于证明技能熟练度和异常处置能力，后者用于支撑职业素养。

### 5.5 视觉生成还像“演示文稿”，不够像“现场系统展示”

`executor.md` 目前强制 Header / Content / Footer 三段结构，这对规范性有帮助，但视频里的比赛 PPT 更像一个统一系统界面：

- 左侧导航。
- 顶部模块标题。
- 中央大卡片/大屏区域。
- 右侧状态/证据/指标。
- 暗色背景。
- 青绿高亮。
- 卡片密度较高。

如果继续使用普通 PPT 三段式，生成结果会显得“写得对，但不像现场比赛”。下一轮 strategist 需要增加比赛专用视觉模式：`competition_cockpit`、`live_demo_board`、`evidence_console`、`team_handoff_board`。

### 5.6 视觉策划字段还不够“可执行”

当前字段：

```text
page_role
judge_focus
visual_strategy
layout_hint
evidence_assets
speaker_goal
```

这些能指导页面长什么样，但不能指导现场怎么演。建议扩展为：

```text
page_role:
stage_mode:
display_target:
time_budget_sec:
speaker_role:
operator_role:
operator_action:
expected_screen_state:
evidence_assets:
fallback_plan:
speaker_goal:
judge_focus:
visible_text_policy:
```

其中 `judge_focus` 应是隐藏策略字段，不应直接出现在可见页面文案中。

基于转译文本，还应增加：

```text
module_flow: 功能讲解 | 代码还原 | 产品测试 | 故障修复 | 模块小结
acceptance_signal: 本页/本段演示成功的可见判据
command_cue: 讲解者发给操作者的口令，例如“请某角色进行设备连接测试”
```

### 5.7 团队合作不应只生成“团队分工页”

视频里的团队合作是贯穿式的：有人讲、有人操作、有人准备下一步、有人接棒。当前 prompt 会生成团队分工内容，但还需要把角色嵌入每个实操段。

建议在 run-of-show 层输出：

```json
{
  "segment": "异常识别实操",
  "speaker_role": "讲解角色A",
  "operator_role": "操作角色B",
  "support_role": "记录角色C",
  "handoff_cue": "讲解角色A说明输入条件后，操作角色B在后台触发识别流程",
  "backup_role": "应急角色D负责切换离线截图"
}
```

转译文本里的团队合作具有“口令式协作”特征，例如项目经理要求队员检查环境、某功能讲解完毕后询问另一角色是否完成准备、测试工程师接棒展示产品效果。PPT agent 应该生成这种 `command_cue`，否则团队页即使写得漂亮，现场仍然缺少真实协作感。

### 5.8 前端资料收集不够反向推理

如果用户只上传一份说明书，系统很难知道真实现场怎么演。视频说明至少需要追问这些信息：

1. 现场会带哪些设备？
2. 是否需要网络？如果断网怎么演？
3. 现场有几个屏幕？哪个屏幕放 PPT，哪个屏幕放系统？
4. 有无后台系统、移动端、代码、硬件设备、数据文件？
5. 一次完整实操从输入到输出有哪些步骤？
6. 每一步由哪个匿名角色操作？
7. 每一步成功的可见结果是什么？
8. 有哪些截图、日志、视频、测试表可以作为证据？
9. 哪些步骤必须现场实时做，哪些步骤可以用预录/截图兜底？
10. 结尾希望评委记住的 3 个成果是什么？
11. 每个核心模块是否都需要展示代码？展示哪一段代码？
12. 每个模块的产品测试步骤是什么？成功判据是什么？
13. 是否允许现场修改代码或参数？如果出现异常，谁处理、怎么说明？
14. 成果数据的来源是什么？是基地反馈、测试记录、调研问卷、企业证明还是估算？

当前缺资料诊断 Agent 的设计方向是对的，但还没有充分进入前端和正式链路。

### 5.9 当前 prompt 缺少“模块三段式技能展示”

转译文本中最稳定的比赛表达不是“一个功能一页”，而是每个核心功能都要拆成：

```text
为什么需要这个功能 -> 技术怎么实现 -> 代码怎么写 -> 产品怎么测 -> 结果怎么证明
```

当前 prompt 会要求“实操流程”和“证据”，但没有强制“代码还原”。这会导致生成结果看起来像产品介绍，而不是技能大赛。尤其在物联网、软件开发、AI 应用类项目里，代码讲解是技能水平的重要证明。

### 5.10 当前 prompt 对现场故障处理重视不足

真实转译文本中，AI 问答模块出现异常后，团队现场解释原因、修改代码、再次提问并成功得到回答。这是比赛里很有价值的“临场处置能力”。

当前 prompt 只有“异常预案/fallback”，容易让模型生成一句泛泛的“若失败则切换备用方案”。应该要求：

- 常见故障类型。
- 排查步骤。
- 现场解释话术。
- 快速修复动作。
- 复测成功判据。

### 5.11 成果数据必须从“展示指标”升级为“证据约束”

转译文本中的成果数据密度很高，但多数数据如果没有用户提供的证明材料，就不能由模型生成。当前门禁已检查数据来源，但还应细化为：

| 数据类型 | 允许用于草稿 | 允许正式导出 |
| --- | --- | --- |
| 用户资料明确给出且有出处 | 允许 | 允许 |
| 用户口播/文字描述给出但无证明 | 允许，但标注待补充 | 阻断或降级表述 |
| 联网可验证行业数据 | 允许 | 允许，需标注来源 |
| 模型推断的提升比例 | 不建议 | 阻断 |

这会直接影响成果页、应用价值页和创新页的可信度。

## 6. 推荐改造方案

### 6.1 新增 FieldRunOfShowAgent

在 `roadshow_agent` 的 Pass 2 与 Pass 3 之间新增一个现场执行分镜 Agent。

输入：

- material_analysis
- locked_facts
- figure/evidence inventory
- user instruction
- target duration 55 min

输出：

```json
{
  "total_duration_min": 55,
  "site_setup": {
    "main_screen": "PPT / system dashboard",
    "side_screen": "code / mobile mirror / operator desktop",
    "device_area": "physical equipment or simulated environment",
    "operator_table": "team laptops"
  },
  "segments": [
    {
      "name": "开场与项目识别",
      "duration_min": 2,
      "pages": [1, 2],
      "stage_mode": "ppt_explain",
      "speaker_role": "讲解角色A",
      "operator_role": "待命",
      "expected_screen_state": "封面与目录",
      "fallback_plan": "无"
    }
  ]
}
```

这个 Agent 的核心不是写内容，而是回答“55 分钟现场怎么跑”。

根据转译文本，`FieldRunOfShowAgent` 还必须输出五大板块和模块三段式：

```json
{
  "competition_blocks": [
    "项目介绍",
    "总体思路",
    "技能要点",
    "主要成果",
    "项目创新"
  ],
  "module_demo_pattern": [
    "功能价值说明",
    "关键技术/代码还原",
    "产品效果测试",
    "模块小结"
  ]
}
```

### 6.2 改造 Manuscript schema

每页保留原始 `page_type`，但增加现场字段：

```markdown
<!-- page_type: content -->
stage_mode: live_system
display_target: main_screen + side_screen
time_budget_sec: 120
speaker_role: 讲解角色A
operator_role: 操作角色B
operator_action: 在后台选择设备并触发异常识别
expected_screen_state: 中央屏显示识别结果，副屏显示操作日志
evidence_assets: [[SCREEN:recognition_result]], [[LOG:operation_trace]]
fallback_plan: 若现场接口失败，切换到预置截图并说明来源
speaker_goal: 证明系统可从输入数据生成可追溯结果
judge_focus: 技能水平-操作规范性；现场讲解效果
module_flow: 代码还原
acceptance_signal: 控制台输出蓝牙解析数据，前端显示温湿度/烟雾/PM2.5
command_cue: 讲解角色A说明代码逻辑后，测试角色D接棒展示用户端效果
```

注意：这些字段主要给生成器和讲稿使用，不应全部出现在页面可见文案里。

### 6.3 扩展证据链 token

新增 `evidence_chain` 类型：

| token | 含义 | 是否必须有真实素材 |
| --- | --- | --- |
| `[[SCREEN:id]]` | 系统界面截图或现场可显示页面 | 正式导出必须绑定素材或标记现场实时 |
| `[[CODE:id]]` | 核心代码/配置片段 | 可由说明书或代码截图提供 |
| `[[MOBILE:id]]` | 移动端界面 | 可由截图或现场镜像提供 |
| `[[DEVICE:id]]` | 设备/硬件/场景 | 可由照片、清单或现场说明提供 |
| `[[LOG:id]]` | 日志/工单/追溯记录 | 正式成果页必须尽量绑定 |
| `[[DATA:id]]` | 测试数据/指标 | 必须有来源和验证方法 |
| `[[ACTION:id]]` | 现场操作动作 | 可无图片，但必须可执行 |
| `[[ROLE:id]]` | 匿名角色 | 禁止真实姓名/学校 |
| `[[FIX:id]]` | 现场故障排查与修复 | 需要说明故障、修改点、复测结果 |
| `[[STANDARD:id]]` | 代码规范、安全协议、项目管理规范 | 需要来自说明书或用户填写 |

### 6.4 新增 Competition Visual System

给 strategist 增加 roadshow 专用视觉系统，不再只依赖通用 PPT 设计：

```text
competition_cockpit:
  - dark / high contrast
  - left navigation
  - main operation canvas
  - right evidence/status rail
  - bottom risk/fallback strip

live_demo_board:
  - current step
  - operator action
  - expected output
  - evidence marker

evidence_console:
  - KPI cards
  - source labels
  - log/data/source mini cards

team_handoff_board:
  - speaker/operator/support roles
  - handoff arrows
  - contingency note
```

### 6.5 修改 executor 规则

当前 executor 的三段式结构可以保留为默认，但 roadshow 应允许以下布局：

- 左侧导航 + 中央大屏 + 右侧证据链。
- 双屏布局：左侧代码/移动端，右侧系统/PPT。
- 实操流程页：输入 / 操作 / 输出 / 证据 / 异常预案。
- 现场状态页：当前步骤、操作者、倒计时、预期结果。
- 总结页：1-2-3 结论卡 + 成果证据 + 推广价值。

同时增加现场可读性规则：

- 中央大屏页面关键字字号必须更大。
- 不使用过小脚注堆满屏幕。
- 代码页只展示核心片段，不整屏小字。
- 移动端界面用竖屏框模拟或真实截图，不拉伸。
- 现场操作页必须让评委一眼看懂“现在正在做哪一步”。

### 6.6 强化正式版导出门禁

正式导出时新增检查：

| 检查项 | 阻断条件 |
| --- | --- |
| 55 分钟执行计划 | 缺失或总时长不在 50-58 分钟 |
| 实操闭环 | 没有输入/操作/输出/证据 |
| 多屏/设备计划 | 声称现场实操但无设备/软件/显示计划 |
| 角色协作 | 无匿名 speaker/operator/support 分工 |
| 证据来源 | 数据、日志、截图、结果无来源 |
| 备用方案 | 关键实操无 fallback |
| 代码还原 | 核心技术模块完全没有代码/实现解释 |
| 故障恢复 | 声称现场实操但无异常处理或复测方案 |
| 成果数据 | 百分比、金额、推广数量无来源 |
| 个人信息 | 出现姓名、学校、电话、邮箱等 |
| 可见页面污染 | 出现“评分点、评委、打分逻辑、讲稿 JSON”等内部策略词 |

## 7. 具体提示词改法

### 7.1 资料分析 Agent

现有方向保留，但增加现场信息抽取：

```text
额外抽取：
- site_setup: 主屏、副屏、设备区、操作席、网络/账号/离线条件
- live_demo_candidates: 可现场演示的功能清单
- screen_assets: 后台、移动端、代码、日志、数据、设备图片或截图
- operation_chain: 输入 -> 操作 -> 输出 -> 证据
- role_chain: 讲解角色、操作角色、记录角色、应急角色
- fallback_assets: 预录视频、截图、离线数据、备用流程
- module_demo_assets: 每个核心模块的功能价值、关键代码、产品测试、成功判据
- standards_assets: 代码规范、安全协议、测试管理、项目管理和质量检查材料
- result_claims: 成果数据、推广应用、经济价值、可持续价值及其来源
```

### 7.2 大纲 Agent

从“章节大纲”升级为“现场分镜大纲”：

```text
不要只输出章节和页数。必须输出每个段落的：
- duration_min
- page_range
- stage_mode
- display_target
- speaker_role
- operator_role
- demo_action
- expected_screen_state
- fallback_plan
- module_flow: 功能讲解/代码还原/产品测试/故障修复/模块小结
- acceptance_signal: 该段演示成功时评委应看到什么
```

默认一级结构应优先采用真实赛场的五大板块：

```text
项目介绍 -> 总体思路 -> 技能要点 -> 主要成果 -> 项目创新
```

其中“技能要点”内部再按核心模块循环组织：

```text
模块背景 -> 技术实现 -> 代码还原 -> 产品测试 -> 结果证明
```

### 7.3 Manuscript Agent

将每页从“内容页”改成“现场页面卡”：

```text
每页必须包含：
stage_mode:
display_target:
time_budget_sec:
speaker_role:
operator_role:
operator_action:
expected_screen_state:
evidence_assets:
fallback_plan:
speaker_goal:
visible_content:
speaker_notes:
module_flow:
acceptance_signal:
command_cue:
```

每个核心功能模块至少生成 4 类页面：

```text
1. 模块价值页：说明为什么需要该功能。
2. 技术实现页：说明协议、接口、算法、框架或数据流。
3. 代码还原页：展示关键函数/配置/逻辑，不整屏堆代码。
4. 产品测试页：展示输入、操作、输出、成功判据和异常预案。
```

### 7.4 Review Agent

新增“现场可执行性评审”：

```text
检查：
- 55分钟是否能真实跑完
- 是否存在连续超过8分钟只有讲解没有实操/证据
- 每个实操段是否有操作者、输入、输出、成功判据
- 角色交接是否清楚
- 有无切屏/加载/异常缓冲
- 生成的页面是否适合现场大屏观看
- 每个核心模块是否覆盖“价值/技术/代码/测试/结果”
- 成果数据是否有来源，没有来源是否被降级或阻断
- 是否准备了现场故障处理和复测脚本
```

### 7.5 Strategist Agent

新增 roadshow 视觉规则：

```text
For Competition Roadshow:
- Treat the deck as a live operation console, not a thesis deck.
- Prefer cockpit/dashboard layouts for architecture, live demo, evidence, and results.
- Include side navigation or current-step indicators where helpful.
- For live demo pages, design around current action, expected screen state, and evidence marker.
- Never expose hidden fields such as judge_focus or scoring logic as visible slide text.
- For code restoration pages, show only the decisive code fragment, annotated with 3-5 callouts and an input-output explanation.
- For product test pages, use a live-demo board: operation step, screen state, expected result, evidence marker, fallback strip.
- For result pages, visually separate verified metrics from pending/unverified claims.
```

## 8. 下一步开发建议

### Phase 1：先补现场执行结构

1. 新增 `FieldRunOfShowAgent`。
2. 在 `roadshow_agent.analyze_materials()` 中插入到 Pass 2 后。
3. 输出 `run_of_show.json` 到 debug/workspace。
4. Manuscript 注入 `stage_mode/display_target/time_budget/operator_action`。
5. Review 增加现场可执行性检查。
6. 新增五大板块结构和核心模块三段式/四段式生成规则。
7. Manuscript 增加 `module_flow`、`acceptance_signal`、`command_cue`。

验收标准：

- 8 页快速验证也能看出现场流程。
- 至少 2 页包含真实 live demo 结构。
- 至少 1 页明确双屏或设备操作。
- 每个实操页有操作者、讲解者、输入、输出、证据、fallback。
- 每个核心模块至少能看到“技术实现/代码还原/产品测试”链条。

### Phase 2：重做 roadshow 视觉系统

1. Strategist 增加 `competition_cockpit` 等布局类型。
2. Executor 支持 dashboard / dual-screen / live-demo-board。
3. 禁止 roadshow 默认套普通 Header/Content/Footer。

验收标准：

- 架构页像系统分层控制台。
- 实操页像现场操作板。
- 成果页像证据看板。
- 团队页体现交接，不是普通组织架构。

### Phase 3：前端资料收集与导出门禁

1. `/ppt-editor` 路演模式新增现场资料表单。
2. 用户资料不足时先进入“缺资料诊断”，允许草稿但标记缺口。
3. 正式导出必须通过 run-of-show、实操闭环、证据链、个人信息四类门禁。
4. 新增核心模块资料表：模块名称、价值、关键代码、测试步骤、成功判据、异常处理、成果证据。
5. 成果数据必须填写来源类型：测试记录、用户反馈、基地证明、企业合作、联网来源或待补充。

验收标准：

- 没有设备/实操/证据时，正式导出被阻断。
- 草稿页明显标记“待补充”，不编造数据。
- 用户能看到系统缺什么资料，而不是只看到生成失败。
- 没有来源的百分比成果不能进入正式版。

## 9. 结论

目前我们的 roadshow agent 已经从“论文 PPT”转向“比赛 PPT”，但还没有完全转向“比赛现场”。视频说明，职业院校技能大赛作品汇报的核心不是单纯生成 35-45 页 PPT，而是生成一套 55 分钟可执行的现场演示系统：

- PPT 是主线。
- 系统界面是证据。
- 设备和代码是可信度。
- 队员交接是团队合作。
- 停顿和切屏是流程的一部分。
- 备用方案是职业素养的一部分。

下一轮最重要的改造不是继续美化模板，而是把 `run_of_show`、`stage_mode`、`display_target`、`operator_action`、`expected_screen_state`、`fallback_plan` 这些现场字段纳入正式链路。只有这样，生成结果才会从“像比赛 PPT”进化到“能支撑比赛现场”。

转译文本进一步把这个结论推得更明确：系统不仅要生成“现场字段”，还要生成“比赛口令”和“技能展示链条”。真实比赛的核心表达是：

```text
岗位角色开场 -> 安全环境确认 -> 五大板块主线 -> 每个核心模块按价值/代码/测试展示
-> 现场故障可处理 -> 后台管理可验证 -> 规范安全可说明 -> 成果数据有来源 -> 创新价值收束
```

因此下一轮开发优先级应调整为：

1. 先做 `FieldRunOfShowAgent` 和模块展示链条。
2. 再做 roadshow 专用视觉系统。
3. 最后扩展页面美化、视觉参考和图标装饰。
