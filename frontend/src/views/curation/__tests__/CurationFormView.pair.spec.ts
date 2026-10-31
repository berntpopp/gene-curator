/** MUI-03: a curation uses its own or its precuration's workflow pair; the scope default last. */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import CurationFormView from '@/views/curation/CurationFormView.vue'
import { useSchemasStore } from '@/stores/schemas'
import { useScopesStore } from '@/stores/scopes'
import { useCurationsStore } from '@/stores/curations'
import { usePrecurationsStore } from '@/stores/precurations'
import { useGenesStore } from '@/stores/genes'

const routeState = vi.hoisted(() => ({
  params: {} as Record<string, string>,
  query: {} as Record<string, string>
}))
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  useRoute: () => routeState,
  onBeforeRouteLeave: vi.fn()
}))
vi.mock('@/composables/useLogger', () => ({
  useLogger: () => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() })
}))

type Stores = {
  schemas: ReturnType<typeof useSchemasStore>
  scopes: ReturnType<typeof useScopesStore>
  curations: ReturnType<typeof useCurationsStore>
  precurations: ReturnType<typeof usePrecurationsStore>
  genes: ReturnType<typeof useGenesStore>
}

async function mountView(setup: (stores: Stores) => void) {
  const stores: Stores = {
    schemas: useSchemasStore(),
    scopes: useScopesStore(),
    curations: useCurationsStore(),
    precurations: usePrecurationsStore(),
    genes: useGenesStore()
  }
  vi.spyOn(stores.schemas, 'fetchSchemas').mockResolvedValue(undefined as never)
  vi.spyOn(stores.schemas, 'fetchWorkflowPairs').mockResolvedValue(undefined as never)
  vi.spyOn(stores.scopes, 'fetchScope').mockResolvedValue({
    default_workflow_pair_id: 'wp1'
  } as never)
  vi.spyOn(stores.scopes, 'fetchUserRole').mockResolvedValue('curator' as never)
  vi.spyOn(stores.curations, 'fetchCurations').mockResolvedValue({ curations: [] } as never)
  vi.spyOn(stores.precurations, 'fetchPrecurations').mockResolvedValue({
    precurations: []
  } as never)
  setup(stores)
  const wrapper = mount(CurationFormView, {
    global: { stubs: { SchemaDrivenCurationForm: true, ReviewFeedbackPanel: true } }
  })
  await flushPromises()
  return { vm: wrapper.vm as unknown as Record<string, unknown> }
}

beforeEach(() => {
  vi.clearAllMocks()
  setActivePinia(createPinia())
  routeState.query = {}
})

describe('CurationFormView workflow pair', () => {
  it("starts on the approved precuration's own pair, not the scope default (MUI-03)", async () => {
    routeState.params = { scopeId: 'sc1', geneId: 'g1' }
    const { vm } = await mountView(({ schemas, scopes, genes, precurations }) => {
      vi.spyOn(scopes, 'fetchScope').mockResolvedValue({
        default_workflow_pair_id: 'wp1',
        allowed_workflow_pair_ids: ['wp2']
      } as never)
      schemas.workflowPairs = [
        { id: 'wp1', precuration_schema_id: 'pre-kgdb', curation_schema_id: 'cur-kgdb' },
        { id: 'wp2', precuration_schema_id: 'pre-clingen', curation_schema_id: 'cur-clingen' }
      ] as never
      vi.spyOn(genes, 'fetchGeneById').mockResolvedValue({ approved_symbol: 'COL4A3' } as never)
      vi.spyOn(precurations, 'fetchCurationPrecuration').mockResolvedValue({
        id: 'p1',
        status: 'approved'
      } as never)
      vi.spyOn(precurations, 'fetchPrecurationById').mockResolvedValue({
        id: 'p1',
        precuration_schema_id: 'pre-clingen'
      } as never)
    })
    expect(vm.resolvedWorkflowPairId).toBe('wp2')
    expect(vm.resolvedSchemaId).toBe('cur-clingen')
  })

  it("takes a loaded curation's pair schema when it names no schema of its own", async () => {
    routeState.params = { scopeId: 'sc1', curationId: 'c1' }
    const { vm } = await mountView(({ schemas, curations }) => {
      schemas.workflowPairs = [
        { id: 'wp1', curation_schema_id: 'cur-kgdb' },
        { id: 'wp2', curation_schema_id: 'cur-clingen' }
      ] as never
      vi.spyOn(curations, 'fetchCurationById').mockResolvedValue({
        id: 'c1',
        status: 'draft',
        workflow_pair_id: 'wp2'
      } as never)
    })
    expect(vm.resolvedSchemaId).toBe('cur-clingen')
  })
})
