import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
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
})
