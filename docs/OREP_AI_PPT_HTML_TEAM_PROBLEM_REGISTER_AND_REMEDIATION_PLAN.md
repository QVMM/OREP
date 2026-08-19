# OREP AI 生成 PPT 式 HTML 功能

## Team 联合问题台账与整改总方案

更新时间：2026-04-27  
来源依据：

- [OREP_AI_PPT_HTML_AGENT_TEAM_REASSESSMENT.md](/Users/liuyixing/项目/OREP/docs/OREP_AI_PPT_HTML_AGENT_TEAM_REASSESSMENT.md)
- 当前代码主干实现
- 已有专项实施文档与阶段性改造结果

---

## 1. 文档目标

这份文档不再重复“角色怎么评价”，而是把 team 评审结论整理成：

1. 全量问题台账
2. 问题分类与优先级
3. 是否可解决的判断
4. 对应解决方案
5. 方案之间是否有冲突
6. 立即处理项与第二阶段项
7. 具体到文件/模块的整改任务表

目标是让后续所有整改都以这份文档为**统一问题总表**，避免再出现：

- 问题重复说
- 同一问题在不同文档里口径不一致
- 先修了体验，后面又被底层逻辑打回去
- 先修了页面，结果评分和交付门禁仍然不认

---

## 2. 总体判断

### 2.1 当前系统所处阶段

OREP 现在已经不是“一个会生成 HTML 的功能”，而是一套由以下子系统组成的复合平台：

- 问卷与项目画像
- Round 1/2/3/4 生成流水线
- 页面契约与页系样张
- 质量检查
- 视觉审查
- 单页修复 / 单页重设计
- 素材证据与绑定
- 评分覆盖
- 路演结构体检
- 下载条件与交付门禁

它的优点是能力已经很强。  
它的核心问题不是“功能太少”，而是：

> 功能已经足够多，但最终成品质量、比赛原生逻辑、系统真相源、用户主路径还没有彻底统一。

### 2.2 统一整改原则

后续所有整改必须遵守 4 条原则：

1. **先定义“什么叫好页面”，再修系统**
2. **先定义“什么算比赛达标”，再谈下载门禁**
3. **后端必须提供唯一当前真相，前端不能再大量二次判案**
4. **用户主路径必须尽量回到当前页，不再让用户频繁跨区理解系统**

---

## 3. 全量问题总表

下面把 team 评审里的问题去重后整理为 4 大类、20 个一级问题。

字段说明：

- `编号`：统一问题 ID
- `类别`：成品 / 比赛逻辑 / 系统实现 / 用户体验
- `问题`：问题描述
- `影响`：为什么严重
- `是否可解`：`可直接解决 / 可阶段性解决 / 只能缓解`
- `建议阶段`：`P0 立刻处理 / P1 第一阶段 / P2 第二阶段`

---

### A. 最终成品类问题

| 编号 | 问题 | 影响 | 是否可解 | 建议阶段 |
|---|---|---|---|---|
| A1 | 页面仍有明显 HTML 味，像网页模块拼装 | 直接影响评委观感，降低“专业 PPT 感” | 可直接解决 | P0 |
| A2 | 技术页、实操页、价值页、创新页最容易模板化 | 最影响比赛得分核心页 | 可直接解决 | P0 |
| A3 | 证据页常常是“内容页加证据”，不是“证据主导页” | 实操与可信度不足 | 可直接解决 | P0 |
| A4 | 主视觉焦点不稳定，很多页信息齐但无记忆点 | 影响路演吸引力与讲解效率 | 可阶段性解决 | P1 |
| A5 | 页系样张仍不够完整，风格更像“封面样张” | 无法稳定输出整套风格化比赛页 | 可直接解决 | P0 |
| A6 | 章节开场页、突破页、结果页、收束页镜头感不足 | 页面虽对，但“不像上台稿” | 可阶段性解决 | P1 |

### B. 比赛逻辑类问题

