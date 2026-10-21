-- =============================================================================
-- 047: contradictory evidence disputes only when its Impact says so (#266)
-- =============================================================================
-- Owner decision (2026-10-22): a contradictory-evidence row forces DISPUTED only when its
-- Impact is "disputed" (the only disputing option of 046's field definition; there is no
-- refuting option, so no REFUTED override). "Note only" and "Review needed" rows never change
-- the class. Before, any filled row turned an 18-point Definitive curation into Disputed.
-- The ClinGen v1 snapshots get the new override where they embed 046's point model exactly
-- (custom models untouched), and the ClinGen working copies get the same point model (they
-- had none, so publishing them unchanged dropped the corrected model). 046 already synced
-- the working copies' field_definitions and ui_configuration to the v1 content.
-- Stored scores do not change here (SQL cannot run the scorer): after deploying, run once
--   cd backend && uv run python -m app.services.recompute_scores
-- The same sanctioned exception to 042's immutability as 046: as the table owner, the
-- trigger is disabled only for this update and re-enabled in the same transaction.
-- Idempotent (a re-run changes nothing); records itself in schema_migrations.
-- =============================================================================

DO $migration$
DECLARE
    old_model CONSTANT JSONB := $old$
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
            {"path": "case_level.autosomal_dominant_or_x_linked.predicted_or_proven_null", "rule": "case_row", "points_key": "proband_counted_points", "blank_at": 1.5, "range": [0, 3]},
            {"path": "case_level.autosomal_dominant_or_x_linked.other_variant_type", "rule": "case_row", "points_key": "proband_counted_points", "blank_at": 0.1, "range": [0, 1.5]},
            {"path": "case_level.autosomal_recessive.predicted_or_proven_null", "rule": "case_row", "points_key": "proband_counted_points", "blank_at": 1.5, "range": [0, 3]},
            {"path": "case_level.autosomal_recessive.other_variant_type", "rule": "case_row", "points_key": "proband_counted_points", "blank_at": 0.1, "range": [0, 3]}
          ]
        },
        {
          "key": "segregation",
          "cap": 3,
          "types": [{"path": "segregation", "rule": "segregation", "range": [0, 3]}]
        },
        {
          "key": "case_control",
          "cap": 12,
          "types": [
            {"path": "case_control.single_variant_analysis", "default": 0, "range": [0, 6]},
            {"path": "case_control.aggregate_variant_analysis", "default": 0, "range": [0, 6]}
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
            {"path": "function.biochemical_function", "default": 0.5, "range": [0, 2]},
            {"path": "function.protein_interaction", "default": 0.5, "range": [0, 2]},
            {"path": "function.expression", "default": 0.5, "range": [0, 2]}
          ]
        },
        {
          "key": "functional_alteration",
          "cap": 2,
          "types": [
            {"path": "functional_alteration.patient_cells", "default": 1, "range": [0, 2]},
            {"path": "functional_alteration.non_patient_cells", "default": 0.5, "range": [0, 1]}
          ]
        },
        {
          "key": "models_and_rescue",
          "cap": 4,
          "types": [
            {"path": "models.non_human_model_organism", "default": 2, "range": [0, 4]},
            {"path": "models.cell_culture_model", "default": 1, "range": [0, 2]},
            {"path": "rescue.human", "default": 2, "range": [0, 4]},
            {"path": "rescue.non_human_model_organism", "default": 2, "range": [0, 4]},
            {"path": "rescue.cell_culture", "default": 1, "range": [0, 2]},
            {"path": "rescue.patient_cells", "default": 1, "range": [0, 2]}
          ]
        }
      ]
    }
  ],
  "overrides": [
    {"when": "contradictory_evidence", "class": "disputed", "description": "Conflicting or contradictory evidence present, resulting in DISPUTED classification."}
  ],
  "bands": [
    {"class": "definitive", "min": 12, "requires": "replicated_over_time", "description": "Total score 12-18 points (Strong) with replication over time supports a DEFINITIVE gene-disease relationship."},
    {"class": "strong", "min": 12, "description": "Total score 12-18 points supports STRONG gene-disease relationship."},
    {"class": "moderate", "min": 7, "description": "Total score 7-11 points supports MODERATE gene-disease relationship."},
    {"class": "limited", "min": 0.1, "description": "Total score 1-6 points supports LIMITED gene-disease relationship."},
    {"class": "no_known", "min": 0, "description": "No evidence supporting a gene-disease relationship."},
    {"class": "disputed", "min": -1, "description": "Conflicting or contradictory evidence present, resulting in DISPUTED classification."},
    {"class": "refuted", "description": "Evidence refutes the gene-disease relationship."}
  ]
}
$old$::jsonb;
    new_model CONSTANT JSONB := jsonb_set(old_model, '{overrides}', $overrides$
[{"when": "contradictory_evidence", "field": "impact", "in": ["disputed"], "class": "disputed", "description": "Contradictory evidence with impact Disputed present, resulting in DISPUTED classification."}]
$overrides$::jsonb);
    corrected TEXT[];
    schemas TEXT[];
BEGIN
    ALTER TABLE methodology_versions DISABLE TRIGGER trigger_methodology_version_immutable;
    WITH fixed AS (
        UPDATE methodology_versions
        SET snapshot = jsonb_set(snapshot, '{scoring_configuration,point_model}', new_model)
        WHERE version = 1
          AND snapshot->'scoring_configuration'->>'engine' = 'clingen_sop_v11'
          AND snapshot->'scoring_configuration'->'point_model' = old_model
        RETURNING id
    )
    SELECT array_agg(id::text ORDER BY id) INTO corrected FROM fixed;
    ALTER TABLE methodology_versions ENABLE TRIGGER trigger_methodology_version_immutable;

    WITH fixed AS (
        UPDATE curation_schemas
        SET scoring_configuration = scoring_configuration
            || jsonb_build_object('point_model', new_model)
        WHERE schema_type = 'curation'
          AND scoring_configuration->>'engine' = 'clingen_sop_v11'
          AND (scoring_configuration->'point_model' IS NULL
               OR scoring_configuration->'point_model' = old_model)
        RETURNING name
    )
    SELECT array_agg(name ORDER BY name) INTO schemas FROM fixed;

    RAISE NOTICE '047: contradictory override by impact in ClinGen v1 snapshots %, working copies %',
        COALESCE(corrected, '{}'), COALESCE(schemas, '{}');
END
$migration$;

INSERT INTO schema_migrations (filename)
VALUES ('047_contradictory_by_impact.sql')
ON CONFLICT DO NOTHING;
