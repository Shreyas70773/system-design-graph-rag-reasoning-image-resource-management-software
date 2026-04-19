import { Suspense, useEffect, useRef, useState } from 'react'
import { Canvas } from '@react-three/fiber'
import {
  OrbitControls,
  TransformControls,
  Environment,
  Grid,
  Html,
} from '@react-three/drei'
import {
  Camera as CameraIcon,
  Loader2,
  MousePointer2,
  Send,
  Sparkles,
  Image as ImageIcon,
  MoveDiagonal,
  RotateCw,
  Scaling,
} from 'lucide-react'
import {
  createScene,
  getScene,
  rerenderScene,
  resolveAssetUrl,
  resolveObjectAtPixel,
  sendNlInteraction,
  sendStructuredInteraction,
} from '../../services/apiV2'

const DEFAULT_CAMERAS = [
  { shot_type: 'hero', aspect_ratio: '1:1' },
  { shot_type: 'detail', aspect_ratio: '1:1' },
  { shot_type: 'wide', aspect_ratio: '16:9' },
]

/**
 * ScenePanel — Pipeline B (authoring + render) + Pipeline C (edit) UI.
 *
 * Flow:
 *   1. User describes intent, picks 1–N camera shots, hits "Create scene".
 *   2. The backend runs ScenePipeline.create_and_render synchronously (mock
 *      mode), returning the full scene graph and a render per camera.
 *   3. The 3D canvas renders each placement as an editable cube with
 *      TransformControls; dragging issues a MOVE_OBJECT structured interaction
 *      which feeds Pipeline C's distiller.
 *   4. The render strip lets the user click a 2D image — the object-ID pass
 *      resolves the pixel to a placement, and NL commands are routed through
 *      /api/v2/interactions/natural-language.
 */
