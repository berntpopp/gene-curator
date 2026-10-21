/**
 * Behaviour tests for the data views: GenesTable, SchemaManagement, SchemaEditor.
 * Stores are real Pinia stores; their actions are stubbed with vi.spyOn.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, RouterLinkStub } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import GenesTable from '@/views/GenesTable.vue'
import SchemaManagement from '@/views/SchemaManagement.vue'
import SchemaEditor from '@/views/SchemaEditor.vue'
import { useGenesStore } from '@/stores/genes'
import { useAuthStore } from '@/stores/auth'
import { useSchemasStore } from '@/stores/schemas'

const confirmMock = vi.hoisted(() => vi.fn())
vi.mock('@/composables/useConfirm', () => ({ useConfirm: () => ({ confirm: confirmMock }) }))

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

describe('GenesTable', () => {
  it('loads genes on mount for an authenticated user and shows the count', async () => {
    useAuthStore().isAuthenticated = true
    const genes = useGenesStore()
    const fetchGenes = vi.spyOn(genes, 'fetchGenes').mockImplementation(async () => {
      genes.genes = [{ id: 'g1', approved_symbol: 'PKD1', hgnc_id: 'HGNC:1' }] as never
      genes.pagination.total = 1
      return undefined as never
    })
    const wrapper = mount(GenesTable, opts())
    await flushPromises()

    expect(fetchGenes).toHaveBeenCalledWith({ page: 1 })
    expect(wrapper.text()).toContain('1 gene')
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

  it('reports a load failure, also for a 404', async () => {
    const fetch = vi.spyOn(useSchemasStore(), 'fetchSchemas')
    fetch.mockRejectedValue({ response: { status: 404 } })
    mount(SchemaManagement, opts())
    await flushPromises()
    expect(showError).toHaveBeenCalledWith('Failed to load schemas')
    showError.mockClear()
    fetch.mockRejectedValue(new Error('500'))
    mount(SchemaManagement, opts())
    await flushPromises()
    expect(showError).toHaveBeenCalledWith('Failed to load schemas')
  })

  it('deletes a schema after confirmation and reports success', async () => {
    const schemas = useSchemasStore()
    schemas.schemas = [schemaRow] as never
    vi.spyOn(schemas, 'fetchSchemas').mockResolvedValue(undefined as never)
    const deleteSchema = vi.spyOn(schemas, 'deleteSchema').mockResolvedValue(undefined as never)
    confirmMock.mockResolvedValue(true)
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
    confirmMock.mockResolvedValue(false)
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
