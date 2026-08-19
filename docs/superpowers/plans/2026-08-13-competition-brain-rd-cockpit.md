# 竞赛大脑研发驾驶舱 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `project management/` 做出独立站点：老板看 11 个竞赛大脑模块做到哪了，研发报进度，证据自动扫描且只读，多人 WebSocket 实时同步。

**Architecture:** 根目录一条命令同时起 Node 服务和 Vue 前端。领域规则（权限、打架、超期、风险、人员负荷）是无 UI 纯函数，先用 `node:test` 锁死。SQLite 只存模块/任务/变更；扫描器读 OREP 仓库和 `data/config.json` 里的探活地址，只写证据层。HTTP 校验角色后落库并经 WebSocket 广播。前端不复用正式产品路由壳。OREP 根目录不是 git 仓库，本工具在 `project management/` 内单独 `git init`。

**Tech Stack:** Node 22（`node:test`、`node:http`、`node:sqlite`）、`ws`、Vue 3、Vite、Vue Router、Pinia、Vitest。

**Spec:** `docs/superpowers/specs/2026-08-13-competition-brain-rd-cockpit-design.md`

---

## File map

```
project management/
  package.json                 # 一条命令 dev / test
  README.md
  .gitignore
  data/probes.json             # 模块 → 仓库路径 / 探活 URL
  data/config.json             # 仓库根路径、扫描间隔、服务基址
  server/package.json
  server/src/domain/catalog.js
  server/src/domain/permissions.js
  server/src/domain/divergence.js
  server/src/domain/week.js
  server/src/domain/risks.js
  server/src/domain/people.js
  server/src/store/db.js
  server/src/scan/fsProbe.js
  server/src/scan/httpProbe.js
  server/src/scan/gitLog.js
  server/src/scan/runner.js
  server/src/realtime/hub.js
  server/src/http/server.js
  server/tests/*.test.mjs
  web/package.json
  web/vite.config.js
  web/index.html
  web/src/main.js
  web/src/App.vue
  web/src/styles.css
  web/src/lib/labels.js
  web/src/lib/derived.js
  web/src/api/client.js
  web/src/stores/session.js
  web/src/stores/cockpit.js
  web/src/components/*.vue
  web/src/views/*.vue
  web/src/router.js
  web/tests/*.test.mjs
```

路径含空格，所有命令给 `project management` 加引号。

---

### Task 1: Scaffold and local git

**Files:**
- Create: `project management/package.json`
- Create: `project management/.gitignore`
- Create: `project management/README.md`
- Create: `project management/data/config.json`
- Create: `project management/data/probes.json`
- Create: `project management/server/package.json`
- Create: `project management/web/package.json`

- [ ] **Step 1: Write root files**

`project management/package.json`:

```json
{
  "name": "competition-brain-rd-cockpit",
  "private": true,
  "scripts": {
    "dev": "node server/src/dev.mjs",
    "test": "node --test server/tests/*.test.mjs && npm --prefix web test",
    "test:server": "node --test server/tests/*.test.mjs"
  }
}
```

`project management/.gitignore`:

```
node_modules/
data/*.sqlite
data/*.sqlite-wal
data/*.sqlite-shm
web/dist/
.DS_Store
```

`project management/README.md`:

```markdown
# 竞赛大脑研发驾驶舱

给研发和老板看产品做到哪了。不接入正式前后端。

## 启动

在本目录执行：

```bash
npm install
npm --prefix server install
npm --prefix web install
npm run dev
```

浏览器打开终端打印的地址（默认 http://localhost:4701 ）。局域网内老板用同一台机器的 IP:4701。

登录选「老板」或「研发」并填显示名。证据每 30 秒扫一次，也可点「立即扫描」。

探活地址在 `data/config.json`。未配置或服务没开时，该项证据为「过期」或「不通」，不会假绿。
```

`project management/data/config.json`（`repoRoot` 相对本目录上一级即 OREP 根）：

```json
{
  "repoRoot": "..",
  "scanIntervalMs": 30000,
  "httpTimeoutMs": 2000,
  "listenHost": "0.0.0.0",
  "serverPort": 4700,
  "bases": {
    "student": "http://127.0.0.1:5174",
    "teacher": "http://127.0.0.1:5175",
    "admin": "http://127.0.0.1:5173",
    "backend": "http://127.0.0.1:8080",
    "scoring": "http://127.0.0.1:8090",
    "assistant": "http://127.0.0.1:8080",
    "ppt": "http://127.0.0.1:8090"
  }
}
```

`project management/data/probes.json`：

```json
{
  "student": {
    "paths": ["frontend/user/src/modules/home/StudentHome.vue", "frontend/user/src/router/index.js"],
    "pageUrl": "{student}/",
    "apiUrl": "{backend}/api/user"
  },
  "teacher": {
    "paths": ["frontend/teacher/src/views/WorkbenchView.vue", "frontend/teacher/src/router/index.js"],
    "pageUrl": "{teacher}/",
    "apiUrl": "{backend}/api/project-teams"
  },
  "project": {
    "paths": ["frontend/teacher/src/views/team/ProjectsView.vue"],
    "pageUrl": "{teacher}/projects",
    "apiUrl": "{backend}/api/project-teams"
  },
  "camp": {
    "paths": ["frontend/teacher/src/views/camp/CampWorkspaceView.vue"],
    "pageUrl": "{teacher}/camp",
    "apiUrl": "{backend}/api/project-teams"
  },
  "roadshow": {
    "paths": ["frontend/teacher/src/views/roadshow/RoadshowHomeView.vue"],
    "pageUrl": "{teacher}/roadshow",
    "apiUrl": "{backend}/api/project-prep"
  },
  "resources": {
    "paths": ["frontend/teacher/src/views/resources/ResourcesView.vue"],
    "pageUrl": "{teacher}/resources",
    "apiUrl": "{backend}/api/project-teams"
  },
  "xiaoqi": {
    "paths": ["frontend/teacher/src/views/ai/AssistantView.vue"],
    "pageUrl": "{teacher}/ai/assistant",
    "apiUrl": "{backend}/api/assistant"
  },
  "ppt": {
    "paths": ["frontend/teacher/src/views/ai/PptManageView.vue", "frontend/user/src/views/ScriptList.vue"],
    "pageUrl": "{teacher}/ai/ppt",
    "apiUrl": "{ppt}/health"
  },
  "scoring": {
    "paths": ["frontend/teacher/src/views/review/ReviewReportsView.vue", "ai-scoring/app"],
    "pageUrl": "{teacher}/review/reports",
    "apiUrl": "{scoring}/health"
  },
  "analytics": {
    "paths": ["frontend/teacher/src/views/analytics/AnalyticsView.vue"],
    "pageUrl": "{teacher}/analytics",
    "apiUrl": "{backend}/api/teacher/student-growth"
  },
  "admin": {
    "paths": ["frontend/admin/src/App.vue"],
    "pageUrl": "{admin}/",
    "apiUrl": "{admin}/"
  }
}
```

`project management/server/package.json`:

```json
{
  "name": "cockpit-server",
  "type": "module",
  "dependencies": { "ws": "^8.18.0" }
}
```

`project management/web/package.json`:

```json
{
  "name": "cockpit-web",
  "type": "module",
  "scripts": {
    "dev": "vite --host 0.0.0.0 --port 4701",
    "build": "vite build",
    "test": "vitest run"
  },
  "dependencies": {
    "pinia": "^2.2.6",
    "vue": "^3.5.13",
    "vue-router": "^4.5.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.2.1",
    "@vue/test-utils": "^2.4.6",
    "happy-dom": "^15.11.7",
    "vite": "^6.0.3",
    "vitest": "^2.1.8"
  }
}
```

- [ ] **Step 2: Init git inside this folder only**

```bash
cd "/Users/liuyixing/项目/OREP/project management"
git init
git add package.json .gitignore README.md data/config.json data/probes.json server/package.json web/package.json
git commit -m "chore: scaffold competition-brain rd cockpit"
```

Expected: 创建本地仓库并完成第一次提交。不要在 OREP 根目录 `git init`。

---

### Task 2: Module catalog

**Files:**
- Create: `project management/server/src/domain/catalog.js`
- Test: `project management/server/tests/catalog.test.mjs`

- [ ] **Step 1: Write the failing test**

