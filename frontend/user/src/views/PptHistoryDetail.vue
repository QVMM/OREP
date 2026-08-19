<template>
  <AiAppShell mode="task" width="wide">
    <template #header>
      <AiAppHeader
        app="ppt"
        mode="task"
        back-label="最近记录"
        :back-to="{ path: '/ppt-editor', query: { view: 'history' } }"
        :title="task?.project_name || 'PPT 历史详情'"
        :subtitle="`${taskStatusText} · ${htmlPages.length} 页 · ${formatDate(task?.created_at)}`"
      >
        <template #actions>
          <el-button
            v-if="task?.status === 'completed'"
            :type="deliverabilityVerdict.status === 'blocked' ? 'warning' : 'primary'"
            :loading="downloadingPpt"
            @click="downloadPpt"
          >
            <el-icon><Download /></el-icon>
            {{ downloadActionText }}
          </el-button>
        </template>
      </AiAppHeader>
    </template>

    <div v-loading="loading" class="ppt-history-detail__content">
      <el-empty v-if="!loading && !detail" description="未找到历史记录" />

      <template v-else-if="detail">
        <div class="summary-grid">
          <div class="summary-item">
            <span class="label">任务 ID</span>
            <span class="value">#{{ task?.id }}</span>
          </div>
          <div class="summary-item">
            <span class="label">领域</span>
            <span class="value">{{ task?.domain || '-' }}</span>
          </div>
          <div class="summary-item">
            <span class="label">团队</span>
            <span class="value">{{ task?.team_name || '-' }}</span>
          </div>
          <div class="summary-item">
            <span class="label">快照</span>
            <span class="value">{{ snapshots.length }} 个</span>
          </div>
          <div class="summary-item health-summary" :class="healthReadinessClass(roadshowHealth?.readiness)">
            <span class="label">上台状态</span>
            <span class="value">{{ healthReadinessText(roadshowHealth?.readiness) }}</span>
          </div>
          <div class="summary-item health-summary" :class="healthReadinessClass(roadshowHealth?.readiness)">
            <span class="label">体检总分</span>
            <span class="value">{{ roadshowHealth?.overall_score ?? '-' }} 分</span>
          </div>
          <div class="summary-item deliverability-summary" :class="deliverabilityClass(deliverabilityVerdict.status)">
            <span class="label">交付状态</span>
            <span class="value">{{ deliverabilityVerdict.label }}</span>
          </div>
          <div class="summary-item deliverability-summary" :class="deliverabilityClass(deliverabilityVerdict.status)">
            <span class="label">交付结论</span>
            <span class="value">{{ deliverabilityVerdict.shortHint }}</span>
          </div>
          <div class="summary-item quality-summary" :class="qualityStatusClass(qualityReport?.overall_status)">
            <span class="label">基础质量</span>
            <span class="value">{{ qualityReport?.average_score ?? '-' }} 分</span>
          </div>
          <div class="summary-item quality-summary" :class="qualityStatusClass(qualityReport?.overall_status)">
            <span class="label">待关注问题</span>
            <span class="value">{{ qualityReport?.issue_count ?? 0 }} 个</span>
          </div>
          <div class="summary-item gate-summary" :class="{ warning: htmlQualityGate.retry_count > 0 }">
            <span class="label">生成期拦截</span>
            <span class="value">{{ htmlQualityGate.retry_count || 0 }} 页</span>
          </div>
          <div class="summary-item gate-summary" :class="{ warning: htmlQualityGate.fallback_count > 0 }">
            <span class="label">安全兜底</span>
            <span class="value">{{ htmlQualityGate.fallback_count || 0 }} 页</span>
          </div>
          <div class="summary-item coverage-summary">
            <span class="label">必备评分点</span>
            <span class="value">{{ scoringCoverage?.required_coverage_rate || '-' }}</span>
          </div>
          <div class="summary-item coverage-summary">
            <span class="label">覆盖评分点</span>
            <span class="value">{{ scoringCoverage?.covered ?? 0 }}/{{ scoringCoverage?.total_points ?? 0 }}</span>
          </div>
          <div class="summary-item scoring-risk-summary" :class="scoringDashboardStatusClass(scoringDashboard?.status)">
            <span class="label">评分风险</span>
            <span class="value">{{ scoringDashboard?.score ?? '-' }} 分</span>
          </div>
          <div class="summary-item scoring-risk-summary" :class="scoringDashboardStatusClass(scoringDashboard?.status)">
            <span class="label">高风险项</span>
            <span class="value">{{ scoringDashboard?.high_risk_count ?? 0 }} 个</span>
          </div>
          <div class="summary-item practice-summary" :class="{ 'needs-evidence': practiceDemo?.completeness_status === 'needs_evidence' }">
            <span class="label">实操步骤</span>
            <span class="value">{{ practiceDemo?.step_count ?? 0 }} 个</span>
          </div>
          <div class="summary-item practice-summary" :class="{ 'needs-evidence': practiceDemo?.completeness_status === 'needs_evidence' }">
            <span class="label">缺失证据</span>
            <span class="value">{{ practiceDemo?.missing_evidence_count ?? 0 }} 项</span>
          </div>
          <div class="summary-item material-summary" :class="{ warning: materialPrivacyRiskCount > 0 }">
            <span class="label">证据素材</span>
            <span class="value">{{ materialAssets.length }} 个</span>
          </div>
          <div class="summary-item material-summary" :class="{ warning: materialPrivacyRiskCount > 0 }">
            <span class="label">匿名风险</span>
            <span class="value">{{ materialPrivacyRiskCount }} 个</span>
          </div>
          <div class="summary-item roadshow-summary" :class="roadshowStatusClass(roadshowStructure?.status)">
            <span class="label">路演结构</span>
            <span class="value">{{ roadshowStructure?.score ?? '-' }} 分</span>
          </div>
          <div class="summary-item roadshow-summary" :class="roadshowStatusClass(roadshowStructure?.status)">
            <span class="label">缺失模块</span>
            <span class="value">{{ roadshowStructure?.required_missing ?? 0 }} 个</span>
          </div>
        </div>

        <PptDownloadReadinessCard
          v-if="downloadChecklist.length"
          :status="deliverabilityVerdict.status"
          :summary="downloadReadinessSummary"
          :status-hint="deliverabilityVerdict.shortHint"
          :warning-suggestion-count="warningSuggestionCount"
          :checklist="downloadChecklist"
          :next-pending-item="nextPendingDownloadItem"
          :next-warning-followup-action="nextWarningFollowupAction"
          :action-feedback="downloadReadinessActionFeedback"
          :loading-key="downloadChecklistActionKey"
          :download-loading="downloadingPpt"
          :download-flow-active="pendingDownloadAfterFix"
          @download="downloadPpt"
          @handle-item="handleDownloadChecklistItem"
          @exit-download-flow="exitDownloadFlow"
        />

        <div v-if="pendingDownloadAfterFix" class="download-flow-banner" :class="deliverabilityVerdict.status">
          <div class="download-flow-banner-copy">
            <span class="quality-eyebrow">下载流程进行中</span>
            <strong>
              {{ deliverabilityVerdict.status === 'ready'
                ? '当前已满足下载条件，可直接继续下载'
                : (deliverabilityVerdict.status === 'warning'
                  ? (downloadFlowFollowupAction ? `当前版已可继续下载，建议继续处理「${downloadFlowFollowupAction.title}」` : '当前版已可继续下载，也可以先补强后再下')
                  : (downloadFlowFollowupAction ? `先处理「${downloadFlowFollowupAction.title}」后继续下载` : '处理当前项后系统会继续带你回到下载流程')) }}
            </strong>
            <p>
              {{ deliverabilityVerdict.status !== 'blocked'
                ? (deliverabilityVerdict.status === 'ready'
                  ? '刚刚处理的关键阻塞项已解除，现在可以直接下载；如果还想继续补强，也可以保留下载流程继续处理建议项。'
                  : (downloadFlowFollowupAction?.detail || '刚刚处理的关键阻塞项已解除，现在可以先下载当前版本；如果还想继续补强，系统也会继续带你处理下一项。'))
                : (downloadFlowFollowupAction?.detail || '你当前是从下载入口进入的，系统会保持下载语境，直到可以继续下载或你主动退出。') }}
            </p>
          </div>
          <div class="download-flow-banner-actions">
            <el-button size="small" text @click="returnToDownloadFlowFocus()">
              返回下载条件
            </el-button>
            <el-button
              v-if="deliverabilityVerdict.status !== 'blocked'"
              size="small"
              type="primary"
              :loading="downloadingPpt"
              @click="downloadPpt"
            >
              {{ deliverabilityVerdict.status === 'ready' ? '继续下载' : '继续下载当前版本' }}
            </el-button>
            <el-button
              v-if="nextPendingDownloadItem"
              size="small"
              type="warning"
              plain
              :loading="downloadChecklistActionKey === nextPendingDownloadItem.key"
              @click="handleDownloadChecklistItem(nextPendingDownloadItem)"
            >
              {{ deliverabilityVerdict.status === 'blocked' ? '先处理并继续下载' : '继续补强下一项' }}
            </el-button>
            <el-button
              v-else-if="nextWarningFollowupAction"
              size="small"
              type="warning"
              plain
              @click="handleWarningFollowupAction"
            >
              继续优化当前版
            </el-button>
            <el-button size="small" text @click="exitDownloadFlow">
              退出下载流程
            </el-button>
          </div>
        </div>

        <div class="readiness-dashboard">
          <div class="readiness-hero">
            <div>
              <span class="quality-eyebrow">路演准备度仪表盘</span>
              <h2>{{ readinessVerdict.title }}</h2>
              <p>{{ readinessVerdict.summary }}</p>
            </div>
            <strong>{{ readinessVerdict.score }} 分</strong>
          </div>

          <div class="readiness-card-grid">
            <button
              v-for="card in readinessCards"
              :key="card.key"
              type="button"
              class="readiness-card"
              :class="card.status"
              @click="activeTab = card.tab"
            >
              <span>{{ card.label }}</span>
              <strong>{{ card.value }}</strong>
              <p>{{ card.hint }}</p>
            </button>
          </div>

          <div v-if="deliverabilityBlockerActions.length" class="deliverability-blockers">
            <div>
              <span class="quality-eyebrow">{{ deliverabilityVerdict.status === 'blocked' ? '交付阻塞项' : '交付补强建议' }}</span>
              <h3>
                {{
                  deliverabilityVerdict.status === 'blocked'
                    ? `先解除这 ${deliverabilityBlockerActions.length} 个阻塞，再导出比赛终稿`
                    : `当前版本已可下载，仍建议继续处理这 ${deliverabilityBlockerActions.length} 项补强建议`
                }}
              </h3>
            </div>
            <div class="deliverability-blocker-list">
              <button
                v-for="item in deliverabilityBlockerActions"
                :key="item.key"
                type="button"
                class="deliverability-blocker"
                :class="item.priority"
                @click="openDeliverabilityBlocker(item)"
              >
                <span>{{ item.priority }} · {{ item.tabLabel }}</span>
                <strong>{{ item.title }}</strong>
                <em>{{ item.hint }}</em>
                <small v-if="item.pageIndex || item.relatedPoints?.length">
                  {{ item.pageIndex ? `定位：第${item.pageIndex}页` : '' }}
                  {{ item.pageIndex && item.relatedPoints?.length ? ' · ' : '' }}
                  {{ item.relatedPoints?.length ? `评分点：${item.relatedPoints.join('、')}` : '' }}
                </small>
              </button>
            </div>
          </div>

          <div v-if="readinessNextActions.length" class="readiness-next-actions">
            <div>
              <span class="quality-eyebrow">下一步建议</span>
              <h3>先处理最可能影响上台质量的 {{ readinessNextActions.length }} 件事</h3>
            </div>
            <div class="readiness-action-list">
              <button
                v-for="action in readinessNextActions"
                :key="action.key"
                type="button"
                :class="action.priority"
                @click="handleReadinessAction(action)"
              >
                <span>{{ action.priority }}</span>
                <strong>{{ action.title }}</strong>
                <em>{{ action.hint }}</em>
              </button>
            </div>
          </div>
        </div>

        <el-tabs v-model="activeTab" class="history-tabs">
          <el-tab-pane label="终稿总审" name="final_review">
            <div class="final-review-panel">
              <div class="final-review-hero" :class="deliverabilityClass(finalReviewVerdict.status)">
                <div>
                  <span class="quality-eyebrow">比赛终稿总审</span>
                  <h2>{{ finalReviewVerdict.title }}</h2>
                  <p>{{ finalReviewVerdict.summary }}</p>
                  <div class="quality-hero-actions">
                    <el-button size="small" type="primary" :loading="healthChecking" @click="runRoadshowHealthCheck">
                      重新总审
                    </el-button>
                  </div>
                </div>
                <strong>{{ finalReviewVerdict.score }} 分</strong>
              </div>

              <div class="final-review-scoreboard">
                <div>
                  <span>通过项</span>
                  <strong>{{ finalReviewSummary.passed }}/{{ finalReviewSummary.total }}</strong>
                </div>
                <div>
                  <span>{{ deliverabilityVerdict.status === 'blocked' ? '阻塞项' : '补强建议' }}</span>
                  <strong>{{ deliverabilityBlockerActions.length }}</strong>
                </div>
                <div>
                  <span>建议项</span>
                  <strong>{{ readinessNextActions.length }}</strong>
                </div>
                <div>
                  <span>交付结论</span>
                  <strong>{{ deliverabilityVerdict.label }}</strong>
                </div>
              </div>

              <div class="final-review-checklist">
                <div
                  v-for="item in finalReviewItems"
                  :key="item.key"
                  class="final-review-card"
                  :class="item.status"
                >
                  <div class="final-review-card-head">
                    <span>{{ item.label }}</span>
                    <strong>{{ item.statusText }}</strong>
                  </div>
                  <h3>{{ item.value }}</h3>
                  <p>{{ item.hint }}</p>
                  <el-button size="small" text @click="handleFinalReviewItem(item)">
                    {{ pendingDownloadAfterFix ? '先处理并继续下载' : '去处理' }}
                  </el-button>
                </div>
              </div>

              <div v-if="deliverabilityBlockerActions.length" class="final-review-blockers">
                <div class="final-review-section-head">
                  <div>
                    <span class="quality-eyebrow">{{ deliverabilityVerdict.status === 'blocked' ? '必须先解除' : '建议继续补强' }}</span>
                    <h3>
                      {{
                        deliverabilityVerdict.status === 'blocked'
                          ? '这些阻塞项不处理，不建议直接拿去比赛'
                          : '这些补强建议继续处理完，比赛终稿会更稳'
                      }}
                    </h3>
                  </div>
                </div>
                <div class="deliverability-blocker-list">
                  <button
                    v-for="item in deliverabilityBlockerActions"
                    :key="`review-${item.key}`"
                    type="button"
                    class="deliverability-blocker"
                    :class="item.priority"
                    @click="openDeliverabilityBlocker(item)"
                  >
                    <span>{{ item.priority }} · {{ item.tabLabel }}</span>
                    <strong>{{ item.title }}</strong>
                    <em>{{ item.hint }}</em>
                  </button>
                </div>
              </div>

              <div class="final-review-columns">
                <div class="final-review-column">
                  <div class="final-review-section-head">
                    <div>
                      <span class="quality-eyebrow">已通过</span>
                      <h3>这些部分已经具备比赛展示基础</h3>
                    </div>
                  </div>
                  <div class="final-review-pass-list">
                    <div v-for="item in finalReviewPassItems" :key="item.key" class="final-review-pass-item">
                      <strong>{{ item.label }}</strong>
                      <p>{{ item.hint }}</p>
                    </div>
                  </div>
                </div>

                <div class="final-review-column">
                  <div class="final-review-section-head">
                    <div>
                      <span class="quality-eyebrow">继续补强</span>
                      <h3>建议先做这几件事，再进入最终讲稿联调</h3>
                    </div>
                  </div>
                  <div class="readiness-action-list">
                    <button
                      v-for="action in readinessNextActions"
                      :key="`review-next-${action.key}`"
                      type="button"
                      :class="action.priority"
                      @click="handleReadinessAction(action)"
                    >
                      <span>{{ action.priority }}</span>
                      <strong>{{ action.title }}</strong>
                      <em>{{ action.hint }}</em>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </el-tab-pane>

          <el-tab-pane label="总报告" name="health">
            <div v-if="roadshowHealth" class="health-panel">
              <div class="health-hero" :class="healthReadinessClass(roadshowHealth.readiness)">
                <div>
                  <span class="quality-eyebrow">路演一键体检报告</span>
                  <h2>{{ roadshowHealth.verdict }}</h2>
                  <p>{{ roadshowHealth.summary }}</p>
                  <small v-if="roadshowHealth.generated_at" class="report-freshness-inline">
                    当前展示为最近一次保存结果 · {{ roadshowHealth.generated_at }}
                  </small>
                  <div class="quality-hero-actions">
                    <el-button size="small" type="primary" :loading="healthChecking" @click="runRoadshowHealthCheck">
                      重新体检
                    </el-button>
                  </div>
                </div>
                <strong>{{ roadshowHealth.overall_score ?? '-' }}</strong>
              </div>

              <div class="health-score-grid">
                <div v-for="item in healthDimensionItems" :key="item.key" class="health-score-card">
                  <span>{{ item.label }}</span>
                  <strong>{{ item.score }} 分</strong>
                </div>
              </div>

              <div v-if="roadshowHealth.blockers?.length" class="health-blockers">
                <h3>上台前阻塞项</h3>
                <div v-for="blocker in roadshowHealth.blockers" :key="`${blocker.type}-${blocker.message}`">
                  {{ blocker.message }}
                </div>
              </div>

              <div class="health-actions">
                <h3>最先改这 3 件事</h3>
                <div
                  v-for="action in roadshowHealth.top_actions || []"
                  :key="`${action.priority}-${action.title}`"
                  class="health-action-card"
                  :class="action.priority"
                >
                  <span>{{ action.priority }} · {{ action.source }}</span>
                  <strong>{{ action.title }}</strong>
                  <p>{{ action.action }}</p>
                </div>
              </div>

              <div class="optimization-queue">
                <div class="optimization-head">
                  <div>
                    <h3>一键优化任务队列</h3>
                    <p>把体检建议转成可执行任务，先处理 P0/P1，再处理页面细节。</p>
                  </div>
                  <el-button size="small" :loading="queueGenerating" @click="generateOptimizationQueue">
                    重新生成队列
                  </el-button>
                </div>
                <div v-if="optimizationQueue?.tasks?.length" class="optimization-list">
                  <div
                    v-for="item in optimizationQueue.tasks"
                    :key="item.task_id"
                    class="optimization-task"
                    :class="[item.priority, { done: isOptimizationTaskDone(item), reviewing: item.status === 'in_progress' }]"
                  >
                    <div class="optimization-task-main">
                      <span>{{ item.priority }} · {{ taskTypeText(item.task_type) }} · {{ item.source }}</span>
                      <h4>{{ item.order }}. {{ item.title }}</h4>
                      <p>{{ item.description }}</p>
                      <small>{{ item.action_hint }}</small>
                      <div v-if="item.related_points?.length" class="optimization-tags">
                        <span v-for="point in item.related_points" :key="point">{{ point }}</span>
                      </div>
                    </div>
                    <div class="optimization-task-actions">
                      <el-button
                        size="small"
                        type="primary"
                        plain
                        @click="executeOptimizationTask(item)"
                      >
                        {{ optimizationActionText(item) }}
                      </el-button>
                      <el-button
                        v-if="item.related_pages?.length"
                        size="small"
                        text
                        @click="previewQualityPage(item.related_pages[0])"
                      >
                        查看第 {{ item.related_pages[0] }} 页
                      </el-button>
                      <el-button
                        size="small"
                        text
                        :loading="updatingOptimizationTaskId === item.task_id"
                        :disabled="isOptimizationTaskDone(item)"
                        @click="markOptimizationTaskDone(item)"
                      >
                        {{ isOptimizationTaskDone(item) ? '已处理' : '标记已处理' }}
                      </el-button>
                      <el-tag size="small" :type="optimizationTaskTagType(item)">
                        {{ optimizationTaskStatusText(item) }}
                      </el-tag>
                    </div>
                  </div>
                </div>
                <el-empty v-else description="暂无优化任务，重新体检后可生成任务队列" />
              </div>

              <div class="health-signals">
                <div><span>页面问题</span><strong>{{ roadshowHealth.signals?.page_issue_count || 0 }}</strong></div>
                <div><span>评分高风险</span><strong>{{ roadshowHealth.signals?.high_risk_scoring_count || 0 }}</strong></div>
                <div><span>实操步骤</span><strong>{{ roadshowHealth.signals?.practice_step_count || 0 }}</strong></div>
                <div><span>素材证据</span><strong>{{ roadshowHealth.signals?.material_count || 0 }}</strong></div>
                <div><span>缺失证据</span><strong>{{ roadshowHealth.signals?.missing_evidence_count || 0 }}</strong></div>
                <div><span>匿名风险</span><strong>{{ roadshowHealth.signals?.privacy_risk_count || 0 }}</strong></div>
              </div>
            </div>
            <el-empty v-else description="暂无路演体检报告" />
          </el-tab-pane>

          <el-tab-pane label="HTML 预览" name="html">
            <div class="preview-layout">
              <div class="page-list">
                <button
                  v-for="page in htmlPages"
                  :key="page.page_index"
                  :class="['page-list-item', pageQualityStatus(page.page_index), {
                    active: page.page_index === currentPageIndex,
                    'pack-linked': selectedMaterialPageIndices.includes(Number(page.page_index))
                  }]"
                  @click="currentPageIndex = page.page_index"
                >
                  <span>{{ page.page_index }}</span>
                  <div class="page-list-copy">
                    <strong>{{ getOutlineTitle(page.page_index) }}</strong>
                    <small>{{ pageQualityLabel(page.page_index) }} · {{ pageRoleText(getOutlinePage(page.page_index)?.slide_role || getOutlinePage(page.page_index)?.page_role) }}</small>
                  </div>
                </button>
              </div>
              <div class="preview-stage">
                <div class="preview-toolbar">
                  <span>第 {{ currentPageIndex }} 页 · {{ getOutlineTitle(currentPageIndex) }}</span>
                  <el-button size="small" @click="openRepairHistory(currentPageIndex)">
                    修复历史
                  </el-button>
                </div>
                <div v-if="currentHtml" ref="previewViewportRef" class="preview-viewport">
                  <div
                    class="preview-canvas"
                    :style="previewCanvasStyle"
                  >
                    <iframe
                      :srcdoc="currentHtml"
                      sandbox="allow-same-origin allow-scripts"
                      class="preview-iframe"
                    />
                  </div>
                </div>
                <el-empty v-else description="该页暂无 HTML" />
              </div>
              <PptHtmlWorkbench
                :quality-tag-type="currentPageQuality?.status === 'pass' ? 'success' : (currentPageQuality?.status === 'fail' ? 'danger' : 'warning')"
                :quality-tag-text="currentPageQuality ? qualityStatusText(currentPageQuality.status) : '待质检'"
                :title="getOutlineTitle(currentPageIndex)"
                :quality-score="currentPageQuality?.score ?? '-'"
                :issue-count="currentPageFailedMessages.length"
                :gate-count="currentPageGateItems.length"
                :sequence-count="currentPageSequenceEvents.length"
                :page-goal="currentPageGoal"
                :template-chips="currentPageTemplateChips"
                :practice-rows="currentPracticeRows"
                :page-script="currentPageScript"
                :action-feedback="currentPageActionFeedback"
                :failed-messages="currentPageFailedMessages"
                :gate-items="currentPageGateItems.map(item => ({ key: `${item.page_index}-${item.action}-${item.title}`, text: gateActionText(item.action) }))"
                :sequence-events="currentPageSequenceEvents.map(event => ({ key: `${event.page_index}-${event.message}`, text: `${sequenceSeverityText(event.severity)}：${event.message}` }))"
                :evidence-hints="currentPageEvidenceHints"
                :material-task="currentPageMaterialTask"
                :linked-assets="currentPageLinkedAssets"
                :recommended-assets="currentPageRecommendedAssets"
                :related-material-tasks="previewRelatedMaterialTasks"
                :show-inline-tasks="showInlineMaterialTasks"
                :current-page-index="currentPageIndex"
                :material-asset-type="materialAssetType"
                :linked-step-id="linkedStepId"
                :material-description="materialDescription"
                :material-description-placeholder="materialDescriptionPlaceholder"
                :practice-steps="practiceDemo?.steps || []"
                :material-uploading="materialUploading"
                :download-flow-active="pendingDownloadAfterFix"
                :primary-action="currentPagePrimaryAction"
                @prepare-inline-material="prepareCurrentPageMaterialInline"
                @toggle-inline-tasks="toggleInlineMaterialTasks"
                @select-material-task="selectMaterialTask"
                @update:materialAssetType="materialAssetType = $event"
                @update:linkedStepId="linkedStepId = $event"
                @update:materialDescription="materialDescription = $event"
                @upload="uploadMaterialAsset"
                @confirm-current-page-binding="confirmCurrentPageMaterialBinding"
                @clear-current-page-binding="clearCurrentPageMaterialBinding"
                @handle-feedback-item="handleDownloadChecklistItem"
                @download-from-feedback="downloadPpt"
                @primary-action="handleCurrentPagePrimaryAction"
                @view-quality="previewQualityPage(currentPageIndex)"
                @repair-history="openRepairHistory(currentPageIndex)"
                @open-material-workspace="openMaterialWorkspaceForCurrentPage"
              />
            </div>
          </el-tab-pane>

          <el-tab-pane label="质量报告" name="quality">
            <PptQualityReportPanel
              v-if="qualityReport"
              :quality-report="qualityReport"
              :quality-checking="qualityChecking"
              :batch-repairable-count="batchRepairableCount"
              :batch-repairing="batchRepairing"
              :quality-priority-groups="qualityPriorityGroups"
              :html-quality-gate="htmlQualityGate"
              :html-quality-gate-items="htmlQualityGateItems"
              :quality-pages="qualityPages"
              :repairing-page-index="repairingPageIndex"
              :quality-status-class="qualityStatusClass"
              :quality-status-text="qualityStatusText"
              :quality-priority-level="qualityPriorityLevel"
              :quality-priority-reason="qualityPriorityReason"
              :normalize-checks="normalizeChecks"
              :page-risk-badges="pageRiskBadges"
              :failed-check-messages="failedCheckMessages"
              :strategy-text="strategyText"
              :resolved-repair-route-reason="resolvedRepairRouteReason"
              :repair-route-label="repairRouteLabel"
              :infer-current-repair-route="inferCurrentRepairRoute"
              :page-issue-profile-summary="pageIssueProfileSummary"
              :repair-action-button-text="repairActionButtonText"
              :gate-action-text="gateActionText"
              :gate-check-text="gateCheckText"
              :get-outline-title="getOutlineTitle"
              @run-quality-check="runQualityCheck"
              @batch-repair="batchRepairPages"
              @preview-page="previewQualityPage"
              @repair-page="repairPage"
              @open-repair-history="openRepairHistory"
            />
            <el-empty v-else description="暂无质量报告，新生成任务完成后会自动沉淀基础质检结果" />
          </el-tab-pane>

          <el-tab-pane label="路演结构" name="roadshow">
            <PptRoadshowPanel
              v-if="roadshowStructure"
              :roadshow-structure="roadshowStructure"
              :roadshow-checking="roadshowChecking"
              :roadshow-story-phases="roadshowStoryPhases"
              :roadshow-storyline-coverage="roadshowStorylineCoverage"
              :roadshow-sequence-events="roadshowSequenceEvents"
              :current-page-index="currentPageIndex"
              :roadshow-status-class="roadshowStatusClass"
              :roadshow-status-text="roadshowStatusText"
              :story-phase-status-text="storyPhaseStatusText"
              :roadshow-module-status-text="roadshowModuleStatusText"
              :sequence-severity-text="sequenceSeverityText"
              :sequence-event-phase-name="sequenceEventPhaseName"
              :pacing-status-text="pacingStatusText"
              @run-check="runRoadshowStructureCheck"
              @preview-page="previewQualityPage"
            />
            <el-empty v-else description="暂无路演结构报告" />
          </el-tab-pane>

          <el-tab-pane label="评分覆盖" name="coverage">
            <PptScoringCoveragePanel
              v-if="scoringCoverage"
              :scoring-coverage="scoringCoverage"
              :scoring-dashboard="scoringDashboard"
              :scoring-dashboard-checking="scoringDashboardChecking"
              :judge-scoring-categories="judgeScoringCategories"
              :missing-required="missingRequired"
              :scoring-dashboard-status-class="scoringDashboardStatusClass"
              :scoring-dashboard-status-text="scoringDashboardStatusText"
              :judge-category-has-highlighted-point="judgeCategoryHasHighlightedPoint"
              :risk-level-text="riskLevelText"
              :scoring-point-matches="scoringPointMatches"
              :target-pages-text="targetPagesText"
              :coverage-evidence-text="coverageEvidenceText"
              @run-dashboard-check="runScoringDashboardCheck"
              @preview-page="previewQualityPage"
            />
            <el-empty v-else description="暂无评分覆盖矩阵" />
          </el-tab-pane>

          <el-tab-pane label="实操演示" name="practice">
            <PptPracticeDemoPanel
              v-if="practiceDemo"
              :practice-demo="practiceDemo"
              :practice-loop-summary="practiceLoopSummary"
              :practice-loop-items="practiceLoopItems"
              :demo-mode-text="demoModeText"
              :target-pages-text="targetPagesText"
              :list-text="listText"
              @preview-page="previewQualityPage"
              @prepare-evidence="preparePracticeEvidenceUpload"
            />
            <el-empty v-else description="暂无实操演示模块" />
          </el-tab-pane>

          <el-tab-pane label="素材证据（高级）" name="materials">
            <PptMaterialsAdvancedPanel
              :active-material-task="activeMaterialTask"
              :active-evidence-pack="activeEvidencePack"
              :current-page-index="currentPageIndex"
              :material-refreshing="materialRefreshing"
              :material-asset-type="materialAssetType"
              :linked-step-id="linkedStepId"
              :material-description="materialDescription"
              :material-description-placeholder="materialDescriptionPlaceholder"
              :material-uploading="materialUploading"
              :practice-steps="practiceDemo?.steps || []"
              :material-upload-tasks="materialUploadTasks"
              :material-upload-pending-count="materialUploadPendingCount"
              :material-evidence-plan="materialEvidencePlan"
              :material-evidence-packs="materialEvidencePacks"
              :material-evidence-groups="materialEvidenceGroups"
              :policy-pages="policyPages"
              :policy-evidence-assets="policyEvidenceAssets"
              :evidence-chain-summary="evidenceChainSummary"
              :evidence-chain-items="evidenceChainItems"
              :material-assets="materialAssets"
              :material-type-text="materialTypeText"
              :target-pages-text="targetPagesText"
              :evidence-chain-status-text="evidenceChainStatusText"
              :format-date="formatDate"
              :material-quality-text="materialQualityText"
              @back-to-html="activeTab = 'html'"
              @set-page="currentPageIndex = $event"
              @clear-evidence-pack-focus="clearEvidencePackFocus"
              @refresh-material-recommendations="refreshMaterialRecommendations"
              @update:materialAssetType="materialAssetType = $event"
              @update:linkedStepId="linkedStepId = $event"
              @update:materialDescription="materialDescription = $event"
              @upload="uploadMaterialAsset"
              @select-material-task="selectMaterialTask"
              @prepare-policy-upload="activeEvidencePackKey = ''; materialAssetType = 'policy_screenshot'; materialDescription = '政策名称：\\n官方来源/链接：\\n证明关系：'"
              @activate-evidence-pack="activateEvidencePack"
              @prepare-evidence-plan-upload="prepareEvidencePlanUpload"
              @confirm-binding="confirmMaterialBinding"
              @clear-confirmed-binding="clearConfirmedMaterialBinding"
            />
          </el-tab-pane>

          <el-tab-pane label="历史大纲" name="outline">
            <div class="outline-list">
              <div v-for="(page, index) in outlinePages" :key="index" class="outline-item">
                <div class="page-number">{{ index + 1 }}</div>
                <div>
                  <h3>{{ page.title || page.section || `第 ${index + 1} 页` }}</h3>
                  <p>{{ page.content || page.summary || page.ppt_text || '暂无摘要' }}</p>
                </div>
              </div>
            </div>
          </el-tab-pane>

          <el-tab-pane label="历史问卷" name="questionnaire">
            <pre class="json-view">{{ prettyQuestionnaire }}</pre>
          </el-tab-pane>

          <el-tab-pane label="生成快照" name="snapshots">
            <div class="snapshot-list">
              <div v-for="snapshot in snapshots" :key="snapshot.id" class="snapshot-item">
                <div class="snapshot-meta">
                  <strong>{{ snapshot.snapshot_type }}</strong>
                  <span>{{ snapshot.stage || '-' }} · v{{ snapshot.version }} · {{ formatDate(snapshot.created_at) }}</span>
                </div>
                <pre class="json-view compact">{{ JSON.stringify(snapshot.payload, null, 2) }}</pre>
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </template>
    </div>

    <el-dialog
      v-model="repairPreviewVisible"
      title="页面级定向修复预览"
      width="92vw"
      class="repair-preview-dialog"
      destroy-on-close
    >
      <div v-if="repairCandidate" class="repair-preview-panel">
        <div class="repair-preview-head">
          <div>
            <span>第 {{ repairCandidate.page_index }} 页 · {{ repairModeText(repairCandidate.repair_mode) }}</span>
            <h3>{{ getOutlineTitle(repairCandidate.page_index) }}</h3>
            <p v-if="repairPreviewAutoEscalationText" class="repair-preview-escalation">
              {{ repairPreviewAutoEscalationText }}
            </p>
          </div>
          <strong :class="qualityStatusClass(repairCandidate.quality_preview?.status)">
            预估 {{ repairCandidate.quality_preview?.score ?? '-' }} 分
          </strong>
        </div>

        <div class="repair-decision-grid">
          <div class="repair-decision-card">
            <span>修复策略</span>
            <strong>{{ repairCandidate.repair_context?.upgrade_mode === 'structure_rebuild' ? '结构重做' : (strategyText(repairCandidate.strategy) || '定向重写') }}</strong>
            <p>{{ repairPreviewDeltaText }}</p>
          </div>
          <div class="repair-decision-card">
            <span>修复前问题</span>
            <strong>{{ repairPreviewBeforeIssues.length }} 个</strong>
            <p>{{ repairPreviewBeforeIssues[0] || '未发现明确失败项，建议重点确认视觉呈现。' }}</p>
          </div>
          <div class="repair-decision-card" :class="repairPreviewAfterIssues.length ? 'warning' : 'success'">
            <span>候选页残留</span>
            <strong>{{ repairPreviewAfterIssues.length }} 个</strong>
            <p>{{ repairPreviewAfterIssues[0] || '候选页当前未发现硬性失败项。' }}</p>
          </div>
          <div class="repair-decision-card" :class="repairPreviewAssessment?.effective ? 'success' : 'warning'">
            <span>本次收益</span>
            <strong>{{ repairPreviewAssessment?.score_delta ?? 0 }} 分</strong>
            <p>{{ repairPreviewAssessment?.summary || '待系统评估修复收益。' }}</p>
          </div>
          <div
            v-if="repairPreviewSeriesValidation?.page_series_type"
            class="repair-decision-card"
            :class="repairPreviewSeriesValidation?.pass ? 'success' : 'warning'"
          >
            <span>页系契约验收</span>
            <strong>{{ repairPreviewSeriesValidation?.pass ? '通过' : '未通过' }}</strong>
            <p>{{ repairPreviewSeriesSummary }}</p>
          </div>
        </div>

        <div
          v-if="repairPreviewContextItems.length || repairPreviewTemplateChips.length || repairPreviewEvidenceHints.length"
          class="repair-context-panel"
        >
          <div v-if="repairPreviewContextItems.length" class="repair-context-block">
            <strong>本次修复依据</strong>
            <p v-for="item in repairPreviewContextItems" :key="item">{{ item }}</p>
          </div>
          <div v-if="repairPreviewTemplateChips.length" class="repair-context-block">
            <strong>版式/角色约束</strong>
            <div class="repair-context-tags">
              <el-tag v-for="chip in repairPreviewTemplateChips" :key="chip" size="small" effect="plain">
                {{ chip }}
              </el-tag>
            </div>
          </div>
          <div v-if="repairPreviewEvidenceHints.length" class="repair-context-block">
            <strong>证据提醒</strong>
            <p v-for="hint in repairPreviewEvidenceHints" :key="hint">{{ hint }}</p>
          </div>
        </div>

        <div class="repair-compare-grid">
          <div class="repair-compare-card">
            <div class="repair-compare-title">当前版本</div>
            <div class="repair-frame-shell">
              <iframe
                :srcdoc="repairCandidate.original_page?.html_content || ''"
                sandbox="allow-same-origin allow-scripts"
              />
            </div>
          </div>
          <div class="repair-compare-card candidate">
            <div class="repair-compare-title">修复候选</div>
            <div class="repair-frame-shell">
              <iframe
                :srcdoc="repairCandidate.html_page?.html_content || ''"
                sandbox="allow-same-origin allow-scripts"
              />
            </div>
          </div>
        </div>
        <div v-if="repairCandidate.quality_preview?.failed_checks?.length" class="repair-preview-warning">
          候选页仍有 {{ repairCandidate.quality_preview.failed_checks.length }} 个质检项需关注，建议确认视觉和表达后再采用。
        </div>
        <div v-if="repairPreviewSeriesIssues.length" class="repair-preview-warning">
          候选页尚未兑现当前页系契约：{{ repairPreviewSeriesIssues.join('；') }}。
        </div>
        <div v-else-if="repairPreviewAfterIssues.length" class="repair-preview-warning">
          候选页仍有 {{ repairPreviewAfterIssues.length }} 个质检项需关注，建议确认视觉和表达后再采用。
        </div>
        <div v-else class="repair-preview-pass">
          候选页已通过当前页面级质检，可以重点人工确认是否符合路演叙事和视觉预期。
        </div>
        <div v-if="repairPreviewNextActionHint" class="repair-preview-next-action">
          <strong>系统建议的下一步</strong>
          <p>{{ repairPreviewNextActionHint }}</p>
        </div>
      </div>
      <template #footer>
        <el-button @click="repairPreviewVisible = false">取消</el-button>
        <el-button
          v-if="repairPreviewNextActionButton"
          plain
          @click="handleRepairPreviewNextAction"
        >
          {{ repairPreviewNextActionButton }}
        </el-button>
        <el-button
          type="primary"
          :loading="applyingRepair"
          :disabled="!repairCandidate?.html_page?.html_content || !repairPreviewAcceptable"
          @click="applyRepairCandidate"
        >
          {{ repairPreviewAcceptable ? '采用修复候选' : '候选页未通过契约验收' }}
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="repairSyncSummaryVisible"
      title="修复同步小结"
      width="640px"
      class="repair-sync-dialog"
      destroy-on-close
    >
      <div v-if="repairSyncSummary" class="repair-sync-panel">
        <div v-if="repairSyncSummary.mode === 'batch'" class="repair-sync-hero batch">
          <div>
            <span>批量修复完成</span>
            <h3>已处理 {{ repairSyncSummary.repaired_count }} / {{ repairSyncSummary.candidate_count }} 个可自动修复页面</h3>
            <p>
              当前仍有 {{ repairSyncSummary.remaining_issue_pages }} 页存在页面级问题，
              {{ repairSyncSummary.skipped_pages.length ? `跳过 ${repairSyncSummary.skipped_pages.length} 页。` : '未发现跳过页。' }}
            </p>
          </div>
          <strong>{{ repairSyncSummary.average_score ?? '-' }} 分</strong>
        </div>

        <div v-else class="repair-sync-hero" :class="qualityStatusClass(repairSyncSummary.quality_status)">
          <div>
            <span>第 {{ repairSyncSummary.page_index }} 页</span>
            <h3>{{ repairSyncSummary.title }}</h3>
            <p>{{ repairSyncSummary.remaining_issues.length ? '候选页仍有问题需要复查。' : '当前页已通过本轮页面级质检。' }}</p>
          </div>
          <strong>{{ repairSyncSummary.quality_score ?? '-' }} 分</strong>
        </div>

        <div class="repair-sync-grid">
          <div
            v-for="item in repairSyncSummary.sync_items"
            :key="item.key"
            class="repair-sync-item"
            :class="item.status"
          >
            <span>{{ item.label }}</span>
            <strong>{{ syncStatusText(item.status) }}</strong>
          </div>
        </div>

        <div class="repair-sync-review">
          <strong>优化任务联动</strong>
          <p v-if="repairSyncSummary.mode === 'batch'">
            已将 {{ repairSyncSummary.review_task_count }} 个批量涉及页面的相关任务标记为“待复查”，并重新生成优化队列。
            若某页问题已经被修掉，对应任务会从新队列中消失。
          </p>
          <p v-else>
            已将 {{ repairSyncSummary.review_task_count }} 个当前页相关任务标记为“待复查”，并重新生成优化队列。
            若问题已经被修掉，对应任务会从新队列中消失。
          </p>
        </div>

        <div v-if="repairSyncSummary.mode === 'batch' && repairSyncSummary.repaired_pages?.length" class="repair-sync-issues batch-pages">
          <strong>已修复页面</strong>
          <p>
            {{ repairSyncSummary.repaired_pages.slice(0, 12).map(page => `第${page.page_index}页`).join('、') }}
            {{ repairSyncSummary.repaired_pages.length > 12 ? '等页面' : '' }}
          </p>
        </div>

        <div v-if="repairSyncSummary.remaining_issues?.length" class="repair-sync-issues">
          <strong>残留问题</strong>
          <p v-for="issue in repairSyncSummary.remaining_issues.slice(0, 4)" :key="issue">{{ issue }}</p>
        </div>
      </div>
      <template #footer>
        <el-button @click="repairSyncSummaryVisible = false">知道了</el-button>
        <el-button
          v-if="repairSyncSummary?.mode !== 'batch' && repairSyncSummary?.remaining_issues?.length"
          type="primary"
          plain
          @click="repairSyncSummaryVisible = false; previewQualityPage(repairSyncSummary.page_index)"
        >
          查看当前页
        </el-button>
        <el-button
          type="primary"
          @click="repairSyncSummaryVisible = false; activeTab = 'health'"
        >
          查看优化队列
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="repairHistoryVisible"
      title="页面修复历史"
      width="760px"
      destroy-on-close
    >
      <div v-loading="repairHistoryLoading" class="repair-history-panel">
        <div v-if="!repairHistoryLoading && repairHistoryRecommendation" class="repair-history-recommendation">
          <div>
            <span>系统推荐动作</span>
            <h3>{{ repairHistoryRecommendation.label }}</h3>
            <p>{{ repairHistoryRecommendation.hint }}</p>
          </div>
          <el-button
            type="primary"
            @click="handleRepairHistoryRecommendation"
          >
            {{ repairHistoryRecommendationActionText }}
          </el-button>
        </div>
        <el-empty
          v-if="!repairHistoryLoading && repairHistoryItems.length === 0"
          description="当前页面暂无可回滚的修复历史。新的单页修复会自动记录版本。"
        />
        <div
          v-for="item in repairHistoryItems"
          :key="item.id"
          class="repair-history-item"
        >
          <div class="repair-history-main">
            <span>快照 #{{ item.id }} · v{{ item.version }} · {{ formatDate(item.created_at) }}</span>
            <h3>{{ item.title || getOutlineTitle(repairHistoryPageIndex) }}</h3>
            <p>
              {{ strategyText(item.strategy) }} · {{ repairModeText(item.repair_mode) }} ·
              原版本 {{ item.original_chars || 0 }} 字符 / 修复版 {{ item.repaired_chars || 0 }} 字符
            </p>
          </div>
          <div class="repair-history-actions">
            <el-button
              size="small"
              :disabled="!item.can_restore_original"
              :loading="rollingBackKey === `${item.id}:original`"
              @click="rollbackRepairVersion(item, 'original')"
            >
              恢复原版本
            </el-button>
            <el-button
              size="small"
              type="primary"
              plain
              :disabled="!item.can_restore_repaired"
              :loading="rollingBackKey === `${item.id}:repaired`"
              @click="rollbackRepairVersion(item, 'repaired')"
            >
              恢复修复版
            </el-button>
          </div>
        </div>
      </div>
    </el-dialog>
  </AiAppShell>
