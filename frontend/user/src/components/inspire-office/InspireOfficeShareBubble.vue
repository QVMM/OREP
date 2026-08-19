<template>
  <span ref="rootRef" class="io-share">
    <button
      type="button"
      class="io-share__trigger"
      :class="[triggerClass, { 'is-open': open }]"
      :title="triggerTitle"
      :aria-label="triggerTitle"
      :aria-expanded="open"
      :aria-haspopup="true"
      :disabled="disabled || !docId"
      @click.stop="toggle"
    >
      <slot>
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="18" cy="5" r="2.4" fill="none" stroke="currentColor" stroke-width="1.7"/>
          <circle cx="6" cy="12" r="2.4" fill="none" stroke="currentColor" stroke-width="1.7"/>
          <circle cx="18" cy="19" r="2.4" fill="none" stroke="currentColor" stroke-width="1.7"/>
          <path d="M8.2 10.9 15.8 6.6M8.2 13.1l7.6 4.3" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>
        </svg>
      </slot>
    </button>

    <Teleport to="body">
      <div
        v-if="open"
        class="io-share-mask"
        @click="close"
      />
      <div
        v-if="open"
        ref="panelRef"
        class="io-share-bubble"
        role="dialog"
        aria-label="确认分享"
        :style="panelStyle"
        @click.stop
      >
        <header class="io-share-bubble__head">
          <strong>分享邀请</strong>
          <button type="button" class="io-share-bubble__x" aria-label="关闭" @click="close">×</button>
        </header>
        <p class="io-share-bubble__hint">将复制以下文案，可粘贴到微信等发送给协作者：</p>
        <pre class="io-share-bubble__preview">{{ message }}</pre>
        <footer class="io-share-bubble__foot">
          <button type="button" class="io-share-bubble__btn" @click="close">取消</button>
          <button type="button" class="io-share-bubble__btn is-primary" :disabled="busy" @click="confirmCopy">
            {{ busy ? '复制中…' : '确认复制' }}
          </button>
        </footer>
      </div>
    </Teleport>
  </span>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  buildInspireOfficeShareMessage,
  buildInspireOfficeShareUrl,
  copyTextToClipboard,
} from '../../utils/inspireOfficeShare'

const props = defineProps({
  docId: { type: [String, Number], default: null },
  inviter: { type: String, default: '' },
  title: { type: String, default: '' },
  teamName: { type: String, default: '' },
  scope: { type: String, default: '' },
  ext: { type: String, default: '' },
  type: { type: String, default: '' },
  /** 触发按钮额外 class（对接工作台/列表样式） */
  triggerClass: { type: [String, Array, Object], default: '' },
  triggerTitle: { type: String, default: '分享邀请' },
  disabled: { type: Boolean, default: false },
  /** 气泡相对触发器的首选方向 */
  placement: { type: String, default: 'bottom-end' },
})

const emit = defineEmits(['copied', 'open', 'close'])

const open = ref(false)
const busy = ref(false)
const rootRef = ref(null)
const panelRef = ref(null)
const panelStyle = ref({})

const message = computed(() => {
  if (!props.docId) return ''
  return buildInspireOfficeShareMessage({
    docId: props.docId,
    inviter: props.inviter,
    title: props.title,
    teamName: props.teamName,
    scope: props.scope,
    ext: props.ext,
    type: props.type,
  })
})

function toggle() {
  if (props.disabled || !props.docId) return
  if (open.value) close()
  else openBubble()
}

async function openBubble() {
  open.value = true
  emit('open')
  await nextTick()
  placePanel()
  window.addEventListener('resize', placePanel)
  window.addEventListener('scroll', placePanel, true)
  window.addEventListener('keydown', onKeydown)
}

function close() {
  if (!open.value) return
  open.value = false
  emit('close')
  window.removeEventListener('resize', placePanel)
  window.removeEventListener('scroll', placePanel, true)
  window.removeEventListener('keydown', onKeydown)
}

function onKeydown(e) {
  if (e.key === 'Escape') close()
}

