"""Interpreter for a point model: item points, category/section caps, bands and a trace.

A point model (``scoring_configuration.point_model``, else the template file named after
``scoring_configuration.engine``) is ``{total_cap, sections: [{key, cap, categories:
[{key, cap, combine?, types: [{path, default?, points_key?, rule?, range?, group_by?, group_cap?,
points_when?, field?, steps?}]}]}],
overrides: [{when, field?, in?, class}], bands: [{class, min?, requires?, section_min?}],
review_flags?: {band_margin?, hotspot?: {max_variants, min_share}, experimental_over_genetic?:
[section, section]}}``. ``path`` is dotted and relative to the section's evidence.

``points_when: [{field, in?, gt?, gte?, lt?, lte?, and?: [condition], points}]`` sets a row's
points from its own fields; the first rule whose conditions all hold wins (#576).
``rule: "step"`` sums ``field`` over the type's rows and scores the highest
``steps: [{min, points}]`` reached as one item. Both are listed in the trace's ``rules_applied``.
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


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _holds(condition: dict[str, Any], row: dict[str, Any]) -> bool:
    """``in`` is strict (``true`` is not ``1``); comparisons need a number; ``present``
    is whether the value is set (not missing, null or a blank string)."""
    value = row.get(condition["field"])
    if "present" in condition and _blank(value) == condition["present"]:
        return False
    if "in" in condition and not any(
        option == value and isinstance(option, bool) == isinstance(value, bool)
        for option in condition["in"]
    ):
        return False
    bounds = [(op, condition[op]) for op in COMPARISONS if op in condition]
    number = _number(value) if bounds else None
    return not bounds or (
        number is not None and all(COMPARISONS[op](number, b) for op, b in bounds)
    )


COMPARISONS: dict[str, Callable[[float, float], bool]] = {
    "gt": lambda a, b: a > b,
    "gte": lambda a, b: a >= b,
    "lt": lambda a, b: a < b,
    "lte": lambda a, b: a <= b,
}


def _blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _points_when(
    type_def: dict[str, Any],
    row: dict[str, Any],
    entered: float,
    at: str,
    applied: list[Any],
) -> float:
    """A matching exclusion (0 points) wins wherever it stands; otherwise the first
    matching rule fills the points only when the curator left them blank."""
    hits = [
        (i, float(rule["points"]))
        for i, rule in enumerate(type_def.get("points_when", []))
        if all(_holds(c, row) for c in [rule, *rule.get("and", [])])
    ]
    if not hits:
        return entered
    i, points = next((hit for hit in hits if hit[1] == 0), hits[0])
    keep = points != 0 and not _blank(row.get(type_def.get("points_key", "points")))
    result = entered if keep else points
    applied.append(
        {"path": at, "rule": "points_when", "index": i}
        | {"entered": entered, "points": result, "applied": not keep}
    )
    return result


def _step_points(
    path: str,
    type_def: dict[str, Any],
    data: Any,
    flags: list[Any],
    excluded: list[Any],
    applied: list[Any],
) -> list[float]:
    """One item: the highest step the rows' summed ``field`` reaches; none without a value."""
    field, total, counted = type_def["field"], 0.0, False
    for i, row in indexed(_at(data, type_def["path"])):
        raw = row.get(field)
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            continue
        number = _number(raw)
        if number is None:  # counts nothing, like an out-of-range row (#278)
            flags.append(
                {"path": f"{path}[{i}].{field}", "value": str(raw), "range": None}
            )
        elif number > 0 and (why := uncited(row, False)):
            excluded.append({"path": f"{path}[{i}]", **why})
        else:
            total, counted = total + number, True
    if not counted:
        return []
    reached = [s["points"] for s in type_def["steps"] if total >= s["min"]]
    points = float(max(reached, default=0))
    applied.append(
        {"path": path, "rule": "step", "field": field, "sum": total, "points": points}
    )
    return [points]


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
    capped: list[Any],
    variants: dict[str, float],
    applied: list[Any],
) -> list[float]:
    """Entered rows' points; rows outside the type's range or non-finite are flagged and
    count nothing (#278), never clamped. Rows with points but no citation count nothing and are listed in ``excluded``.
    With ``group_by``, rows sharing a non-blank value score at most ``group_cap`` together (#557).
    Counted case-row points add up in ``variants`` by normalised variant (the #559 hotspot flag)."""
    if type_def.get("rule") == "step":
        return _step_points(path, type_def, data, flags, excluded, applied)
    limits = type_def.get("range")
    group_by = type_def.get("group_by")
    groups: dict[
        str, tuple[str, list[int]]
    ] = {}  # normalised -> (typed, point indexes)
    points: list[float] = []
    keys: list[str] = []  # each counted point's variant, for ``variants``
    for i, row in indexed(_at(data, type_def["path"])):
        value = rule(type_def, row)
        if value is None:
            continue
        value = _points_when(type_def, row, value, f"{path}[{i}]", applied)
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
            if group_by and (group := _norm(row.get(group_by))):
                typed = str(row[group_by])  # shown as the curator typed it
                groups.setdefault(group, (typed, []))[1].append(len(points))
            points.append(value)
            keys.append(
                _norm(row.get("variant_1" if "variant_1" in row else "variant"))
            )
    if groups:
        _cap_groups(path, type_def["group_cap"], groups, points, capped)
    _count_variants(type_def, keys, points, variants)
    return points


