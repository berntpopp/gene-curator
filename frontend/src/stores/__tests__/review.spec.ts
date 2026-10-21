import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useReviewStore } from '@/stores/review'
import { reviewCommentsAPI } from '@/api/reviewComments'

vi.mock('@/api/reviewComments', () => ({
  reviewCommentsAPI: {
    getDiff: vi.fn(),
    list: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    myPendingItemIds: vi.fn()
  }
}))

const api = vi.mocked(reviewCommentsAPI)
const comment = (o: Record<string, unknown>) =>
  ({ id: 'k1', status: 'open', kind: 'query', ...o }) as never

describe('review store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    Object.values(api).forEach(m => m.mockReset())
  })

  it('loads the diff and the comments together', async () => {
    api.getDiff.mockResolvedValue({ baseline: null, items: [{ path: 'a' }] } as never)
    api.list.mockResolvedValue([comment({})] as never)
    const s = useReviewStore()
    await s.load('cur')
    expect(s.diff?.items).toHaveLength(1)
    expect(s.comments).toHaveLength(1)
    expect(s.error).toBeNull()
  })

  it('keeps an error message when loading fails', async () => {
    api.getDiff.mockRejectedValue({ response: { data: { detail: 'nope' } } })
    api.list.mockResolvedValue([])
    const s = useReviewStore()
    await s.load('cur')
    expect(s.error).toBe('nope')
  })

  it('accepts an item, queries it and replies', async () => {
    api.create.mockImplementation(async (_c, body) => comment({ id: `n${Math.random()}`, ...body }))
    const s = useReviewStore()
    s.curationId = 'cur'
    await s.accept('p')
    await s.query('p', 'why?')
    expect(api.create).toHaveBeenNthCalledWith(1, 'cur', { item_path: 'p', kind: 'accepted' })
    expect(api.create).toHaveBeenNthCalledWith(2, 'cur', {
      item_path: 'p',
      kind: 'query',
      body: 'why?'
    })
    expect(s.comments).toHaveLength(2)
  })

  it('withdraws an acceptance and resolves a thread by resolving every open query', async () => {
    api.update.mockImplementation(async (_c, id, body) => comment({ id, ...body }))
    const s = useReviewStore()
    s.curationId = 'cur'
    s.comments = [
      comment({ id: 'a', item_path: 'p', kind: 'accepted' }),
      comment({ id: 'q1', item_path: 'p' }),
      comment({ id: 'q2', item_path: 'p' }),
      comment({ id: 'q3', item_path: 'other' })
    ]
    await s.withdraw('a')
    await s.resolveThread('p')
    expect(s.comments.map(x => [x.id, x.status])).toEqual([
      ['a', 'resolved'],
      ['q1', 'resolved'],
      ['q2', 'resolved'],
      ['q3', 'open']
    ])
  })

  it('reads my pending review item ids', async () => {
    api.myPendingItemIds.mockResolvedValue(['c1', 'c2'])
    const s = useReviewStore()
    expect(await s.fetchMyPending()).toEqual(new Set(['c1', 'c2']))
  })
})
