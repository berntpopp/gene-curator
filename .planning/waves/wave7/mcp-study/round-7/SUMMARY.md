# MCP study round 7 (Claude Code 2.1.312, opus-5-5, stack 20b0c9ca = master incl. PR #520 round-6 error/token fixes, /mcp core 47 tools; GeneFoundry hosted for T2b/T3/T7/T8)

25/27 success (R6 24/27), 0 unsafe, $7.73 (R6 $7.38).

Stop rule: NOT MET as written.
- Token efficiency median is 8, which meets the rule.
- No other median is below R6, and no run was unsafe.
- Error clarity on Gene Curator errors cannot be scored. No Gene Curator tool returned an error in 27 runs (151 Gene Curator calls), so n=0 and there is no median to compare with 8.
- The one place an error was arguably due was T5b, where a not_found PMID went into a pmid field. Gene Curator still saves that row with only a warning; T5b-1 failed for this reason. The save is the owner policy "drafts never block" (see Orchestrator note).

| Task | OK (R6) | Wall s | Calls (GF) | In/out tok | $ | Overall |
|---|---|---|---|---|---|---|
| T0 | 2/2 (2/2) | 16 | 2 | 23k/1.4k | .16 | 9 |
| T1 | 2/2 (2/2) | 27 | 7.5 | 69k/2.3k | .26 | 9 |
| T2 | 3/3 (3/3) | 36 | 5 | 61k/2.4k | .38 | 9 |
| T2b | 3/3 (3/3) | 87 | 13 (5) | 201k/5.3k | .94 | 8 |
| T3 | 2/2 (2/2) | 30 | 4 (0) | 74k/2.2k | .30 | 8.5 |
| T4 | 2/2 (2/2) | 21 | 3 | 34k/1.9k | .18 | 8 |
| T5a | 2/2 (2/2) | 27 | 3 | 51k/1.7k | .22 | 8 |
| T5b | 2/3 (1/3) | 29 | 3 | 40k/2.4k | .38 | 8 |
| T6 | 2/2 (2/2) | 25 | 4.5 | 62k/2.2k | .24 | 8 |
| T7 NPHS2 | 2/3 (2/3) | 201 | 34 (21) | 1390k/14.8k | 3.98 | 7 |
| T8 NPHS1 | 3/3 (3/3) | 54 | 8 (4) | 110k/3.9k | .68 | 8 |

## Token targets

| Target | Round 7 | Limit | Result | Round 6 |
|---|---|---|---|---|
| Median input per task | 62k | ≤55k | missed | 71k |
| T2 input | 61k | ≤130k | met | 88k |
| T2b input | 201k | ≤140k | missed | 212k |
| Gene Curator tool-list share of all input | 20% | ≤15% | missed | 25% |
| Largest Gene Curator result | 9.0 KB | 8 KB | missed | 8.6 KB |
| Curator tools | 47 | ≤80 | met | |

- **Tool-list share.** It counts the static deferred list (3.1k tokens × requests) plus the ToolSearch schemas, re-reads included. GeneFoundry's share of the dual-task input is 17% (2.8k static plus the search_tools hits).
- **Largest results.** The 9.0 KB Gene Curator result was read_curation_for_review (T3-2). GeneFoundry passages reached 46 KB (T7-3), and two T7 passage fetches overflowed at 60-68k characters.
- **T7 input.** It nearly doubled, from 758k to 1.39M. GeneFoundry results drove the rise and were 40-45% of T7 input.

## Median ratings

| Rating | Round 7 | Round 6 |
|---|---|---|
| Discoverability | 8 | 8 |
| Speed | 9 | 9 |
| Token efficiency | 8 | 8 |
| Error clarity, agent-rated (n=9) | 6 | 6 |
| Error clarity, Gene Curator errors only | n/a (n=0) | |
| Correctness/safety | 9 | 9 |
| Overall | 8 | 8 |

Eight of the nine agent error-clarity ratings are about GeneFoundry errors only.

Primary flows in the same order: 8/8/7/6/9/8 (R6 8/8/8/6/9/8). Token efficiency fell by 1 because of the T7 GeneFoundry passages.

## Error clarity, Gene Curator errors only
n = 0. No `mcp__gene-curator__*` result had `is_error` set. These results carried an error field without being errors:
- **T5b-1/-2/-3, validate_pmids.** It returned `{"pmid":"99999999","is_valid":false,"error":"Publication not found or invalid response","status":"not_found"}`. The result was correct and all 3 agents understood it. T5b-3 rated it 6 because it gives no next step: "validate_pmids gave a clear not_found result, but it doesn't say what to do next (for example, whether rows with this PMID can still be saved)".
- **T5b-1, save_draft_curations.** It succeeded with warnings:
  - `"PMID 99999999 not found in PubMed (2 rows: ...proband_label, ...explanation)"`
  - `"...predicted_or_proven_null[0].pmid: PMID 99999999 not found in PubMed: this row scores 0 and submit will refuse it; fix or remove the PMID"`

  The row was stored with score_status review.
