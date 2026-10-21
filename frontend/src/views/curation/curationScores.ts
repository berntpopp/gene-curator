import { asRows, caseControlScore, classifyScore } from '@/components/clingen/scoring'

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

const sum = (items: unknown, key: keyof Points = 'points'): number =>
  (asRows(items) as Points[]).reduce((acc, v) => acc + (v[key] || 0), 0)

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
  const segregation = Math.min(sum(genetic.segregation), 3)
  const caseControlData = genetic.case_control ?? {}
  const caseControl = caseControlScore(
    sum(caseControlData.single_variant_analysis),
    sum(caseControlData.aggregate_variant_analysis)
  )

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
    Math.min(biochemical + proteinInteraction + expression, 2) +
      Math.min(functionalAlteration, 2) +
      Math.min(models, 4) +
      Math.min(rescue, 4),
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
export const classifyScores = (
  total: number,
  _genetic: number,
  hasContradictory = false,
  replicatedOverTime = false
): string => classifyScore(total, hasContradictory, replicatedOverTime)
