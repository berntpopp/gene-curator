/** `field_definitions` of the seeded ClinGen precuration schema (016_seed_precuration_schema.sql) */
export const precurationSeed = {
  field_definitions: {
    sections: [
      {
        id: 'disease_entity',
        label: 'Disease Entity Definition',
        description: 'Establish the gene-disease pair to be curated',
        fields: [
          {
            id: 'mondo_id',
            label: 'Mondo Disease ID',
            type: 'external_reference',
            required: true,
            external_source: 'mondo',
            placeholder: 'MONDO:0000001',
            help_text: 'Search for disease using Mondo Disease Ontology'
          },
          {
            id: 'disease_name',
            label: 'Disease Name',
            type: 'text',
            required: true,
            help_text:
              'Use dyadic naming: Gene-associated phenotype (e.g., SCN1A-related seizure disorder)'
          },
          {
            id: 'disease_phenotypes',
            label: 'Key Phenotypes',
            type: 'array',
            item_type: 'external_reference',
            external_source: 'hpo',
            required: false,
            help_text: 'Add relevant HPO terms describing the phenotype'
          }
        ]
      },
      {
        id: 'inheritance',
        label: 'Mode of Inheritance',
        description: 'Specify the inheritance pattern for this gene-disease pair',
        fields: [
          {
            id: 'mode_of_inheritance',
            label: 'Mode of Inheritance',
            type: 'select',
            required: true,
            options: [
              { value: 'AD', label: 'Autosomal Dominant (HP:0000006)' },
              { value: 'AR', label: 'Autosomal Recessive (HP:0000007)' },
              { value: 'XLD', label: 'X-linked Dominant (HP:0001417)' },
              { value: 'XLR', label: 'X-linked Recessive (HP:0001419)' },
              { value: 'SD', label: 'Semidominant (HP:0032113)' },
              { value: 'MT', label: 'Mitochondrial (HP:0001427)' },
              { value: 'Other', label: 'Other (specify)' }
            ]
          },
          {
            id: 'moi_notes',
            label: 'MOI Notes',
            type: 'textarea',
            required: false,
            show_when: { mode_of_inheritance: 'Other' },
            help_text: 'Provide details for Other inheritance pattern'
          }
        ]
      },
      {
        id: 'lumping_splitting',
        label: 'Lumping & Splitting',
        description: 'Document any lumping or splitting decisions per ClinGen guidelines',
        fields: [
          {
            id: 'lumping_splitting_applicable',
            label: 'Lumping/Splitting Applicable?',
            type: 'boolean',
            required: true,
            default: false,
            help_text: 'Does this curation involve combining or separating disease entities?'
          },
          {
            id: 'lumping_splitting_decision',
            label: 'Decision',
            type: 'select',
            required: true,
            show_when: { lumping_splitting_applicable: true },
            options: [
              { value: 'LUMP', label: 'Lump - Combine disease entities' },
              { value: 'SPLIT', label: 'Split - Separate disease entities' }
            ]
          },
          {
            id: 'lumping_splitting_rationale',
            label: 'Rationale',
            type: 'textarea',
            required: true,
            show_when: { lumping_splitting_applicable: true },
            help_text: 'Explain the rationale for lumping or splitting per ClinGen guidelines'
          }
        ]
      },
      {
        id: 'metadata',
        label: 'Precuration Metadata',
        fields: [
          {
            id: 'affiliation',
            label: 'Expert Panel / Affiliation',
            type: 'text',
            required: true,
            help_text: 'Your ClinGen Expert Panel or curation group'
          },
          {
            id: 'curator_notes',
            label: 'Curator Notes',
            type: 'textarea',
            required: false,
            help_text: 'Any additional notes for the precuration record'
          }
        ]
      }
    ]
  },
  ui_configuration: {
    form_layout: 'wizard',
    sections_collapsible: false,
    show_progress_bar: true,
    auto_save_interval_seconds: 30
  },
  scoring_configuration: null
}
