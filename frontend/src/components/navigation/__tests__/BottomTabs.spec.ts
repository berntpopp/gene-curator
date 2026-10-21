import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import { VLayout } from 'vuetify/components'
import { createPinia, setActivePinia } from 'pinia'
import { useAuthStore } from '@/stores/auth'
import { useScopesStore } from '@/stores/scopes'
import { useWorkCountsStore } from '@/stores/workCounts'
import { showInfo } from '@/composables/useNotifications'
import BottomTabs from '../BottomTabs.vue'
import { makeRealRouter } from './realRoutes'

vi.mock('@/composables/useNotifications', () => ({ showInfo: vi.fn() }))
vi.mock('@/composables/useLogger', () => ({
  useLogger: () => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() })
}))
vi.mock('@/services/logService', () => ({
  logService: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }
}))

const makeRouter = makeRealRouter

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
  // A reviewer in one scope: the Review tab shows for scope reviewers and admins only
  useScopesStore().scopes = [{ id: 's1', name: 'k', user_role: 'reviewer' }] as never
  return auth
}

describe('BottomTabs', () => {
  beforeEach(() => {
    document.body.innerHTML = ''
    setActivePinia(createPinia())
    vi.spyOn(useWorkCountsStore(), 'fetch').mockResolvedValue(undefined as never)
    vi.spyOn(useScopesStore(), 'fetchUserScopes').mockResolvedValue([] as never)
  })

  it('renders nothing for signed-out users', async () => {
    const { wrapper } = await mountTabs()
    expect(wrapper.find('nav').exists()).toBe(false)
    wrapper.unmount()
  })

  it('is a labelled landmark with one tab per primary destination plus Account', async () => {
    signIn('user')
    Object.assign(useWorkCountsStore(), { review: 3, needsYou: 5 })
    const { wrapper } = await mountTabs()

    expect(wrapper.find('nav').attributes('aria-label')).toBe('Primary')
    const labels = wrapper.findAll('.v-btn').map(b => b.attributes('aria-label') ?? b.text())
    expect(labels).toEqual([
      'My work, 5 pending',
      'Review, 3 pending',
      'Gene Catalogue',
      'Scopes',
      'Account'
    ])
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
