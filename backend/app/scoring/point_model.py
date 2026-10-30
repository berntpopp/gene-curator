"""Interpreter for a point model: item points, category/section caps, bands and a trace.

A point model (``scoring_configuration.point_model``, else the template file named after
``scoring_configuration.engine``) is ``{total_cap, sections: [{key, cap, categories:
[{key, cap, combine?, types: [{path, default?, points_key?, rule?, range?}]}]}],
overrides: [{when, field?, in?, class}], bands: [{class, min?, requires?, section_min?}]}``. ``path`` is dotted and relative to the section's evidence.
"""

import json
import math
from collections.abc import Callable
from functools import cache
from pathlib import Path
from typing import Any

from .evidence_items import has_content, indexed, rows, uncited

TEMPLATES = Path(__file__).parent / "templates"
# (type definition, evidence row) -> points; None means the row is not entered evidence
ItemRule = Callable[[dict[str, Any], dict[str, Any]], float | None]
# (section key, flat legacy item list, flags, excluded) -> {category key: [item points]}
LegacyRule = Callable[[str, list[Any], list[Any], list[Any]], dict[str, list[float]]]


@cache
def template(engine: str) -> dict[str, Any] | None:
    """The bundled point model for an engine name, if one ships."""
    names = {p.stem for p in TEMPLATES.glob("*.json")}  # never build a path from data
    if engine not in names:
        return None
    model: dict[str, Any] = json.loads((TEMPLATES / f"{engine}.json").read_text())
    return model


def point_model(scoring_configuration: dict[str, Any] | None) -> dict[str, Any] | None:
    """The configured point model, else the engine's template, else None."""
    config = scoring_configuration or {}
    model = config.get("point_model")
    if isinstance(model, dict):
        return model
    engine = config.get("engine")
    return template(engine) if isinstance(engine, str) else None


def default_points(type_def: dict[str, Any], row: dict[str, Any]) -> float:
    """The row's points, or the type's default when the row has no points key."""
    value = row.get(type_def.get("points_key", "points"), type_def.get("default", 0))
    return float(value or 0)


def _at(data: Any, path: str) -> Any:
    for key in path.split("."):
        data = data.get(key) if isinstance(data, dict) else None
    return data


def _category(
    category: dict[str, Any], points: dict[str, list[float]]
) -> dict[str, Any]:
    totals = [sum(values) for values in points.values()]
    types = [
        {"path": path, "items": len(values), "score": total}
        for (path, values), total in zip(points.items(), totals, strict=True)
    ]
    raw = max(totals, default=0.0) if category.get("combine") == "max" else sum(totals)
    cap = category.get("cap")
    return {
        "key": category["key"],
        "raw": raw,
        "cap": cap,
        "score": raw if cap is None else min(raw, cap),
        "types": types,
    }


def _type_points(
    path: str,
    type_def: dict[str, Any],
    data: Any,
    rule: ItemRule,
    flags: list[Any],
    excluded: list[Any],
) -> list[float]:
    """Entered rows' points; rows outside the type's range or non-finite are flagged and
    count nothing (#278), never clamped. Rows with points but no citation count nothing and are listed in ``excluded``."""
    limits = type_def.get("range")
    points = []
    for i, row in indexed(_at(data, type_def["path"])):
        value = rule(type_def, row)
        if value is None:
            continue
        finite = math.isfinite(value)
        flagged = not finite or (limits and not limits[0] <= value <= limits[1])
        if flagged:
            key = type_def.get("points_key", "points")
            if not finite and type_def.get("rule") == "segregation" and key not in row:
                key = (
                    "lod_score"
                    if row.get("lod_score") is not None
                    else "segregations_counted"
                )
            flags.append(
                {
                    "path": f"{path}[{i}].{key}",
                    "value": value if finite else str(value),  # JSONB has no NaN
                    "range": list(limits) if limits else None,  # not the cached model's
                }
            )
        case_row = type_def.get("rule") == "case_row"
        case_level = case_row or type_def.get("require_variant") is True  # #535
        if value > 0 and (why := uncited(row, case_level, by_status=case_row)):
            excluded.append({"path": f"{path}[{i}]", **why})
        elif not flagged:  # flagged rows count nothing (#278); the trace lists them
            points.append(value)
    return points


