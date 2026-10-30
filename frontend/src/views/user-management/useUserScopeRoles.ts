import { ref } from 'vue'
import { useScopesStore, type ScopeRecord, type ScopeRole } from '@/stores/scopes'

/** One accepted membership of a user, as shown in User Management. */
export interface UserScopeRole {
  scope_id: string
  scope_name: string
  role: ScopeRole
}

/** Accepted scope roles of every user, gathered from the member list of each scope (#218). */
export function useUserScopeRoles() {
  const store = useScopesStore()
  const scopes = ref<ScopeRecord[]>([])
  const rolesByUser = ref<Record<string, UserScopeRole[]>>({})

  // ponytail: one members call per scope; add memberships to the users list response if scopes grow
  async function load() {
    scopes.value = await store.fetchUserScopes({ limit: 1000 })
    const lists = await Promise.all(scopes.value.map(s => store.fetchMembers(s.id)))
    const map: Record<string, UserScopeRole[]> = {}
    scopes.value.forEach((s, i) => {
      for (const m of lists[i] ?? []) {
        ;(map[m.user_id] ??= []).push({ scope_id: s.id, scope_name: s.name, role: m.role })
      }
    })
    rolesByUser.value = map
  }

  return { scopes, rolesByUser, load }
}
