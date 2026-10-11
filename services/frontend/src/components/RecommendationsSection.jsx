import { useState } from 'react'
import { useRecommendations } from '../hooks/useRecommendations.js'

export default function RecommendationsSection({ favoriteGenres = [] }) {
  const { recommendations, loading, error, fetchRecommendations } = useRecommendations()
  const [message, setMessage] = useState('')

  return (
    <div>
      {/* <input
        type="text"
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        placeholder="Optional: anything specific tonight? (e.g. something short and funny)"
        style={{ width: '100%', padding: 8, marginBottom: 12 }}
      /> */}

      <button
        onClick={() => fetchRecommendations()}
        disabled={loading}
        style={{ width: '100%', padding: 10, marginBottom: 16 }}
      >
        {loading ? 'Thinking...' : 'Get Recommendations'}
      </button>

      {error && (
        <p style={{ color: 'red' }}>
          {error || "Something went wrong. Please try again in a moment."}
        </p>
      )}

      {!loading && !error && recommendations.length === 0 && (
        <p style={{ color: '#888' }}>No recommendations yet — click the button above.</p>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {recommendations.map((rec, i) => (
          <div
            key={i}
            style={{
              border: '1px solid #ddd',
              borderRadius: 8,
              padding: 12,
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <strong>{rec.title} ({rec.year})</strong>
              <span style={{ color: '#888', fontSize: 13 }}>
                {Math.round(rec.confidence * 100)}% match
              </span>
            </div>
            <p style={{ margin: '4px 0', fontSize: 13, color: '#666' }}>
              {rec.genres.map((genre, idx) => (
                <span key={idx}>
                  {idx > 0 && ', '}
                  {favoriteGenres.includes(genre) ? <strong>{genre}</strong> : genre}
                </span>
              ))}
            </p>
            <p style={{ margin: 0 }}>{rec.reason}</p>
          </div>
        ))}
      </div>
    </div>
  )
}