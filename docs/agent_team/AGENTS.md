# Agent Team 协作总则

> 项目：OREP AI PPT 智能生成系统
> 版本：v1.0
> 日期：2026-04-15

---

## 一、Team 架构

```
                    ┌─────────────┐
                    │   Tech Lead  │  ← 总指挥，架构决策，冲突仲裁
                    └──────┬──────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
   ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
   │ Prompt Eng  │ │ Backend Eng │ │ Frontend Eng│
   └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
          │                │                │
          └────────────────┼────────────────┘
                           │
                    ┌──────▼──────┐
                    │  QA / Review │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Standards   │
                    └─────────────┘
```

**6 个 Agent 角色，职责边界清晰，不越权。**

---

## 二、各角色职责

### Tech Lead（技术负责人）

**职责：**
- 架构决策
- Sprint 计划与任务分配
- 跨角色冲突仲裁
- 里程碑把控

**不做：**
- 不写代码
- 不写 Prompt
- 不做 UI 设计

### Prompt Engineer（提示词工程师）

**职责：**
- Round1-4 Prompt 设计/调试/优化
- Few-shot 示例库建设
- Prompt 版本管理

**不做：**
- 不写后端代码
- 不做前端 UI

### Backend Engineer（后端工程师）

**职责：**
- API 实现
- Pipeline 编排
- 文件存储管理
- HTML→图片→PPTX 后处理

**不做：**
- 不改 Prompt 内容
- 不做前端页面

### Frontend Engineer（前端工程师）

**职责：**
- 确认节点 UI
- 问卷表单
- 版本对比 UI
- 图片上传

**不做：**
- 不写后端逻辑
- 不设计 Prompt

### QA Reviewer（质量审查员）

**职责：**
- 代码审查
- 产出物质量审查
- 有退回权

**不做：**
- 不写代码

### Standards Keeper（规范制定者）

**职责：**
- 编码规范
- 验收标准
- 术语表

**不做：**
- 不写代码
- 不审查代码

---

## 三、文件管理约定

```
OREP/
├── docs/agent_team/           # Agent Team 文档
│   ├── AGENTS.md              # 本文件
│   └── *.md                   # 其他协作文档
├── WORK_LOG/                  # 工作日志
│   ├── tech_lead.md
│   ├── prompt_eng.md
│   ├── backend_eng.md
│   ├── frontend_eng.md
│   ├── qa.md
│   └── standards.md
├── ai-scoring/app/services/ppt/  # PPT 服务（Backend 管理）
│   ├── prompts/                  # Prompts（Prompt Eng 管理）
│   └── ...
└── frontend/user/src/views/      # 前端（Frontend 管理）
```

---

## 四、协作协议

### 每日
- 各 Agent 在 WORK_LOG/*.md 记录当日进展
- 遇到阻塞立即 @Tech Lead

### 每 Sprint
- Sprint 开始：Tech Lead 发布 SPRINT_PLAN.md
- Sprint 结束：Tech Lead 发布 SPRINT_REVIEW.md

### 跨角色协作
- Prompt Eng 需要数据格式 → 找 Standards
- Backend 需要 Prompt 接口定义 → 找 Prompt Eng
- Frontend 需要 API 契约 → 找 Backend
- 任何分歧 → Tech Lead 仲裁

---

## 五、Git 分支策略

```
main
├── develop
│   ├── feature/prompt-xxx
│   ├── feature/backend-xxx
│   └── feature/frontend-xxx
└── hotfix/xxx
```

**合并规则：**
- feature → develop：QA 审查 + Tech Lead 审批
- develop → main：Standards 验收 + Tech Lead 审批

---

*本文档由 Tech Lead 维护。*