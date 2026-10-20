import { describe, it, expect } from 'vitest'
import { ref } from 'vue'
import { useScoring, type ScoredEvidence } from '../useScoring'

const item = (
  evidence_type: string,
  evidence_category: string,
  computed_score: number
): ScoredEvidence => ({ evidence_type, evidence_category, computed_score })

describe('useScoring', () => {
  it('returns zero breakdown and no-evidence classification for empty input', () => {
    const { breakdown, classificationColor, progressPercentage, isSufficientEvidence } = useScoring(
      ref([])
    )

    expect(breakdown.value.total_score).toBe(0)
    expect(breakdown.value.classification).toBe('No Known Disease Relationship')
    expect(classificationColor.value).toBe('error')
    expect(progressPercentage.value).toBe(0)
    expect(isSufficientEvidence.value).toBe(false)
  })

  it('sums genetic categories and caps genetic total at 12', () => {
    const evidence = ref([
      item('genetic', 'case_level', 8),
      item('genetic', 'segregation', 5),
      item('genetic', 'case_control', 4)
    ])
    const { breakdown } = useScoring(evidence)

    expect(breakdown.value.case_level_score).toBe(8)
    expect(breakdown.value.segregation_score).toBe(5)
    expect(breakdown.value.case_control_score).toBe(4)
    expect(breakdown.value.genetic_total).toBe(12)
  })

  it('caps individual category scores at their SOP maxima', () => {
    const evidence = ref([item('genetic', 'segregation', 20), item('experimental', 'models', 9)])
    const { breakdown } = useScoring(evidence)

    expect(breakdown.value.segregation_score).toBe(7)
    expect(breakdown.value.models_score).toBe(4)
  })

  it('caps experimental total at 6 and sums experimental categories', () => {
    const evidence = ref([
      item('experimental', 'expression', 2),
      item('experimental', 'protein_function', 2),
      item('experimental', 'models', 4),
      item('experimental', 'rescue', 2)
    ])
    const { breakdown } = useScoring(evidence)

    expect(breakdown.value.experimental_total).toBe(6)
    expect(breakdown.value.rescue_score).toBe(2)
  })

  it('ignores items with missing or non-matching type and treats null score as zero', () => {
    const evidence = ref<ScoredEvidence[]>([
      { evidence_type: 'other', evidence_category: 'case_level', computed_score: 10 },
      { evidence_type: 'genetic', evidence_category: 'case_level', computed_score: null }
    ])
    const { breakdown } = useScoring(evidence)

    expect(breakdown.value.total_score).toBe(0)
  })

  it.each([
    [12, 'Definitive', 'success'],
    [7, 'Strong', 'info'],
    [2, 'Moderate', 'warning'],
    [0.1, 'Limited', 'grey']
  ])('total %s classifies as %s with colour %s', (score, classification, color) => {
    const evidence = ref([item('genetic', 'case_level', score)])
    const { breakdown, classificationColor, isSufficientEvidence } = useScoring(evidence)

    expect(breakdown.value.classification).toBe(classification)
    expect(classificationColor.value).toBe(color)
    expect(isSufficientEvidence.value).toBe(true)
  })

  it('progress percentage is relative to 12 and capped at 100', () => {
    const { progressPercentage } = useScoring(ref([item('genetic', 'case_level', 6)]))
    expect(progressPercentage.value).toBe(50)

    const full = useScoring(ref([item('genetic', 'case_level', 30)]))
    expect(full.progressPercentage.value).toBe(100)
  })

  it('reacts to changes in the evidence list', () => {
    const evidence = ref<ScoredEvidence[]>([])
    const { breakdown } = useScoring(evidence)

    evidence.value = [item('genetic', 'case_level', 3)]
    expect(breakdown.value.total_score).toBe(3)
  })
})
