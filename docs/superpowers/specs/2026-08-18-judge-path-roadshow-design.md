# 路演评委路径（完整规格）

> 日期：2026-08-18  
> 状态：待你确认后写实施计划  
> 配套界面稿：`docs/superpowers/mocks/judge-path-hifi/index.html`  
> 讲稿对页：`2026-08-18-script-page-binding-design.md`（逐字稿里的翻页、动作、现场怎么对 PPT）  
> 已有 PPT 全链：`2026-08-18-existing-ppt-full-chain-design.md`  
> 上游已落地：讲稿 `script.content` 真源、`apply_script_patch`、智能文档改稿、P1 评分对照清单  
> 本文替换的主路径：`/ppt-editor` 问卷 → 38 页内容卡 → 逐页 SVG / image2  
> 本文不废：论文 PPT 长链、旧任务历史、启发 Office 原文件精调、P0/P1 改稿

---

## 0. 一句话

**产品不是「智能 PPT 生成器」。产品是评委路径编译器：把这一次评分、这一份讲稿、这一堆证据，编译成评委必须依次相信的命题；页型只负责把过闸命题印刷成台上翻的 12–16 页。**

没有命题，不许出页。没有证据，不许把缺口写成事实。模板不是方案，是印刷机。

---

## 1. 要解决的四件事，分别靠什么

| 用户原话 | 不靠什么 | 靠什么 |
|---|---|---|
| 要填大量资料 | 分区问卷、资料齐全才生成 | 项目里已有的讲稿、评分、任务书、资源中心；没有讲稿才写 8 句骨架 |
| 生成特别慢 | 九 Agent + 35–45 页逐页画 SVG | 编译命题（秒级）+ 套页型填槽（30–60 秒） |
| 内容死板、上台不行、逻辑不连贯 | 模型把评分表写成 38 页散文 | 命题链 + 四条硬闸 + 模拟后再改命题 |
| 样式差、改单页仍不连贯 | 每页让模型重排 | 8 页型 × 密度变体 × 整份一皮；旧 PPT 分 L1/L2 |

含金量在编译器和闸，不在页型。页型保证的是「印出来不散、不叠字」。

---

## 2. 产品边界

### 2.1 主交付

台上翻页用的薄 PPT：默认 12–16 页，对应约 15–20 分钟讲解 + 现场实操。不是给评委会后翻阅的 38 页材料包。

厚材料若以后要，做成「附录包」，不进入台上时间轴。本期不做附录生成。

### 2.2 两条进门，一个真源

| 门 | 用户现状 | 进门后 |
|---|---|---|
| 没有能上台的 PPT | 无 PPT，或旧稿作废 | 编译评委路径 → 确认命题 → 印刷 |
| 已有一份，改不动 | 启发 Office / 本机 pptx | 同一条评委路径去对照旧页 → L1 改字或 L2 换页型 |

两条门的真源都是 `judge_path`，不是两套生成器。

### 2.3 和已有规格的关系

| 已有 | 关系 |
|---|---|
| `2026-08-18-xiaoqi-script-ppt-agent-design.md` | 讲稿补丁、锁角色、不确认不落盘，全部保留 |
| 智能文档 sdoc 工作台 | 继续当讲稿编辑现场 |
| P1 `script_score_revise` | 评分条目仍只读；本方案在对照结果上编译命题，不只改两句形容词 |
| 计划 Task 7 P2 PPT 跟随 | 并入本方案 D 期：跟随的是命题对应页，不是 refine 整页乱画 |
| 计划 Task 8 P3 表格视图 | 独立，不挡本方案 |
| 现有 `/api/ppt/generate` 问卷长链 | 路演主入口下线；旧 job 只读历史；论文 PPT 仍走长链 |

### 2.4 明确不做

- 用 Collabora 让 AI 改 PPT
- 用自由 Word / 散文 sdoc 当讲稿真源
- 一次生成全新讲稿 + 全新 PPT 且不经命题
- 无确认覆盖讲稿或 PPT
- 模型自绘自由连线架构图
- 从旧 PPT「抽全套设计系统」并承诺无缝
- v1 做评委翻阅用的 35–45 页厚稿
- 把九 Agent 换皮继续当主路径

---

## 3. 对象模型

三层，不许混。

