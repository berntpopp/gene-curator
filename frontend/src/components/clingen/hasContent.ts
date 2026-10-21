// Defaults a new contradictory row is created with (ContradictoryEvidenceSection.vue); mirrors the backend
const ROW_DEFAULTS: Record<string, unknown> = { evidence_type: 'population', impact: 'note' }

/** True if the value holds anything entered; blank rows added to a list do not count (matches the backend engine). */
export function hasContent(value: unknown): boolean {
  if (typeof value === 'string') return value.trim().length > 0
  if (Array.isArray(value)) return value.some(hasContent)
  if (value && typeof value === 'object') {
    return Object.entries(value).some(([k, v]) => ROW_DEFAULTS[k] !== v && hasContent(v))
  }
  return value !== null && value !== undefined && value !== false
}
