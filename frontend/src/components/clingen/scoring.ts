import type { EvidenceItem, ExperimentalEvidence, GeneticEvidence } from './types'

export interface GeneticBreakdown {
  caseLevel: number
  segregation: number
  caseControl: number
  total: number
}

export interface ExperimentalBreakdown {
  function: number
  functionalAlteration: number
  models: number
  rescue: number
  total: number
}

/** Same coercion as the original `parseFloat(item.x) || 0`: parseFloat stringifies its argument. */
function pointsOf(value: unknown): number {
  return parseFloat(String(value)) || 0
}

export function sumPoints(items: EvidenceItem[] | undefined): number {
  if (!Array.isArray(items)) return 0
  return items.reduce((sum, item) => sum + pointsOf(item.points), 0)
}

export function sumProbandPoints(items: EvidenceItem[] | undefined): number {
  if (!Array.isArray(items)) return 0
  return items.reduce((sum, item) => sum + pointsOf(item.proband_counted_points), 0)
}

export function calculateGeneticScore(ge: GeneticEvidence): GeneticBreakdown {
  let caseLevelTotal = 0
  let segregationTotal = 0
  let caseControlTotal = 0

  if (ge.case_level) {
    if (ge.case_level.autosomal_dominant_or_x_linked) {
      const adXl = ge.case_level.autosomal_dominant_or_x_linked
      caseLevelTotal += sumProbandPoints(adXl.predicted_or_proven_null)
      caseLevelTotal += sumProbandPoints(adXl.other_variant_type)
    }
    if (ge.case_level.autosomal_recessive) {
      const ar = ge.case_level.autosomal_recessive
      caseLevelTotal += sumProbandPoints(ar.predicted_or_proven_null)
      caseLevelTotal += sumProbandPoints(ar.other_variant_type)
    }
  }

  if (ge.segregation && Array.isArray(ge.segregation)) {
    segregationTotal = sumPoints(ge.segregation)
  }

  if (ge.case_control) {
    caseControlTotal = caseControlScore(
      sumPoints(ge.case_control.single_variant_analysis),
      sumPoints(ge.case_control.aggregate_variant_analysis)
    )
  }

  return {
    caseLevel: Math.min(caseLevelTotal, 12),
    segregation: Math.min(segregationTotal, 3),
    caseControl: Math.min(caseControlTotal, 6),
    total: Math.min(
      Math.min(caseLevelTotal, 12) + Math.min(segregationTotal, 3) + caseControlTotal,
      12
    )
  }
}

export function calculateExperimentalScore(exp: ExperimentalEvidence): ExperimentalBreakdown {
  let functionTotal = 0
  let functionalAlterationTotal = 0
  let modelsTotal = 0
  let rescueTotal = 0

  if (exp.function) {
    const biochem = sumPoints(exp.function.biochemical_function)
    const protein = sumPoints(exp.function.protein_interaction)
    const expression = sumPoints(exp.function.expression)
    functionTotal = Math.min(biochem + protein + expression, 2)
  }

  if (exp.functional_alteration) {
    const patient = sumPoints(exp.functional_alteration.patient_cells)
    const nonPatient = sumPoints(exp.functional_alteration.non_patient_cells)
    functionalAlterationTotal = Math.min(patient + nonPatient, 2)
  }

  if (exp.models) {
    const organism = sumPoints(exp.models.non_human_model_organism)
    const cellCulture = sumPoints(exp.models.cell_culture_model)
    modelsTotal = Math.min(organism + cellCulture, 4)
  }

  if (exp.rescue) {
    const human = sumPoints(exp.rescue.human)
    const organism = sumPoints(exp.rescue.non_human_model_organism)
    const cellCulture = sumPoints(exp.rescue.cell_culture)
    const patientCells = sumPoints(exp.rescue.patient_cells)
    rescueTotal = Math.min(human + organism + cellCulture + patientCells, 4)
  }

  return {
    function: functionTotal,
    functionalAlteration: functionalAlterationTotal,
    models: modelsTotal,
    rescue: rescueTotal,
    total: Math.min(functionTotal + functionalAlterationTotal + modelsTotal + rescueTotal, 6)
  }
}

/** Classification from the total score; contradictory evidence overrides to "Disputed". */
export function classifyScore(total: number, hasContradictory: boolean): string {
  if (hasContradictory) return 'Disputed'
  // Definitive also requires expert assessment of replication over time.
  if (total >= 12) return 'Strong'
  if (total >= 7) return 'Moderate'
  if (total >= 0.1) return 'Limited'
  return 'No Known Disease Relationship'
}

/** Use the stronger case-control method, capped at six points. */
export function caseControlScore(single: number, aggregate: number): number {
  return Math.min(Math.max(single, aggregate), 6)
}
