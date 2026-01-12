"""External validation service with TTL-based caching

This service coordinates external API validators (HGNC, PubMed, HPO) with
intelligent caching to minimize API calls and improve performance.

Design Principles:
- Single Responsibility: Only handles validation coordination and caching
- Dependency Inversion: Depends on ExternalValidator abstraction
- Open/Closed: Easy to add new validators via configuration
"""

import hashlib
from datetime import datetime, timedelta
from typing import Final

from sqlalchemy.orm import Session

from app.core.logging import get_logger, timed_operation
from app.models.models import ValidationCache
from app.schemas.validation import ValidationResult
from app.services.validators import HGNCValidator, HPOValidator, PubMedValidator
from app.services.validators.base import ExternalValidator

logger = get_logger(__name__)


class ValidationService:
    """Centralized validation service with intelligent TTL-based caching

    Features:
    - SHA256-based cache keys for consistent lookups
    - TTL-based expiration (different per validator type)
    - Cache hit/miss metrics tracking
    - Graceful degradation on validator failures
    - Batch validation support
    """

    # TTL configuration (in days) - follows domain semantics
    # Gene symbols: rarely change (30 days)
    # Publications: immutable once published (90 days)
    # Ontology terms: updated more frequently (14 days)
    TTL_DAYS: Final[dict[str, int]] = {
        "hgnc": 30,
        "pubmed": 90,
        "hpo": 14,
    }

    def __init__(self, db: Session) -> None:
        """Initialize validation service

        Args:
            db: Database session for cache operations
        """
        self.db = db

        # Initialize validators (Dependency Injection pattern)
        self.validators: dict[str, ExternalValidator] = {
            "hgnc": HGNCValidator(),
            "pubmed": PubMedValidator(),
            "hpo": HPOValidator(),
        }

        logger.debug(
            "ValidationService initialized",
            validator_count=len(self.validators),
            ttl_config=self.TTL_DAYS,
        )

    def _generate_cache_key(self, validator_name: str, input_value: str) -> str:
        """Generate deterministic cache key using SHA256

        Design: Case-insensitive, whitespace-normalized keys prevent
        duplicate cache entries for semantically identical values.

        Args:
            validator_name: Type of validator (hgnc, pubmed, hpo)
            input_value: Value to validate

        Returns:
            64-character hex string (SHA256 hash)
        """
        # Normalize input for consistent caching
        normalized = f"{validator_name}:{input_value.lower().strip()}"
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @timed_operation("cache_lookup", warning_threshold_ms=50)
    def _get_cached_result(
        self, validator_name: str, input_value: str
    ) -> ValidationResult | None:
        """Retrieve validation result from cache if available and not expired

        Args:
            validator_name: Type of validator
            input_value: Value to validate

        Returns:
            Cached ValidationResult if found and valid, None otherwise
        """
        cache_key = self._generate_cache_key(validator_name, input_value)

        # Query with expiration check in single database hit
        cached = (
            self.db.query(ValidationCache)
            .filter(
                ValidationCache.validator_input_hash == cache_key,
                ValidationCache.expires_at > datetime.now(),
            )
            .first()
        )

        if cached:
            # Update access metrics (analytics for cache optimization)
            cached.access_count += 1
            cached.last_accessed_at = datetime.now()
            self.db.commit()

            logger.info(
                "Validation cache HIT",
                validator=validator_name,
                input_value=input_value[:50],  # Truncate for logs
                access_count=cached.access_count,
                ttl_remaining_days=(cached.expires_at - datetime.now()).days,
            )

            return ValidationResult(
                is_valid=cached.is_valid,
                status=cached.validation_status,
                data=cached.validation_response,
                suggestions=cached.suggestions,
                error_message=cached.error_message,
                error_code=cached.error_code,
            )

        logger.info(
            "Validation cache MISS",
            validator=validator_name,
            input_value=input_value[:50],
        )
        return None

    def _cache_result(
        self, validator_name: str, input_value: str, result: ValidationResult
    ) -> None:
        """Store validation result in cache with TTL

        Args:
            validator_name: Type of validator
            input_value: Value that was validated
            result: Validation result to cache
        """
        cache_key = self._generate_cache_key(validator_name, input_value)
        ttl_days = self.TTL_DAYS.get(validator_name, 7)  # Default 7 days
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
            error_code=result.error_code,
            expires_at=expires_at,
            access_count=0,  # Will be incremented on first access
        )

        self.db.add(cache_entry)
        self.db.commit()

        logger.info(
            "Validation result cached",
            validator=validator_name,
            input_value=input_value[:50],
            is_valid=result.is_valid,
            ttl_days=ttl_days,
            expires_at=expires_at.isoformat(),
        )

    @timed_operation("validation", warning_threshold_ms=5000)
    async def validate(
        self, validator_name: str, input_value: str, skip_cache: bool = False
    ) -> ValidationResult:
        """Validate input using specified validator with caching

        Args:
            validator_name: Type of validator (hgnc, pubmed, hpo)
            input_value: Value to validate
            skip_cache: If True, bypass cache (for testing/refresh)

        Returns:
            ValidationResult with validation outcome

        Raises:
            No exceptions - returns ValidationResult with error status on failure
        """
        # Input validation
        if not input_value or not input_value.strip():
            return ValidationResult(
                is_valid=False,
                status="invalid",
                error_message="Input value cannot be empty",
                error_code="EMPTY_INPUT",
            )

        # Check cache first (unless explicitly skipped)
        if not skip_cache:
            cached_result = self._get_cached_result(validator_name, input_value)
            if cached_result:
                return cached_result

        # Get validator
        validator = self.validators.get(validator_name)
        if not validator:
            logger.error("Unknown validator requested", validator_name=validator_name)
            return ValidationResult(
                is_valid=False,
                status="error",
                error_message=f"Unknown validator: {validator_name}",
                error_code="UNKNOWN_VALIDATOR",
            )

        # Perform validation (calls external API)
        try:
            result = await validator.validate(input_value)

            # Cache successful AND failed validations
            # (prevents repeated calls for invalid inputs)
            self._cache_result(validator_name, input_value, result)

            return result

        except Exception as e:
            # Graceful degradation: return error result instead of raising
            logger.error(
                "Validation failed",
                validator=validator_name,
                input_value=input_value[:50],
                error=e,
            )

            return ValidationResult(
                is_valid=False,
                status="error",
                error_message=f"Validation error: {e!s}",
                error_code="VALIDATION_EXCEPTION",
            )

    async def validate_batch(
        self, validator_name: str, input_values: list[str]
    ) -> dict[str, ValidationResult]:
        """Validate multiple values efficiently

        Design: Processes values sequentially to respect API rate limits.
        Cache hits are still fast, only cache misses incur API latency.

        Args:
            validator_name: Type of validator
            input_values: List of values to validate

        Returns:
            Dictionary mapping input values to ValidationResults
        """
        if not input_values:
            logger.warning("Empty batch validation requested")
            return {}

        logger.info(
            "Batch validation started",
            validator=validator_name,
            total_values=len(input_values),
        )

        results: dict[str, ValidationResult] = {}

        for value in input_values:
            results[value] = await self.validate(validator_name, value)

        # Calculate batch statistics
        valid_count = sum(1 for r in results.values() if r.is_valid)
        cache_hit_count = sum(
            1
            for v in input_values
            if self._get_cached_result(validator_name, v) is not None
        )

        logger.info(
            "Batch validation completed",
            validator=validator_name,
            total=len(input_values),
            valid=valid_count,
            invalid=len(input_values) - valid_count,
            cache_hit_rate=f"{(cache_hit_count / len(input_values) * 100):.1f}%",
        )

        return results

    async def cleanup_expired_cache(self) -> int:
        """Remove expired cache entries (maintenance operation)

        Returns:
            Number of entries deleted
        """
        deleted_count = (
            self.db.query(ValidationCache)
            .filter(ValidationCache.expires_at <= datetime.now())
            .delete()
        )

        self.db.commit()

        if deleted_count > 0:
            logger.info("Expired cache entries cleaned up", deleted_count=deleted_count)

        return deleted_count

    def get_cache_statistics(self) -> dict[str, int]:
        """Get cache statistics for monitoring

        Returns:
            Dictionary with cache metrics
        """
        total_entries = self.db.query(ValidationCache).count()
        expired_entries = (
            self.db.query(ValidationCache)
            .filter(ValidationCache.expires_at <= datetime.now())
            .count()
        )

        stats_by_validator = {}
        for validator_name in self.validators:
            count = (
                self.db.query(ValidationCache)
                .filter(ValidationCache.validator_name == validator_name)
                .count()
            )
            stats_by_validator[validator_name] = count

        return {
            "total_entries": total_entries,
            "active_entries": total_entries - expired_entries,
            "expired_entries": expired_entries,
            **stats_by_validator,
        }
