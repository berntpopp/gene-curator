import { describe, it, expect, vi } from 'vitest'
import apiClient from '@/api/client'
import { myWorkApi } from '@/api/myWork'

vi.mock('@/api/client', () => ({ default: { get: vi.fn() } }))

describe('myWorkApi', () => {
  it('reads /me/work', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: { items: [], counts: {} } })
    expect(await myWorkApi.getMyWork()).toEqual({ items: [], counts: {} })
    expect(apiClient.get).toHaveBeenCalledWith('/me/work')
  })
})
