<template>
  <section class="learning-editor" :class="{ 'is-compact': compact }">
    <header v-if="!compact" class="learning-editor__head">
      <div>
        <span>01</span>
        <div>
          <h3>今日学习</h3>
          <p>学生会先看到这里的内容，再进入任务书与成果提交。</p>
        </div>
      </div>
      <div class="learning-editor__summary">
        <span>{{ resources.length }} 项</span>
        <span>{{ requiredCount }} 项必学</span>
        <span>约 {{ estimatedMinutes }} 分钟</span>
      </div>
    </header>

    <div class="learning-editor__toolbar">
      <button type="button" class="teacher-btn teacher-btn--secondary teacher-btn--sm" :disabled="busy || !dayId" @click="fileInput?.click()">
        {{ uploading ? '上传中…' : '上传视频或资料' }}
      </button>
      <button type="button" class="teacher-btn teacher-btn--secondary teacher-btn--sm" :disabled="busy || !dayId" @click="openEmbedDialog">
        站外视频内嵌
      </button>
      <button type="button" class="teacher-btn teacher-btn--secondary teacher-btn--sm" :disabled="busy || !dayId" @click="openLinkDialog">
        普通外链
      </button>
      <details v-if="!compact" class="learning-editor__format-help">
        <summary>查看支持格式</summary>
        <p>视频 MP4/WebM/MOV（最大 500MB）；其他资料最大 50MB，支持音频、PDF、Word、PPT、Excel、CSV、文本、图片及 ZIP/RAR/7Z。</p>
      </details>
      <span v-else class="learning-editor__compact-meta">
        {{ resources.length }} 项 · {{ requiredCount }} 必学
        <template v-if="estimatedMinutes"> · 约 {{ estimatedMinutes }} 分钟</template>
      </span>
      <input
        ref="fileInput"
        type="file"
        multiple
        :accept="LEARNING_FILE_ACCEPT"
        @change="chooseFiles"
      />
    </div>

    <div v-if="uploading" class="learning-editor__upload-progress" role="status" aria-live="polite">
      <div>
        <span>正在上传 {{ uploadBatch.currentIndex }}/{{ uploadBatch.total }}</span>
        <strong>{{ uploadBatch.overallPercent }}%</strong>
      </div>
      <p>{{ uploadBatch.currentFile }}</p>
      <div class="learning-editor__upload-track">
        <i :style="{ width: `${uploadBatch.overallPercent}%` }"></i>
      </div>
      <small>当前文件 {{ uploadBatch.filePercent }}%</small>
    </div>

    <div
      v-if="notice"
      class="learning-editor__notice"
      :class="{ 'is-error': error, 'is-warning': warning }"
      :role="error ? 'alert' : 'status'"
      aria-live="polite"
    >{{ notice }}</div>

    <div v-if="resources.length" class="learning-resource-list">
      <article v-for="(item, index) in resources" :key="item.id">
        <span class="learning-resource-list__type" :class="{ 'is-embed': item.resourceType === 'EMBED_VIDEO' }">
          {{ typeLabel(item.resourceType, item.provider) }}
        </span>
        <label class="learning-resource-list__copy">
          <span>{{ item.resourceType === 'VIDEO' || item.resourceType === 'EMBED_VIDEO' ? '视频名称' : '内容名称' }}</span>
          <input
            :value="item.title"
            :disabled="busy"
            maxlength="200"
            :aria-label="item.resourceType === 'VIDEO' || item.resourceType === 'EMBED_VIDEO' ? '视频名称' : '学习内容名称'"
            placeholder="请输入学生看到的名称"
            @change="updateField(item, 'title', $event.target.value)"
          />
          <small>
            {{ item.fileName || hostLabel(item.resourceUrl) }}
            <template v-if="item.resourceType === 'EMBED_VIDEO'"> · 平台内播放 · 完成 {{ Math.round(Number(item.completeRatio || 0.8) * 100) }}%</template>
            · {{ item.status === 'ACTIVE' ? '学生可见' : '待发布' }}
          </small>
        </label>
        <label class="learning-resource-list__duration">
          <input
            :value="Math.ceil(Number(item.durationSeconds || 0) / 60)"
            type="number"
            min="0"
            max="1440"
            aria-label="预计分钟"
            @change="updateField(item, 'durationSeconds', Number($event.target.value || 0) * 60)"
          />
          <span>分钟</span>
        </label>
        <label class="learning-resource-list__required">
          <input
            :checked="isRequired(item)"
            type="checkbox"
            @change="updateField(item, 'required', $event.target.checked)"
          />
          必学
        </label>
        <div class="learning-resource-list__actions">
          <button type="button" :disabled="busy || index === 0" aria-label="上移学习内容" @click="move(index, -1)">↑</button>
          <button type="button" :disabled="busy || index === resources.length - 1" aria-label="下移学习内容" @click="move(index, 1)">↓</button>
          <a
            :href="previewHref(item.resourceUrl)"
            target="_blank"
            rel="noopener"
            :download="isDownloadOnly(item) ? (item.fileName || '') : null"
          >{{ isDownloadOnly(item) ? '下载' : '预览' }}</a>
          <button type="button" class="is-delete" :disabled="busy" aria-label="删除学习内容" @click="remove(item)">×</button>
        </div>
      </article>
    </div>

    <div v-else class="learning-editor__empty" :class="{ 'is-compact': compact }">
      <strong>{{ compact ? '暂无学习资料' : '今天还没有学习内容' }}</strong>
      <span v-if="!compact">支持上传视频/资料、B 站等站外视频内嵌，或普通外链。</span>
      <span v-else>上传视频/文档，或站外视频内嵌（可选）</span>
    </div>

    <Teleport to="body">
      <div
        v-if="showLinkDialog"
        class="learning-dialog teacher-overlay-mask"
        role="presentation"
        @click.self="showLinkDialog = false"
      >
        <form class="learning-dialog__card" role="dialog" aria-modal="true" aria-label="添加外部课程链接" @submit.prevent="saveLink">
          <header><div><span>添加学习内容</span><h3>普通外链</h3></div><button type="button" @click="showLinkDialog = false">×</button></header>
          <label><span>标题 *</span><input v-model.trim="linkForm.title" required maxlength="200" placeholder="例如：模块拆分的三个判断标准" /></label>
          <label><span>HTTPS 链接 *</span><input v-model.trim="linkForm.url" required type="url" pattern="https://.*" placeholder="https://..." /></label>
          <label><span>补充说明</span><textarea v-model.trim="linkForm.description" rows="3" maxlength="1000" placeholder="告诉学生重点看什么" /></label>
          <div class="learning-dialog__row">
            <label><span>预计时长</span><input v-model.number="linkForm.minutes" type="number" min="0" max="1440" /><small>分钟</small></label>
            <label class="is-check"><input v-model="linkForm.required" type="checkbox" />设为必学</label>
          </div>
          <footer>
            <button type="button" class="teacher-btn teacher-btn--secondary" @click="showLinkDialog = false">取消</button>
            <button type="submit" class="teacher-btn teacher-btn--primary" :disabled="busy">{{ busy ? '正在添加…' : '添加内容' }}</button>
          </footer>
        </form>
      </div>
    </Teleport>

    <Teleport to="body">
      <div
        v-if="showEmbedDialog"
        class="learning-dialog teacher-overlay-mask"
        role="presentation"
        @click.self="showEmbedDialog = false"
      >
        <form class="learning-dialog__card learning-dialog__card--wide" role="dialog" aria-modal="true" aria-label="添加站外视频内嵌" @submit.prevent="saveEmbed">
          <header>
            <div>
              <span>今日学习</span>
              <h3>站外视频内嵌</h3>
            </div>
            <button type="button" @click="showEmbedDialog = false">×</button>
          </header>
          <p class="learning-dialog__hint">粘贴 B 站视频链接，学生将在平台内播放；按时长累计学习进度（默认学满 80% 算完成）。</p>
          <label>
            <span>视频链接 *</span>
            <div class="learning-dialog__url-row">
              <input
                v-model.trim="embedForm.url"
                required
                placeholder="https://www.bilibili.com/video/BVxxxx 或 BV 号"
                @blur="tryParseEmbed"
              />
              <button type="button" class="teacher-btn teacher-btn--secondary teacher-btn--sm" :disabled="busy || parsingEmbed" @click="tryParseEmbed">
                {{ parsingEmbed ? '识别中…' : '识别' }}
              </button>
            </div>
          </label>
          <div v-if="embedParsed" class="learning-dialog__preview">
            <div class="learning-dialog__preview-frame">
              <iframe
                v-if="embedParsed.embedUrl"
                :src="embedParsed.embedUrl"
                title="预览"
                allowfullscreen
                scrolling="no"
                frameborder="0"
                sandbox="allow-scripts allow-same-origin allow-popups allow-presentation"
              />
            </div>
            <div class="learning-dialog__preview-meta">
              <span class="learning-dialog__badge">{{ embedParsed.providerLabel || 'B站' }}</span>
              <small>{{ embedParsed.providerVideoId }}</small>
              <p>已识别，可在下方修改名称与预计时长后加入。</p>
            </div>
          </div>
          <p v-if="embedParseError" class="learning-dialog__error">{{ embedParseError }}</p>
          <label><span>显示名称 *</span><input v-model.trim="embedForm.title" required maxlength="200" placeholder="学生看到的标题" /></label>
          <label><span>学习要求 / 说明</span><textarea v-model.trim="embedForm.description" rows="2" maxlength="1000" placeholder="例如：重点看 3:20–8:00 的方案拆解" /></label>
          <div class="learning-dialog__row">
            <label>
              <span>预计时长 *</span>
              <input v-model.number="embedForm.minutes" type="number" min="1" max="1440" required />
              <small>分钟</small>
            </label>
            <label class="is-check"><input v-model="embedForm.required" type="checkbox" />设为必学</label>
          </div>
          <footer>
            <button type="button" class="teacher-btn teacher-btn--secondary" @click="showEmbedDialog = false">取消</button>
            <button type="submit" class="teacher-btn teacher-btn--primary" :disabled="busy || !embedParsed">
              {{ busy ? '正在添加…' : '加入今日学习' }}
            </button>
          </footer>
        </form>
      </div>
    </Teleport>
  </section>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  createTeacherLearningEmbed,
  createTeacherLearningLink,
  deleteTeacherLearningResource,
  parseTeacherLearningEmbed,
  reorderTeacherLearningResources,
  updateTeacherLearningResource,
  uploadTeacherLearningResource
} from '../../api'
import { getToken } from '../../utils/auth'

