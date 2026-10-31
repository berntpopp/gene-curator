/**
 * Tests for DynamicField's per-type rendering, hints, help links and the
 * component registry fallback.
 *
 * @see src/components/dynamic/DynamicField.vue
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, type VueWrapper } from '@vue/test-utils'
import DynamicField from '../DynamicField.vue'
import type { FieldSchema } from '../types'

vi.mock('@/composables/useLogger', () => ({
  useLogger: () => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() })
}))

vi.mock('../componentRegistry', () => ({
  fieldTypes: {},
  componentRegistry: {
    KnownWidget: { name: 'KnownWidget', template: '<div class="known-widget" />' }
  }
}))

const stubs = {
  'v-text-field': {
    name: 'VTextField',
    props: ['modelValue', 'label', 'hint', 'type', 'errorMessages'],
    emits: ['update:modelValue', 'blur'],
    template:
      '<div class="text-field-stub"><slot name="prepend-inner" /><slot name="append-inner" /><slot name="details" /></div>'
  },
  'v-textarea': {
    name: 'VTextarea',
    props: ['modelValue', 'label', 'rows'],
    emits: ['update:modelValue', 'blur'],
    template: '<div class="textarea-stub"><slot name="details" /></div>'
  },
  'v-select': {
    name: 'VSelect',
    props: ['modelValue', 'items', 'label'],
    emits: ['update:modelValue'],
    template: '<div class="select-stub" />'
  },
  'v-checkbox': {
    name: 'VCheckbox',
    props: ['modelValue', 'label', 'hint'],
    emits: ['update:modelValue'],
    template: '<div class="checkbox-stub" />'
  },
  'v-tooltip': { template: '<div><slot name="activator" :props="{}" /><slot /></div>' },
  'v-icon': {
    name: 'VIcon',
    props: ['icon'],
    template: '<span v-bind="$attrs" :data-icon="icon"><slot /></span>'
  },
  'v-label': { template: '<label><slot /></label>' },
  'v-card': { template: '<div><slot /></div>' },
  'v-card-text': { template: '<div><slot /></div>' },
  'v-row': { template: '<div><slot /></div>' },
  'v-col': { template: '<div><slot /></div>' },
  'v-btn': { template: '<button v-bind="$attrs"><slot /></button>' },
  'v-alert': { template: '<div class="alert-stub"><slot /></div>' }
}

function mountField(fieldSchema: FieldSchema, props: Record<string, unknown> = {}) {
  return mount(DynamicField, {
    props: { fieldName: 'sample_field', fieldSchema, ...props },
    global: { stubs }
  })
}

const hasComponent = (wrapper: VueWrapper, name: string) => wrapper.findComponent({ name }).exists()

describe('DynamicField field types', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders plain strings as a text field with a title-cased label', () => {
    const wrapper = mountField({ type: 'string' })

    expect(hasComponent(wrapper, 'VTextField')).toBe(true)
    expect(wrapper.findComponent({ name: 'VTextField' }).props('label')).toBe('Sample Field')
  })

  it('renders multiline strings as a textarea', () => {
    const wrapper = mountField({ type: 'string', multiline: true })

    expect(hasComponent(wrapper, 'VTextarea')).toBe(true)
  })

  it('renders enumerated strings as a select built from enumOptions', () => {
    const wrapper = mountField({
      type: 'string',
      enum: ['a', 'b'],
      enumOptions: [{ label: 'Alpha', value: 'a' }, 'b']
    })

    expect(hasComponent(wrapper, 'VSelect')).toBe(true)
    expect(wrapper.findComponent({ name: 'VSelect' }).props('items')).toEqual([
      { title: 'Alpha', value: 'a' },
      { title: 'B', value: 'b' }
    ])
  })

  it('builds select items from enum values when no enumOptions are given', () => {
    const wrapper = mountField({ type: 'string', enum: ['x'] })

    expect(wrapper.findComponent({ name: 'VSelect' }).props('items')).toEqual([
      { title: 'X', value: 'x' }
    ])
  })

  it('humanizes the value of an enumOptions object that has no label', () => {
    const wrapper = mountField({
      type: 'string',
      enum: ['unknown'],
      enumOptions: [{ value: 'unknown' } as never]
    })
    expect(wrapper.findComponent({ name: 'VSelect' }).props('items')).toEqual([
      { title: 'Unknown', value: 'unknown' }
    ])
  })

  it('humanizes plain lowercase and slashed enum values', () => {
    const wrapper = mountField({
      type: 'string',
      enum: ['mitochondrial', 'lump/split/undecided']
    })

    expect(
      wrapper
        .findComponent({ name: 'VSelect' })
        .props('items')
        .map((i: { title: string }) => i.title)
    ).toEqual(['Mitochondrial', 'Lump/split/undecided'])
  })

  it('titles snake_case enum values readably and keeps the stored value', () => {
    const wrapper = mountField({ type: 'string', enum: ['autosomal_dominant', 'AD'] })

    expect(wrapper.findComponent({ name: 'VSelect' }).props('items')).toEqual([
      { title: 'Autosomal dominant', value: 'autosomal_dominant' },
      { title: 'AD', value: 'AD' }
    ])
  })

  it('renders numbers and integers as numeric text fields', () => {
    const wrapper = mountField({ type: 'integer', minimum: 0, maximum: 9 })

    expect(wrapper.findComponent({ name: 'VTextField' }).props('type')).toBe('number')
  })

  it('renders booleans as a checkbox', () => {
    const wrapper = mountField({ type: 'boolean' })

    expect(hasComponent(wrapper, 'VCheckbox')).toBe(true)
  })

  it('asks a required boolean as Yes / No so No is an answer (monkey B14)', async () => {
    const wrapper = mountField({ type: 'boolean', required: true, title: 'Curated by ClinGen' })

    expect(hasComponent(wrapper, 'VCheckbox')).toBe(false)
    const radios = wrapper.findAll('input[type="radio"]')
    expect(radios).toHaveLength(2)
    await radios[1]!.setValue(true)
    expect(wrapper.emitted('update:model-value')?.at(-1)).toEqual([false])
  })

  it('renders date-formatted strings as a native date input', () => {
    const wrapper = mountField({ type: 'string', format: 'date' })

    expect(wrapper.findComponent({ name: 'VTextField' }).props('type')).toBe('date')
  })

  it('shows a fallback text field for unsupported types', () => {
    const wrapper = mountField({ type: 'weird' })

    expect(wrapper.findComponent({ name: 'VTextField' }).props('label')).toBe(
      'Sample Field (Unknown Type: weird)'
    )
    expect(wrapper.findComponent({ name: 'VTextField' }).props('hint')).toContain(
      'Field type not recognized'
    )
  })

  it('warns instead of nesting once the maximum depth is reached', () => {
    const wrapper = mountField({ type: 'object', properties: {} }, { depth: 10 })

    expect(wrapper.find('.alert-stub').text()).toContain(
      'Maximum nesting depth reached (10 levels)'
    )
  })

  it('shows the schema description when there is no hint', () => {
    const wrapper = mountField({ type: 'boolean', description: 'Explains the flag' })

    expect(wrapper.text()).toContain('Explains the flag')
  })

  it('renders a registered custom component by name', () => {
    const wrapper = mountField({ type: 'string', component: 'KnownWidget' })

    expect(wrapper.find('.known-widget').exists()).toBe(true)
  })

  it('falls back and reports an unknown custom component', () => {
    const wrapper = mountField({ type: 'string', component: 'MissingWidget' })

    expect(wrapper.emitted('component-fallback')).toEqual([
      [
        {
          requestedComponent: 'MissingWidget',
          fieldName: 'sample_field',
          fallbackType: 'text-field'
        }
      ]
    ])
  })

  it('emits the value and clears the backend error on input', () => {
    const wrapper = mountField({ type: 'string' })

    wrapper.findComponent({ name: 'VTextField' }).vm.$emit('update:modelValue', 'typed')

    expect(wrapper.emitted('update:model-value')![0]).toEqual(['typed'])
    expect(wrapper.emitted('clear-backend-error')).toHaveLength(1)
  })

  it('emits validate with the input value on blur', () => {
    const wrapper = mountField({ type: 'string' })

    wrapper
      .findComponent({ name: 'VTextField' })
      .vm.$emit('blur', { target: { value: 'left' } } as unknown as FocusEvent)

    expect(wrapper.emitted('validate')).toEqual([['left']])
  })

  it('shows backend errors in preference to validation results', () => {
    const wrapper = mountField(
      { type: 'string' },
      {
        backendErrors: ['Backend says no'],
        validationResult: { errors: [{ message: 'Client says no' }] }
      }
    )

    expect(wrapper.findComponent({ name: 'VTextField' }).props('errorMessages')).toEqual([
      'Backend says no'
    ])
  })

  it('reads validation messages when no backend errors exist', () => {
    const wrapper = mountField(
      { type: 'string' },
      { validationResult: { errors: [{ message: 'Client says no' }] } }
    )

    expect(wrapper.findComponent({ name: 'VTextField' }).props('errorMessages')).toEqual([
      'Client says no'
    ])
  })

  describe('hints', () => {
    const longHint = 'x'.repeat(120)

    it('truncates long hints and expands them on request', async () => {
      const wrapper = mountField({ type: 'string', hint: longHint })

      expect(wrapper.text()).toContain(`${'x'.repeat(100)}...`)
      expect(wrapper.text()).toContain('show more')

      await wrapper.find('a').trigger('click')
      expect(wrapper.text()).toContain(longHint)
      expect(wrapper.text()).toContain('show less')
    })

    it('keeps short hints in full', () => {
      const wrapper = mountField({ type: 'string', hint: 'Short hint' })

      expect(wrapper.findComponent({ name: 'VTextField' }).props('hint')).toBe('Short hint')
    })
  })

  describe('tooltips and help links', () => {
    it('shows an info icon when only a tooltip is defined', () => {
      const wrapper = mountField({ type: 'string', tooltip: 'More info' })

      expect(wrapper.html()).toContain('mdi-information-outline')
    })

    it('opens a valid help URL in a new tab', async () => {
      const open = vi.spyOn(window, 'open').mockImplementation(() => null)
      const wrapper = mountField({
        type: 'string',
        helpUrl: 'https://example.org/help'
      })

      const helpIcon = wrapper
        .findAllComponents({ name: 'VIcon' })
        .find(icon => icon.props('icon') === 'mdi-help-circle-outline')
      await helpIcon!.trigger('click')

      expect(open).toHaveBeenCalledWith('https://example.org/help', '_blank', 'noopener,noreferrer')
    })

    it('does not offer a help link for non-http URLs', () => {
      const wrapper = mountField({ type: 'string', helpUrl: 'javascript:alert(1)' })

      expect(
        wrapper
          .findAllComponents({ name: 'VIcon' })
          .some(icon => icon.props('icon') === 'mdi-help-circle-outline')
      ).toBe(false)
    })

    it('offers a help link on boolean fields too', () => {
      const wrapper = mountField({ type: 'boolean', helpUrl: 'https://example.org' })

      expect(
        wrapper
          .findAllComponents({ name: 'VIcon' })
          .some(icon => icon.props('icon') === 'mdi-help-circle-outline')
      ).toBe(true)
    })
  })
})
