import LoginForm from '../components/LoginForm.jsx'

export default function LoginPage() {
  return (
    <div style={{ maxWidth: 320, margin: '80px auto', fontFamily: 'sans-serif' }}>
      <h2>Login</h2>
      <LoginForm />
    </div>
  )
}