import axios from 'axios'
import { API_BASE_URL } from './api'

const apiV3 = axios.create({
  baseURL: API_BASE_URL,
  timeout: 600000,
})

apiV3.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.detail || error.message || 'An error occurred'
    return Promise.reject(new Error(message))
  }
)

export async function getCapstoneCapabilities() {
  const response = await apiV3.get('/api/v3/capabilities')
  return response.data
}

export async function getCapstoneAccuracyPresets() {
  const response = await apiV3.get('/api/v3/accuracy-presets')
  return response.data
}

export async function uploadCapstoneScene(file, extras = {}) {
  const formData = new FormData()
  formData.append('file', file)
  if (extras.title) formData.append('title', extras.title)
  if (extras.ownerUserId) formData.append('owner_user_id', extras.ownerUserId)
  if (extras.email) formData.append('email', extras.email)

  const response = await apiV3.post('/api/v3/scenes/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return response.data
}

export async function getCapstoneScene(sceneId) {
  const response = await apiV3.get(`/api/v3/scenes/${sceneId}`)
  return response.data
}

export async function segmentCapstoneClick(sceneId, payload) {
  const response = await apiV3.post(`/api/v3/scenes/${sceneId}/segment-click`, payload)
  return response.data
}

export async function removeCapstoneObject(sceneId, payload) {
  const response = await apiV3.post(`/api/v3/scenes/${sceneId}/remove-object`, payload)
  return response.data
}
