"""Genes x scopes catalogue matrix: cells, agreement, visibility, bounded queries."""

import hashlib
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.core.security import create_access_token, get_password_hash
from app.models.models import (
    ActiveCuration,
    CurationNew,
    Gene,
    Scope,
    ScopeMembership,
    UserNew,
    WorkflowPair,
)

pytestmark = pytest.mark.unit
URL = "/api/v1/gene-catalogue/matrix"


def _gene(db: Session, symbol: str, n: int, **kw: Any) -> Gene:
    gene = Gene(
        id=uuid4(),
        hgnc_id=f"HGNC:{n}",
        approved_symbol=symbol,
        record_hash=hashlib.sha256(f"{symbol}{n}".encode()).hexdigest(),
        **{"previous_symbols": [], "alias_symbols": [], **kw},
    )
    db.add(gene)
    db.commit()
    return gene


def _scope(db: Session, name: str, public: bool) -> Scope:
    scope = Scope(
        id=uuid4(),
        name=name,
        display_name=name.title(),
        is_public=public,
        is_active=True,
    )
    db.add(scope)
    db.commit()
    return scope


def _user(db: Session, name: str, role: str = "user") -> tuple[UserNew, dict[str, str]]:
    user = UserNew(
        id=uuid4(),
        email=f"{name}@t.org",
        hashed_password=get_password_hash("x"),
        name=name,
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    token = create_access_token(data={"sub": str(user.id)})
    return user, {"Authorization": f"Bearer {token}"}


def _member(db: Session, scope: Scope, user: UserNew, accepted: bool = True) -> None:
    db.add(
        ScopeMembership(
            scope_id=scope.id,
            user_id=user.id,
            role="viewer",
            accepted_at=datetime.now(UTC) if accepted else None,
        )
    )
    db.commit()


def _curation(
    db: Session,
    pair: WorkflowPair,
    gene: Gene,
    scope: Scope,
    verdict: str | None,
    status: str = "active",
    stage: str = "active",
    total: float | None = None,
) -> CurationNew:
    c = CurationNew(
        id=uuid4(),
        scope_id=scope.id,
        gene_id=gene.id,
        workflow_pair_id=pair.id,
        workflow_stage=stage,
        status=status,
        evidence_data={},
        computed_verdict=verdict,
        computed_scores={"total_score": total} if total is not None else {},
        approved_at=datetime.now(UTC) if status == "active" else None,  # #613
    )
    db.add(c)
    db.commit()
    if status == "active":
        db.add(
            ActiveCuration(
                gene_id=gene.id,
                scope_id=scope.id,
                curation_id=c.id,
                activated_at=datetime.now(UTC),
            )
        )
        db.commit()
    return c


class World:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.pair = WorkflowPair(id=uuid4(), name="wp", version="1")
        db.add(self.pair)
        db.commit()
        self.pub = _scope(db, "pub", True)
        self.priv = _scope(db, "priv", False)
        self.other = _scope(db, "other", False)
        self.pkd1 = _gene(db, "PKD1", 1, alias_symbols=["PBP"])
        self.hnf1b = _gene(db, "HNF1B", 2)
        self.uromod = _gene(db, "UMOD", 3)

    def cur(
        self, gene: Gene, scope: Scope, verdict: str | None, **kw: Any
    ) -> CurationNew:
        return _curation(self.db, self.pair, gene, scope, verdict, **kw)

    def ids(self, *scopes: Scope) -> list[tuple[str, str]]:
        return [("scope_ids", str(s.id)) for s in scopes]


@pytest.fixture
def world(db_session: Session) -> World:
    return World(db_session)


def test_returns_cells_per_scope_with_agreement(
    client: TestClient, world: World
) -> None:
    world.cur(world.pkd1, world.pub, "Definitive", total=14.5)
    world.cur(world.pkd1, world.priv, "Disputed")
    world.cur(world.hnf1b, world.pub, "Strong")
    world.cur(world.hnf1b, world.priv, "strong")
    alice, headers = _user(world.db, "alice")
    _member(world.db, world.priv, alice)

    body = client.get(
        URL, params=world.ids(world.pub, world.priv), headers=headers
    ).json()

    assert body["total"] == 2
    assert [s["id"] for s in body["scopes"]] == [str(world.pub.id), str(world.priv.id)]
    rows = {r["approved_symbol"]: r for r in body["rows"]}
    assert rows["PKD1"]["agreement"] == "disagree"
    assert rows["HNF1B"]["agreement"] == "agree"
    cell = next(c for c in rows["PKD1"]["cells"] if c["scope_id"] == str(world.pub.id))
    assert cell["classification"] == "Definitive"
    assert cell["stage"] == "active"
    assert cell["total_score"] == 14.5
    assert cell["in_progress"] is False


def test_agreement_values_for_single_and_none(client: TestClient, world: World) -> None:
    world.cur(world.pkd1, world.pub, "Definitive")
    world.cur(world.hnf1b, world.pub, None)
    body = client.get(URL, params=world.ids(world.pub)).json()
    rows = {r["approved_symbol"]: r["agreement"] for r in body["rows"]}
    assert rows == {"HNF1B": "none", "PKD1": "single"}


def test_disagreement_filter_matches_agreement_column(
    client: TestClient, world: World
) -> None:
    world.cur(world.pkd1, world.pub, "Definitive")
    world.cur(world.pkd1, world.other, "Refuted")
    world.cur(world.hnf1b, world.pub, "Strong")
    world.cur(world.hnf1b, world.other, "Strong")
    world.cur(world.uromod, world.pub, "Limited")
    alice, headers = _user(world.db, "alice")
    _member(world.db, world.other, alice)
    params = world.ids(world.pub, world.other)
    everything = client.get(URL, params=params, headers=headers).json()
    dis = client.get(
        URL, params=[*params, ("agreement", "disagree")], headers=headers
    ).json()
    agree = client.get(
        URL, params=[*params, ("agreement", "agree")], headers=headers
    ).json()
    assert (
        {r["approved_symbol"] for r in dis["rows"]}
        == {
            r["approved_symbol"]
            for r in everything["rows"]
            if r["agreement"] == "disagree"
        }
        == {"PKD1"}
    )
    assert dis["total"] == 1
    assert {r["approved_symbol"] for r in agree["rows"]} == {"HNF1B"}


def test_private_scope_hidden_from_anonymous_and_pending_member(
    client: TestClient, world: World
) -> None:
    world.cur(world.pkd1, world.priv, "Definitive")
    world.cur(world.pkd1, world.pub, "Strong")
    carol, headers = _user(world.db, "carol")
    _member(world.db, world.priv, carol, accepted=False)
    for h in ({}, headers):
        body = client.get(
            URL, params=world.ids(world.pub, world.priv), headers=h
        ).json()
        assert [s["id"] for s in body["scopes"]] == [str(world.pub.id)]
        assert [c["scope_id"] for c in body["rows"][0]["cells"]] == [str(world.pub.id)]
    only_private = client.get(URL, params=world.ids(world.priv), headers=headers).json()
    assert only_private["total"] == 0
    assert only_private["scopes"] == []


def test_platform_admin_has_no_bypass(client: TestClient, world: World) -> None:
    world.cur(world.pkd1, world.priv, "Definitive")
    world.cur(world.pkd1, world.pub, "Strong")
    _, headers = _user(world.db, "root", role="admin")
    body = client.get(
        URL, params=world.ids(world.pub, world.priv), headers=headers
    ).json()
    assert [s["id"] for s in body["scopes"]] == [str(world.pub.id)]
    assert len(body["rows"][0]["cells"]) == 1


def test_in_progress_cells_only_for_accepted_members(
    client: TestClient, world: World
) -> None:
    world.cur(world.hnf1b, world.pub, "Strong")
    world.cur(world.pkd1, world.pub, None, status="in_review", stage="review")
    world.cur(world.uromod, world.priv, None, status="draft", stage="curation")
    member, mh = _user(world.db, "mem")
    _member(world.db, world.pub, member)
    _member(world.db, world.priv, member)
    _, other_h = _user(world.db, "outsider")
    params = world.ids(world.pub, world.priv)

    mine = client.get(URL, params=params, headers=mh).json()
    assert {r["approved_symbol"] for r in mine["rows"]} == {"HNF1B", "PKD1", "UMOD"}
    pkd = next(r for r in mine["rows"] if r["approved_symbol"] == "PKD1")
    assert pkd["cells"][0]["in_progress"] is True
    assert pkd["cells"][0]["stage"] == "review"
    assert pkd["cells"][0]["classification"] is None

    for h in ({}, other_h):
        theirs = client.get(URL, params=params, headers=h).json()
        assert {r["approved_symbol"] for r in theirs["rows"]} == {"HNF1B"}
        assert theirs["total"] == 1


def test_active_cell_wins_over_in_progress_revision(
    client: TestClient, world: World
) -> None:
    world.cur(world.pkd1, world.pub, "Strong")
    world.cur(world.pkd1, world.pub, None, status="draft", stage="curation")
    mem, h = _user(world.db, "mem")
    _member(world.db, world.pub, mem)
    cells = client.get(URL, params=world.ids(world.pub), headers=h).json()["rows"][0][
        "cells"
    ]
    assert [(c["classification"], c["in_progress"]) for c in cells] == [
        ("Strong", False)
    ]


def test_search_paging_and_sort(client: TestClient, world: World) -> None:
    for gene in (world.pkd1, world.hnf1b, world.uromod):
        world.cur(gene, world.pub, "Strong")
    base = world.ids(world.pub)
    assert [
        r["approved_symbol"] for r in client.get(URL, params=base).json()["rows"]
    ] == ["HNF1B", "PKD1", "UMOD"]
    desc = client.get(
        URL, params=[*base, ("sort_order", "desc"), ("limit", "2")]
    ).json()
    assert [r["approved_symbol"] for r in desc["rows"]] == ["UMOD", "PKD1"]
    assert desc["total"] == 3 and desc["has_next"] and not desc["has_prev"]
    page2 = client.get(URL, params=[*base, ("limit", "2"), ("skip", "2")]).json()
    assert [r["approved_symbol"] for r in page2["rows"]] == ["HNF1B"] or page2[
        "has_prev"
    ]
    found = client.get(URL, params=[*base, ("search", "pbp")]).json()
    assert [r["approved_symbol"] for r in found["rows"]] == ["PKD1"]
    assert found["total"] == 1


def test_scope_cap_and_required(client: TestClient, world: World) -> None:
    assert client.get(URL).status_code == 422
    many = [("scope_ids", str(uuid4())) for _ in range(51)]
    assert client.get(URL, params=many).status_code == 422
    unknown = client.get(URL, params=[("scope_ids", str(uuid4()))])
    assert unknown.status_code == 200 and unknown.json()["total"] == 0


def test_query_count_is_bounded(
    client: TestClient, world: World, db_session: Session
) -> None:
    scopes = [world.pub] + [_scope(world.db, f"s{i}", True) for i in range(6)]
    genes = [world.pkd1, world.hnf1b, world.uromod] + [
        _gene(world.db, f"G{i}", 10 + i) for i in range(20)
    ]
    for gene in genes:
        for scope in scopes:
            world.cur(gene, scope, "Strong")
    _, h = _user(world.db, "mem")
    params = [*world.ids(*scopes), ("limit", "100")]
    statements: list[str] = []
    engine = db_session.get_bind()

    def count(conn: Any, cursor: Any, statement: str, *a: Any) -> None:
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", count)
    try:
        body = client.get(URL, params=params, headers=h).json()
    finally:
        event.remove(engine, "before_cursor_execute", count)
    assert len(body["rows"]) == 23
    assert len(statements) <= 10, statements


def test_ties_on_symbol_page_without_repeats_or_gaps(
    client: TestClient, world: World
) -> None:
    genes = [_gene(world.db, "DUP", 100 + i) for i in range(5)]
    for gene in genes:
        world.cur(gene, world.pub, "Strong")
    seen: list[str] = []
    for skip in range(0, 5, 2):
        body = client.get(
            URL, params=[*world.ids(world.pub), ("limit", "2"), ("skip", str(skip))]
        ).json()
        seen += [r["gene_id"] for r in body["rows"]]
    assert sorted(seen) == sorted(str(g.id) for g in genes)


def test_like_wildcards_in_search_are_literal(client: TestClient, world: World) -> None:
    world.cur(world.pkd1, world.pub, "Strong")
    world.cur(world.hnf1b, world.pub, "Strong")
    odd = _gene(world.db, "A_B", 50)
    world.cur(odd, world.pub, "Strong")
    world.cur(_gene(world.db, "AXB", 51), world.pub, "Strong")
    base = world.ids(world.pub)
    for term in ("%", "\\"):
        assert client.get(URL, params=[*base, ("search", term)]).json()["total"] == 0
    found = client.get(URL, params=[*base, ("search", "A_B")]).json()
    assert [r["approved_symbol"] for r in found["rows"]] == ["A_B"]


def test_search_rejects_nul_and_overlong(client: TestClient, world: World) -> None:
    base = world.ids(world.pub)
    assert client.get(URL, params=[*base, ("search", "a\x00b")]).status_code == 422
    assert client.get(URL, params=[*base, ("search", "x" * 101)]).status_code == 422


def test_deactivated_scope_is_hidden(client: TestClient, world: World) -> None:
    world.cur(world.pkd1, world.pub, "Strong")
    world.cur(world.hnf1b, world.other, "Strong")
    world.other.is_public = True
    world.other.is_active = False
    world.db.commit()
    body = client.get(URL, params=world.ids(world.pub, world.other)).json()
    assert [s["id"] for s in body["scopes"]] == [str(world.pub.id)]
    assert [r["approved_symbol"] for r in body["rows"]] == ["PKD1"]


def test_agreement_is_per_disease_entity(client: TestClient, world: World) -> None:
    """#530: two entities of one gene are compared on their own, not with each other."""

    def entity(gene: Gene, scope: Scope, verdict: str, key: str) -> None:
        c = world.cur(gene, scope, verdict)
        c.entity_key = key
        world.db.query(ActiveCuration).filter_by(curation_id=c.id).update(
            {"entity_key": key}
        )
        world.db.commit()

    entity(world.hnf1b, world.pub, "Limited", "MONDO:2|AD")
    entity(world.hnf1b, world.pub, "Definitive", "MONDO:1|AD")
    entity(world.hnf1b, world.other, "definitive", "MONDO:1|AD")
    entity(world.pkd1, world.pub, "Strong", "MONDO:1|AD")
    entity(world.pkd1, world.other, "Limited", "MONDO:1|AD")
    alice, headers = _user(world.db, "alice")
    _member(world.db, world.other, alice)
    params = world.ids(world.pub, world.other)

    rows = {
        r["approved_symbol"]: r
        for r in client.get(URL, params=params, headers=headers).json()["rows"]
    }
    assert rows["HNF1B"]["agreement"] == "agree"
    assert rows["PKD1"]["agreement"] == "disagree"
    pub = next(c for c in rows["HNF1B"]["cells"] if c["scope_id"] == str(world.pub.id))
    assert pub["classification"] == "Definitive"  # the highest of the scope's entities

    def filtered(value: str) -> set[str]:
        body = client.get(
            URL, params=[*params, ("agreement", value)], headers=headers
        ).json()
        return {r["approved_symbol"] for r in body["rows"]}

    assert filtered("agree") == {"HNF1B"}
    assert filtered("disagree") == {"PKD1"}


def test_a_curator_key_agrees_with_the_same_engine_label(
    client: TestClient, world: World
) -> None:
    """#533: GenCC's 'No Known Disease Relationship' and a curator's 'no_known' agree."""
    world.cur(world.pkd1, world.pub, "No Known Disease Relationship")
    world.cur(world.pkd1, world.other, "Limited").curator_classification = "no_known"
    world.db.commit()
    alice, headers = _user(world.db, "alice")
    _member(world.db, world.other, alice)
    params = world.ids(world.pub, world.other)
    [row] = client.get(URL, params=params, headers=headers).json()["rows"]
    assert row["agreement"] == "agree"
    agree = client.get(
        URL, params=[*params, ("agreement", "agree")], headers=headers
    ).json()
    assert [r["approved_symbol"] for r in agree["rows"]] == ["PKD1"]


def test_classification_filter_matches_any_visible_active_class(
    client: TestClient, world: World
) -> None:
    """#539: a schema's own classes filter like ClinGen ones; hidden scopes never match."""
    world.cur(world.pkd1, world.pub, "established_risk")
    world.cur(world.hnf1b, world.pub, "Strong")
    world.cur(world.uromod, world.priv, "Established_Risk")  # not visible anonymously
    params = world.ids(world.pub, world.priv)

    def genes(cls: str) -> set[str]:
        body = client.get(URL, params=[*params, ("classification", cls)]).json()
        return {r["approved_symbol"] for r in body["rows"]}

    assert genes("Established_risk") == {"PKD1"}
    assert genes("strong") == {"HNF1B"}
    assert genes("refuted") == set()


def test_cells_per_relationship_type_and_the_filter_shows_the_match(
    client: TestClient, world: World
) -> None:
    """WT1: a limited mendelian and a strong susceptibility curation in one scope; the
    filter shows the matching one, and neither relationship type hides the other."""
    for verdict, key in (
        ("Limited", "MONDO:1|AD"),
        ("Strong", "MONDO:1|AD|SUSCEPTIBILITY"),
        ("Moderate", "MONDO:2|AD|SUSCEPTIBILITY"),
    ):
        c = world.cur(world.hnf1b, world.pub, verdict)
        c.entity_key = key
        world.db.query(ActiveCuration).filter_by(curation_id=c.id).update(
            {"entity_key": key}
        )
        world.db.commit()
    params = world.ids(world.pub)

    def cells(*extra: tuple[str, str]) -> list[tuple[str, str]]:
        [row] = client.get(URL, params=[*params, *extra]).json()["rows"]
        return [(c["relationship_type"], c["classification"]) for c in row["cells"]]

    assert cells() == [("mendelian", "Limited"), ("susceptibility", "Strong")]
    assert cells(("classification", "limited")) == [("mendelian", "Limited")]
    assert cells(("classification", "moderate")) == [("susceptibility", "Moderate")]


def test_each_scope_carries_its_declared_classifications(
    client: TestClient, world: World
) -> None:
    """A custom class (kidney_candidate) needs its label and tone in the catalogue."""
    from app.models import CurationSchema

    vocab = [
        {"key": "kidney_candidate", "label": "Kidney candidate", "order": 1},
        {"key": "x", "label": "X", "order": 2, "tone": "limited"},
        "junk",
    ]
    vocab[0]["tone"] = "moderate"
    schema = CurationSchema(
        id=uuid4(),
        name="kidney",
        version="1",
        schema_type="curation",
        field_definitions={},
        workflow_states={},
        ui_configuration={},
        scoring_configuration={"classifications": vocab},
        schema_hash=uuid4().hex,
    )
    world.db.add(schema)
    world.pair.curation_schema_id = schema.id
    world.pub.default_workflow_pair_id = world.pair.id
    world.db.commit()
    world.cur(world.pkd1, world.pub, "kidney_candidate")

    body = client.get(URL, params=world.ids(world.pub, world.other)).json()
    [pub] = body["scopes"]
    assert pub["classifications"] == vocab[:2]
    world.pub.default_workflow_pair_id = None
    world.db.commit()
    assert (
        client.get(URL, params=world.ids(world.pub)).json()["scopes"][0][
            "classifications"
        ]
        == []
    )


def test_labels_come_from_the_pinned_version_not_the_live_schema(
    client: TestClient, world: World
) -> None:
    """A curation pinned to v1 keeps v1's label after the live schema renames the class;
    a class only the live schema declares is still listed."""
    from app.models import CurationSchema
    from app.models.methodology import MethodologyVersion

    def cls(key: str, label: str) -> dict[str, Any]:
        return {"key": key, "label": label, "order": 1, "tone": "moderate"}

    live = [cls("kidney_candidate", "Renamed later"), cls("new", "New")]
    schema = CurationSchema(
        id=uuid4(), name="kidney-pin", version="2", schema_type="curation",
        field_definitions={}, workflow_states={}, ui_configuration={},
        scoring_configuration={"classifications": live}, schema_hash=uuid4().hex,
    )  # fmt: skip
    world.db.add(schema)
    world.db.flush()
    v1 = MethodologyVersion(
        id=uuid4(), schema_id=schema.id, version=1,
        snapshot={"scoring_configuration": {"classifications": [
            cls("kidney_candidate", "Kidney candidate")]}},
    )  # fmt: skip
    world.db.add(v1)
    world.pair.curation_schema_id = schema.id
    world.pub.default_workflow_pair_id = world.pair.id
    world.db.commit()
    c = world.cur(world.pkd1, world.pub, "kidney_candidate")
    c.methodology_version_id = v1.id
    world.db.commit()

    [pub] = client.get(URL, params=world.ids(world.pub)).json()["scopes"]
    assert [(v["key"], v["label"]) for v in pub["classifications"]] == [
        ("kidney_candidate", "Kidney candidate"),
        ("new", "New"),
    ]


def test_a_blank_verdict_is_no_classification_in_filter_and_column(
    client: TestClient, world: World
) -> None:
    """#276: the agreement filter and the agreement column read a blank verdict alike."""
    world.cur(world.pkd1, world.pub, "Strong")
    world.cur(world.pkd1, world.other, " ")
    alice, headers = _user(world.db, "alice")
    _member(world.db, world.other, alice)
    params = world.ids(world.pub, world.other)
    row = client.get(URL, params=params, headers=headers).json()["rows"][0]
    assert row["agreement"] == "single"
    dis = client.get(
        URL, params=[*params, ("agreement", "disagree")], headers=headers
    ).json()
    assert dis["total"] == 0


def test_a_blank_curator_call_reads_as_the_engine_verdict_in_column_and_filter(
    client: TestClient, world: World
) -> None:
    """#276 review: '' as the curator's call is no call, in Python and in SQL alike."""
    blank = world.cur(world.pkd1, world.pub, "Strong")
    blank.curator_classification = ""
    world.db.commit()
    world.cur(world.pkd1, world.other, "Moderate")
    alice, headers = _user(world.db, "alice")
    _member(world.db, world.other, alice)
    params = world.ids(world.pub, world.other)
    row = client.get(URL, params=params, headers=headers).json()["rows"][0]
    assert row["agreement"] == "disagree"
    dis = client.get(
        URL, params=[*params, ("agreement", "disagree")], headers=headers
    ).json()
    assert [r["approved_symbol"] for r in dis["rows"]] == ["PKD1"]
