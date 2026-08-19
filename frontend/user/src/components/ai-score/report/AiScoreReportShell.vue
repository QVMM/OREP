<template>
  <div
    class="report-shell"
    :class="{
      'is-overview': mode === 'overview',
      'is-editorial': mode === 'editorial'
    }"
  >
    <main class="report-main" :class="{ 'is-editorial': mode === 'editorial' }">
      <header
        v-if="mode !== 'editorial'"
        class="report-header"
        :class="{ 'is-overview': mode === 'overview' }"
      >
        <div v-if="mode === 'overview'" class="overview-title-row">
          <h1>{{ title }}</h1>
          <span class="subtitle-text">{{ subtitle }}</span>
        </div>
        <div v-else>
          <h1>
            {{ title }}
            <span class="report-mode-badge">证据审计台</span>
          </h1>
          <p>{{ subtitle }}</p>
        </div>
        <div v-show="mode !== 'overview'" class="report-actions">
          <slot name="actions" />
          <button type="button" class="secondary" @click="downloadPdf">下载 PDF</button>
          <button type="button" class="secondary" @click="goMeeting">← 返回路演</button>
        </div>
      </header>

      <nav v-if="mode !== 'overview' && mode !== 'editorial'" class="report-tabs" aria-label="AI评分报告导航">
        <RouterLink
          v-for="item in navItems"
          :key="item.key"
          :to="sectionPath(item.key)"
          class="tab-item"
          active-class="active"
        >
          <span class="tab-icon" aria-hidden="true">{{ tabIcon(item.key) }}</span>
          <span>{{ item.label }}</span>
        </RouterLink>
      </nav>

      <slot />
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { useAiScoreReportContext } from '../../../composables/useAiScoreReport'

defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
  mode: { type: String, default: '' }
})

const report = useAiScoreReportContext()

const navItems = report.navItems
const sectionPath = report.sectionPath
const goMeeting = report.goMeeting
const downloadPdf = report.downloadPdf

function tabIcon(key) {
  const icons = {
    result: '▤',
    todos: '☑',
    why: '↗',
    compare: '⇄',
    jury: '♙',
    // legacy keys (in case deep links still surface them)
    overview: '▤',
    dimensions: '▣',
    evidence: '↗',
    voice: '◴',
    presentation: '▱',
    actions: '☑'
  }
  return icons[key] || '•'
}
</script>

<style scoped>
.report-shell {
  min-height: calc(100vh - var(--workspace-header-height, var(--header-height, 64px)));
  max-width: 100%;
  overflow-x: clip;
  background: var(--ds-canvas, #f6f2ec);
  color: var(--ds-ink, #12141a);
  font-size: var(--ds-text-body-sm, 14px);
  font-family: var(--ds-font-sans, inherit);
}

.report-shell.is-editorial {
  /* 填满主区内容盒；页边距只来自 workspace-main */
  box-sizing: border-box;
  flex: 1 1 auto;
  width: 100%;
  min-width: 0;
  min-height: 0;
  height: 100%;
  max-height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: transparent;
  color: var(--ds-ink, #12141a);
  font-size: var(--ds-text-body, 15px);
  font-family: var(--ds-font-sans, inherit);
}

.report-main {
  min-width: 0;
  max-width: var(--ds-page-max, 1280px);
  width: 100%;
  margin: 0 auto;
  padding: 0;
  box-sizing: border-box;
  overflow-x: clip;
}

.report-main.is-editorial {
  flex: 1 1 auto;
  min-height: 0;
  min-width: 0;
  padding: 0;
  max-width: var(--ds-page-max, 1280px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* 子页根节点（result-page / why-page / todos-page）吃满剩余高度 */
.report-main.is-editorial > :deep(*) {
  flex: 1 1 auto;
  min-height: 0;
  min-width: 0;
}

.report-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 18px;
}

.report-header.is-overview {
  margin-bottom: 24px;
}

.overview-title-row {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 14px;
}

.overview-title-row h1 {
  margin: 0;
  color: #111827;
  font-size: 28px;
  font-weight: 900;
  line-height: 1.15;
}

.overview-title-row .subtitle-text {
  font-size: 13px;
  color: #55627a;
  font-weight: 500;
}

.report-header h1 {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0;
  color: #111827;
  font-size: 28px;
  font-weight: 900;
  line-height: 1.15;
}

.report-mode-badge {
  display: inline-flex;
  align-items: center;
  height: 26px;
  padding: 0 10px;
  border-radius: 6px;
  color: #0b706d;
  background: #e6f5f2;
  font-size: 13px;
  font-weight: 850;
}

.report-header p {
  margin: 8px 0 0;
  color: #55627a;
  font-size: 13px;
}

.report-tabs {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  align-items: stretch;
  margin-bottom: 18px;
  border: 1px solid #dfe5ee;
  border-radius: 6px;
  background: #fff;
  box-shadow: 0 1px 2px rgba(15, 23, 42, .03);
}

.tab-item {
  position: relative;
  min-height: 54px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  border-right: 1px solid #edf1f6;
  color: #667085;
  text-decoration: none;
  font-size: 14px;
  font-weight: 800;
}

.tab-item:last-child {
  border-right: 0;
}

.tab-item.active {
  color: #f15a24;
}

.tab-item.active::after {
  content: '';
  position: absolute;
  left: 8px;
  right: 8px;
  bottom: -1px;
  height: 4px;
  border-radius: 999px 999px 0 0;
  background: #f15a24;
}

.tab-icon {
  color: currentColor;
  font-size: 18px;
  line-height: 1;
}

.report-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: flex-end;
}

.report-actions button,
.report-actions :deep(button) {
  height: 38px;
  padding: 0 16px;
  border: 1px solid #aab3c0;
  border-radius: 3px;
  background: #fff;
  color: #111827;
  font-size: 13px;
  font-weight: 750;
  cursor: pointer;
}

.report-actions :deep(.primary) {
  border-color: #f15a24;
  background: #f15a24;
  color: #fff;
}

@media (max-width: 960px) {
  .report-header {
    flex-direction: column;
  }

  .report-tabs {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .tab-item {
    justify-content: flex-start;
    padding: 0 16px;
  }
}
</style>
