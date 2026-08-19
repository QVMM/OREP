/**
 * OREP Recording Bot Service
 *
 * 服务端加入 LiveKit 房间，生成单一带音频的会议视频：
 * - 视频：优先屏幕共享，其次摄像头宫格，绘制到 canvas
 * - 音频：订阅到的所有音频轨道混音
 * - 输出：recording_*.webm，停止后回传 Spring 后端，由后端入 MinIO 和数据库
 */

const express = require('express');
const cors = require('cors');
const { AccessToken } = require('livekit-server-sdk');
const puppeteer = require('puppeteer');
const { v4: uuidv4 } = require('uuid');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');

const app = express();
app.use(cors());
app.use(express.json({ limit: '2mb' }));

const LIVEKIT_URL = process.env.LIVEKIT_URL || 'ws://127.0.0.1:7880';
const LIVEKIT_API_KEY = process.env.LIVEKIT_API_KEY || 'devkey-orep-local';
const LIVEKIT_API_SECRET = process.env.LIVEKIT_API_SECRET || 'OREP_DEV_ONLY_LIVEKIT_SECRET_32_CHARS';
const RECORDINGS_DIR = process.env.RECORDINGS_DIR || path.join(__dirname, '..', 'recordings');
const BOT_PORT = Number(process.env.BOT_PORT || 8091);
const DEFAULT_CALLBACK_BASE_URL = process.env.BACKEND_CALLBACK_BASE_URL || 'http://127.0.0.1:8080';
const DEFAULT_CALLBACK_SECRET = process.env.RECORDING_BOT_SECRET || 'OREP_DEV_RECORDING_BOT_SECRET';
const CHROME_EXECUTABLE_PATH = process.env.CHROME_EXECUTABLE_PATH || findLocalChrome();
const LIVEKIT_CLIENT_UMD_PATH = process.env.LIVEKIT_CLIENT_UMD_PATH || findLiveKitClientUmd();

fs.mkdirSync(RECORDINGS_DIR, { recursive: true });

const activeRecordings = new Map();

if (LIVEKIT_CLIENT_UMD_PATH) {
  app.use('/vendor/livekit-client', express.static(path.dirname(LIVEKIT_CLIENT_UMD_PATH)));
}

app.post('/api/recording/start', async (req, res) => {
  const {
    meetingId,
    roomName,
    backendRecordingId,
    recordingId = uuidv4().slice(0, 12),
    callbackBaseUrl = DEFAULT_CALLBACK_BASE_URL,
    callbackSecret = DEFAULT_CALLBACK_SECRET,
  } = req.body || {};

  if (!meetingId || !roomName || !backendRecordingId) {
    return res.status(400).json({ error: 'meetingId, roomName and backendRecordingId are required' });
  }
  if (activeRecordings.has(String(meetingId))) {
    return res.status(409).json({ error: 'Recording already in progress', meetingId });
  }

  try {
    const sessionDir = path.join(RECORDINGS_DIR, `meeting_${meetingId}`, String(backendRecordingId));
    fs.mkdirSync(sessionDir, { recursive: true });
    const botToken = await generateBotToken(String(roomName), `recorder-${recordingId}`);
    const recording = await startRecording({
      meetingId: String(meetingId),
      backendRecordingId: String(backendRecordingId),
      recordingId,
      botToken,
      sessionDir,
      callbackBaseUrl,
      callbackSecret,
    });
    activeRecordings.set(String(meetingId), recording);
    res.json({
      success: true,
      meetingId,
      recordingId,
      backendRecordingId,
      status: 'recording',
    });
  } catch (err) {
    console.error(`[Bot] start failed: ${err.stack || err.message}`);
    res.status(500).json({ error: err.message });
  }
});

app.post('/api/recording/stop', async (req, res) => {
  const { meetingId } = req.body || {};
  const key = String(meetingId || '');
  if (!key) return res.status(400).json({ error: 'meetingId is required' });

  const recording = activeRecordings.get(key);
  if (!recording) return res.status(404).json({ error: 'No active recording found' });
  if (recording.status === 'processing') {
    return res.json({ success: true, meetingId, status: 'processing' });
  }

  recording.status = 'processing';
  res.json({ success: true, meetingId, status: 'processing' });

  setImmediate(async () => {
    try {
      await stopRecording(recording);
    } catch (err) {
      console.error(`[Bot] stop failed: ${err.stack || err.message}`);
      await notifyFailure(recording, err.message).catch(() => {});
    } finally {
      activeRecordings.delete(key);
    }
  });
});

