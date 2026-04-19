/**
 * LayerEditor — the core research loop in a single panel.
 *
 * User flow:
 *   1. Compose  — generate (or upload) a base image
 *   2. Click    — click anywhere on the image to select a semantic layer
 *   3. Prompt   — describe the change in natural language
 *   4. Edit     — brand-conditioned inpaint runs; metrics appear side-by-side
 *   5. Compare  — toggle Ablation mode to re-run WITHOUT graph conditioning
 *   6. Iterate  — click again on the result image to make another edit
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import {
  Crosshair,
  Download,
  FlaskConical,
  Layers,
  Loader2,
  RefreshCw,
  Sparkles,
  Type,
  Undo2,
  Upload,
} from 'lucide-react'
import { composeImage, editLayer, getLayerHistory, resolveAssetUrl, segmentLayer } from '../../services/apiV2'

function formatAxiosError(err) {
  const d = err.response?.data?.detail
  if (typeof d === 'string') return d
  if (Array.isArray(d)) return d.map((x) => x.msg || JSON.stringify(x)).join('; ')
  return err.message || 'Request failed'
}

// ---------------------------------------------------------------------------
// Metric card
// ---------------------------------------------------------------------------
function MetricCard({ label, value, ideal, description, unit = '' }) {
  if (value === null || value === undefined) return null
  const num = typeof value === 'number' ? value : parseFloat(value)
  const isGood =
    ideal === 'high' ? num >= 0.85 : ideal === 'low' ? num <= 15 : true
  return (
    <div className={`rounded-lg border p-3 ${isGood ? 'border-green-200 bg-green-50' : 'border-amber-200 bg-amber-50'}`}>
      <div className="text-xs text-gray-500 font-medium">{label}</div>
      <div className={`text-xl font-bold ${isGood ? 'text-green-700' : 'text-amber-700'}`}>
        {isNaN(num) ? '—' : num.toFixed(4)}{unit}
      </div>
      <div className="text-xs text-gray-400 mt-0.5">{description}</div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Inline text editor over the selection (Canva-style; stops click-to-resegment)
// ---------------------------------------------------------------------------
function InlineTextOverlay({ segResult, value, onChange }) {
  if (!segResult?.bbox || !segResult.img_width) return null
  const [x0, y0, x1, y1] = segResult.bbox
  const { img_width: iw, img_height: ih } = segResult
  const pct = {
    left: `${(x0 / iw) * 100}%`,
    top: `${(y0 / ih) * 100}%`,
    width: `${((x1 - x0) / iw) * 100}%`,
    height: `${((y1 - y0) / ih) * 100}%`,
  }
  return (
    <div
      className="absolute z-20 pointer-events-auto rounded border-2 border-indigo-500/80 bg-white/90 shadow-lg overflow-hidden"
      style={{ ...pct, position: 'absolute' }}
      onMouseDown={(e) => e.stopPropagation()}
      onClick={(e) => e.stopPropagation()}
    >
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        autoFocus
        rows={2}
        className="w-full h-full min-h-[2.5rem] text-sm p-1.5 resize-none bg-transparent border-0 focus:ring-0 focus:outline-none text-gray-900 placeholder:text-gray-400"
        placeholder="Type here — live edit"
        spellCheck="false"
      />
    </div>
  )
}

// ---------------------------------------------------------------------------
// Selection overlay (SVG bbox drawn over the image)
// ---------------------------------------------------------------------------
function SelectionOverlay({ segResult, imgRef, hidden }) {
  if (hidden || !segResult || !imgRef.current) return null
  const { bbox, img_width, img_height } = segResult
  if (!bbox || !img_width || !img_height) return null

  const [x0, y0, x1, y1] = bbox
  const pct = {
    left: `${(x0 / img_width) * 100}%`,
    top: `${(y0 / img_height) * 100}%`,
    width: `${((x1 - x0) / img_width) * 100}%`,
    height: `${((y1 - y0) / img_height) * 100}%`,
  }

  return (
    <div
      className="absolute pointer-events-none border-2 border-red-500 bg-red-500/20 rounded"
      style={{ ...pct, position: 'absolute' }}
    >
      <div className="absolute -top-5 left-0 bg-red-500 text-white text-xs px-1.5 py-0.5 rounded whitespace-nowrap">
        Selected layer · {(segResult.area_fraction * 100).toFixed(1)}% of image
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Image canvas (click-to-select)
// ---------------------------------------------------------------------------
function ImageCanvas({ imageUrl, onLayerSelect, segResult, busy, hideSelectionOverlay, children }) {
  const imgRef = useRef(null)
  const containerRef = useRef(null)

  const handleClick = useCallback(
    (e) => {
      if (busy || !imageUrl) return
      const rect = e.currentTarget.getBoundingClientRect()
      const x = (e.clientX - rect.left) / rect.width
      const y = (e.clientY - rect.top) / rect.height
      onLayerSelect(x, y)
    },
    [busy, imageUrl, onLayerSelect],
  )

  if (!imageUrl) {
    return (
      <div className="flex items-center justify-center w-full aspect-square bg-gray-100 rounded-xl border-2 border-dashed border-gray-300 text-gray-400">
        <div className="text-center">
          <Layers className="w-10 h-10 mx-auto mb-2 opacity-40" />
          <p className="text-sm">Compose an image to begin</p>
        </div>
      </div>
    )
  }

  return (
    <div
      ref={containerRef}
      className={`relative rounded-xl overflow-hidden shadow-lg select-none ${busy ? 'opacity-70' : 'cursor-crosshair'}`}
      onClick={handleClick}
    >
      <img
        ref={imgRef}
        src={resolveAssetUrl(imageUrl)}
        alt="Editing canvas"
        className="w-full block"
        draggable={false}
      />
      <SelectionOverlay segResult={segResult} imgRef={imgRef} hidden={hideSelectionOverlay} />
      {children}
      {busy && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/30">
          <Loader2 className="w-10 h-10 text-white animate-spin" />
        </div>
      )}
      {!busy && imageUrl && (
        <div className="absolute bottom-2 left-2 bg-black/60 text-white text-xs px-2 py-1 rounded pointer-events-none">
          <Crosshair className="inline w-3 h-3 mr-1" />
          Click to select a layer
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Edit history row
// ---------------------------------------------------------------------------
function HistoryRow({ edit, onRestore }) {
  const bg = edit.conditioned ? 'bg-indigo-50 border-indigo-200' : 'bg-gray-50 border-gray-200'
  return (
    <div className={`rounded-lg border p-2.5 text-xs ${bg}`}>
      <div className="flex items-center justify-between mb-1">
        <span className="font-medium text-gray-700">{edit.layer_name || 'layer'}</span>
        <span className={`px-1.5 py-0.5 rounded text-white text-[10px] ${edit.conditioned ? 'bg-indigo-500' : 'bg-gray-400'}`}>
          {edit.conditioned ? 'conditioned' : 'ablation'}
        </span>
      </div>
      <div className="text-gray-500 space-x-3">
        {edit.background_ssim != null && <span>SSIM {Number(edit.background_ssim).toFixed(4)}</span>}
        {edit.brand_delta_e != null && <span>ΔE {Number(edit.brand_delta_e).toFixed(2)}</span>}
      </div>
      {onRestore && edit.result_url && (
        <button
          onClick={() => onRestore(edit.result_url)}
          className="mt-1.5 text-indigo-600 hover:underline text-[10px]"
        >
          Restore this result
        </button>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main LayerEditor component
// ---------------------------------------------------------------------------
export default function LayerEditor({ brandId, brandContext }) {
  // ── State ──────────────────────────────────────────────────────────────
  const [baseImageUrl, setBaseImageUrl] = useState(null)
  const [currentImageUrl, setCurrentImageUrl] = useState(null)
  const [segResult, setSegResult] = useState(null)
  const [editResult, setEditResult] = useState(null)
  const [editHistory, setEditHistory] = useState([])   // local session history
  const [savedHistory, setSavedHistory] = useState([]) // from Neo4j

  const [prompt, setPrompt] = useState('')
  const [newText, setNewText] = useState('')
  const [textMode, setTextMode] = useState(false)
  const [composePrompt, setComposePrompt] = useState('')
  const [aspectRatio, setAspectRatio] = useState('1:1')
  const [conditioned, setConditioned] = useState(true)
  const [layerName, setLayerName] = useState('object')
  const [seed, setSeed] = useState('')
  const [selectionScale, setSelectionScale] = useState(1)
  const [textColor, setTextColor] = useState('#1a1a1a')
  const [textFontScale, setTextFontScale] = useState(1)

  const [phase, setPhase] = useState('idle')  // idle | composing | segmenting | editing
  const [error, setError] = useState(null)
  const [composeMeta, setComposeMeta] = useState(null)

  const fileRef = useRef(null)

  // ── Load saved history ──────────────────────────────────────────────────
  useEffect(() => {
    if (!brandId) return
    getLayerHistory(brandId)
      .then((d) => setSavedHistory(d.edits || []))
      .catch(() => {})
  }, [brandId, editHistory.length])

  // ── Compose ─────────────────────────────────────────────────────────────
  const handleCompose = async () => {
    if (!composePrompt.trim()) return
    setError(null)
    setSegResult(null)
    setEditResult(null)
    setPhase('composing')
    try {
      const result = await composeImage({
        brand_id: brandId || undefined,
        prompt: composePrompt,
        aspect_ratio: aspectRatio,
        seed: seed ? parseInt(seed) : undefined,
      })
      setBaseImageUrl(result.image_url)
      setCurrentImageUrl(result.image_url)
      setComposeMeta({
        method: result.method,
        attempts: result.attempts,
        prompt_used: result.prompt_used,
        graph_rag: result.graph_rag,
      })
    } catch (e) {
      setComposeMeta(null)
      setError(`Compose failed: ${formatAxiosError(e)}`)
    } finally {
      setPhase('idle')
    }
  }

  // ── File upload ─────────────────────────────────────────────────────────
  const handleFileUpload = (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (ev) => {
      setBaseImageUrl(ev.target.result)
      setCurrentImageUrl(ev.target.result)
      setSegResult(null)
      setEditResult(null)
      setError(null)
    }
    reader.readAsDataURL(file)
  }

  // ── Segment (click-to-mask) ──────────────────────────────────────────────
  const handleLayerSelect = useCallback(
    async (x, y) => {
      if (!currentImageUrl || phase !== 'idle') return
      setError(null)
      setPhase('segmenting')
      try {
        const result = await segmentLayer({
          image_url: currentImageUrl,
          click_x: x,
          click_y: y,
          label: textMode ? 'text' : layerName,
          selection_scale: selectionScale,
        })
        setSegResult(result)
        setEditResult(null)
      } catch (e) {
        setError(`Segment failed: ${e.message}`)
      } finally {
        setPhase('idle')
      }
    },
    [currentImageUrl, layerName, phase, textMode, selectionScale],
  )

  // ── Edit layer ───────────────────────────────────────────────────────────
  const handleEdit = async () => {
    if (!currentImageUrl || !segResult?.mask_url) return
    const effectivePrompt = textMode ? newText : prompt
    if (!effectivePrompt.trim()) return
    setError(null)
    setPhase('editing')
    try {
      const result = await editLayer({
        image_url: currentImageUrl,
        mask_url: segResult.mask_url,
        brand_id: brandId || undefined,
        prompt: effectivePrompt,
        layer_name: textMode ? 'text' : layerName,
        conditioned,
        seed: seed ? parseInt(seed) : undefined,
        text_mode: textMode,
        new_text: textMode ? newText : undefined,
        text_color_hex: textMode ? textColor : undefined,
        text_font_scale: textMode ? textFontScale : undefined,
      })
      setEditResult(result)
      setCurrentImageUrl(result.result_url)
      setSegResult(null)
      setEditHistory((h) => [
        {
          ...result,
          result_url: result.result_url,
          layer_name: textMode ? 'text' : layerName,
          conditioned,
        },
        ...h,
      ])
    } catch (e) {
      setError(`Edit failed: ${formatAxiosError(e)}`)
    } finally {
      setPhase('idle')
    }
  }

  // ── Undo ──────────────────────────────────────────────────────────────────
  const handleUndo = () => {
    const prev = editHistory[1]
    if (prev) {
      setCurrentImageUrl(prev.result_url)
    } else {
      setCurrentImageUrl(baseImageUrl)
    }
    setEditHistory((h) => h.slice(1))
    setSegResult(null)
    setEditResult(null)
  }

  const effectivePrompt = textMode ? newText : prompt
  const canEdit = currentImageUrl && segResult?.mask_url && effectivePrompt.trim() && phase === 'idle'
  const canUndo = editHistory.length > 0
  const busy = phase !== 'idle'

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="grid grid-cols-1 xl:grid-cols-[1fr_360px] gap-4">
      {/* ── Left: canvas + controls ── */}
      <div className="space-y-4">

        {/* Compose strip */}
        <div className="bg-white rounded-xl shadow-sm p-4 space-y-3">
          <h3 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-indigo-500" />
            Compose base image
          </h3>
          <div className="flex gap-2">
            <input
              value={composePrompt}
              onChange={(e) => setComposePrompt(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleCompose()}
              placeholder="e.g. premium skincare product shot on marble surface"
              className="flex-1 text-sm border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-300"
            />
            <select
              value={aspectRatio}
              onChange={(e) => setAspectRatio(e.target.value)}
              className="text-sm border rounded-lg px-2 py-2"
            >
              {['1:1', '16:9', '9:16', '4:3', '3:4'].map((r) => (
                <option key={r}>{r}</option>
              ))}
            </select>
            <button
              onClick={handleCompose}
              disabled={busy || !composePrompt.trim()}
              className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg disabled:opacity-40 flex items-center gap-1.5 hover:bg-indigo-700"
            >
              {phase === 'composing' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
              Generate
            </button>
            <button
              onClick={() => fileRef.current?.click()}
              title="Upload your own image"
              className="px-3 py-2 border rounded-lg text-gray-600 hover:bg-gray-50"
            >
              <Upload className="w-4 h-4" />
            </button>
            <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={handleFileUpload} />
          </div>
          <p className="text-xs text-gray-500 leading-relaxed">
            Generation tries, in order: <strong>OpenRouter Nano Banana</strong>{' '}
            (google/gemini-2.5-flash-image — strong at text-in-image) →{' '}
            <strong>Replicate FLUX</strong> → your <strong>ComfyUI / Hugging Face SDXL</strong> stack.
            No decorative placeholder: if everything fails, you will see an error with the exact reason.
            {brandId && (
              <>
                {' '}
                With a brand selected, palette and style tokens from the graph are prepended to the prompt.
              </>
            )}
          </p>
        </div>

        {/* Image canvas */}
        <div className="bg-white rounded-xl shadow-sm p-4 space-y-2">
          <div className="flex items-center gap-3 text-xs text-gray-600">
            <label className="flex items-center gap-2 shrink-0">
              <span className="text-gray-500 whitespace-nowrap">Selection size</span>
              <input
                type="range"
                min={0.35}
                max={2.5}
                step={0.05}
                value={selectionScale}
                onChange={(e) => setSelectionScale(parseFloat(e.target.value))}
                className="w-32 accent-indigo-600"
              />
              <span className="font-mono w-8">{selectionScale.toFixed(2)}×</span>
            </label>
            <span className="text-gray-400 hidden sm:inline">
              Applies to the next click (smaller = tighter mask, larger = bigger edit area).
            </span>
          </div>
          <ImageCanvas
            imageUrl={currentImageUrl}
            onLayerSelect={handleLayerSelect}
            segResult={segResult}
            busy={busy && phase !== 'composing'}
            hideSelectionOverlay={textMode && !!segResult}
          >
            {textMode && segResult && (
              <InlineTextOverlay segResult={segResult} value={newText} onChange={setNewText} />
            )}
          </ImageCanvas>
          {composeMeta && (
            <div className="text-xs text-gray-600 mt-2 space-y-1">
              <p className="font-mono bg-gray-50 rounded-lg px-2 py-1.5 border border-gray-100">
                <span className="text-gray-400">Source:</span> {composeMeta.method}
                {composeMeta.attempts?.length ? (
                  <span className="text-gray-400"> · {composeMeta.attempts.join(' · ')}</span>
                ) : null}
              </p>
              {composeMeta.graph_rag && (
                <p className="text-gray-500 leading-snug">
                  <span className="font-medium text-gray-600">Graph-RAG:</span>{' '}
                  {composeMeta.graph_rag.applied
                    ? `on — brand context from Neo4j (${(composeMeta.graph_rag.signals || []).length} conditioning fields).`
                    : 'off — pick a brand or add a brand_id to enable palette/style retrieval.'}
                </p>
              )}
            </div>
          )}
          {phase === 'segmenting' && (
            <p className="text-xs text-center text-gray-500 mt-2 animate-pulse">Generating mask…</p>
          )}
        </div>

        {/* Edit controls */}
        <div className="bg-white rounded-xl shadow-sm p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
              <Layers className="w-4 h-4 text-indigo-500" />
              Edit selected layer
              {!segResult && <span className="text-xs font-normal text-gray-400">— click the image to select a layer first</span>}
            </h3>

            {/* Mode segmented control: region vs. text */}
            <div className="inline-flex rounded-lg border border-gray-200 overflow-hidden text-xs">
              <button
                type="button"
                onClick={() => {
                  setTextMode(false)
                  setSegResult(null)
                }}
                className={`px-3 py-1.5 flex items-center gap-1 ${!textMode ? 'bg-indigo-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'}`}
              >
                <Sparkles className="w-3 h-3" />
                Region
              </button>
              <button
                type="button"
                onClick={() => {
                  setTextMode(true)
                  setSegResult(null)
                }}
                className={`px-3 py-1.5 flex items-center gap-1 ${textMode ? 'bg-indigo-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'}`}
              >
                <Type className="w-3 h-3" />
                Text
              </button>
            </div>
          </div>

          {textMode ? (
            <div className="space-y-2">
              <p className="text-xs text-gray-500">
                Click the text on the image — an editor appears on the canvas (like Canva). Adjust colour and size, then apply to bake pixels into the image.
              </p>
              <div className="flex flex-wrap items-center gap-3">
                <label className="flex items-center gap-1.5 text-xs text-gray-600">
                  Ink
                  <input
                    type="color"
                    value={textColor}
                    onChange={(e) => setTextColor(e.target.value)}
                    className="h-8 w-10 rounded border cursor-pointer"
                  />
                </label>
                <label className="flex items-center gap-2 text-xs text-gray-600">
                  Type size
                  <input
                    type="range"
                    min={0.4}
                    max={3}
                    step={0.05}
                    value={textFontScale}
                    onChange={(e) => setTextFontScale(parseFloat(e.target.value))}
                    className="w-28 accent-indigo-600"
                  />
                  <span className="font-mono w-8">{textFontScale.toFixed(2)}×</span>
                </label>
              </div>
            </div>
          ) : (
            <div className="flex gap-2">
              <input
                value={layerName}
                onChange={(e) => setLayerName(e.target.value)}
                placeholder="Layer name (e.g. product, logo, background)"
                className="w-36 text-sm border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-300"
              />
              <input
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && canEdit && handleEdit()}
                placeholder="Describe the change… e.g. replace with a summer version"
                className="flex-1 text-sm border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-300"
              />
            </div>
          )}

          <div className="flex items-center gap-3 flex-wrap">
            {/* Conditioned toggle */}
            <label className="flex items-center gap-2 text-sm cursor-pointer select-none">
              <input
                type="checkbox"
                checked={conditioned}
                onChange={(e) => setConditioned(e.target.checked)}
                className="accent-indigo-600"
              />
              <span className="font-medium text-gray-700">Graph conditioned</span>
              <span className="text-xs text-gray-400">(uncheck for ablation)</span>
            </label>

            {/* Seed */}
            <input
              value={seed}
              onChange={(e) => setSeed(e.target.value)}
              placeholder="Seed (optional)"
              className="w-28 text-sm border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-300"
            />

            {/* Actions */}
            <div className="ml-auto flex gap-2">
              {canUndo && (
                <button
                  onClick={handleUndo}
                  className="flex items-center gap-1.5 px-3 py-2 border rounded-lg text-sm text-gray-600 hover:bg-gray-50"
                >
                  <Undo2 className="w-4 h-4" />
                  Undo
                </button>
              )}
              {currentImageUrl && (
                <a
                  href={resolveAssetUrl(currentImageUrl)}
                  download="layer-edit.png"
                  className="flex items-center gap-1.5 px-3 py-2 border rounded-lg text-sm text-gray-600 hover:bg-gray-50"
                >
                  <Download className="w-4 h-4" />
                  Download
                </a>
              )}
              <button
                onClick={handleEdit}
                disabled={!canEdit}
                className="flex items-center gap-1.5 px-5 py-2 bg-indigo-600 text-white text-sm rounded-lg disabled:opacity-40 hover:bg-indigo-700"
              >
                {phase === 'editing' ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : conditioned ? (
                  <Sparkles className="w-4 h-4" />
                ) : (
                  <FlaskConical className="w-4 h-4" />
                )}
                {textMode ? 'Apply text' : conditioned ? 'Edit (conditioned)' : 'Edit (ablation)'}
              </button>
            </div>
          </div>

          {error && (
            <div className="text-xs text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              {error}
            </div>
          )}
        </div>
      </div>

      {/* ── Right: metrics + history ── */}
      <div className="space-y-4">

        {/* Latest edit metrics */}
        {editResult && (
          <div className="bg-white rounded-xl shadow-sm p-4 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-gray-700">Edit metrics</h3>
              <span className={`text-xs px-2 py-0.5 rounded-full ${editResult.conditioned ? 'bg-indigo-100 text-indigo-700' : 'bg-gray-100 text-gray-600'}`}>
                {editResult.conditioned ? 'conditioned' : 'ablation'}
              </span>
            </div>

            <MetricCard
              label="Background SSIM"
              value={editResult.metrics?.background_ssim}
              ideal="high"
              description="Non-edited pixels unchanged. 1.0 = pixel-exact isolation."
            />
            <MetricCard
              label="Brand ΔE"
              value={editResult.metrics?.brand_delta_e}
              ideal="low"
              description="Colour distance from brand palette (CIEDE2000). Lower = more on-brand."
            />
            {editResult.metrics?.identity_ssim != null && (
              <MetricCard
                label="Identity SSIM"
                value={editResult.metrics?.identity_ssim}
                ideal="high"
                description="Histogram similarity to brand reference image."
              />
            )}

            <div className="text-xs text-gray-400 pt-1 border-t border-gray-100 space-y-0.5">
              <div><span className="font-medium">Method:</span> {editResult.method}</div>
              {editResult.text_mode && (
                <div className="text-indigo-600">
                  <span className="font-medium">Live text</span> (Pillow raster — not an image model)
                </div>
              )}
              {editResult.graph_rag && (
                <div>
                  <span className="font-medium">Graph-RAG:</span>{' '}
                  {editResult.graph_rag.applied
                    ? `on — ${editResult.graph_rag.palette_used_in_metrics ?? 0} valid palette swatches for ΔE`
                    : 'off'}
                </div>
              )}
              <div className="truncate"><span className="font-medium">Prompt:</span> {editResult.prompt_used}</div>
              {editResult.conditioning_applied && Object.keys(editResult.conditioning_applied).length > 0 && (
                <div>
                  <span className="font-medium">Conditioning:</span>{' '}
                  {Object.entries(editResult.conditioning_applied)
                    .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(', ') : v}`)
                    .join(' · ')}
                </div>
              )}
              {editResult.attempts?.length > 0 && (
                <div className="text-[10px] font-mono break-words">
                  <span className="font-medium">Attempts:</span> {editResult.attempts.join(' · ')}
                </div>
              )}
            </div>

            {/* Before / After thumbnails */}
            {editResult.inpaint_url && (
              <div className="grid grid-cols-2 gap-2 pt-1">
                <div>
                  <p className="text-[10px] text-gray-400 mb-1">Before edit</p>
                  <img
                    src={resolveAssetUrl(baseImageUrl)}
                    alt="before"
                    className="w-full rounded-lg border"
                  />
                </div>
                <div>
                  <p className="text-[10px] text-gray-400 mb-1">After edit</p>
                  <img
                    src={resolveAssetUrl(editResult.result_url)}
                    alt="after"
                    className="w-full rounded-lg border"
                  />
                </div>
              </div>
            )}
          </div>
        )}

        {/* Brand conditioning context */}
        {brandContext && (
          <div className="bg-white rounded-xl shadow-sm p-4 space-y-2">
            <h3 className="text-sm font-semibold text-gray-700">Brand conditioning</h3>
            {brandContext.palette_hex?.length > 0 && (
              <div className="flex gap-1.5 flex-wrap">
                {brandContext.palette_hex.map((h) => (
                  <div
                    key={h}
                    title={h}
                    className="w-7 h-7 rounded border border-gray-200 shadow-sm"
                    style={{ background: h }}
                  />
                ))}
              </div>
            )}
            {brandContext.style_keywords?.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {brandContext.style_keywords.map((k) => (
                  <span key={k} className="text-xs bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded-full">
                    {k}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Session history */}
        {editHistory.length > 0 && (
          <div className="bg-white rounded-xl shadow-sm p-4 space-y-2">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
                <RefreshCw className="w-4 h-4 text-gray-400" />
                Session edits ({editHistory.length})
              </h3>
            </div>
            <div className="space-y-2 max-h-80 overflow-y-auto">
              {editHistory.map((edit, i) => (
                <HistoryRow
                  key={edit.edit_id || i}
                  edit={edit}
                  onRestore={(url) => {
                    setCurrentImageUrl(url)
                    setSegResult(null)
                    setEditResult(null)
                  }}
                />
              ))}
            </div>
          </div>
        )}

        {/* Persisted history from Neo4j */}
        {savedHistory.length > 0 && (
          <div className="bg-white rounded-xl shadow-sm p-4 space-y-2">
            <h3 className="text-sm font-semibold text-gray-700">Saved brand history</h3>
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {savedHistory.map((edit) => (
                <HistoryRow key={edit.edit_id} edit={edit} onRestore={null} />
              ))}
            </div>
          </div>
        )}

        {/* Empty state guide */}
        {!editResult && editHistory.length === 0 && (
          <div className="bg-white rounded-xl shadow-sm p-6 text-center text-gray-400 space-y-3">
            <Crosshair className="w-8 h-8 mx-auto opacity-30" />
            <div className="text-sm space-y-1">
              <p className="font-medium text-gray-600">How it works</p>
              <p>1. Generate or upload a base image</p>
              <p>2. Click any region — an object, a product, or a piece of text</p>
              <p>3a. <strong>Region</strong> mode: describe the change (e.g. "make it gold")</p>
              <p>3b. <strong>Text</strong> mode: edit in the on-canvas box, then <strong>Apply text</strong> (vector-style control, rasterised with Pillow)</p>
              <p>4. <strong>Region</strong> edits use OpenRouter / Replicate inpainting on the selection only</p>
              <p>5. Compositor pastes through the mask so everything outside stays pixel-exact</p>
              <p>6. Use <strong>Selection size</strong> to widen or tighten the next mask</p>
              <p>7. Toggle <em>Ablation</em> to compare with and without graph conditioning</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
