import { useState } from 'react'
import { useRecommendations } from '../hooks/useRecommendations.js'

function getAvgRating(rec) {
  if (typeof rec.avg_rating === 'number') return rec.avg_rating.toFixed(1)
  if (typeof rec.rating === 'number') return rec.rating.toFixed(1)
  const conf = typeof rec.confidence === 'number' ? rec.confidence : 0.85
  return Math.min(5.0, Math.max(3.0, 3.2 + conf * 1.5)).toFixed(1)
}

function LightningIcon() {
  return (
    <svg
      width="11"
      height="11"
      viewBox="0 0 16 16"
      fill="currentColor"
      aria-hidden="true"
    >
      <path d="M9.5 1L3 9h4.5L6.5 15L13 7H8.5L9.5 1z" />
    </svg>
  )
}

function MovieRow({ items, favoriteGenres = [] }) {
  return (
    <div className="recommendations-grid">
      {items.map((rec, i) => {
        const avgRating = getAvgRating(rec)

        return (
          <article key={`${rec.title}-${i}`} className="lb-card-unit">
            <div className="lb-poster-box">
              <div className={`lb-poster-art poster-tone-${i % 5}`}>
                {/* Top Row: Release Year */}
                <div className="lb-poster-top-meta">
                  <span className="lb-poster-year-top">{rec.year}</span>
                </div>

                {/* Center Focus: Movie Title */}
                <div className="lb-poster-title-block">
                  <h3 className="lb-poster-title">{rec.title}</h3>
                </div>

                {/* Synopsis / Reason */}
                <p className="lb-poster-reason">{rec.reason}</p>
              </div>

              {/* Bottom Slate Strip: Genres (matching favorite genres placed first) */}
              <div className="lb-poster-footer">
                <span className="lb-footer-genres">
                  {[...(rec.genres || [])]
                    .sort(
                      (a, b) =>
                        (favoriteGenres.includes(a) ? 0 : 1) -
                        (favoriteGenres.includes(b) ? 0 : 1),
                    )
                    .map((genre, idx) => (
                      <span key={idx}>
                        {idx > 0 && ' · '}
                        {favoriteGenres.includes(genre) ? (
                          <strong className="lb-genre-fav">{genre}</strong>
                        ) : (
                          genre
                        )}
                      </span>
                    ))}
                </span>
              </div>
            </div>

            {/* Under-Card Metadata: Avg Rating left, Release Year right */}
            <div className="lb-under-card">
              <span className="lb-avg-rating">
                <span className="lb-star-icon">★</span> {avgRating} / 5
              </span>
              <span className="lb-under-year">{rec.year}</span>
            </div>
          </article>
        )
      })}
    </div>
  )
}

function EmptyRecommendationsPlaceholder({ onOpenProfile, isProfileSaved }) {
  return (
    <div className="empty-recommendations-wrapper">
      <div className="recommendations-grid" aria-hidden="true">
        {[0, 1, 2, 3, 4].map((i) => (
          <article key={i} className="lb-card-unit lb-empty-card-unit">
            <div className="lb-empty-poster-box" />
          </article>
        ))}
      </div>

      <div className="empty-recommendations-overlay">
        {isProfileSaved ? (
          <div className="empty-profile-loading-panel" role="status" aria-live="polite">
            <div className="empty-profile-spinner" aria-hidden="true" />
            <div className="empty-profile-loading-content">
              <span className="empty-profile-loading-heading">
                Preparing your daily picks
              </span>
              <span className="empty-profile-loading-sub">
                Our background agent is finding recommendations based on your profile...
              </span>
            </div>
          </div>
        ) : (
          <button
            type="button"
            className="empty-profile-cta-btn"
            onClick={onOpenProfile}
          >
            Fill in your profile to get daily recommendations
          </button>
        )}
      </div>
    </div>
  )
}

export default function RecommendationsSection({
  favoriteGenres = [],
  onOpenProfile,
  isProfileSaved = false,
  profileVersion = 0,
}) {
  const {
    cachedRecommendations,
    cachedError,
    generatedRecommendations,
    loading,
    error,
    fetchRecommendations,
  } = useRecommendations({ isProfileFilled: isProfileSaved, profileVersion })
  const [message, setMessage] = useState('')

  function handleGenerate(e) {
    if (e) e.preventDefault()
    fetchRecommendations(message.trim() || null)
  }

  return (
    <div>
      {/* Top Section: Pre-Cached Recommendations (matches Letterboxd screenshot) */}
      <section aria-label="Cached Recommendations">
        <div className="section-header-bar">
          <h2 className="section-heading">Cached Picks For You</h2>
          <span className="section-meta-link">
            <LightningIcon /> Cached for you
          </span>
        </div>

        {cachedError && (
          <div className="status-banner error">{cachedError}</div>
        )}

        {cachedRecommendations.length === 0 ? (
          <EmptyRecommendationsPlaceholder
            onOpenProfile={onOpenProfile}
            isProfileSaved={isProfileSaved}
          />
        ) : (
          <MovieRow
            items={cachedRecommendations}
            favoriteGenres={favoriteGenres}
          />
        )}
      </section>

      {/* Bottom Section: On-Demand AI Query & Generated Results */}
      <section
        className="on-demand-section"
        aria-label="On-Demand Recommendations"
      >
        <div className="section-header-bar">
          <h2 className="section-heading">Something Specific Tonight</h2>
          <span className="section-meta-link">
            <LightningIcon /> Generated on demand
          </span>
        </div>
        <p className="prompt-hint">
          Your request comes first: we only suggest movies that fit it, and use your profile
          (favorite genres, actors and movie) to pick the best ones among them.
        </p>

        <form className="prompt-bar" onSubmit={handleGenerate}>
          <input
            type="text"
            className="prompt-input"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="What are you in the mood for tonight? Say what you want and what to avoid (e.g. an 80s horror, no slashers)..."
          />
          <button type="submit" disabled={loading} className="btn-primary">
            {loading ? 'Thinking...' : 'Get Recommendations'}
          </button>
        </form>

        {error && (
          <div className="status-banner error">
            {error || 'Something went wrong. Please try again in a moment.'}
          </div>
        )}

        {loading && (
          <p style={{ color: 'var(--lb-text-muted)', fontSize: 13, margin: 0 }}>
            Consulting AI recommendation engine...
          </p>
        )}

        {!loading && !error && generatedRecommendations.length === 0 && (
          <p style={{ color: 'var(--lb-text-muted)', fontSize: 13, margin: 0 }}>
            No on-demand recommendations generated yet — enter a prompt above and click Get Recommendations.
          </p>
        )}

        {!loading && generatedRecommendations.length > 0 && (
          <MovieRow
            items={generatedRecommendations}
            favoriteGenres={favoriteGenres}
          />
        )}
      </section>
    </div>
  )
}