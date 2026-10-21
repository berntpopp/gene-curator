/**
 * AppBar Component Tests
 *
 * @see src/components/AppBar.vue
 */

import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest'
import { mount, RouterLinkStub, type VueWrapper } from '@vue/test-utils'
import { defineComponent, h, ref } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import { useAuthStore } from '@/stores/auth'
import AppBar from '../AppBar.vue'

const logger = vi.hoisted(() => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }))
vi.mock('@/composables/useLogger', () => ({ useLogger: () => logger }))

vi.mock('@/components/navigation/MainNavigation.vue', () => ({
  default: defineComponent({ name: 'MainNavigation', render: () => h('nav') })
}))
vi.mock('@/components/navigation/UserMenu.vue', () => ({
  default: defineComponent({ name: 'UserMenu', render: () => h('div') })
}))

// v-app-bar needs a Vuetify layout; render it as a plain container instead.
const passthrough = defineComponent({
  setup(_, { slots }) {
    return () => h('div', slots.default?.())
  }
})

const display = vi.hoisted(() => ({ mdAndUp: { value: true } }))
vi.mock('vuetify', async importOriginal => ({
  ...(await importOriginal<typeof import('vuetify')>()),
  useDisplay: () => display
}))

let wrapper: VueWrapper | undefined

let pinia = createPinia()

function mountAppBar() {
  wrapper = mount(AppBar, {
    global: {
      plugins: [pinia],
      stubs: { VAppBar: passthrough, RouterLink: RouterLinkStub }
    }
  })
  return wrapper
}

describe('AppBar', () => {
  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
  })

  afterEach(() => {
    wrapper?.unmount()
    wrapper = undefined
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('shows the app version and build', () => {
    mountAppBar()

    expect(wrapper?.text()).toContain('Version: 0.3.0 - Build: dev')
  })

  it('links logo and title to home with one keyboard-reachable link', () => {
    mountAppBar()

    const link = wrapper?.findComponent(RouterLinkStub)
    expect(link?.props('to')).toBe('/')
    expect(link?.attributes('aria-label')).toBe('Gene Curator home')
    expect(link?.text()).toContain('Gene Curator')
    expect(wrapper?.find('.v-img').attributes('alt') ?? '').toBe('')
  })

  it('hides version, theme toggle and user menu below md', () => {
    display.mdAndUp = ref(false)
    mountAppBar()

    expect(wrapper?.text()).not.toContain('Version')
    expect(wrapper?.find('.ml-2').exists()).toBe(false)
    expect(wrapper?.findComponent({ name: 'UserMenu' }).exists()).toBe(false)
    display.mdAndUp = ref(true)
  })

  it('toggles the theme, persists it and logs the change', async () => {
    mountAppBar()

    const toggle = wrapper?.find('.ml-2')
    await toggle?.trigger('click')

    expect(localStorage.getItem('theme')).toBe('dark')
    expect(logger.info).toHaveBeenCalledWith('Theme toggled', { theme: 'dark' })

    await toggle?.trigger('click')

    expect(localStorage.getItem('theme')).toBe('light')
  })

  it('labels the theme toggle with its target theme and shows that theme icon', async () => {
    mountAppBar()
    const toggle = wrapper?.find('.ml-2')

    expect(toggle?.attributes('aria-label')).toBe('Switch to dark theme')
    expect(toggle?.html()).toContain('mdi-weather-night')

    await toggle?.trigger('click')

    expect(toggle?.attributes('aria-label')).toBe('Switch to light theme')
    expect(toggle?.html()).toContain('mdi-white-balance-sunny')
  })

  it('hides navigation and user menu while a stored token has no user loaded yet', () => {
    const auth = useAuthStore()
    auth.token = 't'
    auth.user = null
    mountAppBar()

    expect(wrapper?.find('nav').exists()).toBe(false)
    expect(wrapper?.findComponent({ name: 'UserMenu' }).exists()).toBe(false)
  })
})
