<template>
  <div class="teacher-page">
    <header class="teacher-page__head">
      <div>
        <h1>{{ title }}</h1>
        <p>{{ desc }}</p>
      </div>
    </header>
    <section class="teacher-card">
      <div class="teacher-card__body teacher-empty">
        {{ desc }}
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const title = computed(() => route.meta?.title || '页面')
const desc = computed(() => route.meta?.placeholder || '框架已就绪，待接入业务。')
</script>
