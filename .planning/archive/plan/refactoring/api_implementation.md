# API Implementation - ClinGen SOP v11

**Parent Plan**: `IMPLEMENTATION_PLAN.md`
**Phase**: Phase 2 (Weeks 5-9)
**Owner**: Backend Developers

---

## Overview

This document specifies all API changes for ClinGen SOP v11 implementation, including new endpoints, service layer architecture, scoring engine, external validators, and complete request/response schemas.

---

## Architecture Layers

```
┌──────────────────────────────────────────────────────────┐
│              API Endpoints (FastAPI)                      │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐         │
│  │ Evidence   │  │ Gene       │  │ Validation │         │
│  │ Routes     │  │ Summary    │  │ Routes     │         │
│  └────────────┘  └────────────┘  └────────────┘         │
└──────────────────────────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────────┐
│              Service Layer (Business Logic)               │
│  ┌─────────────────┐  ┌─────────────────┐               │
│  │ Scope           │  │ Validation      │               │
│  │ Permission      │  │ Service         │               │
│  │ Service         │  └─────────────────┘               │
│  └─────────────────┘           ↓                         │
│           ↓           ┌─────────────────┐               │
│  ┌─────────────────┐  │ External        │               │
│  │ Gene Summary    │  │ Validators      │               │
│  │ Service         │  │ (HGNC/PubMed)   │               │
│  └─────────────────┘  └─────────────────┘               │
└──────────────────────────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────────┐
│              Scoring Layer                                │
│  ┌─────────────────┐  ┌─────────────────┐               │
│  │ ClinGen         │  │ LOD Score       │               │
│  │ Scoring Engine  │  │ Calculator      │               │
│  └─────────────────┘  └─────────────────┘               │
└──────────────────────────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────────┐
│              CRUD Layer (Data Access)                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │ Evidence    │  │ Gene        │  │ Validation  │     │
│  │ CRUD        │  │ Summary     │  │ Cache CRUD  │     │
│  └─────────────┘  │ CRUD        │  └─────────────┘     │
│                   └─────────────┘                        │
└──────────────────────────────────────────────────────────┘
```

---

## Service Layer

### 1. ScopePermissionService

**File**: `backend/app/services/scope_permissions.py`

```python
"""Scope-based permission service for access control"""

from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.models import CurationNew, Scope, UserNew

logger = get_logger(__name__)


class ScopePermissionService:
    """Centralized scope-based permission logic"""

    @staticmethod
    def can_view_scope(db: Session, user: Optional[UserNew], scope: Scope) -> bool:
        """Check if user can view scope"""
        # Public scopes: anyone can view
        if scope.is_public:
            return True

        # Private scopes: must be authenticated and member
        if user is None:
            return False

        # Admin can view all
        if user.role == "admin":
            return True

        # Check if user is scope member
        return db.query(ScopeMember).filter(
            ScopeMember.scope_id == scope.id,
            ScopeMember.user_id == user.id,
            ScopeMember.is_active == True
        ).count() > 0

    @staticmethod
    def can_view_curation(
        db: Session,
        user: Optional[UserNew],
        curation: CurationNew
    ) -> bool:
        """Check if user can view curation"""
        scope = db.query(Scope).filter(Scope.id == curation.scope_id).first()

        if not scope:
            return False

        return ScopePermissionService.can_view_scope(db, user, scope)

    @staticmethod
    def can_create_curation(db: Session, user: UserNew, scope_id: UUID) -> bool:
        """Check if user can create curation in scope"""
        if user.role == "admin":
            return True

        scope = db.query(Scope).filter(Scope.id == scope_id).first()
        if not scope:
            return False

        # Must be scope member with curator+ role
        member = db.query(ScopeMember).filter(
            ScopeMember.scope_id == scope_id,
            ScopeMember.user_id == user.id,
            ScopeMember.is_active == True
        ).first()

        if not member:
            return False

        return member.role in ["curator", "scope_admin"]

    @staticmethod
    def can_edit_curation(
        db: Session,
        user: UserNew,
        curation: CurationNew
    ) -> bool:
        """Check if user can edit curation"""
        # Admin can edit all
        if user.role == "admin":
            return True

        # Creator can edit own curations (if not in review/active)
        if curation.created_by == user.id and curation.stage not in ["review", "active"]:
            return True

        # Scope admin can edit any curation in their scope
        scope_member = db.query(ScopeMember).filter(
            ScopeMember.scope_id == curation.scope_id,
            ScopeMember.user_id == user.id,
            ScopeMember.is_active == True
        ).first()

        if scope_member and scope_member.role == "scope_admin":
            return True

        return False

    @staticmethod
    def can_approve_curation(
        db: Session,
        user: UserNew,
        curation: CurationNew
    ) -> bool:
        """Check if user can approve/activate curation (4-eyes principle)"""
        # Admin can approve all
        if user.role == "admin":
            return True

        # Cannot approve own curation (4-eyes)
        if curation.created_by == user.id:
            return False

        # Must be scope member with reviewer+ role
        scope_member = db.query(ScopeMember).filter(
            ScopeMember.scope_id == curation.scope_id,
            ScopeMember.user_id == user.id,
            ScopeMember.is_active == True
        ).first()

        if not scope_member:
            return False

        return scope_member.role in ["reviewer", "scope_admin"]

    @staticmethod
    def get_visible_scopes(db: Session, user: Optional[UserNew]) -> list[Scope]:
        """Get all scopes visible to user"""
        query = db.query(Scope).filter(Scope.is_active == True)

        # Anonymous: only public scopes
        if user is None:
            return query.filter(Scope.is_public == True).all()

        # Admin: all scopes
        if user.role == "admin":
            return query.all()

        # Authenticated: public scopes + private scopes where user is member
        public_scopes = query.filter(Scope.is_public == True).all()

        member_scope_ids = db.query(ScopeMember.scope_id).filter(
            ScopeMember.user_id == user.id,
            ScopeMember.is_active == True
        ).all()

        private_scopes = query.filter(
            Scope.id.in_([sid[0] for sid in member_scope_ids]),
            Scope.is_public == False
        ).all()

        return public_scopes + private_scopes

    @staticmethod
    def filter_visible_curations(
        db: Session,
        query,
        user: Optional[UserNew]
    ):
        """Apply visibility filter to curation query"""
        visible_scope_ids = [
            s.id for s in ScopePermissionService.get_visible_scopes(db, user)
        ]

        return query.filter(CurationNew.scope_id.in_(visible_scope_ids))
```

