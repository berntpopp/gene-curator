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


# Field types the renderer accepts (form vocabulary plus the seeded JSON-schema style)
VALID_FIELD_TYPES = (
    *("text", "number", "boolean", "array", "object", "date", "select", "multiselect"),
    *("string", "integer", "enum", "textarea", "external_reference", "evidence_table"),
)
Diagnostic = tuple[str, str, str]  # (severity, JSON path, message)


def check_schema_definition(schema: dict[str, Any]) -> list[Diagnostic]:
    """Static checks of a schema definition; each diagnostic names a JSON path (#269)."""
    out: list[Diagnostic] = []
    for key in ("field_definitions", "workflow_states", "ui_configuration"):
        if not schema.get(key):
            out.append(("error", key, f"Missing required field: {key}"))
    fields = schema.get("field_definitions") or {}
    names: set[str] = set()
    if not isinstance(fields, dict):
        out.append(
            ("error", "field_definitions", "field_definitions must be a dictionary")
        )
    else:
        for path, name, cfg in _field_items(fields):
            names.add(name)
            out += _check_field(path, name, cfg)
    out += _check_workflow(schema.get("workflow_states"))
    ui = schema.get("ui_configuration")
    if ui is not None and not isinstance(ui, dict):
        out.append(
            ("error", "ui_configuration", "ui_configuration must be a dictionary")
        )
    elif isinstance(ui, dict) and "sections" not in ui:
        msg = "UI configuration missing 'sections' - form may not render properly"
        out.append(("warning", "ui_configuration.sections", msg))
    out += _check_scoring(schema.get("scoring_configuration"))
    out += _check_rules(schema.get("validation_rules"), names)
    return out


def _field_items(fields: dict[str, Any]) -> Any:
    """(path, name, config) for flat fields and the seeded `sections` list shape."""
    for name, cfg in fields.items():
        if name != "sections" or not isinstance(cfg, list):
            yield f"field_definitions.{name}", name, cfg
            continue
        for i, section in enumerate(cfg):
            section_fields = (
                section.get("fields") if isinstance(section, dict) else None
            )
            for j, f in enumerate(section_fields or []):
                key = f.get("id", "?") if isinstance(f, dict) else "?"
                yield f"field_definitions.sections[{i}].fields[{j}]", str(key), f


def _check_field(path: str, name: str, cfg: Any) -> list[Diagnostic]:
    if not isinstance(cfg, dict):
        return [
            ("error", path, f"Field configuration for '{name}' must be a dictionary")
        ]
    field_type = cfg.get("type")
    if field_type is None:
        return [
            ("error", f"{path}.type", f"Field '{name}' missing required property: type")
        ]
    if field_type not in VALID_FIELD_TYPES:
        msg = f"Field '{name}' has invalid type: {field_type}"
        return [("error", f"{path}.type", msg)]
    if field_type != "evidence_table":
        return []
    columns = cfg.get("columns")
    if not isinstance(columns, dict | list) or not columns:
        return [("error", f"{path}.columns", f"Evidence table '{name}' needs columns")]
    items = columns.items() if isinstance(columns, dict) else enumerate(columns)
    return [
        (
            "error",
            f"{path}.columns.{key}.type",
            f"Column '{key}' of '{name}' has no type",
        )
        for key, col in items
        if not (isinstance(col, dict) and col.get("type"))
    ]


