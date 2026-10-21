import { ref } from 'vue'
import { useScopesStore } from '@/stores/scopes'

/**
 * Entry guard for the create forms: only curators and admins of the scope may start work.
 * `denied` stays false until `check()` has read the role, and also when the role cannot be read
 * (the server refuses the save anyway).
 */
export function useCurateGuard(scopeId: () => string) {
  const denied = ref(false)

  async function check() {
    try {
      const role = await useScopesStore().fetchUserRole(scopeId())
      denied.value = role !== 'curator' && role !== 'admin'
    } catch {
      denied.value = false
    }
  }

  return { denied, check }
}
