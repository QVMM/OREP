<template>
  <AiAppShell mode="landing" width="wide">
    <template #header>
      <AiAppHeader
        app="roadshow"
        mode="landing"
        back-label="AI 应用中心"
        back-to="/ai-apps"
        title="路演台"
        subtitle="把这场讲稿和 PPT 放一起。对照完再改，原件不会动。"
      >
        <template #actions>
          <button class="student-primary-btn" type="button" :disabled="!canStart || busy" @click="start">
            {{ busy ? '正在对照…' : '开始对照' }}
          </button>
        </template>
      </AiAppHeader>
    </template>

    <p class="rs-lede">你不用先选路。讲稿说什么、PPT 现在什么样，对上了才知道改哪几页。</p>
    <p v-if="err" class="rs-err">{{ err }}</p>

    <section class="student-card rs-claim">
      <div class="rs-kicker">1 · 这场讲稿</div>
      <h2 style="margin-top: 8px">{{ script ? (script.title || '讲稿') : '还没有讲稿' }}</h2>
      <p class="rs-lede" style="margin-bottom: 12px">
        {{ scriptHint }}
      </p>
      <div v-if="scripts.length > 1" class="rs-list">
        <button
          v-for="item in scripts"
          :key="item.id"
          type="button"
          class="student-card rs-item"
          :class="{ 'is-on': script && script.id === item.id }"
          @click="script = item"
        >
          <b>{{ item.title || `讲稿 ${item.id}` }}</b>
          <small>{{ item.sdocDocumentId ? '智能文档有正文' : '还没接到文档' }}{{ script && script.id === item.id && meterLabel ? ' · ' + meterLabel : '' }}</small>
        </button>
      </div>
      <div class="rs-acts">
        <a class="student-secondary-btn" href="/inspire-office">去写讲稿</a>
      </div>
    </section>

    <section class="student-card rs-claim" style="margin-top: 16px">
      <div class="rs-kicker">2 · 这场 PPT</div>
      <h2 style="margin-top: 8px">{{ deck ? prettyDeckTitle(deck.title) : '还没有交 PPT' }}</h2>
      <p class="rs-lede" style="margin-bottom: 12px">
        {{ deckHint }}
      </p>
      <div v-if="decks.length" class="rs-list">
        <button
          v-for="item in decks"
          :key="item.id || item.documentId"
          type="button"
          class="student-card rs-item"
          :class="{ 'is-on': deck && sameDeck(deck, item) }"
          @click="pickDeck(item)"
        >
          <b>{{ prettyDeckTitle(item.title) }}</b>
          <small>{{ item.pageCount ? `${item.pageCount} 页` : (item.ext || '') }} · {{ item.createdAt || item.updatedAt || '' }}</small>
        </button>
      </div>
      <DropFileUpload
        v-model="localFile"
        size="md"
        accept=".pptx"
        title="没有合适的，把 pptx 拖到这里"
        hint="松开就会收下。加了密码的请先解开。"
        accept-hint="只要 pptx"
        :max-size-mb="80"
        :disabled="busy"
      />
    </section>
  </AiAppShell>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import AiAppHeader from '../../components/ai-apps/AiAppHeader.vue'
import AiAppShell from '../../components/ai-apps/AiAppShell.vue'
import DropFileUpload from '../../components/base/DropFileUpload.vue'
import {
  attachDeck,
  compilePath,
  getScriptMeter,
  ingestLegacyDocument,
  ingestLegacyFile,
  listLegacyCandidates,
  listMyDecks,
  listMyScripts,
} from '../../services/roadshowPathClient.js'
import { pageHealth, prettyDeckTitle } from './roadshowCopy.js'

const router = useRouter()
const scripts = ref([])
const script = ref(null)
const decks = ref([])
const deck = ref(null)
const localFile = ref(null)
const busy = ref(false)
const err = ref('')
const meter = ref(null)

