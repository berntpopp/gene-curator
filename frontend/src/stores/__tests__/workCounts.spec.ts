import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { myWorkApi } from '@/api/myWork'
import { useWorkCountsStore } from '../workCounts'

vi.mock('@/api/myWork', () => ({ myWorkApi: { getMyWork: vi.fn() } }))

const item = (kind: string, tab: string) => ({ kind, tab })

describe('workCounts store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('derives both badges from one /me/work response', async () => {
    vi.mocked(myWorkApi.getMyWork).mockResolvedValue({
      items: [item('review', 'needs_you'), item('review', 'done'), item('draft', 'needs_you')],
      counts: { needs_you: 2, waiting: 0, done: 1 }
    } as never)
    const store = useWorkCountsStore()
    await store.fetch()

    expect(myWorkApi.getMyWork).toHaveBeenCalledTimes(1)
    expect(store.needsYou).toBe(2)
    expect(store.review).toBe(1)
  })

  it('keeps the last counts when a refresh fails, and reset clears them', async () => {
    const store = useWorkCountsStore()
    vi.mocked(myWorkApi.getMyWork).mockResolvedValueOnce({
      items: [],
      counts: { needs_you: 4 }
    } as never)
    await store.fetch()
    vi.mocked(myWorkApi.getMyWork).mockRejectedValueOnce(new Error('offline'))
    await store.fetch()
    expect(store.needsYou).toBe(4)

    store.reset()
    expect(store.needsYou).toBe(0)
    expect(store.review).toBe(0)
  })
})
