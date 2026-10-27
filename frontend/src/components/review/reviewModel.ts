/** Pure helpers for the review diff: grouping by evidence item, per-item state, approve rules. */
import type { Schema } from '@/types/api'
import { humanize } from '@/components/dynamic/fieldLabels'

type DiffItem = Schema<'DiffItem'>
type Comment = Schema<'ReviewComment'>

/** A curation schema field definition, as far as the diff needs it (labels, enum options). */
export interface FieldDef {
  title?: string
  label?: string
  properties?: Record<string, FieldDef>
  item_schema?: Record<string, FieldDef>
  items?: FieldDef
  options?: (string | { value: unknown; label?: string })[]
}

/** Where readable names come from: the schema's `field_definitions` and the current evidence. */
export interface DiffContext {
  /** Untyped JSON from the API; read as `FieldDef`s. */
  fields?: Record<string, unknown> | null
  evidence?: unknown
}

export interface DiffField {
  /** Field below the item ('' for a scalar item, whose label is the item's). */
  name: string
  label: string
  options?: FieldDef['options']
  change: DiffItem['change']
  before: unknown
  after: unknown
}

export interface DiffGroup {
  key: string
  label: string
  /** The sections the item sits in, e.g. `Genetic evidence › Case level`. */
  context: string
  change: DiffItem['change']
  fields: DiffField[]
}

/** An item is a list record (`a.b[id]`) with all its fields, or a scalar path on its own. */
export function itemKey(path: string): string {
  const end = path.lastIndexOf(']')
  return end === -1 ? path : path.slice(0, end + 1)
}

/** One-line item name for text (to-dos, feedback): `Name · record (enclosing section)`. */
export function itemLabel(key: string, ctx: DiffContext = {}): string {
  const { label, context } = name(key, ctx)
  const section = context.split(' › ').pop()
  return section ? `${label} (${section})` : label
}

// ponytail: fixed list of abbreviations in SOP v11 keys; schema titles override them
const TOKENS: Record<string, string> = {
  pmid: 'PMID',
  hpo: 'HPO',
  mondo: 'MONDO',
  omim: 'OMIM',
  hgnc: 'HGNC',
  hgvs: 'HGVS',
  lod: 'LOD',
  id: 'ID',
  'x linked': 'X-linked'
}
const TOKEN = new RegExp(`\\b(${Object.keys(TOKENS).join('|')})\\b`, 'gi')
const readable = (key: string) => humanize(key).replace(TOKEN, t => TOKENS[t.toLowerCase()]!)

const isRecord = (v: unknown): v is Record<string, unknown> =>
  typeof v === 'object' && v !== null && !Array.isArray(v)

const segments = (path: string) => path.replace(/\[[^\]]*\]/g, '').split('.')

/** Schema definition of a path; list records step into `item_schema` (or `items`). */
function fieldAt(fields: DiffContext['fields'], path: string): FieldDef | undefined {
  let props = (fields ?? undefined) as Record<string, FieldDef> | undefined
  let node: FieldDef | undefined
  for (const s of segments(path)) {
    node = props?.[s]
    props = node?.properties ?? node?.item_schema ?? node?.items?.properties
  }
  return node
}

const fieldLabel = (fields: DiffContext['fields'], path: string) => {
  const node = fieldAt(fields, path)
  return node?.title || node?.label || readable(segments(path).pop() ?? path)
}

/** The value at a diff path (`a.b[0].c`, `[id]` matching a record's id) in the evidence. */
function valueAt(root: unknown, path: string): unknown {
  let v = root
  for (const [, key, index] of path.matchAll(/([^.[\]]+)|\[([^\]]*)\]/g)) {
    if (key !== undefined) v = isRecord(v) ? v[key] : undefined
    else if (Array.isArray(v))
      v =
        v.find(r => isRecord(r) && String(r.id) === index) ??
        (/^\d+$/.test(index!) ? v[+index!] : undefined)
    else v = undefined
  }
  return v
}

/**
 * Filled leaves of a nested value as `path -> scalar`; empty containers and blanks are dropped.
 * Records are keyed `[id]` when every one has an id (as the backend diff does), else by position.
 */
function leaves(v: unknown, path: string): [string, unknown][] {
  if (Array.isArray(v)) {
    if (v.every(x => typeof x !== 'object' || x === null)) {
      return v.length ? [[path, v.join(', ')]] : []
    }
    const byId = v.every(x => isRecord(x) && 'id' in x)
    return v.flatMap((x, i) => leaves(x, `${path}[${byId ? String(x.id) : i}]`))
  }
  if (isRecord(v)) {
    const idKeyed = path.endsWith(`[${String(v.id)}]`) // the id is in the key already
    return Object.entries(v)
      .filter(([k]) => !(idKeyed && k === 'id'))
      .flatMap(([k, x]) => leaves(x, path ? `${path}.${k}` : k))
  }
  return v === null || v === undefined || v === '' ? [] : [[path, v]]
}

