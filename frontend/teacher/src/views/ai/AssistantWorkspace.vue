<template>
  <div
    class="assistant-layout"
    :class="{ 'is-left-open': leftOpen, 'is-right-open': rightOpen }"
  >
    <!-- 左：会话 -->
    <aside class="assistant-pane assistant-pane--left" aria-label="会话列表">
      <div class="assistant-pane__head">
        <h2 class="assistant-brand-title">
          <XiaoQiMark :size="28" :hoverable="true" aria-label="小启AI" />
          <span>小启AI</span>
        </h2>
        <button type="button" class="xq-icon-btn xq-icon-btn--accent" title="新对话" aria-label="新对话" @click="onCreateSession">
          <XqIcon name="plus" size="md" />
        </button>
      </div>
      <div class="assistant-search">
        <div class="assistant-search__field">
          <XqIcon name="search" size="sm" class="assistant-search__icon" />
          <input
            v-model="sessionKeyword"
            type="search"
            placeholder="搜索对话…"
            @input="onSearchInput"
            @keydown.enter.prevent="refreshSessions"
          />
        </div>
      </div>
      <div class="assistant-session-list">
        <div
          v-for="s in sessions"
          :key="s.id"
          class="assistant-session-item"
          :class="{ 'is-active': String(s.id) === String(activeSessionId) }"
        >
          <button type="button" class="assistant-session-item__main" @click="selectSession(s.id)">
            <strong>{{ s.title || '新对话' }}</strong>
            <small>{{ formatTime(s.updatedAt || s.lastMessageAt) }}</small>
          </button>
          <div class="assistant-session-item__ops">
            <button
              type="button"
              class="xq-icon-btn xq-icon-btn--xs"
              :class="{ 'is-on': s.pin }"
              :title="s.pin ? '取消置顶' : '置顶'"
              @click.stop="togglePin(s)"
            ><XqIcon name="pin" size="sm" /></button>
            <button
              type="button"
              class="xq-icon-btn xq-icon-btn--xs"
              title="删除对话"
              @click.stop="removeSession(s.id)"
            ><XqIcon name="trash" size="sm" /></button>
          </div>
        </div>
        <div v-if="!sessions.length" class="assistant-empty">
          <p>还没有对话</p>
          <button type="button" class="xq-text-btn" @click="onCreateSession">新建一个</button>
        </div>
      </div>
    </aside>

    <!-- 中：对话 -->
    <section class="assistant-pane assistant-pane--chat" aria-label="对话区">
      <header class="assistant-chat-header">
        <button
          type="button"
          class="xq-icon-btn"
          :class="{ 'is-on': leftOpen }"
          title="会话列表"
          aria-label="会话列表"
          :aria-pressed="leftOpen"
          @click="toggleLeftPanel"
        >
          <XqIcon name="panel-left" />
        </button>
        <input
          v-if="activeSession"
          v-model="titleDraft"
          class="title-input"
          maxlength="80"
          aria-label="对话标题"
          @blur="saveTitle"
          @keydown.enter.prevent="saveTitle"
        />
        <span v-else class="title-fallback">小启AI</span>

        <div class="assistant-header-actions">
          <div v-if="activeSession" class="team-bind-mini" title="绑定项目后可引用资源中心">
            <select v-model="boundTeamId" @change="onBindTeam">
              <option :value="null">项目</option>
              <option v-for="t in teams" :key="t.id || t.teamId" :value="Number(t.id || t.teamId)">
                {{ t.name || t.teamName || `项目 ${t.id || t.teamId}` }}
              </option>
            </select>
          </div>
          <button
            type="button"
            class="xq-icon-btn"
            :class="{ 'is-on': chatSearchOpen }"
            title="搜索当前对话"
            aria-label="搜索当前对话"
            :disabled="!activeSessionId"
            @click="chatSearchOpen = !chatSearchOpen"
          ><XqIcon name="search" /></button>
          <button
            type="button"
            class="xq-icon-btn"
            title="导出 PDF"
            aria-label="导出 PDF"
            :disabled="!activeSessionId || isResponding || exportBusy"
            @click="exportPdf"
          ><XqIcon name="download" /></button>
          <button
            type="button"
            class="xq-icon-btn"
            title="分享到团队"
            aria-label="分享到团队"
            :disabled="!activeSessionId || isResponding"
            @click="openShare"
          ><XqIcon name="share" /></button>
          <button
            v-if="isResponding"
            type="button"
            class="xq-icon-btn xq-icon-btn--danger"
            title="停止生成"
            aria-label="停止生成"
            @click="stopGeneration"
          ><XqIcon name="stop" /></button>
          <button
            type="button"
            class="xq-icon-btn"
            :class="{ 'is-on': rightOpen }"
            title="本场文件与写作习惯"
            aria-label="本场文件与写作习惯"
            :aria-pressed="rightOpen"
            @click="toggleRightPanel"
          >
            <XqIcon name="panel-right" />
          </button>
        </div>
      </header>

      <!-- 窄屏打开侧栏时的遮罩 -->
      <button
        v-if="leftOpen"
        type="button"
        class="assistant-left-scrim"
        aria-label="关闭会话列表"
        @click="leftOpen = false"
      />
      <button
        v-if="rightOpen"
        type="button"
        class="assistant-right-scrim"
        aria-label="关闭资料面板"
        @click="rightOpen = false"
      />

      <div v-if="activeSessionId && chatSearchOpen" class="chat-search-bar">
        <XqIcon name="search" size="sm" class="chat-search-bar__icon" />
        <input
          v-model="chatKeyword"
          type="search"
          placeholder="在当前对话中搜索…"
          aria-label="当前对话搜索"
        />
        <span v-if="chatKeyword.trim()" class="chat-search-count">{{ filteredMessages.length }} 条</span>
        <button type="button" class="xq-icon-btn xq-icon-btn--xs" title="关闭搜索" @click="chatSearchOpen = false; chatKeyword = ''">
          <XqIcon name="close" size="sm" />
        </button>
      </div>

      <div
        ref="messagesRef"
        class="assistant-messages"
        :class="{
          'is-switching': sessionSwitching,
          'is-loading-session': sessionLoading,
        }"
        @scroll="onScroll"
      >
        <Transition name="xq-surface" mode="out-in">
          <div v-if="showWelcome" key="welcome" class="assistant-welcome">
            <div class="assistant-welcome__hero">
              <XiaoQiMark :size="56" :hoverable="true" aria-label="小启AI" />
              <h1>{{ activeSessionId ? '开始新对话' : '今天带队，想先搞定哪件事？' }}</h1>
              <p>
                {{ activeSessionId
                  ? '点下方示例，或直接问：待批、缺交、进度、怎么催交。'
                  : '查工作台、看进度、催缺交、写批改反馈、排今日任务——按你的真实数据答。' }}
              </p>
            </div>
            <div class="assistant-chips">
              <button
                v-for="chip in welcomeChips"
                :key="chip"
                type="button"
                class="assistant-chip"
                @click="activeSessionId ? sendText(chip) : quickStart(chip)"
              >
                {{ chip }}
              </button>
            </div>
          </div>

          <div
            v-else
            key="thread"
            class="assistant-thread"
            :class="{ 'is-fading': sessionSwitching || (sessionLoading && !messages.length) }"
          >
          <div
            v-if="sessionLoading && !messages.length"
            class="assistant-thread-loading"
            aria-live="polite"
          >
            加载对话中…
          </div>
          <div
            v-if="chatKeyword.trim() && !filteredMessages.length && messages.length"
            class="assistant-empty"
          >
            没有匹配「{{ chatKeyword }}」的消息
          </div>

          <article
            v-for="msg in filteredMessages"
            :key="msg.id || msg._localId"
            class="assistant-msg"
            :class="[
              msg.role === 'user' ? 'is-user' : 'is-assistant',
              msg.status === 'streaming' ? 'is-streaming' : '',
            ]"
          >
            <div v-if="msg.role === 'assistant'" class="assistant-msg__avatar is-xiaoqi">
              <XiaoQiMark :size="28" :hoverable="false" aria-label="小启AI" />
            </div>
            <div class="assistant-msg__body">
              <details
                v-if="msg.role === 'assistant' && msg.thinkingText"
                class="assistant-thinking"
                :open="msg.status === 'streaming' && !msg.contentText"
              >
                <summary>思考过程</summary>
                <pre>{{ msg.thinkingText }}</pre>
              </details>

              <div v-if="msg.role === 'assistant' && msg.brainHints" class="assistant-brain-hints">
                <span v-if="msg.brainHints.project" class="brain-chip">项目 · {{ msg.brainHints.project }}</span>
                <span v-if="msg.brainHints.goal" class="brain-chip">{{ brainGoalLabel(msg.brainHints.goal) }}</span>
                <span v-if="msg.brainHints.softIntent" class="brain-chip is-soft">意图纠偏</span>
                <span
                  v-for="(a, i) in (msg.brainHints.assumptions || []).slice(0, 2)"
                  :key="`assump-${i}`"
                  class="brain-chip is-muted"
                  :title="a"
                >{{ a }}</span>
              </div>

              <div v-if="msg.steps?.length || msg.ocrLogs?.length" class="assistant-steps" aria-live="polite">
                <div
                  v-for="step in msg.steps"
                  :key="`${step.stepNo}-${step.stepKey || ''}`"
                  class="assistant-step"
                  :class="`is-${step.status || 'running'}`"
                >
                  <span class="dot" />
                  <span>{{ step.title }}{{ step.outputSummary ? ` · ${step.outputSummary}` : '' }}</span>
                </div>
                <div
                  v-for="(log, li) in (msg.ocrLogs || []).slice(-4)"
                  :key="`ocr-log-${li}`"
                  class="assistant-step is-running assistant-step--ocr"
                >
                  <span class="dot" />
                  <span>{{ log }}</span>
                </div>
              </div>

              <div v-if="msg.citations?.length" class="assistant-citations">
                <span class="assistant-citations__label">参考</span>
                <button
                  v-for="(c, idx) in msg.citations"
                  :key="`${c.resourceId || c.fileId || idx}`"
                  type="button"
                  class="assistant-citation-chip"
                  :class="{ 'is-ocr': c.ocr || c.method === 'ocr', 'is-cache': c.fromCache }"
                  :title="citationTitle(c)"
                >
                  <span v-if="c.ocr || c.method === 'ocr'" class="cite-badge">OCR</span>
                  <span v-else-if="c.fromCache" class="cite-badge cite-badge--cache">缓存</span>
                  {{ c.title || '资料' }}
                </button>
              </div>

              <div
                class="assistant-content xq-md"
                :class="{ 'is-empty-stream': msg.role === 'assistant' && msg.status === 'streaming' && !msg.contentText }"
                v-html="formatMarkdown(msg.contentText || (msg.status === 'streaming' ? '' : ''), { streaming: msg.status === 'streaming' })"
              />
              <span
                v-if="msg.role === 'assistant' && msg.status === 'streaming'"
                class="assistant-cursor"
                aria-hidden="true"
              />

              <div v-if="msg.files?.length" class="assistant-msg-files">
                <div v-for="f in msg.files" :key="f.fileId || f.id" class="assistant-file-pill">
                  <XqIcon name="file" size="sm" />
                  <strong>{{ f.name }}</strong>
                  <a
                    v-if="f.fileId || f.id"
                    class="xq-text-btn"
                    :href="fileDownloadUrl(f.fileId || f.id)"
                    target="_blank"
                    rel="noopener"
                  >下载</a>
                  <button
                    v-if="f.fileId || f.id"
                    type="button"
                    class="xq-text-btn"
                    @click="saveFileToTeam(f.fileId || f.id)"
                  >存到资源中心</button>
                </div>
              </div>

              <div
                v-if="msg.role === 'assistant' && (msg.status === 'completed' || msg.status === 'failed' || msg.status === 'cancelled') && (msg.contentText || msg.errorMessage)"
                class="assistant-msg-toolbar"
              >
                <button v-if="msg.contentText" type="button" class="xq-icon-btn xq-icon-btn--xs" title="复制" @click="copyText(msg.contentText)">
                  <XqIcon name="copy" size="sm" />
                </button>
                <button v-if="msg.contentText" type="button" class="xq-icon-btn xq-icon-btn--xs" title="保存 Markdown" @click="saveMessageAsFile(msg, 'md')">
                  <XqIcon name="file" size="sm" />
                </button>
                <button v-if="msg.contentText" type="button" class="xq-text-btn" @click="saveMessageAsFile(msg, 'docx')">Word</button>
                <button v-if="msg.contentText" type="button" class="xq-text-btn" @click="saveMessageAsFile(msg, 'pdf')">PDF</button>
                <button v-if="msg.contentText" type="button" class="xq-text-btn" @click="saveMessageAsFile(msg, 'pptx')">PPT</button>
                <button type="button" class="xq-icon-btn xq-icon-btn--xs" title="重新生成" :disabled="isResponding" @click="regenerateFrom(msg)">
                  <XqIcon name="refresh" size="sm" />
                </button>
              </div>

              <div v-if="msg.errorMessage" class="assistant-error">{{ msg.errorMessage }}</div>

              <!-- L2 写操作确认卡 -->
              <div
                v-if="msg.role === 'assistant' && msg.actionProposals?.length"
                class="assistant-action-cards"
              >
                <div
                  v-for="ap in msg.actionProposals"
                  :key="ap.proposalId"
                  class="assistant-action-card"
                  :class="`is-${ap.status || 'pending'}`"
                >
                  <div class="assistant-action-card__head">
                    <strong>{{ ap.title || '待确认操作' }}</strong>
                    <span class="assistant-action-card__badge">{{ actionStatusLabel(ap.status) }}</span>
                  </div>
                  <p class="assistant-action-card__summary">{{ ap.summary || '确认后才会真正修改数据。' }}</p>
                  <div v-if="ap.status === 'pending' || !ap.status" class="assistant-action-card__actions">
                    <button
                      type="button"
                      class="xq-text-btn assistant-action-card__confirm"
                      :disabled="ap._busy"
                      @click="confirmActionProposal(msg, ap)"
                    >{{ ap.confirmLabel || '确认执行' }}</button>
                    <button
                      type="button"
                      class="xq-text-btn"
                      :disabled="ap._busy"
                      @click="rejectActionProposal(msg, ap)"
                    >{{ ap.cancelLabel || '取消' }}</button>
                  </div>
                  <p v-if="ap.resultMessage" class="assistant-action-card__result">{{ ap.resultMessage }}</p>
                </div>
              </div>
            </div>
          </article>
          </div>
        </Transition>
      </div>

      <footer class="assistant-composer">
        <div v-if="selectedResources.length || pendingFiles.length" class="composer-attachments">
          <span v-for="r in selectedResources" :key="`r-${r.id}`" class="composer-chip">
            <XqIcon name="library" size="sm" />
            {{ r.name }}
            <button type="button" aria-label="移除" @click="removeSelectedResource(r.id)"><XqIcon name="close" size="sm" /></button>
          </span>
          <span v-for="f in pendingFiles" :key="`f-${f.id}`" class="composer-chip">
            <XqIcon name="paperclip" size="sm" />
            {{ f.name }}
            <button type="button" aria-label="移除" @click="removePending(f.id)"><XqIcon name="close" size="sm" /></button>
          </span>
        </div>

        <div class="assistant-composer__shell">
          <div class="assistant-composer__box">
            <textarea
              v-model="inputText"
              rows="1"
              placeholder="问问小启：今天待批多少？谁缺交？帮我写催交话术…"
              :disabled="isResponding"
              @keydown="onKeydown"
              @compositionstart="onComposerCompositionStart"
              @compositionend="onComposerCompositionEnd"
              @input="autoGrowComposer"
              ref="composerRef"
            />
            <div class="assistant-composer__actions">
              <div class="composer-tools">
                <label class="xq-icon-btn" title="上传附件" aria-label="上传附件">
                  <XqIcon name="paperclip" />
                  <input type="file" hidden multiple @change="onPickFiles" />
                </label>
                <button
                  type="button"
                  class="xq-icon-btn"
                  :disabled="!boundTeamId"
                  :title="boundTeamId ? '从资源中心选择' : '请先绑定项目'"
                  aria-label="从资源中心选择"
                  @click="openResourcePicker"
                >
                  <XqIcon name="library" />
                </button>
              </div>
              <button
                type="button"
                class="xq-send-btn"
                :disabled="isResponding || (!inputText.trim() && !pendingFiles.length && !selectedResources.length)"
                :title="isResponding ? '生成中' : '发送'"
                aria-label="发送"
                @click="sendText(inputText)"
              >
                <XqIcon v-if="!isResponding" name="send" size="md" />
                <span v-else class="xq-send-btn__spin" aria-hidden="true" />
              </button>
            </div>
          </div>
          <p class="composer-hint">Enter 发送（输入法选词时除外）· Shift+Enter 换行 · 提到「评分」才会读评分</p>
        </div>
      </footer>
    </section>

    <!-- 右：本场文件 / 写作习惯 -->
    <aside class="assistant-pane assistant-pane--right" aria-label="本场文件与写作习惯">
      <div class="assistant-pane__head">
        <div class="assistant-right-tabs" role="tablist">
          <button
            type="button"
            role="tab"
            :aria-selected="rightTab === 'files'"
            :class="{ 'is-active': rightTab === 'files' }"
            @click="rightTab = 'files'"
          >本场文件</button>
          <button
            type="button"
            role="tab"
            :aria-selected="rightTab === 'memory'"
            :class="{ 'is-active': rightTab === 'memory' }"
            @click="rightTab = 'memory'"
          >写作习惯</button>
        </div>
        <button type="button" class="xq-icon-btn xq-icon-btn--xs" title="收起" @click="rightOpen = false">
          <XqIcon name="close" size="sm" />
        </button>
      </div>

      <div class="assistant-right-body">
        <!-- —— 本场文件 —— -->
        <template v-if="rightTab === 'files'">
          <section class="xq-side-guide">
            <strong>本场文件是什么？</strong>
            <p>只属于<strong>当前这场对话</strong>：你上传的、从资源中心点进来的、小启生成的。队友默认看不到。</p>
            <ul class="xq-side-guide__list">
              <li><b>引用</b>：给小启当参考，帮你改稿</li>
              <li><b>生成</b>：Word / PPT / PDF 等可下载</li>
              <li><b>存到资源中心</b>：才会进团队共享</li>
            </ul>
          </section>

          <div class="xq-side-actions">
            <label class="xq-side-action" :class="{ 'is-disabled': isResponding }">
              <XqIcon name="paperclip" size="sm" />
              <span>上传附件</span>
              <input type="file" hidden multiple :disabled="isResponding" @change="onPickFiles" />
            </label>
            <button
              type="button"
              class="xq-side-action"
              :disabled="!boundTeamId || isResponding"
              :title="boundTeamId ? '从团队资源中心选择资料' : '请先在顶栏选择项目'"
              @click="openResourcePicker"
            >
              <XqIcon name="library" size="sm" />
              <span>引用团队资料</span>
            </button>
          </div>
          <p v-if="!boundTeamId" class="xq-side-tip">
            顶栏先选「项目」，才能引用资源中心里的资料。
          </p>

          <div v-if="!sessionFiles.length" class="xq-side-empty">
            <strong>这一场还没有文件</strong>
            <p>可上传附件或引用团队资源；小启整理的催交/批改文稿也会出现在这里。</p>
          </div>

          <template v-else>
            <section v-if="filesByGroup.ref.length" class="xq-file-group">
              <header class="xq-file-group__head">
                <span>引用给小启看的</span>
                <small>{{ filesByGroup.ref.length }}</small>
              </header>
              <article v-for="f in filesByGroup.ref" :key="f.id" class="xq-file-card">
                <div class="xq-file-card__icon"><XqIcon name="library" size="sm" /></div>
                <div class="xq-file-card__main">
                  <strong :title="f.name">{{ f.name }}</strong>
                  <small>资源中心 · {{ formatSize(f.sizeBytes) }}</small>
                </div>
                <a class="xq-text-btn" :href="fileDownloadUrl(f.id)" target="_blank" rel="noopener">打开</a>
              </article>
            </section>

            <section v-if="filesByGroup.upload.length" class="xq-file-group">
              <header class="xq-file-group__head">
                <span>我上传的</span>
                <small>{{ filesByGroup.upload.length }}</small>
              </header>
              <article v-for="f in filesByGroup.upload" :key="f.id" class="xq-file-card">
                <div class="xq-file-card__icon"><XqIcon name="paperclip" size="sm" /></div>
                <div class="xq-file-card__main">
                  <strong :title="f.name">{{ f.name }}</strong>
                  <small>本场私有 · {{ formatSize(f.sizeBytes) }}</small>
                </div>
                <div class="xq-file-card__ops">
                  <a class="xq-text-btn" :href="fileDownloadUrl(f.id)" target="_blank" rel="noopener">下载</a>
                  <button type="button" class="xq-text-btn" @click="saveFileToTeam(f.id)">共享给团队</button>
                </div>
              </article>
            </section>

            <section v-if="filesByGroup.generated.length" class="xq-file-group">
              <header class="xq-file-group__head">
                <span>小启生成的</span>
                <small>{{ filesByGroup.generated.length }}</small>
              </header>
              <article v-for="f in filesByGroup.generated" :key="f.id" class="xq-file-card">
                <div class="xq-file-card__icon is-gen"><XqIcon name="file" size="sm" /></div>
                <div class="xq-file-card__main">
                  <strong :title="f.name">{{ f.name }}</strong>
                  <small>{{ fileSourceLabel(f.source) }} · {{ formatSize(f.sizeBytes) }}</small>
                </div>
                <div class="xq-file-card__ops">
                  <a class="xq-text-btn" :href="fileDownloadUrl(f.id)" target="_blank" rel="noopener">下载</a>
                  <button type="button" class="xq-text-btn" @click="saveFileToTeam(f.id)">共享给团队</button>
                </div>
              </article>
            </section>
          </template>
        </template>

        <!-- —— 写作习惯 —— -->
        <template v-else>
          <section class="xq-side-guide">
            <strong>带队习惯是什么？</strong>
            <p>写给小启的<strong>教学偏好小抄</strong>（仅你可见）。换新对话也会参考，不用每次重说。</p>
            <ul class="xq-side-guide__list">
              <li><b>适合写</b>：催交口径、批改标准、本周训练重点、关注哪些学生</li>
              <li><b>别写</b>：学生隐私、无关账号密码、未公开的成绩细节</li>
            </ul>
          </section>

          <label class="assistant-pref-label" for="assistant-memory-input">用一句话告诉小启</label>
          <div class="assistant-pref-form">
            <textarea
              id="assistant-memory-input"
              v-model="memoryDraft"
              maxlength="500"
              rows="3"
              placeholder="例如：催交语气要专业克制，优先点名缺交≥2天的学生"
              @keydown.meta.enter.prevent="addMemory"
              @keydown.ctrl.enter.prevent="addMemory"
            />
            <div class="assistant-pref-form__actions">
              <span class="assistant-pref-count">{{ memoryDraft.length }}/500 · ⌘/Ctrl+Enter</span>
              <button type="button" class="xq-pill-btn xq-pill-btn--primary" @click="addMemory">保存习惯</button>
            </div>
          </div>

          <div class="assistant-pref-examples">
            <span class="assistant-pref-examples__label">不会写？点一条试试</span>
            <div class="assistant-chips assistant-chips--start">
              <button
                v-for="ex in memoryExamples"
                :key="ex"
                type="button"
                class="assistant-chip assistant-chip--sm"
                @click="memoryDraft = ex"
              >{{ ex }}</button>
            </div>
          </div>

          <header class="xq-file-group__head xq-file-group__head--alone">
            <span>已保存的习惯</span>
            <small>{{ memories.length }}</small>
          </header>

          <div v-if="!memories.length" class="xq-side-empty">
            <strong>还没有习惯</strong>
            <p>加 1～2 条就够用。之后催交、批改反馈会更贴你的带队风格。</p>
          </div>

          <article v-for="m in memories" :key="m.id" class="xq-memory-card">
            <div class="xq-memory-card__top">
              <span class="assistant-memory-tag">{{ memoryTypeLabel(m.memoryType) }}</span>
              <small>{{ formatTime(m.updatedAt) }}</small>
            </div>
            <p class="xq-memory-card__text">{{ m.content }}</p>
            <button type="button" class="xq-text-btn" @click="removeMemory(m.id)">删除这条</button>
          </article>
        </template>
      </div>
    </aside>

    <!-- 资源选择弹层 -->
    <Teleport to="body">
    <div v-if="pickerOpen" class="assistant-modal" role="dialog" aria-modal="true" aria-label="选择资源中心资料">
      <div class="assistant-modal__scrim" @click="pickerOpen = false" />
      <div class="assistant-modal__panel">
        <header class="assistant-modal__head">
          <h3>从资源中心选择资料</h3>
          <button type="button" class="xq-icon-btn" title="关闭" @click="pickerOpen = false"><XqIcon name="close" /></button>
        </header>
        <div class="assistant-modal__body">
          <p v-if="!boundTeamId" class="assistant-error">请先在顶栏绑定项目</p>
          <template v-else>
            <p class="assistant-memory-hint">勾选后，下一次发送会把资料文本交给助手参考（文本类可解析全文）。</p>
            <div v-if="pickerLoading" class="assistant-empty">加载中…</div>
            <label
              v-for="f in pickerFiles"
              :key="f.id"
              class="picker-row"
            >
              <input type="checkbox" :value="f.id" v-model="pickerChecked" />
              <span>
                <strong>{{ f.name }}</strong>
                <small>
                  {{ f.ext || '' }} · {{ formatSize(f.fileSize) }}
                  <template v-if="f.extractMethod">
                    ·
                    <span v-if="f.extractMethod === 'ocr'" class="picker-status is-ocr">已OCR</span>
                    <span v-else-if="f.extractMethod === 'text_layer'" class="picker-status">文字层</span>
                    <span v-else-if="f.extractMethod === 'docx'" class="picker-status">Word</span>
                    <span v-else-if="f.extractMethod === 'pptx'" class="picker-status">PPT</span>
                    <span v-else class="picker-status">已解析</span>
                    <span v-if="f.extractChars" class="picker-status-chars">{{ Number(f.extractChars).toLocaleString() }} 字</span>
                  </template>
                  <template v-else> · <span class="picker-status is-pending">未解析</span></template>
                </small>
              </span>
            </label>
            <div v-if="!pickerLoading && !pickerFiles.length" class="assistant-empty-card">
              <strong>该项目暂无资料</strong>
              <p>请先到资源管理上传训练资料或文档。</p>
            </div>
          </template>
        </div>
        <footer class="assistant-modal__foot">
          <button type="button" class="xq-pill-btn" @click="pickerOpen = false">取消</button>
          <button type="button" class="xq-pill-btn xq-pill-btn--primary" @click="confirmPicker">加入参考 ({{ pickerChecked.length }})</button>
        </footer>
      </div>
    </div>
    </Teleport>

    <!-- 分享弹层 -->
    <Teleport to="body">
    <div v-if="shareOpen" class="assistant-modal" role="dialog" aria-modal="true" aria-label="分享对话">
      <div class="assistant-modal__scrim" @click="shareOpen = false" />
      <div class="assistant-modal__panel">
        <header class="assistant-modal__head">
          <h3>分享对话到项目</h3>
          <button type="button" class="xq-icon-btn" title="关闭" @click="shareOpen = false"><XqIcon name="close" /></button>
        </header>
        <div class="assistant-modal__body">
          <p class="assistant-memory-hint">会生成一份 Markdown 纪要放到资源中心，不会共享你的带队习惯条目。</p>
          <label class="assistant-pref-label">目标项目</label>
          <select v-model="shareTeamId" class="assistant-select">
            <option v-for="t in teams" :key="t.id || t.teamId" :value="Number(t.id || t.teamId)">
              {{ t.name || t.teamName || `项目 ${t.id || t.teamId}` }}
            </option>
          </select>
          <label class="assistant-pref-label" style="margin-top:12px">分享内容</label>
          <select v-model="shareMode" class="assistant-select">
            <option value="summary">对话摘要（推荐）</option>
            <option value="full_text">完整对话</option>
            <option value="artifacts_only">仅文件产物说明</option>
          </select>
        </div>
        <footer class="assistant-modal__foot">
          <button type="button" class="xq-pill-btn" @click="shareOpen = false">取消</button>
          <button type="button" class="xq-pill-btn xq-pill-btn--primary" :disabled="!shareTeamId || shareBusy" @click="confirmShare">
            {{ shareBusy ? '分享中…' : '确认分享' }}
          </button>
        </footer>
      </div>
    </div>
    </Teleport>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import '../../styles/assistant.css'
