import { useState, useRef } from 'react'

export default function StarRatingPicker({ value, onChange, size = 16 }) {
  const [hoverRating, setHoverRating] = useState(null)
  const [isDragging, setIsDragging] = useState(false)
  const dragMovedRef = useRef(false)
  const downValueRef = useRef(0)
  const trackRef = useRef(null)

  const currentVal = Number(value) || 0
  const activeValue = hoverRating !== null ? hoverRating : currentVal

  function getStarFromClientX(clientX) {
    if (!trackRef.current) return null
    const rect = trackRef.current.getBoundingClientRect()
    const relX = clientX - rect.left
    if (relX <= 2) return 0
    const ratio = Math.max(0, Math.min(1, relX / rect.width))
    const halfSteps = Math.max(1, Math.min(10, Math.ceil(ratio * 10)))
    return halfSteps / 2
  }

  function handlePointerDown(e) {
    e.preventDefault()
    setIsDragging(true)
    dragMovedRef.current = false
    downValueRef.current = currentVal
    if (e.currentTarget.setPointerCapture) {
      e.currentTarget.setPointerCapture(e.pointerId)
    }
    const next = getStarFromClientX(e.clientX)
    if (next !== null) {
      setHoverRating(next)
      onChange(next)
    }
  }

  function handlePointerMove(e) {
    const next = getStarFromClientX(e.clientX)
    if (next !== null) {
      if (isDragging && next !== downValueRef.current) {
        dragMovedRef.current = true
      }
      setHoverRating(next)
      if (isDragging) {
        onChange(next)
      }
    }
  }

  function handlePointerUp(e) {
    if (isDragging) {
      const next = getStarFromClientX(e.clientX)
      if (next !== null) {
        if (!dragMovedRef.current && next === downValueRef.current) {
          onChange(0)
          setHoverRating(0)
        } else {
          onChange(next)
        }
      }
      setIsDragging(false)
    }
  }

  function handlePointerLeave() {
    if (!isDragging) {
      setHoverRating(null)
    }
  }

  return (
    <div className="lb-star-picker-wrap" title={`${activeValue} / 5 stars`}>
      <div
        ref={trackRef}
        className="lb-star-picker"
        role="slider"
        aria-label="Rating out of 5 stars"
        aria-valuemin={0}
        aria-valuemax={5}
        aria-valuenow={currentVal}
        tabIndex={0}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={() => {
          setIsDragging(false)
          setHoverRating(null)
        }}
        onPointerLeave={handlePointerLeave}
        onKeyDown={(e) => {
          if (e.key === 'ArrowRight' || e.key === 'ArrowUp') {
            e.preventDefault()
            onChange(Math.min(5, Math.round((currentVal + 0.5) * 2) / 2))
          } else if (e.key === 'ArrowLeft' || e.key === 'ArrowDown') {
            e.preventDefault()
            onChange(Math.max(0, Math.round((currentVal - 0.5) * 2) / 2))
          }
        }}
      >
        {[1, 2, 3, 4, 5].map((star) => {
          const isFull = activeValue >= star
          const isHalf = !isFull && activeValue >= star - 0.5
          return (
            <span key={star} className="lb-star-unit">
              <svg
                width={size}
                height={size}
                viewBox="2 2 20 19.02"
                aria-hidden="true"
              >
                <path
                  d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z"
                  fill={isFull ? 'var(--lb-green)' : '#445566'}
                />
                {isHalf && (
                  <path
                    d="M12 2L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z"
                    fill="var(--lb-green)"
                  />
                )}
              </svg>
            </span>
          )
        })}
      </div>
    </div>
  )
}
