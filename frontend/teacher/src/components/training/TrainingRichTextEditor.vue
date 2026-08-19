<template>
  <div class="rich-editor" :class="{ 'is-focused': editor?.isFocused }">
    <div v-if="editor" class="rich-editor__toolbar" role="toolbar" aria-label="任务说明格式">
      <label class="rich-editor__select-wrap">
        <span class="sr-only">段落格式</span>
        <select :value="activeBlock" aria-label="段落格式" @change="setBlockType">
          <option value="paragraph">正文</option>
          <option value="heading-1">一级标题</option>
          <option value="heading-2">二级标题</option>
          <option value="heading-3">三级标题</option>
        </select>
      </label>
      <span class="rich-editor__divider" aria-hidden="true"></span>
      <button type="button" :class="{ 'is-active': editor.isActive('bold') }" aria-label="加粗" title="加粗" @click="editor.chain().focus().toggleBold().run()"><strong>B</strong></button>
      <button type="button" :class="{ 'is-active': editor.isActive('bulletList') }" @click="editor.chain().focus().toggleBulletList().run()">项目列表</button>
      <button type="button" :class="{ 'is-active': editor.isActive('orderedList') }" @click="editor.chain().focus().toggleOrderedList().run()">编号列表</button>
      <button type="button" :class="{ 'is-active': editor.isActive('blockquote') }" @click="editor.chain().focus().toggleBlockquote().run()">引用</button>
      <span class="rich-editor__divider" aria-hidden="true"></span>
      <label class="rich-editor__select-wrap rich-editor__color-select">
        <span class="rich-editor__color-dot" :style="{ background: activeColor || '#12141a' }" aria-hidden="true"></span>
        <select :value="activeColor" aria-label="文字颜色" @change="setTextColor">
          <option value="">默认颜色</option>
          <option v-for="item in colorOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
        </select>
      </label>
      <button type="button" :class="{ 'is-active': editor.isActive('link') }" @click="setLink">链接</button>
      <button type="button" @click="imageInput?.click()">插入图片</button>
      <input ref="imageInput" class="rich-editor__file-input" type="file" accept="image/*" @change="insertImage" />
    </div>
    <div ref="contentScrollEl" class="rich-editor__content">
      <EditorContent :editor="editor" />
    </div>
    <div class="rich-editor__foot">
      <span class="rich-editor__status" :class="{ 'has-notice': pasteNotice }" aria-live="polite">
        {{ pasteNotice || '支持标题、颜色、Word 图文粘贴与正文图片' }}
      </span>
      <span>{{ characterCount }} 字</span>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { EditorContent, useEditor } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import Link from '@tiptap/extension-link'
import Image from '@tiptap/extension-image'
import { Color, TextStyle } from '@tiptap/extension-text-style'
import { useNestedScrollChain } from '../../composables/useNestedScrollChain'
import { stripAuthQueryFromHtml, withAuthMediaHtml } from '../../utils/mediaUrl'

const props = defineProps({ modelValue: { type: String, default: '' } })
const emit = defineEmits(['update:modelValue'])
const imageInput = ref(null)
const contentScrollEl = ref(null)
const pendingImages = ref([])
const pasteNotice = ref('')
let noticeTimer = null

// 仅聚焦编辑时：内滚到顶/底再交给 .teacher-main；未聚焦靠 CSS overflow:hidden 走原生滚动（不丢惯性）
useNestedScrollChain(contentScrollEl, { pageScrollUnlessFocused: true })

const colorOptions = [
  { label: '正文黑', value: '#12141a' },
  { label: '辅助灰', value: '#6b7280' },
  { label: '主题橙', value: '#e84a1c' },
  { label: '成功绿', value: '#0f9f6e' },
  { label: '提醒黄', value: '#d98200' },
  { label: '错误红', value: '#d83a45' }
]

