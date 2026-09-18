export async function getRecommendations(user_id) {
  const res = await fetch(`/api/inference/recommendations/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id }),
  })

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.error || 'Failed to generate recommendations')
  }

  return res.json()
}