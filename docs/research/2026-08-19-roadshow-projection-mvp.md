# 竞赛大脑·证据—命题—投影模型 MVP 实现规范

| 项 | 内容 |
|---|---|
| 版本 | 2026-08-19 MVP-0 |
| 依据 | 修订稿 E（理论冻结）。本文不是修订稿 F。 |
| 目的 | 把 E 压成老师愿意维护、工程做得出来的最小可运行闭环，用来验证 Projection Intelligence 是否成立。 |
| 产品承诺（本阶段） | 不承诺提分。验证：同一批证据，两个不同页面任务，能选出不同材料，并给出可回放的选择理由。 |

E 已经够用。本文只回答怎么做第一版，以及明确什么现在不做。

---

## 0. 三条红线（比功能列表更先遵守）

1. **Assessment 按需生成，禁止全矩阵。** 150 个命题 × 30 个观测点 = 4500 条，老师不会维护。只在命题进入某页候选集时，对该页相关观测点建评估。
2. **决策轨迹内部完整，用户只看关键决策。** 库里 200 条全部参与计算。落盘和界面只保留：入选、差一点入选、被关键约束淘汰、与下一页抢资源的候选。每页最多展示「选它的 2 个原因 + 没选另外 2 个的原因」。
3. **V1 只做一个赛道、一个评分表、一个 Presentation Profile、两个 Page Intent。** `Aggregate = max` 写死。组合规则引擎、38–45 页整本出稿、22 个文件夹、Observation / 诊断回写，全部不进本 MVP。

底层对象通用；本 MVP 上层必须是职业技能大赛的窄切片，不是「什么演讲都能用」的空壳。

---

## 1. 本版验证什么、不验证什么

### 1.1 必须跑通的一条链

```
8 条时事证据
  → 8 个命题（人确认）
  → 2 个 Page Intent（紧迫感 / 桥接到项目问题）
  → 系统选出 2 条不同材料
  → 生成 2 页可见文字 + 2 段讲稿
  → 输出决策轨迹与关键理由
```

这条链一旦成立，才能说「投影智能」不是加权排序器。40 页好看 PPT 不能证明这件事。

### 1.2 验收（写进测试，不写进宣传）

| # | 断言 | 失败意味着 |
|---|---|---|
| T1 | 上场每一短句能指回命题，再指回至少一条已核验证据 | 又在发明句子 |
| T2 | 两页 Intent.role 不同，选中集合必须不同；禁止「同一命题、只改标点」冒充任务依赖 | 还是 Top-K |
| T3 | 固定库，只改第 4 页 role：选中集合变化，**或**选中不变时 `expression.task_focus`（urgency/bridge）必须变，且 slide 含任务相关槽（紧迫页含「当下」，桥接页含痛点命题） | 伪智能：同选 N4，只改一个逗号 |
| T4 | 每页 \(\Delta\) 的 reasons 因子都能在 trace 里找到 | 事后编理由 |
| T5 | 界面理由 ≤ 选 2 + 不选 2；完整 trace 只在内部/调试开关 | 做成算法调试器 |
| T6 | Assessment 条数 ≤ 候选命题 × 该页相关观测点数；不得出现 Claim×全量 R | 全矩阵 |
| T7 | 空库或 Required 不齐时，页输出「本场无法完成」，不生成默认命题 | 套话机器 |
| T8 | 软成功只标「待人审」，系统文案不得出现「评委已理解」 | 装懂 |

### 1.3 明确不做

- 不改已有番茄 38 页设计稿的 XML，不压成十几页。
- 不接 Collabora 当 AI 改稿引擎。
- 不预告分数、不对照界面改分、不新造评分引擎。
- 不实现 V2 组合充分度。
- 不建 22 个用户可见文件夹。
- 不做录像 Observation、不做 A/B/C/D 诊断回写。表结构可留空位，本 MVP 不写业务。
- 不把七层做成七个微服务。

---

## 2. 接到现有 OREP 模块，不新开产品门

