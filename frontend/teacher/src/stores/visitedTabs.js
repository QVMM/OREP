import { defineStore } from 'pinia'
import { pathTitle } from '../config/nav'

function normalizePath(path, query = {}) {
  if (path === '/resources') {
    const scope = query.scope === 'public' ? 'public' : 'team'
    return `/resources?scope=${scope}`
  }
  return path || '/'
}

function parseKey(key) {
  if (key.includes('?')) {
    const [path, qs] = key.split('?')
    const query = Object.fromEntries(new URLSearchParams(qs))
    return { path, query }
  }
  return { path: key, query: {} }
}

export const useVisitedTabsStore = defineStore('teacherVisitedTabs', {
  state: () => ({
    tabs: [{ key: '/', title: '首页', affix: true }],
  }),
  actions: {
    remember(route) {
      const key = normalizePath(route.path, route.query || {})
      const title = pathTitle(route.path, route.query || {})
      if (!this.tabs.some((t) => t.key === key)) {
        this.tabs.push({ key, title, affix: key === '/' })
      } else {
        const tab = this.tabs.find((t) => t.key === key)
        if (tab) tab.title = title
      }
    },
    close(key, router, currentKey) {
      const index = this.tabs.findIndex((t) => t.key === key)
      if (index < 0 || this.tabs[index].affix) return
      const isCurrent = currentKey === key
      this.tabs.splice(index, 1)
      if (isCurrent) {
        const next = this.tabs[Math.max(0, index - 1)] || this.tabs[0]
        const loc = parseKey(next.key)
        router.push(loc.query && Object.keys(loc.query).length ? loc : loc.path)
      }
    },
    open(key, router) {
      const loc = parseKey(key)
      router.push(loc.query && Object.keys(loc.query).length ? loc : loc.path)
    },
    currentKey(route) {
      return normalizePath(route.path, route.query || {})
    },
  },
})
