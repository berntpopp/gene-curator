import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref, reactive, defineComponent, h, shallowRef, type Component } from 'vue'
import App from '../App.vue'
import { useAuthStore } from '@/stores/auth'
import { useLogStore } from '@/stores/logStore'
import { useDisclaimerStore } from '@/stores/disclaimer'

const display = vi.hoisted(() => ({ mdAndUp: { value: true } }))
vi.mock('vuetify', async importOriginal => ({
  ...(await importOriginal<typeof import('vuetify')>()),
  useDisplay: () => display
}))
vi.mock('@/stores/auth', () => ({ useAuthStore: vi.fn() }))
vi.mock('@/stores/logStore', () => ({ useLogStore: vi.fn() }))
vi.mock('@/stores/disclaimer', () => ({ useDisclaimerStore: vi.fn() }))
vi.mock('@/composables/useNotifications', () => ({
  snackbarState: { show: false, message: '', color: 'info', timeout: 3000 }
}))
vi.mock('@/composables/useLogger', () => ({
  useLogger: () => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() })
}))

interface DisclaimerState {
  showManually: boolean
  shouldShowDisclaimer: boolean
  disclaimerVersion: string
  formattedAcknowledgmentDate: string
  resetShowManually: ReturnType<typeof vi.fn>
  saveAcknowledgment: ReturnType<typeof vi.fn>
  initialize: ReturnType<typeof vi.fn>
}

const stubs = {
  AppBar: true,
  SideRail: true,
  BottomTabs: true,
  PhoneHeader: true,
  FooterBar: true,
  MessageSnackbar: true,
  LogViewer: true,
  DisclaimerDialog: true,
  CommandPalette: true,
  'router-view': true
}