| 模型对象 | 落在现有能力 | 本 MVP 怎么用 |
|---|---|---|
| Evidence 原件 | 资源中心 / 项目文件 | 存 URL、上传件、摘录；不另做资料库 App |
| Claim 正文 | 智能文档（`inspire_smart_doc`）或本规范新瘦表 | 人看到的是「一条判断」，可改字 |
| 赛道与观测点 | `track_rubric_config` + v1.2 人工智能赛道 | 只读正式观测点名称，不改评分定义 |
| 页输出 | 旧智能 PPT 槽，或两页纯文本预览 | 先保证字来自投影；版式漂亮不是验收 |
| 讲稿 | 讲稿表 / 智能文档按页两段 | 与页同序，不得超事实 |
| 路演 / 评分 / 复盘 | 已有模块 | 本 MVP 不调用 |

用户入口建议挂在现有项目工作台的一个窄入口，文案用「这场先出两页时事」，不用「竞赛大脑七层操作系统」。

---

## 3. 最小对象：8 张表，不是 8 个系统

项目级前缀建议 `rs_`（roadshow content），避免和评分引擎的 `ai_score_evidence_*` 混成一套。

| 表 | 必须实现 | 说明 |
|---|---|---|
| `rs_evidence` | 是 | 事实证据 |
| `rs_claim` | 是 | 瘦命题 |
| `rs_claim_evidence` | 是 | 命题—证据多对多 |
| `rs_claim_relation` | 是 | 最小关系集 |
| `rs_assessment` | 是 | 稀疏，按需 |
| `rs_page_intent` | 是 | 本 MVP 只种子 2 条 |
| `rs_projection_run` | 是 | 一次出稿 |
| `rs_projection_page` | 是 | 页结果 + 压缩后的 \(\Delta\) + 表达 + 讲稿 |

不建独立的 Expression 表、Observation 表、Evaluation 表。表达和讲稿挂在 `rs_projection_page`。Observation / Evaluation 本阶段不建表。

配置（Profile、默认 \(\mu\)、赛道切片）用一份 JSON 种子，不建规则引擎表。

---

## 4. 最小字段

约定：`必填` = 没有就不能进下一步。`模型` = 可起草，默认草稿。`人` = 必须有人点过确认，或人改过并保存。`系统` = 计算得出，人不能当事实改（改了要回草稿）。

### 4.1 `rs_evidence`

| 字段 | 谁写 | 必填 | 备注 |
|---|---|---|---|
| id | 系统 | 是 | |
| project_id | 系统 | 是 | |
| source_url 或 file_id | 人 | 二选一 | 无指针不得核验 |
| source_title | 模型/人 | 是 | |
| source_date | 人 | 建议 | 时事无日期不得标已核验 |
| original_quote | 人 | 是 | 能回原文 |
| extracted_fact | 模型 | 是 | 原子事实，不是判断 |
| metric_json | 人 | 有数才填 | 无口径不得填点估计 |
| verification_status | 人 | 是 | `draft` / `verified` / `disabled` |
| category | 系统/人 | 可空 | MVP 默认 `news`，不强迫选 22 叶 |

**人在这一层只做：** 粘贴/上传来源，核对摘录和日期，点「这条出处没问题」。

### 4.2 `rs_claim`

| 字段 | 谁写 | 必填 | 备注 |
|---|---|---|---|
| id | 系统 | 是 | |
| project_id | 系统 | 是 | |
| proposition | 模型/人 | 是 | 一句判断 |
| status | 人 | 是 | `draft` / `ready` / `disabled`。`ready` = 可以进候选，**不是「已被证明」** |
| category | 系统 | 可空 | MVP 默认 `news` |

禁止字段：`slide_line`、`speak_line`、`sufficiency`、`rubric_ids`、`confidence`、`pair_id`。

界面文案：

- `ready` → 「可以上场候选」
- 禁止 → 「已证明」「已核验通过，评委该给分」

Evidence `verified` 只表示材料真。Claim `ready` 只表示这句话写清楚了、至少挂了一条已核验证据。这句话够不够撑某个评分点，只看 Assessment。

### 4.3 `rs_claim_evidence`

