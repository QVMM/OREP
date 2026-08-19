# AI 评分整改周期页面开发方案

## 1. 设计目标

将当前 AI 评分报告页从“报告展示页”改造成“路演整改周期工作台”。

核心闭环：

```txt
AI评分结果 -> 扣分项 -> 证据锚点 -> 整改任务 -> 验收标准 -> 下一轮重评
```

本方案采用类似 Linear 的产品思路：重点不是展示很多图表，而是让用户知道：

- 当前分数卡在哪里
- 哪些问题必须先改
- 哪些证据阻塞重评
- 每个任务什么时候完成
- 改完后如何验收
- 评审团复核如何进入答辩训练

---

## 2. 导航结构调整

### 2.1 当前问题

原型图里出现了左侧菜单和顶部菜单重复的问题。

### 2.2 调整方案

只保留：

```txt
系统顶部主导航
+
AI评分页内横向 tabs
```

删除当前 `AiScoreResult.vue` 里的左侧 `rail`。

### 2.3 页面结构

```txt
OrepTopNav
  ↓
AiScoreCycleLayout
  ├─ 页面 Header
  ├─ 横向 Tabs
  └─ 当前 Tab 内容
```

Tabs：

```txt
总览 / 五维评分 / 证据链 / 表达节奏 / 现场呈现 / 改进方案 / AI评审团
```

---

## 3. 推荐文件结构

```txt
frontend/user/src/views/AiScoreResult.vue

frontend/user/src/components/ai-score-cycle/
  AiScoreCycleLayout.vue
  CycleTabs.vue
  CycleHealthStrip.vue
  CycleRoadmap.vue
  CycleIssuePill.vue
  CycleDependencyFlow.vue
  CycleEvidenceFrame.vue
  CycleMetricRow.vue

frontend/user/src/components/ai-score-cycle/pages/
  CycleOverview.vue
  CycleDimensions.vue
  CycleEvidence.vue
  CycleExpression.vue
  CyclePresentation.vue
  CycleActionPlan.vue
  CycleJury.vue

frontend/user/src/composables/ai-score-cycle/
  useAiScoreCycleData.js
  useCycleRoadmap.js
  useCycleTasks.js

frontend/user/src/styles/
  ai-score-cycle.css
```

---

## 4. 核心技术选型

| 模块 | 技术 |
|---|---|
| 周期 Roadmap | Vue DOM + CSS Grid |
| 任务连接线 | SVG overlay |
| 任务 pill | Vue 组件 |
| 趋势图 | ECharts |
| 雷达图 | ECharts |
| 证据帧 | `img` + Vue 状态 |
| 分歧矩阵 | CSS Grid |
| 评委分数尺 | DOM + absolute positioning |
| Tabs | Vue state |
| 团队任务生成 | 复用现有接口 |

不建议引入重型图编辑库。

Roadmap 和连接线用 `CSS Grid + SVG` 最合适，可控、轻量、容易响应式。

---

## 5. 关键组件说明

## 5.1 `CycleRoadmap.vue`

用于展示整改周期。

```txt
今天 / Day1 / Day2 / Day3 / 重评
```

支持多种 lane：

```txt
证据补齐
材料修改
彩排训练
答辩准备
```

技术实现：

- CSS Grid 负责列布局
- 每个任务是 `CycleIssuePill`
- SVG overlay 绘制任务依赖线
- 点击任务后在右侧或下方展示详情

## 5.2 `CycleIssuePill.vue`

用于展示一个可执行问题。

字段建议：

```js
{
  id: 'OREP-121',
  priority: 'P0',
  title: '补用户痛点证据',
  owner: '产品负责人',
  dueDay: 'Day1',
  expectedGain: '+8',
  status: 'open',
  source: 'SCORE-01'
}
```

显示内容：

```txt
OREP-121
P0
补用户痛点证据
+8
负责人
状态
```

## 5.3 `CycleDependencyFlow.vue`

用于展示底部依赖链：

```txt
扣分项 -> 证据锚点 -> 任务 -> 验收 -> 下一轮评分
```

技术实现：

- DOM 节点
- SVG 箭头
- 当前阻塞节点高亮

---

## 6. 各页面开发方案

