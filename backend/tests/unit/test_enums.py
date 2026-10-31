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

    def test_enum_values(self) -> None:
        """Test that enum values are correct."""
        assert ApplicationRole.ADMIN.value == "admin"
        assert ApplicationRole.USER.value == "user"

    def test_string_representation(self) -> None:
        """Test __str__ returns the value."""
        assert str(ApplicationRole.ADMIN) == "admin"
        assert str(ApplicationRole.USER) == "user"

    def test_from_string_lowercase(self) -> None:
        """Test from_string with lowercase input."""
        role = ApplicationRole.from_string("admin")
        assert role == ApplicationRole.ADMIN

        role = ApplicationRole.from_string("user")
        assert role == ApplicationRole.USER

    def test_from_string_uppercase(self) -> None:
        """Test from_string with uppercase input."""
        role = ApplicationRole.from_string("ADMIN")
        assert role == ApplicationRole.ADMIN

        role = ApplicationRole.from_string("USER")
        assert role == ApplicationRole.USER

    def test_from_string_mixed_case(self) -> None:
        """Test from_string with mixed case input."""
        role = ApplicationRole.from_string("Admin")
        assert role == ApplicationRole.ADMIN

        role = ApplicationRole.from_string("UsEr")
        assert role == ApplicationRole.USER

    def test_from_string_invalid(self) -> None:
        """Test from_string with invalid input raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            ApplicationRole.from_string("invalid")

        assert "Invalid application role: invalid" in str(exc_info.value)
        assert "admin" in str(exc_info.value)
        assert "user" in str(exc_info.value)

    def test_from_string_empty(self) -> None:
        """Test from_string with empty string raises ValueError."""
        with pytest.raises(ValueError):
            ApplicationRole.from_string("")

    def test_enum_iteration(self) -> None:
        """Test iterating over all enum values."""
        all_roles = list(ApplicationRole)
        assert len(all_roles) == 2
        assert ApplicationRole.ADMIN in all_roles
        assert ApplicationRole.USER in all_roles

    def test_enum_comparison(self) -> None:
        """Test enum equality comparison."""
        assert ApplicationRole.ADMIN == ApplicationRole.ADMIN
        assert ApplicationRole.USER == ApplicationRole.USER
        assert ApplicationRole.ADMIN != ApplicationRole.USER  # type: ignore[comparison-overlap]


class TestScopeRole:
    """Test suite for ScopeRole enum."""

    def test_enum_values(self) -> None:
        """Test that enum values are correct."""
        assert ScopeRole.ADMIN.value == "admin"
        assert ScopeRole.CURATOR.value == "curator"
        assert ScopeRole.REVIEWER.value == "reviewer"
        assert ScopeRole.VIEWER.value == "viewer"

    def test_string_representation(self) -> None:
        """Test __str__ returns the value."""
        assert str(ScopeRole.ADMIN) == "admin"
        assert str(ScopeRole.CURATOR) == "curator"
        assert str(ScopeRole.REVIEWER) == "reviewer"
        assert str(ScopeRole.VIEWER) == "viewer"

    def test_from_string_lowercase(self) -> None:
        """Test from_string with lowercase input."""
        assert ScopeRole.from_string("admin") == ScopeRole.ADMIN
        assert ScopeRole.from_string("curator") == ScopeRole.CURATOR
        assert ScopeRole.from_string("reviewer") == ScopeRole.REVIEWER
        assert ScopeRole.from_string("viewer") == ScopeRole.VIEWER

    def test_from_string_uppercase(self) -> None:
        """Test from_string with uppercase input."""
        assert ScopeRole.from_string("ADMIN") == ScopeRole.ADMIN
        assert ScopeRole.from_string("CURATOR") == ScopeRole.CURATOR

    def test_from_string_invalid(self) -> None:
        """Test from_string with invalid input raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            ScopeRole.from_string("invalid")

        assert "Invalid scope role: invalid" in str(exc_info.value)
        assert "admin" in str(exc_info.value)

    # Display properties tests

    def test_display_name(self) -> None:
        """Test display_name property."""
        assert ScopeRole.ADMIN.display_name == "Admin"
        assert ScopeRole.CURATOR.display_name == "Curator"
        assert ScopeRole.REVIEWER.display_name == "Reviewer"
        assert ScopeRole.VIEWER.display_name == "Viewer"

    def test_description(self) -> None:
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

    def test_enum_iteration(self) -> None:
        """Test iterating over all enum values."""
        all_roles = list(ScopeRole)
        assert len(all_roles) == 4
        assert ScopeRole.ADMIN in all_roles
        assert ScopeRole.CURATOR in all_roles
        assert ScopeRole.REVIEWER in all_roles
        assert ScopeRole.VIEWER in all_roles

    def test_enum_comparison(self) -> None:
        """Test enum equality comparison."""
        assert ScopeRole.ADMIN == ScopeRole.ADMIN
        assert ScopeRole.CURATOR == ScopeRole.CURATOR
        assert ScopeRole.ADMIN != ScopeRole.CURATOR  # type: ignore[comparison-overlap]


class TestEnumIntegration:
    """Integration tests for enum usage patterns."""

    def test_enum_in_dict_keys(self) -> None:
        """Test using enums as dictionary keys."""
        permissions = {
            ScopeRole.ADMIN: ["all"],
            ScopeRole.CURATOR: ["create", "edit"],
            ScopeRole.REVIEWER: ["review"],
            ScopeRole.VIEWER: ["view"],
        }

        assert permissions[ScopeRole.ADMIN] == ["all"]
        assert permissions[ScopeRole.CURATOR] == ["create", "edit"]

    def test_enum_in_sets(self) -> None:
        """Test using enums in sets."""
        curation_roles = {ScopeRole.ADMIN, ScopeRole.CURATOR}

        assert ScopeRole.ADMIN in curation_roles
        assert ScopeRole.CURATOR in curation_roles
        assert ScopeRole.REVIEWER not in curation_roles
        assert ScopeRole.VIEWER not in curation_roles

    def test_enum_serialization(self) -> None:
        """Test that enums can be serialized to strings."""
        role = ScopeRole.CURATOR
        serialized = role.value

        assert serialized == "curator"
        assert isinstance(serialized, str)

        # Deserialize
        deserialized = ScopeRole.from_string(serialized)
        assert deserialized == role


def test_no_non_enum_scope_role_literals_in_app() -> None:
    """'scope_admin' is not a scope_role enum value; querying it 500s on Postgres."""
    from pathlib import Path

    root = Path(__file__).parents[2] / "app"
    bad = [
        str(p)
        for p in root.rglob("*.py")
        if '"scope_admin"' in p.read_text() or "'scope_admin'" in p.read_text()
    ]
    assert bad == []


def test_role_in_queries_never_use_string_literals() -> None:
    """Any `<x>.role.in_(...)` argument (or the list it names) must come from ScopeRole."""
    import ast
    from pathlib import Path

    root = Path(__file__).parents[2] / "app"
    bad: list[str] = []
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text())
        assigned: dict[str, list[ast.AST]] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        assigned.setdefault(t.id, []).append(node.value)
        for node in ast.walk(tree):
            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "in_"
                and isinstance(node.func.value, ast.Attribute)
                and node.func.value.attr == "role"
            ):
                continue
            arg = node.args[0]
            parts = assigned.get(arg.id, []) if isinstance(arg, ast.Name) else [arg]
            for part in parts:
                if any(
                    isinstance(n, ast.Constant) and isinstance(n.value, str)
                    for n in ast.walk(part)
                ):
                    bad.append(f"{path}:{node.lineno}")
    assert bad == []
