"""049 preserves immutable history and uses successor pins through the real app_user API."""

import copy
import json
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.scoring.point_model import template
from tests.postgres.test_methodology_versions import W, _h, _owner, client, w
from tests.unit.test_clingen_successor import successor_model

pytestmark = pytest.mark.postgres
__all__ = ["client", "w"]
MIGRATION = Path(__file__).parents[3] / "database/sql/049_clingen_successor.sql"
STOCK = "ClinGen_SOP_v11"


def clone_stock(s, *, custom=False, derived=False):
    original = s.execute(
        text(
            "SELECT c.id, mv.snapshot FROM curation_schemas c JOIN methodology_versions mv ON mv.schema_id=c.id AND mv.version=1 WHERE c.name=:name AND c.version='1.0.0'"
        ),
        {"name": STOCK},
    ).one()
    snapshot = copy.deepcopy(original.snapshot)
    if custom:
        snapshot["scoring_configuration"]["point_model"]["total_cap"] = 17
    # Transaction-local rename makes room for an exact stock identity; rollback restores it.
    s.execute(
        text("UPDATE curation_schemas SET name=:name WHERE id=:id"),
        {"name": f"original-{uuid4()}", "id": original.id},
    )
    sid = s.scalar(
        text(
            "INSERT INTO curation_schemas (name, version, schema_type, field_definitions, validation_rules, scoring_configuration, workflow_states, ui_configuration, schema_hash, based_on_schema_id) VALUES (:name, '1.0.0', 'curation', CAST(:fields AS jsonb), CAST(:rules AS jsonb), CAST(:config AS jsonb), CAST(:workflow AS jsonb), CAST(:ui AS jsonb), repeat('4',64), :parent) RETURNING id"
        ),
        {
            "name": STOCK,
            "fields": json.dumps(snapshot["field_definitions"]),
            "rules": json.dumps(snapshot["validation_rules"]),
            "config": json.dumps(snapshot["scoring_configuration"]),
            "workflow": json.dumps(snapshot["workflow_states"]),
            "ui": json.dumps(snapshot["ui_configuration"]),
            "parent": original.id if derived else None,
        },
    )
    return sid, snapshot


def versions(s, sid):
    return s.execute(
        text(
            "SELECT version, snapshot::text FROM methodology_versions WHERE schema_id=:s ORDER BY version"
        ),
        {"s": sid},
    ).all()


def run_migration(s):
    s.execute(text(MIGRATION.read_text()))


def test_fresh_database_has_successors_without_replacing_v1(owner_session):
    # versions 1-2 are 049's; 068 publishes ClinGen_SOP_v11 v3 on top
    rows = owner_session.execute(
        text(
            "SELECT c.name, mv.version, mv.snapshot #>> '{scoring_configuration,point_model,sections,0,categories,1,types,0,rule}' FROM curation_schemas c JOIN methodology_versions mv ON mv.schema_id=c.id WHERE c.name IN ('ClinGen_SOP_v11', 'ClinGen Gene-Disease Validity SOP') AND mv.version <= 2 ORDER BY c.name,mv.version"
        )
    ).all()
    assert len(rows) == 4
    assert [r[1:] for r in rows] == [(1, "segregation"), (2, "explicit_points")] * 2


@pytest.mark.parametrize("existing_identical_version", [False, True])
def test_migration_is_idempotent_preserves_all_history_and_never_overwrites_numbers(
    owner_session, existing_identical_version
):
    s = owner_session
    sid, snapshot = clone_stock(s)
    if existing_identical_version:
        s.execute(
            text(
                "INSERT INTO methodology_versions (schema_id,version,snapshot) VALUES (:s,2,CAST(:doc AS jsonb))"
            ),
            {"s": sid, "doc": json.dumps(snapshot)},
        )
    before = versions(s, sid)
    history = s.execute(
        text("SELECT id,snapshot::text FROM methodology_versions ORDER BY id")
    ).all()
    curations = s.execute(
        text(
            "SELECT id,methodology_version_id,evidence_data::text,computed_scores::text,computed_verdict FROM curations ORDER BY id"
        )
    ).all()
    precurations = s.execute(
        text(
            "SELECT id,methodology_version_id,evidence_data::text FROM precurations ORDER BY id"
        )
    ).all()
    run_migration(s)
    after = versions(s, sid)
    assert after[:-1] == before
    assert after[-1][0] == (3 if existing_identical_version else 2)
    successor = json.loads(after[-1][1])
    assert successor["scoring_configuration"]["point_model"] == successor_model()
    ar = successor["field_definitions"]["genetic_evidence"]["properties"]["case_level"][
        "properties"
    ]["autosomal_recessive"]["properties"]
    assert (
        ar["predicted_or_proven_null"]["items"]["properties"]["proband_counted_points"][
            "default"
        ]
        == 3
    )
    assert ar["other_variant_type"]["items"]["properties"]["proband_counted_points"][
        "default_by"
    ]["values"] == {"null_and_other": 1.5, "two_other": 0.2, "homozygous_other": 0.2}
    for vid, old in history:
        assert (
            s.scalar(
                text("SELECT snapshot::text FROM methodology_versions WHERE id=:id"),
                {"id": vid},
            )
            == old
        )
    assert (
        s.execute(
            text(
                "SELECT id,methodology_version_id,evidence_data::text,computed_scores::text,computed_verdict FROM curations ORDER BY id"
            )
        ).all()
        == curations
    )
    assert (
        s.execute(
            text(
                "SELECT id,methodology_version_id,evidence_data::text FROM precurations ORDER BY id"
            )
        ).all()
        == precurations
    )
    run_migration(s)
    assert versions(s, sid) == after
    with pytest.raises(Exception, match="immutable"), s.begin_nested():
        s.execute(
            text("UPDATE methodology_versions SET snapshot='{}' WHERE schema_id=:s"),
            {"s": sid},
        )


