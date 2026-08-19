import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const workspaceSource = readFileSync(
  new URL('../src/components/resource-center/ResourceCenterWorkspace.vue', import.meta.url),
  'utf8'
)
const folderSource = readFileSync(
  new URL('../src/components/resource-center/ResourceFolderBadge.vue', import.meta.url),
  'utf8'
)
const thumbnailSource = readFileSync(
  new URL('../src/components/resource-center/ResourceFileThumbnail.vue', import.meta.url),
  'utf8'
)
const previewSource = readFileSync(
  new URL('../src/components/FilePreview.vue', import.meta.url),
  'utf8'
)
const scriptListSource = readFileSync(
  new URL('../src/views/ScriptList.vue', import.meta.url),
  'utf8'
)
const clientSource = readFileSync(
  new URL('../src/services/resourceCenterClient.js', import.meta.url),
  'utf8'
)

test('resource center accepts inspire office smart docs', () => {
  const service = readFileSync(
    new URL('../../../backend/src/main/java/com/orep/backend/service/ResourceCenterService.java', import.meta.url),
    'utf8'
  )
  assert.match(service, /"sdoc"/)
  assert.match(workspaceSource, /'\.sdoc'/)
})

test('resource center uses the dedicated Finder workspace and current team scope', () => {
  assert.match(scriptListSource, /<ResourceCenterWorkspace[\s\S]*:team-id="activeTeamId"[\s\S]*:team-name="activeTeamName"/)
  assert.match(workspaceSource, /grid-template-columns:\s*minmax\(520px,\s*1fr\)\s*clamp\(360px,\s*38vw,\s*560px\)/)
  assert.match(clientSource, /get\('\/api\/resource-center'[\s\S]*params:\s*\{\s*teamId\s*\}/)
  assert.doesNotMatch(workspaceSource, /TEAM RESOURCE OS/)
})

test('resource center inherits the global page title and page margins', () => {
  assert.match(workspaceSource, /<h1 class="workspace-page-title">资源中心<\/h1>/)
  assert.doesNotMatch(workspaceSource, /\.resource-center__heading h1\s*\{[^}]*font-size:/)
  assert.match(scriptListSource, /\.prep-workbench\.mode-materials\s*\{[^}]*padding:\s*0;/)
  assert.doesNotMatch(scriptListSource, /\.prep-workbench\.mode-materials\s*\{[^}]*padding:\s*0 0 var\(--ds-space-6/)
})

test('folder badge fans three document covers and accepts file drops', () => {
  assert.match(folderSource, /displayCovers/)
  assert.match(folderSource, /slice\(0,\s*3\)/)
  assert.doesNotMatch(folderSource, /fallback-1/)
  assert.match(folderSource, /<ResourceFileThumbnail\s+:file="cover"/)
  assert.match(folderSource, /is-layer-1/)
  assert.match(folderSource, /--teaser-width:\s*60px/)
  assert.match(folderSource, /--preview-width:\s*112px/)
  assert.match(folderSource, /translateY\(-20px\)/)
  assert.match(folderSource, /@drop\.prevent="onDrop"/)
  assert.match(folderSource, /emit\('drop-file'/)
})

test('folder shell opens as physical back, file and front layers', () => {
  assert.match(folderSource, /resource-folder__back[\s\S]*v-for="\(cover,\s*index\)\s+in\s+displayCovers"[\s\S]*resource-folder__front/)
  assert.doesNotMatch(folderSource, /resource-folder__shell/)
  assert.match(folderSource, /\.resource-folder__back\s*\{[\s\S]*z-index:\s*1/)
  assert.match(folderSource, /\.resource-folder__front\s*\{[\s\S]*z-index:\s*5/)
  assert.match(folderSource, /transform-origin:\s*50%\s+100%/)
  assert.match(folderSource, /translateY\(7px\)\s+rotateX\(-18deg\)/)
})

test('public folder keeps neutral semantics with a stronger open state', () => {
  assert.match(folderSource, /\.resource-folder\.is-public\s+\.resource-folder__back path\s*\{[\s\S]*fill:\s*#e9ecf2/)
  assert.match(folderSource, /\.resource-folder\.is-public\s+\.resource-folder__front path\s*\{[\s\S]*fill:\s*#aeb6c5/)
  assert.match(folderSource, /translateY\(9px\)\s+rotateX\(-23deg\)/)
  assert.match(folderSource, /\.resource-folder\.is-public:hover\s+\.resource-folder__front path[\s\S]*fill:\s*#9da7b8/)
})

test('folder covers lazily render real PDF, image and video thumbnails with caching', () => {
  assert.match(thumbnailSource, /IntersectionObserver/)
  assert.match(thumbnailSource, /__orepResourceThumbnailCache/)
  assert.match(thumbnailSource, /renderPdfThumbnail/)
  assert.match(thumbnailSource, /getPage\(1\)/)
  assert.match(thumbnailSource, /renderVideoThumbnail/)
  assert.match(thumbnailSource, /withAuthMediaUrl/)
  assert.match(thumbnailSource, /resource-file-thumbnail__fallback/)
})

test('file preview is click-driven with keyboard and immersive fallbacks', () => {
  assert.match(workspaceSource, /@click="selectFile\(file\)"/)
  assert.match(workspaceSource, /@keydown\.enter\.prevent="selectFile\(file\)"/)
  assert.match(workspaceSource, /@keydown\.space\.prevent="selectFile\(file\)"/)
  assert.match(workspaceSource, /@dblclick="openImmersivePreview\(file\)"/)
  assert.doesNotMatch(workspaceSource, /@mouseenter="schedulePreview\(file\)"/)
  assert.doesNotMatch(workspaceSource, /hoveredFile|hoverTimer|schedulePreview|cancelScheduledPreview/)
  assert.match(workspaceSource, /点击文件切换预览/)
})

test('file moving has drag and menu paths with optimistic rollback', () => {
  assert.match(workspaceSource, /:draggable="!file\.public"/)
  assert.match(workspaceSource, /@dragstart="startFileDrag\(\$event,\s*file\)"/)
  assert.match(workspaceSource, /moveFromSelect/)
  assert.match(workspaceSource, /teamFiles\.value\s*=\s*previousFiles/)
  assert.match(clientSource, /patch\(`\/api\/resource-center\/files\/\$\{resourceId\}\/folder`/)
})

test('public resources are visibly read-only and cannot be moved', () => {
  assert.match(workspaceSource, /<ResourceFolderBadge[\s\S]*:folder="publicFolder"[\s\S]*readonly/)
  assert.match(workspaceSource, /v-if="!file\.public"/)
  assert.match(workspaceSource, /公共只读/)
  assert.doesNotMatch(workspaceSource, /resource-file-row__readonly/)
})

test('file table action heading follows the right-aligned action column', () => {
  assert.match(
    workspaceSource,
    /\.resource-file-table__head span:last-child\s*\{[^}]*justify-self:\s*end;[^}]*padding-right:\s*10px;/,
  )
})

test('shared file preview supports inline rendering and reloads on URL changes', () => {
  assert.match(previewSource, /inline:\s*\{\s*type:\s*Boolean/)
  assert.match(previewSource, /fp-overlay--inline/)
  assert.match(previewSource, /watch\(\s*\(\)\s*=>\s*\[props\.visible,\s*props\.fileUrl\]/)
  assert.match(previewSource, /\{\s*immediate:\s*true\s*\}/)
})

test('PPT preview measures its container and prevents horizontal overflow', () => {
  assert.match(previewSource, /ref="pptContainerRef"/)
  assert.match(previewSource, /:options="pptxOptions"/)
  assert.match(previewSource, /:key="pptRenderKey"/)
  assert.match(previewSource, /new ResizeObserver\(schedulePptMeasurement\)/)
  assert.match(previewSource, /container\.clientWidth\s*-\s*horizontalPadding/)
  assert.match(previewSource, /container\.clientHeight\s*-\s*verticalPadding/)
  assert.match(previewSource, /\.fp-ppt-container\s*\{[^}]*box-sizing:\s*border-box;[^}]*width:\s*100%;[^}]*min-width:\s*0;/)
  assert.match(previewSource, /\.fp-ppt-container\s+:deep\(\.pptx-preview-wrapper\)\s*\{[^}]*overflow-x:\s*hidden\s*!important;/)
  assert.match(previewSource, /stopPptResizeObserver\(\{\s*reset:\s*true\s*\}\)/)
})

test('folder and preview motion respect reduced-motion preferences', () => {
  assert.match(folderSource, /prefers-reduced-motion:\s*reduce/)
  assert.match(workspaceSource, /prefers-reduced-motion:\s*reduce/)
})
