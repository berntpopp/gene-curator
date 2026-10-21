/**
 * Required-field check against a precuration schema; mirrors backend `missing_required_fields`
 * (crud/precuration.py). Required = `required: true` in flat/nested definitions or in
 * `sections[].fields[]`, plus `validation_rules.required_fields`. A field hidden by its
 * `visible_when` / `show_when` condition is not required; an unset checkbox counts as false.
 */
import { conditionHolds } from '@/components/dynamic/conditions'
import type { Condition } from '@/components/dynamic/types'

const humanize = (key: string) => {
  const words = key.replace(/_/g, ' ').trim()
  return words.charAt(0).toUpperCase() + words.slice(1)
}

const isEmpty = (v: unknown) =>
  v == null ||
  (typeof v === 'string' && !v.trim()) ||
  (typeof v === 'object' && Object.keys(v).length === 0)

interface Cfg {
  id?: string
  label?: string
  title?: string
  type?: string
  required?: unknown
  properties?: unknown
  fields?: unknown
  visible_when?: Condition
  show_when?: Condition
}

/** [dotted path, config] of every field (backend `_fields`). */
function allFields(defs: unknown, prefix = ''): [string, Cfg][] {
  if (!defs || typeof defs !== 'object') return []
  const found: [string, Cfg][] = []
  const record = defs as Record<string, unknown>
  const sections = Array.isArray(record.sections) ? (record.sections as Cfg[]) : []
  for (const section of sections) {
    for (const f of Array.isArray(section?.fields) ? (section.fields as Cfg[]) : []) {
      if (f?.id) found.push([prefix + f.id, f])
    }
  }
  for (const [name, raw] of Object.entries(record)) {
    if (name === 'sections' || !raw || typeof raw !== 'object') continue
    const cfg = raw as Cfg
    found.push([prefix + name, cfg])
    if (cfg.required !== true && cfg.type === 'object') {
      found.push(...allFields(cfg.properties, `${prefix}${name}.`))
    }
  }
  return found
}

const valueAt = (data: unknown, path: string) =>
  path
    .split('.')
    .reduce<unknown>(
      (v, k) => (v && typeof v === 'object' ? (v as Record<string, unknown>)[k] : undefined),
      data
    )

/** Labels of required fields that are empty in `data`. */
export function missingRequiredLabels(defs: unknown, data: unknown, rules?: unknown): string[] {
  const fields = allFields(defs)
  const configs = new Map(fields)
  const listed = (rules as { required_fields?: unknown } | null | undefined)?.required_fields
  const paths = new Set([
    ...fields.filter(([, cfg]) => cfg.required === true).map(([path]) => path),
    ...(Array.isArray(listed) ? (listed as string[]) : [])
  ])
  return [...paths]
    .filter(path => {
      const cfg = configs.get(path)
      const when = cfg?.visible_when ?? cfg?.show_when
      if (when && !conditionHolds(when, data)) return false
      return cfg?.type !== 'boolean' && isEmpty(valueAt(data, path))
    })
    .map(path => {
      const cfg = configs.get(path)
      return cfg?.label || cfg?.title || humanize(path.split('.').pop() ?? path)
    })
}
