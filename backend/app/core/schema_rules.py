"""Resolve a field's named validation rule (`"validation": "<rule>"`) into a regex pattern."""

from typing import Any

from app.core.schema_validation_result import SchemaValidationResult


def resolve_named_rules(schema_definition: dict[str, Any]) -> Any:
    """The schema's field definitions with named regex rules turned into `pattern` + `pattern_message`."""
    return _resolve(
        schema_definition.get("field_definitions", {}),
        schema_definition.get("validation_rules", {}),
    )


def _resolve(fields: Any, rules: dict[str, Any]) -> Any:
    if not isinstance(fields, dict):
        return fields
    out: dict[str, Any] = {}
    for name, cfg in fields.items():
        if not isinstance(cfg, dict):
            out[name] = cfg
            continue
        cfg = dict(cfg)
        rule = rules.get(str(cfg.get("validation")))
        if (
            isinstance(rule, dict)
            and rule.get("type") == "regex"
            and rule.get("pattern")
        ):
            cfg["pattern"] = rule["pattern"]
            cfg["pattern_message"] = rule.get("message")
        if "properties" in cfg:
            cfg["properties"] = _resolve(cfg["properties"], rules)
        out[name] = cfg
    return out


# Rule keys the seeded schemas store as lists/maps of fields rather than one rule config
FIELD_LIST_RULES = ("required_fields", "conditional_required", "custom_validators")


def apply_field_list_rules(
    data: dict[str, Any], rules: dict[str, Any], result: SchemaValidationResult
) -> dict[str, Any]:
    """Apply `required_fields`, `conditional_required` and `custom_validators` (#408).

    Returns the remaining (per-rule config) rules.
    """
    required = list(rules.get("required_fields") or [])
    for name, cond in (rules.get("conditional_required") or {}).items():
        when = cond.get("when") if isinstance(cond, dict) else None
        if when and all(data.get(k) == v for k, v in when.items()):
            required.append(name)
    for name in required:
        if (
            data.get(name) in (None, "", [])
            and name not in result.required_fields_missing
        ):
            result.add_error(name, "Required field is missing", "required")
            result.required_fields_missing.append(name)
    for rule in rules.get("custom_validators") or []:
        value = data.get(rule.get("field"))
        if rule.get("pattern") and isinstance(value, str) and value:
            result.check_pattern(
                rule["field"],
                rule["pattern"],
                value,
                {"pattern_message": rule.get("message")},
            )
    return {k: v for k, v in rules.items() if k not in FIELD_LIST_RULES}
