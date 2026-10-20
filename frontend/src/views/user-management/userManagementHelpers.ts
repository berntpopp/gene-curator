// Pure helpers shared by the user-management views (no component state)

export interface UserRecord {
  id: string
  name: string
  email: string
  role: string
  is_active: boolean
  created_at?: string | null
  last_login?: string | null
}

const roleColors: Record<string, string> = { admin: 'error', curator: 'warning', viewer: 'info' }
const roleIcons: Record<string, string> = {
  admin: 'mdi-shield-crown',
  curator: 'mdi-pencil',
  viewer: 'mdi-eye'
}

export function getRoleColor(role: string | null | undefined): string {
  return (role && roleColors[role]) || 'primary'
}

export function getRoleIcon(role: string | null | undefined): string {
  return (role && roleIcons[role]) || 'mdi-account'
}

export function formatDate(date: string | null | undefined): string {
  if (!date) return 'N/A'
  return new Date(date).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}
