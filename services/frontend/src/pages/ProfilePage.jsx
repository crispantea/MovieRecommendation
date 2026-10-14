import { useState } from 'react'
import Header from '../components/Header.jsx'
import ProfileForm from '../components/ProfileForm.jsx'
import RecommendationsSection from '../components/RecommendationsSection.jsx'
import UserProfileModal from '../components/UserProfileModal.jsx'
import LogMovieModal from '../components/LogMovieModal.jsx'
import { useAuth } from '../hooks/useAuth.js'
import { useProfile } from '../hooks/useProfile.js'

export default function ProfilePage() {
  const { user } = useAuth()
  const profileState = useProfile()
  const [isProfileOpen, setIsProfileOpen] = useState(false)
  const [isLogMovieOpen, setIsLogMovieOpen] = useState(false)
  const [selectedSearchUser, setSelectedSearchUser] = useState(null)

  const displayName =
    user?.name ||
    [user?.given_name, user?.family_name].filter(Boolean).join(' ') ||
    user?.preferred_username?.split('@')[0] ||
    user?.email?.split('@')[0] ||
    user?.sub ||
    'User'

  // The layered loading add-on should only appear AFTER saving the profile (pressing green button / enter)
  const isProfileSaved = Boolean(
    profileState.profileVersion > 0 ||
    (profileState.profile && (
      (profileState.profile.favorite_genres && profileState.profile.favorite_genres.length > 0) ||
      (profileState.profile.favorite_movie && String(profileState.profile.favorite_movie).trim().length > 0) ||
      (profileState.profile.favorite_actors && profileState.profile.favorite_actors.length > 0) ||
      (profileState.profile.watch_history && profileState.profile.watch_history.length > 0)
    ))
  )

  return (
    <div className="app-shell">
      <Header
        isProfileOpen={isProfileOpen}
        onToggleProfile={() => setIsProfileOpen((prev) => !prev)}
        favoriteMovie={profileState.favoriteMovie}
        onSelectUser={(member) => setSelectedSearchUser(member)}
        onOpenLogMovie={() => setIsLogMovieOpen(true)}
      />

      <main className="main-container">
        {isProfileOpen && (
          <ProfileForm
            profileState={profileState}
            onClose={() => setIsProfileOpen(false)}
          />
        )}

        <p className="welcome-greeting">
          Welcome back,{' '}
          <span
            className="welcome-username"
            onClick={() => setIsProfileOpen((prev) => !prev)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                setIsProfileOpen((prev) => !prev)
              }
            }}
          >
            {displayName}
          </span>
          . Here&rsquo;s today&rsquo;s recommendations:
        </p>

        <RecommendationsSection
          favoriteGenres={profileState.favoriteGenres}
          onOpenProfile={() => {
            setIsProfileOpen(true)
            window.scrollTo({ top: 0, behavior: 'smooth' })
          }}
          isProfileSaved={isProfileSaved}
          profileVersion={profileState.profileVersion}
        />
      </main>

      <UserProfileModal
        selectedUser={selectedSearchUser}
        onClose={() => setSelectedSearchUser(null)}
      />

      <LogMovieModal
        isOpen={isLogMovieOpen}
        onClose={() => setIsLogMovieOpen(false)}
        onLogMovie={profileState.logMovie}
      />
    </div>
  )
}