import { apiFetch } from './client'

export async function getMyProfile() {
  return apiFetch('/api/profiles/me')
}

export async function updateMyProfile(updates) {
  return apiFetch('/api/profiles/me', {
    method: 'PATCH',
    body: JSON.stringify(updates),
  })
}