const meterLabel = computed(() => {
  const n = Number(meter.value?.scriptPageCount)
  if (!n) return ''
  return pageHealth(n).label
})
const scriptHint = computed(() => {
  if (!script.value) return '没有讲稿，对不上这份 PPT。先去智能文档写这场要说的话。'
  const pages = meterLabel.value
  if (pages) return `讲稿大约 ${pages}。没标翻页也会按结构估。健康区间 38–45 页。`
  if (script.value.sdocDocumentId) return '对照时用这一份。智能文档里有正文就按正文来，不用再抄一遍。'
  return '对照时用这一份。得有这场要说的话。'
})
const deckHint = computed(() => {
  if (!deck.value) return '把本机 pptx 拖进来。松开就会收下。'
  const n = Number(deck.value.pageCount) || 0
  const health = n ? pageHealth(n).label : ''
  return `已收下，页数不动。${health || (n ? n + ' 页' : '')}`
})
const canStart = computed(() => Boolean(script.value?.id && deck.value?.id))

function sameDeck(a, b) {
  if (!a || !b) return false
  if (a.id && b.id) return a.id === b.id
  return a.documentId && a.documentId === b.documentId
}

function unwrap(res) {
  return res?.data || res || []
}

async function loadMeter() {
  meter.value = null
  if (!script.value?.id) return
  try {
    const res = await getScriptMeter(script.value.id)
    meter.value = res?.data || res || null
  } catch {
    meter.value = null
  }
}

async function load() {
  try {
    const [sRes, dRes, cRes] = await Promise.all([
      listMyScripts(),
      listMyDecks(),
      listLegacyCandidates(),
    ])
    const list = unwrap(sRes)
    scripts.value = Array.isArray(list) ? list : []
    script.value = scripts.value.find((s) => s.sdocDocumentId && /讲稿/.test(s.title || ''))
      || scripts.value.find((s) => s.sdocDocumentId)
      || scripts.value[0]
      || null
    await loadMeter()
    const uploaded = unwrap(dRes)
    const office = (unwrap(cRes) || []).map((item) => ({
      ...item,
      id: item.id,
      title: item.title,
    }))
    decks.value = [...(Array.isArray(uploaded) ? uploaded : []), ...office]
    deck.value = decks.value.find((d) => d.id) || null
  } catch {
    scripts.value = []
  }
}

async function pickDeck(item) {
  err.value = ''
  if (item.id && item.kind === 'upload') {
    deck.value = item
    return
  }
  if (item.documentId || item.kind === 'office') {
    if (item.usable === false) {
      err.value = '这份还不是 pptx。请用 WPS 另存后再选。'
      return
    }
    busy.value = true
    try {
      const res = await ingestLegacyDocument(item.documentId)
      const saved = res?.data || res
      deck.value = { id: saved.id, title: saved.title, pageCount: saved.pageCount, kind: 'upload' }
      if (!decks.value.some((d) => d.id === saved.id)) decks.value.unshift(deck.value)
    } catch (e) {
      err.value = e?.message || '这份现在用不了'
    } finally {
      busy.value = false
    }
  }
}

watch(localFile, async (value) => {
  const file = Array.isArray(value) ? value[0] : value
  if (!file || busy.value) return
  busy.value = true
  err.value = ''
  try {
    const res = await ingestLegacyFile(file)
    const saved = res?.data || res
    deck.value = { id: saved.id, title: saved.title, pageCount: saved.pageCount, kind: 'upload' }
    decks.value = [deck.value, ...decks.value.filter((d) => d.id !== saved.id)]
  } catch (e) {
    err.value = e?.message || '这份现在用不了'
  } finally {
    busy.value = false
  }
})

async function start() {
  if (!script.value?.id) {
    err.value = '还没有讲稿。先去智能文档写这场要说的话。'
    return
  }
  if (!deck.value?.id) {
    err.value = '还没有 PPT。把文件拖进来，或选一份已经交过的。'
    return
  }
  busy.value = true
  err.value = ''
  try {
    const compiled = await compilePath(script.value.id)
    const path = compiled?.data || compiled
    const hasTalk = (path.propositions || []).some((p) => String(p.spoken || '').trim())
    if (!hasTalk) {
      err.value = '讲稿里还没写要说的话。先去智能文档写几句，再点开始对照。'
      return
    }
    await attachDeck(path.id, deck.value.id)
    router.push({ path: `/roadshow/fix/${path.id}` })
  } catch (e) {
    err.value = e?.message || '还对不上，稍后再试'
  } finally {
    busy.value = false
  }
}

watch(script, () => {
  loadMeter()
})

onMounted(load)
</script>

<style src="./roadshow.css"></style>
