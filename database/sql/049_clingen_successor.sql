-- 049: immutable ClinGen successor (#438), delegated Wave 5 decision.
-- SOP v11 pp.17/20/21: AR starting suggestions are per allele; the mixed case uses
-- the documented GCI-rounded 1.5. Untouched rows never score under the successor.
-- Segregation requires explicit points: the current schema cannot represent the
-- eligibility/method/aggregate inputs in SOP pp.28-35. Full automation: issue #447.
-- Existing versions, pins, evidence and scores are NEVER updated or recomputed.
-- Only unmodified stock definitions whose current working copy still equals v1
-- qualify. Custom models, derived definitions, edits and later changed publications
-- remain untouched. Schema-row locks use the same serialization as API publication.
-- Idempotent and self-recording; no immutability trigger is disabled.

CREATE OR REPLACE FUNCTION pg_temp.clingen_049(doc JSONB)
RETURNS JSONB AS $fn$
DECLARE
    change JSONB;
BEGIN
    FOR change IN SELECT value FROM jsonb_array_elements($patches$
[
  {
    "path": [
      "field_definitions",
      "genetic_evidence",
      "properties",
      "case_level",
      "properties",
      "autosomal_recessive",
      "properties",
      "predicted_or_proven_null",
      "items",
      "properties",
      "proband_counted_points",
      "default"
    ],
    "value": 3
  },
  {
    "path": [
      "field_definitions",
      "genetic_evidence",
      "properties",
      "case_level",
      "properties",
      "autosomal_recessive",
      "properties",
      "predicted_or_proven_null",
      "description"
    ],
    "value": "Two null variants or homozygous null: starting suggestion 3 points (0\u20133 per proband). Starting suggestions assume qualifying biallelic evidence. Reassess the score for the case; loaded or manually edited scores stay unchanged when the variant type changes."
  },
  {
    "path": [
      "field_definitions",
      "genetic_evidence",
      "properties",
      "case_level",
      "properties",
      "autosomal_recessive",
      "properties",
      "other_variant_type",
      "items",
      "properties",
      "proband_counted_points",
      "default"
    ],
    "value": 1.5
  },
  {
    "path": [
      "field_definitions",
      "genetic_evidence",
      "properties",
      "case_level",
      "properties",
      "autosomal_recessive",
      "properties",
      "other_variant_type",
      "items",
      "properties",
      "proband_counted_points",
      "default_by"
    ],
    "value": {
      "field": "variant_type",
      "values": {
        "null_and_other": 1.5,
        "two_other": 0.2,
        "homozygous_other": 0.2
      }
    }
  },
  {
    "path": [
      "field_definitions",
      "genetic_evidence",
      "properties",
      "case_level",
      "properties",
      "autosomal_recessive",
      "properties",
      "other_variant_type",
      "description"
    ],
    "value": "Null + Other starts at 1.5 (SOP v11 GCI-rounded example); two other or homozygous other starts at 0.2 (0\u20133 per proband). Starting suggestions assume qualifying biallelic evidence. Reassess the score for the case; loaded or manually edited scores stay unchanged when the variant type changes."
  },
  {
    "path": [
      "field_definitions",
      "genetic_evidence",
      "properties",
      "segregation",
      "description"
    ],
    "value": "Enter curator-assigned segregation points after assessing all included families, eligibility and sequencing methods (category max 3). LOD and family counts do not generate automatic points. See ClinGen SOP v11 pp.28\u201335."
  },
  {
    "path": [
      "scoring_configuration",
      "point_model",
      "sections",
      "0",
      "categories",
      "0",
      "types",
      "2",
      "blank_at"
    ],
    "value": null
  },
  {
    "path": [
      "scoring_configuration",
      "point_model",
      "sections",
      "0",
      "categories",
      "0",
      "types",
      "3",
      "blank_at"
    ],
    "value": null
  },
  {
    "path": [
      "scoring_configuration",
      "point_model",
      "sections",
      "0",
      "categories",
      "1",
      "types",
      "0",
      "rule"
    ],
    "value": "explicit_points"
  },
  {
    "path": [
      "scoring_configuration",
      "point_model",
      "sections",
      "0",
      "categories",
      "1",
      "types",
      "0",
      "default"
    ],
    "value": 0
  }
]
$patches$::jsonb)
    LOOP
        doc := jsonb_set(doc, ARRAY(SELECT jsonb_array_elements_text(change->'path')),
                         change->'value', true);
    END LOOP;
    RETURN doc;
END
$fn$ LANGUAGE plpgsql IMMUTABLE;

DO $migration$
DECLARE
    old_model CONSTANT JSONB := $model$
{
  "name": "ClinGen SOP v11",
  "total_cap": 18,
  "sections": [
    {
      "key": "genetic_evidence",
      "cap": 12,
      "categories": [
        {
          "key": "case_level",
          "cap": 12,
          "types": [
            {
              "path": "case_level.autosomal_dominant_or_x_linked.predicted_or_proven_null",
              "rule": "case_row",
              "points_key": "proband_counted_points",
              "blank_at": 1.5,
              "range": [
                0,
                3
              ]
            },
            {
              "path": "case_level.autosomal_dominant_or_x_linked.other_variant_type",
              "rule": "case_row",
              "points_key": "proband_counted_points",
              "blank_at": 0.1,
              "range": [
                0,
                1.5
              ]
            },
            {
              "path": "case_level.autosomal_recessive.predicted_or_proven_null",
              "rule": "case_row",
              "points_key": "proband_counted_points",
              "blank_at": 1.5,
              "range": [
                0,
                3
              ]
            },
            {
              "path": "case_level.autosomal_recessive.other_variant_type",
              "rule": "case_row",
              "points_key": "proband_counted_points",
              "blank_at": 0.1,
              "range": [
                0,
                3
              ]
            }
          ]
        },
        {
          "key": "segregation",
          "cap": 3,
          "types": [
            {
              "path": "segregation",
              "rule": "segregation",
              "range": [
                0,
                3
              ]
            }
          ]
        },
        {
          "key": "case_control",
          "cap": 12,
          "types": [
            {
              "path": "case_control.single_variant_analysis",
              "default": 0,
              "range": [
                0,
                6
              ]
            },
            {
              "path": "case_control.aggregate_variant_analysis",
              "default": 0,
              "range": [
                0,
                6
              ]
            }
          ]
        }
      ]
    },
    {
      "key": "experimental_evidence",
      "cap": 6,
      "categories": [
        {
          "key": "function",
          "cap": 2,
          "types": [
            {
              "path": "function.biochemical_function",
              "default": 0.5,
              "range": [
                0,
                2
              ]
            },
            {
              "path": "function.protein_interaction",
              "default": 0.5,
              "range": [
                0,
                2
              ]
            },
            {
              "path": "function.expression",
              "default": 0.5,
              "range": [
                0,
                2
              ]
            }
          ]
        },
        {
          "key": "functional_alteration",
          "cap": 2,
          "types": [
            {
              "path": "functional_alteration.patient_cells",
              "default": 1,
              "range": [
                0,
                2
              ]
            },
            {
              "path": "functional_alteration.non_patient_cells",
              "default": 0.5,
              "range": [
                0,
                1
              ]
            }
          ]
        },
        {
          "key": "models_and_rescue",
          "cap": 4,
          "types": [
            {
              "path": "models.non_human_model_organism",
              "default": 2,
              "range": [
                0,
                4
              ]
            },
            {
              "path": "models.cell_culture_model",
              "default": 1,
              "range": [
                0,
                2
              ]
            },
            {
              "path": "rescue.human",
              "default": 2,
              "range": [
                0,
                4
              ]
            },
            {
              "path": "rescue.non_human_model_organism",
              "default": 2,
              "range": [
                0,
                4
              ]
            },
            {
              "path": "rescue.cell_culture",
              "default": 1,
              "range": [
                0,
                2
              ]
            },
            {
              "path": "rescue.patient_cells",
              "default": 1,
              "range": [
                0,
                2
              ]
            }
          ]
        }
      ]
    }
  ],
  "overrides": [
    {
      "when": "contradictory_evidence",
      "field": "impact",
      "in": [
        "disputed"
      ],
      "class": "disputed",
      "description": "Contradictory evidence with impact Disputed present, resulting in DISPUTED classification."
    }
  ],
  "bands": [
    {
      "class": "definitive",
      "min": 12,
      "requires": "replicated_over_time",
      "description": "Total score 12-18 points (Strong) with replication over time supports a DEFINITIVE gene-disease relationship."
    },
    {
      "class": "strong",
      "min": 12,
      "description": "Total score 12-18 points supports STRONG gene-disease relationship."
    },
    {
      "class": "moderate",
      "min": 7,
      "description": "Total score 7-11 points supports MODERATE gene-disease relationship."
    },
    {
      "class": "limited",
      "min": 0.1,
      "description": "Total score 1-6 points supports LIMITED gene-disease relationship."
    },
    {
      "class": "no_known",
      "min": 0,
      "description": "No evidence supporting a gene-disease relationship."
    },
    {
      "class": "disputed",
      "min": -1,
      "description": "Conflicting or contradictory evidence present, resulting in DISPUTED classification."
    },
    {
      "class": "refuted",
      "description": "Evidence refutes the gene-disease relationship."
    }
  ]
}
$model$::jsonb;
    s curation_schemas%ROWTYPE;
    original methodology_versions%ROWTYPE;
    latest methodology_versions%ROWTYPE;
    corrected JSONB;
    published TEXT[] := '{}';
BEGIN
    FOR s IN SELECT * FROM curation_schemas
        WHERE schema_type = 'curation' AND based_on_schema_id IS NULL
          AND (name, version) IN (('ClinGen_SOP_v11', '1.0.0'),
                                 ('ClinGen Gene-Disease Validity SOP', '11.0'))
        ORDER BY id FOR UPDATE
    LOOP
        SELECT * INTO original FROM methodology_versions
            WHERE schema_id = s.id AND version = 1;
        SELECT * INTO latest FROM methodology_versions
            WHERE schema_id = s.id ORDER BY version DESC LIMIT 1;
        IF original.id IS NULL OR original.derived_from_version_id IS NOT NULL
           OR original.snapshot->'scoring_configuration'->>'engine' IS DISTINCT FROM 'clingen_sop_v11'
           OR original.snapshot->'scoring_configuration'->'point_model' IS DISTINCT FROM old_model
           OR methodology_snapshot(s) IS DISTINCT FROM original.snapshot
           OR latest.snapshot IS DISTINCT FROM original.snapshot THEN
            CONTINUE;
        END IF;
        corrected := pg_temp.clingen_049(original.snapshot);
        INSERT INTO methodology_versions
            (schema_id, version, snapshot, created_by, derived_from_version_id)
        VALUES (s.id, latest.version + 1, corrected, s.created_by, original.id);
        UPDATE curation_schemas
            SET field_definitions = corrected->'field_definitions',
                scoring_configuration = corrected->'scoring_configuration'
            WHERE id = s.id;
        published := array_append(published, s.name || ' v' || (latest.version + 1)::text);
    END LOOP;
    RAISE NOTICE '049: published %, existing versions, pins, evidence and custom definitions unchanged', published;
END
$migration$;

INSERT INTO schema_migrations (filename) VALUES ('049_clingen_successor.sql')
ON CONFLICT DO NOTHING;
