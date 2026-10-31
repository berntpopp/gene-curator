/** Shape of the axios-style errors thrown by the API layer (only the fields stores read). */
export interface ApiError {
  message?: string
  stack?: string
  response?: {
    status?: number
    data?: { detail?: unknown; [key: string]: unknown }
  }
}

/** Narrow a caught `unknown` to the API error shape without `any`. */
export function toApiError(error: unknown): ApiError {
  return (error ?? {}) as ApiError
}

/** Human-readable message: server detail (string or first validation msg), axios message, fallback. */
export function errorMessage(error: unknown, fallback: string): string {
  const err = toApiError(error)
  const detail = err.response?.data?.detail
  if (typeof detail === 'string' && detail) return detail
  if (Array.isArray(detail)) {
    const msg = (detail[0] as { msg?: unknown } | undefined)?.msg
    if (typeof msg === 'string' && msg) return msg
  }
  return err.message || fallback
}

/** A 409 for a stale lock_version (its body has current_lock_version), not a workflow refusal. */
export function isStaleSave(error: unknown): boolean {
  const res = toApiError(error).response
  const detail = res?.data?.detail
  const nested = typeof detail === 'object' && detail !== null && 'current_lock_version' in detail
  return res?.status === 409 && (nested || res.data?.current_lock_version !== undefined)
}
