<template>
  <AiAppShell mode="workspace" width="wide">
    <template #header>
      <AiAppHeader
        app="roadshow"
        mode="workspace"
        back-label="路演台"
        back-to="/roadshow"
        :title="path.scriptTitle || '这场怎么讲'"
        :subtitle="subtitle"
      >
        <template #actions>
          <RouterLink v-if="path.legacyDeck" class="student-secondary-btn" :to="`/roadshow/fix/${id}`">对着这份改</RouterLink>
          <RouterLink class="student-secondary-btn" :to="`/roadshow/bind/${id}`">讲稿对哪一页</RouterLink>
          <button class="student-primary-btn" type="button" :disabled="!ready || busy" @click="onConfirm">
            {{ busy ? '正在做页…' : path.legacyDeck ? '另做一套页' : '做成 PPT' }}
          </button>
        </template>
      </AiAppHeader>
    </template>

    <p v-if="!ready" class="rs-lede">还有内容没有出处，先决定这场写不写进 PPT。</p>
    <p v-if="err" class="rs-err">{{ err }}</p>
    <p v-if="path.legacyDeck" class="rs-lede">
      已收下「{{ path.legacyDeck.title }}」，原件不会改。先确认这场怎么讲，再对着改。
    </p>

    <div v-if="path.id" class="rs-layout">
      <aside class="rs-side">
        <div class="rs-h4">这场要讲清这些</div>
        <button
          v-for="(p, i) in path.propositions || []"
          :key="p.id || i"
          type="button"
          class="student-card rs-item"
          :class="{ 'is-on': sel === i }"
          @click="sel = i"
        >
          <span class="rs-tag" :class="p.printPage ? '' : 'is-warn'">{{ p.printPage ? '可以上 PPT' : '不配页' }}</span>
          <b>{{ slideTitle(p) }}</b>
          <small>第 {{ p.printPage || '—' }} 页 · {{ p.role || '' }}</small>
        </button>
        <div class="rs-h4">这场先别写上 PPT</div>
        <button
          v-for="h in path.holes || []"
          :key="h.id"
          type="button"
          class="student-card rs-item"
          @click="selHole = h.id"
        >
          <span class="rs-tag" :class="h.acked ? '' : 'is-bad'">{{ h.acked ? '这场不写' : '先别写' }}</span>
          <b>{{ holeTitle(h) }}</b>
        </button>
      </aside>
      <section class="rs-main">
        <article v-if="current" class="student-card rs-claim">
          <div class="rs-kicker">{{ actLabel(current.act) }}</div>
          <h2>{{ slideTitle(current) }}</h2>
          <div class="rs-src"><b>你会说</b>{{ current.spoken }}</div>
          <div class="rs-src"><b>这页只写</b>{{ slideLine(current) }}</div>
        </article>
        <div v-for="h in openHoles" :key="h.id" class="rs-hole">
          <strong>{{ holeTitle(h) }}</strong>
          <p>{{ h.why }}</p>
          <div class="rs-acts">
            <button class="student-primary-btn" type="button" @click="onAck(h.id)">这场先不写</button>
          </div>
        </div>
      </section>
    </div>
  </AiAppShell>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AiAppHeader from '../../components/ai-apps/AiAppHeader.vue'
import AiAppShell from '../../components/ai-apps/AiAppShell.vue'
import { ackHole, confirmPath, getPath, printPath } from '../../services/roadshowPathClient.js'
import { actLabel, canMakePpt, holeTitle } from './roadshowCopy.js'

const route = useRoute()
const router = useRouter()
const id = computed(() => route.params.id)
const path = ref({})
const sel = ref(0)
const selHole = ref('')
const err = ref('')
const busy = ref(false)

const current = computed(() => (path.value.propositions || [])[sel.value] || null)
const openHoles = computed(() => (path.value.holes || []).filter((h) => !h.acked))
const ready = computed(() => canMakePpt(path.value))
const subtitle = computed(() => {
  const n = (path.value.propositions || []).length
  return n ? `${n} 件事要讲清` : '用的是这份讲稿和这次评分'
})

function slideTitle(p) {
  return p?.onSlide?.title || actLabel(p?.act)
}
function slideLine(p) {
  const o = p?.onSlide || {}
  return [o.title, o.number, o.line].filter(Boolean).join(' · ')
}

async function load() {
  const res = await getPath(id.value)
  path.value = res?.data || res || {}
}

async function onAck(holeId) {
  err.value = ''
  const res = await ackHole(id.value, holeId)
  path.value = res?.data || res || path.value
}

async function onConfirm() {
  if (!ready.value || busy.value) return
  err.value = ''
  busy.value = true
  try {
    await confirmPath(id.value)
    await printPath(id.value)
    router.push({ path: `/roadshow/print/${id.value}` })
  } catch (e) {
    err.value = e?.message || '还不能做成 PPT'
  } finally {
    busy.value = false
  }
}

onMounted(load)
</script>

<style src="./roadshow.css"></style>