/** Added or removed values become one row per filled leaf, so a new section splits into its records. */
function rows(it: DiffItem): [string, unknown, unknown][] {
  if (it.change === 'changed') return [[it.path, it.before, it.after]]
  const added = it.change === 'added'
  const filled = leaves(added ? it.after : it.before, it.path)
  // An empty record removed still shows; an empty value added has nothing to review (#406)
  if (!filled.length && added) return []
  return (filled.length ? filled : [[it.path, 'none']]).map(([p, v]) =>
    added ? [p, undefined, v] : [p, v, undefined]
  )
}

// The record's own name: its `label` / `*_label` field (every SOP v11 list item has one).
const isNameField = (name: string) => name === 'label' || name.endsWith('_label')

function name(key: string, ctx: DiffContext, rows: DiffField[] = []) {
  const list = key.replace(/\[[^\]]*\]$/, '')
  const sections = segments(list).map((_, i, all) =>
    fieldLabel(ctx.fields, all.slice(0, i + 1).join('.'))
  )
  const label = sections.pop() ?? key
  if (list === key) return { label, context: sections.join(' › ') }
  const row = rows.find(f => isNameField(f.name))
  const record = valueAt(ctx.evidence, key)
  const own =
    row?.after ??
    row?.before ??
    (isRecord(record) ? Object.entries(record).find(([k]) => isNameField(k))?.[1] : null)
  const index = key.match(/\[(\d+)\]$/)?.[1]
  const suffix = own ? ` · ${String(own)}` : index !== undefined ? ` #${+index + 1}` : ''
  return { label: label + suffix, context: sections.join(' › ') }
}

export function groupDiff(items: DiffItem[], ctx: DiffContext = {}): DiffGroup[] {
  const groups = new Map<string, DiffGroup>()
  for (const it of items) {
    for (const [path, before, after] of rows(it)) {
      const key = itemKey(path)
      let g = groups.get(key)
      if (!g) groups.set(key, (g = { key, label: '', context: '', change: it.change, fields: [] }))
      const field = path.slice(key.length).replace(/^\./, '')
      const def = field ? fieldAt(ctx.fields, path) : undefined
      g.fields.push({
        name: field,
        label: field ? fieldLabel(ctx.fields, path) : '',
        ...(def?.options ? { options: def.options } : {}),
        change: it.change,
        before,
        after
      })
      if (g.change !== it.change) g.change = 'changed'
    }
  }
  return [...groups.values()].map(g => Object.assign(g, name(g.key, ctx, g.fields)))
}

export { formatValue } from '@/utils/evidenceValue'

export type ItemStatus = 'unreviewed' | 'accepted' | 'queried' | 'answered'

export function itemState(comments: Comment[], path: string, me: string) {
  const here = comments.filter(c => c.item_path === path)
  const accepted =
    here.find(c => c.kind === 'accepted' && c.status === 'open' && c.author_id === me) ?? null
  const queries = here.filter(c => c.kind === 'query')
  const status: ItemStatus = queries.some(q => q.status === 'open')
    ? 'queried'
    : accepted
      ? 'accepted'
      : queries.length
        ? 'answered'
        : 'unreviewed'
  return { status, queries, accepted }
}

/** Items that still block approval: neither accepted by me nor with all queries resolved. */
export function approveBlockers(groups: DiffGroup[], comments: Comment[], me: string): DiffGroup[] {
  return groups.filter(g => {
    const s = itemState(comments, g.key, me).status
    return s !== 'accepted' && s !== 'answered'
  })
}

/** One limit for a query and for the request-changes feedback (the API enforces the same). */
export const REVIEW_TEXT_MAX = 2000

/**
 * Open reviewer queries as a to-do list for "Request changes" (the curator's own replies are not
 * to-dos). Always within REVIEW_TEXT_MAX so the prefilled feedback can be sent as is.
 */
export function queryTodos(creatorId: string, comments: Comment[], ctx?: DiffContext): string {
  const lines = comments
    .filter(c => c.kind === 'query' && c.status === 'open' && c.author_id !== creatorId)
    .map(c => `- ${itemLabel(c.item_path, ctx)}: ${c.body}`)
  const whole = lines.join('\n')
  if (whole.length <= REVIEW_TEXT_MAX) return whole

  const kept: string[] = []
  let length = 0
  for (const line of lines) {
    const rest = lines.length - kept.length
    const tail = `\n- …and ${rest} more open ${rest === 1 ? 'query' : 'queries'}`
    if (length + line.length + 1 + tail.length > REVIEW_TEXT_MAX) {
      if (!kept.length) return `${line.slice(0, REVIEW_TEXT_MAX - 1)}…` // one query alone is too long
      return `${kept.join('\n')}${tail}`
    }
    kept.push(line)
    length += line.length + 1
  }
  return whole
}

export interface ChecklistItem {
  id: string
  label: string
}

// ponytail: fixed SOP v11 list; move into the schema's review configuration when methodologies need their own
export function checklistFor(classification: string | null | undefined): ChecklistItem[] {
  return [
    { id: 'publication', label: 'Every scored item has a publication' },
    { id: 'points', label: 'Points above default are explained' },
    { id: 'contradictory', label: 'Contradictory evidence was considered' },
    ...(classification === 'Definitive'
      ? [{ id: 'replication', label: 'Definitive: replication over time is documented' }]
      : [])
  ]
}
