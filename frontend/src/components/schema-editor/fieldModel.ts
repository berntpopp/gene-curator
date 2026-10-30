/**
 * The field editor's view of `field_definitions`. Two stored shapes exist: `sections[].fields[]`
 * (each field carries its `id`) and a flat `{ key: field }` map (the key is the id; `order`
 * restores the order jsonb drops). The editor always works on sections; a flat map is one
 * section and is written back flat, so existing schemas keep their shape and render unchanged.
 */

/** The five JSON blocks of a schema, all editable in the Advanced tab */
export type BlockKey =
  | 'field_definitions'
  | 'ui_configuration'
  | 'validation_rules'
  | 'scoring_configuration'
  | 'workflow_states'

export type FieldDef = Record<string, unknown> & { id: string }

export interface EditorSection {
  id: string
  label?: string
  description?: string
  fields: FieldDef[]
  [key: string]: unknown
}

export interface Layout {
  /** false: a flat map shown as one section; sections cannot be added */
  sectioned: boolean
  sections: EditorSection[]
}

/** Same list as the backend validator (`core/schema_rules.py: VALID_FIELD_TYPES`) */
export const FIELD_TYPES = [
  { value: 'text', title: 'Text' },
  { value: 'textarea', title: 'Long text' },
  { value: 'number', title: 'Number' },
  { value: 'integer', title: 'Whole number' },
  { value: 'boolean', title: 'Yes / no' },
  { value: 'date', title: 'Date' },
  { value: 'url', title: 'Link (URL)' },
  { value: 'select', title: 'Single choice' },
  { value: 'multiselect', title: 'Multiple choice' },
  { value: 'enum', title: 'Choice (enum)' },
  { value: 'external_reference', title: 'Ontology reference' },
  { value: 'evidence_table', title: 'Evidence table' },
  { value: 'array', title: 'List' },
  { value: 'object', title: 'Group (object)' },
  { value: 'string', title: 'String' }
]

/** Types whose values come from an options list */
export const CHOICE_TYPES = ['select', 'multiselect', 'enum']

const isRecord = (v: unknown): v is Record<string, unknown> =>
  !!v && typeof v === 'object' && !Array.isArray(v)

export const clone = <T>(value: T): T => JSON.parse(JSON.stringify(value)) as T

export function readLayout(definitions: Record<string, unknown> | null | undefined): Layout {
  const defs = definitions ?? {}
  if (Array.isArray(defs.sections) || !Object.keys(defs).length) {
    return { sectioned: true, sections: clone((defs.sections ?? []) as EditorSection[]) }
  }
  const fields = Object.entries(defs)
    .filter(([, def]) => isRecord(def))
    .map(([id, def]): FieldDef => ({ ...clone(def as Record<string, unknown>), id }))
    .sort((a, b) => Number(a.order ?? Infinity) - Number(b.order ?? Infinity))
  return { sectioned: false, sections: [{ id: 'fields', label: 'Fields', fields }] }
}

/** `original` keeps any keys the editor does not show (e.g. a non-field entry of a flat map) */
export function writeLayout(
  layout: Layout,
  original: Record<string, unknown> | null | undefined
): Record<string, unknown> {
  if (layout.sectioned) return { ...(original ?? {}), sections: layout.sections }
  const kept = Object.entries(original ?? {}).filter(([, def]) => !isRecord(def))
  const fields = (layout.sections[0]?.fields ?? []).map(({ id, ...def }) => [id, def])
  return Object.fromEntries([...kept, ...fields])
}

/** Every field id in the layout (show_when targets, duplicate check) */
export const fieldIds = (layout: Layout) => layout.sections.flatMap(s => s.fields.map(f => f.id))

/** Move item `index` of `list` by `step` (-1 up, +1 down); out of range is a no-op */
export function move<T>(list: T[], index: number, step: number): void {
  const to = index + step
  if (to < 0 || to >= list.length) return
  const [item] = list.splice(index, 1)
  list.splice(to, 0, item as T)
}

/** Flat maps keep their order in `order`: renumber after a move (sections keep array order) */
export function renumber(layout: Layout): void {
  if (!layout.sectioned) layout.sections[0]?.fields.forEach((f, i) => (f.order = i + 1))
}

/** "a, true, 3" -> scalars as JSON reads them, else text; one value stays scalar */
export function parseValues(text: string): unknown {
  const values = text
    .split(',')
    .map(v => v.trim())
    .filter(Boolean)
    .map(v => {
      try {
        const parsed: unknown = JSON.parse(v)
        return isRecord(parsed) || Array.isArray(parsed) ? v : parsed
      } catch {
        return v
      }
    })
  return values.length === 1 ? values[0] : values
}

export const formatValues = (value: unknown) =>
  (Array.isArray(value) ? value : [value]).map(v => String(v)).join(', ')
