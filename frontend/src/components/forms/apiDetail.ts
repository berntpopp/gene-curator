import { rowLabel } from '@/views/curation/curationScores'

/** The API's own explanation of a failed request (`detail`), else the fallback. Never axios' generic text. */
export function apiDetail(error: unknown, fallback: string): string {
  const detail = (error as { response?: { data?: { detail?: unknown } } } | null)?.response?.data
    ?.detail
  if (typeof detail === 'string' && detail) return detail
  if (Array.isArray(detail)) {
    const msg = (detail[0] as { msg?: unknown } | undefined)?.msg
    if (typeof msg === 'string' && msg) return msg
  }
  const { message, errors } = (detail ?? {}) as { message?: unknown; errors?: unknown }
  if (typeof message !== 'string' || !message) return fallback
  // A refused submit lists {path, message}: name each row and field
  const listed = (Array.isArray(errors) ? (errors as { path?: unknown; message?: unknown }[]) : [])
    .map(e => `${rowLabel(String(e?.path ?? ''))}: ${String(e?.message ?? '')}`)
    .join('; ')
  return listed ? `${message}: ${listed}` : message
}