```
评分条目 / 讲稿步骤 / 证据令牌     ← 只读输入
        ↓ 编译（规则为主，模型只压缩口播）
命题 Proposition / 漏洞 Hole      ← 内容真源 judge_path
        ↓ 印刷（页型 + 密度变体）
台上页 PrintedPage                ← 槽里的字和图，不是自由画布
```

### 3.1 输入钉（CompilePin）

编译时必须写进路径，之后换一句还在：

```json
{
  "scriptId": 12,
  "scriptTitle": "智慧农业损耗治理",
  "contentVersion": 7,
  "scoreReportId": 8841,
  "overallScore": 72,
  "taskBookRef": null,
  "pptJobId": null,
  "inspirePptDocumentId": null,
  "teamId": 3
}
```

没有评分：仍可编译，缺口列表为空，覆盖率显示「未钉评分」，不允许假装覆盖了评分。  
没有讲稿：走 8 句骨架（见 7.6），编出的命题全部标 `source=skeleton`。  
没有证据：命题可存在，但状态只能是 `pending_evidence`，页上禁止出现无来源数字。

### 3.2 证据令牌 EvidenceToken

只从讲稿正文、资源中心文件名/摘录、任务书摘录里抽。禁止模型创造令牌。

```json
{
  "id": "t_23pct",
  "kind": "metric",
  "surface": "23%",
  "unit": "%",
  "noun": "损耗",
  "source": { "type": "script_step", "stepId": "s4" },
  "assetId": "res_1024",
  "assetKind": "photo"
}
```

`kind` 只允许：`metric` | `name` | `contrast` | `photo` | `log` | `quote` | `role`。

抽取规则（确定性，单测锁死）：

1. 数字：`\d+(\.\d+)?\s*%`、`\d+(\.\d+)?\s*(万|千|元|秒|分钟|项|个|步|层|园|棚)`。
2. 对比：同一段落或相邻步骤出现两个同单位数字，且上下文有「前/后/降到/从…到」。
3. 专名：讲稿标题、锁定项目名；不把「物联网」「数字化」当令牌。
4. 角色：步骤上的 `role`，只用于实操页「谁操作谁讲」。
5. 图片：资源中心图片/截图，按文件名与邻近步骤关键词打分，只建议，不自动当事实。
6. 金额、证书、专利、合作方：没有对应资源文件，不得生成 `metric`/`name` 令牌。

### 3.3 命题 Proposition（内容原子）

评委必须信的一件事。一页只印刷一个命题（方案+架构允许 1 命题拆 2 页，见 5.2）。

```json
{
  "id": "p1",
  "status": "bound",
  "judgeMustBelieve": "损耗发生在入库前，而且你们量过",
  "act": "problem",
  "scoreItemIds": ["score-8841-3"],
  "scoreDimension": "应用价值/实用性",
  "scriptStepIds": ["s4"],
  "role": "主讲A",
  "durationSec": 40,
  "tokenIds": ["t_23pct", "t_3sites", "t_photo_weigh"],
  "spoken": "评委老师，我们在三个试点大棚量过，从采到入库平均损耗 23%。",
  "onSlide": {
    "title": "损耗发生在入库前",
    "number": "23%",
    "line": "三个试点 · 采摘到入库",
    "assetId": "res_1024"
  },
  "pageType": "problem",
  "density": "S",
  "payoffIn": "p5",
  "printPage": 3,
  "riskIfCut": "实用性缺口没有现场锚点"
}
```

`status`：

| 值 | 含义 | 能否印刷 |
|---|---|---|
| `bound` | 讲稿有句、评分有缺口或有必要幕、令牌够印 | 能 |
| `pending_evidence` | 论证需要，但关键令牌没有 | 能印无数字/待补图变体，不能印假数 |
| `spoken_only` | 只配口播，不配页（交接、认账） | 否 |
| `rejected` | 用户删掉 | 否 |

`act` 只允许：`hook` | `problem` | `cause` | `method` | `demo` | `evidence` | `craft` | `team` | `close`。

### 3.4 漏洞 Hole

评分要、证据池没有、讲稿也撑不住。**不是一页 PPT。**

