import { useState } from 'react'
import { getRecommendations } from '../api/recommendations.js'

export function useRecommendations() {
  const [recommendations, setRecommendations] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function fetchRecommendations(message = null) {
    setError('')
    setLoading(true)
    setRecommendations([])

    try {
      const data = await getRecommendations(message)
      setRecommendations(data.recommendations)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return { recommendations, loading, error, fetchRecommendations }
}