import * as api from '../../services/assistantClient'
import { fileDownloadUrl } from '../../services/assistantClient'
import XiaoQiMark from '../../components/brand/XiaoQiMark.vue'
import XqIcon from '../../components/assistant/XqIcon.vue'
import { formatAssistantMarkdown } from '../../utils/assistantMarkdown'
// 教师端：同一套小启界面；数据权限由 JWT role + 教师工具约束

const route = useRoute()
const router = useRouter()

const sessions = ref([])
const teams = ref([])
const activeSessionId = ref(null)
const activeSession = ref(null)
const boundTeamId = ref(null)
const messages = ref([])
const sessionFiles = ref([])
const memories = ref([])
const inputText = ref('')
const titleDraft = ref('')
const memoryDraft = ref('')
const pendingFiles = ref([])
const selectedResources = ref([])
const isResponding = ref(false)
/** 会话切换/加载中，用于平滑过渡，避免闪欢迎页 */
const sessionLoading = ref(false)
const sessionSwitching = ref(false)
let sessionLoadSeq = 0
/** 当前流式输出绑定的会话，切换会话后忽略过期事件 */
let streamBoundSessionId = null
/** 宽屏默认打开会话栏；窄屏默认关，点顶栏按钮打开 */
const leftOpen = ref(typeof window !== 'undefined' ? window.innerWidth >= 960 : true)
/** 宽屏默认打开资料栏；窄屏默认关，点顶栏按钮打开 */
const rightOpen = ref(typeof window !== 'undefined' ? window.innerWidth >= 1280 : true)
const rightTab = ref('files')