</template>

<script setup>
import { computed, h, nextTick, onBeforeUnmount, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Download, Upload } from '@element-plus/icons-vue'
import AiAppHeader from '@/components/ai-apps/AiAppHeader.vue'
import AiAppShell from '@/components/ai-apps/AiAppShell.vue'
import request from '../utils/request'
import { useAuthStore } from '../stores/auth'
import { usePptDownloadReadiness } from '../composables/usePptDownloadReadiness'
import { usePptCurrentPageWorkspace } from '../composables/usePptCurrentPageWorkspace'
import { usePptRepairWorkspace } from '../composables/usePptRepairWorkspace'
import { usePptWorkbenchNavigation } from '../composables/usePptWorkbenchNavigation'
import { JUDGE_SCORING_CATEGORIES, ROADSHOW_STORY_PHASES } from '../constants/pptHistoryDetail'
import PptDownloadReadinessCard from '../components/ppt/PptDownloadReadinessCard.vue'
import PptHtmlWorkbench from '../components/ppt/PptHtmlWorkbench.vue'
import PptQualityReportPanel from '../components/ppt/PptQualityReportPanel.vue'
import PptRoadshowPanel from '../components/ppt/PptRoadshowPanel.vue'
import PptScoringCoveragePanel from '../components/ppt/PptScoringCoveragePanel.vue'
import PptPracticeDemoPanel from '../components/ppt/PptPracticeDemoPanel.vue'
import PptMaterialsAdvancedPanel from '../components/ppt/PptMaterialsAdvancedPanel.vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const loading = ref(false)
const detail = ref(null)
const activeTab = ref('html')
const currentPageIndex = ref(1)
const selectedScoringPoints = ref([])
const materialAssetType = ref('screenshot')
const materialDescription = ref('')
const linkedStepId = ref('')
const activeEvidencePackKey = ref('')
const materialUploading = ref(false)
const materialRefreshing = ref(false)
const showInlineMaterialTasks = ref(false)
const healthChecking = ref(false)
const queueGenerating = ref(false)
const qualityChecking = ref(false)
const roadshowChecking = ref(false)
const scoringDashboardChecking = ref(false)
const repairingPageIndex = ref(null)
const repairPreviewVisible = ref(false)
const repairCandidate = ref(null)
const applyingRepair = ref(false)
const pageActionFeedback = ref({})
const repairSyncSummaryVisible = ref(false)
const repairSyncSummary = ref(null)
const batchRepairing = ref(false)
const repairHistoryVisible = ref(false)
const repairHistoryLoading = ref(false)
const repairHistory = ref(null)
const repairHistoryPageIndex = ref(1)
const rollingBackKey = ref('')
const updatingOptimizationTaskId = ref('')
const pendingFocusIntent = ref(null)
const lastDeliverabilityIntent = ref(null)
const downloadChecklistActionKey = ref('')
const downloadChecklistFocusKey = ref('')
const downloadReadinessActionFeedback = ref(null)
const downloadingPpt = ref(false)
const pendingDownloadAfterFix = ref(false)
const pageLifecycle = (() => {
  let generation = 1
  let disposed = false
  const controllers = new Set()
  const isCurrent = token => !disposed && token === generation

  return {
    capture() {
      return generation
    },
    isCurrent,
    createController(token) {
      const controller = new AbortController()
      if (!isCurrent(token)) {
        controller.abort()
      } else {
        controllers.add(controller)
      }
      return controller
    },
    releaseController(controller) {
      controllers.delete(controller)
    },
    invalidate() {
      disposed = true
      generation += 1
      controllers.forEach(controller => controller.abort())
      controllers.clear()
    }
  }
})()
const isPageCurrent = token => pageLifecycle.isCurrent(token)
const isAbortError = error => (
  error?.name === 'AbortError'
  || error?.code === 'ERR_CANCELED'
  || error?.message === 'canceled'
)
const downloadCoordinator = (() => {
  const locks = new Set()
  return {
    async runOnce(key, operation) {
      if (locks.has(key)) return { started: false }
      locks.add(key)
      try {
        return { started: true, value: await operation() }
      } finally {
        locks.delete(key)
      }
    }
  }
})()
const previewViewportRef = ref(null)
const previewScale = ref(0.5)

const task = computed(() => detail.value?.task || null)
const htmlPages = computed(() => detail.value?.html_pages || [])
const snapshots = computed(() => detail.value?.snapshots || [])
const outlinePages = computed(() => detail.value?.outline?.pages || [])
const pageIssueProfiles = computed(() => detail.value?.page_issue_profiles?.pages || [])
const qualityReport = computed(() => detail.value?.quality_report || null)
const qualityPages = computed(() => {
  return qualityReport.value?.pages || detail.value?.page_quality_reports || []
})
const htmlQualityGate = computed(() => detail.value?.html_quality_gate || {})
const htmlQualityGateItems = computed(() => htmlQualityGate.value?.items || [])
const roadshowStructure = computed(() => detail.value?.roadshow_structure || null)
const roadshowHealth = computed(() => detail.value?.roadshow_health || null)
const roadshowSequenceEvents = computed(() => roadshowStructure.value?.sequence?.events || [])
const roadshowStoryPhases = computed(() => {
  const pagesByRole = buildPagesByStoryRole()
  const modulePages = buildRoadshowModulePageMap()
  return ROADSHOW_STORY_PHASES.map(phase => {
    const rolePages = phase.roles.flatMap(role => pagesByRole[role] || [])
    const detectedModulePages = phase.module_keys.flatMap(key => modulePages[key] || [])
    const pageIndices = [...new Set([...rolePages, ...detectedModulePages])].sort((a, b) => a - b)
    const sequenceEvents = roadshowSequenceEvents.value.filter(event => {
      if (event.page_index && pageIndices.includes(Number(event.page_index))) return true
      return Array.isArray(event.related_pages) && event.related_pages.map(Number).some(page => pageIndices.includes(page))
    })
    return {
      ...phase,
      page_indices: pageIndices,
      sequence_events: sequenceEvents,
      status: pageIndices.length ? 'ready' : 'missing'
    }
  })
})
const roadshowStorylineCoverage = computed(() => {
  const total = roadshowStoryPhases.value.length
  const ready = roadshowStoryPhases.value.filter(phase => phase.status === 'ready').length
  return { total, ready }
})
const optimizationQueue = computed(() => detail.value?.optimization_queue || null)
const scoringCoverage = computed(() => detail.value?.scoring_coverage || null)
const scoringDashboard = computed(() => detail.value?.scoring_dashboard || null)
const missingRequired = computed(() => scoringCoverage.value?.missing_required || [])
const missingRequiredScoringItems = computed(() => {
  return (scoringCoverage.value?.items || []).filter(item => item.required && !item.covered)
})
const missingRequiredScoringPoints = computed(() => {
  const backendPriority = (scoringCoverage.value?.priority_missing_points || [])
    .map(point => String(point || ''))
    .filter(Boolean)
  if (backendPriority.length) return backendPriority
  return missingRequiredScoringItems.value
    .map(item => String(item.point_name || ''))
    .filter(Boolean)
})
const scoringCoverageTargetPages = computed(() => {
  const backendPointPages = scoringCoverage.value?.point_to_pages || {}
  const fromBackend = missingRequiredScoringPoints.value
    .flatMap(point => Array.isArray(backendPointPages?.[point]) ? backendPointPages[point] : [])
    .map(Number)
    .filter(Boolean)
  const keywordMap = {
    操作规范性: ['操作规范', '规范操作', '输入', '操作', '输出', '步骤', '参数', '验收', '流程'],
    技能熟练度: ['技能熟练', '熟练度', '采集', '配置', '训练', '推理', '部署', '调试', '运行', '演示'],
    任务难易度: ['任务难度', '复杂问题', '难点', '挑战', '复杂', '多源', '轻量化', '断网', '优化', '攻关'],
    技术先进性: ['先进性', '新技术', '前沿', '边缘', '时序', '融合', '物联网', '模型', '算法', '标准'],
    现场讲解效果: ['讲解效果', '表达效果', '汇报结构', '目录', '过渡', '总结', '答辩', '讲解', '重点'],
    职业道德与行为规范: ['职业道德', '行为规范', '合规', '知识产权', '守法', '开发规范'],
    工匠精神: ['工匠精神', '质量意识', '精益求精', '迭代', '复盘', '打磨', '细节', '优化'],
    安全意识: ['安全意识', '安全规范', '风险防范', '安全', '风险', '预案', '防护', '应急', '容灾', '数据安全'],
    实用性: ['实用性', '应用落地', '解决实际问题', '场景', '落地', '服务对象', '解决', '应用', '客户'],
    经济性: ['经济性', '降本增效', '收益测算', '成本', '收益', 'roi', '降本', '增效', '增收', '效率'],
    可持续性: ['可持续性', '绿色低碳', '长期推广', '可持续', '绿色', '低碳', '长期', '维护', '推广路径', '扩展'],
    团队合作: ['团队合作', '团队精神', '沟通协作', '岗位职责', '团队', '分工', '职责', '协作', '沟通', '补位', '共同目标'],
    创新创意: ['创新创意', '创新意识', '创新成效', '原创性', '创新', '原创', '改良', '优化', '突破', '对比']
  }
  const roleBoostMap = {
    操作规范性: ['practice_demo', 'operation_overview', 'practice_result', 'dev_logic'],
    技能熟练度: ['practice_demo', 'operation_overview', 'practice_result', 'dev_logic'],
    任务难易度: ['technical_architecture', 'core_algorithm', 'dev_logic', 'challenge_story'],
    技术先进性: ['technical_architecture', 'core_algorithm', 'innovation'],
    现场讲解效果: ['cover', 'agenda', 'project_definition', 'closing_summary'],
    职业道德与行为规范: ['safety_norms', 'team_collaboration'],
    工匠精神: ['rd_journey', 'technical_architecture', 'practice_demo'],
    安全意识: ['safety_norms', 'practice_demo', 'risk_control'],
    实用性: ['application_value', 'policy_context', 'industry_promotion'],
    经济性: ['application_value', 'economic_value', 'value_matrix'],
    可持续性: ['application_value', 'sustainability', 'industry_promotion'],
    团队合作: ['team_collaboration', 'industry_education'],
    创新创意: ['innovation', 'innovation_points', 'application_value']
  }
  const pointSpecificCandidates = missingRequiredScoringPoints.value.flatMap(point => {
    const keywords = keywordMap[point] || [point]
    const roleHints = roleBoostMap[point] || []
    const matchedPages = outlinePages.value
      .map((page, index) => {
        const text = `${page?.title || ''} ${page?.section || ''} ${page?.content || ''} ${page?.summary || ''}`.toLowerCase()
        const roleText = `${page?.role || ''} ${page?.slide_role || ''}`.toLowerCase()
        const pageIndex = Number(page?.page_index || index + 1)
        const titleHit = keywords.some(keyword => text.includes(String(keyword).toLowerCase()))
        const roleHit = roleHints.some(keyword => roleText.includes(keyword))
        const genericCompetitionHit = ['实操', '技术', '安全', '规范', '团队', '创新', '价值', '答辩', '讲解', '应用'].some(keyword => text.includes(keyword))
        if (!titleHit && !roleHit && !genericCompetitionHit) return null
        let score = 0
        if (titleHit) score += 3
        if (roleHit) score += 2
        if (genericCompetitionHit) score += 1
        if (point === '现场讲解效果' && pageIndex <= 4) score += 1
        if (point === '团队合作' && pageIndex >= 28) score += 1
        if (point === '创新创意' && pageIndex >= 24) score += 1
        return { pageIndex, score }
      })
      .filter(Boolean)
      .sort((a, b) => b.score - a.score || a.pageIndex - b.pageIndex)
      .map(item => item.pageIndex)
    return matchedPages.slice(0, 3)
  })
  const fromEvidence = missingRequiredScoringItems.value.flatMap(item => {
    return (item.evidence || []).map(evidence => Number(evidence.page_index)).filter(Boolean)
  })
  const fromQuality = qualityPages.value
    .filter(page => (page.failed_checks || []).includes('scoring_alignment'))
    .sort((a, b) => {
      const aComplexity = (a.failed_checks || []).length
      const bComplexity = (b.failed_checks || []).length
      if (aComplexity !== bComplexity) return aComplexity - bComplexity
      return Number(a.page_index) - Number(b.page_index)
    })
    .map(page => Number(page.page_index))
    .filter(Boolean)
  const stableFallback = outlinePages.value
    .filter((page, index) => {
      const text = `${page?.title || ''} ${page?.section || ''} ${page?.content || ''} ${page?.summary || ''}`.toLowerCase()
      return ['实操', '技术', '安全', '规范', '团队', '创新', '价值', '应用', '答辩'].some(keyword => text.includes(keyword))
    })
    .map((page, index) => Number(page?.page_index || index + 1))
    .filter(Boolean)
  return [...new Set([...fromBackend, ...fromEvidence, ...pointSpecificCandidates, ...fromQuality, ...stableFallback])].slice(0, 6)
})
const p0TargetPages = computed(() => {
  const group = qualityPriorityGroups.value.find(item => item.level === 'P0')
  return (group?.pages || []).map(page => Number(page.page_index)).filter(Boolean).slice(0, 6)
})
const judgeScoringCategories = computed(() => {
  const dashboardItems = scoringDashboard.value?.items || []
  const coverageItems = scoringCoverage.value?.items || []
  return JUDGE_SCORING_CATEGORIES.map(def => {
    const points = mergeJudgeCategoryPoints(def, dashboardItems, coverageItems)
    const pageIndices = [...new Set(points.flatMap(point => point.page_indices || []))].sort((a, b) => a - b)
    const highRiskCount = points.filter(point => point.risk_level === 'high' || point.covered === false).length
    const mediumRiskCount = points.filter(point => point.risk_level === 'medium').length
    const coveredCount = points.filter(point => point.covered || (point.page_indices || []).length).length
    const materialCount = points.reduce((sum, point) => sum + Number(point.material_count || 0), 0)
    const riskLevel = highRiskCount ? 'high' : (mediumRiskCount ? 'medium' : 'low')
    return {
      ...def,
      points,
      total_count: points.length,
      covered_count: coveredCount,
      high_risk_count: highRiskCount,
      material_count: materialCount,
      page_indices: pageIndices,
      risk_level: riskLevel,
      action: judgeCategoryActionText(def.key, riskLevel, highRiskCount)
    }
  })
})
const practiceDemo = computed(() => detail.value?.practice_demo || null)
const practiceLoopItems = computed(() => {
  return (practiceDemo.value?.steps || []).map(step => {
    const technicalPoints = step.technical_points || []
    const requiredEvidence = step.required_evidence || []
    const missingEvidence = step.missing_evidence || []
    const speakerScript = step.speaker_script || ''
    const checks = [
      { key: 'input', label: '输入', pass: hasPracticeSignal(step, ['输入', '原始', '数据', '设备', '参数']) },
      { key: 'operation', label: '操作', pass: Boolean(step.operation_goal || step.step_title || speakerScript) },
      { key: 'output', label: '输出', pass: hasPracticeSignal(step, ['输出', '结果', '完成', '生成', '入库', '指标']) },
      { key: 'evidence', label: '证据', pass: requiredEvidence.length > 0 && missingEvidence.length === 0 },
      { key: 'scoring', label: '评分点', pass: technicalPoints.length > 0 || hasPracticeSignal(step, ['评分', '规范', '熟练', '先进', '难度']) }
    ]
    const missing = checks.filter(check => !check.pass).map(check => check.label)
    return {
      ...step,
      technical_points: technicalPoints,
      required_evidence: requiredEvidence,
      missing_evidence: missingEvidence,
      target_pages: step.target_pages || [],
      checks,
      complete: missing.length === 0,
      next_action: missing.length
        ? `建议补齐：${missing.join('、')}。`
        : '闭环较完整，建议继续确认现场讲法和证据清晰度。'
    }
  })
})
const practiceLoopSummary = computed(() => {
  const total = practiceLoopItems.value.length
  const complete = practiceLoopItems.value.filter(item => item.complete).length
  return { total, complete }
})
const readinessCards = computed(() => {
  const p0Count = qualityPriorityGroups.value.find(group => group.level === 'P0')?.pages.length || 0
  const storyMissing = roadshowStoryPhases.value.filter(phase => phase.status !== 'ready').length
  const scoringHighRisk = judgeScoringCategories.value.reduce((sum, category) => sum + category.high_risk_count, 0)
  const practiceMissing = practiceLoopItems.value.filter(item => !item.complete).length
  const evidenceWeak = evidenceChainItems.value.filter(item => item.status !== 'ready').length
  return [
    {
      key: 'health',
      label: '总报告',
      value: `${roadshowHealth.value?.overall_score ?? '-'}分`,
      status: readinessStatusFromScore(roadshowHealth.value?.overall_score),
      hint: healthReadinessText(roadshowHealth.value?.readiness),
      tab: 'health'
    },
    {
      key: 'quality',
      label: '页面质量',
      value: `${qualityReport.value?.average_score ?? '-'}分`,
      status: p0Count ? 'danger' : readinessStatusFromScore(qualityReport.value?.average_score),
      hint: p0Count ? `${p0Count} 个 P0 硬伤` : `${qualityReport.value?.issue_count ?? 0} 个待关注`,
      tab: 'quality'
    },
    {
      key: 'storyline',
      label: '故事线',
      value: `${roadshowStorylineCoverage.value.ready}/${roadshowStorylineCoverage.value.total}`,
      status: storyMissing ? 'warning' : 'ready',
      hint: storyMissing ? `${storyMissing} 个阶段缺支撑` : '60分钟结构已覆盖',
      tab: 'roadshow'
    },
    {
      key: 'scoring',
      label: '评分风险',
      value: `${scoringDashboard.value?.score ?? '-'}分`,
      status: scoringHighRisk ? 'danger' : scoringDashboardStatusToReadiness(scoringDashboard.value?.status),
      hint: scoringHighRisk ? `${scoringHighRisk} 个高风险观测点` : '评分支撑较稳定',
      tab: 'coverage'
    },
    {
      key: 'practice',
      label: '实操闭环',
      value: `${practiceLoopSummary.value.complete}/${practiceLoopSummary.value.total}`,
      status: practiceMissing ? 'warning' : 'ready',
      hint: practiceMissing ? `${practiceMissing} 个步骤需补闭环` : '实操闭环较完整',
      tab: 'practice'
    },
    {
      key: 'evidence',
      label: '证据链',
      value: `${evidenceChainSummary.value.ready}/${evidenceChainSummary.value.total}`,
      status: evidenceWeak ? 'warning' : 'ready',
      hint: evidenceWeak ? `${evidenceWeak} 类证据需补强` : `${materialAssets.value.length} 份素材可用`,
      tab: 'materials'
    }
  ]
})
const readinessVerdict = computed(() => {
  const statusPenalty = { ready: 0, warning: 10, danger: 20, unknown: 8 }
  const baseScore = Number(roadshowHealth.value?.overall_score ?? qualityReport.value?.average_score ?? 70)
  const penalty = readinessCards.value.reduce((sum, card) => sum + (statusPenalty[card.status] || 0), 0)
  const score = Math.max(0, Math.min(100, Math.round(baseScore - penalty / 2)))
  if (readinessCards.value.some(card => card.status === 'danger')) {
    return {
      score,
      title: '暂不建议直接上台',
      summary: '仍存在页面硬伤或评分高风险，建议先处理 P0/P1 问题，再进入讲稿和视觉精修。'
    }
  }
  if (readinessCards.value.some(card => card.status === 'warning')) {
    return {
      score,
      title: '可以预览，但还需要补强',
      summary: '整体框架已成型，但故事线、实操闭环或证据链仍有短板，建议继续按下一步建议处理。'
    }
  }
  return {
    score,
    title: '已具备路演打磨基础',
    summary: '页面质量、故事线、评分支撑、实操闭环和证据链整体较稳定，可以进入讲稿节奏和视觉精修。'
  }
})
const finalReviewItems = computed(() => {
  const contractRiskCount = contractRiskPages.value.length
  const contractRejectedCount = contractRiskPages.value.filter(profile => {
    const rejection = profile?.last_contract_rejection || {}
    return Boolean(
      rejection.reason
      || (Array.isArray(rejection.missing_expected_roles) && rejection.missing_expected_roles.length)
      || (Array.isArray(rejection.internal_leaks) && rejection.internal_leaks.length)
    )
  }).length
  const contractRiskHints = Array.from(
    new Set(
      contractRiskPages.value.flatMap(profile =>
        normalizeContractProblemTypes(profile).map(type => {
          const map = {
            contract_mismatch: '页面不像它声明的页面类型',
            series_language_missing: '缺少页系样张的家族视觉语言',
            visual_role_not_realized: '主视觉没有承担应有职责'
          }
          return map[type] || ''
        })
      ).filter(Boolean)
    )
  )
  return [
    {
      key: 'deliverability',
      label: '交付门禁',
      value: deliverabilityVerdict.value.label,
      status: deliverabilityVerdict.value.status === 'ready' ? 'pass' : (deliverabilityVerdict.value.status === 'blocked' ? 'blocked' : 'warning'),
      statusText: deliverabilityVerdict.value.shortHint,
      hint: deliverabilityVerdict.value.summary,
      tab: deliverabilityVerdict.value.status === 'blocked' ? 'quality' : 'health'
    },
    {
      key: 'quality',
      label: '页面质量',
      value: `${qualityReport.value?.average_score ?? '-'} 分`,
      status: qualityReport.value?.overall_status === 'pass' ? 'pass' : (qualityReport.value?.overall_status === 'fail' ? 'blocked' : 'warning'),
      statusText: qualityStatusText(qualityReport.value?.overall_status),
      hint: `${qualityReport.value?.issue_count ?? 0} 个待关注问题，P0 页面优先处理。`,
      tab: 'quality'
    },
    {
      key: 'page_contract',
      label: '页面设计契约',
      value: contractRiskCount ? `${contractRiskCount} 页` : '已通过',
      status: contractRiskCount === 0 ? 'pass' : 'warning',
      statusText: contractRiskCount === 0 ? '页系契约已兑现' : '仍有页系契约未兑现',
      hint: contractRiskCount === 0
        ? '当前重点页已基本长成声明的页面类型和视觉职责。'
        : `${targetPagesText(contractRiskTargetPages.value)} 仍然更像普通 HTML，而不是目标比赛页。优先补强：${contractRiskHints.join('、') || '页面不像该页 / 缺页系语言 / 主视觉没落地'}。${contractRejectedCount ? ` 其中 ${contractRejectedCount} 页最近一次候选页仍未通过比赛页契约验收。` : ''}`,
      tab: 'quality'
    },
    {
      key: 'roadshow',
      label: '路演结构',
      value: `${roadshowStructure.value?.score ?? '-'} 分`,
      status: roadshowStructure.value?.status === 'ready' ? 'pass' : (roadshowStructure.value?.status === 'at_risk' ? 'blocked' : 'warning'),
      statusText: roadshowStatusText(roadshowStructure.value?.status),
      hint: roadshowStructure.value?.summary || '检查 60 分钟比赛结构、顺序和节奏。',
      tab: 'roadshow'
    },
    {
      key: 'scoring',
      label: '评分支撑',
      value: `${scoringDashboard.value?.score ?? '-'} 分`,
      status: scoringDashboard.value?.status === 'stable' ? 'pass' : (scoringDashboard.value?.status === 'high_risk' ? 'blocked' : 'warning'),
      statusText: scoringDashboardStatusText(scoringDashboard.value?.status),
      hint: scoringDashboard.value?.summary || '检查必备评分点是否真正被页面和证据支撑。',
      tab: 'coverage'
    },
    {
      key: 'practice',
      label: '实操闭环',
      value: `${practiceLoopSummary.value.complete}/${practiceLoopSummary.value.total}`,
      status: practiceLoopItems.value.every(item => item.complete) ? 'pass' : (practiceDemo.value?.step_count ? 'warning' : 'blocked'),
      statusText: practiceLoopItems.value.every(item => item.complete) ? '闭环较完整' : '仍需补强',
      hint: `${practiceDemo.value?.missing_evidence_count ?? 0} 项实操证据缺口，需保证输入-操作-输出-证据完整。`,
      tab: 'practice'
    },
    {
      key: 'evidence',
      label: '证据链',
      value: `${materialAssets.value.length} 份`,
      status: evidenceChainItems.value.every(item => item.status === 'ready') ? 'pass' : (materialAssets.value.length ? 'warning' : 'blocked'),
      statusText: evidenceChainItems.value.every(item => item.status === 'ready') ? '证据较稳' : '仍需补证',
      hint: `${evidenceChainItems.value.filter(item => item.status !== 'ready').length} 类证据仍需补强。`,
      tab: 'materials'
    }
  ]
})
const finalReviewSummary = computed(() => {
  const total = finalReviewItems.value.length
  const passed = finalReviewItems.value.filter(item => item.status === 'pass').length
  const blocked = finalReviewItems.value.filter(item => item.status === 'blocked').length
  const warning = finalReviewItems.value.filter(item => item.status === 'warning').length
  return { total, passed, blocked, warning }
})
const finalReviewVerdict = computed(() => {
  const baseScore = Number(readinessVerdict.value?.score || roadshowHealth.value?.overall_score || 70)
  const score = Math.max(0, Math.min(100, Math.round(baseScore - finalReviewSummary.value.blocked * 8 - finalReviewSummary.value.warning * 3)))
  const contractRiskCount = contractRiskPages.value.length
  if (deliverabilityVerdict.value.status === 'blocked' || finalReviewSummary.value.blocked > 0) {
    return {
      status: 'blocked',
      score,
      title: '当前不建议直接作为比赛终稿',
      summary: contractRiskCount
        ? '仍有比赛级阻塞项，且部分页面还没长成目标比赛页。建议先解除阻塞，再继续按页面契约收视觉和讲述。'
        : '仍有比赛级阻塞项或关键模块短板。建议先解除阻塞，再进入最终讲稿联调和视觉润色。'
    }
  }
  if (finalReviewSummary.value.warning > 0) {
    return {
      status: 'warning',
      score,
      title: '可以预演，但正式上台前还需补强',
      summary: contractRiskCount
        ? '骨架和主要内容已具备，但部分页面仍然更像普通 HTML，而不是目标比赛页；建议继续补强证据链、评分支撑和页面契约。'
        : '骨架和主要内容已具备，但证据链、评分支撑或实操闭环还有需要加固的地方。'
    }
  }
  return {
    status: 'ready',
    score,
    title: '已达到比赛终稿进入终审的条件',
    summary: '当前材料已具备较完整的比赛展示基础，可以重点进入讲稿节奏、台上配合和视觉细修。'
  }
})
const finalReviewPassItems = computed(() => {
  return finalReviewItems.value.filter(item => item.status === 'pass')
})

