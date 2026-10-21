import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { useScopesStore } from '@/stores/scopes'
import ScopeList from '@/views/scope/ScopeList.vue'

const push = vi.fn()
const replace = vi.fn()
const route = vi.hoisted(() => ({ query: {} as Record<string, string> }))
vi.mock('vue-router', () => ({
  useRouter: () => ({ push, replace }),
  useRoute: () => route
}))

const scope = (overrides: Record<string, unknown>) => ({
  id: 's1',
  name: 'kidney',
  display_name: 'Kidney Genetics',
  is_public: true,
  is_active: true,
  created_at: '2024-01-01T00:00:00Z',
  stats: null,
  ...overrides
})

const mountView = () => mount(ScopeList, { global: { stubs: { RouterLink: true } } })

describe('ScopeList view', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    push.mockClear()
    replace.mockClear()
    route.query = {}
  })

  it('loads the user scopes on mount', async () => {
    const store = useScopesStore()
    store.fetchUserScopes = vi.fn().mockResolvedValue(undefined) as never
    mountView()
    await flushPromises()
    expect(store.fetchUserScopes).toHaveBeenCalledTimes(1)
  })

  it('shows the empty state when there are no scopes', async () => {
    const store = useScopesStore()
    store.fetchUserScopes = vi.fn().mockResolvedValue(undefined) as never
    store.scopes = []
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.text()).toContain('No scopes found')
  })

  it('shows a progress bar while loading', () => {
    const store = useScopesStore()
    store.fetchUserScopes = vi.fn(() => new Promise(() => {})) as never
    store.loading = true
    const wrapper = mountView()
    expect(wrapper.find('.v-progress-linear').exists()).toBe(true)
  })

  it('lists scopes and filters them by search text', async () => {
    const store = useScopesStore()
    store.fetchUserScopes = vi.fn().mockResolvedValue(undefined) as never
    store.scopes = [
      scope({ id: 's1', display_name: 'Kidney Genetics' }),
      scope({ id: 's2', name: 'cardiac', display_name: 'Cardiac Genetics' })
    ] as never
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.text()).toContain('Kidney Genetics')
    expect(wrapper.text()).toContain('Cardiac Genetics')

    route.query = { q: 'cardiac' }
    const filtered = mountView()
    await flushPromises()
    expect(filtered.text()).toContain('Cardiac Genetics')
    expect(filtered.text()).not.toContain('Kidney Genetics')
  })

  it('shows the user role per row as a table, with search as the only control', async () => {
    const store = useScopesStore()
    store.fetchUserScopes = vi.fn().mockResolvedValue(undefined) as never
    store.scopes = [
      scope({ id: 's1', user_role: 'reviewer', stats: { total_genes: 12, member_count: 4 } }),
      scope({ id: 's2', display_name: 'Public only', user_role: null })
    ] as never
    const wrapper = mountView()
    await flushPromises()

    const rows = wrapper.findAll('tbody tr')
    expect(rows).toHaveLength(2)
    expect(rows[0]!.text()).toContain('Reviewer')
    expect(rows[0]!.text()).toContain('12')
    expect(rows[1]!.text()).not.toMatch(/Reviewer|Curator|Viewer|Admin/)
    const headers = wrapper.findAll('th').map(h => h.text())
    expect(headers).toEqual(expect.arrayContaining(['Your role', 'Genes', 'Members']))
    expect(wrapper.text()).not.toMatch(/Visibility|Sort by/)
  })

  it('opens a scope from its name and offers New scope with the admin hint', async () => {
    const store = useScopesStore()
    store.fetchUserScopes = vi.fn().mockResolvedValue(undefined) as never
    store.scopes = [scope({ id: 's1' })] as never
    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('tbody button.scope-link').trigger('click')
    expect(push).toHaveBeenCalledWith({ name: 'scope-dashboard', params: { scopeId: 's1' } })

    expect(wrapper.text()).toContain('New scope')
    expect(wrapper.text()).toContain('You become the scope admin')
    await wrapper
      .findAll('button')
      .find(b => b.text() === 'New scope')!
      .trigger('click')
    expect(push).toHaveBeenCalledWith({ name: 'scope-create' })
  })

  it('sorts by the chosen column from the URL', async () => {
    const store = useScopesStore()
    store.fetchUserScopes = vi.fn().mockResolvedValue(undefined) as never
    store.scopes = [
      scope({ id: 's1', display_name: 'A', stats: { total_genes: 1 } }),
      scope({ id: 's2', display_name: 'B', stats: { total_genes: 9 } })
    ] as never
    route.query = { sort: 'genes', order: 'desc' }
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.findAll('tbody tr')[0]!.text()).toContain('B')
  })
})
