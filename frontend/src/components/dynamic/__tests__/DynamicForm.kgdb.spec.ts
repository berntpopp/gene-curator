/**
 * KGDB curation detail (monkey B1): the read-only view renders the server JSON schema, whose
 * layout keeps component-only sections (ScoreSummary) without `fields`.
 */
import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import bundle from '../../../../../docs/schemas/kidney-genetics/kgdb-methodology.json'

const curation = bundle.schemas.find(s => s.name === 'KGDB Mendelian Curation')!
const store = vi.hoisted(() => ({
  loading: false,
  error: null,
  getJsonSchema: vi.fn(),
  getValidationResult: vi.fn(() => null),
  generateJsonSchema: vi.fn(),
  validateEvidence: vi.fn(),
  validateField: vi.fn(),
  clearValidationResult: vi.fn()
}))
vi.mock('@/stores', () => ({ useValidationStore: () => store }))

import DynamicForm from '../DynamicForm.vue'

describe('KGDB curation detail', () => {
  it('renders read-only without crashing on a component-only section', async () => {
    store.getJsonSchema.mockReturnValue({
      properties: { evidence_summary: { type: 'string', title: 'Evidence summary' } },
      ui_configuration: curation.ui_configuration
    })
    const wrapper = mount(DynamicForm, {
      props: { schemaId: 's1', initialData: { evidence_summary: 'Strong' }, readonly: true }
    })
    await flushPromises()
    expect(wrapper.text()).toContain('Genetic evidence')
    expect(wrapper.text()).toContain('Evidence summary')
  })
})
