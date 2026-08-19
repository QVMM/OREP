import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const source = readFileSync(new URL('./OnlineMeeting.vue', import.meta.url), 'utf8')

test('successful meeting join navigates in the current tab so browsers cannot block it as a popup', () => {
  assert.match(source, /router\.push\(`\/meeting\/\$\{meetingId\}`\)/)
  assert.doesNotMatch(source, /window\.open\(routeData\.href/)
})