```json
{
  "id": "h1",
  "scoreItemId": "score-8841-7",
  "scoreDimension": "应用价值/经济性",
  "why": "扣了经济账，令牌池没有金额",
  "forbiddenOnSlide": ["12万", "节约", "回本"],
  "advice": "补一张成本表，或本场口头认账，不要做一页假账"
}
```

漏洞的 `forbiddenOnSlide` 在印刷前扫描全部 `onSlide` 字符串，命中则整份禁止出页。

### 3.5 路径 JudgePath（落库）

表 `judge_path`：

| 列 | 类型 | 含义 |
|---|---|---|
| id | bigint pk | |
| team_id | bigint | 团队 |
| created_by | bigint | |
| script_id | bigint null | 可空（仅骨架） |
| score_report_id | bigint null | 可空 |
| script_content_version | int null | 编译时讲稿版本 |
| ppt_job_id | varchar null | 印刷产出或对照的旧 job |
| status | varchar | `compiled` / `confirmed` / `printed` / `replayed` |
| path_json | json | pins, tokens, propositions, holes, gates, printPlan |
| created_at / updated_at | | |

每次重新编译插新行，或在同一行写新版本快照到 `judge_path_revision`（与 `script_revision` 同模式）。确认命题才把 `status` 推到 `confirmed`。

### 3.6 印刷页 PrintedPage

```json
{
  "page": 3,
  "propositionId": "p1",
  "pageType": "problem",
  "density": "S",
  "skin": "arena-dark",
  "slots": { "title": "损耗发生在入库前", "number": "23%", "line": "三个试点 · 采摘到入库" },
  "assetId": "res_1024",
  "origin": "printed"
}
```

`origin`：`printed` | `legacy_l1` | `legacy_l2` | `legacy_untouched`。旧 PPT 对照后混排时用来标「换过」。

---

## 4. 编译器（含金量在这里）

纯函数，Java 单测锁行为。模型只参与 4.5「口播压缩」，且输出必须过令牌闭包，失败则回退到讲稿原句截断。

### 4.1 输入

- `script.content` 章节/步骤（`ScriptScoreRevisePlanner.flattenSteps` 已有）
- 最新 `ai_score_report.improvement_priorities_json`（P1 已读）+ 维度分（若报告里有）
- 资源中心该团队图片/表格清单（id、文件名、ext、可选摘录）
- 可选任务书短摘录（有则只读）
- 可选 8 句骨架

### 4.2 步骤分类（确定性）

对每一步 `content`+`focus` 打 `act`，按关键词表，取最高分；低于阈值标 `logistics`（交接、谢谢、现在开始演示）。

| act | 关键词例子 |
|---|---|
| hook | 评委好、汇报、作品名称、场景 |
| problem | 损耗、痛点、问题是、高达、不足 |
| cause | 原因、断点、因为、卡在 |
| method | 方案、我们做、架构、模块、端、边、云 |
| demo | 演示、操作、第 N 步、现场 |
| evidence | 降到、对比、测试、结果、数据 |
| craft | 安全、规范、知识产权、合规 |
| team | 分工、补台、角色、主讲、操作 |
| close | 总结、请评委、追问 |
| logistics | 交给、下一棒、开始演示、谢谢观看 |

`logistics` 默认 `spoken_only`，不配页。

### 4.3 评分缺口

沿用 P1：不推断扣分。只使用报告里的条目。

每条评分项：

1. 用现有 token overlap 映射到步骤（`ScriptScoreRevisePlanner.bestStep`）。
2. 映射到 `act`：实用性→problem，难易→cause，先进性→method，操作规范/熟练度→demo，成效→evidence，团队→team，职业素养→craft，经济性/可持续→evidence 或 hole。
3. 有步骤且该步骤抽得到所需令牌 → 进入命题候选。
4. 有步骤无令牌 → 命题 `pending_evidence`。
5. 无步骤无令牌 → Hole。
6. 无步骤但讲稿其它处有令牌 → 命题挂到有令牌的步骤，并记 `mapped=false` 供小启说明。

没有评分时：只按幕生成最小命题集（hook / problem / method / demo / close），全部来自讲稿，覆盖率 UI 显示「未钉评分」。

### 4.4 命题装配与排序

固定幕序，**不许模型重排**：

`hook → problem → cause → method → demo → evidence → craft → team → close`

