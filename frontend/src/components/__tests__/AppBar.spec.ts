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

    expect(wrapper?.text()).toContain('Version: 0.4.0 - Build: dev')
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

  it('cycles system -> light -> dark -> system, persisting each choice without deprecation warnings', async () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    mountAppBar()
    const toggle = wrapper?.find('.ml-2')

    expect(toggle?.attributes('aria-label')).toBe('Theme: system. Switch to light theme')
    expect(toggle?.html()).toContain('mdi-theme-light-dark')

    for (const [next, label, icon] of [
      ['light', 'Theme: light. Switch to dark theme', 'mdi-white-balance-sunny'],
      ['dark', 'Theme: dark. Switch to system theme', 'mdi-weather-night'],
      ['system', 'Theme: system. Switch to light theme', 'mdi-theme-light-dark']
    ]) {
      await toggle?.trigger('click')
      expect(localStorage.getItem('theme')).toBe(next)
      expect(logger.info).toHaveBeenLastCalledWith('Theme changed', { theme: next })
      expect(toggle?.attributes('aria-label')).toBe(label)
      expect(toggle?.html()).toContain(icon)
    }
    expect(warn).not.toHaveBeenCalled()
  })

  it('starts from the saved theme', () => {
    localStorage.setItem('theme', 'dark')
    mountAppBar()

    expect(wrapper?.find('.ml-2').attributes('aria-label')).toBe(
      'Theme: dark. Switch to system theme'
    )
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
