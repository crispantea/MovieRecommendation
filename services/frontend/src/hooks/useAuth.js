import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { loginRequest, registerRequest } from '../api/auth.js'

export function useAuth() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
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
      localStorage.setItem('user_id', data.user_id)
      navigate('/')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function register(e) {
    e.preventDefault()

    if (!email || !password || !confirmPassword) {
      setError('Please fill in all fields')
      return
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match')
      return
    }

    setError('')
    setLoading(true)

    try {
      const data = await registerRequest(email, password)
      localStorage.setItem('token', data.token)
      localStorage.setItem('user_id', data.user_id)
      navigate('/')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  function logout() {
    localStorage.removeItem('token')
    localStorage.removeItem('user_id')
    navigate('/login')
  }

  return { email, setEmail, password, setPassword, confirmPassword, setConfirmPassword, error, loading, login, register, logout }
}