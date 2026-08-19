import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const userSrc = path.resolve(__dirname, '../user/src')
// 默认 HTTP，避免自签证书浏览器打不开；需要 HTTPS 时设 VITE_DEV_HTTPS=1
const enableHttps = process.env.VITE_DEV_HTTPS === '1'
const certDir = path.resolve(__dirname, '../../certs')
const hasCerts = fs.existsSync(path.join(certDir, 'cert.pem'))

export default defineConfig({
  base: process.env.VITE_PUBLIC_BASE || '/teacher/',
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
      '@user-styles': path.resolve(userSrc, 'styles'),
      '@sdoc': path.resolve(userSrc, 'views/inspire-office/smart-doc'),
    },
  },
  optimizeDeps: {
    include: ['docx', 'html2canvas', 'jspdf'],
  },
  server: {
    port: 5175,
    host: '0.0.0.0',
    strictPort: true,
    ...(enableHttps && hasCerts
      ? {
          https: {
            cert: fs.readFileSync(path.join(certDir, 'cert.pem')),
            key: fs.readFileSync(path.join(certDir, 'key.pem')),
          },
        }
      : {}),
    proxy: {
      '/api': {
        target: process.env.VITE_BACKEND_PROXY_TARGET || 'http://localhost:8080',
        changeOrigin: true,
      },
      '/uploads': {
        target: process.env.VITE_BACKEND_PROXY_TARGET || 'http://localhost:8080',
        changeOrigin: true,
      },
      '/ws': {
        target: process.env.VITE_BACKEND_PROXY_TARGET || 'http://localhost:8080',
        changeOrigin: true,
        ws: true,
      },
    },
  },
})
