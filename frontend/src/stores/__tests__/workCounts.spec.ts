import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { myWorkApi } from '@/api/myWork'
import { useWorkCountsStore } from '../workCounts'

vi.mock('@/api/myWork', () => ({ myWorkApi: { getMyWork: vi.fn() } }))

const router = { afterEach: () => () => undefined } as never
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
    store.acquire(router)
    vi.mocked(myWorkApi.getMyWork).mockClear()
    await store.fetch()

    expect(myWorkApi.getMyWork).toHaveBeenCalledTimes(1)
    expect(store.needsYou).toBe(2)
    expect(store.review).toBe(1)
  })

  it('ignores a response that arrives after the last holder released (sign-out)', async () => {
    let resolve!: (v: never) => void
    vi.mocked(myWorkApi.getMyWork).mockReturnValueOnce(new Promise(r => (resolve = r)) as never)
    const store = useWorkCountsStore()
    store.acquire(router)
    store.release()
    resolve({ items: [], counts: { needs_you: 9 } } as never)
    await vi.waitFor(() => expect(myWorkApi.getMyWork).toHaveBeenCalled())
    await Promise.resolve()
    expect(store.needsYou).toBe(0)
  })

  it('keeps the last counts when a refresh fails, and reset clears them', async () => {
    const store = useWorkCountsStore()
    store.acquire(router)
    await vi.waitFor(() => expect(myWorkApi.getMyWork).toHaveBeenCalled())
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
