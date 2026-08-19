# Agent Team 协作总则

> 项目代号：PitchForge
> 版本：1.0.0
> 创建日期：2026-04-15
> 维护者：Tech Lead

---

## 一、团队角色

| 角色 | 职责 | 不做的事 |
|------|------|---------|
| Orchestrator | 调度者，唯一与人对话的接口 | 不写代码、不做技术决策 |
| Tech Lead | 架构决策、任务分配、冲突仲裁 | 不写具体代码 |
| Prompt Engineer | Prompt 设计、调试、优化 | 不写后端/前端 |
| Backend Engineer | API、Pipeline、后端实现 | 不改 Prompt、不做前端 |
| Frontend Engineer | 确认节点 UI、进度展示 | 不写后端逻辑 |
| QA Reviewer | 代码审查、产出物质量审查 | 不写代码 |
| Standards Keeper | 规范制定、验收标准 | 不写代码、不审查代码 |

---

## 二、文件管理约定

```
项目根目录/
├── ORCHESTRATOR_BOARD.md       # Orchestrator 全局状态看板
├── DECISIONS_LOG.md            # Orchestrator 决策记录
├── TASK_QUEUE/                 # Orchestrator 任务队列
│   ├── pending/                # 待执行任务
│   ├── in_progress/            # 正在执行
│   └── completed/              # 已完成
├── docs/                       # Tech Lead 管理
├── standards/                  # Standards 管理
├── prompts/                    # Prompt Eng 管理
├── backend/                    # Backend 管理
├── frontend/                   # Frontend 管理
├── qa/                         # QA 管理
├── AGENTS.md                   # 本文件
├── CHANGELOG.md                # 全局变更日志
└── WORK_LOG/                   # 各 Agent 工作日志
```

---

## 三、调度规则

1. **Sprint 0 先启动 Standards（无依赖）和 Tech Lead（全局规划）**
2. **Prompt Eng 依赖 Standards 的数据格式规范**
3. **Backend 依赖 Standards + QA 的规范**
4. **Frontend 依赖 Standards 的数据格式**
5. **QA 依赖 Standards 的审查标准**
6. **任何 Agent 完成后，Orchestrator 检查产出物，决定下一步**
7. **遇到分歧升级给 Tech Lead，Tech Lead 裁决不了升级给人类**

---

## 四、决策升级路径

```
Agent → Tech Lead → Orchestrator → 人类
```

---

## 五、Definition of Done

一个任务完成的定义（由 Standards Keeper 维护）：
```
✅ 代码已编写并通过本地测试
✅ 单元测试覆盖率 ≥ 80%
✅ 通过 QA 代码审查
✅ 接口文档已更新
✅ 无 P0/P1 级 Bug
✅ 符合 CODING_STANDARDS.md
✅ 产出物通过内容质量审查（如适用）
✅ 已合并到主分支
```

---

## 六、变更历史

| 版本 | 日期 | 变更内容 | 变更人 |
|------|------|---------|-------|
| 1.0.0 | 2026-04-15 | 初始版本 | Orchestrator |

