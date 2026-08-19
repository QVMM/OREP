<template>
  <AiAppShell mode="workspace" width="wide">
    <template #header>
      <AiAppHeader
        app="roadshow"
        mode="workspace"
        back-label="路演台"
        back-to="/roadshow"
        :title="headerTitle"
        :subtitle="headerSub"
      >
        <template #actions>
          <button class="student-primary-btn" type="button" :disabled="!deckId || busy" @click="download">
            下载这份 PPT
          </button>
        </template>
      </AiAppHeader>
    </template>

    <p class="rs-lede">{{ summary }}</p>
    <p v-if="err" class="rs-err">{{ err }}</p>
    <p v-if="ok" class="rs-lede">{{ ok }}</p>

    <div v-if="deckPages.length" class="rs-layout">
      <aside class="rs-side">
        <div class="rs-h4">这份 {{ deckPages.length }} 页，点一页看</div>
        <button
          v-for="item in deckPages"
          :key="item.page"
          type="button"
          class="student-card rs-item"
          :class="{ 'is-on': page && page.page === item.page }"
          @click="select(item.page)"
        >
          <img
            class="rs-thumb"
            :src="previewUrl(item.page)"
            :alt="`第 ${item.page} 页`"
            loading="lazy"
          >
          <span class="rs-tag" :class="tagClass(item)">{{ shortStatus(item) }}</span>
          <b>第 {{ item.page }} 页</b>
        </button>
      </aside>

      <div v-if="page" class="rs-main">
        <section class="student-card rs-stage">
          <div class="rs-kicker">现在这一页</div>
          <div class="rs-stage-frame">
            <img
              class="rs-stage-img"
              :src="previewUrl(page.page)"
              :alt="`第 ${page.page} 页画面`"
            >
          </div>
        </section>
        <section class="student-card rs-claim">
          <div class="rs-kicker">讲稿对这页会说</div>
          <p class="rs-lede" style="margin: 8px 0 0">{{ speakText || '讲稿里对不上这页。先留着。' }}</p>
        </section>
        <section class="student-card rs-claim">
          <div class="rs-kicker">这一页</div>
          <p class="rs-lede" style="margin: 8px 0 0">{{ pageNote }}</p>
          <div class="rs-acts" style="margin-top: 16px">
            <button
              v-if="canEdit"
              class="student-primary-btn"
              type="button"
              :disabled="busy || page.applied"
              @click="apply"
            >
              {{ page.applied ? '这页已改' : '只改这页上的字' }}
            </button>
            <button class="student-secondary-btn" type="button" @click="nextNeed">
              {{ nextNeedLabel }}
            </button>
          </div>
        </section>
      </div>
    </div>
  </AiAppShell>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import AiAppHeader from '../../components/ai-apps/AiAppHeader.vue'
import AiAppShell from '../../components/ai-apps/AiAppShell.vue'
import { alignPath, applyLegacyPage, downloadLegacyDeck, slidePreviewUrl } from '../../services/roadshowPathClient.js'
import { pageHealth } from './roadshowCopy.js'

const route = useRoute()
const id = computed(() => route.params.id)
const err = ref('')
const ok = ref('')
const busy = ref(false)
const report = ref({ deck: { pages: [] } })
const selected = ref(1)
const bust = ref(Date.now())

