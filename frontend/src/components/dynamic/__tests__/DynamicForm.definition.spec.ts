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
  validateField: vi.fn(),
  clearValidationResult: vi.fn()
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

  it('applies conditions to nested children against the whole form data (#433)', async () => {
    const wrapper = mountForm(
      {
        field_definitions: {
          moi: { type: 'text', label: 'MOI' },
          details: {
            type: 'object',
            label: 'Details',
            properties: {
              note: { type: 'text', label: 'MOI note', visible_when: { moi: 'Other' } },
              why: { type: 'text', label: 'Why other', required_when: { moi: 'Other' } }
            }
          }
        }
      },
      { moi: 'AD', details: {} }
    )
    await flushPromises()
    expect(wrapper.text()).not.toContain('MOI note')
    expect(wrapper.findAll('input[required]')).toHaveLength(0)

    vmOf(wrapper).formData.moi = 'Other'
    await flushPromises()
    expect(wrapper.text()).toContain('MOI note')
    expect(wrapper.findAll('input[required]')).toHaveLength(1)
  })

  it('hides a dotted section field while its parent is hidden (#433)', async () => {
    const wrapper = mountForm(
      {
        field_definitions: {
          on: { type: 'boolean', label: 'Applicable' },
          other: { type: 'text', label: 'Other' },
          extra: {
            type: 'object',
            visible_when: { on: true },
            properties: { why: { type: 'text', label: 'Reason given' } }
          }
        },
        ui_configuration: {
          layout: {
            tabs: [
              { id: 'a', name: 'A', sections: [{ name: 'S', fields: ['on', 'extra.why'] }] },
              { id: 'b', name: 'B', sections: [{ name: 'T', fields: ['other'] }] }
            ]
          }
        }
      },
      { on: false }
    )
    await flushPromises()
    expect(wrapper.text()).toContain('Applicable')
    expect(wrapper.text()).not.toContain('Reason given')

    vmOf(wrapper).formData.on = true
    await flushPromises()
    expect(wrapper.text()).toContain('Reason given')
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

  it('validates against the pinned version it renders', async () => {
    mount(DynamicForm, {
      props: {
        schemaId: 's1',
        definition: { field_definitions: { note: { type: 'text' } } },
        methodologyVersionId: 'v7',
        initialData: { note: 'x' }
      }
    })
    await flushPromises()
    expect(store.validateEvidence).toHaveBeenCalledWith({ note: 'x' }, 's1', 'form', 'v7')
  })

  it('renders component-only sections through the section slot and can hide its scoring', async () => {
    const wrapper = mount(DynamicForm, {
      props: {
        schemaId: 's1',
        hideScoring: true,
        definition: {
          field_definitions: { note: { type: 'text', label: 'Note' } },
          scoring_configuration: { engine: 'clingen_sop_v11' },
          ui_configuration: {
            layout: {
              tabs: [
                {
                  id: 'a',
                  name: 'A',
                  sections: [
                    { name: 'Notes', fields: ['note'] },
                    { name: 'Score', component: 'ScoreSummary' }
                  ]
                },
                { id: 'b', name: 'B', sections: [{ name: 'Lumping', component: 'Lumping' }] }
              ]
            }
          }
        }
      },
      slots: {
        section:
          '<template #section="{ section }"><b class="slot">{{ section.component }}</b></template>'
      }
    })
    await flushPromises()
    expect(wrapper.find('.slot').text()).toBe('ScoreSummary')
    expect(wrapper.text()).toContain('B') // a tab with only a component section is kept
    expect(wrapper.findComponent({ name: 'ScoreDisplay' }).exists()).toBe(false)
  })

  it('validates once per pause in typing and clears the shared result on mount and unmount', async () => {
    vi.useFakeTimers()
    try {
      const wrapper = mount(DynamicForm, {
        props: { schemaId: 's1', definition: { field_definitions: { note: { type: 'text' } } } }
      })
      expect(store.clearValidationResult).toHaveBeenCalledWith('form')
      const form = vmOf(wrapper)
      form.formData.note = 'a'
      await flushPromises()
      form.formData.note = 'ab'
      await flushPromises()
      expect(store.validateEvidence).not.toHaveBeenCalled()
      await vi.advanceTimersByTimeAsync(500)
      expect(store.validateEvidence).toHaveBeenCalledTimes(1)

      store.clearValidationResult.mockClear()
      wrapper.unmount()
      expect(store.clearValidationResult).toHaveBeenCalledWith('form')
    } finally {
      vi.useRealTimers()
    }
  })
})
