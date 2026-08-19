import { getUserToken } from './authStorage.js'
import {
  RealtimeAudioChunkSender,
  buildLiveVideoTiming,
  createMediaClockId
} from './realtimeAudioChunkSender.js'

const LIVE_MEDIA_GATEWAY_ENABLED = ['1', 'true', 'yes', 'on'].includes(
  String(import.meta.env?.VITE_UNIFIED_LIVE_MEDIA_GATEWAY_ENABLED || 'false').toLowerCase()
)

/**
 * MeetingMediaRecorder — 会议音视频录制器
 * 基于 LiveKit 音频/视频轨道 + Web Audio API + MediaRecorder
 *
 * 录制逻辑：
 * 1. 混合本地麦克风 + 所有远端音频轨道 → 音频轨
 * 2. 合并屏幕共享的视频轨道（如果存在） → 视频轨
 * 3. 通过 MediaRecorder 录制为 webm（含音视频）
 * 4. 会议结束后上传到 AI 服务 → 触发融合分析
 */

class MeetingMediaRecorder {
  constructor(options = {}) {
    // Audio 相关
    this.audioContext = null
    this.destNode = null       // 混音目标节点
    this._connectedSources = new Set()

    // Video 相关
    this._videoTrack = null    // 屏幕共享视频轨道

    // 录制器
    this.mediaRecorder = null
    this.chunks = []
    this.lastBlob = null  // 录制完成后的 blob（清除 chunks 前保存）
    this.isRecording = false
    this.startTime = null
    this._meetingId = options.meetingId || null
    this._sessionId = options.sessionId || null
    this._authoritativeSessionId = options.authoritativeSessionId || null
    this._room = null
    this._videoTransform = { videoRotation: 0, videoOrientation: 'unknown', cameraPreset: 'unknown' }
    this._mediaClockId = null
    this._clockIdFactory = options.clockIdFactory || createMediaClockId

    // Realtime ASR
    this.asrSocket = null
    this.asrSourceNode = null
    this.asrProcessorNode = null
    this.asrMuteGainNode = null
    this.asrChunkCount = 0
    this.realtimeAudioSender = null

    // Visual frame capture
    this.frameVideoEl = null
    this.frameCanvas = null
    this.sceneCanvas = null
    this.frameIntervalTimer = null
    this.sceneCheckTimer = null
    this.lastSceneData = null
    this.lastSceneUploadAt = 0

    // 回调
    this.onStatusChange = options.onStatusChange || (() => {})
    this.onUploadComplete = options.onUploadComplete || (() => {})
    this.onUploadProgress = options.onUploadProgress || (() => {})
    this.onError = options.onError || console.error
    this.onRealtimeAsrStatusChange = options.onRealtimeAsrStatusChange || (() => {})
  }

  // ──────────────────────────── Room 绑定 ────────────────────────────

  setRoom(room) {
    this._room = room

    // 监听新轨道订阅
    this._room.on?.('trackSubscribed', (track, publication, participant) => {
      if (!this.isRecording) return

      if (this._isAudioPublication(publication, track)) {
        const key = `${participant?.sid || 'remote'}:${publication?.source || 'audio'}`
        // console.log(`[MediaRecorder] 检测到新的音频轨 ${key}，自动接入`)
        this.addRemoteTrack(track.mediaStreamTrack, key)
      }

      if (this._isVideoPublication(publication, track) && !this._videoTrack) {
        // console.log(`[MediaRecorder] 检测到新的${this._isScreenShareVideoPublication(publication, track) ? '屏幕共享' : '摄像头'}视频轨，自动接入`)
        this.setVideoTrack(track.mediaStreamTrack)
      }
    })
  }

  setSessionId(sessionId) {
    this._sessionId = sessionId || null
  }

  setAuthoritativeSessionId(sessionId) {
    this._authoritativeSessionId = sessionId || null
  }

  setMediaClockId(clockId) {
    this._mediaClockId = clockId ? String(clockId) : null
  }

  getMediaClockId() {
    return this._mediaClockId
  }

  _resolveMediaClockId() {
    return this._mediaClockId || this._clockIdFactory()
  }

  setVideoTransform(meta = {}) {
    this._videoTransform = {
      ...this._videoTransform,
      ...meta,
      videoRotation: Number(meta.videoRotation ?? meta.rotation ?? this._videoTransform.videoRotation ?? 0) || 0
    }
  }

  // ──────────────────────────── Realtime ASR ────────────────────────────

