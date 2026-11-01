// Pure helpers shared by the user-management views (no component state)

export interface UserRecord {
  id: string
  name: string
  email: string
  role: string
  is_active: boolean
  is_agent?: boolean // #639: an AI agent account
  created_at?: string | null
  last_login?: string | null
}

const roleColors: Record<string, string> = { admin: 'primary', user: 'info' }
const roleIcons: Record<string, string> = {
  admin: 'mdi-shield-crown',
  user: 'mdi-account'
}

export function getRoleColor(role: string | null | undefined): string {
  return (role && roleColors[role]) || 'primary'
}

export function getRoleIcon(role: string | null | undefined): string {
  return (role && roleIcons[role]) || 'mdi-account'
}

export function initials(name: string | null | undefined): string {
  return (name ?? '')
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map(w => w[0]!.toUpperCase())
    .join('')
}
