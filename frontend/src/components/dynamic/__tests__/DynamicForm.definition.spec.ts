/**
 * DynamicForm rendering from raw methodology config (`definition` prop): seeded precuration,
 * config-only fields and evidence tables, conditions.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { precurationSeed } from './precurationSeed'
import { vmOf } from './testHelpers'

const store = vi.hoisted(() => ({
  loading: true,
  error: null,
  getJsonSchema: vi.fn(() => null),
  getValidationResult: vi.fn(() => null),
  generateJsonSchema: vi.fn(),
  validateEvidence: vi.fn(),
  validateField: vi.fn()
}))

vi.mock('@/stores', () => ({ useValidationStore: () => store }))
vi.mock('@/composables/useLogger', () => ({
  useLogger: () => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() })
}))
// Ontology widgets are covered by their own specs; here only their presence matters
vi.mock('@/components/evidence/MONDOAutocomplete.vue', () => ({
  default: {
    name: 'MONDOAutocomplete',
    props: ['label'],
    template: '<div class="mondo">{{ label }}</div>'
  }
}))
vi.mock('@/components/evidence/HPOInput.vue', () => ({
  default: { name: 'HPOInput', props: ['label'], template: '<div class="hpo">{{ label }}</div>' }
}))

import DynamicForm from '../DynamicForm.vue'

function mountForm(definition: Record<string, unknown>, initialData: Record<string, unknown> = {}) {
  return mount(DynamicForm, {
    props: { schemaId: 's1', definition, initialData, hideActions: true },
    attachTo: document.body
  })
}

beforeEach(() => vi.clearAllMocks())

describe('DynamicForm from raw config', () => {
  it('renders the seeded precuration as steps without fetching a generated schema', async () => {
    const wrapper = mountForm(precurationSeed)
    await flushPromises()
    expect(store.generateJsonSchema).not.toHaveBeenCalled()
    const text = wrapper.text()
    for (const step of [
      'Disease Entity Definition',
      'Mode of Inheritance',
      'Lumping & Splitting',
      'Precuration Metadata'
    ]) {
      expect(text).toContain(step)
    }
    expect(wrapper.find('.mondo').text()).toBe('Mondo Disease ID')
    expect(wrapper.find('.hpo').text()).toBe('Key Phenotypes')
    expect(text).not.toContain('Loading form schema')
  })

  it('hides fields until their visible_when condition holds', async () => {
    const wrapper = mountForm(precurationSeed, { mode_of_inheritance: 'AD' })
    const form = vmOf(wrapper)
    form.activeTab = 'inheritance'
    await flushPromises()
    expect(wrapper.text()).toContain('Mode of Inheritance')
    expect(wrapper.text()).not.toContain('MOI Notes')

    form.formData.mode_of_inheritance = 'Other'
    await flushPromises()
    expect(wrapper.text()).toContain('MOI Notes')

    form.activeTab = 'lumping_splitting'
    await flushPromises()
    expect(wrapper.text()).not.toContain('Rationale')
    form.formData.lumping_splitting_applicable = true
    await flushPromises()
    expect(wrapper.text()).toContain('Rationale')
  })

  it('renders a field and a table added only in config, with required_when', async () => {
    const wrapper = mountForm(
      {
        field_definitions: {
          kind: { type: 'enum', label: 'Kind', options: [{ value: 'cohort', label: 'Cohort' }] },
          inherited: { type: 'text', label: 'Inherited', readonly: true },
          cohort_size: { type: 'number', label: 'Cohort size', required_when: { kind: 'cohort' } },
          registry: {
            type: 'evidence_table',
            label: 'Patient registry',
            columns: { cohort: { type: 'text', label: 'Cohort', required: true } }
          }
        }
      },
      { kind: 'cohort', registry: [{ id: 'r1', cohort: 'A' }] }
    )
    await flushPromises()
    expect(wrapper.text()).toContain('Kind')
    const disabled = wrapper.findAll('.v-input--disabled').map(el => el.text())
    expect(disabled).toEqual([expect.stringContaining('Inherited')])
    expect(wrapper.find('caption').text()).toContain('Patient registry')
    expect(wrapper.find('input[aria-label="Cohort, row 1"]').exists()).toBe(true)
    // required_when resolved: the number field carries the required marker
    expect(wrapper.find('input[type="number"]').attributes()).toHaveProperty('required')
  })

  it('writes evidence cells to the form on change, not per keystroke', async () => {
    const wrapper = mountForm(
      {
        field_definitions: {
          registry: { type: 'evidence_table', columns: { cohort: { type: 'text' } } }
        }
      },
      { registry: [{ id: 'r1', cohort: 'A' }] }
    )
    await flushPromises()
    const before = wrapper.emitted('update:modelValue')?.length ?? 0
    const validations = store.validateEvidence.mock.calls.length
    const input = wrapper.find<HTMLInputElement>('input[aria-label="Cohort, row 1"]')
    input.element.value = 'AB'
    await input.trigger('input')
    expect(wrapper.emitted('update:modelValue')?.length ?? 0).toBe(before)
    expect(store.validateEvidence.mock.calls.length).toBe(validations)

    await input.trigger('change')
    const last = wrapper.emitted('update:modelValue')!.at(-1)![0] as Record<string, unknown>
    expect(last.registry).toEqual([{ id: 'r1', cohort: 'AB' }])
  })
})
