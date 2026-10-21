import type { Schema } from '@/types/api'
import type { ScoreSnapshot } from '@/components/workspace/useWorkspaceFrame'

interface TraceSection {
  key: string
  categories?: { key: string; score: number; types?: { path: string; score: number }[] }[]
}

/**
 * The backend score preview (`GET /curations/{id}/score`, scored with the pinned point model)
 * as the workspace score panel shows it. Category scores come from the trace (after caps).
 */
export function scoreSnapshot(
  preview: Schema<'CurationScoreResponse'>,
  hasContradictory: boolean
): ScoreSnapshot {
  const trace = preview.breakdown?.trace as { sections?: TraceSection[] } | undefined
  const categories = (section: string) =>
    trace?.sections?.find(s => s.key === section)?.categories ?? []
  const cat = (section: string, key: string) =>
    Number(categories(section).find(c => c.key === key)?.score) || 0
  // A category shared by several kinds (SOP v11 "Models & Rescue"): each kind's own points
  const kind = (section: string, prefix: string) =>
    categories(section).find(c => c.key === prefix)
      ? cat(section, prefix)
      : categories(section)
          .flatMap(c => c.types ?? [])
          .filter(t => t.path.startsWith(`${prefix}.`))
          .reduce((sum, t) => sum + (Number(t.score) || 0), 0)
  return {
    genetic: preview.genetic_score,
    experimental: preview.experimental_score,
    total: preview.total_score,
    classification: preview.classification,
    hasContradictory,
    geneticBreakdown: {
      caseLevel: cat('genetic_evidence', 'case_level'),
      segregation: cat('genetic_evidence', 'segregation'),
      caseControl: cat('genetic_evidence', 'case_control')
    },
    experimentalBreakdown: {
      function: cat('experimental_evidence', 'function'),
      functionalAlteration: cat('experimental_evidence', 'functional_alteration'),
      models: kind('experimental_evidence', 'models'),
      rescue: kind('experimental_evidence', 'rescue')
    }
  }
}
