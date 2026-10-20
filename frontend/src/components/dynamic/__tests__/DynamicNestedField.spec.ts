/**
 * Tests for DynamicNestedField (object and array fields of the form engine).
 *
 * @see src/components/dynamic/DynamicNestedField.vue
 */

import { describe, it, expect } from 'vitest'
import { mount, type VueWrapper } from '@vue/test-utils'
import DynamicNestedField from '../DynamicNestedField.vue'
import type { FieldSchema } from '../types'

const stubs = {
  DynamicField: {
    name: 'DynamicField',
    props: ['fieldName', 'fieldSchema', 'modelValue', 'depth', 'variant', 'disabled'],
    template: '<div class="stub-field" />'
  },
  'v-label': { template: '<label><slot /></label>' },
  'v-card': { template: '<div><slot /></div>' },
  'v-card-text': { template: '<div><slot /></div>' },
  'v-row': { template: '<div><slot /></div>' },
  'v-col': { template: '<div><slot /></div>' },
  'v-btn': { template: '<button v-bind="$attrs"><slot /></button>' },
  'v-icon': { template: '<span />' }
}

interface MountProps {
  fieldSchema: FieldSchema
  label?: string
  modelValue?: unknown
  depth?: number
  disabled?: boolean
  errorMessages?: string[]
}

function mountField(props: MountProps): VueWrapper {
  return mount(DynamicNestedField, {
    props: {
      label: 'Section',
      depth: 0,
      errorMessages: [],
      ...props
    },
    global: { stubs }
  })
}

const arraySchema: FieldSchema = {
  type: 'array',
  title: 'Genes',
  items: {
    properties: {
      name: { type: 'string' },
      count: { type: 'integer' },
      flag: { type: 'boolean' },
      note: { type: 'string', default: 'default note' }
    }
  }
}

const objectSchema: FieldSchema = {
  type: 'object',
  title: 'Address',
  properties: {
    street: { type: 'string' },
    city: { type: 'string' },
    zip: { type: 'string' }
  }
}

describe('DynamicNestedField', () => {
  describe('array fields', () => {
    it('shows the empty state when there are no items', () => {
      const wrapper = mountField({ fieldSchema: arraySchema, label: 'Genes' })

      expect(wrapper.text()).toContain('No items added yet')
      expect(wrapper.text()).toContain('Genes')
    })

    it('renders one block per item and a field per item property', () => {
      const wrapper = mountField({
        fieldSchema: arraySchema,
        modelValue: [{ name: 'A' }, { name: 'B' }]
      })

      expect(wrapper.findAll('h4').map(h => h.text())).toEqual(['Item 1', 'Item 2'])
      expect(wrapper.findAllComponents({ name: 'DynamicField' })).toHaveLength(8)
    })

    it('marks required arrays with an asterisk', () => {
      const wrapper = mountField({ fieldSchema: { ...arraySchema, required: true } })

      expect(wrapper.find('.text-error').text()).toBe('*')
    })

    it('appends an item initialised from the property defaults', async () => {
      const wrapper = mountField({ fieldSchema: arraySchema, modelValue: [] })

      await wrapper.findAll('button').at(-1)!.trigger('click')

      const emitted = wrapper.emitted('update:model-value')!
      expect(emitted[0]![0]).toEqual([{ name: '', count: 0, flag: false, note: 'default note' }])
    })

    it('appends an empty object when the array has no item properties', async () => {
      const wrapper = mountField({ fieldSchema: { type: 'array' }, modelValue: [] })

      await wrapper.findAll('button').at(-1)!.trigger('click')

      expect(wrapper.emitted('update:model-value')![0]![0]).toEqual([{}])
    })

    it('removes an item when its delete button is clicked', async () => {
      const wrapper = mountField({
        fieldSchema: arraySchema,
        modelValue: [{ name: 'A' }, { name: 'B' }]
      })

      await wrapper.findAll('button').at(0)!.trigger('click')

      expect(wrapper.emitted('update:model-value')![0]![0]).toEqual([{ name: 'B' }])
    })

    it('emits the whole array when a sub-field changes', () => {
      const wrapper = mountField({
        fieldSchema: arraySchema,
        modelValue: [{ name: 'A' }, { name: 'B' }]
      })

      wrapper
        .findAllComponents({ name: 'DynamicField' })[0]!
        .vm.$emit('update:model-value', 'Renamed')

      expect(wrapper.emitted('update:model-value')![0]![0]).toEqual([
        { name: 'Renamed' },
        { name: 'B' }
      ])
    })

    it('shows validation messages below the block', () => {
      const wrapper = mountField({
        fieldSchema: arraySchema,
        errorMessages: ['Too short', 'Missing']
      })

      expect(wrapper.find('.text-error.text-caption').text()).toBe('Too short, Missing')
    })

    it('reloads its items when the model value changes from outside', async () => {
      const wrapper = mountField({ fieldSchema: arraySchema, modelValue: [] })

      await wrapper.setProps({ modelValue: [{ name: 'Z' }] })

      expect(wrapper.findAll('h4').map(h => h.text())).toEqual(['Item 1'])
    })
  })

  describe('object fields', () => {
    it('renders one child field per property', () => {
      const wrapper = mountField({ fieldSchema: objectSchema, label: 'Address' })

      expect(wrapper.text()).toContain('Address')
      expect(wrapper.findAllComponents({ name: 'DynamicField' })).toHaveLength(3)
    })

    it('emits the merged object when a child field changes', () => {
      const wrapper = mountField({
        fieldSchema: objectSchema,
        modelValue: { street: 'Old', city: 'Berlin' }
      })

      wrapper
        .findAllComponents({ name: 'DynamicField' })[0]!
        .vm.$emit('update:model-value', 'Main St')

      expect(wrapper.emitted('update:model-value')![0]![0]).toEqual({
        street: 'Main St',
        city: 'Berlin'
      })
    })

    it('passes the current value of each property to its child field', async () => {
      const wrapper = mountField({ fieldSchema: objectSchema, modelValue: { street: 'A' } })

      expect(wrapper.findAllComponents({ name: 'DynamicField' })[0]!.props('modelValue')).toBe('A')

      await wrapper.setProps({ modelValue: { street: 'B' } })

      expect(wrapper.findAllComponents({ name: 'DynamicField' })[0]!.props('modelValue')).toBe('B')
    })

    it('shows validation messages below the block', () => {
      const wrapper = mountField({ fieldSchema: objectSchema, errorMessages: ['Invalid'] })

      expect(wrapper.find('.text-error.text-caption').text()).toBe('Invalid')
    })
  })

  describe('nesting depth', () => {
    it('applies no tint at shallow depths', () => {
      const wrapper = mountField({ fieldSchema: objectSchema, depth: 1 })

      expect(wrapper.html()).not.toContain('transition: background-color')
    })

    it('tints deeper levels progressively', () => {
      const wrapper = mountField({ fieldSchema: objectSchema, depth: 3 })

      expect(wrapper.html()).toContain('background-color 0.2s ease')
    })
  })
})
