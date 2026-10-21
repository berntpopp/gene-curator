/** The seeded ClinGen v1 config renders through the generic renderer (no ClinGen code). */
import { describe, it, expect, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import DynamicForm from '@/components/dynamic/DynamicForm.vue'
import snapshot from './clingenV1Snapshot.json'

const store = vi.hoisted(() => ({
  loading: false,
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

interface FormVm {
  activeTab: string
}

describe('ClinGen curation form from the pinned config', () => {
  it('renders the ClinGen steps, the replication flag and the evidence tables in order', async () => {
    const wrapper = mount(DynamicForm, {
      props: {
        schemaId: 's1',
        definition: snapshot,
        methodologyVersionId: 'v1',
        hideActions: true
      },
      attachTo: document.body
    })
    await flushPromises()
    const text = wrapper.text()
    for (const tab of ['Summary', 'Genetic Evidence', 'Experimental Evidence', 'Contradictory']) {
      expect(text).toContain(tab)
    }
    expect(text).toContain('Replicated over time')

    ;(wrapper.vm as unknown as FormVm).activeTab = 'genetic'
    await flushPromises()
    const captions = wrapper.findAll('caption').map(c => c.text())
    expect(captions[0]).toContain('Predicted or Proven Null')
    expect(captions[1]).toContain('Other Variant Type')
    const headers = wrapper
      .findAll('table')[0]!
      .findAll('th[scope="col"]')
      .map(th => th.text())
    expect(headers.slice(0, 4)).toEqual(['Proband', 'Type', 'Variant (HGVS)', 'PMID'])
  })
})
