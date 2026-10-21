import { storedScores, type StoredScores } from '@/views/curation/curationScores'
import type { ScoreSnapshot } from '@/components/workspace/useWorkspaceFrame'

/** validate-evidence's score_calculations: the pinned point model's result (nothing stored). */
export interface ScoreCalculations extends StoredScores {
  verdict?: string | null
}

/**
 * The live backend score preview (validate-evidence, run debounced on every edit) as the
 * workspace score panel shows it; null until the backend returned a verdict.
 */
export function scoreSnapshot(
  calc: ScoreCalculations | null | undefined,
  hasContradictory: boolean
): ScoreSnapshot | null {
  if (!calc?.verdict) return null
  const s = storedScores(calc)
  return {
    genetic: s.genetic,
    experimental: s.experimental,
    total: s.total,
    classification: calc.verdict,
    hasContradictory,
    geneticBreakdown: {
      caseLevel: s.caseLevelTotal,
      segregation: s.segregation,
      caseControl: s.caseControl
    },
    experimentalBreakdown: {
      function: s.functionTotal,
      functionalAlteration: s.functionalAlteration,
      models: s.models,
      rescue: s.rescue
    }
  }
}
