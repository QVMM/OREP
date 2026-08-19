<template>
  <div class="sdoc" :class="{ 'is-embedded': embedded, 'is-painting': paint.on, 'is-author-color': colorByPerson, 'is-toc-collapsed': !tocOpen }">
    <component :is="'style'">{{ authorColorCss }}</component>
    <header class="sdoc-top">
      <RouterLink v-if="!embedded" class="sdoc-top__back" :to="listPath" title="返回文档库">←</RouterLink>
      <input
        v-model="titleDraft"
        class="sdoc-top__title"
        maxlength="200"
        @change="commitTitle"
        @keydown.enter.prevent="commitTitle"
      />
      <span class="sdoc-top__save" :data-state="saveState">{{ saveLabel }}</span>
      <div v-if="splitHost" class="sdoc-split-btns" role="group" aria-label="窗口布局">
        <button type="button" class="sdoc-icon-btn" title="单屏" :class="{ 'is-on': splitHost.layout.value === 'single' }" @click="splitHost.setLayout('single')">
          <SdocIcon name="splitSingle" />
        </button>
        <button type="button" class="sdoc-icon-btn" title="左右分屏" :class="{ 'is-on': splitHost.layout.value === 'horizontal' }" @click="splitHost.setLayout('horizontal')">
          <SdocIcon name="splitCols" />
        </button>
        <button type="button" class="sdoc-icon-btn" title="上下分屏" :class="{ 'is-on': splitHost.layout.value === 'vertical' }" @click="splitHost.setLayout('vertical')">
          <SdocIcon name="splitRows" />
        </button>
      </div>
      <SdocPresenceBar
        :peers="collabPeers"
        :self-session="presenceSessionId"
        :color-by-person="colorByPerson"
        @toggle-color="colorByPerson = !colorByPerson"
        @focus-peer="focusPeer"
      />
      <div class="sdoc-top__export">
        <button type="button" class="sdoc-top__ver" :class="{ 'is-on': exportOpen }" @click="toggleExport">导出</button>
        <div v-if="exportOpen" class="sdoc-menu sdoc-top__export-menu">
          <button type="button" :disabled="exportBusy" @click="exportAs('docx')">Word</button>
          <button type="button" :disabled="exportBusy" @click="exportAs('pdf')">PDF</button>
          <button type="button" :disabled="exportBusy" @click="exportAs('md')">Markdown</button>
          <button type="button" :disabled="exportBusy" @click="exportAs('html')">HTML</button>
        </div>
      </div>
      <button
        type="button"
        class="sdoc-top__ask"
        @click="askXiaoQiFromSdoc"
      >问小启</button>
      <button type="button" class="sdoc-top__ver" :class="{ 'is-on': versionOpen }" @click="toggleVersions">版本</button>
    </header>

    <div v-if="conflict" class="sdoc-banner" role="alert">
      <span>文档已在其他处更新</span>
      <button type="button" @click="keepMine">保留我的</button>
      <button type="button" @click="useServer">用服务器的</button>
    </div>
    <div v-else-if="draftOffer" class="sdoc-banner" role="status">
      <span>发现未发出的本地草稿</span>
      <button type="button" @click="restoreDraft">恢复草稿</button>
      <button type="button" @click="discardDraft">丢弃</button>
    </div>

    <div class="sdoc-fmt" role="toolbar" aria-label="格式">
      <div class="sdoc-fmt__row">
      <button type="button" class="sdoc-icon-btn" title="撤销" :disabled="!editor?.can().undo()" @click="editor?.chain().focus().undo().run()">
        <SdocIcon name="undo" />
      </button>
      <button type="button" class="sdoc-icon-btn" title="重做" :disabled="!editor?.can().redo()" @click="editor?.chain().focus().redo().run()">
        <SdocIcon name="redo" />
      </button>
      <button
        type="button"
        class="sdoc-icon-btn"
        title="格式刷，双击可连续刷"
        :class="{ 'is-on': paint.on, 'is-locked': paint.locked }"
        @click="onPaintClick"
        @dblclick.prevent="lockPaint"
      >
        <SdocIcon name="painter" />
      </button>
      <span class="sdoc-fmt__sep" />
      <select class="sdoc-fmt__select" :value="currentBlock" title="段落样式" @change="applyBlock($event.target.value)">
        <option value="paragraph">正文</option>
        <option value="h1">标题 1</option>
        <option value="h2">标题 2</option>
        <option value="h3">标题 3</option>
      </select>
      <select class="sdoc-fmt__select sdoc-fmt__size" :value="currentFontSize" title="字号" @change="applyFontSize($event.target.value)">
        <option v-for="size in FONT_SIZES" :key="size" :value="size">{{ size }}</option>
      </select>
      <button type="button" class="sdoc-icon-btn" title="加粗" :class="{ 'is-on': editor?.isActive('bold') }" @click="editor?.chain().focus().toggleBold().run()">
        <SdocIcon name="bold" />
      </button>
      <button type="button" class="sdoc-icon-btn" title="斜体" :class="{ 'is-on': editor?.isActive('italic') }" @click="editor?.chain().focus().toggleItalic().run()">
        <SdocIcon name="italic" />
      </button>
      <button type="button" class="sdoc-icon-btn" title="下划线" :class="{ 'is-on': editor?.isActive('underline') }" @click="editor?.chain().focus().toggleUnderline().run()">
        <SdocIcon name="underline" />
      </button>
      <div class="sdoc-fmt__pop">
        <button
          type="button"
          class="sdoc-icon-btn sdoc-icon-btn--swatch"
          title="文字颜色"
          :class="{ 'is-on': colorOpen || !!currentColor }"
          :style="{ '--sdoc-swatch': currentColor || '#1d1d1f' }"
          @click="toggleColorPop"
        >
          <SdocIcon name="color" />
        </button>
        <div v-if="colorOpen" class="sdoc-swatches" role="menu">
          <button
            v-for="c in TEXT_COLORS"
            :key="c"
            type="button"
            class="sdoc-swatch"
            :class="{ 'is-on': currentColor === c }"
            :style="{ background: c }"
            :title="c"
            @click="applyColor(c)"
          />
          <button type="button" class="sdoc-swatch is-clear" title="默认颜色" @click="applyColor('')">A</button>
        </div>
      </div>
      <div class="sdoc-fmt__pop">
        <button
          type="button"
          class="sdoc-icon-btn sdoc-icon-btn--swatch"
          title="高亮"
          :class="{ 'is-on': highlightOpen || editor?.isActive('highlight') }"
          :style="{ '--sdoc-swatch': currentHighlight || '#fff3bf' }"
          @click="toggleHighlightPop"
        >
          <SdocIcon name="highlight" />
        </button>
        <div v-if="highlightOpen" class="sdoc-swatches" role="menu">
          <button
            v-for="c in HIGHLIGHT_COLORS"
            :key="c"
            type="button"
            class="sdoc-swatch"
            :class="{ 'is-on': currentHighlight === c }"
            :style="{ background: c }"
            :title="c"
            @click="applyHighlight(c)"
          />
          <button type="button" class="sdoc-swatch is-clear" title="清除高亮" @click="applyHighlight('')">×</button>
        </div>
      </div>
      <button type="button" class="sdoc-icon-btn" title="上标" :class="{ 'is-on': editor?.isActive('superscript') }" @click="editor?.chain().focus().toggleSuperscript().run()">
        <SdocIcon name="super" />
      </button>
      <button type="button" class="sdoc-icon-btn" title="行内代码" :class="{ 'is-on': editor?.isActive('code') }" @click="editor?.chain().focus().toggleCode().run()">
        <SdocIcon name="code" />
      </button>
      <span class="sdoc-fmt__sep" />
      <button type="button" class="sdoc-icon-btn" title="待办" :class="{ 'is-on': editor?.isActive('taskList') }" @click="editor?.chain().focus().toggleTaskList().run()">
        <SdocIcon name="task" />
      </button>
      <button type="button" class="sdoc-icon-btn" title="有序列表" :class="{ 'is-on': editor?.isActive('orderedList') }" @click="editor?.chain().focus().toggleOrderedList().run()">
        <SdocIcon name="ordered" />
      </button>
      <button type="button" class="sdoc-icon-btn" title="无序列表" :class="{ 'is-on': editor?.isActive('bulletList') }" @click="editor?.chain().focus().toggleBulletList().run()">
        <SdocIcon name="bullet" />
      </button>
      <button type="button" class="sdoc-icon-btn" title="减少缩进" @click="editor?.chain().focus().outdentBlock().run()">
        <SdocIcon name="outdent" />
      </button>
      <button type="button" class="sdoc-icon-btn" title="增加缩进" @click="editor?.chain().focus().indentBlock().run()">
        <SdocIcon name="indent" />
      </button>
      <template v-if="inTable">
        <span class="sdoc-fmt__sep" />
        <button type="button" title="左侧加列" @click="editor?.chain().focus().addColumnBefore().run()">+列←</button>
        <button type="button" title="右侧加列" @click="editor?.chain().focus().addColumnAfter().run()">+列→</button>
        <button type="button" title="上方加行" @click="editor?.chain().focus().addRowBefore().run()">+行↑</button>
        <button type="button" title="下方加行" @click="editor?.chain().focus().addRowAfter().run()">+行↓</button>
        <button type="button" title="删除列" @click="editor?.chain().focus().deleteColumn().run()">删列</button>
        <button type="button" title="删除行" @click="editor?.chain().focus().deleteRow().run()">删行</button>
        <button type="button" title="删除表格" @click="editor?.chain().focus().deleteTable().run()">删表</button>
      </template>
      <span class="sdoc-fmt__sep" />
      <button type="button" class="sdoc-icon-btn" title="查找" :class="{ 'is-on': findOpen }" @click="toggleFind">
        <SdocIcon name="search" />
      </button>
      <div v-if="findOpen" class="sdoc-find">
        <input
          ref="findInputRef"
          v-model="findQuery"
          type="search"
          placeholder="查找"
          @keydown.enter.prevent="findStep(1)"
          @keydown.esc.prevent="closeFind"
        />
        <span class="sdoc-find__count">{{ findHits.length ? `${findIndex + 1}/${findHits.length}` : '0/0' }}</span>
        <button type="button" class="sdoc-icon-btn" title="上一个" :disabled="!findHits.length" @click="findStep(-1)"><SdocIcon name="findPrev" /></button>
        <button type="button" class="sdoc-icon-btn" title="下一个" :disabled="!findHits.length" @click="findStep(1)"><SdocIcon name="findNext" /></button>
        <button type="button" class="sdoc-icon-btn" title="关闭查找" @click="closeFind"><SdocIcon name="close" /></button>
      </div>
      <div class="sdoc-fmt__insert">
        <button
          ref="insertBtnRef"
          type="button"
          class="sdoc-fmt__insert-btn"
          :aria-expanded="insertOpen"
          @click="toggleInsertMenu"
        >
          <SdocIcon name="plus" />
          插入
        </button>
      </div>
      </div>
    </div>
    <Teleport to="body">
      <div
        v-if="insertOpen"
        class="sdoc-menu"
        role="menu"
        :style="insertMenuStyle"
      >
        <div class="sdoc-menu__quick">
          <button v-for="item in insertQuickItems" :key="item.key" type="button" :title="item.label" @click="runSlash(item)">
            <span class="sdoc-menu__glyph" :data-tone="slashTone(item.key)"><SdocIcon :name="item.icon || 'paragraph'" /></span>
          </button>
        </div>
        <template v-for="group in insertMenuGroups" :key="group.name">
          <div class="sdoc-menu__group">{{ group.name === '基础' ? '通用' : group.name }}</div>
          <button v-for="item in group.items" :key="item.key" type="button" @click="runSlash(item)">
            <span class="sdoc-menu__glyph" :data-tone="slashTone(item.key)"><SdocIcon :name="item.icon || 'paragraph'" /></span>
            {{ item.label }}
          </button>
        </template>
      </div>
      <div
        v-if="emojiOpen"
        class="sdoc-emoji"
        :style="emojiStyle"
      >
        <button v-for="emo in emojis" :key="emo" type="button" @click="insertEmoji(emo)">{{ emo }}</button>
      </div>
    </Teleport>

    <div class="sdoc-body">
      <aside class="sdoc-side" :class="{ 'is-collapsed': !tocOpen }" aria-label="目录">
        <div class="sdoc-side__head">
          <div v-if="tocOpen" class="sdoc-side__tabs">
            <button type="button" class="is-on">目录</button>
            <button type="button" disabled>要点</button>
          </div>
          <button
            type="button"
            class="sdoc-side__toggle"
            :title="tocOpen ? '收起目录' : '展开目录'"
            :aria-expanded="tocOpen"
            @click="toggleToc"
          >
            <SdocIcon :name="tocOpen ? 'tocFold' : 'tocExpand'" />
          </button>
        </div>
        <template v-if="tocOpen">
          <p v-if="!headings.length" class="sdoc-side__hint">在文中使用「标题」样式即可生成目录</p>
          <nav v-else class="sdoc-toc">
            <button
              v-for="h in headings"
              :key="h.pos"
              type="button"
              :data-level="h.level"
              :class="{ 'is-active': h.pos === activeHeadingPos }"
              @click="scrollToHeading(h.pos)"
            >{{ h.text }}</button>
          </nav>
        </template>
      </aside>

      <main ref="paperRef" class="sdoc-paper">
        <input
          v-model="pageTitle"
          class="sdoc-paper__h1"
          placeholder="输入标题"
          maxlength="200"
          @change="commitTitleFromPage"
        />
        <div class="sdoc-meta">
          <span>{{ ownerLabel }}</span>
          <span>你在 {{ updatedLabel }} 更新</span>
        </div>

        <div v-if="loading" class="sdoc-empty">正在打开文档…</div>
        <div v-else-if="loadError" class="sdoc-empty is-error">{{ loadError }}</div>
        <editor-content v-else :editor="editor" class="sdoc-canvas" />
        <Teleport to="body">
          <div
            v-if="xiaoQiAsk && !xqInline"
            class="sdoc-selbar"
            :style="xiaoQiAsk.style"
            @mousedown="onSelBarMouseDown"
            @mouseup="onSelBarMouseUp"
          >
            <button type="button" class="sdoc-selbar__ask" @click="openInlineAsk">
              问问小启
              <span class="sdoc-selbar__play" aria-hidden="true">▶</span>
            </button>
            <span class="sdoc-fmt__sep" />
            <select class="sdoc-fmt__select" :value="currentBlock" title="段落样式" @change="applyBlock($event.target.value)">
              <option value="paragraph">正文</option>
              <option value="h1">标题 1</option>
              <option value="h2">标题 2</option>
              <option value="h3">标题 3</option>
            </select>
            <select class="sdoc-fmt__select sdoc-fmt__size" :value="currentFontSize" title="字号" @change="applyFontSize($event.target.value)">
              <option v-for="size in FONT_SIZES" :key="size" :value="size">{{ size }}</option>
            </select>
            <button type="button" class="sdoc-icon-btn" title="加粗" :class="{ 'is-on': editor?.isActive('bold') }" @click="editor?.chain().focus().toggleBold().run()">
              <SdocIcon name="bold" />
            </button>
            <button type="button" class="sdoc-icon-btn" title="斜体" :class="{ 'is-on': editor?.isActive('italic') }" @click="editor?.chain().focus().toggleItalic().run()">
              <SdocIcon name="italic" />
            </button>
            <button type="button" class="sdoc-icon-btn" title="下划线" :class="{ 'is-on': editor?.isActive('underline') }" @click="editor?.chain().focus().toggleUnderline().run()">
              <SdocIcon name="underline" />
            </button>
            <div class="sdoc-fmt__pop">
              <button
                type="button"
                class="sdoc-icon-btn sdoc-icon-btn--swatch"
                title="文字颜色"
                :class="{ 'is-on': colorOpen || !!currentColor }"
                :style="{ '--sdoc-swatch': currentColor || '#1d1d1f' }"
                @click="toggleColorPop"
              >
                <SdocIcon name="color" />
              </button>
              <div v-if="colorOpen" class="sdoc-swatches" role="menu">
                <button
                  v-for="c in TEXT_COLORS"
                  :key="c"
                  type="button"
                  class="sdoc-swatch"
                  :class="{ 'is-on': currentColor === c }"
                  :style="{ background: c }"
                  :title="c"
                  @click="applyColor(c)"
                />
                <button type="button" class="sdoc-swatch is-clear" title="默认颜色" @click="applyColor('')">A</button>
              </div>
            </div>
            <div class="sdoc-fmt__pop">
              <button
                type="button"
                class="sdoc-icon-btn sdoc-icon-btn--swatch"
                title="高亮"
                :class="{ 'is-on': highlightOpen || editor?.isActive('highlight') }"
                :style="{ '--sdoc-swatch': currentHighlight || '#fff3bf' }"
                @click="toggleHighlightPop"
              >
                <SdocIcon name="highlight" />
              </button>
              <div v-if="highlightOpen" class="sdoc-swatches" role="menu">
                <button
                  v-for="c in HIGHLIGHT_COLORS"
                  :key="c"
                  type="button"
                  class="sdoc-swatch"
                  :class="{ 'is-on': currentHighlight === c }"
                  :style="{ background: c }"
                  :title="c"
                  @click="applyHighlight(c)"
                />
                <button type="button" class="sdoc-swatch is-clear" title="清除高亮" @click="applyHighlight('')">×</button>
              </div>
            </div>
            <button type="button" class="sdoc-icon-btn" title="行内代码" :class="{ 'is-on': editor?.isActive('code') }" @click="editor?.chain().focus().toggleCode().run()">
              <SdocIcon name="code" />
            </button>
            <button type="button" class="sdoc-icon-btn" title="链接" :class="{ 'is-on': editor?.isActive('link') }" @click="toggleLink">
              <SdocIcon name="link" />
            </button>
            <button type="button" class="sdoc-icon-btn" title="上标" :class="{ 'is-on': editor?.isActive('superscript') }" @click="editor?.chain().focus().toggleSuperscript().run()">
              <SdocIcon name="super" />
            </button>
            <span class="sdoc-fmt__sep" />
            <button type="button" class="sdoc-icon-btn" title="有序列表" :class="{ 'is-on': editor?.isActive('orderedList') }" @click="editor?.chain().focus().toggleOrderedList().run()">
              <SdocIcon name="ordered" />
            </button>
            <button type="button" class="sdoc-icon-btn" title="无序列表" :class="{ 'is-on': editor?.isActive('bulletList') }" @click="editor?.chain().focus().toggleBulletList().run()">
              <SdocIcon name="bullet" />
            </button>
            <button
              type="button"
              class="sdoc-icon-btn"
              title="格式刷，双击可连续刷"
              :class="{ 'is-on': paint.on, 'is-locked': paint.locked }"
              @click="onPaintClick"
              @dblclick.prevent="lockPaint"
            >
              <SdocIcon name="painter" />
            </button>
          </div>
          <template v-if="xqInline">
            <div
              v-for="(r, i) in xqInline.rects"
              :key="`hl-${i}`"
              class="sdoc-ask-hl"
              :style="r"
            />
            <form
              class="sdoc-ask-inline"
              :style="xqInline.style"
              @mousedown.stop
              @submit.prevent="submitInlineAsk"
            >
              <input
                ref="xqInlineInput"
                v-model="xqInlineDraft"
                type="text"
                maxlength="500"
                placeholder="问问这段…"
                autocomplete="off"
                @keydown.esc.prevent="closeInlineAsk"
              />
              <button
                type="submit"
                class="sdoc-ask-inline__send"
                :disabled="!String(xqInlineDraft || '').trim()"
                aria-label="发送"
              >
                <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
                  <path fill="currentColor" d="M5.2 3.1v9.8L13 8z" />
                </svg>
              </button>
            </form>
          </template>
          <template v-if="xqPendingEdit">
            <div
              v-for="(r, i) in xqPendingEdit.rects"
              :key="`edit-hl-${i}`"
              class="sdoc-edit-hl"
              :style="r"
            />
            <div class="sdoc-edit-confirm" :style="xqPendingEdit.chipStyle">
              <button type="button" class="sdoc-edit-confirm__ok" @mousedown.prevent @click="confirmPendingEdit">确定修改</button>
              <button type="button" @mousedown.prevent @click="undoPendingEdit">撤回</button>
            </div>
          </template>
        </Teleport>

        <div v-if="showEmptyActions && editor" class="sdoc-quick">
          <button type="button" disabled title="即将支持">导入</button>
          <button type="button" disabled title="即将支持">模板</button>
        </div>

        <div v-if="slash.open" class="sdoc-slash" :style="slashStyle">
          <template v-for="group in slashFilteredGroups" :key="group.name">
            <div class="sdoc-slash__group">{{ group.name }}</div>
            <button
              v-for="item in group.items"
              :key="item.key"
              type="button"
              :class="{ 'is-active': slash.filtered[slash.index]?.key === item.key }"
              @mousedown.prevent="runSlash(item)"
            >
              <span class="sdoc-menu__glyph" :data-tone="slashTone(item.key)"><SdocIcon :name="item.icon || 'paragraph'" /></span>
              {{ item.label }}
            </button>
          </template>
          <p v-if="!slash.filtered.length" class="sdoc-slash__empty">无匹配项</p>
        </div>
      </main>
    </div>

    <SdocXiaoQiPanel
      v-if="xqOpen && xqCtx"
      :ctx="xqCtx"
      :messages="xqMessages"
      :draft="xqDraft"
      :busy="xqBusy"
      :status="xqStatus"
      :error="xqError"
      :preview="xqPreview"
      @close="closeXiaoQiPanel"
      @send="sendXiaoQi"
      @apply="applyXiaoQiPatch"
      @reject="rejectXiaoQiPatch"
      @confirm-proposal="confirmScoreProposal"
      @reject-proposal="rejectScoreProposal"
      @stop="stopXiaoQi"
      @update:draft="xqDraft = $event"
    />
    <aside v-if="versionOpen" class="sdoc-versions" aria-label="版本存档">
      <div class="sdoc-versions__head">
        <strong>版本</strong>
        <button type="button" @click="refreshVersions">刷新</button>
      </div>
      <div class="sdoc-versions__form">
        <input v-model="snapshotLabel" type="text" maxlength="80" placeholder="备注，如：提交前" />
        <button type="button" :disabled="snapshotting" @click="doSnapshot">{{ snapshotting ? '…' : '存档' }}</button>
      </div>
      <ul v-if="versions.length">
        <li v-for="v in versions" :key="v.id || v.versionNo">
          <div>
            <strong>v{{ v.versionNo }}</strong>
            <span>{{ v.sourceLabel || v.source }}</span>
            <small>{{ formatRel(v.createdAt) }}</small>
          </div>
          <button type="button" :disabled="restoring === v.versionNo" @click="doRestore(v)">
            {{ restoring === v.versionNo ? '…' : '恢复' }}
          </button>
        </li>
      </ul>
      <p v-else class="sdoc-versions__empty">{{ versionsLoading ? '加载中…' : '暂无版本' }}</p>
    </aside>

    <footer class="sdoc-foot">
      <span>{{ wordCount }} 个字</span>
    </footer>

    <input ref="imageInput" type="file" accept="image/*" hidden @change="onPickedFile('image', $event)">
    <input ref="fileInput" type="file" hidden @change="onPickedFile('file', $event)">
    <input ref="mediaInput" type="file" accept="video/*,audio/*" hidden @change="onPickedFile('media', $event)">
    <input ref="dateInput" type="date" hidden @change="onDatePicked">

    <Teleport to="body">
      <div v-if="cloudOpen" class="sdoc-modal" role="dialog" aria-modal="true" @click.self="cloudOpen = false">
        <div class="sdoc-dialog">
          <header>
            <h2>插入云文档</h2>
            <button type="button" class="sdoc-dialog__x" aria-label="关闭" @click="cloudOpen = false">×</button>
          </header>
          <input v-model="cloudKeyword" type="search" class="sdoc-dialog__search" placeholder="搜索标题" />
          <div v-if="cloudLoading" class="sdoc-dialog__empty">加载中…</div>
          <ul v-else-if="cloudDocs.length" class="sdoc-dialog__list">
            <li v-for="doc in cloudDocs" :key="doc.id">
              <button type="button" @click="insertCloudDoc(doc)">
                <strong>{{ doc.title }}</strong>
                <small>{{ cloudTypeLabel(doc) }} · {{ doc.scope || '个人' }}</small>
              </button>
            </li>
          </ul>
          <div v-else class="sdoc-dialog__empty">没有可插入的文档</div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, provide, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import request from '../../../utils/request'
