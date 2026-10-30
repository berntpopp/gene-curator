"""Which evidence_data keys an LLM run may send (#489, #534). Pure: no database access.

Shared = the seeded schemas' evidence facts (SHARED_EVIDENCE_KEYS) plus every field a
schema flags `llm_share: true`, never a curator judgement key (JUDGEMENT_KEYS), so the
second view stays blind (#464). Anything else, e.g. a curator_name a custom schema adds,
is dropped; schema validation warns about such fields (schema_rules).
"""

from collections.abc import Iterator
from typing import Any

# Curator judgement and conclusion; never sent, and llm_share on one is refused.
JUDGEMENT_KEYS = frozenset(
    {
        "decision",
        "evidence_quality",
        "evidence_summary",
        "explanation",
        "impact",
        "inheritance_consistency",
        "phenotype_match",
        "points",
        "preliminary_verdict",
        "proband_counted_points",
        "proband_not_counted_points",
        "rationale",
        "replicated_over_time",
        "score_status",
        "segregations_counted",
        "segregations_not_counted",
        "study_design_strength",
    }
)

SHARED_EVIDENCE_KEYS = frozenset(
    {
        "age",
        "aggregate_variant_analysis",
        "analysis_type",
        "assay_method",
        "autosomal_dominant_or_x_linked",
        "autosomal_recessive",
        "biochemical_function",
        "case_control",
        "case_control_data",
        "case_level",
        "case_level_data",
        "cases_total",
        "cases_with_variant",
        "cases_with_variants",
        "cell_culture",
        "cell_culture_model",
        "cell_line",
        "cell_type",
        "clinical_assessment",
        "confidence_interval",
        "consanguinity",
        "contradictory_evidence",
        "controls_total",
        "controls_with_variant",
        "controls_with_variants",
        "de_novo",
        "description",
        "disease_mechanism_relevance",
        "disease_name",
        "disease_relevance",
        "disease_tissue_relevance",
        "entity_definition",
        "ethnicity",
        "evidence_type",
        "experimental_category",
        "experimental_evidence",
        "expression",
        "expression_method",
        "family_label",
        "function",
        "functional_alteration",
        "functional_data",
        "functional_effect",
        "gene_function_description",
        "genetic_evidence",
        "human",
        "human_phenotype_match",
        "inheritance_pattern_match",
        "initial_assessment",
        "interacting_protein",
        "interaction_method",
        "key_references",
        "label",
        "literature_review",
        "literature_search_strategy",
        "lod_score",
        "lod_score_method",
        "lumping_splitting",
        "methods",
        "mode_of_inheritance",
        "model_type",
        "models",
        "modification",
        "mondo_id",
        "non_human_model_organism",
        "non_patient_cells",
        "odds_ratio",
        "organism",
        "other_variant_type",
        "p_value",
        "paternity_maternity_confirmed",
        "patient_cells",
        "pedigree_description",
        "phase_confirmed",
        "phenotype_observed",
        "phenotype_rescued",
        "phenotypes",
        "pmid",
        "predicted_or_proven_null",
        "previous_testing",
        "proband_label",
        "proband_with_variant",
        "protein_interaction",
        "relationship_type",
        "rescue",
        "rescue_extent",
        "rescue_method",
        "sections",
        "segregation",
        "segregation_data",
        "segregations",
        "sex",
        "single_variant_analysis",
        "statistical_test",
        "study_label",
        "tissue_organ",
        "variant",
        "variant_1",
        "variant_2",
        "variant_engineered",
        "variant_tested",
        "variant_type",
        "zygosity",
    }
)


