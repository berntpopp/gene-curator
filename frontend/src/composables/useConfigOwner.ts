import { computed, ref, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useScopesStore } from '@/stores/scopes'

/**
 * Who owns methodologies and workflows in the Setup pages (#284): platform admins manage
 * global templates and every scope's; scope admins manage their own scopes' items and see
 * global templates read-only (to derive from or pair).
 */
export function useConfigOwner() {
  const auth = useAuthStore()
  const scopesStore = useScopesStore()
  const isPlatformAdmin = computed(() => auth.isAdmin)
  const ownScopes = computed(() =>
    scopesStore.scopes.filter(s => isPlatformAdmin.value || s.user_role === 'admin')
  )
  const ownerOptions = computed(() => [
    ...(isPlatformAdmin.value ? [{ title: 'Global (all scopes)', value: null }] : []),
    ...ownScopes.value.map(s => ({ title: s.display_name || s.name, value: s.id as string }))
  ])
  /** Owner of what the user creates next; the first option by default. */
  const owner = ref<string | null>(null)
  watch(
    ownerOptions,
    options => {
      if (!options.some(o => o.value === owner.value)) owner.value = options[0]?.value ?? null
    },
    { immediate: true }
  )

  const canManage = (ownerScopeId?: string | null) =>
    isPlatformAdmin.value || (!!ownerScopeId && ownScopes.value.some(s => s.id === ownerScopeId))
  /** Rows to list: everything for platform admins, else global and the user's own scopes'. */
  const visible = <T extends { owner_scope_id?: string | null }>(rows: T[]): T[] =>
    isPlatformAdmin.value
      ? rows
      : rows.filter(r => !r.owner_scope_id || canManage(r.owner_scope_id))
  const ownerName = (ownerScopeId?: string | null) =>
    ownerScopeId
      ? (scopesStore.scopes.find(s => s.id === ownerScopeId)?.display_name ?? 'Scope')
      : 'Global'

  async function load() {
    if (scopesStore.scopes.length === 0) await scopesStore.fetchUserScopes().catch(() => undefined)
  }

  return { isPlatformAdmin, ownerOptions, owner, canManage, visible, ownerName, load }
}
