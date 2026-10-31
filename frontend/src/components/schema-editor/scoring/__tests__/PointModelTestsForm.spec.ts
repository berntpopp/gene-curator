/** Point-model tests are filled in the schema's own form (#282) */
import { describe, it, expect, afterEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PointModelTests from '../PointModelTests.vue'
import FieldsEditor from '../../FieldsEditor.vue'
import DynamicForm from '@/components/dynamic/DynamicForm.vue'
import type { ScoringTest } from '../pointModel'
import { usePointModelChecks } from '../usePointModelChecks'
import { validationAPI } from '@/api'
import { useValidationStore } from '@/stores/validation'

vi.mock('@/composables/useLogger', () => ({
  useLogger: () => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() })
}))

afterEach(() => {
  document.body.innerHTML = ''
})

describe('PointModelTests form entry', () => {
  it('fills test evidence from the form, one test at a time', async () => {
    setActivePinia(createPinia())
    const tests: ScoringTest[] = [
      { name: 'a', evidence_data: { n: 1 }, expect: {} },
      { name: 'b', evidence_data: {}, expect: {} }
    ]
    const w = mount(PointModelTests, {
      props: {
        modelValue: tests,
        results: [],
        running: false,
        classKeys: [],
        definition: {
          field_definitions: { n: { type: 'number' }, ok: { type: 'boolean', default: false } }
        },
        schemaId: 's1'
      },
      attachTo: document.body
    })
    expect(w.findComponent(DynamicForm).exists()).toBe(false) // JSON until Form is picked
    const toggles = w.findAllComponents({ name: 'VBtnToggle' })
    toggles[0]!.vm.$emit('update:modelValue', 'form')
    await flushPromises()
    const form = w.findComponent(DynamicForm)
    expect(form.props('initialData')).toEqual({ n: 1 })
    expect(tests[0]!.evidence_data).toEqual({ n: 1 }) // opening adds no defaults
    form.vm.$emit('update:modelValue', { n: 1, ok: false })
    expect(tests[0]!.evidence_data).toEqual({ n: 1 })
    form.vm.$emit('update:modelValue', { n: 3, ok: false })
    expect(tests[0]!.evidence_data).toEqual({ n: 3, ok: false })
    form.vm.$emit('update:modelValue', { n: 3, ok: false }) // same data: no write
    toggles[1]!.vm.$emit('update:modelValue', 'form')
    await flushPromises()
    expect(w.findAllComponents(DynamicForm)).toHaveLength(1)
    toggles[1]!.vm.$emit('update:modelValue', 'json')
    await flushPromises()
    expect(w.findComponent(DynamicForm).exists()).toBe(false)
  })
})

describe('FieldsEditor diagnostics', () => {
  it('shows a field its own validator messages in both stored shapes', () => {
    const diagnostics = [
      {
        field: 'field_definitions.sections[0].fields[1].type',
        message: 'bad type',
        severity: 'error' as const
      },
      {
        field: 'field_definitions.x.required_when.y',
        message: 'unknown y',
        severity: 'error' as const
      }
    ]
    const sectioned = mount(FieldsEditor, {
      props: {
        modelValue: {
          sections: [
            {
              id: 's',
              fields: [
                { id: 'a', type: 'text' },
                { id: 'b', type: '?' }
              ]
            }
          ]
        },
        diagnostics
      }
    })
    expect(sectioned.find('[data-testid="field-b"]').text()).toContain('bad type')
    expect(sectioned.find('[data-testid="field-a"]').text()).not.toContain('bad type')
    const flat = mount(FieldsEditor, {
      props: { modelValue: { x: { type: 'text' } }, diagnostics }
    })
    expect(flat.findAll('[data-testid="field-diagnostic"]').map(d => d.text())).toEqual([
      'unknown y'
    ])
  })
})

describe('draft checks', () => {
  it('a slower, older check never overwrites a newer one', async () => {
    let finish: (v: unknown) => void = () => {}
    const slow = new Promise(r => (finish = r))
    const reply = (field: string) => ({ errors: [{ field, message: field }], warnings: [] })
    vi.spyOn(validationAPI, 'validateSchema')
      .mockReturnValueOnce(slow as never)
      .mockResolvedValueOnce(reply('new') as never)
    const checks = usePointModelChecks()
    const older = checks.checkDraft({})
    await checks.checkDraft({})
    finish(reply('old'))
    await older
    expect(checks.diagnostics.value.map(d => d.field)).toEqual(['new'])
    expect(checks.checking.value).toBe(false)
  })

  it('validates form evidence against the unsaved definition', async () => {
    setActivePinia(createPinia())
    const post = vi.spyOn(validationAPI, 'validateEvidence').mockResolvedValue({} as never)
    const definition = { field_definitions: { n: { type: 'number' } } }
    await useValidationStore().validateEvidence({ n: 1 }, 's1', 'form', undefined, definition)
    expect(post).toHaveBeenCalledWith({
      evidence_data: { n: 1 },
      schema_id: 's1',
      schema_definition: definition
    })
    mount(DynamicForm, { props: { schemaId: 's1', definition } })
    await flushPromises()
    expect(post.mock.calls.at(-1)![0]).toMatchObject({ schema_definition: definition })
    mount(DynamicForm, { props: { schemaId: 's1', definition, methodologyVersionId: 'v1' } })
    await flushPromises()
    expect(post.mock.calls.at(-1)![0]).not.toHaveProperty('schema_definition')
  })
})
