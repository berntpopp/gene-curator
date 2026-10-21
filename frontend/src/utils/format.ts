/** Shared date and empty-value formatting: locale-neutral ISO output, em dash when missing. */
export const EMPTY = '—'

type DateInput = string | Date | null | undefined

const toIso = (value: DateInput): string | null => {
  if (!value) return null
  const d = value instanceof Date ? value : new Date(value)
  return Number.isNaN(d.getTime()) ? null : d.toISOString()
}

/** 2026-10-20 (UTC) */
export const formatDate = (value: DateInput): string => toIso(value)?.slice(0, 10) ?? EMPTY

/** 2026-10-20 14:02 (UTC) */
export const formatDateTime = (value: DateInput): string =>
  toIso(value)?.slice(0, 16).replace('T', ' ') ?? EMPTY
