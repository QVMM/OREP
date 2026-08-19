<template>
  <div class="resource-page">
    <div class="resource-orbit resource-orbit-one"></div>
    <div class="resource-orbit resource-orbit-two"></div>

    <div class="resource-shell">
      <div class="page-bar">
        <el-button text @click="router.push('/')" class="back-btn">
          <el-icon><ArrowLeft /></el-icon>
          <span>返回首页</span>
        </el-button>
      </div>

      <div class="page-hero">
        <div class="hero-copy">
          <span class="hero-tag">路演资料</span>
          <h2>路演资源中心</h2>
          <p>集中下载路演模板、评分表和交付文档，快速进入任务准备状态。</p>
        </div>
        <div class="hero-console">
          <span>可下载文件</span>
          <strong>{{ files.length }}</strong>
          <small>{{ loading ? '同步资源目录中' : '资源就绪' }}</small>
        </div>
      </div>

      <div class="resource-stats">
        <div class="stat-cell">
          <span>文件</span>
          <strong>{{ files.length }}</strong>
          <small>文件数量</small>
        </div>
        <div class="stat-cell">
          <span>格式</span>
          <strong>{{ resourceFormatCount }}</strong>
          <small>资源类型</small>
        </div>
        <div class="stat-cell">
          <span>状态</span>
          <strong>可下载</strong>
          <small>下载状态</small>
        </div>
      </div>

      <div class="content" v-loading="loading">
        <div class="content-head">
          <div>
            <span>资料目录</span>
            <strong>资源清单</strong>
          </div>
          <small>{{ files.length ? '选择资源并下载到本地' : '暂无可下载资源' }}</small>
        </div>

        <div v-if="files.length === 0" class="empty-state">
          <div class="empty-mark">
            <el-icon><Document /></el-icon>
          </div>
          <strong>暂无资源文件</strong>
          <p>资源上传后会在这里展示文件名、格式和大小。</p>
        </div>
        <div v-else class="file-list">
          <div v-for="(f, index) in files" :key="f.name" class="file-card">
            <div class="file-seq">{{ String(index + 1).padStart(2, '0') }}</div>
            <div class="file-icon" :class="`type-${(f.ext || 'file').toLowerCase()}`">
              <el-icon><Document /></el-icon>
            </div>
            <div class="file-body">
              <div class="file-name">{{ f.name }}</div>
              <div class="file-meta">
                <span>{{ f.size }}</span>
                <span>{{ extLabel(f.ext) }}</span>
              </div>
            </div>
            <el-button type="primary" round class="download-btn" @click="download(f)">
              <el-icon><Download /></el-icon>
              <span>下载</span>
            </el-button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import request from '../utils/request'
import { getUserToken } from '../utils/authStorage'
import { ArrowLeft, Download, Document } from '@element-plus/icons-vue'

const router = useRouter()
const loading = ref(false)
const files = ref([])

const resourceFormatCount = computed(() => {
  const formats = new Set(files.value.map(file => (file.ext || 'file').toLowerCase()).filter(Boolean))
  return formats.size || 0
})

onMounted(async () => {
  loading.value = true
  try {
    const res = await request.get('/api/ppt-template')
    if (res.code === 200) files.value = res.data || []
  } catch (e) { console.error(e) }
  loading.value = false
})

function download(file) {
  const token = getUserToken()
  const a = document.createElement('a')
  a.href = file.url + '?t=' + token
  a.download = file.name
  a.click()
}

function extLabel(ext) {
  if (!ext) return '未知格式'
  return { pdf: 'PDF 文档', doc: 'Word 文档', docx: 'Word 文档', pptx: 'PowerPoint', ppt: 'PowerPoint' }[ext] || ext.toUpperCase()
}
</script>

