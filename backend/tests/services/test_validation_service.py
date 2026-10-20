"""Behaviour tests for ValidationService: TTL cache, refresh, batch and maintenance."""

import hashlib
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.orm import Session

from app.models.models import ValidationCache
from app.schemas.validation import ValidationResult
from app.services.validation_service import ValidationService


def _valid(symbol: str = "BRCA1") -> ValidationResult:
    return ValidationResult(
        is_valid=True, status="valid", data={"approved_symbol": symbol}
    )


@pytest.fixture
def service(db_session: Session) -> ValidationService:
    svc = ValidationService(db_session)
    # Replace real HTTP-backed validators with mocks at the validator boundary.
    for name in list(svc.validators):
        svc.validators[name] = AsyncMock()
    return svc


def _mock(service: ValidationService, name: str = "hgnc") -> AsyncMock:
    mock = service.validators[name]
    assert isinstance(mock, AsyncMock)
    return mock


def test_cache_key_is_case_and_whitespace_insensitive(
    service: ValidationService,
) -> None:
    a = service._generate_cache_key("hgnc", "  BRCA1 ")
    b = service._generate_cache_key("hgnc", "brca1")
    c = service._generate_cache_key("hpo", "brca1")

    assert a == b
    assert a != c
    assert len(a) == 64


@pytest.mark.asyncio
async def test_empty_input_is_rejected_without_calling_validator(
    service: ValidationService,
) -> None:
    result = await service.validate("hgnc", "   ")

    assert result.status == "invalid"
    assert result.error_code == "EMPTY_INPUT"
    _mock(service).validate.assert_not_called()


@pytest.mark.asyncio
async def test_unknown_validator_returns_error_result(
    service: ValidationService,
) -> None:
    result = await service.validate("omim", "123")

    assert result.status == "error"
    assert result.error_code == "UNKNOWN_VALIDATOR"


@pytest.mark.asyncio
async def test_miss_then_hit_uses_cache_and_counts_access(
    service: ValidationService, db_session: Session
) -> None:
    mock = _mock(service)
    mock.validate.return_value = _valid()

    first = await service.validate("hgnc", "BRCA1")
    second = await service.validate("hgnc", "brca1")

    assert first.is_valid is True
    assert second.is_valid is True
    assert second.data == {"approved_symbol": "BRCA1"}
    mock.validate.assert_awaited_once()  # second call served from cache

    entry = db_session.query(ValidationCache).one()
    assert entry.validator_name == "hgnc"
    assert entry.access_count == 1
    assert entry.expires_at > datetime.now() + timedelta(days=29)


@pytest.mark.asyncio
async def test_skip_cache_bypasses_lookup(service: ValidationService) -> None:
    mock = _mock(service)
    mock.validate.return_value = _valid()

    await service.validate("hgnc", "BRCA1")
    await service.validate("hgnc", "BRCA1", skip_cache=True)

    assert mock.validate.await_count == 2


@pytest.mark.asyncio
async def test_validator_exception_is_converted_to_error_result(
    service: ValidationService, db_session: Session
) -> None:
    _mock(service).validate.side_effect = RuntimeError("boom")

    result = await service.validate("hgnc", "BRCA1")

    assert result.status == "error"
    assert result.error_code == "VALIDATION_EXCEPTION"
    assert "boom" in (result.error_message or "")
    assert db_session.query(ValidationCache).count() == 0


@pytest.mark.asyncio
async def test_transient_error_results_are_not_cached(
    service: ValidationService,
) -> None:
    mock = _mock(service)
    mock.validate.side_effect = [
        ValidationResult(
            is_valid=False,
            status="error",
            error_message="timed out",
            error_code="TIMEOUT",
        ),
        _valid(),
    ]

    first = await service.validate("hgnc", "BRCA1")
    second = await service.validate("hgnc", "BRCA1")

    assert first.status == "error"
    assert second.is_valid is True  # retry reaches the validator again
    assert mock.validate.await_count == 2


