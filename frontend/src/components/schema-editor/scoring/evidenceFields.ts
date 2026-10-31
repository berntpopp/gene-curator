/**
 * Picker options for the point model, read from the schema's own field definitions, so an
 * evidence path or condition field is chosen rather than typed. Mirrors how the scorer and
 * `schema_rules._check_model_paths` resolve paths: relative to the section's object field
 * when the section key names one, else from the top level (UI-built forms are flat).
 */
type Defs = Record<string, unknown>

export interface Option {
  title: string
  value: string
  subtitle?: string
}
export interface ColumnOption extends Option {
  /** Choice values of a select column, offered by "is one of". */
  options: string[]
}
export interface TableOption extends Option {
  columns: ColumnOption[]
}

const obj = (v: unknown): Defs | null =>
  v && typeof v === 'object' && !Array.isArray(v) ? (v as Defs) : null

/** Flat fields plus the seeded `sections[].fields[]` shape, by data key. */
export function topFields(defs: unknown): Defs {
  const all = obj(defs) ?? {}
  const out: Defs = {}
  for (const [k, v] of Object.entries(all)) if (k !== 'sections' || !Array.isArray(v)) out[k] = v
  for (const s of Array.isArray(all.sections) ? all.sections : []) {
    const fields = obj(s)?.fields
    for (const f of Array.isArray(fields) ? fields : []) {
      const id = obj(f)?.id
      if (typeof id === 'string' && !(id in out)) out[id] = f
    }
  }
  return out
}

/** Row columns of a table field, or null when the field holds no rows. */
function rowFields(cfg: Defs): Defs | null {
  const items = obj(cfg.items)
  return obj(cfg.columns) ?? obj(cfg.item_schema) ?? obj(items?.properties) ?? null
}

const label = (key: string, cfg: Defs | null) =>
  typeof cfg?.label === 'string' && cfg.label ? cfg.label : key

/** Label as the title, the stored key underneath when they differ. */
const option = (key: string, cfg: Defs | null, value = key): Option => {
  const title = label(key, cfg)
  return title === value ? { title, value } : { title, value, subtitle: value }
}

function choices(cfg: Defs | null): string[] {
  const raw = cfg?.options ?? cfg?.enum
  if (!Array.isArray(raw)) return []
  return raw.map(o => String(obj(o)?.value ?? o))
}

function walk(fields: Defs, prefix: string, out: TableOption[]) {
  for (const [key, raw] of Object.entries(fields)) {
    const cfg = obj(raw)
    if (!cfg) continue
    const path = `${prefix}${key}`
    const rows = rowFields(cfg)
    if (rows) {
      const columns = Object.entries(rows).map(([col, c]) => ({
        ...option(col, obj(c)),
        options: choices(obj(c))
      }))
      out.push({ ...option(key, cfg, path), columns })
    } else if (obj(cfg.properties)) {
      walk(obj(cfg.properties)!, `${path}.`, out)
    }
  }
}

/** Object fields at the top level: what a point-model section key can read. */
export function sectionOptions(defs: unknown): Option[] {
  return Object.entries(topFields(defs))
    .filter(([, cfg]) => obj(obj(cfg)?.properties))
    .map(([key, cfg]) => option(key, obj(cfg)))
}

/** Evidence tables a section's types can read, with paths as the scorer resolves them. */
export function tableOptions(defs: unknown, sectionKey: string): TableOption[] {
  const top = topFields(defs)
  const own = obj(obj(top[sectionKey])?.properties)
  const out: TableOption[] = []
  walk(own ?? top, '', out)
  return out
}
