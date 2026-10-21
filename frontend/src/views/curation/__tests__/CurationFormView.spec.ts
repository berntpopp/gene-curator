import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import CurationFormView from '@/views/curation/CurationFormView.vue'
import { useSchemasStore } from '@/stores/schemas'
import { useScopesStore } from '@/stores/scopes'
import { useCurationsStore } from '@/stores/curations'
import { usePrecurationsStore } from '@/stores/precurations'
import { useGenesStore } from '@/stores/genes'
import { useNotificationsStore } from '@/stores/notifications'

const { routerPush, routerBack, routeState, logger } = vi.hoisted(() => ({
  routerPush: vi.fn(),
  routerBack: vi.fn(),
  routeState: {
    params: {} as Record<string, string>,
    query: {} as Record<string, string>
  },
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: routerPush, back: routerBack }),
  useRoute: () => routeState
}))
vi.mock('@/composables/useLogger', () => ({ useLogger: () => logger }))

type Vm = Record<string, unknown> & Record<string, (...args: never[]) => unknown>

const stubs = { SchemaDrivenCurationForm: true, CurationSchemaSelect: true }

const mountView = async (
  setup?: (stores: {
    schemas: ReturnType<typeof useSchemasStore>
    scopes: ReturnType<typeof useScopesStore>
    curations: ReturnType<typeof useCurationsStore>
    precurations: ReturnType<typeof usePrecurationsStore>
    genes: ReturnType<typeof useGenesStore>
  }) => void
) => {
  const schemas = useSchemasStore()
  const scopes = useScopesStore()
  const curations = useCurationsStore()
  const precurations = usePrecurationsStore()
  const genes = useGenesStore()
  vi.spyOn(schemas, 'fetchSchemas').mockResolvedValue(undefined as never)
  vi.spyOn(schemas, 'fetchWorkflowPairs').mockResolvedValue(undefined as never)
  vi.spyOn(scopes, 'fetchScope').mockResolvedValue({ default_workflow_pair_id: 'wp1' } as never)
  setup?.({ schemas, scopes, curations, precurations, genes })
  const wrapper = mount(CurationFormView, { global: { stubs } })
  await flushPromises()
  return {
    wrapper,
    schemas,
    scopes,
    curations,
    precurations,
    genes,
    vm: wrapper.vm as unknown as Vm
  }
}

beforeEach(() => {
  vi.clearAllMocks()
  setActivePinia(createPinia())
  routeState.params = { scopeId: 'sc1' }
  routeState.query = {}
})

