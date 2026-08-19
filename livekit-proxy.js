/**
 * LiveKit WebSocket 代理
 * 解决 LiveKit Client 2.x (/rtc/v1) 与 LiveKit Server 1.9.12 (/rtc) 路径不匹配
 */
const https = require('https');
const http = require('http');
const net = require('net');
const fs = require('fs');
const path = require('path');

const CERT_DIR = process.env.LIVEKIT_PROXY_CERT_DIR
  ? path.resolve(process.env.LIVEKIT_PROXY_CERT_DIR)
  : path.resolve(__dirname, 'certs');
const PORT = Number(process.env.LIVEKIT_PROXY_PORT || 7882);
const LIVEKIT_HOST = process.env.LIVEKIT_HOST || '127.0.0.1';
const LIVEKIT_PORT = Number(process.env.LIVEKIT_PORT || 7880);

const httpsOptions = {
  cert: fs.readFileSync(path.join(CERT_DIR, 'cert.pem')),
  key: fs.readFileSync(path.join(CERT_DIR, 'key.pem')),
};

function rewritePath(url) {
  if (!url) return url
  return url.replace('/rtc/v1', '/rtc')
}

// HTTP 代理（token 接口等）
const server = https.createServer(httpsOptions, (req, res) => {
  const targetPath = rewritePath(req.url);

  const proxyReq = http.request({
    hostname: LIVEKIT_HOST,
    port: LIVEKIT_PORT,
    path: targetPath,
    method: req.method,
    headers: { ...req.headers, host: `${LIVEKIT_HOST}:${LIVEKIT_PORT}` },
  }, (proxyRes) => {
    res.writeHead(proxyRes.statusCode, proxyRes.headers);
    proxyRes.pipe(res);
  });
  proxyReq.on('error', () => { res.writeHead(502); res.end('Proxy Error'); });
  req.pipe(proxyReq);
});

// WebSocket 升级：直接 TCP pipe，更可靠
server.on('upgrade', (req, clientSocket, head) => {
  const targetPath = rewritePath(req.url);
  const proxySocket = net.createConnection(LIVEKIT_PORT, LIVEKIT_HOST, () => {
    // 构建转发请求头
    const headers = [
      `GET ${targetPath} HTTP/1.1`,
      ...Object.entries(req.headers).map(([k, v]) => `${k}: ${v}`),
      '', ''
    ].join('\r\n');
    proxySocket.write(headers);
    if (head.length) proxySocket.write(head);

    // 双向 pipe
    clientSocket.pipe(proxySocket);
    proxySocket.pipe(clientSocket);

    clientSocket.on('error', () => proxySocket.destroy());
    proxySocket.on('error', () => clientSocket.destroy());
  });

  proxySocket.on('error', () => {
    clientSocket.write('HTTP/1.1 502 Bad Gateway\r\n\r\n');
    clientSocket.destroy();
  });
});

server.listen(PORT, () => {
  console.log(`LiveKit proxy running on https://0.0.0.0:${PORT}`);
  console.log(`  upstream: http://${LIVEKIT_HOST}:${LIVEKIT_PORT}`);
  console.log(`  /rtc/v1 → /rtc (LiveKit Server 1.9.12 compatibility)`);
});

process.on('uncaughtException', (err) => {
  // 忽略连接重置等常规网络错误
  if (['ECONNRESET', 'EPIPE', 'ERR_STREAM_DESTROYED'].includes(err.code)) return;
  console.error('Proxy error:', err.message);
});
process.on('SIGTERM', () => process.exit(0));
process.on('SIGINT', () => process.exit(0));
