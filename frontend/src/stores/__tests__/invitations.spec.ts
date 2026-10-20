import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import type { Invitation } from '@/stores/invitations'
import { setActivePinia, createPinia } from 'pinia'
import { useInvitationsStore } from '@/stores/invitations'
import { invitationsApi } from '@/api/invitations'
import apiClient from '@/api/client'
import { logService } from '@/services/logService'

vi.mock('@/api/invitations', () => ({
  invitationsApi: {
    getPendingInvitations: vi.fn(),
    declineInvitation: vi.fn()
  }
}))

vi.mock('@/api/client', () => ({
  default: { post: vi.fn() }
}))

vi.mock('@/services/logService', () => ({
  logService: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }
}))

const api = vi.mocked(invitationsApi)
const client = vi.mocked(apiClient)

const invite = (id: string, expired = false) =>
  ({ id, scope_id: 's1', is_expired: expired }) as Invitation

describe('useInvitationsStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  describe('computed', () => {
    it('splits pending and expired invitations', () => {
      const store = useInvitationsStore()
      store.invitations = [invite('a'), invite('b', true)] as never

      expect(store.pendingCount).toBe(1)
      expect(store.pendingInvitations.map(i => i.id)).toEqual(['a'])
      expect(store.expiredInvitations.map(i => i.id)).toEqual(['b'])
      expect(store.hasPendingInvitations).toBe(true)
    })

    it('reports no pending invitations when all are expired', () => {
      const store = useInvitationsStore()
      store.invitations = [invite('b', true)] as never
      expect(store.hasPendingInvitations).toBe(false)
    })
  })

  describe('fetchPendingInvitations', () => {
    it('loads invitations and records the fetch time', async () => {
      vi.useFakeTimers()
      vi.setSystemTime(new Date('2025-01-01T00:00:00Z'))
      const store = useInvitationsStore()
      api.getPendingInvitations.mockResolvedValue({ invitations: [invite('a')] })

      const result = await store.fetchPendingInvitations({ includeExpired: true })

      expect(api.getPendingInvitations).toHaveBeenCalledWith({ includeExpired: true })
      expect(result).toHaveLength(1)
      expect(store.lastFetched).toBe(Date.parse('2025-01-01T00:00:00Z'))
      expect(store.loading).toBe(false)
    })

    it('skips the request when fetched within 30 seconds unless forced', async () => {
      vi.useFakeTimers()
      const store = useInvitationsStore()
      api.getPendingInvitations.mockResolvedValue({ invitations: [invite('a')] })
      await store.fetchPendingInvitations()

      vi.advanceTimersByTime(5000)
      await store.fetchPendingInvitations()
      expect(api.getPendingInvitations).toHaveBeenCalledTimes(1)
      expect(logService.debug).toHaveBeenCalledWith(
        'Skipping invitation fetch - recently fetched',
        expect.any(Object)
      )

      await store.fetchPendingInvitations({ force: true })
      expect(api.getPendingInvitations).toHaveBeenCalledTimes(2)
    })

    it('refetches once the 30 second window has passed', async () => {
      vi.useFakeTimers()
      const store = useInvitationsStore()
      api.getPendingInvitations.mockResolvedValue({ invitations: [] })
      await store.fetchPendingInvitations()

      vi.advanceTimersByTime(30000)
      await store.fetchPendingInvitations()

      expect(api.getPendingInvitations).toHaveBeenCalledTimes(2)
    })

    it('stores the API detail, logs and rethrows on failure', async () => {
      const store = useInvitationsStore()
      const failure = Object.assign(new Error('x'), { response: { data: { detail: 'Auth' } } })
      api.getPendingInvitations.mockRejectedValue(failure)

      await expect(store.fetchPendingInvitations()).rejects.toBe(failure)
      expect(store.error).toBe('Auth')
      expect(store.loading).toBe(false)
      expect(logService.error).toHaveBeenCalledWith(
        'Failed to fetch invitations',
        expect.objectContaining({ error: 'x' })
      )
    })

    it('uses a generic message when the failure has no detail', async () => {
      const store = useInvitationsStore()
      api.getPendingInvitations.mockRejectedValue(new Error('net'))

      await expect(store.fetchPendingInvitations()).rejects.toThrow('net')
      expect(store.error).toBe('Failed to fetch invitations')
    })
  })

  describe('acceptInvitation', () => {
    it('posts the acceptance, removes the invitation and returns the membership', async () => {
      const store = useInvitationsStore()
      store.invitations = [invite('a'), invite('b')] as never
      client.post.mockResolvedValue({ data: { role: 'curator' } })

      const membership = await store.acceptInvitation('a', 's1')

      expect(client.post).toHaveBeenCalledWith('/scopes/s1/invitations/a/accept')
      expect(membership).toEqual({ role: 'curator' })
      expect(store.invitations.map(i => i.id)).toEqual(['b'])
      expect(store.loading).toBe(false)
    })

    it('stores the error and rethrows on failure', async () => {
      const store = useInvitationsStore()
      client.post.mockRejectedValue(
        Object.assign(new Error('x'), { response: { data: { detail: 'Expired' } } })
      )

      await expect(store.acceptInvitation('a', 's1')).rejects.toThrow('x')
      expect(store.error).toBe('Expired')
      expect(logService.error).toHaveBeenCalledWith(
        'Failed to accept invitation',
        expect.objectContaining({ invitationId: 'a', scopeId: 's1' })
      )
    })

    it('uses a generic message when no detail is returned', async () => {
      const store = useInvitationsStore()
      client.post.mockRejectedValue(new Error('net'))

      await expect(store.acceptInvitation('a', 's1')).rejects.toThrow('net')
      expect(store.error).toBe('Failed to accept invitation')
    })
  })

  describe('declineInvitation', () => {
    it('removes the invitation locally', async () => {
      const store = useInvitationsStore()
      store.invitations = [invite('a'), invite('b')] as never
      api.declineInvitation.mockResolvedValue({} as never)

      await store.declineInvitation('a')

      expect(api.declineInvitation).toHaveBeenCalledWith('a')
      expect(store.invitations.map(i => i.id)).toEqual(['b'])
    })

    it('stores the error and rethrows on failure', async () => {
      const store = useInvitationsStore()
      api.declineInvitation.mockRejectedValue(new Error('gone'))

      await expect(store.declineInvitation('a')).rejects.toThrow('gone')
      expect(store.error).toBe('Failed to decline invitation')
    })

    it('prefers the API detail when present', async () => {
      const store = useInvitationsStore()
      api.declineInvitation.mockRejectedValue(
        Object.assign(new Error('x'), { response: { data: { detail: 'Locked' } } })
      )

      await expect(store.declineInvitation('a')).rejects.toThrow('x')
      expect(store.error).toBe('Locked')
    })
  })

  describe('clearInvitations and $reset', () => {
    it('clearInvitations empties state and the fetch timestamp', () => {
      const store = useInvitationsStore()
      store.invitations = [invite('a')] as never
      store.lastFetched = 123
      store.error = 'x'

      store.clearInvitations()

      expect(store.invitations).toEqual([])
      expect(store.lastFetched).toBeNull()
      expect(store.error).toBeNull()
    })

    it('$reset clears invitations, loading and error', () => {
      const store = useInvitationsStore()
      store.invitations = [invite('a')] as never
      store.loading = true
      store.error = 'x'

      store.$reset()

      expect(store.invitations).toEqual([])
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
    })
  })
})
