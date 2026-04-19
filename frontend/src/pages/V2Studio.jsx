import { useCallback, useEffect, useState } from 'react'
import { Activity, FlaskConical, Layers, Sparkles } from 'lucide-react'
import BrandSetup from '../components/v2/BrandSetup'
import AssetEditor from '../components/v2/AssetEditor'
import LayerEditor from '../components/v2/LayerEditor'
import PreferencesPanel from '../components/v2/PreferencesPanel'
import { getRetrievalPreview, v2Health } from '../services/apiV2'

/**
 * V2 Studio — brand-conditioned layer editing workbench.
 *
 * Layout:
 *   ┌──────────────┬────────────────────────────────────────────┐
 *   │  BrandSetup  │        Asset ingestion | Layer Editor      │
 *   │              ├────────────────────────────────────────────┤
 *   │ Preferences  │                                            │
 *   └──────────────┴────────────────────────────────────────────┘
 *
 * The Layer Editor is the core research loop:
 *   compose → click layer → brand-conditioned inpaint → measure metrics
 *   toggle ablation mode → re-run without graph conditioning → compare ΔE
 */
export default function V2Studio() {
  const [brandId, setBrandId] = useState(null)
  const [brandContext, setBrandContext] = useState(null)
  const [tab, setTab] = useState('layer')
  const [health, setHealth] = useState(null)
  const [refreshToken, setRefreshToken] = useState(0)

  useEffect(() => {
    v2Health()
      .then(setHealth)
      .catch((e) => setHealth({ status: 'unreachable', detail: e.message }))
  }, [])

  useEffect(() => {
    if (!brandId) {
      setBrandContext(null)
      return
    }
    getRetrievalPreview(brandId, 'digital')
      .then(setBrandContext)
      .catch(() => setBrandContext(null))
  }, [brandId, refreshToken])

  const bumpRefresh = useCallback(() => setRefreshToken((t) => t + 1), [])

  return (
    <div className="space-y-4">
      {/* Title strip */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Layers className="w-6 h-6 text-indigo-600" />
            Layer Studio
            <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-700 font-medium">
              Graph-RAG · brand-conditioned
            </span>
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Generate a composition → click any layer → edit it with brand conditioning → measure ΔE.
            Toggle ablation mode to compare with and without graph conditioning.
          </p>
        </div>
        <HealthBadge health={health} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[260px_1fr] gap-4">
        {/* Left rail */}
        <div className="space-y-4">
          <BrandSetup activeBrandId={brandId} onBrandSelected={setBrandId} />
          <PreferencesPanel brandId={brandId} refreshToken={refreshToken} />
        </div>

        {/* Right work surface */}
        <div className="space-y-4">
          <TabBar tab={tab} onTab={setTab} />

          {tab === 'layer' && (
            <LayerEditor
              brandId={brandId}
              brandContext={brandContext}
              onEditApplied={bumpRefresh}
            />
          )}

          {tab === 'assets' && <AssetEditor brandId={brandId} />}
        </div>
      </div>
    </div>
  )
}

function TabBar({ tab, onTab }) {
  const tabs = [
    { id: 'layer', label: 'Layer Editor', icon: Sparkles, desc: 'Core research loop' },
    { id: 'assets', label: 'Asset Ingestion', icon: Layers, desc: 'Brand kit upload' },
  ]
  return (
    <div className="bg-white rounded-xl shadow-sm p-1 flex gap-1">
      {tabs.map(({ id, label, icon: Icon, desc }) => (
        <button
          key={id}
          onClick={() => onTab(id)}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition flex-1 justify-center ${
            tab === id
              ? 'bg-indigo-50 text-indigo-700'
              : 'text-gray-500 hover:bg-gray-50 hover:text-gray-700'
          }`}
        >
          <Icon className="w-4 h-4" />
          {label}
          <span className="text-xs opacity-60 font-normal hidden sm:inline">· {desc}</span>
        </button>
      ))}
    </div>
  )
}

function HealthBadge({ health }) {
  if (!health)
    return (
      <span className="text-xs text-gray-400 flex items-center gap-1">
        <Activity className="w-3 h-3" /> checking…
      </span>
    )
  const ok = health.status === 'ok' || health.status === 'healthy'
  const mock = health.mock_mode ?? health.mock ?? false
  return (
    <span
      className={`text-xs px-2 py-1 rounded-full border flex items-center gap-2 ${
        ok ? 'border-green-200 bg-green-50 text-green-700' : 'border-red-200 bg-red-50 text-red-700'
      }`}
    >
      <Activity className="w-3 h-3" />
      V2 {health.status}
      {mock !== undefined && ` · mock=${String(mock)}`}
    </span>
  )
}
