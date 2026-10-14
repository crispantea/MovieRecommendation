import keycloak from '../lib/keycloak'

// Call the API with the user's token. Resolves with the JSON response;
// throws an Error with the server's message when the request fails.
export async function api(url, { body, ...options } = {}) {
  try {
    if (keycloak && keycloak.authenticated && typeof keycloak.updateToken === 'function') {
      await keycloak.updateToken(30).catch(() => {})
    }
  } catch {
    // Continue with existing credentials or public access
  }
  const headers = { 'Content-Type': 'application/json', ...options.headers }
  if (keycloak?.token) {
    headers.Authorization = `Bearer ${keycloak.token}`
  }
  const res = await fetch(url, {
    ...options,
    headers,
    body: body && JSON.stringify(body),
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`)
  return data
}