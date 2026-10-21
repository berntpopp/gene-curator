import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useMyWorkStore } from '@/stores/myWork'
import { myWorkApi } from '@/api/myWork'
import type { Schema } from '@/types/api'

vi.mock('@/api/myWork', () => ({ myWorkApi: { getMyWork: vi.fn() } }))
vi.mock('@/services/logService', () => ({
  logService: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }
}))

const item = (tab: Schema<'WorkItem'>['tab']) => ({ tab, verb: 'Do it' }) as Schema<'WorkItem'>

describe('useMyWorkStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('loads items and counts, and filters by tab', async () => {
    vi.mocked(myWorkApi.getMyWork).mockResolvedValue({
      items: [item('needs_you'), item('done')],
      counts: { needs_you: 1, waiting: 0, done: 1 }
    })
    const store = useMyWorkStore()
    await store.fetchMyWork()
    expect(store.byTab('needs_you')).toHaveLength(1)
    expect(store.counts.done).toBe(1)
    expect(store.error).toBeNull()
  })

  it('keeps an error message and stops loading when the request fails', async () => {
    vi.mocked(myWorkApi.getMyWork).mockRejectedValue(new Error('boom'))
    const store = useMyWorkStore()
    await store.fetchMyWork()
    expect(store.error).toBe('boom')
    expect(store.loading).toBe(false)
  })
})
