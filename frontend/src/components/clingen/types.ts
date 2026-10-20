/** One ClinGen SOP v11 evidence row. Scoring fields are read loosely, so the rest stays free-form. */
export interface EvidenceItem {
  points?: number | string | null
  proband_counted_points?: number | string | null
  [field: string]: unknown
}

export interface CaseLevelGroup {
  predicted_or_proven_null?: EvidenceItem[]
  other_variant_type?: EvidenceItem[]
}

export interface GeneticEvidence {
  case_level?: {
    autosomal_dominant_or_x_linked?: CaseLevelGroup
    autosomal_recessive?: CaseLevelGroup
  }
  segregation?: EvidenceItem[]
  case_control?: {
    single_variant_analysis?: EvidenceItem[]
    aggregate_variant_analysis?: EvidenceItem[]
  }
}

export interface ExperimentalEvidence {
  function?: {
    biochemical_function?: EvidenceItem[]
    protein_interaction?: EvidenceItem[]
    expression?: EvidenceItem[]
  }
  functional_alteration?: {
    patient_cells?: EvidenceItem[]
    non_patient_cells?: EvidenceItem[]
  }
  models?: {
    non_human_model_organism?: EvidenceItem[]
    cell_culture_model?: EvidenceItem[]
  }
  rescue?: {
    human?: EvidenceItem[]
    non_human_model_organism?: EvidenceItem[]
    cell_culture?: EvidenceItem[]
    patient_cells?: EvidenceItem[]
  }
}

export interface ClinGenEvidenceData {
  evidence_summary: string
  genetic_evidence: GeneticEvidence
  experimental_evidence: ExperimentalEvidence
  contradictory_evidence: EvidenceItem[]
}

export interface EvidenceColumn {
  key: string
  label: string
  width?: string
  type?: 'pmid' | 'select' | 'number'
  options?: { value: string; label: string }[]
  min?: number
  max?: number
  step?: number
}

/** Scoped logger from useLogger(); its inferred JS return type loses the method signatures. */
export interface ComponentLogger {
  debug(message: string, data?: Record<string, unknown>): void
  info(message: string, data?: Record<string, unknown>): void
  warn(message: string, data?: Record<string, unknown>): void
  error(message: string, data?: Record<string, unknown>): void
}

export interface GeneInfo {
  symbol?: string | null
  approved_symbol?: string | null
  hgnc_id?: string | null
}

export interface DiseaseInfo {
  name?: string | null
  mondo_id?: string | null
}

export interface MimPhenotype {
  mim_number: string
  name?: string | null
  inheritance?: string | null
}

export interface LumpingSplittingData {
  curation_type?: string | null
  rationale?: string[] | null
  evaluation_date?: string | null
  included_mim_phenotypes?: MimPhenotype[] | null
  excluded_mim_phenotypes?: MimPhenotype[] | null
  supporting_pmids?: string[] | string | null
  notes?: string | null
}

/** Approved precuration as passed to the curation form (fields are read from both top level and nested blocks). */
export interface PrecurationData extends LumpingSplittingData {
  id?: string | null
  precuration_id?: string | null
  disease_name?: string | null
  mondo_id?: string | null
  mode_of_inheritance?: string | null
  expert_panel?: string | null
  phenotypes?: string[] | null
  pmids?: string | null
  rationale_notes?: string | null
  entity_definition?: {
    disease_name?: string | null
    mondo_id?: string | null
    mode_of_inheritance?: string | null
    phenotypes?: string[] | null
  }
  lumping_splitting?: LumpingSplittingData
}