const readinessNextActions = computed(() => {
  const actions = []
  const p0Count = qualityPriorityGroups.value.find(group => group.level === 'P0')?.pages.length || 0
  const storyMissing = roadshowStoryPhases.value.filter(phase => phase.status !== 'ready').length
  const scoringHighRisk = judgeScoringCategories.value.reduce((sum, category) => sum + category.high_risk_count, 0)
  const practiceMissing = practiceLoopItems.value.filter(item => !item.complete).length
  const evidenceWeak = evidenceChainItems.value.filter(item => item.status !== 'ready').length
  const contractRiskCount = contractRiskPages.value.length
  if (deliverabilityVerdict.value.status === 'blocked') {
    actions.push({ key: 'deliverability', priority: 'P0', title: '先解除不可交付状态', hint: deliverabilityVerdict.value.summary, tab: 'quality' })
  }
  if (p0Count) actions.push({ key: 'quality-p0', priority: 'P0', title: `修复 ${p0Count} 个页面硬伤`, hint: '先处理空页、重叠、图表漂移等会直接破坏观感的问题。', tab: 'quality' })
  if (contractRiskCount) actions.push({ key: 'contract-risk', priority: 'P1', title: `收口 ${contractRiskCount} 个页面契约风险`, hint: '这些页还没长成目标比赛页，优先按契约重做页面类型、页系语言和主视觉职责。', tab: 'quality' })
  if (scoringHighRisk) actions.push({ key: 'scoring-risk', priority: 'P1', title: `补强 ${scoringHighRisk} 个评分高风险项`, hint: '按评委评分矩阵补页面、证据和讲解锚点。', tab: 'coverage' })
  if (storyMissing) actions.push({ key: 'story-missing', priority: 'P1', title: `补齐 ${storyMissing} 个故事线阶段`, hint: '按60分钟比赛逻辑补政策、实操、价值或总结阶段。', tab: 'roadshow' })
  if (practiceMissing) actions.push({ key: 'practice-loop', priority: 'P1', title: `补齐 ${practiceMissing} 个实操闭环`, hint: '让每一步都有输入、操作、输出、证据和评分点。', tab: 'practice' })
  if (evidenceWeak) actions.push({ key: 'evidence-chain', priority: 'P2', title: `补强 ${evidenceWeak} 类证据链`, hint: '优先补政策截图、实操截图和评分点支撑材料。', tab: 'materials' })
  return actions.slice(0, 4)
})
const materialAssets = computed(() => detail.value?.material_assets || [])
const materialEvidencePlan = computed(() => detail.value?.material_evidence_plan || null)
const materialEvidenceGroups = computed(() => materialEvidencePlan.value?.groups || [])
const materialEvidencePacks = computed(() => materialEvidencePlan.value?.evidence_packs || [])
const materialUploadTasks = computed(() => {
  const grouped = new Map()
  for (const group of materialEvidenceGroups.value) {
    for (const requirement of group.requirements || []) {
      const pageIndex = Number(requirement.page_index || 0)
      if (!pageIndex) continue
      const key = `${pageIndex}`
      if (!grouped.has(key)) {
        grouped.set(key, {
          key,
          page_index: pageIndex,
          page_title: requirement.page_title || getOutlineTitle(pageIndex),
          status: requirement.status || 'missing',
          required_assets: [],
          reasons: [],
          asset_types: [],
          requirements: [],
          primary_requirement: requirement
        })
      }
      const item = grouped.get(key)
      item.requirements.push(requirement)
      item.required_assets.push(...(requirement.required_assets || []))
      item.reasons.push(...(requirement.reasons || []))
      item.asset_types.push(requirement.asset_type || '')
      if (requirement.status !== 'ready') {
        item.status = 'missing'
        item.primary_requirement = requirement
      }
    }
  }
  return [...grouped.values()]
    .map(item => ({
      ...item,
      required_assets: [...new Set(item.required_assets)].filter(Boolean),
      reasons: [...new Set(item.reasons)].filter(Boolean),
      asset_types: [...new Set(item.asset_types)].filter(Boolean),
      summary: item.reasons[0]
        || `建议补充：${[...new Set(item.required_assets)].slice(0, 3).join('、') || '页面证据素材'}`
    }))
    .sort((a, b) => a.page_index - b.page_index)
})
const materialUploadPendingCount = computed(() => materialUploadTasks.value.filter(item => item.status !== 'ready').length)
const activeMaterialTask = computed(() => {
  if (activeEvidencePack.value?.page_indices?.length) {
    const firstPage = Number(activeEvidencePack.value.page_indices[0])
    return materialUploadTasks.value.find(item => item.page_index === firstPage) || null
  }
  return materialUploadTasks.value.find(item => item.page_index === currentPageIndex.value)
    || materialUploadTasks.value.find(item => item.status !== 'ready')
    || materialUploadTasks.value[0]
    || null
})
const currentPageMaterialTask = computed(() => {
  return materialUploadTasks.value.find(item => Number(item.page_index) === Number(currentPageIndex.value)) || null
})
const previewRelatedMaterialTasks = computed(() => {
  const current = Number(currentPageIndex.value)
  const selectedPages = new Set(selectedMaterialPageIndices.value.map(Number))
  const picked = []
  for (const taskItem of materialUploadTasks.value) {
    const pageIndex = Number(taskItem.page_index || 0)
    if (!pageIndex) continue
    if (
      pageIndex === current
      || selectedPages.has(pageIndex)
      || (taskItem.status !== 'ready' && Math.abs(pageIndex - current) <= 1)
    ) {
      picked.push(taskItem)
    }
  }
  const unique = []
  const seen = new Set()
  for (const taskItem of picked) {
    if (seen.has(taskItem.key)) continue
    seen.add(taskItem.key)
    unique.push(taskItem)
  }
  return unique.slice(0, 4)
})
const activeEvidencePack = computed(() => {
  if (!activeEvidencePackKey.value) return null
  return materialEvidencePacks.value.find(pack => pack.key === activeEvidencePackKey.value) || null
})
const selectedMaterialPageIndices = computed(() => {
  return (activeEvidencePack.value?.page_indices || []).map(Number).filter(Boolean)
})
const policyPages = computed(() => {
  return outlinePages.value
    .map((page, index) => ({ ...page, page_index: index + 1 }))
    .filter(page => isPolicyOutlinePage(page))
})
const policyEvidenceAssets = computed(() => {
  return materialAssets.value.filter(asset => {
    const text = `${asset.asset_type || ''} ${asset.filename || ''} ${asset.description || ''} ${JSON.stringify(asset.analysis_result || {})}`.toLowerCase()
    return asset.asset_type === 'policy_screenshot'
      || asset.asset_type === 'policy_document'
      || ['政策', '官方', '官网', '规划', '指导意见', '通知', 'gov.cn'].some(keyword => text.includes(keyword))
  })
})
const materialDescriptionPlaceholder = computed(() => {
  if (materialAssetType.value === 'policy_screenshot') {
    return '建议填写：政策名称、官方发布单位、网页链接、这张截图用于证明哪条政策依据。'
  }
  if (materialAssetType.value === 'policy_document') {
    return '建议填写：政策文件名称、发布单位、发布日期、与项目方向的关系。'
  }
  return '补充说明：这张图证明什么？用于哪个操作环节？'
})
const materialPrivacyRiskCount = computed(() => {
  return materialAssets.value.filter(asset => asset.privacy_risk && asset.privacy_risk !== 'low').length
})
const practiceEvidenceAssets = computed(() => {
  return materialAssets.value.filter(asset => {
    const analysis = asset.analysis_result || {}
    const text = `${asset.asset_type || ''} ${asset.description || ''} ${asset.filename || ''} ${JSON.stringify(analysis)}`.toLowerCase()
    return ['screenshot', 'image', 'chart', 'video_frame'].includes(asset.asset_type)
      || Boolean(analysis.recommended_step_bindings?.length)
      || ['实操', '操作', '截图', '设备', '数据', '结果', '流程'].some(keyword => text.includes(keyword))
  })
})
const scoringEvidenceAssets = computed(() => {
  return materialAssets.value.filter(asset => {
    const analysis = asset.analysis_result || {}
    const text = `${asset.description || ''} ${JSON.stringify(analysis)}`.toLowerCase()
    return Boolean(analysis.recommended_scoring_bindings?.length)
      || ['评分', '技能', '规范', '创新', '价值', '团队', '安全'].some(keyword => text.includes(keyword))
  })
})
const evidenceChainItems = computed(() => {
  const missingPracticeEvidence = practiceLoopItems.value.filter(item => item.missing_evidence.length || !item.complete)
  const highRiskScoring = judgeScoringCategories.value.reduce((sum, category) => sum + category.high_risk_count, 0)
  return [
    {
      key: 'policy',
      title: '政策官方证据',
      count: policyEvidenceAssets.value.length,
      status: policyEvidenceAssets.value.length ? 'ready' : 'missing',
      description: `识别到 ${policyPages.value.length} 个政策页，建议至少有官网截图或政策文件截图。`,
      tags: policyEvidenceAssets.value.slice(0, 3).map(asset => asset.filename),
      actionText: '上传政策截图',
      action: () => {
        materialAssetType.value = 'policy_screenshot'
        materialDescription.value = '政策名称：\n官方来源/链接：\n证明关系：'
      }
    },
    {
      key: 'practice',
      title: '实操过程证据',
      count: practiceEvidenceAssets.value.length,
      status: missingPracticeEvidence.length ? 'warning' : 'ready',
      description: missingPracticeEvidence.length
        ? `仍有 ${missingPracticeEvidence.length} 个实操步骤缺少闭环或证据。`
        : '实操步骤证据链较完整，继续确认截图可读性和绑定关系。',
      tags: missingPracticeEvidence.slice(0, 3).map(item => `Step ${item.step_order}`),
      actionText: '补实操证据',
      action: () => missingPracticeEvidence[0] && preparePracticeEvidenceUpload(missingPracticeEvidence[0])
    },
    {
      key: 'scoring',
      title: '评分点支撑证据',
      count: scoringEvidenceAssets.value.length,
      status: highRiskScoring ? 'warning' : 'ready',
      description: highRiskScoring
        ? `仍有 ${highRiskScoring} 个评分观测点存在高风险，需要页面或素材支撑。`
        : '评分点证据支撑较稳定，可继续优化表达。',
      tags: judgeScoringCategories.value.filter(item => item.high_risk_count).map(item => item.name),
      actionText: '查看评分风险',
      action: () => { activeTab.value = 'coverage' }
    },
    {
      key: 'privacy',
      title: '隐私与合规风险',
      count: materialPrivacyRiskCount.value,
      status: materialPrivacyRiskCount.value ? 'warning' : 'ready',
      description: materialPrivacyRiskCount.value
        ? '部分素材存在匿名或隐私风险，路演前建议做脱敏处理。'
        : '暂未发现明显素材隐私风险。',
      tags: materialAssets.value.filter(asset => asset.privacy_risk && asset.privacy_risk !== 'low').slice(0, 3).map(asset => asset.filename),
      actionText: '查看风险素材',
      action: null
    }
  ]
})
const evidenceChainSummary = computed(() => {
  const total = evidenceChainItems.value.length
  const ready = evidenceChainItems.value.filter(item => item.status === 'ready').length
  return { total, ready }
})
const batchRepairableCount = computed(() => {
  return qualityPages.value.filter(page => {
    return page.status !== 'pass'
      && page.can_auto_fix
      && (page.repair_route || 'html') === 'html'
      && !page.auto_fix_suspended
      && page.regeneration_strategy !== 'attach_material_evidence'
      && page.regeneration_strategy !== 'attach_policy_evidence'
  }).length
})
const qualityPriorityGroups = computed(() => {
  const groups = [
    {
      level: 'P0',
      title: '必须先修',
      description: '空页、HTML无效、布局重叠、图表漂移、内容不可读等会直接破坏路演观感的问题。',
      pages: []
    },
    {
      level: 'P1',
      title: '重要补强',
      description: '评分点、实操证据、政策依据、页面论点等影响评委判断和专业可信度的问题。',
      pages: []
    },
    {
      level: 'P2',
      title: '最后打磨',
      description: '信息密度、讲解节奏、视觉焦点等影响高级感但不一定阻断预览的问题。',
      pages: []
    }
  ]
  const groupMap = Object.fromEntries(groups.map(group => [group.level, group]))
  qualityPages.value.forEach(page => {
    if (page.status === 'pass') return
    groupMap[qualityPriorityLevel(page)]?.pages.push(page)
  })
  return groups
})
const {
  deliverabilityVerdict,
  deliverabilityBlockerActions,
  contractRiskPages,
  contractRiskTargetPages,
  downloadChecklist,
  downloadReadinessSummary,
  warningSuggestionCount,
  buildDownloadChecklistSnapshot,
  compareDownloadChecklistProgress,
  buildChecklistProgressFeedback
} = usePptDownloadReadiness({
  detail,
  qualityPages,
  pageIssueProfiles,
  qualityReport,
  optimizationQueue,
  scoringCoverage,
  missingRequiredScoringPoints,
  scoringCoverageTargetPages,
  qualityPriorityGroups,
  p0TargetPages,
  targetPagesText
})
const nextPendingDownloadItem = computed(() => {
  return downloadChecklist.value.find(item => !item.done && item.actionable)
    || downloadChecklist.value.find(item => !item.done)
    || null
})

const nextWarningFollowupAction = computed(() => {
  if (deliverabilityVerdict.value.status !== 'warning') return null
  if (nextPendingDownloadItem.value) return null
  const first = deliverabilityBlockerActions.value[0]
  if (!first) return null
  return {
    key: `warning-followup-${first.key || 'item'}`,
    title: first.title || '继续优化当前版本',
    detail: first.hint || '当前版本已经可以下载，但仍建议继续处理这项优化建议。'
  }
})

const downloadFlowFollowupAction = computed(() => {
  return nextPendingDownloadItem.value || nextWarningFollowupAction.value || null
})

function focusDownloadChecklistItem(itemKey, lifecycleToken = pageLifecycle.capture()) {
  if (!itemKey || !isPageCurrent(lifecycleToken)) return
  downloadChecklistFocusKey.value = itemKey
  nextTick(() => {
    if (!isPageCurrent(lifecycleToken)) return
    const element = document.querySelector(`.download-readiness-item[data-checklist-key="${itemKey}"]`)
      || document.querySelector('.download-next-item')
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'center' })
      element.classList.remove('focus-pulse')
      void element.offsetWidth
      element.classList.add('focus-pulse')
      window.setTimeout(() => {
        element.classList.remove('focus-pulse')
      }, 1800)
    }
  })
}

function focusDownloadReadinessCard(lifecycleToken = pageLifecycle.capture()) {
  if (!isPageCurrent(lifecycleToken)) return
  nextTick(() => {
    if (!isPageCurrent(lifecycleToken)) return
    const element = document.querySelector('[data-download-readiness-root="true"]')
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' })
      element.classList.remove('focus-pulse')
      void element.offsetWidth
      element.classList.add('focus-pulse')
      window.setTimeout(() => {
        element.classList.remove('focus-pulse')
      }, 1800)
    }
  })
}

function returnToDownloadFlowFocus() {
  focusDownloadReadinessCard()
  const pending = nextPendingDownloadItem.value
  if (pending?.key) {
    focusDownloadChecklistItem(pending.key)
  }
}

function announceNextDownloadChecklistItem(previousKey = '') {
  const nextItem = downloadChecklist.value.find(item => !item.done && item.key !== previousKey && item.actionable)
    || downloadChecklist.value.find(item => !item.done && item.key !== previousKey)
  if (!nextItem) {
    const followup = nextWarningFollowupAction.value
    focusDownloadReadinessCard()
    if (followup) {
      ElMessage.info(`当前关键下载条件已满足，建议继续：${followup.title}`)
      return
    }
    ElMessage.success('当前下载条件已全部处理完成，可以继续尝试导出')
    return
  }
  focusDownloadReadinessCard()
  focusDownloadChecklistItem(nextItem.key)
  ElMessage.info(`当前这项已处理，建议下一步继续：${nextItem.title}`)
}

function guideToFirstPendingDownloadItem(summary = '') {
  const pending = downloadChecklist.value.find(item => !item.done && item.actionable)
    || downloadChecklist.value.find(item => !item.done)
  if (!pending) return false
  downloadReadinessActionFeedback.value = {
    type: 'warning',
    title: '请先处理当前下载阻塞项',
    summary: summary || pending.detail || '当前版本暂时不能直接下载，请先处理未满足项。',
    points: [
      `当前优先处理：${pending.title}`,
      pending.targetPages?.length ? `关联页面：${targetPagesText(pending.targetPages.slice(0, 4))}` : ''
    ].filter(Boolean),
    allowDownload: false,
    nextPendingItem: pending
  }
  focusDownloadReadinessCard()
  if (pending.key) {
    focusDownloadChecklistItem(pending.key)
  }
  return true
}

function isDownloadFlowFeedback(feedback) {
  const title = `${feedback?.title || ''}`
  return [
    '当前已可直接下载',
    '当前版已可继续下载',
    '仍在下载流程中',
    '继续处理并返回下载',
    '已下载当前版本',
    '已下载可交付版本'
  ].some(keyword => title.includes(keyword))
}

function setDownloadFlowNavigationFeedback(item, summary = '') {
  if (!item) return
  const focusPoints = Array.isArray(item.relatedPoints) ? item.relatedPoints.slice(0, 3) : []
  const focusPages = Array.isArray(item.targetPages) ? item.targetPages.slice(0, 4) : []
  downloadReadinessActionFeedback.value = {
    type: 'warning',
    title: '继续处理并返回下载',
    summary: summary || `已带你进入「${item.title}」处理区，处理完后系统会继续带你回到下载流程。`,
    points: [
      focusPages.length ? `关联页面：${targetPagesText(focusPages)}` : '',
      focusPoints.length ? `优先补：${focusPoints.join('、')}` : ''
    ].filter(Boolean),
    allowDownload: false,
    nextPendingItem: item
  }
}

function exitDownloadFlow() {
  pendingDownloadAfterFix.value = false
  if (isDownloadFlowFeedback(downloadReadinessActionFeedback.value)) {
    downloadReadinessActionFeedback.value = null
  }
  ElMessage.info('已退出下载流程引导，你可以继续按普通编辑节奏处理当前页面。')
}

const {
  applyInitialFocusFromRoute,
  queueIntentFocus,
  markOptimizationTasksInProgressByIntent,
  openWorkbenchIntent,
  handleReadinessAction,
  handleFinalReviewItem,
  openDeliverabilityBlocker
} = usePptWorkbenchNavigation({
  route,
  nextTick,
  request,
  ElMessage,
  activeTab,
  currentPageIndex,
  selectedScoringPoints,
  linkedStepId,
  pendingFocusIntent,
  lastDeliverabilityIntent,
  task,
  detail,
  optimizationQueue,
  qualityPages,
  qualityPriorityGroups,
  deliverabilityBlockerActions,
  judgeScoringCategories,
  practiceLoopItems,
  evidenceChainItems,
  roadshowStoryPhases,
  materialAssetType,
  materialDescription,
  queueIntentFocusMessage: '已跳到对应处理区域',
  qualityPriorityLevel,
  repairPage
})
const healthDimensionItems = computed(() => {
  const scores = roadshowHealth.value?.dimension_scores || {}
  return [
    { key: 'page_quality', label: '页面质量', score: scores.page_quality ?? '-' },
    { key: 'roadshow_structure', label: '结构完整度', score: scores.roadshow_structure ?? '-' },
    { key: 'scoring_risk', label: '评分风险', score: scores.scoring_risk ?? '-' },
    { key: 'practice_demo', label: '实操演示', score: scores.practice_demo ?? '-' },
    { key: 'material_evidence', label: '素材证据', score: scores.material_evidence ?? '-' },
    { key: 'pacing', label: '讲解节奏', score: scores.pacing ?? '-' }
  ]
})
const {
  currentHtml,
  previewCanvasStyle,
  currentOutlinePage,
  currentPageQuality,
  currentPageActionFeedback,
  currentPagePrimaryAction,
  currentPageScript,
  currentPageGoal,
  currentPageFailedMessages,
  currentPageGateItems,
  currentPageSequenceEvents,
  currentPageTemplateChips,
  currentPracticeRows,
  currentPageEvidenceHints,
  currentPageLinkedAssets,
  currentPageRecommendedAssets
} = usePptCurrentPageWorkspace({
  currentPageIndex,
  previewScale,
  pageActionFeedback,
  htmlPages,
  outlinePages,
  qualityPages,
  htmlQualityGateItems,
  roadshowSequenceEvents,
  currentPageMaterialTask,
  materialAssets,
  policyEvidenceAssets,
  getPageLinkedAssets,
  pageHasEvidenceFailure,
  repairActionButtonText,
  resolvedRepairRouteReason,
  pageRoleText,
  failedCheckMessages,
  isPolicyOutlinePage
})
const {
  repairHistoryItems,
  repairHistoryRecommendation,
  repairHistoryRecommendationActionText,
  repairPreviewContext,
  repairPreviewAssessment,
  repairPreviewAutoEscalation,
  repairPreviewAutoEscalationText,
  repairPreviewBeforeIssues,
  repairPreviewAfterIssues,
  repairPreviewContextItems,
  repairPreviewTemplateChips,
  repairPreviewEvidenceHints,
  repairPreviewSeriesValidation,
  repairPreviewAcceptable,
  repairPreviewSeriesIssues,
  repairPreviewSeriesSummary,
  repairPreviewNextAction,
  repairPreviewNextActionButton,
  repairPreviewNextActionHint,
  repairPreviewDeltaText
} = usePptRepairWorkspace({
  repairHistory,
  repairCandidate,
  repairPreviewNextActionText,
  strategyText,
  pageRoleText,
  failedCheckMessages,
  gateActionText,
  gateCheckText,
  sequenceSeverityText
})

const taskStatusText = computed(() => {
  const statusMap = {
    completed: '已完成',
    outline_ready: '大纲待确认',
    generating: '生成中',
    rendering: '渲染中',
    failed: '生成失败',
    cancelled: '已取消'
  }
  return statusMap[task.value?.status] || task.value?.status || '未知状态'
})

const downloadActionText = computed(() => {
  if (pendingDownloadAfterFix.value) {
    if (deliverabilityVerdict.value.status === 'blocked') return '查看并继续下载'
    if (deliverabilityVerdict.value.status === 'warning') return '继续下载当前版本'
    return '继续下载'
  }
  if (deliverabilityVerdict.value.status === 'blocked') return '查看下载条件'
  if (deliverabilityVerdict.value.status === 'warning') return '下载当前版本'
  return '下载 PPT'
})

const prettyQuestionnaire = computed(() => {
  const questionnaire = detail.value?.questionnaire
  return JSON.stringify(questionnaire?.responses || questionnaire || {}, null, 2)
})

onMounted(() => {
  loadDetail()
  window.addEventListener('resize', updatePreviewScale)
  nextTick(updatePreviewScale)
})

onBeforeUnmount(() => {
  pageLifecycle.invalidate()
  ElMessageBox.close()
})

onUnmounted(() => {
  window.removeEventListener('resize', updatePreviewScale)
})

watch(
  () => [activeTab.value, currentPageIndex.value, currentHtml.value],
  async () => {
    await nextTick()
    updatePreviewScale()
  }
)

async function loadDetail() {
  const lifecycleToken = pageLifecycle.capture()
  const controller = pageLifecycle.createController(lifecycleToken)
  if (!isPageCurrent(lifecycleToken)) return
  loading.value = true
  const rawId = String(route.params.id || '').trim()
  try {
    // 1) 优先尝试旧版数字 task 的 history-detail
    try {
      const res = await request.get(`/api/ppt/task/${rawId}/history-detail`, {
        signal: controller.signal,
        silentError: true
      })
      if (!isPageCurrent(lifecycleToken)) return
      const payload = res?.data || res
      // 空对象 / 无关键字段视为无效，进入 job 历史回退
      if (payload && (payload.task || payload.html_pages || payload.pages || payload.deliverability)) {
        detail.value = payload
        currentPageIndex.value = htmlPages.value[0]?.page_index || 1
        applyInitialFocusFromRoute()
        return
      }
    } catch (legacyErr) {
      if (isAbortError(legacyErr) || !isPageCurrent(lifecycleToken)) return
    }

    // 2) 新版 agent 历史（job_id 字符串，如 cd5b08a55c4e）→ 跳转编辑器打开
    try {
      const res = await request.get(`/api/ppt/history/${rawId}`, {
        signal: controller.signal,
        silentError: true
      })
      if (!isPageCurrent(lifecycleToken)) return
      const job = res?.data?.job || res?.job
      if (job?.job_id || rawId) {
        ElMessage.info('正在打开历史生成任务…')
        await router.replace({
          path: '/ppt-editor',
          query: { job: String(job?.job_id || rawId) }
        })
        return
      }
    } catch (agentErr) {
      if (isAbortError(agentErr) || !isPageCurrent(lifecycleToken)) return
    }

    if (isPageCurrent(lifecycleToken)) {
      ElMessage.error('加载 PPT 历史详情失败：记录不存在或无权访问')
      detail.value = null
    }
  } catch (err) {
    if (isPageCurrent(lifecycleToken) && !isAbortError(err)) {
      ElMessage.error('加载 PPT 历史详情失败')
    }
  } finally {
    pageLifecycle.releaseController(controller)
    if (isPageCurrent(lifecycleToken)) {
      loading.value = false
    }
  }
}

function blockerCountOf(deliverability = {}) {
  if (Array.isArray(deliverability?.blocker_details) && deliverability.blocker_details.length) {
    return deliverability.blocker_details.length
  }
  return Array.isArray(deliverability?.blockers) ? deliverability.blockers.length : 0
}

function compareDeliverabilityProgress(previous, next) {
  const prevStatus = previous?.status || 'unknown'
  const nextStatus = next?.status || 'unknown'
  const prevCount = blockerCountOf(previous)
  const nextCount = blockerCountOf(next)
  const order = { blocked: 0, warning: 1, ready: 2, unknown: -1 }

  if (order[nextStatus] > order[prevStatus]) {
    return {
      type: 'success',
      message: `交付状态已从「${previous?.label || prevStatus}」提升为「${next?.label || nextStatus}」`
    }
  }

  if (nextStatus === prevStatus && nextCount < prevCount) {
    return {
      type: 'success',
      message: nextStatus === 'warning'
        ? `已减少 ${prevCount - nextCount} 项补强建议`
        : `已解除 ${prevCount - nextCount} 个交付阻塞项`
    }
  }

  if (nextStatus === 'ready' && prevStatus !== 'ready') {
    return {
      type: 'success',
      message: '当前材料已进入“可交付”状态，可继续做终审和讲稿联调'
    }
  }

  if (nextStatus === prevStatus && nextCount === prevCount) {
    return {
      type: 'info',
      message: nextStatus === 'warning'
        ? '交付状态已刷新，当前补强建议数量暂未变化'
        : '交付状态已刷新，当前阻塞项数量暂未变化'
    }
  }

  return null
}

function applyWorkspaceState(latest) {
  if (!latest) return
  if (!detail.value) {
    detail.value = latest
    return
  }
  detail.value = {
    ...detail.value,
    deliverability: latest.deliverability || detail.value.deliverability,
    optimization_queue: latest.optimization_queue || detail.value.optimization_queue,
    roadshow_health: latest.roadshow_health || detail.value.roadshow_health,
    roadshow_structure: latest.roadshow_structure || detail.value.roadshow_structure,
    scoring_coverage: latest.scoring_coverage || detail.value.scoring_coverage,
    scoring_dashboard: latest.scoring_dashboard || detail.value.scoring_dashboard,
    practice_demo: latest.practice_demo || detail.value.practice_demo,
    material_evidence_plan: latest.material_evidence_plan || detail.value.material_evidence_plan,
    material_assets: latest.material_assets || detail.value.material_assets,
    quality_report: latest.quality_report || detail.value.quality_report,
    page_issue_profiles: latest.page_issue_profiles || detail.value.page_issue_profiles
  }
}

async function refreshDeliverabilitySnapshot(
  options = {},
  lifecycleToken = pageLifecycle.capture(),
  externalSignal = null
) {
  const taskId = task.value?.id
  if (!taskId || !isPageCurrent(lifecycleToken)) return
  const controller = externalSignal ? null : pageLifecycle.createController(lifecycleToken)
  const signal = externalSignal || controller?.signal
  try {
    const previousDeliverability = detail.value?.deliverability || null
    const previousChecklist = buildDownloadChecklistSnapshot(downloadChecklist.value)
    const res = await request.post(
      `/api/ppt/task/${taskId}/workspace-refresh`,
      undefined,
      { signal }
    )
    if (!isPageCurrent(lifecycleToken)) return
    const latest = res.data || res || {}
    applyWorkspaceState(latest)
    if (options.resetScoringHighlight) {
      selectedScoringPoints.value = []
    }
    const checklistDelta = compareDownloadChecklistProgress(previousChecklist, buildDownloadChecklistSnapshot(downloadChecklist.value))
    const checklistFeedback = buildChecklistProgressFeedback(checklistDelta, downloadChecklist.value, options.intentLabel || '')
    let pageFeedbackPayload = null
    if (checklistFeedback) {
      const nextFeedback = {
        ...checklistFeedback,
        updatedAt: Date.now()
      }
      if (pendingDownloadAfterFix.value && latest.deliverability?.status && latest.deliverability.status !== 'blocked') {
        const nextPending = downloadFlowFollowupAction.value
        nextFeedback.type = latest.deliverability.status === 'ready' ? 'success' : 'warning'
        nextFeedback.title = latest.deliverability.status === 'ready' ? '当前已可直接下载' : '当前版已可继续下载'
        nextFeedback.summary = latest.deliverability.status === 'ready'
          ? '刚刚处理的下载阻塞项已解除，现在可以直接下载可交付版本。'
          : '刚刚处理的下载阻塞项已解除，现在可以先下载当前版本，也可以继续处理剩余建议项。'
        nextFeedback.allowDownload = true
        nextFeedback.nextPendingItem = latest.deliverability.status === 'ready' ? null : nextPending
        if (latest.deliverability.status !== 'ready' && nextPending) {
          nextFeedback.points = [
            ...(Array.isArray(nextFeedback.points) ? nextFeedback.points : []),
            `建议继续：${nextPending.title}`,
            nextPending.detail || ''
          ].filter(Boolean).slice(0, 3)
        }
      } else if (pendingDownloadAfterFix.value && latest.deliverability?.status === 'blocked') {
        const nextPending = downloadChecklist.value.find(item => !item.done && item.actionable)
          || downloadChecklist.value.find(item => !item.done)
        nextFeedback.title = '仍在下载流程中'
        nextFeedback.summary = nextPending
          ? `刚刚处理后，下载条件仍未全部满足。继续处理「${nextPending.title}」后，系统会再次带你回到下载流程。`
          : '刚刚处理后，下载条件仍未全部满足，请继续处理剩余未满足项。'
        nextFeedback.nextPendingItem = nextPending || null
      }
      downloadReadinessActionFeedback.value = nextFeedback
      focusDownloadReadinessCard(lifecycleToken)
      pageFeedbackPayload = nextFeedback
    } else if (options.clearChecklistFeedback) {
      downloadReadinessActionFeedback.value = null
    }
    if (options.feedbackPageIndex) {
      if (pageFeedbackPayload) {
        setPageActionFeedback(options.feedbackPageIndex, pageFeedbackPayload)
      }
    }
    if (options.announceProgress && latest.deliverability) {
      const progress = compareDeliverabilityProgress(previousDeliverability, latest.deliverability)
      const sourceHint = options.intentLabel || lastDeliverabilityIntent.value?.title || ''
      if (progress?.type === 'success') {
        ElMessage.success(sourceHint ? `${progress.message}，本次处理聚焦：「${sourceHint}」` : progress.message)
        lastDeliverabilityIntent.value = null
      } else if (progress?.type === 'info') {
        ElMessage.info(sourceHint ? `${progress.message}，当前关注项仍是「${sourceHint}」` : progress.message)
      }
    }
  } catch (err) {
    if (!isPageCurrent(lifecycleToken) || isAbortError(err)) return
    console.warn('刷新交付状态快照失败:', err)
    try {
      const res = await request.get(`/api/ppt/task/${taskId}/history-detail`, { signal })
      if (!isPageCurrent(lifecycleToken)) return
      const latest = res.data || res || {}
      if (detail.value && latest) {
        detail.value = {
          ...detail.value,
          ...latest
        }
      }
    } catch (fallbackErr) {
      if (isPageCurrent(lifecycleToken) && !isAbortError(fallbackErr)) {
        console.warn('回退读取历史详情失败:', fallbackErr)
      }
    }
  } finally {
    if (controller) {
      pageLifecycle.releaseController(controller)
    }
  }
}

function getOutlineTitle(pageIndex) {
  const page = outlinePages.value[pageIndex - 1]
  return page?.title || page?.section || `第 ${pageIndex} 页`
}

function getOutlinePage(pageIndex) {
  return outlinePages.value[pageIndex - 1] || {}
}

function buildPagesByStoryRole() {
  const result = {}
  outlinePages.value.forEach((page, index) => {
    const role = page.slide_role || page.page_role || inferStoryRoleFromPage(page)
    if (!role) return
    if (!result[role]) result[role] = []
    result[role].push(index + 1)
  })
  return result
}

function buildRoadshowModulePageMap() {
  const result = {}
  ;(roadshowStructure.value?.modules || []).forEach(module => {
    if (!module?.key) return
    result[module.key] = module.page_indices || []
  })
  return result
}

function inferStoryRoleFromPage(page = {}) {
  const text = [
    page.title,
    page.section,
    page.phase,
    page.content,
    page.summary,
    page.ppt_text
  ].filter(Boolean).join(' ').toLowerCase()
  const rules = [
    ['agenda', ['目录', '汇报路径', '议程']],
    ['policy_context', ['policy', '政策', '官方', '规划', '指导意见', '国家战略', '地方政策']],
    ['project_definition', ['项目定义', '项目定位', '是什么']],
    ['market_pain', ['痛点', '需求', '问题', '行业现状']],
    ['solution_overview', ['解决方案', '方案总览', '总体方案']],
    ['technical_architecture', ['架构', '技术栈', '核心技术', '系统设计']],
    ['practice_demo', ['实操', '演示', '操作', '流程', '入库', '清洗', '部署']],
    ['application_value', ['应用价值', '经济性', '可持续', '社会价值', '乡村振兴']],
    ['innovation', ['创新', '先进性', '原创']],
    ['safety_norms', ['安全', '规范', '职业素养', '知识产权']],
    ['team_collaboration', ['团队', '分工', '岗位职责', '协作']],
    ['rd_journey', ['研发历程', '迭代', '里程碑']],
    ['industry_education', ['产教融合', '校企合作', '合作探究']],
    ['future_plan', ['未来', '规划', '路线']],
    ['summary', ['总结', '成果', '答辩']]
  ]
  const matched = rules.find(([, keywords]) => keywords.some(keyword => text.includes(keyword)))
  return matched?.[0] || ''
}

function pageQualityStatus(pageIndex) {
  const page = qualityPages.value.find(item => Number(item.page_index) === Number(pageIndex))
  return page?.status ? `is-${page.status}` : 'is-unknown'
}

function pageQualityLabel(pageIndex) {
  const page = qualityPages.value.find(item => Number(item.page_index) === Number(pageIndex))
  if (!page) return '待质检'
  if (page.status === 'pass') return `${page.score ?? '-'}分 可用`
  if (page.status === 'warning') return `${page.score ?? '-'}分 待打磨`
  if (page.status === 'fail') return `${page.score ?? '-'}分 需修复`
  return `${page.score ?? '-'}分`
}

function pageRoleText(role) {
  const map = {
    cover: '首页',
    agenda: '目录',
    policy_context: '政策依据',
    project_definition: '项目定义',
    solution_overview: '方案总览',
    market_pain: '痛点需求',
    technical_architecture: '技术架构',
    practice_demo: '实操演示',
    application_value: '应用价值',
    innovation: '创新亮点',
    safety_norms: '安全规范',
    team_collaboration: '团队协作',
    rd_journey: '研发历程',
    industry_education: '产教融合',
    future_plan: '未来规划',
    summary: '总结'
  }
  return map[role] || role || '普通页'
}

function formatDate(date) {
  if (!date) return '-'
  return new Date(date).toLocaleString('zh-CN')
}

function qualityStatusText(status) {
  const map = {
    pass: '整体可用于路演预览',
    warning: '存在需要关注的页面',
    fail: '存在明显生成问题'
  }
  return map[status] || '暂无质量结论'
}

function qualityStatusClass(status) {
  return `is-${status || 'unknown'}`
}

function qualityPriorityLevel(page = {}) {
  if (!page || page.status === 'pass') return 'P3'
  const failed = new Set(page.failed_checks || [])
  const visualProblems = new Set((getPageIssueProfile(page)?.visual_problems || []).map(problem => problem?.type))
  const strategy = page.regeneration_strategy || ''
  const p0Checks = new Set([
    'placeholder_content',
    'industry_consistency',
    'html_valid',
    'no_fallback_shell',
    'not_empty',
    'meaningful_content',
    'viewport_fit',
    'layout_collision',
    'diagram_integrity'
  ])
  const p1Checks = new Set([
    'template_page_risk',
    'scoring_alignment',
    'practice_steps',
    'operation_io_evidence',
    'material_evidence',
    'policy_evidence',
    'page_argument'
  ])
  if (page.status === 'fail' || [...failed].some(check => p0Checks.has(check))) return 'P0'
  if ([...visualProblems].some(type => ['contract_mismatch', 'series_language_missing', 'visual_role_not_realized'].includes(type))) return 'P1'
  if ([...failed].some(check => p1Checks.has(check))) return 'P1'
  if (['attach_material_evidence', 'attach_policy_evidence', 'align_scoring_points', 'enrich_practice_steps', 'rewrite_page_argument', 'remove_placeholder_content', 'align_industry_language'].includes(strategy)) {
    return 'P1'
  }
  return 'P2'
}

