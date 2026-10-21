/**
 * FormRecoveryDialog Component Tests
 *
 * @see src/components/FormRecoveryDialog.vue
 */

import { formatDate } from '@/utils/format'
import { describe, it, expect, afterEach, beforeEach, vi } from 'vitest'
import { mount, type VueWrapper } from '@vue/test-utils'
import FormRecoveryDialog from '../FormRecoveryDialog.vue'

const NOW = new Date('2026-03-10T12:00:00Z')

let wrapper: VueWrapper | undefined

function mountDialog(timestamp: string | null = null) {
  wrapper = mount(FormRecoveryDialog, {
    props: { modelValue: true, timestamp },
    attachTo: document.body
  })
  return wrapper
}

function agoMs(ms: number) {
  return new Date(NOW.getTime() - ms).toISOString()
}

function clickButton(text: string) {
  Array.from(document.querySelectorAll('button'))
    .find(b => b.textContent?.includes(text))
    ?.click()
}

describe('FormRecoveryDialog', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(NOW)
  })

  afterEach(() => {
    wrapper?.unmount()
    wrapper = undefined
    document.body.innerHTML = ''
    vi.useRealTimers()
  })

  it('omits the time without a timestamp', () => {
    mountDialog(null)

    expect(document.body.textContent).toContain('Restore unsaved changes? This replaces')
  })

  it.each([
    [30 * 1000, 'less than a minute ago'],
    [60 * 1000, '1 minute ago'],
    [5 * 60 * 1000, '5 minutes ago'],
    [60 * 60 * 1000, '1 hour ago'],
    [3 * 60 * 60 * 1000, '3 hours ago'],
    [24 * 60 * 60 * 1000, '1 day ago'],
    [3 * 24 * 60 * 60 * 1000, '3 days ago']
  ])('formats %i ms ago as "%s"', (ms, expected) => {
    mountDialog(agoMs(ms))

    expect(document.body.textContent).toContain(expected)
  })

  it('shows a calendar date for timestamps older than a week', () => {
    const old = agoMs(30 * 24 * 60 * 60 * 1000)
    mountDialog(old)

    expect(document.body.textContent).toContain(formatDate(old))
  })

  it('emits restore and discard from the action buttons', () => {
    const w = mountDialog(null)

    clickButton('Discard')
    clickButton('Restore')

    expect(w.emitted('discard')).toHaveLength(1)
    expect(w.emitted('restore')).toHaveLength(1)
  })
})
