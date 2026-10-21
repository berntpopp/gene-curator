import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises, RouterLinkStub } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import GeneAssignments from '@/views/GeneAssignments.vue'
import { useAssignmentsStore } from '@/stores/assignments'
import { useAuthStore } from '@/stores/auth'
import { useScopesStore } from '@/stores/scopes'

const mine = {
  id: 'a1',
  gene_id: 'g1',
  gene_symbol: 'HNF1B',
  gene_hgnc_id: 'HGNC:11630',
  scope_id: 's1',
  scope_name: 'kidney',
  priority: 'high',
  assigned_at: '2026-01-01T00:00:00Z',
  has_active_work: true
}

function setup(user = { id: 'u1', role: 'user' }) {
  setActivePinia(createPinia())
  useAuthStore().user = user as never
  useScopesStore().scopes = [{ id: 's1', name: 'kidney', display_name: 'Kidney Genetics' }] as never
  vi.spyOn(useScopesStore(), 'fetchUserScopes').mockResolvedValue(undefined as never)
  return useAssignmentsStore()
}

const mountView = () =>
  mount(GeneAssignments, {
    global: {
      stubs: {
        RouterLink: RouterLinkStub,
        'router-link': RouterLinkStub,
        GeneAssignmentManager: { template: '<div class="manager-stub" />' }
      }
    }
  })

describe('GeneAssignments (My Work)', () => {
  beforeEach(() => vi.clearAllMocks())

  it("lists only the current user's assignments via the curator endpoint", async () => {
    const store = setup()
    const fetch = vi.spyOn(store, 'fetchCuratorAssignments').mockResolvedValue([mine] as never)
    const wrapper = mountView()
    await flushPromises()

    expect(fetch).toHaveBeenCalledWith('u1')
    expect(wrapper.text()).toContain('HNF1B')
    expect(wrapper.text()).toContain('Kidney Genetics')
    const links = wrapper.findAllComponents(RouterLinkStub).map(l => l.props('to'))
    expect(links).toContain('/assignments/a1')
    expect(wrapper.find('.manager-stub').exists()).toBe(false)
  })

  it('shows an empty state that links to the review queue', async () => {
    const store = setup()
    vi.spyOn(store, 'fetchCuratorAssignments').mockResolvedValue([])
    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.text()).toContain('No assignments')
    expect(wrapper.findAllComponents(RouterLinkStub).map(l => l.props('to'))).toContain(
      '/review-queue'
    )
  })

  it('shows an error with retry instead of the empty state when loading fails', async () => {
    const store = setup()
    const fetch = vi
      .spyOn(store, 'fetchCuratorAssignments')
      .mockImplementationOnce(async () => {
        store.error = 'Request failed'
        throw new Error('500')
      })
      .mockResolvedValueOnce([mine] as never)
    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.text()).toContain('Failed to load your assignments')
    expect(wrapper.text()).not.toContain('No assignments')
    await wrapper.find('button.retry').trigger('click')
    await flushPromises()
    expect(fetch).toHaveBeenCalledTimes(2)
    expect(wrapper.text()).toContain('HNF1B')
  })

  it('shows the all-assignments manager to admins only', async () => {
    const store = setup({ id: 'root', role: 'admin' })
    vi.spyOn(store, 'fetchCuratorAssignments').mockResolvedValue([])
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.text()).toContain('All assignments')
    expect(wrapper.find('.manager-stub').exists()).toBe(true)
  })
  it('shows the all-assignments manager to scope admins', async () => {
    const store = setup()
    useScopesStore().scopes = [{ id: 's1', name: 'k', user_role: 'admin' }] as never
    vi.spyOn(store, 'fetchCuratorAssignments').mockResolvedValue([])
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.find('.manager-stub').exists()).toBe(true)
  })

  it('does not blank My Work when only the shared store error is set', async () => {
    const store = setup()
    vi.spyOn(store, 'fetchCuratorAssignments').mockResolvedValue([mine] as never)
    store.error = 'manager failed'
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.text()).toContain('HNF1B')
    expect(wrapper.text()).not.toContain('manager failed')
  })
})
