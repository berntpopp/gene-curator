# MCP study round 6 (Claude Code 2.1.312, opus-5-5, stack a3c4c82b = PR #519 lean /mcp core, 47 tools; GeneFoundry hosted for T2b/T3/T7/T8)

24/27 success (R5 21/24), 0 unsafe, $7.38. Stop rule NOT met (T5b 1/3, T7 2/3, medians below 9). No plateau (token efficiency +1). The lean core lost nothing agents needed: no call to a missing tool, no /mcp/full detour; the 3 Gene Curator errors were schema guessing (T2-1) and a 2000-char comment limit (T8-1/-3).

| Task | OK (R5) | Wall s | Calls (GF) | In/out tok | $ | Overall |
|---|---|---|---|---|---|---|
| T0 | 2/2 (2/2) | 15 | 2 | 23k/1.3k | .20 | 9 |
| T1 | 2/2 (2/2) | 38 | 8 | 71k/2.5k | .28 | 9 |
| T2 | 3/3 (2/2) | 32 | 6 | 88k/3.0k | .49 | 8 |
| T2b | 3/3 (2/2) | 86 | 13 (6) | 212k/5.3k | 1.05 | 8 |
| T3 | 2/2 (2/2) | 26 | 4 (0) | 72k/2.1k | .29 | 9 |
| T4 | 2/2 (2/2) | 22 | 4 | 40k/2.0k | .20 | 7.5 |
| T5a | 2/2 (2/2) | 22 | 3 | 49k/1.8k | .22 | 8 |
| T5b | 1/3 (2/2) | 34 | 5 | 65k/2.9k | .40 | 8 |
| T6 | 2/2 (2/2) | 32 | 5 | 58k/2.5k | .26 | 8 |
| T7 NPHS2 | 2/3 (0/3) | 160 | 30 (16) | 758k/12.7k | 3.17 | 8 |
| T8 NPHS1 | 3/3 (3/3) | 56 | 9 (4) | 147k/4.5k | .81 | 8 |

Token targets: median input per task 71k (<=55k missed; R5 54k); T2 88k (<=130k met); T2b 212k (<=140k missed). Tool-list share (static deferred list 3.1k tok x requests + ToolSearch schemas, with re-reads): Gene Curator 25% of all input (<=15% missed); GeneFoundry 17% of dual-task input (static 2.8k + search_tools hits). Largest result: Gene Curator 8.6 KB read_curation_for_review (T3-2, target 8 KB just missed); GeneFoundry passages 22-33 KB (T7). Curator tools 47 (<=80 met).

Median ratings (R5): discoverability 8 (8), speed 9 (9), token efficiency 8 (+1), error clarity 6 (-1.5, n=9, mostly GeneFoundry errors), correctness/safety 9 (9), overall 8 (8). Primary flows: 8/8/8/6/9/8.

T7 (runner and grader2 agree): T7-1 pass (Definitive, gen 12 + exp 5, 7 PMIDs incl. Boute 2000), T7-2 pass (Definitive 15.5; minor: 6 identical-genotype rows from one paper), T7-3 FAIL (Strong 14.2: replicated_over_time not set although its own summary says replicated >20 years; genetic under-scored 8.2). All runs: MONDO:0010974 + AR right, all PMIDs real and on topic, founding paper present but only scored as expression; nothing fabricated.
T8: 3/3, E1/E2/E3 caught in every run by both graders, changes requested.

GeneFoundry: used in T2b (3/3), T7 (3/3), T8 (3/3), not in T3. Only pubtator_search_literature / get_publication_passages / get_publication_annotations / get_variant_evidence worked; the pinned mondo_resolve_disease and clingen_get_gene_validity returned not_found in every attempt (hosted router serves only PubTator). Results share 10-30% of input (T7 30%). Carry-over: all 25 T7 PMIDs stored came from GeneFoundry results and validated; HGVS taken from PubTator passages (one internal inconsistency, T7-2 c.460dup vs p.156); MONDO came from the precuration (GF lookup failed).

Below-9 reasons:
- Discoverability 8: "no tool shows the precuration schema's fields, required keys or allowed values" (T2-1, 5; T2-2/T2-3); "GeneFoundry pinned resolvers ... not_found" (T7-3, 5).
- Token efficiency 8: "get_curation returns the full evidence payload twice ... only needed lock_version" (T5a-2, 6; T4-1/-2); "every save echoes a long warning that lists all 15 row paths" (T7-1, 5); "passage call returned ~60 'dropped' entries" (T7-3, 5).
- Error clarity 6: "invalid_input ... never said the 2000-character maxLength was the problem" (T8-1/T8-3, 4); GeneFoundry "could not complete the requested operation" / not_found for pinned tools (T2b-2, T7-2, T7-3, T8-2: 5-6).
- Overall 8: precuration field contract by trial and error (T2-1); "couldn't find who is assigned to review" (T4-2, 7); "research side limited to PubTator" (T7-3, 7).

## Findings (ranked; owner)
1. (3, T5b 2/3) save_draft accepts a row whose pmid validate_pmids just reported not_found (99999999 stored with "must be verified"); reject not_found PMIDs in pmid fields at save (submit already does) and scan free text only to warn. Gene Curator.
2. (3, T7 1/3) Classification not upgraded although replication is stated: have calculate_score/save warnings say "total >=12 and first evidence > 3 y old: set replicated_over_time for Definitive", and warn when the founding paper is only used for expression. Gene Curator (validating).
3. (2, T8 2/3) submit_peer_review invalid_input must name the constraint and value ("comments 2187 > 2000"), or accept longer comments / put details in feedback_data. Gene Curator.
4. (2, T2 3/3) Precuration field contract: create_precuration response or description should list required fields/options (or point to get_curation_schema for the precuration schema). Gene Curator.
5. (2, 7/12 dual runs) GeneFoundry hosted serves only PubTator: pinned mondo/clingen/gencc entry points return not_found; fix the deployment or drop them from instructions; error must say "backend not deployed". GeneFoundry.
6. (2, T7) Token cost: GeneFoundry passages 22-33 KB with dropped-section lists; Gene Curator save warnings repeat all row paths, get_curation returns full evidence (add fields= / concise). Both.
7. (1) get_curation/list_curations should show assigned reviewers (T4); curation_diff needs an approved baseline (T6); validate_pmids optional gene/keyword relevance check (T2b/T7, 6 runs). Gene Curator; relevance ranking itself is GeneFoundry research.

## Study artefacts
T0 auto-check failed by construction (10-line answer not in the structured summary; Alice in 7 scopes incl. T7/T8) -> regraded pass by hand. T8 fake PMID planted in row text (v1 refused at submit). T8 grader2 first ran without the planted list (file missing), rerun with it: same 3/3. Dual baseline (both servers) failed to build (sed), shares use the single-server baselines. GeneFoundry partial outage (PubTator only) depresses T7 discoverability/error ratings. Third runs: T2, T2b, T5b. All 3 PATs revoked (401 after).
