import { useEffect, useState } from 'react'
import { useAuth } from '../hooks/useAuth.js'
import { getMyProfile } from '../api/profile.js'

export default function MainPage() {
  const { logout } = useAuth()
  const user = localStorage.getItem('user_id')

  const [profile, setProfile] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getMyProfile()
      .then(setProfile)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div style={{ maxWidth: 320, margin: '80px auto', fontFamily: 'sans-serif' }}>
      <h2>Welcome!</h2>
      <p>You are logged in as <b>{user}</b>.</p>

      {loading && <p>Loading profile...</p>}
      {error && <p style={{ color: 'red' }}>{error}</p>}

      {profile && (
        <div style={{ marginTop: 20 }}>
          <p><b>Favorite genres:</b> {profile.favorite_genres?.join(', ') || 'none yet'}</p>
          <p><b>Favorite actors:</b> {profile.favorite_actors?.join(', ') || 'none yet'}</p>
          <p><b>Mood:</b> {profile.mood || 'not set'}</p>
          <p><b>Watch history:</b> {profile.watch_history?.length || 0} movies logged</p>
        </div>
      )}

      <button onClick={logout} style={{ padding: 10, marginTop: 20 }}>Log Out</button>
    </div>
  )
}