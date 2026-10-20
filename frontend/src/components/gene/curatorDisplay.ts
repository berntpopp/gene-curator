/**
 * Display helpers for curator avatars shared by the assignment modals.
 */

const AVATAR_COLORS = ['primary', 'secondary', 'success', 'info', 'warning', 'error']

/** Avatar colour derived from a stable hash of the email. */
export function getAvatarColor(email: string | null | undefined): string {
  const hash = (email || '').split('').reduce((acc, char) => acc + char.charCodeAt(0), 0)
  return AVATAR_COLORS[hash % AVATAR_COLORS.length] ?? 'primary'
}

/** Two-letter initials from a full name, or '?' when there is no name. */
export function getInitials(name: string | null | undefined): string {
  if (!name) return '?'
  const parts = name.trim().split(' ')
  const first = parts[0] ?? ''
  const last = parts[parts.length - 1] ?? ''
  if (parts.length === 1) return first.charAt(0).toUpperCase()
  return (first.charAt(0) + last.charAt(0)).toUpperCase()
}
