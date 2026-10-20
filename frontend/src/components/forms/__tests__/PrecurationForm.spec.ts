import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import PrecurationForm from '../PrecurationForm.vue'
import { precurationsAPI } from '@/api'

const logger = vi.hoisted(() => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }))
const push = vi.hoisted(() => vi.fn())
const scopesState = vi.hoisted(() => ({
  scopes: [{ id: 'scope-1', display_name: 'Cancer' }] as unknown[]
}))
const locking = vi.hoisted(() => ({
  saveWithLockCheck: vi.fn(),
  resolveConflict: vi.fn(() => ({ theirVersion: 9 }))
}))
const history = vi.hoisted(() => ({
  canUndo: { value: false },
  canRedo: { value: false },
  undo: vi.fn(),
  redo: vi.fn(),
  recordAction: vi.fn(),
  clearHistory: vi.fn()
}))
const recovery = vi.hoisted(() => ({
  clearRecovery: vi.fn(),
  // Set by the useFormRecovery mock below; the template needs a real ref.
  lastSaved: null as null | { value: string | null }
}))

vi.mock('@/composables/useLogger', () => ({ useLogger: () => logger }))
vi.mock('vue-router', () => ({ useRouter: () => ({ push }) }))
vi.mock('@/stores/scopes', () => ({
  useScopesStore: () => ({
    get scopes() {
      return scopesState.scopes
    },
    fetchScopes: vi.fn()
  })
}))
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
    canUndo: history.canUndo,
    canRedo: history.canRedo,
    recordAction: history.recordAction,
    undo: history.undo,
    redo: history.redo,
    clearHistory: history.clearHistory
  })
}))
vi.mock('@/composables/useOptimisticLocking', async () => {
  const { ref } = await import('vue')
  return {
    useOptimisticLocking: () => ({
      conflictDetected: ref(false),
      conflictData: ref(null),
      saveWithLockCheck: locking.saveWithLockCheck,
      resolveConflict: locking.resolveConflict
    })
  }
})
vi.mock('@/composables/useSessionTimeout', async () => {
  const { ref } = await import('vue')
  return {
    useSessionTimeout: () => ({
      showWarning: ref(false),
      timeRemaining: ref(0),
      extendSession: vi.fn()
    })
  }
})
vi.mock('@/api', () => ({
  precurationsAPI: {
    getPrecuration: vi.fn(),
    createPrecuration: vi.fn(),
    updatePrecuration: vi.fn(),
    saveDraft: vi.fn()
  }
}))

const getPrecuration = vi.mocked(precurationsAPI.getPrecuration)
const createPrecuration = vi.mocked(precurationsAPI.createPrecuration)
const saveDraft = vi.mocked(precurationsAPI.saveDraft)

/** Internal state read through wrapper.vm. */
interface PrecurationFormVm {
  formData: {
    gene_symbol: string
    scope_id: string
    hpo_terms: string[]
    rationale: string
    pmids: string[]
    curator_notes: string
    lock_version: number
  }
  isFormValid: boolean
  isDraft: boolean
  handleKeydown(event: KeyboardEvent): void
  handleCancel(): void
  handleSubmit(): Promise<void>
  handleSaveDraft(): Promise<void>
  formatTimeAgo(timestamp: string | number): string
}

function internals(wrapper: { vm: unknown }): PrecurationFormVm {
  return wrapper.vm as PrecurationFormVm
}

const stubs = {
  ErrorBoundary: { template: '<div><slot /></div>' },
  ValidatedInput: true,
  PMIDInput: true,
  HPOInput: true,
  FormRecoveryDialog: true,
  ConflictResolutionDialog: true,
  SessionTimeoutWarning: true
}

// Window key listeners outlive a test unless the component is unmounted.
const mounted: Array<{ unmount(): void }> = []

async function mountForm(props: Record<string, unknown> = {}) {
  const wrapper = mount(PrecurationForm, { props, global: { stubs } })
  mounted.push(wrapper)
  await flushPromises()
  return wrapper
}

function fillValid(vm: PrecurationFormVm) {
  vm.formData.gene_symbol = 'BRCA1'
  vm.formData.scope_id = 'scope-1'
  vm.formData.hpo_terms = ['HP:0000001']
  vm.formData.rationale = 'Because'
  vm.formData.pmids = ['123']
}