describe('CurationFormView', () => {
  it('uses the scope default workflow pair to resolve the curation schema', async () => {
    const { wrapper, vm } = await mountView(({ schemas }) => {
      schemas.workflowPairs = [{ id: 'wp1', curation_schema_id: 'sch-wp' }] as never
    })
    expect(vm.resolvedSchemaId).toBe('sch-wp')
    expect(vm.resolvedWorkflowPairId).toBe('wp1')
    expect(wrapper.text()).toContain('New Curation')
  })

  it('auto-selects the only available curation schema', async () => {
    const { vm } = await mountView(({ schemas, scopes }) => {
      schemas.schemas = [{ id: 'only', schema_type: 'curation' }] as never
      vi.spyOn(scopes, 'fetchScope').mockResolvedValue({} as never)
    })
    expect(vm.resolvedSchemaId).toBe('only')
  })

  it('offers a schema picker when several schemas are available and remembers the choice', async () => {
    const { wrapper, vm } = await mountView(({ schemas, scopes }) => {
      schemas.schemas = [
        { id: 'a', schema_type: 'curation' },
        { id: 'b', schema_type: 'combined' }
      ] as never
      vi.spyOn(scopes, 'fetchScope').mockResolvedValue({} as never)
    })
    expect(vm.resolvedSchemaId).toBeUndefined()
    expect(wrapper.findComponent({ name: 'CurationSchemaSelect' }).exists()).toBe(true)
    ;(vm.handleSchemaSelected as (id: string) => void)('b')
    expect(vm.resolvedSchemaId).toBe('b')
    expect(logger.debug).toHaveBeenCalledWith('Schema selected', { schemaId: 'b' })
  })

  it('prefers the schema from the query string over the scope default', async () => {
    routeState.query = { schema_id: 'from-query' }
    const { vm } = await mountView(({ schemas }) => {
      schemas.workflowPairs = [{ id: 'wp1', curation_schema_id: 'sch-wp' }] as never
    })
    expect(vm.resolvedSchemaId).toBe('from-query')
  })

  it('reports that no schema is available', async () => {
    const { wrapper } = await mountView(({ scopes }) => {
      vi.spyOn(scopes, 'fetchScope').mockResolvedValue({} as never)
    })
    expect(wrapper.find('.v-alert').exists()).toBe(true)
  })

  it('loads an existing curation when editing and takes its schema and workflow pair', async () => {
    routeState.params = { scopeId: 'sc1', curationId: 'c1' }
    const { vm, curations } = await mountView(({ curations }) => {
      vi.spyOn(curations, 'fetchCurationById').mockResolvedValue({
        curation_schema_id: 'sch-c',
        workflow_pair_id: 'wp-c'
      } as never)
    })
    expect(curations.fetchCurationById).toHaveBeenCalledWith('c1')
    expect(vm.isEdit).toBe(true)
    expect(vm.resolvedSchemaId).toBe('sch-c')
    expect(vm.resolvedWorkflowPairId).toBe('wp-c')
  })

  it('falls back to the curation gene on the edit route and opens active curations read-only', async () => {
    routeState.params = { scopeId: 'sc1', curationId: 'c1' }
    const { wrapper, genes } = await mountView(({ curations, genes }) => {
      vi.spyOn(curations, 'fetchCurationById').mockResolvedValue({
        curation_schema_id: 'sch-c',
        gene_id: 'g-9',
        workflow_stage: 'active'
      } as never)
      vi.spyOn(genes, 'fetchGeneById').mockResolvedValue({ approved_symbol: 'HNF1B' } as never)
    })
    expect(genes.fetchGeneById).toHaveBeenCalledWith('g-9')
    const form = wrapper.findComponent({ name: 'SchemaDrivenCurationForm' })
    expect(form.props('gene')).toEqual({ symbol: 'HNF1B' })
    expect(form.props('readonly')).toBe(true)
  })

  it('finds the workflow pair through the resolved schema when the scope has no default', async () => {
    routeState.query = { schema_id: 'sch-x' }
    const { vm } = await mountView(({ schemas, scopes }) => {
      schemas.workflowPairs = [{ id: 'wp-x', curation_schema_id: 'sch-x' }] as never
      vi.spyOn(scopes, 'fetchScope').mockResolvedValue({} as never)
    })
    expect(vm.resolvedWorkflowPairId).toBe('wp-x')
  })

  it('maps the gene to the symbol the form displays', async () => {
    routeState.params = { scopeId: 'sc1', geneId: 'g1' }
    const { vm } = await mountView(({ genes, precurations }) => {
      vi.spyOn(genes, 'fetchGeneById').mockResolvedValue({ approved_symbol: 'HNF1B' } as never)
      vi.spyOn(precurations, 'fetchPrecurations').mockImplementation(async () => {
        precurations.precurations = [{ status: 'approved' }] as never
        return undefined as never
      })
    })
    expect(vm.formGene).toEqual({ symbol: 'HNF1B' })
    expect(vm.precurationStatus).toBe('approved')
  })

  it('sends the user to the precuration form when none is approved', async () => {
    routeState.params = { scopeId: 'sc1', geneId: 'g1' }
    const notifications = useNotificationsStore()
    const toast = vi.spyOn(notifications, 'addToast')
    await mountView(({ genes, precurations }) => {
      vi.spyOn(genes, 'fetchGeneById').mockResolvedValue({ approved_symbol: 'HNF1B' } as never)
      vi.spyOn(precurations, 'fetchPrecurations').mockImplementation(async () => {
        precurations.precurations = [{ status: 'draft' }] as never
        return undefined as never
      })
    })
    expect(toast).toHaveBeenCalledWith(
      'Please complete and approve a precuration before starting curation',
      'warning'
    )
    expect(routerPush).toHaveBeenCalledWith({
      name: 'gene-precuration-create',
      params: { scopeId: 'sc1', geneId: 'g1' }
    })
  })

  it('reopens an existing unapproved precuration instead of creating a new one', async () => {
    routeState.params = { scopeId: 'sc1', geneId: 'g1' }
    await mountView(({ genes, precurations }) => {
      vi.spyOn(genes, 'fetchGeneById').mockResolvedValue({ approved_symbol: 'X' } as never)
      vi.spyOn(precurations, 'fetchPrecurations').mockImplementation(async () => {
        precurations.precurations = [{ id: 'p9', status: 'draft' }] as never
        return {} as never
      })
    })
    expect(routerPush).toHaveBeenCalledWith({
      name: 'precuration-edit',
      params: { scopeId: 'sc1', precurationId: 'p9' }
    })
  })

  it('treats a failing precuration lookup as no precuration', async () => {
    routeState.query = { gene_id: 'g2' }
    const { vm } = await mountView(({ genes, precurations }) => {
      vi.spyOn(genes, 'fetchGeneById').mockResolvedValue(null as never)
      vi.spyOn(precurations, 'fetchPrecurations').mockRejectedValue(new Error('boom'))
    })
    expect(vm.precurationStatus).toBe('none')
    expect(logger.error).toHaveBeenCalledWith(
      'Failed to check precuration status',
      expect.objectContaining({ error: 'boom' })
    )
  })

  it('logs a scope load failure and a data load failure', async () => {
    await mountView(({ scopes }) => {
      vi.spyOn(scopes, 'fetchScope').mockRejectedValue(new Error('scope down'))
    })
    expect(logger.error).toHaveBeenCalledWith(
      'Failed to load scope',
      expect.objectContaining({ error: 'scope down' })
    )
    routeState.params = { scopeId: 'sc1', curationId: 'c1' }
    const toast = vi.spyOn(useNotificationsStore(), 'addToast')
    await mountView(({ curations }) => {
      vi.spyOn(curations, 'fetchCurationById').mockRejectedValue(new Error('gone'))
    })
    expect(toast).toHaveBeenCalledWith('Failed to load data', 'error')
  })

  it('opens the saved curation after a submit, using the store as the source of the id', async () => {
    const toast = vi.spyOn(useNotificationsStore(), 'addToast')
    const { vm, curations } = await mountView()
    curations.currentCuration = { id: 'new-1' } as never
    ;(vm.handleSubmit as () => void)()
    expect(toast).toHaveBeenCalledWith('Curation submitted successfully', 'success')
    expect(routerPush).toHaveBeenCalledWith({
      name: 'curation-detail',
      params: { scopeId: 'sc1', curationId: 'new-1' }
    })
  })

  it('falls back to the scope dashboard when no curation id is known after a submit', async () => {
    const { vm } = await mountView()
    ;(vm.handleSubmit as () => void)()
    expect(routerPush).toHaveBeenCalledWith({
      name: 'scope-dashboard',
      params: { scopeId: 'sc1' }
    })
  })

  it('cancels back to the scope dashboard from a gene, otherwise one page back', async () => {
    const { vm } = await mountView()
    ;(vm.handleCancel as () => void)()
    expect(routerBack).toHaveBeenCalled()
    routeState.params = { scopeId: 'sc1', geneId: 'g1' }
    const second = await mountView(({ genes, precurations }) => {
      vi.spyOn(genes, 'fetchGeneById').mockResolvedValue({} as never)
      vi.spyOn(precurations, 'fetchPrecurations').mockImplementation(async () => {
        precurations.precurations = [{ status: 'approved' }] as never
        return undefined as never
      })
    })
    ;(second.vm.handleCancel as () => void)()
    expect(routerPush).toHaveBeenCalledWith({ name: 'scope-dashboard', params: { scopeId: 'sc1' } })
  })

  it('announces a saved draft', async () => {
    const toast = vi.spyOn(useNotificationsStore(), 'addToast')
    const { vm } = await mountView()
    ;(vm.handleSaved as () => void)()
    expect(toast).toHaveBeenCalledWith('Draft saved', 'info')
  })
})
