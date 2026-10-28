# MCP study round 1: gap analysis to a 9/10 median

Inputs: 24 Claude runs, 9 Codex runs (T0-T2 only; T3-T6 void, quota). Target: median >= 9 in every category for
both clients. Round-1 medians (disc/speed/tokens/errors/safety/overall): Claude 6/8/5/6/8/7, Codex 6/8/5/7/8/6.
"Covered" = fixed by W7M1 (precuration routing, no 500, actionable approval errors), W7M2 (evidence validated and
scored on create), W7M3 (truthful invite, compact schema read, one score trace, names and name filters on review
lists and list_curations; branch `fix/mcp-study-token-efficiency`). Run ids: C = Claude, X = Codex.

## 1. Reasons below 9, grouped into root causes

| Root cause | Categories hit (runs) | Covered? |
| --- | --- | --- |
| R1 Curator cannot route a precuration; create_curation/assign_peer_reviewer dead-end ("approved precuration is required", "only supported for curations") | disc 5-6, speed 7, errors 6-8, overall 5 (C T2-1..3, X T2-4..6) | W7M1, but see A2: T2 still cannot finish in one session |
| R2 No entry point that says what I can do; ~186 tools; preconditions not stated up front ("nothing said precuration approval is a hard gate"); `auth_info` returns REST login URLs | disc 5-7, overall 8 (C T0-1..3, T2-1..3, T1-2, T5a-1/3; X T0-4..6, T2-5/6) | No |
| R3 list_scopes returns every scope with scope_config, description, timestamps (5-9 KB) just to map a name to an id; no name filter | tokens 5-7 (C T0, T1, T4-1..3, T5b-1..3, T6-1; X T1-4..6) | No (W7M3 filters list_curations, not list_scopes) |
| R4 Every result is sent twice: text JSON and identical structuredContent ("Responses duplicated records in text and structuredContent") | tokens 4-6 (X T0-4..6, T1-5/6, T2-4) | No |
| R5 get_curation_schema 39 KB; score trace twice in get_curation | tokens 3-5 (C T2, T3, T5a, T6; X T2) | W7M3 |
| R6 Two active ClinGen workflow pairs, no default | disc 6-7, safety 6-7 (C T1-1..3, X T1-4..6) | No (finding 5) |
| R7 invite_member pending vs documented auto-accept; roles not effective | errors 4-5, safety 6-7, overall 6-7 (all T1) | W7M3 fixes errors; safety stays ~7 because roles remain pending (see F6) |
| R8 Evidence accepted unvalidated/unscored; review of a 0-score curation not flagged | errors 5-6, safety 7, disc 6 (C T5b-1..3, T3-1/2) | W7M2 (if get_curation also shows unscored counts) |
| R9 get_workflow_state advertises `active` to the author while a review is pending; pending_reviews has only reviewer UUIDs, get_user is 403 | safety 4/8, errors 6, disc 6-7 (C T4-1..3) | W7M1 names approvers in errors only, not in the state read |
| R10 Review assignments without scope/gene, 3-4 get_curation calls to find one | disc 6, speed 7 (C T3-1..3) | W7M3 |
| R11 curation_diff baseline is the review audit, not the submission; empty list is ambiguous | disc 6, safety 7, overall 7 (C T6-1..3) | No |
| R12 No who/what on concurrent edits; 409 described but shows nothing | errors 6, overall 7 (C T5a-1..3) | No (half artefact, A1) |
| R13 error_clarity scored 5-7 because no error happened ("couldn't be tested") | errors (C T0-1..3, T3, T5a, T6; X T0-4..6) | Artefact, A3 |

Speed is 8 almost everywhere with reasons like "5 calls, mostly parallel": raters stop at 8 unless a task is
short and dead-end free. It rises with R1/R2/R10 fixed and fewer probing calls; no separate fix.

## 2. Transcript friction behind the uncovered causes

- Tool search never failed: Claude used `select:` on guessed names (all hits). Discovery cost is mis-ordering and
  probing, not lookup. Claude T2 loaded 2-4 tool batches; Codex T2 called four PMID tools (`get_publication` x4,
  `validate_pmids`, `validate_pubmed`, `list_publications`) for one job and probed `get_workflow_configuration`,
  `list_members`, `get_peer_reviewers`, `get_scope_assignments`, `get_workflow_state`, `get_precuration` after
  the 400s. T2 calls: Claude 16-19, Codex 24-28; minimum with W7M1 is ~9 (resolve, create genes, assign,
  schema, MONDO, validate PMIDs, create + submit precuration, route to Bob).