装配规则：

1. 同一 `act` 下，被评分条目命中的步骤优先。
2. 相邻步骤同一 `act` 且令牌重叠 ≥ 50% → 合并为一个命题。
3. `method` 若同时有「一句方案」和「3–5 块结构」，拆成两页：method 一句话 + 架构页，仍算同一命题的两张印刷。
4. `demo`：现场 18–22 分钟只印 1–2 页（步骤总览 + 当前步截图槽），其余步骤 `spoken_only`。
5. 数字令牌出现在 `problem`，必须在后续 `evidence` 找到同单位第二数，否则 `payoffIn` 空，问题页闸失败。
6. 命题总数目标 8–14；超过 14 先合并同幕，再把未被评分命中的 hook/craft 降为 `spoken_only`。少于 6 且讲稿步骤 ≥ 8，允许一命题拆两页，不许用空话补页。

`judgeMustBelieve` 用模板，不靠模型发挥：

| act | 模板 |
|---|---|
| hook | `{项目名}是给{对象}解决{场景}的` |
| problem | `{名词}发生在{地点或阶段}，而且量过` |
| cause | 断点是{令牌列举}，不是空泛管理问题 |
| method | 方案对的是这些断点 |
| demo | 现场按{N}步能做完，谁操作谁讲 |
| evidence | `{数A}到了{数B}，方法可核对` |
| craft | 规范/安全当场可指出 |
| team | 不是一个人，角色补得上 |
| close | 三句话收束：问题、能做、有效 |

缺槽位用讲稿短句填；仍缺则该命题降 `pending_evidence` 或变 Hole。

### 4.5 口播与页上字

- `spoken` 默认 = 主步骤 `content` 压缩到一句。允许一次模型调用，prompt 只给该步骤全文 + 令牌列表，要求：不得出现令牌外的数字和专名，不超过 60 字。
- 输出跑闭包：抽出数字/金额/专名，差集非空则丢弃模型结果，改用「按句号截到 ≤60 字」的确定性截断。
- `onSlide` 只从令牌和模板填。标题 ≤ 16 字（超了切密度 M，再超截断并标 `truncated=true`）。页上总汉字 ≤ `durationSec * 0.5` 且 ≤ 24。
- 念稿闸：`onSlide` 汉字数 / `spoken` 汉字数 < 0.35。不过则减页上字（先丢掉 `line`，再缩短 title），直到过闸或标失败。

### 4.6 出页闸（全部绿才能 `confirmed`→印刷）

| 闸 | 公式 | 失败 |
|---|---|---|
| 令牌闭包 | 所有印刷页字符串中的数字/金额/证书名 ⊆ tokens ∪ holes.forbidden 的补集 | 禁止印刷 |
| 漏洞禁词 | holes.forbiddenOnSlide 不得出现在任何 onSlide | 禁止印刷 |
| 念稿 | 见 4.5 | 该命题不可印 |
| 回收 | 每个 problem 数字令牌必须有 payoffIn | 该问题命题不可印 |
| 覆盖 | 有评分时，每条评分项 ∈ 某命题.scoreItemIds 或某 Hole | 列表必须显示未覆盖，禁止默默丢 |
| 投影 | logistics 步骤不得有 printPage | 编译器自己保证 |
| 时长 | 有页命题的 duration 之和 ∈ [8, 22] 分钟 | 警告可印；<6 或 >28 禁止印刷 |
| 页数 | 印刷页 8–16 | 超了必须先合并 |

用户可在确认前删命题（变 `rejected`）、把 `pending_evidence` 标「本场口头认账」（变 `spoken_only`）。这些动作要留下谁点的。

---

## 5. 印刷层（只值 10%，但必须写死）

### 5.1 页型

| pageType | 槽 | 密度 |
|---|---|---|
| cover | 项目名、一句定位、赛项、匿名角色 | S 无图 / M 有底图 |
| scene | 一句、一张现场图 | 仅 M |
| problem | 标题、一个数字、一句、可选图 | S 无图 / M 有图 |
| contrast | 左数、右数、左标、右标 | 仅 S |
| architecture | 3–5 块标题 | S=3 / M=4 / L=5，禁止自由连线 |
| process | 4–6 横步，每步 ≤4 字 | 按步数切 |
| demo | 序号、截图槽、操作者、讲解者 | S 总览 / M 单步 |
| evidence | 最多 3 个有来源的数 | S=1 / M=3 |
| list | 最多 5 行，行 ≤16 字 | 仅 S；只给规范要点，不准装方案 |
| close | 三句 | 仅 S |

