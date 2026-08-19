import { expect, test } from '@playwright/test'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const projectTeamPath = path.resolve(__dirname, '../src/views/ProjectTeam.vue')
const trainingPlanPath = path.resolve(__dirname, '../src/modules/training/TrainingPlan.vue')

test('task management shell uses 40px top padding', () => {
  const source = fs.readFileSync(projectTeamPath, 'utf8')
  expect(source).toMatch(/padding-top:\s*40px/)
  expect(source).toMatch(/class="student-page task-management-shell/)
})

test('project team merges locked training schedule and blocks navigation', () => {
  const source = fs.readFileSync(projectTeamPath, 'utf8')
  expect(source).toContain('trainingSchedule')
  expect(source).toContain('createLockedTrainingWorkItem')
  expect(source).toContain('isLockedWorkItem')
  expect(source).toContain("ElMessage.warning(lockedUnlockMessage(item))")
  expect(source).toContain('aria-disabled')
  expect(source).toContain('待教师发布')
  expect(source).toContain('未开放')
  expect(source).toContain('已超期')
  expect(source).not.toMatch(/已逾期/)
})

test('training plan renders locked day shells without navigation', () => {
  const source = fs.readFileSync(trainingPlanPath, 'utf8')
  expect(source).toContain('isDayLocked')
  expect(source).toContain('task-item is-locked')
  expect(source).toContain('aria-disabled="true"')
  expect(source).toContain('暂不可进入')
  expect(source).toContain('00:00开放')
})
