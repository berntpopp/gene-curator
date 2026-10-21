/**
 * DisclaimerDialog Component Tests
 *
 * @see src/components/DisclaimerDialog.vue
 */

import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest'
import { mount, type VueWrapper } from '@vue/test-utils'
import DisclaimerDialog from '../DisclaimerDialog.vue'

const logger = vi.hoisted(() => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }))
vi.mock('@/composables/useLogger', () => ({ useLogger: () => logger }))

const ACCEPT_LABEL = 'Accept disclaimer and continue to application'

describe('DisclaimerDialog', () => {
  let wrapper: VueWrapper | undefined

  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    wrapper?.unmount()
    wrapper = undefined
    document.body.innerHTML = ''
    vi.useRealTimers()
    vi.clearAllMocks()
  })

  function mountDialog(props: Record<string, unknown> = { modelValue: true }) {
    wrapper = mount(DisclaimerDialog, { props, attachTo: document.body })
    return wrapper
  }

  it('shows the research-use disclaimer when open', () => {
    mountDialog()

    expect(document.body.textContent).toContain('Research Use Disclaimer')
    expect(document.body.textContent).toContain('NOT a clinical diagnostic tool')
  })

  it('acknowledges immediately and closes', async () => {
    const w = mountDialog()
    const button = document.querySelector<HTMLButtonElement>(`[aria-label="${ACCEPT_LABEL}"]`)

    button?.click()
    await w.vm.$nextTick()

    expect(w.emitted('acknowledged')).toHaveLength(1)
    expect(w.emitted('update:modelValue')?.at(-1)).toEqual([false])
    expect(logger.info).toHaveBeenCalledWith('Disclaimer acknowledged')
  })

  it('keeps the full text behind an expansion and scrolls inside the dialog', () => {
    mountDialog()

    expect(document.querySelector('.v-dialog--scrollable')).not.toBeNull()
    expect(document.body.textContent).toContain('Full disclaimer')
    expect(document.querySelectorAll('.disclaimer-summary li')).toHaveLength(3)
  })

  it('reflects the modelValue prop in the dialog visibility', async () => {
    const w = mountDialog({ modelValue: false })

    expect(document.querySelector(`[aria-label="${ACCEPT_LABEL}"]`)).toBeNull()

    await w.setProps({ modelValue: true })

    expect(document.querySelector(`[aria-label="${ACCEPT_LABEL}"]`)).not.toBeNull()
  })
})
