<template>
  <article class="rs-slide">
    <div class="rs-slide-k">{{ page.kicker || '页' }}</div>
    <h2>{{ page.title || '这一页' }}</h2>
    <div v-if="leftRight" class="rs-slide-pair">
      <div>
        <b>{{ leftRight[0] }}</b>
        <small>之前</small>
      </div>
      <span>→</span>
      <div>
        <b>{{ leftRight[1] }}</b>
        <small>现在</small>
      </div>
    </div>
    <div v-else-if="page.number" class="rs-slide-num">{{ page.number }}</div>
    <div v-if="page.line" class="rs-slide-line">{{ page.line }}</div>
    <ul v-if="page.blocks?.length" class="rs-slide-blocks">
      <li v-for="block in page.blocks" :key="block">{{ block }}</li>
    </ul>
  </article>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  page: { type: Object, default: () => ({}) },
})

const leftRight = computed(() => {
  const raw = String(props.page?.number || '')
  if (!raw.includes('→') && !raw.includes('->')) return null
  const parts = raw.split(/\s*(?:→|->)\s*/)
  return parts.length === 2 ? parts : null
})
</script>
