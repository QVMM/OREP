import { expect, test } from '@playwright/test'
import { readdirSync, readFileSync } from 'node:fs'
import { extname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const repoRoot = resolve(fileURLToPath(new URL('.', import.meta.url)), '../../..')
const productionRoots = [
  'frontend/user/src',
  'frontend/admin/src',
  'frontend/teacher/src',
  'backend/src/main',
  'ai-scoring/app',
  'recording-bot/src',
  'signaling'
]
const textExtensions = new Set([
  '.css',
  '.html',
  '.java',
  '.js',
  '.json',
  '.jsx',
  '.properties',
  '.py',
  '.scss',
  '.ts',
  '.tsx',
  '.vue',
  '.yaml',
  '.yml'
])

function collectForbiddenCopy(relativeRoot) {
  const absoluteRoot = resolve(repoRoot, relativeRoot)
  const matches = []

  function visit(directory) {
    for (const entry of readdirSync(directory, { withFileTypes: true })) {
      if (entry.name === 'node_modules' || entry.name === 'dist' || entry.name === 'target') continue
      const absolutePath = resolve(directory, entry.name)
      if (entry.isDirectory()) {
        visit(absolutePath)
        continue
      }
      if (!textExtensions.has(extname(entry.name))) continue

      readFileSync(absolutePath, 'utf8').split(/\r?\n/).forEach((line, index) => {
        if (line.includes('逾期')) {
          matches.push(`${relativeRoot}/${absolutePath.slice(absoluteRoot.length + 1)}:${index + 1}`)
        }
      })
    }
  }

  visit(absoluteRoot)
  return matches
}

test('生产界面统一使用“超期”术语', () => {
  const matches = productionRoots.flatMap(collectForbiddenCopy)
  expect(matches, `仍包含禁用文案：\n${matches.join('\n')}`).toEqual([])
})
