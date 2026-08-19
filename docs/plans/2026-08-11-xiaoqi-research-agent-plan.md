# 小启 Research Agent：对齐 Grok Build 式联网（不含换引擎）

**日期：** 2026-08-11  
**状态：** **Grok 主路径收敛**：deep_search 由 Research Agent（think→tool→…）独占联网；Java 不再关键词预搜（2026-08-11）


**非目标：** 不解决国内外网络出口、不更换搜索引擎（继续 360/Bing/DDG 现有实现）

## 1. 目标

在**不换检索引擎**前提下，把小启联网从「前置一次性流水线」升级为接近 Grok Build 的 **Agent 工具循环**：

```
用户问题 → 模型/策略决策 → tool(search|open) → 观察 → … → 综合作答
```

成功标准（场景内对标 Grok）：

1. 名单类：官方通知 + ≥1 可点 PDF + 明确「非聊天附件」
2. 多跳：首轮弱相关时自动再搜，过程 SSE 可见
3. 同会话追问可复用 evidence
4. 零「无法实时网络搜索」话术
5. 黄金集：附件题 100% 有链；权威域命中达阈值

## 2. 架构

```
┌─────────────────────────────────────────────┐
│  Research Agent (ai-scoring)                 │
│  tools: web_search / open_url / finish       │
│  max_steps, evidence[], stop policy          │
└──────────────┬──────────────────────────────┘
               │ inject search_fn / open_fn
               ▼
     现有 web_research + Java 检索实现（不换引擎）
               │
               ▼
     researchBlock + citations + SSE steps
               │
               ▼
     最终回答（模板 + 诚实约束）
```

**原则：** 引擎实现可注入（TDD 用 fake）；生产注入真实 360/Bing 抓取。

## 3. 阶段与 Ticket

详见同目录 `2026-08-11-xiaoqi-research-agent-tickets.md`。

| 阶段 | 主题 | Ticket |
|------|------|--------|
| P0 | Tool loop 形状 + 测试 + 黄金集骨架 | T-P0-01 … T-P0-06 |
| P1 | 停止条件、会话 evidence、答案模板 | T-P1-01 … T-P1-06 |
| P2 | PDF 浅抽、多源对照、轨迹 UI | T-P2-01 … T-P2-05 |
| P3 | 偏好重排、线上指标 | T-P3-01 … T-P3-03 |

## 4. TDD 与多智能体约定

### TDD
- **先写失败测试，再写实现**（Iron Law）
- 单元测不依赖真实外网；search/open 全部可注入
- 黄金集集成测：可 mock 引擎，断言 evidence 形状

### 多智能体角色
| 角色 | 职责 |
|------|------|
| Planner/Controller | 本会话：拆 ticket、分派、合并、验收 |
| Implementer | 单 ticket：TDD 实现 + 单测绿 |
| Spec Reviewer | 对照 ticket 验收标准 |
| Quality Reviewer | 代码质量、无过度工程 |
| Verifier | 跑 pytest / 冒烟 |

### 执行顺序
1. 落盘本计划 + tickets  
2. 按依赖执行 P0 tickets（TDD）  
3. 每完成一批跑 `pytest` 相关用例  
4. P0 验收后再开 P1  

## 5. 文件落点（预期）

| 路径 | 说明 |
|------|------|
| `ai-scoring/app/services/assistant/research_agent.py` | Agent 循环核心 |
| `ai-scoring/app/services/assistant/research_tools.py` | Tool 定义与执行 |
| `ai-scoring/app/services/assistant/web_research.py` | 现有检索/抓页（被注入） |
| `ai-scoring/app/services/assistant/orchestrator.py` | 联网模式接入 agent |
| `ai-scoring/tests/test_research_agent.py` | 单元测试 |
| `ai-scoring/tests/test_research_stop_policy.py` | 停止策略 |
| `ai-scoring/tests/fixtures/research_golden.json` | 黄金集 |
| `ai-scoring/tests/test_research_golden.py` | 黄金集形状/策略测 |
| `backend/.../AssistantService.java` | SSE step / 可选调用 agent API |
| `docs/plans/2026-08-11-xiaoqi-research-agent-*.md` | 计划与 ticket 板 |

## 6. 风险

| 风险 | 缓解 |
|------|------|
| 延迟变长 | max_steps、并行 open、fast 不走 loop |
| 假 tool 标签 | 服务端执行 tool；strip 伪调用 |
| Token 暴涨 | evidence 截断 |
| 与「不换引擎」冲突 | tool 底层只调现有实现 |

## 7. 变更记录

| 日期 | 说明 |
|------|------|
| 2026-08-11 | 初稿；启动 P0 多智能体 TDD 执行 |
