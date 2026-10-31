/**
 * Synopsis per curated entity: the text field a schema names in
 * `ui_configuration.synopsis_field` (dotted path), as `backend/app/core/synopsis.py` reads it.
 */
export function synopsisOf(evidence: unknown, ui: unknown): string | null {
  const path = (ui as { synopsis_field?: unknown } | null)?.synopsis_field
  if (typeof path !== 'string') return null
  let value: unknown = evidence
  for (const part of path.split('.'))
    value = value && typeof value === 'object' ? (value as Record<string, unknown>)[part] : null
  return typeof value === 'string' && value.trim() ? value.trim() : null
}
