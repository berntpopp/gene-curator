"""
Unit tests for scope-centric enums.

Tests ApplicationRole and ScopeRole enums, including string conversion,
validation, and permission checking methods.

Created: 2025-10-13
Author: Claude Code (Automated Implementation)
"""

import pytest

from app.core.enums import ApplicationRole, ScopeRole


class TestApplicationRole:
    """Test suite for ApplicationRole enum."""

    def test_enum_values(self):
        """Test that enum values are correct."""
        assert ApplicationRole.ADMIN.value == "admin"
        assert ApplicationRole.USER.value == "user"

    def test_string_representation(self):
        """Test __str__ returns the value."""
        assert str(ApplicationRole.ADMIN) == "admin"
        assert str(ApplicationRole.USER) == "user"

    def test_from_string_lowercase(self):
        """Test from_string with lowercase input."""
        role = ApplicationRole.from_string("admin")
        assert role == ApplicationRole.ADMIN

        role = ApplicationRole.from_string("user")
        assert role == ApplicationRole.USER

    def test_from_string_uppercase(self):
        """Test from_string with uppercase input."""
        role = ApplicationRole.from_string("ADMIN")
        assert role == ApplicationRole.ADMIN

        role = ApplicationRole.from_string("USER")
        assert role == ApplicationRole.USER

    def test_from_string_mixed_case(self):
        """Test from_string with mixed case input."""
        role = ApplicationRole.from_string("Admin")
        assert role == ApplicationRole.ADMIN

        role = ApplicationRole.from_string("UsEr")
        assert role == ApplicationRole.USER

    def test_from_string_invalid(self):
        """Test from_string with invalid input raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            ApplicationRole.from_string("invalid")

        assert "Invalid application role: invalid" in str(exc_info.value)
        assert "admin" in str(exc_info.value)
        assert "user" in str(exc_info.value)

    def test_from_string_empty(self):
        """Test from_string with empty string raises ValueError."""
        with pytest.raises(ValueError):
            ApplicationRole.from_string("")

    def test_enum_iteration(self):
        """Test iterating over all enum values."""
        all_roles = list(ApplicationRole)
        assert len(all_roles) == 2
        assert ApplicationRole.ADMIN in all_roles
        assert ApplicationRole.USER in all_roles

    def test_enum_comparison(self):
        """Test enum equality comparison."""
        assert ApplicationRole.ADMIN == ApplicationRole.ADMIN
        assert ApplicationRole.USER == ApplicationRole.USER
        assert ApplicationRole.ADMIN != ApplicationRole.USER


class TestScopeRole:
    """Test suite for ScopeRole enum."""

    def test_enum_values(self):
        """Test that enum values are correct."""
        assert ScopeRole.ADMIN.value == "admin"
        assert ScopeRole.CURATOR.value == "curator"
        assert ScopeRole.REVIEWER.value == "reviewer"
        assert ScopeRole.VIEWER.value == "viewer"

    def test_string_representation(self):
        """Test __str__ returns the value."""
        assert str(ScopeRole.ADMIN) == "admin"
        assert str(ScopeRole.CURATOR) == "curator"
        assert str(ScopeRole.REVIEWER) == "reviewer"
        assert str(ScopeRole.VIEWER) == "viewer"

    def test_from_string_lowercase(self):
        """Test from_string with lowercase input."""
        assert ScopeRole.from_string("admin") == ScopeRole.ADMIN
        assert ScopeRole.from_string("curator") == ScopeRole.CURATOR
        assert ScopeRole.from_string("reviewer") == ScopeRole.REVIEWER
        assert ScopeRole.from_string("viewer") == ScopeRole.VIEWER

    def test_from_string_uppercase(self):
        """Test from_string with uppercase input."""
        assert ScopeRole.from_string("ADMIN") == ScopeRole.ADMIN
        assert ScopeRole.from_string("CURATOR") == ScopeRole.CURATOR

    def test_from_string_invalid(self):
        """Test from_string with invalid input raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            ScopeRole.from_string("invalid")

        assert "Invalid scope role: invalid" in str(exc_info.value)
        assert "admin" in str(exc_info.value)

    # Permission checking tests

    def test_can_curate_admin(self):
        """Test that admin can curate."""
        assert ScopeRole.ADMIN.can_curate() is True

    def test_can_curate_curator(self):
        """Test that curator can curate."""
        assert ScopeRole.CURATOR.can_curate() is True

    def test_can_curate_reviewer(self):
        """Test that reviewer CANNOT curate."""
        assert ScopeRole.REVIEWER.can_curate() is False

    def test_can_curate_viewer(self):
        """Test that viewer CANNOT curate."""
        assert ScopeRole.VIEWER.can_curate() is False

    def test_can_review_admin(self):
        """Test that admin can review."""
        assert ScopeRole.ADMIN.can_review() is True

    def test_can_review_reviewer(self):
        """Test that reviewer can review."""
        assert ScopeRole.REVIEWER.can_review() is True

    def test_can_review_curator(self):
        """Test that curator CANNOT review."""
        assert ScopeRole.CURATOR.can_review() is False

    def test_can_review_viewer(self):
        """Test that viewer CANNOT review."""
        assert ScopeRole.VIEWER.can_review() is False

    def test_can_manage_scope_admin(self):
        """Test that admin can manage scope."""
        assert ScopeRole.ADMIN.can_manage_scope() is True

    def test_can_manage_scope_others(self):
        """Test that non-admin roles CANNOT manage scope."""
        assert ScopeRole.CURATOR.can_manage_scope() is False
        assert ScopeRole.REVIEWER.can_manage_scope() is False
        assert ScopeRole.VIEWER.can_manage_scope() is False

    def test_can_invite_members_admin(self):
        """Test that admin can invite members."""
        assert ScopeRole.ADMIN.can_invite_members() is True

    def test_can_invite_members_others(self):
        """Test that non-admin roles CANNOT invite members."""
        assert ScopeRole.CURATOR.can_invite_members() is False
        assert ScopeRole.REVIEWER.can_invite_members() is False
        assert ScopeRole.VIEWER.can_invite_members() is False

    def test_can_view_all_roles(self):
        """Test that all roles can view (minimum permission)."""
        assert ScopeRole.ADMIN.can_view() is True
        assert ScopeRole.CURATOR.can_view() is True
        assert ScopeRole.REVIEWER.can_view() is True
        assert ScopeRole.VIEWER.can_view() is True

    # Display properties tests

    def test_display_name(self):
        """Test display_name property."""
        assert ScopeRole.ADMIN.display_name == "Admin"
        assert ScopeRole.CURATOR.display_name == "Curator"
        assert ScopeRole.REVIEWER.display_name == "Reviewer"
        assert ScopeRole.VIEWER.display_name == "Viewer"

    def test_description(self):
        """Test description property."""
        admin_desc = ScopeRole.ADMIN.description
        assert "Full access" in admin_desc
        assert "manage scope" in admin_desc

        curator_desc = ScopeRole.CURATOR.description
        assert "create and edit curations" in curator_desc

        reviewer_desc = ScopeRole.REVIEWER.description
        assert "review curations" in reviewer_desc
        assert "4-eyes principle" in reviewer_desc

        viewer_desc = ScopeRole.VIEWER.description
        assert "Read-only" in viewer_desc

    # Role hierarchy tests

    def test_role_hierarchy_permissions(self):
        """Test that role permissions follow a logical hierarchy."""
        # Admin has all permissions
        assert ScopeRole.ADMIN.can_view()
        assert ScopeRole.ADMIN.can_curate()
        assert ScopeRole.ADMIN.can_review()
        assert ScopeRole.ADMIN.can_manage_scope()
        assert ScopeRole.ADMIN.can_invite_members()

        # Curator has subset of permissions
        assert ScopeRole.CURATOR.can_view()
        assert ScopeRole.CURATOR.can_curate()
        assert not ScopeRole.CURATOR.can_review()
        assert not ScopeRole.CURATOR.can_manage_scope()

        # Reviewer has different subset
        assert ScopeRole.REVIEWER.can_view()
        assert not ScopeRole.REVIEWER.can_curate()
        assert ScopeRole.REVIEWER.can_review()
        assert not ScopeRole.REVIEWER.can_manage_scope()

        # Viewer has minimal permissions
        assert ScopeRole.VIEWER.can_view()
        assert not ScopeRole.VIEWER.can_curate()
        assert not ScopeRole.VIEWER.can_review()
        assert not ScopeRole.VIEWER.can_manage_scope()

    def test_enum_iteration(self):
        """Test iterating over all enum values."""
        all_roles = list(ScopeRole)
        assert len(all_roles) == 4
        assert ScopeRole.ADMIN in all_roles
        assert ScopeRole.CURATOR in all_roles
        assert ScopeRole.REVIEWER in all_roles
        assert ScopeRole.VIEWER in all_roles

    def test_enum_comparison(self):
        """Test enum equality comparison."""
        assert ScopeRole.ADMIN == ScopeRole.ADMIN
        assert ScopeRole.CURATOR == ScopeRole.CURATOR
        assert ScopeRole.ADMIN != ScopeRole.CURATOR


