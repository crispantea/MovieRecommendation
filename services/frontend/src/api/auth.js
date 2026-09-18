export async function loginRequest(email, password) {
  const res = await fetch(`/api/profiles/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })

  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(data.message || 'Login failed')
  }

  return res.json() // e.g. { token: '...' }
}

export async function registerRequest(email, password) {
  const res = await fetch(`/api/profiles/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.error || 'Registration failed')
  }

  return res.json()
}