def field_specs(
    fields: Any, path: str = "field_definitions"
) -> Iterator[tuple[str, str, dict[str, Any]]]:
    """(JSON path, key, config) of every field at any depth: flat maps, the seeded
    `sections` list shape, list-shaped definitions, properties, items and table columns."""
    if isinstance(fields, dict):
        pairs = list(fields.items())
    elif isinstance(fields, list):
        pairs = [
            (str(f.get("id") or f.get("name") or ""), f)
            for f in fields
            if isinstance(f, dict)
        ]
    else:
        return
    for i, (name, cfg) in enumerate(pairs):
        here = f"{path}.{name}" if isinstance(fields, dict) else f"{path}[{i}]"
        if name == "sections" and isinstance(cfg, list):
            for j, section in enumerate(cfg):
                if isinstance(section, dict):
                    yield from field_specs(section.get("fields"), f"{here}[{j}].fields")
            continue
        if not name or not isinstance(cfg, dict):
            continue
        yield here, name, cfg
        yield from field_specs(cfg.get("properties"), f"{here}.properties")
        items = cfg.get("items")
        if isinstance(items, dict):
            yield from field_specs(items.get("properties"), f"{here}.items.properties")
        yield from field_specs(cfg.get("columns"), f"{here}.columns")


def _flags(fields: Any) -> tuple[set[str], set[str]]:
    specs = list(field_specs(fields))
    flagged = {name for _, name, cfg in specs if cfg.get("llm_share") is True}
    withheld = {name for _, name, cfg in specs if cfg.get("llm_share") is False}
    return flagged, withheld


def shared_keys(fields: Any) -> frozenset[str]:
    """The keys a run sends for a curation made with these field definitions.

    Explicit llm_share: false withholds even a seeded evidence key.
    """
    flagged, withheld = _flags(fields)
    return (SHARED_EVIDENCE_KEYS | flagged) - withheld - JUDGEMENT_KEYS


_DROP = object()


def _view(
    value: Any, keys: frozenset[str], blocked: frozenset[str], shared: bool
) -> Any:
    if isinstance(value, dict):
        kept = {
            k: r
            for k, v in value.items()
            if k not in blocked
            and (r := _view(v, keys, blocked, k in keys)) is not _DROP
        }
        return kept if kept or shared else _DROP
    if isinstance(value, list):
        rows = [r for v in value if (r := _view(v, keys, blocked, shared)) is not _DROP]
        return rows if rows or shared else _DROP
    return value if shared else _DROP


def shared_view(evidence: dict[str, Any], fields: Any) -> dict[str, Any]:
    """`evidence` with only shared leaves, at any depth. An unshared container (a custom
    section or table key) survives when a descendant is shared (#534); judgement and
    llm_share: false keys are dropped with their whole subtree."""
    _, withheld = _flags(fields)
    blocked = frozenset(withheld) | JUDGEMENT_KEYS
    result: dict[str, Any] = _view(evidence, shared_keys(fields), blocked, True)
    return result


def check_llm_share(fields: Any) -> list[tuple[str, str, str]]:
    """Schema diagnostics: llm_share on a judgement key is an error, and so is one key
    name shared in one place and not another (sharing is by name at every depth); fields
    a run would drop get one warning, so no drop is silent."""
    out: list[tuple[str, str, str]] = []
    dropped: list[str] = []
    first: dict[str, bool] = {}  # key name -> shared where first defined
    for path, name, cfg in field_specs(fields):
        share = cfg.get("llm_share", False)
        sent = share is True or (
            "llm_share" not in cfg and name in SHARED_EVIDENCE_KEYS
        )
        if first.setdefault(name, sent) != sent and name not in JUDGEMENT_KEYS:
            msg = (
                f"'{name}' is shared with LLM runs in one place and not in another; "
                f"sharing is by key name at every depth, so flag every '{name}' the same"
            )
            out.append(("error", f"{path}.llm_share", msg))
        if not isinstance(share, bool):
            out.append(
                ("error", f"{path}.llm_share", "llm_share must be true or false")
            )
        elif share and name in JUDGEMENT_KEYS:
            msg = f"'{name}' is curator judgement and is never shared with LLM runs"
            out.append(("error", f"{path}.llm_share", msg))
        elif not share and name not in SHARED_EVIDENCE_KEYS | JUDGEMENT_KEYS:
            dropped.append(name)
    if dropped:
        msg = "Not sent to LLM runs (set llm_share: true to send): " + ", ".join(
            sorted(set(dropped))
        )
        out.append(("warning", "field_definitions", msg))
    return out
