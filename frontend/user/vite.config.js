import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import react from '@vitejs/plugin-react'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'
import fs from 'fs'
import { fileURLToPath } from 'url'
import path from 'path'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

const certDir = path.resolve(__dirname, '../../certs')
const hasCerts = fs.existsSync(path.join(certDir, 'cert.pem'))
// Keep local development on HTTP by default because the student portal,
// callbacks and E2E base URL all use http://localhost:5174. HTTPS remains
// available when it is explicitly requested for meeting/media testing.
const enableHttps = hasCerts && process.env.VITE_DEV_HTTPS === '1'
const longUploadTimeoutMs = 2 * 60 * 60 * 1000

function manualChunks(id) {
  if (!id.includes('node_modules')) return

  if (
    id.includes('/vue/') ||
    id.includes('/vue-router/') ||
    id.includes('/pinia/')
  ) {
    return 'vendor-vue'
  }

  if (
    id.includes('/element-plus/') ||
    id.includes('/@vueuse/')
  ) {
    return 'vendor-ui'
  }

  if (id.includes('/@element-plus/icons-vue/')) {
    return 'vendor-ui-icons'
  }

  if (id.includes('/echarts/')) {
    return 'vendor-echarts'
  }

  if (
    id.includes('/livekit-client/') ||
    id.includes('/livekit-server-sdk/')
  ) {
    return 'vendor-livekit'
  }

  if (
    id.includes('/socket.io-client/') ||
    id.includes('/@stomp/') ||
    id.includes('/sockjs-client/')
  ) {
    return 'vendor-realtime'
  }

  if (id.includes('/axios/')) {
    return 'vendor-http'
  }

  return 'vendor-misc'
}

export default defineConfig({
  plugins: [
    vue(),
    react(),
    AutoImport({
      resolvers: [ElementPlusResolver({ importStyle: 'css' })],
      dts: false
    }),
    Components({
      resolvers: [ElementPlusResolver({ importStyle: 'css' })],
      dts: false
    })
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src')
    }
  },
  // 预构建小启 Markdown 等依赖，避免 dev 下 504 Outdated Optimize Dep
  // 导致动态 import 失败、路由「打不开」
  optimizeDeps: {
    include: [
      'vue',
      'vue-router',
      'pinia',
      'axios',
      'element-plus',
      'element-plus/es',
      'element-plus/es/locale/lang/zh-cn',
      'marked',
      'dompurify',
      '@element-plus/icons-vue',
      '@tiptap/vue-3',
      '@tiptap/starter-kit',
      '@tiptap/extension-table',
      '@tiptap/extension-table-row',
      '@tiptap/extension-table-cell',
      '@tiptap/extension-table-header',
      '@tiptap/extension-image',
      'docx',
      'html2canvas',
      'jspdf',
    ],
  },
  build: {
    sourcemap: false,
    chunkSizeWarningLimit: 800,
    rollupOptions: {
      output: {
        manualChunks
      }
    }
  },
  server: {
    port: 5174,
    host: '0.0.0.0',
    ...(enableHttps && {
      https: {
        cert: fs.readFileSync(path.join(certDir, 'cert.pem')),
        key: fs.readFileSync(path.join(certDir, 'key.pem'))
      }
    }),
    proxy: {
      '/api/ai-chat': {
        target: 'http://localhost:8080',
        changeOrigin: true,
        secure: false
      },
      '/api/ai-score': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true,
        secure: false,
        timeout: longUploadTimeoutMs,
        proxyTimeout: longUploadTimeoutMs
      },
      '^/api/ai(/|$)': {
        target: 'http://127.0.0.1:8090',
        changeOrigin: true,
        secure: false,
        ws: true
      },
      '/api/ppt-template': {
        target: 'http://localhost:8080',
        changeOrigin: true,
        secure: false
      },
      '/api/ppt': {
        target: 'http://127.0.0.1:8090',
        changeOrigin: true,
        secure: false,
        ws: true
      },
      '/api/ppt-generator': {
        target: 'http://127.0.0.1:8090',
        changeOrigin: true,
        secure: false
      },
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
        secure: false
      },
      '/uploads': {
        target: 'http://localhost:8080',
        changeOrigin: true,
        secure: false
      },
      '/ws': {
        target: 'http://localhost:8080',
        changeOrigin: true,
        secure: false,
        ws: true
      },
      '/socket.io': {
        target: 'https://localhost:3000',
        changeOrigin: true,
        secure: false,
        ws: true
      },
      '/livekit': {
        target: 'http://localhost:7880',
        changeOrigin: true,
        secure: false,
        ws: true,
        configure: (proxy) => {
          proxy.on('proxyReq', (proxyReq) => {
            if (proxyReq.path && proxyReq.path.includes('/rtc/v1')) {
              proxyReq.path = proxyReq.path.replace('/rtc/v1', '/rtc')
            }
          })
          proxy.on('proxyReqWs', (proxyReq) => {
            if (proxyReq.path && proxyReq.path.includes('/rtc/v1')) {
              proxyReq.path = proxyReq.path.replace('/rtc/v1', '/rtc')
            }
          })
        },
        rewrite: (p) => p.replace(/^\/livekit/, '')
      },
      // 启发 Office / Collabora（本地）：
      // coolwsd.xml 默认 service_root=/collabora，所有请求必须带 /collabora 前缀。
      // 切勿 stripPrefix：剥掉后会变成 /browser/...，Collabora 直接 400 → iframe 空白。
      // 公网基址见后端 env OREP_COLLABORA_PUBLIC_URL（默认 http://127.0.0.1:5174）。
      // Collabora 上游地址可用 env OREP_COLLABORA_PROXY_TARGET（默认 127.0.0.1:9980）。
      ...createCollaboraProxy({
        // 主路径：discovery 返回的 /collabora/browser/.../cool.html 与 WS
        '/collabora': true,
        // 兼容部分资源未带 service_root 时的请求（一般用不到，保留兜底）
        '/browser': true,
        '/cool': true,
        '/hosting': true,
      }),
    }
  }
})

