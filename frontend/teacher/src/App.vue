<template>
  <div class="teacher-app">
    <router-view />
  </div>
</template>

<style>
html,
body,
#app,
.teacher-app {
  width: 100%;
  height: 100%;
  margin: 0;
}
body {
  font-family: var(--ds-font-sans);
  color: var(--ds-ink);
  background: var(--ds-canvas);
  background-image: var(--ds-canvas-background);
  -webkit-font-smoothing: antialiased;
}
</style>