function toggleLeftPanel() {
  leftOpen.value = !leftOpen.value
}

function toggleRightPanel() {
  rightOpen.value = !rightOpen.value
}
const messagesRef = ref(null)
const stickBottom = ref(true)

const pickerOpen = ref(false)
const pickerLoading = ref(false)
const pickerFiles = ref([])
const pickerChecked = ref([])

const shareOpen = ref(false)
const shareTeamId = ref(null)
const shareMode = ref('summary')
const shareBusy = ref(false)
const sessionKeyword = ref('')
const chatKeyword = ref('')
const chatSearchOpen = ref(false)
const exportBusy = ref(false)
const composerRef = ref(null)
let searchTimer = null

function autoGrowComposer() {
  const el = composerRef.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = `${Math.min(el.scrollHeight, 160)}px`
}

const filteredMessages = computed(() => {
  const q = chatKeyword.value.trim().toLowerCase()
  if (!q) return messages.value
  return messages.value.filter((m) => {
    const text = String(m.contentText || '').toLowerCase()
    const think = String(m.thinkingText || '').toLowerCase()
    return text.includes(q) || think.includes(q)
  })
})

/** 有会话且无消息、且不在发送/加载时才显示欢迎页，避免创建会话后仍停在空页 */
const showWelcome = computed(() => {
  if (isResponding.value) return false
  if (sessionLoading.value || sessionSwitching.value) return false
  if (messages.value.length) return false
  // 无 activeSessionId：默认落地页；有 id 且空消息：刚建好的「开始新对话」
  return true
})

