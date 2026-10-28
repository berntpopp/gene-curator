import { storedScores, record, rowLabel } from '@/views/curation/curationScores'
import type { ScoreSnapshot } from '@/components/workspace/useWorkspaceFrame'

// Why a row with points scores 0 (backend scoring/evidence_items.uncited); `refused`: submit
// refuses it (services/review_guards._UNCITED), not_scored is the curator's own choice
const REASONS: Record<string, [string, boolean]> = {
  no_pmid: ['needs a PMID', true],
  no_variant: ['needs a variant', true],
  placeholder_variant: [
    'needs a real variant (HGVS c./p./g., an rsID or a genomic coordinate)',
    true
  ],
  missing_status: ['needs a score status: score, review or contradicts', true],
  not_scored: ['not scored (status review or contradicts)', false]
}

export function scoreSnapshot(
  value: unknown,
  hasContradictory: boolean,
  evidence?: unknown
): ScoreSnapshot | null {
  const calc = record(value)
  if (typeof calc?.verdict !== 'string' || !calc.verdict) return null
  const excluded = (Array.isArray(calc.excluded) ? calc.excluded : []).map(e => {
    const { path, reason } = (record(e) ?? {}) as { path?: unknown; reason?: unknown }
    const [why, refused] = REASONS[String(reason)] ?? [String(reason).replaceAll('_', ' '), false]
    return { text: `${rowLabel(String(path), evidence)} scores 0: ${why}`, refused }
  })
  return { ...storedScores(calc), classification: calc.verdict, hasContradictory, excluded }
}