---

### 2. ValidationService

**File**: `backend/app/services/validation_service.py`

```python
"""External validation service with caching"""

import hashlib
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.models import ValidationCache
from app.schemas.validation import ValidationResult
from app.services.validators.base import ExternalValidator
from app.services.validators.hgnc import HGNCValidator
from app.services.validators.hpo import HPOValidator
from app.services.validators.pubmed import PubMedValidator

logger = get_logger(__name__)


class ValidationService:
    """Centralized validation service with caching"""

    # TTL for each validator (in days)
    TTL_DAYS = {
        "hgnc": 30,
        "pubmed": 90,
        "hpo": 14,
    }

    def __init__(self, db: Session):
        self.db = db
        self.validators: dict[str, ExternalValidator] = {
            "hgnc": HGNCValidator(),
            "pubmed": PubMedValidator(),
            "hpo": HPOValidator(),
        }

    def _generate_cache_key(self, validator_name: str, input_value: str) -> str:
        """Generate SHA256 hash for cache lookup"""
        combined = f"{validator_name}:{input_value.lower().strip()}"
        return hashlib.sha256(combined.encode()).hexdigest()

    def _get_cached_result(
        self, validator_name: str, input_value: str
    ) -> Optional[ValidationResult]:
        """Check cache for validation result"""
        cache_key = self._generate_cache_key(validator_name, input_value)

        cached = (
            self.db.query(ValidationCache)
            .filter(
                ValidationCache.validator_input_hash == cache_key,
                ValidationCache.expires_at > datetime.now(),
            )
            .first()
        )

        if cached:
            # Update access metrics
            cached.access_count += 1
            cached.last_accessed_at = datetime.now()
            self.db.commit()

            logger.info(
                "Validation cache hit",
                validator=validator_name,
                input_value=input_value,
                access_count=cached.access_count,
            )

            return ValidationResult(
                is_valid=cached.is_valid,
                status=cached.validation_status,
                data=cached.validation_response,
                suggestions=cached.suggestions,
                error_message=cached.error_message,
            )

        logger.info("Validation cache miss", validator=validator_name, input_value=input_value)
        return None

    def _cache_result(
        self, validator_name: str, input_value: str, result: ValidationResult
    ) -> None:
        """Cache validation result"""
        cache_key = self._generate_cache_key(validator_name, input_value)
        ttl_days = self.TTL_DAYS.get(validator_name, 7)
        expires_at = datetime.now() + timedelta(days=ttl_days)

        cache_entry = ValidationCache(
            validator_name=validator_name,
            input_value=input_value.strip(),
            validator_input_hash=cache_key,
            is_valid=result.is_valid,
            validation_status=result.status,
            validation_response=result.data or {},
            suggestions=result.suggestions,
            error_message=result.error_message,
            expires_at=expires_at,
        )

        self.db.add(cache_entry)
        self.db.commit()

        logger.info(
            "Validation result cached",
            validator=validator_name,
            input_value=input_value,
            expires_at=expires_at,
        )

    async def validate(
        self, validator_name: str, input_value: str, skip_cache: bool = False
    ) -> ValidationResult:
        """Validate input using specified validator"""
        # Check cache first
        if not skip_cache:
            cached_result = self._get_cached_result(validator_name, input_value)
            if cached_result:
                return cached_result

        # Get validator
        validator = self.validators.get(validator_name)
        if not validator:
            return ValidationResult(
                is_valid=False,
                status="error",
                error_message=f"Unknown validator: {validator_name}",
            )

        # Validate
        try:
            result = await validator.validate(input_value)
            self._cache_result(validator_name, input_value, result)
            return result

        except Exception as e:
            logger.error(
                "Validation failed",
                validator=validator_name,
                input_value=input_value,
                error=e,
            )
            return ValidationResult(
                is_valid=False, status="error", error_message=str(e)
            )

    async def validate_batch(
        self, validator_name: str, input_values: list[str]
    ) -> dict[str, ValidationResult]:
        """Validate multiple values"""
        results = {}

        for value in input_values:
            results[value] = await self.validate(validator_name, value)

        return results
```

---

### 3. GeneSummaryService

**File**: `backend/app/services/gene_summary_service.py`

