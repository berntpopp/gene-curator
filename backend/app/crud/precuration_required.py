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


def _fields(defs: Any, prefix: str = "") -> list[tuple[str, dict[str, Any]]]:
    """(dotted path, config) of every field in a flat/nested definition dict or `sections`."""
    if not isinstance(defs, dict):
        return []
    found: list[tuple[str, dict[str, Any]]] = []
    for section in defs.get("sections") or []:
        for field in section.get("fields", []) if isinstance(section, dict) else []:
            if isinstance(field, dict):
                found.append((f"{prefix}{field.get('id')}", field))
    for name, config in defs.items():
        if name == "sections" or not isinstance(config, dict):
            continue
        found.append((f"{prefix}{name}", config))
        if config.get("required") is not True and config.get("type") == "object":
            found += _fields(config.get("properties"), f"{prefix}{name}.")
    return found


def _value_at(data: Any, path: str) -> Any:
    for key in path.split("."):
        data = data.get(key) if isinstance(data, dict) else None
    return data


def _same(a: Any, b: Any) -> bool:
    return bool(a == b and isinstance(a, bool) == isinstance(b, bool))


def condition_holds(condition: Any, data: Any) -> bool:
    """`{path: value}` equals, `{path: [values]}` in; every entry must hold (frontend
    conditions.ts). Anything that is not a dict is no condition."""
    if not isinstance(condition, dict):
        return True
    for path, expected in condition.items():
        options = expected if isinstance(expected, list) else [expected]
        if not any(_same(_value_at(data, path), option) for option in options):
            return False
    return True


def missing_required_fields(
    field_definitions: Any, data: Any, validation_rules: Any = None
) -> list[str]:
    """Dotted paths of required fields empty in ``data``.

    Required = ``required: true`` in flat/nested definitions or ``sections[].fields[]``,
    plus ``validation_rules.required_fields``; a field hidden by its ``visible_when`` /
    ``show_when`` condition is not required, nor is a checkbox. Mirrored by the frontend requiredFields.ts.
    """
    fields = _fields(field_definitions)
    paths = [path for path, config in fields if config.get("required") is True]
    listed = (
        (validation_rules or {}).get("required_fields") if validation_rules else None
    )
    paths += [p for p in listed or [] if p not in paths]
    configs = dict(fields)
    return [
        path
        for path in dict.fromkeys(paths)
        if condition_holds(
            (config := configs.get(path, {})).get(
                "visible_when", config.get("show_when")
            ),
            data,
        )
        # an unset checkbox is false, not missing
        and config.get("type") != "boolean"
        and _is_empty(_value_at(data, path))
    ]
