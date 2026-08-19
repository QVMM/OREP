<template>
  <span class="sdoc-ico" :data-name="name" aria-hidden="true" v-html="svg" />
</template>

<script setup>
import { computed } from 'vue'
import { sdocIcon } from './sdocIcons.js'

const props = defineProps({
  name: { type: String, required: true },
})

const svg = computed(() => sdocIcon(props.name))
</script>
