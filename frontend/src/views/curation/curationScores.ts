/** Presentation model for the backend's untyped JSON score trace. No scoring rules live here. */
export interface TraceType {
  path: string
  items: number | null
  score: number | null
}
export interface TraceCategory {
  key: string
  raw: number | null
  cap: number | null
  score: number | null
  types: TraceType[]
}
export interface TraceSection extends Omit<TraceCategory, 'types'> {
  categories: TraceCategory[]
}
export interface ScoreTrace {
  raw_total: number | null
  total_cap: number | null
  total: number | null
  class: string
  sections: TraceSection[]
  classification_rule: Record<string, unknown> | null
}
export interface EvidenceScores {
  total: number | null
  trace: ScoreTrace | null
}
export const record = (v: unknown): Record<string, unknown> | null =>
  v !== null && typeof v === 'object' && !Array.isArray(v) ? (v as Record<string, unknown>) : null
const number = (v: unknown): number | null =>
  typeof v === 'number' && Number.isFinite(v) ? v : null
const objects = (v: unknown): Record<string, unknown>[] =>
  Array.isArray(v) ? v.flatMap(x => (record(x) ? [record(x)!] : [])) : []
const values = (v: Record<string, unknown>) => ({
  key: String(v.key ?? ''),
  raw: number(v.raw),
  cap: number(v.cap),
  score: number(v.score)
})

export function storedScores(value: unknown): EvidenceScores {
  const scores = record(value)
  const t = record(scores?.trace)
  const trace: ScoreTrace | null =
    t && Array.isArray(t.sections)
      ? {
          raw_total: number(t.raw_total),
          total_cap: number(t.total_cap),
          total: number(t.total),
          class: typeof t.class === 'string' ? t.class : '',
          classification_rule: record(t.classification_rule),
          sections: objects(t.sections).map(s => ({
            ...values(s),
            categories: objects(s.categories).map(c => ({
              ...values(c),
              types: objects(c.types).map(t => ({
                path: String(t.path ?? ''),
                items: number(t.items),
                score: number(t.score)
              }))
            }))
          }))
        }
      : null
  return { total: number(scores?.total_score), trace }
}
export const formatScore = (value: number | null | undefined): string =>
  value == null ? 'Unavailable' : value.toFixed(2)
export const traceLabel = (key: string): string =>
  key
    .replaceAll('_', ' ')
    .replaceAll('.', ' › ')
    .replace(/^./, c => c.toUpperCase())
