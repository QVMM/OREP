# OREP AI 生成 PPT 式 HTML

## 后端收口实施文档

> 目标：把当前后端从“多套派生状态并行叠加”收口成“唯一当前态 + 清晰派生层 + 稳定交付层”，优先解决：
>
> - 传了图仍然提示缺图
> - 补了评分点但分数不涨
> - 下载门禁前后不一致
> - 单页修复反复空转
> - 草稿态/终稿态约束互相打架

---

## 1. 本文档解决的核心问题

当前后端的主要问题不是某一个 API 写错了，而是：

1. **没有唯一当前真相**
   - `ppt_task`
   - `ppt_generation_snapshot`
   - `ppt_html_page`
   - `ppt_page_quality_report`
   - `ppt_scoring_coverage`
   - `ppt_material_asset`
   - `deliverability`
   都在表达“当前状态”，但口径不统一

2. **推荐绑定被当成事实绑定**
   - `recommended_page_bindings` 当前在很多地方被直接当成“已绑定”

3. **评分规则赛事化不彻底**
   - 默认规则仍带商业 BP 偏向

4. **修复系统没有真正按根因分流**
   - 证据问题、结构问题、HTML 问题经常被混成“再修一页”

5. **Prompt 约束缺少草稿态 / 终稿态分层**
   - 前面允许 `[待补充]`
   - 后面又把它当硬伤

---

## 2. 收口后的目标架构

后端应清晰分成 3 层：

### 2.1 事实层

只存“当前被系统承认的真实状态”：

- 当前任务：`ppt_task`
- 当前大纲：`ppt_task.outline_json`
- 当前页面：`ppt_html_page`
- 当前显式素材绑定：`ppt_material_asset.confirmed_page_bindings`

### 2.2 派生层

基于当前事实重算或持久化：

- 质量报告：`ppt_page_quality_report`
- 评分覆盖：`ppt_scoring_coverage`
- 实操模块：`ppt_practice_demo_step`
- 路演结构 / 健康：快照或派生结构

### 2.3 决策层

只做最终判断：

- 当前推荐动作
- 下载条件
- 交付门禁
- warning / ready / blocked

---

## 3. 第一批必须执行的改造

## 3.1 建立“唯一当前态聚合层”

### 目标

所有前端详情页、下载判断、总审、质量页，都从同一入口拿“当前状态”。

### 重点文件

- [ppt_service.py](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/ppt_service.py)
- [ppt_router.py](/Users/liuyixing/项目/OREP/ai-scoring/app/routers/ppt_router.py)

### 实施动作

1. 新建统一聚合方法，例如：
   - `build_current_task_state(task_id)`
2. 这个方法只做 3 件事：
   - 读取当前事实层
   - 触发或读取当前派生层
   - 组装当前决策层
3. 后续这些接口统一只读该聚合结果：
   - `GET /api/ppt/task/{id}`
   - `GET /api/ppt/task/{id}/history-detail`
   - `GET /api/ppt/task/{id}/download`
   - `GET /api/ppt/task/{id}/quality-summary`
   - `GET /api/ppt/task/{id}/roadshow-health`

### 验收标准

- 同一个任务在：
  - 下载条件卡
  - 总审
  - 下载接口
  - 历史详情
  里看到的 `deliverability` 一致

---

## 3.2 素材绑定改成双层模型

### 目标

把“推荐绑定”和“事实绑定”分开，彻底解决“传了图还说缺图”。

### 当前问题

很多逻辑直接读：

- `recommended_page_bindings`

这会导致：

- 推荐错了就等于显示错了
- 已上传但未确认的图被当成已绑定

### 数据结构调整

为 `ppt_material_asset` 增加：

- `recommended_page_bindings`
- `confirmed_page_bindings`

如果已有字段，可明确语义区分，不一定必须新表。

### 重点文件

- [ppt_service.py](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/ppt_service.py)

### 实施动作

1. 推荐逻辑继续生成 `recommended_page_bindings`
2. 所有页面显示、缺图判断、质量门禁，只认：
   - `confirmed_page_bindings`
3. 上传后允许：
   - 系统自动确认当前页预填上传
   - 或用户手动确认绑定页

### 验收标准

- 第 N 页上传图片后，不会再因为其他页推荐绑定漂移而误显示
- 缺图提醒与当前页确认绑定严格一致

---

## 3.3 评分覆盖改成赛事优先规则

### 目标

让评分系统默认服务“职业院校技能大赛”，不是普通商业路演。

### 当前问题

- `scoring_checker.py` 仍带商业 BP 倾向
- 市场、融资、财务类项被默认当必备主项
- 与比赛核心项优先级不一致

### 重点文件

- [scoring_checker.py](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/scoring_checker.py)
- [scoring_rules_v2.py](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/scoring_rules_v2.py)