<style scoped>
.resource-page {
  position: relative;
  min-height: 100vh;
  overflow: hidden;
  padding: 34px 28px 64px;
  background-color: #ffffff;
  background-image: none;
  color: var(--ds-ink, #1d1d1f);
}

.resource-orbit {
  position: absolute;
  pointer-events: none;
  border: 1px solid rgba(240, 241, 250, .075);
  border-radius: 50%;
}

.resource-orbit-one {
  right: -240px;
  top: 140px;
  width: 560px;
  height: 560px;
}

.resource-orbit-two {
  left: -280px;
  bottom: -330px;
  width: 640px;
  height: 640px;
}

.resource-shell {
  position: relative;
  z-index: 1;
  width: min(1120px, 100%);
  margin: 0 auto;
}

.page-bar {
  margin-bottom: 18px;
}

.back-btn {
  height: 34px;
  padding: 0 12px !important;
  border: 1px solid rgba(240, 241, 250, .12);
  border-radius: 999px;
  background: rgba(240, 241, 250, .045);
  color: rgba(240, 241, 250, .72);
  font-size: 13px;
  font-weight: 720;
  transition: background .18s ease, color .18s ease, transform .18s ease;
}

.back-btn:hover {
  background: rgba(122, 255, 180, .08);
  color: #f4fff8;
  transform: translateX(-2px);
}

.page-hero {
  min-height: 238px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 220px;
  gap: 28px;
  align-items: stretch;
  padding: 42px 46px;
  border: 1px solid rgba(240, 241, 250, .12);
  background:
    linear-gradient(90deg, rgba(240, 241, 250, .055), transparent 44%),
    radial-gradient(circle at 82% 28%, rgba(122, 255, 180, .12), transparent 36%),
    rgba(11, 12, 16, .8);
  box-shadow:
    inset 0 1px 0 rgba(240, 241, 250, .05),
    0 26px 80px rgba(0, 0, 0, .34);
}

.hero-copy {
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.hero-tag {
  color: rgba(122, 255, 180, .78);
  font-size: 11px;
  font-weight: 840;
  letter-spacing: .18em;
}

.page-hero h2 {
  margin: 12px 0 16px;
  color: #f4f6ff;
  font-size: clamp(38px, 5vw, 72px);
  line-height: .96;
  font-weight: 850;
  letter-spacing: 0;
}

.page-hero p {
  max-width: 620px;
  margin: 0;
  color: rgba(240, 241, 250, .6);
  font-size: 15px;
  line-height: 1.8;
}

.hero-console {
  display: grid;
  align-content: center;
  justify-items: start;
  padding: 24px;
  border: 1px solid rgba(122, 255, 180, .18);
  background:
    radial-gradient(circle at 50% 0%, rgba(122, 255, 180, .12), transparent 58%),
    rgba(6, 7, 10, .62);
}

.hero-console span,
.stat-cell span,
.content-head span {
  color: rgba(240, 241, 250, .42);
  font-size: 11px;
  font-weight: 840;
  letter-spacing: .18em;
}

.hero-console strong {
  margin-top: 16px;
  color: #7affb4;
  font-size: 48px;
  line-height: 1;
  font-weight: 860;
  font-variant-numeric: tabular-nums;
}

.hero-console small {
  margin-top: 8px;
  color: rgba(240, 241, 250, .54);
  font-size: 13px;
  font-weight: 720;
}

.resource-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  border: 1px solid rgba(240, 241, 250, .12);
  border-top: 0;
  background: rgba(9, 10, 13, .72);
  margin-bottom: 18px;
}

.stat-cell {
  min-height: 104px;
  padding: 20px 22px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  border-right: 1px solid rgba(240, 241, 250, .1);
}

.stat-cell:last-child {
  border-right: 0;
}

.stat-cell strong {
  margin-top: 12px;
  color: #f4f6ff;
  font-size: 28px;
  line-height: 1;
  font-weight: 850;
  font-variant-numeric: tabular-nums;
}

.stat-cell small {
  margin-top: 8px;
  color: rgba(240, 241, 250, .48);
  font-size: 13px;
}

.content {
  min-height: 420px;
  padding: 26px;
  border: 1px solid rgba(240, 241, 250, .11);
  background:
    radial-gradient(circle at 82% 10%, rgba(122, 255, 180, .045), transparent 32%),
    rgba(9, 10, 13, .86);
  box-shadow: 0 22px 70px rgba(0, 0, 0, .28);
}

.content-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 16px;
  margin-bottom: 20px;
}

.content-head strong {
  display: block;
  margin-top: 7px;
  color: #f4f6ff;
  font-size: 24px;
  line-height: 1;
  font-weight: 850;
}

.content-head small {
  color: rgba(240, 241, 250, .48);
  font-size: 13px;
}

.file-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.file-card {
  display: grid;
  grid-template-columns: 42px 52px minmax(0, 1fr) auto;
  align-items: center;
  gap: 14px;
  min-height: 86px;
  padding: 14px 16px;
  border: 1px solid rgba(240, 241, 250, .1);
  background:
    linear-gradient(90deg, rgba(240, 241, 250, .045), rgba(240, 241, 250, .018));
  transition: transform .18s ease, border-color .18s ease, background .18s ease;
}

.file-card:hover {
  transform: translateY(-2px);
  border-color: rgba(122, 255, 180, .22);
  background:
    linear-gradient(90deg, rgba(122, 255, 180, .055), rgba(240, 241, 250, .02));
}

