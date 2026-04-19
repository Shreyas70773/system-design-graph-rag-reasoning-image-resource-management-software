import { useEffect, useMemo, useRef, useState } from 'react'
import {
  AlertCircle,
  CheckCircle2,
  Cpu,
  Eraser,
  Eye,
  ImagePlus,
  Loader2,
  ScanSearch,
  Sparkles,
  Wand2,
} from 'lucide-react'
import {
  getCapstoneAccuracyPresets,
  getCapstoneCapabilities,
  getCapstoneScene,
  removeCapstoneObject,
  segmentCapstoneClick,
  uploadCapstoneScene,
} from '../services/apiV3'

export default function CapstoneStudio() {
  const imageRef = useRef(null)
  const [capabilities, setCapabilities] = useState(null)
  const [presets, setPresets] = useState(null)
  const [scene, setScene] = useState(null)
  const [selectedObjectId, setSelectedObjectId] = useState(null)
  const [segmentPresetKey, setSegmentPresetKey] = useState('balanced')
  const [inpaintPresetKey, setInpaintPresetKey] = useState('balanced')
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
  const selectedSegmentationPreset = presets?.segmentation?.[segmentPresetKey] || {}
  const selectedInpaintPreset = presets?.inpainting?.[inpaintPresetKey] || {}

  async function refreshScene(sceneId) {
    const fresh = await getCapstoneScene(sceneId)
    setScene(fresh)
    if (fresh.objects.length === 0) {
      setSelectedObjectId(null)
    } else if (!fresh.objects.find((item) => item.object_id === selectedObjectId)) {
      setSelectedObjectId(fresh.objects[0].object_id)
    }
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
      setMessage(`Uploaded scene ${uploaded.scene.scene_id}. Click inside the image to segment an object.`)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy('')
      event.target.value = ''
    }
  }

  async function handleImageClick(event) {
    if (!scene?.scene?.scene_id || busy) return
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
      setMessage(`Segmented object with ${result.method}. You can remove it now or click elsewhere to add another object.`)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy('')
    }
  }

  async function handleRemoveObject() {
    if (!scene?.scene?.scene_id || !selectedObject) return
    setBusy('remove')
    setError('')
    setMessage('')
    try {
      const result = await removeCapstoneObject(scene.scene.scene_id, {
        object_id: selectedObject.object_id,
        tuning: selectedInpaintPreset,
      })
      await refreshScene(scene.scene.scene_id)
      setMessage(
        `Removed ${selectedObject.class_label} with ${result.method}. Scene graph and canvas history were updated.`
      )
    } catch (err) {
      setError(err.message)
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
            <h1 className="text-3xl font-semibold tracking-tight">Capstone Studio</h1>
            <p className="max-w-3xl text-sm text-slate-200">
              Upload a photo, click to segment an object with SAM 2, then remove it with Big-LaMa while
              preserving a persistent scene graph and edit history.
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
                  Click the image to create a segmentation mask. Selected objects are highlighted.
                </p>
              </div>
              {busy ? (
                <span className="inline-flex items-center gap-2 rounded-full bg-cyan-50 px-3 py-1 text-xs font-medium text-cyan-700">
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  {busy}
                </span>
              ) : null}
            </div>

            {imageUrl ? (
              <div className="relative overflow-hidden rounded-2xl border border-slate-200 bg-slate-100">
                <img
                  ref={imageRef}
                  src={imageUrl}
                  alt="Capstone scene"
                  className="block max-h-[720px] w-full cursor-crosshair object-contain"
                  onClick={handleImageClick}
                />
                {objects.map((item, index) => (
                  <ObjectOverlay
                    key={item.object_id}
                    object={item}
                    scene={scene?.scene}
                    isSelected={item.object_id === selectedObjectId}
                    colorIndex={index}
                    onSelect={() => setSelectedObjectId(item.object_id)}
                  />
                ))}
              </div>
            ) : (
              <div className="flex min-h-[520px] items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-slate-50 text-center text-slate-500">
                <div className="space-y-3 px-6">
                  <ImagePlus className="mx-auto h-10 w-10 text-slate-400" />
                  <p className="text-sm">Upload a test image to start the real SAM 2 + LaMa workflow.</p>
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
              <button
                type="button"
                onClick={handleRemoveObject}
                disabled={!selectedObject || busy === 'remove'}
                className="inline-flex items-center gap-2 rounded-2xl bg-rose-500 px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
              >
                <Eraser className="h-4 w-4" />
                Remove Selected
              </button>
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
                    onClick={() => setSelectedObjectId(item.object_id)}
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
        <h2 className="text-lg font-semibold text-slate-900">Local Runtime</h2>
      </div>
      <div className="space-y-3 text-sm">
        <CapabilityRow name="SAM 2" status={capabilities?.sam2?.ready} detail={capabilities?.sam2?.device} />
        <CapabilityRow name="Big-LaMa" status={capabilities?.lama?.ready} detail={capabilities?.lama?.device} />
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

function ObjectOverlay({ object, scene, isSelected, colorIndex, onSelect }) {
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
        event.stopPropagation()
        onSelect()
      }}
      className="absolute"
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
