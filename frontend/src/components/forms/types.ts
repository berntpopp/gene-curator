/**
 * Shared types for the forms and gene components.
 */

/** Minimal shape of an axios-style error as caught in catch blocks. */
export interface ApiErrorLike {
  message?: string
  response?: { status?: number }
}