const deckPages = computed(() => report.value.deck?.pages || [])
const page = computed(() => deckPages.value.find((p) => p.page === selected.value) || deckPages.value[0] || null)
const deckId = computed(() => report.value.deck?.id)
const headerTitle = computed(() => (page.value ? `第 ${page.value.page} 页 / 共 ${deckPages.value.length} 页` : '这份 PPT'))
const headerSub = computed(() => '对着页看。页数不动。')
const speakText = computed(() => cleanSpeak(page.value?.spoken))
const canEdit = computed(() => {
  if (!page.value || page.value.action !== 'edit') return false
  return !unsafeClaim(page.value.willTitle) && !unsafeClaim(page.value.willLine)
})
const pageNote = computed(() => {
  if (!page.value) return ''
  if (page.value.applied) return '这页字已经按讲稿改过。样子还是原来的。'
  if (canEdit.value) return page.value.why || '只改这页上已经有的字。'
  return '这页先留着。不要把讲稿整段糊上去。'
})
const needs = computed(() => deckPages.value.filter((p) => p.action === 'edit' && !unsafeClaim(p.willTitle)))
const summary = computed(() => {
  const deckN = Number(report.value.deckPageCount) || deckPages.value.length
  const scriptN = Number(report.value.scriptPageCount) || 0
  const n = needs.value.length
  const talk = scriptN ? `讲稿大约 ${pageHealth(scriptN).label}` : '讲稿还看不出页数'
  const deck = deckN ? `这份 PPT ${pageHealth(deckN).label}，页数不动` : ''
  return `${talk}。${deck}。${n ? `只有 ${n} 页值得改几个字，其余先留着。` : '没有必须改的页。'}健康区间 38–45 页。`
})
const nextNeedLabel = computed(() => (needs.value.length ? '下一处要对的' : '下一页'))

function previewUrl(n) {
  if (!deckId.value || !n) return ''
  return slidePreviewUrl(deckId.value, n, bust.value)
}
function cleanText(s) {
  return String(s || '')
    .replace(/&quot;/g, '"')
    .replace(/&apos;/g, "'")
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&amp;/g, '&')
    .replace(/^按讲稿\s*/, '')
    .trim()
}
function cleanSpeak(s) {
  let t = cleanText(s)
  if (/nitrogen|raw_data|ustruct|async def|"soil_/.test(t)) return ''
  if (t.length > 160) t = t.slice(0, 160) + '…'
  return t
}
function unsafeClaim(s) {
  const t = cleanText(s)
  if (!t) return false
  if (/nitrogen|raw_data|ustruct|&quot;/.test(t)) return true
  return t.includes('：') && t.length > 22
}
function shortStatus(item) {
  if (item.action === 'edit' && !unsafeClaim(item.willTitle)) return '可改字'
  return '先留着'
}
function tagClass(item) {
  return item.action === 'edit' && !unsafeClaim(item.willTitle) ? 'is-warn' : ''
}
function select(n) {
  selected.value = n
  ok.value = ''
  err.value = ''
}
function nextNeed() {
  const list = needs.value
  if (!list.length) {
    const i = deckPages.value.findIndex((p) => p.page === selected.value)
    selected.value = deckPages.value[(i + 1) % deckPages.value.length]?.page || selected.value
    return
  }
  const i = list.findIndex((p) => p.page === selected.value)
  selected.value = list[(i + 1) % list.length].page
}

async function apply() {
  if (!page.value || !deckId.value || !canEdit.value) return
  busy.value = true
  err.value = ''
  ok.value = ''
  try {
    await applyLegacyPage(deckId.value, {
      page: page.value.page,
      action: 'edit',
      title: page.value.willTitle || '',
      number: page.value.willNumber || '',
      line: page.value.willLine || '',
    })
    page.value.applied = true
    bust.value = Date.now()
    ok.value = '只改了这页上的字。上面画面是改完的。原来那份还在。'
  } catch (e) {
    err.value = e?.message || '这一页现在改不了'
  } finally {
    busy.value = false
  }
}

async function download() {
  if (!deckId.value) return
  busy.value = true
  err.value = ''
  try {
    const name = (report.value.deck?.title || '路演') + '.pptx'
    await downloadLegacyDeck(deckId.value, name)
  } catch (e) {
    err.value = e?.message || '下载失败'
  } finally {
    busy.value = false
  }
}

onMounted(async () => {
  try {
    const res = await alignPath(id.value)
    report.value = res?.data || res || { deck: { pages: [] } }
    selected.value = deckPages.value[0]?.page || 1
  } catch (e) {
    err.value = e?.message || '还对不上'
  }
})
</script>

<style src="./roadshow.css"></style>
