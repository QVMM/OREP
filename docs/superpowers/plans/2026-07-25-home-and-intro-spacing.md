# 首页与引导页空间统一实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 统一正式首页四张卡片的空间密度，并让引导页交互工作台在浏览器缩放和不同视口宽度下稳定展示。

**Architecture:** 正式首页继续使用现有 Vue 模板，只把四卡片统一为标题、内容、操作三段式弹性布局，并用一组局部 CSS 变量控制 16/10/14 间距。引导页工作台采用同一空间规则，移除冲突的固定视口高度，用宽度断点和自然高度完成重排。

**Tech Stack:** Vue 3、Vite、Scoped CSS、Node Test、Chromium/浏览器响应式验证。

---

### Task 1: 正式首页四卡片空间标准

**Files:**
- Modify: `frontend/user/src/modules/home/StudentHome.vue`

- [ ] **Step 1: 为首页根节点定义统一空间变量**

在 `.student-home` 中加入：

```css
--home-card-padding: 16px;
--home-card-gap: 14px;
--home-content-gap: 10px;
--home-action-gap: 14px;
```

- [ ] **Step 2: 取消桌面固定行高**

将首页网格从固定 `308px/310px` 改为：

```css
grid-template-rows: 156px repeat(2, minmax(308px, auto));
gap: var(--home-card-gap);
```

- [ ] **Step 3: 统一四卡片容器结构**

让 `.home-card` 使用统一内边距和弹性列布局：

```css
.home-card {
  padding: var(--home-card-padding);
  display: flex;
  flex-direction: column;
  gap: var(--home-content-gap);
}
```

删除各卡片为补偿固定高度而设置的不一致顶部间距。

- [ ] **Step 4: 统一今日任务卡片的内容节奏**

将标题、摘要、元信息和要求列表限制为稳定高度，操作区贴底：

```css
.today-card__actions {
  margin-top: auto;
  padding-top: var(--home-action-gap);
}
```

- [ ] **Step 5: 统一学习图表、路演卡和评分卡**

学习图表使用 `min-height` 和弹性绘图区；路演卡、评分卡按钮均使用 `margin-top: auto`，内容块之间统一 `10px`。

- [ ] **Step 6: 构建验证**

Run: `npm run build`

Expected: Vite build succeeds with no CSS or Vue compilation errors.

### Task 2: 引导页工作台结构与数据同步

**Files:**
- Modify: `frontend/user/src/components/intro/IntroProductPreview.vue`

- [ ] **Step 1: 同步正式首页内容**

删除“先看课程”，补充今日任务必交项，把分数和五维示例改为正式首页当前数据结构。

- [ ] **Step 2: 统一卡片空间变量**

在 `.ipp` 中加入与正式首页相同的 `16/10/14` 变量，并应用到 `.home-grid` 和 `.home-card`。

- [ ] **Step 3: 移除冲突固定高度**

将：

```css
height: min(700px, 78vh);
min-height: 600px;
max-height: 760px;
```

改为内容驱动：

```css
min-height: clamp(640px, 72vw, 860px);
height: auto;
```

并取消 `.ipp-content` 的内部主滚动依赖。

- [ ] **Step 4: 增加窄桌面断点**

在 `1100px` 以下保留竖向侧栏，但让工作台自然增高；在 `900px` 以下切换横向导航与单列卡片。

- [ ] **Step 5: 保持交互功能**

确认侧栏切换、柱状图点击、按钮 toast 和模块返回首页继续工作。

- [ ] **Step 6: 构建验证**

Run: `npm run build`

Expected: Vite build succeeds.

### Task 3: 响应式与云端验证

**Files:**
- Verify: `frontend/user/dist/`

- [ ] **Step 1: 检查源码残留**

Run: `rg "先看课程|height: min\(700px, 78vh\)" frontend/user/src/components/intro/IntroProductPreview.vue`

Expected: no matches.

- [ ] **Step 2: 本地构建**

Run: `npm run build`

Expected: success.

- [ ] **Step 3: 部署用户端**

同步 `frontend/user/dist/` 到云端 `/opt/orep/deploy/frontend/user/dist/`，重建并重启 `frontend-user`。

- [ ] **Step 4: 云端产物核对**

比较本地和云端 `StudentHome-*.js`、`Intro-*.js` 的 SHA-256。

Expected: both pairs match.

- [ ] **Step 5: 线上健康检查**

Run HTTP checks for `/` and `/intro`.

Expected: HTTP 200 and Nginx configuration valid.
