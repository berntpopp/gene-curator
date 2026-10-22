"""Opt-in explicit segregation scoring for a pinned successor model.

SOP v11 pp.28-35 requires pedigree eligibility, sequencing methods and aggregate LOD.
The current evidence schema cannot represent those inputs: never infer points here.
"""

from typing import Any

from .evidence_items import rows


def explicit_points(type_def: dict[str, Any], item: dict[str, Any]) -> float:
    return float(item.get(type_def.get("points_key", "points")) or 0)


def explicit_legacy_segregation(model: dict[str, Any]) -> dict[str, Any] | None:
    """Only the pinned type can opt legacy-shaped evidence into explicit scoring."""
    for section in model["sections"]:
        if section["key"] != "genetic_evidence":
            continue
        for category in section["categories"]:
            types = category["types"]
            if (
                category["key"] == "segregation"
                and len(types) == 1
                and types[0].get("rule") == "explicit_points"
            ):
                return dict(types[0])
    return None


def missing_score_warnings(
    model: dict[str, Any], evidence: dict[str, Any]
) -> list[str]:
    warnings = []
    for section in model["sections"]:
        data = evidence.get(section["key"])
        for category in section["categories"]:
            for type_def in category["types"]:
                if type_def.get("rule") != "explicit_points":
                    continue
                if isinstance(data, list):
                    entries = [
                        (i, row)
                        for i, row in enumerate(rows(data))
                        if row.get("evidence_category") == category["key"]
                    ]
                    path = section["key"]
                else:
                    value = data
                    for key in type_def["path"].split("."):
                        value = value.get(key) if isinstance(value, dict) else None
                    entries = list(enumerate(rows(value)))
                    path = f"{section['key']}.{type_def['path']}"
                key = type_def.get("points_key", "points")
                for index, row in entries:
                    has_lod = any(
                        row.get(k) not in (None, "", 0)
                        for k in ("lod_score", "segregations_counted", "family_count")
                    )
                    if row.get(key) in (None, "") and has_lod:
                        warnings.append(
                            f"{path}[{index}].{key}: Enter segregation points after assessing "
                            "the included families and sequencing methods; LOD and counts "
                            "are not automatically converted to points."
                        )
    return warnings
