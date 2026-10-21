"""
ClinGen SOP v11 scoring engine: the point-model interpreter plus ClinGen item rules.

Caps, defaults and bands live in ``templates/clingen_sop_v11.json`` (or a schema's own
``scoring_configuration.point_model``). This module keeps only what a point model cannot
say: the case-row blank check, the LOD tables and the legacy flat-list evidence shapes.

References:
- https://www.clinicalgenome.org/docs/gene-disease-validity-sop-v11/
"""

import math
import re
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from typing import Any

from app.core.logging import get_logger, timed_operation

from .base import ScoringEngine, ScoringResult
from .evidence_items import case_row_has_content, has_content, rows
from .point_model import ItemRule, point_model, score, template

logger = get_logger(__name__)

# Row keys that are not entered evidence: row id, the PMID itself, preset case-row points
# ponytail: a row whose only entry is points (no other field) is not flagged for its PMID
_NOT_EVIDENCE_KEYS = {"id", "pmid", "proband_counted_points"}

ENGINE_NAME = "clingen_sop_v11"


def lod_to_points_sop11(lod_score: float) -> float:
    """SOP v11 segregation: LOD 0.6-1.2 -> 1, 1.2-2.4 -> 2, >= 2.4 -> 3 points."""
    if lod_score < 0.6:
        return 0.0
    if lod_score < 1.2:
        return 1.0
    if lod_score < 2.4:
        return 2.0
    return 3.0


def segregation_points(item: dict[str, Any]) -> float:
    """Entered points, else points from the LOD score, else from counted segregations."""
    if "points" in item:
        return float(item["points"] or 0)
    lod_score = item.get("lod_score")
    if lod_score is not None:
        return lod_to_points_sop11(float(lod_score))
    segregations = item.get("segregations_counted", 0)
    if segregations > 0:
        return lod_to_points_sop11(segregations * math.log10(2))
    return 0.0


def _case_row(type_def: dict[str, Any], item: dict[str, Any]) -> float | None:
    if not case_row_has_content(item, type_def["blank_at"]):
        return None  # untouched form row: points still at the new-row default
    return float(item.get(type_def.get("points_key", "points")) or 0)


RULES: dict[str, ItemRule] = {
    "case_row": _case_row,
    "segregation": lambda _type, item: segregation_points(item),
}


# --- Legacy flat-list evidence (evidence_category per item) ---


def legacy_case_level_points(item: dict[str, Any]) -> float:
    """Per proband: null 1.5 (+0.5 de novo), missense 0.1 (+0.4), other 0.5; +0.4 functional."""
    variant_type = item.get("variant_type", "").lower()
    proband_count = max(int(item.get("proband_count", 0)), 0)
    base = {"predicted_null": 1.5, "missense": 0.1}.get(variant_type, 0.5)
    points: float = base * proband_count
    if item.get("de_novo"):
        points += {"predicted_null": 0.5, "missense": 0.4}.get(
            variant_type, 0
        ) * proband_count
    if item.get("functional_alteration"):
        points += 0.4 * proband_count
    return points


def legacy_lod(family_count: int, inheritance: str) -> float:
    """Approximate LOD: 3 informative meioses per dominant/X-linked family, 2 per recessive."""
    meioses = {"autosomal_dominant": 3, "x_linked": 3, "autosomal_recessive": 2}
    if inheritance not in meioses:
        logger.warning(
            "Unknown inheritance pattern for segregation", inheritance=inheritance
        )
    if family_count < 1:
        return 0.0
    return family_count * meioses.get(inheritance, 0) * math.log10(2)


def legacy_lod_to_points(lod_score: float) -> float:
    """LOD < 3 -> 0, 3-5 -> 1, 5-7 -> 2, then +0.5 per LOD unit up to 7 points."""
    if lod_score < 3.0:
        return 0.0
    if lod_score < 5.0:
        return 1.0
    if lod_score < 7.0:
        return 2.0
    return min(7.0, 2.0 + (lod_score - 7.0) * 0.5)


def legacy_segregation_points(item: dict[str, Any]) -> float:
    lod_score = item.get("lod_score")
    if lod_score is None:
        inheritance = item.get("inheritance_pattern", "").lower()
        lod_score = legacy_lod(item.get("family_count", 0), inheritance)
    return legacy_lod_to_points(float(lod_score))