## 6.1 总览页

### 目标

展示整个 3 天整改周期。

### 页面内容

- 当前分：72.5
- 目标分：88
- 可追回：+18-24
- 未解决 P0：3
- 证据置信度：86%
- 评审团共识：82%
- 三天整改 Roadmap
- 风险与阻塞
- 评分依据依赖图

### 技术实现

| 区域 | 技术 |
|---|---|
| 健康指标 | `CycleHealthStrip` |
| 三天周期 | `CycleRoadmap` |
| 任务 pill | `CycleIssuePill` |
| 依赖图 | `CycleDependencyFlow` |
| 风险列表 | DOM list |

---

## 6.2 五维评分页

### 目标

不是只展示分数，而是说明每个维度如何在周期里被修复。

### 页面内容

- 项目价值
- 商业逻辑
- 技术可行性
- 表达节奏
- 评委说服力
- 每个维度对应的整改任务
- 每个维度对应验收标准

### 技术实现

| 区域 | 技术 |
|---|---|
| 维度条形进度 | CSS progress bar |
| 能力雷达 | ECharts Radar |
| 维度整改周期 | `CycleRoadmap` |
| 评分项表格 | CSS Grid table |
| 任务映射 | DOM rows |

---

## 6.3 证据链页

### 目标

说明哪些证据已经固定，哪些证据阻塞重评。

### 页面内容

- 证据快照状态
- 转写片段数
- 关键帧数量
- 证据锚点数量
- 技术校准
- 证据覆盖矩阵
- 当前证据详情
- 证据时间线

### 技术实现

| 区域 | 技术 |
|---|---|
| 证据快照 | metric strip |
| 关键帧 | `CycleEvidenceFrame` |
| 证据时间线 | DOM timeline |
| 技术校准 | `CycleMetricRow` |
| 证据覆盖矩阵 | CSS Grid |
| 证据依赖 | SVG connection |

---

## 6.4 表达节奏页

### 目标

把语速、停顿、口头禅转成可训练任务。

### 页面内容

- 平均语速
- 严重停顿
- 最长停顿
- 口头禅次数
- 需要回练的句段
- 关键句替换
- 表达训练排期

### 技术实现

| 区域 | 技术 |
|---|---|
| 语音指标 | metric strip |
| 语音趋势 | ECharts Line/Bar |
| 停顿 marker | ECharts markPoint 或 DOM marker |
| 句段列表 | CSS Grid rows |
| before/after 替换 | DOM diff block |
| 训练排期 | `CycleRoadmap` |

---

## 6.5 现场呈现页

### 目标

把画面、站位、屏幕内容、音画冲突转成彩排动作。

### 页面内容

- 视觉综合分
- 音画冲突数量
- 关键帧数量
- 主要屏幕类型
- 阶段诊断
- 动作处方
- 音画融合趋势
- 复盘依据

### 技术实现

| 区域 | 技术 |
|---|---|
| 阶段诊断 | timeline lanes |
| 视频帧 | `img` + caption |
| 动作处方 | checklist rows |
| 融合趋势 | ECharts Line |
| 复盘依据 | metric grid |
| 问题排期 | `CycleRoadmap` |

---

## 6.6 改进方案页

### 目标

这是整改周期的执行中心。

### 页面内容

- 团队工作项生成器
- 三天整改周期
- 提分优先级
- 训练任务
- 话术替换
- PPT 材料清单
- 60 分钟彩排排期
- 重评前验收清单

### 技术实现

| 区域 | 技术 |
|---|---|
| 工作项生成 | 复用 `reportWorkItemDrafts` |
| 团队选择 | select |
| 任务生成 | 现有 `/api/project-teams/{id}/tasks` |
| 三天周期 | `CycleRoadmap` |
| 验收清单 | checkbox list |
| 话术替换 | before/after block |
| 材料清单 | CSS rows |

---

## 6.7 AI评审团页

### 目标

让评审团复核进入整改周期，而不是孤立展示。

### 页面内容

- 官方评分
- 评审团均分
- 分差
- 评委数
- 共识问题
- 分歧焦点
- 下一轮训练优先级
- 评委分数尺
- 维度分歧矩阵
- 答辩追问题库

