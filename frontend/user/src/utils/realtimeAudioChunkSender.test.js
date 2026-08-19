import assert from 'node:assert/strict'
import test from 'node:test'

import {
  RealtimeAudioChunkSender,
  buildLiveVideoTiming
} from './realtimeAudioChunkSender.js'


class FakeSocket {
  constructor(url) {
    this.url = url
    this.readyState = 0
    this.sent = []
    this.onopen = null
    this.onmessage = null
    this.onclose = null
    this.onerror = null
  }

  open() {
    this.readyState = 1
    this.onopen?.()
  }

  message(payload) {
    this.onmessage?.({ data: JSON.stringify(payload) })
  }

  send(payload) {
    this.sent.push(payload)
  }

  close() {
    this.readyState = 3
    this.onclose?.()
  }
}


function fixture(options = {}) {
  const sockets = []
  const reconnects = []
  const statuses = []
  const sender = new RealtimeAudioChunkSender({
    url: 'ws://localhost/audio?protocol=media-evidence-v2',
    socketFactory: url => {
      const socket = new FakeSocket(url)
      sockets.push(socket)
      return socket
    },
    reconnectScheduler: callback => {
      reconnects.push(callback)
      return reconnects.length
    },
    onStatus: (status, detail) => statuses.push({ status, detail }),
    ...options
  })
  return { sender, sockets, reconnects, statuses }
}


async function ready(fx, nextSequence = 0) {
  fx.sender.start()
  const socket = fx.sockets.at(-1)
  socket.open()
  const hello = JSON.parse(socket.sent[0])
  assert.equal(hello.type, 'hello')
  assert.equal(hello.protocol, 'media-evidence-v2')
  socket.message({
    type: 'ready',
    protocol: 'media-evidence-v2',
    sampleRate: 16000,
    channels: 1,
    nextSequence
  })
  await fx.sender.whenIdle()
  return socket
}


test('aggregates PCM into one-second sequenced chunks', async () => {
  const fx = fixture({ clockId: 'clock-live-1' })
  const socket = await ready(fx)
  const pcm = new Uint8Array(32000)
  pcm[0] = 7

  await fx.sender.pushPcm(pcm.buffer)

  assert.equal(socket.sent.length, 3)
  const metadata = JSON.parse(socket.sent[1])
  assert.deepEqual(
    {
      type: metadata.type,
      sequence: metadata.sequence,
      clockId: metadata.clockId,
      startSample: metadata.startSample,
      sampleCount: metadata.sampleCount,
      startMs: metadata.startMs,
      endMs: metadata.endMs,
      hashPrefix: metadata.payloadHash.slice(0, 7)
    },
    {
      type: 'audio_chunk',
      sequence: 0,
      clockId: 'clock-live-1',
      startSample: 0,
      sampleCount: 16000,
      startMs: 0,
      endMs: 1000,
      hashPrefix: 'sha256:'
    }
  )
  assert.equal(socket.sent[2].byteLength, 32000)
  assert.equal(fx.sender.pendingCount, 1)
})


test('one clock identity survives reconnect and advances by sample count', async () => {
  const fx = fixture({ clockId: 'clock-live-stable' })
  const first = await ready(fx)
  await fx.sender.pushPcm(new Uint8Array(32000).buffer)
  const firstHello = JSON.parse(first.sent[0])
  assert.equal(firstHello.clockId, 'clock-live-stable')
  assert.equal(firstHello.masterSource, 'AUDIO_SAMPLE_CLOCK')

  first.close()
  fx.reconnects.shift()()
  const second = fx.sockets.at(-1)
  second.open()
  const secondHello = JSON.parse(second.sent[0])
  assert.equal(secondHello.clockId, firstHello.clockId)
  second.message({
    type: 'ready',
    protocol: 'media-evidence-v2',
    sampleRate: 16000,
    channels: 1,
    clockId: 'clock-live-stable',
    nextSequence: 0,
    nextSample: 0
  })
  await fx.sender.whenIdle()

  const replayed = JSON.parse(second.sent[1])
  assert.equal(replayed.startSample, 0)
  assert.equal(replayed.sampleCount, 16000)
})


