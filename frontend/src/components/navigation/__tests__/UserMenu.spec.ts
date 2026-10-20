/**
 * UserMenu Tests
 *
 * Login button vs. user menu, route-driven menu items filtered by auth and role,
 * role labels, unread badge input, and logout. Internals are reached through the
 * component instance.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createMemoryHistory, type Router } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useNotificationsStore } from '@/stores/notifications'
import { logService } from '@/services/logService'
import UserMenu from '../UserMenu.vue'

vi.mock('@/services/logService', () => ({
  logService: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }
}))

interface UserMenuInternals {
  userMenuItems: { name: string; label: string }[]
  roleLabel: string
  totalUnread: number
  handleLogout: () => Promise<void>
}

const component = { render: () => null }

function makeRouter(): Router {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'Home', component },
      { path: '/login', name: 'Login', component },
      {
        path: '/profile',
        name: 'Profile',
        component,
        meta: {
          showInUserMenu: true,
          requiresAuth: true,
          label: 'Profile',
          icon: 'mdi-account',
          order: 2
        }
      },
      {
        path: '/admin-tools',
        name: 'AdminTools',
        component,
        meta: { showInUserMenu: true, requiredRoles: ['admin'], label: 'Admin tools', order: 1 }
      },
      { path: '/hidden', name: 'Hidden', component, meta: { label: 'Hidden' } }
    ]
  })
}

describe('UserMenu', () => {
  let pinia: ReturnType<typeof createPinia>
  let router: Router

  beforeEach(async () => {
    pinia = createPinia()
    setActivePinia(pinia)
    router = makeRouter()
    await router.push('/')
    await router.isReady()
    vi.mocked(logService.error).mockClear()
  })

  async function mountMenu(user: { email: string; role: string } | null) {
    const auth = useAuthStore()
    auth.isAuthenticated = user !== null
    auth.user = user as typeof auth.user
    const notifications = useNotificationsStore()
    const fetchSpy = vi
      .spyOn(notifications, 'fetchNotifications')
      .mockResolvedValue(undefined as never)
    const wrapper = mount(UserMenu, { global: { plugins: [pinia, router] } })
    await flushPromises()
    return {
      wrapper,
      auth,
      notifications,
      fetchSpy,
      vm: wrapper.vm as unknown as UserMenuInternals
    }
  }

  it('shows a login button and no menu for guests', async () => {
    const { wrapper, vm, fetchSpy } = await mountMenu(null)

    expect(wrapper.find('.mdi-login').exists()).toBe(true)
    expect(wrapper.find('.mdi-account-circle').exists()).toBe(false)
    expect(vm.userMenuItems).toEqual([])
    expect(fetchSpy).not.toHaveBeenCalled()
  })

  it('renders the avatar and loads notifications for signed-in users', async () => {
    const { wrapper, fetchSpy } = await mountMenu({ email: 'c@example.org', role: 'curator' })

    expect(wrapper.find('.mdi-account-circle').exists()).toBe(true)
    expect(wrapper.find('.mdi-login').exists()).toBe(false)
    expect(fetchSpy).toHaveBeenCalledTimes(1)
  })

  it('lists only the route items the user may see, ordered by meta.order', async () => {
    const curator = await mountMenu({ email: 'c@example.org', role: 'curator' })
    expect(curator.vm.userMenuItems.map(i => i.label)).toEqual(['Profile'])

    const admin = await mountMenu({ email: 'a@example.org', role: 'admin' })
    expect(admin.vm.userMenuItems.map(i => i.label)).toEqual(['Admin tools', 'Profile'])
  })

  it('translates the role into its display label', async () => {
    const admin = await mountMenu({ email: 'a@example.org', role: 'admin' })
    expect(admin.vm.roleLabel).toBe('Admin')

    const unknown = await mountMenu({ email: 'x@example.org', role: 'mystery' })
    expect(unknown.vm.roleLabel).toBe('mystery')

    const noRole = await mountMenu({ email: 'y@example.org', role: '' })
    expect(noRole.vm.roleLabel).toBe('')
  })

  it('counts unread notifications for the badge', async () => {
    const { notifications, vm } = await mountMenu({ email: 'c@example.org', role: 'curator' })
    notifications.notifications = [
      { is_read: false },
      { is_read: true },
      { is_read: false }
    ] as never

    expect(vm.totalUnread).toBe(2)
  })

  it('logs out, returns home and logs the event', async () => {
    const { auth, vm } = await mountMenu({ email: 'c@example.org', role: 'curator' })
    const logout = vi.spyOn(auth, 'logout').mockResolvedValue(undefined as never)

    await vm.handleLogout()
    await flushPromises()

    expect(logout).toHaveBeenCalledTimes(1)
    expect(router.currentRoute.value.name).toBe('Home')
  })

  it('logs a failed logout without throwing', async () => {
    const { auth, vm } = await mountMenu({ email: 'c@example.org', role: 'curator' })
    vi.spyOn(auth, 'logout').mockRejectedValueOnce(new Error('network'))

    await expect(vm.handleLogout()).resolves.toBeUndefined()

    expect(logService.error).toHaveBeenCalledWith(
      'Logout error:',
      expect.objectContaining({ error: 'network' })
    )
  })

  it('logs non-Error logout failures without a message', async () => {
    const { auth, vm } = await mountMenu({ email: 'c@example.org', role: 'curator' })
    vi.spyOn(auth, 'logout').mockRejectedValueOnce('plain string')

    await vm.handleLogout()

    expect(logService.error).toHaveBeenCalledWith(
      'Logout error:',
      expect.objectContaining({ error: undefined, stack: undefined })
    )
  })

  it('opens the avatar menu, lists role-filtered items and logs out from it', async () => {
    const { wrapper, auth } = await mountMenu({ email: 'a@example.org', role: 'admin' })
    const logout = vi.spyOn(auth, 'logout').mockResolvedValue(undefined as never)

    await wrapper.find('button').trigger('click')
    await flushPromises()
    expect(document.body.textContent).toContain('a@example.org')
    expect(document.body.textContent).toContain('Admin tools')

    const logoutItem = Array.from(document.querySelectorAll('.v-list-item'))
      .filter(el => el.textContent?.includes('Logout'))
      .pop() as HTMLElement | undefined
    logoutItem?.click()
    await flushPromises()

    expect(logout).toHaveBeenCalledTimes(1)
    wrapper.unmount()
  })
})
