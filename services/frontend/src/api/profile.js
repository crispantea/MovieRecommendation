export async function getMyProfile() {
  const user_id = localStorage.getItem('user_id')

  const res = await fetch(`/api/profiles/profiles/me?user_id=${user_id}`)

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.error || 'Failed to load profile')
  }

  return res.json()
}

export async function updateMyProfile(user_id, updates) {
  const res = await fetch(`/api/profiles/profiles/me?user_id=${user_id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updates),
  })

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.error || 'Failed to update profile')
  }

  return res.json()
}