/** The API's own explanation of a failed request (`detail`), else the fallback. Never axios' generic text. */
export function apiDetail(error: unknown, fallback: string): string {
  const detail = (error as { response?: { data?: { detail?: unknown } } } | null)?.response?.data
    ?.detail
  if (typeof detail === 'string' && detail) return detail
  if (Array.isArray(detail)) {
    const msg = (detail[0] as { msg?: unknown } | undefined)?.msg
    if (typeof msg === 'string' && msg) return msg
  }
  const message = (detail as { message?: unknown } | undefined)?.message
  return typeof message === 'string' && message ? message : fallback
}
