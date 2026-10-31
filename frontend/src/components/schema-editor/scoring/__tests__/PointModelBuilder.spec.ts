import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'
import PointModelBuilder from '../PointModelBuilder.vue'
import { validationAPI } from '@/api'
import { call, vmOf } from '@/views/__tests__/vm'
import type { ScoringConfig } from '../pointModel'

vi.mock('@/api', () => ({
  validationAPI: { validateSchema: vi.fn(), validateEvidence: vi.fn() }
}))
const api = vi.mocked(validationAPI)

const response = (extra: Record<string, unknown> = {}) =>
  ({
    is_valid: true,
    errors: [],
    warnings: [],
    field_validations: {},
    business_rule_violations: [],
    score_calculations: {},
    completeness_score: 0,
    required_fields_missing: [],
    suggested_improvements: [],
    ...extra
  }) as never

const config = (): ScoringConfig => ({
  engine: 'clingen_sop_v11',
  custom_note: 'kept',
  point_model: {
    total_cap: 18,
    sections: [
      {
        key: 'genetic',
        cap: 12,
        categories: [
          {
            key: 'probands',
            cap: 10,
            types: [
              { path: 'probands', default: 1, range: [0, 3], group_by: 'variant', group_cap: 2 }
            ]
          }
        ]
      },
      { key: 'experimental', cap: 6, categories: [] }
    ],
    bands: [
      { class: 'strong', min: 12 },
      { class: 'moderate', min: 7, section_min: { genetic: 4 } },
      { class: 'no_known' }
    ]
  },
  tests: [
    { name: 'CLDN16', evidence_data: { genetic: {} }, expect: { total: 12, class: 'Strong' } }
  ]
})

function mountBuilder(value: ScoringConfig | null = config()) {
  const w = mount(PointModelBuilder, {
    props: {
      modelValue: value,
      fieldDefinitions: { probands: { type: 'evidence_table' } },
      'onUpdate:modelValue': (v: ScoringConfig | null) => w.setProps({ modelValue: v })
    },
    attachTo: document.body
  })
  return w
}

const last = (w: ReturnType<typeof mountBuilder>) =>
  w.emitted('update:modelValue')?.at(-1)?.[0] as ScoringConfig

