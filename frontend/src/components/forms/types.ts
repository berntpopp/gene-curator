/**
 * Shared types for the forms and gene components.
 */

/** Scoped logger from useLogger(); its JSDoc types the return value as Object, so it is narrowed here. */
export interface ComponentLogger {
  debug(message: string, data?: Record<string, unknown>): void
  info(message: string, data?: Record<string, unknown>): void
  warn(message: string, data?: Record<string, unknown>): void
  error(message: string, data?: Record<string, unknown>): void
}

/** Minimal shape of an axios-style error as caught in catch blocks. */
export interface ApiErrorLike {
  message?: string
  response?: { status?: number }
}
