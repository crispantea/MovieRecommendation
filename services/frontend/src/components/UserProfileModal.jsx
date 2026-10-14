import { useEffect, useState } from 'react'
import { getUserProfile } from '../api/profile.js'

export default function UserProfileModal({ selectedUser, onClose }) {
  const [fetchedProfile, setFetchedProfile] = useState(null)

  useEffect(() => {
    if (!selectedUser?.user_id) return undefined

    let active = true

    getUserProfile(selectedUser.user_id)
      .then((fullProfile) => {
        if (active && fullProfile) {
          setFetchedProfile(fullProfile)
        }
      })
      .catch(() => {
        // Keep selectedUser fallback if getUserProfile fails
      })

    return () => {
      active = false
    }
  }, [selectedUser])

  useEffect(() => {
    if (!selectedUser) return undefined

    function handleKeyDown(e) {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [selectedUser, onClose])

  if (!selectedUser) return null

  const profileData =
    fetchedProfile && fetchedProfile.user_id === selectedUser.user_id
      ? fetchedProfile
      : selectedUser
  const loading =
    Boolean(selectedUser.user_id) &&
    (!fetchedProfile || fetchedProfile.user_id !== selectedUser.user_id)

  const displayName =
    profileData.name ||
    profileData.email ||
    (profileData.user_id ? `Member (${profileData.user_id.slice(0, 8)})` : 'Member')
  const showEmail = profileData.email && profileData.name && profileData.name !== profileData.email
  const genres = profileData.favorite_genres || []
  const actors = profileData.favorite_actors || []
  const watchHistory = profileData.watch_history || []

  return (
    <div
      className="modal-backdrop"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label={`${displayName}'s profile`}
    >
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-user-identity">
            <img src="/default-avatar.png" alt="" className="modal-avatar" />
            <div>
              <h2 className="modal-user-name">{displayName}</h2>
              {showEmail && (
                <p className="modal-user-email">{profileData.email}</p>
              )}
            </div>
          </div>

          <button
            type="button"
            className="drawer-close-btn"
            onClick={onClose}
            aria-label="Close modal"
          >
            Close ✕
          </button>
        </div>

        <div className="modal-body">
          {loading && (
            <p style={{ margin: 0, fontSize: 12, color: 'var(--lb-text-muted)' }}>
              Refreshing member profile...
            </p>
          )}

          {/* Highlighted Favorite Movie Banner (only if set) */}
          {profileData.favorite_movie?.trim() && (
            <div className="favorite-movie-banner">
              <div>
                <div className="favorite-movie-label">Favorite Film</div>
                <div className="favorite-movie-title">
                  {profileData.favorite_movie.trim()}
                </div>
              </div>
            </div>
          )}

          {/* Favorite Genres & Favorite Actors */}
          <div className="profile-form-grid" style={{ marginBottom: 0 }}>
            <div>
              <div className="form-label">Favorite Genres</div>
              {genres.length > 0 ? (
                <div className="movie-genres">
                  {genres.map((g) => (
                    <span key={g} className="genre-pill is-favorite">
                      {g}
                    </span>
                  ))}
                </div>
              ) : (
                <span style={{ fontSize: 12, color: 'var(--lb-text-muted)' }}>
                  No favorite genres listed
                </span>
              )}
            </div>

            <div>
              <div className="form-label">Favorite Actors</div>
              {actors.length > 0 ? (
                <div className="movie-genres">
                  {actors.map((actor) => (
                    <span key={actor} className="genre-pill">
                      {actor}
                    </span>
                  ))}
                </div>
              ) : (
                <span style={{ fontSize: 12, color: 'var(--lb-text-muted)' }}>
                  No favorite actors listed
                </span>
              )}
            </div>
          </div>

          {/* Watch History Diary with Star Ratings */}
          <div>
            <div className="form-label">
              <span>Recent Activity</span>
              <span className="form-label-hint">
                {watchHistory.length} films
              </span>
            </div>

            {watchHistory.length > 0 ? (
              <ul className="watch-history-list" style={{ marginBottom: 0 }}>
                {watchHistory.map((item, idx) => (
                  <li key={idx} className="watch-history-item">
                    <span className="watch-history-title">{item.title}</span>
                    <span className="watch-history-rating">
                      {'★'.repeat(Math.floor(Number(item.rating) || 0))}
                      {(Number(item.rating) || 0) % 1 >= 0.5 ? '½' : ''}{' '}
                      ({item.rating}/5)
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p style={{ margin: 0, fontSize: 12, color: 'var(--lb-text-muted)' }}>
                No logged films yet.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
