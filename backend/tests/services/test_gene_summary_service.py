"""Behaviour tests for GeneSummaryService on the in-memory SQLite session."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.models import (
    ActiveCuration,
    CurationNew,
    Gene,
    Scope,
    UserNew,
    WorkflowPair,
)
from app.services.gene_summary_service import GeneSummaryService


def _curation(
    db: Session,
    gene: Gene,
    scope: Scope,
    user: UserNew,
    pair: WorkflowPair,
    verdict: str | None,
) -> CurationNew:
    curation = CurationNew(
        id=uuid4(),
        scope_id=scope.id,
        gene_id=gene.id,
        workflow_pair_id=pair.id,
        workflow_stage="curation",
        evidence_data={},
        computed_verdict=verdict,
        approved_at=datetime.now(UTC),  # #613: final once approved
        computed_scores={
            "genetic_evidence_total": 4,
            "experimental_evidence_total": 1,
            "total_score": 5,
            "evidence_items": [{"id": 1}, {"id": 2}],
        },
        created_by=user.id,
    )
    db.add(curation)
    db.commit()
    db.refresh(curation)
    return curation


def _activate(
    db: Session,
    gene: Gene,
    scope: Scope,
    user: UserNew,
    pair: WorkflowPair,
    verdict: str | None,
    *,
    archived: bool = False,
) -> CurationNew:
    curation = _curation(db, gene, scope, user, pair, verdict)
    db.add(
        ActiveCuration(
            gene_id=gene.id,
            scope_id=scope.id,
            curation_id=curation.id,
            archived_at=datetime.now(UTC) if archived else None,
        )
    )
    db.commit()
    return curation


def _scope(db: Session, name: str) -> Scope:
    scope = Scope(
        id=uuid4(),
        name=name,
        display_name=name,
        description=name,
        is_public=False,
        is_active=True,
    )
    db.add(scope)
    db.commit()
    return scope


def test_full_summary_aggregates_active_curations_across_scopes(
    db_session: Session,
    test_gene: Gene,
    test_scope: Scope,
    test_public_scope: Scope,
    test_user_curator: UserNew,
    test_workflow_pair: WorkflowPair,
) -> None:
    _activate(
        db_session,
        test_gene,
        test_scope,
        test_user_curator,
        test_workflow_pair,
        "definitive",
    )
    _activate(
        db_session,
        test_gene,
        test_public_scope,
        test_user_curator,
        test_workflow_pair,
        "limited",
    )
    # Archived link (own scope: one active row per gene+scope) must be ignored.
    _activate(
        db_session,
        test_gene,
        _scope(db_session, "archived-scope"),
        test_user_curator,
        test_workflow_pair,
        "definitive",
        archived=True,
    )

    summary = GeneSummaryService(db_session).get_full_summary(
        test_gene.id, test_user_curator
    )

    assert summary.total_scopes_curated == 2
    assert summary.public_scopes_count == 1
    assert summary.private_scopes_count == 1
    assert summary.classification_summary == {"definitive": 1, "limited": 1}
    assert summary.has_conflicts is True
    assert summary.is_stale is False
    assert summary.last_updated is not None
    assert len(summary.scope_summaries) == 2
    entry = next(s for s in summary.scope_summaries if s.scope_name == "test-scope")
    assert entry.genetic_score == 4
    assert entry.total_score == 5
    assert entry.evidence_count == 2
    assert entry.curator_count == 1


def test_full_summary_consensus_and_no_conflicts(
    db_session: Session,
    test_gene: Gene,
    test_scope: Scope,
    test_public_scope: Scope,
    test_user_curator: UserNew,
    test_workflow_pair: WorkflowPair,
) -> None:
    _activate(
        db_session,
        test_gene,
        test_scope,
        test_user_curator,
        test_workflow_pair,
        "definitive",
    )
    _activate(
        db_session,
        test_gene,
        test_public_scope,
        test_user_curator,
        test_workflow_pair,
        "definitive",
    )

    summary = GeneSummaryService(db_session).get_full_summary(
        test_gene.id, test_user_curator
    )

    assert summary.has_conflicts is False
    assert summary.consensus_classification == "definitive"
    assert float(summary.consensus_confidence or 0) == 1.0


def test_full_summary_handles_missing_verdicts_and_scores(
    db_session: Session,
    test_gene: Gene,
    test_scope: Scope,
    test_user_curator: UserNew,
    test_workflow_pair: WorkflowPair,
) -> None:
    curation = _activate(
        db_session, test_gene, test_scope, test_user_curator, test_workflow_pair, None
    )
    curation.computed_scores = {}
    db_session.commit()

    summary = GeneSummaryService(db_session).get_full_summary(
        test_gene.id, test_user_curator
    )

    assert summary.classification_summary == {"unknown": 1}
    assert summary.consensus_classification == "unknown"
    assert summary.has_conflicts is False
    assert summary.scope_summaries[0].genetic_score == 0
    assert summary.scope_summaries[0].evidence_count == 0

    # a custom point model's sections (genetic, experimental), not ClinGen names
    curation.computed_scores = {"genetic_total": 2, "experimental_total": 6}
    db_session.commit()
    [scope] = (
        GeneSummaryService(db_session)
        .get_full_summary(test_gene.id, test_user_curator)
        .scope_summaries
    )
    assert (scope.genetic_score, scope.experimental_score) == (2, 6)


def test_get_public_summary_computes_missing_summary_and_filters_scopes(
    db_session: Session,
    test_gene: Gene,
    test_scope: Scope,
    test_public_scope: Scope,
    test_user_curator: UserNew,
    test_workflow_pair: WorkflowPair,
) -> None:
    _activate(
        db_session,
        test_gene,
        test_scope,
        test_user_curator,
        test_workflow_pair,
        "definitive",
    )
    _activate(
        db_session,
        test_gene,
        test_public_scope,
        test_user_curator,
        test_workflow_pair,
        "limited",
    )

    public = GeneSummaryService(db_session).get_public_summary(test_gene.id)

    assert public is not None
    assert public.public_scopes_count == 1
    assert [s.scope_name for s in public.scope_summaries] == ["public-scope"]
    # private scopes must not leak into public aggregates
    assert public.classification_summary == {"limited": 1}


def test_get_public_summary_none_without_public_scopes(
    db_session: Session,
    test_gene: Gene,
    test_scope: Scope,
    test_user_curator: UserNew,
    test_workflow_pair: WorkflowPair,
) -> None:
    _activate(
        db_session,
        test_gene,
        test_scope,
        test_user_curator,
        test_workflow_pair,
        "definitive",
    )

    assert GeneSummaryService(db_session).get_public_summary(test_gene.id) is None


def test_curator_count_counts_distinct_creators(
    db_session: Session,
    test_gene: Gene,
    test_scope: Scope,
    test_user_curator: UserNew,
    test_user_admin: UserNew,
    test_workflow_pair: WorkflowPair,
) -> None:
    first = _activate(
        db_session, test_gene, test_scope, test_user_curator, test_workflow_pair, "x"
    )
    first.entity_key = "MONDO:0000001|AD"  # one open curation per entity
    db_session.commit()
    # Second author in the same scope, not the active link.
    _curation(
        db_session, test_gene, test_scope, test_user_admin, test_workflow_pair, "x"
    )

    service = GeneSummaryService(db_session)
    assert service._get_curator_count(test_gene.id, test_scope.id) == 2
    assert service._get_curator_count(uuid4(), test_scope.id) == 0


def test_consensus_and_conflicts_are_per_disease_entity(
    db_session: Session,
    test_gene: Gene,
    test_user_curator: UserNew,
    test_workflow_pair: WorkflowPair,
) -> None:
    """#530: two entities with different verdicts are no conflict and no single consensus;
    the same entity with different verdicts across scopes is a conflict."""
    pub, other = _scope(db_session, "pub-a"), _scope(db_session, "pub-b")
    for s in (pub, other):
        s.is_public = True
    db_session.commit()

    def entity(scope: Scope, verdict: str, key: str) -> None:
        c = _activate(
            db_session, test_gene, scope, test_user_curator, test_workflow_pair, verdict
        )
        c.entity_key = key
        c.evidence_data = {"mondo_id": key.split("|")[0]}
        db_session.query(ActiveCuration).filter_by(curation_id=c.id).update(
            {"entity_key": key}
        )
        db_session.commit()

    entity(pub, "definitive", "MONDO:1|AD")
    entity(pub, "limited", "MONDO:2|AD")
    summary = GeneSummaryService(db_session).get_public_summary(test_gene.id)
    assert summary is not None
    assert len(summary.scope_summaries) == 2
    assert summary.has_conflicts is False
    assert summary.consensus_classification is None

    entity(other, "strong", "MONDO:1|AD")
    summary = GeneSummaryService(db_session).get_public_summary(test_gene.id)
    assert summary is not None and summary.has_conflicts is True
    # W8 round 2: the disagreement names only the entity in conflict, counts scopes
    assert summary.conflict_summary == {"definitive": 1, "strong": 1}
    assert summary.public_scopes_count == 2
    assert {s.mondo_id for s in summary.scope_summaries} == {"MONDO:1", "MONDO:2"}
    full = GeneSummaryService(db_session).get_full_summary(
        test_gene.id, test_user_curator
    )
    assert (full.public_scopes_count, full.conflict_summary) == (
        2,
        {"definitive": 1, "strong": 1},
    )
