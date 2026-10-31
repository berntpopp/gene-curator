/**
 * Row authorship (#593): who added and who last changed an evidence row, from the
 * curation's `row_provenance` map (kept beside the evidence, keyed `path#row id`, else
 * `path[index]`), as the server stamps it (person, and the AI agent of an MCP write).
 */
import type { InjectionKey, Ref } from 'vue'
import { formatDate } from '@/utils/format'

export type Stamps = Record<string, unknown> | null | undefined
/** The curation's row_provenance, provided by the curation views */
export const ROW_PROVENANCE: InjectionKey<Ref<Stamps>> = Symbol('row-provenance')
/** Dotted data path of the enclosing object fields ('' at the top), e.g. "genetic." */
export const FIELD_PATH: InjectionKey<string> = Symbol('field-path')

interface Actor {
  name?: string | null
  agent?: { model?: string; agent?: string; tools_used?: string[] }
}
type Stamp = Record<string, unknown> | undefined

export function stampOf(
  stamps: Stamps,
  path: string,
  row: Record<string, unknown>,
  i: number
): Stamp {
  const key = row.id != null ? `${path}#${String(row.id)}` : `${path}[${i}]`
  const stamp = stamps?.[key]
  return stamp && typeof stamp === 'object' ? (stamp as Record<string, unknown>) : undefined
}

const who = (by: Actor) =>
  [by.name ?? 'unknown', by.agent && `via ${by.agent.agent ?? 'AI'} (${by.agent.model ?? '?'})`]
    .filter(Boolean)
    .join(' ')

/** "Added by …; changed by …", or '' for a row without a stamp */
export function rowAuthorship(stamp: Stamp): string {
  if (!stamp) return ''
  const part = (step: 'added' | 'changed') => {
    const by = stamp[`${step}_by`] as Actor | undefined
    const label = step === 'added' ? 'Added' : 'Changed'
    return by ? `${label} by ${who(by)}, ${formatDate(String(stamp[`${step}_at`]))}` : ''
  }
  return [part('added'), part('changed')].filter(Boolean).join('; ')
}

/** Tools an AI agent reported for this row */
export function rowTools(stamp: Stamp): string[] {
  const s = stamp as Record<string, Actor> | undefined
  return [s?.added_by, s?.changed_by].flatMap(by => by?.agent?.tools_used ?? [])
}