def _check_workflow(states: Any) -> list[Diagnostic]:
    if states is None:
        return []
    if (
        isinstance(states, dict)
        and "states" not in states
        and "transitions" not in states
    ) and all(isinstance(v, dict) for v in states.values()):
        return _check_stage_map(states)
    if isinstance(states, dict) and "states" in states:
        names = [s.get("name") for s in states["states"] if isinstance(s, dict)]
        transitions = states.get("transitions") or {}
    elif isinstance(states, list):
        names, transitions = states, {}
    elif isinstance(states, dict):
        msg = "workflow_states must list states or map state names to objects"
        return [("error", "workflow_states", msg)]
    else:
        return [("error", "workflow_states", "workflow_states must be a list")]
    out: list[Diagnostic] = [
        ("error", "workflow_states", f"Missing required workflow state: {s}")
        for s in ("draft", "submitted")
        if s not in names
    ]
    for source, targets in transitions.items():
        for i, target in enumerate(targets if isinstance(targets, list) else []):
            if target not in names:
                path = f"workflow_states.transitions.{source}[{i}]"
                out.append(("error", path, f"Unknown transition target: {target}"))
    return out


def _check_stage_map(states: dict[str, Any]) -> list[Diagnostic]:
    """Stage-keyed map (seeded SOP schemas): targets are known stages, reviewers 1-5."""
    from app.models.model_enums import WorkflowStage

    known = set(states) | {stage.value for stage in WorkflowStage}
    out: list[Diagnostic] = []
    for stage, cfg in states.items():
        for i, target in enumerate(cfg.get("allowed_transitions") or []):
            if target not in known:
                path = f"workflow_states.{stage}.allowed_transitions[{i}]"
                out.append(("error", path, f"Unknown transition target: {target}"))
    reviewers = (states.get("review") or {}).get("reviewers_required")
    if reviewers is not None and (
        isinstance(reviewers, bool) or reviewers not in range(1, 6)
    ):
        msg = "reviewers_required must be an integer from 1 to 5"
        out.append(("error", "workflow_states.review.reviewers_required", msg))
    return out


def _is_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _check_scoring(scoring: Any) -> list[Diagnostic]:
    path = "scoring_configuration"
    if scoring is None:
        return []  # absent or null both mean "no scoring"
    if not isinstance(scoring, dict):
        return [("error", path, "scoring_configuration must be a dictionary")]
    out: list[Diagnostic] = []
    if "engine" not in scoring:
        msg = "Scoring configuration missing 'engine' specification"
        out.append(("warning", f"{path}.engine", msg))
    else:
        from app.scoring.registry import scoring_registry

        if scoring_registry.get_engine(str(scoring["engine"])) is None:
            msg = f"Unknown scoring engine: {scoring['engine']}"
            out.append(("error", f"{path}.engine", msg))
    # ponytail: assumes point_model {categories: {key: {cap}}, bands: [{min}]}; align with W4E
    model = scoring.get("point_model")
    if isinstance(model, dict):
        categories = model.get("categories") or {}
        items = (
            categories.items()
            if isinstance(categories, dict)
            else enumerate(categories)
        )
        for key, cat in items:
            if not (isinstance(cat, dict) and _is_number(cat.get("cap"))):
                cap_path = f"{path}.point_model.categories.{key}.cap"
                out.append(("error", cap_path, f"Category '{key}' needs a numeric cap"))
        lows: list[Any] = [
            b.get("min") if isinstance(b, dict) else None
            for b in model.get("bands") or []
        ]
        if not all(_is_number(low) for low in lows) or lows != sorted(lows):
            msg = "Bands need a numeric min and must be ordered by it"
            out.append(("error", f"{path}.point_model.bands", msg))
    return out


def _check_rules(rules: Any, names: set[str]) -> list[Diagnostic]:
    if rules is None:
        return []
    if not isinstance(rules, dict):
        return [("error", "validation_rules", "validation_rules must be a dictionary")]
    out: list[Diagnostic] = []
    for i, name in enumerate(rules.get("required_fields") or []):
        if name not in names:
            path = f"validation_rules.required_fields[{i}]"
            out.append(("error", path, f"Unknown field in required_fields: {name}"))
    for i, rule in enumerate(rules.get("custom_validators") or []):
        name = rule.get("field") if isinstance(rule, dict) else None
        if name not in names:
            path = f"validation_rules.custom_validators[{i}].field"
            out.append(("error", path, f"Unknown field in custom_validators: {name}"))
    return out
