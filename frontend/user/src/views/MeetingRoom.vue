<template>
  <div class="meeting-room" :class="[`stage-mode-${mobileStageMode}`, `camera-preset-${cameraPreset}`]">
    <div class="room-grid-bg"></div>
    <div class="room-orbit orbit-a"></div>
    <div class="room-orbit orbit-b"></div>
    <!-- 连接/重连遮罩 -->
    <div v-if="reconnecting" class="reconnect-overlay">
      <div class="reconnect-box">
        <div class="reconnect-spinner"></div>
        <span class="reconnect-text">{{ reconnectText }}</span>
        <span class="reconnect-hint">第 {{ reconnectAttempt }} / {{ maxRetries }} 次尝试</span>
        <el-button v-if="reconnectAttempt >= maxRetries" size="small" @click="manualReconnect" style="margin-top:12px">手动重连</el-button>
      </div>
    </div>

    <!-- 顶栏 -->
    <div class="room-header">
      <div class="header-left">
        <div class="meeting-title-wrap">
          <span class="room-mark" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none">
              <rect x="3" y="5.5" width="12.5" height="13" rx="2.2" stroke="currentColor" stroke-width="1.7" />
              <path d="m15.5 10 5-2.7v9.4l-5-2.7" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round" />
            </svg>
          </span>
          <span class="meeting-title-copy">
            <small>路演室</small>
            <strong class="meeting-title">{{ meetingInfo?.title || '正在进入路演' }}</strong>
          </span>
        </div>
        <span
          class="meeting-status-badge"
          :class="{
            'is-running': meetingInfo?.status === 'RUNNING',
            'is-ended': meetingInfo?.status === 'ENDED',
            'is-pending': meetingInfo?.status !== 'RUNNING' && meetingInfo?.status !== 'ENDED'
          }"
        >
          {{ meetingInfo?.status === 'RUNNING' ? '进行中' : meetingInfo?.status === 'ENDED' ? '已结束' : '待开始' }}
        </span>
        <div class="livekit-agent-chip" :class="{ connected }">
          <AgentVisualizer variant="bar" :state="connected ? 'speaking' : 'connecting'" compact />
          <span>{{ connected ? '实时会话已连接' : '正在建立实时会话' }}</span>
        </div>
      </div>
      <div class="header-right">
        <div class="net-status header-plain-meta" v-if="connected">
          <div class="signal-bars" :data-level="networkQuality">
            <span class="bar b1"></span>
            <span class="bar b2"></span>
            <span class="bar b3"></span>
          </div>
          <span class="net-text" :style="{ color: getNetColor(networkQuality) }">{{ getNetText(networkQuality) }}</span>
        </div>
        <span class="participant-num header-plain-meta">
          <el-icon><User /></el-icon>
          <span>成员</span>
          <strong>{{ participants.length }}</strong>
        </span>
        <div class="stage-timer-group">
          <button
            type="button"
            class="countdown-pill stage-timer"
            :class="{ 'is-running': stageTimerRunning, 'is-paused': !stageTimerRunning && stageTimerSeconds > 0 }"
            :title="stageTimerRunning ? '点击暂停计时' : (stageTimerSeconds > 0 ? '点击继续计时' : '点击开始计时')"
            @click="toggleStageTimer"
          >
            <span class="countdown-label">{{ stageTimerRunning ? '计时中' : (stageTimerSeconds > 0 ? '已暂停' : '计时') }}</span>
            <span class="countdown-time">{{ stageTimerText }}</span>
          </button>
          <button
            type="button"
            class="stage-timer-reset"
            :disabled="stageTimerSeconds === 0 && !stageTimerRunning"
            title="重置计时"
            @click="resetStageTimer"
          >
            重置
          </button>
        </div>
      </div>
    </div>

    <!-- 主体 -->
    <div class="room-body">
      <!-- 视频区域 -->
      <div
        ref="videoAreaRef"
        class="video-area"
        :class="[
          { 'chat-open': showChat || showScore },
          `layout-mode-${layoutMode}`,
          `video-fit-${videoFit}`
        ]"
      >
        <!-- 屏幕共享模式：大画面 + 侧边小头像 -->
        <div v-if="hasScreenShare" class="screen-share-layout" :class="'layout-' + screenLayout">
          <!-- 默认：大屏幕 + 小头像侧边栏 -->
          <template v-if="screenLayout === 'default'">
            <div class="screen-main">
              <div class="screen-tile">
                <video :ref="el => { if(el && screenShareParticipant) { videoRefs.set(screenShareParticipant.id, el); if(screenShareParticipant.track) screenShareParticipant.track.attach(el) } }" autoplay playsinline muted disablepictureinpicture controlslist="noremoteplayback noplaybackrate" @dblclick="unpinCamera" title="双击切回共享屏幕主画面"></video>
                <div class="tile-info">
                  <span class="tile-name">{{ screenShareParticipant?.name || '' }} 的屏幕</span>
                </div>
              </div>
            </div>
            <div class="screen-sidebar" v-if="showScreenSidebar">
              <div
                v-for="p in visibleScreenParticipants"
                :key="p.id"
                class="sidebar-tile"
                :class="{ 'is-local': p.isLocal, 'has-video': p.hasVideo, 'is-muted': !p.hasAudio, 'is-speaking': p.isSpeaking }"
                @dblclick="pinCamera(p.id)"
                :title="isScreenShareOwner(p.id) ? '该用户正在共享屏幕，主画面优先显示屏幕共享' : '双击切换为主画面'"
              >
                <div class="sidebar-tile-preview">
                  <template v-if="p.hasVideo && p.id !== screenShareParticipant?.id">
                    <video :ref="el => attachVideo(p, el)" autoplay playsinline :muted="p.isLocal" disablepictureinpicture controlslist="noremoteplayback noplaybackrate"></video>
                  </template>
                  <template v-else>
                    <VoiceAvatar :initials="p.initials" :speaking="p.isSpeaking" :muted="!p.hasAudio" />
                  </template>
                  <div class="sidebar-tile-meta" :title="`${p.name}${p.isLocal ? ' (我)' : ''}`">
                    <span class="sidebar-status" :class="p.hasAudio ? 'is-live' : 'is-muted'" aria-hidden="true"></span>
                    <span class="sidebar-name">{{ p.name }}{{ p.isLocal ? ' (我)' : '' }}</span>
                  </div>
                </div>
              </div>
            </div>
            <el-icon class="sidebar-toggle" :class="{ 'collapsed': !showScreenSidebar }" @click="showScreenSidebar = !showScreenSidebar">
              <DArrowRight v-if="showScreenSidebar" /><DArrowLeft v-else />
            </el-icon>
          </template>

          <!-- 双画面：屏幕 + 1个摄像头并排 -->
          <template v-else-if="screenLayout === 'dual'">
            <div class="dual-main">
              <div class="dual-tile" :class="{ 'has-video': pinnedParticipant?.hasVideo, 'is-muted': pinnedParticipant && !pinnedParticipant.hasAudio, 'is-speaking': pinnedParticipant?.isSpeaking }">
                <template v-if="pinnedParticipant?.hasVideo">
                  <video :ref="el => attachVideo(pinnedParticipant, el)" autoplay playsinline :muted="pinnedParticipant.isLocal" disablepictureinpicture controlslist="noremoteplayback noplaybackrate" @dblclick="unpinCamera" title="双击切回共享屏幕主画面"></video>
                </template>
                <template v-else>
                  <video :ref="el => { if(el && screenShareParticipant) { videoRefs.set(screenShareParticipant.id, el); if(screenShareParticipant.track) screenShareParticipant.track.attach(el) } }" autoplay playsinline muted disablepictureinpicture controlslist="noremoteplayback noplaybackrate" @dblclick="unpinCamera" title="双击切回共享屏幕主画面"></video>
                </template>
                <div class="tile-info">
                  <span class="tile-name">{{ pinnedParticipant ? `${pinnedParticipant.name}${pinnedParticipant.isLocal ? ' (我)' : ''}` : `${screenShareParticipant?.name || ''} 的屏幕` }}</span>
                </div>
              </div>
            </div>
            <div class="dual-sidebar" v-if="showScreenSidebar">
              <div
                v-if="pinnedParticipant && screenShareParticipant"
                class="sidebar-tile sidebar-tile-sm has-video screen-share-thumb"
                @dblclick="unpinCamera"
                title="双击切回共享屏幕主画面"
              >
                <video :ref="el => { if(el && screenShareParticipant) { videoRefs.set(screenShareParticipant.id, el); if(screenShareParticipant.track) screenShareParticipant.track.attach(el) } }" autoplay playsinline muted disablepictureinpicture controlslist="noremoteplayback noplaybackrate"></video>
                <div class="tile-info">
                  <span class="tile-name">{{ screenShareParticipant?.name || '' }} 的屏幕</span>
                </div>
              </div>
              <div v-for="p in visibleScreenParticipants" :key="p.id" class="sidebar-tile sidebar-tile-sm" :class="{ 'is-local': p.isLocal, 'has-video': p.hasVideo, 'is-muted': !p.hasAudio, 'is-speaking': p.isSpeaking }" @dblclick="pinCamera(p.id)" :title="isScreenShareOwner(p.id) ? '该用户正在共享屏幕，主画面优先显示屏幕共享' : '双击切换为主画面'">
                <template v-if="p.hasVideo && p.id !== screenShareParticipant?.id">
                  <video :ref="el => attachVideo(p, el)" autoplay playsinline :muted="p.isLocal" disablepictureinpicture controlslist="noremoteplayback noplaybackrate"></video>
                </template>
                <template v-else>
                  <VoiceAvatar :initials="p.initials" :speaking="p.isSpeaking" :muted="!p.hasAudio" />
                </template>
                <div class="tile-info">
                  <span class="tile-name">{{ p.name }}{{ p.isLocal ? ' (我)' : '' }}</span>
                </div>
              </div>
            </div>
          </template>

          <!-- 多画面：屏幕 + 摄像头网格 -->
          <template v-else-if="screenLayout === 'multi'">
            <div class="multi-main">
              <div class="multi-tile">
                <video :ref="el => { if(el && screenShareParticipant) { videoRefs.set(screenShareParticipant.id, el); if(screenShareParticipant.track) screenShareParticipant.track.attach(el) } }" autoplay playsinline muted disablepictureinpicture controlslist="noremoteplayback noplaybackrate" @dblclick="unpinCamera" title="双击切回共享屏幕主画面"></video>
                <div class="tile-info">
                  <span class="tile-name">{{ screenShareParticipant?.name || '' }} 的屏幕</span>
                </div>
              </div>
            </div>
            <div class="multi-cameras">
              <div v-for="p in visibleScreenParticipants" :key="p.id" class="multi-tile-small" :class="{ 'is-local': p.isLocal, 'is-pinned': p.id === pinnedCamera, 'has-video': p.hasVideo, 'is-muted': !p.hasAudio, 'is-speaking': p.isSpeaking }" @dblclick="pinCamera(p.id)" :title="isScreenShareOwner(p.id) ? '该用户正在共享屏幕，主画面优先显示屏幕共享' : '双击切换为主画面'">
                <template v-if="p.hasVideo && p.id !== screenShareParticipant?.id">
                  <video :ref="el => attachVideo(p, el)" autoplay playsinline :muted="p.isLocal" disablepictureinpicture controlslist="noremoteplayback noplaybackrate"></video>
                </template>
                <template v-else>
                  <VoiceAvatar :initials="p.initials" :speaking="p.isSpeaking" :muted="!p.hasAudio" />
                </template>
                <div class="tile-info">
                  <span class="tile-name">{{ p.name }}{{ p.isLocal ? ' (我)' : '' }}</span>
                  <span v-if="!p.hasAudio" class="icon-muted"><LiveKitIcon name="mic-off" /></span>
                </div>
              </div>
            </div>
          </template>
        </div>

        <!-- 普通模式：网格布局 -->
        <div
          v-else
          class="video-grid"
          :class="[
            {
              'has-mobile-primary-video': !!focusTrackId && secondaryTracks.length > 0,
              'secondary-collapsed': secondaryCollapsed && secondaryTracks.length > 0
            },
            focusTrackId ? `primary-orientation-${focusTrackOrientation}` : ''
          ]"
          :style="gridStyle"
        >
          <div
            v-for="p in layoutParticipants"
            :key="p.id"
            class="video-tile"
            :class="[
              {
                'is-local': p.isLocal,
                'has-video': p.hasVideo,
                'is-muted': !p.hasAudio,
                'is-speaking': p.isSpeaking,
                'mobile-primary-video': p.id === focusTrackId,
                'video-rotate-90': Number(p.videoRotation) === 90,
                'video-rotate-270': Number(p.videoRotation) === 270
              },
              p.videoOrientation ? `orientation-${p.videoOrientation}` : '',
              mobileSecondaryIndex(p.id) ? `mobile-secondary-${mobileSecondaryIndex(p.id)}` : ''
            ]"
            @dblclick="p.hasVideo ? pinCamera(p.id) : null"
            :title="p.hasVideo ? '双击切换为主画面' : ''"
          >
            <template v-if="p.hasVideo">
              <video :ref="el => attachVideo(p, el)" autoplay playsinline :muted="p.isLocal" disablepictureinpicture controlslist="noremoteplayback noplaybackrate"></video>
            </template>
            <template v-else>
              <VoiceAvatar :initials="p.initials" :speaking="p.isSpeaking" :muted="!p.hasAudio" />
            </template>
            <div class="tile-info">
              <span class="tile-name">{{ p.name }}{{ p.isLocal ? ' (我)' : '' }}</span>
              <span v-if="!p.hasAudio" class="icon-muted"><LiveKitIcon name="mic-off" /></span>
            </div>
          </div>
          <button
            v-if="focusTrackId && secondaryTracks.length > 0"
            class="secondary-toggle"
            :class="{ collapsed: secondaryCollapsed }"
            type="button"
            :aria-label="secondaryCollapsed ? '展开次要画面' : '折叠次要画面'"
            @click="secondaryCollapsed = !secondaryCollapsed"
          >
            <span class="toggle-count" v-if="secondaryCollapsed">{{ secondaryTracks.length }}</span>
            <el-icon>
              <DArrowLeft v-if="secondaryCollapsed" />
              <DArrowRight v-else />
            </el-icon>
          </button>
          <div v-if="layoutParticipants.length === 0" class="grid-empty">
            <div class="empty-visualizer">
              <AgentVisualizer variant="aura" :state="connected ? 'listening' : 'connecting'" />
            </div>
            <span class="empty-title">{{ connected ? '等待其他参与者' : '正在进入路演室' }}</span>
            <span class="empty-subtitle">{{ connected ? '路演已就绪，可以开始交流' : '正在准备音视频连接' }}</span>
          </div>
        </div>
      </div>

      <!-- 右侧面板 -->
      <transition name="slide-right">
        <div v-if="showChat" class="side-panel chat-panel">
          <div class="panel-head">
            <span>路演交流</span>
            <el-icon class="close-icon" @click="showChat = false"><Close /></el-icon>
          </div>
          <div class="chat-messages" ref="chatMessagesRef">
            <div v-for="(msg, i) in chatMessages" :key="i" class="chat-msg" :class="{ own: msg.sender === currentUser }">
              <div class="msg-head">
                <span class="msg-sender">{{ msg.sender }}</span>
                <span class="msg-time">{{ formatTime(msg.time) }}</span>
              </div>
              <div class="msg-body" :class="`msg-type-${msg.type || 'text'}`">
                <span v-if="msg.type === 'text' || !msg.type" class="msg-text">{{ msg.content }}</span>
                <el-image v-else-if="msg.type === 'image'" :src="chatMediaUrl(msg.content)" :preview-src-list="[chatMediaUrl(msg.content)]" class="msg-image" fit="cover" />
                <a v-else-if="msg.type === 'file'" :href="chatMediaUrl(msg.content)" target="_blank" class="file-link">
                  <span class="file-icon"><el-icon><Paperclip /></el-icon></span>
                  <span class="file-meta">
                    <strong>{{ msg.fileName || '路演附件' }}</strong>
                    <small>点击打开或下载</small>
                  </span>
                </a>
              </div>
            </div>
            <div v-if="chatMessages.length === 0" class="chat-empty">
              <LiveKitIcon name="chat" />
              <strong>暂无聊天消息</strong>
              <span>路演中的文字、图片和文件会显示在这里</span>
            </div>
          </div>
          <div class="chat-input">
            <div class="chat-bar">
              <el-upload :http-request="uploadImage" :show-file-list="false" accept="image/*" class="chat-upload-btn">
                <el-icon :size="18"><PictureFilled /></el-icon>
              </el-upload>
              <el-upload :http-request="uploadDoc" :show-file-list="false" class="chat-upload-btn">
                <el-icon :size="18"><Paperclip /></el-icon>
              </el-upload>
              <el-input v-model="chatInput" placeholder="输入消息..." size="small" @keyup.enter="sendChat" clearable style="flex:1" />
              <el-button type="primary" size="small" @click="sendChat" :disabled="!chatInput.trim()" class="send-btn">
                <el-icon :size="16"><Promotion /></el-icon>
              </el-button>
            </div>
          </div>
        </div>

        <div v-else-if="showScore" class="side-panel score-panel">
          <div class="panel-head">
            <div class="panel-title-wrap">
              <span class="panel-kicker">SCORE PANEL</span>
              <span>路演评分</span>
            </div>
            <el-icon class="close-icon" @click="showScore = false"><Close /></el-icon>
          </div>
          <div class="score-body">
            <div class="score-total-bar">
              <div class="score-total-copy">
                <span class="score-total-label">当前总分</span>
                <strong class="total-val">{{ totalScore }}</strong>
                <span class="score-total-max">/ {{ maxTotalScore }}</span>
              </div>
              <div class="score-total-progress">
                <span :style="{ width: `${scoreProgress}%` }"></span>
              </div>
            </div>
            <div v-for="(group, gIdx) in groupedScoreItems" :key="gIdx" class="score-group">
              <div class="group-title">
                <span>{{ group.category }}</span>
                <small>{{ group.items.length }} 项</small>
              </div>
              <div v-for="item in group.items" :key="item.id" class="score-item">
                <div class="score-item-head">
                  <div class="score-row-left">
                    <el-tooltip :content="item.description" placement="top" :show-after="500">
                      <span class="score-name">{{ item.name }}</span>
                    </el-tooltip>
                  </div>
                  <div class="score-value-pill">
                    <el-input-number
                      v-model="scoreForm.scores[item.id]"
                      :min="0"
                      :max="Number(item.maxScore)||100"
                      :step="0.5"
                      :controls="false"
                      size="small"
                      class="score-number-input"
                    />
                    <small>/{{ item.maxScore }}</small>
                  </div>
                </div>
                <div v-if="item.description" class="score-desc">{{ item.description }}</div>
                <el-slider
                  v-model="scoreForm.scores[item.id]"
                  :min="0"
                  :max="Number(item.maxScore)||100"
                  :step="0.5"
                  :show-tooltip="false"
                  class="score-slider"
                />
                <el-input
                  v-model="scoreForm.comments[item.id]"
                  :placeholder="`${item.name}评语`"
                  size="small"
                  type="textarea"
                  :rows="1"
                  class="score-comment"
                />
              </div>
            </div>
            <div v-if="scoreItems.length === 0" class="score-empty">
              <AgentVisualizer variant="grid" state="thinking" compact />
              <span>正在加载评分项</span>
            </div>
          </div>
          <div class="panel-footer score-footer">
            <div class="score-submit-meta">
              <span>待提交总分</span>
              <strong>{{ totalScore }}</strong>
            </div>
            <el-button type="primary" :loading="submitting" @click="submitScore">提交评分</el-button>
          </div>
        </div>
      </transition>
    </div>


    <!-- AI评分功能由 AudioRecorder 组件处理 -->

    <!-- 底部控制栏（腾讯会议风格） -->
    <div class="control-bar">
      <!-- 左区：媒体控制 -->
      <div class="control-section control-left">
        <el-button size="large" circle @click="toggleMic" :class="{ 'btn-off': isMuted, 'btn-live': !isMuted }" :title="isMuted ? '开启麦克风' : '关闭麦克风'">
          <LiveKitIcon :name="isMuted ? 'mic-off' : 'mic'" />
        </el-button>
        <el-button size="large" circle @click="toggleCam" :class="{ 'btn-off': isCamOff, 'btn-live': !isCamOff }" :title="isCamOff ? '开启摄像头' : '关闭摄像头'">
          <LiveKitIcon :name="isCamOff ? 'camera-off' : 'camera'" />
        </el-button>
        <el-button size="large" circle @click="toggleScreen" :class="[{ 'btn-active': isScreenSharing }, 'mobile-fold-control']" title="共享屏幕">
          <LiveKitIcon :name="isScreenSharing ? 'screen-stop' : 'screen'" />
        </el-button>
      </div>

      <!-- 中区：功能面板 -->
      <div class="control-section control-center">
        <el-button
          size="large"
          circle
          @click="toggleServerRecording"
          :loading="isRecordingLoading"
          :class="[{ 'btn-recording': isRecording }, 'mobile-fold-control']"
          :title="isRecording ? '停止路演录制' : '开始路演录制'"
        >
          <LiveKitIcon :name="isRecording ? 'record-stop' : 'record'" />
        </el-button>
        <AudioRecorder
          ref="audioRecorderRef"
          :meeting-id="meetingId"
          :project-id="meetingInfo?.projectId || null"
          :team-id="meetingInfo?.teamId || null"
          :camera-meta="localCameraMeta"
          :track-id="meetingInfo?.trackId || meetingInfo?.trackName || '新一代信息技术赛道'"
          :track-name="meetingInfo?.trackName || '新一代信息技术赛道'"
          :project-name="meetingInfo?.projectName || ''"
          :team-name="meetingInfo?.teamName || ''"
          @recording-status-change="onRecordingStatus"
        />
        <el-button v-if="hasScreenShare" size="large" circle @click="cycleScreenLayout" title="切换布局" :class="[{ 'btn-active': screenLayout !== 'default' }, 'mobile-fold-control']">
          <LiveKitIcon name="grid" />
        </el-button>
        <el-button size="large" circle @click="showChat = !showChat; showScore = false" :class="[{ 'btn-active': showChat }, 'mobile-fold-control']" title="聊天">
          <LiveKitIcon name="chat" />
        </el-button>
        <el-button size="large" circle @click="showScore = !showScore; showChat = false" :class="[{ 'btn-active': showScore }, 'mobile-fold-control']" title="评分">
          <LiveKitIcon name="score" />
        </el-button>
        <el-button size="large" circle @click="showIssues = !showIssues" class="mobile-fold-control" title="问题列表">
          <LiveKitIcon name="issues" />
        </el-button>
      </div>

      <!-- 右区：AI评分 + 辅助 + 退出 -->
      <div class="control-section control-right">
        <el-dropdown
          class="mobile-fold-control"
          trigger="click"
          placement="top-end"
          popper-class="meeting-quality-popper"
          :teleported="!isFullscreen"
          @command="changeQuality"
        >
          <el-button size="large" circle title="清晰度">
            <LiveKitIcon name="settings" />
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item v-for="opt in qualityOptions" :key="opt.value" :command="opt.value" :class="{ 'is-active-quality': videoQuality === opt.value }">
                <span>{{ opt.label }}</span>
                <el-icon v-if="videoQuality === opt.value" style="margin-left:8px"><Check /></el-icon>
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-dropdown
          trigger="click"
          placement="top-end"
          popper-class="meeting-mobile-more-popper"
          :teleported="!isFullscreen"
          @command="handleMobileMoreCommand"
        >
          <el-button size="large" circle class="mobile-more-control" title="更多功能">
            <el-icon><MoreFilled /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item disabled class="mobile-menu-label">路演操作</el-dropdown-item>
              <el-dropdown-item command="screen">
                {{ isScreenSharing ? '停止共享屏幕' : '共享屏幕' }}
              </el-dropdown-item>
              <el-dropdown-item command="record" :class="{ 'is-active-quality': isRecording }">
                {{ isRecording ? '停止录制' : '路演录制' }}
              </el-dropdown-item>
              <el-dropdown-item command="chat" :class="{ 'is-active-quality': showChat }">
                路演交流
              </el-dropdown-item>
              <el-dropdown-item command="score" :class="{ 'is-active-quality': showScore }">
                手动评分
              </el-dropdown-item>
              <el-dropdown-item command="issues" :class="{ 'is-active-quality': showIssues }">
                问题列表
              </el-dropdown-item>
              <el-dropdown-item v-if="hasScreenShare" command="layout" :class="{ 'is-active-quality': screenLayout !== 'default' }">
                切换布局
              </el-dropdown-item>
              <el-dropdown-item command="fullscreen">
                {{ isFullscreen ? '退出全屏' : '全屏显示' }}
              </el-dropdown-item>
              <el-dropdown-item disabled class="mobile-menu-label" divided>摄像头</el-dropdown-item>
              <el-dropdown-item command="camera-mode:front" :class="{ 'is-active-quality': cameraPreset === 'front' }">
                前置
                <el-icon v-if="cameraPreset === 'front'" style="margin-left:8px"><Check /></el-icon>
              </el-dropdown-item>
              <el-dropdown-item command="camera-mode:rearLandscape" :class="{ 'is-active-quality': cameraPreset === 'rearLandscape' }">
                后置宽屏 16:9
                <el-icon v-if="cameraPreset === 'rearLandscape'" style="margin-left:8px"><Check /></el-icon>
              </el-dropdown-item>
              <el-dropdown-item command="camera-mode:rearPortrait" :class="{ 'is-active-quality': cameraPreset === 'rearPortrait' }">
                后置竖屏 9:16
                <el-icon v-if="cameraPreset === 'rearPortrait'" style="margin-left:8px"><Check /></el-icon>
              </el-dropdown-item>
              <el-dropdown-item
                v-for="opt in qualityOptions"
                :key="`mobile-quality-${opt.value}`"
                :command="`quality:${opt.value}`"
                :class="{ 'is-active-quality': videoQuality === opt.value }"
                :divided="opt.value === 'low'"
              >
                <span>{{ opt.label }}</span>
                <el-icon v-if="videoQuality === opt.value" style="margin-left:8px"><Check /></el-icon>
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-button size="large" circle @click="toggleFullscreen" class="mobile-fold-control" :title="isFullscreen ? '退出全屏' : '全屏'">
          <LiveKitIcon name="fullscreen" />
        </el-button>
        <el-button size="large" type="danger" round @click="leaveMeeting">
          <LiveKitIcon name="leave" />
          <span>离开路演</span>
        </el-button>
      </div>
    </div>

    <!-- 问题列表抽屉 -->
    <el-drawer v-model="showIssues" direction="rtl" size="460px" class="issues-drawer" :with-header="false">
      <div class="issues-panel">
          <div class="issues-head">
            <div>
              <strong>问题列表</strong>
              <p>路演评分生成的问题清单与处理状态。</p>
            </div>
            <button class="issues-close" type="button" @click="showIssues = false" aria-label="关闭问题列表">
              <el-icon><Close /></el-icon>
            </button>
            <div class="issues-metrics">
              <button type="button" :class="{ active: issueFilter === 'all' }" @click="issueFilter = 'all'">全部 {{ issues.length }}</button>
              <button type="button" :class="{ active: issueFilter === 'open' }" @click="issueFilter = 'open'">待解决 {{ pendingIssueCount }}</button>
              <button type="button" :class="{ active: issueFilter === 'resolved' }" @click="issueFilter = 'resolved'">已解决 {{ resolvedIssueCount }}</button>
              <button type="button" class="refresh" @click="loadIssues">刷新</button>
            </div>
          </div>

        <div v-if="!filteredIssues.length" class="issues-empty">
          <span>NO ISSUE</span>
          <strong>{{ issues.length ? '当前筛选下暂无问题' : '暂无问题记录' }}</strong>
          <p>{{ issues.length ? '可以切换筛选条件查看其他状态。' : '评分或 AI 复盘生成问题后，会显示在这里。' }}</p>
        </div>

        <div v-else class="issues-list">
          <div
            v-for="issue in filteredIssues"
            :key="issue.id"
            class="issue-row-card"
            :class="{ resolved: isIssueResolved(issue) }"
          >
            <div class="issue-index">#{{ issue.id }}</div>
            <div class="issue-copy">
              <div class="issue-row-top">
                <div class="issue-title">{{ issue.title || issue.description || '未填写问题描述' }}</div>
                <span class="issue-category-pill">{{ issue.category || '未分类' }}</span>
                <span class="issue-state">{{ isIssueResolved(issue) ? '已解决' : '待解决' }}</span>
              </div>
              <div class="issue-desc" v-if="issue.description">{{ issue.description }}</div>
              <div class="issue-meta">
                <span v-if="issue.createdAt">创建：{{ formatDateTime(issue.createdAt) }}</span>
                <span v-if="issue.reporterName">来源：{{ issue.reporterName }}</span>
                <span v-if="issue.resolvedAt">解决：{{ formatDateTime(issue.resolvedAt) }}</span>
              </div>
            </div>
            <div class="issue-actions">
              <button v-if="!isIssueResolved(issue)" type="button" @click="resolveIssue(issue)">标记解决</button>
              <span v-else>已完成</span>
            </div>
          </div>
        </div>
      </div>
    </el-drawer>


  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, computed, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Room, RoomEvent, Track, VideoPresets, ScreenSharePresets, ConnectionQuality, VideoQuality
} from 'livekit-client'
import {
  Microphone, VideoCamera, Monitor, Close, User,
  ChatDotRound, EditPen, List, PictureFilled, Paperclip, Promotion,
  Mute, VideoPause, VideoPlay, Setting, Check, Loading, Download, DArrowRight, DArrowLeft, Switch, FullScreen, Grid, MoreFilled
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import request from '../utils/request'
import { getUserToken } from '../utils/authStorage'
import { withAuthMediaUrl } from '../utils/mediaUrl'
import AudioRecorder from '../components/AudioRecorder.vue'
import AgentVisualizer from '../components/AgentVisualizer.vue'
import LiveKitIcon from '../components/LiveKitIcon.vue'
import VoiceAvatar from '../components/VoiceAvatar.vue'

const audioRecorderRef = ref(null)

function chatMediaUrl(url) {
  return withAuthMediaUrl(url)
}

const route = useRoute()
const router = useRouter()
const meetingId = computed(() => route.params.id)
const currentUser = computed(() => { const u = JSON.parse(localStorage.getItem('user') || '{}'); return u.username || '' })
const userId = computed(() => { const u = JSON.parse(localStorage.getItem('user') || '{}'); return u.id || 0 })
const VERIFIED_MEETING_ACCESS_KEY = 'verifiedMeetingAccess'
const VERIFIED_MEETING_ACCESS_TTL = 10 * 60 * 1000

// ---- 会议 ----
const meetingInfo = ref(null)
// Stage stopwatch (manual + auto with AI scoring)
const stageTimerSeconds = ref(0)
const stageTimerRunning = ref(false)
const stageTimerText = computed(() => formatStageTimer(stageTimerSeconds.value))
let stageTimerInterval = null
let stageTimerAutoOwned = false // started by AI scoring, should auto-stop with it

// ---- 面板 ----
const showChat = ref(false)
const showScore = ref(false)
const showIssues = ref(false)

// ---- LiveKit ----
const connected = ref(false)
const isMuted = ref(true)
const isCamOff = ref(true)
const isScreenSharing = ref(false)
const isRecording = ref(false)
const isRecordingLoading = ref(false)
const recordingDbId = ref(null)
let recordingStatusTimer = null
const showProgress = ref(false)
const progressPercent = ref(0)
const progressSteps = ref([
  { label: '录制完成', detail: '', active: false, done: false },
  { label: '上传文件', detail: '', active: false, done: false },
  { label: '音频转码', detail: '', active: false, done: false },
  { label: '语音识别', detail: '', active: false, done: false },
  { label: '语音分析', detail: '', active: false, done: false },
  { label: '视频分析', detail: '', active: false, done: false },
  { label: '音视频融合', detail: '', active: false, done: false },
  { label: 'AI五维评分', detail: '', active: false, done: false },
  { label: '生成能力画像', detail: '', active: false, done: false },
])
const isFullscreen = ref(false)
const networkQuality = ref(0)
const reconnecting = ref(false)
const reconnectAttempt = ref(0)
const reconnectText = ref('正在连接...')
const maxRetries = 5
let leavingMeeting = false
let _micMutedByScreenShare = false // 因屏幕共享音频而自动静音麦克风的标记
// 连接保护（防重入 + 防重连风暴）
let isConnecting = false
let _connectId = 0
let _reconnectTimer = null
const currentFacing = ref('user') // 'user' = 前置, 'environment' = 后置 // 0=unknown, 1=poor, 2=good, 3=excellent (LiveKit ConnectionQuality)
const rearCameraRatio = ref('portrait') // environment 摄像头采集比例：portrait=9:16，landscape=16:9
const cameraPreset = computed(() => {
  if (currentFacing.value !== 'environment') return 'front'
  return rearCameraRatio.value === 'landscape' ? 'rearLandscape' : 'rearPortrait'
})
const localCameraMeta = computed(() => {
  const local = participants.value.find(p => p.id === 'local') || {}
  return {
    cameraPreset: cameraPreset.value,
    facing: currentFacing.value,
    rearCameraRatio: rearCameraRatio.value,
    rawOrientation: local.rawOrientation || 'unknown',
    videoOrientation: local.videoOrientation || (cameraPreset.value === 'rearLandscape' ? 'landscape' : 'portrait'),
    videoRotation: Number(local.videoRotation || 0)
  }
})
const videoQuality = ref('high') // low=360p, medium=720p, high=1080p
const showScreenSidebar = ref(true)
const qualityOptions = [
  { label: '流畅 360P', value: 'low' },
  { label: '高清 720P', value: 'medium' },
  { label: '超清 1080P', value: 'high' }
]
const qualityLabels = { low: '360P', medium: '720P', high: '1080P' }

function hasVerifiedMeetingAccess() {
  const currentMeetingId = String(meetingId.value)
  if (sessionStorage.getItem('verifiedMeetingId') === currentMeetingId) return true

  try {
    const access = JSON.parse(localStorage.getItem(VERIFIED_MEETING_ACCESS_KEY) || '{}')
    const verifiedAt = Number(access.verifiedAt) || 0
    const isCurrentMeeting = String(access.meetingId || '') === currentMeetingId
    const isFresh = Date.now() - verifiedAt < VERIFIED_MEETING_ACCESS_TTL
    if (isCurrentMeeting && isFresh) {
      sessionStorage.setItem('verifiedMeetingId', currentMeetingId)
      return true
    }
  } catch {}

  return false
}

function clearVerifiedMeetingAccess() {
  sessionStorage.removeItem('verifiedMeetingId')
  localStorage.removeItem(VERIFIED_MEETING_ACCESS_KEY)
}

const mobileStageMode = ref('auto') // auto | landscape | portrait
const screenLayout = ref('default') // 'default'=大屏幕+小头像, 'dual'=屏幕+1摄像头并排, 'multi'=屏幕+摄像头网格
const pinnedCamera = ref(null) // 钉选的摄像头 participant.id
const secondaryCollapsed = ref(false)
const videoAreaRef = ref(null)
const videoAreaSize = ref({ width: 0, height: 0 })
let room = null
let screenAudioCheckTimer = null
let videoAreaObserver = null

// ---- 参与者模型 ----
const AVATAR_COLORS = ['#1677ff', '#52c41a', '#fa541c', '#722ed1', '#eb2f96', '#13c2c2', '#fa8c16', '#2f54eb']

function getInitials(name) {
  if (!name) return '?'
  const clean = name.replace(/\(我\)|（我）/g, '').trim()
  return clean.length > 2 ? clean.slice(0, 2) : clean
}

function getColor(id) {
  let hash = 0
  const s = String(id)
  for (let i = 0; i < s.length; i++) hash = ((hash << 5) - hash + s.charCodeAt(i)) | 0
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length]
}

const participants = ref([]) // 真实用户 { id, name, isLocal, hasVideo, hasAudio, track, color, initials }
const screenShares = ref([]) // 屏幕共享源 { id, ownerId, name, isLocal, hasVideo, track, source }

function isHiddenParticipant(p) {
  const identity = String(p?.identity || '')
  const name = String(p?.name || '')
  const sid = String(p?.sid || '')
  const looksLikeLiveKitSid = value => /^PA_[A-Za-z0-9]+$/.test(String(value || ''))
  return identity.startsWith('recorder-')
    || name === 'Recording Bot'
    || looksLikeLiveKitSid(identity)
    || looksLikeLiveKitSid(name)
    || (!identity && !name && looksLikeLiveKitSid(sid))
}

function isScreenShareAudioPublication(pub) {
  if (!pub) return false
  return pub.source === Track.Source.ScreenShareAudio
    || (pub.source === Track.Source.ScreenShare && pub.track?.kind === 'audio')
}

function updateParticipant(id, updates) {
  const displayName = updates.name || id
  if (!updates.isLocal && /^PA_[A-Za-z0-9]+$/.test(String(displayName || ''))) return
  const idx = participants.value.findIndex(p => p.id === id)
  if (idx >= 0) {
    Object.assign(participants.value[idx], updates)
  } else {
    participants.value.push({
      id,
      name: displayName,
      isLocal: !!updates.isLocal,
      hasVideo: false,
      hasAudio: false,
      isSpeaking: false,
      track: null,
      videoOrientation: 'unknown',
      videoRotation: 0,
      cameraPreset: 'unknown',
      color: getColor(id),
      initials: getInitials(displayName),
      ...updates
    })
  }
}

function syncActiveSpeakers(activeSpeakers = []) {
  const activeIds = new Set(activeSpeakers.map(p => {
    if (p?.isLocal) return 'local'
    return p?.sid || p?.identity
  }).filter(Boolean))

  participants.value.forEach(p => {
    if (p.source === 'screenShare') {
      p.isSpeaking = false
      return
    }
    p.isSpeaking = activeIds.has(p.id) && p.hasAudio
  })
}

function removeParticipant(id) {
  participants.value = participants.value.filter(p => p.id !== id)
}

function removeHiddenParticipants() {
  participants.value = participants.value.filter(p => !isHiddenParticipant({
    sid: p.id,
    identity: p.identity,
    name: p.name
  }))
}

function updateScreenShare(id, updates) {
  const idx = screenShares.value.findIndex(p => p.id === id)
  if (idx >= 0) {
    Object.assign(screenShares.value[idx], updates)
  } else {
    screenShares.value.push({
      id,
      ownerId: updates.ownerId || id,
      name: updates.name || id,
      isLocal: !!updates.isLocal,
      hasVideo: true,
      track: null,
      source: 'screenShare',
      ...updates
    })
  }
}

function removeScreenShare(id) {
  screenShares.value = screenShares.value.filter(p => p.id !== id)
}

const videoRefs = new Map()

