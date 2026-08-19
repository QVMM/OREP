<template>
  <div class="sdoc-office">
    <div v-if="loading" class="sdoc-office__state">正在打开 {{ kindLabel }}…</div>
    <div v-else-if="error" class="sdoc-office__state is-error">
      <p>{{ error }}</p>
      <button type="button" @click="load">重试</button>
    </div>
    <iframe
      v-show="!loading && !error"
      ref="frame"
      class="sdoc-office__frame"
      :title="kindLabel"
      allow="fullscreen; clipboard-read; clipboard-write"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useSdocHost } from './sdocHost'
import { officeKind, officeKindLabel } from './sdocSplit'

const props = defineProps({
  documentId: { type: [String, Number], required: true },
  ext: { type: String, default: '' },
  documentType: { type: String, default: '' },
})

const host = useSdocHost()
const frame = ref(null)
const loading = ref(true)
const error = ref('')
const kindLabel = computed(() => officeKindLabel(officeKind({
  ext: props.ext,
  documentType: props.documentType,
})))

async function load() {
  loading.value = true
  error.value = ''
  if (!host.fetchEditorSession) {
    error.value = '当前入口不能打开 Word / PPT'
    loading.value = false
    return
  }
  try {
    const payload = await host.fetchEditorSession(props.documentId, 'edit')
    if (!payload?.editorUrl) throw new Error('未返回编辑地址')
    await Promise.resolve()
    if (frame.value) frame.value.src = payload.editorUrl
  } catch (err) {
    error.value = err?.message || '打开失败'
  } finally {
    loading.value = false
  }
}

watch(() => props.documentId, load)
onMounted(load)
</script>
