import { ref, type Ref } from 'vue'
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
  onSubmit: () => void
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
  const submitting = ref(false)

  /** Payload for a new curation; a gene and workflow pair are required by the API. */
  function createPayload(evidence: EvidenceData) {
    const gene_id = geneId()
    const workflow_pair_id = workflowPairId()
    if (!gene_id || !workflow_pair_id) throw new Error('A gene and a workflow pair are required')
    return { gene_id, scope_id: scopeId(), workflow_pair_id, evidence_data: evidence }
  }

  /**
   * Save draft
   */
  async function handleSaveDraft() {
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
          notificationsStore.addToast(
            curationsStore.error?.message || 'Failed to save draft',
            'error'
          )
          return
        }
        lockVersion.value = updated.lock_version as number
        options.onSaved()
      } else {
        // Create new curation as draft
        const created = (await curationsStore.createCuration(
          createPayload(evidenceData.value)
        )) as CurationRecord
        // Navigate to edit the created curation
        router.replace({
          name: 'curation-edit',
          params: { scopeId: scopeId(), curationId: created.id }
        })
      }

      notificationsStore.addToast('Draft saved', 'success')
      clearRecovery()
    } catch (error) {
      logger.error('Failed to save draft', { error: (error as ApiErrorLike).message })
      notificationsStore.addToast(apiDetail(error, 'Failed to save draft'), 'error')
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
    try {
      const id = curationId()
      if (id) {
        await curationsStore.submitCuration(id, {
          lock_version: lockVersion.value
        })
      } else {
        // Create and submit
        const created = (await curationsStore.createCuration(
          createPayload(evidenceData.value)
        )) as CurationRecord
        await curationsStore.submitCuration(created.id, { lock_version: 0 })
      }

      notificationsStore.addToast('Curation submitted for review', 'success')
      clearRecovery()
      clearHistory()
      options.onSubmit()
    } catch (error) {
      logger.error('Failed to submit curation', { error: (error as ApiErrorLike).message })
      notificationsStore.addToast(apiDetail(error, 'Failed to submit curation'), 'error')
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
    try {
      const id = curationId()
      if (id) {
        // Update existing curation evidence and submit
        const updated = (await curationsStore.updateCuration(id, {
          evidence_data: { ...clingenEvidenceData },
          lock_version: lockVersion.value
        })) as CurationRecord
        await curationsStore.submitCuration(id, { lock_version: updated.lock_version as number })
      } else {
        // Create and submit new curation
        const created = (await curationsStore.createCuration(
          createPayload({ ...clingenEvidenceData })
        )) as CurationRecord
        await curationsStore.submitCuration(created.id, { lock_version: 0 })
      }

      notificationsStore.addToast('Curation submitted for review', 'success')
      clearRecovery()
      options.onSubmit()
    } catch (error) {
      logger.error('Failed to submit ClinGen curation', { error: (error as ApiErrorLike).message })
      notificationsStore.addToast(apiDetail(error, 'Failed to submit curation'), 'error')
    } finally {
      submitting.value = false
    }
  }

  /**
   * Handle ClinGen form save draft
   */
  async function handleClinGenSaveDraft(clingenEvidenceData: ClinGenEvidenceData | EvidenceData) {
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
          notificationsStore.addToast(
            curationsStore.error?.message || 'Failed to save draft',
            'error'
          )
          return
        }
        lockVersion.value = updated.lock_version as number
        options.onSaved()
      } else {
        // Create new curation as draft
        const created = (await curationsStore.createCuration(
          createPayload({ ...clingenEvidenceData })
        )) as CurationRecord
        // Navigate to edit the created curation
        router.replace({
          name: 'curation-edit',
          params: { scopeId: scopeId(), curationId: created.id }
        })
      }

      notificationsStore.addToast('Draft saved', 'success')
      clearRecovery()
    } catch (error) {
      logger.error('Failed to save ClinGen draft', { error: (error as ApiErrorLike).message })
      notificationsStore.addToast(apiDetail(error, 'Failed to save draft'), 'error')
    } finally {
      savingDraft.value = false
    }
  }

  return {
    savingDraft,
    submitting,
    handleSaveDraft,
    handleSubmit,
    handleClinGenSubmit,
    handleClinGenSaveDraft
  }
}
