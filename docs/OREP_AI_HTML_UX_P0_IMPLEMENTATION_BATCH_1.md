# OREP AI HTML 生成功能 UX 修复 — 第一批开发实施清单（P0）

> 版本：v1.0
> 日期：2026-04-23
> 来源文档：
> - `/Users/liuyixing/项目/OREP/docs/OREP_AI_HTML_UX_EXECUTION_PLAN.md`
> - `/Users/liuyixing/项目/OREP/docs/OREP_AI_HTML_UX_CODE_TASK_BREAKDOWN.md`

---

## 一、目标

这一批只做 `P0`，目的不是“让系统更漂亮”，而是先修掉最影响用户信任的核心问题：

1. 明明处理了，状态却不变
2. 明明通过了，还是不能下载
3. 明明补图了，系统还说缺图
4. 明明补评分点了，分数不涨
5. 页面被内部调试内容误判失败

这一批完成后，至少要达到：

- 下载门禁可信
- 评分覆盖可信
- 补图绑定可信
- 质量检查可信
- 前端状态刷新可信

---

## 二、实施顺序总览

### 推荐顺序

1. 统一交付门禁口径
2. 清理内部修复痕迹污染
3. 评分覆盖按当前 HTML 重算
4. 补图绑定与缺图提示一致性修复
5. 前端统一刷新链路收口

原因很简单：

- 第 1 步不做，后面所有处理结果都可能继续被旧门禁拦住
- 第 2 步不做，质检结果会继续被误杀
- 第 3 步不做，补评分点永远像没效果
- 第 4 步不做，补图永远像没生效
- 第 5 步不做，用户感知上仍会是“点了没变化”

---

## 三、第一批开发实施清单

## 第 1 步：统一交付门禁口径

### 目标

先解决“为什么永远也下载不了”“前端和后端结论不一致”。

### 主要修改文件

- `/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/ppt_service.py`
- `/Users/liuyixing/项目/OREP/ai-scoring/app/routers/ppt_router.py`
- `/Users/liuyixing/项目/OREP/frontend/user/src/stores/ppt.js`
- `/Users/liuyixing/项目/OREP/frontend/user/src/views/PptHistoryDetail.vue`

### 要改什么

#### 后端

在 `ppt_service.py`：

- 统一 `assess_task_deliverability()` 为唯一交付判断入口
- 严格定义：
  - `blocked`
  - `warning`
  - `ready`
- `p0_count` 只统计真正未完成的硬阻塞项
- 软建议项不再参与下载硬拦截

在 `ppt_router.py`：

- 所有任务详情/历史详情/下载接口统一返回最新 `deliverability`
- 下载接口只在 `deliverability.status == "blocked"` 时返回拦截

#### 前端

在 `ppt.js`：

- 增加统一的任务详情刷新方法
- 所有交付相关数据都从统一详情接口取

在 `PptHistoryDetail.vue`：

- 下载条件卡、终稿总审、下载按钮状态统一读同一份 `deliverability`
- `warning` 允许下载，但继续显示补强提示

### 验证方式

#### 接口验证

1. 用同一个任务 ID 调：
   - 任务详情接口
   - 历史详情接口
   - 下载接口
2. 对比三处 `deliverability.status` 是否一致

#### 页面验证

1. 找一个当前为 `warning` 的任务
2. 页面应显示：
   - “可预览但需补强”
   - 下载按钮可点击
3. 下载接口不能再报 409

#### 通过标准

- 同一任务前后端交付结论一致
- `warning` 不再阻止下载

---

## 第 2 步：清理内部修复痕迹污染

### 目标

解决“页面明明没问题，却因为内部修复提示词/调试面板被判失败”。

### 主要修改文件

- `/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/ppt_service.py`
- `/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/html_generator.py`
- `/Users/liuyixing/项目/OREP/frontend/user/src/views/PptHistoryDetail.vue`

### 要改什么

#### 后端

在 `ppt_service.py`：

- 所有正式检查前统一执行内部修复痕迹剥离：
  - 质量检查
  - 交付门禁
  - 评分覆盖
  - 导出前处理
- 重点确保以下内容不参与正式判断：
  - `orep-repair-panel`
  - 调试浮层
  - 建议补充/建议上传文案
  - 内部评分辅助说明

在 `html_generator.py`：

- 区分正式输出和调试输出
- 降级页、修复页不要继续把辅助说明混进正式主体

#### 前端

在 `PptHistoryDetail.vue`：

- 当前页预览、修复预览、正式内容预览三区分
- 明确哪些是用户可见辅助层，哪些是正式导出内容

### 验证方式

#### 接口验证

1. 对一个之前因“占位词”失败的页面重新跑质检
2. 检查 `placeholder_content` 是否仍误杀

#### 页面验证

1. 打开一页修复过的页面
2. 页面里若仍有辅助面板，只能是前端单独渲染，不应写进正式 HTML

#### 通过标准

- 不再出现内部修复文案导致页面失败
- 导出 HTML 中不含内部调试辅助块

---

## 第 3 步：评分覆盖按当前 HTML 重算

### 目标

解决“一键补评分点点了没效果，分数不涨”。

### 主要修改文件

