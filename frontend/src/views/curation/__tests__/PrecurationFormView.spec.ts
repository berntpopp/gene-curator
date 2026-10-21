import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('@/api', () => ({
  genesAPI: { getGeneById: vi.fn() },
  scopesAPI: { getScopeById: vi.fn() },
  schemasAPI: { getWorkflowPairs: vi.fn() }
}))

const route = vi.hoisted(() => ({ params: {} as Record<string, string>, query: {} }))

vi.mock('@/api/precurations', () => ({ precurationsAPI: { getPrecuration: vi.fn() } }))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => route
}))

import { genesAPI, scopesAPI, schemasAPI } from '@/api'
import { precurationsAPI } from '@/api/precurations'
import PrecurationFormView from '@/views/curation/PrecurationFormView.vue'

describe('PrecurationFormView', () => {
  beforeEach(() => {
    route.params = { scopeId: 'sc1', geneId: 'g1' }
    setActivePinia(createPinia())
    vi.mocked(scopesAPI.getScopeById).mockResolvedValue({
      default_workflow_pair_id: 'wp1'
    } as never)
    vi.mocked(schemasAPI.getWorkflowPairs).mockResolvedValue([
      { id: 'wp1', precuration_schema_id: 'schema-1' }
    ] as never)
  })

  it('loads the scope, its precuration schema and the gene', async () => {
    vi.mocked(genesAPI.getGeneById).mockResolvedValue({ approved_symbol: 'BRCA1' } as never)
    const wrapper = mount(PrecurationFormView, {
      global: { stubs: { SchemaDrivenPrecurationForm: true } }
    })
    await flushPromises()
    expect(scopesAPI.getScopeById).toHaveBeenCalledWith('sc1')
    expect(genesAPI.getGeneById).toHaveBeenCalledWith('g1')
    expect(wrapper.text()).toContain('BRCA1')
    expect(wrapper.text()).not.toContain('Unknown')
    expect(wrapper.findComponent({ name: 'SchemaDrivenPrecurationForm' }).props('gene')).toEqual({
      symbol: 'BRCA1'
    })
  })

  it('shows an error when the gene cannot be loaded', async () => {
    vi.mocked(genesAPI.getGeneById).mockRejectedValue(new Error('404'))
    const wrapper = mount(PrecurationFormView, {
      global: { stubs: { SchemaDrivenPrecurationForm: true } }
    })
    await flushPromises()
    expect(wrapper.text()).toContain('Could not load gene information: 404')
  })

  it.each([
    ['draft', false],
    ['submitted', true]
  ])('opens an existing %s precuration by id (readonly=%s)', async (status, readonly) => {
    route.params = { scopeId: 'sc1', precurationId: 'p1' }
    vi.mocked(precurationsAPI.getPrecuration).mockResolvedValue({
      id: 'p1',
      gene_id: 'g7',
      status
    } as never)
    vi.mocked(genesAPI.getGeneById).mockResolvedValue({ approved_symbol: 'PKD1' } as never)
    const wrapper = mount(PrecurationFormView, {
      global: { stubs: { SchemaDrivenPrecurationForm: true } }
    })
    await flushPromises()
    expect(genesAPI.getGeneById).toHaveBeenCalledWith('g7')
    const form = wrapper.findComponent({ name: 'SchemaDrivenPrecurationForm' })
    expect(form.props('precurationId')).toBe('p1')
    expect(form.props('readonly')).toBe(readonly)
  })

  it('shows an error when the precuration cannot be loaded', async () => {
    route.params = { scopeId: 'sc1', precurationId: 'p1' }
    vi.mocked(precurationsAPI.getPrecuration).mockRejectedValue(new Error('404'))
    const wrapper = mount(PrecurationFormView, {
      global: { stubs: { SchemaDrivenPrecurationForm: true } }
    })
    await flushPromises()
    expect(wrapper.text()).toContain('Could not load precuration')
  })
})
