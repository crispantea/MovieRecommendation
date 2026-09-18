import { Link } from 'react-router-dom'
import RegisterForm from '../components/RegisterForm.jsx'

export default function RegisterPage() {
  return (
    <div style={{ maxWidth: 320, margin: '80px auto', fontFamily: 'sans-serif' }}>
      <h2>Register</h2>
      <RegisterForm />

      <p>Already have an account? <Link to="/login">Back to login page</Link></p>
    </div>
  )
}