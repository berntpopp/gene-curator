import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { AxiosResponse } from 'axios'
import apiClient from '../client'
import { usersApi } from '../users'

// usersApi goes through the shared client (token refresh lives there, see client.spec.ts)
vi.mock('../client', () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() }
}))

const client = vi.mocked(apiClient)
const ok = { data: 'payload' } as AxiosResponse

type Method = 'get' | 'post' | 'put' | 'delete'
const rows: { name: string; run: () => Promise<unknown>; method: Method; args: unknown[] }[] = [
  {
    name: 'getUsers',
    run: () => usersApi.getUsers({ skip: 0, limit: 10 }),
    method: 'get',
    args: ['/users/', { params: { skip: 0, limit: 10 } }]
  },
  {
    name: 'getUser',
    run: () => usersApi.getUser('u1'),
    method: 'get',
    args: ['/users/u1']
  },
  {
    name: 'createUser',
    run: () => usersApi.createUser({ email: 'a@b.c' } as never),
    method: 'post',
    args: ['/users/', { email: 'a@b.c' }]
  },
  {
    name: 'updateUser',
    run: () => usersApi.updateUser('u1', { name: 'N' } as never),
    method: 'put',
    args: ['/users/u1', { name: 'N' }]
  },
  {
    name: 'updateUserPassword sends a JSON body, never a query string',
    run: () => usersApi.updateUserPassword('u1', 'longpassword'),
    method: 'put',
    args: ['/users/u1/password', { new_password: 'longpassword' }]
  },
  {
    name: 'activateUser',
    run: () => usersApi.activateUser('u1'),
    method: 'put',
    args: ['/users/u1/activate']
  },
  {
    name: 'deactivateUser',
    run: () => usersApi.deactivateUser('u1'),
    method: 'put',
    args: ['/users/u1/deactivate']
  },
  {
    name: 'deleteUser',
    run: () => usersApi.deleteUser('u1'),
    method: 'delete',
    args: ['/users/u1']
  },
  {
    name: 'getUserStatistics',
    run: () => usersApi.getUserStatistics(),
    method: 'get',
    args: ['/users/statistics']
  },
  {
    name: 'getUserActivity',
    run: () => usersApi.getUserActivity('u1'),
    method: 'get',
    args: ['/users/u1/activity']
  }
]

describe('usersApi', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    for (const m of ['get', 'post', 'put', 'delete'] as const) client[m].mockResolvedValue(ok)
  })

  it.each(rows)('$name', async row => {
    expect(await row.run()).toBe('payload')
    expect(client[row.method]).toHaveBeenCalledWith(...row.args)
  })

  it('searchUsers sends the query as q', async () => {
    await usersApi.searchUsers('ann')
    expect(client.get).toHaveBeenCalledWith('/users/search', {
      params: expect.objectContaining({ q: 'ann' })
    })
  })
})
