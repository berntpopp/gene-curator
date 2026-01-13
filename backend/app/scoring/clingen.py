"""
ClinGen Standard Operating Procedure v11 scoring engine.

Implements complete gene-disease validity evidence scoring per ClinGen SOP v11
(September 2024) including:
- Case-level evidence with variant type bonuses
- Segregation evidence with LOD score calculations
- Case-control evidence
- Experimental evidence (expression, function, models, rescue)

References:
- https://www.clinicalgenome.org/docs/gene-disease-validity-sop-v11/
"""

import math
from datetime import UTC, datetime
from typing import Any, Final

from app.core.logging import get_logger, timed_operation

from .base import ScoringEngine, ScoringResult

logger = get_logger(__name__)


class ClinGenEngine(ScoringEngine):
    """ClinGen Gene-Disease Validity Scoring Engine (SOP v11)

    This engine implements the complete ClinGen scoring methodology with:
    - Genetic evidence scoring (max 12 points)
    - Experimental evidence scoring (max 6 points)
    - Total maximum score: 18 points
    - Classification thresholds: Definitive (12+), Strong (7+), Moderate (2+), Limited (0.1+)
    """

    # Maximum scores per category (SOP v11 specifications)
    MAX_GENETIC_SCORE: Final[float] = 12.0
    MAX_EXPERIMENTAL_SCORE: Final[float] = 6.0
    MAX_TOTAL_SCORE: Final[float] = 18.0

    # Genetic evidence category limits
    MAX_CASE_LEVEL_SCORE: Final[float] = 12.0
    MAX_SEGREGATION_SCORE: Final[float] = (
        3.0  # ClinGen SOP v11: max 3 points for segregation
    )
    MAX_CASE_CONTROL_SCORE: Final[float] = 6.0

    # Experimental evidence category limits (SOP v11)
    MAX_FUNCTION_SCORE: Final[float] = (
        2.0  # biochemical + protein interaction + expression
    )
    MAX_FUNCTIONAL_ALTERATION_SCORE: Final[float] = 2.0  # patient + non-patient cells
    MAX_MODELS_SCORE: Final[float] = 4.0  # organism + cell culture
    MAX_RESCUE_SCORE: Final[float] = (
        4.0  # human + organism + cell culture + patient cells
    )

    # Classification thresholds
    THRESHOLDS: Final[dict[str, float]] = {
        "definitive": 12.0,
        "strong": 7.0,
        "moderate": 2.0,
        "limited": 0.1,
        "no_known": 0.0,
        "disputed": -1.0,
        "refuted": -2.0,
    }

    @property
    def name(self) -> str:
        return "clingen_sop_v11"

    @property
    def version(self) -> str:
        return "11.0.0"

    def get_supported_verdicts(self) -> list[str]:
        return [
            "definitive",
            "strong",
            "moderate",
            "limited",
            "no_known",
            "disputed",
            "refuted",
        ]

    def get_scoring_categories(self) -> list[str]:
        return ["genetic_evidence", "experimental_evidence"]

    @timed_operation("clingen_scoring", warning_threshold_ms=500)
    def calculate_scores(
        self,
        evidence_data: dict[str, Any],
        schema_config: dict[str, Any],
        scope_context: dict[str, Any] | None = None,
    ) -> ScoringResult:
        """Calculate ClinGen SOP v11 scores with complete evidence categorization

        Args:
            evidence_data: Evidence items organized by category
            schema_config: Schema configuration (unused but required by interface)
            scope_context: Optional scope-specific context

        Returns:
            ScoringResult with complete score breakdown and classification
        """
        genetic_evidence = evidence_data.get("genetic_evidence", [])
        experimental_evidence = evidence_data.get("experimental_evidence", [])

        logger.info(
            "Calculating ClinGen scores",
            genetic_items=len(genetic_evidence),
            experimental_items=len(experimental_evidence),
        )

        # Calculate genetic evidence score (max 12 points)
        genetic_score, genetic_details = self._calculate_genetic_evidence(
            genetic_evidence
        )

        # Calculate experimental evidence score (max 6 points)
        experimental_score, experimental_details = (
            self._calculate_experimental_evidence(experimental_evidence)
        )

        # Total score (max 18 points)
        total_score = min(
            genetic_score + experimental_score,
            self.MAX_TOTAL_SCORE,
        )

        # Determine classification
        classification = self._classify(total_score)

        # Generate rationale
        rationale = self._generate_rationale(
            genetic_score, experimental_score, total_score, classification
        )

        # Check for warnings
        warnings = self._check_warnings(genetic_evidence, experimental_evidence)

        logger.info(
            "ClinGen scoring completed",
            total_score=total_score,
            genetic_score=genetic_score,
            experimental_score=experimental_score,
            classification=classification,
            warnings_count=len(warnings),
        )

        return ScoringResult(
            scores={
                "genetic_evidence_total": genetic_score,
                "experimental_evidence_total": experimental_score,
                "total_score": total_score,
            },
            total_score=total_score,
            verdict=classification,
            verdict_rationale=rationale,
            evidence_breakdown={
                "genetic_evidence_details": genetic_details,
                "experimental_evidence_details": experimental_details,
            },
            warnings=warnings,
            metadata={
                "sop_version": "v11",
                "engine_version": self.version,
                "calculated_at": datetime.now(UTC).isoformat(),
                "scope_context": scope_context or {},
            },
        )

    def _calculate_genetic_evidence(
        self, evidence_data: list[dict[str, Any]] | dict[str, Any]
    ) -> tuple[float, dict[str, Any]]:
        """Calculate genetic evidence score (max 12 points)

        Processes three categories:
        - Case-level evidence (variants in probands)
        - Segregation evidence (family studies with LOD scores)
        - Case-control evidence (population studies)

        Supports both legacy flat list format and new SOP v11 nested format.

        Args:
            evidence_data: Genetic evidence - either nested dict (SOP v11)
                          or flat list (legacy format)

        Returns:
            Tuple of (total_score, detailed_breakdown)
        """
        # Handle both nested (new) and flat list (legacy) formats
        if isinstance(evidence_data, list):
            return self._calculate_genetic_evidence_legacy(evidence_data)

        # New nested format per ClinGen SOP v11
        case_level_score = 0.0
        segregation_score = 0.0
        case_control_score = 0.0

        case_level_details: dict[str, Any] = {}
        segregation_details: list[dict[str, Any]] = []
        case_control_details: dict[str, Any] = {}

        # --- Case-Level Evidence ---
        case_level_data = evidence_data.get("case_level", {})
        if isinstance(case_level_data, dict):
            # AD/X-linked evidence
            ad_xl_data = case_level_data.get("autosomal_dominant_or_x_linked", {})
            ad_xl_score, ad_xl_details = self._score_case_level_nested(
                ad_xl_data, "AD/X-linked"
            )

            # Autosomal Recessive evidence
            ar_data = case_level_data.get("autosomal_recessive", {})
            ar_score, ar_details = self._score_case_level_nested(ar_data, "AR")

            case_level_score = ad_xl_score + ar_score
            case_level_details = {
                "autosomal_dominant_or_x_linked": ad_xl_details,
                "autosomal_recessive": ar_details,
                "total": min(case_level_score, self.MAX_CASE_LEVEL_SCORE),
            }

        # --- Segregation Evidence ---
        segregation_items = evidence_data.get("segregation", [])
        if isinstance(segregation_items, list):
            for item in segregation_items:
                score = self._score_segregation_nested(item)
                segregation_score += score
                segregation_details.append({**item, "computed_score": score})

        # --- Case-Control Evidence ---
        case_control_data = evidence_data.get("case_control", {})
        if isinstance(case_control_data, dict):
            # Single variant analysis
            single_items = case_control_data.get("single_variant_analysis", [])
            single_score = sum(float(item.get("points", 0)) for item in single_items)

            # Aggregate variant analysis
            aggregate_items = case_control_data.get("aggregate_variant_analysis", [])
            aggregate_score = sum(
                float(item.get("points", 0)) for item in aggregate_items
            )

            # Max 6 from either method (not combined)
            case_control_score = max(single_score, aggregate_score)
            case_control_details = {
                "single_variant_analysis": {
                    "items": single_items,
                    "score": single_score,
                },
                "aggregate_variant_analysis": {
                    "items": aggregate_items,
                    "score": aggregate_score,
                },
                "total": min(case_control_score, self.MAX_CASE_CONTROL_SCORE),
            }

        # Apply category-specific limits
        case_level_score = min(case_level_score, self.MAX_CASE_LEVEL_SCORE)
        segregation_score = min(segregation_score, self.MAX_SEGREGATION_SCORE)
        case_control_score = min(case_control_score, self.MAX_CASE_CONTROL_SCORE)

        # Total genetic score (overall max 12)
        total = min(
            case_level_score + segregation_score + case_control_score,
            self.MAX_GENETIC_SCORE,
        )

        details = {
            "case_level_score": case_level_score,
            "segregation_score": segregation_score,
            "case_control_score": case_control_score,
            "total_genetic_score": total,
            "case_level_details": case_level_details,
            "segregation_items": segregation_details,
            "case_control_details": case_control_details,
        }

        return total, details

    def _score_case_level_nested(
        self, inheritance_data: dict[str, Any], inheritance_type: str
    ) -> tuple[float, dict[str, Any]]:
        """Score case-level evidence from nested SOP v11 format.

        Args:
            inheritance_data: Dict with predicted_or_proven_null and other_variant_type
            inheritance_type: 'AD/X-linked' or 'AR' for logging

        Returns:
            Tuple of (score, details)
        """
        null_score = 0.0
        other_score = 0.0
        null_items: list[dict[str, Any]] = []
        other_items: list[dict[str, Any]] = []

        # Predicted/proven null variants
        null_variants = inheritance_data.get("predicted_or_proven_null", [])
        for item in null_variants:
            # Use proband_counted_points from the item (already scored by user)
            points = float(item.get("proband_counted_points", 1.5))
            null_score += points
            null_items.append({**item, "computed_score": points})

        # Other variant types
        other_variants = inheritance_data.get("other_variant_type", [])
        for item in other_variants:
            points = float(item.get("proband_counted_points", 0.1))
            other_score += points
            other_items.append({**item, "computed_score": points})

        total = null_score + other_score

        logger.debug(
            "Case-level scoring",
            inheritance=inheritance_type,
            null_count=len(null_items),
            null_score=null_score,
            other_count=len(other_items),
            other_score=other_score,
            total=total,
        )

        return total, {
            "predicted_or_proven_null": {
                "items": null_items,
                "score": null_score,
            },
            "other_variant_type": {
                "items": other_items,
                "score": other_score,
            },
            "total": total,
        }

    def _score_segregation_nested(self, item: dict[str, Any]) -> float:
        """Score segregation evidence from nested SOP v11 format.

        Args:
            item: Segregation evidence item with points or lod_score

        Returns:
            Points awarded
        """
        # If points provided directly, use that
        if "points" in item:
            return float(item["points"])

        # Otherwise calculate from LOD score
        lod_score = item.get("lod_score")
        if lod_score is not None:
            return self._lod_to_points_sop11(float(lod_score))

        # Fall back to counting segregations
        segregations = item.get("segregations_counted", 0)
        if segregations > 0:
            # Approximate LOD from segregation count
            lod = segregations * math.log10(2)
            return self._lod_to_points_sop11(lod)

        return 0.0

    def _lod_to_points_sop11(self, lod_score: float) -> float:
        """Convert LOD score to points per SOP v11 thresholds.

        SOP v11 segregation scoring:
        - LOD 0.6-1.2: 1 point
        - LOD 1.2-2.4: 2 points
        - LOD > 2.4: 3 points (max)

        Args:
            lod_score: Calculated or provided LOD score

        Returns:
            Points (0-3)
        """
        if lod_score < 0.6:
            return 0.0
        elif lod_score < 1.2:
            return 1.0
        elif lod_score < 2.4:
            return 2.0
        else:
            return 3.0

    def _calculate_genetic_evidence_legacy(
        self, evidence_items: list[dict[str, Any]]
    ) -> tuple[float, dict[str, Any]]:
        """Calculate genetic evidence from legacy flat list format.

        Kept for backwards compatibility with existing curations.

        Args:
            evidence_items: Flat list of evidence items with evidence_category field

        Returns:
            Tuple of (total_score, detailed_breakdown)
        """
        case_level_score = 0.0
        segregation_score = 0.0
        case_control_score = 0.0

        case_level_items = []
        segregation_items = []
        case_control_items = []

        for item in evidence_items:
            category = item.get("evidence_category", "")

            if category == "case_level":
                score = self._score_case_level(item)
                case_level_score += score
                case_level_items.append({**item, "computed_score": score})

            elif category == "segregation":
                score = self._score_segregation(item)
                segregation_score += score
                segregation_items.append({**item, "computed_score": score})

            elif category == "case_control":
                score = self._score_case_control(item)
                case_control_score += score
                case_control_items.append({**item, "computed_score": score})

        # Apply category-specific limits
        case_level_score = min(case_level_score, self.MAX_CASE_LEVEL_SCORE)
        segregation_score = min(segregation_score, self.MAX_SEGREGATION_SCORE)
        case_control_score = min(case_control_score, self.MAX_CASE_CONTROL_SCORE)

        # Total genetic score (overall max 12)
        total = min(
            case_level_score + segregation_score + case_control_score,
            self.MAX_GENETIC_SCORE,
        )

        details = {
            "case_level_score": case_level_score,
            "segregation_score": segregation_score,
            "case_control_score": case_control_score,
            "total_genetic_score": total,
            "case_level_items": case_level_items,
            "segregation_items": segregation_items,
            "case_control_items": case_control_items,
        }

        return total, details

    def _score_case_level(self, item: dict[str, Any]) -> float:
        """Score case-level genetic evidence with variant type and modifier bonuses

        Scoring rules (SOP v11):
        - Predicted null variant: 1.5 points per proband
        - Missense variant: 0.1 points per proband
        - Other variant types: 0.5 points per proband

        Modifiers:
        - De novo: +0.5 (predicted null), +0.4 (missense)
        - Functional alteration: +0.4 (all types)

        Args:
            item: Case-level evidence item

        Returns:
            Computed score for this evidence item
        """
        variant_type = item.get("variant_type", "").lower()
        proband_count = max(int(item.get("proband_count", 0)), 0)
        de_novo = bool(item.get("de_novo", False))
        functional_alteration = bool(item.get("functional_alteration", False))

        # Base score per proband based on variant type
        base_score: float
        if variant_type == "predicted_null":
            base_score = 1.5
        elif variant_type == "missense":
            base_score = 0.1
        else:
            base_score = 0.5  # Other variant types

        score: float = base_score * proband_count

        # De novo bonuses
        if de_novo:
            if variant_type == "predicted_null":
                score += 0.5 * proband_count
            elif variant_type == "missense":
                score += 0.4 * proband_count

        # Functional alteration bonus
        if functional_alteration:
            score += 0.4 * proband_count

        return score

    def _score_segregation(self, item: dict[str, Any]) -> float:
        """Score segregation evidence using LOD scores

        If LOD score is provided, use it directly. Otherwise, calculate from
        family count using inheritance pattern.

        LOD to points conversion (SOP v11):
        - LOD < 3.0: 0 points
        - LOD 3.0-4.99: 1 point
        - LOD 5.0-6.99: 2 points
        - LOD ≥ 7.0: up to 7 points (maximum)

        Args:
            item: Segregation evidence item

        Returns:
            Points awarded for segregation evidence
        """
        family_count = item.get("family_count", 0)
        lod_score = item.get("lod_score")
        inheritance = item.get("inheritance_pattern", "").lower()

        # Use provided LOD score or calculate from family count
        if lod_score is not None:
            calculated_lod = float(lod_score)
        else:
            # Calculate LOD score based on inheritance pattern
            if inheritance in ["autosomal_dominant", "x_linked"]:
                calculated_lod = self._calculate_dominant_lod(family_count)
            elif inheritance == "autosomal_recessive":
                calculated_lod = self._calculate_recessive_lod(family_count)
            else:
                logger.warning(
                    "Unknown inheritance pattern for segregation",
                    inheritance=inheritance,
                )
                calculated_lod = 0.0

        # Convert LOD score to points
        return self._lod_to_points(calculated_lod, inheritance)

    def _calculate_dominant_lod(self, family_count: int) -> float:
        """Calculate LOD score for dominant/X-linked inheritance

        Formula: LOD = log10(1 / 0.5^n) where n = number of segregations
        Simplified assumption: ~3 informative meioses per family

        Args:
            family_count: Number of families with segregation data

        Returns:
            Calculated LOD score
        """
        if family_count < 1:
            return 0.0

        # Approximate: 3 informative meioses per family
        segregations = family_count * 3

        # LOD = log10(1 / 0.5^n)
        # This simplifies to: LOD = n * log10(2) ≈ n * 0.301
        lod_score = segregations * math.log10(2)

        logger.debug(
            "Dominant LOD calculation",
            family_count=family_count,
            segregations=segregations,
            lod_score=round(lod_score, 2),
        )

        return lod_score

    def _calculate_recessive_lod(self, family_count: int) -> float:
        """Calculate LOD score for recessive inheritance

        Formula similar to dominant but with different segregation assumptions
        Simplified assumption: ~2 informative meioses per family

        Args:
            family_count: Number of families with segregation data

        Returns:
            Calculated LOD score
        """
        if family_count < 1:
            return 0.0

        # Approximate: 2 informative meioses per family for recessive
        segregations = family_count * 2
        lod_score = segregations * math.log10(2)

        logger.debug(
            "Recessive LOD calculation",
            family_count=family_count,
            segregations=segregations,
            lod_score=round(lod_score, 2),
        )

        return lod_score

    def _lod_to_points(self, lod_score: float, inheritance: str) -> float:
        """Convert LOD score to points per SOP v11

        Thresholds:
        - LOD < 3.0: 0 points (not significant)
        - LOD 3.0-4.99: 1 point
        - LOD 5.0-6.99: 2 points
        - LOD ≥ 7.0: up to 7 points maximum

        Args:
            lod_score: Calculated or provided LOD score
            inheritance: Inheritance pattern (for logging)

        Returns:
            Points awarded (0-7)
        """
        if lod_score < 3.0:
            points = 0.0
        elif lod_score < 5.0:
            points = 1.0
        elif lod_score < 7.0:
            points = 2.0
        else:
            # Progressive increase up to maximum of 7 points
            # Beyond LOD 7.0: add 0.5 points per LOD unit
            points = min(7.0, 2.0 + (lod_score - 7.0) * 0.5)

        logger.debug(
            "LOD to points conversion",
            lod_score=round(lod_score, 2),
            inheritance=inheritance,
            points=round(points, 2),
        )

        return points

    def _score_case_control(self, item: dict[str, Any]) -> float:
        """Score case-control evidence

        Simplified for MVP: Uses provided score or default.
        Full implementation would analyze p-values, odds ratios, and study quality.

        Args:
            item: Case-control evidence item

        Returns:
            Points awarded (max 6 per SOP v11)
        """
        # Use explicitly provided score if available
        if "computed_score" in item:
            return float(item["computed_score"])

        # Default conservative score for case-control data
        # TODO: Implement full scoring based on p-value and odds ratio
        return 3.0

    def _calculate_experimental_evidence(
        self, evidence_data: list[dict[str, Any]] | dict[str, Any]
    ) -> tuple[float, dict[str, Any]]:
        """Calculate experimental evidence score (max 6 points)

        Per ClinGen SOP v11, processes four main categories:
        - Function (max 2 pts): biochemical function, protein interaction, expression
        - Functional Alteration (max 2 pts): patient cells, non-patient cells
        - Models (max 4 pts): non-human organism, cell culture
        - Rescue (max 4 pts): human, organism, cell culture, patient cells

        Total max: 6 points (despite subcategory maxes summing higher)

        Args:
            evidence_data: Experimental evidence - either nested dict (new format)
                          or flat list (legacy format)

        Returns:
            Tuple of (total_score, detailed_breakdown)
        """
        # Handle both nested (new) and flat list (legacy) formats
        if isinstance(evidence_data, list):
            return self._calculate_experimental_evidence_legacy(evidence_data)

        # New nested format per SOP v11
        function_score = 0.0
        functional_alteration_score = 0.0
        models_score = 0.0
        rescue_score = 0.0

        function_details: dict[str, Any] = {}
        functional_alteration_details: dict[str, Any] = {}
        models_details: dict[str, Any] = {}
        rescue_details: dict[str, Any] = {}

        # --- Function Category (max 2 points combined) ---
        function_data = evidence_data.get("function", {})
        if isinstance(function_data, dict):
            # Biochemical function (0.5-2 pts per item)
            biochem_items = function_data.get("biochemical_function", [])
            biochem_score = sum(
                float(item.get("points", 0.5)) for item in biochem_items
            )
            function_details["biochemical_function"] = {
                "items": biochem_items,
                "score": biochem_score,
            }

            # Protein interaction (0.5-2 pts per item)
            protein_items = function_data.get("protein_interaction", [])
            protein_score = sum(
                float(item.get("points", 0.5)) for item in protein_items
            )
            function_details["protein_interaction"] = {
                "items": protein_items,
                "score": protein_score,
            }

            # Expression (0.5-2 pts per item)
            expression_items = function_data.get("expression", [])
            expression_score = sum(
                float(item.get("points", 0.5)) for item in expression_items
            )
            function_details["expression"] = {
                "items": expression_items,
                "score": expression_score,
            }

            function_score = min(
                biochem_score + protein_score + expression_score,
                self.MAX_FUNCTION_SCORE,
            )

        # --- Functional Alteration Category (max 2 points combined) ---
        fa_data = evidence_data.get("functional_alteration", {})
        if isinstance(fa_data, dict):
            # Patient cells (1-2 pts per item)
            patient_items = fa_data.get("patient_cells", [])
            patient_score = sum(
                float(item.get("points", 1.0)) for item in patient_items
            )
            functional_alteration_details["patient_cells"] = {
                "items": patient_items,
                "score": patient_score,
            }

            # Non-patient cells (0.5-1 pts per item)
            non_patient_items = fa_data.get("non_patient_cells", [])
            non_patient_score = sum(
                float(item.get("points", 0.5)) for item in non_patient_items
            )
            functional_alteration_details["non_patient_cells"] = {
                "items": non_patient_items,
                "score": non_patient_score,
            }

            functional_alteration_score = min(
                patient_score + non_patient_score,
                self.MAX_FUNCTIONAL_ALTERATION_SCORE,
            )

        # --- Models Category (max 4 points combined) ---
        models_data = evidence_data.get("models", {})
        if isinstance(models_data, dict):
            # Non-human model organism (2-4 pts per item)
            organism_items = models_data.get("non_human_model_organism", [])
            organism_score = sum(
                float(item.get("points", 2.0)) for item in organism_items
            )
            models_details["non_human_model_organism"] = {
                "items": organism_items,
                "score": organism_score,
            }

            # Cell culture model (1-2 pts per item)
            cell_items = models_data.get("cell_culture_model", [])
            cell_score = sum(float(item.get("points", 1.0)) for item in cell_items)
            models_details["cell_culture_model"] = {
                "items": cell_items,
                "score": cell_score,
            }

            models_score = min(
                organism_score + cell_score,
                self.MAX_MODELS_SCORE,
            )

        # --- Rescue Category (max 4 points combined) ---
        rescue_data = evidence_data.get("rescue", {})
        if isinstance(rescue_data, dict):
            # Human rescue (2-4 pts)
            human_items = rescue_data.get("human", [])
            human_score = sum(float(item.get("points", 2.0)) for item in human_items)
            rescue_details["human"] = {"items": human_items, "score": human_score}

            # Non-human organism rescue (2-4 pts)
            organism_rescue_items = rescue_data.get("non_human_model_organism", [])
            organism_rescue_score = sum(
                float(item.get("points", 2.0)) for item in organism_rescue_items
            )
            rescue_details["non_human_model_organism"] = {
                "items": organism_rescue_items,
                "score": organism_rescue_score,
            }

            # Cell culture rescue (1-2 pts)
            cell_rescue_items = rescue_data.get("cell_culture", [])
            cell_rescue_score = sum(
                float(item.get("points", 1.0)) for item in cell_rescue_items
            )
            rescue_details["cell_culture"] = {
                "items": cell_rescue_items,
                "score": cell_rescue_score,
            }

            # Patient cells rescue (1-2 pts)
            patient_rescue_items = rescue_data.get("patient_cells", [])
            patient_rescue_score = sum(
                float(item.get("points", 1.0)) for item in patient_rescue_items
            )
            rescue_details["patient_cells"] = {
                "items": patient_rescue_items,
                "score": patient_rescue_score,
            }

            rescue_score = min(
                human_score
                + organism_rescue_score
                + cell_rescue_score
                + patient_rescue_score,
                self.MAX_RESCUE_SCORE,
            )

        # Total experimental score (max 6 per SOP v11)
        total = min(
            function_score + functional_alteration_score + models_score + rescue_score,
            self.MAX_EXPERIMENTAL_SCORE,
        )

        details = {
            "function_score": function_score,
            "functional_alteration_score": functional_alteration_score,
            "models_score": models_score,
            "rescue_score": rescue_score,
            "total_experimental_score": total,
            "function_details": function_details,
            "functional_alteration_details": functional_alteration_details,
            "models_details": models_details,
            "rescue_details": rescue_details,
        }

        return total, details

    def _calculate_experimental_evidence_legacy(
        self, evidence_items: list[dict[str, Any]]
    ) -> tuple[float, dict[str, Any]]:
        """Calculate experimental evidence from legacy flat list format.

        Kept for backwards compatibility with existing curations.

        Args:
            evidence_items: Flat list of evidence items with evidence_category field

        Returns:
            Tuple of (total_score, detailed_breakdown)
        """
        function_score = 0.0
        models_score = 0.0
        rescue_score = 0.0

        function_items = []
        models_items = []
        rescue_items = []

        for item in evidence_items:
            category = item.get("evidence_category", "")
            model_system = item.get("model_system", "").lower()
            rescue_observed = item.get("rescue_observed", False)

            if category in ["expression", "protein_function", "function"]:
                # Function evidence: use provided points or default
                score = float(item.get("points", 1.0))
                function_score += score
                function_items.append({**item, "computed_score": score})

            elif category == "models":
                # Model systems: use provided points or default based on type
                score = float(
                    item.get(
                        "points",
                        4.0
                        if model_system in ["patient_cells", "animal_model"]
                        else 2.0,
                    )
                )
                models_score += score
                models_items.append({**item, "computed_score": score})

            elif category == "rescue":
                # Rescue: use provided points or default based on rescue_observed
                score = float(item.get("points", 2.0 if rescue_observed else 0.0))
                rescue_score += score
                rescue_items.append({**item, "computed_score": score})

        # Apply category-specific limits
        function_score = min(function_score, self.MAX_FUNCTION_SCORE)
        models_score = min(models_score, self.MAX_MODELS_SCORE)
        rescue_score = min(rescue_score, self.MAX_RESCUE_SCORE)

        # Total experimental score (max 6)
        total = min(
            function_score + models_score + rescue_score,
            self.MAX_EXPERIMENTAL_SCORE,
        )

        details = {
            "function_score": function_score,
            "functional_alteration_score": 0.0,  # Not in legacy format
            "models_score": models_score,
            "rescue_score": rescue_score,
            "total_experimental_score": total,
            "function_items": function_items,
            "models_items": models_items,
            "rescue_items": rescue_items,
        }

        return total, details

    def _classify(self, total_score: float) -> str:
        """Determine classification based on total score per SOP v11 thresholds

        Thresholds (SOP v11):
        - Definitive: ≥12 points
        - Strong: 7-11.99 points
        - Moderate: 2-6.99 points
        - Limited: 0.1-1.99 points
        - No Known: 0 points
        - Disputed: contradictory evidence (handled separately)
        - Refuted: contradictory evidence overwhelms supporting (handled separately)

        Args:
            total_score: Combined genetic + experimental score

        Returns:
            Classification string
        """
        if total_score >= self.THRESHOLDS["definitive"]:
            return "definitive"
        elif total_score >= self.THRESHOLDS["strong"]:
            return "strong"
        elif total_score >= self.THRESHOLDS["moderate"]:
            return "moderate"
        elif total_score >= self.THRESHOLDS["limited"]:
            return "limited"
        elif total_score >= self.THRESHOLDS["no_known"]:
            return "no_known"
        elif total_score >= self.THRESHOLDS["disputed"]:
            return "disputed"
        else:
            return "refuted"

    def _generate_rationale(
        self,
        genetic_score: float,
        experimental_score: float,
        total_score: float,
        classification: str,
    ) -> str:
        """Generate human-readable rationale for classification

        Args:
            genetic_score: Genetic evidence total
            experimental_score: Experimental evidence total
            total_score: Combined total
            classification: Determined classification

        Returns:
            Rationale string explaining the classification
        """
        rationale = (
            f"Based on ClinGen SOP v11 scoring methodology: "
            f"genetic evidence = {genetic_score:.1f} points, "
            f"experimental evidence = {experimental_score:.1f} points, "
            f"total score = {total_score:.1f} points. "
        )

        classification_explanations = {
            "definitive": "Total score ≥12 points supports DEFINITIVE gene-disease relationship.",
            "strong": "Total score 7-11.99 points supports STRONG gene-disease relationship.",
            "moderate": "Total score 2-6.99 points supports MODERATE gene-disease relationship.",
            "limited": "Total score 0.1-1.99 points supports LIMITED gene-disease relationship.",
            "no_known": "No evidence supporting a gene-disease relationship.",
            "disputed": "Conflicting or contradictory evidence present, resulting in DISPUTED classification.",
            "refuted": "Evidence refutes the gene-disease relationship.",
        }

        rationale += classification_explanations.get(
            classification,
            "Classification could not be determined.",
        )

        return rationale

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

        # Check experimental evidence
        if not self._has_experimental_evidence(experimental_evidence):
            warnings.append(
                "No experimental evidence provided - may limit classification strength"
            )

        # Check PMIDs
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

        if not genetic_evidence:
            warnings.append(
                "No genetic evidence provided - at least one item recommended"
            )
            return warnings

        # Handle nested format (SOP v11)
        if isinstance(genetic_evidence, dict):
            return self._check_genetic_evidence_warnings_nested(genetic_evidence)

        # Legacy flat list format
        case_level_items = [
            item
            for item in genetic_evidence
            if item.get("evidence_category") == "case_level"
        ]
        if len(case_level_items) < 2:
            warnings.append(
                f"Only {len(case_level_items)} case-level evidence item(s) - "
                "consider adding more for stronger support"
            )

        # Check for LOD scores in segregation evidence
        segregation_items = [
            item
            for item in genetic_evidence
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

        # Count case-level evidence items
        case_level_count = 0
        case_level_data = genetic_evidence.get("case_level", {})
        if isinstance(case_level_data, dict):
            for inheritance_type in [
                "autosomal_dominant_or_x_linked",
                "autosomal_recessive",
            ]:
                inh_data = case_level_data.get(inheritance_type, {})
                if isinstance(inh_data, dict):
                    null_items = inh_data.get("predicted_or_proven_null", [])
                    other_items = inh_data.get("other_variant_type", [])
                    case_level_count += len(null_items) + len(other_items)

        if case_level_count < 2:
            warnings.append(
                f"Only {case_level_count} case-level evidence item(s) - "
                "consider adding more for stronger support"
            )

        # Check segregation evidence
        segregation_items = genetic_evidence.get("segregation", [])
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

    def _has_experimental_evidence(
        self, experimental_evidence: list[dict[str, Any]] | dict[str, Any]
    ) -> bool:
        """Check if any experimental evidence exists."""
        if isinstance(experimental_evidence, list):
            return len(experimental_evidence) > 0

        if isinstance(experimental_evidence, dict):
            for category in ["function", "functional_alteration", "models", "rescue"]:
                cat_data = experimental_evidence.get(category, {})
                if isinstance(cat_data, dict):
                    for items in cat_data.values():
                        if isinstance(items, list) and len(items) > 0:
                            return True
        return False

    def _count_missing_pmids(
        self,
        genetic_evidence: list[dict[str, Any]],
        experimental_evidence: list[dict[str, Any]] | dict[str, Any],
    ) -> int:
        """Count evidence items with missing or invalid PMIDs."""
        count = 0

        # Check genetic evidence
        for item in genetic_evidence:
            if not self._is_valid_pmid(item.get("pmid", "")):
                count += 1

        # Check experimental evidence
        if isinstance(experimental_evidence, dict):
            count += self._count_missing_pmids_nested(experimental_evidence)
        elif isinstance(experimental_evidence, list):
            for item in experimental_evidence:
                if not self._is_valid_pmid(item.get("pmid", "")):
                    count += 1

        return count

    def _count_missing_pmids_nested(self, exp_data: dict[str, Any]) -> int:
        """Count missing PMIDs in nested experimental evidence."""
        count = 0
        for category in ["function", "functional_alteration", "models", "rescue"]:
            cat_data = exp_data.get(category, {})
            if isinstance(cat_data, dict):
                for items in cat_data.values():
                    if isinstance(items, list):
                        for item in items:
                            if not self._is_valid_pmid(item.get("pmid", "")):
                                count += 1
        return count

    def _is_valid_pmid(self, pmid: Any) -> bool:
        """Check if a PMID is valid."""
        pmid_str = str(pmid)
        return pmid_str.isdigit() and len(pmid_str) >= 7

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
