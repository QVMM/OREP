<template>
  <AiAppShell mode="workspace" width="wide">
    <template #header>
      <AiAppHeader
        app="roadshow"
        mode="workspace"
        back-label="这场怎么讲"
        :back-to="`/roadshow/path/${id}`"
        :title="`这 ${pages.length} 页`"
        :subtitle="minutesLabel(pages.length)"
      >
        <template #actions>
          <RouterLink class="student-secondary-btn" :to="`/roadshow/bind/${id}`">讲稿对哪一页</RouterLink>
          <button class="student-primary-btn" type="button" :disabled="!pages.length || busy" @click="onDownload">
            {{ busy ? '正在准备…' : '下载 PPT' }}
          </button>
        </template>
      </AiAppHeader>
    </template>

    <p v-if="err" class="rs-err">{{ err }}</p>
    <div v-else-if="!pages.length" class="rs-lede">还没有页。先回到这场怎么讲，确认后再做。</div>
    <div v-else class="rs-print">
      <div class="rs-phases">
        <span v-for="chip in chips" :key="chip">{{ chip }}</span>
        <span class="rs-phase-note">一页只讲一件事。交接不用单独做页。下载后页上的字都能改。</span>
      </div>
      <div class="rs-print-stage">
        <RoadshowSlide :page="current" />
      </div>
      <div class="rs-grid">
        <button
          v-for="(page, i) in pages"
          :key="page.page || i"
          type="button"
          class="student-card rs-pcard"
          :class="{ 'is-on': sel === i }"
          @click="sel = i"
        >
          <div class="th">
            <div class="t">P{{ padPage(page.page || i + 1) }} · {{ page.kicker }}</div>
            <div class="c">{{ page.title }}</div>
          </div>
          <div class="meta">
            <b>{{ page.kicker }}</b>
            {{ page.number || page.line || '能改字' }}
          </div>
        </button>
      </div>
    </div>
  </AiAppShell>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import AiAppHeader from '../../components/ai-apps/AiAppHeader.vue'
import AiAppShell from '../../components/ai-apps/AiAppShell.vue'
import { downloadPptx, getPath, printPath } from '../../services/roadshowPathClient.js'
import { canMakePpt, minutesLabel, padPage, phaseChips } from './roadshowCopy.js'
import RoadshowSlide from './RoadshowSlide.vue'

const route = useRoute()
const id = computed(() => route.params.id)
const path = ref({})
const sel = ref(0)
const err = ref('')
const busy = ref(false)

const pages = computed(() => path.value.printPages || [])
const current = computed(() => pages.value[sel.value] || pages.value[0] || {})
const chips = computed(() => phaseChips(pages.value))

async function load() {
  err.value = ''
  const res = await getPath(id.value)
  path.value = res?.data || res || {}
  if (pages.value.length) return
  if (!canMakePpt(path.value)) {
    err.value = '还有内容没有出处，先决定这场写不写进 PPT。'
    return
  }
  try {
    const printed = await printPath(id.value)
    path.value = printed?.data || printed || path.value
  } catch (e) {
    err.value = e?.message || '还不能做成 PPT'
  }
}

async function onDownload() {
  if (!pages.value.length || busy.value) return
  busy.value = true
  err.value = ''
  try {
    const title = path.value.scriptTitle || '路演'
    await downloadPptx(id.value, `${title} · 路演台.pptx`)
  } catch (e) {
    err.value = e?.message || '下载失败'
  } finally {
    busy.value = false
  }
}

onMounted(load)
</script>

<style src="./roadshow.css"></style>
