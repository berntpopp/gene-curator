"""Owner decision 2026-10-27, cited evidence only: a row that scores points needs a PMID, and a
case-level row also a variant; otherwise it scores 0 and is listed in breakdown.excluded."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.models import CurationNew
from app.scoring import clingen, point_model
from app.scoring.case_rows import case_row_warnings, is_variant
from app.scoring.clingen import ClinGenEngine
from app.services.evidence_ids import score_scorable

pytestmark = pytest.mark.unit

AD = "genetic_evidence.case_level.autosomal_dominant_or_x_linked"
AR = "genetic_evidence.case_level.autosomal_recessive"


def _case(ad: list[dict], ar: list[dict] | None = None) -> dict:
    return {
        "genetic_evidence": {
            "case_level": {
                "autosomal_dominant_or_x_linked": {"predicted_or_proven_null": ad},
                "autosomal_recessive": {"predicted_or_proven_null": ar or []},
            }
        }
    }


def test_case_rows_need_a_pmid_and_a_variant() -> None:
    evidence = _case(
        [
            {"pmid": "1", "variant": "c.1A>T", "proband_counted_points": 2},
            {"variant": "c.2A>T", "proband_counted_points": 2},
            {"pmid": "3", "variant": " ", "proband_counted_points": 2},
            {"pmid": "4", "proband_counted_points": 0},  # scores nothing: not listed
        ],
        [{"pmid": "5", "variant_1": "c.5A>T", "proband_counted_points": 1}],
    )
    result = ClinGenEngine().calculate_scores(evidence, {})
    assert result.total_score == 3
    assert result.evidence_breakdown["excluded"] == [
        {
            "path": f"{AD}.predicted_or_proven_null[1]",
            "field": "pmid",
            "reason": "no_pmid",
        },
        {
            "path": f"{AD}.predicted_or_proven_null[2]",
            "field": "variant",
            "reason": "no_variant",
        },
    ]


def test_ar_row_without_variant_names_variant_1() -> None:
    evidence = _case([], [{"pmid": "5", "proband_counted_points": 1, "variant_1": ""}])
    result = ClinGenEngine().calculate_scores(evidence, {})
    assert result.total_score == 0
    assert result.evidence_breakdown["excluded"] == [
        {
            "path": f"{AR}.predicted_or_proven_null[0]",
            "field": "variant_1",
            "reason": "no_variant",
        }
    ]


def test_default_points_without_a_pmid_score_nothing() -> None:
    evidence = {
        "experimental_evidence": {
            "function": {"biochemical_function": [{"rationale": "binds X"}]}
        }
    }
    result = ClinGenEngine().calculate_scores(evidence, {})
    assert result.total_score == 0
    assert result.evidence_breakdown["excluded"][0]["reason"] == "no_pmid"


def test_clean_evidence_has_no_excluded_key() -> None:
    evidence = _case([{"pmid": "1", "variant": "c.1A>T", "proband_counted_points": 2}])
    breakdown = ClinGenEngine().calculate_scores(evidence, {}).evidence_breakdown
    assert "excluded" not in breakdown


def test_legacy_flat_case_rows_need_a_pmid_and_a_variant() -> None:
    row = {"evidence_category": "case_level", "variant_type": "missense"}
    evidence = {
        "genetic_evidence": [
            {**row, "proband_count": 1},
            {**row, "proband_count": 1, "pmid": "1"},
            {**row, "proband_count": 1, "pmid": "2", "variant": "c.1A>T"},
        ]
    }
    result = ClinGenEngine().calculate_scores(evidence, {})
    assert result.total_score == pytest.approx(0.1)
    assert [
        (e["path"], e["reason"]) for e in result.evidence_breakdown["excluded"]
    ] == [
        ("genetic_evidence[0]", "no_pmid"),
        ("genetic_evidence[1]", "no_variant"),
    ]


def test_unknown_pmids_join_the_excluded_rows_with_a_code() -> None:
    evidence = _case(
        [
            {"pmid": "99", "variant": "c.1A>T", "proband_counted_points": 2},
            {"pmid": "abc", "variant": "c.1A>T", "proband_counted_points": 2},
            {"variant": "c.1A>T", "proband_counted_points": 2},
        ]
    )
    result = score_scorable(ClinGenEngine(), {}, evidence, {"99"})
    assert result.total_score == 0
    assert [e["reason"] for e in result.evidence_breakdown["excluded"]] == [
        "unknown_pmid",
        "unknown_pmid",
        "no_pmid",
    ]


@pytest.fixture
def uncited_off(monkeypatch: pytest.MonkeyPatch) -> None:
    """Points arithmetic of fixtures written before the policy (golden parity, caps)."""
    for module in (clingen, point_model):
        monkeypatch.setattr(module, "uncited", lambda row, case_level: None)


def test_placeholder_variants_score_nothing() -> None:
    placeholder = "PKHD1 truncating variant (as reported in publication)"
    evidence = _case(
        [
            {"pmid": "1", "variant": placeholder, "proband_counted_points": 2},
            {
                "pmid": "2",
                "variant": "NM_138694.4:c.107C>T",
                "proband_counted_points": 1,
            },
        ],
        [{"pmid": "3", "variant_1": "rs137852944", "proband_counted_points": 1}],
    )
    result = ClinGenEngine().calculate_scores(evidence, {})
    assert result.total_score == 2
    assert result.evidence_breakdown["excluded"] == [
        {
            "path": f"{AD}.predicted_or_proven_null[0]",
            "field": "variant",
            "reason": "placeholder_variant",
        }
    ]
    assert (
        f"{AD}.predicted_or_proven_null[0].variant: {placeholder!r} is not a variant"
        in (" ".join(result.warnings))
    )


@pytest.mark.parametrize(
    ("text", "real"),
    [
        ("c.107C>T", True),
        ("NM_138694.4:c.107C>T (p.Thr36Met)", True),
        ("p.(Arg12Ter)", True),
        ("rs137852944", True),
        ("chr6:51524409", True),
        ("6-51524409-G-A", True),
        ("exon 32 deletion", True),
        ("exons 30-32 deletion", True),
        ("whole gene deletion", True),
        ("whole-gene duplication", True),
        ("chr6:51,775,000 G>A", True),
        ("arr[GRCh37] 6p12.3(51480000_51960000)x1", True),
        ("del(6)(p12.3)", True),
        ("truncating variant", False),
        ("see p.5 of paper", False),
        ("(c.f. Table 2)", False),
        ("families 1-123", False),
        ("X-100 cohort", False),
        ("p.Arg12*", True),
        ("c.-12A>G", True),
        ("as reported, e.g. nonsense", False),
        ("", False),
        (12345, False),
    ],
)
def test_is_variant(text: object, real: bool) -> None:
    assert is_variant(text) is real


def _warn(table: str, row: dict, moi: str = "autosomal_dominant_or_x_linked") -> list:
    tables = {moi: {table: [{"pmid": "1", "proband_counted_points": 1, **row}]}}
    return case_row_warnings({"genetic_evidence": {"case_level": tables}})


def test_misfiled_variants_and_cohort_rows_warn_with_paths() -> None:
    other = f"{AD}.other_variant_type[0]"
    assert _warn("other_variant_type", {"variant": "c.100_101del (p.Gly34fs)"}) == [
        f"{other}: variant looks null (frameshift, stop, canonical splice or "
        "deletion); record it under predicted_or_proven_null"
    ]
    assert _warn("other_variant_type", {"variant": "c.100+1G>A"})
    assert _warn("other_variant_type", {"variant": "c.100C>T (p.Arg34Cys)"}) == []
    assert _warn("predicted_or_proven_null", {"variant": "c.100C>T p.Arg34Cys"}) == [
        f"{AD}.predicted_or_proven_null[0]: variant looks missense; record it under "
        "other_variant_type"
    ]
    assert _warn("predicted_or_proven_null", {"variant": "c.100C>T (p.Arg34Ter)"}) == []
    # AR null + other belongs in other_variant_type; two nulls do not
    ar = {"variant_1": "c.1A>T (p.Lys1Ter)", "variant_2": "c.5C>T (p.Arg2Cys)"}
    assert _warn("other_variant_type", ar, "autosomal_recessive") == []
    ar["variant_2"] = "c.9del (p.Gly3fs)"
    assert _warn("other_variant_type", ar, "autosomal_recessive")
    cohort = _warn(
        "predicted_or_proven_null",
        {"variant": "c.1A>T", "proband_label": "12 patients"},
    )
    assert cohort == [
        f"{AD}.predicted_or_proven_null[0].proband_label: names a cohort; record one "
        "row per described proband"
    ]


def test_one_paper_as_many_probands_warns() -> None:
    rows = [{"pmid": "7", "variant": f"c.{i}A>T"} for i in range(1, 4)]
    warnings = case_row_warnings(_case(rows))
    paths = ", ".join(f"{AD}.predicted_or_proven_null[{i}]" for i in range(3))
    assert warnings == [
        f"PMID 7 is scored as 3 proband rows ({paths}); confirm each is a distinct "
        "proband with its own variant"
    ]
    assert case_row_warnings(_case(rows[:2])) == []


def test_submit_refuses_uncited_scored_rows_by_field_path(
    client: TestClient,
    curator_token: str,
    db_session: Session,
    test_curation: CurationNew,
) -> None:
    test_curation.evidence_data = _case(
        [
            {"variant": "c.1A>T", "proband_counted_points": 2},
            {"pmid": "2", "variant": "truncating", "proband_counted_points": 2},
            {"pmid": "3", "proband_counted_points": 2},
            {"pmid": "4", "variant": "c.4A>T", "proband_counted_points": 2},
        ]
    )
    db_session.commit()
    r = client.post(
        f"/api/v1/curations/{test_curation.id}/submit",
        json={"lock_version": test_curation.lock_version},
        headers={"Authorization": f"Bearer {curator_token}"},
    )
    assert r.status_code == 422, r.text
    rows = f"{AD}.predicted_or_proven_null"
    assert [(e["path"], e["message"][:30]) for e in r.json()["detail"]["errors"]] == [
        (f"{rows}[0].pmid", "Scored row needs a PMID"),
        (f"{rows}[1].variant", "Scored case-level row needs a "),
        (f"{rows}[2].variant", "Scored case-level row needs a "),
    ]
    db_session.refresh(test_curation)
    assert test_curation.workflow_stage == "curation"


def test_recompute_keeps_active_results_until_resubmitted(
    db_session: Session,
    test_curation: CurationNew,
    test_user_admin: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import recompute_scores
    from app.services.recompute_scores import recompute_all_scores

    test_curation.evidence_data = _case(
        [{"variant": "c.1A>T", "proband_counted_points": 2}]
    )
    test_curation.computed_scores = {"total_score": 2.0}
    logged: list[dict] = []
    monkeypatch.setattr(
        recompute_scores.logger, "info", lambda msg, **kw: logged.append(kw)
    )
    for status in ("active", "archived"):
        test_curation.status = status
        db_session.commit()
        recompute_all_scores(db_session)
        db_session.refresh(test_curation)
        assert test_curation.computed_scores == {"total_score": 2.0}
        assert logged[-1]["kept_uncited_ids"] == [str(test_curation.id)]
        assert (logged[-1]["kept_uncited"], logged[-1]["unchanged"]) == (1, 0)
    test_curation.status = "draft"
    db_session.commit()
    recompute_all_scores(db_session)
    db_session.refresh(test_curation)
    assert test_curation.computed_scores["total_score"] == 0
