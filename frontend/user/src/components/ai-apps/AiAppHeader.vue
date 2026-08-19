<template>
  <header class="ai-app-header" :class="[`is-${mode}`, `is-${app}`]">
    <!-- Landing / Task：返回独立一行，标题对齐 student-page 页头 -->
    <template v-if="mode === 'landing' || mode === 'task'">
      <div class="ai-app-header__stack">
        <RouterLink
          :to="backTo"
          class="ai-app-header__back"
          :aria-label="`返回${backLabel}`"
        >
          <ArrowLeft aria-hidden="true" />
          <span>{{ backLabel }}</span>
        </RouterLink>

        <div class="ai-app-header__title-row">
          <div class="ai-app-header__copy">
            <h1>
              <input
                v-if="editableTitle"
                class="ai-app-header__title-input"
                type="text"
                :value="title"
                :maxlength="titleMaxlength"
                :aria-label="titleLabel"
                @input="emit('update:title', $event.target.value)"
                @blur="emit('titleBlur', $event)"
              />
              <template v-else>{{ title }}</template>
            </h1>
            <p v-if="subtitle">{{ subtitle }}</p>
          </div>

          <div class="ai-app-header__right">
            <p v-if="status" class="ai-app-header__status" role="status" aria-live="polite">{{ status }}</p>
            <nav v-if="$slots.localNavigation" class="ai-app-header__local-navigation" aria-label="应用内导航">
              <slot name="localNavigation" />
            </nav>
            <div v-if="$slots.actions" class="ai-app-header__actions">
              <slot name="actions" />
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- Workspace：紧凑顶栏 -->
    <template v-else>
      <div class="ai-app-header__main">
        <RouterLink
          :to="backTo"
          class="ai-app-header__back"
          :aria-label="`返回${backLabel}`"
        >
          <ArrowLeft aria-hidden="true" />
          <span>{{ backLabel }}</span>
        </RouterLink>

        <span class="ai-app-header__divider" aria-hidden="true"></span>

        <span v-if="context" class="ai-app-header__context">{{ context }}</span>

        <div class="ai-app-header__identity">
          <span class="ai-app-header__icon" aria-hidden="true">
            <component :is="applicationIcon" />
          </span>
          <div class="ai-app-header__copy">
            <h1>
              <input
                v-if="editableTitle"
                class="ai-app-header__title-input"
                type="text"
                :value="title"
                :maxlength="titleMaxlength"
                :aria-label="titleLabel"
                @input="emit('update:title', $event.target.value)"
                @blur="emit('titleBlur', $event)"
              />
              <template v-else>{{ title }}</template>
            </h1>
            <p v-if="subtitle">{{ subtitle }}</p>
          </div>
        </div>

        <nav v-if="$slots.localNavigation" class="ai-app-header__local-navigation" aria-label="应用内导航">
          <slot name="localNavigation" />
        </nav>
      </div>

      <div class="ai-app-header__right">
        <p v-if="status" class="ai-app-header__status" role="status" aria-live="polite">{{ status }}</p>
        <div v-if="$slots.actions" class="ai-app-header__actions">
          <slot name="actions" />
        </div>
      </div>
    </template>
  </header>
</template>

<script setup>
import { computed } from 'vue'
import { ArrowLeft, Document, EditPen, Flag, Picture } from '@element-plus/icons-vue'
import { RouterLink } from 'vue-router'

const props = defineProps({
  mode: {
    type: String,
    default: 'landing',
    validator: value => ['landing', 'task', 'workspace'].includes(value),
  },
  app: {
    type: String,
    required: true,
    validator: value => ['ppt', 'script', 'typing', 'inspire-office', 'roadshow'].includes(value),
  },
  backLabel: {
    type: String,
    required: true,
  },
  backTo: {
    type: [String, Object],
    required: true,
  },
  context: {
    type: String,
    default: '',
  },
  title: {
    type: String,
    required: true,
  },
  editableTitle: {
    type: Boolean,
    default: false,
  },
  titleMaxlength: {
    type: Number,
    default: 100,
    validator: value => Number.isInteger(value) && value > 0,
  },
  titleLabel: {
    type: String,
    default: '页面标题',
  },
  subtitle: {
    type: String,
    default: '',
  },
  status: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['update:title', 'titleBlur'])

const applicationIcon = computed(() => {
  if (props.app === 'ppt') return Picture
  if (props.app === 'typing') return EditPen
  if (props.app === 'roadshow') return Flag
  return Document
})
</script>
