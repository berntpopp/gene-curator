"""Deletion must preserve precurations referenced by curations in any state."""

from unittest.mock import patch

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.api.v1.endpoints.precurations import delete_precuration
from app.models import CurationNew, CurationStatus, PrecurationNew, UserNew

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "linked_status",
    [CurationStatus.DRAFT, CurationStatus.ACTIVE, CurationStatus.ARCHIVED],
)
def test_linked_curation_prevents_archiving_direct(
    db_session: Session,
    test_precuration: PrecurationNew,
    test_curation: CurationNew,
    test_user_curator: UserNew,
    linked_status: CurationStatus,
):
    test_curation.precuration_id = test_precuration.id
    test_curation.status = linked_status
    db_session.commit()
    with (
        patch("app.api.v1.endpoints.precurations.set_rls_context"),
        pytest.raises(HTTPException) as error,
    ):
        delete_precuration(
            precuration_id=test_precuration.id,
            db=db_session,
            current_user=test_user_curator,
        )
    assert error.value.status_code == 409
    assert (
        error.value.detail
        == "Cannot delete precuration: 1 linked curation(s) exist. Remove or reassign them first."
    )
    db_session.refresh(test_precuration)
    db_session.refresh(test_curation)
    assert test_precuration.status == CurationStatus.DRAFT
    assert test_curation.precuration_id == test_precuration.id