v1 皮肤两套：`arena-dark`（#152238 / 白字 / #e8b86d）、`day-light`（纸色 / 海军字 / 同一强调橙）。整份只能选一套。

### 5.2 act → pageType

| act | 默认页型 | 例外 |
|---|---|---|
| hook | cover，必要时 + scene | 讲稿无项目名则只有 scene |
| problem | problem | 有前后两数则直接 contrast |
| cause | process 或 list | 3 个以上断点用 process |
| method | process（一句）+ architecture | 无模块令牌则只一页 |
| demo | demo | 见 4.4 只 1–2 页 |
| evidence | contrast 或 evidence | |
| craft | list | 无令牌则 spoken_only |
| team | list（匿名角色，禁止姓名） | |
| close | close | 禁止「谢谢观看」空页 |

### 5.3 适配算法（确定性，不是模型排版）

1. 按 act 选 pageType。
2. 量标题字数、有无图、块数，选 S/M/L。
3. 仍溢出：按槽优先级丢掉（先图，再 line，再次要块），标 `truncated`。
4. 禁止：叠字、低于最小字号、另起一种布局、把 problem 改成 bullet 清单。
5. 图槽固定 16:10，`object-fit: cover`。无图走无图变体。

### 5.4 渲染与导出

预览可以用图画。**下载必须是能改字的标准 pptx**（真实文本框和形状）。整页图片打进 pptx 不算交付。细则和右门同一套：`2026-08-18-existing-ppt-full-chain-design.md` 第 5 节。

---

## 6. 已有 PPT

整节以专文为准，这里不缩写：

`docs/superpowers/specs/2026-08-18-existing-ppt-full-chain-design.md`

收口：交来 → 分档读取（不能 100% 懂意思）→ 人对齐 → OOXML 改副本 → 新版本 + 下载，原件不动。Collabora 只给人精调，AI 不进。

---

## 7. 界面（按屏写死）

界面稿已可点。线上用现有小启栏、橙色强调、启发 Office 顶栏，不另做一套黑壳。

### 7.1 入口 · 替换 `/ppt-editor` 落地页

检测本团队：讲稿最新一版、最新评分、资源图片数、启发 Office PPT / 最近 ppt_job。

- 左门：没有能上台的 PPT → 进评委路径。  
- 右门：已有一份 → 先编译路径再进诊断。  
- 底下弱入口：没有讲稿 → 8 句骨架。  
- 论文 PPT、旧问卷生成：收进「历史 / 高级」，不在主视觉。

顶栏：项目名、赛项、评分、返回文档库。

### 7.2 评委路径（主界面，内容真源）

左：命题列表（已绑定 / 待证）+ 漏洞列表。  
中：当前命题 = 评委必须信的那一句 + 讲稿出处 + 评分出处 + 令牌 + 闸状态。  
右：现有小启。编译说明、页上只准印、漏洞认账。  
顶栏：覆盖率（如 11/13）、主按钮「命题过闸，印刷成页」（红闸未清则禁用）。

状态：

- 编译中：左列骨架先出，命题逐条出现（目标 < 8 秒出齐，口播压缩可后填）。  
- 无评分：横幅「未钉评分，只按讲稿出最小路径」。  
- 讲稿版本变了：横幅「讲稿已改到 v8，是否按新稿重编译」，不自动覆盖已确认命题。

### 7.3 印刷预览（分镜）

过闸后才进。14 张左右页型缩略图。点开只改槽（换图、改短标题），不能改 pageType 为未映射类型。主按钮「印成 PPT」。印刷中每张卡从线框变实页，总目标 30–60 秒。

### 7.4 诊断已有 PPT

左：对不上的页（红 L2 / 黄 L1 / 灰补页）。  
中：原页，L1 描将改的字。  
右：小启卡，级别必须写在角标上。按钮：换成问题页 / 只改能塞的字 / 不要 / 下一条。

顶栏文案：「先判断改字还是换结构」，禁止「只改可见文字」这种假保证。

