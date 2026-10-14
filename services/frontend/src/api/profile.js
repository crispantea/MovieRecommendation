import { api } from './client'

const env = window.__ENV__ ?? {}

// Runtime config in production, VITE_* from .env in local dev
const profiles_service_url = (
  env.PROFILES_SERVICE_URL ??
  import.meta.env.VITE_PROFILES_SERVICE_URL ??
  '/profiles'
).replace(/\/+$/, '')

export const getMyProfile = () => api(`${profiles_service_url}/me`)

export const updateMyProfile = (updates) =>
  api(`${profiles_service_url}/me`, { method: 'PATCH', body: updates })

export async function searchUsers(query = '', excludeUserId = '') {
  const q = String(query || '').trim()
  const exclude = String(excludeUserId || '').trim()

  const params = new URLSearchParams()
  if (q) params.set('q', q)
  if (exclude) params.set('exclude', exclude)
  const queryString = params.toString()

  const url = queryString
    ? `${profiles_service_url}/?${queryString}`
    : `${profiles_service_url}/`

  try {
    const data = await api(url)
    const list = Array.isArray(data?.users) ? data.users : Array.isArray(data) ? data : []
    return exclude
      ? list.filter((u) => u.user_id !== exclude && u.id !== exclude)
      : list
  } catch {
    return []
  }
}

export async function getUserProfile(userId) {
  if (!userId) throw new Error('User ID is required')
  const data = await api(`${profiles_service_url}/${encodeURIComponent(userId)}`)
  if (!data || (!data.user_id && !data.id)) {
    throw new Error('User profile not found')
  }
  return data
}