```js
import test from 'node:test'
import assert from 'node:assert/strict'
import { MODULES, moduleById } from '../src/domain/catalog.js'

test('catalog has 11 stable modules in four groups', () => {
  assert.equal(MODULES.length, 11)
  assert.deepEqual(
    MODULES.map((m) => m.id),
    ['student', 'teacher', 'project', 'camp', 'roadshow', 'resources', 'xiaoqi', 'ppt', 'scoring', 'analytics', 'admin'],
  )
  assert.equal(MODULES.filter((m) => m.group === '两端工作台').length, 2)
  assert.equal(MODULES.filter((m) => m.group === '备赛闭环').length, 4)
  assert.equal(MODULES.filter((m) => m.group === '智能与裁决').length, 3)
  assert.equal(MODULES.filter((m) => m.group === '治理与学情').length, 2)
  assert.equal(moduleById('scoring').name, 'AI 评分')
  assert.equal(MODULES[0].judgment, 'not_started')
  assert.equal(MODULES[0].progressPercent, 0)
  assert.equal(MODULES[0].ownerName, null)
})
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd "/Users/liuyixing/项目/OREP/project management"
node --test server/tests/catalog.test.mjs
```

Expected: `ERR_MODULE_NOT_FOUND`

- [ ] **Step 3: Write catalog**

```js
export const MODULES = [
  { id: 'student', name: '学生端', group: '两端工作台' },
  { id: 'teacher', name: '教师端', group: '两端工作台' },
  { id: 'project', name: '项目管理', group: '备赛闭环' },
  { id: 'camp', name: '训练营', group: '备赛闭环' },
  { id: 'roadshow', name: '路演', group: '备赛闭环' },
  { id: 'resources', name: '资源中心', group: '备赛闭环' },
  { id: 'xiaoqi', name: '小启 AI', group: '智能与裁决' },
  { id: 'ppt', name: 'PPT/讲稿', group: '智能与裁决' },
  { id: 'scoring', name: 'AI 评分', group: '智能与裁决' },
  { id: 'analytics', name: '学情分析', group: '治理与学情' },
  { id: 'admin', name: '管理端', group: '治理与学情' },
].map((m) => ({
  ...m,
  judgment: 'not_started',
  progressPercent: 0,
  ownerName: null,
  priority: 'normal',
  riskFlag: false,
  riskNote: '',
  briefs: [],
  evidence: {
    pages: 'stale',
    apis: 'stale',
    service: 'stale',
    detail: {},
    scannedAt: null,
    lastSuccessAt: null,
    recentCommits: [],
  },
}))

export function moduleById(id) {
  return MODULES.find((m) => m.id === id) || null
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
node --test server/tests/catalog.test.mjs
```

Expected: `ok` / pass

- [ ] **Step 5: Commit**

```bash
git add server/src/domain/catalog.js server/tests/catalog.test.mjs
git commit -m "feat: add 11-module catalog"
```

---

### Task 3: Permission rules

**Files:**
- Create: `project management/server/src/domain/permissions.js`
- Test: `project management/server/tests/permissions.test.mjs`

- [ ] **Step 1: Write the failing test**

```js
import test from 'node:test'
import assert from 'node:assert/strict'
import { applyModulePatch, applyTaskPatch, addBrief } from '../src/domain/permissions.js'

const boss = { displayName: '林总', role: 'boss' }
const dev = { displayName: '高志淼', role: 'dev' }

test('dev can change judgment and progress, boss cannot', () => {
  const mod = { judgment: 'not_started', progressPercent: 0 }
  const ok = applyModulePatch(dev, mod, { judgment: 'shipped', progressPercent: 80 })
  assert.equal(ok.ok, true)
  assert.equal(ok.value.judgment, 'shipped')
  const denied = applyModulePatch(boss, mod, { judgment: 'shipped' })
  assert.equal(denied.ok, false)
  assert.match(denied.error, /老板不能改完成度|老板不能改产品判断/)
})

test('boss can assign owner and flag risk, dev cannot reassign module owner', () => {
  const mod = { ownerName: null, riskFlag: false, priority: 'normal' }
  const ok = applyModulePatch(boss, mod, { ownerName: '高志淼', riskFlag: true, priority: 'high' })
  assert.equal(ok.ok, true)
  const denied = applyModulePatch(dev, mod, { ownerName: '别人' })
  assert.equal(denied.ok, false)
})

test('nobody can patch evidence', () => {
  const mod = { evidence: { pages: 'present' } }
  assert.equal(applyModulePatch(dev, mod, { evidence: { pages: 'missing' } }).ok, false)
  assert.equal(applyModulePatch(boss, mod, { evidence: { pages: 'missing' } }).ok, false)
})

test('dev claims task only as self; boss reassigns anyone', () => {
  const task = { ownerName: null, status: 'todo', progressNote: '', evidenceSummary: 'x', source: 'scan' }
  assert.equal(applyTaskPatch(dev, task, { ownerName: '高志淼' }, dev).ok, true)
  assert.equal(applyTaskPatch(dev, task, { ownerName: '别人' }, dev).ok, false)
  assert.equal(applyTaskPatch(boss, task, { ownerName: '别人' }, boss).ok, true)
})

test('dev cannot edit scan evidenceSummary; boss cannot change status', () => {
  const task = { status: 'todo', evidenceSummary: 'locked', source: 'scan', progressNote: '' }
  assert.equal(applyTaskPatch(dev, task, { evidenceSummary: 'fake' }, dev).ok, false)
  assert.equal(applyTaskPatch(boss, task, { status: 'done' }, boss).ok, false)
  assert.equal(applyTaskPatch(dev, task, { status: 'doing', progressNote: '在修' }, dev).ok, true)
})

test('only boss adds briefs', () => {
  assert.equal(addBrief(boss, '先上评分').ok, true)
  assert.equal(addBrief(dev, '先上评分').ok, false)
})
```

- [ ] **Step 2: Run test to verify it fails**

```bash
node --test server/tests/permissions.test.mjs
```

Expected: `ERR_MODULE_NOT_FOUND`

- [ ] **Step 3: Write permissions**

```js
const MODULE_DEV = new Set(['judgment', 'progressPercent'])
const MODULE_BOSS = new Set(['ownerName', 'priority', 'riskFlag', 'riskNote'])
const TASK_DEV = new Set(['title', 'status', 'dueAt', 'thisWeek', 'blockedReason', 'progressNote', 'moduleId'])
const TASK_BOSS = new Set(['priority'])
const NEVER = new Set(['evidence', 'evidenceSummary', 'source', 'divergence', 'id', 'briefs'])

function deny(error) {
  return { ok: false, error }
}

function apply(role, allowed, current, patch, extraCheck) {
  const next = { ...current }
  for (const [key, value] of Object.entries(patch)) {
    if (NEVER.has(key)) return deny(role === 'boss' ? '不能改自动证据' : '研发不能改证据')
    if (key === 'ownerName') continue
    if (!allowed.has(key)) {
      if (role === 'boss') return deny('老板不能改完成度或任务进度')
      return deny('研发不能改优先级、负责人或批示')
    }
    next[key] = value
  }
  if (Object.prototype.hasOwnProperty.call(patch, 'ownerName')) {
    const checked = extraCheck(patch.ownerName)
    if (!checked.ok) return checked
    next.ownerName = patch.ownerName
  }
  if (Object.prototype.hasOwnProperty.call(patch, 'judgment') && role === 'boss') {
    return deny('老板不能改产品判断')
  }
  return { ok: true, value: next }
}

export function applyModulePatch(actor, module, patch) {
  const allowed = actor.role === 'dev' ? MODULE_DEV : MODULE_BOSS
  return apply(actor.role, allowed, module, patch, (name) => {
    if (actor.role !== 'boss') return deny('研发不能改模块负责人')
    return { ok: true }
  })
}

export function applyTaskPatch(actor, task, patch) {
  const allowed = actor.role === 'dev' ? TASK_DEV : TASK_BOSS
  return apply(actor.role, allowed, task, patch, (name) => {
    if (actor.role === 'boss') return { ok: true }
    if (name !== actor.displayName) return deny('研发只能认领给自己')
    return { ok: true }
  })
}

export function addBrief(actor, text) {
  if (actor.role !== 'boss') return deny('只有老板能写批示')
  const body = String(text || '').trim()
  if (!body) return deny('批示不能为空')
  return {
    ok: true,
    value: { author: actor.displayName, at: new Date().toISOString(), text: body },
  }
}

export function canTriggerScan() {
  return true
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
node --test server/tests/permissions.test.mjs
```

Expected: all pass. If the boss+judgment message does not match the test regex, adjust the deny string to include `老板不能改产品判断`.

- [ ] **Step 5: Commit**

```bash
git add server/src/domain/permissions.js server/tests/permissions.test.mjs
git commit -m "feat: lock boss/dev permission rules"
```

---

### Task 4: Divergence sentence

**Files:**
- Create: `project management/server/src/domain/divergence.js`
- Test: `project management/server/tests/divergence.test.mjs`

- [ ] **Step 1: Write the failing test**