```python
"""Gene summary aggregation service"""

from typing import Optional
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.models import CurationNew, GeneSummary, Scope
from app.schemas.gene_summary import GeneSummaryPublic, ScopeSummary

logger = get_logger(__name__)


class GeneSummaryService:
    """Service for gene summary aggregation across scopes"""

    def __init__(self, db: Session):
        self.db = db

    def compute_summary(self, gene_id: UUID) -> GeneSummary:
        """Compute or update gene summary"""
        # Get all CURRENT ACTIVE curations for gene
        curations = (
            self.db.query(CurationNew)
            .filter(
                CurationNew.gene_id == gene_id,
                CurationNew.is_current == True,
                CurationNew.stage == "active",
            )
            .all()
        )

        # Get unique scopes
        scope_ids = list(set([c.scope_id for c in curations]))
        scopes = self.db.query(Scope).filter(Scope.id.in_(scope_ids)).all()
        scope_map = {s.id: s for s in scopes}

        # Count public vs private
        public_count = sum(1 for c in curations if scope_map[c.scope_id].is_public)
        private_count = len(curations) - public_count

        # Classification counts
        classification_summary = {}
        for c in curations:
            classification = c.classification or "unknown"
            classification_summary[classification] = (
                classification_summary.get(classification, 0) + 1
            )

        # Per-scope summaries
        scope_summaries = []
        for curation in curations:
            scope = scope_map[curation.scope_id]
            scope_summaries.append(
                {
                    "scope_id": str(curation.scope_id),
                    "scope_name": scope.name,
                    "is_public": scope.is_public,
                    "classification": curation.classification,
                    "genetic_score": curation.computed_scores.get("genetic_evidence_total", 0),
                    "experimental_score": curation.computed_scores.get("experimental_evidence_total", 0),
                    "total_score": curation.computed_scores.get("total_score", 0),
                    "last_updated": curation.updated_at.isoformat(),
                    "curator_count": 1,  # TODO: Get from curation history
                    "evidence_count": len(curation.computed_scores.get("evidence_items", [])),
                }
            )

        # Check for conflicts
        unique_classifications = set([c.classification for c in curations if c.classification])
        has_conflicts = len(unique_classifications) > 1

        # Get or create summary
        summary = (
            self.db.query(GeneSummary)
            .filter(GeneSummary.gene_id == gene_id)
            .first()
        )

        if not summary:
            summary = GeneSummary(gene_id=gene_id)
            self.db.add(summary)

        # Update fields
        summary.total_scopes_curated = len(scope_ids)
        summary.public_scopes_count = public_count
        summary.private_scopes_count = private_count
        summary.classification_summary = classification_summary
        summary.scope_summaries = scope_summaries
        summary.has_conflicts = has_conflicts
        summary.is_stale = False
        summary.last_computed_at = func.now()

        # Compute consensus (simple majority for MVP)
        if classification_summary:
            summary.consensus_classification = max(
                classification_summary, key=classification_summary.get
            )
            summary.consensus_confidence = (
                classification_summary[summary.consensus_classification] / len(curations)
            )

        self.db.commit()
        self.db.refresh(summary)

        logger.info(
            "Gene summary computed",
            gene_id=str(gene_id),
            total_scopes=len(scope_ids),
            public_scopes=public_count,
            has_conflicts=has_conflicts,
        )

        return summary

    def get_public_summary(self, gene_id: UUID) -> Optional[GeneSummaryPublic]:
        """Get public summary (only public scopes)"""
        summary = (
            self.db.query(GeneSummary)
            .filter(GeneSummary.gene_id == gene_id)
            .first()
        )

        if not summary:
            # Compute if doesn't exist
            summary = self.compute_summary(gene_id)

        # Recompute if stale
        if summary.is_stale:
            summary = self.compute_summary(gene_id)

        # Filter to only public scopes
        public_scope_summaries = [
            s for s in summary.scope_summaries if s.get("is_public", False)
        ]

        if not public_scope_summaries:
            return None

        return GeneSummaryPublic(
            gene_id=summary.gene_id,
            public_scopes_count=summary.public_scopes_count,
            classification_summary=summary.classification_summary,
            consensus_classification=summary.consensus_classification,
            has_conflicts=summary.has_conflicts,
            scope_summaries=public_scope_summaries,
            last_updated=summary.last_computed_at,
        )

    def mark_stale(self, gene_id: UUID) -> None:
        """Mark gene summary as stale (called by trigger)"""
        self.db.query(GeneSummary).filter(GeneSummary.gene_id == gene_id).update(
            {"is_stale": True}
        )
        self.db.commit()
```

---

## Scoring Layer

### 1. ClinGen Scoring Engine

**File**: `backend/app/scoring/clingen.py` (ENHANCED)

