<template>
  <div class="student-page aac">
    <header class="aac__head">
      <div class="aac__head-text">
        <h1>AI 应用中心</h1>
        <p>选一个工具，立刻开始</p>
      </div>
      <span class="aac__count" aria-live="polite">{{ filteredApps.length }} 个应用</span>
    </header>

    <nav class="aac__filters" aria-label="应用分类">
      <button
        v-for="category in categories"
        :key="category.key"
        type="button"
        class="aac__chip"
        :class="{ 'is-active': activeCategory === category.key }"
        :aria-pressed="activeCategory === category.key"
        @click="activeCategory = category.key"
      >
        {{ category.label }}
      </button>
    </nav>

    <ul v-if="filteredApps.length" class="aac__grid">
      <li v-for="app in filteredApps" :key="app.key">
        <RouterLink
          :to="app.to"
          class="aac-card"
          :class="`is-${app.tone}`"
          :aria-label="`${app.action}：${app.name}`"
        >
          <div class="aac-card__top">
            <span class="aac-card__icon" aria-hidden="true">
              <XiaoQiMark v-if="app.key === 'assistant'" :size="28" :hoverable="false" />
              <component :is="app.icon" v-else />
            </span>
            <span class="aac-card__go" aria-hidden="true">
              <ArrowRight />
            </span>
          </div>

          <div class="aac-card__body">
            <div class="aac-card__title">
              <strong>{{ app.name }}</strong>
              <em>{{ categoryLabel(app.category) }}</em>
            </div>
            <p>{{ app.summary }}</p>
          </div>
        </RouterLink>
      </li>
    </ul>

    <div v-else class="aac__empty" role="status">
      <strong>这个分类下暂无应用</strong>
      <p>切换到「全部」看看其它工具。</p>
      <button type="button" class="student-secondary-btn" @click="activeCategory = ALL_CATEGORY_KEY">
        查看全部
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import {
  ArrowRight,
  Document,
  EditPen,
  FolderOpened,
  Flag,
  Picture,
} from '@element-plus/icons-vue'
import { RouterLink } from 'vue-router'
import XiaoQiMark from '../components/brand/XiaoQiMark.vue'

const ALL_CATEGORY_KEY = 'all'

const categoryDefinitions = [
  { key: 'roadshow', label: '路演', order: 10 },
  { key: 'skill', label: '训练', order: 20 },
  { key: 'office', label: '办公', order: 30 },
]

const apps = [
  {
    key: 'assistant',
    name: '小启 AI',
    category: 'roadshow',
    summary: '对话改稿、生成材料，备赛随时问',
    action: '打开',
    tone: 'xiaoqi',
    icon: Document,
    to: '/assistant',
  },
  {
    key: 'ppt',
    name: 'PPT 制作',
    category: 'roadshow',
    summary: '资料一键成演示稿，可继续改',
    action: '制作',
    tone: 'rose',
    icon: Picture,
    to: '/ppt-editor',
  },
  {
    key: 'roadshow-stage',
    name: '路演台',
    category: 'roadshow',
    summary: '按讲稿和评分排这场要讲的事，再做成能改的页',
    action: '打开',
    tone: 'amber',
    icon: Flag,
    to: '/roadshow',
  },
  // 讲稿制作：暂时下线，不在应用中心展示（路由仍保留，旧链接可打开）
  // {
  //   key: 'script',
  //   name: '讲稿制作',
  //   category: 'roadshow',
  //   summary: '整理现场讲解词，支持协作',
  //   action: '撰写',
  //   tone: 'amber',
  //   icon: Document,
  //   to: '/script-editor?tab=script',
  // },
  {
    key: 'typing',
    name: '智能打字',
    category: 'skill',
    summary: '跟打练习 + AI 诊断薄弱点',
    action: '练习',
    tone: 'sky',
    icon: EditPen,
    to: '/typing-practice',
  },
  {
    key: 'inspire-office',
    name: '启发 Office',
    category: 'office',
    summary: '在线 Word / Excel / 演示，可协同',
    action: '打开',
    tone: 'emerald',
    icon: FolderOpened,
    to: '/inspire-office',
  },
]

const categoryDefinitionMap = new Map(
  categoryDefinitions.map((category) => [category.key, category])
)

const activeCategory = ref(ALL_CATEGORY_KEY)

const categories = computed(() => {
  const used = new Set(apps.map((app) => app.category))
  const list = categoryDefinitions
    .filter((c) => used.has(c.key))
    .sort((a, b) => a.order - b.order)
  return [{ key: ALL_CATEGORY_KEY, label: '全部', order: 0 }, ...list]
})

const filteredApps = computed(() => {
  if (activeCategory.value === ALL_CATEGORY_KEY) return apps
  return apps.filter((app) => app.category === activeCategory.value)
})

function categoryLabel(categoryKey) {
  return categoryDefinitionMap.get(categoryKey)?.label || '其他'
}
</script>

<style scoped>
/* 拉满主内容区宽度，避免贴左 + 右侧大片空白 */
.aac {
  width: 100%;
  max-width: none;
  margin: 0;
  box-sizing: border-box;
}

/* —— 页头：与网格同宽 —— */
.aac__head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  margin: 0 0 18px;
}

.aac__head h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 700;
  letter-spacing: -0.03em;
  line-height: 1.25;
  color: var(--ds-ink, #111827);
}