### 7.5 路演台（日常工作台）

启发 Office 新布局 `roadshow`：

| 区 | 内容 |
|---|---|
| 左 | 智能文档讲稿，当前命题步骤高亮，角色锁 |
| 中 | 当前印刷页，槽位可改 |
| 右 | 小启，确认卡 |
| 底 | 分镜条，当前命题页描边 |

讲稿确认写入后问：「命题 p1 对应 P03 要不要按新口播重印？」默认不自动印。重印只动这一页槽，不重抽布局。

顶栏主按钮「去模拟」，不是再生成。

### 7.6 八句骨架（无讲稿）

单行 8 格，提交即当临时讲稿步骤（角色暂空、duration 平均切），再编译。8 格固定：做的是 / 给谁 / 最大问题 / 怎么解决 / 演示哪一步 / 能拿出来的数 / 创新点 / 收束。没有第 9 个字段。有数无来源 → 令牌不建，该句只能进 pending_evidence。

### 7.7 空态与错态

| 情况 | 界面 |
|---|---|
| 项目空、无讲稿无评分无资源 | 只留 8 句骨架，不出现问卷 |
| 评分服务失败 | 按无评分编译，横幅可重试钉评分 |
| 印刷超时 | 已印页保留，未印页可续 |
| 闭包失败 | 列出违规词，定位命题，禁止出页 |
| 409 讲稿被改 | 与现改稿相同：「刷新后再确认」 |

---

## 8. API

全部 JWT，讲稿/评分/资源鉴权与现网一致（讲稿 `createdBy`，评分按团队，资源按团队）。

| 方法 | 路径 | 作用 |
|---|---|---|
| POST | `/api/roadshow/path/compile` | body: `{scriptId?, scoreReportId?, skeleton?}` 返回 path |
| GET | `/api/roadshow/path/{id}` | 读路径 |
| GET | `/api/roadshow/path/latest` | 本团队最新一条 |
| POST | `/api/roadshow/path/{id}/patch` | 删命题 / 认账 / 换图槽，写 revision |
| POST | `/api/roadshow/path/{id}/confirm` | 闸全绿才 200，否则 409+失败闸 |
| POST | `/api/roadshow/path/{id}/print` | 异步印刷，回 job 进度（复用 ppt ws 或新 seq） |
| GET | `/api/roadshow/path/{id}/print/status` | 页完成情况 |
| POST | `/api/roadshow/path/{id}/diagnose` | body: `{pptJobId? , documentId?}` |
| POST | `/api/roadshow/path/{id}/apply-page` | `{page, mode:l1\|l2\|skip\|drop}` 走确认卡 |
| POST | `/api/roadshow/path/{id}/replay` | `{scoreReportId}` 新旧命题 diff |
| GET | `/api/script/{id}/score-revise-brief` | 已有，编译器继续用 |

小启提案新类型（沿用 `ai_assistant_action_proposal`）：

- `confirm_judge_path`：确认整条路径  
- `apply_print_page`：印刷或重印一页  
- `apply_legacy_l1` / `apply_legacy_l2`  
- 已有 `apply_script_patch` 不变

不确认不落盘。TTL 30 分钟沿用。

---

## 9. 小启怎么说话

一次只许短五段，与改稿规格相同：钉住了什么 / 打算做什么 / 进行到哪 / 结果卡 / 回执。

编译完成必须先报：讲稿名+版本、评分 ID+总分、命题数、漏洞数、覆盖率。禁止把整份评分贴进聊天。

改命题口播时：原文/建议/原因（必须带 scoreItemId 或 stepId），确认才写 `path_json`。

---

## 10. 模拟回流

新评分到来（用户点「按最新评分重跑路径」）：

1. 用新报告再编译，不覆盖旧 `judge_path`，出 diff。  
2. 仍信：命题保留印刷页。  
3. 仍是漏洞：保持红框。  
4. 新缺口：新命题或新漏洞。  
5. 旧命题被新评分打穿：标「评委仍不信」，只重开这一张命题，不整份重印。

这是第二层含金量。C 期不做，E 期做。没有这个，产品仍像一次性生成器。

---

## 11. 分阶段

原则：每一期都能单独演示、单独验收。不做「六期做完才看得见」。

