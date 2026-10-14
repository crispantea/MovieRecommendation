import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import keycloak from './lib/keycloak'
import App from './App'
import './index.css'

const root = createRoot(document.getElementById('root'))

root.render(<div className="auth-status-screen">Signing you in...</div>)

// Log in FIRST, render the app AFTER.
// If the session expires and the token can't be renewed, send the user back to sign in.
keycloak.onAuthRefreshError = () => keycloak.login()

keycloak
  .init({ onLoad: 'login-required', checkLoginIframe: false })
  .then(() => {
    root.render(
      <StrictMode>
        <App />
      </StrictMode>,
    )
  })
  .catch((err) => {
    console.error('Keycloak init failed:', err)
    root.render(
      <div className="auth-status-screen">
        Could not sign you in. Check the browser console.
      </div>,
    )
  })