/**
 * MainNavigation Tests
 *
 * Route-driven main menu: simple items, the Curation and Curation Setup
 * dropdowns, role/auth filtering, the review-queue badge and its refresh timer.
 * Internals are reached through the component instance.
 */
import { precurationsAPI } from '@/api'
import { usePrecurationsStore } from '@/stores/precurations'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { defineComponent, h, ref } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createMemoryHistory, type Router } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useWorkflowStore } from '@/stores/workflow'
import MainNavigation from '../MainNavigation.vue'

vi.mock('@/services/logService', () => ({
  logService: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }
}))

const display = vi.hoisted(() => ({ mdAndUp: { value: true } }))
vi.mock('vuetify', async importOriginal => ({
  ...(await importOriginal<typeof import('vuetify')>()),
  useDisplay: () => display
}))

interface Item {
  name: string
  label: string
  badge?: number | null
}

interface MainNavInternals {
  simpleItems: Item[]
  curationItems: Item[]
  curationSetupItems: Item[]
  pendingReviewCount: number
}

const component = { render: () => null }

function makeRouter(): Router {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'Home', component },
      { path: '/profile', name: 'UserProfile', component },
      {
        path: '/dashboard',
        name: 'Dashboard',
        component,
        meta: { showInMainMenu: true, label: 'Dashboard', icon: 'mdi-home', order: 1 }
      },
      {
        path: '/login',
        name: 'Login',
        component,
        meta: { showInMainMenu: true, requiresGuest: true, label: 'Login', order: 5 }
      },
      {
        path: '/curations',
        name: 'Curations',
        component,
        meta: { showInDropdown: 'curation', requiresAuth: true, label: 'Curations', order: 1 }
      },
      {
        path: '/review',
        name: 'review-queue',
        component,
        meta: {
          showInMainMenu: true,
          requiresAuth: true,
          label: 'Review queue',
          order: 2
        }
      },
      {
        path: '/schemas',
        name: 'Schemas',
        component,
        meta: {
          showInDropdown: 'curationSetup',
          requiredRoles: ['admin'],
          label: 'Schemas',
          order: 1
        }
      },
      {
        path: '/titled',
        name: 'Titled',
        component,
        meta: { showInMainMenu: true, requiresAuth: true, title: 'Titled page' }
      }
    ]
  })
}

