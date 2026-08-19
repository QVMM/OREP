import assert from 'node:assert/strict'
import { batchDeleteSummary, idsFromRows } from '../src/utils/batchDelete.js'

assert.deepEqual(idsFromRows([{ id: 1 }, { id: 2 }, { id: 1 }, { id: null }, {}]), [1, 2])

assert.deepEqual(batchDeleteSummary({ data: { deleted: 3, failed: [] } }, '用户'), {
  type: 'success',
  message: '已删除 3 条用户'
})

assert.deepEqual(batchDeleteSummary({ deleted: 2, failed: [{ id: 9, reason: '不存在' }] }, '课程'), {
  type: 'warning',
  message: '已删除 2 条课程，1 条失败'
})
