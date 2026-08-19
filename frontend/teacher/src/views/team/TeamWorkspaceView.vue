<template>
  <div class="teacher-page team-workspace">
    <header class="teacher-page__head workspace-head">
      <div class="workspace-head__main">
        <div class="workspace-head__title-row">
          <h1>{{ projectDisplayName }}</h1>
          <span v-if="team.currentStage" class="workspace-stage-pill">{{ stageLabel(team.currentStage) }}</span>
        </div>
        <p class="workspace-head__meta">
          <span v-if="team.trackName || team.track">{{ team.trackName || team.track }}</span>
          <span>{{ memberRows.length }} 名成员</span>
          <span>负责人 {{ captainName }}</span>
          <span v-if="team.description" class="workspace-head__desc">{{ team.description }}</span>
        </p>
      </div>
      <div class="teacher-page__actions">
        <button type="button" class="teacher-btn teacher-btn--secondary" @click="openDrawer('member')">加成员</button>
        <button type="button" class="teacher-btn teacher-btn--secondary" @click="openDrawer('file')">上传文件</button>
        <button type="button" class="teacher-btn teacher-btn--primary" @click="openDrawer('task')">新建任务</button>
      </div>
    </header>

    <p v-if="error" class="workspace-error">
      {{ error }}
      <button type="button" class="teacher-link text-button" @click="load">重新加载</button>
    </p>

    <nav class="workspace-tabs" aria-label="项目详情分区">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        type="button"
        :class="{ 'is-active': activeTab === tab.key }"
        @click="setTab(tab.key)"
      >
        {{ tab.label }}
      </button>
    </nav>

    <div v-if="loading" class="teacher-card workspace-loading">正在加载项目数据…</div>

    <template v-else-if="activeTab === 'overview'">
      <section class="workspace-kpi" aria-label="项目关键指标">
        <article class="workspace-kpi__card">
          <small>待处理任务</small>
          <strong class="is-accent">{{ pendingTaskCount }}</strong>
          <em>需跟进</em>
        </article>
        <article class="workspace-kpi__card">
          <small>项目成员</small>
          <strong>{{ memberRows.length }}</strong>
          <em>含指导与学生</em>
        </article>
        <article class="workspace-kpi__card">
          <small>下一场路演</small>
          <strong>{{ nextRoadshowDate }}</strong>
          <em>{{ nextRoadshowTitle }}</em>
        </article>
        <article class="workspace-kpi__card">
          <small>最近评分</small>
          <strong>{{ roadshowScore }}</strong>
          <em>{{ roadshowScore === '—' ? '暂无报告' : '路演得分' }}</em>
        </article>
      </section>

      <div class="workspace-grid">
        <section class="teacher-card workspace-panel">
          <div class="teacher-card__head">
            <h2>近期任务</h2>
            <button type="button" class="teacher-link text-button" @click="setTab('tasks')">全部 ›</button>
          </div>
          <div class="teacher-card__body">
            <div v-if="taskRows.length" class="teacher-list">
              <button
                v-for="task in taskRows.slice(0, 5)"
                :key="task.id"
                type="button"
                class="teacher-list__item is-clickable"
                @click="openTaskDetail(task)"
              >
                <div class="task-list-main">
                  <strong>{{ task.title }}</strong>
                  <small class="task-list-meta">
                    <AnimatedTeamTooltip
                      v-if="task.owners?.length"
                      :items="task.owners"
                      :total-count="task.owners.length"
                      :max-visible="3"
                      :show-count="false"
                      class="task-owner-tooltip task-owner-tooltip--compact"
                      @click.stop
                    />
                    <span v-else class="teacher-muted">待指派</span>
                    <span class="task-list-meta__sep">截止 {{ task.due }} · {{ task.source }}</span>
                  </small>
                </div>
                <span class="teacher-tag">{{ task.status }}</span>
              </button>
            </div>
            <div v-else class="workspace-empty-block">
              <p>还没有团队任务</p>
              <button type="button" class="teacher-btn teacher-btn--primary teacher-btn--sm" @click="openDrawer('task')">
                新建任务
              </button>
            </div>
          </div>
        </section>

        <section class="teacher-card workspace-panel">
          <div class="teacher-card__head">
            <h2>成员速览</h2>
            <button type="button" class="teacher-link text-button" @click="setTab('members')">管理 ›</button>
          </div>
          <div class="teacher-card__body">
            <div v-if="memberRows.length" class="member-strip">
              <div v-for="member in memberRows.slice(0, 8)" :key="member.id">
                <span>{{ member.name.slice(0, 1) }}</span>
                <strong>{{ member.name }}</strong>
                <small>{{ member.role }}</small>
              </div>
            </div>
            <div v-else class="workspace-empty-block">
              <p>暂无项目成员</p>
              <button type="button" class="teacher-btn teacher-btn--secondary teacher-btn--sm" @click="openDrawer('member')">
                添加成员
              </button>
            </div>
          </div>
        </section>

        <section class="teacher-card workspace-panel workspace-panel--wide">
          <div class="teacher-card__head">
            <h2>荣誉奖状</h2>
            <button type="button" class="teacher-link text-button" @click="openDrawer('certificate')">颁发 ›</button>
          </div>
          <div class="teacher-card__body">
            <div v-if="certificateRows.length" class="teacher-list">
              <button
                v-for="item in certificateRows.slice(0, 4)"
                :key="item.id"
                type="button"
                class="teacher-list__item is-clickable"
                @click="openCertificatePreview(item)"
              >
                <span>
                  <strong>{{ item.title }}</strong>
                  <small>{{ item.awardLevel || '荣誉' }} · {{ formatDate(item.issuedAt) }}</small>
                </span>
                <span class="teacher-tag" :class="item.status === 'ACTIVE' ? 'is-ok' : 'is-warn'">
                  {{ item.status === 'ACTIVE' ? '有效' : '已撤销' }}
                </span>
              </button>
            </div>
            <div v-else class="workspace-empty-block">
              <p>尚未颁发奖状</p>
              <button type="button" class="teacher-btn teacher-btn--secondary teacher-btn--sm" @click="openDrawer('certificate')">
                颁发奖状
              </button>
            </div>
          </div>
        </section>
      </div>
    </template>

    <section v-else-if="activeTab === 'members'" class="teacher-card">
      <div class="teacher-card__head">
        <h2>成员与岗位</h2>
        <button type="button" class="teacher-btn teacher-btn--primary teacher-btn--sm" @click="openDrawer('member')">加成员</button>
      </div>
      <div class="teacher-card__body">
        <p class="member-role-note">系统角色为全局身份。设为教师后，该成员重新登录即可获得教师端权限。</p>
        <table class="teacher-table">
          <thead><tr><th>成员</th><th>系统角色</th><th>团队角色</th><th>岗位</th><th>状态</th><th></th></tr></thead>
          <tbody>
            <tr v-for="member in memberRows" :key="member.id">
              <td>
                <div class="member-cell">
                  <span class="member-cell__avatar" aria-hidden="true">{{ memberInitial(member.name) }}</span>
                  <strong class="member-cell__name">{{ member.name }}</strong>
                </div>
              </td>
              <td>
                <select
                  v-model="member.systemRole"
                  class="inline-select system-role-select"
                  :disabled="member.roleInTeam === 'CAPTAIN' || member.savingRole"
                  @change="changeMemberSystemRole(member)"
                >
                  <option value="STUDENT">学生</option>
                  <option value="TEACHER">教师</option>
                </select>
                <small v-if="member.roleInTeam === 'CAPTAIN'" class="role-hint">队长须为学生</small>
              </td>
              <td>{{ member.teamRole }}</td>
              <td>
                <el-select
                  class="inline-position-select"
                  :model-value="member.role"
                  :aria-label="`${member.name}的岗位`"
                  filterable
                  allow-create
                  default-first-option
                  :disabled="member.roleInTeam === 'MENTOR' || member.savingPosition"
                  :loading="member.savingPosition"
                  placeholder="选择或输入岗位"
                  no-match-text="回车创建此岗位"
                  @change="changeMemberRole(member, $event)"
                >
                  <el-option v-for="role in roles" :key="role" :label="role" :value="role" />
                </el-select>
              </td>
              <td><span class="teacher-tag is-ok">正常</span></td>
              <td><button v-if="!['CAPTAIN','MENTOR'].includes(member.roleInTeam)" type="button" class="teacher-link text-button" @click="removeMember(member)">移出</button><span v-else class="protected-label">不可移出</span></td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section v-else-if="activeTab === 'tasks'" class="teacher-card">
      <div class="teacher-card__head">
        <h2>团队任务</h2>
        <button type="button" class="teacher-btn teacher-btn--primary teacher-btn--sm" @click="openDrawer('task')">
          新建任务
        </button>
      </div>
      <div class="teacher-card__body">
        <table v-if="taskRows.length" class="teacher-table teacher-table--clickable">
          <thead>
            <tr>
              <th>任务</th>
              <th>负责人</th>
              <th>截止</th>
              <th>来源</th>
              <th>状态</th>
              <th class="col-actions" aria-hidden="true"></th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="task in taskRows"
              :key="task.id"
              class="is-row-link"
              role="link"
              tabindex="0"
              :aria-label="`查看任务 ${task.title}`"
              @click="openTaskDetail(task)"
              @keydown.enter.prevent="openTaskDetail(task)"
              @keydown.space.prevent="openTaskDetail(task)"
            >
              <td>
                <strong class="task-title">{{ task.title }}</strong>
              </td>
              <td @click.stop>
                <AnimatedTeamTooltip
                  v-if="task.owners?.length"
                  :items="task.owners"
                  :total-count="task.owners.length"
                  :max-visible="3"
                  :show-count="false"
                  class="task-owner-tooltip"
                />
                <span v-else class="teacher-muted">待指派</span>
              </td>
              <td>{{ task.due }}</td>
              <td>
                <span class="teacher-tag" :class="task.source === 'AI 整改' ? 'is-info' : ''">{{ task.source }}</span>
              </td>
              <td>
                <span class="teacher-tag" :class="taskStatusClass(task.status)">{{ task.status }}</span>
              </td>
              <td class="col-actions" aria-hidden="true">
                <span class="row-chevron">›</span>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-else class="workspace-empty-block">
          <strong>还没有团队任务</strong>
          <p>发布任务后，学生端协作台会同步可见，便于跟进交付与批改。</p>
          <button type="button" class="teacher-btn teacher-btn--primary teacher-btn--sm" @click="openDrawer('task')">
            新建第一个任务
          </button>
        </div>
      </div>
    </section>

    <section v-else-if="activeTab === 'files'" class="teacher-card">
      <div class="teacher-card__head">
        <div>
          <h2>团队文件</h2>
          <p class="teacher-card__sub">项目团队共享的文档、演示稿与资料，学生端文件中心可同步查看。</p>
        </div>
        <button type="button" class="teacher-btn teacher-btn--primary teacher-btn--sm" @click="openDrawer('file')">
          上传文件
        </button>
      </div>
      <div class="teacher-card__body">
        <table v-if="fileRows.length" class="teacher-table">
          <thead>
            <tr>
              <th>名称</th>
              <th>类型</th>
              <th>状态</th>
              <th>更新</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="file in fileRows" :key="file.id">
              <td><strong class="task-title">{{ file.name }}</strong></td>
              <td>{{ file.type }}</td>
              <td><span class="teacher-tag" :class="file.reviewStatus === '已通过' ? 'is-ok' : ''">{{ file.reviewStatus }}</span></td>
              <td>{{ file.updatedAt }}</td>
              <td class="col-actions">
                <a v-if="file.url" class="teacher-link" :href="file.url" target="_blank" rel="noreferrer">打开</a>
                <span v-else class="teacher-muted">无文件</span>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-else class="workspace-empty-block">
          <strong>还没有团队文件</strong>
          <p>上传讲稿、PPT、文档等，方便全队共享与学生端同步。</p>
          <button type="button" class="teacher-btn teacher-btn--primary teacher-btn--sm" @click="openDrawer('file')">
            上传第一个文件
          </button>
        </div>
      </div>
    </section>

    <section v-else class="teacher-card">
      <div class="teacher-card__head">
        <h2>训练与路演</h2>
        <button type="button" class="teacher-btn teacher-btn--secondary teacher-btn--sm" @click="openDrawer('certificate')">颁发奖状</button>
      </div>
      <div class="teacher-card__body relation-grid relation-page">
        <router-link to="/camp"><span>训练营</span><strong>{{ trainingCampLabel }}</strong><small>日计划、批改、进度 ›</small></router-link>
        <router-link to="/camp"><span>训练营</span><strong>编排训练日</strong><small>发布今日任务 ›</small></router-link>
        <router-link to="/roadshow"><span>路演场次</span><strong>{{ nextRoadshowTitle }}</strong><small>时间、名单、录制 ›</small></router-link>
        <router-link to="/review/reports"><span>评分报告</span><strong>{{ roadshowScore === '—' ? '暂无评分' : `${roadshowScore} 分` }}</strong><small>报告与整改 ›</small></router-link>
      </div>
      <div class="teacher-card__body" style="border-top: 1px solid var(--ds-line)">
        <div class="teacher-card__head" style="padding: 0 0 12px; border: 0"><h2 style="font-size: 15px">项目荣誉</h2></div>
        <table class="teacher-table">
          <thead>
            <tr>
              <th>名称</th>
              <th>等级</th>
              <th>来源</th>
              <th>状态</th>
              <th>颁发时间</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in certificateRows" :key="item.id">
              <td>
                <strong>{{ item.title }}</strong>
                <small class="cert-meta">{{ item.certificateNo || '无编号' }} · {{ item.issuerName || '启发·竞赛大脑' }}</small>
              </td>
              <td>{{ item.awardLevel || '—' }}</td>
              <td>{{ item.sourceType === 'GENERATED' ? '系统生成' : '上传文件' }}</td>
              <td><span class="teacher-tag" :class="item.status === 'ACTIVE' ? 'is-ok' : 'is-warn'">{{ item.status === 'ACTIVE' ? '有效' : '已撤销' }}</span></td>
              <td>{{ formatDate(item.issuedAt) }}</td>
              <td class="cert-actions">
                <button type="button" class="teacher-link text-button" @click="openCertificatePreview(item)">预览</button>
                <button type="button" class="teacher-link text-button" @click="openCertificatePreview(item, true)">下载</button>
                <button v-if="item.status === 'ACTIVE'" type="button" class="teacher-link text-button" @click="revokeCertificate(item)">撤销</button>
              </td>
            </tr>
            <tr v-if="!certificateRows.length"><td colspan="6" class="workspace-empty">还没有颁发奖状</td></tr>
          </tbody>
        </table>
      </div>
    </section>

    <Teleport to="body">
    <div
      v-if="drawer"
      class="drawer-mask teacher-overlay-mask"
      role="presentation"
      @click.self="closeDrawer"
      @keydown.esc.prevent="closeDrawer"
    >
      <aside
        class="workspace-drawer"
        :class="{
          'workspace-drawer--task': drawer === 'task' || drawer === 'file' || drawer === 'task-detail',
        }"
        role="dialog"
        aria-modal="true"
        :aria-label="drawerTitle"
      >
        <header class="workspace-drawer__head">
          <h2>{{ drawerTitle }}</h2>
          <button type="button" class="teacher-btn teacher-btn--secondary teacher-btn--sm" @click="closeDrawer">
            关闭
          </button>
        </header>

      <template v-if="drawer === 'task-detail'">
        <div class="task-detail-drawer">
          <div v-if="taskDetailLoading" class="drawer-empty">正在加载任务详情…</div>
          <template v-else-if="taskDetail">
            <p class="drawer-tip">
              {{ taskDetailStatusLabel }}
              <template v-if="taskDetail.dueAt"> · 截止 {{ formatDate(taskDetail.dueAt) }}</template>
              <template v-if="taskDetailSource"> · {{ taskDetailSource }}</template>
            </p>
            <div class="task-detail-body">
              <section class="task-detail-block">
                <h3>任务说明</h3>
                <p class="task-detail-desc">
                  {{ taskDetail.description || taskDetail.content || '暂无任务说明' }}
                </p>
              </section>

              <section v-if="taskDetailOwners.length" class="task-detail-block">
                <h3>负责人</h3>
                <AnimatedTeamTooltip
                  :items="taskDetailOwners"
                  :total-count="taskDetailOwners.length"
                  :max-visible="5"
                  :show-count="true"
                />
              </section>

              <section v-if="taskDetailRequirements.length" class="task-detail-block">
                <h3>交付要求</h3>
                <ul class="task-detail-list">
                  <li v-for="req in taskDetailRequirements" :key="req.id || req.title">
                    <strong>{{ req.title || '要求' }}</strong>
                    <span v-if="req.description">{{ req.description }}</span>
                    <em v-if="req.required">必交</em>
                  </li>
                </ul>
              </section>

              <section v-if="taskDetailSubmissions.length" class="task-detail-block">
                <h3>提交情况</h3>
                <ul class="task-detail-list">
                  <li
                    v-for="sub in taskDetailSubmissions"
                    :key="sub.id || sub.submissionId || sub.createdAt"
                  >
                    <strong>{{ sub.submitterName || sub.username || '成员' }}</strong>
                    <span>
                      {{ submissionStatusLabel(sub.status) }}
                      <template v-if="sub.createdAt || sub.submittedAt">
                        · {{ formatDate(sub.createdAt || sub.submittedAt) }}
                      </template>
                    </span>
                  </li>
                </ul>
              </section>

              <section v-if="taskDetail.taskBook?.dayTitle || taskDetail.taskBook?.campName" class="task-detail-block">
                <h3>关联训练</h3>
                <p class="task-detail-desc">
                  <template v-if="taskDetail.taskBook?.campName">{{ taskDetail.taskBook.campName }}</template>
                  <template v-if="taskDetail.taskBook?.dayNo"> · 第 {{ taskDetail.taskBook.dayNo }} 天</template>
                  <template v-if="taskDetail.taskBook?.dayTitle"> · {{ taskDetail.taskBook.dayTitle }}</template>
                </p>
              </section>
            </div>
            <div class="drawer-actions">
              <router-link
                class="teacher-btn teacher-btn--secondary"
                to="/camp/review-queue"
                @click="closeDrawer"
              >
                提交与批改
              </router-link>
              <button
                v-if="hasPendingSubmission"
                type="button"
                class="teacher-btn teacher-btn--primary"
                @click="goReviewQueue"
              >
                去批改
              </button>
              <button type="button" class="teacher-btn teacher-btn--secondary" @click="closeDrawer">
                关闭
              </button>
            </div>
          </template>
          <div v-else class="drawer-empty">
            {{ taskDetailError || '任务详情加载失败' }}
          </div>
        </div>
      </template>

      <template v-else-if="drawer === 'member'">
        <p class="drawer-tip">
          从本租户可加入的学生/教师中选择。教师加入后自动成为团队指导教师；学生可指定岗位。
        </p>
        <div v-if="availableMembers.length" class="candidate-drawer">
          <div v-for="member in availableMembers" :key="member.id" class="candidate-role-row">
            <label>
              <input v-model="selectedMemberIds" type="checkbox" :value="member.id" />
              <span>
                <strong>{{ member.name }}</strong>
                <small>{{ member.studentNo || '无学号' }} · {{ member.group || systemRoleLabel(member.systemRole) }}</small>
              </span>
            </label>
            <select v-model="member.roleOverride" aria-label="成员系统角色">
              <option value="">自动（{{ systemRoleLabel(member.systemRole) }}）</option>
              <option value="STUDENT">学生</option>
              <option value="TEACHER">教师</option>
            </select>
          </div>
        </div>
        <div v-else class="drawer-empty">
          <strong>没有可加入的候选成员</strong>
          <p>当前租户下没有尚未入队的用户，或候选人列表为空。可先在成员管理中确认学生账号是否已创建。</p>
          <router-link class="teacher-btn teacher-btn--secondary teacher-btn--sm" to="/members">去成员管理</router-link>
        </div>
        <label class="drawer-field">
          <span>学生加入后的默认岗位</span>
          <select v-model="memberPosition">
            <option v-for="role in roles" :key="role" :value="role">{{ role }}</option>
          </select>
        </label>
        <button
          type="button"
          class="teacher-btn teacher-btn--primary"
          :disabled="saving || !selectedMemberIds.length"
          @click="addMembers"
        >
          {{ saving ? '处理中…' : `加入团队${selectedMemberIds.length ? `（${selectedMemberIds.length}）` : ''}` }}
        </button>
      </template>

      <template v-else-if="drawer === 'task'">
        <div class="task-drawer">
          <p class="drawer-tip">
            发布后学生端协作任务会同步可见。建议写清交付物与截止时间，方便学生执行与你批改。
          </p>

          <div class="task-drawer__body">
            <label class="drawer-field">
              <span>任务标题 <i>*</i></span>
              <input
                v-model="taskForm.title"
                maxlength="120"
                placeholder="例如：完善路演第 1 页问题定义"
                autofocus
              />
            </label>

            <label class="drawer-field">
              <span>任务说明</span>
              <textarea
                v-model="taskForm.content"
                rows="4"
                maxlength="2000"
                placeholder="说明目标、交付物（截图/文档/链接）和验收标准"
              />
            </label>

            <label class="drawer-field">
              <span>负责人</span>
              <select v-model="taskForm.ownerUserId">
                <option value="">暂不指派（全员可见）</option>
                <option v-for="member in studentMembers" :key="member.id" :value="member.id">
                  {{ member.name }}{{ member.role ? ` · ${member.role}` : '' }}
                </option>
              </select>
              <small v-if="!studentMembers.length" class="drawer-field-hint">
                项目里还没有学生成员，可先加成员再指派
              </small>
            </label>

            <div class="drawer-field">
              <span>优先级</span>
              <div class="priority-pills" role="group" aria-label="任务优先级">
                <button
                  v-for="p in taskPriorities"
                  :key="p.value"
                  type="button"
                  class="priority-pill"
                  :class="{ 'is-active': taskForm.priority === p.value }"
                  :data-level="p.value"
                  @click="taskForm.priority = p.value"
                >
                  {{ p.label }}
                </button>
              </div>
            </div>

            <label class="drawer-field">
              <span>截止日期</span>
              <div class="due-quick">
                <button
                  type="button"
                  class="due-chip"
                  :class="{ 'is-active': taskDuePreset === 'tonight' }"
                  @click="setTaskDue('tonight')"
                >
                  今晚 22:00
                </button>
                <button
                  type="button"
                  class="due-chip"
                  :class="{ 'is-active': taskDuePreset === 'tomorrow' }"
                  @click="setTaskDue('tomorrow')"
                >
                  明天 22:00
                </button>
                <button
                  type="button"
                  class="due-chip"
                  :class="{ 'is-active': taskDuePreset === '3d' }"
                  @click="setTaskDue('3d')"
                >
                  3 天后
                </button>
              </div>
              <input
                v-model="taskForm.dueAt"
                type="datetime-local"
                class="due-input"
                :class="{ 'is-empty': !taskForm.dueAt }"
                @input="taskDuePreset = ''"
              />
            </label>

            <label class="task-review-row">
              <input v-model="taskForm.reviewRequired" type="checkbox" />
              <span>
                <strong>完成后需要教师确认</strong>
                <small>勾选后，学生提交会进入待你批改</small>
              </span>
            </label>
          </div>

          <p v-if="formError" class="drawer-form-error" role="alert">{{ formError }}</p>

          <div class="drawer-actions">
            <button type="button" class="teacher-btn teacher-btn--secondary" :disabled="saving" @click="closeDrawer">
              取消
            </button>
            <button
              type="button"
              class="teacher-btn teacher-btn--primary"
              :disabled="saving || !taskForm.title.trim()"
              @click="addTask"
            >
              {{ saving ? '发布中…' : '发布任务' }}
            </button>
          </div>
        </div>
      </template>
      <template v-else-if="drawer === 'certificate'">
        <label class="drawer-field"><span>奖状名称</span><input v-model="certForm.title" placeholder="例如：优秀路演团队" /></label>
        <label class="drawer-field"><span>奖项等级</span><input v-model="certForm.awardLevel" placeholder="一等奖 / 优秀奖" /></label>
        <label class="drawer-field"><span>颁发单位</span><input v-model="certForm.issuerName" placeholder="竞赛大脑" /></label>
        <label class="drawer-field"><span>说明</span><textarea v-model="certForm.description" rows="3" placeholder="获奖理由" /></label>
        <label class="drawer-field"><span>接收对象</span>
          <select v-model="certForm.recipientMode">
            <option value="TEAM">整个团队</option>
            <option value="USER">指定学生</option>
          </select>
        </label>
        <div v-if="certForm.recipientMode === 'USER'" class="candidate-drawer">
          <label v-for="member in studentMembers" :key="member.id">
            <input v-model="certForm.recipientIds" type="checkbox" :value="member.id" />
            <span><strong>{{ member.name }}</strong><small>{{ member.teamRole }}</small></span>
          </label>
        </div>
        <label class="drawer-field"><span>生成方式</span>
          <select v-model="certForm.sourceType">
            <option value="GENERATED">系统生成 PDF</option>
            <option value="UPLOADED">上传 PDF / 图片</option>
          </select>
        </label>
        <label v-if="certForm.sourceType === 'UPLOADED'" class="drawer-field"><span>奖状文件</span><input type="file" accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg" @change="onCertFileChange" /></label>
        <button type="button" class="teacher-btn teacher-btn--primary" :disabled="saving || !certForm.title.trim()" @click="issueCertificate">{{ saving ? '颁发中…' : '确认颁发' }}</button>
      </template>
      <template v-else-if="drawer === 'file'">
        <div class="task-drawer">
          <p class="drawer-tip">
            上传到本项目的团队文件库。支持文档、演示稿、图片、音视频与压缩包（单文件 ≤ 200MB）。也可只填外链。
          </p>
          <div class="task-drawer__body">
            <label class="drawer-field">
              <span>本地文件</span>
              <input
                type="file"
                class="file-input"
                accept=".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.csv,.txt,.md,.png,.jpg,.jpeg,.gif,.webp,.mp4,.webm,.mov,.mp3,.wav,.m4a,.zip,.rar,.7z"
                @change="onTeamFileChange"
              />
              <small v-if="fileForm.file" class="drawer-field-hint">已选：{{ fileForm.file.name }}（{{ formatFileSize(fileForm.file.size) }}）</small>
              <small v-else class="drawer-field-hint">选择文件后将实际上传到服务器；不选则可仅登记外链</small>
            </label>
            <label class="drawer-field">
              <span>名称 <i v-if="!fileForm.file">*</i></span>
              <input v-model="fileForm.name" maxlength="120" placeholder="例如：路演讲稿 第2版" />
            </label>
            <label class="drawer-field">
              <span>类型</span>
              <select v-model="fileForm.type">
                <option value="DOCS">文档</option>
                <option value="PPT">演示文稿</option>
                <option value="SCRIPT">讲稿</option>
                <option value="VIDEO">视频</option>
                <option value="LINK">链接</option>
              </select>
            </label>
            <label v-if="!fileForm.file" class="drawer-field">
              <span>外链地址</span>
              <input v-model="fileForm.url" placeholder="https://… 或已有文件地址" />
            </label>
            <label class="drawer-field">
              <span>说明</span>
              <textarea v-model="fileForm.description" rows="3" maxlength="1000" placeholder="用途、版本说明（可选）" />
            </label>
          </div>
          <p v-if="formError" class="drawer-form-error" role="alert">{{ formError }}</p>
          <div class="drawer-actions">
            <button type="button" class="teacher-btn teacher-btn--secondary" :disabled="saving" @click="closeDrawer">取消</button>
            <button
              type="button"
              class="teacher-btn teacher-btn--primary"
              :disabled="saving || (!fileForm.file && !fileForm.name.trim())"
              @click="addFile"
            >
              {{ saving ? (fileForm.file ? '上传中…' : '创建中…') : (fileForm.file ? '上传文件' : '创建记录') }}
            </button>
          </div>
        </div>
      </template>
    </aside>
    </div>
    </Teleport>

    <CertificatePreview
      v-model="certificatePreviewOpen"
      :certificate="selectedCertificate"
      :recipient-label="certificateRecipientLabel"
      :auto-download="certificateAutoDownload"
    />
    <Teleport to="body">
      <p v-if="notice" class="workspace-notice" role="status" aria-live="polite">{{ notice }}</p>
    </Teleport>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { ElOption, ElSelect } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import AnimatedTeamTooltip from '../../components/dashboard/AnimatedTeamTooltip.vue'
