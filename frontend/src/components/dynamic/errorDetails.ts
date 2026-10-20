/**
 * Log-friendly details for a caught value of unknown type.
 *
 * `catch` bindings are `unknown` under strict TypeScript, so the message and
 * stack are read defensively instead of through `error.message`.
 */
export function errorDetails(error: unknown): { error: string; stack?: string } {
  if (error instanceof Error) {
    return { error: error.message, stack: error.stack }
  }
  return { error: String(error) }
}
