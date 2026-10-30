"""Resolve a field's named validation rule (`"validation": "<rule>"`) into a regex pattern."""

from typing import Any
from urllib.parse import urlsplit

from app.core.schema_defaults import check_default_mappings, finite_number
from app.core.schema_validation_result import SchemaValidationResult

# One copy of the condition semantics (#433), shared with submit and the frontend
from app.crud.precuration_required import (
    is_visible,
    missing_required_fields,
    required_when_holds,
)


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


def resolve_conditions(fields: Any, data: Any, shown: bool = True) -> Any:
    """The fields as `data` shows them (frontend `resolveField`): one hidden by its own or a
    parent's condition is not required, a shown one whose `required_when` holds is."""
    if not isinstance(fields, dict):
        return fields
    return {
        name: _resolve_field(cfg, data, shown) if isinstance(cfg, dict) else cfg
        for name, cfg in fields.items()
    }


def _resolve_field(cfg: dict[str, Any], data: Any, shown: bool) -> dict[str, Any]:
    visible = shown and is_visible(cfg, data)
    cfg = dict(cfg)
    if not visible:
        cfg["required"] = False
    elif required_when_holds(cfg, data):
        cfg["required"] = True
    if "properties" in cfg:
        cfg["properties"] = resolve_conditions(cfg["properties"], data, visible)
    if isinstance(cfg.get("items"), dict):
        cfg["items"] = _resolve_field(cfg["items"], data, visible)
    return cfg


# Rule keys the seeded schemas store as lists/maps of fields rather than one rule config
FIELD_LIST_RULES = ("required_fields", "conditional_required", "custom_validators")


def apply_field_list_rules(
    data: dict[str, Any],
    rules: dict[str, Any],
    result: SchemaValidationResult,
    fields: dict[str, Any],
) -> dict[str, Any]:
    """Apply `required_fields`, `conditional_required` and `custom_validators` (#408).

    A field hidden by its condition in `fields` is not required. Returns the remaining
    (per-rule config) rules.
    """
    listed = _as(list, rules.get("required_fields"))
    conditional = _as(dict, rules.get("conditional_required"))
    for name in missing_required_fields(fields, data, rules):
        if (
            name in listed or name in conditional
        ) and name not in result.required_fields_missing:
            result.add_error(name, "Required field is missing", "required")
            result.required_fields_missing.append(name)
    for rule in _as(list, rules.get("custom_validators")):
        if not isinstance(rule, dict) or not isinstance(rule.get("field"), str):
            continue
        value = data.get(rule["field"])
        if isinstance(rule.get("pattern"), str) and isinstance(value, str) and value:
            result.check_pattern(
                rule["field"],
                rule["pattern"],
                value,
                {"pattern_message": rule.get("message")},
            )
    return {k: v for k, v in rules.items() if k not in FIELD_LIST_RULES}


def _as(kind: type, value: Any) -> Any:
    """`value` if it is a `kind`, else an empty `kind`."""
    return value if isinstance(value, kind) else kind()


# Field types the renderer accepts (form vocabulary plus the seeded JSON-schema style)
VALID_FIELD_TYPES = (
    *("text", "number", "boolean", "array", "object", "date", "select", "multiselect"),
    *("string", "integer", "enum", "textarea", "external_reference", "evidence_table"),
    "url",
)
Diagnostic = tuple[str, str, str]  # (severity, JSON path, message)


def valid_url(value: Any) -> bool:
    """Blank (a cleared optional field: `required` is its own rule) or an http(s) URL with a
    host without whitespace, like the form's `new URL` check (#538). Only spaces is not blank,
    so a required url of spaces fails here."""
    if value == "":
        return True
    text = value.strip() if isinstance(value, str) else None
    try:
        parts = urlsplit(text) if text else None
    except ValueError:  # e.g. an unclosed IPv6 bracket
        return False
    host = parts.hostname if parts and parts.scheme in ("http", "https") else None
    return bool(host) and not any(c.isspace() for c in host or "")


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
    out += check_default_mappings(fields)
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


# Stages every item passes through in the workflow engine (entry -> precuration -> review)
REQUIRED_STAGES = ("entry", "precuration", "review")


def _check_stage_map(states: dict[str, Any]) -> list[Diagnostic]:
    """Stage-keyed map (seeded SOP schemas): targets are known stages, reviewers 1-5."""
    from app.models.model_enums import WorkflowStage

    known = set(states) | {stage.value for stage in WorkflowStage}
    out: list[Diagnostic] = [
        ("error", "workflow_states", f"Missing required stage: {stage}")
        for stage in REQUIRED_STAGES
        if stage not in states
    ]
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
    if isinstance(scoring.get("point_model"), dict):
        out += _check_point_model(scoring["point_model"], f"{path}.point_model")
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


