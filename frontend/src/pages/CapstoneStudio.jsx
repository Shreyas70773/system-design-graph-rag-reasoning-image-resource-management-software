import { useEffect, useMemo, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import {
  AlertCircle,
  CheckCircle2,
  Cpu,
  Download,
  Eraser,
  Eye,
  ImagePlus,
  Loader2,
  PenLine,
  ScanSearch,
  Sparkles,
  Wand2,
  XCircle,
} from 'lucide-react'
import {
  getCapstoneAccuracyPresets,
  getCapstoneCapabilities,
  getCapstoneScene,
  removeCapstoneObject,
  segmentCapstoneClick,
  segmentCapstoneFreehand,
  uploadCapstoneScene,
} from '../services/apiV3'

function clamp01(value) {
  return Math.max(0, Math.min(1, value))
}

function distanceSquared(a, b) {
  const dx = a.x - b.x
  const dy = a.y - b.y
  return dx * dx + dy * dy
}

const REFINEMENT_PROFILES = {
  soft: {
    mask_dilate_px: 2,
    refine_n_iters: 6,
    refine_lr: 0.001,
    refine_max_scales: 2,
    refine_px_budget: 1200000,
  },
}

export default function CapstoneStudio() {
  const location = useLocation()
  const imageRef = useRef(null)
  const [capabilities, setCapabilities] = useState(null)
  const [presets, setPresets] = useState(null)
  const [scene, setScene] = useState(null)
  const [selectedObjectId, setSelectedObjectId] = useState(null)
  const [removalObjectId, setRemovalObjectId] = useState(null)
  const [segmentPresetKey, setSegmentPresetKey] = useState('balanced')
  const [inpaintPresetKey, setInpaintPresetKey] = useState('balanced')
  const [lastRemoveMeta, setLastRemoveMeta] = useState(null)
  const [selectionMode, setSelectionMode] = useState('click')
  const [freehandMode, setFreehandMode] = useState('lasso')
  const [brushSizePx, setBrushSizePx] = useState(24)
  const [isDrawing, setIsDrawing] = useState(false)
  const [freehandPaths, setFreehandPaths] = useState([])
  const [activePath, setActivePath] = useState([])
  const [busy, setBusy] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    async function loadBootData() {
      try {
        const [caps, accuracy] = await Promise.all([
          getCapstoneCapabilities(),
          getCapstoneAccuracyPresets(),
        ])
        setCapabilities(caps)
        setPresets(accuracy)
        
        // If a scene ID is passed via navigation state, load it
        if (location.state?.sceneId) {
          const scene = await getCapstoneScene(location.state.sceneId)
          setScene(scene)
        }
      } catch (err) {
        setError(err.message)
      }
    }
    loadBootData()
  }, [])

  const imageUrl = scene?.scene?.image_path
  const objects = scene?.objects || []
  const history = scene?.edit_events || []
  const selectedObject = useMemo(
    () => objects.find((item) => item.object_id === selectedObjectId) || null,
    [objects, selectedObjectId]
  )
  const removalTargetObject = useMemo(
    () => objects.find((item) => item.object_id === (selectedObjectId || removalObjectId)) || null,
    [objects, selectedObjectId, removalObjectId]
  )
  const drawnPaths = useMemo(
    () => (activePath.length >= 2 ? [...freehandPaths, { points: activePath }] : freehandPaths),
    [freehandPaths, activePath]
  )
  const freehandStrokeWidth = useMemo(() => {
    if (!scene?.scene) return 0.01
    return brushSizePx / Math.max(scene.scene.canvas_width, scene.scene.canvas_height)
  }, [scene?.scene, brushSizePx])
  const selectedSegmentationPreset = presets?.segmentation?.[segmentPresetKey] || {}
  const selectedInpaintPreset = presets?.inpainting?.[inpaintPresetKey] || {}
  const refineSupported = Boolean(capabilities?.lama?.refine_supported)
  const softRefinementProfile = REFINEMENT_PROFILES.soft
  const effectiveInpaintTuning = useMemo(
    () => ({
      ...selectedInpaintPreset,
      ...softRefinementProfile,
      enable_refinement: refineSupported,
    }),
    [selectedInpaintPreset, softRefinementProfile, refineSupported]
  )

  async function refreshScene(sceneId) {
    const fresh = await getCapstoneScene(sceneId)
    setScene(fresh)
    const selectedStillExists =
      selectedObjectId !== null && fresh.objects.some((item) => item.object_id === selectedObjectId)
    const removalStillExists =
      removalObjectId !== null && fresh.objects.some((item) => item.object_id === removalObjectId)

    if (fresh.objects.length === 0) {
      setSelectedObjectId(null)
      setRemovalObjectId(null)
      return
    }

    if (!selectedStillExists) {
      setSelectedObjectId(null)
    }
    if (!removalStillExists) {
      setRemovalObjectId(fresh.objects[0].object_id)
    }
  }

  function handleSelectObject(objectId) {
    setSelectedObjectId(objectId)
    setRemovalObjectId(objectId)
  }

  async function handleUpload(event) {
    const file = event.target.files?.[0]
    if (!file) return
    setBusy('upload')
    setError('')
    setMessage('')
    try {
      const uploaded = await uploadCapstoneScene(file, { title: file.name })
      setScene(uploaded)
      setSelectedObjectId(null)
      setRemovalObjectId(null)
      setFreehandPaths([])
      setActivePath([])
      setLastRemoveMeta(null)
      setMessage(`Uploaded scene ${uploaded.scene.scene_id}. Click or draw to segment an object.`)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy('')
      event.target.value = ''
    }
  }

  async function handleImageClick(event) {
    if (!scene?.scene?.scene_id || busy || selectionMode !== 'click') return
    const rect = imageRef.current?.getBoundingClientRect()
    if (!rect) return

    const clickX = (event.clientX - rect.left) / rect.width
    const clickY = (event.clientY - rect.top) / rect.height

    setBusy('segment')
    setError('')
    setMessage('')
    try {
      const result = await segmentCapstoneClick(scene.scene.scene_id, {
        click_x: clickX,
        click_y: clickY,
        label: 'object',
        register_object: true,
        tuning: selectedSegmentationPreset,
      })
      await refreshScene(scene.scene.scene_id)
      setSelectedObjectId(result.scene_object_id || null)
      setRemovalObjectId(result.scene_object_id || null)
      setMessage(`Segmented object with ${result.method}. You can remove it now or click elsewhere to add another object.`)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy('')
    }
  }

  function toRelativePoint(event) {
    const rect = imageRef.current?.getBoundingClientRect()
    if (!rect) return null
    return {
      x: clamp01((event.clientX - rect.left) / rect.width),
      y: clamp01((event.clientY - rect.top) / rect.height),
    }
  }

  async function applyFreehandPaths(paths, trigger = 'manual') {
    if (!scene?.scene?.scene_id || busy) return
    if (paths.length === 0) {
      setError('Draw at least one freehand stroke before applying segmentation.')
      return
    }

    setBusy('segment-freehand')
    setError('')
    setMessage('')
    try {
      const result = await segmentCapstoneFreehand(scene.scene.scene_id, {
        paths,
        mode: freehandMode,
        brush_size_px: brushSizePx,
        label: 'object',
        register_object: true,
        sam_refine: true,
        tuning: selectedSegmentationPreset,
      })
      await refreshScene(scene.scene.scene_id)
      setSelectedObjectId(result.scene_object_id || null)
      setRemovalObjectId(result.scene_object_id || null)
      clearFreehandPaths()
      if (trigger === 'auto-lasso') {
        setMessage(`Auto-snapped object boundary with ${result.method}. You can remove it now.`)
      } else {
        setMessage(`Segmented object with ${result.method}. Freehand guide + SAM2 auto-snap applied.`)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy('')
    }
  }

  function commitActivePath(pathPoints, options = {}) {
    const normalized = pathPoints.length >= 2 ? [...freehandPaths, { points: pathPoints }] : freehandPaths
    if (pathPoints.length >= 2) {
      setFreehandPaths(normalized)
    }
    if (options.autoApply && normalized.length > 0) {
      void applyFreehandPaths(normalized, 'auto-lasso')
    }
  }

  function handleFreehandPointerDown(event) {
    if (!scene?.scene?.scene_id || busy || selectionMode !== 'freehand') return
    const point = toRelativePoint(event)
    if (!point) return
    setIsDrawing(true)
    setActivePath([point])
    if (event.currentTarget.setPointerCapture) {
      event.currentTarget.setPointerCapture(event.pointerId)
    }
  }

  function handleFreehandPointerMove(event) {
    if (!isDrawing || selectionMode !== 'freehand') return
    const point = toRelativePoint(event)
    if (!point) return
    setActivePath((path) => {
      if (path.length === 0) return [point]
      const last = path[path.length - 1]
      if (distanceSquared(last, point) < 0.000004) return path
      return [...path, point]
    })
  }

  function handleFreehandPointerUp() {
    if (!isDrawing) return
    setIsDrawing(false)
    setActivePath((current) => {
      commitActivePath(current, { autoApply: freehandMode === 'lasso' })
      return []
    })
  }

  function clearFreehandPaths() {
    setIsDrawing(false)
    setActivePath([])
    setFreehandPaths([])
  }

  async function handleApplyFreehand() {
    const paths = activePath.length >= 2 ? [...freehandPaths, { points: activePath }] : freehandPaths
    await applyFreehandPaths(paths, 'manual')
  }

  async function handleRemoveObject() {
    if (!scene?.scene?.scene_id || !removalTargetObject) return
    setBusy('remove')
    setError('')
    setMessage('')
    try {
      const result = await removeCapstoneObject(scene.scene.scene_id, {
        object_id: removalTargetObject.object_id,
        tuning: effectiveInpaintTuning,
      })
      await refreshScene(scene.scene.scene_id)
      const refineEnabled = Boolean(result.refine_enabled)
      const refiner = result.refiner || {}
      setLastRemoveMeta({
        refineRequested: Boolean(result.refine_requested),
        refineEnabled,
        refineSupported: Boolean(result.refine_supported),
        refineSkipReason: result.refine_skip_reason || '',
        refinePipeline: result.refine_pipeline || 'predict',
        refineOverrides: result.refine_overrides || [],
        maskAreaFraction: result.mask_area_fraction,
        profile: 'soft',
        refiner,
      })
      const skipSuffix = result.refine_skip_reason ? ` ${result.refine_skip_reason}` : ''
      setMessage(
        `Removed ${removalTargetObject.class_label} with ${result.method}. Refinement ${
          refineEnabled ? 'ON' : 'OFF'
        }. Scene graph and canvas history were updated.${skipSuffix}`
      )
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy('')
    }
  }

  function handleDeselectObject() {
    setSelectedObjectId(null)
    setError('')
    if (removalTargetObject) {
      setMessage('Selection cleared. Remove will still target the last detected object.')
    } else {
      setMessage('Selection cleared.')
    }
  }

  async function handleDownloadScene() {
    if (!imageUrl) return
    setBusy('download')
    setError('')
    try {
      const response = await fetch(imageUrl)
      if (!response.ok) {
        throw new Error(`Download failed with status ${response.status}`)
      }
      const blob = await response.blob()
      const ext = blob.type.includes('jpeg') ? 'jpg' : 'png'
      const sceneId = scene?.scene?.scene_id || 'scene'
      const href = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = href
      link.download = `${sceneId}-canvas.${ext}`
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(href)
      setMessage('Downloaded current canvas image.')
    } catch (err) {
      setError(err.message || 'Failed to download image')
    } finally {
      setBusy('')
    }
  }

  return (
    <div className="space-y-6">
      <section className="rounded-3xl border border-slate-200 bg-gradient-to-br from-slate-950 via-slate-900 to-cyan-950 text-white p-8 shadow-xl">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-3">
            <div className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-xs uppercase tracking-[0.18em] text-cyan-100">
              <Sparkles className="h-3.5 w-3.5" />
              GraphRAG Image Manipulation Platform
            </div>
            <h1 className="text-3xl font-semibold tracking-tight">Content Editor</h1>
            <p className="max-w-3xl text-sm text-slate-200">
              Upload a photo, click to segment an object, then remove it while preserving a persistent
              scene graph and edit history.
            </p>
          </div>
          <label className="inline-flex cursor-pointer items-center gap-2 rounded-2xl bg-cyan-400 px-4 py-3 text-sm font-semibold text-slate-950 shadow-lg transition hover:bg-cyan-300">
            <ImagePlus className="h-4 w-4" />
            Upload Scene
            <input type="file" accept="image/png,image/jpeg" className="hidden" onChange={handleUpload} />
          </label>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[320px_minmax(0,1fr)_320px]">
        <div className="space-y-6">
          <StatusCard capabilities={capabilities} />
          <PresetCard
            icon={<ScanSearch className="h-4 w-4" />}
            title="Segmentation Preset"
            value={segmentPresetKey}
            options={presets?.segmentation || {}}
            onChange={setSegmentPresetKey}
          />
          <PresetCard
            icon={<Wand2 className="h-4 w-4" />}
            title="Inpaint Preset"
            value={inpaintPresetKey}
            options={presets?.inpainting || {}}
            onChange={setInpaintPresetKey}
          />
        </div>

        <div className="space-y-4">
          <div className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="mb-3 flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-slate-900">Interactive Canvas</h2>
                <p className="text-sm text-slate-500">
                  Click to select an object, or draw a rough outline and release to auto-snap object edges.
                </p>
              </div>
              {busy ? (
                <span className="inline-flex items-center gap-2 rounded-full bg-cyan-50 px-3 py-1 text-xs font-medium text-cyan-700">
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  {busy}
                </span>
              ) : null}
            </div>

            <div className="mb-3 flex flex-wrap items-center gap-2 rounded-2xl border border-slate-200 bg-slate-50 p-2">
              <button
                type="button"
                onClick={() => setSelectionMode('click')}
                className={`rounded-xl px-3 py-2 text-xs font-semibold uppercase tracking-wide transition ${
                  selectionMode === 'click'
                    ? 'bg-cyan-500 text-white'
                    : 'bg-white text-slate-700 hover:bg-slate-100'
                }`}
              >
                Click Select
              </button>
              <button
                type="button"
                onClick={() => setSelectionMode('freehand')}
                className={`inline-flex items-center gap-1 rounded-xl px-3 py-2 text-xs font-semibold uppercase tracking-wide transition ${
                  selectionMode === 'freehand'
                    ? 'bg-cyan-500 text-white'
                    : 'bg-white text-slate-700 hover:bg-slate-100'
                }`}
              >
                <PenLine className="h-3.5 w-3.5" />
                Freehand
              </button>

              {selectionMode === 'freehand' ? (
                <>
                  <select
                    value={freehandMode}
                    onChange={(event) => setFreehandMode(event.target.value)}
                    className="rounded-xl border border-slate-200 bg-white px-2 py-2 text-xs text-slate-700"
                  >
                    <option value="brush">brush</option>
                    <option value="lasso">lasso</option>
                  </select>
                  <label className="inline-flex items-center gap-2 rounded-xl bg-white px-2 py-2 text-xs text-slate-700">
                    size
                    <input
                      type="range"
                      min={4}
                      max={96}
                      value={brushSizePx}
                      onChange={(event) => setBrushSizePx(Number(event.target.value))}
                    />
                    <span>{brushSizePx}px</span>
                  </label>
                  <button
                    type="button"
                    onClick={handleApplyFreehand}
                    disabled={freehandMode === 'lasso' || drawnPaths.length === 0 || !!busy}
                    className="rounded-xl bg-emerald-500 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-white disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {freehandMode === 'lasso' ? 'Auto on Release' : 'Apply Freehand'}
                  </button>
                  <button
                    type="button"
                    onClick={clearFreehandPaths}
                    disabled={drawnPaths.length === 0 || !!busy}
                    className="rounded-xl bg-slate-200 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    Clear Sketch
                  </button>
                </>
              ) : null}
            </div>

            {imageUrl ? (
              <div className="relative overflow-hidden rounded-2xl border border-slate-200 bg-slate-100">
                <img
                  ref={imageRef}
                  src={imageUrl}
                  alt="Capstone scene"
                  className={`block max-h-[720px] w-full object-contain ${
                    selectionMode === 'freehand' ? 'cursor-cell' : 'cursor-crosshair'
                  }`}
                  onClick={selectionMode === 'click' ? handleImageClick : undefined}
                />
                {objects.map((item, index) => (
                  <ObjectOverlay
                    key={item.object_id}
                    object={item}
                    scene={scene?.scene}
                    isSelected={item.object_id === selectedObjectId}
                    colorIndex={index}
                    interactionEnabled={selectionMode !== 'freehand'}
                    onSelect={() => handleSelectObject(item.object_id)}
                  />
                ))}
                {selectionMode === 'freehand' ? (
                  <div
                    className="absolute inset-0 z-20"
                    onPointerDown={handleFreehandPointerDown}
                    onPointerMove={handleFreehandPointerMove}
                    onPointerUp={handleFreehandPointerUp}
                    onPointerCancel={handleFreehandPointerUp}
                    onPointerLeave={handleFreehandPointerUp}
                  >
                    <svg className="h-full w-full" viewBox="0 0 1 1" preserveAspectRatio="none">
                      {drawnPaths.map((path, index) => {
                        const points = path.points.map((point) => `${point.x},${point.y}`).join(' ')
                        if (freehandMode === 'lasso' && path.points.length >= 3) {
                          return (
                            <polygon
                              key={`lasso-${index}`}
                              points={points}
                              fill="rgba(6, 182, 212, 0.20)"
                              stroke="#22d3ee"
                              strokeWidth={Math.max(0.003, freehandStrokeWidth)}
                              vectorEffect="non-scaling-stroke"
                            />
                          )
                        }
                        return (
                          <polyline
                            key={`brush-${index}`}
                            points={points}
                            fill="none"
                            stroke="#22d3ee"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={Math.max(0.003, freehandStrokeWidth)}
                            vectorEffect="non-scaling-stroke"
                          />
                        )
                      })}
                    </svg>
                  </div>
                ) : null}
              </div>
            ) : (
              <div className="flex min-h-[520px] items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-slate-50 text-center text-slate-500">
                <div className="space-y-3 px-6">
                  <ImagePlus className="mx-auto h-10 w-10 text-slate-400" />
                  <p className="text-sm">Upload an image to start editing and removing objects.</p>
                </div>
              </div>
            )}
          </div>

          {message ? <Notice kind="success" text={message} /> : null}
          {error ? <Notice kind="error" text={error} /> : null}
        </div>

        <div className="space-y-6">
          <div className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-slate-900">Scene Objects</h2>
                <p className="text-sm text-slate-500">{objects.length} registered objects</p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <span className="inline-flex items-center gap-2 rounded-2xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700">
                  Soft Refinement Default
                </span>
                <button
                  type="button"
                  onClick={handleDownloadScene}
                  disabled={!imageUrl || !!busy}
                  className="inline-flex items-center gap-2 rounded-2xl bg-slate-700 px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <Download className="h-4 w-4" />
                  Download
                </button>
                <button
                  type="button"
                  onClick={handleDeselectObject}
                  disabled={!selectedObject || !!busy}
                  className="inline-flex items-center gap-2 rounded-2xl bg-slate-500 px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <XCircle className="h-4 w-4" />
                  Deselect
                </button>
                <button
                  type="button"
                  onClick={handleRemoveObject}
                  disabled={!removalTargetObject || busy === 'remove'}
                  className="inline-flex items-center gap-2 rounded-2xl bg-rose-500 px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <Eraser className="h-4 w-4" />
                  Remove Selected
                </button>
              </div>
            </div>
            <div className="mb-3 rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600">
              Refinement is pinned to soft by default for remove-object to reduce artifacts.
              {lastRemoveMeta ? (
                <span className="ml-2 font-medium text-slate-800">
                  requested {lastRemoveMeta.refineRequested ? 'ON' : 'OFF'},
                  Last run: {lastRemoveMeta.refineEnabled ? 'ON' : 'OFF'}
                  {lastRemoveMeta.profile ? `, ${lastRemoveMeta.profile}` : ''}
                  {lastRemoveMeta.refinePipeline ? `, ${lastRemoveMeta.refinePipeline}` : ''}
                  {lastRemoveMeta.refiner?.n_iters ? ` (${lastRemoveMeta.refiner.n_iters} iters)` : ''}
                  {lastRemoveMeta.maskAreaFraction !== undefined && lastRemoveMeta.maskAreaFraction !== null
                    ? `, mask ${(lastRemoveMeta.maskAreaFraction * 100).toFixed(1)}%`
                    : ''}
                  {lastRemoveMeta.refineSkipReason ? `, skipped: ${lastRemoveMeta.refineSkipReason}` : ''}
                </span>
              ) : null}
            </div>
            <div className="space-y-3">
              {objects.length === 0 ? (
                <p className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-500">
                  No objects yet. Upload an image and click the canvas.
                </p>
              ) : (
                objects.map((item, index) => (
                  <button
                    key={item.object_id}
                    type="button"
                    onClick={() => handleSelectObject(item.object_id)}
                    className={`w-full rounded-2xl border px-4 py-3 text-left transition ${
                      item.object_id === selectedObjectId
                        ? 'border-cyan-300 bg-cyan-50'
                        : 'border-slate-200 bg-white hover:border-slate-300'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="inline-flex h-2.5 w-2.5 rounded-full bg-cyan-500" />
                          <span className="font-medium text-slate-900">
                            {item.class_label || `object-${index + 1}`}
                          </span>
                        </div>
                        <p className="mt-1 text-xs text-slate-500">{item.object_id}</p>
                      </div>
                      <span className="rounded-full bg-slate-100 px-2 py-1 text-xs text-slate-600">
                        z {item.z_order}
                      </span>
                    </div>
                    <p className="mt-3 text-xs text-slate-500">
                      bbox: {item.bbox.x}, {item.bbox.y}, {item.bbox.w} × {item.bbox.h}
                    </p>
                  </button>
                ))
              )}
            </div>
          </div>

          <div className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="mb-3 flex items-center gap-2">
              <Eye className="h-4 w-4 text-slate-600" />
              <h2 className="text-lg font-semibold text-slate-900">Edit History</h2>
            </div>
            <div className="space-y-2">
              {history.length === 0 ? (
                <p className="text-sm text-slate-500">No edits yet.</p>
              ) : (
                [...history].reverse().slice(-8).map((event) => (
                  <div key={event.event_id} className="rounded-2xl bg-slate-50 px-3 py-3 text-sm">
                    <div className="font-medium text-slate-900">{event.event_type}</div>
                    <div className="mt-1 text-xs text-slate-500">{event.event_id}</div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}

function StatusCard({ capabilities }) {
  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-center gap-2">
        <Cpu className="h-4 w-4 text-slate-700" />
        <h2 className="text-lg font-semibold text-slate-900">Processing</h2>
      </div>
      <div className="space-y-3 text-sm">
        <CapabilityRow name="Segmentation" status={capabilities?.sam2?.ready} detail={capabilities?.sam2?.device} />
        <CapabilityRow name="Inpainting" status={capabilities?.lama?.ready} detail={capabilities?.lama?.device} />
      </div>
    </div>
  )
}

function CapabilityRow({ name, status, detail }) {
  return (
    <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-3 py-3">
      <div>
        <div className="font-medium text-slate-900">{name}</div>
        <div className="text-xs text-slate-500">{detail || 'pending'}</div>
      </div>
      <div
        className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold ${
          status ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'
        }`}
      >
        {status ? <CheckCircle2 className="h-3.5 w-3.5" /> : <AlertCircle className="h-3.5 w-3.5" />}
        {status ? 'ready' : 'not ready'}
      </div>
    </div>
  )
}

function PresetCard({ icon, title, value, options, onChange }) {
  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-center gap-2 text-slate-900">
        {icon}
        <h2 className="text-lg font-semibold">{title}</h2>
      </div>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-cyan-400"
      >
        {Object.keys(options).map((key) => (
          <option key={key} value={key}>
            {key}
          </option>
        ))}
      </select>
      <pre className="mt-3 overflow-x-auto rounded-2xl bg-slate-950 p-3 text-xs text-cyan-100">
        {JSON.stringify(options[value] || {}, null, 2)}
      </pre>
    </div>
  )
}

function ObjectOverlay({ object, scene, isSelected, colorIndex, onSelect, interactionEnabled }) {
  if (!scene) return null
  const palette = ['#06b6d4', '#22c55e', '#f59e0b', '#a855f7', '#ef4444']
  const color = palette[colorIndex % palette.length]
  const left = `${(object.bbox.x / scene.canvas_width) * 100}%`
  const top = `${(object.bbox.y / scene.canvas_height) * 100}%`
  const width = `${(object.bbox.w / scene.canvas_width) * 100}%`
  const height = `${(object.bbox.h / scene.canvas_height) * 100}%`

  return (
    <button
      type="button"
      onClick={(event) => {
        if (!interactionEnabled) return
        event.stopPropagation()
        onSelect()
      }}
      className={`absolute ${interactionEnabled ? '' : 'pointer-events-none'}`}
      style={{
        left,
        top,
        width,
        height,
        border: `2px solid ${isSelected ? '#ffffff' : color}`,
        boxShadow: isSelected ? `0 0 0 9999px rgba(15, 23, 42, 0.15), 0 0 0 2px ${color}` : 'none',
      }}
    >
      <span
        className="absolute left-1 top-1 rounded-full px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-white"
        style={{ backgroundColor: color }}
      >
        {object.class_label}
      </span>
    </button>
  )
}

function Notice({ kind, text }) {
  const tone =
    kind === 'error'
      ? 'border-rose-200 bg-rose-50 text-rose-700'
      : 'border-emerald-200 bg-emerald-50 text-emerald-700'
  return <div className={`rounded-2xl border px-4 py-3 text-sm ${tone}`}>{text}</div>
}
