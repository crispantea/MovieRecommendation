import { api } from './client'

const env = window.__ENV__ ?? {}

// Runtime config in production, VITE_* from .env in local dev
const cache_agent_url = env.CACHE_AGENT_URL ?? import.meta.env.VITE_CACHE_AGENT_URL

export const getCacheRecommendations = () =>
  api(`${cache_agent_url}/profiles/me/recommendations`, { method: 'GET' })