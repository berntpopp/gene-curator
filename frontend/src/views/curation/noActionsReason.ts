/** Why a user has no workflow action on a curation (monkey R2-5). */
export function noActionsReason(
  c: { status?: string; corrected_disease?: boolean; approvals_remaining?: number | null },
  isAuthorInReview: boolean
): string {
  const left = c.approvals_remaining ?? 0
  if (isAuthorInReview) return 'Waiting for review by another scope reviewer (4-eyes)'
  if (c.corrected_disease)
    return 'You corrected the disease entity, so another reviewer must approve it (4-eyes)'
  if (c.status === 'in_review' && left)
    return `Waiting for ${left} more ${left === 1 ? 'approval' : 'approvals'}`
  return 'No actions available'
}
