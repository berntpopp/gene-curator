import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import CurationFormView from '@/views/curation/CurationFormView.vue'
import { useSchemasStore } from '@/stores/schemas'
import { useScopesStore } from '@/stores/scopes'
import { useCurationsStore } from '@/stores/curations'
import { usePrecurationsStore } from '@/stores/precurations'
import { useGenesStore } from '@/stores/genes'

// #530: a gene split into several disease entities asks which one, never takes the first
const { routerReplace, routeState } = vi.hoisted(() => ({
  routerReplace: vi.fn(),
  routeState: { params: {} as Record<string, string>, query: {} as Record<string, string> }
}))
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn(), replace: routerReplace, back: vi.fn() }),
  useRoute: () => routeState,
  onBeforeRouteLeave: vi.fn()
}))
vi.mock('@/composables/useLogger', () => ({
  useLogger: () => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() })
}))

const row = (id: string, status: string) => ({ id, status })
// curation id -> its status and precuration (entity), when a test links them
const links: Record<string, { status: string; precuration_id: string }> = {}
const detail = (id: string) =>
  ({
    id,
    status: 'active',
    disease_name: `Disease ${id}`,
    mondo_id: `MONDO:${id}`,
    mode_of_inheritance: 'AD',
    ...links[id]
  }) as never

const approvedPrecuration = (id: string) => ({
  id,
  status: 'approved',
  disease_name: `Disease ${id}`,
  mondo_id: `MONDO:${id}`,
  mode_of_inheritance: 'AR'
})

async function mountView(
  rows: { id: string; status: string }[],
  query: Record<string, string>,
  approved: ReturnType<typeof approvedPrecuration>[] = [],
  scope: Record<string, unknown> = { default_workflow_pair_id: 'wp1' }
) {
  Object.assign(routeState, { params: { scopeId: 'sc1', geneId: 'g1' }, query })
  const curations = useCurationsStore()
  vi.spyOn(useSchemasStore(), 'fetchSchemas').mockResolvedValue(undefined as never)
  vi.spyOn(useSchemasStore(), 'fetchWorkflowPairs').mockResolvedValue(undefined as never)
  vi.spyOn(useScopesStore(), 'fetchScope').mockResolvedValue(scope as never)
  vi.spyOn(useScopesStore(), 'fetchUserRole').mockResolvedValue('curator' as never)
  vi.spyOn(useGenesStore(), 'fetchGeneById').mockResolvedValue({} as never)
  vi.spyOn(usePrecurationsStore(), 'fetchCurationPrecuration').mockResolvedValue({
    status: 'approved'
  } as never)
  vi.spyOn(usePrecurationsStore(), 'fetchPrecurations').mockResolvedValue({
    precurations: approved
  } as never)
  vi.spyOn(curations, 'createCuration').mockResolvedValue({ id: 'new1' } as never)
  vi.spyOn(curations, 'fetchCurations').mockResolvedValue({ curations: rows } as never)
  vi.spyOn(curations, 'fetchCurationById').mockImplementation(async id => detail(id))
  const wrapper = mount(CurationFormView, {
    global: { stubs: { SchemaDrivenCurationForm: true, ReviewFeedbackPanel: true } }
  })
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  vi.clearAllMocks()
  setActivePinia(createPinia())
  for (const id of Object.keys(links)) delete links[id]
})