| 字段 | 谁写 | 必填 |
|---|---|---|
| claim_id, evidence_id | 模型建议，人可改 | 是 |

一条命题可挂多条证据。MVP 时事链通常 1:1，允许 1:N。

### 4.4 `rs_claim_relation`

最小类型，禁止自由字符串：

| type | 含义 | MVP 是否用 |
|---|---|---|
| `supports` | A 支持 B | 可用 |
| `contradicts` | A 与 B 冲突 | 可用（冲突则两条都不能 `ready` 到上场，除非人裁决） |
| `responds_to` | 策略回应痛点 | 本链不用 |
| `bridges_to` | 外部事件桥接到项目问题 | **本链硬成功要用** |
| `depends_on` | 依赖 | 不用 |
| `refines` | 细化 | 不用 |

| 字段 | 谁写 | 必填 |
|---|---|---|
| from_claim_id, to_claim_id, type | 模型建议，硬成功需要的那条人确认 | 是 |

第 5 页硬成功：必须存在 `bridges_to(选中的时事命题, 已有项目痛点命题)`。MVP 允许预置 1 条项目痛点命题（人手写一句「成熟度误判导致损耗」），不必先做完痛点子系统。

**`bridges_to` 成立 ≠ AI 理解了叙事。** 它只证明系统按预定义关系完成了可机检的桥接任务。「读完是不是自然桥接」只属于 soft success，由人勾选。系统文案、测试名称、提交说明里禁止写「AI 已经理解叙事」。

### 4.5 `rs_assessment`（稀疏）

| 字段 | 谁写 | 必填 | 备注 |
|---|---|---|---|
| claim_id, rubric_id | 系统在进入候选时创建 | 是 | 不得预先铺全表 |
| strength | 模型建议，人可改 | 是 | 0–3 |
| verifiability | 模型建议，人可改 | 是 | 0–2 |
| chi | 系统 | 是 | 默认 \(\mu\)，界面显示 E 档短句，文案须带「准备态，不是正式分」 |
| created_by_run_id | 系统 | 是 | 首次因哪次 run 进入候选 |
| created_by_page_intent_id | 系统 | 是 | 首次因哪条 Intent |
| created_for_rubric_id | 系统 | 是 | 与 `rubric_id` 相同，单独落列以便审计，禁止只存一句「第4页候选时创建」 |

实例化规则：

```
当 claim K 通过第 4 页或第 5 页的硬过滤，进入候选集：
  对该页 related_rubrics 里每一个 r：
    若不存在 A(K,r)，则插入一条，status=suggested
      created_by_run_id / created_by_page_intent_id / created_for_rubric_id 一次写死
    若已存在，复用，不改 created_by_*（第 5 页再用同一 Claim 时仍能回答「它为什么存在」）
人确认或修改后 → confirmed
投影只读 confirmed 或 suggested（suggested 可用，但「下一步」里提示「还没确认」）
禁止：对未进入任何候选集的 (K,r) 建行
禁止：后台提供「生成全部评估矩阵」按钮
工程约束（必须进测试）：没进过任何候选集的 Claim，rs_assessment 行数 = 0。
```

本链 `related_rubrics` 只有一个正式观测点：人工智能赛道 v1.2 **实用性**（问题是否来自真实场景）。不把 15 个观测点都挂上。

V1：`Suff(页或场, r) = max(chi)`。代码里留 `aggregateSufficiency(list) { return max(list) }`，没有配置 DSL。

### 4.6 `rs_page_intent`（种子，不是老师填的表单）

本 MVP 只插入两行，老师不新建 Intent。

**Intent A（页序 4，制造问题紧迫感）**

```
role: 制造问题紧迫感
required: 1 条已 ready 的时事命题；冲击因子高；可指认现场或具体事件
forbidden: 展开技术方案；本页做桥接
budget: 1 个命题
related_rubrics: [实用性]
hard_success:
  - 恰好引用 1 个 news claim
  - 未引用技术实现类命题
  - 未创建 bridges_to（本页不做桥接）
soft_success:
  - 人勾选：读完能感到问题就在当下
```

**Intent B（页序 5，转到本项目问题）**

