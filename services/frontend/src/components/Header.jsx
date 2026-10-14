import { useState, useEffect, useRef } from 'react'
import { useAuth } from '../hooks/useAuth.js'
import { searchUsers } from '../api/profile.js'

export default function Header({
  isProfileOpen = false,
  onToggleProfile,
  favoriteMovie = '',
  onSelectUser,
  onOpenLogMovie,
}) {
  const { user, logout } = useAuth()
  const displayName =
    user?.name ||
    [user?.given_name, user?.family_name].filter(Boolean).join(' ') ||
    user?.preferred_username?.split('@')[0] ||
    user?.email?.split('@')[0] ||
    user?.sub ||
    'User'

  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [isSearchOpen, setIsSearchOpen] = useState(false)
  const [searching, setSearching] = useState(false)
  const searchContainerRef = useRef(null)

  const currentUserId = user?.sub || ''
  const currentEmail = user?.email || ''

  useEffect(() => {
    let active = true

    if (!isSearchOpen && !query.trim()) {
      return undefined
    }

    const timer = setTimeout(() => {
      setSearching(true)
      searchUsers(query, currentUserId)
        .then((users) => {
          if (active) {
            const others = (users || []).filter((u) => {
              if (currentUserId && (u.user_id === currentUserId || u.id === currentUserId)) {
                return false
              }
              if (currentEmail && u.email && u.email.toLowerCase() === currentEmail.toLowerCase()) {
                return false
              }
              return true
            })
            setResults(others)
          }
        })
        .finally(() => {
          if (active) setSearching(false)
        })
    }, 120)

    return () => {
      active = false
      clearTimeout(timer)
    }
  }, [query, isSearchOpen, currentUserId, currentEmail])

  useEffect(() => {
    function handleClickOutside(e) {
      if (
        searchContainerRef.current &&
        !searchContainerRef.current.contains(e.target)
      ) {
        setIsSearchOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  function handleSelectResult(selectedUser) {
    setIsSearchOpen(false)
    if (onSelectUser) {
      onSelectUser(selectedUser)
    }
  }

  return (
    <header className="site-header">
      <div className="site-header-inner">
        {/* Top-Left: User Panel Button + Log Out Button right next to it */}
        <div className="header-left">
          <button
            type="button"
            className={`user-panel-btn ${isProfileOpen ? 'is-active' : ''}`}
            onClick={onToggleProfile}
            aria-expanded={isProfileOpen}
            title="Toggle your profile & taste editor"
          >
            <img src="/default-avatar.png" alt="" className="user-avatar" />
            <span className="user-panel-name">{displayName}</span>
            {favoriteMovie && !isProfileOpen && (
              <span className="user-panel-sub">· {favoriteMovie}</span>
            )}
            <svg
              className="user-panel-chevron"
              width="12"
              height="12"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </button>

          <button type="button" onClick={logout} className="logout-btn">
            Log Out
          </button>
        </div>

        {/* Top-Center: User Discovery Search Bar */}
        <div className="header-center" ref={searchContainerRef}>
          <div className="search-input-wrapper">
            <svg
              className="search-icon"
              width="15"
              height="15"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
            <input
              type="text"
              className="search-input"
              value={query}
              onFocus={() => setIsSearchOpen(true)}
              onChange={(e) => {
                setQuery(e.target.value)
                setIsSearchOpen(true)
              }}
              placeholder="Search users by name or email..."
              aria-label="Search users by name or email"
            />
            {query && (
              <button
                type="button"
                className="search-clear-btn"
                onClick={() => {
                  setQuery('')
                  setIsSearchOpen(false)
                }}
                aria-label="Clear search"
              >
                ✕
              </button>
            )}
          </div>

          {isSearchOpen && (
            <div className="search-dropdown" role="listbox">
              <div className="search-dropdown-header">
                {query.trim()
                  ? `Matching members (${results.length})`
                  : 'Discover community members'}
              </div>

              {searching && results.length === 0 ? (
                <div className="search-empty">Searching members...</div>
              ) : results.length === 0 ? (
                <div className="search-empty">
                  No members found matching &ldquo;{query}&rdquo;
                </div>
              ) : (
                results.map((member) => {
                  const memberName =
                    member.name ||
                    member.email ||
                    (member.user_id ? `Member (${member.user_id.slice(0, 8)})` : 'Member')
                  const showEmail =
                    member.email && member.name && member.name !== member.email

                  return (
                    <button
                      key={member.user_id || member.email}
                      type="button"
                      className="search-result-item"
                      onClick={() => handleSelectResult(member)}
                    >
                      <div className="search-result-user">
                        <img src="/default-avatar.png" alt="" className="user-avatar" />
                        <div className="search-result-info">
                          <div className="search-result-name">{memberName}</div>
                          {showEmail && (
                            <div className="search-result-email">{member.email}</div>
                          )}
                        </div>
                      </div>
                      {member.favorite_movie?.trim() && (
                        <span className="search-result-fav">
                          Favorite: {member.favorite_movie.trim()}
                        </span>
                      )}
                    </button>
                  )
                })
              )}
            </div>
          )}
        </div>

        {/* Top-Right: Log Movie Button (Letterboxd + LOG style) */}
        <div className="header-right">
          <button
            type="button"
            onClick={onOpenLogMovie}
            className="btn-primary log-movie-btn"
          >
            <svg
              className="log-movie-plus-icon"
              width="10"
              height="10"
              viewBox="0 0 16 16"
              fill="currentColor"
              aria-hidden="true"
            >
              <path d="M8 1.5a1 1 0 0 1 1 1V7h4.5a1 1 0 0 1 0 2H9v4.5a1 1 0 0 1-2 0V9H2.5a1 1 0 0 1 0-2H7V2.5a1 1 0 0 1 1-1z" />
            </svg>
            <span>Log Movie</span>
          </button>
        </div>
      </div>
    </header>
  )
}