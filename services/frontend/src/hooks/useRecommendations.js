import { useState, useEffect, useCallback } from 'react'
import { getRecommendations, getCachedRecommendations } from '../api/recommendations.js'

export function useRecommendations({ isProfileFilled = false, profileVersion = 0 } = {}) {
  // Pre-cached recommendations from the background agent (top section)
  const [cachedRecommendations, setCachedRecommendations] = useState([])
  const [cachedLoading, setCachedLoading] = useState(true)
  const [cachedError, setCachedError] = useState('')

  // On-demand AI recommendations from manual prompt queries (bottom section)
  const [generatedRecommendations, setGeneratedRecommendations] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const loadCachedRecommendations = useCallback(async () => {
    setCachedError('')
    setCachedLoading(true)

    try {
      const data = await getCachedRecommendations()
      const recs = data.recommendations || []
      setCachedRecommendations(recs)
      return recs
    } catch (err) {
      setCachedError(err.message)
      return []
    } finally {
      setCachedLoading(false)
    }
  }, [])

  // Initial load on mount
  useEffect(() => {
    let active = true

    getCachedRecommendations()
      .then((data) => {
        if (!active) return
        setCachedRecommendations(data.recommendations || [])
      })
      .catch((err) => {
        if (!active) return
        setCachedError(err.message)
      })
      .finally(() => {
        if (active) setCachedLoading(false)
      })

    return () => {
      active = false
    }
  }, [])

  // When profileVersion changes (> 0), reset cached picks during render so we immediately show loading
  const [prevProfileVersion, setPrevProfileVersion] = useState(profileVersion)
  if (profileVersion !== prevProfileVersion) {
    setPrevProfileVersion(profileVersion)
    if (profileVersion > 0) {
      setCachedRecommendations([])
      setCachedLoading(true)
    }
  }

  // Auto-polling effect: when profile is filled and cached recommendations are empty,
  // poll every 3 seconds until the cache agent delivers recommendations
  useEffect(() => {
    if (!isProfileFilled || cachedRecommendations.length > 0) {
      return undefined
    }

    let active = true

    // Check immediately
    getCachedRecommendations()
      .then((data) => {
        if (!active) return
        if (Array.isArray(data.recommendations) && data.recommendations.length > 0) {
          setCachedRecommendations(data.recommendations)
          setCachedLoading(false)
        }
      })
      .catch(() => {})

    const interval = setInterval(async () => {
      if (!active) return
      try {
        const data = await getCachedRecommendations()
        if (!active) return
        if (Array.isArray(data.recommendations) && data.recommendations.length > 0) {
          setCachedRecommendations(data.recommendations)
          setCachedLoading(false)
        }
      } catch {
        // Continue retrying
      }
    }, 3000)

    return () => {
      active = false
      clearInterval(interval)
    }
  }, [isProfileFilled, cachedRecommendations.length, profileVersion])

  async function fetchRecommendations(message = null) {
    setError('')
    setLoading(true)

    try {
      const trimmed = message ? message.trim() : null
      const data = await getRecommendations(trimmed)
      setGeneratedRecommendations(data.recommendations || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return {
    cachedRecommendations,
    cachedLoading,
    cachedError,
    generatedRecommendations,
    recommendations: generatedRecommendations,
    loading,
    error,
    fetchRecommendations,
    loadCachedRecommendations,
  }
}