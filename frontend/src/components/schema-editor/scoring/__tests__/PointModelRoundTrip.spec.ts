import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import PointModelBuilder from '../PointModelBuilder.vue'
import { validationAPI } from '@/api'
import { call, vmOf } from '@/views/__tests__/vm'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

// vitest runs in frontend/; the seeded schemas live in database/sql
const sql = (name: string) => readFileSync(join(process.cwd(), '../database/sql', name), 'utf8')
const seed = sql('004_seed_data.sql')
const correction = sql('046_clingen_v1_correction.sql')

vi.mock('@/api', () => ({
  validationAPI: { validateSchema: vi.fn(), validateEvidence: vi.fn() }
}))

/** The seeded ClinGen scoring_configuration (004) with the point model 046 installs. */
function seededClinGen(): Record<string, unknown> {
  const start = seed.indexOf("'", seed.indexOf('-- scoring_configuration')) + 1
  const config = JSON.parse(seed.slice(start, seed.indexOf("'", start))) as Record<string, unknown>
  const body = correction.split('$model$')[1]!
  return { ...config, point_model: JSON.parse(body) }
}

afterEach(() => {
  document.body.innerHTML = ''
})

describe('PointModelBuilder round trip', () => {
  it('opens every tab and the code view of the seeded ClinGen config without changing it', async () => {
    vi.mocked(validationAPI.validateSchema).mockResolvedValue({ errors: [], warnings: [] } as never)
    const input = seededClinGen()
    expect(input.engine).toBe('clingen_sop_v11')
    expect((input.point_model as { sections: unknown[] }).sections).toHaveLength(2)
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
    expect(vmOf(w).tab).toBe('code')
    expect(JSON.parse(vmOf(w).codeText as string)).toEqual(snapshot)
    await call(vmOf(w), 'setCode', vmOf(w).codeText) // re-applying the code view is a no-op
    await flushPromises()
    expect(w.emitted('update:modelValue')?.length ?? 0).toBe(0)
    expect(input).toEqual(snapshot)
  }, 20_000) // the full ClinGen model renders hundreds of inputs; CI adds coverage and load
})
