"""Synopsis per curated entity (like SysNDD's clinical synopsis): the schema's
`ui_configuration.synopsis_field` names one text field (a dotted path through object
fields, e.g. evidence_summary); unset means no synopsis. Shown with the same
visibility as the evidence (members; others only when export_evidence_public is on)."""

from typing import Any

TEXT_TYPES = ("text", "textarea", "string")
KEY = "synopsis_field"


def _field(fields: Any, path: str) -> dict[str, Any] | None:
    if not isinstance(fields, dict):
        return None
    node: dict[str, Any] = {k: v for k, v in fields.items() if k != "sections"}
    for section in fields.get("sections") or []:  # seeded precuration shape
        for f in section.get("fields", []) if isinstance(section, dict) else []:
            if isinstance(f, dict) and f.get("id"):
                node.setdefault(f["id"], f)
    cfg: Any = None
    for part in path.split("."):
        cfg = node.get(part)
        if not isinstance(cfg, dict):
            return None
        node = cfg.get("properties") or {}
    return cfg if isinstance(cfg, dict) else None


def synopsis_diagnostics(schema: dict[str, Any]) -> list[tuple[str, str, str]]:
    """An error when synopsis_field is set but names no text field."""
    ui = schema.get("ui_configuration")
    path = ui.get(KEY) if isinstance(ui, dict) else None
    if path is None:
        return []
    cfg = (
        _field(schema.get("field_definitions"), path) if isinstance(path, str) else None
    )
    if cfg is None or cfg.get("type") not in TEXT_TYPES:
        msg = f"synopsis_field '{path}' must name a text or textarea field"
        return [("error", f"ui_configuration.{KEY}", msg)]
    return []


def synopsis_of(evidence: Any, ui: Any) -> str | None:
    """The synopsis text of a curation's evidence, or None."""
    path = ui.get(KEY) if isinstance(ui, dict) else None
    value: Any = evidence
    for part in path.split(".") if isinstance(path, str) else [None]:
        value = value.get(part) if isinstance(value, dict) and part else None
    return value.strip() or None if isinstance(value, str) else None
