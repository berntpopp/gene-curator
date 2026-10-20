import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { useScopesStore } from '@/stores/scopes'
import ScopeList from '@/views/scope/ScopeList.vue'

const push = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({ push })
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

    const search = wrapper.find('input[type="text"]')
    await search.setValue('cardiac')
    await flushPromises()
    expect(wrapper.text()).toContain('Cardiac Genetics')
    expect(wrapper.text()).not.toContain('Kidney Genetics')
  })
})
