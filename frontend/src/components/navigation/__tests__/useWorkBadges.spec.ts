import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useWorkCountsStore } from '@/stores/workCounts'
import { usePrecurationsStore } from '@/stores/precurations'
import { useWorkBadges } from '../useWorkBadges'

vi.mock('@/api/precurations', () => ({
  precurationsAPI: {
    approvePrecuration: vi.fn().mockResolvedValue({ id: 'p1' }),
    getPrecurations: vi.fn().mockRejectedValue(new Error('x'))
  }
}))
const component = { render: () => null }

function setup() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component },
      { path: '/x', component }
    ]
  })
  const wrapper = mount(defineComponent({ setup: () => (useWorkBadges(), () => h('div')) }), {
    global: { plugins: [router] }
  })
  return { router, wrapper }
}

describe('useWorkBadges', () => {
  let fetch: ReturnType<typeof vi.fn>

  beforeEach(() => {
    vi.useFakeTimers()
    setActivePinia(createPinia())
    fetch = vi.spyOn(useWorkCountsStore(), 'fetch').mockResolvedValue(undefined) as never
  })
  afterEach(() => vi.useRealTimers())

  it('does nothing for guests', async () => {
    const { wrapper } = setup()
    vi.advanceTimersByTime(120_000)
    expect(fetch).not.toHaveBeenCalled()
    wrapper.unmount()
  })

  it('fetches once on mount, then every 60 s only while the tab is visible', async () => {
    useAuthStore().isAuthenticated = true
    const { wrapper } = setup()
    expect(fetch).toHaveBeenCalledTimes(1)

    vi.advanceTimersByTime(60_000)
    expect(fetch).toHaveBeenCalledTimes(2)

    vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('hidden')
    vi.advanceTimersByTime(60_000)
    expect(fetch).toHaveBeenCalledTimes(2)

    vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('visible')
    document.dispatchEvent(new Event('visibilitychange'))
    expect(fetch).toHaveBeenCalledTimes(3)
    wrapper.unmount()
  })

  it('refreshes after navigation and precuration approve/reject, not other actions', async () => {
    useAuthStore().isAuthenticated = true
    const { wrapper, router } = setup()
    await flushPromises()
    fetch.mockClear()
    await router.push('/x')
    expect(fetch).toHaveBeenCalledTimes(1)

    const pre = usePrecurationsStore()
    await pre.approvePrecuration('p1')
    await flushPromises()
    expect(fetch).toHaveBeenCalledTimes(2)

    await pre.fetchPrecurations().catch(() => undefined)
    expect(fetch).toHaveBeenCalledTimes(2)
    wrapper.unmount()
  })

  it('stops polling, drops listeners and resets counts on unmount or sign-out', async () => {
    const auth = useAuthStore()
    auth.isAuthenticated = true
    const reset = vi.spyOn(useWorkCountsStore(), 'reset')
    const { wrapper } = setup()
    await flushPromises()
    fetch.mockClear()

    auth.isAuthenticated = false
    await flushPromises()
    expect(reset).toHaveBeenCalled()
    vi.advanceTimersByTime(120_000)
    expect(fetch).not.toHaveBeenCalled()

    auth.isAuthenticated = true
    await flushPromises()
    expect(fetch).toHaveBeenCalledTimes(1)
    wrapper.unmount()
    vi.advanceTimersByTime(120_000)
    expect(fetch).toHaveBeenCalledTimes(1)
  })
})