### 实施动作

1. 定义“赛项模板优先”的评分集
2. 区分：
   - 必备比赛项
   - 建议商业补充项
3. `required_coverage_rate` 只按比赛必备项计算
4. 一键补评分点时优先补：
   - 技术先进性
   - 技能水平
   - 实操规范
   - 应用价值
   - 团队协作
   - 创新成效

### 验收标准

- 评分覆盖报告中，比赛必备项与补充项显示分层
- warning / ready 判断优先看比赛项，不被商业项拖死

---

## 3.4 修复系统改成根因分流 + 熔断

### 目标

不再让所有问题都走“继续修一页 HTML”。

### 根因分三类

1. `html_polish`
   - 版式、留白、重叠、字体、视觉焦点
2. `structure_rebuild`
   - 模板化、叙事错位、评分点弱、章节失配
3. `evidence_attach_or_wait`
   - 缺图、缺政策证据、缺实操素材

### 重点文件

- [ppt_service.py](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/ppt_service.py)

### 实施动作

1. 在 `repair_html_page()` 前先做根因分类
2. 不同根因走不同 handler
3. 增加熔断规则：
   - 连续 2 次收益不足 -> 自动切策略
   - 连续 3 次同路径失败 -> 停止继续修，给回滚/托底/补证据入口

### 验收标准

- 不再出现同一页修五六次还走同一路线
- 证据问题不会反复当布局问题修

---

## 3.5 Prompt 改成草稿态 / 终稿态两套约束

### 目标

解决：

- Round 1/3 允许 `[待补充]`
- Round 4/交付门禁又把它视为致命硬伤

### 重点文件

- [round1_structurize.md](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/prompts/round1_structurize.md)
- [round2_narrative.md](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/prompts/round2_narrative.md)
- [round3_enrich.md](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/prompts/round3_enrich.md)
- [round4_html_generation_optimized.md](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/prompts/round4_html_generation_optimized.md)

### 实施动作

1. Round 1 / 2：
   - 允许缺失项显式标注
2. Round 3：
   - 允许“建议补证据”进入元数据
   - 不允许直接进入终稿正文
3. Round 4：
   - 禁止 `[待补充] / [待核实] / 建议上传` 进入正式页面主体

### 验收标准

- 草稿信息不会再污染终稿门禁
- 页面质量不再被系统自己注入的占位语言误伤

---

## 4. 第二批改造

## 4.1 统一 LLM 错误语义

### 目标

让上游明确区分：

- 空响应
- JSON 解析失败
- 网络错误
- 超时
- 拒答

### 重点文件

- [qwen_client.py](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/qwen_client.py)
- [llm_factory.py](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/llm_factory.py)

### 建议返回结构

```json
{
  "ok": false,
  "error_type": "empty_response|json_parse|network|timeout|model_refusal",
  "retryable": true,
  "raw_text": "..."
}
```

## 4.2 质量检查分层

把当前大一统质量报告拆成：

- `layout_checks`
- `content_checks`
- `evidence_checks`
- `competition_checks`
- `delivery_checks`

这样修复系统才能按层分流。

---

## 5. API 与数据契约补充

## 5.1 建议补充的统一接口结果

### 当前任务聚合详情

`GET /api/ppt/task/{id}/current-state`

建议返回：

- current task
- current outline
- current html pages
- current quality summary
- current scoring summary
- current materials by page
- current deliverability
- current next recommended action

## 5.2 素材绑定确认接口

`POST /api/ppt/task/{id}/materials/{asset_id}/confirm-binding`

请求：

```json
{
  "page_indices": [26, 27]
}
```

## 5.3 修复根因分类返回

单页修复预览建议返回：

- `root_cause_type`
- `strategy_used`
- `history_recommendation`
- `gain_assessment`

---

## 6. 实施优先级

### 第一优先级

1. 唯一当前态聚合层
2. confirmed material binding
3. scoring checker 赛事优先化
4. deliverability 硬阻塞 / 软建议分层

### 第二优先级

5. repair 根因分流 + 熔断
6. Prompt 草稿态 / 终稿态分层
7. 质量检查分层

### 第三优先级

8. LLM 错误契约统一
9. API 数据结构补齐

---

## 7. 开工建议

如果马上开干，我建议按这个顺序：

1. 先改 `scoring_checker.py` 和 `scoring_rules_v2.py`
2. 再改 `ppt_material_asset` 绑定语义
3. 再做 `build_current_task_state()` 聚合层
4. 最后收 `repair` 根因分流

原因是：

- 评分规则和素材绑定会直接影响用户当前最痛的“补了没生效”
- 当前态聚合层决定前端状态是否可信
- repair 分流要建立在前两者收口后才更稳
