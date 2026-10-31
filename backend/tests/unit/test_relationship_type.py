"""Relationship type (#539): the entity_key suffix, its exposure, the curation entity
guard and the schema-declared classification vocabulary."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.schema_rules import check_schema_definition
from app.crud.precuration_entity import entity_key_of
from app.models import CurationNew
from app.schemas.curation import relationship_type
from tests.api.scopes.factories import auth_headers
from tests.unit.test_split_entities import A, World, no_rls_on_sqlite

__all__ = ["no_rls_on_sqlite"]
SUS = {**A, "relationship_type": "susceptibility"}


def test_only_susceptibility_suffixes_the_key(db_session: Session) -> None:
    def key(evidence: dict) -> str:
        return entity_key_of(db_session, evidence)

    mendelian = key(A)
    assert mendelian == "MONDO:0000001|AD"
    assert key({**A, "relationship_type": "mendelian"}) == mendelian
    assert key({**A, "relationship_type": "other"}) == mendelian
    assert key(SUS) == f"{mendelian}|SUSCEPTIBILITY"
    nested = {"entity_definition": {**A, "relationship_type": " Susceptibility "}}
    assert key(nested) == key(SUS)
    assert key({"relationship_type": "susceptibility"}) == ""  # no MONDO, no entity


def test_risk_allele_and_undetermined_moi_join_the_key(db_session: Session) -> None:
    """#614: two risk alleles of one gene and disease are two entities; the allele is
    ignored for Mendelian entities; UD / MF MOI are canonical codes."""

    def key(evidence: dict) -> str:
        return entity_key_of(db_session, evidence)

    base = "MONDO:0000001|AD|SUSCEPTIBILITY"
    assert key({**SUS, "risk_allele": " rs4664308 "}) == f"{base}|RS4664308"
    assert key({**SUS, "risk_allele": "rs17831251"}) == f"{base}|RS17831251"
    assert key({**SUS, "risk_allele": " "}) == base
    assert key({**A, "risk_allele": "rs1"}) == "MONDO:0000001|AD"
    assert (
        key({**SUS, "mode_of_inheritance": "HP:0000005"}).split("|")[1]
        == "UNDETERMINED"
    )
    assert (
        key({**SUS, "mode_of_inheritance": "Multifactorial"}).split("|")[1]
        == "MULTIFACTORIAL"
    )


def test_relationship_type_defaults_to_mendelian() -> None:
    assert relationship_type(None, None) == "mendelian"
    assert relationship_type({}, SUS) == "susceptibility"  # inherited
    assert relationship_type({"relationship_type": "mendelian"}, SUS) == "mendelian"


def test_curation_inherits_and_cannot_move_its_entity(
    client: TestClient, db_session: Session
) -> None:
    world = World(db_session)
    _, mendelian = world.approve(A)
    _, sus = world.approve(SUS)  # coexists with the Mendelian entity
    assert mendelian and sus and mendelian != sus
    curation = db_session.get(CurationNew, sus)
    assert curation and curation.entity_key == "MONDO:0000001|AD|SUSCEPTIBILITY"

    h = auth_headers(world.author)
    r = client.get(f"/api/v1/curations/{sus}", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["relationship_type"] == "susceptibility"

    def save(evidence: dict, url: str = f"/api/v1/curations/{sus}/draft") -> int:
        version = db_session.get(CurationNew, sus).lock_version  # type: ignore[union-attr]
        db_session.expire_all()
        r = client.patch(
            url, json={"evidence_data": evidence, "lock_version": version}, headers=h
        )
        return r.status_code

    moved = {"entity_definition": {**A, "mondo_id": "MONDO:0000002"}}
    assert save(moved) == 409
    r = client.put(
        f"/api/v1/curations/{sus}",
        json={"evidence_data": moved, "lock_version": curation.lock_version},
        headers=h,
    )
    assert r.status_code == 409, r.text
    assert r.json()["detail"]["curation_id"] == str(sus)
    assert save({"entity_definition": A}) == 200  # the precuration supplies the type
    assert save({"notes": "no disease fields"}) == 200


def _schema(scoring: dict) -> dict:
    return {
        "field_definitions": {"x": {"type": "text"}},
        "workflow_states": {"states": ["draft"]},
        "ui_configuration": {"sections": []},
        "scoring_configuration": {"engine": "clingen_sop_v11", **scoring},
    }


def _errors(scoring: dict) -> list[tuple[str, str]]:
    return [
        (path, msg)
        for severity, path, msg in check_schema_definition(_schema(scoring))
        if severity == "error" and "classifications" in path
    ]


def test_classification_vocabulary_is_validated() -> None:
    good = {
        "key": "established_risk",
        "label": "Established",
        "order": 1,
        "tone": "strong",
    }
    assert _errors({"classifications": [good]}) == []
    assert _errors({"classifications": "x"}) == [
        ("scoring_configuration.classifications", "classifications must be a list")
    ]
    bad = _errors(
        {
            "classifications": [
                good,
                {**good, "label": "", "order": True, "tone": "red"},
                3,
            ]
        }
    )
    assert [p.rsplit(".", 1)[-1] for p, _ in bad] == [
        "key",
        "label",
        "order",
        "tone",
        "classifications[2]",
    ]
    case = {"key": "Strong", "label": "S", "order": 1, "tone": "strong"}
    assert _errors({"classifications": [case, {**case, "key": "strong"}]}) == [
        (
            "scoring_configuration.classifications[1].key",
            "key must be a unique, non-empty text",
        )
    ]
    assert (
        _errors(
            {
                "classifications": [case],
                "point_model": {"bands": [{"class": "strong"}]},
            }
        )
        == []
    )
    clash = {"key": "Strong", "label": "Strong", "order": 1, "tone": "limited"}
    assert _errors({"classifications": [clash]}) == [
        (
            "scoring_configuration.classifications[0].tone",
            "ClinGen class 'Strong' keeps its own tone (strong)",
        )
    ]
    assert _errors({"classifications": [{**clash, "tone": "strong"}]}) == []
    model = {"bands": [{"class": "established_risk"}, {"class": "likely_risk"}]}
    assert _errors({"classifications": [good], "point_model": model})[-1] == (
        "scoring_configuration.classifications",
        "Point model class 'likely_risk' is not in classifications",
    )


def test_create_refuses_evidence_naming_another_entity(
    client: TestClient, db_session: Session
) -> None:
    world = World(db_session)
    pre, curation_id = world.approve(SUS)
    db_session.delete(db_session.get(CurationNew, curation_id))  # free the entity
    db_session.commit()
    moved = {"entity_definition": {**A, "mondo_id": "MONDO:0000002"}}
    status, body = world.create(client, precuration_id=str(pre.id), evidence_data=moved)
    assert status == 409, body
    assert body["detail"]["precuration_id"] == str(pre.id)
    status, body = world.create(
        client, precuration_id=str(pre.id), evidence_data={"entity_definition": A}
    )
    assert status == 201, body
    made = db_session.get(CurationNew, body["id"])
    assert made and made.entity_key == "MONDO:0000001|AD|SUSCEPTIBILITY"


def test_class_key_matches_the_frontend_class_key() -> None:
    """Same inputs as config/__tests__/classification.spec.ts (classKey)."""
    from app.schemas.curation import class_key

    assert class_key("Limited - Moderate") == "limited___moderate"
    assert class_key(" Strong  Association ") == "strong__association"
    assert class_key("No Known Disease Relationship") == "no_known"
