/**
 * ErrorBoundary Component Tests
 *
 * @see src/components/ErrorBoundary.vue
 */

import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount, type VueWrapper } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import ErrorBoundary from '../ErrorBoundary.vue'

const logger = vi.hoisted(() => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }))
vi.mock('@/composables/useLogger', () => ({ useLogger: () => logger }))

const router = vi.hoisted(() => ({ push: vi.fn() }))
vi.mock('vue-router', () => ({ useRouter: () => router }))

// Child that throws while `broken.value` is true, so tests can recover it.
const broken = vi.hoisted(() => ({ value: true }))
const Child = defineComponent({
  name: 'BoundaryChild',
  render() {
    if (broken.value) throw new Error('boom')
    return h('p', { class: 'child-ok' }, 'child ok')
  }
})

let wrapper: VueWrapper | undefined

// Errors are captured during mount, and the boundary re-renders on the next tick.
async function mountBoundary() {
  wrapper = mount(ErrorBoundary, { slots: { default: () => h(Child) } })
  await wrapper.vm.$nextTick()
  return wrapper
}

async function clickButton(text: string) {
  const button = wrapper?.findAll('button').find(b => b.text().includes(text))
  await button?.trigger('click')
  await wrapper?.vm.$nextTick()
}

describe('ErrorBoundary', () => {
  afterEach(() => {
    wrapper?.unmount()
    wrapper = undefined
    broken.value = true
    vi.clearAllMocks()
  })

  it('renders the slot when nothing has failed', async () => {
    broken.value = false
    await mountBoundary()

    expect(wrapper?.find('.child-ok').exists()).toBe(true)
    expect(wrapper?.find('.error-boundary').exists()).toBe(false)
  })

  it('shows the error and logs it when a child throws', async () => {
    await mountBoundary()

    expect(wrapper?.text()).toContain('Something went wrong')
    expect(wrapper?.text()).toContain('boom')
    expect(logger.error).toHaveBeenCalledWith(
      'Component error boundary caught error',
      expect.objectContaining({ error: 'boom', component: 'BoundaryChild' })
    )
  })

  it('offers development stack details', async () => {
    await mountBoundary()

    expect(wrapper?.text()).toContain('Error Details (Development Only)')
  })

  it('re-renders the slot after Try Again', async () => {
    await mountBoundary()
    broken.value = false

    await clickButton('Try again')

    expect(wrapper?.find('.child-ok').exists()).toBe(true)
    expect(logger.info).toHaveBeenCalledWith('Error boundary reset')
  })

  it('navigates to the dashboard from Go to Dashboard', async () => {
    await mountBoundary()

    await clickButton('Go to dashboard')

    expect(router.push).toHaveBeenCalledWith('/dashboard')
    expect(logger.info).toHaveBeenCalledWith('Error boundary - navigated to dashboard')
  })

  it('does not offer a Report Issue button that only logs', async () => {
    const wrapper = await mountBoundary()

    expect(wrapper.text()).not.toContain('Report Issue')
  })
})