const LEARNING_FILE_ACCEPT = [
  '.mp4', '.webm', '.mov',
  '.mp3', '.wav', '.m4a',
  '.pdf', '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx',
  '.csv', '.txt', '.md',
  '.jpg', '.jpeg', '.png', '.gif', '.webp',
  '.zip', '.rar', '.7z',
  'video/mp4', 'video/webm', 'video/quicktime',
  'audio/mpeg', 'audio/wav', 'audio/mp4',
  'application/pdf',
  'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'application/vnd.ms-powerpoint', 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
  'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  'text/csv', 'text/plain', 'text/markdown',
  'image/jpeg', 'image/png', 'image/gif', 'image/webp',
  'application/zip', 'application/vnd.rar', 'application/x-7z-compressed'
].join(',')
const DOWNLOAD_ONLY_EXTENSIONS = new Set(['zip', 'rar', '7z'])

const props = defineProps({
  dayId: { type: [Number, String], default: null },
  modelValue: { type: Array, default: () => [] },
  /** 嵌入每日计划单页时使用更紧凑样式 */
  compact: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue'])

const resources = ref([])
const busy = ref(false)
const uploading = ref(false)
const notice = ref('')
const error = ref(false)
const warning = ref(false)
const fileInput = ref(null)
const showLinkDialog = ref(false)
const linkForm = ref({ title: '', url: '', description: '', minutes: 0, required: true })
const showEmbedDialog = ref(false)
const parsingEmbed = ref(false)
const embedParsed = ref(null)
const embedParseError = ref('')
const embedForm = ref({ title: '', url: '', description: '', minutes: 15, required: true })
const uploadBatch = ref({
  currentIndex: 0,
  total: 0,
  currentFile: '',
  filePercent: 0,
  overallPercent: 0
})

watch(() => props.modelValue, value => {
  resources.value = (value || []).map(item => ({ ...item }))
}, { immediate: true, deep: true })

const requiredCount = computed(() => resources.value.filter(isRequired).length)
const estimatedMinutes = computed(() => Math.ceil(resources.value.reduce((sum, item) => sum + Number(item.durationSeconds || 0), 0) / 60))

function commit(next) {
  resources.value = (next || []).map(item => ({ ...item }))
  emit('update:modelValue', resources.value)
}

function isRequired(item) {
  return item?.required === true || Number(item?.required) === 1
}

function typeLabel(type, provider) {
  if (type === 'EMBED_VIDEO') {
    if (String(provider || '').toUpperCase() === 'BILIBILI') return 'B站'
    return '站外'
  }
  return { VIDEO: '视频', DOCUMENT: '资料', LINK: '链接' }[type] || '资源'
}

function hostLabel(url) {
  try { return new URL(url).host }
  catch { return '外部链接' }
}

/** Learning media is auth-gated; browser open needs ?t= JWT. */
function previewHref(url) {
  if (!url || typeof url !== 'string') return '#'
  if (/^https?:\/\//i.test(url) && !url.includes('/uploads/training/learning/')) return url
  const path = url.startsWith('/') ? url : `/${url}`
  if (!path.startsWith('/uploads/training/learning/')) return path
  const token = getToken()
  if (!token) return path
  const sep = path.includes('?') ? '&' : '?'
  return `${path}${sep}t=${encodeURIComponent(token)}`
}

function fileExtension(item) {
  const source = String(item?.fileName || item?.resourceUrl || '').split(/[?#]/)[0]
  const index = source.lastIndexOf('.')
  return index < 0 ? '' : source.slice(index + 1).toLowerCase()
}

function isDownloadOnly(item) {
  return DOWNLOAD_ONLY_EXTENSIONS.has(fileExtension(item))
}

async function chooseFiles(event) {
  const files = [...(event.target.files || [])]
  event.target.value = ''
  if (!files.length || !props.dayId) return
  busy.value = true
  uploading.value = true
  clearNotice()
  const failures = []
  let successCount = 0
  uploadBatch.value = {
    currentIndex: 1,
    total: files.length,
    currentFile: files[0]?.name || '',
    filePercent: 0,
    overallPercent: 0
  }
  try {
    for (const [index, file] of files.entries()) {
      updateUploadProgress(index, files.length, file, 0)
      try {
        const uploaded = await uploadTeacherLearningResource(props.dayId, file, {
          title: defaultFileTitle(file),
          required: true,
          durationSeconds: 0
        }, {
          onUploadProgress(progressEvent) {
            const totalBytes = Number(progressEvent.total || file.size || 0)
            const loadedBytes = Number(progressEvent.loaded || 0)
            const ratio = totalBytes > 0 ? loadedBytes / totalBytes : 0
            updateUploadProgress(index, files.length, file, ratio)
          }
        })
        commit([...resources.value, uploaded])
        successCount += 1
      } catch (err) {
        failures.push({
          fileName: file.name || '未命名文件',
          message: uploadErrorMessage(err)
        })
      }
      updateUploadProgress(index, files.length, file, 1)
    }

    if (!failures.length) {
      const message = `${successCount} 项学习内容已上传，名称默认取自原文件名，可直接修改`
      setNotice(message)
      ElMessage.success({ message, duration: 5000, showClose: true, offset: 72 })
    } else if (successCount > 0) {
      const message = `${successCount} 项上传成功，${failures.length} 项失败：${failureLabel(failures)}`
      setNotice(message, 'warning')
      ElMessage.warning({ message, duration: 5000, showClose: true, offset: 72 })
    } else {
      const message = `学习内容上传失败：${failureLabel(failures)}`
      setNotice(message, 'error')
      ElMessage.error({ message, duration: 5000, showClose: true, offset: 72 })
    }
  } finally {
    uploading.value = false
    busy.value = false
  }
}

function updateUploadProgress(index, totalFiles, file, ratio) {
  const safeRatio = Math.max(0, Math.min(1, Number(ratio || 0)))
  uploadBatch.value = {
    currentIndex: index + 1,
    total: totalFiles,
    currentFile: file?.name || '未命名文件',
    filePercent: Math.round(safeRatio * 100),
    overallPercent: Math.round(((index + safeRatio) / totalFiles) * 100)
  }
}

function uploadErrorMessage(err) {
  const message = err?.response?.data?.message || err?.message || ''
  if (err?.code === 'ECONNABORTED' || /timeout|超时/i.test(message)) {
    return '上传超时，请检查网络后重新上传'
  }
  return message || '学习内容上传失败'
}

function failureLabel(failures) {
  const first = failures[0]
  if (!first) return '未知错误'
  const remaining = failures.length > 1 ? `，另有 ${failures.length - 1} 个文件失败` : ''
  return `${first.fileName}（${first.message}）${remaining}`
}

function clearNotice() {
  notice.value = ''
  error.value = false
  warning.value = false
}

function setNotice(message, tone = 'success') {
  notice.value = message
  error.value = tone === 'error'
  warning.value = tone === 'warning'
}

function defaultFileTitle(file) {
  const originalName = String(file?.name || '').trim()
  return originalName.replace(/\.[^.]+$/, '').trim() || '未命名学习内容'
}

function openLinkDialog() {
  linkForm.value = { title: '', url: '', description: '', minutes: 0, required: true }
  showLinkDialog.value = true
}

function openEmbedDialog() {
  embedForm.value = { title: '', url: '', description: '', minutes: 15, required: true }
  embedParsed.value = null
  embedParseError.value = ''
  showEmbedDialog.value = true
}

async function tryParseEmbed() {
  if (!props.dayId || !embedForm.value.url) return
  parsingEmbed.value = true
  embedParseError.value = ''
  try {
    const parsed = await parseTeacherLearningEmbed(props.dayId, embedForm.value.url)
    embedParsed.value = parsed
    if (!embedForm.value.title && parsed?.title) {
      embedForm.value.title = parsed.title
    }
  } catch (err) {
    embedParsed.value = null
    embedParseError.value = err?.response?.data?.message || err?.message || '识别失败'
  } finally {
    parsingEmbed.value = false
  }
}

async function saveEmbed() {
  if (!props.dayId || !embedParsed.value) return
  if (!Number(embedForm.value.minutes) || Number(embedForm.value.minutes) < 1) {
    setNotice('请填写预计时长（至少 1 分钟）', 'error')
    return
  }
  busy.value = true
  clearNotice()
  try {
    const created = await createTeacherLearningEmbed(props.dayId, {
      title: embedForm.value.title,
      url: embedForm.value.url || embedParsed.value.originalUrl,
      description: embedForm.value.description,
      durationSeconds: Number(embedForm.value.minutes || 0) * 60,
      required: embedForm.value.required,
      completeRatio: 0.8
    })
    commit([...resources.value, created])
    showEmbedDialog.value = false
    setNotice('站外视频已加入今日学习，学生可在平台内播放')
    ElMessage.success({ message: '站外视频已添加', duration: 3000, offset: 72 })
  } catch (err) {
    setNotice(err?.response?.data?.message || err?.message || '添加失败', 'error')
  } finally {
    busy.value = false
  }
}

async function saveLink() {
  if (!props.dayId) return
  busy.value = true
  clearNotice()
  try {
    const created = await createTeacherLearningLink(props.dayId, {
      title: linkForm.value.title,
      url: linkForm.value.url,
      description: linkForm.value.description,
      durationSeconds: Number(linkForm.value.minutes || 0) * 60,
      required: linkForm.value.required
    })
    commit([...resources.value, created])
    showLinkDialog.value = false
    setNotice('外部课程链接已添加，发布日任务后学生可见')
  } catch (err) {
    setNotice(err?.response?.data?.message || err?.message || '外部课程链接添加失败', 'error')
  } finally {
    busy.value = false
  }
}

async function updateField(item, key, value) {
  if (!props.dayId || !item?.id) return
  busy.value = true
  clearNotice()
  try {
    const updated = await updateTeacherLearningResource(props.dayId, item.id, { [key]: value })
    commit(resources.value.map(resource => resource.id === item.id ? updated : resource))
  } catch (err) {
    setNotice(err?.response?.data?.message || err?.message || '学习内容更新失败', 'error')
  } finally {
    busy.value = false
  }
}

async function move(index, offset) {
  const target = index + offset
  if (target < 0 || target >= resources.value.length || !props.dayId) return
  const next = [...resources.value]
  const [item] = next.splice(index, 1)
  next.splice(target, 0, item)
  busy.value = true
  clearNotice()
  try {
    commit(await reorderTeacherLearningResources(props.dayId, next.map(resource => resource.id)))
  } catch (err) {
    setNotice(err?.response?.data?.message || err?.message || '学习内容排序失败', 'error')
  } finally {
    busy.value = false
  }
}

async function remove(item) {
  if (!props.dayId || !item?.id || !window.confirm(`确认删除学习内容“${item.title}”吗？历史学习记录会保留。`)) return
  busy.value = true
  clearNotice()
  try {
    await deleteTeacherLearningResource(props.dayId, item.id)
    commit(resources.value.filter(resource => resource.id !== item.id))
    setNotice('学习内容已移除')
  } catch (err) {
    setNotice(err?.response?.data?.message || err?.message || '学习内容删除失败', 'error')
  } finally {
    busy.value = false
  }
}
</script>

<style scoped>
.learning-editor{padding:16px;border:1px solid rgba(232,74,28,.2);border-radius:14px;background:#fff8f5}.learning-editor__head{display:flex;align-items:flex-start;justify-content:space-between;gap:16px}.learning-editor__head>div:first-child{display:flex;gap:10px}.learning-editor__head>div:first-child>span{width:28px;height:28px;border-radius:9px;display:grid;place-items:center;color:#fff;background:var(--ds-orange);font-size:10px;font-weight:900}.learning-editor h3{margin:0;font-size:15px}.learning-editor p{margin:4px 0 0;color:var(--ds-muted);font-size:11px}.learning-editor__summary{display:flex;flex-wrap:wrap;justify-content:flex-end;gap:5px}.learning-editor__summary span{padding:4px 7px;border-radius:999px;color:var(--ds-orange-deep);background:#fff0ea;font-size:9px;font-weight:700}.learning-editor__toolbar{margin-top:14px;display:flex;align-items:center;flex-wrap:wrap;gap:7px}.learning-editor__toolbar input{display:none}.learning-editor__format-help{position:relative;color:var(--ds-muted);font-size:10px}.learning-editor__format-help summary{padding:7px 4px;cursor:pointer;user-select:none}.learning-editor__format-help p{position:absolute;z-index:5;top:100%;left:0;width:min(420px,72vw);margin:4px 0 0;padding:10px 12px;border:1px solid var(--ds-line);border-radius:10px;color:var(--ds-ink-soft);background:#fff;box-shadow:0 10px 28px rgba(31,36,45,.12);line-height:1.6}.learning-editor__upload-progress{margin-top:10px;padding:10px;border:1px solid rgba(232,74,28,.18);border-radius:10px;background:#fff}.learning-editor__upload-progress>div:first-child{display:flex;align-items:center;justify-content:space-between;gap:12px;color:var(--ds-orange-deep);font-size:10px;font-weight:800}.learning-editor__upload-progress p{overflow:hidden;margin:5px 0 7px;color:var(--ds-ink);text-overflow:ellipsis;white-space:nowrap}.learning-editor__upload-progress small{display:block;margin-top:5px;color:var(--ds-muted);font-size:9px}.learning-editor__upload-track{height:5px;overflow:hidden;border-radius:999px;background:#f1e5df}.learning-editor__upload-track i{display:block;height:100%;border-radius:inherit;background:linear-gradient(90deg,var(--ds-orange),#ff966f);transition:width .18s ease}.learning-editor__notice{margin-top:10px;padding:8px 10px;border-radius:9px;color:#0b7753;background:#e6f6ef;font-size:11px}.learning-editor__notice.is-warning{color:#875400;background:#fff4d9}.learning-editor__notice.is-error{color:#a33a24;background:#fff0ec}.learning-resource-list{margin-top:10px;border:1px solid var(--ds-line);border-radius:12px;overflow:hidden;background:#fff}.learning-resource-list article{min-height:74px;padding:10px;display:grid;grid-template-columns:42px minmax(170px,1fr) 82px 58px auto;gap:10px;align-items:center;border-bottom:1px solid var(--ds-line)}.learning-resource-list article:last-child{border-bottom:0}.learning-resource-list__type{height:34px;border-radius:9px;display:grid;place-items:center;color:var(--ds-orange-deep);background:var(--ds-orange-wash);font-size:9px;font-weight:900}.learning-resource-list__copy{min-width:0;display:grid;gap:4px;color:var(--ds-muted);font-size:9px;font-weight:700}.learning-resource-list__copy>span{letter-spacing:.02em}.learning-resource-list__copy input{box-sizing:border-box;width:100%;height:32px;border:1px solid var(--ds-input-border);border-radius:8px;padding:5px 9px;color:var(--ds-ink);background:#fff;font:700 12px var(--ds-font-sans);transition:border-color .16s ease,box-shadow .16s ease}.learning-resource-list__copy input:hover{border-color:#d8b7a7}.learning-resource-list__copy input:focus{outline:none;border-color:var(--ds-orange);box-shadow:0 0 0 3px rgba(232,74,28,.09)}.learning-resource-list__copy input:disabled{color:var(--ds-muted);background:var(--ds-surface-soft)}.learning-resource-list__copy small{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--ds-muted);font-size:9px;font-weight:500}.learning-resource-list__duration{height:30px;display:flex;align-items:center;border:1px solid var(--ds-line);border-radius:8px;background:#fff}.learning-resource-list__duration input{min-width:0;width:42px;border:0;padding:5px;background:transparent;text-align:right;font-size:10px}.learning-resource-list__duration span{padding-right:5px;color:var(--ds-muted);font-size:9px}.learning-resource-list__required{display:flex;align-items:center;gap:4px;color:var(--ds-ink-soft);font-size:10px}.learning-resource-list__actions{display:flex;align-items:center;gap:4px}.learning-resource-list__actions button,.learning-resource-list__actions a{width:27px;height:27px;border:0;border-radius:7px;display:grid;place-items:center;color:var(--ds-muted);background:var(--ds-surface-soft);font-size:10px;text-decoration:none;cursor:pointer}.learning-resource-list__actions a{width:auto;padding:0 7px}.learning-resource-list__actions button.is-delete{color:#a33a24;background:#fff0ec}.learning-resource-list__actions button:disabled{opacity:.35;cursor:not-allowed}.learning-editor__empty{margin-top:10px;padding:22px;border:1px dashed var(--ds-line-strong);border-radius:12px;display:grid;gap:5px;text-align:center}.learning-editor__empty strong{font-size:12px}.learning-editor__empty span{color:var(--ds-muted);font-size:10px}.learning-dialog{padding:24px;display:grid;place-items:center;box-sizing:border-box}.learning-dialog__card{box-sizing:border-box;width:min(520px,100%);padding:20px;border-radius:16px;background:#fff;box-shadow:0 24px 70px rgba(0,0,0,.18);display:grid;gap:14px}.learning-dialog__card>header{display:flex;justify-content:space-between}.learning-dialog__card>header span{color:var(--ds-orange);font-size:10px;font-weight:800}.learning-dialog__card>header h3{margin-top:4px;font-size:18px}.learning-dialog__card>header button{width:30px;height:30px;border:0;border-radius:8px;background:var(--ds-surface-soft);cursor:pointer}.learning-dialog__card>label{display:grid;gap:6px;color:var(--ds-muted);font-size:11px;font-weight:700}.learning-dialog__card input,.learning-dialog__card textarea{box-sizing:border-box;width:100%;border:1px solid var(--ds-input-border);border-radius:10px;padding:9px 11px;font:500 12px/1.5 var(--ds-font-sans)}.learning-dialog__row{display:grid;grid-template-columns:1fr 1fr;gap:12px}.learning-dialog__row label{display:flex;align-items:center;gap:6px;font-size:11px}.learning-dialog__row label:first-child{display:grid;grid-template-columns:1fr 70px auto}.learning-dialog__row label:first-child>span{grid-column:1/-1}.learning-dialog__row .is-check input{width:auto}.learning-dialog__card footer{display:flex;justify-content:flex-end;gap:8px}@media(max-width:760px){.learning-editor__head{display:grid}.learning-editor__summary{justify-content:flex-start}.learning-resource-list article{grid-template-columns:40px minmax(0,1fr);gap:7px}.learning-resource-list__duration,.learning-resource-list__required,.learning-resource-list__actions{grid-column:2}.learning-resource-list__actions{justify-content:flex-end}.learning-dialog__row{grid-template-columns:1fr}}
.learning-editor.is-compact{padding:12px;border-color:var(--ds-line);background:#fafafa;border-radius:12px}
.learning-editor.is-compact .learning-editor__toolbar{margin-top:0}
.learning-editor__compact-meta{margin-left:auto;color:var(--ds-muted);font-size:12px;font-weight:600}
.learning-editor__empty.is-compact{padding:14px;margin-top:10px}
.learning-editor.is-compact .learning-resource-list{margin-top:10px}
.learning-resource-list__type.is-embed{color:#1d4ed8;background:#dbeafe}
.learning-dialog__card--wide{width:min(640px,100%)}
.learning-dialog__hint{margin:0;color:var(--ds-muted);font-size:12px;line-height:1.5;font-weight:500}
.learning-dialog__url-row{display:grid;grid-template-columns:1fr auto;gap:8px;align-items:center}
.learning-dialog__preview{display:grid;grid-template-columns:minmax(0,1.2fr) minmax(0,.8fr);gap:12px;padding:10px;border:1px solid var(--ds-line);border-radius:12px;background:#fafafa}
.learning-dialog__preview-frame{aspect-ratio:16/9;border-radius:10px;overflow:hidden;background:#0f172a}
.learning-dialog__preview-frame iframe{width:100%;height:100%;border:0}
.learning-dialog__preview-meta{display:grid;align-content:start;gap:6px}
.learning-dialog__badge{display:inline-flex;width:fit-content;padding:3px 8px;border-radius:999px;background:#dbeafe;color:#1d4ed8;font-size:11px;font-weight:800}
.learning-dialog__preview-meta p{margin:0;color:var(--ds-muted);font-size:11px;line-height:1.45}
.learning-dialog__error{margin:0;color:#a33a24;font-size:12px}
@media(max-width:760px){.learning-dialog__preview{grid-template-columns:1fr}.learning-dialog__url-row{grid-template-columns:1fr}}
</style>
