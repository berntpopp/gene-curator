import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ref } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import SchemaDrivenCurationForm from '../SchemaDrivenCurationForm.vue'

const logger = vi.hoisted(() => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }))
const addToast = vi.hoisted(() => vi.fn())
const push = vi.hoisted(() => vi.fn())
const replace = vi.hoisted(() => vi.fn())
const recovery = vi.hoisted(() => ({
  clearRecovery: vi.fn(),
  lastSaved: null as null | { value: string | null }
}))
const schemaState = vi.hoisted(() => ({ useDynamicForm: true as boolean | undefined }))
const curationsStore = vi.hoisted(() => ({
  currentCuration: null as unknown,
  fetchCurationById: vi.fn(),
  saveDraft: vi.fn(),
  createCuration: vi.fn(),
  submitCuration: vi.fn(),
  updateCuration: vi.fn()
}))
const precurationsStore = vi.hoisted(() => ({
  precurations: [] as unknown[],
  fetchPrecurations: vi.fn(),
  fetchPrecurationById: vi.fn()
}))
const schemasStore = vi.hoisted(() => ({
  getWorkflowPairById: vi.fn(),
  fetchSchemaById: vi.fn()
}))
const utils = vi.hoisted(() => ({
  isLegacyFormat: vi.fn(),
  migrateLegacyFormat: vi.fn(),
  applyDataMapping: vi.fn()
}))