@pytest.mark.parametrize(
    "case", ["custom_model", "derived", "working_edit", "published_edit"]
)
def test_migration_leaves_custom_derived_and_changed_stock_alone(owner_session, case):
    s = owner_session
    sid, snapshot = clone_stock(
        s, custom=case == "custom_model", derived=case == "derived"
    )
    if case == "working_edit":
        s.execute(
            text(
                'UPDATE curation_schemas SET field_definitions=field_definitions || \'{"custom_note":{"type":"text"}}\'::jsonb WHERE id=:s'
            ),
            {"s": sid},
        )
    if case == "published_edit":
        snapshot["field_definitions"]["custom_note"] = {"type": "text"}
        s.execute(
            text(
                "INSERT INTO methodology_versions (schema_id,version,snapshot) VALUES (:s,2,CAST(:doc AS jsonb))"
            ),
            {"s": sid, "doc": json.dumps(snapshot)},
        )
    before = versions(s, sid)
    working = s.scalar(
        text(
            "SELECT methodology_snapshot(c)::text FROM curation_schemas c WHERE id=:s"
        ),
        {"s": sid},
    )
    run_migration(s)
    assert versions(s, sid) == before
    assert (
        s.scalar(
            text(
                "SELECT methodology_snapshot(c)::text FROM curation_schemas c WHERE id=:s"
            ),
            {"s": sid},
        )
        == working
    )


