import { api } from './client'
import { getCacheRecommendations } from './cache.js'

const env = window.__ENV__ ?? {}

// Runtime config in production, VITE_* from .env in local dev
const inference_service_url = env.INFERENCE_SERVICE_URL ?? import.meta.env.VITE_INFERENCE_SERVICE_URL

export const getRecommendations = (message = null) =>
  api(`${inference_service_url}/recommendations/generate`, {
    method: 'POST',
    body: message ? { message } : {},
  })

export async function getCachedRecommendations() {
  const data = await getCacheRecommendations()
  return {
    recommendations: Array.isArray(data?.recommendations) ? data.recommendations : [],
    source: data?.source ?? 'cache',
  }
}