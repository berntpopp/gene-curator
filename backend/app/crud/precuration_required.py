"""Required-field check for precuration submit, and the one condition semantics (#433).

Shared with the frontend (components/dynamic/conditions.ts); both run the table in
frontend/src/components/dynamic/__tests__/conditionCases.json.

- A condition ``{path: value, ...}`` holds when every entry holds: a list value means "one of",
  anything else equals. Equality is strict: ``true`` is not ``1``, ``"1"`` is not ``1``.
- Paths are dotted from the root of the evidence data, for nested fields too; a numeric segment
  (``rows.0.kind``) indexes a list. A missing value is not ``null``: ``{x: null}`` holds only for
  an explicit null.
- No condition (absent or null) holds. A malformed one (not an object, or a value that is an
  object or a nested list) also holds: the field stays shown and, for ``required_when``,
  required, so a schema typo never drops a required check.
- ``visible_when`` wins over its alias ``show_when``; a field under a hidden parent is hidden,
  and a hidden field is never required. Required is ``required: true``, a ``required_when``
  that holds, ``validation_rules.required_fields`` or a ``conditional_required`` entry whose
  ``when`` holds.
"""

import re
from typing import Any


class MissingRequiredFieldsError(ValueError):
    """Submit refused: schema-required fields are empty (dotted paths in ``fields``)."""

    def __init__(
        self, fields: list[str], contract: list[dict[str, Any]] | None = None
    ) -> None:
        super().__init__(f"Missing required fields: {', '.join(fields)}")
        self.fields = fields
        self.contract = contract or []


def field_contract(
    field_definitions: Any, data: Any, paths: list[str]
) -> list[dict[str, Any]]:
    """{path, type, allowed?} per path, so a client fills fields without guessing."""
    configs = dict(_fields(field_definitions, data=data))
    out = []
    for path in paths:
        config = configs.get(path, {})
        options = config.get("options") or config.get("enum")
        row: dict[str, Any] = {"path": path, "type": config.get("type")}
        if isinstance(options, list):
            row["allowed"] = [
                o.get("value") if isinstance(o, dict) else o for o in options
            ]
        out.append(row)
    return out


_MISSING = object()  # an absent value, unlike None (an explicit null)
_INDEX = re.compile(r"0|[1-9][0-9]*")


def _is_empty(value: Any) -> bool:
    return (
        value is None
        or value is _MISSING
        or (isinstance(value, str) and not value.strip())
        or (isinstance(value, list | dict) and not value)
    )


def _fields(
    defs: Any, prefix: str = "", data: Any = None
) -> list[tuple[str, dict[str, Any]]]:
    """(dotted path, config) of every field in a flat/nested definition dict or `sections`."""
    if not isinstance(defs, dict):
        return []
    found: list[tuple[str, dict[str, Any]]] = []
    for section in defs.get("sections") or []:
        for field in section.get("fields", []) if isinstance(section, dict) else []:
            if isinstance(field, dict):
                found += (
                    _fields({field["id"]: field}, prefix, data)
                    if field.get("id")
                    else []
                )
    for name, config in defs.items():
        if name == "sections" or not isinstance(config, dict):
            continue
        found.append((f"{prefix}{name}", config))
        if config.get("type") == "object":
            found += _fields(config.get("properties"), f"{prefix}{name}.", data)
        if config.get("type") == "array":
            rows = _value_at(data, f"{prefix}{name}")
            if isinstance(rows, list) and isinstance(config.get("items"), dict):
                found += _fields(
                    {str(index): config["items"] for index in range(len(rows))},
                    f"{prefix}{name}.",
                    data,
                )
    return found


def _value_at(data: Any, path: str) -> Any:
    for key in path.split("."):
        if isinstance(data, dict) and key in data:
            data = data[key]
        elif isinstance(data, list) and _INDEX.fullmatch(key) and int(key) < len(data):
            data = data[int(key)]
        else:
            return _MISSING
    return data


def _scalar(value: Any) -> bool:
    return value is None or isinstance(value, str | int | float)


def _same(a: Any, b: Any) -> bool:
    return bool(a == b and isinstance(a, bool) == isinstance(b, bool))


def condition_holds(condition: Any, data: Any) -> bool:
    """Whether ``condition`` holds for ``data`` (module docstring)."""
    if not isinstance(condition, dict) or not all(
        _scalar(v) or (isinstance(v, list) and all(map(_scalar, v)))
        for v in condition.values()
    ):
        return True  # no condition, or malformed: shown and required, never skipped
    return all(
        any(
            _same(_value_at(data, path), option)
            for option in (expected if isinstance(expected, list) else [expected])
        )
        for path, expected in condition.items()
    )


def visible_when(config: dict[str, Any]) -> Any:
    """The field's ``visible_when``, or its alias ``show_when`` when that is absent or null."""
    when = config.get("visible_when")
    return config.get("show_when") if when is None else when


def is_visible(config: dict[str, Any], data: Any) -> bool:
    """The field's own ``visible_when`` (or ``show_when``) holds."""
    return condition_holds(visible_when(config), data)


def required_when_holds(config: dict[str, Any], data: Any) -> bool:
    """The field has a ``required_when`` and it holds."""
    when = config.get("required_when")
    return when is not None and condition_holds(when, data)


def missing_required_fields(
    field_definitions: Any, data: Any, validation_rules: Any = None
) -> list[str]:
    """Dotted paths of required fields empty in ``data``.

    Fields from flat/nested definitions or ``sections[].fields[]``; required and shown as the
    module docstring says. False is an answered boolean. Mirrored by the frontend requiredFields.ts.
    """
    fields = _fields(field_definitions, data=data)
    configs = dict(fields)
    rules = validation_rules if isinstance(validation_rules, dict) else {}
    paths = [
        path
        for path, config in fields
        if config.get("required") is True or required_when_holds(config, data)
    ]
    listed = rules.get("required_fields")
    paths += (
        [p for p in listed if isinstance(p, str)] if isinstance(listed, list) else []
    )
    conditional = rules.get("conditional_required")
    if isinstance(conditional, dict):
        paths += [
            path
            for path, rule in conditional.items()
            if condition_holds(
                rule.get("when") if isinstance(rule, dict) else rule, data
            )
        ]
    return [
        path
        for path in dict.fromkeys(paths)
        if _shown(configs, path, data) and _is_empty(_value_at(data, path))
    ]


def _shown(configs: dict[str, dict[str, Any]], path: str, data: Any) -> bool:
    """The field and every parent it has a config for are visible."""
    parts = path.split(".")
    prefixes = (".".join(parts[: i + 1]) for i in range(len(parts)))
    return all(is_visible(configs[p], data) for p in prefixes if p in configs)
