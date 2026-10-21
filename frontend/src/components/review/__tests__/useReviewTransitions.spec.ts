import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

const transitionCuration = vi.hoisted(() => vi.fn())
vi.mock('@/api', () => ({ workflowAPI: { transitionCuration } }))
vi.mock('@/stores/workCounts', () => ({ useWorkCountsStore: () => ({ fetch: vi.fn() }) }))
vi.mock('@/composables/useLogger', () => ({
  useLogger: () => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() })
}))

import { useReviewTransitions } from '../useReviewTransitions'

describe('useReviewTransitions errors', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    transitionCuration.mockReset()
  })

  it('shows a 422 as a readable sentence, not raw validation JSON', async () => {
    transitionCuration.mockRejectedValue({
      response: {
        data: {
          detail: [
            {
              type: 'string_too_long',
              loc: ['body', 'notes'],
              msg: 'String should have at most 2000 characters'
            }
          ]
        }
      }
    })
    const t = useReviewTransitions(
      () => 'c1',
      async () => {}
    )
    await t.reject('x')
    expect(t.error.value).toBe('Notes: String should have at most 2000 characters.')
  })

  it('keeps a string detail and falls back for a network failure', async () => {
    const t = useReviewTransitions(
      () => 'c1',
      async () => {}
    )
    transitionCuration.mockRejectedValue({ response: { data: { detail: 'Not in review' } } })
    await t.approve('')
    expect(t.error.value).toBe('Not in review')
    transitionCuration.mockRejectedValue({})
    await t.approve('')
    expect(t.error.value).toBe('Request failed')
  })
})
