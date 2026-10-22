/**
 * Required-field check against a precuration schema; mirrors backend `missing_required_fields`
 * (crud/precuration_required.py). Required = `required: true` or a `required_when` that holds in
 * flat/nested definitions or in `sections[].fields[]`, plus `validation_rules.required_fields` and
 * `conditional_required`. A field hidden by its own or a parent's condition is not required; an
 * unset checkbox counts as false. Condition semantics: components/dynamic/conditions.ts.
 */
import {
  conditionHolds,
  isVisible,
  requiredWhenHolds,
  valueAt
} from '@/components/dynamic/conditions'

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
  visible_when?: unknown
  show_when?: unknown
  required_when?: unknown
}

const isRecord = (v: unknown): v is Record<string, unknown> =>
  !!v && typeof v === 'object' && !Array.isArray(v)

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

/** Dotted paths of required fields that are empty in `data`. */
export function missingRequiredPaths(defs: unknown, data: unknown, rules?: unknown): string[] {
  const fields = allFields(defs)
  const configs = new Map(fields)
  const { required_fields: listed, conditional_required: conditional } = isRecord(rules)
    ? rules
    : {}
  const paths = new Set([
    ...fields
      .filter(([, cfg]) => cfg.required === true || requiredWhenHolds(cfg, data))
      .map(([path]) => path),
    ...(Array.isArray(listed) ? listed.filter((p): p is string => typeof p === 'string') : []),
    ...Object.entries(isRecord(conditional) ? conditional : {})
      .filter(([, rule]) => conditionHolds(isRecord(rule) ? rule.when : rule, data))
      .map(([path]) => path)
  ])
  return [...paths].filter(path => {
    const parts = path.split('.')
    // the field and every parent it has a config for are visible
    const shown = parts.every((_, i) => {
      const cfg = configs.get(parts.slice(0, i + 1).join('.'))
      return !cfg || isVisible(cfg, data)
    })
    return shown && configs.get(path)?.type !== 'boolean' && isEmpty(valueAt(data, path))
  })
}

/** Labels of required fields that are empty in `data`. */
export function missingRequiredLabels(defs: unknown, data: unknown, rules?: unknown): string[] {
  const configs = new Map(allFields(defs))
  return missingRequiredPaths(defs, data, rules).map(path => {
    const cfg = configs.get(path)
    return cfg?.label || cfg?.title || humanize(path.split('.').pop() ?? path)
  })
}
