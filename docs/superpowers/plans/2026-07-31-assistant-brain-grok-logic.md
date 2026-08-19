# 竞赛助手 Brain：把 Grok 式逻辑融进竞赛大脑

> 日期：2026-07-31  
> 状态：Phase 1 已落地（规则 Brain + 契约注入 + 产物清洗）

## 1. Grok / 通用智能助手可工程化的 6 条

| # | 逻辑 | 工程含义 | OREP 落地 |
|---|------|----------|-----------|
| 1 | Understand-before-act | 先结构化目标，再选工具与回答形态 | `brain.plan_turn` → `BrainPlan` |
| 2 | Multi-turn slots | 「这个/报告/继续」从历史补全 | `REF_LAST` + 历史 blob 合并 |
| 3 | Mode routing | 同一模型，不同 goal 换契约 | `system_addendum` 分 goal |
| 4 | Tool gating | 评分/重解析等贵工具按需开 | `need_scores` / `need_rag` |
| 5 | Dual channel | 聊天叙述 ≠ 可下载产物 | `need_doc_gen` + `prepare_artifact_markdown` |
| 6 | Answer-first + assumptions | 残句先给可用框架并标明假设 | `goal=clarify` + assumptions |

## 2. 流水线（当前）

```text
用户消息 + 最近 messages
        │
        ▼
  brain.plan_turn  ──► goal / artifact / tools / assumptions / system_addendum
        │
        ├─ need_scores → 拉评分摘要
        ├─ need_rag    → 注入资料
        ▼
  MiMo stream（system = 通用原则 + Brain 契约 + 工具结果）
        │
        ├─ 聊天 content_delta（给人看）
        └─ need_doc_gen → 清洗 Markdown → 按 artifact 渲染 md/docx/pptx/xlsx/pdf
```

## 3. goal 一览

| goal | 触发示例 | 行为 |
|------|----------|------|
| `answer` | 一般提问、要提纲 | 对话；提纲不强制导出 |
| `rewrite` | 润色/改开场 | 改稿契约 |
| `plan` | 训练计划 | 可执行条目 |
| `score_review` | 根据评分完善… | 开评分工具 + 复盘契约 |
| `artifact` | 生成 ppt / 导出 excel | 成片契约 + 文件通道 |
| `clarify` | 「生成一份智慧农业的」 | 先框架 + 假设 + 一句澄清 |

## 4. Phase 状态

| Phase | 内容 | 状态 |
|-------|------|------|
| P1 | Brain 结构化意图 + 契约 + 产物清洗 | ✅ |
| P2 | 产物 JSON 二段生成 + schema 渲染 | ✅ |
| P2b | 轻量 LLM 意图分类（规则冲突/残句时） | ✅ |
| P3 | 会话级 slot 持久化（context_json） | ✅ |
| P3b | 接 OREP 精美 PPT pipeline | 未做 |

### P2 细节

```text
聊天回答（stream）
   → generate_artifact_schema（二次 LLM，temperature=0.2）
   → deck | plan | doc JSON
   → 失败则 markdown_fallback
   → deck_schema_to_pptx_bytes / plan_schema_to_xlsx_bytes / doc_schema_to_docx_bytes
   → 同时产出 .md 真源 + .json 结构（可再编辑）
```

## 5. 关键文件

- `ai-scoring/app/services/assistant/brain.py`
- `ai-scoring/app/services/assistant/artifact_schema.py`  ← P2
- `ai-scoring/app/services/assistant/intent.py`（兼容层）
- `ai-scoring/app/services/assistant/orchestrator.py`
- `ai-scoring/app/services/assistant/doc_generate.py`
