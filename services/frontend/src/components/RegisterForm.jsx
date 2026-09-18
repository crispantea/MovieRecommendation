import InputField from './InputField.jsx'
import { useAuth } from '../hooks/useAuth.js'

export default function RegisterForm() {
  const {
    email, setEmail,
    password, setPassword,
    confirmPassword, setConfirmPassword,
    error, loading, register
  } = useAuth()

  return (
    <form onSubmit={register}>
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
      <InputField
        label="Confirm Password"
        type="password"
        value={confirmPassword}
        onChange={(e) => setConfirmPassword(e.target.value)}
      />
      {error && <p style={{ color: 'red' }}>{error}</p>}
      <button type="submit" disabled={loading} style={{ width: '100%', padding: 10 }}>
        {loading ? 'Registering...' : 'Register'}
      </button>
    </form>
  )
}