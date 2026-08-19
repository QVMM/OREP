<template>
  <AiAppShell mode="landing" width="wide">
    <template #header>
      <AiAppHeader
        app="roadshow"
        mode="landing"
        back-label="用哪一份 PPT"
        back-to="/roadshow/ingest"
        :title="deck.title ? `已收下「${shortTitle}」` : '正在看这份 PPT'"
        :subtitle="deckSummary(deck)"
      >
        <template #actions>
          <RouterLink class="student-primary-btn" to="/roadshow">去对照讲稿</RouterLink>
        </template>
      </AiAppHeader>
    </template>

    <p class="rs-lede">原件不会改。下面只是读到的字。要改哪几页，回到路演台点「开始对照」。</p>
    <p v-if="err" class="rs-err">{{ err }}</p>

    <div class="rs-list">
      <div v-for="page in pages" :key="page.page" class="student-card rs-src">
        <b>
          第 {{ page.page }} 页 ·
          <span :class="page.grade === 'editable' ? 'rs-ok' : 'rs-warn'">{{ page.label }}</span>
        </b>
        {{ page.excerpt || emptyHint(page) }}
      </div>
    </div>
  </AiAppShell>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import AiAppHeader from '../../components/ai-apps/AiAppHeader.vue'
import AiAppShell from '../../components/ai-apps/AiAppShell.vue'
import { getLegacyPages } from '../../services/roadshowPathClient.js'
import { deckSummary } from './roadshowCopy.js'

const route = useRoute()
const deck = ref({})
const err = ref('')

const pages = computed(() => deck.value.pages || [])
const shortTitle = computed(() => String(deck.value.title || '这份 PPT').replace(/\.pptx$/i, ''))

onMounted(async () => {
  try {
    const res = await getLegacyPages(route.params.id)
    deck.value = res?.data || res || {}
  } catch (e) {
    err.value = e?.message || '这份现在看不了'
  }
})

function emptyHint(page) {
  if (page.grade === 'picture') return '整页是图，改不了上面的字。'
  if (page.grade === 'empty') return '没什么内容。'
  return ''
}
</script>

<style src="./roadshow.css"></style>
