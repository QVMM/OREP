# 评分报告来源标识去按钮化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将评分报告列表中的来源胶囊改为普通元数据文字，消除它是独立按钮或筛选器的误解。

**Architecture:** 保持报告行作为唯一交互容器，只调整 `Statistics.vue` 的来源文案和表现类。使用现有设计令牌渲染弱化文字，并由 Playwright 回归测试锁定非控件语义、无控件装饰及响应式无溢出。

**Tech Stack:** Vue 3、scoped CSS、Playwright、平台 `--ds-*` 设计令牌

---

### Task 1: 锁定普通来源元数据契约

**Files:**
- Modify: `frontend/user/tests/review-pages-design.spec.js:25-92`

- [ ] **Step 1: 将报告夹具设为上传视频来源**

把参加者报告夹具中的来源改为：

```js
sourceType: 'uploaded_video',
```

- [ ] **Step 2: 添加来源文字与视觉语义断言**

在“路演训练评分标签使用嵌入式报告表面并保留可读日期”测试中加入：

```js
const sourceMeta = page.getByText('来源：上传视频', { exact: true })
await expect(sourceMeta).toBeVisible()

const sourceMetrics = await sourceMeta.evaluate(node => {
  const style = getComputedStyle(node)
  return {
    tagName: node.tagName,
    role: node.getAttribute('role'),
    backgroundColor: style.backgroundColor,
    backgroundImage: style.backgroundImage,
    borderTopWidth: style.borderTopWidth,
    borderRadius: style.borderRadius,
    boxShadow: style.boxShadow,
    textAlign: style.textAlign
  }
})
expect(sourceMetrics.tagName).toBe('SPAN')
expect(sourceMetrics.role).toBeNull()
expect(sourceMetrics.backgroundColor).toBe('rgba(0, 0, 0, 0)')
expect(sourceMetrics.backgroundImage).toBe('none')
expect(sourceMetrics.borderTopWidth).toBe('0px')
expect(sourceMetrics.borderRadius).toBe('0px')
expect(sourceMetrics.boxShadow).toBe('none')
expect(sourceMetrics.textAlign).toBe('left')
```

- [ ] **Step 3: 运行测试并确认红灯**

Run:

```bash
cd frontend/user
VITE_DEV_HTTPS=0 npx playwright test tests/review-pages-design.spec.js --grep "路演训练评分标签"
```

Expected: FAIL，因为页面仍显示“上传视频”胶囊，尚未出现“来源：上传视频”。

### Task 2: 将来源胶囊改为普通元数据

**Files:**
- Modify: `frontend/user/src/views/Statistics.vue:64`
- Modify: `frontend/user/src/views/Statistics.vue:420-429`
- Modify: `frontend/user/src/views/Statistics.vue:677-687`

- [ ] **Step 1: 修改来源文案和类名**

将模板来源节点替换为：

```vue
<span class="source-meta">来源：{{ report.sourceLabel }}</span>
```

- [ ] **Step 2: 删除旧胶囊样式**

完整删除两个 `.source-badge` 规则，避免未使用的按钮化视觉代码残留。

- [ ] **Step 3: 添加纯文字元数据样式**

在平台规范覆盖区加入：

```css
.source-meta {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  color: var(--ds-muted);
  font-size: var(--ds-text-micro);
  font-weight: var(--ds-weight-medium);
  line-height: var(--ds-leading-body);
  text-align: left;
  white-space: nowrap;
}
```

该规则不得加入背景、边框、阴影、圆角、指针样式或独立 hover/focus 状态。

- [ ] **Step 4: 运行专项测试并确认绿灯**

Run:

```bash
cd frontend/user
VITE_DEV_HTTPS=0 npx playwright test tests/review-pages-design.spec.js --grep "路演训练评分标签"
```

Expected: 1 passed。

### Task 3: 回归与真实页面验收

**Files:**
- Verify: `frontend/user/src/views/Statistics.vue`
- Verify: `frontend/user/tests/review-pages-design.spec.js`

- [ ] **Step 1: 运行报告标签与设计回归**

Run:

```bash
cd frontend/user
VITE_DEV_HTTPS=0 npx playwright test tests/online-meeting-report-tabs.spec.js tests/review-pages-design.spec.js
```

Expected: 全部通过，报告筛选、查询参数、日期和跳转行为不变。

- [ ] **Step 2: 运行生产构建**

Run:

```bash
cd frontend/user
npm run build
```

Expected: Vite 构建成功，无 Vue 模板或 CSS 解析错误；既有 chunk-size 警告不阻塞。

- [ ] **Step 3: 检查残留胶囊类**

Run:

```bash
rg -n "source-badge|来源：\\{\\{" frontend/user/src/views/Statistics.vue frontend/user/tests/review-pages-design.spec.js
```

Expected: 无 `source-badge`；模板只有 `source-meta` 的“来源：”文案。

- [ ] **Step 4: 在真实页面检查桌面与窄屏**

打开 `http://localhost:5174/online-meeting?tab=reports` 并确认：

1. 来源显示为“来源：上传视频”或“来源：在线路演”；
2. 来源没有底色、边框、阴影和胶囊圆角；
3. 鼠标经过来源时没有独立反馈，整行仍可进入报告；
4. 桌面端与 390px 窄屏均无横向溢出；
5. “查看报告”仍是行内唯一显式操作提示。

> 当前工作区不是 Git 仓库，因此不执行 commit、分支合并或工作树清理步骤。