### A 期 · 评委路径能看、能过闸（先做）

**目标：** 用户打开项目，8 秒内看到命题和漏洞；能确认；不能印刷假数。

**做：**

- `JudgePathCompiler` 纯函数：抽令牌、分类步骤、装配命题、漏洞、六条闸。  
- 口播先用确定性截断，模型压缩可同期待，但失败必须回退。  
- 表 `judge_path` + `judge_path_revision`。  
- API compile / get / patch / confirm。  
- 前端：AI 应用中心**另开**「路演台」进双门。旧「PPT 制作」入口和页面全部保留。  
- 8 句骨架可提交编译。  
- 小启只展示编译说明，不另做生成动画。

**不做：** 出 PPT、旧 PPT 诊断、路演台、换皮。

**单测（必须先写）：**

1. 讲稿有 23%、评分扣实用性 → 命题 problem，令牌 23%。  
2. 评分扣经济性、全文无金额 → Hole，forbidden 含「万」。  
3. 把「节约 12 万」写进 onSlide → 闭包/禁词失败。  
4. logistics「交给下一位」→ 无 printPage。  
5. 23% 后面没有第二数 → 回收闸失败。  
6. 念稿：页上字 / 口播 ≥ 0.35 → 失败。  
7. 无评分仍能编译最小幕，覆盖率字段为 `unpinned`。

**演示验收：** 用现有智慧农业讲稿 + 一份真实评分。左列能指出至少 1 个漏洞。确认前主按钮在红闸时点不了。

**风险：** 步骤分类关键词误伤。处理：单测金样 3 份真实讲稿，误分只调词表，不加模型分类。

### B 期 · 过闸命题印刷成页

**目标：** 确认后 60 秒内 12–16 页预览可翻，可下载图片型 PPTX。

**做：**

- 8 页型 Vue 组件 + 两套皮 + 密度变体。  
- print API + 进度。  
- 印刷预览屏（界面稿屏 3）。  
- 导出 PNG→PPTX。  
- 左门主路径走完：路径 → 印刷 → 下载。  
- `/ppt-generator` 问卷向导从导航拿掉，历史入口保留。

**不做：** L2 抽色、Collabora 回写、可编辑矢量 PPTX。

**验收：**

- 命题 p1 的 onSlide 与印刷页槽位逐字相同。  
- 改密度后布局仍是同一页型。  
- 禁止印刷时（红闸）print 接口 409。  
- 计时：10 页印刷 p95 < 60 秒（预发环境）。

**风险：** 真实形状导出比出图麻烦。处理：页型形状表先锁 8 套，不临场发挥。预览可以用图，下载必须能改字。

### C 期 · 已有 PPT 全链条

**目标：** 右门从交来到还回去闭环。专文：`2026-08-18-existing-ppt-full-chain-design.md`。

**做：**

- 四个来源收口成 `legacy_deck`，原件只读。  
- 每页阅读档：能改字 / 只能部分改 / 读不全 / 失败。不做默认 OCR。  
- 人对齐后，OOXML 改工作副本（改字 / 换页 / 拿掉 / 补页）。  
- 新版本进启发 Office + 下载标准 pptx。原件不动。  
- Collabora 只给人打开新版本，AI 不写 WOPI。

**验收：**

- 「系统主要模块」对「23%」只能走出「换成另一张」，不能只改字。  
- 改字后，WPS 里能选中新字继续改。  
- 没动过的页，打开后仍能改字，和原件一致。  
- 原件 hash 不变。  
- 读不全的页必须标「这页是图，改不了字」，不能装已识别。  
- 假金额出现在旧页，不处理完不能交付。

**风险：** .ppt 转换丢版式。处理：警告并建议 WPS 另存 pptx；转换失败就停，不硬改。

### D 期 · 路演台 + 讲稿跟随

**目标：** 日常打开就是讲稿 | 当前页 | 小启 | 分镜条。改讲稿后可重印对应一页。

**做：**

- 启发 Office 布局 `roadshow`。  
- 命题 ↔ 步骤 ↔ 页 三向高亮。  
- 并入原计划 Task 7：`apply_script_patch` 确认后问要不要重印该命题页。  
- 槽位编辑写回 `path_json.onSlide`，再印该页。  
- 不自动整份重印。