- `/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/ppt_service.py`
- `/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/scoring_checker.py`
- `/Users/liuyixing/项目/OREP/frontend/user/src/stores/ppt.js`
- `/Users/liuyixing/项目/OREP/frontend/user/src/views/PptHistoryDetail.vue`

### 要改什么

#### 后端

在 `ppt_service.py`：

- `get_task_scoring_coverage(task_id)` 强制优先按当前 HTML 重算
- 大纲只做兜底，不再做主数据源
- “一键补评分点”时，将 `target_points` 作为硬约束塞给修复逻辑

在 `scoring_checker.py`：

- 补强对必备评分点的识别规则
- 输出当前缺失点、优先补点、点到页面映射

#### 前端

在 `ppt.js`：

- 增加评分覆盖强制刷新方法

在 `PptHistoryDetail.vue`：

- “一键补评分点”执行后，立即刷新：
  - 评分覆盖
  - 交付状态
  - 质量摘要
- 卡片中显示：
  - 当前优先补哪些评分点
  - 这些评分点关联哪几页

### 验证方式

#### 接口验证

1. 选一个当前缺必备评分点的任务
2. 记录补前：
   - 覆盖率
   - 缺失评分点列表
3. 执行补评分点
4. 再查评分覆盖接口

#### 页面验证

1. 点击“一键补评分点”
2. 页面卡片中的覆盖率应变化
3. 缺失评分点数应减少

#### 通过标准

- 补评分点后分数真实上涨或缺项真实减少
- 不再出现“点了没反应”的假动作

---

## 第 4 步：补图绑定与缺图提示一致性修复

### 目标

解决“明明传了图，系统还一直提示缺图”。

### 主要修改文件

- `/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/ppt_service.py`
- `/Users/liuyixing/项目/OREP/ai-scoring/app/routers/ppt_router.py`
- `/Users/liuyixing/项目/OREP/frontend/user/src/stores/ppt.js`
- `/Users/liuyixing/项目/OREP/frontend/user/src/views/PptHistoryDetail.vue`

### 要改什么

#### 后端

在 `ppt_service.py`：

- 强化显式页码绑定规则：
  - 文件名含 `page26`
  - 描述含 `第26页`
  - 标题语义匹配
- 上传后支持按页静默重质检
- 缺图判断只看最新质检结果

在 `ppt_router.py`：

- 上传素材接口增加可选“上传后重质检当前页”

#### 前端

在 `ppt.js`：

- 封装“上传成功后自动重跑当前页质检”

在 `PptHistoryDetail.vue`：

- 当前页提示只看最新 `failed_checks`
- 如果 `material_evidence = pass`：
  - 不再提示“先补图”
  - 直接切换到剩余问题提示：
    - 占位词
    - 模板化
    - 评分点

### 验证方式

#### 接口验证

1. 上传一张带明确页码提示的图片
2. 检查绑定结果是否正确落到对应页
3. 检查当前页最新质检结果是否刷新

#### 页面验证

1. 给第 27 页上传一张图
2. 页面右侧应显示：
   - 已关联素材更新
   - 缺图提示消失
3. 若仍失败，应提示真实剩余问题，而不是继续让用户补图

#### 通过标准

- 补图后不再机械提示“先补图”
- 当前页已关联素材准确，不串页

---

## 第 5 步：前端统一刷新链路收口

### 目标

解决“其实后台已经变了，但前端看起来还是旧状态”。

### 主要修改文件

- `/Users/liuyixing/项目/OREP/frontend/user/src/stores/ppt.js`
- `/Users/liuyixing/项目/OREP/frontend/user/src/views/PptHistoryDetail.vue`
- `/Users/liuyixing/项目/OREP/frontend/user/src/views/PptEditor.vue`

### 要改什么

#### 前端

在 `ppt.js`：

- 统一提供：
  - `fetchTaskDetail`
  - `refreshDeliverability`
  - `refreshScoringCoverage`
  - `refreshQualityReport`
  - `refreshCurrentPageQuality`

在 `PptHistoryDetail.vue`：

- 所有一键动作执行后，统一走一个“刷新快照”入口
- 避免各按钮各自刷新部分数据，导致页面状态不一致

在 `PptEditor.vue`：

- 若预览区也依赖相同任务状态，统一接 store 刷新结果

### 验证方式

#### 页面验证

1. 连续执行：
   - 补图
   - 补评分点
   - 清占位词
2. 每次执行后观察：
   - 评分覆盖
   - 交付状态
   - 当前页状态
   - 下载条件卡
   是否同步刷新

#### 通过标准

- 所有主视图刷新口径一致
- 不再需要用户手动反复刷新页面才能看到结果

---

## 四、批次完成标准

这一批 `P0` 完成后，必须达到：

### 状态一致性

- 下载状态、质检状态、评分状态一致

### 动作有效性

- 补图后缺图状态能消除
- 补评分点后评分覆盖能变化
- 修复后不会再被内部辅助层误杀

### 用户感知

- 用户不再遇到“永远也下载不了”
- 用户不再遇到“点了也没反应”

---

## 五、建议执行方式

建议不要多线并发开发这一批，而是严格按顺序做：

1. 先改后端门禁与评分逻辑
2. 再改补图绑定与质检刷新
3. 最后改前端统一刷新与表现层

因为前端很多“没效果”的根因，其实都在后端判断口径不统一。

