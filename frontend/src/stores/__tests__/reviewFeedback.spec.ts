import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useReviewFeedbackStore } from '@/stores/reviewFeedback'
import { reviewCommentsAPI } from '@/api/reviewComments'
import { workflowAPI } from '@/api'

vi.mock('@/api/reviewComments', () => ({ reviewCommentsAPI: { list: vi.fn() } }))
vi.mock('@/api', () => ({ workflowAPI: { getCurationWorkflowHistory: vi.fn() } }))

const list = vi.mocked(reviewCommentsAPI.list)
const history = vi.mocked(workflowAPI.getCurationWorkflowHistory)

const query = (o: Record<string, unknown>) =>
  ({
    id: 'q',
    kind: 'query',
    status: 'open',
    item_path: 'summary',
    body: 'Explain',
    author_id: 'bob',
    ...o
  }) as never
const entry = (o: Record<string, unknown>) =>
  ({
    from_stage: 'review',
    to_stage: 'curation',
    notes: 'Please fix',
    executed_at: '2026-10-20T10:00:00Z',
    ...o
  }) as never

describe('review feedback store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    list.mockReset()
    history.mockReset()
  })

  it('returns the latest request-changes note and the reviewers open queries', async () => {
    list.mockResolvedValue([
      query({}),
      query({ id: 'r', status: 'resolved' }),
      query({ id: 'own', author_id: 'alice' }),
      query({ id: 'acc', kind: 'accepted' })
    ])
    history.mockResolvedValue({ entries: [entry({})] } as never)
    const fb = await useReviewFeedbackStore().fetch('c1', 'alice')
    expect(fb.note).toBe('Please fix')
    expect(fb.queries.map(q => q.id)).toEqual(['q'])
    expect(fb.any).toBe(true)
  })

  it('ignores a note that was superseded by a later transition', async () => {
    list.mockResolvedValue([])
    history.mockResolvedValue({
      entries: [
        entry({}),
        entry({
          from_stage: 'curation',
          to_stage: 'review',
          notes: null,
          executed_at: '2026-10-21T10:00:00Z'
        })
      ]
    } as never)
    const fb = await useReviewFeedbackStore().fetch('c1', 'alice')
    expect(fb.note).toBeNull()
    expect(fb.any).toBe(false)
  })

  it('degrades to what loaded when one request fails', async () => {
    list.mockRejectedValue(new Error('403'))
    history.mockResolvedValue({ entries: [entry({})] } as never)
    const fb = await useReviewFeedbackStore().fetch('c1', 'alice')
    expect(fb.note).toBe('Please fix')
    expect(fb.queries).toEqual([])
  })
})
