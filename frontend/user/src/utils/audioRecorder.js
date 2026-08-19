import { getUserToken } from './authStorage'

/**
 * MeetingAudioRecorder — 会议音频录制器
 * 基于 LiveKit 音频轨道 + Web Audio API + MediaRecorder
 *
 * 录制逻辑：
 * 1. 混合本地麦克风 + 所有远端音频轨道
 * 2. 通过 MediaRecorder 录制为 webm/ogg
 * 3. 会议结束后上传到后端 → 触发 AI 评分
 */

class MeetingAudioRecorder {
  constructor(options = {}) {
    this.audioContext = null
    this.destNode = null       // 混音目标节点
    this.mediaRecorder = null
    this.audioChunks = []
    this.isRecording = false
    this.onStatusChange = options.onStatusChange || (() => {})
    this.onUploadComplete = options.onUploadComplete || (() => {})
    this.onUploadProgress = options.onUploadProgress || (() => {})
    this.onError = options.onError || console.error
    this.startTime = null
    this._meetingId = options.meetingId || null
    this._room = null
    this._connectedSources = new Set()
  }

  /**
   * 设置 LiveKit Room 引用（用于录制开始时扫描已有轨道）
   */
  setRoom(room) {
    this._room = room
  }

  /**
   * 录制开始时主动扫描已有音频轨道
   */
  _scanExistingTracks() {
    if (!this._room) {
      // console.warn('[AudioRecorder] Room 未设置，无法扫描已有轨道')
      return
    }

    try {
      // 扫描本地麦克风轨道
      const localMic = this._room.localParticipant?.getTrackPublication('microphone')
      if (localMic?.track?.mediaStreamTrack) {
        this.addLocalTrack(localMic.track.mediaStreamTrack)
      }

      // 扫描本地屏幕共享音频（部分系统可捕获系统音频）
      const localScreen = this._room.localParticipant?.getTrackPublication('screen_share_audio')
        || this._room.localParticipant?.trackPublications?.values
          ? [...(this._room.localParticipant.trackPublications || new Map()).values()]
              .find(p => p.source === 'screen_share' && p.track?.kind === 'audio')
          : null
      if (localScreen?.track?.mediaStreamTrack) {
        this.addLocalTrack(localScreen.track.mediaStreamTrack)
      }

      // 扫描所有远端参与者（麦克风 + 屏幕共享音频）
      this._room.remoteParticipants?.forEach(p => {
        // 远端麦克风
        const micPub = p.getTrackPublication('microphone')
        if (micPub?.track?.mediaStreamTrack) {
          this.addRemoteTrack(micPub.track.mediaStreamTrack, p.sid)
        }
        // 远端屏幕共享音频
        const screenPub = [...(p.trackPublications || new Map()).values()]
          .find(pub => pub.source === 'screen_share' && pub.track?.kind === 'audio')
        if (screenPub?.track?.mediaStreamTrack) {
          this.addRemoteTrack(screenPub.track.mediaStreamTrack, p.sid + ':screen_audio')
        }
      })

      // console.log(`[AudioRecorder] 扫描完成，已连接源: ${this._connectedSources.size} 个`)
    } catch (e) {
      // console.warn('[AudioRecorder] 扫描已有轨道失败:', e)
    }
  }

