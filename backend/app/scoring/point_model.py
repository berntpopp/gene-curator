"""Interpreter for a point model: item points, category/section caps, bands and a trace.

A point model (``scoring_configuration.point_model``, else the template file named after
``scoring_configuration.engine``) is ``{total_cap, sections: [{key, cap, categories:
[{key, cap, combine?, types: [{path, default?, points_key?, rule?, range?, group_by?, group_cap?,
points_when?, field?, steps?}]}]}],
overrides: [{when, field?, in?, class}], bands: [{class, min?, requires?, section_min?}],
review_flags?: {band_margin?, hotspot?: {max_variants, min_share}, experimental_over_genetic?:
[section, section]}}``. ``path`` is dotted and relative to the section's evidence; when
the evidence has nothing under the section key, it is read from the top level (forms built
in the UI store their fields flat).

``points_when: [{field, in?, present?, gt?, gte?, lt?, lte?, and?: [condition], points}]`` sets
a row's points from its own fields: a matching 0-point rule always wins, otherwise the first
matching rule fills the points only when the curator left them blank (#576, #582); then
``factor`` / ``max`` rules scale or cap it, and ``group_by`` may list fields or map one
field's values to named groups (``group_values``): docs/POINT-MODEL.md (#615).
``rule: "step"`` sums ``field`` over the type's rows and scores the highest
``steps: [{min, points}]`` reached as one item. ``rule: "segregation_sop11"`` scores a
segregation family table by SOP v11 pp.28-35 and Figure 6 (#447, docs/POINT-MODEL.md). All
three are listed in the trace's ``rules_applied``.

Under the neutral ``point_model`` engine a blank points cell (null, empty) scores the type's
default, as a missing key does; ClinGen keeps scoring an explicit null as 0 (golden parity).
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
        # The neutral engine (#576) has no ClinGen-era data to keep: blank is the default
        neutral = config.get("engine") == "point_model"
        return {**model, "blank_points_default": True} if neutral else model
    engine = config.get("engine")
    return template(engine) if isinstance(engine, str) else None


def default_points(type_def: dict[str, Any], row: dict[str, Any]) -> float:
    """The row's points, or the type's default when the row has no points key."""
    value = row.get(type_def.get("points_key", "points"), type_def.get("default", 0))
    return float(value or 0)


def blank_default_points(type_def: dict[str, Any], row: dict[str, Any]) -> float:
    """Like ``default_points``, but a blank cell also scores the type's default (B2)."""
    value = row.get(type_def.get("points_key", "points"))
    return default_points(type_def, {}) if _blank(value) else float(value or 0)


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
    is whether the value is set (not missing, null, a blank string or an empty list);
    ``in`` holds for a list cell when any of its values is an option."""
    value = row.get(condition["field"])
    if "present" in condition and _blank(value) == condition["present"]:
        return False
    values = value if isinstance(value, list) else [value]
    if "in" in condition and not any(
        option == v and isinstance(option, bool) == isinstance(v, bool)
        for option in condition["in"]
        for v in values
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
    return value in (None, []) or (isinstance(value, str) and not value.strip())


def _points_when(
    type_def: dict[str, Any],
    row: dict[str, Any],
    entered: float,
    at: str,
    applied: list[Any],
) -> float:
    """A matching exclusion (0 points) wins wherever it stands; otherwise the first
    matching rule fills the points only when the curator left them blank."""
    matching = [
        (i, rule)
        for i, rule in enumerate(type_def.get("points_when", []))
        if all(_holds(c, row) for c in [rule, *rule.get("and", [])])
    ]
    hits = [(i, float(rule["points"])) for i, rule in matching if "points" in rule]
    result = entered
    if hits:
        i, points = next((hit for hit in hits if hit[1] == 0), hits[0])
        keep = points != 0 and not _blank(row.get(type_def.get("points_key", "points")))
        result = entered if keep else points
        applied.append(
            {"path": at, "rule": "points_when", "index": i}
            | {"entered": entered, "points": result, "applied": not keep}
        )
    for i, rule in ((i, r) for i, r in matching if "points" not in r):  # factor / max
        before = result
        if "factor" in rule:
            result *= float(rule["factor"])
        else:
            result = min(result, float(rule["max"]))
        applied.append(
            {"path": at, "rule": "points_when", "index": i}
            | {"entered": before, "points": result, "applied": result != before}
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


# --- rule: segregation_sop11 (#447; SOP v11 pp.28-35, Figure 6 p.34) ---

LOG2 = math.log10(2)
# Figure 6: (summed LOD min, label, candidate gene C, comprehensive D), half-open bands
FIGURE_6 = [
    (5.0, ">=5", 1.5, 3.0),
    (3.0, "3-4.99", 1.0, 2.0),
    (2.0, "2-2.99", 0.5, 1.0),
    (-math.inf, "0-1.99", 0.0, 0.0),
]
SEGREGATION_MAX = 3.0  # Figure 2 p.17
METHODS = {"candidate_gene": "candidate gene", "comprehensive": "comprehensive"}
AR_BASES = {"ar_classic": (0.25, 0.75), "ar_one_parent_affected": (0.5, 0.5)}


def _figure_6(total: float) -> tuple[float, str, float, float]:
    return next(band for band in FIGURE_6 if total >= band[0])


def _half_up(value: float) -> float:
    """Round to 0.1, half up (decision OPEN-10); the epsilon absorbs float noise."""
    return math.floor(value * 10 + 0.5 + 1e-9) / 10


def _whole(value: Any) -> int | None:
    n = _number(value)
    return int(n) if n is not None and n >= 0 and n % 1 == 0 else None


def _estimate(row: dict[str, Any]) -> tuple[float | None, str, str | None]:
    """(eLOD, how it was computed, why the family is excluded) at theta = 0 (pp.28-32)."""
    formula, inheritance = row.get("lod_formula"), row.get("inheritance")
    if formula == "adjusted":  # an expert's formal LOD; no size minimum (decision 1)
        lod = _number(row.get("adjusted_lod"))
        if lod is None or lod < 0:
            return None, "", "adjusted LOD must be a number >= 0 (SOP v11 p.30)"
        if _blank(row.get("explanation")):
            return (
                lod,
                "adjusted",
                "an adjusted LOD needs notes explaining it (SOP v11 p.30)",
            )
        return lod, "adjusted", None
    if formula == "ad_xl":
        if inheritance not in ("AD", "XL"):
            return (
                None,
                "",
                "the ad_xl formula needs AD or XL inheritance (SOP v11 p.30)",
            )
        n = _whole(row.get("segregations_counted"))
        if n is None:
            return None, "", "segregations_counted must be a whole number >= 0"
        why = None if n >= 4 else "AD/XL eLOD needs >= 4 segregations (SOP v11 p.28)"
        return n * LOG2, f"from {n} segregations", why
    if formula in AR_BASES:
        return _ar_estimate(row, formula, inheritance)
    reason = "LOD formula must be ad_xl, ar_classic, ar_one_parent_affected or adjusted"
    return None, "", f"{reason} (SOP v11 p.30)"


def _ar_estimate(
    row: dict[str, Any], formula: str, inheritance: Any
) -> tuple[float | None, str, str | None]:
    """AR eLOD (Figure 5 p.31; one parent affected: Harel 2017, p.31)."""
    if inheritance != "AR":
        return (
            None,
            "",
            f"the {formula} formula needs AR inheritance (SOP v11 p.31)",
        )
    a, u = _whole(row.get("affected_count")), _whole(row.get("unaffected_count"))
    if not a or u is None:
        return (
            None,
            "",
            "affected_count >= 1 and unaffected_count must be whole numbers",
        )
    affected, unaffected = AR_BASES[formula]
    lod = -((a - 1) * math.log10(affected) + u * math.log10(unaffected))
    kind = "classic" if formula == "ar_classic" else "one parent affected"
    how = f"from {a} affected, {u} unaffected (AR {kind})"
    if a < 3:
        why = "AR eLOD needs >= 3 affected individuals including the proband"
    elif row.get("genotypes_complete") is not True:
        why = "AR eLOD needs genotypes for every counted individual"
    elif row.get("compound_het") is True and row.get("in_trans_shown") is not True:
        why = "compound heterozygous variants not shown to be in trans"
    else:
        return lod, how, None
    return lod, how, f"{why} (SOP v11 p.28)"


def _family(
    row: dict[str, Any], asserted: bool
) -> tuple[float | None, str, str | None]:
    """(LOD, how, exclusion reason): a published LOD stands as entered (p.28, decision 1)."""
    source = row.get("lod_source")
    if source == "published":
        lod, how = _number(row.get("published_lod")), ""
        why = (
            None
            if lod is not None and lod >= 0
            else "published LOD must be a number >= 0"
        )
        if why is None and row.get("published_lod_disputed") is True:
            why = "published LOD disputed; discuss with the expert reviewers"
        why = why and f"{why} (SOP v11 p.28)"
    elif source == "estimated":
        lod, how, why = _estimate(row)
        if not asserted:  # decision 2: asserted once per curation
            why = (
                "eLOD preconditions (rare, highly penetrant disorder; phenocopies rare) "
                "not asserted (SOP v11 p.28)"
            )
    else:
        return None, "", "LOD source must be published or estimated (SOP v11 p.28)"
    if why is None and row.get("unexplained_non_segregation") is True:
        why = "unexplained non-segregation (SOP v11 p.28)"
    if why is None and row.get("sequencing_method") not in METHODS:
        why = "sequencing method must be candidate_gene or comprehensive (SOP v11 p.33)"
    if why is None and row.get("scored") is False:
        why = "not scored by the curator (Score? unchecked, SOP v11 p.35)"
    return lod, how, why


def _rationale(row: dict[str, Any], i: int, family: dict[str, Any], how: str) -> str:
    pmid = str(row.get("pmid") or "").strip()
    head = f"{row.get('family_label') or f'Family {i + 1}'} "
    head += f"(PMID {pmid})" if pmid else "(no PMID)"
    kind = "pLOD" if row.get("lod_source") == "published" else "eLOD"
    lod = family["lod"]
    shown = f"{kind} {lod:.2f}" if lod is not None else f"{kind} n/a"
    shown += f" {how}" if how else ""
    method = METHODS.get(str(row.get("sequencing_method")), "method not given")
    status = {
        "included": "included",
        "excluded": f"excluded: {family.get('why')}",
        "omitted_lower": "omitted: lower-quality candidate evidence (SOP v11 p.35)",
    }[family["status"]]
    inheritance = row.get("inheritance") or "inheritance not given"
    return f"{head}: {inheritance}, {shown}, {method}; {status}"


def _override(assessment: dict[str, Any]) -> dict[str, Any] | None:
    """The curator's override (decision 11): needs a rationale and 0-3 points."""
    raw = assessment.get("override_points")
    if _blank(raw):
        return None
    points, rationale = _number(raw), assessment.get("override_rationale")
    if _blank(rationale):
        return {"points": raw, "applied": False, "reason": "needs override_rationale"}
    if points is None or not 0 <= points <= SEGREGATION_MAX:
        return {"points": raw, "applied": False, "reason": "points must be 0-3"}
    return {"points": points, "applied": True, "rationale": str(rationale)}