function checkScreenAudioAudible(audioTrack) {
  if (!audioTrack) return
  if (screenAudioCheckTimer) clearTimeout(screenAudioCheckTimer)

  let audioContext = null
  let source = null
  let analyser = null
  let peak = 0
  try {
    audioContext = new AudioContext()
    analyser = audioContext.createAnalyser()
    analyser.fftSize = 2048
    source = audioContext.createMediaStreamSource(new MediaStream([audioTrack]))
    source.connect(analyser)
    const buffer = new Uint8Array(analyser.fftSize)
    const startedAt = Date.now()

    const sample = () => {
      if (!analyser) return
      analyser.getByteTimeDomainData(buffer)
      for (let i = 0; i < buffer.length; i++) {
        peak = Math.max(peak, Math.abs(buffer[i] - 128) / 128)
      }
      if (Date.now() - startedAt < 3500) {
        screenAudioCheckTimer = setTimeout(sample, 250)
        return
      }
      try { source?.disconnect() } catch {}
      audioContext?.close?.().catch(() => {})
      screenAudioCheckTimer = null
      if (peak < 0.002) {
        ElMessage.warning('已检测到屏幕音频轨，但当前没有声音。请确认共享的是 Chrome 标签页并勾选共享标签页音频')
      }
    }
    sample()
  } catch {
    try { source?.disconnect() } catch {}
    audioContext?.close?.().catch(() => {})
  }
}

// 网格布局：根据参与人数动态调整
const gridLayout = computed(() => {
  const visibleCount = focusTrackId.value
    ? Math.min(participants.value.length, 1 + maxSecondaryTracks.value)
    : participants.value.length
  const n = visibleCount
  if (n <= 0) return { cols: 1, rows: 1 }
  if (n === 1) return { cols: 1, rows: 1 }
  if (n === 2) return { cols: 2, rows: 1 }
  if (n <= 4) return { cols: 2, rows: 2 }
  if (n <= 6) return { cols: 3, rows: 2 }
  if (n <= 9) return { cols: 3, rows: 3 }
  if (n <= 12) return { cols: 4, rows: 3 }
  if (n <= 16) return { cols: 4, rows: 4 }
  if (n <= 20) return { cols: 5, rows: 4 }
  const cols = Math.ceil(Math.sqrt(n))
  const rows = Math.ceil(n / cols)
  return { cols, rows }
})
const gridStyle = computed(() => {
  const { cols, rows } = gridLayout.value
  return {
    gridTemplateColumns: `repeat(${cols}, 1fr)`,
    gridTemplateRows: `repeat(${rows}, 1fr)`
  }
})
const hasScreenShare = computed(() => {
  return screenShares.value.some(p => p.hasVideo)
})
const screenShareParticipant = computed(() => {
  return screenShares.value.find(p => p.hasVideo)
})
// 可钉选的摄像头用户（有视频且不是屏幕共享）
const cameraParticipants = computed(() => {
  return participants.value.filter(p => p.hasVideo)
})

const areaIsMobile = computed(() => {
  const width = videoAreaSize.value.width || window.innerWidth || 0
  return width <= 768
})
const focusTrack = computed(() => {
  if (hasScreenShare.value) return screenShareParticipant.value || null
  if (pinnedCamera.value) {
    const pinned = participants.value.find(p => p.id === pinnedCamera.value)
    if (pinned) return pinned
  }
  const remoteCamera = participants.value.find(p => p.hasVideo && !p.isLocal)
  const localCamera = participants.value.find(p => p.hasVideo && p.isLocal)
  const speaking = participants.value.find(p => p.isSpeaking && p.hasAudio)
  const local = participants.value.find(p => p.isLocal)
  return remoteCamera || localCamera || speaking || local || participants.value[0] || null
})
const focusTrackId = computed(() => focusTrack.value?.id || '')
const focusTrackOrientation = computed(() => {
  const primary = participants.value.find(p => p.id === focusTrackId.value)
  return primary?.videoOrientation && primary.videoOrientation !== 'unknown'
    ? primary.videoOrientation
    : 'portrait'
})
const secondaryTracks = computed(() => {
  return participants.value.filter(p => p.id !== focusTrackId.value)
})
watch(() => secondaryTracks.value.length, (count) => {
  if (count === 0) secondaryCollapsed.value = false
})
const layoutMode = computed(() => {
  if (hasScreenShare.value) return 'screenShare'
  if (focusTrackId.value) return areaIsMobile.value ? 'mobileFocus' : 'focus'
  return 'grid'
})
const videoFit = computed(() => focusTrackId.value || hasScreenShare.value ? 'contain' : 'cover')
const maxSecondaryTracks = computed(() => {
  const { width, height } = videoAreaSize.value
  const total = secondaryTracks.value.length
  if (!focusTrackId.value) return total
  if ((width || window.innerWidth) <= 768) return Math.min(total, 2)
  // Keep small meetings complete. The filmstrip can scroll/stack visually, but
  // dropping participants makes different clients appear to have missing video.
  if (height && height < 600) return Math.min(total, 4)
  if (width && width < 1180) return Math.min(total, 2)
  return Math.min(total, 4)
})
const layoutParticipants = computed(() => {
  if (!focusTrackId.value) return participants.value
  const focus = participants.value.find(p => p.id === focusTrackId.value)
  if (!focus) return participants.value
  if (secondaryCollapsed.value) return [focus]
  return [focus, ...secondaryTracks.value.slice(0, maxSecondaryTracks.value)]
})
const visibleScreenParticipants = computed(() => {
  const base = pinnedCamera.value
    ? participants.value.filter(p => p.id !== pinnedCamera.value)
    : participants.value
  return base
})
function isScreenShareOwner(participantId) {
  if (!hasScreenShare.value) return false
  return screenShares.value.some(share => share.hasVideo && share.ownerId === participantId)
}
function mobileSecondaryIndex(participantId) {
  if (!focusTrackId.value || participantId === focusTrackId.value) return 0
  return layoutParticipants.value.filter(p => p.id !== focusTrackId.value).findIndex(p => p.id === participantId) + 1
}
// 钉选的摄像头参与者
const pinnedParticipant = computed(() => {
  if (!pinnedCamera.value) return null
  return participants.value.find(p => p.id === pinnedCamera.value) || null
})
watch(pinnedParticipant, (participant) => {
  if (pinnedCamera.value && !participant) unpinCamera()
})
watch(screenShareParticipant, () => {
  if (pinnedCamera.value && isScreenShareOwner(pinnedCamera.value)) unpinCamera()
})
// 侧边栏显示的参与者（排除钉选的）
const sidebarParticipants = computed(() => {
  if (!pinnedCamera.value) return participants.value
  return participants.value.filter(p => p.id !== pinnedCamera.value)
})

function attachVideo(p, el) {
  if (el) {
    videoRefs.set(p.id, el)
    if (p.track) p.track.attach(el)
    bindVideoOrientation(p, el)
  }
}

function resolveVideoOrientation(width, height) {
  if (!width || !height) return 'unknown'
  return width >= height ? 'landscape' : 'portrait'
}

function getTrackOrientation(track) {
  const settings = track?.mediaStreamTrack?.getSettings?.() || track?.getSettings?.() || {}
  return resolveVideoOrientation(settings.width, settings.height)
}

function normalizeCameraMeta(meta = {}, fallbackTrack = null) {
  const preset = meta.cameraPreset || meta.preset || 'unknown'
  const rawOrientation = meta.rawOrientation || meta.actualOrientation || getTrackOrientation(fallbackTrack)
  let videoOrientation = meta.videoOrientation || meta.orientation || rawOrientation
  let videoRotation = Number(meta.videoRotation ?? meta.rotation ?? 0) || 0

  if (preset === 'rearLandscape') {
    videoOrientation = 'landscape'
    videoRotation = rawOrientation === 'portrait' ? 90 : videoRotation
  } else if (preset === 'rearPortrait') {
    videoOrientation = 'portrait'
  }

  if (!['landscape', 'portrait'].includes(videoOrientation)) {
    videoOrientation = rawOrientation !== 'unknown' ? rawOrientation : 'portrait'
  }

  return {
    cameraPreset: preset,
    rawOrientation,
    videoOrientation,
    videoRotation
  }
}

function buildLocalCameraMeta(track) {
  return normalizeCameraMeta({
    cameraPreset: cameraPreset.value,
    facing: currentFacing.value,
    rearCameraRatio: rearCameraRatio.value
  }, track)
}

function applyCameraMeta(participantId, meta = {}, fallbackTrack = null) {
  const normalized = normalizeCameraMeta(meta, fallbackTrack)
  updateParticipant(participantId, {
    cameraPreset: normalized.cameraPreset,
    rawOrientation: normalized.rawOrientation,
    videoOrientation: normalized.videoOrientation,
    videoRotation: normalized.videoRotation
  })
  return normalized
}

function publishLocalCameraMeta(track = null) {
  if (!room?.localParticipant) return
  const pub = room.localParticipant.getTrackPublication(Track.Source.Camera)
  const cameraTrack = track || pub?.track
  if (!cameraTrack) return
  const meta = applyCameraMeta('local', buildLocalCameraMeta(cameraTrack), cameraTrack)
  try {
    room.localParticipant.publishData(chatEncoder.encode(JSON.stringify({
      type: 'camera-meta',
      ...meta,
      facing: currentFacing.value,
      rearCameraRatio: rearCameraRatio.value,
      ts: Date.now()
    })), { reliable: true })
  } catch (err) {
    console.warn('[CameraMeta] 发布摄像头姿态失败:', err)
  }
}

function getCameraResolution(quality = videoQuality.value, facing = currentFacing.value, ratio = rearCameraRatio.value) {
  const base = qualityMap[quality] || qualityMap.high
  if (facing === 'environment' && ratio === 'portrait') {
    return { width: base.height, height: base.width }
  }
  return { width: base.width, height: base.height }
}

function getCameraConstraints(quality = videoQuality.value, facing = currentFacing.value, ratio = rearCameraRatio.value) {
  const res = getCameraResolution(quality, facing, ratio)
  return {
    width: { ideal: res.width, max: res.width },
    height: { ideal: res.height, max: res.height },
    aspectRatio: { ideal: res.width / res.height },
    resizeMode: { ideal: 'none' },
    facingMode: { ideal: facing }
  }
}

async function applyCameraPreset(preset) {
  if (preset === 'front') return switchCameraFacing('user', rearCameraRatio.value)
  if (preset === 'rearLandscape') return switchCameraFacing('environment', 'landscape')
  if (preset === 'rearPortrait') return switchCameraFacing('environment', 'portrait')
}

async function applyDeviceOrientationForCamera(facing, ratio) {
  const isMobile = window.matchMedia?.('(max-width: 768px)').matches
  if (!isMobile) return
  if (!screen?.orientation?.lock) return
  try {
    if (facing === 'environment' && ratio === 'landscape') {
      if (!document.fullscreenElement) {
        await document.documentElement.requestFullscreen?.().catch(() => {})
      }
      await screen.orientation.lock('landscape')
    } else if (facing === 'environment' && ratio === 'portrait') {
      await screen.orientation.lock('portrait')
    } else {
      screen.orientation.unlock?.()
    }
  } catch {
    // 部分移动浏览器只允许在全屏或用户手势后锁定方向。
  }
}

function refreshVideoOrientation(p, el) {
  if (!p?.id) return
  const videoOrientation = resolveVideoOrientation(el?.videoWidth, el?.videoHeight)
  const trackOrientation = getTrackOrientation(p.track)
  const rawOrientation = videoOrientation !== 'unknown' ? videoOrientation : trackOrientation
  const normalized = normalizeCameraMeta({
    cameraPreset: p.cameraPreset,
    videoRotation: p.videoRotation,
    rawOrientation
  }, p.track)
  if (normalized.videoOrientation !== 'unknown' && (
    p.videoOrientation !== normalized.videoOrientation ||
    Number(p.videoRotation || 0) !== normalized.videoRotation ||
    p.rawOrientation !== normalized.rawOrientation
  )) {
    updateParticipant(p.id, normalized)
    if (p.isLocal) publishLocalCameraMeta(p.track)
  }
}

function bindVideoOrientation(p, el) {
  if (!el || !p?.id) return
  if (el.__orepOrientationCleanup && el.__orepOrientationParticipant !== p.id) {
    el.__orepOrientationCleanup()
  }
  if (el.__orepOrientationParticipant !== p.id) {
    const update = () => refreshVideoOrientation(p, el)
    el.addEventListener('loadedmetadata', update)
    el.addEventListener('resize', update)
    el.__orepOrientationCleanup = () => {
      el.removeEventListener('loadedmetadata', update)
      el.removeEventListener('resize', update)
    }
    el.__orepOrientationParticipant = p.id
  }
  refreshVideoOrientation(p, el)
  setTimeout(() => refreshVideoOrientation(p, el), 120)
}

// ---- 聊天 ----
const chatMessages = ref([])
const chatInput = ref('')
const chatMessagesRef = ref(null)
const chatDecoder = new TextDecoder()
const chatEncoder = new TextEncoder()

// ---- 评分 ----
const scoreItems = ref([])
const scoreForm = reactive({ scores: {}, comments: {} })
const submitting = ref(false)
const totalScore = computed(() => Object.values(scoreForm.scores).reduce((s, v) => s + (Number(v) || 0), 0))
const maxTotalScore = computed(() => scoreItems.value.reduce((s, i) => s + (Number(i.maxScore) || 0), 0))
const scoreProgress = computed(() => {
  const max = Number(maxTotalScore.value) || 0
  if (max <= 0) return 0
  return Math.min(100, Math.max(0, Math.round((Number(totalScore.value) / max) * 100)))
})
const groupedScoreItems = computed(() => {
  const groups = {}
  scoreItems.value.forEach(item => {
    const cat = item.category || '其他'
    if (!groups[cat]) groups[cat] = { category: cat, items: [] }
    groups[cat].items.push(item)
  })
  return Object.values(groups)
})

// ---- 问题 ----
const issues = ref([])
const issueFilter = ref('all')
function isIssueResolved(issue) {
  return issue?.status === 1 || issue?.status === 'RESOLVED'
}
const pendingIssueCount = computed(() => issues.value.filter(issue => !isIssueResolved(issue)).length)
const resolvedIssueCount = computed(() => issues.value.filter(isIssueResolved).length)
const filteredIssues = computed(() => {
  if (issueFilter.value === 'open') return issues.value.filter(issue => !isIssueResolved(issue))
  if (issueFilter.value === 'resolved') return issues.value.filter(isIssueResolved)
  return issues.value
})

// ============ 连接 ============

async function connectRoom() {
  // 防止并发调用
  if (isConnecting) return
  isConnecting = true
  _connectId++
  const myId = _connectId

  const delays = [0, 1000, 2000, 4000, 8000] // 指数退避
  reconnecting.value = true
  reconnectAttempt.value = 0

  // 清理旧参与者（防止重复头像）
  participants.value = []
  screenShares.value = []
  videoRefs.clear()

  for (let attempt = 0; attempt < maxRetries; attempt++) {
    if (leavingMeeting || _connectId !== myId) { isConnecting = false; return }
    reconnectAttempt.value = attempt + 1
    reconnectText.value = attempt === 0 ? '正在加入路演...' : '正在重连...'
    if (delays[attempt] > 0) await sleep(delays[attempt])
    if (leavingMeeting || _connectId !== myId) { isConnecting = false; return }

    try {
      // 清理旧连接
      if (room) { try { room.disconnect() } catch {} room = null }

      const tokenUrl = '/api/livekit/token'
      const res = await request.get(tokenUrl, { params: { meetingId: meetingId.value } })
      const { token } = res.data

      // 走前端同源代理，避免依赖单独的 7882 LiveKit 代理进程。
      const connectUrl = `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/livekit`

      room = new Room({
        adaptiveStream: false,
        dynacast: true,
        singlePeerConnection: true,
        videoCaptureDefaults: { resolution: VideoPresets.h1080.resolution },
        screenShareCaptureDefaults: { resolution: ScreenSharePresets.h1080fps15.resolution },
      })

      room.on(RoomEvent.Connected, () => {
        connected.value = true
        reconnecting.value = false
        isConnecting = false
        updateParticipant('local', {
          name: currentUser.value,
          isLocal: true,
          hasVideo: false,
          hasAudio: false
        })
        room.remoteParticipants.forEach(addRemote)
        loadChatHistory()
      })

      // 断开时延迟重连（防抖，避免风暴）
      room.on(RoomEvent.Disconnected, () => {
        connected.value = false
        if (!leavingMeeting && _connectId === myId) {
          clearTimeout(_reconnectTimer)
          _reconnectTimer = setTimeout(() => {
            if (!isConnecting && !leavingMeeting) {
              connectRoom()
            }
          }, 2000)
        }
      })

      room.on(RoomEvent.ConnectionQualityChanged, (quality, participant) => {
        if (participant.isLocal) networkQuality.value = quality
      })

      room.on(RoomEvent.ActiveSpeakersChanged, syncActiveSpeakers)

    room.on(RoomEvent.ParticipantConnected, (p) => {
      addRemote(p)
      setTimeout(() => publishLocalCameraMeta(), 300)
    })
    room.on(RoomEvent.ParticipantDisconnected, (p) => {
      removeParticipant(p.sid)
      removeScreenShare(p.sid + ':screen')
      stopRemoteAudio(p.sid)
      stopRemoteAudio(p.sid + ':screen')
      removeHiddenParticipants()
    })

    room.on(RoomEvent.TrackSubscribed, (track, pub, participant) => {
      if (isHiddenParticipant(participant)) return
      // 跳过本机发布的屏幕共享音频（避免自己听到两遍）
      if (room.localParticipant && participant.sid === room.localParticipant.sid
        && isScreenShareAudioPublication(pub) && track.kind === 'audio') {
        return
      }
      if (track.kind === 'video') {
        const isScreenShare = pub.source === Track.Source.ScreenShare
        const id = isScreenShare ? participant.sid + ':screen' : participant.sid
        // 用当前选择的画质
        if (pub.setVideoQuality) {
          const qualityMap = { high: 'HIGH', medium: 'MEDIUM', low: 'LOW' }
          const q = qualityMap[videoQuality.value] || 'HIGH'
          try { pub.setVideoQuality(VideoQuality[q]) } catch {}
        }
        if (isScreenShare) {
          updateScreenShare(id, {
            ownerId: participant.sid,
            name: participant.name || participant.identity,
            isLocal: false,
            hasVideo: true,
            track
          })
        } else {
          updateParticipant(id, {
            name: participant.name || participant.identity,
            isLocal: false,
            hasVideo: true,
            track,
            source: 'camera'
          })
          applyCameraMeta(id, {}, track)
        }
        nextTick(() => {
          const el = videoRefs.get(id)
          if (el) track.attach(el)
        })
      } else if (track.kind === 'audio') {
        // 远端音频用自定义播放（比 SDK attach 更可靠）
        const isScreenShareAudio = isScreenShareAudioPublication(pub)
        const audioKey = isScreenShareAudio
          ? participant.sid + ':screen' : participant.sid
        playRemoteAudio(track, audioKey)
        if (!isScreenShareAudio) {
          updateParticipant(participant.sid, { hasAudio: true })
        }
      }
    })

    room.on(RoomEvent.TrackUnsubscribed, (track, pub, participant) => {
      if (isHiddenParticipant(participant)) return
      if (track.kind === 'video') {
        const isScreenShare = pub.source === Track.Source.ScreenShare
        if (isScreenShare) {
          removeScreenShare(participant.sid + ':screen')
        } else {
          updateParticipant(participant.sid, { hasVideo: false, track: null })
        }
      } else if (track.kind === 'audio') {
        const isScreenShareAudio = isScreenShareAudioPublication(pub)
        const audioKey = isScreenShareAudio
          ? participant.sid + ':screen' : participant.sid
        stopRemoteAudio(audioKey)
        if (!isScreenShareAudio) {
          updateParticipant(participant.sid, { hasAudio: false })
        }
      }
    })

    room.on(RoomEvent.TrackPublished, (pub, participant) => {
      if (isHiddenParticipant(participant)) return
      // 用当前选择的画质
      if (pub.setVideoQuality) {
        const qualityMap = { high: 'HIGH', medium: 'MEDIUM', low: 'LOW' }
        const q = qualityMap[videoQuality.value] || 'HIGH'
        try { pub.setVideoQuality(VideoQuality[q]) } catch {}
      }
      if (pub.track) {
        if (pub.track.kind === 'video') {
          const isScreenShare = pub.source === Track.Source.ScreenShare
          const id = isScreenShare ? participant.sid + ':screen' : participant.sid
          if (isScreenShare) {
            updateScreenShare(id, {
              ownerId: participant.sid,
              name: participant.name || participant.identity,
              isLocal: false,
              hasVideo: true,
              track: pub.track
            })
          } else {
            updateParticipant(id, {
              name: participant.name || participant.identity,
              isLocal: false,
              hasVideo: true,
              track: pub.track,
              source: 'camera'
            })
            applyCameraMeta(id, {}, pub.track)
          }
          nextTick(() => {
            const el = videoRefs.get(id)
            if (el) pub.track.attach(el)
          })
        } else if (!isScreenShareAudioPublication(pub)) {
          updateParticipant(participant.sid, { hasAudio: true })
        }
      }
    })

    // 本地轨道发布
    room.on(RoomEvent.LocalTrackPublished, (pub) => {
      if (pub.source === Track.Source.Camera && pub.track) {
        const localMeta = buildLocalCameraMeta(pub.track)
        updateParticipant('local', {
          name: currentUser.value,
          isLocal: true,
          hasVideo: true,
          track: pub.track,
          source: 'camera',
          ...localMeta
        })
        nextTick(() => {
          const el = videoRefs.get('local')
          if (el) pub.track.attach(el)
        })
        setTimeout(() => publishLocalCameraMeta(pub.track), 160)
        isCamOff.value = false
      } else if (pub.source === Track.Source.Microphone) {
        updateParticipant('local', { hasAudio: true })
        isMuted.value = false
      } else if (pub.source === Track.Source.ScreenShare && pub.track?.kind === 'video') {
        updateScreenShare('local:screen', {
          ownerId: 'local',
          name: currentUser.value,
          isLocal: true,
          hasVideo: true,
          track: pub.track
        })
        nextTick(() => {
          const el = videoRefs.get('local:screen')
          if (el) pub.track.attach(el)
        })
        isScreenSharing.value = true
      }
    })

    room.on(RoomEvent.LocalTrackUnpublished, (pub) => {
      if (pub.source === Track.Source.Camera) {
        updateParticipant('local', { hasVideo: false, track: null })
        isCamOff.value = true
      } else if (pub.source === Track.Source.Microphone) {
        updateParticipant('local', { hasAudio: false })
        isMuted.value = true
      } else if (pub.source === Track.Source.ScreenShare && pub.track?.kind === 'video') {
        removeScreenShare('local:screen')
        isScreenSharing.value = false
      }
    })

    // 聊天 DataChannel
    room.on(RoomEvent.DataReceived, (payload, participant) => {
      try {
        const data = JSON.parse(chatDecoder.decode(payload))
        if (data.type === 'chat') {
          chatMessages.value.push({
            sender: data.sender, content: data.content,
            type: data.msgType || 'text', fileName: data.fileName,
            time: new Date().toISOString()
          })
          scrollChat()
        } else if (data.type === 'camera-meta' && participant?.sid) {
          applyCameraMeta(participant.sid, data)
        }
      } catch {}
    })

      await room.connect(connectUrl, token)
      // 连接成功，传 room 给 AudioRecorder（用于录制摄像头/屏幕视频轨）
      audioRecorderRef.value?.setRoom(room)
      // 连接成功，不自动开启摄像头和麦克风
      nextTick(() => {
      })
      return // 成功退出重试循环
    } catch (err) {
      console.error(`连接尝试 ${reconnectAttempt.value} 失败:`, err)
      // 密码未验证，不重试，直接跳回加入页面
      if (err?.response?.status === 403 || err?.message?.includes('会议密码')) {
        reconnecting.value = false
        isConnecting = false
        clearVerifiedMeetingAccess()
        ElMessage.warning('请先输入路演密码')
        router.push('/online-meeting')
        return
      }
      if (reconnectAttempt.value < maxRetries) {
        reconnectText.value = '连接失败，正在重试...'
      }
    }
  }

  // 所有重试失败
  reconnecting.value = false
  isConnecting = false
  ElMessage.error('加入路演失败，请检查网络后重试')
}

function manualReconnect() {
  connectRoom()
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

// ============ 音频播放 ============

const _audioElements = new Map() // participantSid → HTMLAudioElement
const _audioResumeHandlers = new Map() // participantSid → click resume handler

/**
 * 播放远端音频：创建隐藏 <audio> 元素，挂到 DOM，set srcObject，play
 */
function playRemoteAudio(track, participantSid) {
  // 先清理旧的
  stopRemoteAudio(participantSid)

  const audioEl = document.createElement('audio')
  audioEl.autoplay = true
  audioEl.style.display = 'none'
  audioEl.setAttribute('data-participant', participantSid)
  // 防止屏幕共享音频在本地扬声器播放后被麦克风拾取（回声源之一）
  audioEl.volume = 1.0
  document.body.appendChild(audioEl)

  audioEl.srcObject = new MediaStream([track.mediaStreamTrack])
  audioEl.play().catch(err => {
    console.warn(`[Audio] 自动播放被阻止: ${participantSid}`, err)
    // 浏览器策略要求用户交互后播放
    const resume = () => {
      audioEl.play().catch(() => {})
      document.removeEventListener('click', resume)
      _audioResumeHandlers.delete(participantSid)
    }
    _audioResumeHandlers.set(participantSid, resume)
    document.addEventListener('click', resume)
  })

  _audioElements.set(participantSid, audioEl)
  // console.log(`[Audio] 远端音频已启动: ${participantSid}`)
}

/**
 * 停止远端音频
 */
function stopRemoteAudio(participantSid) {
  const resume = _audioResumeHandlers.get(participantSid)
  if (resume) {
    document.removeEventListener('click', resume)
    _audioResumeHandlers.delete(participantSid)
  }

  const audioEl = _audioElements.get(participantSid)
  if (!audioEl) return
  try {
    audioEl.srcObject = null
    audioEl.remove()
  } catch {}
  _audioElements.delete(participantSid)
}

function stopAllRemoteAudio() {
  Array.from(new Set([
    ..._audioElements.keys(),
    ..._audioResumeHandlers.keys()
  ])).forEach(stopRemoteAudio)
}

function addRemote(p) {
  if (isHiddenParticipant(p)) return

  updateParticipant(p.sid, {
    name: p.name || p.identity,
    isLocal: false,
    hasVideo: false,
    hasAudio: false
  })
  // 检查已有摄像头轨道
  const camPub = p.getTrackPublication(Track.Source.Camera)
  if (camPub?.track) {
    updateParticipant(p.sid, { hasVideo: true, track: camPub.track })
    applyCameraMeta(p.sid, {}, camPub.track)
    nextTick(() => {
      const el = videoRefs.get(p.sid)
      if (el) camPub.track.attach(el)
    })
  }
  // 检查已有麦克风轨道
  const micPub = p.getTrackPublication(Track.Source.Microphone)
  if (micPub?.track) {
    playRemoteAudio(micPub.track, p.sid)
    updateParticipant(p.sid, { hasAudio: true })
  }
  // 检查已有屏幕共享轨道
  const screenPub = p.getTrackPublication(Track.Source.ScreenShare)
  if (screenPub?.track) {
    updateScreenShare(p.sid + ':screen', {
      ownerId: p.sid,
      name: p.name || p.identity,
      isLocal: false,
      hasVideo: true,
      track: screenPub.track
    })
    nextTick(() => {
      const el = videoRefs.get(p.sid + ':screen')
      if (el) screenPub.track.attach(el)
    })
  }
  // 检查已有屏幕共享音频轨道（source=screen_share_audio）
  const screenAudioPub = [...(p.trackPublications || new Map()).values()]
    .find(pub => isScreenShareAudioPublication(pub))
  if (screenAudioPub?.track) {
    playRemoteAudio(screenAudioPub.track, p.sid + ':screen')
  }
}

// ============ 媒体控制 ============

async function toggleMic() {
  if (!room) return
  if (isMuted.value) {
    try {
      // 显式启用回声消除、噪声抑制、自动增益
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          channelCount: 1,
          sampleRate: 48000
        }
      })
      const track = stream.getAudioTracks()[0]
      await room.localParticipant.publishTrack(track, { source: Track.Source.Microphone })
      isMuted.value = false
    } catch {
      ElMessage.warning('无法开启麦克风')
    }
  } else {
    const micPub = room.localParticipant.getTrackPublication(Track.Source.Microphone)
    if (micPub) {
      micPub.track.stop()
      await room.localParticipant.unpublishTrack(micPub.track)
    }
    isMuted.value = true
  }
}

async function toggleCam() {
  if (!room) return
  if (isCamOff.value) {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: getCameraConstraints()
      })
      const track = stream.getVideoTracks()[0]
      await room.localParticipant.publishTrack(track, { source: Track.Source.Camera })
      applyCameraMeta('local', buildLocalCameraMeta(track), track)
      setTimeout(() => publishLocalCameraMeta(track), 180)
      isCamOff.value = false
    } catch {
      ElMessage.warning('无法开启摄像头')
    }
  } else {
    const camPub = room.localParticipant.getTrackPublication(Track.Source.Camera)
    if (camPub) {
      camPub.track.stop()
      await room.localParticipant.unpublishTrack(camPub.track)
    }
    isCamOff.value = true
  }
}

async function switchCamera() {
  if (!room) return
  const previousFacing = currentFacing.value
  const nextFacing = previousFacing === 'user' ? 'environment' : 'user'
  await switchCameraFacing(nextFacing, nextFacing === 'environment' ? rearCameraRatio.value : rearCameraRatio.value, previousFacing)
}

async function switchCameraFacing(nextFacing, nextRatio = rearCameraRatio.value, fallbackFacing = currentFacing.value) {
  const previousFacing = fallbackFacing
  const previousRatio = rearCameraRatio.value
  currentFacing.value = nextFacing
  if (nextFacing === 'environment') {
    rearCameraRatio.value = nextRatio === 'landscape' ? 'landscape' : 'portrait'
    mobileStageMode.value = rearCameraRatio.value
  } else {
    mobileStageMode.value = 'auto'
  }
  await applyDeviceOrientationForCamera(nextFacing, rearCameraRatio.value)

  const camPub = room?.localParticipant.getTrackPublication(Track.Source.Camera)
  if (!camPub?.track) {
    const ratioText = nextFacing === 'environment'
      ? (rearCameraRatio.value === 'landscape' ? '后置宽屏' : '后置竖屏')
      : '前置摄像头'
    ElMessage.info(`下次开启${ratioText}`)
    return
  }

  try {
    camPub.track.stop()
    await room.localParticipant.unpublishTrack(camPub.track)
    const stream = await navigator.mediaDevices.getUserMedia({
      video: getCameraConstraints(videoQuality.value, nextFacing, rearCameraRatio.value)
    })
    const newTrack = stream.getVideoTracks()[0]
    await room.localParticipant.publishTrack(newTrack, { source: Track.Source.Camera })
    publishLocalCameraMeta(newTrack)
    ElMessage.success(nextFacing === 'environment'
      ? `已切换后置${rearCameraRatio.value === 'landscape' ? '宽屏' : '竖屏'}`
      : '已切换前置摄像头')
  } catch {
    currentFacing.value = previousFacing
    rearCameraRatio.value = previousRatio
    ElMessage.warning('切换摄像头失败')
  }
}

async function toggleScreen() {
  if (!room) return
  if (isScreenSharing.value) {
    // 停止视频轨道
    const screenPub = room.localParticipant.getTrackPublication(Track.Source.ScreenShare)
    if (screenPub) {
      screenPub.track.stop()
      await room.localParticipant.unpublishTrack(screenPub.track)
    }
    // 停止屏幕共享音频轨道
    for (const pub of room.localParticipant.trackPublications.values()) {
      if (isScreenShareAudioPublication(pub)) {
        pub.track.stop()
        await room.localParticipant.unpublishTrack(pub.track)
      }
    }
    isScreenSharing.value = false
    // 恢复麦克风（如果之前因屏幕共享音频而被静音）
    if (_micMutedByScreenShare) {
      _micMutedByScreenShare = false
      await toggleMic()
      ElMessage.info('已恢复麦克风')
    }
  } else {
    // 检查是否已有其他人共享屏幕
    const otherScreen = screenShares.value.find(p => p.id !== 'local:screen')
    if (otherScreen) {
      ElMessage.warning('有人正在共享屏幕，请等待对方结束后再共享')
      return
    }
    try {
      // 手动捕获高分辨率屏幕流（含音频）
      const stream = await navigator.mediaDevices.getDisplayMedia({
        video: {
          width: { ideal: 1920, max: 1920 },
          height: { ideal: 1080, max: 1080 },
          frameRate: { ideal: 15, max: 30 }
        },
        audio: {
          echoCancellation: false,  // 系统音频不需要回声消除
          noiseSuppression: false,
          autoGainControl: false
        }
      })
      const videoTrack = stream.getVideoTracks()[0]
      const audioTrack = stream.getAudioTracks()[0]

      // 将屏幕共享视频轨传给录制器（用于音视频融合分析）

      // 用户点击浏览器停止共享按钮时自动处理
      videoTrack.addEventListener('ended', () => {
        isScreenSharing.value = false
        if (audioTrack) audioTrack.stop()
        // 恢复麦克风
        if (_micMutedByScreenShare) {
          _micMutedByScreenShare = false
          toggleMic()
        }
      })

      // 发布视频轨道
      await room.localParticipant.publishTrack(videoTrack, {
        source: Track.Source.ScreenShare,
        videoEncoding: { maxBitrate: 3_000_000, maxFramerate: 30 },
        videoSimulcastLayers: [
          { width: 1920, height: 1080, quality: 2, fps: 15 },
          { width: 1280, height: 720, quality: 1, fps: 15 },
          { width: 640, height: 360, quality: 0, fps: 15 },
        ]
      })

      // 如果浏览器提供了音频轨道（共享标签页/屏幕时勾选了"共享音频"），也发布音频
      if (audioTrack) {
        checkScreenAudioAudible(audioTrack)
        await room.localParticipant.publishTrack(audioTrack, {
          source: Track.Source.ScreenShareAudio
        })
        // console.log('[ScreenShare] 屏幕共享音频已发布')

        // 关键修复：屏幕共享音频与麦克风同时存在会产生回声反馈
        // 自动静音麦克风，停止共享时自动恢复
        if (!isMuted.value) {
          const micPub = room.localParticipant.getTrackPublication(Track.Source.Microphone)
          if (micPub) {
            micPub.track.stop()
            await room.localParticipant.unpublishTrack(micPub.track)
            isMuted.value = true
            _micMutedByScreenShare = true
            ElMessage.info('已自动静音麦克风（防止回声），停止屏幕共享后将自动恢复')
          }
        }
      } else {
        ElMessage.warning('未检测到屏幕共享音频，录制回放可能没有系统声音')
      }
    } catch {
      ElMessage.warning('无法开启屏幕共享')
    }
  }
}

// ============ 清晰度设置 ============

const qualityMap = {
  low: { width: 640, height: 360 },
  medium: { width: 1280, height: 720 },
  high: { width: 1920, height: 1080 }
}

async function changeQuality(val) {
  if (!room) return
  videoQuality.value = val

  let changed = false

  // 本地摄像头切换分辨率
  const camPub = room.localParticipant.getTrackPublication(Track.Source.Camera)
  if (camPub?.track) {
    try {
      camPub.track.stop()
      await room.localParticipant.unpublishTrack(camPub.track)
      const stream = await navigator.mediaDevices.getUserMedia({
        video: getCameraConstraints(val)
      })
      const newTrack = stream.getVideoTracks()[0]
      // console.log('切换画质:', val, '实际分辨率:', newTrack.getSettings())
      await room.localParticipant.publishTrack(newTrack, { source: Track.Source.Camera })
      changed = true
    } catch (err) {
      console.error('切换清晰度失败:', err)
    }
  }

  // 远端屏幕共享订阅画质
  room.remoteParticipants.forEach(p => {
    const screenPub = p.getTrackPublication(Track.Source.ScreenShare)
    if (screenPub?.isSubscribed && screenPub.setVideoQuality) {
      const qualityMap = { high: 'HIGH', medium: 'MEDIUM', low: 'LOW' }
      try { screenPub.setVideoQuality(VideoQuality[qualityMap[val] || 'HIGH']) } catch {}
      changed = true
    }
  })

  if (changed) {
    ElMessage.success(`清晰度已切换至 ${qualityLabels[val]}`)
  }
}

// 网络质量文字
function getNetText(quality) {
  if (quality === ConnectionQuality.Excellent) return '优良'
  if (quality === ConnectionQuality.Good) return '良好'
  if (quality === ConnectionQuality.Poor) return '差'
  return '未知'
}

function getNetColor(quality) {
  if (quality === ConnectionQuality.Excellent) return '#52c41a'
  if (quality === ConnectionQuality.Good) return '#faad14'
  if (quality === ConnectionQuality.Poor) return '#ff4d4f'
  return '#888'
}

// ============ 聊天 ============

function sendChat() {
  if (!chatInput.value.trim() || !room) return
  const text = chatInput.value.trim()
  const msg = JSON.stringify({
    type: 'chat', sender: currentUser.value, content: text, msgType: 'text'
  })
  room.localParticipant.publishData(chatEncoder.encode(msg), { reliable: true })
  const chatMsg = { sender: currentUser.value, content: text, type: 'text', time: new Date().toISOString() }
  chatMessages.value.push(chatMsg)
  chatInput.value = ''
  scrollChat()
  // 持久化到后端
  saveChatToDb('text', text)
}

function scrollChat() {
  nextTick(() => { if (chatMessagesRef.value) chatMessagesRef.value.scrollTop = chatMessagesRef.value.scrollHeight })
}

// 聊天消息持久化
async function saveChatToDb(type, content, fileName) {
  try {
    await request.post('/api/chat/send', {
      meetingId: meetingId.value, sender: currentUser.value,
      messageType: type, content, fileName
    })
  } catch {}
}

async function loadChatHistory() {
  try {
    const res = await request.get('/api/chat/history', { params: { meetingId: meetingId.value } })
    const msgs = res.data || res
    if (Array.isArray(msgs)) {
      chatMessages.value = msgs.map(m => ({
        sender: m.senderName, content: m.content,
        type: m.messageType, fileName: m.fileName,
        time: m.createdAt
      }))
      scrollChat()
    }
  } catch {}
}

