-- =============================================================================
-- 046: correct the ClinGen v1 methodology snapshots in place (#265, #266)
-- =============================================================================
-- Owner decision (2026-10-21): fix v1 in place instead of publishing a v2. The ClinGen v1
-- snapshots declared evidence the forms never write (genetic_evidence as an array in the
-- legacy seed; item_schema columns, min/max and enum types the validator ignores), so
-- validate-evidence rejected real data and accepted any point value.
-- The fields literal holds the evidence definitions the ClinGen forms actually write: the column sets of
-- frontend/src/components/clingen/sections/evidenceTableColumns.ts with the add-row defaults,
-- point ranges the validator enforces (min_value/max_value; min/max for the form), "order"
-- (jsonb sorts object keys), and replicated_over_time, which the Definitive band requires.
-- evidence_data paths are unchanged, so pins and stored data stay valid.
-- This is the one sanctioned exception to 042's immutability: as the table owner, the
-- trigger is disabled only for this update and re-enabled in the same transaction.
-- Idempotent (a re-run changes nothing); records itself in schema_migrations.
-- =============================================================================

-- A corrected copy of a snapshot-shaped document; the layout patch is keyed by section name
CREATE OR REPLACE FUNCTION pg_temp.clingen_046(s JSONB)
RETURNS JSONB AS $fn$
    SELECT s
        || jsonb_build_object(
            'field_definitions',
            COALESCE(s->'field_definitions', '{}'::jsonb) || $fields$
{
  "genetic_evidence": {
    "type": "object",
    "label": "Genetic Evidence",
    "description": "Genetic evidence supporting the gene-disease relationship (max 12 points)",
    "properties": {
      "case_level": {
        "type": "object",
        "label": "Case-Level Data",
        "description": "Case-level variant evidence by inheritance pattern and variant type",
        "properties": {
          "autosomal_dominant_or_x_linked": {
            "type": "object",
            "label": "Autosomal Dominant or X-linked",
            "description": "Evidence for AD or X-linked inheritance",
            "properties": {
              "predicted_or_proven_null": {
                "type": "array",
                "label": "Predicted or Proven Null",
                "description": "Predicted or proven null variants (default 1.5, 0-3 points)",
                "ui_component": "EvidenceTable",
                "items": {
                  "type": "object",
                  "properties": {
                    "proband_label": {"type": "string", "label": "Proband", "order": 1},
                    "variant_type": {"type": "select", "label": "Type", "options": [{"value": "nonsense", "label": "Nonsense"}, {"value": "frameshift", "label": "Frameshift"}, {"value": "canonical_splice", "label": "Splice (+/-1,2)"}, {"value": "initiation_codon", "label": "Init codon"}, {"value": "single_exon_deletion", "label": "Single exon del"}, {"value": "multi_exon_deletion", "label": "Multi-exon del"}, {"value": "whole_gene_deletion", "label": "Whole gene del"}], "default": "nonsense", "order": 2},
                    "variant": {"type": "string", "label": "Variant (HGVS)", "order": 3},
                    "pmid": {"type": "string", "label": "PMID", "validation": "pmid_format", "pattern": "^((?:[Pp][Mm][Ii][Dd]:?\\s*)?\\d{1,9})?$", "pattern_message": "PMID must be digits only", "order": 4},
                    "score_status": {"type": "select", "label": "Status", "options": [{"value": "score", "label": "Score"}, {"value": "review", "label": "Review"}, {"value": "contradicts", "label": "Contradicts"}], "default": "score", "order": 5},
                    "proband_counted_points": {"type": "number", "label": "Points", "min": 0, "min_value": 0, "max": 3, "max_value": 3, "step": 0.1, "default": 1.5, "order": 6},
                    "explanation": {"type": "string", "label": "Explanation", "order": 7}
                  }
                },
                "order": 1
              },
              "other_variant_type": {
                "type": "array",
                "label": "Other Variant Type",
                "description": "Other variant types (default 0.1, 0-1.5 points)",
                "ui_component": "EvidenceTable",
                "items": {
                  "type": "object",
                  "properties": {
                    "proband_label": {"type": "string", "label": "Proband", "order": 1},
                    "variant_type": {"type": "select", "label": "Type", "options": [{"value": "missense", "label": "Missense"}, {"value": "in_frame_indel", "label": "In-frame indel"}, {"value": "cryptic_splice", "label": "Cryptic splice"}, {"value": "synonymous", "label": "Synonymous"}, {"value": "5_utr", "label": "5' UTR"}, {"value": "3_utr", "label": "3' UTR"}, {"value": "intronic", "label": "Intronic"}, {"value": "other", "label": "Other"}], "default": "missense", "order": 2},
                    "variant": {"type": "string", "label": "Variant (HGVS)", "order": 3},
                    "pmid": {"type": "string", "label": "PMID", "validation": "pmid_format", "pattern": "^((?:[Pp][Mm][Ii][Dd]:?\\s*)?\\d{1,9})?$", "pattern_message": "PMID must be digits only", "order": 4},
                    "score_status": {"type": "select", "label": "Status", "options": [{"value": "score", "label": "Score"}, {"value": "review", "label": "Review"}, {"value": "contradicts", "label": "Contradicts"}], "default": "score", "order": 5},
                    "proband_counted_points": {"type": "number", "label": "Points", "min": 0, "min_value": 0, "max": 1.5, "max_value": 1.5, "step": 0.1, "default": 0.1, "order": 6},
                    "explanation": {"type": "string", "label": "Explanation", "order": 7}
                  }
                },
                "order": 2
              }
            },
            "order": 1
          },
          "autosomal_recessive": {
            "type": "object",
            "label": "Autosomal Recessive",
            "description": "Evidence for autosomal recessive inheritance",
            "properties": {
              "predicted_or_proven_null": {
                "type": "array",
                "label": "Predicted or Proven Null",
                "description": "Biallelic predicted or proven null variants (default 1.5, 0-3 points)",
                "ui_component": "EvidenceTable",
                "items": {
                  "type": "object",
                  "properties": {
                    "proband_label": {"type": "string", "label": "Proband", "order": 1},
                    "variant_type": {"type": "select", "label": "Type", "options": [{"value": "two_null", "label": "Two null variants"}, {"value": "null_and_null", "label": "Homozygous null"}], "default": "two_null", "order": 2},
                    "variant_1": {"type": "string", "label": "Variant 1", "order": 3},
                    "variant_2": {"type": "string", "label": "Variant 2", "order": 4},
                    "pmid": {"type": "string", "label": "PMID", "validation": "pmid_format", "pattern": "^((?:[Pp][Mm][Ii][Dd]:?\\s*)?\\d{1,9})?$", "pattern_message": "PMID must be digits only", "order": 5},
                    "score_status": {"type": "select", "label": "Status", "options": [{"value": "score", "label": "Score"}, {"value": "review", "label": "Review"}, {"value": "contradicts", "label": "Contradicts"}], "default": "score", "order": 6},
                    "proband_counted_points": {"type": "number", "label": "Points", "min": 0, "min_value": 0, "max": 3, "max_value": 3, "step": 0.1, "default": 1.5, "order": 7},
                    "explanation": {"type": "string", "label": "Explanation", "order": 8}
                  }
                },
                "order": 1
              },
              "other_variant_type": {
                "type": "array",
                "label": "Other Variant Type",
                "description": "Biallelic other variant types (default 0.1, 0-1.5 points)",
                "ui_component": "EvidenceTable",
                "items": {
                  "type": "object",
                  "properties": {
                    "proband_label": {"type": "string", "label": "Proband", "order": 1},
                    "variant_type": {"type": "select", "label": "Type", "options": [{"value": "null_and_other", "label": "Null + Other"}, {"value": "two_other", "label": "Two other variants"}, {"value": "homozygous_other", "label": "Homozygous other"}], "default": "null_and_other", "order": 2},
                    "variant_1": {"type": "string", "label": "Variant 1", "order": 3},
                    "variant_2": {"type": "string", "label": "Variant 2", "order": 4},
                    "pmid": {"type": "string", "label": "PMID", "validation": "pmid_format", "pattern": "^((?:[Pp][Mm][Ii][Dd]:?\\s*)?\\d{1,9})?$", "pattern_message": "PMID must be digits only", "order": 5},
                    "score_status": {"type": "select", "label": "Status", "options": [{"value": "score", "label": "Score"}, {"value": "review", "label": "Review"}, {"value": "contradicts", "label": "Contradicts"}], "default": "score", "order": 6},
                    "proband_counted_points": {"type": "number", "label": "Points", "min": 0, "min_value": 0, "max": 1.5, "max_value": 1.5, "step": 0.1, "default": 0.1, "order": 7},
                    "explanation": {"type": "string", "label": "Explanation", "order": 8}
                  }
                },
                "order": 2
              }
            },
            "order": 2
          }
        },
        "order": 1
      },
      "segregation": {
        "type": "array",
        "label": "Segregation",
        "description": "Segregation evidence (max 3 points)",
        "ui_component": "EvidenceTable",
        "items": {
          "type": "object",
          "properties": {
            "family_label": {"type": "string", "label": "Family", "order": 1},
            "pmid": {"type": "string", "label": "PMID", "validation": "pmid_format", "pattern": "^((?:[Pp][Mm][Ii][Dd]:?\\s*)?\\d{1,9})?$", "pattern_message": "PMID must be digits only", "order": 2},
            "lod_score": {"type": "number", "label": "LOD Score", "min": 0, "min_value": 0, "step": 0.1, "default": 0, "order": 3},
            "segregations_counted": {"type": "number", "label": "Seg. Counted", "min": 0, "min_value": 0, "default": 0, "order": 4},
            "points": {"type": "number", "label": "Points", "min": 0, "min_value": 0, "max": 3, "max_value": 3, "step": 0.1, "default": 0, "order": 5},
            "explanation": {"type": "string", "label": "Explanation", "order": 6}
          }
        },
        "order": 2
      },
      "case_control": {
        "type": "object",
        "label": "Case-Control Data",
        "description": "Case-control studies (max 6 points)",
        "properties": {
          "single_variant_analysis": {
            "type": "array",
            "label": "Single Variant Analysis",
            "description": "Single variant analysis (0-6 points)",
            "ui_component": "EvidenceTable",
            "items": {
              "type": "object",
              "properties": {
                "study_label": {"type": "string", "label": "Study", "order": 1},
                "pmid": {"type": "string", "label": "PMID", "validation": "pmid_format", "pattern": "^((?:[Pp][Mm][Ii][Dd]:?\\s*)?\\d{1,9})?$", "pattern_message": "PMID must be digits only", "order": 2},
                "variant": {"type": "string", "label": "Variant", "order": 3},
                "cases_with_variant": {"type": "number", "label": "Cases+", "min": 0, "min_value": 0, "default": 0, "order": 4},
                "cases_total": {"type": "number", "label": "Cases", "min": 1, "min_value": 1, "default": 1, "order": 5},
                "controls_with_variant": {"type": "number", "label": "Ctrl+", "min": 0, "min_value": 0, "default": 0, "order": 6},
                "controls_total": {"type": "number", "label": "Ctrl", "min": 1, "min_value": 1, "default": 1, "order": 7},
                "odds_ratio": {"type": "number", "label": "OR", "min": 0, "min_value": 0, "default": 0, "order": 8},
                "p_value": {"type": "number", "label": "P-value", "min": 0, "min_value": 0, "max": 1, "max_value": 1, "default": 1, "order": 9},
                "points": {"type": "number", "label": "Points", "min": 0, "min_value": 0, "max": 6, "max_value": 6, "step": 0.5, "default": 0, "order": 10}
              }
            },
            "order": 1
          },
          "aggregate_variant_analysis": {
            "type": "array",
            "label": "Aggregate Variant Analysis",
            "description": "Aggregate variant analysis (0-6 points)",
            "ui_component": "EvidenceTable",
            "items": {
              "type": "object",
              "properties": {
                "study_label": {"type": "string", "label": "Study", "order": 1},
                "pmid": {"type": "string", "label": "PMID", "validation": "pmid_format", "pattern": "^((?:[Pp][Mm][Ii][Dd]:?\\s*)?\\d{1,9})?$", "pattern_message": "PMID must be digits only", "order": 2},
                "analysis_type": {"type": "select", "label": "Analysis", "options": [{"value": "burden", "label": "Burden test"}, {"value": "collapsing", "label": "Collapsing"}, {"value": "skat", "label": "SKAT"}, {"value": "skat_o", "label": "SKAT-O"}, {"value": "other", "label": "Other"}], "default": "burden", "order": 3},
                "cases_with_variants": {"type": "number", "label": "Cases+", "min": 0, "min_value": 0, "default": 0, "order": 4},
                "cases_total": {"type": "number", "label": "Cases", "min": 1, "min_value": 1, "default": 1, "order": 5},
                "controls_with_variants": {"type": "number", "label": "Ctrl+", "min": 0, "min_value": 0, "default": 0, "order": 6},
                "controls_total": {"type": "number", "label": "Ctrl", "min": 1, "min_value": 1, "default": 1, "order": 7},
                "p_value": {"type": "number", "label": "P-value", "min": 0, "min_value": 0, "max": 1, "max_value": 1, "default": 1, "order": 8},
                "points": {"type": "number", "label": "Points", "min": 0, "min_value": 0, "max": 6, "max_value": 6, "step": 0.5, "default": 0, "order": 9}
              }
            },
            "order": 2
          }
        },
        "order": 3
      }
    }
  },
  "experimental_evidence": {
    "type": "object",
    "label": "Experimental Evidence",
    "description": "Experimental evidence supporting the gene-disease relationship (max 6 points)",
    "properties": {
      "function": {
        "type": "object",
        "label": "Function",
        "description": "Function (max 2 points)",
        "properties": {
          "biochemical_function": {
            "type": "array",
            "label": "Biochemical Function",
            "description": "Gene product performs a biochemical function shared with other known disease genes (default 0.5, 0-2 points)",
            "ui_component": "EvidenceTable",
            "items": {
              "type": "object",
              "properties": {
                "label": {"type": "string", "label": "Label", "order": 1},
                "pmid": {"type": "string", "label": "PMID", "validation": "pmid_format", "pattern": "^((?:[Pp][Mm][Ii][Dd]:?\\s*)?\\d{1,9})?$", "pattern_message": "PMID must be digits only", "order": 2},
                "gene_function_description": {"type": "string", "label": "Function Description", "order": 3},
                "disease_mechanism_relevance": {"type": "string", "label": "Disease Relevance", "order": 4},
                "score_status": {"type": "select", "label": "Status", "options": [{"value": "score", "label": "Score"}, {"value": "review", "label": "Review"}], "default": "score", "order": 5},
                "points": {"type": "number", "label": "Points", "min": 0, "min_value": 0, "max": 2, "max_value": 2, "step": 0.5, "default": 0.5, "order": 6},
                "explanation": {"type": "string", "label": "Explanation", "order": 7}
              }
            },
            "order": 1
          },
          "protein_interaction": {
            "type": "array",
            "label": "Protein Interaction",
            "description": "Gene product interacts with proteins implicated in the disease (default 0.5, 0-2 points)",
            "ui_component": "EvidenceTable",
            "items": {
              "type": "object",
              "properties": {
                "label": {"type": "string", "label": "Label", "order": 1},
                "pmid": {"type": "string", "label": "PMID", "validation": "pmid_format", "pattern": "^((?:[Pp][Mm][Ii][Dd]:?\\s*)?\\d{1,9})?$", "pattern_message": "PMID must be digits only", "order": 2},
                "interacting_protein": {"type": "string", "label": "Interacting Protein", "order": 3},
                "interaction_method": {"type": "string", "label": "Method", "order": 4},
                "disease_relevance": {"type": "string", "label": "Disease Relevance", "order": 5},
                "score_status": {"type": "select", "label": "Status", "options": [{"value": "score", "label": "Score"}, {"value": "review", "label": "Review"}], "default": "score", "order": 6},
                "points": {"type": "number", "label": "Points", "min": 0, "min_value": 0, "max": 2, "max_value": 2, "step": 0.5, "default": 0.5, "order": 7}
              }
            },
            "order": 2
          },
          "expression": {
            "type": "array",
            "label": "Expression",
            "description": "Gene is expressed in tissues relevant to the disease (default 0.5, 0-2 points)",
            "ui_component": "EvidenceTable",
            "items": {
              "type": "object",
              "properties": {
                "label": {"type": "string", "label": "Label", "order": 1},
                "pmid": {"type": "string", "label": "PMID", "validation": "pmid_format", "pattern": "^((?:[Pp][Mm][Ii][Dd]:?\\s*)?\\d{1,9})?$", "pattern_message": "PMID must be digits only", "order": 2},
                "tissue_organ": {"type": "string", "label": "Tissue/Organ", "order": 3},
                "expression_method": {"type": "string", "label": "Method", "order": 4},
                "disease_tissue_relevance": {"type": "string", "label": "Relevance", "order": 5},
                "score_status": {"type": "select", "label": "Status", "options": [{"value": "score", "label": "Score"}, {"value": "review", "label": "Review"}], "default": "score", "order": 6},
                "points": {"type": "number", "label": "Points", "min": 0, "min_value": 0, "max": 2, "max_value": 2, "step": 0.5, "default": 0.5, "order": 7}
              }
            },
            "order": 3
          }
        },
        "order": 1
      },
      "functional_alteration": {
        "type": "object",
        "label": "Functional Alteration",
        "description": "Functional alteration (max 2 points)",
        "properties": {
          "patient_cells": {
            "type": "array",
            "label": "Patient Cells",
            "description": "Functional alteration in patient cells (default 1, 0-2 points)",
            "ui_component": "EvidenceTable",
            "items": {
              "type": "object",
              "properties": {
                "label": {"type": "string", "label": "Label", "order": 1},
                "pmid": {"type": "string", "label": "PMID", "validation": "pmid_format", "pattern": "^((?:[Pp][Mm][Ii][Dd]:?\\s*)?\\d{1,9})?$", "pattern_message": "PMID must be digits only", "order": 2},
                "cell_type": {"type": "string", "label": "Cell Type", "order": 3},
                "variant_tested": {"type": "string", "label": "Variant", "order": 4},
                "functional_effect": {"type": "string", "label": "Effect", "order": 5},
                "assay_method": {"type": "string", "label": "Assay", "order": 6},
                "score_status": {"type": "select", "label": "Status", "options": [{"value": "score", "label": "Score"}, {"value": "review", "label": "Review"}], "default": "score", "order": 7},
                "points": {"type": "number", "label": "Points", "min": 0, "min_value": 0, "max": 2, "max_value": 2, "step": 0.5, "default": 1, "order": 8}
              }
            },
            "order": 1
          },
          "non_patient_cells": {
            "type": "array",
            "label": "Non-patient Cells",
            "description": "Functional alteration in non-patient cells (default 0.5, 0-1 points)",
            "ui_component": "EvidenceTable",
            "items": {
              "type": "object",
              "properties": {
                "label": {"type": "string", "label": "Label", "order": 1},
                "pmid": {"type": "string", "label": "PMID", "validation": "pmid_format", "pattern": "^((?:[Pp][Mm][Ii][Dd]:?\\s*)?\\d{1,9})?$", "pattern_message": "PMID must be digits only", "order": 2},
                "cell_line": {"type": "string", "label": "Cell Line", "order": 3},
                "variant_engineered": {"type": "string", "label": "Variant", "order": 4},
                "functional_effect": {"type": "string", "label": "Effect", "order": 5},
                "assay_method": {"type": "string", "label": "Assay", "order": 6},
                "score_status": {"type": "select", "label": "Status", "options": [{"value": "score", "label": "Score"}, {"value": "review", "label": "Review"}], "default": "score", "order": 7},
                "points": {"type": "number", "label": "Points", "min": 0, "min_value": 0, "max": 1, "max_value": 1, "step": 0.5, "default": 0.5, "order": 8}
              }
            },
            "order": 2
          }
        },
        "order": 2
      },
      "models": {
        "type": "object",
        "label": "Models",
        "description": "Models; one Models & Rescue category with rescue (max 4 points combined)",
        "properties": {
          "non_human_model_organism": {
            "type": "array",
            "label": "Non-human Model Organism",
            "description": "Non-human model organism recapitulates the phenotype (default 2, 0-4 points)",
            "ui_component": "EvidenceTable",
            "items": {
              "type": "object",
              "properties": {
                "label": {"type": "string", "label": "Label", "order": 1},
                "pmid": {"type": "string", "label": "PMID", "validation": "pmid_format", "pattern": "^((?:[Pp][Mm][Ii][Dd]:?\\s*)?\\d{1,9})?$", "pattern_message": "PMID must be digits only", "order": 2},
                "organism": {"type": "select", "label": "Organism", "options": [{"value": "mouse", "label": "Mouse"}, {"value": "rat", "label": "Rat"}, {"value": "zebrafish", "label": "Zebrafish"}, {"value": "drosophila", "label": "Drosophila"}, {"value": "c_elegans", "label": "C. elegans"}, {"value": "xenopus", "label": "Xenopus"}, {"value": "yeast", "label": "Yeast"}, {"value": "other", "label": "Other"}], "default": "mouse", "order": 3},
                "model_type": {"type": "select", "label": "Type", "options": [{"value": "knockout", "label": "Knockout"}, {"value": "knockin", "label": "Knockin"}, {"value": "transgenic", "label": "Transgenic"}, {"value": "morpholino", "label": "Morpholino"}, {"value": "crispr", "label": "CRISPR"}, {"value": "other", "label": "Other"}], "default": "knockout", "order": 4},
                "phenotype_observed": {"type": "string", "label": "Phenotype", "order": 5},
                "human_phenotype_match": {"type": "string", "label": "Human Match", "order": 6},
                "score_status": {"type": "select", "label": "Status", "options": [{"value": "score", "label": "Score"}, {"value": "review", "label": "Review"}], "default": "score", "order": 7},
                "points": {"type": "number", "label": "Points", "min": 0, "min_value": 0, "max": 4, "max_value": 4, "step": 0.5, "default": 2, "order": 8}
              }
            },
            "order": 1
          },
          "cell_culture_model": {
            "type": "array",
            "label": "Cell Culture Model",
            "description": "Cell culture model recapitulates the phenotype (default 1, 0-2 points)",
            "ui_component": "EvidenceTable",
            "items": {
              "type": "object",
              "properties": {
                "label": {"type": "string", "label": "Label", "order": 1},
                "pmid": {"type": "string", "label": "PMID", "validation": "pmid_format", "pattern": "^((?:[Pp][Mm][Ii][Dd]:?\\s*)?\\d{1,9})?$", "pattern_message": "PMID must be digits only", "order": 2},
                "cell_type": {"type": "select", "label": "Cell Type", "options": [{"value": "ipsc", "label": "iPSC-derived"}, {"value": "organoid", "label": "Organoid"}, {"value": "primary", "label": "Primary cells"}, {"value": "cell_line", "label": "Cell line"}, {"value": "other", "label": "Other"}], "default": "ipsc", "order": 3},
                "modification": {"type": "string", "label": "Modification", "order": 4},
                "phenotype_observed": {"type": "string", "label": "Phenotype", "order": 5},
                "score_status": {"type": "select", "label": "Status", "options": [{"value": "score", "label": "Score"}, {"value": "review", "label": "Review"}], "default": "score", "order": 6},
                "points": {"type": "number", "label": "Points", "min": 0, "min_value": 0, "max": 2, "max_value": 2, "step": 0.5, "default": 1, "order": 7}
              }
            },
            "order": 2
          }
        },
        "order": 3
      },
      "rescue": {
        "type": "object",
        "label": "Rescue",
        "description": "Rescue; one Models & Rescue category with models (max 4 points combined)",
        "properties": {
          "human": {
            "type": "array",
            "label": "Rescue in Human",
            "description": "Rescue in human (default 2, 0-4 points)",
            "ui_component": "EvidenceTable",
            "items": {
              "type": "object",
              "properties": {
                "label": {"type": "string", "label": "Label", "order": 1},
                "pmid": {"type": "string", "label": "PMID", "validation": "pmid_format", "pattern": "^((?:[Pp][Mm][Ii][Dd]:?\\s*)?\\d{1,9})?$", "pattern_message": "PMID must be digits only", "order": 2},
                "rescue_method": {"type": "string", "label": "Method", "order": 3},
                "phenotype_rescued": {"type": "string", "label": "Phenotype Rescued", "order": 4},
                "rescue_extent": {"type": "string", "label": "Rescue Extent", "order": 5},
                "score_status": {"type": "select", "label": "Status", "options": [{"value": "score", "label": "Score"}, {"value": "review", "label": "Review"}], "default": "score", "order": 6},
                "points": {"type": "number", "label": "Points", "min": 0, "min_value": 0, "max": 4, "max_value": 4, "step": 0.5, "default": 2, "order": 7}
              }
            },
            "order": 1
          },
          "non_human_model_organism": {
            "type": "array",
            "label": "Rescue in Non-human Model Organism",
            "description": "Rescue in non-human model organism (default 2, 0-4 points)",
            "ui_component": "EvidenceTable",
            "items": {
              "type": "object",
              "properties": {
                "label": {"type": "string", "label": "Label", "order": 1},
                "pmid": {"type": "string", "label": "PMID", "validation": "pmid_format", "pattern": "^((?:[Pp][Mm][Ii][Dd]:?\\s*)?\\d{1,9})?$", "pattern_message": "PMID must be digits only", "order": 2},
                "organism": {"type": "string", "label": "Organism", "order": 3},
                "rescue_method": {"type": "string", "label": "Method", "order": 4},
                "phenotype_rescued": {"type": "string", "label": "Phenotype Rescued", "order": 5},
                "score_status": {"type": "select", "label": "Status", "options": [{"value": "score", "label": "Score"}, {"value": "review", "label": "Review"}], "default": "score", "order": 6},
                "points": {"type": "number", "label": "Points", "min": 0, "min_value": 0, "max": 4, "max_value": 4, "step": 0.5, "default": 2, "order": 7}
              }
            },
            "order": 2
          },
          "cell_culture": {
            "type": "array",
            "label": "Rescue in Cell Culture Model",
            "description": "Rescue in cell culture model (default 1, 0-2 points)",
            "ui_component": "EvidenceTable",
            "items": {
              "type": "object",
              "properties": {
                "label": {"type": "string", "label": "Label", "order": 1},
                "pmid": {"type": "string", "label": "PMID", "validation": "pmid_format", "pattern": "^((?:[Pp][Mm][Ii][Dd]:?\\s*)?\\d{1,9})?$", "pattern_message": "PMID must be digits only", "order": 2},
                "cell_type": {"type": "string", "label": "Cell Type", "order": 3},
                "rescue_method": {"type": "string", "label": "Method", "order": 4},
                "phenotype_rescued": {"type": "string", "label": "Phenotype Rescued", "order": 5},
                "score_status": {"type": "select", "label": "Status", "options": [{"value": "score", "label": "Score"}, {"value": "review", "label": "Review"}], "default": "score", "order": 6},
                "points": {"type": "number", "label": "Points", "min": 0, "min_value": 0, "max": 2, "max_value": 2, "step": 0.5, "default": 1, "order": 7}
              }
            },
            "order": 3
          },
          "patient_cells": {
            "type": "array",
            "label": "Rescue in Patient Cells",
            "description": "Rescue in patient cells (default 1, 0-2 points)",
            "ui_component": "EvidenceTable",
            "items": {
              "type": "object",
              "properties": {
                "label": {"type": "string", "label": "Label", "order": 1},
                "pmid": {"type": "string", "label": "PMID", "validation": "pmid_format", "pattern": "^((?:[Pp][Mm][Ii][Dd]:?\\s*)?\\d{1,9})?$", "pattern_message": "PMID must be digits only", "order": 2},
                "cell_type": {"type": "string", "label": "Cell Type", "order": 3},
                "rescue_method": {"type": "string", "label": "Method", "order": 4},
                "phenotype_rescued": {"type": "string", "label": "Phenotype Rescued", "order": 5},
                "score_status": {"type": "select", "label": "Status", "options": [{"value": "score", "label": "Score"}, {"value": "review", "label": "Review"}], "default": "score", "order": 6},
                "points": {"type": "number", "label": "Points", "min": 0, "min_value": 0, "max": 2, "max_value": 2, "step": 0.5, "default": 1, "order": 7}
              }
            },
            "order": 4
          }
        },
        "order": 4
      }
    }
  },
  "contradictory_evidence": {
    "type": "array",
    "label": "Contradictory Evidence",
    "ui_component": "EvidenceTable",
    "description": "Evidence that contradicts the gene-disease relationship (may result in Disputed)",
    "items": {
      "type": "object",
      "properties": {
        "label": {"type": "string", "label": "Label", "order": 1},
        "pmid": {"type": "string", "label": "PMID", "validation": "pmid_format", "pattern": "^((?:[Pp][Mm][Ii][Dd]:?\\s*)?\\d{1,9})?$", "pattern_message": "PMID must be digits only", "order": 2},
        "evidence_type": {"type": "select", "label": "Type", "options": [{"value": "population", "label": "Population/control data"}, {"value": "segregation", "label": "Non-segregation"}, {"value": "functional", "label": "Contradictory functional data"}, {"value": "phenotype", "label": "Phenotype mismatch"}, {"value": "other", "label": "Other"}], "default": "population", "order": 3},
        "description": {"type": "string", "label": "Description", "order": 4},
        "impact": {"type": "select", "label": "Impact", "options": [{"value": "disputed", "label": "Disputed"}, {"value": "note", "label": "Note only"}, {"value": "requires_review", "label": "Review needed"}], "default": "note", "order": 5}
      }
    }
  },
  "replicated_over_time": {"type": "boolean", "label": "Replicated over time (\u22652 independent publications, >3 years)", "default": false}
}
$fields$::jsonb)
        || CASE WHEN jsonb_typeof(s->'ui_configuration'->'layout'->'tabs') = 'array' THEN
            jsonb_build_object('ui_configuration', jsonb_set(
                s->'ui_configuration', '{layout,tabs}',
                (SELECT jsonb_agg(
                    CASE WHEN jsonb_typeof(tab->'sections') = 'array' THEN jsonb_set(
                        tab, '{sections}',
                        (SELECT jsonb_agg(
                            sec || COALESCE($ui${
                                "Classification Summary": {"fields": ["evidence_summary", "replicated_over_time"]},
                                "Models": {"help_text": "Non-human model organisms and cell culture (Models & Rescue: max 4 pts combined)"},
                                "Rescue": {"help_text": "Rescue experiments (Models & Rescue: max 4 pts combined)"}
                            }$ui$::jsonb -> (sec->>'name'), '{}'::jsonb)
                            ORDER BY j)
                         FROM jsonb_array_elements(tab->'sections') WITH ORDINALITY AS y(sec, j)))
                    ELSE tab END
                    ORDER BY i)
                 FROM jsonb_array_elements(s->'ui_configuration'->'layout'->'tabs')
                      WITH ORDINALITY AS x(tab, i))))
        ELSE '{}'::jsonb END
$fn$ LANGUAGE SQL IMMUTABLE;

DO $migration$
DECLARE
    corrected TEXT[];
    schemas TEXT[];
BEGIN
    ALTER TABLE methodology_versions DISABLE TRIGGER trigger_methodology_version_immutable;
    WITH fixed AS (
        UPDATE methodology_versions
        SET snapshot = pg_temp.clingen_046(snapshot)
        WHERE version = 1
          AND snapshot->'scoring_configuration'->>'engine' = 'clingen_sop_v11'
          AND snapshot IS DISTINCT FROM pg_temp.clingen_046(snapshot)
        RETURNING id
    )
    SELECT array_agg(id::text ORDER BY id) INTO corrected FROM fixed;
    ALTER TABLE methodology_versions ENABLE TRIGGER trigger_methodology_version_immutable;

    -- The working copies too, so the next publish does not bring the drift back
    WITH fixed AS (
        UPDATE curation_schemas c
        SET field_definitions = f.doc->'field_definitions',
            ui_configuration = NULLIF(f.doc->'ui_configuration', 'null'::jsonb)
        FROM (
            SELECT id, pg_temp.clingen_046(jsonb_build_object(
                'field_definitions', field_definitions,
                'ui_configuration', ui_configuration
            )) AS doc
            FROM curation_schemas
            WHERE schema_type = 'curation'
              AND scoring_configuration->>'engine' = 'clingen_sop_v11'
        ) f
        WHERE c.id = f.id
          AND (c.field_definitions, c.ui_configuration)
              IS DISTINCT FROM (f.doc->'field_definitions', NULLIF(f.doc->'ui_configuration', 'null'::jsonb))
        RETURNING c.name
    )
    SELECT array_agg(name ORDER BY name) INTO schemas FROM fixed;

    RAISE NOTICE '046: corrected ClinGen v1 snapshots %, working copies %',
        COALESCE(corrected, '{}'), COALESCE(schemas, '{}');
END
$migration$;

INSERT INTO schema_migrations (filename)
VALUES ('046_clingen_v1_correction.sql')
ON CONFLICT DO NOTHING;
