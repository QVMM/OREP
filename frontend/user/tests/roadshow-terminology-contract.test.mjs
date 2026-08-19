import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const files = [
  'src/views/MyRecordings.vue',
  'src/views/MeetingReplay.vue',
  'src/views/MeetingRoom.vue',
  'src/components/AudioRecorder.vue',
  'src/components/ai-score/AiScoreControl.vue',
  'src/components/ai-score/AiScoreStartDialog.vue',
  'src/components/ai-score/ScoreSummaryHeader.vue',
  'src/components/ai-score/report/AiScoreReportShell.vue',
  'src/components/ai-score/report/AiScoreSummaryChrome.vue',
]

test('路演直接关联界面不再使用旧入口术语', async () => {
  const contents = await Promise.all(
    files.map(file => readFile(new URL(`../${file}`, import.meta.url), 'utf8'))
  )
  const source = contents.join('\n')
  const legacyPatterns = [
    /在线会议室/,
    />\s*会议聊天\s*</,
    />\s*离开会议\s*</,
    /会议室录制/,
    /返回会议/,
    /返回会议回放/,
    />\s*会议回放\s*</,
  ]

  for (const pattern of legacyPatterns) {
    assert.doesNotMatch(source, pattern)
  }
})
