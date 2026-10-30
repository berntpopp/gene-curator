"""Curator and final classification (#533): stored on save, rationale required at submit
when it differs from the computed verdict, and the catalogue and export publish the final."""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.crud.curator_classification import (
    allowed_classifications,
    classification_choices,
)
from app.models.models import (
    ActiveCuration,
    CurationNew,
    CurationSchema,
    Gene,
    Scope,
    WorkflowPair,
)
from app.services.review_guards import _unexplained_override

pytestmark = pytest.mark.unit


def _h(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _detail(client: TestClient, token: str, cid: object) -> dict[str, Any]:
    r = client.get(f"/api/v1/curations/{cid}", headers=_h(token))
    assert r.status_code == 200, r.text
    return r.json()  # type: ignore[no-any-return]


def test_override_needs_a_rationale_at_submit_and_saves_keep_or_clear_it(
    client: TestClient, admin_token: str, test_curation: CurationNew
) -> None:
    url = f"/api/v1/curations/{test_curation.id}"
    r = client.put(
        url,
        json={"curator_classification": " Strong ", "lock_version": 0},
        headers=_h(admin_token),
    )
    assert r.status_code == 200, r.text
    body = _detail(client, admin_token, test_curation.id)
    assert body["curator_classification"] == "strong"  # a label is stored as its key
    assert body["final_classification"] == "strong"
    assert body["computed_verdict"] != "strong"
    lock = body["lock_version"]

    refused = client.post(
        f"{url}/submit", json={"lock_version": lock}, headers=_h(admin_token)
    )
    assert refused.status_code == 422, refused.text
    assert [e["path"] for e in refused.json()["detail"]["errors"]] == [
        "curator_classification_rationale"
    ]

    # A draft save without the keys keeps them; the rationale alone is added
    r = client.patch(
        f"{url}/draft",
        json={
            "evidence_data": test_curation.evidence_data,
            "curator_classification_rationale": "Replicated over 5 years",
            "lock_version": lock,
        },
        headers=_h(admin_token),
    )
    assert r.status_code == 200, r.text
    body = _detail(client, admin_token, test_curation.id)
    assert body["curator_classification"] == "strong"
    assert body["curator_classification_rationale"] == "Replicated over 5 years"

    listed = client.get("/api/v1/curations/", headers=_h(admin_token)).json()
    assert listed["curations"][0]["final_classification"] == "strong"

    # null clears it: the computed verdict is final again
    r = client.put(
        url,
        json={"curator_classification": None, "lock_version": body["lock_version"]},
        headers=_h(admin_token),
    )
    assert r.status_code == 200, r.text
    body = _detail(client, admin_token, test_curation.id)
    assert body["curator_classification"] is None
    assert body["final_classification"] == body["computed_verdict"]


def test_unknown_classification_is_refused_and_changes_nothing(
    client: TestClient, admin_token: str, test_curation: CurationNew
) -> None:
    r = client.put(
        f"/api/v1/curations/{test_curation.id}",
        json={"curator_classification": "Very strong", "lock_version": 0},
        headers=_h(admin_token),
    )
    assert r.status_code == 422, r.text
    [error] = r.json()["detail"]["errors"]
    assert error["path"] == "curator_classification"
    assert "no_known" in error["message"]
    body = _detail(client, admin_token, test_curation.id)
    assert (body["curator_classification"], body["lock_version"]) == (None, 0)


def test_allowed_classes_are_the_engine_verdicts_as_keys() -> None:
    model = {
        "point_model": {
            "bands": [{"class": "high", "min": 5}, {"class": "low"}],
            "overrides": [{"when": "x", "class": "contested"}, {"class": "low"}],
        }
    }
    assert allowed_classifications(model) == ["high", "low", "contested"]
    clingen = allowed_classifications({})
    assert clingen[0] == "definitive" and "no_known" in clingen
    assert (
        allowed_classifications({"engine": "qualitative_assessment"})[0]
        == "strong_association"
    )
    assert "no_known" in allowed_classifications({"engine": "gencc_based"})


def test_declared_vocabulary_comes_first_in_its_order_with_its_labels() -> None:
    """#539: the schema's classes, then any engine verdict it lacks."""
    config = {
        "classifications": [
            {
                "key": "Uncertain_Risk",
                "label": "Uncertain",
                "order": 3,
                "tone": "limited",
            },
            {
                "key": "established_risk",
                "label": "Established",
                "order": 1,
                "tone": "strong",
            },
            {"label": "no key"},
        ],
        "point_model": {"bands": [{"class": "established_risk"}, {"class": "other"}]},
    }
    assert classification_choices(config) == [
        {"key": "established_risk", "label": "Established"},
        {"key": "uncertain_risk", "label": "Uncertain"},
        {"key": "other", "label": "other"},
    ]
    qualitative = classification_choices({"engine": "qualitative_assessment"})
    assert qualitative[0] == {
        "key": "strong_association",
        "label": "Strong Association",
    }


def test_curation_detail_lists_the_choices(
    client: TestClient, admin_token: str, test_curation: CurationNew
) -> None:
    choices = _detail(client, admin_token, test_curation.id)["classification_choices"]
    keys = [c["key"] for c in choices]
    assert keys[0] == "definitive" and "no_known" in keys


def test_qualitative_curator_picks_the_agreeing_key_without_rationale(
    client: TestClient,
    admin_token: str,
    db_session: Session,
    test_curation: CurationNew,
) -> None:
    schema = CurationSchema(
        id=uuid4(),
        name="Qualitative",
        version="1",
        schema_type="curation",
        field_definitions={},
        workflow_states={},
        ui_configuration={},
        scoring_configuration={"engine": "qualitative_assessment"},
        schema_hash=uuid4().hex * 2,
    )
    db_session.add(schema)
    db_session.flush()
    pair = db_session.get(WorkflowPair, test_curation.workflow_pair_id)
    assert pair is not None
    pair.curation_schema_id = schema.id
    db_session.commit()
    r = client.put(
        f"/api/v1/curations/{test_curation.id}",
        json={"curator_classification": "Strong Association", "lock_version": 0},
        headers=_h(admin_token),
    )
    assert r.status_code == 200, r.text
    db_session.refresh(test_curation)
    assert test_curation.curator_classification == "strong_association"
    test_curation.computed_verdict = "Strong Association"
    assert not _unexplained_override(test_curation)


def test_override_equal_to_computed_needs_no_rationale(
    test_curation: CurationNew,
) -> None:
    test_curation.computed_verdict = "No Known Disease Relationship"
    test_curation.curator_classification = "no_known"  # agreeing: no rationale
    assert not _unexplained_override(test_curation)
    test_curation.computed_verdict = "moderate"
    test_curation.curator_classification = "moderate"
    assert not _unexplained_override(test_curation)
    test_curation.curator_classification = "Limited"
    assert _unexplained_override(test_curation)
    test_curation.curator_classification_rationale = "  "
    assert _unexplained_override(test_curation)


def _active(
    db: Session,
    pair: WorkflowPair,
    gene: Gene,
    scope: Scope,
    computed: str,
    curator: str | None,
) -> CurationNew:
    at = datetime(2026, 1, 1, tzinfo=UTC)
    c = CurationNew(
        id=uuid4(),
        scope_id=scope.id,
        gene_id=gene.id,
        workflow_pair_id=pair.id,
        workflow_stage="active",
        status="active",
        evidence_data={},
        computed_verdict=computed,
        curator_classification=curator,
        curator_classification_rationale="Contradictory evidence" if curator else None,
        updated_at=at,
    )
    db.add(c)
    db.flush()
    db.add(
        ActiveCuration(
            gene_id=gene.id,
            scope_id=scope.id,
            curation_id=c.id,
            entity_key="",
            activated_at=at,
            updated_at=at,
        )
    )
    db.commit()
    return c


@pytest.mark.parametrize(
    ("curator", "final"), [("Disputed", "Disputed"), (None, "Moderate")]
)
def test_catalogue_and_export_publish_final_and_computed(
    client: TestClient,
    db_session: Session,
    test_workflow_pair: WorkflowPair,
    test_gene: Gene,
    test_public_scope: Scope,
    curator: str | None,
    final: str,
) -> None:
    c = _active(
        db_session,
        test_workflow_pair,
        test_gene,
        test_public_scope,
        "Moderate",
        curator,
    )

    [item] = client.get("/api/v1/export/curations").json()["items"]
    assert item["curation_id"] == str(c.id)
    assert item["curator_classification_rationale"] == (
        "Contradictory evidence" if curator else None
    )
    assert (item["computed_verdict"], item["final_classification"]) == (
        "Moderate",
        final,
    )

    cat = client.get("/api/v1/gene-catalogue/").json()
    [gene] = cat["entries"]
    assert gene["classifications"] == {final.lower(): 1}
    [summary] = gene["scope_curations"]
    assert (summary["computed_verdict"], summary["classification"]) == (
        "Moderate",
        final,
    )
    assert cat["summary"]["classification_summary"] == {final.lower(): 1}
    filtered = client.get(
        "/api/v1/gene-catalogue/", params={"classification": final.lower()}
    ).json()
    assert len(filtered["entries"]) == 1
    assert client.get("/api/v1/gene-catalogue/filters/classifications").json() == [
        final.lower()
    ]


def test_engine_label_and_curator_key_count_in_one_bucket(
    client: TestClient,
    db_session: Session,
    test_workflow_pair: WorkflowPair,
    test_gene: Gene,
    test_public_scope: Scope,
) -> None:
    other = Gene(
        id=uuid4(),
        hgnc_id="HGNC:99",
        approved_symbol="OTHER",
        record_hash="f" * 64,
        previous_symbols=[],
        alias_symbols=[],
    )
    db_session.add(other)
    db_session.commit()
    _active(
        db_session,
        test_workflow_pair,
        test_gene,
        test_public_scope,
        "No Known Disease Relationship",  # GenCC's label
        None,
    )
    _active(
        db_session, test_workflow_pair, other, test_public_scope, "Limited", "no_known"
    )

    cat = client.get("/api/v1/gene-catalogue/").json()
    assert cat["summary"]["classification_summary"] == {"no_known": 2}
    assert sorted(e["classifications"]["no_known"] for e in cat["entries"]) == [1, 1]
    filtered = client.get(
        "/api/v1/gene-catalogue/",
        params={"classification": "No known disease relationship"},
    ).json()
    assert filtered["total"] == 2
    assert client.get("/api/v1/gene-catalogue/filters/classifications").json() == [
        "no_known"
    ]