/**
 * Collabora 反向代理：同源 + branding no-store。
 *
 * 关键：changeOrigin 必须为 false。
 * 若改成 true，cool.html 会把 data-host 写成 ws://127.0.0.1:9980，
 * 浏览器 Origin 仍是 5174，Collabora 会报：
 *   Rejecting origin [http://127.0.0.1:5174] expected [http://127.0.0.1:9980]
 * 保持 Host=5174，让 WS 也走代理，Origin 与 Host 一致即可升级成功。
 *
 * 上游地址：process.env.OREP_COLLABORA_PROXY_TARGET 或默认本机 9980。
 * 云端不走 Vite 代理，由 nginx 反代 /collabora → collabora 容器。
 */
function createCollaboraProxy(routes) {
  const target = process.env.OREP_COLLABORA_PROXY_TARGET || 'http://127.0.0.1:9980'
  const noStore = (proxy) => {
    proxy.on('proxyRes', (proxyRes) => {
      proxyRes.headers['cache-control'] = 'no-store, no-cache, must-revalidate, max-age=0'
      proxyRes.headers['pragma'] = 'no-cache'
      delete proxyRes.headers['etag']
      delete proxyRes.headers['last-modified']
      delete proxyRes.headers['expires']
    })
  }
  const out = {}
  for (const [routePath, opt] of Object.entries(routes)) {
    const strip = opt && opt.stripPrefix
    out[routePath] = {
      target,
      changeOrigin: false,
      secure: false,
      ws: true,
      ...(strip
        ? {
            rewrite: (p) => {
              const next = p.replace(new RegExp(`^${routePath}`), '')
              return next.length ? next : '/'
            },
          }
        : {}),
      configure: noStore,
    }
  }
  return out
}
