import type { EvidenceColumn } from '../types'

// Column definitions for the genetic and experimental evidence tables (ClinGen SOP v11).

export const nullVariantColumns: EvidenceColumn[] = [
  { key: 'proband_label', label: 'Proband', width: '100px' },
  {
    key: 'variant_type',
    label: 'Type',
    width: '140px',
    type: 'select',
    options: [
      { value: 'nonsense', label: 'Nonsense' },
      { value: 'frameshift', label: 'Frameshift' },
      { value: 'canonical_splice', label: 'Splice (+/-1,2)' },
      { value: 'initiation_codon', label: 'Init codon' },
      { value: 'single_exon_deletion', label: 'Single exon del' },
      { value: 'multi_exon_deletion', label: 'Multi-exon del' },
      { value: 'whole_gene_deletion', label: 'Whole gene del' }
    ]
  },
  { key: 'variant', label: 'Variant (HGVS)', width: '160px' },
  { key: 'pmid', label: 'PMID', width: '100px', type: 'pmid' },
  {
    key: 'score_status',
    label: 'Status',
    width: '100px',
    type: 'select',
    options: [
      { value: 'score', label: 'Score' },
      { value: 'review', label: 'Review' },
      { value: 'contradicts', label: 'Contradicts' }
    ]
  },
  {
    key: 'proband_counted_points',
    label: 'Points',
    width: '80px',
    type: 'number',
    min: 0,
    max: 3,
    step: 0.1
  },
  { key: 'explanation', label: 'Explanation', width: '200px' }
]

export const otherVariantColumns: EvidenceColumn[] = [
  { key: 'proband_label', label: 'Proband', width: '100px' },
  {
    key: 'variant_type',
    label: 'Type',
    width: '140px',
    type: 'select',
    options: [
      { value: 'missense', label: 'Missense' },
      { value: 'in_frame_indel', label: 'In-frame indel' },
      { value: 'cryptic_splice', label: 'Cryptic splice' },
      { value: 'synonymous', label: 'Synonymous' },
      { value: '5_utr', label: "5' UTR" },
      { value: '3_utr', label: "3' UTR" },
      { value: 'intronic', label: 'Intronic' },
      { value: 'other', label: 'Other' }
    ]
  },
  { key: 'variant', label: 'Variant (HGVS)', width: '160px' },
  { key: 'pmid', label: 'PMID', width: '100px', type: 'pmid' },
  {
    key: 'score_status',
    label: 'Status',
    width: '100px',
    type: 'select',
    options: [
      { value: 'score', label: 'Score' },
      { value: 'review', label: 'Review' },
      { value: 'contradicts', label: 'Contradicts' }
    ]
  },
  {
    key: 'proband_counted_points',
    label: 'Points',
    width: '80px',
    type: 'number',
    min: 0,
    max: 1.5,
    step: 0.1
  },
  { key: 'explanation', label: 'Explanation', width: '200px' }
]

export const arNullVariantColumns: EvidenceColumn[] = [
  { key: 'proband_label', label: 'Proband', width: '100px' },
  {
    key: 'variant_type',
    label: 'Type',
    width: '140px',
    type: 'select',
    options: [
      { value: 'two_null', label: 'Two null variants' },
      { value: 'null_and_null', label: 'Homozygous null' }
    ]
  },
  { key: 'variant_1', label: 'Variant 1', width: '140px' },
  { key: 'variant_2', label: 'Variant 2', width: '140px' },
  { key: 'pmid', label: 'PMID', width: '100px', type: 'pmid' },
  {
    key: 'score_status',
    label: 'Status',
    width: '100px',
    type: 'select',
    options: [
      { value: 'score', label: 'Score' },
      { value: 'review', label: 'Review' },
      { value: 'contradicts', label: 'Contradicts' }
    ]
  },
  {
    key: 'proband_counted_points',
    label: 'Points',
    width: '80px',
    type: 'number',
    min: 0,
    max: 3,
    step: 0.1
  },
  { key: 'explanation', label: 'Explanation', width: '180px' }
]

