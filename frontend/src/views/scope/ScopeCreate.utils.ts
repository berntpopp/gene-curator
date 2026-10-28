// Pure helpers for ScopeCreate.vue

export const displayNameRules = [
  (v: string) => !!v || 'Display name is required',
  (v: string) => (v && v.length >= 4) || 'Minimum 4 characters required',
  (v: string) => (v && v.length <= 100) || 'Maximum 100 characters allowed'
]

/** "Kidney Genetics" -> "kidney-genetics": ASCII-folded words joined by single dashes, max 64, starts with a letter */
// Letters NFKD cannot decompose; without this they would be dropped ("Ünicøde" -> "unic-de")
const FOLD: Record<string, string> = {
  ø: 'o',
  æ: 'ae',
  œ: 'oe',
  ß: 'ss',
  ł: 'l',
  đ: 'd',
  ð: 'd',
  þ: 'th'
}

export const slugify = (text: string): string => {
  const slug = text
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[øæœßłđðþ]/g, c => FOLD[c] ?? c)
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
  const lettered = /^\d/.test(slug) ? `s-${slug}` : slug
  return lettered.slice(0, 64).replace(/-+$/, '')
}
