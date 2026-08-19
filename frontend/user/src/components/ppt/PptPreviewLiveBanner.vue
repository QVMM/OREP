<template>
  <div class="preview-live-banner">
    <div class="preview-live-copy">
      <strong>后台仍在继续生成</strong>
      <p>{{ summary }}</p>
      <div class="preview-live-facts">
        <span class="preview-live-pill">已生成 {{ rendered }}/{{ totalLabel }} 页</span>
        <span class="preview-live-pill">剩余 {{ remainingLabel }}</span>
        <span class="preview-live-pill">最近进展 {{ lastChangeText }}</span>
        <span class="preview-live-pill" :class="status.level">{{ status.label }}</span>
      </div>
    </div>
    <div class="preview-live-actions">
      <el-button
        v-if="status.action === 'retry'"
        size="small"
        type="primary"
        :loading="retryLoading"
        @click="$emit('retry')"
      >
        建议重试生成
      </el-button>
      <el-button size="small" @click="$emit('back')">
        返回生成进度
      </el-button>
      <el-button v-if="showSnooze" size="small" @click="$emit('snooze')">
        继续等待
      </el-button>
      <el-button size="small" @click="$emit('refresh')" :loading="refreshLoading">
        刷新已生成页面
      </el-button>
    </div>
  </div>
</template>

<script setup>
defineEmits(['retry', 'back', 'snooze', 'refresh'])

defineProps({
  summary: { type: String, default: '' },
  rendered: { type: Number, default: 0 },
  totalLabel: { type: [Number, String], default: '?' },
  remainingLabel: { type: String, default: '待计算' },
  lastChangeText: { type: String, default: '刚刚' },
  status: {
    type: Object,
    default: () => ({ level: 'running', label: '继续生成中', action: 'wait' })
  },
  retryLoading: { type: Boolean, default: false },
  refreshLoading: { type: Boolean, default: false },
  showSnooze: { type: Boolean, default: false }
})
</script>

<style scoped>
.preview-live-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 16px 18px;
  margin-bottom: 16px;
  border-radius: 16px;
  border: 1px solid rgba(59, 130, 246, 0.24);
  background: linear-gradient(135deg, rgba(15, 23, 42, 0.92), rgba(30, 64, 175, 0.22));
}

.preview-live-copy {
  display: grid;
  gap: 6px;
}

.preview-live-copy strong {
  color: #eff6ff;
  font-size: 16px;
  font-weight: 800;
}

.preview-live-copy p {
  margin: 0;
  color: rgba(226, 232, 240, 0.78);
  line-height: 1.6;
}

.preview-live-facts {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 4px;
}

.preview-live-pill {
  padding: 7px 12px;
  border-radius: 999px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: rgba(15, 23, 42, 0.56);
  color: rgba(226, 232, 240, 0.82);
  font-size: 12px;
  font-weight: 700;
}

.preview-live-pill.running {
  border-color: rgba(59, 130, 246, 0.34);
  color: #bfdbfe;
}

.preview-live-pill.warning {
  border-color: rgba(250, 204, 21, 0.34);
  color: #fde68a;
}

.preview-live-pill.risk {
  border-color: rgba(248, 113, 113, 0.38);
  color: #fecaca;
}

.preview-live-pill.done {
  border-color: rgba(74, 222, 128, 0.32);
  color: #bbf7d0;
}

.preview-live-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

@media (max-width: 1180px) {
  .preview-live-banner {
    flex-direction: column;
    align-items: flex-start;
  }

  .preview-live-actions {
    justify-content: flex-start;
    flex-wrap: wrap;
  }
}
</style>
