<template>
  <div
    class="workspace-app"
    :class="{
      'is-motion-enabled': isWorkspaceMotionEnabled,
      'is-desktop-rail': !isMobileChrome
    }"
  >
    <!-- 桌面侧栏轨；移动端隐藏且不挂载，避免与顶栏重复拉消息 -->
    <WorkspaceSidebar v-if="!isMobileChrome" />
    <!-- 桌面：无顶栏（能力迁入左侧轨）；移动端：保留消息/账户顶栏 -->
    <WorkspaceTopbar v-if="isMobileChrome" />
    <main
      ref="mainRef"
      class="workspace-main workspace-scrollbar"
      :class="{
        'is-home-page': route.path === '/',
        'is-flush': isFlushPage,
        'is-score-report-page': isScoreReportPage,
        'is-route-switching': isRouteSwitching,
      }"
    >
      <div class="workspace-view-host">
        <router-view v-slot="{ Component, route: workspaceRoute }">
          <!--
            切换策略（残影 / 卡顿治理）：
            1) 涉及 keep-alive 首页：关闭 CSS 过渡，瞬时切换，并在钩子里清 opacity 残留
            2) 其它页：mode=out-in + 仅 opacity 短淡入淡出（禁止 translate 叠层残影）
            3) 切到沉浸/重页：不动画
          -->
          <Transition
            :name="workspaceTransitionName"
            :css="routeTransitionCss"
            :mode="routeTransitionMode"
            @before-leave="onViewBeforeLeave"
            @after-leave="onViewAfterLeave"
            @before-enter="onViewBeforeEnter"
            @after-enter="onViewAfterEnter"
          >
            <keep-alive :include="['DashboardHome']">
              <component
                :is="Component"
                :key="workspaceViewKey(workspaceRoute)"
                class="workspace-view-page"
              />
            </keep-alive>
          </Transition>
        </router-view>
      </div>
    </main>
    <WorkspaceMobileNav />
    <CollaborationHub />
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import CollaborationHub from '../collaboration/CollaborationHub.vue'
import WorkspaceMobileNav from './WorkspaceMobileNav.vue'
import WorkspaceSidebar from './WorkspaceSidebar.vue'
import WorkspaceTopbar from './WorkspaceTopbar.vue'

const route = useRoute()
const mainRef = ref(null)
const hasNavigated = ref(false)
/** 本跳是否跑 CSS 过渡（不含首页 keep-alive） */
const routeTransitionEnabled = ref(false)
const isRouteSwitching = ref(false)
const previousPath = ref(route.path)
const previousRouteMotionEligible = ref(shouldAnimateWorkspaceRoute(route))
const isMobileChrome = ref(
  typeof window !== 'undefined' ? window.matchMedia('(max-width: 1023px)').matches : false
)
const isWorkspaceMotionEnabled = computed(() => shouldAnimateWorkspaceRoute(route))
const workspaceTransitionName = computed(() => (
  hasNavigated.value && routeTransitionEnabled.value ? 'workspace-route' : ''
))
/** 空 name 时关掉 CSS，避免 Vue 仍挂 transition 钩子 class 造成残影 */
const routeTransitionCss = computed(() => Boolean(workspaceTransitionName.value))
/** 有动画才 out-in，避免进出叠层；首页瞬时切换不设 mode */
const routeTransitionMode = computed(() => (
  routeTransitionEnabled.value ? 'out-in' : undefined
))
const isScoreReportPage = computed(() => {
  if (!route.path.startsWith('/ai-score/')) return false
  const section = route.path.split('/').filter(Boolean).at(-1)
  return ['result', 'todos', 'why', 'jury'].includes(section)
})
const isFlushPage = computed(() => Boolean(route.meta?.flushMain))

let mobileMql = null
let switchClearTimer = 0
let scrollRaf = 0

function syncMobileChrome() {
  isMobileChrome.value = mobileMql ? mobileMql.matches : false
}

function shouldAnimateWorkspaceRoute(currentRoute) {
  if (currentRoute.meta?.flushMain || currentRoute.meta?.immersive) return false
  const path = currentRoute.path
  return ![
    '/script-editor',
    '/ppt-editor',
    '/ppt-generator',
    '/roadshow',
    '/online-meeting',
    '/meeting/',
    '/my-recordings',
    '/course-learning/',
    '/assistant',
  ].some(prefix => path.startsWith(prefix))
}

/** keep-alive 的首页：禁止参与 opacity 过渡 */
function isKeepAliveHomePath(path) {
  return path === '/'
}

function workspaceViewKey(currentRoute) {
  const path = currentRoute?.path || ''
  if (path === '/assistant' || path.startsWith('/assistant/')) {
    return 'assistant-workspace'
  }
  return path
}

