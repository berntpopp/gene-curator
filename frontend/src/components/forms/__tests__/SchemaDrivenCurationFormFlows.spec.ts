import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ref } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import SchemaDrivenCurationForm from '../SchemaDrivenCurationForm.vue'
import { stubs } from './schemaCurationFormStubs'
import { WORKSPACE_FRAME, createWorkspaceFrame } from '@/components/workspace/useWorkspaceFrame'

const confirmMock = vi.hoisted(() => vi.fn())
vi.mock('@/composables/useConfirm', () => ({ useConfirm: () => ({ confirm: confirmMock }) }))

const logger = vi.hoisted(() => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }))
const addToast = vi.hoisted(() => vi.fn())
const push = vi.hoisted(() => vi.fn())
const replace = vi.hoisted(() => vi.fn())
const recovery = vi.hoisted(() => ({
  clearRecovery: vi.fn(),
  restoreRecovery: vi.fn(),
  showRecoveryDialog: null as null | { value: boolean },
  lastSaved: null as null | { value: string | null }
}))
const PINNED = { id: 'v1', snapshot: { scoring_configuration: { engine: 'clingen_sop_v11' } } }
const curationsStore = vi.hoisted(() => ({
  currentCuration: null as unknown,
  fetchCurationById: vi.fn(),
  saveDraft: vi.fn(),
  createCuration: vi.fn(),
  submitCuration: vi.fn(),
  updateCuration: vi.fn(),
  calculateScore: vi.fn()
}))
const precurationsStore = vi.hoisted(() => ({
  precurations: [] as unknown[],
  fetchCurationPrecuration: vi.fn(),
  fetchPrecurationById: vi.fn()
}))
const schemasStore = vi.hoisted(() => ({
  getWorkflowPairById: vi.fn(),
  fetchSchemaById: vi.fn(),
  fetchPinnedVersion: vi.fn()
}))
const utils = vi.hoisted(() => ({
  isLegacyFormat: vi.fn(),
  migrateLegacyFormat: vi.fn()
}))

vi.mock('@/composables/useLogger', () => ({ useLogger: () => logger }))
vi.mock('vue-router', () => ({ useRouter: () => ({ push, replace }) }))
vi.mock('@/stores/schemas', () => ({
  useSchemasStore: () => ({
    getSchemaById: (id: string) => ({ id, name: 'Panel schema' }),
    getWorkflowPairById: schemasStore.getWorkflowPairById,
    fetchSchemaById: schemasStore.fetchSchemaById,
    fetchPinnedVersion: schemasStore.fetchPinnedVersion
  })
}))
vi.mock('@/stores/curations', () => ({ useCurationsStore: () => curationsStore }))
vi.mock('@/stores/precurations', () => ({ usePrecurationsStore: () => precurationsStore }))
vi.mock('@/stores/notifications', () => ({ useNotificationsStore: () => ({ addToast }) }))
vi.mock('@/utils/evidenceDataMigration', () => ({
  isLegacyFormat: utils.isLegacyFormat,
  migrateLegacyFormat: utils.migrateLegacyFormat
}))
vi.mock('@/composables/useFormRecovery', async () => {
  const { ref } = await import('vue')
  recovery.lastSaved = ref<string | null>(null)
  recovery.showRecoveryDialog = ref(false)
  return {
    useFormRecovery: () => ({
      showRecoveryDialog: recovery.showRecoveryDialog,
      recoveryData: ref(null),
      recoveryTimestamp: ref('2026-01-01T00:00:00Z'),
      recoveryStale: ref(true),
      lastSaved: recovery.lastSaved,
      restoreRecovery: recovery.restoreRecovery,
      discardRecovery: vi.fn(),
      setBaseline: vi.fn(),
      markSaved: vi.fn(),
      clearRecovery: recovery.clearRecovery
    })
  }
})
vi.mock('@/composables/useHistory', () => ({
  useHistory: () => ({
    canUndo: ref(false),
    canRedo: ref(false),
    recordAction: vi.fn(),
    undo: vi.fn(),
    redo: vi.fn(),
    clearHistory: vi.fn()
  })
}))
/** Internal state read through wrapper.vm. */
interface SchemaCurationVm {
  evidenceData: Record<string, unknown>
  precurationData: Record<string, unknown>
  lockVersion: number
  isDraft: boolean
  curationStatus: string
  formatRelativeTime(timestamp: string | null): string
  handleRestore(): void
  handleCancel(): void | Promise<void>
  handleKeydown(event: KeyboardEvent): void
}
function internals(wrapper: { vm: unknown }): SchemaCurationVm {
  return wrapper.vm as SchemaCurationVm
}

