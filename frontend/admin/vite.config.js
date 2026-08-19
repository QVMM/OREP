import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import fs from 'fs'
import path from 'path'

const certDir = path.resolve(__dirname, '../../certs')
const hasCerts = fs.existsSync(path.join(certDir, 'cert.pem'))

export default defineConfig({
  base: process.env.VITE_PUBLIC_BASE || '/admin/',
  plugins: [vue()],
  server: {
    port: 5173,
    host: '0.0.0.0',
    ...(hasCerts && {
      https: {
        cert: fs.readFileSync(path.join(certDir, 'cert.pem')),
        key: fs.readFileSync(path.join(certDir, 'key.pem'))
      }
    }),
    proxy: {
      '/api/ppt': {
        target: 'http://localhost:8090',
        changeOrigin: true,
        secure: false
      },
      '/api': {
        target: process.env.VITE_BACKEND_PROXY_TARGET || 'http://localhost:8080',
        changeOrigin: true,
      }
      ,
      '/uploads': {
        target: process.env.VITE_BACKEND_PROXY_TARGET || 'http://localhost:8080',
        changeOrigin: true,
        secure: false
      }
    }
  }
})