describe('MainNavigation', () => {
  let pinia: ReturnType<typeof createPinia>
  let router: Router

  beforeEach(async () => {
    vi.useRealTimers()
    pinia = createPinia()
    setActivePinia(pinia)
    router = makeRouter()
    await router.push('/')
    await router.isReady()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  async function mountNav(user: { role: string } | null) {
    const auth = useAuthStore()
    auth.isAuthenticated = user !== null
    auth.user = user as typeof auth.user
    const workflow = useWorkflowStore()
    const fetchSpy = vi.spyOn(workflow, 'fetchPendingReviewCount').mockImplementation(async () => {
      workflow.pendingReviewCount = 3
      return 3
    })
    const wrapper = mount(MainNavigation, { global: { plugins: [pinia, router] } })
    await flushPromises()
    return { wrapper, auth, fetchSpy, vm: wrapper.vm as unknown as MainNavInternals }
  }

  it('shows guest-only items to guests and hides role-restricted ones', async () => {
    const { vm } = await mountNav(null)

    expect(vm.simpleItems.map(i => i.label)).toEqual(['Dashboard', 'Login'])
    expect(vm.curationItems).toEqual([])
    expect(vm.curationSetupItems).toEqual([])
  })

  it('shows curation items to any signed-in user and hides guest-only links', async () => {
    const { vm } = await mountNav({ role: 'user' })

    expect(vm.simpleItems.map(i => i.label)).toEqual(['Dashboard', 'Review queue', 'Titled page'])
    expect(vm.curationItems.map(i => i.label)).toEqual(['Curations'])
  })

  it('shows the review queue and its pending badge to any signed-in user', async () => {
    const { wrapper, vm, fetchSpy } = await mountNav({ role: 'user' })

    expect(vm.simpleItems.find(i => i.name === 'review-queue')?.badge).toBe(3)
    expect(fetchSpy).toHaveBeenCalled()
    expect(vm.pendingReviewCount).toBe(3)
    await flushPromises()
    expect(wrapper.find('.main-navigation .v-badge').text()).toContain('3')
    expect(wrapper.text()).toContain('Curation')
  })

  it('shows the setup dropdown only to admins', async () => {
    const curator = await mountNav({ role: 'user' })
    expect(curator.vm.curationSetupItems).toEqual([])

    const admin = await mountNav({ role: 'admin' })
    expect(admin.vm.curationSetupItems.map(i => i.label)).toEqual(['Schemas'])
  })

  it('refreshes the badge every minute and stops when unmounted', async () => {
    vi.useFakeTimers()
    const { wrapper, fetchSpy } = await mountNav({ role: 'user' })
    expect(fetchSpy).toHaveBeenCalledTimes(1)

    await vi.advanceTimersByTimeAsync(60000)
    expect(fetchSpy).toHaveBeenCalledTimes(2)

    wrapper.unmount()
    await vi.advanceTimersByTimeAsync(60000)
    expect(fetchSpy).toHaveBeenCalledTimes(2)
  })

  it('refreshes the badge after navigation and after a precuration review action', async () => {
    const { fetchSpy } = await mountNav({ role: 'user' })
    fetchSpy.mockClear()

    await router.push('/profile')
    await flushPromises()
    expect(fetchSpy).toHaveBeenCalledTimes(1)

    const precurations = usePrecurationsStore()
    vi.spyOn(precurationsAPI, 'approvePrecuration').mockResolvedValue({} as never)
    await precurations.approvePrecuration('p1')
    await flushPromises()
    expect(fetchSpy).toHaveBeenCalledTimes(2)
  })

  it('skips the poll while the tab is hidden', async () => {
    vi.useFakeTimers()
    const { fetchSpy } = await mountNav({ role: 'user' })
    const state = vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('hidden')

    await vi.advanceTimersByTimeAsync(120000)
    expect(fetchSpy).toHaveBeenCalledTimes(1)

    state.mockReturnValue('visible')
    document.dispatchEvent(new Event('visibilitychange'))
    await flushPromises()
    expect(fetchSpy).toHaveBeenCalledTimes(2)
    state.mockRestore()
  })

  it('stops listening for visibility changes after unmount', async () => {
    const { wrapper, fetchSpy } = await mountNav({ role: 'user' })
    wrapper.unmount()
    document.dispatchEvent(new Event('visibilitychange'))
    await flushPromises()
    expect(fetchSpy).toHaveBeenCalledTimes(1)
  })

  it('clears the badge on sign-out and restarts refreshing on sign-in', async () => {
    const { auth, fetchSpy, vm } = await mountNav({ role: 'user' })
    expect(vm.pendingReviewCount).toBe(3)

    auth.isAuthenticated = false
    await flushPromises()
    expect(vm.pendingReviewCount).toBe(0)

    auth.isAuthenticated = true
    await flushPromises()
    expect(fetchSpy).toHaveBeenCalledTimes(2)
  })

  it('keeps navigation working when the badge refresh fails', async () => {
    const auth = useAuthStore()
    auth.isAuthenticated = true
    auth.user = { role: 'user' } as unknown as typeof auth.user
    const workflow = useWorkflowStore()
    vi.spyOn(workflow, 'fetchPendingReviewCount').mockRejectedValue(new Error('down'))

    const wrapper = mount(MainNavigation, { global: { plugins: [pinia, router] } })
    await flushPromises()

    expect((wrapper.vm as unknown as MainNavInternals).pendingReviewCount).toBe(0)
  })

  it('opens the curation dropdown and renders its items as router links', async () => {
    const auth = useAuthStore()
    auth.isAuthenticated = true
    auth.user = { role: 'user' } as unknown as typeof auth.user
    vi.spyOn(useWorkflowStore(), 'fetchPendingReviewCount').mockResolvedValue(0)
    const wrapper = mount(MainNavigation, {
      global: { plugins: [pinia, router] },
      attachTo: document.body
    })
    await flushPromises()

    const trigger = wrapper.findAll('button').find(b => b.text().includes('Curation'))
    await trigger?.trigger('click')
    await flushPromises()
    const option = Array.from(document.querySelectorAll('.v-list-item'))
      .filter(el => el.textContent?.includes('Curations'))
      .pop() as HTMLElement | undefined
    // The item is a router link; navigation itself is covered by the router
    expect(option?.getAttribute('href')).toBe('/curations')
    wrapper.unmount()
  })

  describe('below md (mobile)', () => {
    // v-navigation-drawer needs a Vuetify layout; render it as a plain container instead.
    const drawerStub = defineComponent({
      setup(_, { slots }) {
        return () => h('aside', { class: 'drawer' }, [slots.default?.(), slots.append?.()])
      }
    })

    async function mountMobile(user: { role: string } | null) {
      display.mdAndUp = ref(false)
      const auth = useAuthStore()
      auth.isAuthenticated = user !== null
      auth.user = user as typeof auth.user
      const workflow = useWorkflowStore()
      vi.spyOn(workflow, 'fetchPendingReviewCount').mockImplementation(async () => {
        workflow.pendingReviewCount = 2
        return 2
      })
      const wrapper = mount(MainNavigation, {
        global: { plugins: [pinia, router], stubs: { VNavigationDrawer: drawerStub } }
      })
      await flushPromises()
      return { wrapper, auth }
    }

    afterEach(() => {
      display.mdAndUp = ref(true)
    })

    it('offers a menu button and lists the same entries as the desktop menu', async () => {
      const { wrapper } = await mountMobile({ role: 'admin' })

      expect(wrapper.find('[aria-label="Open menu"]').exists()).toBe(true)
      const labels = wrapper.findAll('.drawer .v-list-item').map(i => i.text())
      for (const label of ['Dashboard', 'Titled page', 'Curations', 'Review queue', 'Schemas']) {
        expect(labels.some(l => l.includes(label))).toBe(true)
      }
      expect(labels.some(l => l.includes('Review queue') && l.includes('2'))).toBe(true)
      expect(labels.some(l => l.includes('Logout'))).toBe(true)
      expect(wrapper.find('.drawer [href="/profile"]').exists()).toBe(true)
    })

    it('logs out from the drawer', async () => {
      const { wrapper, auth } = await mountMobile({ role: 'user' })
      const logout = vi.spyOn(auth, 'logout').mockResolvedValue(undefined as never)

      await wrapper
        .findAll('.drawer .v-list-item')
        .find(i => i.text().includes('Logout'))
        ?.trigger('click')

      expect(logout).toHaveBeenCalled()
    })

    it('offers Sign in to guests', async () => {
      const { wrapper } = await mountMobile(null)

      expect(wrapper.find('.drawer [href="/login"]').exists()).toBe(true)
    })
  })
})
