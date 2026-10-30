"""Audited correction of a curation's disease entity by a scope admin (#453)."""

from typing import Annotated

from pydantic import BaseModel, StringConstraints

from app.schemas.curation import RelationshipType

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class DiseaseCorrection(BaseModel):
    """The disease entity the record should name, and why it is corrected."""

    disease_name: Text
    mondo_id: Annotated[
        str, StringConstraints(strip_whitespace=True, pattern=r"^MONDO:\d{7}$")
    ]
    mode_of_inheritance: Text
    relationship_type: RelationshipType | None = None
    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3)]
    lock_version: int
