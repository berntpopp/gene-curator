"""Schema-declared classification vocabulary (#539): `scoring_configuration.classifications`
is a list of {key, label, order, tone}. The frontend renders order, label and tone from it
and falls back to the ClinGen list without it."""

from typing import Any

from app.schemas.curation import class_key

# A tone renders like that ClinGen class (frontend config/classification.ts)
TONES = (
    "definitive",
    "strong",
    "moderate",
    "limited",
    "no_known",
    "disputed",
    "refuted",
)


def _clingen(key: object) -> str | None:
    """The ClinGen class `key` names ("No Known Disease Relationship" too), else None."""
    norm = class_key(str(key))
    return norm if norm in TONES else None


def _check_item(
    item: dict[str, Any], at: str, keys: set[str]
) -> list[tuple[str, str, str]]:
    """One vocabulary entry; adds its class key to `keys` ('Strong' and 'strong' clash)."""
    out: list[tuple[str, str, str]] = []
    key, label, order = item.get("key"), item.get("label"), item.get("order")
    norm = class_key(key) if isinstance(key, str) else ""
    if not norm or norm in keys:
        out.append(("error", f"{at}.key", "key must be a unique, non-empty text"))
    keys.add(norm)
    if not isinstance(label, str) or not label.strip():
        out.append(("error", f"{at}.label", "label must be a non-empty text"))
    if isinstance(order, bool) or not isinstance(order, int | float):
        out.append(("error", f"{at}.order", "order must be a number"))
    tone = item.get("tone")
    if tone not in TONES:
        msg = f"tone must be one of: {', '.join(TONES)}"
        out.append(("error", f"{at}.tone", msg))
    builtin = _clingen(key)
    if builtin and tone != builtin:
        msg = f"ClinGen class '{key}' keeps its own tone ({builtin})"
        out.append(("error", f"{at}.tone", msg))
    return out


def check_classifications(
    scoring: dict[str, Any], path: str
) -> list[tuple[str, str, str]]:
    """(severity, path, message) for a malformed vocabulary or a point-model class it lacks."""
    items = scoring.get("classifications")
    path = f"{path}.classifications"
    if not isinstance(items, list):
        return [("error", path, "classifications must be a list")]
    out: list[tuple[str, str, str]] = []
    keys: set[str] = set()
    for i, item in enumerate(items):
        at = f"{path}[{i}]"
        if not isinstance(item, dict):
            out.append(("error", at, "A classification must be an object"))
            continue
        out += _check_item(item, at, keys)
    model = scoring.get("point_model")
    rules = (
        [*model.get("bands", []), *model.get("overrides", [])]
        if isinstance(model, dict)
        else []
    )
    for cls in dict.fromkeys(r.get("class") for r in rules if isinstance(r, dict)):
        if isinstance(cls, str) and class_key(cls) not in keys:
            msg = f"Point model class '{cls}' is not in classifications"
            out.append(("error", path, msg))
    return out
