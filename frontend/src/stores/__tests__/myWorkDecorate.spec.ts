import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { flushPromises } from '@vue/test-utils'
import { useMyWorkStore } from '@/stores/myWork'
import { useScopesStore } from '@/stores/scopes'
import { useAuthStore } from '@/stores/auth'
import { useReviewFeedbackStore } from '@/stores/reviewFeedback'
import { myWorkApi } from '@/api/myWork'
import type { Schema } from '@/types/api'

vi.mock('@/api/myWork', () => ({ myWorkApi: { getMyWork: vi.fn() } }))
vi.mock('@/services/logService', () => ({
  logService: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }
}))

const item = (o: Partial<Schema<'WorkItem'>>): Schema<'WorkItem'> => ({
  kind: 'draft',
  tab: 'needs_you',
  verb: 'Continue curation draft',
  item_type: 'curation',
  item_id: 'c1',
  gene_id: 'g1',
  gene_symbol: 'PKD1',
  scope_id: 's1',
  scope_name: 'kidney-genetics',
  link: '/scopes/s1/curations/c1/edit',
  updated_at: null,
  ...o
})

async function load(items: Schema<'WorkItem'>[]) {
  vi.mocked(myWorkApi.getMyWork).mockResolvedValue({ items, counts: {} } as never)
  const store = useMyWorkStore()
  await store.fetchMyWork()
  await flushPromises() // feedback labels arrive after the list
  return store.items
}

describe('My work decoration', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    useScopesStore().scopes = [
      { id: 's1', name: 'kidney-genetics', display_name: 'Kidney genetics' }
    ] as never
    useAuthStore().user = { id: 'alice' } as never
  })

  it('shows the scope display name, not its slug', async () => {
    const [row] = await load([
      item({ kind: 'assignment', verb: 'Start precuration', item_type: 'assignment' })
    ])
    expect(row!.scope_name).toBe('Kidney genetics')
  })

  it('keeps the API name for scopes it does not know', async () => {
    const [row] = await load([
      item({
        scope_id: 'other',
        scope_name: 'other-scope',
        kind: 'assignment',
        item_type: 'assignment'
      })
    ])
    expect(row!.scope_name).toBe('other-scope')
  })

  it('sends a precuration review to the review queue, where the review actions are', async () => {
    const [row] = await load([
      item({
        kind: 'review',
        item_type: 'precuration',
        verb: 'Review precuration',
        link: '/scopes/s1/precurations/p1',
        gene_symbol: 'BRCA1'
      })
    ])
    expect(row!.link).toBe('/review-queue?q=BRCA1')
  })

  it('leaves curation review links on the curation page (it has the review actions)', async () => {
    const [row] = await load([
      item({ kind: 'review', verb: 'Review curation', link: '/scopes/s1/curations/c1' })
    ])
    expect(row!.link).toBe('/scopes/s1/curations/c1')
  })

  it('relabels a draft curation that has reviewer feedback', async () => {
    vi.spyOn(useReviewFeedbackStore(), 'fetch').mockResolvedValue({
      note: 'Fix',
      queries: [],
      any: true
    })
    const [row] = await load([item({})])
    expect(row!.verb).toBe('Address review feedback')
  })

  it('keeps the label without feedback, or when the feedback lookup fails', async () => {
    const fetch = vi.spyOn(useReviewFeedbackStore(), 'fetch')
    fetch.mockResolvedValueOnce({ note: null, queries: [], any: false })
    expect((await load([item({})]))[0]!.verb).toBe('Continue curation draft')
    fetch.mockRejectedValueOnce(new Error('x'))
    expect((await load([item({})]))[0]!.verb).toBe('Continue curation draft')
  })

  it('renders the list before the feedback labels resolve', async () => {
    let release!: () => void
    vi.spyOn(useReviewFeedbackStore(), 'fetch').mockImplementation(
      () => new Promise(r => (release = () => r({ note: 'Fix', queries: [], any: true })))
    )
    vi.mocked(myWorkApi.getMyWork).mockResolvedValue({ items: [item({})], counts: {} } as never)
    const store = useMyWorkStore()
    await store.fetchMyWork()
    expect(store.loading).toBe(false)
    expect(store.items[0]!.verb).toBe('Continue curation draft')
    release()
    await flushPromises()
    expect(store.items[0]!.verb).toBe('Address review feedback')
  })

  it('looks up at most 4 drafts at a time', async () => {
    let running = 0
    let peak = 0
    vi.spyOn(useReviewFeedbackStore(), 'fetch').mockImplementation(async () => {
      peak = Math.max(peak, ++running)
      await new Promise(r => setTimeout(r, 1))
      running--
      return { note: null, queries: [], any: false }
    })
    await load(Array.from({ length: 10 }, (_, i) => item({ item_id: `c${i}` })))
    await vi.waitFor(() => expect(running).toBe(0))
    expect(peak).toBe(4)
  })

  it('ignores labels that arrive after a newer load replaced the list', async () => {
    let release!: () => void
    vi.spyOn(useReviewFeedbackStore(), 'fetch').mockImplementation(
      () => new Promise(r => (release = () => r({ note: 'Fix', queries: [], any: true })))
    )
    vi.mocked(myWorkApi.getMyWork).mockResolvedValue({ items: [item({})], counts: {} } as never)
    const store = useMyWorkStore()
    await store.fetchMyWork()
    const stale = release
    vi.mocked(myWorkApi.getMyWork).mockResolvedValue({
      items: [item({ item_id: 'c2' })],
      counts: {}
    } as never)
    await store.fetchMyWork()
    stale()
    await flushPromises()
    expect(store.items[0]!.item_id).toBe('c2')
    expect(store.items[0]!.verb).toBe('Continue curation draft')
  })
})