def _count_variants(
    type_def: dict[str, Any],
    keys: list[str],
    points: list[float],
    variants: dict[str, float],
) -> None:
    if type_def.get("rule") == "case_row":
        for key, value in zip(keys, points, strict=True):
            variants[key] = variants.get(key, 0.0) + value


def _norm(value: Any) -> str:
    return str(value or "").strip().casefold()


def _cap_groups(
    path: str,
    cap: float,
    groups: dict[str, tuple[str, list[int]]],
    points: list[float],
    capped: list[Any],
) -> None:
    """Cap each group's summed points in place; the group's first row carries the cap,
    so the trace's item count still counts rows."""
    for typed, at in groups.values():
        raw = sum(points[i] for i in at)
        if raw > cap:
            capped.append({"path": path, "value": typed, "raw": raw, "capped": cap})
            for i in at:
                points[i] = 0.0
            points[at[0]] = cap


def _section_points(
    section: dict[str, Any],
    data: Any,
    rules: dict[str, ItemRule],
    legacy: LegacyRule | None,
    flags: list[Any],
    excluded: list[Any],
    capped: list[Any],
    variants: dict[str, float],
    applied: list[Any],
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
                path, type_def, data, rule, flags, excluded, capped, variants, applied
            )
    return out


def classify(
    model: dict[str, Any],
    total: float,
    evidence: dict[str, Any],
    sections: dict[str, float],
) -> dict[str, Any]:
    """First matching override (curator-asserted evidence), else first matching band.

    ``sections`` are the capped section scores a band's ``section_min`` is checked against;
    bands passed over only for a section minimum are listed in the rule's ``skipped``.
    """
    skipped: list[dict[str, Any]] = []
    for override in model.get("overrides", []):
        value = evidence.get(override["when"])
        if "field" in override:  # only rows whose field holds one of the "in" values
            value = [
                r for r in rows(value) if r.get(override["field"]) in override["in"]
            ]
        if has_content(value):
            return dict(override)
    for band in model["bands"]:
        if total >= band.get("min", float("-inf")) and (
            "requires" not in band or evidence.get(band["requires"]) is True
        ):
            short = [
                {"class": band["class"], "section": key, "min": low, "score": got}
                for key, low in band.get("section_min", {}).items()
                if (got := sections.get(key, 0)) < low
            ]
            if not short:
                return {**band, "skipped": skipped} if skipped else dict(band)
            skipped += short
    # ponytail: only reached when no band lacks a min
    return (
        {"class": "no_known", "skipped": skipped} if skipped else {"class": "no_known"}
    )


def score(
    model: dict[str, Any],
    evidence: dict[str, Any],
    rules: dict[str, ItemRule] | None = None,
    legacy: LegacyRule | None = None,
) -> dict[str, Any]:
    """Interpret ``model`` over ``evidence``: {total, class, sections, trace, excluded,
    model, variant_points}."""
    sections = []
    flags: list[Any] = []
    excluded: list[Any] = []
    capped: list[Any] = []
    variants: dict[str, float] = {}
    applied: list[Any] = []
    for section in model["sections"]:
        data = evidence.get(section["key"])
        points = _section_points(
            section,
            data,
            rules or {},
            legacy,
            flags,
            excluded,
            capped,
            variants,
            applied,
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
    if capped:
        trace["capped_groups"] = capped
    if applied:
        trace["rules_applied"] = applied
    return {
        "total": total,
        "class": band["class"],
        "description": band.get("description", ""),
        "sections": {s["key"]: s["score"] for s in sections},
        "trace": trace,
        "excluded": excluded,
        "model": model,  # evidence_warnings reads its review_flags and bands (#559)
        "variant_points": variants,
    }
