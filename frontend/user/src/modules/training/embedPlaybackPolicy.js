/** 站外内嵌视频：iframe 内点击到不了父页面，不能用父页指针空闲判断「没在看」。 */

export const EMBED_HEARTBEAT_MS = 8000

export function isEmbedLearningActive({ pageVisible, activated } = {}) {
  return Boolean(pageVisible) && Boolean(activated)
}

export function embedSessionStorageKey(resourceId) {
  return `orep_embed_learn_session:${resourceId || 'unknown'}`
}

export function readOrCreateEmbedSessionId(storage, resourceId, createId) {
  const key = embedSessionStorageKey(resourceId)
  try {
    const existing = storage?.getItem?.(key)
    if (existing && /^[A-Za-z0-9_-]{8,64}$/.test(existing)) return existing
    const next = typeof createId === 'function' ? createId() : `embed_${Date.now()}`
    storage?.setItem?.(key, next)
    return next
  } catch {
    return typeof createId === 'function' ? createId() : `embed_${Date.now()}`
  }
}
