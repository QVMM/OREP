import { Extension } from '@tiptap/core'
import { Plugin, PluginKey } from '@tiptap/pm/state'
import { Decoration, DecorationSet } from '@tiptap/pm/view'
import { dedupePeersByUser, resolvePeerCaret, shouldDrawRemoteCaret } from './sdocCollab.js'

const key = new PluginKey('sdocAwareness')
const AUTHOR_TYPES = new Set(['paragraph', 'heading', 'highlightBlock', 'blockquote', 'codeBlock'])

function sameId(a, b) {
  return a != null && b != null && String(a) === String(b)
}

function makeCaretEl(peer) {
  const color = peer.color || '#c43a12'
  const root = document.createElement('span')
  root.className = 'sdoc-remote-caret'
  root.contentEditable = 'false'
  root.style.setProperty('--sdoc-peer', color)
  root.style.cssText += 'position:relative;display:inline-block;width:0;height:1em;overflow:visible;vertical-align:text-bottom;pointer-events:none;'

  const bar = document.createElement('span')
  bar.className = 'sdoc-remote-caret__bar'
  bar.style.cssText = `position:absolute;left:0;top:0;width:2px;height:1.35em;background:${color};border-radius:1px;`

  const flag = document.createElement('span')
  flag.className = 'sdoc-remote-caret__flag'
  flag.textContent = peer.name || '协作者'
  flag.style.cssText = `position:absolute;left:0;top:-16px;padding:1px 6px;border-radius:4px;background:${color};color:#fff;font-size:10px;font-weight:700;line-height:16px;white-space:nowrap;z-index:8;`

  root.append(flag, bar)
  return root
}

function buildDecos(state, peers, selfSession, selfUserId, colorByPerson) {
  const decos = []
  for (const peer of dedupePeersByUser(peers)) {
    if (sameId(peer.sessionId, selfSession) || sameId(peer.userId, selfUserId)) continue
    const caret = resolvePeerCaret(state.doc, peer)
    if (!caret || !shouldDrawRemoteCaret(caret, state.selection)) continue
    const color = peer.color || '#c43a12'
    if (caret.to > caret.from) {
      decos.push(Decoration.inline(caret.from, caret.to, {
        class: 'sdoc-remote-sel',
        style: `background: color-mix(in srgb, ${color} 22%, transparent);`,
      }))
    }
    decos.push(Decoration.widget(caret.to, () => makeCaretEl(peer), {
      side: -1,
      key: `caret-${peer.sessionId}`,
      ignoreSelection: true,
      stopEvent: () => true,
    }))

    if (colorByPerson) {
      try {
        const $pos = state.doc.resolve(caret.from)
        for (let d = $pos.depth; d > 0; d -= 1) {
          const node = $pos.node(d)
          if (AUTHOR_TYPES.has(node.type.name)) {
            const start = $pos.before(d)
            decos.push(Decoration.node(start, start + node.nodeSize, {
              class: 'sdoc-peer-block',
              style: `--sdoc-peer:${color}`,
            }))
            break
          }
        }
      } catch {
        // ignore stale positions
      }
    }
  }
  return DecorationSet.create(state.doc, decos)
}

export const SdocAwareness = Extension.create({
  name: 'sdocAwareness',
  addStorage() {
    return { remote: false }
  },
  addOptions() {
    return {
      getPeers: () => [],
      getSelfSession: () => '',
      getColorByPerson: () => false,
      getUserId: () => '',
    }
  },
  addGlobalAttributes() {
    return [{
      types: [...AUTHOR_TYPES],
      attributes: {
        authorId: {
          default: null,
          parseHTML: (el) => el.getAttribute('data-author') || null,
          renderHTML: (attrs) => (attrs.authorId ? { 'data-author': String(attrs.authorId) } : {}),
        },
      },
    }]
  },
  addProseMirrorPlugins() {
    const ext = this
    return [
      new Plugin({
        key,
        state: {
          init: (_, state) => buildDecos(
            state,
            ext.options.getPeers(),
            ext.options.getSelfSession(),
            ext.options.getUserId(),
            ext.options.getColorByPerson(),
          ),
          apply(tr, old, _oldState, state) {
            // Only rebuild from peer locators when the room list changes.
            // Local typing must map existing widgets so 张's caret cannot
            // jump onto 李's insertion point on every keystroke.
            if (tr.getMeta(key)) {
              return buildDecos(
                state,
                ext.options.getPeers(),
                ext.options.getSelfSession(),
                ext.options.getUserId(),
                ext.options.getColorByPerson(),
              )
            }
            return old.map(tr.mapping, tr.doc)
          },
        },
        props: {
          decorations(state) {
            return key.getState(state)
          },
        },
        appendTransaction(transactions, _oldState, newState) {
          if (ext.editor?.storage?.sdocAwareness?.remote) return null
          if (transactions.some((tr) => tr.getMeta('sdoc-remote'))) return null
          if (!transactions.some((tr) => tr.docChanged)) return null
          const userId = String(ext.options.getUserId?.() || '')
          if (!userId) return null
          const $from = newState.selection.$from
          for (let d = $from.depth; d > 0; d -= 1) {
            const node = $from.node(d)
            if (!AUTHOR_TYPES.has(node.type.name)) continue
            if (String(node.attrs.authorId || '') === userId) return null
            const pos = $from.before(d)
            return newState.tr.setNodeMarkup(pos, undefined, { ...node.attrs, authorId: userId })
          }
          return null
        },
      }),
    ]
  },
})

export function refreshAwareness(editor) {
  if (!editor?.view) return
  editor.view.dispatch(editor.state.tr.setMeta(key, Date.now()))
}
