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
const detail = (id: string) =>
  ({
    id,
    status: 'active',
    disease_name: `Disease ${id}`,
    mondo_id: `MONDO:${id}`,
    mode_of_inheritance: 'AD'
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
  approved: ReturnType<typeof approvedPrecuration>[] = []
) {
  Object.assign(routeState, { params: { scopeId: 'sc1', geneId: 'g1' }, query })
  const curations = useCurationsStore()
  vi.spyOn(useSchemasStore(), 'fetchSchemas').mockResolvedValue(undefined as never)
  vi.spyOn(useSchemasStore(), 'fetchWorkflowPairs').mockResolvedValue(undefined as never)
  vi.spyOn(useScopesStore(), 'fetchScope').mockResolvedValue({
    default_workflow_pair_id: 'wp1'
  } as never)
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
