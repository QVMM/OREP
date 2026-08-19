import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const read = (relativePath) => readFileSync(
  new URL(relativePath, import.meta.url),
  'utf8'
)

const uploadForm = read('../src/components/ai-score/VideoScoreUploadForm.vue')
const uploadApi = read('../src/utils/aiScoreUpload.js')
const viteConfig = read('../vite.config.js')
const applicationConfig = read('../../../backend/src/main/resources/application.yml')
const preprocessService = read('../../../backend/src/main/java/com/orep/backend/service/AiScoreMediaPreprocessService.java')
const mediaAssetService = read('../../../backend/src/main/java/com/orep/backend/service/AiScoreMediaAssetService.java')
const uploadController = read('../../../backend/src/main/java/com/orep/backend/controller/AiScoreUploadController.java')

const nginxConfigs = [
  '../../../deploy/nginx/nginx.conf',
  '../../../deploy/nginx.conf',
  '../../../deploy/nginx.prod.conf',
  '../../../cloudrun/config/nginx.conf.template',
  '../../../cloudrun/release/orep-cloudrun/config/nginx.conf.template',
  '../../../dockerrun/config/nginx.conf.template',
  '../../../windowsrun/config/nginx-orep.conf.template',
  '../nginx-default.conf'
]

test('AI score upload enforces the 5GB video and material limits before upload', () => {
  assert.match(uploadForm, /const MAX_VIDEO_BYTES = 5 \* 1024 \* 1024 \* 1024/)
  assert.match(uploadForm, /const MAX_MATERIAL_BYTES = 200 \* 1024 \* 1024/)
  assert.match(uploadForm, /const MAX_TOTAL_MATERIAL_BYTES = 1 \* 1024 \* 1024 \* 1024/)
  assert.match(uploadForm, /路演视频最大5GB，请压缩后上传/)
  assert.match(uploadForm, /单个佐证材料最大200MB/)
  assert.match(uploadForm, /佐证材料合计最大1GB/)
  assert.doesNotMatch(uploadForm, /createAiScorePreprocessJob/)
  assert.doesNotMatch(uploadForm, /needsPreprocess/)
})

test('frontend upload clients use the unified two-hour timeout', () => {
  assert.match(uploadApi, /const AI_SCORE_UPLOAD_TIMEOUT_MS = 2 \* 60 \* 60 \* 1000/)
  assert.match(viteConfig, /const longUploadTimeoutMs = 2 \* 60 \* 60 \* 1000/)
})

test('Spring and preprocessing use a 5GB file limit with a 7GB request envelope', () => {
  assert.match(applicationConfig, /max-http-form-post-size: \$\{SERVER_TOMCAT_MAX_HTTP_FORM_POST_SIZE:7GB\}/)
  assert.match(applicationConfig, /max-file-size: \$\{SPRING_SERVLET_MULTIPART_MAX_FILE_SIZE:5GB\}/)
  assert.match(applicationConfig, /max-request-size: \$\{SPRING_SERVLET_MULTIPART_MAX_REQUEST_SIZE:7GB\}/)
  assert.match(preprocessService, /MAX_SOURCE_VIDEO_BYTES = 5L \* 1024 \* 1024 \* 1024/)
  assert.match(preprocessService, /源视频超过 5GB/)
  assert.match(mediaAssetService, /MAX_TOTAL_MATERIAL_BYTES = 1L \* 1024 \* 1024 \* 1024/)
  assert.match(mediaAssetService, /佐证材料合计最大1GB/)
  assert.match(uploadController, /mediaAssetService\.validateUploadBatch\(video, materials\)/)
})

test('every active nginx config streams AI score uploads with the 7GB envelope', () => {
  for (const configPath of nginxConfigs) {
    const source = read(configPath)
    const block = source.match(/location \/api\/ai-score\/\s*\{[^}]*\}/s)?.[0]
    assert.ok(block, `${configPath} 缺少 /api/ai-score/ 专用代理`)
    assert.match(block, /client_max_body_size 7G;/, configPath)
    assert.match(block, /client_body_timeout 7200s;/, configPath)
    assert.match(block, /proxy_http_version 1\.1;/, configPath)
    assert.match(block, /proxy_request_buffering off;/, configPath)
    assert.match(block, /proxy_read_timeout 7200s;/, configPath)
    assert.match(block, /proxy_send_timeout 7200s;/, configPath)
  }
})