export default function ScenePanel({ brandId, brandContext, onInteractionApplied }) {
  const [intent, setIntent] = useState(
    'Hero shot of the flagship product on a clean studio backdrop with the tagline "Bold."'
  )
  const [deployment, setDeployment] = useState('digital')
  const [cameras, setCameras] = useState(DEFAULT_CAMERAS)
  const [creating, setCreating] = useState(false)
  const [scene, setScene] = useState(null)
  const [selectedPlacementId, setSelectedPlacementId] = useState(null)
  const [selectedRenderIdx, setSelectedRenderIdx] = useState(0)
  const [nlText, setNlText] = useState('')
  const [nlBusy, setNlBusy] = useState(false)
  const [nlResult, setNlResult] = useState(null)
  const [error, setError] = useState(null)
  const [transformMode, setTransformMode] = useState('translate')

  const reloadScene = async (sceneId) => {
    const fresh = await getScene(sceneId)
    setScene(fresh)
  }

  const handleCreate = async (e) => {
    e?.preventDefault?.()
    if (!brandId) return
    setCreating(true)
    setError(null)
    try {
      const resp = await createScene({
        brandId,
        intentText: intent,
        deploymentContext: deployment,
        cameras,
        sync: true,
      })
      if (!resp.scene_id) throw new Error('Scene create returned no scene_id')
      await reloadScene(resp.scene_id)
      setSelectedRenderIdx(0)
    } catch (err) {
      setError(err.message)
    } finally {
      setCreating(false)
    }
  }

  const handleRerender = async (cameraIds = null) => {
    if (!scene?.scene?.id) return
    setCreating(true)
    try {
      await rerenderScene(scene.scene.id, cameraIds)
      // Rerender is async (queued). Poll scene a few times to surface new renders.
      for (let i = 0; i < 8; i++) {
        await new Promise((r) => setTimeout(r, 800))
        const fresh = await getScene(scene.scene.id)
        if ((fresh.renders?.length || 0) !== (scene.renders?.length || 0)) {
          setScene(fresh)
          break
        }
        if (i === 7) setScene(fresh)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setCreating(false)
    }
  }

  const applyStructured = async (payload) => {
    if (!brandId) return
    try {
      const resp = await sendStructuredInteraction({ brand_id: brandId, ...payload })
      onInteractionApplied?.(resp)
      if (scene?.scene?.id) await reloadScene(scene.scene.id)
    } catch (err) {
      setError(err.message)
    }
  }

  const applyNl = async (e) => {
    e?.preventDefault?.()
    if (!brandId || !scene?.scene?.id || !nlText.trim()) return
    setNlBusy(true)
    setError(null)
    try {
      const render = scene.renders?.[selectedRenderIdx]
      const resp = await sendNlInteraction({
        brand_id: brandId,
        scene_id: scene.scene.id,
        text: nlText,
        selected_placement_ids: selectedPlacementId ? [selectedPlacementId] : [],
        selected_text_ids: [],
        last_render_url: render?.rgb_url || null,
      })
      setNlResult(resp)
      if (resp.status === 'applied') {
        setNlText('')
        onInteractionApplied?.(resp)
        await reloadScene(scene.scene.id)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setNlBusy(false)
    }
  }

  const handleRenderClick = async (render, e) => {
    if (!render?.id || !render.object_id_pass_url) return
    const rect = e.currentTarget.getBoundingClientRect()
    const img = e.currentTarget.querySelector('img')
    if (!img?.naturalWidth) return
    const scaleX = img.naturalWidth / rect.width
    const scaleY = img.naturalHeight / rect.height
    const x = Math.floor((e.clientX - rect.left) * scaleX)
    const y = Math.floor((e.clientY - rect.top) * scaleY)
    try {
      const resp = await resolveObjectAtPixel(render.id, x, y)
      if (resp.resolved) {
        setSelectedPlacementId(resp.placement_id)
      } else {
        setSelectedPlacementId(null)
      }
    } catch {
      /* picking failed — leave selection untouched */
    }
  }

  const placements = scene?.placements || []
  const renders = scene?.renders || []
  const selectedPlacement = placements.find((p) => p.id === selectedPlacementId)

  if (!brandId) {
    return (
      <div className="bg-white rounded-xl shadow-sm p-6 text-gray-500">
        Select a brand to author scenes.
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Intent + camera form */}
      <div className="bg-white rounded-xl shadow-sm p-4">
        <h2 className="text-lg font-semibold mb-3">Scene Intent</h2>
        <form onSubmit={handleCreate} className="space-y-3">
          <textarea
            className="input"
            rows={2}
            value={intent}
            onChange={(e) => setIntent(e.target.value)}
            placeholder="Describe the scene (e.g. 'Hero shot of the product with tagline Bold.')"
          />
          <div className="flex items-center gap-3 flex-wrap">
            <select
              value={deployment}
              onChange={(e) => setDeployment(e.target.value)}
              className="text-sm border border-gray-200 rounded px-2 py-1.5"
            >
              <option value="digital">digital</option>
              <option value="print">print</option>
              <option value="social">social</option>
              <option value="ooh">out-of-home</option>
            </select>
            <CameraChips cameras={cameras} onChange={setCameras} />
            <button
              type="submit"
              disabled={creating}
              className="btn-primary ml-auto flex items-center gap-1 px-4 py-2"
            >
              {creating ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Sparkles className="w-4 h-4" />
              )}
              {creating ? 'Rendering…' : 'Create & render'}
            </button>
          </div>
          {error && <div className="text-sm text-red-600">{error}</div>}
        </form>
      </div>

      {scene && (
        <>
          {/* 3D + 2D split */}
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
            <Scene3DCanvas
              placements={placements}
              selectedId={selectedPlacementId}
              onSelect={setSelectedPlacementId}
              onMove={(id, absolutePosition) =>
                applyStructured({
                  action: 'move',
                  target_kind: 'placement',
                  target_id: id,
                  params: { delta: absolutePosition, absolute: true },
                  surface: '3d_canvas',
                })
              }
              onRotate={(id, quat) =>
                applyStructured({
                  action: 'rotate',
                  target_kind: 'placement',
                  target_id: id,
                  params: { axis: 'quat', angle_deg: 0, quat },
                  surface: '3d_canvas',
                })
              }
              onScale={(id, factor) =>
                applyStructured({
                  action: 'scale',
                  target_kind: 'placement',
                  target_id: id,
                  params: { factor },
                  surface: '3d_canvas',
                })
              }
              transformMode={transformMode}
              setTransformMode={setTransformMode}
              brandContext={brandContext}
            />

            <RenderGallery
              renders={renders}
              selectedIdx={selectedRenderIdx}
              onSelect={setSelectedRenderIdx}
              onCanvasClick={handleRenderClick}
              selectedPlacementId={selectedPlacementId}
              onRerenderOne={(cid) => handleRerender([cid])}
            />
          </div>

          {/* NL command bar */}
          <div className="bg-white rounded-xl shadow-sm p-4">
            <h3 className="text-sm font-semibold flex items-center gap-2 mb-2">
              <MousePointer2 className="w-4 h-4 text-primary-600" />
              Natural-language edit
              {selectedPlacement && (
                <span className="text-xs text-gray-500 font-mono">
                  · target: {selectedPlacement.id.slice(0, 8)}
                </span>
              )}
            </h3>
            <form onSubmit={applyNl} className="flex gap-2">
              <input
                className="input flex-1"
                value={nlText}
                onChange={(e) => setNlText(e.target.value)}
                placeholder={
                  selectedPlacementId
                    ? 'e.g. "move it slightly to the right" or "make it warmer"'
                    : 'Click an object in either canvas first, then describe the edit…'
                }
              />
              <button
                type="submit"
                disabled={nlBusy || !selectedPlacementId}
                className="btn-primary px-4 flex items-center gap-1"
              >
                {nlBusy ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Send className="w-4 h-4" />
                )}
                Apply
              </button>
            </form>
            {nlResult && (
              <div className="mt-3 text-xs bg-gray-50 border border-gray-200 rounded p-2">
                <div className="font-medium text-gray-700 mb-1">
                  Status: {nlResult.status}
                </div>
                <pre className="whitespace-pre-wrap text-gray-600 max-h-40 overflow-auto">
                  {JSON.stringify(
                    nlResult.resolution || nlResult.proposed || {},
                    null,
                    2
                  )}
                </pre>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}

function CameraChips({ cameras, onChange }) {
  const toggle = (shot, aspect) => {
    const exists = cameras.some(
      (c) => c.shot_type === shot && c.aspect_ratio === aspect
    )
    if (exists) {
      onChange(
        cameras.filter(
          (c) => !(c.shot_type === shot && c.aspect_ratio === aspect)
        )
      )
    } else {
      onChange([...cameras, { shot_type: shot, aspect_ratio: aspect }])
    }
  }
  const opts = [
    { shot: 'hero', aspect: '1:1' },
    { shot: 'detail', aspect: '1:1' },
    { shot: 'wide', aspect: '16:9' },
    { shot: 'portrait', aspect: '4:5' },
    { shot: 'overhead', aspect: '1:1' },
  ]
  return (
    <div className="flex items-center gap-1 flex-wrap">
      {opts.map(({ shot, aspect }) => {
        const active = cameras.some(
          (c) => c.shot_type === shot && c.aspect_ratio === aspect
        )
        return (
          <button
            key={`${shot}-${aspect}`}
            type="button"
            onClick={() => toggle(shot, aspect)}
            className={`text-xs px-2 py-1 rounded-full border flex items-center gap-1 ${
              active
                ? 'border-primary-500 bg-primary-50 text-primary-700'
                : 'border-gray-200 text-gray-600 hover:bg-gray-50'
            }`}
          >
            <CameraIcon className="w-3 h-3" /> {shot}·{aspect}
          </button>
        )
      })}
    </div>
  )
}

function Scene3DCanvas({
  placements,
  selectedId,
  onSelect,
  onMove,
  onRotate,
  onScale,
  transformMode,
  setTransformMode,
  brandContext,
}) {
  const bg = brandContext?.colors?.[0]?.hex || '#0f172a'
  return (
    <div className="bg-white rounded-xl shadow-sm p-3 space-y-2">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">3D Scene</h3>
        <div className="flex items-center gap-1">
          <ModeBtn
            active={transformMode === 'translate'}
            onClick={() => setTransformMode('translate')}
            icon={<MoveDiagonal className="w-3.5 h-3.5" />}
            label="Move"
          />
          <ModeBtn
            active={transformMode === 'rotate'}
            onClick={() => setTransformMode('rotate')}
            icon={<RotateCw className="w-3.5 h-3.5" />}
            label="Rotate"
          />
          <ModeBtn
            active={transformMode === 'scale'}
            onClick={() => setTransformMode('scale')}
            icon={<Scaling className="w-3.5 h-3.5" />}
            label="Scale"
          />
        </div>
      </div>
      <div className="relative h-[420px] rounded-lg overflow-hidden border border-gray-200 bg-slate-900">
        <Canvas
          camera={{ position: [4, 3, 4], fov: 50 }}
          shadows
          dpr={[1, 1.75]}
          onPointerMissed={() => onSelect(null)}
        >
          <color attach="background" args={[bg]} />
          <ambientLight intensity={0.5} />
          <directionalLight position={[4, 6, 3]} intensity={1.0} castShadow />
          <Suspense fallback={<Html center className="text-white text-xs">Loading…</Html>}>
            {placements.map((p) => (
              <PlacementMesh
                key={p.id}
                placement={p}
                selected={p.id === selectedId}
                onSelect={() => onSelect(p.id)}
                mode={transformMode}
                onCommit={(mode, value) => {
                  if (mode === 'translate') onMove(p.id, value)
                  else if (mode === 'rotate') onRotate(p.id, value)
                  else if (mode === 'scale') onScale(p.id, value)
                }}
              />
            ))}
            <Environment preset="studio" />
          </Suspense>
          <Grid
            args={[20, 20]}
            cellColor="#334155"
            sectionColor="#475569"
            infiniteGrid
            fadeDistance={30}
          />
          <OrbitControls makeDefault enableDamping />
        </Canvas>
        {placements.length === 0 && (
          <div className="absolute inset-0 grid place-items-center text-slate-400 text-sm">
            No placements in this scene yet.
          </div>
        )}
      </div>
      {selectedId && (
        <div className="text-xs text-gray-500 font-mono">
          selected placement: {selectedId}
        </div>
      )}
    </div>
  )
}

function ModeBtn({ active, onClick, icon, label }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`text-xs px-2 py-1 rounded flex items-center gap-1 border ${
        active
          ? 'border-primary-500 bg-primary-50 text-primary-700'
          : 'border-gray-200 text-gray-600 hover:bg-gray-50'
      }`}
    >
      {icon} {label}
    </button>
  )
}

function PlacementMesh({ placement, selected, onSelect, mode, onCommit }) {
  const meshRef = useRef()
  const pos = placement.position || [0, 0, 0]
  const quat = placement.rotation_quat || [0, 0, 0, 1]
  const scl = placement.scale || [1, 1, 1]
  const color = deterministicColor(placement.asset_id || placement.id)
  // Track committed values so we only emit interactions when the user actually
  // drags — avoids hammering the API on every TransformControls frame.
  const lastCommitted = useRef({
    position: pos,
    quat: quat,
    scaleMag: (scl[0] + scl[1] + scl[2]) / 3,
  })

  // Apply incoming quaternion on every render — Three.js mesh.quaternion is
  // not reactive via props, so we sync imperatively.
  useEffect(() => {
    if (meshRef.current) {
      meshRef.current.quaternion.set(quat[0], quat[1], quat[2], quat[3])
    }
  }, [quat[0], quat[1], quat[2], quat[3]])

  const handleDragEnd = () => {
    if (!meshRef.current) return
    const m = meshRef.current
    const nextPos = [m.position.x, m.position.y, m.position.z]
    const nextQuat = [m.quaternion.x, m.quaternion.y, m.quaternion.z, m.quaternion.w]
    const nextScaleMag = (m.scale.x + m.scale.y + m.scale.z) / 3

    if (mode === 'translate' && !arraysEqual(nextPos, lastCommitted.current.position)) {
      lastCommitted.current.position = nextPos
      onCommit('translate', nextPos)
    } else if (mode === 'rotate' && !arraysEqual(nextQuat, lastCommitted.current.quat)) {
      lastCommitted.current.quat = nextQuat
      onCommit('rotate', nextQuat)
    } else if (mode === 'scale' && Math.abs(nextScaleMag - lastCommitted.current.scaleMag) > 1e-3) {
      // Backend takes a single scale factor (uniform scale). We pass the mean
      // of the axis scales, which matches TransformControls scale mode when
      // the user isn't doing anisotropic scaling.
      const factor = nextScaleMag / Math.max(0.001, lastCommitted.current.scaleMag)
      lastCommitted.current.scaleMag = nextScaleMag
      onCommit('scale', factor)
    }
  }

  return (
    <>
      <mesh
        ref={meshRef}
        position={pos}
        scale={scl}
        castShadow
        receiveShadow
        onClick={(e) => {
          e.stopPropagation()
          onSelect()
        }}
      >
        <boxGeometry args={[1, 1, 1]} />
        <meshStandardMaterial
          color={color}
          emissive={selected ? color : '#000000'}
          emissiveIntensity={selected ? 0.35 : 0}
          roughness={0.5}
        />
      </mesh>
      {selected && meshRef.current && (
        <TransformControls
          object={meshRef.current}
          mode={mode}
          onMouseUp={handleDragEnd}
        />
      )}
    </>
  )
}

function RenderGallery({
  renders,
  selectedIdx,
  onSelect,
  onCanvasClick,
  selectedPlacementId,
  onRerenderOne,
}) {
  const active = renders[selectedIdx]
  return (
    <div className="bg-white rounded-xl shadow-sm p-3 space-y-2">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold flex items-center gap-1">
          <ImageIcon className="w-4 h-4 text-primary-600" /> Renders
        </h3>
        {renders.length > 1 && (
          <div className="flex items-center gap-1">
            {renders.map((r, i) => (
              <button
                key={r.id || i}
                onClick={() => onSelect(i)}
                className={`text-[10px] px-2 py-1 rounded border font-mono ${
                  i === selectedIdx
                    ? 'border-primary-500 bg-primary-50 text-primary-700'
                    : 'border-gray-200 text-gray-600 hover:bg-gray-50'
                }`}
              >
                {r.shot_type || (r.camera_id || `cam-${i}`).slice(0, 6)}
              </button>
            ))}
          </div>
        )}
      </div>
      <div
        className="relative h-[420px] rounded-lg overflow-hidden border border-gray-200 bg-slate-100 cursor-crosshair"
        onClick={active ? (e) => onCanvasClick(active, e) : undefined}
      >
        {active?.rgb_url ? (
          <img
            src={resolveAssetUrl(active.rgb_url)}
            alt="render"
            className="w-full h-full object-contain select-none pointer-events-none"
          />
        ) : (
          <div className="h-full grid place-items-center text-gray-400 text-sm">
            No render yet.
          </div>
        )}
        {selectedPlacementId && (
          <div className="absolute top-2 left-2 bg-white/90 text-[10px] px-2 py-1 rounded border border-gray-200 font-mono">
            selected: {selectedPlacementId.slice(0, 8)}
          </div>
        )}
      </div>
      {active && (
        <div className="flex items-center justify-between text-xs text-gray-500">
          <span className="font-mono">
            {active.shot_type || active.camera_id?.slice(0, 8)}
            {active.render_backend ? ` · ${active.render_backend}` : ''}
          </span>
          <button
            onClick={() => onRerenderOne(active.camera_id)}
            className="text-primary-600 hover:underline flex items-center gap-1"
          >
            <Loader2 className="w-3 h-3" /> Re-render this shot
          </button>
        </div>
      )}
    </div>
  )
}

function deterministicColor(seed) {
  let hash = 0
  for (let i = 0; i < (seed || '').length; i++) {
    hash = ((hash << 5) - hash + (seed || '').charCodeAt(i)) | 0
  }
  const h = Math.abs(hash) % 360
  return `hsl(${h} 60% 55%)`
}

function arraysEqual(a, b, eps = 1e-4) {
  if (!a || !b || a.length !== b.length) return false
  for (let i = 0; i < a.length; i++) {
    if (Math.abs(a[i] - b[i]) > eps) return false
  }
  return true
}
