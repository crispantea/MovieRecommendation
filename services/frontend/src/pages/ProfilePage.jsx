import Header from '../components/Header.jsx'
import ProfileForm from '../components/ProfileForm.jsx'
import RecommendationsSection from '../components/RecommendationsSection.jsx'
import { useAuth } from '../hooks/useAuth.js'

export default function ProfilePage() {
  const { logout } = useAuth()
  const email = localStorage.getItem('email')

  return (
    <div style={{ maxWidth: 480, margin: '40px auto', fontFamily: 'sans-serif' }}>
      <Header />

      <h1>Your Profile</h1>
      <ProfileForm />

      <h1>Recommendations</h1>
      <RecommendationsSection />
    </div>
  )
}