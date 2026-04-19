import { useEffect, useState } from 'react'
import { Plus, Building2, Copy, CheckCircle2 } from 'lucide-react'
import {
  createV2Brand,
  getV2Brand,
  listLocalV2Brands,
  recordLocalV2Brand,
} from '../../services/apiV2'

/**
 * Brand setup panel for the V2 Studio.
 *
 * The V2 backend intentionally doesn't expose a brand-list endpoint (brand
 * discovery is a separate concern), so we track brand IDs the current user
 * has created in localStorage and hydrate each one on mount.
 */
export default function BrandSetup({ activeBrandId, onBrandSelected }) {
  const [brands, setBrands] = useState([])
  const [loading, setLoading] = useState(false)
  const [creating, setCreating] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({
    name: '',
    primary: '#ff3344, #ffffff',
    secondary: '#0b0b0b',
    accent: '',
    voice: 'bold, confident, modern',
    description: '',
  })
  const [error, setError] = useState(null)

  useEffect(() => {
    const ids = listLocalV2Brands()
    if (!ids.length) return
    setLoading(true)
    Promise.all(
      ids.map((id) => getV2Brand(id).then((d) => d.brand).catch(() => null))
    )
      .then((rows) => setBrands(rows.filter(Boolean)))
      .finally(() => setLoading(false))
  }, [])

  const handleCreate = async (e) => {
    e.preventDefault()
    setError(null)
    setCreating(true)
    try {
      const parseList = (s) =>
        s.split(',').map((x) => x.trim()).filter(Boolean)
      const resp = await createV2Brand({
        name: form.name,
        primary_hex: parseList(form.primary),
        secondary_hex: parseList(form.secondary),
        accent_hex: parseList(form.accent),
        voice_keywords: parseList(form.voice),
        description: form.description || null,
      })
      recordLocalV2Brand(resp.brand_id)
      const full = await getV2Brand(resp.brand_id)
      setBrands((prev) => [full.brand, ...prev])
      onBrandSelected(resp.brand_id)
      setShowForm(false)
      setForm((f) => ({ ...f, name: '', description: '' }))
    } catch (err) {
      setError(err.message)
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="bg-white rounded-xl shadow-sm p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <Building2 className="w-5 h-5 text-primary-600" /> V2 Brands
        </h2>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="text-sm text-primary-600 hover:underline flex items-center gap-1"
        >
          <Plus className="w-4 h-4" /> New brand
        </button>
      </div>

      {loading && (
        <div className="text-sm text-gray-500">Loading brands…</div>
      )}

      {brands.length === 0 && !loading && !showForm && (
        <p className="text-sm text-gray-500">
          No V2 brands yet. Create one to start ingesting assets.
        </p>
      )}

      <ul className="space-y-1">
        {brands.map((b) => {
          const isActive = b.id === activeBrandId
          return (
            <li key={b.id}>
              <button
                onClick={() => onBrandSelected(b.id)}
                className={`w-full text-left px-3 py-2 rounded-lg border transition ${
                  isActive
                    ? 'border-primary-500 bg-primary-50'
                    : 'border-gray-200 hover:bg-gray-50'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium text-gray-900">{b.name}</span>
                  {isActive && (
                    <CheckCircle2 className="w-4 h-4 text-primary-600" />
                  )}
                </div>
                <div className="flex items-center gap-2 mt-1">
                  {(b.primary_hex || []).slice(0, 4).map((hx) => (
                    <span
                      key={hx}
                      className="w-4 h-4 rounded border border-gray-200"
                      style={{ backgroundColor: hx }}
                      title={hx}
                    />
                  ))}
                  <span className="text-xs text-gray-400 font-mono truncate">
                    {b.id.slice(0, 8)}
                    <CopyId value={b.id} />
                  </span>
                </div>
              </button>
            </li>
          )
        })}
      </ul>

      {showForm && (
        <form
          onSubmit={handleCreate}
          className="space-y-2 border-t border-gray-100 pt-3"
        >
          <input
            className="input"
            placeholder="Brand name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            required
          />
          <input
            className="input"
            placeholder="Primary hex (comma-separated)"
            value={form.primary}
            onChange={(e) => setForm({ ...form, primary: e.target.value })}
          />
          <input
            className="input"
            placeholder="Secondary hex"
            value={form.secondary}
            onChange={(e) => setForm({ ...form, secondary: e.target.value })}
          />
          <input
            className="input"
            placeholder="Accent hex"
            value={form.accent}
            onChange={(e) => setForm({ ...form, accent: e.target.value })}
          />
          <input
            className="input"
            placeholder="Voice keywords"
            value={form.voice}
            onChange={(e) => setForm({ ...form, voice: e.target.value })}
          />
          <textarea
            className="input"
            rows={2}
            placeholder="Description (optional)"
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
          />
          {error && <div className="text-sm text-red-600">{error}</div>}
          <button
            type="submit"
            disabled={creating}
            className="btn-primary w-full"
          >
            {creating ? 'Creating…' : 'Create brand'}
          </button>
        </form>
      )}
    </div>
  )
}

function CopyId({ value }) {
  const [copied, setCopied] = useState(false)
  return (
    <button
      type="button"
      onClick={(e) => {
        e.stopPropagation()
        navigator.clipboard.writeText(value)
        setCopied(true)
        setTimeout(() => setCopied(false), 1500)
      }}
      className="ml-1 text-gray-400 hover:text-gray-600"
      aria-label="Copy brand id"
    >
      {copied ? <CheckCircle2 className="inline w-3 h-3" /> : <Copy className="inline w-3 h-3" />}
    </button>
  )
}