| 编号 | 问题 | 影响 | 是否可解 | 建议阶段 |
|---|---|---|---|---|
| B1 | 底层评分覆盖仍残留商业 BP 语义 | 会把系统优化方向带偏 | 可直接解决 | P0 |
| B2 | 结构检查存在，但节奏控制不够比赛原生 | 容易前松后挤，实操不突出 | 可直接解决 | P0 |
| B3 | 实操页更像流程说明页，而不是操作能力展示页 | 直接影响技能水平打分 | 可直接解决 | P0 |
| B4 | 团队协作、安全规范、职业素养页易变成“态度表达页” | 存在但不服务评分 | 可直接解决 | P1 |
| B5 | 创新与应用价值页容易泛化，缺少量化与证据 | 影响创新与应用价值得分 | 可直接解决 | P1 |
| B6 | 当前“可下载”不等于“比赛终稿版” | 用户误以为能下就能上台 | 可直接解决 | P0 |

### C. 系统实现类问题

| 编号 | 问题 | 影响 | 是否可解 | 建议阶段 |
|---|---|---|---|---|
| C1 | 当前真相源过多，task/html_page/quality/scoring/snapshot 并存 | 状态漂移、结果打架 | 可直接解决 | P0 |
| C2 | 多个读接口带写副作用 | 刷新页面会“悄悄改状态” | 可直接解决 | P0 |
| C3 | HTML 真值与交付给前端的页面不完全一致 | 修复、下载、预览可能看见不同版本 | 可直接解决 | P0 |
| C4 | 评分覆盖仍高度依赖文本启发式 | 一键补评分点效果不稳定 | 可直接解决 | P0 |
| C5 | repair / fallback / rebuild / deliverability 仍是并行环路 | 难以稳定判断“当前到底通过没” | 可阶段性解决 | P1 |
| C6 | 页面契约已接入，但 deterministic validator 还不完整 | 契约有时只是“希望 AI 遵守” | 可直接解决 | P0 |
| C7 | 素材绑定仍偏推荐型，硬关系层不足 | 传了图也可能不被认 | 可直接解决 | P1 |
| C8 | history-detail 是超级聚合接口，过重 | 性能和一致性都有风险 | 可阶段性解决 | P1 |
| C9 | `ppt_service.py` 仍是超级单体 | 维护成本高，易交叉影响 | 可阶段性解决 | P2 |
| C10 | 旧链路和新链路仍有并存遗留 | 新人难判断主链路，兼容逻辑复杂 | 可直接解决 | P1 |

### D. 用户体验类问题

| 编号 | 问题 | 影响 | 是否可解 | 建议阶段 |
|---|---|---|---|---|
| D1 | 生成完成后，用户要做的事仍太多 | 用户预期落差大 | 可阶段性解决 | P1 |
| D2 | 预览页虽然已成主工作台，但仍偏重 | 普通用户仍有压迫感 | 可阶段性解决 | P1 |
| D3 | 内部概念暴露仍偏多 | 增加理解成本 | 可直接解决 | P1 |
| D4 | 下载链路虽改善很多，但还不够“系统替我过关” | 用户仍会犹豫和焦虑 | 可阶段性解决 | P1 |
| D5 | 等待过程不是零焦虑，用户仍不完全知道系统在做什么 | 长时间生成时体验不稳 | 可阶段性解决 | P2 |
| D6 | 素材证据、评分补强、修页仍存在分散理解负担 | 工作台还未彻底“当前页化” | 可阶段性解决 | P1 |

---

## 4. 先解决什么：优先级分层

## 4.1 必须立刻处理的问题

这些问题如果不先处理，后面继续加功能、改交互、做比赛页，都会反复被打回。

### P0-A：比赛页成品能力

- A1 页面仍有明显 HTML 味
- A2 技术页/实操页/价值页模板化
- A3 证据页不是证据主导页
- A5 页系样张体系不完整

### P0-B：比赛逻辑底座

- B1 评分覆盖仍残留商业 BP 语义
- B2 节奏控制不够比赛原生
- B3 实操页不够像操作能力展示页
- B6 可下载不等于比赛终稿

### P0-C：系统真相源与执行闭环

- C1 当前真相源过多
- C2 读接口带写副作用
- C3 HTML 真值与交付页面不一致
- C4 评分覆盖文本启发式太重
- C6 页面契约 deterministic validator 不足

### 为什么这些必须先处理

因为这些问题决定的是：

- 系统生成出来的东西到底像不像比赛页
- 系统对“通过”与“不通过”的判断到底稳不稳
- 后面再修前端体验时，会不会又被底层状态打回来