const TRANSITION_RESIDUE_CLASSES = [
  'workspace-route-enter-from',
  'workspace-route-enter-active',
  'workspace-route-enter-to',
  'workspace-route-leave-from',
  'workspace-route-leave-active',
  'workspace-route-leave-to',
  'v-enter-from',
  'v-enter-active',
  'v-enter-to',
  'v-leave-from',
  'v-leave-active',
  'v-leave-to',
]

/** 清掉 keep-alive / 中断过渡留下的 opacity:0 与 class */
function scrubTransitionResidue(el) {
  if (!el || el.nodeType !== 1) return
  el.style.opacity = ''
  el.style.transform = ''
  el.style.pointerEvents = ''
  for (const c of TRANSITION_RESIDUE_CLASSES) {
    el.classList.remove(c)
  }
}

function onViewBeforeLeave(el) {
  isRouteSwitching.value = true
  // leave 层不接收点击，避免残影可点
  if (el?.style) el.style.pointerEvents = 'none'
}

function onViewAfterLeave(el) {
  scrubTransitionResidue(el)
}

function onViewBeforeEnter(el) {
  isRouteSwitching.value = true
  scrubTransitionResidue(el)
}

function onViewAfterEnter(el) {
  scrubTransitionResidue(el)
  isRouteSwitching.value = false
  scheduleScrollReset()
}

watch(
  () => route.fullPath,
  () => {
    const fromPath = previousPath.value
    const toPath = route.path
    const nextRouteMotionEligible = shouldAnimateWorkspaceRoute(route)
    const involvesKeepAliveHome = isKeepAliveHomePath(fromPath) || isKeepAliveHomePath(toPath)

    // 首页 keep-alive 永不走 CSS 过渡（防 opacity 粘死 + 出/入叠层残影）
    routeTransitionEnabled.value = (
      hasNavigated.value
      && !involvesKeepAliveHome
      && previousRouteMotionEligible.value
      && nextRouteMotionEligible
    )

    // 瞬时切换也要短暂锁 overflow，减少首页 padding 变化时的闪动
    isRouteSwitching.value = true
    if (switchClearTimer) window.clearTimeout(switchClearTimer)
    switchClearTimer = window.setTimeout(() => {
      isRouteSwitching.value = false
      // 再扫一遍当前页，清 keep-alive 回填可能带回的残类
      const host = mainRef.value?.querySelector?.('.workspace-view-page')
      scrubTransitionResidue(host)
    }, routeTransitionEnabled.value ? 280 : 32)

    previousRouteMotionEligible.value = nextRouteMotionEligible
    previousPath.value = toPath
    hasNavigated.value = true
  },
  { flush: 'sync' }
)

watch(
  () => route.fullPath,
  () => {
    // 单次 rAF 滚顶，避免 nextTick + rAF + 80ms 三重滚动造成卡顿
    scheduleScrollReset()
  },
  { flush: 'post' }
)

function scheduleScrollReset() {
  if (scrollRaf) cancelAnimationFrame(scrollRaf)
  scrollRaf = requestAnimationFrame(() => {
    scrollRaf = 0
    resetWorkspaceScroll()
  })
}

function resetWorkspaceScroll() {
  const main = mainRef.value
  if (main) {
    main.scrollTop = 0
    main.scrollLeft = 0
  }
  // 仅在 window 真的滚了时再动，减少无谓 layout
  if (window.scrollY !== 0 || window.scrollX !== 0) {
    window.scrollTo(0, 0)
  }
}

onMounted(() => {
  mobileMql = window.matchMedia('(max-width: 1023px)')
  syncMobileChrome()
  mobileMql.addEventListener?.('change', syncMobileChrome)
  mobileMql.addListener?.(syncMobileChrome)
})

onBeforeUnmount(() => {
  mobileMql?.removeEventListener?.('change', syncMobileChrome)
  mobileMql?.removeListener?.(syncMobileChrome)
  if (switchClearTimer) window.clearTimeout(switchClearTimer)
  if (scrollRaf) cancelAnimationFrame(scrollRaf)
})
</script>