const editor = useEditor({
  content: withAuthMediaHtml(props.modelValue || ''),
  extensions: [
    StarterKit.configure({ heading: { levels: [1, 2, 3] }, link: false }),
    TextStyle,
    Color.configure({ types: ['textStyle'] }),
    Link.configure({ openOnClick: false, autolink: true, linkOnPaste: true }),
    Image.configure({ allowBase64: false, inline: false })
  ],
  editorProps: {
    attributes: { 'aria-label': '日任务详细说明', class: 'rich-editor__prose' },
    handlePaste: (_view, event) => interceptRichPaste(event)
  },
  onUpdate: ({ editor: activeEditor }) => emit('update:modelValue', stripAuthQueryFromHtml(activeEditor.getHTML()))
})

const characterCount = computed(() => editor.value?.getText()?.length || 0)
const activeBlock = computed(() => {
  if (editor.value?.isActive('heading', { level: 1 })) return 'heading-1'
  if (editor.value?.isActive('heading', { level: 2 })) return 'heading-2'
  if (editor.value?.isActive('heading', { level: 3 })) return 'heading-3'
  return 'paragraph'
})
const activeColor = computed(() => String(editor.value?.getAttributes('textStyle')?.color || '').toLowerCase())

watch(() => props.modelValue, (value) => {
  if (!editor.value) return
  const next = withAuthMediaHtml(value || '')
  if (stripAuthQueryFromHtml(editor.value.getHTML()) !== stripAuthQueryFromHtml(next)) {
    editor.value.commands.setContent(next, { emitUpdate: false })
  }
})

function setBlockType(event) {
  if (!editor.value) return
  const value = event.target.value
  if (value === 'paragraph') editor.value.chain().focus().setParagraph().run()
  else editor.value.chain().focus().setHeading({ level: Number(value.slice(-1)) }).run()
}

function setTextColor(event) {
  if (!editor.value) return
  const color = event.target.value
  if (!color) editor.value.chain().focus().unsetColor().removeEmptyTextStyle().run()
  else editor.value.chain().focus().setColor(color).run()
}

function setLink() {
  const previous = editor.value?.getAttributes('link')?.href || ''
  const href = window.prompt('请输入链接地址（http:// 或 https://）', previous)
  if (href === null || !editor.value) return
  if (!href.trim()) {
    editor.value.chain().focus().extendMarkRange('link').unsetLink().run()
    return
  }
  const normalized = /^https?:\/\//i.test(href.trim()) ? href.trim() : `https://${href.trim()}`
  editor.value.chain().focus().extendMarkRange('link').setLink({ href: normalized }).run()
}

function insertImage(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file || !editor.value) return
  const localUrl = registerPendingImage(file)
  editor.value.chain().focus().setImage({ src: localUrl, alt: file.name || '任务说明图片' }).run()
}

