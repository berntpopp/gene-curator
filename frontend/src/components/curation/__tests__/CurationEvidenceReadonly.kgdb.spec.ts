/** KGDB curation detail (monkey B1): evidence tables render from the pinned snapshot as tables. */
import { describe, it, expect, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import bundle from '../../../../../docs/schemas/kidney-genetics/kgdb-methodology.json'

const snapshot = bundle.schemas.find(s => s.name === 'KGDB Mendelian Curation')!
vi.mock('@/stores/schemas', () => ({
  useSchemasStore: () => ({
    fetchPinnedVersion: vi.fn(async () => ({ id: 'v1', snapshot }))
  })
}))
vi.mock('@/stores', () => ({
  useValidationStore: () => ({
    loading: false,
    error: null,
    getJsonSchema: vi.fn(),
    getValidationResult: vi.fn(() => null),
    generateJsonSchema: vi.fn(),
    validateEvidence: vi.fn(async () => null),
    validateField: vi.fn(),
    clearValidationResult: vi.fn()
  })
}))

import CurationEvidenceReadonly from '../CurationEvidenceReadonly.vue'

describe('CurationEvidenceReadonly with the KGDB bundle', () => {
  it('renders a proband as a table row, not as JSON text', async () => {
    const evidence = { genetic: { probands: [{ proband_label: 'P1', variant: 'c.494G>A' }] } }
    const wrapper = mount(CurationEvidenceReadonly, {
      props: { evidence, schemaId: 's1', versionId: 'v1' },
      attachTo: document.body
    })
    await flushPromises()
    await wrapper
      .findAll('.v-tab')
      .find(t => t.text().includes('Genetic evidence'))!
      .trigger('click')
    await flushPromises()
    const row = wrapper.findAll('tr').find(r => r.text().includes('P1'))
    expect(row?.text()).toContain('c.494G>A')
    expect(wrapper.text()).not.toContain('"proband_label"')
    wrapper.unmount()
  })

  it('shows the synopsis the bundle names (evidence_summary)', async () => {
    const evidence = { evidence_summary: 'HOMG3, autosomal recessive' }
    const wrapper = mount(CurationEvidenceReadonly, {
      props: { evidence, schemaId: 's1', versionId: 'v1' }
    })
    await flushPromises()
    expect(wrapper.get('[data-testid="curation-synopsis"]').text()).toContain(
      'HOMG3, autosomal recessive'
    )
  })
})
