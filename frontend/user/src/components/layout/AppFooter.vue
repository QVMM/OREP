<template>
  <footer class="app-footer">
    <div class="footer-inner">
      <div class="footer-copyright">
        © {{ currentYear }} 竞赛大脑 COMPETITION BRAIN. All rights reserved.
      </div>
      <nav class="footer-links">
        <a href="/privacy" class="footer-link">隐私政策</a>
        <a href="/terms" class="footer-link">服务条款</a>
        <a href="/contact" class="footer-link">联系我们</a>
      </nav>
    </div>
  </footer>
</template>

<script setup>
const currentYear = new Date().getFullYear()
</script>

<style scoped>
.app-footer {
  background: var(--bg-primary);
  border-top: 1px solid var(--border-light);
  padding: var(--spacing-lg) 0;
}

.footer-inner {
  max-width: var(--content-max-width);
  margin: 0 auto;
  padding: 0 var(--spacing-xl);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.footer-copyright {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  line-height: var(--line-height-normal);
}

.footer-links {
  display: flex;
  align-items: center;
  gap: var(--spacing-lg);
}

.footer-link {
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
  text-decoration: none;
  transition: color var(--transition-fast);
}

.footer-link:hover {
  color: var(--color-primary);
}

@media (max-width: 768px) {
  .footer-inner {
    flex-direction: column;
    gap: var(--spacing-sm);
    text-align: center;
    padding: 0 var(--spacing-md);
  }
}
</style>