import CertificatePreview from '../../components/CertificatePreview.vue'
import {
  addTeamMember,
  createPositionRole,
  createTeamCertificate,
  createTeamMaterial,
  uploadTeamMaterial,
  createTeamTask,
  fetchCandidateMembers,
  fetchTeamCertificates,
  fetchTeamDashboard,
  fetchTeamTask,
  removeTeamMember,
  revokeTeamCertificate,
  updateTeamMemberPosition,
  uploadTeamCertificate
} from '../../api'

const OWNER_AVATAR_COLORS = ['#e84a1c', '#2563eb', '#0f766e', '#7c3aed', '#b45309', '#db2777']

const MAX_POSITION_NAME_LENGTH = 80
const route = useRoute()
const router = useRouter()
const teamId = computed(() => Number(route.params.projectId || route.params.teamId))
const team = reactive({})
const metrics = reactive({})
const roadshow = ref(null)
const meetings = ref([])
const roleOptions = ref([])
const candidateRows = ref([])
const memberRows = ref([])
const taskRows = ref([])
const fileRows = ref([])
const certificateRows = ref([])
const certificatePreviewOpen = ref(false)
const selectedCertificate = ref(null)
const certificateAutoDownload = ref(false)
const loading = ref(true)
const saving = ref(false)
const error = ref('')
const formError = ref('')
const tabs = [
  { key: 'overview', label: '项目概览' },
  { key: 'members', label: '成员与岗位' },
  { key: 'tasks', label: '团队任务' },
  { key: 'files', label: '团队文件' },
  { key: 'relations', label: '训练与路演' },
]
const activeTab = ref(normalizeTab(route.query.tab))
watch(
  () => route.query.tab,
  (tab) => {
    activeTab.value = normalizeTab(tab)
  }
)
const trainingSchedule = ref([])
const drawer = ref('')
const notice = ref('')
const selectedMemberIds = ref([])
const memberPosition = ref('项目成员')
const taskDetail = ref(null)
const taskDetailLoading = ref(false)
const taskDetailError = ref('')
const taskPriorities = [
  { value: 'LOW', label: '低' },
  { value: 'MEDIUM', label: '中' },
  { value: 'HIGH', label: '高' },
]
const taskForm = reactive({
  title: '',
  ownerUserId: '',
  dueAt: '',
  content: '',
  priority: 'MEDIUM',
  reviewRequired: true,
})
const taskDuePreset = ref('')
const fileForm = reactive({ name: '', type: 'DOCS', url: '', description: '', file: null })
const certForm = reactive({
  title: '',
  awardLevel: '',
  issuerName: '启发·竞赛大脑',
  description: '',
  recipientMode: 'TEAM',
  recipientIds: [],
  sourceType: 'GENERATED',
  file: null
})

