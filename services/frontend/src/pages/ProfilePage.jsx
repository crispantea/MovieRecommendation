import Header from '../components/Header.jsx'
import ProfileForm from '../components/ProfileForm.jsx'
import RecommendationsSection from '../components/RecommendationsSection.jsx'
import { useAuth } from '../hooks/useAuth.js'
import { useProfile } from '../hooks/useProfile.js'

export default function ProfilePage() {
  const { user } = useAuth()
  const profileState = useProfile()

  return (
    <div style={{ maxWidth: 480, margin: '40px auto', fontFamily: 'sans-serif' }}>
      <Header />

      <h1>Your Profile</h1>
      <ProfileForm profileState={profileState} />

      <h1>Recommendations</h1>
      <RecommendationsSection favoriteGenres={profileState.favoriteGenres} />
    </div>
  )
}