import { describe, it, expect, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import ConfirmDialog from '../ConfirmDialog.vue'
import { useConfirm } from '@/composables/useConfirm'

const BaseDialog = {
  props: ['modelValue', 'title', 'size', 'persistent'],
  emits: ['update:modelValue', 'cancel'],
  template:
    '<div v-if="modelValue" class="dlg"><h1>{{ title }}</h1><slot /><slot name="actions" /></div>'
}

describe('ConfirmDialog', () => {
  afterEach(() => {
    document.body.innerHTML = ''
  })

  const mountDialog = () =>
    mount(ConfirmDialog, { global: { stubs: { BaseDialog } }, attachTo: document.body })

  it('resolves true when the confirm button is clicked', async () => {
    const wrapper = mountDialog()
    const result = useConfirm().confirm({ title: 'Delete?', text: 'Gone.', confirmText: 'Remove' })
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('Delete?')
    expect(wrapper.text()).toContain('Gone.')
    await wrapper
      .findAll('button')
      .find(b => b.text() === 'Remove')!
      .trigger('click')

    expect(await result).toBe(true)
  })

  it('resolves false on Cancel and on Escape', async () => {
    const wrapper = mountDialog()
    const viaButton = useConfirm().confirm({ title: 'A' })
    await wrapper.vm.$nextTick()
    await wrapper
      .findAll('button')
      .find(b => b.text() === 'Cancel')!
      .trigger('click')
    expect(await viaButton).toBe(false)

    const viaEscape = useConfirm().confirm({ title: 'B' })
    await wrapper.vm.$nextTick()
    wrapper.findComponent(BaseDialog).vm.$emit('cancel')
    expect(await viaEscape).toBe(false)
  })

  it('colors the confirm button error when destructive', async () => {
    const wrapper = mountDialog()
    void useConfirm().confirm({ title: 'X', destructive: true })
    await wrapper.vm.$nextTick()
    expect(wrapper.findAll('button').at(-1)!.classes().join(' ')).toContain('error')
  })
})
