<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="cert-modal-mask teacher-overlay-mask"
      role="presentation"
      @click.self="close"
      @keydown.esc.prevent="close"
    >
      <div
        class="cert-modal"
        role="dialog"
        aria-modal="true"
        :aria-label="certificate?.title || '奖状预览'"
      >
        <header class="cert-modal__head">
          <div>
            <span class="cert-scope" :class="{ 'is-team': isTeam }">
              {{ isTeam ? '团队奖状' : '个人奖状' }}
            </span>
            <h2>{{ certificate?.title || '奖状预览' }}</h2>
          </div>
          <button type="button" class="cert-modal__close" aria-label="关闭" @click="close">×</button>
        </header>

        <div class="cert-modal__body">
          <!-- 上传的图片：框内直接展示 -->
          <div
            v-if="isImageFile"
            class="cert-sheet cert-sheet--uploaded"
            :class="{ 'is-team': isTeam }"
          >
            <img :src="fileUrl" :alt="certificate?.title || '奖状'" class="cert-sheet__image" />
          </div>

          <!-- 系统生成 / PDF：展示带样式奖状 -->
          <div
            v-else
            ref="sheetRef"
            class="cert-sheet"
            :class="{ 'is-team': isTeam }"
          >
            <span class="cert-sheet__frame" aria-hidden="true"></span>
            <span class="cert-sheet__glow" aria-hidden="true"></span>
            <div class="cert-sheet__brand">
              <span>
                <img src="/brand/competition-brain-mark.svg" alt="" />
                <b>竞赛大脑</b>
              </span>
              <em>{{ displayNo }}</em>
            </div>
            <h3 class="cert-sheet__title">奖 状</h3>
            <p class="cert-sheet__grant">
              兹授予
              <b>{{ grantName }}</b>
            </p>
            <h4 class="cert-sheet__name">{{ certificate?.title || '荣誉奖状' }}</h4>
            <p v-if="certificate?.awardLevel" class="cert-sheet__level">{{ certificate.awardLevel }}</p>
            <p class="cert-sheet__desc">
              {{
                certificate?.description
                  || '表彰在本次备赛过程中表现突出的个人或团队，特发此状，以资鼓励。'
              }}
            </p>
            <div class="cert-sheet__meta">
              <span>
                <small>颁发单位</small>
                <strong>{{ certificate?.issuerName || '启发·竞赛大脑' }}</strong>
              </span>
              <span>
                <small>颁发日期</small>
                <strong>{{ issuedText }}</strong>
              </span>
            </div>
            <span class="cert-sheet__seal" aria-hidden="true">{{ sealLabel }}</span>
          </div>
        </div>

        <footer class="cert-modal__foot">
          <button type="button" class="teacher-btn teacher-btn--secondary" @click="close">关闭</button>
          <button
            type="button"
            class="teacher-btn teacher-btn--secondary"
            :disabled="exporting"
            @click="downloadStyled"
          >
            {{ exporting ? '导出中…' : '下载样式图' }}
          </button>
          <a
            v-if="fileUrl"
            class="teacher-btn teacher-btn--primary"
            :href="fileUrl"
            :download="downloadName"
            target="_blank"
            rel="noreferrer"
          >
            {{ isImageFile ? '下载原图' : '下载原文件' }}
          </a>
        </footer>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  certificate: { type: Object, default: null },
  /** 授予对象展示名（团队名 / 学生名） */
  recipientLabel: { type: String, default: '' },
  /** 打开后自动导出样式图 */
  autoDownload: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue'])

const open = computed({
  get: () => props.modelValue && !!props.certificate,
  set: (v) => emit('update:modelValue', v),
})

const sheetRef = ref(null)
const exporting = ref(false)
const autoDownloadFired = ref(false)

const isTeam = computed(() => String(props.certificate?.certificateType || '').toUpperCase() === 'TEAM')
const fileUrl = computed(() => props.certificate?.pdfUrl || '')
const mime = computed(() => String(props.certificate?.mimeType || '').toLowerCase())
const isImageFile = computed(() => {
  if (mime.value.startsWith('image/')) return true
  const url = fileUrl.value
  return /\.(png|jpe?g|gif|webp)(\?|$)/i.test(url)
})

const displayNo = computed(() => {
  const number = String(props.certificate?.certificateNo || '').trim().replace(/^OREP-/i, '')
  return number || '荣誉证明'
})

const sealLabel = computed(() => {
  const level = String(props.certificate?.awardLevel || '').trim()
  if (level) return level.slice(0, 2)
  return isTeam.value ? '团队' : '荣誉'
})

