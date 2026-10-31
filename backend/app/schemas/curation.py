"""
Pydantic V2 schemas for curation API operations.
Follows existing patterns from gene_assignment.py (InDBBase pattern).
"""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import CurationStatus, WorkflowStage
from app.schemas.review_comment import CurationDiff
from app.schemas.workflow_engine import AssignedReviewer, WorkflowStateInfo

# ========================================
# BASE SCHEMAS (DRY - shared fields)
# ========================================


class CurationBase(BaseModel):
    """Base schema with common curation fields."""

    gene_id: UUID = Field(..., description="Gene UUID")
    scope_id: UUID = Field(..., description="Scope UUID")
    workflow_pair_id: UUID = Field(..., description="Workflow pair UUID")
    precuration_id: UUID | None = Field(None, description="Parent precuration UUID")
    evidence_data: dict[str, Any] = Field(
        default_factory=dict, description="Schema-agnostic evidence"
    )


# ========================================
# REQUEST SCHEMAS
# ========================================


MERGE_DESCRIPTION = (
    "false or omitted: evidence_data replaces the stored evidence_data entirely. true: "
    "evidence_data is an RFC 7396 JSON merge patch on the stored evidence_data (objects "
    "merge, null deletes a key). Arrays are replaced whole: send every row of an "
    "array you touch, or the rows you leave out are dropped (the save warns). A stale "
    "lock_version still 409s."
)


class CuratorClassificationIn(BaseModel):
    """The curator's proposed classification (#533); omitted keeps it, null clears it."""

    curator_classification: str | None = Field(None, max_length=100)
    curator_classification_rationale: str | None = Field(None, max_length=5000)

    @field_validator("curator_classification", "curator_classification_rationale")
    @classmethod
    def _blank_is_none(cls, v: str | None) -> str | None:
        return (v or "").strip() or None


def class_key(value: str) -> str:
    """'Strong', ' strong ' or 'No Known Disease Relationship' as a class key (#533).
    crud.curator_classification.class_key_sql is the same rule in SQL: keep them equal."""
    key = value.strip().lower().replace(" ", "_").replace("-", "_")
    return "no_known" if key.startswith("no_known") else key


class CurationCreate(CurationBase, CuratorClassificationIn):
    """Schema for creating a new curation; a re-curation carries the curator's call."""


CLASSIFICATION_KEYS = {
    "curator_classification",
    "curator_classification_rationale",
}


class CurationUpdate(CuratorClassificationIn):
    """Schema for updating an existing curation."""

    evidence_data: dict[str, Any] | None = Field(
        None, description="Updated evidence data"
    )
    lock_version: int = Field(..., description="Optimistic locking version (required)")
    merge: bool | None = Field(None, description=MERGE_DESCRIPTION)

    model_config = ConfigDict(extra="forbid")


class CurationDraftSave(CuratorClassificationIn):
    """Schema for saving a curation as draft."""

    evidence_data: dict[str, Any] = Field(..., description="Draft evidence data")
    lock_version: int = Field(..., description="Optimistic locking version (required)")
    merge: bool | None = Field(None, description=MERGE_DESCRIPTION)


class CurationSubmit(BaseModel):
    """Schema for submitting a curation for review."""

    notes: str | None = Field(None, max_length=1000, description="Submission notes")
    lock_version: int = Field(..., description="Lock version for optimistic locking")
    reviewer_id: UUID | None = Field(
        None,
        description="Also route it to this reviewer, in the same transaction (assign-reviewer rules)",
    )
    reviewer_email: str | None = Field(
        None,
        max_length=255,
        description="Or the reviewer's email (a reviewer of the scope)",
    )


# ========================================
# DATABASE SCHEMAS (InDBBase pattern - matches gene_assignment.py)
# ========================================


class CurationInDBBase(CurationBase):
    """Base schema with database fields."""

    id: UUID
    status: CurationStatus
    workflow_stage: WorkflowStage
    is_draft: bool

    # Computed results
    computed_scores: dict[str, Any]
    computed_verdict: str | None
    computed_summary: str | None
    curator_classification: str | None = None
    curator_classification_rationale: str | None = None
    final_classification: str | None = Field(
        None, description="curator_classification if set, else computed_verdict"
    )
    clingen_adoption: dict[str, Any] | None = Field(
        None, description="ClinGen record this curation adopted (#105), else null"
    )

    # Optimistic locking
    lock_version: int

    # Methodology version pinned at creation (None only without the 042 trigger, e.g. SQLite)
    methodology_version_id: UUID | None = None

    # Timestamps
    created_at: datetime
    updated_at: datetime
    submitted_at: datetime | None
    approved_at: datetime | None
    auto_saved_at: datetime | None

    # User references
    created_by: UUID | None
    updated_by: UUID | None
    submitted_by: UUID | None
    approved_by: UUID | None

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


