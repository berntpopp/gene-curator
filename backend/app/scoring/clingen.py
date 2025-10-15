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
    MAX_SEGREGATION_SCORE: Final[float] = 7.0
    MAX_CASE_CONTROL_SCORE: Final[float] = 6.0

    # Experimental evidence category limits
    MAX_EXPRESSION_SCORE: Final[float] = 2.0
    MAX_FUNCTION_SCORE: Final[float] = 2.0
    MAX_MODELS_SCORE: Final[float] = 4.0
    MAX_RESCUE_SCORE: Final[float] = 2.0

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
        experimental_score, experimental_details = self._calculate_experimental_evidence(
            experimental_evidence
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
        self, evidence_items: list[dict[str, Any]]
    ) -> tuple[float, dict[str, Any]]:
        """Calculate genetic evidence score (max 12 points)

        Processes three categories:
        - Case-level evidence (variants in probands)
        - Segregation evidence (family studies with LOD scores)
        - Case-control evidence (population studies)

        Args:
            evidence_items: List of genetic evidence items

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
        self, evidence_items: list[dict[str, Any]]
    ) -> tuple[float, dict[str, Any]]:
        """Calculate experimental evidence score (max 6 points)

        Processes four categories:
        - Expression evidence (tissue/cell type expression)
        - Protein function evidence (biochemical assays)
        - Model systems evidence (cell/animal models)
        - Rescue evidence (complementation/rescue experiments)

        Args:
            evidence_items: List of experimental evidence items

        Returns:
            Tuple of (total_score, detailed_breakdown)
        """
        expression_score = 0.0
        function_score = 0.0
        models_score = 0.0
        rescue_score = 0.0

        expression_items = []
        function_items = []
        models_items = []
        rescue_items = []

        for item in evidence_items:
            category = item.get("evidence_category", "")
            model_system = item.get("model_system", "").lower()
            rescue_observed = item.get("rescue_observed", False)

            if category == "expression":
                # Expression evidence: patient cells (2.0) or other (1.0)
                score = 2.0 if model_system == "patient_cells" else 1.0
                expression_score += score
                expression_items.append({**item, "computed_score": score})

            elif category == "protein_function":
                # Protein function evidence: patient cells (2.0) or other (1.0)
                score = 2.0 if model_system == "patient_cells" else 1.0
                function_score += score
                function_items.append({**item, "computed_score": score})

            elif category == "models":
                # Model systems: patient cells/animal models (4.0) or other (2.0)
                score = (
                    4.0
                    if model_system in ["patient_cells", "animal_model"]
                    else 2.0
                )
                models_score += score
                models_items.append({**item, "computed_score": score})

            elif category == "rescue":
                # Rescue evidence: successful rescue (2.0) or no rescue (0.0)
                score = 2.0 if rescue_observed else 0.0
                rescue_score += score
                rescue_items.append({**item, "computed_score": score})

        # Apply category-specific limits
        expression_score = min(expression_score, self.MAX_EXPRESSION_SCORE)
        function_score = min(function_score, self.MAX_FUNCTION_SCORE)
        models_score = min(models_score, self.MAX_MODELS_SCORE)
        rescue_score = min(rescue_score, self.MAX_RESCUE_SCORE)

        # Total experimental score (max 6)
        total = min(
            expression_score + function_score + models_score + rescue_score,
            self.MAX_EXPERIMENTAL_SCORE,
        )

        details = {
            "expression_score": expression_score,
            "function_score": function_score,
            "models_score": models_score,
            "rescue_score": rescue_score,
            "total_experimental_score": total,
            "expression_items": expression_items,
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
        experimental_evidence: list[dict[str, Any]],
    ) -> list[str]:
        """Check for potential issues or warnings in evidence data

        Args:
            genetic_evidence: List of genetic evidence items
            experimental_evidence: List of experimental evidence items

        Returns:
            List of warning messages
        """
        warnings = []

        # Check for missing evidence
        if not genetic_evidence:
            warnings.append("No genetic evidence provided - at least one item recommended")

        if not experimental_evidence:
            warnings.append(
                "No experimental evidence provided - may limit classification strength"
            )

        # Check case-level evidence count
        case_level_items = [
            item for item in genetic_evidence if item.get("evidence_category") == "case_level"
        ]
        if len(case_level_items) < 2:
            warnings.append(
                f"Only {len(case_level_items)} case-level evidence item(s) - "
                "consider adding more for stronger support"
            )

        # Check for missing PMIDs
        all_items = genetic_evidence + experimental_evidence
        missing_pmid_count = 0

        for item in all_items:
            pmid = str(item.get("pmid", ""))
            if not pmid or not pmid.isdigit() or len(pmid) < 7:
                missing_pmid_count += 1

        if missing_pmid_count > 0:
            warnings.append(
                f"{missing_pmid_count} evidence item(s) with invalid or missing PMID"
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

    def validate_evidence(  # noqa: C901
        self, evidence_data: dict[str, Any], schema_config: dict[str, Any]
    ) -> list[str]:
        """Validate evidence data structure and required fields

        Args:
            evidence_data: Evidence items organized by category
            schema_config: Schema configuration (unused but required by interface)

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        genetic_evidence = evidence_data.get("genetic_evidence", [])
        experimental_evidence = evidence_data.get("experimental_evidence", [])

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

        # Validate experimental evidence items
        for idx, item in enumerate(experimental_evidence):
            category = item.get("evidence_category")

            if not category:
                errors.append(
                    f"Experimental evidence item {idx + 1}: Missing evidence_category"
                )
                continue

            # Validate category is one of the expected types
            valid_categories = ["expression", "protein_function", "models", "rescue"]
            if category not in valid_categories:
                errors.append(
                    f"Experimental evidence {idx + 1}: Invalid category "
                    f"(must be one of: {', '.join(valid_categories)})"
                )

            # Model system validation for categories that use it
            if category in ["expression", "protein_function", "models"] and "model_system" not in item:
                errors.append(
                    f"Experimental evidence {idx + 1}: Missing model_system"
                )

            # Rescue evidence validation
            if category == "rescue" and "rescue_observed" not in item:
                errors.append(
                    f"Rescue evidence {idx + 1}: Missing rescue_observed field"
                )

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
