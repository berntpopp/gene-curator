# MCP design ideas after round 3 (2026-10-28)

Goal: every category median >= 9 for Claude Code, T2/T2b/T3/T6/T7/T8 perfect. Inputs: round-3 SUMMARY,
structured.json of all 26 runs, tokens.txt, TOKEN-EFFICIENCY-PLAN, GAP-ANALYSIS, origin/master eff78fe5
(`backend/app/mcp/{server,audit}.py`, `mcp_tools_core.snapshot`), GeneFoundry fleet (read-only), live
GeneFoundry MCP, web sources. No product code changed.

## 1. What actually holds the scores down

| Category (median) | Cited cause (runs) | Root |
| --- | --- | --- |
| error clarity 5 | gene 404 -> "list_scopes/list_curations" (T2-1, T2-2); curation_diff 404 same hint (T6-1/2/4); literal `{item_id}` 422 (T3-1) | one generic 404 hint; no argument check before the call |
| correctness/safety 8, T7 6-7 | off-topic PMIDs valid; no abstracts; rows per paper with placeholder variants; truncating variant under other_variant_type (T7-1 fail); no-PMID row scores (T8-2); baseline=submitted silently "no change" (T6-4) | evidence content is never checked, only its shape |
| token efficiency 7 | compact schema 15 KB (T2b, T5b-2); calculate_score trace twice (T7, T8-2); get_curation whole trace for a lock_version (T4, T5a, T5b-3) | no path/field read |
| discoverability 8 | create_scope absent (T1); no snapshot ids (T6); no literature search (T7); descriptions name tools not on /mcp (T1-1) | gaps, not wording |
| speed 8 | 4/7 calls on diff baselines (T6-4); PMID guessing (T7, 17 validate_pmids calls) | round trips |

Token sinks (round 3, 2.5M input): base prefix x requests 49%, ToolSearch-loaded schemas 16%, results 17%
(schema 6%, get_curation 2%, validate_pmids 2%). T7 alone is 34% of all input (250-312k per run) because
the agent guesses PMIDs in bulk. **Requests per task stay the multiplier; removing a round trip beats
shrinking a result.**

## 2. What the fleet and the sources show (only what pays off here)