def _section_points(
    section: dict[str, Any],
    data: Any,
    rules: dict[str, ItemRule],
    legacy: LegacyRule | None,
    flags: list[Any],
    excluded: list[Any],
) -> dict[str, dict[str, list[float]]]:
    """{category key: {type path: [item points]}} for one section's evidence."""
    if isinstance(data, list) and legacy is not None:
        by_category = legacy(section["key"], data, flags, excluded)
        return {
            c["key"]: {"legacy": by_category.get(c["key"], [])}
            for c in section["categories"]
        }
    out: dict[str, dict[str, list[float]]] = {}
    for category in section["categories"]:
        out[category["key"]] = {}
        for type_def in category["types"]:
            rule = rules.get(type_def.get("rule", ""), default_points)
            path = f"{section['key']}.{type_def['path']}"
            out[category["key"]][type_def["path"]] = _type_points(
                path, type_def, data, rule, flags, excluded
            )
    return out


def classify(
    model: dict[str, Any],
    total: float,
    evidence: dict[str, Any],
    sections: dict[str, float] | None = None,
) -> dict[str, Any]:
    """First matching override (curator-asserted evidence), else first matching band.

    ``sections`` are the capped section scores a band's ``section_min`` is checked against.
    """
    sections = sections or {}
    for override in model.get("overrides", []):
        value = evidence.get(override["when"])
        if "field" in override:  # only rows whose field holds one of the "in" values
            value = [
                r for r in rows(value) if r.get(override["field"]) in override["in"]
            ]
        if has_content(value):
            return dict(override)
    for band in model["bands"]:
        if (
            total >= band.get("min", float("-inf"))
            and ("requires" not in band or evidence.get(band["requires"]) is True)
            and all(
                sections.get(key, 0) >= low
                for key, low in band.get("section_min", {}).items()
            )
        ):
            return dict(band)
    return {"class": "no_known"}  # ponytail: only reached when no band lacks a min


def score(
    model: dict[str, Any],
    evidence: dict[str, Any],
    rules: dict[str, ItemRule] | None = None,
    legacy: LegacyRule | None = None,
) -> dict[str, Any]:
    """Interpret ``model`` over ``evidence``: {total, class, sections, trace, excluded}."""
    sections = []
    flags: list[Any] = []
    excluded: list[Any] = []
    for section in model["sections"]:
        points = _section_points(
            section, evidence.get(section["key"]), rules or {}, legacy, flags, excluded
        )
        categories = [_category(c, points[c["key"]]) for c in section["categories"]]
        raw = sum(c["score"] for c in categories)
        cap = section.get("cap")
        sections.append(
            {
                "key": section["key"],
                "raw": raw,
                "cap": cap,
                "score": raw if cap is None else min(raw, cap),
                "categories": categories,
            }
        )
    raw_total = sum(s["score"] for s in sections)
    total_cap = model.get("total_cap")
    total = raw_total if total_cap is None else min(raw_total, total_cap)
    band = classify(model, total, evidence, {s["key"]: s["score"] for s in sections})
    trace = {
        "raw_total": raw_total,
        "total_cap": total_cap,
        "total": total,
        "class": band["class"],
        "classification_rule": band,
        "sections": sections,
    }
    if flags:  # only then: unflagged traces stay as stored
        trace["out_of_range"] = flags
    return {
        "total": total,
        "class": band["class"],
        "description": band.get("description", ""),
        "sections": {s["key"]: s["score"] for s in sections},
        "trace": trace,
        "excluded": excluded,
    }
