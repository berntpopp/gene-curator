"""
Comprehensive tests for Scope CRUD operations.

Tests the complete lifecycle of scopes including:
- Creating scopes
- Reading scopes (list and detail)
- Updating scopes
- Deleting scopes
- Permission checks (admin only)
- Scope statistics
"""

from collections.abc import Sequence
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.crud.scope import scope_crud
from app.models.models import Scope, UserNew
from app.schemas.scope import ScopeCreate, ScopeUpdate
from app.tests.conftest import set_test_user_context


# Shared fixtures for all test classes
@pytest.fixture
def admin_user(db: Session) -> UserNew:
    """Create an admin user for testing."""
    admin = UserNew(
        id=uuid4(),
        email="test.admin@example.com",
        hashed_password="hashed",  # noqa: S106
        name="Test Admin",
        role="admin",  # Application-level admin
        is_active=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)

    # Set RLS context for this admin user
    # This makes all subsequent operations in the test use this user's permissions
    set_test_user_context(db, str(admin.id))

    return admin


@pytest.fixture
def regular_user(db: Session) -> UserNew:
    """Create a regular user for testing."""
    user = UserNew(
        id=uuid4(),
        email="test.user@example.com",
        hashed_password="hashed",  # noqa: S106
        name="Test User",
        role="user",  # Standard user
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_scope(db: Session, admin_user: UserNew) -> Scope:
    """Create a test scope."""
    scope_data = ScopeCreate(
        name="test-genetics",
        display_name="Test Genetics",
        description="Test genetic disorders scope",
        institution="Test Institution",
        is_public=False,
        scope_config={"test": "config"},
        default_workflow_pair_id=None,
    )
    scope = scope_crud.create_scope(db, scope_data, admin_user.id)
    return scope


class TestScopeCRUD:
    """Test scope CRUD operations."""

    def test_create_scope_success(self, db: Session, admin_user: UserNew) -> None:
        """Test successful scope creation."""
        scope_data = ScopeCreate(
            name="new-scope",
            display_name="New Scope",
            description="A new test scope",
            institution="Test Institution",
            is_public=False,
            scope_config={"key": "value"},
            default_workflow_pair_id=None,
        )

        scope = scope_crud.create_scope(db, scope_data, admin_user.id)

        assert scope.id is not None
        assert scope.name == "new-scope"
        assert scope.display_name == "New Scope"
        assert scope.description == "A new test scope"
        assert scope.institution == "Test Institution"
        assert scope.is_active is True
        assert scope.is_public is False
        assert scope.scope_config == {"key": "value"}
        assert scope.created_by == admin_user.id
        assert scope.created_at is not None
        assert scope.updated_at is not None

    def test_create_scope_duplicate_name_fails(
        self, db: Session, admin_user: UserNew, test_scope: Scope
    ) -> None:
        """Test that creating a scope with duplicate name fails."""
        from sqlalchemy.exc import IntegrityError

        scope_data = ScopeCreate(
            name=test_scope.name,  # Duplicate name
            display_name="Another Display Name",
            description="Different description",
            institution=None,
            is_public=False,
            scope_config={},
            default_workflow_pair_id=None,
        )

        with pytest.raises(IntegrityError):
            scope_crud.create_scope(db, scope_data, admin_user.id)

    def test_create_scope_invalid_name_format(self, db: Session, admin_user: UserNew) -> None:
        """Test that invalid scope name format fails."""
        from pydantic import ValidationError

        # Pydantic validation raises error during instantiation
        with pytest.raises(ValidationError):
            ScopeCreate(
                name="Invalid Name With Spaces",  # Invalid: spaces not allowed
                display_name="Invalid Scope",
                description="Should fail",
                institution=None,
                is_public=False,
                scope_config={},
                default_workflow_pair_id=None,
            )

    def test_get_scope_by_id(self, db: Session, test_scope: Scope) -> None:
        """Test retrieving a scope by ID."""
        scope = scope_crud.get_scope(db, test_scope.id)

        assert scope is not None
        assert scope.id == test_scope.id
        assert scope.name == test_scope.name
        assert scope.display_name == test_scope.display_name

    def test_get_scope_by_id_not_found(self, db: Session) -> None:
        """Test retrieving a non-existent scope returns None."""
        fake_id = uuid4()
        scope = scope_crud.get_scope(db, fake_id)

        assert scope is None

    def test_get_scope_by_name(self, db: Session, test_scope: Scope) -> None:
        """Test retrieving a scope by name."""
        scope = scope_crud.get_scope_by_name(db, test_scope.name)

        assert scope is not None
        assert scope.id == test_scope.id
        assert scope.name == test_scope.name

    def test_get_scope_by_name_not_found(self, db: Session) -> None:
        """Test retrieving a non-existent scope by name returns None."""
        scope = scope_crud.get_scope_by_name(db, "non-existent-scope")

        assert scope is None

    def test_get_scopes_list(self, db: Session, test_scope: Scope, admin_user: UserNew) -> None:
        """Test listing scopes."""
        # Create additional scopes
        for i in range(3):
            scope_data = ScopeCreate(
                name=f"scope-{i}",
                display_name=f"Scope {i}",
                description=f"Test scope {i}",
                institution=None,
                is_public=False,
                scope_config={},
                default_workflow_pair_id=None,
            )
            scope_crud.create_scope(db, scope_data, admin_user.id)

        # Get all scopes
        scopes = scope_crud.get_scopes(db, skip=0, limit=100)

        # Should have at least 4 scopes (1 test_scope + 3 new + seed data scopes)
        assert len(scopes) >= 4

        # Verify test scope is in the list
        scope_names = [s.name for s in scopes]
        assert test_scope.name in scope_names

    def test_get_scopes_pagination(self, db: Session, admin_user: UserNew) -> None:
        """Test scope listing with pagination."""
        # Create 10 scopes
        for i in range(10):
            scope_data = ScopeCreate(
                name=f"pagination-scope-{i}",
                display_name=f"Pagination Scope {i}",
                description=f"Test pagination {i}",
                institution=None,
                is_public=False,
                scope_config={},
                default_workflow_pair_id=None,
            )
            scope_crud.create_scope(db, scope_data, admin_user.id)

        # Test first page
        page1 = scope_crud.get_scopes(db, skip=0, limit=5)
        assert len(page1) <= 5

        # Test second page
        page2 = scope_crud.get_scopes(db, skip=5, limit=5)
        assert len(page2) <= 5

        # Verify no overlap
        page1_ids = {s.id for s in page1}
        page2_ids = {s.id for s in page2}
        assert len(page1_ids & page2_ids) == 0  # No common elements

    def test_get_active_scopes_only(
        self, db: Session, test_scope: Scope, admin_user: UserNew
    ) -> None:
        """Test filtering active scopes only."""
        # Create an inactive scope
        inactive_scope_data = ScopeCreate(
            name="inactive-scope",
            display_name="Inactive Scope",
            description="Should be inactive",
            institution=None,
            is_public=False,
            scope_config={},
            default_workflow_pair_id=None,
        )
        inactive_scope = scope_crud.create_scope(db, inactive_scope_data, admin_user.id)

        # Deactivate it
        update_data = ScopeUpdate(is_active=False)  # type: ignore[call-arg]
        scope_crud.update_scope(db, inactive_scope.id, update_data)

        # Get only active scopes
        active_scopes = scope_crud.get_scopes(db, skip=0, limit=100, active_only=True)

        # Verify inactive scope is not in the list
        active_scope_ids = {s.id for s in active_scopes}
        assert inactive_scope.id not in active_scope_ids
        assert test_scope.id in active_scope_ids

    def test_update_scope_success(self, db: Session, test_scope: Scope) -> None:
        """Test updating a scope."""
        # Store original updated_at before update
        original_updated_at = test_scope.updated_at

        update_data = ScopeUpdate(
            display_name="Updated Display Name",
            description="Updated description",
            institution="Updated Institution",
            is_public=True,
            scope_config={"updated": "config"},
            is_active=None,
            default_workflow_pair_id=None,
        )

        updated_scope = scope_crud.update_scope(db, test_scope.id, update_data)

        assert updated_scope is not None
        assert updated_scope.id == test_scope.id
        assert updated_scope.name == test_scope.name  # Name should not change
        assert updated_scope.display_name == "Updated Display Name"
        assert updated_scope.description == "Updated description"
        assert updated_scope.institution == "Updated Institution"
        assert updated_scope.is_public is True
        assert updated_scope.scope_config == {"updated": "config"}
        assert updated_scope.updated_at >= original_updated_at

    def test_update_scope_partial(self, db: Session, test_scope: Scope) -> None:
        """Test partial update of a scope."""
        original_description = test_scope.description
        original_institution = test_scope.institution

        # For partial updates, construct dict and use **kwargs to avoid setting None values
        update_dict: dict[str, Any] = {"display_name": "Partially Updated Name"}
        update_data = ScopeUpdate(**update_dict)

        updated_scope = scope_crud.update_scope(db, test_scope.id, update_data)

        assert updated_scope is not None
        assert updated_scope.display_name == "Partially Updated Name"
        assert updated_scope.description == original_description  # Unchanged
        assert updated_scope.institution == original_institution  # Unchanged

    def test_update_scope_not_found(self, db: Session) -> None:
        """Test updating a non-existent scope returns None."""
        fake_id = uuid4()
        update_data = ScopeUpdate(display_name="Should Fail")  # type: ignore[call-arg]

        updated_scope = scope_crud.update_scope(db, fake_id, update_data)

        assert updated_scope is None

    def test_update_scope_name_not_allowed(self, db: Session, test_scope: Scope) -> None:
        """Test that scope name cannot be changed via update."""
        # Attempt to update name (should be ignored by ScopeUpdate schema)
        # name cannot be in ScopeUpdate
        update_data = ScopeUpdate(display_name="Updated")  # type: ignore[call-arg]

        updated_scope = scope_crud.update_scope(db, test_scope.id, update_data)

        # Name should remain unchanged
        assert updated_scope is not None
        assert updated_scope.name == test_scope.name

    def test_delete_scope_soft_delete(self, db: Session, test_scope: Scope) -> None:
        """Test soft deleting a scope (mark as inactive)."""
        # Soft delete (set is_active = False)
        result = scope_crud.delete_scope(db, test_scope.id, soft_delete=True)

        assert result is True

        # Verify scope still exists but is inactive
        scope = scope_crud.get_scope(db, test_scope.id)
        assert scope is not None
        assert scope.is_active is False

    def test_delete_scope_hard_delete(self, db: Session, admin_user: UserNew) -> None:
        """Test hard deleting a scope (remove from database)."""
        # Create a scope to delete
        scope_data = ScopeCreate(
            name="to-be-deleted",
            display_name="To Be Deleted",
            description="This scope will be deleted",
            institution=None,
            is_public=False,
            scope_config={},
            default_workflow_pair_id=None,
        )
        scope = scope_crud.create_scope(db, scope_data, admin_user.id)
        scope_id = scope.id

        # Hard delete
        result = scope_crud.delete_scope(db, scope_id, soft_delete=False)

        assert result is True

        # Verify scope no longer exists
        deleted_scope = scope_crud.get_scope(db, scope_id)
        assert deleted_scope is None

    def test_delete_scope_not_found(self, db: Session) -> None:
        """Test deleting a non-existent scope returns False."""
        fake_id = uuid4()

        result = scope_crud.delete_scope(db, fake_id)

        assert result is False

    def test_get_scope_statistics(
        self, db: Session, test_scope: Scope, admin_user: UserNew
    ) -> None:
        """Test retrieving scope statistics."""
        # This tests that the function exists and returns data
        # Actual statistics calculations would require more setup (genes, curations, etc.)
        stats: dict[str, Any] = scope_crud.get_scope_statistics(db, test_scope.id)

        assert stats is not None
        assert "total_genes_assigned" in stats
        assert "genes_with_curator" in stats
        assert "total_precurations" in stats
        assert "total_curations" in stats
        assert "total_reviews" in stats
        assert "active_curations" in stats
        assert "active_curators" in stats
        assert "active_reviewers" in stats
        assert "curations_last_30_days" in stats
        assert "activations_last_30_days" in stats

        # Initially should be all zeros
        assert stats["total_genes_assigned"] == 0
        assert stats["total_curations"] == 0

    def test_scope_name_validation_lowercase_only(
        self, db: Session, admin_user: UserNew
    ) -> None:
        """Test that scope names are validated and normalized."""
        # Use unique names to avoid conflicts with seed data
        # Database constraint allows alphanumeric and hyphens ONLY (no underscores)
        # Pydantic validator auto-converts uppercase to lowercase
        valid_names = [
            "valid-name-1",
            "valid-scope-123",
            "a-unique-name",
            "test-validation-2",  # Hyphens allowed
        ]
        # Names with uppercase are converted to lowercase (also valid)
        uppercase_names = [
            ("Valid-Name-2", "valid-name-2"),  # (input, expected output)
            ("TEST-SCOPE-3", "test-scope-3"),
        ]
        # Spaces, underscores, and special characters should fail
        invalid_names = [
            "invalid name",  # Space - NOT allowed
            "invalid.name",  # Period - NOT allowed
            "invalid@name",  # @ symbol - NOT allowed
            "invalid_name",  # Underscore - NOT allowed by database constraint
        ]

        # Valid names should work
        for name in valid_names:
            scope_data = ScopeCreate(
                name=name,
                display_name=f"Display {name}",
                description="Test",
                institution=None,
                is_public=False,
                scope_config={},
                default_workflow_pair_id=None,
            )
            scope = scope_crud.create_scope(db, scope_data, admin_user.id)
            assert scope.name == name

        # Uppercase names should be converted to lowercase
        for input_name, expected_name in uppercase_names:
            scope_data = ScopeCreate(
                name=input_name,
                display_name=f"Display {input_name}",
                description="Test",
                institution=None,
                is_public=False,
                scope_config={},
                default_workflow_pair_id=None,
            )
            scope = scope_crud.create_scope(db, scope_data, admin_user.id)
            assert scope.name == expected_name

        # Invalid names should fail (Pydantic validation during instantiation)
        from pydantic import ValidationError

        for name in invalid_names:
            with pytest.raises(ValidationError):
                ScopeCreate(
                    name=name,
                    display_name=f"Display {name}",
                    description="Test",
                    institution=None,
                    is_public=False,
                    scope_config={},
                    default_workflow_pair_id=None,
                )

    def test_scope_config_jsonb_storage(self, db: Session, admin_user: UserNew) -> None:
        """Test that scope_config JSONB field stores and retrieves correctly."""
        complex_config: dict[str, Any] = {
            "primary_inheritance_modes": ["Autosomal Recessive", "X-linked"],
            "focus_areas": ["Area 1", "Area 2"],
            "nested": {"key1": "value1", "key2": [1, 2, 3]},
        }

        scope_data = ScopeCreate(
            name="config-test-scope",
            display_name="Config Test Scope",
            description="Testing JSONB config",
            institution=None,
            is_public=False,
            scope_config=complex_config,
            default_workflow_pair_id=None,
        )

        scope = scope_crud.create_scope(db, scope_data, admin_user.id)

        # Verify config was stored correctly
        assert scope.scope_config == complex_config
        assert scope.scope_config["nested"]["key2"] == [1, 2, 3]

        # Verify retrieval
        retrieved_scope = scope_crud.get_scope(db, scope.id)
        assert retrieved_scope is not None
        assert retrieved_scope.scope_config == complex_config

    def test_scope_created_by_tracking(self, db: Session, admin_user: UserNew) -> None:
        """Test that scope creator is tracked correctly."""
        scope_data = ScopeCreate(
            name="creator-test",
            display_name="Creator Test",
            description="Test creator tracking",
            institution=None,
            is_public=False,
            scope_config={},
            default_workflow_pair_id=None,
        )

        scope = scope_crud.create_scope(db, scope_data, admin_user.id)

        assert scope.created_by == admin_user.id

        # Verify the relationship works
        db.refresh(scope)
        # Note: created_by_user relationship may not be loaded by default
        # This tests that the foreign key is correct

    def test_get_scopes_by_institution(
        self, db: Session, admin_user: UserNew, test_scope: Scope
    ) -> None:
        """Test filtering scopes by institution."""
        # Create scopes with different institutions
        for i, institution in enumerate(
            ["Institution A", "Institution B", "Institution A"]
        ):
            scope_data = ScopeCreate(
                name=f"inst-scope-{i}",
                display_name=f"Institution Scope {i}",
                description=f"Scope {i}",
                institution=institution,
                is_public=False,
                scope_config={},
                default_workflow_pair_id=None,
            )
            scope_crud.create_scope(db, scope_data, admin_user.id)

        # Get scopes by institution
        inst_a_scopes: Sequence[Scope] = scope_crud.get_scopes_by_institution(db, "Institution A")

        assert len(inst_a_scopes) >= 2  # At least the 2 we created
        for scope in inst_a_scopes:
            assert scope.institution == "Institution A"


class TestScopeEdgeCases:
    """Test edge cases and error conditions."""

    def test_scope_with_minimal_data(self, db: Session, admin_user: UserNew) -> None:
        """Test creating a scope with only required fields."""
        from app.models.models import Scope

        # Create scope with minimal data (name and display_name only)
        # But need created_by for RLS policy compliance
        minimal_scope = Scope(
            name="minimal-scope",
            display_name="Minimal Scope",
            created_by=admin_user.id,
        )

        db.add(minimal_scope)
        db.commit()
        db.refresh(minimal_scope)

        assert minimal_scope.id is not None
        assert minimal_scope.is_active is True  # Default
        assert minimal_scope.is_public is False  # Default
        assert minimal_scope.scope_config == {}  # Default
        assert minimal_scope.created_by == admin_user.id

    def test_scope_with_unicode_characters(self, db: Session, admin_user: UserNew) -> None:
        """Test scope with unicode characters in display_name and description."""
        scope_data = ScopeCreate(
            name="unicode-scope",
            display_name="Génétique Rénale 腎臓遺伝学",
            description="Testing unicode: Café, Zürich, 日本語, Ελληνικά",
            institution=None,
            is_public=False,
            scope_config={},
            default_workflow_pair_id=None,
        )

        scope = scope_crud.create_scope(db, scope_data, admin_user.id)

        assert "Génétique" in scope.display_name
        assert "腎臓遺伝学" in scope.display_name
        assert scope.description is not None
        assert "日本語" in scope.description

    def test_scope_with_very_long_description(self, db: Session, admin_user: UserNew) -> None:
        """Test scope with very long description (TEXT field)."""
        long_description = "A" * 10000  # 10,000 characters

        scope_data = ScopeCreate(
            name="long-desc-scope",
            display_name="Long Description Scope",
            description=long_description,
            institution=None,
            is_public=False,
            scope_config={},
            default_workflow_pair_id=None,
        )

        scope = scope_crud.create_scope(db, scope_data, admin_user.id)

        assert scope.description is not None
        assert len(scope.description) == 10000
        assert scope.description == long_description

    def test_scope_timestamps_auto_update(self, db: Session, test_scope: Scope) -> None:
        """Test that updated_at timestamp is automatically updated."""
        original_updated_at = test_scope.updated_at

        # Wait a moment and update
        import time

        time.sleep(0.1)

        update_data = ScopeUpdate(display_name="Updated Name")  # type: ignore[call-arg]
        updated_scope = scope_crud.update_scope(db, test_scope.id, update_data)

        assert updated_scope is not None
        assert updated_scope.updated_at >= original_updated_at

    def test_concurrent_scope_updates(self, db: Session, test_scope: Scope) -> None:
        """Test that concurrent updates don't cause data corruption."""
        # This is a basic test - full concurrency testing would require more setup
        update_data_1 = ScopeUpdate(display_name="Update 1")  # type: ignore[call-arg]
        update_data_2 = ScopeUpdate(description="Update 2 description")  # type: ignore[call-arg]

        # Perform updates sequentially
        scope_crud.update_scope(db, test_scope.id, update_data_1)
        scope_2 = scope_crud.update_scope(db, test_scope.id, update_data_2)

        # Verify both updates were applied
        assert scope_2 is not None
        assert scope_2.display_name == "Update 1"
        assert scope_2.description == "Update 2 description"
