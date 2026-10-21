import { ref, watch, type Ref } from 'vue'
import { useRouter } from 'vue-router'
import { useCurationsStore } from '@/stores/curations'
import { useNotificationsStore } from '@/stores/notifications'
import { useLogger } from '@/composables/useLogger'
import type { ClinGenEvidenceData } from '@/components/clingen/types'
import { apiDetail } from './apiDetail'
import type { ApiErrorLike } from './types'

export type EvidenceData = Record<string, unknown>

/** Curation fields read after a create/update/save call. */
interface CurationRecord {
  id: string
  lock_version?: number | null
}

export interface CurationSubmissionOptions {
  curationId: () => string | null | undefined
  geneId: () => string | null | undefined
  scopeId: () => string
  workflowPairId: () => string | null | undefined
  evidenceData: Ref<EvidenceData>
  lockVersion: Ref<number>
  canSubmit: () => boolean
  clearRecovery: () => void
  clearHistory: () => void
  onSaved: () => void
  /** Receives the id of the submitted curation (new when it was created on submit). */
  onSubmit: (id: string) => void
}

/**
 * Save-draft and submit operations for SchemaDrivenCurationForm, both for the
 * generic DynamicForm path and for the ClinGen-specific form.
 */
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
    clearHistory
  } = options
  const router = useRouter()
  const logger = useLogger()
  const curationsStore = useCurationsStore()
  const notificationsStore = useNotificationsStore()

  const savingDraft = ref(false)
  // Another tab saved first: saving is blocked until the page is reloaded (see SaveState)
  const conflict = ref(false)
  // The local copy is older than the server's: never offer it back after the reload
  watch(conflict, isConflict => isConflict && clearRecovery())
  const submitting = ref(false)

  /** Payload for a new curation; a gene and workflow pair are required by the API. */
  function createPayload(evidence: EvidenceData) {
    const gene_id = geneId()
    const workflow_pair_id = workflowPairId()
    if (!gene_id || !workflow_pair_id) throw new Error('A gene and a workflow pair are required')
    return { gene_id, scope_id: scopeId(), workflow_pair_id, evidence_data: evidence }
  }

  /** Submit at a known version and keep the version the server answers with. */
  async function submitAt(id: string, version: number): Promise<string> {
    const submitted = (await curationsStore.submitCuration(id, { lock_version: version })) as
      CurationRecord | undefined
    if (submitted?.lock_version != null) lockVersion.value = submitted.lock_version
    return id
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
        evidence_data: evidenceData.value,
        lock_version: lockVersion.value
      }

      const id = curationId()
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
        options.onSaved()
      } else {
        // Create new curation as draft
        const created = (await curationsStore.createCuration(
          createPayload(evidenceData.value)
        )) as CurationRecord
        lockVersion.value = created.lock_version ?? 0
        options.onSaved()
        // Navigate to edit the created curation
        router.replace({
          name: 'curation-edit',
          params: { scopeId: scopeId(), curationId: created.id }
        })
      }

      notificationsStore.addToast('Draft saved', 'success')
      clearRecovery()
      return true
    } catch (error) {
      logger.error('Failed to save draft', { error: (error as ApiErrorLike).message })
      notificationsStore.addToast(apiDetail(error, 'Failed to save draft'), 'error')
      return false
    } finally {
      savingDraft.value = false
    }
  }

  /**
   * Submit curation
   */
  async function handleSubmit() {
    if (!canSubmit()) return

    submitting.value = true
    let submittedId: string
    try {
      const id = curationId()
      if (id) {
        submittedId = await submitAt(id, lockVersion.value)
      } else {
        // Create and submit
        const created = (await curationsStore.createCuration(
          createPayload(evidenceData.value)
        )) as CurationRecord
        submittedId = await submitAt(created.id, created.lock_version ?? 0)
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

  /**
   * Handle ClinGen form submit
   * Receives full evidence data from ClinGenCurationForm
   */
  async function handleClinGenSubmit(clingenEvidenceData: ClinGenEvidenceData | EvidenceData) {
    submitting.value = true
    let submittedId: string
    try {
      const id = curationId()
      if (id) {
        // Update existing curation evidence and submit
        const updated = (await curationsStore.updateCuration(id, {
          evidence_data: { ...clingenEvidenceData },
          lock_version: lockVersion.value
        })) as CurationRecord
        // The update bumped the version: keep it, so a retry after a refused submit is not stale
        lockVersion.value = updated.lock_version as number
        submittedId = await submitAt(id, lockVersion.value)
      } else {
        // Create and submit new curation
        const created = (await curationsStore.createCuration(
          createPayload({ ...clingenEvidenceData })
        )) as CurationRecord
        submittedId = await submitAt(created.id, created.lock_version ?? 0)
      }

      notificationsStore.addToast('Curation submitted for review', 'success')
      clearRecovery()
      options.onSubmit(submittedId)
    } catch (error) {
      logger.error('Failed to submit ClinGen curation', { error: (error as ApiErrorLike).message })
      reportSubmitError(error)
    } finally {
      submitting.value = false
    }
  }

  /**
   * Handle ClinGen form save draft
   */
  async function handleClinGenSaveDraft(
    clingenEvidenceData: ClinGenEvidenceData | EvidenceData
  ): Promise<boolean> {
    if (savingDraft.value || conflict.value) return false
    savingDraft.value = true
    try {
      const id = curationId()
      if (id) {
        const updated = (await curationsStore.saveDraft(id, {
          evidence_data: { ...clingenEvidenceData },
          lock_version: lockVersion.value
        })) as CurationRecord | undefined
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
        options.onSaved()
      } else {
        // Create new curation as draft
        const created = (await curationsStore.createCuration(
          createPayload({ ...clingenEvidenceData })
        )) as CurationRecord
        lockVersion.value = created.lock_version ?? 0
        options.onSaved()
        // Navigate to edit the created curation
        router.replace({
          name: 'curation-edit',
          params: { scopeId: scopeId(), curationId: created.id }
        })
      }

      notificationsStore.addToast('Draft saved', 'success')
      clearRecovery()
      return true
    } catch (error) {
      logger.error('Failed to save ClinGen draft', { error: (error as ApiErrorLike).message })
      notificationsStore.addToast(apiDetail(error, 'Failed to save draft'), 'error')
      return false
    } finally {
      savingDraft.value = false
    }
  }

  return {
    savingDraft,
    conflict,
    submitting,
    handleSaveDraft,
    handleSubmit,
    handleClinGenSubmit,
    handleClinGenSaveDraft
  }
}
