import { computed, nextTick, ref, watch } from 'vue'
import {
  applySkillSlash,
  detectSlashQuery,
  filterSkillsByQuery,
  skillsForAudience,
} from './skillsCatalog'

/**
 * 输入框 `/` 技能菜单逻辑（工作台 + 首页半栏共用）。
 *
 * @param {object} opts
 * @param {import('vue').Ref<string>} opts.textRef - v-model 文本
 * @param {import('vue').Ref<HTMLTextAreaElement|null>} opts.inputRef
 * @param {import('vue').Ref|import('vue').ComputedRef|string} [opts.audience='student']
 * @param {() => boolean} [opts.isDisabled]
 */
export function useSkillSlashMenu(opts) {
  const {
    textRef,
    inputRef,
    audience = 'student',
    isDisabled = () => false,
  } = opts

  const menuOpen = ref(false)
  const menuRange = ref(null)
  const menuQuery = ref('')
  const forcedOpen = ref(false)
  const menuRef = ref(null)

  const audienceValue = computed(() => {
    if (typeof audience === 'string') return audience
    return audience?.value ?? 'student'
  })

  const catalog = computed(() => skillsForAudience(audienceValue.value))

  const menuItems = computed(() => {
    if (forcedOpen.value && !menuQuery.value) return catalog.value
    return filterSkillsByQuery(catalog.value, menuQuery.value)
  })

  function readCursor() {
    const el = inputRef.value
    if (!el || typeof el.selectionStart !== 'number') {
      return String(textRef.value || '').length
    }
    return el.selectionStart
  }

  function refreshFromText() {
    if (isDisabled()) {
      if (menuOpen.value || forcedOpen.value) closeMenu()
      return
    }
    const text = String(textRef.value ?? '')
    const cursor = readCursor()
    const hit = detectSlashQuery(text, cursor)
    if (!hit) {
      if (!forcedOpen.value) closeMenu()
      else {
        // 强制打开时若已离开 slash 态，仅在有 / 前缀时过滤
        menuQuery.value = ''
      }
      return
    }
    forcedOpen.value = false
    menuRange.value = { start: hit.start, end: hit.end }
    menuQuery.value = hit.query
    menuOpen.value = true
  }

  function closeMenu() {
    menuOpen.value = false
    menuRange.value = null
    menuQuery.value = ''
    forcedOpen.value = false
  }

  /** 工具栏「/」按钮：在光标处插入 / 并打开菜单 */
  async function openMenuFromButton() {
    if (isDisabled()) return
    const el = inputRef.value
    const text = String(textRef.value ?? '')
    const cursor = readCursor()
    const needSpace = cursor > 0 && !/[\s\n]/.test(text[cursor - 1] || '')
    const insert = `${needSpace ? ' ' : ''}/`
    textRef.value = text.slice(0, cursor) + insert + text.slice(cursor)
    const nextCursor = cursor + insert.length
    menuRange.value = { start: nextCursor - 1, end: nextCursor }
    menuQuery.value = ''
    forcedOpen.value = true
    menuOpen.value = true
    await nextTick()
    if (el) {
      el.focus()
      el.setSelectionRange(nextCursor, nextCursor)
    }
    refreshFromText()
  }

  async function pickSkill(skill) {
    if (!skill) return
    const text = String(textRef.value ?? '')
    let range = menuRange.value
    if (!range) {
      const cursor = readCursor()
      const hit = detectSlashQuery(text, cursor)
      range = hit || { start: cursor, end: cursor }
    }
    const { text: next, cursor } = applySkillSlash(text, range, skill)
    textRef.value = next
    closeMenu()
    await nextTick()
    const el = inputRef.value
    if (el) {
      el.focus()
      el.setSelectionRange(cursor, cursor)
      // 触发父级 autoGrow（若监听 input）
      el.dispatchEvent(new Event('input', { bubbles: true }))
    }
  }

  /**
   * @param {KeyboardEvent} e
   * @returns {boolean} true = 已消费，父级勿再处理发送
   */
  function onKeydown(e) {
    // `/` 或 `／` 刚按下时 v-model 可能尚未写入，下一帧再扫
    if (e.key === '/' || e.key === '／' || e.code === 'Slash') {
      requestAnimationFrame(() => refreshFromText())
    }

    if (!menuOpen.value || !menuItems.value.length) {
      if (e.key.length === 1 || e.key === 'Backspace' || e.key === 'Delete') {
        requestAnimationFrame(() => refreshFromText())
      }
      return false
    }

    if (e.key === 'Escape') {
      e.preventDefault()
      closeMenu()
      return true
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      menuRef.value?.move?.(1)
      return true
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault()
      menuRef.value?.move?.(-1)
      return true
    }
    if (e.key === 'Enter' || e.key === 'Tab') {
      // IME 选词中不抢
      if (e.isComposing || e.keyCode === 229) return false
      e.preventDefault()
      menuRef.value?.pickActive?.()
      return true
    }
    if (e.key === 'Backspace' || e.key === 'Delete' || e.key.length === 1) {
      requestAnimationFrame(() => refreshFromText())
    }
    return false
  }

  function onInput() {
    // 等 v-model 同步后再匹配
    nextTick(() => refreshFromText())
  }

  function onSelect() {
    nextTick(() => refreshFromText())
  }

  watch(textRef, () => {
    nextTick(() => refreshFromText())
  })

  return {
    menuOpen,
    menuItems,
    menuRef,
    menuQuery,
    catalog,
    refreshFromText,
    closeMenu,
    openMenuFromButton,
    pickSkill,
    onKeydown,
    onInput,
    onSelect,
  }
}
