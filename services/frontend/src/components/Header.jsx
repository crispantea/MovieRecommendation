import { useAuth } from '../hooks/useAuth.js'

export default function Header() {
  const user_id = localStorage.getItem('user_id')
  const { logout } = useAuth()

  return (
    <header style={{
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      paddingBottom: 16,
      marginBottom: 24,
      borderBottom: '1px solid #ddd',
    }}>
      <span style={{ fontWeight: 600 }}>User: {user_id}</span>
      <button onClick={logout} style={{
        padding: '6px 14px',
        background: 'transparent',
        border: '1px solid #ccc',
        borderRadius: 6,
        cursor: 'pointer',
      }}>
        Log Out
      </button>
    </header>
  )
}