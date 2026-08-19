const PROTOCOL = 'media-evidence-v2'
const SAMPLE_RATE = 16000
const CHANNELS = 1
const BYTES_PER_SAMPLE = 2


export function createMediaClockId() {
  if (typeof globalThis.crypto?.randomUUID === 'function') {
    return globalThis.crypto.randomUUID()
  }
  const bytes = new Uint8Array(16)
  globalThis.crypto?.getRandomValues?.(bytes)
  const entropy = [...bytes].map(value => value.toString(16).padStart(2, '0')).join('')
  return `media-clock-${Date.now().toString(36)}-${entropy || 'fallback'}`
}


export function buildLiveVideoTiming({
  clockId,
  videoTimeSeconds,
  observedAudioSample
}) {
  const seconds = Number(videoTimeSeconds)
  const audioSample = Number(observedAudioSample)
  if (!clockId || !Number.isFinite(seconds) || seconds < 0) {
    throw new TypeError('valid clockId and non-negative video time are required')
  }
  if (!Number.isInteger(audioSample) || audioSample < 0) {
    throw new TypeError('observed audio sample must be a non-negative integer')
  }
  return {
    clockId: String(clockId),
    rawPts: Math.round(seconds * 1000),
    ptsTimebaseNum: 1,
    ptsTimebaseDen: 1000,
    observedAudioSample: audioSample
  }
}


async function sha256Hex(bytes) {
  const digest = await globalThis.crypto.subtle.digest(
    'SHA-256',
    bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength)
  )
  return `sha256:${[...new Uint8Array(digest)]
    .map(value => value.toString(16).padStart(2, '0'))
    .join('')}`
}


function asBytes(value) {
  if (value instanceof Uint8Array) return value
  if (value instanceof ArrayBuffer) return new Uint8Array(value)
  if (ArrayBuffer.isView(value)) {
    return new Uint8Array(value.buffer, value.byteOffset, value.byteLength)
  }
  throw new TypeError('PCM payload must be an ArrayBuffer or typed array')
}


function joinBytes(left, right) {
  if (!left.byteLength) return right.slice()
  const joined = new Uint8Array(left.byteLength + right.byteLength)
  joined.set(left, 0)
  joined.set(right, left.byteLength)
  return joined
}


export class RealtimeAudioChunkSender {
  constructor(options = {}) {
    this.url = options.url || ''
    this.socketFactory = options.socketFactory || (url => new WebSocket(url))
    this.reconnectScheduler = options.reconnectScheduler
      || ((callback, delay) => setTimeout(callback, delay))
    this.onStatus = options.onStatus || (() => {})
    this.maxPendingChunks = Math.max(1, Number(options.maxPendingChunks || 30))
    this.chunkDurationMs = Math.max(100, Number(options.chunkDurationMs || 1000))
    this.chunkBytes = Math.round(
      SAMPLE_RATE * BYTES_PER_SAMPLE * (this.chunkDurationMs / 1000)
    )
    this.reconnectDelays = options.reconnectDelays || [250, 500, 1000, 2000, 5000]
    this.clockId = String(options.clockId || createMediaClockId())
    this.masterSource = 'AUDIO_SAMPLE_CLOCK'

    this.socket = null
    this.ready = false
    this.stopping = false
    this.stopped = false
    this.reconnectAttempt = 0
    this.sequence = 0
    this.timelineBytes = 0
    this.timelineSamples = 0
    this.buffer = new Uint8Array(0)
    this.pending = new Map()
    this.droppedSequences = []
    this.work = Promise.resolve(true)
  }

  get pendingCount() {
    return this.pending.size
  }

  get pendingSequences() {
    return [...this.pending.keys()].sort((a, b) => a - b)
  }

  start() {
    if (this.socket || this.stopping || this.stopped) return
    this._connect()
  }

  _connect() {
    const socket = this.socketFactory(this.url)
    this.socket = socket
    this.ready = false

    socket.onopen = () => {
      socket.send(JSON.stringify({
        type: 'hello',
        protocol: PROTOCOL,
        sampleRate: SAMPLE_RATE,
        channels: CHANNELS,
        clockId: this.clockId,
        masterSource: this.masterSource,
        resumeFromSequence: this.pendingSequences[0] ?? this.sequence
      }))
      this.onStatus('connecting', { attempt: this.reconnectAttempt })
    }

    socket.onmessage = event => {
      let message
      try {
        message = JSON.parse(event.data)
      } catch {
        this.onStatus('degraded', { code: 'INVALID_SERVER_MESSAGE' })
        return
      }
      if (message.type === 'ready') {
        this.work = this.work.then(() => this._handleReady(message))
      } else if (message.type === 'ack') {
        this.pending.delete(Number(message.sequence))
        this.onStatus(
          message.providerStatus === 'degraded' ? 'degraded' : 'streaming',
          message
        )
      } else if (message.type === 'error') {
        this.onStatus('degraded', message)
      } else if (message.type === 'finalized') {
        this.stopped = true
        this.onStatus('finalized', message.summary)
      }
    }

    socket.onerror = () => {
      this.onStatus('degraded', { code: 'LIVE_SOCKET_ERROR' })
    }

    socket.onclose = () => {
      if (this.socket === socket) this.socket = null
      this.ready = false
      if (this.stopping || this.stopped) {
        this.onStatus(this.stopped ? 'finalized' : 'closed')
        return
      }
      const delay = this.reconnectDelays[
        Math.min(this.reconnectAttempt, this.reconnectDelays.length - 1)
      ]
      this.reconnectAttempt += 1
      this.onStatus('reconnecting', { attempt: this.reconnectAttempt, delay })
      this.reconnectScheduler(() => this._connect(), delay)
    }
  }

