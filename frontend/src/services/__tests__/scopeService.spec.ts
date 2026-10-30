import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { AxiosResponse } from 'axios'
import apiClient from '@/api/client'
import { scopeService } from '../scopeService'

vi.mock('@/api/client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn()
  }
}))

const client = vi.mocked(apiClient)

function response(data: unknown): AxiosResponse {
  return { data } as AxiosResponse
}

describe('scopeService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('fetchScopes', () => {
    it('returns a bare array response as-is', async () => {
      client.get.mockResolvedValue(response([{ id: 's1' }]))

      await expect(scopeService.fetchScopes({ limit: 5 })).resolves.toEqual([{ id: 's1' }])
      expect(client.get).toHaveBeenCalledWith('/scopes/', {
        params: { detail: true, limit: 5 }
      })
    })
  })

  it('fetchScope, createScope and updateScope call the scope endpoints', async () => {
    client.get.mockResolvedValue(response({ id: 's1' }))
    client.post.mockResolvedValue(response({ id: 's3' }))
    client.patch.mockResolvedValue(response({ id: 's1', display_name: 'New' }))

    await expect(scopeService.fetchScope('s1')).resolves.toEqual({ id: 's1' })
    await expect(
      scopeService.createScope({ name: 'kidney', display_name: 'Kidney' } as never)
    ).resolves.toEqual({ id: 's3' })
    await expect(scopeService.updateScope('s1', { display_name: 'New' } as never)).resolves.toEqual(
      { id: 's1', display_name: 'New' }
    )

    expect(client.get).toHaveBeenCalledWith('/scopes/s1')
    expect(client.post).toHaveBeenCalledWith('/scopes/', { name: 'kidney', display_name: 'Kidney' })
    expect(client.patch).toHaveBeenCalledWith('/scopes/s1', { display_name: 'New' })
  })

  it('deleteScope and removeMember resolve to nothing', async () => {
    client.delete.mockResolvedValue(response(undefined))

    await expect(scopeService.deleteScope('s1')).resolves.toBeUndefined()
    await expect(scopeService.removeMember('s1', 'u1')).resolves.toBeUndefined()

    expect(client.delete).toHaveBeenCalledWith('/scopes/s1')
    expect(client.delete).toHaveBeenCalledWith('/scopes/s1/members/u1')
  })

  it('fetchStatistics reads the statistics endpoint', async () => {
    client.get.mockResolvedValue(response({ total_genes: 100 }))

    await expect(scopeService.fetchStatistics('s1')).resolves.toEqual({ total_genes: 100 })
    expect(client.get).toHaveBeenCalledWith('/scopes/s1/statistics')
  })

  describe('fetchMembers', () => {
    it('returns the members list, adding include_pending only when requested', async () => {
      client.get.mockResolvedValue(response({ members: [{ user_id: 'u1' }], total: 1 }))

      await expect(scopeService.fetchMembers('s1')).resolves.toEqual([{ user_id: 'u1' }])
      expect(client.get).toHaveBeenLastCalledWith('/scopes/s1/members', { params: {} })

      await scopeService.fetchMembers('s1', { includePending: true })
      expect(client.get).toHaveBeenLastCalledWith('/scopes/s1/members', {
        params: { include_pending: true }
      })
    })

    it('fetchMembersWithStats returns the full payload', async () => {
      const payload = { scope_id: 's1', total: 2, members: [], active_count: 2 }
      client.get.mockResolvedValue(response(payload))

      await expect(scopeService.fetchMembersWithStats('s1', true)).resolves.toEqual(payload)
      expect(client.get).toHaveBeenCalledWith('/scopes/s1/members', {
        params: { include_pending: true }
      })

      await scopeService.fetchMembersWithStats('s1')
      expect(client.get).toHaveBeenLastCalledWith('/scopes/s1/members', { params: {} })
    })
  })

  describe('fetchUserRole', () => {
    it('returns the matching membership', async () => {
      client.get.mockResolvedValue(
        response({
          members: [
            { user_id: 'u1', role: 'admin' },
            { user_id: 'u2', role: 'viewer' }
          ]
        })
      )

      await expect(scopeService.fetchUserRole('s1', 'u2')).resolves.toEqual({
        user_id: 'u2',
        role: 'viewer'
      })
    })

    it('returns null when the user is not a member', async () => {
      client.get.mockResolvedValue(response({ members: [{ user_id: 'u1', role: 'admin' }] }))

      await expect(scopeService.fetchUserRole('s1', 'nobody')).resolves.toBeNull()
    })

    it('returns null for 403 and 404 responses', async () => {
      client.get.mockRejectedValueOnce({ response: { status: 403 } })
      await expect(scopeService.fetchUserRole('s1', 'u1')).resolves.toBeNull()

      client.get.mockRejectedValueOnce({ response: { status: 404 } })
      await expect(scopeService.fetchUserRole('s1', 'u1')).resolves.toBeNull()
    })

    it('rethrows any other failure', async () => {
      const boom = { response: { status: 500 } }
      client.get.mockRejectedValueOnce(boom)

      await expect(scopeService.fetchUserRole('s1', 'u1')).rejects.toBe(boom)
    })
  })

  it('searchUsersForInvite sends the query and limit', async () => {
    client.get.mockResolvedValue(response([{ id: 'x' }]))

    await expect(scopeService.searchUsersForInvite('s1', 'ada')).resolves.toEqual([{ id: 'x' }])
    expect(client.get).toHaveBeenCalledWith('/scopes/s1/users/search', {
      params: { q: 'ada', limit: 10 }
    })
  })

  it('inviteMember posts the invitation and updateMemberRole patches the role', async () => {
    client.post.mockResolvedValue(response({ id: 'm1' }))
    client.patch.mockResolvedValue(response({ id: 'm1', role: 'reviewer' }))

    await expect(
      scopeService.inviteMember('s1', { email: 'x@y.z', role: 'curator' } as never)
    ).resolves.toEqual({ id: 'm1' })
    await expect(scopeService.updateMemberRole('s1', 'u1', 'reviewer')).resolves.toEqual({
      id: 'm1',
      role: 'reviewer'
    })

    expect(client.post).toHaveBeenCalledWith('/scopes/s1/invitations', {
      email: 'x@y.z',
      role: 'curator'
    })
    expect(client.patch).toHaveBeenCalledWith('/scopes/s1/members/u1', { role: 'reviewer' })
  })

  it('inviteMember with direct posts to /members (#505)', async () => {
    client.post.mockResolvedValue(response({ id: 'm2' }))
    await scopeService.inviteMember('s1', { user_id: 'u1', role: 'viewer' } as never, true)
    expect(client.post).toHaveBeenCalledWith('/scopes/s1/members', {
      user_id: 'u1',
      role: 'viewer'
    })
  })

  it('declineInvitation hits the decline endpoint', async () => {
    client.post.mockResolvedValue(response({}))

    await expect(scopeService.declineInvitation('i1')).resolves.toBeUndefined()

    expect(client.post).toHaveBeenCalledWith('/invitations/i1/decline')
  })
})
