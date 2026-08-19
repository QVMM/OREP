<template>
  <div class="version-diff">
    <h3>版本对比</h3>
    <div class="diff-container">
      <div class="version old">
        <h4>旧版本</h4>
        <div class="version-content">
          <slot name="old"></slot>
        </div>
      </div>
      <div class="version new">
        <h4>新版本</h4>
        <div class="version-content">
          <slot name="new"></slot>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
// Version Diff Component - displays differences between versions
</script>

<style scoped>
.version-diff {
  background: #fff;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 1rem;
}

.diff-container {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  margin-top: 1rem;
}

.version h4 {
  margin-bottom: 0.5rem;
  padding: 0.5rem;
  background: #f5f5f5;
  border-radius: 4px;
}

.version-content {
  padding: 1rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  min-height: 200px;
}
</style>
