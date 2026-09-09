import test from 'node:test'
import assert from 'node:assert/strict'
import { quotaRows } from '../src/quota.ts'

test('subscription exhaustion does not hide remaining resource credits', () => {
  const rows = quotaRows({ userQuota: { total: 6000, used: 6000, remaining: 0 }, orgResourcePackage: { cap: 14000, used: 5030, remaining: 8970, available: true } })
  assert.equal(rows.length, 2)
  assert.deepEqual(rows.map(r => [r.kind, r.total, r.used, r.remaining]), [['subscription', 6000, 6000, 0], ['resource', 14000, 5030, 8970]])
  assert.equal(rows[1].percentage, 5030 / 14000)
})
test('missing package is unknown, not zero available credits', () => {
  const rows = quotaRows({userQuota: {total: 6000, remaining: 42}})
  assert.equal(rows[1].total, undefined)
  assert.equal(rows[1].remaining, undefined)
  assert.equal(rows[1].percentage, undefined)
})
test('unavailable and exhausted packages retain explicit state and zeros', () => {
  const row = quotaRows({orgResourcePackage: {cap: 100, used: 100, remaining: 0, available: false}})[1]
  assert.equal(row.available, false)
  assert.equal(row.remaining, 0)
  assert.equal(row.percentage, 1)
})
