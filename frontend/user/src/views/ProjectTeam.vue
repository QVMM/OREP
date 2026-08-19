<template>
  <div class="team-page team-console-page task-management-page">
    <div class="team-grid" aria-hidden="true"></div>

    <section v-if="loading" class="console-state">
      <strong>正在同步任务</strong>
      <span>读取当前项目、任务、负责人和提交状态。</span>
    </section>

    <section v-else-if="teamLoadError" class="console-state warning">
      <strong>任务数据加载失败</strong>
      <span>{{ teamLoadError }}</span>
      <button type="button" @click="fetchTeams">重新加载</button>
    </section>

    <section v-else-if="!dashboard" class="console-state">
      <strong>{{ canCreateProjectFromUser ? '暂无可管理项目' : '暂无任务' }}</strong>
      <span>{{ canCreateProjectFromUser ? '创建项目后，可在任务管理中统一分配和跟进任务。' : '你还没有加入项目，请联系老师或队长分配任务。' }}</span>
      <button v-if="canCreateProjectFromUser" type="button" @click="openProjectDialog">创建项目</button>
    </section>

    <section v-else-if="isTaskDetailRoute" class="student-page project-task-detail-page">
      <header class="student-page__head project-task-detail-head">
        <div>
          <h1>任务详情</h1>
          <p v-if="detailWorkItem">{{ team.name || '当前项目' }} · {{ detailWorkItem.sourceLabel }} · {{ detailWorkItem.stageLabel }}</p>
          <p v-else>{{ team.name || '当前项目' }} · 查看任务内容与提交记录</p>
        </div>
        <div class="project-task-detail-head-actions">
          <button type="button" class="project-task-back" @click="goBackToTaskList">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m15 18-6-6 6-6"/></svg>
            返回任务管理
          </button>
          <button
            v-for="action in detailWorkItem ? detailPageActions(detailWorkItem) : []"
            :key="`${detailWorkItem.id}-page-${action.key}`"
            type="button"
            :class="['project-task-head-action', action.kind]"
            @click="runWorkItemAction(detailWorkItem, action.key)"
          >
            {{ action.label }}
          </button>
        </div>
      </header>

      <section v-if="!detailWorkItem" class="student-card project-task-not-found">
        <strong>没有找到这项任务</strong>
        <p>任务可能已经被调整，返回任务管理查看最新列表。</p>
        <button type="button" @click="goBackToTaskList">返回任务管理</button>
      </section>

      <template v-else>
        <section class="project-task-detail-layout">
          <main class="project-task-detail-main">
            <section class="project-task-section project-task-description">
              <header>
                <span aria-hidden="true"></span>
                <div><h2>任务书</h2></div>
              </header>
              <div class="project-task-section-body">
                <div class="project-task-detail-tags">
                  <span>{{ detailWorkItem.sourceLabel }}</span>
                  <b :class="{ warning: isActionablyOverdue(detailWorkItem) || detailWorkItem.status === 'CHANGES_REQUESTED' }">{{ focusedTaskStatusLabel(detailWorkItem) }}</b>
                </div>
                <div class="project-task-title-block">
                  <span>任务主题</span>
                  <h3>{{ detailWorkItem.title }}</h3>
                </div>
                <section class="project-task-book-summary">
                  <h4>任务概要</h4>
                  <p>{{ detailTaskBook.summary || detailWorkItem.summary || '暂无任务说明' }}</p>
                </section>
                <button
                  type="button"
                  class="project-task-book-toggle"
                  :aria-expanded="detailTaskBookExpanded"
                  aria-controls="projectTaskBookDetails"
                  @click="toggleDetailTaskBook"
                >
                  <span>
                    <strong>{{ detailTaskBookExpanded ? '收起完整任务书' : '展开完整任务书' }}</strong>
                    <small>正式任务描述、交付要求与任务附件</small>
                  </span>
                  <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m8 10 4 4 4-4" /></svg>
                </button>
                <div v-if="detailTaskBookExpanded" id="projectTaskBookDetails" class="project-task-book-details">
                  <div v-if="detailTaskBookLoading" class="project-task-book-state">正在加载完整任务书...</div>
                  <div v-else-if="detailTaskBookError" class="project-task-book-state error">
                    <span>{{ detailTaskBookError }}</span>
                    <button type="button" @click="fetchDetailTaskBook">重新加载</button>
                  </div>
                  <template v-else>
                    <section v-if="detailTaskBookHtml" class="project-task-book-section">
                      <h4>正式任务描述</h4>
                      <div class="project-task-rich-content" v-html="detailTaskBookHtml"></div>
                    </section>
                    <section v-if="detailTaskBookRequirements.length" class="project-task-book-section">
                      <h4>交付要求</h4>
                      <div class="project-task-requirements" aria-label="交付要求">
                        <article v-for="item in detailTaskBookRequirements" :key="item.id">
                          <span :class="{ optional: !Boolean(item.required) }" aria-hidden="true"></span>
                          <div>
                            <strong>{{ item.title }}</strong>
                            <p v-if="item.description">{{ item.description }}</p>
                          </div>
                          <em>{{ Boolean(item.required) ? '必交' : '可选' }}</em>
                        </article>
                      </div>
                    </section>
                    <section v-if="detailTaskBookAttachments.length" class="project-task-book-section">
                      <h4>任务附件</h4>
                      <div class="project-task-attachment-list">
                        <article v-for="attachment in detailTaskBookAttachments" :key="attachment.id">
                          <i>{{ fileKindLabel(attachment) }}</i>
                          <div>
                            <strong>{{ attachment.fileName || '任务附件' }}</strong>
                            <small>{{ formatFileSize(attachment.fileSize || 0) }}</small>
                          </div>
                          <span>
                            <button type="button" @click="previewAttachment(attachment)">预览</button>
                            <a :href="attachmentUrl(attachment)" target="_blank" rel="noopener noreferrer" download>下载</a>
                          </span>
                        </article>
                      </div>
                    </section>
                  </template>
                  <div v-if="detailWorkItem.isTrainingTask" class="project-task-context-note">
                    <strong>训练营实操任务</strong>
                    <span>任务要求来自训练营，提交与审核记录统一沉淀在协作任务中。</span>
                  </div>
                  <div v-else-if="taskSourceKey(detailWorkItem) === 'SCORE'" class="project-task-context-note score">
                    <strong>评分改进项</strong>
                    <span>该事项来自路演评分或复盘建议，可拆分为团队任务继续推进。</span>
                  </div>
                </div>
              </div>
            </section>

            <section v-if="detailTask" class="project-task-section project-task-submissions">
              <header>
                <span aria-hidden="true"></span>
                <div>
                  <h2>最新提交</h2>
                  <p>{{ detailLatestSubmission ? `当前为 V${detailLatestSubmission.versionNo || 1}，历史版本默认收起` : '提交成果后，每次修改都会保存为新版本' }}</p>
                </div>
              </header>
              <div class="project-task-section-body">
                <article
                  v-if="detailLatestSubmission"
                  class="project-submission-card"
                  :class="{ focused: isFocusedSubmission(detailLatestSubmission) }"
                >
                  <div class="project-submission-head">
                    <div>
                      <span>V{{ detailLatestSubmission.versionNo || 1 }}</span>
                      <b>{{ submissionTypeLabel(detailLatestSubmission.submissionType) }}</b>
                      <em v-if="isFocusedSubmission(detailLatestSubmission)">本次查看</em>
                      <em v-else class="latest">最新版本</em>
                    </div>
                    <strong>{{ materialStatusText(detailLatestSubmission.status) }}</strong>
                  </div>
                  <div class="project-submission-copy">
                    <span>提交说明</span>
                    <p>{{ detailLatestSubmission.content || '本次提交未填写说明。' }}</p>
                  </div>
                  <div class="project-submission-meta">
                    <span>{{ detailLatestSubmission.submitterName || '提交人' }}</span>
                    <span>{{ formatDate(detailLatestSubmission.createdAt) }}</span>
                  </div>
                  <div v-if="detailLatestSubmission.reviewComment" class="project-submission-review">
                    <span>审核意见</span>
                    <p>{{ detailLatestSubmission.reviewComment }}</p>
                  </div>
                  <div v-if="submissionAssets(detailLatestSubmission).length" class="project-submission-resource-block">
                    <span>成果文件 · {{ submissionAssets(detailLatestSubmission).length }}</span>
                    <div class="project-submission-file-list">
                      <div v-for="asset in submissionAssets(detailLatestSubmission)" :key="asset.id || asset.fileUrl" class="project-submission-file">
                        <div>
                          <i>{{ fileKindLabel(asset) }}</i>
                          <span><strong>{{ asset.fileName || '成果文件' }}</strong><small>{{ formatFileSize(asset.fileSize || 0) }}</small></span>
                        </div>
                        <div>
                          <button type="button" @click="previewAttachment(asset)">预览</button>
                          <a :href="attachmentUrl(asset)" target="_blank" rel="noopener noreferrer" download>下载</a>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div v-if="recordSubmissionLinks(detailLatestSubmission).length" class="project-submission-resource-block">
                    <span>成果链接 · {{ recordSubmissionLinks(detailLatestSubmission).length }}</span>
                    <div class="project-submission-link-list">
                      <a v-for="link in recordSubmissionLinks(detailLatestSubmission)" :key="link.id || link.url" :href="link.url" target="_blank" rel="noopener noreferrer">
                        <strong>{{ link.title || '成果链接' }}</strong><span>打开链接</span>
                      </a>
                    </div>
                  </div>
                </article>

                <div v-else class="project-task-empty-submission">
                  <strong>还没有提交记录</strong>
                  <p>提交第一个版本后，说明、文件和审核状态会显示在这里。</p>
                </div>

                <div v-if="canSubmitTask(detailTask)" class="project-submission-primary-action">
                  <button v-if="!detailSubmissionEditorOpen" type="button" @click="openDetailSubmissionEditor">
                    {{ detailLatestSubmission ? '编辑并重新提交' : '提交第一个版本' }}
                  </button>
                  <span v-if="!detailSubmissionEditorOpen">每次提交都会生成新版本，历史内容不会被覆盖。</span>
                </div>

                <form v-if="detailSubmissionEditorOpen && canSubmitTask(detailTask)" class="project-version-editor" @submit.prevent="submitDetailVersion">
                  <header>
                    <div>
                      <span>新版本</span>
                      <h3>提交 V{{ nextDetailVersionNo }}</h3>
                      <p>已自动带入最新版本，你可以修改说明、移除旧文件或追加新文件。</p>
                    </div>
                    <button type="button" @click="closeDetailSubmissionEditor">取消编辑</button>
                  </header>

                  <label class="project-version-field">
                    <span>提交说明</span>
                    <textarea v-model="submissionDrafts[detailTask.id]" rows="6" placeholder="说明本次修改了什么，以及需要老师重点查看的内容"></textarea>
                  </label>

                  <section class="project-version-resources">
                    <header><div><strong>成果文件</strong><span>保留的旧文件和新文件会一起写入新版本</span></div></header>
                    <div v-if="retainedSubmissionAssets(detailTask.id).length" class="project-version-file-list">
                      <div v-for="asset in retainedSubmissionAssets(detailTask.id)" :key="`retained-${asset.id || asset.fileUrl}`" class="project-version-file retained">
                        <div><i>{{ fileKindLabel(asset) }}</i><span><strong>{{ asset.fileName || '成果文件' }}</strong><small>保留自 V{{ detailLatestSubmission?.versionNo || 1 }} · {{ formatFileSize(asset.fileSize || 0) }}</small></span></div>
                        <button type="button" @click="removeRetainedSubmissionAsset(detailTask.id, asset)">从新版本移除</button>
                      </div>
                    </div>
                    <div v-if="taskSubmissionFiles(detailTask.id).length" class="project-version-file-list">
                      <div v-for="file in taskSubmissionFiles(detailTask.id)" :key="file.id" class="project-version-file added">
                        <div><i>{{ fileKindLabel(file) }}</i><span><strong>{{ file.name }}</strong><small>新添加 · {{ formatFileSize(file.size) }}</small></span></div>
                        <button type="button" @click="removeTaskFile(detailTask.id, file.id)">移除</button>
                      </div>
                    </div>
                    <DropFileUpload
                      :key="`detail-upload-${detailTask.id}-${taskUploadNonce[detailTask.id] || 0}`"
                      multiple
                      size="sm"
                      title="拖拽成果文件到此处，或点击添加"
                      hint="支持一次选择多个文件"
                      @change="(files) => addTaskFilesFromDrop(detailTask, files)"
                    />
                  </section>

                  <section class="project-version-resources">
                    <header>
                      <div><strong>成果链接</strong><span>仓库、网盘、在线文档、演示或视频地址</span></div>
                      <button type="button" @click="addSubmissionLink(detailTask.id)">添加链接</button>
                    </header>
                    <div v-if="ensureSubmissionLinks(detailTask.id).length" class="project-version-link-editor">
                      <div v-for="(link, index) in ensureSubmissionLinks(detailTask.id)" :key="index">
                        <select v-model="link.linkType" aria-label="链接类型">
                          <option v-for="type in submissionLinkTypeOptions" :key="type.key" :value="type.key">{{ type.label }}</option>
                        </select>
                        <input v-model="link.title" placeholder="链接标题" />
                        <input v-model="link.url" placeholder="https://..." />
                        <button type="button" @click="removeSubmissionLink(detailTask.id, index)">移除</button>
                      </div>
                    </div>
                    <p v-else class="project-version-empty-hint">暂未添加成果链接。</p>
                  </section>

                  <footer>
                    <span>提交后将生成 V{{ nextDetailVersionNo }}，V{{ detailLatestSubmission?.versionNo || 0 }} 及更早版本保持不变。</span>
                    <div><button type="button" @click="closeDetailSubmissionEditor">取消</button><button class="primary" type="submit" :disabled="submissionUploading[detailTask.id]">{{ submissionUploading[detailTask.id] ? '正在提交' : `提交 V${nextDetailVersionNo}` }}</button></div>
                  </footer>
                </form>

                <section v-if="detailHistoricalSubmissions.length" class="project-submission-history">
                  <button type="button" class="project-history-toggle" :aria-expanded="detailHistoryExpanded" @click="detailHistoryExpanded = !detailHistoryExpanded">
                    <span><strong>历史版本</strong><small>共 {{ detailHistoricalSubmissions.length }} 个旧版本</small></span>
                    <b>{{ detailHistoryExpanded ? '收起历史版本' : '查看历史版本' }}</b>
                  </button>
                  <div v-if="detailHistoryExpanded" class="project-history-list">
                    <article v-for="item in detailHistoricalSubmissions" :key="item.id" class="project-history-card">
                      <header><div><strong>V{{ item.versionNo || 1 }}</strong><span>{{ materialStatusText(item.status) }}</span></div><time>{{ formatDate(item.createdAt) }}</time></header>
                      <div class="project-history-content"><span>提交说明</span><p>{{ item.content || '本次提交未填写说明。' }}</p></div>
                      <div v-if="item.reviewComment" class="project-submission-review"><span>审核意见</span><p>{{ item.reviewComment }}</p></div>
                      <div v-if="submissionAssets(item).length" class="project-submission-file-list compact">
                        <div v-for="asset in submissionAssets(item)" :key="asset.id || asset.fileUrl" class="project-submission-file">
                          <div><i>{{ fileKindLabel(asset) }}</i><span><strong>{{ asset.fileName || '成果文件' }}</strong><small>{{ formatFileSize(asset.fileSize || 0) }}</small></span></div>
                          <div><button type="button" @click="previewAttachment(asset)">预览</button><a :href="attachmentUrl(asset)" target="_blank" rel="noopener noreferrer" download>下载</a></div>
                        </div>
                      </div>
                      <div v-if="recordSubmissionLinks(item).length" class="project-submission-link-list compact">
                        <a v-for="link in recordSubmissionLinks(item)" :key="link.id || link.url" :href="link.url" target="_blank" rel="noopener noreferrer"><strong>{{ link.title || link.url }}</strong><span>打开</span></a>
                      </div>
                    </article>
                  </div>
                </section>
              </div>
            </section>
          </main>

          <aside class="project-task-detail-aside">
            <section>
              <h2>任务信息</h2>
              <dl>
                <div><dt>负责人</dt><dd>{{ detailWorkItem.ownerName || '未分配' }}</dd></div>
                <div><dt>截止时间</dt><dd>{{ formatDate(detailWorkItem.dueAt) }}</dd></div>
                <div><dt>任务类型</dt><dd>{{ detailWorkItem.taskTypeLabel || detailWorkItem.typeLabel }}</dd></div>
                <div><dt>优先级</dt><dd>{{ priorityText(detailWorkItem.priority) }}</dd></div>
                <div><dt>所在阶段</dt><dd>{{ detailWorkItem.stageLabel }}</dd></div>
                <div><dt>任务来源</dt><dd>{{ detailWorkItem.sourceMeta || detailWorkItem.sourceLabel }}</dd></div>
              </dl>
            </section>
            <section v-if="detailTask" class="project-task-version-summary">
              <span>提交版本</span>
              <strong>{{ detailTaskSubmissions.length }}</strong>
              <p>{{ detailLatestSubmission ? `最新状态：${taskStatusText(detailLatestSubmission.status)}` : '尚未提交成果' }}</p>
            </section>
          </aside>
        </section>
      </template>
    </section>

    <section v-else class="student-page task-management-shell task-learning-layout focused-task-shell">
      <header class="task-management-hero">
        <div class="task-hero-copy">
          <h1>任务管理</h1>
          <p>集中处理训练营任务与团队协作事项，任务来源和处理状态一目了然。</p>
        </div>
        <div class="task-hero-actions">
          <div v-if="teams.length > 1" ref="taskSwitcherRef" class="task-team-switcher">
            <button type="button" :class="{ active: projectSwitcherOpen }" @click="projectSwitcherOpen = !projectSwitcherOpen">{{ team.name || '切换项目' }}</button>
            <Transition name="project-switch-pop">
              <div v-if="projectSwitcherOpen" class="project-switch-menu">
                <button
                  v-for="item in teams"
                  :key="item.id"
                  type="button"
                  :class="{ active: item.id === selectedTeamId }"
                  @click="selectTeamFromSwitcher(item.id)"
                >
                  <span>{{ item.name }}</span>
                  <em v-if="item.id === selectedTeamId">当前</em>
                </button>
              </div>
            </Transition>
          </div>
          <button v-if="canAssignTask" type="button" class="task-primary-btn" @click="openTaskDialog">新建任务</button>
        </div>
      </header>

      <section class="focused-task-overview" aria-label="任务概览">
        <div v-for="metric in focusedTaskMetrics" :key="metric.key" class="focused-task-metric">
          <strong>{{ metric.value }}</strong>
          <span>{{ metric.label }}</span>
        </div>
        <p>{{ focusedTaskGuide }}</p>
      </section>

      <section class="focused-task-layout">
        <main class="focused-task-queue">
          <div class="focused-task-toolbar">
            <div>
              <h2>任务队列</h2>
              <p>按处理优先级排列，完成一项再推进下一项。</p>
            </div>
            <label class="focused-task-search">
              <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="6.5"/><path d="m16 16 4 4"/></svg>
              <input v-model.trim="focusedTaskKeyword" type="search" placeholder="搜索任务、负责人" aria-label="搜索任务" />
            </label>
          </div>

          <nav class="focused-source-filters" aria-label="按任务来源筛选">
            <button
              v-for="filter in focusedTaskSourceFilters"
              :key="filter.key"
              type="button"
              :class="{ active: focusedTaskSourceFilter === filter.key }"
              :aria-pressed="focusedTaskSourceFilter === filter.key"
              @click="focusedTaskSourceFilter = filter.key"
            >
              <span>{{ filter.label }}</span>
              <em>{{ filter.count }}</em>
            </button>
          </nav>

          <div v-if="focusedTaskGroups.length" class="focused-task-groups">
            <section v-for="group in focusedTaskGroups" :key="group.key" class="focused-task-group">
              <header>
                <div>
                  <span :class="['focused-group-dot', group.tone]"></span>
                  <h3>{{ group.label }}</h3>
                  <b>{{ group.items.length }}</b>
                </div>
                <p>{{ group.hint }}</p>
              </header>

              <div class="focused-task-list">
                <button
                  v-for="item in group.items"
                  :key="item.id"
                  type="button"
                  class="focused-task-row"
                  :class="{
                    overdue: isActionablyOverdue(item),
                    completed: isCompletedWorkItem(item),
                    locked: isLockedWorkItem(item)
                  }"
                  :aria-disabled="isLockedWorkItem(item) ? 'true' : 'false'"
                  @click="openFocusedTaskDetail(item)"
                >
                  <span :class="['focused-source-icon', `source-${taskSourceKey(item).toLowerCase()}`, { locked: isLockedWorkItem(item) }]">
                    <template v-if="isLockedWorkItem(item)">
                      <svg viewBox="0 0 24 24" aria-hidden="true" class="focused-lock-icon"><rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/></svg>
                    </template>
                    <template v-else>{{ item.badge }}</template>
                  </span>
                  <span class="focused-task-main">
                    <span class="focused-task-labels">
                      <em>{{ item.sourceLabel }}</em>
                      <i v-if="item.priority === 'HIGH' && !isCompletedWorkItem(item) && !isLockedWorkItem(item)">高优先级</i>
                    </span>
                    <strong>{{ item.title }}</strong>
                    <small>{{ item.summary || '暂无任务说明' }}</small>
                  </span>
                  <span class="focused-task-owner">
                    <small>负责人</small>
                    <strong>{{ item.ownerName || '未分配' }}</strong>
                  </span>
                  <span class="focused-task-due">
                    <small>{{ isLockedWorkItem(item) ? '开放时间' : (isActionablyOverdue(item) ? '已超期' : '截止时间') }}</small>
                    <strong>{{ isLockedWorkItem(item) ? lockedUnlockLabel(item) : formatShortDate(item.dueAt) }}</strong>
                  </span>
                  <span :class="['focused-task-status', {
                    warning: isActionablyOverdue(item) || item.status === 'CHANGES_REQUESTED',
                    locked: isLockedWorkItem(item)
                  }]">{{ focusedTaskStatusLabel(item) }}</span>
                  <svg v-if="!isLockedWorkItem(item)" class="focused-row-arrow" viewBox="0 0 24 24" aria-hidden="true"><path d="m9 6 6 6-6 6"/></svg>
                  <span v-else class="focused-row-lock-label">锁定</span>
                </button>
              </div>
            </section>
          </div>

          <div v-else class="focused-task-empty">
            <span>✓</span>
            <strong>当前没有匹配的任务</strong>
            <p>可以调整来源筛选或搜索关键词。</p>
          </div>
        </main>

      </section>
    </section>

    <section v-if="false" class="team-console-shell team-redesign-shell">
      <header class="team-redesign-head">
        <div class="team-redesign-title-row">
          <div class="team-context-main">
            <span class="team-title-caret" aria-hidden="true"></span>
            <h1>{{ team.name || '项目团队' }}</h1>
            <div class="team-project-switcher" v-if="teams.length > 1">
              <button type="button" class="project-switch-trigger" :aria-expanded="projectSwitcherOpen" aria-label="切换项目" @click="projectSwitcherOpen = !projectSwitcherOpen">
                <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
                  <path d="M8 7h9" />
                  <path d="m14 4 3 3-3 3" />
                  <path d="M16 17H7" />
                  <path d="m10 14-3 3 3 3" />
                </svg>
              </button>
              <Transition name="project-switch-pop">
                <div v-if="projectSwitcherOpen" class="project-switch-menu">
                  <button
                    v-for="item in teams"
                    :key="item.id"
                    type="button"
                    :class="{ active: item.id === selectedTeamId }"
                    @click="selectTeamFromSwitcher(item.id)"
                  >
                    <span>{{ item.name }}</span>
                    <em v-if="item.id === selectedTeamId">当前</em>
                  </button>
                </div>
              </Transition>
            </div>
          </div>
          <div class="team-redesign-status">
            <span>{{ collaborationStatus }}</span>
            <span>准备 {{ metrics.overallProgress || 0 }}%</span>
            <span>{{ onlineMemberCount }} 人在线</span>
            <span>{{ overviewActionItems.length }} 项待处理</span>
          </div>
        </div>
      </header>

      <nav class="team-section-tabs" aria-label="项目团队分区">
        <button
          v-for="item in teamNavItems"
          :key="item.key"
          type="button"
          :class="{ active: activeTeamSection === item.key }"
          @click="activeTeamSection = item.key"
        >
          {{ item.label }}
        </button>
      </nav>

      <div class="team-redesign-layout">
        <aside class="linear-team-rail">
          <div class="linear-rail-group">
            <span>工作视图</span>
            <button
              v-for="item in workViewItems"
              :key="`work-view-${item.key}`"
              type="button"
              :class="{ active: activeTeamSection === 'overview' && activeRailMode === 'work' && activeWorkView === item.key }"
              @click="selectWorkView(item.key)"
            >
              <i><SvgIcon :name="item.icon" /></i>
              <b>{{ item.label }}</b>
              <em>{{ workViewCounts[item.key] || 0 }}</em>
            </button>
          </div>
          <div class="linear-rail-group stage-filter-group">
            <button type="button" class="rail-group-toggle" @click="toggleRailGroup('stage')">
              <span>阶段筛选</span>
              <em>{{ collapsedRailGroups.stage ? '展开' : '收起' }}</em>
            </button>
            <button
              v-if="!collapsedRailGroups.stage"
              v-for="item in workStageFilters"
              :key="`stage-filter-${item.key}`"
              type="button"
              :class="{ active: activeTeamSection === 'overview' && activeRailMode === 'stage' && activeStageFilter === item.key }"
              @click="selectStageFilter(item.key)"
            >
              <i><SvgIcon :name="stageIconName(item.key)" /></i>
              <b>{{ item.label }}</b>
            </button>
          </div>
          <div class="linear-rail-group muted">
            <button type="button" class="rail-group-toggle" @click="toggleRailGroup('team')">
              <span>资料与团队</span>
              <em>{{ collapsedRailGroups.team ? '展开' : '收起' }}</em>
            </button>
            <button
              v-if="!collapsedRailGroups.team"
              v-for="item in teamNavItems.filter((nav) => nav.key !== 'overview')"
              :key="`rail-${item.key}`"
              type="button"
              :class="{ active: activeTeamSection === item.key }"
              @click="activeTeamSection = item.key"
            >
              <i><SvgIcon :name="item.icon" /></i>
              <b>{{ item.label }}</b>
            </button>
          </div>
          <div class="linear-rail-progress">
            <div>
              <span>准备进度</span>
              <strong>{{ metrics.overallProgress || 0 }}%</strong>
            </div>
            <i><b :style="{ width: `${metrics.overallProgress || 0}%` }"></b></i>
            <small>{{ stageRemainingText }}</small>
          </div>
          <div class="linear-rail-stats">
            <span><b>{{ overviewActionItems.length }}</b> 待处理</span>
            <span><b>{{ members.length }}</b> 成员</span>
            <span><b>{{ todayTaskDoneCount }}/{{ tasks.length || 0 }}</b> 任务</span>
            <span><b>{{ deliveryItems.length }}</b> 版本</span>
          </div>
          <div class="linear-rail-group muted">
            <button type="button" class="rail-group-toggle" @click="toggleRailGroup('quick')">
              <span>快捷入口</span>
              <em>{{ collapsedRailGroups.quick ? '展开' : '收起' }}</em>
            </button>
            <button v-if="!collapsedRailGroups.quick" type="button" @click="router.push('/script-editor')"><i><SvgIcon name="prepare" /></i><b>进入准备</b></button>
            <button v-if="!collapsedRailGroups.quick" type="button" @click="goVideoScoreUpload"><i><SvgIcon name="score" /></i><b>视频评分</b></button>
          </div>
        </aside>

        <main class="team-redesign-main">
          <section v-if="activeTeamSection === 'overview' || activeTeamSection === 'profile'" class="work-hub-panel" :class="{ 'filter-open': workFilterOpen }">
            <div class="work-hub-head">
              <div>
                <h2>{{ currentWorkScopeTitle }}</h2>
              </div>
              <button type="button" v-if="canAssignTask" class="create-work-btn" @click="openTaskDialog">
                <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true"><path d="M12 5v14M5 12h14" /></svg>
                新建工作项
              </button>
            </div>

            <div class="work-flow-toolbar" aria-label="工作项工具栏">
              <div class="work-flow-current">
                <span>{{ filteredWorkItems.length }} 项工作</span>
              </div>
              <div class="work-flow-tools">
                <button type="button" :class="{ active: workFilterOpen || workTypeFilter !== 'ALL' }" @click="workFilterOpen = !workFilterOpen">
                  筛选<span v-if="workTypeFilter !== 'ALL'">：{{ workTypeFilterLabel }}</span>
                </button>
                <button type="button" @click="cycleWorkSort">排序：{{ workSortLabel }}</button>
                <button type="button" @click="cycleWorkDensity">密度：{{ workDensityLabel }}</button>
                <button type="button" @click="toggleWorkSummary">视图：{{ workSummaryVisible ? '摘要' : '紧凑' }}</button>
              </div>
            </div>

            <div v-if="workFilterOpen" class="work-filter-panel" aria-label="工作项筛选条件">
              <button
                v-for="item in workTypeFilterItems"
                :key="item.key"
                type="button"
                :class="{ active: workTypeFilter === item.key }"
                @click="workTypeFilter = item.key"
              >
                {{ item.label }}
              </button>
            </div>

            <div class="work-list-table work-issue-stream" :class="[`density-${workDensity}`, { 'summary-hidden': !workSummaryVisible }]" aria-label="团队工作项列表">
              <button
                v-for="(item, index) in filteredWorkItems"
                :key="item.id"
                type="button"
                class="work-item-row"
                :class="[{ active: selectedWorkItem?.id === item.id, overdue: item.isOverdue }, `priority-${item.priority.toLowerCase()}`]"
                @click="selectWorkItem(item)"
                @dblclick="runWorkItemAction(item)"
              >
                <span class="work-code">{{ item.typeLabel }}-{{ String(index + 1).padStart(3, '0') }}</span>
                <span class="work-state-dot" :class="workProgressClass(item)" :style="workProgressStyle(item)" aria-hidden="true"></span>
                <span class="work-title"><strong>{{ item.title }}</strong><small>{{ item.summary }}</small></span>
                <span class="work-meta">
                  <span class="work-tag">{{ item.stageLabel }}</span>
                  <span class="work-tag accent" v-if="item.isOverdue">已过期</span>
                  <span class="work-tag accent" v-else-if="item.priority === 'HIGH'">高优先级</span>
                  <span class="work-tag" v-else>{{ item.statusLabel }}</span>
                  <span v-if="item.assignees.length" class="work-avatar-stack" :title="item.assignees.map((member) => member.username).join('、')">
                    <span v-for="member in item.assignees.slice(0, 3)" :key="`${item.id}-${member.userId}`" class="work-avatar">{{ member.username?.slice(0, 1) || '人' }}</span>
                    <b v-if="item.assignees.length > 3">+{{ item.assignees.length - 3 }}</b>
                  </span>
                  <span class="work-date">{{ formatShortDate(item.dueAt) }}</span>
                </span>
              </button>
              <div v-if="!filteredWorkItems.length" class="work-empty-state">
                <strong>当前视图暂无工作项</strong>
                <span>切换左侧视图或阶段筛选，查看其他团队事项。</span>
              </div>
            </div>
          </section>

          <section v-else-if="activeTeamSection === 'materials' || activeTeamSection === 'versions'" class="console-card material-console-card">
            <div class="console-card-head">
              <div>
                <h2>{{ activeTeamSection === 'versions' ? '作品版本' : '资料库' }}</h2>
                <p>PPT、讲稿、PDF、视频和作品素材统一沉淀，支撑准备页生成与路演复盘。</p>
              </div>
            </div>
            <div class="file-tabs">
              <button
                v-for="item in materialTypeTabs"
                :key="item.key"
                type="button"
                :class="{ active: materialTypeFilter === item.key }"
                @click="materialTypeFilter = item.key"
              >
                {{ item.label }}
              </button>
            </div>
            <div class="file-table">
              <div class="file-table-head">
                <span>名称</span>
                <span>类型</span>
                <span>更新人</span>
                <span>更新时间</span>
                <span>大小</span>
                <span>操作</span>
              </div>
              <div v-for="item in visibleMaterialRows" :key="item.deliveryId" class="file-row">
                <strong><i :class="fileKindClass(item)">{{ fileKindLabel(item) }}</i>{{ item.title }}</strong>
                <span>{{ item.typeLabel }}</span>
                <span>{{ item.actorName || '未分配' }}</span>
                <span>{{ formatDate(item.updatedAt) }}</span>
                <span>{{ formatFileSize(item.attachmentSize) }}</span>
                <span class="file-actions">
                  <button type="button" @click="inspectDelivery(item)">详情</button>
                  <button type="button" :disabled="!canPreviewAttachment(item)" @click="previewAttachment(item)">预览</button>
                </span>
              </div>
              <div v-if="!visibleMaterialRows.length" class="console-empty">暂无资料，可从项目准备页或任务提交中沉淀。</div>
            </div>
          </section>

          <section v-else-if="activeTeamSection === 'tasks'" class="console-card task-progress-card">
            <div class="console-card-head">
              <div>
                <h2>任务推进</h2>
                <p>按阶段拆解团队行动，AI 生成任务与老师手动任务都会汇入这里。</p>
              </div>
              <button type="button" v-if="canAssignTask" class="create-work-btn" @click="openTaskDialog">
                <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true"><path d="M12 5v14M5 12h14" /></svg>
                新建任务
              </button>
            </div>
            <div class="phase-list">
              <section v-for="stage in stageTaskGroups" :key="stage.stageKey">
                <button type="button" class="phase-head" @click="canEditStageSchedule && openStageEditor(stage.raw)">
                  <span>{{ stage.title }}</span>
                  <b>{{ stage.done }}/{{ stage.total }}</b>
                </button>
                <div v-for="task in stage.tasks.slice(0, 4)" :key="task.id" class="phase-task">
                  <i :class="statusClass(task.status)"></i>
                  <strong>{{ task.title }}</strong>
                  <small>{{ task.ownerName || '未分配' }} · {{ formatDate(task.dueAt) }}</small>
                  <em>{{ taskStatusText(task.status) }}</em>
                </div>
              </section>
            </div>
          </section>

          <section v-else-if="activeTeamSection === 'members'" class="console-card team-members-card">
            <div class="console-card-head">
              <div>
                <h2>团队成员</h2>
                <p>查看岗位、职责和当前分工，必要时补充团队成员。</p>
              </div>
              <button type="button" v-if="canAssignTask" @click="openProjectDialog">成员分工</button>
            </div>
            <div class="member-table-list">
              <button v-for="member in members" :key="member.userId" type="button" :class="{ active: activeAbilityUserId === member.userId }" @click="activeAbilityUserId = member.userId">
                <span>{{ member.username?.slice(0, 1) || '成' }}</span>
                <strong>{{ member.username }}</strong>
                <small>{{ roleInTeamText(member.roleInTeam) }} · {{ member.positionName || '未设岗位' }}</small>
                <em>{{ member.responsibility || '负责阶段交付与协作同步' }}</em>
              </button>
              <button v-if="canAssignTask" type="button" class="member-invite" @click="openProjectDialog">
                <span>+</span>
                <strong>邀请成员</strong>
                <small>补充团队岗位</small>
              </button>
            </div>
          </section>

          <section v-else-if="activeTeamSection === 'review'" class="console-card roadshow-redesign-card">
            <div class="console-card-head">
              <div>
                <h2>路演复盘</h2>
                <p>绑定会议或上传视频评分，查看报告、问题和下一轮训练建议。</p>
              </div>
              <button type="button" @click="goVideoScoreUpload">上传视频评分</button>
            </div>
            <div class="roadshow-redesign-grid">
              <article class="roadshow-score-card" :class="statusClass(activeRoadshow.status)">
                <div class="roadshow-score-head">
                  <div>
                    <span>{{ roadshowTypeText(activeRoadshow.roadshowType) }}</span>
                    <h3>{{ activeRoadshow.meetingTitle || '未选择会议' }}</h3>
                    <small>{{ activeRoadshow.summary || '选择或绑定会议后同步评分与复盘内容' }}</small>
                  </div>
                  <div class="roadshow-score-value">
                    <strong>{{ formatScore(activeRoadshow.score || 0) }}</strong>
                    <b>{{ activeRoadshow.scoreSource || roadshowStatusText(activeRoadshow.status) }}</b>
                  </div>
                </div>
              </article>
              <div class="meeting-picker">
                <label>
                  <span>本团队复盘会议</span>
                  <select v-model="selectedRoadshowMeetingId">
                    <option value="">{{ roadshowMeetings.length ? '选择会议查看复盘' : '本团队尚未绑定会议' }}</option>
                    <option v-for="item in roadshowMeetings" :key="item.meetingId" :value="String(item.meetingId)">
                      {{ item.meetingTitle }} · {{ roadshowStatusText(item.status) }}
                    </option>
                  </select>
                </label>
              </div>
            </div>
            <div class="review-columns compact-review-columns">
              <article>
                <span>亮点证据</span>
                <div v-for="item in activeRoadshowHighlights.slice(0, 3)" :key="`h-${item.title}`">
                  <strong>{{ item.title }}</strong>
                  <small>{{ item.description }}</small>
                </div>
                <div v-if="!activeRoadshowHighlights.length" class="mini-empty">暂无亮点摘要</div>
              </article>
              <article>
                <span>待改进问题</span>
                <div v-for="item in activeRoadshowProblems.slice(0, 4)" :key="`p-${item.title}`" :class="statusClass(item.severity)">
                  <strong>{{ item.title }}</strong>
                  <small>{{ item.description }}</small>
                </div>
                <div v-if="!activeRoadshowProblems.length" class="mini-empty">暂无问题记录</div>
              </article>
              <article>
                <span>下一步训练</span>
                <div v-for="item in activeRoadshowActions.slice(0, 4)" :key="`a-${item.title}`">
                  <strong>{{ item.title }}</strong>
                  <small>{{ item.description }}</small>
                </div>
                <div v-if="!activeRoadshowActions.length" class="mini-empty">等待评分后生成建议</div>
              </article>
            </div>
          </section>
        </main>

        <aside class="team-action-aside">
          <section class="side-card work-detail-card" v-if="activeTeamSection === 'overview' && selectedWorkItem">
            <div class="work-detail-topline">
              <span>{{ selectedWorkItem.typeLabel }}详情</span>
              <b :class="{ warn: selectedWorkItem.isOverdue || selectedWorkItem.priority === 'HIGH' }">{{ selectedWorkItem.isOverdue ? '已过期' : selectedWorkItem.statusLabel }}</b>
            </div>
            <div class="work-detail-title-block">
              <h2>{{ selectedWorkItem.title }}</h2>
              <p>{{ selectedWorkItem.summary }}</p>
            </div>

            <div class="work-detail-fields">
              <div v-if="selectedWorkItem.assignees.length"><span>负责人</span><strong class="detail-avatar-stack"><span v-for="member in selectedWorkItem.assignees" :key="`${selectedWorkItem.id}-detail-${member.userId}`"><b>{{ member.username?.slice(0, 1) || '人' }}</b>{{ member.username }}</span></strong></div>
              <div><span>阶段</span><strong>{{ selectedWorkItem.stageLabel }}</strong></div>
              <div><span>优先级</span><strong>{{ selectedWorkItem.priority === 'HIGH' ? '高' : selectedWorkItem.priority === 'LOW' ? '低' : '中' }}</strong></div>
              <div><span>截止</span><strong>{{ formatDate(selectedWorkItem.dueAt) }}</strong></div>
              <div><span>来源</span><strong>{{ selectedWorkItem.sourceLabel }}</strong></div>
            </div>

            <div class="work-detail-section">
              <span>关联内容</span>
              <button
                v-for="link in selectedWorkItem.links"
                :key="`${selectedWorkItem.id}-${link.label}`"
                type="button"
                @click="runWorkItemAction(selectedWorkItem, link.action)"
              >
                {{ link.label }}
              </button>
              <small v-if="!selectedWorkItem.links.length">暂无关联文件或报告。</small>
            </div>

            <div class="work-detail-actions">
              <button
                v-for="action in selectedWorkItem.actions"
                :key="`${selectedWorkItem.id}-${action.key}`"
                type="button"
                :class="{ primary: action.kind === 'primary' }"
                @click="runWorkItemAction(selectedWorkItem, action.key)"
              >
                {{ action.label }}
              </button>
            </div>
          </section>

          <section class="side-card action-aside-card" v-else>
            <div class="side-card-head">
              <h2>当前待处理</h2>
              <strong>{{ currentSideItems.length }} 项</strong>
            </div>
            <div class="missing-list">
              <button v-for="item in currentSideItems" :key="`${item.type}-${item.title}`" type="button" @click="handleActionItem(item)">
                <span>{{ item.badge }}</span>
                <strong>{{ item.title }}</strong>
                <small>{{ item.note }}</small>
              </button>
              <div v-if="!currentSideItems.length" class="console-empty">当前分区暂无待处理事项。</div>
            </div>
          </section>
        </aside>
      </div>
    </section>

    <section class="team-hero">
      <div>
        <span class="kicker">PROJECT TEAM OPS</span>
        <h1>项目团队</h1>
        <p>{{ team?.description || '课程、测评、材料、路演与复盘一体化追踪。' }}</p>
        <div class="team-switch" v-if="teams.length > 1">
          <button
            v-for="item in teams"
            :key="item.id"
            type="button"
            :class="{ active: item.id === selectedTeamId }"
            @click="selectTeam(item.id)"
          >
            {{ item.name }}
          </button>
        </div>
        <div v-if="canTeachObserve || canCreateProjectFromUser" class="hero-actions">
          <button type="button" class="primary-action" @click="openProjectDialog">
            创建项目
          </button>
          <span>按学校、学院、班级和用户组选择队伍成员</span>
        </div>
      </div>

      <div class="cmd-kpi">
        <div class="kpi-health">
          <span>项目状态</span>
          <strong>{{ metrics.overallProgress || 0 }}%</strong>
          <small>{{ healthText }}</small>
        </div>
        <div class="kpi-grid">
          <div><b>{{ metrics.taskCount || 0 }}</b><span>任务</span></div>
          <div><b>{{ metrics.pendingReviews || 0 }}</b><span>待审核</span></div>
          <div><b>{{ metrics.roadshowScore || '--' }}</b><span>路演评分</span></div>
          <div><b>{{ metrics.openIssues || 0 }}</b><span>待复盘</span></div>
        </div>
      </div>
    </section>

    <section v-if="loading" class="team-state-panel">
      <span class="kicker">SYNCING</span>
      <h2>正在同步项目团队</h2>
      <p>正在读取你的项目、成员、任务、路演复盘和能力证据。</p>
    </section>

    <section v-else-if="teamLoadError" class="team-state-panel warning">
      <span class="kicker">DATA LINK</span>
      <h2>项目团队数据加载失败</h2>
      <p>{{ teamLoadError }}</p>
      <button type="button" class="primary-action" @click="fetchTeams">重新加载</button>
    </section>

    <section v-else-if="!dashboard" class="team-state-panel">
      <span class="kicker">NO PROJECT</span>
      <h2>{{ canCreateProjectFromUser ? '暂无可管理项目' : '暂无项目团队' }}</h2>
      <p>{{ canCreateProjectFromUser ? '可以创建项目并选择队长、成员、权限与阶段周期。' : '你还没有加入项目团队，请联系老师或队长分配项目。' }}</p>
      <button v-if="canCreateProjectFromUser" type="button" class="primary-action" @click="openProjectDialog">
        创建项目
      </button>
    </section>

    <template v-else>
    <section class="stage-line" aria-label="项目阶段">
      <article v-for="stage in stages" :key="stage.stageKey" :class="stageClass(stage)">
        <div class="stage-marker" aria-hidden="true">
          <span></span>
        </div>
        <div class="stage-card-head">
          <em>{{ stage.stageKey }}<span v-if="stage.optional" class="stage-optional">可选</span></em>
          <button
            v-if="canEditStageSchedule"
            type="button"
            class="stage-edit-btn"
            title="编辑阶段"
            aria-label="编辑阶段"
            @click="openStageEditor(stage)"
          >
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04a1.003 1.003 0 0 0 0-1.42l-2.34-2.34a1.003 1.003 0 0 0-1.42 0l-1.83 1.83 3.75 3.75 1.84-1.82z" />
            </svg>
          </button>
        </div>
        <strong>{{ stage.title }}</strong>
        <i><b :style="{ width: `${stage.progress || 0}%` }"></b></i>
        <small>
          {{ stage.statusLabel || stageStatusText(stage.status) }}
          <template v-if="stage.personalProgress != null"> · 我的 {{ stage.personalProgress }}%</template>
          · 开始 {{ formatStageDate(stage.startDate) }}
          · 截止 {{ formatStageDate(stage.dueDate) }}
        </small>
        <p v-if="stage.suggestion" class="stage-suggestion">{{ stage.suggestion }}</p>
      </article>
    </section>

    <section class="role-banner" :class="roleClass">
      <span>{{ roleLabel }}</span>
      <strong>{{ roleMainText }}</strong>
      <small>{{ roleSubText }}</small>
      <div v-if="myRoleInTeam === 'CAPTAIN' && !canTeachObserve" class="permission-pills">
        <b v-for="option in captainPermissionOptions" :key="option.key" :class="{ active: managementPermissions[option.key] }">
          {{ option.label }}
        </b>
      </div>
    </section>

    <section class="work-tier">
      <main class="workbench">
        <section class="panel action-panel">
          <div class="panel-head">
            <div class="task-title-switch" :class="{ single: !canShowTaskManagement }">
              <button
                type="button"
                :class="{ active: workbenchTab === 'TASKS' || !canShowTaskManagement }"
                @click="workbenchTab = 'TASKS'"
              >
                <span>{{ canManage ? '团队任务看板' : '我的行动队列' }}</span>
                <strong>{{ canManage ? '团队任务' : '我的行动' }}</strong>
                <small>{{ taskCountByFilter('ALL') }} 项任务</small>
              </button>
              <button
                v-if="canShowTaskManagement"
                type="button"
                :class="{ active: workbenchTab === 'MANAGEMENT' }"
                @click="workbenchTab = 'MANAGEMENT'"
              >
                <span>任务管理</span>
                <strong>任务管理中心</strong>
                <small>{{ deliveryCountByFilter('PENDING_REVIEW') }} 项待审核</small>
              </button>
            </div>
            <button v-if="canAssignTask" type="button" class="assign-task-btn" @click="openTaskDialog">
              <span>分配任务</span>
              <i aria-hidden="true">+</i>
            </button>
          </div>

          <div v-show="workbenchTab === 'TASKS' || !canShowTaskManagement" class="task-pane">
            <div class="workbench-tabs" aria-label="任务筛选">
              <button
                v-for="tab in taskStatusTabs"
                :key="tab.key"
                type="button"
                :class="{ active: taskFilter === tab.key }"
                @click="taskFilter = tab.key"
              >
                <span>{{ tab.label }}</span>
                <b>{{ taskCountByFilter(tab.key) }}</b>
              </button>
            </div>

            <div class="task-grid">
              <article v-for="task in visibleTasks" :key="task.id" class="task-card" :class="taskClass(task)">
                <div class="task-top">
                  <span>{{ task.stageKey }}</span>
                  <b :class="statusClass(task.status)">{{ taskStatusText(task.status) }}</b>
                </div>
                <h3>{{ task.title }}</h3>
                <p>{{ task.description || '暂无说明' }}</p>
                <div class="task-meta">
                  <small>负责人：{{ task.ownerName || '未分配' }}</small>
                  <small>截止：{{ formatDate(task.dueAt) }}</small>
                </div>

                <div class="delivery-strip">
                  <span>交付状态</span>
                  <strong>{{ deliveryText(task) }}</strong>
                  <small v-if="task.latestSubmittedAt">
                    {{ task.latestSubmitterName || task.ownerName }} · {{ formatDate(task.latestSubmittedAt) }}
                  </small>
                  <div v-if="task.latestAttachmentUrl" class="attachment-actions compact-actions">
                    <button v-if="canPreviewAttachment(task)" type="button" @click="previewAttachment(task)">在线查看</button>
                    <button type="button" @click="downloadAttachment(task)">下载文件</button>
                  </div>
                </div>

                <form v-if="canSubmitTask(task)" class="submit-box" @submit.prevent="submitTask(task)">
                  <textarea v-model="submissionDrafts[task.id]" rows="2" placeholder="提交说明、周报摘要、链接或修改记录"></textarea>
                  <DropFileUpload
                    :key="`card-upload-${task.id}-${taskUploadNonce[task.id] || 0}`"
                    multiple
                    size="sm"
                    :title="selectedFileName(task.id) || '拖拽成果文件到此处，或点击选择'"
                    :hint="selectedFileName(task.id) ? selectedFileHelp(task.id) : '支持周报、PPT、逐字稿、PDF、视频或压缩包'"
                    @change="(files) => addTaskFilesFromDrop(task, files)"
                  />
                  <button type="submit" :disabled="submissionUploading[task.id]">
                    {{ submissionUploading[task.id] ? '提交中' : '提交成果' }}
                  </button>
                </form>
                <div v-else-if="submitLockedReason(task)" class="submit-lock">
                  {{ submitLockedReason(task) }}
                </div>
              </article>
              <div v-if="!visibleTasks.length" class="empty-state">当前筛选条件下暂无任务。</div>
            </div>
          </div>

          <div v-if="canShowTaskManagement && workbenchTab === 'MANAGEMENT'" class="task-management-pane">
            <div class="material-overview">
              <article v-for="item in deliverySummary" :key="item.key">
                <span>{{ item.label }}</span>
                <strong>{{ item.value }}</strong>
              </article>
            </div>

            <div class="workbench-tabs material-tabs" aria-label="任务管理筛选">
              <button
                v-for="tab in deliveryStatusTabs"
                :key="tab.key"
                type="button"
                :class="{ active: deliveryFilter === tab.key }"
                @click="deliveryFilter = tab.key"
              >
                <span>{{ tab.label }}</span>
                <b>{{ deliveryCountByFilter(tab.key) }}</b>
              </button>
            </div>

            <div class="material-list">
              <article v-for="item in visibleDeliveries" :key="item.deliveryId" class="material-row delivery-row" :class="deliveryClass(item)">
                <div class="material-type">
                  <span>{{ item.typeLabel }}</span>
                  <b :class="statusClass(item.status)">{{ materialStatusText(item.status) }}</b>
                </div>
                <div class="material-main">
                  <h3>{{ item.title }}</h3>
                  <p>{{ item.description || '暂无说明' }}</p>
                  <small>{{ item.actorLabel }}：{{ item.actorName || '未分配' }} · {{ item.timeLabel }}：{{ formatDate(item.updatedAt) }}</small>
                </div>
                <div class="material-tools">
                  <div class="attachment-actions">
                    <button type="button" @click="inspectDelivery(item)">查看</button>
                    <button type="button" :disabled="!deliveryUrl(item)" @click="downloadAttachment(item)">下载</button>
                    <button
                      v-if="canReviewDelivery(item)"
                      type="button"
                      class="review-open-btn"
                      @click="openDeliveryReview(item)"
                    >
                      审核
                    </button>
                  </div>
                </div>
              </article>
              <div v-if="!visibleDeliveries.length" class="empty-state">当前筛选条件下暂无交付物。</div>
            </div>
          </div>
        </section>

        <section class="panel roadshow-panel">
          <div class="panel-head">
            <div>
              <span class="kicker">ROADSHOW & REVIEW</span>
              <h2>路演与复盘</h2>
            </div>
            <span class="panel-note">选择会议查看 AI/评委复盘</span>
          </div>

          <div class="roadshow-review-layout">
            <article class="roadshow-score-card" :class="statusClass(activeRoadshow.status)">
              <div class="roadshow-score-head">
                <div>
                  <span>{{ roadshowTypeText(activeRoadshow.roadshowType) }}</span>
                  <h3>{{ activeRoadshow.meetingTitle || '未选择会议' }}</h3>
                  <small>{{ activeRoadshow.summary || '选择或绑定会议后同步评分与复盘内容' }}</small>
                </div>
                <div class="roadshow-score-value">
                  <strong>{{ formatScore(activeRoadshow.score || 0) }}</strong>
                  <b>{{ activeRoadshow.scoreSource || roadshowStatusText(activeRoadshow.status) }}</b>
                </div>
              </div>
              <div class="roadshow-dimensions">
                <div v-for="item in activeRoadshowDimensions" :key="item.key || item.name" class="dimension-row">
                  <div>
                    <em>{{ item.name }}</em>
                    <small>{{ dimensionRatio(item) }}</small>
                  </div>
                  <i><b :style="{ width: `${dimensionPercentValue(item)}%` }"></b></i>
                  <strong>{{ dimensionPercentValue(item) }}%</strong>
                </div>
                <span v-if="!activeRoadshowDimensions.length" class="muted-dimension">暂无维度评分</span>
              </div>
            </article>

            <div class="review-console">
              <div class="meeting-picker">
                <label>
                  <span>本团队复盘会议</span>
                  <select v-model="selectedRoadshowMeetingId">
                    <option value="">{{ roadshowMeetings.length ? '选择会议查看复盘' : '本团队尚未绑定会议' }}</option>
                    <option v-for="item in roadshowMeetings" :key="item.meetingId" :value="String(item.meetingId)">
                      {{ item.meetingTitle }} · {{ roadshowStatusText(item.status) }}
                    </option>
                  </select>
                </label>
                <button type="button" class="upload-score-entry" @click="goVideoScoreUpload">
                  上传视频评分
                </button>
                <AiScoreControl
                  v-if="selectedRoadshowMeetingId"
                  class="team-ai-score-control"
                  :meeting-id="selectedRoadshowMeetingId"
                  :team-id="selectedTeamId"
                  :team-name="team.name || ''"
                  :track-id="team.trackId || team.trackName || activeRoadshow.trackName || '新一代信息技术赛道'"
                  :track-name="team.trackName || activeRoadshow.trackName || '新一代信息技术赛道'"
                  :project-name="team.projectName || team.name || ''"
                  source-type="meeting_recording"
                  source-label="团队路演会议"
                />
              </div>

              <div class="review-columns">
                <article>
                  <span>亮点证据</span>
                  <div v-for="item in activeRoadshowHighlights.slice(0, 3)" :key="`h-${item.title}`">
                    <strong>{{ item.title }}</strong>
                    <small>{{ item.description }}</small>
                  </div>
                  <div v-if="!activeRoadshowHighlights.length" class="mini-empty">暂无亮点摘要</div>
                </article>
                <article>
                  <span>待改进问题</span>
                  <div v-for="item in activeRoadshowProblems.slice(0, 4)" :key="`p-${item.title}`" :class="statusClass(item.severity)">
                    <strong>{{ item.title }}</strong>
                    <small>{{ item.description }}</small>
                  </div>
                  <div v-if="!activeRoadshowProblems.length" class="mini-empty">暂无问题记录</div>
                </article>
                <article>
                  <span>下一步训练</span>
                  <div v-for="item in activeRoadshowActions.slice(0, 4)" :key="`a-${item.title}`">
                    <strong>{{ item.title }}</strong>
                    <small>{{ item.description }}</small>
                  </div>
                  <div v-if="!activeRoadshowActions.length" class="mini-empty">等待评分后生成建议</div>
                </article>
              </div>
            </div>
          </div>

          <section class="roadshow-memory-panel">
            <div class="memory-head">
              <div>
                <span class="kicker">ROADSHOW MEMORY</span>
                <h3>连续评分记忆</h3>
              </div>
              <small v-if="roadshowMemoryLoading">同步历史评分中</small>
              <small v-else-if="roadshowMemoryError">{{ roadshowMemoryError }}</small>
              <small v-else>{{ roadshowMemoryStatusText }}</small>
            </div>

            <div class="memory-metrics">
              <article>
                <span>评分轮次</span>
                <strong>{{ memoryRounds.length }}</strong>
              </article>
              <article>
                <span>较首轮变化</span>
                <strong>{{ memoryDeltaText }}</strong>
              </article>
              <article>
                <span>本轮上限</span>
                <strong>{{ formatScore(memoryFullScoreGap.ceilingScore || activeRoadshow.score || 0) }}</strong>
              </article>
              <article>
                <span>新增扣分</span>
                <strong>{{ memoryNewIssues.length }}</strong>
              </article>
            </div>

            <div class="memory-grid">
              <article class="memory-list">
                <span>上轮问题复检</span>
                <div
                  v-for="item in memoryPriorIssueReview.slice(0, 4)"
                  :key="`${item.title}-${item.status}`"
                  :class="statusClass(item.status)"
                >
                  <b>{{ memoryIssueStatusText(item.status) }}</b>
                  <strong>{{ item.title }}</strong>
                  <small>{{ item.conclusion || item.description || '等待下一轮证据确认' }}</small>
                  <button
                    v-for="anchor in memoryAnchors(item).slice(0, 2)"
                    :key="`${item.title}-${anchor.type}-${anchor.sourceRef}`"
                    type="button"
                    class="evidence-chip"
                    @click="openEvidenceAnchor(anchor, item)"
                  >
                    {{ evidenceAnchorText(anchor) }}
                  </button>
                </div>
                <p v-if="!memoryPriorIssueReview.length">{{ memoryEmptyReviewText }}</p>
              </article>

              <article class="memory-list">
                <span>本轮新增扣分</span>
                <div v-for="item in memoryNewIssues.slice(0, 4)" :key="item.title">
                  <b>{{ item.severity || 'MEDIUM' }}</b>
                  <strong>{{ item.title }}</strong>
                  <small>{{ item.description || '需要补充评审证据与训练动作' }}</small>
                  <button
                    v-for="anchor in memoryAnchors(item).slice(0, 2)"
                    :key="`${item.title}-${anchor.type}-${anchor.sourceRef}`"
                    type="button"
                    class="evidence-chip"
                    @click="openEvidenceAnchor(anchor, item)"
                  >
                    {{ evidenceAnchorText(anchor) }}
                  </button>
                </div>
                <p v-if="!memoryNewIssues.length">本轮没有识别出新的主要扣分项。</p>
              </article>

              <article class="memory-list full-score-gap">
                <span>为什么不是 100</span>
                <div>
                  <b>技术校准</b>
                  <strong>
                    原始 {{ formatScore(memoryFullScoreGap.rawScore || activeRoadshow.score || 0) }}
                    → 上限 {{ formatScore(memoryFullScoreGap.ceilingScore || activeRoadshow.score || 0) }}
                  </strong>
                  <small>技术能力 {{ formatScore(memoryFullScoreGap.skillScore || 0) }} / 现场演示证据会共同限制满分。</small>
                </div>
                <ul v-if="memoryFullScoreReasons.length">
                  <li v-for="reason in memoryFullScoreReasons.slice(0, 4)" :key="reason">{{ reason }}</li>
                </ul>
                <p v-else>等待 AI 评分校准数据，用于解释满分差距。</p>
              </article>

              <article class="memory-list">
                <span>下一轮训练验收</span>
                <div v-for="item in memoryTrainingPlan.slice(0, 4)" :key="item.title">
                  <b>{{ item.acceptance || '需可验收' }}</b>
                  <strong>{{ item.title }}</strong>
                  <small>{{ item.description || item.action || '下一轮评分会按此检查是否真实改进' }}</small>
                </div>
                <p v-if="!memoryTrainingPlan.length">等待 AI 评分报告生成训练计划。</p>
              </article>
            </div>

            <div v-if="memoryTimeline.length" class="memory-timeline">
              <span
                v-for="round in memoryTimeline"
                :key="round.meetingId || round.roundNo"
                :title="round.title"
              >
                第{{ round.roundNo }}轮 · {{ formatScore(round.score || 0) }}分 · {{ round.issueCount || 0 }}项问题
              </span>
            </div>
          </section>

          <form v-if="canBindRoadshow" class="bind-form" @submit.prevent="bindRoadshow">
            <select v-model="roadshowForm.meetingId">
              <option value="">从我可绑定的会议中选择</option>
              <option
                v-for="item in bindableRoadshowMeetings"
                :key="`bind-${item.meetingId}`"
                :value="String(item.meetingId)"
              >
                {{ bindableMeetingLabel(item) }}
              </option>
            </select>
            <input v-model="roadshowForm.manualMeetingId" placeholder="或手动输入会议 ID" />
            <select v-model="roadshowForm.roadshowType">
              <option value="REHEARSAL">彩排</option>
              <option value="FINAL">正式路演</option>
            </select>
            <button type="submit">绑定到本团队</button>
          </form>
          <p v-if="canBindRoadshow && !roadshowMeetings.length" class="bind-hint">
            新建团队默认没有会议。请从「我可绑定的会议」中选择，或输入会议 ID 绑定后，才会出现在上方复盘列表。
          </p>
        </section>

        <section v-if="canTeachObserve" class="panel observe-panel">
          <div class="panel-head compact">
            <div>
              <span class="kicker">MENTOR OBSERVE</span>
              <h2>指导观察</h2>
            </div>
          </div>
          <div class="observe-body">
            <div class="observe-col">
              <p>{{ teacherObservation.summary }}</p>
              <div class="readiness-card" :class="statusClass(teacherObservation.readinessLevel)">
                <span>准备度</span>
                <strong>{{ teacherObservation.readinessScore || 0 }}%</strong>
                <small>{{ readinessText(teacherObservation.readinessLevel) }}</small>
              </div>
              <div class="observe-metrics">
                <span>进度 {{ teacherObservation.overallProgress || 0 }}%</span>
                <span>待审核 {{ teacherObservation.pendingReviews || 0 }}</span>
                <span>问题 {{ teacherObservation.openIssues || 0 }}</span>
              </div>
            </div>
            <div class="observe-col">
              <div class="observe-list">
                <b>关注点</b>
                <small v-for="item in teacherObservation.focusAreas || []" :key="item">{{ item }}</small>
              </div>
              <div class="observe-list">
                <b>建议动作</b>
                <small v-for="item in teacherObservation.actions || []" :key="item">{{ item }}</small>
              </div>
              <strong class="observe-intervention">{{ teacherObservation.intervention }}</strong>
            </div>
          </div>

          <div v-if="roadshowSpeakers.length" class="speaker-align">
            <div class="speaker-align-head">
              <b>路演发言人对齐</b>
              <small>AI 按自报岗位/姓名匹配到成员，教师可一键确认、改派或忽略</small>
            </div>
            <article
              v-for="sp in roadshowSpeakers"
              :key="sp.id"
              class="speaker-row"
              :class="statusClass(sp.status)"
            >
              <div class="speaker-main">
                <span class="speaker-tag">{{ sp.speakerLabel }}</span>
                <div class="speaker-info">
                  <p class="speaker-claim">
                    自报：{{ sp.claimedRole || sp.normalizedRole || '未识别岗位' }}
                    <em v-if="sp.matchedName">（自报姓名 {{ sp.matchedName }}）</em>
                  </p>
                  <p class="speaker-match">
                    <template v-if="sp.matchedUsername">
                      对齐到 <strong>{{ sp.matchedUsername }}</strong> · {{ sp.matchedRoleName || '—' }} ·
                      {{ speakerMethodLabel(sp.matchMethod) }} · 置信度 {{ speakerConfidence(sp) }}
                    </template>
                    <em v-else class="unmatched">未对齐（同岗多人或无法识别，待教师指定）</em>
                  </p>
                  <p v-if="sp.quote" class="speaker-quote">“{{ sp.quote }}”</p>
                </div>
                <span class="speaker-status">{{ speakerStatusLabel(sp.status) }}</span>
              </div>
              <div class="speaker-actions">
                <select class="speaker-select" @change="onReassignSpeaker(sp, $event)">
                  <option value="">改派给…</option>
                  <option v-for="m in members" :key="m.userId" :value="m.userId">
                    {{ m.username }}（{{ m.positionName || '未分配' }}）
                  </option>
                </select>
                <button
                  v-if="sp.matchedUserId && sp.status !== 'CONFIRMED'"
                  class="speaker-btn confirm"
                  @click="confirmSpeaker(sp)"
                >确认</button>
                <button
                  v-if="sp.status !== 'REJECTED'"
                  class="speaker-btn reject"
                  @click="rejectSpeaker(sp)"
                >忽略</button>
                <button
                  v-if="sp.status !== 'AUTO'"
                  class="speaker-btn reset"
                  @click="resetSpeaker(sp)"
                >重置</button>
              </div>
            </article>
          </div>
        </section>
      </main>

      <aside class="work-side">
        <section class="panel members-panel">
          <div class="panel-head compact">
            <div>
              <span class="kicker">TEAM ROSTER</span>
              <h2>成员与分工</h2>
            </div>
          </div>
          <div class="member-list">
            <button
              v-for="member in members"
              :key="member.userId"
              type="button"
              :class="{ active: activeAbilityUserId === member.userId }"
              @click="activeAbilityUserId = member.userId"
            >
              <span>{{ member.username?.slice(0, 1)?.toUpperCase() }}</span>
              <strong>{{ member.username }}</strong>
              <small>{{ roleInTeamText(member.roleInTeam) }} · {{ member.positionName || '未设岗位' }}</small>
            </button>
          </div>
          <div v-if="canAssignTask && activeMember" class="member-position-editor">
            <div class="mpe-head">
              <span class="kicker">ROLE SETTINGS</span>
              <div class="mpe-head-row">
                <span class="mpe-avatar">{{ activeMember.username?.slice(0, 1)?.toUpperCase() }}</span>
                <div>
                  <h3>{{ activeMember.username }} 的岗位</h3>
                  <span class="mpe-current">{{ roleInTeamText(activeMember.roleInTeam) }} · {{ memberPositionForm.positionName || activeMember.positionName || '未设岗位' }}</span>
                </div>
              </div>
            </div>
            <label class="mpe-field">
              <span>岗位角色</span>
              <select v-model="memberPositionForm.positionName">
                <option value="">选择岗位</option>
                <option v-for="role in positionRoles" :key="role.name" :value="role.name">
                  {{ role.name }}
                </option>
              </select>
            </label>
            <div class="add-position inline">
              <span class="add-position-label">没有合适岗位？现场新增一个</span>
              <div class="add-position-row">
                <input v-model="newPositionRole.name" placeholder="新增岗位名称" maxlength="80" />
                <button
                  type="button"
                  class="ghost"
                  :disabled="addingPositionRole || !newPositionRole.name.trim()"
                  @click="addMemberPositionRole"
                >
                  {{ addingPositionRole ? '添加中…' : '+ 新增岗位' }}
                </button>
              </div>
            </div>
            <label class="mpe-field">
              <span>职责说明</span>
              <textarea
                v-model="memberPositionForm.responsibility"
                rows="3"
                :placeholder="defaultResponsibilityForPosition(memberPositionForm.positionName)"
              ></textarea>
            </label>
            <button class="mpe-save" type="button" :disabled="positionSaving || !memberPositionForm.positionName" @click="saveMemberPosition">
              {{ positionSaving ? '保存中…' : '保存岗位' }}
            </button>
          </div>
        </section>

        <section class="panel ability-panel">
          <div class="panel-head compact">
            <div>
              <span class="kicker">ABILITY EVIDENCE</span>
              <h2>能力画像</h2>
            </div>
            <span class="panel-note">跟随左侧选中成员</span>
          </div>

          <div class="radar-wrap">
            <svg viewBox="0 0 260 260" role="img" :aria-label="`${activeAbility?.username || '成员'} 能力雷达图`">
              <g transform="translate(130 130)">
                <polygon v-for="ring in radarRings" :key="ring" class="radar-ring" :points="radarPoints(dimensions.map(() => ring))" />
                <line v-for="point in axisPoints" :key="point.label" class="radar-axis" x1="0" y1="0" :x2="point.x" :y2="point.y" />
                <polygon class="radar-fill" :class="{ 'radar-fill-pending': sampledDimensionCount === 0 }" :points="radarPoints(activeAbilityValues)" />
                <circle
                  v-for="(point, index) in abilityPoints"
                  :key="point.label"
                  class="radar-dot"
                  :class="{ 'radar-dot-pending': !activeAbilityList[index]?.sampled }"
                  :cx="point.x"
                  :cy="point.y"
                  r="4"
                />
              </g>
            </svg>
            <div class="radar-labels">
              <span v-for="point in labelPoints" :key="point.label" :style="{ left: `${point.left}%`, top: `${point.top}%` }">
                {{ point.label }}
              </span>
            </div>
          </div>

          <div class="ability-bars">
            <div v-for="item in activeAbilityList" :key="item.key" :class="{ placeholder: !item.sampled }">
              <span>
                {{ item.label }}
                <em v-if="!item.sampled" class="sample-tag">待采样</em>
              </span>
              <i><b :style="{ width: `${item.value}%` }"></b></i>
              <small>{{ item.sampled ? item.value : '—' }}</small>
            </div>
          </div>

          <div class="ability-confidence">
            <span>证据置信度</span>
            <strong>{{ activeAbility.confidence || 0 }}%</strong>
            <small v-if="sampledDimensionCount < dimensions.length">
              已采样 {{ sampledDimensionCount }}/{{ dimensions.length }} 个维度，灰显维度为基础占位分（50），尚无真实证据
            </small>
            <small v-else>由课程、测评、任务、材料审核和路演评分加权形成</small>
          </div>

          <div class="evidence-list">
            <article
              v-for="item in activeEvidence.slice(0, 6)"
              :key="`${item.dimensionKey}-${item.sourceType}-${item.summary}`"
              :class="{ muted: Number(item.weight || 0) <= 0 }"
            >
              <span>{{ dimensionLabel(item.dimensionKey) }} · {{ sourceTypeLabel(item.sourceType) }} · {{ evidenceWeightText(item) }}</span>
              <p>{{ item.summary }}</p>
            </article>
          </div>
        </section>
      </aside>
    </section>
    </template>

    <Teleport to="body">
      <div v-if="taskComposerOpen" class="task-modal-overlay" @click.self="closeTaskDialog">
        <section class="task-modal" role="dialog" aria-modal="true" aria-label="分配任务">
          <header class="task-modal-head">
            <div>
              <span class="kicker">新建工作项</span>
            </div>
            <button type="button" class="close-btn" aria-label="关闭弹窗" @click="closeTaskDialog">
              <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18" /></svg>
            </button>
          </header>

          <form class="task-modal-form task-create-form" @submit.prevent="createTask">
            <section class="task-create-intro">
              <div>
                <strong>先确定任务是什么，再安排什么时候做</strong>
                <span>任务类型和计划时间会直接决定用户端今日任务里的上午、下午、晚上展示。</span>
              </div>
            </section>

            <div class="task-create-layout">
              <section class="task-create-block task-create-content">
                <header><b>1</b><span>任务内容</span></header>
                <label class="task-title-field">
                  <span>任务标题</span>
                  <input v-model="taskForm.title" placeholder="例如：完成课程第 3 章学习" />
                </label>
                <label>
                  <span>任务说明与验收标准</span>
                  <textarea v-model="taskForm.description" rows="4" placeholder="写清楚要做什么、完成标准、需要提交什么材料"></textarea>
                </label>
              </section>

              <section class="task-create-block task-create-plan">
                <header><b>2</b><span>类型与时间</span></header>
                <div class="task-type-picker">
                  <span>任务类型</span>
                  <div>
                    <button
                      v-for="item in taskTypeOptions"
                      :key="item.key"
                      type="button"
                      :class="{ active: taskForm.taskType === item.key }"
                      @click="selectTaskType(item.key)"
                    >
                      {{ item.label }}
                    </button>
                  </div>
                  <input
                    v-if="taskForm.taskType === 'CUSTOM'"
                    v-model="taskForm.customTaskType"
                    placeholder="自定义类型，如：市场调研、财务测算"
                    maxlength="30"
                  />
                </div>
                <div class="task-time-slot-picker">
                  <span>计划时间段</span>
                  <div>
                    <button
                      v-for="item in taskTimeSlotOptions"
                      :key="item.key"
                      type="button"
                      :class="{ active: taskForm.timeSlot === item.key }"
                      @click="applyTaskTimeSlot(item.key)"
                    >
                      <b>{{ item.label }}</b>
                      <small>{{ item.hint }}</small>
                    </button>
                  </div>
                </div>
              </section>
            </div>

            <section class="task-create-block task-create-assign">
              <header><b>3</b><span>分配与截止</span></header>
            <div class="task-attribute-grid">
              <div class="task-assignee-picker">
                <span>负责人</span>
                <div>
                  <button
                    v-for="member in members"
                    :key="`task-owner-${member.userId}`"
                    type="button"
                    :class="{ active: taskForm.ownerUserIds.includes(member.userId) }"
                    @click="toggleTaskAssignee(member.userId)"
                  >
                    <b>{{ member.username?.slice(0, 1) || '人' }}</b>
                    {{ member.username }}
                  </button>
                </div>
              </div>
              <label>
                <span>所属阶段</span>
                <select v-model="taskForm.stageKey">
                  <option v-for="stage in stages" :key="stage.stageKey" :value="stage.stageKey">{{ stage.title }}</option>
                </select>
              </label>
              <label>
                <span>优先级</span>
                <select v-model="taskForm.priority">
                  <option value="LOW">低</option>
                  <option value="MEDIUM">中</option>
                  <option value="HIGH">高</option>
                </select>
              </label>
              <label class="date-attribute">
                <span>开始</span>
                <input v-model="taskForm.startAt" type="datetime-local" />
              </label>
              <label>
                <span>截止</span>
                <input v-model="taskForm.dueAt" type="datetime-local" />
              </label>
            </div>
            </section>
            <footer class="task-modal-actions">
              <button type="button" class="secondary-action" @click="closeTaskDialog">取消</button>
              <button type="submit">创建并分配</button>
            </footer>
          </form>
        </section>
      </div>
    </Teleport>

    <Teleport to="body">
      <div v-if="stageEditorOpen" class="task-modal-overlay" @click.self="closeStageEditor">
        <section class="task-modal stage-editor-modal" role="dialog" aria-modal="true" aria-label="编辑阶段">
          <header class="task-modal-head">
            <div>
              <span class="kicker">阶段配置</span>
              <h2>编辑阶段 · {{ stageEditorForm.stageKey }}</h2>
              <p>调整阶段名称、起止时间、是否必做，以及给团队展示的说明提示。</p>
            </div>
            <button type="button" class="close-btn" aria-label="关闭弹窗" @click="closeStageEditor">
              <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18" /></svg>
            </button>
          </header>

          <form class="task-modal-form" @submit.prevent="saveStageEditor">
            <label>
              <span>阶段名称</span>
              <input v-model="stageEditorForm.title" placeholder="例如：材料准备" maxlength="80" />
            </label>
            <label>
              <span>开始日期</span>
              <input v-model="stageEditorForm.startDate" type="date" />
            </label>
            <label>
              <span>截止日期</span>
              <input v-model="stageEditorForm.dueDate" type="date" />
            </label>
            <label>
              <span>阶段性质</span>
              <select v-model="stageEditorForm.optionalMode">
                <option value="required">必做（计入主链路）</option>
                <option value="optional">可选（不阻断后续节点）</option>
              </select>
            </label>
            <label class="task-modal-wide">
              <span>说明提示</span>
              <textarea
                v-model="stageEditorForm.suggestion"
                rows="4"
                placeholder="展示在阶段卡片下方，例如：建议完成推荐课程（可选，不阻断后续节点）"
              ></textarea>
            </label>
            <footer class="task-modal-actions">
              <button type="button" class="secondary-action" @click="closeStageEditor">取消</button>
              <button type="submit" :disabled="stageEditorSaving">{{ stageEditorSaving ? '保存中' : '保存配置' }}</button>
            </footer>
          </form>
        </section>
      </div>
    </Teleport>

    <Teleport to="body">
      <div v-if="projectDialogOpen" class="project-modal-overlay" @click.self="closeProjectDialog">
        <section class="project-modal" role="dialog" aria-modal="true" aria-label="创建项目">
          <header class="project-modal-head">
            <div>
              <span class="kicker">项目创建</span>
              <h2>创建项目</h2>
              <p>确定项目名称、队长、成员和队长权限。创建后会自动生成课程、测评、材料、路演和复盘阶段。</p>
            </div>
            <button type="button" class="close-btn" @click="closeProjectDialog">关闭</button>
          </header>

          <form class="project-modal-body" @submit.prevent="createProject">
            <div class="project-details">
              <label>
                <span>项目名称</span>
                <input v-model="projectForm.name" placeholder="例如：智能养老路演项目" />
              </label>
              <label>
                <span>项目说明</span>
                <textarea v-model="projectForm.description" rows="4" placeholder="项目目标、交付范围和路演方向"></textarea>
              </label>
              <label>
                <span>项目队长</span>
                <select v-model="projectForm.captainUserId">
                  <option value="">选择队长</option>
                  <option v-for="user in captainOptions" :key="user.id" :value="user.id">
                    {{ user.username }} · {{ user.schoolName }} / {{ user.className }}
                  </option>
                </select>
              </label>
              <div class="captain-position-grid">
                <label>
                  <span>队长岗位</span>
                  <select v-model="projectForm.captainPositionName">
                    <option v-for="role in positionRoles" :key="role.name" :value="role.name">
                      {{ role.name }}
                    </option>
                  </select>
                </label>
                <label>
                  <span>职责说明</span>
                  <input
                    v-model="projectForm.captainResponsibility"
                    :placeholder="defaultResponsibilityForPosition(projectForm.captainPositionName)"
                  />
                </label>
              </div>

              <div class="add-position modal-section">
                <span>新增岗位角色</span>
                <div class="add-position-row">
                  <input v-model="newPositionRole.name" placeholder="岗位名称，如：产品经理" maxlength="80" />
                  <input v-model="newPositionRole.description" placeholder="岗位职责说明（选填）" maxlength="300" />
                  <button
                    type="button"
                    :disabled="addingPositionRole || !newPositionRole.name.trim()"
                    @click="createPositionRole"
                  >
                    {{ addingPositionRole ? '添加中' : '添加岗位' }}
                  </button>
                </div>
                <p class="add-position-hint">新增后可在下方队长与成员岗位下拉中选择，并在项目内继续复用。</p>
              </div>

              <div class="selected-strip">
                <span>已选成员</span>
                <strong>{{ selectedCandidateMembers.length }}</strong>
                <div>
                  <button
                    v-for="user in selectedCandidateMembers.slice(0, 6)"
                    :key="user.id"
                    type="button"
                    @click="removeSelectedMember(user.id)"
                  >
                    {{ user.username }} ×
                  </button>
                  <small v-if="selectedCandidateMembers.length > 6">+{{ selectedCandidateMembers.length - 6 }}</small>
                </div>
              </div>

              <div v-if="selectedCandidateMembers.length" class="position-assignment modal-section">
                <span>成员岗位分配</span>
                <div class="position-assignment-list">
                  <div v-for="user in selectedCandidateMembers" :key="user.id" class="position-assignment-row">
                    <strong>{{ user.username }}</strong>
                    <select v-model="projectForm.memberPositions[user.id]">
                      <option value="">选择岗位</option>
                      <option v-for="role in positionRoles" :key="role.name" :value="role.name">
                        {{ role.name }}
                      </option>
                    </select>
                    <input
                      v-model="projectForm.memberResponsibilities[user.id]"
                      :placeholder="defaultResponsibilityForPosition(projectForm.memberPositions[user.id])"
                    />
                  </div>
                </div>
              </div>

              <div class="permission-picker modal-section">
                <span>队长权限</span>
                <div class="permission-grid">
                  <label v-for="option in captainPermissionOptions" :key="option.key" class="permission-card">
                    <input v-model="projectForm.captainPermissions" type="checkbox" :value="option.key" />
                    <b>{{ option.label }}</b>
                    <small>{{ option.help }}</small>
                  </label>
                </div>
              </div>
            </div>

            <div class="member-console">
              <div class="member-console-head">
                <div>
                  <span class="kicker">成员范围</span>
                  <h3>选择成员</h3>
                </div>
                <button type="button" @click="selectFilteredMembers">选择当前结果</button>
              </div>

              <div class="member-search">
                <input v-model="memberFilters.keyword" placeholder="搜索姓名、邮箱、学校、学院、班级" />
              </div>

              <div class="filter-grid">
                <label>
                  <span>用户组</span>
                  <select v-model="memberFilters.userGroup">
                    <option value="ALL">全部用户组</option>
                    <option v-for="item in userGroupOptions" :key="item" :value="item">{{ item }}</option>
                  </select>
                </label>
                <label>
                  <span>学校</span>
                  <select v-model="memberFilters.schoolName">
                    <option value="ALL">全部学校</option>
                    <option v-for="item in schoolOptions" :key="item" :value="item">{{ item }}</option>
                  </select>
                </label>
                <label>
                  <span>学院</span>
                  <select v-model="memberFilters.collegeName">
                    <option value="ALL">全部学院</option>
                    <option v-for="item in collegeOptions" :key="item" :value="item">{{ item }}</option>
                  </select>
                </label>
                <label>
                  <span>班级</span>
                  <select v-model="memberFilters.className">
                    <option value="ALL">全部班级</option>
                    <option v-for="item in classOptions" :key="item" :value="item">{{ item }}</option>
                  </select>
                </label>
                <label>
                  <span>角色</span>
                  <select v-model="memberFilters.role">
                    <option value="STUDENT">仅学生</option>
                    <option value="ALL">全部角色</option>
                    <option v-for="item in roleOptions" :key="item" :value="item">{{ roleText(item) }}</option>
                  </select>
                </label>
              </div>

              <div class="member-pool" aria-label="项目成员候选列表">
                <label v-for="user in filteredCandidateMembers" :key="user.id" class="member-row">
                  <input
                    v-model="projectForm.memberUserIds"
                    type="checkbox"
                    :value="user.id"
                    @change="ensureProjectMemberPosition(user.id)"
                  />
                  <b>{{ user.username }}</b>
                  <span>{{ roleText(user.role) }}</span>
                  <small>{{ user.schoolName }} · {{ user.collegeName }} · {{ user.className }}</small>
                  <em>{{ user.userGroup }}</em>
                </label>
                <div v-if="!filteredCandidateMembers.length" class="empty-state">
                  当前筛选条件下没有成员。
                </div>
              </div>
            </div>

            <footer class="project-modal-actions">
              <button type="button" class="secondary-action" @click="closeProjectDialog">取消</button>
              <button type="submit" :disabled="creatingProject">
                {{ creatingProject ? '创建中' : '创建项目' }}
              </button>
            </footer>
          </form>
        </section>
      </div>
    </Teleport>

    <Teleport to="body">
      <div v-if="activeTaskDetailWorkItem" class="task-drawer-overlay" @click.self="closeTaskDetailDrawer">
        <aside class="task-action-drawer" role="dialog" aria-modal="true" :aria-label="`任务详情：${activeTaskDetailWorkItem.title}`">
          <header class="task-drawer-head">
            <div>
              <span>{{ activeTaskDetailWorkItem.typeLabel }} · {{ focusedTaskStatusLabel(activeTaskDetailWorkItem) }}</span>
              <h3>{{ activeTaskDetailWorkItem.title }}</h3>
              <p>{{ activeTaskDetailWorkItem.summary || '暂无说明' }}</p>
            </div>
            <button type="button" @click="closeTaskDetailDrawer">关闭</button>
          </header>

          <div class="task-drawer-body">
            <section class="task-info-grid">
              <div><span>负责人</span><strong>{{ activeTaskDetailWorkItem.ownerName || '未分配' }}</strong></div>
              <div><span>任务类型</span><strong>{{ activeTaskDetailWorkItem.taskTypeLabel || '其他业务' }}</strong></div>
              <div><span>阶段</span><strong>{{ activeTaskDetailWorkItem.stageLabel }}</strong></div>
              <div><span>优先级</span><strong>{{ priorityText(activeTaskDetailWorkItem.priority) }}</strong></div>
              <div><span>截止时间</span><strong>{{ formatDate(activeTaskDetailWorkItem.dueAt) }}</strong></div>
              <div><span>来源</span><strong>{{ activeTaskDetailWorkItem.sourceLabel }}</strong></div>
            </section>

            <section class="task-requirement-panel">
              <div>
                <span>通用交付要求</span>
                <strong>{{ activeTaskDetailWorkItem.taskTypeLabel || '成果材料' }}</strong>
              </div>
              <p>适配全赛道全专业：可提交文字说明、外部成果链接和成果文件。PPT、讲稿、代码、视频、图片、表格、PDF、压缩包等材料都走同一套任务提交与审核闭环。</p>
              <div class="task-requirement-tags">
                <span>提交说明</span>
                <span>成果链接</span>
                <span>成果文件</span>
                <span>版本留痕</span>
              </div>
            </section>

            <section class="task-history-panel">
              <div class="task-panel-title">
                <strong>提交记录</strong>
                <span>{{ taskSubmissions(activeTaskDetailTask).length }} 版</span>
              </div>
              <article
                v-for="item in taskSubmissions(activeTaskDetailTask)"
                :key="item.id"
                class="task-history-row"
                :class="{ 'is-focused-submission': isFocusedSubmission(item) }"
              >
                <div>
                  <span>
                    V{{ item.versionNo || 1 }} · {{ submissionTypeLabel(item.submissionType) }} · {{ materialStatusText(item.status) }}
                    <em v-if="isFocusedSubmission(item)">本次查看</em>
                  </span>
                  <strong>{{ item.content || submissionSummary(item) }}</strong>
                  <small>{{ item.submitterName || '提交人' }} · {{ formatDate(item.createdAt) }}</small>
                  <small v-if="item.reviewComment">审核意见：{{ item.reviewComment }}</small>
                  <div v-if="submissionAssets(item).length || recordSubmissionLinks(item).length" class="task-history-assets">
                    <button v-for="asset in submissionAssets(item)" :key="asset.id || asset.fileUrl" type="button" @click="previewAttachment(asset)">
                      {{ asset.fileName || '成果文件' }}
                    </button>
                    <button v-for="link in recordSubmissionLinks(item)" :key="link.id || link.url" type="button" @click="openExternalLink(link.url)">
                      {{ link.title || '成果链接' }}
                    </button>
                  </div>
                </div>
                <div class="task-history-actions">
                  <button v-if="canPreviewAttachment(item)" type="button" @click="previewAttachment(item)">预览</button>
                  <button type="button" :disabled="!deliveryUrl(item)" @click="downloadAttachment(item)">下载</button>
                </div>
              </article>
              <div v-if="!taskSubmissions(activeTaskDetailTask).length" class="task-drawer-empty">还没有提交记录。</div>
            </section>
          </div>

          <footer class="task-drawer-actions">
            <button v-if="activeTaskDetailTask && canSubmitTask(activeTaskDetailTask)" type="button" class="primary" @click="openTaskSubmissionDrawer(activeTaskDetailWorkItem)">提交成果</button>
            <button v-if="activeTaskDetailWorkItem.links?.length" type="button" @click="runWorkItemAction(activeTaskDetailWorkItem, activeTaskDetailWorkItem.links[0].action)">查看附件</button>
          </footer>
        </aside>
      </div>
    </Teleport>

    <Teleport to="body">
      <div v-if="activeTaskSubmissionWorkItem" class="task-drawer-overlay" @click.self="closeTaskSubmissionDrawer">
        <aside class="task-action-drawer submit-drawer" role="dialog" aria-modal="true" :aria-label="`提交成果：${activeTaskSubmissionWorkItem.title}`">
          <header class="task-drawer-head">
            <div>
              <span>提交成果</span>
              <h3>{{ activeTaskSubmissionWorkItem.title }}</h3>
              <p>{{ activeTaskSubmissionWorkItem.summary || '提交说明、链接或附件，至少填写一项。' }}</p>
            </div>
            <button type="button" @click="closeTaskSubmissionDrawer">关闭</button>
          </header>

          <form v-if="activeTaskSubmissionTask" class="task-submit-form" @submit.prevent="submitTaskFromDrawer(activeTaskSubmissionTask)">
            <section class="task-submit-guidance">
              <strong>成果可以是任何专业形态</strong>
              <span>方案文档、PPT、讲稿、代码、视频、数据、设计稿、证明材料、压缩包和外部链接统一在这里提交、审核、归档。</span>
            </section>

            <section class="submission-type-grid" aria-label="成果类型">
              <button
                v-for="item in submissionTypeOptions"
                :key="item.key"
                type="button"
                :class="{ active: taskSubmissionType(activeTaskSubmissionTask.id) === item.key }"
                @click="setTaskSubmissionType(activeTaskSubmissionTask.id, item.key)"
              >
                <strong>{{ item.label }}</strong>
                <span>{{ item.hint }}</span>
              </button>
            </section>

            <label>
              <span>提交说明</span>
              <textarea v-model="submissionDrafts[activeTaskSubmissionTask.id]" rows="5" placeholder="说明本次提交了什么、完成到哪一步、老师或队长审核时要重点看什么"></textarea>
            </label>

            <section class="submission-links-panel">
              <div class="submission-subhead">
                <div>
                  <strong>成果链接</strong>
                  <span>支持仓库、网盘、在线文档、演示地址、设计稿和视频链接</span>
                </div>
                <button type="button" @click="addSubmissionLink(activeTaskSubmissionTask.id)">添加链接</button>
              </div>
              <div v-if="ensureSubmissionLinks(activeTaskSubmissionTask.id).length" class="submission-link-list">
                <div v-for="(link, index) in ensureSubmissionLinks(activeTaskSubmissionTask.id)" :key="index" class="submission-link-row">
                  <select v-model="link.linkType" aria-label="链接类型">
                    <option v-for="type in submissionLinkTypeOptions" :key="type.key" :value="type.key">{{ type.label }}</option>
                  </select>
                  <input v-model="link.title" placeholder="标题，可不填" />
                  <input v-model="link.url" placeholder="https://..." />
                  <button type="button" @click="removeSubmissionLink(activeTaskSubmissionTask.id, index)">移除</button>
                </div>
              </div>
              <input v-else v-model="submissionLinkDrafts[activeTaskSubmissionTask.id]" placeholder="也可以先粘贴一个链接，提交时会自动保存" />
            </section>

            <DropFileUpload
              :key="`drawer-upload-${activeTaskSubmissionTask.id}-${taskUploadNonce[activeTaskSubmissionTask.id] || 0}`"
              multiple
              size="sm"
              :title="selectedFileName(activeTaskSubmissionTask.id) || '拖拽成果文件到此处，或点击选择'"
              :hint="selectedFileName(activeTaskSubmissionTask.id) ? selectedFileHelp(activeTaskSubmissionTask.id) : '可一次选择多个文件；不同专业成果不需要强行打包'"
              @change="(files) => addTaskFilesFromDrop(activeTaskSubmissionTask, files)"
            />

            <div v-if="taskSubmissionFiles(activeTaskSubmissionTask.id).length" class="submission-file-list">
              <div v-for="file in taskSubmissionFiles(activeTaskSubmissionTask.id)" :key="file.id" class="submission-file-row">
                <div>
                  <strong>{{ file.name }}</strong>
                  <span>{{ attachmentKind(file) }} · {{ formatFileSize(file.size) }}</span>
                </div>
                <button type="button" @click="removeTaskFile(activeTaskSubmissionTask.id, file.id)">移除</button>
              </div>
            </div>

            <button
              type="button"
              class="submission-sync-toggle"
              :class="{ active: taskSubmissionSyncEnabled(activeTaskSubmissionTask.id) }"
              @click="toggleTaskSubmissionSync(activeTaskSubmissionTask.id)"
            >
              <span>{{ taskSubmissionSyncEnabled(activeTaskSubmissionTask.id) ? '已同步材料中心' : '不同步材料中心' }}</span>
              <small>开启后，本次提交的文件和链接会进入资源中心，便于后续复盘和路演调用。</small>
            </button>

            <div v-if="submitLockedReason(activeTaskSubmissionTask)" class="task-submit-lock">
              {{ submitLockedReason(activeTaskSubmissionTask) }}
            </div>

            <footer class="task-drawer-actions">
              <button type="button" @click="closeTaskSubmissionDrawer">取消</button>
              <button class="primary" type="submit" :disabled="submissionUploading[activeTaskSubmissionTask.id] || !canSubmitTask(activeTaskSubmissionTask)">
                {{ submissionUploading[activeTaskSubmissionTask.id] ? '提交中' : '提交成果' }}
              </button>
            </footer>
          </form>
        </aside>
      </div>
    </Teleport>

    <Teleport to="body">
      <div v-if="inspectedDelivery" class="material-inspector-overlay" @click.self="closeMaterialInspector">
        <aside class="material-inspector" role="dialog" aria-modal="true" :aria-label="`查看交付：${inspectedDelivery.title}`">
          <div class="inspector-head">
            <div>
              <span class="kicker">交付详情</span>
              <h3>{{ inspectedDelivery.title }}</h3>
            </div>
            <button type="button" @click="closeMaterialInspector">关闭</button>
          </div>
          <div class="inspector-body">
            <div class="inspector-meta">
              <span>{{ deliveryCategoryLabel(inspectedDelivery) }}</span>
              <b :class="statusClass(inspectedDelivery.status)">{{ materialStatusText(inspectedDelivery.status) }}</b>
              <small>{{ inspectedDelivery.actorLabel }}：{{ inspectedDelivery.actorName || '未分配' }}</small>
              <small>{{ inspectedDelivery.timeLabel }}：{{ formatDate(inspectedDelivery.updatedAt) }}</small>
            </div>
            <p>{{ inspectedDelivery.description || '暂无说明' }}</p>
            <div class="inspector-file">
              <span>{{ deliveryAssetKindLabel(inspectedDelivery) }}</span>
              <strong>{{ deliveryFileName(inspectedDelivery) }}</strong>
              <small v-if="deliveryStorageName(inspectedDelivery)">存储文件：{{ deliveryStorageName(inspectedDelivery) }}</small>
              <small>{{ deliveryInspectHint(inspectedDelivery) }}</small>
              <div class="attachment-actions">
                <button
                  v-if="!isExternalDelivery(inspectedDelivery) && canPreviewAttachment(inspectedDelivery)"
                  type="button"
                  @click="previewAttachment(inspectedDelivery)"
                >
                  在线查看
                </button>
                <button
                  v-if="isExternalDelivery(inspectedDelivery)"
                  type="button"
                  :disabled="!deliveryUrl(inspectedDelivery)"
                  @click="openExternalLink(deliveryUrl(inspectedDelivery))"
                >
                  打开链接
                </button>
                <button
                  v-else
                  type="button"
                  :disabled="!deliveryUrl(inspectedDelivery)"
                  @click="downloadAttachment(inspectedDelivery)"
                >
                  下载文件
                </button>
                <button
                  v-if="canReviewDelivery(inspectedDelivery)"
                  type="button"
                  class="review-open-btn"
                  @click="openDeliveryReview(inspectedDelivery)"
                >
                  审核
                </button>
              </div>
            </div>
          </div>
        </aside>
      </div>
    </Teleport>

    <Teleport to="body">
      <div v-if="activeReviewDelivery" class="material-inspector-overlay" @click.self="closeDeliveryReview">
        <aside class="material-inspector review-dialog" role="dialog" aria-modal="true" :aria-label="`审核交付：${activeReviewDelivery.title}`">
          <div class="inspector-head">
            <div>
              <span class="kicker">审核工作台</span>
              <h3>{{ activeReviewDelivery.title }}</h3>
            </div>
            <button type="button" @click="closeDeliveryReview">关闭</button>
          </div>
          <div class="review-dialog-body">
            <div class="review-dialog-file">
              <span>{{ deliveryCategoryLabel(activeReviewDelivery) }}</span>
              <b :class="statusClass(activeReviewDelivery.status)">{{ materialStatusText(activeReviewDelivery.status) }}</b>
              <strong>{{ deliveryFileName(activeReviewDelivery) }}</strong>
              <small v-if="deliveryStorageName(activeReviewDelivery)">存储文件：{{ deliveryStorageName(activeReviewDelivery) }}</small>
              <small>{{ activeReviewDelivery.actorName }} · {{ formatDate(activeReviewDelivery.updatedAt) }}</small>
              <p>{{ activeReviewDelivery.description || '仅提交了附件，等待审核说明补充。' }}</p>
              <div class="attachment-actions">
                <button v-if="!isExternalDelivery(activeReviewDelivery) && canPreviewAttachment(activeReviewDelivery)" type="button" @click="previewAttachment(activeReviewDelivery)">在线查看</button>
                <button v-if="isExternalDelivery(activeReviewDelivery)" type="button" :disabled="!deliveryUrl(activeReviewDelivery)" @click="openExternalLink(deliveryUrl(activeReviewDelivery))">打开链接</button>
                <button v-else type="button" :disabled="!deliveryUrl(activeReviewDelivery)" @click="downloadAttachment(activeReviewDelivery)">下载文件</button>
              </div>
            </div>
            <label class="review-dialog-comment">
              <span>审核意见</span>
              <textarea v-model="reviewDialogComment" rows="5" placeholder="写明通过依据、退回原因或需要补充的材料"></textarea>
            </label>
          </div>
          <footer class="review-dialog-actions">
            <button type="button" @click="submitDeliveryReview('APPROVED')">通过</button>
            <button type="button" @click="submitDeliveryReview('CHANGES_REQUESTED')">退回修改</button>
            <button type="button" @click="submitDeliveryReview('REJECTED')">驳回</button>
          </footer>
        </aside>
      </div>
    </Teleport>

    <FilePreview
      v-model:visible="filePreviewVisible"
      :file-url="filePreviewUrl"
      :file-name="filePreviewName"
      :file-type="filePreviewType"
      :start-time="filePreviewStartTime"
      @download="onPreviewDownload"
    />

    <Teleport to="body">
      <div v-if="activeEvidenceAnchor" class="material-inspector-overlay" @click.self="closeEvidenceAnchor">
        <aside class="material-inspector evidence-anchor-dialog" role="dialog" aria-modal="true" aria-label="证据详情">
          <div class="inspector-head">
            <div>
              <span class="kicker">证据详情</span>
              <h3>{{ evidenceAnchorText(activeEvidenceAnchor) }}</h3>
            </div>
            <button type="button" @click="closeEvidenceAnchor">关闭</button>
          </div>
          <div class="inspector-body evidence-anchor-body">
            <div class="inspector-meta">
              <span>{{ evidenceTypeText(activeEvidenceAnchor?.type) }}</span>
              <small v-if="activeEvidenceAnchor?.meetingId">会议 {{ activeEvidenceAnchor.meetingId }}</small>
              <small v-if="activeEvidenceAnchor?.sourceRef">来源 {{ activeEvidenceAnchor.sourceRef }}</small>
            </div>
            <p>{{ activeEvidenceExcerpt?.summary || activeEvidenceAnchor?.summary || '该证据用于复核本轮 AI 记忆结论。' }}</p>
            <div v-if="evidenceExcerptLoading" class="evidence-excerpt-state">正在读取 AI 原始片段...</div>
            <div v-else-if="evidenceExcerptError" class="evidence-excerpt-state error">{{ evidenceExcerptError }}</div>
            <pre v-else-if="activeEvidenceExcerpt?.raw" class="evidence-raw">{{ formatEvidenceRaw(activeEvidenceExcerpt.raw) }}</pre>
          </div>
        </aside>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { computed, h, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import DOMPurify from 'dompurify'
import request from '../utils/request'
import { getStoredUser } from '../utils/authStorage'
import FilePreview from '../components/FilePreview.vue'
import DropFileUpload from '../components/base/DropFileUpload.vue'
import AiScoreControl from '../components/ai-score/AiScoreControl.vue'

const iconPaths = {
  inbox: ['M4 14h4l2 3h4l2-3h4', 'M6 6h12l2 8v4H4v-4l2-8Z'],
  mine: ['M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z', 'M4 21a8 8 0 0 1 16 0'],
  review: ['M5 4h14v16H5z', 'M8 8h8', 'M8 12h5', 'M16 14l2 2-3 3-2-2 3-3Z'],
  score: ['M12 3l2.6 5.3 5.9.9-4.3 4.2 1 5.9L12 16.6 6.8 19.4l1-5.9-4.3-4.2 5.9-.9L12 3Z'],
  blocked: ['M12 4a8 8 0 1 0 0 16 8 8 0 0 0 0-16Z', 'M8 8l8 8'],
  materials: ['M5 5h6l2 2h6v12H5z', 'M8 11h8', 'M8 15h5'],
  tasks: ['M6 5h12v14H6z', 'M9 9h6', 'M9 13h6', 'M9 17h3'],
  members: ['M8 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z', 'M16 11a3 3 0 1 0 0-6', 'M3 20a5 5 0 0 1 10 0', 'M14 18a5 5 0 0 1 7 2'],
  versions: ['M7 7h10v12H7z', 'M5 5h10', 'M9 3h10v12'],
  roadshow: ['M5 17h14', 'M7 17V7h10v10', 'M9 10h6', 'M10 13h4'],
  stage: ['M4 6h16', 'M4 12h16', 'M4 18h16', 'M8 6v12'],
  course: ['M5 6.5 12 4l7 2.5v11L12 20l-7-2.5v-11Z', 'M12 4v16', 'M8 8.5l4-1.5 4 1.5'],
  ability: ['M12 4v3', 'M12 17v3', 'M5 12h3', 'M16 12h3', 'M8 8l8 8', 'M16 8l-8 8'],
  rehearsal: ['M6 17c2-4 10-4 12 0', 'M8 14l-3 3 3 3', 'M16 10l3-3-3-3', 'M5 7c2-4 10-4 12 0'],
  final: ['M12 4l2 5h5l-4 3 1.5 5-4.5-3-4.5 3L9 12 5 9h5l2-5Z'],
  all: ['M5 5h6v6H5z', 'M13 5h6v6h-6z', 'M5 13h6v6H5z', 'M13 13h6v6h-6z'],
  prepare: ['M6 4h12v16H6z', 'M9 8h6', 'M9 12h6', 'M9 16h3'],
  task: ['M6 5h12v14H6z', 'M9 9h6', 'M9 13h6', 'M9 17h3'],
  material: ['M5 5h6l2 2h6v12H5z', 'M8 12h8'],
  member: ['M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z', 'M4 21a8 8 0 0 1 16 0'],
  system: ['M12 3v3', 'M12 18v3', 'M4.8 7.2l2.1 2.1', 'M17.1 16.7l2.1 2.1', 'M3 12h3', 'M18 12h3', 'M4.8 16.8l2.1-2.1', 'M17.1 7.3l2.1-2.1', 'M9 12a3 3 0 1 0 6 0 3 3 0 0 0-6 0Z']
}

const SvgIcon = (props) => {
  const paths = iconPaths[props.name] || iconPaths.task
  return h('svg', { viewBox: '0 0 24 24', class: 'rail-svg-icon', 'aria-hidden': 'true', focusable: 'false' }, paths.map((d) => h('path', { d })))
}

function stageIconName(key) {
  const normalized = String(key || '').toUpperCase()
  const map = {
    ALL: 'all',
    COURSE: 'course',
    TOPIC: 'course',
    PLAN: 'review',
    ABILITY: 'ability',
    MATERIAL: 'materials',
    ROADSHOW: 'roadshow',
    REHEARSAL: 'rehearsal',
    FINAL: 'final',
    REVIEW: 'score'
  }
  return map[normalized] || 'stage'
}

const validWorkViews = ['inbox', 'mine', 'review', 'score', 'blocked']
const router = useRouter()
const route = useRoute()
const isTaskDetailRoute = computed(() => Boolean(route.params.workItemId))
const loading = ref(false)
const teamLoadError = ref('')
const storedUser = ref(getStoredUser())
const teams = ref([])
const selectedTeamId = ref(null)
const dashboard = ref(null)
const taskComposerOpen = ref(false)
const workbenchTab = ref('TASKS')
const taskFilter = ref('ALL')
const simpleTaskFilter = ref('ALL')
const focusedTaskSourceFilter = ref('ALL')
const focusedTaskKeyword = ref('')
const deliveryFilter = ref('ALL')
const activeTeamSection = ref('overview')
const activeWorkView = ref(validWorkViews.includes(String(route.query.workView)) ? String(route.query.workView) : 'inbox')
const activeStageFilter = ref(route.query.stageFilter ? String(route.query.stageFilter).toUpperCase() : 'ALL')
const activeRailMode = ref(route.query.stageFilter ? 'stage' : 'work')
const workFilterOpen = ref(false)
const workTypeFilter = ref('ALL')
const workSortMode = ref('smart')
const workDensity = ref('comfortable')
const workSummaryVisible = ref(true)
const collapsedRailGroups = reactive({ stage: false, team: false, quick: false })
const projectSwitcherOpen = ref(false)
const taskSwitcherRef = ref(null)
const selectedWorkItemId = ref('')
const activeTaskDetailItemId = ref('')
const activeTaskSubmissionItemId = ref('')
const materialTypeFilter = ref('ALL')
const activityFilter = ref('ALL')
const inspectedDeliveryId = ref(null)
const activeReviewDeliveryId = ref(null)
const reviewDialogComment = ref('')
const activeAbilityUserId = ref(null)
const candidateMembers = ref([])
const creatingProject = ref(false)
const projectDialogOpen = ref(false)
const selectedRoadshowMeetingId = ref('')
const roadshowMemory = ref(null)
const roadshowMemoryLoading = ref(false)
const roadshowMemoryError = ref('')
const positionSaving = ref(false)
const stageEditorOpen = ref(false)
const stageEditorSaving = ref(false)
const stageEditorForm = reactive({
  stageKey: '',
  title: '',
  startDate: '',
  dueDate: '',
  optionalMode: 'required',
  suggestion: ''
})
const customPositionRoles = ref([])
const addingPositionRole = ref(false)
const newPositionRole = reactive({ name: '', description: '' })

const filePreviewVisible = ref(false)
const filePreviewUrl = ref('')
const filePreviewName = ref('')
const filePreviewType = ref('')
const filePreviewStartTime = ref(0)
const activeEvidenceAnchor = ref(null)
const activeEvidenceExcerpt = ref(null)
const evidenceExcerptLoading = ref(false)
const evidenceExcerptError = ref('')
const evidenceBlobUrl = ref('')

const captainPermissionOptions = [
  { key: 'ASSIGN_TASK', label: '分配任务', help: '创建任务、指定负责人和时间周期' },
  { key: 'REVIEW_SUBMISSION', label: '审核提交', help: '审核队员任务成果和版本' },
  { key: 'REVIEW_MATERIAL', label: '审核材料', help: '通过或退回项目材料、PPT、逐字稿' },
  { key: 'BIND_ROADSHOW', label: '绑定路演', help: '关联会议室路演评分和复盘数据' }
]

const defaultPositionRoles = [
  { name: '项目经理', description: '统筹项目计划、进度、风险和团队协作' },
  { name: '产品经理', description: '梳理需求、用户价值、产品方案和演示逻辑' },
  { name: '前端开发工程师', description: '负责前端页面、交互体验和演示界面实现' },
  { name: '后端开发工程师', description: '负责接口、数据库、服务稳定性和数据闭环' },
  { name: '算法工程师', description: '负责AI能力、模型调用、数据分析和效果验证' },
  { name: '测试工程师', description: '负责测试用例、缺陷跟踪、验收和质量保障' },
  { name: 'UI/UX设计师', description: '负责视觉规范、交互流程和路演展示体验' },
  { name: '路演主讲', description: '负责路演表达、答辩组织和现场节奏控制' },
  { name: '资料负责人', description: '负责周报、PPT、逐字稿和佐证材料归档' },
  { name: '运维部署工程师', description: '负责部署环境、演示设备和运行保障' }
]

const projectForm = reactive({
  name: '',
  description: '',
  captainUserId: '',
  captainPositionName: '项目经理',
  captainResponsibility: '',
  memberUserIds: [],
  memberPositions: {},
  memberResponsibilities: {},
  captainPermissions: captainPermissionOptions.map((item) => item.key)
})

const memberPositionForm = reactive({
  userId: null,
  positionName: '',
  responsibility: ''
})

const memberFilters = reactive({
  keyword: '',
  userGroup: 'ALL',
  schoolName: 'ALL',
  collegeName: 'ALL',
  className: 'ALL',
  role: 'STUDENT'
})

const taskForm = reactive({
  title: '',
  description: '',
  taskType: 'COURSE_LEARNING',
  customTaskType: '',
  timeSlot: 'MORNING',
  ownerUserId: '',
  ownerUserIds: [],
  stageKey: 'MATERIAL',
  priority: 'MEDIUM',
  startAt: '',
  dueAt: ''
})

const roadshowForm = reactive({
  meetingId: '',
  manualMeetingId: '',
  roadshowType: 'REHEARSAL'
})

const submissionDrafts = reactive({})
const submissionLinkDrafts = reactive({})
const submissionFiles = reactive({})
const submissionFileMeta = reactive({})
const submissionFileQueues = reactive({})
const submissionRetainedAssets = reactive({})
const submissionLinks = reactive({})
const submissionTypeDrafts = reactive({})
const submissionSyncDrafts = reactive({})
const submissionUploading = reactive({})
const detailSubmissionEditorOpen = ref(false)
const detailHistoryExpanded = ref(false)
const detailTaskBookExpanded = ref(false)
const detailTaskBookPayload = ref({})
const detailTaskBookLoading = ref(false)
const detailTaskBookError = ref('')
const reviewDrafts = reactive({})
const materialReviewDrafts = reactive({})

const dimensions = [
  { key: 'problemSolving', label: '解决问题' },
  { key: 'coding', label: '代码能力' },
  { key: 'communication', label: '沟通能力' },
  { key: 'teamwork', label: '团队协作' },
  { key: 'presentation', label: '演讲能力' },
  { key: 'creativity', label: '创意能力' }
]
const radarRings = [20, 40, 60, 80, 100]
const taskStatusTabs = [
  { key: 'ALL', label: '全部' },
  { key: 'TODO', label: '待处理' },
  { key: 'IN_PROGRESS', label: '进行中' },
  { key: 'REVIEWING', label: '待审核' },
  { key: 'CHANGES_REQUESTED', label: '需修改' },
  { key: 'DONE', label: '已完成' }
]
const taskTypeOptions = [
  { key: 'COURSE_LEARNING', label: '课程学习', defaultStage: 'COURSE' },
  { key: 'EXAM_TASK', label: '考试任务', defaultStage: 'ABILITY' },
  { key: 'PPT_TASK', label: 'PPT任务', defaultStage: 'MATERIAL' },
  { key: 'SCRIPT_TASK', label: '讲稿任务', defaultStage: 'MATERIAL' },
  { key: 'OTHER_BUSINESS', label: '其他业务', defaultStage: 'REVIEW' },
  { key: 'CUSTOM', label: '自定义新增任务', defaultStage: 'MATERIAL' }
]
const taskTimeSlotOptions = [
  { key: 'MORNING', label: '上午', hint: '08:30-12:00', start: '08:30', end: '12:00' },
  { key: 'AFTERNOON', label: '下午', hint: '14:00-18:00', start: '14:00', end: '18:00' },
  { key: 'EVENING', label: '晚上', hint: '19:30-22:00', start: '19:30', end: '22:00' }
]
const deliveryStatusTabs = [
  { key: 'ALL', label: '全部' },
  { key: 'PENDING_REVIEW', label: '待审核' },
  { key: 'CHANGES_REQUESTED', label: '需修改' },
  { key: 'DRAFT', label: '草稿' },
  { key: 'APPROVED', label: '已通过' }
]
const teamNavItems = [
  { key: 'overview', label: '工作中枢', icon: 'inbox' },
  { key: 'materials', label: '资料库', icon: 'materials' },
  { key: 'tasks', label: '任务管理', icon: 'tasks' },
  { key: 'members', label: '团队成员', icon: 'members' },
  { key: 'versions', label: '作品版本', icon: 'versions' },
  { key: 'review', label: '路演复盘', icon: 'roadshow' }
]
const workViewItems = [
  { key: 'inbox', label: '收件箱', icon: 'inbox' },
  { key: 'mine', label: '我的工作', icon: 'mine' },
  { key: 'review', label: '待审核', icon: 'review' },
  { key: 'score', label: '评分扣分项', icon: 'score' },
  { key: 'blocked', label: '过期/阻塞', icon: 'blocked' }
]

const simpleTaskFilters = [
  { key: 'ALL', label: '全部' },
  { key: 'MINE', label: '我的' },
  { key: 'TODO', label: '待处理' },
  { key: 'IN_PROGRESS', label: '进行中' },
  { key: 'DONE', label: '已完成' },
  { key: 'EXPIRED', label: '已过期' }
]

const fallbackStageFilters = [
  { key: 'COURSE', label: '课程学习' },
  { key: 'ABILITY', label: '能力测评' },
  { key: 'MATERIAL', label: '材料准备' },
  { key: 'ROADSHOW', label: '路演展示' },
  { key: 'REVIEW', label: '复盘提升' }
]
const materialTypeTabs = [
  { key: 'ALL', label: '全部' },
  { key: 'PPT', label: 'PPT' },
  { key: 'SCRIPT', label: '讲稿' },
  { key: 'VIDEO', label: '视频' },
  { key: 'IMAGE', label: '图片' },
  { key: 'DOC', label: '证明材料' },
  { key: 'DATA', label: '数据表' },
  { key: 'OTHER', label: '其他' }
]
const submissionTypeOptions = [
  { key: 'DOCUMENT', label: '文档', hint: '方案、报告、证明材料、PDF' },
  { key: 'PPT', label: 'PPT', hint: '路演稿、答辩稿、展示材料' },
  { key: 'SCRIPT', label: '讲稿', hint: '逐字稿、讲解稿、答辩话术' },
  { key: 'CODE', label: '代码', hint: '源码、仓库、部署包' },
  { key: 'VIDEO', label: '视频', hint: '演示录屏、作品视频、路演录像' },
  { key: 'DATA', label: '数据', hint: '数据集、表格、测试结果' },
  { key: 'DESIGN', label: '设计', hint: '原型、UI稿、模型图' },
  { key: 'PACKAGE', label: '压缩包', hint: '多材料打包提交' },
  { key: 'LINK', label: '链接', hint: '网盘、仓库、演示地址' },
  { key: 'OTHER', label: '其他', hint: '跨专业自定义成果' }
]
const submissionLinkTypeOptions = [
  { key: 'DEMO', label: '演示地址' },
  { key: 'REPO', label: '代码仓库' },
  { key: 'CLOUD', label: '网盘链接' },
  { key: 'DESIGN', label: '设计稿' },
  { key: 'VIDEO', label: '视频链接' },
  { key: 'DOC', label: '在线文档' },
  { key: 'OTHER', label: '其他链接' }
]

onMounted(fetchTeams)
onMounted(fetchPositionRoles)
onMounted(() => {
  document.addEventListener('pointerdown', closeProjectSwitcherOnOutside, true)
})
onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', closeProjectSwitcherOnOutside, true)
})

function closeProjectSwitcherOnOutside(event) {
  if (!projectSwitcherOpen.value) return
  const target = event.target
  if (taskSwitcherRef.value && target instanceof Node && taskSwitcherRef.value.contains(target)) return
  projectSwitcherOpen.value = false
}

async function fetchTeams() {
  loading.value = true
  teamLoadError.value = ''
  dashboard.value = null
  try {
    const res = await request.get('/api/project-teams/my')
    teams.value = res.data || []
    const queryTeamId = route.query.teamId ? Number(route.query.teamId) : null
    const matchedTeam = queryTeamId ? teams.value.find((item) => Number(item.id) === queryTeamId) : null
    selectedTeamId.value = matchedTeam?.id || teams.value[0]?.id || null
    if (selectedTeamId.value) await fetchDashboard()
    if (!selectedTeamId.value) {
      teams.value = []
    }
  } catch (error) {
    teams.value = []
    selectedTeamId.value = null
    dashboard.value = null
    teamLoadError.value = error?.response?.data?.message || error?.message || '请检查登录状态、接口服务或当前账号是否具备项目团队访问权限。'
  } finally {
    loading.value = false
  }
}

async function fetchDashboard() {
  if (!selectedTeamId.value) return
  const res = await request.get(`/api/project-teams/${selectedTeamId.value}/dashboard`)
  dashboard.value = res.data
  applyTaskDeepLink()
  activeAbilityUserId.value = abilities.value[0]?.userId || members.value[0]?.userId || null
  selectedRoadshowMeetingId.value = String(roadshow.value?.meetingId || roadshowMeetings.value[0]?.meetingId || '')
  await fetchRoadshowMemory()
  if (canTeachObserve.value) await fetchCandidateMembers()
}

async function fetchDetailTaskBook() {
  const taskId = Number(detailTask.value?.id || detailTask.value?.taskId)
  if (!isTaskDetailRoute.value || !selectedTeamId.value || !Number.isFinite(taskId)) {
    detailTaskBookPayload.value = {}
    detailTaskBookError.value = ''
    return
  }
  detailTaskBookLoading.value = true
  detailTaskBookError.value = ''
  try {
    const res = await request.get(`/api/project-teams/${selectedTeamId.value}/tasks/${taskId}`)
    detailTaskBookPayload.value = res.data || {}
  } catch (error) {
    detailTaskBookPayload.value = {}
    detailTaskBookError.value = error?.response?.data?.message || error?.message || '完整任务书暂时没有加载出来。'
  } finally {
    detailTaskBookLoading.value = false
  }
}

async function toggleDetailTaskBook() {
  detailTaskBookExpanded.value = !detailTaskBookExpanded.value
  if (!detailTaskBookExpanded.value) return
  if (detailTaskBookLoading.value || Object.keys(detailTaskBookPayload.value || {}).length) return
  await fetchDetailTaskBook()
}

async function fetchRoadshowMemory() {
  if (!selectedTeamId.value) {
    roadshowMemory.value = null
    return
  }
  roadshowMemoryLoading.value = true
  roadshowMemoryError.value = ''
  try {
    const res = await request.get(`/api/project-teams/${selectedTeamId.value}/roadshow-memory`)
    roadshowMemory.value = res.data || {}
  } catch (error) {
    roadshowMemory.value = null
    roadshowMemoryError.value = error?.response?.data?.message || '连续评分记忆暂不可用'
  } finally {
    roadshowMemoryLoading.value = false
  }
}

function syncMemberPositionForm() {
  const member = activeMember.value
  memberPositionForm.userId = member?.userId || null
  memberPositionForm.positionName = member?.positionName || ''
  memberPositionForm.responsibility = member?.responsibility || ''
}

async function selectTeam(teamId) {
  selectedTeamId.value = teamId
  router.replace({
    path: '/project-team',
    query: {
      ...route.query,
      workView: activeWorkView.value,
      teamId
    }
  })
  await fetchDashboard()
}

async function selectTeamFromSwitcher(teamId) {
  projectSwitcherOpen.value = false
  if (Number(selectedTeamId.value) === Number(teamId)) return
  await selectTeam(teamId)
}

async function createTask() {
  if (!selectedTeamId.value) return
  if (!taskForm.title.trim()) {
    ElMessage.warning('请填写任务标题')
    return
  }
  if (taskForm.taskType === 'CUSTOM' && !taskForm.customTaskType.trim()) {
    ElMessage.warning('请填写自定义任务类型')
    return
  }
  const taskTypeLabel = resolveTaskTypeLabel(taskForm)
  await request.post(`/api/project-teams/${selectedTeamId.value}/tasks`, {
    ...taskForm,
    taskType: taskForm.taskType,
    taskTypeLabel,
    businessType: taskForm.taskType,
    businessTypeLabel: taskTypeLabel,
    timeSlot: taskForm.timeSlot,
    timePeriod: taskForm.timeSlot,
    ownerUserId: taskForm.ownerUserIds.length ? Number(taskForm.ownerUserIds[0]) : null,
    assigneeUserIds: taskForm.ownerUserIds.map((id) => Number(id)),
    startAt: taskForm.startAt ? taskForm.startAt.replace('T', ' ') : null,
    dueAt: taskForm.dueAt ? taskForm.dueAt.replace('T', ' ') : null
  })
  Object.assign(taskForm, { title: '', description: '', taskType: 'COURSE_LEARNING', customTaskType: '', timeSlot: 'MORNING', ownerUserId: '', ownerUserIds: [], stageKey: 'COURSE', priority: 'MEDIUM', startAt: '', dueAt: '' })
  applyTaskTimeSlot('MORNING')
  taskComposerOpen.value = false
  await fetchDashboard()
}

function openTaskDialog() {
  if (!taskForm.startAt) applyTaskTimeSlot(taskForm.timeSlot || 'MORNING')
  taskComposerOpen.value = true
}

function closeTaskDialog() {
  taskComposerOpen.value = false
}

function toggleTaskAssignee(userId) {
  const id = Number(userId)
  const index = taskForm.ownerUserIds.findIndex((item) => Number(item) === id)
  if (index >= 0) {
    taskForm.ownerUserIds.splice(index, 1)
  } else {
    taskForm.ownerUserIds.push(id)
  }
  taskForm.ownerUserId = taskForm.ownerUserIds[0] || ''
}

function selectTaskType(type) {
  taskForm.taskType = type
  const option = taskTypeOptions.find((item) => item.key === type)
  if (option?.defaultStage && stages.value.some((stage) => normalStageKey(stage.stageKey) === normalStageKey(option.defaultStage))) {
    taskForm.stageKey = option.defaultStage
  }
}

function applyTaskTimeSlot(slot) {
  taskForm.timeSlot = slot
  const option = taskTimeSlotOptions.find((item) => item.key === slot) || taskTimeSlotOptions[0]
  const date = datePart(taskForm.startAt || taskForm.dueAt || currentDateTimeLocal())
  taskForm.startAt = `${date}T${option.start}`
  taskForm.dueAt = `${date}T${option.end}`
}

async function fetchCandidateMembers() {
  const res = await request.get('/api/project-teams/candidate-members')
  candidateMembers.value = (res.data || []).map(normalizeCandidateMember)
}

async function fetchPositionRoles() {
  try {
    const res = await request.get('/api/project-teams/position-roles')
    customPositionRoles.value = res.data || []
  } catch (error) {
    customPositionRoles.value = []
  }
}

async function createPositionRole() {
  const name = newPositionRole.name.trim()
  if (!name) {
    ElMessage.warning('请输入岗位名称')
    return
  }
  addingPositionRole.value = true
  try {
    const res = await request.post('/api/project-teams/position-roles', {
      name,
      description: newPositionRole.description.trim()
    })
    await fetchPositionRoles()
    const created = res.data?.name || name
    newPositionRole.name = ''
    newPositionRole.description = ''
    ElMessage.success(`岗位「${created}」已添加`)
    return created
  } finally {
    addingPositionRole.value = false
  }
}

async function addMemberPositionRole() {
  const created = await createPositionRole()
  if (created) {
    memberPositionForm.positionName = created
    if (!memberPositionForm.responsibility) {
      memberPositionForm.responsibility = defaultResponsibilityForPosition(created)
    }
  }
}

async function openProjectDialog() {
  if (!candidateMembers.value.length) await fetchCandidateMembers()
  await fetchPositionRoles()
  projectDialogOpen.value = true
}

function closeProjectDialog() {
  projectDialogOpen.value = false
}

function normalizeCandidateMember(user) {
  return {
    ...user,
    id: Number(user.id),
    username: user.username || `用户 ${user.id}`,
    email: user.email || '',
    role: user.role || 'STUDENT',
    schoolName: user.schoolName || '未设置学校',
    collegeName: user.collegeName || '未设置学院',
    className: user.className || '未设置班级',
    userGroup: user.userGroup || user.role || '默认用户组'
  }
}

function selectFilteredMembers() {
  const merged = new Set(projectForm.memberUserIds.map(Number))
  filteredCandidateMembers.value.forEach((user) => {
    merged.add(Number(user.id))
    ensureProjectMemberPosition(user.id)
  })
  projectForm.memberUserIds = Array.from(merged)
}

function removeSelectedMember(userId) {
  projectForm.memberUserIds = projectForm.memberUserIds.filter((id) => Number(id) !== Number(userId))
  delete projectForm.memberPositions[userId]
  delete projectForm.memberResponsibilities[userId]
}

function ensureProjectMemberPosition(userId) {
  const key = String(userId)
  if (!projectForm.memberPositions[key]) projectForm.memberPositions[key] = '产品经理'
}

function resetProjectForm() {
  Object.assign(projectForm, {
    name: '',
    description: '',
    captainUserId: '',
    captainPositionName: '项目经理',
    captainResponsibility: '',
    memberUserIds: [],
    captainPermissions: captainPermissionOptions.map((item) => item.key)
  })
  clearReactiveObject(projectForm.memberPositions)
  clearReactiveObject(projectForm.memberResponsibilities)
}

function clearReactiveObject(target) {
  Object.keys(target).forEach((key) => delete target[key])
}

function defaultResponsibilityForPosition(positionName) {
  return positionRoles.value.find((item) => item.name === positionName)?.description || '按团队任务节点完成交付并同步进度'
}

async function createProject() {
  if (!projectForm.name.trim() || !projectForm.captainUserId) return
  creatingProject.value = true
  try {
    const memberAssignments = selectedCandidateMembers.value.map((user) => {
      const key = String(user.id)
      const positionName = projectForm.memberPositions[key] || '项目成员'
      return {
        userId: Number(user.id),
        positionName,
        responsibility: projectForm.memberResponsibilities[key] || defaultResponsibilityForPosition(positionName)
      }
    })
    const res = await request.post('/api/project-teams', {
      name: projectForm.name.trim(),
      description: projectForm.description.trim(),
      captainUserId: Number(projectForm.captainUserId),
      captainPositionName: projectForm.captainPositionName || '项目经理',
      captainResponsibility: projectForm.captainResponsibility || defaultResponsibilityForPosition(projectForm.captainPositionName),
      memberUserIds: projectForm.memberUserIds.map(Number),
      memberAssignments,
      captainPermissions: projectForm.captainPermissions
    })
    const createdId = res.data?.id
    resetProjectForm()
    projectDialogOpen.value = false
    const teamsRes = await request.get('/api/project-teams/my')
    teams.value = teamsRes.data || []
    selectedTeamId.value = createdId || teams.value[0]?.id || null
    if (selectedTeamId.value) await fetchDashboard()
  } finally {
    creatingProject.value = false
  }
}

async function saveMemberPosition() {
  if (!selectedTeamId.value || !memberPositionForm.userId || !memberPositionForm.positionName) return
  positionSaving.value = true
  try {
    await request.patch(`/api/project-teams/${selectedTeamId.value}/members/${memberPositionForm.userId}/position`, {
      positionName: memberPositionForm.positionName,
      responsibility: memberPositionForm.responsibility || defaultResponsibilityForPosition(memberPositionForm.positionName)
    })
    ElMessage.success('岗位角色已更新')
    await fetchDashboard()
  } finally {
    positionSaving.value = false
  }
}

function openStageEditor(stage) {
  if (!canEditStageSchedule.value) return
  stageEditorForm.stageKey = stage?.stageKey || ''
  stageEditorForm.title = stage?.title || ''
  stageEditorForm.startDate = stageDateInput(stage?.startDate)
  stageEditorForm.dueDate = stageDateInput(stage?.dueDate)
  stageEditorForm.optionalMode = stage?.optional ? 'optional' : 'required'
  stageEditorForm.suggestion = stage?.suggestion || ''
  stageEditorOpen.value = true
}

function closeStageEditor() {
  stageEditorOpen.value = false
}

async function saveStageEditor() {
  if (!canEditStageSchedule.value) {
    ElMessage.warning('仅管理员或指导教师可修改阶段配置')
    return
  }
  if (!selectedTeamId.value || !stageEditorForm.stageKey) return
  if (!stageEditorForm.title.trim()) {
    ElMessage.warning('请填写阶段名称')
    return
  }
  if (!stageEditorForm.startDate || !stageEditorForm.dueDate) {
    ElMessage.warning('请填写开始和截止日期')
    return
  }
  if (stageEditorForm.startDate > stageEditorForm.dueDate) {
    ElMessage.warning('开始日期不能晚于截止日期')
    return
  }
  stageEditorSaving.value = true
  try {
    await request.patch(`/api/project-teams/${selectedTeamId.value}/stages/${stageEditorForm.stageKey}`, {
      title: stageEditorForm.title.trim(),
      startDate: stageEditorForm.startDate,
      dueDate: stageEditorForm.dueDate,
      optional: stageEditorForm.optionalMode === 'optional',
      suggestion: stageEditorForm.suggestion.trim()
    })
    ElMessage.success('阶段配置已更新')
    stageEditorOpen.value = false
    await fetchDashboard()
  } catch (error) {
    ElMessage.error(error?.message || '更新阶段配置失败')
  } finally {
    stageEditorSaving.value = false
  }
}

function stageDateInput(value) {
  if (!value) return ''
  return String(value).slice(0, 10)
}

function formatStageDate(value) {
  if (!value) return '未设置'
  return String(value).slice(0, 10)
}

function taskSubmissionContent(task) {
  if (!task?.id) return ''
  return String(submissionDrafts[task.id] || '').trim()
}

async function submitTask(task) {
  if (!canSubmitTask(task)) {
    ElMessage.warning(submitLockedReason(task) || '当前任务暂不可提交')
    return false
  }
  const content = taskSubmissionContent(task)
  const queuedFiles = taskSubmissionFiles(task.id)
  const links = taskSubmissionLinks(task.id)
  const legacyLink = String(submissionLinkDrafts[task.id] || '').trim()
  if (legacyLink) {
    links.push({ title: '成果链接', url: legacyLink, linkType: 'OTHER' })
  }
  if (!content && !queuedFiles.length && !links.length) {
    ElMessage.warning('请填写提交说明、成果链接或上传成果文件')
    return false
  }
  submissionUploading[task.id] = true
  try {
    const assets = retainedSubmissionAssets(task.id).map((asset) => ({
      assetKind: asset.assetKind || 'MAIN',
      fileUrl: asset.fileUrl || asset.url || asset.attachmentUrl,
      fileName: asset.fileName || asset.name || asset.attachmentName,
      fileSize: asset.fileSize || asset.size || asset.attachmentSize || 0,
      fileType: asset.fileType || asset.type || asset.attachmentType || ''
    })).filter((asset) => asset.fileUrl)
    for (const item of queuedFiles) {
      const attachment = await uploadTaskAttachment(item.file)
      if (!attachment.fileUrl) {
        ElMessage.error('文件上传未返回有效地址，请重试')
        throw new Error('文件上传成功但未返回文件地址')
      }
      assets.push(attachment)
    }
    const response = await request.post(`/api/project-teams/tasks/${task.id}/submissions`, {
      content,
      submissionType: taskSubmissionType(task.id),
      syncToMaterial: taskSubmissionSyncEnabled(task.id),
      assets,
      links
    })
    resetSubmissionDraft(task.id)
    await fetchDashboard()
    ElMessage.success('成果已提交，等待审核')
    return response.data || response
  } catch (error) {
    ElMessage.error(error?.message || '提交成果失败')
    return false
  } finally {
    submissionUploading[task.id] = false
  }
}

async function submitTaskFromDrawer(task) {
  const result = await submitTask(task)
  if (result) closeTaskSubmissionDrawer()
}

async function reviewSubmission(item, status, comment = reviewDrafts[item.id] || '') {
  await request.post(`/api/project-teams/submissions/${item.id}/review`, {
    status,
    reviewComment: comment
  })
  reviewDrafts[item.id] = ''
  await fetchDashboard()
}

async function reviewMaterial(item, reviewStatus, comment = materialReviewDrafts[item.id] || '') {
  await request.post(`/api/project-teams/materials/${item.id}/review`, {
    reviewStatus,
    reviewComment: comment
  })
  materialReviewDrafts[item.id] = ''
  await fetchDashboard()
}

async function bindRoadshow() {
  if (!selectedTeamId.value) return
  const meetingId = Number(roadshowForm.meetingId || roadshowForm.manualMeetingId)
  if (!meetingId) {
    ElMessage.warning('请选择可绑定会议，或输入会议 ID')
    return
  }
  await request.post(`/api/project-teams/${selectedTeamId.value}/roadshows/bind`, {
    meetingId,
    roadshowType: roadshowForm.roadshowType
  })
  roadshowForm.meetingId = ''
  roadshowForm.manualMeetingId = ''
  selectedRoadshowMeetingId.value = String(meetingId)
  await fetchDashboard()
  ElMessage.success('已绑定到本团队')
}

async function resolveSpeaker(speaker, action, matchedUserId) {
  if (!speaker?.id) return
  try {
    await request.post(`/api/project-teams/roadshow-speakers/${speaker.id}/resolve`, {
      action,
      matchedUserId: matchedUserId != null ? Number(matchedUserId) : undefined
    })
    await fetchDashboard()
    ElMessage.success('已更新发言人对齐')
  } catch (error) {
    ElMessage.error(error?.response?.data?.message || '操作失败，请重试')
  }
}

function confirmSpeaker(speaker) {
  resolveSpeaker(speaker, 'CONFIRM')
}

function rejectSpeaker(speaker) {
  resolveSpeaker(speaker, 'REJECT')
}

function resetSpeaker(speaker) {
  resolveSpeaker(speaker, 'RESET')
}

function onReassignSpeaker(speaker, event) {
  const value = event?.target?.value
  if (!value) return
  resolveSpeaker(speaker, 'ASSIGN', value)
  if (event?.target) event.target.value = ''
}

function speakerMethodLabel(method) {
  const labels = { NAME: '按姓名', ROLE_ALIGN: '按岗位', ATTENDANCE: '按出席', TEACHER: '教师指定', NONE: '未匹配' }
  return labels[method] || method || '未匹配'
}

function speakerStatusLabel(status) {
  const labels = { AUTO: 'AI 待确认', CONFIRMED: '已确认', REJECTED: '已忽略' }
  return labels[status] || status || 'AI 待确认'
}

function speakerConfidence(speaker) {
  const value = Number(speaker?.matchConfidence || 0)
  if (!value) return '—'
  return `${Math.round(value * 100)}%`
}

const team = computed(() => dashboard.value?.team || {})
const metrics = computed(() => dashboard.value?.metrics || {})
const members = computed(() => dashboard.value?.members || [])
const positionRoles = computed(() => {
  if (customPositionRoles.value.length) return customPositionRoles.value
  const roles = dashboard.value?.positionRoles || []
  return roles.length ? roles : defaultPositionRoles
})
const stages = computed(() => dashboard.value?.stages || [])
const tasks = computed(() => dashboard.value?.tasks || [])
const submissions = computed(() => dashboard.value?.submissions || [])
const materials = computed(() => dashboard.value?.materials || [])
const roadshow = computed(() => dashboard.value?.roadshow || {})
const roadshowMeetings = computed(() => dashboard.value?.roadshowMeetings || [])
const bindableRoadshowMeetings = computed(() => dashboard.value?.bindableRoadshowMeetings || [])
const reviewIssues = computed(() => dashboard.value?.reviewIssues || [])
const abilities = computed(() => dashboard.value?.abilities || [])
const teacherObservation = computed(() => dashboard.value?.teacherObservation || {})
const roadshowSpeakers = computed(() => teacherObservation.value?.roadshowSpeakers || [])
const currentUserId = computed(() => dashboard.value?.currentUserId || null)
const canManage = computed(() => Boolean(dashboard.value?.canManage))
const canTeachObserve = computed(() => Boolean(dashboard.value?.canTeachObserve))
const storedRole = computed(() => String(storedUser.value?.role || '').toUpperCase())
const canCreateProjectFromUser = computed(() => ['ADMIN', 'SCHOOL_ADMIN', 'TEACHER'].includes(storedRole.value))
const myRoleInTeam = computed(() => dashboard.value?.myRoleInTeam || 'MEMBER')
const managementPermissions = computed(() => dashboard.value?.managementPermissions || {})
const canAssignTask = computed(() => Boolean(managementPermissions.value.ASSIGN_TASK))
const canEditStageSchedule = computed(() => dashboard.value?.canEditStageSchedule === true)
const canReviewSubmission = computed(() => Boolean(managementPermissions.value.REVIEW_SUBMISSION))
const canReviewMaterial = computed(() => Boolean(managementPermissions.value.REVIEW_MATERIAL))
const canBindRoadshow = computed(() => Boolean(managementPermissions.value.BIND_ROADSHOW))
const canShowTaskManagement = computed(() => Boolean(canManage.value || canTeachObserve.value))
const activeMember = computed(() => members.value.find((member) => Number(member.userId) === Number(activeAbilityUserId.value)) || null)

watch(activeAbilityUserId, syncMemberPositionForm)
watch(members, syncMemberPositionForm)
watch(() => route.query.workView, (value) => {
  if (validWorkViews.includes(String(value))) {
    activeTeamSection.value = 'overview'
    activeRailMode.value = 'work'
    activeStageFilter.value = 'ALL'
    activeWorkView.value = String(value)
  }
})
watch(() => route.query.stageFilter, (value) => {
  if (value) {
    activeTeamSection.value = 'overview'
    activeRailMode.value = 'stage'
    activeStageFilter.value = String(value).toUpperCase()
  }
})
watch(() => route.query.teamId, async (value) => {
  if (!value) return
  const teamId = Number(value)
  if (!Number.isFinite(teamId) || Number(selectedTeamId.value) === teamId) return
  if (teams.value.some((item) => Number(item.id) === teamId)) {
    selectedTeamId.value = teamId
    await fetchDashboard()
  }
})
watch([() => route.params.workItemId, () => route.query.taskId, () => route.query.submissionId], async () => {
  detailSubmissionEditorOpen.value = false
  detailHistoryExpanded.value = false
  detailTaskBookExpanded.value = false
  detailTaskBookPayload.value = {}
  applyTaskDeepLink()
})
watch(filePreviewVisible, (visible) => {
  if (!visible) cleanupEvidenceBlob()
})

const schoolOptions = computed(() => uniqueOptions(candidateMembers.value.map((item) => item.schoolName)))
const collegeOptions = computed(() => uniqueOptions(
  candidateMembers.value
    .filter((item) => matchesFilter(item.schoolName, memberFilters.schoolName))
    .map((item) => item.collegeName)
))
const classOptions = computed(() => uniqueOptions(
  candidateMembers.value
    .filter((item) => matchesFilter(item.schoolName, memberFilters.schoolName))
    .filter((item) => matchesFilter(item.collegeName, memberFilters.collegeName))
    .map((item) => item.className)
))
const userGroupOptions = computed(() => uniqueOptions(candidateMembers.value.flatMap((item) => groupNamesOf(item))))
const roleOptions = computed(() => uniqueOptions(candidateMembers.value.map((item) => item.role)))
const filteredCandidateMembers = computed(() => {
  const keyword = memberFilters.keyword.trim().toLowerCase()
  return candidateMembers.value.filter((user) => {
    if (memberFilters.userGroup !== 'ALL' && !groupNamesOf(user).includes(memberFilters.userGroup)) return false
    if (!matchesFilter(user.schoolName, memberFilters.schoolName)) return false
    if (!matchesFilter(user.collegeName, memberFilters.collegeName)) return false
    if (!matchesFilter(user.className, memberFilters.className)) return false
    if (memberFilters.role !== 'ALL' && user.role !== memberFilters.role) return false
    if (!keyword) return true
    return [user.username, user.email, user.schoolName, user.collegeName, user.className, user.userGroup]
      .filter(Boolean)
      .some((value) => String(value).toLowerCase().includes(keyword))
  })
})
const selectedCandidateMembers = computed(() => {
  const ids = new Set(projectForm.memberUserIds.map(Number))
  return candidateMembers.value.filter((user) => ids.has(Number(user.id)))
})
const captainOptions = computed(() => {
  const students = filteredCandidateMembers.value.filter((user) => user.role === 'STUDENT')
  const source = students.length ? students : candidateMembers.value.filter((user) => user.role === 'STUDENT')
  const selectedCaptain = candidateMembers.value.find((user) => Number(user.id) === Number(projectForm.captainUserId))
  if (selectedCaptain && !source.some((user) => Number(user.id) === Number(selectedCaptain.id))) {
    return [selectedCaptain, ...source]
  }
  return source
})

const visibleTasks = computed(() => {
  if (taskFilter.value === 'ALL') return tasks.value
  return tasks.value.filter((item) => item.status === taskFilter.value)
})
const deliveryItems = computed(() => [
  ...submissions.value.map((item) => normalizeDeliveryItem({
    deliveryId: `submission-${item.id}`,
    source: 'SUBMISSION',
    typeLabel: '任务提交',
    title: item.taskTitle || '任务提交',
    description: item.content || '',
    status: item.status || 'PENDING_REVIEW',
    actorLabel: '提交人',
    actorName: item.submitterName,
    timeLabel: '提交',
    updatedAt: item.createdAt,
    versionNo: item.versionNo,
    raw: item
  })),
  ...materials.value.map((item) => normalizeDeliveryItem({
    deliveryId: `material-${item.id}`,
    source: 'MATERIAL',
    typeLabel: materialTypeText(item.materialType),
    title: item.name || '项目材料',
    description: item.description || '',
    status: item.reviewStatus || 'DRAFT',
    actorLabel: '负责人',
    actorName: item.ownerName,
    timeLabel: '更新',
    updatedAt: item.updatedAt,
    raw: item
  }))
].sort((a, b) => new Date(b.updatedAt || 0).getTime() - new Date(a.updatedAt || 0).getTime()))
const visibleMaterialRows = computed(() => {
  const rows = deliveryItems.value.filter((item) => item.source === 'MATERIAL' || item.source === 'SUBMISSION')
  if (materialTypeFilter.value === 'ALL') return rows.slice(0, 6)
  return rows.filter((item) => materialFilterKey(item) === materialTypeFilter.value).slice(0, 6)
})
const visibleDeliveries = computed(() => {
  if (deliveryFilter.value === 'ALL') return deliveryItems.value
  return deliveryItems.value.filter((item) => item.status === deliveryFilter.value)
})
const currentStageTitle = computed(() => stages.value.find((item) => item.stageKey === team.value.currentStage)?.title || '未设置')
const completedStageCount = computed(() => stages.value.filter((item) => String(item.status || '').toUpperCase() === 'DONE').length)
const onlineMemberCount = computed(() => members.value.filter((member) => member.online || member.onlineStatus === 'ONLINE' || member.isOnline).length || Math.min(3, members.value.length))
const collaborationStatus = computed(() => {
  if (deliveryCountByFilter('PENDING_REVIEW') > 0) return '待审核'
  if (taskCountByFilter('IN_PROGRESS') > 0) return '协作中'
  if (Number(metrics.value.overallProgress || 0) >= 90) return '冲刺中'
  return '准备中'
})
const stageRemainingText = computed(() => {
  const current = stages.value.find((item) => item.stageKey === team.value.currentStage) || stages.value.find((item) => String(item.status || '').toUpperCase() === 'IN_PROGRESS')
  if (!current?.dueDate) return '阶段截止时间未设置'
  const end = new Date(current.dueDate)
  const diff = Math.ceil((end.getTime() - Date.now()) / (24 * 60 * 60 * 1000))
  if (!Number.isFinite(diff)) return '阶段截止时间未设置'
  if (diff < 0) return `已过期 ${Math.abs(diff)} 天`
  if (diff === 0) return '今天截止'
  return `距离阶段截止还有 ${diff} 天`
})
const storagePercent = computed(() => Math.min(100, Math.max(8, Number(metrics.value.storagePercent || metrics.value.storageUsagePercent || 36))))
const storageUsageText = computed(() => metrics.value.storageText || `${formatFileSize(metrics.value.storageUsed || 36.2 * 1024 * 1024 * 1024)} / ${formatFileSize(metrics.value.storageTotal || 100 * 1024 * 1024 * 1024)}`)
const todayFileCount = computed(() => {
  const today = new Date().toISOString().slice(0, 10)
  return deliveryItems.value.filter((item) => String(item.updatedAt || '').slice(0, 10) === today).length || Math.min(8, deliveryItems.value.length)
})
const todayTaskDoneCount = computed(() => tasks.value.filter((item) => String(item.status || '').toUpperCase() === 'DONE').length)
const stageTaskGroups = computed(() => {
  const fallbackStages = stages.value.length ? stages.value : [
    { stageKey: 'TOPIC', title: '选题与调研', status: 'DONE' },
    { stageKey: 'PLAN', title: '方案设计', status: 'IN_PROGRESS' },
    { stageKey: 'MATERIAL', title: '材料制作', status: 'PENDING' },
    { stageKey: 'REHEARSAL', title: '模拟演练', status: 'PENDING' },
    { stageKey: 'FINAL', title: '最终打磨', status: 'PENDING' }
  ]
  return fallbackStages.map((stage) => {
    const stageTasks = tasks.value.filter((task) => String(task.stageKey || '').toUpperCase() === String(stage.stageKey || '').toUpperCase())
    const done = stageTasks.filter((task) => String(task.status || '').toUpperCase() === 'DONE').length
    return {
      ...stage,
      raw: stage,
      tasks: stageTasks.length ? stageTasks : syntheticStageTasks(stage),
      total: stageTasks.length || syntheticStageTasks(stage).length,
      done
    }
  }).slice(0, 5)
})
const prepSteps = computed(() => {
  const current = String(team.value.currentStage || '').toUpperCase()
  const progress = Number(metrics.value.overallProgress || 0)
  const steps = [
    { key: 'TOPIC', name: '选题策划' },
    { key: 'MATERIAL', name: '材料整理' },
    { key: 'PPT', name: 'PPT生成' },
    { key: 'SCRIPT', name: '讲稿制作' },
    { key: 'ROADSHOW', name: '路演联调' }
  ]
  return steps.map((step, index) => {
    const threshold = (index + 1) * 18
    const done = progress >= threshold || current === step.key
    const active = current === step.key || (!current && progress < threshold && progress >= index * 18)
    return {
      ...step,
      done: done && !active,
      active,
      status: active ? '进行中' : done ? '已完成' : '未开始'
    }
  })
})
const missingMaterials = computed(() => {
  const reviewRows = deliveryItems.value
    .filter((item) => ['PENDING_REVIEW', 'CHANGES_REQUESTED', 'REJECTED', 'DRAFT'].includes(String(item.status || '').toUpperCase()))
    .slice(0, 4)
    .map((item) => ({
      title: item.title,
      note: item.status === 'DRAFT' ? '尚未提交' : materialStatusText(item.status)
    }))
  if (reviewRows.length) return reviewRows
  return [
    { title: '市场调研数据报告', note: '缺少最新年份数据' },
    { title: '财务测算表', note: '部分数据待确认' },
    { title: '导师推荐信', note: '尚未上传' },
    { title: '专利或软著证明', note: '尚未上传' }
  ]
})
const overdueTasks = computed(() => tasks.value
  .filter((task) => {
    if (String(task.status || '').toUpperCase() === 'DONE') return false
    if (!task.dueAt) return false
    return new Date(task.dueAt).getTime() < Date.now()
  })
  .slice(0, 3))
const overviewActionItems = computed(() => {
  const reviewItems = deliveryItems.value
    .filter((item) => ['PENDING_REVIEW', 'CHANGES_REQUESTED', 'REJECTED', 'DRAFT'].includes(String(item.status || '').toUpperCase()))
    .slice(0, 3)
    .map((item) => ({
      type: 'material',
      badge: '材',
      title: item.title,
      note: `${item.typeLabel} · ${materialStatusText(item.status)}`,
      payload: item
    }))
  const taskItems = overdueTasks.value.map((task) => ({
    type: 'task',
    badge: '任',
    title: task.title,
    note: `${task.ownerName || '未分配'} · ${formatDate(task.dueAt)} 截止`,
    payload: task
  }))
  const roadshowItems = activeRoadshowProblems.value.slice(0, 2).map((item) => ({
    type: 'roadshow',
    badge: '复',
    title: item.title,
    note: item.description || '路演复盘待改进问题',
    payload: item
  }))
  return [...reviewItems, ...taskItems, ...roadshowItems].slice(0, 5)
})
const currentSideItems = computed(() => {
  if (activeTeamSection.value === 'materials' || activeTeamSection.value === 'versions') {
    return overviewActionItems.value.filter((item) => item.type === 'material').slice(0, 4)
  }
  if (activeTeamSection.value === 'tasks') {
    return [
      ...overdueTasks.value.map((task) => ({
        type: 'task',
        badge: '任',
        title: task.title,
        note: `${task.ownerName || '未分配'} · ${formatDate(task.dueAt)} 截止`,
        payload: task
      })),
      ...tasks.value.filter((task) => String(task.status || '').toUpperCase() === 'REVIEWING').slice(0, 3).map((task) => ({
        type: 'task',
        badge: '审',
        title: task.title,
        note: `${task.ownerName || '未分配'} · 待审核`,
        payload: task
      }))
    ].slice(0, 4)
  }
  if (activeTeamSection.value === 'members') {
    return members.value
      .filter((member) => !member.positionName || !member.responsibility)
      .slice(0, 4)
      .map((member) => ({
        type: 'member',
        badge: '员',
        title: member.username,
        note: member.positionName ? '职责说明待补充' : '岗位待设置',
        payload: member
      }))
  }
  if (activeTeamSection.value === 'review') {
    const items = activeRoadshowProblems.value.slice(0, 4).map((item) => ({
      type: 'roadshow',
      badge: '复',
      title: item.title,
      note: item.description || '路演复盘待改进问题',
      payload: item
    }))
    if (!items.length) {
      items.push({ type: 'roadshow', badge: '评', title: '上传视频评分', note: '生成路演评分报告和训练建议' })
    }
    return items
  }
  return overviewActionItems.value.slice(0, 4)
})
const workStageFilters = computed(() => {
  const fromStages = stages.value.map((stage) => ({
    key: String(stage.stageKey || '').toUpperCase(),
    label: stage.title || stage.stageKey || '未命名阶段'
  })).filter((item) => item.key)
  return [{ key: 'ALL', label: '全部阶段' }, ...(fromStages.length ? fromStages : fallbackStageFilters)]
})
const workTypeFilterItems = computed(() => {
  const typeMap = new Map([['ALL', '全部类型']])
  workItems.value.forEach((item) => {
    if (!item?.type) return
    typeMap.set(item.type, item.typeLabel || item.type)
  })
  return Array.from(typeMap.entries()).map(([key, label]) => ({ key, label }))
})
const workTypeFilterLabel = computed(() => workTypeFilterItems.value.find((item) => item.key === workTypeFilter.value)?.label || '全部类型')
const workSortLabel = computed(() => ({ smart: '智能', due: '截止', priority: '优先级', updated: '最新' }[workSortMode.value] || '智能'))
const workDensityLabel = computed(() => ({ comfortable: '舒适', compact: '紧凑' }[workDensity.value] || '舒适'))
const trainingSchedule = computed(() => Array.isArray(dashboard.value?.trainingSchedule) ? dashboard.value.trainingSchedule : [])
const workItems = computed(() => {
  const scheduleByTaskId = new Map()
  trainingSchedule.value.forEach((day) => {
    ;(day.taskIds || []).forEach((taskId) => {
      scheduleByTaskId.set(Number(taskId), day)
    })
  })
  const taskItems = tasks.value.map((task) => {
    const item = createTaskWorkItem(task)
    const day = scheduleByTaskId.get(Number(task.id))
    if (day) attachTrainingAvailability(item, day)
    return item
  })
  const existingTaskIds = new Set(tasks.value.map((task) => Number(task.id)).filter(Number.isFinite))
  const lockedScheduleItems = trainingSchedule.value
    .filter((day) => Boolean(day.locked))
    .filter((day) => {
      const taskIds = (day.taskIds || []).map(Number).filter(Number.isFinite)
      return !taskIds.length || taskIds.every((id) => !existingTaskIds.has(id))
    })
    .map((day) => createLockedTrainingWorkItem(day))
  const deliveryWorkItems = deliveryItems.value
    .filter((item) => ['PENDING_REVIEW', 'REVIEWING', 'CHANGES_REQUESTED', 'REJECTED', 'DRAFT'].includes(normalStatus(item.status)))
    .map((item) => createDeliveryWorkItem(item))
  const scoreItems = activeRoadshowProblems.value.map((item, index) => createRoadshowWorkItem(item, index, 'score'))
  const reviewItems = activeRoadshowActions.value.map((item, index) => createRoadshowWorkItem(item, index, 'review'))
  const systemItems = createSystemWorkItems()
  return [...taskItems, ...lockedScheduleItems, ...deliveryWorkItems, ...scoreItems, ...reviewItems, ...systemItems]
    .filter(Boolean)
    .sort(compareWorkItems)
})
const filteredWorkItems = computed(() => {
  const filtered = workItems.value.filter((item) => {
    if (activeRailMode.value === 'stage' && activeStageFilter.value !== 'ALL' && normalStageKey(item.stageKey) !== normalStageKey(activeStageFilter.value)) return false
    if (workTypeFilter.value !== 'ALL' && item.type !== workTypeFilter.value) return false
    if (activeRailMode.value !== 'work') return item.status !== 'DONE'
    if (activeWorkView.value === 'mine') return Number(item.ownerUserId) === Number(currentUserId.value) || item.assignees?.some((member) => Number(member.userId) === Number(currentUserId.value))
    if (activeWorkView.value === 'review') return ['PENDING_REVIEW', 'REVIEWING', 'CHANGES_REQUESTED'].includes(item.status)
    if (activeWorkView.value === 'score') return item.type === 'score'
    if (activeWorkView.value === 'blocked') return item.isOverdue || item.status === 'BLOCKED'
    return item.status !== 'DONE'
  })
  return sortWorkItems(filtered, workSortMode.value)
})
const selectedWorkItem = computed(() => {
  const list = filteredWorkItems.value
  return list.find((item) => item.id === selectedWorkItemId.value) || list[0] || null
})
const activeTaskDetailWorkItem = computed(() => taskActionWorkItem(activeTaskDetailItemId.value))
const activeTaskSubmissionWorkItem = computed(() => taskActionWorkItem(activeTaskSubmissionItemId.value))
const activeTaskDetailTask = computed(() => activeTaskDetailWorkItem.value?.raw || null)
const activeTaskSubmissionTask = computed(() => activeTaskSubmissionWorkItem.value?.raw || null)
const activeWorkViewLabel = computed(() => workViewItems.find((item) => item.key === activeWorkView.value)?.label || '收件箱')
const activeStageFilterLabel = computed(() => workStageFilters.value.find((item) => normalStageKey(item.key) === normalStageKey(activeStageFilter.value))?.label || '全部阶段')
const currentWorkScopeTitle = computed(() => activeRailMode.value === 'stage' ? activeStageFilterLabel.value : activeWorkViewLabel.value)
const workViewCounts = computed(() => {
  const openItems = workItems.value.filter((item) => item.status !== 'DONE')
  return {
    inbox: openItems.length,
    mine: openItems.filter((item) => Number(item.ownerUserId) === Number(currentUserId.value)).length,
    review: openItems.filter((item) => ['PENDING_REVIEW', 'REVIEWING', 'CHANGES_REQUESTED'].includes(item.status)).length,
    score: openItems.filter((item) => item.type === 'score').length,
    blocked: openItems.filter((item) => item.isOverdue || item.status === 'BLOCKED').length
  }
})
const simpleTaskItems = computed(() => workItems.value
  .filter((item) => ['task', 'score', 'material', 'review', 'system'].includes(item.type))
  .sort(compareWorkItems))
const mySimpleTaskItems = computed(() => simpleTaskItems.value.filter(isMyWorkItem))
const simpleFilteredWorkItems = computed(() => {
  const list = simpleTaskItems.value
  if (simpleTaskFilter.value === 'MINE') return list.filter(isMyWorkItem)
  if (simpleTaskFilter.value === 'EXPIRED') return list.filter((item) => item.isOverdue)
  if (simpleTaskFilter.value === 'DONE') return list.filter((item) => ['DONE', 'APPROVED'].includes(item.status))
  if (simpleTaskFilter.value === 'TODO') return list.filter((item) => item.status === 'TODO')
  if (simpleTaskFilter.value === 'IN_PROGRESS') return list.filter((item) => ['IN_PROGRESS', 'PENDING_REVIEW', 'REVIEWING', 'CHANGES_REQUESTED'].includes(item.status))
  return list
})
const focusedTaskSourceFilters = computed(() => {
  const all = simpleTaskItems.value
  const countBySource = (key) => all.filter((item) => taskSourceKey(item) === key).length
  return [
    { key: 'ALL', label: '全部', count: all.length },
    { key: 'MINE', label: '与我相关', count: all.filter(isMyWorkItem).length },
    { key: 'TRAINING', label: '训练营', count: countBySource('TRAINING') },
    { key: 'TEAM', label: '团队自建', count: countBySource('TEAM') },
    { key: 'SCORE', label: '评分改进', count: countBySource('SCORE') }
  ]
})
const focusedFilteredTaskItems = computed(() => {
  const keyword = focusedTaskKeyword.value.trim().toLowerCase()
  return simpleTaskItems.value.filter((item) => {
    const source = taskSourceKey(item)
    if (focusedTaskSourceFilter.value === 'MINE' && !isMyWorkItem(item)) return false
    if (!['ALL', 'MINE'].includes(focusedTaskSourceFilter.value) && source !== focusedTaskSourceFilter.value) return false
    if (!keyword) return true
    return [item.title, item.summary, item.ownerName, item.sourceLabel, item.taskTypeLabel]
      .some((value) => String(value || '').toLowerCase().includes(keyword))
  })
})
const detailWorkItem = computed(() => {
  const workItemId = String(route.params.workItemId || '')
  if (workItemId) return simpleTaskItems.value.find((item) => item.id === workItemId) || null
  const taskId = Number(route.query.taskId)
  if (!Number.isFinite(taskId)) return null
  return simpleTaskItems.value.find((item) => Number(item.raw?.id || item.raw?.taskId) === taskId) || null
})
const detailDeliverySubmission = computed(() => {
  const item = detailWorkItem.value
  if (item?.raw?.source !== 'SUBMISSION') return null
  return item.raw.raw || null
})
const detailTask = computed(() => {
  if (detailWorkItem.value?.type === 'task') return detailWorkItem.value.raw || null
  const taskId = Number(detailDeliverySubmission.value?.taskId)
  if (!Number.isFinite(taskId)) return null
  return tasks.value.find((task) => Number(task.id) === taskId) || null
})
const detailTaskBook = computed(() => detailTaskBookPayload.value?.taskBook || {})
const detailTaskBookRequirements = computed(() => detailTaskBook.value.requirements || [])
const detailTaskBookAttachments = computed(() => detailTaskBook.value.attachments || [])
const detailTaskBookHtml = computed(() => DOMPurify.sanitize(detailTaskBook.value.contentHtml || '', {
  ALLOWED_TAGS: ['p', 'h1', 'h2', 'h3', 'strong', 'b', 'ul', 'ol', 'li', 'blockquote', 'a', 'img', 'br', 'span'],
  ALLOWED_ATTR: ['href', 'title', 'target', 'rel', 'src', 'alt', 'data-text-color']
}))
const detailTaskSubmissions = computed(() => taskSubmissions(detailTask.value))
const detailLatestSubmission = computed(() => detailTaskSubmissions.value[0] || null)
const detailHistoricalSubmissions = computed(() => detailTaskSubmissions.value.slice(1))
const nextDetailVersionNo = computed(() => Number(detailLatestSubmission.value?.versionNo || 0) + 1)
const focusedTaskGroups = computed(() => {
  const urgent = []
  const today = []
  const next = []
  const completed = []
  focusedFilteredTaskItems.value.forEach((item) => {
    const status = normalStatus(item.status)
    if (isCompletedWorkItem(item)) {
      completed.push(item)
      return
    }
    if (isLockedWorkItem(item)) {
      next.push(item)
      return
    }
    if (isActionablyOverdue(item) || item.priority === 'HIGH' || ['BLOCKED', 'CHANGES_REQUESTED', 'REJECTED'].includes(status)) {
      urgent.push(item)
      return
    }
    if (isLocalToday(item.dueAt) || isLocalToday(item.trainingDate)) {
      today.push(item)
      return
    }
    next.push(item)
  })
  return [
    { key: 'URGENT', label: '需立即处理', hint: '超期、高优先级或需修改', tone: 'danger', items: urgent.sort(compareWorkItems) },
    { key: 'TODAY', label: '今天', hint: '今天需要推进的任务', tone: 'today', items: today.sort(compareWorkItems) },
    { key: 'NEXT', label: '接下来', hint: '未开放训练日与后续任务', tone: 'next', items: next.sort(compareWorkItems) },
    { key: 'COMPLETED', label: '已完成', hint: '近期完成的任务记录', tone: 'done', items: completed.sort(compareWorkItems) }
  ].filter((group) => group.items.length)
})
const focusedSelectedWorkItem = computed(() => focusedFilteredTaskItems.value
  .find((item) => item.id === selectedWorkItemId.value) || focusedTaskGroups.value[0]?.items[0] || null)
const focusedTaskMetrics = computed(() => {
  const open = simpleTaskItems.value.filter((item) => !isCompletedWorkItem(item))
  const urgent = open.filter((item) => isActionablyOverdue(item) || item.priority === 'HIGH' || ['BLOCKED', 'CHANGES_REQUESTED', 'REJECTED'].includes(normalStatus(item.status)))
  const mine = open.filter(isMyWorkItem)
  const review = open.filter((item) => ['PENDING_REVIEW', 'REVIEWING'].includes(normalStatus(item.status)))
  return [
    { key: 'open', label: '待处理', value: open.length },
    { key: 'urgent', label: '需优先', value: urgent.length },
    { key: 'mine', label: '与我相关', value: mine.length },
    { key: 'review', label: '待审核', value: review.length }
  ]
})
const focusedTaskGuide = computed(() => {
  const urgent = focusedTaskMetrics.value.find((item) => item.key === 'urgent')?.value || 0
  if (urgent > 0) return `建议先处理 ${urgent} 项紧急任务，再继续推进今天的工作。`
  const mine = focusedTaskMetrics.value.find((item) => item.key === 'mine')?.value || 0
  return mine > 0 ? `当前有 ${mine} 项与你相关的任务，按截止时间依次推进即可。` : '当前没有需要立即处理的任务。'
})
const todayTaskGroups = computed(() => {
  const groups = [
    { key: 'MORNING', label: '上午', range: [0, 12], items: [] },
    { key: 'AFTERNOON', label: '下午', range: [12, 18], items: [] },
    { key: 'EVENING', label: '晚上', range: [18, 24], items: [] }
  ]
  const today = new Date().toISOString().slice(0, 10)
  mySimpleTaskItems.value
    .filter((item) => String(item.dueAt || '').slice(0, 10) === today)
    .forEach((item) => {
      const slot = resolveTaskTimeSlot(item)
      const hour = new Date(item.dueAt).getHours()
      const group = groups.find((entry) => entry.key === slot) || groups.find((entry) => hour >= entry.range[0] && hour < entry.range[1]) || groups[2]
      group.items.push(item)
    })
  return groups.map((group) => ({ ...group, items: group.items.sort(compareWorkItems) }))
})
const taskSummaryCards = computed(() => {
  const all = simpleTaskItems.value
  const open = all.filter((item) => !['DONE', 'APPROVED'].includes(item.status))
  const done = all.filter((item) => ['DONE', 'APPROVED'].includes(item.status))
  const expired = open.filter((item) => item.isOverdue)
  const mine = mySimpleTaskItems.value.filter((item) => !['DONE', 'APPROVED'].includes(item.status))
  const todayOpenCount = todayTaskGroups.value.reduce((sum, group) => sum + group.items.filter((item) => !isCompletedWorkItem(item)).length, 0)
  return [
    { key: 'today', label: '今日待办', value: todayOpenCount, hint: '按上午、下午、晚上拆分' },
    { key: 'mine', label: '我的任务', value: mine.length, hint: '当前登录人负责或参与' },
    { key: 'done', label: '已完成', value: done.length, hint: `全部 ${all.length} 项任务` },
    { key: 'expired', label: '已过期', value: expired.length, hint: '需要优先处理' }
  ]
})
const taskHeroSubtitle = computed(() => {
  const project = team.value?.name || '当前项目'
  const todayOpen = todayTaskGroups.value.reduce((sum, group) => sum + group.items.filter((item) => !isCompletedWorkItem(item)).length, 0)
  const pendingReview = deliveryCountByFilter('PENDING_REVIEW')
  const overdue = simpleTaskItems.value.filter((item) => item.isOverdue && !isCompletedWorkItem(item)).length
  const stage = currentStageTitle.value && currentStageTitle.value !== '未设置' ? `${currentStageTitle.value}阶段` : '项目推进中'
  const parts = [`${project} · ${stage}`]
  if (todayOpen > 0) parts.push(`今日 ${todayOpen} 项待办`)
  if (pendingReview > 0) parts.push(`${pendingReview} 项待审核`)
  if (overdue > 0) parts.push(`${overdue} 项已过期需处理`)
  if (parts.length === 1) parts.push('暂无紧急任务，保持资料与进度同步')
  return parts.join('，')
})
const recentVersions = computed(() => deliveryItems.value
  .filter((item) => attachmentUrl(item))
  .slice(0, 4))
const activityItems = computed(() => {
  const materialActivities = deliveryItems.value.slice(0, 4).map((item) => ({
    id: `material-${item.deliveryId}`,
    type: 'MATERIAL',
    actor: item.actorName || '团队成员',
    action: `${item.timeLabel || '更新'}了 ${item.title}`,
    time: formatDate(item.updatedAt)
  }))
  const taskActivities = tasks.value.slice(0, 4).map((task) => ({
    id: `task-${task.id}`,
    type: 'TASK',
    actor: task.ownerName || '团队成员',
    action: `${taskStatusText(task.status)}：${task.title}`,
    time: formatDate(task.updatedAt || task.dueAt)
  }))
  const roadshowActivities = activeRoadshow.value?.meetingTitle ? [{
    id: 'roadshow-current',
    type: 'ROADSHOW',
    actor: '系统',
    action: `同步了路演复盘：${activeRoadshow.value.meetingTitle}`,
    time: formatDate(activeRoadshow.value.updatedAt || activeRoadshow.value.startedAt)
  }] : []
  return [...materialActivities, ...taskActivities, ...roadshowActivities].slice(0, 6)
})
const visibleActivities = computed(() => {
  if (activityFilter.value === 'ALL') return activityItems.value
  return activityItems.value.filter((item) => item.type === activityFilter.value)
})
const deliverySummary = computed(() => [
  { key: 'total', label: '交付总数', value: deliveryItems.value.length },
  { key: 'pending', label: '待审核', value: deliveryCountByFilter('PENDING_REVIEW') },
  { key: 'changes', label: '需修改', value: deliveryCountByFilter('CHANGES_REQUESTED') + deliveryCountByFilter('REJECTED') },
  { key: 'ready', label: '已通过', value: deliveryCountByFilter('APPROVED') }
])
const inspectedDelivery = computed(() => deliveryItems.value.find((item) => item.deliveryId === inspectedDeliveryId.value) || null)
const activeReviewDelivery = computed(() => deliveryItems.value.find((item) => item.deliveryId === activeReviewDeliveryId.value) || null)

const roleClass = computed(() => {
  if (canTeachObserve.value) return 'teacher'
  if (myRoleInTeam.value === 'CAPTAIN') return 'captain'
  return 'student'
})

const roleLabel = computed(() => {
  if (canTeachObserve.value) return '指导模式'
  if (myRoleInTeam.value === 'CAPTAIN') return '队长模式'
  return '成员模式'
})

const roleMainText = computed(() => {
  if (canTeachObserve.value) return '你可以观察团队整体进度、风险和能力证据。'
  if (myRoleInTeam.value === 'CAPTAIN') return '你可以分配任务、设置周期并审核队员提交。'
  return '你可以查看自己的任务、提交成果并追踪能力成长。'
})

const roleSubText = computed(() => {
  if (canTeachObserve.value) return '教师专属数据由后端权限控制，学生与队长不会收到这些字段。'
  if (myRoleInTeam.value === 'CAPTAIN') return '请优先处理待审核提交和过期任务。'
  return '请关注待提交、被退回和即将到期的任务。'
})

const healthText = computed(() => {
  const progress = Number(metrics.value.overallProgress || 0)
  if (progress >= 85) return '状态优秀，可准备正式路演'
  if (progress >= 70) return '状态稳定，建议补齐复盘证据'
  return '需要集中推进任务、材料和测评'
})

const activeAbility = computed(() => {
  return abilities.value.find((item) => item.userId === activeAbilityUserId.value) || abilities.value[0] || {}
})

const activeAbilityValues = computed(() => dimensions.map((item) => Number(activeAbility.value[item.key] || 0)))
const activeAbilityList = computed(() => dimensions.map((item, index) => {
  const sampled = activeAbility.value.dimensionSampled?.[item.key] === true
  return { ...item, value: activeAbilityValues.value[index] || 0, sampled }
}))
const sampledDimensionCount = computed(() => activeAbilityList.value.filter((item) => item.sampled).length)
const activeEvidence = computed(() => activeAbility.value.evidence || [])
const activeRoadshow = computed(() => {
  const selected = roadshowMeetings.value.find((item) => String(item.meetingId) === String(selectedRoadshowMeetingId.value))
  return selected || roadshow.value || {}
})
const activeRoadshowDimensions = computed(() => activeRoadshow.value?.dimensions || [])
const activeRoadshowHighlights = computed(() => normalizeInsightList(activeRoadshow.value?.highlights || []))
const activeRoadshowProblems = computed(() => {
  const fromMeeting = normalizeInsightList(activeRoadshow.value?.criticalIssues || [])
  const fromTeam = reviewIssues.value
    .filter((item) => item.sourceType === 'AI_SCORE')
    .map((item) => ({
      title: item.title,
      description: item.description,
      severity: item.severity || 'MEDIUM',
      category: item.category
    }))
  return fromMeeting.length ? fromMeeting : fromTeam
})
const activeRoadshowActions = computed(() => normalizeInsightList(activeRoadshow.value?.improvementPriorities || []))
const memoryRounds = computed(() => Array.isArray(roadshowMemory.value?.rounds) ? roadshowMemory.value.rounds : [])
const memoryPriorIssueReview = computed(() => normalizeMemoryList(roadshowMemory.value?.priorIssueReview || []))
const memoryNewIssues = computed(() => normalizeMemoryList(roadshowMemory.value?.newIssues || []))
const memoryTrainingPlan = computed(() => normalizeMemoryList(roadshowMemory.value?.trainingPlan || []))
const memoryTimeline = computed(() => Array.isArray(roadshowMemory.value?.timeline) ? roadshowMemory.value.timeline : [])
const memoryFullScoreGap = computed(() => roadshowMemory.value?.fullScoreGap || {})
const memoryFullScoreReasons = computed(() => {
  const reasons = memoryFullScoreGap.value?.reasons
  return Array.isArray(reasons) ? reasons.filter(Boolean).map(String) : []
})
const roadshowMemoryStatusText = computed(() => {
  return roadshowMemory.value?.memoryStatusText || '按同一团队多轮路演对比改进证据'
})

function goVideoScoreUpload() {
  router.push({
    path: '/ai-score-upload',
    query: selectedTeamId.value ? { teamId: selectedTeamId.value } : {}
  })
}

function handleActionItem(item) {
  if (!item) return
  if (item.type === 'material' && item.payload) return inspectDelivery(item.payload)
  if (item.type === 'task') {
    activeTeamSection.value = 'tasks'
    return
  }
  if (item.type === 'member') {
    activeTeamSection.value = 'members'
    if (item.payload?.userId) activeAbilityUserId.value = item.payload.userId
    return
  }
  if (item.type === 'roadshow') {
    activeTeamSection.value = 'review'
    if (item.title === '上传视频评分') goVideoScoreUpload()
  }
}

function selectWorkView(key) {
  if (!validWorkViews.includes(key)) return
  activeTeamSection.value = 'overview'
  activeRailMode.value = 'work'
  activeStageFilter.value = 'ALL'
  activeWorkView.value = key
  router.replace({
    path: '/project-team',
    query: {
      ...route.query,
      workView: key,
      stageFilter: undefined,
      teamId: selectedTeamId.value || route.query.teamId || undefined
    }
  })
}

function selectStageFilter(key) {
  activeTeamSection.value = 'overview'
  activeRailMode.value = 'stage'
  activeStageFilter.value = key
  router.replace({
    path: '/project-team',
    query: {
      ...route.query,
      workView: undefined,
      stageFilter: key,
      teamId: selectedTeamId.value || route.query.teamId || undefined
    }
  })
}

function toggleRailGroup(key) {
  collapsedRailGroups[key] = !collapsedRailGroups[key]
}

function taskActionWorkItem(itemId) {
  if (!itemId) return null
  return workItems.value.find((item) => item.id === itemId) || simpleTaskItems.value.find((item) => item.id === itemId) || null
}

function applyTaskDeepLink() {
  if (!dashboard.value) return
  const workItemId = String(route.params.workItemId || '')
  const taskId = Number(route.query.taskId)
  const legacySubmissionId = Number(workItemId.match(/^delivery-submission-(\d+)$/)?.[1])
  if (Number.isFinite(legacySubmissionId)) {
    const linkedSubmission = submissions.value.find((submission) => Number(submission.id || submission.submissionId) === legacySubmissionId)
    if (linkedSubmission?.taskId) {
      router.replace({
        path: `/project-team/details/task-${linkedSubmission.taskId}`,
        query: {
          teamId: selectedTeamId.value || route.query.teamId || undefined,
          submissionId: linkedSubmission.id || linkedSubmission.submissionId || legacySubmissionId
        }
      })
      return
    }
  }
  const item = workItemId
    ? simpleTaskItems.value.find((entry) => entry.id === workItemId)
    : Number.isFinite(taskId)
      ? simpleTaskItems.value.find((entry) => Number(entry.raw?.id || entry.raw?.taskId) === taskId)
      : null
  if (!item) return
  const linkedSubmission = item.raw?.source === 'SUBMISSION' ? item.raw.raw : null
  if (workItemId && linkedSubmission?.taskId) {
    router.replace({
      path: `/project-team/details/task-${linkedSubmission.taskId}`,
      query: {
        teamId: selectedTeamId.value || route.query.teamId || undefined,
        submissionId: linkedSubmission.id || linkedSubmission.submissionId || route.query.submissionId || undefined
      }
    })
    return
  }
  focusedTaskSourceFilter.value = 'ALL'
  focusedTaskKeyword.value = ''
  selectedWorkItemId.value = item.id
  activeTaskDetailItemId.value = ''
  if (!isTaskDetailRoute.value && Number.isFinite(taskId)) {
    router.replace({
      path: `/project-team/details/${item.id}`,
      query: {
        teamId: selectedTeamId.value || route.query.teamId || undefined,
        submissionId: route.query.submissionId || undefined
      }
    })
  }
}

function isFocusedSubmission(item) {
  const submissionId = Number(route.query.submissionId)
  return Number.isFinite(submissionId) && Number(item?.id || item?.submissionId) === submissionId
}

function openFocusedTaskDetail(item) {
  if (!item?.id) return
  if (isLockedWorkItem(item)) {
    ElMessage.warning(lockedUnlockMessage(item))
    return
  }
  const linkedSubmission = item.raw?.source === 'SUBMISSION' ? item.raw.raw : null
  router.push({
    path: linkedSubmission?.taskId
      ? `/project-team/details/task-${linkedSubmission.taskId}`
      : `/project-team/details/${item.id}`,
    query: {
      teamId: selectedTeamId.value || undefined,
      submissionId: linkedSubmission?.id || linkedSubmission?.submissionId || undefined
    }
  })
}

function goBackToTaskList() {
  router.push({
    path: '/project-team',
    query: selectedTeamId.value ? { teamId: selectedTeamId.value } : {}
  })
}

function detailPageActions(item) {
  return (item?.actions || []).filter((action) => !['open-task', 'submit-task'].includes(action.key))
}

function taskSubmissions(task) {
  if (!task?.id) return []
  return submissions.value
    .filter((item) => Number(item.taskId) === Number(task.id))
    .sort((a, b) => Number(b.versionNo || b.id || 0) - Number(a.versionNo || a.id || 0))
}

function createTaskWorkItem(task) {
  const status = normalStatus(task.latestSubmissionStatus || task.status || 'TODO')
  const dueAt = task.dueAt || task.updatedAt || ''
  const scoreTask = isScoreGeneratedTask(task)
  const prepTask = isPrepGeneratedTask(task)
  const trainingTask = isTrainingLinkedTask(task)
  const assignees = normalizeTaskAssignees(task)
  return {
    id: `task-${task.id}`,
    type: scoreTask ? 'score' : prepTask ? 'material' : 'task',
    typeLabel: scoreTask ? '评分' : prepTask ? '准备' : '任务',
    badge: scoreTask ? '评' : prepTask ? '准' : '任',
    icon: scoreTask ? 'score' : prepTask ? 'prepare' : 'task',
    title: task.title || '未命名任务',
    summary: task.description || deliveryText(task),
    taskType: resolveTaskTypeKey(task),
    taskTypeLabel: resolveTaskTypeLabel(task),
    timeSlot: resolveTaskTimeSlot(task),
    status,
    statusLabel: taskStatusText(status),
    priority: normalPriority(task.priority || (isOverdueDate(dueAt, status) ? 'HIGH' : 'MEDIUM')),
    ownerName: assignees.length ? assignees.map((item) => item.username).join('、') : '',
    ownerUserId: task.ownerUserId,
    assignees,
    stageKey: trainingTask ? 'TRAINING' : task.stageKey || (scoreTask ? 'REVIEW' : prepTask ? 'MATERIAL' : team.value.currentStage) || 'MATERIAL',
    stageLabel: trainingTask ? '训练营' : stageTitle(task.stageKey || (scoreTask ? 'REVIEW' : prepTask ? 'MATERIAL' : '')),
    dueAt,
    sourceKey: trainingTask ? 'TRAINING' : scoreTask ? 'SCORE' : 'TEAM',
    isTrainingTask: trainingTask,
    locked: false,
    published: true,
    lockReason: null,
    scheduledUnlockAt: null,
    earlyUnlockedAt: null,
    sourceLabel: trainingTask ? '训练营任务' : scoreTask ? '评分改进' : prepTask ? '团队准备任务' : '团队自建任务',
    sourceMeta: trainingTask
      ? '来自训练营 · 实操能力训练'
      : scoreTask
        ? '由评分扣分项或训练建议生成'
        : prepTask
          ? '由材料、策划书或讲稿同步生成'
          : (task.latestSubmissionStatus ? `团队任务 · 交付状态：${taskStatusText(task.latestSubmissionStatus)}` : '由老师或团队成员创建'),
    isOverdue: isOverdueDate(dueAt, status),
    raw: task,
    actions: [
      {
        key: scoreTask ? 'open-review' : prepTask ? 'open-prep' : 'open-task',
        label: scoreTask ? '查看评分复盘' : prepTask ? '回到准备页' : trainingTask ? (Number(task.submissionCount || 0) ? '查看提交详情' : '查看任务要求') : '查看任务详情',
        kind: 'primary'
      },
      ...(canReviewTaskSubmission(task, status) ? [{ key: 'review-task-submission', label: '审核成果', kind: 'secondary' }] : []),
      ...(canSubmitTask(task) ? [{ key: 'submit-task', label: '提交成果', kind: 'secondary' }] : [])
    ],
    links: task.latestAttachmentUrl ? [{ label: task.latestAttachmentName || '任务附件', action: 'preview-task' }] : []
  }
}

function attachTrainingAvailability(item, day) {
  if (!item || !day) return item
  item.published = day.published !== false && String(day.status || '').toUpperCase() !== 'DRAFT'
  item.locked = Boolean(day.locked)
  item.lockReason = day.lockReason || null
  item.scheduledUnlockAt = day.scheduledUnlockAt || null
  item.earlyUnlockedAt = day.earlyUnlockedAt || null
  item.trainingDate = day.trainingDate || item.trainingDate
  item.dayNo = day.dayNo || item.dayNo
  if (item.locked) {
    item.status = 'LOCKED'
    item.statusLabel = item.published === false || item.lockReason === 'NOT_PUBLISHED' ? '待教师发布' : '未开放'
    item.isOverdue = false
    item.actions = []
    item.summary = lockedUnlockMessage(item)
  }
  return item
}

function createLockedTrainingWorkItem(day) {
  const published = day.published !== false && String(day.status || '').toUpperCase() !== 'DRAFT'
  const lockReason = day.lockReason || (published ? 'SCHEDULED' : 'NOT_PUBLISHED')
  const item = {
    id: `training-day-${day.dayId}`,
    type: 'task',
    typeLabel: '任务',
    badge: '锁',
    icon: 'task',
    title: day.title || (day.dayNo ? `第 ${day.dayNo} 天训练任务` : '训练任务'),
    summary: '',
    taskType: 'TRAINING_DAY',
    taskTypeLabel: '训练营',
    timeSlot: 'MORNING',
    status: 'LOCKED',
    statusLabel: published ? '未开放' : '待教师发布',
    priority: 'MEDIUM',
    ownerName: '训练营',
    ownerUserId: null,
    assignees: [],
    stageKey: 'TRAINING',
    stageLabel: '训练营',
    dueAt: day.dueAt || day.trainingDate || '',
    trainingDate: day.trainingDate || '',
    dayNo: day.dayNo,
    sourceKey: 'TRAINING',
    isTrainingTask: true,
    locked: true,
    published,
    lockReason,
    scheduledUnlockAt: day.scheduledUnlockAt || null,
    earlyUnlockedAt: day.earlyUnlockedAt || null,
    sourceLabel: '训练营任务',
    sourceMeta: published ? '训练日尚未开放' : '待教师发布',
    isOverdue: false,
    raw: day,
    actions: [],
    links: []
  }
  item.summary = lockedUnlockMessage(item)
  return item
}

function isLockedWorkItem(item) {
  return Boolean(item?.locked) || normalStatus(item?.status) === 'LOCKED'
}

function lockedUnlockLabel(item) {
  if (!item?.published || item?.lockReason === 'NOT_PUBLISHED') return '待发布'
  const value = item.scheduledUnlockAt || item.trainingDate
  if (!value) return '待开放'
  const date = new Date(value)
  if (!Number.isFinite(date.getTime())) {
    const text = String(value)
    return text.includes('T') ? `${text.slice(5, 10).replace('-', '月')}日 00:00` : text
  }
  return `${date.getMonth() + 1}月${date.getDate()}日 00:00`
}

function lockedUnlockMessage(item) {
  if (!item?.published || item?.lockReason === 'NOT_PUBLISHED') {
    return '待教师发布后开放'
  }
  return `${lockedUnlockLabel(item)} 开放`
}

function normalizeTaskAssignees(task) {
  const source = Array.isArray(task?.assignees) ? task.assignees : []
  if (source.length) {
    return source.map((item) => ({
      userId: Number(item.userId || item.user_id || item.id),
      username: item.username || item.name || '成员',
      positionName: item.positionName || item.position_name || item.roleInTeam || item.role_in_team || ''
    })).filter((item) => Number.isFinite(item.userId))
  }
  const ownerId = Number(task?.ownerUserId || task?.owner_user_id)
  if (Number.isFinite(ownerId) && task?.ownerName) return [{ userId: ownerId, username: task.ownerName, positionName: task.ownerPositionName || '' }]
  return []
}

function isScoreGeneratedTask(task) {
  const explicitSource = String(task.sourceType || task.source_type || task.originType || task.origin_type || '').toUpperCase()
  if (['AI_SCORE', 'SCORE_REPORT', 'AI_SCORE_REPORT'].includes(explicitSource)) return true
  const text = `${task.title || ''}\n${task.description || ''}\n${task.sourceLabel || ''}\n${task.sourceMeta || ''}`
  return /AI\s*路演评分报告|评分报告|评分扣分|扣分项|提分优先级|下一轮训练任务|综合评分[:：]/i.test(text)
}

function isPrepGeneratedTask(task) {
  const explicitSource = String(task.sourceType || task.source_type || task.originType || task.origin_type || '').toUpperCase()
  if (['PROJECT_PREP', 'PREP_SYNC', 'MATERIAL_PREP'].includes(explicitSource)) return true
  const text = `${task.title || ''}\n${task.description || ''}\n${task.sourceLabel || ''}\n${task.sourceMeta || ''}`
  return /准备页内容同步|准备页材料库|准备页版本记录|准备页讲稿制作|确认项目材料|审核策划书版本|同步讲稿修改/i.test(text)
}

function isTrainingLinkedTask(task) {
  const type = String(task?.taskType || task?.task_type || '').toUpperCase()
  const stage = String(task?.stageKey || task?.stage_key || '').toUpperCase()
  return type === 'TRAINING_DAY' || stage === 'TRAINING'
}

function taskSourceKey(item) {
  if (item?.sourceKey) return item.sourceKey
  if (item?.isTrainingTask || isTrainingLinkedTask(item?.raw)) return 'TRAINING'
  if (['score', 'review'].includes(item?.type)) return 'SCORE'
  return 'TEAM'
}

function createDeliveryWorkItem(item) {
  const status = normalStatus(item.status || 'PENDING_REVIEW')
  return {
    id: `delivery-${item.deliveryId}`,
    type: 'material',
    typeLabel: '资料',
    badge: '资',
    icon: 'material',
    title: item.title || '项目资料',
    summary: item.description || `${item.typeLabel} · ${materialStatusText(status)}`,
    status,
    statusLabel: materialStatusText(status),
    priority: ['CHANGES_REQUESTED', 'REJECTED'].includes(status) ? 'HIGH' : 'MEDIUM',
    ownerName: item.actorName || '团队成员',
    ownerUserId: item.raw?.ownerUserId || item.raw?.submitterUserId,
    assignees: item.actorName ? normalizeTaskAssignees({ assignees: [{ userId: item.raw?.ownerUserId || item.raw?.submitterUserId || item.deliveryId, username: item.actorName }] }) : [],
    stageKey: item.raw?.stageKey || team.value.currentStage || 'MATERIAL',
    stageLabel: stageTitle(item.raw?.stageKey || 'MATERIAL'),
    dueAt: item.updatedAt,
    sourceLabel: item.typeLabel || '项目资料',
    sourceMeta: `${item.actorName || '团队成员'} · ${formatDate(item.updatedAt)}`,
    isOverdue: false,
    raw: item,
    actions: [
      { key: 'open-material', label: '打开资料', kind: 'primary' },
      ...(canPreviewAttachment(item) ? [{ key: 'preview-material', label: '预览文件', kind: 'secondary' }] : [])
    ],
    links: attachmentUrl(item) ? [{ label: item.attachmentName || item.title || '资料文件', action: 'preview-material' }] : []
  }
}

function createRoadshowWorkItem(item, index, kind) {
  const isScore = kind === 'score'
  return {
    id: `${kind}-${index}-${slugText(item.title || item.description || index)}`,
    type: isScore ? 'score' : 'review',
    typeLabel: isScore ? '评分' : '复盘',
    badge: isScore ? '评' : '复',
    icon: isScore ? 'score' : 'roadshow',
    title: item.title || (isScore ? '评分扣分项待处理' : '复盘建议待处理'),
    summary: item.description || (isScore ? '来自 AI 评分报告的扣分原因' : '来自路演复盘的改进建议'),
    status: 'TODO',
    statusLabel: '待处理',
    priority: normalPriority(item.severity || (isScore ? 'HIGH' : 'MEDIUM')),
    ownerName: '团队',
    ownerUserId: null,
    assignees: [],
    stageKey: isScore ? 'ROADSHOW' : 'REVIEW',
    stageLabel: isScore ? '路演展示' : '复盘提升',
    dueAt: activeRoadshow.value?.updatedAt || activeRoadshow.value?.startedAt || '',
    sourceLabel: isScore ? 'AI 评分扣分项' : '路演复盘建议',
    sourceMeta: activeRoadshow.value?.meetingTitle || '路演评分报告',
    isOverdue: false,
    raw: item,
    actions: [
      { key: 'open-review', label: '查看复盘', kind: 'primary' },
      { key: 'create-task', label: '拆成任务', kind: 'secondary' }
    ],
    links: [{ label: activeRoadshow.value?.meetingTitle || '评分报告', action: 'open-review' }]
  }
}

function createSystemWorkItems() {
  const items = []
  const videoMaterial = deliveryItems.value.find((item) => materialFilterKey(item) === 'VIDEO')
  if (videoMaterial && !activeRoadshowProblems.value.length) {
    items.push({
      id: `system-video-score-${videoMaterial.deliveryId}`,
      type: 'system',
      typeLabel: '建议',
      badge: '建',
      icon: 'system',
      title: '已上传路演视频，建议发起 AI 评分',
      summary: `可基于「${videoMaterial.title}」生成评分报告和扣分项`,
      status: 'TODO',
      statusLabel: '建议',
      priority: 'MEDIUM',
      ownerName: '系统',
      ownerUserId: null,
      assignees: [],
      stageKey: 'ROADSHOW',
      stageLabel: '路演展示',
      dueAt: videoMaterial.updatedAt,
      sourceLabel: '系统建议',
      sourceMeta: '视频资料已就绪',
      isOverdue: false,
      raw: videoMaterial,
      actions: [{ key: 'upload-score', label: '上传视频评分', kind: 'primary' }],
      links: [{ label: videoMaterial.title, action: 'open-material' }]
    })
  }
  return items
}

function normalStatus(value) {
  const status = String(value || '').toUpperCase()
  if (status === 'PENDING') return 'TODO'
  if (status === 'REVIEWING') return 'PENDING_REVIEW'
  return status || 'TODO'
}

function normalPriority(value) {
  const priority = String(value || '').toUpperCase()
  if (['CRITICAL', 'HIGH'].includes(priority)) return 'HIGH'
  if (['LOW'].includes(priority)) return 'LOW'
  return 'MEDIUM'
}

function normalStageKey(value) {
  return String(value || '').toUpperCase()
}

function stageTitle(stageKey) {
  const key = normalStageKey(stageKey)
  const stage = stages.value.find((item) => normalStageKey(item.stageKey) === key)
  const fallback = fallbackStageFilters.find((item) => item.key === key)
  return stage?.title || fallback?.label || currentStageTitle.value || '未设置阶段'
}

function isOverdueDate(value, status) {
  if (!value || ['DONE', 'APPROVED'].includes(normalStatus(status))) return false
  const time = new Date(value).getTime()
  return Number.isFinite(time) && time < Date.now()
}

function isCompletedWorkItem(item) {
  return ['DONE', 'APPROVED'].includes(normalStatus(item?.status))
}

function isActionablyOverdue(item) {
  if (isLockedWorkItem(item)) return false
  if (!item?.isOverdue || isCompletedWorkItem(item)) return false
  return !['PENDING_REVIEW', 'REVIEWING'].includes(normalStatus(item.status))
}

function isLocalToday(value) {
  if (!value) return false
  const date = new Date(value)
  if (!Number.isFinite(date.getTime())) return false
  const today = new Date()
  return date.getFullYear() === today.getFullYear()
    && date.getMonth() === today.getMonth()
    && date.getDate() === today.getDate()
}

function priorityRank(priority) {
  return { HIGH: 3, MEDIUM: 2, LOW: 1 }[normalPriority(priority)] || 0
}

function statusRank(status) {
  const normalized = normalStatus(status)
  if (['BLOCKED'].includes(normalized)) return 5
  if (['PENDING_REVIEW', 'REVIEWING', 'CHANGES_REQUESTED', 'REJECTED'].includes(normalized)) return 4
  if (['TODO', 'IN_PROGRESS'].includes(normalized)) return 3
  if (['DRAFT'].includes(normalized)) return 2
  if (['DONE', 'APPROVED'].includes(normalized)) return 0
  return 1
}

function compareWorkItems(a, b) {
  const aLocked = isLockedWorkItem(a)
  const bLocked = isLockedWorkItem(b)
  if (aLocked !== bLocked) return aLocked ? 1 : -1
  if (a.isOverdue !== b.isOverdue) return a.isOverdue ? -1 : 1
  const statusDiff = statusRank(b.status) - statusRank(a.status)
  if (statusDiff) return statusDiff
  const priorityDiff = priorityRank(b.priority) - priorityRank(a.priority)
  if (priorityDiff) return priorityDiff
  const aTime = new Date(a.trainingDate || a.scheduledUnlockAt || a.dueAt || 0).getTime()
  const bTime = new Date(b.trainingDate || b.scheduledUnlockAt || b.dueAt || 0).getTime()
  if (aLocked && bLocked) return aTime - bTime
  return bTime - aTime
}

function workProgressValue(item) {
  const status = normalStatus(item?.status)
  if (['DONE', 'APPROVED'].includes(status)) return 100
  if (['IN_PROGRESS', 'REVIEWING'].includes(status)) return 62
  if (['PENDING_REVIEW', 'CHANGES_REQUESTED', 'REJECTED'].includes(status)) return 48
  if (item?.isOverdue || item?.priority === 'HIGH' || status === 'BLOCKED') return 34
  if (['DRAFT'].includes(status)) return 18
  return 0
}

function workProgressClass(item) {
  const status = normalStatus(item?.status)
  return {
    done: ['DONE', 'APPROVED'].includes(status),
    warning: item?.isOverdue || item?.priority === 'HIGH' || status === 'BLOCKED',
    muted: workProgressValue(item) === 0
  }
}

function workProgressStyle(item) {
  const value = Math.max(0, Math.min(100, workProgressValue(item)))
  return { '--progress': `${value}%` }
}

function isMyWorkItem(item) {
  return Number(item.ownerUserId) === Number(currentUserId.value)
    || item.assignees?.some((member) => Number(member.userId) === Number(currentUserId.value))
}

function simpleTaskStatusLabel(item) {
  if (item?.isOverdue) return '已过期'
  return item?.statusLabel || taskStatusText(item?.status)
}

function focusedTaskStatusLabel(item) {
  if (isLockedWorkItem(item)) {
    return item?.published === false || item?.lockReason === 'NOT_PUBLISHED' ? '待教师发布' : '未开放'
  }
  const status = normalStatus(item?.status)
  if (['PENDING_REVIEW', 'REVIEWING'].includes(status)) return '已提交 · 待审核'
  if (item?.isTrainingTask && isActionablyOverdue(item)) return '待补交 · 已超期'
  if (isActionablyOverdue(item)) return '待处理 · 已超期'
  if (normalStatus(item?.status) === 'CHANGES_REQUESTED') return '需修改'
  return item?.statusLabel || taskStatusText(item?.status)
}

function priorityText(priority) {
  const normalized = normalPriority(priority)
  if (normalized === 'HIGH') return '高'
  if (normalized === 'LOW') return '低'
  return '中'
}

function sortWorkItems(items, mode) {
  const list = [...items]
  if (mode === 'due') {
    return list.sort((a, b) => new Date(a.dueAt || '9999-12-31').getTime() - new Date(b.dueAt || '9999-12-31').getTime())
  }
  if (mode === 'priority') {
    return list.sort((a, b) => priorityRank(b.priority) - priorityRank(a.priority) || compareWorkItems(a, b))
  }
  if (mode === 'updated') {
    return list.sort((a, b) => new Date(b.updatedAt || b.dueAt || 0).getTime() - new Date(a.updatedAt || a.dueAt || 0).getTime())
  }
  return list.sort(compareWorkItems)
}

function cycleWorkSort() {
  const modes = ['smart', 'due', 'priority', 'updated']
  const index = modes.indexOf(workSortMode.value)
  workSortMode.value = modes[(index + 1) % modes.length]
}

function cycleWorkDensity() {
  workDensity.value = workDensity.value === 'comfortable' ? 'compact' : 'comfortable'
}

function toggleWorkSummary() {
  workSummaryVisible.value = !workSummaryVisible.value
}

function slugText(value) {
  return String(value || '').replace(/\s+/g, '-').slice(0, 24)
}

function selectWorkItem(item) {
  selectedWorkItemId.value = item?.id || ''
}

function openTaskDetailDrawer(item) {
  if (!item?.raw) return
  selectedWorkItemId.value = item.id
  activeTaskDetailItemId.value = item.id
}

function closeTaskDetailDrawer() {
  activeTaskDetailItemId.value = ''
}

function openTaskSubmissionDrawer(item) {
  if (!item?.raw) return
  selectedWorkItemId.value = item.id
  activeTaskDetailItemId.value = ''
  if (!submissionTypeDrafts[item.raw.id]) submissionTypeDrafts[item.raw.id] = suggestedSubmissionType(item.raw)
  if (submissionSyncDrafts[item.raw.id] === undefined) submissionSyncDrafts[item.raw.id] = true
  ensureSubmissionFiles(item.raw.id)
  ensureSubmissionLinks(item.raw.id)
  activeTaskSubmissionItemId.value = item.id
}

function closeTaskSubmissionDrawer() {
  activeTaskSubmissionItemId.value = ''
}

function runWorkItemAction(item, actionKey) {
  if (!item) return
  const key = actionKey || item.actions?.[0]?.key
  if (key === 'open-task') return openTaskDetailDrawer(item)
  if (key === 'review-task-submission') return openTaskSubmissionReview(item)
  if (key === 'submit-task') return openTaskSubmissionDrawer(item)
  if (key === 'open-material') return inspectDelivery(item.raw)
  if (key === 'preview-material') return previewAttachment(item.raw)
  if (key === 'preview-task') return previewAttachment(item.raw)
  if (key === 'open-review') {
    activeTeamSection.value = 'review'
    return
  }
  if (key === 'open-prep') {
    router.push({
      path: '/script-editor',
      query: selectedTeamId.value ? { teamId: selectedTeamId.value } : {}
    })
    return
  }
  if (key === 'create-task') return openTaskDialog()
  if (key === 'upload-score') return goVideoScoreUpload()
}

function openTaskSubmissionReview(item) {
  const delivery = latestTaskSubmissionDelivery(item?.raw)
  if (!delivery) {
    ElMessage.warning('没有找到这条任务的最新提交记录，请刷新后重试')
    return
  }
  if (!canReviewDelivery(delivery)) {
    ElMessage.warning('当前账号没有审核该成果的权限')
    return
  }
  openDeliveryReview(delivery)
}

function suggestedSubmissionType(task) {
  const text = `${task?.taskType || ''} ${task?.taskTypeLabel || ''} ${task?.title || ''}`.toLowerCase()
  if (text.includes('ppt')) return 'PPT'
  if (text.includes('讲稿') || text.includes('逐字稿') || text.includes('script')) return 'SCRIPT'
  if (text.includes('代码') || text.includes('code') || text.includes('源码')) return 'CODE'
  if (text.includes('视频') || text.includes('录屏') || text.includes('video')) return 'VIDEO'
  if (text.includes('数据') || text.includes('表格') || text.includes('data')) return 'DATA'
  if (text.includes('设计') || text.includes('原型') || text.includes('ui')) return 'DESIGN'
  if (text.includes('链接') || text.includes('仓库') || text.includes('网盘')) return 'LINK'
  if (text.includes('材料') || text.includes('报告') || text.includes('文档')) return 'DOCUMENT'
  return 'OTHER'
}

function submissionTypeLabel(type) {
  return submissionTypeOptions.find((item) => item.key === type)?.label || '其他'
}

function submissionAssets(item) {
  const assets = Array.isArray(item?.assets) ? item.assets : []
  if (assets.length) return assets
  const url = attachmentUrl(item)
  if (!url) return []
  return [{
    id: `legacy-${item.id || url}`,
    fileUrl: url,
    fileName: attachmentName(item),
    fileSize: attachmentSize(item),
    fileType: attachmentMime(item)
  }]
}

function recordSubmissionLinks(item) {
  return Array.isArray(item?.links) ? item.links.filter((link) => link?.url) : []
}

function submissionSummary(item) {
  const assets = submissionAssets(item).length
  const links = recordSubmissionLinks(item).length
  if (assets && links) return `${assets} 个文件，${links} 个链接`
  if (assets) return `${assets} 个成果文件`
  if (links) return `${links} 个成果链接`
  return '提交了成果'
}

const memoryEmptyReviewText = computed(() => {
  if (roadshowMemory.value?.memoryStatus === 'SINGLE_ROUND') {
    return roadshowMemory.value?.memoryStatusText || '已完成首轮评分，下一轮会复检本轮扣分项。'
  }
  if (roadshowMemory.value?.memoryStatus === 'EMPTY') {
    return roadshowMemory.value?.memoryStatusText || '暂无已完成评分。'
  }
  return '暂无可对比的历史扣分项。'
})
const memoryDeltaText = computed(() => {
  const value = Number(roadshowMemory.value?.improvementDelta || 0)
  if (!Number.isFinite(value) || value === 0) return '0'
  return `${value > 0 ? '+' : ''}${formatScore(value)}`
})

const axisPoints = computed(() => dimensions.map((item, index) => radarCoordinate(100, index, item.label)))
const abilityPoints = computed(() => activeAbilityList.value.map((item, index) => radarCoordinate(item.value, index, item.label)))
const labelPoints = computed(() => dimensions.map((item, index) => {
  const point = radarCoordinate(116, index, item.label)
  return {
    label: item.label,
    left: 50 + (point.x / 260) * 100,
    top: 50 + (point.y / 260) * 100
  }
}))

function syntheticStageTasks(stage) {
  const title = stage?.title || '阶段任务'
  const status = String(stage?.status || '').toUpperCase()
  if (status === 'DONE') {
    return [{ id: `${stage.stageKey}-done`, title: `${title}已完成`, ownerName: '团队', status: 'DONE', dueAt: stage?.dueDate }]
  }
  if (status === 'IN_PROGRESS') {
    return [{ id: `${stage.stageKey}-active`, title: `推进${title}关键交付`, ownerName: '团队', status: 'IN_PROGRESS', dueAt: stage?.dueDate }]
  }
  return [{ id: `${stage.stageKey}-pending`, title: `等待进入${title}`, ownerName: '团队', status: 'PENDING', dueAt: stage?.dueDate }]
}

function materialFilterKey(item) {
  const kind = attachmentKind(item)
  if (kind === 'PPT') return 'PPT'
  if (kind === 'VIDEO') return 'VIDEO'
  if (kind === 'IMAGE') return 'IMAGE'
  if (kind === 'DOC' || kind === 'PDF') return 'DOC'
  if (kind === 'SHEET') return 'DATA'
  const type = String(item?.typeLabel || item?.title || '').toLowerCase()
  if (type.includes('讲稿') || type.includes('script')) return 'SCRIPT'
  return 'OTHER'
}

function fileKindLabel(item) {
  const kind = attachmentKind(item)
  const map = {
    PPT: 'P',
    DOC: 'W',
    PDF: 'PDF',
    SHEET: 'X',
    VIDEO: '▶',
    IMAGE: '图',
    PACKAGE: '包',
    FILE: '文'
  }
  return map[kind] || '文'
}

function fileKindClass(item) {
  return String(attachmentKind(item) || 'FILE').toLowerCase()
}

function canSubmitTask(task) {
  if (task.currentUserIsOwner !== undefined) {
    return Boolean(task.currentUserIsOwner)
  }
  if (task.currentUserCanSubmit !== undefined) {
    return Boolean(task.currentUserCanSubmit)
  }
  const assignees = normalizeTaskAssignees(task)
  return Number(task.ownerUserId) === Number(currentUserId.value)
    || assignees.some((member) => Number(member.userId) === Number(currentUserId.value))
}

function canReviewTaskSubmission(task, status = normalStatus(task?.latestSubmissionStatus || task?.status)) {
  return Boolean(
    task?.latestSubmissionId
    && canReviewSubmission.value
    && ['PENDING_REVIEW', 'REVIEWING'].includes(normalStatus(status))
  )
}

function latestTaskSubmissionDelivery(task) {
  const submissionId = task?.latestSubmissionId
  if (!submissionId) return null
  return deliveryItems.value.find((item) => item.source === 'SUBMISSION' && Number(item.raw?.id) === Number(submissionId)) || null
}

function submitLockedReason(task) {
  if (canSubmitTask(task)) return ''
  if (task.submitLockedReason) return task.submitLockedReason
  if (Number(task.ownerUserId) !== Number(currentUserId.value)) return '只有任务负责人可以提交成果'
  return ''
}

function taskSubmissionType(taskId) {
  return submissionTypeDrafts[taskId] || 'OTHER'
}

function setTaskSubmissionType(taskId, type) {
  submissionTypeDrafts[taskId] = type
}

function taskSubmissionSyncEnabled(taskId) {
  return submissionSyncDrafts[taskId] !== false
}

function toggleTaskSubmissionSync(taskId) {
  submissionSyncDrafts[taskId] = !taskSubmissionSyncEnabled(taskId)
}

function ensureSubmissionFiles(taskId) {
  if (!submissionFileQueues[taskId]) submissionFileQueues[taskId] = []
  return submissionFileQueues[taskId]
}

function ensureRetainedSubmissionAssets(taskId) {
  if (!submissionRetainedAssets[taskId]) submissionRetainedAssets[taskId] = []
  return submissionRetainedAssets[taskId]
}

function retainedSubmissionAssets(taskId) {
  return ensureRetainedSubmissionAssets(taskId)
}

function submissionAssetKey(asset) {
  return String(asset?.id || asset?.fileUrl || asset?.url || asset?.attachmentUrl || '')
}

function removeRetainedSubmissionAsset(taskId, asset) {
  const assets = ensureRetainedSubmissionAssets(taskId)
  const key = submissionAssetKey(asset)
  const index = assets.findIndex((item) => submissionAssetKey(item) === key)
  if (index >= 0) assets.splice(index, 1)
}

function taskSubmissionFiles(taskId) {
  return ensureSubmissionFiles(taskId)
}

function ensureSubmissionLinks(taskId) {
  if (!submissionLinks[taskId]) submissionLinks[taskId] = []
  return submissionLinks[taskId]
}

function taskSubmissionLinks(taskId) {
  return ensureSubmissionLinks(taskId)
    .map((item) => ({
      title: String(item.title || '').trim(),
      url: String(item.url || '').trim(),
      linkType: item.linkType || 'OTHER'
    }))
    .filter((item) => item.url)
}

function addSubmissionLink(taskId) {
  ensureSubmissionLinks(taskId).push({ title: '', url: '', linkType: 'OTHER' })
}

function removeSubmissionLink(taskId, index) {
  ensureSubmissionLinks(taskId).splice(index, 1)
}

function resetSubmissionDraft(taskId) {
  submissionDrafts[taskId] = ''
  submissionLinkDrafts[taskId] = ''
  delete submissionFiles[taskId]
  delete submissionFileMeta[taskId]
  submissionFileQueues[taskId] = []
  submissionRetainedAssets[taskId] = []
  submissionLinks[taskId] = []
  submissionTypeDrafts[taskId] = 'OTHER'
  submissionSyncDrafts[taskId] = true
}

function openDetailSubmissionEditor() {
  const task = detailTask.value
  if (!task?.id || !canSubmitTask(task)) return
  const latest = detailLatestSubmission.value
  submissionDrafts[task.id] = latest?.content || ''
  submissionTypeDrafts[task.id] = latest?.submissionType || suggestedSubmissionType(task)
  submissionSyncDrafts[task.id] = latest?.syncToMaterial !== false
  submissionFileQueues[task.id] = []
  submissionRetainedAssets[task.id] = submissionAssets(latest).map((asset) => ({ ...asset }))
  submissionLinks[task.id] = recordSubmissionLinks(latest).map((link) => ({
    title: link.title || '',
    url: link.url || '',
    linkType: link.linkType || 'OTHER'
  }))
  detailSubmissionEditorOpen.value = true
}

function closeDetailSubmissionEditor() {
  const taskId = detailTask.value?.id
  if (taskId) resetSubmissionDraft(taskId)
  detailSubmissionEditorOpen.value = false
}

async function submitDetailVersion() {
  const task = detailTask.value
  if (!task?.id) return
  const result = await submitTask(task)
  if (!result) return
  detailSubmissionEditorOpen.value = false
  detailHistoryExpanded.value = false
  const submissionId = result.id || result.submissionId
  router.replace({
    path: `/project-team/details/task-${task.id}`,
    query: {
      teamId: selectedTeamId.value || route.query.teamId || undefined,
      submissionId: submissionId || undefined
    }
  })
}

const taskUploadNonce = reactive({})

function handleTaskFileChange(task, eventOrFiles) {
  const files = Array.isArray(eventOrFiles)
    ? eventOrFiles
    : eventOrFiles instanceof File
      ? [eventOrFiles]
      : Array.from(eventOrFiles?.target?.files || [])
  if (!files.length) return
  const queue = ensureSubmissionFiles(task.id)
  files.forEach((file) => {
    queue.push({
      id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
      file,
      name: file.name,
      size: file.size,
      type: file.type
    })
  })
  submissionFiles[task.id] = queue[0]?.file
  submissionFileMeta[task.id] = queue[0]
  if (eventOrFiles?.target) eventOrFiles.target.value = ''
}

/** DropFileUpload：追加后重置组件以便继续拖入 */
function addTaskFilesFromDrop(task, value) {
  handleTaskFileChange(task, value)
  taskUploadNonce[task.id] = (taskUploadNonce[task.id] || 0) + 1
}

function removeTaskFile(taskId, fileId) {
  const queue = ensureSubmissionFiles(taskId)
  const index = queue.findIndex((item) => item.id === fileId)
  if (index >= 0) queue.splice(index, 1)
  if (queue[0]) {
    submissionFiles[taskId] = queue[0].file
    submissionFileMeta[taskId] = queue[0]
  } else {
    delete submissionFiles[taskId]
    delete submissionFileMeta[taskId]
  }
}

async function uploadTaskAttachment(file) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('category', 'task-submission')
  const res = await request.post('/api/upload', formData)
  const data = res.data || {}
  return {
    fileUrl: data.url,
    fileName: data.name || file.name,
    fileSize: Number(data.size || file.size || 0),
    fileType: data.type || file.type || '',
    assetKind: 'MAIN',
    attachmentUrl: data.url,
    attachmentName: data.name || file.name,
    attachmentSize: Number(data.size || file.size || 0),
    attachmentType: data.type || file.type || ''
  }
}

function selectedFileName(taskId) {
  const queue = taskSubmissionFiles(taskId)
  if (queue.length > 1) return `${queue.length} 个成果文件`
  return queue[0]?.name || submissionFileMeta[taskId]?.name || ''
}

function selectedFileHelp(taskId) {
  const queue = taskSubmissionFiles(taskId)
  if (queue.length > 1) {
    const totalSize = queue.reduce((sum, item) => sum + Number(item.size || 0), 0)
    return `${queue.length} 个文件 · ${formatFileSize(totalSize)}`
  }
  const meta = queue[0] || submissionFileMeta[taskId]
  if (!meta) return ''
  return `${attachmentKind(meta)} · ${formatFileSize(meta.size)}`
}

function deliveryText(task) {
  if (task.latestSubmissionStatus) return `已提交 · ${materialStatusText(task.latestSubmissionStatus)}`
  if (task.status === 'CHANGES_REQUESTED') return '需按审核意见重新提交'
  if (task.status === 'DONE') return '已验收'
  return '等待负责人提交'
}

function taskCountByFilter(key) {
  if (key === 'ALL') return tasks.value.length
  return tasks.value.filter((item) => item.status === key).length
}

function materialCountByFilter(key) {
  if (key === 'ALL') return materials.value.length
  return materials.value.filter((item) => item.reviewStatus === key).length
}

function deliveryCountByFilter(key) {
  if (key === 'ALL') return deliveryItems.value.length
  return deliveryItems.value.filter((item) => item.status === key).length
}

function inspectDelivery(item) {
  inspectedDeliveryId.value = item?.deliveryId || null
}

function closeMaterialInspector() {
  inspectedDeliveryId.value = null
}

function openDeliveryReview(item) {
  activeReviewDeliveryId.value = item?.deliveryId || null
  reviewDialogComment.value = ''
}

function closeDeliveryReview() {
  activeReviewDeliveryId.value = null
  reviewDialogComment.value = ''
}

async function submitDeliveryReview(status) {
  const item = activeReviewDelivery.value
  if (!item) return
  if (item.source === 'SUBMISSION') {
    await reviewSubmission(item.raw, status, reviewDialogComment.value)
  } else {
    await reviewMaterial(item.raw, status, reviewDialogComment.value)
  }
  closeDeliveryReview()
}

function canReviewDelivery(item) {
  if (!item || item.status === 'APPROVED') return false
  if (item.source === 'SUBMISSION') return canReviewSubmission.value
  return canReviewMaterial.value
}

function deliveryClass(item) {
  return [
    statusClass(item?.status),
    {
      dormant: item?.status === 'DRAFT',
      review: item?.status === 'PENDING_REVIEW',
      warning: item?.status === 'CHANGES_REQUESTED' || item?.status === 'REJECTED',
      complete: item?.status === 'APPROVED'
    }
  ]
}

function deliveryUrl(item) {
  return attachmentUrl(item)
}

function attachmentUrl(item) {
  return item?.attachmentUrl ||
    item?.latestAttachmentUrl ||
    item?.fileUrl ||
    item?.raw?.attachmentUrl ||
    item?.raw?.latestAttachmentUrl ||
    item?.raw?.fileUrl ||
    ''
}

function attachmentName(item) {
  const url = attachmentUrl(item)
  return item?.attachmentName ||
    item?.latestAttachmentName ||
    item?.fileName ||
    item?.originalName ||
    item?.raw?.attachmentName ||
    item?.raw?.latestAttachmentName ||
    item?.raw?.fileName ||
    item?.raw?.originalName ||
    readableFileName(url) ||
    ''
}

function attachmentMime(item) {
  return String(
    item?.attachmentType ||
    item?.latestAttachmentType ||
    item?.fileType ||
    item?.type ||
    item?.raw?.attachmentType ||
    item?.raw?.latestAttachmentType ||
    item?.raw?.fileType ||
    item?.raw?.type ||
    ''
  ).toLowerCase()
}

function attachmentSize(item) {
  return Number(
    item?.attachmentSize ||
    item?.latestAttachmentSize ||
    item?.fileSize ||
    item?.size ||
    item?.raw?.attachmentSize ||
    item?.raw?.latestAttachmentSize ||
    item?.raw?.fileSize ||
    item?.raw?.size ||
    0
  )
}

function normalizeDeliveryItem(item) {
  const url = attachmentUrl(item.raw || item)
  const name = attachmentName(item.raw || item)
  const type = attachmentMime(item.raw || item)
  const size = attachmentSize(item.raw || item)
  return {
    ...item,
    attachmentUrl: url,
    attachmentName: name,
    attachmentType: type,
    attachmentSize: size
  }
}

function attachmentKind(item) {
  const name = String(attachmentName(item) || attachmentUrl(item) || item?.name || '')
  const type = attachmentMime(item)
  const ext = fileExt(name)
  if (type.includes('pdf') || ext === 'pdf') return 'PDF'
  if (type.startsWith('image/') || ['png', 'jpg', 'jpeg', 'webp', 'gif'].includes(ext)) return 'IMAGE'
  if (type.startsWith('video/') || ['mp4', 'webm', 'mov'].includes(ext)) return 'VIDEO'
  if (['ppt', 'pptx'].includes(ext)) return 'PPT'
  if (['doc', 'docx'].includes(ext)) return 'DOC'
  if (['xls', 'xlsx'].includes(ext)) return 'SHEET'
  if (['zip', 'rar', '7z'].includes(ext)) return 'PACKAGE'
  return 'FILE'
}

function attachmentKindLabel(kind) {
  const map = {
    PDF: 'PDF 文档',
    IMAGE: '图片',
    VIDEO: '视频',
    PPT: '演示文稿',
    DOC: '文档',
    SHEET: '表格',
    PACKAGE: '压缩包',
    FILE: '文件'
  }
  return map[kind] || '文件'
}

function deliveryCategoryLabel(item) {
  if (item?.source === 'SUBMISSION') {
    return submissionTypeLabel(item.raw?.submissionType) || '任务提交'
  }
  return item?.typeLabel || materialTypeText(item?.raw?.materialType) || '项目材料'
}

function isExternalDelivery(item) {
  const materialType = String(item?.raw?.materialType || item?.materialType || '').toUpperCase()
  const sourceType = String(item?.raw?.sourceType || item?.sourceType || '').toUpperCase()
  const submissionType = String(item?.raw?.submissionType || item?.submissionType || '').toUpperCase()
  const url = deliveryUrl(item)
  return materialType === 'LINK' ||
    sourceType === 'TASK_LINK' ||
    submissionType === 'LINK' ||
    /^https?:\/\//i.test(url)
}

function deliveryAssetKindLabel(item) {
  if (isExternalDelivery(item)) return '外部链接'
  return attachmentKindLabel(attachmentKind(item))
}

function canPreviewAttachment(item) {
  const name = String(attachmentName(item) || item?.name || attachmentUrl(item) || '')
  const type = attachmentMime(item)
  const ext = fileExt(name)
  return type.includes('pdf') ||
    type.startsWith('image/') ||
    type.startsWith('video/') ||
    type.includes('word') ||
    type.includes('document') ||
    type.includes('sheet') ||
    type.includes('excel') ||
    type.includes('presentation') ||
    type.includes('powerpoint') ||
    ['pdf', 'png', 'jpg', 'jpeg', 'webp', 'gif', 'svg',
     'mp4', 'webm', 'mov', 'mkv', 'avi',
     'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
     'txt', 'md'].includes(ext)
}

function materialFileName(item) {
  const url = attachmentUrl(item)
  if (!url) return '尚未关联文件'
  const storedName = attachmentName(item)
  const titleName = item?.title || item?.name || item?.raw?.name || item?.raw?.taskTitle || ''
  if (titleName && (!storedName || isOpaqueUploadedName(storedName))) return titleName
  return storedName || titleName || '项目材料附件'
}

function deliveryStorageName(item) {
  const storedName = attachmentName(item)
  const readableName = deliveryFileName(item)
  if (!storedName || !readableName || storedName === readableName) return ''
  return storedName
}

function materialInspectHint(item) {
  if (!attachmentUrl(item)) return '当前材料只有文字记录，尚未上传或关联附件。'
  if (isExternalDelivery(item)) return '这是外部成果链接，请打开链接查看在线文档、仓库、网盘或演示地址。'
  const kind = attachmentKind(item)
  if (kind === 'PACKAGE') return '压缩包无法在线展开，请下载后查看其中的项目文件。'
  const ext = fileExt(String(attachmentName(item) || item?.name || attachmentUrl(item) || ''))
  if (['doc', 'xls', 'ppt'].includes(ext)) return '旧版 Office 格式预览能力有限，建议下载后用 Office 软件打开。'
  if (canPreviewAttachment(item)) return '该文件支持在线预览，也可以下载留档。'
  return '该类型暂不支持在线预览，请下载后查看。'
}

function deliveryFileName(item) {
  return materialFileName(item)
}

function deliveryInspectHint(item) {
  return materialInspectHint(item)
}

function openAttachment(url) {
  if (!url) return
  window.open(normalizeAttachmentUrl(url), '_blank', 'noopener,noreferrer')
}

function openExternalLink(url) {
  if (!url) return
  window.open(url, '_blank', 'noopener,noreferrer')
}

function previewAttachment(item) {
  const url = attachmentUrl(item)
  if (!url) return
  const ext = fileExt(String(attachmentName(item) || item.name || url || ''))
  // .doc and .old xls/ppt can't be previewed client-side — fall back to new tab
  if (ext === 'doc' || ext === 'xls' || ext === 'ppt') {
    openAttachment(url)
    return
  }
  filePreviewUrl.value = normalizeAttachmentUrl(url)
  filePreviewName.value = attachmentName(item) || item.name || '文件预览'
  filePreviewType.value = attachmentMime(item)
  filePreviewVisible.value = true
}

function onPreviewDownload() {
  filePreviewVisible.value = false
  cleanupEvidenceBlob()
}

function cleanupEvidenceBlob() {
  if (evidenceBlobUrl.value?.startsWith('blob:')) {
    URL.revokeObjectURL(evidenceBlobUrl.value)
  }
  evidenceBlobUrl.value = ''
  filePreviewStartTime.value = 0
}

async function openEvidenceAnchor(anchor, memoryItem = null) {
  if (!anchor) return
  if (isRecordingAnchor(anchor)) {
    await previewRecordingAnchor(anchor, parseAnchorStartSeconds(anchor))
    return
  }
  const startTime = parseAnchorStartSeconds(anchor)
  const siblingRecording = startTime > 0 ? firstRecordingAnchor(memoryItem) : null
  if (siblingRecording) {
    await previewRecordingAnchor(siblingRecording, startTime)
    return
  }
  activeEvidenceAnchor.value = anchor
  await loadEvidenceExcerpt(anchor)
}

function closeEvidenceAnchor() {
  activeEvidenceAnchor.value = null
  activeEvidenceExcerpt.value = null
  evidenceExcerptLoading.value = false
  evidenceExcerptError.value = ''
}

async function loadEvidenceExcerpt(anchor) {
  activeEvidenceExcerpt.value = null
  evidenceExcerptError.value = ''
  const aiReportId = anchor?.aiReportId
  const sourceRef = String(anchor?.sourceRef || '')
  if (!selectedTeamId.value || !aiReportId || !sourceRef || String(anchor?.type || '').startsWith('recording_')) return
  evidenceExcerptLoading.value = true
  try {
    const res = await request.get(`/api/project-teams/${selectedTeamId.value}/evidence-excerpt`, {
      params: { aiReportId, sourceRef }
    })
    activeEvidenceExcerpt.value = res.data || res || null
  } catch (error) {
    evidenceExcerptError.value = error?.response?.data?.message || 'AI 原始片段读取失败，请稍后重试。'
  } finally {
    evidenceExcerptLoading.value = false
  }
}

async function previewRecordingAnchor(anchor, startTime = 0) {
  const sourceRef = String(anchor?.sourceRef || '')
  if (!sourceRef) {
    activeEvidenceAnchor.value = anchor
    return
  }
  try {
    if (evidenceBlobUrl.value?.startsWith('blob:')) URL.revokeObjectURL(evidenceBlobUrl.value)
    const fileType = recordingAnchorFileType(anchor)
    const res = await request.get(sourceRef, {
      responseType: 'blob',
      timeout: 60000
    })
    const blob = res instanceof Blob ? res : res.data
    const mime = fileType === 'audio' ? 'audio/webm' : 'video/webm'
    const playableBlob = blob.type && blob.type !== 'application/octet-stream' ? blob : new Blob([blob], { type: mime })
    evidenceBlobUrl.value = URL.createObjectURL(playableBlob)
    filePreviewUrl.value = evidenceBlobUrl.value
    filePreviewName.value = `${evidenceTypeText(anchor.type)}.${fileType === 'audio' ? 'webm' : 'webm'}`
    filePreviewType.value = mime
    filePreviewStartTime.value = Number(startTime || 0)
    filePreviewVisible.value = true
  } catch (error) {
    activeEvidenceAnchor.value = anchor
    ElMessage.error(error?.response?.data?.message || '证据播放失败，请检查录制权限或文件状态')
  }
}

function firstRecordingAnchor(memoryItem) {
  return memoryAnchors(memoryItem).find((anchor) => {
    const type = String(anchor?.type || '')
    return ['recording_video', 'recording_screen', 'recording_camera'].includes(type) && isRecordingAnchor(anchor)
  }) || null
}

function isRecordingAnchor(anchor) {
  return String(anchor?.type || '').startsWith('recording_') && String(anchor?.sourceRef || '').startsWith('/api/recording/')
}

function recordingAnchorFileType(anchor) {
  const type = String(anchor?.type || '')
  if (type.includes('audio')) return 'audio'
  if (type.includes('screen')) return 'screen'
  if (type.includes('camera')) return 'camera'
  return 'video'
}

function parseAnchorStartSeconds(anchor) {
  const source = String(anchor?.sourceRef || '')
  const hms = source.match(/(\d{1,2}):(\d{2}):(\d{2}(?:\.\d+)?)/)
  if (hms) return Number(hms[1]) * 3600 + Number(hms[2]) * 60 + Number(hms[3])
  const at = source.match(/@(\d{1,2}):(\d{1,2}(?:\.\d+)?)/)
  if (at) return Number(at[1]) * 60 + Number(at[2])
  const mmss = source.match(/(\d{1,2}):(\d{1,2}(?:\.\d+)?)(?:-|$)/)
  if (mmss) return Number(mmss[1]) * 60 + Number(mmss[2])
  return 0
}

function downloadAttachment(item) {
  const url = attachmentUrl(item)
  if (!url) return
  const link = document.createElement('a')
  link.href = normalizeAttachmentUrl(url)
  link.download = attachmentName(item) || item.name || 'project-delivery'
  document.body.appendChild(link)
  link.click()
  link.remove()
}

function normalizeAttachmentUrl(url) {
  if (!url) return ''
  if (/^https?:\/\//.test(url)) return url
  return url.startsWith('/') ? url : `/${url}`
}

function fileExt(name) {
  const parts = String(name || '').split('.')
  return parts.length > 1 ? parts.pop().toLowerCase() : ''
}

function readableFileName(url) {
  try {
    return decodeURIComponent(String(url || '').split('/').filter(Boolean).pop() || '')
  } catch {
    return String(url || '').split('/').filter(Boolean).pop() || ''
  }
}

function isOpaqueUploadedName(name) {
  const base = String(name || '').split('/').pop()?.replace(/\.[^.]+$/, '') || ''
  return /^[a-f0-9]{24,}$/i.test(base) || /^[a-f0-9]{8,}-[a-f0-9-]{18,}$/i.test(base)
}

function formatFileSize(value) {
  const size = Number(value || 0)
  if (!size) return '未知大小'
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / 1024 / 1024).toFixed(1)} MB`
}

function stageClass(stage) {
  const status = String(stage?.status || '').toUpperCase()
  return [
    statusClass(status),
    {
      current: status === 'IN_PROGRESS' || status === 'DONE',
      complete: status === 'DONE',
      optional: Boolean(stage?.optional),
      muted: status === 'PENDING'
    }
  ]
}

function taskClass(task) {
  const status = String(task?.status || '').toUpperCase()
  return [
    statusClass(status),
    {
      active: status === 'TODO' || status === 'IN_PROGRESS',
      review: status === 'REVIEWING',
      warning: status === 'CHANGES_REQUESTED',
      complete: status === 'DONE'
    }
  ]
}

function materialClass(item) {
  const status = String(item?.reviewStatus || '').toUpperCase()
  return [
    statusClass(status),
    {
      dormant: status === 'DRAFT',
      review: status === 'PENDING_REVIEW',
      warning: status === 'CHANGES_REQUESTED' || status === 'REJECTED',
      complete: status === 'APPROVED'
    }
  ]
}

function issueClass(issue) {
  const status = String(issue?.status || '').toUpperCase()
  const severity = String(issue?.severity || '').toUpperCase()
  return [
    statusClass(status || severity),
    {
      warning: severity === 'HIGH' || status === 'OPEN',
      active: status === 'IN_PROGRESS',
      complete: status === 'DONE'
    }
  ]
}

function normalizeInsightList(list) {
  return (Array.isArray(list) ? list : []).map((item) => {
    if (item && typeof item === 'object') {
      return {
        title: item.title || item.name || item.category || '复盘项',
        description: item.description || item.detail || item.summary || item.suggestion || item.action || '',
        severity: item.severity || 'MEDIUM',
        category: item.category || ''
      }
    }
    return { title: String(item || '复盘项'), description: String(item || ''), severity: 'MEDIUM', category: '' }
  })
}

function normalizeMemoryList(list) {
  return (Array.isArray(list) ? list : []).map((item) => {
    if (item && typeof item === 'object') {
      return {
        ...item,
        title: item.title || item.name || item.category || '复盘项',
        description: item.description || item.detail || item.summary || item.suggestion || item.action || '',
        severity: item.severity || 'MEDIUM',
        status: item.status || ''
      }
    }
    return { title: String(item || '复盘项'), description: String(item || ''), severity: 'MEDIUM', status: '' }
  })
}

function memoryIssueStatusText(status) {
  const map = {
    resolved: '已改进',
    not_resolved: '待继续',
    new: '新增'
  }
  return map[String(status || '').toLowerCase()] || '待确认'
}

function memoryAnchors(item) {
  return (Array.isArray(item?.evidenceAnchors) ? item.evidenceAnchors : [])
    .filter((anchor) => !isLowValueTranscriptAnchor(anchor))
}

function isLowValueTranscriptAnchor(anchor) {
  const type = String(anchor?.type || '')
  if (!type.includes('transcript') && !type.includes('转写')) return false
  const text = String(anchor?.summary || '').replace(/[\s，。,.!！?？]+/g, '')
  if (text.length <= 6) return true
  return ['大家好', '各位评委大家好', '老师好', '收到', '好的', '谢谢'].includes(text)
}

function evidenceAnchorText(anchor) {
  const typeMap = {
    transcript: '转写',
    transcript_segment: '转写片段',
    ai_issue: 'AI问题',
    ai_highlight: 'AI亮点',
    speech_quality: '语音',
    screen_ocr: '屏幕识别',
    key_frame: '关键帧',
    fusion_timeline: '融合时间线',
    recording_video: '完整录制',
    recording_camera: '摄像头',
    recording_screen: '屏幕录制',
    recording_audio: '音频',
    ai_result_file: '结果文件',
    evidence: '证据'
  }
  const label = typeMap[anchor?.type] || anchor?.type || '证据'
  const ref = anchor?.sourceRef ? ` · ${anchor.sourceRef}` : ''
  return `${label}${ref}`
}

function evidenceTypeText(type) {
  const label = evidenceAnchorText({ type, sourceRef: '' })
  return label.replace(/ · .*$/, '')
}

function formatEvidenceRaw(value) {
  try {
    return JSON.stringify(value, null, 2)
  } catch (error) {
    return String(value || '')
  }
}

function roadshowStatusText(status) {
  const map = {
    AI_COMPLETED: 'AI 已评分',
    MANUAL_SCORE: '评委已评分',
    WAITING_SCORE: '等待评分',
    NOT_BOUND: '未绑定',
    BINDABLE: '可绑定',
    completed: 'AI 已评分',
    failed: '评分失败',
    processing: '评分中'
  }
  return map[status] || status || '待复盘'
}

function bindableMeetingLabel(item) {
  const title = item?.meetingTitle || `会议 #${item?.meetingId || ''}`
  if (item?.createdByMe == 1 || item?.createdByMe === true) return `${title} · 我创建`
  if (item?.participated == 1 || item?.participated === true) return `${title} · 我参加`
  return title
}

function roadshowTypeText(type) {
  const map = { REHEARSAL: '彩排', FINAL: '正式路演', REVIEW: '复盘会议' }
  return map[type] || '路演会议'
}

function readinessText(level) {
  const map = {
    READY: '可进入正式路演',
    WATCH: '需要持续观察',
    RISK: '存在准备风险'
  }
  return map[level] || '等待数据'
}

function stageStatusText(status) {
  const map = { DONE: '已完成', IN_PROGRESS: '进行中', PENDING: '待开始', BLOCKED: '有卡点' }
  return map[status] || status || '未设置'
}

function taskStatusText(status) {
  const normalized = normalStatus(status)
  const map = {
    TODO: '待处理',
    IN_PROGRESS: '进行中',
    PENDING_REVIEW: '待审核',
    REVIEWING: '待审核',
    CHANGES_REQUESTED: '需修改',
    REJECTED: '已驳回',
    APPROVED: '已通过',
    DONE: '已完成'
  }
  return map[normalized] || normalized || '未知'
}

function materialStatusText(status) {
  const normalized = normalStatus(status)
  const map = {
    DRAFT: '草稿',
    PENDING_REVIEW: '待审核',
    REVIEWING: '待审核',
    APPROVED: '已通过',
    REJECTED: '已驳回',
    CHANGES_REQUESTED: '需修改',
    DONE: '已完成',
    TODO: '待处理',
    IN_PROGRESS: '进行中'
  }
  return map[normalized] || normalized || '未设置'
}

function materialTypeText(type) {
  const normalized = String(type || '').toUpperCase()
  const map = {
    PROGRESS: '项目进度',
    DOCS: '项目材料',
    DOC: '文档材料',
    PPT: 'PPT',
    SCRIPT: '逐字稿',
    VIDEO: '路演视频',
    IMAGE: '图片材料',
    DATA: '数据材料',
    CODE: '代码成果',
    LINK: '外部链接',
    OTHER: '项目材料'
  }
  return map[normalized] || '项目材料'
}

function roleInTeamText(role) {
  const map = { CAPTAIN: '队长', MEMBER: '队员', MENTOR: '指导', OBSERVER: '观察' }
  return map[role] || role || '成员'
}

function roleText(role) {
  const map = { STUDENT: '学生', TEACHER: '教师', ADMIN: '管理员', SCHOOL_ADMIN: '校级管理员' }
  return map[role] || role || '成员'
}

function uniqueOptions(values) {
  return Array.from(new Set(values.filter(Boolean))).sort((a, b) => String(a).localeCompare(String(b), 'zh-Hans-CN'))
}

function matchesFilter(value, filterValue) {
  return filterValue === 'ALL' || value === filterValue
}

function groupNamesOf(user) {
  return String(user?.userGroup || '')
    .split('、')
    .map((item) => item.trim())
    .filter(Boolean)
}

function dimensionLabel(key) {
  return dimensions.find((item) => item.key === key)?.label || key
}

function sourceTypeLabel(type) {
  const labels = {
    COURSE: '课程',
    EXAM: '测评',
    TASK: '任务',
    MATERIAL: '材料',
    ROADSHOW: '个人路演',
    ROADSHOW_CONTEXT: '团队路演',
    REVIEW: '复盘',
    BASELINE: '基础分'
  }
  return labels[type] || type
}

function evidenceWeightText(item) {
  const weight = Number(item?.weight || 0)
  return weight > 0 ? `权重${weight}` : '未计入'
}

function formatScore(value) {
  const number = Number(value || 0)
  return Number.isInteger(number) ? String(number) : number.toFixed(1).replace(/\.0$/, '')
}

function dimensionPercentValue(item) {
  const direct = Number(item?.percent)
  if (Number.isFinite(direct) && direct >= 0) return Math.round(Math.min(100, direct))
  const score = Number(item?.score)
  const maxScore = Number(item?.maxScore || item?.max_score)
  if (Number.isFinite(score) && Number.isFinite(maxScore) && maxScore > 0) {
    return Math.round(Math.min(100, Math.max(0, (score / maxScore) * 100)))
  }
  return Math.round(Math.min(100, Math.max(0, score || 0)))
}

function dimensionRatio(item) {
  const score = formatScore(item?.score || 0)
  const maxScore = formatScore(item?.maxScore || item?.max_score || 100)
  return `${score}/${maxScore}`
}

function statusClass(status) {
  return String(status || '').toLowerCase().replaceAll('_', '-')
}

function formatDate(value) {
  if (!value) return '未设置'
  return String(value).replace('T', ' ').slice(0, 16)
}

function formatShortDate(value) {
  if (!value) return '未设置'
  const raw = String(value)
  const match = raw.match(/(\d{4})[-/](\d{1,2})[-/](\d{1,2})/)
  if (match) return `${match[1].slice(2)}/${Number(match[2])}/${Number(match[3])}`
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return raw.slice(0, 10)
  return `${String(date.getFullYear()).slice(2)}/${date.getMonth() + 1}/${date.getDate()}`
}

function datePart(value) {
  const raw = String(value || '')
  const match = raw.match(/\d{4}-\d{2}-\d{2}/)
  if (match) return match[0]
  return currentDateTimeLocal().slice(0, 10)
}

function resolveTaskTypeKey(task) {
  return String(task?.taskType || task?.task_type || task?.businessType || task?.business_type || task?.categoryKey || task?.category_key || 'OTHER_BUSINESS').toUpperCase()
}

function resolveTaskTypeLabel(task) {
  const customLabel = String(task?.customTaskType || task?.custom_task_type || '').trim()
  const explicitLabel = String(task?.taskTypeLabel || task?.task_type_label || task?.businessTypeLabel || task?.business_type_label || '').trim()
  if (customLabel) return customLabel
  if (explicitLabel) return explicitLabel
  const key = resolveTaskTypeKey(task)
  return taskTypeOptions.find((item) => item.key === key)?.label || '其他业务'
}

function resolveTaskTimeSlot(task) {
  const value = String(task?.timeSlot || task?.time_slot || task?.timePeriod || task?.time_period || '').toUpperCase()
  if (['MORNING', 'AM', '上午'].includes(value)) return 'MORNING'
  if (['AFTERNOON', 'PM', '下午'].includes(value)) return 'AFTERNOON'
  if (['EVENING', 'NIGHT', '晚上'].includes(value)) return 'EVENING'
  const hour = new Date(task?.dueAt || task?.due_at || task?.updatedAt || '').getHours()
  if (Number.isFinite(hour)) {
    if (hour < 12) return 'MORNING'
    if (hour < 18) return 'AFTERNOON'
  }
  return 'EVENING'
}

function currentDateTimeLocal() {
  const date = new Date()
  date.setSeconds(0, 0)
  const offset = date.getTimezoneOffset() * 60000
  return new Date(date.getTime() - offset).toISOString().slice(0, 16)
}

function radarCoordinate(value, index, label = '') {
  const radius = Math.max(0, Math.min(100, Number(value) || 0))
  const angle = -Math.PI / 2 + (Math.PI * 2 * index) / dimensions.length
  return { label, x: Math.cos(angle) * radius, y: Math.sin(angle) * radius }
}

function radarPoints(values) {
  return values.map((value, index) => {
    const point = radarCoordinate(value, index)
    return `${point.x},${point.y}`
  }).join(' ')
}
</script>

<style scoped>
.team-page {
  position: relative;
  min-height: calc(100vh - 72px);
  overflow: hidden;
  padding: 54px 32px 80px;
  color: #f0f0fa;
  background-color: #ffffff;
  background-image: none;
}

.team-grid {
  position: absolute;
  inset: 0;
  pointer-events: none;
  opacity: 0.18;
  background-image:
    linear-gradient(rgba(240, 240, 250, 0.08) 1px, transparent 1px),
    linear-gradient(90deg, rgba(240, 240, 250, 0.08) 1px, transparent 1px);
  background-size: 72px 72px;
}

.team-hero,
.team-state-panel,
.metric-strip,
.stage-line,
.role-banner,
.work-tier,
.main-layout {
  position: relative;
  width: min(1320px, 100%);
  margin: 0 auto;
}

.team-hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  align-items: stretch;
  gap: 28px;
}

.cmd-kpi {
  display: grid;
  grid-template-columns: 132px minmax(0, 1fr);
  gap: 18px;
  align-items: stretch;
  padding: 20px;
  border: 1px solid rgba(240, 240, 250, 0.14);
  border-radius: 8px;
  background:
    linear-gradient(135deg, rgba(124, 255, 178, 0.08), transparent 70%),
    rgba(8, 10, 12, 0.84);
  box-shadow: 0 24px 70px rgba(0, 0, 0, 0.3);
}

.kpi-health {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 4px;
  padding-right: 18px;
  border-right: 1px solid rgba(240, 240, 250, 0.1);
}

.kpi-health span {
  color: rgba(240, 240, 250, 0.48);
  font-size: 10px;
  font-weight: 850;
  letter-spacing: 0.12em;
}

.kpi-health strong {
  color: #7cffb2;
  font-size: 40px;
  font-weight: 950;
  line-height: 1;
}

.kpi-health small {
  color: rgba(240, 240, 250, 0.56);
  font-size: 11px;
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px 14px;
  align-content: center;
}

.kpi-grid div {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.kpi-grid b {
  font-size: 24px;
  font-weight: 900;
  color: #f0f0fa;
  line-height: 1.1;
}

.kpi-grid span {
  color: rgba(240, 240, 250, 0.5);
  font-size: 11px;
  letter-spacing: 0.06em;
}

.kicker {
  color: rgba(124, 255, 178, 0.76);
  font-size: 12px;
  font-weight: 850;
  letter-spacing: 0.14em;
}

.team-hero h1 {
  margin: 12px 0 0;
  font-size: 48px;
  font-weight: 950;
}

.team-hero p,
.task-card p,
.material-card p,
.issue-list small,
.role-banner small,
.observe-panel p {
  color: rgba(240, 240, 250, 0.62);
  line-height: 1.8;
}

.team-switch {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 22px;
}

button,
input,
select,
textarea {
  font: inherit;
}

.team-switch button,
.ghost-btn,
.composer button,
.submit-box button,
.review-actions button,
.material-actions button,
.bind-form button,
.assign-task-btn,
.primary-action,
.project-modal-actions button,
.member-console-head button,
.attachment-actions button {
  min-height: 38px;
  border: 1px solid rgba(124, 255, 178, 0.36);
  border-radius: 8px;
  background: rgba(124, 255, 178, 0.1);
  color: #f0f0fa;
  cursor: pointer;
  font-weight: 850;
}

.team-switch button {
  padding: 0 14px;
}

.assign-task-btn {
  position: relative;
  min-width: 120px;
  padding: 0 12px 0 16px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  background:
    linear-gradient(135deg, rgba(124, 255, 178, 0.18), rgba(106, 166, 255, 0.09)),
    rgba(8, 10, 12, 0.86);
  box-shadow: 0 12px 36px rgba(124, 255, 178, 0.08);
}

.assign-task-btn i {
  width: 24px;
  height: 24px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: rgba(124, 255, 178, 0.2);
  color: #7cffb2;
  font-style: normal;
  font-size: 18px;
  line-height: 1;
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 14px;
  margin-top: 22px;
}

.primary-action {
  padding: 0 18px;
}

.hero-actions span {
  color: rgba(240, 240, 250, 0.5);
  font-size: 13px;
}

.team-switch button.active,
.ghost-btn:hover,
.composer button:hover,
.submit-box button:hover,
.assign-task-btn:hover,
.primary-action:hover,
.member-console-head button:hover {
  background: rgba(124, 255, 178, 0.18);
  border-color: rgba(124, 255, 178, 0.62);
}

.health-card,
.team-state-panel,
.metric-strip,
.stage-line article,
.role-banner,
.panel,
.task-card,
.material-card,
.review-card,
.score-card {
  border: 1px solid rgba(240, 240, 250, 0.14);
  border-radius: 8px;
  background: rgba(8, 10, 12, 0.84);
  box-shadow: 0 24px 70px rgba(0, 0, 0, 0.3);
}

.health-card {
  padding: 24px;
}

.team-state-panel {
  margin-top: 34px;
  padding: 28px;
  display: grid;
  gap: 12px;
  background:
    linear-gradient(135deg, rgba(106, 166, 255, 0.08), transparent 62%),
    rgba(8, 10, 12, 0.86);
}

.team-state-panel.warning {
  border-color: rgba(255, 138, 22, 0.34);
  background:
    linear-gradient(135deg, rgba(255, 138, 22, 0.1), transparent 62%),
    rgba(8, 10, 12, 0.86);
}

.team-state-panel h2 {
  margin: 0;
  font-size: 28px;
}

.team-state-panel p {
  max-width: 680px;
  margin: 0;
  color: rgba(240, 240, 250, 0.62);
  line-height: 1.8;
}

.team-state-panel .primary-action {
  width: max-content;
}

.health-card span,
.metric-strip span,
.stage-line em,
.task-top span,
.material-card span,
.score-card span,
.evidence-list span {
  color: rgba(240, 240, 250, 0.48);
  font-size: 11px;
  font-weight: 850;
  letter-spacing: 0.12em;
  font-style: normal;
}

.health-card strong {
  display: block;
  margin-top: 14px;
  color: #7cffb2;
  font-size: 48px;
}

.health-card small,
.metric-strip small,
.stage-line small {
  color: rgba(240, 240, 250, 0.56);
}

.stage-optional {
  margin-left: 6px;
  padding: 1px 6px;
  border-radius: 999px;
  font-size: 10px;
  font-style: normal;
  font-weight: 600;
  color: rgba(240, 240, 250, 0.72);
  background: rgba(106, 166, 255, 0.18);
  vertical-align: middle;
}

.stage-suggestion {
  margin: 8px 0 0;
  font-size: 12px;
  line-height: 1.45;
  color: rgba(170, 198, 255, 0.82);
}

.stage-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.stage-card-head em {
  min-width: 0;
}

.stage-edit-btn {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  padding: 0;
  border: 1px solid rgba(106, 166, 255, 0.28);
  border-radius: 8px;
  background: rgba(8, 14, 28, 0.55);
  color: rgba(214, 228, 255, 0.88);
  cursor: pointer;
  transition: border-color 0.18s ease, background 0.18s ease, color 0.18s ease;
}

.stage-edit-btn svg {
  width: 14px;
  height: 14px;
  fill: currentColor;
}

.stage-edit-btn:hover {
  border-color: rgba(124, 255, 178, 0.45);
  background: rgba(124, 255, 178, 0.12);
  color: #d9ffe8;
}

.stage-editor-modal {
  width: min(560px, calc(100vw - 32px));
}

.stage-line article.optional {
  opacity: 0.92;
}

.stage-line article.optional i b {
  background: linear-gradient(90deg, rgba(124, 255, 178, 0.65), rgba(106, 166, 255, 0.65));
}

.metric-strip {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  margin-top: 34px;
}

.metric-strip article {
  padding: 18px 20px;
}

.metric-strip article + article {
  border-left: 1px solid rgba(240, 240, 250, 0.1);
}

.metric-strip strong {
  display: block;
  margin: 10px 0 4px;
  font-size: 28px;
}

.stage-line {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 14px;
  margin-top: 28px;
}

.stage-line article {
  position: relative;
  min-height: 120px;
  padding: 18px;
  overflow: hidden;
  transition: transform 180ms ease, border-color 180ms ease, background 180ms ease, opacity 180ms ease;
}

.stage-line article::after {
  content: "";
  position: absolute;
  inset: auto 16px 14px auto;
  width: 54px;
  height: 54px;
  border: 1px solid rgba(240, 240, 250, 0.08);
  border-radius: 50%;
  pointer-events: none;
}

.stage-marker {
  position: absolute;
  top: 18px;
  right: 18px;
  width: 22px;
  height: 22px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: rgba(240, 240, 250, 0.06);
}

.stage-marker span {
  width: 9px;
  height: 9px;
  display: block;
  border-radius: 50%;
  background: rgba(240, 240, 250, 0.36);
}

.stage-line strong {
  display: block;
  margin: 8px 0 12px;
  font-size: 18px;
}

.stage-line i,
.task-card i,
.ability-bars i {
  display: block;
  height: 8px;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(240, 240, 250, 0.08);
}

.stage-line i b,
.task-card i b,
.ability-bars b {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #7cffb2, #6aa6ff);
}

.stage-line article.done,
.stage-line article.complete {
  border-color: rgba(124, 255, 178, 0.32);
  background:
    linear-gradient(135deg, rgba(124, 255, 178, 0.1), transparent 58%),
    rgba(8, 10, 12, 0.88);
}

.stage-line article.done .stage-marker,
.stage-line article.complete .stage-marker {
  background: rgba(124, 255, 178, 0.16);
}

.stage-line article.done .stage-marker span,
.stage-line article.complete .stage-marker span {
  background: #7cffb2;
  box-shadow: 0 0 18px rgba(124, 255, 178, 0.46);
}

.stage-line article.in-progress,
.stage-line article.current {
  border-color: rgba(106, 166, 255, 0.42);
  background:
    linear-gradient(135deg, rgba(106, 166, 255, 0.14), transparent 58%),
    rgba(8, 10, 12, 0.9);
}

.stage-line article.in-progress .stage-marker,
.stage-line article.current .stage-marker {
  background: rgba(106, 166, 255, 0.18);
}

.stage-line article.in-progress .stage-marker span,
.stage-line article.current .stage-marker span {
  background: #6aa6ff;
  box-shadow: 0 0 18px rgba(106, 166, 255, 0.5);
}

.stage-line article.pending,
.stage-line article.muted {
  opacity: 0.62;
  border-color: rgba(240, 240, 250, 0.08);
  background:
    repeating-linear-gradient(135deg, rgba(240, 240, 250, 0.025) 0 8px, transparent 8px 16px),
    rgba(8, 10, 12, 0.62);
}

.stage-line article.pending strong,
.stage-line article.muted strong {
  color: rgba(240, 240, 250, 0.58);
}

.stage-line article.pending i b,
.stage-line article.muted i b {
  background: rgba(240, 240, 250, 0.28);
}

.stage-line article.blocked {
  border-color: rgba(255, 138, 22, 0.4);
  background:
    linear-gradient(135deg, rgba(255, 138, 22, 0.12), transparent 58%),
    rgba(8, 10, 12, 0.88);
}

.role-banner {
  display: grid;
  grid-template-columns: 160px minmax(0, 1fr);
  gap: 8px 24px;
  margin-top: 24px;
  padding: 18px 20px;
}

.role-banner span {
  grid-row: span 2;
  color: #7cffb2;
  font-size: 12px;
  font-weight: 950;
  letter-spacing: 0.14em;
}

.role-banner.teacher span {
  color: #6aa6ff;
}

.permission-pills {
  grid-column: 2;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 6px;
}

.permission-pills b {
  padding: 6px 9px;
  border: 1px solid rgba(240, 240, 250, 0.12);
  border-radius: 6px;
  background: rgba(240, 240, 250, 0.05);
  color: rgba(240, 240, 250, 0.44);
  font-size: 11px;
}

.permission-pills b.active {
  border-color: rgba(124, 255, 178, 0.34);
  background: rgba(124, 255, 178, 0.1);
  color: #7cffb2;
}

.project-form {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 14px;
}

.project-form > label,
.member-picker,
.permission-picker {
  display: grid;
  gap: 8px;
}

.project-form > label > span,
.member-picker > span,
.permission-picker > span {
  color: rgba(240, 240, 250, 0.56);
  font-size: 12px;
  font-weight: 850;
}

.project-form > label:nth-of-type(2),
.member-picker,
.permission-picker,
.project-form button {
  grid-column: 1 / -1;
}

.check-grid,
.permission-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.check-card,
.permission-card {
  position: relative;
  padding: 12px 12px 12px 38px;
  border: 1px solid rgba(240, 240, 250, 0.12);
  border-radius: 8px;
  background: rgba(240, 240, 250, 0.045);
  cursor: pointer;
}

.check-card input,
.permission-card input {
  position: absolute;
  left: 12px;
  top: 16px;
  width: auto;
}

.check-card:has(input:checked),
.permission-card:has(input:checked) {
  border-color: rgba(124, 255, 178, 0.44);
  background: rgba(124, 255, 178, 0.09);
}

.check-card b,
.permission-card b {
  display: block;
  color: #f0f0fa;
  font-size: 14px;
}

.check-card small,
.permission-card small {
  display: block;
  margin-top: 4px;
  color: rgba(240, 240, 250, 0.52);
  line-height: 1.5;
}

.project-form button:disabled {
  cursor: not-allowed;
  opacity: 0.54;
}

.project-modal-overlay,
.task-modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 6200;
  display: grid;
  place-items: center;
  padding: 32px;
  background: rgba(0, 0, 0, 0.72);
  backdrop-filter: blur(18px);
}

.project-modal,
.task-modal {
  width: min(1160px, 100%);
  max-height: min(88vh, 860px);
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  overflow: hidden;
  border: 1px solid rgba(240, 240, 250, 0.16);
  border-radius: 10px;
  background:
    radial-gradient(circle at 12% 10%, rgba(124, 255, 178, 0.12), transparent 30%),
    radial-gradient(circle at 88% 0%, rgba(106, 166, 255, 0.12), transparent 28%),
    rgba(8, 10, 12, 0.96);
  box-shadow: 0 34px 120px rgba(0, 0, 0, 0.56);
}

.task-modal {
  width: min(760px, 100%);
}

.project-modal-head,
.task-modal-head {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  padding: 24px 28px 20px;
  border-bottom: 1px solid rgba(240, 240, 250, 0.1);
}

.project-modal-head h2,
.task-modal-head h2 {
  margin: 8px 0 6px;
  font-size: 30px;
}

.project-modal-head p,
.task-modal-head p {
  margin: 0;
  color: rgba(240, 240, 250, 0.58);
  line-height: 1.7;
}

.close-btn,
.secondary-action {
  min-height: 36px;
  padding: 0 14px;
  border: 1px solid rgba(240, 240, 250, 0.14);
  border-radius: 8px;
  background: rgba(240, 240, 250, 0.05);
  color: rgba(240, 240, 250, 0.78);
  cursor: pointer;
  font-weight: 850;
}

.project-modal-body {
  min-height: 0;
  display: grid;
  grid-template-columns: 0.85fr 1.15fr;
  gap: 22px;
  padding: 24px 28px 28px;
  overflow: auto;
}

.project-details,
.member-console {
  min-width: 0;
  display: grid;
  align-content: start;
  gap: 14px;
}

.project-details > label,
.member-search,
.filter-grid label {
  display: grid;
  gap: 8px;
}

.project-details span,
.filter-grid span {
  color: rgba(240, 240, 250, 0.56);
  font-size: 12px;
  font-weight: 850;
}

.selected-strip,
.member-console {
  border: 1px solid rgba(240, 240, 250, 0.12);
  border-radius: 8px;
  background: rgba(240, 240, 250, 0.045);
}

.selected-strip {
  display: grid;
  grid-template-columns: auto auto minmax(0, 1fr);
  align-items: center;
  gap: 10px;
  padding: 12px;
}

.selected-strip strong {
  color: #7cffb2;
}

.selected-strip div {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.selected-strip button {
  border: 1px solid rgba(124, 255, 178, 0.24);
  border-radius: 999px;
  background: rgba(124, 255, 178, 0.08);
  color: rgba(240, 240, 250, 0.82);
  cursor: pointer;
}

.modal-section {
  padding-top: 4px;
}

.add-position {
  display: grid;
  gap: 8px;
}

.add-position > span {
  font-size: 13px;
  font-weight: 600;
  opacity: 0.85;
}

.add-position-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.add-position-row input {
  flex: 1 1 160px;
  min-width: 120px;
}

.add-position-row button {
  flex: 0 0 auto;
  padding: 0 16px;
  white-space: nowrap;
}

.add-position-row button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.add-position-hint {
  margin: 0;
  font-size: 12px;
  opacity: 0.6;
}

.member-position-editor {
  margin-top: 16px;
  padding: 16px;
  display: grid;
  gap: 14px;
  border: 1px solid rgba(124, 255, 178, 0.22);
  border-radius: 12px;
  background:
    linear-gradient(135deg, rgba(124, 255, 178, 0.08), transparent 62%),
    rgba(8, 10, 12, 0.55);
}

.mpe-head {
  display: grid;
  gap: 8px;
}

.mpe-head-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.mpe-avatar {
  flex: 0 0 auto;
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: rgba(124, 255, 178, 0.16);
  color: #7cffb2;
  font-weight: 950;
}

.mpe-head h3 {
  margin: 0;
  font-size: 16px;
  color: #f0f0fa;
}

.mpe-current {
  display: inline-block;
  margin-top: 5px;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  color: #7cffb2;
  background: rgba(124, 255, 178, 0.12);
  border: 1px solid rgba(124, 255, 178, 0.28);
}

.mpe-field {
  display: grid;
  gap: 6px;
}

.mpe-field > span {
  font-size: 12px;
  font-weight: 600;
  color: rgba(240, 240, 250, 0.6);
}

.member-position-editor select,
.member-position-editor textarea,
.member-position-editor input {
  width: 100%;
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid rgba(240, 240, 250, 0.14);
  background: rgba(240, 240, 250, 0.04);
  color: #f0f0fa;
  font-size: 13px;
  font-family: inherit;
}

.member-position-editor textarea {
  resize: vertical;
  line-height: 1.6;
}

.member-position-editor select:focus,
.member-position-editor textarea:focus,
.member-position-editor input:focus {
  outline: none;
  border-color: rgba(124, 255, 178, 0.5);
  background: rgba(124, 255, 178, 0.06);
}

.add-position.inline {
  display: grid;
  gap: 8px;
  padding: 12px;
  border-radius: 10px;
  border: 1px dashed rgba(240, 240, 250, 0.16);
  background: rgba(240, 240, 250, 0.02);
}

.add-position-label {
  font-size: 11px;
  color: rgba(240, 240, 250, 0.5);
}

.add-position-row button.ghost {
  flex: 0 0 auto;
  min-height: 38px;
  padding: 0 14px;
  border-radius: 8px;
  border: 1px solid rgba(124, 255, 178, 0.4);
  background: rgba(124, 255, 178, 0.08);
  color: #7cffb2;
  font-weight: 700;
  white-space: nowrap;
  cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease;
}

.add-position-row button.ghost:hover:not(:disabled) {
  background: rgba(124, 255, 178, 0.16);
  border-color: rgba(124, 255, 178, 0.6);
}

.add-position-row button.ghost:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.mpe-save {
  min-height: 42px;
  border: 1px solid rgba(124, 255, 178, 0.5);
  border-radius: 9px;
  background: linear-gradient(135deg, rgba(124, 255, 178, 0.92), rgba(106, 166, 255, 0.85));
  color: #04130b;
  font-weight: 900;
  letter-spacing: 0.02em;
  cursor: pointer;
  transition: filter 0.15s ease, transform 0.05s ease;
}

.mpe-save:hover:not(:disabled) {
  filter: brightness(1.08);
}

.mpe-save:active:not(:disabled) {
  transform: translateY(1px);
}

.mpe-save:disabled {
  cursor: not-allowed;
  background: rgba(240, 240, 250, 0.08);
  color: rgba(240, 240, 250, 0.5);
  border-color: rgba(240, 240, 250, 0.14);
}

.member-console {
  padding: 16px;
}

.member-console-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.member-console-head h3 {
  margin: 6px 0 0;
  font-size: 22px;
}

.member-console-head button {
  padding: 0 14px;
}

.filter-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 10px;
}

.member-pool {
  display: grid;
  gap: 10px;
  max-height: 360px;
  overflow: auto;
  padding-right: 4px;
}

.member-row {
  display: grid;
  grid-template-columns: auto minmax(96px, 0.8fr) auto minmax(0, 1.4fr) auto;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border: 1px solid rgba(240, 240, 250, 0.1);
  border-radius: 8px;
  background: rgba(10, 12, 14, 0.78);
  cursor: pointer;
}

.member-row:has(input:checked) {
  border-color: rgba(124, 255, 178, 0.42);
  background: rgba(124, 255, 178, 0.08);
}

.member-row b {
  color: #f0f0fa;
}

.member-row span,
.member-row em {
  color: rgba(124, 255, 178, 0.74);
  font-size: 12px;
  font-style: normal;
  font-weight: 850;
}

.member-row small {
  min-width: 0;
  color: rgba(240, 240, 250, 0.56);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.project-modal-actions {
  grid-column: 1 / -1;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding-top: 4px;
}

.project-modal-actions button {
  min-width: 116px;
}

.project-modal-actions button:disabled {
  cursor: not-allowed;
  opacity: 0.54;
}

.task-modal-form {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  padding: 24px 28px 28px;
}

.task-modal-form label {
  display: grid;
  gap: 8px;
}

.task-modal-form label span {
  color: rgba(240, 240, 250, 0.58);
  font-size: 12px;
  font-weight: 850;
}

.task-modal-wide,
.task-modal-actions {
  grid-column: 1 / -1;
}

.task-modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.task-modal-actions button {
  min-width: 120px;
  min-height: 40px;
  border: 1px solid rgba(124, 255, 178, 0.36);
  border-radius: 8px;
  background: rgba(124, 255, 178, 0.1);
  color: #f0f0fa;
  cursor: pointer;
  font-weight: 850;
}

.task-modal-actions button:hover {
  background: rgba(124, 255, 178, 0.18);
  border-color: rgba(124, 255, 178, 0.62);
}

.task-modal-overlay {
  background: rgba(23, 18, 15, 0.28);
  backdrop-filter: blur(14px);
}

.task-modal {
  width: min(860px, calc(100vw - 36px));
  border: 1px solid rgba(234, 223, 215, 0.9);
  border-radius: 18px;
  background: #fffdfb;
  box-shadow: 0 30px 90px rgba(49, 35, 22, 0.18);
}

.task-modal-head {
  align-items: flex-start;
  padding: 16px 18px 10px;
  border-bottom: 1px solid #eee4dc;
}

.task-modal-head .kicker {
  color: #f25b0c;
  font-size: 12px;
  font-weight: 850;
  letter-spacing: 0.02em;
}

.task-modal-head h2 {
  display: none;
}

.task-modal-head p {
  display: none;
}

.task-modal .close-btn {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  min-height: 32px;
  padding: 0;
  border: 0;
  border-radius: 9px;
  background: #f7efe8;
  color: #8a8179;
}

.task-modal .close-btn:hover {
  background: #fff1e8;
  color: #f25b0c;
}

.task-modal .close-btn svg {
  width: 15px;
  height: 15px;
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-width: 2.2;
}

.task-modal-form {
  grid-template-columns: 1fr;
  gap: 0;
  padding: 0 18px 16px;
  background: #fffdfb;
}

.task-modal-form label {
  gap: 7px;
}

.task-modal-form label span {
  color: #7f766f;
  font-size: 12px;
  font-weight: 850;
}

.task-title-field > span,
.task-modal-wide > span {
  display: none;
}

.task-title-field {
  padding: 10px 0 6px;
  border-bottom: 1px solid #eee4dc;
}

.task-modal-form input,
.task-modal-form select,
.task-modal-form textarea {
  width: 100%;
  border: 1px solid #eadfd7;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.82);
  color: #17120f;
  outline: none;
  box-shadow: none;
}

.task-title-field input {
  height: 48px;
  padding: 0;
  border: 0;
  border-color: transparent;
  border-radius: 0;
  background: transparent;
  color: #17120f;
  font-size: 22px;
  font-weight: 900;
  letter-spacing: -0.035em;
}

.task-title-field input::placeholder {
  color: #8f857d;
  font-weight: 850;
}

.task-title-field input:focus {
  box-shadow: none;
}

.task-modal-form input,
.task-modal-form select {
  height: 38px;
  padding: 0 11px;
}

.task-modal-form textarea {
  min-height: 128px;
  padding: 2px 0 14px;
  border: 0;
  border-radius: 0;
  border-bottom: 1px solid #eee4dc;
  background: transparent;
  resize: vertical;
}

.task-modal-form textarea::placeholder {
  color: #9a9088;
}

.task-type-picker,
.task-time-slot-picker {
  display: grid;
  gap: 10px;
}

.task-create-form {
  gap: 14px;
}

.task-create-intro {
  border: 1px solid #f0ded4;
  border-radius: 18px;
  padding: 12px 14px;
  background: #fffaf7;
}

.task-create-intro div {
  display: grid;
  gap: 3px;
}

.task-create-intro strong {
  color: #2c2925;
  font-size: 15px;
}

.task-create-intro span {
  color: #8b8178;
  font-size: 13px;
  font-weight: 700;
}

.task-create-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(260px, 0.95fr);
  gap: 14px;
}

.task-create-block {
  border: 1px solid #f0ded4;
  border-radius: 18px;
  padding: 14px;
  background: rgba(255, 250, 247, 0.72);
}

.task-create-block header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  color: #2c2925;
  font-size: 14px;
  font-weight: 900;
}

.task-create-block header b {
  width: 22px;
  height: 22px;
  border-radius: 999px;
  display: grid;
  place-items: center;
  color: #fff;
  background: #ea580c;
  font-size: 12px;
}

.task-create-content textarea {
  min-height: 112px;
}

.task-type-picker > div,
.task-time-slot-picker > div {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.task-type-picker > div {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.task-type-picker button,
.task-time-slot-picker button {
  border: 1px solid #eadfd8;
  border-radius: 999px;
  padding: 8px 12px;
  color: #5f574f;
  background: #fffaf6;
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
}

.task-type-picker button {
  border-radius: 13px;
  text-align: center;
}

.task-time-slot-picker button {
  border-radius: 14px;
  min-width: 92px;
  flex: 1 1 0;
  display: grid;
  gap: 2px;
  text-align: left;
}

.task-time-slot-picker button small {
  color: #9a9188;
  font-size: 11px;
  font-weight: 700;
}

.task-type-picker button.active,
.task-time-slot-picker button.active {
  border-color: rgba(234, 88, 12, 0.42);
  color: #ea580c;
  background: #fff1e8;
}

.task-type-picker input {
  width: 100%;
  border: 1px solid #eadfd8;
  border-radius: 14px;
  padding: 10px 12px;
  color: #2c2925;
  background: #fffaf6;
  font-size: 14px;
  outline: none;
}

.task-create-assign {
  padding-bottom: 6px;
}

.task-attribute-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 12px 0 14px;
  border: 0;
  border-bottom: 1px solid #eee4dc;
  background: transparent;
}

.task-attribute-grid label {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  min-width: 0;
  min-height: 32px;
  padding: 0 9px;
  border: 1px solid #eadfd7;
  border-radius: 999px;
  background: rgba(255, 250, 247, 0.86);
}

.task-assignee-picker {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 32px;
  padding: 0 8px;
  border: 1px solid #eadfd7;
  border-radius: 999px;
  background: rgba(255, 250, 247, 0.86);
}

.task-assignee-picker > span {
  flex: 0 0 auto;
  color: #9a9088;
  font-size: 12px;
  font-weight: 750;
}

.task-assignee-picker > div {
  display: flex;
  align-items: center;
  gap: 4px;
  max-width: 360px;
  overflow-x: auto;
  scrollbar-width: none;
}

.task-assignee-picker > div::-webkit-scrollbar {
  display: none;
}

.task-assignee-picker button {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 26px;
  padding: 0 7px 0 3px;
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: #6f665e;
  font-size: 12px;
  font-weight: 800;
  white-space: nowrap;
}

.task-assignee-picker button.active {
  background: #fff1e8;
  color: #f25b0c;
}

.task-assignee-picker button b {
  display: grid;
  place-items: center;
  width: 20px;
  height: 20px;
  border-radius: 999px;
  background: #17120f;
  color: #fff;
  font-size: 10px;
}

.task-assignee-picker button.active b {
  background: #f25b0c;
}

.task-attribute-grid label:focus-within {
  border-color: rgba(242, 91, 12, 0.32);
  background: #fff6ef;
}

.task-attribute-grid label span {
  flex: 0 0 auto;
  color: #9a9088;
  font-size: 12px;
  font-weight: 750;
}

.task-attribute-grid select,
.task-attribute-grid input {
  width: auto;
  max-width: 170px;
  height: 30px;
  padding: 0;
  border: 0;
  border-radius: 0;
  background: transparent;
  font-size: 13px;
  font-weight: 750;
}

.task-attribute-grid select {
  appearance: none;
  padding-right: 14px;
  background:
    linear-gradient(45deg, transparent 50%, #8a8179 50%) right 5px center / 5px 5px no-repeat,
    linear-gradient(135deg, #8a8179 50%, transparent 50%) right 1px center / 5px 5px no-repeat;
}

.task-attribute-grid input[type="datetime-local"] {
  min-width: 128px;
  color: #17120f;
}

.task-attribute-grid input[type="datetime-local"]::-webkit-calendar-picker-indicator {
  opacity: 0.68;
  cursor: pointer;
}

.date-attribute {
  min-width: 188px;
}

.task-attribute-grid select:focus,
.task-attribute-grid input:focus {
  box-shadow: none;
}

.task-modal-form input:focus,
.task-modal-form select:focus,
.task-modal-form textarea:focus {
  border-color: rgba(242, 91, 12, 0.45);
  box-shadow: 0 0 0 3px rgba(242, 91, 12, 0.08);
}

.task-modal-actions {
  align-items: center;
  padding-top: 12px;
}

.task-modal-actions button {
  min-width: 108px;
  min-height: 38px;
  border: 0;
  border-radius: 10px;
  background: #f25b0c;
  color: #fff;
  box-shadow: none;
}

.task-modal-actions button:hover {
  border-color: transparent;
  background: #e24f06;
}

.task-modal-actions .secondary-action {
  background: #f7efe8;
  color: #6f665e;
}

.task-modal-actions .secondary-action:hover {
  background: #fff1e8;
  color: #f25b0c;
}

.main-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 390px;
  gap: 22px;
  margin-top: 36px;
}

.work-tier {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 380px;
  gap: 22px;
  margin-top: 36px;
  align-items: start;
}

.workbench,
.work-side,
.side-stack {
  display: grid;
  align-content: start;
  gap: 18px;
}

.panel {
  padding: 22px;
}

.panel-head {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 18px;
}

.panel-head h2 {
  margin: 8px 0 0;
  font-size: 24px;
}

.panel-head.compact h2 {
  font-size: 20px;
}

.composer,
.bind-form {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 18px;
  padding: 14px;
  border: 1px solid rgba(124, 255, 178, 0.18);
  border-radius: 8px;
  background: rgba(124, 255, 178, 0.04);
}

.composer textarea,
.composer button {
  grid-column: 1 / -1;
}

input,
select,
textarea {
  width: 100%;
  border: 1px solid rgba(240, 240, 250, 0.14);
  border-radius: 8px;
  background: rgba(240, 240, 250, 0.06);
  color: #f0f0fa;
  outline: none;
  padding: 10px 12px;
}

textarea {
  resize: vertical;
}

.workbench-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 0 0 16px;
}

.workbench-tabs button {
  display: inline-flex;
  min-height: 34px;
  align-items: center;
  gap: 8px;
  border: 1px solid rgba(240, 240, 250, 0.1);
  border-radius: 8px;
  background: rgba(240, 240, 250, 0.045);
  color: rgba(240, 240, 250, 0.58);
  cursor: pointer;
  font-weight: 850;
  padding: 0 10px;
}

.workbench-tabs button.active {
  border-color: rgba(124, 255, 178, 0.38);
  background: rgba(124, 255, 178, 0.1);
  color: #dfffee;
}

.workbench-tabs b {
  min-width: 22px;
  padding: 3px 7px;
  border-radius: 999px;
  background: rgba(240, 240, 250, 0.08);
  color: rgba(240, 240, 250, 0.74);
  text-align: center;
  font-size: 11px;
}

.workbench-tabs button.active b {
  background: rgba(124, 255, 178, 0.16);
  color: #7cffb2;
}

.task-pane,
.task-management-pane {
  display: grid;
  gap: 14px;
}

.task-title-switch {
  display: inline-grid;
  grid-template-columns: repeat(2, minmax(170px, 1fr));
  gap: 6px;
  align-items: stretch;
  padding: 6px;
  border: 1px solid rgba(240, 240, 250, 0.08);
  border-radius: 8px;
  background:
    linear-gradient(135deg, rgba(124, 255, 178, 0.055), rgba(106, 166, 255, 0.035) 54%, transparent),
    rgba(240, 240, 250, 0.035);
}

.task-title-switch button {
  position: relative;
  display: grid;
  min-width: 0;
  justify-items: start;
  gap: 4px;
  border: 1px solid transparent;
  border-radius: 7px;
  background: transparent;
  color: rgba(240, 240, 250, 0.48);
  cursor: pointer;
  padding: 12px 18px 14px;
  text-align: left;
  transition:
    background 180ms ease,
    border-color 180ms ease,
    color 180ms ease,
    transform 180ms ease;
}

.task-title-switch button span {
  color: rgba(240, 240, 250, 0.38);
  font-size: 10px;
  font-weight: 850;
  letter-spacing: 0.18em;
}

.task-title-switch button strong {
  color: rgba(240, 240, 250, 0.56);
  font-size: 22px;
  line-height: 1.15;
}

.task-title-switch button small {
  color: rgba(240, 240, 250, 0.46);
  font-size: 12px;
  font-weight: 760;
}

.task-title-switch button:hover {
  background: rgba(240, 240, 250, 0.04);
}

.task-title-switch button.active {
  border-color: rgba(124, 255, 178, 0.34);
  background:
    linear-gradient(135deg, rgba(124, 255, 178, 0.15), rgba(124, 255, 178, 0.055)),
    rgba(6, 12, 10, 0.72);
  box-shadow:
    inset 0 -2px 0 rgba(124, 255, 178, 0.55),
    0 12px 30px rgba(124, 255, 178, 0.06);
}

.task-title-switch button.active span {
  color: #68d391;
}

.task-title-switch button.active strong {
  color: #f0f0fa;
}

.task-title-switch button.active small {
  color: rgba(223, 255, 238, 0.72);
}

.task-title-switch.single {
  grid-template-columns: minmax(180px, 1fr);
  padding: 0;
  border-color: transparent;
  background: transparent;
}

.task-title-switch.single button {
  cursor: default;
  padding: 0;
}

.task-title-switch.single button.active {
  border-color: transparent;
  background: transparent;
  box-shadow: none;
}

.material-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  align-items: start;
  gap: 14px;
}

.task-grid,
.material-list {
  display: grid;
  max-height: min(1180px, calc(100vh - 360px));
  min-height: 520px;
  overflow-y: auto;
  padding-right: 6px;
  scrollbar-width: thin;
  scrollbar-color: rgba(124, 255, 178, 0.42) rgba(240, 240, 250, 0.06);
}

.task-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  align-items: start;
  align-content: start;
  gap: 12px;
}

.task-grid::-webkit-scrollbar,
.material-list::-webkit-scrollbar {
  width: 8px;
}

.task-grid::-webkit-scrollbar-track,
.material-list::-webkit-scrollbar-track {
  background: rgba(240, 240, 250, 0.06);
  border-radius: 999px;
}

.task-grid::-webkit-scrollbar-thumb,
.material-list::-webkit-scrollbar-thumb {
  background: rgba(124, 255, 178, 0.34);
  border-radius: 999px;
}

.task-card,
.material-card,
.review-card {
  position: relative;
  padding: 18px;
  overflow: hidden;
  transition: transform 180ms ease, border-color 180ms ease, background 180ms ease, opacity 180ms ease;
}

.task-card::after,
.material-card::after {
  content: "";
  position: absolute;
  right: -34px;
  bottom: -56px;
  width: 112px;
  height: 112px;
  border: 1px solid rgba(240, 240, 250, 0.06);
  border-radius: 50%;
  pointer-events: none;
}

.task-top,
.task-meta,
.review-actions,
.material-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.task-top b,
.issue-list b,
.material-card small b {
  padding: 5px 8px;
  border-radius: 6px;
  background: rgba(240, 240, 250, 0.08);
  color: rgba(240, 240, 250, 0.64);
  font-size: 11px;
  white-space: nowrap;
}

.task-card h3,
.material-card h3,
.review-card h3 {
  margin: 14px 0 7px;
  font-size: 20px;
}

.task-card {
  display: block;
  min-width: 0;
  overflow: visible;
  isolation: isolate;
}

.task-card > * {
  position: relative;
  z-index: 1;
}

.task-card > p {
  min-height: 0;
  margin: 0 0 10px;
  line-height: 1.55;
}

.task-grid > .empty-state {
  grid-column: 1 / -1;
}

.task-meta small,
.material-card small {
  display: flex;
  align-items: center;
  gap: 8px;
  color: rgba(240, 240, 250, 0.54);
  font-size: 12px;
}

.task-card.dormant,
.material-card.dormant {
  opacity: 0.72;
  background:
    repeating-linear-gradient(135deg, rgba(240, 240, 250, 0.018) 0 8px, transparent 8px 16px),
    rgba(8, 10, 12, 0.72);
}

.task-card.dormant h3,
.material-card.dormant h3 {
  color: rgba(240, 240, 250, 0.7);
}

.task-card.active {
  border-color: rgba(106, 166, 255, 0.34);
  background:
    linear-gradient(135deg, rgba(106, 166, 255, 0.09), transparent 58%),
    #080a0c;
}

.task-card.review,
.material-card.review {
  border-color: rgba(106, 166, 255, 0.42);
  background:
    linear-gradient(135deg, rgba(106, 166, 255, 0.13), transparent 58%),
    #080a0c;
}

.task-card.warning,
.material-card.warning {
  border-color: rgba(255, 138, 22, 0.44);
  background:
    linear-gradient(135deg, rgba(255, 138, 22, 0.12), transparent 58%),
    #080a0c;
}

.task-card.complete,
.material-card.complete {
  border-color: rgba(124, 255, 178, 0.34);
  background:
    linear-gradient(135deg, rgba(124, 255, 178, 0.1), transparent 58%),
    #080a0c;
}

.task-top b.todo,
.material-card b.draft {
  color: rgba(240, 240, 250, 0.52);
  background: rgba(240, 240, 250, 0.06);
}

.task-top b.in-progress {
  color: #9ec4ff;
  background: rgba(106, 166, 255, 0.14);
}

.task-top b.reviewing,
.material-card b.pending-review {
  color: #9ec4ff;
  background: rgba(106, 166, 255, 0.16);
}

.task-top b.changes-requested,
.material-card b.changes-requested,
.material-card b.rejected {
  color: #ffb35b;
  background: rgba(255, 138, 22, 0.16);
}

.task-top b.done,
.material-card b.approved {
  color: #7cffb2;
  background: rgba(124, 255, 178, 0.14);
}

.delivery-strip {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 6px 12px;
  margin-top: 12px;
  padding: 10px 12px;
  border: 1px solid rgba(240, 240, 250, 0.1);
  border-radius: 8px;
  background: rgba(240, 240, 250, 0.035);
}

.delivery-strip > span,
.submission-file span,
.review-title span,
.history-head h3,
.history-card small {
  color: rgba(240, 240, 250, 0.5);
  font-size: 11px;
  font-weight: 850;
  letter-spacing: 0.1em;
}

.delivery-strip strong {
  color: #f0f0fa;
  font-size: 14px;
}

.delivery-strip small {
  color: rgba(240, 240, 250, 0.54);
  font-size: 12px;
}

.delivery-strip .attachment-actions {
  grid-row: 1 / span 3;
  grid-column: 2;
  align-self: center;
}

.submit-box,
.material-actions {
  display: grid;
  gap: 10px;
  margin-top: 12px;
}

.submit-box {
  grid-template-columns: minmax(0, 1fr) 148px;
}

.submit-box textarea {
  grid-column: 1 / -1;
  min-height: 64px;
  resize: vertical;
}

.upload-zone {
  display: grid;
  gap: 5px;
  min-height: 64px;
  align-content: center;
  padding: 10px 12px;
  border: 1px dashed rgba(124, 255, 178, 0.34);
  border-radius: 8px;
  background:
    linear-gradient(135deg, rgba(124, 255, 178, 0.08), transparent 68%),
    rgba(124, 255, 178, 0.035);
  cursor: pointer;
}

.upload-zone input {
  display: none;
}

.upload-zone span {
  color: #dfffee;
  font-weight: 850;
}

.upload-zone small {
  color: rgba(240, 240, 250, 0.52);
}

.submit-box button:disabled {
  cursor: progress;
  opacity: 0.62;
}

.submit-box > button {
  min-height: 64px;
}

.submit-lock {
  margin-top: 12px;
  padding: 10px 12px;
  border: 1px solid rgba(106, 166, 255, 0.18);
  border-radius: 8px;
  background: rgba(106, 166, 255, 0.08);
  color: rgba(214, 228, 255, 0.78);
  font-size: 12px;
  font-weight: 750;
}

.material-overview {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 14px;
}

.material-overview article {
  padding: 12px;
  border: 1px solid rgba(240, 240, 250, 0.09);
  border-radius: 8px;
  background: rgba(240, 240, 250, 0.035);
}

.material-overview span,
.material-type span {
  color: rgba(240, 240, 250, 0.48);
  font-size: 11px;
  font-weight: 850;
  letter-spacing: 0.1em;
}

.material-overview strong {
  display: block;
  margin-top: 8px;
  color: #f0f0fa;
  font-size: 24px;
}

.material-tabs {
  margin-bottom: 12px;
}

.material-list {
  display: grid;
  gap: 10px;
}

.material-row {
  display: grid;
  grid-template-columns: 120px minmax(0, 1fr) minmax(280px, 0.9fr);
  align-items: center;
  gap: 16px;
  padding: 14px;
  border: 1px solid rgba(240, 240, 250, 0.1);
  border-radius: 8px;
  background: rgba(8, 10, 12, 0.78);
  transition: border-color 180ms ease, background 180ms ease, opacity 180ms ease;
}

.delivery-row {
  grid-template-columns: 116px minmax(0, 1fr) auto;
  min-height: 104px;
}

.material-row.review,
.material-row.pending-review {
  border-color: rgba(106, 166, 255, 0.3);
  background:
    linear-gradient(135deg, rgba(106, 166, 255, 0.08), transparent 68%),
    rgba(8, 10, 12, 0.86);
}

.material-row.warning,
.material-row.changes-requested,
.material-row.rejected {
  border-color: rgba(255, 138, 22, 0.36);
  background:
    linear-gradient(135deg, rgba(255, 138, 22, 0.09), transparent 68%),
    rgba(8, 10, 12, 0.86);
}

.material-row.complete,
.material-row.approved {
  border-color: rgba(124, 255, 178, 0.26);
  background:
    linear-gradient(135deg, rgba(124, 255, 178, 0.07), transparent 68%),
    rgba(8, 10, 12, 0.84);
}

.material-row.dormant,
.material-row.draft {
  opacity: 0.74;
  background:
    repeating-linear-gradient(135deg, rgba(240, 240, 250, 0.018) 0 8px, transparent 8px 16px),
    rgba(8, 10, 12, 0.68);
}

.material-type {
  display: grid;
  gap: 10px;
}

.material-type b {
  width: max-content;
  max-width: 100%;
  padding: 5px 8px;
  border-radius: 6px;
  background: rgba(240, 240, 250, 0.08);
  color: rgba(240, 240, 250, 0.62);
  font-size: 11px;
  white-space: nowrap;
}

.material-type b.pending-review {
  color: #9ec4ff;
  background: rgba(106, 166, 255, 0.16);
}

.material-type b.changes-requested,
.material-type b.rejected {
  color: #ffb35b;
  background: rgba(255, 138, 22, 0.16);
}

.material-type b.approved {
  color: #7cffb2;
  background: rgba(124, 255, 178, 0.14);
}

.material-main h3 {
  margin: 0 0 6px;
  font-size: 18px;
}

.material-main p {
  margin: 0;
  color: rgba(240, 240, 250, 0.62);
  line-height: 1.6;
}

.material-main small {
  display: block;
  margin-top: 8px;
  color: rgba(240, 240, 250, 0.46);
  font-size: 12px;
}

.material-tools {
  display: grid;
  justify-items: end;
  gap: 10px;
}

.delivery-row .material-main h3 {
  margin-bottom: 5px;
}

.delivery-row .material-main p {
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.review-open-btn {
  border-color: rgba(240, 75, 24, 0.22) !important;
  background: #fff1e8 !important;
  color: var(--workspace-orange-700, #d94312) !important;
}

.review-dialog {
  width: min(760px, 100%);
}

.review-dialog-body {
  display: grid;
  grid-template-columns: minmax(0, 0.95fr) minmax(260px, 1fr);
  gap: 16px;
  padding: 16px;
}

.review-dialog-file,
.review-dialog-comment {
  display: grid;
  align-content: start;
  gap: 10px;
  padding: 14px;
  border: 1px solid rgba(240, 222, 213, 0.82);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.74);
}

.review-dialog-file span,
.review-dialog-comment span {
  color: #8b93a1;
  font-size: 11px;
  font-weight: 850;
  letter-spacing: 0;
}

.review-dialog-file b {
  width: max-content;
  padding: 6px 10px;
  border-radius: 999px;
  background: #eff6ff;
  color: #2563eb;
  font-size: 12px;
  font-weight: 850;
}

.review-dialog-file b.changes-requested,
.review-dialog-file b.rejected {
  background: #fff7ed;
  color: #ea580c;
}

.review-dialog-file b.approved {
  background: #ecfdf5;
  color: #047857;
}

.review-dialog-file strong {
  color: #111827;
  word-break: break-word;
  font-size: 17px;
  line-height: 1.42;
}

.review-dialog-file small,
.review-dialog-file p {
  margin: 0;
  color: #697386;
  line-height: 1.7;
}

.review-dialog-comment textarea {
  min-height: 180px;
  border: 1px solid rgba(229, 214, 205, 0.92);
  border-radius: 12px;
  padding: 12px;
  color: #111827;
  background: rgba(255, 255, 255, 0.82);
  font: inherit;
  font-size: 13px;
  outline: none;
  resize: vertical;
}

.review-dialog-comment textarea:focus {
  border-color: rgba(240, 75, 24, 0.42);
  box-shadow: 0 0 0 3px rgba(240, 75, 24, 0.08);
}

.review-dialog-actions {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  padding: 0 16px 16px;
}

.review-dialog-actions button {
  min-height: 42px;
  border: 1px solid rgba(229, 214, 205, 0.86);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.76);
  color: #4b5563;
  cursor: pointer;
  font-weight: 850;
}

.review-dialog-actions button:first-child {
  border-color: rgba(16, 185, 129, 0.24);
  background: #ecfdf5;
  color: #047857;
}

.review-dialog-actions button:nth-child(2) {
  border-color: rgba(240, 75, 24, 0.24);
  background: #fff1e8;
  color: var(--workspace-orange-700, #d94312);
}

.review-dialog-actions button:last-child {
  border-color: rgba(239, 68, 68, 0.22);
  background: #fef2f2;
  color: #dc2626;
}

.material-review-line {
  display: grid;
  width: min(100%, 420px);
  grid-template-columns: minmax(0, 1fr) 64px 64px;
  gap: 8px;
}

.material-review-line button {
  min-height: 36px;
  border: 1px solid rgba(124, 255, 178, 0.34);
  border-radius: 8px;
  background: rgba(124, 255, 178, 0.1);
  color: #f0f0fa;
  cursor: pointer;
  font-weight: 850;
}

.material-inspector-overlay {
  position: fixed;
  inset: 0;
  z-index: 6200;
  display: grid;
  place-items: center;
  padding: 28px;
  background: rgba(20, 24, 32, 0.34);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
}

.material-inspector {
  width: min(860px, 100%);
  max-height: min(680px, calc(100vh - 56px));
  overflow: auto;
  border: 1px solid rgba(255, 255, 255, 0.86);
  border-radius: 22px;
  background:
    radial-gradient(circle at 100% 0%, rgba(255, 122, 69, 0.14), transparent 30%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.97), rgba(255, 249, 245, 0.94));
  box-shadow: 0 28px 80px rgba(84, 52, 32, 0.26);
}

.inspector-head {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 14px;
  padding: 20px 22px;
  border-bottom: 1px solid rgba(240, 222, 213, 0.78);
}

.inspector-head h3 {
  margin: 8px 0 0;
  color: #111827;
  font-size: 22px;
  line-height: 1.3;
  font-weight: 850;
}

.material-inspector .kicker {
  color: var(--workspace-orange-700, #d94312);
  font-size: 12px;
  font-weight: 850;
  letter-spacing: 0;
}

.inspector-head button {
  min-height: 34px;
  border: 1px solid rgba(229, 214, 205, 0.82);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.72);
  color: #4b5563;
  cursor: pointer;
  font-weight: 850;
  padding: 0 14px;
}

.inspector-body {
  display: grid;
  grid-template-columns: 180px minmax(0, 1fr);
  gap: 16px;
  padding: 18px 22px 22px;
}

.inspector-meta,
.inspector-file {
  display: grid;
  align-content: start;
  gap: 8px;
}

.inspector-meta span,
.inspector-file span {
  color: #8b93a1;
  font-size: 12px;
  font-weight: 850;
  letter-spacing: 0;
}

.inspector-meta b {
  width: max-content;
  padding: 6px 10px;
  border-radius: 999px;
  background: #f3f4f6;
  color: #4b5563;
  font-size: 12px;
  font-weight: 850;
}

.inspector-meta b.pending-review {
  color: #2563eb;
  background: #eff6ff;
}

.inspector-meta b.changes-requested,
.inspector-meta b.rejected {
  color: #ea580c;
  background: #fff7ed;
}

.inspector-meta b.approved {
  color: #047857;
  background: #ecfdf5;
}

.inspector-meta small,
.inspector-file small {
  color: #697386;
  line-height: 1.6;
}

.inspector-body p {
  margin: 0;
  color: #4b5563;
  line-height: 1.8;
}

.inspector-file {
  grid-column: 1 / -1;
  padding: 12px;
  border: 1px solid rgba(240, 222, 213, 0.82);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.78);
}

.inspector-file strong {
  color: #111827;
  word-break: break-word;
  font-size: 17px;
  line-height: 1.45;
}

.inspector-file small {
  word-break: break-word;
}

.review-list,
.issue-list,
.member-list,
.evidence-list {
  display: grid;
  gap: 12px;
}

.review-card {
  display: grid;
  gap: 12px;
  border-color: rgba(106, 166, 255, 0.3);
  background:
    linear-gradient(135deg, rgba(106, 166, 255, 0.11), transparent 60%),
    rgba(8, 10, 12, 0.9);
}

.review-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.review-title b {
  color: rgba(240, 240, 250, 0.54);
  font-size: 12px;
  font-weight: 700;
}

.review-card p {
  color: rgba(240, 240, 250, 0.72);
}

.submission-file,
.history-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 12px;
  border: 1px solid rgba(124, 255, 178, 0.18);
  border-radius: 8px;
  background: rgba(124, 255, 178, 0.055);
}

.submission-file strong,
.history-card strong {
  display: block;
  margin: 4px 0;
  color: #f0f0fa;
}

.submission-file small {
  color: rgba(240, 240, 250, 0.56);
}

.attachment-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}

.attachment-actions button {
  min-height: 32px;
  padding: 0 10px;
  border: 1px solid rgba(229, 214, 205, 0.86);
  border-radius: 11px;
  color: #4b5563;
  background: rgba(255, 255, 255, 0.78);
  cursor: pointer;
  font-size: 12px;
  font-weight: 820;
}

.attachment-actions button:first-child {
  border-color: rgba(37, 99, 235, 0.2);
  color: #2563eb;
  background: #eff6ff;
}

.attachment-actions .review-open-btn {
  border-color: rgba(240, 75, 24, 0.22) !important;
  color: var(--workspace-orange-700, #d94312) !important;
  background: #fff1e8 !important;
}

.attachment-actions button:disabled {
  cursor: not-allowed;
  opacity: 0.42;
}

.compact-actions {
  justify-content: flex-start;
}

.submission-history {
  margin-top: 20px;
  padding-top: 18px;
  border-top: 1px solid rgba(240, 240, 250, 0.1);
}

.history-head {
  margin-bottom: 12px;
}

.history-head h3 {
  margin: 6px 0 0;
  color: #f0f0fa;
  font-size: 18px;
  letter-spacing: 0;
}

.history-card + .history-card {
  margin-top: 10px;
}

.history-card b {
  display: inline-flex;
  margin-bottom: 7px;
  padding: 5px 8px;
  border-radius: 6px;
  background: rgba(240, 240, 250, 0.08);
  color: rgba(240, 240, 250, 0.62);
  font-size: 11px;
}

.history-card b.approved {
  color: #7cffb2;
  background: rgba(124, 255, 178, 0.14);
}

.history-card b.pending-review {
  color: #9ec4ff;
  background: rgba(106, 166, 255, 0.16);
}

.history-card b.changes-requested,
.history-card b.rejected {
  color: #ffb35b;
  background: rgba(255, 138, 22, 0.16);
}

.panel-note {
  color: rgba(240, 240, 250, 0.5);
  font-size: 12px;
}

.roadshow-review-layout {
  display: grid;
  grid-template-columns: minmax(250px, 0.72fr) minmax(0, 1.28fr);
  gap: 16px;
  align-items: stretch;
}

.roadshow-score-card {
  display: grid;
  gap: 16px;
  align-content: start;
  min-height: 0;
  padding: 18px;
  border: 1px solid rgba(124, 255, 178, 0.18);
  border-radius: 8px;
  background:
    linear-gradient(145deg, rgba(124, 255, 178, 0.09), transparent 58%),
    rgba(8, 10, 12, 0.82);
}

.roadshow-score-head {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 16px;
  align-items: start;
}

.roadshow-score-card h3 {
  margin: 8px 0;
  color: #f0f0fa;
  font-size: 22px;
  letter-spacing: 0;
}

.roadshow-score-card span,
.review-columns > article > span {
  color: rgba(124, 255, 178, 0.72);
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 0.12em;
}

.roadshow-score-card small,
.review-columns small,
.mini-empty {
  color: rgba(240, 240, 250, 0.56);
  line-height: 1.6;
}

.roadshow-score-value {
  display: grid;
  justify-items: end;
  gap: 8px;
}

.roadshow-score-value strong {
  color: #7cffb2;
  font-size: 48px;
  line-height: 0.95;
}

.roadshow-score-value b {
  width: max-content;
  padding: 6px 9px;
  border-radius: 999px;
  background: rgba(106, 166, 255, 0.12);
  color: #9ec4ff;
  font-size: 12px;
}

.roadshow-dimensions {
  display: grid;
  gap: 9px;
  padding: 12px;
  border: 1px solid rgba(240, 240, 250, 0.08);
  border-radius: 8px;
  background: rgba(240, 240, 250, 0.035);
}

.dimension-row {
  display: grid;
  grid-template-columns: 96px minmax(0, 1fr) 38px;
  align-items: center;
  gap: 8px;
}

.dimension-row > div {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.roadshow-dimensions em {
  color: rgba(240, 240, 250, 0.58);
  font-size: 12px;
  font-style: normal;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.roadshow-dimensions .dimension-row small {
  color: rgba(240, 240, 250, 0.38);
  font-size: 10px;
  line-height: 1;
}

.roadshow-dimensions .dimension-row strong {
  color: #f0f0fa;
  font-size: 12px;
  text-align: right;
}

.roadshow-dimensions i,
.ability-bars i {
  height: 7px;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(240, 240, 250, 0.08);
}

.roadshow-dimensions i b,
.ability-bars i b {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #7cffb2, #6aa6ff);
}

.muted-dimension {
  display: block !important;
  color: rgba(240, 240, 250, 0.44) !important;
}

.issue-list article,
.evidence-list article {
  display: grid;
  gap: 6px;
  padding: 14px;
  border: 1px solid rgba(240, 240, 250, 0.1);
  border-radius: 8px;
  background: rgba(240, 240, 250, 0.04);
}

.evidence-list article.muted {
  border-color: rgba(240, 240, 250, 0.08);
  background:
    repeating-linear-gradient(135deg, rgba(240, 240, 250, 0.018) 0 8px, transparent 8px 16px),
    rgba(240, 240, 250, 0.025);
}

.evidence-list article.muted span,
.evidence-list article.muted p {
  color: rgba(240, 240, 250, 0.46);
}

.issue-list article {
  grid-template-columns: 72px minmax(0, 1fr);
}

.issue-list article.warning {
  border-color: rgba(255, 138, 22, 0.36);
  background: rgba(255, 138, 22, 0.07);
}

.issue-list article.active {
  border-color: rgba(106, 166, 255, 0.34);
  background: rgba(106, 166, 255, 0.07);
}

.issue-list article.complete {
  border-color: rgba(124, 255, 178, 0.28);
  background: rgba(124, 255, 178, 0.06);
}

.issue-list b.open,
.issue-list b.high {
  color: #ffb35b;
  background: rgba(255, 138, 22, 0.16);
}

.issue-list b.in-progress,
.issue-list b.medium {
  color: #9ec4ff;
  background: rgba(106, 166, 255, 0.15);
}

.issue-list b.done,
.issue-list b.low {
  color: #7cffb2;
  background: rgba(124, 255, 178, 0.13);
}

.bind-form {
  grid-template-columns: 1fr 140px 120px;
  margin-top: 16px;
  margin-bottom: 0;
}

.review-console {
  display: grid;
  gap: 14px;
  min-width: 0;
}

.meeting-picker {
  display: grid;
  grid-template-columns: minmax(220px, 1fr) auto auto auto;
  align-items: end;
  gap: 12px;
  padding: 12px;
  border: 1px solid rgba(240, 240, 250, 0.1);
  border-radius: 8px;
  background: rgba(240, 240, 250, 0.035);
}

.team-ai-score-control {
  justify-self: end;
}

.upload-score-entry {
  min-height: 40px;
  border: 1px solid rgba(103, 183, 255, 0.28);
  border-radius: 8px;
  padding: 0 14px;
  background: rgba(103, 183, 255, 0.1);
  color: rgba(236, 246, 255, 0.92);
  font-weight: 900;
  cursor: pointer;
}

.upload-score-entry:hover {
  border-color: rgba(103, 183, 255, 0.48);
  background: rgba(103, 183, 255, 0.16);
}

.meeting-picker label {
  display: grid;
  gap: 8px;
}

.meeting-picker label span {
  color: rgba(240, 240, 250, 0.54);
  font-size: 12px;
  font-weight: 800;
}

.review-columns {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.review-columns article {
  display: grid;
  align-content: start;
  gap: 10px;
  max-height: 360px;
  overflow: auto;
  padding: 14px;
  border: 1px solid rgba(240, 240, 250, 0.1);
  border-radius: 8px;
  background: rgba(8, 10, 12, 0.74);
  scrollbar-width: thin;
  scrollbar-color: rgba(124, 255, 178, 0.44) rgba(240, 240, 250, 0.08);
}

.review-columns article div {
  display: grid;
  gap: 4px;
  padding: 10px;
  border-radius: 8px;
  background: rgba(240, 240, 250, 0.045);
}

.review-columns article div.high {
  background: rgba(255, 138, 22, 0.09);
  border: 1px solid rgba(255, 138, 22, 0.22);
}

.review-columns strong {
  color: #f0f0fa;
  font-size: 13px;
  letter-spacing: 0;
  line-height: 1.45;
}

.roadshow-memory-panel {
  display: grid;
  gap: 14px;
  margin-top: 16px;
  padding: 16px;
  border: 1px solid rgba(106, 166, 255, 0.16);
  border-radius: 8px;
  background:
    linear-gradient(135deg, rgba(106, 166, 255, 0.07), transparent 64%),
    rgba(8, 10, 12, 0.72);
}

.memory-head {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 18px;
}

.memory-head h3 {
  margin: 4px 0 0;
  color: #f0f0fa;
  font-size: 20px;
  letter-spacing: 0;
}

.memory-head small {
  max-width: 280px;
  color: rgba(240, 240, 250, 0.5);
  font-size: 12px;
  line-height: 1.6;
  text-align: right;
}

.memory-metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.memory-metrics article {
  display: grid;
  gap: 4px;
  padding: 12px;
  border: 1px solid rgba(240, 240, 250, 0.1);
  border-radius: 8px;
  background: rgba(240, 240, 250, 0.04);
}

.memory-metrics span,
.memory-list > span {
  color: rgba(124, 255, 178, 0.72);
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 0.12em;
}

.memory-metrics strong {
  color: #f0f0fa;
  font-size: 24px;
  line-height: 1.1;
}

.memory-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.memory-list {
  display: grid;
  align-content: start;
  gap: 10px;
  min-width: 0;
  padding: 13px;
  border: 1px solid rgba(240, 240, 250, 0.1);
  border-radius: 8px;
  background: rgba(5, 6, 8, 0.64);
}

.memory-list div {
  display: grid;
  gap: 5px;
  padding: 10px;
  border-radius: 8px;
  background: rgba(240, 240, 250, 0.045);
}

.memory-list div.not-resolved {
  border: 1px solid rgba(255, 138, 22, 0.2);
  background: rgba(255, 138, 22, 0.08);
}

.memory-list div.resolved {
  border: 1px solid rgba(124, 255, 178, 0.2);
  background: rgba(124, 255, 178, 0.07);
}

.memory-list b {
  justify-self: start;
  padding: 4px 7px;
  border-radius: 999px;
  background: rgba(106, 166, 255, 0.14);
  color: #9ec4ff;
  font-size: 10px;
  line-height: 1;
}

.memory-list div.not-resolved b,
.memory-list div.high b {
  color: #ffb35b;
  background: rgba(255, 138, 22, 0.16);
}

.memory-list div.resolved b {
  color: #7cffb2;
  background: rgba(124, 255, 178, 0.14);
}

.memory-list strong {
  color: #f0f0fa;
  font-size: 13px;
  line-height: 1.45;
}

.memory-list small,
.memory-list p,
.memory-list li {
  margin: 0;
  color: rgba(240, 240, 250, 0.56);
  font-size: 12px;
  line-height: 1.65;
}

.evidence-chip {
  justify-self: start;
  max-width: 100%;
  overflow: hidden;
  padding: 4px 7px;
  border: 1px solid rgba(106, 166, 255, 0.18);
  border-radius: 999px;
  background: rgba(106, 166, 255, 0.08);
  color: rgba(158, 196, 255, 0.82);
  cursor: pointer;
  font-style: normal;
  font-size: 12px;
  line-height: 1.65;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.evidence-chip:hover {
  border-color: rgba(124, 255, 178, 0.34);
  color: #7cffb2;
}

.evidence-anchor-dialog {
  max-width: 640px;
}

.evidence-anchor-body {
  grid-template-columns: 180px minmax(0, 1fr);
}

.evidence-excerpt-state {
  padding: 10px 12px;
  border: 1px solid rgba(106, 166, 255, 0.14);
  border-radius: 8px;
  background: rgba(106, 166, 255, 0.08);
  color: rgba(240, 240, 250, 0.62);
  font-size: 12px;
  line-height: 1.6;
}

.evidence-excerpt-state.error {
  border-color: rgba(255, 84, 84, 0.22);
  background: rgba(255, 84, 84, 0.08);
  color: rgba(255, 176, 176, 0.88);
}

.evidence-raw {
  overflow: auto;
  max-height: 300px;
  margin: 0;
  padding: 12px;
  border: 1px solid rgba(240, 240, 250, 0.1);
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.28);
  color: rgba(240, 240, 250, 0.72);
  font-size: 12px;
  line-height: 1.55;
  white-space: pre-wrap;
  word-break: break-word;
}

.memory-list ul {
  display: grid;
  gap: 6px;
  margin: 0;
  padding-left: 18px;
}

.full-score-gap {
  border-color: rgba(255, 138, 22, 0.2);
  background:
    linear-gradient(145deg, rgba(255, 138, 22, 0.07), transparent 62%),
    rgba(5, 6, 8, 0.64);
}

.memory-timeline {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.memory-timeline span {
  max-width: 100%;
  overflow: hidden;
  padding: 7px 9px;
  border: 1px solid rgba(106, 166, 255, 0.16);
  border-radius: 999px;
  background: rgba(106, 166, 255, 0.08);
  color: rgba(240, 240, 250, 0.68);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.member-list button {
  display: grid;
  grid-template-columns: 40px minmax(0, 1fr);
  gap: 2px 12px;
  align-items: center;
  padding: 12px;
  border: 1px solid rgba(240, 240, 250, 0.12);
  border-radius: 8px;
  background: rgba(240, 240, 250, 0.04);
  color: inherit;
  text-align: left;
  cursor: pointer;
}

.member-list button.active {
  border-color: rgba(124, 255, 178, 0.48);
  background: rgba(124, 255, 178, 0.1);
}

.member-list button span {
  grid-row: span 2;
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: rgba(124, 255, 178, 0.16);
  color: #7cffb2;
  font-weight: 950;
}

.member-list button small {
  color: rgba(240, 240, 250, 0.54);
}

.radar-wrap {
  position: relative;
  width: 100%;
  aspect-ratio: 1;
}

.radar-wrap svg {
  width: 100%;
  height: 100%;
}

.radar-ring {
  fill: none;
  stroke: rgba(240, 240, 250, 0.1);
  stroke-width: 1;
}

.radar-axis {
  stroke: rgba(240, 240, 250, 0.12);
  stroke-width: 1;
}

.radar-fill {
  fill: rgba(124, 255, 178, 0.22);
  stroke: #7cffb2;
  stroke-width: 2;
}

.radar-dot {
  fill: #f0f0fa;
  stroke: #7cffb2;
  stroke-width: 2;
}

.radar-labels span {
  position: absolute;
  transform: translate(-50%, -50%);
  color: rgba(240, 240, 250, 0.58);
  font-size: 11px;
  font-weight: 850;
  white-space: nowrap;
}

.ability-bars {
  display: grid;
  gap: 10px;
  margin-top: 10px;
}

.ability-bars div {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr) 34px;
  align-items: center;
  gap: 10px;
}

.ability-bars span,
.ability-bars small {
  color: rgba(240, 240, 250, 0.58);
  font-size: 12px;
}

.ability-bars span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.ability-bars .sample-tag {
  font-style: normal;
  font-size: 10px;
  font-weight: 800;
  line-height: 1;
  padding: 2px 5px;
  border-radius: 5px;
  color: rgba(240, 240, 250, 0.5);
  background: rgba(240, 240, 250, 0.08);
  border: 1px solid rgba(240, 240, 250, 0.16);
}

.ability-bars div.placeholder span,
.ability-bars div.placeholder small {
  color: rgba(240, 240, 250, 0.34);
}

.ability-bars div.placeholder i b {
  background: repeating-linear-gradient(
    -45deg,
    rgba(240, 240, 250, 0.22),
    rgba(240, 240, 250, 0.22) 4px,
    rgba(240, 240, 250, 0.08) 4px,
    rgba(240, 240, 250, 0.08) 8px
  );
  box-shadow: none;
  opacity: 0.7;
}

.radar-fill-pending {
  opacity: 0.4;
  stroke-dasharray: 4 4;
}

.radar-dot-pending {
  fill: rgba(240, 240, 250, 0.35);
}

.speaker-align {
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px solid rgba(240, 240, 250, 0.1);
  display: grid;
  gap: 10px;
}

.speaker-align-head {
  display: flex;
  align-items: baseline;
  gap: 10px;
  flex-wrap: wrap;
}

.speaker-align-head b {
  color: #f0f0fa;
  font-size: 14px;
}

.speaker-align-head small {
  color: rgba(240, 240, 250, 0.5);
  font-size: 12px;
}

.speaker-row {
  padding: 12px;
  border: 1px solid rgba(240, 240, 250, 0.12);
  border-left: 3px solid rgba(240, 240, 250, 0.25);
  border-radius: 10px;
  background: rgba(240, 240, 250, 0.035);
  display: grid;
  gap: 10px;
}

.speaker-row.confirmed {
  border-left-color: #7cffb2;
  background: rgba(124, 255, 178, 0.06);
}

.speaker-row.rejected {
  border-left-color: rgba(240, 240, 250, 0.2);
  opacity: 0.6;
}

.speaker-main {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 10px;
  align-items: start;
}

.speaker-tag {
  font-weight: 850;
  font-size: 12px;
  color: #6aa6ff;
  padding: 3px 8px;
  border-radius: 6px;
  background: rgba(106, 166, 255, 0.12);
}

.speaker-info {
  display: grid;
  gap: 3px;
}

.speaker-info p {
  margin: 0;
  font-size: 12px;
  line-height: 1.6;
  color: rgba(240, 240, 250, 0.72);
}

.speaker-match strong {
  color: #7cffb2;
}

.speaker-match .unmatched {
  color: #ffcf6a;
  font-style: normal;
}

.speaker-quote {
  color: rgba(240, 240, 250, 0.5) !important;
  font-style: italic;
}

.speaker-status {
  font-size: 11px;
  font-weight: 800;
  color: rgba(240, 240, 250, 0.55);
  white-space: nowrap;
}

.speaker-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}

.speaker-select {
  height: 30px;
  padding: 0 8px;
  border-radius: 7px;
  border: 1px solid rgba(240, 240, 250, 0.16);
  background: rgba(8, 10, 14, 0.6);
  color: #f0f0fa;
  font-size: 12px;
}

.speaker-btn {
  height: 30px;
  padding: 0 12px;
  border-radius: 7px;
  border: 1px solid transparent;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  background: rgba(240, 240, 250, 0.08);
  color: rgba(240, 240, 250, 0.8);
  transition: filter 0.15s ease;
}

.speaker-btn:hover {
  filter: brightness(1.15);
}

.speaker-btn.confirm {
  background: rgba(124, 255, 178, 0.16);
  color: #7cffb2;
  border-color: rgba(124, 255, 178, 0.3);
}

.speaker-btn.reject {
  background: rgba(255, 207, 106, 0.12);
  color: #ffcf6a;
}

.speaker-btn.reset {
  background: transparent;
  color: rgba(240, 240, 250, 0.5);
}

.evidence-list {
  margin-top: 16px;
}

.ability-confidence {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 4px 10px;
  margin-top: 14px;
  padding: 12px;
  border: 1px solid rgba(124, 255, 178, 0.18);
  border-radius: 8px;
  background: rgba(124, 255, 178, 0.055);
}

.ability-confidence span,
.ability-confidence small {
  color: rgba(240, 240, 250, 0.56);
  font-size: 12px;
}

.ability-confidence strong {
  grid-row: span 2;
  color: #7cffb2;
  font-size: 22px;
}

.evidence-list p {
  margin: 0;
  color: rgba(240, 240, 250, 0.68);
  line-height: 1.7;
}

.observe-body {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 18px;
  align-items: start;
}

.observe-col {
  display: grid;
  gap: 12px;
  align-content: start;
}

.observe-intervention {
  display: block;
  margin-top: 4px;
  padding: 12px 14px;
  border-radius: 8px;
  background: rgba(124, 255, 178, 0.08);
  border: 1px solid rgba(124, 255, 178, 0.18);
  color: #cfeede;
  line-height: 1.7;
}

.observe-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin: 0;
}

.readiness-card {
  display: grid;
  gap: 4px;
  margin-top: 14px;
  padding: 14px;
  border: 1px solid rgba(106, 166, 255, 0.18);
  border-radius: 8px;
  background: rgba(106, 166, 255, 0.07);
}

.readiness-card.ready {
  border-color: rgba(124, 255, 178, 0.3);
  background: rgba(124, 255, 178, 0.07);
}

.readiness-card.risk {
  border-color: rgba(255, 138, 22, 0.34);
  background: rgba(255, 138, 22, 0.07);
}

.readiness-card span,
.readiness-card small {
  color: rgba(240, 240, 250, 0.56);
  font-size: 12px;
}

.readiness-card strong {
  color: #7cffb2;
  font-size: 30px;
}

.observe-metrics span {
  padding: 9px;
  border-radius: 8px;
  background: rgba(106, 166, 255, 0.1);
  color: rgba(240, 240, 250, 0.72);
  text-align: center;
  font-size: 12px;
}

.observe-list {
  display: grid;
  gap: 8px;
  margin-top: 12px;
}

.observe-list b {
  color: rgba(124, 255, 178, 0.74);
  font-size: 12px;
  letter-spacing: 0.08em;
}

.observe-list small {
  padding: 10px;
  border-radius: 8px;
  background: rgba(240, 240, 250, 0.045);
  color: rgba(240, 240, 250, 0.66);
  line-height: 1.6;
}

.empty-state {
  padding: 18px;
  border: 1px dashed rgba(240, 240, 250, 0.14);
  border-radius: 8px;
  color: rgba(240, 240, 250, 0.52);
}

@media (max-width: 1180px) {
  .team-hero,
  .main-layout,
  .work-tier,
  .task-grid,
  .observe-body,
  .roadshow-review-layout,
  .review-columns {
    grid-template-columns: 1fr;
  }

  .cmd-kpi {
    grid-template-columns: 132px minmax(0, 1fr);
  }

  .project-modal-body {
    grid-template-columns: 1fr;
  }

  .filter-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .stage-line,
  .metric-strip,
  .check-grid,
  .permission-grid,
  .material-overview,
  .memory-grid,
  .memory-metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .material-row {
    grid-template-columns: 110px minmax(0, 1fr);
    align-items: start;
  }

  .inspector-body {
    grid-template-columns: 1fr;
  }

  .material-tools {
    grid-column: 1 / -1;
    justify-items: stretch;
  }
}

@media (max-width: 760px) {
  .team-page {
    padding: 34px 18px 96px;
  }

  .team-hero h1 {
    font-size: 38px;
  }

  .metric-strip,
  .stage-line,
  .task-grid,
  .material-grid,
  .material-overview,
  .material-row,
  .submit-box,
  .composer,
  .bind-form,
  .meeting-picker,
    .role-banner,
    .project-form,
    .filter-grid,
    .member-row,
    .check-grid,
    .permission-grid,
    .memory-grid,
    .memory-metrics {
    grid-template-columns: 1fr;
  }

  .memory-head {
    display: grid;
  }

  .memory-head small {
    max-width: none;
    text-align: left;
  }

  .project-modal-overlay,
  .task-modal-overlay {
    padding: 14px;
    place-items: end center;
  }

  .project-modal,
  .task-modal {
    max-height: calc(100vh - 28px);
  }

  .project-modal-head,
  .task-modal-head,
  .member-console-head,
  .project-modal-actions,
  .task-modal-actions,
  .hero-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .task-modal-form {
    grid-template-columns: 1fr;
  }

  .selected-strip {
    grid-template-columns: 1fr;
  }

  .material-review-line {
    grid-template-columns: 1fr;
  }

  .review-dialog-body,
  .review-dialog-actions {
    grid-template-columns: 1fr;
  }

  .material-inspector-overlay {
    padding: 14px;
    place-items: end center;
  }

  .material-inspector {
    max-height: calc(100vh - 28px);
  }

  .inspector-head {
    align-items: center;
  }

  .permission-pills {
    grid-column: 1;
  }

  .metric-strip article + article {
    border-left: 0;
    border-top: 1px solid rgba(240, 240, 250, 0.1);
  }
}
.team-console-page {
  min-height: calc(100vh - 72px);
  padding: 0;
  background-color: #ffffff;
  background-image: none;
  color: #17120f;
}

.team-console-page > .team-hero,
.team-console-page > .team-state-panel:not(.console-state),
.team-console-page > .stage-line,
.team-console-page > .role-banner,
.team-console-page > .work-tier {
  display: none !important;
}

.team-console-page button,
.team-console-page select {
  font: inherit;
}

.team-console-page button {
  cursor: pointer;
}

.console-state {
  display: grid;
  gap: 12px;
  width: min(720px, calc(100vw - 48px));
  margin: 72px auto;
  padding: 32px;
  border: 1px solid #ece4dc;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 18px 48px rgba(39, 28, 18, 0.08);
}

.console-state strong {
  font-size: 24px;
}

.console-state span {
  color: #766d66;
}

.console-state button {
  width: fit-content;
  min-width: 112px;
  height: 40px;
  border: 0;
  border-radius: 8px;
  background: #17120f;
  color: #fffaf5;
  font-weight: 800;
}

.console-state.warning {
  border-color: #ffd9c0;
  background: #fff6ef;
}

.team-console-shell {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr) 300px;
  min-height: calc(100vh - 72px);
}

.team-console-rail {
  position: sticky;
  top: 72px;
  align-self: start;
  display: grid;
  grid-template-rows: auto 1fr auto;
  gap: 18px;
  height: calc(100vh - 72px);
  padding: 22px 16px;
  border-right: 1px solid #ece4dc;
  background: rgba(255, 255, 255, 0.78);
  backdrop-filter: blur(16px);
}

.team-project-card {
  display: grid;
  grid-template-columns: 76px minmax(0, 1fr);
  gap: 12px;
  padding: 12px;
  border: 1px solid #e9dfd5;
  border-radius: 12px;
  background: #fffdfb;
}

.project-cover {
  overflow: hidden;
  height: 76px;
  border-radius: 8px;
  background:
    linear-gradient(135deg, rgba(242, 91, 12, 0.12), rgba(84, 139, 74, 0.16)),
    linear-gradient(160deg, #cfe6d7 0 32%, #7fad8f 33% 42%, #eef6ee 43% 62%, #8fc28f 63% 100%);
  box-shadow: inset 0 0 0 1px rgba(23, 18, 15, 0.08);
}

.project-cover span {
  display: block;
  width: 100%;
  height: 100%;
  background:
    repeating-linear-gradient(72deg, transparent 0 11px, rgba(255, 255, 255, 0.68) 12px 13px),
    linear-gradient(180deg, transparent 55%, rgba(21, 88, 53, 0.16));
}

.team-project-card strong,
.team-project-card small,
.team-project-card em {
  display: block;
}

.team-project-card strong {
  margin: 3px 0 6px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 15px;
}

.team-project-card small {
  color: #7d746d;
  font-size: 12px;
  line-height: 1.55;
}

.team-project-card em {
  margin-top: 7px;
  color: #8b8179;
  font-size: 11px;
  font-style: normal;
}

.team-console-nav {
  display: grid;
  align-content: start;
  gap: 8px;
}

.team-console-nav button {
  display: grid;
  grid-template-columns: 28px 1fr;
  align-items: center;
  gap: 10px;
  min-height: 44px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: #5d544d;
  text-align: left;
}

.team-console-nav button span {
  display: grid;
  place-items: center;
  width: 26px;
  height: 26px;
  margin-left: 4px;
  border: 1px solid #ebe2da;
  border-radius: 8px;
  background: #fffdfb;
  color: #5e534c;
  font-size: 12px;
  font-weight: 900;
}

.team-console-nav button b {
  font-size: 14px;
}

.team-console-nav button.active {
  background: linear-gradient(90deg, rgba(242, 91, 12, 0.14), rgba(242, 91, 12, 0.04));
  color: #f25b0c;
  box-shadow: inset 3px 0 0 #f25b0c;
}

.team-console-nav button.active span {
  border-color: rgba(242, 91, 12, 0.24);
  background: #fff0e7;
  color: #f25b0c;
}

.team-storage {
  display: grid;
  gap: 12px;
  padding: 14px;
  border: 1px solid #eee4dc;
  border-radius: 12px;
  background: #fffdfb;
}

.team-storage div {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  color: #746a63;
  font-size: 12px;
}

.team-storage i {
  overflow: hidden;
  height: 6px;
  border-radius: 999px;
  background: #eee7e1;
}

.team-storage i b {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #f25b0c, #ff8b45);
}

.team-storage button {
  height: 38px;
  border: 1px solid #eadfd7;
  border-radius: 8px;
  background: #fffaf6;
  color: #4f453f;
  font-weight: 800;
}

.team-console-main {
  display: grid;
  align-content: start;
  gap: 16px;
  padding: 28px;
}

.console-page-head {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 20px;
}

.console-page-head h1 {
  margin: 0 0 8px;
  font-size: 28px;
  letter-spacing: 0;
}

.console-page-head p {
  margin: 0;
  color: #716960;
  font-size: 14px;
}

.team-switch.compact {
  max-width: 420px;
  overflow: auto;
  border-color: #e9dfd7;
  background: #fffdfb;
}

.team-overview-strip {
  display: grid;
  grid-template-columns: 1fr 1.35fr 1fr 1fr;
  gap: 0;
  overflow: hidden;
  border: 1px solid #e9dfd7;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.86);
}

.team-overview-strip article {
  display: grid;
  gap: 7px;
  min-height: 102px;
  padding: 22px 26px;
  border-right: 1px solid #eee7e1;
}

.team-overview-strip article:last-child {
  border-right: 0;
}

.team-overview-strip span,
.console-card-head p,
.side-card p {
  color: #746b64;
}

.team-overview-strip strong {
  font-size: 25px;
  line-height: 1;
}

.team-overview-strip small {
  color: #8f867f;
  font-size: 12px;
}

.team-overview-strip strong i {
  display: inline-block;
  width: 9px;
  height: 9px;
  margin-right: 8px;
  border-radius: 999px;
  background: #26b260;
  box-shadow: 0 0 0 5px rgba(38, 178, 96, 0.12);
  vertical-align: 3px;
}

.progress-overview div {
  overflow: hidden;
  height: 7px;
  border-radius: 999px;
  background: #eee8e2;
}

.progress-overview div b {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #f25b0c, #ff8b45);
}

.console-card,
.side-card {
  border: 1px solid #e9dfd7;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.88);
  box-shadow: 0 12px 32px rgba(42, 28, 18, 0.045);
}

.console-card {
  padding: 18px;
}

.console-card-head,
.side-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 16px;
}

.console-card-head h2,
.side-card h2 {
  margin: 0;
  font-size: 18px;
}

.console-card-head p {
  max-width: 640px;
  margin: 5px 0 0;
  font-size: 13px;
}

.console-card-head button,
.side-card-head button,
.side-card > button,
.roadshow-side-card button {
  min-width: 92px;
  height: 36px;
  border: 1px solid #e9dfd7;
  border-radius: 8px;
  background: #fffdfb;
  color: #17120f;
  font-weight: 800;
}

.console-card-head button:hover,
.side-card > button:hover,
.roadshow-side-card button:hover {
  border-color: #f25b0c;
  color: #f25b0c;
}

.member-tiles {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 12px;
}

.member-tiles button {
  display: grid;
  grid-template-columns: 48px 1fr;
  column-gap: 10px;
  row-gap: 3px;
  align-items: center;
  min-height: 96px;
  padding: 14px;
  border: 1px solid #e9dfd7;
  border-radius: 10px;
  background: #fffdfb;
  text-align: left;
}

.member-tiles button span {
  grid-row: span 3;
  display: grid;
  place-items: center;
  width: 48px;
  height: 48px;
  border-radius: 999px;
  background: linear-gradient(145deg, #fff1e8, #f3f0ed);
  color: #f25b0c;
  font-weight: 900;
}

.member-tiles button strong,
.member-tiles button small,
.member-tiles button em {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.member-tiles button small,
.member-tiles button em {
  color: #837970;
  font-size: 12px;
  font-style: normal;
}

.member-tiles button.active {
  border-color: rgba(242, 91, 12, 0.32);
  background: #fff7f0;
}

.member-tiles .member-invite {
  border-style: dashed;
  background: #fffaf6;
}

.console-split {
  display: grid;
  grid-template-columns: minmax(0, 1.08fr) minmax(360px, 0.92fr);
  gap: 16px;
}

.file-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 14px;
}

.file-tabs button {
  height: 30px;
  padding: 0 13px;
  border: 1px solid #eee3db;
  border-radius: 999px;
  background: #fffdfb;
  color: #6e645d;
  font-size: 12px;
  font-weight: 800;
}

.file-tabs button.active {
  border-color: #f25b0c;
  background: #f25b0c;
  color: #fffaf5;
}

.file-table {
  overflow: hidden;
  border: 1px solid #f0e7df;
  border-radius: 10px;
}

.file-table-head,
.file-row {
  display: grid;
  grid-template-columns: minmax(210px, 1.8fr) 84px 88px 112px 74px 104px;
  align-items: center;
  gap: 12px;
  min-height: 48px;
  padding: 0 12px;
}

.file-table-head {
  background: #fbf6f1;
  color: #8b8178;
  font-size: 12px;
}

.file-row {
  border-top: 1px solid #f0e7df;
  color: #5b514a;
  font-size: 12px;
}

.file-row strong {
  display: flex;
  align-items: center;
  gap: 9px;
  min-width: 0;
  color: #17120f;
}

.file-row strong i {
  display: grid;
  flex: 0 0 auto;
  place-items: center;
  width: 24px;
  height: 24px;
  border-radius: 6px;
  background: #f25b0c;
  color: #fffaf5;
  font-size: 10px;
  font-style: normal;
  font-weight: 900;
}

.file-row strong i.doc,
.file-row strong i.pdf {
  background: #4678e8;
}

.file-row strong i.sheet {
  background: #28a65a;
}

.file-row strong i.image {
  background: #8a5cf6;
}

.file-row strong i.video {
  background: #f25b0c;
}

.file-actions {
  display: flex;
  gap: 6px;
}

.file-actions button {
  height: 28px;
  padding: 0 9px;
  border: 1px solid #eadfd7;
  border-radius: 7px;
  background: #fffdfb;
  color: #413832;
  font-size: 12px;
  font-weight: 800;
}

.file-actions button:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.phase-list {
  display: grid;
  gap: 9px;
}

.phase-list section {
  overflow: hidden;
  border: 1px solid #eee4dc;
  border-radius: 10px;
  background: #fffdfb;
}

.phase-head {
  display: grid;
  grid-template-columns: 1fr auto;
  width: 100%;
  min-height: 36px;
  padding: 0 12px;
  border: 0;
  background: linear-gradient(90deg, #fff6ee, #fffdfb);
  color: #514842;
  text-align: left;
  font-weight: 900;
}

.phase-task {
  display: grid;
  grid-template-columns: 16px minmax(0, 1fr) 112px 54px;
  align-items: center;
  gap: 8px;
  min-height: 38px;
  padding: 0 12px;
  border-top: 1px solid #f0e7df;
  font-size: 12px;
}

.phase-task i {
  width: 10px;
  height: 10px;
  border: 1px solid #d8cec6;
  border-radius: 999px;
}

.phase-task i.done,
.phase-task i.approved {
  border-color: #27aa5f;
  background: #27aa5f;
}

.phase-task i.in-progress {
  border-color: #f25b0c;
  background: #f25b0c;
}

.phase-task strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.phase-task small {
  color: #877d74;
}

.phase-task em {
  color: #8b8178;
  font-style: normal;
  text-align: right;
}

.activity-card select {
  height: 32px;
  border: 1px solid #e9dfd7;
  border-radius: 8px;
  background: #fffdfb;
  color: #5b5149;
}

.activity-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 28px;
}

.activity-item {
  display: grid;
  grid-template-columns: 16px 86px minmax(0, 1fr) 92px;
  align-items: center;
  min-height: 34px;
  border-bottom: 1px solid #f1e9e2;
  color: #5f554d;
  font-size: 13px;
}

.activity-item span {
  width: 7px;
  height: 7px;
  border: 1px solid #17120f;
  border-radius: 999px;
}

.activity-item p {
  overflow: hidden;
  margin: 0;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.activity-item small {
  color: #8c837b;
  text-align: right;
}

.console-empty {
  padding: 18px;
  color: #8a8179;
  font-size: 13px;
}

.team-console-aside {
  display: grid;
  align-content: start;
  gap: 16px;
  padding: 28px 24px 28px 0;
}

.side-card {
  padding: 18px;
}

.side-card-head strong {
  color: #f25b0c;
}

.prep-status-card {
  background: linear-gradient(145deg, #fffdfb, #fff6ef);
}

.prep-status-card .side-card-head button,
.roadshow-side-card button {
  border-color: transparent;
  background: #f25b0c;
  color: #fffaf5;
}

.prep-ring {
  position: relative;
  display: grid;
  place-items: center;
  width: 118px;
  height: 118px;
  margin: 4px 0 16px;
  border-radius: 999px;
  background:
    radial-gradient(circle at center, #fffdfb 0 54%, transparent 55%),
    conic-gradient(#f25b0c calc(var(--progress) * 1%), #ebe4de 0);
}

.prep-ring strong {
  font-size: 26px;
}

.prep-ring span {
  margin-top: 34px;
  color: #766d66;
  font-size: 11px;
}

.prep-step-list {
  display: grid;
  gap: 9px;
}

.prep-step-list div {
  display: grid;
  grid-template-columns: 14px 1fr 56px;
  align-items: center;
  gap: 8px;
  color: #716860;
  font-size: 12px;
}

.prep-step-list i {
  width: 10px;
  height: 10px;
  border: 1px solid #bdb3ab;
  border-radius: 999px;
}

.prep-step-list div.done i {
  border-color: #27aa5f;
  background: #27aa5f;
}

.prep-step-list div.active {
  color: #f25b0c;
  font-weight: 900;
}

.prep-step-list div.active i {
  border-color: #f25b0c;
  box-shadow: 0 0 0 5px rgba(242, 91, 12, 0.12);
}

.prep-step-list b {
  text-align: right;
}

.missing-list,
.version-list {
  display: grid;
  gap: 8px;
}

.missing-list button,
.version-list button {
  display: grid;
  grid-template-columns: 24px minmax(0, 1fr);
  column-gap: 10px;
  row-gap: 2px;
  align-items: center;
  min-height: 40px;
  padding: 8px 10px;
  border: 0;
  border-radius: 8px;
  background: #fff8f2;
  color: #504740;
  text-align: left;
}

.missing-list button span {
  grid-row: span 2;
  display: grid;
  place-items: center;
  width: 20px;
  height: 20px;
  border-radius: 6px;
  background: #fff0e8;
  color: #f25b0c;
  font-weight: 900;
}

.missing-list small,
.version-list small {
  color: #8c837b;
}

.version-list button {
  grid-template-columns: 34px minmax(0, 1fr);
  background: #fffdfb;
  box-shadow: inset 0 -1px 0 #f0e7df;
}

.version-list b {
  grid-row: span 2;
  color: #b47448;
}

.version-list span,
.version-list small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.roadshow-side-card {
  display: grid;
  gap: 10px;
}

.roadshow-side-card p {
  margin: 0;
  font-size: 13px;
  line-height: 1.7;
}

.roadshow-side-card span {
  color: #6a625b;
  font-size: 13px;
}

@media (max-width: 1320px) {
  .team-console-shell {
    grid-template-columns: 220px minmax(0, 1fr);
  }

  .team-console-aside {
    grid-column: 2;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    padding: 0 28px 28px;
  }

  .team-console-rail {
    height: calc(100vh - 72px);
  }

  .member-tiles {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 980px) {
  .team-console-shell {
    display: block;
  }

  .team-console-rail {
    position: static;
    height: auto;
    border-right: 0;
    border-bottom: 1px solid #ece4dc;
  }

  .team-console-nav {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }

  .team-console-main,
  .team-console-aside {
    padding: 20px;
  }

  .team-overview-strip,
  .console-split,
  .activity-grid,
  .team-console-aside {
    grid-template-columns: 1fr;
  }

  .team-overview-strip article {
    border-right: 0;
    border-bottom: 1px solid #eee7e1;
  }

  .team-overview-strip article:last-child {
    border-bottom: 0;
  }

  .file-table {
    overflow-x: auto;
  }

  .file-table-head,
  .file-row {
    min-width: 760px;
  }
}

/* 总览优先改版覆盖 */
.team-redesign-shell {
  display: block;
  min-height: calc(100vh - 72px);
  width: min(1640px, calc(100vw - 48px));
  margin: 0 auto;
  padding: 28px 0 48px;
}

.team-redesign-head {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 260px auto;
  gap: 18px;
  align-items: center;
  padding: 22px 24px;
  border: 1px solid #ece4dc;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 16px 42px rgba(45, 31, 18, 0.06);
}

.team-redesign-copy span,
.section-title span {
  color: #f25b0c;
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 2px;
}

.team-redesign-copy h1 {
  margin: 6px 0;
  font-size: 28px;
  line-height: 1.18;
}

.team-redesign-copy p {
  max-width: 760px;
  margin: 0;
  color: #716960;
  line-height: 1.7;
}

.team-redesign-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.team-redesign-tags b {
  padding: 6px 10px;
  border: 1px solid rgba(242, 91, 12, 0.16);
  border-radius: 999px;
  background: #fff6ef;
  color: #cc4808;
  font-size: 12px;
}

.team-redesign-progress {
  display: grid;
  gap: 8px;
  padding: 14px;
  border: 1px solid rgba(242, 91, 12, 0.16);
  border-radius: 14px;
  background: #fff8f3;
}

.team-redesign-progress span,
.team-redesign-progress small {
  color: #8b8179;
  font-size: 12px;
}

.team-redesign-progress strong {
  font-size: 26px;
}

.team-redesign-progress i,
.stage-compact-list i {
  display: block;
  overflow: hidden;
  height: 7px;
  border-radius: 999px;
  background: #eee6df;
}

.team-redesign-progress i b,
.stage-compact-list i em {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #f25b0c, #ff8b45);
}

.team-redesign-actions {
  display: grid;
  gap: 10px;
  min-width: 132px;
}

.team-redesign-actions button,
.team-section-tabs button,
.team-redesign-switch button {
  border: 1px solid #eadfd7;
  border-radius: 10px;
  background: #fffdfb;
  color: #4f453f;
  font-weight: 800;
}

.team-redesign-actions button {
  height: 42px;
  padding: 0 16px;
}

.team-redesign-actions .primary-action {
  border-color: #f25b0c;
  background: #f25b0c;
  color: #fff;
}

.team-redesign-switch {
  display: flex;
  gap: 10px;
  margin-top: 16px;
  overflow-x: auto;
}

.team-redesign-switch button {
  height: 38px;
  padding: 0 14px;
  white-space: nowrap;
}

.team-redesign-switch button.active,
.team-section-tabs button.active {
  border-color: rgba(242, 91, 12, 0.26);
  background: #fff0e7;
  color: #f25b0c;
}

.team-section-tabs {
  display: flex;
  gap: 10px;
  margin-top: 16px;
  padding: 8px;
  border: 1px solid #ece4dc;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.78);
  overflow-x: auto;
}

.team-section-tabs button {
  height: 38px;
  padding: 0 16px;
  white-space: nowrap;
}

.team-redesign-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 20px;
  margin-top: 20px;
}

.team-redesign-main,
.team-overview-board {
  display: grid;
  gap: 18px;
  min-width: 0;
}

.team-action-aside {
  position: sticky;
  top: 92px;
  align-self: start;
}

.focus-card {
  border-color: rgba(242, 91, 12, 0.18);
  background: linear-gradient(135deg, #fffaf6, #fff);
}

.focus-list,
.compact-row-list,
.member-table-list,
.stage-compact-list {
  display: grid;
  gap: 10px;
}

.focus-list button,
.compact-row-list button,
.member-table-list button,
.stage-compact-list button {
  width: 100%;
  min-height: 58px;
  border: 1px solid #eee4dc;
  border-radius: 12px;
  background: #fffdfb;
  color: #17120f;
  text-align: left;
}

.focus-list button {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr);
  column-gap: 12px;
  align-items: center;
  padding: 12px;
}

.focus-list button span,
.missing-list button span {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border-radius: 999px;
  background: #f25b0c;
  color: #fff;
  font-size: 12px;
  font-weight: 900;
}

.focus-list button strong,
.focus-list button small {
  grid-column: 2;
}

.focus-list button small,
.compact-row-list button small,
.member-table-list button small,
.member-table-list button em {
  color: #7d746d;
}

.stage-compact-card .console-card-head {
  margin-bottom: 12px;
}

.stage-compact-list button {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px 14px;
  padding: 12px;
}

.stage-compact-list i {
  grid-column: 1 / -1;
}

.overview-two-col {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}

.compact-row-list button {
  display: grid;
  gap: 4px;
  padding: 12px;
}

.member-table-list {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.member-table-list button {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr);
  gap: 4px 12px;
  align-items: center;
  padding: 12px;
}

.member-table-list button > span {
  grid-row: 1 / 4;
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  border-radius: 999px;
  background: #fff0e7;
  color: #f25b0c;
  font-weight: 900;
}

.member-table-list button.active {
  border-color: rgba(242, 91, 12, 0.28);
  background: #fff8f3;
}

.member-table-list .member-invite {
  border-style: dashed;
}

.roadshow-redesign-card {
  display: grid;
  gap: 16px;
}

.roadshow-redesign-grid,
.compact-review-columns {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 16px;
}

.compact-review-columns {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.action-aside-card {
  display: grid;
  gap: 12px;
}

@media (max-width: 1180px) {
  .team-redesign-head,
  .team-redesign-layout,
  .roadshow-redesign-grid {
    grid-template-columns: 1fr;
  }

  .team-action-aside {
    position: static;
  }

  .team-redesign-actions {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .team-redesign-shell {
    width: min(100% - 24px, 1640px);
    padding-top: 16px;
  }

  .team-redesign-head,
  .overview-two-col,
  .member-table-list,
  .compact-review-columns {
    grid-template-columns: 1fr;
  }

  .team-redesign-actions {
    grid-template-columns: 1fr;
  }
}

/* 专业控制台质感强化 */
.team-redesign-shell {
  width: min(1580px, calc(100vw - 56px));
  padding-top: 30px;
}

/* Linear 方向：紧凑、低装饰、列表优先 */
.team-console-page {
  background: #faf9f7;
}

.team-redesign-shell {
  width: min(1500px, calc(100vw - 48px));
  padding-top: 24px;
}

.team-redesign-head {
  grid-template-columns: minmax(0, 1fr) 220px auto;
  padding: 20px 22px;
  border-color: #e9dfd6;
  border-radius: 14px;
  background: #fffdfb;
  box-shadow: none;
}

.team-redesign-head::before {
  display: none;
}

.team-redesign-copy span,
.team-command-metrics span,
.team-section-tabs button,
.console-card-head p,
.compact-row-list button small,
.focus-list button small,
.stage-compact-list button b,
.member-table-list button small,
.member-table-list button em {
  letter-spacing: 0;
}

.team-redesign-copy span {
  color: #8b8179;
  font-size: 12px;
}

.team-redesign-copy h1 {
  margin: 4px 0 6px;
  font-size: 26px;
  letter-spacing: -0.03em;
}

.team-redesign-copy p {
  max-width: 700px;
  color: #6f665f;
  font-size: 14px;
  line-height: 1.6;
}

.team-redesign-tags {
  margin-top: 10px;
}

.team-redesign-tags b {
  padding: 4px 8px;
  border-color: #eadfd7;
  background: #faf7f3;
  color: #5f554e;
  box-shadow: none;
  font-size: 12px;
  font-weight: 700;
}

.team-redesign-tags b:first-child {
  border-color: rgba(242, 91, 12, 0.22);
  background: #fff4eb;
  color: #d64d09;
}

.team-redesign-progress {
  padding: 12px;
  border-color: #eadfd7;
  border-radius: 12px;
  background: #faf7f3;
  backdrop-filter: none;
}

.team-redesign-progress strong {
  font-size: 24px;
}

.team-redesign-progress i,
.stage-compact-list i {
  height: 5px;
  background: #e8ded6;
}

.team-redesign-actions {
  min-width: 124px;
}

.team-redesign-actions button {
  height: 38px;
  border-radius: 9px;
  box-shadow: none;
  font-size: 13px;
}

.team-redesign-actions .primary-action {
  background: #ef5a10;
}

.team-command-metrics {
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin-top: 10px;
}

.team-command-metrics article {
  min-height: 76px;
  padding: 12px 14px;
  border-color: #e9dfd6;
  border-radius: 12px;
  background: #fffdfb;
  box-shadow: none;
}

.team-command-metrics span,
.team-command-metrics small {
  color: #8b8179;
  font-size: 12px;
}

.team-command-metrics strong {
  margin: 6px 0 2px;
  font-size: 22px;
  letter-spacing: -0.03em;
}

.team-redesign-switch {
  margin-top: 10px;
}

.team-redesign-switch button,
.team-section-tabs button {
  border-radius: 8px;
  box-shadow: none;
}

.team-section-tabs {
  gap: 4px;
  margin-top: 10px;
  padding: 4px;
  border-color: #e9dfd6;
  border-radius: 12px;
  background: #fffdfb;
  box-shadow: none;
}

.team-section-tabs button {
  height: 34px;
  padding: 0 12px;
  border-color: transparent;
  background: transparent;
  color: #6f665f;
  font-size: 13px;
}

.team-section-tabs button.active {
  border-color: #eadfd7;
  background: #faf3ed;
  color: #17120f;
}

.team-redesign-layout {
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 16px;
  margin-top: 14px;
}

.team-redesign-main,
.team-overview-board {
  gap: 12px;
}

.console-card,
.side-card {
  border-color: #e9dfd6;
  border-radius: 12px;
  background: #fffdfb;
  box-shadow: none;
}

.console-card {
  padding: 16px;
}

.console-card-head {
  margin-bottom: 12px;
}

.console-card-head h2,
.side-card h2 {
  font-size: 17px;
  letter-spacing: -0.02em;
}

.console-card-head p {
  margin-top: 4px;
  color: #8b8179;
  font-size: 13px;
  line-height: 1.5;
}

.focus-card,
.action-aside-card {
  border-color: #e9dfd6;
  background: #fffdfb;
}

.focus-list,
.compact-row-list,
.member-table-list,
.stage-compact-list,
.missing-list {
  gap: 0;
  border: 1px solid #eee4dc;
  border-radius: 10px;
  overflow: hidden;
}

.focus-list button,
.compact-row-list button,
.member-table-list button,
.stage-compact-list button,
.missing-list button {
  min-height: 52px;
  border: 0;
  border-bottom: 1px solid #eee4dc;
  border-radius: 0;
  background: #fffdfb;
  box-shadow: none;
  transform: none;
}

.focus-list button:last-child,
.compact-row-list button:last-child,
.member-table-list button:last-child,
.stage-compact-list button:last-child,
.missing-list button:last-child {
  border-bottom: 0;
}

.focus-list button:hover,
.compact-row-list button:hover,
.member-table-list button:hover,
.stage-compact-list button:hover,
.missing-list button:hover {
  border-color: transparent;
  background: #faf7f3;
  box-shadow: none;
  transform: none;
}

.focus-list button {
  grid-template-columns: 28px minmax(0, 1fr);
  min-height: 58px;
  padding: 11px 12px;
}

.focus-list button span,
.missing-list button span {
  width: 22px;
  height: 22px;
  background: #ef5a10;
  font-size: 11px;
}

.focus-list button strong,
.compact-row-list button strong,
.member-table-list button strong {
  font-size: 14px;
}

.focus-list button small,
.compact-row-list button small,
.member-table-list button small,
.member-table-list button em {
  font-size: 12px;
}

.overview-two-col {
  gap: 12px;
}

.compact-row-list button {
  min-height: 50px;
  padding: 10px 12px;
}

.stage-compact-list button {
  min-height: 48px;
  padding: 10px 12px;
}

.member-table-list {
  grid-template-columns: 1fr;
}

.member-table-list button {
  grid-template-columns: 34px minmax(0, 1fr);
  min-height: 56px;
  padding: 10px 12px;
}

.member-table-list button > span {
  width: 32px;
  height: 32px;
  background: #faf3ed;
  color: #ef5a10;
}

.file-table,
.phase-list {
  border: 1px solid #eee4dc;
  border-radius: 10px;
  overflow: hidden;
}

.file-table-head,
.file-row,
.phase-head,
.phase-task {
  border-color: #eee4dc;
}

.team-action-aside {
  top: 88px;
}

.side-card {
  padding: 16px;
}

.action-aside-card .side-card-head {
  margin-bottom: 12px;
}

.missing-list button {
  padding: 11px 12px;
}

.roadshow-redesign-grid,
.compact-review-columns {
  gap: 12px;
}

.team-redesign-head {
  position: relative;
  overflow: hidden;
  grid-template-columns: minmax(0, 1fr) 240px auto;
  gap: 20px;
  padding: 26px 28px;
  border-color: rgba(242, 91, 12, 0.16);
  border-radius: 20px;
  background:
    linear-gradient(135deg, rgba(255, 246, 239, 0.98), rgba(255, 255, 255, 0.96) 52%, rgba(255, 250, 246, 0.98)),
    #fff;
  box-shadow: 0 22px 60px rgba(55, 36, 18, 0.08);
}

.team-redesign-head::before {
  content: "";
  position: absolute;
  inset: 0;
  background:
    linear-gradient(90deg, rgba(242, 91, 12, 0.08), transparent 42%),
    radial-gradient(circle at 86% 18%, rgba(242, 91, 12, 0.12), transparent 28%);
  pointer-events: none;
}

.team-redesign-copy,
.team-redesign-progress,
.team-redesign-actions {
  position: relative;
  z-index: 1;
}

.team-redesign-copy h1 {
  font-size: 34px;
  letter-spacing: -0.04em;
}

.team-redesign-copy p {
  font-size: 15px;
}

.team-redesign-tags {
  margin-top: 14px;
}

.team-redesign-tags b {
  padding: 7px 11px;
  border-color: rgba(242, 91, 12, 0.18);
  background: rgba(255, 255, 255, 0.76);
  color: #bf4307;
  box-shadow: 0 6px 16px rgba(242, 91, 12, 0.06);
}

.team-redesign-progress {
  padding: 16px;
  border-color: rgba(242, 91, 12, 0.18);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.68);
  backdrop-filter: blur(12px);
}

.team-redesign-progress strong {
  font-size: 30px;
  letter-spacing: -0.04em;
}

.team-redesign-actions button {
  height: 46px;
  padding: 0 18px;
  border-radius: 12px;
  box-shadow: 0 12px 30px rgba(242, 91, 12, 0.08);
}

.team-command-metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-top: 14px;
}

.team-command-metrics article {
  min-height: 92px;
  padding: 16px;
  border: 1px solid #ece4dc;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.86);
  box-shadow: 0 12px 28px rgba(55, 36, 18, 0.04);
}

.team-command-metrics span,
.team-command-metrics small {
  display: block;
  color: #8b8179;
  font-size: 12px;
}

.team-command-metrics strong {
  display: block;
  margin: 8px 0 4px;
  color: #17120f;
  font-size: 28px;
  letter-spacing: -0.04em;
}

.team-section-tabs {
  margin-top: 14px;
  padding: 7px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.88);
  box-shadow: 0 10px 26px rgba(55, 36, 18, 0.04);
}

.team-section-tabs button {
  height: 42px;
  padding: 0 18px;
  border-radius: 12px;
}

.team-redesign-layout {
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 22px;
}

.focus-card {
  border-color: rgba(242, 91, 12, 0.2);
  background: linear-gradient(135deg, #fff8f1, #fff 48%);
}

.focus-list button,
.compact-row-list button,
.member-table-list button,
.stage-compact-list button {
  min-height: 64px;
  border-color: #eee2d8;
  border-radius: 14px;
  transition: border-color .18s ease, transform .18s ease, box-shadow .18s ease, background .18s ease;
}

.focus-list button:hover,
.compact-row-list button:hover,
.member-table-list button:hover,
.stage-compact-list button:hover {
  border-color: rgba(242, 91, 12, 0.24);
  background: #fffaf7;
  box-shadow: 0 12px 28px rgba(55, 36, 18, 0.06);
  transform: translateY(-1px);
}

.focus-list button {
  padding: 14px;
}

.action-aside-card {
  border-color: rgba(242, 91, 12, 0.16);
  background: linear-gradient(180deg, #fff, #fff8f3);
}

@media (max-width: 1180px) {
  .team-command-metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .team-redesign-shell {
    width: min(100% - 24px, 1580px);
  }

  .team-command-metrics {
    grid-template-columns: 1fr;
  }
}

/* Linear app shell final override */
.team-redesign-head {
  grid-template-columns: minmax(0, 1fr) 190px auto;
  padding: 16px 18px;
}

.team-redesign-copy h1 {
  font-size: 24px;
}

.team-redesign-progress {
  padding: 10px 12px;
}

.team-redesign-progress strong {
  font-size: 22px;
}

.team-command-metrics article {
  min-height: 68px;
  padding: 10px 12px;
}

.team-command-metrics strong {
  font-size: 20px;
}

.team-section-tabs {
  display: none;
}

.team-redesign-layout {
  grid-template-columns: 220px minmax(0, 1fr) 320px;
  gap: 16px;
}

.linear-team-rail {
  position: sticky;
  top: 88px;
  align-self: start;
  display: grid;
  gap: 14px;
  padding: 12px;
  border: 1px solid #e9dfd6;
  border-radius: 12px;
  background: #fffdfb;
}

.linear-rail-group {
  display: grid;
  gap: 4px;
}

.linear-rail-group + .linear-rail-group {
  padding-top: 12px;
  border-top: 1px solid #eee4dc;
}

.linear-rail-group span {
  padding: 6px 8px;
  color: #9a9088;
  font-size: 12px;
  font-weight: 750;
  letter-spacing: 0.01em;
}

.linear-rail-group button {
  display: grid;
  grid-template-columns: 24px minmax(0, 1fr);
  align-items: center;
  gap: 8px;
  min-height: 34px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: #5f554e;
  font-size: 14px;
  line-height: 1.2;
  text-align: left;
}

.linear-rail-group button:hover {
  background: #faf7f3;
}

.linear-rail-group button.active {
  background: #f5eee8;
  color: #17120f;
}

.linear-rail-group button i {
  display: grid;
  place-items: center;
  width: 18px;
  height: 18px;
  border-radius: 0;
  background: transparent;
  color: #9a9088;
  font-size: 11px;
  font-style: normal;
  font-weight: 900;
}

.linear-rail-group button:hover i,
.linear-rail-group button.active i {
  color: #f25b0c;
}

.rail-svg-icon {
  width: 16px;
  height: 16px;
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.85;
}

.linear-rail-group button b {
  overflow: hidden;
  font-size: 14px;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.focus-list button,
.compact-row-list button {
  grid-template-columns: 28px minmax(0, 1fr) 18px;
}

.focus-list button::after,
.compact-row-list button::after {
  content: "›";
  color: #b3aaa3;
  font-size: 18px;
}

@media (max-width: 1180px) {
  .team-redesign-layout {
    grid-template-columns: 1fr;
  }

  .linear-team-rail {
    position: static;
  }

  .linear-rail-group {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }

  .linear-rail-group span {
    grid-column: 1 / -1;
  }
}

@media (max-width: 760px) {
  .linear-rail-group {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

/* Compact project context bar */
.team-redesign-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-height: 52px;
  margin-bottom: 12px;
  padding: 10px 14px;
  border-color: #e9dfd6;
  border-radius: 12px;
  background: #fffdfb;
  box-shadow: none;
}

.team-redesign-head::before {
  content: none;
}

.team-redesign-copy {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.team-redesign-copy h1 {
  overflow: hidden;
  margin: 0;
  font-size: 17px;
  font-weight: 900;
  letter-spacing: -0.02em;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.team-redesign-copy span {
  flex: 0 0 auto;
  padding: 4px 8px;
  border: 1px solid #eee4dc;
  border-radius: 999px;
  background: #faf7f3;
  color: #7a7068;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0;
}

.team-redesign-status {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
  color: #837970;
  font-size: 12px;
  font-weight: 800;
}

.team-redesign-status span {
  padding: 4px 8px;
  border-radius: 999px;
  background: #faf7f3;
  white-space: nowrap;
}

.team-redesign-layout {
  margin-top: 0;
}

.linear-rail-progress {
  display: grid;
  gap: 7px;
  padding: 10px;
  border-top: 1px solid #eee4dc;
  border-bottom: 1px solid #eee4dc;
}

.linear-rail-progress div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.linear-rail-progress span,
.linear-rail-progress small {
  color: #8f857d;
  font-size: 11px;
  font-weight: 800;
}

.linear-rail-progress strong {
  color: #17120f;
  font-size: 18px;
  letter-spacing: -0.03em;
}

.linear-rail-progress i {
  display: block;
  overflow: hidden;
  height: 5px;
  border-radius: 999px;
  background: #eee6df;
}

.linear-rail-progress i b {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: #f25b0c;
}

.linear-rail-stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px;
}

.linear-rail-stats span {
  padding: 8px;
  border-radius: 8px;
  background: #faf7f3;
  color: #827870;
  font-size: 11px;
  font-weight: 800;
}

.linear-rail-stats b {
  display: block;
  margin-bottom: 2px;
  color: #17120f;
  font-size: 15px;
}

@media (max-width: 760px) {
  .team-redesign-head {
    align-items: flex-start;
    flex-direction: column;
  }

  .team-redesign-status {
    justify-content: flex-start;
  }
}

/* Work item hub final layout */
.work-hub-panel {
  overflow: hidden;
  border: 1px solid #e8dfd7;
  border-radius: 12px;
  background: #fff;
}

.work-hub-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-height: 40px;
  padding: 5px 18px;
  border-bottom: 1px solid #eee7e0;
}

.work-hub-head span {
  color: #8a8179;
  font-size: 12px;
  font-weight: 700;
}

.work-hub-head h2 {
  margin: 0;
  color: #17120f;
  font-size: 17px;
  font-weight: 850;
  letter-spacing: -0.03em;
}

.work-hub-head p {
  margin: 4px 0 0;
  color: #8a8179;
  font-size: 14px;
  font-weight: 500;
  line-height: 1.45;
}

.work-hub-head button,
.work-detail-actions button,
.work-detail-section button {
  border: 1px solid #e4dbd2;
  border-radius: 8px;
  background: #fff;
  color: #332b26;
  font-size: 15px;
  font-weight: 850;
}

.work-hub-head button {
  height: 30px;
  padding: 0 10px;
  font-size: 13px;
}

.create-work-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  border: 0 !important;
  border-radius: 9px !important;
  background: linear-gradient(135deg, #ff7a1a 0%, #f25b0c 48%, #d9480a 100%) !important;
  color: #fff !important;
  box-shadow: none !important;
}

.create-work-btn:hover {
  background: linear-gradient(135deg, #ff8a2f 0%, #f25b0c 46%, #c94006 100%) !important;
  box-shadow: 0 8px 18px rgba(242, 91, 12, 0.18) !important;
}

.create-work-btn svg {
  width: 15px;
  height: 15px;
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-width: 2.4;
}

.work-list-table {
  display: grid;
  align-content: start;
  grid-auto-rows: max-content;
}

.work-flow-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-height: 40px;
  padding: 0 18px;
  border-bottom: 1px solid #eee4dc;
}

.work-flow-current {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.work-flow-current strong {
  color: #17120f;
  font-size: 14px;
  font-weight: 800;
}

.work-flow-current span {
  color: #9a9088;
  font-size: 12px;
  font-weight: 650;
}

.work-flow-tools {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
  min-width: 0;
}

.work-flow-tools button,
.work-filter-panel button {
  height: 28px;
  padding: 0 9px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: #8a8179;
  font-size: 12px;
  font-weight: 750;
  white-space: nowrap;
}

.work-flow-tools button:hover,
.work-flow-tools button.active,
.work-filter-panel button:hover,
.work-filter-panel button.active {
  background: #f7ede6;
  color: #17120f;
}

.work-filter-panel {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 18px;
  border-bottom: 1px solid #eee4dc;
  background: rgba(255, 248, 243, 0.48);
  overflow-x: auto;
}

.work-list-head,
.work-item-row {
  display: grid;
  grid-template-columns: 78px 18px minmax(220px, 1fr) minmax(280px, auto);
  gap: 12px;
  align-items: center;
}

.work-list-head {
  padding: 8px 14px;
  border-bottom: 1px solid #eee7e0;
  background: #fbfaf8;
  color: #8a8179;
  font-size: 12px;
  font-weight: 700;
}

.work-item-row {
  align-self: start;
  width: 100%;
  min-height: 50px;
  padding: 8px 18px;
  border: 0;
  border-bottom: 1px solid rgba(240, 235, 230, 0.72);
  background: transparent;
  color: #463d36;
  font-size: 13px;
  text-align: left;
}

.work-issue-stream.density-compact .work-item-row {
  min-height: 40px;
  padding-top: 5px;
  padding-bottom: 5px;
}

.work-issue-stream.density-compact .work-title {
  gap: 0;
}

.work-issue-stream.summary-hidden .work-title small {
  display: none;
}

.work-issue-stream.summary-hidden .work-item-row {
  min-height: 42px;
}

.work-item-row:hover,
.work-item-row.active {
  background: rgba(255, 248, 243, 0.76);
}

.work-item-row.overdue {
  box-shadow: inset 2px 0 0 #f25b0c;
}

.work-code {
  overflow: hidden;
  color: #9a9088;
  font-size: 13px;
  font-variant-numeric: tabular-nums;
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.work-state-dot {
  --progress: 0%;
  --progress-color: #f25b0c;
  flex: 0 0 auto;
  width: 15px;
  height: 15px;
  border: 2px solid var(--progress-color);
  border-radius: 999px;
  background: conic-gradient(var(--progress-color) 0 var(--progress), transparent var(--progress) 100%);
}

.work-state-dot.muted {
  --progress-color: #aaa19a;
}

.work-state-dot.done {
  --progress-color: #2fa45a;
}

.work-state-dot.warning {
  --progress-color: #f25b0c;
}

.work-type {
  display: flex;
  align-items: center;
  gap: 7px;
  color: #6f665e;
  font-size: 13px;
  font-weight: 700;
}

.work-type i {
  display: grid;
  place-items: center;
  width: 18px;
  height: 18px;
  border-radius: 0;
  background: transparent;
  color: #9a9088;
  font-style: normal;
}

.work-item-row:hover .work-type i,
.work-item-row.active .work-type i,
.work-item-row.overdue .work-type i {
  color: #f25b0c;
}

.work-title {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.work-title strong {
  overflow: hidden;
  color: #17120f;
  font-size: 15px;
  font-weight: 750;
  line-height: 1.3;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.work-title small,
.work-item-row > span:not(.work-title):not(.work-type) {
  overflow: hidden;
  color: #8a8179;
  font-size: 13px;
  font-weight: 500;
  line-height: 1.4;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.work-meta {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  min-width: 0;
  overflow: hidden;
}

.work-tag {
  display: inline-flex;
  align-items: center;
  max-width: 98px;
  height: 24px;
  padding: 0 9px;
  border: 1px solid #eadfd7;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.68);
  color: #6f665e;
  font-size: 12px;
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.work-tag.accent {
  border-color: rgba(242, 91, 12, 0.24);
  background: rgba(242, 91, 12, 0.08);
  color: #d94d08;
}

.work-avatar {
  flex: 0 0 auto;
  display: grid;
  place-items: center;
  width: 22px;
  height: 22px;
  border-radius: 999px;
  background: #17120f;
  color: #fff !important;
  font-size: 11px !important;
  font-weight: 850 !important;
}

.work-avatar-stack {
  display: inline-flex;
  align-items: center;
  justify-content: flex-end;
  min-width: 0;
}

.work-avatar-stack .work-avatar {
  margin-left: -6px;
  border: 2px solid #fffdfb;
}

.work-avatar-stack .work-avatar:first-child {
  margin-left: 0;
}

.work-avatar-stack b {
  display: grid;
  place-items: center;
  width: 22px;
  height: 22px;
  margin-left: -6px;
  border: 2px solid #fffdfb;
  border-radius: 999px;
  background: #f7efe8;
  color: #6f665e;
  font-size: 10px;
  font-weight: 850;
}

.work-date {
  flex: 0 0 54px;
  overflow: hidden;
  color: #8a8179;
  font-size: 13px;
  font-weight: 500;
  text-align: right;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.work-status {
  font-weight: 650;
}

.priority-high .work-status,
.work-item-row.overdue .work-status {
  color: #f25b0c;
}

.work-empty-state {
  display: grid;
  place-items: center;
  gap: 6px;
  min-height: 220px;
  color: #8a8179;
}

.work-empty-state strong {
  color: #17120f;
}

.linear-rail-group button em {
  justify-self: end;
  color: #9a9088;
  font-size: 13px;
  font-style: normal;
  font-weight: 750;
}

.linear-rail-group button {
  grid-template-columns: 18px minmax(0, 1fr) auto;
}

.rail-group-toggle {
  grid-template-columns: minmax(0, 1fr) auto !important;
  min-height: 28px !important;
  padding: 0 8px !important;
  color: #9a9088 !important;
}

.rail-group-toggle span {
  padding: 0 !important;
}

.rail-group-toggle em {
  color: #b8aea5 !important;
  font-size: 11px !important;
}

.work-detail-card {
  display: grid;
  align-content: start;
  gap: 14px;
  padding-top: 8px;
}

.work-detail-topline,
.work-detail-section > span {
  color: #8a8179;
  font-size: 13px;
  font-weight: 700;
}

.work-detail-topline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  min-height: 28px;
}

.work-detail-topline span {
  color: #8a8179;
  font-size: 12px;
  font-weight: 750;
}

.work-detail-topline b {
  display: inline-flex;
  align-items: center;
  height: 24px;
  padding: 0 9px;
  border: 1px solid #eadfd7;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.72);
  color: #6f665e;
  font-size: 12px;
  font-weight: 800;
  white-space: nowrap;
}

.work-detail-topline b.warn {
  border-color: rgba(242, 91, 12, 0.24);
  background: rgba(242, 91, 12, 0.08);
  color: #d94d08;
}

.work-detail-title-block {
  display: grid;
  gap: 10px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(238, 231, 224, 0.9);
}

.work-detail-card h2 {
  margin: 0;
  color: #17120f;
  font-size: 19px;
  font-weight: 850;
  line-height: 1.35;
  letter-spacing: -0.03em;
}

.work-detail-card p {
  margin: 0;
  color: #6f665e;
  font-size: 13px;
  font-weight: 500;
  line-height: 1.65;
}

.work-detail-fields {
  display: grid;
  gap: 2px;
  padding: 2px 0 8px;
  border-bottom: 1px solid rgba(238, 231, 224, 0.9);
}

.work-detail-fields div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 30px;
  color: #8a8179;
  font-size: 13px;
  font-weight: 500;
}

.work-detail-fields strong {
  color: #17120f;
  font-weight: 750;
  text-align: right;
}

.detail-avatar-stack {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 6px;
  max-width: 210px;
}

.detail-avatar-stack span {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: #17120f;
  font-size: 12px;
  font-weight: 800;
}

.detail-avatar-stack b {
  display: grid;
  place-items: center;
  width: 20px;
  height: 20px;
  border-radius: 999px;
  background: #17120f;
  color: #fff;
  font-size: 10px;
}

.work-detail-section,
.work-detail-actions {
  display: grid;
  gap: 9px;
}

.work-detail-section {
  padding-bottom: 4px;
}

.work-detail-section small {
  color: #8a8179;
  font-size: 13px;
  line-height: 1.5;
}

.work-detail-section button,
.work-detail-actions button {
  min-height: 38px;
  padding: 0 12px;
  border-color: #eadfd7;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.72);
  color: #332b26;
  font-size: 13px;
  font-weight: 800;
  text-align: left;
}

.work-detail-actions button.primary {
  border-color: #f25b0c;
  background: #f25b0c;
  color: #fff;
  min-height: 44px;
  text-align: center;
}

@media (min-width: 1181px) {
  .team-console-page {
    height: calc(100vh - 72px);
    overflow: hidden;
  }

  .team-redesign-shell {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 0;
    padding: 6px 16px 10px;
    border: 0;
    border-radius: 0;
    background:
      linear-gradient(90deg, rgba(255, 248, 242, 0.88) 0%, rgba(255, 253, 251, 0.96) 19%, rgba(255, 255, 255, 0.98) 52%, rgba(255, 253, 251, 0.96) 81%, rgba(255, 248, 242, 0.86) 100%);
    box-shadow: none;
  }

  .team-redesign-head {
    flex: 0 0 auto;
    position: relative;
    display: block;
    gap: 6px;
    min-height: 0;
    margin: 0 -16px;
    padding: 0 calc(clamp(420px, 34vw, 620px) + 16px) 6px 18px;
    border-bottom: 1px solid rgba(234, 223, 215, 0.78);
    border: 0;
    border-radius: 0;
    background: transparent;
  }

  .team-redesign-title-row {
    display: flex;
    align-items: center;
    gap: 18px;
    width: 100%;
    min-width: 0;
  }

  .team-context-main {
    display: flex;
    align-items: center;
    gap: 7px;
    min-width: 0;
  }

  .team-title-caret {
    width: 0;
    height: 0;
    border-top: 5px solid transparent;
    border-bottom: 5px solid transparent;
    border-left: 8px solid #f25b0c;
    filter: drop-shadow(0 2px 5px rgba(242, 91, 12, 0.22));
  }

  .team-context-main h1 {
    overflow: hidden;
    max-width: 360px;
    margin: 0;
    color: #17120f;
    background: linear-gradient(110deg, #17120f 0%, #17120f 38%, #f25b0c 48%, #fff4ec 52%, #17120f 62%, #17120f 100%);
    background-size: 260% 100%;
    background-clip: text;
    -webkit-background-clip: text;
    font-size: 18px;
    font-weight: 900;
    letter-spacing: -0.03em;
    text-overflow: ellipsis;
    -webkit-text-fill-color: transparent;
    white-space: nowrap;
    animation: team-title-light-sweep 4.8s ease-in-out infinite;
  }

  .team-project-switcher {
    position: relative;
    flex: 0 0 auto;
  }

  .project-switch-trigger {
    display: inline-grid;
    place-items: center;
    width: 22px;
    height: 22px;
    padding: 0;
    border: 0;
    border-radius: 7px;
    background: transparent;
    color: #a0968f;
  }

  .project-switch-trigger:hover,
  .project-switch-trigger[aria-expanded="true"] {
    border-color: transparent;
    background: rgba(242, 91, 12, 0.08);
    color: #f25b0c;
  }

  .project-switch-trigger svg {
    width: 15px;
    height: 15px;
    fill: none;
    stroke: currentColor;
    stroke-linecap: round;
    stroke-linejoin: round;
    stroke-width: 2.15;
    transition: transform 0.18s ease;
  }

  .project-switch-trigger[aria-expanded="true"] svg {
    transform: rotate(90deg) scale(0.96);
  }

  .project-switch-menu {
    position: absolute;
    z-index: 20;
    top: 50%;
    left: calc(100% + 8px);
    display: flex;
    flex-direction: row;
    align-items: center;
    gap: 6px;
    width: max-content;
    max-width: min(560px, calc(100vw - 520px));
    padding: 0;
    border: 0;
    border-radius: 0;
    background: linear-gradient(90deg, rgba(255, 253, 251, 0.84), rgba(255, 248, 242, 0.38), rgba(255, 253, 251, 0));
    box-shadow: none;
    backdrop-filter: none;
    transform: translateY(-50%);
  }

  .project-switch-menu button {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    height: 26px;
    max-width: 178px;
    padding: 0 10px;
    border: 0;
    border-radius: 999px;
    background: rgba(255, 253, 251, 0.72);
    color: #5d544d;
    font-size: 12px;
    font-weight: 850;
    text-align: left;
  }

  .project-switch-menu button:hover,
  .project-switch-menu button.active {
    background: rgba(242, 91, 12, 0.08);
    color: #f25b0c;
  }

  .project-switch-menu button span {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .project-switch-menu button em {
    color: #b66a3e;
    font-size: 10px;
    font-style: normal;
    font-weight: 900;
    letter-spacing: 0.02em;
  }

  .project-switch-pop-enter-active,
  .project-switch-pop-leave-active {
    transition: opacity 0.16s ease, transform 0.16s ease;
  }

  .project-switch-pop-enter-to,
  .project-switch-pop-leave-from {
    opacity: 1;
    transform: translate(0, -50%) scale(1);
  }

  .project-switch-pop-enter-from,
  .project-switch-pop-leave-to {
    opacity: 0;
    transform: translate(-8px, -50%) scale(0.98);
  }

  @keyframes team-title-light-sweep {
    0%, 28% {
      background-position: 115% 50%;
      filter: drop-shadow(0 0 0 rgba(242, 91, 12, 0));
    }

    52% {
      background-position: 0% 50%;
      filter: drop-shadow(0 2px 7px rgba(242, 91, 12, 0.16));
    }

    76%, 100% {
      background-position: -70% 50%;
      filter: drop-shadow(0 0 0 rgba(242, 91, 12, 0));
    }
  }

  .team-redesign-copy b {
    padding: 5px 9px;
    border: 1px solid #eee4dc;
    border-radius: 999px;
    background: #faf7f3;
    color: #7a7068;
    font-size: 12px;
    font-weight: 850;
    white-space: nowrap;
  }

  .team-redesign-switch,
  .team-section-tabs {
    flex: 0 0 auto;
  }

  .team-redesign-switch {
    display: flex;
    gap: 6px;
    justify-content: flex-start;
    min-width: 0;
    margin: 0;
    padding: 0;
    border: 0;
    border-radius: 0;
    background: transparent;
  }

  .team-redesign-switch button {
    overflow: hidden;
    height: 24px;
    max-width: 220px;
    padding: 0 8px;
    border: 0;
    border-radius: 6px;
    background: transparent;
    color: #8a8179;
    font-size: 12px;
    font-weight: 850;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .team-redesign-switch button.active {
    border-color: transparent;
    background: #fff1e8;
    color: #f25b0c;
  }

  .team-redesign-status {
    position: absolute;
    top: 3px;
    right: 18px;
    display: flex;
    flex-wrap: nowrap;
    justify-content: flex-end;
    gap: 6px;
    width: max-content;
    min-width: 0;
    padding-top: 2px;
    overflow: hidden;
  }

  .team-redesign-status span {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 0 7px;
    border-radius: 999px;
    background: transparent;
    color: #8f857d;
    font-size: 11px;
    font-weight: 850;
    white-space: nowrap;
  }

  .team-redesign-status span::before {
    content: "";
    width: 6px;
    height: 6px;
    border-radius: 999px;
    background: #d6cec7;
  }

  .team-redesign-status span:first-child::before,
  .team-redesign-status span:last-child::before {
    background: #f25b0c;
    box-shadow: 0 0 0 3px rgba(242, 91, 12, 0.1);
  }

  .team-redesign-status span + span {
    border-left: 1px solid #eee4dc;
    border-radius: 0;
  }

  .team-redesign-layout {
    grid-template-columns: 220px minmax(0, 1fr) 320px;
    align-items: stretch;
    flex: 1 1 auto;
    min-height: 0;
    margin: 0 -16px -14px;
    background:
      linear-gradient(90deg, rgba(255, 248, 242, 0.82) 0%, rgba(255, 253, 251, 0.7) 17%, rgba(255, 255, 255, 0.98) 26%, rgba(255, 255, 255, 0.98) 74%, rgba(255, 253, 251, 0.72) 84%, rgba(255, 248, 242, 0.82) 100%);
    overflow: hidden;
  }

  .linear-team-rail {
    display: flex;
    flex-direction: column;
    gap: 8px;
    position: static;
    align-self: stretch;
    min-height: 0;
    height: 100%;
    padding: 8px 14px 12px 16px;
    border: 0;
    border-right: 1px solid rgba(238, 228, 220, 0.58);
    border-radius: 0;
    background: linear-gradient(90deg, rgba(255, 248, 242, 0.72), rgba(255, 253, 251, 0.28));
    overflow-y: auto;
    overscroll-behavior: contain;
    scrollbar-width: none;
  }

  .linear-team-rail::-webkit-scrollbar {
    display: none;
  }

  .linear-rail-group {
    flex: 0 0 auto;
    gap: 2px;
  }

  .linear-rail-group + .linear-rail-group {
    padding-top: 8px;
  }

  .linear-rail-group span {
    padding: 3px 8px;
  }

  .linear-rail-group button {
    min-height: 28px;
  }

  .linear-rail-group button i {
    width: 18px;
    height: 18px;
  }

  .linear-rail-group button b {
    font-size: 14px;
  }

  .linear-rail-progress {
    gap: 5px;
    padding: 8px;
  }

  .linear-rail-stats {
    gap: 5px;
  }

  .linear-rail-stats span {
    padding: 6px 8px;
  }

  .linear-rail-progress,
  .linear-rail-stats {
    display: none;
  }

  .team-redesign-main,
  .team-action-aside {
    min-height: 0;
    height: 100%;
  }

  .team-redesign-main {
    display: grid;
    padding: 0;
    border-right: 1px solid rgba(238, 228, 220, 0.58);
    background: rgba(255, 255, 255, 0.86);
  }

  .team-action-aside {
    align-self: stretch;
    height: 100%;
    padding: 0 16px 0 18px;
    background: linear-gradient(90deg, rgba(255, 253, 251, 0.28), rgba(255, 248, 242, 0.78));
    overflow: hidden;
  }

  .work-list-table::-webkit-scrollbar {
    width: 8px;
  }

  .work-list-table::-webkit-scrollbar-thumb {
    border: 2px solid transparent;
    border-radius: 999px;
    background: rgba(147, 130, 116, 0.28);
    background-clip: padding-box;
  }

  .work-list-table::-webkit-scrollbar-track {
    background: transparent;
  }

  .work-hub-panel {
    display: grid;
    grid-template-rows: auto auto minmax(0, 1fr);
    height: 100%;
    min-height: 0;
    border: 0;
    border-radius: 0;
    background: transparent;
  }

  .work-hub-panel.filter-open {
    grid-template-rows: auto auto auto minmax(0, 1fr);
  }

  .work-hub-head {
    padding: 5px 18px;
  }

  .side-card {
    border: 0;
    border-radius: 0;
    background: transparent;
    box-shadow: none;
  }

  .work-list-table {
    min-height: 0;
    overflow-y: auto;
    overscroll-behavior: contain;
    scrollbar-gutter: stable;
  }

  .work-detail-card,
  .action-aside-card {
    height: 100%;
    max-height: 100%;
    overflow: hidden;
  }
}

@media (max-width: 760px) {
  .work-list-head {
    display: none;
  }

  .work-flow-toolbar {
    align-items: flex-start;
    flex-direction: column;
    gap: 8px;
    padding: 10px 14px;
  }

  .work-flow-current,
  .work-flow-tools {
    width: 100%;
  }

  .work-flow-tools {
    justify-content: flex-start;
    overflow-x: auto;
  }

  .work-item-row {
    grid-template-columns: 66px 16px minmax(0, 1fr);
    padding: 10px 14px;
  }

  .work-item-row > span:nth-child(n+4) {
    display: none;
  }
}
.task-management-page {
  min-height: calc(100vh - var(--workspace-header-height, 72px));
  overflow: visible;
  padding: 0;
  color: var(--workspace-ink-700, #343a49);
  background-color: #ffffff;
  background-image: none;
}

.task-management-page .team-grid {
  opacity: 0.08;
  background-image:
    linear-gradient(rgba(249, 115, 22, 0.12) 1px, transparent 1px),
    linear-gradient(90deg, rgba(249, 115, 22, 0.12) 1px, transparent 1px);
}

.task-management-shell {
  position: relative;
  width: 100%;
  max-width: none;
  margin: 0;
  display: grid;
  gap: 18px;
  padding: 40px var(--ds-page-margin-x, 40px) 72px;
  padding-top: 40px;
}

.today-task-card,
.all-task-card,
.task-detail-card,
.task-overview-panel {
  border: 1px solid rgba(255, 255, 255, 0.78);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.76), rgba(255, 255, 255, 0.52));
  box-shadow: 0 12px 28px rgba(116, 71, 39, 0.055), inset 0 1px 0 rgba(255, 255, 255, 0.84);
  backdrop-filter: blur(18px) saturate(1.1);
  -webkit-backdrop-filter: blur(18px) saturate(1.1);
}

.task-management-hero {
  position: relative;
  z-index: 12;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 22px;
  padding: 2px 2px 12px;
  margin-bottom: -6px;
  overflow: visible;
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

.task-hero-copy h1,
.task-section-head h2,
.task-detail-card h2 {
  margin: 0;
  color: #111827;
}

.task-hero-copy h1 {
  font-size: clamp(22px, 1.45vw, 26px);
  line-height: 1.18;
  letter-spacing: -0.01em;
  font-weight: 800;
}

.task-hero-copy p {
  max-width: 760px;
  margin: 6px 0 0;
  color: var(--workspace-ink-500, #697386);
  font-size: 13px;
  line-height: 1.5;
  font-weight: 650;
}

.task-hero-actions {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 10px;
  padding-bottom: 3px;
}

.task-team-switcher {
  position: relative;
}

.task-team-switcher > button,
.task-primary-btn,
.simple-task-filters button,
.task-detail-actions button {
  border: 0;
  border-radius: 14px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 760;
  letter-spacing: 0;
}

.task-team-switcher > button {
  padding: 10px 13px;
  color: #4b5563;
  background: #fff7f2;
  font-size: 13px;
}

.task-primary-btn,
.task-detail-actions .primary {
  min-height: 42px;
  padding: 0 18px;
  color: #fff;
  background: linear-gradient(135deg, var(--workspace-orange-600, #f04b18), #ff7a45);
  box-shadow: 0 10px 20px rgba(240, 75, 24, 0.16), inset 0 1px 0 rgba(255, 255, 255, 0.24);
}

.task-section-head small,
.task-detail-meta span {
  color: #6b7280;
  font-size: 13px;
  font-weight: 800;
}

.today-task-card,
.all-task-card,
.task-detail-card {
  border-radius: 22px;
  padding: 18px;
}

.task-content-layout {
  display: grid;
  grid-template-columns: minmax(196px, 230px) minmax(520px, 1fr) minmax(268px, 300px);
  gap: 16px;
  align-items: start;
}

.task-overview-panel {
  position: sticky;
  top: 14px;
  border-radius: 22px;
  padding: 18px;
  display: grid;
  gap: 14px;
}

.task-overview-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.task-overview-head strong {
  color: var(--workspace-ink-900, #171a24);
  font-size: 16px;
  font-weight: 760;
}

.task-overview-head span {
  color: #9ca3af;
  font-size: 12px;
  font-weight: 800;
}

.task-overview-stats {
  display: grid;
  gap: 8px;
}

.task-overview-stats button {
  border: 0;
  border-radius: 12px;
  min-height: 42px;
  padding: 0 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: var(--workspace-ink-500, #697386);
  background: rgba(255, 255, 255, 0.56);
  font-size: 13px;
  font-weight: 760;
  cursor: pointer;
}

.task-overview-stats button.active,
.task-overview-stats button:hover {
  color: #ea580c;
  background: #fff1e8;
}

.task-overview-stats b {
  color: var(--workspace-ink-900, #171a24);
  font: 800 18px/1 var(--workspace-font-number, inherit);
}

.task-overview-note {
  border-top: 1px solid #f1e1d8;
  padding-top: 12px;
  display: grid;
  gap: 5px;
}

.task-overview-note strong {
  color: #111827;
  font-size: 13px;
}

.task-overview-note span {
  color: #8b93a1;
  font-size: 12px;
  line-height: 1.6;
}

.task-workspace-panel {
  display: grid;
  gap: 18px;
}

.task-section-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 16px;
}

.task-section-head h2 {
  font-size: 16px;
  line-height: 1.2;
  letter-spacing: 0;
  font-weight: 760;
}

.task-section-head p {
  margin: 5px 0 0;
  color: var(--workspace-ink-500, #697386);
  font-size: 12px;
  font-weight: 650;
}

.task-inline-summary {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.task-inline-summary span {
  padding: 5px 9px;
  border-radius: 999px;
  color: #6b7280;
  background: #fff7f2;
  font-size: 12px;
  font-weight: 800;
}

.today-task-grid,
.today-task-timeline {
  display: grid;
  gap: 8px;
}

.today-task-group {
  min-height: 0;
  border-radius: 16px;
  padding: 12px 14px;
  display: grid;
  grid-template-columns: 78px minmax(0, 1fr);
  gap: 12px;
  background: rgba(255, 250, 247, 0.76);
  border: 1px solid rgba(243, 222, 211, 0.7);
}

.today-task-group header {
  display: grid;
  align-content: start;
  gap: 4px;
  color: #111827;
}

.today-task-group-body {
  display: grid;
  gap: 8px;
}

.today-task-group header span {
  color: var(--workspace-orange-600, #f04b18);
  font-size: 11px;
  font-weight: 900;
}

.task-main-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(260px, 330px);
  gap: 14px;
  align-items: start;
}

.simple-task-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 14px;
}

.simple-task-filters button {
  min-height: 34px;
  padding: 0 12px;
  color: var(--workspace-ink-500, #697386);
  background: rgba(255, 255, 255, 0.6);
  font-size: 12px;
}

.simple-task-filters button.active {
  color: #fff;
  background: #111827;
}

.simple-task-list {
  display: grid;
  gap: 10px;
}

.simple-task-row {
  width: 100%;
  border: 1px solid rgba(240, 222, 213, 0.78);
  border-radius: 14px;
  padding: 12px 14px;
  display: grid;
  gap: 4px;
  color: var(--workspace-ink-700, #343a49);
  text-align: left;
  background: rgba(255, 255, 255, 0.72);
  cursor: pointer;
  transition: transform 160ms var(--workspace-ease, ease), border-color 160ms var(--workspace-ease, ease), box-shadow 160ms var(--workspace-ease, ease), background 160ms var(--workspace-ease, ease);
}

.simple-task-row:hover,
.simple-task-row.active {
  border-color: rgba(234, 88, 12, 0.48);
  box-shadow: 0 8px 18px rgba(234, 88, 12, 0.07);
}

.simple-task-row.expired {
  border-color: rgba(220, 38, 38, 0.35);
}

.simple-task-row.completed {
  border-color: rgba(148, 163, 184, 0.24);
  background: rgba(248, 250, 252, 0.68);
  box-shadow: none;
}

.simple-task-row.completed:hover,
.simple-task-row.completed.active {
  border-color: rgba(148, 163, 184, 0.4);
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.04);
}

.simple-task-row.completed .simple-task-title {
  color: #8a8f98;
  text-decoration: line-through;
  text-decoration-thickness: 1.5px;
  text-decoration-color: rgba(107, 114, 128, 0.75);
}

.simple-task-row.completed small {
  color: #8a8f98;
}

.simple-task-row.large {
  grid-template-columns: 34px minmax(0, 1fr) minmax(128px, auto);
  align-items: center;
  column-gap: 12px;
}

.simple-task-badge {
  width: 30px;
  height: 30px;
  border-radius: 10px;
  display: grid;
  place-items: center;
  color: #ea580c;
  background: #fff1e8;
  font-size: 13px;
  font-weight: 900;
}

.simple-task-title {
  min-width: 0;
  display: grid;
  gap: 3px;
  font-size: 14px;
  font-weight: 760;
}

.simple-task-title strong {
  font-size: 14px;
  line-height: 1.35;
  font-weight: 760;
}

.simple-task-title strong,
.simple-task-title small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.simple-task-row small,
.simple-task-meta small {
  color: var(--workspace-ink-500, #697386);
  font-size: 12px;
  font-weight: 620;
}

.simple-task-meta {
  display: grid;
  gap: 3px;
  text-align: right;
}

.simple-task-meta b,
.task-detail-status b {
  color: var(--workspace-orange-600, #f04b18);
  font-size: 12px;
  font-weight: 820;
}

.task-detail-card {
  position: sticky;
  top: 14px;
  display: grid;
  gap: 12px;
}

.task-detail-card h2 {
  font-size: 18px;
  line-height: 1.35;
  font-weight: 800;
}

.task-detail-card p {
  margin: 0;
  color: var(--workspace-ink-500, #697386);
  font-size: 13px;
  line-height: 1.65;
}

.task-detail-status {
  display: flex;
  justify-content: space-between;
  color: var(--workspace-ink-500, #697386);
  font-size: 12px;
  font-weight: 900;
}

.task-detail-status .warn {
  color: #dc2626;
}

.task-detail-meta {
  display: grid;
  gap: 8px;
}

.task-detail-meta div {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid #f3e2d9;
}

.task-detail-meta strong {
  color: var(--workspace-ink-900, #171a24);
  font-size: 13px;
  line-height: 1.35;
  text-align: right;
}

.task-detail-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.task-detail-actions button {
  padding: 9px 13px;
  color: #4b5563;
  background: #fff7f2;
  font-size: 13px;
}

.simple-empty {
  border-radius: 14px;
  padding: 14px;
  color: #9ca3af;
  background: rgba(255, 255, 255, 0.58);
  font-size: 13px;
  font-weight: 800;
  text-align: center;
}

.simple-empty.block {
  padding: 30px;
}

.task-management-page .task-team-switcher > button,
.task-management-page .task-primary-btn,
.task-management-page .simple-task-filters button,
.task-management-page .task-detail-actions button {
  min-height: 38px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 760;
}

.task-management-page .task-team-switcher > button {
  padding: 0 14px;
  border: 1px solid rgba(240, 75, 24, 0.24);
  color: var(--workspace-orange-700, #d94312);
  background: linear-gradient(135deg, rgba(255, 246, 239, 0.98), rgba(255, 224, 207, 0.92));
  box-shadow: 0 8px 18px rgba(240, 75, 24, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.74);
}

.task-management-page .task-team-switcher > button:hover,
.task-management-page .task-team-switcher > button.active {
  border-color: rgba(240, 75, 24, 0.42);
  color: #fff;
  background: linear-gradient(135deg, var(--workspace-orange-600, #f04b18), #ff7a45);
  box-shadow: 0 12px 24px rgba(240, 75, 24, 0.18), inset 0 1px 0 rgba(255, 255, 255, 0.24);
}

.task-management-page .project-switch-menu {
  z-index: 60;
  top: calc(100% + 8px);
  right: 0;
  left: auto;
  width: min(280px, calc(100vw - 40px));
  max-width: min(280px, calc(100vw - 40px));
  display: grid;
  gap: 6px;
  padding: 8px;
  border: 1px solid rgba(240, 222, 213, 0.9);
  border-radius: 14px;
  background: rgba(255, 253, 250, 0.98);
  box-shadow: 0 18px 34px rgba(116, 71, 39, 0.14);
  backdrop-filter: blur(18px) saturate(1.05);
  -webkit-backdrop-filter: blur(18px) saturate(1.05);
  transform: none;
}

.task-management-page .project-switch-menu button {
  width: 100%;
  max-width: none;
  height: 36px;
  border-radius: 10px;
  padding: 0 10px;
  background: transparent;
  color: #4b5563;
}

.task-management-page .project-switch-menu button:hover,
.task-management-page .project-switch-menu button.active {
  background: #fff1e8;
  color: var(--workspace-orange-700, #d94312);
}

.task-management-page .task-primary-btn,
.task-management-page .task-detail-actions .primary {
  padding: 0 18px;
  color: var(--orep-surface-raised, #fff);
  background: linear-gradient(135deg, var(--workspace-orange-600, #f04b18), #ff7a45);
}

.task-management-page .task-overview-panel,
.task-management-page .today-task-card,
.task-management-page .all-task-card,
.task-management-page .task-detail-card {
  border: 1px solid rgba(255, 255, 255, 0.78);
  border-radius: 22px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.78), rgba(255, 255, 255, 0.56));
  box-shadow: 0 12px 28px rgba(116, 71, 39, 0.055), inset 0 1px 0 rgba(255, 255, 255, 0.84);
}

.task-management-page .task-overview-panel {
  padding: 18px 16px 20px;
}

.task-management-page .task-overview-stats button {
  min-height: 42px;
  border-radius: 12px;
  padding: 0 10px;
  color: var(--orep-muted, #6b7280);
  background: rgba(255, 255, 255, 0.56);
  font-size: 13px;
}

.task-management-page .task-overview-stats button.active,
.task-management-page .task-overview-stats button:hover {
  color: var(--orep-orange, #ea580c);
  background: var(--orep-orange-wash, #fff1e8);
}

.task-management-page .all-task-card {
  padding: 0;
  overflow: hidden;
}

.task-management-page .all-task-card .task-section-head,
.task-management-page .all-task-card .simple-task-filters {
  min-height: 60px;
  margin: 0;
  padding: 0 18px;
  border-bottom: 1px solid var(--orep-border-soft, oklch(0.91 0.02 55));
}

.task-management-page .all-task-card .simple-task-filters {
  align-items: center;
  gap: 10px;
}

.task-management-page .all-task-card .simple-task-list {
  padding: 18px;
}

.task-management-page .simple-task-filters button {
  min-height: 34px;
  min-width: 62px;
  border: 1px solid rgba(229, 214, 205, 0.82);
  border-radius: 11px;
  padding: 0 14px;
  color: var(--orep-muted, #6b7280);
  background: oklch(0.982 0.004 55);
}

.task-management-page .simple-task-filters button.active {
  border-color: var(--orep-text-strong, #111827);
  color: var(--orep-surface-raised, #fff);
  background: var(--orep-text-strong, #111827);
}

.task-management-page .today-task-group {
  border: 1px solid rgba(243, 222, 211, 0.62);
  border-radius: 14px;
  background: rgba(255, 250, 247, 0.72);
}

.task-management-page .simple-task-row {
  min-height: 68px;
  border: 1px solid rgba(230, 214, 205, 0.72);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.78);
  box-shadow: 0 6px 16px rgba(116, 71, 39, 0.045);
}

.task-management-page .simple-task-row:hover,
.task-management-page .simple-task-row.active {
  transform: translateY(-1px);
  border-color: oklch(0.9 0.06 55);
  box-shadow: 0 12px 24px rgba(116, 71, 39, 0.09);
}

.task-management-page .simple-task-badge {
  width: 30px;
  height: 30px;
  border-radius: 999px;
  background: var(--orep-orange-soft, #ffe4d6);
  color: var(--orep-orange, #ea580c);
}

.task-management-page .simple-empty {
  border-radius: 7px;
  background: oklch(0.975 0.003 55);
  color: oklch(0.61 0.016 55);
}

.task-management-page .task-detail-status b {
  min-height: 27px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  padding: 0 10px;
  background: var(--orep-orange-soft, #ffe4d6);
  color: var(--orep-orange, #ea580c);
  font-size: 12px;
  font-weight: 880;
}

.task-management-page .task-detail-status .warn {
  color: #dc2626;
  background: #fee2e2;
}

.task-management-page .task-detail-actions button {
  padding: 0 16px;
  color: var(--orep-muted, #6b7280);
  background: oklch(0.982 0.004 55);
}

.task-drawer-overlay {
  position: fixed;
  inset: 0;
  z-index: 6200;
  display: flex;
  justify-content: flex-end;
  padding: 18px;
  background: rgba(20, 24, 32, 0.32);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}

.task-action-drawer {
  width: min(560px, 100%);
  max-height: calc(100vh - 36px);
  overflow: auto;
  border: 1px solid rgba(255, 255, 255, 0.82);
  border-radius: 22px;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  background:
    radial-gradient(circle at 100% 0%, rgba(255, 122, 69, 0.16), transparent 28%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(255, 249, 245, 0.92));
  box-shadow: 0 28px 70px rgba(84, 52, 32, 0.28);
}

.task-drawer-head,
.task-drawer-actions {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  padding: 20px;
}

.task-drawer-head {
  border-bottom: 1px solid rgba(240, 222, 213, 0.78);
}

.task-drawer-head span,
.task-panel-title span,
.task-info-grid span,
.task-requirement-panel span,
.task-history-row span,
.task-upload-field small,
.task-submit-guidance span {
  color: var(--workspace-ink-500, #697386);
  font-size: 12px;
  font-weight: 760;
}

.task-drawer-head h3 {
  margin: 6px 0;
  color: #111827;
  font-size: 22px;
  line-height: 1.25;
  font-weight: 820;
}

.task-drawer-head p {
  margin: 0;
  color: #697386;
  font-size: 13px;
  line-height: 1.65;
}

.task-drawer-head button,
.task-drawer-actions button,
.task-history-actions button {
  min-height: 36px;
  border: 1px solid rgba(229, 214, 205, 0.82);
  border-radius: 12px;
  padding: 0 14px;
  color: #4b5563;
  background: rgba(255, 255, 255, 0.68);
  cursor: pointer;
  font-size: 12px;
  font-weight: 800;
}

.task-drawer-body {
  display: grid;
  gap: 14px;
  padding: 18px 20px 6px;
}

.task-info-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.task-info-grid div,
.task-requirement-panel,
.task-history-row,
.task-submit-guidance {
  border: 1px solid rgba(240, 222, 213, 0.72);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.72);
}

.task-info-grid div {
  display: grid;
  gap: 5px;
  padding: 12px;
}

.task-info-grid strong,
.task-requirement-panel strong,
.task-history-row strong,
.task-submit-guidance strong {
  color: #111827;
  font-size: 13px;
  line-height: 1.45;
}

.task-requirement-panel {
  display: grid;
  gap: 10px;
  padding: 14px;
}

.task-requirement-panel div,
.task-panel-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.task-requirement-panel p {
  margin: 0;
  color: #697386;
  font-size: 13px;
  line-height: 1.7;
}

.task-requirement-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.task-requirement-tags span {
  border-radius: 999px;
  padding: 5px 9px;
  color: var(--workspace-orange-700, #d94312);
  background: #fff1e8;
}

.task-history-panel {
  display: grid;
  gap: 10px;
  order: 1;
}

.task-requirement-panel {
  order: 2;
}

.task-panel-title strong {
  color: #111827;
  font-size: 15px;
}

.task-history-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
  padding: 12px;
}

.task-history-row.is-focused-submission {
  border-color: rgba(46, 155, 103, 0.5);
  background: rgba(46, 155, 103, 0.07);
  box-shadow: 0 0 0 3px rgba(46, 155, 103, 0.08);
}

.task-history-row span em {
  display: inline-flex;
  margin-left: 7px;
  padding: 3px 7px;
  border-radius: 999px;
  color: #23794f;
  background: rgba(46, 155, 103, 0.12);
  font-size: 10px;
  font-style: normal;
  line-height: 1;
}

.task-history-row div:first-child {
  min-width: 0;
  display: grid;
  gap: 4px;
}

.task-history-row strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-history-row small {
  color: #8b93a1;
  font-size: 12px;
  line-height: 1.45;
}

.task-history-actions {
  display: flex;
  gap: 8px;
}

.task-history-assets {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 4px;
}

.task-history-assets button {
  min-height: 28px;
  max-width: 170px;
  border: 1px solid rgba(255, 214, 194, 0.88);
  border-radius: 999px;
  padding: 0 9px;
  overflow: hidden;
  color: var(--workspace-orange-700, #d94312);
  background: #fff7f1;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
  font-size: 11px;
  font-weight: 800;
}

.task-drawer-empty,
.task-submit-lock {
  border-radius: 12px;
  padding: 12px;
  color: #8b93a1;
  background: rgba(255, 255, 255, 0.62);
  font-size: 13px;
  font-weight: 760;
}

.task-drawer-actions {
  border-top: 1px solid rgba(240, 222, 213, 0.78);
}

.task-drawer-actions .primary,
.task-submit-form .primary {
  border-color: transparent;
  color: #fff;
  background: linear-gradient(135deg, var(--workspace-orange-600, #f04b18), #ff7a45);
  box-shadow: 0 10px 20px rgba(240, 75, 24, 0.16);
}

.task-drawer-actions button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.task-submit-form {
  display: grid;
  gap: 14px;
  padding: 18px 20px 0;
}

.task-submit-guidance {
  display: grid;
  gap: 5px;
  padding: 13px 14px;
}

.task-submit-form label {
  display: grid;
  gap: 8px;
  color: #111827;
  font-size: 13px;
  font-weight: 800;
}

.task-submit-form textarea,
.task-submit-form input,
.task-submit-form select {
  width: 100%;
  border: 1px solid rgba(229, 214, 205, 0.92);
  border-radius: 12px;
  padding: 11px 12px;
  color: #111827;
  background: rgba(255, 255, 255, 0.78);
  font: inherit;
  font-size: 13px;
  outline: none;
}

.task-submit-form textarea:focus,
.task-submit-form input:focus,
.task-submit-form select:focus {
  border-color: rgba(240, 75, 24, 0.42);
  box-shadow: 0 0 0 3px rgba(240, 75, 24, 0.08);
}

.submission-type-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 8px;
}

.submission-type-grid button {
  min-height: 68px;
  border: 1px solid rgba(229, 214, 205, 0.84);
  border-radius: 14px;
  display: grid;
  align-content: center;
  gap: 4px;
  padding: 10px;
  color: #111827;
  background: rgba(255, 255, 255, 0.66);
  cursor: pointer;
  text-align: left;
}

.submission-type-grid button.active {
  border-color: rgba(240, 75, 24, 0.44);
  background: linear-gradient(180deg, #fff3ea, #fff);
  box-shadow: 0 10px 24px rgba(240, 75, 24, 0.1);
}

.submission-type-grid strong {
  font-size: 13px;
  font-weight: 860;
}

.submission-type-grid span,
.submission-subhead span,
.submission-file-row span,
.submission-sync-toggle small {
  color: #8b93a1;
  font-size: 11px;
  line-height: 1.35;
  font-weight: 720;
}

.submission-links-panel,
.submission-file-list {
  display: grid;
  gap: 10px;
}

.submission-subhead {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.submission-subhead strong {
  display: block;
  color: #111827;
  font-size: 13px;
  font-weight: 850;
}

.submission-subhead button,
.submission-link-row button,
.submission-file-row button {
  min-height: 34px;
  border: 1px solid rgba(229, 214, 205, 0.84);
  border-radius: 11px;
  padding: 0 12px;
  color: #4b5563;
  background: rgba(255, 255, 255, 0.72);
  cursor: pointer;
  font-size: 12px;
  font-weight: 800;
}

.submission-link-list {
  display: grid;
  gap: 8px;
}

.submission-link-row {
  display: grid;
  grid-template-columns: 118px minmax(0, 0.7fr) minmax(0, 1.3fr) auto;
  gap: 8px;
}

.submission-file-row {
  border: 1px solid rgba(240, 222, 213, 0.74);
  border-radius: 13px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  background: rgba(255, 255, 255, 0.7);
}

.submission-file-row div {
  min-width: 0;
  display: grid;
  gap: 3px;
}

.submission-file-row strong {
  overflow: hidden;
  color: #111827;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
}

.submission-sync-toggle {
  border: 1px solid rgba(229, 214, 205, 0.9);
  border-radius: 14px;
  display: grid;
  gap: 4px;
  padding: 12px 14px;
  color: #697386;
  background: rgba(255, 255, 255, 0.7);
  cursor: pointer;
  text-align: left;
}

.submission-sync-toggle.active {
  border-color: rgba(52, 211, 153, 0.36);
  color: #047857;
  background: #ecfdf5;
}

.submission-sync-toggle span {
  font-size: 13px;
  font-weight: 860;
}

.task-upload-field {
  border: 1px dashed rgba(240, 75, 24, 0.36);
  border-radius: 14px;
  padding: 14px;
  background: rgba(255, 241, 232, 0.5);
  cursor: pointer;
}

.task-upload-field input {
  display: none;
}

.task-upload-field > span {
  color: var(--workspace-orange-700, #d94312);
}

@media (max-width: 1023px) {
  .task-management-page {
    padding: 0;
  }

  .task-management-shell {
    width: min(100% - 28px, 720px);
    padding: 22px 0 96px;
  }

  .task-management-hero,
  .task-main-grid,
  .task-content-layout {
    grid-template-columns: 1fr;
  }

  .task-management-hero {
    display: grid;
    padding: 8px 2px 18px;
  }

  .task-management-hero::after {
    width: 100%;
    opacity: 0.45;
  }

  .task-summary-grid,
  .today-task-grid,
  .today-task-timeline {
    grid-template-columns: 1fr;
  }

  .task-overview-panel,
  .task-detail-card {
    position: static;
  }

  .task-overview-stats {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .today-task-group {
    grid-template-columns: 1fr;
  }

  .simple-task-row.large {
    grid-template-columns: 34px minmax(0, 1fr);
  }

  .simple-task-meta {
    grid-column: 2;
    text-align: left;
  }

  .task-detail-card {
    position: static;
  }

  .task-create-layout {
    grid-template-columns: 1fr;
  }

  .task-type-picker > div {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 1279px) {
  .task-management-shell {
    width: 100%;
  }

  .task-content-layout {
    grid-template-columns: minmax(190px, 220px) minmax(0, 1fr);
  }

  .task-detail-card {
    position: static;
    grid-column: 1 / -1;
  }

  .task-detail-meta {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 1023px) {
  .task-content-layout {
    grid-template-columns: 1fr;
  }

  .task-detail-card {
    grid-column: auto;
  }

  .task-detail-meta {
    grid-template-columns: 1fr;
  }
}

/* Collaboration refresh: follow the solid, restrained page language used by
   the home and training modules. */
.task-management-page {
  background: transparent;
}

.task-management-page .team-grid {
  display: none;
}

.task-management-shell {
  gap: var(--ds-space-5, 20px);
  padding: 40px var(--ds-page-margin-x, 40px) 72px;
  padding-top: 40px;
}

.task-management-hero {
  align-items: center;
  margin: 0;
  padding: 0 0 var(--ds-space-1, 4px);
}

.task-hero-copy h1 {
  font-size: var(--ds-text-h1, 24px);
  line-height: 1.2;
  font-weight: var(--ds-weight-bold, 760);
}

.task-hero-copy p {
  margin-top: 7px;
  color: var(--ds-muted, #6b7280);
  font-weight: var(--ds-weight-medium, 560);
}

.task-content-layout {
  grid-template-columns: minmax(0, 1fr) minmax(272px, 292px);
  grid-template-rows: auto auto;
  gap: var(--ds-space-5, 20px);
}

.task-overview-panel {
  position: static;
  grid-column: 1;
  grid-row: 1;
  padding: var(--ds-space-5, 20px);
}

.task-workspace-panel {
  grid-column: 1;
  grid-row: 2;
  gap: var(--ds-space-5, 20px);
}

.task-detail-card {
  grid-column: 2;
  grid-row: 1 / span 2;
  top: var(--ds-space-5, 20px);
  gap: var(--ds-space-4, 16px);
  padding: var(--ds-space-6, 24px);
}

.task-management-page .task-overview-panel,
.task-management-page .today-task-card,
.task-management-page .all-task-card,
.task-management-page .task-detail-card {
  border: 1px solid var(--ds-card-border, #e5e7eb);
  border-radius: var(--ds-radius-lg, 16px);
  background: var(--ds-card-bg, #fff);
  box-shadow: var(--ds-card-shadow, 2px 4px 12px rgba(18, 20, 26, 0.08));
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
}

.task-management-page .today-task-card {
  padding: var(--ds-space-6, 24px);
}

.task-overview-head strong,
.task-section-head h2 {
  font-size: var(--ds-text-h3, 17px);
  color: var(--ds-ink, #12141a);
}

.task-overview-stats {
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--ds-space-3, 12px);
}

.task-management-page .task-overview-stats button {
  min-height: 64px;
  padding: 10px 12px;
  border: 1px solid var(--ds-line-soft, #eceef2);
  border-radius: var(--ds-radius-md, 12px);
  background: var(--ds-surface-subtle, #f8f9fb);
}

.task-management-page .task-overview-stats button.active,
.task-management-page .task-overview-stats button:hover {
  border-color: var(--ds-orange-100, #fee9df);
  color: var(--ds-orange-700, #d94312);
  background: var(--ds-orange-50, #fff7f2);
}

.task-overview-stats b {
  font-size: 20px;
}

.task-overview-note {
  padding-top: var(--ds-space-3, 12px);
  border-top-color: var(--ds-line-soft, #eceef2);
}

.today-task-timeline {
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--ds-space-3, 12px);
}

.task-management-page .today-task-group {
  grid-template-columns: 1fr;
  align-content: start;
  padding: var(--ds-space-4, 16px);
  border-color: var(--ds-line-soft, #eceef2);
  background: var(--ds-surface-subtle, #f8f9fb);
}

.today-task-group .simple-task-title {
  display: -webkit-box;
  overflow: hidden;
  white-space: normal;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.task-management-page .simple-task-row {
  min-height: 64px;
  border-color: var(--ds-line-soft, #eceef2);
  background: var(--ds-card-bg, #fff);
  box-shadow: none;
}

.task-management-page .simple-task-row:hover,
.task-management-page .simple-task-row.active {
  transform: none;
  border-color: var(--ds-orange-200, #fdcdb8);
  background: var(--ds-orange-50, #fff7f2);
  box-shadow: none;
}

.task-management-page .task-team-switcher > button,
.task-management-page .task-detail-actions button {
  border: 1px solid var(--ds-btn-secondary-border, #d9dde5);
  color: var(--ds-btn-secondary-fg, #343944);
  background: var(--ds-btn-secondary-bg, #fff);
  box-shadow: none;
}

.task-management-page .task-team-switcher > button:hover,
.task-management-page .task-team-switcher > button.active,
.task-management-page .task-detail-actions button:hover {
  border-color: var(--ds-btn-secondary-border-hover, #c8cdd7);
  color: var(--ds-ink, #12141a);
  background: var(--ds-btn-secondary-bg-hover, #f7f8fa);
  box-shadow: none;
}

.task-management-page .task-primary-btn,
.task-management-page .task-detail-actions .primary {
  border-color: var(--ds-orange-700, #d94312);
  color: #fff;
  background: var(--ds-orange-700, #d94312);
  box-shadow: none;
}

.task-management-page .task-primary-btn:hover,
.task-management-page .task-detail-actions .primary:hover {
  border-color: var(--ds-orange-800, #b12f0a);
  color: #fff;
  background: var(--ds-orange-800, #b12f0a);
}

.task-detail-meta div {
  border-bottom-color: var(--ds-line-soft, #eceef2);
}

.task-management-page .project-switch-menu {
  border-color: var(--ds-card-border, #e5e7eb);
  border-radius: var(--ds-radius-md, 12px);
  background: var(--ds-card-bg, #fff);
  box-shadow: var(--ds-shadow-popover, 0 16px 36px rgba(18, 20, 26, 0.14));
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
}

@media (max-width: 1180px) {
  .task-content-layout {
    grid-template-columns: 1fr;
  }

  .task-overview-panel,
  .task-workspace-panel,
  .task-detail-card {
    position: static;
    grid-column: 1;
    grid-row: auto;
  }

  .task-detail-meta {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .task-management-shell {
    width: 100%;
    padding: 24px 16px 72px;
  }

  .task-management-hero {
    display: grid;
    gap: 16px;
  }

  .task-hero-actions {
    width: 100%;
  }

  .task-primary-btn {
    flex: 1;
  }

  .task-overview-stats {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .today-task-timeline,
  .task-detail-meta {
    grid-template-columns: 1fr;
  }

  .task-management-page .all-task-card .task-section-head,
  .task-management-page .all-task-card .simple-task-filters,
  .task-management-page .all-task-card .simple-task-list {
    padding-right: 16px;
    padding-left: 16px;
  }

  .task-management-page .all-task-card .simple-task-filters {
    min-height: auto;
    padding-top: 12px;
    padding-bottom: 12px;
  }
}

/* Focused collaboration task queue */
.focused-task-shell {
  gap: var(--ds-space-5, 20px);
  padding: 0 0 var(--ds-space-6, 24px);
  background: transparent;
}

.focused-task-shell .task-management-hero {
  min-height: 54px;
  padding: 0;
  margin: 0;
}

.focused-task-shell .task-primary-btn,
.focused-task-shell .task-team-switcher > button {
  box-sizing: border-box;
  min-height: var(--ds-btn-height, 40px);
  padding: 0 var(--ds-btn-padding-x, 18px);
  border-radius: var(--ds-radius-pill, 999px);
  font-size: var(--ds-btn-font, 13px);
  font-weight: var(--ds-weight-bold, 700);
  line-height: 1;
  box-shadow: none;
  transition: color var(--ds-control-transition, 160ms ease), background-color var(--ds-control-transition, 160ms ease), border-color var(--ds-control-transition, 160ms ease);
}

.focused-task-shell .task-primary-btn {
  border: 1px solid var(--ds-btn-primary-bg, #c93b16);
  color: var(--ds-btn-primary-fg, #fff);
  background: var(--ds-btn-primary-bg, #c93b16);
}

.focused-task-shell .task-primary-btn:hover {
  border-color: var(--ds-btn-primary-bg-hover, #b53212);
  background: var(--ds-btn-primary-bg-hover, #b53212);
}

.focused-task-shell .task-team-switcher > button {
  border: 1px solid var(--ds-btn-secondary-border, #dedbd7);
  color: var(--ds-btn-secondary-fg, #24272e);
  background: var(--ds-btn-secondary-bg, #fff);
}

.focused-task-shell .task-team-switcher > button:hover,
.focused-task-shell .task-team-switcher > button.active {
  border-color: var(--ds-btn-secondary-border-hover, #efa789);
  color: var(--ds-orange-500, #e84a1c);
  background: var(--ds-btn-secondary-bg-hover, #fffaf7);
}

.focused-task-shell .task-primary-btn:focus-visible,
.focused-task-shell .task-team-switcher > button:focus-visible,
.focused-source-filters button:focus-visible {
  outline: var(--ds-focus-outline, 2px solid #e84a1c);
  outline-offset: var(--ds-focus-offset, 2px);
}

.focused-task-overview {
  display: flex;
  align-items: center;
  min-height: 68px;
  padding: 12px 20px;
  border: 1px solid var(--ds-card-border, #e7e8ec);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.88);
  box-shadow: 0 4px 14px rgba(25, 29, 38, 0.04);
}

.focused-task-metric {
  display: grid;
  grid-template-columns: auto auto;
  align-items: baseline;
  gap: 8px;
  min-width: 108px;
  padding: 0 20px;
  border-right: 1px solid var(--ds-line-soft, #eceef2);
}

.focused-task-metric:first-child {
  padding-left: 0;
}

.focused-task-metric strong {
  color: var(--ds-ink, #16181d);
  font-size: 24px;
  line-height: 1;
  font-weight: 750;
  letter-spacing: -0.04em;
}

.focused-task-metric span {
  color: var(--ds-muted, #777d89);
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
}

.focused-task-overview > p {
  margin: 0 0 0 auto;
  padding-left: 22px;
  color: var(--ds-muted, #737986);
  font-size: 13px;
  line-height: 1.6;
  text-align: right;
}

.focused-task-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  align-items: start;
  gap: 20px;
}

.focused-task-queue,
.focused-task-detail {
  border: 1px solid var(--ds-card-border, #e5e7eb);
  border-radius: var(--ds-radius-lg, 16px);
  background: var(--ds-card-bg, #fff);
  box-shadow: 0 7px 24px rgba(22, 24, 29, 0.055);
}

.focused-task-queue {
  min-width: 0;
  overflow: hidden;
}

.focused-task-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 22px 24px 18px;
}

.focused-task-toolbar h2,
.focused-task-detail h2 {
  margin: 0;
  color: var(--ds-ink, #16181d);
  font-size: 18px;
  line-height: 1.35;
  font-weight: 720;
}

.focused-task-toolbar p {
  margin: 5px 0 0;
  color: var(--ds-muted, #7a808c);
  font-size: 12px;
}

.focused-task-search {
  display: flex;
  align-items: center;
  gap: 8px;
  width: min(240px, 40%);
  min-height: 38px;
  padding: 0 12px;
  border: 1px solid var(--ds-line-soft, #e5e7eb);
  border-radius: 10px;
  background: var(--ds-surface-subtle, #f8f9fb);
  transition: border-color 160ms ease, box-shadow 160ms ease, background 160ms ease;
}

.focused-task-search:focus-within {
  border-color: var(--ds-orange-300, #f7a17c);
  background: #fff;
  box-shadow: 0 0 0 3px rgba(234, 77, 28, 0.09);
}

.focused-task-search svg {
  width: 17px;
  height: 17px;
  flex: none;
  fill: none;
  stroke: #8a909c;
  stroke-width: 1.7;
  stroke-linecap: round;
}

.focused-task-search input {
  width: 100%;
  min-width: 0;
  padding: 0;
  border: 0;
  outline: 0;
  color: var(--ds-ink, #16181d);
  background: transparent;
  font: inherit;
  font-size: 13px;
}

.focused-source-filters {
  display: flex;
  gap: 2px;
  width: fit-content;
  max-width: calc(100% - 48px);
  margin: 0 24px 17px;
  padding: 4px;
  border: 1px solid var(--ds-line, #e8e3dc);
  border-radius: var(--ds-radius-md, 12px);
  background: var(--ds-surface-subtle, #f7f4f0);
  overflow-x: auto;
  scrollbar-width: none;
}

.focused-source-filters::-webkit-scrollbar {
  display: none;
}

.focused-source-filters button {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  min-height: 36px;
  padding: 0 13px;
  border: 0;
  border-radius: var(--ds-radius-sm, 8px);
  color: #666d78;
  background: transparent;
  font-size: 12px;
  font-weight: 650;
  white-space: nowrap;
  cursor: pointer;
}

.focused-source-filters button:hover {
  color: var(--ds-ink, #1f2430);
  background: rgba(255, 255, 255, 0.56);
}

.focused-source-filters button.active {
  color: var(--ds-ink, #1f2430);
  background: #fff;
  box-shadow: 0 3px 10px rgba(45, 36, 29, 0.08);
}

.focused-source-filters em {
  min-width: 0;
  height: auto;
  padding: 0;
  border-radius: 0;
  color: #8b9099;
  background: transparent;
  font-size: 10px;
  line-height: 1;
  font-style: normal;
  text-align: center;
}

.focused-source-filters button.active em {
  color: var(--ds-orange-500, #e84a1c);
  background: transparent;
}

.focused-task-groups {
  padding: 4px 0 12px;
}

.focused-task-group + .focused-task-group {
  border-top: 1px solid var(--ds-line-soft, #eceef2);
}

.focused-task-group > header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 17px 24px 10px;
}

.focused-task-group > header > div {
  display: flex;
  align-items: center;
  gap: 8px;
}

.focused-task-group h3 {
  margin: 0;
  color: #282c34;
  font-size: 13px;
  font-weight: 720;
}

.focused-task-group header b {
  display: grid;
  place-items: center;
  min-width: 19px;
  height: 19px;
  padding: 0 5px;
  border-radius: 999px;
  color: #747a86;
  background: #f0f2f4;
  font-size: 10px;
}

.focused-task-group header p {
  margin: 0;
  color: #969ba4;
  font-size: 11px;
}

.focused-group-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #a4a9b2;
}

.focused-group-dot.danger { background: #e24b2b; box-shadow: 0 0 0 4px #fff0eb; }
.focused-group-dot.today { background: #e48a28; box-shadow: 0 0 0 4px #fff5e9; }
.focused-group-dot.next { background: #6b7b94; box-shadow: 0 0 0 4px #eef2f8; }
.focused-group-dot.done { background: #48a073; box-shadow: 0 0 0 4px #ebf7f0; }

.focused-task-list {
  padding: 0 12px 10px;
}

.focused-task-row {
  position: relative;
  display: grid;
  grid-template-columns: 38px minmax(190px, 1fr) minmax(76px, 0.34fr) 78px auto 16px;
  align-items: center;
  gap: 13px;
  width: 100%;
  min-height: 78px;
  padding: 10px 12px;
  border: 1px solid transparent;
  border-radius: 11px;
  color: inherit;
  background: transparent;
  text-align: left;
  cursor: pointer;
  transition: background 150ms ease, border-color 150ms ease;
}

.focused-task-row + .focused-task-row {
  margin-top: 2px;
}

.focused-task-row:hover {
  background: #f8f9fa;
}

.focused-task-row.active {
  border-color: #f4cbbb;
  background: #fff8f4;
}

.focused-task-row.completed {
  opacity: 0.72;
}

.focused-task-row.locked {
  cursor: not-allowed;
  opacity: 0.92;
  background: #f8fafc;
}

.focused-task-row.locked:hover {
  background: #f1f5f9;
  border-color: transparent;
}

.focused-source-icon.locked {
  color: #64748b;
  background: #e2e8f0;
}

.focused-lock-icon {
  width: 16px;
  height: 16px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
}

.focused-task-status.locked {
  color: #64748b;
  background: #e2e8f0;
}

.focused-row-lock-label {
  color: #94a3b8;
  font-size: 11px;
  font-weight: 700;
}

.focused-source-icon {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  border-radius: 10px;
  color: #565e6b;
  background: #f0f2f5;
  font-size: 12px;
  font-weight: 750;
}

.focused-source-icon.source-training {
  color: #d84818;
  background: #fff0e9;
}

.focused-source-icon.source-score {
  color: #8b5cba;
  background: #f5edfc;
}

.focused-source-icon.source-team {
  color: #4d6888;
  background: #edf2f8;
}

.focused-task-main {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 4px;
}

.focused-task-labels {
  display: flex;
  align-items: center;
  gap: 7px;
}

.focused-task-labels em,
.focused-task-labels i {
  color: #7b818c;
  font-size: 10px;
  line-height: 1.2;
  font-style: normal;
  font-weight: 620;
}

.focused-task-labels i {
  color: #d14a20;
}

.focused-task-main > strong,
.focused-task-owner strong,
.focused-task-due strong {
  overflow: hidden;
  color: #242830;
  font-size: 13px;
  font-weight: 680;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.focused-task-main > small {
  overflow: hidden;
  color: #858b96;
  font-size: 11px;
  line-height: 1.45;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.focused-task-owner,
.focused-task-due {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 5px;
}

.focused-task-owner small,
.focused-task-due small {
  color: #9a9fa8;
  font-size: 10px;
}

.focused-task-owner strong,
.focused-task-due strong {
  font-size: 11px;
  font-weight: 620;
}

.focused-task-status {
  justify-self: end;
  padding: 6px 9px;
  border-radius: 999px;
  color: #536172;
  background: #eef2f5;
  font-size: 10px;
  font-weight: 680;
  white-space: nowrap;
}

.focused-task-status.warning {
  color: #d14317;
  background: #fff0e9;
}

.focused-row-arrow {
  width: 15px;
  height: 15px;
  fill: none;
  stroke: #b0b4bc;
  stroke-width: 1.7;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.focused-task-empty {
  display: grid;
  justify-items: center;
  padding: 72px 24px 80px;
  color: #7e8490;
  text-align: center;
}

.focused-task-empty span {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  margin-bottom: 14px;
  border-radius: 50%;
  color: #4d9c72;
  background: #edf8f2;
  font-size: 20px;
}

.focused-task-empty strong { color: #353a43; font-size: 14px; }
.focused-task-empty p { margin: 7px 0 0; font-size: 12px; }

.focused-task-detail {
  position: sticky;
  top: 20px;
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 22px;
}

.focused-detail-kicker {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.focused-detail-kicker span,
.focused-detail-kicker b {
  padding: 6px 9px;
  border-radius: 999px;
  color: #566376;
  background: #eef2f6;
  font-size: 10px;
  font-weight: 680;
}

.focused-detail-kicker span {
  color: #d44717;
  background: #fff0e9;
}

.focused-detail-kicker b.warning {
  color: #ca4118;
  background: #fff0e9;
}

.focused-task-detail h2 {
  font-size: 19px;
  line-height: 1.45;
}

.focused-detail-summary {
  margin: -8px 0 0;
  color: #737985;
  font-size: 12px;
  line-height: 1.7;
}

.focused-detail-alert {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px;
  border: 1px solid #f6d3c5;
  border-radius: 10px;
  color: #9b4327;
  background: #fff8f4;
  font-size: 11px;
  line-height: 1.55;
}

.focused-detail-alert svg {
  width: 18px;
  height: 18px;
  flex: none;
  fill: none;
  stroke: #dc572f;
  stroke-width: 1.7;
  stroke-linecap: round;
}

.focused-detail-alert span { display: grid; gap: 2px; }
.focused-detail-alert strong { color: #753522; }

.focused-detail-meta {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 18px;
  margin: 0;
  padding: 0;
  border-top: 1px solid var(--ds-line-soft, #eceef2);
}

.focused-detail-meta div {
  display: grid;
  gap: 5px;
  min-width: 0;
  padding: 13px 0;
  border-bottom: 1px solid var(--ds-line-soft, #eceef2);
}

.focused-detail-meta dt {
  color: #979ca6;
  font-size: 10px;
}

.focused-detail-meta dd {
  overflow: hidden;
  margin: 0;
  color: #30343c;
  font-size: 11px;
  font-weight: 650;
  line-height: 1.4;
  text-overflow: ellipsis;
}

.focused-submission-summary {
  padding: 14px;
  border: 1px solid #e7e9ed;
  border-radius: 11px;
  background: #f8f9fa;
}

.focused-submission-summary div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.focused-submission-summary span { color: #838995; font-size: 11px; }
.focused-submission-summary strong { color: #30343c; font-size: 12px; }
.focused-submission-summary p { margin: 8px 0 0; color: #858b96; font-size: 10px; line-height: 1.55; }

.focused-detail-actions {
  display: grid;
  gap: 9px;
}

.focused-detail-actions button {
  min-height: 40px;
  padding: 0 14px;
  border: 1px solid #dfe2e7;
  border-radius: 10px;
  color: #3d424b;
  background: #fff;
  font-size: 12px;
  font-weight: 680;
  cursor: pointer;
}

.focused-detail-actions button:hover {
  border-color: #cfd3da;
  background: #f8f9fa;
}

.focused-detail-actions button.primary {
  border-color: var(--ds-orange-700, #d94312);
  color: #fff;
  background: var(--ds-orange-700, #d94312);
}

.focused-detail-actions button.primary:hover {
  border-color: var(--ds-orange-800, #b12f0a);
  background: var(--ds-orange-800, #b12f0a);
}

.project-task-detail-page {
  --project-task-orange: var(--ds-orange-action, #e84a1c);
  --project-task-line: var(--ds-line, #e8e3dc);
  max-width: none;
  padding: 0 0 var(--ds-space-6, 24px);
}

.project-task-detail-head {
  margin: 0 0 var(--ds-space-5, 20px);
  align-items: flex-end;
}

.project-task-detail-head-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--ds-space-3, 12px);
}

.project-task-back,
.project-task-head-action {
  box-sizing: border-box;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  min-height: var(--ds-btn-height, 40px);
  padding: 0 var(--ds-btn-padding-x, 18px);
  border: 1px solid var(--ds-btn-secondary-border, #dedbd7);
  border-radius: var(--ds-radius-pill, 999px);
  color: var(--ds-ink, #1f2430);
  background: var(--ds-btn-secondary-bg, #fff);
  font: inherit;
  font-size: var(--ds-btn-font, 13px);
  font-weight: 700;
  line-height: 1;
  cursor: pointer;
  transition: color 160ms ease, border-color 160ms ease, background-color 160ms ease;
}

.project-task-back:hover,
.project-task-head-action:hover {
  border-color: var(--ds-btn-secondary-border-hover, #efa789);
  color: var(--project-task-orange);
  background: var(--ds-btn-secondary-bg-hover, #fffaf7);
}

.project-task-head-action.primary {
  border-color: var(--ds-btn-primary-bg, #c93b16);
  color: var(--ds-btn-primary-fg, #fff);
  background: var(--ds-btn-primary-bg, #c93b16);
}

.project-task-head-action.primary:hover {
  border-color: var(--ds-btn-primary-bg-hover, #b53212);
  color: var(--ds-btn-primary-fg, #fff);
  background: var(--ds-btn-primary-bg-hover, #b53212);
}

.project-task-back svg {
  width: 18px;
  height: 18px;
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.8;
}

.project-task-not-found {
  display: grid;
  justify-items: start;
  gap: 10px;
  padding: 48px;
}

.project-task-not-found strong {
  color: var(--ds-ink, #16181d);
  font-size: 22px;
}

.project-task-not-found p {
  margin: 0;
  color: var(--ds-muted, #777d89);
}

.project-task-not-found button {
  min-height: 40px;
  margin-top: 10px;
  padding: 0 18px;
  border: 0;
  border-radius: 10px;
  color: #fff;
  background: var(--ds-orange-700, #d94312);
  font-weight: 680;
  cursor: pointer;
}

.project-task-detail-tags {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: var(--ds-space-4, 16px);
}

.project-task-detail-tags span,
.project-task-detail-tags b {
  display: inline-flex;
  align-items: center;
  min-height: 25px;
  padding: 0 9px;
  border-radius: 999px;
  font-size: 11px;
  font-style: normal;
  font-weight: 680;
}

.project-task-detail-tags span {
  color: var(--ds-orange-700, #d94312);
  background: var(--ds-orange-50, #fff3ee);
}

.project-task-detail-tags b {
  color: #5b626e;
  background: #f0f2f4;
}

.project-task-detail-tags b.warning {
  color: #b53a16;
  background: #fff0e9;
}

.project-task-detail-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.68fr) minmax(320px, 0.92fr);
  align-items: start;
  gap: var(--ds-space-5, 20px);
}

.project-task-detail-main,
.project-task-detail-aside {
  display: grid;
  gap: 20px;
  min-width: 0;
}

.project-task-detail-main > *,
.project-task-detail-aside > *,
.project-task-section,
.project-version-editor {
  box-sizing: border-box;
  min-width: 0;
  max-width: 100%;
}

.project-task-section,
.project-task-detail-aside > section {
  border: 1px solid var(--ds-card-border, rgba(29, 29, 31, 0.07));
  border-radius: var(--ds-radius-lg, 16px);
  background: var(--ds-card-bg, #fff);
  box-shadow: var(--ds-card-shadow, 0 1px 2px rgba(29, 29, 31, 0.025), 0 10px 28px rgba(29, 29, 31, 0.055));
}

.project-task-section {
  padding: var(--ds-space-6, 24px);
}

.project-task-section > header {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 0;
  margin-bottom: var(--ds-space-5, 20px);
  padding: 0;
  border: 0;
}

.project-task-section > header > span {
  width: 4px;
  height: 22px;
  border-radius: var(--ds-radius-pill, 999px);
  background: var(--project-task-orange);
}

.project-task-section > header h2,
.project-task-detail-aside h2 {
  margin: 0;
  color: var(--ds-ink, #16181d);
  font-size: 16px;
  line-height: 1.4;
}

.project-task-section > header p {
  margin: 5px 0 0;
  color: var(--ds-muted, #858b96);
  font-size: var(--ds-text-micro, 11px);
  line-height: 1.5;
}

.project-task-section-body {
  padding: 0;
}

.project-task-title-block > span {
  color: var(--ds-muted, #777d89);
  font-size: var(--ds-text-micro, 11px);
  font-weight: 700;
}

.project-task-title-block h3 {
  margin: 5px 0 0;
  color: var(--ds-ink, #16181d);
  font-size: clamp(22px, 1.8vw, 28px);
  line-height: 1.28;
  letter-spacing: -0.02em;
}

.project-task-book-summary {
  margin-top: var(--ds-space-5, 20px);
  padding-top: var(--ds-space-5, 20px);
  border-top: 1px solid var(--project-task-line);
}

.project-task-book-summary h4 {
  margin: 0 0 var(--ds-space-3, 12px);
  color: var(--ds-ink, #16181d);
  font-size: 14px;
}

.project-task-book-summary p {
  margin: 0;
  color: var(--ds-muted, #6f7581);
  font-size: 14px;
  line-height: 1.75;
  white-space: pre-line;
}

.project-task-book-toggle {
  width: 100%;
  min-height: 58px;
  margin-top: var(--ds-space-5, 20px);
  padding: var(--ds-space-3, 12px) 0;
  border: 0;
  border-top: 1px solid var(--project-task-line);
  border-bottom: 1px solid var(--project-task-line);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--ds-space-4, 16px);
  color: var(--ds-ink, #16181d);
  background: transparent;
  text-align: left;
  cursor: pointer;
}

.project-task-book-toggle > span {
  display: grid;
  gap: 3px;
}

.project-task-book-toggle strong {
  font-size: 13px;
  font-weight: 760;
}

.project-task-book-toggle small {
  color: var(--ds-muted, #777d89);
  font-size: 11px;
}

.project-task-book-toggle svg {
  width: 18px;
  height: 18px;
  flex: 0 0 auto;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
  transition: transform 160ms ease;
}

.project-task-book-toggle[aria-expanded="true"] svg {
  transform: rotate(180deg);
}

.project-task-book-toggle:hover,
.project-task-book-toggle:focus-visible {
  color: var(--project-task-orange);
}

.project-task-book-toggle:focus-visible {
  outline: var(--ds-focus-outline, 2px solid #f04b18);
  outline-offset: var(--ds-focus-offset, 2px);
}

.project-task-book-details {
  display: flow-root;
}

.project-task-book-section {
  margin-top: var(--ds-space-5, 20px);
  padding-top: var(--ds-space-5, 20px);
  border-top: 1px solid var(--project-task-line);
}

.project-task-book-section > h4 {
  margin: 0 0 var(--ds-space-3, 12px);
  color: var(--ds-ink, #16181d);
  font-size: 14px;
}

.project-task-book-state {
  margin-top: var(--ds-space-5, 20px);
  padding: var(--ds-space-4, 16px);
  border: 1px solid var(--ds-line, #e8e3dc);
  border-radius: var(--ds-radius-md, 12px);
  color: var(--ds-muted, #6f7581);
  background: var(--ds-input-readonly-bg, #f8f9fa);
  font-size: 13px;
}

.project-task-book-state.error {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--ds-space-3, 12px);
  color: var(--ds-status-danger-fg, #b42332);
  background: var(--ds-status-danger-bg, #fff1f2);
}

.project-task-book-state button {
  min-height: 34px;
  padding: 0 14px;
  border: 1px solid var(--ds-btn-secondary-border, #dedbd7);
  border-radius: var(--ds-radius-pill, 999px);
  color: var(--ds-ink, #16181d);
  background: var(--ds-btn-secondary-bg, #fff);
  font: inherit;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}

.project-task-rich-content {
  color: var(--ds-ink-2, #343944);
  font-size: 14px;
  line-height: 1.8;
}

.project-task-rich-content :deep(p) { margin: 0 0 12px; }
.project-task-rich-content :deep(p:last-child) { margin-bottom: 0; }
.project-task-rich-content :deep(h1) { margin: 22px 0 10px; color: var(--ds-ink, #16181d); font-size: 24px; line-height: 1.35; }
.project-task-rich-content :deep(h2) { margin: 20px 0 9px; color: var(--ds-ink, #16181d); font-size: 20px; line-height: 1.4; }
.project-task-rich-content :deep(h3) { margin: 18px 0 8px; color: var(--ds-ink, #16181d); font-size: 17px; line-height: 1.45; }
.project-task-rich-content :deep(h1:first-child),
.project-task-rich-content :deep(h2:first-child),
.project-task-rich-content :deep(h3:first-child) { margin-top: 0; }
.project-task-rich-content :deep(ul),
.project-task-rich-content :deep(ol) { margin: 10px 0; padding-left: 24px; }
.project-task-rich-content :deep(blockquote) { margin: 14px 0; padding: 11px 14px; border: 1px solid var(--ds-orange-100, #fee9df); border-radius: var(--ds-radius-sm, 8px); background: var(--ds-orange-wash, #fff7f2); }
.project-task-rich-content :deep(a) { color: var(--ds-orange-deep, #b12f0a); text-underline-offset: 3px; }
.project-task-rich-content :deep(img) { display: block; max-width: 100%; height: auto; margin: 16px auto; border-radius: var(--ds-radius-md, 12px); box-shadow: 0 6px 20px rgba(31, 35, 41, 0.09); }

.project-task-requirements {
  display: grid;
  gap: var(--ds-space-4, 16px);
}

.project-task-requirements article {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: start;
  gap: var(--ds-space-3, 12px);
}

.project-task-requirements article > span {
  width: 8px;
  height: 8px;
  margin-top: 6px;
  border-radius: 50%;
  background: var(--project-task-orange);
}

.project-task-requirements article > span.optional {
  background: var(--ds-faint, #a3a8b1);
}

.project-task-requirements strong {
  color: var(--ds-ink, #16181d);
  font-size: 13px;
}

.project-task-requirements p {
  margin: 4px 0 0;
  color: var(--ds-muted, #6f7581);
  font-size: 12px;
  line-height: 1.65;
}

.project-task-requirements em {
  padding: 3px 7px;
  border-radius: var(--ds-radius-pill, 999px);
  color: var(--ds-muted, #6f7581);
  background: var(--ds-surface-subtle, #f3f4f6);
  font-size: 10px;
  font-style: normal;
  font-weight: 700;
}

.project-task-attachment-list {
  display: grid;
  gap: var(--ds-space-2, 8px);
}

.project-task-attachment-list article {
  display: grid;
  grid-template-columns: 38px minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--ds-space-3, 12px);
  min-height: 60px;
  padding: 10px 12px;
  border: 1px solid var(--ds-line, #e8e3dc);
  border-radius: var(--ds-radius-md, 12px);
  background: var(--ds-surface-subtle, #f8f9fa);
}

.project-task-attachment-list i {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  border-radius: var(--ds-radius-sm, 8px);
  color: var(--project-task-orange);
  background: var(--ds-orange-wash, #fff7f2);
  font-size: 10px;
  font-style: normal;
  font-weight: 750;
}

.project-task-attachment-list article > div {
  display: grid;
  min-width: 0;
}

.project-task-attachment-list strong {
  overflow: hidden;
  color: var(--ds-ink-2, #343944);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.project-task-attachment-list small {
  margin-top: 3px;
  color: var(--ds-muted, #6f7581);
  font-size: 10px;
}

.project-task-attachment-list article > span {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2, 8px);
}

.project-task-attachment-list button,
.project-task-attachment-list a {
  padding: 5px 7px;
  border: 0;
  color: var(--ds-muted, #6f7581);
  background: transparent;
  font: inherit;
  font-size: 11px;
  font-weight: 650;
  text-decoration: none;
  cursor: pointer;
}

.project-task-attachment-list button:hover,
.project-task-attachment-list a:hover {
  color: var(--project-task-orange);
}

.project-task-context-note {
  display: grid;
  gap: 5px;
  margin-top: 22px;
  padding: 14px 16px;
  border-left: 3px solid var(--ds-orange-500, #ed6b3d);
  border-radius: 0 10px 10px 0;
  background: var(--ds-orange-50, #fff7f3);
}

.project-task-context-note.score {
  border-left-color: #8b66c7;
  background: #f7f3fc;
}

.project-task-context-note strong {
  color: #363b44;
  font-size: 12px;
}

.project-task-context-note span {
  color: #777d89;
  font-size: 12px;
  line-height: 1.65;
}

.project-task-submissions .project-task-section-body {
  display: grid;
  gap: 12px;
}

.project-submission-card {
  padding: 18px;
  border: 1px solid #e7e9ed;
  border-radius: 12px;
  background: #fff;
}

.project-submission-card.focused {
  border-color: #75b991;
  background: #f3faf6;
  box-shadow: 0 0 0 3px rgba(70, 151, 102, 0.1);
}

.project-submission-head em.latest {
  color: #6a707b;
  background: #eef0f3;
}

.project-submission-copy {
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px solid #eceef2;
}

.project-submission-copy > span,
.project-submission-resource-block > span,
.project-history-content > span {
  color: #858b96;
  font-size: 11px;
  font-weight: 700;
}

.project-submission-copy p,
.project-history-content p {
  margin: 7px 0 0;
  color: #3f4650;
  font-size: 13px;
  line-height: 1.75;
  white-space: pre-line;
}

.project-submission-resource-block {
  display: grid;
  gap: 9px;
  margin-top: 18px;
}

.project-submission-file-list,
.project-version-file-list,
.project-submission-link-list {
  display: grid;
  gap: 8px;
}

.project-submission-file {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-height: 58px;
  padding: 10px 12px;
  border: 1px solid #e7e9ed;
  border-radius: 10px;
  background: #fafbfc;
}

.project-submission-file > div,
.project-submission-file > div:first-child,
.project-version-file > div {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.project-submission-file i,
.project-version-file i {
  display: inline-flex;
  flex: 0 0 34px;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 8px;
  color: var(--ds-orange-700, #d94312);
  background: var(--ds-orange-50, #fff2ec);
  font-size: 10px;
  font-style: normal;
  font-weight: 750;
}

.project-submission-file span,
.project-version-file span {
  display: grid;
  min-width: 0;
}

.project-submission-file strong,
.project-version-file strong {
  overflow: hidden;
  color: #3b414a;
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.project-submission-file small,
.project-version-file small {
  margin-top: 3px;
  color: #9298a2;
  font-size: 10px;
}

.project-submission-file button,
.project-submission-file a {
  padding: 5px 7px;
  border: 0;
  color: #646b76;
  background: transparent;
  font-size: 11px;
  font-weight: 650;
  text-decoration: none;
  cursor: pointer;
}

.project-submission-file button:hover,
.project-submission-file a:hover {
  color: var(--ds-orange-700, #d94312);
}

.project-submission-link-list a {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  min-height: 44px;
  padding: 0 13px;
  border: 1px solid #e7e9ed;
  border-radius: 9px;
  color: #3e444d;
  background: #fafbfc;
  font-size: 11px;
  text-decoration: none;
}

.project-submission-link-list a span {
  color: var(--ds-orange-700, #d94312);
  font-weight: 680;
}

.project-submission-primary-action {
  display: flex;
  align-items: center;
  gap: 13px;
  padding-top: 4px;
}

.project-submission-primary-action button {
  min-height: 40px;
  padding: 0 17px;
  border: 0;
  border-radius: 10px;
  color: #fff;
  background: var(--ds-orange-700, #d94312);
  font-size: 12px;
  font-weight: 720;
  cursor: pointer;
}

.project-submission-primary-action span {
  color: #858b96;
  font-size: 11px;
}

.project-version-editor {
  display: grid;
  gap: 20px;
  padding: 22px;
  border: 1px solid #f0b39b;
  border-radius: 14px;
  background: #fffbf9;
  box-shadow: 0 8px 24px rgba(217, 67, 18, 0.07);
}

.project-version-editor > header,
.project-version-resources > header,
.project-version-editor > footer {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
}

.project-version-editor > header span {
  color: var(--ds-orange-700, #d94312);
  font-size: 10px;
  font-weight: 760;
  letter-spacing: 0.08em;
}

.project-version-editor h3 {
  margin: 4px 0 0;
  color: #242830;
  font-size: 18px;
}

.project-version-editor > header p,
.project-version-resources header span,
.project-version-editor > footer > span {
  margin: 5px 0 0;
  color: #858b96;
  font-size: 11px;
  line-height: 1.55;
}

.project-version-editor > header > button,
.project-version-resources header > button {
  padding: 5px 0;
  border: 0;
  color: #777d89;
  background: transparent;
  font-size: 11px;
  font-weight: 680;
  cursor: pointer;
}

.project-version-field {
  display: grid;
  gap: 8px;
}

.project-version-field > span,
.project-version-resources header strong {
  color: #3c424b;
  font-size: 12px;
  font-weight: 720;
}

.project-version-field textarea {
  width: 100%;
  min-height: 126px;
  resize: vertical;
  padding: 13px 14px;
  border: 1px solid #dfe2e7;
  border-radius: 10px;
  color: #303640;
  background: #fff;
  font: inherit;
  font-size: 13px;
  line-height: 1.7;
  outline: none;
}

.project-version-field textarea:focus,
.project-version-link-editor input:focus,
.project-version-link-editor select:focus {
  border-color: #ed8d68;
  box-shadow: 0 0 0 3px rgba(232, 74, 28, 0.09);
}

.project-version-resources {
  display: grid;
  gap: 11px;
  padding-top: 18px;
  border-top: 1px solid #eee3df;
}

.project-version-resources header > div {
  display: grid;
}

.project-version-file {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-height: 58px;
  padding: 10px 12px;
  border: 1px solid #e4e6ea;
  border-radius: 10px;
  background: #fff;
}

.project-version-file.retained {
  background: #f8f9fa;
}

.project-version-file.added {
  border-color: #bcdac7;
  background: #f5faf7;
}

.project-version-file > button {
  flex: 0 0 auto;
  border: 0;
  color: #8a5b4d;
  background: transparent;
  font-size: 11px;
  font-weight: 650;
  cursor: pointer;
}

.project-version-upload {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-height: 52px;
  padding: 0 14px;
  border: 1px dashed #d7a490;
  border-radius: 10px;
  color: var(--ds-orange-700, #d94312);
  background: #fff;
  cursor: pointer;
}

.project-version-upload input {
  position: absolute;
  width: 1px;
  height: 1px;
  opacity: 0;
  pointer-events: none;
}

.project-version-upload span {
  font-size: 12px;
  font-weight: 720;
}

.project-version-upload small,
.project-version-empty-hint {
  color: #9298a2;
  font-size: 10px;
}

.project-version-link-editor {
  display: grid;
  gap: 8px;
}

.project-version-link-editor > div {
  display: grid;
  grid-template-columns: minmax(96px, 112px) minmax(0, 0.7fr) minmax(0, 1.4fr) auto;
  gap: 8px;
}

.project-version-link-editor input,
.project-version-link-editor select {
  box-sizing: border-box;
  width: 100%;
  min-width: 0;
  min-height: 38px;
  padding: 0 10px;
  border: 1px solid #dfe2e7;
  border-radius: 8px;
  color: #3e444e;
  background: #fff;
  font: inherit;
  font-size: 11px;
  outline: none;
}

.project-version-link-editor button {
  border: 0;
  color: #8a5b4d;
  background: transparent;
  font-size: 11px;
  font-weight: 650;
  cursor: pointer;
}

.project-version-editor > footer {
  align-items: center;
  padding-top: 18px;
  border-top: 1px solid #eee3df;
}

.project-version-editor > footer > div {
  display: flex;
  gap: 9px;
}

.project-version-editor > footer button {
  min-height: 40px;
  padding: 0 17px;
  border: 1px solid #dfe2e7;
  border-radius: 9px;
  color: #565d68;
  background: #fff;
  font-size: 12px;
  font-weight: 680;
  cursor: pointer;
}

.project-version-editor > footer button.primary {
  border-color: var(--ds-orange-700, #d94312);
  color: #fff;
  background: var(--ds-orange-700, #d94312);
}

.project-version-editor > footer button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.project-submission-history {
  display: grid;
  gap: 12px;
  padding-top: 4px;
}

.project-history-toggle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  width: 100%;
  min-height: 62px;
  padding: 0 16px;
  border: 1px solid #e5e7eb;
  border-radius: 11px;
  color: #3c424b;
  background: #f8f9fa;
  text-align: left;
  cursor: pointer;
}

.project-history-toggle > span {
  display: grid;
  gap: 3px;
}

.project-history-toggle strong {
  font-size: 12px;
}

.project-history-toggle small {
  color: #8a909b;
  font-size: 10px;
}

.project-history-toggle b {
  color: var(--ds-orange-700, #d94312);
  font-size: 11px;
}

.project-history-list {
  display: grid;
  gap: 10px;
  padding-left: 14px;
  border-left: 2px solid #e7e9ed;
}

.project-history-card {
  padding: 17px;
  border: 1px solid #e7e9ed;
  border-radius: 11px;
  background: #fafbfc;
}

.project-history-card > header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding-bottom: 12px;
  border-bottom: 1px solid #eceef2;
}

.project-history-card > header > div {
  display: flex;
  align-items: center;
  gap: 8px;
}

.project-history-card > header strong {
  color: #343a43;
  font-size: 13px;
}

.project-history-card > header span,
.project-history-card > header time {
  color: #858b96;
  font-size: 10px;
}

.project-history-content {
  margin-top: 14px;
}

.project-submission-file-list.compact,
.project-submission-link-list.compact {
  margin-top: 13px;
}

.project-submission-head,
.project-submission-meta,
.project-submission-head > div {
  display: flex;
  align-items: center;
}

.project-submission-head {
  justify-content: space-between;
  gap: 16px;
}

.project-submission-head > div {
  gap: 8px;
}

.project-submission-head span {
  color: var(--ds-orange-700, #d94312);
  font-size: 12px;
  font-weight: 760;
}

.project-submission-head b,
.project-submission-head > strong {
  color: #555c67;
  font-size: 12px;
}

.project-submission-head em {
  padding: 3px 7px;
  border-radius: 999px;
  color: #287244;
  background: #dff3e7;
  font-size: 10px;
  font-style: normal;
  font-weight: 750;
}

.project-submission-card > p,
.project-submission-review p {
  margin: 13px 0 0;
  color: #4e5560;
  font-size: 13px;
  line-height: 1.7;
  white-space: pre-line;
}

.project-submission-meta {
  gap: 14px;
  margin-top: 14px;
  color: #8a909b;
  font-size: 11px;
}

.project-submission-review {
  margin-top: 15px;
  padding: 13px 14px;
  border-radius: 9px;
  background: #f6f7f9;
}

.project-submission-review span {
  color: #737a86;
  font-size: 11px;
  font-weight: 700;
}

.project-submission-review p {
  margin-top: 5px;
}

.project-submission-assets {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 14px;
}

.project-submission-assets button {
  min-height: 34px;
  padding: 0 12px;
  border: 1px solid #dfe2e7;
  border-radius: 8px;
  color: #4e5560;
  background: #fff;
  font-size: 11px;
  font-weight: 650;
  cursor: pointer;
}

.project-task-empty-submission {
  display: grid;
  justify-items: center;
  gap: 7px;
  padding: 32px 20px;
  color: #777d89;
  text-align: center;
}

.project-task-empty-submission strong {
  color: #3e444e;
  font-size: 14px;
}

.project-task-empty-submission p {
  margin: 0;
  font-size: 12px;
}

.project-task-detail-aside {
  position: sticky;
  top: 0;
  max-height: calc(100dvh - var(--workspace-header-height, 64px) - (var(--ds-page-margin-y, 40px) * 2));
  overflow-x: hidden;
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-gutter: stable;
  scrollbar-width: thin;
}

.project-task-detail-aside > section {
  padding: var(--ds-space-6, 24px);
}

.project-task-detail-aside h2 {
  padding-bottom: 16px;
  border-bottom: 1px solid var(--ds-line-soft, #eceef2);
}

.project-task-detail-aside dl {
  display: grid;
  gap: 0;
  margin: 0;
}

.project-task-detail-aside dl > div {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  padding: 13px 0;
  border-bottom: 1px solid #f0f1f3;
}

.project-task-detail-aside dl > div:last-child {
  padding-bottom: 0;
  border-bottom: 0;
}

.project-task-detail-aside dt,
.project-task-version-summary > span {
  color: #8a909b;
  font-size: 11px;
}

.project-task-detail-aside dd {
  margin: 0;
  color: #3b414a;
  font-size: 12px;
  font-weight: 650;
  text-align: right;
}

.project-task-version-summary {
  display: grid;
  gap: 7px;
}

.project-task-version-summary strong {
  color: var(--ds-ink, #16181d);
  font-size: 30px;
  line-height: 1;
}

.project-task-version-summary p {
  margin: 4px 0 0;
  color: #777d89;
  font-size: 11px;
}

@media (max-width: 1380px) {
  .focused-task-row {
    grid-template-columns: 38px minmax(190px, 1fr) minmax(76px, 0.34fr) 78px auto 16px;
  }
}

@media (max-width: 1160px) {
  .focused-task-layout {
    grid-template-columns: 1fr;
  }

  .focused-task-detail {
    position: static;
  }

  .focused-task-row {
    grid-template-columns: 38px minmax(180px, 1fr) minmax(76px, 0.34fr) 78px auto 16px;
  }

  .focused-task-owner {
    display: flex;
  }
}

@media (max-width: 1080px) {
  .project-task-detail-page {
    padding: var(--ds-space-6, 24px);
  }

  .project-task-detail-layout {
    grid-template-columns: 1fr;
  }

  .project-task-detail-aside {
    position: static;
    top: auto;
    max-height: none;
    overflow: visible;
    scrollbar-gutter: auto;
  }
}

@media (max-width: 1023px) {
  .focused-task-shell {
    padding: var(--ds-space-6, 24px);
  }
}

@media (max-width: 820px) {
  .focused-task-shell {
    padding: var(--ds-space-5, 20px) var(--ds-space-4, 16px) 96px;
  }

  .project-task-detail-page {
    padding: var(--ds-space-5, 20px) var(--ds-space-4, 16px) 96px;
  }

  .project-task-detail-head {
    align-items: flex-start;
    flex-direction: column;
    gap: var(--ds-space-4, 16px);
  }

  .project-task-detail-head-actions {
    width: 100%;
    justify-content: flex-start;
    flex-wrap: wrap;
  }

  .project-version-link-editor > div {
    grid-template-columns: 1fr 1fr;
  }

  .project-version-link-editor > div input:nth-of-type(2) {
    grid-column: 1 / -1;
  }

  .focused-task-overview {
    align-items: stretch;
    flex-wrap: wrap;
  }

  .focused-task-overview > p {
    width: 100%;
    margin: 8px 0 0;
    padding: 10px 0 0;
    border-top: 1px solid var(--ds-line-soft, #eceef2);
    text-align: left;
  }

  .focused-task-metric {
    flex: 1 1 42%;
    padding: 4px 12px;
  }

  .focused-task-metric:nth-child(2) {
    border-right: 0;
  }

  .focused-task-toolbar {
    align-items: stretch;
    flex-direction: column;
  }

  .focused-task-search {
    width: 100%;
  }

  .focused-task-row {
    grid-template-columns: 36px minmax(0, 1fr) auto 14px;
  }

  .focused-task-owner,
  .focused-task-due {
    display: none;
  }
}

@media (max-width: 560px) {
  .project-task-detail-head-actions,
  .project-task-back,
  .project-task-head-action {
    width: 100%;
  }

  .project-submission-primary-action,
  .project-version-editor > header,
  .project-version-editor > footer,
  .project-submission-file,
  .project-version-file {
    align-items: stretch;
    flex-direction: column;
  }

  .project-version-editor {
    padding: 18px;
  }

  .project-version-editor > footer > div,
  .project-version-editor > footer button {
    width: 100%;
  }

  .project-version-link-editor > div {
    grid-template-columns: 1fr;
  }

  .project-version-link-editor > div input:nth-of-type(2) {
    grid-column: auto;
  }

  .project-task-section,
  .project-task-detail-aside > section {
    padding: 18px;
  }

  .focused-task-overview {
    padding: 12px;
  }

  .focused-task-metric {
    min-width: 0;
  }

  .focused-task-toolbar {
    padding: 20px 16px 16px;
  }

  .focused-source-filters {
    padding: 0 16px 14px;
  }

  .focused-task-group > header {
    padding-right: 16px;
    padding-left: 16px;
  }

  .focused-task-group header p {
    display: none;
  }

  .focused-task-list {
    padding-right: 6px;
    padding-left: 6px;
  }

  .focused-task-row {
    min-height: 74px;
    gap: 10px;
    padding-right: 8px;
    padding-left: 8px;
  }

  .focused-task-main > small {
    display: none;
  }

  .focused-task-status {
    max-width: 82px;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .focused-task-detail {
    padding: 18px;
  }
}
</style>
