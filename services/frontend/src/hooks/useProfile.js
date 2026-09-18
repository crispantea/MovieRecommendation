import { useState, useEffect } from 'react'
import { getMyProfile, updateMyProfile } from '../api/profile.js'

const ALLOWED_GENRES = [
  'sci-fi', 'thriller', 'mystery', 'drama', 'comedy', 'action',
  'horror', 'romance', 'musical', 'documentary', 'animation',
  'fantasy', 'crime', 'adventure', 'war', 'biography',
]

export function useProfile() {
  const userId = localStorage.getItem('user_id')

  const [profile, setProfile] = useState(null)
  const [favoriteGenres, setFavoriteGenres] = useState([])
  const [favoriteActors, setFavoriteActors] = useState('')
  const [mood, setMood] = useState('')
  const [watchHistory, setWatchHistory] = useState([])
  const [newTitle, setNewTitle] = useState('')
  const [newRating, setNewRating] = useState(5)

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  useEffect(() => {
    getMyProfile(userId)
      .then((data) => {
        setProfile(data)
        setFavoriteGenres(data.favorite_genres || [])
        setFavoriteActors((data.favorite_actors || []).join(', '))
        setMood(data.mood || '')
        setWatchHistory(data.watch_history || [])
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [userId])

  function toggleGenre(genre) {
    setFavoriteGenres((prev) =>
      prev.includes(genre) ? prev.filter((g) => g !== genre) : [...prev, genre]
    )
  }

  function addWatchedMovie() {
    if (!newTitle.trim()) return
    setWatchHistory((prev) => [...prev, { title: newTitle.trim(), rating: Number(newRating) }])
    setNewTitle('')
    setNewRating(5)
  }

  function removeWatchedMovie(index) {
    setWatchHistory((prev) => prev.filter((_, i) => i !== index))
  }

  async function saveProfile(e) {
    e.preventDefault()
    setError('')
    setSuccess('')
    setSaving(true)

    try {
      const updated = await updateMyProfile(userId, {
        favorite_genres: favoriteGenres,
        favorite_actors: favoriteActors
          .split(',')
          .map((a) => a.trim())
          .filter(Boolean),
        mood,
        watch_history: watchHistory,
      })
      setProfile(updated)
      setSuccess('Profile saved')
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return {
    ALLOWED_GENRES,
    profile, loading, saving, error, success,
    favoriteGenres, toggleGenre,
    favoriteActors, setFavoriteActors,
    mood, setMood,
    watchHistory, addWatchedMovie, removeWatchedMovie,
    newTitle, setNewTitle,
    newRating, setNewRating,
    saveProfile,
  }
}