let abortController = null
/** 刷新后重连订阅用，abort 只断订阅不断服务端任务 */
let resumeAbort = null
let currentRunId = null

function stopClientStream({ keepResponding = false } = {}) {
  if (resumeAbort) {
    try { resumeAbort.abort() } catch { /* ignore */ }
    resumeAbort = null
  }
  if (abortController) {
    try { abortController.abort() } catch { /* ignore */ }
    abortController = null
  }
  streamBoundSessionId = null
  currentRunId = null
  if (!keepResponding) isResponding.value = false
}

function isStreamForActiveSession(sessionId) {
  if (sessionId == null) return false
  return String(activeSessionId.value) === String(sessionId)
    && (streamBoundSessionId == null || String(streamBoundSessionId) === String(sessionId))
}

/** 教师端引导：对齐「每天要盯什么、小启能代劳什么」 */
const welcomeChips = [
  '汇总工作台：待批改、今日未交、需关注学生各有多少？',
  '当前训练营进度怎么样？列出缺交较多的学生并给催交建议',
  '帮我写一段专业克制的催交通知，面向今日未交学生',
  '根据待批队列，给我今日批改优先级和反馈话术模板',
]

const memoryExamples = [
  '催交语气要专业克制，先点明截止时间再给补交路径',
  '批改反馈先肯定再给 1～2 条可改点，避免长篇说教',
  '优先盯缺交≥2 天和连续未交的学生',
  '本周训练重点是路演结构与交付截图规范',
]