app.get('/api/recording/status/:meetingId', (req, res) => {
  const key = String(req.params.meetingId);
  const recording = activeRecordings.get(key);
  if (recording) {
    return res.json({
      meetingId: key,
      status: recording.status || 'recording',
      recordingId: recording.recordingId,
      backendRecordingId: recording.backendRecordingId,
      startTime: new Date(recording.startTime).toISOString(),
      sources: recording.sources,
    });
  }
  res.json({ meetingId: key, status: 'idle' });
});

app.get('/api/recording/health', (req, res) => {
  res.json({
    service: 'OREP Recording Bot',
    version: '2.0.0',
    mode: 'server-composited-webm',
    active_recordings: activeRecordings.size,
    livekit_url: LIVEKIT_URL,
    livekit_client_umd: LIVEKIT_CLIENT_UMD_PATH || 'cdn-fallback',
  });
});

app.post('/api/recording/save-composite', express.raw({
  type: 'application/octet-stream',
  limit: '1200mb',
}), (req, res) => {
  const filename = req.headers['x-filename'];
  const meetingId = req.headers['x-meeting-id'];
  const backendRecordingId = req.headers['x-recording-id'];
  if (!filename || !meetingId || !backendRecordingId) {
    return res.status(400).json({ error: 'Missing recording headers' });
  }
  const sessionDir = path.join(RECORDINGS_DIR, `meeting_${meetingId}`, String(backendRecordingId));
  fs.mkdirSync(sessionDir, { recursive: true });
  const filePath = path.join(sessionDir, path.basename(String(filename)));
  fs.writeFileSync(filePath, req.body);
  res.json({ success: true, path: filePath, size: req.body.length });
});

async function generateBotToken(roomName, identity) {
  const at = new AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET, {
    identity,
    name: 'Recording Bot',
    ttl: '2h',
  });
  at.addGrant({
    room: roomName,
    roomJoin: true,
    canSubscribe: true,
    canPublish: false,
    canPublishData: false,
  });
  return await at.toJwt();
}

async function startRecording(config) {
  const browser = await puppeteer.launch({
    headless: 'new',
    ...(CHROME_EXECUTABLE_PATH ? { executablePath: CHROME_EXECUTABLE_PATH } : {}),
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--autoplay-policy=no-user-gesture-required',
      '--use-fake-ui-for-media-stream',
      '--disable-dev-shm-usage',
      '--disable-background-timer-throttling',
      '--disable-renderer-backgrounding',
    ],
  });

  const page = await browser.newPage();
  page.on('console', msg => console.log(`[Recorder:${config.meetingId}] ${msg.text()}`));
  page.on('pageerror', err => console.error(`[Recorder:${config.meetingId}] page error: ${err.message}`));
  await page.setViewport({ width: 1280, height: 720, deviceScaleFactor: 1 });

  const html = generateRecorderHTML(LIVEKIT_URL, config.botToken, BOT_PORT, config.meetingId, config.backendRecordingId);
  await page.setContent(html, { waitUntil: 'networkidle0', timeout: 30000 });
  await page.evaluate(async () => window.__startCompositeRecording__());

  return {
    ...config,
    browser,
    page,
    status: 'recording',
    startTime: Date.now(),
    sources: { camera: false, screen: false, audio: false },
  };
}

function findLocalChrome() {
  const candidates = [
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
    '/Applications/Chromium.app/Contents/MacOS/Chromium',
    '/usr/bin/google-chrome',
    '/usr/bin/chromium-browser',
    '/usr/bin/chromium',
  ];
  return candidates.find(p => fs.existsSync(p)) || '';
}

function findLiveKitClientUmd() {
  const candidates = [
    path.join(__dirname, '..', 'node_modules', 'livekit-client', 'dist', 'livekit-client.umd.js'),
    path.join(__dirname, '..', '..', 'frontend', 'user', 'node_modules', 'livekit-client', 'dist', 'livekit-client.umd.js'),
  ];
  return candidates.find(p => fs.existsSync(p)) || '';
}

