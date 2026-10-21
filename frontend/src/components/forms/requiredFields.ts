/** Required-field check against a schema's `field_definitions`; mirrors the backend submit rule. */

const humanize = (key: string) => {
  const words = key.replace(/_/g, ' ').trim()
  return words.charAt(0).toUpperCase() + words.slice(1)
}

const isEmpty = (v: unknown) =>
  v == null ||
  (typeof v === 'string' && !v.trim()) ||
  (typeof v === 'object' && Object.keys(v).length === 0)

/** Labels (schema `label`/`title`, else humanized key) of required fields that are empty. */
export function missingRequiredLabels(defs: unknown, data: unknown): string[] {
  if (!defs || typeof defs !== 'object') return []
  const values = (data && typeof data === 'object' ? data : {}) as Record<string, unknown>
  const missing: string[] = []
  for (const [name, raw] of Object.entries(defs)) {
    if (!raw || typeof raw !== 'object') continue
    const cfg = raw as { label?: string; title?: string; type?: string; required?: unknown }
    if (cfg.required === true && isEmpty(values[name])) {
      missing.push(cfg.label || cfg.title || humanize(name))
    } else if (cfg.type === 'object') {
      missing.push(
        ...missingRequiredLabels((raw as { properties?: unknown }).properties, values[name])
      )
    }
  }
  return missing
}
