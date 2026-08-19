<template>
  <div class="teacher-review-detail">
    <div v-if="view.loading" class="teacher-review-detail__loading">正在加载成果详情…</div>
    <template v-else>
      <header>
        <span>{{ item.teamName || '项目团队' }} · 待审核</span>
        <h3>{{ item.taskTitle || item.title }}</h3>
        <p>{{ item.content || item.taskDescription || '学生暂未填写成果说明。' }}</p>
      </header>
      <div class="teacher-review-detail__meta">
        <span>提交人<strong>{{ item.submitterName || '团队成员' }}</strong></span>
        <span>版本<strong>V{{ item.versionNo || 1 }}</strong></span>
        <span>成果类型<strong>{{ item.submissionType || 'OTHER' }}</strong></span>
      </div>
      <div v-if="item.assets?.length || item.links?.length" class="teacher-review-detail__assets">
        <a v-for="asset in item.assets || []" :key="asset.id || asset.fileUrl" :href="asset.fileUrl" target="_blank" rel="noreferrer">
          {{ asset.fileName || '查看成果文件' }}
        </a>
        <a v-for="link in item.links || []" :key="link.id || link.url" :href="link.url" target="_blank" rel="noreferrer">
          {{ link.title || link.url }}
        </a>
      </div>
      <label>
        <span>审核意见</span>
        <textarea v-model.trim="comment" rows="4" maxlength="1000" placeholder="通过时可简要确认；要求修改时请写清具体问题"></textarea>
      </label>
      <p v-if="error" class="teacher-review-detail__error" role="alert">{{ error }}</p>
      <footer>
        <button type="button" :disabled="busy" @click="submit('CHANGES_REQUESTED')">要求修改</button>
        <button class="is-primary" type="button" :disabled="busy" @click="submit('APPROVED')">审核通过</button>
      </footer>
    </template>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useTeacherCollaborationStore } from '../../stores/collaboration'

const props = defineProps({ view: { type: Object, required: true } })
const store = useTeacherCollaborationStore()
const item = computed(() => props.view.item || {})
const comment = ref('')
const busy = ref(false)
const error = ref('')

async function submit(status) {
  if (busy.value) return
  busy.value = true
  error.value = ''
  try {
    await store.reviewSubmission(
      item.value.submissionId || item.value.id,
      status,
      comment.value
    )
  } catch (submitError) {
    error.value = submitError?.message || '审核提交失败'
  } finally {
    busy.value = false
  }
}
</script>

<style scoped>
.teacher-review-detail { min-height:100%; display:flex; flex-direction:column; }
.teacher-review-detail__loading { min-height:260px; display:grid; place-items:center; color:var(--ds-muted); font-size:12px; }
.teacher-review-detail header { padding-bottom:16px; border-bottom:1px solid var(--ds-line); }
.teacher-review-detail header span { color:var(--ds-orange-deep); font-size:11px; font-weight:700; }
.teacher-review-detail h3 { margin:10px 0 7px; font-size:17px; }
.teacher-review-detail header p { margin:0; color:var(--ds-muted); font-size:12px; line-height:1.7; white-space:pre-wrap; }
.teacher-review-detail__meta { padding:16px 0; display:grid; grid-template-columns:repeat(3,1fr); gap:8px; }
.teacher-review-detail__meta span { color:var(--ds-muted); font-size:10px; }
.teacher-review-detail__meta strong { display:block; margin-top:4px; color:var(--ds-ink-2); font-size:12px; }
.teacher-review-detail__assets { margin-bottom:14px; display:grid; gap:6px; }
.teacher-review-detail__assets a { padding:9px 10px; border:1px solid var(--ds-line); border-radius:8px; color:var(--ds-orange-deep); background:#fff; font-size:11px; text-decoration:none; }
.teacher-review-detail > label { display:grid; gap:6px; color:var(--ds-muted); font-size:11px; font-weight:700; }
.teacher-review-detail textarea { box-sizing:border-box; width:100%; border:1px solid var(--ds-input-border); border-radius:9px; padding:9px 10px; font:500 12px/1.6 var(--ds-font-sans); resize:vertical; }
.teacher-review-detail textarea:focus { outline:none; border-color:var(--ds-orange); box-shadow:var(--ds-input-focus-ring); }
.teacher-review-detail__error { color:#b42318; font-size:11px; }
.teacher-review-detail footer { margin-top:auto; padding-top:14px; border-top:1px solid var(--ds-line); display:flex; justify-content:flex-end; gap:8px; }
.teacher-review-detail footer button { height:36px; padding:0 14px; border:1px solid var(--ds-line-strong); border-radius:9px; background:#fff; color:var(--ds-ink-2); font:700 12px var(--ds-font-sans); cursor:pointer; }
.teacher-review-detail footer button.is-primary { border-color:var(--ds-orange-deep); color:#fff; background:var(--ds-orange-deep); }
</style>
