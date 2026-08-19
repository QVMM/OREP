<template>
  <div class="sdoc-collab" :class="{ 'is-coloring': colorByPerson }">
    <div class="sdoc-collab__people" role="list">
      <button
        v-for="peer in visiblePeers"
        :key="String(peer.userId || peer.sessionId)"
        type="button"
        class="sdoc-collab__avatar"
        :class="{ 'is-self': peer.sessionId === selfSession }"
        :style="{ '--sdoc-peer': peer.color }"
        :title="peerTitle(peer)"
        role="listitem"
        @mouseenter="hovered = peer"
        @mouseleave="hovered = null"
        @click="$emit('focus-peer', peer)"
      >
        <img :src="peer.avatar" :alt="peer.name" draggable="false" />
      </button>
      <span v-if="overflow > 0" class="sdoc-collab__more">+{{ overflow }}</span>
      <span v-if="!uniquePeers.length" class="sdoc-collab__empty">仅自己</span>
    </div>
    <div v-if="hovered" class="sdoc-collab__tip">
      <strong>{{ hovered.name }}</strong>
      <small>{{ roleLabel(hovered.role) }}{{ hovered.editing ? ' · 正在编辑' : ' · 在看' }}</small>
      <p>{{ hovered.inProtect ? '仅教师可见' : (hovered.preview || '正文') }}</p>
    </div>
    <button
      type="button"
      class="sdoc-collab__paint"
      :class="{ 'is-on': colorByPerson }"
      title="按人物给正文着色"
      @click="$emit('toggle-color')"
    >
      按人物着色
    </button>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { dedupePeersByUser, roleLabel } from './sdocCollab.js'

const props = defineProps({
  peers: { type: Array, default: () => [] },
  selfSession: { type: String, default: '' },
  colorByPerson: { type: Boolean, default: false },
})

defineEmits(['toggle-color', 'focus-peer'])

const hovered = ref(null)
const uniquePeers = computed(() => dedupePeersByUser(props.peers))
const visiblePeers = computed(() => uniquePeers.value.slice(0, 5))
const overflow = computed(() => Math.max(0, uniquePeers.value.length - 5))

function peerTitle(peer) {
  const state = peer.editing ? '正在编辑' : '在看'
  const preview = peer.inProtect ? '仅教师可见' : (peer.preview || '正文')
  return `${peer.name} · ${roleLabel(peer.role)} · ${state}：${preview}`
}
</script>
