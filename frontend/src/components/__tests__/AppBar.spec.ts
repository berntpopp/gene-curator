/**
 * AppBar Component Tests
 *
 * @see src/components/AppBar.vue
 */

import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount, RouterLinkStub, type VueWrapper } from '@vue/test-utils'
import { defineComponent, h, ref } from 'vue'
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

function mountAppBar() {
  wrapper = mount(AppBar, {
    global: {
      stubs: { VAppBar: passthrough, RouterLink: RouterLinkStub }
    }
  })
  return wrapper
}

describe('AppBar', () => {
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

  it('labels the icon-only theme toggle for screen readers', () => {
    mountAppBar()

    expect(wrapper?.find('.ml-2').attributes('aria-label')).toBe('Toggle theme')
  })
})
