import { ref } from 'vue'
import { workflowAPI } from '@/api'
import { useLogger } from '@/composables/useLogger'
import { useNotificationsStore } from '@/stores/notifications'
import { useWorkCountsStore } from '@/stores/workCounts'
import { readableApiError } from '@/utils/apiErrorText'

/** Approve (-> active) and request changes (-> back to curation) for a curation in review. */
export function useReviewTransitions(curationId: () => string, reload: () => Promise<void>) {
  const logger = useLogger()
  const notifications = useNotificationsStore()
  const workCounts = useWorkCountsStore()

  const showApprove = ref(false)
  const showReject = ref(false)
  const busy = ref(false)
  const error = ref<string | null>(null)

  /** Open a dialog with a clean error state. */
  function open(kind: 'approve' | 'reject') {
    error.value = null
    if (kind === 'approve') showApprove.value = true
    else showReject.value = true
  }

  // The API detail is shown inside the dialog, not just as a toast
  async function transition(
    target_stage: 'active' | 'curation',
    notes: string | null,
    doneMessage: string
  ) {
    busy.value = true
    error.value = null
    try {
      await workflowAPI.transitionCuration(curationId(), { target_stage, notes })
      showApprove.value = false
      showReject.value = false
      notifications.addToast(doneMessage, 'success')
      workCounts.fetch()
      await reload()
    } catch (err) {
      error.value = readableApiError(err, 'Request failed')
      logger.error('Failed review transition', { target_stage, error: error.value })
    } finally {
      busy.value = false
    }
  }

  return {
    showApprove,
    showReject,
    busy,
    error,
    open,
    approve: (note: string) =>
      transition('active', note || null, 'Curation approved and activated'),
    reject: (feedback: string) =>
      transition('curation', feedback, 'Curation returned to curator for changes')
  }
}