describe('App', () => {
  let authInitialize: ReturnType<typeof vi.fn>
  let toggleViewer: ReturnType<typeof vi.fn>
  let disclaimer: DisclaimerState & Record<string, unknown>

  beforeEach(() => {
    vi.clearAllMocks()
    authInitialize = vi.fn().mockResolvedValue(undefined)
    toggleViewer = vi.fn()
    disclaimer = reactive({
      showManually: false,
      shouldShowDisclaimer: false,
      disclaimerVersion: '1.0',
      formattedAcknowledgmentDate: 'yesterday',
      resetShowManually: vi.fn(),
      saveAcknowledgment: vi.fn(),
      initialize: vi.fn()
    }) as DisclaimerState & Record<string, unknown>

    vi.mocked(useAuthStore).mockReturnValue({ initialize: authInitialize } as never)
    vi.mocked(useLogStore).mockReturnValue({ toggleViewer } as never)
    vi.mocked(useDisclaimerStore).mockReturnValue(disclaimer as never)
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('shows the side rail only to signed-in users at md and up', async () => {
    const auth = reactive({ initialize: authInitialize, isAuthenticated: false })
    vi.mocked(useAuthStore).mockReturnValue(auth as never)
    const wrapper = mount(App, { global: { stubs, mocks: { $route: { fullPath: '/' } } } })
    await flushPromises()
    expect(wrapper.findComponent({ name: 'SideRail' }).exists()).toBe(false)
    expect(wrapper.findComponent({ name: 'AppBar' }).exists()).toBe(true)

    expect(wrapper.findComponent({ name: 'BottomTabs' }).exists()).toBe(false)

    auth.isAuthenticated = true
    await flushPromises()
    expect(wrapper.findComponent({ name: 'SideRail' }).exists()).toBe(true)
    expect(wrapper.findComponent({ name: 'AppBar' }).exists()).toBe(false)
    wrapper.unmount()
  })

  it('shows the bottom tabs, not the rail, below md', async () => {
    display.mdAndUp = ref(false)
    const wrapper = mount(App, { global: { stubs, mocks: { $route: { fullPath: '/' } } } })
    await flushPromises()
    expect(wrapper.findComponent({ name: 'BottomTabs' }).exists()).toBe(true)
    expect(wrapper.findComponent({ name: 'SideRail' }).exists()).toBe(false)
    expect(wrapper.findComponent({ name: 'AppBar' }).exists()).toBe(true) // guest: brand bar
    display.mdAndUp = ref(true)
    wrapper.unmount()
  })

  it('replaces the brand bar with the page header for signed-in phones', async () => {
    display.mdAndUp = ref(false)
    vi.mocked(useAuthStore).mockReturnValue({
      initialize: authInitialize,
      isAuthenticated: true
    } as never)
    const wrapper = mount(App, { global: { stubs, mocks: { $route: { fullPath: '/' } } } })
    await flushPromises()
    expect(wrapper.findComponent({ name: 'PhoneHeader' }).exists()).toBe(true)
    expect(wrapper.findComponent({ name: 'AppBar' }).exists()).toBe(false)
    display.mdAndUp = ref(true)
    wrapper.unmount()
  })

  it('marks the app has-phone-header only while the phone header renders', async () => {
    display.mdAndUp = ref(false)
    const auth = reactive({ initialize: authInitialize, isAuthenticated: false })
    vi.mocked(useAuthStore).mockReturnValue(auth as never)
    const wrapper = mount(App, { global: { stubs, mocks: { $route: { fullPath: '/' } } } })
    await flushPromises()
    expect(wrapper.classes()).not.toContain('has-phone-header') // guest phone keeps view titles
    auth.isAuthenticated = true
    await flushPromises()
    expect(wrapper.classes()).toContain('has-phone-header')
    display.mdAndUp = ref(true)
    wrapper.unmount()
  })

  it('initialises auth and disclaimer stores on mount', async () => {
    const wrapper = mount(App, { global: { stubs, mocks: { $route: { fullPath: '/' } } } })
    await flushPromises()

    expect(authInitialize).not.toHaveBeenCalled()
    expect(disclaimer.initialize).toHaveBeenCalledTimes(1)
    wrapper.unmount()
  })

  it('shows the disclaimer after a short delay when it has not been acknowledged', async () => {
    vi.useFakeTimers()
    disclaimer.shouldShowDisclaimer = true

    const wrapper = mount(App, { global: { stubs, mocks: { $route: { fullPath: '/' } } } })
    await flushPromises()

    const dialog = wrapper.findComponent({ name: 'DisclaimerDialog' })
    expect(dialog.props('modelValue')).toBe(false)

    vi.advanceTimersByTime(500)
    await flushPromises()

    expect(dialog.props('modelValue')).toBe(true)
    wrapper.unmount()
  })

  it('opens the disclaimer on a manual request and resets the request flag', async () => {
    const wrapper = mount(App, { global: { stubs, mocks: { $route: { fullPath: '/' } } } })
    await flushPromises()

    disclaimer.showManually = true
    await flushPromises()

    expect(disclaimer.resetShowManually).toHaveBeenCalledTimes(1)
    expect(wrapper.findComponent({ name: 'DisclaimerDialog' }).props('modelValue')).toBe(true)
    wrapper.unmount()
  })

  it('saves the acknowledgment and closes the dialog when the user accepts', async () => {
    disclaimer.showManually = true
    const wrapper = mount(App, { global: { stubs, mocks: { $route: { fullPath: '/' } } } })
    await flushPromises()

    const dialog = wrapper.findComponent({ name: 'DisclaimerDialog' })
    dialog.vm.$emit('acknowledged')
    await flushPromises()

    expect(disclaimer.saveAcknowledgment).toHaveBeenCalledTimes(1)
    expect(dialog.props('modelValue')).toBe(false)
    wrapper.unmount()
  })

  it('mounts the log viewer only while it is visible', async () => {
    const logStore = reactive({ toggleViewer, isViewerVisible: false })
    vi.mocked(useLogStore).mockReturnValue(logStore as never)
    const wrapper = mount(App, { global: { stubs, mocks: { $route: { fullPath: '/' } } } })
    await flushPromises()
    expect(wrapper.findComponent({ name: 'LogViewer' }).exists()).toBe(false)

    logStore.isViewerVisible = true
    await flushPromises()
    expect(wrapper.findComponent({ name: 'LogViewer' }).exists()).toBe(true)
    wrapper.unmount()
  })

  it('shows the error boundary when a routed view throws and recovers on navigation', async () => {
    const Throwing = defineComponent({
      setup() {
        throw new Error('view exploded')
      }
    })
    const route = reactive({ fullPath: '/a' })
    const view = shallowRef<Component>(Throwing)
    const RouterView = defineComponent({ render: () => h(view.value) })
    const wrapper = mount(App, {
      global: {
        stubs: { ...stubs, 'router-view': RouterView },
        mocks: { $route: route }
      }
    })
    await flushPromises()
    expect(wrapper.text()).toContain('view exploded')

    view.value = defineComponent({ render: () => h('p', 'fine') })
    route.fullPath = '/b'
    await flushPromises()
    expect(wrapper.text()).toContain('fine')
    expect(wrapper.text()).not.toContain('view exploded')
    wrapper.unmount()
  })

  it('has a skip link that focuses the main content', async () => {
    const wrapper = mount(App, {
      global: { stubs: { ...stubs, 'v-main': false }, mocks: { $route: { fullPath: '/' } } },
      attachTo: document.body
    })
    await flushPromises()

    expect(wrapper.find('a.skip-link').attributes('href')).toBe('#main-content')
    wrapper.unmount()
  })

  it('toggles the log viewer on Ctrl+Shift+L and ignores other keys', async () => {
    const wrapper = mount(App, { global: { stubs, mocks: { $route: { fullPath: '/' } } } })
    await flushPromises()

    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'L', ctrlKey: true, shiftKey: true }))
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'l', ctrlKey: true, shiftKey: true }))
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'L', ctrlKey: true }))

    expect(toggleViewer).toHaveBeenCalledTimes(1)
    wrapper.unmount()
  })

  it('stops listening for keyboard shortcuts after unmount', async () => {
    const wrapper = mount(App, { global: { stubs, mocks: { $route: { fullPath: '/' } } } })
    await flushPromises()
    wrapper.unmount()

    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'L', ctrlKey: true, shiftKey: true }))

    expect(toggleViewer).not.toHaveBeenCalled()
  })
})