describe('PrecurationForm', () => {
  afterEach(() => {
    mounted.splice(0).forEach(w => w.unmount())
  })

  beforeEach(() => {
    vi.clearAllMocks()
    scopesState.scopes = [{ id: 'scope-1', display_name: 'Cancer' }]
    recovery.lastSaved!.value = null
    history.canUndo.value = false
    history.canRedo.value = false
    // happy-dom does not implement confirm()
    window.confirm = vi.fn(() => true)
  })

  it('pre-fills the scope from props and is invalid until required fields are set', async () => {
    const wrapper = await mountForm({ scopeId: 'scope-1' })
    const vm = internals(wrapper)

    expect(vm.formData.scope_id).toBe('scope-1')
    expect(vm.isFormValid).toBe(false)

    fillValid(vm)
    await flushPromises()
    expect(vm.isFormValid).toBe(true)
  })

  it('loads the existing precuration when editing', async () => {
    getPrecuration.mockResolvedValue({
      gene_symbol: 'TP53',
      scope_id: 'scope-1',
      lock_version: 3,
      is_draft: false,
      evidence_data: { hpo_terms: ['HP:1'], rationale: 'r', pmids: ['5'], curator_notes: '' }
    } as never)

    const wrapper = await mountForm({ precurationId: 'pre-1' })
    const vm = internals(wrapper)

    expect(getPrecuration).toHaveBeenCalledWith('pre-1')
    expect(vm.formData.gene_symbol).toBe('TP53')
    expect(vm.isDraft).toBe(false)
    expect(wrapper.text()).toContain('Submitted')
  })

  it('shows an auto-save indicator with the elapsed time', async () => {
    recovery.lastSaved!.value = new Date(Date.now() - 120_000).toISOString()
    const wrapper = await mountForm()

    expect(wrapper.text()).toMatch(/Auto-saved\s+2 minutes ago/)
    expect(internals(wrapper).formatTimeAgo(Date.now() - 30_000)).toBe('30 seconds ago')
    expect(internals(wrapper).formatTimeAgo(Date.now() - 3 * 3600_000)).toBe('3 hours ago')
  })

  it('submits a new precuration and navigates to the list', async () => {
    createPrecuration.mockResolvedValue({ id: 'new-1', lock_version: 0 } as never)
    const wrapper = await mountForm()
    const vm = internals(wrapper)
    fillValid(vm)
    await flushPromises()

    await vm.handleSubmit()

    expect(createPrecuration).toHaveBeenCalledWith(expect.objectContaining({ is_draft: false }))
    expect(wrapper.emitted('success')?.[0]).toEqual([{ id: 'new-1', lock_version: 0 }])
    expect(push).toHaveBeenCalledWith({ name: 'Precurations' })
  })

  it('saves a draft and keeps the returned lock version', async () => {
    createPrecuration.mockResolvedValue({ id: 'new-1', lock_version: 4 } as never)
    const wrapper = await mountForm()
    const vm = internals(wrapper)

    await vm.handleSaveDraft()

    expect(createPrecuration).toHaveBeenCalledWith(expect.objectContaining({ is_draft: true }))
    expect(vm.formData.lock_version).toBe(4)
  })

  it('saves drafts through the draft endpoint when editing', async () => {
    getPrecuration.mockResolvedValue({ id: 'pre-1', gene_symbol: 'X' } as never)
    saveDraft.mockResolvedValue({ id: 'pre-1', lock_version: 6 } as never)
    const wrapper = await mountForm({ precurationId: 'pre-1' })

    await internals(wrapper).handleSaveDraft()

    expect(saveDraft).toHaveBeenCalledWith('pre-1', expect.objectContaining({ is_draft: true }))
  })

  it('discards changes only after confirmation', async () => {
    const wrapper = await mountForm()
    const vm = internals(wrapper)

    vi.mocked(window.confirm).mockReturnValueOnce(false)
    vm.handleCancel()
    expect(push).not.toHaveBeenCalled()

    vm.handleCancel()
    expect(recovery.clearRecovery).toHaveBeenCalled()
    expect(history.clearHistory).toHaveBeenCalled()
    expect(wrapper.emitted('cancel')).toHaveLength(1)
    expect(push).toHaveBeenCalledWith({ name: 'Precurations' })
  })

  it('applies undo and redo from history', async () => {
    const wrapper = await mountForm()
    const vm = internals(wrapper)
    const previous = { gene_symbol: 'OLD' }
    history.undo.mockReturnValueOnce(previous)
    history.canUndo.value = true

    vm.handleKeydown(new KeyboardEvent('keydown', { key: 'z', ctrlKey: true }))
    expect(history.undo).toHaveBeenCalled()
    expect(vm.formData.gene_symbol).toBe('OLD')

    history.redo.mockReturnValueOnce(null)
    history.canRedo.value = true
    vm.handleKeydown(new KeyboardEvent('keydown', { key: 'z', ctrlKey: true, shiftKey: true }))
    expect(history.redo).toHaveBeenCalled()
  })

  it('does not undo when there is nothing to undo', async () => {
    const wrapper = await mountForm()

    internals(wrapper).handleKeydown(new KeyboardEvent('keydown', { key: 'z', ctrlKey: true }))

    expect(history.undo).not.toHaveBeenCalled()
  })

  it('maps Ctrl+S and Escape from the window to draft save and cancel', async () => {
    const wrapper = await mountForm()
    fillValid(internals(wrapper))
    await flushPromises()

    window.dispatchEvent(new KeyboardEvent('keydown', { key: 's', ctrlKey: true }))
    await flushPromises()
    expect(createPrecuration).toHaveBeenCalledTimes(1)
    expect(createPrecuration).toHaveBeenCalledWith(expect.objectContaining({ is_draft: true }))

    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    expect(window.confirm).toHaveBeenCalledWith('Discard unsaved changes?')
  })

  it('handles conflict resolution by overwriting with the server version', async () => {
    const wrapper = await mountForm({ precurationId: 'pre-1' })
    getPrecuration.mockResolvedValue({ id: 'pre-1' } as never)
    locking.saveWithLockCheck.mockResolvedValue({ id: 'pre-1' })
    const vm = wrapper.vm as unknown as { handleConflictResolution(r: string): Promise<void> }

    await vm.handleConflictResolution('overwrite-theirs')

    expect(locking.resolveConflict).toHaveBeenCalledWith('overwrite-theirs')
  })
})
