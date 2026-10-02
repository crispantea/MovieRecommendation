import Keycloak from 'keycloak-js'

const env = window.__ENV__ ?? {}

// Runtime config in production, VITE_* from .env in local dev
const url = env.KEYCLOAK_URL ?? import.meta.env.VITE_KEYCLOAK_URL
const realm = env.KEYCLOAK_APP_REALM ?? import.meta.env.VITE_KEYCLOAK_APP_REALM
const clientId = env.KEYCLOAK_APP_CLIENT_ID ?? import.meta.env.VITE_KEYCLOAK_APP_CLIENT_ID

for (const [name, value] of Object.entries({ url, realm, clientId })) {
  if (!value) throw new Error(`Missing Keycloak config: ${name}`)
}

export default new Keycloak({ url, realm, clientId })