async function stopRecording(recording) {
  const { page, browser, meetingId, backendRecordingId, callbackBaseUrl, callbackSecret } = recording;
  const stopped = await page.evaluate(async () => window.__stopCompositeRecording__());
  const durationSeconds = Math.round((Date.now() - recording.startTime) / 1000);

  await browser.close();

  const filePath = stopped.path;
  await remuxWebmForSeeking(filePath).catch(err => {
    console.warn(`[Recording Bot] WebM remux skipped: ${err.message}`);
  });
  const stats = fs.statSync(filePath);
  const metadata = {
    meetingId,
    backendRecordingId,
    recordingId: recording.recordingId,
    filePath,
    size: stats.size,
    durationSeconds,
    hasAudio: !!stopped.hasAudio,
    hasVideo: !!stopped.hasVideo,
    sources: stopped.sources,
    recordedAt: new Date().toISOString(),
  };
  fs.writeFileSync(path.join(recording.sessionDir, 'metadata.json'), JSON.stringify(metadata, null, 2));

  await uploadToBackend({
    callbackBaseUrl,
    callbackSecret,
    backendRecordingId,
    meetingId,
    durationSeconds,
    filePath,
    hasAudio: metadata.hasAudio,
    hasVideo: metadata.hasVideo,
  });

  return {
    duration: durationSeconds,
    size: stats.size,
    hasAudio: metadata.hasAudio,
    hasVideo: metadata.hasVideo,
    sources: stopped.sources,
  };
}

function remuxWebmForSeeking(filePath) {
  return new Promise((resolve, reject) => {
    if (!filePath || path.extname(filePath).toLowerCase() !== '.webm') {
      resolve(false);
      return;
    }

    const tmpPath = filePath.replace(/\.webm$/i, '.seekable.tmp.webm');
    const ffmpeg = spawn('ffmpeg', [
      '-y',
      '-i', filePath,
      '-c', 'copy',
      tmpPath,
    ]);
    let stderr = '';

    ffmpeg.stderr.on('data', chunk => {
      stderr += chunk.toString();
      if (stderr.length > 6000) stderr = stderr.slice(-6000);
    });
    ffmpeg.on('error', reject);
    ffmpeg.on('close', code => {
      if (code !== 0) {
        fs.rmSync(tmpPath, { force: true });
        reject(new Error(stderr.trim() || `ffmpeg exited with code ${code}`));
        return;
      }
      const originalSize = fs.statSync(filePath).size;
      const remuxedSize = fs.statSync(tmpPath).size;
      if (remuxedSize <= 0) {
        fs.rmSync(tmpPath, { force: true });
        reject(new Error('remuxed file is empty'));
        return;
      }
      fs.renameSync(tmpPath, filePath);
      console.log(`[Recording Bot] WebM remuxed for seeking: ${path.basename(filePath)} ${originalSize} -> ${remuxedSize}`);
      resolve(true);
    });
  });
}

async function uploadToBackend({ callbackBaseUrl, callbackSecret, backendRecordingId, meetingId, durationSeconds, filePath, hasAudio, hasVideo }) {
  const formData = new FormData();
  const bytes = fs.readFileSync(filePath);
  formData.append('recording_id', backendRecordingId);
  formData.append('meeting_id', meetingId);
  formData.append('duration_seconds', String(durationSeconds));
  formData.append('has_audio', String(hasAudio));
  formData.append('has_video', String(hasVideo));
  formData.append('video', new Blob([bytes], { type: 'video/webm' }), path.basename(filePath));

  const response = await fetch(`${callbackBaseUrl}/api/recording/bot-complete`, {
    method: 'POST',
    headers: { 'X-Recording-Secret': callbackSecret },
    body: formData,
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`backend callback failed ${response.status}: ${text}`);
  }
}

async function notifyFailure(recording, message) {
  if (!recording) return;
  await fetch(`${recording.callbackBaseUrl}/api/recording/bot-failed`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Recording-Secret': recording.callbackSecret,
    },
    body: JSON.stringify({
      recording_id: Number(recording.backendRecordingId),
      meeting_id: Number(recording.meetingId),
      error: message,
    }),
  });
}