```python
"""Complete ClinGen SOP v11 scoring engine"""

import math
from typing import Any

from app.core.logging import get_logger
from app.schemas.scoring import ScoringResult
from app.scoring.base import ScoringEngine

logger = get_logger(__name__)


class ClinGenEngine(ScoringEngine):
    """
    ClinGen Gene-Disease Validity Scoring Engine (SOP v11)

    References:
    - https://www.clinicalgenome.org/docs/gene-disease-validity-sop-v11/
    """

    name = "clingen"
    version = "11.0"
    description = "ClinGen Gene-Disease Clinical Validity Curation (September 2024)"

    # Maximum scores per category
    MAX_GENETIC_SCORE = 12.0
    MAX_EXPERIMENTAL_SCORE = 6.0

    # Classification thresholds
    THRESHOLDS = {
        "definitive": 12.0,
        "strong": 7.0,
        "moderate": 2.0,
        "limited": 0.1,
        "no_known": 0.0,
        "disputed": -1.0,
        "refuted": -2.0,
    }

    def calculate_scores(
        self, evidence_data: dict[str, Any], schema_config: dict[str, Any]
    ) -> ScoringResult:
        """Calculate complete ClinGen scores"""

        genetic_evidence = evidence_data.get("genetic_evidence", [])
        experimental_evidence = evidence_data.get("experimental_evidence", [])

        # Calculate genetic evidence score
        genetic_score, genetic_details = self._calculate_genetic_evidence(
            genetic_evidence
        )

        # Calculate experimental evidence score
        experimental_score, experimental_details = self._calculate_experimental_evidence(
            experimental_evidence
        )

        # Total score
        total_score = genetic_score + experimental_score

        # Classification
        classification = self._classify(total_score)

        return ScoringResult(
            total_score=total_score,
            classification=classification,
            score_breakdown={
                "genetic_evidence_total": genetic_score,
                "experimental_evidence_total": experimental_score,
                "genetic_evidence_details": genetic_details,
                "experimental_evidence_details": experimental_details,
            },
            is_valid=True,
            validation_errors=[],
        )

    def _calculate_genetic_evidence(
        self, evidence_items: list[dict[str, Any]]
    ) -> tuple[float, dict[str, Any]]:
        """Calculate genetic evidence score (max 12 points)"""

        case_level_score = 0.0
        segregation_score = 0.0
        case_control_score = 0.0

        case_level_items = []
        segregation_items = []
        case_control_items = []

        for item in evidence_items:
            category = item.get("evidence_category")

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

        # Apply category limits
        case_level_score = min(case_level_score, 12.0)
        segregation_score = min(segregation_score, 7.0)
        case_control_score = min(case_control_score, 6.0)

        # Total genetic score (max 12)
        total = min(case_level_score + segregation_score + case_control_score, self.MAX_GENETIC_SCORE)

        details = {
            "case_level_score": case_level_score,
            "segregation_score": segregation_score,
            "case_control_score": case_control_score,
            "case_level_items": case_level_items,
            "segregation_items": segregation_items,
            "case_control_items": case_control_items,
        }

        return total, details

    def _score_case_level(self, item: dict[str, Any]) -> float:
        """Score case-level genetic evidence"""
        variant_type = item.get("variant_type", "")
        proband_count = item.get("proband_count", 0)
        de_novo = item.get("de_novo", False)
        functional_alteration = item.get("functional_alteration", False)

        # Base score per proband
        if variant_type == "predicted_null":
            base_score = 1.5
        elif variant_type == "missense":
            base_score = 0.1
        else:
            base_score = 0.5  # Other variant types

        score = base_score * proband_count

        # Bonuses
        if de_novo:
            if variant_type == "predicted_null":
                score += 0.5 * proband_count
            elif variant_type == "missense":
                score += 0.4 * proband_count

        if functional_alteration:
            if variant_type == "missense":
                score += 0.4 * proband_count
            else:
                score += 0.4 * proband_count

        return score

    def _score_segregation(self, item: dict[str, Any]) -> float:
        """Score segregation evidence using LOD scores"""
        family_count = item.get("family_count", 0)
        lod_score = item.get("lod_score")
        inheritance = item.get("inheritance_pattern", "")

        if lod_score is not None:
            # Use provided LOD score
            return self._lod_to_points(lod_score, inheritance)

        # Calculate LOD score from family count
        # (This is simplified - actual calculation depends on family structure)
        if inheritance in ["autosomal_dominant", "x_linked"]:
            calculated_lod = self._calculate_dominant_lod(family_count)
        else:
            calculated_lod = self._calculate_recessive_lod(family_count)

        return self._lod_to_points(calculated_lod, inheritance)

    def _calculate_dominant_lod(self, family_count: int) -> float:
        """Calculate LOD score for dominant/X-linked inheritance"""
        if family_count < 4:
            return 0.0

        # LOD = log10(1 / 0.5^n) where n = number of segregations
        # Simplified: assume 3 segregations per family on average
        segregations = family_count * 3
        return math.log10(1 / (0.5 ** segregations))

    def _calculate_recessive_lod(self, family_count: int) -> float:
        """Calculate LOD score for recessive inheritance"""
        if family_count < 2:
            return 0.0

        # Simplified calculation for recessive
        segregations = family_count * 2
        return math.log10(1 / (0.5 ** segregations))

    def _lod_to_points(self, lod_score: float, inheritance: str) -> float:
        """Convert LOD score to points"""
        if lod_score < 3.0:
            return 0.0
        elif lod_score < 5.0:
            return 1.0
        elif lod_score < 7.0:
            return 2.0
        else:
            # Max 7 points for segregation
            return min(7.0, 2.0 + (lod_score - 7.0) * 0.5)

    def _score_case_control(self, item: dict[str, Any]) -> float:
        """Score case-control evidence"""
        # Simplified: actual scoring depends on p-values, odds ratios, etc.
        # For MVP, use provided score or default
        return item.get("computed_score", 3.0)

    def _calculate_experimental_evidence(
        self, evidence_items: list[dict[str, Any]]
    ) -> tuple[float, dict[str, Any]]:
        """Calculate experimental evidence score (max 6 points)"""

        expression_score = 0.0
        function_score = 0.0
        models_score = 0.0
        rescue_score = 0.0

        expression_items = []
        function_items = []
        models_items = []
        rescue_items = []

        for item in evidence_items:
            category = item.get("evidence_category")
            model_system = item.get("model_system", "")
            rescue_observed = item.get("rescue_observed", False)

            if category == "expression":
                score = 2.0 if model_system == "patient_cells" else 1.0
                expression_score += score
                expression_items.append({**item, "computed_score": score})

            elif category == "protein_function":
                score = 2.0 if model_system == "patient_cells" else 1.0
                function_score += score
                function_items.append({**item, "computed_score": score})

            elif category == "models":
                score = 4.0 if model_system in ["patient_cells", "animal_model"] else 2.0
                models_score += score
                models_items.append({**item, "computed_score": score})

            elif category == "rescue":
                score = 2.0 if rescue_observed else 0.0
                rescue_score += score
                rescue_items.append({**item, "computed_score": score})

        # Apply category limits
        expression_score = min(expression_score, 2.0)
        function_score = min(function_score, 2.0)
        models_score = min(models_score, 4.0)
        rescue_score = min(rescue_score, 2.0)

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
            "expression_items": expression_items,
            "function_items": function_items,
            "models_items": models_items,
            "rescue_items": rescue_items,
        }

        return total, details

    def _classify(self, total_score: float) -> str:
        """Classify based on total score"""
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

    def validate_evidence(
        self, evidence_data: dict[str, Any], schema_config: dict[str, Any]
    ) -> list[str]:
        """Validate evidence structure"""
        errors = []

        genetic_evidence = evidence_data.get("genetic_evidence", [])
        if not genetic_evidence:
            errors.append("At least one genetic evidence item is required")

        for idx, item in enumerate(genetic_evidence):
            category = item.get("evidence_category")
            if not category:
                errors.append(f"Genetic evidence item {idx}: Missing evidence_category")

            if category == "case_level":
                if "proband_count" not in item:
                    errors.append(f"Case-level evidence {idx}: Missing proband_count")
                if "variant_type" not in item:
                    errors.append(f"Case-level evidence {idx}: Missing variant_type")

            if category == "segregation":
                if "family_count" not in item and "lod_score" not in item:
                    errors.append(f"Segregation evidence {idx}: Missing family_count or lod_score")

        return errors
```

