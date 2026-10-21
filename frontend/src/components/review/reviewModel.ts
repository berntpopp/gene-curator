/** Pure helpers for the review diff: grouping by evidence item, per-item state, approve rules. */
import type { Schema } from '@/types/api'

type DiffItem = Schema<'DiffItem'>
type Comment = Schema<'ReviewComment'>

export interface DiffField {
  /** Field below the item ('' when the whole item was added or removed). */
  name: string
  change: DiffItem['change']
  before: unknown
  after: unknown
}

export interface DiffGroup {
  key: string
  label: string
  change: DiffItem['change']
  fields: DiffField[]
}

/** An item is a list record (`a.b[id]`) with all its fields, or a scalar path on its own. */
export function itemKey(path: string): string {
  const end = path.lastIndexOf(']')
  return end === -1 ? path : path.slice(0, end + 1)
}

const words = (s: string) => {
  const t = s.replace(/_/g, ' ')
  return t.charAt(0).toUpperCase() + t.slice(1)
}

export function itemLabel(key: string): string {
  const m = key.match(/^(.*?)(\[[^\]]*\])?$/)
  const parts = (m?.[1] ?? key).split('.').map(words)
  return parts.join(' › ') + (m?.[2] ? ` ${m[2]}` : '')
}

export function groupDiff(items: DiffItem[]): DiffGroup[] {
  const groups = new Map<string, DiffGroup>()
  for (const it of items) {
    const key = itemKey(it.path)
    let g = groups.get(key)
    if (!g) groups.set(key, (g = { key, label: itemLabel(key), change: it.change, fields: [] }))
    g.fields.push({
      name: it.path.slice(key.length).replace(/^\./, ''),
      change: it.change,
      before: it.before,
      after: it.after
    })
    if (g.fields.some(f => f.change !== g.fields[0]!.change)) g.change = 'changed'
  }
  return [...groups.values()]
}

export function formatValue(v: unknown): string {
  if (v === null || v === undefined) return 'none'
  return typeof v === 'object' ? JSON.stringify(v) : String(v)
}

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

/** Open queries as a to-do list for "Request changes". */
export function queryTodos(comments: Comment[]): string {
  return comments
    .filter(c => c.kind === 'query' && c.status === 'open')
    .map(c => `- ${itemLabel(c.item_path)}: ${c.body}`)
    .join('\n')
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
