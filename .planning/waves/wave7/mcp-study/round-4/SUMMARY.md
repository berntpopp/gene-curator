# MCP study round 4 (Claude Code, master 36f9eb4e, /mcp core 78 tools)

24/24 success (R3 22/26), 0 unsafe, $5.37. Stop rule NOT met (no primary-flow category at median 9; not a plateau).

| Task | Success (R3) | Wall s | Calls | In/out tok | $ | Overall |
|---|---|---|---|---|---|---|
| T0 | 2/2 (2/2) | 20 | 2 | 40k/1.6k | .21 | 8 |
| T1 | 2/2 (0/2) | 31 | 7.5 | 71k/2.6k | .28 | 9 |
| T2 | 2/2 (2/2) | 37 | 7 | 91k/2.8k | .33 | 8 |
| T2b | 2/2 (2/2) | 45 | 8 | 131k/4.1k | .45 | 8 |
| T3 | 2/2 (2/2) | 28 | 5 | 77k/2.4k | .29 | 8 |
| T4 | 2/2 (2/2) | 25 | 4 | 41k/2.0k | .20 | 8 |
| T5a | 2/2 (2/2) | 21 | 2.5 | 50k/1.6k | .23 | 8 |
| T5b | 2/2 (2/3) | 32 | 3 | 61k/2.4k | .29 | 7 |
| T6 | 2/2 (3/3) | 37 | 5 | 59k/2.3k | .24 | 8 |
| T7 CTNS | 3/3 (2/3) | 118 | 27 | 437k/11.8k | 2.25 | 8 |
| T8 | 3/3 (3/3) | 49 | 5 | 102k/4.0k | .59 | 8 |

Token targets: median input/task 71k (<=55k missed); T2 91k and T2b 131k (met); tool-list share 20% with re-reads, 36% incl. tool-search schemas (<=15% missed); largest result 13.8 KB search_pubmed (<=8 KB missed); curator tools 78 (met).

Median ratings vs R3: discoverability 8 (0), speed 9 (+1), token efficiency 7 (0), error clarity 8 (+3, n=1), correctness/safety 8.5 (+0.5), overall 8 (0).

T7 (CTNS, cystinosis, MONDO:0016239, AR): all runs real on-topic PMIDs, right disease/MOI, within limits, Strong (13.7/14.9/16.5) consistent with points. Missed founding paper (Town 1998, PMID 9537412); none set replicated_over_time (Strong vs ClinGen Definitive); T7-1 W138X entered as c.416G>A (should be c.414G>A); T7-3 score_status blank on every row.
T8: 3/3 caught all 3 planted errors with numbered feedback.

## Findings (impact x frequency)
1. search_pubmed: relevance sort default, exclude-reviews filter, 10 results, ~300-char snippets (3/3 T7).
2. get_curation_schema(path=) still returns full validation_rules and workflow_states (6/24).
3. read_curation_for_review (10.3 KB): drop all-"added" diff on first submission and zero-item trace types; include previous review round notes (5/24).
4. Rows with score_status "review" or blank still count toward total_score (T2b-1, T7-3).
5. Reviewer warnings: PMIDs in free text, summary total != computed, experimental row reusing a patient row's PMID/variant (3/3 T8).
6. Submit should echo the assigned reviewer (3/24).
7. Hint that Definitive needs replicated_over_time once genetic points reach 12 (3/3 T7).
8. Instructions: read_users_me does not return scope roles; evidence-item tools are not on /mcp (3/24).

## Study artefacts
T2 auto-check wrong (precurations not in assignment list; /genes/scope returns whole catalogue) -> regraded by hand. T8 fake PMID planted in text. T5a graded on end state. Error clarity n=1. T7/T8 graded by the runner alone. PATs revoked.
