/**
 * SessionTimeoutWarning Component Tests
 *
 * @see src/components/SessionTimeoutWarning.vue
 */

import { describe, it, expect, afterEach } from 'vitest'
import { mount, type VueWrapper } from '@vue/test-utils'
import SessionTimeoutWarning from '../SessionTimeoutWarning.vue'
import { installVisualViewport } from './overlay-env'

installVisualViewport()

let wrapper: VueWrapper | undefined

function mountWarning(timeRemaining: number) {
  wrapper = mount(SessionTimeoutWarning, {
    props: { modelValue: true, timeRemaining },
    attachTo: document.body
  })
  return wrapper
}

function clickButton(text: string) {
  Array.from(document.querySelectorAll('button'))
    .find(b => b.textContent?.includes(text))
    ?.click()
}

describe('SessionTimeoutWarning', () => {
  afterEach(() => {
    wrapper?.unmount()
    wrapper = undefined
    document.body.innerHTML = ''
  })

  it('formats the remaining time as m:ss', () => {
    mountWarning(125)

    expect(document.body.textContent).toContain('2:05')
  })

  it('warns about unsaved changes when under two minutes remain', () => {
    mountWarning(90)

    expect(document.body.textContent).toContain('Unsaved changes will be lost')
  })

  it('does not show the data-loss warning with more than two minutes left', () => {
    mountWarning(300)

    expect(document.body.textContent).not.toContain('Unsaved changes will be lost')
  })

  it('emits extend and dismiss from the action buttons', async () => {
    const w = mountWarning(60)

    clickButton('Extend Session')
    clickButton('Dismiss')
    await w.vm.$nextTick()

    expect(w.emitted('extend')).toHaveLength(1)
    expect(w.emitted('dismiss')).toHaveLength(1)
  })
})
