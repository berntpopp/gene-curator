/**
 * Display helpers for curator avatars shared by the assignment modals.
 */
import type { Schema } from '@/types/api'
import type { CuratorOption } from './types'

/** Map a scope membership to a curator choice (names come from the user_* response fields). */
export function toCuratorOption(member: Schema<'ScopeMembershipResponse'>): CuratorOption {
  return {
    user_id: member.user_id,
    role: member.role,
    full_name: member.user_full_name,
    email: member.user_email,
    displayName: member.user_full_name || member.user_email || member.user_id
  }
}

const AVATAR_COLORS = ['primary', 'success', 'info', 'warning', 'error']

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
