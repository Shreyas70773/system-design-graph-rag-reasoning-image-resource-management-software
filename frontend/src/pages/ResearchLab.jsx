import { useEffect, useMemo, useState } from 'react'
import {
  exportResearchExperiment,
  exportResearchRun,
  getResearchManifest,
  runResearchControlledGeneration,
  runResearchDeltaEJob,
  runResearchAblation,
  compareResearchExperiment,
  getResearchStats,
  listResearchRuns,
  validateResearchManifest,
} from '../services/api'
import { getActiveBrandId, setActiveBrandId } from '../services/brandSession'

const DATA_IMAGE_PREFIX = 'data:image/'
const MAX_TEXT_PREVIEW_CHARS = 240

function sanitizeResultForDisplay(value) {
  if (Array.isArray(value)) {
    return value.map((item) => sanitizeResultForDisplay(item))
  }

  if (value && typeof value === 'object') {
    const sanitizedEntries = Object.entries(value).map(([key, nestedValue]) => {
      if (
        key === 'image_url' &&
        typeof nestedValue === 'string' &&
        nestedValue.startsWith(DATA_IMAGE_PREFIX)
      ) {
        const payloadLength = Math.max(0, nestedValue.length - nestedValue.indexOf(',') - 1)
        const approxKb = Math.round(payloadLength / 1024)
        return [
          key,
          `[inline image base64 redacted: ~${approxKb} KB, use candidate preview/download buttons above]`,
        ]
      }

      return [key, sanitizeResultForDisplay(nestedValue)]
    })

    return Object.fromEntries(sanitizedEntries)
  }

  if (typeof value === 'string' && value.length > 800) {
    return `${value.slice(0, MAX_TEXT_PREVIEW_CHARS)} ...[truncated ${value.length - MAX_TEXT_PREVIEW_CHARS} chars]`
  }

  return value
}

function parseSeeds(rawSeeds) {
  return rawSeeds
    .split(',')
    .map((value) => Number.parseInt(value.trim(), 10))
    .filter((value) => Number.isInteger(value) && value >= 0)
}

