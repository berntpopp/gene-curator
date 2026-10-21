import { defineStore } from 'pinia'
import { reviewCommentsAPI } from '@/api/reviewComments'
import { workflowAPI } from '@/api'
import type { Schema } from '@/types/api'

export interface ReviewFeedback {
  /** Notes of the request-changes that sent the curation back (null once it was resubmitted). */
  note: string | null
  /** Who sent it back, and when (with the note). */
  noteBy: string | null
  noteAt: string | null
  /** The reviewers' open queries (the curator's own replies excluded). */
  queries: Schema<'ReviewComment'>[]
  any: boolean
}

/** What a reviewer told the curator after changes were requested: the note and open item queries. */
export const useReviewFeedbackStore = defineStore('reviewFeedback', () => {
  async function fetch(curationId: string, me: string): Promise<ReviewFeedback> {
    const [comments, history] = await Promise.allSettled([
      reviewCommentsAPI.list(curationId),
      workflowAPI.getCurationWorkflowHistory(curationId)
    ])
    const queries =
      comments.status === 'fulfilled'
        ? comments.value.filter(
            c => c.kind === 'query' && c.status === 'open' && c.author_id !== me
          )
        : []
    let sentBack: Schema<'WorkflowAuditEntry'> | undefined
    if (history.status === 'fulfilled') {
      const latest = [...history.value.entries].sort((a, b) =>
        b.executed_at.localeCompare(a.executed_at)
      )[0]
      if (latest?.from_stage === 'review' && latest.to_stage === 'curation') sentBack = latest
    }
    const note = sentBack?.notes ?? null
    return {
      note,
      noteBy: (note && sentBack?.executed_by_name) || null,
      noteAt: (note && sentBack?.executed_at) || null,
      queries,
      any: !!note || queries.length > 0
    }
  }

  return { fetch }
})
