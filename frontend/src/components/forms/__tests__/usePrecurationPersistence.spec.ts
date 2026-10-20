import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ref, type Ref } from 'vue'
import { precurationsAPI } from '@/api'
import {
  usePrecurationPersistence,
  type PrecurationFormData,
  type PrecurationPayload,
  type PrecurationRecord
} from '../usePrecurationPersistence'

const logger = vi.hoisted(() => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }))
const push = vi.hoisted(() => vi.fn())

vi.mock('@/composables/useLogger', () => ({ useLogger: () => logger }))
vi.mock('vue-router', () => ({ useRouter: () => ({ push }) }))
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
const updatePrecuration = vi.mocked(precurationsAPI.updatePrecuration)
const saveDraft = vi.mocked(precurationsAPI.saveDraft)

function emptyForm(): PrecurationFormData {
  return {
    gene_symbol: 'BRCA1',
    scope_id: 'scope-1',
    hpo_terms: ['HP:0000001'],
    rationale: 'Because',
    pmids: ['123'],
    curator_notes: 'note',
    lock_version: 2
  }
}

interface Harness {
  formData: Ref<PrecurationFormData>
  isDraft: Ref<boolean>
  precurationId: { value: string | null }
  clearRecovery: () => void
  clearHistory: () => void
  onSuccess: (result: PrecurationRecord) => void
  saveWithLockCheck: (
    apiCall: (data: PrecurationPayload) => Promise<unknown>,
    payload: PrecurationPayload,
    currentVersion: number
  ) => Promise<unknown>
  valid: { value: boolean }
}

function setup(precurationId: string | null = null): {
  api: ReturnType<typeof usePrecurationPersistence>
  h: Harness
} {
  const h: Harness = {
    formData: ref(emptyForm()),
    isDraft: ref(true),
    precurationId: { value: precurationId },
    clearRecovery: vi.fn(),
    clearHistory: vi.fn(),
    onSuccess: vi.fn(),
    saveWithLockCheck: vi.fn(
      async (apiCall: (d: PrecurationPayload) => Promise<unknown>, payload: PrecurationPayload) =>
        apiCall(payload)
    ) as Harness['saveWithLockCheck'],
    valid: { value: true }
  }
  const api = usePrecurationPersistence({
    precurationId: () => h.precurationId.value,
    isFormValid: () => h.valid.value,
    formData: h.formData,
    isDraft: h.isDraft,
    saveWithLockCheck: h.saveWithLockCheck,
    clearRecovery: h.clearRecovery,
    clearHistory: h.clearHistory,
    onSuccess: h.onSuccess
  })
  return { api, h }
}