def _legacy_experimental_points(item: dict[str, Any]) -> float:
    category = item.get("evidence_category", "")
    if category == "models":
        system = item.get("model_system", "").lower()
        default = 4.0 if system in ["patient_cells", "animal_model"] else 2.0
        return float(item.get("points", default))
    if category == "rescue":
        return float(
            item.get("points", 2.0 if item.get("rescue_observed") else 0.0) or 0
        )
    return float(item.get("points", 1.0) or 0)


_LEGACY_CATEGORY = {
    "case_level": "case_level",
    "segregation": "segregation",
    "case_control": "case_control",
    "expression": "function",
    "protein_function": "function",
    "function": "function",
    # SOP v11: Models & Rescue is one category
    "models": "models_and_rescue",
    "rescue": "models_and_rescue",
}
_LEGACY_SECTION: dict[str, dict[str, Callable[[dict[str, Any]], float]]] = {
    "genetic_evidence": {
        "case_level": legacy_case_level_points,
        "segregation": legacy_segregation_points,
        # Curator-assigned points only; unscored studies count nothing
        "case_control": lambda item: float(item.get("computed_score") or 0),
    },
    "experimental_evidence": dict.fromkeys(
        ["function", "models_and_rescue"], _legacy_experimental_points
    ),
}


def legacy_points(section_key: str, items: list[Any]) -> dict[str, list[float]]:
    """{category: [item points]} for a legacy flat list; unknown categories are ignored."""
    scorers = _LEGACY_SECTION.get(section_key, {})
    out: dict[str, list[float]] = {}
    for item in rows(items):
        category = _LEGACY_CATEGORY.get(item.get("evidence_category", ""), "")
        if category in scorers:
            out.setdefault(category, []).append(scorers[category](item))
    return out


