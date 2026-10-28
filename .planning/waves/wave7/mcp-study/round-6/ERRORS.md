# Round 6 tool errors

Source: `claude/*/stream.jsonl`, every MCP tool_result with `is_error` set, plus results that came back empty or unhelpful. ToolSearch and StructuredOutput are excluded. GeneFoundry calls were reproduced live on 2026-10-28 through the hosted router.

Classes: (a) not available / not deployed, (b) wrong usage by the agent, (c) correct call handled badly, (d) upstream outage.

## Gene Curator (4 hard errors, 0 bugs)

| Run | Tool | Arguments | Response (short) | Class | Message told the fix? |
|---|---|---|---|---|---|
| T2-1 | submit_precuration | lock_version 1 | 422 `Missing required fields: lumping_splitting_applicable, affiliation` plus `fields[]` | b (required fields unknown before submit) | yes, names the fields |
| T2-1 | submit_precuration | lock_version 2 | 422 `mode_of_inheritance: Value must be one of: AD, AR, ...`; `lumping_splitting_decision: LUMP, SPLIT` | b (guessed enum values) | yes, path and allowed values |
| T8-1 | submit_peer_review | comments 2009 chars | `invalid_input: submit_peer_review: comments: '<first ~200 chars echoed>' next: fix the arguments; accepts review_id, decision, comments, suggested_changes` | b (exceeded maxLength 2000) | **no**: limit, actual length and constraint are all missing. The agent cut the text to 1370 chars by guessing. |
| T8-3 | submit_peer_review | comments 2037 chars | same | b | **no**. The agent retried at 1024 chars and moved the rest into suggested_changes. |

Not errors: `validate_pmids` returning `not_found` for the planted 99999999 (T5b x3) and 98765432 (T8 x3). These are correct and were understood.

## GeneFoundry (hosted router, PubTator only)

| Runs | Tool | Arguments | Response (short) | Class | Notes |
|---|---|---|---|---|---|
| T2b-2, T7-2, T7-3, T8-1, T8-2, T8-3 (6 calls) | call_tool clingen_get_gene_validity | gene PKD2/NPHS2/NPHS1 | `not_found: The requested tool is not available.` suggests search_tools | a | pinned in the instructions, never served |
| T7-1, T7-2, T7-3, T8-1 (4 calls) | call_tool mondo_resolve_disease | query "nephrotic syndrome type 2" / "MONDO:0009732" | same not_found | a | same |
| T7-1 (2), T7-2, T7-3 (2), T8-1, T8-3 (8 calls) | search_tools | "mondo disease ontology search", "clingen gene disease validity ..." | `{"result":[]}` | a | following the error's own suggestion leads nowhere; nothing says "backend not deployed" |
| T2b-1, T2b-2, T2b-3 (2), T8-1, T8-2, T8-3 (7 calls) | pubtator_search_literature | `query` instead of `text` | invalid_input with `missing_params:["text"]`, `unexpected_params:["query"]` | b | yes, one retry fixed it every time (rated 8-9). Small flaws: `field_errors` reports `"field":"unknown"`; recovery_action "inspect diagnostics" is generic. |
| T7-2, T7-3 (2) (3 calls) | pubtator_search_literature | `publication_types:["Case Reports"]` | success, 0 results | c | reproduced: 202 hits without the filter, the Review filter works. Silent-empty filter bug. |
| T2b-2 (1 call) | call_tool pubtator_get_publication_annotations | pmids, format pubtator, full true | `invalid_input: The tool could not complete the requested operation.` | c | reproduced. Each option works alone; the combination fails opaquely. |
| T2b-1, T7-3 (2), T8-2 (4 calls) | pubtator_search_literature | exact year 1997 / `sections:["title"]` with 5-7 AND terms / very specific query | success, 0 results | b (query too narrow) | sections:["title"] works on a broad query (checked live) |
| T2b-1/2/3, T7-1, T7-3 | pubtator_search_literature | `year_max` only | results with a note that the year range was applied locally over one newest-first page | not an error | documented limitation, the message explains it |

No class (d) errors: PubTator3 answered every well-formed call.

Counts. Gene Curator: a 0, b 4, c 0, d 0. GeneFoundry: a 20 (12 not_found + 8 empty search_tools), b 11 (7 argument errors + 4 narrow-query empties), c 4, d 0.

## Error clarity, Gene Curator only

| Run | Agent rating | Reason | GC-only |
|---|---|---|---|
| T2-1 | 8 | 422 named the fields and allowed values | **8** |
| T8-1 | 4 | invalid_input cut off the comment, never named the 2000-char limit | **4** |
| T8-3 | 4 | same | **4** |
| T2b-1 | 8 | PubTator `query`/`text` error | excluded (GeneFoundry) |
| T2b-2 | 6 | "could not complete", pinned clingen not available | excluded (GeneFoundry) |
| T2b-3 | 9 | PubTator param error | excluded (GeneFoundry) |
| T7-2 | 5 | mondo/clingen not_found | excluded (GeneFoundry) |
| T7-3 | 6 | not_found did not say the backend was missing | excluded (GeneFoundry) |
| T8-2 | 6 | PubTator ok, clingen generic | excluded (GeneFoundry, no GC error in this run) |
| T7-1 | null | no GC errors | n/a |

**Gene Curator-only median: 4 (n=3: 8, 4, 4).** The SUMMARY's 6 (n=9) mixes in GeneFoundry; removing GeneFoundry makes the number worse, not better. Only 2 messages are bad (precuration 422s are good), but the same message type failed in both runs that hit it.

Gene Curator messages still to fix:
1. `submit_peer_review` (and the generic invalid_input mapper behind it): name the constraint and the value, e.g. `comments: 2037 characters, max 2000`. Keep the "next" hint, but say "shorten comments to <=2000 or move details to suggested_changes". Do not echo 200 chars of the user's text in place of the reason.
2. `submit_precuration`: the messages are good. The cost is the trial and error that comes first (finding #4: expose required fields/enums before submit). It is a discoverability gap, not a message problem.

## Issues filed (GeneFoundry)
- https://github.com/berntpopp/genefoundry-router/issues/256 (pinned mondo/clingen not_found, empty search_tools; 7/12 runs)
- https://github.com/berntpopp/pubtator-link/issues/230 (Case Reports filter silently empty; 2/12 runs)
- https://github.com/berntpopp/pubtator-link/issues/231 (annotations pubtator+full opaque error; 1/12 runs; generic recovery_action and `field: unknown` noted)

Not filed: the `query`/`text` mistake (agent misuse, the message already names the fix) and the narrow-query empties.
