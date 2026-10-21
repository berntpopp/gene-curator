"""Resolve a field's named validation rule (`"validation": "<rule>"`) into a regex pattern."""

from typing import Any


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
