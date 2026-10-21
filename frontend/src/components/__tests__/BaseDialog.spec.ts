import { describe, it, expect, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import BaseDialog from '../BaseDialog.vue'

// Stub keeps the v-dialog contract (after-leave event, attrs fall through) without teleport/transition.
const VDialog = {
  props: ['modelValue', 'maxWidth', 'persistent'],
  emits: ['after-leave'],
  template: '<div v-if="modelValue" class="dlg"><slot /></div>'
}

describe('BaseDialog', () => {
  afterEach(() => {
    document.body.innerHTML = ''
  })

  const mountDialog = (props: Record<string, unknown> = {}) =>
    mount(BaseDialog, {
      props: { modelValue: false, ...props },
      slots: { default: 'Body', actions: '<button>Go</button>' },
      global: { stubs: { VDialog } },
      attachTo: document.body
    })

  it('returns focus to the opener after close', async () => {
    const opener = document.createElement('button')
    document.body.appendChild(opener)
    opener.focus()
    const wrapper = mountDialog()

    await wrapper.setProps({ modelValue: true })
    ;(document.activeElement as HTMLElement).blur()
    await wrapper.setProps({ modelValue: false })
    wrapper.findComponent(VDialog).vm.$emit('after-leave')

    expect(document.activeElement).toBe(opener)
  })

  it('emits cancel on Escape even when persistent', async () => {
    const wrapper = mountDialog({ modelValue: true, persistent: true })

    await wrapper.find('.dlg').trigger('keydown', { key: 'Escape' })

    expect(wrapper.emitted('cancel')).toHaveLength(1)
  })

  it('maps size to width and renders title and actions', () => {
    const wrapper = mountDialog({ modelValue: true, size: 'lg', title: 'Edit' })

    expect(wrapper.findComponent(VDialog).props('maxWidth')).toBe(800)
    expect(wrapper.text()).toContain('Edit')
    expect(wrapper.text()).toContain('Go')
  })
})
