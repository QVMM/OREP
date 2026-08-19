<template>
  <header class="coach-chrome" data-testid="coach-report-chrome">
    <div class="coach-chrome__bar">
      <nav class="coach-tabs" role="tablist" aria-label="评分报告">
        <RouterLink
          class="coach-tab"
          :class="{ 'is-active': active === 'result' }"
          :to="sectionPath('result')"
          role="tab"
          :aria-selected="active === 'result'"
        >
          结果
        </RouterLink>
        <RouterLink
          class="coach-tab"
          :class="{ 'is-active': active === 'todos' }"
          :to="sectionPath('todos')"
          role="tab"
          :aria-selected="active === 'todos'"
        >
          待办
          <span v-if="todoCount != null && todoCount !== ''" class="coach-tab__count">{{ todoCount }}</span>
        </RouterLink>
        <RouterLink
          class="coach-tab"
          :class="{ 'is-active': active === 'why' }"
          :to="sectionPath('why')"
          role="tab"
          :aria-selected="active === 'why'"
        >
          依据
        </RouterLink>
      </nav>

      <div class="coach-chrome__right">
        <div class="coach-score" aria-label="本场得分">
          <span>得分</span>
          <strong>{{ scoreDisplay }}</strong>
          <small>/100</small>
        </div>
        <div class="coach-actions">
          <button type="button" class="coach-btn coach-btn--ghost" @click="onDownload">下载</button>
          <button type="button" class="coach-btn coach-btn--ghost" @click="onBack">返回</button>
          <button v-if="showSync" type="button" class="coach-btn coach-btn--primary" @click="$emit('sync')">
            同步任务
          </button>
        </div>
      </div>
    </div>

    <div class="coach-chrome__title">
      <h1>{{ title }}</h1>
      <p v-if="description">{{ description }}</p>
    </div>
  </header>
</template>

<script setup>
import { RouterLink } from 'vue-router'
import { useAiScoreReportContext } from '../../../composables/useAiScoreReport'

defineProps({
  active: { type: String, required: true },
  title: { type: String, required: true },
  description: { type: String, default: '' },
  scoreDisplay: { type: [String, Number], default: '—' },
  todoCount: { type: [Number, String], default: null },
  showSync: { type: Boolean, default: true }
})

defineEmits(['sync'])

const report = useAiScoreReportContext()
const sectionPath = report.sectionPath

function onDownload() {
  report.downloadPdf?.()
}

function onBack() {
  report.goMeeting?.()
}
</script>

<style scoped>
.coach-chrome {
  margin: 0 0 var(--ds-space-5);
}

.coach-chrome__bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--ds-space-4);
  flex-wrap: wrap;
  min-height: 48px;
  padding-bottom: var(--ds-space-4);
  border-bottom: 1px solid var(--ds-line);
}

.coach-tabs {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  min-width: 0;
  padding: 3px;
  border-radius: var(--ds-radius-pill);
  background: var(--ds-canvas-deep);
}

.coach-tab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 34px;
  padding: 0 14px;
  border-radius: var(--ds-radius-pill);
  color: var(--ds-muted);
  font-size: var(--ds-text-body-sm);
  font-weight: var(--ds-weight-semibold);
  text-decoration: none;
  transition:
    background var(--ds-control-transition),
    color var(--ds-control-transition),
    box-shadow var(--ds-control-transition);
}

.coach-tab:hover {
  color: var(--ds-ink);
  background: rgba(255, 255, 255, 0.55);
}

.coach-tab.is-active {
  color: var(--ds-orange-deep);
  background: var(--ds-surface-solid);
  box-shadow: 0 1px 2px rgba(18, 20, 26, 0.06);
}

.coach-tab__count {
  min-width: 18px;
  padding: 0 6px;
  border-radius: var(--ds-radius-pill);
  background: rgba(18, 20, 26, 0.06);
  color: inherit;
  font-size: var(--ds-text-micro);
  line-height: 18px;
  text-align: center;
  transition: background var(--ds-control-transition);
}

.coach-tab.is-active .coach-tab__count {
  background: var(--ds-orange-soft);
}

.coach-chrome__right {
  display: flex;
  align-items: center;
  gap: var(--ds-space-4);
  flex-wrap: wrap;
}

.coach-score {
  display: inline-flex;
  align-items: baseline;
  gap: 4px;
  padding: 6px 12px;
  border-radius: var(--ds-radius-md);
  background: var(--ds-surface-solid);
  border: 1px solid var(--ds-line);
  color: var(--ds-faint);
  font-size: var(--ds-text-caption);
  font-weight: var(--ds-weight-semibold);
}

.coach-score strong {
  color: var(--ds-ink);
  font-size: 22px;
  font-weight: var(--ds-weight-bold);
  font-family: var(--ds-font-num);
  letter-spacing: -0.02em;
  line-height: 1;
}

.coach-score small {
  color: var(--ds-faint);
  font-size: var(--ds-text-caption);
  font-weight: var(--ds-weight-medium);
}

.coach-actions {
  display: flex;
  gap: var(--ds-space-2);
}

.coach-btn {
  box-sizing: border-box;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: var(--ds-btn-height-sm);
  padding: 0 var(--ds-btn-padding-x-sm);
  border-radius: var(--ds-radius-pill);
  border: 1px solid transparent;
  font: inherit;
  font-size: var(--ds-btn-font-sm);
  font-weight: 700;
  cursor: pointer;
  transition:
    background var(--ds-control-transition),
    border-color var(--ds-control-transition),
    color var(--ds-control-transition),
    transform var(--ds-control-transition);
}

.coach-btn:active {
  transform: translateY(var(--ds-motion-press-y));
}

.coach-btn:focus-visible {
  outline: var(--ds-focus-outline);
  outline-offset: var(--ds-focus-offset);
}

.coach-btn--ghost {
  border-color: var(--ds-btn-secondary-border);
  color: var(--ds-btn-secondary-fg);
  background: var(--ds-btn-secondary-bg);
}

.coach-btn--ghost:hover {
  background: var(--ds-btn-secondary-bg-hover);
  border-color: var(--ds-btn-secondary-border-hover);
}

.coach-btn--primary {
  color: var(--ds-btn-primary-fg);
  background: var(--ds-btn-primary-bg);
}

.coach-btn--primary:hover {
  background: var(--ds-btn-primary-bg-hover);
}

.coach-chrome__title {
  margin-top: var(--ds-space-5);
}

.coach-chrome__title h1 {
  margin: 0;
  color: var(--ds-ink);
  font-size: var(--ds-text-h1);
  font-weight: var(--ds-weight-bold);
  line-height: var(--ds-leading-title);
}

.coach-chrome__title p {
  margin: var(--ds-space-2) 0 0;
  max-width: 42em;
  color: var(--ds-muted);
  font-size: var(--ds-text-body-sm);
  line-height: var(--ds-leading-body);
}

@media (max-width: 720px) {
  .coach-chrome__bar {
    align-items: stretch;
  }

  .coach-chrome__right {
    width: 100%;
    justify-content: space-between;
  }

  .coach-tabs {
    width: 100%;
  }

  .coach-tab {
    flex: 1;
    justify-content: center;
  }
}

@media (prefers-reduced-motion: reduce) {
  .coach-tab,
  .coach-btn {
    transition: none;
  }
}
</style>