```js
import test from 'node:test'
import assert from 'node:assert/strict'
import { computeDivergence } from '../src/domain/divergence.js'

test('shipped + down service is a fight', () => {
  const d = computeDivergence({
    name: 'AI 评分',
    judgment: 'shipped',
    evidence: { pages: 'present', apis: 'present', service: 'down' },
  })
  assert.equal(d.kind, 'judgment_vs_evidence')
  assert.equal(d.sentence, '负责人标「已上线」，但评分服务探活失败。')
})

test('not_started + all stale is not a fight', () => {
  const d = computeDivergence({
    name: '学生端',
    judgment: 'not_started',
    evidence: { pages: 'stale', apis: 'stale', service: 'stale' },
  })
  assert.equal(d, null)
})

test('usable_incomplete + missing pages fights', () => {
  const d = computeDivergence({
    name: '路演',
    judgment: 'usable_incomplete',
    evidence: { pages: 'missing', apis: 'present', service: 'present' },
  })
  assert.match(d.sentence, /可用不完整/)
  assert.match(d.sentence, /关键页面缺失/)
})
```

- [ ] **Step 2: Run test to verify it fails**

```bash
node --test server/tests/divergence.test.mjs
```

Expected: module not found

- [ ] **Step 3: Write divergence**

```js
const JUDGMENT_LABEL = {
  shipped: '已上线',
  usable_incomplete: '可用不完整',
  in_progress: '做到一半',
  not_started: '未开始',
}

function evidenceProblems(name, evidence) {
  const bits = []
  if (evidence.service === 'down') bits.push(name.includes('评分') ? '评分服务探活失败' : `${name}服务探活失败`)
  if (evidence.pages === 'missing') bits.push('关键页面缺失')
  if (evidence.apis === 'missing') bits.push('关键接口缺失')
  if (evidence.pages === 'down') bits.push('页面不通')
  if (evidence.apis === 'down') bits.push('接口不通')
  if (evidence.service === 'missing') bits.push('服务不存在')
  if (evidence.pages === 'stale' || evidence.apis === 'stale' || evidence.service === 'stale') {
    bits.push('证据已过期')
  }
  return bits
}

export function computeDivergence(module) {
  const optimistic = module.judgment === 'shipped' || module.judgment === 'usable_incomplete'
  if (!optimistic) return null
  const problems = evidenceProblems(module.name, module.evidence || {})
  if (!problems.length) return null
  return {
    kind: 'judgment_vs_evidence',
    sentence: `负责人标「${JUDGMENT_LABEL[module.judgment]}」，但${problems.join('，')}。`,
  }
}

export { JUDGMENT_LABEL }
```

- [ ] **Step 4: Run test to verify it passes**

```bash
node --test server/tests/divergence.test.mjs
```

Expected: pass. If `stale` on unused channels makes extra problems, only include stale when that channel is the failing one and others are not worse — keep the implementation matching the tests above.

- [ ] **Step 5: Commit**

```bash
git add server/src/domain/divergence.js server/tests/divergence.test.mjs
git commit -m "feat: compute judgment vs evidence divergence"
```

---

### Task 5: Week and 超期

**Files:**
- Create: `project management/server/src/domain/week.js`
- Test: `project management/server/tests/week.test.mjs`

- [ ] **Step 1: Write the failing test**

```js
import test from 'node:test'
import assert from 'node:assert/strict'
import { isThisWeek, isOverdue, selectWeekTasks } from '../src/domain/week.js'

const now = new Date('2026-08-13T10:00:00+08:00')

test('thisWeek flag or due in this week', () => {
  assert.equal(isThisWeek({ thisWeek: true, dueAt: null }, now), true)
  assert.equal(isThisWeek({ thisWeek: false, dueAt: '2026-08-14T00:00:00+08:00' }, now), true)
  assert.equal(isThisWeek({ thisWeek: false, dueAt: '2026-07-01T00:00:00+08:00' }, now), false)
})

test('overdue is due before today and not done', () => {
  assert.equal(isOverdue({ dueAt: '2026-08-12T23:00:00+08:00', status: 'doing' }, now), true)
  assert.equal(isOverdue({ dueAt: '2026-08-12T23:00:00+08:00', status: 'done' }, now), false)
  assert.equal(isOverdue({ dueAt: '2026-08-13T23:00:00+08:00', status: 'todo' }, now), false)
})

test('week list puts overdue first', () => {
  const rows = selectWeekTasks([
    { id: 'a', thisWeek: true, dueAt: '2026-08-15', status: 'todo' },
    { id: 'b', thisWeek: true, dueAt: '2026-08-10', status: 'doing' },
    { id: 'c', thisWeek: false, dueAt: null, status: 'todo' },
  ], now)
  assert.deepEqual(rows.map((t) => t.id), ['b', 'a'])
})
```

- [ ] **Step 2: Run test to verify it fails**

```bash
node --test server/tests/week.test.mjs
```

Expected: module not found

- [ ] **Step 3: Write week.js**

```js
function startOfDay(now) {
  const d = new Date(now)
  d.setHours(0, 0, 0, 0)
  return d
}

function startOfWeekMonday(now) {
  const d = startOfDay(now)
  const day = d.getDay()
  const offset = day === 0 ? 6 : day - 1
  d.setDate(d.getDate() - offset)
  return d
}

function endOfWeek(now) {
  const d = startOfWeekMonday(now)
  d.setDate(d.getDate() + 7)
  return d
}

export function isThisWeek(task, now = new Date()) {
  if (task.thisWeek) return true
  if (!task.dueAt) return false
  const due = new Date(task.dueAt)
  return due >= startOfWeekMonday(now) && due < endOfWeek(now)
}

export function isOverdue(task, now = new Date()) {
  if (!task.dueAt || task.status === 'done') return false
  return new Date(task.dueAt) < startOfDay(now)
}

export function selectWeekTasks(tasks, now = new Date()) {
  return tasks
    .filter((t) => isThisWeek(t, now))
    .sort((a, b) => Number(isOverdue(b, now)) - Number(isOverdue(a, now)))
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
node --test server/tests/week.test.mjs
```

Expected: pass

- [ ] **Step 5: Commit**

```bash
git add server/src/domain/week.js server/tests/week.test.mjs
git commit -m "feat: this-week and overdue task rules"
```

---

### Task 6: Risks and people

**Files:**
- Create: `project management/server/src/domain/risks.js`
- Create: `project management/server/src/domain/people.js`
- Test: `project management/server/tests/derived.test.mjs`

- [ ] **Step 1: Write the failing test**

```js
import test from 'node:test'
import assert from 'node:assert/strict'
import { collectRisks } from '../src/domain/risks.js'
import { collectPeople } from '../src/domain/people.js'

const now = new Date('2026-08-13T10:00:00+08:00')

test('five risk kinds', () => {
  const risks = collectRisks({
    now,
    modules: [
      { id: 'scoring', name: 'AI 评分', ownerName: null, riskFlag: true, judgment: 'shipped', evidence: { pages: 'present', apis: 'present', service: 'down' } },
    ],
    tasks: [
      { id: 't1', title: '修探活', moduleId: 'scoring', status: 'blocked', ownerName: '高', dueAt: null, thisWeek: false },
      { id: 't2', title: '本周卡', moduleId: 'scoring', status: 'doing', ownerName: '高', dueAt: '2026-08-10', thisWeek: true },
    ],
  })
  const kinds = risks.map((r) => r.kind).sort()
  assert.deepEqual(kinds, ['blocked', 'boss_risk', 'divergence', 'unassigned', 'week_overdue'].sort())
})

test('people load from module and task owners', () => {
  const people = collectPeople({
    now,
    modules: [{ id: 'scoring', ownerName: '高' }],
    tasks: [
      { id: 't1', ownerName: '高', status: 'doing', dueAt: null, thisWeek: false },
      { id: 't2', ownerName: '高', status: 'blocked', dueAt: '2026-08-10', thisWeek: true },
    ],
  })
  assert.equal(people[0].displayName, '高')
  assert.equal(people[0].moduleCount, 1)
  assert.equal(people[0].doing, 1)
  assert.equal(people[0].blocked, 1)
  assert.equal(people[0].weekOverdue, 1)
})
```

- [ ] **Step 2: Run test to verify it fails**

```bash
node --test server/tests/derived.test.mjs
```

Expected: module not found

- [ ] **Step 3: Write risks.js and people.js**

`risks.js`:

```js
import { computeDivergence } from './divergence.js'
import { isOverdue, isThisWeek } from './week.js'

export function collectRisks({ modules, tasks, now = new Date() }) {
  const rows = []
  for (const mod of modules) {
    if (!mod.ownerName) {
      rows.push({ kind: 'unassigned', moduleId: mod.id, title: `${mod.name} 未指派`, ref: { type: 'module', id: mod.id } })
    }
    if (mod.riskFlag) {
      rows.push({ kind: 'boss_risk', moduleId: mod.id, title: `${mod.name} 被老板标风险`, ref: { type: 'module', id: mod.id } })
    }
    const d = computeDivergence(mod)
    if (d) {
      rows.push({ kind: 'divergence', moduleId: mod.id, title: d.sentence, ref: { type: 'module', id: mod.id } })
    }
  }
  for (const task of tasks) {
    if (task.status === 'blocked') {
      rows.push({ kind: 'blocked', moduleId: task.moduleId, title: task.title, ref: { type: 'task', id: task.id } })
    }
    if (isThisWeek(task, now) && isOverdue(task, now)) {
      rows.push({ kind: 'week_overdue', moduleId: task.moduleId, title: task.title, ref: { type: 'task', id: task.id } })
    }
  }
  return rows
}

export function summaryCounts({ modules, tasks, now = new Date() }) {
  const risks = collectRisks({ modules, tasks, now })
  return {
    shipped: modules.filter((m) => m.judgment === 'shipped').length,
    divergence: risks.filter((r) => r.kind === 'divergence').length,
    unassigned: risks.filter((r) => r.kind === 'unassigned').length,
    weekOverdue: risks.filter((r) => r.kind === 'week_overdue').length,
    blocked: risks.filter((r) => r.kind === 'blocked').length,
  }
}
```

`people.js`:

```js
import { isOverdue, isThisWeek } from './week.js'

export function collectPeople({ modules, tasks, now = new Date() }) {
  const names = new Set()
  for (const m of modules) if (m.ownerName) names.add(m.ownerName)
  for (const t of tasks) if (t.ownerName) names.add(t.ownerName)
  return [...names].sort().map((displayName) => {
    const ownedTasks = tasks.filter((t) => t.ownerName === displayName)
    return {
      displayName,
      moduleCount: modules.filter((m) => m.ownerName === displayName).length,
      doing: ownedTasks.filter((t) => t.status === 'doing').length,
      blocked: ownedTasks.filter((t) => t.status === 'blocked').length,
      weekOverdue: ownedTasks.filter((t) => isThisWeek(t, now) && isOverdue(t, now)).length,
      tasks: ownedTasks,
    }
  })
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
node --test server/tests/derived.test.mjs
```

Expected: pass

- [ ] **Step 5: Commit**

```bash
git add server/src/domain/risks.js server/src/domain/people.js server/tests/derived.test.mjs
git commit -m "feat: derive risks, summary, people load"
```

---

### Task 7: SQLite store

**Files:**
- Create: `project management/server/src/store/db.js`
- Test: `project management/server/tests/store.test.mjs`

- [ ] **Step 1: Write the failing test**

```js
import test from 'node:test'
import assert from 'node:assert/strict'
import { openStore } from '../src/store/db.js'
import { MODULES } from '../src/domain/catalog.js'

test('seeds 11 modules once and keeps human fields across evidence write', async () => {
  const store = openStore(':memory:')
  store.seedModules(MODULES)
  store.seedModules(MODULES)
  assert.equal(store.listModules().length, 11)
  store.patchModule('scoring', { judgment: 'shipped', progressPercent: 70, ownerName: '高' })
  store.writeEvidence('scoring', {
    pages: 'present',
    apis: 'present',
    service: 'down',
    detail: { service: 'ECONNREFUSED' },
    scannedAt: '2026-08-13T01:00:00.000Z',
    lastSuccessAt: '2026-08-13T00:00:00.000Z',
    recentCommits: [],
  })
  const scoring = store.getModule('scoring')
  assert.equal(scoring.judgment, 'shipped')
  assert.equal(scoring.progressPercent, 70)
  assert.equal(scoring.evidence.service, 'down')
  const task = store.createTask({
    moduleId: 'scoring',
    title: '修评分探活',
    status: 'todo',
    ownerName: null,
    source: 'manual',
  })
  store.patchTask(task.id, { status: 'doing' })
  assert.equal(store.listTasks().length, 1)
  assert.equal(store.getTask(task.id).status, 'doing')
  store.close()
})
```

- [ ] **Step 2: Run test to verify it fails**

```bash
node --test server/tests/store.test.mjs
```

Expected: module not found

- [ ] **Step 3: Write db.js using `node:sqlite`**

```js
import { DatabaseSync } from 'node:sqlite'

function parseJson(value, fallback) {
  if (value == null || value === '') return fallback
  return JSON.parse(value)
}

export function openStore(filename) {
  const db = new DatabaseSync(filename)
  db.exec(`
    CREATE TABLE IF NOT EXISTS modules (
      id TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      group_name TEXT NOT NULL,
      judgment TEXT NOT NULL,
      progress_percent INTEGER NOT NULL,
      owner_name TEXT,
      priority TEXT NOT NULL,
      risk_flag INTEGER NOT NULL,
      risk_note TEXT NOT NULL,
      briefs_json TEXT NOT NULL,
      evidence_json TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS tasks (
      id TEXT PRIMARY KEY,
      module_id TEXT NOT NULL,
      title TEXT NOT NULL,
      status TEXT NOT NULL,
      owner_name TEXT,
      due_at TEXT,
      this_week INTEGER NOT NULL,
      priority TEXT NOT NULL,
      blocked_reason TEXT NOT NULL,
      progress_note TEXT NOT NULL,
      briefs_json TEXT NOT NULL,
      source TEXT NOT NULL,
      evidence_summary TEXT
    );
    CREATE TABLE IF NOT EXISTS changes (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      at TEXT NOT NULL,
      actor TEXT NOT NULL,
      role TEXT NOT NULL,
      entity TEXT NOT NULL,
      entity_id TEXT NOT NULL,
      summary TEXT NOT NULL
    );
  `)

  function rowToModule(row) {
    return {
      id: row.id,
      name: row.name,
      group: row.group_name,
      judgment: row.judgment,
      progressPercent: row.progress_percent,
      ownerName: row.owner_name,
      priority: row.priority,
      riskFlag: Boolean(row.risk_flag),
      riskNote: row.risk_note,
      briefs: parseJson(row.briefs_json, []),
      evidence: parseJson(row.evidence_json, {}),
    }
  }

  function rowToTask(row) {
    return {
      id: row.id,
      moduleId: row.module_id,
      title: row.title,
      status: row.status,
      ownerName: row.owner_name,
      dueAt: row.due_at,
      thisWeek: Boolean(row.this_week),
      priority: row.priority,
      blockedReason: row.blocked_reason,
      progressNote: row.progress_note,
      briefs: parseJson(row.briefs_json, []),
      source: row.source,
      evidenceSummary: row.evidence_summary,
    }
  }

  return {
    seedModules(modules) {
      const insert = db.prepare(`INSERT OR IGNORE INTO modules
        (id,name,group_name,judgment,progress_percent,owner_name,priority,risk_flag,risk_note,briefs_json,evidence_json)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)`)
      for (const m of modules) {
        insert.run(
          m.id, m.name, m.group, m.judgment, m.progressPercent, m.ownerName,
          m.priority, m.riskFlag ? 1 : 0, m.riskNote || '',
          JSON.stringify(m.briefs || []), JSON.stringify(m.evidence),
        )
      }
    },
    listModules() {
      return db.prepare('SELECT * FROM modules').all().map(rowToModule)
    },
    getModule(id) {
      const row = db.prepare('SELECT * FROM modules WHERE id=?').get(id)
      return row ? rowToModule(row) : null
    },
    patchModule(id, patch) {
      const current = this.getModule(id)
      const next = { ...current, ...patch }
      db.prepare(`UPDATE modules SET judgment=?, progress_percent=?, owner_name=?, priority=?,
        risk_flag=?, risk_note=?, briefs_json=? WHERE id=?`).run(
        next.judgment, next.progressPercent, next.ownerName, next.priority,
        next.riskFlag ? 1 : 0, next.riskNote || '', JSON.stringify(next.briefs || []), id,
      )
      return this.getModule(id)
    },
    writeEvidence(id, evidence) {
      db.prepare('UPDATE modules SET evidence_json=? WHERE id=?').run(JSON.stringify(evidence), id)
      return this.getModule(id)
    },
    appendBrief(id, brief) {
      const current = this.getModule(id)
      const briefs = [...current.briefs, brief]
      db.prepare('UPDATE modules SET briefs_json=? WHERE id=?').run(JSON.stringify(briefs), id)
      return this.getModule(id)
    },
    listTasks() {
      return db.prepare('SELECT * FROM tasks').all().map(rowToTask)
    },
    getTask(id) {
      const row = db.prepare('SELECT * FROM tasks WHERE id=?').get(id)
      return row ? rowToTask(row) : null
    },
    createTask(input) {
      const id = input.id || crypto.randomUUID()
      db.prepare(`INSERT INTO tasks
        (id,module_id,title,status,owner_name,due_at,this_week,priority,blocked_reason,progress_note,briefs_json,source,evidence_summary)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)`).run(
        id, input.moduleId, input.title, input.status || 'todo', input.ownerName || null,
        input.dueAt || null, input.thisWeek ? 1 : 0, input.priority || 'normal',
        input.blockedReason || '', input.progressNote || '',
        JSON.stringify(input.briefs || []), input.source || 'manual',
        input.evidenceSummary || null,
      )
      return this.getTask(id)
    },
    patchTask(id, patch) {
      const current = this.getTask(id)
      const next = { ...current, ...patch }
      db.prepare(`UPDATE tasks SET title=?, status=?, owner_name=?, due_at=?, this_week=?,
        priority=?, blocked_reason=?, progress_note=?, briefs_json=?, module_id=? WHERE id=?`).run(
        next.title, next.status, next.ownerName, next.dueAt, next.thisWeek ? 1 : 0,
        next.priority, next.blockedReason || '', next.progressNote || '',
        JSON.stringify(next.briefs || []), next.moduleId, id,
      )
      return this.getTask(id)
    },
    appendTaskBrief(id, brief) {
      const current = this.getTask(id)
      const briefs = [...current.briefs, brief]
      db.prepare('UPDATE tasks SET briefs_json=? WHERE id=?').run(JSON.stringify(briefs), id)
      return this.getTask(id)
    },
    logChange(entry) {
      db.prepare('INSERT INTO changes (at,actor,role,entity,entity_id,summary) VALUES (?,?,?,?,?,?)')
        .run(entry.at || new Date().toISOString(), entry.actor, entry.role, entry.entity, entry.entityId, entry.summary)
    },
    listChanges(limit = 50) {
      return db.prepare('SELECT * FROM changes ORDER BY id DESC LIMIT ?').all(limit)
    },
    snapshot() {
      return { modules: this.listModules(), tasks: this.listTasks() }
    },
    close() {
      db.close()
    },
  }
}
```