function qualityPriorityReason(page = {}) {
  const level = qualityPriorityLevel(page)
  const failed = new Set(page.failed_checks || [])
  const visualProblems = new Set((getPageIssueProfile(page)?.visual_problems || []).map(problem => problem?.type))
  const strategy = page.regeneration_strategy || ''
  if (level === 'P0') {
    if (failed.has('placeholder_content')) return 'P0 硬伤：页面仍含待补充、截图位或未完成占位文案'
    if (failed.has('industry_consistency')) return 'P0 硬伤：页面混入了不属于当前项目赛道的术语'
    if (failed.has('layout_collision')) return 'P0 硬伤：存在文字、卡片或图表重叠风险'
    if (failed.has('diagram_integrity')) return 'P0 硬伤：流程图/架构图可能不完整或连接线漂移'
    if (failed.has('meaningful_content') || failed.has('not_empty')) return 'P0 硬伤：页面有效内容不足，疑似降级页'
    if (failed.has('html_valid') || failed.has('viewport_fit')) return 'P0 硬伤：HTML 或 16:9 画布存在风险'
    return 'P0 硬伤：当前页不建议直接进入路演预览'
  }
  if (level === 'P1') {
    if (visualProblems.has('contract_mismatch')) return 'P1 补强：页面没有长成它声明的页面类型，建议按契约整页重做'
    if (visualProblems.has('series_language_missing')) return 'P1 补强：页面缺少对应页系样张的家族视觉语言'
    if (visualProblems.has('visual_role_not_realized')) return 'P1 补强：主视觉没有承担应有的讲述任务或焦点职责'
    if (failed.has('template_page_risk')) return 'P1 补强：页面模板化明显，项目专属性不足'
    if (strategy === 'remove_placeholder_content') return 'P1 补强：建议先去掉占位内容，再补证据素材'
    if (strategy === 'align_industry_language') return 'P1 补强：建议统一行业术语，避免跨赛道表达'
    if (strategy === 'attach_policy_evidence') return 'P1 补强：政策依据缺少官方截图或来源'
    if (strategy === 'attach_material_evidence') return 'P1 补强：实操或成果缺少素材证据'
    if (failed.has('scoring_alignment')) return 'P1 补强：评分点支撑不够清晰'
    if (failed.has('operation_io_evidence')) return 'P1 补强：实操输入、操作、输出、证据闭环不足'
    return 'P1 补强：会影响专业可信度和评委判断'
  }
  return 'P2 打磨：建议优化信息密度、讲解节奏或视觉焦点'
}

function healthReadinessText(readiness) {
  const map = {
    ready: '可打磨',
    needs_work: '需补强',
    not_ready: '不建议'
  }
  return map[readiness] || '待体检'
}

function healthReadinessClass(readiness) {
  return `is-${readiness || 'unknown'}`
}

function deliverabilityClass(status) {
  return `is-${status || 'unknown'}`
}

function scoringPointMatches(pointName) {
  if (!pointName) return false
  return selectedScoringPoints.value.includes(String(pointName))
}

function judgeCategoryHasHighlightedPoint(category) {
  return Array.isArray(category?.points) && category.points.some(point => scoringPointMatches(point.point_name))
}

function readinessStatusFromScore(score) {
  const numeric = Number(score)
  if (Number.isNaN(numeric)) return 'unknown'
  if (numeric >= 85) return 'ready'
  if (numeric >= 70) return 'warning'
  return 'danger'
}

function scoringDashboardStatusToReadiness(status) {
  if (status === 'stable') return 'ready'
  if (status === 'watch') return 'warning'
  if (status === 'high_risk') return 'danger'
  return 'unknown'
}

function roadshowStatusText(status) {
  const map = {
    ready: '结构完整，可进入路演打磨',
    needs_focus: '结构基本成立，需重点补强',
    at_risk: '结构风险较高，建议先补骨架'
  }
  return map[status] || '暂无结构结论'
}

function roadshowStatusClass(status) {
  return `is-${status || 'unknown'}`
}

function roadshowModuleStatusText(status) {
  const map = {
    ready: '已具备',
    partial: '需补强',
    missing: '缺失'
  }
  return map[status] || status || '待判断'
}

function storyPhaseStatusText(status) {
  const map = {
    ready: '已覆盖',
    partial: '需补强',
    missing: '缺失'
  }
  return map[status] || '待判断'
}

function sequenceEventPhaseName(event = {}) {
  const pageIndex = Number(event.page_index || 0)
  const relatedPages = Array.isArray(event.related_pages) ? event.related_pages.map(Number) : []
  const phase = roadshowStoryPhases.value.find(item => {
    if (pageIndex && item.page_indices.includes(pageIndex)) return true
    return relatedPages.some(page => item.page_indices.includes(page))
  })
  return phase?.name || '整篇结构'
}

function sequenceSeverityText(severity) {
  const map = {
    high: '高优先级',
    medium: '需调整',
    low: '可优化',
    info: '通过'
  }
  return map[severity] || '需关注'
}

function scoringDashboardStatusText(status) {
  const map = {
    stable: '评分点支撑较稳定',
    watch: '存在中风险评分点',
    high_risk: '存在高风险丢分项'
  }
  return map[status] || '暂无评分风险结论'
}

function scoringDashboardStatusClass(status) {
  return `is-${status || 'unknown'}`
}

function riskLevelText(level) {
  const map = {
    high: '高风险',
    medium: '中风险',
    low: '低风险'
  }
  return map[level] || level || '待判断'
}

function mergeJudgeCategoryPoints(def, dashboardItems, coverageItems) {
  const normalize = value => `${value || ''}`.toLowerCase()
  const matchedDashboard = dashboardItems.filter(item => {
    const text = normalize(`${item.category} ${item.point_name} ${item.action} ${(item.risk_reasons || []).join(' ')}`)
    return def.keywords.some(keyword => text.includes(normalize(keyword)))
  })
  const matchedCoverage = coverageItems.filter(item => {
    const text = normalize(`${item.category} ${item.point_name} ${item.hint}`)
    return def.keywords.some(keyword => text.includes(normalize(keyword)))
  })
  const byName = new Map()
  matchedCoverage.forEach(item => {
    byName.set(item.point_name, {
      ...item,
      risk_level: item.covered ? 'low' : 'high',
      page_indices: (item.evidence || []).map(evidence => evidence.page_index).filter(Boolean)
    })
  })
  matchedDashboard.forEach(item => {
    const existing = byName.get(item.point_name) || {}
    byName.set(item.point_name, {
      ...existing,
      ...item,
      covered: existing.covered || Boolean(item.page_indices?.length),
      page_indices: item.page_indices || existing.page_indices || []
    })
  })
  return [...byName.values()]
}

function judgeCategoryActionText(key, riskLevel, highRiskCount) {
  if (riskLevel === 'low') return '当前支撑较稳定，建议保持证据链清晰并优化讲稿表达。'
  const map = {
    skill: `优先补实操步骤、操作结果和技术难点证明，当前 ${highRiskCount} 项可能影响 60 分主权重。`,
    professional: '补安全规范、知识产权、开发规范和职业行为说明，不要只放口号。',
    value: '补应用场景、经济性、可持续性和社会价值证据，测试阶段可先绑定临时演示素材。',
    team: '补岗位职责、协作机制、现场配合和突发情况应对，体现团队合作观测点。',
    innovation: '补创新点与创新成效的前后对比，避免只写“采用 AI/大数据”等泛化表述。'
  }
  return map[key] || '补齐支撑页、证据素材和现场讲解锚点。'
}

function taskTypeText(type) {
  const map = {
    scoring: '评分点',
    evidence: '证据素材',
    practice: '实操演示',
    page_quality: '页面质量',
    pacing: '讲解节奏',
    roadshow: '路演结构',
    quality: '基础质量',
    health: '总报告'
  }
  return map[type] || type || '优化任务'
}

function optimizationActionText(item) {
  const map = {
    evidence: '去上传素材',
    scoring: '去看评分点',
    practice: '去看实操',
    page_quality: '生成修复预览',
    pacing: '去调整页面',
    roadshow: '去看结构',
    quality: '去质量报告',
    health: '查看总报告'
  }
  return map[item?.task_type] || '开始处理'
}

function isOptimizationTaskDone(item) {
  return item?.status === 'done'
}

function optimizationTaskStatusText(item) {
  const map = {
    done: '已处理',
    in_progress: '待复查',
    skipped: '已跳过',
    todo: '待处理'
  }
  return map[item?.status] || '待处理'
}

function optimizationTaskTagType(item) {
  if (item?.status === 'done') return 'success'
  if (item?.status === 'in_progress') return 'warning'
  if (item?.status === 'skipped') return 'info'
  return item?.priority === 'P0' ? 'danger' : (item?.priority === 'P1' ? 'warning' : 'info')
}

function syncStatusText(status) {
  const map = {
    success: '已同步',
    failed: '失败',
    skipped: '跳过'
  }
  return map[status] || '待同步'
}

function pacingStatusText(status) {
  const map = {
    smooth: '讲解节奏顺畅',
    needs_trim: '需要压缩或补过渡',
    at_risk: '节奏风险较高'
  }
  return map[status] || '暂无节奏结论'
}

function normalizeChecks(checks) {
  if (!checks || typeof checks !== 'object') return []
  return Object.entries(checks).map(([key, item]) => ({
    key,
    label: item.label || '检查项',
    pass: Boolean(item.pass),
    message: item.message || ''
  }))
}

function getPageIssueProfile(page = {}) {
  return pageIssueProfiles.value.find(item => Number(item.page_index) === Number(page.page_index)) || null
}

function visualProblemTypeText(type) {
  const map = {
    contract_mismatch: '页面契约未兑现：这页看起来不像它声明的页面类型或内容职责',
    series_language_missing: '页系语言缺失：没有体现同一风格样张家族应有的统一视觉语言',
    visual_role_not_realized: '主视觉职责未落地：页面声明了主视觉任务，但截图里没有真正形成焦点'
  }
  return map[type] || ''
}

function profileVisualProblemSummaries(page = {}) {
  const profile = getPageIssueProfile(page)
  if (!profile || !Array.isArray(profile.visual_problems)) return []
  return profile.visual_problems
    .map(problem => {
      const mapped = visualProblemTypeText(problem?.type)
      if (!mapped) return ''
      const description = String(problem?.description || '').trim()
      return description ? `${mapped}。${description}` : mapped
    })
    .filter(Boolean)
}

function failedCheckMessages(page) {
  const messages = normalizeChecks(page?.checks)
    .filter(check => !check.pass)
    .map(check => `${check.label}：${check.message || '需要进一步优化'}`)
  for (const summary of profileVisualProblemSummaries(page).slice(0, 2)) {
    if (!messages.some(message => message.includes(summary))) {
      messages.push(`视觉审查：${summary}`)
    }
  }
  return messages
}

function pageRiskBadges(page = {}) {
  const failed = new Set(page.failed_checks || [])
  const visualProblems = new Set((getPageIssueProfile(page)?.visual_problems || []).map(problem => problem?.type))
  const contractRejection = getPageIssueProfile(page)?.last_contract_rejection || {}
  const badges = []
  if (failed.has('placeholder_content')) badges.push('终稿占位词')
  if (failed.has('industry_consistency')) badges.push('跨行业污染')
  if (failed.has('template_page_risk')) badges.push('模板页风险')
  if (visualProblems.has('contract_mismatch')) badges.push('页面契约未兑现')
  if (visualProblems.has('series_language_missing')) badges.push('页系语言缺失')
  if (visualProblems.has('visual_role_not_realized')) badges.push('主视觉职责未落地')
  if (contractRejection.reason || (contractRejection.missing_expected_roles || []).length || (contractRejection.internal_leaks || []).length) {
    badges.push('候选页未过契约门')
  }
  if (page.auto_fix_suspended) badges.push('重复修复未收敛')
  return badges
}

function pageIssueProfileSummary(page = {}) {
  const profile = getPageIssueProfile(page)
  if (!profile) return []
  const lines = []
  const currentRoute = inferCurrentRepairRoute(page) || profile.primary_problem_type
  if (currentRoute) {
    lines.push(`问题类型：${repairRouteLabel(currentRoute)}`)
  }
  if (profile.contract_id || profile.page_type) {
    lines.push(`页面契约：${profile.contract_id || profile.page_type}`)
  }
  if (profile.page_series_type || profile.page_visual_role) {
    lines.push(`设计职责：${profile.page_series_type || '未定义'} / ${profile.page_visual_role || '未定义'}`)
  }
  if (profile.repair_attempts) {
    lines.push(`累计修复：${profile.repair_attempts} 次`)
  }
  if (profile.recommended_action) {
    lines.push(`推荐动作：${repairPreviewNextActionText(profile.recommended_action)}`)
  }
  const visualSummary = profileVisualProblemSummaries(page)[0]
  if (visualSummary) {
    lines.push(`视觉缺陷：${visualSummary}`)
  }
  const contractRejection = profile.last_contract_rejection || {}
  if (contractRejection.reason || (contractRejection.missing_expected_roles || []).length || (contractRejection.internal_leaks || []).length) {
    const roleLabelMap = {
      system_diagram: '系统主图',
      supporting_argument: '技术支撑说明',
      operation_stage_board: '实操闭环主区',
      evidence_wall: '证据墙主区',
      value_matrix: '价值矩阵主区',
      closing_signal: '收束主视觉'
    }
    const roleLabel = (contractRejection.missing_expected_roles || [])
      .map(role => roleLabelMap[role] || role)
      .filter(Boolean)[0]
    const leakLabel = (contractRejection.internal_leaks || [])[0]
    lines.push(
      roleLabel
        ? `候选页未过契约验收：仍缺 ${roleLabel}`
        : leakLabel
          ? `候选页未过契约验收：仍暴露内部词 ${leakLabel}`
          : `候选页未过契约验收：${contractRejection.reason || contractRejection.summary}`
    )
  }
  const contractLabels = contractVisualIssueLabels(page)
  if (contractLabels.length) {
    lines.push(`比赛页标准：当前候选页若仍缺 ${contractLabels[0]}，将不会被正式采用`)
  }
  if (Array.isArray(profile.must_not_repeat) && profile.must_not_repeat.length) {
    lines.push(`避免重复：${profile.must_not_repeat[0]}`)
  }
  return lines.slice(0, 4)
}

function pageHasEvidenceFailure(page = {}) {
  const failed = new Set(page.failed_checks || [])
  return failed.has('material_evidence') || failed.has('policy_evidence')
}

function parseAssetAnalysis(asset = {}) {
  if (typeof asset.analysis_result === 'string') {
    try {
      return JSON.parse(asset.analysis_result)
    } catch {
      return {}
    }
  }
  return asset.analysis_result || {}
}

function getPageLinkedAssets(pageIndex) {
  const targetPage = Number(pageIndex || 0)
  if (!targetPage) return []
  return materialAssets.value.filter(asset => {
    const analysis = parseAssetAnalysis(asset)
    const explicitBindings = (analysis.confirmed_page_indices || [])
      .map(Number)
      .filter(Boolean)
    if (explicitBindings.includes(targetPage)) return true
    const description = `${asset.description || ''}`
    const filename = `${asset.filename || ''}`.toLowerCase()
    return description.includes(`第${targetPage}页`)
      || filename.includes(`page${targetPage}`)
  })
}

function resolvedRepairRouteReason(page = {}) {
  const rawReason = page?.repair_route_reason || ''
  if (!rawReason) return ''
  const currentRoute = inferCurrentRepairRoute(page)
  if (currentRoute === 'evidence' && !pageHasEvidenceFailure(page)) {
    return ''
  }
  if (pageHasEvidenceFailure(page)) {
    return rawReason
  }
  if (currentRoute === 'structure' && (
    rawReason.includes('缺少截图')
    || rawReason.includes('政策来源')
    || rawReason.includes('素材证据')
    || rawReason.includes('先补证据')
  )) {
    return '当前剩余问题主要在结构表达、评分点承载或页面模板化，建议继续整页重做。'
  }
  if (currentRoute === 'html' && (
    rawReason.includes('缺少截图')
    || rawReason.includes('政策来源')
    || rawReason.includes('素材证据')
    || rawReason.includes('先补证据')
  )) {
    return '当前缺图问题已不是主要矛盾，请继续处理占位词、模板化或页面表达问题。'
  }
  return rawReason
}

function inferCurrentRepairRoute(page = {}) {
  const failed = new Set(page.failed_checks || [])
  const linkedAssetCount = getPageLinkedAssets(page.page_index).length
  const nonEvidenceFailures = [...failed].filter(key => !['material_evidence', 'policy_evidence'].includes(key))
  if (pageHasEvidenceFailure(page) && !(linkedAssetCount && nonEvidenceFailures.length)) return 'evidence'
  if (
    failed.has('template_page_risk')
    || failed.has('scoring_alignment')
    || failed.has('practice_step_detail')
    || failed.has('operation_io_evidence')
    || failed.has('narrative_readiness')
    || failed.has('speaker_script')
  ) {
    return 'structure'
  }
  if (page.repair_route && page.repair_route !== 'evidence') {
    return page.repair_route
  }
  return 'html'
}

function repairActionButtonText(page = {}) {
  const currentRoute = inferCurrentRepairRoute(page)
  if (currentRoute === 'evidence') return '去补素材证据'
  if (currentRoute === 'structure') return '升级重做此页'
  if (!page?.auto_fix_suspended) return '生成修复预览'
  if (page.repair_next_action === 'materials') return '去补素材证据'
  return '查看修复历史'
}

function repairRouteLabel(route) {
  const map = {
    html: 'HTML修复',
    structure: '结构重做',
    evidence: '证据补充'
  }
  return map[route] || '页面处理'
}

function repairPreviewNextActionText(action) {
  const map = {
    accept_candidate: '采用当前候选',
    attach_evidence: '先补素材证据',
    structure_rebuild: '升级重做此页',
    retry_or_restore: '查看修复历史或恢复较优版本',
    restore_best_repaired: '恢复推荐版本',
    repair_html: '继续修复HTML'
  }
  return map[action] || '继续处理'
}

function strategyText(strategy) {
  const map = {
    regenerate_html: '重新生成该页 HTML',
    remove_placeholder_content: '清理待补充/截图位等占位内容',
    align_industry_language: '校正页面术语，消除跨行业表达',
    reduce_density_or_split_page: '减少文字密度，必要时拆分页面',
    fix_viewport_css: '修复 16:9 画布与 overflow 样式',
    enrich_practice_steps: '补充实操步骤、关键技术和操作结果',
    attach_material_evidence: '上传或绑定截图、设备照片、数据图等素材证据',
    attach_policy_evidence: '补充官方政策链接、截图或文件来源',
    align_scoring_points: '补充页面服务的评分点或调整页面目标',
    rewrite_page_argument: '重写页面标题、核心论点和讲解支点',
    fix_layout_hierarchy: '重排视觉层级，消除文字、卡片、图表重叠',
    rebuild_diagram_layout: '重建流程图/架构图，让节点和连接线完整可读',
    enrich_visual_focus: '补充主视觉焦点，避免页面空洞或像普通网页'
  }
  return map[strategy] || strategy
}

function gateActionText(action) {
  const map = {
    ai_retry_passed: '已自动触发 AI 单页重写，并通过生成期 P0 门禁',
    fallback_after_retry_failed: 'AI 二次修复后仍未通过，已使用安全兜底页避免坏页进入预览'
  }
  return map[action] || action || '已执行生成期处理'
}

function gateCheckText(check) {
  const map = {
    html_valid: 'HTML结构',
    viewport_fit: '16:9画布',
    no_fallback_shell: '非降级页',
    meaningful_content: '有效内容',
    layout_collision: '布局重叠',
    diagram_integrity: '图表完整',
    visual_focus: '视觉焦点'
  }
  return map[check] || check
}

function coverageEvidenceText(item) {
  const evidences = Array.isArray(item.evidence) ? item.evidence : []
  const pages = evidences
    .map(evidence => `第${evidence.page_index}页「${evidence.title || '未命名'}」`)
    .join('、')
  const scoreBlocks = evidences
    .filter(evidence => evidence.source === 'score_evidence_block')
    .map(evidence => {
      const hint = String(evidence.content_hint || '').trim()
      return hint || String(evidence.evidence_type || '').trim()
    })
    .filter(Boolean)
  if (pages && scoreBlocks.length) {
    return `覆盖页面：${pages}；评分证据：${scoreBlocks.slice(0, 2).join('；')}`
  }
  if (pages) {
    return `覆盖页面：${pages}；建议继续补可验证的比赛评分证据。`
  }
  return '已在大纲中覆盖，建议继续补充可验证的比赛评分证据。'
}

function demoModeText(mode) {
  const map = {
    onsite: '现场演示',
    ppt: 'PPT 展示',
    fallback: '兜底说明'
  }
  return map[mode] || '演示建议'
}

function hasPracticeSignal(step = {}, keywords = []) {
  const text = [
    step.step_title,
    step.operation_goal,
    step.speaker_script,
    step.fallback_script,
    ...(step.technical_points || []),
    ...(step.required_evidence || [])
  ].filter(Boolean).join(' ')
  return keywords.some(keyword => text.includes(keyword))
}

function targetPagesText(pages) {
  if (!Array.isArray(pages) || pages.length === 0) return '待绑定页面'
  return pages.map(page => `第${page}页`).join('、')
}

function listText(list) {
  if (!Array.isArray(list) || list.length === 0) return ''
  return list.join('、')
}

function buildMaterialUploadFeedback(previousPlan, nextPlan, packKey) {
  const nextPacks = Array.isArray(nextPlan?.evidence_packs) ? nextPlan.evidence_packs : []
  const prevPacks = Array.isArray(previousPlan?.evidence_packs) ? previousPlan.evidence_packs : []
  const currentPack = nextPacks.find(pack => pack.key === packKey) || null
  const previousPack = prevPacks.find(pack => pack.key === packKey) || null
  const missingCount = Number(nextPlan?.missing_count || 0)
  const remainingTitles = nextPacks
    .filter(pack => pack.status !== 'ready')
    .slice(0, 2)
    .map(pack => pack.title)

  if (!currentPack) {
    return missingCount > 0
      ? `素材证据已上传，当前还剩 ${missingCount} 组证据包待补。`
      : '素材证据已上传，关键证据包已全部覆盖。'
  }

  const pageText = currentPack.page_indices?.length ? targetPagesText(currentPack.page_indices) : '相关页面'
  const becameReady = previousPack && previousPack.status !== 'ready' && currentPack.status === 'ready'
  const remainingText = missingCount > 0
    ? `；当前还剩 ${missingCount} 组待补${remainingTitles.length ? `（${remainingTitles.join('、')}）` : ''}`
    : '；当前关键证据包已全部覆盖'

  if (becameReady) {
    return `「${currentPack.title}」已覆盖，关联 ${pageText}${remainingText}。`
  }

  if (currentPack.status === 'ready') {
    return `已继续补强「${currentPack.title}」，关联 ${pageText}${remainingText}。`
  }

  return `已上传到「${currentPack.title}」，关联 ${pageText}；当前这组还需继续补强${remainingText}。`
}

function buildUploadedAssetBindingText(asset) {
  const analysis = typeof asset?.analysis_result === 'string'
    ? (() => {
        try { return JSON.parse(asset.analysis_result) } catch { return {} }
      })()
    : (asset?.analysis_result || {})
  const boundPages = (analysis?.confirmed_page_indices || [])
    .map(Number)
    .filter(Boolean)
  if (!boundPages.length) return ''
  return `已确认绑定 ${targetPagesText(boundPages.slice(0, 4))}`
}

function setPageActionFeedback(pageIndex, payload = {}) {
  if (!pageIndex) return
  pageActionFeedback.value = {
    ...pageActionFeedback.value,
    [pageIndex]: {
      type: payload.type || 'info',
      title: payload.title || '已更新当前页',
      summary: payload.summary || '',
      points: Array.isArray(payload.points) ? payload.points.filter(Boolean).slice(0, 3) : [],
      allowDownload: Boolean(payload.allowDownload),
      nextPendingItem: payload.nextPendingItem || null
    }
  }
}

function contractVisualIssueLabels(page) {
  const issues = new Set(normalizeContractProblemTypes(page))
  const labels = []
  if (issues.has('contract_mismatch')) labels.push('页面不像它声明的页面类型')
  if (issues.has('series_language_missing')) labels.push('缺少页系样张的家族视觉语言')
  if (issues.has('visual_role_not_realized')) labels.push('主视觉没有承担应有职责')
  return labels
}

function normalizeContractProblemTypes(profile = {}) {
  const problems = Array.isArray(profile?.visual_problems) ? profile.visual_problems : []
  return problems
    .map(problem => (typeof problem === 'string' ? problem : (problem?.type || '')))
    .filter(Boolean)
}

function getNextPendingEvidencePack(plan, currentPackKey = '') {
  const packs = Array.isArray(plan?.evidence_packs) ? plan.evidence_packs : []
  const candidates = packs.filter(pack => pack.status !== 'ready')
  if (!candidates.length) return null
  return candidates.find(pack => pack.key !== currentPackKey) || candidates[0] || null
}

async function offerNextEvidencePack(previousPlan, nextPlan, packKey) {
  if (!packKey || Number(nextPlan?.missing_count || 0) <= 0) return

  const nextPacks = Array.isArray(nextPlan?.evidence_packs) ? nextPlan.evidence_packs : []
  const prevPacks = Array.isArray(previousPlan?.evidence_packs) ? previousPlan.evidence_packs : []
  const currentPack = nextPacks.find(pack => pack.key === packKey) || null
  const previousPack = prevPacks.find(pack => pack.key === packKey) || null
  const becameReady = currentPack && currentPack.status === 'ready' && (!previousPack || previousPack.status !== 'ready')
  if (!becameReady) return

  const nextPack = getNextPendingEvidencePack(nextPlan, packKey)
  if (!nextPack) return

  try {
    await ElMessageBox.confirm(
      `「${currentPack.title}」已补齐。下一组建议优先处理「${nextPack.title}」，可覆盖 ${targetPagesText(nextPack.page_indices)}。`,
      '继续补下一组',
      {
        confirmButtonText: `去补「${nextPack.title}」`,
        cancelButtonText: '稍后再说',
        type: 'info'
      }
    )
    activateEvidencePack(nextPack)
  } catch {
    // 用户选择稍后处理时不额外提示
  }
}

function materialTypeText(type) {
  const map = {
    policy_screenshot: '政策官网截图',
    policy_document: '政策文件材料',
    screenshot: '系统截图',
    image: '设备照片',
    chart: '数据图表',
    video_frame: '视频关键帧',
    document: '文档材料'
  }
  return map[type] || type || '素材'
}

function isPolicyOutlinePage(page = {}) {
  const text = [
    page.slide_role,
    page.title,
    page.section,
    page.phase,
    page.content,
    page.summary,
    page.ppt_text
  ].filter(Boolean).join(' ').toLowerCase()
  return ['policy', '政策', '官方', '国家战略', '地方政策', '产业政策', '规划', '指导意见'].some(keyword => text.includes(keyword))
}

function materialQualityText(quality) {
  const map = {
    high: '高质量',
    medium: '可用',
    low: '需优化'
  }
  return map[quality] || '待判断'
}

function evidenceChainStatusText(status) {
  const map = {
    ready: '较完整',
    warning: '需补强',
    missing: '缺失'
  }
  return map[status] || '待判断'
}

