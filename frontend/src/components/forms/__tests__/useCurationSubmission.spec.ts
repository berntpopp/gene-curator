import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ref, type Ref } from 'vue'
import { useCurationSubmission, type EvidenceData } from '../useCurationSubmission'

const logger = vi.hoisted(() => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }))
const push = vi.hoisted(() => vi.fn())
const replace = vi.hoisted(() => vi.fn())
const addToast = vi.hoisted(() => vi.fn())
const curationsStore = vi.hoisted(() => ({
  saveDraft: vi.fn(),
  createCuration: vi.fn(),
  submitCuration: vi.fn(),
  updateCuration: vi.fn(),
  error: null as { message: string; isConflict?: boolean } | null
}))

vi.mock('@/composables/useLogger', () => ({ useLogger: () => logger }))
vi.mock('vue-router', () => ({ useRouter: () => ({ push, replace }) }))
vi.mock('@/stores/curations', () => ({ useCurationsStore: () => curationsStore }))
vi.mock('@/stores/notifications', () => ({ useNotificationsStore: () => ({ addToast }) }))

interface Setup {
  curationId: { value: string | null | undefined }
  evidenceData: Ref<EvidenceData>
  lockVersion: Ref<number>
  canSubmit: { value: boolean }
  clearRecovery: () => void
  clearHistory: () => void
  onSaved: () => void
  onSubmit: () => void
}

function setup(curationId: string | null = null) {
  const s: Setup = {
    curationId: { value: curationId },
    evidenceData: ref<EvidenceData>({ a: 1 }),
    lockVersion: ref(3),
    canSubmit: { value: true },
    clearRecovery: vi.fn(),
    clearHistory: vi.fn(),
    onSaved: vi.fn(),
    onSubmit: vi.fn()
  }
  const api = useCurationSubmission({
    curationId: () => s.curationId.value,
    geneId: () => 'gene-1',
    scopeId: () => 'scope-1',
    workflowPairId: () => 'wp-1',
    evidenceData: s.evidenceData,
    lockVersion: s.lockVersion,
    canSubmit: () => s.canSubmit.value,
    clearRecovery: s.clearRecovery,
    clearHistory: s.clearHistory,
    onSaved: s.onSaved,
    onSubmit: s.onSubmit
  })
  return { api, s }
}

