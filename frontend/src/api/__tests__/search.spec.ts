import { describe, it, expect, vi } from 'vitest'
import type { AxiosResponse } from 'axios'
import apiClient from '../client'
import { searchAPI } from '../search'

vi.mock('../client', () => ({ default: { get: vi.fn() } }))

describe('searchAPI', () => {
  it('sends q and the abort signal to GET /search and returns the body', async () => {
    const body = { genes: [], curations: [], scopes: [] }
    vi.mocked(apiClient.get).mockResolvedValueOnce({ data: body } as AxiosResponse)
    const { signal } = new AbortController()
    await expect(searchAPI.search('pkd', signal)).resolves.toBe(body)
    expect(apiClient.get).toHaveBeenCalledWith('/search', { params: { q: 'pkd' }, signal })
  })
})