class ClinGenEngine(ScoringEngine):
    """ClinGen Gene-Disease Validity Scoring Engine (SOP v11), driven by a point model."""

    @property
    def name(self) -> str:
        return ENGINE_NAME

    @property
    def version(self) -> str:
        return "11.0.0"

    @staticmethod
    def _template() -> dict[str, Any]:
        model = template(ENGINE_NAME)
        assert model is not None  # shipped with the package
        return model

    def get_supported_verdicts(self) -> list[str]:
        return [band["class"] for band in self._template()["bands"]]

    def get_scoring_categories(self) -> list[str]:
        return [section["key"] for section in self._template()["sections"]]

    @timed_operation("clingen_scoring", warning_threshold_ms=500)
    def calculate_scores(
        self,
        evidence_data: dict[str, Any],
        schema_config: dict[str, Any],
        scope_context: dict[str, Any] | None = None,
    ) -> ScoringResult:
        """Score evidence with the config's point model (ClinGen template by default)."""
        model = point_model(schema_config) or self._template()
        result = score(model, evidence_data, RULES, legacy_points)
        scores = {f"{key}_total": value for key, value in result["sections"].items()}
        scores["total_score"] = result["total"]
        parts = ", ".join(
            f"{key.replace('_', ' ')} = {value:.1f} points"
            for key, value in result["sections"].items()
        )
        rationale = (
            f"Based on {model.get('name', 'the configured point model')} scoring "
            f"methodology: {parts}, total score = {result['total']:.1f} points. "
            + (result["description"] or "Classification could not be determined.")
        )
        warnings = self._check_warnings(
            evidence_data.get("genetic_evidence", []),
            evidence_data.get("experimental_evidence", []),
        )
        logger.info(
            "ClinGen scoring completed",
            total_score=result["total"],
            classification=result["class"],
            warnings_count=len(warnings),
        )
        return ScoringResult(
            scores=scores,
            total_score=result["total"],
            verdict=result["class"],
            verdict_rationale=rationale,
            evidence_breakdown={"trace": result["trace"]},
            warnings=warnings,
            metadata={
                "sop_version": "v11",
                "engine_version": self.version,
                "calculated_at": datetime.now(UTC).isoformat(),
                "scope_context": scope_context or {},
            },
        )

    def _check_warnings(
        self,
        genetic_evidence: list[dict[str, Any]],
        experimental_evidence: list[dict[str, Any]] | dict[str, Any],
    ) -> list[str]:
        """Check for potential issues or warnings in evidence data

        Args:
            genetic_evidence: List of genetic evidence items
            experimental_evidence: Experimental evidence (list or nested dict)

        Returns:
            List of warning messages
        """
        warnings = []

        # Check genetic evidence
        warnings.extend(self._check_genetic_evidence_warnings(genetic_evidence))

        # No "no/too few evidence" hints: in-progress work, and the score panel shows it

        missing_pmid_count = self._count_missing_pmids(
            genetic_evidence, experimental_evidence
        )
        if missing_pmid_count > 0:
            warnings.append(
                f"{missing_pmid_count} evidence item(s) with invalid or missing PMID"
            )

        return warnings

    def _check_genetic_evidence_warnings(
        self, genetic_evidence: list[dict[str, Any]] | dict[str, Any]
    ) -> list[str]:
        """Check genetic evidence for warnings.

        Handles both legacy flat list and new nested SOP v11 formats.
        """
        warnings = []

        # Handle nested format (SOP v11)
        if isinstance(genetic_evidence, dict):
            return self._check_genetic_evidence_warnings_nested(genetic_evidence)

        # Legacy flat list format: segregation needs a LOD score or family count
        segregation_items = [
            item
            for item in rows(genetic_evidence)
            if item.get("evidence_category") == "segregation"
        ]
        for seg_item in segregation_items:
            if "lod_score" not in seg_item and "family_count" not in seg_item:
                warnings.append(
                    "Segregation evidence missing both lod_score and family_count"
                )
                break

        return warnings

    def _check_genetic_evidence_warnings_nested(
        self, genetic_evidence: dict[str, Any]
    ) -> list[str]:
        """Check nested genetic evidence for warnings."""
        warnings = []

        # Check segregation evidence
        segregation_items = rows(genetic_evidence.get("segregation"))
        if isinstance(segregation_items, list):
            for seg_item in segregation_items:
                has_score = (
                    "lod_score" in seg_item
                    or "points" in seg_item
                    or "segregations_counted" in seg_item
                )
                if not has_score:
                    warnings.append(
                        "Segregation evidence missing lod_score, points, "
                        "or segregations_counted"
                    )
                    break

        return warnings

    def _count_missing_pmids(
        self,
        genetic_evidence: list[dict[str, Any]],
        experimental_evidence: list[dict[str, Any]] | dict[str, Any],
    ) -> int:
        """Count evidence items with missing or invalid PMIDs."""
        # Genetic and experimental evidence: nested SOP v11 dict or legacy list
        items = [
            *self._iter_evidence_items(genetic_evidence),
            *self._iter_evidence_items(experimental_evidence),
        ]
        return sum(1 for item in items if self._lacks_valid_pmid(item))

    def _lacks_valid_pmid(self, item: dict[str, Any]) -> bool:
        """A filled-in but invalid PMID, or a row with other content but no PMID.

        A freshly added row (only its id and preset points) is not flagged yet.
        """
        pmid = str(item.get("pmid") or "").strip()
        if pmid:
            return not self._is_valid_pmid(pmid)
        rest = {k: v for k, v in item.items() if k not in _NOT_EVIDENCE_KEYS}
        return has_content(rest)

    @classmethod
    def _iter_evidence_items(cls, node: Any) -> Iterator[dict[str, Any]]:
        """Yield evidence item dicts from a flat list or a nested SOP v11 dict."""
        if isinstance(node, list):
            for item in node:
                if isinstance(item, dict):
                    yield item
        elif isinstance(node, dict):
            for child in node.values():
                yield from cls._iter_evidence_items(child)

    def _is_valid_pmid(self, pmid: Any) -> bool:
        """PMID as the forms accept it (pmid_format): optional "PMID:" prefix, 1-9 digits."""
        return re.fullmatch(r"(PMID:?\s*)?\d{1,9}", str(pmid).strip()) is not None

    def validate_evidence(  # noqa: C901
        self, evidence_data: dict[str, Any], schema_config: dict[str, Any]
    ) -> list[str]:
        """Validate evidence data structure and required fields

        Supports both nested (SOP v11) and legacy flat list formats.

        Args:
            evidence_data: Evidence items organized by category
            schema_config: Schema configuration (unused but required by interface)

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        genetic_evidence = evidence_data.get("genetic_evidence", [])
        experimental_evidence = evidence_data.get("experimental_evidence", {})

        # Validate genetic evidence items
        if not genetic_evidence:
            errors.append("At least one genetic evidence item is required")

        for idx, item in enumerate(genetic_evidence):
            category = item.get("evidence_category")

            if not category:
                errors.append(
                    f"Genetic evidence item {idx + 1}: Missing evidence_category"
                )
                continue

            # Validate case-level evidence
            if category == "case_level":
                if "proband_count" not in item:
                    errors.append(
                        f"Case-level evidence {idx + 1}: Missing proband_count"
                    )
                if "variant_type" not in item:
                    errors.append(
                        f"Case-level evidence {idx + 1}: Missing variant_type"
                    )

                variant_type = item.get("variant_type", "").lower()
                if variant_type not in ["predicted_null", "missense", "other"]:
                    errors.append(
                        f"Case-level evidence {idx + 1}: Invalid variant_type "
                        f"(must be predicted_null, missense, or other)"
                    )

            # Validate segregation evidence
            elif category == "segregation":
                if "lod_score" not in item and "family_count" not in item:
                    errors.append(
                        f"Segregation evidence {idx + 1}: Must provide either "
                        "lod_score or family_count"
                    )

                if "inheritance_pattern" not in item:
                    errors.append(
                        f"Segregation evidence {idx + 1}: Missing inheritance_pattern"
                    )

            # Validate case-control evidence
            elif category == "case_control":
                # Case-control requires at least a computed score
                if "computed_score" not in item:
                    errors.append(
                        f"Case-control evidence {idx + 1}: Missing computed_score"
                    )

        # Validate experimental evidence - handle both formats
        if isinstance(experimental_evidence, list):
            # Legacy flat list format
            errors.extend(
                self._validate_experimental_evidence_legacy(experimental_evidence)
            )
        elif isinstance(experimental_evidence, dict):
            # New nested format (SOP v11)
            errors.extend(
                self._validate_experimental_evidence_nested(experimental_evidence)
            )

        return errors

    def _validate_experimental_evidence_legacy(
        self, evidence_items: list[dict[str, Any]]
    ) -> list[str]:
        """Validate legacy flat list experimental evidence format."""
        errors = []

        for idx, item in enumerate(evidence_items):
            category = item.get("evidence_category")

            if not category:
                errors.append(
                    f"Experimental evidence item {idx + 1}: Missing evidence_category"
                )
                continue

            # Validate category is one of the expected types
            valid_categories = [
                "expression",
                "protein_function",
                "function",
                "models",
                "rescue",
            ]
            if category not in valid_categories:
                errors.append(
                    f"Experimental evidence {idx + 1}: Invalid category "
                    f"(must be one of: {', '.join(valid_categories)})"
                )

            # Model system validation for categories that use it
            if (
                category in ["expression", "protein_function", "function", "models"]
                and "model_system" not in item
            ):
                errors.append(f"Experimental evidence {idx + 1}: Missing model_system")

            # Rescue evidence validation
            if category == "rescue" and "rescue_observed" not in item:
                errors.append(
                    f"Rescue evidence {idx + 1}: Missing rescue_observed field"
                )

        return errors

    def _validate_experimental_evidence_nested(
        self, evidence_data: dict[str, Any]
    ) -> list[str]:
        """Validate nested SOP v11 experimental evidence format."""
        errors = []

        # Define expected subcategories for each main category
        expected_structure = {
            "function": ["biochemical_function", "protein_interaction", "expression"],
            "functional_alteration": ["patient_cells", "non_patient_cells"],
            "models": ["non_human_model_organism", "cell_culture_model"],
            "rescue": [
                "human",
                "non_human_model_organism",
                "cell_culture",
                "patient_cells",
            ],
        }

        for category, subcategories in expected_structure.items():
            cat_data = evidence_data.get(category, {})
            if not isinstance(cat_data, dict):
                continue

            for subcategory in subcategories:
                items = cat_data.get(subcategory, [])
                if not isinstance(items, list):
                    continue

                for idx, item in enumerate(items):
                    item_label = f"{category}.{subcategory}[{idx}]"

                    # Validate PMID
                    if "pmid" not in item:
                        errors.append(f"{item_label}: Missing PMID")

                    # Validate points
                    if "points" not in item:
                        errors.append(f"{item_label}: Missing points value")

                    # Validate rationale
                    if "rationale" not in item:
                        errors.append(f"{item_label}: Missing rationale")

        return errors

    def supports_schema(self, schema_name: str, schema_version: str) -> bool:
        """Check if engine supports a specific schema version

        Args:
            schema_name: Name of the schema
            schema_version: Version string

        Returns:
            True if this engine supports the schema
        """
        return schema_name.startswith("ClinGen_SOP") and schema_version.startswith(
            "11."
        )