**验收：**

- 改 s4 确认 → 只问 P03。  
- 重印后 P02、P04 像素级不变（可用哈希或截图像素差）。  
- 角色列仍锁。

**风险：** 分屏已有 sdoc + Collabora。处理：路演台中栏是页型组件，不是 Collabora；「在 Office 打开原件」放菜单。

### E 期 · 评分回流

**目标：** 第二次模拟后，路径出 diff，只重开被打穿的命题。

**做：**

- replay API + diff 结构：kept / broken / newHole / newProp。  
- 路径页增加「按最新评分重跑」。  
- 小启只提被打穿的命题卡。

**验收：**

- 实用性从扣 2 到过线 → p1 标 kept。  
- 新扣经济性 → 只多一个 Hole，已印页不动。  
- 成效仍扣且 9% 被评委质疑 → p5 标 broken，只重开 p5。

### F 期 · 补齐（可砍）

按需，不挡发布：

- 清单页型给规范要点。  
- 附录包（台上时间轴之外）。  
- 可编辑 SVG/PPTX 导出。  
- 任务书摘录入令牌。  
- 皮肤第三套。  
- 讲稿表格视图（原 Task 8，可平行）。

---

## 12. 和现网代码的落点

| 能力 | 落点 |
|---|---|
| 编译纯函数 | `backend/.../service/roadshow/JudgePathCompiler.java` + `JudgePathGates.java` |
| 令牌抽取 | `EvidenceTokenizer.java` |
| 步骤分类 | `StepActClassifier.java` |
| 持久化 | Flyway `V124__judge_path.sql` |
| HTTP | `RoadshowPathController.java` |
| 复用 | `ScriptScoreRevisePlanner` / `ScriptScoreReviseService.latestScore` |
| 前端入口 | 替换 `PptEditor.vue` landing，新视图 `RoadshowPath.vue` `RoadshowPrint.vue` `RoadshowDiagnose.vue` |
| 页型 | `frontend/user/src/views/roadshow/types/*` |
| 路演台 | `InspireOfficeWorkbench` 增 layout=`roadshow`，中栏挂页型 |
| 小启 | `AssistantActionService` 加 3 个类型；面板复用现卡 |
| 印刷导出 | 复用 ppt 工作台 PNG→PPTX；不走 questionnaire generate |
| 下线 | 学生导航去掉「创建问卷 PPT」主按钮；`PptGenerator.vue` 仅历史深链 |

论文 PPT：`selectedDeckType=paper` 仍进旧链，入口只留高级。

---

## 13. 权限、确认、回滚

- 编译：能读该讲稿、该团队评分、该团队资源的人。  
- 确认/印刷/L1/L2：与讲稿相同，本期 `createdBy`（团队共享不在本期放大）。  
- 不确认：`judge_path` 可存 `compiled`，PPT 文件不写，讲稿不动。  
- 回滚：`judge_path_revision` 覆盖 path_json；印刷页按页保留上一张 PNG。  
- 讲稿 409 规则不变。

---

## 14. 成功标准（产品，不是工程自嗨）

A 期结束后就可以对外说：

1. 不再为了出 PPT 填问卷。  
2. 评委还不信的事，系统用红框说，不会写成一页假内容。  
3. 页上数字都能指回讲稿或资源。

B 期结束后：

4. 从确认命题到可下载 < 1 分钟。  
5. 台上是 12–16 页，不是 38 页清单。

D+E 结束后：

6. 改一句讲稿只动对应页。  
7. 第二次评分后，只重开被打穿的命题。  
8. 这是 OREP 独有闭环，不是套模板网站。

做不到 1–3，B 期不许开工。做不到 4–5，不算路演 PPT 换完。做不到 6–7，仍是一次性生成器。

---

## 15. 自检

- 无「以后再说」的核心规则：闸、令牌、L1/L2、幕序都已写死。  
- 与上一版不矛盾：已删除「版式不动却换结构」；模板降为印刷。  
- 范围按期切开，A 期可独立演示。  
- 台上薄 PPT 是主交付；厚附录明确不做于 A–E。  

界面对照：`docs/superpowers/mocks/2026-08-18-roadshow-stage-ui.html`（顶栏「评委路径」即 7.2）。
