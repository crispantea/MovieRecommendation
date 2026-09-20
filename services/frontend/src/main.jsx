import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import keycloak from './lib/keycloak'
import App from './App'

const root = createRoot(document.getElementById('root'))

root.render(<p>Signing you in...</p>)

// Log in FIRST, render the app AFTER.
// If the session expires and the token can't be renewed, send the user back to sign in.
keycloak.onAuthRefreshError = () => keycloak.login()

keycloak
  .init({ onLoad: 'login-required', pkceMethod: 'S256' })
  .then(() => {
    root.render(
      <StrictMode>
        <App />
      </StrictMode>,
    )
  })
  .catch((err) => {
    console.error('Keycloak init failed:', err)
    root.render(<p>Could not sign you in. Check the browser console.</p>)
  })