- **Argument errors that name the field.** `hgnc-link/hgnc_link/mcp/middleware.py:85` `ArgValidationMiddleware`
  + `mcp/arg_help.py:93`: missing/unknown argument -> `invalid_input` with `field`, `allowed_values` (valid
  names), did-you-mean (difflib), signature hint; `litvar-link/litvar_link/mcp/argument_errors.py`: "The tool
  EXISTS -- this is an argument error". MCP SEP-1303 (final, in 2025-11-25): input validation errors are tool
  execution errors (`isError: true`) so the model can self-correct
  (https://modelcontextprotocol.io/seps/1303-input-validation-errors-as-tool-execution-errors).
- **Not-found that routes to the right tool, computed per tool.** `hgnc-link/hgnc_link/mcp/next_commands.py:28`
  (`default_error_next_commands`: failed get_gene -> resolver/search), withdrawn -> `replaced_by`
  (`mcp/envelope.py:184-200`); pubtator `errors.py:53`: validation failures are never `not_found`
  ("the model strikes the tool from its list").
- **A test that every hint names a real tool and real arguments:** `clingen-link/tests/unit/test_next_commands_are_callable.py`;
  every error code has a hint: `hpo-link/tests/unit/test_next_commands_coverage.py`.
- **Descriptions: "Use this when...; do not use for X, use Y; Next: Z"** (`pubtator-link/pubtator_link/mcp/tools/publications.py:358`),
  required words pinned by tests (`panelapp-link/tests/test_tool_descriptions.py`, `genereviews-link/tests/test_tool_schema_descriptions.py`).
- **Honest size limits.** gnomad `shaping.py:256-285` `truncated{dropped, to_restore}`; pubtator passages
  `max_chars` + `dropped[]` + `recommended_max_chars`. We already return `response_too_large` (fine for a
  write-heavy server: an agent must not act on a silently cut curation).
- **Literature for curation.** pubtator `search_literature(text, entity_ids=["@GENE_X"], publication_types,
  year_min, limit<=20)`, `get_publication_passages(pmids<=25, mode="full_abstract")`,
  `get_variant_evidence(gene, variant)`; litvar variant -> PMIDs. No fleet tool says "is PMID about gene X"
  or lists variants per PMID (`entities_by_pmid` is internal only, `services/topic_literature_map.py:90`).
- **Prompts/resources:** fleet has workflow prompts (`clinvar-link/clinvar_link/mcp/prompts.py`). In Claude Code
  prompts are user slash commands (`/mcp__server__prompt`) and resources are `@` mentions or an extra read
  tool (https://code.claude.com/docs/en/mcp). An agent given a task never calls a prompt: no rating gain.
- **Anthropic:** actionable, steering errors instead of opaque codes; concise vs detailed (~1/3 tokens); 25k
  default cap in Claude Code; consolidate multi-step operations
  (https://www.anthropic.com/engineering/writing-tools-for-agents). Claude Code: warning at 10k tokens, file
  spill at 50k chars, `_meta["anthropic/maxResultSizeChars"]`, `anthropic/alwaysLoad` (docs above).

Live GeneFoundry, PKHD1/ARPKD (2026-10-28): only pubtator was reachable; hgnc/mondo/clingen `call_tool`
returned `not_found: The requested tool is not available` and `search_tools("ClinGen validity")` returned `[]`.
**Lesson: a backend outage looked like a missing tool.** Our `upstream_unavailable` must never collapse into
not_found (T5b-1/3 asked exactly this for validate_pmids). `pubtator_search_literature` 5 hits = 4.9 KB
(~1 KB/hit, `recommended_citation` repeats title/journal, ~40%); relevance was good (cohort, case report, iPSC
lines). `get_publication_passages(full_abstract, max_chars=3000, verbosity=lean)`: 3.3 KB for 1.3 KB of
text (provenance + sha256 per passage), second abstract dropped with a clear `dropped[]` and
`recommended_max_chars`: pleasant. `limit=50` error said "Invalid MCP arguments" + all valid params but
not "limit max 20": the error must name the field and the bound.

## 3. Ranked changes (impact x effort)

E = effort (S <= 50 lines, M <= 200). "In flight" = W7M8/W7M9/W7M10/#509 as briefed.

| # | Change | Fixes | Owning files | Evidence | Expected effect | In flight? |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | **Case-row lint with paths** in the ClinGen engine, shown on save, get_curation, calculate_score and to the reviewer: (a) placeholder variant: no HGVS/rs/coordinate token (`c.`, `p.`, `g.`, `m.`, `NM_`, `NC_`, `rs\d+`, `chr\d+:`, `del`/`dup` with coordinates) or phrases like "as reported"; (b) variant looks null (`fs`, `Ter`/`*`/`X` stop, `c.N+1/+2/-1/-2`, whole-gene/exon deletion) but row is in `other_variant_type` -> "move to predicted_or_proven_null"; missense in `predicted_or_proven_null` -> the reverse; (c) one PMID on >= 3 proband rows whose labels say cohort/patients/family, or a label that names a cohort -> "one row per described proband". Warnings name `genetic_evidence.case_level.autosomal_recessive.other_variant_type[1]`. | T7 quality (all 3 runs), T7-1 fail, T8 reviewer aid, T5b-2 "which variant_type" | `backend/app/scoring/clingen.py` (`_check_genetic_evidence_warnings_nested`), small regex table next to it, test in `tests/scoring/` | T7 verify.json: every row `"PKHD1 truncating variant (as reported in publication)"`; T7-1 truncating under other_variant_type | T7 safety 6-7 -> 9 once (2) refuses (a); T8 reviewers get specific line items | **No.** W7M10 refuses rows "without variant"; a placeholder string passes that check |
| 2 | **Submit refuses scored case rows with a placeholder variant** (lint 1a), same path as W7M10's no-PMID/no-variant refusal; save only warns (drafts stay editable). | T7 safety, owner "perfect" | W7M10 files (`crud/workflow_engine.py` / submit validation) | as above | agents must go read the paper; with (3) they can | Extend W7M10 (one more predicate) |
| 3 | **Abstracts + PubMed search** (W7M9) plus `gene_symbol=` on `validate_pmids`: `mentions_gene: false` when title/abstract lack the symbol and HGNC aliases. Distinct `not_found` vs `upstream_unavailable` per PMID. | T7 (all runs' top change), T2b-2 off-topic PMIDs, T5b-1/3 | `endpoints/publications.py`, publication service, `audit.py` `SLIM_KEYS` (keep `abstract` out of validate_pmids, in get_publication) | T7 x3, T2b-2, T5b x2 asks; 17 validate_pmids calls/45k tokens from guessing | T7 calls 19 -> ~12, input 273k -> ~150k; safety +1 | Search and abstracts: yes (W7M9). Gene-mention flag and not_found/upstream split: **no**, add to W7M9 |
| 4 | **Argument check before the call** in `ToolAuditMiddleware.on_call_tool`: from `tool.parameters`, reject missing required and unknown argument names (`isError`, `invalid_input: get_workflow_audit_trail: missing item_id; unknown curation_id (did you mean item_id?); accepts item_type, item_id`). No silent aliasing on write tools. Also enum/bound violations name field + allowed range. | error clarity (T3-1), the `{item_id}` 422 | `backend/app/mcp/audit.py`, `tests/api/test_mcp_hints.py` | hgnc ArgValidationMiddleware, SEP-1303; live pubtator limit=50 counter-example | removes a whole class of confusing errors | W7M8 planned: make sure it covers unknown names + did-you-mean, not only "required" |
| 5 | **Per-resource 404 hints** keyed by the path parameter of the failed route, not one global line: `gene_id`/`hgnc_id`/`symbol` -> "not in Gene Curator yet: resolve_genes, then create_gene(hgnc_id)"; `audit_id`/curation_diff -> "snapshot ids: get_workflow_audit_trail(item_type, item_id)"; `pmid` -> "search_publications / validate_pmids"; `scope_id` -> "list_scopes(name=)". Plus a test: every tool named in a hint or in a /mcp description is on /mcp (clingen `test_next_commands_are_callable` pattern; catches T1-1's create_scope mention). | error clarity 5 -> 9 (T2, T6) | `audit.py` (`_TOOL_HINTS` -> param-keyed table), `tests/api/test_mcp_hints.py` | T2-1/2, T6-1/2/4 cite the hint directly | 5 of 9 error runs | W7M8 has gene 404 only: **extend to curation_diff/audit and pmid** and add the callable-hint test |
| 6 | **Evidence-path read** on get_curation (`paths=` incl. top-level `lock_version,status,assigned_reviewers`) and `get_curation_schema(path=)` subtree; drop the duplicate calculate_score trace. | tokens 7 -> 9 (T2b, T4, T5a, T5b, T7, T8) | `endpoints/curations.py`, `endpoints/schemas.py`, `MCP_DEFAULTS` | 4 runs ask for schema path filter, 5 for get_curation fields; schema 15 KB x 8 calls | max result 15 KB -> ~3 KB; ~6% input | W7M8 (evidence by path, compact schema < 8 KB, trace once). **Prefer a schema `path=` filter over squeezing the compact schema**: agents asked for it 4x and it keeps the 8 KB target by construction |
| 7 | **Two lines in `_EVIDENCE_PATHS`** (already on save/update/create_curation): "One row per proband described in the paper, each with its own HGVS variant(s) and PMID; never one row per paper or cohort. variant_type: nonsense, frameshift, canonical +/-1,2 splice, exon/whole-gene deletion -> predicted_or_proven_null; missense, in-frame, other splice -> other_variant_type." | T7 quality, T5b-2 | `backend/app/mcp/server.py` | T5b-2 top change 3; T7 pattern | cheap prevention; lint (1) catches the rest | No |
| 8 | **Diff and audit** (W7M10): baseline=previous_submission, snapshot ids on audit entries, and a diff result that says what it compared (`baseline: {kind, audit_id, at}`) so `changed:false` is never ambiguous. | T6 disc 5, safety 6, speed 6 | W7M10 files | T6 x3 | T6 6 -> 9 | Yes; check the explicit baseline echo is in it |
| 9 | **Reviewer read** (W7M9 "one reviewer read"): must include previous round's request_changes notes, `superseded` flag on old review rows (or default pending only), lint warnings from (1) and "evidence_summary claims X points, computed Y". | T3 disc 7-8, T8 safety 7-8 | review endpoints, `get_my_review_assignments` | T3-1/2, T8-1/2 top changes | T3/T8 -> 9 | Partly; **add summary-vs-score mismatch and superseded rows** if not in scope |
| 10 | **Can I approve, and who can** in one read: `get_curation` (or list rows) carries `assigned_reviewers` (names) and `you_can`/`blocked_reason` (e.g. "author (4-eyes)"), derived from the same workflow check the API enforces. If `get_workflow_state` already returns this (GAP F5), just add one instruction line "May I approve? get_workflow_state". | T4 overall 7-8 | `crud/workflow_engine.py`, `schemas/` or `server.py` INSTRUCTIONS | T4-1/2 top changes | T4 -> 9 | No |
| 11 | **Instructions: cross-server and one-shot loading.** Add: "With GeneFoundry connected, find papers with pubtator_search_literature (entity_ids @GENE_X), read them with pubtator_get_publication_passages(mode=full_abstract), variants with litvar/pubtator_get_variant_evidence; record evidence here." And a "curate a gene" tool set to load in one ToolSearch `select:`. | T7 speed/quality where GeneFoundry exists; ToolSearch 16% | `server.py` INSTRUCTIONS (stay < 4,096 chars) | live test; tokens.txt 40 searches | ~1 search/run less; zero code | No. Does not replace (3): the study stack and many users lack GeneFoundry |
| 12 | **Edit context on get_curation**: `updated_by_name`, `updated_at`, and changed top-level keys since `since_lock_version` (cheap if the audit row is at hand). | T5a safety 8 | `endpoints/curations.py` | T5a-1/2 | T5a -> 9 | No (GAP F8 half done) |
| 13 | **Surface budget tests**: largest seeded result per hot tool (< 8 KB), loaded-definition size per tool (fleet B1 1,200 tok), description must not name a tool missing from its endpoint. | keeps gains | `tests/api/test_mcp_toolsets.py` | litvar `test_tool_surface_budget.py`, panelapp description test | regression guard | No |

Order to ship: 4+5 (one PR, `audit.py` + tests), 1+2+7 (scoring lint + W7M10 predicate + text), 3 delta,
6 (fold into W7M8), 9-10, 12, 11, 13. Items 1-7 cover every T7/T8 quality gap and all error runs.

## 4. Considered and dropped

- MCP prompts (guided curate-gene): user-invoked slash commands, the agent never sees them; instructions +
  `_EVIDENCE_PATHS` already carry the workflow.
- Evidence-row templates returned with the schema: (7) + lint (1) + schema `path=` give the same with no new
  payload.
- Resource links instead of inline blobs: in Claude Code a link costs a second read call; the path filter
  shrinks the inline result instead.
- Generic `next:` on every write result: only the submit -> assign step was missed, and W7M9 merges it.
- Per-tool `response_mode` on all tools, hgnc-style argument aliasing, router/code mode, fleet `_meta`
  stamps: same reasons as GAP-ANALYSIS section 4; aliasing on writes risks writing the wrong field.
- `anthropic/maxResultSizeChars`: we want smaller results, not bigger ones.
- Proxying GeneFoundry through Gene Curator: duplicates a server, adds an anonymous upstream; agents can use
  both servers side by side (11).

## 5. Rule conflicts

- Per-user RLS: none. Lints run in the scoring engine on data the caller can already read; the
  gene-mention flag uses only the shared PubMed cache (public data, already cached today).
- Parity on /mcp/full: (1), (2), (3), (6), (8)-(10), (12) are REST/engine changes, so UI, /mcp and /mcp/full
  get them alike. (4), (5) live in the MCP middleware and apply to both endpoints (the core flag gates only
  lean output and the cap).
- No caching of per-user data: nothing proposed caches; computed hints are per call.
- No anonymous mode: (11) is the agent using two servers with their own auth; Gene Curator never calls
  GeneFoundry.
- 4-eyes: (10) only reports what the API enforces; it must call the same check, never a copy.
- Owner decision needed: (2) submit refusal on placeholder variants also binds UI users and legacy data
  (warn on save, refuse on submit; existing active curations unaffected until edited).