  _buildAsrUrl() {
    if (!this._sessionId) return ''
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const base = `${protocol}://${window.location.host}/api/ai/asr/stream/${encodeURIComponent(this._sessionId)}`
    return LIVE_MEDIA_GATEWAY_ENABLED
      ? `${base}?protocol=media-evidence-v2`
      : base
  }

  _floatToPcm16(float32Data, sourceSampleRate, targetSampleRate = 16000) {
    let samples = float32Data

    if (sourceSampleRate && sourceSampleRate !== targetSampleRate) {
      const ratio = sourceSampleRate / targetSampleRate
      const newLength = Math.round(float32Data.length / ratio)
      const resampled = new Float32Array(newLength)
      for (let i = 0; i < newLength; i++) {
        const sourceIndex = i * ratio
        const index = Math.floor(sourceIndex)
        const nextIndex = Math.min(index + 1, float32Data.length - 1)
        const fraction = sourceIndex - index
        resampled[i] = float32Data[index] * (1 - fraction) + float32Data[nextIndex] * fraction
      }
      samples = resampled
    }

    const pcm = new Int16Array(samples.length)
    for (let i = 0; i < samples.length; i++) {
      const sample = Math.max(-1, Math.min(1, samples[i]))
      pcm[i] = sample < 0 ? sample * 0x8000 : sample * 0x7fff
    }
    return pcm.buffer
  }

