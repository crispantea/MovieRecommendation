import { useAuth } from '../hooks/useAuth.js'

export default function MainPage() {
  const { logout } = useAuth()
  const user = localStorage.getItem('email')

  return (
    <div style={{ maxWidth: 320, margin: '80px auto', fontFamily: 'sans-serif' }}>
      <h2>Welcome!</h2>
      <p>You are logged in as <b>{user}</b>.</p>
      <button onClick={logout} style={{ padding: 10 }}>
        Log Out
      </button>
    </div>
  )
}