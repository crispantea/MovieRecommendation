export default function ProfileForm({ profileState }) {
  const {
    ALLOWED_GENRES,
    loading, saving, error, success,
    favoriteGenres, toggleGenre,
    favoriteActors, setFavoriteActors,
    mood, setMood,
    watchHistory, addWatchedMovie, removeWatchedMovie,
    newTitle, setNewTitle,
    newRating, setNewRating,
    saveProfile,
  } = profileState

  if (loading) return <p>Loading profile...</p>

  return (
    <form onSubmit={saveProfile} style={{ marginBottom: 50 }}>
      <h3>Favorite genres</h3>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 16 }}>
        {ALLOWED_GENRES.map((genre) => (
          <label key={genre} style={{ fontSize: 14 }}>
            <input
              type="checkbox"
              checked={favoriteGenres.includes(genre)}
              onChange={() => toggleGenre(genre)}
            />
            {' '}{genre}
          </label>
        ))}
      </div>

      <h3>Favorite actors</h3>
      <input
        type="text"
        value={favoriteActors}
        onChange={(e) => setFavoriteActors(e.target.value)}
        placeholder="Comma-separated, e.g. Amy Adams, Denzel Washington"
        style={{ width: '100%', padding: 8, marginBottom: 16 }}
      />

      <h3>Mood</h3>
      <input
        type="text"
        value={mood}
        onChange={(e) => setMood(e.target.value)}
        placeholder="e.g. tense and cerebral, not too long"
        style={{ width: '100%', padding: 8, marginBottom: 16 }}
      />

      <h3>Watch history</h3>
      <ul style={{ listStyle: 'none', padding: 0 }}>
        {watchHistory.map((entry, i) => (
          <li key={i} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
            <span>{entry.title} — {entry.rating}/5</span>
            <button type="button" onClick={() => removeWatchedMovie(i)}>Remove</button>
          </li>
        ))}
      </ul>

      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        <input
          type="text"
          value={newTitle}
          onChange={(e) => setNewTitle(e.target.value)}
          placeholder="Movie title"
          style={{ flex: 1, padding: 8 }}
        />
        <select value={newRating} onChange={(e) => setNewRating(e.target.value)}>
          {[0, 1, 2, 3, 4, 5].map((r) => (
            <option key={r} value={r}>{r}</option>
          ))}
        </select>
        <button type="button" onClick={addWatchedMovie}>Add</button>
      </div>

      {error && <p style={{ color: 'red' }}>{error}</p>}
      {success && <p style={{ color: 'green' }}>{success}</p>}

      <button type="submit" disabled={saving} style={{ width: '100%', padding: 10 }}>
        {saving ? 'Saving...' : 'Save Profile'}
      </button>
    </form>
  )
}