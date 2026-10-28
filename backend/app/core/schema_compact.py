"""Agent-sized views of a curation schema's field definitions (MCP study 6, round 3)."""

import json
from typing import Any

# Display-only keys; everything else (required_when, default_by, limits...) decides validity
_DISPLAY_KEYS = {
    "label",
    "description",
    "help_text",
    "order",
    "ui_component",
    "collapsible",
    "collapsed",
    "icon",
    "placeholder",
}
_NESTED_KEYS = ("properties", "columns", "item_schema", "items")


def compact_field(cfg: Any) -> Any:
    if isinstance(cfg, list):  # columns may be a list of column dicts
        return [compact_field(c) for c in cfg]
    if not isinstance(cfg, dict):
        return cfg
    out = {k: v for k, v in cfg.items() if k not in _DISPLAY_KEYS}
    if isinstance(cfg.get("options"), list):
        out["options"] = [_compact_option(o) for o in cfg["options"]]
    for key in _NESTED_KEYS:
        nested = cfg.get(key)
        if isinstance(nested, dict) and key != "items":  # map of child fields
            out[key] = {k: compact_field(v) for k, v in nested.items()}
        elif isinstance(nested, dict | list):  # one item field, or a column list
            out[key] = compact_field(nested)
    return out


def _compact_option(option: Any) -> Any:
    """{value, label} becomes the bare value; extra option keys are kept."""
    if not isinstance(option, dict):
        return option
    kept = {k: v for k, v in option.items() if k not in _DISPLAY_KEYS}
    return kept["value"] if kept.keys() == {"value"} else kept


def subtree(fields: dict[str, Any], path: str) -> Any:
    """The field at a dotted path through properties and array items.

    Raises KeyError naming the missing key and the keys that exist there.
    """
    node: Any = {"properties": fields}
    for key in path.split("."):
        items = node.get("items") if isinstance(node, dict) else None
        children = (
            (node.get("properties") if isinstance(node, dict) else None)
            or (items.get("properties") if isinstance(items, dict) else None)
            or {}
        )
        if key not in children:
            options = ", ".join(children) or "none, it is a single field"
            raise KeyError(f"path {path!r}: no {key!r} here; choose from {options}")
        node = children[key]
    return node


def rules_for(rules: dict[str, Any], path: str, fields: Any) -> dict[str, Any]:
    """The validation rules that touch a subtree: named by one of its fields
    ("validation": "pmid_format") or naming a key on the path in their text."""
    used = json.dumps(fields)
    keys = path.split(".")
    return {
        name: rule
        for name, rule in rules.items()
        if f'"{name}"' in used or any(key in json.dumps(rule) for key in keys)
    }


def ranges_for(model: dict[str, Any], path: str) -> list[dict[str, Any]]:
    """Point range and category cap of each evidence type at, under or above path."""
    return [
        {"path": full, "range": t["range"], "category_cap": c.get("cap")}
        for s in model.get("sections", [])
        for c in s.get("categories", [])
        for t in c.get("types", [])
        if "range" in t
        and (
            (full := f"{s['key']}.{t['path']}") == path
            or full.startswith(f"{path}.")
            or path.startswith(f"{full}.")
        )
    ]