async function mountForm(props: Record<string, unknown> = {}) {
  const wrapper = mount(SchemaDrivenCurationForm, {
    props: { schemaId: 'schema-1', scopeId: 'scope-1', ...props },
    global: { stubs }
  })
  await flushPromises()
  return wrapper
}
describe('SchemaDrivenCurationForm loading and ClinGen flows', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    schemasStore.fetchPinnedVersion.mockResolvedValue(PINNED)
    curationsStore.currentCuration = null
    precurationsStore.precurations = []
    recovery.lastSaved!.value = null
    recovery.showRecoveryDialog!.value = false
    utils.isLegacyFormat.mockReturnValue(false)
    confirmMock.mockResolvedValue(true)
  })

  it('loads an existing curation, its linked precuration and lock version', async () => {
    curationsStore.fetchCurationById.mockResolvedValue({
      evidence_data: { panel: 'x' },
      lock_version: 5,
      status: 'submitted',
      precuration_id: 'p-1'
    })
    curationsStore.currentCuration = { precuration_id: 'p-1' }
    precurationsStore.fetchPrecurationById.mockResolvedValue({
      evidence_data: { disease_name: 'Cancer' }
    })

    const wrapper = await mountForm({ curationId: 'cur-1' })
    const vm = internals(wrapper)

    expect(vm.evidenceData).toEqual({ panel: 'x' })
    expect(vm.lockVersion).toBe(5)
    expect(vm.isDraft).toBe(false)
    expect(vm.curationStatus).toBe('submitted')
    expect(precurationsStore.fetchPrecurationById).toHaveBeenCalledWith('p-1')
    expect(vm.precurationData).toEqual({ disease_name: 'Cancer', id: undefined })
  })

  it('reuses the store curation when its id matches instead of refetching', async () => {
    curationsStore.currentCuration = {
      id: 'cur-1',
      evidence_data: { panel: 'y' },
      lock_version: 2,
      status: 'draft'
    }

    const wrapper = await mountForm({ curationId: 'cur-1' })

    expect(curationsStore.fetchCurationById).not.toHaveBeenCalled()
    expect(internals(wrapper).evidenceData).toEqual({ panel: 'y' })
    expect(internals(wrapper).lockVersion).toBe(2)
  })

  it('migrates legacy evidence formats when loading a curation', async () => {
    curationsStore.fetchCurationById.mockResolvedValue({
      evidence_data: { old: true },
      status: 'draft'
    })
    utils.isLegacyFormat.mockReturnValue(true)
    utils.migrateLegacyFormat.mockReturnValue({ evidence_items: [] })

    const wrapper = await mountForm({ curationId: 'cur-1' })

    expect(logger.info).toHaveBeenCalledWith('Migrating legacy evidence_data format', {
      curationId: 'cur-1'
    })
    expect(internals(wrapper).evidenceData).toEqual({ evidence_items: [] })
  })

  it('starts a re-curation from the active curation: its evidence and precuration, a new draft', async () => {
    const evidence = {
      entity_definition: { mondo_id: 'MONDO:0018965' },
      genetic_evidence: { x: 1 }
    }
    curationsStore.fetchCurationById.mockResolvedValue({
      id: 'active-1',
      precuration_id: 'stale-pre', // rejected since: create would refuse this link
      evidence_data: evidence,
      disease_name: 'Alport syndrome',
      mondo_id: 'MONDO:0018965',
      mode_of_inheritance: 'XL',
      lock_version: 6,
      status: 'active'
    })
    curationsStore.createCuration.mockResolvedValue({ id: 'new-c', lock_version: 0 })
    precurationsStore.fetchCurationPrecuration.mockResolvedValue({
      id: 'pre-2',
      status: 'approved'
    })

    const wrapper = await mountForm({
      geneId: 'g-1',
      workflowPairId: 'wp-1',
      prefillFrom: 'active-1'
    })
    const vm = internals(wrapper)

    expect(curationsStore.fetchCurationById).toHaveBeenCalledWith('active-1')
    // Only the evidence: resolved disease fields are not copied to the top level (#409)
    expect(vm.evidenceData).toEqual(evidence)
    // The new curation is a fresh draft, not the active one
    expect(vm.lockVersion).toBe(0)
    expect(vm.curationStatus).toBe('draft')

    // The draft links the currently approved precuration, never the source's stale one (#409)
    vm.handleKeydown(new KeyboardEvent('keydown', { key: 's', ctrlKey: true }))
    await flushPromises()
    expect(curationsStore.createCuration).toHaveBeenCalledWith({
      gene_id: 'g-1',
      scope_id: 'scope-1',
      workflow_pair_id: 'wp-1',
      precuration_id: 'pre-2',
      evidence_data: evidence
    })
  })

  it('creates a re-curation without a link when no precuration is approved', async () => {
    curationsStore.fetchCurationById.mockResolvedValue({
      id: 'active-1',
      precuration_id: 'stale-pre',
      evidence_data: { a: 1 },
      status: 'active'
    })
    curationsStore.createCuration.mockResolvedValue({ id: 'new-c', lock_version: 0 })
    precurationsStore.fetchCurationPrecuration.mockResolvedValue({
      id: 'stale-pre',
      status: 'rejected'
    })

    const wrapper = await mountForm({
      geneId: 'g-1',
      workflowPairId: 'wp-1',
      prefillFrom: 'active-1'
    })
    internals(wrapper).handleKeydown(new KeyboardEvent('keydown', { key: 's', ctrlKey: true }))
    await flushPromises()

    expect(curationsStore.createCuration).toHaveBeenCalledWith({
      gene_id: 'g-1',
      scope_id: 'scope-1',
      workflow_pair_id: 'wp-1',
      evidence_data: { a: 1 }
    })
  })

  it('ignores the prefill source when editing an existing curation, and reports a failed prefill', async () => {
    curationsStore.currentCuration = { id: 'cur-1', evidence_data: { a: 1 }, status: 'draft' }
    await mountForm({ curationId: 'cur-1', prefillFrom: 'active-1' })
    expect(curationsStore.fetchCurationById).not.toHaveBeenCalled()

    curationsStore.fetchCurationById.mockRejectedValue({ message: 'gone' })
    await mountForm({ prefillFrom: 'active-1' })
    expect(addToast).toHaveBeenCalledWith('Failed to load the active curation', 'error')
  })

  it('reports a failed curation load', async () => {
    curationsStore.fetchCurationById.mockRejectedValue({ message: 'gone' })

    await mountForm({ curationId: 'cur-1' })

    expect(logger.error).toHaveBeenCalledWith('Failed to load curation', { error: 'gone' })
    expect(addToast).toHaveBeenCalledWith('Failed to load curation', 'error')
  })

  it('loads the full approved precuration for a new curation', async () => {
    precurationsStore.fetchCurationPrecuration.mockResolvedValue({ id: 'p-2', status: 'approved' })
    precurationsStore.fetchPrecurationById.mockResolvedValue({
      evidence_data: { disease_name: 'Cancer' }
    })

    const wrapper = await mountForm({ geneId: 'g-1', workflowPairId: 'wp-1' })

    expect(precurationsStore.fetchCurationPrecuration).toHaveBeenCalledWith('g-1', 'scope-1')
    expect(precurationsStore.fetchPrecurationById).toHaveBeenCalledWith('p-2')
    expect(internals(wrapper).precurationData).toEqual({ disease_name: 'Cancer', id: 'p-2' })
    expect(
      wrapper.findComponent({ name: 'LumpingSplittingSection' }).props('precurationData')
    ).toEqual({ disease_name: 'Cancer', id: 'p-2' })
    expect(internals(wrapper).evidenceData).toEqual({})
  })

  it('logs and continues when the precuration lookup fails', async () => {
    precurationsStore.fetchCurationPrecuration.mockRejectedValue({ message: 'down' })

    await mountForm({ geneId: 'g-1' })

    expect(logger.warn).toHaveBeenCalledWith('Failed to load precuration data', { error: 'down' })
  })

  it('passes the recovery timestamp and staleness to the recovery dialog', async () => {
    const wrapper = await mountForm()
    const dialog = wrapper.findComponent({ name: 'FormRecoveryDialog' })
    expect(dialog.props('timestamp')).toBe('2026-01-01T00:00:00Z')
    expect(dialog.props('stale')).toBe(true)
  })

  it('restores through the recovery composable', async () => {
    const wrapper = await mountForm()
    wrapper.findComponent({ name: 'FormRecoveryDialog' }).vm.$emit('restore')
    expect(recovery.restoreRecovery).toHaveBeenCalled()
  })

  it('keeps local recovery unavailable while readonly, including a late restore action', async () => {
    recovery.showRecoveryDialog!.value = true
    const wrapper = await mountForm({ readonly: true })
    expect(wrapper.findComponent({ name: 'FormRecoveryDialog' }).exists()).toBe(false)
    await wrapper.setProps({ readonly: false })
    const dialog = wrapper.findComponent({ name: 'FormRecoveryDialog' })
    expect(dialog.props('modelValue')).toBe(true)
    dialog.vm.$emit('restore')
    expect(recovery.restoreRecovery).toHaveBeenCalledOnce()
    await wrapper.setProps({ readonly: true })
    internals(wrapper).handleRestore()
    expect(recovery.restoreRecovery).toHaveBeenCalledOnce()
    await internals(wrapper).handleCancel()
    expect(wrapper.emitted('cancel')).toHaveLength(1)
    expect(recovery.clearRecovery).not.toHaveBeenCalled()
  })

  it('offers no actions and ignores shortcuts for a read-only generic form', async () => {
    const wrapper = await mountForm({ readonly: true })
    expect(wrapper.findComponent({ name: 'FormActions' }).exists()).toBe(false)
    internals(wrapper).handleKeydown(new KeyboardEvent('keydown', { key: 's', ctrlKey: true }))
    expect(curationsStore.saveDraft).not.toHaveBeenCalled()
    expect(curationsStore.createCuration).not.toHaveBeenCalled()
  })

  it('paints no form until the pinned version has loaded', async () => {
    schemasStore.fetchPinnedVersion.mockReturnValue(new Promise(() => {}))
    const wrapper = await mountForm()
    expect(wrapper.findComponent({ name: 'DynamicForm' }).exists()).toBe(false)
    expect(wrapper.find('.v-skeleton-loader').exists()).toBe(true)
  })

  it('renders an existing curation from the version it is pinned to', async () => {
    curationsStore.fetchCurationById.mockResolvedValue({
      evidence_data: {},
      status: 'draft',
      methodology_version_id: 'v-old'
    })
    const wrapper = await mountForm({ curationId: 'cur-1' })
    expect(schemasStore.fetchPinnedVersion).toHaveBeenCalledWith('v-old', 'schema-1')
    expect(wrapper.findComponent({ name: 'DynamicForm' }).props()).toMatchObject({
      definition: PINNED.snapshot,
      methodologyVersionId: 'v1',
      hideScoring: true
    })
  })

  it("renders a new curation from the schema's latest version", async () => {
    await mountForm()
    expect(schemasStore.fetchPinnedVersion).toHaveBeenCalledWith(null, 'schema-1')
  })

  it('says so when no version can be loaded', async () => {
    schemasStore.fetchPinnedVersion.mockRejectedValueOnce({ message: 'none' })
    const wrapper = await mountForm()
    expect(addToast).toHaveBeenCalledWith('Failed to load curation schema', 'error')
    expect(wrapper.text()).toContain('No schema assigned')
    schemasStore.fetchPinnedVersion.mockReset()
  })

  it('tracks evidence changes from the form', async () => {
    const wrapper = await mountForm({ curationId: 'cur-1' })
    wrapper.findComponent({ name: 'DynamicForm' }).vm.$emit('update:model-value', { b: 2 })
    expect(internals(wrapper).evidenceData).toEqual({ b: 2 })
  })

  it('logs form rendering errors from the error boundary', async () => {
    const wrapper = await mountForm()
    const boundary = wrapper.findComponent({ name: 'ErrorBoundary' })

    boundary.vm.$emit('error', new Error('render broke'))

    expect(logger.error).toHaveBeenCalledWith(
      'Form rendering failed',
      expect.objectContaining({ error: 'render broke' })
    )
    expect(addToast).toHaveBeenCalledWith('Form failed to render. Please try refreshing.', 'error')
  })

  it('clears recovery and data when the schema changes', async () => {
    const wrapper = await mountForm()
    internals(wrapper).evidenceData = { a: 1 }

    await wrapper.setProps({ schemaId: 'schema-2' })

    expect(recovery.clearRecovery).toHaveBeenCalled()
    expect(internals(wrapper).evidenceData).toEqual({})
    expect(logger.info).toHaveBeenCalledWith('Schema changed, cleared form recovery', {
      oldId: 'schema-1',
      newId: 'schema-2'
    })
  })

  it('shows the last server save, not the recovery autosave', async () => {
    recovery.lastSaved!.value = new Date().toISOString()
    const wrapper = await mountForm()
    expect(wrapper.text()).not.toContain('Saved')

    ;(wrapper.vm as unknown as { savedAt: number }).savedAt = Date.now() - 10 * 60_000
    await flushPromises()
    expect(wrapper.text()).toContain('Saved 10m ago')
    expect(internals(wrapper).formatRelativeTime(null)).toBe('')
  })

  it('confirms before cancelling with entered data', async () => {
    const wrapper = await mountForm()
    const vm = internals(wrapper)
    vm.evidenceData = { a: 1 }
    confirmMock.mockResolvedValueOnce(false)
    await vm.handleCancel()
    expect(wrapper.emitted('cancel')).toBeUndefined()
    await vm.handleCancel()
    expect(wrapper.emitted('cancel')).toHaveLength(1)
  })

  it('submits on Ctrl+Enter only when submission is allowed, after confirming', async () => {
    curationsStore.createCuration.mockResolvedValue({ id: 'new-c' })
    const wrapper = await mountForm({ readonly: true, geneId: 'g-1', workflowPairId: 'wp-1' })
    const vm = internals(wrapper)
    vm.evidenceData = { a: 1 }

    vm.handleKeydown(new KeyboardEvent('keydown', { key: 'Enter', ctrlKey: true }))
    await flushPromises()
    expect(curationsStore.createCuration).not.toHaveBeenCalled()

    await wrapper.setProps({ readonly: false })
    confirmMock.mockResolvedValueOnce(false)
    vm.handleKeydown(new KeyboardEvent('keydown', { key: 'Enter', ctrlKey: true }))
    await flushPromises()
    expect(curationsStore.createCuration).not.toHaveBeenCalled()

    vm.handleKeydown(new KeyboardEvent('keydown', { key: 'Enter', ctrlKey: true }))
    await flushPromises()
    expect(curationsStore.createCuration).toHaveBeenCalledTimes(1)
  })

  it('Escape cancels only when it does not come from a field, cell or menu', async () => {
    const wrapper = await mountForm({ geneId: 'g-1', workflowPairId: 'wp-1' })
    const vm = internals(wrapper)
    // Dispatch Escape from the innermost element of `html`, bubbling up to the form's handler
    const press = (html: string) => {
      const form = document.createElement('form')
      form.innerHTML = html
      form.addEventListener('keydown', e => vm.handleKeydown(e))
      const from = form.querySelector('input, button')!
      from.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    }

    // Open select menu, select just picked from (menu closed), evidence-table cell being edited
    press('<input role="combobox" aria-expanded="true">')
    press('<input role="combobox" aria-expanded="false">')
    press('<table class="evidence-table-field"><tr><td><input></td></tr></table>')
    await flushPromises()
    expect(wrapper.emitted('cancel')).toBeUndefined()

    press('<button>Somewhere</button>')
    await flushPromises()
    expect(wrapper.emitted('cancel')).toHaveLength(1)
  })

  describe('workspace frame hook', () => {
    async function mountFramed() {
      const frame = createWorkspaceFrame()
      const wrapper = mount(SchemaDrivenCurationForm, {
        props: { schemaId: 'schema-1', scopeId: 'scope-1', curationId: 'cur-1' },
        global: { stubs, provide: { [WORKSPACE_FRAME as symbol]: frame } }
      })
      await flushPromises()
      frame.markClean()
      return { wrapper, frame }
    }

    it('reports edits as unsaved and saves the draft through the frame', async () => {
      curationsStore.fetchCurationById.mockResolvedValue({ evidence_data: {}, lock_version: 2 })
      curationsStore.saveDraft.mockResolvedValue({ lock_version: 3 })
      const { wrapper, frame } = await mountFramed()
      expect(frame.state.value).toBe('saved')

      wrapper.findComponent({ name: 'DynamicForm' }).vm.$emit('update:model-value', { a: 1 })
      await flushPromises()
      expect(frame.state.value).toBe('unsaved')

      expect(await frame.save()).toBe(true)
      expect(curationsStore.saveDraft).toHaveBeenCalledWith('cur-1', {
        evidence_data: { a: 1 },
        lock_version: 2
      })
      expect(frame.state.value).toBe('saved')
    })

    it('reports a failed save through the frame', async () => {
      curationsStore.fetchCurationById.mockResolvedValue({ evidence_data: {}, lock_version: 2 })
      curationsStore.saveDraft.mockResolvedValue(undefined)
      const { wrapper, frame } = await mountFramed()
      wrapper.findComponent({ name: 'DynamicForm' }).vm.$emit('update:model-value', { b: 2 })
      await flushPromises()
      expect(await frame.save()).toBe(false)
      expect(frame.state.value).toBe('failed')
    })

    it('shows the live backend score from validate-evidence', async () => {
      curationsStore.fetchCurationById.mockResolvedValue({
        evidence_data: { contradictory_evidence: [{ description: 'x', impact: 'disputed' }] },
        lock_version: 2
      })
      const { wrapper, frame } = await mountFramed()
      const form = wrapper.findComponent({ name: 'DynamicForm' })
      form.vm.$emit('validation-change', { is_valid: true, score_calculations: { total_score: 1 } })
      await flushPromises()
      expect(frame.score.value).toBeNull() // no verdict yet: no panel

      form.vm.$emit('validation-change', {
        is_valid: true,
        score_calculations: {
          total_score: 8,
          genetic_evidence_total: 6,
          experimental_evidence_total: 2,
          verdict: 'Moderate',
          trace: {
            sections: [{ key: 'genetic_evidence', categories: [{ key: 'segregation', score: 1 }] }]
          }
        }
      })
      await flushPromises()
      expect(frame.score.value).toMatchObject({
        total: 8,
        classification: 'Moderate',
        hasContradictory: true,
        trace: {
          sections: [{ key: 'genetic_evidence', categories: [{ key: 'segregation', score: 1 }] }]
        }
      })
      expect(wrapper.findComponent({ name: 'ScoreSummary' }).props('scores').total).toBe(8)
      form.vm.$emit('validation-change', undefined)
      await flushPromises()
      expect(frame.score.value).toBeNull()
      form.vm.$emit('validation-pending', true)
      expect(frame.scorePending.value).toBe(true)
      form.vm.$emit('validation-pending', false)
      expect(frame.scorePending.value).toBe(false)
      expect(curationsStore.calculateScore).not.toHaveBeenCalled()
    })

    it('requires case-level or segregation evidence for a ClinGen definition', async () => {
      schemasStore.fetchPinnedVersion.mockResolvedValue({
        id: 'v1',
        snapshot: { field_definitions: { genetic_evidence: { type: 'object' } } }
      })
      curationsStore.fetchCurationById.mockResolvedValue({
        evidence_data: { evidence_summary: 'x', genetic_evidence: { case_level: {} } },
        lock_version: 2
      })
      const { wrapper, frame } = await mountFramed()
      expect(frame.canSubmit.value).toBe(false)
      expect(frame.submit()).toBe(false)

      wrapper.findComponent({ name: 'DynamicForm' }).vm.$emit('update:model-value', {
        genetic_evidence: { segregation: [{ pmid: '1', points: 1 }] }
      })
      await flushPromises()
      expect(frame.canSubmit.value).toBe(true)
    })

    it('never submits while a save is in flight', async () => {
      curationsStore.fetchCurationById.mockResolvedValue({
        evidence_data: { a: 1 },
        lock_version: 2
      })
      curationsStore.saveDraft.mockReturnValue(new Promise(() => {}))
      const { wrapper, frame } = await mountFramed()
      void frame.save()
      await flushPromises()
      internals(wrapper).handleKeydown(
        new KeyboardEvent('keydown', { key: 'Enter', ctrlKey: true })
      )
      await flushPromises()
      expect(confirmMock).not.toHaveBeenCalled()
      expect(curationsStore.submitCuration).not.toHaveBeenCalled()
    })

    it('submits through the frame after confirming, saving the evidence first', async () => {
      curationsStore.fetchCurationById.mockResolvedValue({
        evidence_data: { a: 1 },
        lock_version: 2
      })
      curationsStore.updateCuration.mockResolvedValue({ lock_version: 3 })
      precurationsStore.fetchPrecurationById.mockResolvedValue({
        id: 'p-1',
        evidence_data: { disease_name: 'Alport', mode_of_inheritance: 'XL' }
      })
      curationsStore.currentCuration = { precuration_id: 'p-1' }
      curationsStore.fetchCurationById.mockResolvedValue({
        evidence_data: { a: 1 },
        lock_version: 2,
        precuration_id: 'p-1'
      })
      const { wrapper, frame } = await mountFramed()
      expect(frame.meta.value).toEqual({ disease: 'Alport', moi: 'XL' })
      expect(wrapper.findComponent({ name: 'FormActions' }).exists()).toBe(false)
      expect(frame.canSubmit.value).toBe(true)

      expect(frame.submit()).toBe(true)
      await flushPromises()
      expect(confirmMock).toHaveBeenCalled()
      expect(curationsStore.updateCuration).toHaveBeenCalledWith('cur-1', {
        evidence_data: { a: 1 },
        lock_version: 2
      })
      expect(curationsStore.submitCuration).toHaveBeenCalledWith('cur-1', { lock_version: 3 })
    })

    it('works without a frame', async () => {
      const wrapper = await mountForm()
      expect(wrapper.exists()).toBe(true)
    })
  })
})
