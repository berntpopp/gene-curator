import { describe, it, expect, vi } from 'vitest'
import apiClient from '../client'
import { reviewCommentsAPI } from '../reviewComments'

vi.mock('../client', () => ({ default: { get: vi.fn(), post: vi.fn(), patch: vi.fn() } }))

describe('reviewCommentsAPI', () => {
  it('reads the diff and the comments', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: 'x' })
    expect(await reviewCommentsAPI.getDiff('c1')).toBe('x')
    expect(apiClient.get).toHaveBeenCalledWith('/curations/c1/diff')
    await reviewCommentsAPI.list('c1')
    expect(apiClient.get).toHaveBeenCalledWith('/curations/c1/review-comments')
  })

  it('creates and updates a comment', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: 'n' })
    vi.mocked(apiClient.patch).mockResolvedValue({ data: 'u' })
    expect(await reviewCommentsAPI.create('c1', { item_path: 'p', kind: 'query', body: 'b' })).toBe(
      'n'
    )
    expect(apiClient.post).toHaveBeenCalledWith('/curations/c1/review-comments', {
      item_path: 'p',
      kind: 'query',
      body: 'b'
    })
    expect(await reviewCommentsAPI.update('c1', 'k', { status: 'resolved' })).toBe('u')
    expect(apiClient.patch).toHaveBeenCalledWith('/curations/c1/review-comments/k', {
      status: 'resolved'
    })
  })

  it('lists the item ids of my pending reviews', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: [{ item_id: 'a' }, { item_id: 'b' }] })
    expect(await reviewCommentsAPI.myPendingItemIds()).toEqual(['a', 'b'])
    expect(apiClient.get).toHaveBeenCalledWith('/workflow/reviews/my-assignments', {
      params: { status: 'pending', limit: 200 }
    })
  })
})
