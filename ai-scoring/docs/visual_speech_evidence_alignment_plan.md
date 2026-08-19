# 音画证据对齐与「未展示 IDE」冲突修复 — 开发方案

> 状态：**已完成 + skill 局部重评（2026-08-12）**  
> 范围：`ai-scoring` 评分链路 + PDF 报告（对外不暴露抽帧机密）

---

## 0. 问题陈述

### 现象
- 本场（session 40）视频画面中有 VS Code / 代码编辑器。
- 视觉分析 `screen_type_distribution` 显示「代码编辑器」21 帧，「代码展示」等 content 有计数；`code_detections` 长度约 29。
- 评分结果 `critical_issues` / `final_verdict.critical_deductions` 仍写「全程未展示 IDE、调试工具…」。

### 根因（对照现网代码）

| # | 根因 | 代码位置 | 说明 |
|---|------|----------|------|
| R1 | 视觉证据注入条件过窄 | `llm_scoring_service.score_roadshow`：仅 `ppt_recognition=True` 时 `_format_visual_evidence` | 部分路径即使有 `screen_content_summary` 也不注入 |
| R2 | 视觉证据格式偏「列表」，缺硬约束 | `_format_visual_evidence` | 有 code_detections 时也未写「禁止写完全未展示 IDE」 |
| R3 | 无评分后消歧 | `_parse_and_validate` / `_backfill_*` | 类似时长口径有 `_sanitize_competition_duration`，**没有** IDE 画面口径消毒 |
| R4 | 证据审计可与画面矛盾 | LLM `evidence_audit` | O02 可写「缺少 IDE 界面」即使视觉已检出 |
| R5 | PDF 曾展示抽帧机密 | `report_service`（已撤回） | 对外报告不得出现抽帧数/内部识别过程 |

### 原则
1. **对外 PDF**：只出评审结论与可执行建议，不出现抽帧数、观测内部字段、识别管道描述。  
2. **对内评分**：必须用音画融合证据包约束措辞；冲突时**先改文案**，分数可选局部重评（本期不做全量重评）。  
3. **可回归**：单元测试覆盖「有代码编辑器画面 + 文案写未展示 IDE → 必须改写」。

---

## 1. 目标

### 功能目标
1. 构建内部 `VisualDevToolFacts`（不写 PDF）。  
2. 评分 prompt 注入强化后的视觉证据 + **硬约束条款**。  
3. 评分结果落库前 **确定性消毒**：禁止与画面冲突的绝对否定句。  
4. 证据审计条目中同类冲突一并改写。  
5. PDF 生成路径对**历史 result** 也走同一消毒（无需立刻重跑 LLM）。  
6. 保持：无抽帧机密进 PDF；关注维度中文；评审团挂载逻辑不变。

### 非目标（本期不做）
- 全量重跑 session 40 LLM。  
- 教师端内部「质检页」UI。  
- 修改前端。  

### 补充：skill_level 局部重评（确定性）
- 触发：`has_dev_tool_ui` 且 skill 偏低（或文案按「无工具」叙事扣分）。  
- 加分信用：代码编辑器 +7 / 终端 +5 / 仅代码内容 +4。  
- 上限：`max_score * 0.58`（60 → 34.8），只升不降。  
- 有 items 时按权重分到熟练度/规范性等；无 items 时直接抬维度分。  
- 总分按 skill 增量回写；写 `_skill_visual_rescore` 内部元数据（PDF 不展示）。

---

## 2. 设计

### 2.1 模块：`app/services/evidence_alignment_service.py`

```text
build_visual_dev_tool_facts(result|fusion|video_analysis) -> VisualDevToolFacts
format_visual_constraints_for_prompt(facts) -> str   # 注入 prompt，可含内部统计
sanitize_scoring_text(text, facts) -> str
sanitize_ai_score_payload(ai_score, facts) -> ai_score
sanitize_result_for_report(result) -> result  # 深拷贝消毒，不改磁盘除非调用方写入
```

**VisualDevToolFacts（内部）**
- `has_code_editor_ui: bool`  — screen_type 含「代码编辑器」或等价  
- `has_terminal_ui: bool`  
- `has_code_content: bool` — content_types 含代码展示 / has_code / code_detections  
- `has_dev_tool_ui: bool` — 以上任一  
- `editor_count / terminal_count / code_detection_count` — 仅内部与 prompt，**禁止写 PDF**  
- `sample_timestamps: list[float]` — 少量时间点给 LLM  

**绝对否定句模式（消毒触发）**  
匹配类似：
- 全程未展示 / 完全未展示 / 未展示任何 + (IDE|开发者工具|调试工具|代码编辑|vscode)  
- 缺少 IDE 界面截图且表述为「完全无」  

**改写策略（确定性，不调 LLM）**  
- 若 `has_dev_tool_ui`：  
  - 将「全程/完全未展示 IDE/开发者工具」  
  - 改为：「虽出现代码/终端类界面，但未充分演示调试、配置修改或异常处理等工程操作，技能深度仍不足。」  
- 保留其余非冲突分句。  
- 不追加「抽帧 N 帧」等机密措辞。

### 2.2 Prompt 注入

