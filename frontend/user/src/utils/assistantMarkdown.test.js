import assert from 'node:assert/strict'
import test from 'node:test'
import {
  formatAssistantMarkdown,
  enhanceKeyboardShortcuts,
} from './assistantMarkdown.js'

test('keyboard shortcuts render as kbd keycaps', () => {
  const html = formatAssistantMarkdown('按 `Ctrl+K` 打开命令面板，或按 `Esc` 关闭。')
  assert.match(html, /xq-kbd/)
  assert.match(html, /Ctrl|⌘|⌃/)
  assert.match(html, /Esc/)
})

test('gfm tables get scroll wrapper', () => {
  const md = `| 事项 | 优先级 |\n| --- | --- |\n| 改开场 | P0 |\n| 练路演 | P1 |`
  const html = formatAssistantMarkdown(md)
  assert.match(html, /xq-table-wrap/)
  assert.match(html, /<table>/)
  assert.match(html, /改开场/)
})

test('code block includes copy button svg toolbar', () => {
  const md = '```js\nconst x = 1\n```'
  const html = formatAssistantMarkdown(md)
  assert.match(html, /xq-code-block/)
  assert.match(html, /data-xq-copy/)
  assert.match(html, /xq-code-bar/)
  assert.match(html, /<svg/)
})

test('enhanceKeyboardShortcuts leaves code fences alone', () => {
  const input = '<pre><code>Ctrl+K is not a shortcut here</code></pre><p>Press Ctrl+K</p>'
  const out = enhanceKeyboardShortcuts(input)
  assert.match(out, /<pre><code>Ctrl\+K is not a shortcut here<\/code><\/pre>/)
  assert.match(out, /xq-kbd/)
})
