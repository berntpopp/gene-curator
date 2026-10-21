/**
 * Shared types for the forms and gene components.
 */

/** Minimal shape of an axios-style error as caught in catch blocks. */
export interface ApiErrorLike {
  message?: string
  response?: { status?: number }
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
