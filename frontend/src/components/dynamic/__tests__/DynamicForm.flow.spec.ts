/**
 * Tests for DynamicForm's flat layout, submit / save-draft flows and the
 * backend validation round trip.
 *
 * @see src/components/dynamic/DynamicForm.vue
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount, flushPromises, type VueWrapper } from '@vue/test-utils'
import { reactive } from 'vue'

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
  validateField: vi.fn(),
  clearValidationResult: vi.fn()
}))

vi.mock('@/stores', () => ({
  useValidationStore: () => store
}))

vi.mock('@/composables/useLogger', () => ({
  useLogger: () => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() })
}))

import DynamicForm from '../DynamicForm.vue'
import type { FormValidationResult } from '../types'
import { scoreSnapshot } from '@/components/forms/scorePreview'

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

  it('shows no errors on an untouched new form, then after the first edit (monkey B13)', async () => {
    store.result = {
      is_valid: false,
      errors: [{ field: 'name', message: 'Required field is missing' }],
      field_validations: { name: { is_valid: false, errors: ['Required field is missing'] } }
    }
    store.schema = {
      properties: { ...flatSchema.properties, age: { type: 'integer', default: 1 } }
    }
    const wrapper = mountForm({ initialData: {} })
    await flushPromises()
    expect(wrapper.emitted('update:modelValue')?.at(-1)?.[0]).toEqual({ age: 1 })
    expect(wrapper.text()).not.toContain('Form Validation Errors')
    expect(fieldStub(wrapper, 'name').props('validationResult')).toBeUndefined()
    // Validity still reaches the parent, so submit stays gated
    expect(wrapper.emitted('validation-change')?.at(-1)?.[0]).toMatchObject({ is_valid: false })
    // The parent echoing the form's own defaults back is not a load
    await wrapper.setProps({ initialData: { age: 1 } })
    expect(wrapper.text()).not.toContain('Form Validation Errors')

    fieldStub(wrapper, 'age').vm.$emit('update:model-value', 3)
    await flushPromises()
    expect(wrapper.text()).toContain('Form Validation Errors')
    expect(fieldStub(wrapper, 'name').props('validationResult')).toMatchObject({ is_valid: false })
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
    store.schema = null
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
    expect(buttonWithText(wrapper, 'Save draft').attributes('disabled')).toBeDefined()

    fieldStub(wrapper, 'name').vm.$emit('update:model-value', 'Grace')
    await flushPromises()
    await buttonWithText(wrapper, 'Save draft').trigger('click')

    expect(wrapper.emitted('save-draft')![0]).toEqual([{ name: 'Grace' }])
    expect(wrapper.emitted('update:modelValue')!.at(-1)).toEqual([{ name: 'Grace' }])
  })

  it('emits submit with the form data when validation passes', async () => {
    store.validateEvidence.mockResolvedValue({ is_valid: true })
    const wrapper = mountForm()
    fieldStub(wrapper, 'age').vm.$emit('update:model-value', 36)
    await flushPromises()

    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(store.validateEvidence).toHaveBeenCalledWith(
      { name: 'Ada', age: 36 },
      'schema-1',
      'form',
      undefined
    )
    expect(wrapper.emitted('submit')![0]).toEqual([{ name: 'Ada', age: 36 }])
  })

  it('invalidates the old preview immediately on an edit, before debounce', async () => {
    vi.useFakeTimers()
    const wrapper = mountForm()
    await flushPromises()
    store.clearValidationResult.mockClear()
    fieldStub(wrapper, 'age').vm.$emit('update:model-value', 37)
    await flushPromises()
    expect(store.clearValidationResult).toHaveBeenCalledWith('form')
    wrapper.unmount()
  })

  it('validates the latest edit on submit, never an older result (submit within the debounce)', async () => {
    vi.useFakeTimers()
    try {
      store.validateEvidence.mockResolvedValue({ is_valid: true })
      const wrapper = mountForm()
      await vi.advanceTimersByTimeAsync(600)
      // The newest edit is invalid; submit comes before its debounced validation runs
      store.validateEvidence.mockResolvedValue({ is_valid: false, errors: [{ message: 'x' }] })
      const before = store.validateEvidence.mock.calls.length
      fieldStub(wrapper, 'age').vm.$emit('update:model-value', -1)
      await wrapper.find('form').trigger('submit')
      await vi.advanceTimersByTimeAsync(600)
      // Only submit's own validation ran: the debounced one was cancelled
      expect(store.validateEvidence.mock.calls.length).toBe(before + 1)

      expect(store.validateEvidence).toHaveBeenLastCalledWith(
        { name: 'Ada', age: -1 },
        'schema-1',
        'form',
        undefined
      )
      expect(wrapper.emitted('submit')).toBeUndefined()
    } finally {
      vi.useRealTimers()
    }
  })

  it.each([
    ['dropped', () => store.validateEvidence.mockResolvedValue(null)],
    ['failed', () => store.validateEvidence.mockRejectedValue(new Error('down'))]
  ])('tells the user and does not submit when the validation is %s', async (_, arrange) => {
    arrange()
    const wrapper = mountForm()
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(wrapper.emitted('submit')).toBeUndefined()
    expect(wrapper.text()).toContain('Could not validate the form. Please try again.')
    store.validateEvidence.mockReset()
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

  it('passes the live verdict and trace through, so the score panel can render', () => {
    const trace = { sections: [{ key: 'genetic_evidence', score: 2 }] }
    store.result = {
      is_valid: true,
      score_calculations: { total_score: 2, verdict: 'limited', trace }
    }
    const wrapper = mountForm()

    const [result] = wrapper.emitted('validation-change')![0] as [FormValidationResult]
    expect(result.score_calculations).toEqual({ total_score: 2, verdict: 'limited', trace })
    expect(scoreSnapshot(result.score_calculations, false)).toMatchObject({
      total: 2,
      classification: 'limited'
    })
  })
})

describe('DynamicForm stays mounted and follows late initial data', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    store.loading = false
    store.error = null
    store.schema = flatSchema
    store.result = null
    store.getJsonSchema.mockImplementation(() => store.schema)
    store.getValidationResult.mockImplementation(() => store.result)
    store.generateJsonSchema.mockResolvedValue(undefined)
    store.validateEvidence.mockResolvedValue(null)
  })

  it('keeps the fields mounted while field validation is loading', async () => {
    store.loading = true // a field validation is in flight, the schema is already loaded
    const wrapper = mountForm()

    expect(wrapper.text()).not.toContain('Loading form schema...')
    expect(wrapper.findAllComponents({ name: 'DynamicField' })).toHaveLength(2)
  })

  it('fills the fields when initial data arrives after mount', async () => {
    const wrapper = mountForm({ initialData: {} })
    await wrapper.setProps({ initialData: { name: 'Grace' } })

    expect(fieldStub(wrapper, 'name').props('modelValue')).toBe('Grace')
  })

  it('keeps typed text when the late load arrives after the parent mirrored the edit', async () => {
    const wrapper = mountForm({ initialData: {} })
    fieldStub(wrapper, 'name').vm.$emit('update:modelValue', 'typed')
    await wrapper.setProps({ initialData: { name: 'typed' } }) // parent mirrors the edit
    await wrapper.setProps({ initialData: { name: 'Grace' } }) // saved draft arrives late

    expect(fieldStub(wrapper, 'name').props('modelValue')).toBe('typed')
  })

  it('fills the fields when initial data is mutated in place (restore)', async () => {
    const data = reactive<Record<string, unknown>>({})
    const wrapper = mountForm({ initialData: data })
    data.name = 'Grace'
    await flushPromises()

    expect(fieldStub(wrapper, 'name').props('modelValue')).toBe('Grace')
  })

  it('does not overwrite edits the user made before late data arrives', async () => {
    const wrapper = mountForm({ initialData: {} })
    fieldStub(wrapper, 'name').vm.$emit('update:modelValue', 'typed')
    await wrapper.setProps({ initialData: { name: 'Grace' } })

    expect(fieldStub(wrapper, 'name').props('modelValue')).toBe('typed')
  })

  it('labels error paths with the schema title, not the raw path', () => {
    store.schema = {
      properties: {
        entity_definition: {
          type: 'object',
          properties: { mode_of_inheritance: { type: 'string', title: 'Mode of inheritance' } }
        }
      }
    }
    store.result = {
      is_valid: false,
      errors: [
        { field: 'entity_definition.mode_of_inheritance', message: 'Required' },
        { field: 'entity_definition.mode_of_inheritance', message: 'Must be AD or AR' }
      ],
      warnings: [
        { field: 'entity_definition.disease_name', message: 'Short' },
        { field: 'entity_definition.disease_name', message: 'Short' }
      ]
    }
    const wrapper = mountForm()

    expect(wrapper.findComponent({ name: 'ValidationWarnings' }).props('messages')).toEqual([
      'Disease name: Short'
    ])
    expect(wrapper.text()).toContain('Mode of inheritance: Required')
    expect(wrapper.text()).toContain('Mode of inheritance: Must be AD or AR')
    expect(wrapper.text()).not.toContain('entity_definition')
  })
})
