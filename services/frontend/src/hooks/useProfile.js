import { useState, useEffect } from 'react'
import { getMyProfile, updateMyProfile } from '../api/profile.js'
import keycloak from '../lib/keycloak'

const ALLOWED_GENRES = [
  'sci-fi', 'thriller', 'mystery', 'drama', 'comedy', 'action',
  'horror', 'romance', 'music', 'documentary', 'animation',
  'fantasy', 'crime', 'adventure', 'war', 'history', 'family', 'western',
]

export function useProfile() {
  const [profile, setProfile] = useState(null)
  const [favoriteMovie, setFavoriteMovie] = useState('')
  const [favoriteGenres, setFavoriteGenres] = useState([])
  const [favoriteActors, setFavoriteActors] = useState('')
  const [watchHistory, setWatchHistory] = useState([])
  const [newTitle, setNewTitle] = useState('')
  const [newRating, setNewRating] = useState(0)

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [profileVersion, setProfileVersion] = useState(0)

  useEffect(() => {
    getMyProfile()
      .then((data) => {
        setProfile(data)
        setFavoriteMovie(data.favorite_movie || '')
        setFavoriteGenres((data.favorite_genres || []).filter((g) => ALLOWED_GENRES.includes(g)))
        setFavoriteActors((data.favorite_actors || []).join(', '))
        setWatchHistory(data.watch_history || [])
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  function toggleGenre(genre) {
    setFavoriteGenres((prev) =>
      prev.includes(genre) ? prev.filter((g) => g !== genre) : [...prev, genre]
    )
  }

  function addWatchedMovie() {
    if (!newTitle.trim()) return
    setWatchHistory((prev) => [...prev, { title: newTitle.trim(), rating: Number(newRating) }])
    setNewTitle('')
    setNewRating(0)
  }

  function removeWatchedMovie(index) {
    setWatchHistory((prev) => prev.filter((_, i) => i !== index))
  }

  async function logMovie(title, rating) {
    const trimmed = String(title || '').trim()
    if (!trimmed) return
    const nextHistory = [
      ...watchHistory,
      { title: trimmed, rating: Number(rating) },
    ]
    setWatchHistory(nextHistory)

    const actorList = favoriteActors
      .split(',')
      .map((a) => a.trim())
      .filter(Boolean)

    const tokenUser = keycloak?.tokenParsed || {}
    const tokenName =
      tokenUser.name ||
      [tokenUser.given_name, tokenUser.family_name].filter(Boolean).join(' ') ||
      tokenUser.preferred_username ||
      ''
    const tokenEmail = tokenUser.email || ''

    const payload = {
      favorite_movie: favoriteMovie.trim(),
      favorite_genres: favoriteGenres,
      favorite_actors: actorList,
      watch_history: nextHistory,
    }
    if (tokenName) payload.name = tokenName
    if (tokenEmail) payload.email = tokenEmail

    const updated = await updateMyProfile(payload)
    setProfile(updated)
    setFavoriteMovie(updated.favorite_movie || '')
    setFavoriteActors((updated.favorite_actors || []).join(', '))
    setProfileVersion((v) => v + 1)
  }

  async function saveProfile(e) {
    if (e && e.preventDefault) e.preventDefault()
    setError('')
    setSuccess('')
    setSaving(true)

    try {
      const actorList = favoriteActors
        .split(',')
        .map((a) => a.trim())
        .filter(Boolean)

      const tokenUser = keycloak?.tokenParsed || {}
      const tokenName =
        tokenUser.name ||
        [tokenUser.given_name, tokenUser.family_name].filter(Boolean).join(' ') ||
        tokenUser.preferred_username ||
        ''
      const tokenEmail = tokenUser.email || ''

      const payload = {
        favorite_movie: favoriteMovie.trim(),
        favorite_genres: favoriteGenres,
        favorite_actors: actorList,
        watch_history: watchHistory,
      }
      if (tokenName) payload.name = tokenName
      if (tokenEmail) payload.email = tokenEmail

      const updated = await updateMyProfile(payload)
      setProfile(updated)
      setFavoriteMovie(updated.favorite_movie || '')
      setFavoriteActors((updated.favorite_actors || []).join(', '))
      setSuccess('Profile saved')
      setProfileVersion((v) => v + 1)
      return true
    } catch (err) {
      setError(err.message)
      return false
    } finally {
      setSaving(false)
    }
  }

  return {
    ALLOWED_GENRES,
    profile, loading, saving, error, success,
    profileVersion,
    favoriteMovie, setFavoriteMovie,
    favoriteGenres, toggleGenre,
    favoriteActors, setFavoriteActors,
    watchHistory, addWatchedMovie, removeWatchedMovie, logMovie,
    newTitle, setNewTitle,
    newRating, setNewRating,
    saveProfile,
  }
}