如果这些不先处理，后面很多体验优化只是“更舒服地使用一个仍不完全稳定的系统”。

---

## 4.2 可以排到第二阶段的问题

这些问题重要，但不一定非要卡在第一批，否则节奏会被拖散。

### P1：第一阶段后半段

- A4 主视觉焦点不稳定
- A6 镜头感不足
- B4 团队/安全/职业素养页不够评分化
- B5 创新与应用价值页量化不足
- C5 repair/fallback/rebuild/deliverability 统一状态机
- C7 素材硬绑定层
- C8 history-detail 聚合瘦身
- C10 旧链路彻底收口
- D1 生成后用户工作量过大
- D2 预览页仍偏重
- D3 内部概念暴露
- D4 下载流程更智能
- D6 工作台彻底当前页化

### P2：第二阶段

- C9 `ppt_service.py` 深度拆域
- D5 等待体验再进一步真实化
- 更深入的性能优化与自动回归基建

---

## 5. 问题是否能解决：可解性分析

## 5.1 可以直接解决的问题

这类问题已经有明确方向、已有部分基础设施，只差系统化推进：

- 页面契约硬化
- 页系样张接入主生成 / rebuild / fallback
- 视觉审查按契约输出问题类型
- repair 按契约进行单页重设计
- 评分覆盖切到比赛评分底座
- 下载状态分层为 `blocked / warning / ready`
- 预览页主工作台化

这些问题是**可直接解决**的，不存在理论障碍，关键在于顺序和收口。

## 5.2 可阶段性解决的问题

这类问题可以明显改善，但不适合许诺“一步到位”：

- 视觉焦点稳定性
- 镜头感和章节情绪控制
- 创新/价值页的高级专业感
- 用户等待焦虑完全清零
- 前端工作台做到极简而不丢能力

这类问题更适合：

1. 先定义规则
2. 再做主链路
3. 再做回归和 A/B

## 5.3 只能缓解、很难彻底消失的问题

这类问题属于生成式系统的长期属性：

- 某些页在信息不足时仍可能产生普通感
- 不同行业、不同任务的视觉偏好差异大
- “比赛页的高级感”带有一定主观审美

这些无法用一次性工程完全消灭，但可以通过：

- 页系样张
- 契约校验
- 截图级回归
- 候选页 accept/reject

把问题压到可控范围。

---

## 6. 方案之间会不会有冲突

这里是最关键的部分。不是所有正确方案都能同时推进，必须识别冲突。

## 6.1 主要冲突点

### 冲突 1：前端体验减法 vs 后端状态还不稳定

表现：

- 如果前端先极限简化，只保留少量动作
- 但后端当前真相源和门禁还没收口
- 那用户会更迷惑，因为前端给的推荐可能不准

结论：

- 必须先解决 `C1/C2/C3/C4/C6`
- 再继续大幅做体验减法

### 冲突 2：做更多视觉花样 vs 契约和页系还没稳定

表现：

- 如果先大量做漂亮样式
- 但页面契约和页系样张还没成为稳定输入
- 那只会生成“偶尔很漂亮，整体仍不稳”

结论：

- 必须先做契约与页系骨架
- 再做视觉高级感

### 冲突 3：继续堆页面类型 vs 比赛逻辑底座还没统一

表现：

- 如果先扩更多页型
- 但底层评分逻辑仍夹杂商业 BP 语义
- 就会生成越来越多“看起来丰富，但比赛导向不纯”的页

结论：

- 必须先完成 `B1/B2/B3/B6`
- 再继续扩内容类型

### 冲突 4：继续做单页修复体验 vs repair 验收标准还不完整

表现：

- 如果前端继续丰富修页入口
- 但后端还不能稳定判断“这页像不像真正比赛页”
- 会出现“修了很多次但还是普通 HTML 味”

结论：

- 必须先强化 `C6`
- 再持续扩修页动作

## 6.2 不冲突、可以并行推进的部分

以下可以并行：

1. 页面契约 / 页系样张 / 单页重设计协议
2. 评分底座比赛原生化
3. 后端真相源收口
4. 前端继续把主路径回收到当前页

因为它们分别解决：
- 生成什么
- 什么算达标
- 系统怎么稳定判断
- 用户怎么操作

这四件事天然互补，不冲突。

---

## 7. 总体解决方案

