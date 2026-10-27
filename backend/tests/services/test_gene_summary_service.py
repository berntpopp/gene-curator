"""Behaviour tests for GeneSummaryService on the in-memory SQLite session."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.models import (
    ActiveCuration,
    CurationNew,
    Gene,
    GeneSummary,
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


def test_compute_summary_without_active_curations_creates_empty_row(
    db_session: Session, test_gene: Gene
) -> None:
    service = GeneSummaryService(db_session)

    summary = service.compute_summary(test_gene.id)
    again = service.compute_summary(test_gene.id)

    assert summary.gene_id == test_gene.id
    assert summary.id == again.id  # reused, not duplicated
    assert db_session.query(GeneSummary).count() == 1


def test_compute_summary_aggregates_active_curations_across_scopes(
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

    summary = GeneSummaryService(db_session).compute_summary(test_gene.id)

    assert summary.total_scopes_curated == 2
    assert summary.public_scopes_count == 1
    assert summary.private_scopes_count == 1
    assert summary.classification_summary == {"definitive": 1, "limited": 1}
    assert summary.has_conflicts is True
    assert summary.is_stale is False
    assert summary.last_computed_at is not None
    assert len(summary.scope_summaries) == 2
    entry = next(s for s in summary.scope_summaries if s["scope_name"] == "test-scope")
    assert entry["genetic_score"] == 4
    assert entry["total_score"] == 5
    assert entry["evidence_count"] == 2
    assert entry["curator_count"] == 1


def test_compute_summary_consensus_and_no_conflicts(
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

    summary = GeneSummaryService(db_session).compute_summary(test_gene.id)

    assert summary.has_conflicts is False
    assert summary.consensus_classification == "definitive"
    assert float(summary.consensus_confidence or 0) == 1.0


def test_compute_summary_handles_missing_verdicts_and_scores(
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

    summary = GeneSummaryService(db_session).compute_summary(test_gene.id)

    assert summary.classification_summary == {"unknown": 1}
    assert summary.consensus_classification == "unknown"
    assert summary.has_conflicts is False
    assert summary.scope_summaries[0]["genetic_score"] == 0
    assert summary.scope_summaries[0]["evidence_count"] == 0


def test_compute_summary_updates_existing_summary_row(
    db_session: Session,
    test_gene: Gene,
    test_scope: Scope,
    test_user_curator: UserNew,
    test_workflow_pair: WorkflowPair,
) -> None:
    service = GeneSummaryService(db_session)
    service.compute_summary(test_gene.id)  # empty summary first
    _activate(
        db_session,
        test_gene,
        test_scope,
        test_user_curator,
        test_workflow_pair,
        "moderate",
    )

    summary = service.compute_summary(test_gene.id)

    assert db_session.query(GeneSummary).count() == 1
    assert summary.consensus_classification == "moderate"


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


def test_get_public_summary_recomputes_stale_summary(
    db_session: Session,
    test_gene: Gene,
    test_public_scope: Scope,
    test_user_curator: UserNew,
    test_workflow_pair: WorkflowPair,
) -> None:
    service = GeneSummaryService(db_session)
    service.compute_summary(test_gene.id)  # no curations yet
    _activate(
        db_session,
        test_gene,
        test_public_scope,
        test_user_curator,
        test_workflow_pair,
        "strong",
    )
    service.mark_stale(test_gene.id)

    public = service.get_public_summary(test_gene.id)

    assert public is not None
    assert public.consensus_classification == "strong"


def test_mark_stale_flags_existing_summary_and_tolerates_missing(
    db_session: Session, test_gene: Gene
) -> None:
    service = GeneSummaryService(db_session)
    service.mark_stale(test_gene.id)  # no row: logs a warning, no error

    service.compute_summary(test_gene.id)
    service.mark_stale(test_gene.id)

    row = (
        db_session.query(GeneSummary).filter(GeneSummary.gene_id == test_gene.id).one()
    )
    assert row.is_stale is True


def test_curator_count_counts_distinct_creators(
    db_session: Session,
    test_gene: Gene,
    test_scope: Scope,
    test_user_curator: UserNew,
    test_user_admin: UserNew,
    test_workflow_pair: WorkflowPair,
) -> None:
    _activate(
        db_session, test_gene, test_scope, test_user_curator, test_workflow_pair, "x"
    )
    # Second author in the same scope, not the active link.
    _curation(
        db_session, test_gene, test_scope, test_user_admin, test_workflow_pair, "x"
    )

    service = GeneSummaryService(db_session)
    assert service._get_curator_count(test_gene.id, test_scope.id) == 2
    assert service._get_curator_count(uuid4(), test_scope.id) == 0


def test_read_summaries_do_not_write_cache(
    db_session: Session,
    test_gene: Gene,
    test_public_scope: Scope,
    test_user_curator: UserNew,
    test_workflow_pair: WorkflowPair,
) -> None:
    """#377: anonymous and member GETs compute in memory; only recompute writes."""
    _activate(
        db_session,
        test_gene,
        test_public_scope,
        test_user_curator,
        test_workflow_pair,
        "strong",
    )
    service = GeneSummaryService(db_session)

    assert service.get_public_summary(test_gene.id) is not None
    assert service.get_full_summary(
        test_gene.id, test_user_curator
    ).total_scopes_curated
    assert db_session.query(GeneSummary).count() == 0


def test_compute_summary_retries_after_concurrent_insert(
    db_session: Session, test_gene: Gene, monkeypatch: pytest.MonkeyPatch
) -> None:
    """#377: a concurrent first insert (unique gene_id) must not surface as a 500."""
    real_commit = db_session.commit
    calls = {"n": 0}

    def racing_commit() -> None:
        calls["n"] += 1
        if calls["n"] == 1:
            db_session.rollback()  # pretend another request inserted the row first
            db_session.add(GeneSummary(gene_id=test_gene.id))
            real_commit()
            raise IntegrityError("INSERT", {}, Exception("duplicate gene_id"))
        real_commit()

    monkeypatch.setattr(db_session, "commit", racing_commit)

    summary = GeneSummaryService(db_session).compute_summary(test_gene.id)

    assert summary.gene_id == test_gene.id
    assert db_session.query(GeneSummary).count() == 1