If `node:sqlite` is unavailable on this Node, switch the same API to a single JSON file written atomically (`data/cockpit.json`) but keep the method names identical so later tasks do not change.

- [ ] **Step 4: Run test to verify it passes**

```bash
node --test server/tests/store.test.mjs
```

Expected: pass

- [ ] **Step 5: Commit**

```bash
git add server/src/store/db.js server/tests/store.test.mjs
git commit -m "feat: sqlite store for modules and tasks"
```

---

### Task 8: Filesystem and HTTP probes

**Files:**
- Create: `project management/server/src/scan/fsProbe.js`
- Create: `project management/server/src/scan/httpProbe.js`
- Create: `project management/server/src/scan/gitLog.js`
- Test: `project management/server/tests/probes.test.mjs`

- [ ] **Step 1: Write the failing test**

```js
import test from 'node:test'
import assert from 'node:assert/strict'
import { mkdtempSync, writeFileSync, mkdirSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { probePaths } from '../src/scan/fsProbe.js'
import { classifyHttp } from '../src/scan/httpProbe.js'
import { readRecentCommits } from '../src/scan/gitLog.js'

test('all listed files present vs missing', () => {
  const root = mkdtempSync(join(tmpdir(), 'probe-'))
  mkdirSync(join(root, 'a'), { recursive: true })
  writeFileSync(join(root, 'a', 'x.vue'), '')
  assert.equal(probePaths(root, ['a/x.vue']).status, 'present')
  assert.equal(probePaths(root, ['a/x.vue', 'nope.js']).status, 'missing')
})

test('http classification', () => {
  assert.equal(classifyHttp({ ok: true, status: 401 }), 'present')
  assert.equal(classifyHttp({ ok: false, code: 'ECONNREFUSED' }), 'down')
  assert.equal(classifyHttp({ ok: false, code: 'ENOTFOUND' }), 'down')
  assert.equal(classifyHttp({ ok: false, timeout: true }), 'down')
  assert.equal(classifyHttp({ ok: false, unconfigured: true }), 'stale')
})

test('git missing is empty list not throw', () => {
  const root = mkdtempSync(join(tmpdir(), 'nogit-'))
  assert.deepEqual(readRecentCommits(root, ['a']), [])
})
```

- [ ] **Step 2: Run test to verify it fails**

```bash
node --test server/tests/probes.test.mjs
```

Expected: module not found

- [ ] **Step 3: Implement probes**

`fsProbe.js`:

```js
import { existsSync } from 'node:fs'
import { join } from 'node:path'

export function probePaths(repoRoot, paths) {
  const missing = (paths || []).filter((rel) => !existsSync(join(repoRoot, rel)))
  return {
    status: missing.length ? 'missing' : 'present',
    missing,
  }
}
```

`httpProbe.js`:

```js
export function classifyHttp(result) {
  if (result.unconfigured) return 'stale'
  if (result.ok) return 'present'
  return 'down'
}

export async function probeUrl(url, timeoutMs) {
  if (!url) return { ok: false, unconfigured: true }
  const ctrl = new AbortController()
  const timer = setTimeout(() => ctrl.abort(), timeoutMs)
  try {
    const res = await fetch(url, { method: 'GET', signal: ctrl.signal, redirect: 'manual' })
    return { ok: true, status: res.status }
  } catch (err) {
    return {
      ok: false,
      timeout: err.name === 'AbortError',
      code: err.cause?.code || err.code || err.name,
    }
  } finally {
    clearTimeout(timer)
  }
}

export function resolveUrl(template, bases) {
  if (!template) return ''
  return template.replace(/\{(\w+)\}/g, (_, key) => bases[key] || '')
}
```

`gitLog.js`:

```js
import { execFileSync } from 'node:child_process'

export function readRecentCommits(repoRoot, paths) {
  try {
    const out = execFileSync(
      'git',
      ['-C', repoRoot, 'log', '-5', '--pretty=format:%h %s', '--', ...(paths || [])],
      { encoding: 'utf8', timeout: 2000, stdio: ['ignore', 'pipe', 'ignore'] },
    )
    return out.split('\n').map((line) => line.trim()).filter(Boolean)
  } catch {
    return []
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
node --test server/tests/probes.test.mjs
```

Expected: pass

- [ ] **Step 5: Commit**

```bash
git add server/src/scan/fsProbe.js server/src/scan/httpProbe.js server/src/scan/gitLog.js server/tests/probes.test.mjs
git commit -m "feat: filesystem and http evidence probes"
```

---

### Task 9: Scan runner

**Files:**
- Create: `project management/server/src/scan/runner.js`
- Test: `project management/server/tests/runner.test.mjs`

- [ ] **Step 1: Write the failing test**

```js
import test from 'node:test'
import assert from 'node:assert/strict'
import { applyScanResult } from '../src/scan/runner.js'
import { openStore } from '../src/store/db.js'
import { MODULES } from '../src/domain/catalog.js'

test('scan writes evidence only and opens a scan task on present to missing', () => {
  const store = openStore(':memory:')
  store.seedModules(MODULES)
  store.patchModule('scoring', { judgment: 'shipped', progressPercent: 90 })
  store.writeEvidence('scoring', {
    pages: 'present', apis: 'present', service: 'present',
    detail: {}, scannedAt: 't0', lastSuccessAt: 't0', recentCommits: [],
  })
  const events = applyScanResult(store, {
    scoring: {
      ok: true,
      evidence: {
        pages: 'missing', apis: 'present', service: 'down',
        detail: { pages: 'ReviewReportsView.vue missing', service: 'ECONNREFUSED' },
        scannedAt: 't1', lastSuccessAt: 't0', recentCommits: [],
      },
    },
  })
  const scoring = store.getModule('scoring')
  assert.equal(scoring.judgment, 'shipped')
  assert.equal(scoring.progressPercent, 90)
  assert.equal(scoring.evidence.pages, 'missing')
  assert.equal(scoring.evidence.service, 'down')
  const created = store.listTasks().filter((t) => t.source === 'scan')
  assert.ok(created.length >= 1)
  assert.match(created[0].evidenceSummary, /pages|service/)
  assert.ok(events.some((e) => e.type === 'task.created'))
  store.close()
})

test('failed scan marks stale and keeps last success snapshot', () => {
  const store = openStore(':memory:')
  store.seedModules(MODULES)
  store.writeEvidence('admin', {
    pages: 'present', apis: 'present', service: 'present',
    detail: {}, scannedAt: 't0', lastSuccessAt: 't0', recentCommits: [],
  })
  applyScanResult(store, {
    admin: { ok: false, error: 'repo unreadable' },
  })
  const admin = store.getModule('admin')
  assert.equal(admin.evidence.pages, 'stale')
  assert.equal(admin.evidence.lastSuccessAt, 't0')
  assert.equal(admin.evidence.detail.error, 'repo unreadable')
  store.close()
})
```

- [ ] **Step 2: Run test to verify it fails**

```bash
node --test server/tests/runner.test.mjs
```

Expected: module not found

- [ ] **Step 3: Write runner.js**