describe('useCurationSubmission', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  describe('handleSaveDraft', () => {
    it('saves the draft of an existing curation and emits saved', async () => {
      curationsStore.saveDraft.mockResolvedValue({ lock_version: 4 })
      const { api, s } = setup('cur-1')

      await api.handleSaveDraft()

      expect(curationsStore.saveDraft).toHaveBeenCalledWith('cur-1', {
        evidence_data: { a: 1 },
        lock_version: 3
      })
      expect(s.lockVersion.value).toBe(4)
      expect(s.onSaved).toHaveBeenCalled()
      expect(addToast).toHaveBeenCalledWith('Draft saved', 'success')
      expect(s.clearRecovery).toHaveBeenCalled()
      expect(api.savingDraft.value).toBe(false)
    })

    it('does not emit saved when the store returns nothing', async () => {
      curationsStore.saveDraft.mockResolvedValue(undefined)
      const { api, s } = setup('cur-1')

      await api.handleSaveDraft()

      expect(s.onSaved).not.toHaveBeenCalled()
      expect(s.lockVersion.value).toBe(3)
    })

    it.each(['handleSaveDraft', 'handleClinGenSaveDraft'] as const)(
      'a double Ctrl+S sends one request, not a second one with the same version (%s)',
      async name => {
        let finish: (v: unknown) => void = () => {}
        curationsStore.saveDraft.mockReturnValue(new Promise(r => (finish = r)))
        const { api } = setup('cur-1')

        const save = api[name] as (data?: EvidenceData) => Promise<boolean>
        const first = save({ a: 1 })
        const second = await save({ a: 1 })
        finish({ lock_version: 4 })
        await first

        expect(second).toBe(false)
        expect(curationsStore.saveDraft).toHaveBeenCalledTimes(1)
        expect(api.conflict.value).toBe(false)
      }
    )

    it('does not save once a conflict is flagged', async () => {
      curationsStore.saveDraft.mockResolvedValue(null)
      curationsStore.error = { message: 'x', isConflict: true }
      const { api } = setup('cur-1')
      await api.handleSaveDraft()
      curationsStore.saveDraft.mockClear()

      expect(await api.handleSaveDraft()).toBe(false)
      expect(curationsStore.saveDraft).not.toHaveBeenCalled()
    })

    it('flags a conflict (another tab saved first) and keeps the loaded version', async () => {
      curationsStore.saveDraft.mockResolvedValue(null)
      curationsStore.error = {
        message: 'Another user has modified this curation.',
        isConflict: true
      }
      const { api, s } = setup('cur-1')

      expect(await api.handleSaveDraft()).toBe(false)

      expect(api.conflict.value).toBe(true)
      expect(s.lockVersion.value).toBe(3) // never adopt the newer version without a reload
      expect(s.onSaved).not.toHaveBeenCalled()
      expect(addToast).not.toHaveBeenCalledWith('Draft saved', 'success')
    })

    it('shows the API error, never a success toast, when the save is refused (403)', async () => {
      curationsStore.saveDraft.mockResolvedValue(null)
      curationsStore.error = { message: 'Not enough permissions' }
      const { api, s } = setup('cur-1')

      await api.handleSaveDraft()

      expect(addToast).toHaveBeenCalledWith('Not enough permissions', 'error')
      expect(addToast).not.toHaveBeenCalledWith('Draft saved', 'success')
      expect(s.clearRecovery).not.toHaveBeenCalled()
      curationsStore.error = null
    })

    it('shows the API detail when submit fails', async () => {
      curationsStore.submitCuration.mockRejectedValue({
        response: { data: { detail: 'Curation is not in draft' } }
      })
      const { api } = setup('cur-1')

      await api.handleSubmit()

      expect(addToast).toHaveBeenCalledWith('Curation is not in draft', 'error')
    })

    it('creates a curation and navigates to its editor when there is none yet', async () => {
      curationsStore.createCuration.mockResolvedValue({ id: 'new-cur' })
      const { api } = setup()

      await api.handleSaveDraft()

      expect(curationsStore.createCuration).toHaveBeenCalledWith({
        gene_id: 'gene-1',
        scope_id: 'scope-1',
        workflow_pair_id: 'wp-1',
        evidence_data: { a: 1 }
      })
      expect(replace).toHaveBeenCalledWith({
        name: 'curation-edit',
        params: { scopeId: 'scope-1', curationId: 'new-cur' }
      })
    })

    it('reports failures and clears the saving flag', async () => {
      curationsStore.saveDraft.mockRejectedValue({ message: 'offline' })
      const { api } = setup('cur-1')

      await api.handleSaveDraft()

      expect(logger.error).toHaveBeenCalledWith('Failed to save draft', { error: 'offline' })
      expect(addToast).toHaveBeenCalledWith('Failed to save draft', 'error')
      expect(api.savingDraft.value).toBe(false)
    })
  })

  describe('handleSubmit', () => {
    it('does nothing when submission is not allowed', async () => {
      const { api, s } = setup('cur-1')
      s.canSubmit.value = false

      await api.handleSubmit()

      expect(curationsStore.submitCuration).not.toHaveBeenCalled()
    })

    it('submits an existing curation with its lock version', async () => {
      const { api, s } = setup('cur-1')

      await api.handleSubmit()

      expect(curationsStore.submitCuration).toHaveBeenCalledWith('cur-1', { lock_version: 3 })
      expect(addToast).toHaveBeenCalledWith('Curation submitted for review', 'success')
      expect(s.clearRecovery).toHaveBeenCalled()
      expect(s.clearHistory).toHaveBeenCalled()
      expect(s.onSubmit).toHaveBeenCalled()
    })

    it('creates and then submits a new curation at version 0', async () => {
      curationsStore.createCuration.mockResolvedValue({ id: 'new-cur' })
      const { api } = setup()

      await api.handleSubmit()

      expect(curationsStore.submitCuration).toHaveBeenCalledWith('new-cur', { lock_version: 0 })
    })

    it('reports failures without emitting submit', async () => {
      curationsStore.submitCuration.mockRejectedValue({ message: 'locked' })
      const { api, s } = setup('cur-1')

      await api.handleSubmit()

      expect(logger.error).toHaveBeenCalledWith('Failed to submit curation', { error: 'locked' })
      expect(addToast).toHaveBeenCalledWith('Failed to submit curation', 'error')
      expect(s.onSubmit).not.toHaveBeenCalled()
      expect(api.submitting.value).toBe(false)
    })
  })

  describe('lock version tracking (409 after save-then-submit on a new curation)', () => {
    it('takes the version of a created draft, so a following submit is not stale', async () => {
      curationsStore.createCuration.mockResolvedValue({ id: 'new-cur', lock_version: 0 })
      const { api, s } = setup()
      await api.handleSaveDraft()
      expect(s.lockVersion.value).toBe(0)
      s.lockVersion.value = 3
      await api.handleClinGenSaveDraft({})
      expect(s.lockVersion.value).toBe(0)
    })

    it('creates and submits at the version the create returned', async () => {
      curationsStore.createCuration.mockResolvedValue({ id: 'n', lock_version: 2 })
      const first = setup()
      await first.api.handleSubmit()
      expect(curationsStore.submitCuration).toHaveBeenCalledWith('n', { lock_version: 2 })
      expect(first.s.onSubmit).toHaveBeenCalledWith('n')
      await setup().api.handleClinGenSubmit({})
      expect(curationsStore.submitCuration).toHaveBeenLastCalledWith('n', { lock_version: 2 })
    })

    it('takes the version a submit returned', async () => {
      curationsStore.submitCuration.mockResolvedValue({ id: 'cur-1', lock_version: 9 })
      curationsStore.updateCuration.mockResolvedValue({ lock_version: 4 })
      const a = setup('cur-1')
      await a.api.handleSubmit()
      expect(a.s.lockVersion.value).toBe(9)
      const b = setup('cur-1')
      await b.api.handleClinGenSubmit({})
      expect(b.s.lockVersion.value).toBe(9)
    })

    it.each(['handleSubmit', 'handleClinGenSubmit'] as const)(
      'shows the conflict, not a generic error, when submit hits a 409 (%s)',
      async name => {
        const err = { response: { status: 409, data: { detail: { error: 'Concurrent' } } } }
        curationsStore.submitCuration.mockRejectedValue(err)
        curationsStore.updateCuration.mockRejectedValue(err)
        curationsStore.error = { message: 'Curation was modified.', isConflict: true }
        const { api } = setup('cur-1')
        await (api[name] as (d?: EvidenceData) => Promise<void>)({})
        expect(api.conflict.value).toBe(true)
        expect(addToast).toHaveBeenCalledWith('Curation was modified.', 'error')
        curationsStore.error = null
      }
    )
  })

  describe('ClinGen handlers', () => {
    const clingen: EvidenceData = { evidence_items: [] }

    it('updates then submits an existing curation at the lock version the update returned', async () => {
      curationsStore.updateCuration.mockResolvedValue({ lock_version: 7 })
      const { api, s } = setup('cur-1')

      await api.handleClinGenSubmit(clingen)

      expect(curationsStore.updateCuration).toHaveBeenCalledWith('cur-1', {
        evidence_data: clingen,
        lock_version: 3
      })
      expect(curationsStore.submitCuration).toHaveBeenCalledWith('cur-1', { lock_version: 7 })
      expect(s.onSubmit).toHaveBeenCalled()
    })

    it('creates and submits a new ClinGen curation', async () => {
      curationsStore.createCuration.mockResolvedValue({ id: 'new-cg' })
      const { api, s } = setup()

      await api.handleClinGenSubmit(clingen)

      expect(curationsStore.createCuration).toHaveBeenCalledWith(
        expect.objectContaining({ evidence_data: clingen })
      )
      expect(curationsStore.submitCuration).toHaveBeenCalledWith('new-cg', { lock_version: 0 })
      expect(s.onSubmit).toHaveBeenCalled()
    })

    it('reports ClinGen submit failures', async () => {
      curationsStore.updateCuration.mockRejectedValue({ message: 'boom' })
      const { api, s } = setup('cur-1')

      await api.handleClinGenSubmit(clingen)

      expect(logger.error).toHaveBeenCalledWith('Failed to submit ClinGen curation', {
        error: 'boom'
      })
      expect(s.onSubmit).not.toHaveBeenCalled()
      expect(api.submitting.value).toBe(false)
    })

    it('saves a ClinGen draft for an existing curation', async () => {
      curationsStore.saveDraft.mockResolvedValue({ lock_version: 8 })
      const { api, s } = setup('cur-1')

      await api.handleClinGenSaveDraft(clingen)

      expect(curationsStore.saveDraft).toHaveBeenCalledWith('cur-1', {
        evidence_data: clingen,
        lock_version: 3
      })
      expect(s.lockVersion.value).toBe(8)
      expect(s.onSaved).toHaveBeenCalled()
      expect(api.savingDraft.value).toBe(false)
    })

    it('creates a ClinGen draft and navigates to the editor when new', async () => {
      curationsStore.createCuration.mockResolvedValue({ id: 'new-cg' })
      const { api } = setup()

      await api.handleClinGenSaveDraft(clingen)

      expect(replace).toHaveBeenCalledWith({
        name: 'curation-edit',
        params: { scopeId: 'scope-1', curationId: 'new-cg' }
      })
      expect(addToast).toHaveBeenCalledWith('Draft saved', 'success')
    })

    it('reports ClinGen draft failures', async () => {
      curationsStore.saveDraft.mockRejectedValue({ message: 'nope' })
      const { api } = setup('cur-1')

      await api.handleClinGenSaveDraft(clingen)

      expect(logger.error).toHaveBeenCalledWith('Failed to save ClinGen draft', { error: 'nope' })
      expect(addToast).toHaveBeenCalledWith('Failed to save draft', 'error')
    })
  })

  describe('save result for the workspace frame', () => {
    const clingen: EvidenceData = { evidence_items: [] }
    it('resolves true on success, also for a first save, and reports it as saved', async () => {
      curationsStore.saveDraft.mockResolvedValue({ lock_version: 4 })
      curationsStore.createCuration.mockResolvedValue({ id: 'n' })
      const existing = setup('cur-1')
      expect(await existing.api.handleSaveDraft()).toBe(true)
      expect(await existing.api.handleClinGenSaveDraft(clingen)).toBe(true)
      const fresh = setup()
      expect(await fresh.api.handleSaveDraft()).toBe(true)
      expect(fresh.s.onSaved).toHaveBeenCalled()
      const freshClinGen = setup()
      expect(await freshClinGen.api.handleClinGenSaveDraft(clingen)).toBe(true)
      expect(freshClinGen.s.onSaved).toHaveBeenCalled()
    })

    it('resolves false when the save is refused or throws', async () => {
      curationsStore.saveDraft.mockResolvedValueOnce(undefined).mockRejectedValue({ message: 'x' })
      const { api } = setup('cur-1')
      expect(await api.handleSaveDraft()).toBe(false)
      expect(await api.handleSaveDraft()).toBe(false)
      expect(await api.handleClinGenSaveDraft(clingen)).toBe(false)
    })
  })
})
