import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { ScopeMember, ScopeRecord } from '@/stores/scopes'
import { setActivePinia, createPinia } from 'pinia'
import { useScopesStore } from '@/stores/scopes'
import { useAuthStore } from '@/stores/auth'
import { scopeService } from '@/services/scopeService'
import { logService } from '@/services/logService'
import type { Schema } from '@/types/api'

vi.mock('@/services/scopeService', () => ({
  scopeService: {
    fetchScopes: vi.fn(),
    fetchScope: vi.fn(),
    createScope: vi.fn(),
    updateScope: vi.fn(),
    deleteScope: vi.fn(),
    fetchStatistics: vi.fn(),
    fetchMembers: vi.fn(),
    inviteMember: vi.fn(),
    updateMemberRole: vi.fn(),
    removeMember: vi.fn()
  }
}))

vi.mock('@/services/logService', () => ({
  logService: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }
}))

// The auth store is real; its only network call (authAPI) is not used by these tests.
vi.mock('@/api', () => ({ authAPI: {} }))

const api = vi.mocked(scopeService)

const scope = (id: string, extra: Record<string, unknown> = {}) =>
  ({
    id,
    name: `scope-${id}`,
    is_public: false,
    is_active: true,
    institution: 'Charite',
    ...extra
  }) as ScopeRecord

const member = (userId: string, role = 'curator') => ({ user_id: userId, role }) as ScopeMember

/** Error with a message, as thrown by the scope service. */
const fail = (message: string) => new Error(message)

