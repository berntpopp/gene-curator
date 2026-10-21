/**
 * Tests for DynamicForm's flat layout, submit / save-draft flows and the
 * backend validation round trip.
 *
 * @see src/components/dynamic/DynamicForm.vue
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount, flushPromises, type VueWrapper } from '@vue/test-utils'

const store = vi.hoisted(() => ({
  loading: false,
  error: null as string | null,
  schema: null as Record<string, unknown> | null,
  result: null as Record<string, unknown> | null,
  formValid: true,
  getJsonSchema: vi.fn(),
  getValidationResult: vi.fn(),
  generateJsonSchema: vi.fn(),
  validateEvidence: vi.fn(),
  validateField: vi.fn()
}))

vi.mock('@/stores', () => ({
  useValidationStore: () => store
}))

vi.mock('@/composables/useLogger', () => ({
  useLogger: () => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() })
}))

import DynamicForm from '../DynamicForm.vue'

const stubs = {
  'v-form': {
    name: 'VForm',
    template: '<form @submit.prevent="$emit(\'submit\', $event)"><slot /></form>',
    emits: ['submit'],
    methods: { validate: () => Promise.resolve({ valid: store.formValid }) }
  },
  'v-row': { template: '<div><slot /></div>' },
  'v-col': { template: '<div><slot /></div>' },
  'v-card': { template: '<div><slot /></div>' },
  'v-card-title': { template: '<div><slot /></div>' },
  'v-card-text': { template: '<div><slot /></div>' },
  'v-card-actions': { template: '<div><slot /></div>' },
  'v-spacer': { template: '<span />' },
  'v-icon': { template: '<span><slot /></span>' },
  'v-progress-circular': { template: '<span />' },
  'v-alert': { template: '<div><slot name="prepend" /><slot /></div>' },
  'v-btn': { template: '<button v-bind="$attrs"><slot /></button>' },
  'v-tabs': { template: '<div><slot /></div>' },
  'v-tab': { template: '<span><slot /></span>' },
  'v-chip': { template: '<span><slot /></span>' },
  'v-badge': { template: '<span />' },
  'v-window': { template: '<div><slot /></div>' },
  'v-window-item': { template: '<div><slot /></div>' },
  DynamicField: {
    name: 'DynamicField',
    props: ['fieldName', 'fieldSchema', 'modelValue', 'backendErrors', 'validationResult'],
    template: '<div class="field-stub" />'
  },
  ScoreDisplay: { name: 'ScoreDisplay', template: '<div class="score-stub" />' }
}

const flatSchema = {
  properties: {
    name: { type: 'string', title: 'Name' },
    age: { type: 'integer', title: 'Age' }
  }
}

function mountForm(props: Record<string, unknown> = {}) {
  return mount(DynamicForm, {
    props: { schemaId: 'schema-1', initialData: { name: 'Ada' }, ...props },
    global: { stubs }
  })
}

function fieldStub(wrapper: VueWrapper, fieldName: string) {
  const field = wrapper
    .findAllComponents({ name: 'DynamicField' })
    .find(c => c.props('fieldName') === fieldName)
  if (!field) throw new Error(`No field ${fieldName}`)
  return field
}

function buttonWithText(wrapper: VueWrapper, text: string) {
  const button = wrapper.findAll('button').find(b => b.text().includes(text))
  if (!button) throw new Error(`No button ${text}`)
  return button
}

describe('DynamicForm flow', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    store.loading = false
    store.error = null
    store.schema = flatSchema
    store.result = null
    store.formValid = true
    store.getJsonSchema.mockImplementation(() => store.schema)
    store.getValidationResult.mockImplementation(() => store.result)
    store.generateJsonSchema.mockResolvedValue(undefined)
    store.validateEvidence.mockResolvedValue(null)
    store.validateField.mockResolvedValue(undefined)
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('loads the JSON schema for its schema id on mount', async () => {
    mountForm()
    await flushPromises()

    expect(store.generateJsonSchema).toHaveBeenCalledWith('schema-1')
  })

  it('renders one field per property of a flat schema', () => {
    const wrapper = mountForm()

    expect(wrapper.findAllComponents({ name: 'DynamicField' })).toHaveLength(2)
    expect(fieldStub(wrapper, 'name').props('modelValue')).toBe('Ada')
  })

  it('hides Save Draft and Submit when readonly', () => {
    const wrapper = mountForm({ readonly: true })

    expect(wrapper.findAll('button')).toHaveLength(0)
  })

  it('says so when the schema defines no fields', () => {
    store.schema = { properties: {} }
    const wrapper = mountForm()

    expect(wrapper.text()).toContain('This schema defines no fields')
  })

  it('shows a loading message while the schema loads', () => {
    store.loading = true
    const wrapper = mountForm()

    expect(wrapper.text()).toContain('Loading form schema...')
  })

  it('shows the failure when the schema cannot be loaded', () => {
    store.schema = null
    store.error = 'not found'
    const wrapper = mountForm()

    expect(wrapper.text()).toContain('Failed to load form schema: not found')
  })

  it('enables saving a draft only after a change and emits the data', async () => {
    const wrapper = mountForm()
    expect(buttonWithText(wrapper, 'Save Draft').attributes('disabled')).toBeDefined()

    fieldStub(wrapper, 'name').vm.$emit('update:model-value', 'Grace')
    await flushPromises()
    await buttonWithText(wrapper, 'Save Draft').trigger('click')

    expect(wrapper.emitted('save-draft')![0]).toEqual([{ name: 'Grace' }])
    expect(wrapper.emitted('update:modelValue')!.at(-1)).toEqual([{ name: 'Grace' }])
  })

  it('emits submit with the form data when validation passes', async () => {
    const wrapper = mountForm()
    fieldStub(wrapper, 'age').vm.$emit('update:model-value', 36)
    await flushPromises()

    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(store.validateEvidence).toHaveBeenCalledWith(
      { name: 'Ada', age: 36 },
      'schema-1',
      'form'
    )
    expect(wrapper.emitted('submit')![0]).toEqual([{ name: 'Ada', age: 36 }])
  })

  it('does not submit when the form fails local validation', async () => {
    store.formValid = false
    const wrapper = mountForm()
    await flushPromises()
    store.validateEvidence.mockClear()

    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(wrapper.emitted('submit')).toBeUndefined()
    expect(store.validateEvidence).not.toHaveBeenCalled()
  })

  it('does not submit when the backend rejects the data', async () => {
    const rejected = { is_valid: false, errors: [{ message: 'Rejected' }] }
    store.validateEvidence.mockResolvedValue(rejected)
    store.result = rejected
    const wrapper = mountForm()
    await flushPromises()

    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(wrapper.emitted('submit')).toBeUndefined()
  })

  it('maps field-level backend errors onto the matching field', async () => {
    vi.useFakeTimers()
    store.validateEvidence.mockResolvedValue({
      is_valid: false,
      field_validations: { name: { errors: [{ message: 'Too short' }] } },
      errors: [{ field: 'name', message: 'Too short' }]
    })
    const wrapper = mountForm()

    fieldStub(wrapper, 'name').vm.$emit('update:model-value', 'A')
    await vi.advanceTimersByTimeAsync(500)
    await flushPromises()

    expect(fieldStub(wrapper, 'name').props('backendErrors')).toEqual(['Too short'])
    // Field-mapped errors are not repeated as form-level errors
    expect(wrapper.text()).not.toContain('Form Error')
  })

  it('shows errors that are not tied to a field as form-level errors', async () => {
    vi.useFakeTimers()
    store.validateEvidence.mockResolvedValue({
      is_valid: false,
      errors: [{ message: 'Record is locked' }]
    })
    const wrapper = mountForm()

    fieldStub(wrapper, 'age').vm.$emit('update:model-value', 3)
    await vi.advanceTimersByTimeAsync(500)
    await flushPromises()

    expect(wrapper.text()).toContain('Form Error')
    expect(wrapper.text()).toContain('Record is locked')
  })

  it('clears a field backend error when the field is edited', async () => {
    store.validateEvidence.mockResolvedValue({
      is_valid: false,
      field_validations: { name: { errors: [{ message: 'Bad' }] } }
    })
    vi.useFakeTimers()
    const wrapper = mountForm()
    fieldStub(wrapper, 'name').vm.$emit('update:model-value', 'B')
    await vi.advanceTimersByTimeAsync(500)
    await flushPromises()
    expect(fieldStub(wrapper, 'name').props('backendErrors')).toEqual(['Bad'])

    fieldStub(wrapper, 'name').vm.$emit('clear-backend-error')
    await flushPromises()

    expect(fieldStub(wrapper, 'name').props('backendErrors')).toEqual([])
  })

  it('validates a field on blur with its field config', async () => {
    const wrapper = mountForm()

    fieldStub(wrapper, 'name').vm.$emit('validate', 'Ad')
    await flushPromises()

    expect(store.validateField).toHaveBeenCalledWith({
      field_name: 'name',
      field_value: 'Ad',
      field_config: { type: 'string', title: 'Name' }
    })
  })

  it('reports blur validation failures without throwing', async () => {
    store.validateField.mockRejectedValue(new Error('offline'))
    const wrapper = mountForm()

    fieldStub(wrapper, 'name').vm.$emit('validate', 'x')
    await flushPromises()

    expect(wrapper.exists()).toBe(true)
  })

  it('shows the live scoring sidebar when the schema defines an engine', () => {
    store.schema = {
      ...flatSchema,
      scoring_configuration: { engine: 'clingen' }
    }
    const wrapper = mountForm()

    expect(wrapper.find('.score-stub').exists()).toBe(true)
  })

  it('omits the scoring sidebar without a scoring engine', () => {
    const wrapper = mountForm()

    expect(wrapper.find('.score-stub').exists()).toBe(false)
  })

  it('emits validation-change with the current result', () => {
    store.result = { is_valid: true }
    const wrapper = mountForm()

    expect(wrapper.emitted('validation-change')![0]).toEqual([{ is_valid: true }])
  })
})
