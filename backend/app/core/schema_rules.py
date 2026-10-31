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
from app.llm.sharing import check_llm_share
from app.scoring.classifications import check_classifications


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
    out += check_llm_share(fields)  # #534
    out += _check_workflow(schema.get("workflow_states"))
    ui = schema.get("ui_configuration")
    if ui is not None and not isinstance(ui, dict):
        out.append(
            ("error", "ui_configuration", "ui_configuration must be a dictionary")
        )
    elif isinstance(ui, dict) and "sections" not in ui:
        msg = "UI configuration missing 'sections' - form may not render properly"
        out.append(("warning", "ui_configuration.sections", msg))
    known = fields if isinstance(fields, dict) else None
    out += _check_scoring(schema.get("scoring_configuration"), known)
    out += _check_rules(schema.get("validation_rules"), names)
    if known is not None:
        out += _check_conditions(known)
    return out


def _children(cfg: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
    """(JSON key, child fields) of an object field or table, as normalizeDefinition.ts reads them."""
    for key in ("properties", "columns", "item_schema"):
        if isinstance(cfg.get(key), dict):
            return key, cfg[key]
    items = cfg.get("items")
    if isinstance(items, dict) and isinstance(items.get("properties"), dict):
        return "items.properties", items["properties"]
    return None


def _top_fields(fields: dict[str, Any]) -> dict[str, Any]:
    """Flat fields plus the seeded ``sections[].fields[]`` shape, by data key."""
    out = {
        k: v for k, v in fields.items() if k != "sections" or not isinstance(v, list)
    }
    for _, name, cfg in _field_items(fields):
        out.setdefault(name, cfg)
    return out


def field_exists(fields: dict[str, Any], path: str) -> bool:
    """Whether a dotted data path names a field; numeric segments index a list.
    ponytail: below a field without readable children (leaf, list columns) anything passes."""
    node: dict[str, Any] | None = _top_fields(fields)
    for key in path.split("."):
        if node is None:
            return True
        if key.isdigit():
            continue
        cfg = node.get(key)
        if not isinstance(cfg, dict):
            return False
        found = _children(cfg)
        node = found[1] if found else None
    return True


def _check_conditions(fields: dict[str, Any]) -> list[Diagnostic]:
    """A ``visible_when``/``show_when`` path that names no field never holds (#576)."""
    out: list[Diagnostic] = []
    todo = [(path, cfg) for path, _, cfg in _field_items(fields)]
    while todo:
        path, cfg = todo.pop()
        if not isinstance(cfg, dict):
            continue
        for key in ("visible_when", "show_when"):
            condition = cfg.get(key)
            for target in condition if isinstance(condition, dict) else ():
                if not field_exists(fields, str(target)):
                    msg = f"{key} names an unknown field: {target}"
                    out.append(("error", f"{path}.{key}.{target}", msg))
        if found := _children(cfg):
            todo += [(f"{path}.{found[0]}.{k}", c) for k, c in found[1].items()]
    return sorted(out)


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


def _check_scoring(
    scoring: Any, fields: dict[str, Any] | None = None
) -> list[Diagnostic]:
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
        model = scoring["point_model"]
        out += _check_point_model(model, f"{path}.point_model")
        if fields is not None:
            out += _check_model_paths(model, f"{path}.point_model", fields)
    elif scoring.get("engine") == "point_model":
        msg = "The point_model engine needs a point_model"
        out.append(("error", f"{path}.point_model", msg))
    if "classifications" in scoring:
        out += check_classifications(scoring, path)
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
    section_keys = {s.get("key") for _, s in _dicts(sections)}
    for i, band in bands:
        out += _check_band(band, f"{path}.bands[{i}]", section_keys)
    lows: list[Any] = [band["min"] for _, band in bands if "min" in band]
    # first match wins, so thresholds must not increase down the list
    if not all(_is_number(low) for low in lows) or lows != sorted(lows, reverse=True):
        msg = "Band min must be numeric and must not increase (first match wins)"
        out.append(("error", f"{path}.bands", msg))
    flags_path = f"{path}.review_flags"
    out += _check_review_flags(model.get("review_flags", {}), flags_path, section_keys)
    return out


def _check_model_paths(
    model: dict[str, Any], path: str, fields: dict[str, Any]
) -> list[Diagnostic]:
    """Evidence paths the model reads must name fields, or they silently score 0 (#576).
    A section whose key is no field reads its paths from the top level, as the scorer does
    for forms built in the UI (B3); a flat-list section is scored by the legacy rule.
    ponytail: skipped when the fields describe no evidence (no section key is a field and
    no top-level evidence table)."""
    top = _top_fields(fields)
    sections = _dicts(_as(list, model.get("sections")))
    tables = any(_as(dict, cfg).get("type") == "evidence_table" for cfg in top.values())
    if not tables and not any(section.get("key") in top for _, section in sections):
        return []
    found: list[tuple[str, str]] = []  # (JSON path, data path)
    for i, section in sections:
        key = str(section.get("key"))
        if _as(dict, top.get(key)).get("type") == "array":
            continue
        base = f"{key}." if key in top else ""  # per section, as the scorer reads it
        for j, cat in _dicts(_as(list, section.get("categories"))):
            for k, item in _dicts(_as(list, cat.get("types"))):
                at = f"{path}.sections[{i}].categories[{j}].types[{k}]"
                table = f"{base}{item.get('path')}"
                found += _type_paths(item, at, table)
    for i, override in _dicts(_as(list, model.get("overrides"))):
        at = f"{path}.overrides[{i}]"
        found.append((f"{at}.when", str(override.get("when"))))
        if isinstance(override.get("field"), str):
            found.append((f"{at}.field", f"{override.get('when')}.{override['field']}"))
    return [
        ("error", at, f"Unknown evidence field: {target}")
        for at, target in found
        if not field_exists(fields, target)
    ]


def _type_paths(item: dict[str, Any], at: str, table: str) -> list[tuple[str, str]]:
    """(JSON path, data path) of what one evidence type reads: its table and row fields."""
    found = [(f"{at}.path", table)]
    if isinstance(item.get("field"), str):
        found.append((f"{at}.field", f"{table}.{item['field']}"))
    for m, rule in _dicts(_as(list, item.get("points_when"))):
        conditions = [(f"{at}.points_when[{m}]", rule)] + [
            (f"{at}.points_when[{m}].and[{n}]", c)
            for n, c in _dicts(_as(list, rule.get("and")))
        ]
        found += [
            (f"{p}.field", f"{table}.{c['field']}")
            for p, c in conditions
            if isinstance(c.get("field"), str)
        ]
    return found


def _check_review_flags(flags: Any, path: str, sections: set[Any]) -> list[Diagnostic]:
    """#559: each flag's settings, as ``review_flags`` in evidence_lint indexes them."""
    if not isinstance(flags, dict):
        return [("error", path, "review_flags must be an object")]
    out: list[Diagnostic] = [
        ("error", f"{path}.{key}", f"Unknown review flag: {key}")
        for key in flags
        if key not in ("band_margin", "hotspot", "experimental_over_genetic")
    ]
    margin = flags.get("band_margin", 0)
    if not (_is_number(margin) and margin >= 0):
        msg = "band_margin must be a number >= 0"
        out.append(("error", f"{path}.band_margin", msg))
    if "hotspot" in flags:
        out += _check_hotspot(flags["hotspot"], f"{path}.hotspot")
    pair = flags.get("experimental_over_genetic", [])
    keys = [key for key in _as(list, pair) if isinstance(key, str) and key in sections]
    if "experimental_over_genetic" in flags and not (
        pair == keys and len(set(keys)) == 2
    ):
        msg = "experimental_over_genetic must be [section key, section key]"
        out.append(("error", f"{path}.experimental_over_genetic", msg))
    return out


def _check_hotspot(hotspot: Any, path: str) -> list[Diagnostic]:
    if not isinstance(hotspot, dict):
        return [("error", path, "hotspot must be an object")]
    out: list[Diagnostic] = [
        ("error", f"{path}.{key}", f"Unknown hotspot key: {key}")
        for key in hotspot
        if key not in ("max_variants", "min_share")
    ]
    n, share = hotspot.get("max_variants"), hotspot.get("min_share")
    if not (isinstance(n, int) and not isinstance(n, bool) and n >= 1):
        msg = "max_variants must be an integer >= 1"
        out.append(("error", f"{path}.max_variants", msg))
    if not (_is_number(share) and isinstance(share, int | float) and 0 < share <= 1):
        msg = "min_share must be a number in (0, 1]"
        out.append(("error", f"{path}.min_share", msg))
    return out


BAND_KEYS = {"class", "min", "requires", "description", "section_min"}


def _check_band(
    band: dict[str, Any], path: str, sections: set[Any]
) -> list[Diagnostic]:
    """`class` required; an unknown key (a typo) would be silently ignored, so it errors."""
    out = _need(band, path, {"class": str})
    out += _optional(band, path, ("requires",))
    out += [
        ("error", f"{path}.{key}", f"Unknown band key: {key}")
        for key in band
        if key not in BAND_KEYS
    ]
    lows = band.get("section_min", {})
    if not isinstance(lows, dict):
        return [*out, ("error", f"{path}.section_min", "section_min must be an object")]
    for key, low in lows.items():
        if key not in sections or not _is_number(low):
            msg = "section_min maps an existing section key to a number"
            out.append(("error", f"{path}.section_min.{key}", msg))
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
    if "group_by" in item or "group_cap" in item:  # one never works without the other
        out += _need(item, path, {"group_by": str})
        if not _is_number(item.get("group_cap")):
            out.append(("error", f"{path}.group_cap", "group_cap must be a number"))
    out += _check_point_rules(item, path)
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


CONDITION_KEYS = {"field", "in", "gt", "gte", "lt", "lte", "present"}


def _check_condition(
    cond: dict[str, Any], path: str, extra: set[str]
) -> list[Diagnostic]:
    out = _need(cond, path, {"field": str})
    out += [
        ("error", f"{path}.{key}", f"Unknown condition key: {key}")
        for key in cond
        if key not in CONDITION_KEYS | extra
    ]
    if "in" in cond and not isinstance(cond["in"], list):
        out.append(("error", f"{path}.in", "'in' must be a list"))
    out += [
        ("error", f"{path}.{op}", f"'{op}' must be a number")
        for op in ("gt", "gte", "lt", "lte")
        if op in cond and not _is_number(cond[op])
    ]
    if not isinstance(cond.get("present", True), bool):
        out.append(("error", f"{path}.present", "'present' must be true or false"))
    if not (CONDITION_KEYS - {"field"}) & set(cond):
        msg = "A condition needs one of in, gt, gte, lt, lte, present"
        out.append(("error", path, msg))
    return out


def _check_point_rules(item: dict[str, Any], path: str) -> list[Diagnostic]:
    """#576: ``points_when`` rules and the ``step`` rule, as the interpreter indexes them."""
    out: list[Diagnostic] = []
    rules = item.get("points_when", [])
    if not isinstance(rules, list):
        out.append(("error", f"{path}.points_when", "points_when must be a list"))
    for i, rule in _items(_as(list, rules), f"{path}.points_when", out):
        at = f"{path}.points_when[{i}]"
        out += _check_condition(rule, at, {"points", "and"})
        if not _is_number(rule.get("points")):
            out.append(("error", f"{at}.points", "points must be a number"))
        for j, cond in _items(_as(list, rule.get("and", [])), f"{at}.and", out):
            out += _check_condition(cond, f"{at}.and[{j}]", set())
        if not isinstance(rule.get("and", []), list):
            out.append(("error", f"{at}.and", "'and' must be a list"))
    if item.get("rule") != "step":
        return out
    out += _need(item, path, {"field": str, "steps": list})
    steps = _items(_as(list, item.get("steps")), f"{path}.steps", out)
    lows: list[float] = [s.get("min", 0) for _, s in steps]
    if not all(
        _is_number(s.get("min")) and _is_number(s.get("points")) for _, s in steps
    ):
        out.append(("error", f"{path}.steps", "Each step needs numeric min and points"))
    elif lows != sorted(set(lows)):
        out.append(("error", f"{path}.steps", "Step min must increase"))
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
