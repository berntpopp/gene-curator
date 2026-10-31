/**
 * What a methodology import would change in one existing schema (#282): the dry run names the
 * action per row, this names the difference. Compares the file's schema with the stored row
 * over the blocks the import writes (crud/schema_repository.py SNAPSHOT_KEYS).
 */
import { fieldIds, readLayout } from './fieldModel'

type Rec = Record<string, unknown>

const BLOCKS: Array<[string, string]> = [
  ['field_definitions', 'Fields'],
  ['ui_configuration', 'Layout'],
  ['validation_rules', 'Validation rules'],
  ['scoring_configuration', 'Scoring'],
  ['workflow_states', 'Workflow']
]

const isRecord = (v: unknown): v is Rec => !!v && typeof v === 'object' && !Array.isArray(v)

/** JSON with sorted keys: jsonb does not keep key order */
const canonical = (v: unknown): string =>
  JSON.stringify(v ?? null, (_, x: unknown) =>
    isRecord(x)
      ? Object.fromEntries(
          Object.keys(x)
            .sort()
            .map(k => [k, x[k]])
        )
      : x
  )

/** The import gives a table column without `order` its place in the file (monkey B10) */
function stampColumnOrder(node: unknown): unknown {
  if (Array.isArray(node)) return node.map(stampColumnOrder)
  if (!isRecord(node)) return node
  const out = Object.fromEntries(Object.entries(node).map(([k, v]) => [k, stampColumnOrder(v)]))
  if (isRecord(out.columns)) {
    Object.values(out.columns).forEach((c, i) => {
      if (isRecord(c) && !('order' in c)) c.order = i + 1
    })
  }
  return out
}

const fieldMap = (defs: unknown) => {
  const layout = readLayout(isRecord(defs) ? defs : {})
  const fields = layout.sections.flatMap(s => s.fields)
  return new Map(fieldIds(layout).map((id, i) => [id, canonical({ ...fields[i], order: 0 })]))
}

const list = (label: string, ids: string[]) => (ids.length ? [`${label}: ${ids.join(', ')}`] : [])

/** One line per changed block; fields are named (added, removed, changed). Empty: identical. */
export function schemaChanges(current: Rec, incoming: Rec): string[] {
  const next = stampColumnOrder(incoming) as Rec
  return BLOCKS.flatMap(([key, label]) => {
    if (canonical(current[key]) === canonical(next[key])) return []
    if (key !== 'field_definitions') return [`${label} changed`]
    const before = fieldMap(current[key])
    const after = fieldMap(next[key])
    const lines = [
      ...list(
        'Fields added',
        [...after.keys()].filter(id => !before.has(id))
      ),
      ...list(
        'Fields removed',
        [...before.keys()].filter(id => !after.has(id))
      ),
      ...list(
        'Fields changed',
        [...after.keys()].filter(id => before.has(id) && before.get(id) !== after.get(id))
      )
    ]
    return lines.length ? lines : ['Fields reordered']
  })
}