async function uploadMaterialAsset(options) {
  if (!task.value?.id) {
    ElMessage.error('任务不存在，无法上传素材')
    return
  }

  materialUploading.value = true
  const previousPlan = materialEvidencePlan.value
  const currentPackKey = activeEvidencePackKey.value
  try {
    const formData = new FormData()
    formData.append('file', options.file)
    formData.append('asset_type', materialAssetType.value)
    formData.append('description', materialDescription.value || '')
    if (linkedStepId.value) {
      formData.append('linked_step_id', linkedStepId.value)
    }

    const res = await request.post(`/api/ppt/task/${task.value.id}/materials`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    const asset = res.data || res
    detail.value.material_assets = [asset, ...materialAssets.value]
    await refreshWorkbenchAfterMutation({
      refreshMaterials: true,
      refreshQuality: true,
      announceProgress: true,
      intentLabel: '素材证据上传',
      feedbackPageIndex: currentPageIndex.value
    })
    const nextPlan = detail.value?.material_evidence_plan || null
    materialDescription.value = ''
    linkedStepId.value = ''
    options.onSuccess?.(asset)
    const bindingText = buildUploadedAssetBindingText(asset)
    const currentTask = currentPageMaterialTask.value
    setPageActionFeedback(currentPageIndex.value, {
      type: 'success',
      title: '已补当前页素材',
      summary: `${buildMaterialUploadFeedback(previousPlan, nextPlan, currentPackKey)}${bindingText ? ` ${bindingText}。` : ''}`,
      points: [
        currentTask?.summary || '',
        nextPlan?.missing_count > 0 ? `还剩 ${nextPlan?.missing_count} 组证据待补` : '当前关键证据包已全部覆盖'
      ]
    })
    ElMessage.success(`${buildMaterialUploadFeedback(previousPlan, nextPlan, currentPackKey)}${bindingText ? ` ${bindingText}。` : ''} 当前页质检已同步刷新。`)
    await offerNextEvidencePack(previousPlan, nextPlan, currentPackKey)
  } catch (err) {
    options.onError?.(err)
    ElMessage.error('素材上传失败')
  } finally {
    materialUploading.value = false
  }
}

async function refreshMaterialRecommendations() {
  if (!task.value?.id) return
  materialRefreshing.value = true
  try {
    const res = await request.post(`/api/ppt/task/${task.value.id}/materials/recommendations/refresh`)
    detail.value.material_assets = res.data || res || []
    await refreshDeliverabilitySnapshot({ announceProgress: false })
    ElMessage.success('素材绑定已刷新，显式页码和步骤选择会被确认为硬绑定')
  } catch {
    ElMessage.error('刷新绑定推荐失败')
  } finally {
    materialRefreshing.value = false
  }
}

function replaceMaterialAssetInDetail(asset) {
  if (!asset || !detail.value) return
  const current = detail.value.material_assets || []
  const next = current.map(item => (String(item.id) === String(asset.id) ? asset : item))
  detail.value.material_assets = next
}

async function confirmMaterialBinding({ asset, bindingType, targetKey, targetLabel }) {
  if (!task.value?.id || !asset?.id || !bindingType || !targetKey) return
  materialRefreshing.value = true
  try {
    const res = await request.post(`/api/ppt/task/${task.value.id}/materials/${asset.id}/bindings/confirm`, {
      binding_type: bindingType,
      target_key: String(targetKey),
      target_label: targetLabel || ''
    })
    const updated = res.data || res
    replaceMaterialAssetInDetail(updated)
    await refreshWorkbenchAfterMutation({
      refreshMaterials: true,
      refreshQuality: true,
      announceProgress: false,
      intentLabel: '素材硬绑定确认',
      feedbackPageIndex: currentPageIndex.value
    })
    ElMessage.success(`已确认这份素材绑定到${bindingType === 'page' ? `${targetLabel || `第${targetKey}页`}` : targetLabel || targetKey}`)
  } catch (err) {
    ElMessage.error(err?.response?.data?.detail || '确认素材硬绑定失败')
  } finally {
    materialRefreshing.value = false
  }
}

async function clearConfirmedMaterialBinding({ asset, bindingType, targetKey }) {
  if (!task.value?.id || !asset?.id || !bindingType || !targetKey) return
  materialRefreshing.value = true
  try {
    const res = await request.delete(`/api/ppt/task/${task.value.id}/materials/${asset.id}/bindings`, {
      params: {
        binding_type: bindingType,
        target_key: String(targetKey)
      }
    })
    const updated = res.data || res
    replaceMaterialAssetInDetail(updated)
    await refreshWorkbenchAfterMutation({
      refreshMaterials: true,
      refreshQuality: true,
      announceProgress: false,
      intentLabel: '素材硬绑定移除',
      feedbackPageIndex: currentPageIndex.value
    })
    ElMessage.success('已移除这份素材的硬绑定')
  } catch (err) {
    ElMessage.error(err?.response?.data?.detail || '移除素材硬绑定失败')
  } finally {
    materialRefreshing.value = false
  }
}

async function confirmCurrentPageMaterialBinding(asset) {
  if (!asset) return
  await confirmMaterialBinding({
    asset,
    bindingType: 'page',
    targetKey: String(currentPageIndex.value),
    targetLabel: `第${currentPageIndex.value}页`
  })
}

async function clearCurrentPageMaterialBinding(asset) {
  if (!asset) return
  await clearConfirmedMaterialBinding({
    asset,
    bindingType: 'page',
    targetKey: String(currentPageIndex.value)
  })
}

function prefillMaterialRequirement(requirement, options = {}) {
  if (!requirement) return
  const {
    switchTab = false,
    announce = true,
    pageIndex = requirement.page_index || null,
    title = requirement.title || requirement.page_title || '证据补强'
  } = options
  const relatedPack = materialEvidencePacks.value.find(pack =>
    (pack.requirements || []).some(item => item.key === requirement.key)
  )
  activeEvidencePackKey.value = relatedPack?.key || ''
  if (switchTab) activeTab.value = 'materials'
  materialAssetType.value = requirement.asset_type || 'screenshot'
  linkedStepId.value = requirement.linked_step_id || ''
  materialDescription.value = requirement.upload_description_template
    || `对应页面：第${requirement.page_index}页「${requirement.page_title || getOutlineTitle(requirement.page_index)}」\n证据类型：${requirement.title || '素材证据'}\n证明内容：`
  if (switchTab) {
    pendingFocusIntent.value = {
      tab: 'materials',
      pageIndex: pageIndex || null,
      relatedPoints: [],
      stepId: requirement.linked_step_id || '',
      title
    }
    queueIntentFocus()
  }
  if (announce) {
    ElMessage.info(`已按第${requirement.page_index}页证据要求预填上传信息`)
  }
}

function prefillCurrentPageMaterial(requirement = null, options = {}) {
  const targetRequirement = requirement
    || currentPageMaterialTask.value?.primary_requirement
    || currentPageMaterialTask.value?.requirements?.[0]
  if (targetRequirement) {
    prefillMaterialRequirement(targetRequirement, {
      switchTab: false,
      announce: true,
      pageIndex: currentPageIndex.value,
      title: `第${currentPageIndex.value}页素材补强`,
      ...options
    })
    return
  }
  activeEvidencePackKey.value = ''
  materialAssetType.value = isPolicyOutlinePage(currentOutlinePage.value || {}) ? 'policy_screenshot' : 'screenshot'
  materialDescription.value = isPolicyOutlinePage(currentOutlinePage.value || {})
    ? `政策名称：\n官方来源/链接：\n对应页面：第${currentPageIndex.value}页「${getOutlineTitle(currentPageIndex.value)}」\n证明关系：`
    : `对应页面：第${currentPageIndex.value}页「${getOutlineTitle(currentPageIndex.value)}」\n证明内容：`
  if (options.announce !== false) {
    ElMessage.info('已按当前页预填补图信息')
  }
  setPageActionFeedback(currentPageIndex.value, {
    type: 'info',
    title: '已准备当前页补图',
    summary: `上传表单已按第${currentPageIndex.value}页预填，现在可以直接给这页上传截图、结果图或政策来源图。`,
    points: [currentPageMaterialTask.value?.summary || '优先补当前页最缺的素材证据']
  })
}

function openMaterialForCurrentPage() {
  prefillCurrentPageMaterial(null, { announce: false })
  activeTab.value = 'materials'
  pendingFocusIntent.value = { tab: 'materials', pageIndex: currentPageIndex.value, relatedPoints: [], stepId: '', title: `第${currentPageIndex.value}页素材补强` }
  queueIntentFocus()
  ElMessage.info(isPolicyOutlinePage(currentOutlinePage.value || {}) ? '已切到政策证据上传，并预填当前页信息' : '已切到素材证据上传，并预填当前页信息')
}

function openMaterialWorkspaceForCurrentPage() {
  openMaterialForCurrentPage()
}

function toggleInlineMaterialTasks() {
  showInlineMaterialTasks.value = !showInlineMaterialTasks.value
  if (showInlineMaterialTasks.value && currentPageMaterialTask.value) {
    prefillCurrentPageMaterial(currentPageMaterialTask.value.primary_requirement || currentPageMaterialTask.value.requirements?.[0], { announce: false })
  }
}

function prepareCurrentPageMaterialInline() {
  prefillCurrentPageMaterial()
}

async function handleCurrentPagePrimaryAction() {
  const action = currentPagePrimaryAction.value
  if (action.mode === 'history') {
    await openRepairHistory(currentPageIndex.value)
    setPageActionFeedback(currentPageIndex.value, {
      type: 'warning',
      title: '已打开修复历史',
      summary: '这页历史修复较多，先看有没有更稳的历史版本，再决定是否继续处理。',
      points: ['优先检查是否存在可恢复的较优版本']
    })
    return
  }
  if (action.mode === 'material') {
    showInlineMaterialTasks.value = true
    prepareCurrentPageMaterialInline()
    return
  }
  if (action.mode === 'contract' && currentPageQuality.value) {
    await repairPage({
      ...currentPageQuality.value,
      repair_route: 'structure',
      regeneration_strategy: 'structure_rebuild'
    })
    return
  }
  if (action.mode === 'repair' && currentPageQuality.value) {
    await repairPage(currentPageQuality.value)
    return
  }
  previewQualityPage(currentPageIndex.value)
  setPageActionFeedback(currentPageIndex.value, {
    type: 'info',
    title: '已切到质量视角',
    summary: '当前页没有明显硬伤，先看这页最新质检结论和评分支点即可。'
  })
}

function preparePracticeEvidenceUpload(step) {
  activeEvidencePackKey.value = ''
  activeTab.value = 'materials'
  materialAssetType.value = 'screenshot'
  linkedStepId.value = step.step_id || ''
  materialDescription.value = `对应实操步骤：${step.step_order}. ${step.step_title}\n对应页面：${targetPagesText(step.target_pages)}\n建议补充证据：${listText(step.missing_evidence) || listText(step.required_evidence)}\n证明内容：`
  pendingFocusIntent.value = { tab: 'materials', pageIndex: step.target_pages?.[0] || null, relatedPoints: [], stepId: step.step_id || '', title: step.step_title || '实操步骤证据补强' }
  queueIntentFocus()
  ElMessage.info('已切到素材证据上传，并预填当前实操步骤')
}

function prepareEvidencePlanUpload(requirement) {
  if (!requirement) return
  prefillMaterialRequirement(requirement, {
    switchTab: true,
    announce: true,
    pageIndex: requirement.page_index || null,
    title: requirement.title || requirement.page_title || '证据补强'
  })
}

function selectMaterialTask(taskItem) {
  if (!taskItem) return
  showInlineMaterialTasks.value = true
  activeEvidencePackKey.value = ''
  currentPageIndex.value = Number(taskItem.page_index) || currentPageIndex.value
  prefillMaterialRequirement(taskItem.primary_requirement || taskItem.requirements?.[0], {
    switchTab: false,
    announce: true,
    pageIndex: taskItem.page_index || null,
    title: taskItem.page_title || '证据补强'
  })
}

function activateEvidencePack(pack) {
  if (!pack) return
  activeEvidencePackKey.value = pack.key || ''
  activeTab.value = 'materials'
  if (Array.isArray(pack.page_indices) && pack.page_indices.length) {
    currentPageIndex.value = Number(pack.page_indices[0]) || currentPageIndex.value
  }
  if (pack.primary_requirement) {
    materialAssetType.value = pack.primary_requirement.asset_type || 'screenshot'
    linkedStepId.value = pack.primary_requirement.linked_step_id || ''
    materialDescription.value = pack.primary_requirement.upload_description_template
      || `证据包：${pack.title}\n覆盖页面：${targetPagesText(pack.page_indices)}\n建议素材：${listText(pack.required_assets)}\n证明内容：`
    pendingFocusIntent.value = {
      tab: 'materials',
      pageIndex: pack.page_indices?.[0] || null,
      relatedPoints: [],
      stepId: pack.primary_requirement.linked_step_id || '',
      title: pack.title || '证据包上传'
    }
    queueIntentFocus()
  } else {
    materialAssetType.value = pack.asset_type || 'screenshot'
    linkedStepId.value = ''
    materialDescription.value = `证据包：${pack.title}\n覆盖页面：${targetPagesText(pack.page_indices)}\n建议素材：${listText(pack.required_assets)}\n证明内容：`
  }
  ElMessage.info(`已切换到「${pack.title}」上传表单，并高亮关联页面`)
}

function clearEvidencePackFocus() {
  activeEvidencePackKey.value = ''
}

function buildPageRepairContext(page) {
  const outlinePage = getOutlinePage(page.page_index)
  const issueProfile = pageIssueProfiles.value.find(item => Number(item.page_index) === Number(page.page_index)) || null
  const placeholderAnalysis = page.placeholder_analysis || {}
  const industryAnalysis = page.industry_analysis || {}
  const templateAnalysis = page.template_analysis || {}
  const failedChecks = new Set(page.failed_checks || [])
  const repairRoute = inferCurrentRepairRoute(page)
  return {
    source: 'preview_adjustment_workbench',
    page_index: page.page_index,
    title: getOutlineTitle(page.page_index),
    slide_role: outlinePage.slide_role || outlinePage.page_role || null,
    page_goal: outlinePage.page_goal || outlinePage.core_argument || null,
    selected_strategy: page.regeneration_strategy || null,
    repair_route: repairRoute,
    repair_route_reason: resolvedRepairRouteReason(page) || null,
    upgrade_mode: repairRoute === 'structure' ? 'structure_rebuild' : null,
    page_issue_profile: issueProfile,
    quality_status: page.status || null,
    quality_score: page.score ?? null,
    failed_messages: failedCheckMessages(page),
    generation_gate_events: htmlQualityGateItems.value
      .filter(item => Number(item.page_index) === Number(page.page_index))
      .map(item => ({
        action: item.action,
        failed_checks: item.failed_checks || [],
        title: item.title || ''
      })),
    sequence_events: roadshowSequenceEvents.value
      .filter(event => {
        if (Number(event.page_index) === Number(page.page_index)) return true
        return Array.isArray(event.related_pages) && event.related_pages.map(Number).includes(Number(page.page_index))
      })
      .map(event => ({
        severity: event.severity,
        message: event.message,
        suggestion: event.suggestion || event.action || ''
      })),
    template_contract: outlinePage.page_template_contract || outlinePage.template_contract || outlinePage.visual_contract || null,
    practice_execution_contract: outlinePage.practice_execution_contract || outlinePage.operation_contract || null,
    evidence_hints: page.page_index === currentPageIndex.value ? currentPageEvidenceHints.value : [],
    speaker_script_available: Boolean(outlinePage.speaker_notes || outlinePage.speech_script || outlinePage.notes || outlinePage.script),
    placeholder_analysis: {
      pass: placeholderAnalysis.pass !== false,
      hits: placeholderAnalysis.hits || []
    },
    industry_analysis: {
      pass: industryAnalysis.pass !== false,
      hits: industryAnalysis.hits || [],
      mode: industryAnalysis.mode || null
    },
    template_analysis: {
      pass: templateAnalysis.pass !== false,
      generic_hit_count: templateAnalysis.generic_hit_count ?? 0,
      project_term_hits: templateAnalysis.project_term_hits ?? 0
    },
    delivery_rules: [
      failedChecks.has('placeholder_content') ? '必须删除“待补充、待核实、截图位、建议放置”等终稿禁用占位词' : null,
      failedChecks.has('industry_consistency') ? '必须统一到当前项目赛道术语，不允许混入其他行业设备/预测维护语境' : null,
      failedChecks.has('template_page_risk') ? '必须重写成项目专属页面，不能继续使用通用输入-操作-输出模板' : null
    ].filter(Boolean),
    rewrite_focus: [
      failedChecks.has('placeholder_content') ? '优先把占位表达改成正式可投屏文案，不要保留空洞提示框' : null,
      failedChecks.has('industry_consistency') ? '结合项目名称、赛道和问卷关键词校正术语、案例和指标口径' : null,
      failedChecks.has('template_page_risk') ? '补足项目关键词、核心论点、讲解锚点和视觉主焦点' : null,
      repairRoute === 'structure' ? '不要在原 HTML 上打补丁，要把这页按比赛叙事职责重新策划并整页重做' : null
    ].filter(Boolean)
  }
}

async function runQualityCheck(
  options = {},
  lifecycleToken = pageLifecycle.capture(),
  externalSignal = null
) {
  const taskId = task.value?.id
  if (!taskId || !isPageCurrent(lifecycleToken)) return
  const controller = externalSignal ? null : pageLifecycle.createController(lifecycleToken)
  const signal = externalSignal || controller?.signal
  const { silent = false, announceProgress = true } = options
  qualityChecking.value = true
  try {
    const res = await request.post(`/api/ppt/task/${taskId}/quality-check`, undefined, { signal })
    if (!isPageCurrent(lifecycleToken)) return
    detail.value.quality_report = res.data || res
    await refreshDeliverabilitySnapshot(
      { resetScoringHighlight: true, announceProgress },
      lifecycleToken,
      signal
    )
    if (!isPageCurrent(lifecycleToken)) return
    if (!silent) {
      ElMessage.success('页面质量检查已更新')
    }
  } catch (err) {
    if (isPageCurrent(lifecycleToken) && !isAbortError(err) && !silent) {
      ElMessage.error('重新质检失败')
    }
  } finally {
    if (controller) {
      pageLifecycle.releaseController(controller)
    }
    if (isPageCurrent(lifecycleToken)) {
      qualityChecking.value = false
    }
  }
}

async function runRoadshowHealthCheck() {
  if (!task.value?.id) return
  healthChecking.value = true
  try {
    await request.post(`/api/ppt/task/${task.value.id}/roadshow-health/check`)
    await refreshDeliverabilitySnapshot({ resetScoringHighlight: true, announceProgress: true })
    ElMessage.success('路演一键体检报告已更新')
  } catch {
    ElMessage.error('路演一键体检失败')
  } finally {
    healthChecking.value = false
  }
}

async function generateOptimizationQueue(showMessage = true) {
  if (!task.value?.id) return
  queueGenerating.value = true
  try {
    await request.post(`/api/ppt/task/${task.value.id}/optimization-queue/generate`)
    await refreshDeliverabilitySnapshot({ resetScoringHighlight: true, announceProgress: true })
    if (showMessage) {
      ElMessage.success('优化任务队列已生成')
    }
  } catch {
    if (showMessage) {
      ElMessage.error('优化任务队列生成失败')
    }
  } finally {
    queueGenerating.value = false
  }
}

async function executeOptimizationTask(item) {
  if (!item) return
  const firstPage = item.related_pages?.[0]
  await markOptimizationTasksInProgressByIntent({
    taskId: item.task_id,
    tab: item.task_type === 'evidence'
      ? 'materials'
      : item.task_type === 'scoring'
        ? 'coverage'
        : item.task_type === 'practice'
          ? 'practice'
          : item.task_type === 'roadshow'
            ? 'roadshow'
            : 'quality',
    pageIndex: firstPage || null,
    targetPages: Array.isArray(item.related_pages) ? item.related_pages.map(Number).filter(Boolean) : [],
    relatedPoints: Array.isArray(item.related_points) ? item.related_points.map(point => String(point)) : [],
    title: item.title || item.description || '优化任务'
  }, {
    note: `已开始处理优化任务：${item.title || item.description || item.task_id}`
  })

  if (item.task_type === 'evidence') {
    activeTab.value = 'materials'
    materialDescription.value = item.description || item.title || ''
    ElMessage.info('已跳到素材证据区，并预填了素材说明')
    return
  }

  if (item.task_type === 'scoring') {
    activeTab.value = 'coverage'
    ElMessage.info('已跳到评分点总控，请优先处理该评分点风险')
    return
  }

  if (item.task_type === 'practice') {
    activeTab.value = 'practice'
    ElMessage.info('已跳到实操演示模块，请补齐步骤或证据')
    return
  }

  if (item.task_type === 'roadshow') {
    activeTab.value = 'roadshow'
    ElMessage.info('已跳到路演结构体检页')
    return
  }

  if (item.task_type === 'page_quality' && firstPage) {
    activeTab.value = 'quality'
    currentPageIndex.value = firstPage
    const qualityPage = qualityPages.value.find(page => page.page_index === firstPage)
    if (qualityPage && qualityPage.status !== 'pass') {
      const failed = new Set(qualityPage.failed_checks || [])
      if (failed.has('placeholder_content')) {
        ElMessage.info('该页含终稿占位词，系统会优先生成“去占位”的正式修复预览')
      } else if (failed.has('industry_consistency')) {
        ElMessage.info('该页存在跨行业污染，系统会优先统一术语和项目语境')
      } else if (failed.has('template_page_risk')) {
        ElMessage.info('该页模板化较重，系统会优先重写核心论点和版式结构')
      }
      await repairPage(qualityPage)
    } else {
      previewQualityPage(firstPage)
    }
    return
  }

  if (item.task_type === 'pacing' && firstPage) {
    previewQualityPage(firstPage)
    ElMessage.info('已打开对应页面，请压缩信息密度或改成分层讲解')
    return
  }

  if (item.task_type === 'quality') {
    activeTab.value = 'quality'
    return
  }

  activeTab.value = 'health'
}

async function markOptimizationTaskDone(item) {
  if (!item?.task_id || isOptimizationTaskDone(item)) return
  if (!task.value?.id) return
  updatingOptimizationTaskId.value = item.task_id
  try {
    await request.patch(`/api/ppt/task/${task.value.id}/optimization-queue/tasks/${item.task_id}/status`, {
      status: 'done'
    })
    await refreshDeliverabilitySnapshot({ announceProgress: false })
    ElMessage.success('已标记为处理完成')
  } catch {
    ElMessage.error('优化任务状态保存失败')
  } finally {
    updatingOptimizationTaskId.value = ''
  }
}

async function runRoadshowStructureCheck() {
  if (!task.value?.id) return
  roadshowChecking.value = true
  try {
    await request.post(`/api/ppt/task/${task.value.id}/roadshow-structure/check`)
    await refreshDeliverabilitySnapshot({ resetScoringHighlight: true, announceProgress: true })
    ElMessage.success('路演结构体检已更新')
  } catch {
    ElMessage.error('路演结构体检失败')
  } finally {
    roadshowChecking.value = false
  }
}

async function runScoringDashboardCheck() {
  if (!task.value?.id) return
  scoringDashboardChecking.value = true
  try {
    await request.post(`/api/ppt/task/${task.value.id}/scoring-dashboard/check`)
    await refreshDeliverabilitySnapshot({ resetScoringHighlight: true, announceProgress: true })
    ElMessage.success('评分点总控看板已更新')
  } catch {
    ElMessage.error('评分点总控看板生成失败')
  } finally {
    scoringDashboardChecking.value = false
  }
}

async function batchRepairPages() {
  if (!task.value?.id || batchRepairableCount.value === 0) return
  try {
    await ElMessageBox.confirm(
      `将批量修复 ${batchRepairableCount.value} 个可自动处理的问题页。素材缺口不会被自动修复，仍需上传证据素材；测试阶段可先用临时演示图。是否继续？`,
      '批量修复可自动项',
      {
        confirmButtonText: '开始批量修复',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
  } catch {
    return
  }

  batchRepairing.value = true
  try {
    const res = await request.post(`/api/ppt/task/${task.value.id}/pages/repair-batch`, {
      use_ai: false,
      max_pages: 12
    })
    const result = res.data || res
    if (Array.isArray(result?.html_pages)) {
      detail.value.html_pages = result.html_pages
    }
    if (result?.quality_report) {
      detail.value.quality_report = result.quality_report
    }
    repairSyncSummary.value = await syncReportsAfterBatchRepair(result)
    repairSyncSummaryVisible.value = Boolean(repairSyncSummary.value)
    ElMessage.success(`已批量修复 ${result?.repaired_count || 0} 页，并同步刷新体检与优化队列`)
  } catch (err) {
    ElMessage.error('批量修复失败，请稍后重试')
  } finally {
    batchRepairing.value = false
  }
}

async function repairPage(page) {
  if (!task.value?.id || !page?.page_index) return
  const route = inferCurrentRepairRoute(page)
  if (route === 'evidence') {
    setPageActionFeedback(page.page_index, {
      type: 'warning',
      title: '当前页更适合先补素材',
      summary: resolvedRepairRouteReason(page) || '这页当前主要缺的是截图、结果图或政策来源，先补素材再修更有效。',
      points: [currentPageMaterialTask.value?.summary || '先补当前页最缺的素材证据']
    })
    routePageToEvidence(page, resolvedRepairRouteReason(page) || '这页先补政策来源、截图或数据图，再继续生成')
    return
  }
  if (page.auto_fix_suspended) {
    const nextAction = page.repair_next_action || 'history'
    if (nextAction === 'materials') {
      setPageActionFeedback(page.page_index, {
        type: 'warning',
        title: '建议先补素材',
        summary: page.repair_feedback_hint || '这页继续自动修复收益很低，先补素材证据更稳。'
      })
      routePageToEvidence(page, page.repair_feedback_hint || '该页继续自动修复收益很低，建议先补素材证据')
      return
    }
    await openRepairHistory(page.page_index)
    ElMessage.warning(page.repair_feedback_hint || '该页已多次修复未收敛，建议先查看修复历史或回滚版本')
    return
  }
  if (pageHasEvidenceFailure(page) && page.regeneration_strategy === 'attach_policy_evidence') {
    setPageActionFeedback(page.page_index, {
      type: 'warning',
      title: '政策页先补官方证据',
      summary: '这页更缺官方截图或政策文件来源，先补政策证据再继续修页。'
    })
    routePageToEvidence(page, '政策页缺的是官方证据，请先上传政策官网截图或政策文件')
    return
  }
  if (pageHasEvidenceFailure(page) && page.regeneration_strategy === 'attach_material_evidence') {
    setPageActionFeedback(page.page_index, {
      type: 'warning',
      title: '当前页先补素材证据',
      summary: '这页更缺截图、照片或数据图，先补素材再继续生成会更有效。'
    })
    routePageToEvidence(page, '该页缺少素材证据，请先上传截图、照片或数据图；测试阶段可先用临时演示图')
    return
  }
  repairingPageIndex.value = page.page_index
  try {
    const repairContext = buildPageRepairContext(page)
    let strategy = page.regeneration_strategy || null
    if (repairContext.repair_route === 'structure') {
      strategy = 'structure_rebuild'
    }
    const res = await request.post(
      `/api/ppt/task/${task.value.id}/pages/${page.page_index}/repair`,
      {
        strategy,
        use_ai: true,
        preview_only: true,
        repair_context: repairContext
      },
      {
        timeout: 240000
      }
    )
    const payload = res?.data || res
    const result = payload?.data || payload
    const nextAction = result?.repair_assessment?.next_action
    if (nextAction === 'attach_evidence') {
      setPageActionFeedback(page.page_index, {
        type: 'warning',
        title: '当前页更适合先补素材',
        summary: result?.repair_assessment?.summary
          || resolvedRepairRouteReason(page)
          || '这页继续空修收益不高，建议先补图再继续。',
        points: [currentPageMaterialTask.value?.summary || '优先补截图、结果图或政策来源图']
      })
      routePageToEvidence(
        page,
        result?.repair_assessment?.summary
          || resolvedRepairRouteReason(page)
          || '本次修复判断该页更缺证据，已切到素材证据区'
      )
      return
    }
    if (nextAction === 'retry_or_restore' || nextAction === 'restore_best_repaired') {
      await openRepairHistory(page.page_index)
      setPageActionFeedback(page.page_index, {
        type: 'warning',
        title: '建议先看修复历史',
        summary: result?.history_recommendation?.hint
          || result?.repair_assessment?.summary
          || '继续自动修复收益有限，先回看历史版本更稳。'
      })
      ElMessage.warning(
        result?.history_recommendation?.hint
          || result?.repair_assessment?.summary
          || '本次修复收益不足，已自动打开修复历史供你直接处理'
      )
      return
    }
    repairCandidate.value = result
    repairPreviewVisible.value = true
    setPageActionFeedback(page.page_index, {
      type: 'success',
      title: repairContext.repair_route === 'structure' ? '已生成结构重做预览' : '已生成当前页修复预览',
      summary: result?.repair_assessment?.summary || '可以先对比候选页与当前页，再决定是否采用。',
      points: [result?.repair_assessment?.next_action ? `下一步建议：${repairPreviewNextActionText(result.repair_assessment.next_action)}` : '如候选页更好，可直接采用并同步刷新当前页状态']
    })
    ElMessage.success(
      repairContext.repair_route === 'structure'
        ? '结构重做预览已生成'
        : (result?.repair_mode === 'ai_repaired' ? 'AI 修复预览已生成' : '规则化修复预览已生成')
    )
  } catch (err) {
    const detail = err?.response?.data?.detail || err?.message
    ElMessage.error(detail ? `生成修复预览失败：${detail}` : '生成修复预览失败，请稍后重试')
  } finally {
    repairingPageIndex.value = null
  }
}

async function applyRepairCandidate() {
  if (!task.value?.id || !repairCandidate.value?.html_page?.html_content) return
  applyingRepair.value = true
  try {
    const candidate = repairCandidate.value
    const repairedPageIndex = candidate.page_index
    const res = await request.post(`/api/ppt/task/${task.value.id}/pages/${candidate.page_index}/repair/apply`, {
      html_content: candidate.html_page.html_content,
      strategy: candidate.strategy || null,
      repair_mode: candidate.repair_mode || null
    })
    const result = res.data || res
    if (result?.workspace_state) {
      applyWorkspaceState(result.workspace_state)
    }
    if (result?.accepted === false) {
      const seriesIssues = [
        ...((result?.series_validation?.missing_expected_roles || []).map(role => `缺少块位：${role}`)),
        ...((result?.series_validation?.internal_leaks || []).map(token => `内部词泄露：${token}`))
      ].filter(Boolean)
      setPageActionFeedback(candidate.page_index, {
        type: 'warning',
        title: '候选页未通过页系契约验收',
        summary: result?.rejected_reason || result?.repair_assessment?.summary || '这页仍然更像普通 HTML，不能直接覆盖正式页。',
        points: seriesIssues.length
          ? seriesIssues
          : ['建议继续走“结构重做/契约页重做”，不要直接采用当前候选页']
      })
      repairPreviewVisible.value = false
      repairCandidate.value = null
      ElMessage.warning(result?.rejected_reason || '候选页未通过页系契约验收，已阻止覆盖正式页')
      return
    }
    if (result?.html_page) {
      const nextPages = [...htmlPages.value]
      const pageIdx = nextPages.findIndex(item => item.page_index === result.html_page.page_index)
      if (pageIdx >= 0) {
        nextPages.splice(pageIdx, 1, result.html_page)
      } else {
        nextPages.push(result.html_page)
        nextPages.sort((a, b) => a.page_index - b.page_index)
      }
      detail.value.html_pages = nextPages
      currentPageIndex.value = result.html_page.page_index
    }
    if (result?.quality_report) {
      detail.value.quality_report = result.quality_report
    }
    repairSyncSummary.value = await syncReportsAfterRepair(repairedPageIndex)
    activeTab.value = 'html'
    repairPreviewVisible.value = false
    repairCandidate.value = null
    repairSyncSummaryVisible.value = Boolean(repairSyncSummary.value)
    const previousFeedbackPoints = pageActionFeedback.value?.[repairedPageIndex]?.points || []
    setPageActionFeedback(repairedPageIndex, {
      type: repairSyncSummary.value?.remaining_issues?.length ? 'warning' : 'success',
      title: '已采用当前页修复结果',
      summary: repairSyncSummary.value?.remaining_issues?.length
        ? '当前页已完成一轮修复，但仍有残留问题需要继续处理。'
        : '当前页已通过本轮页面级质检。',
      points: [
        previousFeedbackPoints[0] || '',
        repairSyncSummary.value?.remaining_issues?.[0] || '',
        repairSyncSummary.value?.remaining_issues?.[1] || ''
      ]
    })
    ElMessage.success('已采用修复候选，并同步刷新体检与优化队列')
  } catch (err) {
    ElMessage.error('采用修复候选失败，请稍后重试')
  } finally {
    applyingRepair.value = false
  }
}

async function handleRepairPreviewNextAction() {
  const action = repairPreviewNextAction.value
  const pageIndex = repairCandidate.value?.page_index
  if (!action || !pageIndex) return

  if (action === 'attach_evidence') {
    repairPreviewVisible.value = false
    const qualityPage = qualityPages.value.find(page => Number(page.page_index) === Number(pageIndex))
    if (qualityPage) {
      await repairPage({
        ...qualityPage,
        auto_fix_suspended: false,
        repair_route: 'evidence'
      })
    }
    return
  }

  if (action === 'structure_rebuild') {
    repairPreviewVisible.value = false
    const qualityPage = qualityPages.value.find(page => Number(page.page_index) === Number(pageIndex))
    if (qualityPage) {
      await repairPage({
        ...qualityPage,
        auto_fix_suspended: false,
        repair_route: 'structure'
      })
    }
    return
  }

  if (action === 'retry_or_restore' || action === 'restore_best_repaired') {
    repairPreviewVisible.value = false
    await openRepairHistory(pageIndex)
  }
}

async function syncReportsAfterRepair(pageIndex) {
  if (!task.value?.id || !pageIndex) return null
  const reviewTaskCount = await markPageOptimizationTasksForReview(pageIndex)

  const [roadshowResult, scoringResult, healthResult] = await Promise.allSettled([
    request.post(`/api/ppt/task/${task.value.id}/roadshow-structure/check`),
    request.post(`/api/ppt/task/${task.value.id}/scoring-dashboard/check`),
    request.post(`/api/ppt/task/${task.value.id}/roadshow-health/check`)
  ])

  let queueStatus = 'success'
  try {
    await request.post(`/api/ppt/task/${task.value.id}/optimization-queue/generate`)
  } catch {
    queueStatus = 'failed'
    ElMessage.warning('修复已采用，但优化任务队列刷新失败，可稍后手动重新生成')
  }
  await refreshDeliverabilitySnapshot({
    resetScoringHighlight: true,
    announceProgress: true,
    intentLabel: '页面修复采用',
    feedbackPageIndex: pageIndex
  })

  const latestQuality = qualityPages.value.find(page => Number(page.page_index) === Number(pageIndex)) || {}
  return {
    page_index: pageIndex,
    title: getOutlineTitle(pageIndex),
    quality_status: latestQuality.status || 'unknown',
    quality_score: latestQuality.score ?? null,
    remaining_issues: failedCheckMessages(latestQuality),
    review_task_count: reviewTaskCount,
    sync_items: [
      { key: 'roadshow_structure', label: '路演结构体检', status: roadshowResult.status === 'fulfilled' ? 'success' : 'failed' },
      { key: 'scoring_dashboard', label: '评分点总控', status: scoringResult.status === 'fulfilled' ? 'success' : 'failed' },
      { key: 'roadshow_health', label: '一键健康报告', status: healthResult.status === 'fulfilled' ? 'success' : 'failed' },
      { key: 'optimization_queue', label: '优化任务队列', status: queueStatus }
    ]
  }
}

async function syncReportsAfterBatchRepair(
  result,
  lifecycleToken = pageLifecycle.capture(),
  signal = null
) {
  const taskId = task.value?.id
  if (!taskId || !isPageCurrent(lifecycleToken)) return null
  const repairedPages = result?.repaired_pages || []
  const pageIndexes = repairedPages.map(page => Number(page.page_index)).filter(Boolean)
  const reviewTaskCount = await markPageOptimizationTasksForReview(pageIndexes, lifecycleToken, signal)
  if (!isPageCurrent(lifecycleToken)) return null

  const [roadshowResult, scoringResult, healthResult] = await Promise.allSettled([
    request.post(`/api/ppt/task/${taskId}/roadshow-structure/check`, undefined, { signal }),
    request.post(`/api/ppt/task/${taskId}/scoring-dashboard/check`, undefined, { signal }),
    request.post(`/api/ppt/task/${taskId}/roadshow-health/check`, undefined, { signal })
  ])
  if (!isPageCurrent(lifecycleToken)) return null

  let queueStatus = 'success'
  try {
    await request.post(`/api/ppt/task/${taskId}/optimization-queue/generate`, undefined, { signal })
    if (!isPageCurrent(lifecycleToken)) return null
  } catch (err) {
    if (!isPageCurrent(lifecycleToken) || isAbortError(err)) return null
    queueStatus = 'failed'
    ElMessage.warning('批量修复已完成，但优化任务队列刷新失败，可稍后手动重新生成')
  }
  await refreshDeliverabilitySnapshot(
    {
      resetScoringHighlight: true,
      announceProgress: true,
      intentLabel: '批量修复',
      feedbackPageIndex: pageIndexes[0] || currentPageIndex.value
    },
    lifecycleToken,
    signal
  )
  if (!isPageCurrent(lifecycleToken)) return null

  const remainingIssuePages = qualityPages.value.filter(page => page.status !== 'pass')
  return {
    mode: 'batch',
    candidate_count: result?.candidate_count || 0,
    repaired_count: result?.repaired_count || 0,
    repaired_pages: repairedPages,
    skipped_pages: result?.skipped_pages || [],
    average_score: qualityReport.value?.average_score ?? null,
    remaining_issue_pages: remainingIssuePages.length,
    remaining_issues: remainingIssuePages
      .slice(0, 4)
      .map(page => `第${page.page_index}页「${page.title || getOutlineTitle(page.page_index)}」：${failedCheckMessages(page)[0] || strategyText(page.regeneration_strategy) || '仍需复查'}`),
    review_task_count: reviewTaskCount,
    sync_items: [
      { key: 'roadshow_structure', label: '路演结构体检', status: roadshowResult.status === 'fulfilled' ? 'success' : 'failed' },
      { key: 'scoring_dashboard', label: '评分点总控', status: scoringResult.status === 'fulfilled' ? 'success' : 'failed' },
      { key: 'roadshow_health', label: '一键健康报告', status: healthResult.status === 'fulfilled' ? 'success' : 'failed' },
      { key: 'optimization_queue', label: '优化任务队列', status: queueStatus }
    ]
  }
}

async function markPageOptimizationTasksForReview(
  pageIndex,
  lifecycleToken = pageLifecycle.capture(),
  signal = null
) {
  if (!isPageCurrent(lifecycleToken)) return 0
  const targetPages = Array.isArray(pageIndex) ? pageIndex.map(Number) : [Number(pageIndex)]
  const tasks = optimizationQueue.value?.tasks || []
  const relatedTasks = tasks.filter(item => {
    if (item.status === 'done' || item.status === 'skipped') return false
    if (!Array.isArray(item.related_pages) || !item.related_pages.map(Number).some(page => targetPages.includes(page))) return false
    return ['page_quality', 'pacing', 'roadshow', 'quality'].includes(item.task_type)
  })
  if (!relatedTasks.length) return 0

  const results = await Promise.allSettled(relatedTasks.map(item => {
    return request.patch(`/api/ppt/task/${task.value.id}/optimization-queue/tasks/${item.task_id}/status`, {
      status: 'in_progress',
      note: targetPages.length > 1
        ? `第 ${targetPages.join('、')} 页已完成批量修复，等待重新体检确认。`
        : `第 ${targetPages[0]} 页已采用单页修复候选，等待重新体检确认。`
    }, { signal })
  }))
  if (!isPageCurrent(lifecycleToken)) return 0
  return results.filter(item => item.status === 'fulfilled').length
}

function repairModeText(mode) {
  const map = {
    ai_repaired: 'AI 单页重写',
    contract_rebuilt: '契约骨架重建',
    rule_repaired: '规则化兜底修复',
    confirmed_repair: '已确认修复'
  }
  return map[mode] || '定向修复'
}

function previewQualityPage(pageIndex) {
  currentPageIndex.value = pageIndex
  activeTab.value = 'html'
}

function updatePreviewScale() {
  const viewport = previewViewportRef.value
  if (!viewport) return
  const { width, height } = viewport.getBoundingClientRect()
  if (!width || !height) return
  const horizontalScale = Math.max((width - 12) / 1920, 0.1)
  const verticalScale = Math.max((height - 12) / 1080, 0.1)
  previewScale.value = Math.min(horizontalScale, verticalScale, 1)
}

function routePageToEvidence(page, message) {
  if (!page?.page_index) return
  if (!pageHasEvidenceFailure(page)) {
    ElMessage.info('当前页缺图问题已解除，接下来请继续处理占位词、模板化或评分点问题。')
    return
  }
  activeTab.value = 'materials'
  if (page.regeneration_strategy === 'attach_policy_evidence') {
    materialAssetType.value = 'policy_screenshot'
    materialDescription.value = `政策名称：\n官方来源/链接：\n对应页面：第${page.page_index}页「${page.title || '政策与产业背景'}」\n证明关系：`
  } else {
    materialDescription.value = `对应页面：第${page.page_index}页「${page.title || '实操/成果页'}」\n证明内容：`
  }
  if (message) {
    ElMessage.info(message)
  }
}

async function openRepairHistory(pageIndex) {
  if (!task.value?.id || !pageIndex) return
  repairHistoryPageIndex.value = pageIndex
  repairHistoryVisible.value = true
  repairHistoryLoading.value = true
  try {
    const res = await request.get(`/api/ppt/task/${task.value.id}/pages/${pageIndex}/repair-history`)
    repairHistory.value = res.data || res
  } catch {
    repairHistory.value = { items: [] }
    ElMessage.error('加载修复历史失败')
  } finally {
    repairHistoryLoading.value = false
  }
}

async function triggerStructureRebuildForPage(pageIndex) {
  const qualityPage = qualityPages.value.find(page => Number(page.page_index) === Number(pageIndex))
  if (!qualityPage) {
    ElMessage.warning('未找到该页最新质检信息，无法升级重做')
    return
  }
  repairHistoryVisible.value = false
  await repairPage({
    ...qualityPage,
    auto_fix_suspended: false,
    repair_route: 'structure'
  })
}

async function handleRepairHistoryRecommendation() {
  const recommendation = repairHistoryRecommendation.value
  if (!recommendation) return

  if (recommendation.mode === 'restore_best_repaired' && recommendation.snapshot_id) {
    const targetItem = repairHistoryItems.value.find(item => Number(item.id) === Number(recommendation.snapshot_id))
    if (!targetItem) {
      ElMessage.warning('推荐版本不存在，请刷新后重试')
      return
    }
    await rollbackRepairVersion(targetItem, recommendation.target || 'repaired')
    return
  }

  if (recommendation.mode === 'attach_evidence') {
    repairHistoryVisible.value = false
    const qualityPage = qualityPages.value.find(page => Number(page.page_index) === Number(repairHistoryPageIndex.value))
    if (qualityPage) {
      await repairPage({
        ...qualityPage,
        auto_fix_suspended: false,
        repair_route: 'evidence'
      })
    }
    return
  }

  if (recommendation.mode === 'structure_rebuild') {
    await triggerStructureRebuildForPage(repairHistoryPageIndex.value)
    return
  }

  if (recommendation.mode === 'regenerate_html') {
    repairHistoryVisible.value = false
    const qualityPage = qualityPages.value.find(page => Number(page.page_index) === Number(repairHistoryPageIndex.value))
    if (qualityPage) {
      await repairPage({
        ...qualityPage,
        auto_fix_suspended: false,
        repair_route: 'html'
      })
    }
  }
}

async function rollbackRepairVersion(item, target) {
  if (!task.value?.id || !item?.id) return
  const targetText = target === 'repaired' ? '修复版' : '原版本'
  try {
    await ElMessageBox.confirm(
      `确认将第 ${repairHistoryPageIndex.value} 页恢复到该快照的${targetText}？当前页面会被覆盖，但本次恢复也会记录快照。`,
      '恢复页面版本',
      {
        confirmButtonText: `恢复${targetText}`,
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
  } catch {
    return
  }

  rollingBackKey.value = `${item.id}:${target}`
  try {
    const res = await request.post(`/api/ppt/task/${task.value.id}/pages/${repairHistoryPageIndex.value}/repair-rollback`, {
      snapshot_id: item.id,
      target
    })
    const result = res.data || res
    if (result?.html_page) {
      const nextPages = [...htmlPages.value]
      const pageIdx = nextPages.findIndex(page => page.page_index === result.html_page.page_index)
      if (pageIdx >= 0) {
        nextPages.splice(pageIdx, 1, result.html_page)
      } else {
        nextPages.push(result.html_page)
        nextPages.sort((a, b) => a.page_index - b.page_index)
      }
      detail.value.html_pages = nextPages
      currentPageIndex.value = result.html_page.page_index
    }
    if (result?.quality_report) {
      detail.value.quality_report = result.quality_report
    }
    activeTab.value = 'html'
    repairHistoryVisible.value = false
    ElMessage.success(`已恢复到${targetText}并刷新质检`)
  } catch {
    ElMessage.error('恢复页面版本失败')
  } finally {
    rollingBackKey.value = ''
  }
}

async function downloadPpt() {
  const lifecycleToken = pageLifecycle.capture()
  if (!task.value?.id || !isPageCurrent(lifecycleToken)) return
  return downloadCoordinator.runOnce('download', async () => {
    if (!isPageCurrent(lifecycleToken)) return
    downloadingPpt.value = true
    try {
      return await performDownloadPpt(lifecycleToken)
    } finally {
      if (isPageCurrent(lifecycleToken)) {
        downloadingPpt.value = false
      }
    }
  })
}

async function performDownloadPpt(lifecycleToken = pageLifecycle.capture()) {
  const taskId = task.value?.id
  if (!taskId || !isPageCurrent(lifecycleToken)) return
  const controller = pageLifecycle.createController(lifecycleToken)
  const isCurrent = () => isPageCurrent(lifecycleToken)

  if (deliverabilityVerdict.value.status === 'blocked') {
    const pending = downloadChecklist.value.filter(item => !item.done)
    if (pendingDownloadAfterFix.value) {
      try {
        const firstPending = pending.find(item => item.actionable) || pending[0] || null
        if (firstPending && isCurrent()) {
          downloadReadinessActionFeedback.value = {
            type: 'warning',
            title: '继续处理并返回下载',
            summary: `当前仍需先处理「${firstPending.title}」，处理完后系统会继续带你回到下载流程。`,
            points: [
              firstPending.targetPages?.length ? `关联页面：${targetPagesText(firstPending.targetPages.slice(0, 4))}` : '',
              firstPending.relatedPoints?.length ? `优先补：${firstPending.relatedPoints.slice(0, 3).join('、')}` : ''
            ].filter(Boolean),
            allowDownload: false,
            nextPendingItem: firstPending
          }
          focusDownloadReadinessCard(lifecycleToken)
          if (firstPending.actionable) {
            await handleDownloadChecklistItem(firstPending, lifecycleToken, controller.signal)
            if (!isCurrent()) return
          } else {
            guideToFirstPendingDownloadItem(deliverabilityVerdict.value.summary || firstPending.detail || '请先处理当前下载条件。')
          }
        }
      } finally {
        pageLifecycle.releaseController(controller)
      }
      return
    }
    try {
      await ElMessageBox.confirm(
        renderDownloadChecklistDialogContent(
          pending.length
            ? pending
            : [{
                key: 'fallback',
                title: '当前还有未满足的下载条件',
                detail: deliverabilityVerdict.value.summary || '请先回到质量报告继续处理。',
                progressText: '未满足',
                progressPercent: 0,
                done: false
              }]
        ),
        '下载条件未达标',
        {
          confirmButtonText: pending.some(item => item.actionable) ? '先处理并继续下载' : '查看下载条件',
          cancelButtonText: '暂不下载',
          type: 'warning',
          customClass: 'download-gate-message-box'
        }
      )
      if (!isCurrent()) return
      const firstPending = pending.find(item => item.actionable)
      if (firstPending) {
        pendingDownloadAfterFix.value = true
        await handleDownloadChecklistItem(firstPending, lifecycleToken, controller.signal)
        if (!isCurrent()) return
        if (deliverabilityVerdict.value.status !== 'blocked') {
          const remaining = downloadChecklist.value.filter(item => !item.done)
          const nextPendingItem = remaining.find(item => item.actionable) || remaining[0] || null
          downloadReadinessActionFeedback.value = {
            type: deliverabilityVerdict.value.status === 'ready' ? 'success' : 'warning',
            title: deliverabilityVerdict.value.status === 'ready' ? '当前已可直接下载' : '当前版已可继续下载',
            summary: deliverabilityVerdict.value.status === 'ready'
              ? '刚刚处理的下载阻塞项已解除，现在可以直接下载可交付版本。'
              : '刚刚处理的下载阻塞项已解除，现在可以先下载当前版本，也可以继续补强剩余建议项。',
            points: deliverabilityVerdict.value.status === 'ready'
              ? ['当前关键下载门禁已放开。']
              : remaining.slice(0, 2).map(item => `建议继续：${item.title}`),
            allowDownload: true,
            nextPendingItem: deliverabilityVerdict.value.status === 'ready' ? null : nextPendingItem
          }
          focusDownloadReadinessCard(lifecycleToken)
        }
      } else if (pending.length) {
        pendingDownloadAfterFix.value = true
        guideToFirstPendingDownloadItem(deliverabilityVerdict.value.summary || pending[0].detail || '请先从下载条件卡开始处理未满足项。')
      }
    } catch (err) {
      if (isCurrent() && !isAbortError(err)) {
        pendingDownloadAfterFix.value = false
      }
    } finally {
      pageLifecycle.releaseController(controller)
    }
    return
  }
  try {
    if (!isCurrent()) return
    downloadReadinessActionFeedback.value = null
    await refreshDeliverabilitySnapshot(
      { announceProgress: false },
      lifecycleToken,
      controller.signal
    )
    if (!isCurrent()) return
    if (deliverabilityVerdict.value.status === 'blocked') {
      guideToFirstPendingDownloadItem(deliverabilityVerdict.value.summary || '下载前检测到当前门禁有更新，请先处理最新未满足项。')
      ElMessage.warning('下载前已同步最新门禁，请先处理当前未满足项')
      return
    }
    const response = await fetch(`/api/ppt/task/${taskId}/download`, {
      headers: {
        Authorization: `Bearer ${authStore.token}`
      },
      signal: controller.signal
    })
    if (!isCurrent()) return
    if (!response.ok) {
      let errorMessage = '下载失败'
      try {
        const payload = await response.json()
        if (!isCurrent()) return
        errorMessage = payload?.detail?.message || payload?.detail || errorMessage
        if (payload?.detail?.deliverability) {
          detail.value = {
            ...detail.value,
            deliverability: payload.detail.deliverability
          }
          downloadReadinessActionFeedback.value = {
            type: 'warning',
            title: '下载条件发生变化',
            summary: payload?.detail?.deliverability?.summary || '当前版本暂时不能直接下载，请先处理最新的阻塞项。',
            points: Array.isArray(payload?.detail?.deliverability?.blockers)
              ? payload.detail.deliverability.blockers.slice(0, 2)
              : [],
            allowDownload: false
          }
          guideToFirstPendingDownloadItem(payload?.detail?.deliverability?.summary || '当前版本暂时不能直接下载，请先处理最新的阻塞项。')
        }
      } catch {
        errorMessage = '下载失败'
      }
      throw new Error(errorMessage)
    }
    const blob = await response.blob()
    if (!isCurrent()) return
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `ppt_${taskId}.pptx`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
    const remaining = downloadChecklist.value.filter(item => !item.done)
    const nextPendingItem = remaining.find(item => item.actionable) || remaining[0] || null
    downloadReadinessActionFeedback.value = {
      type: deliverabilityVerdict.value.status === 'ready' ? 'success' : 'warning',
      title: deliverabilityVerdict.value.status === 'ready' ? '已下载可交付版本' : '已下载当前版本',
      summary: deliverabilityVerdict.value.status === 'ready'
        ? '当前关键下载条件已经满足，本次导出可直接用于后续终审或正式交付。'
        : `当前版本已经下载完成，但仍建议继续处理剩余 ${remaining.length} 条下载建议，让版本更稳。`,
      points: deliverabilityVerdict.value.status === 'ready'
        ? ['当前已满足下载门禁，可继续做讲稿联调或终审复核。']
        : remaining.slice(0, 2).map(item => `建议继续：${item.title}`),
      allowDownload: true,
      nextPendingItem: deliverabilityVerdict.value.status === 'ready' ? null : (downloadFlowFollowupAction.value || nextPendingItem)
    }
    if (downloadFlowFollowupAction.value?.key) {
      focusDownloadReadinessCard(lifecycleToken)
      focusDownloadChecklistItem(downloadFlowFollowupAction.value.key, lifecycleToken)
    } else {
      focusDownloadReadinessCard(lifecycleToken)
    }
    pendingDownloadAfterFix.value = deliverabilityVerdict.value.status !== 'ready' && Boolean(downloadFlowFollowupAction.value)
    ElMessage.success(deliverabilityVerdict.value.status === 'ready' ? 'PPT 下载成功' : '当前版本已下载，可继续补强后再复导')
  } catch (err) {
    if (isCurrent() && !isAbortError(err)) {
      pendingDownloadAfterFix.value = false
      ElMessage.error(err?.message || '下载失败')
    }
  } finally {
    pageLifecycle.releaseController(controller)
  }
}

function mergeDirectlyRepairedPage(result) {
  if (result?.workspace_state) {
    applyWorkspaceState(result.workspace_state)
  }
  if (!result?.html_page) return
  const nextPages = [...htmlPages.value]
  const pageIdx = nextPages.findIndex(page => Number(page.page_index) === Number(result.html_page.page_index))
  if (pageIdx >= 0) {
    nextPages.splice(pageIdx, 1, result.html_page)
  } else {
    nextPages.push(result.html_page)
    nextPages.sort((a, b) => Number(a.page_index) - Number(b.page_index))
  }
  detail.value.html_pages = nextPages
}

async function refreshScoringCoverageSnapshot(
  lifecycleToken = pageLifecycle.capture(),
  externalSignal = null
) {
  const taskId = task.value?.id
  if (!taskId || !isPageCurrent(lifecycleToken)) return
  const controller = externalSignal ? null : pageLifecycle.createController(lifecycleToken)
  const signal = externalSignal || controller?.signal
  await Promise.allSettled([
    request.get(`/api/ppt/task/${taskId}/scoring-coverage`, { signal }),
    request.post(`/api/ppt/task/${taskId}/scoring-dashboard/check`, undefined, { signal }),
    request.post(`/api/ppt/task/${taskId}/optimization-queue/generate`, undefined, { signal })
  ])
  if (controller) {
    pageLifecycle.releaseController(controller)
  }
}

async function refreshWorkbenchAfterMutation(
  options = {},
  lifecycleToken = pageLifecycle.capture(),
  externalSignal = null
) {
  if (!isPageCurrent(lifecycleToken)) return
  const {
    refreshQuality = true,
    refreshScoring = false,
    announceProgress = true,
    intentLabel = '',
    feedbackPageIndex = null
  } = options

  if (refreshQuality) {
    await runQualityCheck(
      { silent: true, announceProgress: false },
      lifecycleToken,
      externalSignal
    )
    if (!isPageCurrent(lifecycleToken)) return
  }
  if (refreshScoring) {
    await refreshScoringCoverageSnapshot(lifecycleToken, externalSignal)
    if (!isPageCurrent(lifecycleToken)) return
  }
  await refreshDeliverabilitySnapshot(
    {
      resetScoringHighlight: true,
      announceProgress,
      intentLabel,
      feedbackPageIndex
    },
    lifecycleToken,
    externalSignal
  )
}

async function runInlineScoringCoverageFix(
  item,
  lifecycleToken = pageLifecycle.capture(),
  signal = null
) {
  const taskId = task.value?.id
  if (!taskId || !isPageCurrent(lifecycleToken)) return
  const targetPages = (item?.targetPages || []).map(Number).filter(Boolean).slice(0, 4)
  if (!targetPages.length) {
    if (isPageCurrent(lifecycleToken)) {
      ElMessage.warning('当前没有可自动补强的评分支撑页，请稍后重试或再补充页面内容')
    }
    return
  }
  downloadChecklistActionKey.value = item.key
  downloadReadinessActionFeedback.value = null
  try {
    let repairedCount = 0
    for (const pageIndex of targetPages) {
      const qualityPage = qualityPages.value.find(page => Number(page.page_index) === Number(pageIndex))
      if (!qualityPage) continue
      const repairContext = buildPageRepairContext(qualityPage)
      const failedChecks = new Set(qualityPage.failed_checks || [])
      const strategy = failedChecks.has('template_page_risk') ? 'structure_rebuild' : 'align_scoring_points'
      const res = await request.post(
        `/api/ppt/task/${taskId}/pages/${pageIndex}/repair`,
        {
          strategy,
          use_ai: true,
          preview_only: false,
          repair_context: {
            ...repairContext,
            source: 'download_checklist_inline_scoring_fix',
            goal: 'boost_required_scoring_coverage',
            target_points: item.relatedPoints || []
          }
        },
        {
          timeout: 240000,
          signal
        }
      )
      if (!isPageCurrent(lifecycleToken)) return
      const payload = res?.data || res
      const result = payload?.data || payload
      if (result?.workspace_state) {
        applyWorkspaceState(result.workspace_state)
      }
      if (result?.accepted === false) {
        continue
      }
      if (result?.html_page) {
        mergeDirectlyRepairedPage(result)
        repairedCount += 1
      }
      if (result?.quality_report) {
        detail.value.quality_report = result.quality_report
      }
    }
    await refreshWorkbenchAfterMutation(
      {
        refreshQuality: true,
        refreshScoring: true,
        announceProgress: true,
        intentLabel: '评分覆盖一键补强',
        feedbackPageIndex: targetPages[0] || currentPageIndex.value
      },
      lifecycleToken,
      signal
    )
    if (!isPageCurrent(lifecycleToken)) return
    ElMessage.success(`已自动补强 ${repairedCount} 个比赛评分证据页面`)
    announceNextDownloadChecklistItem(item.key)
  } catch (err) {
    if (isPageCurrent(lifecycleToken) && !isAbortError(err)) {
      const detailMessage = err?.response?.data?.detail || err?.message
      ElMessage.error(detailMessage ? `一键补比赛评分证据失败：${detailMessage}` : '一键补比赛评分证据失败，请稍后重试')
    }
  } finally {
    if (isPageCurrent(lifecycleToken)) {
      downloadChecklistActionKey.value = ''
    }
  }
}

async function runInlineP0QuickFix(
  item,
  lifecycleToken = pageLifecycle.capture(),
  signal = null
) {
  const taskId = task.value?.id
  if (!taskId || !isPageCurrent(lifecycleToken)) return
  downloadChecklistActionKey.value = item.key
  downloadReadinessActionFeedback.value = null
  try {
    const res = await request.post(`/api/ppt/task/${taskId}/pages/repair-batch`, {
      use_ai: false,
      max_pages: Math.max(4, Math.min(8, Number(optimizationQueue.value?.p0_count || 4)))
    }, { signal })
    if (!isPageCurrent(lifecycleToken)) return
    const result = res.data || res
    if (result?.workspace_state) {
      applyWorkspaceState(result.workspace_state)
    }
    if (Array.isArray(result?.html_pages)) {
      detail.value.html_pages = result.html_pages
    }
    if (result?.quality_report) {
      detail.value.quality_report = result.quality_report
    }
    repairSyncSummary.value = await syncReportsAfterBatchRepair(result, lifecycleToken, signal)
    if (!isPageCurrent(lifecycleToken)) return
    repairSyncSummaryVisible.value = Boolean(repairSyncSummary.value)
    ElMessage.success(`已在当前页自动处理一批 P0 问题页，当前优先页：${targetPagesText((item?.targetPages || []).slice(0, 3)) || '已刷新最新结果'}`)
    announceNextDownloadChecklistItem(item.key)
  } catch (err) {
    if (isPageCurrent(lifecycleToken) && !isAbortError(err)) {
      const detailMessage = err?.response?.data?.detail || err?.message
      ElMessage.error(detailMessage ? `一键处理 P0 失败：${detailMessage}` : '一键处理 P0 失败，请稍后重试')
    }
  } finally {
    if (isPageCurrent(lifecycleToken)) {
      downloadChecklistActionKey.value = ''
    }
  }
}

async function runInlinePlaceholderFix(
  item,
  lifecycleToken = pageLifecycle.capture(),
  signal = null
) {
  const taskId = task.value?.id
  if (!taskId || !isPageCurrent(lifecycleToken)) return
  const targetPages = (item?.targetPages || []).map(Number).filter(Boolean).slice(0, 4)
  if (!targetPages.length) {
    if (isPageCurrent(lifecycleToken)) {
      ElMessage.warning('当前没有需要清理占位词的页面')
    }
    return
  }
  downloadChecklistActionKey.value = item.key
  downloadReadinessActionFeedback.value = null
  try {
    let repairedCount = 0
    for (const pageIndex of targetPages) {
      const qualityPage = qualityPages.value.find(page => Number(page.page_index) === Number(pageIndex))
      if (!qualityPage) continue
      const res = await request.post(
        `/api/ppt/task/${taskId}/pages/${pageIndex}/repair`,
        {
          strategy: 'remove_placeholder_content',
          use_ai: true,
          preview_only: false,
          repair_context: {
            ...buildPageRepairContext(qualityPage),
            source: 'download_checklist_inline_placeholder_fix',
            goal: 'clear_placeholder_content'
          }
        },
        {
          timeout: 240000,
          signal
        }
      )
      if (!isPageCurrent(lifecycleToken)) return
      const payload = res?.data || res
      const result = payload?.data || payload
      if (result?.workspace_state) {
        applyWorkspaceState(result.workspace_state)
      }
      if (result?.accepted === false) {
        continue
      }
      if (result?.html_page) {
        mergeDirectlyRepairedPage(result)
        repairedCount += 1
      }
      if (result?.quality_report) {
        detail.value.quality_report = result.quality_report
      }
    }
    await refreshWorkbenchAfterMutation(
      {
        refreshQuality: true,
        announceProgress: true,
        intentLabel: '占位词一键清理',
        feedbackPageIndex: targetPages[0] || currentPageIndex.value
      },
      lifecycleToken,
      signal
    )
    if (!isPageCurrent(lifecycleToken)) return
    ElMessage.success(`已在当前页自动清理 ${repairedCount} 个页面的终稿占位词`)
    announceNextDownloadChecklistItem(item.key)
  } catch (err) {
    if (isPageCurrent(lifecycleToken) && !isAbortError(err)) {
      const detailMessage = err?.response?.data?.detail || err?.message
      ElMessage.error(detailMessage ? `一键清占位词失败：${detailMessage}` : '一键清占位词失败，请稍后重试')
    }
  } finally {
    if (isPageCurrent(lifecycleToken)) {
      downloadChecklistActionKey.value = ''
    }
  }
}

async function runInlinePracticeTemplateFix(
  item,
  lifecycleToken = pageLifecycle.capture(),
  signal = null
) {
  const taskId = task.value?.id
  if (!taskId || !isPageCurrent(lifecycleToken)) return
  const targetPages = (item?.targetPages || []).map(Number).filter(Boolean).slice(0, 3)
  if (!targetPages.length) {
    if (isPageCurrent(lifecycleToken)) {
      ElMessage.warning('当前没有需要重做的模板化页面')
    }
    return
  }
  downloadChecklistActionKey.value = item.key
  downloadReadinessActionFeedback.value = null
  try {
    let rebuiltCount = 0
    for (const pageIndex of targetPages) {
      const qualityPage = qualityPages.value.find(page => Number(page.page_index) === Number(pageIndex))
      if (!qualityPage) continue
      const res = await request.post(
        `/api/ppt/task/${taskId}/pages/${pageIndex}/repair`,
        {
          strategy: 'structure_rebuild',
          use_ai: true,
          preview_only: false,
          repair_context: {
            ...buildPageRepairContext(qualityPage),
            source: 'download_checklist_inline_template_fix',
            goal: 'rebuild_template_like_practice_page'
          }
        },
        {
          timeout: 240000,
          signal
        }
      )
      if (!isPageCurrent(lifecycleToken)) return
      const payload = res?.data || res
      const result = payload?.data || payload
      if (result?.workspace_state) {
        applyWorkspaceState(result.workspace_state)
      }
      if (result?.accepted === false) {
        continue
      }
      if (result?.html_page) {
        mergeDirectlyRepairedPage(result)
        rebuiltCount += 1
      }
      if (result?.quality_report) {
        detail.value.quality_report = result.quality_report
      }
    }
    await refreshWorkbenchAfterMutation(
      {
        refreshQuality: true,
        announceProgress: true,
        intentLabel: '模板页一键重做',
        feedbackPageIndex: targetPages[0] || currentPageIndex.value
      },
      lifecycleToken,
      signal
    )
    if (!isPageCurrent(lifecycleToken)) return
    ElMessage.success(`已在当前页自动重做 ${rebuiltCount} 个模板化页面`)
    announceNextDownloadChecklistItem(item.key)
  } catch (err) {
    if (isPageCurrent(lifecycleToken) && !isAbortError(err)) {
      const detailMessage = err?.response?.data?.detail || err?.message
      ElMessage.error(detailMessage ? `一键重做模板页失败：${detailMessage}` : '一键重做模板页失败，请稍后重试')
    }
  } finally {
    if (isPageCurrent(lifecycleToken)) {
      downloadChecklistActionKey.value = ''
    }
  }
}

async function runInlinePageContractFix(
  item,
  lifecycleToken = pageLifecycle.capture(),
  signal = null
) {
  const taskId = task.value?.id
  if (!taskId || !isPageCurrent(lifecycleToken)) return
  const targetPages = (item?.targetPages || []).map(Number).filter(Boolean).slice(0, 3)
  if (!targetPages.length) {
    if (isPageCurrent(lifecycleToken)) {
      ElMessage.warning('当前没有需要按页面契约重做的页面')
    }
    return
  }
  downloadChecklistActionKey.value = item.key
  downloadReadinessActionFeedback.value = null
  try {
    let rebuiltCount = 0
    const contractFocus = Array.from(
      new Set(
        targetPages.flatMap(pageIndex => {
          const qualityPage = qualityPages.value.find(page => Number(page.page_index) === Number(pageIndex))
          return contractVisualIssueLabels(qualityPage)
        })
      )
    )
    for (const pageIndex of targetPages) {
      const qualityPage = qualityPages.value.find(page => Number(page.page_index) === Number(pageIndex))
      if (!qualityPage) continue
      const res = await request.post(
        `/api/ppt/task/${taskId}/pages/${pageIndex}/repair`,
        {
          strategy: 'structure_rebuild',
          use_ai: true,
          preview_only: false,
          repair_context: {
            ...buildPageRepairContext(qualityPage),
            source: 'download_checklist_inline_page_contract_fix',
            goal: 'rebuild_page_by_contract',
            upgrade_mode: 'structure_rebuild'
          }
        },
        {
          timeout: 240000,
          signal
        }
      )
      if (!isPageCurrent(lifecycleToken)) return
      const payload = res?.data || res
      const result = payload?.data || payload
      if (result?.workspace_state) {
        applyWorkspaceState(result.workspace_state)
      }
      if (result?.accepted === false) {
        continue
      }
      if (result?.html_page) {
        mergeDirectlyRepairedPage(result)
        rebuiltCount += 1
      }
      if (result?.quality_report) {
        detail.value.quality_report = result.quality_report
      }
    }
    await refreshWorkbenchAfterMutation(
      {
        refreshQuality: true,
        announceProgress: true,
        intentLabel: '页面契约一键重做',
        feedbackPageIndex: targetPages[0] || currentPageIndex.value
      },
      lifecycleToken,
      signal
    )
    if (!isPageCurrent(lifecycleToken)) return
    downloadReadinessActionFeedback.value = {
      type: 'success',
      title: '页面契约已开始收敛',
      summary: `已按页面契约自动重做 ${rebuiltCount} 个页面，系统会继续检查这些页是否更贴近它们声明的页面类型、页系样张和主视觉职责。`,
      points: [
        targetPages.length ? `已处理页面：${targetPagesText(targetPages)}` : '',
        contractFocus.length ? `重点收口：${contractFocus.join('；')}` : '重点收口：页面不像该页、缺页系语言、主视觉没落地'
      ].filter(Boolean),
      allowDownload: false,
      nextPendingItem: nextPendingDownloadItem.value
    }
    ElMessage.success(`已按页面契约自动重做 ${rebuiltCount} 个页面`)
    announceNextDownloadChecklistItem(item.key)
  } catch (err) {
    if (isPageCurrent(lifecycleToken) && !isAbortError(err)) {
      const detailMessage = err?.response?.data?.detail || err?.message
      ElMessage.error(detailMessage ? `一键重做契约页失败：${detailMessage}` : '一键重做契约页失败，请稍后重试')
    }
  } finally {
    if (isPageCurrent(lifecycleToken)) {
      downloadChecklistActionKey.value = ''
    }
  }
}

async function handleDownloadChecklistItem(
  item,
  lifecycleToken = pageLifecycle.capture(),
  externalSignal = null
) {
  if (!item || !isPageCurrent(lifecycleToken)) return
  const controller = externalSignal ? null : pageLifecycle.createController(lifecycleToken)
  const signal = externalSignal || controller?.signal
  try {
    if (item.key === 'placeholder') {
      await runInlinePlaceholderFix(item, lifecycleToken, signal)
      return
    }
    if (item.key === 'practice-template') {
      await runInlinePracticeTemplateFix(item, lifecycleToken, signal)
      return
    }
    if (item.key === 'page-contract') {
      await runInlinePageContractFix(item, lifecycleToken, signal)
      return
    }
    if (item.key === 'scoring-coverage') {
      await runInlineScoringCoverageFix(item, lifecycleToken, signal)
      return
    }
    if (item.key === 'p0') {
      await runInlineP0QuickFix(item, lifecycleToken, signal)
      return
    }
    if (!isPageCurrent(lifecycleToken)) return
    const navigationMessage = pendingDownloadAfterFix.value
      ? `已跳到「${item.title}」处理区，处理完后系统会继续带你回到下载流程。`
      : (item.detail || '已跳到对应处理区域')
    if (pendingDownloadAfterFix.value) {
      setDownloadFlowNavigationFeedback(item, navigationMessage)
    }
    await openWorkbenchIntent({
      tab: item.tab || 'quality',
      pageIndex: item.pageIndex ? Number(item.pageIndex) : null,
      relatedPoints: Array.isArray(item.relatedPoints) ? item.relatedPoints : [],
      targetPages: Array.isArray(item.targetPages) ? item.targetPages : [],
      title: item.title || '下载条件处理项'
    }, {
      message: navigationMessage
    })
  } finally {
    if (controller) {
      pageLifecycle.releaseController(controller)
    }
  }
}

async function handleWarningFollowupAction() {
  const first = deliverabilityBlockerActions.value[0]
  if (!first) {
    focusDownloadReadinessCard()
    return
  }
  downloadReadinessActionFeedback.value = {
    type: 'warning',
    title: '继续优化当前版本',
    summary: first.hint || `当前版本已经可以下载，但仍建议继续处理「${first.title}」。`,
    points: [
      first.pageIndex ? `优先页面：第${first.pageIndex}页` : '',
      Array.isArray(first.relatedPoints) && first.relatedPoints.length ? `优先补：${first.relatedPoints.slice(0, 3).join('、')}` : ''
    ].filter(Boolean),
    allowDownload: true
  }
  await openDeliverabilityBlocker(first)
}

function renderDownloadChecklistDialogContent(items) {
  return h('div', {
    style: {
      display: 'grid',
      gap: '14px',
      paddingTop: '4px'
    }
  }, [
    h('div', {
      style: {
        padding: '14px 16px',
        borderRadius: '16px',
        background: '#f8fafc',
        border: '1px solid #e2e8f0',
        color: '#334155',
        lineHeight: '1.7',
        fontSize: '14px'
      }
    }, '当前还不能直接下载。你可以先处理第一条关键条件，处理完后系统会继续带你回到下载流程。'),
    ...items.map((item, index) => h('div', {
      style: {
        padding: '16px',
        borderRadius: '18px',
        border: item.done ? '1px solid #bbf7d0' : '1px solid #fed7aa',
        background: item.done ? '#f0fdf4' : '#fff7ed',
        display: 'grid',
        gap: '8px'
      }
    }, [
      h('div', {
        style: {
          display: 'flex',
          justifyContent: 'space-between',
          gap: '12px',
          alignItems: 'center'
        }
      }, [
        h('strong', {
          style: {
            color: '#0f172a',
            fontSize: '15px',
            lineHeight: '1.5'
          }
        }, `${index + 1}. ${item.title}`),
        h('span', {
          style: {
            flexShrink: '0',
            padding: '4px 10px',
            borderRadius: '999px',
            background: item.done ? '#dcfce7' : '#ffedd5',
            color: item.done ? '#166534' : '#c2410c',
            fontSize: '12px',
            fontWeight: '700'
          }
        }, item.progressText || (item.done ? '已满足' : '未满足'))
      ]),
      h('div', {
        style: {
          height: '8px',
          borderRadius: '999px',
          background: '#e2e8f0',
          overflow: 'hidden'
        }
      }, [
        h('div', {
          style: {
            width: `${item.progressPercent || 0}%`,
            height: '100%',
            background: item.done ? 'linear-gradient(90deg, #22c55e, #16a34a)' : 'linear-gradient(90deg, #f59e0b, #ea580c)'
          }
        })
      ]),
      h('p', {
        style: {
          margin: '0',
          color: '#475569',
          fontSize: '13px',
          lineHeight: '1.7'
        }
      }, item.detail)
    ]))
  ])
}
</script>

<style scoped>
.ppt-history-detail__content {
  max-width: none;
  margin: 0;
  min-height: 0;
  padding: 22px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 20px;
  box-shadow: 0 18px 60px rgba(15, 23, 42, 0.08);
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 20px;
}

.summary-item {
  padding: 14px;
  border-radius: 14px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
}

.summary-item.quality-summary {
  background: #f0fdf4;
  border-color: #bbf7d0;
}

.summary-item.quality-summary.is-warning {
  background: #fffbeb;
  border-color: #fde68a;
}

.summary-item.quality-summary.is-fail {
  background: #fef2f2;
  border-color: #fecaca;
}

.summary-item.gate-summary {
  background: #eff6ff;
  border-color: #bfdbfe;
}

.summary-item.gate-summary.warning {
  background: #fffbeb;
  border-color: #fde68a;
}

.summary-item.health-summary {
  background: #f8fafc;
  border-color: #cbd5e1;
}

.summary-item.health-summary.is-ready {
  background: #f0fdf4;
  border-color: #bbf7d0;
}

.summary-item.health-summary.is-needs_work {
  background: #fffbeb;
  border-color: #fde68a;
}

.summary-item.health-summary.is-not_ready {
  background: #fef2f2;
  border-color: #fecaca;
}

.summary-item.deliverability-summary {
  background: #eff6ff;
  border-color: #bfdbfe;
}

.summary-item.deliverability-summary.is-ready {
  background: #f0fdf4;
  border-color: #bbf7d0;
}

.summary-item.deliverability-summary.is-warning {
  background: #fffbeb;
  border-color: #fde68a;
}

.summary-item.deliverability-summary.is-blocked {
  background: #fef2f2;
  border-color: #fecaca;
}

.summary-item.coverage-summary {
  background: #eef2ff;
  border-color: #c7d2fe;
}

.summary-item.scoring-risk-summary {
  background: #f8fafc;
  border-color: #cbd5e1;
}

.summary-item.scoring-risk-summary.is-stable {
  background: #f0fdf4;
  border-color: #bbf7d0;
}

.summary-item.scoring-risk-summary.is-watch {
  background: #fffbeb;
  border-color: #fde68a;
}

.summary-item.scoring-risk-summary.is-high_risk {
  background: #fef2f2;
  border-color: #fecaca;
}

.summary-item.practice-summary {
  background: #ecfeff;
  border-color: #a5f3fc;
}

.summary-item.practice-summary.needs-evidence {
  background: #fff7ed;
  border-color: #fed7aa;
}

.summary-item.material-summary {
  background: #f0fdfa;
  border-color: #99f6e4;
}

.summary-item.material-summary.warning {
  background: #fff7ed;
  border-color: #fed7aa;
}

.summary-item.roadshow-summary {
  background: #f5f3ff;
  border-color: #ddd6fe;
}

.summary-item.roadshow-summary.is-ready {
  background: #f0fdf4;
  border-color: #bbf7d0;
}

.summary-item.roadshow-summary.is-needs_focus {
  background: #fffbeb;
  border-color: #fde68a;
}

.summary-item.roadshow-summary.is-at_risk {
  background: #fef2f2;
  border-color: #fecaca;
}

.label {
  display: block;
  color: #94a3b8;
  font-size: 12px;
  margin-bottom: 6px;
}

.value {
  color: #0f172a;
  font-weight: 700;
}

.readiness-dashboard {
  display: grid;
  gap: 14px;
  margin-bottom: 20px;
  padding: 22px;
  border: 1px solid rgba(30, 64, 175, 0.14);
  border-radius: 24px;
  background:
    radial-gradient(circle at 94% 8%, rgba(37, 99, 235, 0.14), transparent 32%),
    radial-gradient(circle at 8% 88%, rgba(20, 184, 166, 0.12), transparent 28%),
    linear-gradient(135deg, #f8fafc, #fff);
}

.readiness-hero {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
}

.readiness-hero h2 {
  margin: 0 0 8px;
  color: #0f172a;
  font-size: 26px;
}

.readiness-hero p {
  margin: 0;
  color: #475569;
  line-height: 1.7;
}

.readiness-hero strong {
  min-width: 120px;
  text-align: right;
  color: #1e3a8a;
  font-size: 54px;
  line-height: 1;
}

.readiness-card-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 10px;
}

.readiness-card {
  min-height: 128px;
  padding: 14px;
  text-align: left;
  cursor: pointer;
  border: 1px solid #cbd5e1;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.78);
}

.readiness-card.ready {
  border-color: #bbf7d0;
  background: #f0fdf4;
}

.readiness-card.warning {
  border-color: #fde68a;
  background: #fffbeb;
}

.readiness-card.danger {
  border-color: #fecaca;
  background: #fef2f2;
}

.readiness-card span {
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
}

.readiness-card strong {
  display: block;
  margin: 8px 0;
  color: #0f172a;
  font-size: 22px;
}

.readiness-card p {
  margin: 0;
  color: #475569;
  font-size: 12px;
  line-height: 1.5;
}

.readiness-next-actions {
  display: grid;
  gap: 12px;
  padding: 16px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.72);
}

.deliverability-blockers {
  display: grid;
  gap: 12px;
  padding: 16px;
  border: 1px solid rgba(239, 68, 68, 0.18);
  border-radius: 20px;
  background: linear-gradient(135deg, rgba(254, 242, 242, 0.92), rgba(255, 255, 255, 0.9));
}

.deliverability-blockers h3 {
  margin: 0;
  color: #0f172a;
  font-size: 18px;
}

.deliverability-blocker-list {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.deliverability-blocker {
  min-height: 120px;
  padding: 14px;
  text-align: left;
  cursor: pointer;
  border: 1px solid #fecaca;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.92);
}

.deliverability-blocker.P0 {
  background: #fef2f2;
  border-color: #fca5a5;
}

.deliverability-blocker.P1 {
  background: #fff7ed;
  border-color: #fdba74;
}

.deliverability-blocker span {
  color: #dc2626;
  font-size: 12px;
  font-weight: 800;
}

.deliverability-blocker strong {
  display: block;
  margin: 6px 0;
  color: #111827;
  font-size: 15px;
}

.deliverability-blocker em {
  color: #475569;
  font-size: 12px;
  font-style: normal;
  line-height: 1.5;
}

.deliverability-blocker small {
  display: block;
  margin-top: 8px;
  color: #64748b;
  font-size: 12px;
  line-height: 1.5;
}

.download-flow-banner {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 18px;
  align-items: center;
  margin: 18px 0 0;
  padding: 18px 20px;
  border: 1px solid rgba(124, 58, 237, 0.18);
  border-radius: 22px;
  background: linear-gradient(135deg, rgba(245, 243, 255, 0.96), rgba(255, 255, 255, 0.98));
}

.download-flow-banner-copy strong {
  display: block;
  margin: 6px 0 8px;
  color: #4c1d95;
  font-size: 18px;
  line-height: 1.5;
}

.download-flow-banner-copy p {
  margin: 0;
  color: #6b7280;
  line-height: 1.7;
}

.download-flow-banner-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 10px;
}

.focus-pulse {
  position: relative;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.3), 0 18px 48px rgba(37, 99, 235, 0.16) !important;
}

.readiness-next-actions h3 {
  margin: 0;
  color: #0f172a;
  font-size: 18px;
}

.readiness-action-list {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.readiness-action-list button {
  min-height: 112px;
  padding: 13px;
  text-align: left;
  cursor: pointer;
  border: 1px solid #dbeafe;
  border-radius: 16px;
  background: #eff6ff;
}

.readiness-action-list button.P0 {
  border-color: #fecaca;
  background: #fef2f2;
}

.readiness-action-list button.P1 {
  border-color: #fde68a;
  background: #fffbeb;
}

.readiness-action-list span {
  color: #2563eb;
  font-size: 12px;
  font-weight: 800;
}

.readiness-action-list strong {
  display: block;
  margin: 6px 0;
  color: #0f172a;
  font-size: 15px;
}

.readiness-action-list em {
  color: #475569;
  font-size: 12px;
  font-style: normal;
  line-height: 1.5;
}

.preview-layout {
  display: grid;
  grid-template-columns: 228px minmax(0, 1fr) 308px;
  gap: 18px;
  align-items: stretch;
}

.page-list {
  height: clamp(700px, 76vh, 920px);
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.page-list-item {
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 12px;
  padding: 10px;
  text-align: left;
  cursor: pointer;
  display: flex;
  gap: 10px;
  align-items: center;
}

.page-list-item.is-pass {
  border-color: rgba(34, 197, 94, 0.28);
}

.page-list-item.is-warning {
  border-color: rgba(245, 158, 11, 0.42);
}

.page-list-item.is-fail {
  border-color: rgba(239, 68, 68, 0.42);
}

.page-list-item span {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  display: grid;
  place-items: center;
  background: #eff6ff;
  color: #2563eb;
  font-size: 12px;
  font-weight: 700;
}

.page-list-copy {
  min-width: 0;
  display: grid;
  gap: 4px;
}

.page-list-copy strong {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #334155;
  font-size: 13px;
}

.page-list-copy small {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #94a3b8;
  font-size: 11px;
}

.page-list-item.active {
  border-color: #2563eb;
  background: #eff6ff;
}

.page-list-item.pack-linked {
  border-color: rgba(59, 130, 246, 0.38);
  background: linear-gradient(135deg, rgba(239, 246, 255, 0.96), rgba(255, 255, 255, 0.96));
  box-shadow: inset 0 0 0 1px rgba(59, 130, 246, 0.08);
}

.preview-stage {
  min-height: clamp(700px, 76vh, 920px);
  border-radius: 18px;
  background: #0f172a;
  padding: 18px 18px 20px;
  overflow: hidden;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 12px;
}

.preview-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-width: 0;
  color: #dbeafe;
}

.preview-toolbar span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
  font-weight: 700;
}

.preview-viewport {
  min-height: 0;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  overflow: auto;
  padding: 8px;
  border-radius: 16px;
  background:
    radial-gradient(circle at top, rgba(59, 130, 246, 0.08), transparent 42%),
    linear-gradient(180deg, rgba(15, 23, 42, 0.96), rgba(2, 6, 23, 0.92));
}

.preview-canvas {
  width: 1920px;
  height: 1080px;
  flex-shrink: 0;
  transform-origin: top center;
  will-change: transform;
}

.preview-iframe {
  width: 1920px;
  height: 1080px;
  border: 0;
  border-radius: 16px;
  background: #fff;
  box-shadow: 0 28px 80px rgba(2, 6, 23, 0.38);
}

.speaker-panel {
  min-height: clamp(700px, 76vh, 920px);
  max-height: clamp(700px, 76vh, 920px);
  overflow: auto;
  padding: 16px;
  border-radius: 18px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background:
    radial-gradient(circle at 100% 0%, rgba(26, 115, 232, 0.14), transparent 34%),
    linear-gradient(180deg, #0f172a, #111827);
  box-shadow: 0 18px 50px rgba(15, 23, 42, 0.18);
}

.speaker-panel-head,
.speaker-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.speaker-panel h3 {
  margin: 14px 0 16px;
  color: rgba(255, 255, 255, 0.94);
  font-size: 20px;
  line-height: 1.35;
}

.workbench-score-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
  margin-bottom: 14px;
}

.workbench-score-grid div {
  padding: 10px 8px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.07);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.workbench-score-grid span {
  display: block;
  color: rgba(203, 213, 225, 0.74);
  font-size: 11px;
}

.workbench-score-grid strong {
  display: block;
  margin-top: 4px;
  color: rgba(255, 255, 255, 0.95);
  font-size: 18px;
}

.speaker-meta {
  padding: 12px 14px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.speaker-meta span,
.speaker-risks strong {
  display: block;
  margin-bottom: 6px;
  color: rgba(148, 163, 184, 0.92);
  font-size: 12px;
}

.speaker-primary-action {
  display: grid;
  gap: 4px;
}

.speaker-primary-action strong {
  color: rgba(255, 255, 255, 0.96);
  font-size: 15px;
}

.speaker-primary-action p {
  margin: 0;
  color: rgba(148, 163, 184, 0.92);
  font-size: 12px;
  line-height: 1.6;
  max-width: 250px;
}

.speaker-secondary-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 10px;
  margin-top: 10px;
}

.speaker-meta strong {
  color: rgba(255, 255, 255, 0.86);
  font-size: 13px;
  line-height: 1.55;
}

.workbench-card {
  margin-top: 14px;
  padding: 14px;
  border-radius: 16px;
  color: rgba(226, 232, 240, 0.9);
  background: rgba(15, 23, 42, 0.46);
  border: 1px solid rgba(148, 163, 184, 0.16);
}

.workbench-card > strong {
  display: block;
  margin-bottom: 10px;
  color: rgba(255, 255, 255, 0.94);
  font-size: 13px;
}

.workbench-card p {
  margin: 0;
  color: rgba(226, 232, 240, 0.82);
  font-size: 13px;
  line-height: 1.65;
}

.workbench-card p + p {
  margin-top: 8px;
}

.workbench-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.practice-contract-card dl {
  margin: 0;
  display: grid;
  gap: 8px;
}

.practice-contract-card dt {
  color: rgba(125, 211, 252, 0.92);
  font-size: 12px;
  font-weight: 700;
}

.practice-contract-card dd {
  margin: -4px 0 0;
  color: rgba(241, 245, 249, 0.84);
  font-size: 13px;
  line-height: 1.55;
}

.speaker-script {
  margin-top: 14px;
  max-height: 240px;
  overflow: auto;
  padding: 16px;
  border-radius: 18px;
  color: rgba(255, 255, 255, 0.82);
  background: rgba(2, 6, 23, 0.38);
  border: 1px solid rgba(148, 163, 184, 0.14);
  line-height: 1.75;
}

.script-title {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.script-title strong {
  color: rgba(255, 255, 255, 0.94);
  font-size: 13px;
}

.script-title span {
  color: rgba(148, 163, 184, 0.86);
  font-size: 11px;
  text-align: right;
  line-height: 1.4;
}

.speaker-script p,
.speaker-risks p {
  margin: 0;
}

.speaker-script .is-empty {
  color: rgba(251, 191, 36, 0.9);
}

.speaker-risks {
  margin-top: 14px;
  padding: 14px;
  border-radius: 16px;
  background: rgba(251, 191, 36, 0.08);
  border: 1px solid rgba(251, 191, 36, 0.18);
}

.speaker-risks p {
  color: rgba(254, 243, 199, 0.88);
  font-size: 13px;
  line-height: 1.6;
}

.action-feedback-card.success {
  background: rgba(34, 197, 94, 0.12);
  border-color: rgba(74, 222, 128, 0.24);
}

.action-feedback-card.warning {
  background: rgba(245, 158, 11, 0.12);
  border-color: rgba(251, 191, 36, 0.22);
}

.action-feedback-card.info {
  background: rgba(37, 99, 235, 0.12);
  border-color: rgba(96, 165, 250, 0.22);
}

.action-feedback-card p {
  margin: 8px 0 0;
  color: rgba(226, 232, 240, 0.9);
  line-height: 1.6;
  font-size: 13px;
}

.action-feedback-list {
  margin: 10px 0 0;
  padding-left: 18px;
  color: rgba(191, 219, 254, 0.95);
  font-size: 12px;
  line-height: 1.7;
}

.gate-mini-card {
  background: rgba(37, 99, 235, 0.12);
  border-color: rgba(96, 165, 250, 0.22);
}

.sequence-mini-card {
  background: rgba(245, 158, 11, 0.11);
  border-color: rgba(251, 191, 36, 0.22);
}

.evidence-mini-card {
  background: rgba(20, 184, 166, 0.1);
  border-color: rgba(45, 212, 191, 0.2);
}

.inline-material-card {
  background:
    radial-gradient(circle at 100% 0%, rgba(34, 197, 94, 0.14), transparent 34%),
    rgba(15, 23, 42, 0.54);
  border-color: rgba(74, 222, 128, 0.22);
}

.inline-material-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.inline-material-head p,
.inline-material-summary {
  margin-top: 6px;
}

.inline-material-summary {
  color: rgba(226, 232, 240, 0.82);
}

.inline-material-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.inline-material-tags span {
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(148, 163, 184, 0.16);
  color: rgba(255, 255, 255, 0.9);
  font-size: 12px;
  font-weight: 700;
}

.inline-material-tags.linked span {
  color: rgba(125, 211, 252, 0.95);
  border-color: rgba(56, 189, 248, 0.24);
  background: rgba(14, 116, 144, 0.18);
}

.inline-material-linked {
  display: grid;
  gap: 8px;
  margin-top: 12px;
}

.inline-material-linked label {
  color: rgba(148, 163, 184, 0.92);
  font-size: 12px;
  font-weight: 700;
}

.inline-material-form {
  display: grid;
  gap: 10px;
  margin-top: 12px;
}

.inline-material-task-drawer {
  display: grid;
  gap: 10px;
  margin-top: 12px;
  padding: 12px;
  border-radius: 16px;
  background: rgba(15, 23, 42, 0.28);
  border: 1px solid rgba(148, 163, 184, 0.14);
}

.inline-material-task-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.inline-material-task-head label {
  color: rgba(226, 232, 240, 0.96);
  font-size: 12px;
  font-weight: 800;
}

.inline-material-task-head p {
  margin: 6px 0 0;
  color: rgba(148, 163, 184, 0.9);
  font-size: 12px;
  line-height: 1.6;
}

.inline-material-task-list {
  display: grid;
  gap: 8px;
}

.inline-material-task-item {
  display: grid;
  gap: 6px;
  padding: 10px 12px;
  border-radius: 14px;
  border: 1px solid rgba(96, 165, 250, 0.16);
  background: rgba(255, 255, 255, 0.04);
  text-align: left;
  cursor: pointer;
}

.inline-material-task-item.active {
  border-color: rgba(59, 130, 246, 0.7);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.12);
}

.inline-material-task-item.ready {
  border-color: rgba(74, 222, 128, 0.3);
  background: rgba(34, 197, 94, 0.1);
}

.inline-material-task-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.inline-material-task-top span {
  color: rgba(125, 211, 252, 0.94);
  font-size: 12px;
  font-weight: 800;
}

.inline-material-task-top strong {
  color: rgba(226, 232, 240, 0.78);
  font-size: 12px;
}

.inline-material-task-item p {
  margin: 0;
  color: rgba(226, 232, 240, 0.88);
  line-height: 1.5;
  font-size: 12px;
}

.inline-material-upload :deep(.el-upload-dragger) {
  padding: 18px 12px;
  border-radius: 16px;
  border-color: rgba(74, 222, 128, 0.24);
  background: rgba(2, 6, 23, 0.24);
}

.speaker-actions {
  justify-content: flex-start;
  flex-wrap: wrap;
  margin-top: 16px;
}

.quality-panel {
  display: grid;
  gap: 18px;
}

.quality-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 24px;
  border-radius: 20px;
  background: linear-gradient(135deg, #ecfdf5, #f8fafc);
  border: 1px solid #bbf7d0;
}

.quality-hero.is-warning {
  background: linear-gradient(135deg, #fffbeb, #f8fafc);
  border-color: #fde68a;
}

.quality-hero.is-fail {
  background: linear-gradient(135deg, #fef2f2, #fff7ed);
  border-color: #fecaca;
}

.quality-eyebrow {
  display: inline-block;
  margin-bottom: 8px;
  color: #2563eb;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.1em;
}

.quality-hero h2 {
  margin: 0 0 8px;
  color: #0f172a;
  font-size: 24px;
}

.quality-hero p {
  margin: 0;
  color: #475569;
  line-height: 1.7;
}

.quality-hero strong {
  min-width: 112px;
  text-align: right;
  color: #0f172a;
  font-size: 48px;
  line-height: 1;
}

.quality-hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.quality-priority-board {
  padding: 22px;
  border: 1px solid rgba(37, 99, 235, 0.16);
  border-radius: 22px;
  background:
    radial-gradient(circle at 92% 10%, rgba(37, 99, 235, 0.12), transparent 30%),
    linear-gradient(135deg, #f8fafc, #fff);
}

.quality-priority-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 16px;
}

.quality-priority-head h3 {
  margin: 0 0 8px;
  color: #0f172a;
  font-size: 20px;
}

.quality-priority-head p {
  margin: 0;
  color: #64748b;
  font-size: 13px;
  line-height: 1.7;
}

.quality-priority-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.quality-priority-card {
  min-height: 190px;
  padding: 16px;
  border: 1px solid #e2e8f0;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.82);
}

.quality-priority-card.P0 {
  border-color: #fecaca;
  background: linear-gradient(135deg, #fef2f2, #fff);
}

.quality-priority-card.P1 {
  border-color: #fde68a;
  background: linear-gradient(135deg, #fffbeb, #fff);
}

.quality-priority-card.P2 {
  border-color: #bfdbfe;
  background: linear-gradient(135deg, #eff6ff, #fff);
}

.priority-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.priority-card-head span {
  display: inline-flex;
  width: 38px;
  height: 30px;
  align-items: center;
  justify-content: center;
  color: #fff;
  border-radius: 10px;
  background: #0f172a;
  font-size: 13px;
  font-weight: 800;
}

.priority-card-head strong {
  color: #0f172a;
  font-size: 24px;
}

.quality-priority-card h4 {
  margin: 12px 0 6px;
  color: #0f172a;
  font-size: 16px;
}

.quality-priority-card p {
  margin: 0;
  color: #475569;
  font-size: 13px;
  line-height: 1.65;
}

.priority-page-links {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  margin-top: 12px;
}

.priority-page-links button {
  padding: 6px 9px;
  color: #1e40af;
  cursor: pointer;
  border: 1px solid #bfdbfe;
  border-radius: 999px;
  background: #eff6ff;
  font-size: 12px;
}

.priority-empty {
  margin-top: 12px;
  color: #16a34a;
  font-size: 13px;
}

.html-gate-card {
  padding: 22px;
  border-radius: 22px;
  border: 1px solid rgba(59, 130, 246, 0.18);
  background:
    radial-gradient(circle at 90% 10%, rgba(14, 165, 233, 0.14), transparent 28%),
    linear-gradient(135deg, #eff6ff, #f8fafc);
}

.html-gate-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 16px;
}

.html-gate-head h3 {
  margin: 0 0 8px;
  color: #0f172a;
  font-size: 20px;
}

.html-gate-head p {
  margin: 0;
  color: #64748b;
  line-height: 1.7;
}

.html-gate-head strong {
  min-width: 96px;
  text-align: right;
  color: #2563eb;
  font-size: 34px;
}

.html-gate-list {
  display: grid;
  gap: 10px;
}

.html-gate-item {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(180px, 1fr) auto;
  align-items: center;
  gap: 14px;
  padding: 14px 16px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.78);
  border: 1px solid rgba(148, 163, 184, 0.18);
}

.html-gate-item span {
  color: #2563eb;
  font-size: 12px;
  font-weight: 700;
}

.html-gate-item h4 {
  margin: 4px 0;
  color: #0f172a;
  font-size: 16px;
}

.html-gate-item p {
  margin: 0;
  color: #64748b;
  font-size: 13px;
  line-height: 1.5;
}

.html-gate-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.html-gate-tags span {
  padding: 5px 8px;
  border-radius: 999px;
  color: #92400e;
  background: rgba(245, 158, 11, 0.14);
  font-size: 12px;
}

.quality-page-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.health-panel {
  display: grid;
  gap: 18px;
}

.final-review-panel {
  display: grid;
  gap: 20px;
}

.final-review-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 26px;
  border-radius: 22px;
  border: 1px solid #cbd5e1;
  background: linear-gradient(135deg, #f8fafc, #fff);
}

.final-review-hero.is-ready {
  border-color: #bbf7d0;
  background: linear-gradient(135deg, #ecfdf5, #f8fafc);
}

.final-review-hero.is-warning {
  border-color: #fde68a;
  background: linear-gradient(135deg, #fffbeb, #f8fafc);
}

.final-review-hero.is-blocked {
  border-color: #fecaca;
  background: linear-gradient(135deg, #fef2f2, #fff7ed);
}

.final-review-hero h2 {
  margin: 0 0 8px;
  color: #0f172a;
  font-size: 26px;
}

.final-review-hero p {
  margin: 0;
  color: #475569;
  line-height: 1.7;
}

.final-review-hero strong {
  min-width: 120px;
  text-align: right;
  color: #0f172a;
  font-size: 54px;
  line-height: 1;
}

.final-review-scoreboard {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.final-review-scoreboard div,
.final-review-card,
.final-review-blockers,
.final-review-column,
.final-review-pass-item {
  border: 1px solid #e2e8f0;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.88);
}

.final-review-scoreboard div {
  padding: 14px;
}

.final-review-scoreboard span {
  display: block;
  margin-bottom: 6px;
  color: #64748b;
  font-size: 12px;
}

.final-review-scoreboard strong {
  color: #0f172a;
  font-size: 18px;
}

.final-review-checklist {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.final-review-card {
  padding: 16px;
}

.final-review-card.pass {
  border-color: #bbf7d0;
  background: #f0fdf4;
}

.final-review-card.warning {
  border-color: #fde68a;
  background: #fffbeb;
}

.final-review-card.blocked {
  border-color: #fecaca;
  background: #fef2f2;
}

.final-review-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
}

.final-review-card h3 {
  margin: 10px 0 8px;
  color: #0f172a;
  font-size: 22px;
}

.final-review-card p {
  margin: 0 0 10px;
  color: #475569;
  line-height: 1.65;
}

.final-review-blockers,
.final-review-column {
  padding: 18px;
}

.final-review-columns {
  display: grid;
  grid-template-columns: 1.1fr 1fr;
  gap: 16px;
}

.download-readiness-card {
  margin-top: 18px;
  padding: 22px;
  border-radius: 24px;
  border: 1px solid #fed7aa;
  background:
    radial-gradient(circle at 100% 0%, rgba(251, 146, 60, 0.14), transparent 30%),
    linear-gradient(135deg, #fff7ed, #fff);
}

.download-readiness-card.ready {
  border-color: #86efac;
  background:
    radial-gradient(circle at 100% 0%, rgba(34, 197, 94, 0.14), transparent 30%),
    linear-gradient(135deg, #f0fdf4, #fff);
}

.download-readiness-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;
}

.download-readiness-head h3 {
  margin: 4px 0 8px;
  color: #0f172a;
  font-size: 20px;
}

.download-readiness-head p {
  margin: 0;
  color: #475569;
  line-height: 1.7;
}

.download-readiness-list {
  display: grid;
  gap: 10px;
}

.download-readiness-item {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  padding: 14px 16px;
  border-radius: 18px;
  border: 1px solid #fed7aa;
  background: rgba(255, 255, 255, 0.82);
}

.download-readiness-item.done {
  border-color: #bbf7d0;
  background: #f0fdf4;
}

.download-readiness-copy strong {
  display: block;
  color: #0f172a;
  font-size: 15px;
}

.download-progress-line {
  display: grid;
  gap: 8px;
  margin-top: 8px;
}

.download-progress-line span {
  color: #1e40af;
  font-size: 12px;
  font-weight: 800;
}

.download-readiness-copy p {
  margin: 6px 0 0;
  color: #475569;
  font-size: 13px;
  line-height: 1.7;
}

.download-inline-assist {
  display: grid;
  gap: 10px;
  margin-top: 12px;
}

.download-inline-group {
  display: grid;
  gap: 8px;
}

.download-inline-label {
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
}

.download-inline-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.download-inline-tag {
  display: inline-flex;
  align-items: center;
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  line-height: 1;
}

.download-inline-tag.point {
  color: #1d4ed8;
  background: #dbeafe;
}

.download-inline-tag.page {
  color: #0f766e;
  background: #ccfbf1;
}

.download-readiness-actions {
  display: grid;
  justify-items: end;
  gap: 8px;
  min-width: 110px;
}

.download-action-hint {
  color: #64748b;
  font-size: 11px;
  line-height: 1.5;
  text-align: right;
}

.final-review-section-head h3 {
  margin: 0;
  color: #0f172a;
  font-size: 18px;
}

.final-review-pass-list {
  display: grid;
  gap: 12px;
}

.final-review-pass-item {
  padding: 14px 16px;
}

.final-review-pass-item strong {
  display: block;
  color: #0f172a;
  font-size: 15px;
}

.final-review-pass-item p {
  margin: 6px 0 0;
  color: #475569;
  line-height: 1.6;
}

.health-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 26px;
  border-radius: 22px;
  border: 1px solid #cbd5e1;
  background: linear-gradient(135deg, #f8fafc, #fff);
}

.health-hero.is-ready {
  border-color: #bbf7d0;
  background: linear-gradient(135deg, #ecfdf5, #f8fafc);
}

.health-hero.is-needs_work {
  border-color: #fde68a;
  background: linear-gradient(135deg, #fffbeb, #f8fafc);
}

.health-hero.is-not_ready {
  border-color: #fecaca;
  background: linear-gradient(135deg, #fef2f2, #fff7ed);
}

.health-hero h2 {
  margin: 0 0 8px;
  color: #0f172a;
  font-size: 26px;
}

.health-hero p {
  margin: 0;
  color: #475569;
  line-height: 1.7;
}

.report-freshness-inline {
  display: block;
  margin-top: 8px;
  color: #64748b;
  font-size: 12px;
}

.health-hero strong {
  min-width: 120px;
  text-align: right;
  color: #0f172a;
  font-size: 54px;
  line-height: 1;
}

.health-score-grid,
.health-signals {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 10px;
}

.health-score-card,
.health-signals div {
  padding: 14px;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  background: #fff;
}

.health-score-card span,
.health-signals span {
  display: block;
  margin-bottom: 6px;
  color: #64748b;
  font-size: 12px;
}

.health-score-card strong,
.health-signals strong {
  color: #0f172a;
  font-size: 18px;
}

.health-blockers,
.health-actions {
  padding: 18px;
  border: 1px solid #e2e8f0;
  border-radius: 18px;
  background: #fff;
}

.health-blockers {
  border-color: #fecaca;
  background: #fef2f2;
}

.health-blockers h3,
.health-actions h3 {
  margin: 0 0 12px;
  color: #0f172a;
}

.health-blockers div {
  margin-top: 8px;
  padding: 10px 12px;
  color: #991b1b;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.72);
}

.health-action-card {
  display: grid;
  gap: 6px;
  margin-top: 10px;
  padding: 14px;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  background: #f8fafc;
}

.health-action-card.P0,
.health-action-card.P1 {
  border-color: #fecaca;
  background: #fff7ed;
}

.health-action-card span {
  color: #2563eb;
  font-size: 12px;
  font-weight: 700;
}

.health-action-card strong {
  color: #0f172a;
}

.health-action-card p {
  margin: 0;
  color: #475569;
  line-height: 1.6;
}

.optimization-queue {
  padding: 18px;
  border: 1px solid #dbeafe;
  border-radius: 18px;
  background: linear-gradient(135deg, #eff6ff, #f8fafc);
}

.optimization-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 12px;
}

.optimization-head h3 {
  margin: 0 0 6px;
  color: #0f172a;
}

.optimization-head p {
  margin: 0;
  color: #475569;
  font-size: 13px;
}

.optimization-list {
  display: grid;
  gap: 10px;
}

.optimization-task {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  padding: 14px;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.82);
}

.optimization-task.P0 {
  border-color: #fecaca;
  background: #fff7ed;
}

.optimization-task.P1 {
  border-color: #fde68a;
  background: #fffbeb;
}

.optimization-task.done {
  opacity: 0.72;
  border-color: #bbf7d0;
  background: #f0fdf4;
}

.optimization-task.reviewing {
  border-color: #bfdbfe;
  background: linear-gradient(135deg, #eff6ff, #fff);
}

.optimization-task-main {
  min-width: 0;
}

.optimization-task-main > span {
  color: #2563eb;
  font-size: 12px;
  font-weight: 700;
}

.optimization-task-main h4 {
  margin: 4px 0 6px;
  color: #0f172a;
}

.optimization-task-main p,
.optimization-task-main small {
  display: block;
  margin: 0;
  color: #475569;
  line-height: 1.6;
}

.optimization-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}

.optimization-tags span {
  padding: 5px 9px;
  color: #1e40af;
  border-radius: 999px;
  background: #dbeafe;
  font-size: 12px;
}

.optimization-task-actions {
  display: flex;
  align-items: center;
  flex-shrink: 0;
  gap: 8px;
}

.roadshow-panel {
  display: grid;
  gap: 18px;
}

.roadshow-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 24px;
  border-radius: 20px;
  border: 1px solid #ddd6fe;
  background: linear-gradient(135deg, #f5f3ff, #f8fafc);
}

.roadshow-hero.is-ready {
  border-color: #bbf7d0;
  background: linear-gradient(135deg, #ecfdf5, #f8fafc);
}

.roadshow-hero.is-needs_focus {
  border-color: #fde68a;
  background: linear-gradient(135deg, #fffbeb, #f8fafc);
}

.roadshow-hero.is-at_risk {
  border-color: #fecaca;
  background: linear-gradient(135deg, #fef2f2, #fff7ed);
}

.roadshow-hero h2 {
  margin: 0 0 8px;
  color: #0f172a;
  font-size: 24px;
}

.roadshow-hero p {
  margin: 0;
  color: #475569;
  line-height: 1.7;
}

.roadshow-hero strong {
  min-width: 112px;
  text-align: right;
  color: #0f172a;
  font-size: 48px;
  line-height: 1;
}

.roadshow-actions {
  padding: 18px;
  border: 1px solid #e2e8f0;
  border-radius: 18px;
  background: #fff;
}

.roadshow-story-map {
  padding: 22px;
  border: 1px solid rgba(14, 165, 233, 0.18);
  border-radius: 22px;
  background:
    radial-gradient(circle at 90% 8%, rgba(14, 165, 233, 0.14), transparent 28%),
    linear-gradient(135deg, #f0f9ff, #fff);
}

.roadshow-story-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 16px;
}

.roadshow-story-head h3 {
  margin: 0 0 8px;
  color: #0f172a;
  font-size: 20px;
}

.roadshow-story-head p {
  margin: 0;
  color: #475569;
  font-size: 13px;
  line-height: 1.7;
}

.roadshow-story-head strong {
  color: #0369a1;
  font-size: 34px;
  white-space: nowrap;
}

.roadshow-story-track {
  display: grid;
  gap: 10px;
}

.story-phase-card {
  display: grid;
  grid-template-columns: 48px minmax(0, 1fr) auto;
  align-items: flex-start;
  gap: 14px;
  padding: 14px;
  border: 1px solid #e2e8f0;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.82);
}

.story-phase-card.ready {
  border-color: #bbf7d0;
}

.story-phase-card.missing {
  border-color: #fecaca;
  background: #fff7ed;
}

.story-phase-card.active {
  box-shadow: inset 5px 0 0 #0ea5e9;
}

.story-phase-index {
  width: 42px;
  height: 42px;
  display: grid;
  place-items: center;
  color: #fff;
  border-radius: 14px;
  background: linear-gradient(135deg, #0369a1, #22c55e);
  font-weight: 800;
}

.story-phase-main span {
  color: #2563eb;
  font-size: 12px;
  font-weight: 700;
}

.story-phase-main h4 {
  margin: 5px 0 6px;
  color: #0f172a;
  font-size: 16px;
}

.story-phase-main p {
  margin: 0;
  color: #475569;
  font-size: 13px;
  line-height: 1.6;
}

.story-phase-alerts {
  display: grid;
  gap: 4px;
  margin-top: 10px;
  padding: 9px 10px;
  border: 1px solid #fde68a;
  border-radius: 12px;
  background: #fffbeb;
}

.story-phase-alerts span {
  color: #b45309;
  font-size: 12px;
  font-weight: 800;
}

.story-phase-alerts em {
  color: #92400e;
  font-size: 12px;
  font-style: normal;
  line-height: 1.45;
}

.story-phase-pages {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  margin-top: 10px;
}

.story-phase-pages button {
  padding: 6px 9px;
  color: #075985;
  cursor: pointer;
  border: 1px solid #bae6fd;
  border-radius: 999px;
  background: #f0f9ff;
  font-size: 12px;
}

.story-phase-pages em {
  color: #b45309;
  font-size: 12px;
  font-style: normal;
}

.story-phase-card > strong {
  color: #334155;
  font-size: 13px;
  white-space: nowrap;
}

.roadshow-actions h3,
.roadshow-sequence h3 {
  margin: 0 0 12px;
  color: #0f172a;
  font-size: 18px;
}

.roadshow-action-item {
  display: grid;
  gap: 4px;
  margin-top: 8px;
  padding: 12px 14px;
  border-radius: 14px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
}

.roadshow-action-item.high {
  background: #fef2f2;
  border-color: #fecaca;
}

.roadshow-action-item.medium {
  background: #fffbeb;
  border-color: #fde68a;
}

.roadshow-action-item strong {
  color: #0f172a;
}

.roadshow-action-item span {
  color: #475569;
  font-size: 13px;
  line-height: 1.6;
}

.roadshow-module-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.roadshow-module-card {
  padding: 16px;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  background: #f8fafc;
}

.roadshow-module-card.ready {
  border-color: #bbf7d0;
  background: #f0fdf4;
}

.roadshow-module-card.partial {
  border-color: #fde68a;
  background: #fffbeb;
}

.roadshow-module-card.missing {
  border-color: #fecaca;
  background: #fef2f2;
}

.roadshow-module-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.roadshow-module-head span {
  color: #64748b;
  font-size: 12px;
}

.roadshow-module-head h3 {
  margin: 4px 0 0;
  color: #0f172a;
  font-size: 16px;
}

.roadshow-module-head strong {
  color: #334155;
  white-space: nowrap;
}

.roadshow-module-card p,
.roadshow-sequence p {
  color: #475569;
  font-size: 13px;
  line-height: 1.6;
}

.roadshow-pages {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.roadshow-pages span {
  padding: 5px 9px;
  color: #1e40af;
  border-radius: 999px;
  background: #dbeafe;
  font-size: 12px;
}

.roadshow-sequence {
  padding: 18px;
  border: 1px solid #e2e8f0;
  border-radius: 18px;
  background: #fff;
  display: grid;
  gap: 10px;
}

.sequence-event {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  padding: 14px 16px;
  border-radius: 14px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
}

.sequence-event.high {
  background: #fef2f2;
  border-color: #fecaca;
}

.sequence-event.medium {
  background: #fffbeb;
  border-color: #fde68a;
}

.sequence-event.info {
  background: #f0fdf4;
  border-color: #bbf7d0;
}

.sequence-event span {
  color: #2563eb;
  font-size: 12px;
  font-weight: 700;
}

.sequence-event h4 {
  margin: 4px 0 6px;
  color: #0f172a;
  font-size: 15px;
}

.sequence-event p {
  margin: 0;
  color: #64748b;
  font-size: 13px;
}

.roadshow-pacing {
  display: grid;
  gap: 14px;
  padding: 18px;
  border: 1px solid #dbeafe;
  border-radius: 18px;
  background: linear-gradient(135deg, #eff6ff, #f8fafc);
}

.roadshow-pacing-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
}

.roadshow-pacing-head h3 {
  margin: 0 0 8px;
  color: #0f172a;
  font-size: 20px;
}

.roadshow-pacing-head p {
  margin: 0;
  color: #475569;
  line-height: 1.7;
}

.roadshow-pacing-head strong {
  color: #1d4ed8;
  font-size: 30px;
  white-space: nowrap;
}

.pacing-metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.pacing-metrics div {
  padding: 12px;
  border: 1px solid #bfdbfe;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.74);
}

.pacing-metrics span {
  display: block;
  color: #64748b;
  font-size: 12px;
  margin-bottom: 4px;
}

.pacing-metrics strong {
  color: #0f172a;
}

.pacing-issues {
  display: grid;
  gap: 8px;
}

.pacing-issues p {
  margin: 0;
  padding: 10px 12px;
  color: #1e3a8a;
  border-radius: 12px;
  background: rgba(219, 234, 254, 0.78);
  font-size: 13px;
  line-height: 1.6;
}

.pacing-page-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.pacing-page-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 7px 10px;
  border: 1px solid #bfdbfe;
  border-radius: 999px;
  background: #fff;
  color: #1e40af;
  cursor: pointer;
}

.pacing-page-chip.dense {
  border-color: #fdba74;
  color: #9a3412;
  background: #fff7ed;
}

.pacing-page-chip.thin {
  border-color: #ddd6fe;
  color: #6d28d9;
  background: #f5f3ff;
}

.pacing-page-chip strong {
  font-size: 12px;
}

.quality-page-card {
  padding: 16px;
  border: 1px solid #bbf7d0;
  border-radius: 16px;
  background: #f8fafc;
}

.quality-page-card.is-warning {
  border-color: #fde68a;
  background: #fffbeb;
}

.quality-page-card.is-fail {
  border-color: #fecaca;
  background: #fef2f2;
}

.quality-page-card.P0 {
  box-shadow: inset 5px 0 0 #ef4444;
}

.quality-page-card.P1 {
  box-shadow: inset 5px 0 0 #f59e0b;
}

.quality-page-card.P2 {
  box-shadow: inset 5px 0 0 #3b82f6;
}

.quality-page-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 12px;
}

.quality-page-head span {
  color: #64748b;
  font-size: 12px;
}

.quality-page-head h3 {
  margin: 4px 0 0;
  color: #0f172a;
  font-size: 15px;
}

.quality-page-head strong {
  color: #0f172a;
  white-space: nowrap;
}

.quality-card-brief {
  display: grid;
  gap: 6px;
  margin-bottom: 12px;
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(148, 163, 184, 0.18);
}

.quality-card-brief span {
  color: #0f172a;
  font-size: 13px;
  font-weight: 700;
}

.quality-card-brief em {
  color: #64748b;
  font-size: 12px;
  font-style: normal;
  line-height: 1.5;
}

.quality-checks {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.quality-checks span {
  padding: 5px 9px;
  color: #92400e;
  background: #fef3c7;
  border-radius: 999px;
  font-size: 12px;
}

.quality-checks span.pass {
  color: #166534;
  background: #dcfce7;
}

.quality-risk-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.risk-badge {
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(239, 68, 68, 0.12);
  color: #b91c1c;
  border: 1px solid rgba(239, 68, 68, 0.18);
  font-size: 12px;
  font-weight: 700;
}

.quality-issues {
  display: grid;
  gap: 6px;
  margin-top: 12px;
}

.quality-issues p {
  margin: 0;
  padding: 8px 10px;
  color: #9a3412;
  background: rgba(255, 237, 213, 0.78);
  border-radius: 10px;
  font-size: 12px;
  line-height: 1.5;
}

.quality-fix {
  margin: 12px 0 0;
  color: #b45309;
  font-size: 13px;
}

.quality-fix.quality-fix-warning {
  padding: 10px 12px;
  color: #9f1239;
  background: rgba(255, 241, 242, 0.92);
  border: 1px solid rgba(244, 114, 182, 0.28);
  border-radius: 12px;
  line-height: 1.6;
}

.quality-issue-profile {
  margin-top: 12px;
  padding: 12px;
  border: 1px solid #dbeafe;
  border-radius: 12px;
  background: linear-gradient(135deg, #eff6ff, #f8fafc);
}

.quality-issue-profile strong {
  display: block;
  margin-bottom: 6px;
  color: #1d4ed8;
  font-size: 12px;
}

.quality-issue-profile p {
  margin: 0;
  color: #475569;
  font-size: 12px;
  line-height: 1.6;
}

.quality-issue-profile p + p {
  margin-top: 4px;
}

.quality-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
}

.repair-preview-panel {
  display: grid;
  gap: 16px;
}

.repair-preview-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 16px;
  border: 1px solid #dbeafe;
  border-radius: 16px;
  background: linear-gradient(135deg, #eff6ff, #f8fafc);
}

.repair-preview-head span {
  color: #2563eb;
  font-size: 12px;
  font-weight: 700;
}

.repair-preview-head h3 {
  margin: 4px 0 0;
  color: #0f172a;
  font-size: 18px;
}

.repair-preview-escalation {
  margin: 8px 0 0;
  color: #1d4ed8;
  font-size: 12px;
  line-height: 1.6;
}

.repair-preview-head strong {
  color: #334155;
  white-space: nowrap;
}

.repair-preview-head strong.is-pass {
  color: #15803d;
}

.repair-preview-head strong.is-warning {
  color: #b45309;
}

.repair-preview-head strong.is-fail {
  color: #dc2626;
}

.repair-decision-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.repair-decision-card {
  min-height: 118px;
  padding: 16px;
  border: 1px solid #dbeafe;
  border-radius: 16px;
  background: linear-gradient(135deg, #f8fafc, #fff);
}

.repair-decision-card.success {
  border-color: #bbf7d0;
  background: linear-gradient(135deg, #ecfdf5, #fff);
}

.repair-decision-card.warning {
  border-color: #fde68a;
  background: linear-gradient(135deg, #fffbeb, #fff);
}

.repair-decision-card span {
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
}

.repair-decision-card strong {
  display: block;
  margin-top: 6px;
  color: #0f172a;
  font-size: 22px;
  line-height: 1.25;
}

.repair-decision-card p {
  margin: 8px 0 0;
  color: #475569;
  font-size: 13px;
  line-height: 1.6;
}

.repair-context-panel {
  display: grid;
  grid-template-columns: minmax(0, 1.3fr) minmax(220px, 0.9fr) minmax(220px, 0.9fr);
  gap: 12px;
  padding: 14px;
  border: 1px solid #e2e8f0;
  border-radius: 18px;
  background:
    radial-gradient(circle at 88% 8%, rgba(59, 130, 246, 0.12), transparent 28%),
    #f8fafc;
}

.repair-context-block {
  padding: 12px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.78);
  border: 1px solid rgba(148, 163, 184, 0.18);
}

.repair-context-block strong {
  display: block;
  margin-bottom: 8px;
  color: #0f172a;
  font-size: 13px;
}

.repair-context-block p {
  margin: 0;
  color: #475569;
  font-size: 13px;
  line-height: 1.6;
}

.repair-context-block p + p {
  margin-top: 6px;
}

.repair-context-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.repair-compare-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.repair-compare-card {
  overflow: hidden;
  border: 1px solid #e2e8f0;
  border-radius: 18px;
  background: #0f172a;
  box-shadow: 0 20px 50px rgba(15, 23, 42, 0.12);
}

.repair-compare-card.candidate {
  border-color: #60a5fa;
}

.repair-compare-title {
  padding: 10px 14px;
  color: #e2e8f0;
  background: rgba(15, 23, 42, 0.92);
  font-size: 13px;
  font-weight: 700;
}

.repair-frame-shell {
  position: relative;
  aspect-ratio: 16 / 9;
  overflow: hidden;
  background: #020617;
}

.repair-frame-shell iframe {
  position: absolute;
  top: 0;
  left: 0;
  display: block;
  width: 1920px;
  height: 1080px;
  border: 0;
  transform: scale(0.4);
  transform-origin: top left;
  background: #020617;
}

.repair-preview-warning {
  padding: 12px 14px;
  color: #92400e;
  border: 1px solid #fde68a;
  border-radius: 12px;
  background: #fffbeb;
  font-size: 13px;
}

.repair-preview-pass {
  padding: 12px 14px;
  color: #166534;
  border: 1px solid #bbf7d0;
  border-radius: 12px;
  background: #f0fdf4;
  font-size: 13px;
}

.repair-preview-next-action {
  padding: 12px 14px;
  border: 1px solid #bfdbfe;
  border-radius: 12px;
  background: linear-gradient(135deg, #eff6ff, #f8fafc);
}

.repair-preview-next-action strong {
  display: block;
  margin-bottom: 6px;
  color: #1d4ed8;
  font-size: 14px;
}

.repair-preview-next-action p {
  margin: 0;
  color: #475569;
  font-size: 13px;
  line-height: 1.6;
}

.repair-sync-panel {
  display: grid;
  gap: 14px;
}

.repair-sync-hero {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  padding: 18px;
  border: 1px solid #e2e8f0;
  border-radius: 18px;
  background: linear-gradient(135deg, #f8fafc, #fff);
}

.repair-sync-hero.is-pass {
  border-color: #bbf7d0;
  background: linear-gradient(135deg, #ecfdf5, #fff);
}

.repair-sync-hero.is-warning {
  border-color: #fde68a;
  background: linear-gradient(135deg, #fffbeb, #fff);
}

.repair-sync-hero.is-fail {
  border-color: #fecaca;
  background: linear-gradient(135deg, #fef2f2, #fff);
}

.repair-sync-hero.batch {
  border-color: #bfdbfe;
  background:
    radial-gradient(circle at 92% 12%, rgba(37, 99, 235, 0.12), transparent 30%),
    linear-gradient(135deg, #eff6ff, #fff);
}

.repair-sync-hero span {
  color: #2563eb;
  font-size: 12px;
  font-weight: 700;
}

.repair-sync-hero h3 {
  margin: 6px 0;
  color: #0f172a;
  font-size: 20px;
}

.repair-sync-hero p {
  margin: 0;
  color: #64748b;
  font-size: 13px;
}

.repair-sync-hero strong {
  color: #0f172a;
  font-size: 34px;
  line-height: 1;
  white-space: nowrap;
}

.repair-sync-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.repair-sync-item {
  padding: 12px;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  background: #fff;
}

.repair-sync-item.success {
  border-color: #bbf7d0;
  background: #f0fdf4;
}

.repair-sync-item.failed {
  border-color: #fecaca;
  background: #fef2f2;
}

.repair-sync-item span {
  display: block;
  color: #64748b;
  font-size: 12px;
}

.repair-sync-item strong {
  display: block;
  margin-top: 5px;
  color: #0f172a;
  font-size: 15px;
}

.repair-sync-review,
.repair-sync-issues {
  padding: 14px;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  background: #f8fafc;
}

.repair-sync-review strong,
.repair-sync-issues strong {
  display: block;
  margin-bottom: 8px;
  color: #0f172a;
  font-size: 14px;
}

.repair-sync-review p,
.repair-sync-issues p {
  margin: 0;
  color: #475569;
  font-size: 13px;
  line-height: 1.7;
}

.repair-sync-issues {
  border-color: #fde68a;
  background: #fffbeb;
}

.repair-sync-issues.batch-pages {
  border-color: #bfdbfe;
  background: #eff6ff;
}

.repair-sync-issues p + p {
  margin-top: 6px;
}

.repair-history-panel {
  min-height: 160px;
  display: grid;
  gap: 12px;
}

.repair-history-recommendation {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 18px;
  border: 1px solid #bfdbfe;
  border-radius: 16px;
  background: linear-gradient(135deg, #eff6ff, #f8fafc);
}

.repair-history-recommendation span {
  color: #2563eb;
  font-size: 12px;
  font-weight: 600;
}

.repair-history-recommendation h3 {
  margin: 6px 0;
  color: #0f172a;
  font-size: 16px;
}

.repair-history-recommendation p {
  margin: 0;
  color: #475569;
  font-size: 13px;
  line-height: 1.5;
}

.repair-history-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  background: #f8fafc;
}

.repair-history-main {
  min-width: 0;
}

.repair-history-main span {
  color: #64748b;
  font-size: 12px;
}

.repair-history-main h3 {
  margin: 4px 0;
  color: #0f172a;
  font-size: 16px;
}

.repair-history-main p {
  margin: 0;
  color: #475569;
  font-size: 13px;
  line-height: 1.5;
}

.repair-history-actions {
  display: flex;
  flex-shrink: 0;
  gap: 8px;
}

@media (max-width: 1200px) {
  .repair-compare-grid {
    grid-template-columns: 1fr;
  }

  .repair-frame-shell iframe {
    transform: scale(0.48);
  }
}

.coverage-panel {
  display: grid;
  gap: 18px;
}

.scoring-dashboard-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 24px;
  border: 1px solid #cbd5e1;
  border-radius: 20px;
  background: linear-gradient(135deg, #f8fafc, #fff);
}

.scoring-dashboard-hero.is-stable {
  border-color: #bbf7d0;
  background: linear-gradient(135deg, #ecfdf5, #f8fafc);
}

.scoring-dashboard-hero.is-watch {
  border-color: #fde68a;
  background: linear-gradient(135deg, #fffbeb, #f8fafc);
}

.scoring-dashboard-hero.is-high_risk {
  border-color: #fecaca;
  background: linear-gradient(135deg, #fef2f2, #fff7ed);
}

.scoring-dashboard-hero h2 {
  margin: 0 0 8px;
  color: #0f172a;
  font-size: 24px;
}

.scoring-dashboard-hero p {
  margin: 0;
  color: #475569;
  line-height: 1.7;
}

.scoring-dashboard-hero strong {
  min-width: 112px;
  text-align: right;
  color: #0f172a;
  font-size: 48px;
  line-height: 1;
}

.scoring-risk-actions {
  padding: 18px;
  border: 1px solid #e2e8f0;
  border-radius: 18px;
  background: #fff;
}

.scoring-risk-actions h3 {
  margin: 0 0 12px;
  color: #0f172a;
  font-size: 18px;
}

.scoring-risk-action {
  display: grid;
  gap: 4px;
  margin-top: 8px;
  padding: 12px 14px;
  border-radius: 14px;
  border: 1px solid #e2e8f0;
  background: #f8fafc;
}

.scoring-risk-action.high {
  border-color: #fecaca;
  background: #fef2f2;
}

.scoring-risk-action.medium {
  border-color: #fde68a;
  background: #fffbeb;
}

.scoring-risk-action strong {
  color: #0f172a;
}

.scoring-risk-action span {
  color: #475569;
  font-size: 13px;
  line-height: 1.6;
}

.judge-matrix {
  padding: 22px;
  border: 1px solid rgba(30, 64, 175, 0.14);
  border-radius: 22px;
  background:
    radial-gradient(circle at 92% 10%, rgba(30, 64, 175, 0.12), transparent 30%),
    linear-gradient(135deg, #f8fafc, #fff);
}

.judge-matrix-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 16px;
}

.judge-matrix-head h3 {
  margin: 0 0 8px;
  color: #0f172a;
  font-size: 20px;
}

.judge-matrix-head p {
  margin: 0;
  color: #64748b;
  font-size: 13px;
  line-height: 1.7;
}

.judge-matrix-head strong {
  color: #1e3a8a;
  font-size: 34px;
  white-space: nowrap;
}

.judge-matrix-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
}

.judge-category-card {
  min-height: 260px;
  padding: 15px;
  border: 1px solid #bbf7d0;
  border-radius: 18px;
  background: #f0fdf4;
}

.judge-category-card.medium {
  border-color: #fde68a;
  background: #fffbeb;
}

.judge-category-card.high {
  border-color: #fecaca;
  background: #fef2f2;
}

.judge-category-card.active {
  border-color: #2563eb;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.12);
}

.judge-category-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.judge-category-head span {
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
}

.judge-category-head h4 {
  margin: 5px 0 0;
  color: #0f172a;
  font-size: 17px;
}

.judge-category-head strong {
  color: #0f172a;
  font-size: 20px;
  white-space: nowrap;
}

.judge-category-card p {
  min-height: 58px;
  margin: 12px 0;
  color: #475569;
  font-size: 13px;
  line-height: 1.55;
}

.judge-category-metrics,
.judge-point-list {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}

.judge-category-metrics span {
  padding: 5px 8px;
  color: #334155;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.76);
  font-size: 12px;
}

.judge-point-list {
  margin-top: 12px;
}

.judge-point-list button {
  padding: 6px 8px;
  color: #334155;
  cursor: pointer;
  border: 1px solid rgba(148, 163, 184, 0.28);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.82);
  font-size: 12px;
}

.judge-point-list button.high {
  color: #991b1b;
  border-color: #fecaca;
  background: #fff1f2;
}

.judge-point-list button.medium {
  color: #92400e;
  border-color: #fde68a;
  background: #fffbeb;
}

.judge-point-list button.active {
  color: #1d4ed8;
  border-color: #2563eb;
  background: #dbeafe;
}

.judge-category-card em {
  display: block;
  margin-top: 12px;
  color: #475569;
  font-size: 12px;
  font-style: normal;
  line-height: 1.55;
}

.scoring-risk-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.scoring-risk-card {
  padding: 16px;
  border: 1px solid #bbf7d0;
  border-radius: 16px;
  background: #f0fdf4;
}

.scoring-risk-card.medium {
  border-color: #fde68a;
  background: #fffbeb;
}

.scoring-risk-card.high {
  border-color: #fecaca;
  background: #fef2f2;
}

.scoring-risk-card.active {
  border-color: #2563eb;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.1);
}

.scoring-risk-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.scoring-risk-head span {
  color: #64748b;
  font-size: 12px;
}

.scoring-risk-head h3 {
  margin: 4px 0 0;
  color: #0f172a;
  font-size: 16px;
}

.scoring-risk-head strong {
  color: #334155;
  white-space: nowrap;
}

.scoring-risk-card p {
  color: #475569;
  font-size: 13px;
  line-height: 1.6;
}

.scoring-risk-reasons,
.scoring-risk-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.scoring-risk-reasons span,
.scoring-risk-meta span {
  padding: 5px 9px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.72);
  color: #334155;
  font-size: 12px;
}

.coverage-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 24px;
  border-radius: 20px;
  background: linear-gradient(135deg, #eef2ff, #f8fafc);
  border: 1px solid #c7d2fe;
}

.coverage-hero h2 {
  margin: 0 0 8px;
  color: #0f172a;
  font-size: 24px;
}

.coverage-hero p {
  margin: 0;
  color: #475569;
  line-height: 1.7;
}

.coverage-hero strong {
  min-width: 120px;
  text-align: right;
  color: #312e81;
  font-size: 44px;
  line-height: 1;
}

.missing-box {
  padding: 18px;
  border: 1px solid #fed7aa;
  border-radius: 18px;
  background: #fff7ed;
}

.missing-box h3 {
  margin: 0 0 12px;
  color: #9a3412;
  font-size: 16px;
}

.missing-item {
  display: grid;
  gap: 4px;
  padding: 12px 0;
  border-top: 1px solid #fed7aa;
}

.missing-item.active {
  padding: 12px;
  border-radius: 14px;
  border-top-color: transparent;
  background: rgba(37, 99, 235, 0.08);
  box-shadow: inset 0 0 0 1px rgba(37, 99, 235, 0.16);
}

.missing-item strong {
  color: #7c2d12;
}

.missing-item span {
  color: #9a3412;
  line-height: 1.6;
}

.coverage-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.coverage-card {
  padding: 16px;
  border: 1px solid #fed7aa;
  border-radius: 16px;
  background: #fff7ed;
}

.coverage-card.covered {
  border-color: #bbf7d0;
  background: #f0fdf4;
}

.coverage-card.required:not(.covered) {
  border-color: #fecaca;
  background: #fef2f2;
}

.coverage-card.active {
  border-color: #2563eb;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.1);
}

.coverage-card-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 10px;
}

.coverage-card-head span {
  color: #64748b;
  font-size: 12px;
}

.coverage-card-head h3 {
  margin: 4px 0 0;
  color: #0f172a;
  font-size: 15px;
}

.coverage-card-head strong {
  color: #0f172a;
  white-space: nowrap;
}

.coverage-card p {
  margin: 0;
  color: #475569;
  line-height: 1.6;
  font-size: 13px;
}

.practice-panel {
  display: grid;
  gap: 18px;
}

.practice-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 24px;
  border-radius: 20px;
  background: linear-gradient(135deg, #ecfeff, #f8fafc);
  border: 1px solid #a5f3fc;
}

.practice-hero.needs-evidence {
  background: linear-gradient(135deg, #fff7ed, #f8fafc);
  border-color: #fed7aa;
}

.practice-hero h2 {
  margin: 0 0 8px;
  color: #0f172a;
  font-size: 24px;
}

.practice-hero p {
  margin: 0;
  color: #475569;
  line-height: 1.7;
}

.practice-hero strong {
  min-width: 120px;
  text-align: right;
  color: #155e75;
  font-size: 42px;
  line-height: 1;
}

.practice-loop-board {
  padding: 22px;
  border: 1px solid #99f6e4;
  border-radius: 22px;
  background:
    radial-gradient(circle at 92% 8%, rgba(20, 184, 166, 0.16), transparent 30%),
    linear-gradient(135deg, #f0fdfa, #fff);
}

.practice-loop-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 16px;
}

.practice-loop-head h3 {
  margin: 0 0 8px;
  color: #0f172a;
  font-size: 20px;
}

.practice-loop-head p {
  margin: 0;
  color: #475569;
  font-size: 13px;
  line-height: 1.7;
}

.practice-loop-head strong {
  color: #0f766e;
  font-size: 34px;
  white-space: nowrap;
}

.practice-loop-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.practice-loop-card {
  padding: 15px;
  border: 1px solid #fed7aa;
  border-radius: 18px;
  background: #fff7ed;
}

.practice-loop-card.complete {
  border-color: #bbf7d0;
  background: #f0fdf4;
}

.practice-loop-title {
  display: flex;
  justify-content: space-between;
  gap: 10px;
}

.practice-loop-title span {
  color: #0f766e;
  font-size: 12px;
  font-weight: 800;
}

.practice-loop-title strong {
  color: #334155;
  font-size: 12px;
  white-space: nowrap;
}

.practice-loop-card h4 {
  margin: 8px 0 10px;
  color: #0f172a;
  font-size: 16px;
}

.practice-loop-checks {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}

.practice-loop-checks span {
  padding: 5px 8px;
  color: #92400e;
  border-radius: 999px;
  background: #ffedd5;
  font-size: 12px;
}

.practice-loop-checks span.pass {
  color: #166534;
  background: #dcfce7;
}

.practice-loop-card p {
  margin: 12px 0;
  color: #475569;
  font-size: 13px;
  line-height: 1.6;
}

.practice-loop-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.practice-list {
  display: grid;
  gap: 14px;
}

.practice-step-card {
  display: grid;
  grid-template-columns: 46px 1fr;
  gap: 14px;
  padding: 18px;
  border: 1px solid #bae6fd;
  border-radius: 18px;
  background: #f8fafc;
}

.practice-step-card.needs-evidence {
  border-color: #fed7aa;
  background: #fff7ed;
}

.practice-step-index {
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  border-radius: 12px;
  color: #fff;
  background: #0891b2;
  font-weight: 800;
}

.practice-step-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 8px;
}

.practice-step-head span {
  color: #64748b;
  font-size: 12px;
}

.practice-step-head h3 {
  margin: 4px 0 0;
  color: #0f172a;
  font-size: 17px;
}

.practice-step-head strong {
  color: #0f172a;
  white-space: nowrap;
}

.practice-goal {
  margin: 0 0 12px;
  color: #475569;
  line-height: 1.7;
}

.practice-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.practice-tags span {
  padding: 5px 10px;
  color: #155e75;
  background: #cffafe;
  border-radius: 999px;
  font-size: 12px;
}

.evidence-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 10px;
}

.evidence-grid > div,
.script-box {
  padding: 12px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid #e2e8f0;
}

.evidence-grid label,
.script-box label {
  display: block;
  margin-bottom: 6px;
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
}

.evidence-grid p,
.script-box p {
  margin: 0;
  color: #334155;
  line-height: 1.6;
  font-size: 13px;
}

.script-box.fallback {
  margin-top: 10px;
  background: #f8fafc;
}

.materials-panel {
  display: grid;
  gap: 18px;
}

.materials-hero {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 20px 22px;
  border-radius: 22px;
  border: 1px solid #dbeafe;
  background:
    radial-gradient(circle at 100% 0%, rgba(37, 99, 235, 0.08), transparent 28%),
    linear-gradient(135deg, #eff6ff, #fff);
}

.materials-hero h3 {
  margin: 6px 0 8px;
  color: #0f172a;
  font-size: 20px;
}

.materials-hero p {
  margin: 0;
  color: #475569;
  line-height: 1.7;
}

.materials-primary-tasks {
  border-radius: 22px;
  border: 1px solid #dbeafe;
  background: #fff;
  overflow: hidden;
}

.materials-primary-tasks > summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 16px 20px;
  cursor: pointer;
  list-style: none;
  color: #0f172a;
  font-weight: 800;
}

.materials-primary-tasks > summary::-webkit-details-marker {
  display: none;
}

.materials-primary-tasks > summary strong {
  min-width: 64px;
  padding: 8px 10px;
  border-radius: 999px;
  background: #eff6ff;
  color: #2563eb;
  font-size: 16px;
  text-align: center;
}

.material-task-board {
  padding: 22px;
  border: 1px solid #bfdbfe;
  border-radius: 24px;
  background:
    radial-gradient(circle at 100% 0%, rgba(37, 99, 235, 0.1), transparent 28%),
    linear-gradient(135deg, #eff6ff, #fff);
}

.material-task-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.material-task-head h3 {
  margin: 4px 0 8px;
  color: #0f172a;
  font-size: 20px;
}

.material-task-head p {
  margin: 0;
  color: #475569;
  line-height: 1.7;
}

.material-task-head strong {
  min-width: 72px;
  padding: 12px 14px;
  border-radius: 18px;
  color: #1d4ed8;
  background: rgba(255, 255, 255, 0.84);
  font-size: 28px;
  text-align: center;
}

.material-task-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.material-task-item {
  display: grid;
  gap: 10px;
  padding: 16px;
  border: 1px solid #dbeafe;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.86);
  text-align: left;
  cursor: pointer;
}

.material-task-item.active {
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.material-task-item.ready {
  border-color: #bbf7d0;
  background: #f0fdf4;
}

.material-task-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.material-task-top span {
  color: #2563eb;
  font-size: 12px;
  font-weight: 900;
}

.material-task-top strong {
  color: #64748b;
  font-size: 12px;
}

.material-task-item h4 {
  margin: 0;
  color: #0f172a;
  font-size: 17px;
}

.material-task-item p {
  margin: 0;
  color: #475569;
  font-size: 13px;
  line-height: 1.7;
}

.material-task-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.material-task-tags span {
  padding: 6px 10px;
  border-radius: 999px;
  color: #92400e;
  background: #fff7ed;
  font-size: 12px;
  font-weight: 800;
}

.material-upload-card {
  display: grid;
  grid-template-columns: minmax(0, 0.9fr) minmax(360px, 1.1fr);
  gap: 20px;
  padding: 24px;
  border: 1px solid #99f6e4;
  border-radius: 20px;
  background: linear-gradient(135deg, #f0fdfa, #f8fafc);
}

.material-pack-banner {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  margin: 14px 0 0;
  padding: 14px 16px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.76);
  border: 1px solid rgba(59, 130, 246, 0.18);
}

.material-pack-banner span {
  color: #2563eb;
  font-size: 12px;
  font-weight: 900;
}

.material-pack-banner strong {
  display: block;
  margin-top: 4px;
  color: #0f172a;
  font-size: 16px;
}

.material-pack-banner small {
  display: block;
  margin-top: 6px;
  color: #64748b;
  line-height: 1.6;
}

.material-pack-banner-pages,
.material-upload-target-pages {
  display: grid;
  gap: 8px;
  margin-top: 12px;
}

.material-pack-banner-pages label,
.material-upload-target-pages label {
  color: #475569;
  font-size: 12px;
  font-weight: 900;
}

.material-pack-focus-board {
  padding: 20px 22px;
  border-radius: 22px;
  border: 1px solid #bfdbfe;
  background:
    radial-gradient(circle at 100% 0%, rgba(37, 99, 235, 0.12), transparent 30%),
    linear-gradient(135deg, #eff6ff, #ffffff);
}

.material-pack-focus-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;
}

.material-pack-focus-head h3 {
  margin: 4px 0 8px;
  color: #0f172a;
  font-size: 20px;
}

.material-pack-focus-head p {
  margin: 0;
  color: #475569;
  line-height: 1.7;
}

.material-pack-focus-head strong {
  min-width: 64px;
  padding: 10px 12px;
  border-radius: 16px;
  color: #1d4ed8;
  background: rgba(255, 255, 255, 0.8);
  font-size: 20px;
  text-align: center;
}

.material-pack-focus-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(0, 0.8fr);
  gap: 14px;
}

.material-pack-focus-block {
  display: grid;
  gap: 10px;
}

.material-pack-focus-block > span {
  color: #64748b;
  font-size: 12px;
  font-weight: 900;
}

.material-pack-page-pills,
.material-pack-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.material-pack-page-pills.compact {
  gap: 6px;
}

.material-pack-page-pill {
  padding: 8px 12px;
  border: 1px solid #bfdbfe;
  border-radius: 999px;
  color: #1d4ed8;
  background: #ffffff;
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
}

.material-pack-page-pills.compact .material-pack-page-pill {
  padding: 6px 10px;
  font-size: 12px;
}

.material-pack-page-pill.active {
  border-color: #2563eb;
  background: #dbeafe;
}

.material-pack-tags strong {
  padding: 8px 12px;
  border-radius: 999px;
  color: #92400e;
  background: #fff7ed;
  font-size: 12px;
}

.policy-evidence-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 20px;
  border-radius: 20px;
  background:
    radial-gradient(circle at 100% 0%, rgba(37, 99, 235, 0.12), transparent 32%),
    linear-gradient(135deg, #eff6ff, #f8fafc);
  border: 1px solid #bfdbfe;
}

.policy-evidence-card h3 {
  margin: 6px 0 8px;
  color: #0f172a;
  font-size: 18px;
}

.policy-evidence-card p {
  margin: 0;
  color: #475569;
  line-height: 1.7;
}

.evidence-plan-board {
  padding: 22px;
  border: 1px solid #fed7aa;
  border-radius: 24px;
  background:
    radial-gradient(circle at 92% 4%, rgba(249, 115, 22, 0.15), transparent 28%),
    linear-gradient(135deg, #fff7ed, #fff);
}

.evidence-plan-board.ready {
  border-color: #86efac;
  background:
    radial-gradient(circle at 92% 4%, rgba(34, 197, 94, 0.16), transparent 28%),
    linear-gradient(135deg, #f0fdf4, #fff);
}

.evidence-plan-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 16px;
}

.evidence-plan-head h3 {
  margin: 0 0 8px;
  color: #0f172a;
  font-size: 20px;
}

.evidence-plan-head p {
  margin: 0;
  color: #475569;
  line-height: 1.7;
}

.evidence-plan-score {
  min-width: 112px;
  padding: 12px 14px;
  border-radius: 18px;
  text-align: center;
  background: rgba(255, 255, 255, 0.78);
  box-shadow: 0 16px 36px rgba(249, 115, 22, 0.12);
}

.evidence-plan-score strong {
  display: block;
  color: #c2410c;
  font-size: 30px;
  line-height: 1;
}

.evidence-plan-score span {
  color: #64748b;
  font-size: 12px;
  font-weight: 800;
}

.evidence-plan-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.evidence-pack-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 16px;
}

.evidence-pack-card {
  display: flex;
  min-height: 220px;
  flex-direction: column;
  gap: 10px;
  padding: 18px;
  border: 1px solid rgba(251, 146, 60, 0.28);
  border-radius: 22px;
  background:
    radial-gradient(circle at 100% 0%, rgba(59, 130, 246, 0.08), transparent 30%),
    rgba(255, 255, 255, 0.9);
  box-shadow: 0 14px 30px rgba(15, 23, 42, 0.06);
}

.evidence-pack-card.ready {
  border-color: rgba(34, 197, 94, 0.28);
  background:
    radial-gradient(circle at 100% 0%, rgba(34, 197, 94, 0.12), transparent 32%),
    #f8fffb;
}

.evidence-pack-card.active {
  border-color: rgba(37, 99, 235, 0.38);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.evidence-pack-card.partial {
  border-color: rgba(245, 158, 11, 0.26);
  background:
    radial-gradient(circle at 100% 0%, rgba(245, 158, 11, 0.12), transparent 32%),
    #fffdf7;
}

.evidence-pack-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
}

.evidence-pack-head span {
  color: #ea580c;
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0.02em;
}

.evidence-pack-head h4 {
  margin: 4px 0 0;
  color: #0f172a;
  font-size: 18px;
}

.evidence-pack-head strong {
  min-width: 58px;
  padding: 8px 10px;
  border-radius: 14px;
  color: #1d4ed8;
  background: rgba(219, 234, 254, 0.78);
  font-size: 18px;
  text-align: center;
}

.evidence-pack-card p {
  margin: 0;
  color: #475569;
  font-size: 13px;
  line-height: 1.7;
}

.evidence-pack-pages,
.evidence-pack-assets {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.evidence-pack-pages span,
.evidence-pack-assets span {
  color: #64748b;
  font-size: 12px;
  font-weight: 800;
}

.evidence-pack-pages strong,
.evidence-pack-assets strong {
  color: #0f172a;
  font-size: 13px;
  line-height: 1.6;
}

.evidence-pack-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.evidence-pack-tags span {
  padding: 6px 10px;
  border-radius: 999px;
  color: #92400e;
  background: #fff7ed;
  font-size: 12px;
  font-weight: 800;
}

.evidence-pack-reasons {
  padding: 10px 12px;
  border-radius: 16px;
  color: #854d0e;
  background: rgba(254, 249, 195, 0.7);
  font-size: 12px;
  line-height: 1.6;
}

.evidence-pack-actions {
  margin-top: auto;
  display: flex;
  justify-content: flex-start;
}

.evidence-plan-subhead {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin: 8px 0 14px;
}

.evidence-plan-subhead strong {
  color: #0f172a;
  font-size: 15px;
}

.evidence-plan-subhead span {
  color: #64748b;
  font-size: 13px;
}

.evidence-plan-card {
  display: flex;
  min-height: 245px;
  flex-direction: column;
  gap: 10px;
  padding: 16px;
  border: 1px solid #fed7aa;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.82);
}

.evidence-plan-card.ready {
  border-color: #bbf7d0;
  background: #f0fdf4;
}

.evidence-plan-card.idle {
  border-color: #e2e8f0;
  background: #f8fafc;
}

.evidence-plan-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.evidence-plan-card-head span {
  color: #ea580c;
  font-size: 12px;
  font-weight: 900;
}

.evidence-plan-card-head strong {
  color: #334155;
  font-size: 12px;
}

.evidence-plan-card h4 {
  margin: 0;
  color: #0f172a;
  font-size: 17px;
}

.evidence-plan-card p {
  min-height: 60px;
  margin: 0;
  color: #475569;
  font-size: 13px;
  line-height: 1.6;
}

.evidence-plan-pages {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  color: #1d4ed8;
  font-size: 12px;
  font-weight: 800;
}

.evidence-plan-requirements {
  display: grid;
  gap: 6px;
}

.evidence-plan-requirements button {
  overflow: hidden;
  padding: 7px 9px;
  border: 1px solid #fed7aa;
  border-radius: 999px;
  color: #9a3412;
  background: #fff7ed;
  font-size: 12px;
  text-align: left;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
}

.evidence-chain-board {
  padding: 22px;
  border: 1px solid #bfdbfe;
  border-radius: 22px;
  background:
    radial-gradient(circle at 92% 10%, rgba(37, 99, 235, 0.12), transparent 30%),
    linear-gradient(135deg, #eff6ff, #fff);
}

.evidence-chain-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 16px;
}

.evidence-chain-head h3 {
  margin: 0 0 8px;
  color: #0f172a;
  font-size: 20px;
}

.evidence-chain-head p {
  margin: 0;
  color: #475569;
  font-size: 13px;
  line-height: 1.7;
}

.evidence-chain-head strong {
  color: #1d4ed8;
  font-size: 34px;
  white-space: nowrap;
}

.evidence-chain-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.evidence-chain-card {
  min-height: 220px;
  padding: 15px;
  border: 1px solid #bbf7d0;
  border-radius: 18px;
  background: #f0fdf4;
}

.evidence-chain-card.warning {
  border-color: #fde68a;
  background: #fffbeb;
}

.evidence-chain-card.missing {
  border-color: #fecaca;
  background: #fef2f2;
}

.evidence-chain-card-head {
  display: flex;
  justify-content: space-between;
  gap: 10px;
}

.evidence-chain-card-head span {
  color: #2563eb;
  font-size: 12px;
  font-weight: 800;
}

.evidence-chain-card-head strong {
  color: #334155;
  font-size: 12px;
  white-space: nowrap;
}

.evidence-chain-card h4 {
  margin: 10px 0 8px;
  color: #0f172a;
  font-size: 17px;
}

.evidence-chain-card p {
  min-height: 62px;
  margin: 0 0 12px;
  color: #475569;
  font-size: 13px;
  line-height: 1.6;
}

.evidence-chain-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  min-height: 30px;
  margin-bottom: 12px;
}

.evidence-chain-tags span {
  padding: 5px 8px;
  color: #1e40af;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.78);
  font-size: 12px;
}

.material-upload-copy h2 {
  margin: 0 0 8px;
  color: #0f172a;
  font-size: 24px;
}

.material-upload-copy p {
  margin: 0 0 14px;
  color: #475569;
  line-height: 1.7;
}

.material-upload-controls {
  display: grid;
  gap: 10px;
}

.material-upload-icon {
  color: #0f766e;
  font-size: 30px;
}

.material-list {
  display: grid;
  gap: 14px;
}

.material-card {
  display: grid;
  grid-template-columns: 180px 1fr;
  gap: 16px;
  padding: 16px;
  border: 1px solid #ccfbf1;
  border-radius: 18px;
  background: #fff;
}

.material-card.warning {
  border-color: #fed7aa;
  background: #fff7ed;
}

.materials-advanced {
  display: grid;
  gap: 18px;
}

.materials-advanced > summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  color: #475569;
  font-size: 13px;
  font-weight: 800;
  list-style: none;
  padding: 12px 14px;
  border-radius: 14px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
}

.materials-advanced > summary::-webkit-details-marker {
  display: none;
}

.material-thumb {
  height: 124px;
  display: grid;
  place-items: center;
  overflow: hidden;
  border-radius: 14px;
  background: #0f172a;
  color: #fff;
  font-weight: 800;
  text-decoration: none;
}

.material-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.material-thumb.document {
  background: linear-gradient(135deg, #0f766e, #0891b2);
}

.material-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 8px;
}

.material-head span {
  color: #64748b;
  font-size: 12px;
}

.material-head h3 {
  margin: 4px 0 0;
  color: #0f172a;
  font-size: 16px;
}

.material-head strong {
  color: #0f766e;
  white-space: nowrap;
}

.material-body p {
  margin: 0 0 10px;
  color: #475569;
  line-height: 1.6;
  font-size: 13px;
}

.material-tags,
.material-tips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}

.material-tags span {
  padding: 5px 10px;
  color: #115e59;
  background: #ccfbf1;
  border-radius: 999px;
  font-size: 12px;
}

.binding-recommendation {
  margin-top: 12px;
  padding: 12px;
  border: 1px solid #dbeafe;
  border-radius: 12px;
  background: #eff6ff;
}

.binding-recommendation label {
  display: block;
  margin-bottom: 6px;
  color: #1d4ed8;
  font-size: 12px;
  font-weight: 800;
}

.binding-recommendation p {
  margin: 0 0 8px;
  color: #1e3a8a;
  font-size: 13px;
  line-height: 1.6;
}

.binding-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}

.binding-list span {
  padding: 5px 10px;
  color: #1e40af;
  background: #dbeafe;
  border-radius: 999px;
  font-size: 12px;
}

.material-tips span {
  padding: 6px 10px;
  color: #9a3412;
  background: #ffedd5;
  border-radius: 10px;
  font-size: 12px;
}

.outline-list,
.snapshot-list {
  display: grid;
  gap: 12px;
}

.outline-item {
  display: grid;
  grid-template-columns: 42px 1fr;
  gap: 14px;
  padding: 14px;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  background: #fff;
}

.page-number {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: grid;
  place-items: center;
  background: #0f172a;
  color: #fff;
  font-weight: 700;
}

.outline-item h3 {
  margin: 0 0 6px;
  color: #0f172a;
  font-size: 15px;
}

.outline-item p {
  margin: 0;
  color: #64748b;
  line-height: 1.6;
}

.json-view {
  margin: 0;
  padding: 16px;
  max-height: 680px;
  overflow: auto;
  border-radius: 14px;
  background: #0f172a;
  color: #dbeafe;
  font-size: 12px;
  line-height: 1.6;
}

.json-view.compact {
  max-height: 260px;
}

.snapshot-item {
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  overflow: hidden;
}

.snapshot-meta {
  display: flex;
  justify-content: space-between;
  padding: 12px 14px;
  background: #f8fafc;
  color: #334155;
}

@media (max-width: 900px) {
  .summary-grid,
  .readiness-card-grid,
  .readiness-action-list,
  .preview-layout,
  .quality-page-list,
  .quality-priority-grid,
  .repair-decision-grid,
  .repair-context-panel,
  .repair-sync-grid,
  .health-score-grid,
  .health-signals,
  .story-phase-card,
  .judge-matrix-grid,
  .practice-loop-grid,
  .evidence-pack-grid,
  .evidence-plan-grid,
  .evidence-chain-grid,
  .coverage-list,
  .scoring-risk-grid,
  .evidence-grid,
  .material-task-list,
  .material-upload-card,
  .material-card,
  .pacing-metrics {
    grid-template-columns: 1fr;
  }

  .policy-evidence-card {
    align-items: flex-start;
    flex-direction: column;
  }

  .material-pack-banner,
  .material-pack-focus-head,
  .material-pack-focus-grid,
  .evidence-plan-head {
    align-items: flex-start;
    flex-direction: column;
  }

  .evidence-plan-subhead {
    align-items: flex-start;
    flex-direction: column;
  }

  .health-hero,
  .quality-hero,
  .roadshow-hero,
  .coverage-hero,
  .practice-hero {
    align-items: flex-start;
    flex-direction: column;
  }

  .readiness-hero,
  .readiness-next-actions {
    align-items: flex-start;
    flex-direction: column;
  }

  .health-hero strong,
  .readiness-hero strong,
  .quality-hero strong,
  .roadshow-hero strong,
  .coverage-hero strong,
  .practice-hero strong {
    text-align: left;
  }

  .roadshow-module-grid {
    grid-template-columns: 1fr;
  }

  .roadshow-pacing-head {
    flex-direction: column;
  }

  .optimization-head,
  .optimization-task {
    flex-direction: column;
  }

  .practice-step-card {
    grid-template-columns: 1fr;
  }
}
</style>
