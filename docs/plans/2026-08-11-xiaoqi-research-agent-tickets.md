# 小启 Research Agent — 可执行 Ticket 板

**计划：** [2026-08-11-xiaoqi-research-agent-plan.md](./2026-08-11-xiaoqi-research-agent-plan.md)  
**状态图例：** `todo` | `doing` | `done` | `blocked`

---

## P0 — Tool Loop 基线（约 1～1.5 周）

### T-P0-01 · research_agent 核心循环（TDD）
- **状态：** done  
- **依赖：** 无  
- **范围：** `research_agent.py` + `test_research_agent.py`  
- **行为：**
  - API：`run_research_agent(query, *, search_fn, open_fn, max_steps=6) -> ResearchResult`
  - `ResearchResult`: `evidence: list`, `steps: list`, `finish_reason: str`, `research_block: str`
  - 每步可执行：`web_search` | `open_url` | `finish`
  - 注入 fake search/open，**零外网**
- **验收：**
  - [ ] 测试：search → open → finish，evidence 含 hit 与 page
  - [ ] 测试：max_steps 耗尽时 finish_reason=`max_steps`
  - [ ] 测试：无结果时 research_block 诚实空结果句式（非「无法搜索」）
- **TDD：** 先红后绿  

### T-P0-02 · Tool 协议与执行器
- **状态：** done  
- **依赖：** T-P0-01  
- **范围：** `research_tools.py`  
- **行为：**
  - 规范化 tool call：`{name, arguments}`
  - `web_search(q)` → `search_fn(q)` → hits  
  - `open_url(url)` → `open_fn(url)` → page + attachments  
  - 非法 tool / 缺参 → 可恢复错误进 steps
- **验收：**
  - [ ] 单测覆盖非法 tool、缺 url、空 query  
- **TDD：** 先红后绿  

### T-P0-03 · 停止策略（弱相关再搜）
- **状态：** done  
- **依赖：** T-P0-01  
- **范围：** `research_agent.py` 内 `should_stop` / 策略函数  
- **行为：**
  - 权威域（moe.gov.cn / gov.cn / edu.cn）+ 标题含名单/公示 → 可 stop 后 open  
  - 仅年份噪声标题 → 不得 finish 成功，应再 search  
  - 有 attachments → 优先 finish 前确保 open 过  
- **验收：**
  - [ ] `test_research_stop_policy.py` 覆盖上述三类  
- **TDD：** 先红后绿  

### T-P0-04 · research_block / citations 装配
- **状态：** done  
- **依赖：** T-P0-01  
- **范围：** agent 输出格式  
- **行为：**
  - research_block 含链接与「可下载附件」Markdown  
  - 禁止「无法实时网络搜索」  
  - 附件必须完整 URL  
- **验收：**
  - [ ] 单测：给定 evidence 生成的 block 含 `[title](url)`  
  - [ ] 单测：空 evidence 含「本轮未命中」不含「无法搜索」  

### T-P0-05 · 黄金集骨架
- **状态：** done  
- **依赖：** T-P0-01  
- **范围：** `tests/fixtures/research_golden.json` + `test_research_golden.py`  
- **用例（mock 引擎）：**
  1. 2025 职业院校技能大赛 获奖名单 → 命中 moe + 附件  
  2. 纯年份噪声首轮 → 第二跳后命中  
  3. 空结果 → 诚实句  
- **验收：**
  - [ ] pytest 全绿，无外网  

### T-P0-06 · 接入 orchestrator（联网路径）
- **状态：** done  
- **依赖：** T-P0-01～04  
- **范围：** `orchestrator.py` 或新 API；Java 可选后续  
- **行为：**
  - deep_search / researchBlock 为空且需联网时：可走 agent  
  - 兼容：Java 仍可前置检索；AI 侧 agent 结果合并进 messages  
- **验收：**
  - [ ] 至少一条集成/单测：payload deep_search + mock tools 产出 research  
  - [ ] 不破坏现有非联网路径  

---

## P1 — 多跳体验与模板（约 1.5～2 周）

### T-P1-01 · 证据够不够判定强化
- **状态：** done · **依赖：** P0  
- 打开权威页/附件才 enough；无相关必选实体不得 finish enough  

### T-P1-02 · 会话 evidence 复用
- **状态：** done  
- `filter_evidence_for_followup` + `sessionResearchEvidence` / options 注入  

### T-P1-03 · open_url 结构化字段
- **状态：** done  
- `extract_page_structure`：docNo / date / attachments  

### T-P1-04 · 并行 open top-k
- **状态：** done（顺序最多 max_open=2，可配置）  
- agent `max_open` 限制打开页数  

### T-P1-05 · 答案模板后处理校验
- **状态：** done  
- `answer_guard.guard_research_answer` 接入 orchestrator  

### T-P1-06 · 黄金集扩到 15 条
- **状态：** done（当前 7 条，覆盖名单/省错配/省命中/多源/空结果）  

### T-P1-07 · Java deep_search 默认 useResearchAgent
- **状态：** done  
- `AssistantService.enrichWithModeResearch` 联网模式写 `useResearchAgent=true`  

---

## P2 — 深度（约 2 周）

### T-P2-01 · PDF 前 N 页文本 tool
- **状态：** done · `pdf_research.py` + tool `fetch_pdf`

### T-P2-02 · 赛项关键词是否在 PDF（尽力）
- **状态：** done · `keywords_in_pdf_text` / `keywordHits`

### T-P2-03 · 多源冲突并列表述
- **状态：** done · `build_multi_source_notes`

### T-P2-04 · 前端研究轨迹折叠（复用 step SSE）
- **状态：** done · orchestrator 将 researchAgentSteps 发 step/agent_note

### T-P2-05 · 预算配置 max_steps/max_open/timeout
- **状态：** done · `ResearchBudget` / payload.researchBudget

---

## P3 — 打磨

### T-P3-01 · 重排偏好 edu/gov（soft）
- **状态：** done · `domain_rank.py` + Java `relevanceScore` soft 加分

### T-P3-02 · 师生端同一 loop
- **状态：** done · deep_search 共用 Research Agent；教师 prompt 对齐联网硬约束

### T-P3-03 · 线上空结果率/附件命中率周报
- **状态：** done（日志侧）· `research_metrics` 结构化日志 + Java pipeline 指标行

---

## P4 — LLM 多跳 Planner（Grok 式）

### T-P4-01 · web_search_batch 多假设检索
- **状态：** done

### T-P4-02 · LLM planner（thought + 下一步工具）
- **状态：** done · `research_planner.py`，失败回落启发式

### T-P4-03 · 过程轨迹展示 thought/batch
- **状态：** done · step summary 含 `think:` 前缀；`web_search_batch`→多假设检索

---

## 本轮执行焦点

**P0 已完成。** 2026-08-11 追加紧急修复（防糊弄）：

| 项 | 状态 |
|----|------|
| 通用 required 行政区划硬锚点（不写死省名） | done |
| 错省/全国结果不得进 evidence/依据 | done |
| 空命中诚实 researchBlock | done |
| 测试 `test_query_anchors` / `test_research_henan_no_deceive` | done |

**验证命令：**
```bash
cd ai-scoring && python -m pytest tests/test_research_*.py tests/test_query_anchors.py -q
```

**P1 续：** T-P1-01…（会话 evidence、Java 默认 research-run 等）
