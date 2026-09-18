const API_URL = import.meta.env.VITE_API_URL

export async function getMyProfile() {
  const user_id = localStorage.getItem('user_id')

  const res = await fetch(`${API_URL}/profiles/me?user_id=${user_id}`)

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.error || 'Failed to load profile')
  }

  return res.json()
}