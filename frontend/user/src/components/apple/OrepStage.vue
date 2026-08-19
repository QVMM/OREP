<template>
  <section class="orep-stage-card">
    <div class="orep-stage-card__copy">
      <p class="orep-stage-card__eyebrow">{{ eyebrow }}</p>
      <h1>{{ title }}</h1>
      <p class="orep-stage-card__subtitle">{{ subtitle }}</p>
      <div class="orep-stage-card__actions">
        <button class="orep-primary-action" type="button" @click="$emit('primary')">
          {{ primaryText }}
        </button>
        <button class="orep-secondary-action" type="button" @click="$emit('secondary')">
          {{ secondaryText }}
        </button>
      </div>
    </div>

    <div class="orep-stage-card__panel" aria-label="项目进度">
      <div class="orep-stage-card__project">
        <span class="orep-stage-card__project-icon">AI</span>
        <div>
          <strong>{{ projectName }}</strong>
          <small>{{ projectMeta }}</small>
        </div>
      </div>
      <div class="orep-stage-card__progress">
        <div class="orep-stage-card__progress-ring" :style="{ '--progress': completion }">
          <span>{{ completion }}%</span>
        </div>
        <div>
          <strong>{{ lastProgressLabel }}</strong>
          <small>{{ scoreLabel }}</small>
        </div>
      </div>
      <slot />
    </div>
  </section>
</template>

<script setup>
defineEmits(['primary', 'secondary'])

defineProps({
  eyebrow: { type: String, default: 'OREP ROADSHOW' },
  title: { type: String, required: true },
  subtitle: { type: String, required: true },
  primaryText: { type: String, default: '开始准备' },
  secondaryText: { type: String, default: '让 Agent 检查' },
  projectName: { type: String, required: true },
  projectMeta: { type: String, required: true },
  completion: { type: Number, default: 72 },
  lastProgressLabel: { type: String, required: true },
  scoreLabel: { type: String, required: true },
})
</script>

<style scoped>
.orep-stage-card {
  min-height: 430px;
  padding: 56px;
  border: 1px solid var(--orep-border-soft);
  border-radius: var(--orep-radius-stage);
  background:
    linear-gradient(115deg, oklch(1 0.003 255) 0%, oklch(0.985 0.012 250) 62%, oklch(0.94 0.035 255) 100%);
  box-shadow: var(--orep-shadow-stage);
  position: relative;
  overflow: hidden;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  align-items: center;
  gap: 40px;
}

.orep-stage-card::before {
  content: "";
  position: absolute;
  left: 8%;
  right: 8%;
  bottom: 26px;
  height: 8px;
  border-radius: 999px;
  background: linear-gradient(90deg, transparent, var(--orep-blue), transparent);
  opacity: 0.34;
  filter: blur(1px);
}

.orep-stage-card__copy,
.orep-stage-card__panel {
  position: relative;
  z-index: 1;
}

.orep-stage-card__eyebrow {
  margin: 0 0 18px;
  color: var(--orep-blue);
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 0;
}

.orep-stage-card h1 {
  margin: 0;
  max-width: 720px;
  color: var(--orep-text-strong);
  font-size: clamp(42px, 5vw, 72px);
  line-height: 1.04;
  letter-spacing: 0;
}

.orep-stage-card__subtitle {
  max-width: 620px;
  margin: 18px 0 0;
  color: var(--orep-muted);
  font-size: 18px;
  line-height: 1.7;
}

.orep-stage-card__actions {
  margin-top: 30px;
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.orep-stage-card__panel {
  border: 1px solid var(--orep-border-soft);
  border-radius: 28px;
  padding: 22px;
  background: oklch(1 0.003 255 / 0.76);
  box-shadow: var(--orep-shadow-soft);
  display: grid;
  gap: 18px;
}

.orep-stage-card__project,
.orep-stage-card__progress {
  display: flex;
  align-items: center;
  gap: 14px;
}

.orep-stage-card__project-icon,
.orep-stage-card__progress-ring {
  flex: 0 0 auto;
  width: 54px;
  height: 54px;
  border-radius: 18px;
  display: grid;
  place-items: center;
  background: var(--orep-blue-soft);
  color: var(--orep-blue);
  font-size: 14px;
  font-weight: 900;
}

.orep-stage-card__progress-ring {
  border-radius: 999px;
  background:
    radial-gradient(circle, var(--orep-surface-raised) 55%, transparent 56%),
    conic-gradient(var(--orep-blue) calc(var(--progress, 72) * 1%), var(--orep-blue-soft) 0);
}

.orep-stage-card__progress-ring span {
  font-size: 13px;
  font-weight: 900;
}

.orep-stage-card strong {
  display: block;
  color: var(--orep-text-strong);
  font-size: 15px;
  line-height: 1.35;
}

.orep-stage-card small {
  display: block;
  margin-top: 4px;
  color: var(--orep-muted);
  font-size: 12px;
  line-height: 1.45;
}

@media (max-width: 980px) {
  .orep-stage-card {
    padding: 36px;
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .orep-stage-card {
    min-height: auto;
    padding: 28px 22px 34px;
    border-radius: 26px;
  }

  .orep-stage-card h1 {
    font-size: 38px;
  }

  .orep-stage-card__subtitle {
    font-size: 16px;
  }
}
</style>
