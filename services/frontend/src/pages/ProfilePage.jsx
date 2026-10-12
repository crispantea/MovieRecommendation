import { useEffect } from 'react'
import Header from '../components/Header.jsx'
import ProfileForm from '../components/ProfileForm.jsx'
import RecommendationsSection from '../components/RecommendationsSection.jsx'
import { useAuth } from '../hooks/useAuth.js'
import { useProfile } from '../hooks/useProfile.js'
import { useCacheRecommendations } from '../hooks/useCache.js'

export default function ProfilePage() {
  const { user } = useAuth()
  const profileState = useProfile()
  const { fetchCacheRecommendations, cacheRecommendations, error } = useCacheRecommendations()

  useEffect(() => { fetchCacheRecommendations() }, [])

  return (
    <div style={{ maxWidth: 480, margin: '40px auto', fontFamily: 'sans-serif' }}>
      <Header />

      <h1>Welcome! We have some suggestions for you:</h1>
      {error && <p style={{ color: 'red' }}>{error}</p>}
      <ul>
        {cacheRecommendations.map((rec) => (
          <li key={rec.id}>{rec.title}</li>
        ))}
      </ul>

      <h1>Your Profile</h1>
      <ProfileForm profileState={profileState} />

      <h1>Recommendations</h1>
      <RecommendationsSection favoriteGenres={profileState.favoriteGenres} />
    </div>
  )
}