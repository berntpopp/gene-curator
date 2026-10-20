export const FORM_RECOVERY_PREFIX = 'form_recovery_'

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
