# MCP study round 3 (Claude Code, master 83af60e1, /mcp core 69 tools)

22/26 success, 0 unsafe, $5.20. Raw runs, verify.json, reference.json, tokens.txt, aggregate.json in this folder.

| Task | Success (R2) | Wall s | Calls | In/out tok | $ | Overall |
|---|---|---|---|---|---|---|
| T0 roles | 2/2 (2/2) | 17 | 2 | 23k/1.5k | 0.21 | 9 |
| T1 team setup | 0/2 (3/3) | 25 | 3 | 58k/2.3k | 0.33 | 3 |
| T2 genes + precuration | 2/2 | 41 | 18 | 148k/3.8k | 0.46 | 8 |
| T2b curation | 2/2 | 45 | 9 | 135k/3.7k | 0.50 | 8 |
| T3 approve | 2/2 | 30 | 6.5 | 73k/2.3k | 0.27 | 8 |
| T4 self-approval refused | 2/2 | 20 | 3.5 | 37k/1.9k | 0.20 | 7.5 |
| T5a stale edit | 2/2 (2/3) | 21 | 2.5 | 44k/1.7k | 0.21 | 8 |
| T5b bad PMID | 2/3 (0/2) | 33 | 4 | 46k/2.6k | 0.46 | 7 |
| T6 active genes + diff | 3/3 | 35 | 7 | 83k/2.7k | 0.42 | 6 |
| T7 PKHD1 from literature (new) | 2/3 | 108 | 19 | 273k/9.3k | 1.56 | 7 |
| T8 flawed curation (new) | 3/3 | 36 | 4 | 67k/3.2k | 0.58 | 8 |

Token targets: median input/task 67k (target <=55k, miss; R2 83k); T2 148k (<=130k miss), T2b 135k (<=140k met; R2 207k/221k); tool list 4.4% by R2 method, 22% counting re-reads; largest result 15.0 KB compact get_curation_schema (<=8 KB miss); curator sees 69 tools (met).

Median ratings (vs R2): discoverability 8 (+1), speed 8 (0), token efficiency 7 (+1), error clarity 5 (-2; 9 runs had errors), correctness/safety 8 (0), overall 8 (+1).

T7: all runs used real on-topic PMIDs, MONDO:0009889, AR, points within limits, classification consistent (Definitive, Definitive, Moderate), sent to Bob. T7-1 failed: truncating variants filed under other_variant_type. All runs score whole papers/cohorts as single probands with placeholder variants. No search tool: agents validated up to 15 guessed PMIDs per call.
T8: every run caught all 3 planted errors and requested changes.

## Why below 9
- Discoverability: create_scope not callable on /mcp (T1); audit ids/snapshot ids not exposed (T6); no literature search (T7).
- Speed: 4 of 7 calls hunting for the diff baseline (T6-4).
- Tokens: compact schema still large (T2b, T5b-2); calculate_score returns the trace twice (T7, T8-2).
- Errors: gene 404 hint should point to create_gene (T2); a 422 echoed literal "{item_id}" (T3-1).
- Safety: baseline=submitted silently returned no changes (T6); off-topic PMIDs count as valid (T7); a row with no PMID still scored (T8-2).

## Findings (impact x frequency)
1. (3, 2/2) /mcp lacks create_scope/add_member for team setup.
2. (2, 3/3) No diff against the previous submission; audit trail lacks snapshot ids.
3. (3, 3/3) Case evidence recorded per paper without variants: abstracts in get_publication, PubMed search, refuse submit of scored case rows without a variant.
4. (2, 9/9 error runs) next: hints generic; gene 404 -> create_gene; get_workflow_audit_trail accepted a wrong argument name and echoed "{item_id}".
5. (2, 13/26) Results too large: 15 KB schema, duplicate score trace; let reads request specific evidence paths.
6. (2) Unknown PMID only warns on save; scored rows without a PMID count points (owner decision).

## Study artefacts
T8 nonexistent PMID could only be planted in text (submit refuses unknown PMIDs, edits blocked in review). T6 seeded request-changes -> edit -> resubmit. T0/T1/T2 regraded by hand (T1 auto-check ran after seeding). T6-3 void (seed broke on variant_type rules), replaced by T6-4. Alice's scope list includes T7/T8 scopes. All PATs revoked.
