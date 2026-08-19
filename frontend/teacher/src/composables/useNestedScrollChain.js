import { onBeforeUnmount, onMounted, unref, watch } from 'vue'

/**
 * 找到真正承载页面滚动的祖先（教师端是 .teacher-main，不是 window）。
 */
function findScrollParent(node) {
  let p = node?.parentElement || null
  while (p && p !== document.body && p !== document.documentElement) {
    const style = window.getComputedStyle(p)
    const oy = style.overflowY
    const scrollableY =
      (oy === 'auto' || oy === 'scroll' || oy === 'overlay') &&
      p.scrollHeight > p.clientHeight + 1
    if (scrollableY) return p
    p = p.parentElement
  }
  return document.scrollingElement || document.documentElement
}

/** 统一成像素 delta（兼容鼠标滚轮 line/page 模式） */
function normalizeWheelDelta(event, port) {
  let dy = event.deltaY
  let dx = event.deltaX
  if (event.deltaMode === 1) {
    // DOM_DELTA_LINE
    const line = 40
    dy *= line
    dx *= line
  } else if (event.deltaMode === 2) {
    // DOM_DELTA_PAGE
    const page = port?.clientHeight || window.innerHeight || 800
    dy *= page
    dx *= page
  }
  return { dy, dx }
}

function scrollNodeBy(node, dy, dx = 0) {
  if (!node) return
  // 直接改 scrollTop，比 scrollBy 更跟手
  node.scrollTop += dy
  if (dx) node.scrollLeft += dx
}

/**
 * 仅在「嵌套容器仍可滚动且未到边界」时保留内滚；
 * 其余情况把滚轮交给外层滚动容器。
 *
 * 注意：JS 接管会失去触控板惯性，因此应尽量少用 alwaysChain，
 * 优先用 CSS（overflow:hidden / 取消内滚）走原生滚动。
 */
export function useNestedScrollChain(target, options = {}) {
  let el = null
  let bound = false

  function resolveEl() {
    const raw = typeof target === 'function' ? target() : unref(target)
    return raw instanceof HTMLElement ? raw : null
  }

  function isEnabled() {
    const e = options.enabled
    if (e === undefined || e === null) return true
    if (typeof e === 'function') return !!e()
    return !!unref(e)
  }

  function chainToPage(node, dy, dx = 0) {
    const parent = findScrollParent(node)
    scrollNodeBy(parent || document.scrollingElement || document.documentElement, dy, dx)
  }

  function onWheel(event) {
    if (!isEnabled()) return
    const node = el
    if (!node || !node.isConnected) return
    if (event.ctrlKey) return

    const parent = findScrollParent(node)
    const { dy, dx } = normalizeWheelDelta(event, parent)
    if (!dy && !dx) return

    // 始终交给外层（会丢惯性，仅作兜底；优先用 CSS 避免调用）
    if (options.alwaysChainToPage) {
      event.preventDefault()
      chainToPage(node, dy, dx)
      return
    }

    // 未聚焦：交给外层（富文本浏览态）
    if (options.pageScrollUnlessFocused) {
      const focused =
        node.matches(':focus-within') ||
        !!node.closest('.is-focused') ||
        !!node.querySelector?.('.ProseMirror-focused')
      if (!focused) {
        // 若 CSS 已是 overflow:hidden，浏览器会原生冒泡；这里不再 preventDefault
        // 只有仍可滚动时才拦截
        if (node.scrollHeight > node.clientHeight + 1) {
          event.preventDefault()
          chainToPage(node, dy, dx)
        }
        return
      }
    }

    const canScrollY = node.scrollHeight > node.clientHeight + 1
    if (Math.abs(dy) >= Math.abs(dx)) {
      if (!canScrollY) {
        // 无内滚 → 不拦截，交给浏览器原生滚外层（保留惯性）
        return
      }
      const top = node.scrollTop
      const max = node.scrollHeight - node.clientHeight
      const atTop = top <= 0.5
      const atBottom = top >= max - 0.5
      if ((dy < 0 && atTop) || (dy > 0 && atBottom)) {
        event.preventDefault()
        chainToPage(node, dy, dx)
      }
      // 中间：原生内滚（保留惯性）
      return
    }
  }

  function bind(node) {
    unbind()
    el = node
    if (!el) return
    el.addEventListener('wheel', onWheel, { passive: false, capture: true })
    bound = true
  }

  function unbind() {
    if (bound && el) {
      el.removeEventListener('wheel', onWheel, { capture: true })
    }
    bound = false
    el = null
  }

  onMounted(() => {
    bind(resolveEl())
    watch(() => resolveEl(), (node) => bind(node), { flush: 'post' })
  })

  onBeforeUnmount(unbind)

  return { refresh: () => bind(resolveEl()), unbind }
}
