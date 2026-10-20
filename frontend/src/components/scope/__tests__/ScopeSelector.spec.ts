/**
 * ScopeSelector Tests
 *
 * Loads the user's scopes on mount, shows the current scope, and navigates on
 * select or create. Handlers are reached through the component instance.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createMemoryHistory, type Router } from 'vue-router'
import { useScopesStore } from '@/stores/scopes'
import { logService } from '@/services/logService'
import ScopeSelector from '../ScopeSelector.vue'
import { stubVisualViewport } from './overlayStubs'

vi.mock('@/services/logService', () => ({
  logService: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }
}))

interface SelectorInternals {
  selectScope: (scope: {
    id: string
    name: string
    display_name: string
    is_public: boolean
    user_role: string
  }) => void
  createScope: () => void
}

const component = { render: () => null }

const scopeA = {
  id: 'scope-a',
  name: 'kidney',
  display_name: 'Kidney',
  is_public: true,
  user_role: 'admin'
}

describe('ScopeSelector', () => {
  let pinia: ReturnType<typeof createPinia>
  let router: Router

  beforeEach(async () => {
    stubVisualViewport()
    pinia = createPinia()
    setActivePinia(pinia)
    router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/', name: 'Home', component },
        { path: '/scopes/:scopeId', name: 'scope-dashboard', component },
        { path: '/scopes/new', name: 'scope-create', component }
      ]
    })
    await router.push('/')
    await router.isReady()
    vi.mocked(logService.error).mockClear()
  })

  async function mountSelector(options: { fetchError?: Error; attachTo?: HTMLElement } = {}) {
    const store = useScopesStore()
    const fetchSpy = vi.spyOn(store, 'fetchUserScopes')
    if (options.fetchError) fetchSpy.mockRejectedValueOnce(options.fetchError)
    else fetchSpy.mockResolvedValue(undefined as never)
    const wrapper = mount(ScopeSelector, {
      attachTo: options.attachTo,
      global: { plugins: [pinia, router] }
    })
    await flushPromises()
    return { wrapper, store, fetchSpy, vm: wrapper.vm as unknown as SelectorInternals }
  }

  it('loads the user scopes on mount and labels the button with the current scope', async () => {
    const { wrapper, store, fetchSpy } = await mountSelector()
    expect(fetchSpy).toHaveBeenCalledTimes(1)
    expect(wrapper.text()).toContain('Select Scope')

    store.currentScope = scopeA as never
    await flushPromises()
    expect(wrapper.text()).toContain('Kidney')
  })

  it('reports a failed scope load without throwing', async () => {
    await mountSelector({ fetchError: new Error('offline') })

    expect(logService.error).toHaveBeenCalledWith(
      'Failed to load scopes',
      expect.objectContaining({ error: 'offline' })
    )
  })

  it('selects a scope in the store and opens its dashboard', async () => {
    const { store, vm } = await mountSelector()
    const setCurrent = vi.spyOn(store, 'setCurrentScope')
    const push = vi.spyOn(router, 'push')

    vm.selectScope(scopeA)

    expect(setCurrent).toHaveBeenCalledWith(scopeA)
    expect(push).toHaveBeenCalledWith({ name: 'scope-dashboard', params: { scopeId: 'scope-a' } })
  })

  it('opens the create page from the new-scope action', async () => {
    const { vm } = await mountSelector()
    const push = vi.spyOn(router, 'push')

    vm.createScope()

    expect(push).toHaveBeenCalledWith({ name: 'scope-create' })
  })

  it('lists the user scopes in the opened menu and navigates when one is clicked', async () => {
    const store = useScopesStore()
    store.scopes = [
      scopeA,
      { ...scopeA, id: 'scope-b', display_name: 'Liver', user_role: 'viewer' }
    ] as never
    const { wrapper } = await mountSelector({ attachTo: document.body })
    const push = vi.spyOn(router, 'push')
    const setCurrent = vi.spyOn(store, 'setCurrentScope')

    await wrapper.find('button').trigger('click')
    await flushPromises()
    const items = Array.from(document.querySelectorAll('.v-list-item'))
    const liver = items.find(el => el.textContent?.includes('Liver')) as HTMLElement | undefined
    expect(document.body.textContent).toContain('My Scopes')
    expect(liver).toBeDefined()
    liver?.click()
    await flushPromises()

    expect(setCurrent).toHaveBeenCalledWith(expect.objectContaining({ id: 'scope-b' }))
    expect(push).toHaveBeenCalledWith({ name: 'scope-dashboard', params: { scopeId: 'scope-b' } })
    wrapper.unmount()
  })

  it('shows the empty state and opens the create page from the menu', async () => {
    const store = useScopesStore()
    store.scopes = [] as never
    const { wrapper } = await mountSelector({ attachTo: document.body })
    const push = vi.spyOn(router, 'push')

    await wrapper.find('button').trigger('click')
    await flushPromises()
    expect(document.body.textContent).toContain('No scopes available')

    const create = Array.from(document.querySelectorAll('.v-list-item'))
      .filter(el => el.textContent?.includes('Create New Scope'))
      .pop() as HTMLElement | undefined
    create?.click()
    await flushPromises()

    expect(push).toHaveBeenCalledWith({ name: 'scope-create' })
    wrapper.unmount()
  })
})
