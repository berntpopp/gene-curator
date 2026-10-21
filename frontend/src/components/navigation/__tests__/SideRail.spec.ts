import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import { VLayout } from 'vuetify/components'
import { createPinia, setActivePinia } from 'pinia'
import { useAuthStore } from '@/stores/auth'
import { useScopesStore } from '@/stores/scopes'
import { useWorkCountsStore } from '@/stores/workCounts'
import SideRail from '../SideRail.vue'
import { makeRealRouter } from './realRoutes'

vi.mock('@/services/logService', () => ({
  logService: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }
}))
vi.mock('@/composables/useLogger', () => ({
  useLogger: () => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() })
}))
vi.mock('../UserMenu.vue', () => ({
  default: defineComponent({ name: 'UserMenu', render: () => h('div') })
}))

const makeRouter = makeRealRouter

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
    vi.spyOn(useWorkCountsStore(), 'fetch').mockResolvedValue(undefined as never)
    vi.spyOn(useScopesStore(), 'fetchUserScopes').mockResolvedValue([] as never)
  })

  it('is a labelled primary navigation landmark listing public destinations for guests', async () => {
    const wrapper = await mountRail()
    const nav = wrapper.find('nav')
    expect(nav.attributes('aria-label')).toBe('Primary')
    expect(nav.text()).toContain('Gene Catalogue')
    expect(nav.text()).not.toContain('My work')
    expect(nav.text()).not.toContain('Users')
    wrapper.unmount()
  })

  it('shows work, review count and scope switcher once signed in; admin group only for admins', async () => {
    const auth = useAuthStore()
    auth.token = 't'
    auth.isAuthenticated = true
    auth.user = { email: 'a@b.c', role: 'user' } as never
    Object.assign(useWorkCountsStore(), { review: 3, needsYou: 5 })
    const scopes = useScopesStore()
    scopes.scopes = [{ id: 's1', name: 'Kidney', user_role: 'reviewer' }] as never
    const wrapper = await mountRail()

    expect(wrapper.text()).toContain('My work')
    expect(wrapper.find('a[aria-label="Review, 3 pending"]').exists()).toBe(true)
    expect(wrapper.find('a[aria-label="My work, 5 pending"]').exists()).toBe(true)
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

  it('loads the scopes when the user signs in after the rail mounted', async () => {
    const auth = useAuthStore()
    const scopes = useScopesStore()
    scopes.scopes = []
    const wrapper = await mountRail()
    expect(scopes.fetchUserScopes).not.toHaveBeenCalled()

    auth.token = 't'
    auth.isAuthenticated = true
    auth.user = { email: 'a@b.c', role: 'user' } as never
    await flushPromises()
    expect(scopes.fetchUserScopes).toHaveBeenCalledTimes(1)
    wrapper.unmount()
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

  describe('entries follow the role (#monkey)', () => {
    const signIn = (role: 'user' | 'admin', scopeRole: string | null) => {
      const auth = useAuthStore()
      auth.token = 't'
      auth.isAuthenticated = true
      auth.user = { email: 'a@b.c', role } as never
      useScopesStore().scopes = [{ id: 's1', name: 'k', user_role: scopeRole }] as never
    }

    it('hides Review and Assignments from a viewer', async () => {
      signIn('user', 'viewer')
      const wrapper = await mountRail()
      expect(wrapper.text()).not.toContain('Review')
      expect(wrapper.text()).not.toContain('Assignments')
      wrapper.unmount()
    })

    it('shows Review to a scope reviewer and to a scope admin, still no Assignments', async () => {
      for (const role of ['reviewer', 'admin']) {
        signIn('user', role)
        const wrapper = await mountRail()
        expect(wrapper.text()).toContain('Review')
        expect(wrapper.text()).not.toContain('Assignments')
        wrapper.unmount()
      }
    })

    it('gives a platform admin Assignments, but Review only with a real reviewer or admin membership', async () => {
      signIn('admin', 'viewer')
      let wrapper = await mountRail()
      expect(wrapper.text()).toContain('Assignments')
      expect(wrapper.text()).not.toContain('Review')
      wrapper.unmount()

      signIn('admin', 'reviewer')
      wrapper = await mountRail()
      expect(wrapper.text()).toContain('Review')
      wrapper.unmount()
    })

    it('hides Review from a curator', async () => {
      signIn('user', 'curator')
      const wrapper = await mountRail()
      expect(wrapper.text()).not.toContain('Review')
      wrapper.unmount()
    })
  })
})
