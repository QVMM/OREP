# 正式考试右侧栏对齐修正设计

## 目标

让桌面端的答题卡与考试状态栏整体从左侧答题面板的顶部基线开始排列，同时保留右侧栏滚动吸顶和现有卡片间距。

## 问题

`ExamTaking.vue` 中 `.answer-side` 的 sticky 偏移最终被覆盖为 `calc(var(--header-height) + 78px)`。该偏移大于左侧答题面板的自然起始位置，导致右侧答题卡被浏览器向下推移约 52px。

## 设计

- 桌面端将 `.answer-side` 的两处 `top` 声明统一为 `90px`。
- `90px` 对应考试顶栏固定行高 `68px` 加内容区顶部间距 `22px`，与 `.question-stage` 的自然顶部一致。
- 保留 `position: sticky`，滚动时右侧栏仍停留在考试顶栏下方。
- 保留答题卡与考试状态卡之间的 `14px` 间距。
- 1100px 以下继续使用现有 `position: static`，不改变单栏响应式布局。

## 范围

仅修改 `/Users/liuyixing/项目/OREP/frontend/user/src/views/ExamTaking.vue` 中 `.answer-side` 的桌面端 sticky 偏移，并扩展现有 Playwright 顶栏测试文件验证左右卡片顶部对齐。

## 验收标准

- 1284×892 视口中，`.question-stage` 与第一个 `.side-panel` 的顶部坐标误差不超过 `1px`。
- 两张右侧卡片仍保持 `14px` 间距。
- 页面向下滚动时右侧栏保持 sticky。
- 1100px 以下页面仍为单栏且无水平溢出。
- 回归测试与生产构建通过。