class TestEnumIntegration:
    """Integration tests for enum usage patterns."""

    def test_enum_in_dict_keys(self):
        """Test using enums as dictionary keys."""
        permissions = {
            ScopeRole.ADMIN: ["all"],
            ScopeRole.CURATOR: ["create", "edit"],
            ScopeRole.REVIEWER: ["review"],
            ScopeRole.VIEWER: ["view"],
        }

        assert permissions[ScopeRole.ADMIN] == ["all"]
        assert permissions[ScopeRole.CURATOR] == ["create", "edit"]

    def test_enum_in_sets(self):
        """Test using enums in sets."""
        curation_roles = {ScopeRole.ADMIN, ScopeRole.CURATOR}

        assert ScopeRole.ADMIN in curation_roles
        assert ScopeRole.CURATOR in curation_roles
        assert ScopeRole.REVIEWER not in curation_roles
        assert ScopeRole.VIEWER not in curation_roles

    def test_enum_serialization(self):
        """Test that enums can be serialized to strings."""
        role = ScopeRole.CURATOR
        serialized = role.value

        assert serialized == "curator"
        assert isinstance(serialized, str)

        # Deserialize
        deserialized = ScopeRole.from_string(serialized)
        assert deserialized == role

    def test_permission_matrix(self):
        """Test complete permission matrix for all roles."""
        permission_matrix = {
            "view": [ScopeRole.ADMIN, ScopeRole.CURATOR, ScopeRole.REVIEWER, ScopeRole.VIEWER],
            "curate": [ScopeRole.ADMIN, ScopeRole.CURATOR],
            "review": [ScopeRole.ADMIN, ScopeRole.REVIEWER],
            "manage": [ScopeRole.ADMIN],
            "invite": [ScopeRole.ADMIN],
        }

        # Verify each role has correct permissions
        for role in ScopeRole:
            assert (role.can_view()) == (role in permission_matrix["view"])
            assert (role.can_curate()) == (role in permission_matrix["curate"])
            assert (role.can_review()) == (role in permission_matrix["review"])
            assert (role.can_manage_scope()) == (role in permission_matrix["manage"])
            assert (role.can_invite_members()) == (role in permission_matrix["invite"])
