/**
 * MessageSnackbar Component Tests
 *
 * The snackbar teleports to document.body, so content is asserted there.
 *
 * @see src/components/MessageSnackbar.vue
 */

import { describe, it, expect, afterEach } from 'vitest'
import { mount, type VueWrapper } from '@vue/test-utils'
import MessageSnackbar from '../MessageSnackbar.vue'
import { installVisualViewport } from './overlay-env'

installVisualViewport()

const mounted: VueWrapper[] = []

function mountSnackbar(props: Record<string, unknown>) {
  const wrapper = mount(MessageSnackbar, { props, attachTo: document.body })
  mounted.push(wrapper)
  return wrapper
}

function findButton(text: string): HTMLButtonElement | undefined {
  return Array.from(document.querySelectorAll('button')).find(b => b.textContent?.includes(text))
}

describe('MessageSnackbar', () => {
  afterEach(() => {
    mounted.splice(0).forEach(w => w.unmount())
    document.body.innerHTML = ''
  })

  it('renders the message when visible', () => {
    mountSnackbar({ modelValue: true, message: 'Gene saved' })

    expect(document.body.textContent).toContain('Gene saved')
  })

  it('picks the icon from the color', () => {
    mountSnackbar({ modelValue: true, message: 'ok', color: 'success' })

    expect(document.body.innerHTML).toContain('mdi-check-circle')
  })

  it('falls back to the info icon for unknown colors', () => {
    mountSnackbar({ modelValue: true, message: 'hi', color: 'purple' })

    expect(document.body.innerHTML).toContain('mdi-information')
  })

  it('updates the icon when the color prop changes', async () => {
    const wrapper = mountSnackbar({ modelValue: true, message: 'x', color: 'info' })

    await wrapper.setProps({ color: 'error' })

    expect(document.body.innerHTML).toContain('mdi-alert-circle')
  })

  it('closes on the Close button and emits close and update:modelValue', async () => {
    const wrapper = mountSnackbar({ modelValue: true, message: 'x' })

    findButton('Close')?.click()
    await wrapper.vm.$nextTick()

    expect(wrapper.emitted('close')).toHaveLength(1)
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([false])
  })

  it('hides when the modelValue prop turns false', async () => {
    const wrapper = mountSnackbar({ modelValue: true, message: 'x' })

    await wrapper.setProps({ modelValue: false })

    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([false])
  })
})