function generateRecorderHTML(livekitUrl, botToken, botPort, meetingId, backendRecordingId) {
  return `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>OREP Composite Recorder</title>
  <style>
    html, body { margin: 0; width: 100%; height: 100%; background: #11131a; overflow: hidden; }
    canvas { width: 1280px; height: 720px; display: block; }
    video { position: fixed; left: -9999px; top: -9999px; width: 1px; height: 1px; }
  </style>
  <script src="${LIVEKIT_CLIENT_UMD_PATH ? `http://127.0.0.1:${botPort}/vendor/livekit-client/${path.basename(LIVEKIT_CLIENT_UMD_PATH)}` : 'https://cdn.jsdelivr.net/npm/livekit-client@2/dist/livekit-client.umd.min.js'}"></script>
</head>
<body>
  <canvas id="stage" width="1280" height="720"></canvas>
  <script>
    const { Room, RoomEvent, Track } = window.LivekitClient;
    const canvas = document.getElementById('stage');
    const ctx = canvas.getContext('2d');
    const videos = new Map();
    const audioSources = new Map();
    const sources = { camera: false, screen: false, audio: false };
    let room = null;
    let audioContext = null;
    let audioDest = null;
    let audioAnalyser = null;
    let audioMonitorTimer = null;
    let audioPeakLevel = 0;
    let mediaRecorder = null;
    let chunks = [];
    let drawTimer = null;

    function log(message) { console.log(message); }

    function ensureAudio() {
      if (!audioContext) {
        audioContext = new AudioContext({ sampleRate: 48000 });
        audioDest = audioContext.createMediaStreamDestination();
        audioAnalyser = audioContext.createAnalyser();
        audioAnalyser.fftSize = 2048;
      }
      return audioDest;
    }

    function startAudioMonitor() {
      if (!audioAnalyser || audioMonitorTimer) return;
      const buffer = new Uint8Array(audioAnalyser.fftSize);
      audioMonitorTimer = setInterval(() => {
        audioAnalyser.getByteTimeDomainData(buffer);
        let peak = 0;
        for (let i = 0; i < buffer.length; i++) {
          peak = Math.max(peak, Math.abs(buffer[i] - 128) / 128);
        }
        audioPeakLevel = Math.max(audioPeakLevel, peak);
      }, 500);
    }

    function addVideoTrack(track, pub, participant) {
      const key = participant.sid + ':' + pub.source;
      const video = document.createElement('video');
      video.autoplay = true;
      video.muted = true;
      video.playsInline = true;
      video.srcObject = new MediaStream([track.mediaStreamTrack]);
      document.body.appendChild(video);
      video.play().catch(() => {});
      videos.set(key, {
        el: video,
        source: pub.source,
        name: participant.name || participant.identity || '参会者',
      });
      if (pub.source === Track.Source.ScreenShare) sources.screen = true;
      else sources.camera = true;
    }

    function removeVideoTrack(pub, participant) {
      const key = participant.sid + ':' + pub.source;
      const item = videos.get(key);
      if (item) {
        item.el.srcObject = null;
        item.el.remove();
        videos.delete(key);
      }
    }

    function addAudioTrack(track, pub, participant) {
      if (participant.identity && participant.identity.startsWith('recorder-')) return;
      const key = participant.sid + ':' + (pub.trackSid || pub.sid || pub.source);
      if (audioSources.has(key)) return;
      const dest = ensureAudio();
      const mediaTrack = track.mediaStreamTrack;
      if (!mediaTrack) {
        log('audio track missing mediaStreamTrack: ' + key);
        return;
      }
      const stream = new MediaStream([mediaTrack]);
      const source = audioContext.createMediaStreamSource(stream);
      source.connect(dest);
      if (audioAnalyser) source.connect(audioAnalyser);
      let element = null;
      try {
        element = track.attach ? track.attach() : document.createElement('audio');
        element.autoplay = true;
        element.playsInline = true;
        element.muted = false;
        element.volume = 1;
        if (!element.srcObject) element.srcObject = stream;
        document.body.appendChild(element);
        element.play().catch(err => log('audio element play failed: ' + err.message));
      } catch (err) {
        log('audio element attach failed: ' + err.message);
      }
      audioContext.resume()
        .then(() => log('audio context state after resume: ' + audioContext.state))
        .catch(err => log('audio context resume failed: ' + err.message));
      mediaTrack.addEventListener('mute', () => log('audio media track muted: ' + key));
      mediaTrack.addEventListener('unmute', () => log('audio media track unmuted: ' + key));
      mediaTrack.addEventListener('ended', () => log('audio media track ended: ' + key));
      audioSources.set(key, { source, stream, element, track });
      sources.audio = true;
      log('audio track mixed: ' + key
        + ' source=' + pub.source
        + ' track=' + (pub.trackSid || pub.sid || mediaTrack.id)
        + ' enabled=' + mediaTrack.enabled
        + ' muted=' + mediaTrack.muted
        + ' readyState=' + mediaTrack.readyState
        + ' ctx=' + audioContext.state);
    }

    function removeAudioTrack(pub, participant) {
      const key = participant.sid + ':' + (pub.trackSid || pub.sid || pub.source);
      const item = audioSources.get(key);
      if (!item) return;
      try { item.source.disconnect(); } catch {}
      if (item.element) {
        try { item.track.detach(item.element); } catch {}
        try { item.element.srcObject = null; } catch {}
        item.element.remove();
      }
      audioSources.delete(key);
    }

    function drawLabel(text, x, y) {
      ctx.font = '22px sans-serif';
      ctx.fillStyle = 'rgba(244,246,252,.92)';
      ctx.fillText(text, x, y);
    }

    function drawPlaceholder() {
      const gradient = ctx.createLinearGradient(0, 0, 1280, 720);
      gradient.addColorStop(0, '#151923');
      gradient.addColorStop(1, '#1f2531');
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, 1280, 720);
      ctx.fillStyle = 'rgba(244,246,252,.82)';
      ctx.font = '38px sans-serif';
      ctx.fillText('OREP 会议录制中', 470, 332);
      ctx.font = '20px sans-serif';
      ctx.fillStyle = 'rgba(244,246,252,.58)';
      ctx.fillText('等待会议视频或屏幕共享画面', 500, 372);
    }

    function drawContain(video, x, y, w, h) {
      const vw = video.videoWidth || 16;
      const vh = video.videoHeight || 9;
      const scale = Math.min(w / vw, h / vh);
      const dw = vw * scale;
      const dh = vh * scale;
      ctx.drawImage(video, x + (w - dw) / 2, y + (h - dh) / 2, dw, dh);
    }

    function drawFrame() {
      const items = [...videos.values()].filter(v => v.el.readyState >= 2);
      const screen = items.find(v => v.source === Track.Source.ScreenShare);
      const cameras = items.filter(v => v.source !== Track.Source.ScreenShare);

      ctx.fillStyle = '#11131a';
      ctx.fillRect(0, 0, 1280, 720);

      if (screen) {
        drawContain(screen.el, 0, 0, 1280, 720);
        drawLabel(screen.name + ' 的屏幕', 24, 44);
        const thumbW = 220;
        const thumbH = 124;
        cameras.slice(0, 3).forEach((cam, index) => {
          const x = 1036;
          const y = 24 + index * 142;
          ctx.fillStyle = 'rgba(17,19,26,.72)';
          ctx.fillRect(x - 8, y - 8, thumbW + 16, thumbH + 34);
          drawContain(cam.el, x, y, thumbW, thumbH);
          ctx.font = '15px sans-serif';
          ctx.fillStyle = 'rgba(244,246,252,.88)';
          ctx.fillText(cam.name, x, y + thumbH + 22);
        });
        return;
      }

      if (!cameras.length) {
        drawPlaceholder();
        return;
      }

      const count = Math.min(cameras.length, 9);
      const cols = count <= 1 ? 1 : count <= 4 ? 2 : 3;
      const rows = Math.ceil(count / cols);
      const gap = 16;
      const cellW = (1280 - gap * (cols + 1)) / cols;
      const cellH = (720 - gap * (rows + 1)) / rows;
      cameras.slice(0, count).forEach((cam, index) => {
        const col = index % cols;
        const row = Math.floor(index / cols);
        const x = gap + col * (cellW + gap);
        const y = gap + row * (cellH + gap);
        ctx.fillStyle = '#1a1f2b';
        ctx.fillRect(x, y, cellW, cellH);
        drawContain(cam.el, x, y, cellW, cellH);
        drawLabel(cam.name, x + 16, y + 34);
      });
    }

    window.__startCompositeRecording__ = async function() {
      ensureAudio();
      await audioContext.resume().catch(() => {});

      room = new Room({ adaptiveStream: false, dynacast: false });
      room.on(RoomEvent.TrackSubscribed, (track, pub, participant) => {
        if (track.kind === 'video') addVideoTrack(track, pub, participant);
        if (track.kind === 'audio') addAudioTrack(track, pub, participant);
      });
      room.on(RoomEvent.TrackUnsubscribed, (track, pub, participant) => {
        if (track.kind === 'video') removeVideoTrack(pub, participant);
        if (track.kind === 'audio') removeAudioTrack(pub, participant);
      });

      await room.connect('${livekitUrl}', '${botToken}');
      log('connected');

      drawTimer = setInterval(drawFrame, 1000 / 15);
      startAudioMonitor();
      const canvasStream = canvas.captureStream(15);
      const tracks = [
        ...canvasStream.getVideoTracks(),
        ...audioDest.stream.getAudioTracks(),
      ];
      const mixedStream = new MediaStream(tracks);
      const mimeType = MediaRecorder.isTypeSupported('video/webm;codecs=vp8,opus')
        ? 'video/webm;codecs=vp8,opus'
        : 'video/webm';
      mediaRecorder = new MediaRecorder(mixedStream, {
        mimeType,
        videoBitsPerSecond: 2500000,
        audioBitsPerSecond: 128000,
      });
      chunks = [];
      mediaRecorder.ondataavailable = event => {
        if (event.data && event.data.size > 0) chunks.push(event.data);
      };
      mediaRecorder.start(1000);
      log('recording started');
    };

    window.__stopCompositeRecording__ = async function() {
      if (!mediaRecorder) throw new Error('recorder was not started');
      await new Promise(resolve => {
        mediaRecorder.onstop = resolve;
        mediaRecorder.stop();
      });
      if (drawTimer) clearInterval(drawTimer);
      drawTimer = null;
      if (audioMonitorTimer) clearInterval(audioMonitorTimer);
      audioMonitorTimer = null;

      const blob = new Blob(chunks, { type: mediaRecorder.mimeType || 'video/webm' });
      const arrayBuffer = await blob.arrayBuffer();
      const filename = 'recording_' + new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19) + '.webm';
      const response = await fetch('http://127.0.0.1:${botPort}/api/recording/save-composite', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/octet-stream',
          'X-Filename': filename,
          'X-Meeting-Id': '${meetingId}',
          'X-Recording-Id': '${backendRecordingId}',
        },
        body: new Uint8Array(arrayBuffer),
      });
      if (!response.ok) throw new Error('save composite failed: ' + response.status);
      const saveResult = await response.json();

      if (room) room.disconnect();
      videos.forEach(item => item.el.remove());
      videos.clear();
      audioSources.forEach(item => {
        try { item.source.disconnect(); } catch {}
        if (item.element) {
          try { item.track.detach(item.element); } catch {}
          try { item.element.srcObject = null; } catch {}
          item.element.remove();
        }
      });
      audioSources.clear();
      if (audioContext) await audioContext.close().catch(() => {});

      return {
        filename,
        path: saveResult.path,
        size: blob.size,
        hasAudio: true,
        hasVideo: true,
        sources: { ...sources, audioAudible: audioPeakLevel > 0.002, audioPeakLevel },
      };
    };
  </script>
</body>
</html>`;
}

app.listen(BOT_PORT, () => {
  console.log(`[Recording Bot] http://0.0.0.0:${BOT_PORT}`);
  console.log(`[Recording Bot] LiveKit: ${LIVEKIT_URL}`);
  console.log(`[Recording Bot] recordings: ${RECORDINGS_DIR}`);
});