---

### 2. External Validators

**File**: `backend/app/services/validators/base.py`

```python
"""Base class for external validators"""

from abc import ABC, abstractmethod
from typing import Any

from app.schemas.validation import ValidationResult


class ExternalValidator(ABC):
    """Abstract base class for external validators"""

    @abstractmethod
    async def validate(self, input_value: str) -> ValidationResult:
        """Validate input value against external API"""
        pass
```

**File**: `backend/app/services/validators/hgnc.py`

```python
"""HGNC gene symbol validator"""

import httpx

from app.core.logging import get_logger
from app.schemas.validation import ValidationResult
from app.services.validators.base import ExternalValidator

logger = get_logger(__name__)


class HGNCValidator(ExternalValidator):
    """Validate gene symbols against HGNC REST API"""

    API_BASE = "https://rest.genenames.org"
    TIMEOUT = 10.0

    async def validate(self, gene_symbol: str) -> ValidationResult:
        """Validate gene symbol"""

        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                response = await client.get(
                    f"{self.API_BASE}/search/symbol/{gene_symbol}",
                    headers={"Accept": "application/json"},
                )

                if response.status_code == 200:
                    data = response.json()
                    docs = data.get("response", {}).get("docs", [])

                    if docs:
                        # Valid gene symbol
                        gene_data = docs[0]
                        return ValidationResult(
                            is_valid=True,
                            status="valid",
                            data={
                                "approved_symbol": gene_data.get("symbol"),
                                "hgnc_id": gene_data.get("hgnc_id"),
                                "alias_symbols": gene_data.get("alias_symbol", []),
                                "previous_symbols": gene_data.get("prev_symbol", []),
                                "status": gene_data.get("status"),
                                "locus_type": gene_data.get("locus_type"),
                            },
                        )

                    # No match - search for suggestions
                    search_response = await client.get(
                        f"{self.API_BASE}/search/{gene_symbol}",
                        headers={"Accept": "application/json"},
                    )

                    suggestions = []
                    if search_response.status_code == 200:
                        search_data = search_response.json()
                        search_docs = search_data.get("response", {}).get("docs", [])
                        suggestions = [doc.get("symbol") for doc in search_docs[:5]]

                    return ValidationResult(
                        is_valid=False,
                        status="not_found",
                        error_message=f"Gene symbol '{gene_symbol}' not found in HGNC",
                        suggestions={"did_you_mean": suggestions} if suggestions else None,
                    )

                else:
                    return ValidationResult(
                        is_valid=False,
                        status="error",
                        error_message=f"HGNC API returned status {response.status_code}",
                    )

        except httpx.TimeoutException:
            logger.error("HGNC API timeout", gene_symbol=gene_symbol)
            return ValidationResult(
                is_valid=False, status="error", error_message="HGNC API timeout"
            )

        except Exception as e:
            logger.error("HGNC validation failed", gene_symbol=gene_symbol, error=e)
            return ValidationResult(
                is_valid=False, status="error", error_message=str(e)
            )
```

**File**: `backend/app/services/validators/pubmed.py`

```python
"""PubMed PMID validator"""

import httpx

from app.core.logging import get_logger
from app.schemas.validation import ValidationResult
from app.services.validators.base import ExternalValidator

logger = get_logger(__name__)


class PubMedValidator(ExternalValidator):
    """Validate PMIDs against NCBI E-utilities"""

    API_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    TIMEOUT = 10.0

    async def validate(self, pmid: str) -> ValidationResult:
        """Validate PMID"""

        # Check format
        if not pmid.isdigit():
            return ValidationResult(
                is_valid=False,
                status="invalid",
                error_message="PMID must be numeric",
            )

        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                # Use esummary to get publication details
                response = await client.get(
                    f"{self.API_BASE}/esummary.fcgi",
                    params={
                        "db": "pubmed",
                        "id": pmid,
                        "retmode": "json",
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    result = data.get("result", {})

                    if pmid in result:
                        pub_data = result[pmid]

                        # Check if valid (not deleted)
                        if "error" in pub_data:
                            return ValidationResult(
                                is_valid=False,
                                status="not_found",
                                error_message=f"PMID {pmid} not found",
                            )

                        return ValidationResult(
                            is_valid=True,
                            status="valid",
                            data={
                                "pmid": pmid,
                                "title": pub_data.get("title", ""),
                                "authors": [
                                    author.get("name", "")
                                    for author in pub_data.get("authors", [])
                                ],
                                "journal": pub_data.get("fulljournalname", ""),
                                "pub_date": pub_data.get("pubdate", ""),
                                "doi": pub_data.get("elocationid", ""),
                            },
                        )

                return ValidationResult(
                    is_valid=False,
                    status="error",
                    error_message=f"PubMed API returned status {response.status_code}",
                )

        except httpx.TimeoutException:
            logger.error("PubMed API timeout", pmid=pmid)
            return ValidationResult(
                is_valid=False, status="error", error_message="PubMed API timeout"
            )

        except Exception as e:
            logger.error("PubMed validation failed", pmid=pmid, error=e)
            return ValidationResult(
                is_valid=False, status="error", error_message=str(e)
            )
```

