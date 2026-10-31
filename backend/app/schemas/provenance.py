# ruff: noqa: N815 (VA-Spec 1.0 field names are camelCase)
"""Provenance in the export (#593), in GA4GH VA-Spec 1.0 field names.

Contribution {contributor: Agent, activityType, date}; activityType is a ClinGen SEPIO
contributory role. A software agent (an AI writing through MCP) carries actedOnBehalfOf,
the person whose token it used (W3C PROV-O). Shared with the ClinGen adoption export.
"""

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

Role = Literal["curator", "assessor", "approver", "interpreter", "publisher"]
# ClinGen contributory role value set
SEPIO_CODES: dict[str, str] = {
    "curator": "SEPIO:0000156",
    "assessor": "SEPIO:0000154",
    "approver": "SEPIO:0000155",
    "interpreter": "SEPIO:0000331",
    "publisher": "SEPIO-CG:97010",
}


class Coding(BaseModel):
    system: str = Field("SEPIO", description="Code system")
    code: str = Field(..., description="SEPIO or SEPIO-CG code of the role")


class ActivityType(BaseModel):
    name: Role = Field(..., description="SEPIO contributory role")
    primaryCoding: Coding


class Extension(BaseModel):
    name: str
    value: Any


class Agent(BaseModel):
    """VA-Spec Agent: a person, an organization or software (an AI model)."""

    name: str | None = Field(None, description="Person's name, or the model")
    agentType: Literal["person", "organization", "software"]
    id: str | None = None
    description: str | None = Field(None, description="Software: the agent (client)")
    extensions: list[Extension] | None = Field(
        None, description="Software: tools_used, as the client reported them"
    )


class Contribution(BaseModel):
    """VA-Spec Contribution."""

    contributor: Agent
    activityType: ActivityType
    date: datetime | None = Field(
        None, description="ISO 8601 date-time, like the other export timestamps"
    )
    actedOnBehalfOf: Agent | None = Field(
        None, description="PROV-O: the person a software agent acted for"
    )

    @field_validator("date")
    @classmethod
    def _utc(cls, value: datetime | None) -> datetime | None:
        """A bare date (ClinGen's classified date) is UTC midnight and an offset converts
        to UTC, so every date is Z."""
        if value is None:
            return None
        return value.astimezone(UTC) if value.tzinfo else value.replace(tzinfo=UTC)


def contribution(role: Role, contributor: Agent, date: Any, **kw: Any) -> Contribution:
    return Contribution(
        contributor=contributor,
        activityType=ActivityType(
            name=role, primaryCoding=Coding(code=SEPIO_CODES[role])
        ),
        date=date,
        **kw,
    )


class ExportSource(BaseModel):
    """VA-Spec Document, plus the GeneFoundry provenance of the record."""

    documentType: str = Field(
        ...,
        description="Source kind: pmid, doi, clinvar, clingen_allele, "
        "clingen_validity, url or database",
    )
    id: str | None = Field(None, description="Identifier as recorded")
    title: str | None = None
    urls: list[str] = Field(default_factory=list)
    pmid: str | None = None
    doi: str | None = None
    citation: str | None = Field(None, description="recommended_citation, verbatim")
    retrieved_at: str | None = None
    tool: str | None = Field(None, description="e.g. genefoundry:clinvar_get_variant")
    record_sha256: str | None = None


class EvidenceLine(BaseModel):
    """One evidence table row (VA-Spec EvidenceLine): its sources and contributions."""

    path: str = Field(..., description="Row path in evidence, e.g. genetic.probands[0]")
    row_id: str | None = None
    directionOfEvidenceProvided: Literal["supports", "disputes", "neutral"] | None = (
        None
    )
    sources: list[ExportSource] = Field(
        default_factory=list, description="VA-Spec reportedIn: the row's documents"
    )
    contributions: list[Contribution] = Field(default_factory=list)
