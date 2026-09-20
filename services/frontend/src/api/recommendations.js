import { api } from './client'

export const getRecommendations = (candidates = [], message = null) =>
  api('/api/inference/recommendations/generate', { method: 'POST', body: { candidates, message } })