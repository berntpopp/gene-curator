// ClinGen SOP v11 score calculation for the curation detail view (pure, no Vue)

interface Points {
  points?: number | null
  proband_counted_points?: number | null
}

interface CaseLevelGroup {
  predicted_or_proven_null?: Points[] | null
  other_variant_type?: Points[] | null
}

/** Shape of curation.evidence_data as used by the score calculation. */
export interface EvidenceData {
  genetic_evidence?: {
    case_level?: {
      autosomal_dominant_or_x_linked?: CaseLevelGroup | null
      autosomal_recessive?: CaseLevelGroup | null
    } | null
    segregation?: Points[] | null
    case_control?: {
      single_variant_analysis?: Points[] | null
      aggregate_variant_analysis?: Points[] | null
    } | null
  } | null
  experimental_evidence?: {
    function?: {
      biochemical_function?: Points[] | null
      protein_interaction?: Points[] | null
      expression?: Points[] | null
    } | null
    functional_alteration?: {
      patient_cells?: Points[] | null
      non_patient_cells?: Points[] | null
    } | null
    models?: {
      non_human_model_organism?: Points[] | null
      cell_culture_model?: Points[] | null
    } | null
    rescue?: {
      human?: Points[] | null
      non_human_model_organism?: Points[] | null
      cell_culture?: Points[] | null
      patient_cells?: Points[] | null
    } | null
  } | null
}

export interface EvidenceScores {
  caseLevel: { adxlNull: number; adxlOther: number; arNull: number; arOther: number }
  segregation: number
  caseControl: number
  genetic: number
  function: { biochemical: number; proteinInteraction: number; expression: number }
  functionalAlteration: number
  models: number
  rescue: number
  experimental: number
  total: number
}

const sum = (items: Points[] | null | undefined, key: keyof Points = 'points'): number =>
  (items ?? []).reduce((acc, v) => acc + (v[key] || 0), 0)

/** Genetic evidence is capped at 12 points, experimental at 6 (SOP v11). */
export function computeScores(evidence: EvidenceData | null | undefined): EvidenceScores {
  const genetic = evidence?.genetic_evidence ?? {}
  const experimental = evidence?.experimental_evidence ?? {}

  const caseLevel = genetic.case_level ?? {}
  const adxl = caseLevel.autosomal_dominant_or_x_linked ?? {}
  const ar = caseLevel.autosomal_recessive ?? {}
  const pc = 'proband_counted_points' as const

  const adxlNull = sum(adxl.predicted_or_proven_null, pc)
  const adxlOther = sum(adxl.other_variant_type, pc)
  const arNull = sum(ar.predicted_or_proven_null, pc)
  const arOther = sum(ar.other_variant_type, pc)
  const segregation = sum(genetic.segregation)
  const caseControlData = genetic.case_control ?? {}
  const caseControl =
    sum(caseControlData.single_variant_analysis) + sum(caseControlData.aggregate_variant_analysis)

  const geneticTotal = Math.min(
    adxlNull + adxlOther + arNull + arOther + segregation + caseControl,
    12
  )

  const func = experimental.function ?? {}
  const biochemical = sum(func.biochemical_function)
  const proteinInteraction = sum(func.protein_interaction)
  const expression = sum(func.expression)

  const functionalAltData = experimental.functional_alteration ?? {}
  const functionalAlteration =
    sum(functionalAltData.patient_cells) + sum(functionalAltData.non_patient_cells)

  const modelsData = experimental.models ?? {}
  const models = sum(modelsData.non_human_model_organism) + sum(modelsData.cell_culture_model)

  const rescueData = experimental.rescue ?? {}
  const rescue =
    sum(rescueData.human) +
    sum(rescueData.non_human_model_organism) +
    sum(rescueData.cell_culture) +
    sum(rescueData.patient_cells)

  const experimentalTotal = Math.min(
    biochemical + proteinInteraction + expression + functionalAlteration + models + rescue,
    6
  )

  return {
    caseLevel: { adxlNull, adxlOther, arNull, arOther },
    segregation,
    caseControl,
    genetic: geneticTotal,
    function: { biochemical, proteinInteraction, expression },
    functionalAlteration,
    models,
    rescue,
    experimental: experimentalTotal,
    total: geneticTotal + experimentalTotal
  }
}

/** Classification thresholds from the SOP v11 score table. */
export function classifyScores(total: number, genetic: number): string {
  if (total >= 12 && genetic >= 6) return 'Definitive'
  if (total >= 12 && genetic >= 4.5) return 'Strong'
  if (total >= 9 && genetic >= 3) return 'Moderate'
  if (total >= 1) return 'Limited'
  return 'No Known Disease Relationship'
}
