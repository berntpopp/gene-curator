import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import { VLayout } from 'vuetify/components'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createMemoryHistory, type Router } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useWorkflowStore } from '@/stores/workflow'
import { showInfo } from '@/composables/useNotifications'
import BottomTabs from '../BottomTabs.vue'

vi.mock('@/composables/useNotifications', () => ({ showInfo: vi.fn() }))
vi.mock('@/composables/useLogger', () => ({
  useLogger: () => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() })
}))
vi.mock('@/services/logService', () => ({
  logService: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }
}))

const component = { render: () => null }
const main = (label: string, order: number, extra = {}) => ({
  showInMainMenu: true,
  label,
  icon: 'mdi-home',
  order,
  requiresAuth: true,
  ...extra
})

function makeRouter(): Router {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'Home', component },
      { path: '/assignments', name: 'GeneAssignments', component, meta: main('My work', 1) },
      { path: '/review-queue', name: 'review-queue', component, meta: main('Review', 2) },
      { path: '/scopes', name: 'scopes', component, meta: main('Scopes', 3, { tabOrder: 4 }) },
      {
        path: '/genes',
        name: 'GeneCatalogue',
        component,
        meta: main('Gene Catalogue', 4, { tabLabel: 'Genes', tabOrder: 3 })
      },
      { path: '/profile', name: 'UserProfile', component },
      {
        path: '/admin/users',
        name: 'UserManagement',
        component,
        meta: {
          requiresAuth: true,
          requiredRoles: ['admin'],
          showInDropdown: 'curationSetup',
          label: 'Users',
          icon: 'mdi-account-group',
          order: 3
        }
      }
    ]
  })
}

async function mountTabs(router = makeRouter()) {
  const wrapper = mount(defineComponent({ render: () => h(VLayout, () => h(BottomTabs)) }), {
    global: { plugins: [router] },
    attachTo: document.body
  })
  await router.push('/')
  await flushPromises()
  return { wrapper, router }
}

function signIn(role: string) {
  const auth = useAuthStore()
  auth.token = 't'
  auth.isAuthenticated = true
  auth.user = { email: 'a@b.c', role } as never
  return auth
}

describe('BottomTabs', () => {
  beforeEach(() => {
    document.body.innerHTML = ''
    setActivePinia(createPinia())
    vi.spyOn(useWorkflowStore(), 'fetchPendingReviewCount').mockResolvedValue(undefined as never)
  })

  it('renders nothing for signed-out users', async () => {
    const { wrapper } = await mountTabs()
    expect(wrapper.find('nav').exists()).toBe(false)
    wrapper.unmount()
  })

  it('is a labelled landmark with one tab per primary destination plus Account', async () => {
    signIn('user')
    useWorkflowStore().pendingReviewCount = 3
    const { wrapper } = await mountTabs()

    expect(wrapper.find('nav').attributes('aria-label')).toBe('Primary')
    const labels = wrapper.findAll('.v-btn').map(b => b.attributes('aria-label') ?? b.text())
    expect(labels).toEqual(['My work', 'Review, 3 pending', 'Gene Catalogue', 'Scopes', 'Account'])
    // the visible text is the short tab label so five tabs fit at 390 px
    expect(wrapper.findAll('.v-btn span').map(s => s.text())).toContain('Genes')
    wrapper.unmount()
  })

  it('opens an account menu with profile and logout; admins also get the admin entries', async () => {
    const auth = signIn('admin')
    const logout = vi.spyOn(auth, 'logout').mockResolvedValue(undefined as never)
    const { wrapper, router } = await mountTabs()

    await wrapper.find('button[aria-label="Account"]').trigger('click')
    await flushPromises()
    const menu = document.body.textContent ?? ''
    expect(menu).toContain('Profile')
    expect(menu).toContain('Users')

    const logoutItem = [...document.body.querySelectorAll('.v-list-item')].find(el =>
      el.textContent?.includes('Logout')
    ) as HTMLElement
    logoutItem.click()
    await flushPromises()
    expect(logout).toHaveBeenCalled()
    expect(showInfo).toHaveBeenCalledWith('Signed out')
    expect(router.currentRoute.value.name).toBe('Home')
    wrapper.unmount()
  })

  it('hides the admin entries from non-admins', async () => {
    signIn('user')
    const { wrapper } = await mountTabs()
    await wrapper.find('button[aria-label="Account"]').trigger('click')
    await flushPromises()
    expect(document.body.textContent).not.toContain('Users')
    wrapper.unmount()
  })
})