import * as assistantApi from '../../../services/assistantClient'
import { applyAssistantStreamEvent } from '../../../modules/assistant-core/handleStreamEvent'
import { buildAskPrompt, clipScriptAround, extractSuggestedRewrite, formatScoreBrief } from './sdocRewrite.js'
import {
  buildScoreItemRewritePrompt,
  formatScoreReviseDiagnosis,
  isScoreReviseIntent,
} from '../../../modules/assistant-core/scriptScoreRevise.js'
import { extractScriptPatchFromReply } from '../../../modules/assistant-core/scriptStepContext.js'
import SdocXiaoQiPanel from './SdocXiaoQiPanel.vue'
import { Editor, EditorContent } from '@tiptap/vue-3'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createCloudDocJSON,
  createDateChipJSON,
  createFileCardJSON,
  createMediaBlockJSON,
  createSmartDocExtensions,
  EMOJI_ITEMS,
  groupSlashItems,
  SLASH_ITEMS,
} from './schema/smartDocExtensions'
import { downloadBlob, safeFileName } from './export/downloadBlob'
import { downloadSmartDocPdf } from './export/smartDocPdf'
import { downloadTextFile, smartDocToHtml, smartDocToMarkdown } from './export/smartDocExport'
import { useSdocHost } from './sdocHost'
import { useSdocSplit } from './sdocSplit'
import SdocIcon from './SdocIcon.vue'
import { SLASH_TONE } from './sdocIcons.js'
import SdocPresenceBar from './collab/SdocPresenceBar.vue'
import { refreshAwareness } from './collab/sdocAwareness.js'
import { mergePeerList, remoteLocatorsChanged, resolvePeerCaret, selectionContext, sdocUserColor } from './collab/sdocCollab.js'
import { decideRemoteApply, planSyncPayload } from './collab/sdocSync.js'
import fallbackWs from '../../../utils/websocket.js'
import './smart-doc.css'