vi.mock('@/composables/useLogger', () => ({ useLogger: () => logger }))
vi.mock('vue-router', () => ({ useRouter: () => ({ push, replace }) }))
vi.mock('@/stores/schemas', () => ({
  useSchemasStore: () => ({
    getSchemaById: (id: string) => ({
      id,
      name: 'Panel schema',
      use_dynamic_form: schemaState.useDynamicForm
    }),
    getWorkflowPairById: schemasStore.getWorkflowPairById,
    fetchSchemaById: schemasStore.fetchSchemaById
  })
}))
vi.mock('@/stores/curations', () => ({ useCurationsStore: () => curationsStore }))
vi.mock('@/stores/precurations', () => ({ usePrecurationsStore: () => precurationsStore }))
vi.mock('@/stores/validation', () => ({
  useValidationStore: () => ({ generateJsonSchema: vi.fn() })
}))
vi.mock('@/stores/notifications', () => ({ useNotificationsStore: () => ({ addToast }) }))
vi.mock('@/utils/evidenceDataMigration', () => ({
  isLegacyFormat: utils.isLegacyFormat,
  migrateLegacyFormat: utils.migrateLegacyFormat
}))
vi.mock('@/utils/dataMapping', () => ({ applyDataMapping: utils.applyDataMapping }))
vi.mock('@/composables/useFormRecovery', async () => {
  const { ref } = await import('vue')
  recovery.lastSaved = ref<string | null>(null)
  return {
    useFormRecovery: () => ({
      showRecoveryDialog: ref(false),
      recoveryData: ref(null),
      lastSaved: recovery.lastSaved,
      restoreRecovery: vi.fn(),
      discardRecovery: vi.fn(),
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
  handleCancel(): void
  handleKeydown(event: KeyboardEvent): void
}

function internals(wrapper: { vm: unknown }): SchemaCurationVm {
  return wrapper.vm as SchemaCurationVm
}

const stubs = {
  ErrorBoundary: { name: 'ErrorBoundary', template: '<div><slot /></div>' },
  ClinGenCurationForm: true,
  DynamicForm: true,
  FormActions: true,
  ScorePreview: true,
  FormRecoveryDialog: true
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
    schemaState.useDynamicForm = true
    curationsStore.currentCuration = null
    precurationsStore.precurations = []
    recovery.lastSaved!.value = null
    utils.isLegacyFormat.mockReturnValue(false)
    utils.applyDataMapping.mockReturnValue({})
    window.confirm = vi.fn(() => true)
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
    expect(vm.precurationData).toEqual({ disease_name: 'Cancer' })
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

  it('reports a failed curation load', async () => {
    curationsStore.fetchCurationById.mockRejectedValue({ message: 'gone' })

    await mountForm({ curationId: 'cur-1' })

    expect(logger.error).toHaveBeenCalledWith('Failed to load curation', { error: 'gone' })
    expect(addToast).toHaveBeenCalledWith('Failed to load curation', 'error')
  })

  it('prefills a new curation from the approved precuration with the workflow mapping', async () => {
    precurationsStore.precurations = [
      { id: 'p-1', status: 'draft', evidence_data: {} },
      { id: 'p-2', status: 'approved', evidence_data: { disease_name: 'Cancer' } }
    ]
    schemasStore.getWorkflowPairById.mockReturnValue({ data_mapping: { x: 'y' } })
    utils.applyDataMapping.mockReturnValue({ mapped: 1 })

    const wrapper = await mountForm({ geneId: 'g-1', workflowPairId: 'wp-1' })
    const vm = internals(wrapper)

    expect(precurationsStore.fetchPrecurations).toHaveBeenCalledWith({
      gene_id: 'g-1',
      scope_id: 'scope-1'
    })
    expect(vm.precurationData).toEqual({ disease_name: 'Cancer' })
    expect(utils.applyDataMapping).toHaveBeenCalledWith({ disease_name: 'Cancer' }, { x: 'y' })
    expect(vm.evidenceData).toEqual({ mapped: 1 })
  })

  it('fetches the full precuration when the summary has no evidence data', async () => {
    precurationsStore.precurations = [{ id: 'p-9', status: 'approved' }]
    precurationsStore.fetchPrecurationById.mockResolvedValue({ evidence_data: { full: true } })

    const wrapper = await mountForm({ geneId: 'g-1' })

    expect(precurationsStore.fetchPrecurationById).toHaveBeenCalledWith('p-9')
    expect(internals(wrapper).precurationData).toEqual({ full: true })
  })

  it('logs and continues when the precuration lookup fails', async () => {
    precurationsStore.fetchPrecurations.mockRejectedValue({ message: 'down' })

    await mountForm({ geneId: 'g-1' })

    expect(logger.warn).toHaveBeenCalledWith('Failed to load precuration data', { error: 'down' })
  })

  it('renders the ClinGen form for schemas that opt out of the dynamic form', async () => {
    schemaState.useDynamicForm = false
    curationsStore.fetchCurationById.mockResolvedValue({ evidence_data: {}, status: 'draft' })

    const wrapper = await mountForm({ curationId: 'cur-1' })
    const clingen = wrapper.findComponent({ name: 'ClinGenCurationForm' })
    expect(clingen.exists()).toBe(true)

    clingen.vm.$emit('submit', { evidence_items: [] })
    await flushPromises()
    expect(curationsStore.updateCuration).toHaveBeenCalledWith('cur-1', {
      evidence_data: { evidence_items: [] },
      lock_version: 0
    })
    expect(wrapper.emitted('submit')).toHaveLength(1)
  })

  it('saves a ClinGen draft from the ClinGen form', async () => {
    schemaState.useDynamicForm = false
    curationsStore.saveDraft.mockResolvedValue({ lock_version: 2 })
    const wrapper = await mountForm({ curationId: 'cur-1' })

    wrapper.findComponent({ name: 'ClinGenCurationForm' }).vm.$emit('save-draft', { a: 1 })
    await flushPromises()

    expect(curationsStore.saveDraft).toHaveBeenCalledWith('cur-1', {
      evidence_data: { a: 1 },
      lock_version: 0
    })
    expect(wrapper.emitted('saved')).toHaveLength(1)
  })

  it('tracks ClinGen evidence changes and cancels from the ClinGen form', async () => {
    schemaState.useDynamicForm = false
    const wrapper = await mountForm({ curationId: 'cur-1' })
    const clingen = wrapper.findComponent({ name: 'ClinGenCurationForm' })

    clingen.vm.$emit('update:modelValue', { b: 2 })
    expect(internals(wrapper).evidenceData).toEqual({ b: 2 })

    clingen.vm.$emit('cancel')
    expect(wrapper.emitted('cancel')).toHaveLength(1)
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

  it('shows when the form was last saved', async () => {
    recovery.lastSaved!.value = new Date(Date.now() - 10 * 60_000).toISOString()
    const wrapper = await mountForm()

    expect(wrapper.text()).toContain('Saved 10m ago')
    expect(internals(wrapper).formatRelativeTime(null)).toBe('')
  })

  it('confirms before cancelling with entered data', async () => {
    const wrapper = await mountForm()
    const vm = internals(wrapper)
    vm.evidenceData = { a: 1 }

    vi.mocked(window.confirm).mockReturnValueOnce(false)
    vm.handleCancel()
    expect(wrapper.emitted('cancel')).toBeUndefined()

    vm.handleCancel()
    expect(wrapper.emitted('cancel')).toHaveLength(1)
  })

  it('submits on Ctrl+Enter only when submission is allowed', async () => {
    curationsStore.createCuration.mockResolvedValue({ id: 'new-c' })
    const wrapper = await mountForm({ readonly: true })
    const vm = internals(wrapper)

    vm.handleKeydown(new KeyboardEvent('keydown', { key: 'Enter', ctrlKey: true }))
    await flushPromises()
    expect(curationsStore.createCuration).not.toHaveBeenCalled()

    await wrapper.setProps({ readonly: false })
    vm.handleKeydown(new KeyboardEvent('keydown', { key: 'Enter', ctrlKey: true }))
    await flushPromises()
    expect(curationsStore.createCuration).toHaveBeenCalledTimes(1)
  })
})