describe('PointModelBuilder', () => {
  it('scores tests with the engine publish uses and clears stale results when tests change', async () => {
    api.validateEvidence.mockResolvedValue(
      response({ score_calculations: { total_score: 12, verdict: 'Strong' } })
    )
    const noEngine = config()
    delete noEngine.engine
    const w = mountBuilder(noEngine)
    await flushPromises()
    await call(vmOf(w), 'runTests')
    const sent = api.validateEvidence.mock.calls[0]![0] as unknown as {
      schema_definition: { scoring_configuration: ScoringConfig }
    }
    expect(sent.schema_definition.scoring_configuration.engine).toBe('clingen_sop_v11')
    expect(last(w)).toBeUndefined() // the default is sent, not written into the schema
    const checks = vmOf(w).checks as { results: { value: unknown[] } }
    expect(checks.results.value).toHaveLength(1)
    ;(vmOf(w).config as ScoringConfig).tests![0]!.expect.total = 11
    await nextTick()
    expect(checks.results.value).toEqual([])
  })

  beforeEach(() => {
    vi.useFakeTimers()
    vi.clearAllMocks()
    api.validateSchema.mockResolvedValue(response())
  })
  afterEach(() => {
    vi.useRealTimers()
    document.body.innerHTML = ''
  })

  it('checks the configuration with the schema fields on mount and debounced after edits', async () => {
    const w = mountBuilder()
    await flushPromises()
    expect(api.validateSchema).toHaveBeenCalledWith({
      schema_definition: {
        field_definitions: { probands: { type: 'evidence_table' } },
        scoring_configuration: expect.objectContaining({ engine: 'clingen_sop_v11' })
      }
    })
    expect(w.text()).toContain('genetic')
    expect(w.text()).toContain('No problems')

    const vm = vmOf(w)
    ;(vm.config as ScoringConfig).point_model!.sections[0]!.cap = 11
    await nextTick()
    expect(last(w).point_model!.sections[0]!.cap).toBe(11)
    expect(last(w).custom_note).toBe('kept') // unknown keys round-trip
    vi.advanceTimersByTime(600)
    await flushPromises()
    expect(api.validateSchema).toHaveBeenCalledTimes(2)
  })

  it('shows diagnostics inline, as tab badges and in the full list', async () => {
    api.validateSchema.mockResolvedValue(
      response({
        errors: [
          {
            field: 'scoring_configuration.point_model.sections[0].cap',
            message: 'Section cap must be a number',
            severity: 'error'
          },
          { field: 'field_definitions', message: 'not mine', severity: 'error' }
        ],
        warnings: [
          {
            field: 'scoring_configuration.point_model.bands[0].class',
            message: 'odd class',
            severity: 'warning'
          }
        ]
      })
    )
    const w = mountBuilder()
    await flushPromises()
    expect(w.text()).toContain('1 error')
    expect(w.text()).not.toContain('not mine')
    const vm = vmOf(w)
    expect(vm.sectionErrors).toBe(1)
    expect(vm.classErrors).toBe(1)
    await w.findAll('.v-expansion-panel-title')[0]!.trigger('click')
    await flushPromises()
    expect(document.body.textContent).toContain('Section cap must be a number')
    for (const tab of w.findAll('.v-tab')) await tab.trigger('click')
    expect(vmOf(w).tab).toBe('code')
    await w.findAll('.v-expansion-panel-title').at(-1)!.trigger('click')
    await flushPromises()
    expect(document.body.textContent).toContain('odd class')
    await w.find('button.v-btn--variant-text').trigger('click') // Check again
    expect(api.validateSchema).toHaveBeenCalledTimes(2)
  })

  it('reports a check that fails to reach the server', async () => {
    api.validateSchema.mockRejectedValue({ response: { data: { detail: 'down' } } })
    const w = mountBuilder()
    await flushPromises()
    expect(w.text()).toContain('down')
  })

  it('runs the embedded tests through the real engine and shows pass and fail', async () => {
    api.validateEvidence
      .mockResolvedValueOnce(
        response({ score_calculations: { total_score: 12, verdict: 'Strong' } })
      )
      .mockRejectedValueOnce(new Error('boom'))
    const value = config()
    value.tests!.push({ evidence_data: {}, expect: { class: 'Limited' } })
    const w = mountBuilder(value)
    await flushPromises()
    await call(vmOf(w), 'runTests')
    await flushPromises()
    const results = vmOf(w).checks as { results: { value: { failures: string[] }[] } }
    expect(results.results.value[0]!.failures).toEqual([])
    expect(results.results.value[1]!.failures[0]).toContain('boom')
    expect(vmOf(w).failedTests).toBe(1)
    expect(api.validateEvidence).toHaveBeenCalledWith({
      evidence_data: { genetic: {} },
      schema_definition: expect.objectContaining({ scoring_configuration: expect.any(Object) })
    })
  })

  it('compares a wrong total like publish does', async () => {
    api.validateEvidence.mockResolvedValue(
      response({ score_calculations: { total_score: 9, verdict: 'Strong' } })
    )
    const w = mountBuilder()
    await flushPromises()
    await call(vmOf(w), 'runTests')
    const results = vmOf(w).checks as { results: { value: { failures: string[] }[] } }
    expect(results.results.value[0]!.failures).toEqual(['expected total 12, got 9'])
  })

  it('round-trips through the code view and keeps the last valid object on bad JSON', async () => {
    const w = mountBuilder()
    await flushPromises()
    const vm = vmOf(w)
    const next = { ...config(), engine: 'gencc_based' }
    await call(vm, 'setCode', JSON.stringify(next))
    await nextTick()
    expect(last(w).engine).toBe('gencc_based')
    await call(vm, 'setCode', '{ broken')
    await nextTick()
    expect(vm.codeError).toContain('Not a JSON object')
    expect(last(w).engine).toBe('gencc_based')
    expect(vm.codeText).toBe('{ broken')
    await call(vm, 'setCode', '[1]')
    expect(vm.codeError).toContain('Not a JSON object')
    expect(w.emitted('error')?.[0]).toEqual([expect.stringContaining('Not a JSON object')])
    await call(vm, 'setCode', '{}')
    await nextTick()
    expect(w.emitted('error')?.at(-1)).toEqual([''])
  })

  it('adopts a new outside value and offers a point model when there is none', async () => {
    const w = mountBuilder(null)
    await flushPromises()
    expect(w.text()).toContain("engine's built-in model")
    await w.setProps({ modelValue: { engine: 'qualitative_assessment' } })
    expect((vmOf(w).config as ScoringConfig).engine).toBe('qualitative_assessment')
    await call(vmOf(w), 'startModel')
    await nextTick()
    expect(last(w).point_model).toEqual({ sections: [], bands: [{ class: 'no_known' }] })
    expect(vmOf(w).tab).toBe('sections')
  })

  it('uses the schema vocabulary for class choices, else the ClinGen classes', async () => {
    const w = mountBuilder()
    await flushPromises()
    expect(vmOf(w).classKeys).toContain('definitive')
    ;(vmOf(w).config as ScoringConfig).classifications = [
      { key: 'established', label: 'Established', order: 1, tone: 'strong' }
    ]
    await nextTick()
    expect(vmOf(w).classKeys).toEqual(['established'])
  })
})