function interceptRichPaste(event) {
  const clipboard = event.clipboardData
  if (!clipboard || !editor.value) return false
  const html = clipboard.getData('text/html') || ''
  const plainText = clipboard.getData('text/plain') || ''
  const imageFiles = Array.from(clipboard.items || [])
    .filter((item) => item.kind === 'file' && item.type.startsWith('image/'))
    .map((item) => item.getAsFile())
    .filter(Boolean)
  const isWord = /class=["']?Mso|mso-|urn:schemas-microsoft-com:office|<o:p|\[if\s+gte\s+mso/i.test(html)
  const hasHtmlImage = /<img\b/i.test(html)

  if (!isWord && !imageFiles.length && !hasHtmlImage) return false
  event.preventDefault()
  pasteRichContent(html, plainText, imageFiles, isWord)
  return true
}

function pasteRichContent(html, plainText, clipboardImages, isWord) {
  if (!editor.value) return
  let insertedImages = 0
  let unavailableImages = 0
  let cleanedHtml = ''

  if (html) {
    const documentNode = new DOMParser().parseFromString(html, 'text/html')
    documentNode.querySelectorAll('script, style, meta, link, xml, title').forEach((node) => node.remove())
    removeComments(documentNode.body)

    const imageNodes = Array.from(documentNode.body.querySelectorAll('img'))
    let clipboardIndex = 0
    imageNodes.forEach((imageNode, imageIndex) => {
      const originalSrc = String(imageNode.getAttribute('src') || '').trim()
      let file = clipboardImages[clipboardIndex] || null
      if (file) clipboardIndex += 1
      if (!file && originalSrc.startsWith('data:image/')) {
        file = dataUrlToFile(originalSrc, `粘贴图片-${imageIndex + 1}`)
      }
      if (!file) {
        if (originalSrc.startsWith('/uploads/task/instructions/')) return
        imageNode.remove()
        unavailableImages += 1
        return
      }
      const localUrl = registerPendingImage(file)
      imageNode.setAttribute('src', localUrl)
      imageNode.setAttribute('alt', imageNode.getAttribute('alt') || file.name || `粘贴图片-${imageIndex + 1}`)
      insertedImages += 1
    })

    clipboardImages.slice(clipboardIndex).forEach((file) => {
      const imageNode = documentNode.createElement('img')
      imageNode.setAttribute('src', registerPendingImage(file))
      imageNode.setAttribute('alt', file.name || '粘贴图片')
      documentNode.body.appendChild(imageNode)
      insertedImages += 1
    })

    normalizeWordMarkup(documentNode.body, isWord)
    cleanedHtml = documentNode.body.innerHTML.trim()
  } else if (clipboardImages.length) {
    cleanedHtml = clipboardImages.map((file) => {
      const localUrl = registerPendingImage(file)
      insertedImages += 1
      return `<img src="${escapeAttribute(localUrl)}" alt="${escapeAttribute(file.name || '粘贴图片')}">`
    }).join('')
  } else if (plainText) {
    cleanedHtml = plainText.split(/\r?\n/).filter((line) => line.trim()).map((line) => `<p>${escapeHtml(line)}</p>`).join('')
  }

  if (cleanedHtml) editor.value.chain().focus().insertContent(cleanedHtml).run()
  const messageParts = []
  if (isWord) messageParts.push('已整理 Word 格式')
  if (insertedImages) messageParts.push(`已加入 ${insertedImages} 张图片，保存任务后上传`)
  if (unavailableImages) messageParts.push(`${unavailableImages} 张本地引用图片无法读取，请重新粘贴或手动插入`)
  showNotice(messageParts.join('；') || '粘贴完成')
}

function normalizeWordMarkup(root, isWord) {
  root.querySelectorAll('o\\:p').forEach((node) => node.remove())
  root.querySelectorAll('p, div').forEach((node) => {
    const visibleText = String(node.textContent || '').replace(/\u00a0/g, ' ').trim()
    const hasMedia = Boolean(node.querySelector('img'))
    const hasStructuredChild = Boolean(node.querySelector('ul, ol, table, blockquote'))
    if (!visibleText && !hasMedia && !hasStructuredChild) node.remove()
  })

  if (isWord) {
    root.querySelectorAll('span').forEach((span) => {
      const style = String(span.getAttribute('style') || '').toLowerCase()
      if (/font-weight\s*:\s*(bold|[6-9]00)/.test(style)) {
        const strong = root.ownerDocument.createElement('strong')
        while (span.firstChild) strong.appendChild(span.firstChild)
        span.replaceWith(strong)
      }
    })
  }

  root.querySelectorAll('*').forEach((node) => {
    const tag = node.tagName.toLowerCase()
    const href = tag === 'a' ? node.getAttribute('href') : null
    const src = tag === 'img' ? node.getAttribute('src') : null
    const alt = tag === 'img' ? node.getAttribute('alt') : null
    Array.from(node.attributes).forEach((attribute) => node.removeAttribute(attribute.name))
    if (href && /^(https?:\/\/|\/|#)/i.test(href)) node.setAttribute('href', href)
    if (src && (src.startsWith('blob:') || src.startsWith('/uploads/task/instructions/'))) node.setAttribute('src', src)
    if (alt) node.setAttribute('alt', alt)
  })
}

function removeComments(root) {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_COMMENT)
  const comments = []
  while (walker.nextNode()) comments.push(walker.currentNode)
  comments.forEach((comment) => comment.remove())
}

function registerPendingImage(file) {
  const localUrl = URL.createObjectURL(file)
  pendingImages.value.push({ localUrl, file })
  return localUrl
}

function dataUrlToFile(dataUrl, baseName) {
  try {
    const match = String(dataUrl).match(/^data:(image\/(?:png|jpeg|gif));base64,(.+)$/i)
    if (!match) return null
    const bytes = atob(match[2])
    const array = new Uint8Array(bytes.length)
    for (let index = 0; index < bytes.length; index += 1) array[index] = bytes.charCodeAt(index)
    const extension = match[1].toLowerCase() === 'image/jpeg' ? 'jpg' : match[1].split('/')[1]
    return new File([array], `${baseName}.${extension}`, { type: match[1] })
  } catch {
    return null
  }
}

function escapeHtml(value) {
  return String(value).replace(/[&<>]/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' })[character])
}

function escapeAttribute(value) {
  return escapeHtml(value).replace(/"/g, '&quot;')
}

function showNotice(message) {
  pasteNotice.value = message
  if (noticeTimer) window.clearTimeout(noticeTimer)
  noticeTimer = window.setTimeout(() => { pasteNotice.value = '' }, 8000)
}

function getPendingImages() { return [...pendingImages.value] }
function setHtml(html) {
  const stored = stripAuthQueryFromHtml(html || '')
  editor.value?.commands.setContent(withAuthMediaHtml(stored), { emitUpdate: false })
  emit('update:modelValue', stored)
}
function clearPendingImages() {
  pendingImages.value.forEach(({ localUrl }) => URL.revokeObjectURL(localUrl))
  pendingImages.value = []
}

onBeforeUnmount(() => {
  clearPendingImages()
  if (noticeTimer) window.clearTimeout(noticeTimer)
})
defineExpose({ getPendingImages, setHtml, clearPendingImages })
</script>

<style scoped>
.rich-editor {
  height: 650px;
  overflow: hidden;
  border: 1px solid var(--ds-input-border);
  border-radius: 12px;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  background: #fff;
  transition: border-color 0.16s ease, box-shadow 0.16s ease;
}
.rich-editor.is-focused {
  border-color: var(--ds-orange);
  box-shadow: var(--ds-input-focus-ring);
}
.rich-editor__toolbar {
  min-height: 48px;
  padding: 7px 8px;
  display: flex;
  align-items: center;
  gap: 4px;
  overflow-x: auto;
  border-bottom: 1px solid var(--ds-line);
  background: var(--ds-surface-soft);
  scrollbar-width: thin;
}
.rich-editor__divider {
  flex: 0 0 1px;
  width: 1px;
  height: 20px;
  margin: 0 3px;
  background: var(--ds-line-strong);
}
.rich-editor__toolbar button,
.rich-editor__select-wrap {
  flex: 0 0 auto;
  min-height: 32px;
  border: 1px solid transparent;
  border-radius: 8px;
  color: var(--ds-ink-2);
  background: transparent;
  font: 600 11px/1 var(--ds-font-sans);
}
.rich-editor__toolbar button {
  padding: 0 10px;
  cursor: pointer;
}
.rich-editor__toolbar button:hover,
.rich-editor__select-wrap:hover {
  border-color: var(--ds-line-strong);
  background: #fff;
}
.rich-editor__toolbar button.is-active {
  color: var(--ds-orange-deep);
  border-color: rgba(232, 74, 28, 0.22);
  background: var(--ds-orange-wash);
}
.rich-editor__select-wrap {
  position: relative;
  display: flex;
  align-items: center;
  background: #fff;
  border-color: var(--ds-line);
}
.rich-editor__select-wrap select {
  height: 30px;
  padding: 0 27px 0 10px;
  border: 0;
  outline: 0;
  color: var(--ds-ink-2);
  background: transparent;
  font: 600 11px/1 var(--ds-font-sans);
  cursor: pointer;
}
.rich-editor__color-select select {
  padding-left: 27px;
}
.rich-editor__color-dot {
  position: absolute;
  left: 10px;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  box-shadow: 0 0 0 1px rgba(18, 20, 26, 0.12);
  pointer-events: none;
}
.rich-editor__file-input,
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
/* 未聚焦：不建立内滚，滚轮原生落到 .teacher-main（快、有惯性） */
.rich-editor__content {
  min-height: 0;
  padding: 18px 20px;
  overflow-y: hidden;
  overscroll-behavior-y: auto;
}
/* 聚焦编辑：才开启内滚，便于写长文 */
.rich-editor.is-focused .rich-editor__content {
  overflow-y: auto;
  scrollbar-gutter: stable;
}
.rich-editor__foot {
  min-height: 36px;
  padding: 0 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border-top: 1px solid var(--ds-line);
  color: var(--ds-muted);
  background: #fff;
  font-size: 10px;
}
.rich-editor__status.has-notice {
  color: var(--ds-orange-deep);
  font-weight: 700;
}
.rich-editor__content :deep(.rich-editor__prose) {
  min-height: 100%;
  outline: 0;
  color: var(--ds-ink-2);
  font: 400 14px/1.75 var(--ds-font-sans);
}
.rich-editor__content :deep(.rich-editor__prose p) {
  margin: 0 0 8px;
}
.rich-editor__content :deep(.rich-editor__prose h1) {
  margin: 20px 0 10px;
  color: var(--ds-ink);
  font-size: 24px;
  line-height: 1.35;
}
.rich-editor__content :deep(.rich-editor__prose h2) {
  margin: 18px 0 8px;
  color: var(--ds-ink);
  font-size: 20px;
  line-height: 1.4;
}
.rich-editor__content :deep(.rich-editor__prose h3) {
  margin: 16px 0 7px;
  color: var(--ds-ink);
  font-size: 17px;
  line-height: 1.45;
}
.rich-editor__content :deep(.rich-editor__prose h1:first-child),
.rich-editor__content :deep(.rich-editor__prose h2:first-child),
.rich-editor__content :deep(.rich-editor__prose h3:first-child) {
  margin-top: 0;
}
.rich-editor__content :deep(.rich-editor__prose ul),
.rich-editor__content :deep(.rich-editor__prose ol) {
  margin: 10px 0;
  padding-left: 24px;
}
.rich-editor__content :deep(.rich-editor__prose blockquote) {
  margin: 12px 0;
  padding: 10px 14px;
  border-left: 3px solid var(--ds-orange);
  border-radius: 0 8px 8px 0;
  background: var(--ds-orange-wash);
  color: var(--ds-ink-2);
}
.rich-editor__content :deep(.rich-editor__prose a) {
  color: var(--ds-orange-deep);
  text-decoration: underline;
  text-underline-offset: 3px;
}
.rich-editor__content :deep(.rich-editor__prose img) {
  max-width: 100%;
  height: auto;
  margin: 14px auto;
  border-radius: 12px;
  display: block;
  box-shadow: 0 5px 18px rgba(31, 35, 41, 0.09);
}
.rich-editor__content :deep(.rich-editor__prose p.is-editor-empty:first-child::before) {
  height: 0;
  float: left;
  color: var(--ds-muted);
  content: '补充任务背景、步骤、示例或注意事项…';
  pointer-events: none;
}
@media (max-width: 760px) {
  .rich-editor {
    height: 390px;
  }
  .rich-editor__toolbar {
    flex-wrap: nowrap;
  }
  .rich-editor__toolbar button {
    white-space: nowrap;
  }
  .rich-editor__content {
    padding: 15px;
  }
}
</style>

