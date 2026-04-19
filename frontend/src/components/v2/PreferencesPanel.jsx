import { useCallback, useEffect, useState } from 'react'
import { Brain, RefreshCw, Trash2, ArrowUpRight, ArrowDownRight } from 'lucide-react'
import {
  deletePreference,
  getRetrievalPreview,
  listPreferences,
  listRecentInteractions,
} from '../../services/apiV2'

/**
 * PreferencesPanel — Pipeline C learning surface.
 *
 * Shows three things the user can reason about:
 *   1. Active preference signals learned from the distiller, with their raw
 *      weight + decayed strength.
 *   2. The compiled biases the scene assembler will receive on the next run.
 *   3. A stream of recent Interaction nodes so the user can see how their
 *      edits are shaping brand memory over time.
 */
export default function PreferencesPanel({ brandId, refreshToken }) {
  const [loading, setLoading] = useState(false)
  const [signals, setSignals] = useState([])
  const [biases, setBiases] = useState({})
  const [preview, setPreview] = useState(null)
  const [interactions, setInteractions] = useState([])
  const [error, setError] = useState(null)

  const refresh = useCallback(async () => {
    if (!brandId) return
    setLoading(true)
    setError(null)
    try {
      const [prefs, pv, rec] = await Promise.all([
        listPreferences(brandId),
        getRetrievalPreview(brandId, 'digital'),
        listRecentInteractions(brandId, 15),
      ])
      setSignals(prefs.signals || [])
      setBiases(prefs.compiled_biases || {})
      setPreview(pv)
      setInteractions(rec || [])
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [brandId])

  useEffect(() => {
    if (brandId) refresh()
  }, [brandId, refresh, refreshToken])

  const handleDelete = async (signalId) => {
    if (!brandId) return
    await deletePreference(brandId, signalId)
    refresh()
  }

  if (!brandId) {
    return (
      <div className="bg-white rounded-xl shadow-sm p-4 text-sm text-gray-500">
        Select a brand to view its learned preferences.
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl shadow-sm p-4 space-y-4">
      <header className="flex items-center justify-between">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <Brain className="w-5 h-5 text-primary-600" /> Learned preferences
        </h2>
        <button
          onClick={refresh}
          className="text-xs text-gray-500 hover:text-gray-800 flex items-center gap-1"
        >
          <RefreshCw className="w-3 h-3" /> Refresh
        </button>
      </header>
      {error && <div className="text-sm text-red-600">{error}</div>}

      {preview && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
          <StatTile label="Approved assets" value={preview.approved_assets} />
          <StatTile label="Total assets" value={preview.total_assets} />
          <StatTile label="Colors in graph" value={preview.colors?.length || 0} />
          <StatTile label="Active signals" value={signals.length} />
        </div>
      )}

      <section>
        <h3 className="text-sm font-semibold text-gray-700 mb-2">
          Active signals ({signals.length})
        </h3>
        {signals.length === 0 && (
          <p className="text-xs text-gray-500">
            No learned preferences yet. Edits flow through the distiller and
            will appear here once the threshold (3 repeats) is crossed.
          </p>
        )}
        <ul className="space-y-1.5">
          {signals.map((s) => (
            <li
              key={s.id}
              className="border border-gray-200 rounded px-3 py-2 text-xs flex items-start justify-between gap-3"
            >
              <div className="min-w-0">
                <div className="font-medium text-gray-800 truncate">
                  {s.kind} · {s.key}
                </div>
                <div className="text-gray-500 truncate">
                  {formatValue(s.value_json)}
                </div>
                <div className="text-[10px] text-gray-400 mt-1">
                  weight {Number(s.weight || 0).toFixed(2)} · occurrences{' '}
                  {s.occurrences ?? 0}
                </div>
              </div>
              <button
                onClick={() => handleDelete(s.id)}
                className="text-gray-400 hover:text-red-600"
                aria-label="Delete preference"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h3 className="text-sm font-semibold text-gray-700 mb-2">
          Compiled biases
        </h3>
        {Object.keys(biases).length === 0 ? (
          <p className="text-xs text-gray-500">
            No biases compiled yet — the scene assembler will run on
            defaults.
          </p>
        ) : (
          <pre className="text-[11px] bg-gray-50 border border-gray-200 rounded p-2 max-h-40 overflow-auto">
            {JSON.stringify(biases, null, 2)}
          </pre>
        )}
      </section>

      <section>
        <h3 className="text-sm font-semibold text-gray-700 mb-2">
          Recent interactions ({interactions.length})
        </h3>
        {interactions.length === 0 && (
          <p className="text-xs text-gray-500">No interactions recorded yet.</p>
        )}
        <ul className="space-y-1">
          {interactions.map((i) => (
            <li
              key={i.id}
              className="border border-gray-100 rounded px-2 py-1.5 text-xs flex items-center gap-2"
            >
              {i.action?.startsWith('approve') ? (
                <ArrowUpRight className="w-3.5 h-3.5 text-green-600 flex-shrink-0" />
              ) : i.action?.startsWith('reject') ? (
                <ArrowDownRight className="w-3.5 h-3.5 text-red-600 flex-shrink-0" />
              ) : (
                <span className="w-1.5 h-1.5 rounded-full bg-blue-500 flex-shrink-0" />
              )}
              <span className="font-mono text-[11px] text-gray-700">
                {i.action}
              </span>
              <span className="text-gray-500 truncate">
                → {i.target_kind}:{(i.target_id || '').slice(0, 8)}
              </span>
              <span className="ml-auto text-[10px] text-gray-400">
                {formatTimestamp(i.created_at)}
              </span>
            </li>
          ))}
        </ul>
      </section>

      {loading && (
        <div className="text-xs text-gray-500">Refreshing…</div>
      )}
    </div>
  )
}

function StatTile({ label, value }) {
  return (
    <div className="border border-gray-200 rounded px-2 py-1.5">
      <div className="text-[10px] uppercase tracking-wide text-gray-500">
        {label}
      </div>
      <div className="text-lg font-semibold text-gray-800">{value}</div>
    </div>
  )
}

function formatValue(v) {
  if (v == null) return ''
  if (typeof v === 'string') {
    try {
      const parsed = JSON.parse(v)
      return JSON.stringify(parsed)
    } catch {
      return v
    }
  }
  try {
    return JSON.stringify(v)
  } catch {
    return String(v)
  }
}

function formatTimestamp(ts) {
  if (!ts) return ''
  try {
    const d = new Date(ts)
    if (Number.isNaN(+d)) return ''
    const now = new Date()
    const diff = (now - d) / 1000
    if (diff < 60) return `${Math.floor(diff)}s`
    if (diff < 3600) return `${Math.floor(diff / 60)}m`
    if (diff < 86400) return `${Math.floor(diff / 3600)}h`
    return d.toLocaleDateString()
  } catch {
    return ''
  }
}
