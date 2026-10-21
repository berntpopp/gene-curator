import { describe, it, expect, vi } from 'vitest'
import apiClient from '../client'
import { geneResolveAPI } from '../geneResolve'

vi.mock('../client', () => ({ default: { post: vi.fn() } }))

describe('geneResolveAPI', () => {
  it('posts the symbols to /genes/resolve and returns the body', async () => {
    const body = { items: [], counts: { resolved: 0, ambiguous: 0, not_found: 0 } }
    vi.mocked(apiClient.post).mockResolvedValue({ data: body })
    expect(await geneResolveAPI.resolve(['PKD1'])).toBe(body)
    expect(apiClient.post).toHaveBeenCalledWith('/genes/resolve', { symbols: ['PKD1'] })
  })
})
