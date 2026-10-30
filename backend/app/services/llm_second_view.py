"""LLM second view (#464, #465): cited findings, engine-scored proposals, three-way diff.

Advisory only: nothing here writes a curation, a review, a score or a workflow state.
The model's proposed evidence is scored by the curation's own engine and pinned
methodology version (no separate scoring code); only scores and class are kept.
"""

import json
import re
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.llm.output import InvalidLLMOutputError
from app.models import CurationNew
from app.models.llm import LLMFinding, LLMRun, PromptTemplateVersion
from app.models.methodology import MethodologyVersion
from app.scoring.registry import engine_for

STRATEGIES = ("advocate", "skeptic")
MAX_FINDINGS = 50
MAX_TEXT = 4000
# PMID:123, a bare PMID, or a source ID such as ClinVar:12345, MONDO:0007254, HP:0001250
_PMID = re.compile(r"(?:PMID:?\s*)?(\d{1,9})", re.IGNORECASE)
_SOURCE_ID = re.compile(r"[A-Za-z][A-Za-z0-9_.-]{0,30}:[A-Za-z0-9_.:-]{1,60}")


def _citation(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if pmid := _PMID.fullmatch(text):
        return f"PMID:{pmid.group(1)}"
    return text if _SOURCE_ID.fullmatch(text) else None


def cited_findings(data: dict[str, Any]) -> list[dict[str, Any]]:
    """The output's findings that cite at least one PMID or source ID; others are dropped."""
    found = data.get("findings")
    out: list[dict[str, Any]] = []
    for item in found if isinstance(found, list) else []:
        if not isinstance(item, dict) or not isinstance(item.get("citations"), list):
            continue
        citations = [c for c in map(_citation, item["citations"]) if c]
        message = item.get("message")
        if citations and isinstance(message, str) and message.strip():
            category = item.get("category")
            out.append(
                {
                    "category": str(category or "general")[:200],
                    "message": message.strip()[:MAX_TEXT],
                    "citations": list(dict.fromkeys(citations))[:20],
                }
            )
    return out[:MAX_FINDINGS]


def proposal(
    data: dict[str, Any], config: dict[str, Any]
) -> tuple[dict[str, float] | None, str | None]:
    """Engine scores and class of the output's proposed evidence, or (None, None)."""
    evidence = data.get("proposed_evidence")
    if evidence is None:
        return None, None
    try:
        # JSON text: structured-output schemas cannot hold a free-form object
        if isinstance(evidence, str):
            evidence = json.loads(evidence)
        if not isinstance(evidence, dict):
            raise TypeError("proposed_evidence is not an object")
        result = engine_for(config).calculate_scores(evidence, config)
    except (TypeError, ValueError, KeyError, AttributeError, IndexError) as exc:
        raise InvalidLLMOutputError(
            "LLM output failed validation at: ['proposed_evidence']"
        ) from exc
    return dict(result.scores), result.verdict


# --- read model -----------------------------------------------------------------


def _latest_runs(db: Session, curation_id: UUID) -> dict[str, dict[str, Any]]:
    rows = db.execute(
        select(LLMRun, PromptTemplateVersion.version, MethodologyVersion.version)
        .outerjoin(
            PromptTemplateVersion, PromptTemplateVersion.id == LLMRun.prompt_version_id
        )
        .outerjoin(
            MethodologyVersion, MethodologyVersion.id == LLMRun.methodology_version_id
        )
        .where(LLMRun.curation_id == curation_id, LLMRun.status == "succeeded")
        .order_by(LLMRun.finished_at.desc(), LLMRun.created_at.desc())
    ).all()
    latest: dict[str, dict[str, Any]] = {}
    for run, prompt_version, methodology_version in rows:
        latest.setdefault(
            run.strategy,
            {
                "run": run,
                "prompt_version": prompt_version,
                "methodology_version": methodology_version,
            },
        )
    return latest


def _differs(row: dict[str, Any]) -> bool:
    values = {row[k] for k in ("human", *STRATEGIES) if row[k] is not None}
    return len(values) > 1


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value)


def diff_rows(curation: CurationNew, runs: dict[str, LLMRun]) -> list[dict[str, Any]]:
    """Human vs advocate vs skeptic per score key and final class; disagreements first."""
    human = curation.computed_scores or {}
    keys = sorted({k for r in runs.values() for k in (r.proposed_scores or {})})
    rows: list[dict[str, Any]] = [
        {
            "category": key,
            "human": _number(human.get(key)),
            **{
                s: _number((runs[s].proposed_scores or {}).get(key))
                if s in runs
                else None
                for s in STRATEGIES
            },
        }
        for key in keys
    ]
    rows.append(
        {
            "category": "classification",
            "human": curation.computed_verdict,
            **{s: runs[s].proposed_verdict if s in runs else None for s in STRATEGIES},
        }
    )
    for row in rows:
        row["disagree"] = _differs(row)
    return sorted(rows, key=lambda r: not r["disagree"])  # stable: order kept within


def second_view(db: Session, curation: CurationNew) -> dict[str, Any]:
    latest = _latest_runs(db, curation.id)
    runs = {s: v["run"] for s, v in latest.items()}
    findings = (
        db.scalars(
            select(LLMFinding)
            .where(LLMFinding.run_id.in_([r.id for r in runs.values()]))
            .order_by(LLMFinding.created_at, LLMFinding.category)
        ).all()
        if runs
        else []
    )
    strategy_of = {r.id: s for s, r in runs.items()}
    pending = db.scalar(
        select(LLMRun.id)
        .where(
            LLMRun.curation_id == curation.id, LLMRun.status.in_(("queued", "running"))
        )
        .limit(1)
    )
    return {
        "curation_id": curation.id,
        "pending": pending is not None,
        "runs": [
            {
                "strategy": s,
                "run_id": v["run"].id,
                "model_id": v["run"].model_id,
                "prompt_version": v["prompt_version"],
                "methodology_version": v["methodology_version"],
                "proposed_verdict": v["run"].proposed_verdict,
                "finished_at": v["run"].finished_at,
            }
            for s, v in sorted(latest.items())
        ],
        "findings": [
            {
                "id": f.id,
                "strategy": strategy_of[f.run_id],
                "category": f.category,
                "message": f.message,
                "citations": list(f.citations),
                "decision": f.decision,
                "decided_at": f.decided_at,
            }
            for f in findings
        ],
        "diff": diff_rows(curation, runs),
    }
