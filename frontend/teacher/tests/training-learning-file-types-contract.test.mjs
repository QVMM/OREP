import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const read = relativePath => readFileSync(
  new URL(relativePath, import.meta.url),
  'utf8'
)

const editorSource = read('../src/components/training/TrainingLearningResourcesEditor.vue')
const studentSectionSource = read('../../user/src/modules/training/components/TrainingLearningSection.vue')
const previewSource = read('../../user/src/components/FilePreview.vue')
const serviceSource = read('../../../backend/src/main/java/com/orep/backend/service/TrainingDayLearningResourceService.java')
const downloadSource = read('../../../backend/src/main/java/com/orep/backend/controller/TrainingLearningResourceDownloadController.java')

const supportedExtensions = [
  'mp4', 'webm', 'mov',
  'mp3', 'wav', 'm4a',
  'pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx',
  'csv', 'txt', 'md',
  'jpg', 'jpeg', 'png', 'gif', 'webp',
  'zip', 'rar', '7z'
]

test('teacher selector and backend whitelist cover the same learning file extensions', () => {
  for (const extension of supportedExtensions) {
    assert.ok(editorSource.includes(`'.${extension}'`), `教师端缺少 .${extension}`)
    assert.match(serviceSource, new RegExp(`"${extension}"`), `后端缺少 ${extension}`)
  }
  assert.match(editorSource, /上传视频或资料/)
  assert.match(editorSource, /Excel、CSV、文本、图片及 ZIP\/RAR\/7Z/)
})

test('backend validates content and derives MIME instead of trusting browser MIME', () => {
  assert.match(serviceSource, /validateFileSignature\(file, extension\)/)
  assert.match(serviceSource, /safeMime\(extension\)/)
  assert.doesNotMatch(serviceSource, /safeMime\(file\.getContentType\(\), extension\)/)
  assert.match(serviceSource, /validateOoxmlPackage\(file, extension\)/)
  assert.match(serviceSource, /case "xlsx" -> "application\/vnd\.openxmlformats-officedocument\.spreadsheetml\.sheet"/)
})

test('student preview supports CSV and download-only archives are explicit', () => {
  assert.match(previewSource, /\['txt', 'csv'\]\.includes\(e\)/)
  assert.match(previewSource, /DOMPurify\.sanitize\(marked\(text\)\)/)
  assert.match(studentSectionSource, /DOWNLOAD_ONLY_EXTENSIONS = new Set\(\['zip', 'rar', '7z'\]\)/)
  assert.match(studentSectionSource, />下载资料<\/a>/)
  assert.match(downloadSource, /ContentDisposition\.attachment\(\)/)
})
