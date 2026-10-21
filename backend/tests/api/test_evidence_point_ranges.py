"""Evidence points are range-checked on save and submit (monkey test: 99 saved for a 0-3 item)."""

from uuid import uuid4

from app.models.models import CurationSchema
from app.scoring.point_limits import point_range_errors

BAD = {
    "genetic_evidence": {
        "case_level": {
            "autosomal_dominant": {
                "predicted_or_proven_null": [{"proband_counted_points": 99}]
            }
        }
    }
}
GOOD = {
    "genetic_evidence": {
        "case_level": {
            "autosomal_dominant": {
                "predicted_or_proven_null": [{"proband_counted_points": 3}]
            }
        },
        "segregation": [{"points": 2.5}],
    },
    "experimental_evidence": {"function": {"expression": [{"points": 0}]}},
}


def test_point_range_errors_name_the_item_and_limit() -> None:
    assert point_range_errors(GOOD) == []
    (error,) = point_range_errors(BAD)
    assert "predicted_or_proven_null[0]" in error and "0 and 3" in error
    assert point_range_errors({"segregation": [{"points": -1}]})
    assert point_range_errors({"segregation": [{"points": "abc"}]})
    assert (
        point_range_errors({"segregation": [{"points": None}, {"points": ""}, "x"]})
        == []
    )


def _engine(db_session, pair, engine: str) -> None:
    schema = CurationSchema(
        id=uuid4(),
        name=f"S-{engine}",
        version="1.0",
        schema_type="curation",
        field_definitions={},
        validation_rules={},
        workflow_states={"states": [], "transitions": {}},
        ui_configuration={},
        scoring_configuration={"engine": engine},
        is_active=True,
        schema_hash=uuid4().hex,
    )
    db_session.add(schema)
    db_session.flush()
    pair.curation_schema_id = schema.id
    db_session.commit()


def _put(client, token, curation, evidence):
    return client.put(
        f"/api/v1/curations/{curation.id}",
        json={"evidence_data": evidence, "lock_version": curation.lock_version},
        headers={"Authorization": f"Bearer {token}"},
    )


def test_clingen_save_rejects_out_of_range_points(
    client, admin_token, db_session, test_curation, test_workflow_pair
) -> None:
    _engine(db_session, test_workflow_pair, "clingen_sop_v11")
    bad = _put(client, admin_token, test_curation, BAD)
    assert bad.status_code == 422
    assert "between 0 and 3" in bad.text
    assert _put(client, admin_token, test_curation, GOOD).status_code == 200


def test_other_engines_are_not_capped(
    client, admin_token, db_session, test_curation, test_workflow_pair
) -> None:
    custom = {
        "expression": [{"points": 5}],
        "experimental": {"expression": [{"points": 5}]},
    }
    # no curation schema at all, GenCC, custom: ClinGen caps do not apply
    assert _put(client, admin_token, test_curation, custom).status_code == 200
    for engine in ("gencc", "custom"):
        _engine(db_session, test_workflow_pair, engine)
        db_session.refresh(test_curation)
        assert _put(client, admin_token, test_curation, custom).status_code == 200


def test_draft_save_is_not_validated(
    client, admin_token, db_session, test_curation, test_workflow_pair
) -> None:
    """Drafts hold partial work; ranges are enforced on save and submit."""
    _engine(db_session, test_workflow_pair, "clingen_sop_v11")
    r = client.patch(
        f"/api/v1/curations/{test_curation.id}/draft",
        json={"evidence_data": BAD},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200, r.text


def test_clingen_submit_rejects_stored_out_of_range_points(
    client, admin_token, db_session, test_curation, test_workflow_pair
) -> None:
    _engine(db_session, test_workflow_pair, "clingen_sop_v11")
    test_curation.evidence_data = BAD  # e.g. saved through /draft
    db_session.commit()
    r = client.post(
        f"/api/v1/curations/{test_curation.id}/submit",
        json={"lock_version": test_curation.lock_version},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 422
    assert "between 0 and 3" in r.text
