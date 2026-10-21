import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { myWorkAPI } from '@/api/myWork'
import { useWorkCountsStore } from '@/stores/workCounts'
import { usePrecurationsStore } from '@/stores/precurations'
import { useWorkBadges } from '../useWorkBadges'

vi.mock('@/api/myWork', () => ({
  myWorkAPI: { get: vi.fn().mockResolvedValue({ items: [], counts: { needs_you: 2 } }) }
}))
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
  const fetch = vi.mocked(myWorkAPI.get)

  beforeEach(() => {
    vi.useFakeTimers()
    setActivePinia(createPinia())
    fetch.mockClear()
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

  it('sends one request per tick however many consumers are mounted', async () => {
    useAuthStore().isAuthenticated = true
    const a = setup()
    const b = setup()
    await flushPromises()
    fetch.mockClear() // initial navigation and mount fetches

    vi.advanceTimersByTime(60_000)
    expect(fetch).toHaveBeenCalledTimes(1)

    a.wrapper.unmount() // one holder left: polling continues
    vi.advanceTimersByTime(60_000)
    expect(fetch).toHaveBeenCalledTimes(2)

    b.wrapper.unmount()
    vi.advanceTimersByTime(120_000)
    expect(fetch).toHaveBeenCalledTimes(2)
  })

  it('stops polling, drops listeners and resets counts on unmount or sign-out', async () => {
    const auth = useAuthStore()
    auth.isAuthenticated = true
    const { wrapper } = setup()
    await flushPromises()
    expect(useWorkCountsStore().needsYou).toBe(2)
    fetch.mockClear()

    auth.isAuthenticated = false
    await flushPromises()
    expect(useWorkCountsStore().needsYou).toBe(0)
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