```
role: 从社会问题转到本项目问题
required: 1 条时事命题；与预置痛点存在 bridges_to
forbidden: 展开技术方案
budget: 1 个命题
related_rubrics: [实用性]
hard_success:
  - 恰好引用 1 个 news claim
  - 存在 bridges_to(该 claim, 预置痛点)
  - 与第 4 页不是同一 claim
soft_success:
  - 人勾选：读完能从外部事件理解项目问题，不是两句并列
```

### 4.7 `rs_projection_run` / `rs_projection_page`

| 字段 | 谁写 | 必填 |
|---|---|---|
| run_id, project_id, profile_id | 系统 | 是 |
| profile_id | 种子 | 固定 `contest_1h_slice_news` |
| page_index, intent_id | 系统 | 是 |
| selected_claim_ids | 系统 | 是 |
| expression_slide_text | 模型 | 是 | 由 Intent + Claim + Evidence 生成，不是库字段 |
| expression_speaking | 模型 | 是 | 同上 |
| hard_success_pass | 系统 | 是 | |
| soft_success_status | 人 | 是 | `pending` / `accepted` / `rejected` |
| decision_compact_json | 系统 | 是 | 见第 6 节，不是全量 200 行 |

讲稿就是 `expression_speaking` 按页展开，可人改字。人改了数字或专名：必须回写 Claim/Evidence 草稿，或拒绝保存并提示「这段话里有库里没有的数」。

---

## 5. 用户到底要维护多少东西（维护预算）

本条链上，老师/学生的必做动作上限：

| 步 | 人做什么 | 次数 |
|---|---|---|
| 1 | 提交 8 个来源（链接或文件）并确认摘录 | 8 |
| 2 | 确认或改 8 句命题 | 8 |
| 3 | 确认或改一条预置痛点 | 1 |
| 4 | 需要时确认系统建议的 Assessment（通常远小于 16） | ≤16，常见 4–8 |
| 5 | 看两页结果；软成功各打一个勾 | 2 |
| 6 | 若理由不对，改 Intent 不改——本 MVP 老师不改 Intent，只反馈「这页选错了」 | 0 或提 issue |

人工维护对象数量控制在 **20–30 个确认动作量级**（确认出处、确认命题、确认评估、软成功勾选）。这不是对外承诺的「20–30 次点击」：打开原文对照摘录是一次确认动作，不是一次按键。产品上要观察的是完成率、实际耗时、放弃点；点击数只做辅助。禁止把「20–30 次点击」写进对外说明。

首页（本入口内）只显示最多 3 句下一步，例如：

1. 还有 2 条时事没确认出处
2. 第 5 页还缺「桥接到项目痛点」
3. 第 4 页软成功还没人看

禁止首页出现充分度百分比、投影率、预计得分。

---

## 6. 选择算法与轨迹（必须可回放，界面必须短）

### 6.1 计算顺序（不得先选定再写理由）

对每一页：

1. 硬过滤：`claim.status=ready`；证据 `verified`；未禁用；未过期（时事无日期或 >180 天淘汰）；本页 forbidden。
2. 轮廓：Required 能否被至少一个候选填上。不能则停，页状态 `blocked`。
3. 按需建 Assessment。
4. **V1 Selection 必须 deterministic。** 因子写死，不接 LLM 打分、不设温度。比较顺序固定：

   1. 硬约束（ready、证据已核验、未过期、未 irrelevant、未 contradicts、本页 forbidden）
   2. 轮廓：Intent A 要求 impact≥4 且 ostensible≥4；Intent B 要求已有 `bridges_to(候选, 预置痛点)`
   3. role 主因子：A = impact，然后 ostensible；B = bridge_value，然后 impact
   4. diversity：与本场已选不同簇优先；B 淘汰与第 4 页相同 claim
   5. chi 降序
   6. freshness 降序（越新越大）
   7. **stable_id 升序（最后平局钉死）**

   同一输入 + 同一配置 + 同一证据/命题版本 = 同一选择。这是 CI 约束，不是愿望。因子来自种子 `rank_factors_json` 与 Assessment.chi，禁止运行时让模型改因子。