.file-seq {
  color: rgba(240, 241, 250, .34);
  font-size: 14px;
  font-weight: 820;
  font-variant-numeric: tabular-nums;
}

.file-icon {
  width: 52px;
  height: 52px;
  border: 1px solid rgba(240, 241, 250, .12);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: #7affb4;
  background:
    radial-gradient(circle at 50% 0%, rgba(122, 255, 180, .18), transparent 54%),
    rgba(122, 255, 180, .055);
}

.file-icon :deep(svg) {
  width: 24px;
  height: 24px;
}

.file-icon.type-pdf,
.file-icon.type-ppt,
.file-icon.type-pptx {
  color: #ffd38a;
  background:
    radial-gradient(circle at 50% 0%, rgba(255, 211, 138, .18), transparent 54%),
    rgba(255, 211, 138, .055);
}

.file-icon.type-doc,
.file-icon.type-docx {
  color: #86eaff;
  background:
    radial-gradient(circle at 50% 0%, rgba(31, 213, 249, .16), transparent 54%),
    rgba(31, 213, 249, .052);
}

.file-body {
  flex: 1;
  min-width: 0;
}

.file-name {
  font-size: 15px;
  font-weight: 780;
  color: rgba(244, 246, 255, .94);
  margin-bottom: 9px;
  word-break: break-all;
}

.file-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: rgba(240, 241, 250, .46);
}

.file-meta span {
  min-height: 24px;
  display: inline-flex;
  align-items: center;
  padding: 0 9px;
  border: 1px solid rgba(240, 241, 250, .08);
  border-radius: 999px;
  background: rgba(240, 241, 250, .035);
}

.download-btn {
  height: 38px;
  min-width: 96px;
  border-color: #eff0fa !important;
  background: #eff0fa !important;
  color: #07080b !important;
  font-weight: 850;
}

.download-btn:hover {
  border-color: #dfe3ee !important;
  background: #dfe3ee !important;
  color: #07080b !important;
}

.empty-state {
  min-height: 300px;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 10px;
  text-align: center;
  border: 1px solid rgba(240, 241, 250, .09);
  background:
    radial-gradient(circle at 50% 46%, rgba(122, 255, 180, .05), transparent 34%),
    rgba(240, 241, 250, .028);
}

.empty-mark {
  width: 76px;
  height: 76px;
  display: grid;
  place-items: center;
  border: 1px solid rgba(122, 255, 180, .18);
  border-radius: 50%;
  color: #7affb4;
  background: rgba(122, 255, 180, .06);
  font-size: 28px;
}

.empty-state strong {
  color: #f4f6ff;
  font-size: 18px;
}

.empty-state p {
  margin: 0;
  color: rgba(240, 241, 250, .46);
  font-size: 13px;
}

.resource-page :deep(.el-loading-mask) {
  background: rgba(5, 6, 9, .72);
  backdrop-filter: blur(8px);
}

.resource-page :deep(.el-loading-spinner .path) {
  stroke: #7affb4;
}

@media (max-width: 820px) {
  .resource-page {
    padding: 22px 14px 42px;
  }

  .page-hero {
    grid-template-columns: 1fr;
    padding: 30px 24px;
  }

  .resource-stats {
    grid-template-columns: 1fr;
    border-top: 1px solid rgba(240, 241, 250, .12);
  }

  .stat-cell {
    border-right: 0;
    border-bottom: 1px solid rgba(240, 241, 250, .1);
  }

  .stat-cell:last-child {
    border-bottom: 0;
  }

  .content {
    padding: 20px 14px;
  }

  .content-head {
    align-items: flex-start;
    flex-direction: column;
  }

  .file-card {
    grid-template-columns: 34px 48px minmax(0, 1fr);
  }

  .download-btn {
    grid-column: 1 / -1;
    justify-self: stretch;
  }
}

@media (max-width: 520px) {
  .page-hero h2 {
    font-size: 36px;
  }

  .file-card {
    grid-template-columns: 1fr;
    justify-items: start;
  }

  .file-seq {
    display: none;
  }

  .download-btn {
    width: 100%;
  }
}

