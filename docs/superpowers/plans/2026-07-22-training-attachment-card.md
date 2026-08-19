# Training Attachment Card Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the training week navigation card with a right-side task attachment card whose files can be previewed and downloaded.

**Architecture:** Keep the existing `TrainingDayView.vue` data source and `FilePreview` integration. Move attachment rendering out of the left task book into a dedicated right-side card, use native anchor downloads for files with `fileUrl`, and leave the submit card unchanged.

**Tech Stack:** Vue 3 SFC, Vue Router, Element Plus icons, Playwright.

---

### Task 1: Lock the new information architecture in the page contract

**Files:**
- Modify: `frontend/user/tests/training-copy.spec.js`

- [ ] **Step 1: Write the failing assertions**

Add assertions that the left task book no longer contains attachments, the right side contains a task attachment card, the week card and training-plan link are absent, and the fixture attachment exposes separate preview and download controls:

```js
await expect(taskBook.getByText('任务附件', { exact: true })).toHaveCount(0)
await expect(side.getByRole('heading', { name: '任务附件' })).toBeVisible()
await expect(side.locator('.training-week-card')).toHaveCount(0)
await expect(side.getByRole('link', { name: '训练计划' })).toHaveCount(0)

const attachmentRow = side.locator('.training-attachment-item').filter({ hasText: '需求访谈记录模板.pdf' })
await expect(attachmentRow.getByRole('button', { name: '预览' })).toBeVisible()
const downloadLink = attachmentRow.getByRole('link', { name: '下载' })
await expect(downloadLink).toHaveAttribute('href', '/fixtures/interview-template.pdf')
await expect(downloadLink).toHaveAttribute('download', '需求访谈记录模板.pdf')
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
cd frontend/user
OREP_E2E_BASE_URL=http://localhost:5174 npx playwright test tests/training-copy.spec.js --reporter=line
```

Expected: FAIL because `.training-week-card` still exists and the attachment is still rendered in the left task book.

### Task 2: Move task attachments into the right column

**Files:**
- Modify: `frontend/user/src/modules/training/TrainingDayView.vue`

- [ ] **Step 1: Remove the left task-book attachment section**

Delete the `training-task-book__section training-task-attachments` block from the left task book while keeping `taskAttachments`, `previewAttachment`, `fileExtension`, and `formatFileSize` available.

- [ ] **Step 2: Replace the week card with the attachment card**

Render the following structure before the submit card:

```vue
<section class="student-card training-attachments-card">
  <div class="training-card-head">
    <h2>任务附件</h2>
    <span>{{ taskAttachments.length }} 个</span>
  </div>
  <div v-if="taskAttachments.length" class="training-attachment-list">
    <article v-for="attachment in taskAttachments" :key="attachment.id" class="training-attachment-item">
      <span class="training-attachment-item__type">{{ fileExtension(attachment.fileName) }}</span>
      <div class="training-attachment-item__meta">
        <strong>{{ attachment.fileName }}</strong>
        <small>{{ formatFileSize(attachment.fileSize) }}</small>
      </div>
      <div class="training-attachment-item__actions">
        <button type="button" @click="previewAttachment(attachment)">预览</button>
        <a v-if="attachment.fileUrl" :href="attachment.fileUrl" :download="attachment.fileName">下载</a>
      </div>
    </article>
  </div>
  <div v-else class="training-inline-empty">老师暂未上传任务附件。</div>
</section>
```

- [ ] **Step 3: Remove week-navigation-only script and CSS**

Delete `currentWeek`, `weekDays`, `weekDateRange`, `formatChineseDate`, `weekdayLabel`, `dayOfMonth`, `weekDayStatus`, `weekDayClass`, and all `.training-week-*` rules because the page no longer renders week navigation.

- [ ] **Step 4: Add compact attachment-card styling**

Style `.training-attachments-card`, `.training-attachment-list`, `.training-attachment-item`, metadata, and actions for the narrow right column. Each item uses a flat divided row, not a nested card; preview is a button and download is an anchor with matching compact-control styling.

- [ ] **Step 5: Run the focused test and verify GREEN**

Run:

```bash
cd frontend/user
OREP_E2E_BASE_URL=http://localhost:5174 npx playwright test tests/training-copy.spec.js --reporter=line
```

Expected: `1 passed`.

### Task 3: Verify build and real-page layout

**Files:**
- Verify: `frontend/user/src/modules/training/TrainingDayView.vue`
- Verify: `frontend/user/tests/training-copy.spec.js`

- [ ] **Step 1: Build the user frontend**

Run:

```bash
cd frontend/user
npm run build
```

Expected: Vite exits with code 0.

- [ ] **Step 2: Inspect the real training day**

Open `http://localhost:5174/training/days/22` and verify:

- The right column contains exactly two cards: “任务附件” and “提交成果”.
- “训练计划” and the week-date card are absent.
- Attachment names, sizes, preview buttons, and download links are visible.
- The left task book no longer contains “任务附件”.
- `document.body.scrollWidth <= document.body.clientWidth` at desktop width.

- [ ] **Step 3: Confirm no stale week-navigation code remains**

Run:

```bash
rg -n "training-week|currentWeek|weekDays|weekDateRange|weekdayLabel|dayOfMonth|weekDayStatus|weekDayClass" frontend/user/src/modules/training/TrainingDayView.vue
```

Expected: no matches.

> This workspace has no Git metadata, so commit checkpoints are not available; test and build outputs are the execution checkpoints.
