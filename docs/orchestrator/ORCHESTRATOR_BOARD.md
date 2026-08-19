# Orchestrator Board — 全局状态看板

> 项目：OREP AI PPT 智能生成系统
> 版本：v1.0
> 日期：2026-04-15
> Sprint：Sprint 0（项目初始化）

---

## 一、项目概览

| 项目 | 状态 |
|------|------|
| 项目名称 | OREP AI PPT 智能生成系统 |
| 方案文档 | ppt-architecture-v4.md |
| Agent Team | 7 个角色（Orchestrator + 6 Agent） |
| 当前 Sprint | Sprint 0（基础设施搭建） |
| Sprint 进度 | 0% |

---

## 二、Sprint 0 任务看板

### 2.1 任务状态总览

| 任务 | 负责人 | 状态 | 依赖 | 备注 |
|------|--------|------|------|------|
| 发布项目 README | Tech Lead | pending | - | |
| 创建目录结构 | Tech Lead | pending | - | |
| 发布 CODING_STANDARDS.md | Standards | pending | - | Sprint 0 优先 |
| 发布 GLOSSARY.md | Standards | pending | - | |
| 发布 Phase 1-3 验收标准 | Standards | pending | - | |
| 建立 CODE_REVIEW_CHECKLIST.md | QA | pending | - | |
| 建立 CONTENT_REVIEW_CHECKLIST.md | QA | pending | - | |
| 分析现有 Prompt 质量 | Prompt Eng | pending | Standards 规范 | |
| 分析现有后端代码 | Backend Eng | pending | Standards 规范 | |
| 分析现有前端代码 | Frontend Eng | pending | Standards 规范 | |

### 2.2 Sprint 0 交付物清单

- [ ] `docs/agent_team/` 目录结构就绪
- [ ] `WORK_LOG/` 工作日志目录就绪
- [ ] `standards/CODING_STANDARDS.md` 发布
- [ ] `standards/GLOSSARY.md` 发布
- [ ] `standards/ACCEPTANCE_CRITERIA/phase1_ac.md` 发布
- [ ] `standards/ACCEPTANCE_CRITERIA/phase2_ac.md` 发布
- [ ] `standards/ACCEPTANCE_CRITERIA/phase3_ac.md` 发布
- [ ] `qa/CODE_REVIEW_CHECKLIST.md` 发布
- [ ] `qa/CONTENT_REVIEW_CHECKLIST.md` 发布
- [ ] 开发环境就绪

---

## 三、Agent 状态

| Agent | 当前任务 | 状态 | 上次活跃 |
|-------|----------|------|----------|
| Tech Lead | Sprint 0 规划 | pending | - |
| Standards | 制定基础规范 | pending | - |
| QA | 建立审查框架 | pending | - |
| Prompt Eng | 分析现有 Prompt | pending | - |
| Backend Eng | 分析现有代码 | pending | - |
| Frontend Eng | 分析现有代码 | pending | - |

---

## 四、调度计划

### Sprint 0 启动顺序（依赖驱动）

```
阶段 1（无依赖，并行启动）
    ├── Standards → 发布 CODING_STANDARDS.md + GLOSSARY.md
    └── Tech Lead → 发布 Sprint Plan + 建立目录结构

阶段 2（依赖 Standards）
    ├── QA → 基于 Standards 规范建立审查清单
    ├── Prompt Eng → 基于 Standards 数据格式分析 Prompt
    ├── Backend Eng → 基于 Standards 编码规范分析代码
    └── Frontend Eng → 基于 Standards 数据格式分析前端

阶段 3（汇总）
    └── Tech Lead → Sprint 0 Review
```

---

## 五、决策记录 (DECISIONS_LOG)

| 日期 | 决策 | 原因 | 决策者 |
|------|------|------|--------|
| 2026-04-15 | Sprint 0 先启动 Standards + Tech Lead | 无依赖，可并行 | Orchestrator |

---

## 六、阻塞事项

| 事项 | 阻塞者 | 解决方案 |
|------|--------|----------|
| 无 | - | - |

---

## 七、人类需要决定的事项

| 事项 | 选项 | 优先级 |
|------|------|--------|
| Sprint 0 持续时间 | 1天 / 3天 / 1周 | P1 |

---

*本文件由 Orchestrator 维护，每次人类唤醒时更新。*