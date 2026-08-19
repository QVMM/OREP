import StarterKit from '@tiptap/starter-kit'
import Placeholder from '@tiptap/extension-placeholder'
import Link from '@tiptap/extension-link'
import Underline from '@tiptap/extension-underline'
import TaskList from '@tiptap/extension-task-list'
import TaskItem from '@tiptap/extension-task-item'
import Highlight from '@tiptap/extension-highlight'
import { TextStyle } from '@tiptap/extension-text-style'
import { Color } from '@tiptap/extension-color'
import Image from '@tiptap/extension-image'
import { Table, TableRow, TableCell, TableHeader } from '@tiptap/extension-table'
import { Extension, Mark, Node, mergeAttributes } from '@tiptap/core'
import { VueNodeViewRenderer } from '@tiptap/vue-3'
import ProtectedRegionView from '../nodes/ProtectedRegionView.vue'
import MindMapView from '../nodes/MindMapView.vue'
import FlowChartView from '../nodes/FlowChartView.vue'
import ScriptSheetView from '../nodes/ScriptSheetView.vue'
import ScriptStepView from '../nodes/ScriptStepView.vue'
import {
  createCloudDocJSON,
  createColumnsJSON,
  createDateChipJSON,
  createEmptyTableJSON,
  createFileCardJSON,
  createMediaBlockJSON,
  createProtectedRegionJSON,
  EMOJI_ITEMS,
  groupSlashItems,
  SLASH_CATALOG,
  SLASH_GROUP_ORDER,
} from './smartDocBlocks.js'
import { createFlowChartJSON, createMindMapJSON, defaultFlowChart, defaultMindMap } from './smartDocDiagrams.js'
import { SdocAwareness } from '../collab/sdocAwareness.js'

export {
  createCloudDocJSON,
  createColumnsJSON,
  createDateChipJSON,
  createEmptyTableJSON,
  createFileCardJSON,
  createMediaBlockJSON,
  createProtectedRegionJSON,
  createFlowChartJSON,
  createMindMapJSON,
  EMOJI_ITEMS,
  groupSlashItems,
  SLASH_CATALOG,
  SLASH_GROUP_ORDER,
}

export const HighlightBlock = Node.create({
  name: 'highlightBlock',
  group: 'block',
  content: 'block+',
  defining: true,
  addAttributes() {
    return {
      tone: { default: 'note' },
    }
  },
  parseHTML() {
    return [{ tag: 'aside[data-sdoc-callout]' }]
  },
  renderHTML({ HTMLAttributes }) {
    return [
      'aside',
      mergeAttributes(HTMLAttributes, {
        'data-sdoc-callout': '',
        class: `sdoc-callout is-${HTMLAttributes.tone || 'note'}`,
      }),
      0,
    ]
  },
})

const COLUMN_CONTENT = '(paragraph | heading | bulletList | orderedList | taskList | blockquote | codeBlock | highlightBlock | table | image | fileCard | cloudDoc | mediaBlock | protectedRegion | mindMap | flowChart | horizontalRule)+'

export const ProtectedRegion = Node.create({
  name: 'protectedRegion',
  group: 'block',
  content: 'block+',
  defining: true,
  isolating: true,
  addOptions() {
    return { canEditProtected: false }
  },
  addAttributes() {
    return {
      id: { default: '' },
      minRole: { default: 'TEACHER' },
      label: { default: '仅教师可见' },
      sealed: { default: false },
    }
  },
  parseHTML() {
    return [{ tag: 'section[data-sdoc-protect]' }]
  },
  renderHTML({ HTMLAttributes }) {
    return [
      'section',
      mergeAttributes(HTMLAttributes, {
        'data-sdoc-protect': '',
        class: `sdoc-protect${HTMLAttributes.sealed ? ' is-sealed' : ''}`,
      }),
      0,
    ]
  },
  addNodeView() {
    return VueNodeViewRenderer(ProtectedRegionView)
  },
})

export const Column = Node.create({
  name: 'column',
  content: COLUMN_CONTENT,
  isolating: true,
  parseHTML() {
    return [{ tag: 'div[data-sdoc-column]' }]
  },
  renderHTML({ HTMLAttributes }) {
    return ['div', mergeAttributes(HTMLAttributes, { 'data-sdoc-column': '', class: 'sdoc-column' }), 0]
  },
})