# ========================================
# RESPONSE SCHEMAS
# ========================================


class Curation(CurationInDBBase):
    """Full curation response schema."""

    curation_schema_id: UUID | None = Field(
        None,
        description="Field contract: get_curation_schema(curation_schema_id, path=)",
    )


class EvidenceWarning(BaseModel):
    """A value a draft keeps but that needs fixing before submit."""

    path: str = Field(..., description="Dotted field path in evidence_data")
    message: str


def _rows(paths: list[str], keep: int = 3) -> str:
    more = ", ..." if len(paths) > keep else ""
    return f"{len(paths)} rows: {', '.join(paths[:keep])}{more}"


def collapse(lines: list[str]) -> list[str]:
    """One "path: message" warning per message; repeats become a count and the first
    3 paths (MCP study round 6: a save listed all 15 row paths)."""
    groups: dict[str, list[str]] = {}
    for line in lines:
        path, sep, message = line.partition(": ")
        if sep and " " not in path:
            groups.setdefault(message, []).append(path)
        else:
            groups.setdefault(line, [])
    out = []
    for message, paths in groups.items():
        if not paths:
            out.append(message)
        elif len(paths) == 1:
            out.append(f"{paths[0]}: {message}")
        else:
            out.append(f"{message} ({_rows(paths)})")
    return out


def collapse_warnings(warnings: list["EvidenceWarning"]) -> list["EvidenceWarning"]:
    """The same for {path, message} warnings: path names the count and first paths."""
    groups: dict[str, list[str]] = {}
    for w in warnings:
        groups.setdefault(w.message, []).append(w.path)
    return [
        EvidenceWarning(path=paths[0] if len(paths) == 1 else _rows(paths), message=m)
        for m, paths in groups.items()
    ]


class CurationDraftResult(Curation):
    """Saved draft plus warnings: malformed or unknown PMIDs, MONDO, OMIM and HPO IDs."""

    warnings: list[EvidenceWarning] = []


_DISEASE_KEYS = ("disease_name", "mondo_id", "mode_of_inheritance")


def _pick(source: dict[str, Any] | None, key: str) -> Any:
    source = source or {}
    nested = source.get("entity_definition")
    return source.get(key) or (nested.get(key) if isinstance(nested, dict) else None)


def disease_fields(
    evidence: dict[str, Any] | None, precuration: dict[str, Any] | None
) -> dict[str, Any]:
    """Disease fields from the flat or nested (`entity_definition.*`) shape; evidence wins."""
    return {k: _pick(evidence, k) or _pick(precuration, k) for k in _DISEASE_KEYS}


RelationshipType = Literal["mendelian", "susceptibility"]
SUSCEPTIBILITY_SUFFIX = "|SUSCEPTIBILITY"


def relationship_of_key(entity_key: str | None) -> RelationshipType:
    """A curation's relationship type: the one its entity_key names (#539)."""
    return (
        "susceptibility"
        if (entity_key or "").endswith(SUSCEPTIBILITY_SUFFIX)
        else "mendelian"
    )


def relationship_type(
    evidence: dict[str, Any] | None, precuration: dict[str, Any] | None
) -> RelationshipType:
    """mendelian unless the evidence (else the precuration) says susceptibility (#539);
    the same rule as the entity_key suffix in ENTITY_KEY_SQL."""
    raw = _pick(evidence, "relationship_type") or _pick(
        precuration, "relationship_type"
    )
    susceptibility = str(raw or "").strip().lower() == "susceptibility"
    return "susceptibility" if susceptibility else "mendelian"


class ClassificationChoice(BaseModel):
    key: str = Field(..., description="Class key, as curator_classification stores it")
    label: str


