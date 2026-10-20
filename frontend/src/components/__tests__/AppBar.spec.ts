/**
 * AppBar Component Tests
 *
 * @see src/components/AppBar.vue
 */

import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount, type VueWrapper } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
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

const router = { push: vi.fn() }

let wrapper: VueWrapper | undefined

function mountAppBar() {
  wrapper = mount(AppBar, {
    global: {
      mocks: { $router: router },
      stubs: { VAppBar: passthrough }
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

  it('navigates home from the title', async () => {
    mountAppBar()

    await wrapper?.find('.clickable').trigger('click')

    expect(router.push).toHaveBeenCalledWith('/')
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
})
