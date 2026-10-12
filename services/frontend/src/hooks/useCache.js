import { useState } from 'react'
import { getCacheRecommendations } from '../api/cache.js'

export function useCacheRecommendations() {
  const [cacheRecommendations, setCacheRecommendations] = useState([])
  const [error, setError] = useState('')

  async function fetchCacheRecommendations() {
    setError('')
    setCacheRecommendations([])

    try {
      const data = await getCacheRecommendations()
      setCacheRecommendations(data.recommendations)
    } catch (err) {
      setError(err.message)
    }
  }

  return { cacheRecommendations, error, fetchCacheRecommendations }
}