class CurationDetail(CurationInDBBase):
    """Detailed curation response with expanded relations."""

    # Expanded from gene relationship
    gene_symbol: str | None = None
    hgnc_id: str | None = None

    # Expanded from scope relationship
    scope_name: str | None = None

    # Schemas of the workflow pair, for the schema read and field contract
    curation_schema_id: UUID | None = None
    precuration_schema_id: UUID | None = None

    # Expanded from creator relationship
    curator_name: str | None = None
    curator_id: UUID | None = None

    # Extracted from evidence_data for convenience
    disease_name: str | None = None
    mondo_id: str | None = None
    mode_of_inheritance: str | None = None
    relationship_type: RelationshipType = "mendelian"

    # User permissions for this curation (set by endpoint based on current user)
    can_edit: bool = False
    can_review: bool = False
    classification_choices: list[ClassificationChoice] = Field(
        default_factory=list,
        description="Classes a curator may choose: the schema's vocabulary or its engine's",
    )
    can_delete: bool = False
    # Open review round only: the user's approval is recorded / approvals still needed (#430)
    has_approved: bool = False
    approvals_remaining: int | None = None
    # The user corrected its disease entity (#453), so they cannot review it (R2-5)
    corrected_disease: bool = False
    assigned_reviewers: list[AssignedReviewer] = Field(
        default_factory=list, description="In review: who still has to review it"
    )

    @classmethod
    def from_orm_with_relations(cls, curation: Any) -> "CurationDetail":
        """Create instance from ORM model with loaded relationships."""
        # Base data from model
        data = {
            "id": curation.id,
            "gene_id": curation.gene_id,
            "scope_id": curation.scope_id,
            "workflow_pair_id": curation.workflow_pair_id,
            "precuration_id": curation.precuration_id,
            "evidence_data": curation.evidence_data or {},
            "status": curation.status,
            "workflow_stage": curation.workflow_stage,
            "is_draft": curation.is_draft,
            "computed_scores": curation.computed_scores or {},
            "computed_verdict": curation.computed_verdict,
            "computed_summary": curation.computed_summary,
            "curator_classification": curation.curator_classification,
            "curator_classification_rationale": curation.curator_classification_rationale,
            "final_classification": curation.final_classification,
            "clingen_adoption": curation.clingen_adoption,
            "lock_version": curation.lock_version,
            "methodology_version_id": curation.methodology_version_id,
            "created_at": curation.created_at,
            "updated_at": curation.updated_at,
            "submitted_at": curation.submitted_at,
            "approved_at": curation.approved_at,
            "auto_saved_at": curation.auto_saved_at,
            "created_by": curation.created_by,
            "updated_by": curation.updated_by,
            "submitted_by": curation.submitted_by,
            "approved_by": curation.approved_by,
        }

        # Expand gene relationship
        if hasattr(curation, "gene") and curation.gene:
            data["gene_symbol"] = curation.gene.approved_symbol
            data["hgnc_id"] = curation.gene.hgnc_id

        pair = getattr(curation, "workflow_pair", None)
        if pair is not None:
            data["curation_schema_id"] = pair.curation_schema_id
            data["precuration_schema_id"] = pair.precuration_schema_id

        # Expand scope relationship
        if hasattr(curation, "scope") and curation.scope:
            data["scope_name"] = curation.scope.name

        # Expand creator relationship
        if hasattr(curation, "creator") and curation.creator:
            data["curator_name"] = curation.creator.name or curation.creator.email
            data["curator_id"] = curation.creator.id

        # Extract from evidence_data OR precuration for convenience
        evidence: dict[str, Any] = curation.evidence_data or {}
        precuration_data: dict[str, Any] = {}
        if hasattr(curation, "precuration") and curation.precuration:
            precuration_data = curation.precuration.evidence_data or {}

        # Priority: evidence_data > precuration_data
        data.update(disease_fields(evidence, precuration_data))
        data["relationship_type"] = relationship_of_key(curation.entity_key)

        return cls(**data)


class CurationSummary(BaseModel):
    """Lightweight curation summary for list views (no evidence_data)."""

    id: UUID
    gene_id: UUID
    gene_symbol: str
    scope_id: UUID
    scope_name: str
    status: CurationStatus
    workflow_stage: WorkflowStage
    computed_verdict: str | None
    final_classification: str | None = None
    clingen_adoption: dict[str, Any] | None = None  # adopted ClinGen record (#105)
    computed_scores: dict[str, Any] | None = None
    disease_name: str | None = None
    relationship_type: RelationshipType = "mendelian"
    is_draft: bool
    created_at: datetime
    updated_at: datetime
    curator_name: str | None
    created_by: UUID | None = None  # For 4-eyes filtering in review queue
    lock_version: int = Field(..., description="Send with the next save or submit")

    model_config = ConfigDict(use_enum_values=True)