export const Columns = Node.create({
  name: 'columns',
  group: 'block',
  content: 'column{2,3}',
  defining: true,
  isolating: true,
  addAttributes() {
    return {
      count: {
        default: 2,
        parseHTML: (el) => Number(el.getAttribute('data-count') || 2),
        renderHTML: (attrs) => ({ 'data-count': attrs.count || 2 }),
      },
    }
  },
  parseHTML() {
    return [{ tag: 'div[data-sdoc-columns]' }]
  },
  renderHTML({ HTMLAttributes }) {
    return [
      'div',
      mergeAttributes(HTMLAttributes, {
        'data-sdoc-columns': '',
        class: 'sdoc-columns',
      }),
      0,
    ]
  },
})

export const FileCard = Node.create({
  name: 'fileCard',
  group: 'block',
  atom: true,
  selectable: true,
  draggable: true,
  addAttributes() {
    return {
      url: { default: '' },
      name: { default: '附件' },
      size: { default: 0 },
      mime: { default: '' },
    }
  },
  parseHTML() {
    return [{ tag: 'a[data-sdoc-file]' }]
  },
  renderHTML({ HTMLAttributes }) {
    const size = Number(HTMLAttributes.size) || 0
    const sizeLabel = size >= 1048576
      ? `${(size / 1048576).toFixed(1)} MB`
      : size >= 1024
        ? `${(size / 1024).toFixed(1)} KB`
        : size
          ? `${size} B`
          : ''
    return [
      'a',
      mergeAttributes(HTMLAttributes, {
        'data-sdoc-file': '',
        class: 'sdoc-card sdoc-card--file',
        href: HTMLAttributes.url || '#',
        target: '_blank',
        rel: 'noopener',
        download: HTMLAttributes.name || true,
      }),
      ['b', { class: 'sdoc-card__mark', 'data-kind': 'file' }, '文'],
      [
        'span',
        { class: 'sdoc-card__meta' },
        ['strong', {}, HTMLAttributes.name || '附件'],
        ['small', {}, sizeLabel ? `本地文件 · ${sizeLabel}` : '本地文件'],
      ],
    ]
  },
})

export const CloudDoc = Node.create({
  name: 'cloudDoc',
  group: 'block',
  atom: true,
  selectable: true,
  draggable: true,
  addAttributes() {
    return {
      documentId: { default: '' },
      title: { default: '云文档' },
      ext: { default: '' },
      kind: { default: 'word' },
      href: { default: '#' },
    }
  },
  parseHTML() {
    return [{ tag: 'a[data-sdoc-cloud]' }]
  },
  renderHTML({ HTMLAttributes }) {
    const mark = HTMLAttributes.kind === 'sdoc'
      ? '智'
      : HTMLAttributes.kind === 'sheet'
        ? 'X'
        : HTMLAttributes.kind === 'slide'
          ? 'P'
          : 'W'
    return [
      'a',
      mergeAttributes(HTMLAttributes, {
        'data-sdoc-cloud': '',
        class: 'sdoc-card sdoc-card--cloud',
        href: HTMLAttributes.href || '#',
      }),
      ['b', { class: 'sdoc-card__mark', 'data-kind': HTMLAttributes.kind || 'word' }, mark],
      [
        'span',
        { class: 'sdoc-card__meta' },
        ['strong', {}, HTMLAttributes.title || '云文档'],
        ['small', {}, `启发 Office · ${HTMLAttributes.ext || '文档'}`],
      ],
    ]
  },
})

export const DateChip = Node.create({
  name: 'dateChip',
  group: 'inline',
  inline: true,
  atom: true,
  selectable: true,
  addAttributes() {
    return {
      value: { default: '' },
    }
  },
  parseHTML() {
    return [{ tag: 'time[data-sdoc-date]' }]
  },
  renderHTML({ HTMLAttributes }) {
    return [
      'time',
      mergeAttributes(HTMLAttributes, {
        'data-sdoc-date': '',
        class: 'sdoc-date',
        datetime: HTMLAttributes.value || '',
      }),
      HTMLAttributes.value || '日期',
    ]
  },
})

export const MindMap = Node.create({
  name: 'mindMap',
  group: 'block',
  atom: true,
  selectable: true,
  draggable: true,
  addAttributes() {
    return {
      data: {
        default: defaultMindMap(),
        parseHTML: (el) => {
          try {
            return JSON.parse(el.getAttribute('data-sdoc-map') || '') || defaultMindMap()
          } catch {
            return defaultMindMap()
          }
        },
        renderHTML: (attrs) => ({ 'data-sdoc-map': JSON.stringify(attrs.data || defaultMindMap()) }),
      },
    }
  },
  parseHTML() {
    return [{ tag: 'figure[data-sdoc-mind]' }]
  },
  renderHTML({ HTMLAttributes }) {
    return [
      'figure',
      {
        'data-sdoc-mind': '',
        class: 'sdoc-diagram',
        'data-sdoc-map': JSON.stringify(HTMLAttributes.data || defaultMindMap()),
      },
    ]
  },
  addNodeView() {
    return VueNodeViewRenderer(MindMapView)
  },
})

