import { ref } from 'vue'
import { workflowAPI } from '@/api'
import { useLogger } from '@/composables/useLogger'
import { useNotificationsStore } from '@/stores/notifications'
import { useWorkCountsStore } from '@/stores/workCounts'
import { readableApiError } from '@/utils/apiErrorText'

/** Approve (-> active, or recorded while more approvals are needed) and request changes (-> back to curation) for a curation in review. */
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
    doneMessage: (toStage: string) => string
  ) {
    busy.value = true
    error.value = null
    try {
      const done = await workflowAPI.transitionCuration(curationId(), { target_stage, notes })
      showApprove.value = false
      showReject.value = false
      notifications.addToast(doneMessage(done.to_stage), 'success')
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
      // With reviewers_required > 1 an approval can leave the curation in review
      transition('active', note || null, to =>
        to === 'active'
          ? 'Curation approved and activated'
          : 'Approval recorded; more reviewers must approve'
      ),
    reject: (feedback: string) =>
      transition('curation', feedback, () => 'Curation returned to curator for changes')
  }
}