### 技术实现

| 区域 | 技术 |
|---|---|
| 评委分数尺 | DOM + absolute positioning |
| 九位评委列表 | compact table/list |
| 共识与分歧 | stacked panels |
| 分歧矩阵 | CSS Grid |
| 分数区间 | mini spectrum bar |
| 追问题库 | issue list |
| 同步训练 | 生成 Day2 答辩训练任务 |

---

## 7. 数据整理方案

新增 composable：

```txt
useAiScoreCycleData.js
```

职责：

- 接收当前 `result`
- 生成周期任务
- 聚合扣分项
- 聚合证据锚点
- 聚合表达节奏问题
- 聚合现场呈现问题
- 聚合评审团问题
- 输出统一 Roadmap 数据

建议输出结构：

```js
{
  health: {
    currentScore: 72.5,
    targetScore: 88,
    recoverableRange: '+18-24',
    evidenceConfidence: 0.86,
    juryConsensus: 0.82
  },
  days: ['今天', 'Day1', 'Day2', 'Day3', '重评'],
  lanes: [
    { key: 'evidence', label: '证据补齐' },
    { key: 'material', label: '材料修改' },
    { key: 'rehearsal', label: '彩排训练' },
    { key: 'defense', label: '答辩准备' }
  ],
  tasks: [
    {
      id: 'OREP-121',
      lane: 'evidence',
      day: 'Day1',
      title: '补用户痛点证据',
      priority: 'P0',
      expectedGain: 8,
      source: 'SCORE-01',
      status: 'open'
    }
  ],
  dependencies: [
    {
      from: 'SCORE-01',
      to: 'OREP-121'
    }
  ]
}
```

---

## 8. 开发顺序

## Phase 1：结构改造

1. 删除左侧菜单。
2. 新增 `AiScoreCycleLayout`。
3. 新增横向 tabs。
4. 保留现有数据加载逻辑。
5. 总览页先用 mock 数据跑通。

## Phase 2：Roadmap 组件

1. 实现 `CycleRoadmap`。
2. 实现 `CycleIssuePill`。
3. 实现 SVG 连接线。
4. 接入真实 tasks。
5. 做响应式验证。

## Phase 3：总览页落地

1. 接入健康指标。
2. 接入风险阻塞。
3. 接入依赖图。
4. 验证 1366 / 1440 / 1920 宽度。

## Phase 4：逐页迁移

顺序建议：

```txt
五维评分 -> 证据链 -> 改进方案 -> 表达节奏 -> 现场呈现 -> AI评审团
```

原因：

- 五维评分、证据链、改进方案是主闭环
- 表达节奏和现场呈现依赖 coaching 数据
- AI评审团可以最后接，因为状态较多

## Phase 5：清理旧代码

1. 删除旧 `rail` 样式。
2. 删除旧深色驾驶舱布局样式。
3. 保留可复用计算逻辑。
4. 将大文件 computed 迁移到 composable。

---

## 9. 测试重点

### 9.1 路由

```txt
/ai-score/:meetingId
/ai-score/report/:sessionId
/ai-score/report-id/:reportId
```

### 9.2 状态

```txt
评分进行中
评分失败
评分完成
没有证据包
没有关键帧
没有评审团复核
没有团队
团队任务生成失败
PDF 下载失败
```

### 9.3 视觉

```txt
1366px
1440px
1920px
移动端降级
连接线不乱
任务 pill 不重叠
tabs 不换行错乱
```

### 9.4 功能

```txt
生成团队工作项
下载 PDF
返回会议
生成证据快照
生成评审团复核
切换 tabs
点击任务查看详情
```

---

## 10. 第一版最小可落地范围

建议第一版只做：

```txt
顶部 tabs
总览页
CycleRoadmap
CycleIssuePill
CycleHealthStrip
CycleDependencyFlow
```

先把“整改周期”的核心体验跑通，再迁移其他页面。

第一版成功标准：

```txt
用户打开 AI评分页后，第一眼知道：
1. 当前多少分
2. 目标多少分
3. 哪些问题阻塞提分
4. 未来 3 天每天做什么
5. 哪些任务来自哪些扣分项
6. 完成后如何重评
```
