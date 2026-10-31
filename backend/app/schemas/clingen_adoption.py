"""Adopting ClinGen gene-disease validity classifications (#105).

The record fields are GeneFoundry `clingen_get_gene_validity` output, stored verbatim:
Gene Curator never fetches the ClinGen record, it checks the row against the entity.
"""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

_ID = Field(..., min_length=1, max_length=500)


class ClinGenRecord(BaseModel):
    """One ClinGen assertion as GeneFoundry returns it (perm_id -> cggv_id,
    raw_sha256 -> record_sha256, recommended_citation -> citation)."""

    source: Literal["clingen"] = "clingen"
    cggv_id: str = Field(..., pattern=r"^CGGV:assertion_\S+$", max_length=200)
    permalink: str = Field(..., pattern=r"^https://\S+$", max_length=500)
    classification: str = _ID
    moi: str = _ID
    mondo: str = Field(..., pattern=r"^MONDO[:_]\d{7}$")
    hgnc_id: str = Field(..., pattern=r"^HGNC:\d+$")
    expert_panel: str = _ID
    classified_date: str = _ID
    retrieved_at: str = _ID
    record_sha256: str = Field(..., pattern=r"^[0-9a-f]{64}$")
    citation: str = Field(..., min_length=1, max_length=2000)


class ClinGenAdoptionRow(BaseModel):
    """The entity to curate (as create_curation needs it) and the ClinGen record."""

    gene_id: UUID
    scope_id: UUID
    workflow_pair_id: UUID
    mondo_id: str = Field(..., max_length=100)
    mode_of_inheritance: str = Field(..., max_length=100)
    disease_name: str | None = Field(None, max_length=500)
    clingen: ClinGenRecord


class ClinGenAdoptionRequest(BaseModel):
    rows: list[ClinGenAdoptionRow] = Field(..., min_length=1, max_length=500)


class ClinGenAdoptionItem(BaseModel):
    """What adoption did (or, on a dry run, would do) for one row."""

    row: int
    cggv_id: str
    action: Literal["create", "unchanged", "refused"] = Field(
        ...,
        description="refused: the row has errors (see errors) and nothing is written",
    )
    curation_id: UUID | None = Field(
        None, description="Empty for curations a dry run would create"
    )


class ClinGenAdoptionResult(BaseModel):
    """The plan and the validation report; nothing is written when errors is not empty."""

    dry_run: bool
    errors: list[str]
    items: list[ClinGenAdoptionItem]
