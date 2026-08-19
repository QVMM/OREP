import { expect, test } from '@playwright/test'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const trainingPlanPath = path.resolve(__dirname, '../src/modules/training/TrainingPlan.vue')

test('training plan prioritizes mutually exclusive student task states', () => {
  const source = fs.readFileSync(trainingPlanPath, 'utf8')

  expect(source).toContain("const activeFilter = ref('current')")
  expect(source).toContain("{ key: 'current', label: '待完成'")
  expect(source).toContain("{ key: 'completed', label: '已提交'")
  expect(source).toContain("{ key: 'upcoming', label: '稍后开始'")
  // 待完成：本周今天+未来；不含过去补交、不含 review
  expect(source).toContain("return ['active', 'revision', 'upcoming'].includes(tone)")
  expect(source).toContain('isInThisCalendarWeek')
  expect(source).toContain('isUnpublishedDay')
  expect(source).toContain('is-future-dim')
  expect(source).toMatch(/filter === 'completed'\) return \['complete', 'review'\]\.includes\(tone\)/)
  // 待完成列表不含 review 态
  expect(source).not.toContain("return ['active', 'revision', 'overdue', 'review']")
})

test('training plan filter is an accessible pressed-button group', () => {
  const source = fs.readFileSync(trainingPlanPath, 'utf8')

  expect(source).toContain('role="group"')
  expect(source).toContain(':aria-pressed="activeFilter === item.key"')
  expect(source).toContain('class="tasks-filter__count"')
  expect(source).toContain('.tasks-filter button:focus-visible')
})

test('training cycle summary aligns to the page edge on desktop', () => {
  const source = fs.readFileSync(trainingPlanPath, 'utf8')

  expect(source).toMatch(/\.tasks-cycle-badge\s*\{[^}]*margin-left:\s*auto;[^}]*text-align:\s*right;/s)
  expect(source).toMatch(/@media \(max-width: 760px\)[\s\S]*\.tasks-cycle-badge\s*\{[^}]*text-align:\s*left;/)
})

test('training plan toolbar provides functional task search', () => {
  const source = fs.readFileSync(trainingPlanPath, 'utf8')

  expect(source).toContain('class="tasks-toolbar__controls"')
  expect(source).toContain('class="tasks-search"')
  expect(source).toContain('aria-label="搜索训练任务"')
  expect(source).toContain('matchesTaskSearch(task, day)')
  expect(source).toContain('matchesDaySearch(day)')
  expect(source).toContain('没有找到“${taskSearch.value.trim()}”')
  expect(source).toContain('当前显示 <strong>{{ visibleTaskCount }}</strong> 项')
  expect(source).toContain('const visibleTaskCount = computed')
})

test('learning preparation is presented as part of the day task card', () => {
  const source = fs.readFileSync(trainingPlanPath, 'utf8')

  expect(source).toContain("class=\"task-items\" :class=\"{ 'has-learning': hasLearning(day) }\"")
  expect(source).toContain('class="task-learning-preview"')
  expect(source).toContain('learningPreviewTitle(day)')
  expect(source).toContain('videoResourceCount')
  expect(source).toContain('completedLearningCount')
  expect(source).toContain('estimatedLearningMinutes')
  expect(source).not.toContain('tasks-day__learning-summary')
  expect(source).toContain('class="task-learning-preview__ring"')
  expect(source).toContain('conic-gradient(')
  expect(source).not.toContain('<span>任务准备</span>')
  expect(source).not.toContain('task-learning-preview__track')
})
