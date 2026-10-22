"""Static checks for numeric defaults selected by another column in the same row."""

import math
from typing import Any

Diagnostic = tuple[str, str, str]


def finite_number(value: Any) -> bool:
    return (
        isinstance(value, int | float)
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _mapping_errors(cfg: dict[str, Any], siblings: dict[str, Any]) -> list[str]:
    mapping = cfg["default_by"]
    if not isinstance(mapping, dict) or not isinstance(mapping.get("field"), str):
        return ["default_by must contain a selector field and values object"]
    if cfg.get("type") not in ("number", "integer", "score"):
        return ["default_by is only supported on numeric columns"]
    selector = siblings.get(mapping["field"])
    if not isinstance(selector, dict) or selector.get("type") not in (
        "select",
        "enum",
        "string",
    ):
        return ["default_by.field must reference an enum selector in the same row"]
    options = selector.get("options", selector.get("enum", []))
    allowed = (
        {str(o.get("value")) if isinstance(o, dict) else str(o) for o in options}
        if isinstance(options, list)
        else set()
    )
    values = mapping.get("values")
    if not allowed or not isinstance(values, dict) or not values:
        return ["default_by needs selector options and a nonempty values object"]
    errors = []
    low = cfg.get("minimum", cfg.get("min_value", cfg.get("min")))
    high = cfg.get("maximum", cfg.get("max_value", cfg.get("max")))
    for key, value in values.items():
        if key not in allowed:
            errors.append(f"default_by value {key!r} is not a selector option")
        if not finite_number(value):
            errors.append(f"default_by value {key!r} must be a finite number")
        elif (finite_number(low) and value < low) or (
            finite_number(high) and value > high
        ):
            errors.append(f"default_by value {key!r} is outside the column bounds")
    return errors


def check_default_mappings(
    fields: Any, path: str = "field_definitions"
) -> list[Diagnostic]:
    if not isinstance(fields, dict):
        return []
    errors: list[Diagnostic] = []
    for name, cfg in fields.items():
        if not isinstance(cfg, dict):
            continue
        here = f"{path}.{name}"
        if "default_by" in cfg:
            errors += [
                ("error", f"{here}.default_by", msg)
                for msg in _mapping_errors(cfg, fields)
            ]
        for key in ("properties", "columns", "item_schema"):
            children = cfg.get(key)
            if isinstance(children, list):
                children = {
                    str(c.get("key", c.get("id", i))): c
                    for i, c in enumerate(children)
                    if isinstance(c, dict)
                }
            errors += check_default_mappings(children, f"{here}.{key}")
        if isinstance(cfg.get("items"), dict):
            errors += check_default_mappings({"items": cfg["items"]}, here)
    return errors
