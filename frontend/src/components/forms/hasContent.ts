/** True if a contradictory row has Impact "disputed"; only those make the class Disputed (#266). */
export function hasDisputingRow(value: unknown): boolean {
  return Array.isArray(value) && value.some(row => row?.impact === 'disputed')
}

// Defaults a new contradictory row is created with; mirrors the backend
const ROW_DEFAULTS: Record<string, unknown> = { evidence_type: 'population', impact: 'note' }

// Case-level row fields preset on a new row; not entered evidence
const PRESET_KEYS = new Set(['variant_type', 'score_status'])

/** True if the value holds anything entered; blank rows added to a list do not count (matches the backend engine). */
export function hasContent(value: unknown): boolean {
  if (typeof value === 'string') return value.trim().length > 0
  if (Array.isArray(value)) return value.some(hasContent)
  if (value && typeof value === 'object') {
    return Object.entries(value).some(
      ([k, v]) => !PRESET_KEYS.has(k) && ROW_DEFAULTS[k] !== v && hasContent(v)
    )
  }
  return value !== null && value !== undefined && value !== false
}
