import type { Schema } from '@/types/api'

export type ApprovalNotice = { message: string; curationId: string }

/** An approval that created no curation names the open one that blocked it (#530). */
export function blockedBy(r: Schema<'PrecurationApprovalResult'>): ApprovalNotice | null {
  return !r.curation_created && r.curation_id
    ? // the link opens it; a raw UUID in the text means nothing to a reader
      { message: r.message.replace(r.curation_id, 'of this gene'), curationId: r.curation_id }
    : null
}