@pytest.mark.asyncio
async def test_expired_entry_is_refreshed_in_place(
    service: ValidationService, db_session: Session
) -> None:
    mock = _mock(service)
    mock.validate.return_value = _valid("BRCA1")
    await service.validate("hgnc", "BRCA1")

    # Age the cache entry past its TTL.
    entry = db_session.query(ValidationCache).one()
    entry.expires_at = datetime.now() - timedelta(days=1)
    db_session.commit()

    refreshed = await service.validate("hgnc", "BRCA1")

    assert refreshed.is_valid is True
    assert db_session.query(ValidationCache).count() == 1


@pytest.mark.asyncio
async def test_skip_cache_refresh_updates_existing_row(
    service: ValidationService, db_session: Session
) -> None:
    mock = _mock(service)
    mock.validate.return_value = _valid("BRCA1")
    await service.validate("hgnc", "BRCA1")

    mock.validate.return_value = ValidationResult(
        is_valid=False, status="not_found", error_message="gone"
    )
    refreshed = await service.validate("hgnc", "BRCA1", skip_cache=True)

    assert refreshed.status == "not_found"
    assert db_session.query(ValidationCache).count() == 1


@pytest.mark.asyncio
async def test_validate_batch_empty_returns_empty_dict(
    service: ValidationService,
) -> None:
    assert await service.validate_batch("hgnc", []) == {}


@pytest.mark.asyncio
async def test_validate_batch_returns_result_per_value(
    service: ValidationService,
) -> None:
    mock = _mock(service)
    mock.validate.side_effect = [
        _valid("BRCA1"),
        ValidationResult(is_valid=False, status="not_found", error_message="nope"),
    ]

    results = await service.validate_batch("hgnc", ["BRCA1", "XXXX"])

    assert results["BRCA1"].is_valid is True
    assert results["XXXX"].status == "not_found"


@pytest.mark.asyncio
async def test_validate_batch_reports_pre_existing_cache_hits(
    service: ValidationService,
) -> None:
    mock = _mock(service)
    mock.validate.return_value = _valid("BRCA1")
    await service.validate("hgnc", "BRCA1")  # warm cache for BRCA1 only
    mock.validate.reset_mock()

    results = await service.validate_batch("hgnc", ["BRCA1", "TP53"])

    assert set(results) == {"BRCA1", "TP53"}
    # BRCA1 was served from cache, so only TP53 hit the validator.
    assert mock.validate.await_count == 1


@pytest.mark.asyncio
async def test_cleanup_removes_only_expired_entries(
    service: ValidationService, db_session: Session
) -> None:
    now = datetime.now()
    db_session.add_all(
        [
            _entry("hgnc", "OLD", now - timedelta(days=1)),
            _entry("hgnc", "NEW", now + timedelta(days=1)),
        ]
    )
    db_session.commit()

    deleted = await service.cleanup_expired_cache()

    assert deleted == 1
    remaining = [e.input_value for e in db_session.query(ValidationCache).all()]
    assert remaining == ["NEW"]


def test_cache_statistics_split_active_and_expired(
    service: ValidationService, db_session: Session
) -> None:
    now = datetime.now()
    db_session.add_all(
        [
            _entry("hgnc", "A", now + timedelta(days=1)),
            _entry("hgnc", "B", now - timedelta(days=1)),
            _entry("hpo", "HP:0000001", now + timedelta(days=1)),
        ]
    )
    db_session.commit()

    stats: dict[str, Any] = service.get_cache_statistics()

    assert stats["total_entries"] == 3
    assert stats["expired_entries"] == 1
    assert stats["active_entries"] == 2
    assert stats["hgnc"] == 2
    assert stats["hpo"] == 1
    assert stats["pubmed"] == 0


def _entry(validator: str, value: str, expires_at: datetime) -> ValidationCache:
    key = hashlib.sha256(f"{validator}:{value.lower()}".encode()).hexdigest()
    return ValidationCache(
        validator_name=validator,
        input_value=value,
        validator_input_hash=key,
        is_valid=True,
        validation_status="valid",
        validation_response={},
        expires_at=expires_at,
        access_count=0,
    )