describe('usePrecurationPersistence', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  describe('loadPrecuration', () => {
    it('fills the form and draft flag from the API response', async () => {
      getPrecuration.mockResolvedValue({
        gene_symbol: 'TP53',
        scope_id: 'scope-2',
        lock_version: 5,
        is_draft: true,
        evidence_data: { hpo_terms: ['HP:1'], rationale: 'r', pmids: ['9'], curator_notes: 'n' }
      } as never)
      const { api, h } = setup('pre-1')

      await api.loadPrecuration()

      expect(getPrecuration).toHaveBeenCalledWith('pre-1')
      expect(h.formData.value).toEqual({
        gene_symbol: 'TP53',
        scope_id: 'scope-2',
        hpo_terms: ['HP:1'],
        rationale: 'r',
        pmids: ['9'],
        curator_notes: 'n',
        lock_version: 5
      })
      expect(h.isDraft.value).toBe(true)
      expect(logger.info).toHaveBeenCalledWith('Precuration loaded for editing', { id: 'pre-1' })
    })

    it('defaults missing fields and treats a missing is_draft as submitted', async () => {
      getPrecuration.mockResolvedValue({ id: 'pre-1' } as never)
      const { api, h } = setup('pre-1')

      await api.loadPrecuration()

      expect(h.formData.value).toEqual({
        gene_symbol: '',
        scope_id: '',
        hpo_terms: [],
        rationale: '',
        pmids: [],
        curator_notes: '',
        lock_version: 0
      })
      expect(h.isDraft.value).toBe(false)
    })

    it('logs and keeps the form when loading fails', async () => {
      getPrecuration.mockRejectedValue(new Error('404'))
      const { api, h } = setup('pre-1')
      const before = h.formData.value

      await api.loadPrecuration()

      expect(logger.error).toHaveBeenCalledWith('Failed to load precuration', { error: '404' })
      expect(h.formData.value).toBe(before)
    })
  })

  describe('handleSubmit', () => {
    it('warns and does nothing when the form is invalid', async () => {
      const { api, h } = setup()
      h.valid.value = false

      await api.handleSubmit()

      expect(logger.warn).toHaveBeenCalledWith('Form validation failed')
      expect(createPrecuration).not.toHaveBeenCalled()
    })

    it('creates a new precuration, clears state, emits success and navigates', async () => {
      createPrecuration.mockResolvedValue({ id: 'new-1', lock_version: 0 } as never)
      const { api, h } = setup()

      await api.handleSubmit()

      expect(createPrecuration).toHaveBeenCalledWith({
        gene_symbol: 'BRCA1',
        scope_id: 'scope-1',
        evidence_data: {
          hpo_terms: ['HP:0000001'],
          rationale: 'Because',
          pmids: ['123'],
          curator_notes: 'note'
        },
        is_draft: false,
        lock_version: 2
      })
      expect(h.clearRecovery).toHaveBeenCalled()
      expect(h.clearHistory).toHaveBeenCalled()
      expect(h.onSuccess).toHaveBeenCalledWith({ id: 'new-1', lock_version: 0 })
      expect(push).toHaveBeenCalledWith({ name: 'Precurations' })
      expect(api.submitting.value).toBe(false)
    })

    it('updates an existing precuration through the optimistic lock check', async () => {
      updatePrecuration.mockResolvedValue({ id: 'pre-1' } as never)
      const { api, h } = setup('pre-1')

      await api.handleSubmit()

      expect(h.saveWithLockCheck).toHaveBeenCalledWith(
        expect.any(Function),
        expect.objectContaining({ is_draft: false }),
        2
      )
      expect(updatePrecuration).toHaveBeenCalledWith(
        'pre-1',
        expect.objectContaining({ is_draft: false })
      )
      expect(h.onSuccess).toHaveBeenCalledWith({ id: 'pre-1' })
    })

    it('logs non-conflict errors and leaves the form in place', async () => {
      createPrecuration.mockRejectedValue({ message: 'bad', response: { status: 500 } })
      const { api, h } = setup()

      await api.handleSubmit()

      expect(logger.error).toHaveBeenCalledWith('Failed to submit precuration', { error: 'bad' })
      expect(h.clearRecovery).not.toHaveBeenCalled()
      expect(push).not.toHaveBeenCalled()
      expect(api.submitting.value).toBe(false)
    })

    it('stays silent on a 409 conflict, which the locking composable handles', async () => {
      createPrecuration.mockRejectedValue({ message: 'conflict', response: { status: 409 } })
      const { api } = setup()

      await api.handleSubmit()

      expect(logger.error).not.toHaveBeenCalled()
    })
  })

  describe('handleSaveDraft', () => {
    it('saves a draft for an existing precuration and updates the lock version', async () => {
      saveDraft.mockResolvedValue({ id: 'pre-1', lock_version: 7 } as never)
      const { api, h } = setup('pre-1')

      await api.handleSaveDraft()

      expect(saveDraft).toHaveBeenCalledWith(
        'pre-1',
        expect.objectContaining({ is_draft: true, lock_version: 2 })
      )
      expect(h.formData.value.lock_version).toBe(7)
      expect(logger.info).toHaveBeenCalledWith('Draft saved', { id: 'pre-1' })
      expect(api.savingDraft.value).toBe(false)
    })

    it('creates a precuration when saving a draft for a new form', async () => {
      createPrecuration.mockResolvedValue({ id: 'new-2' } as PrecurationRecord as never)
      const { api, h } = setup()

      await api.handleSaveDraft()

      expect(createPrecuration).toHaveBeenCalledWith(expect.objectContaining({ is_draft: true }))
      // The response had no lock_version; the form keeps the value it received (undefined), as before.
      expect(h.formData.value.lock_version).toBeUndefined()
    })

    it('logs failures and clears the saving flag', async () => {
      saveDraft.mockRejectedValue({ message: 'offline' })
      const { api } = setup('pre-1')

      await api.handleSaveDraft()

      expect(logger.error).toHaveBeenCalledWith('Failed to save draft', { error: 'offline' })
      expect(api.savingDraft.value).toBe(false)
    })
  })

  describe('handleConflictResolution', () => {
    it('reloads the server version when the user discards their changes', async () => {
      getPrecuration.mockResolvedValue({ gene_symbol: 'FRESH' } as never)
      const { api, h } = setup('pre-1')

      await api.handleConflictResolution('discard-mine', 0)

      expect(h.formData.value.gene_symbol).toBe('FRESH')
    })

    it('forces a save at the server version when the user overwrites theirs', async () => {
      updatePrecuration.mockResolvedValue({ id: 'pre-1' } as never)
      const { api, h } = setup('pre-1')

      await api.handleConflictResolution('overwrite-theirs', 9)

      expect(h.formData.value.lock_version).toBe(9)
      expect(updatePrecuration).toHaveBeenCalledWith(
        'pre-1',
        expect.objectContaining({ lock_version: 9 })
      )
    })

    it('only logs when the user chooses to merge manually', async () => {
      const { api } = setup('pre-1')

      await api.handleConflictResolution('merge', 1)

      expect(logger.info).toHaveBeenCalledWith('Manual merge initiated')
      expect(updatePrecuration).not.toHaveBeenCalled()
    })
  })
})