**File**: `backend/app/services/validators/hpo.py`

```python
"""HPO term validator"""

import httpx

from app.core.logging import get_logger
from app.schemas.validation import ValidationResult
from app.services.validators.base import ExternalValidator

logger = get_logger(__name__)


class HPOValidator(ExternalValidator):
    """Validate HPO terms against EMBL-EBI OLS API"""

    API_BASE = "https://www.ebi.ac.uk/ols/api"
    TIMEOUT = 10.0

    async def validate(self, hpo_term: str) -> ValidationResult:
        """Validate HPO term (e.g., HP:0001250)"""

        # Check format
        if not hpo_term.startswith("HP:"):
            return ValidationResult(
                is_valid=False,
                status="invalid",
                error_message="HPO term must start with 'HP:'",
            )

        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                # Encode colon for URL
                encoded_term = hpo_term.replace(":", "_")

                response = await client.get(
                    f"{self.API_BASE}/ontologies/hp/terms/http%253A%252F%252Fpurl.obolibrary.org%252Fobo%252F{encoded_term}",
                    headers={"Accept": "application/json"},
                )

                if response.status_code == 200:
                    data = response.json()

                    return ValidationResult(
                        is_valid=True,
                        status="valid",
                        data={
                            "term_id": hpo_term,
                            "term_name": data.get("label", ""),
                            "definition": data.get("description", [""])[0] if data.get("description") else "",
                            "synonyms": data.get("synonyms", []),
                        },
                    )

                elif response.status_code == 404:
                    return ValidationResult(
                        is_valid=False,
                        status="not_found",
                        error_message=f"HPO term '{hpo_term}' not found",
                    )

                else:
                    return ValidationResult(
                        is_valid=False,
                        status="error",
                        error_message=f"OLS API returned status {response.status_code}",
                    )

        except httpx.TimeoutException:
            logger.error("OLS API timeout", hpo_term=hpo_term)
            return ValidationResult(
                is_valid=False, status="error", error_message="OLS API timeout"
            )

        except Exception as e:
            logger.error("HPO validation failed", hpo_term=hpo_term, error=e)
            return ValidationResult(
                is_valid=False, status="error", error_message=str(e)
            )
```

---

## API Endpoints

### 1. Evidence Management Endpoints

**File**: `backend/app/api/v1/endpoints/evidence.py`

```python
"""Evidence item endpoints"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core import deps
from app.core.database import get_db
from app.crud.evidence import evidence_crud
from app.models.models import UserNew
from app.schemas.evidence import EvidenceItem, EvidenceItemCreate, EvidenceItemUpdate
from app.services.scope_permissions import ScopePermissionService

router = APIRouter()


@router.post("/curations/{curation_id}/evidence", response_model=EvidenceItem)
def create_evidence_item(
    *,
    db: Session = Depends(get_db),
    curation_id: UUID,
    evidence_in: EvidenceItemCreate,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> EvidenceItem:
    """Create new evidence item for curation"""

    # Check permissions
    curation = db.query(CurationNew).filter(CurationNew.id == curation_id).first()
    if not curation:
        raise HTTPException(status_code=404, detail="Curation not found")

    if not ScopePermissionService.can_edit_curation(db, current_user, curation):
        raise HTTPException(status_code=403, detail="Cannot edit this curation")

    # Create evidence item
    evidence = evidence_crud.create_with_curation(
        db, obj_in=evidence_in, curation_id=curation_id, user_id=current_user.id
    )

    return evidence


@router.put("/curations/{curation_id}/evidence/{item_id}", response_model=EvidenceItem)
def update_evidence_item(
    *,
    db: Session = Depends(get_db),
    curation_id: UUID,
    item_id: UUID,
    evidence_in: EvidenceItemUpdate,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> EvidenceItem:
    """Update evidence item"""

    # Check permissions
    curation = db.query(CurationNew).filter(CurationNew.id == curation_id).first()
    if not curation:
        raise HTTPException(status_code=404, detail="Curation not found")

    if not ScopePermissionService.can_edit_curation(db, current_user, curation):
        raise HTTPException(status_code=403, detail="Cannot edit this curation")

    # Get evidence item
    evidence = evidence_crud.get(db, id=item_id)
    if not evidence or evidence.curation_id != curation_id:
        raise HTTPException(status_code=404, detail="Evidence item not found")

    # Update
    evidence = evidence_crud.update(
        db, db_obj=evidence, obj_in=evidence_in, updated_by=current_user.id
    )

    return evidence


@router.delete("/curations/{curation_id}/evidence/{item_id}")
def delete_evidence_item(
    *,
    db: Session = Depends(get_db),
    curation_id: UUID,
    item_id: UUID,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> dict[str, str]:
    """Delete evidence item (soft delete)"""

    # Check permissions
    curation = db.query(CurationNew).filter(CurationNew.id == curation_id).first()
    if not curation:
        raise HTTPException(status_code=404, detail="Curation not found")

    if not ScopePermissionService.can_edit_curation(db, current_user, curation):
        raise HTTPException(status_code=403, detail="Cannot edit this curation")

    # Get evidence item
    evidence = evidence_crud.get(db, id=item_id)
    if not evidence or evidence.curation_id != curation_id:
        raise HTTPException(status_code=404, detail="Evidence item not found")

    # Soft delete
    evidence_crud.soft_delete(db, db_obj=evidence, deleted_by=current_user.id)

    return {"message": "Evidence item deleted"}


@router.get("/curations/{curation_id}/evidence", response_model=list[EvidenceItem])
def get_evidence_items(
    *,
    db: Session = Depends(get_db),
    curation_id: UUID,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> list[EvidenceItem]:
    """Get all evidence items for curation"""

    # Check permissions
    curation = db.query(CurationNew).filter(CurationNew.id == curation_id).first()
    if not curation:
        raise HTTPException(status_code=404, detail="Curation not found")

    if not ScopePermissionService.can_view_curation(db, current_user, curation):
        raise HTTPException(status_code=403, detail="Cannot view this curation")

    # Get evidence items
    evidence_items = evidence_crud.get_by_curation(db, curation_id=curation_id)

    return evidence_items
```

