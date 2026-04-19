/**
 * V2 API Service — Graph-RAG 3D-First Pipeline
 *
 * Thin wrappers around /api/v2/* endpoints. Every call returns raw response
 * data; callers handle UI-level error states. The backend is expected to run
 * at API_BASE_URL in mock mode during local development.
 */
import axios from 'axios';
import { API_BASE_URL } from './api';

const v2 = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 180000,
});

v2.interceptors.response.use(
  (r) => r,
  (err) => {
    const msg = err.response?.data?.detail || err.message || 'V2 API error';
    return Promise.reject(new Error(msg));
  }
);

export const V2_API_BASE = API_BASE_URL;

// Resolve a potentially relative upload path to an absolute URL.
export const resolveAssetUrl = (url) => {
  if (!url) return null;
  if (/^(data:|https?:|blob:)/.test(url)) return url;
  if (url.startsWith('/uploads/')) return `${API_BASE_URL}${url}`;
  return url;
};

// ============== Health ==============

export const v2Health = () => v2.get('/api/v2/health').then((r) => r.data);

// ============== Brands ==============

// The backend only exposes POST + GET /{id} for V2 brands, so we track the
// user's created brand IDs locally and hydrate each one on demand.
const BRAND_STORAGE_KEY = 'v2_brand_ids';

export const recordLocalV2Brand = (brandId) => {
  try {
    const ids = JSON.parse(localStorage.getItem(BRAND_STORAGE_KEY) || '[]');
    if (!ids.includes(brandId)) {
      ids.unshift(brandId);
      localStorage.setItem(BRAND_STORAGE_KEY, JSON.stringify(ids.slice(0, 50)));
    }
  } catch {
    /* localStorage unavailable */
  }
};

export const listLocalV2Brands = () => {
  try {
    return JSON.parse(localStorage.getItem(BRAND_STORAGE_KEY) || '[]');
  } catch {
    return [];
  }
};

export const createV2Brand = (payload) =>
  v2.post('/api/v2/brands', payload).then((r) => r.data);

export const getV2Brand = (brandId) =>
  v2.get(`/api/v2/brands/${brandId}`).then((r) => r.data);

export const getRetrievalPreview = (brandId, deploymentContext = 'digital') =>
  v2
    .get(`/api/v2/brands/${brandId}/retrieval-preview`, {
      params: { deployment_context: deploymentContext },
    })
    .then((r) => r.data);

export const listPreferences = (brandId) =>
  v2.get(`/api/v2/brands/${brandId}/preferences`).then((r) => r.data);

export const deletePreference = (brandId, signalId) =>
  v2
    .delete(`/api/v2/brands/${brandId}/preferences/${signalId}`)
    .then((r) => r.data);

// ============== Assets ==============

export const listAssets = (brandId, status = null) =>
  v2
    .get('/api/v2/assets', { params: { brand_id: brandId, status: status || undefined } })
    .then((r) => r.data);

export const getAsset = (assetId) =>
  v2.get(`/api/v2/assets/${assetId}`).then((r) => r.data);

export const ingestAsset = ({ brandId, assetType, sourceImageUrl, sync = true }) =>
  v2
    .post('/api/v2/assets', {
      brand_id: brandId,
      asset_type: assetType,
      source_image_url: sourceImageUrl,
      sync,
    })
    .then((r) => r.data);

export const approveAsset = (assetId) =>
  v2.post(`/api/v2/assets/${assetId}/approve`).then((r) => r.data);

export const rejectAsset = (assetId, reason = null) =>
  v2
    .post(`/api/v2/assets/${assetId}/reject`, null, { params: reason ? { reason } : {} })
    .then((r) => r.data);

export const regeneratePart = (assetId, partId, strategy = 'crop_and_realign') =>
  v2
    .post(`/api/v2/assets/${assetId}/regenerate-part`, { part_id: partId, strategy })
    .then((r) => r.data);

// ============== Scenes ==============

export const createScene = ({
  brandId,
  intentText,
  deploymentContext = 'digital',
  cameras,
  sync = true,
}) =>
  v2
    .post('/api/v2/scenes', {
      brand_id: brandId,
      intent_text: intentText,
      deployment_context: deploymentContext,
      cameras,
      sync,
    })
    .then((r) => r.data);

export const getScene = (sceneId) =>
  v2.get(`/api/v2/scenes/${sceneId}`).then((r) => r.data);

export const rerenderScene = (sceneId, cameraIds = null) =>
  v2
    .post(`/api/v2/scenes/${sceneId}/render`, { camera_ids: cameraIds })
    .then((r) => r.data);

export const getRender = (renderId) =>
  v2.get(`/api/v2/renders/${renderId}`).then((r) => r.data);

export const resolveObjectAtPixel = (renderId, x, y) =>
  v2
    .get(`/api/v2/renders/${renderId}/object-at`, { params: { x, y } })
    .then((r) => r.data);

// ============== Interactions (Pipeline C) ==============

export const sendStructuredInteraction = (payload) =>
  v2.post('/api/v2/interactions/structured', payload).then((r) => r.data);

export const sendNlInteraction = (payload) =>
  v2.post('/api/v2/interactions/natural-language', payload).then((r) => r.data);

export const listRecentInteractions = (brandId, limit = 25) =>
  v2
    .get('/api/v2/interactions/recent', { params: { brand_id: brandId, limit } })
    .then((r) => r.data);

// ============== Layer Editing (core research loop) ==============

/**
 * Generate a full brand-aligned composition as the editing canvas.
 * @param {{ brand_id?, prompt, aspect_ratio?, seed? }} payload
 */
export const composeImage = (payload) =>
  v2.post('/api/v2/compose', payload).then((r) => r.data);

/**
 * Click-to-mask: returns mask_url, bbox, img_width, img_height, area_fraction.
 * @param {{ image_url, click_x, click_y, label? }} payload
 */
export const segmentLayer = (payload) =>
  v2.post('/api/v2/layers/segment', {
    selection_scale: 1,
    ...payload,
  }).then((r) => r.data);

/**
 * Brand-conditioned inpaint + composite + measure.
 * Returns result_url, metrics {background_ssim, brand_delta_e, identity_ssim}, method.
 * Set conditioned=false for ablation (no graph conditioning).
 * @param {{ image_url, mask_url, brand_id?, prompt, layer_name?, conditioned?, seed? }} payload
 */
export const editLayer = (payload) =>
  v2.post('/api/v2/layers/edit', payload).then((r) => r.data);

/**
 * Fetch edit history for a brand from Neo4j.
 */
export const getLayerHistory = (brandId, limit = 20) =>
  v2.get(`/api/v2/layers/history/${brandId}`, { params: { limit } }).then((r) => r.data);

// ============== Jobs ==============

export const getJob = (jobId) =>
  v2.get(`/api/v2/jobs/${jobId}`).then((r) => r.data);

export const streamJob = (jobId, onUpdate) => {
  const ctrl = new AbortController();
  (async () => {
    try {
      const resp = await fetch(`${API_BASE_URL}/api/v2/jobs/${jobId}/stream`, {
        signal: ctrl.signal,
      });
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buf = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const events = buf.split('\n\n');
        buf = events.pop() || '';
        for (const e of events) {
          const line = e.split('\n').find((l) => l.startsWith('data: '));
          if (line) {
            try {
              onUpdate(JSON.parse(line.slice(6)));
            } catch {
              /* ignore malformed chunks */
            }
          }
        }
      }
    } catch (e) {
      if (e.name !== 'AbortError') console.error('streamJob error', e);
    }
  })();
  return () => ctrl.abort();
};

export default v2;
