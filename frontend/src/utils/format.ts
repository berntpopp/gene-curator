/** Shared date and empty-value formatting: locale-neutral ISO output, em dash when missing. */
export const EMPTY = '—'

type DateInput = string | Date | null | undefined

const DATE_ONLY = /^\d{4}-\d{2}-\d{2}$/
const p2 = (n: number) => String(n).padStart(2, '0')

/** Local-time [date, time] parts; date-only strings pass through unshifted. */
const parts = (value: DateInput): [string, string | null] | null => {
  if (!value) return null
  if (typeof value === 'string' && DATE_ONLY.test(value)) return [value, null]
  const d = value instanceof Date ? value : new Date(value)
  if (Number.isNaN(d.getTime())) return null
  return [
    `${d.getFullYear()}-${p2(d.getMonth() + 1)}-${p2(d.getDate())}`,
    `${p2(d.getHours())}:${p2(d.getMinutes())}`
  ]
}

/** "v1.0.0" for a numeric version; "alpha" and "SOP v11" stay as written (monkey B22) */
export const formatVersion = (value: string | null | undefined): string =>
  !value ? EMPTY : /^\d/.test(value) ? `v${value}` : value

/** 2026-10-20 (local time) */
export const formatDate = (value: DateInput): string => parts(value)?.[0] ?? EMPTY

/** 2026-10-20 14:02 (local time; date-only input stays date-only) */
export const formatDateTime = (value: DateInput): string => {
  const p = parts(value)
  return p ? (p[1] ? `${p[0]} ${p[1]}` : p[0]) : EMPTY
}