---

### 2. Gene Summary Endpoints

**File**: `backend/app/api/v1/endpoints/gene_summaries.py`

```python
"""Gene summary endpoints"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core import deps
from app.core.database import get_db
from app.models.models import UserNew
from app.schemas.gene_summary import GeneSummaryFull, GeneSummaryPublic, ScopeSummary
from app.services.gene_summary_service import GeneSummaryService

router = APIRouter()


@router.get("/genes/{gene_id}/summary", response_model=GeneSummaryPublic)
def get_gene_public_summary(
    *,
    db: Session = Depends(get_db),
    gene_id: UUID,
) -> GeneSummaryPublic:
    """Get public gene summary (no authentication required)"""

    service = GeneSummaryService(db)
    summary = service.get_public_summary(gene_id)

    if not summary:
        raise HTTPException(
            status_code=404,
            detail="No public curations found for this gene"
        )

    return summary


@router.get("/genes/{gene_id}/summary/full", response_model=GeneSummaryFull)
def get_gene_full_summary(
    *,
    db: Session = Depends(get_db),
    gene_id: UUID,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> GeneSummaryFull:
    """Get complete gene summary including private scopes (requires authentication)"""

    service = GeneSummaryService(db)
    summary = service.compute_summary(gene_id)  # Always recompute for authenticated

    if not summary:
        raise HTTPException(status_code=404, detail="Gene not found")

    # Filter scope summaries based on user permissions
    visible_scope_ids = [
        str(s.id)
        for s in ScopePermissionService.get_visible_scopes(db, current_user)
    ]

    filtered_scope_summaries = [
        s for s in summary.scope_summaries
        if s.get("scope_id") in visible_scope_ids
    ]

    return GeneSummaryFull(
        gene_id=summary.gene_id,
        total_scopes_curated=len(filtered_scope_summaries),
        public_scopes_count=sum(1 for s in filtered_scope_summaries if s.get("is_public")),
        private_scopes_count=sum(1 for s in filtered_scope_summaries if not s.get("is_public")),
        classification_summary=summary.classification_summary,
        consensus_classification=summary.consensus_classification,
        consensus_confidence=summary.consensus_confidence,
        has_conflicts=summary.has_conflicts,
        scope_summaries=filtered_scope_summaries,
        last_updated=summary.last_computed_at,
    )


@router.get("/genes/{gene_id}/scopes", response_model=list[dict])
def get_gene_curating_scopes(
    *,
    db: Session = Depends(get_db),
    gene_id: UUID,
    current_user: Optional[UserNew] = Depends(deps.get_current_user_optional),
) -> list[dict]:
    """Get list of scopes curating this gene"""

    # Get curations
    query = db.query(CurationNew).filter(
        CurationNew.gene_id == gene_id,
        CurationNew.is_current == True,
        CurationNew.stage == "active"
    )

    # Apply visibility filter
    query = ScopePermissionService.filter_visible_curations(db, query, current_user)

    curations = query.all()

    # Get unique scopes
    scope_ids = list(set([c.scope_id for c in curations]))
    scopes = db.query(Scope).filter(Scope.id.in_(scope_ids)).all()

    return [
        {
            "scope_id": str(scope.id),
            "scope_name": scope.name,
            "is_public": scope.is_public,
            "curation_count": sum(1 for c in curations if c.scope_id == scope.id),
        }
        for scope in scopes
    ]


@router.post("/genes/{gene_id}/summary/recompute")
def recompute_gene_summary(
    *,
    db: Session = Depends(get_db),
    gene_id: UUID,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> dict[str, str]:
    """Manually trigger gene summary recomputation (admin only)"""

    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    service = GeneSummaryService(db)
    service.compute_summary(gene_id)

    return {"message": "Gene summary recomputed"}
```

---

### 3. Validation Endpoints

**File**: `backend/app/api/v1/endpoints/validation.py`

```python
"""External validation endpoints"""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core import deps
from app.core.database import get_db
from app.models.models import UserNew
from app.schemas.validation import ValidationRequest, ValidationResult
from app.services.validation_service import ValidationService

router = APIRouter()


@router.post("/validation/validate", response_model=dict[str, ValidationResult])
async def validate_batch(
    *,
    db: Session = Depends(get_db),
    request: ValidationRequest,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> dict[str, ValidationResult]:
    """Batch validate values using specified validator"""

    service = ValidationService(db)
    results = await service.validate_batch(
        request.validator_name,
        request.values
    )

    return results


@router.post("/validation/hgnc", response_model=ValidationResult)
async def validate_hgnc(
    *,
    db: Session = Depends(get_db),
    gene_symbol: str,
    skip_cache: bool = False,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> ValidationResult:
    """Validate gene symbol against HGNC"""

    service = ValidationService(db)
    result = await service.validate("hgnc", gene_symbol, skip_cache=skip_cache)

    return result


@router.post("/validation/pubmed", response_model=ValidationResult)
async def validate_pubmed(
    *,
    db: Session = Depends(get_db),
    pmid: str,
    skip_cache: bool = False,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> ValidationResult:
    """Validate PMID against PubMed"""

    service = ValidationService(db)
    result = await service.validate("pubmed", pmid, skip_cache=skip_cache)

    return result


@router.post("/validation/hpo", response_model=ValidationResult)
async def validate_hpo(
    *,
    db: Session = Depends(get_db),
    hpo_term: str,
    skip_cache: bool = False,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> ValidationResult:
    """Validate HPO term against OLS"""

    service = ValidationService(db)
    result = await service.validate("hpo", hpo_term, skip_cache=skip_cache)

    return result
```

