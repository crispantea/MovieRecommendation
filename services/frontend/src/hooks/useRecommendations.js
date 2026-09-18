import { useState } from 'react'
import { getRecommendations } from '../api/recommendations.js'

export function useRecommendations() {
  const userId = localStorage.getItem('user_id')

  const [recommendations, setRecommendations] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function fetchRecommendations() {
    setError('')
    setLoading(true)
    setRecommendations([])

    try {
      const data = await getRecommendations(userId)
      setRecommendations(data.recommendations)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return { recommendations, loading, error, fetchRecommendations }
}