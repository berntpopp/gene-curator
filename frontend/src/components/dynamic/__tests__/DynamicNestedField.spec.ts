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

// A stable id lets review diffs and anchored comments follow a row when others are removed
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/

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
      expect(emitted[0]![0]).toEqual([
        { id: expect.stringMatching(UUID), name: '', count: 0, flag: false, note: 'default note' }
      ])
    })

    it('appends an empty object when the array has no item properties', async () => {
      const wrapper = mountField({ fieldSchema: { type: 'array' }, modelValue: [] })

      await wrapper.findAll('button').at(-1)!.trigger('click')

      expect(wrapper.emitted('update:model-value')![0]![0]).toEqual([
        { id: expect.stringMatching(UUID) }
      ])
    })

    it('gives every new item its own id', async () => {
      const wrapper = mountField({ fieldSchema: arraySchema, modelValue: [] })
      const add = wrapper.findAll('button').at(-1)!

      await add.trigger('click')
      await add.trigger('click')

      const [first, second] = wrapper.emitted('update:model-value')!.at(-1)![0] as { id: string }[]
      expect(first!.id).not.toBe(second!.id)
    })

    it('leaves the ids of existing items alone', async () => {
      const wrapper = mountField({
        fieldSchema: arraySchema,
        modelValue: [{ id: 'keep-me', name: 'A' }]
      })

      await wrapper.findAll('button').at(-1)!.trigger('click')

      const [kept] = wrapper.emitted('update:model-value')![0]![0] as { id: string }[]
      expect(kept!.id).toBe('keep-me')
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

      expect(wrapper.find('.text-error.text-body-small').text()).toBe('Too short, Missing')
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

      expect(wrapper.find('.text-error.text-body-small').text()).toBe('Invalid')
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

describe('DynamicNestedField MONDO pick', () => {
  const disease = {
    mondo_id: { type: 'string', component: 'MONDOAutocomplete' },
    disease_name: { type: 'string' }
  } as Record<string, FieldSchema>
  const pick = (w: VueWrapper, name: string) =>
    w.findAllComponents({ name: 'DynamicField' })[0]!.vm.$emit('update:disease-name', name)

  it('fills the sibling disease name of a nested object, as the top level does', () => {
    const w = mountField({
      fieldSchema: { type: 'object', properties: disease },
      modelValue: { mondo_id: 'MONDO:1', disease_name: 'old' }
    })
    pick(w, '')
    expect(w.emitted('update:model-value')).toBeUndefined() // a cleared term keeps the name
    pick(w, 'Alport syndrome')
    expect(w.emitted('update:model-value')!.at(-1)![0]).toMatchObject({
      disease_name: 'Alport syndrome'
    })
  })

  it('fills the disease name of the array row the term was picked in', () => {
    const w = mountField({
      fieldSchema: { type: 'array', items: { properties: disease } },
      modelValue: [{ mondo_id: 'MONDO:1' }]
    })
    pick(w, 'Alport syndrome')
    expect(w.emitted('update:model-value')!.at(-1)![0]).toEqual([
      { mondo_id: 'MONDO:1', disease_name: 'Alport syndrome' }
    ])
  })

  it('leaves objects without a disease name field alone', () => {
    const w = mountField({
      fieldSchema: { type: 'object', properties: { mondo_id: disease.mondo_id! } }
    })
    pick(w, 'Alport syndrome')
    expect(w.emitted('update:model-value')).toBeUndefined()
  })
})