---

## Pydantic Schemas

**File**: `backend/app/schemas/evidence.py`

```python
"""Evidence item schemas"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel


class EvidenceItemBase(BaseModel):
    evidence_category: str
    evidence_type: str
    evidence_data: dict[str, Any]


class EvidenceItemCreate(EvidenceItemBase):
    pass


class EvidenceItemUpdate(BaseModel):
    evidence_data: Optional[dict[str, Any]] = None
    validation_status: Optional[str] = None


class EvidenceItem(EvidenceItemBase):
    id: UUID
    curation_id: UUID
    computed_score: Optional[float] = None
    validation_status: str
    created_at: datetime
    updated_at: datetime
    created_by: UUID

    model_config = {"from_attributes": True}
```

**File**: `backend/app/schemas/gene_summary.py`

```python
"""Gene summary schemas"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel


class ScopeSummary(BaseModel):
    scope_id: UUID
    scope_name: str
    is_public: bool
    classification: Optional[str] = None
    genetic_score: float
    experimental_score: float
    total_score: float
    last_updated: datetime
    curator_count: int
    evidence_count: int


class GeneSummaryPublic(BaseModel):
    gene_id: UUID
    public_scopes_count: int
    classification_summary: dict[str, int]
    consensus_classification: Optional[str] = None
    has_conflicts: bool
    scope_summaries: list[dict[str, Any]]
    last_updated: datetime


class GeneSummaryFull(GeneSummaryPublic):
    total_scopes_curated: int
    private_scopes_count: int
    consensus_confidence: Optional[float] = None
```

**File**: `backend/app/schemas/validation.py`

```python
"""Validation schemas"""

from typing import Any, Optional

from pydantic import BaseModel


class ValidationResult(BaseModel):
    is_valid: bool
    status: str  # 'valid', 'invalid', 'not_found', 'error'
    data: Optional[dict[str, Any]] = None
    suggestions: Optional[dict[str, list[str]]] = None
    error_message: Optional[str] = None


class ValidationRequest(BaseModel):
    validator_name: str
    values: list[str]
```

---

## CRUD Operations

**File**: `backend/app/crud/evidence.py`

```python
"""Evidence CRUD operations"""

from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.models import EvidenceItem
from app.schemas.evidence import EvidenceItemCreate, EvidenceItemUpdate


class CRUDEvidence(CRUDBase[EvidenceItem, EvidenceItemCreate, EvidenceItemUpdate]):
    def create_with_curation(
        self,
        db: Session,
        *,
        obj_in: EvidenceItemCreate,
        curation_id: UUID,
        user_id: UUID
    ) -> EvidenceItem:
        """Create evidence item for curation"""
        db_obj = EvidenceItem(
            **obj_in.model_dump(),
            curation_id=curation_id,
            created_by=user_id
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_by_curation(
        self,
        db: Session,
        *,
        curation_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> list[EvidenceItem]:
        """Get all evidence items for curation"""
        return (
            db.query(EvidenceItem)
            .filter(
                EvidenceItem.curation_id == curation_id,
                EvidenceItem.is_deleted == False
            )
            .order_by(EvidenceItem.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def soft_delete(
        self,
        db: Session,
        *,
        db_obj: EvidenceItem,
        deleted_by: UUID
    ) -> EvidenceItem:
        """Soft delete evidence item"""
        db_obj.is_deleted = True
        db_obj.deleted_at = func.now()
        db_obj.deleted_by = deleted_by
        db.commit()
        db.refresh(db_obj)
        return db_obj


evidence_crud = CRUDEvidence(EvidenceItem)
```

---

## Testing Checklist

### Unit Tests
- [ ] ClinGen scoring engine (all evidence categories)
- [ ] LOD score calculations (dominant/recessive)
- [ ] Classification thresholds
- [ ] External validators (HGNC, PubMed, HPO)
- [ ] Validation caching logic
- [ ] Scope permission checks
- [ ] Gene summary aggregation

### Integration Tests
- [ ] Create evidence item (with permissions)
- [ ] Update evidence item (concurrency control)
- [ ] Delete evidence item (soft delete)
- [ ] Compute gene summary across scopes
- [ ] Public vs authenticated summary filtering
- [ ] Validation cache hit/miss
- [ ] External API failures (with graceful degradation)

### API Tests
- [ ] POST /curations/{id}/evidence (201, 403, 404)
- [ ] PUT /curations/{id}/evidence/{item_id} (200, 403, 404)
- [ ] DELETE /curations/{id}/evidence/{item_id} (200, 403, 404)
- [ ] GET /genes/{id}/summary (200, 404)
- [ ] GET /genes/{id}/summary/full (200, 401, 404)
- [ ] POST /validation/hgnc (200, timeout handling)
- [ ] POST /validation/pubmed (200, timeout handling)
- [ ] POST /validation/hpo (200, timeout handling)

---

## Next Steps

1. **Review** this document with backend team
2. **Implement** service layer (ScopePermissionService, ValidationService, GeneSummaryService)
3. **Implement** scoring engine (ClinGenEngine with complete evidence categories)
4. **Implement** external validators (HGNC, PubMed, HPO)
5. **Implement** API endpoints (evidence, summaries, validation)
6. **Write** comprehensive tests (unit + integration + API)
7. **Move to** frontend implementation (see `frontend_implementation.md`)

---

**Document Status**: ✅ Ready for Implementation
**Estimated Effort**: 4-5 weeks (Phase 2)
**Dependencies**: Database implementation (Phase 1) must be complete