5. 取 budget=1。
6. 写 compact \(\Delta\)，reasons 只从 trace/factors 生成。Block 0 的 Expression 用任务模板（`task_focus=urgency|bridge`），**不接生成模型**。
7. 跑硬成功。软成功置 `pending`。不得输出「评委已理解」。

### 6.2 落盘：Top-N explanation

`decision_compact_json` 只允许这些块：

```
{
  selected: [{ claim_id, factors, matched, violated }],
  runner_up: [{ claim_id, factors, why_not }]     // 最多 2
  eliminated_key: [{ claim_id, constraint }]      // 最多 2，如同簇、留给下页
  reserved_next: [{ claim_id, for_intent_id }]    // 最多 1
  trace_steps: ["filter:8→6", "rank:A", "pick:N4", "reserve:N8"]
}
```

全量 8 条的因子分可以进日志或调试开关，不进默认 API、不进默认 UI。

界面固定四行以内：

```
选 N4：现场冲击强，事件可指认
不选 N8：更适合下一页桥接
不选 N1：和 N4 同一类损耗通稿，冲击更弱
```

reasons 的因子必须是 compact JSON 里出现过的键。测试 T4 扫这个。

### 6.3 算例（与 E 第 12 节同一库，作为夹具）

种子 8 条类型（不要编造真实新闻标题当实测）：N1 损耗通稿、N2 同事件、N3 政策动态、N4 储运爆仓有现场、N5 无关财经、N6 地方试点、N7 过期、N8 分级误判有对照。

合法：第 4 页 N4，第 5 页 N8。  
非法：两页都是「分最高的两条」且相同；第 4 页 N3+N6；N1+N2 同簇。

夹具测试必须覆盖 T2/T3。

---

## 7. 配置切片（专家模板，不是通用引擎）

一份种子文件即可，例如 `config/rs_mvp_ai_contest_1h_news.json`：

```
track_id: 人工智能
rubric_internal_version: v1.2
rubrics_in_scope: [实用性]
profile: contest_1h_slice_news
intents: [intent_urgency, intent_bridge]
mu_table: E 正文默认表（仅准备态标签）
aggregate: max
relation_types: [supports, contradicts, bridges_to]
news_fresh_days: 180
```

42 赛道的其它观测点、其它 Intent、组合规则，全部不出现在这份文件里。底层表通用，本文件必须很「大赛化」、很窄。

---

## 8. 界面（只做这一条链需要的 4 个屏）

日常用语，不用模型符号。

1. **证据。** 8 张卡片：来源、日期、摘录、事实句、「出处没问题」。
2. **判断。** 8 句命题 + 挂了哪条证据。「可以上场候选」。另有 1 句预置痛点。
3. **两页结果。** 左页画面/文案，右页讲稿。下展开「为什么这样选」（最多 4 行）。硬成功红/绿。软成功一个勾。
4. **下一步。** 最多 3 件事。

不要：22 目录、评估矩阵表、200 行 trace、预计得分、E0–E5 希腊字母、L1/令牌/命题权。

准备态若借用 E 档，必须写成「按准备情况，现在像 E3，不是正式分」。

---

## 9. 实施切块（仍然可以停在阶段 II）

**块 0 — 种子与表。** 8 张表 + JSON 配置 + 夹具 8 条。无 UI 也可单测 T2/T4/T6/T7。

**块 1 — 入库。** 资源中心收 8 个来源，抽出 fact 与 claim，人确认。维护预算第 1–3 步。此时已是可用的「8 条时事证据本」，即使不出 PPT。

**块 2 — 投影。** 两个 Intent，按第 6 节选，落 compact \(\Delta\)，生成两页文字和两段讲稿。跑 T1–T8。

**块 3 — 入口。** 4 个屏挂进现有工作台。自己用番茄项目的真实时事走一遍，记下卡点。

块 1 单独可交付。块 2 才叫投影智能验证。未过 T2/T4，不得做第 3 页，更不得做 40 页。

---

## 10. 与 E 的对应（防止实现时加回层）