## 7.1 第一阶段总目标

第一阶段不是“做更多功能”，而是要完成下面这件事：

> 让系统稳定产出“更像比赛级 PPT 的页面”，并且后端/前端对“当前是否达标”的判断一致。

### 第一阶段要解决的问题范围

- A1/A2/A3/A5
- B1/B2/B3/B6
- C1/C2/C3/C4/C6

## 7.2 第二阶段总目标

在第一阶段稳定后，再继续做：

> 让整套稿子不仅达标，而且更有镜头感、更有高级感、更省用户精力。

对应范围：

- A4/A6
- B4/B5
- C5/C7/C8/C10
- D1/D2/D3/D4/D6

## 7.3 第三阶段总目标

> 把系统从“可用且不错”推进到“长期稳定、容易维护、适合持续演进”。

对应范围：

- C9
- D5
- 更完整的自动验收和运维治理

---

## 8. 具体到文件和模块的整改任务表

下面按模块列出后续整改任务。

---

## 8.1 编导与页面设计专项

### 模块 1：页面契约与页系样张

**目标**
- 让页面真正按比赛页类型生成

**文件**
- [page_contracts.py](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/page_contracts.py)
- [round2_narrative.md](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/prompts/round2_narrative.md)
- [round3_enrich.md](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/prompts/round3_enrich.md)
- [round4_html_generation_optimized.md](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/prompts/round4_html_generation_optimized.md)
- [html_generator.py](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/html_generator.py)

**任务**
1. 补全第一批页系契约：
   - evidence_board
   - practice_evidence
   - architecture_system
   - value_matrix
   - closing_board
2. 契约定义 `required_blocks / forbidden_blocks / visual_rules / layout_slots`
3. 主生成器按 `page_series_type + layout_slots` 选骨架
4. Round 3 enriched page 输出 `page_template_contract`

**验收**
- 同一页系下不同 `layout_slots` 页面不再长得一样
- 技术页、实操页、价值页不再统一掉回普通卡片页

---

### 模块 2：视觉审查与单页重设计

**文件**
- [vision_judge_service.py](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/vision_judge_service.py)
- [ppt_service.py](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/ppt_service.py)

**任务**
1. 强化契约型视觉问题：
   - contract_mismatch
   - series_language_missing
   - visual_role_not_realized
2. 强化候选页 accept/reject：
   - 缺块位不允许采用
   - 内部设计词泄露不允许采用
3. repair 继续按根因分流：
   - html
   - structure_rebuild
   - evidence

**验收**
- 候选页不会因为“只是合法 HTML”就误采用
- 当前页、质量卡、下载条件、总审对契约问题口径一致

---

## 8.2 产品 / 比赛逻辑专项

### 模块 3：评分底座与比赛语言统一

**文件**
- [ppt_service.py](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/ppt_service.py)
- [scoring_checker.py](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/scoring_checker.py)
- [round2_narrative.md](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/prompts/round2_narrative.md)
- [round3_enrich.md](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/prompts/round3_enrich.md)

**任务**
1. 必备评分点优先切换为技能大赛维度
2. 商业 BP 语义降级为补充项
3. 页面显式声明：
   - served_scoring_dimensions
   - score_evidence_blocks
4. 一键补评分点不再只补文案，要补：
   - 页面职责
   - 证据位
   - 结构块位

**验收**
- 同任务不会再优先提示“融资需求”而弱化“操作规范性/实操能力”
- 评分覆盖率变化稳定、可解释

---

### 模块 4：比赛节奏与实操观测点

**文件**
- [page_contracts.py](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/page_contracts.py)
- [ppt_service.py](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/ppt_service.py)
- [pipeline_coordinator.py](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/adapter_code/pipeline_coordinator.py)

**任务**
1. 把四幕式比赛叙事继续内化为章节配额与顺序规则
2. 对背景页、技术页、实操页、价值页设置上限/下限
3. 实操页必须有：
   - 输入
   - 操作
   - 输出
   - 证据
4. 区分：
   - 可下载预演版
   - 比赛终稿版

**验收**
- 实操页不再只有流程说明
- 生成结果中段一定能看到技术与实操主体

---

## 8.3 后端收口专项

### 模块 5：唯一当前态与读写边界