修改 `llm_scoring_service._format_visual_evidence`：
1. 始终输出 `screen_type_distribution` Top 项（内部 prompt 可用）。  
2. 若 `has_dev_tool_ui`，追加 **硬约束** 段落（禁止绝对否定）。  
3. `score_roadshow`：只要 `fusion_context` 含 `screen_content_summary` 或 video per_frame 可建 facts，**即注入** visual_evidence（不再仅依赖 `ppt_recognition`）。  
   - 模拟风险：纯摄像头无屏幕时 summary 为空 → 不注入，OK。  
   - 仅摄像头误标 screen_type 极少，可接受。

### 2.3 评分后与报告前

- `score_roadshow` 在拼装 `ai_score` 返回前调用 `sanitize_ai_score_payload`。  
- `generate_report` 入口对 `result['ai_score']` 调用 `sanitize_result_for_report`（历史数据自愈）。  
- **不**把 facts 写入 result JSON 对外字段；可选写入 `result['_internal_visual_facts']` 仅调试且默认关闭。

### 2.4 fusion 侧小增强（可选但稳）

`fusion_service`：`screen_type == '代码编辑器'` 或 content 含「代码展示」时，即使 `has_code` 假，也并入 `code_detections`。  
降低 R2 上游漏检。

---

## 3. 模拟走查（假设合入后）

| 场景 | 预期 | 风险与处理 |
|------|------|------------|
| session 40 只重生 PDF | generate_report 消毒 → 结论不再写「完全未展示 IDE」 | 分数仍 36.8；可接受（本期） |
| 新评分 + 有代码编辑器 | prompt 有约束 + 出口消毒 | 双重保险 |
| 真无 IDE 画面 | facts.has_dev_tool_ui=False → 允许「未展示 IDE」 | 正则勿过宽 |
| 只有终端无编辑器 | has_terminal_ui → 同样禁止「未展示任何开发者工具」 | 改写句覆盖终端 |
| 纯音频无 fusion | facts 空 → 行为与现网一致 | OK |
| PDF 文案 | 无「抽帧」「N 帧识别」 | 测试 grep |
| 性能 | 消毒 O(文本量) 毫秒级 | OK |
| 并发 | 纯函数无全局状态 | OK |

### 模拟发现问题 → 方案修正

1. **问题**：`_format_visual_evidence` 若打印「21 帧」会进 LLM 上下文，可能泄漏到学生可见的 reason。  
   **优化**：prompt 内可用「多处/多次出现」代替精确帧数；或精确帧数仅用于约束段且消毒时 strip「抽帧\d+帧」。  
2. **问题**：改写后 `critical_issues` 与 `dimensions.skill_level` reason 仍旧。  
   **优化**：`sanitize_ai_score_payload` 递归处理 dict/list 字符串字段（白名单字段名）。  
3. **问题**：报告生成修改内存 result 可能污染调用方。  
   **优化**：`sanitize_result_for_report` 深拷贝。  

---

## 4. 任务清单与状态

| ID | 任务 | 状态 |
|----|------|------|
| T0 | 本方案文档 + 模拟走查 | ✅ 完成 |
| T1 | 实现 `evidence_alignment_service.py` + 单测 | ✅ 完成（8 tests OK） |
| T2 | 增强 `_format_visual_evidence` + 注入条件 | ✅ 完成（有 screen_summary 即注入 + 硬约束） |
| T3 | `score_roadshow` 出口消毒 | ✅ 完成（`_sanitize_visual_speech_alignment`） |
| T4 | `generate_report` 入口消毒（历史 PDF） | ✅ 完成（`sanitize_result_for_report`） |
| T5 | fusion `code_detections` 覆盖代码编辑器类型 | ✅ 完成 |
| T6 | 单测全绿 + 重生 session 40 PDF 抽检无泄密/无冲突绝对句 | ✅ 完成 |
| T7 | skill_level 画面局部重评（分数随工具可见性校正） | ✅ 完成 |

### 验收记录（session 40）

- 本地 `unittest tests.test_evidence_alignment_service`：**12/12 OK**（含 skill 重评）
- 生产热补丁后重生 PDF：`/Users/liuyixing/Downloads/SC-20260812091431414-rescored.pdf`
- PDF grep：`抽帧|画面识别提示|全程未展示IDE|36.8` → **0**
- 关键扣分：由「全程未展示 IDE…」→「虽出现代码/终端类界面，但未充分演示调试、配置修改或异常处理…」
- 分数（局部重评，不重跑 LLM）：skill **27→34**（+7 编辑器信用，帽 34.8）；overall **36.8→43.8**
- 叙述同步：诊断/结论中的 27/60、36.8 已改为 34/60、43.8；评审团章 AI 基准与分差按新分重算（+10.2）

---

## 5. 测试计划

1. 单元测试：  
   - facts 从 screen_type_distribution 构建  
   - 冲突句改写  
   - 无画面不改写  
   - 递归消毒 critical_issues / final_verdict  
2. PDF：`grep` 无 抽帧|画面识别提示|代码编辑器约  
3. PDF/消毒后 JSON 文案：无「全程未展示任何IDE」类句（当 facts 为真时）  

---

## 6. 回滚

- 删除/关闭 `sanitize_*` 调用即可回退文案行为。  
- prompt 增强向后兼容。  

---

## 7. 后续（不在本期勾选）

- 教师内质检页  
- 冲突率监控埋点  
- 可选：将校正后分数写回 `result_*.json` 持久化（当前报告生成时内存校正即可） 