const roles = computed(() => {
  const names = roleOptions.value.map((item) => typeof item === 'string' ? item : item.name).filter(Boolean)
  return names.length ? names : ['项目成员']
})
const availableMembers = computed(() => candidateRows.value.filter((candidate) => !memberRows.value.some((member) => Number(member.id) === Number(candidate.id))))
const studentMembers = computed(() => memberRows.value.filter((member) => member.systemRole === 'STUDENT'))
const projectDisplayName = computed(() => team.projectName || team.name || '项目详情')
const captainName = computed(() => memberRows.value.find((member) => member.roleInTeam === 'CAPTAIN')?.name || '未设置')
const pendingTaskCount = computed(() => taskRows.value.filter((task) => !['已完成','已取消'].includes(task.status)).length)
const nextMeeting = computed(() => meetings.value.find((item) => item.startTime) || (roadshow.value?.startTime ? roadshow.value : null))
const nextRoadshowDate = computed(() => formatDate(nextMeeting.value?.startTime, true))
const nextRoadshowTitle = computed(() => nextMeeting.value?.meetingTitle || nextMeeting.value?.title || '暂无路演排期')
const roadshowScore = computed(() => {
  const raw = roadshow.value?.aiScore ?? metrics.roadshowScore
  return raw === null || raw === undefined ? '—' : Number(raw).toFixed(Number(raw) % 1 ? 1 : 0)
})
const trainingCampLabel = computed(() => {
  const first = trainingSchedule.value?.[0]
  if (first?.campName) return first.campName
  if (first?.name) return first.name
  return '查看训练安排'
})
const drawerTitle = computed(() => {
  if (drawer.value === 'task-detail') {
    return taskDetail.value?.title || '任务详情'
  }
  return (
    {
      member: '添加成员',
      task: '新建团队任务',
      file: '上传团队文件',
      certificate: '颁发奖状',
    }[drawer.value] || '操作'
  )
})

