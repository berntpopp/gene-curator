import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { defineComponent, h, inject, onMounted, ref, type Ref } from 'vue'
import { WORKSPACE_FRAME, type WorkspaceFrame } from '@/components/workspace/useWorkspaceFrame'
import { useNotificationsStore } from '@/stores/notifications'
import CurationFormView from '@/views/curation/CurationFormView.vue'
import { useSchemasStore } from '@/stores/schemas'
import { useScopesStore } from '@/stores/scopes'
import { useCurationsStore } from '@/stores/curations'
import { usePrecurationsStore } from '@/stores/precurations'
import { useGenesStore } from '@/stores/genes'

const { routerPush, routerReplace, routerBack, routeState, logger } = vi.hoisted(() => ({
  routerPush: vi.fn(),
  routerReplace: vi.fn(),
  routerBack: vi.fn(),
  routeState: {
    params: {} as Record<string, string>,
    query: {} as Record<string, string>
  },
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: routerPush, replace: routerReplace, back: routerBack }),
  useRoute: () => routeState,
  onBeforeRouteLeave: vi.fn()
}))
const confirmMock = vi.hoisted(() => vi.fn())
vi.mock('@/composables/useConfirm', () => ({ useConfirm: () => ({ confirm: confirmMock }) }))
vi.mock('@/composables/useLogger', () => ({ useLogger: () => logger }))

type Vm = Record<string, unknown> & Record<string, (...args: never[]) => unknown>

const stubs = {
  SchemaDrivenCurationForm: true,
  CurationSchemaSelect: true,
  ReviewFeedbackPanel: true,
  'router-link': { props: ['to'], template: '<a :href="to"><slot /></a>' }
}

