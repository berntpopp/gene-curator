import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('@/api', () => ({
  curationsAPI: { getCurations: vi.fn() }
}))

vi.mock('@/api/precurations', () => ({
  precurationsAPI: {
    getPrecurations: vi.fn(),
    approvePrecuration: vi.fn(),
    rejectPrecuration: vi.fn()
  }
}))

import { curationsAPI } from '@/api'
import { precurationsAPI } from '@/api/precurations'
import { useWorkflowStore } from '@/stores/workflow'
import { useScopesStore } from '@/stores/scopes'
import { useNotificationsStore } from '@/stores/notifications'
import { confirmState } from '@/composables/useConfirm'
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
    vi.mocked(precurationsAPI.getPrecurations).mockReset()
    vi.mocked(precurationsAPI.getPrecurations).mockResolvedValue({
      precurations: [],
      total: 0
    } as never)
    vi.mocked(precurationsAPI.approvePrecuration).mockReset()
    vi.mocked(precurationsAPI.rejectPrecuration).mockReset()
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
      pending_review: true,
      skip: 0,
      limit: 200
    })
    expect(precurationsAPI.getPrecurations).toHaveBeenCalledWith(
      expect.objectContaining({ pending_review: true })
    )
    expect(wrapper.text()).toContain('All caught up!')
  })

  it('shows the scope display name instead of the machine name', async () => {
    useScopesStore().scopes = [
      { id: 'sc1', name: 'mt2-scope', display_name: 'Cancer Panel' }
    ] as never
    vi.mocked(curationsAPI.getCurations).mockResolvedValue({
      curations: [row({ scope_name: 'mt2-scope' })],
      total: 1
    } as never)
    const wrapper = mount(ReviewQueueView)
    await flushPromises()
    expect(wrapper.text()).toContain('Cancer Panel')
    expect(wrapper.text()).not.toContain('mt2-scope')
  })

  it('shows an error toast when loading fails', async () => {
    vi.mocked(curationsAPI.getCurations).mockRejectedValue(new Error('offline'))
    const notifications = useNotificationsStore()
    const addToast = vi.spyOn(notifications, 'addToast')
    mount(ReviewQueueView)
    await flushPromises()
    expect(addToast).toHaveBeenCalledWith('Failed to load review queue', 'error')
  })

  it('pages through every server-filtered curation instead of capping at 200', async () => {
    const mk = (n: number, from: number) =>
      Array.from({ length: n }, (_, i) => row({ id: `c${from + i}`, gene_symbol: `G${from + i}` }))
    vi.mocked(curationsAPI.getCurations)
      .mockResolvedValueOnce({ curations: mk(200, 0), total: 250 } as never)
      .mockResolvedValueOnce({ curations: mk(50, 200), total: 250 } as never)
    const wrapper = mount(ReviewQueueView)
    await flushPromises()
    expect(curationsAPI.getCurations).toHaveBeenCalledTimes(2)
    expect(vi.mocked(curationsAPI.getCurations).mock.calls[1]![0]).toMatchObject({ skip: 200 })
    expect(wrapper.text()).toContain('250')
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

  describe('precurations in review', () => {
    const pre = {
      id: 'p1',
      gene_id: 'g9',
      gene_symbol: 'PKD1',
      scope_id: 'sc1',
      scope_name: 'Kidney',
      status: 'submitted',
      disease_name: 'ADPKD',
      curator_name: 'Alice',
      created_by: 'alice',
      updated_at: '2024-05-02T00:00:00Z'
    }

    it('lists submitted precurations with a Precuration chip', async () => {
      vi.mocked(curationsAPI.getCurations).mockResolvedValue({ curations: [] } as never)
      vi.mocked(precurationsAPI.getPrecurations).mockResolvedValue({
        precurations: [pre],
        total: 1
      } as never)
      const wrapper = mount(ReviewQueueView)
      await flushPromises()
      expect(precurationsAPI.getPrecurations).toHaveBeenCalledWith(
        expect.objectContaining({ precuration_status: 'submitted' })
      )
      expect(wrapper.text()).toContain('PKD1')
      expect(wrapper.text()).toContain('Precuration')
      expect(wrapper.text()).toContain('Approve')
    })

    it('links a precuration row to its page', async () => {
      vi.mocked(curationsAPI.getCurations).mockResolvedValue({ curations: [] } as never)
      vi.mocked(precurationsAPI.getPrecurations).mockResolvedValue({
        precurations: [pre],
        total: 1
      } as never)
      const wrapper = mount(ReviewQueueView)
      await flushPromises()
      const open = wrapper
        .findAllComponents({ name: 'VBtn' })
        .find(b => b.attributes('data-test') === 'open-precuration')
      expect(open?.props('to')).toBe('/scopes/sc1/precurations/p1')
    })

    it('fetches every page of submitted precurations', async () => {
      vi.mocked(curationsAPI.getCurations).mockResolvedValue({ curations: [] } as never)
      vi.mocked(precurationsAPI.getPrecurations).mockImplementation((async (params: {
        skip: number
      }) => ({
        precurations: [{ ...pre, id: `p${params.skip}`, gene_symbol: `G${params.skip}` }],
        total: 120
      })) as never)
      const wrapper = mount(ReviewQueueView)
      await flushPromises()
      expect(precurationsAPI.getPrecurations).toHaveBeenCalledTimes(3)
      expect(wrapper.text()).toContain('G100')
    })

    it('keeps the request-changes dialog open and shows the API error inline', async () => {
      vi.mocked(curationsAPI.getCurations).mockResolvedValue({ curations: [] } as never)
      vi.mocked(precurationsAPI.getPrecurations).mockResolvedValue({
        precurations: [pre],
        total: 1
      } as never)
      vi.mocked(precurationsAPI.rejectPrecuration).mockRejectedValue({
        response: { data: { detail: 'Not allowed' } }
      })
      const wrapper = mount(ReviewQueueView)
      await flushPromises()
      const vm = wrapper.vm as unknown as {
        rejectReason: string
        rejectError: string | null
        showReject: boolean
        openReject: (i: unknown) => void
        confirmReject: () => Promise<void>
      }
      vm.openReject({ id: 'p1', gene_symbol: 'PKD1' })
      vm.rejectReason = 'x'
      await vm.confirmReject()
      expect(vm.rejectError).toBe('Not allowed')
      expect(vm.showReject).toBe(true)
    })

    it('approves a precuration and removes it from the queue', async () => {
      const refreshBadge = vi
        .spyOn(useWorkflowStore(), 'fetchPendingReviewCount')
        .mockResolvedValue(0)
      vi.mocked(curationsAPI.getCurations).mockResolvedValue({ curations: [] } as never)
      vi.mocked(precurationsAPI.getPrecurations).mockResolvedValue({
        precurations: [pre],
        total: 1
      } as never)
      vi.mocked(precurationsAPI.approvePrecuration).mockResolvedValue({} as never)
      const wrapper = mount(ReviewQueueView)
      await flushPromises()
      await wrapper.find('[data-test="approve-precuration"]').trigger('click')
      confirmState.settle(true)
      await flushPromises()
      expect(precurationsAPI.approvePrecuration).toHaveBeenCalledWith('p1')
      expect(refreshBadge).toHaveBeenCalled()
      expect(wrapper.text()).not.toContain('PKD1')
    })

    it('does nothing when the approval confirmation is declined', async () => {
      vi.mocked(curationsAPI.getCurations).mockResolvedValue({ curations: [] } as never)
      vi.mocked(precurationsAPI.getPrecurations).mockResolvedValue({
        precurations: [pre],
        total: 1
      } as never)
      const wrapper = mount(ReviewQueueView)
      await flushPromises()
      await wrapper.find('[data-test="approve-precuration"]').trigger('click')
      expect(confirmState.open).toBe(true)
      confirmState.settle(false)
      await flushPromises()
      expect(precurationsAPI.approvePrecuration).not.toHaveBeenCalled()
      expect(wrapper.text()).toContain('PKD1')
    })

    it('keeps the precuration and toasts when approval fails', async () => {
      vi.mocked(curationsAPI.getCurations).mockResolvedValue({ curations: [] } as never)
      vi.mocked(precurationsAPI.getPrecurations).mockResolvedValue({
        precurations: [pre],
        total: 1
      } as never)
      vi.mocked(precurationsAPI.approvePrecuration).mockRejectedValue(new Error('4-eyes'))
      const addToast = vi.spyOn(useNotificationsStore(), 'addToast')
      const wrapper = mount(ReviewQueueView)
      await flushPromises()
      await wrapper.find('[data-test="approve-precuration"]').trigger('click')
      confirmState.settle(true)
      await flushPromises()
      expect(addToast).toHaveBeenCalledWith(expect.stringContaining('Failed'), 'error')
      expect(wrapper.text()).toContain('PKD1')
    })

    it('requests changes with the reason typed in the dialog', async () => {
      vi.mocked(curationsAPI.getCurations).mockResolvedValue({ curations: [] } as never)
      vi.mocked(precurationsAPI.getPrecurations).mockResolvedValue({
        precurations: [pre],
        total: 1
      } as never)
      vi.mocked(precurationsAPI.rejectPrecuration).mockResolvedValue({} as never)
      const wrapper = mount(ReviewQueueView, { attachTo: document.body })
      await flushPromises()
      await wrapper.find('[data-test="reject-precuration"]').trigger('click')
      await flushPromises()
      const vm = wrapper.vm as unknown as { rejectReason: string }
      vm.rejectReason = 'Needs MOI'
      await flushPromises()
      await (wrapper.vm as unknown as { confirmReject: () => Promise<void> }).confirmReject()
      expect(precurationsAPI.rejectPrecuration).toHaveBeenCalledWith('p1', { reason: 'Needs MOI' })
      expect(wrapper.text()).not.toContain('PKD1')
      wrapper.unmount()
    })
  })
})

describe('ReviewQueueView status label', () => {
  it('uses the shared status label', async () => {
    setActivePinia(createPinia())
    vi.mocked(curationsAPI.getCurations).mockResolvedValue({
      curations: [row({})],
      total: 1
    } as never)
    vi.mocked(precurationsAPI.getPrecurations).mockResolvedValue({
      precurations: [],
      total: 0
    } as never)
    const wrapper = mount(ReviewQueueView)
    await flushPromises()
    expect(wrapper.text()).toContain('In review')
    expect(wrapper.text()).not.toContain('Awaiting Review')
  })
})
