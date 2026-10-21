/** True if the value holds anything entered; blank rows added to a list do not count (matches the backend engine). */
export function hasContent(value: unknown): boolean {
  if (typeof value === 'string') return value.trim().length > 0
  if (Array.isArray(value)) return value.some(hasContent)
  if (value && typeof value === 'object') return Object.values(value).some(hasContent)
  return value !== null && value !== undefined && value !== false
}
