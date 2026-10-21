/**
 * Behaviour tests for the data views: GeneSummaryView, GenesTable, SchemaManagement, SchemaEditor.
 * Stores are real Pinia stores; their actions are stubbed with vi.spyOn.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, RouterLinkStub } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { useRoute } from 'vue-router'
import GeneSummaryView from '@/views/GeneSummaryView.vue'
import GenesTable from '@/views/GenesTable.vue'
import SchemaManagement from '@/views/SchemaManagement.vue'
import SchemaEditor from '@/views/SchemaEditor.vue'
import { useGeneSummaryStore } from '@/stores/geneSummary'
import { useGenesStore } from '@/stores/genes'
import { useAuthStore } from '@/stores/auth'
import { useSchemasStore } from '@/stores/schemas'

const { routerPush, routeState, logger, showError, showSuccess } = vi.hoisted(() => ({
  routerPush: vi.fn(),
  routeState: { params: {} as Record<string, string>, query: {} as Record<string, string> },
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() },
  showError: vi.fn(),
  showSuccess: vi.fn()
}))

vi.mock('vue-router', async importOriginal => {
  const { reactive } = await import('vue')
  // Reactive view of routeState so tests can simulate in-place navigation
  const reactiveRoute = reactive(routeState)
  return {
    ...(await importOriginal<typeof import('vue-router')>()),
    useRouter: () => ({ push: routerPush, back: vi.fn() }),
    useRoute: () => reactiveRoute
  }
})
vi.mock('@/composables/useLogger', () => ({ useLogger: () => logger }))
vi.mock('@/composables/useNotifications', () => ({
  showError,
  showSuccess,
  showInfo: vi.fn(),
  showWarning: vi.fn()
}))

let pinia: ReturnType<typeof createPinia>
const opts = () => ({
  global: { plugins: [pinia], stubs: { RouterLink: RouterLinkStub } }
})

beforeEach(() => {
  vi.clearAllMocks()
  pinia = createPinia()
  setActivePinia(pinia)
})

describe('GeneSummaryView', () => {
  beforeEach(() => {
    routeState.params = { geneId: 'gene-1' }
  })

  it('shows a summary with scope count, consensus and conflict warning', async () => {
    const summaries = useGeneSummaryStore()
    vi.spyOn(summaries, 'fetchPublicSummary').mockResolvedValue(undefined as never)
    summaries.publicSummaries.set('gene-1', {
      gene_id: 'gene-1',
      public_scopes_count: 2,
      consensus_classification: 'Definitive',
      has_conflicts: true,
      classification_summary: { Definitive: 1, Limited: 1 },
      scope_summaries: [],
      last_updated: '2026-01-02T10:00:00Z'
    })
    vi.spyOn(useGenesStore(), 'fetchGeneById').mockResolvedValue({
      approved_symbol: 'HNF1B'
    } as never)

    const wrapper = mount(GeneSummaryView, opts())
    await flushPromises()

    expect(wrapper.text()).toContain('Gene Summary: HNF1B')
    expect(wrapper.text()).toContain('Scopes Curating')
    expect(wrapper.text()).toContain('Definitive')
    expect(wrapper.text()).toContain('Conflicting Classifications')
  })

  it('reloads the summary when the route gene changes', async () => {
    const fetchSummary = vi
      .spyOn(useGeneSummaryStore(), 'fetchPublicSummary')
      .mockResolvedValue(undefined as never)
    vi.spyOn(useGenesStore(), 'fetchGeneById').mockResolvedValue({ approved_symbol: 'X' } as never)
    mount(GeneSummaryView, opts())
    await flushPromises()
    expect(fetchSummary).toHaveBeenLastCalledWith('gene-1')

    useRoute().params = { geneId: 'gene-2' }
    await flushPromises()
    expect(fetchSummary).toHaveBeenLastCalledWith('gene-2')
  })

  it('shows the loading indicator while the summary is being fetched', () => {
    vi.spyOn(useGeneSummaryStore(), 'fetchPublicSummary').mockReturnValue(new Promise(() => {}))
    const wrapper = mount(GeneSummaryView, opts())
    expect(wrapper.find('.v-progress-linear').exists()).toBe(true)
  })

  it('shows the error message when the summary fails to load', async () => {
    vi.spyOn(useGeneSummaryStore(), 'fetchPublicSummary').mockRejectedValue(
      new Error('Server down')
    )
    const wrapper = mount(GeneSummaryView, opts())
    await flushPromises()
    expect(wrapper.text()).toContain('Server down')
    expect(logger.error).toHaveBeenCalled()
  })

  it('shows the no-curations message when there is no summary', async () => {
    vi.spyOn(useGeneSummaryStore(), 'fetchPublicSummary').mockResolvedValue(undefined as never)
    vi.spyOn(useGenesStore(), 'fetchGeneById').mockRejectedValue(new Error('not found'))
    const wrapper = mount(GeneSummaryView, opts())
    await flushPromises()
    expect(wrapper.text()).toContain('No Curations Found')
    expect(logger.warn).toHaveBeenCalled()
  })
})

describe('GenesTable', () => {
  it('loads genes on mount for an authenticated user and shows the count', async () => {
    useAuthStore().isAuthenticated = true
    const genes = useGenesStore()
    const fetchGenes = vi.spyOn(genes, 'fetchGenes').mockImplementation(async () => {
      genes.genes = [{ id: 'g1', approved_symbol: 'PKD1', hgnc_id: 'HGNC:1' }] as never
      return undefined as never
    })
    const wrapper = mount(GenesTable, opts())
    await flushPromises()

    expect(fetchGenes).toHaveBeenCalledWith({ page: 1 })
    expect(wrapper.text()).toContain('1 genes')
    expect(wrapper.text()).toContain('PKD1')
  })

  it('swallows a failed load (the store error is shown, no toast)', async () => {
    useAuthStore().isAuthenticated = true
    vi.spyOn(useGenesStore(), 'fetchGenes').mockRejectedValue(new Error('boom'))
    mount(GenesTable, opts())
    await flushPromises()
    expect(showError).not.toHaveBeenCalled()
  })

  it('debounces the search box and runs a search with the typed query', async () => {
    vi.useFakeTimers()
    useAuthStore().isAuthenticated = true
    const genes = useGenesStore()
    vi.spyOn(genes, 'fetchGenes').mockResolvedValue(undefined as never)
    const searchGenes = vi.spyOn(genes, 'searchGenes').mockResolvedValue(undefined as never)
    const wrapper = mount(GenesTable, opts())
    await flushPromises()

    const input = wrapper.find('input[type="text"]')
    await input.setValue('PKD')
    vi.advanceTimersByTime(300)
    await flushPromises()

    expect(searchGenes).toHaveBeenCalledWith(expect.objectContaining({ query: 'PKD', page: 1 }))
    vi.useRealTimers()
  })
})

describe('SchemaManagement', () => {
  const schemaRow = {
    id: 's1',
    name: 'ClinGen precuration',
    schema_type: 'precuration',
    is_active: true,
    version: '1.0.0',
    created_at: '2026-01-01T00:00:00Z'
  }

  it('lists schemas returned by the store', async () => {
    vi.spyOn(useSchemasStore(), 'fetchSchemas').mockImplementation(async () => {
      useSchemasStore().schemas = [schemaRow] as never
      return undefined as never
    })
    const wrapper = mount(SchemaManagement, opts())
    await flushPromises()
    expect(wrapper.text()).toContain('ClinGen precuration')
  })

  it('explains that the feature is unavailable when the endpoint returns 404', async () => {
    vi.spyOn(useSchemasStore(), 'fetchSchemas').mockRejectedValue({ response: { status: 404 } })
    mount(SchemaManagement, opts())
    await flushPromises()
    expect(showError).toHaveBeenCalledWith(
      'Schema management is not yet available. This feature is under development.'
    )
  })

  it('reports a generic load failure for other errors', async () => {
    vi.spyOn(useSchemasStore(), 'fetchSchemas').mockRejectedValue(new Error('500'))
    mount(SchemaManagement, opts())
    await flushPromises()
    expect(showError).toHaveBeenCalledWith('Failed to load schemas. Please refresh.')
  })

  it('deletes a schema after confirmation and reports success', async () => {
    const schemas = useSchemasStore()
    schemas.schemas = [schemaRow] as never
    vi.spyOn(schemas, 'fetchSchemas').mockResolvedValue(undefined as never)
    const deleteSchema = vi.spyOn(schemas, 'deleteSchema').mockResolvedValue(undefined as never)
    vi.stubGlobal(
      'confirm',
      vi.fn(() => true)
    )
    const wrapper = mount(SchemaManagement, opts())
    await flushPromises()

    await (
      wrapper.vm as unknown as { deleteSchema: (s: typeof schemaRow) => Promise<void> }
    ).deleteSchema(schemaRow)
    expect(deleteSchema).toHaveBeenCalledWith('s1')
    expect(showSuccess).toHaveBeenCalledWith('Schema "ClinGen precuration" deleted successfully')
    vi.unstubAllGlobals()
  })

  it('does nothing when deletion is cancelled', async () => {
    const schemas = useSchemasStore()
    vi.spyOn(schemas, 'fetchSchemas').mockResolvedValue(undefined as never)
    const deleteSchema = vi.spyOn(schemas, 'deleteSchema').mockResolvedValue(undefined as never)
    vi.stubGlobal(
      'confirm',
      vi.fn(() => false)
    )
    const wrapper = mount(SchemaManagement, opts())
    await flushPromises()

    await (
      wrapper.vm as unknown as { deleteSchema: (s: typeof schemaRow) => Promise<void> }
    ).deleteSchema(schemaRow)
    expect(deleteSchema).not.toHaveBeenCalled()
    vi.unstubAllGlobals()
  })
})

describe('SchemaEditor', () => {
  const schema = {
    id: 's1',
    name: 'Curation schema',
    version: '2.0.0',
    usage_count: 0,
    json_schema: { properties: { a: {} }, required: ['a'] },
    scoring_config: null
  }

  beforeEach(() => {
    routeState.params = { id: 's1' }
  })

  it('loads the schema and shows its field count', async () => {
    vi.spyOn(useSchemasStore(), 'fetchSchemaById').mockResolvedValue(schema as never)
    const wrapper = mount(SchemaEditor, opts())
    await flushPromises()
    expect(wrapper.text()).toContain('Curation schema')
  })

  it('shows the error when the schema cannot be loaded', async () => {
    vi.spyOn(useSchemasStore(), 'fetchSchemaById').mockRejectedValue(new Error('Not found'))
    const wrapper = mount(SchemaEditor, opts())
    await flushPromises()
    expect(wrapper.text()).toContain('Not found')
    expect(logger.error).toHaveBeenCalledWith(
      'Failed to load schema:',
      expect.objectContaining({ error: 'Not found' })
    )
  })

  afterEach(() => {
    routeState.params = {}
  })
})