function memoryTypeLabel(type) {
  return ({
    preference: '带队习惯',
    goal: '教学重点',
    style: '沟通风格',
    project_focus: '项目关注',
    manual: '我的备注',
    auto_summary: '自动提炼',
  })[type] || '我的备注'
}

function fileSourceLabel(source) {
  return ({
    upload: '我上传的',
    generated: '小启生成的',
    resource_ref: '资源中心引用',
    export: '分享导出',
  })[source] || source || '文件'
}

/** 本场文件分组，方便用户理解来源 */
const filesByGroup = computed(() => {
  const ref = []
  const upload = []
  const generated = []
  for (const f of sessionFiles.value || []) {
    const src = String(f.source || '')
    if (src === 'resource_ref') ref.push(f)
    else if (src === 'upload') upload.push(f)
    else generated.push(f) // generated / export / 其它产物
  }
  return { ref, upload, generated }
})

function citationTitle(c) {
  const bits = [c.title || '资料']
  if (c.ocr || c.method === 'ocr') bits.push('OCR 识别')
  else if (c.fromCache) bits.push('缓存')
  else if (c.method === 'text_layer') bits.push('PDF 文字层')
  if (c.snippet) bits.push(String(c.snippet).slice(0, 120))
  return bits.join(' · ')
}

