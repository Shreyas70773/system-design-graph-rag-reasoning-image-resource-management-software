import { Component, Suspense, useEffect, useMemo, useRef, useState } from 'react'
import { Canvas, useLoader } from '@react-three/fiber'
import {
  OrbitControls,
  Environment,
  Grid,
  Html,
  Bounds,
} from '@react-three/drei'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader'
import { Upload, CheckCircle2, XCircle, RefreshCw, Loader2, AlertTriangle } from 'lucide-react'
import {
  approveAsset,
  getAsset,
  ingestAsset,
  listAssets,
  rejectAsset,
  regeneratePart,
  resolveAssetUrl,
  v2Health,
} from '../../services/apiV2'

/**
 * AssetEditor — Pipeline A UI.
 *
 * Surfaces:
 *   1. An upload tile that ingests a single 2D image → triggers the 7-step
 *      Pipeline A orchestrator synchronously (mock mode) and pushes a fresh
 *      asset card onto the list.
 *   2. An asset list grouped by ingestion status (pending / awaiting_approval
 *      / approved / rejected).
 *   3. A 3D viewer for the selected asset's canonical mesh (R3F + GLTF).
 *   4. A semantic-parts panel with per-part regenerate.
 *   5. Approve / Reject actions that hit the Pipeline C applier under the
 *      hood, so every decision becomes a graph-visible Interaction.
 */
