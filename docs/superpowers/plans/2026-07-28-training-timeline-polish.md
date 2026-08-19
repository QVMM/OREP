# 训练时间轴视觉精修实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将训练任务页的周信息改为无边框章节标记，并让追踪光束与紧凑型任务节点稳定对齐。

**Architecture:** 保留 `TrainingPlan.vue` 的业务数据、筛选和任务结构，只调整周标题与节点视觉；保留 `TrainingTracingBeam.vue` 的滚动计算，只提前首个弯折位置。通过现有 Playwright 专项测试验证样式、几何对齐、响应式和原交互。

**Tech Stack:** Vue 3、CSS、SVG、Playwright、Vite

---

### Task 1: 建立视觉回归测试

**Files:**
- Modify: `frontend/user/tests/training-task-list.spec.js`

- [ ] **Step 1: 为周章节标记、节点尺寸和折线位置增加断言**

在“训练任务使用纯中文跟踪光束时间线并在窄屏降为单列”测试中增加：

```js
await expect(firstWeek.locator('.tasks-week__head')).toHaveCSS('border-top-width', '0px')
await expect(firstWeek.locator('.tasks-week__head')).toHaveCSS('box-shadow', 'none')

const firstNode = firstWeek.locator('.tasks-day__date i').first()
await expect(firstNode).toHaveCSS('width', '7px')
await expect(firstNode).toHaveCSS('height', '7px')

const pathData = await tracingBeam.locator('.training-tracing-beam__path--base').getAttribute('d')
const firstTurn = Number(pathData.match(/L 20 ([\\d.]+)/)?.[1])
const nodeTop = await firstNode.evaluate(node => {
  const beam = node.closest('[data-training-tracing-beam]')
  return node.getBoundingClientRect().top - beam.getBoundingClientRect().top
})
expect(firstTurn).toBeLessThan(nodeTop)
```

- [ ] **Step 2: 运行专项测试并确认新增断言失败**

Run:

```bash
cd frontend/user
OREP_E2E_BASE_URL=http://localhost:5174 npx playwright test tests/training-task-list.spec.js
```

Expected: 新增样式或几何断言失败，原有业务断言继续执行。

### Task 2: 改造周章节标记和任务节点

**Files:**
- Modify: `frontend/user/src/modules/training/TrainingPlan.vue`

- [ ] **Step 1: 去除周信息卡片视觉**

将 `.tasks-week__head` 的边框、圆角、白底和阴影移除，增加克制的章节引导线；保留吸顶和现有文字结构。

- [ ] **Step 2: 收紧周信息层级**

将周次、标题、日期、提交统计和进度线改为轻量排版，进度线高度降为 2 像素。

- [ ] **Step 3: 将任务节点固定为 7 像素**

普通、当前、完成和超期状态共用相同几何尺寸，仅改变颜色。当前节点使用 `::after` 绘制 14 像素以内的柔光呼吸环。

- [ ] **Step 4: 增加减少动态效果适配**

在 `prefers-reduced-motion: reduce` 下关闭呼吸动画并保留静态细环。

### Task 3: 校准追踪光束折线

**Files:**
- Modify: `frontend/user/src/modules/training/components/TrainingTracingBeam.vue`

- [ ] **Step 1: 提前首个弯折**

将 `upperTurn` 限制在内容顶部 22 像素以内，使第一处弯折在首个任务节点上方结束。

- [ ] **Step 2: 保持第二处弯折和滚动渐变逻辑不变**

不修改滚动容器、渐变推进、尺寸监听和响应式横向基准。

### Task 4: 验证和发布

**Files:**
- Update build output: `frontend/user/dist`
- Update deployment copy: `deploy/frontend/user/dist`

- [ ] **Step 1: 运行专项测试**

```bash
cd frontend/user
OREP_E2E_BASE_URL=http://localhost:5174 npx playwright test tests/training-task-list.spec.js
```

Expected: 全部通过。

- [ ] **Step 2: 完成学生端生产构建**

```bash
cd frontend/user
npm run build
```

Expected: 退出码为 0。

- [ ] **Step 3: 检查桌面端和窄屏页面**

在 `1280×900` 和 `720×900` 下确认章节标记、节点对齐、呼吸效果和横向溢出。

- [ ] **Step 4: 更新云端学生端**

备份服务器现有学生端静态资源，只替换学生端构建产物；使用无依赖重建方式启动学生端并重启入口代理。

- [ ] **Step 5: 验证生产页面**

确认生产地址返回 200、新资源文件已生效、容器健康且训练任务页可访问。