async function uploadHandler(options, msgType) {
  const fd = new FormData()
  fd.append('file', options.file)
  fd.append('category', msgType === 'image' ? 'chat-image' : 'chat-file')
  try {
    const res = await request.post('/api/upload', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
    const data = res.data || res, url = typeof data === 'string' ? data : (data.url || '')
    if (!url) { ElMessage.error('上传失败'); return }
    // 构建完整 URL（相对路径需要拼接 origin）
    const fullUrl = url.startsWith('http') ? url : url
    const msg = JSON.stringify({ type: 'chat', sender: currentUser.value, content: fullUrl, msgType, fileName: options.file.name })
    room.localParticipant.publishData(chatEncoder.encode(msg), { reliable: true })
    chatMessages.value.push({ sender: currentUser.value, content: fullUrl, type: msgType, fileName: options.file.name, time: new Date().toISOString() })
    scrollChat()
    saveChatToDb(msgType, fullUrl, options.file.name)
  } catch { ElMessage.error('上传失败') }
}

const uploadImage = (opts) => uploadHandler(opts, 'image')
const uploadDoc = (opts) => uploadHandler(opts, 'file')

// ============ 评分 ============

async function loadScoreItems() {
  try {
    const res = await request.get('/api/score/items')
    scoreItems.value = res.data || []
    scoreItems.value.forEach(item => { scoreForm.scores[item.id] = 0; scoreForm.comments[item.id] = '' })
  } catch {}
}

async function submitScore() {
  submitting.value = true
  try {
    const scores = scoreItems.value.map(item => ({
      itemId: item.id, score: scoreForm.scores[item.id] || 0, comment: scoreForm.comments[item.id] || ''
    }))
    await request.post('/api/score/submit', { meetingId: Number(meetingId.value), scores })
    ElMessage.success('评分提交成功')
  } catch { ElMessage.error('提交失败') }
  finally { submitting.value = false }
}

async function loadIssues() {
  try {
    const res = await request.get('/api/issue/list', { params: { meetingId: meetingId.value } })
    issues.value = res.data || []
  } catch {}
}

async function resolveIssue(issue) {
  if (!issue?.id) return
  try {
    await request.post('/api/issue/resolve', { issueId: issue.id, meetingId: Number(meetingId.value) })
    ElMessage.success('问题已标记为解决')
    await loadIssues()
  } catch {
    ElMessage.error('处理问题失败')
  }
}

async function loadMeeting() {
  try {
    // 检查是否已通过密码验证（从 OnlineMeeting 页面跳转时设置）
    if (!hasVerifiedMeetingAccess()) {
      ElMessage.warning('请先输入路演密码')
      router.push('/online-meeting')
      return
    }
    const res = await request.get(`/api/meeting/${meetingId.value}`)
    meetingInfo.value = res.data
    startCountdown()
    await connectRoom()
    await refreshServerRecordingStatus()
  } catch (err) { console.warn('加载会议失败:', err) }
}

async function toggleServerRecording() {
  if (isRecordingLoading.value) return
  if (!connected.value) {
    ElMessage.warning('路演连接后才能录制')
    return
  }
  if (isRecording.value) {
    await stopServerRecording()
  } else {
    await startServerRecording()
  }
}

async function startServerRecording() {
  isRecordingLoading.value = true
  try {
    const res = await request.post('/api/recording/start', { meetingId: Number(meetingId.value) })
    const recording = res.data?.recording
    recordingDbId.value = recording?.id || res.data?.recordingId || null
    isRecording.value = true
    startRecordingStatusPolling()
    ElMessage.success('路演录制已开始')
  } catch (err) {
    isRecording.value = false
  } finally {
    isRecordingLoading.value = false
  }
}

async function stopServerRecording() {
  isRecordingLoading.value = true
  try {
    await request.post('/api/recording/stop', { meetingId: Number(meetingId.value) })
    isRecording.value = false
    ElMessage.success('录制已停止，正在生成回放')
    startRecordingStatusPolling()
  } finally {
    isRecordingLoading.value = false
  }
}

async function refreshServerRecordingStatus() {
  try {
    const res = await request.get(`/api/recording/status/${meetingId.value}`)
    const status = res.data?.status
    const recording = res.data?.recording
    recordingDbId.value = recording?.id || null
    isRecording.value = ['STARTING', 'RECORDING'].includes(status)
    if (['STARTING', 'RECORDING', 'PROCESSING'].includes(status)) {
      startRecordingStatusPolling()
    } else {
      stopRecordingStatusPolling()
    }
  } catch {}
}

function startRecordingStatusPolling() {
  if (recordingStatusTimer) return
  recordingStatusTimer = setInterval(refreshServerRecordingStatus, 5000)
}

function stopRecordingStatusPolling() {
  if (recordingStatusTimer) {
    clearInterval(recordingStatusTimer)
    recordingStatusTimer = null
  }
}

// ============ 录制：AudioRecorder 处理音频，本函数录制摄像头+屏幕视频 ============
let _camRec = null, _screenRec = null
let _camChunks = [], _screenChunks = []

function startVideoCapture() {
  if (!room) return
  const vp = room.localParticipant
  let mime = ''
  for (const t of ['video/webm;codecs=vp9','video/webm;codecs=vp8','video/webm']) {
    if (MediaRecorder.isTypeSupported(t)) { mime = t; break }
  }
  const camPub = vp.getTrackPublication(Track.Source.Camera)
  if (camPub?.track?.mediaStreamTrack) {
    const s = new MediaStream([camPub.track.mediaStreamTrack])
    _camRec = new MediaRecorder(s, { mimeType: mime, videoBitsPerSecond: 4000000 })
    _camChunks = []
    _camRec.ondataavailable = e => { if (e.data.size > 0) _camChunks.push(e.data) }
    _camRec.start(1000)
  }
  const screenPub = vp.getTrackPublication(Track.Source.ScreenShare)
  if (screenPub?.track?.mediaStreamTrack) {
    const s = new MediaStream([screenPub.track.mediaStreamTrack])
    _screenRec = new MediaRecorder(s, { mimeType: mime, videoBitsPerSecond: 5000000 })
    _screenChunks = []
    _screenRec.ondataavailable = e => { if (e.data.size > 0) _screenChunks.push(e.data) }
    _screenRec.start(1000)
  }
}

function stopVideoCapture() {
  const camRecorder = _camRec
  const screenRecorder = _screenRec
  const camChunks = [..._camChunks]
  const screenChunks = [..._screenChunks]

  // 停止录制器
  const promises = []
  if (camRecorder && camRecorder.state === 'recording') {
    promises.push(new Promise(resolve => {
      camRecorder.onstop = resolve
      camRecorder.stop()
    }))
  }
  if (screenRecorder && screenRecorder.state === 'recording') {
    promises.push(new Promise(resolve => {
      screenRecorder.onstop = resolve
      screenRecorder.stop()
    }))
  }

  _camRec = _screenRec = null
  _camChunks = _screenChunks = []

  // 等录制器完全停止后，上传到 MinIO
  Promise.all(promises).then(() => {
    const audioBlob = audioRecorderRef.value?.getRecorder?.()?.getRecordedBlob?.() || null
    const cameraBlob = camChunks.length > 0 ? new Blob(camChunks, { type: 'video/webm' }) : null
    const screenBlob = screenChunks.length > 0 ? new Blob(screenChunks, { type: 'video/webm' }) : null

    if (!cameraBlob && !screenBlob && !audioBlob) return

    const formData = new FormData()
    formData.append('meeting_id', String(meetingId.value))
    formData.append('camera_preset', localCameraMeta.value.cameraPreset)
    formData.append('camera_orientation', localCameraMeta.value.videoOrientation)
    formData.append('camera_raw_orientation', localCameraMeta.value.rawOrientation)
    formData.append('camera_rotation', String(localCameraMeta.value.videoRotation || 0))
    if (cameraBlob) formData.append('camera', cameraBlob, `camera_${meetingId.value}.webm`)
    if (screenBlob) formData.append('screen', screenBlob, `screen_${meetingId.value}.webm`)
    if (audioBlob) formData.append('audio', audioBlob, `audio_${meetingId.value}.webm`)

    // 后台上传到 MinIO（不影响主流程）
    request.post('/api/recording/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    }).then(res => {
      // console.log('[Recording] 文件已保存到 MinIO:', res.data?.recordingId)
    }).catch(err => {
      // console.warn('[Recording] MinIO 保存失败:', err.message)
    })
  })
}

function onRecordingStatus(s) {
  // AudioRecorder 组件开始录制时 → 同时录制摄像头+屏幕视频
  // AI 评分开始 → 自动重新开始计时；结束评分 → 自动暂停计时
  if (s === 'recording') {
    startVideoCapture()
    stageTimerAutoOwned = true
    startStageTimer({ reset: true })
  } else if (s === 'stopping') {
    stopVideoCapture()
    if (stageTimerAutoOwned) {
      pauseStageTimer()
      stageTimerAutoOwned = false
    }
  } else if (s === 'upload_failed' || s === 'idle') {
    if (stageTimerAutoOwned) {
      pauseStageTimer()
      stageTimerAutoOwned = false
    }
  }
}

// ============ 舞台计时 ============
function formatStageTimer(totalSeconds) {
  const sec = Math.max(0, Number(totalSeconds) || 0)
  const h = Math.floor(sec / 3600)
  const m = Math.floor((sec % 3600) / 60)
  const s = sec % 60
  if (h > 0) {
    return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  }
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

function clearStageTimerInterval() {
  if (stageTimerInterval) {
    clearInterval(stageTimerInterval)
    stageTimerInterval = null
  }
}

function startStageTimer({ reset = false } = {}) {
  if (reset) stageTimerSeconds.value = 0
  if (stageTimerRunning.value) return
  stageTimerRunning.value = true
  clearStageTimerInterval()
  stageTimerInterval = setInterval(() => {
    stageTimerSeconds.value += 1
  }, 1000)
}

function pauseStageTimer() {
  stageTimerRunning.value = false
  clearStageTimerInterval()
}

function toggleStageTimer() {
  // Manual control takes ownership away from auto AI linkage until next AI start
  if (stageTimerRunning.value) {
    pauseStageTimer()
    stageTimerAutoOwned = false
    return
  }
  stageTimerAutoOwned = false
  startStageTimer({ reset: stageTimerSeconds.value === 0 })
}

function resetStageTimer() {
  clearStageTimerInterval()
  stageTimerRunning.value = false
  stageTimerSeconds.value = 0
  stageTimerAutoOwned = false
}

// ============ 离开 ============

// ============ 全屏 ============
function toggleFullscreen() {
  const el = document.querySelector('.meeting-room')
  if (!document.fullscreenElement) {
    el?.requestFullscreen?.()
  } else {
    document.exitFullscreen?.()
  }
}

// ============ 屏幕布局 & 钉选 ============
function cycleScreenLayout() {
  const layouts = ['default', 'dual', 'multi']
  const idx = layouts.indexOf(screenLayout.value)
  screenLayout.value = layouts[(idx + 1) % layouts.length]
  // 切回默认时清除钉选
  if (screenLayout.value === 'default') pinnedCamera.value = null
}

function toggleMobileStageMode() {
  const modes = ['auto', 'landscape', 'portrait']
  const idx = modes.indexOf(mobileStageMode.value)
  mobileStageMode.value = modes[(idx + 1) % modes.length]
}

async function handleMobileMoreCommand(command) {
  const value = String(command)
  if (value === 'screen') return toggleScreen()
  if (value === 'record') return toggleServerRecording()
  if (value === 'chat') {
    showChat.value = !showChat.value
    if (showChat.value) showScore.value = false
    return
  }
  if (value === 'score') {
    showScore.value = !showScore.value
    if (showScore.value) showChat.value = false
    return
  }
  if (value === 'issues') {
    showIssues.value = !showIssues.value
    return
  }
  if (value === 'layout') return cycleScreenLayout()
  if (value.startsWith('camera-mode:')) return applyCameraPreset(value.replace('camera-mode:', ''))
  if (value === 'stage-mode') return toggleMobileStageMode()
  if (value === 'camera-facing') return switchCamera()
  if (value.startsWith('rear-ratio:')) {
    const rawRatio = value.replace('rear-ratio:', '')
    const ratio = rawRatio === 'landscape' ? 'landscape' : 'portrait'
    return switchCameraFacing('environment', ratio)
  }
  if (value === 'fullscreen') return toggleFullscreen()
  if (value.startsWith('quality:')) return changeQuality(value.replace('quality:', ''))
}

function pinCamera(participantId) {
  const participant = participants.value.find(p => p.id === participantId)
  if (!participant?.hasVideo) return
  if (isScreenShareOwner(participantId)) {
    unpinCamera()
    return
  }
  // 双击钉选/取消钉选
  if (pinnedCamera.value === participantId) {
    unpinCamera()
  } else {
    pinnedCamera.value = participantId
    if (screenLayout.value === 'default') screenLayout.value = 'dual'
  }
}

function unpinCamera() {
  pinnedCamera.value = null
  screenLayout.value = 'default'
}

function cleanupTeleportedMeetingUi() {
  document.querySelectorAll('.meeting-quality-popper').forEach(el => el.remove())
  document.querySelectorAll('.meeting-mobile-more-popper').forEach(el => el.remove())
  document.querySelectorAll('.el-overlay').forEach(overlay => {
    if (overlay.querySelector('.issues-drawer')) overlay.remove()
  })
  document.body.classList.remove('el-popup-parent--hidden')
  document.body.style.removeProperty('overflow')
  document.body.style.removeProperty('padding-right')
}

async function unpublishLocalTracks() {
  if (!room?.localParticipant) return
  const publications = Array.from(room.localParticipant.trackPublications.values())
  for (const pub of publications) {
    const track = pub.track
    if (!track) continue
    try {
      await room.localParticipant.unpublishTrack(track)
    } catch {}
    try {
      track.stop()
    } catch {}
  }
  removeScreenShare('local:screen')
  updateParticipant('local', { hasVideo: false, hasAudio: false, track: null })
  isScreenSharing.value = false
  isCamOff.value = true
  isMuted.value = true
}

function stopLocalTracksSync() {
  if (!room?.localParticipant) return
  const publications = Array.from(room.localParticipant.trackPublications.values())
  publications.forEach(pub => {
    try { pub.track?.stop?.() } catch {}
  })
}

async function cleanupMeetingSession({ exitFullscreen = true } = {}) {
  leavingMeeting = true
  if (screenAudioCheckTimer) clearTimeout(screenAudioCheckTimer)
  clearStageTimerInterval()
  stageTimerRunning.value = false
  stageTimerAutoOwned = false
  isConnecting = false
  _connectId++
  _micMutedByScreenShare = false
  clearTimeout(_reconnectTimer)
  reconnecting.value = false
  showChat.value = false
  showScore.value = false
  showIssues.value = false
  showProgress.value = false
  pinnedCamera.value = null
  screenLayout.value = 'default'
  stopRecordingStatusPolling()
  stopAllRemoteAudio()
  await unpublishLocalTracks()
  if (room) { try { room.disconnect() } catch {} room = null }
  cleanupTeleportedMeetingUi()
  if (exitFullscreen && document.fullscreenElement) {
    await document.exitFullscreen?.().catch(() => {})
  }
}

async function leaveMeeting() {
  if (leavingMeeting) return
  const leavingMeetingId = route.params.id
  await cleanupMeetingSession()
  clearVerifiedMeetingAccess()
  // 调用后端记录离开时间和时长
  request.post(`/api/meeting/${leavingMeetingId}/leave`).catch(() => {})
  await nextTick()
  router.push('/online-meeting')
}

function startCountdown() {
  // legacy no-op: remaining countdown replaced by stage stopwatch
}

function formatTime(t) {
  if (!t) return ''
  return new Date(t).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function formatDateTime(t) {
  if (!t) return ''
  return new Date(t).toLocaleString('zh-CN')
}

// ============ 生命周期 ============

function handleFullscreenChange() {
  isFullscreen.value = !!document.fullscreenElement
}

function observeVideoArea() {
  if (!videoAreaRef.value || typeof ResizeObserver === 'undefined') {
    const rect = videoAreaRef.value?.getBoundingClientRect?.()
    if (rect) videoAreaSize.value = { width: rect.width, height: rect.height }
    return
  }
  videoAreaObserver?.disconnect?.()
  videoAreaObserver = new ResizeObserver(entries => {
    const rect = entries[0]?.contentRect
    if (!rect) return
    videoAreaSize.value = { width: rect.width, height: rect.height }
  })
  videoAreaObserver.observe(videoAreaRef.value)
}

onMounted(async () => {
  await loadMeeting()
  await loadScoreItems()
  await loadIssues()
  await nextTick()
  observeVideoArea()
  document.addEventListener('fullscreenchange', handleFullscreenChange)
  // 关闭页面时记录离开
  window.addEventListener('beforeunload', handleBeforeUnload)
})

function handleBeforeUnload() {
  stopLocalTracksSync()
  if (room) { try { room.disconnect() } catch {} room = null }
  const meetingId = route.params.id
  const token = getUserToken()
  if (meetingId && token) {
    fetch(`/api/meeting/${meetingId}/leave`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
      keepalive: true
    }).catch(() => {})
  }
}

onUnmounted(() => {
  cleanupMeetingSession({ exitFullscreen: true })
  videoAreaObserver?.disconnect?.()
  videoAreaObserver = null
  document.removeEventListener('fullscreenchange', handleFullscreenChange)
  window.removeEventListener('beforeunload', handleBeforeUnload)
})
</script>

<style scoped>
/* ==================== 整体布局 ==================== */
.meeting-room {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #1a1a1a;
  color: #fff;
  overflow: hidden;
}
.meeting-room:fullscreen {
  height: 100vh;
  background: #1a1a1a;
}

/* ==================== 重连遮罩 ==================== */
.reconnect-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,.65);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}
.reconnect-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  background: #2b2b2b;
  border-radius: 16px;
  padding: 32px 40px;
  min-width: 200px;
  box-shadow: 0 8px 32px rgba(0,0,0,.4);
}
.reconnect-spinner {
  width: 36px;
  height: 36px;
  border: 3px solid #444;
  border-top-color: #1677ff;
  border-radius: 50%;
  animation: spin .8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.reconnect-text {
  font-size: 15px;
  color: #fff;
  font-weight: 500;
}
.reconnect-hint {
  font-size: 12px;
  color: #888;
}

/* ==================== 顶栏 ==================== */
.room-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
  height: 48px;
  background: #2b2b2b;
  flex-shrink: 0;
  z-index: 10;
}
.header-left { display: flex; align-items: center; gap: 10px; }
.meeting-title { font-size: 15px; font-weight: 500; }
.header-right { display: flex; align-items: center; gap: 16px; }
.participant-num {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: #aaa;
}
.countdown-pill {
  background: rgba(250, 173, 20, .15);
  border: 1px solid rgba(250, 173, 20, .4);
  border-radius: 16px;
  padding: 3px 12px;
}
.countdown-time {
  font-size: 14px;
  font-weight: 600;
  color: #faad14;
  font-variant-numeric: tabular-nums;
}

/* 网络状态 */
.net-status {
  display: flex;
  align-items: center;
  gap: 5px;
}
.signal-bars {
  display: flex;
  align-items: flex-end;
  gap: 2px;
  height: 14px;
}
.bar {
  display: block;
  width: 4px;
  border-radius: 1px;
  background: #555;
}
.b1 { height: 4px; }
.b2 { height: 9px; }
.b3 { height: 14px; }
/* 按网络质量亮灯 */
.signal-bars[data-level="1"] .b1 { background: #ff4d4f; }
.signal-bars[data-level="2"] .b1, .signal-bars[data-level="2"] .b2 { background: #faad14; }
.signal-bars[data-level="3"] .b1, .signal-bars[data-level="3"] .b2, .signal-bars[data-level="3"] .b3 { background: #52c41a; }
.net-text {
  font-size: 12px;
  font-variant-numeric: tabular-nums;
}

/* ==================== 主体 ==================== */
.room-body {
  flex: 1;
  display: flex;
  min-height: 0;
  position: relative;
}

/* ==================== 视频区域 ==================== */
.video-area {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 12px;
  min-height: 0;
  overflow: hidden;
}

/* ==================== 屏幕共享布局 ==================== */
.screen-share-layout {
  display: flex;
  gap: 10px;
  width: 100%;
  height: 100%;
  position: relative;
}
.screen-main {
  flex: 1;
  min-width: 0;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}
.screen-tile {
  position: relative;
  width: 100%;
  height: 100%;
  background: #111;
  border-radius: 12px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}
.screen-tile video {
  width: 100%;
  height: 100%;
  object-fit: contain;
}
.screen-sidebar {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 160px;
  flex-shrink: 0;
  min-height: 0;
  max-height: 100%;
  overflow-y: auto;
  overscroll-behavior: contain;
}
.screen-sidebar::-webkit-scrollbar,
.dual-sidebar::-webkit-scrollbar {
  width: 4px;
}
.screen-sidebar::-webkit-scrollbar-thumb,
.dual-sidebar::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, .24);
  border-radius: 999px;
}
.sidebar-toggle {
  position: absolute;
  right: 0;
  top: 50%;
  transform: translateY(-50%);
  background: rgba(0,0,0,.5);
  color: #fff;
  width: 20px;
  height: 48px;
  border-radius: 4px 0 0 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 5;
  font-size: 14px;
}
.sidebar-toggle.collapsed {
  right: 0;
}
.sidebar-toggle:hover {
  background: rgba(0,0,0,.7);
}
.sidebar-tile {
  position: relative;
  width: 160px;
  height: 120px;
  background: #333;
  border-radius: 8px;
  overflow: hidden;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}
.sidebar-tile video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.sidebar-tile .avatar-block {
  width: 40px;
  height: 40px;
}
.sidebar-tile .avatar-text {
  font-size: 16px;
}
.sidebar-tile .tile-info {
  padding: 4px 8px;
}
.sidebar-tile .tile-name {
  font-size: 11px;
}
.sidebar-tile .icon-muted {
  font-size: 11px;
}

/* ===== 双画面布局 ===== */
.screen-share-layout.layout-dual {
  flex-direction: row;
}
.dual-main {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}
.dual-tile {
  position: relative;
  width: 100%;
  height: 100%;
  background: #111;
  border-radius: 12px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}
.dual-tile video {
  width: 100%;
  height: 100%;
  object-fit: contain;
}
.dual-pinned {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}
.dual-sidebar {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100px;
  flex-shrink: 0;
  min-height: 0;
  max-height: 100%;
  overflow-y: auto;
  overscroll-behavior: contain;
}
.sidebar-tile-sm {
  position: relative;
  width: 100px;
  height: 75px;
  background: #333;
  border-radius: 8px;
  overflow: hidden;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  border: 2px solid transparent;
}
.sidebar-tile-sm:hover {
  border-color: #1677ff;
}
.sidebar-tile-sm video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.sidebar-tile-sm .avatar-block {
  width: 30px;
  height: 30px;
}
.sidebar-tile-sm .avatar-text {
  font-size: 12px;
}
.sidebar-tile-sm .tile-info {
  padding: 2px 4px;
}
.sidebar-tile-sm .tile-name {
  font-size: 10px;
}

/* ===== 多画面布局 ===== */
.screen-share-layout.layout-multi {
  flex-direction: column;
}
.multi-main {
  flex: 2;
  min-height: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}
.multi-tile {
  position: relative;
  width: 100%;
  height: 100%;
  background: #111;
  border-radius: 12px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}
.multi-tile video {
  width: 100%;
  height: 100%;
  object-fit: contain;
}
.multi-cameras {
  flex: 1;
  min-height: 0;
  display: grid;
  gap: 8px;
  padding: 4px;
  grid-auto-flow: column;
  grid-auto-columns: minmax(120px, 1fr);
  overflow-x: auto;
  overscroll-behavior-x: contain;
}
.multi-tile-small {
  position: relative;
  background: #333;
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  border: 2px solid transparent;
  min-width: 120px;
  min-height: 80px;
  aspect-ratio: 16/9;
}
.multi-tile-small:hover {
  border-color: #1677ff;
}
.multi-tile-small.is-pinned {
  border-color: #1677ff;
}
.multi-tile-small video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.multi-tile-small .avatar-block {
  width: 30px;
  height: 30px;
}
.multi-tile-small .avatar-text {
  font-size: 12px;
}
.multi-tile-small .tile-info {
  padding: 2px 4px;
}
.multi-tile-small .tile-name {
  font-size: 10px;
}

/* ==================== 网格布局 ==================== */
.video-grid {
  display: grid;
  gap: 8px;
  width: 100%;
  height: 100%;
  padding: 4px;
}
/* 单人：居中大画面 */
.video-grid .video-tile:only-child {
  width: 100%;
  max-width: 640px;
  max-height: 100%;
  margin: auto;
}

/* ==================== 视频瓦片 ==================== */
.video-tile {
  position: relative;
  background: #333;
  border-radius: 10px;
  overflow: hidden;
  min-height: 0;
  min-width: 0;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}
.video-tile video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.video-tile.video-rotate-90 video,
.video-tile.video-rotate-270 video {
  transform-origin: center;
  object-fit: contain;
}

.video-tile.video-rotate-90 video {
  transform: rotate(90deg) scale(1.78);
}

.video-tile.video-rotate-270 video {
  transform: rotate(270deg) scale(1.78);
}

.video-area.video-fit-cover .video-tile video,
.dual-pinned .dual-tile video,
.multi-tile-small video,
.sidebar-tile video {
  object-fit: cover;
}

.video-area.video-fit-contain .video-tile video,
.video-area.video-fit-contain .screen-tile video,
.video-area.video-fit-contain .multi-tile video,
.dual-main .dual-tile video {
  object-fit: contain;
}

/* ==================== 头像块 ==================== */
.avatar-block {
  display: flex;
  align-items: center;
  justify-content: center;
  width: clamp(36px, 10vw, 96px);
  height: clamp(36px, 10vw, 96px);
  border-radius: 50%;
  flex-shrink: 0;
}
.avatar-text {
  font-size: clamp(14px, 3vw, 36px);
  font-weight: 600;
  color: #fff;
  user-select: none;
}

/* ==================== 瓦片信息 ==================== */
.tile-info {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 8px;
  background: linear-gradient(transparent, rgba(0,0,0,.6));
}
.tile-name {
  font-size: clamp(10px, 1.2vw, 14px);
  color: #fff;
  text-shadow: 0 1px 2px rgba(0,0,0,.5);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.tile-icons {
  display: flex;
  align-items: center;
  gap: 4px;
}
.icon-muted {
  font-size: 14px;
  background: rgba(255,77,79,.8);
  padding: 1px 4px;
  border-radius: 4px;
}

/* ==================== 空状态 ==================== */
.grid-empty {
  grid-column: 1 / -1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  color: #888;
  font-size: 14px;
}
.pulse-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #ff4d4f;
  animation: pulse 1.4s infinite;
}
.pulse-dot.ok { background: #52c41a; }
@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: .4; transform: scale(1.4); }
}

