import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises, RouterLinkStub } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import AssignmentDetail from '@/views/AssignmentDetail.vue'
import { useAssignmentsStore } from '@/stores/assignments'
import { precurationsAPI, curationsAPI } from '@/api'

vi.mock('@/api', () => ({
  precurationsAPI: { getPrecurations: vi.fn() },
  curationsAPI: { getCurations: vi.fn() }
}))

const { routeState } = vi.hoisted(() => ({ routeState: { params: { id: 'a1' } } }))

vi.mock('vue-router', () => ({
  useRoute: () => routeState,
  useRouter: () => ({ push: vi.fn(), back: vi.fn() })
}))

const assignment = {
  id: 'a1',
  gene_id: 'g1',
  scope_id: 's1',
  is_active: true,
  priority: 'high',
  due_date: null,
  assignment_notes: 'Prioritise',
  assigned_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  gene_symbol: 'HNF1B',
  gene_hgnc_id: 'HGNC:11630',
  scope_name: 'kidney',
  scope_display_name: 'Kidney Genetics',
  curator_name: 'Ada'
}

function mountView() {
  return mount(AssignmentDetail, {
    global: { stubs: { RouterLink: RouterLinkStub, 'router-link': RouterLinkStub } }
  })
}

describe('AssignmentDetail', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.mocked(precurationsAPI.getPrecurations).mockResolvedValue({ precurations: [] } as never)
    vi.mocked(curationsAPI.getCurations).mockResolvedValue({ curations: [] } as never)
  })

  it('loads the assignment by route id and shows its details', async () => {
    const store = useAssignmentsStore()
    const fetch = vi.spyOn(store, 'fetchAssignmentById').mockResolvedValue(assignment as never)

    const wrapper = mountView()
    await flushPromises()

    expect(fetch).toHaveBeenCalledWith('a1')
    const text = wrapper.text()
    expect(text).toContain('HNF1B')
    expect(text).toContain('Kidney Genetics')
    expect(text).toContain('Ada')
    expect(text).toContain('No due date')
    expect(text).toContain('Prioritise')
    expect(text).toContain('Active')
  })

  const actions = (wrapper: ReturnType<typeof mountView>) =>
    wrapper
      .findAllComponents({ name: 'VBtn' })
      .filter(btn => btn.props('to'))
      .map(btn => ({ text: btn.text(), to: btn.props('to') }))

  it('offers to start precuration when nothing exists yet', async () => {
    vi.spyOn(useAssignmentsStore(), 'fetchAssignmentById').mockResolvedValue(assignment as never)
    const wrapper = mountView()
    await flushPromises()

    expect(vi.mocked(curationsAPI.getCurations)).toHaveBeenCalledWith(
      expect.objectContaining({ scope_id: 's1', gene_id: 'g1' })
    )
    expect(actions(wrapper)).toEqual([
      {
        text: 'Start precuration',
        to: { name: 'gene-precuration-create', params: { scopeId: 's1', geneId: 'g1' } }
      }
    ])
    expect(wrapper.text()).toContain('Assigned')
    expect(wrapper.findComponent(RouterLinkStub).props('to')).toBe('/genes/g1')
  })

  it('offers to continue an existing precuration', async () => {
    vi.spyOn(useAssignmentsStore(), 'fetchAssignmentById').mockResolvedValue(assignment as never)
    vi.mocked(precurationsAPI.getPrecurations).mockResolvedValue({
      precurations: [
        { id: 'p1', gene_id: 'g1', status: 'draft', updated_at: '2026-01-01T00:00:00Z' }
      ]
    } as never)
    const wrapper = mountView()
    await flushPromises()

    expect(actions(wrapper).map(a => a.text)).toEqual(['Continue precuration'])
    expect(wrapper.text()).toContain('draft')
  })

  it('offers only "Open curation" when the best curation is active', async () => {
    vi.spyOn(useAssignmentsStore(), 'fetchAssignmentById').mockResolvedValue(assignment as never)
    vi.mocked(curationsAPI.getCurations).mockResolvedValue({
      curations: [
        { id: 'c1', gene_id: 'g1', status: 'draft', updated_at: '2026-02-01T00:00:00Z' },
        { id: 'c2', gene_id: 'g1', status: 'active', updated_at: '2026-01-01T00:00:00Z' }
      ]
    } as never)
    const wrapper = mountView()
    await flushPromises()

    expect(actions(wrapper)).toEqual([
      {
        text: 'Open curation',
        to: { name: 'curation-detail', params: { scopeId: 's1', curationId: 'c2' } }
      }
    ])
    expect(wrapper.text()).not.toContain('Start')
  })

  it('shows an error with retry when loading fails', async () => {
    const fetch = vi
      .spyOn(useAssignmentsStore(), 'fetchAssignmentById')
      .mockRejectedValueOnce(new Error('boom'))
      .mockResolvedValueOnce(assignment as never)

    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.text()).toContain('Failed to load assignment')

    await wrapper.find('button').trigger('click')
    await flushPromises()
    expect(fetch).toHaveBeenCalledTimes(2)
    expect(wrapper.text()).toContain('HNF1B')
  })
})