const taskDetailOwners = computed(() => mapTaskOwners(taskDetail.value || {}))
const taskDetailSource = computed(() => sourceLabel(taskDetail.value || {}))
const taskDetailStatusLabel = computed(() => taskStatus(taskDetail.value?.status))
const taskDetailRequirements = computed(() => {
  const list = taskDetail.value?.requirements
  return Array.isArray(list) ? list : []
})
const taskDetailSubmissions = computed(() => {
  const detail = taskDetail.value || {}
  if (Array.isArray(detail.submissions) && detail.submissions.length) return detail.submissions
  if (detail.latestSubmission) return [detail.latestSubmission]
  return []
})
const hasPendingSubmission = computed(() => {
  const s = String(taskDetail.value?.status || '').toUpperCase()
  if (['REVIEWING', 'PENDING_REVIEW'].includes(s)) return true
  return taskDetailSubmissions.value.some((row) =>
    ['PENDING_REVIEW', 'REVIEWING'].includes(String(row.status || '').toUpperCase())
  )
})

function normalizeTab(tab) {
  const raw = String(tab || 'overview')
  if (raw === 'certificates') return 'relations'
  if (['overview', 'members', 'tasks', 'files', 'relations'].includes(raw)) return raw
  return 'overview'
}

function memberInitial(name) {
  const s = String(name || '').trim()
  return s ? s.slice(0, 1) : '?'
}

function submissionStatusLabel(status) {
  const s = String(status || '').toUpperCase()
  return (
    {
      PENDING_REVIEW: '待审核',
      REVIEWING: '审核中',
      APPROVED: '已通过',
      CHANGES_REQUESTED: '需修改',
      REJECTED: '未通过',
      DRAFT: '草稿',
    }[s] || status || '未知'
  )
}

async function openTaskDetail(task) {
  const id = task?.id
  if (!id || !teamId.value) return
  drawer.value = 'task-detail'
  taskDetail.value = null
  taskDetailError.value = ''
  taskDetailLoading.value = true
  try {
    const detail = await fetchTeamTask(teamId.value, id)
    const rawTask = detail?.task || detail || {}
    const book = detail?.taskBook || {}
    taskDetail.value = {
      ...rawTask,
      title: rawTask.title || book.title || task.title,
      description:
        rawTask.description ||
        book.summary ||
        stripHtml(book.contentHtml) ||
        task.description ||
        '',
      requirements: book.requirements || rawTask.requirements || [],
      taskBook: book,
      status: rawTask.status || task.rawStatus,
      dueAt: rawTask.dueAt || task.dueAt,
      assignees: rawTask.assignees,
      ownerName: rawTask.ownerName || task.owner,
      ownerUserId: rawTask.ownerUserId,
    }
  } catch (err) {
    // 接口失败时至少展示列表行上已有信息
    taskDetail.value = {
      id,
      title: task.title,
      description: task.description || '',
      status: task.rawStatus || task.status,
      dueAt: task.dueAt,
      assignees: (task.owners || []).map((o) => ({
        userId: o.id,
        username: o.name,
        positionName: o.designation,
      })),
      ownerName: task.owner,
      requirements: [],
    }
    taskDetailError.value = err?.response?.data?.message || err?.message || '任务详情加载失败'
  } finally {
    taskDetailLoading.value = false
  }
}

