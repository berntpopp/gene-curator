/**
 * Pipeline stage of a gene in a scope. Assignments carry no status of their own, so the stage
 * comes from the gene's curator and its latest precuration and curation (one place for the
 * stage strip, the table column, the filter and the detail dialog).
 */
import { CURATION_STATUS } from '@/config/status'

export type GeneStage = 'unassigned' | 'precuration' | 'curation' | 'review' | 'active'

export const GENE_STAGES: { value: GeneStage; title: string; color?: string }[] = [
  { value: 'unassigned', title: 'Unassigned' },
  { value: 'precuration', title: 'Precuration' },
  { value: 'curation', title: 'Curation' },
  { value: 'review', title: 'In review', color: CURATION_STATUS.in_review.color },
  { value: 'active', title: 'Active', color: CURATION_STATUS.active.color }
]

export const stageTitle = (stage: GeneStage): string =>
  GENE_STAGES.find(s => s.value === stage)?.title ?? stage

const IN_REVIEW = ['submitted', 'in_review', 'approved']

export function stageOf(
  hasCurator: boolean,
  precuration?: { status: string } | null,
  curation?: { status: string } | null
): GeneStage {
  if (curation?.status === 'active') return 'active'
  if (curation && IN_REVIEW.includes(curation.status)) return 'review'
  if (curation || precuration?.status === 'approved') return 'curation'
  return precuration || hasCurator ? 'precuration' : 'unassigned'
}