  async _handleReady(message) {
    if (message.protocol !== PROTOCOL) {
      this.onStatus('degraded', { code: 'PROTOCOL_MISMATCH' })
      return false
    }
    if (message.clockId && message.clockId !== this.clockId) {
      this.onStatus('degraded', {
        code: 'CLOCK_ID_MISMATCH',
        expectedClockId: this.clockId,
        actualClockId: message.clockId
      })
      return false
    }
    const nextSequence = Math.max(0, Number(message.nextSequence || 0))
    for (const sequence of this.pendingSequences) {
      if (sequence < nextSequence) this.pending.delete(sequence)
    }
    this.ready = true
    this.reconnectAttempt = 0
    for (const sequence of this.pendingSequences) {
      if (sequence >= nextSequence) this._sendEntry(this.pending.get(sequence))
    }
    this.onStatus('ready', {
      nextSequence,
      nextSample: Number(message.nextSample ?? this.timelineSamples),
      clockId: this.clockId
    })
    return true
  }

  _sendEntry(entry) {
    if (!entry || !this.ready || !this.socket || this.socket.readyState !== 1) {
      return false
    }
    this.socket.send(JSON.stringify(entry.metadata))
    this.socket.send(
      entry.payload.buffer.slice(
        entry.payload.byteOffset,
        entry.payload.byteOffset + entry.payload.byteLength
      )
    )
    return true
  }

  async _queueChunk(bytes) {
    const payload = bytes.slice()
    if (payload.byteLength % BYTES_PER_SAMPLE !== 0) {
      throw new TypeError('PCM16 payload byte length must be even')
    }
    const sequence = this.sequence
    this.sequence += 1
    const startSample = this.timelineSamples
    const sampleCount = payload.byteLength / BYTES_PER_SAMPLE
    const startMs = Math.round((startSample / SAMPLE_RATE) * 1000)
    this.timelineBytes += payload.byteLength
    this.timelineSamples += sampleCount
    const endMs = Math.round((this.timelineSamples / SAMPLE_RATE) * 1000)

    if (this.pending.size >= this.maxPendingChunks) {
      this.droppedSequences.push(sequence)
      this.onStatus('degraded', {
        code: 'LIVE_BUFFER_LIMIT_REACHED',
        droppedSequence: sequence,
        maxPendingChunks: this.maxPendingChunks
      })
      return false
    }

    const metadata = {
      type: 'audio_chunk',
      sequence,
      clockId: this.clockId,
      startSample,
      sampleCount,
      startMs,
      endMs,
      payloadHash: await sha256Hex(payload)
    }
    const entry = { metadata, payload }
    this.pending.set(sequence, entry)
    this._sendEntry(entry)
    return true
  }

  pushPcm(value) {
    const incoming = asBytes(value)
    this.work = this.work.then(async () => {
      this.buffer = joinBytes(this.buffer, incoming)
      let accepted = true
      while (this.buffer.byteLength >= this.chunkBytes) {
        const chunk = this.buffer.slice(0, this.chunkBytes)
        this.buffer = this.buffer.slice(this.chunkBytes)
        if (!await this._queueChunk(chunk)) accepted = false
      }
      return accepted
    })
    return this.work
  }

  async flush() {
    await this.work
    if (!this.buffer.byteLength) return true
    const partial = this.buffer
    this.buffer = new Uint8Array(0)
    return this._queueChunk(partial)
  }

  async whenIdle() {
    return this.work
  }

  async _waitForAcknowledgements(timeoutMs) {
    const deadline = Date.now() + timeoutMs
    while (this.pending.size && Date.now() < deadline) {
      await new Promise(resolve => setTimeout(resolve, 20))
    }
    return this.pending.size === 0
  }

  async stop({ waitForAck = true, timeoutMs = 2000 } = {}) {
    if (this.stopping || this.stopped) return
    await this.flush()
    this.stopping = true
    if (waitForAck) await this._waitForAcknowledgements(timeoutMs)
    if (this.ready && this.socket?.readyState === 1) {
      this.socket.send(JSON.stringify({ type: 'stop' }))
    } else {
      this.onStatus('degraded', {
        code: 'STOP_WITHOUT_LIVE_CONNECTION',
        pendingSequences: this.pendingSequences,
        droppedSequences: [...this.droppedSequences]
      })
    }
  }
}


export const REALTIME_AUDIO_PROTOCOL = Object.freeze({
  protocol: PROTOCOL,
  sampleRate: SAMPLE_RATE,
  channels: CHANNELS,
  bytesPerSample: BYTES_PER_SAMPLE
})
