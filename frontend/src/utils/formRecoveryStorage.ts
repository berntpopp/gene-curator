export const FORM_RECOVERY_PREFIX = 'form_recovery_'

/** The server version a draft is bound to: every save changes lock_version and updated_at */
export const recoveryVersion = (record: {
  lock_version?: number | null
  updated_at?: string | null
}): string => `${record.lock_version}@${record.updated_at}`

/** Remove every saved form draft (all users) so a shared browser never leaks them. */
export function clearFormRecoveryDrafts(): void {
  try {
    Object.keys(localStorage)
      .filter(key => key.startsWith(FORM_RECOVERY_PREFIX))
      .forEach(key => localStorage.removeItem(key))
  } catch {
    // storage unavailable: nothing to clear
  }
}
