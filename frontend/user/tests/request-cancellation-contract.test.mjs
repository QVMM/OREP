import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const requestSource = readFileSync(
  new URL('../src/utils/request.js', import.meta.url),
  'utf8'
)

test('request interceptor rejects cancellations before telemetry, auth, routing, or toast side effects', () => {
  const errorInterceptor = requestSource.slice(
    requestSource.indexOf('(error) => {', requestSource.indexOf('request.interceptors.response.use'))
  )
  const cancellationGuardIndex = errorInterceptor.indexOf('axios.isCancel(error)')
  const telemetryIndex = errorInterceptor.indexOf('trackApiRequest(')

  assert.ok(cancellationGuardIndex >= 0, 'response interceptor must recognize axios cancellations')
  assert.ok(
    cancellationGuardIndex < telemetryIndex,
    'cancellation guard must run before telemetry and all other error side effects'
  )
  assert.match(
    errorInterceptor,
    /axios\.isCancel\(error\)[\s\S]*error\?\.code\s*===\s*['"]ERR_CANCELED['"][\s\S]*error\?\.name\s*===\s*['"]CanceledError['"]/
  )
  assert.match(
    errorInterceptor,
    /if\s*\([^)]*axios\.isCancel\(error\)[\s\S]*?\)\s*\{\s*return Promise\.reject\(error\)\s*\}/
  )
})

test('request interceptor retains ordinary network and 401 handling', () => {
  assert.match(requestSource, /if\s*\(status\s*===\s*401\)[\s\S]*clearUserAuth\(\)[\s\S]*router\.replace\(['"]\/intro['"]\)[\s\S]*登录已过期，请重新登录/)
  assert.match(requestSource, /else\s*\{\s*ElMessage\.error\(extractErrorMessage\(error\)\s*\|\|\s*['"]网络错误，请检查网络连接['"]\)/)
  assert.match(requestSource, /return Promise\.reject\(error\)/)
})