```js
function channels(evidence) {
  return ['pages', 'apis', 'service'].map((key) => ({ key, value: evidence?.[key] }))
}

function openScanTaskExists(store, moduleId, key) {
  return store.listTasks().some(
    (t) => t.moduleId === moduleId && t.source === 'scan' && t.status !== 'done' && (t.evidenceSummary || '').includes(key),
  )
}

export function applyScanResult(store, results) {
  const events = []
  for (const [moduleId, result] of Object.entries(results)) {
    const current = store.getModule(moduleId)
    if (!current) continue
    if (!result.ok) {
      const stale = {
        ...current.evidence,
        pages: 'stale',
        apis: 'stale',
        service: 'stale',
        detail: { ...current.evidence.detail, error: result.error },
        scannedAt: new Date().toISOString(),
        lastSuccessAt: current.evidence.lastSuccessAt,
      }
      store.writeEvidence(moduleId, stale)
      events.push({ type: 'evidence.updated', moduleId })
      continue
    }
    const prev = current.evidence
    store.writeEvidence(moduleId, result.evidence)
    events.push({ type: 'evidence.updated', moduleId })
    for (const { key, value } of channels(result.evidence)) {
      const before = prev[key]
      const worsened = (before === 'present' && (value === 'missing' || value === 'down'))
        || (before !== 'missing' && value === 'missing')
      if (!worsened || openScanTaskExists(store, moduleId, key)) continue
      const task = store.createTask({
        moduleId,
        title: `处理 ${current.name} 证据：${key} ${before} → ${value}`,
        status: 'todo',
        source: 'scan',
        evidenceSummary: `${key}: ${before} → ${value}. ${result.evidence.detail?.[key] || ''}`,
      })
      events.push({ type: 'task.created', taskId: task.id })
    }
  }
  return events
}
```

在同一文件导出 `runScan`：

```js
import { probePaths } from './fsProbe.js'
import { probeUrl, resolveUrl, classifyHttp } from './httpProbe.js'
import { readRecentCommits } from './gitLog.js'

export async function runScan({ store, repoRoot, probes, bases, timeoutMs }) {
  const results = {}
  for (const [moduleId, probe] of Object.entries(probes)) {
    try {
      const files = probePaths(repoRoot, probe.paths)
      const api = classifyHttp(await probeUrl(resolveUrl(probe.apiUrl, bases), timeoutMs))
      const page = classifyHttp(await probeUrl(resolveUrl(probe.pageUrl, bases), timeoutMs))
      const now = new Date().toISOString()
      const current = store.getModule(moduleId)
      const okHit = files.status === 'present' || api === 'present' || page === 'present'
      results[moduleId] = {
        ok: true,
        evidence: {
          pages: files.status,
          apis: api,
          service: page,
          detail: {
            missing: files.missing,
            apiUrl: resolveUrl(probe.apiUrl, bases),
            pageUrl: resolveUrl(probe.pageUrl, bases),
          },
          scannedAt: now,
          lastSuccessAt: okHit ? now : current?.evidence?.lastSuccessAt || null,
          recentCommits: readRecentCommits(repoRoot, probe.paths),
        },
      }
    } catch (err) {
      results[moduleId] = { ok: false, error: String(err.message || err) }
    }
  }
  return applyScanResult(store, results)
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
node --test server/tests/runner.test.mjs
```

Expected: pass

- [ ] **Step 5: Commit**

```bash
git add server/src/scan/runner.js server/tests/runner.test.mjs
git commit -m "feat: apply scan results without touching human fields"
```

---

### Task 10: HTTP API + WebSocket hub

**Files:**
- Create: `project management/server/src/realtime/hub.js`
- Create: `project management/server/src/http/app.js`
- Test: `project management/server/tests/http.test.mjs`

- [ ] **Step 1: Write the failing test**

```js
import test from 'node:test'
import assert from 'node:assert/strict'
import { createApp } from '../src/http/app.js'
import { openStore } from '../src/store/db.js'
import { MODULES } from '../src/domain/catalog.js'

function listen(store, extras = {}) {
  const { server } = createApp({ store, ...extras })
  return new Promise((resolve) => {
    server.listen(0, '127.0.0.1', () => {
      const { port } = server.address()
      resolve({ server, url: `http://127.0.0.1:${port}` })
    })
  })
}

test('dev can patch progress, boss cannot; both see snapshot', async () => {
  const store = openStore(':memory:')
  store.seedModules(MODULES)
  const { server, url } = await listen(store)
  const deny = await fetch(`${url}/api/modules/scoring`, {
    method: 'PATCH',
    headers: { 'content-type': 'application/json', 'x-actor-name': '林总', 'x-actor-role': 'boss' },
    body: JSON.stringify({ judgment: 'shipped' }),
  })
  assert.equal(deny.status, 403)
  const body = await deny.json()
  assert.match(body.error, /老板不能改/)
  const ok = await fetch(`${url}/api/modules/scoring`, {
    method: 'PATCH',
    headers: { 'content-type': 'application/json', 'x-actor-name': '高', 'x-actor-role': 'dev' },
    body: JSON.stringify({ judgment: 'in_progress', progressPercent: 40 }),
  })
  assert.equal(ok.status, 200)
  const state = await (await fetch(`${url}/api/state`)).json()
  assert.equal(state.modules.find((m) => m.id === 'scoring').progressPercent, 40)
  assert.equal(state.summary.shipped, 0)
  server.close()
  store.close()
})
```

- [ ] **Step 2: Run test to verify it fails**

```bash
node --test server/tests/http.test.mjs
```

Expected: module not found

- [ ] **Step 3: Implement hub + app**

`hub.js`:

```js
import { WebSocketServer } from 'ws'

export function createHub(server) {
  const wss = new WebSocketServer({ server, path: '/ws' })
  function broadcast(message) {
    const raw = JSON.stringify(message)
    for (const client of wss.clients) {
      if (client.readyState === 1) client.send(raw)
    }
  }
  return { wss, broadcast }
}
```

`app.js`:

```js
import http from 'node:http'
import { createHub } from '../realtime/hub.js'
import { applyModulePatch, applyTaskPatch, addBrief } from '../domain/permissions.js'
import { collectRisks, summaryCounts } from '../domain/risks.js'
import { collectPeople } from '../domain/people.js'
import { selectWeekTasks } from '../domain/week.js'
import { computeDivergence } from '../domain/divergence.js'

function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = []
    req.on('data', (c) => chunks.push(c))
    req.on('end', () => {
      if (!chunks.length) return resolve({})
      try { resolve(JSON.parse(Buffer.concat(chunks).toString('utf8'))) }
      catch (err) { reject(err) }
    })
    req.on('error', reject)
  })
}

function send(res, status, payload) {
  const body = JSON.stringify(payload)
  res.writeHead(status, { 'content-type': 'application/json', 'content-length': Buffer.byteLength(body) })
  res.end(body)
}

function actorOf(req) {
  return {
    displayName: req.headers['x-actor-name'] || '',
    role: req.headers['x-actor-role'] || '',
  }
}

function withDivergence(modules) {
  return modules.map((m) => ({ ...m, divergence: computeDivergence(m) }))
}

function snapshot(store) {
  const modules = withDivergence(store.listModules())
  const tasks = store.listTasks()
  const now = new Date()
  return {
    modules,
    tasks,
    summary: summaryCounts({ modules, tasks, now }),
    risks: collectRisks({ modules, tasks, now }),
    people: collectPeople({ modules, tasks, now }),
    week: selectWeekTasks(tasks, now),
    changes: store.listChanges(),
  }
}