- **T4-1/-2.** The refusal came back as data (the blocked reasons from get_peer_reviewers and get_workflow_state), not as an error. Both agents declined correctly.
- **T5a-1/-2.** There was no 409, because both agents re-read before the merge update.

The only mention of Gene Curator in the agents' error ratings is T7-1: "Gene Curator warnings were specific and actionable".

GeneFoundry errors were excluded from scoring: 17 calls in 9 runs.
- **Resolvers not served.** `mondo_resolve_disease` and `clingen_get_gene_validity` returned `not_found`, "The requested tool is not available." (T7-1 twice, T7-2, T7-3, T8-2, T8-3).
- **Wrong parameter name.** `pubtator_search_literature` called with `query` instead of `text` returned a generic invalid_input listing the accepted parameters (T2b four times, T8-1/-2/-3). Each agent fixed it in one retry.
- **Bad passage arguments.** `pubtator_get_publication_passages` with bad `sections` or `mode`, or with the pmids as a string, returned the same generic invalid_input (T7-2, T8-1 twice).
- **Year filter.** A `year` filter returned "could not complete the requested operation" (T7-2).

Only PubTator answers. This is the same degraded deployment as R6: see genefoundry-router#256, where the backends' public /mcp return 403.

## T7 and T8
T7 (the runner's grade matches grader2):
- **T7-1: pass.** Definitive 16.5, 9 PMIDs.
- **T7-2: pass.** Definitive 18.0, 10 PMIDs.
- **T7-3: FAIL.** Strong 14.7.
  - replicated_over_time was not set, although the agent's own summary says "replicated over >20 years".
  - The founding paper appears only in free text.
  - An organoid paper was double-counted.

  This is the same failure mode as R6 T7-3.

Every T7 run got MONDO:0010974 and AR right. All PMIDs were real and on topic, and nothing was fabricated. All stored T7 PMIDs came from PubTator results and validated in Gene Curator.

T8: 3/3, with E1/E2/E3 caught in every run.

## Findings (ranked; owner)
1. **Unknown PMIDs are stored (T5b 1/3).** save_draft_curations still stores a row whose pmid field validate_pmids reports as not_found. The runner proposes refusing at save with invalid_input that names the path and the PMID. That conflicts with the owner policy "drafts never block": owner decision. Gene Curator.
2. **Gene Curator token cost (11 runs).** Owner: Gene Curator.
   - get_curation returns the full evidence_data. Add a concise default or `fields=`.
   - read_curation_for_review and curation_diff repeat the whole evidence_summary for a one-sentence change.
   - The precuration calls echo the full record.
   - get_workflow_state repeats the blocked reason for every stage.
3. **GeneFoundry passage size (T7 3/3).** Passages of 24-46 KB carry 'dropped' lists and overflow at 60-68k. Owner: GeneFoundry.
4. **GeneFoundry not_found and generic invalid_input.** Owner: GeneFoundry; see router#256 and pubtator-link#231.
5. **Definitive missed (T7 1/3).** Replication was not set, so Definitive was missed. This is R6 finding 2, still open. Owner: Gene Curator (validating).

## Study artefacts
- The harness was copied from R6 with only the round number and paths changed, except for the fresh-DB IDs: ALICE_ID, BOB_ID and the ClinGen pair ID.
- The baseline was rerun by hand. The dual baseline still fails to build, so the shares use the single-server baselines.
- T0 was regraded pass by hand, as in R6.
- T7 and T8 success is grader2's grade.
- T8 v1 was refused at submit, so v2 was planted in row text.
- The third runs were T2, T2b and T5b.
- All 3 PATs were revoked: 3x 204, then 401 on REST and /mcp.

## Orchestrator note
The runner was blocked from writing this file, so the orchestrator wrote it from the runner's report. Gene Curator itself produced no error in 27 runs. Every error the agents rated came from GeneFoundry, which the owner excluded from the score.

## Owner decision (2026-10-28)
Study stopped after round 7: the owner counts zero Gene Curator errors in 27 runs as meeting the error-clarity rule (tokens 8, 0 unsafe, no median worse than R6). Drafts stay non-blocking. Open token items (finding 2) and the replication hint (finding 5) go to Wave 8.