function placePanel() {
  const trigger = rootRef.value?.querySelector?.('.io-share__trigger') || rootRef.value
  if (!trigger) return
  const rect = trigger.getBoundingClientRect()
  const gap = 8
  const maxW = Math.min(360, window.innerWidth - 16)
  let left = rect.right - maxW
  if (left < 8) left = 8
  if (left + maxW > window.innerWidth - 8) left = window.innerWidth - maxW - 8

  // 优先在下方；空间不够则翻到上方
  const preferBottom = props.placement.startsWith('bottom')
  let top
  if (preferBottom) {
    top = rect.bottom + gap
    if (top + 220 > window.innerHeight && rect.top > 240) {
      top = Math.max(8, rect.top - gap - 220)
    }
  } else {
    top = Math.max(8, rect.top - gap - 220)
  }

  panelStyle.value = {
    position: 'fixed',
    top: `${Math.round(top)}px`,
    left: `${Math.round(left)}px`,
    width: `${maxW}px`,
    zIndex: 3200,
  }
}

async function confirmCopy() {
  if (busy.value || !props.docId) return
  busy.value = true
  try {
    const text = message.value || buildInspireOfficeShareMessage({
      docId: props.docId,
      inviter: props.inviter,
      title: props.title,
      teamName: props.teamName,
      scope: props.scope,
    })
    if (!text) throw new Error('无法生成分享文案')
    // 确保 URL 用实时域名
    if (!buildInspireOfficeShareUrl(props.docId)) throw new Error('无法生成访问地址')
    await copyTextToClipboard(text)
    ElMessage({
      type: 'success',
      message: '邀请文案已复制',
      duration: 1800,
      customClass: 'io-share-toast',
      offset: 56,
    })
    emit('copied', text)
    close()
  } catch (e) {
    ElMessage.error(e?.message || '复制失败')
  } finally {
    busy.value = false
  }
}

watch(
  () => props.docId,
  () => {
    if (open.value) placePanel()
  }
)

onBeforeUnmount(() => {
  window.removeEventListener('resize', placePanel)
  window.removeEventListener('scroll', placePanel, true)
  window.removeEventListener('keydown', onKeydown)
})
</script>

<style scoped>
.io-share {
  display: inline-flex;
  vertical-align: middle;
  align-items: center;
}

.io-share__trigger {
  appearance: none;
  margin: 0;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  font: inherit;
  color: inherit;
  background: transparent;
  border: 0;
  padding: 0;
}

/* 作为图标按钮时由外部 is-icon 控制尺寸；有文字时交给外部 io-btn 等 */
.io-share__trigger:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.io-share__trigger svg {
  width: 13px;
  height: 13px;
  display: block;
  flex: 0 0 auto;
}
</style>

<style>
/* Teleport 到 body，不用 scoped */
.io-share-mask {
  position: fixed;
  inset: 0;
  z-index: 3190;
  background: transparent;
}

.io-share-bubble {
  box-sizing: border-box;
  padding: 12px 12px 10px;
  border: 1px solid #e8eaed;
  border-radius: 14px;
  background: #fff;
  box-shadow: 0 16px 40px rgba(15, 23, 42, 0.14);
  color: #111827;
  font: 13px/1.45 system-ui, -apple-system, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

.io-share-bubble__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 6px;
}

.io-share-bubble__head strong {
  font-size: 13px;
  font-weight: 750;
}

.io-share-bubble__x {
  appearance: none;
  border: 0;
  background: transparent;
  width: 26px;
  height: 26px;
  border-radius: 8px;
  color: #6b7280;
  font-size: 18px;
  line-height: 1;
  cursor: pointer;
}

.io-share-bubble__x:hover {
  background: #f3f4f6;
  color: #111827;
}

.io-share-bubble__hint {
  margin: 0 0 8px;
  color: #6b7280;
  font-size: 12px;
  line-height: 1.4;
}

.io-share-bubble__preview {
  margin: 0;
  padding: 10px;
  max-height: 160px;
  overflow: auto;
  border: 1px solid #eef0f3;
  border-radius: 10px;
  background: #f8fafc;
  color: #1f2937;
  font: 12px/1.55 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  white-space: pre-wrap;
  word-break: break-all;
}

.io-share-bubble__foot {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 10px;
}

.io-share-bubble__btn {
  appearance: none;
  border: 1px solid #e5e7eb;
  background: #fff;
  color: #111827;
  border-radius: 9px;
  min-height: 32px;
  padding: 0 12px;
  font: 650 12px/1 inherit;
  cursor: pointer;
}

.io-share-bubble__btn:hover:not(:disabled) {
  background: #f3f4f6;
}

.io-share-bubble__btn.is-primary {
  border-color: transparent;
  background: #e5481d;
  color: #fff;
}

.io-share-bubble__btn.is-primary:hover:not(:disabled) {
  background: #d1431a;
}

.io-share-bubble__btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
</style>