function formatTime(v) {
  if (!v) return ''
  const d = new Date(v)
  if (Number.isNaN(d.getTime())) return String(v)
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

function formatSize(n) {
  if (n == null) return ''
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / 1024 / 1024).toFixed(1)} MB`
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

function formatMarkdown(text, opts = {}) {
  return formatAssistantMarkdown(text, opts)
}

function scrollToBottom(force = false) {
  if (!force && !stickBottom.value) return
  nextTick(() => {
    const el = messagesRef.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

function onScroll() {
  const el = messagesRef.value
  if (!el) return
  stickBottom.value = el.scrollHeight - el.scrollTop - el.clientHeight < 80
}

function teamIdOf(t) {
  return Number(t.id || t.teamId)
}

function brainGoalLabel(goal) {
  const map = {
    answer: '对话',
    rewrite: '改稿',
    plan: '计划',
    score_review: '评分复盘',
    artifact: '生成产物',
    clarify: '补全意图',
  }
  return map[goal] || goal || '对话'
}

async function refreshSessions() {
  const params = { page: 0, size: 50 }
  if (sessionKeyword.value.trim()) params.keyword = sessionKeyword.value.trim()
  const res = await api.listSessions(params)
  sessions.value = res.data || []
}

function onSearchInput() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    refreshSessions().catch(() => {})
  }, 280)
}

async function refreshTeams() {
  try {
    const res = await api.listTeams()
    teams.value = res.data || []
  } catch {
    teams.value = []
  }
}

async function refreshMemories() {
  const res = await api.listMemories()
  memories.value = res.data || []
}

async function refreshFiles() {
  if (!activeSessionId.value) {
    sessionFiles.value = []
    return
  }
  const res = await api.listFiles(activeSessionId.value)
  sessionFiles.value = res.data || []
}

function linkParentUserMessageIds(list) {
  for (let i = 0; i < list.length; i += 1) {
    const msg = list[i]
    if (msg.role !== 'assistant') continue
    if (msg.parentUserMessageId) continue
    for (let j = i - 1; j >= 0; j -= 1) {
      if (list[j].role === 'user' && list[j].id) {
        msg.parentUserMessageId = list[j].id
        break
      }
    }
  }
  return list
}

function parseContentJson(raw) {
  if (!raw) return { citations: [], files: [] }
  try {
    const obj = typeof raw === 'string' ? JSON.parse(raw) : raw
    return {
      citations: Array.isArray(obj.citations) ? obj.citations : [],
      files: Array.isArray(obj.files)
        ? obj.files.map((f) => ({
            ...f,
            fileId: f.fileId || f.id,
            id: f.id || f.fileId,
          }))
        : [],
    }
  } catch {
    return { citations: [], files: [] }
  }
}

async function loadMessages(sessionId) {
  const res = await api.listMessages(sessionId, { limit: 100 })
  const list = (res.data || []).map((m) => {
    const parsed = parseContentJson(m.contentJson)
    return {
      ...m,
      id: m.id != null ? Number(m.id) : m.id,
      runId: m.runId != null ? Number(m.runId) : m.runId,
      steps: Array.isArray(m.steps) ? m.steps : [],
      citations: parsed.citations,
      files: parsed.files,
      thinkingText: m.thinkingText || '',
      contentText: m.contentText || '',
      live: !!m.live,
    }
  })
  messages.value = linkParentUserMessageIds(list)
  scrollToBottom(true)
}

/** 进入会话时：若有 streaming 消息，重连订阅实时进度 */
async function resumeLiveRuns() {
  const liveMsgs = messages.value.filter(
    (m) => m.role === 'assistant'
      && m.runId
      && (m.status === 'streaming' || m.status === 'pending' || m.live),
  )
  if (!liveMsgs.length) return

  // 只续订最新一条进行中的
  const last = liveMsgs[liveMsgs.length - 1]
  const sessionId = activeSessionId.value
  if (resumeAbort) {
    try { resumeAbort.abort() } catch { /* ignore */ }
  }
  resumeAbort = new AbortController()
  isResponding.value = true
  currentRunId = Number(last.runId)
  streamBoundSessionId = sessionId
  last.status = 'streaming'

  try {
    await api.subscribeRun(last.runId, {
      signal: resumeAbort.signal,
      onEvent: (event, data) => {
        if (!isStreamForActiveSession(sessionId)) return
        // 快照：整段替换当前态
        if (event === 'snapshot') {
          if (data.contentText != null) last.contentText = data.contentText || ''
          if (data.thinkingText != null) last.thinkingText = data.thinkingText || ''
          if (Array.isArray(data.steps)) last.steps = data.steps
          if (data.assistantMessageId != null) last.id = Number(data.assistantMessageId)
          if (data.userMessageId != null) last.parentUserMessageId = Number(data.userMessageId)
          if (data.status) last.status = data.status === 'running' ? 'streaming' : data.status
          if (data.intent) {
            handleStreamEvent('intent', data.intent, last)
          }
          scrollToBottom(true)
          return
        }
        handleStreamEvent(event, data, last)
      },
    })
  } catch (e) {
    if (e.name !== 'AbortError') {
      console.warn('resume live run failed', e)
    }
  } finally {
    if (String(streamBoundSessionId) === String(sessionId) && currentRunId === Number(last.runId)) {
      isResponding.value = false
      currentRunId = null
      streamBoundSessionId = null
    }
    // 结束后刷新一次，拿到落库的 files
    if (String(activeSessionId.value) === String(sessionId)) {
      await loadMessages(sessionId)
      await refreshFiles()
    }
  }
}

/**
 * 进入/切换会话。
 * @param {string|number} id
 * @param {{ soft?: boolean }} [opts] soft=true：刚创建的空会话，不拉历史、不打断即将发起的流式发送
 */
async function selectSession(id, opts = {}) {
  const soft = !!opts.soft
  const targetId = id
  const targetKey = String(targetId)
  const prevKey = activeSessionId.value != null ? String(activeSessionId.value) : null
  const switching = prevKey != null && prevKey !== targetKey

  // 切换到别的会话：断开本页流式/续订（服务端任务继续）
  if (switching || !soft) {
    stopClientStream({ keepResponding: soft && !switching })
  }

  const loadToken = ++sessionLoadSeq
  if (switching) {
    sessionSwitching.value = true
    // 先清空，避免旧会话内容闪进新会话
    messages.value = []
    sessionFiles.value = []
    chatKeyword.value = ''
  }
  if (!soft) sessionLoading.value = true

  activeSessionId.value = targetId
  // 仅窄屏抽屉模式：选中会话后自动收起列表
  if (typeof window !== 'undefined' && window.innerWidth < 960) {
    leftOpen.value = false
  }
  if (String(route.params.sessionId || '') !== targetKey) {
    await router.replace(`/assistant/c/${targetId}`)
  }

  try {
    const res = await api.getSession(targetId)
    if (loadToken !== sessionLoadSeq) return
    activeSession.value = res.data
    titleDraft.value = activeSession.value?.title || '新对话'
    boundTeamId.value = activeSession.value?.teamId ? Number(activeSession.value.teamId) : null

    if (!soft) {
      await loadMessages(targetId)
      if (loadToken !== sessionLoadSeq) return
      await refreshFiles()
      // 后台异步续订，不阻塞进入
      resumeLiveRuns().catch(() => {})
    } else {
      // 新建空会话：保持空消息列表，立刻可显示欢迎或随后被 sendText 填入
      if (!messages.value.length) {
        messages.value = []
      }
      sessionFiles.value = []
    }
  } catch (e) {
    if (loadToken === sessionLoadSeq) {
      ElMessage.error(e.message || '加载对话失败')
    }
  } finally {
    if (loadToken === sessionLoadSeq) {
      sessionLoading.value = false
      sessionSwitching.value = false
      nextTick(() => scrollToBottom(true))
    }
  }
}

/** 默认页发消息：创建会话并切 URL，但不拉空历史、不闪欢迎页 */
async function ensureSessionForSend() {
  if (activeSessionId.value) return activeSessionId.value
  const teamId = boundTeamId.value || (route.query.teamId ? Number(route.query.teamId) : undefined)
  const res = await api.createSession(teamId ? { teamId } : {})
  const s = res.data
  await refreshSessions()
  await selectSession(s.id, { soft: true })
  return s.id
}

async function onCreateSession() {
  const teamId = boundTeamId.value || (route.query.teamId ? Number(route.query.teamId) : undefined)
  const res = await api.createSession(teamId ? { teamId } : {})
  const s = res.data
  await refreshSessions()
  await selectSession(s.id, { soft: true })
}

async function quickStart(text) {
  await sendText(text)
}

async function saveTitle() {
  if (!activeSessionId.value || !titleDraft.value.trim()) return
  try {
    await api.patchSession(activeSessionId.value, { title: titleDraft.value.trim() })
    await refreshSessions()
  } catch (e) {
    ElMessage.error(e.message || '重命名失败')
  }
}

async function onBindTeam() {
  if (!activeSessionId.value) return
  try {
    await api.patchSession(activeSessionId.value, { teamId: boundTeamId.value })
    ElMessage.success(boundTeamId.value ? '已绑定团队' : '已取消绑定')
    const res = await api.getSession(activeSessionId.value)
    activeSession.value = res.data
  } catch (e) {
    ElMessage.error(e.message || '绑定失败')
  }
}

/** 中文/日文等 IME 正在选词时，Enter 用于上屏而非发送 */
const composerComposing = ref(false)

function onComposerCompositionStart() {
  composerComposing.value = true
}

function onComposerCompositionEnd() {
  // 部分浏览器 end 晚于 keydown，下一帧再清，避免误发
  requestAnimationFrame(() => {
    composerComposing.value = false
  })
}

function isImeComposing(e) {
  // 标准：KeyboardEvent.isComposing；部分环境 keyCode 229 表示 IME 处理中
  return Boolean(
    composerComposing.value
    || e.isComposing
    || e.keyCode === 229
    || e.which === 229,
  )
}

function onKeydown(e) {
  if (e.key !== 'Enter' && e.key !== 'NumpadEnter') return
  // 输入法选词/确认候选：不要发送
  if (isImeComposing(e)) return
  if (e.shiftKey) return // Shift+Enter 换行
  e.preventDefault()
  sendText(inputText.value)
}

async function onPickFiles(e) {
  const files = Array.from(e.target.files || [])
  e.target.value = ''
  if (!activeSessionId.value) {
    try {
      await ensureSessionForSend()
    } catch (err) {
      ElMessage.error(err.message || '创建会话失败')
      return
    }
  }
  for (const file of files) {
    try {
      const res = await api.uploadFile(activeSessionId.value, file)
      pendingFiles.value.push(res.data)
      await refreshFiles()
    } catch (err) {
      ElMessage.error(err.message || `上传失败：${file.name}`)
    }
  }
}

function removePending(id) {
  pendingFiles.value = pendingFiles.value.filter((f) => f.id !== id)
}

function removeSelectedResource(id) {
  selectedResources.value = selectedResources.value.filter((r) => r.id !== id)
}

async function openResourcePicker() {
  if (!boundTeamId.value) {
    ElMessage.warning('请先在顶栏选择团队')
    return
  }
  pickerOpen.value = true
  pickerLoading.value = true
  pickerChecked.value = selectedResources.value.map((r) => r.id)
  try {
    const res = await api.resourcePicker(boundTeamId.value)
    const data = res.data || {}
    pickerFiles.value = [...(data.teamFiles || []), ...(data.publicFiles || [])]
  } catch (e) {
    ElMessage.error(e.message || '加载资料失败')
    pickerFiles.value = []
  } finally {
    pickerLoading.value = false
  }
}

function confirmPicker() {
  const map = new Map(pickerFiles.value.map((f) => [f.id, f]))
  selectedResources.value = pickerChecked.value
    .map((id) => map.get(id))
    .filter(Boolean)
  pickerOpen.value = false
  if (selectedResources.value.length) {
    ElMessage.success(`已加入 ${selectedResources.value.length} 份参考资料`)
  }
}

async function sendText(text) {
  const content = (text || '').trim()
  if ((!content && !pendingFiles.value.length && !selectedResources.value.length) || isResponding.value) return
  // 防连点：进入后立即锁；并立刻退出欢迎态
  isResponding.value = true
  sessionSwitching.value = false
  sessionLoading.value = false

  let sessionId = activeSessionId.value
  if (!sessionId) {
    try {
      sessionId = await ensureSessionForSend()
    } catch (e) {
      isResponding.value = false
      ElMessage.error(e.message || '创建会话失败')
      return
    }
  }

  const userMsg = {
    _localId: `u-${Date.now()}`,
    role: 'user',
    contentText: content || '（见附件/资料）',
    status: 'completed',
  }
  const assistantMsg = {
    _localId: `a-${Date.now()}`,
    role: 'assistant',
    contentText: '',
    thinkingText: '',
    steps: [],
    citations: [],
    files: [],
    status: 'streaming',
  }
  messages.value.push(userMsg, assistantMsg)
  inputText.value = ''
  nextTick(() => {
    if (composerRef.value) {
      composerRef.value.style.height = 'auto'
    }
  })
  const attachmentFileIds = pendingFiles.value.map((f) => f.id)
  const resourceIds = selectedResources.value.map((r) => r.id)
  pendingFiles.value = []
  selectedResources.value = []
  stickBottom.value = true
  scrollToBottom(true)

  abortController = new AbortController()
  currentRunId = null
  streamBoundSessionId = sessionId

  try {
    await api.streamMessage(
      sessionId,
      {
        content: content || '请结合我选中的资料与附件进行分析和建议。',
        clientMessageId: crypto.randomUUID?.() || `${Date.now()}-${Math.random()}`,
        attachmentFileIds,
        resourceIds,
        teamId: boundTeamId.value || undefined,
      },
      {
        signal: abortController.signal,
        onEvent: (event, data) => {
          // 用户已切走会话：忽略过期流事件，避免串台
          if (!isStreamForActiveSession(sessionId)) return
          const last = messages.value[messages.value.length - 1]
          if (!last || last.role !== 'assistant') return
          handleStreamEvent(event, data, last)
        },
      }
    )
  } catch (e) {
    if (e.name !== 'AbortError') {
      if (isStreamForActiveSession(sessionId)) {
        const last = messages.value[messages.value.length - 1]
        if (last?.role === 'assistant') {
          last.errorMessage = e.message || '网络错误'
          last.status = 'failed'
        }
        ElMessage.error(e.message || '发送失败')
      }
    }
  } finally {
    if (String(streamBoundSessionId) === String(sessionId)) {
      isResponding.value = false
      abortController = null
      currentRunId = null
      streamBoundSessionId = null
    }
    await refreshSessions()
    if (isStreamForActiveSession(sessionId) || String(activeSessionId.value) === String(sessionId)) {
      await refreshFiles()
    }
  }
}

async function stopGeneration() {
  if (currentRunId) {
    try { await api.cancelRun(currentRunId) } catch { /* ignore */ }
  }
  abortController?.abort()
  isResponding.value = false
}

function findPrevUserMessageId(assistantMsg) {
  // 1) 流式/历史已挂载的父消息
  if (assistantMsg?.parentUserMessageId) {
    return Number(assistantMsg.parentUserMessageId)
  }

  // 2) 按数组位置往前找最近 user
  const idx = messages.value.findIndex((m) => (
    m === assistantMsg
    || (assistantMsg?._localId && m._localId === assistantMsg._localId)
    || (assistantMsg?.id != null && m.id != null && Number(m.id) === Number(assistantMsg.id))
  ))
  const start = idx >= 0 ? idx - 1 : messages.value.length - 1
  for (let i = start; i >= 0; i -= 1) {
    const m = messages.value[i]
    if (m.role === 'user' && m.id != null) {
      return Number(m.id)
    }
  }

  // 3) 同 runId 关联
  if (assistantMsg?.runId != null) {
    const sameRunUser = messages.value.find((m) => (
      m.role === 'user' && m.id != null && Number(m.runId) === Number(assistantMsg.runId)
    ))
    if (sameRunUser) return Number(sameRunUser.id)
  }

  // 4) 最后一条有 id 的用户消息
  for (let i = messages.value.length - 1; i >= 0; i -= 1) {
    if (messages.value[i].role === 'user' && messages.value[i].id != null) {
      return Number(messages.value[i].id)
    }
  }
  return null
}

function handleStreamEvent(event, data, last) {
  if (event === 'run_started') {
    currentRunId = data.runId
    last.id = data.assistantMessageId != null ? Number(data.assistantMessageId) : last.id
    last.runId = data.runId != null ? Number(data.runId) : last.runId
    last.status = 'streaming'
    if (data.userMessageId != null) {
      last.parentUserMessageId = Number(data.userMessageId)
      // 回写本轮用户消息 id（此前本地消息只有 _localId）
      for (let i = messages.value.length - 1; i >= 0; i -= 1) {
        const m = messages.value[i]
        if (m.role === 'user') {
          if (m.id == null) m.id = Number(data.userMessageId)
          m.runId = last.runId
          break
        }
      }
    }
  } else if (event === 'message_completed') {
    if (data.contentText != null) last.contentText = data.contentText
    if (Array.isArray(data.files) && data.files.length) {
      last.files = data.files.map((f) => ({
        ...f,
        fileId: f.fileId || f.id,
        id: f.id || f.fileId,
      }))
    }
    if (Array.isArray(data.citations)) last.citations = data.citations
    last.status = 'completed'
  } else if (event === 'run_completed') {
    last.status = data?.status === 'failed' ? 'failed' : (data?.status === 'cancelled' ? 'cancelled' : 'completed')
  } else if (event === 'intent') {
    last.intent = data || {}
    // 把假设/项目挂到步骤旁可读字段
    if (data?.assumptions?.length || data?.projectHint || data?.slots?.project_name) {
      last.brainHints = {
        project: data.projectHint || data.slots?.project_name || '',
        goal: data.goal || '',
        assumptions: data.assumptions || [],
        softIntent: !!data.softIntent,
      }
    }
  } else if (event === 'thinking_delta') {
    last.thinkingText = (last.thinkingText || '') + (data.text || '')
    scrollToBottom()
  } else if (event === 'content_delta') {
    last.contentText = (last.contentText || '') + (data.text || '')
    scrollToBottom()
  } else if (event === 'step_start') {
    last.steps = last.steps || []
    const existing = last.steps.find((s) => s.stepNo === data.stepNo && s.stepKey === data.stepKey)
    if (existing) {
      existing.title = data.title
      existing.status = 'running'
    } else {
      last.steps.push({
        stepNo: data.stepNo,
        stepKey: data.stepKey,
        title: data.title,
        status: 'running',
      })
    }
    scrollToBottom()
  } else if (event === 'step_end') {
    const step = (last.steps || []).find((s) => s.stepNo === data.stepNo)
    if (step) {
      step.status = data.status || 'completed'
      step.outputSummary = data.outputSummary
      if (data.outputSummary) step.title = step.title || data.outputSummary
    }
  } else if (event === 'ocr_progress') {
    last.steps = last.steps || []
    let step = last.steps.find((s) => s.stepKey === 'extract' || s.stepNo === 0)
    const label = data.label || (
      data.phase === 'ocr' && data.page && Number(data.page) > 0
        ? `正在 OCR 第 ${data.page}/${data.total || '?'} 页${data.title ? ` · ${data.title}` : ''}`
        : data.phase === 'text_layer'
          ? `文字层解析（无需 OCR）${data.title ? ` · ${data.title}` : ''}`
          : data.phase === 'cache'
            ? (data.label || '命中资料缓存')
            : `解析资料中${data.title ? ` · ${data.title}` : ''}`
    )
    if (!step) {
      step = {
        stepNo: 0,
        stepKey: 'extract',
        title: label,
        status: 'running',
      }
      last.steps.unshift(step)
    } else {
      step.title = label
      step.status = data.phase === 'cache' || data.phase === 'text_layer' || data.phase === 'ocr' || data.phase === 'done'
        ? (data.phase === 'ocr' && Number(data.page) > 0 ? 'running' : step.status)
        : 'running'
      if (data.phase === 'ocr' && Number(data.page) > 0) step.status = 'running'
    }
    // 额外保留一条 OCR 明细，避免被覆盖后看不见
    if (data.phase === 'ocr' && Number(data.page) > 0) {
      last.ocrLogs = last.ocrLogs || []
      last.ocrLogs.push(label)
      // 只保留最近 12 条
      if (last.ocrLogs.length > 12) last.ocrLogs = last.ocrLogs.slice(-12)
    }
    scrollToBottom()
  } else if (event === 'citation') {
    last.citations = last.citations || []
    last.citations.push(data)
  } else if (event === 'file' || event === 'artifact') {
    last.files = last.files || []
    last.files.push(data)
    refreshFiles()
  } else if (event === 'error') {
    last.errorMessage = data.message || '生成失败'
    last.status = 'failed'
  } else if (event === 'action_proposal') {
    last.actionProposals = last.actionProposals || []
    const id = data.proposalId
    if (id != null && !last.actionProposals.some((p) => String(p.proposalId) === String(id))) {
      last.actionProposals.push({
        proposalId: id,
        actionType: data.actionType,
        title: data.title,
        summary: data.summary,
        args: data.args,
        confirmLabel: data.confirmLabel || '确认执行',
        cancelLabel: data.cancelLabel || '取消',
        status: data.status || 'pending',
        expiresAt: data.expiresAt,
        resultMessage: '',
        _busy: false,
      })
    }
    scrollToBottom()
  } else if (event === 'message_completed') {
    last.contentText = data.contentText ?? last.contentText
    last.status = 'completed'
    if (Array.isArray(data.citations) && data.citations.length) {
      last.citations = data.citations
    }
    if (Array.isArray(data.files) && data.files.length) {
      last.files = data.files.map((f) => ({
        ...f,
        fileId: f.fileId || f.id,
        id: f.id || f.fileId,
      }))
    }
  } else if (event === 'run_completed') {
    last.status = data.status === 'completed' ? 'completed' : data.status
  }
}

async function regenerateFrom(assistantMsg) {
  if (!activeSessionId.value || isResponding.value) return

  let userMessageId = findPrevUserMessageId(assistantMsg)
  // 若当前列表缺 id（例如异常中断），先从服务端重拉再解析
  if (!userMessageId) {
    try {
      await loadMessages(activeSessionId.value)
      // 用 id/_localId 重新定位当前助手消息
      const refreshed = messages.value.find((m) => (
        (assistantMsg?.id != null && Number(m.id) === Number(assistantMsg.id))
        || (assistantMsg?._localId && m._localId === assistantMsg._localId)
      )) || assistantMsg
      userMessageId = findPrevUserMessageId(refreshed)
    } catch {
      /* ignore */
    }
  }
  if (!userMessageId) {
    ElMessage.warning('找不到对应的用户消息，请重新发送问题')
    return
  }

  const newAssistant = {
    _localId: `a-regen-${Date.now()}`,
    role: 'assistant',
    contentText: '',
    thinkingText: '',
    steps: [],
    citations: [],
    files: [],
    status: 'streaming',
    parentUserMessageId: userMessageId,
  }
  const sessionId = activeSessionId.value
  messages.value.push(newAssistant)
  isResponding.value = true
  stickBottom.value = true
  scrollToBottom(true)
  abortController = new AbortController()
  currentRunId = null
  streamBoundSessionId = sessionId

  try {
    await api.regenerateMessage(sessionId, userMessageId, {
      signal: abortController.signal,
      onEvent: (event, data) => {
        if (!isStreamForActiveSession(sessionId)) return
        const last = messages.value[messages.value.length - 1]
        if (!last || last.role !== 'assistant') return
        handleStreamEvent(event, data, last)
      },
    })
  } catch (e) {
    if (e.name !== 'AbortError') {
      if (isStreamForActiveSession(sessionId)) {
        const last = messages.value[messages.value.length - 1]
        if (last?.role === 'assistant') {
          last.errorMessage = e.message || '重新生成失败'
          last.status = 'failed'
        }
        ElMessage.error(e.message || '重新生成失败')
      }
    }
  } finally {
    if (String(streamBoundSessionId) === String(sessionId)) {
      isResponding.value = false
      abortController = null
      currentRunId = null
      streamBoundSessionId = null
    }
    await refreshSessions()
    if (String(activeSessionId.value) === String(sessionId)) {
      await refreshFiles()
    }
  }
}

async function togglePin(session) {
  try {
    const next = !(session.pin === 1 || session.pin === true)
    await api.patchSession(session.id, { pin: next })
    await refreshSessions()
  } catch (e) {
    ElMessage.error(e.message || '置顶失败')
  }
}

async function removeSession(id) {
  try {
    await ElMessageBox.confirm('删除后可从列表消失（软删除）。确定删除这条对话吗？', '删除对话', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    await api.deleteSession(id)
    if (String(activeSessionId.value) === String(id)) {
      activeSessionId.value = null
      activeSession.value = null
      messages.value = []
      sessionFiles.value = []
      router.replace('/assistant')
    }
    await refreshSessions()
    ElMessage.success('对话已删除')
  } catch (e) {
    ElMessage.error(e.message || '删除失败')
  }
}

function openShare() {
  if (!activeSessionId.value) return
  shareTeamId.value = boundTeamId.value || (teams.value[0] ? teamIdOf(teams.value[0]) : null)
  shareMode.value = 'summary'
  shareOpen.value = true
}

async function confirmShare() {
  if (!shareTeamId.value) {
    ElMessage.warning('请选择团队')
    return
  }
  shareBusy.value = true
  try {
    const res = await api.shareSession(activeSessionId.value, {
      teamId: Number(shareTeamId.value),
      shareMode: shareMode.value,
      includeThinking: false,
      makeSearchable: false,
      folderKey: 'content',
    })
    ElMessage.success(res.data?.resourceId ? `已分享到资源中心 #${res.data.resourceId}` : '已分享')
    shareOpen.value = false
  } catch (e) {
    ElMessage.error(e.message || '分享失败')
  } finally {
    shareBusy.value = false
  }
}

