"""Audited correction of a curation's disease entity by a scope admin (#453)."""

from typing import Annotated

from pydantic import AfterValidator, BaseModel, StringConstraints

from app.schemas.curation import RelationshipType


def _at_least(n: int) -> AfterValidator:
    """min_length after trimming; pydantic's message counted the padding (monkey L5)."""

    def check(value: str) -> str:
        if len(value) < n:
            raise ValueError(f"{len(value)} characters after trimming, min {n}")
        return value

    return AfterValidator(check)


Trimmed = StringConstraints(strip_whitespace=True)
Text = Annotated[str, Trimmed, _at_least(1)]


class DiseaseCorrection(BaseModel):
    """The disease entity the record should name, and why it is corrected."""

    disease_name: Text
    mondo_id: Annotated[
        str, StringConstraints(strip_whitespace=True, pattern=r"^MONDO:\d{7}$")
    ]
    mode_of_inheritance: Text
    relationship_type: RelationshipType | None = None
    reason: Annotated[str, Trimmed, _at_least(3)]
    lock_version: int