  _startRealtimeAsr() {
    if (!this._sessionId || !this.destNode?.stream || !this.audioContext) {
      return
    }

    this._stopRealtimeAsr()

    const url = this._buildAsrUrl()
    if (!url) return

    if (LIVE_MEDIA_GATEWAY_ENABLED) {
      try {
        this.realtimeAudioSender = new RealtimeAudioChunkSender({
          url,
          clockId: this._mediaClockId,
          maxPendingChunks: 30,
          onStatus: (status, detail) => {
            if (status === 'degraded') {
              // 实时证据通道降级不能中断完整 MediaRecorder 录制。
              this.onRealtimeAsrStatusChange('degraded', detail)
            } else {
              this.onRealtimeAsrStatusChange(status, detail)
            }
          }
        })
        this.realtimeAudioSender.start()
        this.asrSourceNode = this.audioContext.createMediaStreamSource(this.destNode.stream)
        this.asrProcessorNode = this.audioContext.createScriptProcessor(4096, 1, 1)
        this.asrMuteGainNode = this.audioContext.createGain()
        this.asrMuteGainNode.gain.value = 0
        this.asrProcessorNode.onaudioprocess = event => {
          const input = event.inputBuffer.getChannelData(0)
          const pcm = this._floatToPcm16(input, this.audioContext.sampleRate, 16000)
          if (pcm.byteLength > 0) {
            this.realtimeAudioSender?.pushPcm(pcm).catch(() => {
              this.onRealtimeAsrStatusChange('degraded')
            })
            this.asrChunkCount += 1
          }
        }
        this.asrSourceNode.connect(this.asrProcessorNode)
        this.asrProcessorNode.connect(this.asrMuteGainNode)
        this.asrMuteGainNode.connect(this.audioContext.destination)
      } catch (e) {
        this.onRealtimeAsrStatusChange('failed')
      }
      return
    }

    try {
      this.asrSocket = new WebSocket(url)
      this.asrSocket.binaryType = 'arraybuffer'
      this.asrChunkCount = 0

      this.asrSocket.onopen = () => {
        try {
          this.asrSourceNode = this.audioContext.createMediaStreamSource(this.destNode.stream)
          this.asrProcessorNode = this.audioContext.createScriptProcessor(4096, 1, 1)
          this.asrMuteGainNode = this.audioContext.createGain()
          this.asrMuteGainNode.gain.value = 0

          this.asrProcessorNode.onaudioprocess = (event) => {
            if (!this.asrSocket || this.asrSocket.readyState !== WebSocket.OPEN) return
            const input = event.inputBuffer.getChannelData(0)
            const pcm = this._floatToPcm16(input, this.audioContext.sampleRate, 16000)
            if (pcm.byteLength > 0) {
              this.asrSocket.send(pcm)
              this.asrChunkCount += 1
            }
          }

          this.asrSourceNode.connect(this.asrProcessorNode)
          this.asrProcessorNode.connect(this.asrMuteGainNode)
          this.asrMuteGainNode.connect(this.audioContext.destination)
          this.onRealtimeAsrStatusChange('streaming')
          // console.log('[MediaRecorder] 实时 ASR 音频流已启动')
        } catch (e) {
          // console.warn('[MediaRecorder] 启动实时 ASR 音频处理失败:', e)
          this.onRealtimeAsrStatusChange('failed')
        }
      }

      this.asrSocket.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data)
          if (payload.type === 'ready') this.onRealtimeAsrStatusChange('ready')
          if (payload.type === 'error') {
            // console.warn('[MediaRecorder] 实时 ASR 服务错误:', payload.message)
            this.onRealtimeAsrStatusChange('failed')
          }
        } catch {}
      }

      this.asrSocket.onerror = (event) => {
        // console.warn('[MediaRecorder] 实时 ASR WebSocket 错误:', event)
        this.onRealtimeAsrStatusChange('failed')
      }

      this.asrSocket.onclose = () => {
        this._disconnectRealtimeAsrNodes()
        this.onRealtimeAsrStatusChange('closed')
      }
    } catch (e) {
      // console.warn('[MediaRecorder] 实时 ASR WebSocket 创建失败:', e)
      this.onRealtimeAsrStatusChange('failed')
    }
  }

  _disconnectRealtimeAsrNodes() {
    try { this.asrProcessorNode?.disconnect() } catch {}
    try { this.asrSourceNode?.disconnect() } catch {}
    try { this.asrMuteGainNode?.disconnect() } catch {}
    if (this.asrProcessorNode) this.asrProcessorNode.onaudioprocess = null
    this.asrProcessorNode = null
    this.asrSourceNode = null
    this.asrMuteGainNode = null
  }

  _stopRealtimeAsr() {
    this._disconnectRealtimeAsrNodes()
    if (this.realtimeAudioSender) {
      const sender = this.realtimeAudioSender
      this.realtimeAudioSender = null
      sender.stop({ waitForAck: true, timeoutMs: 1500 }).catch(() => {
        this.onRealtimeAsrStatusChange('degraded')
      })
    }
    if (this.asrSocket) {
      try {
        if (this.asrSocket.readyState === WebSocket.OPEN) {
          this.asrSocket.send(JSON.stringify({ type: 'stop' }))
        }
      } catch {}
      try { this.asrSocket.close() } catch {}
      this.asrSocket = null
    }
  }

  // ──────────────────────────── Media availability ────────────────────────────

  _publicationValues(collection) {
    if (!collection) return []
    if (typeof collection.values === 'function') return [...collection.values()]
    return Object.values(collection)
  }

  _trackKind(track) {
    return track?.mediaStreamTrack?.kind || track?.kind || ''
  }

  _trackMediaStreamTrack(track) {
    return track?.mediaStreamTrack || track || null
  }

  _isLiveMediaTrack(track, expectedKind) {
    if (!track) return false
    const mediaTrack = this._trackMediaStreamTrack(track)
    if (!mediaTrack || mediaTrack.kind !== expectedKind) return false
    return mediaTrack.readyState === 'live' && mediaTrack.enabled !== false
  }

  _isAudioPublication(pub, fallbackTrack = null) {
    const source = pub?.source
    const track = pub?.track || fallbackTrack
    return this._trackKind(track) === 'audio' || source === 'microphone' || source === 'screen_share_audio'
  }

  _isVideoPublication(pub, fallbackTrack = null) {
    const source = pub?.source
    const track = pub?.track || fallbackTrack
    return this._trackKind(track) === 'video' || source === 'camera' || source === 'screen_share'
  }

  _isScreenShareAudioPublication(pub, fallbackTrack = null) {
    const source = pub?.source
    const track = pub?.track || fallbackTrack
    return source === 'screen_share_audio' || (source === 'screen_share' && this._trackKind(track) === 'audio')
  }

  _isScreenShareVideoPublication(pub, fallbackTrack = null) {
    const source = pub?.source
    const track = pub?.track || fallbackTrack
    return source === 'screen_share' && this._trackKind(track) === 'video'
  }

  _getAvailabilityFromPublications(publications) {
    let hasAudio = false
    let hasVideo = false

    publications.forEach(pub => {
      const track = this._trackMediaStreamTrack(pub?.track)
      if (this._isLiveMediaTrack(track, 'audio')) hasAudio = true
      if (this._isLiveMediaTrack(track, 'video')) hasVideo = true
    })

    return { hasAudio, hasVideo }
  }

  getMediaAvailability() {
    if (!this._room) {
      return {
        hasRoom: false,
        hasAudio: false,
        hasVideo: false,
        audioCount: 0,
        videoCount: 0
      }
    }

    let audioCount = 0
    let videoCount = 0
    const countAvailability = (availability) => {
      if (availability.hasAudio) audioCount += 1
      if (availability.hasVideo) videoCount += 1
    }

    const localPublications = this._publicationValues(this._room.localParticipant?.trackPublications)
    countAvailability(this._getAvailabilityFromPublications(localPublications))

    this._room.remoteParticipants?.forEach?.(participant => {
      const remotePublications = this._publicationValues(participant.trackPublications)
      countAvailability(this._getAvailabilityFromPublications(remotePublications))
    })

    return {
      hasRoom: true,
      hasAudio: audioCount > 0,
      hasVideo: videoCount > 0,
      audioCount,
      videoCount
    }
  }

  // ──────────────────────────── Audio ────────────────────────────

  _initAudioContext() {
    if (this.audioContext) {
      if (this.audioContext.state === 'suspended') {
        this.audioContext.resume()
      }
      return
    }
    this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
      sampleRate: 16000
    })
    this.destNode = this.audioContext.createMediaStreamDestination()
  }

  addLocalTrack(track) {
    if (!track || this._connectedSources.has('local')) return
    this._initAudioContext()
    try {
      const source = this.audioContext.createMediaStreamSource(new MediaStream([track]))
      source.connect(this.destNode)
      this._connectedSources.add('local')
      // console.log('[MediaRecorder] 本地麦克风已加入混音')
    } catch (e) {
      // console.warn('[MediaRecorder] 添加本地轨道失败:', e)
    }
  }

  addRemoteTrack(track, participantSid) {
    if (!track || this._connectedSources.has(participantSid)) return
    this._initAudioContext()
    try {
      const source = this.audioContext.createMediaStreamSource(new MediaStream([track]))
      source.connect(this.destNode)
      this._connectedSources.add(participantSid)
      // console.log(`[MediaRecorder] 远端轨道 ${participantSid} 已加入混音`)
    } catch (e) {
      // console.warn(`[MediaRecorder] 添加远端轨道失败: ${participantSid}`, e)
    }
  }

  removeRemoteTrack(participantSid) {
    this._connectedSources.delete(participantSid)
  }

  // ──────────────────────────── Video ────────────────────────────

  /**
   * 设置屏幕共享视频轨道
   * @param {MediaStreamTrack} videoTrack - getDisplayMedia 获取的视频轨
   */
  setVideoTrack(videoTrack) {
    this._videoTrack = videoTrack
    // console.log('[MediaRecorder] 视频轨道已设置')
    if (this.isRecording && this._sessionId && !this.frameIntervalTimer) {
      this._startVisualFrameCapture()
    }
  }

  // ──────────────────────────── Visual frame capture ────────────────────────────

  _startVisualFrameCapture() {
    if (!this._sessionId || !this._videoTrack) return
    this._stopVisualFrameCapture()

    try {
      this.frameVideoEl = document.createElement('video')
      this.frameVideoEl.muted = true
      this.frameVideoEl.playsInline = true
      this.frameVideoEl.autoplay = true
      this.frameVideoEl.srcObject = new MediaStream([this._videoTrack])
      this.frameCanvas = document.createElement('canvas')
      this.sceneCanvas = document.createElement('canvas')

      const startTimers = () => {
        this._captureVisualFrame('start', 0)
        this.frameIntervalTimer = setInterval(() => {
          this._captureVisualFrame('interval', 0)
        }, 8000)
        this.sceneCheckTimer = setInterval(() => {
          this._checkSceneChange()
        }, 2000)
      }

      this.frameVideoEl.onloadedmetadata = () => {
        this.frameVideoEl.play()
          .then(startTimers)
          .catch((e) => {
            // console.warn('[MediaRecorder] 视频帧采集播放失败:', e)
          })
      }

      this._videoTrack.onended = () => {
        // console.log('[MediaRecorder] 视频轨道结束，停止关键帧采集')
        this._stopVisualFrameCapture()
      }
    } catch (e) {
      // console.warn('[MediaRecorder] 启动视频关键帧采集失败:', e)
    }
  }

  _stopVisualFrameCapture() {
    if (this.frameIntervalTimer) {
      clearInterval(this.frameIntervalTimer)
      this.frameIntervalTimer = null
    }
    if (this.sceneCheckTimer) {
      clearInterval(this.sceneCheckTimer)
      this.sceneCheckTimer = null
    }
    if (this.frameVideoEl) {
      try {
        this.frameVideoEl.pause()
        this.frameVideoEl.srcObject = null
      } catch {}
      this.frameVideoEl = null
    }
    this.frameCanvas = null
    this.sceneCanvas = null
    this.lastSceneData = null
    this.lastSceneUploadAt = 0
  }

  _getVideoDimensions(maxWidth = 960) {
    const width = this.frameVideoEl?.videoWidth || 0
    const height = this.frameVideoEl?.videoHeight || 0
    if (!width || !height) return null
    const rotation = Math.abs(Number(this._videoTransform?.videoRotation || 0)) % 180
    const outputWidth = rotation === 90 ? height : width
    const outputHeight = rotation === 90 ? width : height
    const scale = Math.min(1, maxWidth / outputWidth)
    return {
      width: Math.round(outputWidth * scale),
      height: Math.round(outputHeight * scale)
    }
  }

  _drawVideoFrame(ctx, width, height) {
    const rotation = ((Number(this._videoTransform?.videoRotation || 0) % 360) + 360) % 360
    ctx.save()
    if (rotation === 90) {
      ctx.translate(width, 0)
      ctx.rotate(Math.PI / 2)
      ctx.drawImage(this.frameVideoEl, 0, 0, height, width)
    } else if (rotation === 270) {
      ctx.translate(0, height)
      ctx.rotate(-Math.PI / 2)
      ctx.drawImage(this.frameVideoEl, 0, 0, height, width)
    } else if (rotation === 180) {
      ctx.translate(width, height)
      ctx.rotate(Math.PI)
      ctx.drawImage(this.frameVideoEl, 0, 0, width, height)
    } else {
      ctx.drawImage(this.frameVideoEl, 0, 0, width, height)
    }
    ctx.restore()
  }

  _captureVisualFrame(frameType = 'interval', diffScore = 0) {
    if (!this._sessionId || !this.frameVideoEl || !this.frameCanvas) return
    const dims = this._getVideoDimensions()
    if (!dims) return

    this.frameCanvas.width = dims.width
    this.frameCanvas.height = dims.height
    const ctx = this.frameCanvas.getContext('2d')
    if (!ctx) return
    this._drawVideoFrame(ctx, dims.width, dims.height)

    this.frameCanvas.toBlob((blob) => {
      if (!blob) return
      this._uploadVisualFrame(blob, frameType, diffScore)
    }, 'image/jpeg', 0.72)
  }

  _checkSceneChange() {
    if (!this.frameVideoEl || !this.sceneCanvas) return
    const dims = this._getVideoDimensions(96)
    if (!dims) return

    this.sceneCanvas.width = dims.width
    this.sceneCanvas.height = dims.height
    const ctx = this.sceneCanvas.getContext('2d', { willReadFrequently: true })
    if (!ctx) return
    this._drawVideoFrame(ctx, dims.width, dims.height)
    const current = ctx.getImageData(0, 0, dims.width, dims.height).data

    if (!this.lastSceneData) {
      this.lastSceneData = new Uint8ClampedArray(current)
      return
    }

    let diff = 0
    const step = 16
    let count = 0
    for (let i = 0; i < current.length; i += 4 * step) {
      diff += Math.abs(current[i] - this.lastSceneData[i])
      diff += Math.abs(current[i + 1] - this.lastSceneData[i + 1])
      diff += Math.abs(current[i + 2] - this.lastSceneData[i + 2])
      count += 3
    }
    const diffScore = count ? diff / (count * 255) : 0
    this.lastSceneData = new Uint8ClampedArray(current)

    const now = Date.now()
    if (diffScore >= 0.12 && now - this.lastSceneUploadAt > 5000) {
      this.lastSceneUploadAt = now
      this._captureVisualFrame('scene_change', diffScore)
    }
  }

  async _uploadVisualFrame(blob, frameType, diffScore) {
    try {
      const videoTimeSeconds = Number(this.frameVideoEl?.currentTime)
      const effectiveVideoTime = Number.isFinite(videoTimeSeconds) && videoTimeSeconds >= 0
        ? videoTimeSeconds
        : this.getDuration()
      const observedAudioSample = Number.isInteger(this.realtimeAudioSender?.timelineSamples)
        ? this.realtimeAudioSender.timelineSamples
        : Math.max(0, Math.round(this.getDuration() * 16000))
      const timing = buildLiveVideoTiming({
        clockId: this._mediaClockId,
        videoTimeSeconds: effectiveVideoTime,
        observedAudioSample
      })
      const formData = new FormData()
      formData.append('frame', blob, `${frameType}_${Date.now()}.jpg`)
      formData.append('timestamp', String(this.getDuration()))
      formData.append('clock_id', timing.clockId)
      formData.append('raw_pts', String(timing.rawPts))
      formData.append('pts_timebase_num', String(timing.ptsTimebaseNum))
      formData.append('pts_timebase_den', String(timing.ptsTimebaseDen))
      formData.append('observed_audio_sample', String(timing.observedAudioSample))
      formData.append('frame_type', frameType)
      formData.append('diff_score', String(diffScore || 0))
      formData.append('camera_preset', this._videoTransform?.cameraPreset || 'unknown')
      formData.append('camera_orientation', this._videoTransform?.videoOrientation || 'unknown')
      formData.append('camera_rotation', String(this._videoTransform?.videoRotation || 0))

      const res = await fetch(`/api/ai/session/${encodeURIComponent(this._sessionId)}/visual-frame`, {
        method: 'POST',
        body: formData
      })
      if (!res.ok) {
        // console.warn('[MediaRecorder] 视频关键帧上传失败:', res.status)
      }
    } catch (e) {
      // console.warn('[MediaRecorder] 视频关键帧上传异常:', e)
    }
  }

  /**
   * 扫描已有轨道（音频+视频）
   */
  _scanExistingTracks() {
    if (!this._room) {
      // console.warn('[MediaRecorder] Room 未设置，无法扫描')
      return
    }

    try {
      // 本地麦克风
      const localTrackPubs = this._publicationValues(this._room.localParticipant?.trackPublications)

      const localAudioPubs = localTrackPubs.filter(pub => this._isAudioPublication(pub))
      localAudioPubs.forEach((pub, index) => {
        const track = this._trackMediaStreamTrack(pub.track)
        if (track) {
          const key = pub.source === 'microphone' ? 'local' : `local:${pub.source || 'audio'}:${index}`
          this.addRemoteTrack(track, key)
        }
      })

      if (localAudioPubs.length === 0) {
        const localMic = this._room.localParticipant?.getTrackPublication('microphone')
        if (localMic?.track?.mediaStreamTrack) {
          this.addLocalTrack(localMic.track.mediaStreamTrack)
        }
      }

      // 本地屏幕共享视频（优先）或摄像头视频
      const localScreenVideo = localTrackPubs.find(p => this._isScreenShareVideoPublication(p))
      if (localScreenVideo?.track?.mediaStreamTrack) {
        this.setVideoTrack(localScreenVideo.track.mediaStreamTrack)
      } else {
        const localCamVideo = localTrackPubs.find(p => p.source === 'camera' && this._isVideoPublication(p))
        if (localCamVideo?.track?.mediaStreamTrack) {
          this.setVideoTrack(localCamVideo.track.mediaStreamTrack)
        }
      }

      // 远端参与者音频 + 屏幕共享视频
      this._room.remoteParticipants?.forEach(p => {
        const remoteTrackPubs = this._publicationValues(p.trackPublications)

        remoteTrackPubs
          .filter(pub => this._isAudioPublication(pub))
          .forEach((pub, index) => {
            const track = this._trackMediaStreamTrack(pub.track)
            if (!track) return
            const suffix = this._isScreenShareAudioPublication(pub) ? ':screen_audio' : `:${pub.source || 'audio'}:${index}`
            this.addRemoteTrack(track, p.sid + suffix)
          })

        // 远端屏幕共享视频（用于 AI 分析，优先）或摄像头视频
        const remoteScreenVideo = remoteTrackPubs
          .find(pub => this._isScreenShareVideoPublication(pub))
        if (remoteScreenVideo?.track?.mediaStreamTrack) {
          this.setVideoTrack(remoteScreenVideo.track.mediaStreamTrack)
        } else if (!this._videoTrack) {
          const remoteCamVideo = remoteTrackPubs
            .find(pub => pub.source === 'camera' && this._isVideoPublication(pub))
          if (remoteCamVideo?.track?.mediaStreamTrack) {
            this.setVideoTrack(remoteCamVideo.track.mediaStreamTrack)
          }
        }
      })

      // console.log(`[MediaRecorder] 扫描完成: ${this._connectedSources.size} 个音频源, 视频=${!!this._videoTrack}`)
      if (this._connectedSources.size === 0) {
        const debugPubs = []
        localTrackPubs.forEach(pub => {
          debugPubs.push({ owner: 'local', source: pub.source, kind: this._trackKind(pub.track), subscribed: pub.isSubscribed })
        })
        this._room.remoteParticipants?.forEach(p => {
          this._publicationValues(p.trackPublications).forEach(pub => {
            debugPubs.push({ owner: p.sid, source: pub.source, kind: this._trackKind(pub.track), subscribed: pub.isSubscribed })
          })
        })
        // console.warn('[MediaRecorder] 未找到可混音音频轨，当前 publications:', debugPubs)
      }
    } catch (e) {
      // console.warn('[MediaRecorder] 扫描失败:', e)
    }
  }

  // ──────────────────────────── 录制 ────────────────────────────

  /**
   * 合并音频和视频轨道为一个 MediaStream
   */
  _buildCombinedStream() {
    if (!this.destNode || !this.destNode.stream) {
      throw new Error('混音节点未初始化')
    }

    const tracks = []

    // 音频轨（混音输出）
    tracks.push(...this.destNode.stream.getAudioTracks())

    // 视频轨（如果有）
    if (this._videoTrack) {
      tracks.push(this._videoTrack)
      // console.log('[MediaRecorder] 合并音视频轨道')
    } else {
      // console.log('[MediaRecorder] 仅音频轨道（无视频）')
    }

    return new MediaStream(tracks)
  }

  async startRecording() {
    if (this.isRecording) {
      // console.warn('[MediaRecorder] 已在录制中')
      return false
    }

    // One immutable clock identity is shared by realtime PCM, visual frames and
    // the final recording upload. Socket reconnects reuse this same value.
    this._mediaClockId = this._resolveMediaClockId()

    this._initAudioContext()

    if (this.audioContext.state === 'suspended') {
      // console.log('[MediaRecorder] AudioContext suspended, resume...')
      await this.audioContext.resume()
    }
    // console.log(`[MediaRecorder] AudioContext: ${this.audioContext.state}`)

    // 扫描已有轨道
    this._scanExistingTracks()

    if (this._connectedSources.size === 0) {
      this.onError('开启 AI 评分前需要会议中存在有效音频')
      return false
    }

    if (!this._videoTrack) {
      this.onError('开启 AI 评分前需要会议中存在摄像头或屏幕共享画面')
      return false
    }

    // 构建合并轨道
    const combinedStream = this._buildCombinedStream()

    // 检查支持的 MIME 类型
    const mimeType = this._getSupportedMimeType()
    if (!mimeType) {
      this.onError('当前浏览器不支持录制')
      return false
    }

    this.chunks = []
    this.mediaRecorder = new MediaRecorder(combinedStream, {
      mimeType,
      videoBitsPerSecond: this._videoTrack ? 1000000 : undefined,
      audioBitsPerSecond: 128000
    })

    this.mediaRecorder.ondataavailable = (event) => {
      if (event.data && event.data.size > 0) {
        this.chunks.push(event.data)
      }
    }

    this.mediaRecorder.onstop = () => {
      this._onRecordingStop()
    }

    this.mediaRecorder.onerror = (event) => {
      this.onError(`录制错误: ${event.error?.message || '未知错误'}`)
    }

    this.mediaRecorder.start(1000)
    this.isRecording = true
    this.startTime = Date.now()
    this._startRealtimeAsr()
    this._startVisualFrameCapture()
    this.onStatusChange('recording')
    // console.log('[MediaRecorder] 录制已启动（' + (this._videoTrack ? '音视频' : '音频') + '）')
    return true
  }

  stopRecording() {
    if (!this.isRecording || !this.mediaRecorder) return
    this._stopRealtimeAsr()
    this._captureVisualFrame('stop', 0)
    this._stopVisualFrameCapture()
    this.mediaRecorder.stop()
    this.isRecording = false
    this.onStatusChange('stopping')
    // console.log('[MediaRecorder] 录制已停止')
  }

  async _onRecordingStop() {
    const elapsed = this.startTime ? (Date.now() - this.startTime) / 1000 : 0
    // console.log(`[MediaRecorder] 停止: chunks=${this.chunks.length}, 时长=${elapsed.toFixed(1)}s`)

    if (this.chunks.length === 0) {
      this.onError('录制数据为空')
      this.onStatusChange('idle')
      return
    }

    const blob = new Blob(this.chunks, { type: this._getSupportedMimeType() })
    this.lastBlob = blob  // 保存 blob 引用，供外部获取
    // console.log(`[MediaRecorder] 录制完成: ${(blob.size / 1024 / 1024).toFixed(2)} MB, ${elapsed.toFixed(1)}s, hasVideo=${!!this._videoTrack}`)

    this.onStatusChange('uploading')

    const formData = new FormData()
    const ext = this._videoTrack ? 'webm' : 'webm'
    formData.append('audio', blob, `meeting_${Date.now()}.${ext}`)
    formData.append('meeting_id', this._meetingId || 'unknown')
    if (this._sessionId) {
      formData.append('session_id', this._sessionId)
    }
    formData.append('audio_source_count', String(this._connectedSources.size))
    formData.append('clock_id', this._mediaClockId || '')
    formData.append('media_clock_master', 'MEDIA_PTS')
    formData.append('has_video', String(!!this._videoTrack))
    formData.append('camera_preset', this._videoTransform?.cameraPreset || 'unknown')
    formData.append('camera_orientation', this._videoTransform?.videoOrientation || 'unknown')
    formData.append('camera_raw_orientation', this._videoTransform?.rawOrientation || 'unknown')
    formData.append('camera_rotation', String(this._videoTransform?.videoRotation || 0))

    // 检测屏幕共享
    let hasScreenShare = !!this._videoTrack
    if (!hasScreenShare) {
      try {
        const participants = this._room?.remoteParticipants
        if (participants) {
          for (const p of participants.values?.() || Object.values(participants)) {
            for (const pub of (p.trackPublications?.values?.() || Object.values(p.trackPublications || {}))) {
              if (pub.source === 'screen_share' && pub.isSubscribed) {
                hasScreenShare = true
                break
              }
            }
            if (hasScreenShare) break
          }
        }
      } catch (e) {}
    }
    formData.append('has_screen_share', String(hasScreenShare))

    try {
      const token = getUserToken()
      const result = await this._uploadWithProgress(formData, token, blob.size)
      // console.log('[MediaRecorder] 上传成功:', result)
      this.onUploadComplete(result)
      this.onStatusChange('uploaded')
    } catch (error) {
      // console.error('[MediaRecorder] 上传失败:', error)
      this.onError(`上传失败: ${error.message}`)
      this.onStatusChange('upload_failed')
      this._saveLocally(blob)
    }
  }

  async _uploadWithProgress(formData, token, fileSize = 0) {
    const controller = new AbortController()
    // 按文件大小动态计算超时：60秒基础 + 每10MB额外30秒
    const fileSizeMB = fileSize / (1024 * 1024)
    const timeoutMs = Math.max(120000, 60000 + Math.ceil(fileSizeMB / 10) * 30000)
    const timeout = setTimeout(() => controller.abort(), timeoutMs)
    // console.log(`[MediaRecorder] 上传超时设置: ${(timeoutMs/1000).toFixed(0)}s, 文件大小: ${fileSizeMB.toFixed(1)}MB`)

    try {
      const headers = {}
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      }
      const uploadUrl = this._authoritativeSessionId
        ? `/api/ai-score/sessions/${encodeURIComponent(this._authoritativeSessionId)}/meeting-media`
        : '/api/ai/upload-audio'
      const res = await fetch(uploadUrl, {
        method: 'POST',
        body: formData,
        signal: controller.signal,
        headers
      })
      if (!res.ok) {
        const text = await res.text()
        throw new Error(`HTTP ${res.status}: ${text}`)
      }
      if (this.onUploadProgress) this.onUploadProgress(100, 0, 0)
      return await res.json()
    } finally {
      clearTimeout(timeout)
    }
  }

  _getSupportedMimeType() {
    // 优先支持视频+音频的格式
    const videoTypes = [
      'video/webm;codecs=vp8,opus',
      'video/webm;codecs=vp9,opus',
      'video/webm',
    ]
    // 如果有视频轨，优先选视频格式
    if (this._videoTrack) {
      for (const t of videoTypes) {
        if (MediaRecorder.isTypeSupported(t)) return t
      }
    }
    // 纯音频回退
    const audioTypes = [
      'audio/webm;codecs=opus',
      'audio/webm',
      'audio/ogg;codecs=opus',
      'audio/mp4',
    ]
    for (const t of audioTypes) {
      if (MediaRecorder.isTypeSupported(t)) return t
    }
    return ''
  }

  _saveLocally(blob) {
    try {
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `meeting_recording_${Date.now()}.webm`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (e) {
      // console.error('[MediaRecorder] 本地保存失败:', e)
    }
  }

  getDuration() {
    if (!this.startTime) return 0
    return (Date.now() - this.startTime) / 1000
  }

  /**
   * 获取录制完成后的 blob（在清除 chunks 前保存的引用）
   * @returns {Blob|null}
   */
  getRecordedBlob() {
    return this.lastBlob
  }

  destroy() {
    if (this.isRecording) this.stopRecording()
    this._stopRealtimeAsr()
    this._stopVisualFrameCapture()
    if (this.audioContext) {
      this.audioContext.close().catch(() => {})
      this.audioContext = null
    }
    if (this._videoTrack) {
      this._videoTrack.stop()
      this._videoTrack = null
    }
    this.destNode = null
    this._connectedSources.clear()
    this.chunks = []
  }
}

export default MeetingMediaRecorder
