export function verifiedSeekLimit(duration, serverVerifiedEnd, localWatchedEnd) {
  const safeDuration = Math.max(0, Number(duration || 0))
  const verifiedEnd = Math.max(0, Number(serverVerifiedEnd || 0))
  const watchedEnd = Math.max(0, Number(localWatchedEnd || 0))
  return Math.min(safeDuration, Math.max(verifiedEnd, watchedEnd))
}

export function resolveSeekRequest({
  requested,
  current,
  duration,
  serverVerifiedEnd,
  localWatchedEnd
}) {
  const limit = verifiedSeekLimit(duration, serverVerifiedEnd, localWatchedEnd)
  const requestedPosition = Math.max(0, Number(requested || 0))
  if (requestedPosition > limit + 0.25) {
    return {
      accepted: false,
      position: Math.max(0, Math.min(Number(current || 0), limit))
    }
  }
  return {
    accepted: true,
    position: Math.min(requestedPosition, limit)
  }
}
