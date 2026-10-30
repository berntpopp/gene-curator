/** Top-level list fields (multiselect, array of plain values) render a multi-value input, not the unknown-type fallback */
import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import DynamicField from '../DynamicField.vue'
import { normalizeField } from '../normalizeDefinition'

vi.mock('@/composables/useLogger', () => ({
  useLogger: () => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() })
}))

const mountField = (raw: Parameters<typeof normalizeField>[0], modelValue: unknown = []) =>
  mount(DynamicField, { props: { fieldName: 'f', fieldSchema: normalizeField(raw), modelValue } })

describe('DynamicField list types', () => {
  it('renders a multiselect as a multiple select of its options', async () => {
    const wrapper = mountField(
      {
        type: 'multiselect',
        label: 'Audiences',
        options: [
          { value: 'patients', label: 'Patients' },
          { value: 'clinicians', label: 'Clinicians' }
        ]
      },
      ['patients']
    )
    expect(wrapper.text()).not.toContain('Unknown Type')
    const select = wrapper.findComponent({ name: 'VSelect' })
    expect(select.exists()).toBe(true)
    expect(select.props('multiple')).toBe(true)
    expect(select.props('items')).toEqual([
      { title: 'Patients', value: 'patients' },
      { title: 'Clinicians', value: 'clinicians' }
    ])
    select.vm.$emit('update:modelValue', ['patients', 'clinicians'])
    expect(wrapper.emitted('update:model-value')?.[0]).toEqual([['patients', 'clinicians']])
  })

  it('renders an array without item fields as free multi-value entry', () => {
    const wrapper = mountField({ type: 'array', label: 'Tools' }, ['SpliceAI'])
    expect(wrapper.text()).not.toContain('Unknown Type')
    const box = wrapper.findComponent({ name: 'VCombobox' })
    expect(box.exists()).toBe(true)
    expect(box.props('multiple')).toBe(true)
    expect(box.props('modelValue')).toEqual(['SpliceAI'])
  })

  it('keeps arrays with item fields on the nested editor', () => {
    const wrapper = mountField({ type: 'array', item_schema: { name: { type: 'text' } } })
    expect(wrapper.findComponent({ name: 'VCombobox' }).exists()).toBe(false)
  })
})
