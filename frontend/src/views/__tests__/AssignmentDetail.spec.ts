import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises, RouterLinkStub } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import AssignmentDetail from '@/views/AssignmentDetail.vue'
import { useAssignmentsStore } from '@/stores/assignments'

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
  beforeEach(() => setActivePinia(createPinia()))

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

  it('links precuration and curation to the scope gene routes', async () => {
    vi.spyOn(useAssignmentsStore(), 'fetchAssignmentById').mockResolvedValue(assignment as never)

    const wrapper = mountView()
    await flushPromises()

    const targets = wrapper
      .findAllComponents({ name: 'VBtn' })
      .map(btn => btn.props('to'))
      .filter(Boolean)
    const params = { scopeId: 's1', geneId: 'g1' }
    expect(targets).toEqual([
      { name: 'gene-precuration-create', params },
      { name: 'gene-curation-create', params }
    ])
    expect(wrapper.findComponent(RouterLinkStub).props('to')).toBe('/genes/g1')
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
