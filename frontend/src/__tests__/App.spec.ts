import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { reactive } from 'vue'
import App from '../App.vue'
import { useAuthStore } from '@/stores/auth'
import { useLogStore } from '@/stores/logStore'
import { useDisclaimerStore } from '@/stores/disclaimer'

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
  FooterBar: true,
  MessageSnackbar: true,
  LogViewer: true,
  DisclaimerDialog: true,
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

  it('initialises auth and disclaimer stores on mount', async () => {
    const wrapper = mount(App, { global: { stubs } })
    await flushPromises()

    expect(authInitialize).toHaveBeenCalledTimes(1)
    expect(disclaimer.initialize).toHaveBeenCalledTimes(1)
    wrapper.unmount()
  })

  it('shows the disclaimer after a short delay when it has not been acknowledged', async () => {
    vi.useFakeTimers()
    disclaimer.shouldShowDisclaimer = true

    const wrapper = mount(App, { global: { stubs } })
    await flushPromises()

    const dialog = wrapper.findComponent({ name: 'DisclaimerDialog' })
    expect(dialog.props('modelValue')).toBe(false)

    vi.advanceTimersByTime(500)
    await flushPromises()

    expect(dialog.props('modelValue')).toBe(true)
    wrapper.unmount()
  })

  it('opens the disclaimer on a manual request and resets the request flag', async () => {
    const wrapper = mount(App, { global: { stubs } })
    await flushPromises()

    disclaimer.showManually = true
    await flushPromises()

    expect(disclaimer.resetShowManually).toHaveBeenCalledTimes(1)
    expect(wrapper.findComponent({ name: 'DisclaimerDialog' }).props('modelValue')).toBe(true)
    wrapper.unmount()
  })

  it('saves the acknowledgment and closes the dialog when the user accepts', async () => {
    disclaimer.showManually = true
    const wrapper = mount(App, { global: { stubs } })
    await flushPromises()

    const dialog = wrapper.findComponent({ name: 'DisclaimerDialog' })
    dialog.vm.$emit('acknowledged')
    await flushPromises()

    expect(disclaimer.saveAcknowledgment).toHaveBeenCalledTimes(1)
    expect(dialog.props('modelValue')).toBe(false)
    wrapper.unmount()
  })

  it('toggles the log viewer on Ctrl+Shift+L and ignores other keys', async () => {
    const wrapper = mount(App, { global: { stubs } })
    await flushPromises()

    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'L', ctrlKey: true, shiftKey: true }))
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'l', ctrlKey: true, shiftKey: true }))
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'L', ctrlKey: true }))

    expect(toggleViewer).toHaveBeenCalledTimes(1)
    wrapper.unmount()
  })

  it('stops listening for keyboard shortcuts after unmount', async () => {
    const wrapper = mount(App, { global: { stubs } })
    await flushPromises()
    wrapper.unmount()

    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'L', ctrlKey: true, shiftKey: true }))

    expect(toggleViewer).not.toHaveBeenCalled()
  })
})
