import keycloak from '../lib/keycloak'

// The user is always signed in when the app renders (see main.jsx).
export const useAuth = () => ({
  user: keycloak.tokenParsed, // sub, email, realm_access.roles, ...
  logout: () => keycloak.logout({ redirectUri: window.location.origin }),
})