.aac__head p {
  margin: 6px 0 0;
  font-size: 14px;
  line-height: 1.45;
  color: var(--ds-muted, #6b7280);
  font-weight: 500;
}

.aac__count {
  flex: 0 0 auto;
  font-size: 13px;
  font-weight: 600;
  color: #9ca3af;
  white-space: nowrap;
  padding-bottom: 2px;
}

/* —— 筛选：与网格同宽 —— */
.aac__filters {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 0 0 18px;
}

.aac__chip {
  appearance: none;
  border: 1px solid transparent;
  background: #f3f4f6;
  color: #4b5563;
  border-radius: 999px;
  min-height: 34px;
  padding: 0 16px;
  font: 650 13px/1 inherit;
  cursor: pointer;
  transition:
    background 0.15s ease,
    color 0.15s ease,
    border-color 0.15s ease;
}

.aac__chip:hover {
  background: #e5e7eb;
  color: #111827;
}

.aac__chip.is-active {
  background: #111827;
  color: #fff;
  border-color: #111827;
}

.aac__chip:focus-visible {
  outline: 2px solid color-mix(in srgb, var(--ds-orange, #e5481d) 70%, transparent);
  outline-offset: 2px;
}

/* —— 方案 A：2 列卡片网格，大屏 3 列 —— */
.aac__grid {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.aac-card {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 148px;
  height: 100%;
  padding: 18px;
  border-radius: 18px;
  border: 1px solid #e8eaed;
  background: #fff;
  text-decoration: none;
  color: inherit;
  box-shadow: 0 1px 0 rgba(15, 23, 42, 0.03);
  transition:
    border-color 0.15s ease,
    box-shadow 0.15s ease,
    background 0.15s ease,
    transform 0.15s ease;
}

.aac-card:hover {
  border-color: #d1d5db;
  background: #fafafa;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
}

.aac-card:active {
  transform: scale(0.995);
}

.aac-card:focus-visible {
  outline: 2px solid color-mix(in srgb, var(--ds-orange, #e5481d) 75%, transparent);
  outline-offset: 2px;
}

.aac-card__top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.aac-card__icon {
  width: 52px;
  height: 52px;
  border-radius: 15px;
  display: grid;
  place-items: center;
  flex-shrink: 0;
  color: #374151;
  background: #f3f4f6;
}

.aac-card__icon :deep(svg) {
  width: 24px;
  height: 24px;
}

.aac-card.is-xiaoqi .aac-card__icon {
  background: linear-gradient(145deg, #fff7ed, #ffedd5);
  color: #c2410c;
}

.aac-card.is-rose .aac-card__icon {
  background: #fff1f2;
  color: #e11d48;
}

.aac-card.is-amber .aac-card__icon {
  background: #fffbeb;
  color: #d97706;
}

.aac-card.is-sky .aac-card__icon {
  background: #eff6ff;
  color: #2563eb;
}

.aac-card.is-emerald .aac-card__icon {
  background: #ecfdf5;
  color: #059669;
}

.aac-card__go {
  width: 32px;
  height: 32px;
  border-radius: 999px;
  display: grid;
  place-items: center;
  color: #9ca3af;
  background: #f3f4f6;
  transition:
    color 0.15s ease,
    background 0.15s ease,
    transform 0.15s ease;
}

.aac-card__go :deep(svg) {
  width: 15px;
  height: 15px;
}

.aac-card:hover .aac-card__go {
  color: #111827;
  background: #e5e7eb;
  transform: translateX(2px);
}

.aac-card__body {
  min-width: 0;
  margin-top: auto;
}

.aac-card__title {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 6px;
}

.aac-card__title strong {
  font-size: 16px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: #111827;
  line-height: 1.3;
}

.aac-card__title em {
  font-style: normal;
  font-size: 12px;
  font-weight: 650;
  color: #9ca3af;
}

.aac-card__body p {
  margin: 0;
  font-size: 13px;
  line-height: 1.5;
  color: #6b7280;
  font-weight: 500;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* —— 空态：与网格同宽 —— */
.aac__empty {
  margin-top: 4px;
  padding: 48px 28px;
  border-radius: 18px;
  border: 1px dashed #e5e7eb;
  background: #fafafa;
  display: grid;
  gap: 6px;
  justify-items: start;
}

.aac__empty strong {
  font-size: 15px;
  color: #111827;
}

.aac__empty p {
  margin: 0 0 10px;
  font-size: 13px;
  color: #6b7280;
}

/* 宽屏：3 列更满、更稳 */
@media (min-width: 1200px) {
  .aac__grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 16px;
  }

  .aac-card {
    min-height: 156px;
    padding: 20px;
  }
}

/* 中窄屏保持 2 列 */
@media (max-width: 720px) {
  .aac__grid {
    grid-template-columns: 1fr;
    gap: 10px;
  }

  .aac-card {
    min-height: 0;
    padding: 14px 16px;
    flex-direction: row;
    align-items: center;
    gap: 14px;
  }

  .aac-card__top {
    flex-direction: column;
    gap: 0;
  }

  .aac-card__go {
    display: none;
  }

  .aac-card__body {
    margin-top: 0;
    flex: 1;
    min-width: 0;
  }

  .aac-card__body p {
    -webkit-line-clamp: 1;
  }

  .aac__head {
    align-items: flex-start;
    flex-direction: column;
    gap: 8px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .aac-card,
  .aac-card__go,
  .aac__chip {
    transition: none;
  }

  .aac-card:active {
    transform: none;
  }
}
</style>
