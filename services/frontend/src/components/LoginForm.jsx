import InputField from './InputField.jsx'
import { useAuth } from '../hooks/useAuth.js'

export default function LoginForm() {
  const { email, setEmail, password, setPassword, error, loading, login } = useAuth()

  return (
    <form onSubmit={login}>
      <InputField
        label="Email"
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
      />
      <InputField
        label="Password"
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
      />
      {error && <p style={{ color: 'red' }}>{error}</p>}
      <button type="submit" disabled={loading} style={{ width: '100%', padding: 10 }}>
        {loading ? 'Logging in...' : 'Log In'}
      </button>
    </form>
  )
}