def _check_point_model(model: dict[str, Any], path: str) -> list[Diagnostic]:
    """The W4E interpreter shape: sections > categories > types, bands first match wins.

    Anything the scorer indexes directly is required, or every scoring call fails.
    """
    out = _need(model, path, {"sections": list, "bands": list})
    if "total_cap" in model and not _is_number(model["total_cap"]):
        out.append(("error", f"{path}.total_cap", "total_cap must be a number"))
    sections = _as(list, model.get("sections"))
    out += _check_nodes(sections, f"{path}.sections", "Section")
    for i, section in _items(sections, f"{path}.sections", out):
        out += _need(section, f"{path}.sections[{i}]", {"key": str, "categories": list})
        cats = _as(list, section.get("categories"))
        cat_path = f"{path}.sections[{i}].categories"
        out += _check_nodes(cats, cat_path, "Category")
        for j, cat in _items(cats, cat_path, out):
            out += _need(cat, f"{cat_path}[{j}]", {"key": str, "types": list})
            if cat.get("combine", "sum") not in ("sum", "max"):
                msg = "combine must be 'sum' or 'max'"
                out.append(("error", f"{cat_path}[{j}].combine", msg))
            types_path = f"{cat_path}[{j}].types"
            for k, item in _items(_as(list, cat.get("types")), types_path, out):
                out += _check_type(item, f"{types_path}[{k}]")
    overrides = _as(list, model.get("overrides"))
    for i, override in _items(overrides, f"{path}.overrides", out):
        out += _need(override, f"{path}.overrides[{i}]", {"when": str, "class": str})
        if "field" in override or "in" in override:  # one never works without the other
            out += _need(override, f"{path}.overrides[{i}]", {"field": str, "in": list})
    bands = _items(_as(list, model.get("bands")), f"{path}.bands", out)
    for i, band in bands:
        out += _need(band, f"{path}.bands[{i}]", {"class": str})
        out += _optional(band, f"{path}.bands[{i}]", ("requires",))
    lows: list[Any] = [band["min"] for _, band in bands if "min" in band]
    # first match wins, so thresholds must not increase down the list
    if not all(_is_number(low) for low in lows) or lows != sorted(lows, reverse=True):
        msg = "Band min must be numeric and must not increase (first match wins)"
        out.append(("error", f"{path}.bands", msg))
    return out


def _check_type(item: dict[str, Any], path: str) -> list[Diagnostic]:
    """One item type: `path` required; optional settings typed; range an ordered pair."""
    out = _need(item, path, {"path": str})
    out += _optional(item, path, ("rule", "points_key"))
    if "default" in item and not _is_number(item["default"]):
        out.append(("error", f"{path}.default", "default must be a number"))
    if not isinstance(item.get("require_variant", False), bool):
        msg = "require_variant must be true or false"
        out.append(("error", f"{path}.require_variant", msg))
    if (
        "blank_at" in item
        and item["blank_at"] is not None
        and not finite_number(item["blank_at"])
    ):
        out.append(
            ("error", f"{path}.blank_at", "blank_at must be null or a finite number")
        )
    if item.get("rule") == "case_row" and "blank_at" not in item:
        out.append(("error", f"{path}.blank_at", "case_row requires blank_at"))
    rng = item.get("range")
    if rng is not None and not (
        isinstance(rng, list)
        and len(rng) == 2
        and all(_is_number(x) for x in rng)
        and rng[0] <= rng[1]
    ):
        msg = "range must be [min, max] numbers with min <= max"
        out.append(("error", f"{path}.range", msg))
    return out


def _need(node: dict[str, Any], path: str, keys: dict[str, type]) -> list[Diagnostic]:
    """An error per required key that is missing or of the wrong type."""
    return [
        ("error", f"{path}.{key}", f"'{key}' is required and must be a {kind.__name__}")
        for key, kind in keys.items()
        if not isinstance(node.get(key), kind)
    ]


def _optional(
    node: dict[str, Any], path: str, keys: tuple[str, ...]
) -> list[Diagnostic]:
    """An error per optional key that is present but not a string."""
    return [
        ("error", f"{path}.{key}", f"'{key}' must be a str")
        for key in keys
        if key in node and not isinstance(node[key], str)
    ]


def _items(
    items: list[Any], path: str, out: list[Diagnostic]
) -> list[tuple[int, dict[str, Any]]]:
    """(index, item) for the dict items; every other item is an error at its index."""
    out += [
        ("error", f"{path}[{i}]", "Must be an object")
        for i, item in enumerate(items)
        if not isinstance(item, dict)
    ]
    return _dicts(items)


def _dicts(items: list[Any]) -> list[tuple[int, dict[str, Any]]]:
    """(index, item) for the dict items; the index keeps JSON paths exact."""
    return [(i, item) for i, item in enumerate(items) if isinstance(item, dict)]


def _check_nodes(nodes: list[Any], path: str, kind: str) -> list[Diagnostic]:
    """Numeric cap where present; keys unique."""
    out: list[Diagnostic] = []
    seen: set[str] = set()
    for i, node in _dicts(nodes):
        if "cap" in node and not _is_number(node["cap"]):
            out.append(("error", f"{path}[{i}].cap", f"{kind} cap must be a number"))
        key = str(node.get("key"))
        if key in seen:
            out.append(
                ("error", f"{path}[{i}].key", f"Duplicate {kind.lower()} key: {key}")
            )
        seen.add(key)
    return out