const grantName = computed(() => {
  if (props.recipientLabel) return props.recipientLabel
  return isTeam.value ? '团队成员' : '获奖同学'
})

const issuedText = computed(() => {
  const raw = props.certificate?.issuedAt
  if (!raw) return '—'
  const s = String(raw).replace('T', ' ')
  return s.slice(0, 10)
})

const downloadName = computed(() => {
  const title = String(props.certificate?.title || '奖状').replace(/[\\/:*?"<>|]/g, '_')
  if (isImageFile.value) return `${title}.png`
  if (mime.value.includes('pdf') || /\.pdf(\?|$)/i.test(fileUrl.value)) return `${title}.pdf`
  return props.certificate?.originalFileName || `${title}`
})

function close() {
  open.value = false
}

watch(open, async (v) => {
  if (v) {
    await nextTick()
    document.body.style.overflow = 'hidden'
    if (props.autoDownload && !autoDownloadFired.value) {
      autoDownloadFired.value = true
      // 稍等一帧，确保样式与字体就绪
      requestAnimationFrame(() => {
        downloadStyled()
      })
    }
  } else {
    document.body.style.overflow = ''
    autoDownloadFired.value = false
  }
})

/**
 * 将当前样式奖状导出为 PNG（带设计样式，不是裸 PDF）
 * - 上传图片：下载原图
 * - 系统生成 / PDF：用 canvas 绘制与预览一致的奖状
 */
async function downloadStyled() {
  if (exporting.value) return
  exporting.value = true
  try {
    if (isImageFile.value && fileUrl.value) {
      await downloadUrl(fileUrl.value, downloadName.value)
      return
    }
    const dataUrl = renderCertificateCanvas()
    const name = `${String(props.certificate?.title || '奖状').replace(/[\\/:*?"<>|]/g, '_')}.png`
    triggerDataUrlDownload(dataUrl, name)
  } catch (err) {
    console.error(err)
    if (fileUrl.value) window.open(fileUrl.value, '_blank', 'noopener,noreferrer')
  } finally {
    exporting.value = false
  }
}

async function downloadUrl(url, name) {
  try {
    const res = await fetch(url, { credentials: 'include' })
    if (!res.ok) throw new Error('fetch failed')
    const blob = await res.blob()
    const href = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = href
    a.download = name
    a.click()
    URL.revokeObjectURL(href)
  } catch {
    window.open(url, '_blank', 'noopener,noreferrer')
  }
}

function triggerDataUrlDownload(dataUrl, name) {
  const a = document.createElement('a')
  a.href = dataUrl
  a.download = name
  a.click()
}

/** Canvas 绘制精美奖状，保证导出与预览视觉一致、不依赖 foreignObject */
function renderCertificateCanvas() {
  const W = 1200
  const H = 780
  const canvas = document.createElement('canvas')
  canvas.width = W
  canvas.height = H
  const ctx = canvas.getContext('2d')
  const team = isTeam.value
  const ink = team ? '#6d4c16' : '#6d2b18'
  const accent = team ? '#b37a12' : '#e84a1c'
  const muted = team ? '#8a6a3a' : '#7f574a'
  const faint = team ? '#9b8360' : '#9b766a'

  // 背景
  const bg = ctx.createLinearGradient(0, 0, W, H)
  if (team) {
    bg.addColorStop(0, '#fffdf7')
    bg.addColorStop(0.48, '#fff6e4')
    bg.addColorStop(1, '#fffdf9')
  } else {
    bg.addColorStop(0, '#fffaf7')
    bg.addColorStop(0.48, '#fff4ed')
    bg.addColorStop(1, '#fffdfb')
  }
  ctx.fillStyle = bg
  ctx.fillRect(0, 0, W, H)

  // 光晕
  const g1 = ctx.createRadialGradient(W * 0.12, H * 0.12, 0, W * 0.12, H * 0.12, 280)
  g1.addColorStop(0, team ? 'rgba(255,228,170,0.55)' : 'rgba(255,214,186,0.55)')
  g1.addColorStop(1, 'rgba(255,255,255,0)')
  ctx.fillStyle = g1
  ctx.fillRect(0, 0, W, H)
  const g2 = ctx.createRadialGradient(W * 0.88, H * 0.86, 0, W * 0.88, H * 0.86, 260)
  g2.addColorStop(0, team ? 'rgba(245,196,112,0.3)' : 'rgba(255,188,148,0.32)')
  g2.addColorStop(1, 'rgba(255,255,255,0)')
  ctx.fillStyle = g2
  ctx.fillRect(0, 0, W, H)

  // 外框
  ctx.strokeStyle = team ? 'rgba(180,120,28,0.45)' : 'rgba(232,74,28,0.45)'
  ctx.lineWidth = 3
  ctx.strokeRect(28, 28, W - 56, H - 56)
  // 内虚线框
  ctx.save()
  ctx.setLineDash([8, 8])
  ctx.strokeStyle = team ? 'rgba(180,120,28,0.28)' : 'rgba(232,74,28,0.22)'
  ctx.lineWidth = 1.5
  ctx.strokeRect(52, 52, W - 104, H - 104)
  ctx.restore()
  // 内实线
  ctx.strokeStyle = team ? 'rgba(180,120,28,0.16)' : 'rgba(232,74,28,0.14)'
  ctx.lineWidth = 1
  ctx.strokeRect(42, 42, W - 84, H - 84)

  const cx = W / 2
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillStyle = ink
  ctx.font = '700 18px "PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif'
  ctx.fillText('竞赛大脑', cx + 10, 110)

  // logo 圆点
  ctx.beginPath()
  ctx.arc(cx - 52, 110, 12, 0, Math.PI * 2)
  ctx.fillStyle = accent
  ctx.fill()
  ctx.fillStyle = '#fff'
  ctx.font = '800 12px sans-serif'
  ctx.fillText('C', cx - 52, 111)

  ctx.fillStyle = faint
  ctx.font = '400 14px "PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif'
  ctx.fillText(displayNo.value, cx, 138)

  ctx.fillStyle = ink
  ctx.font = '800 56px "Songti SC","STSong","SimSun","PingFang SC",serif'
  ctx.letterSpacing = '0.28em'
  ctx.fillText('奖 状', cx, 210)

  ctx.fillStyle = muted
  ctx.font = '400 20px "PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif'
  ctx.fillText('兹授予', cx, 268)
  ctx.fillStyle = ink
  ctx.font = '700 24px "PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif'
  ctx.fillText(grantName.value, cx, 300)

  ctx.fillStyle = accent
  ctx.font = '800 34px "PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif'
  wrapText(ctx, props.certificate?.title || '荣誉奖状', cx, 360, W - 220, 42)

  let y = 420
  if (props.certificate?.awardLevel) {
    const level = String(props.certificate.awardLevel)
    ctx.font = '700 16px "PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif'
    const tw = ctx.measureText(level).width
    const px = 18
    const py = 10
    const bx = cx - tw / 2 - px
    const by = y - 12
    roundRect(ctx, bx, by, tw + px * 2, 28, 14)
    ctx.fillStyle = team ? 'rgba(180,120,28,0.12)' : 'rgba(232,74,28,0.1)'
    ctx.fill()
    ctx.fillStyle = team ? '#92400e' : '#9a4a1f'
    ctx.fillText(level, cx, y + 2)
    y += 40
  }

  const desc =
    props.certificate?.description ||
    '表彰在本次备赛过程中表现突出的个人或团队，特发此状，以资鼓励。'
  ctx.fillStyle = muted
  ctx.font = '400 18px "PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif'
  wrapText(ctx, desc, cx, y + 10, W - 280, 30)

  // meta
  const metaY = H - 150
  ctx.textAlign = 'left'
  ctx.fillStyle = faint
  ctx.font = '400 14px "PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif'
  ctx.fillText('颁发单位', 160, metaY)
  ctx.fillText('颁发日期', W - 360, metaY)
  ctx.fillStyle = ink
  ctx.font = '700 18px "PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif'
  ctx.fillText(props.certificate?.issuerName || '启发·竞赛大脑', 160, metaY + 28)
  ctx.fillText(issuedText.value, W - 360, metaY + 28)

  // 印章
  const sealX = W - 150
  const sealY = H - 150
  ctx.save()
  ctx.translate(sealX, sealY)
  ctx.rotate((-12 * Math.PI) / 180)
  ctx.beginPath()
  ctx.arc(0, 0, 48, 0, Math.PI * 2)
  ctx.strokeStyle = team ? 'rgba(163,112,28,0.55)' : 'rgba(196,58,18,0.5)'
  ctx.lineWidth = 4
  ctx.stroke()
  ctx.beginPath()
  ctx.arc(0, 0, 40, 0, Math.PI * 2)
  ctx.strokeStyle = team ? 'rgba(163,112,28,0.2)' : 'rgba(196,58,18,0.18)'
  ctx.lineWidth = 2
  ctx.stroke()
  ctx.fillStyle = team ? 'rgba(128,93,29,0.65)' : 'rgba(196,58,18,0.6)'
  ctx.font = '800 20px "PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif'
  ctx.textAlign = 'center'
  ctx.fillText(sealLabel.value, 0, 2)
  ctx.restore()

  return canvas.toDataURL('image/png')
}

function wrapText(ctx, text, x, y, maxWidth, lineHeight) {
  const chars = String(text || '').split('')
  let line = ''
  let cy = y
  let lines = 0
  for (let i = 0; i < chars.length; i += 1) {
    const test = line + chars[i]
    if (ctx.measureText(test).width > maxWidth && line) {
      ctx.fillText(line, x, cy)
      line = chars[i]
      cy += lineHeight
      lines += 1
      if (lines >= 4) {
        ctx.fillText(line + '…', x, cy)
        return
      }
    } else {
      line = test
    }
  }
  if (line) ctx.fillText(line, x, cy)
}

function roundRect(ctx, x, y, w, h, r) {
  const radius = Math.min(r, w / 2, h / 2)
  ctx.beginPath()
  ctx.moveTo(x + radius, y)
  ctx.arcTo(x + w, y, x + w, y + h, radius)
  ctx.arcTo(x + w, y + h, x, y + h, radius)
  ctx.arcTo(x, y + h, x, y, radius)
  ctx.arcTo(x, y, x + w, y, radius)
  ctx.closePath()
}

defineExpose({ downloadStyled, close })
</script>

<style scoped>
.cert-modal-mask {
  position: fixed;
  inset: 0;
  z-index: 1200;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(18, 20, 26, 0.48);
  backdrop-filter: blur(4px);
}

.cert-modal {
  width: min(720px, 100%);
  max-height: min(92vh, 900px);
  display: flex;
  flex-direction: column;
  border-radius: 18px;
  background: #fff;
  box-shadow: 0 28px 64px rgba(18, 20, 26, 0.22);
  overflow: hidden;
}

.cert-modal__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 20px 12px;
  border-bottom: 1px solid var(--ds-line, #ececef);
}

.cert-modal__head h2 {
  margin: 8px 0 0;
  color: #1f1f23;
  font-size: 18px;
  line-height: 1.3;
}

.cert-scope {
  display: inline-flex;
  align-items: center;
  min-height: 22px;
  padding: 0 8px;
  border-radius: 999px;
  color: #c2410c;
  background: rgba(232, 74, 28, 0.1);
  font-size: 11px;
  font-weight: 750;
}

.cert-scope.is-team {
  color: #92400e;
  background: rgba(194, 138, 28, 0.14);
}

.cert-modal__close {
  width: 32px;
  height: 32px;
  border: 0;
  border-radius: 10px;
  color: #8b8b90;
  background: #f5f5f6;
  font-size: 22px;
  line-height: 1;
  cursor: pointer;
  flex: none;
}

.cert-modal__close:hover {
  color: #e84a1c;
  background: #fff1eb;
}

.cert-modal__body {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 16px 18px;
  background: #f7f7f8;
}

.cert-modal__foot {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 10px;
  padding: 14px 18px 16px;
  border-top: 1px solid var(--ds-line, #ececef);
  background: #fff;
}

/* —— 奖状本体 —— */
.cert-sheet {
  position: relative;
  min-height: 380px;
  display: grid;
  place-content: center;
  justify-items: center;
  gap: 10px;
  margin: 0 auto;
  padding: 44px 42px 40px;
  overflow: hidden;
  border: 1px solid rgba(232, 74, 28, 0.28);
  outline: 1px solid rgba(232, 74, 28, 0.12);
  outline-offset: -8px;
  border-radius: 4px;
  color: #6d2b18;
  background:
    radial-gradient(circle at 12% 12%, rgba(255, 214, 186, 0.42), transparent 28%),
    radial-gradient(circle at 88% 86%, rgba(255, 188, 148, 0.28), transparent 30%),
    linear-gradient(160deg, #fffaf7 0%, #fff4ed 48%, #fffdfb 100%);
  text-align: center;
  box-shadow: 0 12px 32px rgba(148, 80, 45, 0.08);
}

.cert-sheet.is-team {
  border-color: rgba(180, 120, 28, 0.28);
  outline-color: rgba(180, 120, 28, 0.12);
  color: #6d4c16;
  background:
    radial-gradient(circle at 12% 12%, rgba(255, 228, 170, 0.45), transparent 28%),
    radial-gradient(circle at 88% 86%, rgba(245, 196, 112, 0.24), transparent 30%),
    linear-gradient(160deg, #fffdf7 0%, #fff6e4 48%, #fffdf9 100%);
}

.cert-sheet--uploaded {
  padding: 16px;
  min-height: 240px;
}

.cert-sheet__image {
  max-width: 100%;
  max-height: 56vh;
  object-fit: contain;
  border-radius: 4px;
  display: block;
  margin: 0 auto;
}

.cert-sheet__frame,
.cert-sheet__glow {
  position: absolute;
  inset: 14px;
  pointer-events: none;
}

.cert-sheet__frame {
  border: 1px dashed rgba(232, 74, 28, 0.18);
}

.cert-sheet.is-team .cert-sheet__frame {
  border-color: rgba(180, 120, 28, 0.2);
}

.cert-sheet__glow {
  inset: 0;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.35), transparent);
  opacity: 0.55;
}

.cert-sheet__brand {
  position: relative;
  z-index: 1;
  display: grid;
  gap: 4px;
  justify-items: center;
}

.cert-sheet__brand span {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.12em;
}

.cert-sheet__brand img {
  width: 24px;
  height: 24px;
  object-fit: contain;
}

.cert-sheet__brand b {
  font: inherit;
}

.cert-sheet__brand em {
  color: #9b766a;
  font-size: 10px;
  font-style: normal;
}

.cert-sheet__title {
  position: relative;
  z-index: 1;
  margin: 8px 0 0;
  font-size: 34px;
  letter-spacing: 0.28em;
  line-height: 1;
  font-weight: 800;
}

.cert-sheet__grant {
  position: relative;
  z-index: 1;
  margin: 10px 0 0;
  color: #7f574a;
  font-size: 13px;
}

.cert-sheet__grant b {
  color: #6d2b18;
  font-size: 15px;
}

.cert-sheet__name {
  position: relative;
  z-index: 1;
  margin: 8px 0 0;
  color: #e84a1c;
  font-size: 22px;
  line-height: 1.35;
  font-weight: 800;
}

.cert-sheet.is-team .cert-sheet__name {
  color: #b37a12;
}

.cert-sheet__level {
  position: relative;
  z-index: 1;
  margin: 4px 0 0;
  min-height: 24px;
  padding: 0 10px;
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  color: #9a4a1f;
  background: rgba(232, 74, 28, 0.08);
  font-size: 12px;
  font-weight: 700;
}

.cert-sheet__desc {
  position: relative;
  z-index: 1;
  margin: 12px 0 0;
  max-width: 440px;
  color: #805546;
  font-size: 13px;
  line-height: 1.75;
}

.cert-sheet__meta {
  position: relative;
  z-index: 1;
  width: min(100%, 420px);
  margin-top: 24px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
}

.cert-sheet__meta span {
  display: grid;
  gap: 4px;
  text-align: left;
}

.cert-sheet__meta small {
  color: #9b766a;
  font-size: 11px;
}

.cert-sheet__meta strong {
  color: #6d2b18;
  font-size: 13px;
}

.cert-sheet__seal {
  position: absolute;
  right: 38px;
  bottom: 42px;
  width: 64px;
  height: 64px;
  display: grid;
  place-items: center;
  border: 3px solid rgba(196, 58, 18, 0.36);
  border-radius: 50%;
  color: rgba(196, 58, 18, 0.55);
  background: rgba(255, 255, 255, 0.42);
  font-size: 15px;
  font-weight: 800;
  letter-spacing: 0.04em;
  transform: rotate(-12deg);
  z-index: 1;
  box-shadow: inset 0 0 0 4px rgba(196, 58, 18, 0.08);
}

.cert-sheet.is-team .cert-sheet__seal {
  border-color: rgba(163, 112, 28, 0.4);
  color: rgba(128, 93, 29, 0.58);
  box-shadow: inset 0 0 0 4px rgba(163, 112, 28, 0.08);
}

@media (max-width: 640px) {
  .cert-sheet {
    min-height: 320px;
    padding: 28px 20px 32px;
  }
  .cert-sheet__title {
    font-size: 28px;
    letter-spacing: 0.2em;
  }
  .cert-sheet__name {
    font-size: 18px;
  }
  .cert-sheet__seal {
    width: 52px;
    height: 52px;
    right: 18px;
    bottom: 24px;
    font-size: 13px;
  }
  .cert-modal__foot {
    flex-direction: column;
  }
  .cert-modal__foot .teacher-btn {
    width: 100%;
    justify-content: center;
  }
}
</style>