/* Student workspace high-fidelity normalization. */
.resource-page {
  min-height: 100%;
  padding: var(--ds-page-margin-y, 40px) var(--ds-page-margin-x, 40px);
  overflow: visible;
  color: var(--ds-ink, #1d1d1f);
  background: transparent;
}

.resource-orbit {
  display: none;
}

.resource-shell {
  width: 100%;
  margin: 0;
}

.page-bar {
  margin-bottom: 16px;
}

.back-btn {
  height: 36px;
  border-color: var(--ds-line, #e5e5e7);
  background: rgba(255, 255, 255, 0.72);
  color: var(--ds-muted, #6e6e73);
  box-shadow: none;
}

.back-btn:hover {
  color: var(--ds-orange, #f4511e);
  background: var(--ds-orange-wash, #fff4ef);
  transform: none;
}

.page-hero {
  min-height: 172px;
  grid-template-columns: minmax(0, 1fr) 210px;
  padding: 28px 32px;
  border-color: rgba(0, 0, 0, 0.06);
  border-radius: var(--ds-radius-xl, 24px);
  background:
    radial-gradient(circle at 88% 18%, rgba(244, 81, 30, 0.09), transparent 34%),
    rgba(255, 255, 255, 0.8);
  box-shadow: 0 12px 32px rgba(29, 29, 31, 0.06);
}

.hero-tag,
.hero-console span,
.stat-cell span,
.content-head span {
  color: var(--ds-orange, #f4511e);
  letter-spacing: 0.08em;
}

.page-hero h2 {
  margin: 10px 0 10px;
  color: var(--ds-ink, #1d1d1f);
  font-size: clamp(26px, 2.3vw, 34px);
  line-height: 1.15;
  font-weight: 800;
}

.page-hero p {
  color: var(--ds-muted, #6e6e73);
  line-height: 1.65;
}

.hero-console {
  padding: 22px;
  border-color: rgba(244, 81, 30, 0.16);
  border-radius: var(--ds-radius-lg, 18px);
  background: rgba(255, 244, 239, 0.78);
}

.hero-console strong {
  color: var(--ds-orange, #f4511e);
  font-size: 40px;
}

.hero-console small {
  color: var(--ds-muted, #6e6e73);
}

.resource-stats {
  margin: 14px 0 18px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: var(--ds-radius-lg, 18px);
  overflow: hidden;
  background: rgba(255, 255, 255, 0.72);
}

.stat-cell {
  min-height: 92px;
  border-right-color: rgba(0, 0, 0, 0.06);
}

.stat-cell strong {
  color: var(--ds-ink, #1d1d1f);
  font-size: 24px;
}

.stat-cell small,
.content-head small,
.file-meta {
  color: var(--ds-muted, #6e6e73);
}

.content {
  min-height: 360px;
  padding: 24px;
  border-color: rgba(0, 0, 0, 0.06);
  border-radius: var(--ds-radius-xl, 24px);
  background: rgba(255, 255, 255, 0.76);
  box-shadow: 0 10px 28px rgba(29, 29, 31, 0.05);
}

.content-head strong,
.file-name,
.empty-state strong {
  color: var(--ds-ink, #1d1d1f);
}

.file-card {
  border-color: rgba(0, 0, 0, 0.07);
  border-radius: var(--ds-radius-md, 14px);
  background: rgba(255, 255, 255, 0.86);
  box-shadow: none;
}

.file-card:hover {
  transform: none;
  border-color: rgba(244, 81, 30, 0.22);
  background: var(--ds-orange-wash, #fff4ef);
}

.file-seq {
  color: var(--ds-faint, #9a9aa0);
}

.file-icon,
.file-icon.type-pdf,
.file-icon.type-ppt,
.file-icon.type-pptx,
.file-icon.type-doc,
.file-icon.type-docx {
  color: var(--ds-orange, #f4511e);
  border-color: rgba(244, 81, 30, 0.14);
  background: var(--ds-orange-wash, #fff4ef);
}

.file-meta span {
  border-color: rgba(0, 0, 0, 0.06);
  background: #f7f7f8;
}

.download-btn,
.download-btn:hover {
  height: 40px;
  min-width: 96px;
  border-color: var(--ds-orange, #f4511e) !important;
  background: var(--ds-orange, #f4511e) !important;
  color: #fff !important;
  box-shadow: none !important;
}

.empty-state {
  border-color: rgba(0, 0, 0, 0.07);
  border-radius: var(--ds-radius-lg, 18px);
  background: #fafafa;
}

.empty-mark {
  border-color: rgba(244, 81, 30, 0.18);
  color: var(--ds-orange, #f4511e);
  background: var(--ds-orange-wash, #fff4ef);
}

.empty-state p {
  color: var(--ds-muted, #6e6e73);
}

.resource-page :deep(.el-loading-mask) {
  background: rgba(245, 245, 247, 0.72);
}

.resource-page :deep(.el-loading-spinner .path) {
  stroke: var(--ds-orange, #f4511e);
}
</style>