def publish(client, w: W, model):
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE curation_schemas SET scoring_configuration=%s WHERE id=%s",
            (json.dumps({"engine": "clingen_sop_v11", "point_model": model}), w.schema),
        )
    response = client.post(
        f"/api/v1/schemas/curation-schemas/{w.schema}/versions", headers=_h(w.admin)
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def create(client, w: W, gene, evidence):
    response = client.post(
        "/api/v1/curations/",
        json={
            "gene_id": str(gene),
            "scope_id": str(w.scope),
            "workflow_pair_id": w.pair,
            "evidence_data": evidence,
        },
        headers=_h(w.alice),
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.parametrize("legacy", [False, True])
def test_app_user_old_pin_stays_old_and_successor_save_preview_reload_agree(
    client, w: W, legacy
):
    old_pin = publish(client, w, template("clingen_sop_v11"))
    row = {"lod_score": 9 if legacy else 1.2, "pmid": "12345678"}
    evidence = {
        "genetic_evidence": [{**row, "evidence_category": "segregation"}]
        if legacy
        else {"segregation": [row]}
    }
    old = create(client, w, w.genes[0], evidence)
    assert old["methodology_version_id"] == old_pin
    assert old["computed_scores"]["total_score"] == (3 if legacy else 2)
    new_pin = publish(client, w, successor_model())
    new = create(client, w, w.genes[1], evidence)
    assert new["methodology_version_id"] == new_pin
    assert new["computed_scores"]["total_score"] == 0
    for current in (old, new):
        saved = client.patch(
            f"/api/v1/curations/{current['id']}/draft?detail=true",
            json={"evidence_data": evidence, "lock_version": current["lock_version"]},
            headers=_h(w.alice),
        )
        assert saved.status_code == 200, saved.text
        assert (
            saved.json()["methodology_version_id"] == current["methodology_version_id"]
        )
        preview = client.post(
            "/api/v1/validation/validate-evidence",
            json={
                "evidence_data": evidence,
                "methodology_version_id": current["methodology_version_id"],
            },
            headers=_h(w.alice),
        )
        assert preview.status_code == 200, preview.text
        detail = client.get(
            f"/api/v1/curations/{current['id']}?detail=true", headers=_h(w.alice)
        )
        assert detail.status_code == 200, detail.text
        trace = current["computed_scores"]["trace"]
        assert saved.json()["computed_scores"]["trace"] == trace
        assert preview.json()["score_calculations"]["trace"] == trace
        assert detail.json()["computed_scores"]["trace"] == trace
        assert any(
            "Enter segregation points" in v["message"]
            for v in preview.json()["warnings"]
        ) is (current is new)


@pytest.mark.parametrize(
    ("table", "variant", "points"),
    [
        ("predicted_or_proven_null", "two_null", 3),
        ("other_variant_type", "null_and_other", 1.5),
        ("other_variant_type", "two_other", 0.2),
    ],
)
def test_app_user_successor_ar_blank_entered_and_manual_zero_agree(
    client, w: W, table, variant, points
):
    pin = publish(client, w, successor_model())
    row = {"id": "new", "variant_type": variant, "proband_counted_points": points}
    evidence = {
        "genetic_evidence": {"case_level": {"autosomal_recessive": {table: [row]}}}
    }
    current = create(client, w, w.genes[0], evidence)
    assert current["computed_scores"]["total_score"] == 0
    row |= {"pmid": "12345678", "variant_1": "c.1A>T", "score_status": "score"}
    for expected in (points, 0):
        row["proband_counted_points"] = expected
        saved = client.patch(
            f"/api/v1/curations/{current['id']}/draft?detail=true",
            json={"evidence_data": evidence, "lock_version": current["lock_version"]},
            headers=_h(w.alice),
        )
        assert saved.status_code == 200, saved.text
        current = saved.json()
        assert current["methodology_version_id"] == pin
        assert current["computed_scores"]["total_score"] == expected
        preview = client.post(
            "/api/v1/validation/validate-evidence",
            json={"evidence_data": evidence, "methodology_version_id": pin},
            headers=_h(w.alice),
        )
        assert preview.status_code == 200, preview.text
        assert (
            preview.json()["score_calculations"]["trace"]
            == current["computed_scores"]["trace"]
        )
        detail = client.get(
            f"/api/v1/curations/{current['id']}?detail=true", headers=_h(w.alice)
        )
        assert detail.status_code == 200, detail.text
        assert detail.json()["evidence_data"] == evidence
        assert (
            detail.json()["computed_scores"]["trace"]
            == current["computed_scores"]["trace"]
        )


def test_successor_new_segregation_rows_start_unassigned_while_v1_keeps_zero(
    owner_session,
):
    defaults = owner_session.execute(
        text(
            "SELECT mv.version, mv.snapshot #> '{field_definitions,genetic_evidence,properties,segregation,items,properties,points,default}' FROM curation_schemas c JOIN methodology_versions mv ON mv.schema_id=c.id WHERE c.name IN ('ClinGen_SOP_v11', 'ClinGen Gene-Disease Validity SOP') AND mv.version <= 2 ORDER BY c.name,mv.version"
        )
    ).all()
    assert defaults == [(1, 0), (2, None)] * 2


@pytest.mark.parametrize("legacy", [False, True])
def test_app_user_untouched_segregation_default_differs_from_assigned_zero(
    client, w: W, legacy
):
    pin = publish(client, w, successor_model())
    published = client.get(
        f"/api/v1/schemas/methodology-versions/{pin}", headers=_h(w.alice)
    )
    assert published.status_code == 200, published.text
    default = published.json()["snapshot"]["field_definitions"]["genetic_evidence"][
        "properties"
    ]["segregation"]["items"]["properties"]["points"]["default"]
    assert (
        default is None
    )  # untouched is unassigned; deliberate zero is a separate case
    row = {"id": "new-row", "lod_score": 3.1, "family_count": 2, "points": default}
    data = (
        [{**row, "evidence_category": "segregation"}]
        if legacy
        else {"segregation": [row]}
    )
    evidence = {"genetic_evidence": data}
    current = create(client, w, w.genes[0], evidence)
    for points in (default, 0):
        if legacy:
            data[0]["points"] = points
        else:
            row["points"] = points
        saved = client.patch(
            f"/api/v1/curations/{current['id']}/draft?detail=true",
            headers=_h(w.alice),
            json={"evidence_data": evidence, "lock_version": current["lock_version"]},
        )
        assert saved.status_code == 200, saved.text
        current = saved.json()
        assert current["computed_scores"]["total_score"] == 0
        preview = client.post(
            "/api/v1/validation/validate-evidence",
            headers=_h(w.alice),
            json={"evidence_data": evidence, "methodology_version_id": pin},
        )
        assert preview.status_code == 200, preview.text
        assert any(
            "Enter segregation points" in warning["message"]
            for warning in preview.json()["warnings"]
        ) is (points is None)
        assert (
            preview.json()["score_calculations"]["trace"]
            == current["computed_scores"]["trace"]
        )
        loaded = client.get(
            f"/api/v1/curations/{current['id']}?detail=true", headers=_h(w.alice)
        )
        assert loaded.status_code == 200, loaded.text
        assert loaded.json()["evidence_data"] == evidence
        assert loaded.json()["computed_scores"] == current["computed_scores"]