describe('CurationFormView entity choice', () => {
  it('asks which open curation to open when several are open', async () => {
    const wrapper = await mountView([row('a', 'draft'), row('b', 'draft')], {})
    const list = wrapper.find('[data-testid="entity-choices"]')
    expect(list.text()).toContain('Disease a · MONDO:a · Autosomal dominant')
    expect(list.text()).toContain('Disease b')
    expect(routerReplace).not.toHaveBeenCalled()
    await wrapper.findAll('.v-list-item')[1]!.trigger('click')
    expect(routerReplace).toHaveBeenCalledWith({
      name: 'curation-edit',
      params: { scopeId: 'sc1', curationId: 'b' }
    })
  })

  it('asks which active curation to re-curate when several are active', async () => {
    const wrapper = await mountView([row('a', 'active'), row('b', 'active')], { recurate: '1' })
    await wrapper.findAll('.v-list-item')[0]!.trigger('click')
    expect(routerReplace).toHaveBeenCalledWith({ query: { from: 'a' } })
  })

  it('re-curates the only active curation without asking', async () => {
    const wrapper = await mountView([row('a', 'active')], { recurate: '1' })
    expect(wrapper.find('[data-testid="entity-choices"]').exists()).toBe(false)
    expect(routerReplace).toHaveBeenCalledWith({ query: { from: 'a' } })
  })

  it('asks which approved entity to curate when several exist and none is open', async () => {
    const wrapper = await mountView([], {}, [approvedPrecuration('p1'), approvedPrecuration('p2')])
    const list = wrapper.find('[data-testid="entity-choices"]')
    expect(list.text()).toContain('Disease p1 · MONDO:p1 · Autosomal recessive')
    expect(list.text()).toContain('Disease p2')
    expect(useCurationsStore().createCuration).not.toHaveBeenCalled()
    await wrapper.findAll('.v-list-item')[1]!.trigger('click')
    expect(routerReplace).toHaveBeenCalledWith({ query: { precuration_id: 'p2' } })
  })

  it('asks across every entity: open draft opens, active re-curates, the rest starts', async () => {
    Object.assign(links, {
      d1: { status: 'draft', precuration_id: 'p1' },
      a1: { status: 'active', precuration_id: 'p2' }
    })
    const entities = ['p1', 'p2', 'p3'].map(approvedPrecuration)
    const wrapper = await mountView([row('d1', 'draft'), row('a1', 'active')], {}, entities)
    const items = () => wrapper.findAll('[data-testid="entity-choices"] .v-list-item')
    expect(items()).toHaveLength(3)
    expect(routerReplace).not.toHaveBeenCalled()
    for (const i of [0, 1, 2]) {
      await items()[i]!.trigger('click')
      await flushPromises()
    }
    expect(routerReplace.mock.calls.map(([to]) => to)).toEqual([
      { name: 'curation-edit', params: { scopeId: 'sc1', curationId: 'd1' } },
      { query: { from: 'a1' } },
      { query: { precuration_id: 'p3' } }
    ])
    expect(useCurationsStore().createCuration).not.toHaveBeenCalled()
  })

  it('lists a legacy open curation without an entity link so it can be continued', async () => {
    const legacy = { status: 'draft', precuration_id: null as never }
    Object.assign(links, { l1: legacy, a1: { status: 'active', precuration_id: 'p2' } })
    const entities = ['p1', 'p2'].map(approvedPrecuration)
    const wrapper = await mountView([row('l1', 'draft'), row('a1', 'active')], {}, entities)
    const items = () => wrapper.findAll('[data-testid="entity-choices"] .v-list-item')
    expect(items()).toHaveLength(3)
    expect(items()[2]!.text()).toContain('Disease l1 · MONDO:l1 · Autosomal dominant · draft')
    await items()[2]!.trigger('click')
    expect(routerReplace).toHaveBeenCalledWith({
      name: 'curation-edit',
      params: { scopeId: 'sc1', curationId: 'l1' }
    })
  })

  it('starts the curation of the precuration named in the route', async () => {
    await mountView([], { precuration_id: 'p2' }, [approvedPrecuration('p1')])
    expect(useCurationsStore().createCuration).toHaveBeenCalledWith(
      expect.objectContaining({
        gene_id: 'g1',
        scope_id: 'sc1',
        workflow_pair_id: 'wp1',
        precuration_id: 'p2'
      })
    )
    expect(routerReplace).toHaveBeenCalledWith({
      name: 'curation-edit',
      params: { scopeId: 'sc1', curationId: 'new1' }
    })
  })

  it("starts a chosen precuration's curation on its own pair (MUI-03)", async () => {
    useSchemasStore().workflowPairs = [
      { id: 'wp1', precuration_schema_id: 'pre-a' },
      { id: 'wp2', precuration_schema_id: 'pre-b' }
    ] as never
    vi.spyOn(usePrecurationsStore(), 'fetchPrecurationById').mockResolvedValue({
      id: 'p2',
      precuration_schema_id: 'pre-b'
    } as never)
    const scope = { default_workflow_pair_id: 'wp1', allowed_workflow_pair_ids: ['wp2'] }
    await mountView([], { precuration_id: 'p2' }, [], scope)
    expect(useCurationsStore().createCuration).toHaveBeenCalledWith(
      expect.objectContaining({ precuration_id: 'p2', workflow_pair_id: 'wp2' })
    )
  })

  it('leaves a refused start (409) to the open-curation redirect', async () => {
    vi.spyOn(useCurationsStore(), 'createCuration').mockImplementationOnce(async () => {
      useCurationsStore().error = { message: 'blocked', openCurationId: 'c9' }
      throw new Error('409')
    })
    await mountView([], { precuration_id: 'p2' })
    expect(routerReplace).toHaveBeenCalledTimes(1)
    expect(routerReplace).toHaveBeenCalledWith({
      name: 'curation-edit',
      params: { scopeId: 'sc1', curationId: 'c9' }
    })
  })

  it('opens the open curation a create was refused for (409)', async () => {
    await mountView([], {})
    useCurationsStore().error = { message: 'blocked', openCurationId: 'c9' }
    await flushPromises()
    expect(routerReplace).toHaveBeenCalledWith({
      name: 'curation-edit',
      params: { scopeId: 'sc1', curationId: 'c9' }
    })
  })
})
