import type { Schema } from '@/types/api'

export const MAX_SYMBOLS = 1000

type Item = Schema<'GeneResolveItem'>
type Candidate = Schema<'GeneCandidate'>

/** Split pasted text on newlines, commas, semicolons, tabs and spaces. */
export const parseSymbols = (text: string): string[] => text.split(/[\s,;]+/).filter(Boolean)

export const REASON_TEXT = {
  lookup_cap: 'Not looked up at HGNC: too many unknown symbols in one list',
  lookup_timeout: 'HGNC did not answer in time, try again'
} as const

/** One review row: the response item plus the user's choice. */
export interface IntakeRow {
  item: Item
  /** Chosen candidate (resolved: the single match; ambiguous: picked by the user). */
  pick: Candidate | null
  include: boolean
  /** Input of the earlier row this one repeats. */
  duplicateOf: string | null
}

export function toRows(items: Item[]): IntakeRow[] {
  return items.map(item => {
    const dup = item.duplicate_of
    const pick = item.status === 'resolved' ? (item.candidates?.[0] ?? null) : null
    return {
      item,
      pick,
      include: !!pick && dup == null,
      duplicateOf: dup == null ? null : (items.find(i => i.index === dup)?.input ?? String(dup))
    }
  })
}

export const reasonText = (item: Item): string =>
  item.reason ? REASON_TEXT[item.reason] : 'Not found at HGNC'
