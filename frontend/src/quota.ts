export interface CreditPool {
  total?: number
  cap?: number
  used?: number
  remaining?: number
  percentage?: number
  available?: boolean
}
export interface AccountQuota {
  uid: string
  name?: string
  ok: boolean
  error?: string
  quota?: { userQuota?: CreditPool; orgResourcePackage?: CreditPool }
}
export interface QuotaRow {
  kind: 'subscription' | 'resource'
  total?: number
  used?: number
  remaining?: number
  percentage?: number
  available?: boolean
}
const number = (value: unknown): number | undefined =>
  typeof value === 'number' && Number.isFinite(value) ? value : undefined

export function quotaRows(quota: AccountQuota['quota']): QuotaRow[] {
  return (['subscription', 'resource'] as const).map(kind => {
    const pool = (kind === 'subscription' ? quota?.userQuota : quota?.orgResourcePackage) || {}
    const total = number(kind === 'resource' ? pool.cap ?? pool.total : pool.total)
    const used = number(pool.used)
    const remaining = number(pool.remaining)
    const percentage = total !== undefined && total > 0 && used !== undefined
      ? used / total : number(pool.percentage)
    return { kind, total, used, remaining, percentage, available: pool.available }
  })
}