class CurationListResponse(BaseModel):
    """Paginated list response."""

    curations: list[CurationSummary]
    total: int
    skip: int
    limit: int


class CurationScoreResponse(BaseModel):
    """Score calculation response."""

    curation_id: UUID
    total_score: float
    classification: str
    genetic_score: float
    experimental_score: float
    breakdown: dict[str, Any]
    trace: dict[str, Any] | None = (
        None  # point model trace: sections > categories > types
    )
    warnings: list[str] = []  # the scorer's reviewer warnings (as on save)
    calculated_at: datetime


class CurationWriteResult(BaseModel):
    """Concise result of a save or submit; detail=true returns the full curation."""

    id: UUID
    status: CurationStatus
    workflow_stage: WorkflowStage
    lock_version: int
    total_score: float | None
    verdict: str | None
    warnings: list[str] = Field(
        default_factory=list,
        description="Scoring warnings, then bad or unknown ID warnings as 'path: message'",
    )

    model_config = ConfigDict(use_enum_values=True)

    @classmethod
    def of(cls, curation: Any) -> "CurationWriteResult":
        scores = curation.computed_scores or {}
        return cls(
            id=curation.id,
            status=curation.status,
            workflow_stage=curation.workflow_stage,
            lock_version=curation.lock_version,
            total_score=scores.get("total_score"),
            verdict=curation.computed_verdict,
            warnings=collapse(scores.get("warnings") or []),
        )


class CurationSubmitResult(CurationWriteResult):
    """Concise submit result, with the reviewer it was routed to."""

    assigned_reviewer: AssignedReviewer | None = Field(
        None, description="Submit with a reviewer: who it was routed to"
    )


def lean_scores(scores: dict[str, Any]) -> dict[str, Any]:
    """computed_scores without the trace's zero-point rows (types with no items and no
    points, then categories left empty with no points)."""
    trace = scores.get("trace")
    if not isinstance(trace, dict):
        return scores

    def lean(category: dict[str, Any]) -> dict[str, Any]:
        types = [
            t for t in category.get("types", []) if t.get("score") or t.get("items")
        ]
        return {**category, "types": types}

    sections = [
        {
            **section,
            "categories": [
                c
                for c in map(lean, section.get("categories", []))
                if c["types"] or c.get("score") or c.get("raw")
            ],
        }
        for section in trace.get("sections", [])
    ]
    return {**scores, "trace": {**trace, "sections": sections}}


class CurationConflictResponse(BaseModel):
    """409 Conflict response for optimistic locking."""

    error: str = "Concurrent modification detected"
    current_lock_version: int
    current_state: dict[str, Any]
    your_lock_version: int
    updated_by_name: str | None = Field(
        None, description="Who saved the current version"
    )
    updated_at: datetime | None = None
    changed_keys: list[str] | None = Field(
        None, description="Top-level evidence keys where your save and theirs differ"
    )


def capped(trace: Any) -> list[str]:
    """One line per section or category whose claimed points exceed its cap."""
    lines = []
    for section in (trace or {}).get("sections", []):
        for path, row in [(section["key"], section)] + [
            (f"{section['key']}.{c['key']}", c) for c in section.get("categories", [])
        ]:
            if row.get("cap") is not None and (row.get("raw") or 0) > row["cap"]:
                lines.append(
                    f"{path}: {row['raw']} points claimed, capped at {row['cap']}"
                )
    return lines


class CurationReviewRead(BaseModel):
    """Everything a reviewer checks, in one read."""

    curation: CurationDetail = Field(
        ...,
        description="Evidence and the score trace without zero-point rows; "
        "computed_scores.excluded lists rows that score nothing, with the reason; "
        "trace.out_of_range flags rows outside their range",
    )
    warnings: list[str] = Field(
        ...,
        description="Saved scoring and ID warnings, then points capped per category",
    )
    workflow: WorkflowStateInfo = Field(
        ..., description="Moves the caller may make; blocked ones with the reason"
    )
    first_submission: bool = Field(
        ..., description="No earlier version to compare: diff is null, review it whole"
    )
    diff: CurationDiff | None = Field(
        None,
        description="Evidence versus what the caller last reviewed, else the previous "
        "submission or the active curation it replaces",
    )
    previous_reviews: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Resubmission: the earlier decisions (reviewer, decision, comments)",
    )
    open_item_comments: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Resubmission: item comments from earlier rounds still open",
    )