describe('useScopesStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('getters', () => {
    it('partitions scopes and counts active ones', () => {
      const store = useScopesStore()
      store.scopes = [
        scope('a', { is_public: true }),
        scope('b', { is_active: false, institution: 'Other' })
      ] as never

      expect(store.userScopes).toHaveLength(2)
      expect(store.publicScopes.map(s => s.id)).toEqual(['a'])
      expect(store.privateScopes.map(s => s.id)).toEqual(['b'])
      expect(store.activeScopesCount).toBe(1)
      expect(store.getScopeById('b')?.id).toBe('b')
      expect(store.getScopeById('zzz')).toBeUndefined()
      expect(store.getScopesByInstitution('Other').map(s => s.id)).toEqual(['b'])
    })

    it('returns scope members and statistics with defaults', () => {
      const store = useScopesStore()
      store.scopeUsers = { s1: [member('u1')] as never }
      store.scopeStatistics = { s1: { total_genes_assigned: 3 } as never }

      expect(store.getScopeUsers('s1')).toEqual([member('u1')])
      expect(store.getScopeUsers('none')).toEqual([])
      expect(store.getScopeStatistics('s1')).toEqual({ total_genes_assigned: 3 })
      expect(store.getScopeStatistics('none')).toBeNull()
    })
  })

  describe('fetchUserScopes', () => {
    it('stores the scopes and returns them', async () => {
      const store = useScopesStore()
      api.fetchScopes.mockResolvedValue([scope('a')])

      await expect(store.fetchUserScopes({ mine: true })).resolves.toEqual([scope('a')])
      expect(api.fetchScopes).toHaveBeenCalledWith({ mine: true })
      expect(store.scopes).toHaveLength(1)
      expect(store.loading).toBe(false)
    })

    it('records the error and rethrows', async () => {
      const store = useScopesStore()
      api.fetchScopes.mockRejectedValue(fail('down'))

      await expect(store.fetchUserScopes()).rejects.toThrow('down')
      expect(store.error).toBe('down')
      expect(logService.error).toHaveBeenCalledWith('Failed to fetch scopes', { error: 'down' })
    })
  })

  describe('fetchScope', () => {
    it('sets current and replaces or appends the list entry', async () => {
      const store = useScopesStore()
      store.scopes = [scope('a', { name: 'old' })]

      api.fetchScope.mockResolvedValueOnce(scope('a', { name: 'new' }) as Schema<'ScopeWithStats'>)
      await store.fetchScope('a')
      expect(store.currentScope).toMatchObject({ name: 'new' })
      expect(store.scopes[0]).toMatchObject({ name: 'new' })

      api.fetchScope.mockResolvedValueOnce(scope('b') as Schema<'ScopeWithStats'>)
      await store.fetchScope('b')
      expect(store.scopes.map(s => s.id)).toEqual(['a', 'b'])
    })

    it('records the error and rethrows', async () => {
      const store = useScopesStore()
      api.fetchScope.mockRejectedValue(fail('404'))

      await expect(store.fetchScope('x')).rejects.toThrow('404')
      expect(store.error).toBe('404')
    })
  })

  describe('createScope', () => {
    it('appends the scope and makes the creator admin', async () => {
      const store = useScopesStore()
      api.createScope.mockResolvedValue(scope('new') as Schema<'Scope'>)

      const created = await store.createScope({
        name: 'New',
        display_name: 'New'
      } as Schema<'ScopeCreate'>)

      expect(created.id).toBe('new')
      expect(store.scopes.map(s => s.id)).toEqual(['new'])
      expect(store.currentScope?.id).toBe('new')
      expect(store.currentUserRole).toBe('admin')
    })

    it('records the error and rethrows', async () => {
      const store = useScopesStore()
      api.createScope.mockRejectedValue(fail('duplicate'))

      await expect(store.createScope({ name: 'X' } as Schema<'ScopeCreate'>)).rejects.toThrow(
        'duplicate'
      )
      expect(store.error).toBe('duplicate')
      expect(logService.error).toHaveBeenCalledWith(
        'Failed to create scope',
        expect.objectContaining({ name: 'X' })
      )
    })
  })

  describe('updateScope', () => {
    it('replaces list and current entries and logs the changed keys', async () => {
      const store = useScopesStore()
      store.scopes = [scope('a')] as never
      store.currentScope = scope('a')
      api.updateScope.mockResolvedValue(scope('a', { name: 'renamed' }) as Schema<'Scope'>)

      await store.updateScope('a', { name: 'renamed' } as Schema<'ScopeUpdate'>)

      expect(store.scopes[0]).toMatchObject({ name: 'renamed' })
      expect(store.currentScope).toMatchObject({ name: 'renamed' })
      expect(logService.info).toHaveBeenCalledWith(
        'Scope updated',
        expect.objectContaining({ scope_id: 'a', changes: ['name'] })
      )
    })

    it('keeps unrelated current scope and records errors', async () => {
      const store = useScopesStore()
      store.currentScope = scope('other')
      api.updateScope.mockResolvedValueOnce(scope('a'))
      await store.updateScope('a', {} as Schema<'ScopeUpdate'>)
      expect(store.currentScope?.id).toBe('other')

      api.updateScope.mockRejectedValueOnce(fail('locked'))
      await expect(store.updateScope('a', {} as Schema<'ScopeUpdate'>)).rejects.toThrow('locked')
      expect(store.error).toBe('locked')
    })
  })

  describe('deleteScope', () => {
    it('removes the scope and its cached data, clearing current and role', async () => {
      const store = useScopesStore()
      store.scopes = [scope('a'), scope('b')] as never
      store.currentScope = scope('a')
      store.currentUserRole = 'admin'
      store.scopeUsers = { a: [member('u1')] }
      store.scopeStatistics = { a: {} as never }
      api.deleteScope.mockResolvedValue({} as never)

      await expect(store.deleteScope('a')).resolves.toBe(true)

      expect(store.scopes.map(s => s.id)).toEqual(['b'])
      expect(store.currentScope).toBeNull()
      expect(store.currentUserRole).toBeNull()
      expect(store.scopeUsers.a).toBeUndefined()
      expect(store.scopeStatistics.a).toBeUndefined()
    })

    it('keeps role and current scope when deleting another scope; records errors', async () => {
      const store = useScopesStore()
      store.currentScope = scope('keep')
      store.currentUserRole = 'curator'
      api.deleteScope.mockResolvedValueOnce({} as never)
      await store.deleteScope('a')
      expect(store.currentScope?.id).toBe('keep')
      expect(store.currentUserRole).toBe('curator')

      api.deleteScope.mockRejectedValueOnce(fail('in use'))
      await expect(store.deleteScope('a')).rejects.toThrow('in use')
      expect(store.error).toBe('in use')
    })
  })

  describe('fetchUserRole', () => {
    it('returns null without a logged-in user', async () => {
      const store = useScopesStore()

      await expect(store.fetchUserRole('s1')).resolves.toBeNull()
      expect(store.currentUserRole).toBeNull()
      expect(api.fetchMembers).not.toHaveBeenCalled()
    })

    it('grants implicit admin to application admins', async () => {
      const auth = useAuthStore()
      auth.user = { id: 'me', role: 'admin' } as never

      await expect(useScopesStore().fetchUserRole('s1')).resolves.toBe('admin')
      expect(api.fetchMembers).not.toHaveBeenCalled()
    })

    it('reads the role from scope membership for other users', async () => {
      const auth = useAuthStore()
      auth.user = { id: 'me', role: 'user' } as never
      const store = useScopesStore()
      api.fetchMembers.mockResolvedValue([member('other', 'admin'), member('me', 'reviewer')])

      await expect(store.fetchUserRole('s1')).resolves.toBe('reviewer')
      expect(store.currentUserRole).toBe('reviewer')
    })

    it('returns null when the user is not a member', async () => {
      const auth = useAuthStore()
      auth.user = { id: 'me', role: 'user' } as never
      const store = useScopesStore()
      api.fetchMembers.mockResolvedValue([])

      await expect(store.fetchUserRole('s1')).resolves.toBeNull()
    })

    it('clears the role, logs and rethrows on failure', async () => {
      const auth = useAuthStore()
      auth.user = { id: 'me', role: 'user' } as never
      const store = useScopesStore()
      store.currentUserRole = 'admin'
      api.fetchMembers.mockRejectedValue(fail('forbidden'))

      await expect(store.fetchUserRole('s1')).rejects.toThrow('forbidden')
      expect(store.currentUserRole).toBeNull()
      expect(logService.error).toHaveBeenCalledWith(
        'Failed to fetch user role',
        expect.objectContaining({ scope_id: 's1', error: 'forbidden' })
      )
    })
  })

  describe('members', () => {
    it('fetchMembers caches the list and rethrows on failure', async () => {
      const store = useScopesStore()
      api.fetchMembers.mockResolvedValueOnce([member('u1')])

      await expect(store.fetchMembers('s1')).resolves.toEqual([member('u1')])
      expect(store.scopeUsers.s1).toEqual([member('u1')])

      api.fetchMembers.mockRejectedValueOnce(fail('no'))
      await expect(store.fetchMembers('s1')).rejects.toThrow('no')
    })

    it('inviteMember refreshes the members list', async () => {
      const store = useScopesStore()
      api.inviteMember.mockResolvedValue(member('invited'))
      api.fetchMembers.mockResolvedValue([member('u2')])

      await expect(
        store.inviteMember('s1', { email: 'new@x.org', role: 'curator' } as never)
      ).resolves.toEqual(member('invited'))

      expect(api.fetchMembers).toHaveBeenCalledWith('s1')
      expect(store.scopeUsers.s1).toEqual([member('u2')])
    })

    it('inviteMember records errors and rethrows', async () => {
      const store = useScopesStore()
      api.inviteMember.mockRejectedValue(fail('full'))

      await expect(store.inviteMember('s1', { role: 'viewer' } as never)).rejects.toThrow('full')
      expect(logService.error).toHaveBeenCalledWith(
        'Failed to invite member',
        expect.objectContaining({ error: 'full' })
      )
    })

    it('updateMemberRole updates the cached member role', async () => {
      const store = useScopesStore()
      store.scopeUsers = { s1: [member('u1', 'viewer')] as never }
      api.updateMemberRole.mockResolvedValue(member('u1', 'curator'))

      await expect(store.updateMemberRole('s1', 'u1', 'curator')).resolves.toEqual(
        member('u1', 'curator')
      )

      expect(store.scopeUsers.s1?.[0]?.role).toBe('curator')
    })

    it('updateMemberRole tolerates an uncached scope and records errors', async () => {
      const store = useScopesStore()
      api.updateMemberRole.mockResolvedValueOnce({} as never)
      await store.updateMemberRole('s9', 'u1', 'admin')
      expect(store.scopeUsers.s9).toBeUndefined()

      api.updateMemberRole.mockRejectedValueOnce(fail('denied'))
      await expect(store.updateMemberRole('s1', 'u1', 'admin')).rejects.toThrow('denied')
    })

    it('removeMember drops the member from the cache and records errors', async () => {
      const store = useScopesStore()
      store.scopeUsers = { s1: [member('u1'), member('u2')] as never }
      api.removeMember.mockResolvedValue({} as never)

      await store.removeMember('s1', 'u1')

      expect(store.scopeUsers.s1?.map(m => m.user_id)).toEqual(['u2'])

      api.removeMember.mockRejectedValueOnce(fail('last admin'))
      await expect(store.removeMember('s1', 'u2')).rejects.toThrow('last admin')
      expect(logService.error).toHaveBeenCalledWith(
        'Failed to remove member',
        expect.objectContaining({ error: 'last admin' })
      )
    })

    it('removeMember is fine for an uncached scope', async () => {
      const store = useScopesStore()
      api.removeMember.mockResolvedValue({} as never)

      await store.removeMember('s9', 'u1')

      expect(store.scopeUsers.s9).toBeUndefined()
    })
  })

  describe('fetchStatistics', () => {
    it('caches statistics and records errors', async () => {
      const store = useScopesStore()
      api.fetchStatistics.mockResolvedValueOnce({
        total_genes_assigned: 4
      } as Schema<'ScopeStatistics'>)

      await expect(store.fetchStatistics('s1')).resolves.toEqual({
        total_genes_assigned: 4
      } as Schema<'ScopeStatistics'>)
      expect(store.scopeStatistics.s1).toEqual({
        total_genes_assigned: 4
      } as Schema<'ScopeStatistics'>)

      api.fetchStatistics.mockRejectedValueOnce(fail('stats'))
      await expect(store.fetchStatistics('s1')).rejects.toThrow('stats')
      expect(logService.error).toHaveBeenCalledWith(
        'Failed to fetch statistics',
        expect.objectContaining({ error: 'stats' })
      )
    })
  })

  describe('local state actions', () => {
    it('setCurrentScope, clearCurrentScope and clearError', () => {
      const store = useScopesStore()
      store.setCurrentScope(scope('a'))
      expect(store.currentScope?.id).toBe('a')

      store.currentUserRole = 'admin'
      store.clearCurrentScope()
      expect(store.currentScope).toBeNull()
      expect(store.currentUserRole).toBeNull()

      store.setCurrentScope(null)
      expect(store.currentScope).toBeNull()

      store.error = 'x'
      store.clearError()
      expect(store.error).toBeNull()
    })
  })
})