test('a server clock mismatch degrades the channel instead of sending evidence', async () => {
  const fx = fixture({ clockId: 'clock-client' })
  fx.sender.start()
  const socket = fx.sockets.at(-1)
  socket.open()
  socket.message({
    type: 'ready',
    protocol: 'media-evidence-v2',
    sampleRate: 16000,
    channels: 1,
    clockId: 'clock-other',
    nextSequence: 0,
    nextSample: 0
  })
  await fx.sender.whenIdle()
  await fx.sender.pushPcm(new Uint8Array(32000).buffer)

  assert.equal(socket.sent.length, 1)
  assert.equal(fx.statuses.at(-1).detail.code, 'CLOCK_ID_MISMATCH')
})


test('video timing keeps raw PTS and captures the simultaneous audio sample cursor', () => {
  assert.deepEqual(
    buildLiveVideoTiming({
      clockId: 'clock-live-1',
      videoTimeSeconds: 1.234,
      observedAudioSample: 19_744
    }),
    {
      clockId: 'clock-live-1',
      rawPts: 1234,
      ptsTimebaseNum: 1,
      ptsTimebaseDen: 1000,
      observedAudioSample: 19_744
    }
  )
})


test('ack removes only the acknowledged chunk', async () => {
  const fx = fixture()
  const socket = await ready(fx)
  await fx.sender.pushPcm(new Uint8Array(64000).buffer)
  assert.equal(fx.sender.pendingCount, 2)

  socket.message({ type: 'ack', sequence: 1, status: 'accepted', nextSequence: 0 })

  assert.equal(fx.sender.pendingCount, 1)
  assert.deepEqual(fx.sender.pendingSequences, [0])
})


test('reconnect replays unacknowledged chunks from server nextSequence', async () => {
  const fx = fixture()
  const first = await ready(fx)
  await fx.sender.pushPcm(new Uint8Array(32000).buffer)
  first.close()
  assert.equal(fx.reconnects.length, 1)

  fx.reconnects.shift()()
  const second = fx.sockets.at(-1)
  second.open()
  second.message({
    type: 'ready',
    protocol: 'media-evidence-v2',
    sampleRate: 16000,
    channels: 1,
    nextSequence: 0
  })
  await fx.sender.whenIdle()

  assert.equal(JSON.parse(second.sent[1]).sequence, 0)
  assert.equal(second.sent[2].byteLength, 32000)
})


test('bounded queue drops realtime evidence explicitly without blocking capture', async () => {
  const fx = fixture({ maxPendingChunks: 1 })
  const socket = await ready(fx)

  const accepted = await fx.sender.pushPcm(new Uint8Array(64000).buffer)

  assert.equal(accepted, false)
  assert.deepEqual(fx.sender.droppedSequences, [1])
  assert.equal(fx.sender.pendingCount, 1)
  assert.equal(socket.sent.length, 3)
  assert.equal(fx.statuses.at(-1).status, 'degraded')
})


test('stop flushes partial audio and sends explicit stop after ack', async () => {
  const fx = fixture()
  const socket = await ready(fx)
  await fx.sender.pushPcm(new Uint8Array(16000).buffer)

  const stopping = fx.sender.stop({ waitForAck: false })
  await stopping

  assert.equal(JSON.parse(socket.sent[1]).endMs, 500)
  assert.equal(JSON.parse(socket.sent.at(-1)).type, 'stop')
})


test('server nextSequence discards already durable pending chunks', async () => {
  const fx = fixture()
  const first = await ready(fx)
  await fx.sender.pushPcm(new Uint8Array(32000).buffer)
  first.close()

  fx.reconnects.shift()()
  const second = fx.sockets.at(-1)
  second.open()
  second.message({
    type: 'ready',
    protocol: 'media-evidence-v2',
    sampleRate: 16000,
    channels: 1,
    nextSequence: 1
  })
  await fx.sender.whenIdle()

  assert.equal(fx.sender.pendingCount, 0)
  assert.equal(second.sent.length, 1)
})
