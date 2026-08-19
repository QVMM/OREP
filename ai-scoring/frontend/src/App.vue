<template>
  <div id="app">
    <header class="app-header">
      <nav>
        <router-link to="/">首页</router-link>
        <router-link to="/ppt-editor">PPT Agent</router-link>
        <router-link to="/generate">PPT 生成</router-link>
        <router-link to="/phase1/round1">Round 1</router-link>
        <router-link to="/phase1/round2">Round 2</router-link>
        <router-link to="/phase1/round3">Round 3</router-link>
        <router-link to="/phase2">Phase 2</router-link>
      </nav>
    </header>
    <main class="app-main">
      <router-view />
    </main>
  </div>
</template>

<script setup>
// Root component with router navigation
</script>

<style scoped>
.app-header {
  background: #2c3e50;
  padding: 1rem;
}

.app-header nav {
  display: flex;
  gap: 1.5rem;
  justify-content: center;
}

.app-header nav a {
  color: #fff;
  text-decoration: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  transition: background 0.3s;
}

.app-header nav a:hover,
.app-header nav a.router-link-active {
  background: #42b983;
}

.app-main {
  padding: 2rem;
  max-width: 1200px;
  margin: 0 auto;
}
</style>
