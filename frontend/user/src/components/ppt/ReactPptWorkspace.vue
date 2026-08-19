<template>
  <div ref="mountRef" class="ppt-react-workspace-shell"></div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import React from 'react'
import { createRoot } from 'react-dom/client'
import { ReactSlideWorkspace } from '@/react-ppt-editor/ReactSlideWorkspace'
import '@/react-ppt-editor/konva-slide-editor.css'
import '@/react-ppt-editor/react-slide-workspace.css'

const props = defineProps({
  slides: {
    type: Array,
    default: () => []
  },
  selectedIndex: {
    type: Number,
    default: 1
  },
  editable: {
    type: Boolean,
    default: false
  },
  downloadUrl: {
    type: String,
    default: ''
  },
  loading: {
    type: Boolean,
    default: false
  },
  createSlide: {
    type: Function,
    required: true
  },
  deleteSlide: {
    type: Function,
    required: true
  },
  refreshPreview: {
    type: Function,
    required: true
  },
  saveSlide: {
    type: Function,
    required: true
  },
  saveNotes: {
    type: Function,
    required: true
  },
  draftKeyPrefix: {
    type: String,
    default: 'ppt-notes'
  }
})

const emit = defineEmits(['select'])

const mountRef = ref(null)
let root = null

class SlideWorkspaceErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, message: '' }
  }

  static getDerivedStateFromError(error) {
    return {
      hasError: true,
      message: error instanceof Error ? error.message : '预览组件渲染异常'
    }
  }

  componentDidUpdate(previousProps) {
    if (previousProps.resetKey !== this.props.resetKey && this.state.hasError) {
      this.setState({ hasError: false, message: '' })
    }
  }

  render() {
    if (!this.state.hasError) return this.props.children
    return React.createElement(
      'div',
      { className: 'ppa-workspace-error' },
      React.createElement('div', { className: 'ppa-workspace-error__kicker' }, 'PREVIEW RECOVERY'),
      React.createElement('h3', null, '预览暂时无法渲染'),
      React.createElement(
        'p',
        null,
        '当前页数据已保留，系统已阻止预览组件继续黑屏。可以刷新预览或切换页面重试。'
      ),
      this.state.message
        ? React.createElement('code', null, this.state.message)
        : null,
      React.createElement(
        'button',
        {
          type: 'button',
          onClick: () => this.setState({ hasError: false, message: '' })
        },
        '重新尝试渲染'
      )
    )
  }
}

function renderReactWorkspace() {
  if (!root) return
  const resetKey = [
    props.selectedIndex,
    props.slides.length,
    props.slides.map((slide) => [
      slide?.index || 0,
      String(slide?.content || '').length,
      String(slide?.notes || '').length,
      String(slide?.document?.speakerNotes || '').length
    ].join(':')).join(',')
  ].join('|')
  root.render(
    React.createElement(
      SlideWorkspaceErrorBoundary,
      { resetKey },
      React.createElement(ReactSlideWorkspace, {
        slides: props.slides,
        selectedIndex: props.selectedIndex,
        editable: props.editable,
        downloadUrl: props.downloadUrl,
        loading: props.loading,
        onSelect: (index) => emit('select', index),
        onCreateSlide: props.createSlide,
        onDeleteSlide: props.deleteSlide,
        onRefresh: props.refreshPreview,
        onSaveSlide: props.saveSlide,
        onSaveNotes: props.saveNotes,
        draftKeyPrefix: props.draftKeyPrefix
      })
    )
  )
}

onMounted(() => {
  root = createRoot(mountRef.value)
  renderReactWorkspace()
})

watch(
  () => [props.slides, props.selectedIndex, props.editable, props.downloadUrl, props.loading, props.draftKeyPrefix],
  renderReactWorkspace,
  { deep: true }
)

onBeforeUnmount(() => {
  if (root) {
    root.unmount()
    root = null
  }
})
</script>