const mountView = async (
  setup?: (stores: {
    schemas: ReturnType<typeof useSchemasStore>
    scopes: ReturnType<typeof useScopesStore>
    curations: ReturnType<typeof useCurationsStore>
    precurations: ReturnType<typeof usePrecurationsStore>
    genes: ReturnType<typeof useGenesStore>
  }) => void,
  extraStubs: Record<string, unknown> = {}
) => {
  const schemas = useSchemasStore()
  const scopes = useScopesStore()
  const curations = useCurationsStore()
  const precurations = usePrecurationsStore()
  const genes = useGenesStore()
  vi.spyOn(schemas, 'fetchSchemas').mockResolvedValue(undefined as never)
  vi.spyOn(schemas, 'fetchWorkflowPairs').mockResolvedValue(undefined as never)
  vi.spyOn(scopes, 'fetchScope').mockResolvedValue({ default_workflow_pair_id: 'wp1' } as never)
  vi.spyOn(scopes, 'fetchUserRole').mockResolvedValue('curator' as never)
  vi.spyOn(curations, 'fetchCurations').mockResolvedValue({ curations: [] } as never)
  setup?.({ schemas, scopes, curations, precurations, genes })
  const wrapper = mount(CurationFormView, { global: { stubs: { ...stubs, ...extraStubs } } })
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
  it('keeps one skeleton (same element) from loading until the form reports ready', async () => {
    let release!: (v: never) => void
    const schemas = useSchemasStore()
    const scopes = useScopesStore()
    vi.spyOn(schemas, 'fetchSchemas').mockResolvedValue(undefined as never)
    vi.spyOn(schemas, 'fetchWorkflowPairs').mockResolvedValue(undefined as never)
    vi.spyOn(scopes, 'fetchScope').mockReturnValue(new Promise(r => (release = r as never)))
    vi.spyOn(scopes, 'fetchUserRole').mockResolvedValue('curator' as never)
    schemas.workflowPairs = [{ id: 'wp1', curation_schema_id: 'sch-wp' }] as never
    const wrapper = mount(CurationFormView, { global: { stubs } })
    await flushPromises()
    const skeletons = () => wrapper.findAll('.v-skeleton-loader')
    expect(skeletons()).toHaveLength(1)
    const first = skeletons()[0]?.element

    release({ default_workflow_pair_id: 'wp1' } as never)
    await flushPromises()
    // schema resolved, form mounted but not ready: still the same single skeleton
    expect(wrapper.find('schema-driven-curation-form-stub').exists()).toBe(true)
    expect(skeletons()).toHaveLength(1)
    expect(skeletons()[0]?.element).toBe(first)

    wrapper.findComponent({ name: 'SchemaDrivenCurationForm' }).vm.$emit('ready')
    await flushPromises()
    expect(skeletons()).toHaveLength(0)
  })

  it('uses the scope default workflow pair to resolve the curation schema', async () => {
    const { wrapper, vm } = await mountView(({ schemas }) => {
      schemas.workflowPairs = [{ id: 'wp1', curation_schema_id: 'sch-wp' }] as never
    })
    expect(vm.resolvedSchemaId).toBe('sch-wp')
    expect(vm.resolvedWorkflowPairId).toBe('wp1')
    expect(wrapper.text()).toContain('New curation')
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
      vi.spyOn(precurations, 'fetchCurationPrecuration').mockImplementation(async () => {
        return { status: 'approved' } as never
      })
    })
    expect(vm.formGene).toEqual({ symbol: 'HNF1B' })
    expect(vm.precurationStatus).toBe('approved')
  })

  it.each([{}, { from: 'c-active' }])(
    'opens the open curation of the gene instead of starting another (query %o)',
    async query => {
      routeState.params = { scopeId: 'sc1', geneId: 'g1' }
      routeState.query = query as Record<string, string>
      const { curations, precurations } = await mountView(({ curations, precurations, genes }) => {
        vi.spyOn(genes, 'fetchGeneById').mockResolvedValue({ approved_symbol: 'PKD1' } as never)
        vi.spyOn(curations, 'fetchCurations').mockResolvedValue({
          curations: [
            { id: 'c-active', status: 'active' },
            { id: 'c-draft', status: 'draft' }
          ]
        } as never)
        vi.spyOn(precurations, 'fetchCurationPrecuration')
      })
      expect(curations.fetchCurations).toHaveBeenCalledWith({ scope_id: 'sc1', gene_id: 'g1' })
      expect(routerReplace).toHaveBeenCalledWith({
        name: 'curation-edit',
        params: { scopeId: 'sc1', curationId: 'c-draft' }
      })
      expect(precurations.fetchCurationPrecuration).not.toHaveBeenCalled()
    }
  )

  it('sends the user to the precuration form when none is approved', async () => {
    routeState.params = { scopeId: 'sc1', geneId: 'g1' }
    const notifications = useNotificationsStore()
    const toast = vi.spyOn(notifications, 'addToast')
    await mountView(({ genes, precurations }) => {
      vi.spyOn(genes, 'fetchGeneById').mockResolvedValue({ approved_symbol: 'HNF1B' } as never)
      vi.spyOn(precurations, 'fetchCurationPrecuration').mockImplementation(async () => {
        return { status: 'draft' } as never
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
      vi.spyOn(precurations, 'fetchCurationPrecuration').mockImplementation(async () => {
        return { id: 'p9', status: 'draft' } as never
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
      vi.spyOn(precurations, 'fetchCurationPrecuration').mockRejectedValue(new Error('boom'))
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

  it.each([404, 403])(
    'shows not found, never an empty form, when the curation load is %i',
    async status => {
      routeState.params = { scopeId: 'sc1', curationId: 'c1' }
      const { wrapper } = await mountView(({ curations }) => {
        vi.spyOn(curations, 'fetchCurationById').mockRejectedValue({ response: { status } })
      })
      expect(wrapper.find('[data-testid="curation-not-found"]').exists()).toBe(true)
      expect(wrapper.findComponent({ name: 'SchemaDrivenCurationForm' }).exists()).toBe(false)
      expect(wrapper.findComponent({ name: 'CurationSchemaSelect' }).exists()).toBe(false)
      expect(wrapper.text()).not.toContain('No Curation Schema Available')
    }
  )

  it('shows not found when the scope is hidden from the user', async () => {
    routeState.params = { scopeId: 'sc1', curationId: 'c1' }
    const { wrapper } = await mountView(({ scopes, curations }) => {
      vi.spyOn(scopes, 'fetchScope').mockRejectedValue({ response: { status: 404 } })
      vi.spyOn(curations, 'fetchCurationById').mockResolvedValue({} as never)
    })
    expect(wrapper.find('[data-testid="curation-not-found"]').exists()).toBe(true)
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

  it('re-curation: starts from the active curation and opens the new one after submit', async () => {
    routeState.query = { from: 'active-1' }
    const { wrapper, vm, curations } = await mountView(({ schemas }) => {
      schemas.workflowPairs = [{ id: 'wp1', curation_schema_id: 'sch-wp' }] as never
    })
    const form = wrapper.findComponent({ name: 'SchemaDrivenCurationForm' })
    expect(form.props('prefillFrom')).toBe('active-1')
    curations.currentCuration = { id: 'active-1' } as never // loaded as the prefill source
    ;(vm.handleSubmit as (id: string) => void)('new-2')
    expect(routerPush).toHaveBeenCalledWith({
      name: 'curation-detail',
      params: { scopeId: 'sc1', curationId: 'new-2' }
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
      vi.spyOn(precurations, 'fetchCurationPrecuration').mockImplementation(async () => {
        return { status: 'approved' } as never
      })
    })
    ;(second.vm.handleCancel as () => void)()
    expect(routerPush).toHaveBeenCalledWith({ name: 'scope-dashboard', params: { scopeId: 'sc1' } })
  })

  describe('workspace frame', () => {
    // Stands in for the form: attaches to the frame like SchemaDrivenCurationForm does
    const FrameForm = defineComponent({
      name: 'SchemaDrivenCurationForm',
      emits: ['ready', 'submit'],
      setup(_, { emit }) {
        const frame = inject(WORKSPACE_FRAME)!
        const evidence = ref<unknown>({ a: 1 })
        const saving = ref(false)
        const savedAt = ref<number | null>(null)
        const save = vi.fn().mockResolvedValue(true)
        frame.attachForm({ evidence, saving, savedAt, save })
        frame.attachSubmit({ canSubmit: ref(true), run: () => emit('submit') })
        frame.setScore({
          trace: null,
          total: 7.5,
          classification: 'Moderate',
          hasContradictory: false
        })
        frame.setMeta({ disease: 'Alport syndrome', moi: 'X-linked' })
        onMounted(() => emit('ready'))
        formApi.frame = frame
        formApi.evidence = evidence
        formApi.save = save
        return () => h('div', { class: 'form' })
      }
    })
    const formApi = {} as {
      evidence: Ref<unknown>
      save: ReturnType<typeof vi.fn>
      frame: WorkspaceFrame
    }

    async function mountFramed(curation: Record<string, unknown> = { workflow_stage: 'curation' }) {
      routeState.params = { scopeId: 'sc1', curationId: 'c1' }
      const wrapper = await mountView(
        ({ schemas, scopes, curations, genes }) => {
          schemas.workflowPairs = [{ id: 'wp1', curation_schema_id: 'sch' }] as never
          vi.spyOn(scopes, 'fetchScope').mockResolvedValue({
            default_workflow_pair_id: 'wp1',
            display_name: 'Kidney genetics'
          } as never)
          vi.spyOn(curations, 'fetchCurationById').mockResolvedValue({
            curation_schema_id: 'sch',
            gene_id: 'g1',
            ...curation
          } as never)
          vi.spyOn(genes, 'fetchGeneById').mockResolvedValue({ approved_symbol: 'COL4A5' } as never)
        },
        { SchemaDrivenCurationForm: FrameForm }
      )
      await flushPromises()
      return wrapper
    }

    it('shows breadcrumb, stage, disease, saved state and the score panel', async () => {
      const { wrapper } = await mountFramed()
      expect(wrapper.find('nav[aria-label="Breadcrumb"]').text()).toContain('Kidney genetics')
      expect(wrapper.find('nav[aria-label="Breadcrumb"]').text()).toContain('COL4A5')
      expect(wrapper.find('h1').text()).toContain('COL4A5')
      expect(wrapper.text()).toContain('Alport syndrome')
      expect(wrapper.find('[aria-current="step"]').text()).toBe('Curation')
      expect(wrapper.text()).toContain('Saved')
      expect(wrapper.text()).toContain('Calculated classification')
      expect(wrapper.text()).toContain('7.5')
    })

    it('keeps the same score panel and checklist mounted while a new score is pending', async () => {
      const { wrapper } = await mountFramed()
      const panel = wrapper.get('.ws-panel').element
      const checklist = wrapper.get('.checklist').element
      formApi.frame.setScorePending(true)
      formApi.frame.setScore(null)
      await flushPromises()
      expect(wrapper.get('.ws-panel').element).toBe(panel)
      expect(wrapper.get('.checklist').element).toBe(checklist)
      expect(wrapper.find('.ws-panel .v-skeleton-loader').exists()).toBe(true)
      expect(wrapper.text()).not.toContain('7.5')
      expect(wrapper.text()).not.toContain('Ready to submit')
      formApi.frame.setScorePending(false)
      await flushPromises()
      expect(wrapper.get('.ws-panel').element).toBe(panel)
      expect(wrapper.find('.ws-panel .v-skeleton-loader').exists()).toBe(false)
      expect(wrapper.get('.ws-panel').text()).toContain('unavailable')
      wrapper.unmount()
    })

    // #470: a new curation (e.g. a re-curation prefill) has nothing on the server yet
    it('shows a prefilled new curation as unsaved until its first save', async () => {
      routeState.params = { scopeId: 'sc1', geneId: 'g1' }
      const { wrapper } = await mountView(
        ({ schemas, scopes, genes }) => {
          schemas.workflowPairs = [{ id: 'wp1', curation_schema_id: 'sch' }] as never
          vi.spyOn(scopes, 'fetchScope').mockResolvedValue({
            default_workflow_pair_id: 'wp1'
          } as never)
          vi.spyOn(genes, 'fetchGeneById').mockResolvedValue({ approved_symbol: 'PKD1' } as never)
        },
        { SchemaDrivenCurationForm: FrameForm }
      )
      await flushPromises()
      expect(wrapper.text()).toContain('Unsaved changes')
      formApi.evidence.value = {}
      await flushPromises()
      expect(wrapper.text()).not.toContain('Unsaved changes')
    })

    it('shows unsaved changes after an edit and saves from the header', async () => {
      const { wrapper } = await mountFramed()
      formApi.evidence.value = { a: 2 }
      await flushPromises()
      expect(wrapper.text()).toContain('Unsaved changes')
      await wrapper.find('[data-testid="ws-save"]').trigger('click')
      await flushPromises()
      expect(formApi.save).toHaveBeenCalledTimes(1)
      expect(wrapper.text()).not.toContain('Unsaved changes')
    })

    it('saves on Ctrl+S, including inside an input, but not inside a dialog', async () => {
      const { wrapper } = await mountFramed()
      void wrapper
      const input = document.createElement('input')
      document.body.append(input)
      input.dispatchEvent(
        new KeyboardEvent('keydown', { key: 's', ctrlKey: true, bubbles: true, cancelable: true })
      )
      expect(formApi.save).toHaveBeenCalledTimes(1)
      const dialog = document.createElement('div')
      dialog.setAttribute('role', 'dialog')
      const inner = document.createElement('input')
      dialog.append(inner)
      document.body.append(dialog)
      inner.dispatchEvent(
        new KeyboardEvent('keydown', { key: 's', ctrlKey: true, bubbles: true, cancelable: true })
      )
      expect(formApi.save).toHaveBeenCalledTimes(1)
      input.remove()
      dialog.remove()
    })

    it('warns on reload only while there are unsaved changes', async () => {
      await mountFramed()
      const fire = () => {
        const e = new Event('beforeunload', { cancelable: true })
        window.dispatchEvent(e)
        return e.defaultPrevented
      }
      expect(fire()).toBe(false)
      formApi.evidence.value = { a: 3 }
      await flushPromises()
      expect(fire()).toBe(true)
    })

    it('marks an active curation read-only: save and submit disabled, no Ctrl+S', async () => {
      const { wrapper } = await mountFramed({ workflow_stage: 'active' })
      expect(wrapper.find('[data-testid="ws-save"]').attributes('disabled')).toBeDefined()
      expect(wrapper.find('[data-testid="ws-submit"]').attributes('disabled')).toBeDefined()
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 's', ctrlKey: true }))
      expect(formApi.save).not.toHaveBeenCalled()
    })

    it('opens an in-review curation read-only with the reason (its /edit URL)', async () => {
      const { wrapper } = await mountFramed({
        workflow_stage: 'review',
        status: 'in_review',
        can_edit: false
      })
      expect(wrapper.find('[data-testid="ws-save"]').attributes('disabled')).toBeDefined()
      expect(wrapper.find('[data-testid="ws-submit"]').attributes('disabled')).toBeDefined()
      expect(wrapper.find('.form').attributes('readonly')).toBeDefined()
      expect(wrapper.find('[data-testid="ws-readonly"]').text()).toContain('in review')
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 's', ctrlKey: true }))
      expect(formApi.save).not.toHaveBeenCalled()
    })

    it('opens a draft read-only for someone who may not edit it', async () => {
      const { wrapper } = await mountFramed({ status: 'draft', can_edit: false })
      expect(wrapper.find('[data-testid="ws-readonly"]').text()).toContain('permission')
    })

    it("names the author of someone else's draft", async () => {
      const { wrapper } = await mountFramed({
        status: 'draft',
        can_edit: false,
        curator_name: 'Alice Smith'
      })
      expect(wrapper.find('[data-testid="ws-readonly"]').text()).toContain(
        'Read-only: this curation belongs to Alice Smith. Only its author can edit it.'
      )
    })

    it('keeps a returned (changes requested) curation editable for its curator', async () => {
      const { wrapper } = await mountFramed({ status: 'rejected', can_edit: true })
      expect(wrapper.find('[data-testid="ws-save"]').attributes('disabled')).toBeUndefined()
      expect(wrapper.find('[data-testid="ws-readonly"]').exists()).toBe(false)
    })

    it('leaves without asking after a submit', async () => {
      const { wrapper } = await mountFramed()
      formApi.evidence.value = { a: 4 }
      await flushPromises()
      await wrapper.find('[data-testid="ws-submit"]').trigger('click')
      await flushPromises()
      const e = new Event('beforeunload', { cancelable: true })
      window.dispatchEvent(e)
      expect(e.defaultPrevented).toBe(false)
    })

    it('shows an archived curation as the terminal stage, read-only as archived', async () => {
      const { wrapper } = await mountFramed({ workflow_stage: 'active', status: 'archived' })
      expect(wrapper.find('[aria-current="step"]').text()).toBe('Archived')
      expect(wrapper.find('[data-testid="ws-readonly"]').text()).toContain('archived')
      const other = await mountFramed({ status: 'archived', can_edit: false })
      expect(other.wrapper.find('[data-testid="ws-readonly"]').text()).toContain('archived')
    })
  })

  describe('who may start a curation and who sees review feedback', () => {
    it('shows a viewer the not-authorized notice instead of the form (new curation)', async () => {
      const { wrapper } = await mountView(({ scopes }) => {
        vi.spyOn(scopes, 'fetchUserRole').mockResolvedValue('viewer' as never)
      })
      expect(wrapper.find('[data-testid=no-curate-access]').exists()).toBe(true)
      expect(wrapper.find('schema-driven-curation-form-stub').exists()).toBe(false)
    })

    it.each(['viewer', 'reviewer'])('gives a %s no dead Save draft (#391)', async role => {
      const { wrapper } = await mountView(({ scopes }) => {
        vi.spyOn(scopes, 'fetchUserRole').mockResolvedValue(role as never)
      })
      expect(wrapper.find('[data-testid=no-curate-access]').exists()).toBe(true)
      expect(wrapper.find('[data-testid=ws-save]').exists()).toBe(false)
    })

    it('never shows the form when the role lookup fails, and retries', async () => {
      const { wrapper, scopes, schemas } = await mountView(({ scopes, schemas }) => {
        vi.spyOn(scopes, 'fetchUserRole').mockRejectedValue(new Error('500'))
        schemas.workflowPairs = [{ id: 'wp1', curation_schema_id: 'sch-wp' }] as never
      })
      expect(wrapper.text()).toContain('could not check')
      expect(wrapper.find('schema-driven-curation-form-stub').exists()).toBe(false)
      vi.mocked(scopes.fetchUserRole).mockResolvedValue('curator' as never)
      void schemas
      await wrapper.find('[data-testid=retry-access]').trigger('click')
      await flushPromises()
      expect(wrapper.find('[data-testid=no-curate-access]').exists()).toBe(false)
    })

    it('lets a curator through', async () => {
      const { wrapper } = await mountView(({ scopes, schemas }) => {
        vi.spyOn(scopes, 'fetchUserRole').mockResolvedValue('curator' as never)
        schemas.workflowPairs = [{ id: 'wp1', curation_schema_id: 'sch-wp' }] as never
      })
      expect(wrapper.find('[data-testid=no-curate-access]').exists()).toBe(false)
    })

    it('does not role-check when editing an existing curation', async () => {
      routeState.params = { scopeId: 'sc1', curationId: 'c1' }
      const { scopes } = await mountView(({ scopes, curations }) => {
        vi.spyOn(curations, 'fetchCurationById').mockResolvedValue({
          id: 'c1',
          status: 'draft'
        } as never)
        vi.spyOn(scopes, 'fetchUserRole').mockResolvedValue('viewer' as never)
      })
      expect(scopes.fetchUserRole).not.toHaveBeenCalled()
    })

    it('shows the review feedback panel for a draft being edited, not for a new curation', async () => {
      routeState.params = { scopeId: 'sc1', curationId: 'c1' }
      const edit = await mountView(({ curations }) => {
        vi.spyOn(curations, 'fetchCurationById').mockResolvedValue({
          id: 'c1',
          status: 'draft'
        } as never)
      })
      expect(edit.wrapper.find('review-feedback-panel-stub').exists()).toBe(true)
      routeState.params = { scopeId: 'sc1' }
      const fresh = await mountView()
      expect(fresh.wrapper.find('review-feedback-panel-stub').exists()).toBe(false)
    })
  })
})
