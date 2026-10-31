/** Synopsis field picker: one select over the text fields, stored in ui_configuration. */
import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { VSelect } from 'vuetify/components/VSelect'
import FieldsEditor from '../FieldsEditor.vue'

vi.mock('@/composables/useConfirm', () => ({ useConfirm: () => ({ confirm: vi.fn() }) }))

const fields = {
  sections: [
    {
      id: 'main',
      label: 'Main',
      fields: [
        { id: 'evidence_summary', type: 'textarea', label: 'Evidence summary' },
        { id: 'points', type: 'number' }
      ]
    }
  ]
}

describe('FieldsEditor synopsis field', () => {
  it('offers text fields only and sets or clears synopsis_field', async () => {
    const wrapper = mount(FieldsEditor, {
      props: { modelValue: fields, uiConfiguration: { tabs: ['x'] } },
      attachTo: document.body
    })
    await flushPromises()
    const select = wrapper.findComponent(VSelect)
    expect(select.props('items')).toEqual([
      { value: 'evidence_summary', title: 'Evidence summary' }
    ])
    select.vm.$emit('update:modelValue', 'evidence_summary')
    select.vm.$emit('update:modelValue', null)
    expect(wrapper.emitted('update:uiConfiguration')).toEqual([
      [{ tabs: ['x'], synopsis_field: 'evidence_summary' }],
      [{ tabs: ['x'] }]
    ])
    wrapper.unmount()
  })
})
