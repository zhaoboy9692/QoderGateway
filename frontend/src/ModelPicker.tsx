import { RefreshCw } from 'lucide-react'

export interface ModelOption { id: string; name: string }

const tierNames: Record<string, string> = {
  auto: '自动（Auto）', lite: '轻量（Lite）', efficient: '高效（Efficient）',
  performance: '性能（Performance）', ultimate: '极致（Ultimate）',
}

export function ModelPicker({ models, value, onChange, loading, error, onRefresh, lang, disabled }: {
  models: ModelOption[]; value: string; onChange: (value: string) => void
  loading: boolean; error: string; onRefresh: () => void; lang: 'zh' | 'en'; disabled: boolean
}) {
  const zh = lang === 'zh'
  return <div className="space-y-3">
    <div className="flex items-center justify-between gap-2">
      <label htmlFor="chat-model" className="font-bold text-ink">{zh ? '模型配置' : 'Model Configuration'}</label>
      <button type="button" onClick={onRefresh} disabled={loading || disabled} className="flex items-center gap-1 text-xs text-body hover:text-ink disabled:opacity-50">
        <RefreshCw size={14} className={loading ? 'animate-spin' : ''} aria-hidden="true" />
        {loading ? (zh ? '加载中…' : 'Loading…') : (zh ? '刷新模型' : 'Refresh models')}
      </button>
    </div>
    <select id="chat-model" value={models.length ? value : ''} onChange={e => onChange(e.target.value)} disabled={loading || disabled || !models.length}
      className="w-full bg-white border border-hairline-strong text-ink text-sm px-3 py-3 rounded-lg outline-none focus:ring-2 focus:ring-ink/10 disabled:opacity-50">
      {!models.length && <option value="">{loading ? (zh ? '正在加载模型…' : 'Loading models…') : (zh ? '暂无可用模型列表' : 'No model list available')}</option>}
      {models.map(model => <option key={model.id} value={model.id}>{zh ? tierNames[model.id] || model.name : model.name}</option>)}
    </select>
    <div role="status" aria-live="polite" className={`text-xs ${error ? 'text-red-600' : 'text-body'}`}>
      {error || (loading ? (zh ? '正在读取网关模型列表…' : 'Loading gateway model catalog…') : (zh ? `已加载 ${models.length} 个模型` : `${models.length} models loaded`))}
    </div>
    {models.some(model => model.id === value) && <p className="text-xs text-body break-all">{zh ? '请求模型：' : 'Request model: '}<code>{value}</code></p>}
  </div>
}
