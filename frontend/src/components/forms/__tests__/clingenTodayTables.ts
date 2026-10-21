/**
 * The ClinGen evidence tables as the hand-written form (components/clingen/**, deleted) showed
 * them: columns and the values a new row started with. Captured before the deletion; the
 * config-driven tables must keep them (#267).
 */
export interface TodayColumn {
  key: string
  label: string
  type: 'text' | 'pmid' | 'select' | 'number'
  options?: string[]
  min?: number
  max?: number
}

export const TODAY_TABLES: Record<
  string,
  { columns: TodayColumn[]; newRow: Record<string, unknown> }
> = {
  'genetic_evidence.case_level.autosomal_dominant_or_x_linked.predicted_or_proven_null': {
    columns: [
      { key: 'proband_label', label: 'Proband', type: 'text' },
      {
        key: 'variant_type',
        label: 'Type',
        type: 'select',
        options: [
          'nonsense',
          'frameshift',
          'canonical_splice',
          'initiation_codon',
          'single_exon_deletion',
          'multi_exon_deletion',
          'whole_gene_deletion'
        ]
      },
      { key: 'variant', label: 'Variant (HGVS)', type: 'text' },
      { key: 'pmid', label: 'PMID', type: 'pmid' },
      {
        key: 'score_status',
        label: 'Status',
        type: 'select',
        options: ['score', 'review', 'contradicts']
      },
      { key: 'proband_counted_points', label: 'Points', type: 'number', min: 0, max: 3 },
      { key: 'explanation', label: 'Explanation', type: 'text' }
    ],
    newRow: {
      proband_label: '',
      variant_type: 'nonsense',
      variant: '',
      pmid: '',
      score_status: 'score',
      proband_counted_points: 1.5,
      explanation: ''
    }
  },
  'genetic_evidence.case_level.autosomal_dominant_or_x_linked.other_variant_type': {
    columns: [
      { key: 'proband_label', label: 'Proband', type: 'text' },
      {
        key: 'variant_type',
        label: 'Type',
        type: 'select',
        options: [
          'missense',
          'in_frame_indel',
          'cryptic_splice',
          'synonymous',
          '5_utr',
          '3_utr',
          'intronic',
          'other'
        ]
      },
      { key: 'variant', label: 'Variant (HGVS)', type: 'text' },
      { key: 'pmid', label: 'PMID', type: 'pmid' },
      {
        key: 'score_status',
        label: 'Status',
        type: 'select',
        options: ['score', 'review', 'contradicts']
      },
      { key: 'proband_counted_points', label: 'Points', type: 'number', min: 0, max: 1.5 },
      { key: 'explanation', label: 'Explanation', type: 'text' }
    ],
    newRow: {
      proband_label: '',
      variant_type: 'missense',
      variant: '',
      pmid: '',
      score_status: 'score',
      proband_counted_points: 0.1,
      explanation: ''
    }
  },
  'genetic_evidence.case_level.autosomal_recessive.predicted_or_proven_null': {
    columns: [
      { key: 'proband_label', label: 'Proband', type: 'text' },
      {
        key: 'variant_type',
        label: 'Type',
        type: 'select',
        options: ['two_null', 'null_and_null']
      },
      { key: 'variant_1', label: 'Variant 1', type: 'text' },
      { key: 'variant_2', label: 'Variant 2', type: 'text' },
      { key: 'pmid', label: 'PMID', type: 'pmid' },
      {
        key: 'score_status',
        label: 'Status',
        type: 'select',
        options: ['score', 'review', 'contradicts']
      },
      { key: 'proband_counted_points', label: 'Points', type: 'number', min: 0, max: 3 },
      { key: 'explanation', label: 'Explanation', type: 'text' }
    ],
    newRow: {
      proband_label: '',
      variant_type: 'two_null',
      variant_1: '',
      variant_2: '',
      pmid: '',
      score_status: 'score',
      proband_counted_points: 1.5,
      explanation: ''
    }
  },
  'genetic_evidence.case_level.autosomal_recessive.other_variant_type': {
    columns: [
      { key: 'proband_label', label: 'Proband', type: 'text' },
      {
        key: 'variant_type',
        label: 'Type',
        type: 'select',
        options: ['null_and_other', 'two_other', 'homozygous_other']
      },
      { key: 'variant_1', label: 'Variant 1', type: 'text' },
      { key: 'variant_2', label: 'Variant 2', type: 'text' },
      { key: 'pmid', label: 'PMID', type: 'pmid' },
      {
        key: 'score_status',
        label: 'Status',
        type: 'select',
        options: ['score', 'review', 'contradicts']
      },
      // SOP v11: an AR proband scores up to 3 (#420); the old form capped at 1.5
      { key: 'proband_counted_points', label: 'Points', type: 'number', min: 0, max: 3 },
      { key: 'explanation', label: 'Explanation', type: 'text' }
    ],
    newRow: {
      proband_label: '',
      variant_type: 'null_and_other',
      variant_1: '',
      variant_2: '',
      pmid: '',
      score_status: 'score',
      proband_counted_points: 0.1,
      explanation: ''
    }
  },
  'genetic_evidence.segregation': {
    columns: [
      { key: 'family_label', label: 'Family', type: 'text' },
      { key: 'pmid', label: 'PMID', type: 'pmid' },
      { key: 'lod_score', label: 'LOD Score', type: 'number', min: 0 },
      { key: 'segregations_counted', label: 'Seg. Counted', type: 'number', min: 0 },
      { key: 'points', label: 'Points', type: 'number', min: 0, max: 3 },
      { key: 'explanation', label: 'Explanation', type: 'text' }
    ],
    newRow: {
      family_label: '',
      pmid: '',
      lod_score: 0,
      segregations_counted: 0,
      points: 0,
      explanation: ''
    }
  },
  'genetic_evidence.case_control.single_variant_analysis': {
    columns: [
      { key: 'study_label', label: 'Study', type: 'text' },
      { key: 'pmid', label: 'PMID', type: 'pmid' },
      { key: 'variant', label: 'Variant', type: 'text' },
      { key: 'cases_with_variant', label: 'Cases+', type: 'number', min: 0 },
      { key: 'cases_total', label: 'Cases', type: 'number', min: 1 },
      { key: 'controls_with_variant', label: 'Ctrl+', type: 'number', min: 0 },
      { key: 'controls_total', label: 'Ctrl', type: 'number', min: 1 },
      { key: 'odds_ratio', label: 'OR', type: 'number', min: 0 },
      { key: 'p_value', label: 'P-value', type: 'number', min: 0, max: 1 },
      { key: 'points', label: 'Points', type: 'number', min: 0, max: 6 }
    ],
    newRow: {
      study_label: '',
      pmid: '',
      variant: '',
      cases_with_variant: 0,
      cases_total: 1,
      controls_with_variant: 0,
      controls_total: 1,
      odds_ratio: 0,
      p_value: 1,
      points: 0
    }
  },
  'genetic_evidence.case_control.aggregate_variant_analysis': {
    columns: [
      { key: 'study_label', label: 'Study', type: 'text' },
      { key: 'pmid', label: 'PMID', type: 'pmid' },
      {
        key: 'analysis_type',
        label: 'Analysis',
        type: 'select',
        options: ['burden', 'collapsing', 'skat', 'skat_o', 'other']
      },
      { key: 'cases_with_variants', label: 'Cases+', type: 'number', min: 0 },
      { key: 'cases_total', label: 'Cases', type: 'number', min: 1 },
      { key: 'controls_with_variants', label: 'Ctrl+', type: 'number', min: 0 },
      { key: 'controls_total', label: 'Ctrl', type: 'number', min: 1 },
      { key: 'p_value', label: 'P-value', type: 'number', min: 0, max: 1 },
      { key: 'points', label: 'Points', type: 'number', min: 0, max: 6 }
    ],
    newRow: {
      study_label: '',
      pmid: '',
      analysis_type: 'burden',
      cases_with_variants: 0,
      cases_total: 1,
      controls_with_variants: 0,
      controls_total: 1,
      p_value: 1,
      points: 0
    }
  },
  'experimental_evidence.function.biochemical_function': {
    columns: [
      { key: 'label', label: 'Label', type: 'text' },
      { key: 'pmid', label: 'PMID', type: 'pmid' },
      { key: 'gene_function_description', label: 'Function Description', type: 'text' },
      { key: 'disease_mechanism_relevance', label: 'Disease Relevance', type: 'text' },
      { key: 'score_status', label: 'Status', type: 'select', options: ['score', 'review'] },
      { key: 'points', label: 'Points', type: 'number', min: 0, max: 2 },
      { key: 'explanation', label: 'Explanation', type: 'text' }
    ],
    newRow: {
      label: '',
      pmid: '',
      gene_function_description: '',
      disease_mechanism_relevance: '',
      score_status: 'score',
      points: 0.5,
      explanation: ''
    }
  },
  'experimental_evidence.function.protein_interaction': {
    columns: [
      { key: 'label', label: 'Label', type: 'text' },
      { key: 'pmid', label: 'PMID', type: 'pmid' },
      { key: 'interacting_protein', label: 'Interacting Protein', type: 'text' },
      { key: 'interaction_method', label: 'Method', type: 'text' },
      { key: 'disease_relevance', label: 'Disease Relevance', type: 'text' },
      { key: 'score_status', label: 'Status', type: 'select', options: ['score', 'review'] },
      { key: 'points', label: 'Points', type: 'number', min: 0, max: 2 }
    ],
    newRow: {
      label: '',
      pmid: '',
      interacting_protein: '',
      interaction_method: '',
      disease_relevance: '',
      score_status: 'score',
      points: 0.5
    }
  },
  'experimental_evidence.function.expression': {
    columns: [
      { key: 'label', label: 'Label', type: 'text' },
      { key: 'pmid', label: 'PMID', type: 'pmid' },
      { key: 'tissue_organ', label: 'Tissue/Organ', type: 'text' },
      { key: 'expression_method', label: 'Method', type: 'text' },
      { key: 'disease_tissue_relevance', label: 'Relevance', type: 'text' },
      { key: 'score_status', label: 'Status', type: 'select', options: ['score', 'review'] },
      { key: 'points', label: 'Points', type: 'number', min: 0, max: 2 }
    ],
    newRow: {
      label: '',
      pmid: '',
      tissue_organ: '',
      expression_method: '',
      disease_tissue_relevance: '',
      score_status: 'score',
      points: 0.5
    }
  },
  'experimental_evidence.functional_alteration.patient_cells': {
    columns: [
      { key: 'label', label: 'Label', type: 'text' },
      { key: 'pmid', label: 'PMID', type: 'pmid' },
      { key: 'cell_type', label: 'Cell Type', type: 'text' },
      { key: 'variant_tested', label: 'Variant', type: 'text' },
      { key: 'functional_effect', label: 'Effect', type: 'text' },
      { key: 'assay_method', label: 'Assay', type: 'text' },
      { key: 'score_status', label: 'Status', type: 'select', options: ['score', 'review'] },
      { key: 'points', label: 'Points', type: 'number', min: 0, max: 2 }
    ],
    newRow: {
      label: '',
      pmid: '',
      cell_type: '',
      variant_tested: '',
      functional_effect: '',
      assay_method: '',
      score_status: 'score',
      points: 1
    }
  },
  'experimental_evidence.functional_alteration.non_patient_cells': {
    columns: [
      { key: 'label', label: 'Label', type: 'text' },
      { key: 'pmid', label: 'PMID', type: 'pmid' },
      { key: 'cell_line', label: 'Cell Line', type: 'text' },
      { key: 'variant_engineered', label: 'Variant', type: 'text' },
      { key: 'functional_effect', label: 'Effect', type: 'text' },
      { key: 'assay_method', label: 'Assay', type: 'text' },
      { key: 'score_status', label: 'Status', type: 'select', options: ['score', 'review'] },
      { key: 'points', label: 'Points', type: 'number', min: 0, max: 1 }
    ],
    newRow: {
      label: '',
      pmid: '',
      cell_line: '',
      variant_engineered: '',
      functional_effect: '',
      assay_method: '',
      score_status: 'score',
      points: 0.5
    }
  },
  'experimental_evidence.models.non_human_model_organism': {
    columns: [
      { key: 'label', label: 'Label', type: 'text' },
      { key: 'pmid', label: 'PMID', type: 'pmid' },
      {
        key: 'organism',
        label: 'Organism',
        type: 'select',
        options: [
          'mouse',
          'rat',
          'zebrafish',
          'drosophila',
          'c_elegans',
          'xenopus',
          'yeast',
          'other'
        ]
      },
      {
        key: 'model_type',
        label: 'Type',
        type: 'select',
        options: ['knockout', 'knockin', 'transgenic', 'morpholino', 'crispr', 'other']
      },
      { key: 'phenotype_observed', label: 'Phenotype', type: 'text' },
      { key: 'human_phenotype_match', label: 'Human Match', type: 'text' },
      { key: 'score_status', label: 'Status', type: 'select', options: ['score', 'review'] },
      { key: 'points', label: 'Points', type: 'number', min: 0, max: 4 }
    ],
    newRow: {
      label: '',
      pmid: '',
      organism: 'mouse',
      model_type: 'knockout',
      phenotype_observed: '',
      human_phenotype_match: '',
      score_status: 'score',
      points: 2
    }
  },
  'experimental_evidence.models.cell_culture_model': {
    columns: [
      { key: 'label', label: 'Label', type: 'text' },
      { key: 'pmid', label: 'PMID', type: 'pmid' },
      {
        key: 'cell_type',
        label: 'Cell Type',
        type: 'select',
        options: ['ipsc', 'organoid', 'primary', 'cell_line', 'other']
      },
      { key: 'modification', label: 'Modification', type: 'text' },
      { key: 'phenotype_observed', label: 'Phenotype', type: 'text' },
      { key: 'score_status', label: 'Status', type: 'select', options: ['score', 'review'] },
      { key: 'points', label: 'Points', type: 'number', min: 0, max: 2 }
    ],
    newRow: {
      label: '',
      pmid: '',
      cell_type: 'ipsc',
      modification: '',
      phenotype_observed: '',
      score_status: 'score',
      points: 1
    }
  },
  'experimental_evidence.rescue.human': {
    columns: [
      { key: 'label', label: 'Label', type: 'text' },
      { key: 'pmid', label: 'PMID', type: 'pmid' },
      { key: 'rescue_method', label: 'Method', type: 'text' },
      { key: 'phenotype_rescued', label: 'Phenotype Rescued', type: 'text' },
      { key: 'rescue_extent', label: 'Rescue Extent', type: 'text' },
      { key: 'score_status', label: 'Status', type: 'select', options: ['score', 'review'] },
      { key: 'points', label: 'Points', type: 'number', min: 0, max: 4 }
    ],
    newRow: {
      label: '',
      pmid: '',
      rescue_method: '',
      phenotype_rescued: '',
      rescue_extent: '',
      score_status: 'score',
      points: 2
    }
  },
  'experimental_evidence.rescue.non_human_model_organism': {
    columns: [
      { key: 'label', label: 'Label', type: 'text' },
      { key: 'pmid', label: 'PMID', type: 'pmid' },
      { key: 'organism', label: 'Organism', type: 'text' },
      { key: 'rescue_method', label: 'Method', type: 'text' },
      { key: 'phenotype_rescued', label: 'Phenotype Rescued', type: 'text' },
      { key: 'score_status', label: 'Status', type: 'select', options: ['score', 'review'] },
      { key: 'points', label: 'Points', type: 'number', min: 0, max: 4 }
    ],
    newRow: {
      label: '',
      pmid: '',
      organism: '',
      rescue_method: '',
      phenotype_rescued: '',
      score_status: 'score',
      points: 2
    }
  },
  'experimental_evidence.rescue.cell_culture': {
    columns: [
      { key: 'label', label: 'Label', type: 'text' },
      { key: 'pmid', label: 'PMID', type: 'pmid' },
      { key: 'cell_type', label: 'Cell Type', type: 'text' },
      { key: 'rescue_method', label: 'Method', type: 'text' },
      { key: 'phenotype_rescued', label: 'Phenotype Rescued', type: 'text' },
      { key: 'score_status', label: 'Status', type: 'select', options: ['score', 'review'] },
      { key: 'points', label: 'Points', type: 'number', min: 0, max: 2 }
    ],
    newRow: {
      label: '',
      pmid: '',
      cell_type: '',
      rescue_method: '',
      phenotype_rescued: '',
      score_status: 'score',
      points: 1
    }
  },
  'experimental_evidence.rescue.patient_cells': {
    columns: [
      { key: 'label', label: 'Label', type: 'text' },
      { key: 'pmid', label: 'PMID', type: 'pmid' },
      { key: 'cell_type', label: 'Cell Type', type: 'text' },
      { key: 'rescue_method', label: 'Method', type: 'text' },
      { key: 'phenotype_rescued', label: 'Phenotype Rescued', type: 'text' },
      { key: 'score_status', label: 'Status', type: 'select', options: ['score', 'review'] },
      { key: 'points', label: 'Points', type: 'number', min: 0, max: 2 }
    ],
    newRow: {
      label: '',
      pmid: '',
      cell_type: '',
      rescue_method: '',
      phenotype_rescued: '',
      score_status: 'score',
      points: 1
    }
  },
  contradictory_evidence: {
    columns: [
      { key: 'label', label: 'Label', type: 'text' },
      { key: 'pmid', label: 'PMID', type: 'pmid' },
      {
        key: 'evidence_type',
        label: 'Type',
        type: 'select',
        options: ['population', 'segregation', 'functional', 'phenotype', 'other']
      },
      { key: 'description', label: 'Description', type: 'text' },
      {
        key: 'impact',
        label: 'Impact',
        type: 'select',
        options: ['disputed', 'note', 'requires_review']
      }
    ],
    newRow: { label: '', pmid: '', evidence_type: 'population', description: '', impact: 'note' }
  }
}
