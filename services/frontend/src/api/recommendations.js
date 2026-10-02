import { api } from './client'

export const getRecommendations = (message = null) =>
  api('/api/inference/recommendations/generate', {
    method: 'POST',
    body: message ? { message } : {},
  })