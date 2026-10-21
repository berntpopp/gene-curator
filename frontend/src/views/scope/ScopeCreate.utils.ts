// Pure helpers for ScopeCreate.vue

export const getInitials = (name: string | null | undefined): string => {
  if (!name) return '?'
  const parts = name.trim().split(' ')
  const first = parts[0] ?? ''
  if (parts.length === 1) return first.charAt(0).toUpperCase()
  const last = parts[parts.length - 1] ?? ''
  return (first.charAt(0) + last.charAt(0)).toUpperCase()
}

export const displayNameRules = [
  (v: string) => !!v || 'Display name is required',
  (v: string) => (v && v.length >= 4) || 'Minimum 4 characters required',
  (v: string) => (v && v.length <= 100) || 'Maximum 100 characters allowed'
]

/** "Kidney Genetics" -> "kidney-genetics": lowercase ASCII words joined by single dashes */
export const slugify = (text: string): string =>
  text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
