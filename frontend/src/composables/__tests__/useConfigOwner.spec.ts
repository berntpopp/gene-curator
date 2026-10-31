import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useAuthStore } from '@/stores/auth'
import { useScopesStore } from '@/stores/scopes'
import { useConfigOwner } from '../useConfigOwner'

const rows = [
  { id: 'g', owner_scope_id: null },
  { id: 'own', owner_scope_id: 's1' },
  { id: 'foreign', owner_scope_id: 's2' }
]

function signIn(role: 'user' | 'admin') {
  const auth = useAuthStore()
  auth.user = { id: 'u', role } as never
  useScopesStore().scopes = [
    { id: 's1', name: 'kidney', display_name: 'Kidney', user_role: 'admin' },
    { id: 's2', name: 'heart', display_name: 'Heart', user_role: 'curator' }
  ] as never
}

describe('useConfigOwner (#284)', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('gives a scope admin its own scopes, global rows read-only, other scopes hidden', () => {
    signIn('user')
    const o = useConfigOwner()
    expect(o.ownerOptions.value).toEqual([{ title: 'Kidney', value: 's1' }])
    expect(o.owner.value).toBe('s1')
    expect(o.visible(rows).map(r => r.id)).toEqual(['g', 'own'])
    expect([o.canManage(null), o.canManage('s1'), o.canManage('s2')]).toEqual([false, true, false])
    expect([o.ownerName(null), o.ownerName('s1'), o.ownerName('x')]).toEqual([
      'Global',
      'Kidney',
      'Scope'
    ])
  })

  it('gives a platform admin global and every scope', () => {
    signIn('admin')
    const o = useConfigOwner()
    expect(o.ownerOptions.value.map(x => x.value)).toEqual([null, 's1', 's2'])
    expect(o.owner.value).toBeNull()
    expect(o.visible(rows)).toHaveLength(3)
    expect(o.canManage(null)).toBe(true)
  })

  it('loads the scopes only when none are loaded', async () => {
    signIn('user')
    const scopes = useScopesStore()
    const fetch = vi.spyOn(scopes, 'fetchUserScopes').mockResolvedValue([] as never)
    await useConfigOwner().load()
    expect(fetch).not.toHaveBeenCalled()
    scopes.scopes = []
    await useConfigOwner().load()
    expect(fetch).toHaveBeenCalledTimes(1)
  })
})
