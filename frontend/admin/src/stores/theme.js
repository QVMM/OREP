import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

const STORAGE_KEY = 'orep_theme_mode'
const THEME_MODES = ['dark', 'light', 'system']

let mediaQuery = null
let mediaListenerBound = false

function readStoredMode() {
  if (typeof window === 'undefined') return 'light'
  const stored = window.localStorage.getItem(STORAGE_KEY)
  return THEME_MODES.includes(stored) ? stored : 'light'
}

export const useThemeStore = defineStore('theme', () => {
  const mode = ref(readStoredMode())
  const systemDark = ref(false)

  const resolvedTheme = computed(() => {
    if (mode.value === 'system') return systemDark.value ? 'dark' : 'light'
    return mode.value
  })

  const isDark = computed(() => resolvedTheme.value === 'dark')
  const label = computed(() => {
    if (mode.value === 'system') return '跟随系统'
    return isDark.value ? '深色' : '浅色'
  })

  function applyTheme() {
    if (typeof document === 'undefined') return
    document.documentElement.dataset.theme = resolvedTheme.value
    document.documentElement.dataset.themeMode = mode.value
    document.documentElement.style.colorScheme = resolvedTheme.value
  }

  function setMode(nextMode) {
    mode.value = THEME_MODES.includes(nextMode) ? nextMode : 'light'
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(STORAGE_KEY, mode.value)
    }
    applyTheme()
  }

  function cycleTheme() {
    const currentIndex = THEME_MODES.indexOf(mode.value)
    setMode(THEME_MODES[(currentIndex + 1) % THEME_MODES.length])
  }

  function initTheme() {
    if (typeof window === 'undefined') return
    mode.value = readStoredMode()
    mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    systemDark.value = mediaQuery.matches

    if (!mediaListenerBound) {
      const handleSystemThemeChange = (event) => {
        systemDark.value = event.matches
        if (mode.value === 'system') applyTheme()
      }
      if (mediaQuery.addEventListener) {
        mediaQuery.addEventListener('change', handleSystemThemeChange)
      } else if (mediaQuery.addListener) {
        mediaQuery.addListener(handleSystemThemeChange)
      }
      mediaListenerBound = true
    }

    applyTheme()
  }

  return {
    mode,
    resolvedTheme,
    isDark,
    label,
    setMode,
    cycleTheme,
    initTheme
  }
})