const FONT_SIZES = ['12', '14', '16', '18', '20', '24', '28', '32']
const TEXT_COLORS = ['#1d1d1f', '#c43a12', '#c9382b', '#d97706', '#217346', '#2b579a', '#6d28d9', '#8e8e93']
const HIGHLIGHT_COLORS = ['#fff3bf', '#ffd6d6', '#d4edda', '#cce5ff', '#f3e8ff', '#ffe8cc']
const INSERT_QUICK_KEYS = ['paragraph', 'h1', 'h2', 'h3', 'bullet', 'ordered', 'task']

const props = defineProps({
  documentId: { type: [String, Number], default: '' },
  embedded: { type: Boolean, default: false },
})
const emit = defineEmits(['title', 'meta'])

const route = useRoute()
const host = useSdocHost()
const splitHost = useSdocSplit()
const emojis = EMOJI_ITEMS
const listPath = host.listPath || '/inspire-office'

const loading = ref(true)
const loadError = ref('')
const titleDraft = ref('未命名文档')
const pageTitle = ref('')
const ownerLabel = ref('创建')
const updatedLabel = ref('刚刚')
const saveState = ref('idle')
const insertOpen = ref(false)
const emojiOpen = ref(false)
const cloudOpen = ref(false)
const cloudLoading = ref(false)
const cloudKeyword = ref('')
const cloudAll = ref([])
const insertBtnRef = ref(null)
const paperRef = ref(null)
const imageInput = ref(null)
const fileInput = ref(null)
const mediaInput = ref(null)
const dateInput = ref(null)
const insertMenuStyle = ref({})
const emojiStyle = ref({})
const contentUpdatedAt = ref('')
const editor = ref(null)
const slash = ref({ open: false, query: '', index: 0, filtered: [], coords: null })
const inTable = ref(false)
const canEditProtected = ref(false)
const headings = ref([])
const activeHeadingPos = ref(null)
const versionOpen = ref(false)
const versions = ref([])
const versionsLoading = ref(false)
const snapshotLabel = ref('')
const snapshotting = ref(false)
const restoring = ref(null)
const conflict = ref(null)
const draftOffer = ref(false)
const exportOpen = ref(false)
const exportBusy = ref(false)
const paint = ref({ on: false, locked: false, marks: null })
const colorOpen = ref(false)
const highlightOpen = ref(false)
const findOpen = ref(false)
const findQuery = ref('')
const findHits = ref([])
const findIndex = ref(0)
const findInputRef = ref(null)
const colorByPerson = ref(false)
const collabPeers = ref([])
const TOC_KEY = 'inspire-sdoc-toc'
const tocOpen = ref(readTocOpen())
const scriptBinding = ref(null)
const xiaoQiAsk = ref(null)
const hasScriptSheet = ref(false)
const xqOpen = ref(false)
const xqCtx = ref(null)
const xqDraft = ref('')
const xqMessages = ref([])
const xqBusy = ref(false)
const xqStatus = ref('idle')
const xqError = ref('')
const xqInline = ref(null)
const xqInlineDraft = ref('')
const xqInlineInput = ref(null)
const xqPendingEdit = ref(null)
const xqBrief = ref(null)
const xqPreview = ref({ after: '', reason: '' })
const xqScoreBrief = ref(null)
const xqScoreQueue = ref([])
let xqAbort = null
let xqSessionId = null
let skipPersist = false
const isScriptWorkbench = computed(() => Boolean(scriptBinding.value || hasScriptSheet.value || route.query.from === 'script'))

const askXiaoQiBridge = { run: async () => {} }
provide('sdocAskXiaoQi', (step, pos) => {
  if (editor.value && typeof pos === 'number' && step?.nodeSize) {
    const from = pos + 1
    const to = pos + step.nodeSize - 1
    if (to > from) {
      try {
        editor.value.chain().setTextSelection({ from, to }).run()
      } catch {
        // ignore
      }
    }
  }
  return askXiaoQiBridge.run()
})

function readTocOpen() {
  try {
    const raw = window.localStorage.getItem(TOC_KEY)
    if (raw === '0') return false
    if (raw === '1') return true
  } catch {
    // ignore
  }
  return typeof window === 'undefined' || window.innerWidth > 960
}

function toggleToc() {
  tocOpen.value = !tocOpen.value
  try {
    window.localStorage.setItem(TOC_KEY, tocOpen.value ? '1' : '0')
  } catch {
    // ignore
  }
}
let paintApplying = false
let collabTimer = 0
let collabSub = null
let syncSub = null
let lastCollabSent = 0
let applyingRemote = false
let lastAckedDoc = null
let lastRev = -1
let localDirty = false
let syncing = false
let syncTimer = 0

const visibleSlashItems = computed(() => {
  if (canEditProtected.value) return SLASH_ITEMS
  return SLASH_ITEMS.filter((item) => item.key !== 'protect')
})
const slashGroups = computed(() => groupSlashItems(visibleSlashItems.value))
const insertQuickItems = computed(() => INSERT_QUICK_KEYS
  .map((key) => visibleSlashItems.value.find((item) => item.key === key))
  .filter(Boolean))
const insertMenuGroups = computed(() => groupSlashItems(
  visibleSlashItems.value.filter((item) => !INSERT_QUICK_KEYS.includes(item.key)),
))

function slashTone(key) {
  return SLASH_TONE[key] || 'ink'
}

function draftKey() {
  return `inspire-sdoc-draft:${activeId.value}`
}

const activeId = computed(() => String(props.documentId || route.params.id || ''))

let saveTimer = 0
let lastSavedJson = ''
const presenceSessionId = globalThis.crypto?.randomUUID?.()
  || `sdoc_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`
let presenceTimer = 0
let lastEditAt = 0

const saveLabel = computed(() => {
  if (saveState.value === 'saving') return '保存中…'
  if (saveState.value === 'error') return '保存失败'
  if (saveState.value === 'saved') return '已保存'
  return ''
})

const wordCount = computed(() => {
  const text = editor.value?.getText() || ''
  return text.replace(/\s+/g, '').length
})

const showEmptyActions = computed(() => {
  if (!editor.value) return false
  const text = (editor.value.getText() || '').trim()
  return text.length === 0
})

const currentBlock = computed(() => {
  const e = editor.value
  if (!e) return 'paragraph'
  if (e.isActive('heading', { level: 1 })) return 'h1'
  if (e.isActive('heading', { level: 2 })) return 'h2'
  if (e.isActive('heading', { level: 3 })) return 'h3'
  return 'paragraph'
})

const currentFontSize = computed(() => {
  const size = editor.value?.getAttributes('textStyle')?.fontSize || '16'
  return String(size).replace('px', '')
})

const currentColor = computed(() => editor.value?.getAttributes('textStyle')?.color || '')
const currentHighlight = computed(() => editor.value?.getAttributes('highlight')?.color || '')

const slashFilteredGroups = computed(() => groupSlashItems(slash.value.filtered))

const authorColorCss = computed(() => {
  const seen = new Map()
  const me = host.getUser?.()
  if (me?.id) seen.set(String(me.id), sdocUserColor(me.id))
  for (const peer of collabPeers.value) {
    if (peer?.userId) seen.set(String(peer.userId), peer.color || sdocUserColor(peer.userId))
  }
  return [...seen.entries()].map(([id, color]) => (
    `.sdoc.is-author-color .sdoc-prose [data-author="${id}"]{--sdoc-peer:${color};background:color-mix(in srgb, ${color} 12%, transparent);box-shadow:inset 3px 0 0 ${color};}`
  )).join('')
})

const slashStyle = computed(() => {
  const coords = slash.value.coords
  if (!coords) return { top: '220px', left: '48px' }
  return {
    top: `${Math.round(coords.top)}px`,
    left: `${Math.round(coords.left)}px`,
  }
})

const cloudDocs = computed(() => {
  const q = cloudKeyword.value.trim().toLowerCase()
  const self = String(activeId.value)
  return (cloudAll.value || []).filter((doc) => {
    if (String(doc.id) === self) return false
    if (q && !String(doc.title || '').toLowerCase().includes(q)) return false
    return true
  })
})

function refreshHeadings() {
  const list = []
  const e = editor.value
  if (!e) {
    headings.value = []
    activeHeadingPos.value = null
    return
  }
  e.state.doc.descendants((node, pos) => {
    if (node.type.name === 'heading') {
      list.push({
        pos,
        level: node.attrs.level || 1,
        text: node.textContent || '未命名标题',
      })
    }
  })
  headings.value = list
  const from = e.state.selection.from
  let current = null
  for (const h of list) {
    if (h.pos <= from) current = h.pos
  }
  activeHeadingPos.value = current
}

function toggleInsertMenu() {
  emojiOpen.value = false
  insertOpen.value = !insertOpen.value
  if (!insertOpen.value) return
  const rect = insertBtnRef.value?.getBoundingClientRect()
  if (!rect) return
  insertMenuStyle.value = {
    position: 'fixed',
    top: `${Math.round(rect.bottom + 6)}px`,
    left: `${Math.round(Math.max(8, rect.right - 260))}px`,
    zIndex: 4000,
  }
}

