import { describe, expect, it, vi, beforeEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import CurationEvidenceReadonly from '../CurationEvidenceReadonly.vue'

const fetchPinnedVersion = vi.hoisted(() => vi.fn())
vi.mock('@/stores/schemas', () => ({ useSchemasStore: () => ({ fetchPinnedVersion }) }))

const DynamicForm = {
  name: 'DynamicForm',
  props: {
    definition: Object,
    methodologyVersionId: String,
    initialData: Object,
    readonly: Boolean
  },
  template: '<div />'
}
const mountIt = () =>
  mount(CurationEvidenceReadonly, {
    props: { evidence: { evidence_summary: 'x' }, schemaId: 's1', versionId: 'v1' },
    global: { stubs: { DynamicForm } }
  })

beforeEach(() => fetchPinnedVersion.mockReset())

describe('CurationEvidenceReadonly', () => {
  it('renders the evidence read-only from the pinned version', async () => {
    fetchPinnedVersion.mockResolvedValue({ id: 'v1', snapshot: { field_definitions: {} } })
    const wrapper = mountIt()
    await flushPromises()
    expect(fetchPinnedVersion).toHaveBeenCalledWith('v1', 's1')
    expect(wrapper.findComponent({ name: 'DynamicForm' }).props()).toMatchObject({
      definition: { field_definitions: {} },
      methodologyVersionId: 'v1',
      initialData: { evidence_summary: 'x' },
      readonly: true
    })
  })

  it('says so when the version cannot be loaded', async () => {
    fetchPinnedVersion.mockImplementation(async () => {
      throw new Error('404')
    })
    const wrapper = mountIt()
    await flushPromises()
    expect(wrapper.text()).toContain('could not be loaded')
    fetchPinnedVersion.mockReset()
  })
})

describe('CurationEvidenceReadonly score summary', () => {
  it('fills the schema’s Score summary section with the saved score', async () => {
    fetchPinnedVersion.mockResolvedValue({ id: 'v1', snapshot: { field_definitions: {} } })
    const WithSection = {
      name: 'DynamicForm',
      template: `<div><slot name="section" :section="{ name: 'Score Summary', component: 'ScoreSummary' }" /></div>`
    }
    const ScoreSummary = {
      name: 'ScoreSummary',
      props: { scores: Object, classification: String },
      template: '<div class="summary" />'
    }
    const scores = { total: 7, trace: null }
    const wrapper = mount(CurationEvidenceReadonly, {
      props: { evidence: {}, schemaId: 's1', scores, classification: 'moderate' },
      global: { stubs: { DynamicForm: WithSection, ScoreSummary } }
    })
    await flushPromises()
    expect(wrapper.findComponent({ name: 'ScoreSummary' }).props()).toEqual({
      scores,
      classification: 'moderate'
    })
  })
})