export const FlowChart = Node.create({
  name: 'flowChart',
  group: 'block',
  atom: true,
  selectable: true,
  draggable: true,
  addAttributes() {
    return {
      data: {
        default: defaultFlowChart(),
        parseHTML: (el) => {
          try {
            return JSON.parse(el.getAttribute('data-sdoc-flow') || '') || defaultFlowChart()
          } catch {
            return defaultFlowChart()
          }
        },
        renderHTML: (attrs) => ({ 'data-sdoc-flow': JSON.stringify(attrs.data || defaultFlowChart()) }),
      },
    }
  },
  parseHTML() {
    return [{ tag: 'figure[data-sdoc-flow]' }]
  },
  renderHTML({ HTMLAttributes }) {
    return [
      'figure',
      {
        'data-sdoc-flow': '',
        class: 'sdoc-diagram',
        'data-sdoc-flow': JSON.stringify(HTMLAttributes.data || defaultFlowChart()),
      },
    ]
  },
  addNodeView() {
    return VueNodeViewRenderer(FlowChartView)
  },
})

export const MediaBlock = Node.create({
  name: 'mediaBlock',
  group: 'block',
  atom: true,
  selectable: true,
  draggable: true,
  addAttributes() {
    return {
      src: { default: '' },
      kind: { default: 'video' },
      name: { default: '' },
    }
  },
  parseHTML() {
    return [{ tag: 'figure[data-sdoc-media]' }]
  },
  renderHTML({ HTMLAttributes }) {
    const tag = HTMLAttributes.kind === 'audio' ? 'audio' : 'video'
    return [
      'figure',
      mergeAttributes(HTMLAttributes, {
        'data-sdoc-media': '',
        class: 'sdoc-media',
        'data-kind': HTMLAttributes.kind || 'video',
      }),
      [tag, { src: HTMLAttributes.src || '', controls: 'true' }],
      ['figcaption', {}, HTMLAttributes.name || (tag === 'audio' ? '音频' : '视频')],
    ]
  },
})

export const Superscript = Mark.create({
  name: 'superscript',
  parseHTML() {
    return [{ tag: 'sup' }]
  },
  renderHTML({ HTMLAttributes }) {
    return ['sup', HTMLAttributes, 0]
  },
  addCommands() {
    return {
      toggleSuperscript: () => ({ commands }) => commands.toggleMark(this.name),
      unsetSuperscript: () => ({ commands }) => commands.unsetMark(this.name),
    }
  },
})

export const FontSize = Extension.create({
  name: 'fontSize',
  addGlobalAttributes() {
    return [{
      types: ['textStyle'],
      attributes: {
        fontSize: {
          default: null,
          parseHTML: (el) => el.style.fontSize || null,
          renderHTML: (attrs) => (attrs.fontSize ? { style: `font-size: ${attrs.fontSize}` } : {}),
        },
      },
    }]
  },
})

export const Indent = Extension.create({
  name: 'indent',
  addGlobalAttributes() {
    return [{
      types: ['paragraph', 'heading'],
      attributes: {
        indent: {
          default: 0,
          parseHTML: (el) => Number(el.getAttribute('data-indent')) || 0,
          renderHTML: (attrs) => {
            const n = Number(attrs.indent) || 0
            if (!n) return {}
            return { 'data-indent': String(n), style: `padding-left: ${n * 24}px` }
          },
        },
      },
    }]
  },
  addCommands() {
    return {
      indentBlock: () => ({ commands, state }) => {
        if (commands.sinkListItem('listItem')) return true
        if (commands.sinkListItem('taskItem')) return true
        const name = state.selection.$from.parent.type.name
        if (name !== 'paragraph' && name !== 'heading') return false
        const cur = Number(state.selection.$from.parent.attrs.indent) || 0
        return commands.updateAttributes(name, { indent: Math.min(6, cur + 1) })
      },
      outdentBlock: () => ({ commands, state }) => {
        if (commands.liftListItem('listItem')) return true
        if (commands.liftListItem('taskItem')) return true
        const name = state.selection.$from.parent.type.name
        if (name !== 'paragraph' && name !== 'heading') return false
        const cur = Number(state.selection.$from.parent.attrs.indent) || 0
        return commands.updateAttributes(name, { indent: Math.max(0, cur - 1) })
      },
    }
  },
})

