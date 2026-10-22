import { storedScores, record } from '@/views/curation/curationScores'
import type { ScoreSnapshot } from '@/components/workspace/useWorkspaceFrame'

export function scoreSnapshot(value: unknown, hasContradictory: boolean): ScoreSnapshot | null {
  const calc = record(value)
  if (typeof calc?.verdict !== 'string' || !calc.verdict) return null
  return { ...storedScores(calc), classification: calc.verdict, hasContradictory }
}
