<template>
  <AiAppShell mode="landing" width="wide">
    <template #header>
      <AiAppHeader
        app="roadshow"
        mode="landing"
        back-label="路演台"
        back-to="/roadshow"
        title="用哪一份 PPT？"
        subtitle="改动会另存一份。原来那份还在。微信、网盘里的文件，先存到电脑再拖进来。"
      />
    </template>

    <p v-if="err" class="rs-err">{{ err }}</p>
    <p v-if="hint" class="rs-lede">{{ hint }}</p>

    <section>
      <div class="rs-h4">项目里已经有</div>
      <p v-if="loading" class="rs-lede">正在看文档库…</p>
      <div v-else-if="candidates.length" class="rs-list">
        <button
          v-for="item in candidates"
          :key="item.documentId"
          type="button"
          class="student-card is-interactive rs-item"
          :disabled="busy"
          @click="useOffice(item)"
        >
          <span class="rs-tag" :class="item.usable ? '' : 'is-warn'">{{ item.usable ? '能用' : '请另存为 pptx' }}</span>
          <b>{{ prettyDeckTitle(item.title) }}</b>
          <small>{{ item.ext }} · {{ sizeLabel(item.sizeBytes) }} · {{ item.updatedAt?.slice(0, 16) || '' }}</small>
        </button>
      </div>
      <p v-else class="rs-lede">文档库里还没有演示文件。把本机 pptx 拖进来也可以。</p>
    </section>

    <section class="rs-upload">
      <div class="rs-h4">本机文件</div>
      <DropFileUpload
        v-model="localFile"
        size="md"
        accept=".pptx"
        title="把 pptx 拖到这里"
        hint="松开就会收下。加了密码的请先解开。大于 80 页或 80MB 请先删附录。"
        accept-hint="只要 pptx"
        :max-size-mb="80"
        :disabled="busy"
      />
      <div class="rs-acts" style="margin-top: 12px">
        <button class="student-primary-btn" type="button" :disabled="!localFile || busy" @click="useLocal">
          {{ busy ? '正在收下…' : '用这份' }}
        </button>
        <RouterLink class="student-secondary-btn" to="/roadshow">返回路演台</RouterLink>
      </div>
    </section>
  </AiAppShell>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import AiAppHeader from '../../components/ai-apps/AiAppHeader.vue'
import AiAppShell from '../../components/ai-apps/AiAppShell.vue'
import DropFileUpload from '../../components/base/DropFileUpload.vue'
import {
  ingestLegacyDocument,
  ingestLegacyFile,
  listLegacyCandidates,
  listMyDecks,
} from '../../services/roadshowPathClient.js'
import { prettyDeckTitle } from './roadshowCopy.js'

const router = useRouter()
const candidates = ref([])
const localFile = ref(null)
const loading = ref(true)
const busy = ref(false)
const err = ref('')
const hint = ref('')

watch(localFile, (value) => {
  if (value && !busy.value) useLocal()
})

onMounted(async () => {
  try {
    const [mine, office] = await Promise.all([listMyDecks(), listLegacyCandidates()])
    const uploaded = (mine?.data || mine || []).map((d) => ({
      ...d,
      documentId: d.id,
      usable: true,
      fromUpload: true,
    }))
    const listed = office?.data || office || []
    candidates.value = [...uploaded, ...listed]
  } catch {
    candidates.value = []
  } finally {
    loading.value = false
  }
})

function sizeLabel(n) {
  const v = Number(n) || 0
  if (v < 1024) return `${v} B`
  if (v < 1024 * 1024) return `${Math.round(v / 1024)} KB`
  return `${(v / 1024 / 1024).toFixed(1)} MB`
}

async function afterDeck(deck) {
  if (!deck?.id) {
    err.value = '这份现在用不了'
    return
  }
  router.push({ path: `/roadshow/analyze/${deck.id}` })
}

async function useOffice(item) {
  if (item.fromUpload && item.id) {
    router.push({ path: `/roadshow/analyze/${item.id}` })
    return
  }
  if (!item.usable) {
    err.value = '这份还不是 pptx。请用 WPS 另存后再选。'
    return
  }
  busy.value = true
  err.value = ''
  try {
    const res = await ingestLegacyDocument(item.documentId)
    await afterDeck(res?.data || res)
  } catch (e) {
    err.value = e?.message || '这份现在用不了'
  } finally {
    busy.value = false
  }
}

async function useLocal() {
  const file = Array.isArray(localFile.value) ? localFile.value[0] : localFile.value
  if (!file) return
  busy.value = true
  err.value = ''
  try {
    const res = await ingestLegacyFile(file)
    await afterDeck(res?.data || res)
  } catch (e) {
    err.value = e?.message || '这份现在用不了'
  } finally {
    busy.value = false
  }
}
</script>

<style src="./roadshow.css"></style>