export const arOtherVariantColumns: EvidenceColumn[] = [
  { key: 'proband_label', label: 'Proband', width: '100px' },
  {
    key: 'variant_type',
    label: 'Type',
    width: '150px',
    type: 'select',
    options: [
      { value: 'null_and_other', label: 'Null + Other' },
      { value: 'two_other', label: 'Two other variants' },
      { value: 'homozygous_other', label: 'Homozygous other' }
    ]
  },
  { key: 'variant_1', label: 'Variant 1', width: '140px' },
  { key: 'variant_2', label: 'Variant 2', width: '140px' },
  { key: 'pmid', label: 'PMID', width: '100px', type: 'pmid' },
  {
    key: 'score_status',
    label: 'Status',
    width: '100px',
    type: 'select',
    options: [
      { value: 'score', label: 'Score' },
      { value: 'review', label: 'Review' },
      { value: 'contradicts', label: 'Contradicts' }
    ]
  },
  {
    key: 'proband_counted_points',
    label: 'Points',
    width: '80px',
    type: 'number',
    min: 0,
    max: 1.5,
    step: 0.1
  },
  { key: 'explanation', label: 'Explanation', width: '180px' }
]

export const segregationColumns: EvidenceColumn[] = [
  { key: 'family_label', label: 'Family', width: '100px' },
  { key: 'pmid', label: 'PMID', width: '100px', type: 'pmid' },
  { key: 'lod_score', label: 'LOD Score', width: '100px', type: 'number', min: 0, step: 0.1 },
  { key: 'segregations_counted', label: 'Seg. Counted', width: '100px', type: 'number', min: 0 },
  { key: 'points', label: 'Points', width: '80px', type: 'number', min: 0, max: 3, step: 0.1 },
  { key: 'explanation', label: 'Explanation', width: '200px' }
]

export const caseControlColumns: EvidenceColumn[] = [
  { key: 'study_label', label: 'Study', width: '100px' },
  { key: 'pmid', label: 'PMID', width: '100px', type: 'pmid' },
  { key: 'variant', label: 'Variant', width: '140px' },
  { key: 'cases_with_variant', label: 'Cases+', width: '80px', type: 'number', min: 0 },
  { key: 'cases_total', label: 'Cases', width: '80px', type: 'number', min: 1 },
  { key: 'controls_with_variant', label: 'Ctrl+', width: '80px', type: 'number', min: 0 },
  { key: 'controls_total', label: 'Ctrl', width: '80px', type: 'number', min: 1 },
  { key: 'odds_ratio', label: 'OR', width: '80px', type: 'number', min: 0 },
  { key: 'p_value', label: 'P-value', width: '100px', type: 'number', min: 0, max: 1 },
  { key: 'points', label: 'Points', width: '80px', type: 'number', min: 0, max: 6, step: 0.5 }
]

export const aggregateColumns: EvidenceColumn[] = [
  { key: 'study_label', label: 'Study', width: '100px' },
  { key: 'pmid', label: 'PMID', width: '100px', type: 'pmid' },
  {
    key: 'analysis_type',
    label: 'Analysis',
    width: '120px',
    type: 'select',
    options: [
      { value: 'burden', label: 'Burden test' },
      { value: 'collapsing', label: 'Collapsing' },
      { value: 'skat', label: 'SKAT' },
      { value: 'skat_o', label: 'SKAT-O' },
      { value: 'other', label: 'Other' }
    ]
  },
  { key: 'cases_with_variants', label: 'Cases+', width: '80px', type: 'number', min: 0 },
  { key: 'cases_total', label: 'Cases', width: '80px', type: 'number', min: 1 },
  { key: 'controls_with_variants', label: 'Ctrl+', width: '80px', type: 'number', min: 0 },
  { key: 'controls_total', label: 'Ctrl', width: '80px', type: 'number', min: 1 },
  { key: 'p_value', label: 'P-value', width: '100px', type: 'number', min: 0, max: 1 },
  { key: 'points', label: 'Points', width: '80px', type: 'number', min: 0, max: 6, step: 0.5 }
]

export const functionColumns: EvidenceColumn[] = [
  { key: 'label', label: 'Label', width: '100px' },
  { key: 'pmid', label: 'PMID', width: '100px', type: 'pmid' },
  { key: 'gene_function_description', label: 'Function Description', width: '200px' },
  { key: 'disease_mechanism_relevance', label: 'Disease Relevance', width: '200px' },
  {
    key: 'score_status',
    label: 'Status',
    width: '100px',
    type: 'select',
    options: [
      { value: 'score', label: 'Score' },
      { value: 'review', label: 'Review' }
    ]
  },
  { key: 'points', label: 'Points', width: '80px', type: 'number', min: 0, max: 2, step: 0.5 },
  { key: 'explanation', label: 'Explanation', width: '180px' }
]

