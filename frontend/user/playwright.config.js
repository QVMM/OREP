import { defineConfig } from '@playwright/test'
import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const certDir = path.resolve(__dirname, '../../certs')
const hasCerts = fs.existsSync(path.join(certDir, 'cert.pem'))
const enableHttps = hasCerts && process.env.VITE_DEV_HTTPS !== '0'
const defaultBaseUrl = `${enableHttps ? 'https' : 'http'}://localhost:5174`

export default defineConfig({
  testDir: './tests',
  timeout: 30_000,
  use: {
    baseURL: process.env.OREP_E2E_BASE_URL || defaultBaseUrl,
    ignoreHTTPSErrors: enableHttps,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure'
  }
})