async function saveFileToTeam(fileId) {
  const teamId = boundTeamId.value || shareTeamId.value
  if (!teamId) {
    if (!teams.value.length) {
      ElMessage.warning('你还没有团队，无法保存到资源中心')
      return
    }
    // use first team as default after confirm via message
    const t = teams.value[0]
    try {
      await api.saveFileToResource(fileId, { teamId: teamIdOf(t), folderKey: 'content' })
      ElMessage.success(`已保存到团队「${t.name || t.teamName || teamIdOf(t)}」资源中心`)
      await refreshFiles()
    } catch (e) {
      ElMessage.error(e.message || '保存失败')
    }
    return
  }
  try {
    await api.saveFileToResource(fileId, { teamId: Number(teamId), folderKey: 'content' })
    ElMessage.success('已保存到资源中心')
    await refreshFiles()
  } catch (e) {
    ElMessage.error(e.message || '保存失败')
  }
}

async function saveMessageAsFile(msg, format = 'md') {
  if (!activeSessionId.value || !msg.contentText) return
  const extMap = { docx: 'docx', pdf: 'pdf', pptx: 'pptx', ppt: 'pptx', md: 'md' }
  const ext = extMap[format] || 'md'
  const tipMap = {
    docx: '正在生成 Word…',
    pdf: '正在生成 PDF…',
    pptx: '正在生成 PPT…',
    md: '正在保存…',
  }
  try {
    ElMessage.info(tipMap[ext] || '正在保存…')
    const res = await api.saveReply(activeSessionId.value, {
      content: msg.contentText,
      format: ext === 'pptx' ? 'pptx' : format,
      fileName: `助手回复-${Date.now()}.${ext}`,
      title: activeSession.value?.title || '小启AI文稿',
      saveToTeam: false,
    })
    ElMessage.success(`已保存为 ${ext.toUpperCase()}，可在右侧下载`)
    await refreshFiles()
    if (res.data?.id) {
      msg.files = msg.files || []
      msg.files.push({ fileId: res.data.id, id: res.data.id, name: res.data.name })
    }
  } catch (e) {
    ElMessage.error(e.message || '保存失败')
  }
}