function applyFontSize(value) {
  const e = editor.value
  if (!e) return
  if (!value || value === '16') e.chain().focus().setMark('textStyle', { fontSize: null }).removeEmptyTextStyle().run()
  else e.chain().focus().setMark('textStyle', { fontSize: `${value}px` }).run()
}

function toggleColorPop() {
  highlightOpen.value = false
  colorOpen.value = !colorOpen.value
}

function toggleHighlightPop() {
  colorOpen.value = false
  highlightOpen.value = !highlightOpen.value
}

function applyColor(color) {
  const e = editor.value
  if (!e) return
  if (!color) e.chain().focus().unsetColor().run()
  else e.chain().focus().setColor(color).run()
  colorOpen.value = false
}

function applyHighlight(color) {
  const e = editor.value
  if (!e) return
  if (!color) e.chain().focus().unsetHighlight().run()
  else e.chain().focus().setHighlight({ color }).run()
  highlightOpen.value = false
}

function snapshotMarks(e) {
  const style = e.getAttributes('textStyle') || {}
  return {
    bold: e.isActive('bold'),
    italic: e.isActive('italic'),
    underline: e.isActive('underline'),
    code: e.isActive('code'),
    highlight: e.isActive('highlight') ? (e.getAttributes('highlight').color || true) : false,
    color: style.color || '',
    fontSize: style.fontSize || '',
    superscript: e.isActive('superscript'),
  }
}

function applyPaintMarks(marks) {
  const e = editor.value
  if (!e || !marks) return
  let chain = e.chain().focus()
    .unsetBold()
    .unsetItalic()
    .unsetUnderline()
    .unsetCode()
    .unsetHighlight()
    .unsetColor()
    .unsetSuperscript()
  if (marks.fontSize) chain = chain.setMark('textStyle', { fontSize: marks.fontSize })
  if (marks.bold) chain = chain.setBold()
  if (marks.italic) chain = chain.setItalic()
  if (marks.underline) chain = chain.setUnderline()
  if (marks.code) chain = chain.setCode()
  if (marks.superscript) chain = chain.toggleSuperscript()
  if (marks.color) chain = chain.setColor(marks.color)
  if (marks.highlight === true) chain = chain.setHighlight()
  else if (marks.highlight) chain = chain.setHighlight({ color: marks.highlight })
  chain.run()
}

function stopPaint() {
  paint.value = { on: false, locked: false, marks: null }
}

let paintClickTimer = 0
function startPaint(locked) {
  if (!editor.value) return
  paint.value = { on: true, locked: !!locked, marks: snapshotMarks(editor.value) }
}

function onPaintClick() {
  window.clearTimeout(paintClickTimer)
  paintClickTimer = window.setTimeout(() => {
    if (paint.value.on && !paint.value.locked) stopPaint()
    else if (!paint.value.on) startPaint(false)
  }, 220)
}

function lockPaint() {
  window.clearTimeout(paintClickTimer)
  startPaint(true)
}

function maybeApplyPaint() {
  if (!paint.value.on || !editor.value || paintApplying) return
  const { empty, from, to } = editor.value.state.selection
  if (empty || to - from < 1) return
  paintApplying = true
  try {
    applyPaintMarks(paint.value.marks)
  } finally {
    paintApplying = false
  }
  if (!paint.value.locked) stopPaint()
}

function collectFindHits(query) {
  const hits = []
  const q = String(query || '')
  if (!q || !editor.value) return hits
  editor.value.state.doc.descendants((node, pos) => {
    if (!node.isText) return
    const text = node.text || ''
    let from = 0
    while (from < text.length) {
      const i = text.indexOf(q, from)
      if (i < 0) break
      hits.push({ from: pos + i, to: pos + i + q.length })
      from = i + q.length
    }
  })
  return hits
}

function jumpFind(index) {
  const hit = findHits.value[index]
  if (!hit || !editor.value) return
  findIndex.value = index
  editor.value.chain().focus().setTextSelection(hit).scrollIntoView().run()
}

function refreshFind() {
  findHits.value = collectFindHits(findQuery.value)
  if (!findHits.value.length) {
    findIndex.value = 0
    return
  }
  jumpFind(Math.min(findIndex.value, findHits.value.length - 1))
}

function findStep(dir) {
  if (!findHits.value.length) {
    refreshFind()
    return
  }
  const next = (findIndex.value + dir + findHits.value.length) % findHits.value.length
  jumpFind(next)
}

function toggleFind() {
  findOpen.value = !findOpen.value
  if (!findOpen.value) return
  window.setTimeout(() => findInputRef.value?.focus(), 20)
  if (findQuery.value) refreshFind()
}

function closeFind() {
  findOpen.value = false
}

function applyBlock(value) {
  const e = editor.value
  if (!e) return
  if (value === 'h1') e.chain().focus().setHeading({ level: 1 }).run()
  else if (value === 'h2') e.chain().focus().setHeading({ level: 2 }).run()
  else if (value === 'h3') e.chain().focus().setHeading({ level: 3 }).run()
  else e.chain().focus().setParagraph().run()
}

function toggleLink() {
  const e = editor.value
  if (!e) return
  if (e.isActive('link')) {
    e.chain().focus().unsetLink().run()
    return
  }
  const prev = e.getAttributes('link')?.href || 'https://'
  const href = window.prompt('链接地址', prev)
  if (!href) return
  e.chain().focus().extendMarkRange('link').setLink({ href: href.trim() }).run()
}

function consumeSlashQuery() {
  if (!editor.value) return
  const { state } = editor.value
  const { $from } = state.selection
  const text = $from.parent.textContent || ''
  const slashAt = text.lastIndexOf('/')
  if (slashAt >= 0) {
    const from = $from.start() + slashAt
    const to = $from.pos
    editor.value.chain().focus().deleteRange({ from, to }).run()
  }
}

function runSlash(item) {
  insertOpen.value = false
  slash.value = { ...slash.value, open: false, query: '' }
  if (!editor.value) return
  consumeSlashQuery()
  if (item.action) {
    handleAction(item.action)
    return
  }
  item.command?.(editor.value)
}

function handleAction(action) {
  if (action === 'image') imageInput.value?.click()
  else if (action === 'file') fileInput.value?.click()
  else if (action === 'media') mediaInput.value?.click()
  else if (action === 'date') pickDate()
  else if (action === 'emoji') openEmoji()
  else if (action === 'cloud') openCloudPicker()
}

function openEmoji() {
  emojiOpen.value = true
  const rect = insertBtnRef.value?.getBoundingClientRect()
  emojiStyle.value = {
    position: 'fixed',
    top: `${Math.round((rect?.bottom || 120) + 6)}px`,
    left: `${Math.round(Math.max(8, (rect?.right || 240) - 280))}px`,
    zIndex: 4001,
  }
}

function insertEmoji(emo) {
  emojiOpen.value = false
  editor.value?.chain().focus().insertContent(emo).run()
}

function pickDate() {
  const el = dateInput.value
  if (!el) return
  el.value = new Date().toISOString().slice(0, 10)
  if (typeof el.showPicker === 'function') el.showPicker()
  else el.click()
}

function onDatePicked(event) {
  const value = event.target?.value
  if (!value || !editor.value) return
  editor.value.chain().focus().insertContent([
    createDateChipJSON(value),
    { type: 'text', text: ' ' },
  ]).run()
}

async function openCloudPicker() {
  cloudOpen.value = true
  cloudKeyword.value = ''
  cloudLoading.value = true
  try {
    cloudAll.value = await host.listDocuments({ scope: 'all' })
  } catch (err) {
    cloudAll.value = []
    ElMessage.error(err?.message || '加载文档失败')
  } finally {
    cloudLoading.value = false
  }
}

function cloudTypeLabel(doc) {
  if (doc.documentType === 'sdoc' || doc.ext === 'sdoc') return '智能文档'
  if (doc.documentType === 'sheet' || doc.documentType === 'cell') return '表格'
  if (doc.documentType === 'slide') return '演示'
  return '文档'
}

function insertCloudDoc(doc) {
  cloudOpen.value = false
  if (!editor.value) return
  editor.value.chain().focus().insertContent(createCloudDocJSON({
    ...doc,
    href: (host.documentHref || ((d) => `/inspire-office/sdoc/${d.id}`))(doc),
    documentType: doc.documentType === 'cell' ? 'sheet' : doc.documentType,
  })).run()
}

async function onPickedFile(kind, event) {
  const file = event.target?.files?.[0]
  if (event.target) event.target.value = ''
  if (!file) return
  await insertUploaded(kind, file)
}

async function insertUploaded(kind, file) {
  if (!editor.value) return
  const limits = { image: 8, file: 30, media: 80 }
  const maxMb = limits[kind] || 30
  if (file.size > maxMb * 1024 * 1024) {
    ElMessage.warning(`${kind === 'image' ? '图片' : kind === 'media' ? '音视频' : '文件'}请小于 ${maxMb}MB`)
    return
  }
  if (kind === 'image' && !file.type.startsWith('image/')) {
    ElMessage.warning('请选择图片文件')
    return
  }
  try {
    const uploaded = await host.uploadAsset(file, kind)
    if (kind === 'image') {
      editor.value.chain().focus().setImage({ src: uploaded.url, alt: uploaded.name }).run()
      return
    }
    if (kind === 'media') {
      const mediaKind = file.type.startsWith('audio/') ? 'audio' : 'video'
      editor.value.chain().focus().insertContent(createMediaBlockJSON({
        src: uploaded.url,
        kind: mediaKind,
        name: uploaded.name,
      })).run()
      return
    }
    editor.value.chain().focus().insertContent(createFileCardJSON({
      url: uploaded.url,
      name: uploaded.name,
      size: uploaded.size,
      mime: uploaded.type,
    })).run()
  } catch (err) {
    ElMessage.error(err?.message || '上传失败')
  }
}

function takeImageFiles(dataTransfer) {
  if (!dataTransfer) return []
  const files = []
  const list = dataTransfer.files?.length ? Array.from(dataTransfer.files) : []
  for (const file of list) {
    if (file.type.startsWith('image/')) files.push(file)
  }
  if (files.length) return files
  const items = dataTransfer.items ? Array.from(dataTransfer.items) : []
  for (const item of items) {
    if (item.kind === 'file' && item.type.startsWith('image/')) {
      const file = item.getAsFile()
      if (file) files.push(file)
    }
  }
  return files
}

function handleSlashKeys(event) {
  if (!slash.value.open) return false
  if (event.key === 'ArrowDown') {
    event.preventDefault()
    slash.value.index = Math.min(slash.value.filtered.length - 1, slash.value.index + 1)
    return true
  }
  if (event.key === 'ArrowUp') {
    event.preventDefault()
    slash.value.index = Math.max(0, slash.value.index - 1)
    return true
  }
  if (event.key === 'Enter') {
    const item = slash.value.filtered[slash.value.index]
    if (item) {
      event.preventDefault()
      runSlash(item)
      return true
    }
  }
  if (event.key === 'Escape') {
    slash.value.open = false
    return true
  }
  return false
}

function refreshSlash() {
  const e = editor.value
  if (!e) return
  const { $from } = e.state.selection
  if (!$from.parent.isTextblock) {
    slash.value.open = false
    return
  }
  const text = $from.parent.textBetween(0, $from.parentOffset, null, '\ufffc')
  const match = text.match(/(^|\s)\/([^\s]*)$/)
  if (!match) {
    slash.value.open = false
    return
  }
  const query = (match[2] || '').toLowerCase()
  const filtered = visibleSlashItems.value.filter((item) => item.label.toLowerCase().includes(query) || item.key.includes(query))
  let coords = null
  try {
    const viewCoords = e.view.coordsAtPos(e.state.selection.from)
    const paper = paperRef.value
    if (paper) {
      const rect = paper.getBoundingClientRect()
      coords = {
        top: viewCoords.bottom - rect.top + paper.scrollTop + 8,
        left: Math.max(8, viewCoords.left - rect.left),
      }
    }
  } catch {
    coords = null
  }
  slash.value = { open: true, query, index: 0, filtered, coords }
}

