"""Unit tests for curation schemas.

Tests Pydantic schema validation without database dependencies.
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.schemas.curation import (
    Curation,
    CurationCreate,
    CurationDraftSave,
    CurationListResponse,
    CurationSubmit,
    CurationSummary,
    CurationUpdate,
)

pytestmark = pytest.mark.unit


class TestCurationCreate:
    """Tests for CurationCreate schema."""

    def test_valid_curation_create(self):
        """Test valid curation creation data."""
        data = CurationCreate(
            gene_id=uuid4(),
            scope_id=uuid4(),
            workflow_pair_id=uuid4(),
            evidence_data={"test": "data"},
        )
        assert data.gene_id is not None
        assert data.scope_id is not None
        assert data.workflow_pair_id is not None
        assert data.evidence_data == {"test": "data"}

    def test_curation_create_with_precuration(self):
        """Test curation creation with precuration reference."""
        precuration_id = uuid4()
        data = CurationCreate(
            gene_id=uuid4(),
            scope_id=uuid4(),
            workflow_pair_id=uuid4(),
            precuration_id=precuration_id,
        )
        assert data.precuration_id == precuration_id

    def test_curation_create_empty_evidence(self):
        """Test curation creation with empty evidence data."""
        data = CurationCreate(
            gene_id=uuid4(),
            scope_id=uuid4(),
            workflow_pair_id=uuid4(),
        )
        assert data.evidence_data == {}


class TestCurationUpdate:
    """Tests for CurationUpdate schema."""

    def test_valid_curation_update(self):
        """Test valid curation update data."""
        data = CurationUpdate(
            evidence_data={"updated": "evidence"},
            lock_version=1,
        )
        assert data.evidence_data == {"updated": "evidence"}
        assert data.lock_version == 1

    def test_curation_update_lock_version_required(self):
        """Test that lock_version is required."""
        with pytest.raises(ValueError):
            CurationUpdate(evidence_data={"test": "data"})

    def test_curation_update_forbids_extra_fields(self):
        """Test that extra fields are forbidden."""
        with pytest.raises(ValueError):
            CurationUpdate(
                evidence_data={"test": "data"},
                lock_version=1,
                invalid_field="should fail",
            )


class TestCurationDraftSave:
    """Tests for CurationDraftSave schema."""

    def test_valid_draft_save(self):
        """Test valid draft save data."""
        data = CurationDraftSave(
            evidence_data={"draft": "data"},
        )
        assert data.evidence_data == {"draft": "data"}
        assert data.lock_version is None

    def test_draft_save_with_lock_version(self):
        """Test draft save with optional lock version."""
        data = CurationDraftSave(
            evidence_data={"draft": "data"},
            lock_version=5,
        )
        assert data.lock_version == 5


class TestCurationSubmit:
    """Tests for CurationSubmit schema."""

    def test_valid_submit(self):
        """Test valid submission data."""
        data = CurationSubmit(
            lock_version=3,
            notes="Ready for review",
        )
        assert data.lock_version == 3
        assert data.notes == "Ready for review"

    def test_submit_lock_version_required(self):
        """Test that lock_version is required for submission."""
        with pytest.raises(ValueError):
            CurationSubmit(notes="No version")

    def test_submit_notes_max_length(self):
        """Test notes max length validation."""
        long_notes = "x" * 1001
        with pytest.raises(ValueError):
            CurationSubmit(lock_version=1, notes=long_notes)


class TestCurationSummary:
    """Tests for CurationSummary schema."""

    def test_valid_summary(self):
        """Test valid curation summary."""
        now = datetime.now(timezone.utc)
        data = CurationSummary(
            id=uuid4(),
            gene_id=uuid4(),
            gene_symbol="BRCA1",
            scope_id=uuid4(),
            scope_name="test-scope",
            status="draft",
            workflow_stage="curation",
            computed_verdict=None,
            is_draft=True,
            created_at=now,
            updated_at=now,
            curator_name="Test Curator",
        )
        assert data.gene_symbol == "BRCA1"
        assert data.scope_name == "test-scope"
        assert data.is_draft is True


class TestCurationListResponse:
    """Tests for CurationListResponse schema."""

    def test_empty_list_response(self):
        """Test empty list response."""
        data = CurationListResponse(
            curations=[],
            total=0,
            skip=0,
            limit=50,
        )
        assert data.curations == []
        assert data.total == 0

    def test_list_response_with_curations(self):
        """Test list response with curations."""
        now = datetime.now(timezone.utc)
        summary = CurationSummary(
            id=uuid4(),
            gene_id=uuid4(),
            gene_symbol="TP53",
            scope_id=uuid4(),
            scope_name="cancer-genetics",
            status="submitted",
            workflow_stage="review",
            computed_verdict="Moderate",
            is_draft=False,
            created_at=now,
            updated_at=now,
            curator_name=None,
        )
        data = CurationListResponse(
            curations=[summary],
            total=1,
            skip=0,
            limit=50,
        )
        assert len(data.curations) == 1
        assert data.curations[0].gene_symbol == "TP53"


class TestCuration:
    """Tests for Curation (full response) schema."""

    def test_curation_from_attributes(self):
        """Test Curation can be created from attributes (ORM-style)."""
        # Create a mock object with attributes
        now = datetime.now(timezone.utc)
        mock_data = {
            "id": uuid4(),
            "gene_id": uuid4(),
            "scope_id": uuid4(),
            "workflow_pair_id": uuid4(),
            "precuration_id": None,
            "evidence_data": {"test": "data"},
            "status": "draft",
            "workflow_stage": "curation",
            "is_draft": True,
            "computed_scores": {},
            "computed_verdict": None,
            "computed_summary": None,
            "lock_version": 0,
            "created_at": now,
            "updated_at": now,
            "submitted_at": None,
            "approved_at": None,
            "auto_saved_at": None,
            "created_by": uuid4(),
            "updated_by": uuid4(),
            "submitted_by": None,
            "approved_by": None,
        }

        curation = Curation.model_validate(mock_data)
        assert curation.is_draft is True
        assert curation.lock_version == 0
        assert curation.status == "draft"
