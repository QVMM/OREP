# AI 评分总结 · 编辑叙事呈现设计

## 背景

现有评分报告七页顶栏结构把后端字段原样堆在前台，视觉上像后台仪表盘（「AI 味」）。用户确认新方向：

- **目标优先级**：行动闭环为主（C），分数定心为辅（A）
- **行动形态**：默认教练处方，可同步团队任务（双层）
- **信息架构**：A 三幕叙事 × B 问题队列 × C 提分旅程
- **视觉语言**：对标 Grok/x.ai 官网——大字、留白、一屏一意、Explore 下钻；主题色保留 OREP 暖米 + 橙

## 目标

1. 将 `overview` 改造成编辑叙事主台，去掉硬编码示例文案。
2. 数据 100% 来自现有 `useAiScoreReport` / 后端字段；缺字段则空态或隐藏。
3. 保留子路由（五维 / 证据 / 表达 / 现场 / 改进 / 评审团），从主台 Explore 进入。
4. 不改后端协议、不改评分算法。

## 非目标

1. 本轮不重写全部 7 个子页皮肤（可后续同风格）。
2. 不新增 mock API 或并行 `/report-v2` 路由。
3. 不为空报告编造分数、可追回分、结论句。

## 架构

```
Layout (useAiScoreReport) ──provide──► Overview
                              │
                              ▼
              buildScoreSummaryPresentation(snapshot)
                              │
                              ▼
                   编辑叙事 UI（无 invent）
```

- 新增纯函数：`frontend/user/src/utils/aiScoreSummaryPresentation.js`
- Overview 只负责渲染与用户操作（同步任务、跳转、下载）
- Shell 支持 `mode="editorial"`：无标题栏、无七 Tab，仅提供背景与主内容槽

## 数据映射

| UI | 来源 | 空态 |
|----|------|------|
| 分数 | `overallScore` | Layout 错误/加载态 |
| 等级 | `scoreLevel.label` | 同分展示 |
| Hero 标题句 | `ai_score.overall_conclusion` 等真实文案 | 不展示假 headline |
| 副文 | `overall_analysis` 等 | 隐藏 |
| 目标/差距 | `score_recovery_summary.target_score` | 无目标则不显示块 |
| 可追回 | recovery summary 或 ruleEngine / tasks 求和 | 无法算则不显示 |
| 处方 Top3 | `trainingTasks` → deductions → workItem drafts | 诚实空列表 |
| 改法/验收 | task / deduction 字段 | 缺则不编 |
| 关键时刻 | anchorIds + frames | 无匹配则少画或不画 |
| 五维 | `dimensions` | &lt;3 维只列表 |
| 同步任务 | `createTeamTasksFromReport` | 无团队提示 |
| Explore | `sectionPath(...)` | 路由已有 |

## 处方排序

1. 有 training tasks：P0 &gt; P1 &gt; P2，再按 expectedRecoverPoints 降序  
2. 否则未追回 structured_deductions，按可追回/扣分降序  
3. 再否则 reportWorkItemDrafts  
4. 取前 3 条；「全部」进 actions 或页内展开真实列表  

## 验收

1. 无硬编码项目文案进入生产路径（结论/分析/语速等）。  
2. session 报告加载后，分数与处方与 API 一致。  
3. 字段缺失时页面不崩溃、不显示虚假数字。  
4. 同步任务、Explore 跳转子页可用。  
5. 前端相关单测通过。  

## 迁移

1. presentation 纯函数 + 单测  
2. 重写 Overview  
3. Shell editorial 模式  
4. 深页同风格（后续）  
