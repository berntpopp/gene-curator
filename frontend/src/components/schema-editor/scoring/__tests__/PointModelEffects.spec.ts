import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import PointModelBuilder from '../PointModelBuilder.vue'
import PointModelRowRules from '../PointModelRowRules.vue'
import { validationAPI } from '@/api'
import { call, vmOf } from '@/views/__tests__/vm'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { effectOf, setEffect, setGroupBy, type ItemType, type PointsWhen } from '../pointModel'

vi.mock('@/api', () => ({
  validationAPI: { validateSchema: vi.fn(), validateEvidence: vi.fn() }
}))

afterEach(() => {
  document.body.innerHTML = ''
})

// #615: points_when factor / max and a list group_by, as the KGDB bundle uses them
describe('point model effects and grouped fields', () => {
  it('switches a rule between points, factor and max, keeping its number', () => {
    const rule: PointsWhen = { field: 'phase', in: ['unknown'], points: 0.5 }
    expect(effectOf(rule)).toBe('points')
    setEffect(rule, 'factor')
    expect(rule).toEqual({ field: 'phase', in: ['unknown'], factor: 0.5 })
    setEffect(rule, 'max')
    expect(rule).toEqual({ field: 'phase', in: ['unknown'], max: 0.5 })
    expect(effectOf({ field: 'x' })).toBe('points')
  })

  it('edits a factor rule in the row rules form', async () => {
    const item: ItemType = {
      path: 'probands',
      points_when: [{ field: 'phase', in: ['unknown'], factor: 0.5 }]
    }
    const w = mount(PointModelRowRules, { props: { item, base: 'b', diag: () => [] } })
    const fields = w.findAll('input[type="number"]')
    expect((fields[0]!.element as HTMLInputElement).value).toBe('0.5')
    await fields[0]!.setValue('0.25')
    expect(item.points_when![0]).toEqual({ field: 'phase', in: ['unknown'], factor: 0.25 })
    expect(w.text()).toContain('Times')
  })

  it('stores one group field as text and several as a list', () => {
    const item: ItemType = { path: 'probands' }
    setGroupBy(item, ['variant', 'population'])
    expect(item.group_by).toEqual(['variant', 'population'])
    setGroupBy(item, ['variant'])
    expect(item.group_by).toBe('variant')
    setGroupBy(item, [])
    expect(item).toEqual({ path: 'probands' })
  })

  it('round-trips the KGDB Mendelian scoring configuration unchanged', async () => {
    vi.mocked(validationAPI.validateSchema).mockResolvedValue({ errors: [], warnings: [] } as never)
    const bundle = JSON.parse(
      readFileSync(
        join(process.cwd(), '../docs/schemas/kidney-genetics/kgdb-methodology.json'),
        'utf8'
      )
    ) as { schemas: { name: string; scoring_configuration: Record<string, unknown> }[] }
    const input = bundle.schemas.find(
      s => s.name === 'KGDB Mendelian Curation'
    )!.scoring_configuration
    const snapshot = JSON.parse(JSON.stringify(input)) as unknown
    const w = mount(PointModelBuilder, { props: { modelValue: input }, attachTo: document.body })
    await flushPromises()
    for (const tab of w.findAll('.v-tab')) {
      await tab.trigger('click')
      await flushPromises()
    }
    for (const panel of w.findAll('.v-expansion-panel-title')) await panel.trigger('click')
    for (const rules of w.findAll('button[aria-label="Show row rules"]'))
      await rules.trigger('click')
    await flushPromises()
    expect(JSON.parse(vmOf(w).codeText as string)).toEqual(snapshot)
    await call(vmOf(w), 'setCode', vmOf(w).codeText)
    await flushPromises()
    expect(w.emitted('update:modelValue')?.length ?? 0).toBe(0)
    expect(input).toEqual(snapshot)
  }, 20_000)
})