function refreshTableState() {
  inTable.value = !!editor.value?.isActive('table')
}

function writeDraft(content) {
  try {
    if (!activeId.value) return
    window.localStorage.setItem(draftKey(), JSON.stringify({
      at: Date.now(),
      content,
    }))
  } catch {
    // ignore quota
  }
}

function readDraft() {
  try {
    const raw = window.localStorage.getItem(draftKey())
    if (!raw) return null
    const data = JSON.parse(raw)
    return data?.content ? data : null
  } catch {
    return null
  }
}

function clearDraft() {
  try {
    window.localStorage.removeItem(draftKey())
  } catch {
    // ignore
  }
  draftOffer.value = false
}

function scheduleSave() {
  if (!editor.value) return
  saveState.value = 'idle'
  lastEditAt = Date.now()
  writeDraft(editor.value.getJSON())
  window.clearTimeout(saveTimer)
  saveTimer = window.setTimeout(flushSave, 1000)
}

async function flushSave() {
  if (!editor.value) return
  if (host.syncCollab) {
    await flushSync()
    saveState.value = saveState.value === 'error' ? 'error' : 'saved'
    await syncScriptFromSdoc()
    return
  }
  const json = JSON.stringify(editor.value.getJSON())
  if (json === lastSavedJson) {
    saveState.value = 'saved'
    return
  }
  const id = activeId.value
  if (!id) return
  saveState.value = 'saving'
  try {
    const data = await host.saveSmartDoc(id, { content: editor.value.getJSON(), updatedAt: contentUpdatedAt.value })
    lastSavedJson = json
    contentUpdatedAt.value = data?.contentUpdatedAt || data?.updatedAt || contentUpdatedAt.value
    if (data?.updatedAt) updatedLabel.value = formatRel(data.updatedAt)
    saveState.value = 'saved'
    conflict.value = null
    clearDraft()
    await syncScriptFromSdoc()
  } catch (err) {
    saveState.value = 'error'
    if (err?.httpStatus === 409 || err?.response?.status === 409 || /其他处更新/.test(err?.message || '')) {
      conflict.value = { mine: editor.value.getJSON() }
    }
  }
}

async function keepMine() {
  if (!conflict.value?.mine || !editor.value) return
  try {
    const data = await host.fetchSmartDoc(activeId.value)
    contentUpdatedAt.value = data?.contentUpdatedAt || data?.updatedAt || ''
    editor.value.commands.setContent(conflict.value.mine)
    conflict.value = null
    await flushSave()
  } catch (err) {
    ElMessage.error(err?.message || '无法保留本地版本')
  }
}

async function useServer() {
  conflict.value = null
  clearDraft()
  await load()
}

function restoreDraft() {
  const draft = readDraft()
  if (!draft?.content || !editor.value) return
  editor.value.commands.setContent(draft.content)
  draftOffer.value = false
  scheduleSave()
}

function discardDraft() {
  clearDraft()
}

async function commitTitle() {
  const id = activeId.value
  const next = titleDraft.value.trim() || '未命名文档'
  titleDraft.value = next
  pageTitle.value = next === '未命名文档' ? pageTitle.value : next
  try {
    await host.renameDocument(id, next)
    emit('title', next)
    emit('meta', { title: next, ext: 'sdoc', documentKind: 'sdoc' })
  } catch {
    ElMessage.error('标题保存失败')
  }
}

function commitTitleFromPage() {
  titleDraft.value = pageTitle.value.trim() || '未命名文档'
  pageTitle.value = titleDraft.value
  commitTitle()
}

function formatRel(value) {
  if (!value) return '刚刚'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return '刚刚'
  const sameDay = new Date().toDateString() === d.toDateString()
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  return sameDay ? `今天 ${hh}:${mm}` : `${d.getMonth() + 1}/${d.getDate()} ${hh}:${mm}`
}

function scrollToHeading(pos) {
  const e = editor.value
  if (!e || pos == null) return
  try {
    const dom = e.view.nodeDOM(pos)
    const el = dom instanceof HTMLElement ? dom : dom?.parentElement
    el?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    e.chain().focus(pos + 1).run()
    activeHeadingPos.value = pos
  } catch {
    // ignore
  }
}

function toggleExport() {
  exportOpen.value = !exportOpen.value
  versionOpen.value = false
}

function exportErrorMessage(err) {
  const status = err?.httpStatus || err?.response?.status
  const raw = String(err?.message || '')
  if (status === 502 || status === 504 || /502|504|Outdated Optimize/.test(raw)) {
    return '导出组件还在加载，请刷新页面后再试（不必等后台接口）'
  }
  return raw || '导出失败'
}

async function exportAs(kind) {
  exportOpen.value = false
  if (!editor.value || exportBusy.value) return
  const title = titleDraft.value || '未命名文档'
  const json = editor.value.getJSON()
  exportBusy.value = true
  try {
    if (kind === 'docx') {
      ElMessage.info('正在生成 Word…')
      const { smartDocToDocxBlob } = await import('./export/smartDocDocx.js')
      const blob = await smartDocToDocxBlob(json, { title })
      if (!blob || blob.size < 200) throw new Error('生成的 Word 是空文件')
      downloadBlob(safeFileName(title, 'docx'), blob)
      ElMessage.success('已导出 Word')
      return
    }
    if (kind === 'pdf') {
      ElMessage.info('正在生成 PDF…')
      await downloadSmartDocPdf(json, { title })
      ElMessage.success('已导出 PDF')
      return
    }
    if (kind === 'html') {
      downloadTextFile(safeFileName(title, 'html'), smartDocToHtml(json, { title }), 'text/html;charset=utf-8')
      return
    }
    downloadTextFile(safeFileName(title, 'md'), smartDocToMarkdown(json, { title }), 'text/markdown;charset=utf-8')
  } catch (err) {
    if (!err?.alreadyToasted) ElMessage.error(exportErrorMessage(err))
  } finally {
    exportBusy.value = false
  }
}

async function toggleVersions() {
  versionOpen.value = !versionOpen.value
  if (versionOpen.value) await refreshVersions()
}

async function refreshVersions() {
  if (!activeId.value) return
  versionsLoading.value = true
  try {
    versions.value = await host.listVersions(activeId.value)
  } catch (err) {
    ElMessage.error(err?.message || '加载版本失败')
  } finally {
    versionsLoading.value = false
  }
}

async function doSnapshot() {
  if (!activeId.value) return
  snapshotting.value = true
  try {
    await flushSave()
    await host.createSnapshot(activeId.value, snapshotLabel.value || undefined)
    snapshotLabel.value = ''
    ElMessage.success('已存档')
    await refreshVersions()
  } catch (err) {
    ElMessage.error(err?.message || '存档失败')
  } finally {
    snapshotting.value = false
  }
}