- Descriptions are raw docstrings: `list_scopes`, `create_scope`, `validate_pmids` ship "Args: db: Database session,
  current_user: ..." text; `get_workflow_pairs` says only "Retrieve workflow pairs"; `create_curation` does not say
  it needs an approved precuration; `bulk_create_gene_assignments` (admins only) was tried by curator alice ->
  "forbidden: HTTP 403: Not enough permissions for this scope" (C T2-2), with no hint that
  `create_gene_assignment` works for curators.
- The server sends no `instructions` (`FastMCP.from_openapi(...)` in `backend/app/mcp/server.py` has none).
- Codex input: 106-143k for a 2-call T0 against a 15.7k no-MCP baseline; every turn re-sends results that are
  doubled (text + structured_content in `events.jsonl`; FastMCP `OpenAPITool.run` returns only
  `structured_content`, which ToolResult mirrors into text). The 39 KB schema read cost ~78 KB per turn.
- T4: `validate_workflow_transition` returns the right errors but mixes in generic "requirements" ("Final
  quality checks must pass"); `get_workflow_state` lists `["precuration","active","curation"]` for alice.
- T6: `curation_diff` -> `{"baseline":{"audit_id":52,"source":"review"},"items":[]}`; all 3 runs then needed
  `get_workflow_audit_trail` + `list_evidence_items` and inferred "no change" from timestamps.

## 3. Additional fixes, ranked by impact

| # | Change | Target | Evidence | Impact | Owner files |
| --- | --- | --- | --- | --- | --- |
| F1 | Server instructions (~40 lines): workflow map Entry -> Precuration (reviewer approves) -> Curation -> Review -> Active, with the tool per step; scope-role table (viewer/curator/reviewer/admin -> allowed actions; 4-eyes; curators assign genes one by one); "find a scope by name with list_scopes(name=)"; "validate PMIDs with validate_pmids". Exclude `auth_info` from MCP. | disc, speed, overall (both) | R2; T0 6/6 asked for a capabilities tool; T2 precondition surprise | High: answers T0 in 2 calls, removes T2/T4 probing | `backend/app/mcp/server.py` (`instructions=`, `EXCLUDED_OPERATIONS`) |
| F2 | Clean tool descriptions in `_annotate`: cut docstrings at `Args:`/`Returns:`/`Raises:`; add one-line preconditions on the ~10 workflow tools (`create_curation`, `submit_precuration`, `assign_peer_reviewer`, `execute_workflow_transition` = "approve is target_stage=active by a reviewer, not the author", `bulk_create_gene_assignments` = "scope admins; curators use create_gene_assignment"); point `validate_pubmed`/`get_publication`/`list_publications` at `validate_pmids` (or exclude `validate_pubmed`). | disc, tokens, speed | Codex 4 PMID tools in T2; 403 in C T2-2 | High, cheap | `server.py` `_annotate`; endpoint docstrings in `endpoints/curations.py`, `workflow.py`, `gene_assignments`, `publications`, `external_validation` |
| F3 | Send each result once: in `ToolAuditMiddleware.on_call_tool` return text-only content (drop `structured_content`) and publish no `outputSchema` (`output_schema=None`), which also shrinks the 149.6 KB `tools/list`. | tokens (Codex mainly) | R4, 5/6 Codex runs | High for Codex (~2x on every result), neutral for Claude | `backend/app/mcp/audit.py`, `server.py` |
| F4 | Lean `list_scopes`: default rows `{id, name, display_name, user_role, gene_count, member_count, default_workflow_pair_id}`; `scope_config`/description only in `get_scope_details`; add `name` filter. | tokens, disc, speed | R3, 14 runs | Medium-high: list_scopes is the first call of 7 of 8 tasks | `endpoints/scopes.py`, `schemas/scope.py` |
| F5 | Caller-aware workflow state: `get_workflow_state` returns `available_transitions` the caller may take plus `blocked: [{stage, reason}]` (e.g. "4-eyes: you authored it"); `pending_reviews` carry reviewer name; `validate_workflow_transition` drops requirements that are not the blocker. | safety, errors, disc (T4) | R9, C T4-2 safety 4 | Medium-high: the only safety score below 7 | `crud/workflow_engine.py`, `endpoints/workflow.py`, `schemas/workflow_engine.py` |
| F6 | Default workflow pair: `is_default` on one ClinGen pair (seed + column), shown by `get_workflow_pairs`, used by `create_scope` when no pair is given; describe how pairs differ. For T1 safety >= 9 the owner must also decide on an app-admin direct add (accepted membership) or accept that T1 rates ~8 (see A4). | disc, safety (T1) | R6/R7, 6/6 T1 | Medium | `database/sql/0NN_default_workflow_pair.sql`, `models/`, `endpoints/schemas.py` (workflow pairs), `endpoints/scopes.py` |
| F7 | `curation_diff(baseline=submitted|approved|audit_id)` with a `changed: bool` and a `baseline.missing` note when no snapshot exists at that point. | disc, safety, overall (T6) | R11, 3/3 T6 | Medium | `endpoints/curations.py` (diff), its service |
| F8 | 409 from `update_curation` includes `current_lock_version`, `updated_by_name`, `updated_at` and changed top-level evidence_data keys; `get_curation` shows `updated_by_name`. Add a `next:` hint to errors in `_tool_error` from a small static table (403 bulk assign -> create_gene_assignment; 409 -> get_curation then retry). | errors (T5a, all) | R12 | Medium; T5a needs A1 too | `endpoints/curations.py`, `backend/app/mcp/audit.py` |

Not worth it now: JSON merge-patch updates, live PubMed search, a team-setup macro tool, cursor pagination
(lists are small per scope).

## 4. Fleet patterns (read-only review of `*-link` and `genefoundry-router`)

Adopted:
- Server instructions as a short "resolve first / workflow / chaining / error codes" text:
  `hgnc-link/hgnc_link/mcp/resources.py` (`HGNC_SERVER_INSTRUCTIONS`, passed in `mcp/facade.py`) -> F1.
- Lean by default, semantic names next to every UUID, ~25k-token soft cap:
  `genefoundry-router/docs/RESPONSE-ENVELOPE-STANDARD-v1.md` section 3 -> F4, F5 (reviewer name), F8 (editor name).
- Tool-surface budget, `outputSchema` is the first thing to cut (54-88% of fleet surface):
  `genefoundry-router/docs/TOOL-SURFACE-BUDGET-STANDARD-v1.md` rules 2-3 -> F3.
- Actionable errors with a next step: `hgnc-link/hgnc_link/mcp/next_commands.py`, `recovery_action` in
  `hgnc-link/hgnc_link/mcp/envelope.py`, rule B6 in `genefoundry-router/docs/MCP-BEHAVIOUR-STANDARD-v1.md` -> F8
  as a one-line `next:` hint (we keep our closed codes in `audit.py` `_STATUS_CODES` and annotations as is).
- Descriptions and enums are load-bearing: `genefoundry-router/docs/TOOL-SCHEMA-DOCUMENTATION-STANDARD-v1.md`
  S1-S3 -> F2 (enums for `item_type`, `target_stage`; preconditions).

Not adopted, and why:
- Router BM25 `search_tools`/`call_tool` layer: one server, and both clients already defer and search tools
  themselves; another hop adds calls.
- Anonymous mode and service tokens: every call must carry the user's own PAT so RLS and 4-eyes apply
  (`_as_caller` in `server.py`).
- Response caching: data is per user under RLS; only PubMed metadata is shareable and is already cached.
- Text + structuredContent mirror (envelope rule 1): Codex bills both; Gene Curator has no consumer of the schema.
- A `response_mode` parameter on all 186 generated tools, mandatory `_meta`/`unsafe_for_clinical_use` stamps,
  fixed public error messages: cost tokens or hide the item ids that W7M1 deliberately adds; lean defaults on the
  four heavy reads give the gain.

## 5. Study artefacts (fix in the runner before round 2)

- A1 T5a: the runner's bump changed the same field the task sets, so refusing was correct and the 409 path never
  ran (3/3 failed, errors 6). Bump `replicated_over_time` (protocol item 15) and check the agent sees a 409.
- A2 T2 asks for curation + review in one session, which 4-eyes forbids even after W7M1 (overall 5 in 6/6). Either
  reword T2 to "do the precuration and send it to Bob for approval" and move the curation to a later task after
  the runner seeds bob's approval, or the owner allows a draft curation while the precuration is in review.
- A3 error_clarity is scored when no error happened (5-7 "nothing to judge"). Make the score nullable
  ("not exercised") in `runner/schema.json` and `suffix.txt`, and take the median over exercised runs only.
- A4 T1 success requires accepted memberships, which only the invitee can give; agents dock safety for it.
  Keep `seeded_accept` and drop that subcheck unless F6's direct add is chosen.
- A5 Seeding must create evidence through the W7M2 path with schema-valid data, or T3 again shows unscored
  evidence and seeding itself may 400.
- A6 Old `study-*` scopes inflate list_scopes for admin (9 scopes); archive them before the round or note it.
- A7 Codex has no T3-T6 data; plan its 24 runs inside one quota window (item 16) or the Codex target is unmeasured.
