import Header from '../components/Header.jsx'
import ProfileForm from '../components/ProfileForm.jsx'

export default function ProfilePage() {
  return (
    <div style={{ maxWidth: 480, margin: '80px auto', fontFamily: 'sans-serif' }}>
      <Header />
      <h2>Your Profile</h2>
      <ProfileForm />
    </div>
  )
}