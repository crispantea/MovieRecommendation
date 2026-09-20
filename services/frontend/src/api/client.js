import keycloak from '../lib/keycloak'

export async function apiFetch(url, options = {}) {
  try {
    await keycloak.updateToken(30) // refreshes the token if it expires within 30s
  } catch {
    await keycloak.login()
  }
  return fetch(url, {
    ...options,
    headers: { ...options.headers, Authorization: `Bearer ${keycloak.token}` },
  })
}