export const ScriptStep = Node.create({
  name: 'scriptStep',
  content: 'paragraph+',
  isolating: true,
  defining: true,
  addAttributes() {
    return {
      stepId: { default: '' },
      role: { default: '' },
      focus: { default: '' },
      duration: { default: '' },
      chapterId: { default: '' },
      chapterTitle: { default: '' },
    }
  },
  parseHTML() {
    return [{ tag: 'article[data-sdoc-script-step]' }]
  },
  renderHTML({ HTMLAttributes }) {
    return ['article', mergeAttributes(HTMLAttributes, { 'data-sdoc-script-step': '', class: 'sdoc-script-step' }), 0]
  },
  addNodeView() {
    return VueNodeViewRenderer(ScriptStepView)
  },
})

export const ScriptSheet = Node.create({
  name: 'scriptSheet',
  group: 'block',
  content: 'scriptStep+',
  isolating: true,
  defining: true,
  addAttributes() {
    return {
      scriptId: { default: '' },
      contentVersion: { default: 1 },
    }
  },
  parseHTML() {
    return [{ tag: 'section[data-sdoc-script-sheet]' }]
  },
  renderHTML({ HTMLAttributes }) {
    return ['section', mergeAttributes(HTMLAttributes, { 'data-sdoc-script-sheet': '', class: 'sdoc-script-sheet' }), 0]
  },
  addNodeView() {
    return VueNodeViewRenderer(ScriptSheetView)
  },
})

export function createSmartDocExtensions({ canEditProtected = false, awareness = null } = {}) {
  return [
    StarterKit.configure({
      heading: { levels: [1, 2, 3] },
      codeBlock: { HTMLAttributes: { class: 'sdoc-code' } },
    }),
    Underline,
    TextStyle,
    Color,
    FontSize,
    Superscript,
    Indent,
    awareness ? SdocAwareness.configure(awareness) : SdocAwareness,
    Highlight.configure({ multicolor: true }),
    Link.configure({ openOnClick: false, autolink: true }),
    TaskList,
    TaskItem.configure({ nested: true }),
    HighlightBlock,
    Image.configure({
      inline: false,
      allowBase64: false,
      HTMLAttributes: { class: 'sdoc-image' },
    }),
    Table.configure({
      resizable: true,
      HTMLAttributes: { class: 'sdoc-table' },
    }),
    TableRow,
    TableHeader,
    TableCell,
    Columns,
    Column,
    FileCard,
    CloudDoc,
    DateChip,
    MediaBlock,
    MindMap,
    FlowChart,
    ScriptSheet,
    ScriptStep,
    ProtectedRegion.configure({ canEditProtected }),
    Placeholder.configure({
      placeholder: ({ node }) => {
        if (node.type.name === 'heading') return '输入标题'
        if (node.type.name === 'column') return '分栏内容'
        return '输入正文或 “/” 插入内容'
      },
    }),
  ]
}

const SLASH_COMMANDS = {
  paragraph: (e) => e.chain().focus().setParagraph().run(),
  h1: (e) => e.chain().focus().toggleHeading({ level: 1 }).run(),
  h2: (e) => e.chain().focus().toggleHeading({ level: 2 }).run(),
  h3: (e) => e.chain().focus().toggleHeading({ level: 3 }).run(),
  bullet: (e) => e.chain().focus().toggleBulletList().run(),
  ordered: (e) => e.chain().focus().toggleOrderedList().run(),
  task: (e) => e.chain().focus().toggleTaskList().run(),
  quote: (e) => e.chain().focus().toggleBlockquote().run(),
  code: (e) => e.chain().focus().toggleCodeBlock().run(),
  hr: (e) => e.chain().focus().setHorizontalRule().run(),
  callout: (e) => e.chain().focus().insertContent({
    type: 'highlightBlock',
    attrs: { tone: 'note' },
    content: [{ type: 'paragraph' }],
  }).run(),
  table: (e) => e.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run(),
  cols2: (e) => e.chain().focus().insertContent(createColumnsJSON(2)).run(),
  cols3: (e) => e.chain().focus().insertContent(createColumnsJSON(3)).run(),
  protect: (e) => e.chain().focus().insertContent(createProtectedRegionJSON()).run(),
  mindmap: (e) => e.chain().focus().insertContent(createMindMapJSON()).run(),
  flow: (e) => e.chain().focus().insertContent(createFlowChartJSON()).run(),
}

export const SLASH_ITEMS = SLASH_CATALOG.map((item) => ({
  ...item,
  command: SLASH_COMMANDS[item.key],
}))
