/** Shape of the axios-style errors thrown by the API layer (only the fields stores read). */
export interface ApiError {
  message?: string
  stack?: string
  response?: {
    status?: number
    data?: { detail?: string; [key: string]: unknown }
  }
}

/** Narrow a caught `unknown` to the API error shape without `any`. */
export function toApiError(error: unknown): ApiError {
  return (error ?? {}) as ApiError
}
