import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('@/api', () => ({
  curationsAPI: { getCurations: vi.fn() }
}))

const routeQuery = vi.hoisted(
  () => ({ q: undefined }) as Record<string, string | string[] | undefined>
)
vi.mock('vue-router', async () => {
  const { reactive } = await import('vue')
  const route = reactive({ query: routeQuery })
  // The table writes its state with router.replace({ query })
  const replace = ({ query }: { query: Record<string, string> }) => {
    for (const k of Object.keys(route.query)) delete route.query[k]
    Object.assign(route.query, query)
  }
  return { useRoute: () => route, useRouter: () => ({ replace }) }
})

vi.mock('@/api/reviewComments', () => ({
  reviewCommentsAPI: { myPendingItemIds: vi.fn() }
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
import { reviewCommentsAPI } from '@/api/reviewComments'
import { useWorkCountsStore } from '@/stores/workCounts'
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

beforeEach(() => {
  for (const k of Object.keys(routeQuery)) delete routeQuery[k]
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

  it('shows a plain empty state when nothing is pending', async () => {
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
    expect(wrapper.text()).toContain('No reviews waiting')
    expect(wrapper.find('.v-alert--variant-tonal.text-success').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('caught up')
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

  it('labels a susceptibility entity in the disease column (W9 monkey)', async () => {
    vi.mocked(curationsAPI.getCurations).mockResolvedValue({
      curations: [row({ relationship_type: 'susceptibility' })],
      total: 1
    } as never)
    const wrapper = mount(ReviewQueueView)
    await flushPromises()
    expect(wrapper.text()).toContain('· Susceptibility')
  })

  it('links a curation row to its AI second view (#530)', async () => {
    vi.mocked(curationsAPI.getCurations).mockResolvedValue({
      curations: [row({})],
      total: 1
    } as never)
    const wrapper = mount(ReviewQueueView)
    await flushPromises()
    const link = wrapper
      .findAllComponents({ name: 'VBtn' })
      .find(b => b.attributes('data-test') === 'open-second-view')
    expect(link?.props('to')).toBe('/scopes/sc1/curations/c1/second-view')
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

    it('shows a 422 as a readable sentence in the request-changes dialog', async () => {
      vi.mocked(curationsAPI.getCurations).mockResolvedValue({ curations: [] } as never)
      vi.mocked(precurationsAPI.getPrecurations).mockResolvedValue({
        precurations: [pre],
        total: 1
      } as never)
      vi.mocked(precurationsAPI.rejectPrecuration).mockRejectedValue({
        response: {
          data: {
            detail: [{ loc: ['body', 'reason'], msg: 'String should have at most 2000 characters' }]
          }
        }
      })
      const wrapper = mount(ReviewQueueView)
      await flushPromises()
      const vm = wrapper.vm as unknown as {
        rejectReason: string
        rejectError: string | null
        openReject: (i: unknown) => void
        confirmReject: () => Promise<void>
      }
      vm.openReject({ id: 'p1', gene_symbol: 'PKD1' })
      vm.rejectReason = 'x'
      await vm.confirmReject()
      expect(vm.rejectError).toBe('Reason: String should have at most 2000 characters.')
    })

    it('approves a precuration and removes it from the queue', async () => {
      const refreshBadge = vi.spyOn(useWorkCountsStore(), 'fetch').mockResolvedValue(undefined)
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

    it('says why an approval created no curation and links the blocking one (#530)', async () => {
      vi.spyOn(useWorkCountsStore(), 'fetch').mockResolvedValue(undefined)
      vi.mocked(curationsAPI.getCurations).mockResolvedValue({ curations: [] } as never)
      vi.mocked(precurationsAPI.getPrecurations).mockResolvedValue({
        precurations: [pre],
        total: 1
      } as never)
      const message = 'Precuration approved; no curation created: Open curation c9 covers'
      vi.mocked(precurationsAPI.approvePrecuration).mockResolvedValue({
        curation_created: false,
        curation_id: 'c9',
        message
      } as never)
      const wrapper = mount(ReviewQueueView, {
        global: {
          stubs: { 'router-link': { props: ['to'], template: '<a :href="to"><slot /></a>' } }
        }
      })
      await flushPromises()
      await wrapper.find('[data-test="approve-precuration"]').trigger('click')
      confirmState.settle(true)
      await flushPromises()
      const notice = wrapper.find('[data-test="approval-notice"]')
      expect(notice.text()).toContain(message.replace('c9', 'of this gene'))
      expect(notice.find('a').attributes('href')).toBe('/scopes/sc1/curations/c9')
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

  describe('filters, pages and labels (#244)', () => {
    const many = (n: number, o: (i: number) => Record<string, unknown> = () => ({})) =>
      Array.from({ length: n }, (_, i) => row({ id: `c${i}`, gene_symbol: `G${i}`, ...o(i) }))

    it('gives the same match count and page count for a disease search', async () => {
      vi.mocked(curationsAPI.getCurations).mockResolvedValue({
        curations: many(25, i => ({
          disease_name: i < 12 ? 'Polycystic kidney' : 'Breast cancer'
        })),
        total: 25
      } as never)
      const wrapper = mount(ReviewQueueView)
      await flushPromises()
      await wrapper.find('input[aria-label="Search table"]').setValue('polycystic')
      await flushPromises()
      expect(wrapper.findAll('[data-testid=review-row]')).toHaveLength(10)
      expect(wrapper.text()).toContain('1-10 of 12')
    })

    it('labels the date as last updated, not submitted', async () => {
      vi.mocked(curationsAPI.getCurations).mockResolvedValue({
        curations: [row({})],
        total: 1
      } as never)
      const wrapper = mount(ReviewQueueView)
      await flushPromises()
      expect(wrapper.text()).toContain('Updated ')
      expect(wrapper.text()).not.toContain('Submitted')
    })

    it('narrows the queue to my assigned reviews with the toggle', async () => {
      vi.mocked(curationsAPI.getCurations).mockResolvedValue({
        curations: many(3),
        total: 3
      } as never)
      vi.mocked(reviewCommentsAPI.myPendingItemIds).mockResolvedValue(['c1'])
      const wrapper = mount(ReviewQueueView)
      await flushPromises()
      expect(wrapper.findAll('[data-testid=review-row]')).toHaveLength(3)
      await wrapper.find('[data-testid=assigned-to-me] input').setValue(true)
      await flushPromises()
      const rows = wrapper.findAll('[data-testid=review-row]')
      expect(rows).toHaveLength(1)
      expect(rows[0]!.text()).toContain('G1')
    })

    it('shows the matching-filters empty state with a clear action', async () => {
      vi.mocked(curationsAPI.getCurations).mockResolvedValue({
        curations: many(2),
        total: 2
      } as never)
      const wrapper = mount(ReviewQueueView)
      await flushPromises()
      await wrapper.find('input[aria-label="Search table"]').setValue('zzz')
      await flushPromises()
      expect(wrapper.text()).toContain('No matching curations')
      const clear = wrapper
        .findAllComponents({ name: 'VBtn' })
        .find(b => b.text() === 'Clear filters')!
      await clear.trigger('click')
      await flushPromises()
      expect(wrapper.findAll('[data-testid=review-row]')).toHaveLength(2)
    })
  })

  it('keeps the scope filter and column sort in the URL and applies them', async () => {
    routeQuery.scope = 'sc2'
    routeQuery.sort = 'gene_symbol'
    vi.mocked(curationsAPI.getCurations).mockResolvedValue({
      curations: [
        row({ id: 'a', gene_symbol: 'ZFP1', scope_id: 'sc2', scope_name: 'Kidney' }),
        row({ id: 'b', gene_symbol: 'ABCA4', scope_id: 'sc2', scope_name: 'Kidney' }),
        row({ id: 'c', gene_symbol: 'BRCA2' })
      ],
      total: 3
    } as never)
    const wrapper = mount(ReviewQueueView)
    await flushPromises()
    const rows = wrapper.findAll('[data-testid=review-row]')
    expect(rows.map(r => r.find('td').text())).toEqual(['ABCA4', 'ZFP1'])
    expect(wrapper.find('[data-testid="filter-scope"]').text()).toContain('Kidney')
  })

  it('lists newest first until a column is sorted', async () => {
    vi.mocked(curationsAPI.getCurations).mockResolvedValue({
      curations: [
        row({ id: 'a', gene_symbol: 'OLD', updated_at: '2024-01-01T00:00:00Z' }),
        row({ id: 'b', gene_symbol: 'NEW', updated_at: '2024-06-01T00:00:00Z' })
      ],
      total: 2
    } as never)
    const wrapper = mount(ReviewQueueView)
    await flushPromises()
    const rows = wrapper.findAll('[data-testid=review-row]')
    expect(rows.map(r => r.find('td').text())).toEqual(['NEW', 'OLD'])
  })

  it('starts with the gene from a My work link in the search', async () => {
    routeQuery.q = 'G1'
    vi.mocked(curationsAPI.getCurations).mockResolvedValue({
      curations: [row({ id: 'a', gene_symbol: 'G1' }), row({ id: 'b', gene_symbol: 'OTHER' })],
      total: 2
    } as never)
    const wrapper = mount(ReviewQueueView)
    await flushPromises()
    routeQuery.q = undefined
    expect(wrapper.findAll('[data-testid=review-row]')).toHaveLength(1)
  })

  it('takes the first value when ?q is repeated', async () => {
    routeQuery.q = ['G1', 'OTHER']
    vi.mocked(curationsAPI.getCurations).mockResolvedValue({
      curations: [row({ id: 'a', gene_symbol: 'G1' }), row({ id: 'b', gene_symbol: 'OTHER' })],
      total: 2
    } as never)
    const wrapper = mount(ReviewQueueView)
    await flushPromises()
    routeQuery.q = undefined
    expect(wrapper.findAll('[data-testid=review-row]')).toHaveLength(1)
  })

  it('applies a second deep link while the queue is open', async () => {
    vi.mocked(curationsAPI.getCurations).mockResolvedValue({
      curations: [row({ id: 'a', gene_symbol: 'G1' }), row({ id: 'b', gene_symbol: 'G2' })],
      total: 2
    } as never)
    const wrapper = mount(ReviewQueueView)
    await flushPromises()
    expect(wrapper.findAll('[data-testid=review-row]')).toHaveLength(2)
    const { useRoute } = await import('vue-router')
    useRoute().query.q = 'G2'
    await flushPromises()
    const rows = wrapper.findAll('[data-testid=review-row]')
    expect(rows).toHaveLength(1)
    expect(rows[0]!.text()).toContain('G2')
    routeQuery.q = undefined
  })
})
