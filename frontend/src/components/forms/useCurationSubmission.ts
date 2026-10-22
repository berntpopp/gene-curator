import { ref, type Ref } from 'vue'
import { useRouter } from 'vue-router'
import { recoveryVersion } from '@/utils/formRecoveryStorage'
import { useCurationsStore } from '@/stores/curations'
import { useNotificationsStore } from '@/stores/notifications'
import { useLogger } from '@/composables/useLogger'
import { replaceKeepingChanges } from '@/components/workspace/useUnsavedGuard'
import { apiDetail } from './apiDetail'
import type { ApiErrorLike } from './types'

export type EvidenceData = Record<string, unknown>

/** Curation fields read after a create/update/save call. */
interface CurationRecord {
  id: string
  lock_version?: number | null
  updated_at?: string | null
}

export interface CurationSubmissionOptions {
  curationId: () => string | null | undefined
  geneId: () => string | null | undefined
  scopeId: () => string
  workflowPairId: () => string | null | undefined
  /** Precuration a new curation links to (a re-curation carries its source's). */
  precurationId?: () => string | null
  evidenceData: Ref<EvidenceData>
  lockVersion: Ref<number>
  canSubmit: () => boolean
  clearRecovery: () => void
  /** The evidence reached the server at this version: local recovery compares with it now */
  markSaved: (saved: EvidenceData, version: string) => void
  clearHistory: () => void
  onSaved: () => void
  /** Receives the id of the submitted curation (new when it was created on submit). */
  onSubmit: (id: string) => void
}

/** Save-draft and submit operations for SchemaDrivenCurationForm. */
export function useCurationSubmission(options: CurationSubmissionOptions) {
  const {
    curationId,
    geneId,
    scopeId,
    workflowPairId,
    evidenceData,
    lockVersion,
    canSubmit,
    clearRecovery,
    markSaved,
    clearHistory
  } = options
  const router = useRouter()
  const logger = useLogger()
  const curationsStore = useCurationsStore()
  const notificationsStore = useNotificationsStore()

  const savingDraft = ref(false)
  // Another tab saved first: saving is blocked until the page is reloaded (see SaveState); the
  // local recovery copy is kept and offered back after the reload, flagged as older
  const conflict = ref(false)
  const submitting = ref(false)
  // Created by a submit that was then refused: a retry reuses it rather than creating another
  let createdId: string | null = null
  const existingId = () => curationId() || createdId

  /** The created curation's edit page is the same document: no leave prompt, the form stays. */
  const openCreated = (id: string) =>
    replaceKeepingChanges(router, {
      name: 'curation-edit',
      params: { scopeId: scopeId(), curationId: id }
    })

  /** Payload for a new curation; a gene and workflow pair are required by the API. */
  function createPayload(evidence: EvidenceData) {
    const gene_id = geneId()
    const workflow_pair_id = workflowPairId()
    if (!gene_id || !workflow_pair_id) throw new Error('A gene and a workflow pair are required')
    const precuration_id = options.precurationId?.()
    return {
      gene_id,
      scope_id: scopeId(),
      workflow_pair_id,
      ...(precuration_id && { precuration_id }),
      evidence_data: evidence
    }
  }

  /** Submit at a known version and keep the version the server answers with. */
  async function submitAt(id: string, version: number): Promise<string> {
    const submitted = (await curationsStore.submitCuration(id, { lock_version: version })) as
      CurationRecord | undefined
    if (submitted?.lock_version != null) lockVersion.value = submitted.lock_version
    return id
  }

  /**
   * Submit a curation this form just created. Only a refused submit moves to its edit page, so a
   * reload reopens it; on success the URL stays, because App.vue remounts the view on any URL
   * change and the unmounted view would never receive `submit` to open the detail page.
   */
  async function submitCreated(created: CurationRecord): Promise<string> {
    createdId = created.id
    lockVersion.value = created.lock_version ?? 0
    try {
      return await submitAt(created.id, lockVersion.value)
    } catch (error) {
      await openCreated(created.id)
      throw error
    }
  }

  /** A 409 shows the conflict banner and the store's conflict text, not a generic error. */
  function reportSubmitError(error: unknown) {
    if (curationsStore.error?.isConflict) {
      conflict.value = true
      notificationsStore.addToast(
        curationsStore.error.message ?? 'Failed to submit curation',
        'error'
      )
      return
    }
    notificationsStore.addToast(apiDetail(error, 'Failed to submit curation'), 'error')
  }

  /**
   * Save draft
   */
  /** Resolves true when the draft reached the server (the workspace frame shows the result). */
  async function handleSaveDraft(): Promise<boolean> {
    // A second Ctrl+S in flight would reuse the same version and 409 against ourselves
    if (savingDraft.value || conflict.value) return false
    savingDraft.value = true
    try {
      const payload = {
        // A copy: nested edits typed during the save mutate the form's objects in place
        evidence_data: JSON.parse(JSON.stringify(evidenceData.value)) as EvidenceData,
        lock_version: lockVersion.value
      }

      const id = existingId()
      if (id) {
        const updated = (await curationsStore.saveDraft(id, payload)) as CurationRecord | undefined
        if (!updated) {
          // The store swallows save errors and returns nothing: surface them, no success toast
          if (curationsStore.error?.isConflict) conflict.value = true
          notificationsStore.addToast(
            curationsStore.error?.message || 'Failed to save draft',
            'error'
          )
          return false
        }
        lockVersion.value = updated.lock_version as number
        markSaved(payload.evidence_data, recoveryVersion(updated))
        options.onSaved()
      } else {
        // Create new curation as draft
        const created = (await curationsStore.createCuration(
          createPayload(evidenceData.value)
        )) as CurationRecord
        lockVersion.value = created.lock_version ?? 0
        options.onSaved()
        await openCreated(created.id)
        clearRecovery() // the edit page loads the created curation under its own key
      }

      notificationsStore.addToast('Draft saved', 'success')
      return true
    } catch (error) {
      logger.error('Failed to save draft', { error: (error as ApiErrorLike).message })
      notificationsStore.addToast(apiDetail(error, 'Failed to save draft'), 'error')
      return false
    } finally {
      savingDraft.value = false
    }
  }

  /** Save the current evidence, then submit it (unsaved edits are never left behind). */
  async function handleSubmit() {
    if (!canSubmit()) return

    submitting.value = true
    let submittedId: string
    try {
      const id = existingId()
      if (id) {
        // Update existing curation evidence and submit
        const evidence = JSON.parse(JSON.stringify(evidenceData.value)) as EvidenceData
        const updated = (await curationsStore.updateCuration(id, {
          evidence_data: evidence,
          lock_version: lockVersion.value
        })) as CurationRecord
        // The update bumped the version: keep it, so a retry after a refused submit is not stale
        lockVersion.value = updated.lock_version as number
        markSaved(evidence, recoveryVersion(updated))
        submittedId = await submitAt(id, lockVersion.value)
      } else {
        // Create and submit new curation
        const created = (await curationsStore.createCuration(
          createPayload({ ...evidenceData.value })
        )) as CurationRecord
        submittedId = await submitCreated(created)
      }

      notificationsStore.addToast('Curation submitted for review', 'success')
      clearRecovery()
      clearHistory()
      options.onSubmit(submittedId)
    } catch (error) {
      logger.error('Failed to submit curation', { error: (error as ApiErrorLike).message })
      reportSubmitError(error)
    } finally {
      submitting.value = false
    }
  }

  return {
    savingDraft,
    conflict,
    submitting,
    handleSaveDraft,
    handleSubmit
  }
}
