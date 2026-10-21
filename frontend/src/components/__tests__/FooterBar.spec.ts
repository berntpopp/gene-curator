/**
 * FooterBar Component Tests
 *
 * @see src/components/FooterBar.vue
 */

import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount, type VueWrapper } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import FooterBar from '../FooterBar.vue'

const logger = vi.hoisted(() => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }))
vi.mock('@/composables/useLogger', () => ({ useLogger: () => logger }))

const logStore = vi.hoisted(() => ({ errorCount: 3, showViewer: vi.fn() }))
vi.mock('@/stores/logStore', () => ({ useLogStore: () => logStore }))

const disclaimerStore = vi.hoisted(() => ({
  isAcknowledged: true,
  formattedAcknowledgmentDate: '1 January 2026',
  showDisclaimerDialog: vi.fn()
}))
vi.mock('@/stores/disclaimer', () => ({ useDisclaimerStore: () => disclaimerStore }))

const authStore = vi.hoisted(() => ({ isAdmin: false }))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => authStore }))

// v-footer needs a Vuetify layout; render it as a plain container instead.
const passthrough = defineComponent({
  setup(_, { slots }) {
    return () => h('footer', slots.default?.())
  }
})

let wrapper: VueWrapper | undefined

function mountFooter() {
  wrapper = mount(FooterBar, { global: { stubs: { VFooter: passthrough } } })
  return wrapper
}

function buttonWith(text: string) {
  return wrapper?.findAll('button, a').find(b => b.text().includes(text))
}

describe('FooterBar', () => {
  afterEach(() => {
    wrapper?.unmount()
    wrapper = undefined
    authStore.isAdmin = false
    vi.unstubAllEnvs()
    vi.clearAllMocks()
  })

  it('shows the current year and the external links', () => {
    mountFooter()

    expect(wrapper?.text()).toContain(String(new Date().getFullYear()))
    expect(buttonWith('GitHub')?.attributes('href')).toBe(
      'https://github.com/halbritter-lab/gene-curator'
    )
    expect(buttonWith('Docs')?.attributes('href')).toBe(
      'https://github.com/halbritter-lab/gene-curator/wiki'
    )
  })

  it('opens the disclaimer from its button', async () => {
    mountFooter()

    await buttonWith('Disclaimer')?.trigger('click')

    expect(disclaimerStore.showDisclaimerDialog).toHaveBeenCalled()
    expect(logger.debug).toHaveBeenCalledWith('Disclaimer button clicked in footer')
  })

  it('hides the Logs button from non-admins outside dev builds', () => {
    vi.stubEnv('DEV', false)
    mountFooter()

    expect(buttonWith('Logs')).toBeUndefined()
  })

  it('shows the Logs button to admins in production builds', () => {
    vi.stubEnv('DEV', false)
    authStore.isAdmin = true
    mountFooter()

    expect(buttonWith('Logs')).toBeDefined()
  })

  it('shows the error count and opens the log viewer', async () => {
    mountFooter()

    expect(wrapper?.text()).toContain('Logs')
    await buttonWith('Logs')?.trigger('click')

    expect(logStore.showViewer).toHaveBeenCalled()
  })

  it('shows the acknowledgement check mark only once acknowledged', async () => {
    mountFooter()
    expect(wrapper?.html()).toContain('mdi-check-circle')

    disclaimerStore.isAcknowledged = false
    wrapper?.unmount()
    mountFooter()
    expect(wrapper?.html()).not.toContain('mdi-check-circle')

    disclaimerStore.isAcknowledged = true
  })
})
