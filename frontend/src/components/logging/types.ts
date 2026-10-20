/**
 * Minimal shape of the logger returned by useLogger().
 * composables/useLogger.js is still JavaScript, so its return type is inferred as {}.
 */
export interface ComponentLogger {
  debug: (message: string, data?: Record<string, unknown>) => void
  info: (message: string, data?: Record<string, unknown>) => void
  warn: (message: string, data?: Record<string, unknown>) => void
  error: (message: string, data?: Record<string, unknown>) => void
}
