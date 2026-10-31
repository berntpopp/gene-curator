// Shape of `scoring_configuration` as backend/app/scoring/point_model.py interprets it.
// It is schema content (JSONB), not an API response type, so it is described here.
// Every node keeps unknown keys: the builder edits in place and the code view round-trips.

type Extra = { [key: string]: unknown }

/** One test of a row column: a value list, filled in / blank, or numeric bounds. */
export interface RowCondition extends Extra {
  field: string
  in?: unknown[]
  present?: boolean
  gt?: number
  gte?: number
  lt?: number
  lte?: number
}

/** Row rule (#576): a matching 0-point rule always wins; a non-zero rule only fills rows
 * whose points are blank. `and` lists further conditions that must all hold too. A rule
 * has one effect: `points`, or (#615) `factor` / `max`, which scale or cap the result. */
export interface PointsWhen extends RowCondition {
  and?: RowCondition[]
  points?: number
  factor?: number
  max?: number
}

export const EFFECTS = [
  { value: 'points', title: 'Points' },
  { value: 'factor', title: 'Times' },
  { value: 'max', title: 'At most' }
] as const
export type Effect = (typeof EFFECTS)[number]['value']

/** The rule's effect key; `points` when it has none yet. */
export const effectOf = (rule: PointsWhen): Effect =>
  EFFECTS.find(e => e.value in rule)?.value ?? 'points'

/** Switch a rule's effect, keeping its number. */
export function setEffect(rule: PointsWhen, effect: Effect) {
  const value = rule[effectOf(rule)] ?? 0
  for (const e of EFFECTS) delete rule[e.value]
  rule[effect] = value
}

/** group_by chips: one stays a field name, several a list (#615), none removes it. */
export function setGroupBy(item: ItemType, chips: unknown) {
  const fields = (Array.isArray(chips) ? chips : [chips]).map(String).filter(f => f.trim())
  if (fields.length > 1) item.group_by = fields
  else if (fields.length === 1) item.group_by = fields[0]
  else delete item.group_by
}

/** Step rule (#576): `field` summed over the rows; the highest `min` reached scores once. */
export interface Step extends Extra {
  min: number
  points: number
}

export interface ItemType extends Extra {
  path: string
  rule?: string
  default?: number
  range?: [number | null, number | null] // null: a bound being typed (the validator flags it)
  points_key?: string
  group_by?: string | string[]
  group_values?: Record<string, string>
  group_cap?: number
  require_variant?: boolean
  points_when?: PointsWhen[]
  field?: string
  steps?: Step[]
}

export interface Category extends Extra {
  key: string
  cap?: number
  combine?: 'sum' | 'max'
  types: ItemType[]
}

export interface Section extends Extra {
  key: string
  cap?: number
  categories: Category[]
}

export interface Band extends Extra {
  class: string
  min?: number
  requires?: string
  description?: string
  section_min?: Record<string, number>
}

export interface Override extends Extra {
  when: string
  field?: string
  in?: unknown[]
  class: string
}

export interface ReviewFlags extends Extra {
  band_margin?: number
  hotspot?: { max_variants: number; min_share: number }
  experimental_over_genetic?: string[]
}

export interface PointModel extends Extra {
  total_cap?: number
  sections: Section[]
  bands: Band[]
  overrides?: Override[]
  review_flags?: ReviewFlags
}

export interface Classification extends Extra {
  key: string
  label: string
  order: number
  tone: string
}

export interface ScoringTest extends Extra {
  name?: string
  evidence_data: Record<string, unknown>
  expect: { total?: number; class?: string }
}

export interface ScoringConfig extends Extra {
  engine?: string
  point_model?: PointModel
  classifications?: Classification[]
  tests?: ScoringTest[]
}

/** Inline diagnostics for one JSON path, e.g. `scoring_configuration.point_model.total_cap`. */
export type DiagFn = (path: string) => string[]

// Tones the backend accepts (backend/app/scoring/classifications.py TONES)
export const TONES = [
  'definitive',
  'strong',
  'moderate',
  'limited',
  'no_known',
  'disputed',
  'refuted'
]

export const MODEL_PATH = 'scoring_configuration.point_model'

/** Set an optional number from a text field; blank removes the key. */
export function setNumber<T extends object>(node: T, key: keyof T & string, value: unknown) {
  const target = node as Extra
  if (value === '' || value === null || value === undefined) delete target[key]
  else target[key] = Number(value)
}

/** Set an optional text; blank removes the key. */
export function setText<T extends object>(node: T, key: keyof T & string, value: unknown) {
  const target = node as Extra
  if (value === '' || value === null || value === undefined) delete target[key]
  else target[key] = String(value)
}

/** JSON copy: the builder never shares objects with its v-model. */
export const clone = <T>(value: T): T => JSON.parse(JSON.stringify(value ?? {})) as T

/**
 * Combobox chips are text; give each the value it had before (2 stays a number), and
 * read 'true'/'false' typed anew as booleans (a checkbox column holds them).
 */
export function keepTypes(previous: unknown[] | undefined, chips: unknown[]): unknown[] {
  const known = new Map((previous ?? []).map(v => [String(v), v]))
  return chips.map(chip =>
    known.has(String(chip))
      ? known.get(String(chip))
      : chip === 'true'
        ? true
        : chip === 'false'
          ? false
          : chip
  )
}
