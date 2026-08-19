<template>
  <main class="orep-page-shell" :class="{ 'is-immersive': immersive }">
    <router-view />
  </main>
</template>

<script setup>
defineProps({
  immersive: {
    type: Boolean,
    default: false,
  },
})
</script>

<style scoped>
.orep-page-shell {
  min-height: calc(100vh - var(--header-height));
  padding-top: var(--header-height);
  background: var(--orep-bg);
}

.orep-page-shell.is-immersive {
  min-height: 100vh;
  padding-top: 0;
}
</style>
