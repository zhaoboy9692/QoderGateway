import React from 'react'
import { quotaRows, type AccountQuota } from './quota'

export function QuotaTable({ entries, lang }: { entries: AccountQuota[]; lang: 'zh' | 'en' }) {
  const zh = lang === 'zh'
  const amount = (value?: number) => value === undefined ? '—' : value.toLocaleString(zh ? 'zh-CN' : 'en-US', { maximumFractionDigits: 2 })
  const headers = zh ? ['账号', '资源类型', '总额度', '已使用', '剩余', '使用率'] : ['Account', 'Resource', 'Total', 'Used', 'Remaining', 'Usage']
  return <div className="overflow-x-auto">
    <table className="w-full text-left">
      <thead className="bg-canvas-soft border-b border-hairline"><tr>
        {headers.map(h => <th key={h} className="px-6 py-3 text-[10px] font-semibold text-body uppercase tracking-wider whitespace-nowrap">{h}</th>)}
      </tr></thead>
      <tbody className="divide-y divide-hairline">
        {entries.map(q => {
          const name = q.name || q.uid.slice(0, 12)
          if (!q.ok || !q.quota) return <tr key={q.uid}>
            <td className="px-6 py-4 font-semibold text-ink">{name}</td>
            <td colSpan={5} className="px-6 py-4 text-xs text-red-600">{q.error || (zh ? '额度查询失败，请刷新重试' : 'Quota unavailable; refresh to retry')}</td>
          </tr>
          return quotaRows(q.quota).map((row, index) => {
            const percentage = row.percentage === undefined ? undefined : Math.max(0, Math.min(100, row.percentage * 100))
            return <tr key={`${q.uid}-${row.kind}`} className="hover:bg-canvas-soft transition-colors">
              {index === 0 && <td rowSpan={2} className="px-6 py-4 font-semibold text-ink align-top">{name}</td>}
              <td className="px-6 py-4 text-xs text-ink whitespace-nowrap">
                {row.kind === 'subscription' ? (zh ? '订阅席位' : 'Subscription seat') : (zh ? '资源包（组织共享）' : 'Resource package (shared)')}
                {row.available === false && <span className="block mt-1 text-body">{zh ? '当前不可用' : 'Currently unavailable'}</span>}
              </td>
              <td className="px-6 py-4 font-mono text-xs text-body">{amount(row.total)}</td>
              <td className="px-6 py-4 font-mono text-xs text-body">{amount(row.used)}</td>
              <td className={`px-6 py-4 font-mono text-xs ${row.remaining === 0 ? 'text-red-600 font-bold' : 'text-body'}`}>{amount(row.remaining)}</td>
              <td className="px-6 py-4">
                {percentage === undefined ? <span className="text-xs text-body">—</span> : <>
                  <span className="block text-xs font-mono text-body mb-1">{percentage.toFixed(1)}%</span>
                  <div className="w-24 h-1.5 bg-hairline-strong rounded-full overflow-hidden" role="progressbar" aria-label={row.kind} aria-valuenow={percentage} aria-valuemin={0} aria-valuemax={100}>
                    <div className={`h-full ${percentage > 80 ? 'bg-red-500' : 'bg-mint'}`} style={{ width: `${percentage}%` }} />
                  </div>
                </>}
              </td>
            </tr>
          })
        })}
        {entries.length === 0 && <tr><td colSpan={6} className="py-6 text-center text-xs text-body">{zh ? '暂无账号' : 'No accounts'}</td></tr>}
      </tbody>
    </table>
    <p className="px-6 py-3 text-xs text-body border-t border-hairline">{zh ? '资源包为组织共享额度，同一组织的账号请勿重复相加。— 表示上游未提供数据。' : 'Resource packages are shared within an organization; do not sum them across its accounts. — means data was not provided.'}</p>
  </div>
}