/* ==================== 右侧面板 ==================== */
.side-panel {
  width: 320px;
  background: #2b2b2b;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  border-left: 1px solid #3a3a3a;
}
.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  font-size: 15px;
  font-weight: 500;
  border-bottom: 1px solid #3a3a3a;
}
.close-icon {
  cursor: pointer;
  color: #888;
  font-size: 18px;
}
.close-icon:hover { color: #fff; }

/* 聊天面板 */
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  min-height: 0;
}
.chat-msg { margin-bottom: 12px; }
.chat-msg.own { text-align: right; }
.msg-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 3px; }
.chat-msg.own .msg-head { flex-direction: row-reverse; }
.msg-sender { font-size: 12px; color: #888; }
.msg-time { font-size: 11px; color: #555; }
.msg-body {
  display: inline-block;
  padding: 7px 12px;
  border-radius: 8px;
  background: #3a3a3a;
  max-width: 80%;
  word-break: break-all;
  font-size: 13px;
  line-height: 1.5;
  text-align: left;
}
.chat-msg.own .msg-body { background: #1677ff; }
.file-link { color: #69b1ff; text-decoration: none; }
.chat-input { padding: 8px 10px; border-top: 1px solid #3a3a3a; }
.chat-bar {
  display: flex;
  align-items: center;
  gap: 6px;
}
.chat-upload-btn {
  cursor: pointer;
  color: #888;
  display: flex;
  align-items: center;
}
.chat-upload-btn:hover { color: #1677ff; }
.send-btn {
  width: 32px !important;
  height: 32px !important;
  padding: 0 !important;
  border-radius: 8px !important;
  flex-shrink: 0;
}
.chat-bar {
  display: flex;
  align-items: center;
  gap: 6px;
}
.chat-upload-btn {
  color: #888;
  cursor: pointer;
  display: flex;
  align-items: center;
  flex-shrink: 0;
}
.chat-upload-btn:hover { color: #fff; }
.send-btn {
  flex-shrink: 0;
  padding: 6px 10px;
  border-radius: 8px;
}

/* 评分面板 */
.score-body { flex: 1; overflow-y: auto; padding: 10px; min-height: 0; }
.score-total-bar {
  padding: 8px 12px;
  background: #3a3a3a;
  border-radius: 8px;
  margin-bottom: 10px;
  font-size: 13px;
  color: #fff;
  text-align: center;
}
.total-val { font-size: 22px; font-weight: 700; color: #1677ff; }
.score-group { margin-bottom: 10px; }
.group-title {
  font-size: 12px;
  font-weight: 600;
  color: #1677ff;
  padding: 5px 0;
  border-bottom: 1px solid #3a3a3a;
  margin-bottom: 6px;
}
.score-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 0;
}
.score-row-left { flex: 1; min-width: 0; }
.score-name {
  font-size: 13px;
  color: #fff;
  cursor: help;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.score-row-right {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
  margin-left: 8px;
}
.score-max {
  font-size: 12px;
  color: #888;
  flex-shrink: 0;
}
.panel-footer { padding: 10px 12px; border-top: 1px solid #3a3a3a; }

/* ==================== 底部控制栏 ==================== */
.control-bar {
  display: flex;
  align-items: center;
  padding: 12px 32px;
  background: #1e1e1e;
  border-top: 1px solid #333;
  flex-shrink: 0;
  z-index: 10;
}
.control-section {
  display: flex;
  align-items: center;
  gap: 16px;
}
.control-left {
  flex: 1;
  justify-content: flex-start;
}
.control-center {
  flex: 1;
  justify-content: center;
  text-align: center;
}
.control-right {
  flex: 1;
  justify-content: flex-end;
}

.control-bar .el-button {
  background: #333;
  border-color: #4a4a4a;
  color: #fff;
}
.control-bar .el-button:hover {
  background: #4a4a4a;
  border-color: #5a5a5a;
}
.btn-off {
  background: rgba(255,77,79,.2) !important;
  border-color: rgba(255,77,79,.4) !important;
  color: #ff4d4f !important;
}
.btn-off:hover {
  background: rgba(255,77,79,.3) !important;
}
.btn-active {
  background: rgba(22,119,255,.2) !important;
  border-color: rgba(22,119,255,.4) !important;
  color: #1677ff !important;
}
.btn-recording {
  background: rgba(255,77,79,.15) !important;
  border-color: rgba(255,77,79,.3) !important;
  color: #ff4d4f !important;
  animation: recording-pulse 1.5s infinite;
}
@keyframes recording-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}
.cam-switch-btn:hover {
  background: #4a4a4a !important;
}

/* 清晰度下拉 */
.is-active-quality {
  background: rgba(22,119,255,.1);
  color: #1677ff;
}

/* ==================== 动画 ==================== */
.slide-right-enter-active, .slide-right-leave-active {
  transition: all .25s ease;
}
.slide-right-enter-from, .slide-right-leave-to {
  transform: translateX(100%);
  opacity: 0;
}

/* 录制进度弹窗 */
.scoring-progress { padding: 10px 0; }
.progress-step {
  display: flex; align-items: center; gap: 12px; padding: 8px 0;
  opacity: 0.4; transition: all 0.3s;
}
.progress-step.active, .progress-step.done { opacity: 1; }
.step-icon {
  width: 28px; height: 28px; border-radius: 50%; display: flex;
  align-items: center; justify-content: center;
  background: #f0f0f0; font-size: 12px; color: #999; flex-shrink: 0;
}
.progress-step.active .step-icon { background: #e6f3ff; color: #1677ff; }
.progress-step.done .step-icon { background: #e6fff0; color: #52c41a; }
.step-num { font-size: 12px; }
.step-label { font-size: 14px; font-weight: 500; }
.step-detail { font-size: 12px; color: #999; }
.spinning { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
.progress-bar-wrap { margin-top: 16px; }

/* AI评分结果卡片 */
.score-result-card {
  position: fixed; top: 60px; right: 20px; z-index: 1000;
  background: #fff; border-radius: 12px; padding: 16px 20px;
  box-shadow: 0 4px 24px rgba(0,0,0,.15); min-width: 320px; max-width: 400px;
}
.score-header {
  display: flex; align-items: center; gap: 10px; margin-bottom: 12px;
}
.score-title { font-weight: 600; font-size: 15px; flex: 1; }
.score-overall { font-size: 28px; font-weight: 700; color: #1677ff; }
.score-model { font-size: 11px; color: #999; background: #f5f5f5; padding: 2px 6px; border-radius: 4px; }
.score-dims { display: flex; flex-direction: column; gap: 8px; margin-bottom: 12px; }
.score-dim-item { display: flex; align-items: center; gap: 8px; }
.dim-name { font-size: 13px; color: #444; width: 70px; flex-shrink: 0; }
.dim-score { font-size: 12px; color: #666; width: 30px; text-align: right; flex-shrink: 0; }
.score-actions { display: flex; gap: 8px; justify-content: flex-end; }
.slide-up-enter-active, .slide-up-leave-active { transition: all .3s; }
.slide-up-enter-from, .slide-up-leave-to { transform: translateY(-20px); opacity: 0; }

/* ==================== 竞赛大脑 Mission Room Upgrade ==================== */
.meeting-room {
  position: relative;
  isolation: isolate;
  background:
    radial-gradient(circle at 76% 18%, rgba(122, 255, 180, .07), transparent 28%),
    linear-gradient(180deg, #07080b 0%, #090a0d 54%, #050608 100%);
  color: #f0f1fa;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
}

.meeting-room::before {
  content: "";
  position: absolute;
  inset: 0;
  pointer-events: none;
  background:
    linear-gradient(rgba(240, 241, 250, .045) 1px, transparent 1px),
    linear-gradient(90deg, rgba(240, 241, 250, .045) 1px, transparent 1px);
  background-size: 72px 72px;
  mask-image: linear-gradient(180deg, rgba(0,0,0,.82), rgba(0,0,0,.46) 72%, transparent);
  z-index: -3;
}

.room-grid-bg {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background:
    linear-gradient(90deg, transparent, rgba(240, 241, 250, .055), transparent);
  opacity: .45;
  transform: translateX(-65%);
  animation: room-scan 9s cubic-bezier(.19, 1, .22, 1) infinite;
  z-index: -2;
}

.room-orbit {
  position: absolute;
  width: 760px;
  height: 760px;
  right: -280px;
  bottom: -330px;
  border: 1px solid rgba(240, 241, 250, .11);
  border-radius: 50%;
  pointer-events: none;
  z-index: -1;
}

.orbit-b {
  width: 520px;
  height: 520px;
  right: -180px;
  bottom: -220px;
  opacity: .72;
}

@keyframes room-scan {
  0%, 42% { transform: translateX(-70%); opacity: 0; }
  58% { opacity: .5; }
  100% { transform: translateX(70%); opacity: 0; }
}

.room-header {
  height: 68px;
  padding: 0 28px;
  background: rgba(6, 7, 10, .92);
  border-bottom: 1px solid rgba(240, 241, 250, .12);
  box-shadow: 0 18px 42px rgba(0, 0, 0, .34);
  backdrop-filter: blur(12px);
}

.header-left {
  gap: 16px;
  min-width: 0;
}

.meeting-title-wrap {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.room-kicker {
  color: rgba(240, 241, 250, .46);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: .18em;
}

.meeting-title {
  color: #f1f2fa;
  font-size: 18px;
  font-weight: 760;
  letter-spacing: .01em;
  max-width: min(52vw, 720px);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.room-header :deep(.el-tag) {
  height: 26px;
  padding: 0 12px;
  border-radius: 999px;
  background: rgba(122, 255, 180, .08);
  border-color: rgba(122, 255, 180, .32);
  color: #7affb4;
  font-weight: 700;
}

.livekit-agent-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  height: 28px;
  padding: 0 11px 0 7px;
  border-radius: 999px;
  border: 1px solid rgba(31, 213, 249, .18);
  background: rgba(31, 213, 249, .055);
  color: rgba(240, 241, 250, .64);
  font-size: 12px;
  font-weight: 650;
  white-space: nowrap;
}

.livekit-agent-chip :deep(.agent-visualizer) {
  width: 28px;
  height: 18px;
}

.livekit-agent-chip.connected {
  border-color: rgba(122, 255, 180, .24);
  background: rgba(122, 255, 180, .07);
}

.livekit-agent-chip.connected :deep(.agent-visualizer) {
  color: #7affb4;
}

.header-right {
  gap: 18px;
}

.net-status,
.participant-num,
.countdown-pill {
  min-height: 34px;
  padding: 0 12px;
  border: 1px solid rgba(240, 241, 250, .12);
  background: rgba(18, 20, 25, .58);
  border-radius: 999px;
}

.participant-num {
  color: rgba(240, 241, 250, .62);
  gap: 7px;
}

.participant-num strong {
  color: #f1f2fa;
  font-size: 14px;
}

.countdown-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: rgba(244, 184, 92, .08);
  border-color: rgba(244, 184, 92, .22);
}

.countdown-label {
  color: rgba(244, 184, 92, .62);
  font-size: 11px;
  font-weight: 700;
}

.countdown-time {
  color: #f4d29d;
  font-size: 15px;
  letter-spacing: .04em;
}

.bar {
  background: rgba(240, 241, 250, .2);
}

.signal-bars[data-level="1"] .b1 { background: #ff6b6b; }
.signal-bars[data-level="2"] .b1,
.signal-bars[data-level="2"] .b2 { background: #f4b85c; }
.signal-bars[data-level="3"] .b1,
.signal-bars[data-level="3"] .b2,
.signal-bars[data-level="3"] .b3 { background: #7affb4; }

.room-body {
  padding: 18px 18px 14px;
  gap: 16px;
}

.video-area {
  position: relative;
  padding: 0;
  border: 1px solid rgba(240, 241, 250, .13);
  background:
    linear-gradient(180deg, rgba(24, 26, 31, .72), rgba(8, 9, 12, .74)),
    linear-gradient(rgba(240, 241, 250, .025) 1px, transparent 1px),
    linear-gradient(90deg, rgba(240, 241, 250, .025) 1px, transparent 1px);
  background-size: auto, 48px 48px, 48px 48px;
  box-shadow: inset 0 1px 0 rgba(240, 241, 250, .08), 0 24px 70px rgba(0, 0, 0, .34);
}

.video-grid,
.screen-share-layout {
  padding: 14px;
  gap: 12px;
}

.video-tile,
.screen-tile,
.dual-tile,
.multi-tile,
.sidebar-tile,
.sidebar-tile-sm,
.multi-tile-small {
  background:
    radial-gradient(circle at 50% 42%, rgba(240, 241, 250, .075), transparent 34%),
    linear-gradient(145deg, #15171c, #090a0d 72%);
  border: 1px solid rgba(240, 241, 250, .11);
  border-radius: 8px;
  box-shadow: inset 0 1px 0 rgba(240, 241, 250, .06);
  transition: border-color .18s ease, transform .18s ease, box-shadow .18s ease, background .18s ease;
}

.video-tile:hover,
.sidebar-tile:hover,
.sidebar-tile-sm:hover,
.multi-tile-small:hover {
  border-color: rgba(122, 255, 180, .36);
  box-shadow: inset 0 1px 0 rgba(240, 241, 250, .08), 0 14px 36px rgba(0, 0, 0, .28);
}

.multi-tile-small.is-pinned,
.sidebar-tile-sm:hover {
  border-color: rgba(122, 255, 180, .48);
}

.video-tile video,
.sidebar-tile video,
.sidebar-tile-sm video,
.multi-tile-small video {
  filter: saturate(.96) contrast(1.03);
}

.screen-tile video,
.dual-tile video,
.multi-tile video {
  background: #050608;
}

.avatar-block {
  position: relative;
  background: linear-gradient(145deg, rgba(240, 241, 250, .18), rgba(122, 255, 180, .12)) !important;
  border: 1px solid rgba(240, 241, 250, .15);
  box-shadow: 0 0 0 8px rgba(240, 241, 250, .035);
  overflow: hidden;
}

.avatar-block :deep(.agent-visualizer) {
  position: absolute;
  inset: -28%;
  opacity: .82;
  color: #1fd5f9;
  mix-blend-mode: screen;
}

.avatar-block::after {
  content: "";
  position: absolute;
  inset: 16%;
  border-radius: inherit;
  background: radial-gradient(circle, rgba(7, 8, 11, .74), rgba(7, 8, 11, .28) 58%, transparent);
}

.avatar-text {
  position: relative;
  z-index: 1;
  color: #f1f2fa;
  font-weight: 760;
}

.tile-info {
  padding: 18px 14px 10px;
  background: linear-gradient(180deg, transparent, rgba(4, 5, 8, .72));
}

.tile-name {
  color: rgba(240, 241, 250, .88);
  font-weight: 650;
  text-shadow: none;
}

.icon-muted {
  background: rgba(255, 107, 107, .13);
  border: 1px solid rgba(255, 107, 107, .34);
  color: #ff8c8c;
}

.grid-empty {
  position: relative;
  justify-content: center;
  min-height: 100%;
  color: rgba(240, 241, 250, .62);
  letter-spacing: .04em;
}

.empty-visualizer {
  width: min(44vw, 420px);
  height: min(44vw, 420px);
  min-width: 260px;
  min-height: 260px;
  margin-bottom: -28px;
}

.empty-title {
  color: #f1f2fa;
  font-size: 18px;
  font-weight: 760;
  letter-spacing: .08em;
}

.empty-subtitle {
  color: rgba(240, 241, 250, .38);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: .18em;
  text-transform: uppercase;
}

.pulse-dot.ok {
  background: #7affb4;
  box-shadow: 0 0 0 8px rgba(122, 255, 180, .08);
}

.pulse-dot {
  background: #ff6b6b;
  box-shadow: 0 0 0 8px rgba(255, 107, 107, .08);
}

.side-panel {
  width: 360px;
  margin-left: 0;
  background:
    linear-gradient(180deg, rgba(18, 20, 25, .96), rgba(8, 9, 12, .98));
  border: 1px solid rgba(240, 241, 250, .12);
  box-shadow: -18px 0 50px rgba(0, 0, 0, .28);
}

.panel-head {
  min-height: 58px;
  padding: 0 18px;
  border-bottom-color: rgba(240, 241, 250, .11);
  color: #f1f2fa;
  font-size: 15px;
  font-weight: 760;
}

.close-icon {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  color: rgba(240, 241, 250, .5);
  transition: background .18s ease, color .18s ease;
}

.close-icon:hover {
  background: rgba(240, 241, 250, .08);
  color: #f1f2fa;
}

.chat-messages,
.score-body {
  padding: 16px;
}

.msg-sender {
  color: rgba(240, 241, 250, .52);
}

.msg-time {
  color: rgba(240, 241, 250, .32);
}

.msg-body {
  background: rgba(240, 241, 250, .075);
  border: 1px solid rgba(240, 241, 250, .09);
  border-radius: 8px;
  color: rgba(240, 241, 250, .82);
}

.chat-msg.own .msg-body {
  background: rgba(122, 255, 180, .1);
  border-color: rgba(122, 255, 180, .24);
  color: #eefaf3;
}

.file-link {
  color: #9deabb;
}

.chat-input,
.panel-footer {
  padding: 12px;
  border-top-color: rgba(240, 241, 250, .11);
  background: rgba(5, 6, 8, .38);
}

.chat-bar {
  gap: 8px;
}

.chat-upload-btn {
  width: 30px;
  height: 30px;
  justify-content: center;
  border-radius: 6px;
  color: rgba(240, 241, 250, .58);
}

.chat-upload-btn:hover {
  background: rgba(240, 241, 250, .08);
  color: #f1f2fa;
}

.chat-bar :deep(.el-input__wrapper),
.score-body :deep(.el-textarea__inner),
.score-body :deep(.el-input__wrapper) {
  background: rgba(240, 241, 250, .055);
  border: 1px solid rgba(240, 241, 250, .11);
  box-shadow: none;
  border-radius: 6px;
}

.chat-bar :deep(.el-input__inner),
.score-body :deep(.el-textarea__inner),
.score-body :deep(.el-input__inner) {
  color: #f1f2fa;
}

.chat-bar :deep(.el-input__wrapper:hover),
.score-body :deep(.el-textarea__inner:hover),
.score-body :deep(.el-input__wrapper:hover) {
  border-color: rgba(240, 241, 250, .2);
}

.send-btn,
.panel-footer :deep(.el-button--primary) {
  background: #eff0fa !important;
  border-color: #eff0fa !important;
  color: #090a0d !important;
}

.send-btn:hover,
.panel-footer :deep(.el-button--primary:hover) {
  background: #dfe3ee !important;
  border-color: #dfe3ee !important;
  color: #090a0d !important;
}

.score-total-bar {
  background: rgba(240, 241, 250, .06);
  border: 1px solid rgba(240, 241, 250, .1);
  color: rgba(240, 241, 250, .7);
}

.total-val,
.group-title {
  color: #7affb4;
}

.group-title {
  border-bottom-color: rgba(240, 241, 250, .1);
  letter-spacing: .08em;
}

.score-name {
  color: rgba(240, 241, 250, .84);
}

.score-max {
  color: rgba(240, 241, 250, .42);
}

.control-bar {
  height: 78px;
  padding: 12px 28px;
  background: rgba(7, 8, 11, .96);
  border-top: 1px solid rgba(240, 241, 250, .12);
  box-shadow: 0 -18px 46px rgba(0, 0, 0, .35);
  backdrop-filter: blur(14px);
}

.control-section {
  gap: 12px;
}

.control-bar :deep(.el-button) {
  width: 44px;
  height: 44px;
  border: 1px solid rgba(240, 241, 250, .14);
  background: rgba(240, 241, 250, .055);
  color: rgba(240, 241, 250, .82);
  box-shadow: none;
  transition: transform .18s ease, background .18s ease, border-color .18s ease, color .18s ease;
}

.control-bar :deep(.el-button:hover),
.control-bar :deep(.el-button:focus) {
  background: rgba(240, 241, 250, .11);
  border-color: rgba(240, 241, 250, .28);
  color: #f1f2fa;
  transform: translateY(-1px);
}

.control-bar :deep(.el-button.is-round) {
  width: auto;
  min-width: 112px;
  padding: 0 22px;
  border-radius: 999px;
  font-weight: 760;
}

.control-bar :deep(.el-button--danger) {
  background: rgba(255, 107, 107, .12);
  border-color: rgba(255, 107, 107, .32);
  color: #ff9a9a;
}

.control-bar :deep(.el-button--danger:hover) {
  background: rgba(255, 107, 107, .2);
  border-color: rgba(255, 107, 107, .48);
  color: #ffd2d2;
}

.btn-off {
  background: rgba(255, 107, 107, .11) !important;
  border-color: rgba(255, 107, 107, .32) !important;
  color: #ff8c8c !important;
}

.btn-active {
  background: rgba(122, 255, 180, .12) !important;
  border-color: rgba(122, 255, 180, .42) !important;
  color: #7affb4 !important;
}

.btn-live {
  position: relative;
  color: #f1f2fa !important;
}

.btn-live::after,
.btn-active::after {
  content: "";
  position: absolute;
  inset: -5px;
  border-radius: inherit;
  border: 1px solid rgba(31, 213, 249, .2);
  opacity: .72;
  animation: control-radar 1.9s cubic-bezier(.19, 1, .22, 1) infinite;
  pointer-events: none;
}

.btn-active::after {
  border-color: rgba(122, 255, 180, .32);
}

@keyframes control-radar {
  0% { transform: scale(.9); opacity: .72; }
  100% { transform: scale(1.28); opacity: 0; }
}

.sidebar-toggle {
  right: 10px;
  width: 26px;
  height: 54px;
  background: rgba(6, 7, 10, .72);
  border: 1px solid rgba(240, 241, 250, .14);
  color: rgba(240, 241, 250, .76);
}

.sidebar-toggle:hover {
  background: rgba(240, 241, 250, .1);
  color: #f1f2fa;
}

.reconnect-overlay {
  background: rgba(3, 4, 6, .78);
  backdrop-filter: blur(10px);
}

.reconnect-box {
  background: rgba(12, 14, 18, .96);
  border: 1px solid rgba(240, 241, 250, .14);
  border-radius: 8px;
  box-shadow: 0 24px 70px rgba(0, 0, 0, .48);
}

.reconnect-spinner {
  border-color: rgba(240, 241, 250, .14);
  border-top-color: #7affb4;
}

.reconnect-text {
  color: #f1f2fa;
}

.reconnect-hint {
  color: rgba(240, 241, 250, .5);
}

.control-right :deep(.el-dropdown-menu),
.meeting-room :deep(.el-dropdown-menu) {
  background: rgba(8, 10, 12, .98);
  border: 1px solid rgba(240, 241, 250, .16);
  border-radius: 8px;
  padding: 6px;
  box-shadow: 0 18px 48px rgba(0, 0, 0, .36);
}

.meeting-room :deep(.el-dropdown-menu__item) {
  min-height: 34px;
  border-radius: 5px;
  color: rgba(240, 241, 250, .74);
}

.meeting-room :deep(.el-dropdown-menu__item:hover),
.meeting-room :deep(.el-dropdown-menu__item:focus) {
  background: rgba(240, 241, 250, .08);
  color: #f1f2fa;
}

.is-active-quality {
  background: rgba(122, 255, 180, .1) !important;
  color: #7affb4 !important;
}

:global(.issues-drawer) {
  background: transparent;
  color: #f1f2fa;
}

:global(.issues-drawer .el-drawer__body) {
  padding: 0;
  overflow: hidden;
  background: #07080b;
}

.issues-panel {
  height: 100%;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  background:
    radial-gradient(circle at 84% 0%, rgba(122, 255, 180, .075), transparent 32%),
    linear-gradient(rgba(240, 241, 250, .018) 1px, transparent 1px),
    linear-gradient(90deg, rgba(240, 241, 250, .018) 1px, transparent 1px),
    #07080b;
  background-size: auto, 58px 58px, 58px 58px, auto;
  border-top: 1px solid rgba(122, 255, 180, .18);
  box-shadow: 0 -24px 74px rgba(0, 0, 0, .46);
}

.issues-head {
  min-height: 82px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 18px 28px;
  border-bottom: 1px solid rgba(240, 241, 250, .09);
  background: rgba(5, 6, 9, .54);
}

.issues-kicker {
  color: rgba(240, 241, 250, .42);
  font-size: 11px;
  font-weight: 840;
  letter-spacing: .18em;
}

.issues-head strong {
  display: block;
  margin-top: 6px;
  color: #f4f6ff;
  font-size: 24px;
  line-height: 1;
  font-weight: 850;
}

.issues-head p {
  margin: 8px 0 0;
  color: rgba(240, 241, 250, .48);
  font-size: 13px;
}

.issues-metrics {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.issues-metrics span {
  min-height: 28px;
  display: inline-flex;
  align-items: center;
  padding: 0 11px;
  border: 1px solid rgba(240, 241, 250, .1);
  border-radius: 999px;
  background: rgba(240, 241, 250, .035);
  color: rgba(240, 241, 250, .66);
  font-size: 12px;
  font-weight: 760;
  white-space: nowrap;
}

.issues-close {
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  flex-shrink: 0;
  border: 1px solid rgba(240, 241, 250, .12);
  border-radius: 50%;
  background: rgba(240, 241, 250, .045);
  color: rgba(240, 241, 250, .68);
  cursor: pointer;
  transition: background .18s ease, color .18s ease, border-color .18s ease;
}

.issues-close:hover {
  background: rgba(240, 241, 250, .09);
  border-color: rgba(240, 241, 250, .22);
  color: #f4f6ff;
}

.issues-list {
  min-height: 0;
  padding: 14px 28px 20px;
  overflow-y: auto;
  display: grid;
  align-content: start;
  gap: 8px;
  scrollbar-width: thin;
  scrollbar-color: rgba(240, 241, 250, .22) transparent;
}

.issues-list::-webkit-scrollbar {
  width: 6px;
}

.issues-list::-webkit-scrollbar-track {
  background: transparent;
}

.issues-list::-webkit-scrollbar-thumb {
  background: rgba(240, 241, 250, .2);
  border-radius: 999px;
}

.issue-row-card {
  display: grid;
  grid-template-columns: 56px minmax(0, 1fr);
  gap: 12px;
  align-items: center;
  min-height: 66px;
  padding: 10px 14px;
  border: 1px solid rgba(255, 211, 138, .18);
  background:
    linear-gradient(90deg, rgba(255, 211, 138, .055), rgba(240, 241, 250, .018));
  transition: transform .18s ease, border-color .18s ease, background .18s ease;
}

.issue-row-card:hover {
  transform: translateY(-1px);
  border-color: rgba(255, 211, 138, .3);
  background:
    linear-gradient(90deg, rgba(255, 211, 138, .08), rgba(240, 241, 250, .024));
}

.issue-row-card.resolved {
  border-color: rgba(122, 255, 180, .16);
  background:
    linear-gradient(90deg, rgba(122, 255, 180, .048), rgba(240, 241, 250, .018));
}

.issue-row-card.resolved:hover {
  border-color: rgba(122, 255, 180, .28);
}

.issue-index {
  display: grid;
  place-items: center;
  height: 42px;
  border-right: 1px solid rgba(240, 241, 250, .08);
  color: rgba(240, 241, 250, .48);
  font-size: 15px;
  font-weight: 850;
  font-variant-numeric: tabular-nums;
}

.issue-copy {
  min-width: 0;
}

.issue-row-top {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.issue-category-pill,
.issue-state {
  min-height: 24px;
  display: inline-flex;
  align-items: center;
  padding: 0 9px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 820;
}

.issue-category-pill {
  border: 1px solid rgba(240, 241, 250, .1);
  background: rgba(240, 241, 250, .035);
  color: rgba(240, 241, 250, .58);
}

.issue-state {
  border: 1px solid rgba(255, 211, 138, .22);
  background: rgba(255, 211, 138, .08);
  color: #ffd38a;
}

.issue-row-card.resolved .issue-state {
  border-color: rgba(122, 255, 180, .22);
  background: rgba(122, 255, 180, .08);
  color: #7affb4;
}

.issue-title {
  color: rgba(244, 246, 255, .88);
  font-size: 15px;
  line-height: 1.35;
  font-weight: 720;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.issue-meta {
  margin-top: 5px;
  color: rgba(240, 241, 250, .36);
  font-size: 12px;
  font-variant-numeric: tabular-nums;
}

.issues-empty {
  min-height: 260px;
  margin: 18px 28px 24px;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 10px;
  text-align: center;
  border: 1px solid rgba(240, 241, 250, .09);
  background:
    radial-gradient(circle at 50% 44%, rgba(122, 255, 180, .05), transparent 34%),
    rgba(240, 241, 250, .028);
}

.issues-empty span {
  width: 76px;
  height: 76px;
  display: grid;
  place-items: center;
  border: 1px solid rgba(122, 255, 180, .18);
  border-radius: 50%;
  color: #7affb4;
  background: rgba(122, 255, 180, .06);
  font-size: 11px;
  font-weight: 880;
  letter-spacing: .08em;
}

.issues-empty strong {
  color: #f4f6ff;
  font-size: 18px;
}

.issues-empty p {
  margin: 0;
  color: rgba(240, 241, 250, .46);
  font-size: 13px;
}

@media (max-width: 960px) {
  .room-header {
    height: auto;
    min-height: 74px;
    padding: 12px 16px;
    align-items: flex-start;
    gap: 10px;
  }

  .header-right {
    gap: 8px;
    flex-wrap: wrap;
    justify-content: flex-end;
  }

  .room-body {
    padding: 10px;
  }

  .side-panel {
    position: absolute;
    top: 10px;
    right: 10px;
    bottom: 10px;
    width: min(360px, calc(100vw - 20px));
    z-index: 8;
  }

  .control-bar {
    height: auto;
    padding: 10px 12px;
    gap: 10px;
    flex-wrap: wrap;
  }

  .control-section {
    flex: 1 1 auto;
  }
}

@media (prefers-reduced-motion: reduce) {
  .room-grid-bg,
  .pulse-dot,
  .btn-recording,
  .reconnect-spinner {
    animation: none !important;
  }
}

/* ==================== LiveKit Conference Layout Pass ==================== */
.meeting-room {
  height: calc(100vh - 72px);
  min-height: 620px;
  background:
    radial-gradient(circle at 50% 118%, rgba(31, 213, 249, .08), transparent 32%),
    radial-gradient(circle at 78% 8%, rgba(122, 255, 180, .045), transparent 26%),
    #050609;
}

.meeting-room:fullscreen {
  height: 100vh;
}

.meeting-room::before {
  background:
    linear-gradient(rgba(240, 241, 250, .026) 1px, transparent 1px),
    linear-gradient(90deg, rgba(240, 241, 250, .026) 1px, transparent 1px);
  background-size: 82px 82px;
  opacity: .76;
}

.room-grid-bg {
  opacity: .18;
}

.room-orbit {
  opacity: .38;
  border-color: rgba(240, 241, 250, .07);
}

.room-header {
  position: absolute;
  top: 18px;
  left: 24px;
  right: 24px;
  height: 40px;
  padding: 0;
  background: transparent;
  border: 0;
  box-shadow: none;
  backdrop-filter: none;
  z-index: 12;
  pointer-events: none;
}

.room-header .header-left,
.room-header .header-right {
  pointer-events: auto;
}

.meeting-title-wrap {
  gap: 1px;
}

.room-kicker {
  font-size: 9px;
  letter-spacing: .22em;
  color: rgba(240, 241, 250, .28);
}

.meeting-title {
  font-size: 13px;
  color: rgba(240, 241, 250, .72);
  font-weight: 720;
  max-width: 36vw;
}

.room-header :deep(.el-tag),
.livekit-agent-chip,
.net-status,
.participant-num,
.countdown-pill {
  min-height: 30px;
  height: 30px;
  border-radius: 999px;
  background: rgba(10, 11, 15, .68);
  border: 1px solid rgba(240, 241, 250, .1);
  box-shadow: 0 10px 28px rgba(0, 0, 0, .22);
}

.livekit-agent-chip {
  display: none;
}

.room-header :deep(.el-tag) {
  color: rgba(122, 255, 180, .88);
}

.header-right {
  gap: 8px;
}

.participant-num span,
.countdown-label {
  display: none;
}

.participant-num strong,
.countdown-time,
.net-text {
  font-size: 12px;
  font-weight: 760;
}

.room-body {
  height: 100%;
  flex: 1;
  padding: 24px 24px 112px;
  gap: 16px;
}

.video-area {
  border: 1px solid rgba(240, 241, 250, .095);
  border-radius: 0;
  background:
    linear-gradient(180deg, rgba(16, 18, 23, .32), rgba(5, 6, 9, .18)),
    linear-gradient(rgba(240, 241, 250, .018) 1px, transparent 1px),
    linear-gradient(90deg, rgba(240, 241, 250, .018) 1px, transparent 1px);
  background-size: auto, 58px 58px, 58px 58px;
  box-shadow: inset 0 1px 0 rgba(240, 241, 250, .04);
  overflow: hidden;
}

.video-grid {
  place-items: center;
  align-content: center;
  justify-content: center;
  gap: 14px;
  padding: 42px 28px 28px;
}

.screen-share-layout {
  gap: 14px;
  padding: 42px 28px 28px;
}

.video-tile,
.screen-tile,
.dual-tile,
.multi-tile {
  border-radius: 12px;
  background:
    radial-gradient(circle at 50% 44%, rgba(31, 213, 249, .035), transparent 34%),
    linear-gradient(180deg, #101217 0%, #06070a 100%);
  border: 1px solid rgba(240, 241, 250, .11);
  box-shadow:
    inset 0 1px 0 rgba(240, 241, 250, .055),
    0 24px 70px rgba(0, 0, 0, .32);
}

.video-grid .video-tile:only-child {
  width: min(100%, 1040px);
  height: auto;
  aspect-ratio: 16 / 9;
  max-width: min(72vw, 1040px);
  max-height: min(68vh, 620px);
  margin: auto;
}

.video-grid:not(:has(.video-tile:only-child)) .video-tile {
  aspect-ratio: 16 / 9;
  min-height: 180px;
}

.video-tile.has-video,
.screen-tile,
.dual-tile.has-video,
.multi-tile {
  background: #050609;
}

.video-tile:hover,
.screen-tile:hover,
.dual-tile:hover,
.multi-tile:hover {
  border-color: rgba(240, 241, 250, .18);
  box-shadow:
    inset 0 1px 0 rgba(240, 241, 250, .075),
    0 26px 78px rgba(0, 0, 0, .38);
}

.video-tile.is-local::before,
.sidebar-tile.is-local::before,
.multi-tile-small.is-local::before {
  content: "";
  position: absolute;
  inset: 0;
  border-radius: inherit;
  border: 1px solid rgba(240, 241, 250, .045);
  pointer-events: none;
}

.video-tile:not(.is-muted),
.sidebar-tile:not(.is-muted),
.multi-tile-small:not(.is-muted) {
  border-color: rgba(31, 213, 249, .24);
}

.video-tile video,
.screen-tile video,
.dual-tile video,
.multi-tile video {
  object-fit: cover;
}

.video-tile.video-rotate-90 video {
  transform: rotate(90deg) scale(1.78);
  transform-origin: center;
}

.video-tile.video-rotate-270 video {
  transform: rotate(270deg) scale(1.78);
  transform-origin: center;
}

.video-area.video-fit-contain .video-tile video,
.screen-tile video,
.multi-tile video {
  object-fit: contain;
}

.avatar-block {
  width: clamp(78px, 9vw, 132px);
  height: clamp(78px, 9vw, 132px);
  background:
    radial-gradient(circle at 35% 24%, rgba(31, 213, 249, .22), transparent 29%),
    linear-gradient(145deg, rgba(240, 241, 250, .12), rgba(240, 241, 250, .035)) !important;
  border: 1px solid rgba(240, 241, 250, .11);
  box-shadow:
    inset 0 1px 0 rgba(240, 241, 250, .09),
    0 0 0 1px rgba(240, 241, 250, .035),
    0 18px 48px rgba(0, 0, 0, .32);
}

.avatar-block :deep(.agent-visualizer) {
  opacity: .26;
  inset: -18%;
}

.avatar-block :deep(.state-idle) {
  opacity: .08;
}

.avatar-block::after {
  inset: 0;
  background:
    radial-gradient(circle at 48% 52%, rgba(5, 6, 9, .05), rgba(5, 6, 9, .48) 72%),
    linear-gradient(180deg, transparent, rgba(5, 6, 9, .24));
}

.avatar-text {
  font-size: clamp(24px, 3vw, 44px);
  letter-spacing: 0;
  font-weight: 820;
  text-transform: uppercase;
}

.tile-info {
  left: 18px;
  right: 18px;
  bottom: 16px;
  padding: 0;
  background: transparent;
}

.tile-name {
  display: inline-flex;
  align-items: center;
  max-width: min(70%, 360px);
  min-height: 30px;
  padding: 0 10px;
  border-radius: 999px;
  background: rgba(5, 6, 9, .58);
  border: 1px solid rgba(240, 241, 250, .09);
  color: rgba(240, 241, 250, .88);
  font-size: 13px;
  font-weight: 760;
  backdrop-filter: blur(10px);
}

.icon-muted {
  width: 30px;
  height: 30px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  border-radius: 8px;
  background: rgba(255, 99, 99, .12);
  border-color: rgba(255, 99, 99, .35);
  color: #ff9a9a;
  font-size: 13px;
  backdrop-filter: blur(10px);
}

.screen-sidebar,
.dual-sidebar {
  width: 148px;
  gap: 10px;
  padding: 0;
}

.sidebar-tile,
.sidebar-tile-sm,
.multi-tile-small {
  width: 148px;
  height: 84px;
  border-radius: 10px;
  background: rgba(8, 9, 12, .9);
  border: 1px solid rgba(240, 241, 250, .1);
  box-shadow: inset 0 1px 0 rgba(240, 241, 250, .045);
}

.sidebar-tile .avatar-block,
.sidebar-tile-sm .avatar-block,
.multi-tile-small .avatar-block {
  width: 42px;
  height: 42px;
  box-shadow: none;
}

.sidebar-tile .avatar-text,
.sidebar-tile-sm .avatar-text,
.multi-tile-small .avatar-text {
  font-size: 16px;
}

.sidebar-tile .tile-info,
.sidebar-tile-sm .tile-info,
.multi-tile-small .tile-info {
  left: 6px;
  right: 6px;
  bottom: 6px;
}

.sidebar-tile .tile-name,
.sidebar-tile-sm .tile-name,
.multi-tile-small .tile-name {
  min-height: 20px;
  padding: 0 6px;
  font-size: 10px;
}

.multi-cameras {
  flex: 0 0 116px;
  padding: 0;
  gap: 10px;
  grid-auto-columns: 174px;
}

.multi-tile-small {
  width: 174px;
  height: 98px;
  min-height: 98px;
}

.grid-empty {
  width: min(100%, 1040px);
  height: auto;
  aspect-ratio: 16 / 9;
  max-width: min(72vw, 1040px);
  max-height: min(68vh, 620px);
  min-height: 360px;
  margin: auto;
  border: 1px solid rgba(240, 241, 250, .11);
  border-radius: 12px;
  background:
    radial-gradient(circle at 50% 44%, rgba(31, 213, 249, .05), transparent 34%),
    linear-gradient(180deg, #101217 0%, #06070a 100%);
  box-shadow:
    inset 0 1px 0 rgba(240, 241, 250, .055),
    0 24px 70px rgba(0, 0, 0, .32);
}

.empty-visualizer {
  width: min(38vw, 340px);
  height: min(38vw, 340px);
  min-width: 210px;
  min-height: 210px;
  margin-bottom: -34px;
}

.empty-title {
  font-size: 15px;
  letter-spacing: .05em;
}

.empty-subtitle {
  font-size: 10px;
  letter-spacing: .16em;
}

.side-panel {
  width: 380px;
  border-radius: 12px;
  background: rgba(9, 10, 13, .94);
  border: 1px solid rgba(240, 241, 250, .11);
  box-shadow: 0 24px 80px rgba(0, 0, 0, .44);
  overflow: hidden;
}

.control-bar {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 104px;
  padding: 20px 36px;
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  background:
    linear-gradient(180deg, transparent 0%, rgba(5, 6, 9, .76) 28%, rgba(5, 6, 9, .98) 100%);
  border-top: 1px solid rgba(240, 241, 250, .06);
  box-shadow: none;
  backdrop-filter: blur(18px);
}

.control-section {
  gap: 12px;
}

.control-left,
.control-center,
.control-right {
  display: inline-flex;
  flex: unset;
}

.control-left {
  justify-self: start;
}

.control-center {
  justify-self: center;
  padding: 0 10px;
}

.control-right {
  justify-self: end;
}

.control-left,
.control-center,
.control-right {
  min-height: 56px;
}

.control-bar :deep(.el-button),
.audio-recorder :deep(.el-button) {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: rgba(18, 20, 25, .88);
  border: 1px solid rgba(240, 241, 250, .12);
  color: rgba(240, 241, 250, .82);
  box-shadow:
    inset 0 1px 0 rgba(240, 241, 250, .06),
    0 10px 28px rgba(0, 0, 0, .24);
}

.control-bar :deep(.el-button:hover),
.audio-recorder :deep(.el-button:hover) {
  transform: translateY(-2px);
  background: rgba(28, 30, 36, .96);
  border-color: rgba(240, 241, 250, .22);
}

.control-bar :deep(.el-button.is-round) {
  height: 52px;
  min-width: 148px;
  padding: 0 26px;
  border-radius: 999px;
  font-size: 14px;
}

.btn-off,
.control-bar :deep(.el-button.btn-off) {
  background: rgba(91, 25, 30, .86) !important;
  border-color: rgba(255, 99, 99, .32) !important;
  color: #ffb0b0 !important;
}

.btn-active,
.control-bar :deep(.el-button.btn-active) {
  background: rgba(31, 213, 249, .13) !important;
  border-color: rgba(31, 213, 249, .36) !important;
  color: #86eaff !important;
}

.btn-live::after,
.btn-active::after {
  inset: -4px;
  border-color: rgba(31, 213, 249, .14);
  animation-duration: 2.3s;
}

.control-bar :deep(.el-button--danger) {
  background: rgba(98, 28, 32, .86) !important;
  border-color: rgba(255, 99, 99, .38) !important;
  color: #ffb0b0 !important;
}

.control-bar :deep(.el-button--danger:hover) {
  background: rgba(120, 34, 39, .95) !important;
  color: #ffe2e2 !important;
}

.reconnect-box {
  border-radius: 12px;
}

@media (max-width: 1100px) {
  .room-header {
    left: 16px;
    right: 16px;
  }

  .livekit-agent-chip {
    display: none;
  }

  .video-grid .video-tile:only-child,
  .grid-empty {
    max-width: 100%;
  }

  .control-bar {
    padding: 16px 18px;
    grid-template-columns: 1fr;
    height: auto;
    gap: 12px;
  }

  .control-left,
  .control-center,
  .control-right {
    justify-self: center;
  }

  .room-body {
    padding-bottom: 178px;
  }
}

/* ==================== Compact Conference Polish ==================== */
.room-body {
  padding: 58px 32px 84px;
}

.video-area {
  border-color: rgba(240, 241, 250, .07);
  background:
    radial-gradient(circle at 50% 42%, rgba(240, 241, 250, .035), transparent 36%),
    linear-gradient(rgba(240, 241, 250, .016) 1px, transparent 1px),
    linear-gradient(90deg, rgba(240, 241, 250, .016) 1px, transparent 1px);
  background-size: auto, 58px 58px, 58px 58px;
  box-shadow: inset 0 1px 0 rgba(240, 241, 250, .035);
}

.video-grid,
.screen-share-layout {
  padding: 18px 24px 18px;
}

.video-grid .video-tile:only-child,
.grid-empty {
  width: min(100%, 1120px);
  max-width: min(68vw, 1120px);
  max-height: min(58vh, 560px);
}

.video-tile,
.screen-tile,
.dual-tile,
.multi-tile {
  border-radius: 10px;
  background:
    radial-gradient(circle at 50% 46%, rgba(240, 241, 250, .025), transparent 32%),
    #07080b;
  border-color: rgba(240, 241, 250, .075);
  box-shadow:
    inset 0 1px 0 rgba(240, 241, 250, .045),
    0 18px 52px rgba(0, 0, 0, .26);
}

.video-tile:hover,
.screen-tile:hover,
.dual-tile:hover,
.multi-tile:hover {
  border-color: rgba(240, 241, 250, .13);
  box-shadow:
    inset 0 1px 0 rgba(240, 241, 250, .06),
    0 20px 58px rgba(0, 0, 0, .3);
}

.avatar-block {
  width: clamp(72px, 7vw, 108px);
  height: clamp(72px, 7vw, 108px);
  border-color: rgba(240, 241, 250, .095);
  box-shadow:
    inset 0 1px 0 rgba(240, 241, 250, .07),
    0 12px 36px rgba(0, 0, 0, .28);
}

.avatar-text {
  font-size: clamp(22px, 2.5vw, 38px);
}

.tile-info {
  left: 16px;
  right: 16px;
  bottom: 14px;
}

.tile-name {
  min-height: 28px;
  padding: 0 10px;
  font-size: 12px;
  background: rgba(5, 6, 9, .46);
  border-color: rgba(240, 241, 250, .075);
}

.icon-muted {
  width: 28px;
  height: 28px;
  border-radius: 7px;
}

.control-bar {
  height: 68px;
  padding: 9px 30px;
  background:
    linear-gradient(180deg, transparent 0%, rgba(5, 6, 9, .58) 34%, rgba(5, 6, 9, .96) 100%);
  overflow: visible;
}

.control-left,
.control-center,
.control-right {
  min-height: 50px;
}

.control-section {
  gap: 8px;
  padding: 4px;
  border-radius: 999px;
  background: rgba(10, 11, 15, .22);
  border: 1px solid rgba(240, 241, 250, .045);
  box-shadow: inset 0 1px 0 rgba(240, 241, 250, .025);
}

.control-bar :deep(.el-button),
.audio-recorder :deep(.el-button) {
  position: relative;
  width: 42px;
  height: 42px;
  padding: 0;
  overflow: hidden;
  border-color: rgba(240, 241, 250, .105);
  background:
    radial-gradient(circle at 50% -10%, rgba(240, 241, 250, .08), transparent 48%),
    rgba(16, 18, 23, .92);
  box-shadow:
    inset 0 1px 0 rgba(240, 241, 250, .045),
    0 8px 20px rgba(0, 0, 0, .18);
  color: rgba(240, 241, 250, .72);
}

.control-bar :deep(.el-button::before),
.audio-recorder :deep(.el-button::before) {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(115deg, transparent 15%, rgba(240, 241, 250, .16) 45%, transparent 72%);
  transform: translateX(-120%);
  transition: transform .36s cubic-bezier(.19, 1, .22, 1);
  pointer-events: none;
}

.control-bar :deep(.el-button.is-round) {
  height: 42px;
  min-width: 126px;
  padding: 0 20px;
  font-size: 13px;
  gap: 8px;
}

.control-bar :deep(.el-button .lk-icon),
.audio-recorder :deep(.el-button .lk-icon) {
  position: relative;
  z-index: 1;
  width: 17px;
  height: 17px;
  transition: transform .2s cubic-bezier(.19, 1, .22, 1), opacity .2s ease;
}

.control-bar :deep(.el-button:hover::before),
.audio-recorder :deep(.el-button:hover::before) {
  transform: translateX(120%);
}

.control-bar :deep(.el-button:hover),
.audio-recorder :deep(.el-button:hover) {
  background:
    radial-gradient(circle at 50% -10%, rgba(240, 241, 250, .18), transparent 50%),
    rgba(22, 24, 30, .98);
  border-color: rgba(240, 241, 250, .2);
  color: #f0f1fa;
}

.control-bar :deep(.el-button:hover .lk-icon),
.audio-recorder :deep(.el-button:hover .lk-icon) {
  transform: scale(1.06);
}

.btn-live::after,
.btn-active::after {
  inset: -3px;
}

.btn-live {
  color: #d8fbff !important;
}

.btn-live::after {
  border-color: rgba(31, 213, 249, .18);
}

.btn-off,
.control-bar :deep(.el-button.btn-off) {
  background:
    radial-gradient(circle at 50% -10%, rgba(255, 148, 148, .18), transparent 52%),
    rgba(73, 22, 28, .86) !important;
  color: #ffbbbb !important;
}

.btn-off:hover,
.control-bar :deep(.el-button.btn-off:hover) {
  background:
    radial-gradient(circle at 50% -10%, rgba(255, 176, 176, .24), transparent 52%),
    rgba(91, 27, 34, .96) !important;
}

.btn-active,
.control-bar :deep(.el-button.btn-active) {
  background:
    radial-gradient(circle at 50% -10%, rgba(31, 213, 249, .16), transparent 52%),
    rgba(13, 34, 42, .92) !important;
  color: #9bf0ff !important;
}

.control-bar :deep(.el-button.btn-active:hover) {
  box-shadow:
    inset 0 1px 0 rgba(240, 241, 250, .045),
    0 8px 20px rgba(0, 0, 0, .22),
    0 0 0 1px rgba(31, 213, 249, .12);
}

.control-bar :deep(.el-button--danger) {
  background:
    radial-gradient(circle at 50% -20%, rgba(255, 174, 174, .16), transparent 54%),
    rgba(92, 24, 31, .92) !important;
  color: #ffc7c7 !important;
}

.control-bar :deep(.el-button--danger:hover) {
  background:
    radial-gradient(circle at 50% -20%, rgba(255, 196, 196, .24), transparent 54%),
    rgba(113, 30, 38, .98) !important;
}

.control-bar :deep(.el-button--danger span) {
  position: relative;
  z-index: 1;
  font-weight: 760;
}

:global(.meeting-quality-popper) {
  z-index: 3200 !important;
}

:global(.meeting-quality-popper.el-popper) {
  border: 1px solid rgba(122, 255, 180, .16) !important;
  border-radius: 12px !important;
  background: rgba(8, 10, 12, .98) !important;
  box-shadow:
    0 18px 54px rgba(0, 0, 0, .5),
    inset 0 1px 0 rgba(240, 241, 250, .055) !important;
  overflow: hidden;
}

:global(.meeting-quality-popper .el-dropdown-menu) {
  min-width: 156px;
  padding: 7px !important;
  background: transparent !important;
  border: 0 !important;
  box-shadow: none !important;
}

:global(.meeting-quality-popper .el-dropdown-menu__item) {
  min-height: 38px;
  padding: 0 12px !important;
  border-radius: 8px;
  color: rgba(240, 241, 250, .72) !important;
  font-size: 13px;
  font-weight: 760;
  letter-spacing: 0;
  transition: background .16s ease, color .16s ease;
}

:global(.meeting-quality-popper .el-dropdown-menu__item:hover),
:global(.meeting-quality-popper .el-dropdown-menu__item:focus) {
  background: rgba(122, 255, 180, .09) !important;
  color: #f4fff8 !important;
}

:global(.meeting-quality-popper .el-dropdown-menu__item.is-active-quality) {
  background: rgba(122, 255, 180, .12) !important;
  color: #7affb4 !important;
}

:global(.meeting-mobile-more-popper .mobile-menu-label) {
  min-height: 24px !important;
  padding: 2px 12px 4px !important;
  color: rgba(240, 241, 250, .38) !important;
  font-size: 10px !important;
  font-weight: 800 !important;
  letter-spacing: .18em !important;
  text-transform: uppercase;
  cursor: default !important;
  opacity: 1 !important;
}

:global(.meeting-mobile-more-popper .mobile-menu-label:hover) {
  background: transparent !important;
  color: rgba(240, 241, 250, .38) !important;
}

:global(.meeting-quality-popper .el-popper__arrow::before) {
  border-color: rgba(122, 255, 180, .16) !important;
  background: rgba(8, 10, 12, .98) !important;
}

.rec-dynamic {
  width: 42px;
  height: 20px;
}

@media (max-width: 1100px) {
  .room-body {
    padding: 56px 16px 144px;
  }

  .video-grid .video-tile:only-child,
  .grid-empty {
    max-width: 100%;
    max-height: none;
  }

  .control-bar {
    height: auto;
    padding: 12px 16px;
  }
}

/* ==================== Score Panel Experience ==================== */
.score-panel {
  position: relative;
  width: 420px;
}

.panel-title-wrap {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.panel-kicker {
  color: rgba(240, 241, 250, .36);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: .18em;
}

.score-panel .panel-head {
  min-height: 70px;
  padding: 0 22px;
}

.score-body {
  padding: 10px 18px 78px;
  background:
    linear-gradient(180deg, rgba(9, 10, 13, .99), rgba(9, 10, 13, .96));
  scrollbar-width: thin;
  scrollbar-color: rgba(240, 241, 250, .22) transparent;
}

.score-body::-webkit-scrollbar {
  width: 6px;
}

.score-body::-webkit-scrollbar-track {
  background: transparent;
}

.score-body::-webkit-scrollbar-thumb {
  background: rgba(240, 241, 250, .2);
  border-radius: 999px;
}

.score-total-bar {
  position: sticky;
  top: 0;
  z-index: 3;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  gap: 8px;
  min-height: 50px;
  margin: 0 0 8px;
  padding: 0 16px;
  border-radius: 12px;
  background:
    radial-gradient(circle at 48% 0%, rgba(122, 255, 180, .14), transparent 52%),
    linear-gradient(180deg, rgba(28, 30, 35, .98), rgba(18, 19, 24, .98));
  border: 1px solid rgba(240, 241, 250, .1);
  backdrop-filter: blur(12px);
}

.score-total-label,
.score-total-max {
  color: rgba(240, 241, 250, .55);
  font-size: 14px;
  font-weight: 650;
}

.total-val {
  color: #7affb4;
  font-size: 28px;
  line-height: 1;
  font-weight: 850;
  font-variant-numeric: tabular-nums;
}

.score-group {
  margin-bottom: 18px;
}

.group-title {
  position: relative;
  z-index: 1;
  margin: 0 0 8px;
  padding: 8px 0 9px;
  background:
    linear-gradient(180deg, rgba(9, 10, 13, .99), rgba(9, 10, 13, .98));
  color: #7affb4;
  border-bottom: 1px solid rgba(122, 255, 180, .18);
  font-size: 14px;
  font-weight: 820;
  letter-spacing: .08em;
  text-align: center;
}

.score-item {
  padding: 10px 0 14px;
  border-bottom: 1px solid rgba(240, 241, 250, .075);
}

.score-item:last-child {
  border-bottom: 0;
}

.score-item-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 8px;
}

.score-name {
  color: rgba(240, 241, 250, .84);
  font-size: 14px;
  font-weight: 720;
}

.score-value-pill {
  min-width: 102px;
  height: 32px;
  display: inline-flex;
  align-items: baseline;
  justify-content: center;
  gap: 3px;
  border-radius: 999px;
  background: rgba(240, 241, 250, .06);
  border: 1px solid rgba(240, 241, 250, .1);
  color: #f0f1fa;
  font-variant-numeric: tabular-nums;
}

.score-value-pill small {
  color: rgba(240, 241, 250, .46);
  font-size: 12px;
  font-weight: 700;
}

.score-number-input {
  width: 54px;
}

.score-number-input :deep(.el-input__wrapper) {
  padding: 0;
  background: transparent;
  border: 0;
  box-shadow: none;
}

.score-number-input :deep(.el-input__inner) {
  height: 28px;
  color: #f0f1fa;
  font-size: 18px;
  font-weight: 800;
  text-align: center;
  font-variant-numeric: tabular-nums;
}

.score-number-input :deep(.el-input__wrapper.is-focus) {
  box-shadow: none;
}

.score-slider {
  margin: 0 4px 8px;
}

.score-slider :deep(.el-slider__runway) {
  height: 4px;
  background: rgba(240, 241, 250, .11);
  border-radius: 999px;
}

.score-slider :deep(.el-slider__bar) {
  height: 4px;
  background: linear-gradient(90deg, #1fd5f9, #7affb4);
  border-radius: 999px;
}

.score-slider :deep(.el-slider__button-wrapper) {
  top: -16px;
}

.score-slider :deep(.el-slider__button) {
  width: 14px;
  height: 14px;
  border: 2px solid #f0f1fa;
  background: #7affb4;
  box-shadow: 0 0 0 5px rgba(122, 255, 180, .1), 0 8px 18px rgba(0, 0, 0, .28);
}

.score-comment :deep(.el-textarea__inner) {
  min-height: 40px !important;
  padding: 10px 12px;
  resize: vertical;
  background: rgba(240, 241, 250, .045);
  border: 1px solid rgba(240, 241, 250, .09);
  border-radius: 8px;
  color: rgba(240, 241, 250, .82);
  box-shadow: none;
  font-size: 13px;
  line-height: 1.45;
}

.score-comment :deep(.el-textarea__inner:hover),
.score-comment :deep(.el-textarea__inner:focus) {
  border-color: rgba(122, 255, 180, .28);
  box-shadow: 0 0 0 3px rgba(122, 255, 180, .06);
}

.score-empty {
  min-height: 180px;
  display: grid;
  place-items: center;
  gap: 10px;
  color: rgba(240, 241, 250, .52);
}

.score-empty :deep(.agent-visualizer) {
  width: 86px;
  height: 86px;
  color: #7affb4;
}

.score-footer {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  gap: 14px;
  z-index: 5;
  padding: 12px 18px 14px;
  background:
    linear-gradient(180deg, rgba(9, 10, 13, .78), rgba(9, 10, 13, .98) 30%, rgba(9, 10, 13, 1));
  border-top: 1px solid rgba(240, 241, 250, .08);
}

.score-submit-meta {
  min-width: 76px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.score-submit-meta span {
  color: rgba(240, 241, 250, .42);
  font-size: 11px;
  font-weight: 760;
}

.score-submit-meta strong {
  color: #7affb4;
  font-size: 22px;
  line-height: 1;
  font-variant-numeric: tabular-nums;
}

.score-footer :deep(.el-button) {
  flex: 1;
  height: 44px;
  border-radius: 999px;
  background: #f0f1fa !important;
  border-color: #f0f1fa !important;
  color: #07080b !important;
  font-size: 14px;
  font-weight: 850;
}

.score-footer :deep(.el-button:hover) {
  background: #dfe3ee !important;
  border-color: #dfe3ee !important;
}

/* ==================== Participant Tile Pro Polish ==================== */
.video-tile,
.dual-tile,
.sidebar-tile,
.sidebar-tile-sm,
.multi-tile-small {
  isolation: isolate;
}

.video-tile:not(.has-video),
.dual-tile:not(.has-video) {
  background:
    radial-gradient(circle at 50% 52%, rgba(31, 213, 249, .045), transparent 24%),
    radial-gradient(circle at 22% 18%, rgba(122, 255, 180, .045), transparent 30%),
    linear-gradient(135deg, rgba(240, 241, 250, .045), transparent 26%),
    #07080b;
}

.video-tile:not(.has-video)::after,
.dual-tile:not(.has-video)::after {
  content: "";
  position: absolute;
  inset: 0;
  pointer-events: none;
  background:
    radial-gradient(circle at 50% 52%, transparent 0 13%, rgba(240, 241, 250, .026) 13.2%, transparent 13.6%),
    radial-gradient(circle at 50% 52%, transparent 0 23%, rgba(31, 213, 249, .032) 23.2%, transparent 23.55%),
    linear-gradient(rgba(240, 241, 250, .015) 1px, transparent 1px),
    linear-gradient(90deg, rgba(240, 241, 250, .015) 1px, transparent 1px);
  background-size: auto, auto, 34px 34px, 34px 34px;
  opacity: .78;
  mask-image: radial-gradient(circle at 50% 52%, rgba(0,0,0,.9), transparent 62%);
  z-index: -1;
}

.video-tile:not(.has-video)::before,
.dual-tile:not(.has-video)::before {
  content: "";
  position: absolute;
  width: 32%;
  aspect-ratio: 1;
  left: 50%;
  top: 50%;
  border-radius: 50%;
  transform: translate(-50%, -50%);
  background:
    radial-gradient(circle, rgba(31, 213, 249, .08), transparent 58%);
  filter: blur(22px);
  opacity: .7;
  pointer-events: none;
}

.video-tile:not(.is-muted)::before,
.dual-tile:not(.is-muted)::before {
  box-shadow: 0 0 0 1px rgba(31, 213, 249, .18);
}

.avatar-block {
  background:
    radial-gradient(circle at 38% 20%, rgba(31, 213, 249, .26), transparent 28%),
    radial-gradient(circle at 72% 78%, rgba(122, 255, 180, .13), transparent 34%),
    linear-gradient(145deg, rgba(240, 241, 250, .15), rgba(240, 241, 250, .038)) !important;
  border-color: rgba(240, 241, 250, .13);
}

.avatar-block::before {
  content: "";
  position: absolute;
  inset: 9px;
  border-radius: inherit;
  border: 1px solid rgba(240, 241, 250, .08);
  z-index: 1;
}

.avatar-block :deep(.agent-visualizer) {
  opacity: .2;
}

.video-tile:not(.is-muted) .avatar-block {
  box-shadow:
    inset 0 1px 0 rgba(240, 241, 250, .08),
    0 0 0 1px rgba(31, 213, 249, .14),
    0 0 42px rgba(31, 213, 249, .12),
    0 18px 46px rgba(0, 0, 0, .3);
}

.tile-info {
  align-items: flex-end;
}

.tile-name {
  min-height: 32px;
  padding: 0 12px;
  background:
    linear-gradient(180deg, rgba(18, 20, 25, .7), rgba(7, 8, 11, .68));
  border-color: rgba(240, 241, 250, .095);
  box-shadow: inset 0 1px 0 rgba(240, 241, 250, .04);
}

.icon-muted {
  background:
    linear-gradient(180deg, rgba(89, 27, 32, .84), rgba(70, 19, 24, .78));
  border-color: rgba(255, 126, 126, .28);
  color: #ffb5b5;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .055);
}

.icon-muted .lk-icon {
  width: 15px;
  height: 15px;
}

.video-tile:not(.is-muted) .tile-info::after,
.dual-tile:not(.is-muted) .tile-info::after {
  content: "";
  position: absolute;
  right: 0;
  bottom: 7px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #7affb4;
  box-shadow: 0 0 0 5px rgba(122, 255, 180, .1);
}

.sidebar-tile:not(.has-video),
.sidebar-tile-sm:not(.has-video),
.multi-tile-small:not(.has-video) {
  background:
    radial-gradient(circle at 50% 42%, rgba(31, 213, 249, .055), transparent 36%),
    #07080b;
}

.sidebar-tile .icon-muted,
.sidebar-tile-sm .icon-muted,
.multi-tile-small .icon-muted {
  width: 22px;
  height: 22px;
  border-radius: 6px;
}

.sidebar-tile .icon-muted .lk-icon,
.sidebar-tile-sm .icon-muted .lk-icon,
.multi-tile-small .icon-muted .lk-icon {
  width: 12px;
  height: 12px;
}

/* ==================== Voice Reactive Avatar ==================== */
.avatar-block {
  width: clamp(86px, 7.8vw, 124px);
  height: clamp(86px, 7.8vw, 124px);
  background:
    radial-gradient(circle at 38% 28%, rgba(230, 250, 255, .18), transparent 22%),
    radial-gradient(circle at 54% 58%, rgba(31, 213, 249, .13), transparent 40%),
    conic-gradient(from 210deg, rgba(31, 213, 249, .34), rgba(122, 255, 180, .14), rgba(240, 241, 250, .08), rgba(31, 213, 249, .34)) !important;
  border: 1px solid rgba(240, 241, 250, .16);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, .08),
    inset 0 -24px 42px rgba(5, 6, 9, .34),
    0 18px 50px rgba(0, 0, 0, .3);
}

.avatar-block::before {
  inset: 7px;
  border-color: rgba(240, 241, 250, .11);
  background:
    radial-gradient(circle at 42% 34%, rgba(240, 241, 250, .08), transparent 26%),
    rgba(5, 6, 9, .22);
}

.avatar-block::after {
  inset: 15px;
  background:
    radial-gradient(circle at 50% 48%, rgba(5, 6, 9, .04), rgba(5, 6, 9, .48) 76%),
    linear-gradient(180deg, rgba(255,255,255,.05), transparent 38%, rgba(5,6,9,.3));
}

.avatar-block :deep(.agent-visualizer) {
  opacity: .13;
  inset: -8%;
}

.avatar-text {
  z-index: 3;
  color: #f4f7ff;
  text-shadow: 0 2px 16px rgba(0, 0, 0, .42);
}

.video-tile.is-speaking,
.dual-tile.is-speaking,
.sidebar-tile.is-speaking,
.sidebar-tile-sm.is-speaking,
.multi-tile-small.is-speaking {
  border-color: rgba(122, 255, 180, .34);
}

.video-tile.is-speaking .avatar-block,
.dual-tile.is-speaking .avatar-block,
.sidebar-tile.is-speaking .avatar-block,
.sidebar-tile-sm.is-speaking .avatar-block,
.multi-tile-small.is-speaking .avatar-block {
  animation: avatar-voice 1.05s cubic-bezier(.19, 1, .22, 1) infinite;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, .1),
    inset 0 -24px 42px rgba(5, 6, 9, .3),
    0 0 0 1px rgba(122, 255, 180, .24),
    0 0 42px rgba(122, 255, 180, .16),
    0 20px 56px rgba(0, 0, 0, .34);
}

.video-tile.is-speaking .avatar-block::before,
.dual-tile.is-speaking .avatar-block::before,
.sidebar-tile.is-speaking .avatar-block::before,
.sidebar-tile-sm.is-speaking .avatar-block::before,
.multi-tile-small.is-speaking .avatar-block::before {
  animation: avatar-inner-wave 1.05s cubic-bezier(.19, 1, .22, 1) infinite;
}

.video-tile.is-speaking .avatar-block::after,
.dual-tile.is-speaking .avatar-block::after,
.sidebar-tile.is-speaking .avatar-block::after,
.sidebar-tile-sm.is-speaking .avatar-block::after,
.multi-tile-small.is-speaking .avatar-block::after {
  animation: avatar-glow-shift 1.05s cubic-bezier(.19, 1, .22, 1) infinite;
}

.video-tile.is-speaking:not(.has-video)::after,
.dual-tile.is-speaking:not(.has-video)::after {
  animation: tile-voice-wave 1.05s cubic-bezier(.19, 1, .22, 1) infinite;
  background:
    radial-gradient(circle at 50% 52%, transparent 0 13%, rgba(122, 255, 180, .12) 13.2%, transparent 13.7%),
    radial-gradient(circle at 50% 52%, transparent 0 23%, rgba(31, 213, 249, .08) 23.2%, transparent 23.7%),
    radial-gradient(circle at 50% 52%, transparent 0 33%, rgba(122, 255, 180, .045) 33.2%, transparent 33.6%),
    linear-gradient(rgba(240, 241, 250, .015) 1px, transparent 1px),
    linear-gradient(90deg, rgba(240, 241, 250, .015) 1px, transparent 1px);
  background-size: auto, auto, auto, 34px 34px, 34px 34px;
}

.video-tile.is-speaking .tile-name,
.dual-tile.is-speaking .tile-name {
  border-color: rgba(122, 255, 180, .22);
  color: #f4fff8;
}

.video-tile.is-speaking .tile-info::after,
.dual-tile.is-speaking .tile-info::after {
  animation: speaking-dot 1.05s cubic-bezier(.19, 1, .22, 1) infinite;
}

@keyframes avatar-voice {
  0%, 100% { transform: scale(1); filter: brightness(1); }
  42% { transform: scale(1.055); filter: brightness(1.12); }
  68% { transform: scale(1.025); }
}

@keyframes avatar-inner-wave {
  0%, 100% { transform: scale(.98); opacity: .72; }
  45% { transform: scale(1.08); opacity: .96; }
}

@keyframes avatar-glow-shift {
  0%, 100% { opacity: .9; transform: scale(1); }
  50% { opacity: .68; transform: scale(.94); }
}

@keyframes tile-voice-wave {
  0%, 100% { opacity: .62; filter: brightness(1); }
  50% { opacity: .96; filter: brightness(1.18); }
}

@keyframes speaking-dot {
  0%, 100% { transform: scale(.8); box-shadow: 0 0 0 4px rgba(122, 255, 180, .08); }
  50% { transform: scale(1.12); box-shadow: 0 0 0 9px rgba(122, 255, 180, 0); }
}

@media (prefers-reduced-motion: reduce) {
  .is-speaking .avatar-block,
  .is-speaking .avatar-block::before,
  .is-speaking .avatar-block::after,
  .is-speaking:not(.has-video)::after,
  .is-speaking .tile-info::after {
    animation: none !important;
  }
}

/* ==================== LiveKit-style Voice Avatar Alignment ==================== */
.video-tile:not(.has-video)::after,
.dual-tile:not(.has-video)::after {
  background:
    linear-gradient(rgba(240, 241, 250, .012) 1px, transparent 1px),
    linear-gradient(90deg, rgba(240, 241, 250, .012) 1px, transparent 1px);
  background-size: 34px 34px;
  opacity: .34;
  mask-image: linear-gradient(180deg, rgba(0,0,0,.55), transparent 86%);
  animation: none !important;
}

.video-tile:not(.has-video)::before,
.dual-tile:not(.has-video)::before {
  display: none;
}

.video-tile.is-speaking:not(.has-video)::after,
.dual-tile.is-speaking:not(.has-video)::after {
  background:
    radial-gradient(circle at 50% 50%, rgba(122, 255, 180, .045), transparent 22%),
    linear-gradient(rgba(240, 241, 250, .012) 1px, transparent 1px),
    linear-gradient(90deg, rgba(240, 241, 250, .012) 1px, transparent 1px);
  background-size: auto, 34px 34px, 34px 34px;
  opacity: .5;
  animation: none !important;
}

.video-tile .voice-avatar,
.dual-tile .voice-avatar {
  margin: auto;
}

.sidebar-tile .voice-avatar,
.sidebar-tile-sm .voice-avatar,
.multi-tile-small .voice-avatar {
  width: 112px;
  height: 60px;
}

.sidebar-tile .voice-avatar :deep(.avatar-initials),
.sidebar-tile-sm .voice-avatar :deep(.avatar-initials),
.multi-tile-small .voice-avatar :deep(.avatar-initials) {
  font-size: 15px;
}

.sidebar-tile .voice-avatar :deep(.avatar-orb),
.sidebar-tile-sm .voice-avatar :deep(.avatar-orb),
.multi-tile-small .voice-avatar :deep(.avatar-orb) {
  width: 42px;
  height: 42px;
}

.sidebar-tile .voice-avatar :deep(.avatar-core),
.sidebar-tile-sm .voice-avatar :deep(.avatar-core),
.multi-tile-small .voice-avatar :deep(.avatar-core) {
  width: 42px;
  height: 42px;
}

@media (min-width: 769px) {
  .video-grid.has-mobile-primary-video {
    position: relative;
    display: grid !important;
    grid-template-columns: 1fr !important;
    grid-template-rows: 1fr !important;
    place-items: stretch;
    padding: 18px;
    overflow: hidden;
  }

  .video-grid.has-mobile-primary-video.secondary-collapsed {
    padding: 10px;
  }

  .video-grid.has-mobile-primary-video .video-tile.mobile-primary-video {
    position: relative;
    z-index: 1;
    width: 100%;
    height: 100%;
    max-width: none;
    max-height: none;
    margin: 0;
    aspect-ratio: auto;
  }

  .video-grid.has-mobile-primary-video .video-tile:not(.mobile-primary-video) {
    position: absolute;
    z-index: 4;
    right: 34px;
    bottom: 34px;
    width: min(220px, 18vw);
    height: min(132px, 11vw);
    min-height: 112px;
    border-radius: 14px;
    box-shadow:
      inset 0 1px 0 rgba(240, 241, 250, .08),
      0 18px 46px rgba(0, 0, 0, .36);
  }

  .video-grid.has-mobile-primary-video .video-tile.mobile-secondary-2 {
    transform: translateY(calc(-100% - 14px));
  }

  .video-grid.has-mobile-primary-video .video-tile.mobile-secondary-3,
  .video-grid.has-mobile-primary-video .video-tile.mobile-secondary-4,
  .video-grid.has-mobile-primary-video .video-tile.mobile-secondary-5 {
    display: none;
  }
}

.secondary-toggle {
  position: absolute;
  z-index: 8;
  right: 28px;
  bottom: 28px;
  width: 38px;
  height: 38px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  padding: 0;
  border: 1px solid rgba(122, 255, 180, .28);
  border-radius: 999px;
  color: rgba(240, 241, 250, .86);
  background:
    radial-gradient(circle at 40% 20%, rgba(122, 255, 180, .14), transparent 34%),
    rgba(8, 10, 14, .84);
  box-shadow:
    inset 0 1px 0 rgba(240, 241, 250, .08),
    0 12px 34px rgba(0, 0, 0, .34);
  cursor: pointer;
  transition:
    width .18s ease,
    transform .18s ease,
    border-color .18s ease,
    background .18s ease;
}

.secondary-toggle:hover,
.secondary-toggle:focus-visible {
  border-color: rgba(122, 255, 180, .52);
  background:
    radial-gradient(circle at 40% 20%, rgba(122, 255, 180, .2), transparent 36%),
    rgba(12, 17, 20, .94);
  outline: none;
}

.secondary-toggle.collapsed {
  width: 58px;
}

.secondary-toggle .el-icon {
  font-size: 16px;
}

.toggle-count {
  min-width: 16px;
  font-size: 12px;
  font-weight: 800;
  color: #7affb4;
  line-height: 1;
}

@media (max-width: 768px) {
  .stage-mode-auto .video-grid.has-mobile-primary-video.primary-orientation-landscape,
  .stage-mode-landscape .video-grid.has-mobile-primary-video {
    display: grid !important;
    align-content: center !important;
    justify-items: center !important;
  }

  .stage-mode-auto .video-grid.has-mobile-primary-video.primary-orientation-landscape .video-tile.mobile-primary-video,
  .stage-mode-landscape .video-grid.has-mobile-primary-video .video-tile.mobile-primary-video {
    width: 100% !important;
    max-width: 100% !important;
    height: auto !important;
    min-height: 0 !important;
    max-height: calc(100% - 20px) !important;
    aspect-ratio: 16 / 9 !important;
    place-self: center !important;
  }

  .stage-mode-portrait .video-grid.has-mobile-primary-video {
    display: grid !important;
    align-content: center !important;
    justify-items: center !important;
  }

  .stage-mode-portrait .video-grid.has-mobile-primary-video .video-tile.mobile-primary-video {
    width: min(76vw, 360px) !important;
    max-width: 100% !important;
    height: auto !important;
    min-height: 0 !important;
    max-height: 100% !important;
    aspect-ratio: 9 / 16 !important;
    place-self: center !important;
  }
}

/* ==================== Light Theme Meeting Room Refresh ==================== */
.meeting-room {
  height: 100dvh;
  min-height: 100dvh;
  background:
    radial-gradient(circle at 12% 0%, rgba(70, 130, 255, .12), transparent 28%),
    radial-gradient(circle at 86% 8%, rgba(16, 185, 129, .1), transparent 26%),
    linear-gradient(180deg, #f7f9fc 0%, #eef3f8 100%);
  color: #172033;
}

.meeting-room:fullscreen {
  height: 100vh;
  min-height: 100vh;
  background:
    radial-gradient(circle at 12% 0%, rgba(70, 130, 255, .12), transparent 28%),
    radial-gradient(circle at 86% 8%, rgba(16, 185, 129, .1), transparent 26%),
    linear-gradient(180deg, #f7f9fc 0%, #eef3f8 100%);
}

.meeting-room::before {
  background:
    linear-gradient(rgba(43, 59, 87, .05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(43, 59, 87, .05) 1px, transparent 1px);
  background-size: 72px 72px;
  opacity: .55;
}

.room-grid-bg {
  opacity: .08;
}

.room-orbit {
  opacity: .18;
  border-color: rgba(40, 80, 130, .12);
}

.room-header {
  top: 16px;
  left: 28px;
  right: 28px;
  height: 42px;
}

.room-kicker {
  color: rgba(67, 80, 105, .48);
}

.meeting-title {
  color: #1d293d;
}

.room-header :deep(.el-tag),
.livekit-agent-chip,
.net-status,
.participant-num,
.countdown-pill {
  background: rgba(255, 255, 255, .78);
  border-color: rgba(123, 139, 169, .22);
  box-shadow: 0 12px 28px rgba(20, 35, 65, .08);
  color: #334155;
}

.room-header :deep(.el-tag) {
  color: #047857;
  background: rgba(236, 253, 245, .86);
  border-color: rgba(16, 185, 129, .22);
}

.participant-num,
.net-text {
  color: #475569;
}

.countdown-pill {
  background: rgba(255, 251, 235, .9);
  border-color: rgba(245, 158, 11, .26);
}

.countdown-time {
  color: #b45309;
}

.room-body {
  height: 100%;
  padding: 66px 28px 82px;
}

.video-area {
  border: 1px solid rgba(126, 143, 172, .24);
  border-radius: 20px;
  background:
    radial-gradient(circle at 50% 38%, rgba(59, 130, 246, .08), transparent 36%),
    linear-gradient(180deg, rgba(255, 255, 255, .9), rgba(248, 250, 252, .82));
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, .9),
    0 18px 56px rgba(31, 41, 55, .1);
}

.video-grid,
.screen-share-layout {
  padding: 18px;
}

.video-grid .video-tile:only-child,
.grid-empty {
  width: 100%;
  max-width: min(78vw, 1280px);
  max-height: min(70vh, 720px);
}

.video-tile,
.screen-tile,
.dual-tile,
.multi-tile,
.sidebar-tile,
.sidebar-tile-sm,
.multi-tile-small {
  background:
    radial-gradient(circle at 50% 42%, rgba(96, 165, 250, .06), transparent 35%),
    linear-gradient(180deg, #151923, #070a10);
  border-color: rgba(76, 95, 125, .24);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, .08),
    0 20px 48px rgba(15, 23, 42, .2);
}

.video-tile:hover,
.screen-tile:hover,
.dual-tile:hover,
.multi-tile:hover {
  border-color: rgba(59, 130, 246, .32);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, .1),
    0 22px 54px rgba(15, 23, 42, .24);
}

.video-tile:not(.is-muted),
.sidebar-tile:not(.is-muted),
.multi-tile-small:not(.is-muted) {
  border-color: rgba(37, 99, 235, .26);
}

.tile-name {
  background: rgba(15, 23, 42, .66);
  border-color: rgba(255, 255, 255, .12);
  color: rgba(248, 250, 252, .94);
}

.grid-empty {
  border-color: rgba(126, 143, 172, .24);
  background:
    radial-gradient(circle at 50% 42%, rgba(59, 130, 246, .08), transparent 32%),
    linear-gradient(180deg, #111827, #05070c);
  color: rgba(248, 250, 252, .72);
}

.side-panel,
.score-panel {
  background: rgba(255, 255, 255, .94);
  border: 1px solid rgba(126, 143, 172, .24);
  box-shadow: 0 22px 64px rgba(15, 23, 42, .14);
  color: #172033;
}

.panel-head {
  border-bottom-color: rgba(126, 143, 172, .18);
  color: #172033;
}

.panel-kicker,
.msg-sender,
.msg-time,
.score-total-label,
.score-total-max,
.score-submit-meta span {
  color: #64748b;
}

.chat-messages,
.score-body {
  background: rgba(248, 250, 252, .72);
}

.msg-body,
.score-total-bar,
.score-value-pill {
  background: #ffffff;
  border: 1px solid rgba(126, 143, 172, .18);
  color: #1e293b;
}

.chat-msg.own .msg-body {
  background: #2563eb;
  color: #ffffff;
  border-color: #2563eb;
}

.group-title {
  background: rgba(248, 250, 252, .96);
  color: #2563eb;
  border-bottom-color: rgba(37, 99, 235, .18);
}

.score-name,
.score-value-pill,
.score-number-input :deep(.el-input__inner),
.score-comment :deep(.el-textarea__inner) {
  color: #172033;
}

.score-item {
  border-bottom-color: rgba(126, 143, 172, .18);
}

.score-comment :deep(.el-textarea__inner) {
  background: #ffffff;
  border-color: rgba(126, 143, 172, .22);
}

.score-footer {
  background: linear-gradient(180deg, rgba(255, 255, 255, .84), #ffffff 34%);
  border-top-color: rgba(126, 143, 172, .18);
}

.score-footer :deep(.el-button) {
  background: #2563eb !important;
  border-color: #2563eb !important;
  color: #ffffff !important;
}

.score-submit-meta strong,
.total-val {
  color: #2563eb;
}

.control-bar {
  height: 72px;
  padding: 10px 30px 12px;
  background:
    linear-gradient(180deg, rgba(247, 249, 252, 0), rgba(247, 249, 252, .86) 28%, rgba(247, 249, 252, .98) 100%);
  border-top-color: rgba(126, 143, 172, .18);
  backdrop-filter: blur(18px);
}

.control-section {
  background: rgba(255, 255, 255, .72);
  border-color: rgba(126, 143, 172, .2);
  box-shadow: 0 12px 32px rgba(15, 23, 42, .08), inset 0 1px 0 rgba(255, 255, 255, .85);
}

.control-bar :deep(.el-button),
.audio-recorder :deep(.el-button) {
  background: rgba(255, 255, 255, .9);
  border-color: rgba(126, 143, 172, .24);
  color: #334155;
  box-shadow: 0 8px 18px rgba(15, 23, 42, .08), inset 0 1px 0 rgba(255, 255, 255, .9);
}

.control-bar :deep(.el-button:hover),
.audio-recorder :deep(.el-button:hover) {
  background: #ffffff;
  border-color: rgba(59, 130, 246, .34);
  color: #1d4ed8;
}

.btn-live {
  color: #0f766e !important;
}

.btn-live::after,
.btn-active::after {
  border-color: rgba(37, 99, 235, .14);
}

.btn-active,
.control-bar :deep(.el-button.btn-active) {
  background: #eff6ff !important;
  border-color: rgba(37, 99, 235, .28) !important;
  color: #2563eb !important;
}

.btn-off,
.control-bar :deep(.el-button.btn-off) {
  background: #fef2f2 !important;
  border-color: rgba(239, 68, 68, .26) !important;
  color: #dc2626 !important;
}

.control-bar :deep(.el-button--danger) {
  background: #fee2e2 !important;
  border-color: rgba(220, 38, 38, .26) !important;
  color: #b91c1c !important;
}

.control-bar :deep(.el-button--danger:hover) {
  background: #fecaca !important;
  color: #991b1b !important;
}

.secondary-toggle {
  background: rgba(255, 255, 255, .9);
  border-color: rgba(37, 99, 235, .28);
  color: #2563eb;
  box-shadow: 0 12px 30px rgba(15, 23, 42, .12);
}

:global(.meeting-quality-popper.el-popper),
:global(.meeting-mobile-more-popper.el-popper) {
  background: rgba(255, 255, 255, .98) !important;
  border-color: rgba(126, 143, 172, .22) !important;
  box-shadow: 0 18px 54px rgba(15, 23, 42, .16) !important;
}

:global(.meeting-quality-popper .el-dropdown-menu__item),
:global(.meeting-mobile-more-popper .el-dropdown-menu__item) {
  color: #334155 !important;
}

:global(.meeting-quality-popper .el-dropdown-menu__item:hover),
:global(.meeting-quality-popper .el-dropdown-menu__item:focus),
:global(.meeting-mobile-more-popper .el-dropdown-menu__item:hover),
:global(.meeting-mobile-more-popper .el-dropdown-menu__item:focus) {
  background: #eff6ff !important;
  color: #2563eb !important;
}

:global(.meeting-quality-popper .el-dropdown-menu__item.is-active-quality),
:global(.meeting-mobile-more-popper .el-dropdown-menu__item.is-active-quality) {
  background: #dbeafe !important;
  color: #1d4ed8 !important;
}

:global(.meeting-mobile-more-popper .mobile-menu-label),
:global(.meeting-mobile-more-popper .mobile-menu-label:hover) {
  color: #94a3b8 !important;
}

:global(.meeting-quality-popper .el-popper__arrow::before),
:global(.meeting-mobile-more-popper .el-popper__arrow::before) {
  border-color: rgba(126, 143, 172, .22) !important;
  background: rgba(255, 255, 255, .98) !important;
}

@media (max-width: 1100px) {
  .room-body {
    padding: 62px 16px 136px;
  }

  .control-bar {
    padding: 12px 16px;
  }
}

@media (max-width: 768px) {
  .meeting-room {
    height: 100dvh !important;
    min-height: 100dvh !important;
  }

  .room-header {
    background: rgba(255, 255, 255, .86) !important;
    border-bottom-color: rgba(126, 143, 172, .18) !important;
    box-shadow: 0 12px 28px rgba(15, 23, 42, .08) !important;
  }

  .room-body {
    padding: 68px 8px 126px !important;
  }

  .video-area {
    border-color: rgba(126, 143, 172, .22) !important;
    background: rgba(255, 255, 255, .82) !important;
  }

  .side-panel,
  .score-panel {
    background: rgba(255, 255, 255, .98) !important;
    border-color: rgba(126, 143, 172, .22) !important;
    box-shadow: 0 -18px 50px rgba(15, 23, 42, .14) !important;
  }

  .control-bar {
    background: rgba(255, 255, 255, .92) !important;
    border-color: rgba(126, 143, 172, .2) !important;
    box-shadow: 0 18px 54px rgba(15, 23, 42, .14) !important;
  }
}

/* ==================== OREP Themed Meeting Workspace ==================== */
.meeting-room {
  height: 100dvh;
  min-height: 100dvh;
  background:
    radial-gradient(circle at 18% 10%, rgba(0, 122, 255, .1), transparent 30%),
    radial-gradient(circle at 84% 8%, rgba(88, 86, 214, .075), transparent 28%),
    linear-gradient(180deg, #f6f8fc 0%, #eef3f8 58%, #e8eef6 100%);
  color: var(--text-primary, #1d1d1f);
}

.meeting-room:fullscreen {
  height: 100vh;
  min-height: 100vh;
  background:
    radial-gradient(circle at 18% 10%, rgba(0, 122, 255, .1), transparent 30%),
    radial-gradient(circle at 84% 8%, rgba(88, 86, 214, .075), transparent 28%),
    linear-gradient(180deg, #f6f8fc 0%, #eef3f8 58%, #e8eef6 100%);
}

.meeting-room::before {
  background:
    linear-gradient(rgba(29, 29, 31, .035) 1px, transparent 1px),
    linear-gradient(90deg, rgba(29, 29, 31, .035) 1px, transparent 1px);
  background-size: 86px 86px;
  opacity: .62;
}

.room-grid-bg {
  opacity: .06;
}

.room-orbit {
  opacity: .14;
  border-color: rgba(0, 122, 255, .12);
}

.room-header {
  top: 18px;
  right: 34px;
  left: 34px;
  height: 48px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
}

.header-left {
  gap: 12px;
}

.meeting-title-wrap {
  gap: 3px;
}

.room-kicker {
  color: var(--text-tertiary, #8e8e93);
  font-size: 10px;
  letter-spacing: .28em;
}

.meeting-title {
  color: var(--text-primary, #1d1d1f);
  font-size: 16px;
  font-weight: 800;
  letter-spacing: -.01em;
  max-width: 42vw;
}

.room-header :deep(.el-tag),
.net-status,
.participant-num,
.countdown-pill {
  height: 34px;
  min-height: 34px;
  padding: 0 14px;
  border-radius: 999px;
  background: rgba(255, 255, 255, .72);
  border: 1px solid rgba(209, 217, 230, .88);
  box-shadow: 0 10px 24px rgba(31, 35, 45, .06);
  color: var(--text-secondary, #3a3a3c);
}

.room-header :deep(.el-tag) {
  background: rgba(232, 249, 240, .96);
  border-color: rgba(48, 209, 88, .22);
  color: #188038;
  font-weight: 760;
}

.net-status {
  gap: 7px;
}

.participant-num {
  gap: 7px;
}

.participant-num span,
.countdown-label {
  display: inline;
  color: var(--text-tertiary, #8e8e93);
  font-size: 12px;
  font-weight: 700;
}

.participant-num strong,
.countdown-time,
.net-text {
  color: var(--text-primary, #1d1d1f);
  font-size: 13px;
  font-weight: 800;
}

.countdown-pill {
  background: rgba(255, 247, 237, .96);
  border-color: rgba(255, 149, 0, .22);
}

.countdown-time {
  color: #c05621;
}

.room-body {
  height: 100%;
  padding: 78px 34px 92px;
}

.video-area {
  position: relative;
  border: 1px solid rgba(209, 217, 230, .95);
  border-radius: 26px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, .82), rgba(248, 250, 255, .72));
  box-shadow:
    0 22px 58px rgba(31, 35, 45, .1),
    inset 0 1px 0 rgba(255, 255, 255, .94);
  padding: 20px;
}

.video-area::before {
  content: "";
  position: absolute;
  inset: 20px;
  border-radius: 18px;
  border: 1px solid rgba(255, 255, 255, .08);
  pointer-events: none;
  z-index: 2;
}

.video-grid,
.screen-share-layout {
  padding: 0;
  gap: 16px;
}

.video-grid .video-tile:only-child,
.grid-empty {
  width: 100%;
  max-width: none;
  max-height: none;
  height: 100%;
  aspect-ratio: auto;
  margin: 0;
}

.video-tile,
.screen-tile,
.dual-tile,
.multi-tile {
  border-radius: 16px;
  background:
    radial-gradient(circle at 28% 12%, rgba(0, 122, 255, .055), transparent 26%),
    linear-gradient(180deg, #0c1118 0%, #05070c 100%);
  border: 1px solid rgba(15, 23, 42, .7);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, .06),
    0 18px 38px rgba(15, 23, 42, .18);
}

.video-tile:hover,
.screen-tile:hover,
.dual-tile:hover,
.multi-tile:hover {
  border-color: rgba(0, 122, 255, .42);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, .08),
    0 22px 46px rgba(15, 23, 42, .22);
}

.video-tile:not(.has-video),
.dual-tile:not(.has-video),
.grid-empty {
  background:
    radial-gradient(circle at 50% 48%, rgba(0, 122, 255, .04), transparent 26%),
    linear-gradient(rgba(255, 255, 255, .018) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, .018) 1px, transparent 1px),
    linear-gradient(180deg, #0d1219 0%, #05070c 100%);
  background-size: auto, 44px 44px, 44px 44px, auto;
}

.avatar-block {
  background:
    radial-gradient(circle at 38% 28%, rgba(255, 255, 255, .16), transparent 23%),
    radial-gradient(circle at 60% 62%, rgba(0, 122, 255, .15), transparent 40%),
    conic-gradient(from 210deg, rgba(0, 122, 255, .34), rgba(52, 199, 89, .13), rgba(255, 255, 255, .08), rgba(0, 122, 255, .34)) !important;
  border-color: rgba(255, 255, 255, .14);
}

.tile-info {
  left: 20px;
  right: 20px;
  bottom: 18px;
}

.tile-name {
  min-height: 34px;
  padding: 0 14px;
  background: rgba(15, 23, 42, .74);
  border: 1px solid rgba(255, 255, 255, .14);
  color: rgba(255, 255, 255, .94);
  font-weight: 800;
}

.side-panel,
.score-panel {
  width: 400px;
  border-radius: 22px;
  background: rgba(255, 255, 255, .96);
  border: 1px solid rgba(209, 217, 230, .95);
  box-shadow: 0 22px 58px rgba(31, 35, 45, .14);
  color: var(--text-primary, #1d1d1f);
}

.panel-head {
  min-height: 64px;
  padding: 0 22px;
  border-bottom-color: rgba(209, 217, 230, .78);
  color: var(--text-primary, #1d1d1f);
}

.panel-kicker,
.msg-sender,
.msg-time,
.score-total-label,
.score-total-max,
.score-submit-meta span {
  color: var(--text-tertiary, #8e8e93);
}

.chat-messages,
.score-body {
  background: #f8fafc;
}

.msg-body,
.score-total-bar,
.score-value-pill {
  background: #ffffff;
  border-color: rgba(209, 217, 230, .9);
  color: var(--text-primary, #1d1d1f);
}

.chat-msg.own .msg-body {
  background: var(--primary-color, #007aff);
  border-color: var(--primary-color, #007aff);
  color: #ffffff;
}

.group-title {
  background: #f8fafc;
  color: var(--primary-color, #007aff);
  border-bottom-color: rgba(0, 122, 255, .18);
}

.score-name,
.score-value-pill,
.score-number-input :deep(.el-input__inner),
.score-comment :deep(.el-textarea__inner) {
  color: var(--text-primary, #1d1d1f);
}

.score-comment :deep(.el-textarea__inner) {
  background: #ffffff;
  border-color: rgba(209, 217, 230, .9);
}

.score-footer {
  background: linear-gradient(180deg, rgba(255, 255, 255, .84), #ffffff 34%);
  border-top-color: rgba(209, 217, 230, .9);
}

.score-footer :deep(.el-button) {
  background: var(--primary-color, #007aff) !important;
  border-color: var(--primary-color, #007aff) !important;
  color: #ffffff !important;
}

.score-submit-meta strong,
.total-val,
.toggle-count {
  color: var(--primary-color, #007aff);
}

.control-bar {
  height: 82px;
  padding: 10px 34px 16px;
  background:
    linear-gradient(180deg, rgba(238, 243, 248, 0), rgba(238, 243, 248, .86) 24%, rgba(238, 243, 248, .98) 100%);
  border-top: 1px solid rgba(209, 217, 230, .78);
  backdrop-filter: blur(18px);
}

.control-section {
  min-height: 54px;
  gap: 8px;
  padding: 6px;
  border-radius: 18px;
  background: rgba(255, 255, 255, .82);
  border: 1px solid rgba(209, 217, 230, .9);
  box-shadow: 0 14px 34px rgba(31, 35, 45, .09), inset 0 1px 0 rgba(255, 255, 255, .94);
}

.control-bar :deep(.el-button),
.audio-recorder :deep(.el-button) {
  width: 44px;
  height: 44px;
  background: #ffffff;
  border-color: rgba(209, 217, 230, .96);
  color: var(--text-secondary, #3a3a3c);
  box-shadow: 0 8px 18px rgba(31, 35, 45, .07);
}

.control-bar :deep(.el-button:hover),
.audio-recorder :deep(.el-button:hover) {
  transform: translateY(-1px);
  background: #f5f9ff;
  border-color: rgba(0, 122, 255, .3);
  color: var(--primary-color, #007aff);
}

.control-bar :deep(.el-button.is-round) {
  height: 44px;
  min-width: 132px;
}

.btn-live {
  color: #188038 !important;
}

.btn-active,
.control-bar :deep(.el-button.btn-active) {
  background: #eaf4ff !important;
  border-color: rgba(0, 122, 255, .28) !important;
  color: var(--primary-color, #007aff) !important;
}

.btn-off,
.control-bar :deep(.el-button.btn-off) {
  background: #fff1f0 !important;
  border-color: rgba(255, 59, 48, .25) !important;
  color: #d93025 !important;
}

.control-bar :deep(.el-button--danger) {
  min-width: 128px;
  background: #fff1f0 !important;
  border-color: rgba(255, 59, 48, .25) !important;
  color: #d93025 !important;
}

.control-bar :deep(.el-button--danger:hover) {
  background: #ffe4e1 !important;
  color: #b3261e !important;
}

.secondary-toggle {
  background: rgba(255, 255, 255, .92);
  border-color: rgba(0, 122, 255, .25);
  color: var(--primary-color, #007aff);
}

@media (max-width: 1100px) {
  .room-header {
    left: 18px;
    right: 18px;
  }

  .room-body {
    padding: 72px 18px 142px;
  }
}

@media (max-width: 768px) {
  .meeting-room {
    height: 100dvh !important;
    min-height: 100dvh !important;
  }

  .room-header {
    left: 0 !important;
    right: 0 !important;
    min-height: 60px !important;
    background: rgba(248, 250, 252, .92) !important;
    border-bottom: 1px solid rgba(209, 217, 230, .9) !important;
    box-shadow: 0 10px 28px rgba(31, 35, 45, .08) !important;
  }

  .meeting-title {
    max-width: 40vw !important;
    font-size: 13px !important;
  }

  .room-body {
    padding: 70px 8px 128px !important;
  }

  .video-area {
    padding: 10px !important;
    border-radius: 20px !important;
    background: rgba(255, 255, 255, .78) !important;
  }

  .video-area::before {
    inset: 10px;
    border-radius: 14px;
  }

  .control-bar {
    background: rgba(248, 250, 252, .94) !important;
    border-color: rgba(209, 217, 230, .9) !important;
    box-shadow: 0 18px 48px rgba(31, 35, 45, .14) !important;
  }
}

/* ==================== Meeting Top Bar Refinement ==================== */
.room-header {
  top: 18px;
  right: 40px;
  left: 40px;
  height: 46px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 16px;
}

.room-header .header-left,
.room-header .header-right {
  min-height: 46px;
  display: inline-flex;
  align-items: center;
  gap: 10px;
}

.room-header .header-left {
  min-width: 0;
  justify-self: start;
  padding: 7px 10px 7px 12px;
  border: 1px solid rgba(209, 217, 230, .72);
  border-radius: 18px;
  background: rgba(255, 255, 255, .42);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .72);
  backdrop-filter: blur(14px);
}

.room-header .header-right {
  justify-self: end;
  padding: 5px;
  border: 1px solid rgba(209, 217, 230, .78);
  border-radius: 999px;
  background: rgba(255, 255, 255, .52);
  box-shadow: 0 12px 28px rgba(31, 35, 45, .06), inset 0 1px 0 rgba(255, 255, 255, .78);
  backdrop-filter: blur(16px);
}

.meeting-title-wrap {
  min-width: 0;
  display: grid;
  grid-template-columns: auto minmax(0, auto);
  align-items: baseline;
  column-gap: 10px;
  row-gap: 0;
}

.room-kicker {
  color: var(--text-tertiary, #8e8e93);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: .08em;
}

.room-kicker::after {
  content: "";
  display: inline-block;
  width: 1px;
  height: 12px;
  margin-left: 10px;
  vertical-align: -1px;
  background: rgba(142, 142, 147, .28);
}

.meeting-title {
  color: var(--text-primary, #1d1d1f);
  font-size: 17px;
  font-weight: 850;
  letter-spacing: -.02em;
  max-width: min(34vw, 520px);
}

.room-header :deep(.el-tag) {
  height: 32px;
  min-height: 32px;
  padding: 0 13px;
  border-radius: 999px;
  background: #e8f9f0;
  border: 1px solid rgba(48, 209, 88, .24);
  color: #188038;
  box-shadow: none;
  font-size: 13px;
  font-weight: 800;
}

.net-status,
.participant-num,
.countdown-pill {
  height: 34px;
  min-height: 34px;
  padding: 0 13px;
  border-radius: 999px;
  background: rgba(255, 255, 255, .76);
  border: 1px solid rgba(209, 217, 230, .74);
  box-shadow: none;
}

.net-status {
  min-width: 76px;
  justify-content: center;
  color: #188038;
  font-weight: 800;
}

.participant-num {
  min-width: 90px;
  justify-content: center;
}

.participant-num span,
.countdown-label {
  display: inline;
  color: var(--text-tertiary, #8e8e93);
  font-size: 12px;
  font-weight: 750;
}

.participant-num strong,
.countdown-time,
.net-text {
  color: var(--text-primary, #1d1d1f);
  font-size: 13px;
  font-weight: 850;
}

.countdown-pill {
  min-width: 128px;
  justify-content: center;
  gap: 7px;
  background: #fff7ed;
  border-color: rgba(255, 149, 0, .24);
}

.countdown-time {
  color: #c05621;
}

@media (max-width: 1100px) {
  .room-header {
    left: 18px;
    right: 18px;
    gap: 10px;
  }

  .meeting-title {
    max-width: 30vw;
  }
}

@media (max-width: 768px) {
  .room-header {
    height: auto !important;
    min-height: 60px !important;
    grid-template-columns: minmax(0, 1fr) auto !important;
    gap: 8px !important;
    padding: 8px 10px !important;
  }

  .room-header .header-left,
  .room-header .header-right {
    min-height: 0 !important;
    padding: 0 !important;
    border: 0 !important;
    background: transparent !important;
    box-shadow: none !important;
  }

  .meeting-title-wrap {
    grid-template-columns: 1fr !important;
    gap: 1px !important;
  }

  .room-kicker {
    font-size: 11px !important;
    letter-spacing: .04em !important;
  }

  .room-kicker::after {
    display: none !important;
  }

  .meeting-title {
    max-width: 42vw !important;
    font-size: 13px !important;
  }

  .net-status {
    min-width: 34px !important;
  }

  .participant-num,
  .countdown-pill {
    min-width: 0 !important;
  }
}

/* ==================== Flat Meeting Header ==================== */
.room-header {
  top: 22px;
  right: 42px;
  left: 42px;
  height: 40px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 18px;
}

.room-header .header-left,
.room-header .header-right {
  min-height: 0;
  padding: 0;
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
}

.room-header .header-left {
  display: inline-flex;
  align-items: center;
  justify-self: start;
  gap: 12px;
}

.room-header .header-right {
  display: inline-flex;
  align-items: center;
  justify-self: end;
  gap: 12px;
}

.meeting-title-wrap {
  display: inline-flex;
  align-items: center;
  gap: 0;
}

.room-kicker {
  color: var(--text-tertiary, #8e8e93);
  font-size: 13px;
  font-weight: 750;
  letter-spacing: .02em;
}

.room-kicker::after {
  display: none;
}

.meeting-title {
  max-width: min(36vw, 520px);
  color: var(--text-primary, #1d1d1f);
  font-size: 18px;
  font-weight: 850;
  letter-spacing: -.02em;
}

.room-header :deep(.el-tag) {
  height: 30px;
  min-height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  background: rgba(232, 249, 240, .92);
  border: 1px solid rgba(48, 209, 88, .24);
  color: #188038;
  box-shadow: none;
  font-size: 13px;
  font-weight: 800;
}

.net-status,
.participant-num,
.countdown-pill {
  height: 30px;
  min-height: 30px;
  padding: 0;
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

.net-status {
  min-width: 0;
  gap: 6px;
}

.signal-bars {
  height: 16px;
  gap: 3px;
}

.bar {
  width: 4px;
  border-radius: 999px;
  background: rgba(29, 29, 31, .24);
}

.signal-bars[data-level="0"] .bar {
  background: rgba(29, 29, 31, .32);
}

.signal-bars[data-level="1"] .b1 {
  background: #ff3b30;
}

.signal-bars[data-level="1"] .b2,
.signal-bars[data-level="1"] .b3 {
  background: rgba(255, 59, 48, .2);
}

.signal-bars[data-level="2"] .b1,
.signal-bars[data-level="2"] .b2 {
  background: #ff9500;
}

.signal-bars[data-level="2"] .b3 {
  background: rgba(255, 149, 0, .22);
}

.signal-bars[data-level="3"] .b1,
.signal-bars[data-level="3"] .b2,
.signal-bars[data-level="3"] .b3 {
  background: #30d158;
}

.net-text {
  color: #188038 !important;
  font-size: 14px;
  font-weight: 850;
}

.participant-num {
  gap: 6px;
  color: var(--text-secondary, #3a3a3c);
}

.participant-num .el-icon {
  color: var(--text-secondary, #3a3a3c);
}

.participant-num span,
.countdown-label {
  display: inline;
  color: var(--text-secondary, #3a3a3c);
  font-size: 13px;
  font-weight: 700;
}

.participant-num strong,
.countdown-time {
  color: var(--text-primary, #1d1d1f);
  font-size: 14px;
  font-weight: 850;
}

.countdown-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.countdown-time {
  color: #c05621;
}

@media (max-width: 1100px) {
  .room-header {
    right: 20px;
    left: 20px;
  }

  .meeting-title {
    max-width: 34vw;
  }
}

@media (max-width: 768px) {
  .room-header {
    top: 0 !important;
    right: 0 !important;
    left: 0 !important;
    min-height: 58px !important;
    padding: 8px 10px !important;
    background: rgba(248, 250, 252, .9) !important;
    border-bottom: 1px solid rgba(209, 217, 230, .75) !important;
  }

  .meeting-title-wrap {
    display: grid !important;
    grid-template-columns: 1fr !important;
    gap: 1px !important;
  }

  .room-kicker {
    font-size: 12px !important;
  }

  .meeting-title {
    max-width: 42vw !important;
    font-size: 13px !important;
  }
}

/* ==================== Single Layer Video Window ==================== */
.room-body {
  padding: 78px 40px 92px;
}

.video-area {
  padding: 0;
  border: 0;
  border-radius: 18px;
  background: transparent;
  box-shadow: 0 18px 42px rgba(15, 23, 42, .14);
  overflow: hidden;
}

.video-area::before {
  display: none;
}

.video-grid,
.screen-share-layout {
  padding: 0;
  gap: 0;
}

.video-grid .video-tile:only-child,
.grid-empty,
.video-tile,
.screen-tile,
.dual-tile,
.multi-tile,
.screen-main {
  border-radius: 18px;
}

.video-tile,
.screen-tile,
.dual-tile,
.multi-tile {
  border: 1px solid rgba(15, 23, 42, .84);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .055);
}

.video-grid .video-tile:only-child,
.grid-empty {
  width: 100%;
  height: 100%;
  max-width: none;
  max-height: none;
  margin: 0;
}

@media (max-width: 1100px) {
  .room-body {
    padding: 72px 20px 142px;
  }
}

@media (max-width: 768px) {
  .room-body {
    padding: 70px 8px 128px !important;
  }

  .video-area {
    padding: 0 !important;
    border: 0 !important;
    border-radius: 16px !important;
    background: transparent !important;
    box-shadow: 0 12px 28px rgba(15, 23, 42, .14) !important;
  }
}

/* ==================== True Single Video Surface ==================== */
.video-area {
  padding: 0 !important;
  border: 0 !important;
  border-radius: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
}

.video-area::before,
.video-area::after {
  display: none !important;
}

.video-grid,
.screen-share-layout {
  width: 100% !important;
  height: 100% !important;
  padding: 0 !important;
  gap: 0 !important;
}

.video-grid .video-tile:only-child,
.grid-empty {
  width: 100% !important;
  height: 100% !important;
  max-width: none !important;
  max-height: none !important;
  margin: 0 !important;
  aspect-ratio: auto !important;
}

.video-tile,
.screen-tile,
.dual-tile,
.multi-tile,
.grid-empty {
  border-radius: 18px !important;
}

/* ==================== Camera-On Stage Layout ==================== */
@media (min-width: 769px) {
  .video-grid.has-mobile-primary-video {
    position: relative !important;
    display: grid !important;
    grid-template-columns: 1fr !important;
    grid-template-rows: 1fr !important;
    padding: 0 !important;
    overflow: hidden !important;
  }

  .video-grid.has-mobile-primary-video .video-tile.mobile-primary-video {
    position: relative !important;
    z-index: 1 !important;
    width: 100% !important;
    height: 100% !important;
    max-width: none !important;
    max-height: none !important;
    margin: 0 !important;
    border-radius: 18px !important;
    aspect-ratio: auto !important;
  }

  .video-grid.has-mobile-primary-video .video-tile.mobile-primary-video video {
    object-fit: contain !important;
    background: #05070c;
  }

  .video-grid.has-mobile-primary-video .video-tile:not(.mobile-primary-video) {
    position: absolute !important;
    z-index: 6 !important;
    right: 22px !important;
    bottom: 58px !important;
    width: clamp(150px, 12vw, 210px) !important;
    height: clamp(92px, 7.2vw, 126px) !important;
    min-height: 0 !important;
    max-width: none !important;
    border-radius: 16px !important;
    border: 1px solid rgba(255, 255, 255, .16) !important;
    background: rgba(5, 7, 12, .92) !important;
    box-shadow: 0 16px 38px rgba(0, 0, 0, .36), inset 0 1px 0 rgba(255, 255, 255, .06) !important;
    overflow: hidden !important;
  }

  .video-grid.has-mobile-primary-video .video-tile:not(.mobile-primary-video) video {
    object-fit: cover !important;
  }

  .video-grid.has-mobile-primary-video .video-tile.mobile-secondary-2 {
    transform: translateY(calc(-100% - 12px)) !important;
  }

  .video-grid.has-mobile-primary-video .video-tile.mobile-secondary-3,
  .video-grid.has-mobile-primary-video .video-tile.mobile-secondary-4,
  .video-grid.has-mobile-primary-video .video-tile.mobile-secondary-5 {
    display: none !important;
  }

  .video-grid.has-mobile-primary-video .video-tile:not(.mobile-primary-video) .voice-avatar {
    width: 100% !important;
    height: 100% !important;
  }

  .video-grid.has-mobile-primary-video .video-tile:not(.mobile-primary-video) .avatar-block,
  .video-grid.has-mobile-primary-video .video-tile:not(.mobile-primary-video) .voice-avatar :deep(.avatar-orb),
  .video-grid.has-mobile-primary-video .video-tile:not(.mobile-primary-video) .voice-avatar :deep(.avatar-core) {
    width: 50px !important;
    height: 50px !important;
  }

  .video-grid.has-mobile-primary-video .video-tile:not(.mobile-primary-video) .avatar-text,
  .video-grid.has-mobile-primary-video .video-tile:not(.mobile-primary-video) .voice-avatar :deep(.avatar-initials) {
    font-size: 18px !important;
  }

  .video-grid.has-mobile-primary-video .video-tile:not(.mobile-primary-video) .tile-info {
    left: 10px !important;
    right: 10px !important;
    bottom: 8px !important;
  }

  .video-grid.has-mobile-primary-video .video-tile:not(.mobile-primary-video) .tile-name {
    max-width: calc(100% - 34px) !important;
    min-height: 24px !important;
    padding: 0 9px !important;
    font-size: 11px !important;
  }

  .video-grid.has-mobile-primary-video .video-tile:not(.mobile-primary-video) .icon-muted {
    position: absolute !important;
    right: 10px !important;
    bottom: 8px !important;
    z-index: 9 !important;
    width: 24px !important;
    height: 24px !important;
    border-radius: 7px !important;
  }

  .video-grid.has-mobile-primary-video .secondary-toggle {
    right: 18px !important;
    bottom: 150px !important;
    z-index: 8 !important;
    width: 34px !important;
    height: 34px !important;
    background: rgba(255, 255, 255, .92) !important;
    border-color: rgba(255, 255, 255, .48) !important;
    color: #0f172a !important;
    box-shadow: 0 10px 24px rgba(0, 0, 0, .24) !important;
  }

  .video-grid.has-mobile-primary-video:not(.secondary-collapsed) .secondary-toggle {
    transform: none !important;
  }

  .video-grid.has-mobile-primary-video.secondary-collapsed .video-tile:not(.mobile-primary-video) {
    display: none !important;
  }
}

/* ==================== Desktop Multi Participant Layout ==================== */
@media (min-width: 769px) {
  .video-grid.has-mobile-primary-video {
    display: grid !important;
    grid-template-columns: minmax(0, 1fr) clamp(176px, 12vw, 220px) !important;
    grid-auto-rows: clamp(96px, 13.6vh, 150px) !important;
    align-content: center !important;
    align-items: stretch !important;
    gap: 12px !important;
    padding: 0 !important;
    overflow: hidden !important;
  }

  .video-grid.has-mobile-primary-video.secondary-collapsed {
    grid-template-columns: minmax(0, 1fr) !important;
  }

  .video-grid.has-mobile-primary-video .video-tile.mobile-primary-video {
    grid-column: 1 !important;
    grid-row: 1 / span 5 !important;
    position: relative !important;
    width: 100% !important;
    height: 100% !important;
    min-height: 0 !important;
    max-width: none !important;
    max-height: none !important;
    margin: 0 !important;
    border-radius: 18px !important;
    aspect-ratio: auto !important;
  }

  .video-grid.has-mobile-primary-video .video-tile.mobile-primary-video video {
    object-fit: contain !important;
    background: #05070c;
  }

  .video-grid.has-mobile-primary-video .video-tile:not(.mobile-primary-video) {
    position: relative !important;
    right: auto !important;
    bottom: auto !important;
    z-index: 3 !important;
    grid-column: 2 !important;
    width: 100% !important;
    height: 100% !important;
    min-height: 0 !important;
    max-width: none !important;
    border-radius: 14px !important;
    border: 1px solid rgba(255, 255, 255, .14) !important;
    background: rgba(5, 7, 12, .92) !important;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, .055) !important;
    transform: none !important;
  }

  .video-grid.has-mobile-primary-video .video-tile.mobile-secondary-2,
  .video-grid.has-mobile-primary-video .video-tile.mobile-secondary-3,
  .video-grid.has-mobile-primary-video .video-tile.mobile-secondary-4,
  .video-grid.has-mobile-primary-video .video-tile.mobile-secondary-5 {
    display: flex !important;
    transform: none !important;
  }

  .video-grid.has-mobile-primary-video.secondary-collapsed .video-tile:not(.mobile-primary-video) {
    display: none !important;
  }

  .video-grid.has-mobile-primary-video .video-tile:not(.mobile-primary-video) video {
    object-fit: cover !important;
  }

  .video-grid.has-mobile-primary-video .video-tile:not(.mobile-primary-video) .voice-avatar {
    width: 100% !important;
    height: 100% !important;
  }

  .video-grid.has-mobile-primary-video .video-tile:not(.mobile-primary-video) .tile-info {
    left: 8px !important;
    right: 8px !important;
    bottom: 8px !important;
  }

  .video-grid.has-mobile-primary-video .video-tile:not(.mobile-primary-video) .tile-name {
    max-width: calc(100% - 34px) !important;
    min-height: 24px !important;
    padding: 0 9px !important;
    font-size: 11px !important;
  }

  .video-grid.has-mobile-primary-video .video-tile:not(.mobile-primary-video) .icon-muted {
    position: absolute !important;
    right: 8px !important;
    bottom: 8px !important;
    z-index: 8 !important;
    width: 24px !important;
    height: 24px !important;
    border-radius: 7px !important;
  }

  .video-grid.has-mobile-primary-video .secondary-toggle {
    position: absolute !important;
    z-index: 10 !important;
    right: calc(clamp(176px, 12vw, 220px) + 8px) !important;
    bottom: 18px !important;
    width: 34px !important;
    height: 34px !important;
    transform: none !important;
    background: rgba(255, 255, 255, .92) !important;
    border-color: rgba(255, 255, 255, .5) !important;
    color: #0f172a !important;
    box-shadow: 0 10px 24px rgba(0, 0, 0, .22) !important;
  }

  .video-grid.has-mobile-primary-video.secondary-collapsed .secondary-toggle {
    right: 18px !important;
  }
}

/* ==================== Stable Participant Sidebar ==================== */
@media (min-width: 769px) {
  .video-grid.has-mobile-primary-video {
    grid-template-columns: minmax(0, 1fr) clamp(188px, 12.5vw, 228px) !important;
    grid-auto-rows: 126px !important;
    align-content: start !important;
    align-items: stretch !important;
    gap: 12px !important;
  }

  .video-grid.has-mobile-primary-video .video-tile.mobile-primary-video {
    grid-row: 1 / -1 !important;
    min-height: 0 !important;
  }

  .video-grid.has-mobile-primary-video .video-tile:not(.mobile-primary-video) {
    width: 100% !important;
    height: 126px !important;
    min-height: 126px !important;
    max-height: 126px !important;
    align-self: stretch !important;
  }

  .video-grid.has-mobile-primary-video .video-tile.mobile-secondary-2,
  .video-grid.has-mobile-primary-video .video-tile.mobile-secondary-3,
  .video-grid.has-mobile-primary-video .video-tile.mobile-secondary-4,
  .video-grid.has-mobile-primary-video .video-tile.mobile-secondary-5 {
    display: flex !important;
    transform: none !important;
  }

  .video-grid.has-mobile-primary-video .secondary-toggle {
    top: 50% !important;
    right: calc(clamp(188px, 12.5vw, 228px) + 6px) !important;
    bottom: auto !important;
    transform: translateY(-50%) !important;
  }

  .video-grid.has-mobile-primary-video.secondary-collapsed .secondary-toggle {
    right: 18px !important;
    transform: translateY(-50%) !important;
  }

  .video-grid.has-mobile-primary-video .video-tile.mobile-primary-video .icon-muted {
    right: 18px !important;
    bottom: 18px !important;
    z-index: 9 !important;
  }
}

/* ==================== Mature Meeting Speaker Layout ==================== */
@media (min-width: 769px) {
  .video-grid.has-mobile-primary-video {
    width: 100% !important;
    height: 100% !important;
    display: grid !important;
    grid-template-columns: minmax(0, 1fr) 224px !important;
    grid-auto-rows: 126px !important;
    align-content: start !important;
    align-items: stretch !important;
    gap: 12px !important;
    padding: 12px !important;
    border-radius: 18px !important;
    background: #05070c !important;
    overflow: hidden !important;
  }

  .video-grid.has-mobile-primary-video.secondary-collapsed {
    grid-template-columns: minmax(0, 1fr) !important;
    padding: 0 !important;
  }

  .video-grid.has-mobile-primary-video .video-tile.mobile-primary-video {
    grid-column: 1 !important;
    grid-row: 1 / -1 !important;
    position: relative !important;
    width: 100% !important;
    height: 100% !important;
    min-height: 0 !important;
    max-width: none !important;
    max-height: none !important;
    margin: 0 !important;
    border-radius: 14px !important;
    border-color: rgba(255, 255, 255, .08) !important;
    background: #05070c !important;
    aspect-ratio: auto !important;
  }

  .video-grid.has-mobile-primary-video .video-tile.mobile-primary-video video {
    width: 100% !important;
    height: 100% !important;
    object-fit: contain !important;
    background: #05070c !important;
  }

  .video-grid.has-mobile-primary-video .video-tile:not(.mobile-primary-video) {
    grid-column: 2 !important;
    position: relative !important;
    right: auto !important;
    bottom: auto !important;
    z-index: 3 !important;
    width: 100% !important;
    height: 126px !important;
    min-height: 126px !important;
    max-height: 126px !important;
    max-width: none !important;
    border-radius: 14px !important;
    border: 1px solid rgba(255, 255, 255, .1) !important;
    background: #11151c !important;
    box-shadow: none !important;
    transform: none !important;
    overflow: hidden !important;
  }

  .video-grid.has-mobile-primary-video .video-tile.mobile-secondary-2,
  .video-grid.has-mobile-primary-video .video-tile.mobile-secondary-3,
  .video-grid.has-mobile-primary-video .video-tile.mobile-secondary-4,
  .video-grid.has-mobile-primary-video .video-tile.mobile-secondary-5 {
    display: flex !important;
    transform: none !important;
  }

  .video-grid.has-mobile-primary-video .video-tile:not(.mobile-primary-video) video {
    object-fit: cover !important;
  }

  .video-grid.has-mobile-primary-video .video-tile:not(.mobile-primary-video) .voice-avatar {
    width: 100% !important;
    height: 100% !important;
  }

  .video-grid.has-mobile-primary-video .video-tile:not(.mobile-primary-video) .avatar-block,
  .video-grid.has-mobile-primary-video .video-tile:not(.mobile-primary-video) .voice-avatar :deep(.avatar-orb),
  .video-grid.has-mobile-primary-video .video-tile:not(.mobile-primary-video) .voice-avatar :deep(.avatar-core) {
    width: 54px !important;
    height: 54px !important;
  }

  .video-grid.has-mobile-primary-video .video-tile:not(.mobile-primary-video) .avatar-text,
  .video-grid.has-mobile-primary-video .video-tile:not(.mobile-primary-video) .voice-avatar :deep(.avatar-initials) {
    font-size: 18px !important;
  }

  .video-grid.has-mobile-primary-video .video-tile:not(.mobile-primary-video) .tile-info {
    left: 8px !important;
    right: 8px !important;
    bottom: 8px !important;
  }

  .video-grid.has-mobile-primary-video .video-tile:not(.mobile-primary-video) .tile-name {
    max-width: calc(100% - 34px) !important;
    min-height: 24px !important;
    padding: 0 9px !important;
    font-size: 11px !important;
  }

  .video-grid.has-mobile-primary-video .video-tile:not(.mobile-primary-video) .icon-muted {
    position: absolute !important;
    right: 8px !important;
    bottom: 8px !important;
    z-index: 8 !important;
    width: 24px !important;
    height: 24px !important;
    border-radius: 7px !important;
  }

  .video-grid.has-mobile-primary-video .secondary-toggle {
    position: absolute !important;
    top: 50% !important;
    right: 224px !important;
    bottom: auto !important;
    z-index: 10 !important;
    width: 32px !important;
    height: 48px !important;
    border-radius: 999px 0 0 999px !important;
    transform: translateY(-50%) !important;
    background: rgba(255, 255, 255, .9) !important;
    border: 1px solid rgba(255, 255, 255, .48) !important;
    color: #0f172a !important;
    box-shadow: 0 10px 24px rgba(0, 0, 0, .24) !important;
  }

  .video-grid.has-mobile-primary-video.secondary-collapsed .secondary-toggle {
    right: 0 !important;
  }

  .video-grid.has-mobile-primary-video.secondary-collapsed .video-tile:not(.mobile-primary-video) {
    display: none !important;
  }
}

/* ==================== Unified Meeting Filmstrip ==================== */
@media (min-width: 769px) {
  .screen-share-layout.layout-default,
  .screen-share-layout.layout-dual {
    --filmstrip-width: 228px;
    --filmstrip-gap: 12px;
    --stage-pad: 12px;
    display: flex !important;
    gap: var(--filmstrip-gap) !important;
    padding: var(--stage-pad) !important;
    border-radius: 18px !important;
    background: #05070c !important;
    overflow: hidden !important;
  }

  .screen-share-layout.layout-default .screen-main,
  .screen-share-layout.layout-dual .dual-main {
    flex: 1 1 auto !important;
    min-width: 0 !important;
    height: 100% !important;
  }

  .screen-share-layout.layout-default .screen-sidebar,
  .screen-share-layout.layout-dual .dual-sidebar {
    width: var(--filmstrip-width) !important;
    flex: 0 0 var(--filmstrip-width) !important;
    max-height: 100% !important;
    gap: var(--filmstrip-gap) !important;
    padding: 0 !important;
    overflow-y: auto !important;
    overflow-x: hidden !important;
  }

  .screen-share-layout.layout-default .sidebar-tile,
  .screen-share-layout.layout-dual .sidebar-tile,
  .screen-share-layout.layout-dual .sidebar-tile-sm,
  .screen-share-layout.layout-dual .screen-share-thumb {
    width: var(--filmstrip-width) !important;
    height: 126px !important;
    min-height: 126px !important;
    max-height: 126px !important;
    max-width: none !important;
    flex: 0 0 126px !important;
    border-radius: 14px !important;
    border: 1px solid rgba(255, 255, 255, .1) !important;
    background: #11151c !important;
    box-shadow: none !important;
    overflow: hidden !important;
  }

  .screen-share-layout.layout-default .sidebar-tile video,
  .screen-share-layout.layout-dual .sidebar-tile video,
  .screen-share-layout.layout-dual .sidebar-tile-sm video,
  .screen-share-layout.layout-dual .screen-share-thumb video {
    width: 100% !important;
    height: 100% !important;
    object-fit: cover !important;
  }

  .screen-share-layout.layout-default .sidebar-tile .tile-info,
  .screen-share-layout.layout-dual .sidebar-tile .tile-info,
  .screen-share-layout.layout-dual .sidebar-tile-sm .tile-info,
  .screen-share-layout.layout-dual .screen-share-thumb .tile-info {
    left: 8px !important;
    right: 8px !important;
    bottom: 8px !important;
  }

  .screen-share-layout.layout-default .sidebar-tile .tile-name,
  .screen-share-layout.layout-dual .sidebar-tile .tile-name,
  .screen-share-layout.layout-dual .sidebar-tile-sm .tile-name,
  .screen-share-layout.layout-dual .screen-share-thumb .tile-name {
    max-width: calc(100% - 34px) !important;
    min-height: 24px !important;
    padding: 0 9px !important;
    font-size: 11px !important;
  }

  .screen-share-layout.layout-dual .screen-share-thumb {
    border-color: rgba(52, 199, 89, .36) !important;
  }

  .screen-share-layout .sidebar-toggle {
    right: calc(var(--stage-pad) + var(--filmstrip-width)) !important;
    width: 32px !important;
    height: 48px !important;
    border-radius: 999px 0 0 999px !important;
    background: rgba(255, 255, 255, .9) !important;
    border: 1px solid rgba(255, 255, 255, .48) !important;
    color: #0f172a !important;
    box-shadow: 0 10px 24px rgba(0, 0, 0, .24) !important;
  }

  .screen-share-layout .sidebar-toggle.collapsed {
    right: 0 !important;
  }
}

/* ==================== Speaker View Fixed Filmstrip ==================== */
@media (min-width: 769px) {
  .video-grid.has-mobile-primary-video {
    --filmstrip-width: 228px;
    --filmstrip-gap: 12px;
    --stage-pad: 12px;
    position: relative !important;
    display: block !important;
    width: 100% !important;
    height: 100% !important;
    padding: var(--stage-pad) !important;
    border-radius: 18px !important;
    background: #05070c !important;
    overflow: hidden !important;
  }

  .video-grid.has-mobile-primary-video.secondary-collapsed {
    --filmstrip-width: 0px;
    --filmstrip-gap: 0px;
  }

  .video-grid.has-mobile-primary-video .video-tile.mobile-primary-video {
    position: absolute !important;
    z-index: 1 !important;
    top: var(--stage-pad) !important;
    right: calc(var(--stage-pad) + var(--filmstrip-width) + var(--filmstrip-gap)) !important;
    bottom: var(--stage-pad) !important;
    left: var(--stage-pad) !important;
    width: auto !important;
    height: auto !important;
    min-height: 0 !important;
    max-width: none !important;
    max-height: none !important;
    margin: 0 !important;
    border-radius: 14px !important;
    border: 1px solid rgba(255, 255, 255, .08) !important;
    background: #05070c !important;
    aspect-ratio: auto !important;
  }

  .video-grid.has-mobile-primary-video .video-tile.mobile-primary-video video {
    width: 100% !important;
    height: 100% !important;
    object-fit: contain !important;
    background: #05070c !important;
  }

  .video-grid.has-mobile-primary-video .video-tile:not(.mobile-primary-video) {
    position: absolute !important;
    z-index: 4 !important;
    right: var(--stage-pad) !important;
    left: auto !important;
    width: var(--filmstrip-width) !important;
    height: 126px !important;
    min-height: 126px !important;
    max-height: 126px !important;
    max-width: none !important;
    border-radius: 14px !important;
    border: 1px solid rgba(255, 255, 255, .1) !important;
    background: #11151c !important;
    box-shadow: none !important;
    transform: none !important;
    overflow: hidden !important;
  }

  .video-grid.has-mobile-primary-video .video-tile.mobile-secondary-1 {
    top: var(--stage-pad) !important;
    display: flex !important;
  }

  .video-grid.has-mobile-primary-video .video-tile.mobile-secondary-2 {
    top: calc(var(--stage-pad) + 138px) !important;
    display: flex !important;
  }

  .video-grid.has-mobile-primary-video .video-tile.mobile-secondary-3 {
    top: calc(var(--stage-pad) + 276px) !important;
    display: flex !important;
  }

  .video-grid.has-mobile-primary-video .video-tile.mobile-secondary-4 {
    top: calc(var(--stage-pad) + 414px) !important;
    display: flex !important;
  }

  .video-grid.has-mobile-primary-video .video-tile.mobile-secondary-5 {
    top: calc(var(--stage-pad) + 552px) !important;
    display: flex !important;
  }

  .video-grid.has-mobile-primary-video.secondary-collapsed .video-tile:not(.mobile-primary-video),
  .video-grid.has-mobile-primary-video .video-tile.mobile-secondary-6,
  .video-grid.has-mobile-primary-video .video-tile.mobile-secondary-7,
  .video-grid.has-mobile-primary-video .video-tile.mobile-secondary-8 {
    display: none !important;
  }

  .video-grid.has-mobile-primary-video .video-tile:not(.mobile-primary-video) video {
    object-fit: cover !important;
  }

  .video-grid.has-mobile-primary-video .video-tile:not(.mobile-primary-video) .voice-avatar {
    width: 100% !important;
    height: 100% !important;
  }

  .video-grid.has-mobile-primary-video .video-tile:not(.mobile-primary-video) .avatar-block,
  .video-grid.has-mobile-primary-video .video-tile:not(.mobile-primary-video) .voice-avatar :deep(.avatar-orb),
  .video-grid.has-mobile-primary-video .video-tile:not(.mobile-primary-video) .voice-avatar :deep(.avatar-core) {
    width: 54px !important;
    height: 54px !important;
  }

  .video-grid.has-mobile-primary-video .video-tile:not(.mobile-primary-video) .avatar-text,
  .video-grid.has-mobile-primary-video .video-tile:not(.mobile-primary-video) .voice-avatar :deep(.avatar-initials) {
    font-size: 18px !important;
  }

  .video-grid.has-mobile-primary-video .video-tile:not(.mobile-primary-video) .tile-info {
    left: 8px !important;
    right: 8px !important;
    bottom: 8px !important;
  }

  .video-grid.has-mobile-primary-video .video-tile:not(.mobile-primary-video) .tile-name {
    max-width: calc(100% - 34px) !important;
    min-height: 24px !important;
    padding: 0 9px !important;
    font-size: 11px !important;
  }

  .video-grid.has-mobile-primary-video .video-tile:not(.mobile-primary-video) .icon-muted {
    position: absolute !important;
    right: 8px !important;
    bottom: 8px !important;
    z-index: 8 !important;
    width: 24px !important;
    height: 24px !important;
    border-radius: 7px !important;
  }

  .video-grid.has-mobile-primary-video .secondary-toggle {
    position: absolute !important;
    top: 50% !important;
    right: calc(var(--stage-pad) + var(--filmstrip-width) - 14px) !important;
    bottom: auto !important;
    z-index: 12 !important;
    width: 30px !important;
    height: 46px !important;
    border-radius: 999px !important;
    transform: translateY(-50%) !important;
    background: rgba(255, 255, 255, .92) !important;
    border: 1px solid rgba(255, 255, 255, .5) !important;
    color: #0f172a !important;
    box-shadow: 0 10px 24px rgba(0, 0, 0, .24) !important;
  }

  .video-grid.has-mobile-primary-video.secondary-collapsed .secondary-toggle {
    right: var(--stage-pad) !important;
  }
}

/* ==================== Name Integrated Mic Status ==================== */
.tile-name {
  display: inline-flex !important;
  align-items: center !important;
  gap: 7px !important;
}

.tile-name::before {
  content: "";
  width: 7px;
  height: 7px;
  flex: 0 0 7px;
  border-radius: 50%;
  background: #30d158;
  box-shadow: 0 0 0 3px rgba(48, 209, 88, .14);
}

.video-tile.is-muted .tile-name::before,
.dual-tile.is-muted .tile-name::before,
.sidebar-tile.is-muted .tile-name::before,
.sidebar-tile-sm.is-muted .tile-name::before,
.multi-tile-small.is-muted .tile-name::before {
  background: #ff453a;
  box-shadow: 0 0 0 3px rgba(255, 69, 58, .16);
}

.icon-muted {
  display: none !important;
}

.video-tile:not(.is-muted) .tile-info::after,
.dual-tile:not(.is-muted) .tile-info::after,
.video-tile.is-speaking .tile-info::after,
.dual-tile.is-speaking .tile-info::after {
  display: none !important;
}

.video-tile.is-speaking:not(.is-muted) .tile-name,
.dual-tile.is-speaking:not(.is-muted) .tile-name,
.sidebar-tile.is-speaking:not(.is-muted) .tile-name,
.sidebar-tile-sm.is-speaking:not(.is-muted) .tile-name,
.multi-tile-small.is-speaking:not(.is-muted) .tile-name {
  border-color: rgba(48, 209, 88, .38) !important;
  color: #f4fff8 !important;
  animation: name-speaking-breathe 1.35s ease-in-out infinite;
}

.video-tile.is-speaking:not(.is-muted) .tile-name::before,
.dual-tile.is-speaking:not(.is-muted) .tile-name::before,
.sidebar-tile.is-speaking:not(.is-muted) .tile-name::before,
.sidebar-tile-sm.is-speaking:not(.is-muted) .tile-name::before,
.multi-tile-small.is-speaking:not(.is-muted) .tile-name::before {
  animation: mic-dot-speaking-breathe 1.35s ease-in-out infinite;
}

@keyframes name-speaking-breathe {
  0%, 100% {
    background: rgba(15, 23, 42, .74);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, .08),
      0 0 0 0 rgba(48, 209, 88, 0);
  }
  50% {
    background: rgba(20, 70, 46, .82);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, .12),
      0 0 0 4px rgba(48, 209, 88, .12),
      0 0 18px rgba(48, 209, 88, .22);
  }
}

@keyframes mic-dot-speaking-breathe {
  0%, 100% {
    transform: scale(1);
    box-shadow: 0 0 0 3px rgba(48, 209, 88, .14);
  }
  50% {
    transform: scale(1.18);
    box-shadow: 0 0 0 6px rgba(48, 209, 88, .2), 0 0 14px rgba(48, 209, 88, .42);
  }
}

@media (prefers-reduced-motion: reduce) {
  .is-speaking:not(.is-muted) .tile-name,
  .is-speaking:not(.is-muted) .tile-name::before {
    animation: none !important;
  }
}

/* ==================== Meeting Chat Redesign ==================== */
.chat-panel {
  width: 430px !important;
  overflow: hidden !important;
  border-radius: 26px !important;
  background: rgba(249, 250, 252, .98) !important;
  border: 1px solid rgba(214, 221, 233, .96) !important;
  box-shadow: 0 24px 70px rgba(26, 32, 44, .16) !important;
}

.chat-panel .panel-head {
  min-height: 76px !important;
  padding: 0 24px !important;
  background: #fff !important;
  border-bottom: 1px solid rgba(222, 228, 238, .9) !important;
  font-size: 18px !important;
  font-weight: 850 !important;
}

.chat-panel .close-icon {
  width: 34px !important;
  height: 34px !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  border-radius: 999px !important;
  color: #98a2b3 !important;
}

.chat-panel .close-icon:hover {
  background: #f2f4f7 !important;
  color: #1d2939 !important;
}

.chat-messages {
  padding: 20px !important;
  background: linear-gradient(180deg, #f8fafc 0%, #f3f6fa 100%) !important;
  scrollbar-width: thin;
  scrollbar-color: rgba(148, 163, 184, .55) transparent;
}

.chat-messages::-webkit-scrollbar { width: 6px; }
.chat-messages::-webkit-scrollbar-thumb { background: rgba(148, 163, 184, .45); border-radius: 999px; }

.chat-msg {
  display: flex !important;
  flex-direction: column !important;
  align-items: flex-start !important;
  gap: 6px !important;
  margin: 0 0 16px !important;
}

.chat-msg.own {
  align-items: flex-end !important;
  text-align: left !important;
}

.msg-head {
  display: flex !important;
  align-items: center !important;
  gap: 8px !important;
  margin: 0 !important;
  padding: 0 4px !important;
}

.chat-msg.own .msg-head { flex-direction: row !important; }

.msg-sender {
  color: #475467 !important;
  font-size: 12px !important;
  font-weight: 750 !important;
}

.msg-time {
  color: #98a2b3 !important;
  font-size: 11px !important;
  font-variant-numeric: tabular-nums !important;
}

.msg-body {
  max-width: min(82%, 320px) !important;
  padding: 10px 13px !important;
  border-radius: 18px 18px 18px 6px !important;
  background: #fff !important;
  border: 1px solid rgba(222, 228, 238, .94) !important;
  box-shadow: 0 8px 18px rgba(16, 24, 40, .05) !important;
  color: #182230 !important;
  font-size: 14px !important;
  line-height: 1.55 !important;
  word-break: break-word !important;
}

.chat-msg.own .msg-body {
  border-radius: 18px 18px 6px 18px !important;
  background: #0f172a !important;
  border-color: #0f172a !important;
  color: #fff !important;
  box-shadow: 0 10px 22px rgba(15, 23, 42, .18) !important;
}

.msg-body.msg-type-image {
  padding: 6px !important;
  background: #fff !important;
}

.msg-image {
  width: min(260px, 100%) !important;
  max-height: 220px !important;
  display: block !important;
  border-radius: 14px !important;
  overflow: hidden !important;
}

.file-link {
  display: grid !important;
  grid-template-columns: 38px minmax(0, 1fr) !important;
  align-items: center !important;
  gap: 10px !important;
  min-width: 230px !important;
  color: inherit !important;
  text-decoration: none !important;
}

.file-icon {
  width: 38px !important;
  height: 38px !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  border-radius: 12px !important;
  background: #eef4ff !important;
  color: #175cd3 !important;
}

.chat-msg.own .file-icon {
  background: rgba(255, 255, 255, .16) !important;
  color: #fff !important;
}

.file-meta {
  display: flex !important;
  min-width: 0 !important;
  flex-direction: column !important;
  gap: 2px !important;
}

.file-meta strong {
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  white-space: nowrap !important;
  font-size: 13px !important;
}

.file-meta small { color: #667085 !important; font-size: 11px !important; }
.chat-msg.own .file-meta small { color: rgba(255, 255, 255, .68) !important; }

.chat-empty {
  height: 100% !important;
  min-height: 360px !important;
  display: flex !important;
  flex-direction: column !important;
  align-items: center !important;
  justify-content: center !important;
  gap: 8px !important;
  color: #98a2b3 !important;
  text-align: center !important;
}

.chat-empty .lk-icon { width: 34px !important; height: 34px !important; color: #667085 !important; }
.chat-empty strong { color: #344054 !important; font-size: 15px !important; }
.chat-empty span { max-width: 220px !important; font-size: 12px !important; line-height: 1.5 !important; }

.chat-input {
  padding: 14px 16px 16px !important;
  background: #fff !important;
  border-top: 1px solid rgba(222, 228, 238, .9) !important;
}

.chat-bar {
  min-height: 50px !important;
  gap: 8px !important;
  padding: 6px !important;
  border-radius: 18px !important;
  background: #f8fafc !important;
  border: 1px solid rgba(214, 221, 233, .96) !important;
}

.chat-upload-btn {
  width: 36px !important;
  height: 36px !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  border-radius: 12px !important;
  color: #667085 !important;
}

.chat-upload-btn:hover {
  background: #eef4ff !important;
  color: #175cd3 !important;
}

.chat-bar :deep(.el-input__wrapper) {
  min-height: 36px !important;
  background: transparent !important;
  box-shadow: none !important;
  border-radius: 12px !important;
}

.chat-bar :deep(.el-input__inner) {
  color: #182230 !important;
  font-size: 14px !important;
}

.send-btn,
.chat-bar :deep(.send-btn.el-button) {
  width: 38px !important;
  height: 38px !important;
  border-radius: 14px !important;
  background: #0f172a !important;
  border-color: #0f172a !important;
  color: #fff !important;
}

.send-btn.is-disabled,
.chat-bar :deep(.send-btn.el-button.is-disabled) {
  background: #e4e7ec !important;
  border-color: #e4e7ec !important;
  color: #98a2b3 !important;
}

/* ==================== Manual Score Redesign ==================== */
.score-panel {
  width: 450px !important;
  overflow: hidden !important;
  border-radius: 26px !important;
  background: rgba(249, 250, 252, .98) !important;
  border: 1px solid rgba(214, 221, 233, .96) !important;
  box-shadow: 0 24px 70px rgba(26, 32, 44, .16) !important;
}

.score-panel .panel-head {
  min-height: 76px !important;
  padding: 0 24px !important;
  background: #fff !important;
  border-bottom: 1px solid rgba(222, 228, 238, .9) !important;
}

.score-panel .panel-title-wrap {
  display: flex !important;
  flex-direction: column !important;
  gap: 5px !important;
}

.score-panel .panel-kicker {
  color: #98a2b3 !important;
  font-size: 10px !important;
  font-weight: 850 !important;
  letter-spacing: .24em !important;
}

.score-panel .panel-title-wrap span:last-child {
  color: #101828 !important;
  font-size: 18px !important;
  font-weight: 880 !important;
}

.score-body {
  padding: 18px 18px 104px !important;
  background: linear-gradient(180deg, #f8fafc 0%, #f3f6fa 100%) !important;
  scrollbar-width: thin;
  scrollbar-color: rgba(148, 163, 184, .55) transparent;
}

.score-total-bar {
  position: sticky !important;
  top: 0 !important;
  z-index: 3 !important;
  display: flex !important;
  flex-direction: column !important;
  gap: 12px !important;
  padding: 18px !important;
  margin: 0 0 18px !important;
  border-radius: 20px !important;
  background: #fff !important;
  border: 1px solid rgba(222, 228, 238, .96) !important;
  box-shadow: 0 14px 30px rgba(16, 24, 40, .07) !important;
}

.score-total-copy {
  display: flex !important;
  align-items: baseline !important;
  justify-content: center !important;
  gap: 8px !important;
}

.score-total-label {
  color: #667085 !important;
  font-size: 13px !important;
  font-weight: 750 !important;
}

.total-val {
  color: #0f172a !important;
  font-size: 34px !important;
  font-weight: 900 !important;
  line-height: 1 !important;
}

.score-total-max {
  color: #98a2b3 !important;
  font-size: 14px !important;
  font-weight: 750 !important;
}

.score-total-progress {
  height: 8px !important;
  overflow: hidden !important;
  border-radius: 999px !important;
  background: #eef2f7 !important;
}

.score-total-progress span {
  display: block !important;
  height: 100% !important;
  border-radius: inherit !important;
  background: linear-gradient(90deg, #1677ff, #30d158) !important;
  transition: width .18s ease !important;
}

.score-group {
  margin: 0 0 18px !important;
}

.group-title {
  position: sticky !important;
  top: 96px !important;
  z-index: 2 !important;
  display: flex !important;
  align-items: center !important;
  justify-content: space-between !important;
  min-height: 42px !important;
  padding: 0 4px !important;
  margin: 0 0 10px !important;
  border: 0 !important;
  background: transparent !important;
  color: #175cd3 !important;
  font-size: 14px !important;
  font-weight: 880 !important;
}

.group-title small {
  padding: 3px 8px !important;
  border-radius: 999px !important;
  background: #eef4ff !important;
  color: #175cd3 !important;
  font-size: 11px !important;
  font-weight: 800 !important;
}

.score-item {
  padding: 16px !important;
  margin: 0 0 12px !important;
  border-radius: 20px !important;
  background: #fff !important;
  border: 1px solid rgba(222, 228, 238, .96) !important;
  box-shadow: 0 10px 24px rgba(16, 24, 40, .05) !important;
}

.score-item-head {
  display: grid !important;
  grid-template-columns: minmax(0, 1fr) auto !important;
  gap: 12px !important;
  align-items: center !important;
  margin: 0 0 8px !important;
}

.score-name {
  color: #101828 !important;
  font-size: 15px !important;
  font-weight: 850 !important;
  white-space: normal !important;
}

.score-desc {
  margin: 0 0 10px !important;
  color: #667085 !important;
  font-size: 12px !important;
  line-height: 1.5 !important;
}

.score-value-pill {
  min-width: 110px !important;
  height: 40px !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  gap: 4px !important;
  padding: 0 12px !important;
  border-radius: 999px !important;
  background: #f8fafc !important;
  border: 1px solid rgba(214, 221, 233, .96) !important;
  color: #101828 !important;
}

.score-value-pill small {
  color: #98a2b3 !important;
  font-size: 12px !important;
  font-weight: 750 !important;
}

.score-number-input {
  width: 54px !important;
}

.score-number-input :deep(.el-input__wrapper) {
  padding: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
}

.score-number-input :deep(.el-input__inner) {
  color: #101828 !important;
  font-size: 18px !important;
  font-weight: 900 !important;
  text-align: center !important;
}

.score-slider {
  margin: 2px 0 10px !important;
}

.score-slider :deep(.el-slider__runway) {
  height: 8px !important;
  border-radius: 999px !important;
  background: #eef2f7 !important;
}

.score-slider :deep(.el-slider__bar) {
  height: 8px !important;
  border-radius: 999px !important;
  background: linear-gradient(90deg, #1677ff, #30d158) !important;
}

.score-slider :deep(.el-slider__button) {
  width: 18px !important;
  height: 18px !important;
  border: 3px solid #fff !important;
  background: #1677ff !important;
  box-shadow: 0 4px 12px rgba(22, 119, 255, .34) !important;
}

.score-comment :deep(.el-textarea__inner) {
  min-height: 52px !important;
  padding: 11px 12px !important;
  border-radius: 14px !important;
  background: #f8fafc !important;
  border: 1px solid rgba(214, 221, 233, .96) !important;
  box-shadow: none !important;
  color: #101828 !important;
  font-size: 13px !important;
}

.score-comment :deep(.el-textarea__inner:focus) {
  border-color: rgba(22, 119, 255, .45) !important;
  background: #fff !important;
}

.score-footer {
  min-height: 84px !important;
  padding: 14px 18px !important;
  display: grid !important;
  grid-template-columns: 96px minmax(0, 1fr) !important;
  gap: 12px !important;
  align-items: center !important;
  background: rgba(255, 255, 255, .96) !important;
  border-top: 1px solid rgba(222, 228, 238, .9) !important;
  backdrop-filter: blur(16px) !important;
}

.score-submit-meta {
  display: flex !important;
  flex-direction: column !important;
  align-items: flex-start !important;
  gap: 2px !important;
}

.score-submit-meta span {
  color: #667085 !important;
  font-size: 11px !important;
  font-weight: 750 !important;
}

.score-submit-meta strong {
  color: #1677ff !important;
  font-size: 28px !important;
  line-height: 1 !important;
  font-weight: 900 !important;
}

.score-footer :deep(.el-button) {
  width: 100% !important;
  height: 52px !important;
  border-radius: 18px !important;
  background: #1677ff !important;
  border-color: #1677ff !important;
  color: #fff !important;
  font-size: 15px !important;
  font-weight: 850 !important;
  box-shadow: 0 12px 28px rgba(22, 119, 255, .24) !important;
}

.score-empty {
  min-height: 360px !important;
  display: flex !important;
  flex-direction: column !important;
  align-items: center !important;
  justify-content: center !important;
  gap: 10px !important;
  color: #667085 !important;
}

/* ==================== Issue Panel Redesign ==================== */
:global(.issues-drawer) {
  background: transparent !important;
}

:global(.issues-drawer .el-drawer__body) {
  padding: 0 !important;
  overflow: hidden !important;
  background: transparent !important;
}

.issues-panel {
  height: 100% !important;
  display: grid !important;
  grid-template-rows: auto minmax(0, 1fr) !important;
  background: #f8fafc !important;
  border-top: 1px solid rgba(214, 221, 233, .96) !important;
  box-shadow: 0 -24px 70px rgba(26, 32, 44, .16) !important;
  color: #101828 !important;
}

:global(.issues-drawer.el-drawer.rtl) {
  width: min(460px, 94vw) !important;
  border-radius: 26px 0 0 26px !important;
  overflow: hidden !important;
}

:global(.issues-drawer.el-drawer.rtl .el-drawer__body) {
  height: 100% !important;
}

.issues-head {
  min-height: 138px !important;
  display: grid !important;
  grid-template-columns: minmax(0, 1fr) auto !important;
  grid-template-rows: auto auto !important;
  gap: 16px !important;
  align-items: center !important;
  padding: 26px 24px 18px !important;
  border-bottom: 1px solid rgba(222, 228, 238, .9) !important;
  background: #fff !important;
}

.issues-head strong {
  display: block !important;
  margin-top: 0 !important;
  color: #101828 !important;
  font-size: 24px !important;
  line-height: 1 !important;
  font-weight: 900 !important;
}

.issues-head p {
  margin: 8px 0 0 !important;
  color: #667085 !important;
  font-size: 13px !important;
}

.issues-metrics {
  grid-column: 1 / -1 !important;
  display: flex !important;
  align-items: center !important;
  gap: 8px !important;
  flex-wrap: nowrap !important;
  justify-content: flex-start !important;
  min-width: 0 !important;
}

.issues-metrics button {
  min-height: 34px !important;
  padding: 0 12px !important;
  border: 1px solid rgba(214, 221, 233, .96) !important;
  border-radius: 999px !important;
  background: #fff !important;
  color: #475467 !important;
  font-size: 12px !important;
  font-weight: 800 !important;
  cursor: pointer !important;
  white-space: nowrap !important;
}

.issues-metrics button.active {
  background: #0f172a !important;
  border-color: #0f172a !important;
  color: #fff !important;
}

.issues-metrics button.refresh {
  background: #eef4ff !important;
  border-color: rgba(23, 92, 211, .16) !important;
  color: #175cd3 !important;
}

.issues-close {
  width: 38px !important;
  height: 38px !important;
  display: grid !important;
  place-items: center !important;
  border: 1px solid rgba(214, 221, 233, .96) !important;
  border-radius: 50% !important;
  background: #fff !important;
  color: #667085 !important;
  cursor: pointer !important;
  align-self: start !important;
}

.issues-close:hover {
  background: #f2f4f7 !important;
  color: #101828 !important;
}

.issues-list {
  min-height: 0 !important;
  padding: 18px 18px 24px !important;
  overflow-y: auto !important;
  display: grid !important;
  align-content: start !important;
  gap: 12px !important;
  background: linear-gradient(180deg, #f8fafc 0%, #f3f6fa 100%) !important;
}

.issue-row-card {
  display: grid !important;
  grid-template-columns: 56px minmax(0, 1fr) !important;
  gap: 12px !important;
  align-items: start !important;
  min-height: 94px !important;
  padding: 14px !important;
  border-radius: 20px !important;
  border: 1px solid rgba(252, 176, 50, .28) !important;
  background: #fff !important;
  box-shadow: 0 10px 24px rgba(16, 24, 40, .05) !important;
}

.issue-row-card.resolved {
  border-color: rgba(52, 199, 89, .22) !important;
  background: linear-gradient(180deg, #fff, #f7fff9) !important;
}

.issue-index {
  width: 48px !important;
  height: 48px !important;
  display: grid !important;
  place-items: center !important;
  border-radius: 18px !important;
  border: 1px solid rgba(252, 176, 50, .22) !important;
  background: #fff7e8 !important;
  color: #b54708 !important;
  font-size: 13px !important;
  font-weight: 900 !important;
  font-variant-numeric: tabular-nums !important;
}

.issue-row-card.resolved .issue-index {
  border-color: rgba(52, 199, 89, .22) !important;
  background: #ecfdf3 !important;
  color: #067647 !important;
}

.issue-copy {
  min-width: 0 !important;
}

.issue-row-top {
  display: flex !important;
  align-items: center !important;
  gap: 8px !important;
  min-width: 0 !important;
  flex-wrap: wrap !important;
}

.issue-title {
  flex: 1 1 260px !important;
  min-width: 0 !important;
  color: #101828 !important;
  font-size: 15px !important;
  line-height: 1.4 !important;
  font-weight: 850 !important;
  white-space: normal !important;
}

.issue-desc {
  margin-top: 8px !important;
  color: #475467 !important;
  font-size: 13px !important;
  line-height: 1.55 !important;
}

.issue-category-pill,
.issue-state {
  min-height: 26px !important;
  display: inline-flex !important;
  align-items: center !important;
  padding: 0 10px !important;
  border-radius: 999px !important;
  font-size: 12px !important;
  font-weight: 850 !important;
}

.issue-category-pill {
  background: #eef4ff !important;
  border: 1px solid rgba(23, 92, 211, .14) !important;
  color: #175cd3 !important;
}

.issue-state {
  background: #fff7e8 !important;
  border: 1px solid rgba(252, 176, 50, .22) !important;
  color: #b54708 !important;
}

.issue-row-card.resolved .issue-state {
  background: #ecfdf3 !important;
  border-color: rgba(52, 199, 89, .22) !important;
  color: #067647 !important;
}

.issue-meta {
  display: flex !important;
  gap: 10px !important;
  flex-wrap: wrap !important;
  margin-top: 8px !important;
  color: #98a2b3 !important;
  font-size: 12px !important;
  font-variant-numeric: tabular-nums !important;
}

.issue-actions {
  grid-column: 2 !important;
  display: flex !important;
  align-items: center !important;
  justify-content: flex-start !important;
  margin-top: 10px !important;
}

.issue-actions button {
  height: 38px !important;
  padding: 0 14px !important;
  border: 0 !important;
  border-radius: 14px !important;
  background: #1677ff !important;
  color: #fff !important;
  font-size: 13px !important;
  font-weight: 850 !important;
  cursor: pointer !important;
  box-shadow: 0 10px 22px rgba(22, 119, 255, .22) !important;
}

.issue-actions span {
  min-height: 32px !important;
  display: inline-flex !important;
  align-items: center !important;
  padding: 0 12px !important;
  border-radius: 999px !important;
  background: #ecfdf3 !important;
  color: #067647 !important;
  font-size: 12px !important;
  font-weight: 850 !important;
}

.issues-empty {
  min-height: 320px !important;
  margin: 18px !important;
  display: grid !important;
  place-items: center !important;
  align-content: center !important;
  gap: 10px !important;
  text-align: center !important;
  border: 1px dashed rgba(214, 221, 233, .96) !important;
  border-radius: 24px !important;
  background: #fff !important;
}

.issues-empty span {
  width: 76px !important;
  height: 76px !important;
  display: grid !important;
  place-items: center !important;
  border: 1px solid rgba(52, 199, 89, .18) !important;
  border-radius: 50% !important;
  color: #067647 !important;
  background: #ecfdf3 !important;
  font-size: 11px !important;
  font-weight: 880 !important;
}

.issues-empty strong {
  color: #101828 !important;
  font-size: 18px !important;
}

.issues-empty p {
  margin: 0 !important;
  color: #667085 !important;
  font-size: 13px !important;
}

/* Final roadshow visual layer. This intentionally changes presentation only:
   the LiveKit layout modes, media controls, scoring, chat and issue behavior
   continue to use the existing template and state. */
.meeting-room,
.meeting-room:fullscreen {
  color: #f4f1ee !important;
  background: #0f1115 !important;
}

.room-grid-bg,
.room-orbit,
.meeting-room::before {
  display: none !important;
}

.room-header {
  min-height: 64px !important;
  padding: 0 20px !important;
  border-bottom: 1px solid rgba(255, 255, 255, .1) !important;
  background: rgba(15, 17, 21, .96) !important;
  box-shadow: none !important;
  backdrop-filter: blur(14px) !important;
}

.meeting-title,
.participant-num,
.countdown-time {
  color: #f4f1ee !important;
}

.participant-num,
.countdown-pill,
.livekit-agent-chip,
.net-status {
  border: 1px solid rgba(255, 255, 255, .1) !important;
  background: rgba(255, 255, 255, .055) !important;
  box-shadow: none !important;
}

.livekit-agent-chip.connected {
  color: #72d7b2 !important;
  border-color: rgba(15, 159, 110, .3) !important;
  background: rgba(15, 159, 110, .1) !important;
}

.room-body,
.video-area,
.video-grid,
.screen-share-layout,
.screen-main,
.dual-main,
.multi-main {
  background: #0f1115 !important;
}

.video-tile,
.sidebar-tile,
.screen-tile,
.dual-tile,
.multi-tile,
.multi-tile-small {
  border: 1px solid rgba(255, 255, 255, .11) !important;
  border-radius: 14px !important;
  background: #181b20 !important;
  box-shadow: none !important;
  transform: none !important;
}

.video-tile.is-speaking,
.sidebar-tile.is-speaking,
.dual-tile.is-speaking,
.multi-tile-small.is-speaking {
  border-color: rgba(15, 159, 110, .78) !important;
  box-shadow: 0 0 0 2px rgba(15, 159, 110, .16) !important;
}

.tile-info {
  color: #f4f1ee !important;
  background: linear-gradient(180deg, transparent, rgba(7, 8, 10, .76)) !important;
}

.control-bar {
  border-top: 1px solid rgba(255, 255, 255, .1) !important;
  background: rgba(15, 17, 21, .97) !important;
  box-shadow: none !important;
  backdrop-filter: blur(14px) !important;
}

.control-bar :deep(.el-button) {
  border-color: rgba(255, 255, 255, .12) !important;
  color: #f4f1ee !important;
  background: rgba(255, 255, 255, .07) !important;
  box-shadow: none !important;
  transform: none !important;
  transition: color 150ms ease-in-out, background-color 150ms ease-in-out, border-color 150ms ease-in-out !important;
}

.control-bar :deep(.el-button:hover) {
  border-color: rgba(255, 255, 255, .22) !important;
  color: #fffaf7 !important;
  background: rgba(255, 255, 255, .12) !important;
  box-shadow: none !important;
  transform: none !important;
}

.control-bar :deep(.el-button.btn-active),
.control-bar :deep(.el-button.btn-live),
.control-bar :deep(.el-button.btn-recording) {
  border-color: rgba(207, 61, 18, .72) !important;
  color: #fffaf7 !important;
  background: rgba(207, 61, 18, .22) !important;
  box-shadow: none !important;
}

.control-bar :deep(.el-button.btn-off) {
  border-color: rgba(216, 58, 69, .42) !important;
  color: #ffb5bc !important;
  background: rgba(216, 58, 69, .14) !important;
}

.control-bar :deep(.el-button--danger) {
  border-color: #d83a45 !important;
  color: #fffaf7 !important;
  background: #d83a45 !important;
}

.control-bar :deep(.el-button--danger:hover) {
  border-color: #c92e3a !important;
  background: #c92e3a !important;
}

.control-bar :deep(.el-button:focus-visible),
.secondary-toggle:focus-visible,
.sidebar-toggle:focus-visible,
.issues-close:focus-visible,
.issues-metrics button:focus-visible,
.issue-actions button:focus-visible {
  outline: 2px solid #cf3d12 !important;
  outline-offset: 2px !important;
}

.side-panel,
.chat-panel,
.score-panel {
  color: var(--ds-ink, #12141a) !important;
  border-left: 1px solid var(--ds-line, rgba(28, 26, 22, .09)) !important;
  background: var(--ds-surface-solid, #fff) !important;
  box-shadow: -12px 0 32px rgba(8, 10, 14, .22) !important;
}

.panel-head,
.chat-input,
.panel-footer,
.score-footer {
  color: var(--ds-ink, #12141a) !important;
  border-color: var(--ds-line, rgba(28, 26, 22, .09)) !important;
  background: var(--ds-surface-solid, #fff) !important;
  box-shadow: none !important;
  backdrop-filter: none !important;
}

.panel-head,
.panel-title-wrap,
.panel-title-wrap > span:last-child,
.score-name,
.score-total-copy,
.score-total-label,
.score-submit-meta strong {
  color: var(--ds-ink, #12141a) !important;
}

.panel-kicker,
.score-desc,
.group-title,
.score-submit-meta span {
  color: var(--ds-muted, #6b7280) !important;
}

.chat-messages,
.score-body {
  background: var(--ds-canvas, #f3f4f6) !important;
}

.chat-msg .msg-body,
.score-item,
.score-total-bar {
  border-color: var(--ds-line, rgba(28, 26, 22, .09)) !important;
  color: var(--ds-ink-2, #2c3038) !important;
  background: var(--ds-surface-solid, #fff) !important;
  box-shadow: none !important;
}

.chat-msg.own .msg-body {
  border-color: var(--ds-orange-100, #fee9df) !important;
  color: var(--ds-ink, #12141a) !important;
  background: var(--ds-orange-50, #fff7f2) !important;
}

.chat-input :deep(.el-input__wrapper),
.score-panel :deep(.el-input__wrapper),
.score-panel :deep(.el-textarea__inner) {
  border: 1px solid var(--ds-input-border, rgba(28, 26, 22, .13)) !important;
  border-radius: var(--ds-input-radius, 12px) !important;
  color: var(--ds-ink, #12141a) !important;
  background: var(--ds-input-bg, #fff) !important;
  box-shadow: none !important;
}

.chat-input :deep(.el-input__wrapper.is-focus),
.score-panel :deep(.el-input__wrapper.is-focus),
.score-panel :deep(.el-textarea__inner:focus) {
  border-color: var(--ds-orange-action, #cf3d12) !important;
  box-shadow: 0 0 0 3px rgba(207, 61, 18, .12) !important;
}

.send-btn,
.score-footer :deep(.el-button) {
  border-color: var(--ds-orange-action, #cf3d12) !important;
  color: #fffaf7 !important;
  background: var(--ds-orange-action, #cf3d12) !important;
  box-shadow: none !important;
  transform: none !important;
}

.send-btn:hover,
.score-footer :deep(.el-button:hover) {
  border-color: var(--ds-orange-700, #c2370e) !important;
  background: var(--ds-orange-700, #c2370e) !important;
}

.score-total-progress,
.score-slider :deep(.el-slider__runway) {
  background: var(--ds-line-strong, rgba(28, 26, 22, .13)) !important;
}

.score-total-progress span,
.score-slider :deep(.el-slider__bar) {
  background: var(--ds-orange-action, #cf3d12) !important;
}

.score-slider :deep(.el-slider__button) {
  border-color: var(--ds-orange-action, #cf3d12) !important;
  background: #fff !important;
  box-shadow: 0 0 0 3px rgba(207, 61, 18, .12) !important;
}

:global(.issues-drawer.el-drawer.rtl) {
  border-radius: var(--ds-radius-lg, 16px) 0 0 var(--ds-radius-lg, 16px) !important;
}

.issues-panel,
.issues-head,
.issues-list,
.issues-empty {
  color: var(--ds-ink, #12141a) !important;
  background: var(--ds-surface-solid, #fff) !important;
  box-shadow: none !important;
}

.issues-head {
  border-bottom-color: var(--ds-line, rgba(28, 26, 22, .09)) !important;
}

.issues-metrics button,
.issues-close {
  border-color: var(--ds-line-strong, rgba(28, 26, 22, .13)) !important;
  color: var(--ds-ink-2, #2c3038) !important;
  background: var(--ds-surface-solid, #fff) !important;
  box-shadow: none !important;
}

.issues-metrics button:hover,
.issues-close:hover {
  color: var(--ds-orange-800, #b12f0a) !important;
  border-color: var(--ds-orange-action, #cf3d12) !important;
  background: var(--ds-orange-50, #fff7f2) !important;
}

.issues-metrics button.active,
.issues-metrics button.refresh,
.issue-actions button {
  border-color: var(--ds-orange-action, #cf3d12) !important;
  color: #fffaf7 !important;
  background: var(--ds-orange-action, #cf3d12) !important;
  box-shadow: none !important;
}

.issue-row-card,
.issue-row-card.resolved {
  border-color: var(--ds-line, rgba(28, 26, 22, .09)) !important;
  border-radius: var(--ds-radius-md, 12px) !important;
  background: var(--ds-surface-solid, #fff) !important;
  box-shadow: none !important;
}

.issue-index,
.issue-category-pill,
.issue-state {
  color: var(--ds-orange-800, #b12f0a) !important;
  border-color: var(--ds-orange-100, #fee9df) !important;
  background: var(--ds-orange-50, #fff7f2) !important;
}

.issue-row-card.resolved .issue-index,
.issue-row-card.resolved .issue-state,
.issue-actions span {
  color: var(--ds-green, #0f9f6e) !important;
  border-color: rgba(15, 159, 110, .22) !important;
  background: rgba(15, 159, 110, .08) !important;
}

:global(.meeting-quality-popper),
:global(.meeting-mobile-more-popper) {
  border: 1px solid rgba(255, 255, 255, .12) !important;
  background: #181b20 !important;
  box-shadow: 0 16px 38px rgba(0, 0, 0, .34) !important;
}

:global(.meeting-quality-popper .el-dropdown-menu),
:global(.meeting-mobile-more-popper .el-dropdown-menu) {
  background: #181b20 !important;
}

:global(.meeting-quality-popper .el-dropdown-menu__item),
:global(.meeting-mobile-more-popper .el-dropdown-menu__item) {
  color: #e9e5e1 !important;
}

:global(.meeting-quality-popper .el-dropdown-menu__item:hover),
:global(.meeting-mobile-more-popper .el-dropdown-menu__item:hover),
:global(.meeting-quality-popper .is-active-quality),
:global(.meeting-mobile-more-popper .is-active-quality) {
  color: #fffaf7 !important;
  background: rgba(207, 61, 18, .22) !important;
}
</style>

<style scoped>
/* Meeting composition v2: a flat meeting bar, quiet stage and unified controls. */
.room-header {
  top: 0 !important;
  right: 0 !important;
  left: 0 !important;
  width: 100% !important;
  height: 72px !important;
  min-height: 72px !important;
  padding: 0 24px !important;
  border: 0 !important;
  border-bottom: 1px solid var(--ds-line, rgba(28, 26, 22, .09)) !important;
  border-radius: 0 !important;
  background: var(--ds-surface-solid, #fffaf7) !important;
  box-shadow: none !important;
}

.room-header .header-left,
.room-header .header-right {
  min-height: 0 !important;
  padding: 0 !important;
  border: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
}

.room-header .header-left {
  gap: 12px !important;
}

.meeting-title-wrap {
  min-width: 0 !important;
  display: flex !important;
  align-items: center !important;
  gap: 10px !important;
}

.room-mark {
  width: 36px;
  height: 36px;
  flex: 0 0 36px;
  border: 1px solid var(--ds-orange-100, #fee9df);
  border-radius: 11px;
  display: grid;
  place-items: center;
  color: var(--ds-orange-action, #cf3d12);
  background: var(--ds-orange-50, #fff7f2);
}

.room-mark svg {
  width: 20px;
  height: 20px;
}

.meeting-title-copy {
  min-width: 0;
  display: grid;
  gap: 2px;
}

.meeting-title-copy small {
  color: var(--ds-muted, #6b7280);
  font-size: 11px;
  font-weight: 600;
  line-height: 1.2;
}

.meeting-title {
  max-width: min(36vw, 460px) !important;
  overflow: hidden;
  color: var(--ds-ink, #12141a) !important;
  font-size: 15px !important;
  font-weight: 700 !important;
  line-height: 1.3 !important;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.room-header :deep(.el-tag) {
  height: 26px !important;
  min-height: 26px !important;
  padding: 0 9px !important;
  font-size: 11px !important;
}

.room-header .header-right {
  gap: 0 !important;
}

.net-status,
.participant-num,
.countdown-pill {
  height: 36px !important;
  min-height: 36px !important;
  min-width: 0 !important;
  padding: 0 16px !important;
  border: 0 !important;
  border-radius: 0 !important;
  background: transparent !important;
}

.net-status + .participant-num,
.participant-num + .countdown-pill {
  border-left: 1px solid var(--ds-line, rgba(28, 26, 22, .09)) !important;
}

.participant-num {
  gap: 6px !important;
}

.participant-num span,
.countdown-label {
  color: var(--ds-muted, #6b7280) !important;
  font-size: 12px !important;
  font-weight: 600 !important;
}

.participant-num strong,
.countdown-time,
.net-text {
  color: var(--ds-ink, #12141a) !important;
  font-size: 14px !important;
  font-weight: 700 !important;
}

.countdown-time {
  color: var(--ds-orange-800, #b12f0a) !important;
}

.room-body {
  padding: 88px 24px 96px !important;
}

.video-area {
  border-radius: 18px !important;
  box-shadow: none !important;
}

.video-grid,
.grid-empty {
  background:
    radial-gradient(circle at 50% 46%, rgba(232, 74, 28, .045), transparent 26%),
    linear-gradient(180deg, #fbfbfc 0%, #f5f5f6 100%) !important;
}

.grid-empty {
  border: 0 !important;
}

.empty-visualizer {
  width: min(27vw, 240px) !important;
  height: min(27vw, 240px) !important;
  min-width: 180px !important;
  min-height: 180px !important;
  margin-bottom: -16px !important;
  opacity: .72;
}

.empty-title {
  color: var(--ds-ink, #12141a) !important;
  font-size: 15px !important;
  font-weight: 700 !important;
  letter-spacing: 0 !important;
}

.empty-subtitle {
  margin-top: 7px;
  color: var(--ds-muted, #6b7280) !important;
  font-size: 12px !important;
  font-weight: 500 !important;
  letter-spacing: 0 !important;
}

.control-bar {
  height: 80px !important;
  padding: 10px 24px !important;
  border-top: 1px solid var(--ds-line, rgba(28, 26, 22, .09)) !important;
  background: var(--ds-surface-solid, #fffaf7) !important;
  box-shadow: none !important;
}

.control-left,
.control-center,
.control-right {
  min-height: 0 !important;
  padding: 0 !important;
  border: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
}

.control-section {
  gap: 8px !important;
}

.control-bar :deep(.el-button) {
  width: 42px !important;
  height: 42px !important;
  min-width: 42px !important;
  padding: 0 !important;
  border-radius: 12px !important;
}

.control-center :deep(.el-button.score-cta),
.control-center :deep(.el-button.ai-score-btn),
.control-center :deep(.el-button[class*="score"]) {
  width: auto !important;
  min-width: 118px !important;
  padding: 0 14px !important;
}

.control-bar :deep(.el-button--danger) {
  width: auto !important;
  min-width: 116px !important;
  padding: 0 16px !important;
  border-radius: var(--ds-radius-pill, 999px) !important;
}

@media (max-width: 900px) {
  .room-header {
    height: 64px !important;
    min-height: 64px !important;
    padding: 0 16px !important;
  }

  .room-mark {
    width: 32px;
    height: 32px;
    flex-basis: 32px;
  }

  .meeting-title-copy small,
  .participant-num span,
  .countdown-label,
  .net-text {
    display: none !important;
  }

  .meeting-title {
    max-width: 34vw !important;
    font-size: 13px !important;
  }

  .net-status,
  .participant-num,
  .countdown-pill {
    padding: 0 10px !important;
  }

  .room-body {
    padding: 76px 12px 112px !important;
  }
}

@media (max-width: 640px) {
  .room-header {
    grid-template-columns: minmax(0, 1fr) auto !important;
  }

  .room-mark,
  .room-header :deep(.el-tag),
  .net-status {
    display: none !important;
  }

  .meeting-title {
    max-width: 42vw !important;
  }

  .control-bar {
    min-height: 88px !important;
    padding: 8px 10px calc(8px + env(safe-area-inset-bottom)) !important;
  }
}

:global(body:has(.app-container.is-meeting-route) .el-message) {
  top: 84px !important;
}
</style>

<style scoped>
/* Light meeting room: consistent with the Home and Training workspace. */
.meeting-room,
.meeting-room:fullscreen {
  color: var(--ds-ink, #12141a) !important;
  background-color: var(--ds-canvas, #f3f4f6) !important;
  background-image: var(--ds-canvas-background) !important;
}

.room-grid-bg,
.room-orbit,
.meeting-room::before {
  display: none !important;
}

.room-header {
  min-height: 64px !important;
  padding: 0 20px !important;
  border: 1px solid var(--ds-line, rgba(28, 26, 22, .09)) !important;
  border-radius: var(--ds-radius-lg, 16px) !important;
  background: var(--ds-surface-solid, #fffaf7) !important;
  box-shadow: var(--ds-card-shadow, 0 8px 24px rgba(28, 26, 22, .06)) !important;
  backdrop-filter: none !important;
}

.meeting-title,
.participant-num,
.participant-num strong,
.countdown-time {
  color: var(--ds-ink, #12141a) !important;
}

.participant-num span,
.countdown-label {
  color: var(--ds-muted, #6b7280) !important;
}

.room-header :deep(.el-tag),
.participant-num,
.countdown-pill,
.livekit-agent-chip,
.net-status {
  border: 1px solid var(--ds-line, rgba(28, 26, 22, .09)) !important;
  background: var(--ds-surface, rgba(255, 250, 247, .92)) !important;
  box-shadow: none !important;
}

.room-header :deep(.el-tag),
.livekit-agent-chip.connected {
  color: var(--ds-green, #0f9f6e) !important;
  border-color: rgba(15, 159, 110, .22) !important;
  background: var(--ds-status-success-bg, rgba(15, 159, 110, .08)) !important;
}

.countdown-pill {
  border-color: var(--ds-orange-100, #fee9df) !important;
  background: var(--ds-orange-50, #fff7f2) !important;
}

.countdown-time {
  color: var(--ds-orange-800, #b12f0a) !important;
}

.room-body {
  background: transparent !important;
}

.video-area {
  border: 1px solid var(--ds-line-strong, rgba(28, 26, 22, .13)) !important;
  border-radius: var(--ds-radius-lg, 16px) !important;
  background: var(--ds-surface-solid, #fffaf7) !important;
  box-shadow: var(--ds-card-shadow, 0 8px 24px rgba(28, 26, 22, .06)) !important;
}

.video-grid,
.screen-share-layout,
.screen-main,
.dual-main,
.multi-main {
  background: var(--ds-surface-solid, #fffaf7) !important;
}

.grid-empty {
  color: var(--ds-ink, #12141a) !important;
  border: 1px solid var(--ds-line, rgba(28, 26, 22, .09)) !important;
  background:
    radial-gradient(circle at 50% 42%, rgba(232, 74, 28, .055), transparent 30%),
    linear-gradient(var(--ds-line, rgba(28, 26, 22, .045)) 1px, transparent 1px),
    linear-gradient(90deg, var(--ds-line, rgba(28, 26, 22, .045)) 1px, transparent 1px),
    var(--ds-surface-solid, #fffaf7) !important;
  background-size: auto, 48px 48px, 48px 48px, auto !important;
  box-shadow: none !important;
}

.empty-title {
  color: var(--ds-ink, #12141a) !important;
}

.empty-subtitle {
  color: var(--ds-muted, #6b7280) !important;
}

.video-tile,
.sidebar-tile,
.screen-tile,
.dual-tile,
.multi-tile,
.multi-tile-small {
  border-color: var(--ds-line-strong, rgba(28, 26, 22, .13)) !important;
  background: var(--ds-canvas-deep, #ebecef) !important;
  box-shadow: none !important;
}

.video-tile.is-speaking,
.sidebar-tile.is-speaking,
.dual-tile.is-speaking,
.multi-tile-small.is-speaking {
  border-color: rgba(15, 159, 110, .64) !important;
  box-shadow: 0 0 0 2px rgba(15, 159, 110, .12) !important;
}

.video-tile video,
.screen-tile video,
.dual-tile video,
.multi-tile video,
.multi-tile-small video,
.screen-main video {
  background: #181a1f !important;
}

.tile-info {
  color: #fffaf7 !important;
  background: linear-gradient(180deg, transparent, rgba(18, 20, 26, .74)) !important;
}

.control-bar {
  border-top: 1px solid var(--ds-line, rgba(28, 26, 22, .09)) !important;
  background: var(--ds-surface-solid, #fffaf7) !important;
  box-shadow: 0 -8px 24px rgba(28, 26, 22, .05) !important;
  backdrop-filter: none !important;
}

.control-section {
  border: 1px solid var(--ds-line, rgba(28, 26, 22, .09)) !important;
  background: var(--ds-canvas, #f3f4f6) !important;
  box-shadow: none !important;
}

.control-bar :deep(.el-button) {
  border-color: var(--ds-btn-secondary-border, rgba(28, 26, 22, .13)) !important;
  color: var(--ds-ink-2, #2c3038) !important;
  background: var(--ds-btn-secondary-bg, #fffaf7) !important;
  box-shadow: none !important;
  transform: none !important;
}

.control-bar :deep(.el-button:hover) {
  border-color: var(--ds-btn-secondary-border-hover, rgba(232, 74, 28, .32)) !important;
  color: var(--ds-orange-800, #b12f0a) !important;
  background: var(--ds-orange-50, #fff7f2) !important;
}

.control-bar :deep(.el-button.btn-active),
.control-bar :deep(.el-button.btn-live),
.control-bar :deep(.el-button.btn-recording) {
  border-color: var(--ds-orange-100, #fee9df) !important;
  color: var(--ds-orange-800, #b12f0a) !important;
  background: var(--ds-orange-50, #fff7f2) !important;
}

.control-bar :deep(.el-button.btn-off) {
  border-color: rgba(216, 58, 69, .28) !important;
  color: var(--ds-red, #d83a45) !important;
  background: rgba(216, 58, 69, .08) !important;
}

.control-bar :deep(.el-button--danger) {
  border-color: rgba(216, 58, 69, .36) !important;
  color: var(--ds-red, #d83a45) !important;
  background: var(--ds-surface-solid, #fffaf7) !important;
}

.control-bar :deep(.el-button--danger:hover) {
  border-color: var(--ds-red, #d83a45) !important;
  color: #fffaf7 !important;
  background: var(--ds-red, #d83a45) !important;
}

.secondary-toggle,
.sidebar-toggle {
  color: var(--ds-ink-2, #2c3038) !important;
  border-color: var(--ds-line-strong, rgba(28, 26, 22, .13)) !important;
  background: var(--ds-surface-solid, #fffaf7) !important;
  box-shadow: var(--ds-shadow-soft, 0 8px 24px rgba(28, 26, 22, .08)) !important;
}

.reconnect-overlay {
  background: rgba(243, 244, 246, .86) !important;
}

.reconnect-box {
  color: var(--ds-ink, #12141a) !important;
  border: 1px solid var(--ds-line, rgba(28, 26, 22, .09)) !important;
  background: var(--ds-surface-solid, #fffaf7) !important;
  box-shadow: var(--ds-shadow-soft, 0 16px 44px rgba(28, 26, 22, .12)) !important;
}

.reconnect-text {
  color: var(--ds-ink, #12141a) !important;
}

.reconnect-hint {
  color: var(--ds-muted, #6b7280) !important;
}

.reconnect-spinner {
  border-color: var(--ds-line-strong, rgba(28, 26, 22, .13)) !important;
  border-top-color: var(--ds-orange-action, #cf3d12) !important;
}

:global(.meeting-quality-popper),
:global(.meeting-mobile-more-popper),
:global(.meeting-quality-popper .el-dropdown-menu),
:global(.meeting-mobile-more-popper .el-dropdown-menu) {
  border-color: var(--ds-line, rgba(28, 26, 22, .09)) !important;
  background: var(--ds-surface-solid, #fffaf7) !important;
  box-shadow: var(--ds-shadow-soft, 0 16px 44px rgba(28, 26, 22, .12)) !important;
}

:global(.meeting-quality-popper .el-dropdown-menu__item),
:global(.meeting-mobile-more-popper .el-dropdown-menu__item) {
  color: var(--ds-ink-2, #2c3038) !important;
}

:global(.meeting-quality-popper .el-dropdown-menu__item:hover),
:global(.meeting-mobile-more-popper .el-dropdown-menu__item:hover),
:global(.meeting-quality-popper .is-active-quality),
:global(.meeting-mobile-more-popper .is-active-quality) {
  color: var(--ds-orange-800, #b12f0a) !important;
  background: var(--ds-orange-50, #fff7f2) !important;
}

@media (max-width: 768px) {
  .room-header {
    border-radius: 0 !important;
    background: var(--ds-surface-solid, #fffaf7) !important;
  }

  .room-body {
    background: transparent !important;
  }

  .control-bar {
    background: var(--ds-surface-solid, #fffaf7) !important;
  }
}
</style>

<style scoped>
/* Keep the v2 composition above the base light-theme palette. */
.room-header {
  top: 0 !important;
  right: 0 !important;
  left: 0 !important;
  width: 100% !important;
  height: 72px !important;
  min-height: 72px !important;
  padding: 0 24px !important;
  border: 0 !important;
  border-bottom: 1px solid var(--ds-line, rgba(28, 26, 22, .09)) !important;
  border-radius: 0 !important;
  box-shadow: none !important;
}

.room-header .header-left,
.room-header .header-right {
  padding: 0 !important;
  border: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
}

.meeting-title-wrap {
  flex-direction: row !important;
}

.net-status,
.participant-num,
.countdown-pill {
  height: 36px !important;
  min-height: 36px !important;
  min-width: 0 !important;
  padding: 0 16px !important;
  border: 0 !important;
  border-radius: 0 !important;
  background: transparent !important;
}

.net-status + .participant-num,
.participant-num + .countdown-pill {
  border-left: 1px solid var(--ds-line, rgba(28, 26, 22, .09)) !important;
}

.video-grid,
.grid-empty {
  background:
    radial-gradient(circle at 50% 46%, rgba(232, 74, 28, .045), transparent 26%),
    linear-gradient(180deg, #fbfbfc 0%, #f5f5f6 100%) !important;
}

.grid-empty {
  border: 0 !important;
  box-shadow: none !important;
}

.control-left,
.control-center,
.control-right {
  padding: 0 !important;
  border: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
}

@media (max-width: 900px) {
  .room-header {
    height: 64px !important;
    min-height: 64px !important;
    padding: 0 16px !important;
  }

  .net-status,
  .participant-num,
  .countdown-pill {
    padding: 0 10px !important;
  }

  .control-bar {
    height: 72px !important;
    min-height: 72px !important;
    padding: 8px 12px !important;
    display: grid !important;
    grid-template-columns: auto minmax(0, 1fr) auto !important;
    grid-template-rows: 1fr !important;
    align-items: center !important;
    gap: 8px !important;
  }

  .control-left,
  .control-center,
  .control-right {
    position: static !important;
    grid-row: 1 !important;
    width: auto !important;
    min-width: 0 !important;
    gap: 6px !important;
  }

  .control-left { grid-column: 1 !important; }
  .control-center { grid-column: 2 !important; }
  .control-right { grid-column: 3 !important; }

  .control-bar :deep(.el-button) {
    width: 38px !important;
    height: 38px !important;
    min-width: 38px !important;
  }

  .control-center :deep(.el-button.score-cta),
  .control-center :deep(.el-button.ai-score-btn),
  .control-center :deep(.el-button[class*="score"]) {
    min-width: 108px !important;
    padding: 0 10px !important;
  }

  .control-bar :deep(.el-button--danger) {
    min-width: 100px !important;
    padding: 0 12px !important;
  }
}

/* ==================== Clean Premium Light Stage (final) ==================== */
.meeting-room {
  --room-rail-width: 228px;
  display: flex !important;
  flex-direction: column !important;
  height: 100dvh !important;
  min-height: 100dvh !important;
  background: #ffffff !important;
  color: #1f2937 !important;
  overflow: hidden !important;
}

.meeting-room:fullscreen {
  height: 100vh !important;
  min-height: 100vh !important;
  background: #ffffff !important;
}

.meeting-room::before,
.meeting-room .room-grid-bg,
.meeting-room .room-orbit {
  opacity: 0 !important;
  display: none !important;
}

/*
  Flow layout (not absolute overlay):
  header → body (flex 1) → control bar
  Content can never be covered by chrome; no fake top/bottom padding rings.
*/
.meeting-room .room-header {
  position: relative !important;
  top: auto !important;
  left: auto !important;
  right: auto !important;
  flex: 0 0 auto !important;
  height: 52px !important;
  min-height: 52px !important;
  padding: 0 16px !important;
  margin: 0 !important;
  background: #ffffff !important;
  border: 0 !important;
  border-bottom: 1px solid rgba(15, 23, 42, 0.07) !important;
  box-shadow: none !important;
  backdrop-filter: none !important;
  z-index: 20 !important;
  pointer-events: auto !important;
}

.meeting-room .room-header .header-left,
.meeting-room .room-header .header-right {
  pointer-events: auto !important;
}

.meeting-room .control-bar {
  position: relative !important;
  left: auto !important;
  right: auto !important;
  bottom: auto !important;
  top: auto !important;
  flex: 0 0 auto !important;
  height: auto !important;
  min-height: 72px !important;
  max-height: none !important;
  padding: 10px 16px calc(10px + env(safe-area-inset-bottom, 0px)) !important;
  margin: 0 !important;
  background: #ffffff !important;
  border: 0 !important;
  border-top: 1px solid rgba(15, 23, 42, 0.08) !important;
  box-shadow: none !important;
  backdrop-filter: none !important;
  z-index: 20 !important;
}

.meeting-room .room-body {
  position: relative !important;
  flex: 1 1 auto !important;
  padding: 0 !important;
  gap: 0 !important;
  margin: 0 !important;
  background: #ffffff !important;
  min-height: 0 !important;
  height: auto !important;
  overflow: hidden !important;
  display: flex !important;
}

.meeting-room .video-area {
  background: #f3f4f6 !important;
  border: 0 !important;
  border-radius: 0 !important;
  box-shadow: none !important;
  padding: 0 !important;
  overflow: hidden !important;
  width: 100% !important;
  height: 100% !important;
  min-height: 0 !important;
  flex: 1 1 auto !important;
  align-items: stretch !important;
  justify-content: stretch !important;
}

.meeting-room .video-area::before,
.meeting-room .video-area::after {
  display: none !important;
}

.meeting-room .video-grid,
.meeting-room .screen-share-layout {
  padding: 0 !important;
  gap: 0 !important;
  background: #f3f4f6 !important;
  width: 100% !important;
  height: 100% !important;
  min-height: 0 !important;
  max-height: 100% !important;
  border-radius: 0 !important;
  box-sizing: border-box !important;
  overflow: hidden !important;
}

/* Main stage surfaces: flat white, zero radius */
.meeting-room .video-tile,
.meeting-room .screen-tile,
.meeting-room .dual-tile,
.meeting-room .multi-tile,
.meeting-room .grid-empty,
.meeting-room .screen-main,
.meeting-room .dual-main,
.meeting-room .multi-main {
  background: #ffffff !important;
  border: 0 !important;
  border-radius: 0 !important;
  box-shadow: none !important;
  min-height: 0 !important;
}

.meeting-room .video-tile,
.meeting-room .screen-tile,
.meeting-room .dual-tile,
.meeting-room .multi-tile,
.meeting-room .grid-empty {
  border-radius: 0 !important;
  width: 100% !important;
  height: 100% !important;
  max-width: none !important;
  max-height: none !important;
  margin: 0 !important;
}

.meeting-room .video-grid .video-tile:only-child,
.meeting-room .grid-empty {
  max-width: none !important;
  max-height: none !important;
  width: 100% !important;
  height: 100% !important;
  margin: 0 !important;
  border-radius: 0 !important;
}

.meeting-room .video-tile:hover,
.meeting-room .screen-tile:hover,
.meeting-room .dual-tile:hover,
.meeting-room .multi-tile:hover {
  border-color: transparent !important;
  box-shadow: none !important;
}

/* Letterbox fill — light, never black under contain */
.meeting-room .video-tile video,
.meeting-room .screen-tile video,
.meeting-room .dual-tile video,
.meeting-room .multi-tile video,
.meeting-room .video-grid.has-mobile-primary-video .video-tile.mobile-primary-video video {
  background: #f0f2f5 !important;
}

/* Shared screen must fully fit inside stage (not cropped under chrome) */
.meeting-room .screen-tile video,
.meeting-room .dual-main .dual-tile video,
.meeting-room .multi-tile video,
.meeting-room .video-area.video-fit-contain .screen-tile video,
.meeting-room .video-area.video-fit-cover .screen-tile video {
  object-fit: contain !important;
  width: 100% !important;
  height: 100% !important;
}

/* Screen-share: main + right rail, both fully inside safe stage */
.meeting-room .screen-share-layout.layout-default {
  display: flex !important;
  flex-direction: row !important;
  align-items: stretch !important;
  gap: 0 !important;
  background: #ffffff !important;
  overflow: hidden !important;
}

.meeting-room .screen-main {
  flex: 1 1 auto !important;
  min-width: 0 !important;
  min-height: 0 !important;
  height: 100% !important;
  background: #ffffff !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  overflow: hidden !important;
  position: relative !important;
}

.meeting-room .screen-main .screen-tile {
  position: relative !important;
  width: 100% !important;
  height: 100% !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  overflow: hidden !important;
}

/* Right participant rail — full height, content packs from top */
.meeting-room .screen-sidebar,
.meeting-room .dual-sidebar {
  position: relative !important;
  flex: 0 0 var(--room-rail-width) !important;
  width: var(--room-rail-width) !important;
  max-width: var(--room-rail-width) !important;
  height: 100% !important;
  max-height: 100% !important;
  min-height: 0 !important;
  display: flex !important;
  flex-direction: column !important;
  align-items: stretch !important;
  justify-content: flex-start !important;
  gap: 10px !important;
  padding: 12px !important;
  background: #eef0f3 !important;
  border-left: 1px solid rgba(15, 23, 42, 0.08) !important;
  overflow-x: hidden !important;
  overflow-y: auto !important;
  overscroll-behavior: contain !important;
  box-sizing: border-box !important;
  z-index: 2 !important;
}

.meeting-room .screen-sidebar::-webkit-scrollbar,
.meeting-room .dual-sidebar::-webkit-scrollbar {
  width: 4px !important;
}

.meeting-room .screen-sidebar::-webkit-scrollbar-thumb,
.meeting-room .dual-sidebar::-webkit-scrollbar-thumb {
  background: rgba(15, 23, 42, 0.16) !important;
  border-radius: 999px !important;
}

/* Toggle sits on the rail edge, fully visible */
.meeting-room .sidebar-toggle {
  position: absolute !important;
  top: 50% !important;
  right: calc(var(--room-rail-width) - 1px) !important;
  left: auto !important;
  transform: translate(50%, -50%) !important;
  width: 28px !important;
  height: 48px !important;
  border-radius: 999px !important;
  background: #ffffff !important;
  color: #475569 !important;
  border: 1px solid rgba(15, 23, 42, 0.1) !important;
  box-shadow: 0 4px 14px rgba(15, 23, 42, 0.1) !important;
  z-index: 8 !important;
}

.meeting-room .sidebar-toggle.collapsed {
  right: 8px !important;
  transform: translate(0, -50%) !important;
}

.meeting-room .sidebar-toggle:hover {
  color: #e84a1c !important;
  border-color: rgba(232, 74, 28, 0.28) !important;
}

/*
  Sidebar participant card:
  preview (fixed) + meta (auto height, multi-line, never clipped by absolute overlay)
*/
.meeting-room .sidebar-tile,
.meeting-room .sidebar-tile-sm {
  position: relative !important;
  width: 100% !important;
  height: auto !important;
  min-height: 0 !important;
  max-height: none !important;
  flex: 0 0 auto !important;
  display: block !important;
  background: #f7f8fa !important;
  /* only a light stroke — no drop shadow */
  border: 1px solid rgba(15, 23, 42, 0.08) !important;
  border-radius: 14px !important;
  box-shadow: none !important;
  filter: none !important;
  outline: none !important;
  overflow: hidden !important;
  cursor: pointer !important;
  transform: none !important;
}

.meeting-room .sidebar-tile:hover,
.meeting-room .sidebar-tile-sm:hover,
.meeting-room .sidebar-tile:focus,
.meeting-room .sidebar-tile-sm:focus,
.meeting-room .sidebar-tile.is-speaking,
.meeting-room .sidebar-tile-sm.is-speaking,
.meeting-room .sidebar-tile.is-local,
.meeting-room .sidebar-tile-sm.is-local {
  border: 1px solid rgba(15, 23, 42, 0.12) !important;
  box-shadow: none !important;
  filter: none !important;
  transform: none !important;
}

.meeting-room .sidebar-tile.is-local::before,
.meeting-room .sidebar-tile-sm.is-local::before {
  display: none !important;
  content: none !important;
  box-shadow: none !important;
}

.meeting-room .sidebar-tile-preview {
  position: relative !important;
  width: 100% !important;
  height: 120px !important;
  min-height: 120px !important;
  display: grid !important;
  place-items: center !important;
  background:
    radial-gradient(circle at 50% 42%, rgba(255, 255, 255, 0.9), transparent 58%),
    #f3f4f6 !important;
  overflow: hidden !important;
  border-radius: 14px !important;
}

.meeting-room .sidebar-tile-preview > video {
  width: 100% !important;
  height: 100% !important;
  object-fit: cover !important;
  background: #e8eaee !important;
}

/* VoiceAvatar is huge by default — force it into the rail preview */
.meeting-room .sidebar-tile-preview > .voice-avatar {
  width: 100% !important;
  max-width: 100% !important;
  height: 100% !important;
  min-height: 0 !important;
  display: grid !important;
  place-items: center !important;
  overflow: hidden !important;
}

.meeting-room .sidebar-tile-preview > .voice-avatar :deep(.voice-wave),
.meeting-room .sidebar-tile-preview > .voice-avatar :deep(.avatar-aura),
.meeting-room .sidebar-tile-preview > .voice-avatar :deep(.avatar-halo) {
  display: none !important;
}

.meeting-room .sidebar-tile-preview > .voice-avatar :deep(.avatar-core) {
  width: 48px !important;
  height: 48px !important;
  min-width: 48px !important;
  min-height: 48px !important;
}

.meeting-room .sidebar-tile-preview > .voice-avatar :deep(.avatar-initials) {
  font-size: 16px !important;
  letter-spacing: 0 !important;
}

/* Name + status float on the card — no color block */
.meeting-room .sidebar-tile-meta {
  position: absolute !important;
  left: 10px !important;
  right: 10px !important;
  bottom: 10px !important;
  z-index: 3 !important;
  display: flex !important;
  align-items: center !important;
  gap: 6px !important;
  width: auto !important;
  min-width: 0 !important;
  min-height: 0 !important;
  padding: 0 !important;
  margin: 0 !important;
  box-sizing: border-box !important;
  background: transparent !important;
  border: 0 !important;
  border-top: 0 !important;
  box-shadow: none !important;
  overflow: visible !important;
  pointer-events: none !important;
}

.meeting-room .sidebar-status {
  flex: 0 0 8px !important;
  width: 8px !important;
  height: 8px !important;
  margin: 0 !important;
  border-radius: 50% !important;
  background: #22c55e !important;
  box-shadow:
    0 0 0 2px rgba(255, 255, 255, 0.9),
    0 0 0 3px rgba(34, 197, 94, 0.2) !important;
}

.meeting-room .sidebar-status.is-muted {
  background: #ef4444 !important;
  box-shadow:
    0 0 0 2px rgba(255, 255, 255, 0.9),
    0 0 0 3px rgba(239, 68, 68, 0.2) !important;
}

.meeting-room .sidebar-name {
  flex: 1 1 auto !important;
  min-width: 0 !important;
  color: #111827 !important;
  font-size: 12px !important;
  font-weight: 700 !important;
  line-height: 1.35 !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  display: block !important;
  max-height: none !important;
  background: transparent !important;
  border: 0 !important;
  box-shadow: none !important;
  /* soft legibility on light preview without a solid chip */
  text-shadow:
    0 0 6px rgba(255, 255, 255, 0.95),
    0 1px 2px rgba(255, 255, 255, 0.9) !important;
  -webkit-line-clamp: unset !important;
  line-clamp: unset !important;
}

.meeting-room .sidebar-tile.is-speaking .sidebar-name {
  color: #0f766e !important;
}

.meeting-room .sidebar-tile.is-speaking {
  border-color: rgba(15, 23, 42, 0.12) !important;
  box-shadow: none !important;
}

/* dual layout still uses old class names on small tiles */
.meeting-room .sidebar-tile-sm,
.meeting-room .multi-tile-small {
  position: relative !important;
  width: 100% !important;
  height: auto !important;
  min-height: 0 !important;
  display: flex !important;
  flex-direction: column !important;
  background: #f7f8fa !important;
  border: 1px solid rgba(15, 23, 42, 0.08) !important;
  border-radius: 12px !important;
  box-shadow: none !important;
  overflow: hidden !important;
}

.meeting-room .video-grid.has-mobile-primary-video .video-tile:not(.mobile-primary-video) {
  background: #ffffff !important;
  border: 1px solid rgba(15, 23, 42, 0.1) !important;
  border-radius: 10px !important;
  box-shadow: 0 6px 18px rgba(15, 23, 42, 0.08) !important;
}

.meeting-room .sidebar-tile-sm video,
.meeting-room .multi-tile-small video,
.meeting-room .video-grid.has-mobile-primary-video .video-tile:not(.mobile-primary-video) video {
  background: #f0f2f5 !important;
  object-fit: cover !important;
}

/* Main stage name: floating, full text */
.meeting-room .video-tile > .tile-info,
.meeting-room .screen-tile > .tile-info,
.meeting-room .dual-tile > .tile-info,
.meeting-room .multi-tile > .tile-info {
  position: absolute !important;
  left: 14px !important;
  right: auto !important;
  bottom: 14px !important;
  width: max-content !important;
  max-width: min(72%, 520px) !important;
  height: auto !important;
  padding: 0 !important;
  background: transparent !important;
  background-image: none !important;
  border: 0 !important;
  box-shadow: none !important;
  pointer-events: none;
  z-index: 4 !important;
}

.meeting-room .video-tile > .tile-info .tile-name,
.meeting-room .screen-tile > .tile-info .tile-name,
.meeting-room .dual-tile > .tile-info .tile-name,
.meeting-room .multi-tile > .tile-info .tile-name {
  display: inline-flex !important;
  align-items: center !important;
  gap: 7px !important;
  width: auto !important;
  max-width: none !important;
  min-height: 30px !important;
  padding: 5px 12px !important;
  color: #1f2937 !important;
  background: rgba(255, 255, 255, 0.96) !important;
  border: 1px solid rgba(15, 23, 42, 0.1) !important;
  box-shadow: 0 2px 10px rgba(15, 23, 42, 0.08) !important;
  border-radius: 999px !important;
  font-size: 13px !important;
  font-weight: 700 !important;
  line-height: 1.35 !important;
  white-space: normal !important;
  overflow: visible !important;
  text-overflow: clip !important;
  word-break: break-word !important;
  text-shadow: none !important;
  animation: none !important;
}

/* Speaking / muted on light chips */
.meeting-room .video-tile.is-speaking:not(.is-muted) .tile-name,
.meeting-room .dual-tile.is-speaking:not(.is-muted) .tile-name,
.meeting-room .sidebar-tile.is-speaking:not(.is-muted) .tile-name,
.meeting-room .sidebar-tile-sm.is-speaking:not(.is-muted) .tile-name,
.meeting-room .multi-tile-small.is-speaking:not(.is-muted) .tile-name {
  color: #0f766e !important;
  border-color: rgba(16, 185, 129, 0.45) !important;
  background: #ecfdf5 !important;
  animation: none !important;
}

.meeting-room .tile-name::before {
  background: #22c55e !important;
  box-shadow: 0 0 0 3px rgba(34, 197, 94, 0.12) !important;
}

.meeting-room .video-tile.is-muted .tile-name::before,
.meeting-room .dual-tile.is-muted .tile-name::before,
.meeting-room .sidebar-tile.is-muted .tile-name::before,
.meeting-room .sidebar-tile-sm.is-muted .tile-name::before,
.meeting-room .multi-tile-small.is-muted .tile-name::before {
  background: #ef4444 !important;
  box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.12) !important;
}

/* Main-stage avatar: larger premium brand orb on clean white */
.meeting-room .video-tile > .voice-avatar,
.meeting-room .dual-tile > .voice-avatar {
  width: min(280px, 34vw) !important;
  height: min(280px, 34vw) !important;
}

.meeting-room .video-tile > .voice-avatar :deep(.avatar-core),
.meeting-room .dual-tile > .voice-avatar :deep(.avatar-core) {
  width: min(120px, 14vw) !important;
  height: min(120px, 14vw) !important;
}

.meeting-room .video-tile > .voice-avatar :deep(.avatar-initials),
.meeting-room .dual-tile > .voice-avatar :deep(.avatar-initials) {
  font-size: min(40px, 4.6vw) !important;
}

.meeting-room .video-tile:has(> .voice-avatar) {
  background:
    radial-gradient(ellipse 46% 30% at 50% 56%, rgba(90, 130, 210, 0.07), transparent 72%),
    #ffffff !important;
}

.meeting-room .avatar-block {
  background:
    radial-gradient(circle at 34% 28%, rgba(255, 255, 255, 0.78), transparent 36%),
    linear-gradient(145deg, #9bb8f5 0%, #6b93e8 48%, #4a78d4 100%) !important;
  border: 1px solid rgba(255, 255, 255, 0.5) !important;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.55),
    0 0 0 10px rgba(90, 130, 210, 0.07),
    0 16px 36px rgba(90, 130, 210, 0.2) !important;
}

.meeting-room .avatar-text {
  color: #ffffff !important;
  text-shadow: 0 1px 2px rgba(30, 50, 100, 0.22);
}

/* Sidebar small orbs stay blue-consistent */
.meeting-room .sidebar-tile-preview > .voice-avatar :deep(.avatar-core) {
  background:
    radial-gradient(circle at 34% 28%, rgba(255, 255, 255, 0.75), transparent 36%),
    linear-gradient(145deg, #9bb8f5 0%, #6b93e8 48%, #4a78d4 100%) !important;
  border-color: rgba(255, 255, 255, 0.5) !important;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.5),
    0 6px 14px rgba(90, 130, 210, 0.2) !important;
}

/* Sidebar collapse control */
.meeting-room .sidebar-toggle {
  background: #ffffff !important;
  color: #475569 !important;
  border: 1px solid rgba(15, 23, 42, 0.1) !important;
  box-shadow: 0 4px 14px rgba(15, 23, 42, 0.08) !important;
}

.meeting-room .sidebar-toggle:hover {
  background: #ffffff !important;
  color: #e84a1c !important;
  border-color: rgba(232, 74, 28, 0.28) !important;
}

.meeting-room .secondary-toggle {
  background: #ffffff !important;
  color: #334155 !important;
  border: 1px solid rgba(15, 23, 42, 0.1) !important;
  box-shadow: 0 6px 16px rgba(15, 23, 42, 0.08) !important;
}

/* Filmstrip when multi-cam (no screen share) */
.meeting-room .video-grid.has-mobile-primary-video .video-tile.mobile-primary-video {
  background: #ffffff !important;
  border-radius: 0 !important;
}

.meeting-room .video-grid.has-mobile-primary-video .video-tile:not(.mobile-primary-video) {
  background: #ffffff !important;
  border: 1px solid rgba(15, 23, 42, 0.1) !important;
  border-radius: 10px !important;
  box-shadow: 0 6px 18px rgba(15, 23, 42, 0.08) !important;
}

.meeting-room .video-grid.has-mobile-primary-video .video-tile:not(.mobile-primary-video) .tile-name {
  max-width: 100% !important;
}

/* Empty state clean */
.meeting-room .grid-empty {
  color: #64748b !important;
  background: #ffffff !important;
  border-radius: 0 !important;
}

/* Header right: plain text meta, no gray cards */
.meeting-room .header-right {
  display: inline-flex !important;
  align-items: center !important;
  gap: 14px !important;
}

.meeting-room .header-plain-meta,
.meeting-room .net-status.header-plain-meta,
.meeting-room .participant-num.header-plain-meta {
  display: inline-flex !important;
  align-items: center !important;
  gap: 5px !important;
  min-height: 0 !important;
  height: auto !important;
  padding: 0 !important;
  margin: 0 !important;
  border: 0 !important;
  border-radius: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
  color: #64748b !important;
  font-size: 12px !important;
  font-weight: 600 !important;
}

.meeting-room .participant-num.header-plain-meta span {
  display: inline !important;
  color: #64748b !important;
}

.meeting-room .participant-num.header-plain-meta strong {
  color: #111827 !important;
  font-size: 13px !important;
  font-weight: 800 !important;
  font-variant-numeric: tabular-nums !important;
}

.meeting-room .net-status.header-plain-meta .net-text {
  color: inherit !important;
  font-size: 12px !important;
  font-weight: 700 !important;
}

.meeting-room .net-status.header-plain-meta .signal-bars {
  height: 12px !important;
}

.meeting-room .net-status.header-plain-meta .bar {
  width: 3px !important;
  background: #cbd5e1 !important;
}

.meeting-room .signal-bars[data-level="1"] .b1 { background: #ef4444 !important; }
.meeting-room .signal-bars[data-level="2"] .b1,
.meeting-room .signal-bars[data-level="2"] .b2 { background: #f59e0b !important; }
.meeting-room .signal-bars[data-level="3"] .b1,
.meeting-room .signal-bars[data-level="3"] .b2,
.meeting-room .signal-bars[data-level="3"] .b3 { background: #22c55e !important; }

/* 进行中 = green pill */
.meeting-room .meeting-status-badge {
  display: inline-flex !important;
  align-items: center !important;
  min-height: 24px !important;
  padding: 0 10px !important;
  border-radius: 999px !important;
  font-size: 12px !important;
  font-weight: 750 !important;
  line-height: 1 !important;
  border: 1px solid transparent !important;
}

.meeting-room .meeting-status-badge.is-running {
  color: #15803d !important;
  background: #dcfce7 !important;
  border-color: rgba(34, 197, 94, 0.28) !important;
}

.meeting-room .meeting-status-badge.is-ended {
  color: #64748b !important;
  background: #f1f5f9 !important;
  border-color: rgba(100, 116, 139, 0.2) !important;
}

.meeting-room .meeting-status-badge.is-pending {
  color: #b45309 !important;
  background: #fffbeb !important;
  border-color: rgba(245, 158, 11, 0.28) !important;
}

/* Also force any leftover el-tag success to green */
.meeting-room .room-header :deep(.el-tag--success),
.meeting-room .room-header :deep(.el-tag.el-tag--success) {
  color: #15803d !important;
  background: #dcfce7 !important;
  border-color: rgba(34, 197, 94, 0.28) !important;
}

.meeting-room .stage-timer-group {
  display: inline-flex !important;
  align-items: center !important;
  gap: 6px !important;
}

.meeting-room .countdown-pill.stage-timer {
  display: inline-flex !important;
  align-items: center !important;
  gap: 6px !important;
  min-height: 30px !important;
  padding: 0 12px !important;
  border-radius: 999px !important;
  border: 1px solid rgba(15, 23, 42, 0.1) !important;
  background: #ffffff !important;
  color: #1f2937 !important;
  cursor: pointer !important;
  font: inherit !important;
  transition: border-color 0.15s ease, background 0.15s ease, color 0.15s ease !important;
}

.meeting-room .countdown-pill.stage-timer .countdown-label {
  display: inline !important;
  color: #64748b !important;
  font-size: 11px !important;
  font-weight: 700 !important;
}

.meeting-room .countdown-pill.stage-timer .countdown-time {
  color: #111827 !important;
  font-size: 13px !important;
  font-weight: 800 !important;
  font-variant-numeric: tabular-nums !important;
  min-width: 3.2em !important;
  text-align: right !important;
}

.meeting-room .countdown-pill.stage-timer.is-running {
  border-color: rgba(232, 74, 28, 0.35) !important;
  background: #fff7f2 !important;
}

.meeting-room .countdown-pill.stage-timer.is-running .countdown-label,
.meeting-room .countdown-pill.stage-timer.is-running .countdown-time {
  color: #c2410c !important;
}

.meeting-room .countdown-pill.stage-timer.is-paused {
  border-color: rgba(59, 130, 246, 0.28) !important;
  background: #f0f7ff !important;
}

.meeting-room .countdown-pill.stage-timer:hover {
  border-color: rgba(232, 74, 28, 0.4) !important;
}

.meeting-room .stage-timer-reset {
  min-height: 28px !important;
  padding: 0 10px !important;
  border: 0 !important;
  border-radius: 999px !important;
  background: transparent !important;
  color: #64748b !important;
  font-size: 12px !important;
  font-weight: 700 !important;
  cursor: pointer !important;
  transition: color 0.15s ease, background 0.15s ease !important;
}

.meeting-room .stage-timer-reset:hover:not(:disabled) {
  color: #e84a1c !important;
  background: rgba(232, 74, 28, 0.08) !important;
}

.meeting-room .stage-timer-reset:disabled {
  opacity: 0.35 !important;
  cursor: not-allowed !important;
}

.meeting-room .meeting-title {
  color: #111827 !important;
}

.meeting-room .room-kicker,
.meeting-room .meeting-title-copy small {
  color: #64748b !important;
}

/* Kill any leftover absolute header overlays that cover the rail */
.meeting-room > .room-header {
  position: relative !important;
  inset: auto !important;
}

/* Neutralize older chip styles on plain meta */
.meeting-room .room-header .net-status,
.meeting-room .room-header .participant-num {
  background: transparent !important;
  border: 0 !important;
  box-shadow: none !important;
}

@media (max-width: 768px) {
  .meeting-room .room-header {
    height: auto !important;
    min-height: 48px !important;
    padding: 8px 10px !important;
  }

  .meeting-room .control-bar {
    min-height: 64px !important;
    padding: 8px 10px calc(8px + env(safe-area-inset-bottom, 0px)) !important;
  }

  .meeting-room {
    --room-rail-width: 168px !important;
  }
}
</style>
