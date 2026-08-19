<template>
  <AiAppShell mode="workspace" width="wide">
    <template #header>
      <AiAppHeader
        app="roadshow"
        mode="workspace"
        back-label="这场怎么讲"
        :back-to="`/roadshow/path/${id}`"
        title="讲稿对哪一页"
        subtitle="稿里写了翻页的用翻页，没写的你点一下"
      >
        <template #actions>
          <RouterLink class="student-primary-btn" :to="`/roadshow/path/${id}`">对完了</RouterLink>
        </template>
      </AiAppHeader>
    </template>

    <p class="rs-lede">没对上的页，系统不会改。现场演示不配新页。</p>
    <div class="rs-list">
      <div v-for="(row, i) in rows" :key="i" class="student-card rs-src">
        <b>{{ row.left }} → {{ row.right }} · <span :class="row.warn ? 'rs-warn' : 'rs-ok'">{{ row.warn ? '要你看一眼' : '已对上' }}</span></b>
        {{ row.note }}
      </div>
    </div>
  </AiAppShell>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import AiAppHeader from '../../components/ai-apps/AiAppHeader.vue'
import AiAppShell from '../../components/ai-apps/AiAppShell.vue'
import { getPath } from '../../services/roadshowPathClient.js'
import { actLabel } from './roadshowCopy.js'

const route = useRoute()
const id = computed(() => route.params.id)
const path = ref({})

const rows = computed(() => (path.value.propositions || []).map((p) => {
  const live = p.act === 'logistics' || p.printPage == null
  return {
    left: (p.spoken || '').slice(0, 36) + ((p.spoken || '').length > 36 ? '…' : ''),
    right: live ? '不配新页' : `第 ${p.printPage} 页 ${actLabel(p.act)}`,
    warn: live || String(p.spoken || '').length > 80,
    note: live ? '这段是交接或现场。PPT 停在当前页。' : (String(p.spoken || '').length > 80 ? '这一段比较长，确认是不是只对这一页。' : ''),
  }
}))

onMounted(async () => {
  const res = await getPath(id.value)
  path.value = res?.data || res || {}
})
</script>

<style src="./roadshow.css"></style>