async function doRestore(v) {
  if (!activeId.value) return
  try {
    await ElMessageBox.confirm(
      `将当前文档恢复为 v${v.versionNo}？会生成新版本。`,
      '恢复版本',
      { type: 'warning', confirmButtonText: '恢复', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  restoring.value = v.versionNo
  try {
    await host.restoreVersion(activeId.value, v.versionNo)
    ElMessage.success(`已恢复至 v${v.versionNo}`)
    conflict.value = null
    clearDraft()
    await load()
    await refreshVersions()
  } catch (err) {
    ElMessage.error(err?.message || '恢复失败')
  } finally {
    restoring.value = null
  }
}

function scheduleSync() {
  if (applyingRemote || !host.syncCollab) return
  localDirty = true
  window.clearTimeout(syncTimer)
  syncTimer = window.setTimeout(() => { flushSync().catch(() => {}) }, 180)
}

function markAcked(doc, rev, updatedAt) {
  if (doc) {
    lastAckedDoc = doc
    lastSavedJson = JSON.stringify(doc)
  }
  if (Number.isFinite(Number(rev))) lastRev = Number(rev)
  if (updatedAt) contentUpdatedAt.value = updatedAt
  saveState.value = 'saved'
}

async function flushSync() {
  if (applyingRemote || syncing || !host.syncCollab || !editor.value || !activeId.value) return
  const next = editor.value.getJSON()
  const payload = planSyncPayload(lastAckedDoc, next)
  if (!payload) {
    localDirty = false
    return
  }
  syncing = true
  try {
    const data = await host.syncCollab(activeId.value, {
      sessionId: presenceSessionId,
      ...payload,
    })
    if (Array.isArray(data?.content) || data?.rev != null) {
      markAcked(next, data?.rev, data?.contentUpdatedAt)
      const still = editor.value.getJSON()
      localDirty = !planSyncPayload(next, still) ? false : true
      if (localDirty) scheduleSync()
    }
  } catch {
    localDirty = true
  } finally {
    syncing = false
  }
}

function applyRemoteSync(msg) {
  if (!msg || !editor.value) return
  const local = editor.value.getJSON()
  const decision = decideRemoteApply({
    incomingRev: msg.rev,
    lastRev,
    incomingSession: msg.sessionId,
    selfSession: presenceSessionId,
    localDirty,
    incomingContent: msg.content,
    localContent: local.content,
  })
  if (decision === 'skip') return
  if (decision === 'ack') {
    markAcked(localDirty ? lastAckedDoc : local, msg.rev, msg.contentUpdatedAt)
    if (!localDirty) localDirty = false
    return
  }
  if (!Array.isArray(msg.content)) return
  const loc = selectionContext(editor.value)
  applyingRemote = true
  if (editor.value.storage?.sdocAwareness) editor.value.storage.sdocAwareness.remote = true
  try {
    editor.value.commands.setContent({ type: 'doc', content: msg.content }, { emitUpdate: false })
    const caret = resolvePeerCaret(editor.value.state.doc, loc)
    if (caret) editor.value.commands.setTextSelection(caret.to)
    markAcked(editor.value.getJSON(), msg.rev, msg.contentUpdatedAt)
    localDirty = false
    refreshHeadings()
    refreshAwareness(editor.value)
  } finally {
    if (editor.value.storage?.sdocAwareness) editor.value.storage.sdocAwareness.remote = false
    applyingRemote = false
  }
}

function applyPeerList(list) {
  const merged = mergePeerList(collabPeers.value, Array.isArray(list) ? list : [])
  const changed = remoteLocatorsChanged(presenceSessionId, collabPeers.value, merged)
  collabPeers.value = merged
  if (changed) refreshAwareness(editor.value)
}

function collabBus() {
  return {
    subscribe: host.subscribeCollab || ((topic, cb) => fallbackWs.subscribe(topic, cb)),
    unsubscribe: host.unsubscribeCollab || ((token) => fallbackWs.unsubscribe(token)),
    connect: host.connectCollab || (() => fallbackWs.connect()),
  }
}

async function startCollab() {
  stopCollab()
  lastRev = -1
  localDirty = false
  if (!host.joinCollab || !activeId.value) return
  try {
    const data = await host.joinCollab(activeId.value, presenceSessionId)
    applyPeerList(data?.peers)
  } catch {
    // ignore
  }
  try {
    const bus = collabBus()
    collabSub = bus.subscribe(`/topic/sdoc/${activeId.value}/presence`, (msg) => {
      if (String(msg?.documentId) === String(activeId.value)) applyPeerList(msg.peers)
    })
    const role = String(host.getRole?.() || '').toUpperCase()
    const canLiveSync = ['TEACHER', 'SCHOOL_ADMIN', 'ADMIN'].includes(role)
    if (canLiveSync) {
      syncSub = bus.subscribe(`/topic/sdoc/${activeId.value}/sync`, (msg) => {
        if (String(msg?.documentId) === String(activeId.value)) applyRemoteSync(msg)
      })
    }
    bus.connect()
  } catch {
    // ignore
  }
  flushCollab(true)
  collabTimer = window.setInterval(() => flushCollab(false), 600)
}

async function pollRemoteSnapshot() {
  if (!host.fetchCollabSnapshot || !editor.value || !activeId.value || applyingRemote) return
  try {
    const data = await host.fetchCollabSnapshot(activeId.value)
    if (!data || !Array.isArray(data.content)) return
    applyRemoteSync({
      documentId: activeId.value,
      sessionId: data.sessionId || '__poll__',
      content: data.content,
      contentUpdatedAt: data.contentUpdatedAt,
      rev: data.rev,
    })
  } catch {
    // ignore
  }
}

async function flushCollab(force = false) {
  if (applyingRemote || !editor.value || !activeId.value) return
  const now = Date.now()
  if (host.reportCollabState && (force || now - lastCollabSent >= 180)) {
    lastCollabSent = now
    const ctx = selectionContext(editor.value)
    try {
      const data = await host.reportCollabState(activeId.value, {
        sessionId: presenceSessionId,
        ...ctx,
        editing: lastEditAt > 0 && now - lastEditAt < 90000,
      })
      if (data?.peers) applyPeerList(data.peers)
    } catch {
      // ignore
    }
  }
  flushSync().catch(() => {})
  pollRemoteSnapshot().catch(() => {})
}

function stopCollab() {
  if (collabTimer) {
    window.clearInterval(collabTimer)
    collabTimer = 0
  }
  window.clearTimeout(syncTimer)
  const bus = collabBus()
  if (collabSub) {
    bus.unsubscribe(collabSub)
    collabSub = null
  }
  if (syncSub) {
    bus.unsubscribe(syncSub)
    syncSub = null
  }
  if (host.leaveCollab && activeId.value) {
    host.leaveCollab(activeId.value, presenceSessionId).catch(() => {})
  }
}

function focusPeer(peer) {
  if (!editor.value || !peer) return
  const caret = resolvePeerCaret(editor.value.state.doc, peer)
  if (!caret) return
  try {
    editor.value.chain().focus().setTextSelection(caret.to).scrollIntoView().run()
  } catch {
    // ignore
  }
}

function refreshScriptSheetFlag() {
  let found = false
  editor.value?.state.doc.descendants((node) => {
    if (node.type?.name === 'scriptStep' || node.type?.name === 'scriptSheet') {
      found = true
      return false
    }
    return true
  })
  hasScriptSheet.value = found
}

async function loadScriptBinding(documentId) {
  try {
    const res = await request.post(`/api/script/from-sdoc/${documentId}/ensure`, {}, { silentError: true })
    const data = res?.data || res
    if (data?.id || data?.scriptId) {
      scriptBinding.value = data
    }
    if (data?.contentChanged && data.content && editor.value) {
      let json = data.content
      if (typeof json === 'string') {
        try { json = JSON.parse(json) } catch { json = null }
      }
      if (json) {
        editor.value.commands.setContent(sanitizeDocJson(json), { emitUpdate: false })
        lastAckedDoc = editor.value.getJSON()
        lastSavedJson = JSON.stringify(lastAckedDoc)
      }
    }
  } catch {
    // 打开普通文档失败不挡编辑
  }
}

async function syncScriptFromSdoc() {
  const scriptId = scriptBinding.value?.id
  if (!scriptId) return
  try {
    const res = await request.post(`/api/script/${scriptId}/sync-from-sdoc`, {}, { silentError: true })
    if (res?.data?.contentVersion != null) {
      scriptBinding.value = { ...scriptBinding.value, contentVersion: res.data.contentVersion }
    }
  } catch {
    // ignore
  }
}

function selectionClientRects(view, from, to) {
  try {
    const a = view.domAtPos(from)
    const b = view.domAtPos(to)
    const range = document.createRange()
    range.setStart(a.node, a.offset)
    range.setEnd(b.node, b.offset)
    return [...range.getClientRects()]
      .filter((r) => r.width > 1 && r.height > 1)
      .map((r) => ({
        top: `${r.top}px`,
        left: `${r.left}px`,
        width: `${r.width}px`,
        height: `${r.height}px`,
      }))
  } catch {
    return []
  }
}

function selectionBox(view, from, to) {
  const start = view.coordsAtPos(from)
  const end = view.coordsAtPos(Math.max(from, to - 1))
  const width = Math.min(Math.max(end.right - start.left, 360), Math.min(560, window.innerWidth - 32))
  const left = Math.min(Math.max(12, start.left), window.innerWidth - width - 16)
  const above = start.top - 56
  const top = above >= 64 ? above : end.bottom + 8
  return {
    style: {
      top: `${top}px`,
      left: `${left}px`,
      width: `${width}px`,
    },
    rects: selectionClientRects(view, from, to),
  }
}

let pointerSelecting = false
let selBarHideTimer = 0
const selBarPinned = ref(false)

function clearSelBarHide() {
  if (!selBarHideTimer) return
  window.clearTimeout(selBarHideTimer)
  selBarHideTimer = 0
}

function hideSelBarSoon() {
  if (selBarPinned.value || xqInline.value) return
  clearSelBarHide()
  selBarHideTimer = window.setTimeout(() => {
    selBarHideTimer = 0
    if (!selBarPinned.value && !xqInline.value) xiaoQiAsk.value = null
  }, 180)
}

function selectionBarStyle(view, from, to) {
  const start = view.coordsAtPos(from)
  const end = view.coordsAtPos(Math.max(from, Math.min(to, view.state.doc.content.size) - 1))
  const topEdge = Math.min(start.top, end.top)
  const bottomEdge = Math.max(start.bottom, end.bottom)
  const leftEdge = Math.min(start.left, end.left)
  const left = Math.min(Math.max(12, leftEdge), Math.max(12, window.innerWidth - 320))
  const above = topEdge - 48
  const top = above >= 64 ? above : bottomEdge + 8
  return {
    top: `${Math.round(top)}px`,
    left: `${Math.round(left)}px`,
  }
}

function updateXiaoQiAsk(current, { fromPointerUp = false } = {}) {
  if (xqInline.value) return
  if (!current) {
    hideSelBarSoon()
    return
  }
  const { from, to, empty } = current.state.selection
  const selection = empty || to <= from
    ? ''
    : current.state.doc.textBetween(from, to, '\n').trim()
  if (!selection) {
    hideSelBarSoon()
    return
  }
  if (pointerSelecting && !fromPointerUp && !xiaoQiAsk.value) return
  clearSelBarHide()
  if (xqOpen.value && xqCtx.value) {
    const ask = resolveAskTarget()
    if (ask?.selection) {
      xqCtx.value = {
        ...xqCtx.value,
        selection: ask.selection,
        from: ask.from,
        to: ask.to,
        speaker: ask.speaker || '',
        nearby: ask.nearby || { prev: '', next: '' },
      }
    }
  }
  let style
  try {
    style = selectionBarStyle(current.view, from, to)
  } catch {
    hideSelBarSoon()
    return
  }
  xiaoQiAsk.value = { selection, style, from, to }
}

function onSelBarMouseDown(event) {
  selBarPinned.value = true
  clearSelBarHide()
  if (event.target.closest('select, input, textarea')) return
  event.preventDefault()
}

function onSelBarMouseUp() {
  window.setTimeout(() => {
    selBarPinned.value = false
  }, 0)
}

function onEditorPointerUp() {
  if (!pointerSelecting) {
    if (editor.value) updateXiaoQiAsk(editor.value, { fromPointerUp: true })
    return
  }
  pointerSelecting = false
  if (editor.value) updateXiaoQiAsk(editor.value, { fromPointerUp: true })
}

function repositionAskChrome() {
  if (xqPendingEdit.value && editor.value) {
    const { from, to } = xqPendingEdit.value
    try {
      xqPendingEdit.value = { ...xqPendingEdit.value, ...pendingEditChrome(from, to) }
    } catch {
      // ignore
    }
  }
  if (xqInline.value && editor.value) {
    const { from, to } = xqInline.value
    try {
      const box = selectionBox(editor.value.view, from, to)
      xqInline.value = { ...xqInline.value, ...box }
    } catch {
      // ignore
    }
    return
  }
  if (xiaoQiAsk.value && editor.value) updateXiaoQiAsk(editor.value)
}

function inferSpeaker(text) {
  const m = String(text || '').match(/^(.{1,16}?)[：:]\s*/)
  return m ? m[1].trim() : ''
}

function paragraphRangeAt($pos) {
  for (let d = $pos.depth; d > 0; d -= 1) {
    const node = $pos.node(d)
    if (node.type.name === 'paragraph') {
      const pos = $pos.before(d)
      return { node, pos, from: pos + 1, to: pos + node.nodeSize - 1 }
    }
  }
  return null
}

function nearbyParagraphs(doc, from) {
  const chunks = []
  doc.descendants((node, pos) => {
    if (node.type.name !== 'paragraph') return true
    const text = node.textContent.trim()
    if (text) chunks.push({ from: pos, text })
    return true
  })
  const idx = chunks.findIndex((c) => c.from <= from && from <= c.from + c.text.length + 8)
  const at = idx < 0 ? chunks.length - 1 : idx
  return {
    prev: at > 0 ? chunks[at - 1].text : '',
    next: at >= 0 && at < chunks.length - 1 ? chunks[at + 1].text : '',
  }
}

function resolveAskTarget() {
  const current = editor.value
  if (!current) return null
  const sel = current.state.selection
  if (!sel.empty && sel.to > sel.from) {
    const text = current.state.doc.textBetween(sel.from, sel.to, '\n').trim()
    if (text) {
      const para = paragraphRangeAt(sel.$from)
      const around = nearbyParagraphs(current.state.doc, sel.from)
      return {
        from: sel.from,
        to: sel.to,
        selection: text,
        speaker: inferSpeaker(text) || inferSpeaker(para?.node?.textContent || ''),
        nearby: around,
      }
    }
  }
  const para = paragraphRangeAt(sel.$from)
  if (para && para.node.textContent.trim()) {
    return {
      from: para.from,
      to: para.to,
      selection: para.node.textContent.trim(),
      speaker: inferSpeaker(para.node.textContent),
      nearby: nearbyParagraphs(current.state.doc, para.from),
    }
  }
  return null
}

function buildAskContext(ask, binding) {
  return {
    scriptId: binding?.id || binding?.scriptId,
    scriptTitle: binding?.title || titleDraft.value,
    contentVersion: binding?.contentVersion || 1,
    speaker: ask.speaker || '',
    selection: ask.selection,
    from: ask.from,
    to: ask.to,
    nearby: ask.nearby || { prev: '', next: '' },
  }
}

function closeXiaoQiPanel() {
  xqAbort?.abort()
  xqAbort = null
  xqOpen.value = false
  xqBusy.value = false
  closeInlineAsk()
}

function stopXiaoQi() {
  xqAbort?.abort()
  xqAbort = null
  xqBusy.value = false
  const last = xqMessages.value[xqMessages.value.length - 1]
  if (last?.role === 'assistant' && last.status === 'streaming') {
    last.status = 'cancelled'
    last.phase = 'done'
  }
  xqStatus.value = String(last?.contentText || '').trim() ? 'ready' : 'idle'
}

function findTextRange(text) {
  const current = editor.value
  const needle = String(text || '')
  if (!current || !needle) return null
  let found = null
  current.state.doc.descendants((node, pos) => {
    if (found || !node.isText || !node.text) return true
    const i = node.text.indexOf(needle)
    if (i >= 0) found = { from: pos + i, to: pos + i + needle.length }
    return true
  })
  return found
}

function applyRangeText(from, to, after, persist = true) {
  if (!editor.value) return false
  const size = editor.value.state.doc.content.size
  let a = from
  let b = to
  if (a == null || b == null || a < 1 || b > size || a >= b) return false
  const next = String(after || '')
  skipPersist = !persist
  try {
    editor.value.chain().focus().insertContentAt({ from: a, to: b }, next).run()
  } finally {
    queueMicrotask(() => { skipPersist = false })
  }
  if (persist) scheduleSave()
  return true
}

function lastAssistantRewrite() {
  const last = [...xqMessages.value].reverse().find((m) => m.role === 'assistant')
  if (!last) return { after: '', reason: '' }
  return extractSuggestedRewrite(last.contentText || last.text, xqCtx.value?.selection)
}

function keepSpeaker(original, next) {
  const speaker = inferSpeaker(original)
  if (!speaker) return next
  if (next.startsWith(speaker)) return next
  const stripped = next.replace(/^.{1,16}[：:]\s*/, '')
  return `${speaker}：${stripped}`
}

async function loadRewriteBrief() {
  if (xqBrief.value) return xqBrief.value
  let scoreText = ''
  const projectBits = [titleDraft.value].filter((x) => x && x !== '未命名文档')
  try {
    const res = await request.get('/api/home/dashboard', { silentError: true })
    const data = res?.data || res
    scoreText = formatScoreBrief(data?.latestScore || {})
    const team = data?.team || {}
    const camp = data?.camp || {}
    for (const bit of [team.name, team.teamName, camp.projectName, team.projectDescription, camp.teamName]) {
      if (bit && !projectBits.includes(bit)) projectBits.push(bit)
    }
  } catch {
    scoreText = ''
  }
  xqBrief.value = {
    scoreText,
    projectText: projectBits.join(' · '),
  }
  return xqBrief.value
}

function pendingEditChrome(from, to) {
  if (!editor.value) return { rects: [], chipStyle: {} }
  const view = editor.value.view
  const rects = selectionClientRects(view, from, to)
  const box = selectionBox(view, from, to)
  return {
    rects,
    chipStyle: {
      top: `${Math.min(window.innerHeight - 56, parseFloat(box.style.top) + 52)}px`,
      left: box.style.left,
    },
  }
}

async function ensureXqSession() {
  if (xqSessionId) return xqSessionId
  const res = await assistantApi.createSession({
    title: `改稿 · ${titleDraft.value || '智能文档'}`,
    folderSlug: 'script',
    contextJson: xqCtx.value,
  })
  xqSessionId = res?.data?.id || res?.id
  return xqSessionId
}

async function sendXiaoQi(text) {
  const hint = String(text || xqDraft.value || '').trim()
  xqDraft.value = ''
  if (!xqCtx.value || !hint || xqBusy.value) return
  xqMessages.value.push({
    _localId: `u-${Date.now()}`,
    role: 'user',
    contentText: hint,
    text: hint,
    status: 'completed',
  })
  if (isScoreReviseIntent(hint)) {
    await runScoreRevise()
    return
  }
  await rewriteInPlace(hint)
}

async function rewriteInPlace(hint) {
  if (!xqCtx.value || xqBusy.value) return
  xqAbort?.abort()
  xqAbort = new AbortController()
  xqBusy.value = true
  xqStatus.value = 'streaming'
  xqError.value = ''
  xqPreview.value = { after: '', reason: '' }
  const live = {
    _localId: `a-${Date.now()}`,
    role: 'assistant',
    contentText: '',
    text: '',
    thinkingText: '',
    steps: [{
      stepNo: 1,
      stepKey: 'read_script_score',
      kind: 'tool',
      title: '对照讲稿和评分',
      action: '对照讲稿和评分',
      query: '选中段 + 最近评分 + 整篇讲稿',
      status: 'running',
    }],
    agentNotes: [{
      id: 'note-load',
      agent: '小启',
      text: '正在读取最近一次评分、项目信息和整篇讲稿。',
      at: Date.now(),
    }],
    status: 'streaming',
    phase: 'thinking',
    streamStartedAt: Date.now(),
    thinkingStartedAt: Date.now(),
  }
  xqMessages.value.push(live)
  try {
    const brief = await loadRewriteBrief()
    const scriptText = clipScriptAround(editor.value?.getText() || '', xqCtx.value.selection)
    live.agentNotes = [
      ...live.agentNotes,
      {
        id: 'note-brief',
        agent: '小启',
        text: brief.scoreText
          ? `已带上评分：${brief.scoreText.slice(0, 80)}${brief.scoreText.length > 80 ? '…' : ''}`
          : '没有找到最近评分，按讲稿上下文改这一段。',
        at: Date.now(),
      },
      {
        id: 'note-write',
        agent: '小启',
        text: '开始写建议稿。只动你选中的句子。',
        at: Date.now(),
      },
    ]
    const sessionId = await ensureXqSession()
    await assistantApi.streamMessage(
      sessionId,
      {
        content: buildAskPrompt(xqCtx.value, hint, { ...brief, scriptText }),
        mode: 'think',
        options: { mode: 'think' },
      },
      {
        signal: xqAbort.signal,
        onEvent: (event, data) => {
          applyAssistantStreamEvent(event, data, live)
        },
      },
    )
    const extracted = extractSuggestedRewrite(live.contentText || live.text || '', xqCtx.value.selection)
    if (extracted.after) {
      xqPreview.value = { ...extracted, before: xqCtx.value.selection }
    }
    const tool = (live.steps || []).find((s) => s.stepKey === 'read_script_score')
    if (tool) {
      tool.status = 'completed'
      tool.outputSummary = extracted.after ? '已写出建议稿' : '已对照上下文'
    }
    live.planDrafts = []
    live.status = 'completed'
    live.phase = 'done'
    xqStatus.value = extracted.after ? 'ready' : 'idle'
    if (!extracted.after && !String(live.contentText || '').trim()) {
      xqError.value = '这一版没写出可落稿的句子，再说一次要求'
    }
  } catch (e) {
    live.status = e.name === 'AbortError' ? 'cancelled' : 'failed'
    live.phase = 'done'
    if (e.name !== 'AbortError') {
      live.errorMessage = e.message || '改稿失败'
      xqError.value = e.message || '改稿失败'
      xqStatus.value = 'idle'
    }
  } finally {
    xqBusy.value = false
    xqAbort = null
  }
}

function pushAssistantNote(text) {
  xqMessages.value.push({
    _localId: `a-${Date.now()}`,
    role: 'assistant',
    contentText: text,
    text: text,
    status: 'completed',
    phase: 'done',
  })
}

async function runScoreRevise() {
  await prepareXqBinding()
  const scriptId = scriptBinding.value?.id || scriptBinding.value?.scriptId
  if (!scriptId) {
    pushAssistantNote('这篇文档还没有挂上讲稿，没法按评分对照。')
    return
  }
  xqBusy.value = true
  xqStatus.value = 'streaming'
  xqError.value = ''
  try {
    const res = await request.get(`/api/script/${scriptId}/score-revise-brief`, { silentError: true })
    const brief = res?.data || res
    xqScoreBrief.value = brief
    xqCtx.value = {
      ...xqCtx.value,
      scriptId,
      scriptTitle: brief.scriptTitle || xqCtx.value.scriptTitle,
      contentVersion: brief.contentVersion || xqCtx.value.contentVersion,
      scoreReportId: brief.scoreReportId,
      intent: 'script_score_revise',
    }
    await ensureXqSession()
    pushAssistantNote(formatScoreReviseDiagnosis(brief))
    xqScoreQueue.value = (brief.diagnosis || []).filter((d) => d.mapped && d.stepId)
    xqStatus.value = xqScoreQueue.value.length ? 'ready' : 'idle'
    await generateNextScoreItem()
  } catch (e) {
    xqError.value = e.message || '对照评分失败'
    xqStatus.value = 'idle'
  } finally {
    xqBusy.value = false
  }
}

async function generateNextScoreItem() {
  const item = xqScoreQueue.value.shift()
  if (!item || !xqScoreBrief.value) return
  await rewriteScoreItem(item, xqScoreBrief.value)
}

async function rewriteScoreItem(item, brief) {
  if (xqBusy.value && xqAbort) {
    // allow sequential: release busy per item by not checking global busy after first
  }
  xqAbort?.abort()
  xqAbort = new AbortController()
  const live = {
    _localId: `a-${Date.now()}`,
    role: 'assistant',
    contentText: '',
    text: '',
    thinkingText: '',
    steps: [],
    actionProposals: [],
    status: 'streaming',
    phase: 'thinking',
    streamStartedAt: Date.now(),
  }
  xqMessages.value.push(live)
  xqStatus.value = 'streaming'
  try {
    const sessionId = await ensureXqSession()
    await assistantApi.streamMessage(
      sessionId,
      {
        content: buildScoreItemRewritePrompt(item, brief),
        mode: 'fast',
        options: { mode: 'fast' },
      },
      {
        signal: xqAbort.signal,
        onEvent: (event, data) => applyAssistantStreamEvent(event, data, live),
      },
    )
    live.status = 'completed'
    live.phase = 'done'
    live.planDrafts = []
    const extracted = extractScriptPatchFromReply(live.contentText || live.text || '', {
      stepContent: item.stepContent,
      selection: '',
    })
    if (!extracted.after || extracted.after === item.stepContent) return
    const reason = extracted.reason.includes(String(item.id))
      ? extracted.reason
      : `评分条目 ${item.id}：${extracted.reason}`
    const res = await assistantApi.proposeScriptPatch({
      sessionId,
      actionType: 'apply_script_patch',
      title: `改写「${item.role || '该步骤'}」· ${item.focus || ''}`,
      summary: reason,
      args: {
        scriptId: brief.scriptId,
        expectedVersion: brief.contentVersion,
        patches: [{
          stepId: item.stepId,
          field: 'content',
          before: item.stepContent,
          after: extracted.after,
          reason,
          scoreItemId: item.id,
        }],
      },
    })
    const proposal = res?.data || res
    if (proposal?.proposalId) {
      live.actionProposals = [{ ...proposal, resultMessage: '', _busy: false }]
    }
    brief.contentVersion = Number(brief.contentVersion || 1)
  } catch (e) {
    if (e.name === 'AbortError') {
      live.status = 'cancelled'
    } else {
      live.status = 'failed'
      live.errorMessage = e.message || '这一条改稿失败'
    }
    live.phase = 'done'
  } finally {
    xqAbort = null
    xqStatus.value = 'ready'
  }
}

async function confirmScoreProposal(msg, ap) {
  if (!ap?.proposalId || ap._busy) return
  ap._busy = true
  try {
    const res = await assistantApi.confirmAction(ap.proposalId)
    ap.status = 'confirmed'
    ap.resultMessage = res?.data?.message || res?.message || '已写入这一格，角色未改'
    const nextVersion = res?.data?.result?.contentVersion ?? res?.result?.contentVersion
    if (nextVersion != null && xqCtx.value) {
      xqCtx.value = { ...xqCtx.value, contentVersion: nextVersion }
    }
    if (scriptBinding.value && nextVersion != null) {
      scriptBinding.value = { ...scriptBinding.value, contentVersion: nextVersion }
    }
    if (xqScoreBrief.value && nextVersion != null) {
      xqScoreBrief.value = { ...xqScoreBrief.value, contentVersion: nextVersion }
    }
    await reloadSdocQuiet()
    ElMessage.success(ap.resultMessage)
    await generateNextScoreItem()
  } catch (e) {
    ap.status = 'failed'
    ap.resultMessage = e.message || '写入失败'
    ElMessage.error(ap.resultMessage)
  } finally {
    ap._busy = false
  }
}

async function rejectScoreProposal(_msg, ap) {
  if (!ap?.proposalId || ap._busy) return
  ap._busy = true
  try {
    await assistantApi.rejectAction(ap.proposalId)
    ap.status = 'rejected'
    ap.resultMessage = '未写入'
    await generateNextScoreItem()
  } catch (e) {
    ap.status = 'failed'
    ap.resultMessage = e.message || '取消失败'
  } finally {
    ap._busy = false
  }
}

async function reloadSdocQuiet() {
  if (!editor.value || !activeId.value) return
  try {
    const data = await host.fetchSmartDoc(activeId.value, { silent: true })
    let json = data?.content
    if (typeof json === 'string') {
      try { json = JSON.parse(json) } catch { json = null }
    }
    if (json) {
      skipPersist = true
      editor.value.commands.setContent(sanitizeDocJson(json), { emitUpdate: false })
      lastAckedDoc = editor.value.getJSON()
      lastSavedJson = JSON.stringify(lastAckedDoc)
      queueMicrotask(() => { skipPersist = false })
    }
  } catch {
    // ignore
  }
}

async function applyXiaoQiPatch() {
  const ctx = xqCtx.value
  const { after } = lastAssistantRewrite()
  if (!ctx || !after || xqBusy.value) return
  if (xqPendingEdit.value) undoPendingEdit()
  const written = keepSpeaker(ctx.selection, after)
  const before = String(xqPreview.value?.before || ctx.selection)
  let from = ctx.from
  let to = ctx.to
  const size = editor.value?.state.doc.content.size || 0
  const atRange = from != null && to != null && from >= 1 && to <= size && from < to
  const current = atRange ? editor.value.state.doc.textBetween(from, to, '\n') : ''
  if (!atRange || current !== before) {
    const hit = findTextRange(before)
    if (hit) {
      from = hit.from
      to = hit.to
    }
  }
  xqBusy.value = true
  xqStatus.value = 'writing'
  xqError.value = ''
  try {
    if (!applyRangeText(from, to, written, false)) {
      throw new Error('原文位置已经变了，重新选一段再问')
    }
    const nextTo = from + written.length
    ctx.selection = written
    ctx.to = nextTo
    xqPendingEdit.value = {
      from,
      to: nextTo,
      before,
      after: written,
      ...pendingEditChrome(from, nextTo),
    }
    xqStatus.value = 'preview'
  } catch (e) {
    xqError.value = e.message || '写回失败'
    xqStatus.value = 'ready'
  } finally {
    xqBusy.value = false
  }
}

function rejectXiaoQiPatch() {
  xqPreview.value = { after: '', reason: '' }
  xqStatus.value = 'idle'
}

function confirmPendingEdit() {
  const pending = xqPendingEdit.value
  xqPendingEdit.value = null
  if (!pending) return
  scheduleSave()
  syncScriptFromSdoc()
  xqStatus.value = 'done'
  ElMessage.success('已确定修改')
}

function undoPendingEdit() {
  const pending = xqPendingEdit.value
  if (!pending) return
  applyRangeText(pending.from, pending.to, pending.before, false)
  if (xqCtx.value) {
    xqCtx.value.selection = pending.before
    xqCtx.value.to = pending.from + pending.before.length
  }
  xqPendingEdit.value = null
  xqStatus.value = 'ready'
}

async function prepareXqBinding() {
  if (!scriptBinding.value?.id && !scriptBinding.value?.scriptId && activeId.value) {
    await loadScriptBinding(activeId.value)
  }
}

function openXiaoQiPanel(ask) {
  const fallback = ask || resolveAskTarget() || {
    selection: '',
    from: null,
    to: null,
    speaker: '',
    nearby: { prev: '', next: '' },
  }
  xqCtx.value = buildAskContext(fallback, scriptBinding.value)
  xqDraft.value = ''
  xqError.value = ''
  if (!xqMessages.value.length) xqStatus.value = 'idle'
  xqOpen.value = true
  versionOpen.value = false
}

function closeInlineAsk() {
  xqInline.value = null
  xqInlineDraft.value = ''
}

async function openInlineAsk() {
  await prepareXqBinding()
  const ask = resolveAskTarget()
  if (!ask?.selection || !editor.value) {
    openXiaoQiPanel(ask)
    xiaoQiAsk.value = null
    return
  }
  const box = selectionBox(editor.value.view, ask.from, ask.to)
  xqInlineDraft.value = ''
  xqInline.value = { ...ask, ...box }
  xiaoQiAsk.value = null
  await nextTick()
  xqInlineInput.value?.focus()
}

async function submitInlineAsk() {
  const text = String(xqInlineDraft.value || '').trim()
  const ask = xqInline.value
  if (!text || !ask?.selection) return
  await prepareXqBinding()
  openXiaoQiPanel(ask)
  closeInlineAsk()
  await sendXiaoQi(text)
}

async function askXiaoQiFromSdoc() {
  const ask = resolveAskTarget()
  if (ask?.selection) {
    await openInlineAsk()
    return
  }
  await prepareXqBinding()
  openXiaoQiPanel(ask)
  xiaoQiAsk.value = null
}

askXiaoQiBridge.run = openInlineAsk

function sanitizeDocJson(node) {
  if (!node || typeof node !== 'object') return node
  if (Array.isArray(node.marks)) {
    node.marks = node.marks.filter((mark) => mark?.type && mark.type !== 'subscript')
  }
  if (Array.isArray(node.content)) {
    node.content = node.content.map((child) => sanitizeDocJson(child))
  }
  return node
}

function mountEditor(docJson) {
  editor.value?.destroy()
  editor.value = new Editor({
    extensions: createSmartDocExtensions({
      canEditProtected: canEditProtected.value,
      awareness: {
        getPeers: () => collabPeers.value,
        getSelfSession: () => presenceSessionId,
        getColorByPerson: () => colorByPerson.value,
        getUserId: () => String(host.getUser?.()?.id || ''),
      },
    }),
    content: sanitizeDocJson(docJson) || { type: 'doc', content: [{ type: 'paragraph' }] },
    editorProps: {
      attributes: { class: 'sdoc-prose' },
      handleDOMEvents: {
        pointerdown(_view, event) {
          if (event.target?.closest?.('.sdoc-selbar, .sdoc-ask-inline')) return false
          pointerSelecting = true
          return false
        },
        keyup(_view, event) {
          if (event.shiftKey || event.key.startsWith('Arrow') || event.key === 'Home' || event.key === 'End') {
            updateXiaoQiAsk(editor.value, { fromPointerUp: true })
          }
          return false
        },
      },
      handleKeyDown(_view, event) {
        if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'f') {
          event.preventDefault()
          if (!findOpen.value) toggleFind()
          else findInputRef.value?.focus()
          return true
        }
        if (event.key === 'Escape') {
          if (paint.value.on) {
            stopPaint()
            return true
          }
          if (findOpen.value) {
            closeFind()
            return true
          }
          if (colorOpen.value || highlightOpen.value) {
            colorOpen.value = false
            highlightOpen.value = false
            return true
          }
        }
        return handleSlashKeys(event)
      },
      handleClick(_view, _pos, event) {
        const a = event.target?.closest?.('a.sdoc-card, a[data-sdoc-file], a[data-sdoc-cloud]')
        if (!a) return false
        const href = a.getAttribute('href')
        if (!href || href === '#') return false
        event.preventDefault()
        if (a.hasAttribute('download') || a.dataset.sdocFile != null) {
          window.open(href, '_blank', 'noopener')
        } else {
          window.location.assign(href)
        }
        return true
      },
      handlePaste(_view, event) {
        const files = takeImageFiles(event.clipboardData)
        if (!files.length) return false
        event.preventDefault()
        files.forEach((file) => insertUploaded('image', file))
        return true
      },
      handleDrop(_view, event) {
        const files = takeImageFiles(event.dataTransfer)
        if (!files.length) return false
        event.preventDefault()
        files.forEach((file) => insertUploaded('image', file))
        return true
      },
    },
    onUpdate() {
      refreshSlash()
      refreshTableState()
      refreshHeadings()
      if (applyingRemote || skipPersist) return
      scheduleSync()
      scheduleSave()
    },
    onSelectionUpdate({ editor: current }) {
      refreshSlash()
      refreshTableState()
      refreshHeadings()
      updateXiaoQiAsk(current)
      if (applyingRemote) return
      maybeApplyPaint()
      flushCollab(false)
    },
  })
  lastSavedJson = JSON.stringify(editor.value.getJSON())
  lastAckedDoc = editor.value.getJSON()
  lastRev = -1
  localDirty = false
  refreshTableState()
  refreshHeadings()
}

async function load() {
  loading.value = true
  loadError.value = ''
  const id = activeId.value
  if (!id) {
    loadError.value = '缺少文档 ID'
    loading.value = false
    return
  }
  try {
    const data = await host.fetchSmartDoc(id)
    titleDraft.value = data?.title || '未命名文档'
    pageTitle.value = data?.title && data.title !== '未命名文档' ? data.title : ''
    ownerLabel.value = data?.ownerName ? `${data.ownerName} 创建` : '创建'
    updatedLabel.value = formatRel(data?.updatedAt)
    contentUpdatedAt.value = data?.contentUpdatedAt || data?.updatedAt || ''
    canEditProtected.value = !!data?.canEditProtected
      || ['TEACHER', 'SCHOOL_ADMIN', 'ADMIN'].includes(String(host.getRole?.() || '').toUpperCase())
    let json = data?.content
    if (typeof json === 'string') {
      try { json = JSON.parse(json) } catch { json = null }
    }
    mountEditor(json)
    const draft = readDraft()
    const draftJson = draft?.content ? JSON.stringify(draft.content) : ''
    draftOffer.value = Boolean(draftJson && draftJson !== lastSavedJson)
    emit('title', titleDraft.value)
    emit('meta', {
      title: titleDraft.value,
      ext: 'sdoc',
      documentKind: 'sdoc',
      scope: data?.scope,
      teamName: data?.teamName,
      teamId: data?.teamId,
    })
    startPresence()
    startCollab()
    await loadScriptBinding(id)
    refreshScriptSheetFlag()
  } catch (err) {
    loadError.value = err?.message || '打开智能文档失败'
    stopPresence()
    stopCollab()
  } finally {
    loading.value = false
  }
}

function onDocClick(ev) {
  if (ev.target.closest?.('.sdoc-fmt__insert') || ev.target.closest?.('.sdoc-menu') || ev.target.closest?.('.sdoc-emoji') || ev.target.closest?.('.sdoc-top__export') || ev.target.closest?.('.sdoc-fmt__pop') || ev.target.closest?.('.sdoc-selbar')) return
  insertOpen.value = false
  emojiOpen.value = false
  exportOpen.value = false
  colorOpen.value = false
  highlightOpen.value = false
  if (xqInline.value && !ev.target.closest?.('.sdoc-ask-inline') && !ev.target.closest?.('.sdoc-selbar')) {
    closeInlineAsk()
  }
}

async function flushPresence(force = false) {
  const id = activeId.value
  if (!id || loading.value || loadError.value) return
  const editing = lastEditAt > 0 && Date.now() - lastEditAt < 90000
  try {
    await host.reportPresence(id, {
      sessionId: presenceSessionId,
      visible: typeof document === 'undefined' ? true : !document.hidden,
      active: true,
      editing: editing || force,
      reset: false,
    })
  } catch {
    // ignore
  }
}

function startPresence() {
  stopPresence()
  flushPresence(true).catch(() => {})
  presenceTimer = window.setInterval(() => {
    flushPresence(false).catch(() => {})
  }, 15000)
}

function stopPresence() {
  if (presenceTimer) {
    window.clearInterval(presenceTimer)
    presenceTimer = 0
  }
}

defineExpose({ flushSave, reload: load })

onMounted(() => {
  document.addEventListener('click', onDocClick)
  document.addEventListener('pointerup', onEditorPointerUp, true)
  document.addEventListener('scroll', repositionAskChrome, true)
  window.addEventListener('resize', repositionAskChrome)
  load()
})

watch(activeId, load)
watch(findQuery, () => {
  if (findOpen.value) refreshFind()
})
watch(colorByPerson, () => refreshAwareness(editor.value))

onBeforeUnmount(() => {
  xqAbort?.abort()
  clearSelBarHide()
  document.removeEventListener('click', onDocClick)
  document.removeEventListener('pointerup', onEditorPointerUp, true)
  document.removeEventListener('scroll', repositionAskChrome, true)
  window.removeEventListener('resize', repositionAskChrome)
  window.clearTimeout(saveTimer)
  if (editor.value && JSON.stringify(editor.value.getJSON()) !== lastSavedJson) {
    flushSave()
  }
  flushPresence(true).catch(() => {})
  stopPresence()
  stopCollab()
  editor.value?.destroy()
})
</script>
