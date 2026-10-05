import { api } from './client'

const env = window.__ENV__ ?? {}

// Runtime config in production, VITE_* from .env in local dev
const profiles_service_url = env.PROFILES_SERVICE_URL ?? import.meta.env.VITE_PROFILES_SERVICE_URL

export const getMyProfile = () => api(`${profiles_service_url}/me`)

export const updateMyProfile = (updates) =>
  api(`${profiles_service_url}/me`, { method: 'PATCH', body: updates })