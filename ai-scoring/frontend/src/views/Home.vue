<template>
  <div class="home">
    <h1>AI Scoring System</h1>
    <p>智能 PPT 评分系统</p>
    <div class="actions">
      <router-link to="/ppt-editor" class="btn-primary">进入 PPT Agent</router-link>
      <router-link to="/generate" class="btn-secondary">旧版生成入口</router-link>
      <router-link to="/phase1/round1" class="btn-secondary">查看评分流程</router-link>
    </div>
  </div>
</template>

<script setup>
// Home page
</script>

<style scoped>
.home {
  text-align: center;
  padding: 3rem;
}

.actions {
  display: flex;
  gap: 1rem;
  justify-content: center;
  margin-top: 2rem;
}

.btn-primary,
.btn-secondary {
  padding: 0.75rem 1.5rem;
  border-radius: 4px;
  text-decoration: none;
  transition: background 0.3s;
}

.btn-primary {
  background: #42b983;
  color: #fff;
}

.btn-primary:hover {
  background: #3aa876;
}

.btn-secondary {
  background: #6c757d;
  color: #fff;
}

.btn-secondary:hover {
  background: #5a6268;
}
</style>
