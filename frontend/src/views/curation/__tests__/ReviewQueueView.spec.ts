import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('@/api', () => ({
  curationsAPI: { getCurations: vi.fn() }
}))

import { curationsAPI } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { useNotificationsStore } from '@/stores/notifications'
import ReviewQueueView from '@/views/curation/ReviewQueueView.vue'

const row = (overrides: Record<string, unknown>) => ({
  id: 'c1',
  gene_id: 'g1',
  gene_symbol: 'BRCA1',
  disease_name: 'Breast cancer',
  scope_id: 'sc1',
  scope_name: 'Cancer',
  curator_name: 'Grace',
  status: 'in_review',
  computed_scores: { total_score: 10 },
  computed_verdict: 'Strong',
  updated_at: '2024-05-01T00:00:00Z',
  created_by: 'someone-else',
  ...overrides
})

describe('ReviewQueueView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.mocked(curationsAPI.getCurations).mockReset()
  })

  it('shows skeleton loaders while the queue loads', () => {
    vi.mocked(curationsAPI.getCurations).mockReturnValue(new Promise(() => {}))
    const wrapper = mount(ReviewQueueView)
    expect(wrapper.findAll('.v-skeleton-loader').length).toBe(3)
  })

  it('shows the all-caught-up empty state when nothing is pending', async () => {
    vi.mocked(curationsAPI.getCurations).mockResolvedValue({ curations: [] } as never)
    const wrapper = mount(ReviewQueueView)
    await flushPromises()
    expect(curationsAPI.getCurations).toHaveBeenCalledWith({
      curation_status: 'in_review',
      limit: 200
    })
    expect(wrapper.text()).toContain('All caught up!')
  })

  it('shows an error toast when loading fails', async () => {
    vi.mocked(curationsAPI.getCurations).mockRejectedValue(new Error('offline'))
    const notifications = useNotificationsStore()
    const addToast = vi.spyOn(notifications, 'addToast')
    mount(ReviewQueueView)
    await flushPromises()
    expect(addToast).toHaveBeenCalledWith('Failed to load review queue', 'error')
  })

  it('hides curations created by the current user (4-eyes principle)', async () => {
    useAuthStore().user = { id: 'me', role: 'curator' } as never
    vi.mocked(curationsAPI.getCurations).mockResolvedValue({
      curations: [
        row({ id: 'c1', gene_symbol: 'BRCA1', created_by: 'me' }),
        row({ id: 'c2', gene_symbol: 'TP53', created_by: 'other' })
      ]
    } as never)
    const wrapper = mount(ReviewQueueView)
    await flushPromises()
    expect(wrapper.text()).toContain('TP53')
    expect(wrapper.text()).not.toContain('BRCA1')
  })

  it('shows no-match text when the search excludes everything', async () => {
    vi.mocked(curationsAPI.getCurations).mockResolvedValue({
      curations: [row({ gene_symbol: 'TP53' })]
    } as never)
    const wrapper = mount(ReviewQueueView)
    await flushPromises()
    ;(wrapper.vm as unknown as { searchQuery: string }).searchQuery = 'zzz-no-match'
    await flushPromises()
    expect(wrapper.text()).toContain('No matching curations')
  })
})
