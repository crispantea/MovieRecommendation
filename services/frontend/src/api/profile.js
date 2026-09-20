import { api } from './client'

export const getMyProfile = () => api('/api/profiles/me')

export const updateMyProfile = (updates) =>
  api('/api/profiles/me', { method: 'PATCH', body: updates })