  /**
   * 初始化 Web Audio 混音环境
   */
  _initAudioContext() {
    if (this.audioContext) {
      // 浏览器自动播放策略：AudioContext 可能被 suspended，需要 resume
      if (this.audioContext.state === 'suspended') {
        this.audioContext.resume()
      }
      return
    }
    this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
      sampleRate: 16000  // 与 ASR 要求一致
    })
    // 创建混音目标节点
    this.destNode = this.audioContext.createMediaStreamDestination()
  }

  /**
   * 添加本地麦克风轨道到混音
   * @param {MediaStreamTrack} track - LiveKit local audio track 的 mediaStreamTrack
   */
  addLocalTrack(track) {
    if (!track || this._connectedSources.has('local')) return
    this._initAudioContext()

    try {
      const source = this.audioContext.createMediaStreamSource(
        new MediaStream([track])
      )
      source.connect(this.destNode)
      this._connectedSources.add('local')
      // console.log('[AudioRecorder] 本地麦克风已加入混音')
    } catch (e) {
      // console.warn('[AudioRecorder] 添加本地轨道失败:', e)
    }
  }

  /**
   * 添加远端音频轨道到混音
   * @param {MediaStreamTrack} track - LiveKit remote audio track 的 mediaStreamTrack
   * @param {string} participantSid - 参与者 SID
   */
  addRemoteTrack(track, participantSid) {
    if (!track || this._connectedSources.has(participantSid)) return
    this._initAudioContext()

    try {
      const source = this.audioContext.createMediaStreamSource(
        new MediaStream([track])
      )
      source.connect(this.destNode)
      this._connectedSources.add(participantSid)
      // console.log(`[AudioRecorder] 远端轨道 ${participantSid} 已加入混音`)
    } catch (e) {
      // console.warn(`[AudioRecorder] 添加远端轨道失败: ${participantSid}`, e)
    }
  }

  /**
   * 移除远端音频轨道
   */
  removeRemoteTrack(participantSid) {
    this._connectedSources.delete(participantSid)
    // 注：Web Audio API 的 source 节点无法直接断开单个输入
    // 但混音器会自动处理（轨道停止后自然无声）
  }

  /**
   * 开始录制
   */
  async startRecording() {
    if (this.isRecording) {
      // console.warn('[AudioRecorder] 已在录制中')
      return false
    }

    this._initAudioContext()

    // 确保 AudioContext 处于 running 状态（浏览器自动播放策略）
    if (this.audioContext.state === 'suspended') {
      // console.log('[AudioRecorder] AudioContext 被 suspended，尝试 resume...')
      await this.audioContext.resume()
    }
    // console.log(`[AudioRecorder] AudioContext 状态: ${this.audioContext.state}, 采样率: ${this.audioContext.sampleRate}`)

    // 尝试通过已有的 LiveKit room 扫描音频轨道
    this._scanExistingTracks()

    if (!this.destNode || !this.destNode.stream) {
      this.onError('混音节点未初始化，请确保有音频轨道')
      return false
    }

    const mimeType = this._getSupportedMimeType()
    if (!mimeType) {
      this.onError('当前浏览器不支持音频录制')
      return false
    }

    this.audioChunks = []
    this.mediaRecorder = new MediaRecorder(this.destNode.stream, {
      mimeType,
      audioBitsPerSecond: 128000
    })

    this.mediaRecorder.ondataavailable = (event) => {
      if (event.data && event.data.size > 0) {
        this.audioChunks.push(event.data)
      }
    }

    this.mediaRecorder.onstop = () => {
      this._onRecordingStop()
    }

    this.mediaRecorder.onerror = (event) => {
      this.onError(`录制错误: ${event.error?.message || '未知错误'}`)
    }

    // 每秒收集一次数据
    this.mediaRecorder.start(1000)
    this.isRecording = true
    this.startTime = Date.now()
    this.onStatusChange('recording')
    // console.log('[AudioRecorder] 录制已启动')
    return true
  }

  /**
   * 停止录制并上传
   */
  stopRecording() {
    if (!this.isRecording || !this.mediaRecorder) return

    this.mediaRecorder.stop()
    this.isRecording = false
    this.onStatusChange('stopping')
    // console.log('[AudioRecorder] 录制已停止')
  }

  /**
   * 录制结束 → 打包上传
   */
  async _onRecordingStop() {
    const elapsed = this.startTime ? (Date.now() - this.startTime) / 1000 : 0
    // console.log(`[AudioRecorder] 停止时状态: chunks=${this.audioChunks.length}, 连接源=${this._connectedSources.size}, 时长=${elapsed.toFixed(1)}s`)

    if (this.audioChunks.length === 0) {
      const sourceCount = this._connectedSources.size
      if (sourceCount === 0) {
        this.onError('录制数据为空：未检测到任何音频轨道（请确认麦克风已开启或有远端参与者）')
      } else {
        this.onError(`录制数据为空：已连接 ${sourceCount} 个音频源但未采集到数据，可能是录制时间过短`)
      }
      this.onStatusChange('idle')
      return
    }

    const blob = new Blob(this.audioChunks, {
      type: this._getSupportedMimeType()
    })

    const durationSec = this.startTime ? (Date.now() - this.startTime) / 1000 : 0
    // console.log(`[AudioRecorder] 录制完成: ${(blob.size / 1024 / 1024).toFixed(2)} MB, ${durationSec.toFixed(1)}s`)

    this.onStatusChange('uploading')

    // 构建表单数据
    const formData = new FormData()
    formData.append('audio', blob, `meeting_${Date.now()}.webm`)
    formData.append('meeting_id', this._meetingId || 'unknown')
    formData.append('audio_source_count', String(this._connectedSources.size))

    // 检测是否有屏幕共享轨道
    let hasScreenShare = false
    try {
      const participants = this._room?.remoteParticipants
      if (participants) {
        // remoteParticipants 可能是 Map 或数组
        const iter = participants instanceof Map ? participants.values() : Object.values(participants)
        for (const p of iter) {
          const pubs = p.trackPublications instanceof Map
            ? p.trackPublications.values()
            : Object.values(p.trackPublications || {})
          for (const pub of pubs) {
            if (pub.source === 'screen_share' && pub.isSubscribed) {
              hasScreenShare = true
              break
            }
          }
          if (hasScreenShare) break
        }
      }
    } catch (e) {
      // console.warn('[AudioRecorder] 检测屏幕共享失败:', e)
    }
    formData.append('has_screen_share', String(hasScreenShare))

    try {
      const token = getUserToken()
      const result = await this._uploadWithProgress(formData, token)
      // console.log('[AudioRecorder] 上传成功:', result)
      this.onUploadComplete(result)
      this.onStatusChange('uploaded')

    } catch (error) {
      // console.error('[AudioRecorder] 上传失败:', error)
      this.onError(`音频上传失败: ${error.message}`)
      this.onStatusChange('upload_failed')

      // 降级：保存到本地
      this._saveLocally(blob)
    }
  }

  /**
   * 带进度追踪的上传
   * 优先用 fetch（更可靠），降级到 XMLHttpRequest
   */
  async _uploadWithProgress(formData, token) {
    try {
      // 方式一：fetch + ReadableStream 进度追踪
      return await this._uploadViaFetch(formData)
    } catch (e) {
      // console.warn('[AudioRecorder] fetch 上传失败，降级到 XHR:', e)
      // 方式二：XMLHttpRequest
      return await this._uploadViaXHR(formData)
    }
  }

  /**
   * fetch 方式上传（无进度追踪，但更稳定）
   */
  async _uploadViaFetch(formData) {
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), 60000)

    try {
      const res = await fetch('/api/ai/upload-audio', {
        method: 'POST',
        body: formData,
        signal: controller.signal
      })

      if (!res.ok) {
        throw new Error(`上传失败: ${res.status}`)
      }

      // 模拟进度：上传阶段显示 50-100%
      if (this.onUploadProgress) {
        this.onUploadProgress(50, 0, 0)
      }

      const result = await res.json()

      if (this.onUploadProgress) {
        this.onUploadProgress(100, 0, 0)
      }

      return result
    } finally {
      clearTimeout(timeout)
    }
  }

  /**
   * XMLHttpRequest 方式上传（带进度追踪）
   */
  _uploadViaXHR(formData) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest()
      xhr.timeout = 60000

      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable && this.onUploadProgress) {
          const percent = Math.round((e.loaded / e.total) * 100)
          this.onUploadProgress(percent, e.loaded, e.total)
        }
      })

      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            resolve(JSON.parse(xhr.responseText))
          } catch {
            reject(new Error('响应解析失败'))
          }
        } else {
          reject(new Error(`上传失败: ${xhr.status}`))
        }
      })

      xhr.addEventListener('error', () => reject(new Error('网络错误')))
      xhr.addEventListener('abort', () => reject(new Error('上传已取消')))
      xhr.addEventListener('timeout', () => reject(new Error('上传超时')))

      xhr.open('POST', '/api/ai/upload-audio')
      xhr.send(formData)
    })
  }

  /**
   * 检测浏览器支持的音频编码
   */
  _getSupportedMimeType() {
    const types = [
      'audio/webm;codecs=opus',
      'audio/webm',
      'audio/ogg;codecs=opus',
      'audio/mp4',
    ]
    return types.find(t => MediaRecorder.isTypeSupported(t)) || ''
  }

  /**
   * 降级：保存到用户本地
   */
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
      // console.log('[AudioRecorder] 已降级保存到本地')
    } catch (e) {
      // console.error('[AudioRecorder] 本地保存也失败了:', e)
    }
  }

  /**
   * 获取录制时长（秒）
   */
  getDuration() {
    if (!this.startTime) return 0
    return (Date.now() - this.startTime) / 1000
  }

  /**
   * 清理资源
   */
  destroy() {
    if (this.isRecording) {
      this.stopRecording()
    }
    if (this.audioContext) {
      this.audioContext.close().catch(() => {})
      this.audioContext = null
    }
    this.destNode = null
    this._connectedSources.clear()
    this.audioChunks = []
  }
}

export default MeetingAudioRecorder