async function exportPdf() {
  if (!activeSessionId.value || exportBusy.value) return
  exportBusy.value = true
  try {
    ElMessage.info('正在导出整段对话 PDF…')
    const res = await api.exportSessionPdf(activeSessionId.value)
    ElMessage.success('已导出 PDF，可在右侧「资料」下载')
    await refreshFiles()
    rightTab.value = 'files'
    rightOpen.value = true
    if (res.data?.id) {
      window.open(fileDownloadUrl(res.data.id), '_blank')
    }
  } catch (e) {
    ElMessage.error(e.message || '导出失败')
  } finally {
    exportBusy.value = false
  }
}

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制')
  } catch {
    ElMessage.error('复制失败')
  }
}

function actionStatusLabel(status) {
  return ({
    pending: '待确认',
    confirmed: '已执行',
    rejected: '已取消',
    expired: '已过期',
    failed: '失败',
  })[status] || '待确认'
}

async function confirmActionProposal(msg, ap) {
  if (!ap?.proposalId || ap._busy) return
  ap._busy = true
  try {
    const res = await api.confirmAction(ap.proposalId)
    ap.status = 'confirmed'
    ap.resultMessage = res.data?.message || '操作已完成'
    ElMessage.success(ap.resultMessage)
  } catch (e) {
    ap.status = 'failed'
    ap.resultMessage = e.message || '执行失败'
    ElMessage.error(ap.resultMessage)
  } finally {
    ap._busy = false
  }
}

async function rejectActionProposal(msg, ap) {
  if (!ap?.proposalId || ap._busy) return
  ap._busy = true
  try {
    const res = await api.rejectAction(ap.proposalId)
    ap.status = 'rejected'
    ap.resultMessage = res.data?.message || '已取消'
    ElMessage.info(ap.resultMessage)
  } catch (e) {
    ElMessage.error(e.message || '取消失败')
  } finally {
    ap._busy = false
  }
}

function inferMemoryType(content) {
  if (/项目|赛道|定位|产品|方案/.test(content)) return 'project_focus'
  if (/本周|重点|目标|训练|改进/.test(content)) return 'goal'
  if (/口语|风格|语速|书面|催交|批改|口径|反馈/.test(content)) return 'style'
  if (/希望|偏好|喜欢|不要/.test(content)) return 'preference'
  return 'manual'
}

async function addMemory() {
  const content = memoryDraft.value.trim()
  if (!content) {
    ElMessage.warning('先写一句希望助手记住的内容')
    return
  }
  try {
    await api.createMemory({ content, memoryType: inferMemoryType(content) })
    memoryDraft.value = ''
    await refreshMemories()
    ElMessage.success('已记住，之后新对话也会参考')
  } catch (e) {
    ElMessage.error(e.message || '添加失败')
  }
}

async function removeMemory(id) {
  await api.deleteMemory(id)
  await refreshMemories()
  ElMessage.success('已取消记住')
}

watch(
  () => route.params.sessionId,
  async (id, prev) => {
    // 同组件内路由变化（稳定 key 后必经此路径）
    if (id && String(id) !== String(activeSessionId.value)) {
      await selectSession(id)
      return
    }
    // 回到默认落地页 /assistant（例如删除当前会话）
    if (!id && prev && activeSessionId.value) {
      // removeSession 已清状态时不要重复清
      if (String(activeSessionId.value) === String(prev)) {
        stopClientStream()
        activeSessionId.value = null
        activeSession.value = null
        messages.value = []
        sessionFiles.value = []
        titleDraft.value = ''
      }
    }
  }
)

onMounted(async () => {
  await Promise.all([refreshSessions(), refreshMemories(), refreshTeams()])
  if (route.params.sessionId) {
    await selectSession(route.params.sessionId)
  } else if (route.query.teamId) {
    boundTeamId.value = Number(route.query.teamId)
  }
})

onUnmounted(() => {
  stopClientStream()
})
</script>
