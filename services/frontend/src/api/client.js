import keycloak from '../lib/keycloak'

// Call the API with the user's token. Resolves with the JSON response;
// throws an Error with the server's message when the request fails.
export async function api(url, { body, ...options } = {}) {
  await keycloak.updateToken(30) // renews the token if it expires within 30s
  const res = await fetch(url, {
    ...options,
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${keycloak.token}` },
    body: body && JSON.stringify(body),
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`)
  return data
}