def _segregation_points(
    path: str,
    type_def: dict[str, Any],
    data: Any,
    excluded: list[Any],
    applied: list[Any],
) -> list[float]:
    """One item: Figure 6 over the summed LOD of the eligible families, the mixed-method
    formula (p.34) or the comprehensive families alone if that scores more (p.35)."""
    assessment = _at(data, type_def.get("assessment", ""))
    assessment = assessment if isinstance(assessment, dict) else {}
    asserted = all(
        assessment.get(key) is True
        for key in ("disorder_rare_highly_penetrant", "phenocopies_rare")
    )
    sums = dict.fromkeys(METHODS, 0.0)
    families, notes = [], []
    for i, row in indexed(_at(data, type_def["path"])):
        if not has_content({k: v for k, v in row.items() if k not in ("id", "scored")}):
            continue  # an untouched form row
        lod, how, why = _family(row, asserted)
        if why is None and (cite := uncited(row, False)):
            excluded.append({"path": f"{path}[{i}]", **cite})
            why = "no PMID (citation policy)"
        method = row.get("sequencing_method")
        if why is None and lod is not None:
            sums[str(method)] += lod
        status = "included" if why is None else "excluded"
        families.append({"index": i, "lod": lod, "lod_source": row.get("lod_source")})
        families[-1] |= {"method": method, "status": status, "why": why}
        notes.append((row, i, how))
    override = _override(assessment)
    if not families and override is None:
        return []
    a, b = sums["candidate_gene"], sums["comprehensive"]
    total = a + b
    _, band, c, d = _figure_6(total)
    formula = _half_up((a * c + b * d) / total) if total > 0 else 0.0
    comprehensive_only = _figure_6(b)[3]
    points = max(formula, comprehensive_only)
    for family, (row, i, how) in zip(families, notes, strict=True):
        if comprehensive_only > formula and family["method"] == "candidate_gene":
            family["status"] = "omitted_lower" if family["why"] is None else "excluded"
        family["rationale"] = _rationale(row, i, family, how)
        del family["why"]
    entry: dict[str, Any] = {"path": path, "rule": "segregation_sop11"}
    entry |= {"families": families, "sum_candidate": a, "sum_comprehensive": b}
    entry |= {"total": total, "band": band, "C": c, "D": d}
    entry |= {
        "formula_points": formula,
        "comprehensive_only_points": comprehensive_only,
    }
    entry |= {"points": points, "max": SEGREGATION_MAX}
    if override is not None:
        entry |= {"computed_points": points, "override": override}
        points = override["points"] if override["applied"] else points
        entry["points"] = points
    applied.append(entry)
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
    variants: dict[str, list[float]],
    applied: list[Any],
) -> list[float]:
    """Entered rows' points; rows outside the type's range or non-finite are flagged and
    count nothing (#278), never clamped. Rows with points but no citation count nothing and are listed in ``excluded``.
    With ``group_by``, rows sharing a non-blank value score at most ``group_cap`` together (#557).
    Counted case-row and grouped points add up in ``variants`` by normalised variant
    (the row's variant field, whatever ``group_by`` names), after the group cap (#559 hotspot)."""
    if type_def.get("rule") == "step":
        return _step_points(path, type_def, data, flags, excluded, applied)
    limits = type_def.get("range")
    group_by = type_def.get("group_by")
    names = {_norm(k): str(v) for k, v in (type_def.get("group_values") or {}).items()}
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
            group, typed = _group(row, group_by, names)
            if group:
                groups.setdefault(group, (typed, []))[1].append(len(points))
            points.append(value)
            variant = "variant_1" if "variant_1" in row else "variant"
            keys.append(_norm(row.get(variant)))
    scored = [value > 0 for value in points]  # before the cap: recurrence counts rows
    if groups:
        _cap_groups(path, type_def["group_cap"], groups, points, capped)
    _count_variants(type_def, keys, points, scored, variants)
    return points


