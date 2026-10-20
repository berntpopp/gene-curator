/**
 * MainNavigation Tests
 *
 * Route-driven main menu: simple items, the Curation and Curation Setup
 * dropdowns, role/auth filtering, the review-queue badge and its refresh timer.
 * Internals are reached through the component instance.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createMemoryHistory, type Router } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useWorkflowStore } from '@/stores/workflow'
import MainNavigation from '../MainNavigation.vue'
import { stubVisualViewport } from './overlayStubs'

vi.mock('@/services/logService', () => ({
  logService: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }
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
          showInDropdown: 'curation',
          requiresAuth: true,
          requiredRoles: ['curator'],
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
    const fetchSpy = vi.spyOn(workflow, 'fetchPendingReviewCount').mockResolvedValue(3)
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

  it('shows curation items to signed-in users and hides guest-only links', async () => {
    const { vm } = await mountNav({ role: 'viewer' })

    expect(vm.simpleItems.map(i => i.label)).toEqual(['Dashboard', 'Titled page'])
    expect(vm.curationItems.map(i => i.label)).toEqual(['Curations'])
  })

  it('shows the review queue and its pending badge to curators', async () => {
    const { wrapper, vm, fetchSpy } = await mountNav({ role: 'curator' })

    expect(vm.curationItems.map(i => i.name)).toEqual(['Curations', 'review-queue'])
    expect(fetchSpy).toHaveBeenCalled()
    expect(vm.pendingReviewCount).toBe(3)
    expect(vm.curationItems.find(i => i.name === 'review-queue')?.badge).toBe(3)
    expect(wrapper.text()).toContain('Curation')
  })

  it('shows the setup dropdown only to admins', async () => {
    const curator = await mountNav({ role: 'curator' })
    expect(curator.vm.curationSetupItems).toEqual([])

    const admin = await mountNav({ role: 'admin' })
    expect(admin.vm.curationSetupItems.map(i => i.label)).toEqual(['Schemas'])
  })

  it('refreshes the badge every minute and stops when unmounted', async () => {
    vi.useFakeTimers()
    const { wrapper, fetchSpy } = await mountNav({ role: 'curator' })
    expect(fetchSpy).toHaveBeenCalledTimes(1)

    await vi.advanceTimersByTimeAsync(60000)
    expect(fetchSpy).toHaveBeenCalledTimes(2)

    wrapper.unmount()
    await vi.advanceTimersByTimeAsync(60000)
    expect(fetchSpy).toHaveBeenCalledTimes(2)
  })

  it('clears the badge on sign-out and restarts refreshing on sign-in', async () => {
    const { auth, fetchSpy, vm } = await mountNav({ role: 'curator' })
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
    auth.user = { role: 'curator' } as unknown as typeof auth.user
    const workflow = useWorkflowStore()
    vi.spyOn(workflow, 'fetchPendingReviewCount').mockRejectedValue(new Error('down'))

    const wrapper = mount(MainNavigation, { global: { plugins: [pinia, router] } })
    await flushPromises()

    expect((wrapper.vm as unknown as MainNavInternals).pendingReviewCount).toBe(0)
  })

  it('opens the curation dropdown and renders its items as router links', async () => {
    stubVisualViewport()
    const auth = useAuthStore()
    auth.isAuthenticated = true
    auth.user = { role: 'curator' } as unknown as typeof auth.user
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
      .filter(el => el.textContent?.includes('Review queue'))
      .pop() as HTMLElement | undefined
    // The item is a router link to the review queue; navigation itself is covered by the router
    expect(option?.getAttribute('href')).toBe('/review')
    wrapper.unmount()
  })
})