export function createApp({ store, runScanNow = async () => snapshot(store) }) {
  const server = http.createServer(async (req, res) => {
    try {
      const url = new URL(req.url, 'http://127.0.0.1')
      const actor = actorOf(req)
      if (req.method === 'GET' && url.pathname === '/api/state') return send(res, 200, snapshot(store))

      if (req.method === 'PATCH' && url.pathname.startsWith('/api/modules/')) {
        const id = url.pathname.split('/')[3]
        const current = store.getModule(id)
        if (!current) return send(res, 404, { error: '模块不存在' })
        const patch = await readBody(req)
        const result = applyModulePatch(actor, current, patch)
        if (!result.ok) return send(res, 403, { error: result.error })
        const module = store.patchModule(id, result.value)
        store.logChange({ actor: actor.displayName, role: actor.role, entity: 'module', entityId: id, summary: '更新模块' })
        server.broadcast?.({ type: 'state', payload: snapshot(store) })
        return send(res, 200, module)
      }

      if (req.method === 'POST' && /\/api\/modules\/[^/]+\/briefs$/.test(url.pathname)) {
        const id = url.pathname.split('/')[3]
        const result = addBrief(actor, (await readBody(req)).text)
        if (!result.ok) return send(res, 403, { error: result.error })
        store.appendBrief(id, result.value)
        store.logChange({ actor: actor.displayName, role: actor.role, entity: 'module', entityId: id, summary: '批示' })
        server.broadcast?.({ type: 'state', payload: snapshot(store) })
        return send(res, 200, store.getModule(id))
      }

      if (req.method === 'POST' && url.pathname === '/api/tasks') {
        if (actor.role !== 'dev') return send(res, 403, { error: '只有研发能新建任务' })
        const body = await readBody(req)
        const task = store.createTask({ ...body, source: 'manual' })
        store.logChange({ actor: actor.displayName, role: actor.role, entity: 'task', entityId: task.id, summary: '新建任务' })
        server.broadcast?.({ type: 'state', payload: snapshot(store) })
        return send(res, 200, task)
      }

      if (req.method === 'PATCH' && url.pathname.startsWith('/api/tasks/')) {
        const id = url.pathname.split('/')[3]
        const current = store.getTask(id)
        if (!current) return send(res, 404, { error: '任务不存在' })
        const result = applyTaskPatch(actor, current, await readBody(req))
        if (!result.ok) return send(res, 403, { error: result.error })
        const task = store.patchTask(id, result.value)
        store.logChange({ actor: actor.displayName, role: actor.role, entity: 'task', entityId: id, summary: '更新任务' })
        server.broadcast?.({ type: 'state', payload: snapshot(store) })
        return send(res, 200, task)
      }

      if (req.method === 'POST' && /\/api\/tasks\/[^/]+\/briefs$/.test(url.pathname)) {
        const id = url.pathname.split('/')[3]
        const result = addBrief(actor, (await readBody(req)).text)
        if (!result.ok) return send(res, 403, { error: result.error })
        store.appendTaskBrief(id, result.value)
        server.broadcast?.({ type: 'state', payload: snapshot(store) })
        return send(res, 200, store.getTask(id))
      }

      if (req.method === 'POST' && url.pathname === '/api/scan') {
        await runScanNow()
        server.broadcast?.({ type: 'state', payload: snapshot(store) })
        return send(res, 200, snapshot(store))
      }

      send(res, 404, { error: 'not found' })
    } catch (err) {
      send(res, 500, { error: String(err.message || err) })
    }
  })
  const hub = createHub(server)
  server.broadcast = hub.broadcast
  return { server, broadcast: hub.broadcast, snapshot: () => snapshot(store) }
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
node --test server/tests/http.test.mjs
```

Expected: pass

- [ ] **Step 5: Commit**

```bash
git add server/src/realtime/hub.js server/src/http/app.js server/tests/http.test.mjs
git commit -m "feat: permissioned http api and websocket hub"
```

---

### Task 11: Wire server process

**Files:**
- Create: `project management/server/src/http/server.js`
- Create: `project management/server/src/dev.mjs`
- Modify: `project management/package.json` if script path needs adjusting

- [ ] **Step 1: Write server.js**

```js
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { openStore } from '../store/db.js'
import { MODULES } from '../domain/catalog.js'
import { createApp } from './app.js'
import { runScan } from '../scan/runner.js'

const root = join(dirname(fileURLToPath(import.meta.url)), '../../..')
const config = JSON.parse(readFileSync(join(root, 'data/config.json'), 'utf8'))
const probes = JSON.parse(readFileSync(join(root, 'data/probes.json'), 'utf8'))
const repoRoot = join(root, config.repoRoot)
const store = openStore(join(root, 'data/cockpit.sqlite'))
store.seedModules(MODULES)

async function runScanNow() {
  await runScan({
    store,
    repoRoot,
    probes,
    bases: config.bases,
    timeoutMs: config.httpTimeoutMs,
  })
}

const { server } = createApp({ store, runScanNow })
server.listen(config.serverPort, config.listenHost, () => {
  console.log(`cockpit api http://127.0.0.1:${config.serverPort}`)
})
runScanNow().catch((err) => console.error('scan', err))
setInterval(() => runScanNow().catch((err) => console.error('scan', err)), config.scanIntervalMs)
```

- [ ] **Step 2: Write `project management/server/src/dev.mjs`**

```js
import { spawn } from 'node:child_process'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(dirname(fileURLToPath(import.meta.url)), '../..')
const kids = [
  spawn(process.execPath, ['server/src/http/server.js'], { cwd: root, stdio: 'inherit' }),
  spawn('npm', ['--prefix', 'web', 'run', 'dev'], { cwd: root, stdio: 'inherit', shell: true }),
]
function shutdown() {
  for (const kid of kids) kid.kill('SIGINT')
  process.exit(0)
}
process.on('SIGINT', shutdown)
process.on('SIGTERM', shutdown)
```

- [ ] **Step 3: Install and boot smoke**

```bash
cd "/Users/liuyixing/项目/OREP/project management"
npm --prefix server install
node server/src/http/server.js
```

Expected: process stays up, `GET http://127.0.0.1:4700/api/state` returns 11 modules. Then Ctrl+C.

- [ ] **Step 4: Commit**

```bash
git add server/src/http/server.js server/src/dev.mjs
git commit -m "feat: start cockpit api and scan loop"
```

---

### Task 12: Vue shell, labels, login

**Files:**
- Create: `project management/web/vite.config.js`
- Create: `project management/web/vitest.config.js`
- Create: `project management/web/index.html`
- Create: `project management/web/src/main.js`
- Create: `project management/web/src/App.vue`
- Create: `project management/web/src/styles.css`
- Create: `project management/web/src/lib/labels.js`
- Create: `project management/web/src/stores/session.js`
- Create: `project management/web/src/components/LoginGate.vue`
- Test: `project management/web/tests/labels.test.mjs`

- [ ] **Step 1: Write the failing test**

```js
import { describe, it, expect } from 'vitest'
import { judgmentLabel, evidenceLabel, riskLabel } from '../src/lib/labels.js'

describe('labels', () => {
  it('uses spec words including 超期', () => {
    expect(judgmentLabel('shipped')).toBe('已上线')
    expect(evidenceLabel('down')).toBe('不通')
    expect(evidenceLabel('stale')).toBe('过期')
    expect(riskLabel('week_overdue')).toBe('本周超期')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd "/Users/liuyixing/项目/OREP/project management/web"
npm install
npx vitest run tests/labels.test.mjs
```

Expected: fail / module not found

- [ ] **Step 3: Implement labels + Vite + login**

`labels.js` maps every enum in the spec to Chinese, including `超期` never `逾期`.

`vite.config.js`: Vue plugin, `server.proxy` `/api` and `/ws` to `http://127.0.0.1:4700`, `ws: true`.

`vitest.config.js`: `environment: 'happy-dom'`.

`styles.css`: light workbench. Tokens only: `--bg: #f4f1ea`, `--paper: #fffaf3`, `--ink: #1c1915`, `--muted: #6b645b`, `--line: #ddd4c6`, `--warn: #8a4b12`, `--danger: #8f2d2d`, `--ok: #2f5d3a`. No dark glass, no rainbow KPI. Body 14px. Buttons min 40×40.

`LoginGate.vue`: display name input, two buttons 老板 / 研发, persist to `sessionStorage` via Pinia `session` store (`displayName`, `role`). No password.

`App.vue`: if no session show login, else router-view.

- [ ] **Step 4: Run test to verify it passes**

```bash
npx vitest run tests/labels.test.mjs
```

Expected: pass

- [ ] **Step 5: Commit**

```bash
git add web
git commit -m "feat: cockpit web shell and login"
```

---

### Task 13: Client, store, reconnect banner

**Files:**
- Create: `project management/web/src/api/client.js`
- Create: `project management/web/src/stores/cockpit.js`
- Create: `project management/web/src/components/NoticeBar.vue`
- Test: `project management/web/tests/client.test.mjs`

- [ ] **Step 1: Write the failing test**

```js
import { describe, it, expect } from 'vitest'
import { actorHeaders } from '../src/api/client.js'

describe('actor headers', () => {
  it('sends name and role', () => {
    expect(actorHeaders({ displayName: '林总', role: 'boss' })).toEqual({
      'x-actor-name': '林总',
      'x-actor-role': 'boss',
    })
  })
})
```

- [ ] **Step 2: Implement client and store**

`client.js`: `getState`, `patchModule`, `patchTask`, `createTask`, `addModuleBrief`, `addTaskBrief`, `triggerScan`. All attach actor headers. On 403 parse `{ error }` and throw `PermissionError`.

`cockpit.js` Pinia store:

- `state`, `notice`, `live: 'live' | 'reconnecting'`
- `load()` GET `/api/state`
- `connect()` WebSocket to `ws://${location.host}/ws`; `onmessage` replace or patch `state`; `onclose` set `reconnecting`, disable writes, retry 1s, on open `load()` without tearing down the current drawer id
- actions wrap API calls, set `notice` on permission error or `已被${name}覆盖` if `updatedAt` changes under you (compare `changes[0]`)

`NoticeBar.vue` shows `notice` and `实时已断开，正在重连` when `live !== 'live'`. Hide write controls when reconnecting.

- [ ] **Step 3: Run test**

```bash
npx vitest run tests/client.test.mjs
```

Expected: pass

- [ ] **Step 4: Commit**

```bash
git add web/src/api/client.js web/src/stores/cockpit.js web/src/components/NoticeBar.vue web/tests/client.test.mjs
git commit -m "feat: api client and live reconnect store"
```

---

### Task 14: App shell and overview

**Files:**
- Create: `project management/web/src/router.js`
- Create: `project management/web/src/components/AppShell.vue`
- Create: `project management/web/src/components/SummaryStrip.vue`
- Create: `project management/web/src/components/ModuleCard.vue`
- Create: `project management/web/src/views/OverviewView.vue`
- Create: `project management/web/src/lib/derived.js`
- Test: `project management/web/tests/overview.test.mjs`

- [ ] **Step 1: Write the failing test**

```js
import { describe, it, expect } from 'vitest'
import { groupModules, cardAlerts } from '../src/lib/derived.js'

describe('overview grouping', () => {
  it('keeps four groups and fight alert', () => {
    const groups = groupModules([
      { id: 'student', group: '两端工作台' },
      { id: 'scoring', group: '智能与裁决', judgment: 'shipped', evidence: { service: 'down' }, divergence: { sentence: 'x' } },
    ])
    expect(groups.map((g) => g.name)).toEqual(['两端工作台', '备赛闭环', '智能与裁决', '治理与学情'])
    expect(cardAlerts({
      divergence: { sentence: '负责人标「已上线」，但评分服务探活失败。' },
      tasks: [{ status: 'blocked' }],
      weekOverdueCount: 1,
      unreadBrief: true,
    })).toContain('判断和证据不一致')
  })
})
```

- [ ] **Step 2: Implement overview**

`AppShell.vue` nav: 产品全貌 / 本周交付 / 风险 / 人员. Header: 「竞赛大脑驾驶舱」、登录名、角色、「立即扫描」、`证据 N 秒前更新`. No 任务 in primary nav. Add a text link 「任务总表」 in the header corner only.

`SummaryStrip.vue`: five numbers from `state.summary` (`shipped`, `divergence`, `unassigned`, `weekOverdue`, `blocked`) labeled 已上线 / 打架 / 未指派 / 本周超期 / 阻塞. Click → `/risks`, `/week`, `/people` as specified.

`ModuleCard.vue` four layers. Boss inline: owner select (free text + apply), 标风险, 写批示. Dev inline: judgment `<select>`, progress number. Card body `tabindex="0"` Enter → `/modules/:id`. Stop propagation on controls.

`OverviewView.vue` renders groups in spec order.

Enrich each module on the client with `computeDivergence` copied into `web/src/lib/divergence.js` (same function as server; do not import from server).

- [ ] **Step 3: Run test**

```bash
npx vitest run tests/overview.test.mjs
```

Expected: pass

- [ ] **Step 4: Commit**

```bash
git add web/src/router.js web/src/components web/src/views/OverviewView.vue web/src/lib/derived.js web/src/lib/divergence.js web/tests/overview.test.mjs
git commit -m "feat: overview module map"
```

---

### Task 15: Module detail, task table, drawer

**Files:**
- Create: `project management/web/src/views/ModuleDetailView.vue`
- Create: `project management/web/src/components/EvidencePanel.vue`
- Create: `project management/web/src/components/TaskTable.vue`
- Create: `project management/web/src/components/TaskDrawer.vue`

- [ ] **Step 1: Implement detail**

Left: judgment, progress, owner, priority, risk, briefs timeline.  
Right: `EvidencePanel` read-only (paths, urls, last success, failure, commits).  
Below: `TaskTable` unfinished first. Row click opens `TaskDrawer`.

`TaskDrawer.vue`: fields by role. Scan `evidenceSummary` always disabled. Esc emits close. If store reports remote update on this id, show 「刚刚由某某更新」 and replace fields. Create-task form only when `role=dev`.

- [ ] **Step 2: Manual route check after `npm run dev`**

Open `/modules/scoring`. Evidence panel has no inputs. Esc closes drawer.

- [ ] **Step 3: Commit**

```bash
git add web/src/views/ModuleDetailView.vue web/src/components/EvidencePanel.vue web/src/components/TaskTable.vue web/src/components/TaskDrawer.vue
git commit -m "feat: module detail and task drawer"
```

---

### Task 16: Week, risks, people, task inbox

**Files:**
- Create: `project management/web/src/views/WeekView.vue`
- Create: `project management/web/src/views/RisksView.vue`
- Create: `project management/web/src/views/PeopleView.vue`
- Create: `project management/web/src/views/TasksView.vue`

- [ ] **Step 1: Implement the four list pages**

Shared layout: left filters, center `TaskTable` or risk/people cards, right same `TaskDrawer`.

- Week: group by module; 超期 rows first; use `state.week`
- Risks: one list, tag `阻塞 / 打架 / 无人认领 / 老板标风险 / 本周超期`; click module risk → `/modules/:id`, task risk → open drawer
- People: one card per person with moduleCount / doing / blocked / weekOverdue; click → filter their tasks
- Tasks: views 全部 / 我的 / 阻塞 / 待指派 / 老板批示；route `/tasks?view=`

Same task id everywhere. Do not clone task objects for display beyond mapping.

- [ ] **Step 2: Add routes**

`/`, `/modules/:id`, `/week`, `/risks`, `/people`, `/tasks`

- [ ] **Step 3: Commit**

```bash
git add web/src/views/WeekView.vue web/src/views/RisksView.vue web/src/views/PeopleView.vue web/src/views/TasksView.vue web/src/router.js
git commit -m "feat: week risks people and task inbox"
```

---

### Task 17: Keyboard, empty, error copy, start script polish

**Files:**
- Modify: `project management/web/src/components/ModuleCard.vue`
- Modify: `project management/web/src/components/TaskDrawer.vue`
- Modify: `project management/web/src/components/NoticeBar.vue`
- Modify: `project management/README.md`
- Modify: `project management/server/src/dev.mjs` if needed

- [ ] **Step 1: Keyboard and empty copy**

- Module cards in a list, Tab moves, Enter opens detail
- Drawer listens `Escape`
- Unassigned owner renders 「未指派」, never a fake name
- 403 shows the server `error` string under the control
- `prefers-reduced-motion: reduce` disables transitions in `styles.css`
- README documents two-browser permission test and `data/config.json`

- [ ] **Step 2: Commit**

```bash
git add web/src project\ management/README.md
git commit -m "feat: keyboard empty and error states"
```

(If pathspec fails, `git add -A` inside `project management`.)

---

### Task 18: Spec acceptance

**Files:**
- None required unless a gap appears

- [ ] **Step 1: Run automated tests**

```bash
cd "/Users/liuyixing/项目/OREP/project management"
npm run test:server
npm --prefix web test
```

Expected: all pass

- [ ] **Step 2: Manual spec checklist**

1. Two browsers: boss changes owner/brief, dev changes progress; other side updates within 2 seconds; crossed forbidden writes show the rule.
2. Stop nothing / stop scoring (`8090`): AI 评分 evidence becomes 不通, judgment unchanged, fight sentence appears.
3. Create a 本周超期 task, a blocked task, clear one module owner: 风险 shows all three; homepage counts match.
4. Edit a task in module detail; open 人员; same status.
5. Kill API process: banner 「实时已断开，正在重连」, writes disabled, no green evidence flash.
6. Keyboard: overview → detail → drawer → Esc.
7. `git -C "/Users/liuyixing/项目/OREP" status` is not a repo; confirm no files added under `frontend/` or `backend/`.

- [ ] **Step 3: Fix any miss then commit**

```bash
git add -A
git commit -m "fix: close spec acceptance gaps"
```

If nothing to fix, skip the commit.

---

## Self-review

**Spec coverage**

| Spec section | Tasks |
|--------------|--------|
| 11 modules, four groups, homepage first | 2, 14 |
| Dual human/system fields, no auto rewrite of judgment | 4, 7, 9 |
| Permission table B | 3, 10, 12, 14, 15 |
| Week / 风险 / 人员 / 任务总表, one task record | 5, 6, 16 |
| Scanner 30s, stale, down ≠ missing, auto scan tasks | 8, 9, 11 |
| WebSocket, reconnect, last-write-wins, split brief/progress | 10, 13 |
| Visual: light, 超期, no fake data | 12, 14, 17 |
| Isolated `project management/` | 1, 18 |
| Acceptance 1–7 | 18 |

**Type names locked:** `judgment`, `progressPercent`, `ownerName`, `riskFlag`, `thisWeek`, `week_overdue`, `evidenceSummary`, `applyModulePatch`, `applyTaskPatch`, `applyScanResult`, `summaryCounts`. UI must say **超期**, never 逾期.

**Out of scope stays out:** no SSO, no teacher-portal menu, no mobile pass, no writing into OREP frontend/backend.
