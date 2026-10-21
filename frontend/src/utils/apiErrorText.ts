/**
 * One readable sentence for a failed request. FastAPI answers a validation error (422) with an
 * array of `{ loc, msg, ... }`; showing that raw (or only its first `msg`) is what users saw.
 */
interface ValidationItem {
  loc?: unknown[]
  msg?: unknown
}

const sentence = (text: string) => (/[.!?]$/.test(text) ? text : `${text}.`)

/** `['body', 'target_stage']` -> `Target stage`. */
function fieldName(loc: unknown[] | undefined): string {
  const name = [...(loc ?? [])].reverse().find(p => typeof p === 'string' && p !== 'body')
  return typeof name === 'string'
    ? name.charAt(0).toUpperCase() + name.slice(1).replace(/_/g, ' ')
    : ''
}

export function readableApiError(error: unknown, fallback: string): string {
  const err = error as { message?: string; response?: { data?: { detail?: unknown } } } | null
  const detail = err?.response?.data?.detail
  if (typeof detail === 'string' && detail) return detail
  if (Array.isArray(detail)) {
    const parts = (detail as ValidationItem[])
      .filter(d => typeof d?.msg === 'string' && d.msg)
      .map(d => {
        const field = fieldName(d.loc)
        return sentence(field ? `${field}: ${d.msg}` : String(d.msg))
      })
    if (parts.length) return [...new Set(parts)].join(' ')
  } else if (detail && typeof detail === 'object') {
    const message = (detail as { message?: unknown }).message
    if (typeof message === 'string' && message) return message
  }
  return err?.message || fallback
}
