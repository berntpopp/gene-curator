import type { ExperimentalEvidence, GeneticEvidence } from './types'

// Full empty shapes: emitted evidence keeps every sub-key, so these must not be trimmed.
export function createEmptyGeneticEvidence(): GeneticEvidence {
  return {
    case_level: {
      autosomal_dominant_or_x_linked: {
        predicted_or_proven_null: [],
        other_variant_type: []
      },
      autosomal_recessive: {
        predicted_or_proven_null: [],
        other_variant_type: []
      }
    },
    segregation: [],
    case_control: {
      single_variant_analysis: [],
      aggregate_variant_analysis: []
    }
  }
}

export function createEmptyExperimentalEvidence(): ExperimentalEvidence {
  return {
    function: {
      biochemical_function: [],
      protein_interaction: [],
      expression: []
    },
    functional_alteration: {
      patient_cells: [],
      non_patient_cells: []
    },
    models: {
      non_human_model_organism: [],
      cell_culture_model: []
    },
    rescue: {
      human: [],
      non_human_model_organism: [],
      cell_culture: [],
      patient_cells: []
    }
  }
}
