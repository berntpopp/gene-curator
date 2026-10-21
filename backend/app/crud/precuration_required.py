"""Required-field check for precuration submit."""

from typing import Any


class MissingRequiredFieldsError(ValueError):
    """Submit refused: schema-required fields are empty (dotted paths in ``fields``)."""

    def __init__(self, fields: list[str]) -> None:
        super().__init__(f"Missing required fields: {', '.join(fields)}")
        self.fields = fields


def _is_empty(value: Any) -> bool:
    return (
        value is None
        or (isinstance(value, str) and not value.strip())
        or (isinstance(value, list | dict) and not value)
    )


def _required_paths(defs: Any, prefix: str = "") -> list[str]:
    """Required field paths from a flat/nested definition dict or a `sections` list."""
    if not isinstance(defs, dict):
        return []
    found: list[str] = []
    for section in defs.get("sections") or []:
        for field in section.get("fields", []) if isinstance(section, dict) else []:
            if isinstance(field, dict) and field.get("required") is True:
                found.append(f"{prefix}{field.get('id')}")
    for name, config in defs.items():
        if name == "sections" or not isinstance(config, dict):
            continue
        if config.get("required") is True:
            found.append(f"{prefix}{name}")
        elif config.get("type") == "object":
            found += _required_paths(config.get("properties"), f"{prefix}{name}.")
    return found


def missing_required_fields(
    field_definitions: Any, data: Any, validation_rules: Any = None
) -> list[str]:
    """Dotted paths of required fields empty in ``data``.

    Required = ``required: true`` in flat/nested definitions or ``sections[].fields[]``,
    plus ``validation_rules.required_fields``. Mirrored by the frontend requiredFields.ts.
    """
    paths = _required_paths(field_definitions)
    listed = (
        (validation_rules or {}).get("required_fields") if validation_rules else None
    )
    paths += [p for p in listed or [] if p not in paths]
    missing = []
    for path in dict.fromkeys(paths):
        value: Any = data
        for key in path.split("."):
            value = value.get(key) if isinstance(value, dict) else None
        if _is_empty(value):
            missing.append(path)
    return missing