| E | 本 MVP |
|---|---|
| 七层对象 | 8 张表 + 现有 7 个产品入口中的 4 个 |
| Presentation Profile | 一个 JSON 切片 |
| 38–45 | 不生成，只在配置注释里标明这是 1 小时画像的两页 |
| Suff 可组合 | 接口冻结为 max |
| Observation / Diagnosis | 不做 |
| 22 叶 | 后台 category 可空，默认 news |
| 证据地图 | 缩成「下一步 ≤3」 |
| 修复优先级 | 本阶段用不上；人发现讲错了就打回 Evidence/Claim 草稿 |

---

## 11. 完成定义

本 MVP 完成，当且仅当：

1. 夹具 8 条上 T1–T8 全绿。
2. 用一份真实项目时事（允许仍是番茄主题）人工走通块 1–3，老师侧点击次数可数，且没有评估矩阵页。
3. 换 Intent.role 的回归能在 CI 里跑。
4. 没有任何界面出现预计得分、22 个空文件夹、或「评委已理解」。

未完成前，不排 40 页出稿、不排诊断回写、不排第二赛道。

理论停在 E。做重了，就是本规范失败，不是模型还缺一层。

---

## 12. Block 0 钉死（建表前必读）

对象不再改，第一条链不再换。下面是编码前必须无歧义的点。

### 12.1 八张表如何对应七层（禁止再发明表）

```
Evidence
   ↓  (rs_claim_evidence)
Claim ── ClaimRelation
   ↓
Assessment ↔ Rubric（按需，稀疏）
   ↓
PageIntent          ← 配置种子，不是第七层
   ↓
ProjectionRun       ← 一次生成执行记录，不是「第七层对象」
   ↓
ProjectionPage      ← MVP 物化：页结果 + Expression + compact Decision
```

| 表 | 是什么 | 不是什么 |
|---|---|---|
| `rs_projection_run` | 一次投影执行 | 不是 Evaluation，不是第七层 |
| `rs_projection_page` | 该页结果 + 表达 + 压缩轨迹 | 不是独立 Expression 对象 |
| （不建）`rs_expression` | — | 禁止再加这张表 |
| （不建）Observation / Evaluation | — | 本阶段不建 |

开发人员看到 8 张表后自行加 `rs_expression`，视为违反本规范。

### 12.2 Assessment 生命周期列

`created_reason` 禁止只存中文句子。必须三列：`created_by_run_id`、`created_by_page_intent_id`、`created_for_rubric_id`。同一 Claim 先因第 4 页建评估、后被第 5 页复用时，created_by_* 保持首次值。CI：未进候选集的 Claim，评估行数 = 0。

### 12.3 负向夹具（与快乐路径同等强制）

| 夹具 | 输入 | 必须 |
|---|---|---|
| Happy | 第 12 节 8 条类型 + `bridges_to(N8, 痛点)` | 第 4 页 N4，第 5 页 N8 |
| Neg-A 空库 | 0 条 ready | 两页 `blocked`，`expression_*` 空，不发明句子 |
| Neg-B 全低质 | 8 条 ready 但无人满足 Required | `blocked`，不降级选「最不差的」 |
| Neg-C 冲突 | 唯一满足 A 轮廓的是 N4，且 N4 `contradicts` 另一条 | **不得选 N4**；无替补则 blocked |

### 12.4 Block 0 实施顺序（本阶段到此为止）

1. 表结构（Flyway，无 `rs_expression`）
2. 种子：两个 Intent + 配置 JSON
3. 负向夹具 + Happy 夹具
4. **deterministic selector**（无 LLM）
5. T1–T8 与三条负向夹具进 CI
6. **然后才允许**接模型生成 Expression

同一输入、同一配置、同一版本证据和命题，Projection **选择**必须可复现。先接模型再测选择，视为顺序错误。

### 12.5 本阶段验收看什么

选没选对；为什么选能否回放；换任务会不会变；没材料会不会拒绝；是否完全不发明事实。**版式漂亮不是验收。** 老师耗时与放弃点留到块 3 入口后再测，不在 Block 0。