function stripHtml(html) {
  if (!html) return ''
  return String(html)
    .replace(/<[^>]+>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

function goReviewQueue() {
  closeDrawer()
  router.push('/camp/review-queue')
}

/** 任务负责人 → AnimatedTeamTooltip items（头像 + 悬停气泡） */
function mapTaskOwners(task) {
  let list = Array.isArray(task?.assignees) ? task.assignees.filter(Boolean) : []
  if (!list.length && (task?.ownerUserId || task?.ownerName)) {
    list = [{ userId: task.ownerUserId, username: task.ownerName || '负责人' }]
  }
  return list.map((person, index) => {
    const name = String(person.username || person.name || '成员').trim() || '成员'
    return {
      id: person.userId ?? `${name}-${index}`,
      name,
      designation: person.positionName || person.role || '负责人',
      initial: name.slice(0, 1),
      color: OWNER_AVATAR_COLORS[index % OWNER_AVATAR_COLORS.length],
    }
  })
}
function stageLabel(value) { return ({ PREPARATION:'准备阶段', TRAINING:'集训阶段', ROADSHOW:'路演阶段', REVIEW:'复盘阶段', COMPLETED:'已完成' })[value] || value || '未设置阶段' }
function taskStatus(value) { return ({ TODO:'待开始', IN_PROGRESS:'进行中', REVIEWING:'待审核', PENDING_REVIEW:'待审核', CHANGES_REQUESTED:'需修改', DONE:'已完成', CANCELLED:'已取消' })[value] || value || '未知' }
function taskStatusClass(label) {
  if (label === '已完成') return 'is-ok'
  if (label === '待审核' || label === '需修改') return 'is-warn'
  if (label === '进行中') return 'is-info'
  return ''
}
function sourceLabel(task) { return task.taskType === 'AI_REMEDIATION' || task.stageKey === 'AI_REMEDIATION' ? 'AI 整改' : task.taskTypeLabel || '老师发布' }
function materialStatus(value) { return ({ APPROVED:'已通过', PENDING_REVIEW:'待审核', CHANGES_REQUESTED:'需修改', REJECTED:'未通过', DRAFT:'草稿' })[value] || value || '未知' }
function formatDate(value, short = false) { if (!value) return '—'; const date = new Date(value); if (Number.isNaN(date.getTime())) return String(value); return date.toLocaleString('zh-CN', short ? { month:'numeric', day:'numeric' } : { month:'numeric', day:'numeric', hour:'2-digit', minute:'2-digit' }) }

function mapDashboard(data) {
  Object.keys(team).forEach((key) => delete team[key])
  Object.assign(team, data.team || {})
  Object.keys(metrics).forEach((key) => delete metrics[key])
  Object.assign(metrics, data.metrics || {})
  roadshow.value = data.roadshow || null
  meetings.value = Array.isArray(data.roadshowMeetings) ? data.roadshowMeetings : []
  trainingSchedule.value = Array.isArray(data.trainingSchedule) ? data.trainingSchedule : []
  roleOptions.value = Array.isArray(data.positionRoles) ? data.positionRoles : []
  memberRows.value = (data.members || []).map((member) => ({
    id: member.userId,
    name: member.username || `用户 ${member.userId}`,
    studentNo: member.username || '—',
    systemRole: member.systemRole,
    savedSystemRole: member.systemRole,
    savingRole: false,
    savedRole: member.positionName || '项目成员',
    savingPosition: false,
    roleInTeam: member.roleInTeam,
    teamRole: ({ CAPTAIN:'队长', MENTOR:'指导教师', MEMBER:'成员' })[String(member.roleInTeam || '').toUpperCase()] || '成员',
    role: member.positionName || '项目成员',
  }))
  taskRows.value = (data.tasks || []).map((task) => {
    const owners = mapTaskOwners(task)
    return {
      id: task.id,
      title: task.title,
      description: task.description || '',
      owner: owners.map((o) => o.name).join('、') || '待指派',
      owners,
      due: formatDate(task.dueAt),
      dueAt: task.dueAt,
      source: sourceLabel(task),
      status: taskStatus(task.status),
      rawStatus: task.status,
    }
  })
  fileRows.value = (data.materials || []).map((file) => ({
    id: file.id,
    name: file.name,
    type: materialTypeZh(file.materialType || 'DOCS'),
    reviewStatus: materialStatus(file.reviewStatus),
    updatedAt: formatDate(file.updatedAt),
    url: file.fileUrl,
  }))
}

function materialTypeZh(value) {
  return ({ DOCS: '文档', DOC: '文档', PPT: '演示文稿', SCRIPT: '讲稿', VIDEO: '视频', LINK: '链接', AUDIO: '音频', IMAGE: '图片' })[String(value || '').toUpperCase()] || value || '文件'
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [dashboard, candidates, certificates] = await Promise.all([
      fetchTeamDashboard(teamId.value),
      fetchCandidateMembers(),
      fetchTeamCertificates(teamId.value).catch(() => [])
    ])
    mapDashboard(dashboard || {})
    candidateRows.value = (candidates || []).map((member) => ({
      id: member.id,
      name: member.username || `用户 ${member.id}`,
      studentNo: member.email || member.username || '—',
      group: member.userGroup || member.role || '未分组',
      systemRole: String(member.role || 'STUDENT').toUpperCase() === 'TEACHER' ? 'TEACHER' : 'STUDENT',
      roleOverride: ''
    }))
    certificateRows.value = Array.isArray(certificates) ? certificates : []
    if (!roles.value.includes(memberPosition.value)) memberPosition.value = roles.value[0]
  } catch (err) {
    error.value = err?.response?.data?.message || err?.message || '团队数据加载失败'
  } finally { loading.value = false }
}
function setTab(tab) { activeTab.value = tab; router.replace({ query: tab === 'overview' ? {} : { tab } }) }
function systemRoleLabel(value) {
  const key = String(value || '').toUpperCase()
  return ({
    TEACHER: '教师',
    STUDENT: '学生',
    ADMIN: '平台管理员',
    SCHOOL_ADMIN: '校级管理员',
    REVIEWER: '评委',
    EXPERT: '专家',
  })[key] || (key ? key : '学生')
}
function selectedRoleFor(candidate) { return candidate?.roleOverride || candidate?.systemRole || 'STUDENT' }
function formatLocalDateTime(date) {
  const d = new Date(date)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function setTaskDue(preset) {
  const d = new Date()
  if (preset === 'tonight') {
    d.setHours(22, 0, 0, 0)
    if (d.getTime() < Date.now()) d.setDate(d.getDate() + 1)
  } else if (preset === 'tomorrow') {
    d.setDate(d.getDate() + 1)
    d.setHours(22, 0, 0, 0)
  } else if (preset === '3d') {
    d.setDate(d.getDate() + 3)
    d.setHours(22, 0, 0, 0)
  }
  taskForm.dueAt = formatLocalDateTime(d)
  taskDuePreset.value = preset
}

function resetTaskForm() {
  taskForm.title = ''
  taskForm.content = ''
  taskForm.ownerUserId = ''
  taskForm.dueAt = ''
  taskForm.priority = 'MEDIUM'
  taskForm.reviewRequired = true
  taskDuePreset.value = ''
}

function lockBodyScroll(locked) {
  if (typeof document === 'undefined') return
  document.body.style.overflow = locked ? 'hidden' : ''
}

function resetFileForm() {
  fileForm.name = ''
  fileForm.type = 'DOCS'
  fileForm.url = ''
  fileForm.description = ''
  fileForm.file = null
}

function onTeamFileChange(event) {
  const file = event.target.files?.[0] || null
  fileForm.file = file
  if (file && !fileForm.name.trim()) {
    fileForm.name = file.name.replace(/\.[^.]+$/, '') || file.name
  }
  if (file) {
    const ext = String(file.name.split('.').pop() || '').toLowerCase()
    if (['ppt', 'pptx'].includes(ext)) fileForm.type = 'PPT'
    else if (['mp4', 'webm', 'mov'].includes(ext)) fileForm.type = 'VIDEO'
    else if (['doc', 'docx', 'pdf', 'txt', 'md'].includes(ext) && /讲稿|script/i.test(file.name)) fileForm.type = 'SCRIPT'
    else fileForm.type = 'DOCS'
  }
}

function formatFileSize(bytes) {
  const n = Number(bytes) || 0
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / (1024 * 1024)).toFixed(1)} MB`
}

function openDrawer(type) {
  drawer.value = type
  formError.value = ''
  if (type === 'task') {
    resetTaskForm()
  }
  if (type === 'file') {
    resetFileForm()
  }
  if (type === 'certificate') {
    certForm.title = ''
    certForm.awardLevel = ''
    certForm.issuerName = '启发·竞赛大脑'
    certForm.description = ''
    certForm.recipientMode = 'TEAM'
    certForm.recipientIds = []
    certForm.sourceType = 'GENERATED'
    certForm.file = null
  }
}
function closeDrawer() {
  drawer.value = ''
  selectedMemberIds.value = []
  formError.value = ''
  taskDetail.value = null
  taskDetailError.value = ''
  taskDetailLoading.value = false
  resetTaskForm()
}

watch(drawer, (value) => {
  lockBodyScroll(!!value)
})
onUnmounted(() => {
  lockBodyScroll(false)
})
function onCertFileChange(event) {
  certForm.file = event.target.files?.[0] || null
}
async function issueCertificate() {
  if (!certForm.title.trim()) return
  saving.value = true
  error.value = ''
  try {
    const recipientType = certForm.recipientMode
    const recipientIds = recipientType === 'TEAM' ? [teamId.value] : certForm.recipientIds
    if (!recipientIds.length) throw new Error(recipientType === 'TEAM' ? '团队不存在' : '请选择获奖学生')
    if (certForm.sourceType === 'UPLOADED') {
      if (!certForm.file) throw new Error('请上传奖状文件')
      const form = new FormData()
      form.append('file', certForm.file)
      form.append('title', certForm.title.trim())
      form.append('recipientType', recipientType)
      form.append('recipientIds', recipientIds.join(','))
      form.append('description', certForm.description || '')
      form.append('awardLevel', certForm.awardLevel || '')
      form.append('issuerName', certForm.issuerName || '竞赛大脑')
      await uploadTeamCertificate(form)
    } else {
      await createTeamCertificate({
        title: certForm.title.trim(),
        description: certForm.description || '',
        awardLevel: certForm.awardLevel || '',
        issuerName: certForm.issuerName || '竞赛大脑',
        recipientType,
        recipientIds,
        sourceType: 'GENERATED'
      })
    }
    closeDrawer()
    await load()
    flash('奖状已颁发，学生端“我的奖状”可查看')
  } catch (err) {
    error.value = err?.response?.data?.message || err?.message || '奖状颁发失败'
  } finally {
    saving.value = false
  }
}
async function revokeCertificate(item) {
  if (!window.confirm(`确认撤销奖状「${item.title}」吗？`)) return
  try {
    await revokeTeamCertificate(item.id)
    await load()
    flash('奖状已撤销')
  } catch (err) {
    error.value = err?.response?.data?.message || err?.message || '撤销失败'
  }
}

const certificateRecipientLabel = computed(() => {
  const cert = selectedCertificate.value
  if (!cert) return projectDisplayName.value || '团队'
  if (String(cert.certificateType || '').toUpperCase() === 'TEAM') {
    return projectDisplayName.value || team.name || '本项目团队'
  }
  return '获奖同学'
})

function openCertificatePreview(item, autoDownload = false) {
  if (!item) return
  selectedCertificate.value = item
  certificateAutoDownload.value = !!autoDownload
  certificatePreviewOpen.value = true
}

watch(certificatePreviewOpen, (open) => {
  if (!open) {
    selectedCertificate.value = null
    certificateAutoDownload.value = false
  }
})
function flash(text) { notice.value = text; setTimeout(() => { notice.value = '' }, 2200) }
async function addMembers() {
  saving.value = true
  try {
    let addedTeacher = false
    for (const userId of selectedMemberIds.value) {
      const candidate = candidateRows.value.find((item) => Number(item.id) === Number(userId))
      if (!candidate) continue
      const systemRole = selectedRoleFor(candidate)
      addedTeacher ||= systemRole === 'TEACHER'
      await addTeamMember(teamId.value, {
        userId,
        systemRole: selectedRoleFor(candidate),
        positionName: systemRole === 'TEACHER' ? '指导教师' : memberPosition.value
      })
    }
    closeDrawer()
    await load()
    flash(addedTeacher ? '成员已加入，教师成员重新登录后教师权限生效' : '成员已加入，学生端团队数据已同步')
  } catch (err) {
    error.value = err?.response?.data?.message || err?.message || '添加成员失败'
  } finally {
    saving.value = false
  }
}
async function removeMember(member) { if (!window.confirm(`确定将 ${member.name} 移出团队吗？`)) return; try { await removeTeamMember(teamId.value, member.id); await load(); flash(`${member.name} 已移出团队`) } catch (err) { error.value = err?.response?.data?.message || err?.message || '移出成员失败' } }
function normalizePositionName(value) {
  return String(value ?? '').replace(/[\r\n\t]+/g, ' ').trim()
}
async function changeMemberRole(member, value) {
  const previousRole = member.savedRole || member.role || '项目成员'
  const nextRole = normalizePositionName(value)
  if (!nextRole) {
    member.role = previousRole
    error.value = '岗位名称不能为空'
    return
  }
  if (nextRole.length > MAX_POSITION_NAME_LENGTH) {
    member.role = previousRole
    error.value = `岗位名称最多 ${MAX_POSITION_NAME_LENGTH} 个字符`
    return
  }
  if (nextRole === previousRole) return

  member.role = nextRole
  member.savingPosition = true
  error.value = ''
  try {
    if (!roles.value.includes(nextRole)) {
      const result = await createPositionRole({ name: nextRole })
      const savedRole = normalizePositionName(result?.name || result?.positionName || nextRole)
      member.role = savedRole
      if (!roles.value.includes(savedRole)) {
        roleOptions.value = [...roleOptions.value, { ...result, name: savedRole }]
      }
    }
    const updated = await updateTeamMemberPosition(teamId.value, member.id, { positionName: member.role })
    member.role = normalizePositionName(updated?.positionName || member.role)
    member.savedRole = member.role
    flash(`${member.name} 的岗位已更新为“${member.role}”`)
  } catch (err) {
    member.role = previousRole
    error.value = err?.response?.data?.message || err?.message || '岗位更新失败'
    await load()
  } finally {
    member.savingPosition = false
  }
}
async function changeMemberSystemRole(member) {
  const nextRole = member.systemRole
  const previousRole = member.savedSystemRole
  const roleText = systemRoleLabel(nextRole)
  if (!window.confirm(`确定将 ${member.name} 的全局身份设置为${roleText}吗？该设置会影响整个平台权限。`)) {
    member.systemRole = previousRole
    return
  }
  member.savingRole = true
  try {
    await updateTeamMemberPosition(teamId.value, member.id, { systemRole: nextRole })
    await load()
    flash(nextRole === 'TEACHER'
      ? `${member.name} 已设为教师，重新登录后教师权限生效`
      : `${member.name} 已设为学生，重新登录后身份权限生效`)
  } catch (err) {
    error.value = err?.response?.data?.message || err?.message || '成员身份更新失败'
    await load()
  } finally {
    member.savingRole = false
  }
}
async function addTask() {
  if (!taskForm.title.trim() || saving.value) return
  saving.value = true
  formError.value = ''
  try {
    const ownerId = taskForm.ownerUserId ? Number(taskForm.ownerUserId) : null
    const dueAt = taskForm.dueAt
      ? (taskForm.dueAt.length === 16 ? `${taskForm.dueAt}:00` : taskForm.dueAt)
      : null
    await createTeamTask(teamId.value, {
      title: taskForm.title.trim(),
      description: taskForm.content.trim() || null,
      ownerUserId: ownerId,
      assigneeUserIds: ownerId ? [ownerId] : [],
      dueAt,
      stageKey: 'COLLABORATION',
      sourceType: 'TEACHER_ASSIGNMENT',
      priority: taskForm.priority || 'MEDIUM',
      status: 'TODO',
      reviewRequired: !!taskForm.reviewRequired,
    })
    closeDrawer()
    await load()
    flash('任务已发布，学生端协作任务已同步')
  } catch (err) {
    formError.value = err?.response?.data?.message || err?.message || '任务发布失败'
  } finally {
    saving.value = false
  }
}
async function addFile() {
  if (saving.value) return
  const hasFile = Boolean(fileForm.file)
  const name = fileForm.name.trim() || (fileForm.file?.name || '')
  if (!hasFile && !name) return
  saving.value = true
  formError.value = ''
  try {
    if (hasFile) {
      await uploadTeamMaterial(teamId.value, {
        file: fileForm.file,
        name: name || undefined,
        materialType: fileForm.type,
        description: fileForm.description.trim() || undefined,
      })
      flash('文件已上传，团队与学生端可同步查看')
    } else {
      if (!fileForm.url.trim() && fileForm.type === 'LINK') {
        throw new Error('链接类型请填写外链地址')
      }
      await createTeamMaterial(teamId.value, {
        name,
        materialType: fileForm.type,
        fileUrl: fileForm.url.trim() || null,
        description: fileForm.description.trim(),
      })
      flash('资源记录已创建')
    }
    resetFileForm()
    closeDrawer()
    await load()
  } catch (err) {
    formError.value = err?.response?.data?.message || err?.message || '上传失败'
  } finally {
    saving.value = false
  }
}
onMounted(load)
</script>

<style scoped>
.workspace-head {
  align-items: flex-start;
  margin-bottom: 14px;
}
.workspace-head__title-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}
.workspace-head__title-row h1 {
  margin: 0;
}
.workspace-stage-pill {
  min-height: 26px;
  padding: 0 10px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  background: var(--ds-orange-wash);
  color: var(--ds-orange-deep);
  font-size: 12px;
  font-weight: 800;
}
.workspace-head__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 14px;
  margin: 8px 0 0 !important;
  max-width: none !important;
}
.workspace-head__meta > span {
  position: relative;
  color: var(--ds-muted);
  font-size: 13px;
}
.workspace-head__meta > span:not(:last-child)::after {
  content: '';
  position: absolute;
  right: -8px;
  top: 50%;
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: #c5c9d1;
  transform: translateY(-50%);
}
.workspace-head__desc {
  flex: 1 1 100%;
  color: var(--ds-faint) !important;
}

.workspace-tabs {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 16px;
  padding: 4px;
  border: 1px solid var(--ds-line, #e4e4e7);
  border-radius: 12px;
  background: #f4f4f5;
  width: fit-content;
  max-width: 100%;
}
.workspace-tabs button {
  min-height: 32px;
  padding: 0 14px;
  border: 0;
  border-radius: 9px;
  color: var(--ds-muted);
  background: transparent;
  font: 700 13px var(--ds-font-sans);
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease, box-shadow 0.15s ease;
}
.workspace-tabs button:hover {
  color: var(--ds-ink-2);
}
.workspace-tabs button.is-active {
  color: var(--ds-ink);
  background: #fff;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
}

.workspace-kpi {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}
.workspace-kpi__card {
  padding: 16px;
  border-radius: var(--ds-card-radius, 16px);
  border: 1px solid var(--ds-card-border, #e4e4e7);
  background: var(--ds-card-bg, #fff);
  box-shadow: var(--ds-card-shadow);
}
.workspace-kpi__card small {
  display: block;
  color: var(--ds-muted);
  font-size: 12px;
  font-weight: 700;
}
.workspace-kpi__card strong {
  display: block;
  margin-top: 8px;
  font-size: 24px;
  font-family: var(--ds-font-num);
  letter-spacing: -0.03em;
  line-height: 1;
}
.workspace-kpi__card strong.is-accent {
  color: var(--ds-orange);
}
.workspace-kpi__card em {
  display: block;
  margin-top: 8px;
  font-style: normal;
  color: var(--ds-faint);
  font-size: 11px;
}

.workspace-grid {
  display: grid;
  grid-template-columns: 1.15fr 0.85fr;
  gap: 14px;
}
.workspace-panel--wide {
  grid-column: 1 / -1;
}
.workspace-empty-block {
  padding: 28px 16px;
  text-align: center;
  display: grid;
  gap: 12px;
  justify-items: center;
}
.workspace-empty-block p {
  margin: 0;
  color: var(--ds-muted);
  font-size: 13px;
}

.text-button {
  border: 0;
  background: none;
  cursor: pointer;
  font: inherit;
}
.workspace-loading {
  padding: 40px;
  text-align: center;
  color: var(--ds-muted);
}
.workspace-empty {
  padding: 18px;
  text-align: center;
  color: var(--ds-muted);
  font-size: 12px;
}
.workspace-error {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin: 0 0 12px;
  padding: 10px 14px;
  border-radius: 10px;
  color: #a33a24;
  background: #fff0ec;
  font-size: 12px;
  font-weight: 700;
}

.teacher-list__item.is-clickable {
  width: 100%;
  border: 0;
  background: transparent;
  text-align: left;
  cursor: pointer;
  font: inherit;
  color: inherit;
  border-radius: 12px;
  transition: background 0.12s ease;
}
.teacher-list__item.is-clickable:hover {
  background: rgba(15, 23, 42, 0.035);
}
.teacher-table--clickable tbody tr.is-row-link {
  cursor: pointer;
}
.teacher-table--clickable tbody tr.is-row-link:hover td {
  background: rgba(15, 23, 42, 0.035);
}
.teacher-table--clickable tbody tr.is-row-link:focus-visible {
  outline: 2px solid var(--ds-orange, #e84a1c);
  outline-offset: -2px;
}
.row-chevron {
  color: var(--ds-faint, #a1a1aa);
  font-size: 18px;
  font-weight: 500;
}
.teacher-table--clickable tbody tr.is-row-link:hover .row-chevron {
  color: var(--ds-orange-deep, #c2410c);
}
.col-actions {
  width: 36px;
  text-align: right;
}

.task-detail-drawer {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}
.task-detail-body {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 8px 20px 12px;
  display: grid;
  gap: 18px;
  align-content: start;
}
.task-detail-block h3 {
  margin: 0 0 8px;
  font-size: 13px;
  font-weight: 750;
  color: var(--ds-ink);
}
.task-detail-desc {
  margin: 0;
  color: var(--ds-ink-2);
  font-size: 13px;
  line-height: 1.65;
  white-space: pre-wrap;
}
.task-detail-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 10px;
}
.task-detail-list li {
  display: grid;
  gap: 4px;
  padding: 10px 12px;
  border: 1px solid var(--ds-line, #e4e4e7);
  border-radius: 12px;
  background: #fafafa;
}
.task-detail-list strong {
  font-size: 13px;
  font-weight: 750;
  color: var(--ds-ink);
}
.task-detail-list span {
  font-size: 12px;
  color: var(--ds-muted);
  line-height: 1.5;
}
.task-detail-list em {
  font-style: normal;
  font-size: 11px;
  font-weight: 750;
  color: var(--ds-orange-deep);
}

.task-owner-tooltip {
  padding: 2px 0;
  min-height: 34px;
}
.task-owner-tooltip :deep(.animated-team-tooltip__avatar) {
  width: 28px;
  height: 28px;
  font-size: 11px;
}
.task-owner-tooltip--compact {
  min-height: 28px;
  padding: 0;
}
.task-owner-tooltip--compact :deep(.animated-team-tooltip__avatar) {
  width: 24px;
  height: 24px;
  font-size: 10px;
}
.task-list-main {
  min-width: 0;
  display: grid;
  gap: 6px;
}
.task-list-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 10px;
}
.task-list-meta__sep {
  color: var(--ds-muted);
  font-size: 12px;
  font-weight: 600;
}

.member-cell {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.member-cell__avatar {
  width: 32px;
  height: 32px;
  flex: none;
  border-radius: 50%;
  display: grid;
  place-items: center;
  color: var(--ds-orange-deep);
  background: var(--ds-orange-soft, var(--ds-orange-wash));
  font-size: 13px;
  font-weight: 800;
  line-height: 1;
}
.member-cell__name {
  font-size: 13px;
  font-weight: 750;
  color: var(--ds-ink);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.member-strip {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(72px, 1fr));
  gap: 12px;
}
.member-strip > div {
  text-align: center;
}
.member-strip span {
  width: 42px;
  height: 42px;
  margin: 0 auto 8px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  color: var(--ds-orange-deep);
  background: var(--ds-orange-soft, var(--ds-orange-wash));
  font-weight: 800;
  font-size: 14px;
}
.member-strip strong,
.member-strip small {
  display: block;
}
.member-strip strong {
  font-size: 12px;
}
.member-strip small {
  margin-top: 3px;
  color: var(--ds-muted);
  font-size: 10px;
}

.relation-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}
.relation-grid a {
  padding: 16px;
  border: 1px solid var(--ds-card-border, #e4e4e7);
  border-radius: var(--ds-card-radius, 16px);
  color: inherit;
  text-decoration: none;
  background: #fafafa;
  transition: border-color 0.15s ease, background 0.15s ease, box-shadow 0.15s ease;
}
.relation-grid a:hover {
  border-color: var(--ds-card-border-hover, #d4d4d8);
  background: #fff;
  box-shadow: var(--ds-card-shadow-hover);
}
.relation-grid span,
.relation-grid strong,
.relation-grid small {
  display: block;
}
.relation-grid span {
  color: var(--ds-muted);
  font-size: 11px;
  font-weight: 700;
}
.relation-grid strong {
  margin-top: 8px;
  font-size: 15px;
  line-height: 1.35;
}
.relation-grid small {
  margin-top: 8px;
  color: var(--ds-orange);
  font-size: 12px;
  font-weight: 700;
}
.relation-page {
  padding: 20px;
}

.inline-select {
  height: 34px;
  max-width: 170px;
  border: 1px solid var(--ds-input-border, #d4d4d8);
  border-radius: 10px;
  background: #fff;
  font-size: 12px;
  color: var(--ds-ink);
}
.inline-position-select {
  width: 176px;
}
.inline-position-select :deep(.el-select__wrapper) {
  min-height: 34px;
  border-radius: 10px;
  background: #fff;
  box-shadow: 0 0 0 1px var(--ds-input-border, #d4d4d8) inset;
  font-size: 12px;
}
.inline-position-select :deep(.el-select__wrapper.is-focused) {
  box-shadow: var(--ds-input-focus-ring), 0 0 0 1px var(--ds-orange-700) inset;
}
.system-role-select {
  min-width: 88px;
}
.role-hint {
  display: block;
  margin-top: 4px;
  color: var(--ds-muted);
  font-size: 10px;
}
.member-role-note {
  margin: 0 0 14px;
  padding: 10px 12px;
  border-left: 3px solid var(--ds-orange);
  color: var(--ds-muted);
  background: var(--ds-surface-soft);
  font-size: 12px;
}
.protected-label {
  color: var(--ds-muted);
  font-size: 11px;
}

.drawer-mask {
  display: grid;
  justify-content: end;
}
.workspace-drawer {
  box-sizing: border-box;
  width: min(440px, 100vw);
  height: 100%;
  max-height: 100vh;
  max-height: 100dvh;
  padding: 20px 20px 24px;
  display: grid;
  align-content: start;
  gap: 14px;
  background: #fff;
  border-left: 1px solid var(--ds-line, #e4e4e7);
  box-shadow: -12px 0 40px rgba(15, 23, 42, 0.12);
  overflow: auto;
}
.workspace-drawer--task {
  display: flex;
  flex-direction: column;
  gap: 0;
  padding: 0;
  overflow: hidden;
}
.workspace-drawer__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-shrink: 0;
}
.workspace-drawer--task .workspace-drawer__head {
  padding: 18px 20px 14px;
  border-bottom: 1px solid var(--ds-line);
}
.workspace-drawer h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 800;
  color: var(--ds-ink);
  letter-spacing: -0.01em;
}
.candidate-drawer {
  display: grid;
  gap: 8px;
  max-height: 46vh;
  overflow: auto;
}
.candidate-drawer label {
  min-height: 52px;
  padding: 8px 10px;
  display: grid;
  grid-template-columns: 22px 1fr;
  gap: 10px;
  align-items: center;
}
.candidate-drawer strong,
.candidate-drawer small {
  display: block;
}
.candidate-drawer strong {
  font-size: 13px;
}
.candidate-drawer small {
  margin-top: 3px;
  color: var(--ds-muted);
  font-size: 11px;
}
.candidate-role-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 140px;
  align-items: center;
  border: 1px solid var(--ds-line);
  border-radius: 10px;
  overflow: hidden;
  background: #fafafa;
}
.candidate-role-row > select {
  height: 34px;
  margin-right: 8px;
  border: 1px solid var(--ds-line-strong);
  border-radius: 6px;
  background: #fff;
  font-size: 11px;
}
.drawer-empty {
  padding: 28px 16px;
  border: 1px dashed var(--ds-line-strong);
  border-radius: 14px;
  text-align: center;
  display: grid;
  gap: 10px;
  justify-items: center;
  background: #fafafa;
}
.drawer-empty strong {
  font-size: 14px;
}
.drawer-empty p {
  margin: 0;
  color: var(--ds-muted);
  font-size: 12px;
  line-height: 1.55;
  max-width: 280px;
}

/* ---- 表单字段 ---- */
.drawer-field {
  display: grid;
  gap: 8px;
  min-width: 0;
  color: var(--ds-muted);
  font-size: 12px;
  font-weight: 700;
}
.drawer-field > span {
  line-height: 1.2;
}
.drawer-field i {
  font-style: normal;
  color: #d14343;
  font-weight: 800;
}
.drawer-field input:not([type='checkbox']):not([type='radio']),
.drawer-field select,
.drawer-field textarea {
  box-sizing: border-box;
  width: 100%;
  min-width: 0;
  border: 1px solid var(--ds-line-strong, var(--ds-input-border));
  border-radius: var(--ds-input-radius, 12px);
  padding: 0 12px;
  background: #fff;
  color: var(--ds-ink);
  font: 500 13px/1.45 var(--ds-font-sans);
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
.drawer-field input:not([type='checkbox']):not([type='radio']),
.drawer-field select {
  height: 40px;
}
.drawer-field textarea {
  min-height: 96px;
  padding: 10px 12px;
  resize: vertical;
  line-height: 1.55;
  border-radius: var(--ds-textarea-radius, 12px);
}
.drawer-field input:not([type='checkbox']):not([type='radio']):focus,
.drawer-field select:focus,
.drawer-field textarea:focus {
  outline: none;
  border-color: var(--ds-orange);
  box-shadow: 0 0 0 3px rgba(232, 74, 28, 0.12);
}
.drawer-field-hint {
  margin: 0;
  color: var(--ds-muted);
  font-size: 11px;
  font-weight: 500;
  line-height: 1.45;
}

/* ---- 新建任务抽屉 ---- */
.task-drawer {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}
.task-drawer .drawer-tip {
  margin: 14px 20px 0;
  flex-shrink: 0;
}
.task-drawer__body {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 16px 20px 8px;
  display: grid;
  gap: 16px;
  align-content: start;
}
.priority-pills {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}
.priority-pill {
  box-sizing: border-box;
  height: 40px;
  padding: 0 10px;
  border: 1px solid var(--ds-line-strong);
  border-radius: 10px;
  background: #fff;
  color: var(--ds-ink-2);
  font: 700 13px var(--ds-font-sans);
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s, color 0.15s, box-shadow 0.15s;
}
.priority-pill:hover {
  border-color: rgba(232, 74, 28, 0.45);
  color: var(--ds-orange-deep);
}
.priority-pill.is-active {
  border-color: var(--ds-orange);
  background: var(--ds-orange-wash);
  color: var(--ds-orange-deep);
  box-shadow: inset 0 0 0 1px var(--ds-orange);
}
.priority-pill[data-level='HIGH'].is-active {
  border-color: #d14343;
  background: #fff1f0;
  color: #d14343;
  box-shadow: inset 0 0 0 1px #d14343;
}
.priority-pill[data-level='LOW'].is-active {
  border-color: #9ca3af;
  background: #f3f4f6;
  color: #4b5563;
  box-shadow: inset 0 0 0 1px #9ca3af;
}
.due-quick {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}
.due-chip {
  box-sizing: border-box;
  height: 34px;
  padding: 0 8px;
  border: 1px solid var(--ds-line-strong);
  border-radius: 999px;
  background: #fff;
  color: var(--ds-ink-2);
  font: 600 12px var(--ds-font-sans);
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s, color 0.15s;
}
.due-chip:hover {
  border-color: rgba(232, 74, 28, 0.45);
  color: var(--ds-orange-deep);
  background: var(--ds-orange-wash);
}
.due-chip.is-active {
  border-color: var(--ds-orange);
  background: var(--ds-orange-wash);
  color: var(--ds-orange-deep);
}
.due-input {
  margin-top: 0;
}
.due-input.is-empty {
  color: var(--ds-muted);
}
.task-review-row {
  display: grid;
  grid-template-columns: 20px 1fr;
  gap: 12px;
  align-items: start;
  padding: 12px 14px;
  border: 1px solid var(--ds-line);
  border-radius: 12px;
  background: #fafafa;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}
.task-review-row:hover {
  border-color: rgba(232, 74, 28, 0.35);
  background: #fffaf7;
}
.task-review-row input[type='checkbox'] {
  box-sizing: border-box;
  width: 18px;
  height: 18px;
  margin: 2px 0 0;
  flex-shrink: 0;
  accent-color: var(--ds-orange, #e84a1c);
  cursor: pointer;
}
.task-review-row strong {
  display: block;
  color: var(--ds-ink);
  font-size: 13px;
  font-weight: 700;
  line-height: 1.35;
}
.task-review-row small {
  display: block;
  margin-top: 4px;
  color: var(--ds-muted);
  font-size: 11px;
  font-weight: 500;
  line-height: 1.45;
}
.task-drawer .drawer-form-error {
  margin: 0 20px 8px;
  flex-shrink: 0;
}
.task-drawer .drawer-actions {
  flex-shrink: 0;
  margin: 0;
  padding: 14px 20px 18px;
  border-top: 1px solid var(--ds-line);
  background: #fff;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
.drawer-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 4px;
  padding-top: 14px;
  border-top: 1px solid var(--ds-line);
}
.drawer-form-error {
  margin: 0;
  padding: 10px 12px;
  border-radius: 10px;
  background: #fff1f0;
  color: #d14343;
  font-size: 12px;
  font-weight: 600;
  line-height: 1.5;
}
.task-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--ds-ink);
}
.teacher-card__sub {
  margin: 4px 0 0;
  color: var(--ds-muted);
  font-size: 12px;
  font-weight: 500;
  line-height: 1.45;
}
.col-actions {
  text-align: right;
  white-space: nowrap;
}
.file-input {
  box-sizing: border-box;
  width: 100%;
  padding: 10px 12px;
  border: 1px dashed var(--ds-line-strong);
  border-radius: 10px;
  background: #fafafa;
  font: 500 13px var(--ds-font-sans);
  cursor: pointer;
}
.file-input::file-selector-button {
  margin-right: 10px;
  height: 30px;
  padding: 0 12px;
  border: 1px solid var(--ds-line-strong);
  border-radius: 8px;
  background: #fff;
  color: var(--ds-ink-2);
  font: 700 12px var(--ds-font-sans);
  cursor: pointer;
}
.workspace-empty-block {
  padding: 36px 20px;
  display: grid;
  gap: 10px;
  justify-items: center;
  text-align: center;
  border: 1px dashed var(--ds-line-strong);
  border-radius: 14px;
  background: #fafafa;
}
.workspace-empty-block strong {
  font-size: 15px;
  color: var(--ds-ink);
}
.workspace-empty-block p {
  margin: 0;
  max-width: 320px;
  color: var(--ds-muted);
  font-size: 12px;
  line-height: 1.55;
}
.drawer-tip {
  margin: 0;
  padding: 10px 12px;
  border-radius: 10px;
  color: var(--ds-ink-2);
  background: #f7f8f9;
  border: 1px solid var(--ds-line);
  font-size: 12px;
  font-weight: 500;
  line-height: 1.55;
}
@media (max-width: 520px) {
  .drawer-field-row {
    grid-template-columns: 1fr;
  }
}
.workspace-notice {
  position: fixed;
  right: 24px;
  bottom: 24px;
  z-index: 1300;
  margin: 0;
  padding: 12px 16px;
  border-radius: 12px;
  color: #fff;
  background: var(--ds-ink);
  font-size: 13px;
  font-weight: 700;
  box-shadow: var(--ds-shadow-stage);
}
.cert-meta {
  display: block;
  margin-top: 4px;
  color: var(--ds-muted);
  font-size: 11px;
  font-weight: 600;
}
.cert-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

@media (max-width: 900px) {
  .workspace-kpi {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .workspace-grid {
    grid-template-columns: 1fr;
  }
  .workspace-panel--wide {
    grid-column: auto;
  }
  .relation-grid {
    grid-template-columns: 1fr;
  }
}
</style>
