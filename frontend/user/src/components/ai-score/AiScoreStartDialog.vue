<template>
  <Teleport to="body">
    <div v-if="modelValue" class="ai-score-modal-overlay" role="presentation" @click.self="$emit('update:modelValue', false)">
      <section class="ai-score-modal" role="dialog" aria-modal="true" aria-label="开始 AI 评分">
        <header class="modal-head">
          <div>
            <span>AI SCORE</span>
            <h3>开始 AI 评分</h3>
          </div>
          <button type="button" class="icon-close" aria-label="关闭" @click="$emit('update:modelValue', false)">×</button>
        </header>

        <div class="ai-score-dialog">
          <div class="score-source">
            <span>评分来源</span>
            <strong>{{ sourceLabel }}</strong>
          </div>
          <div class="score-context">
            <div><span>项目</span><b>{{ projectName || '当前项目' }}</b></div>
            <div><span>团队</span><b>{{ teamName || '当前团队' }}</b></div>
            <div><span>赛道</span><b>{{ trackName || '未选择赛道' }}</b></div>
          </div>
          <div class="score-notice">系统将根据所选赛道自动匹配评分标准。</div>
          <div v-if="errorMessage" class="score-error">{{ errorMessage }}</div>
          <div class="score-switches">
            <label>
              <input type="checkbox" :checked="useHistoryMemory" @change="$emit('update:useHistoryMemory', $event.target.checked)" />
              <span>引用历史评分记忆</span>
            </label>
          </div>
        </div>

        <footer class="modal-actions">
          <button type="button" class="ghost-btn" @click="$emit('update:modelValue', false)">取消</button>
          <button type="button" class="primary-btn" :disabled="loading || !trackName || disabled" @click="$emit('confirm')">
            {{ loading ? '创建中' : '开始评分' }}
          </button>
        </footer>
      </section>
    </div>
  </Teleport>
</template>

<script setup>
defineProps({
  modelValue: Boolean,
  loading: Boolean,
  sourceLabel: { type: String, default: '路演录制' },
  projectName: { type: String, default: '' },
  teamName: { type: String, default: '' },
  trackName: { type: String, default: '' },
  useHistoryMemory: { type: Boolean, default: true },
  juryEnabled: { type: Boolean, default: false },
  disabled: Boolean,
  errorMessage: { type: String, default: '' }
})

defineEmits(['update:modelValue', 'update:useHistoryMemory', 'update:juryEnabled', 'confirm'])
</script>

<style scoped>
.ai-score-modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 6000;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(3, 5, 8, 0.72);
  backdrop-filter: blur(10px);
}

.ai-score-modal {
  display: grid;
  gap: 16px;
  width: min(560px, 100%);
  border: 1px solid rgba(240, 245, 250, 0.16);
  border-radius: 8px;
  padding: 20px;
  background: #0b1017;
  box-shadow: 0 26px 90px rgba(0, 0, 0, 0.48);
  color: rgba(250, 252, 255, 0.94);
}

.modal-head,
.modal-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.modal-head span {
  color: rgba(124, 255, 178, 0.86);
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 3px;
}

.modal-head h3 {
  margin: 4px 0 0;
  font-size: 22px;
}

.icon-close {
  width: 36px;
  height: 36px;
  border: 1px solid rgba(240, 245, 250, 0.16);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.04);
  color: rgba(250, 252, 255, 0.82);
  font-size: 24px;
  line-height: 1;
  cursor: pointer;
}

.ai-score-dialog {
  display: grid;
  gap: 14px;
}

.score-source {
  display: flex;
  justify-content: space-between;
  padding: 12px;
  border: 1px solid rgba(240, 245, 250, 0.12);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.035);
}

.score-source span,
.score-context span {
  color: rgba(240, 245, 250, 0.58);
  font-size: 12px;
}

.score-source strong,
.score-context b {
  color: rgba(250, 252, 255, 0.94);
}

.score-context {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.score-context div {
  display: grid;
  gap: 4px;
  min-width: 0;
  padding: 10px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.045);
}

.score-context b {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.score-notice {
  padding: 10px 12px;
  border: 1px solid rgba(103, 183, 255, 0.22);
  border-radius: 8px;
  background: rgba(103, 183, 255, 0.08);
  color: rgba(209, 232, 255, 0.86);
  font-size: 13px;
}

.score-error {
  padding: 10px 12px;
  border: 1px solid rgba(255, 96, 96, 0.28);
  border-radius: 8px;
  background: rgba(255, 96, 96, 0.1);
  color: #ffb4b4;
  font-size: 13px;
  font-weight: 800;
  line-height: 1.5;
}

.score-switches {
  display: grid;
  gap: 10px;
}

.score-switches label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: rgba(240, 245, 250, 0.78);
  font-weight: 700;
}

.modal-actions {
  justify-content: flex-end;
}

.ghost-btn,
.primary-btn {
  min-width: 96px;
  height: 38px;
  border: 1px solid rgba(240, 245, 250, 0.16);
  border-radius: 8px;
  font-weight: 900;
  cursor: pointer;
}

.ghost-btn {
  background: rgba(255, 255, 255, 0.04);
  color: rgba(250, 252, 255, 0.82);
}

.primary-btn {
  border: 0;
  background: linear-gradient(135deg, #7cffb2, #67b7ff);
  color: #06100c;
}

.primary-btn:disabled {
  cursor: wait;
  opacity: 0.65;
}

@media (max-width: 640px) {
  .score-context {
    grid-template-columns: 1fr;
  }

  .modal-actions {
    flex-direction: column-reverse;
    align-items: stretch;
  }

  .ghost-btn,
  .primary-btn {
    width: 100%;
  }
}
</style>