export const proteinColumns: EvidenceColumn[] = [
  { key: 'label', label: 'Label', width: '100px' },
  { key: 'pmid', label: 'PMID', width: '100px', type: 'pmid' },
  { key: 'interacting_protein', label: 'Interacting Protein', width: '150px' },
  { key: 'interaction_method', label: 'Method', width: '150px' },
  { key: 'disease_relevance', label: 'Disease Relevance', width: '180px' },
  {
    key: 'score_status',
    label: 'Status',
    width: '100px',
    type: 'select',
    options: [
      { value: 'score', label: 'Score' },
      { value: 'review', label: 'Review' }
    ]
  },
  { key: 'points', label: 'Points', width: '80px', type: 'number', min: 0, max: 2, step: 0.5 }
]

export const expressionColumns: EvidenceColumn[] = [
  { key: 'label', label: 'Label', width: '100px' },
  { key: 'pmid', label: 'PMID', width: '100px', type: 'pmid' },
  { key: 'tissue_organ', label: 'Tissue/Organ', width: '140px' },
  { key: 'expression_method', label: 'Method', width: '140px' },
  { key: 'disease_tissue_relevance', label: 'Relevance', width: '180px' },
  {
    key: 'score_status',
    label: 'Status',
    width: '100px',
    type: 'select',
    options: [
      { value: 'score', label: 'Score' },
      { value: 'review', label: 'Review' }
    ]
  },
  { key: 'points', label: 'Points', width: '80px', type: 'number', min: 0, max: 2, step: 0.5 }
]

export const patientCellsColumns: EvidenceColumn[] = [
  { key: 'label', label: 'Label', width: '100px' },
  { key: 'pmid', label: 'PMID', width: '100px', type: 'pmid' },
  { key: 'cell_type', label: 'Cell Type', width: '120px' },
  { key: 'variant_tested', label: 'Variant', width: '140px' },
  { key: 'functional_effect', label: 'Effect', width: '160px' },
  { key: 'assay_method', label: 'Assay', width: '140px' },
  {
    key: 'score_status',
    label: 'Status',
    width: '100px',
    type: 'select',
    options: [
      { value: 'score', label: 'Score' },
      { value: 'review', label: 'Review' }
    ]
  },
  { key: 'points', label: 'Points', width: '80px', type: 'number', min: 0, max: 2, step: 0.5 }
]

export const nonPatientCellsColumns: EvidenceColumn[] = [
  { key: 'label', label: 'Label', width: '100px' },
  { key: 'pmid', label: 'PMID', width: '100px', type: 'pmid' },
  { key: 'cell_line', label: 'Cell Line', width: '120px' },
  { key: 'variant_engineered', label: 'Variant', width: '140px' },
  { key: 'functional_effect', label: 'Effect', width: '160px' },
  { key: 'assay_method', label: 'Assay', width: '140px' },
  {
    key: 'score_status',
    label: 'Status',
    width: '100px',
    type: 'select',
    options: [
      { value: 'score', label: 'Score' },
      { value: 'review', label: 'Review' }
    ]
  },
  { key: 'points', label: 'Points', width: '80px', type: 'number', min: 0, max: 1, step: 0.5 }
]

export const organismColumns: EvidenceColumn[] = [
  { key: 'label', label: 'Label', width: '100px' },
  { key: 'pmid', label: 'PMID', width: '100px', type: 'pmid' },
  {
    key: 'organism',
    label: 'Organism',
    width: '120px',
    type: 'select',
    options: [
      { value: 'mouse', label: 'Mouse' },
      { value: 'rat', label: 'Rat' },
      { value: 'zebrafish', label: 'Zebrafish' },
      { value: 'drosophila', label: 'Drosophila' },
      { value: 'c_elegans', label: 'C. elegans' },
      { value: 'xenopus', label: 'Xenopus' },
      { value: 'yeast', label: 'Yeast' },
      { value: 'other', label: 'Other' }
    ]
  },
  {
    key: 'model_type',
    label: 'Type',
    width: '120px',
    type: 'select',
    options: [
      { value: 'knockout', label: 'Knockout' },
      { value: 'knockin', label: 'Knockin' },
      { value: 'transgenic', label: 'Transgenic' },
      { value: 'morpholino', label: 'Morpholino' },
      { value: 'crispr', label: 'CRISPR' },
      { value: 'other', label: 'Other' }
    ]
  },
  { key: 'phenotype_observed', label: 'Phenotype', width: '180px' },
  { key: 'human_phenotype_match', label: 'Human Match', width: '160px' },
  {
    key: 'score_status',
    label: 'Status',
    width: '100px',
    type: 'select',
    options: [
      { value: 'score', label: 'Score' },
      { value: 'review', label: 'Review' }
    ]
  },
  { key: 'points', label: 'Points', width: '80px', type: 'number', min: 0, max: 4, step: 0.5 }
]

