# OREP AI PPT Agent Team

OREP 项目 AI PPT 智能生成系统的 Agent Team 协作框架。

## 团队架构

| Agent | 角色 | 核心职责 |
|-------|------|---------|
| Tech Lead | 技术负责人 | 架构决策、Sprint 计划、冲突仲裁 |
| Prompt Engineer | 提示词工程师 | Round1-4 Prompt 设计/调试/优化 |
| Backend Engineer | 后端工程师 | API、Pipeline、后处理 |
| Frontend Engineer | 前端工程师 | 确认节点 UI、问卷表单 |
| QA Reviewer | 质量审查员 | 代码审查、产出物质量审查 |
| Standards Keeper | 规范制定者 | 编码规范、验收标准、术语表 |

## 快速开始

### 1. 启动 Agent

```bash
cd /Users/liuyixing/项目/OREP/docs/agent_team
./start_team.sh <agent_id>
```

**Agent ID 列表：**
- `tech_lead` - Tech Lead
- `prompt_eng` - Prompt Engineer
- `backend_eng` - Backend Engineer
- `frontend_eng` - Frontend Engineer
- `qa` - QA Reviewer
- `standards` - Standards Keeper

### 2. 查看所有启动提示词

```bash
./start_team.sh all
```

### 3. 查看协作总则

阅读 `AGENTS.md` 了解团队协作规范。

## 目录结构

```
docs/agent_team/
├── README.md              # 本文件
├── AGENTS.md              # 团队协作总则
├── start_team.sh          # Agent 启动脚本
└── startup_prompts/       # 各 Agent 启动提示词
    ├── 01_tech_lead.md
    ├── 02_prompt_engineer.md
    ├── 03_backend_engineer.md
    ├── 04_frontend_engineer.md
    ├── 05_qa_reviewer.md
    └── 06_standards_keeper.md

WORK_LOG/                  # 各 Agent 工作日志
├── tech_lead.md
├── prompt_eng.md
├── backend_eng.md
├── frontend_eng.md
├── qa.md
└── standards.md
```

## 工作流程

1. **Sprint 开始**：Tech Lead 发布 `SPRINT_PLAN.md`，分配任务
2. **每日**：各 Agent 在 `WORK_LOG/*.md` 记录进展
3. **跨角色协作**：通过文件注释和 WORK_LOG 沟通
4. **Sprint 结束**：Tech Lead 发布 `SPRINT_REVIEW.md`

## 相关文档

- [PPT 生成架构 v4.0](../../docs/ppt-architecture-v4.md)
- [PPT 设计系统 v4.0](../../docs/ppt-design-system-v4.md)
- [OREP 融合方案](../../docs/PPT生成系统与OREP融合方案.md)