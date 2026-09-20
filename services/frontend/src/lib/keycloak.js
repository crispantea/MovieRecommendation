import Keycloak from 'keycloak-js'

const url = import.meta.env.VITE_KEYCLOAK_URL
const realm = import.meta.env.VITE_KEYCLOAK_APP_REALM
const clientId = import.meta.env.VITE_KEYCLOAK_APP_CLIENT_ID

export default new Keycloak({ url, realm, clientId })