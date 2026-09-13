import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { loginRequest } from '../api/auth.js'

export function useAuth() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  async function login(e) {
    e.preventDefault()

    if (!email || !password) {
      setError('Please fill in both fields')
      return
    }

    setError('')
    setLoading(true)

    try {
      const data = await loginRequest(email, password)
      localStorage.setItem('token', data.token)
      localStorage.setItem('email', email)
      navigate('/')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  function logout() {
    localStorage.removeItem('token')
    localStorage.removeItem('email')
    navigate('/login')
  }

  return { email, setEmail, password, setPassword, error, loading, login, logout }
}