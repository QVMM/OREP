/**
 * 启发 Office 文档分享（可在微信等场景粘贴直达编辑页）。
 * 对方需登录，且具备该文档权限（个人文档=本人；项目/团队=成员）。
 *
 * 分享域名：始终取浏览器当前访问的 origin（本地 localhost、云端正式域名），不写死。
 */

/** 实时解析当前站点源，避免写死 localhost / 云端域名 */
export function resolveShareOrigin() {
  if (typeof window === 'undefined' || !window.location) return ''
  const { protocol, hostname, port } = window.location
  // hostname 已是当前访问主机：localhost / 127.0.0.1 / www.jingsaidanao.com 等
  if (port && port !== '80' && port !== '443') {
    return `${protocol}//${hostname}:${port}`
  }
  return `${protocol}//${hostname}`
}

export function buildInspireOfficeShareUrl(docId, meta = {}) {
  const id = String(docId || '').trim()
  if (!id) return ''
  const origin = resolveShareOrigin()
  if (!origin) return ''
  const path = `/inspire-office/edit/${encodeURIComponent(id)}`
  const q = new URLSearchParams()
  if (meta.title) q.set('title', String(meta.title).slice(0, 80))
  if (meta.ext) q.set('ext', String(meta.ext).replace(/^\./, ''))
  if (meta.type || meta.documentType) q.set('type', String(meta.type || meta.documentType))
  const qs = q.toString()
  // 完整 URL 单独成行用，此处只返回纯地址（无前后空白）
  return `${origin}${path}${qs ? `?${qs}` : ''}`
}

/**
 * 生成邀请文案。
 * 「访问地址：」后换行，完整 URL 独占一行（便于微信识别为可点链接）。
 */
export function buildInspireOfficeShareMessage(opts = {}) {
  const inviter = String(opts.inviter || opts.username || '我').trim() || '我'
  const title = String(opts.title || '未命名文档').trim() || '未命名文档'
  const team = String(opts.teamName || opts.team || '').trim()
  const url = String(opts.url || buildInspireOfficeShareUrl(opts.docId, opts)).trim()
  if (!url) return ''

  let head
  if (team) {
    head = `${inviter}邀请您加入${team}团队的「${title}」文件共同编辑，访问地址：`
  } else if (opts.scope === 'project' || opts.scope === 'team') {
    head = `${inviter}邀请您加入团队的「${title}」文件共同编辑，访问地址：`
  } else {
    head = `${inviter}邀请您共同编辑「${title}」文件，访问地址：`
  }

  // 冒号后换行，地址单独一行（行首/行尾不带多余空格）
  return `${head}\n${url}`
}

/** 复制文本；优先 Clipboard API，失败时退回 execCommand */
export async function copyTextToClipboard(text) {
  const value = String(text || '')
  if (!value) throw new Error('没有可复制的内容')
  if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(value)
      return true
    } catch {
      // 非安全上下文 / 权限拒绝 → 降级
    }
  }
  if (typeof document === 'undefined') throw new Error('无法复制')
  const ta = document.createElement('textarea')
  ta.value = value
  ta.setAttribute('readonly', '')
  ta.style.position = 'fixed'
  ta.style.left = '-9999px'
  ta.style.top = '0'
  document.body.appendChild(ta)
  ta.select()
  ta.setSelectionRange(0, value.length)
  const ok = document.execCommand('copy')
  document.body.removeChild(ta)
  if (!ok) throw new Error('复制失败')
  return true
}

/**
 * 复制带邀请文案的分享内容。
 * @returns {{ url: string, message: string }}
 */
export async function copyInspireOfficeShareLink(docId, meta = {}) {
  const url = buildInspireOfficeShareUrl(docId, meta)
  if (!url) throw new Error('文档无效')
  const message = buildInspireOfficeShareMessage({
    ...meta,
    docId,
    url,
  })
  await copyTextToClipboard(message)
  return { url, message }
}
