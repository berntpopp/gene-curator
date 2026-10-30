import type { Schema } from '@/types/api'

export type ApprovalNotice = { message: string; curationId: string }

/** An approval that created no curation names the open one that blocked it (#530). */
export function blockedBy(r: Schema<'PrecurationApprovalResult'>): ApprovalNotice | null {
  return !r.curation_created && r.curation_id
    ? { message: r.message, curationId: r.curation_id }
    : null
}