def _count_variants(
    type_def: dict[str, Any],
    keys: list[str],
    points: list[float],
    scored: list[bool],
    variants: dict[str, list[float]],
) -> None:
    """Case rows and grouped rows (#557) feed the hotspot flag: per variant its capped
    points and its scoring rows."""
    grouped = type_def.get("group_by") and not type_def.get("group_values")
    if type_def.get("rule") == "case_row" or grouped:
        for key, value, row in zip(keys, points, scored, strict=True):
            total = variants.setdefault(key, [0.0, 0.0])
            total[0], total[1] = total[0] + value, total[1] + row


def _group(row: dict[str, Any], group_by: Any, names: Any) -> tuple[str, str]:
    """(key, label as typed) of the row's group; blank when it has none."""
    by = [group_by] if isinstance(group_by, str) else group_by or []
    if not by or not _norm(row.get(by[0])):
        return "", ""
    group = "|".join(_norm(row.get(f)) for f in by)
    typed = " | ".join(str(row.get(f) or "") for f in by)
    return (names.get(group, ""),) * 2 if names else (group, typed)


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
    flat: dict[str, Any],
    rules: dict[str, ItemRule],
    legacy: LegacyRule | None,
    flags: list[Any],
    excluded: list[Any],
    capped: list[Any],
    variants: dict[str, list[float]],
    applied: list[Any],
) -> dict[str, dict[str, list[float]]]:
    """{category key: {type path: [item points]}} for one section's evidence; ``data``
    is ``flat`` (the whole evidence) when the section key holds nothing."""
    if isinstance(data, list) and legacy is not None:
        by_category = legacy(section["key"], data, flags, excluded)
        return {
            c["key"]: {"legacy": by_category.get(c["key"], [])}
            for c in section["categories"]
        }
    out: dict[str, dict[str, list[float]]] = {}
    base = f"{section['key']}." if data is not flat else ""
    for category in section["categories"]:
        out[category["key"]] = {}
        for type_def in category["types"]:
            rule = rules.get(type_def.get("rule", ""), default_points)
            path = f"{base}{type_def['path']}"
            out[category["key"]][type_def["path"]] = (
                _segregation_points(path, type_def, data, excluded, applied)
                if type_def.get("rule") == "segregation_sop11"
                else _type_points(
                    path,
                    type_def,
                    data,
                    rule,
                    flags,
                    excluded,
                    capped,
                    variants,
                    applied,
                )
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
    model, variant_points, variant_rows}."""
    sections = []
    flags: list[Any] = []
    excluded: list[Any] = []
    capped: list[Any] = []
    variants: dict[str, list[float]] = {}
    applied: list[Any] = []
    if model.get("blank_points_default"):
        rules = {"": blank_default_points, **(rules or {})}
    for section in model["sections"]:
        data = evidence.get(section["key"])
        points = _section_points(
            section,
            evidence if data is None else data,
            evidence,
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
        "variant_points": {k: v[0] for k, v in variants.items()},
        "variant_rows": {k: int(v[1]) for k, v in variants.items()},
    }