**文件**
- [ppt_service.py](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/ppt_service.py)
- [ppt_router.py](/Users/liuyixing/项目/OREP/ai-scoring/app/routers/ppt_router.py)

**任务**
1. 定义 canonical source：
   - task
   - html_page
   - quality
   - scoring
   - deliverability
2. 收读接口副作用：
   - 读时不再顺手修页/写快照/重算大对象
3. deliverability 保持唯一聚合口径
4. history-detail 改成稳定聚合视图

**验收**
- 同一任务刷新两次，不应出现莫名状态漂移
- 前端与下载接口对 blocked/warning/ready 判断一致

---

### 模块 6：评分覆盖与素材绑定结构化

**文件**
- [ppt_service.py](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/ppt_service.py)
- [scoring_checker.py](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/scoring_checker.py)

**任务**
1. 评分覆盖优先消费结构化声明，不再主要依赖关键词
2. 素材绑定增加 confirmed binding 层
3. 素材上传、页面缺图、质量检查三处统一认同一套绑定事实

**验收**
- “传了图还是提示缺图”这类问题不再反复出现
- 一键补评分点后，分数变化稳定可解释

---

## 8.4 前端主路径专项

### 模块 7：当前页主工作台继续减法

**文件**
- [PptHistoryDetail.vue](/Users/liuyixing/项目/OREP/frontend/user/src/views/PptHistoryDetail.vue)
- [PptHtmlWorkbench.vue](/Users/liuyixing/项目/OREP/frontend/user/src/components/ppt/PptHtmlWorkbench.vue)
- [usePptCurrentPageWorkspace.js](/Users/liuyixing/项目/OREP/frontend/user/src/composables/usePptCurrentPageWorkspace.js)

**任务**
1. 当前页主动作继续保持唯一优先动作
2. 补图/修页/补评分点更多在当前页内完成
3. 契约型问题主动作统一为 `重做契约页`
4. 候选页未过契约门的反馈留在当前页

**验收**
- 用户尽量不用跨 tab 才能完成主修复链

---

### 模块 8：下载条件与总审继续当前页化

**文件**
- [PptDownloadReadinessCard.vue](/Users/liuyixing/项目/OREP/frontend/user/src/components/ppt/PptDownloadReadinessCard.vue)
- [usePptDownloadReadiness.js](/Users/liuyixing/项目/OREP/frontend/user/src/composables/usePptDownloadReadiness.js)
- [PptHistoryDetail.vue](/Users/liuyixing/项目/OREP/frontend/user/src/views/PptHistoryDetail.vue)

**任务**
1. 下载条件继续保持：
   - blocked / warning / ready
   的人话口径统一
2. 当前版下载与继续补强并行引导
3. 契约型问题纳入下载条件正式项
4. 总审与下载条件、质量报告保持同口径

**验收**
- 用户知道现在是：
   - 不能下载
   - 可以下载当前版
   - 可以下载终稿

---

## 9. 建议实施顺序

建议不要并行乱做，按下面顺序推进：

### 第一批：必须先做

1. 页面契约 + 页系样张稳定进主生成器 / rebuild / fallback
2. 评分底座比赛原生化
3. 后端当前真相源与读写边界收口
4. deterministic validator 补强

### 第二批：在第一批稳定后继续

5. 素材绑定 confirmed layer
6. 实操页、团队页、安全页、创新页、价值页比赛化强化
7. 前端当前页工作台继续减法
8. 下载条件和总审继续人话化、自动化

### 第三批：稳定化与长期治理

9. `history-detail` 聚合瘦身
10. `ppt_service.py` 深度拆域
11. 更强自动回归与性能治理

---

## 10. 最终结论

这次 team 评审之后，最重要的判断是：

### 不是所有问题都要一起修

当前真正必须先处理的是：

1. 让页面更像比赛级 PPT
2. 让比赛逻辑真正成为底座
3. 让系统当前真相源收口

如果这三件事不先做：

- 前端再怎么优化，用户也会遇到“做了但不生效”
- 页面再怎么修饰，最终成品也可能只是更稳定的普通 HTML
- 下载链路再怎么解释，也难以让用户相信系统真的可靠

### 因此，最正确的下一阶段主线是

> 先继续收“编导与页面设计 + 比赛逻辑 + 后端真相源”，再继续把前端变得更轻、更顺手。

