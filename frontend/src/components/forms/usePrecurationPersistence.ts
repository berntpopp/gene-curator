import { ref, type Ref } from 'vue'
import { useRouter } from 'vue-router'
import { precurationsAPI } from '@/api'
import { useLogger } from '@/composables/useLogger'
import type { ApiErrorLike, ComponentLogger } from './types'

export interface PrecurationFormData {
  gene_symbol: string
  scope_id: string
  hpo_terms: string[]
  rationale: string
  pmids: string[]
  curator_notes: string
  lock_version: number
}

/** Payload sent to the create/draft/update endpoints. */
export interface PrecurationPayload {
  gene_symbol: string
  scope_id: string
  evidence_data: {
    hpo_terms: string[]
    rationale: string
    pmids: string[]
    curator_notes: string
  }
  is_draft: boolean
  lock_version: number
}

/** Subset of the precuration response this form reads. */
export interface PrecurationRecord {
  id: string
  gene_symbol?: string
  scope_id?: string
  lock_version?: number
  is_draft?: boolean
  evidence_data?: {
    hpo_terms?: string[]
    rationale?: string
    pmids?: string[]
    curator_notes?: string
  }
}

export interface PrecurationPersistenceOptions {
  precurationId: () => string | null | undefined
  isFormValid: () => boolean
  formData: Ref<PrecurationFormData>
  isDraft: Ref<boolean>
  saveWithLockCheck: (
    apiCall: (data: PrecurationPayload) => Promise<unknown>,
    payload: PrecurationPayload,
    currentVersion: number
  ) => Promise<unknown>
  clearRecovery: () => void
  clearHistory: () => void
  onSuccess: (result: PrecurationRecord) => void
}

/**
 * Load, submit and draft-save operations for PrecurationForm.
 */
export function usePrecurationPersistence(options: PrecurationPersistenceOptions) {
  const { precurationId, formData, isDraft, saveWithLockCheck, clearRecovery, clearHistory } =
    options
  const router = useRouter()
  const logger = useLogger() as ComponentLogger

  const submitting = ref(false)
  const savingDraft = ref(false)

  /**
   * Build the API payload from the current form state
   */
  function buildPayload(draft: boolean): PrecurationPayload {
    return {
      gene_symbol: formData.value.gene_symbol,
      scope_id: formData.value.scope_id,
      evidence_data: {
        hpo_terms: formData.value.hpo_terms,
        rationale: formData.value.rationale,
        pmids: formData.value.pmids,
        curator_notes: formData.value.curator_notes
      },
      is_draft: draft,
      lock_version: formData.value.lock_version
    }
  }

  /**
   * The API JSDoc describes gene_id/precuration_schema_id, but this form has always sent
   * gene_symbol and is_draft (pre-existing mismatch, kept unchanged; see report).
   */
  function createPrecuration(payload: PrecurationPayload): Promise<PrecurationRecord> {
    // @ts-expect-error payload shape differs from the API's documented create request
    return precurationsAPI.createPrecuration(payload)
  }

  /**
   * Load existing precuration for editing
   */
  async function loadPrecuration() {
    try {
      const precuration = (await precurationsAPI.getPrecuration(
        precurationId() as string
      )) as PrecurationRecord

      formData.value = {
        gene_symbol: precuration.gene_symbol || '',
        scope_id: precuration.scope_id || '',
        hpo_terms: precuration.evidence_data?.hpo_terms || [],
        rationale: precuration.evidence_data?.rationale || '',
        pmids: precuration.evidence_data?.pmids || [],
        curator_notes: precuration.evidence_data?.curator_notes || '',
        lock_version: precuration.lock_version || 0
      }

      isDraft.value = precuration.is_draft || false

      logger.info('Precuration loaded for editing', { id: precurationId() })
    } catch (error) {
      logger.error('Failed to load precuration', { error: (error as ApiErrorLike).message })
      // Show error notification
    }
  }

  /**
   * Handle form submission
   */
  async function handleSubmit() {
    if (!options.isFormValid()) {
      logger.warn('Form validation failed')
      return
    }

    submitting.value = true

    try {
      const payload = buildPayload(false)

      let result: PrecurationRecord
      if (precurationId()) {
        // Update with optimistic locking
        result = (await saveWithLockCheck(
          (data: PrecurationPayload) =>
            precurationsAPI.updatePrecuration(precurationId() as string, data),
          payload,
          formData.value.lock_version
        )) as PrecurationRecord
      } else {
        // Create new
        result = await createPrecuration(payload)
      }

      // Clear recovery and history on successful submit
      clearRecovery()
      clearHistory()

      logger.info('Precuration submitted successfully', { id: result.id })
      options.onSuccess(result)

      // Navigate to success page or list
      router.push({ name: 'Precurations' })
    } catch (error) {
      if ((error as ApiErrorLike).response?.status !== 409) {
        // Not a conflict - show error
        logger.error('Failed to submit precuration', { error: (error as ApiErrorLike).message })
      }
      // Conflict (409) is handled by useOptimisticLocking
    } finally {
      submitting.value = false
    }
  }

  /**
   * Save as draft
   */
  async function handleSaveDraft() {
    savingDraft.value = true

    try {
      const payload = buildPayload(true)

      let result: PrecurationRecord
      if (precurationId()) {
        result = (await precurationsAPI.saveDraft(
          precurationId() as string,
          payload
        )) as PrecurationRecord
      } else {
        result = await createPrecuration(payload)
      }

      // Update lock version
      // Same assignment as before the TS migration (undefined stays undefined)
      formData.value.lock_version = result.lock_version as number

      logger.info('Draft saved', { id: result.id })
    } catch (error) {
      logger.error('Failed to save draft', { error: (error as ApiErrorLike).message })
    } finally {
      savingDraft.value = false
    }
  }

  /**
   * Handle conflict resolution
   */
  async function handleConflictResolution(resolution: string, theirVersion: number) {
    if (resolution === 'discard-mine') {
      // Reload their version
      await loadPrecuration()
    } else if (resolution === 'overwrite-theirs') {
      // Force save with their version number + 1
      formData.value.lock_version = theirVersion
      await handleSubmit()
    } else if (resolution === 'merge') {
      // Show merge UI (future enhancement)
      logger.info('Manual merge initiated')
    }
  }

  return {
    submitting,
    savingDraft,
    loadPrecuration,
    handleSubmit,
    handleSaveDraft,
    handleConflictResolution
  }
}
