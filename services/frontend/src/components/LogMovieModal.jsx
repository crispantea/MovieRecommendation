import { useState, useEffect } from 'react'
import StarRatingPicker from './StarRatingPicker.jsx'

export default function LogMovieModal({ isOpen, onClose, onLogMovie }) {
  const [title, setTitle] = useState('')
  const [rating, setRating] = useState(5)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!isOpen) return undefined

    function handleKeyDown(e) {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, onClose])

  if (!isOpen) return null

  async function handleSubmit(e) {
    e.preventDefault()
    if (!title.trim() || submitting) return

    setError('')
    setSubmitting(true)
    try {
      await onLogMovie(title.trim(), rating)
      setTitle('')
      setRating(5)
      onClose()
    } catch (err) {
      setError(err.message || 'Failed to log movie')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div
      className="modal-backdrop"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Log a movie"
    >
      <div
        className="modal-card log-movie-modal"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-header">
          <h2 className="modal-user-name">I Watched...</h2>
          <button
            type="button"
            className="drawer-close-btn"
            onClick={onClose}
            aria-label="Close modal"
          >
            Close ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} className="modal-body">
          <div className="form-field" style={{ marginBottom: 0 }}>
            <label className="form-label">
              <span>Film Title</span>
            </label>
            <input
              type="text"
              className="dark-input"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Good Will Hunting"
              autoFocus
            />
          </div>

          <div className="form-field" style={{ marginBottom: 0 }}>
            <label className="form-label">
              <span>Rating</span>
              <span className="form-label-hint">
                {rating > 0 ? `${rating} / 5 stars` : 'Unrated'}
              </span>
            </label>
            <div style={{ display: 'flex', alignItems: 'center', paddingTop: 2 }}>
              <StarRatingPicker
                value={rating}
                onChange={(r) => setRating(r)}
                size={22}
              />
            </div>
          </div>

          {error && <div className="status-banner error">{error}</div>}

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
            <button
              type="submit"
              disabled={!title.trim() || submitting}
              className="btn-primary"
            >
              {submitting ? 'Saving...' : 'Save'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
