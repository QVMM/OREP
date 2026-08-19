<template>
  <section class="evidence-bundle-panel">
    <div class="bundle-head">
      <div>
        <span>EVIDENCE BUNDLE</span>
        <strong>评分证据快照</strong>
        <small>{{ statusText }}</small>
      </div>
      <button v-if="canPrepare" type="button" :disabled="loading" @click="$emit('prepare')">
        {{ loading ? '生成中' : '生成证据快照' }}
      </button>
    </div>

    <div class="bundle-grid">
      <article>
        <span>转写片段</span>
        <strong>{{ bundle?.transcriptSegmentCount ?? 0 }}</strong>
      </article>
      <article>
        <span>关键帧</span>
        <strong>{{ bundle?.frameCount ?? 0 }}</strong>
      </article>
      <article>
        <span>证据锚点</span>
        <strong>{{ bundle?.evidenceAnchorCount ?? 0 }}</strong>
      </article>
      <article>
        <span>媒体资产</span>
        <strong>{{ bundle?.mediaAssetCount ?? 0 }}</strong>
      </article>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  bundle: { type: Object, default: null },
  loading: { type: Boolean, default: false }
})

defineEmits(['prepare'])

const statusText = computed(() => {
  const status = props.bundle?.snapshotStatus || 'missing'
  if (status === 'ready') return '已固定正式评分证据，后续报告引用该快照'
  if (status === 'failed') return '证据快照生成失败'
  return '尚未生成正式证据快照'
})

const canPrepare = computed(() => props.bundle?.snapshotStatus !== 'ready')
</script>

<style scoped>
.evidence-bundle-panel {
  display: grid;
  gap: 14px;
  padding: 18px;
  border: 1px solid rgba(124, 255, 178, 0.18);
  border-radius: 8px;
  background: rgba(10, 14, 20, 0.82);
}

.bundle-head {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 14px;
}

.bundle-head div {
  display: grid;
  gap: 4px;
}

.bundle-head span {
  color: rgba(124, 255, 178, 0.86);
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 3px;
}

.bundle-head strong {
  color: rgba(250, 252, 255, 0.94);
  font-size: 18px;
}

.bundle-head small {
  color: rgba(240, 245, 250, 0.58);
}

.bundle-head button {
  min-height: 38px;
  white-space: nowrap;
  border: 0;
  border-radius: 8px;
  padding: 0 14px;
  background: linear-gradient(135deg, #7cffb2, #67b7ff);
  color: #06100c;
  font-weight: 900;
  cursor: pointer;
}

.bundle-head button:disabled {
  cursor: wait;
  opacity: 0.7;
}

.bundle-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.bundle-grid article {
  display: grid;
  gap: 6px;
  padding: 12px;
  border: 1px solid rgba(240, 245, 250, 0.1);
  border-radius: 8px;
  background: rgba(240, 245, 250, 0.04);
}

.bundle-grid span {
  color: rgba(240, 245, 250, 0.58);
  font-size: 12px;
  font-weight: 800;
}

.bundle-grid strong {
  color: rgba(250, 252, 255, 0.94);
  font-size: 24px;
}

@media (max-width: 760px) {
  .bundle-head {
    display: grid;
  }

  .bundle-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