export const cellCultureColumns: EvidenceColumn[] = [
  { key: 'label', label: 'Label', width: '100px' },
  { key: 'pmid', label: 'PMID', width: '100px', type: 'pmid' },
  {
    key: 'cell_type',
    label: 'Cell Type',
    width: '120px',
    type: 'select',
    options: [
      { value: 'ipsc', label: 'iPSC-derived' },
      { value: 'organoid', label: 'Organoid' },
      { value: 'primary', label: 'Primary cells' },
      { value: 'cell_line', label: 'Cell line' },
      { value: 'other', label: 'Other' }
    ]
  },
  { key: 'modification', label: 'Modification', width: '140px' },
  { key: 'phenotype_observed', label: 'Phenotype', width: '180px' },
  {
    key: 'score_status',
    label: 'Status',
    width: '100px',
    type: 'select',
    options: [
      { value: 'score', label: 'Score' },
      { value: 'review', label: 'Review' }
    ]
  },
  { key: 'points', label: 'Points', width: '80px', type: 'number', min: 0, max: 2, step: 0.5 }
]

export const rescueColumns: EvidenceColumn[] = [
  { key: 'label', label: 'Label', width: '100px' },
  { key: 'pmid', label: 'PMID', width: '100px', type: 'pmid' },
  { key: 'rescue_method', label: 'Method', width: '150px' },
  { key: 'phenotype_rescued', label: 'Phenotype Rescued', width: '180px' },
  { key: 'rescue_extent', label: 'Rescue Extent', width: '140px' },
  {
    key: 'score_status',
    label: 'Status',
    width: '100px',
    type: 'select',
    options: [
      { value: 'score', label: 'Score' },
      { value: 'review', label: 'Review' }
    ]
  },
  { key: 'points', label: 'Points', width: '80px', type: 'number', min: 0, max: 4, step: 0.5 }
]

export const organismRescueColumns: EvidenceColumn[] = [
  { key: 'label', label: 'Label', width: '100px' },
  { key: 'pmid', label: 'PMID', width: '100px', type: 'pmid' },
  { key: 'organism', label: 'Organism', width: '120px' },
  { key: 'rescue_method', label: 'Method', width: '150px' },
  { key: 'phenotype_rescued', label: 'Phenotype Rescued', width: '180px' },
  {
    key: 'score_status',
    label: 'Status',
    width: '100px',
    type: 'select',
    options: [
      { value: 'score', label: 'Score' },
      { value: 'review', label: 'Review' }
    ]
  },
  { key: 'points', label: 'Points', width: '80px', type: 'number', min: 0, max: 4, step: 0.5 }
]

export const cellRescueColumns: EvidenceColumn[] = [
  { key: 'label', label: 'Label', width: '100px' },
  { key: 'pmid', label: 'PMID', width: '100px', type: 'pmid' },
  { key: 'cell_type', label: 'Cell Type', width: '120px' },
  { key: 'rescue_method', label: 'Method', width: '150px' },
  { key: 'phenotype_rescued', label: 'Phenotype Rescued', width: '180px' },
  {
    key: 'score_status',
    label: 'Status',
    width: '100px',
    type: 'select',
    options: [
      { value: 'score', label: 'Score' },
      { value: 'review', label: 'Review' }
    ]
  },
  { key: 'points', label: 'Points', width: '80px', type: 'number', min: 0, max: 2, step: 0.5 }
]

export const patientRescueColumns: EvidenceColumn[] = cellRescueColumns
