import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import { VLayout } from 'vuetify/components'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createMemoryHistory, type Router } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useScopesStore } from '@/stores/scopes'
import { useWorkflowStore } from '@/stores/workflow'
import SideRail from '../SideRail.vue'

vi.mock('@/services/logService', () => ({
  logService: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }
}))
vi.mock('@/composables/useLogger', () => ({
  useLogger: () => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() })
}))
vi.mock('../UserMenu.vue', () => ({
  default: defineComponent({ name: 'UserMenu', render: () => h('div') })
}))

const component = { render: () => null }
const main = (label: string, order: number, extra = {}) => ({
  showInMainMenu: true,
  label,
  icon: 'mdi-home',
  order,
  ...extra
})

function makeRouter(): Router {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'Home', component },
      {
        path: '/assignments',
        name: 'GeneAssignments',
        component,
        meta: main('My work', 1, { requiresAuth: true })
      },
      {
        path: '/review-queue',
        name: 'review-queue',
        component,
        meta: main('Review', 2, { requiresAuth: true })
      },
      { path: '/genes', name: 'GeneCatalogue', component, meta: main('Genes', 4) },
      { path: '/scopes/:scopeId', name: 'scope-dashboard', component },
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

async function mountRail(router = makeRouter()) {
  const wrapper = mount(
    defineComponent({ render: () => h('div', [h(VLayout, () => h(SideRail))]) }),
    { global: { plugins: [router] }, attachTo: document.body }
  )
  await router.push('/')
  await flushPromises()
  return wrapper
}

describe('SideRail', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    const workflow = useWorkflowStore()
    vi.spyOn(workflow, 'fetchPendingReviewCount').mockResolvedValue(undefined as never)
    vi.spyOn(useScopesStore(), 'fetchUserScopes').mockResolvedValue([] as never)
  })

  it('is a labelled primary navigation landmark listing public destinations for guests', async () => {
    const wrapper = await mountRail()
    const nav = wrapper.find('nav')
    expect(nav.attributes('aria-label')).toBe('Primary')
    expect(nav.text()).toContain('Genes')
    expect(nav.text()).not.toContain('My work')
    expect(nav.text()).not.toContain('Users')
    wrapper.unmount()
  })

  it('shows work, review count and scope switcher once signed in; admin group only for admins', async () => {
    const auth = useAuthStore()
    auth.token = 't'
    auth.isAuthenticated = true
    auth.user = { email: 'a@b.c', role: 'user' } as never
    useWorkflowStore().pendingReviewCount = 3
    const scopes = useScopesStore()
    scopes.scopes = [{ id: 's1', name: 'Kidney' }] as never
    const wrapper = await mountRail()

    expect(wrapper.text()).toContain('My work')
    expect(wrapper.find('a[aria-label="Review, 3 pending"]').exists()).toBe(true)
    expect(wrapper.find('[aria-label="Scope"]').exists()).toBe(true)
    expect(wrapper.text()).not.toContain('Users')
    expect(scopes.fetchUserScopes).not.toHaveBeenCalled() // already loaded
    wrapper.unmount()

    auth.user = { email: 'a@b.c', role: 'admin' } as never
    const admin = await mountRail()
    expect(admin.text()).toContain('Admin')
    expect(admin.text()).toContain('Users')
    admin.unmount()
  })

  it('loads the scopes when signed in and none are loaded yet, and navigates on switch', async () => {
    const auth = useAuthStore()
    auth.token = 't'
    auth.isAuthenticated = true
    auth.user = { email: 'a@b.c', role: 'user' } as never
    const scopes = useScopesStore()
    scopes.scopes = []
    const router = makeRouter()
    const wrapper = await mountRail(router)
    expect(scopes.fetchUserScopes).toHaveBeenCalledTimes(1)

    scopes.scopes = [{ id: 's1', name: 'Kidney' }] as never
    wrapper.findComponent({ name: 'VSelect' }).vm.$emit('update:modelValue', 's1')
    await vi.waitFor(() => expect(router.currentRoute.value.fullPath).toBe('/scopes/s1'))
    wrapper.unmount()
  })
})
