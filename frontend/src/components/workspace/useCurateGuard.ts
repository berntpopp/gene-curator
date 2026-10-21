import { computed, ref } from 'vue'
import { useScopesStore } from '@/stores/scopes'

/**
 * Entry guard for the create forms: only curators and admins of the scope may start work.
 * Fails closed: the form shows only once the role is confirmed (`allowed`). A 403 from the role
 * lookup is a denial; any other error is `failed` (the page offers a retry).
 */
export function useCurateGuard(scopeId: () => string) {
  const decided = ref(false)
  const denied = ref(false)
  const failed = ref(false)
  const allowed = computed(() => decided.value && !denied.value && !failed.value)

  async function check() {
    decided.value = false
    denied.value = false
    failed.value = false
    try {
      const role = await useScopesStore().fetchUserRole(scopeId())
      denied.value = role !== 'curator' && role !== 'admin'
    } catch (e) {
      const status = (e as { response?: { status?: number } }).response?.status
      if (status === 403) denied.value = true
      else failed.value = true
    }
    decided.value = true
  }

  return { allowed, denied, failed, check }
}
