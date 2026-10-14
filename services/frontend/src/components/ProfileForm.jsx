import { useRef, useEffect } from 'react'
import StarRatingPicker from './StarRatingPicker.jsx'

function formatLetterboxdStars(rating) {
  const num = Math.max(0, Math.min(5, Number(rating) || 0))
  const full = Math.floor(num)
  const hasHalf = num - full >= 0.5
  return '★'.repeat(full) + (hasHalf ? '½' : '')
}

export default function ProfileForm({ profileState, onClose }) {
  const drawerRef = useRef(null)

  useEffect(() => {
    if (!onClose) return undefined

    function handleClickOutside(e) {
      if (drawerRef.current && !drawerRef.current.contains(e.target)) {
        // Prevent conflict if clicking on toggle controls that have their own click handlers
        if (
          e.target.closest('.user-panel-btn') ||
          e.target.closest('.welcome-username') ||
          e.target.closest('.empty-profile-cta-btn')
        ) {
          return
        }
        onClose()
      }
    }

    function handleKeyDown(e) {
      if (e.key === 'Escape') {
        onClose()
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    window.addEventListener('keydown', handleKeyDown)

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [onClose])

  const {
    ALLOWED_GENRES,
    loading,
    saving,
    error,
    success,
    favoriteMovie,
    setFavoriteMovie,
    favoriteGenres,
    toggleGenre,
    favoriteActors,
    setFavoriteActors,
    watchHistory,
    addWatchedMovie,
    removeWatchedMovie,
    newTitle,
    setNewTitle,
    newRating,
    setNewRating,
    saveProfile,
  } = profileState

  if (loading) {
    return (
      <div className="profile-drawer-wrapper" ref={drawerRef}>
        <div className="profile-form">
          <p style={{ color: 'var(--lb-text-body)', margin: 0, fontSize: 12 }}>
            Loading your profile...
          </p>
        </div>
      </div>
    )
  }

  async function handleSubmit(e) {
    const ok = await saveProfile(e)
    if (ok && onClose) {
      onClose()
    }
  }

  return (
    <section className="profile-drawer-wrapper" ref={drawerRef} aria-label="Profile Editor">
      <div className="profile-drawer-header">
        <h2 className="profile-drawer-title">Your Profile &amp; Taste</h2>
        {onClose && (
          <button
            type="button"
            className="drawer-close-btn"
            onClick={onClose}
          >
            Close ✕
          </button>
        )}
      </div>

      <form onSubmit={handleSubmit} className="profile-form">
        <div className="profile-form-grid">
          <div className="form-field" style={{ marginBottom: 0 }}>
            <label className="form-label">
              <span>Favorite Movie</span>
            </label>
            <input
              type="text"
              className="dark-input"
              value={favoriteMovie}
              onChange={(e) => setFavoriteMovie(e.target.value)}
              placeholder="e.g. In the Mood for Love (2000)"
            />
          </div>

          <div className="form-field" style={{ marginBottom: 0 }}>
            <label className="form-label">
              <span>Favorite Actors</span>
              <span className="form-label-hint">Comma-separated</span>
            </label>
            <input
              type="text"
              className="dark-input"
              value={favoriteActors}
              onChange={(e) => setFavoriteActors(e.target.value)}
              placeholder="e.g. Amy Adams, Denzel Washington"
            />
          </div>
        </div>

        <div className="form-field">
          <label className="form-label">
            <span>Favorite Genres</span>
            <span className="form-label-hint">
              {favoriteGenres.length} selected
            </span>
          </label>
          <div className="genre-Grid">
            {ALLOWED_GENRES.map((genre) => {
              const selected = favoriteGenres.includes(genre)
              return (
                <label
                  key={genre}
                  className={`genre-toggle-pill ${selected ? 'is-selected' : ''}`}
                >
                  <input
                    type="checkbox"
                    checked={selected}
                    onChange={() => toggleGenre(genre)}
                  />
                  <span>{selected ? '★ ' : ''}{genre}</span>
                </label>
              )
            })}
          </div>
        </div>

        <div className="form-field" style={{ marginBottom: 12 }}>
          <label className="form-label">
            <span>Watch History &amp; Ratings</span>
            <span className="form-label-hint">
              {watchHistory.length} logged
            </span>
          </label>

          {watchHistory.length > 0 && (
            <ul className="watch-history-list">
              {watchHistory.map((entry, i) => (
                <li key={i} className="watch-history-item">
                  <div>
                    <span className="watch-history-title">{entry.title}</span>
                    <span className="watch-history-rating">
                      {formatLetterboxdStars(entry.rating)}
                    </span>
                  </div>
                  <button
                    type="button"
                    className="watch-remove-btn"
                    onClick={() => removeWatchedMovie(i)}
                  >
                    Remove
                  </button>
                </li>
              ))}
            </ul>
          )}

          <div className="watch-add-row">
            <input
              type="text"
              className="dark-input"
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              placeholder="Movie title"
            />
            <StarRatingPicker
              value={newRating}
              onChange={(r) => setNewRating(r)}
            />
            <button
              type="button"
              className="btn-secondary"
              onClick={addWatchedMovie}
            >
              Add
            </button>
          </div>
        </div>

        {error && <div className="status-banner error">{error}</div>}
        {success && <div className="status-banner success">{success}</div>}

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
          <button type="submit" disabled={saving} className="btn-primary">
            {saving ? 'Saving...' : 'Save Profile'}
          </button>
        </div>
      </form>
    </section>
  )
}