<style scoped>
.workspace-app {
  width: 100%;
  height: 100vh;
  min-height: 100vh;
  display: grid;
  /* 得到大脑式：仅侧栏 + 全高主区，无顶栏行 */
  grid-template-columns: var(--workspace-sidebar-width) minmax(0, 1fr);
  grid-template-rows: minmax(0, 1fr);
  background-color: var(--ds-canvas, #f7f7f8);
  background-image: none;
  /*
   * 不可 overflow:hidden：会裁掉侧栏 hover 气泡（向右伸出轨外）。
   * 页面滚动只交给 .workspace-main。
   */
  overflow: visible;
}

.workspace-main {
  box-sizing: border-box;
  position: relative;
  z-index: 1;
  grid-column: 2;
  grid-row: 1;
  width: 100%;
  height: 100vh;
  min-height: 0;
  min-width: 0;
  overflow-x: hidden;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  overscroll-behavior-y: none;
  padding: var(--ds-page-margin-y, 40px) var(--ds-page-margin-x, 40px);
  background-color: var(--ds-canvas, #f7f7f8);
  background-image: none;
  /* padding 变化用同一 canvas，减少首页进出时的「闪边」 */
  transition: padding 0.12s var(--ds-motion-ease-standard, ease);
}

.workspace-main.is-route-switching {
  /* 切换瞬间禁止主区滚动条跳动与双层可点 */
  overflow-y: hidden;
  pointer-events: none;
}

.workspace-main.is-flush {
  padding: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: none;
}

.workspace-main.is-flush > .workspace-view-host,
.workspace-main.is-flush .workspace-view-page {
  flex: 1 1 auto;
  min-height: 0;
  min-width: 0;
}

/*
 * 评分报告：主区定高 + 内部滚动。
 * 避免「子层 overflow:auto + overscroll contain 却无定高」吞掉滚轮，
 * 导致中间区域滚不动、外层 workspace-main 也滚不动。
 */
.workspace-main.is-score-report-page {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  overscroll-behavior: none;
  background-color: var(--ds-canvas, #f7f7f8);
  background-image: none;
}

.workspace-main.is-score-report-page > .workspace-view-host,
.workspace-main.is-score-report-page .workspace-view-page {
  flex: 1 1 auto;
  min-height: 0;
  min-width: 0;
  width: 100%;
  display: flex;
  flex-direction: column;
}

/*
 * 首页：整页不滚动。圆润统一页边，高度锁在主区内；
 * 左右栏局部滚动；小启是文档流分栏，不是悬浮层。
 */
.workspace-main.is-home-page {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  overscroll-behavior: none;
  padding: 24px 24px 20px;
  box-sizing: border-box;
}

.workspace-main.is-home-page > .workspace-view-host,
.workspace-main.is-home-page .workspace-view-page {
  flex: 1 1 auto;
  min-height: 0;
  min-width: 0;
  width: 100%;
}

/* 视图宿主：保证 out-in 时高度稳定、不叠两页 */
.workspace-view-host {
  position: relative;
  width: 100%;
  min-width: 0;
  min-height: 0;
  isolation: isolate;
}

.workspace-view-page {
  width: 100%;
  min-width: 0;
  /* 防止 leave 的 opacity 残留粘在 keep-alive 根上后看不见 */
  opacity: 1;
  transform: none;
  backface-visibility: hidden;
}

/*
 * 仅 opacity，禁止 translate：双页短暂同屏时 translate 最像「残影」。
 * out-in 下 leave 先结束再 enter，更干净。
 */
.workspace-route-enter-active,
.workspace-route-leave-active {
  transition: opacity 150ms var(--ds-motion-ease-standard, cubic-bezier(0.2, 0, 0, 1));
  will-change: opacity;
}

.workspace-route-enter-from,
.workspace-route-leave-to {
  opacity: 0;
}

.workspace-route-enter-to,
.workspace-route-leave-from {
  opacity: 1;
}

@media (max-width: 1023px) {
  .workspace-app {
    display: block;
    min-height: 100dvh;
    min-height: 100vh;
    height: 100dvh;
    height: 100vh;
    overflow: auto;
    padding-bottom: env(safe-area-inset-bottom, 0px);
  }

  .workspace-main {
    width: 100%;
    min-height: 100dvh;
    min-height: 100vh;
    height: auto;
    overflow: visible;
    padding: 16px 16px calc(96px + env(safe-area-inset-bottom, 0px));
  }

  .workspace-main.is-flush {
    padding: 0 0 calc(72px + env(safe-area-inset-bottom, 0px));
    min-height: 100dvh;
    height: auto;
    overflow: auto;
  }

  /* 移动端评分报告仍锁主区高度，保证内部 .result-scroll 可滚 */
  .workspace-main.is-score-report-page {
    height: 100dvh;
    height: 100vh;
    min-height: 0;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    padding: 16px 16px calc(96px + env(safe-area-inset-bottom, 0px));
  }

  .workspace-main.is-score-report-page > .workspace-view-host,
  .workspace-main.is-score-report-page .workspace-view-page {
    flex: 1 1 auto;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }
}

@media (max-width: 720px) {
  .workspace-main:not(.is-flush) {
    padding: 12px 14px calc(88px + env(safe-area-inset-bottom, 0px));
  }

  .workspace-main.is-home-page {
    padding-top: 10px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .workspace-main {
    transition: none;
  }

  .workspace-route-enter-active,
  .workspace-route-leave-active {
    transition-duration: 0.01ms;
  }

  .workspace-route-enter-from,
  .workspace-route-leave-to {
    opacity: 1;
  }
}
</style>
