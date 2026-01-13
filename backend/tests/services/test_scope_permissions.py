"""Tests for ScopePermissionService.

Tests cover:
- Admin bypass decorator functionality
- has_scope_access with EXISTS query optimization
- get_user_scope_ids for different user types
- get_user_scope_role for membership lookup
- can_create_precuration, can_approve_precuration, can_edit_gene_assignment
"""

from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.models.models import PrecurationNew, Scope, ScopeMembership, UserNew
from app.services.scope_permissions import (
    ScopePermissionService,
    _is_global_admin,
    admin_bypass_returns_true,
)

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def admin_user(db_session: Session) -> UserNew:
    """Create admin user without scope membership."""
    user = UserNew(
        id=uuid4(),
        email="admin@test.com",
        hashed_password="hashed",
        name="Admin User",
        role="admin",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def regular_user(db_session: Session) -> UserNew:
    """Create regular user without any scope membership."""
    user = UserNew(
        id=uuid4(),
        email="regular@test.com",
        hashed_password="hashed",
        name="Regular User",
        role="user",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def scope(db_session: Session) -> Scope:
    """Create active scope."""
    scope = Scope(
        id=uuid4(),
        name="test-scope",
        display_name="Test Scope",
        description="Test scope",
        is_public=False,
        is_active=True,
    )
    db_session.add(scope)
    db_session.commit()
    db_session.refresh(scope)
    return scope


@pytest.fixture
def inactive_scope(db_session: Session) -> Scope:
    """Create inactive scope."""
    scope = Scope(
        id=uuid4(),
        name="inactive-scope",
        display_name="Inactive Scope",
        description="Inactive test scope",
        is_public=False,
        is_active=False,
    )
    db_session.add(scope)
    db_session.commit()
    db_session.refresh(scope)
    return scope


@pytest.fixture
def scope2(db_session: Session) -> Scope:
    """Create second active scope for multi-scope tests."""
    scope = Scope(
        id=uuid4(),
        name="test-scope-2",
        display_name="Test Scope 2",
        description="Second test scope",
        is_public=False,
        is_active=True,
    )
    db_session.add(scope)
    db_session.commit()
    db_session.refresh(scope)
    return scope


@pytest.fixture
def curator_membership(
    db_session: Session, regular_user: UserNew, scope: Scope
) -> ScopeMembership:
    """Create active curator membership."""
    membership = ScopeMembership(
        user_id=regular_user.id,
        scope_id=scope.id,
        role="curator",
        is_active=True,
    )
    db_session.add(membership)
    db_session.commit()
    db_session.refresh(membership)
    return membership


@pytest.fixture
def viewer_membership(
    db_session: Session, regular_user: UserNew, scope: Scope
) -> ScopeMembership:
    """Create active viewer membership."""
    membership = ScopeMembership(
        user_id=regular_user.id,
        scope_id=scope.id,
        role="viewer",
        is_active=True,
    )
    db_session.add(membership)
    db_session.commit()
    db_session.refresh(membership)
    return membership


@pytest.fixture
def inactive_membership(
    db_session: Session, regular_user: UserNew, scope: Scope
) -> ScopeMembership:
    """Create inactive membership."""
    membership = ScopeMembership(
        user_id=regular_user.id,
        scope_id=scope.id,
        role="curator",
        is_active=False,
    )
    db_session.add(membership)
    db_session.commit()
    db_session.refresh(membership)
    return membership


@pytest.fixture
def reviewer_membership(
    db_session: Session, regular_user: UserNew, scope: Scope
) -> ScopeMembership:
    """Create active reviewer membership."""
    membership = ScopeMembership(
        user_id=regular_user.id,
        scope_id=scope.id,
        role="reviewer",
        is_active=True,
    )
    db_session.add(membership)
    db_session.commit()
    db_session.refresh(membership)
    return membership


# =============================================================================
# Test Admin Bypass Helper
# =============================================================================


class TestIsGlobalAdmin:
    """Test the _is_global_admin helper function."""

    def test_returns_true_for_admin_role(self, admin_user: UserNew) -> None:
        """Should return True for users with admin role."""
        assert _is_global_admin(admin_user) is True

    def test_returns_false_for_user_role(self, regular_user: UserNew) -> None:
        """Should return False for users with user role."""
        assert _is_global_admin(regular_user) is False


class TestAdminBypassDecorator:
    """Test the admin_bypass_returns_true decorator."""

    def test_decorator_returns_true_for_admin(
        self, db_session: Session, admin_user: UserNew
    ) -> None:
        """Admin should bypass and get True without function execution."""
        call_count = 0

        @admin_bypass_returns_true
        def check_permission(db: Session, user: UserNew) -> bool:
            nonlocal call_count
            call_count += 1
            return False

        result = check_permission(db_session, admin_user)
        assert result is True
        assert call_count == 0  # Function was not called

    def test_decorator_calls_function_for_non_admin(
        self, db_session: Session, regular_user: UserNew
    ) -> None:
        """Non-admin should execute the wrapped function."""
        call_count = 0

        @admin_bypass_returns_true
        def check_permission(db: Session, user: UserNew) -> bool:
            nonlocal call_count
            call_count += 1
            return False

        result = check_permission(db_session, regular_user)
        assert result is False
        assert call_count == 1  # Function was called


# =============================================================================
# Test has_scope_access
# =============================================================================


class TestHasScopeAccess:
    """Test has_scope_access method with EXISTS query optimization."""

    def test_admin_bypasses_membership_check(
        self, db_session: Session, admin_user: UserNew, scope: Scope
    ) -> None:
        """Admin should have access without membership."""
        result = ScopePermissionService.has_scope_access(
            db_session, admin_user, scope.id
        )
        assert result is True

    def test_member_has_access(
        self,
        db_session: Session,
        regular_user: UserNew,
        scope: Scope,
        curator_membership: ScopeMembership,
    ) -> None:
        """User with active membership should have access."""
        result = ScopePermissionService.has_scope_access(
            db_session, regular_user, scope.id
        )
        assert result is True

    def test_non_member_denied(
        self, db_session: Session, regular_user: UserNew, scope: Scope
    ) -> None:
        """User without membership should be denied."""
        result = ScopePermissionService.has_scope_access(
            db_session, regular_user, scope.id
        )
        assert result is False

    def test_inactive_membership_denied(
        self,
        db_session: Session,
        regular_user: UserNew,
        scope: Scope,
        inactive_membership: ScopeMembership,
    ) -> None:
        """User with inactive membership should be denied."""
        result = ScopePermissionService.has_scope_access(
            db_session, regular_user, scope.id
        )
        assert result is False

    def test_required_role_check_passes(
        self,
        db_session: Session,
        regular_user: UserNew,
        scope: Scope,
        curator_membership: ScopeMembership,
    ) -> None:
        """User with matching role should have access."""
        result = ScopePermissionService.has_scope_access(
            db_session, regular_user, scope.id, required_roles=["curator", "admin"]
        )
        assert result is True

    def test_required_role_check_fails(
        self,
        db_session: Session,
        regular_user: UserNew,
        scope: Scope,
        viewer_membership: ScopeMembership,
    ) -> None:
        """User without matching role should be denied."""
        result = ScopePermissionService.has_scope_access(
            db_session, regular_user, scope.id, required_roles=["curator"]
        )
        assert result is False

    def test_inactive_scope_denied(
        self,
        db_session: Session,
        regular_user: UserNew,
        inactive_scope: Scope,
    ) -> None:
        """Access to inactive scope should be denied."""
        # Create membership for inactive scope
        membership = ScopeMembership(
            user_id=regular_user.id,
            scope_id=inactive_scope.id,
            role="curator",
            is_active=True,
        )
        db_session.add(membership)
        db_session.commit()

        result = ScopePermissionService.has_scope_access(
            db_session, regular_user, inactive_scope.id
        )
        assert result is False

    def test_nonexistent_scope_denied(
        self, db_session: Session, regular_user: UserNew
    ) -> None:
        """Access to nonexistent scope should be denied."""
        fake_scope_id = uuid4()
        result = ScopePermissionService.has_scope_access(
            db_session, regular_user, fake_scope_id
        )
        assert result is False


# =============================================================================
# Test get_user_scope_ids
# =============================================================================


class TestGetUserScopeIds:
    """Test get_user_scope_ids method."""

    def test_admin_gets_all_active_scopes(
        self, db_session: Session, admin_user: UserNew, scope: Scope, scope2: Scope
    ) -> None:
        """Admin should get all active scopes."""
        scope_ids = ScopePermissionService.get_user_scope_ids(db_session, admin_user)
        assert scope.id in scope_ids
        assert scope2.id in scope_ids

    def test_admin_excludes_inactive_scopes(
        self,
        db_session: Session,
        admin_user: UserNew,
        scope: Scope,
        inactive_scope: Scope,
    ) -> None:
        """Admin should not get inactive scopes."""
        scope_ids = ScopePermissionService.get_user_scope_ids(db_session, admin_user)
        assert scope.id in scope_ids
        assert inactive_scope.id not in scope_ids

    def test_user_gets_only_member_scopes(
        self,
        db_session: Session,
        regular_user: UserNew,
        scope: Scope,
        scope2: Scope,
        curator_membership: ScopeMembership,
    ) -> None:
        """User should only get scopes they're a member of."""
        scope_ids = ScopePermissionService.get_user_scope_ids(db_session, regular_user)
        assert scope.id in scope_ids
        assert scope2.id not in scope_ids

    def test_user_excludes_inactive_memberships(
        self,
        db_session: Session,
        regular_user: UserNew,
        scope: Scope,
        inactive_membership: ScopeMembership,
    ) -> None:
        """User should not get scopes with inactive memberships."""
        scope_ids = ScopePermissionService.get_user_scope_ids(db_session, regular_user)
        assert scope.id not in scope_ids

    def test_role_filter_applied(
        self,
        db_session: Session,
        regular_user: UserNew,
        scope: Scope,
        scope2: Scope,
    ) -> None:
        """Role filter should limit returned scopes."""
        # Create curator membership for scope
        membership1 = ScopeMembership(
            user_id=regular_user.id,
            scope_id=scope.id,
            role="curator",
            is_active=True,
        )
        # Create viewer membership for scope2
        membership2 = ScopeMembership(
            user_id=regular_user.id,
            scope_id=scope2.id,
            role="viewer",
            is_active=True,
        )
        db_session.add_all([membership1, membership2])
        db_session.commit()

        # Get only curator scopes
        curator_scope_ids = ScopePermissionService.get_user_scope_ids(
            db_session, regular_user, required_roles=["curator"]
        )
        assert scope.id in curator_scope_ids
        assert scope2.id not in curator_scope_ids

        # Get all scopes (no role filter)
        all_scope_ids = ScopePermissionService.get_user_scope_ids(
            db_session, regular_user
        )
        assert scope.id in all_scope_ids
        assert scope2.id in all_scope_ids

    def test_empty_for_user_without_memberships(
        self, db_session: Session, regular_user: UserNew, scope: Scope
    ) -> None:
        """User without memberships should get empty list."""
        scope_ids = ScopePermissionService.get_user_scope_ids(db_session, regular_user)
        assert scope_ids == []


# =============================================================================
# Test get_user_scope_role
# =============================================================================


class TestGetUserScopeRole:
    """Test get_user_scope_role method."""

    def test_returns_role_for_member(
        self,
        db_session: Session,
        regular_user: UserNew,
        scope: Scope,
        curator_membership: ScopeMembership,
    ) -> None:
        """Should return role for active member."""
        role = ScopePermissionService.get_user_scope_role(
            db_session, regular_user.id, scope.id
        )
        assert role == "curator"

    def test_returns_none_for_non_member(
        self, db_session: Session, regular_user: UserNew, scope: Scope
    ) -> None:
        """Should return None for non-member."""
        role = ScopePermissionService.get_user_scope_role(
            db_session, regular_user.id, scope.id
        )
        assert role is None

    def test_returns_none_for_inactive_membership(
        self,
        db_session: Session,
        regular_user: UserNew,
        scope: Scope,
        inactive_membership: ScopeMembership,
    ) -> None:
        """Should return None for inactive membership."""
        role = ScopePermissionService.get_user_scope_role(
            db_session, regular_user.id, scope.id
        )
        assert role is None


# =============================================================================
# Test can_create_precuration
# =============================================================================


class TestCanCreatePrecuration:
    """Test can_create_precuration method."""

    def test_admin_can_create(
        self, db_session: Session, admin_user: UserNew, scope: Scope
    ) -> None:
        """Admin should be able to create precurations."""
        result = ScopePermissionService.can_create_precuration(
            db_session, admin_user, scope.id
        )
        assert result is True

    def test_curator_can_create(
        self,
        db_session: Session,
        regular_user: UserNew,
        scope: Scope,
        curator_membership: ScopeMembership,
    ) -> None:
        """Curator should be able to create precurations."""
        result = ScopePermissionService.can_create_precuration(
            db_session, regular_user, scope.id
        )
        assert result is True

    def test_viewer_cannot_create(
        self,
        db_session: Session,
        regular_user: UserNew,
        scope: Scope,
        viewer_membership: ScopeMembership,
    ) -> None:
        """Viewer should not be able to create precurations."""
        result = ScopePermissionService.can_create_precuration(
            db_session, regular_user, scope.id
        )
        assert result is False


# =============================================================================
# Test can_approve_precuration
# =============================================================================


class TestCanApprovePrecuration:
    """Test can_approve_precuration method with 4-eyes principle."""

    @pytest.fixture
    def precuration(
        self, db_session: Session, regular_user: UserNew, scope: Scope
    ) -> PrecurationNew:
        """Create test precuration owned by regular_user."""
        import hashlib

        from app.models.models import CurationSchema, Gene

        # Create gene
        gene_data = "HGNC:1100:BRCA1"
        record_hash = hashlib.sha256(gene_data.encode()).hexdigest()
        gene = Gene(
            id=uuid4(),
            hgnc_id="HGNC:1100",
            approved_symbol="BRCA1",
            record_hash=record_hash,
            previous_symbols=[],
            alias_symbols=[],
        )
        db_session.add(gene)

        # Create schema
        schema_data = "Test Precuration Schema1.0"
        schema_hash = hashlib.sha256(schema_data.encode()).hexdigest()
        schema = CurationSchema(
            id=uuid4(),
            name="Test Schema",
            version="1.0",
            schema_type="precuration",
            is_active=True,
            field_definitions={},
            validation_rules={},
            workflow_states={},
            ui_configuration={},
            schema_hash=schema_hash,
        )
        db_session.add(schema)
        db_session.flush()

        precuration = PrecurationNew(
            id=uuid4(),
            scope_id=scope.id,
            gene_id=gene.id,
            precuration_schema_id=schema.id,
            workflow_stage="precuration",
            evidence_data={},
            created_by=regular_user.id,
        )
        db_session.add(precuration)
        db_session.commit()
        db_session.refresh(precuration)
        return precuration

    @pytest.fixture
    def other_user(self, db_session: Session) -> UserNew:
        """Create another user for approval tests."""
        user = UserNew(
            id=uuid4(),
            email="other@test.com",
            hashed_password="hashed",
            name="Other User",
            role="user",
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    def test_creator_cannot_approve_own_work(
        self,
        db_session: Session,
        regular_user: UserNew,
        scope: Scope,
        precuration: PrecurationNew,
        curator_membership: ScopeMembership,
    ) -> None:
        """Creator should not be able to approve own precuration (4-eyes)."""
        result = ScopePermissionService.can_approve_precuration(
            db_session, regular_user, precuration
        )
        assert result is False

    def test_other_reviewer_can_approve(
        self,
        db_session: Session,
        other_user: UserNew,
        scope: Scope,
        precuration: PrecurationNew,
    ) -> None:
        """Other user with reviewer role can approve."""
        # Create reviewer membership for other user
        membership = ScopeMembership(
            user_id=other_user.id,
            scope_id=scope.id,
            role="reviewer",
            is_active=True,
        )
        db_session.add(membership)
        db_session.commit()

        result = ScopePermissionService.can_approve_precuration(
            db_session, other_user, precuration
        )
        assert result is True

    def test_admin_can_approve(
        self,
        db_session: Session,
        admin_user: UserNew,
        precuration: PrecurationNew,
    ) -> None:
        """Admin should be able to approve any precuration."""
        result = ScopePermissionService.can_approve_precuration(
            db_session, admin_user, precuration
        )
        assert result is True


# =============================================================================
# Test can_edit_gene_assignment
# =============================================================================


class TestCanEditGeneAssignment:
    """Test can_edit_gene_assignment method."""

    def test_admin_can_edit(
        self, db_session: Session, admin_user: UserNew, scope: Scope
    ) -> None:
        """Admin should be able to edit gene assignments."""
        result = ScopePermissionService.can_edit_gene_assignment(
            db_session, admin_user, scope.id
        )
        assert result is True

    def test_curator_can_edit(
        self,
        db_session: Session,
        regular_user: UserNew,
        scope: Scope,
        curator_membership: ScopeMembership,
    ) -> None:
        """Curator should be able to edit gene assignments."""
        result = ScopePermissionService.can_edit_gene_assignment(
            db_session, regular_user, scope.id
        )
        assert result is True

    def test_viewer_cannot_edit(
        self,
        db_session: Session,
        regular_user: UserNew,
        scope: Scope,
        viewer_membership: ScopeMembership,
    ) -> None:
        """Viewer should not be able to edit gene assignments."""
        result = ScopePermissionService.can_edit_gene_assignment(
            db_session, regular_user, scope.id
        )
        assert result is False

    def test_reviewer_cannot_edit(
        self,
        db_session: Session,
        regular_user: UserNew,
        scope: Scope,
        reviewer_membership: ScopeMembership,
    ) -> None:
        """Reviewer should not be able to edit gene assignments."""
        result = ScopePermissionService.can_edit_gene_assignment(
            db_session, regular_user, scope.id
        )
        assert result is False
