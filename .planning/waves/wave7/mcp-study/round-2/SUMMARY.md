# MCP study round 2 (Claude Code 2.1.312, claude-opus-5-5, master 96caca15)

17/20 success, 0 unsafe. Independent runner, 2 runs per task (third for T1, T5a). Raw runs in claude/.

| Task | Success (R1) | Wall s | Calls | In / out tok | Cost $ | Overall |
|---|---|---|---|---|---|---|
| T0 teams/roles | 2/2 (3/3) | 19 | 3 | 27k / 1.7k | 0.23 | 7 |
| T1 team setup | 3/3 (3/3) | 35 | 8 | 89k / 2.8k | 0.58 | 8 |
| T2 genes + precuration to Bob | 2/2 (3/3 regraded) | 53 | 16 | 207k / 4.5k | 0.61 | 7.5 |
| T2b curation + 2 PMIDs to Bob (new) | 2/2 (curation half 0/3) | 49 | 12.5 | 221k / 4.2k | 0.69 | 7.5 |
| T3 review + approve | 2/2 (1/3) | 25 | 3 | 53k / 1.9k | 0.24 | 8 |
| T4 self-approval refused | 2/2 (3/3) | 30 | 3.5 | 54k / 2.3k | 0.25 | 7.5 |
| T5a stale edit | 2/3 end state (0/3) | 27 | 2 | 44k / 2.2k | 0.49 | 8 |
| T5b bad PMID | 0/2 (0/3) | 33 | 5 | 107k / 2.9k | 0.52 | 7 |
| T6 active genes + diff | 2/2 (3/3) | 35 | 4 | 76k / 2.7k | 0.32 | 7 |

Totals: median wall 35 s (R1 31), median 4.5 calls (R1 5), 1.97M in / 59k out (R1 2.55M / 69k), $4.41 incl. baselines (R1 Claude $4.52). Tool list 4.4k tokens = 5.3% of median input (R1 5.7%; 62% without tool search).

Median ratings (vs R1): discoverability 7 (+1), speed 8 (0), token efficiency 6 (+1), error clarity 7 (+1, n=3), correctness/safety 8 (0), overall 7 (0). All below 9.

## Why below 9 (paraphrased)
- Discoverability: ~190 deferred tools, no capability overview; scope -> pair -> schema lookup; two ClinGen pairs.
- Speed: create_gene failures, resolve_genes gives no local gene_id; 2 calls to find a schema.
- Tokens: every save/submit echoes evidence_data + score trace; ~15k-token schema reads; get_curation_schemas 73k chars.
- Errors: "JSON unparseable" without location; "already exists" without id.
- Safety: diff baseline is the review, not the submission; replace vs merge unclear.

## Findings (impact x frequency)
1. (3) The scoring evidence path does no validation: save_draft_curations stored nonexistent PMID 99999999 and scored it 3 points; submit accepted pmid "PMID12x". Deprecated create_evidence_item 500s on categories over 50 chars (varchar(50)).
2. (3) Saves replace the whole evidence_data: a one-field edit resends ~1.4 KB; T5a-2 failed after 5 malformed client inputs; a stale resend could drop a co-curator's edit. Need merge-patch and a clear description.
3. (2, 14/20) Responses too big: full evidence_data + score trace with zero rows on every get/write; large schema reads; no compact schema list.
4. (2, 6/20) get_curation/get_scope lack curation_schema_id/precuration_schema_id; create_precuration should default its schema from the scope's pair.
5. (1, 7/7) Still open from R1, in batch 2: default ClinGen pair, diff baseline, capability overview / auth_info.

## Artefacts for round 3
T5a never hits a 409 (agents read first; grade end state, drop saw_conflict). T6 diff empty by construction (seed an edit during review). Parallel chains share the gene catalogue (T2-1 400s partly runner-caused). Error clarity n=3. All PATs revoked.