export default function AssetEditor({ brandId }) {
  const [assets, setAssets] = useState([])
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [selectedId, setSelectedId] = useState(null)
  const [detail, setDetail] = useState(null)
  const [statusMsg, setStatusMsg] = useState(null)
  const [error, setError] = useState(null)
  const [assetType, setAssetType] = useState('product')
  const [meshBackend, setMeshBackend] = useState(null)

  useEffect(() => {
    v2Health().then((h) => setMeshBackend(h.mesh_backend)).catch(() => {})
  }, [])

  const refreshList = async () => {
    if (!brandId) return
    setLoading(true)
    try {
      const rows = await listAssets(brandId)
      setAssets(rows)
      if (!selectedId && rows.length) setSelectedId(rows[0].id)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    setAssets([])
    setDetail(null)
    setSelectedId(null)
    if (brandId) refreshList()
  }, [brandId])

  useEffect(() => {
    if (!selectedId) {
      setDetail(null)
      return
    }
    getAsset(selectedId).then(setDetail).catch((e) => setError(e.message))
  }, [selectedId])

  const handleUpload = async (file) => {
    if (!file || !brandId) return
    setError(null)
    setUploading(true)
    setStatusMsg('Reading file…')
    try {
      const dataUrl = await fileToDataUrl(file)
      const meshLabel = meshBackend === 'tripo' ? 'TripoAI'
                      : meshBackend === 'meshy' ? 'Meshy'
                      : 'depth-preview'
      setStatusMsg(`Pipeline A: describe → segment → delight → 3D mesh (${meshLabel}, ~30-90s for cloud) → validate…`)
      const resp = await ingestAsset({
        brandId,
        assetType,
        sourceImageUrl: dataUrl,
        sync: true,
      })
      setStatusMsg(`Ingested ${resp.asset_id?.slice(0, 8)} (${resp.status})`)
      await refreshList()
      setSelectedId(resp.asset_id)
    } catch (e) {
      setError(e.message)
    } finally {
      setUploading(false)
      setTimeout(() => setStatusMsg(null), 4000)
    }
  }

  const handleApprove = async () => {
    if (!selectedId) return
    await approveAsset(selectedId)
    await refreshList()
    const fresh = await getAsset(selectedId)
    setDetail(fresh)
  }

  const handleReject = async () => {
    if (!selectedId) return
    const reason = window.prompt('Reason for rejection?', 'mesh seams visible')
    await rejectAsset(selectedId, reason || undefined)
    await refreshList()
    const fresh = await getAsset(selectedId)
    setDetail(fresh)
  }

  const handleRegeneratePart = async (partId) => {
    if (!selectedId) return
    await regeneratePart(selectedId, partId)
    setStatusMsg(`Queued regenerate for part ${partId.slice(0, 8)}`)
    setTimeout(() => setStatusMsg(null), 3000)
  }

  if (!brandId) {
    return (
      <div className="bg-white rounded-xl shadow-sm p-6 text-gray-500">
        Select a brand to ingest assets.
      </div>
    )
  }

  // Schema field is `file_url` (Mesh3D.file_url in schema_v2.py).
  const meshUrl = detail?.geometry?.[0]?.file_url
  const parts = detail?.parts || []
  const statusPill = detail?.asset?.ingestion_status

  return (
    <div className="bg-white rounded-xl shadow-sm p-4 space-y-4">
      <header className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Asset Editor</h2>
        <div className="flex items-center gap-3">
          <MeshBackendBadge backend={meshBackend} />
          <button
            onClick={refreshList}
            className="text-sm text-gray-500 hover:text-gray-800 flex items-center gap-1"
          >
            <RefreshCw className="w-4 h-4" /> Refresh
          </button>
        </div>
      </header>

      {meshBackend === 'depth-preview' && (
        <div className="flex items-start gap-2 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 text-xs text-amber-800">
          <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
          <div>
            <strong>Depth-preview mode</strong> — no API key configured. Models will be a 3-D depth-displaced surface, not a full reconstruction.{' '}
            Set <code className="bg-amber-100 px-1 rounded">TRIPO_API_KEY</code> (free at{' '}
            <a href="https://platform.tripo3d.ai" target="_blank" rel="noreferrer" className="underline">tripo3d.ai</a>)
            {' '}or <code className="bg-amber-100 px-1 rounded">MESHY_API_KEY</code> (free at{' '}
            <a href="https://meshy.ai" target="_blank" rel="noreferrer" className="underline">meshy.ai</a>)
            {' '}in the backend environment then restart.
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-[240px_1fr] gap-4">
        {/* Asset list */}
        <div className="space-y-2">
          <UploadTile
            uploading={uploading}
            statusMsg={statusMsg}
            assetType={assetType}
            onAssetType={setAssetType}
            onUpload={handleUpload}
          />
          {loading && <div className="text-sm text-gray-500">Loading…</div>}
          {error && <div className="text-sm text-red-600">{error}</div>}
          <div className="space-y-1 max-h-[420px] overflow-y-auto">
            {assets.length === 0 && !loading && (
              <p className="text-xs text-gray-400">No assets yet.</p>
            )}
            {assets.map((a) => (
              <button
                key={a.id}
                onClick={() => setSelectedId(a.id)}
                className={`w-full text-left px-3 py-2 rounded border text-sm ${
                  a.id === selectedId
                    ? 'border-primary-500 bg-primary-50'
                    : 'border-gray-200 hover:bg-gray-50'
                }`}
              >
                <div className="flex justify-between items-center">
                  <span className="font-mono text-xs">{a.id.slice(0, 8)}</span>
                  <StatusPill status={a.ingestion_status} />
                </div>
                <div className="text-xs text-gray-500 mt-1">{a.asset_type}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Detail pane */}
        <div className="space-y-3">
          <div className="relative rounded-lg overflow-hidden border border-gray-200 bg-slate-900 h-[360px]">
            {detail ? (
              <MeshViewer meshUrl={resolveAssetUrl(meshUrl)} />
            ) : (
              <div className="h-full grid place-items-center text-slate-400 text-sm">
                Upload or select an asset to preview its 3D geometry.
              </div>
            )}
          </div>

          {detail && (
            <div className="flex flex-wrap items-center gap-3">
              <StatusPill status={statusPill} />
              <span className="text-xs text-gray-500 font-mono">
                {detail.asset?.id}
              </span>
              {statusPill === 'awaiting_approval' && (
                <>
                  <button
                    onClick={handleApprove}
                    className="btn-primary text-sm px-3 py-1.5 flex items-center gap-1"
                  >
                    <CheckCircle2 className="w-4 h-4" /> Approve
                  </button>
                  <button
                    onClick={handleReject}
                    className="btn-secondary text-sm px-3 py-1.5 flex items-center gap-1"
                  >
                    <XCircle className="w-4 h-4" /> Reject
                  </button>
                </>
              )}
            </div>
          )}

          {parts.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-2">
                Semantic parts ({parts.length})
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                {parts.map((p) => (
                  <div
                    key={p.id}
                    className="border border-gray-200 rounded p-2 text-xs space-y-1"
                  >
                    <div className="font-medium text-gray-800">{p.name}</div>
                    <div className="text-gray-500">{p.part_type}</div>
                    {p.mask_url && (
                      <img
                        src={resolveAssetUrl(p.mask_url)}
                        alt={p.name}
                        className="w-full h-16 object-contain bg-gray-100 rounded"
                      />
                    )}
                    <button
                      onClick={() => handleRegeneratePart(p.id)}
                      className="w-full text-[11px] text-primary-600 hover:underline"
                    >
                      Regenerate part
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function UploadTile({ uploading, statusMsg, assetType, onAssetType, onUpload }) {
  const inputRef = useRef(null)

  const handleDrop = (e) => {
    e.preventDefault()
    const f = e.dataTransfer.files?.[0]
    if (f && !uploading) onUpload(f)
  }

  return (
    <div className="space-y-2">
      {/* Drop zone — clicking this div opens the file picker */}
      <div
        role="button"
        tabIndex={0}
        onClick={() => !uploading && inputRef.current?.click()}
        onKeyDown={(e) => e.key === 'Enter' && !uploading && inputRef.current?.click()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-lg p-4 text-center cursor-pointer transition select-none ${
          uploading
            ? 'border-primary-400 bg-primary-50 cursor-not-allowed'
            : 'border-gray-300 hover:border-primary-400 hover:bg-gray-50'
        }`}
      >
        <div className="flex flex-col items-center gap-1 pointer-events-none">
          {uploading ? (
            <Loader2 className="w-5 h-5 text-primary-600 animate-spin" />
          ) : (
            <Upload className="w-5 h-5 text-gray-400" />
          )}
          <span className="text-xs font-medium text-gray-700">
            {uploading ? 'Ingesting…' : 'Click or drop image to ingest'}
          </span>
          {statusMsg && (
            <span className="text-[11px] text-gray-500 mt-1">{statusMsg}</span>
          )}
        </div>
      </div>

      {/* Asset type selector — outside the drop zone so it never interferes */}
      <select
        className="text-xs border border-gray-200 rounded px-2 py-1.5 w-full"
        value={assetType}
        onChange={(e) => onAssetType(e.target.value)}
        disabled={uploading}
      >
        <option value="product">product</option>
        <option value="logo">logo</option>
        <option value="character">character</option>
        <option value="prop">prop</option>
        <option value="background">background</option>
      </select>

      {/* Hidden real file input */}
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        className="hidden"
        disabled={uploading}
        onChange={(e) => {
          const f = e.target.files?.[0]
          if (f) onUpload(f)
          e.target.value = ''
        }}
      />
    </div>
  )
}

function MeshBackendBadge({ backend }) {
  if (!backend) return null
  const map = {
    'tripo':         { cls: 'bg-green-50 border-green-300 text-green-800',  label: '3D: TripoAI' },
    'meshy':         { cls: 'bg-blue-50 border-blue-300 text-blue-800',    label: '3D: Meshy' },
    'depth-preview': { cls: 'bg-amber-50 border-amber-300 text-amber-800', label: '3D: depth-preview' },
  }
  const { cls, label } = map[backend] || { cls: 'bg-gray-100 text-gray-600', label: `3D: ${backend}` }
  return (
    <span className={`text-[10px] font-medium px-2 py-1 rounded-full border ${cls}`}>
      {label}
    </span>
  )
}

function StatusPill({ status }) {
  if (!status) return null
  const map = {
    pending: 'bg-gray-100 text-gray-600',
    describing: 'bg-blue-100 text-blue-700',
    segmenting: 'bg-blue-100 text-blue-700',
    delighting: 'bg-blue-100 text-blue-700',
    meshing: 'bg-blue-100 text-blue-700',
    validating: 'bg-blue-100 text-blue-700',
    awaiting_approval: 'bg-yellow-100 text-yellow-800',
    approved: 'bg-green-100 text-green-800',
    rejected: 'bg-red-100 text-red-800',
    failed: 'bg-red-100 text-red-800',
  }
  const cls = map[status] || 'bg-gray-100 text-gray-700'
  return (
    <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${cls}`}>
      {status}
    </span>
  )
}

class GlbErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { failed: false, error: null }
  }
  static getDerivedStateFromError(error) {
    return { failed: true, error }
  }
  render() {
    if (this.state.failed) {
      return (
        <Html center>
          <div className="bg-slate-800 text-slate-300 text-xs rounded px-3 py-2 max-w-[220px] text-center">
            GLB load failed — showing wireframe.
            <br />
            <span className="text-slate-500">{String(this.state.error?.message || '').slice(0, 80)}</span>
          </div>
        </Html>
      )
    }
    return this.props.children
  }
}

function MeshViewer({ meshUrl }) {
  return (
    <Canvas camera={{ position: [2.4, 1.8, 2.4], fov: 45 }} shadows={false} dpr={[1, 1.5]}>
      <color attach="background" args={["#0f172a"]} />
      <ambientLight intensity={0.6} />
      <directionalLight position={[5, 5, 5]} intensity={1.0} />
      <Suspense fallback={<Html center><span className="text-white text-xs">Loading mesh…</span></Html>}>
        <GlbErrorBoundary>
          <Bounds fit clip observe margin={1.2}>
            {meshUrl ? <GlbMesh url={meshUrl} /> : <PlaceholderCube />}
          </Bounds>
        </GlbErrorBoundary>
        <Environment preset="studio" />
      </Suspense>
      <Grid args={[10, 10]} cellColor="#334155" sectionColor="#475569" infiniteGrid fadeDistance={20} />
      <OrbitControls makeDefault enableDamping />
    </Canvas>
  )
}

function GlbMesh({ url }) {
  const gltf = useLoader(GLTFLoader, url)
  const scene = useMemo(() => gltf.scene.clone(true), [gltf])
  return <primitive object={scene} />
}

function PlaceholderCube() {
  return (
    <mesh castShadow receiveShadow>
      <boxGeometry args={[1, 1, 1]} />
      <meshStandardMaterial color="#64748b" roughness={0.6} metalness={0.1} />
    </mesh>
  )
}

function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result)
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}