export default function ResearchLab() {
  const [brandId, setBrandId] = useState(getActiveBrandId())
  const [prompt, setPrompt] = useState('Product hero shot for summer launch with strong brand identity')
  const [methodName, setMethodName] = useState('graph_guided')
  const [imageProvider, setImageProvider] = useState('comfyui')
  const [comfyWorkflowJson, setComfyWorkflowJson] = useState('')
  const [seedsInput, setSeedsInput] = useState('11,22,33')
  const [experimentId, setExperimentId] = useState('')
  const [statsMetric, setStatsMetric] = useState('brand_score')
  const [baselineMethod, setBaselineMethod] = useState('prompt_only')
  const [bootstrapResamples, setBootstrapResamples] = useState(2000)
  const [ciAlpha, setCiAlpha] = useState(0.05)
  const [randomSeed, setRandomSeed] = useState(42)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)

  const parsedSeeds = useMemo(() => parseSeeds(seedsInput), [seedsInput])

  const parseComfyWorkflowIfProvided = () => {
    if (imageProvider !== 'comfyui') {
      return { ok: true, workflow: undefined }
    }

    const rawWorkflow = comfyWorkflowJson.trim()
    if (!rawWorkflow) {
      return { ok: true, workflow: undefined }
    }

    try {
      const parsedWorkflow = JSON.parse(rawWorkflow)
      if (!parsedWorkflow || typeof parsedWorkflow !== 'object' || Array.isArray(parsedWorkflow)) {
        return {
          ok: false,
          message: 'ComfyUI workflow JSON must be an object keyed by node IDs.',
        }
      }

      return { ok: true, workflow: parsedWorkflow }
    } catch (err) {
      return {
        ok: false,
        message: `Invalid ComfyUI workflow JSON: ${err.message}`,
      }
    }
  }

  useEffect(() => {
    if (brandId?.trim()) {
      setActiveBrandId(brandId)
    }
  }, [brandId])

  const basePayload = {
    brand_id: brandId,
    prompt,
    method_name: methodName,
    image_provider: imageProvider,
    experiment_id: experimentId || undefined,
    seeds: parsedSeeds.length ? parsedSeeds : [11, 22, 33],
    module_toggles: {
      color_regularizer: true,
      layout_constraint: true,
      identity_lock: true,
      dynamic_cfg: true,
    },
    use_proxy_color: true,
    use_comfyui: imageProvider === 'comfyui',
  }

  const currentRunId = result?.run_id || result?.run?.id || ''

  const summaryCards = useMemo(() => {
    const cards = []
    const summary = result?.summary || result?.run?.result_summary || null

    if (summary) {
      cards.push({ label: 'Candidates', value: summary.candidate_count ?? '-' })
      cards.push({ label: 'Success Rate', value: summary.success_rate != null ? `${(summary.success_rate * 100).toFixed(1)}%` : '-' })
      cards.push({ label: 'Brand Score Mean', value: summary.brand_score_mean != null ? summary.brand_score_mean.toFixed(3) : '-' })
      cards.push({ label: 'Color Align Mean', value: summary.color_alignment_mean != null ? summary.color_alignment_mean.toFixed(3) : '-' })
      cards.push({ label: 'DeltaE00 Mean', value: summary.delta_e_ciede2000_mean != null ? summary.delta_e_ciede2000_mean.toFixed(3) : '-' })
      cards.push({ label: 'DeltaE00 Pass Rate', value: summary.delta_e_ciede2000_pass_rate_mean != null ? `${(summary.delta_e_ciede2000_pass_rate_mean * 100).toFixed(1)}%` : '-' })
    }

    if (result?.comparison?.run_count != null) {
      cards.push({ label: 'Compared Runs', value: result.comparison.run_count })
    }

    if (result?.result?.pairwise) {
      cards.push({ label: 'Pairwise Tests', value: result.result.pairwise.length })
      const availableWilcoxon = result.result.pairwise.filter((p) => p.wilcoxon?.available).length
      cards.push({ label: 'Wilcoxon Available', value: `${availableWilcoxon}/${result.result.pairwise.length}` })
    }

    if (result?.result?.analysis_config) {
      cards.push({ label: 'Bootstrap N', value: result.result.analysis_config.bootstrap_resamples ?? '-' })
      cards.push({ label: 'CI Alpha', value: result.result.analysis_config.ci_alpha ?? '-' })
    }

    return cards
  }, [result])

  const onRunControlled = async () => {
    if (!brandId || !prompt) {
      setError('Brand ID and prompt are required.')
      return
    }

    const workflowParse = parseComfyWorkflowIfProvided()
    if (!workflowParse.ok) {
      setError(workflowParse.message)
      return
    }

    setLoading(true)
    setError('')
    try {
      const response = await runResearchControlledGeneration({
        ...basePayload,
        comfy_workflow: imageProvider === 'comfyui' ? workflowParse.workflow : undefined,
      })
      setResult(response)
      if (response?.experiment_id) {
        setExperimentId(response.experiment_id)
      }
    } catch (err) {
      setError(err.message || 'Failed to run controlled experiment')
    } finally {
      setLoading(false)
    }
  }

  const onRunAblation = async () => {
    if (!brandId || !prompt) {
      setError('Brand ID and prompt are required.')
      return
    }

    const workflowParse = parseComfyWorkflowIfProvided()
    if (!workflowParse.ok) {
      setError(workflowParse.message)
      return
    }

    setLoading(true)
    setError('')
    try {
      const response = await runResearchAblation({
        brand_id: brandId,
        prompt,
        base_method: 'graph_guided',
        image_provider: imageProvider,
        experiment_id: experimentId || undefined,
        seeds: parsedSeeds.length ? parsedSeeds : [11, 22, 33],
        use_comfyui: imageProvider === 'comfyui',
        comfy_workflow: imageProvider === 'comfyui' ? workflowParse.workflow : undefined,
      })
      setResult(response)
      if (response?.experiment_id) {
        setExperimentId(response.experiment_id)
      }
    } catch (err) {
      setError(err.message || 'Failed to run ablation')
    } finally {
      setLoading(false)
    }
  }

  const onCompareExperiment = async () => {
    if (!experimentId) {
      setError('Experiment ID is required for comparison.')
      return
    }

    setLoading(true)
    setError('')
    try {
      const response = await compareResearchExperiment(experimentId)
      setResult(response)
    } catch (err) {
      setError(err.message || 'Failed to compare experiment runs')
    } finally {
      setLoading(false)
    }
  }

  const onLoadRuns = async () => {
    if (!brandId) {
      setError('Brand ID is required to list runs.')
      return
    }

    setLoading(true)
    setError('')
    try {
      const response = await listResearchRuns(brandId, 20)
      setResult(response)
    } catch (err) {
      setError(err.message || 'Failed to list research runs')
    } finally {
      setLoading(false)
    }
  }

  const onRunStats = async () => {
    if (!experimentId) {
      setError('Experiment ID is required for statistical comparison.')
      return
    }

    setLoading(true)
    setError('')
    try {
      const safeResamples = Number.isFinite(bootstrapResamples) ? Math.max(100, Math.floor(bootstrapResamples)) : 2000
      const safeAlpha = Number.isFinite(ciAlpha) ? Math.min(Math.max(ciAlpha, 0.001), 0.49) : 0.05
      const safeSeed = Number.isFinite(randomSeed) ? Math.max(0, Math.floor(randomSeed)) : 42

      const response = await getResearchStats(experimentId, statsMetric, baselineMethod, {
        bootstrapResamples: safeResamples,
        ciAlpha: safeAlpha,
        randomSeed: safeSeed,
      })
      setResult(response)
    } catch (err) {
      setError(err.message || 'Failed to compute experiment stats')
    } finally {
      setLoading(false)
    }
  }

  const onGetManifest = async () => {
    if (!experimentId) {
      setError('Experiment ID is required to fetch manifest.')
      return
    }

    setLoading(true)
    setError('')
    try {
      const response = await getResearchManifest(experimentId)
      setResult(response)
    } catch (err) {
      setError(err.message || 'Failed to fetch manifest')
    } finally {
      setLoading(false)
    }
  }

  const onValidateManifest = async () => {
    if (!experimentId || !brandId || !prompt) {
      setError('Experiment ID, Brand ID, and prompt are required for manifest validation.')
      return
    }

    setLoading(true)
    setError('')
    try {
      const response = await validateResearchManifest({
        experiment_id: experimentId,
        brand_id: brandId,
        prompt,
        seeds: parsedSeeds.length ? parsedSeeds : [11, 22, 33],
        locked_config: {
          aspect_ratio: basePayload.aspect_ratio || '1:1',
          num_inference_steps: basePayload.num_inference_steps || 30,
          guidance_scale: basePayload.guidance_scale || 7.5,
          use_comfyui: basePayload.use_comfyui || false,
          use_proxy_color: basePayload.use_proxy_color || true,
        },
      })
      setResult(response)
    } catch (err) {
      setError(err.message || 'Failed to validate manifest')
    } finally {
      setLoading(false)
    }
  }

  const onRunDeltaEJob = async () => {
    if (!currentRunId) {
      setError('Run ID is required. Execute or load a run first.')
      return
    }

    setLoading(true)
    setError('')
    try {
      const response = await runResearchDeltaEJob(currentRunId)
      setResult(response)
    } catch (err) {
      setError(err.message || 'Failed to run DeltaE refinement job')
    } finally {
      setLoading(false)
    }
  }

  const downloadBlob = (blob, filename) => {
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    link.click()
    window.URL.revokeObjectURL(url)
  }

  const onExportRun = async (format) => {
    if (!currentRunId) {
      setError('Run ID is required to export run data.')
      return
    }

    setLoading(true)
    setError('')
    try {
      const response = await exportResearchRun(currentRunId, format)
      if (format === 'csv') {
        downloadBlob(response, `run_${currentRunId}.csv`)
      } else {
        setResult(response)
      }
    } catch (err) {
      setError(err.message || 'Failed to export run data')
    } finally {
      setLoading(false)
    }
  }

  const onExportExperiment = async (format) => {
    if (!experimentId) {
      setError('Experiment ID is required to export experiment data.')
      return
    }

    setLoading(true)
    setError('')
    try {
      const response = await exportResearchExperiment(experimentId, format)
      if (format === 'csv') {
        downloadBlob(response, `experiment_${experimentId}.csv`)
      } else {
        setResult(response)
      }
    } catch (err) {
      setError(err.message || 'Failed to export experiment data')
    } finally {
      setLoading(false)
    }
  }

  const comparisonRows = result?.comparison?.runs || result?.rows || []
  const pairwiseRows = result?.result?.pairwise || []
  const candidateRows = result?.candidates || []

  const sanitizedResultText = useMemo(() => {
    if (!result) {
      return 'No run output yet.'
    }
    return JSON.stringify(sanitizeResultForDisplay(result), null, 2)
  }, [result])

  const downloadCandidateImage = (candidate) => {
    const imageUrl = candidate?.image_url
    if (!imageUrl) return

    const anchor = document.createElement('a')
    anchor.href = imageUrl
    anchor.download = `${result?.run_id || 'research_run'}_seed_${candidate.seed || 'unknown'}.png`
    anchor.rel = 'noopener noreferrer'
    anchor.click()
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Research Lab</h1>
        <p className="text-gray-600 mt-2">
          Execute controlled runs, ablations, and experiment comparisons for GraphRAG-guided generation.
        </p>
      </div>

      <div className="bg-white border border-gray-200 rounded-xl p-5 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Brand ID</label>
            <input
              value={brandId}
              onChange={(e) => setBrandId(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="e.g. b2a8f1c0"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Method</label>
            <select
              value={methodName}
              onChange={(e) => setMethodName(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="prompt_only">prompt_only</option>
              <option value="retrieval_prompt">retrieval_prompt</option>
              <option value="adapter_only">adapter_only</option>
              <option value="graph_guided">graph_guided</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Image Provider</label>
            <select
              value={imageProvider}
              onChange={(e) => setImageProvider(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="comfyui">comfyui (local self-hosted)</option>
              <option value="fal.ai">fal.ai (diffusion)</option>
              <option value="replicate">replicate (diffusion)</option>
              <option value="fallback">fallback (policy-gated)</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Seeds</label>
            <input
              value={seedsInput}
              onChange={(e) => setSeedsInput(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="11,22,33"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Experiment ID (optional)</label>
            <input
              value={experimentId}
              onChange={(e) => setExperimentId(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="auto-generated if empty"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Stats Metric</label>
            <select
              value={statsMetric}
              onChange={(e) => setStatsMetric(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="brand_score">brand_score</option>
              <option value="color_alignment_score">color_alignment_score</option>
              <option value="palette_match_rate">palette_match_rate</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Baseline Method</label>
            <select
              value={baselineMethod}
              onChange={(e) => setBaselineMethod(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="prompt_only">prompt_only</option>
              <option value="retrieval_prompt">retrieval_prompt</option>
              <option value="adapter_only">adapter_only</option>
              <option value="graph_guided">graph_guided</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Bootstrap Resamples</label>
            <input
              type="number"
              min={100}
              max={50000}
              value={bootstrapResamples}
              onChange={(e) => setBootstrapResamples(Number(e.target.value))}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">CI Alpha</label>
            <input
              type="number"
              min={0.001}
              max={0.49}
              step={0.001}
              value={ciAlpha}
              onChange={(e) => setCiAlpha(Number(e.target.value))}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Stats Random Seed</label>
            <input
              type="number"
              min={0}
              value={randomSeed}
              onChange={(e) => setRandomSeed(Number(e.target.value))}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Prompt</label>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            rows={4}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </div>

        {imageProvider === 'comfyui' && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">ComfyUI Workflow JSON</label>
            <textarea
              value={comfyWorkflowJson}
              onChange={(e) => setComfyWorkflowJson(e.target.value)}
              rows={8}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-xs focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder='{"3":{"class_type":"KSampler","inputs":{"cfg":7.5}}}'
            />
            <p className="text-xs text-gray-500 mt-1">
              Optional. Leave this blank to use backend auto-workflow with your first local checkpoint.
            </p>
          </div>
        )}

        <div className="flex flex-wrap gap-3">
          <button
            onClick={onRunControlled}
            disabled={loading}
            className="rounded-lg bg-primary-600 text-white px-4 py-2 font-medium hover:bg-primary-700 disabled:opacity-60"
          >
            {loading ? 'Running...' : 'Run Controlled'}
          </button>

          <button
            onClick={onRunAblation}
            disabled={loading}
            className="rounded-lg bg-gray-900 text-white px-4 py-2 font-medium hover:bg-black disabled:opacity-60"
          >
            {loading ? 'Running...' : 'Run Ablation'}
          </button>

          <button
            onClick={onCompareExperiment}
            disabled={loading}
            className="rounded-lg border border-gray-300 bg-white text-gray-800 px-4 py-2 font-medium hover:bg-gray-50 disabled:opacity-60"
          >
            Compare Experiment
          </button>

          <button
            onClick={onLoadRuns}
            disabled={loading}
            className="rounded-lg border border-gray-300 bg-white text-gray-800 px-4 py-2 font-medium hover:bg-gray-50 disabled:opacity-60"
          >
            List Brand Runs
          </button>

          <button
            onClick={onRunStats}
            disabled={loading}
            className="rounded-lg border border-gray-300 bg-white text-gray-800 px-4 py-2 font-medium hover:bg-gray-50 disabled:opacity-60"
          >
            Compute Stats
          </button>

          <button
            onClick={onGetManifest}
            disabled={loading}
            className="rounded-lg border border-gray-300 bg-white text-gray-800 px-4 py-2 font-medium hover:bg-gray-50 disabled:opacity-60"
          >
            Get Manifest
          </button>

          <button
            onClick={onValidateManifest}
            disabled={loading}
            className="rounded-lg border border-gray-300 bg-white text-gray-800 px-4 py-2 font-medium hover:bg-gray-50 disabled:opacity-60"
          >
            Validate Manifest
          </button>

          <button
            onClick={onRunDeltaEJob}
            disabled={loading}
            className="rounded-lg border border-gray-300 bg-white text-gray-800 px-4 py-2 font-medium hover:bg-gray-50 disabled:opacity-60"
          >
            Run DeltaE Job
          </button>

          <button
            onClick={() => onExportRun('json')}
            disabled={loading}
            className="rounded-lg border border-gray-300 bg-white text-gray-800 px-4 py-2 font-medium hover:bg-gray-50 disabled:opacity-60"
          >
            Export Run JSON
          </button>

          <button
            onClick={() => onExportRun('csv')}
            disabled={loading}
            className="rounded-lg border border-gray-300 bg-white text-gray-800 px-4 py-2 font-medium hover:bg-gray-50 disabled:opacity-60"
          >
            Export Run CSV
          </button>

          <button
            onClick={() => onExportExperiment('json')}
            disabled={loading}
            className="rounded-lg border border-gray-300 bg-white text-gray-800 px-4 py-2 font-medium hover:bg-gray-50 disabled:opacity-60"
          >
            Export Experiment JSON
          </button>

          <button
            onClick={() => onExportExperiment('csv')}
            disabled={loading}
            className="rounded-lg border border-gray-300 bg-white text-gray-800 px-4 py-2 font-medium hover:bg-gray-50 disabled:opacity-60"
          >
            Export Experiment CSV
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-700 text-sm">
          {error}
        </div>
      )}

      {summaryCards.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-6 gap-3">
          {summaryCards.map((card) => (
            <div key={card.label} className="bg-white border border-gray-200 rounded-lg p-3">
              <div className="text-xs uppercase tracking-wide text-gray-500">{card.label}</div>
              <div className="text-lg font-semibold text-gray-900 mt-1">{card.value}</div>
            </div>
          ))}
        </div>
      )}

      {comparisonRows.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-xl p-4 overflow-x-auto">
          <div className="text-sm font-semibold text-gray-900 mb-3">Comparison Table</div>
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left text-gray-600 border-b border-gray-200">
                <th className="py-2 pr-4">Method</th>
                <th className="py-2 pr-4">Status</th>
                <th className="py-2 pr-4">Brand Score Mean</th>
                <th className="py-2 pr-4">Color Align Mean</th>
                <th className="py-2 pr-4">DeltaE00 Mean</th>
                <th className="py-2 pr-4">Latency Mean (ms)</th>
              </tr>
            </thead>
            <tbody>
              {comparisonRows.map((row, idx) => {
                const source = row.summary || row
                return (
                  <tr key={`${row.run_id || idx}-${row.method_name || idx}`} className="border-b border-gray-100">
                    <td className="py-2 pr-4 font-medium text-gray-900">{row.method_name || '-'}</td>
                    <td className="py-2 pr-4 text-gray-700">{row.status || '-'}</td>
                    <td className="py-2 pr-4 text-gray-700">{source.brand_score_mean ?? '-'}</td>
                    <td className="py-2 pr-4 text-gray-700">{source.color_alignment_mean ?? '-'}</td>
                    <td className="py-2 pr-4 text-gray-700">{source.delta_e_ciede2000_mean ?? '-'}</td>
                    <td className="py-2 pr-4 text-gray-700">{source.latency_ms_mean ?? '-'}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {pairwiseRows.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-xl p-4 overflow-x-auto">
          <div className="text-sm font-semibold text-gray-900 mb-3">Pairwise Statistical Results</div>
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left text-gray-600 border-b border-gray-200">
                <th className="py-2 pr-4">Target Method</th>
                <th className="py-2 pr-4">Pairs</th>
                <th className="py-2 pr-4">Delta Mean</th>
                <th className="py-2 pr-4">Delta Mean CI</th>
                <th className="py-2 pr-4">Wilcoxon p</th>
                <th className="py-2 pr-4">Sign Test p</th>
                <th className="py-2 pr-4">Holm p</th>
                <th className="py-2 pr-4">Cohen dz</th>
              </tr>
            </thead>
            <tbody>
              {pairwiseRows.map((row, idx) => (
                <tr key={`${row.target_method}-${idx}`} className="border-b border-gray-100">
                  <td className="py-2 pr-4 font-medium text-gray-900">{row.target_method}</td>
                  <td className="py-2 pr-4 text-gray-700">{row.n_pairs}</td>
                  <td className="py-2 pr-4 text-gray-700">{row.delta_mean != null ? row.delta_mean.toFixed(4) : '-'}</td>
                  <td className="py-2 pr-4 text-gray-700">
                    {row.delta_mean_ci
                      ? `[${row.delta_mean_ci.ci_lower.toFixed(4)}, ${row.delta_mean_ci.ci_upper.toFixed(4)}]`
                      : '-'}
                  </td>
                  <td className="py-2 pr-4 text-gray-700">{row.wilcoxon?.p_value != null ? row.wilcoxon.p_value.toFixed(6) : 'fallback'}</td>
                  <td className="py-2 pr-4 text-gray-700">{row.sign_test?.p_value != null ? row.sign_test.p_value.toFixed(6) : '-'}</td>
                  <td className="py-2 pr-4 text-gray-700">{row.p_value_adjusted_holm != null ? row.p_value_adjusted_holm.toFixed(6) : '-'}</td>
                  <td className="py-2 pr-4 text-gray-700">{row.effect_size?.cohen_dz != null ? row.effect_size.cohen_dz.toFixed(4) : '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {candidateRows.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-xl p-4">
          <div className="text-sm font-semibold text-gray-900 mb-3">Candidate Preview</div>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {candidateRows.map((candidate, idx) => {
              const imageUrl = candidate?.image_url
              const isImage = typeof imageUrl === 'string' && imageUrl.startsWith(DATA_IMAGE_PREFIX)

              return (
                <div key={`${candidate.seed || idx}-${candidate.candidate_id || idx}`} className="border border-gray-200 rounded-lg p-3">
                  <div className="flex items-center justify-between text-sm mb-2">
                    <span className="font-medium text-gray-900">Seed {candidate.seed ?? '-'}</span>
                    <span className="text-gray-600">{candidate.status || 'unknown'}</span>
                  </div>

                  {imageUrl ? (
                    <img
                      src={imageUrl}
                      alt={`Candidate ${candidate.seed ?? idx}`}
                      className="w-full h-40 object-cover rounded-md border border-gray-100 bg-gray-50"
                    />
                  ) : (
                    <div className="w-full h-40 rounded-md border border-dashed border-gray-300 bg-gray-50 flex items-center justify-center text-xs text-gray-500">
                      No image returned
                    </div>
                  )}

                  <div className="mt-3 flex items-center justify-between">
                    <span className="text-xs text-gray-500">{candidate.model_used || candidate.provider || '-'}</span>
                    {imageUrl && (
                      <button
                        type="button"
                        onClick={() => downloadCandidateImage(candidate)}
                        className="text-xs px-2 py-1 rounded border border-gray-300 hover:bg-gray-50"
                      >
                        {isImage ? 'Download PNG' : 'Open Image'}
                      </button>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      <div className="bg-gray-900 text-gray-100 rounded-xl p-4 overflow-x-auto">
        <div className="text-xs uppercase tracking-wide text-gray-400 mb-2">Result</div>
        <pre className="text-xs leading-relaxed whitespace-pre-wrap break-all">
          {sanitizedResultText}
        </pre>
      </div>
    </div>
  )
}
