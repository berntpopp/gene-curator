"""Guard: Pydantic v1-style `class Config` must not come back in app/ (#330)."""

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

APP = Path(__file__).resolve().parents[2] / "app"


def test_no_inner_class_config_in_app() -> None:
    offenders = [
        f"{path.relative_to(APP)}:{child.lineno}"
        for path in APP.rglob("*.py")
        for cls in ast.walk(ast.parse(path.read_text()))
        if isinstance(cls, ast.ClassDef)
        for child in cls.body
        if isinstance(child, ast.ClassDef) and child.name == "Config"
    ]
    assert not offenders, f"use model_config = ConfigDict(...): {offenders}"
