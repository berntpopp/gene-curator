"""Evidence points are range-checked on save and submit (monkey test: 99 saved for a 0-3 item)."""

from fastapi.testclient import TestClient

from app.models.models import CurationNew
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


def test_save_rejects_out_of_range_points(
    client: TestClient, admin_token: str, test_curation: CurationNew
) -> None:
    headers = {"Authorization": f"Bearer {admin_token}"}
    url = f"/api/v1/curations/{test_curation.id}"
    bad = client.put(
        url,
        json={"evidence_data": BAD, "lock_version": test_curation.lock_version},
        headers=headers,
    )
    assert bad.status_code == 422
    assert "between 0 and 3" in bad.text
    ok = client.put(
        url,
        json={"evidence_data": GOOD, "lock_version": test_curation.lock_version},
        headers=headers,
    )
    assert ok.status_code == 200


def test_submit_rejects_stored_out_of_range_points(
    client: TestClient, admin_token: str, db_session, test_curation: CurationNew
) -> None:
    test_curation.evidence_data = BAD  # legacy row saved before the check existed
    db_session.commit()
    r = client.post(
        f"/api/v1/curations/{test_curation.id}/submit",
        json={"lock_version": test_curation.lock_version},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 422
    assert "between 0 and 3" in r.text
